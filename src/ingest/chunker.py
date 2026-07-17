import re
from src.core.models import Chunk
from src.ingest.parser import PageContent

def token_count(text: str) -> int:
    return len(text) // 4

def chunk_pages(pages: list[PageContent]) -> list[Chunk]:
    chunks = []

    for page in pages:
        if not page.section_no:
            continue

        context_prefix = f"[Sec {page.section_no} {page.section_title}"

        for table_no, tbl in page.tables:
            header = f"{context_prefix} | Table {table_no}]" if table_no else f"{context_prefix}]"
            chunks.append(Chunk(
                section_no=page.section_no,
                section_title=page.section_title or "",
                content_type="table",
                page_start=page.page_no,
                page_end=page.page_no,
                content=f"{header}\n{tbl}",
                table_no=table_no
            ))

        current_chunk_text = ""
        current_para_id = None
        chunk_start_para_id = None
        current_major = ""

        major_pattern = re.compile(r'^([A-Z])\.$')
        para_pattern = re.compile(r'^(\d+(?:\.[A-Za-z0-9]+)*)$')

        for line in page.text.split('\n'):
            line = line.strip()
            if not line:
                continue

            m_major = major_pattern.match(line)
            m_para = para_pattern.match(line)

            if m_major or m_para:
                if token_count(current_chunk_text) > 400:
                    header_para = chunk_start_para_id or current_para_id
                    header = f"{context_prefix} | {header_para}]" if header_para else f"{context_prefix}]"
                    is_formula = False
                    if "where" in current_chunk_text.lower() and "=" in current_chunk_text:
                        for ln in current_chunk_text.split('\n'):
                            if "=" in ln and len(ln.strip()) < 80:
                                is_formula = True
                                break
                    content_type = "formula" if is_formula else "narrative"
                    chunks.append(Chunk(
                        section_no=page.section_no,
                        section_title=page.section_title or "",
                        content_type=content_type,
                        page_start=page.page_no,
                        page_end=page.page_no,
                        content=f"{header}\n{current_chunk_text}",
                        paragraph_id=header_para
                    ))
                    current_chunk_text = ""
                    chunk_start_para_id = None

            if m_major:
                current_major = m_major.group(1)
            elif m_para:
                minor = m_para.group(1)
                current_para_id = f"{current_major}.{minor}" if current_major else minor
                if chunk_start_para_id is None:
                    chunk_start_para_id = current_para_id

            current_chunk_text = f"{current_chunk_text}\n{line}".strip()

        if current_chunk_text:
            header_para = chunk_start_para_id or current_para_id
            header = f"{context_prefix} | {header_para}]" if header_para else f"{context_prefix}]"
            is_formula = False
            if "where" in current_chunk_text.lower() and "=" in current_chunk_text:
                for ln in current_chunk_text.split('\n'):
                    if "=" in ln and len(ln.strip()) < 80:
                        is_formula = True
                        break
            content_type = "formula" if is_formula else "narrative"
            chunks.append(Chunk(
                section_no=page.section_no,
                section_title=page.section_title or "",
                content_type=content_type,
                page_start=page.page_no,
                page_end=page.page_no,
                content=f"{header}\n{current_chunk_text}",
                paragraph_id=header_para
            ))

    return chunks
