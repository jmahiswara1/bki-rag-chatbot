from src.core.db import get_client
from src.ingest.chunker import chunk_pages
from src.ingest.embedder import embed
from src.ingest.parser import parse_pdf


def run(pdf_path: str) -> int:
    # parse -> chunk -> embed -> store.
    pages = parse_pdf(pdf_path)
    chunks = chunk_pages(pages)
    client = get_client()

    rows = []
    for c in chunks:
        header = f"[Sec {c.section_no} {c.section_title}] "
        c.embedding = embed(header + c.content)
        rows.append(
            {
                "section_no": c.section_no,
                "section_title": c.section_title,
                "paragraph_id": c.paragraph_id,
                "content_type": c.content_type,
                "table_no": c.table_no,
                "page_start": c.page_start,
                "page_end": c.page_end,
                "content": c.content,
                "embedding": c.embedding,
            }
        )

    # Batch insert to stay within request limits.
    for i in range(0, len(rows), 100):
        client.table("chunks").insert(rows[i : i + 100]).execute()
    return len(rows)
