"""Build 28 — DB repair: targeted narrative re-ingest for 23 pages with duplicates.

Read-only dry-run by default. Pass --execute to write.

Strategy:
  1. For each duplicate page, backup the duplicate narrative rows only.
  2. Delete those specific narrative rows.
  3. Re-ingest the page with fixed parser/chunker.
  4. Insert only the NEW narrative chunks (table + figure chunks are preserved as-is).
  5. Captions, notes, footnotes, prose preserved; table cells excluded from narrative.
"""
import sys, io, json, os, re
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from src.core.db import get_client
from src.ingest.parser import parse_pdf
from src.ingest.chunker import chunk_pages
from src.ingest.embedder import embed_batch

PDF_PATH = Path(__file__).resolve().parent.parent / "data" / "bki_hull_2026.pdf"
BACKUP_DIR = Path(__file__).resolve().parent.parent / "build28_backup"
EXECUTE = "--execute" in sys.argv


def _norm(s: str) -> str:
    s = s.strip().lower()
    s = s.replace("\u2264", "<=").replace("\u2265", ">=")
    s = s.replace("\u00b7", "*").replace("\u00d7", "x")
    s = re.sub(r"\s+", "", s)
    return s


def is_true_duplicate(tc: str, nc: str, tn: str) -> bool:
    def tokens(text):
        toks = set()
        for line in text.split("\n"):
            ln = _norm(line)
            if not ln:
                continue
            for p in [p for p in re.split(r"\s*\|\s*", ln) if p]:
                if re.search(r"\d", p):
                    toks.add(p)
        return toks
    tt = tokens(tc)
    nt = tokens(nc)
    jac = len(tt & nt) / len(tt | nt) if (tt and nt) else 0.0

    data_rows = []
    for line in tc.split("\n"):
        ln = _norm(line)
        if not ln or not re.search(r"\d", ln):
            continue
        cells = [p for p in re.split(r"\s*\|\s*", ln) if p]
        if cells:
            data_rows.append(cells)
    nf = _norm(nc)
    rec = sum(1 for r in data_rows if all(c in nf for c in r))
    rr = rec / len(data_rows) if data_rows else 0.0
    all_rows = rec == len(data_rows) and len(data_rows) > 0

    same_ref = tn and tn.lower() in nc.lower()
    if all_rows and same_ref and rr >= 0.75:
        return True
    if all_rows and jac >= 0.25:
        return True
    if rr >= 0.8 and jac >= 0.20 and same_ref:
        return True
    return rr >= 0.8 and jac >= 0.30


