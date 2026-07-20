"""Build 34 — source-grounded sibling-table disambiguation regression tests.

EN C*->COLL must return COLL-Notation mapping values, NOT v*cr speed values.
Speed queries must correctly cite T35.2 with v*cr values.
ID C*->COLL must cite T35.1.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.llm.chain import _pre_answer_pipeline


class TestSiblingDisambiguationEN:
    """EN C*->COLL must return mapping, not speed."""

    def test_en_c_to_coll_ranking_boosts_t351(self):
        """T35.1 must be ranked above C.1 narrative after boost."""
        state = _pre_answer_pipeline("COLL notation for C star 3", None, "default")
        candidates = state.candidates
        t351_rank = None
        c1_rank = None
        for i, c in enumerate(candidates):
            if c.table_no == "35.1":
                t351_rank = i
            if "C.1" in c.content[:80] and c.content_type == "narrative":
                c1_rank = i
        assert t351_rank is not None, "T35.1 not found in candidates"
        assert t351_rank < c1_rank, (
            f"T35.1 at rank {t351_rank} must be above C.1 at rank {c1_rank}"
        )

    def test_en_c_to_coll_table_evidence_is_coll2(self):
        """Table selector must emit COLL 2 for C*=3, not v*cr."""
        state = _pre_answer_pipeline("COLL notation for C star 3", None, "default")
        assert state.table_evidence, "Table evidence must not be empty"
        assert "COLL 2" in state.table_evidence, (
            f"Expected COLL 2 in table_evidence, got: {state.table_evidence[:200]}"
        )
        assert "v*" not in state.table_evidence, (
            "table_evidence must NOT contain v*cr speed values"
        )

    def test_en_speed_retrieves_t352(self):
        """Speed query must return T35.2 chunk with v*cr values."""
        state = _pre_answer_pipeline(
            "minimum critical speed vcr for COLL 2", None, "default"
        )
        candidates = state.candidates
        t352_found = any(
            c.table_no == "35.2" and "v*" in c.content
            for c in candidates
        )
        assert t352_found, "Speed query must retrieve T35.2 with v* content"


class TestSiblingDisambiguationID:
    """ID C*->COLL must cite T35.1 (citation lock, pre-existing value drift noted)."""

    def test_id_c_to_coll_cites_t351(self):
        """ID C*->COLL must cite Table 35.1 and return COLL notation, not v*cr."""
        state = _pre_answer_pipeline("notasi COLL untuk C 3", None, "default")
        assert state.table_evidence, "Table evidence must not be empty"
        assert "Table 35.1" in state.table_evidence, (
            f"Expected Table 35.1 citation, got: {state.table_evidence[:200]}"
        )
        assert "COLL 2" in state.table_evidence, (
            f"Expected COLL 2 value, got: {state.table_evidence[:200]}"
        )
        assert "v*" not in state.table_evidence, (
            "Table evidence must not contain speed values from sibling T35.2"
        )

    def test_id_speed_retrieves_t352(self):
        """ID speed query must retrieve T35.2 chunk."""
        state = _pre_answer_pipeline(
            "kecepatan kritis minimum vcr untuk COLL 2", None, "default"
        )
        candidates = state.candidates
        t352_found = any(
            c.table_no == "35.2" and "v*" in c.content
            for c in candidates
        )
        assert t352_found, "ID speed query must retrieve T35.2 with v* content"
