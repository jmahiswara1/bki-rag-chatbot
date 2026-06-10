from dataclasses import dataclass, field
from typing import Optional
import fitz
import pdfplumber

@dataclass
class PageContent:
    page_no: int
    section_no: Optional[int]
    section_title: Optional[str]
    text: str
    tables: list[tuple[Optional[str], str]] = field(default_factory=list)

def parse_pdf(pdf_path: str, pages: Optional[list[int]] = None) -> list[PageContent]:
    doc = fitz.open(pdf_path)
    plumber_doc = pdfplumber.open(pdf_path)
    
    page_indices = pages if pages is not None else range(len(doc))
    results = []
    
    import re
    
    for idx in page_indices:
        page = doc[idx]
        raw_text = page.get_text("text")
        table_titles = re.findall(r'Table\s+(\d+\.\d+)', raw_text)
        
        plumber_page = plumber_doc.pages[idx]
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
        
        lines = raw_text.split("\n")
        section_no = None
        section_title = None
        
        header_end_idx = 0
        for i, line in enumerate(lines[:15]):
            if line.startswith("Sec "):
                try:
                    section_no = int(line.replace("Sec ", "").strip())
                    if i + 1 < len(lines):
                        section_title = lines[i+1].strip()
                    header_end_idx = i + 2
                    break
                except ValueError:
                    pass
            elif line.strip() == "Sec":
                try:
                    section_no = int(lines[i+1].strip())
                    section_title = lines[i+2].strip()
                    header_end_idx = i + 3
                    break
                except (ValueError, IndexError):
                    pass
                    
        if header_end_idx > 0:
            lines = lines[header_end_idx:]
            
        while lines and ("Biro Klasifikasi Indonesia" in lines[-1] or "Page " in lines[-1] or not lines[-1].strip()):
            lines.pop()
            
        clean_text = "\n".join(lines).strip().replace("\x00", "")
        
        results.append(PageContent(
            page_no=idx + 1,
            section_no=section_no,
            section_title=section_title,
            text=clean_text,
            tables=tables_str
        ))
        
    doc.close()
    plumber_doc.close()
    return results

