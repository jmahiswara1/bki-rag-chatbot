"""Unit tests for the lexical-anchor boost module (Build 45).

No DB, no LLM, no reranker.
"""
import sys
sys.path.insert(0, r"E:\Project\bki-rag-chatbot")

from src.core.models import RetrievedChunk
from src.retrieval.lexical_boost import apply_lexical_boosts


def _mk(sec, para, content, score):
    return RetrievedChunk(
        section_no=sec, section_title="", paragraph_id=para,
        content_type="narrative", table_no=None, figure_no=None,
        page_start=1, page_end=1, content=content, score=score,
    )


def test_indonesian_flag_boost_promotes_footnote():
    chunks = [
        _mk(24, "A.4.3.9", "Where a corner-to-corner situation occurs between a safe space and a cargo tank...", 2.0),
        _mk(12, "A.5.2.1", "1) For Indonesian flag ship, the cofferdams are also required between accommodation spaces and oil tanks.", 1.0),
        _mk(24, "E.1.2", "Cofferdam bulkheads forming boundaries of cargo tanks...", 0.5),
    ]
    out = apply_lexical_boosts(
        chunks,
        "Untuk kapal berbendera Indonesia, di area mana lagi sekat pembatas ganda (cofferdams) wajib disediakan?",
        "indonesian flag ship cofferdam accommodation spaces oil tanks",
    )
    assert out[0].paragraph_id == "A.5.2.1"
    assert out[0].section_no == 12


def test_no_boost_without_trigger():
    chunks = [
        _mk(24, "A.4.3.9", "corner-to-corner safe space cargo tank", 2.0),
        _mk(12, "A.5.2.1", "1) For Indonesian flag ship, the cofferdams are also required between accommodation spaces and oil tanks.", 1.0),
    ]
    out = apply_lexical_boosts(
        chunks,
        "Di mana cofferdam harus dipasang antara tangki bahan bakar dan tangki cairan lain?",
        "where must cofferdams be fitted between fuel oil tanks and other liquid tanks",
    )
    assert out[0].section_no == 24, "generic cofferdam query must not boost footnote"


def test_circulating_tank_boost_promotes_500mm():
    chunks = [
        _mk(12, "A.6.2", "Upon special approval on small ships the arrangement of cofferdams...", 1.5),
        _mk(8, "B.5.2.2", "The lubricating oil circulating tanks are to be separated from the shell by at least 500 mm.", 1.0),
    ]
    out = apply_lexical_boosts(
        chunks,
        "Berapa jarak minimum pemisahan tangki sirkulasi minyak lumas dari kulit lambung kapal?",
        "lubricating oil circulating tank shell separation minimum distance",
    )
    assert out[0].section_no == 8
    assert out[0].paragraph_id == "B.5.2.2"


def test_wheel_house_top_boost():
    chunks = [
        _mk(14, "A.2.3", "The rudder stock is to be carried through the hull...", 1.0),
        _mk(4, "C.5.2", "For exposed wheel house tops the load is not to be taken less than p = 2,5 [kN/m2].", 1.2),
    ]
    out = apply_lexical_boosts(
        chunks,
        "Berapakah beban desain minimum untuk area atap ruang kemudi yang terbuka?",
        "minimum design load exposed wheel house tops",
    )
    assert out[0].section_no == 4


def test_fire_door_gap_boost():
    chunks = [
        _mk(22, "B.6.6.2", "All openings in the divisions are to be provided with permanently attached means of closing...", 2.0),
        _mk(22, "C.6.3", "Doors approved without the sill being part of the frame ... shall be installed such that the gap under the door does not exceed 12 mm.", 1.0),
    ]
    out = apply_lexical_boosts(
        chunks,
        "Berapa batas maksimum celah di bawah pintu kebakaran yang dipasang pada atau setelah 1 Juli 2010?",
        "maximum gap under a fire door installed after 1 July 2010",
    )
    assert out[0].paragraph_id == "C.6.3"


def test_brittle_crack_thick_plates_boost():
    chunks = [
        _mk(23, "5.3", "The thickness of side shell plating located between hopper and upper wing tanks...", 1.0),
        _mk(39, "A.4.1", "For steel plates with thickness of over 50 mm and not greater than 100 mm, the measures for prevention of brittle crack initiation and propagation are to be taken.", 1.4),
    ]
    out = apply_lexical_boosts(
        chunks,
        "Untuk pelat baja sangat tebal di kapal kontainer, pada rentang ketebalan berapakah pencegahan retak getas wajib diterapkan?",
        "extremely thick steel plates container ship brittle crack prevention thickness range",
    )
    assert out[0].section_no == 39


def test_empty_chunks_noop():
    assert apply_lexical_boosts([], "anything", "indonesian flag") == []


# ---------- Runner ----------

if __name__ == "__main__":
    test_indonesian_flag_boost_promotes_footnote()
    test_no_boost_without_trigger()
    test_circulating_tank_boost_promotes_500mm()
    test_wheel_house_top_boost()
    test_fire_door_gap_boost()
    test_brittle_crack_thick_plates_boost()
    test_empty_chunks_noop()
    print("\nAll lexical_boost tests passed!")
