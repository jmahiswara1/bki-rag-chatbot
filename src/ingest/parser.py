from dataclasses import dataclass, field
from typing import Optional
import re
import fitz
import pdfplumber

@dataclass
class PageContent:
    page_no: int
    section_no: Optional[int]
    section_title: Optional[str]
    text: str
    tables: list[tuple[Optional[str], str]] = field(default_factory=list)


_BKI_HEADER_KEYWORDS = (
    "Seagoing Ships", "Rules for Hull", "Rules for Machinery",
    "Rules for Equipment", "Rules for Electrical",
)


def _bbox_overlap_ratio(block_bbox, table_bbox):
    """Fraction of block bbox area that falls inside table bbox."""
    x0b, y0b, x1b, y1b = block_bbox
    x0t, y0t, x1t, y1t = table_bbox

    ix0 = max(x0b, x0t)
    iy0 = max(y0b, y0t)
    ix1 = min(x1b, x1t)
    iy1 = min(y1b, y1t)

    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0

    inter_area = (ix1 - ix0) * (iy1 - iy0)
    block_area = (x1b - x0b) * (y1b - y0b)
    return inter_area / block_area if block_area > 0 else 0.0


def _is_header_block(text: str) -> bool:
    return any(kw in text for kw in _BKI_HEADER_KEYWORDS)


def _extract_major_from_header(text: str) -> str:
    """Extract major section letter (e.g. 'B') from a header block, if present."""
    m = re.search(r"\n([A-Z])\.\s*$", text)
    return m.group(1) if m else ""


def _is_footer_block(text: str) -> bool:
    return "Biro Klasifikasi Indonesia" in text or bool(re.match(r"^Page\s+\d", text))


def _blocks_to_narrative_text(blocks, table_bboxes):
    """Reconstruct page text from fitz blocks, excluding table-body blocks."""
    sorted_blocks = sorted(blocks, key=lambda b: (b[1], b[0]))
    output_lines = []
    major_prefix = ""

    for b in sorted_blocks:
        text = b[4].strip()
        if not text:
            continue
        if _is_footer_block(text):
            continue

        if _is_header_block(text):
            major_prefix = _extract_major_from_header(text)
            continue

        bbox = (b[0], b[1], b[2], b[3])
        if any(_bbox_overlap_ratio(bbox, tb) > 0.5 for tb in table_bboxes):
            continue

        output_lines.append(text)

    if major_prefix and output_lines:
        output_lines.insert(0, major_prefix + ".")

    return "\n".join(output_lines).strip().replace("\x00", "")


def parse_pdf(pdf_path: str, pages: Optional[list[int]] = None) -> list[PageContent]:
    doc = fitz.open(pdf_path)
    plumber_doc = pdfplumber.open(pdf_path)

    page_indices = pages if pages is not None else range(len(doc))
    results = []

    for idx in page_indices:
        page = doc[idx]
        raw_text = page.get_text("text")
        table_titles = re.findall(r"Table\s+(\d+\.\d+)", raw_text)

        plumber_page = plumber_doc.pages[idx]

        # Extract table bboxes for block filtering
        plumber_tables = plumber_page.find_tables({"text_x_tolerance": 1.5})
        table_bboxes = [t.bbox for t in plumber_tables]

        # Extract table data
        raw_tables = plumber_page.extract_tables({"text_x_tolerance": 1.5})
        tables_str = []
        for t_idx, tbl in enumerate(raw_tables):
            tbl_lines = []
            for row in tbl:
                clean_row = [str(c).replace("\n", " ").replace("\x00", "").strip() if c else "" for c in row]
                tbl_lines.append(" | ".join(clean_row))
            if tbl_lines:
                t_no = table_titles[t_idx] if t_idx < len(table_titles) else None
                tables_str.append((t_no, "\n".join(tbl_lines)))

        # Section/heading detection from raw_text (unchanged)
        lines = raw_text.split("\n")
        section_no = None
        section_title = None

        header_end_idx = 0
        for i, line in enumerate(lines[:15]):
            if line.startswith("Sec "):
                try:
                    section_no = int(line.replace("Sec ", "").strip())
                    if i + 1 < len(lines):
                        section_title = lines[i + 1].strip()
                    header_end_idx = i + 2
                    break
                except ValueError:
                    pass
            elif line.strip() == "Sec":
                try:
                    section_no = int(lines[i + 1].strip())
                    section_title = lines[i + 2].strip()
                    header_end_idx = i + 3
                    break
                except (ValueError, IndexError):
                    pass

        # Build narrative text from blocks, excluding table-body blocks
        blocks = page.get_text("blocks")
        block_text = _blocks_to_narrative_text(blocks, table_bboxes)

        # Strip trailing blank/footer lines
        text_lines = block_text.split("\n")
        while text_lines and (not text_lines[-1].strip() or _is_footer_block(text_lines[-1])):
            text_lines.pop()

        clean_text = "\n".join(text_lines).strip().replace("\x00", "")

        results.append(PageContent(
            page_no=idx + 1,
            section_no=section_no,
            section_title=section_title,
            text=clean_text,
            tables=tables_str,
        ))

    doc.close()
    plumber_doc.close()
    return results
