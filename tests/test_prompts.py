"""Static tests for src/llm/prompts.py SYSTEM_PROMPT.

These tests verify the SYSTEM_PROMPT retains the constraints required by
AGENTS.md and includes the anti-fabrication clauses added in the
answer-faithfulness fix.  No LLM calls are made.
"""
import sys
sys.path.insert(0, r"E:\Project\bki-rag-chatbot")

from src.llm.prompts import SYSTEM_PROMPT, TRANSLATE_CONDENSE_SYSTEM


def test_system_prompt_preserves_citation_format():
    """Canonical citation format (Sec N | paragraph_id p.XX) must remain."""
    assert "(Sec N | paragraph_id p.XX)" in SYSTEM_PROMPT


def test_system_prompt_preserves_language_constraint():
    """Hard language constraint must remain."""
    assert "LANGUAGE CONSTRAINT" in SYSTEM_PROMPT


def test_system_prompt_preserves_no_manual_compute():
    """Calculator-results-only rule must remain."""
    assert "calculator results" in SYSTEM_PROMPT


def test_system_prompt_has_anti_fabrication_no_invent():
    """Anti-fabrication: do not invent values/formulas."""
    assert "Do not invent" in SYSTEM_PROMPT


def test_system_prompt_has_anti_fabrication_no_fabricate_citation():
    """Anti-fabrication: never fabricate a citation."""
    assert "Never fabricate a citation" in SYSTEM_PROMPT


def test_system_prompt_has_not_found_clause():
    """If value/formula not in context, say so explicitly."""
    assert "not found in the retrieved rules" in SYSTEM_PROMPT


def test_system_prompt_has_no_guess_clause():
    """Do not guess when context is missing a piece of the answer."""
    assert "Do not guess" in SYSTEM_PROMPT


def test_system_prompt_has_verbatim_values_clause():
    """Values must come verbatim from context, not approximated."""
    assert "verbatim in the context" in SYSTEM_PROMPT


def test_system_prompt_has_contradiction_rule():
    """Contradiction resolution: prefer most relevant section."""
    assert "prioritize the value" in SYSTEM_PROMPT


def test_system_prompt_has_no_flat_menu():
    """Contradiction: do NOT list contradictory values as a flat menu."""
    assert "flat menu" in SYSTEM_PROMPT


def test_translate_condense_has_history_facts_rule():
    """Translate prompt must instruct folding history facts."""
    assert "From conversation history" in TRANSLATE_CONDENSE_SYSTEM


def test_translate_condense_has_self_contained_rule():
    """History facts must produce self-contained question."""
    assert "fully self-contained" in TRANSLATE_CONDENSE_SYSTEM


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_system_prompt_preserves_citation_format()
    test_system_prompt_preserves_language_constraint()
    test_system_prompt_preserves_no_manual_compute()
    test_system_prompt_has_anti_fabrication_no_invent()
    test_system_prompt_has_anti_fabrication_no_fabricate_citation()
    test_system_prompt_has_not_found_clause()
    test_system_prompt_has_no_guess_clause()
    test_system_prompt_has_verbatim_values_clause()
    test_system_prompt_has_contradiction_rule()
    test_system_prompt_has_no_flat_menu()
    test_translate_condense_has_history_facts_rule()
    test_translate_condense_has_self_contained_rule()
    print(f"\nAll {len([f for f in dir() if f.startswith('test_')])} tests passed!")
