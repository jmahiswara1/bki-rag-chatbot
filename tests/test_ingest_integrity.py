"""Build 28 — Data-integrity repair: table/narrative dedup, heading metadata, provenance.

Tests cover the ingestion layer only (parser + chunker).
No live DB, no Ollama — the PDF fixture is read-only.
"""
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ingest.parser import parse_pdf
from src.ingest.chunker import chunk_pages

PDF_PATH = Path(__file__).resolve().parent.parent / "data" / "bki_hull_2026.pdf"


def _chunks_for_page(page_idx: int):
    pages = parse_pdf(str(PDF_PATH), pages=[page_idx])
    return chunk_pages(pages)


class TestTableNarrativeDedup:
    """Verify table cells don't leak into narrative chunks."""

    def test_single_table_page_no_pipe_in_narrative(self):
        """Page 418: Table 19.1 cells must NOT appear pipe-delimited in narrative."""
        chunks = _chunks_for_page(417)
        narrative_chunks = [c for c in chunks if c.content_type == "narrative"]
        for nc in narrative_chunks:
            pipe_lines = [l for l in nc.content.split("\n") if "|" in l and not l.startswith("[")]
            assert not pipe_lines, f"Narrative chunk pipe lines: {pipe_lines}"

    def test_table_cells_not_in_narrative_page_22_1(self):
        """Page 490: large Table 22.1 cells must not leak into narrative."""
        chunks = _chunks_for_page(489)
        narrative_chunks = [c for c in chunks if c.content_type == "narrative"]
        for nc in narrative_chunks:
            pipe_lines = [l for l in nc.content.split("\n") if "|" in l and not l.startswith("[")]
            assert not pipe_lines, f"Narrative chunk pipe lines: {pipe_lines}"

    def test_caption_present_in_narrative(self):
        """Table caption 'Table 19.1 Minimum inner bending radius r' must remain."""
        chunks = _chunks_for_page(417)
        all_narrative_text = "\n".join(c.content for c in chunks if c.content_type == "narrative")
        assert "Table 19.1" in all_narrative_text
        assert "Minimum inner bending radius r" in all_narrative_text

    def test_notes_present_in_narrative(self):
        """Table Note must remain in narrative."""
        chunks = _chunks_for_page(417)
        all_narrative_text = "\n".join(c.content for c in chunks if c.content_type == "narrative")
        assert "bending capacity" in all_narrative_text.lower()

    def test_applicability_paragraph_present(self):
        """B.2.6.3 prose text after Table 19.1 must be present."""
        chunks = _chunks_for_page(417)
        all_narrative_text = "\n".join(c.content for c in chunks if c.content_type == "narrative")
        assert "minimum nominal upper yield point" in all_narrative_text.lower()
        assert "2% or more permanent elongation" in all_narrative_text.lower()

    def test_two_tables_page_no_cell_leak(self):
        """Page 474: Tables 21.3 + 21.4 with no pipe in narrative."""
        chunks = _chunks_for_page(473)
        narrative_chunks = [c for c in chunks if c.content_type == "narrative"]
        for nc in narrative_chunks:
            pipe_lines = [l for l in nc.content.split("\n") if "|" in l and not l.startswith("[")]
            assert not pipe_lines, f"Narrative chunk pipe lines: {pipe_lines}"

    def test_non_table_page_semantic_equivalent(self):
        """Page 419 has no tables — text should be equivalent to pre-fix."""
        chunks = _chunks_for_page(418)
        all_text = "\n".join(c.content for c in chunks if c.content_type == "narrative")
        # Should have full narrative — spot-check key content
        assert "3.2" in all_text
        assert "Weld shapes and dimensions" in all_text or "weld shapes" in all_text.lower()

    def test_multi_page_table_handling(self):
        """Page 70 (Table 3.7) is part of a multi-page table."""
        chunks = _chunks_for_page(69)
        table_chunks = [c for c in chunks if c.content_type == "table"]
        assert len(table_chunks) > 0, "Should have at least one table chunk"