def run():
    print("Loading all chunks from DB...")
    client = get_client()
    all_chunks = client.table("chunks").select("*").order("id").execute()
    chunks_by_id = {c["id"]: c for c in all_chunks.data}

    table_chunks = [c for c in all_chunks.data if c["content_type"] == "table"]
    narrative_by_page = defaultdict(list)
    for c in all_chunks.data:
        if c["content_type"] == "narrative":
            for p in range(c["page_start"], c["page_end"] + 1):
                narrative_by_page[p].append(c)

    # Find duplicate narrative chunks per page
    dup_narr_ids = set()
    dup_pages = set()
    dup_pairs = []
    for tc in table_chunks:
        pn = tc["page_start"]
        for nc in narrative_by_page.get(pn, []):
            if is_true_duplicate(tc["content"], nc["content"], tc.get("table_no") or ""):
                dup_narr_ids.add(nc["id"])
                dup_pages.add(pn)
                dup_pairs.append((tc["id"], nc["id"], pn, tc.get("table_no")))

    dup_pages = sorted(dup_pages)
    dup_narr_ids = sorted(dup_narr_ids)
    print(f"  {len(dup_narr_ids)} duplicate narrative chunks across {len(dup_pages)} pages")

    # Count existing chunks per page
    before_ct = defaultdict(lambda: defaultdict(int))
    for c in all_chunks.data:
        for p in range(c["page_start"], c["page_end"] + 1):
            if p in dup_pages:
                before_ct[p][c["content_type"]] += 1

    print("\nBefore counts per page:")
    for pn in dup_pages:
        print(f"  Page {pn}: {dict(before_ct[pn])}")

    if not EXECUTE:
        print(f"\n=== DRY-RUN ===")
        print(f"  Would DELETE {len(dup_narr_ids)} narrative rows")
        print(f"  Would RE-INGEST {len(dup_pages)} pages (narrative only)")
        print(f"  Would preserve all table + figure + formula chunks")
        for tc_id, nc_id, pn, tn in dup_pairs:
            c = chunks_by_id[nc_id]
            print(f"    Page {pn}: DELETE narr {nc_id} (para={c.get('paragraph_id')}, table={tn})")
        return

    # ── EXECUTION ────────────────────────────────────────────────────
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # Backup duplicate narrative rows
    backup_rows = []
    for nid in dup_narr_ids:
        row = chunks_by_id.get(nid)
        if row:
            backup_rows.append({k: v for k, v in row.items() if k != "embedding"})

    backup_path = BACKUP_DIR / f"backup_{timestamp}.json"
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(backup_rows, f, indent=2, ensure_ascii=False)
    print(f"\nBackup: {backup_path} ({len(backup_rows)} rows)")

    rollback_path = BACKUP_DIR / f"rollback_{timestamp}.py"
    with open(rollback_path, "w", encoding="utf-8") as f:
        f.write(f'"""Rollback Build 28 — restore {len(backup_rows)} rows."""\n'
                f'import sys, json\n'
                f'from pathlib import Path\n'
                f'sys.path.insert(0, str(Path(__file__).resolve().parent.parent))\n'
                f'from src.core.db import get_client\n'
                f'with open(r"{backup_path}", "r", encoding="utf-8") as fp:\n'
                f'    rows = json.load(fp)\n'
                f'client = get_client()\n'
                f'for row in rows:\n'
                f'    insert_data = {{k: v for k, v in row.items() if k != "id"}}\n'
                f'    client.table("chunks").insert(insert_data).execute()\n'
                f'print(f"Restored {{len(rows)}} rows")\n')
    print(f"Rollback: {rollback_path}")

    # Delete duplicate narrative rows
    print(f"\nDeleting {len(dup_narr_ids)} duplicate narratives...")
    for nid in dup_narr_ids:
        client.table("chunks").delete().eq("id", nid).execute()
        print(f"  Deleted narrative chunk {nid}")

    # Re-ingest affected pages (narrative only)
    page_indices = [p - 1 for p in dup_pages]
    parsed = parse_pdf(str(PDF_PATH), pages=page_indices)
    all_new = chunk_pages(parsed)

    # Only insert NEW narrative chunks (table chunks are unchanged)
    new_narratives = [c for c in all_new if c.content_type == "narrative"]

    print(f"\nRe-ingested {len(dup_pages)} pages -> {len(all_new)} total new chunks")
    print(f"  Table chunks (will NOT insert, keep existing): {len([c for c in all_new if c.content_type == 'table'])}")
    print(f"  Narrative chunks to insert: {len(new_narratives)}")

    # Embed and insert new narratives
    inserted = 0
    batch_size = 50
    for i in range(0, len(new_narratives), batch_size):
        batch = new_narratives[i:i + batch_size]
        texts = [c.content for c in batch]
        embeddings = embed_batch(texts)

        batch_rows = []
        for c, emb in zip(batch, embeddings):
            batch_rows.append({
                "section_no": c.section_no,
                "section_title": c.section_title,
                "paragraph_id": c.paragraph_id,
                "content_type": c.content_type,
                "table_no": c.table_no,
                "figure_no": c.figure_no,
                "page_start": c.page_start,
                "page_end": c.page_end,
                "content": c.content,
                "embedding": emb,
            })
        client.table("chunks").insert(batch_rows).execute()
        inserted += len(batch_rows)
        print(f"  Inserted batch {i // batch_size + 1} ({len(batch_rows)} rows)")

    # Verify
    remaining = client.table("chunks").select("id", count="exact").execute()
    print(f"\n=== Post-repair ===")
    print(f"  Before: {len(chunks_by_id)} chunks")
    print(f"  Deleted: {len(dup_narr_ids)}")
    print(f"  Inserted: {inserted}")
    print(f"  Now: {remaining.count}")

    # Check chunk 746
    check = client.table("chunks").select("id").eq("id", 746).execute()
    print(f"  Chunk 746: {'STILL EXISTS' if check.data else 'GONE'}")

    # Check all table chunks preserved
    for tc in table_chunks:
        if tc["page_start"] in dup_pages:
            existing = client.table("chunks").select("id,content_type,table_no").eq("id", tc["id"]).execute()
            if not existing.data:
                print(f"  WARNING: table chunk {tc['id']} MISSING!")
            else:
                print(f"  OK: table chunk {tc['id']} (Table {tc.get('table_no')}) preserved")

    # After counts
    check_all = client.table("chunks").select("id,content_type").order("id").execute()
    after_ct = defaultdict(lambda: defaultdict(int))
    for c in check_all.data:
        for p in range(c.get("page_start", 0), c.get("page_end", 0) + 1):
            if p in dup_pages:
                after_ct[p][c.get("content_type", "?")] += 1

    print(f"\nPage-level after counts:")
    for pn in dup_pages:
        print(f"  Page {pn}: was {dict(before_ct[pn])} -> now {dict(after_ct[pn])}")


if __name__ == "__main__":
    run()
