import re

from src.core.config import settings
from src.core.models import Intent

# Explicit computation verbs: primary calculation signal.
# Bare interrogatives (berapa, how much, what is, apa) are NOT signals alone.
_CALC_VERBS = (
    "calculate",
    "compute",
    "determine the value of",
    "hitung",
    "menghitung",
    "hitunglah",
)

# Domain-specific composite terms that imply numeric computation.
_CALC_TERMS = (
    "section modulus",
    "moment of inertia",
    "frame spacing",
    "jarak gading",
    "modulus penampang",
    "plate thickness of",   # "of" anchors it as a specific calc target
)

# Number + engineering unit: strong calculation signal.
_NUMBER_UNIT_RE = re.compile(
    r"\d+(?:[.,]\d+)?\s*(?:mm|cm|m\b|MPa|kPa|GPa|N\b|kN|ton|kg|deg|degree)",
    re.IGNORECASE,
)


def classify(query: str, history: list[dict] | None = None) -> Intent:
    """Heuristic intent classification. Cheap and deterministic.

    Returns high-confidence calculation only when an explicit computation verb
    OR a numeric operand with engineering unit is present.  Bare interrogatives
    (berapa / how much / what is) are ignored because they appear in plain
    rules-QA questions too.

    Returns Intent with low confidence for rules_qa so the caller can invoke
    the LLM fallback for default mode.
    """
    q = (query or "").lower().strip()
    score = 0

    # Explicit verbs: strong signal (+2 each).
    for verb in _CALC_VERBS:
        if verb in q:
            score += 2

    # Domain composite terms: context-specific, less conclusive alone (+1).
    for term in _CALC_TERMS:
        if term in q:
            score += 1

    # Number + engineering unit: operand present (+2).
    if _NUMBER_UNIT_RE.search(q):
        score += 2

    if score >= 1:
        return Intent(kind="calculation", confidence="high", source="heuristic")
    return Intent(kind="rules_qa", confidence="low", source="heuristic")


def classify_with_llm(query: str, *, temperature: float) -> Intent:
    """LLM fallback for ambiguous cases. Used only in default mode.

    Always uses settings.fast_model with think=False (AGENTS.md hard rule):
    utility LLM calls must not use the reasoning model and must not enable
    thinking mode, otherwise the non-streaming response content comes back empty.
    """
    from src.llm.client import chat
    from src.llm.prompts import INTENT_SYSTEM

    messages = [
        {"role": "system", "content": INTENT_SYSTEM},
        {"role": "user", "content": query},
    ]
    out = chat(
        settings.fast_model,
        messages,
        temperature=temperature,
        think=False,
    ).strip().lower()
    if "calculation" in out:
        return Intent(kind="calculation", confidence="high", source="llm")
    return Intent(kind="rules_qa", confidence="high", source="llm")