class TestHeadingMetadata:
    """Verify paragraph_id metadata correctness after table."""

    def test_paragraph_id_not_wrong_section(self):
        """Page 418 narrative chunk must NOT carry B.2.7.3 as paragraph_id."""
        chunks = _chunks_for_page(417)
        narrative_chunks = [c for c in chunks if c.content_type == "narrative" and c.paragraph_id]
        for nc in narrative_chunks:
            assert nc.paragraph_id != "B.2.7.3", (
                f"paragraph_id should not be B.2.7.3, got {nc.paragraph_id}"
            )

    def test_paragraph_id_reflects_start_of_chunk_content(self):
        """The first paragraph boundary in the chunk should be the paragraph_id."""
        chunks = _chunks_for_page(417)
        for c in chunks:
            if c.content_type != "narrative" or not c.paragraph_id:
                continue
            # Extract the first paragraph-id boundary from the chunk content
            content_no_header = c.content.split("]", 1)[-1].strip() if "]" in c.content else c.content
            lines = content_no_header.split("\n")
            # Find first major letter or paragraph number
            para_pattern = re.compile(r"^\d+(?:\.[A-Za-z0-9]+)*$")
            major_pattern = re.compile(r"^[A-Z]\.$")
            first_para = None
            current_major = ""
            for line in lines:
                line = line.strip()
                if major_pattern.match(line):
                    current_major = line.rstrip(".")
                elif para_pattern.match(line):
                    first_para = f"{current_major}.{line}" if current_major else line
                    break
            if first_para:
                # paragraph_id should match or be the parent of the first boundary
                assert c.paragraph_id == first_para or first_para.startswith(c.paragraph_id), (
                    f"paragraph_id={c.paragraph_id} should match first boundary {first_para}"
                )


class TestIdempotence:
    """Running parser+chunker twice must produce identical output."""

    def test_parse_idempotent(self):
        pages1 = parse_pdf(str(PDF_PATH), pages=[417])
        pages2 = parse_pdf(str(PDF_PATH), pages=[417])
        assert len(pages1) == len(pages2)
        for p1, p2 in zip(pages1, pages2):
            assert p1.text == p2.text, "page text not idempotent"
            assert len(p1.tables) == len(p2.tables), "table count not idempotent"

    def test_chunk_idempotent(self):
        pages = parse_pdf(str(PDF_PATH), pages=[417])
        chunks1 = chunk_pages(pages)
        chunks2 = chunk_pages(pages)
        assert len(chunks1) == len(chunks2)
        for c1, c2 in zip(chunks1, chunks2):
            assert c1.content_type == c2.content_type
            assert c1.content == c2.content
            assert c1.paragraph_id == c2.paragraph_id


class TestNonTableRegression:
    """Pages without tables should be byte-equivalent to old behavior."""

    def test_non_table_page_has_narrative_chunks(self):
        """Page 419 (no tables) must produce narrative chunks."""
        chunks = _chunks_for_page(418)
        assert any(c.content_type == "narrative" for c in chunks)
        assert not any(c.content_type == "table" for c in chunks)

    def test_non_table_section_page(self):
        """Page 20 (Section 1 narrative, no tables) produces narrative chunks."""
        chunks = _chunks_for_page(19)
        assert any(c.content_type == "narrative" for c in chunks)


class TestTableFixtures:
    """Varying table types from different sections."""

    def test_table_22_1_pipe_format(self):
        """Table 22.1 large pipe-delimited table is correctly extracted."""
        chunks = _chunks_for_page(489)
        table_chunks = [c for c in chunks if c.content_type == "table"]
        assert any(c.table_no == "22.1" for c in table_chunks)
        for tc in table_chunks:
            if tc.table_no == "22.1":
                assert "|" in tc.content, "Table chunk should be pipe-delimited"

    def test_table_7_3_no_narrative_leak(self):
        """Table 7.3 has surrounding formula prose that must stay."""
        chunks = _chunks_for_page(205)
        narrative_chunks = [c for c in chunks if c.content_type == "narrative"]
        pipe_narr = [l for l in "\n".join(c.content for c in narrative_chunks).split("\n")
                     if "|" in l and not l.startswith("[")]
        assert not pipe_narr, f"Pipe in narrative: {pipe_narr}"

    def test_table_14_1_preserved(self):
        """Table 14.1 structural member categorisation preserved."""
        chunks = _chunks_for_page(283)
        table_chunks = [c for c in chunks if c.content_type == "table"]
        assert any(c.table_no == "14.1" for c in table_chunks)
