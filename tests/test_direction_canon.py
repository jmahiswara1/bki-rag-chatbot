"""Unit tests for Build 41 fore/aft direction canonicalization.

canonicalize_direction_query() deterministically fixes a condensed English
query that drifted fore/aft direction (e.g. original 'bagian buritan' ->
'at the bow'). Pure function, no DB/Ollama.
"""
import sys
sys.path.insert(0, r"E:\Project\bki-rag-chatbot")

from src.llm.chain import canonicalize_direction_query


def test_aft_pinned_bow_drift_fixed():
    out = canonicalize_direction_query(
        "Berapa ketebalan pelat pada bangunan atas di bagian buritan?",
        "What is the plate thickness of the superstructure at the bow?",
    )
    assert "aft" in out
    assert "bow" not in out


def test_aft_pinned_in_bow_drift_fixed():
    out = canonicalize_direction_query(
        "geladak di buritan",
        "the deck in the bow",
    )
    assert "aft" in out
    assert "bow" not in out


def test_fwd_pinned_stern_drift_fixed():
    out = canonicalize_direction_query(
        "struktur di bagian haluan",
        "the structure at the stern",
    )
    assert "forward" in out
    assert "stern" not in out


def test_no_direction_no_change():
    q = "What is the plate thickness of the superstructure?"
    out = canonicalize_direction_query("Berapa tebal pelat bangunan atas?", q)
    assert out == q


def test_correct_direction_unchanged():
    q = "What is the plate thickness of the superstructure at the bow?"
    out = canonicalize_direction_query("struktur di haluan", q)
    assert out == q


def test_no_overreach_on_forward_already():
    q = "What is the plate thickness of the superstructure forward?"
    out = canonicalize_direction_query("struktur di bagian haluan", q)
    assert out == q
