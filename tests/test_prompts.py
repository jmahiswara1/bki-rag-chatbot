"""Static tests for src/llm/prompts.py SYSTEM_PROMPT.

These tests verify the SYSTEM_PROMPT retains the constraints required by
AGENTS.md and includes the anti-fabrication clauses added in the
answer-faithfulness fix.  No LLM calls are made.
"""
import sys
sys.path.insert(0, r"E:\Project\bki-rag-chatbot")

from src.llm.prompts import SYSTEM_PROMPT, TRANSLATE_CONDENSE_SYSTEM, _ANSWER_STYLE_DETAILED


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


def test_system_prompt_has_no_echo_rule():
    """Model must NOT echo internal instructions."""
    assert "DO NOT REPEAT" not in SYSTEM_PROMPT  # only in user message
    assert "double brackets" in SYSTEM_PROMPT


def test_system_prompt_has_anti_repetition():
    """Anti-repetition: never repeat same citation more than once."""
    assert "Never repeat the same citation more than once" in SYSTEM_PROMPT


def test_system_prompt_has_paragraph_limit():
    """Answer must fit in 1-3 paragraphs."""
    assert "1-3 paragraphs" in SYSTEM_PROMPT


def test_answer_style_detailed_no_cover_every_clause():
    """Detailed style must NOT force covering every clause."""
    assert "cover every relevant clause" not in _ANSWER_STYLE_DETAILED


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
    test_system_prompt_has_no_echo_rule()
    test_system_prompt_has_anti_repetition()
    test_system_prompt_has_paragraph_limit()
    test_answer_style_detailed_no_cover_every_clause()
    all_count = len([f for f in dir() if f.startswith("test_")])
    print(f"\nAll {all_count} tests passed!")
