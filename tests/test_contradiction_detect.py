import sys
sys.path.insert(0, r"E:\Project\bki-rag-chatbot")

from src.core.models import RetrievedChunk
from src.retrieval.contradiction_detect import (
    detect_contradictions,
    build_conflict_annotation,
)


def _ck(section_no, title, content, score=1.0, para="A.1"):
    return RetrievedChunk(
        section_no=section_no, section_title=title, paragraph_id=para,
        content_type="narrative", table_no=None, figure_no=None,
        page_start=100, page_end=100, content=content, score=score,
    )


# --- detect_contradictions ---

def test_no_conflict_single_section():
    chunks = [
        _ck(17, "Cargo Hatchways", "hatch opening plate thickness 1.0 mm"),
        _ck(17, "Cargo Hatchways", "coaming thickness 2.0 mm"),
    ]
    conflicts = detect_contradictions(chunks, "hatch plate thickness")
    # both chunks from Sec 17, same unit "mm" → only 1 section → no conflict
    assert conflicts is None or len(conflicts) == 0

def test_conflict_different_sections():
    chunks = [
        _ck(17, "Cargo Hatchways", "hatch opening plate thickness 1.0 mm"),
        _ck(30, "Sheltered Water Service", "minimum plate thickness 3.0 mm"),
    ]
    conflicts = detect_contradictions(chunks, "hatch plate thickness")
    assert conflicts is not None
    assert len(conflicts) >= 1
    assert 17 in conflicts[0][1]
    assert 30 in conflicts[0][1]

def test_no_conflict_different_units():
    chunks = [
        _ck(17, "Cargo Hatchways", "plate thickness 1.0 mm"),
        _ck(7, "Decks", "deck load 5.0 kN"),
    ]
    conflicts = detect_contradictions(chunks, "hatch plate thickness")
    # different units (mm vs kN) → no conflict
    assert conflicts is None

def test_empty_chunks():
    assert detect_contradictions([], "hatch thickness") is None

def test_single_chunk():
    chunks = [_ck(17, "Cargo Hatchways", "thickness 1.0 mm")]
    assert detect_contradictions(chunks, "hatch") is None

def test_two_chunks_same_section_values():
    chunks = [
        _ck(17, "Cargo Hatchways", "position 1 plate 600 mm"),
        _ck(17, "Cargo Hatchways", "position 2 plate 380 mm"),
    ]
    conflicts = detect_contradictions(chunks, "hatch thickness")
    # same section, different values but valid → no cross-section conflict
    assert conflicts is None

def test_three_chunks_two_conflicting():
    chunks = [
        _ck(17, "Cargo Hatchways", "plate thickness 600 mm"),
        _ck(30, "Sheltered Water", "minimum 3.0 mm"),
        _ck(7, "Decks", "deck load 5.0 kN"),
    ]
    conflicts = detect_contradictions(chunks, "hatch plate thickness")
    # mm appears in 17 + 30 → conflict
    assert conflicts is not None
    assert any(unit == "mm" for unit, _ in conflicts)

def test_multiple_units_conflict():
    chunks = [
        _ck(17, "Cargo Hatchways", "plate 600 mm and 5.0 kN"),
        _ck(7, "Decks", "deck plate 4.0 mm and 10.0 kN"),
    ]
    conflicts = detect_contradictions(chunks, "deck hatch")
    # mm and kN both appear in 17 + 7
    assert conflicts is not None
    assert len(conflicts) == 2


# --- build_conflict_annotation ---

def test_annotation_with_conflict():
    chunks = [
        _ck(17, "Cargo Hatchways", "hatch opening plate thickness 600 mm hatch"),
        _ck(30, "Sheltered Water Service", "minimum plate thickness 3.0 mm"),
    ]
    query = "what is the hatch opening plate thickness"
    anno = build_conflict_annotation(chunks, query)
    assert "CONTRADICTION ANNOTATION" in anno
    assert "PRIMARY SOURCE" in anno
    assert "Sec 17" in anno  # Cargo Hatchways should beat Sheltered Water for "hatch"

def test_annotation_no_conflict():
    chunks = [
        _ck(17, "Cargo Hatchways", "plate 600 mm"),
        _ck(7, "Decks", "deck load 5.0 kN"),
    ]
    anno = build_conflict_annotation(chunks, "hatch")
    assert anno == ""


# ---------- Runner ----------

if __name__ == "__main__":
    test_no_conflict_single_section()
    test_conflict_different_sections()
    test_no_conflict_different_units()
    test_empty_chunks()
    test_single_chunk()
    test_two_chunks_same_section_values()
    test_three_chunks_two_conflicting()
    test_multiple_units_conflict()
    test_annotation_with_conflict()
    test_annotation_no_conflict()
    print(f"\nAll {len([f for f in dir() if f.startswith('test_')])} tests passed!")
