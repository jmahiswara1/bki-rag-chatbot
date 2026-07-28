import sys
sys.path.insert(0, r"E:\Project\bki-rag-chatbot")

from src.core.models import RetrievedChunk
from src.retrieval.domain_scorer import (
    detect_ship_type,
    apply_domain_scores,
    domain_boost_meta,
)


def _make_chunk(section_no: int, title: str, score: float, para: str = "A.1") -> RetrievedChunk:
    return RetrievedChunk(
        section_no=section_no, section_title=title, paragraph_id=para,
        content_type="narrative", table_no=None, figure_no=None,
        page_start=100, page_end=100, content=f"Content of Sec {section_no}", score=score,
    )


# --- detect_ship_type ---

def test_detect_container_ship():
    assert detect_ship_type("container ship scantling factors") == "container ship"

def test_detect_bulk_carrier():
    assert detect_ship_type("bulk carrier hatch opening plate") == "bulk carrier"

def test_detect_tanker():
    assert detect_ship_type("tanker deck structure") == "tanker"

def test_detect_passenger_ship():
    assert detect_ship_type("passenger ship fire protection") == "passenger ship"

def test_detect_tug():
    assert detect_ship_type("tug winch requirements") == "tug"

def test_detect_fishing_vessel():
    assert detect_ship_type("fishing vessel hull") == "fishing vessel"

def test_detect_dredger():
    assert detect_ship_type("dredger bottom structure") == "dredger"

def test_detect_barge():
    assert detect_ship_type("barge construction rules") == "barge"

def test_detect_pontoon():
    assert detect_ship_type("pontoon construction rules") == "pontoon"

def test_detect_supply_vessel():
    assert detect_ship_type("supply vessel scantling") == "supply vessel"

def test_detect_chemical():
    assert detect_ship_type("chemical tanker bulkhead") == "chemical"

def test_detect_liquefied_gas():
    assert detect_ship_type("liquefied gas carrier tank") == "liquefied gas"

def test_detect_floating_dock():
    assert detect_ship_type("floating dock special rules") == "floating dock"

def test_detect_none_generic():
    assert detect_ship_type("shell plating thickness minimum") is None

def test_detect_none_empty():
    assert detect_ship_type("") is None

def test_detect_none_irrelevant():
    assert detect_ship_type("longitudinal strength section modulus") is None


# --- apply_domain_scores ---

def test_apply_boost_container():
    chunks = [
        _make_chunk(23, "Bulk Carriers", 1.2),
        _make_chunk(39, "Container Ships", 0.9),
        _make_chunk(6, "Shell Plating", 1.5),
    ]
    result = apply_domain_scores(chunks, "container ship")
    # Sec 39 (+2.0) should now be top
    assert result[0].section_no == 39
    assert abs(result[0].score - 2.9) < 0.001

def test_apply_boost_bulk_carrier():
    chunks = [
        _make_chunk(23, "Bulk Carriers", 0.8),
        _make_chunk(39, "Container Ships", 1.0),
        _make_chunk(6, "Shell Plating", 1.5),
    ]
    result = apply_domain_scores(chunks, "bulk carrier")
    assert result[0].section_no == 23
    assert abs(result[0].score - 2.8) < 0.001

def test_apply_boost_tanker():
    chunks = [
        _make_chunk(24, "Tankers", 0.7),
        _make_chunk(6, "Shell Plating", 1.5),
    ]
    result = apply_domain_scores(chunks, "tanker")
    assert result[0].section_no == 24
    assert abs(result[0].score - 2.7) < 0.001

def test_apply_no_ship_type_none():
    chunks = [
        _make_chunk(39, "Container Ships", 0.9),
        _make_chunk(6, "Shell Plating", 1.5),
    ]
    result = apply_domain_scores(chunks, None)
    # Scores unchanged, Sec 6 still top
    assert result[0].section_no == 6
    assert result[0].score == 1.5

def test_apply_no_ship_type_unknown():
    chunks = [
        _make_chunk(39, "Container Ships", 0.9),
        _make_chunk(6, "Shell Plating", 1.5),
    ]
    result = apply_domain_scores(chunks, "unknown_ship_type")
    assert result[0].section_no == 6
    assert result[0].score == 1.5

def test_apply_empty_chunks():
    result = apply_domain_scores([], "container ship")
    assert result == []

def test_apply_multiple_same_section():
    chunks = [
        _make_chunk(39, "Container Ships", 1.0, para="A.1"),
        _make_chunk(39, "Container Ships", 0.5, para="A.2"),
        _make_chunk(6, "Shell Plating", 1.2),
    ]
    result = apply_domain_scores(chunks, "container ship")
    # Both Sec 39 chunks boosted
    assert result[0].section_no == 39
    assert result[1].section_no == 39
    assert abs(result[0].score - 3.0) < 0.001
    assert abs(result[1].score - 2.5) < 0.001

def test_apply_boost_ore_carrier():
    chunks = [
        _make_chunk(23, "Bulk Carriers", 0.6),
        _make_chunk(6, "Shell Plating", 1.5),
    ]
    result = apply_domain_scores(chunks, "ore carrier")
    assert result[0].section_no == 23
    assert abs(result[0].score - 2.6) < 0.001


# --- domain_boost_meta ---

def test_meta_container():
    meta = domain_boost_meta("container ship")
    assert meta is not None
    assert meta["ship_type"] == "container ship"
    assert meta["target_section"] == 39
    assert meta["boost"] == 2.0
    assert "Container Ships" in meta["label"]

def test_meta_bulk_carrier():
    meta = domain_boost_meta("bulk carrier")
    assert meta is not None
    assert meta["target_section"] == 23

def test_meta_unknown():
    assert domain_boost_meta("unknown") is None

def test_meta_none():
    assert domain_boost_meta(None) is None


# ---------- Runner ----------

if __name__ == "__main__":
    test_detect_container_ship()
    test_detect_bulk_carrier()
    test_detect_tanker()
    test_detect_passenger_ship()
    test_detect_tug()
    test_detect_fishing_vessel()
    test_detect_dredger()
    test_detect_barge()
    test_detect_pontoon()
    test_detect_supply_vessel()
    test_detect_chemical()
    test_detect_liquefied_gas()
    test_detect_floating_dock()
    test_detect_none_generic()
    test_detect_none_empty()
    test_detect_none_irrelevant()
    test_apply_boost_container()
    test_apply_boost_bulk_carrier()
    test_apply_boost_tanker()
    test_apply_no_ship_type_none()
    test_apply_no_ship_type_unknown()
    test_apply_empty_chunks()
    test_apply_multiple_same_section()
    test_apply_boost_ore_carrier()
    test_meta_container()
    test_meta_bulk_carrier()
    test_meta_unknown()
    test_meta_none()
    print(f"\nAll {len([f for f in dir() if f.startswith('test_')])} tests passed!")
