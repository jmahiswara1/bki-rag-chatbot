from dataclasses import dataclass, field


@dataclass
class PageContent:
    page_no: int
    text: str
    tables: list = field(default_factory=list)


def parse_pdf(pdf_path: str) -> list[PageContent]:
    # Hybrid parsing: pdftotext -layout for clean narrative glyphs,
    # pdfplumber.extract_tables for table structure. Strip repeating
    # page headers and footers after reading the section metadata.
    raise NotImplementedError("Phase 1: implement hybrid PDF parsing")
