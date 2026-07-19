import re

from src.core.config import settings
from src.core.models import Intent

# Explicit computation imperatives (command form).
COMPUTE_IMPERATIVE = {
    "hitung", "kalkulasi", "kalkulasikan",
    "calculate", "compute",
}

# Question cues (interrogatives that signal rules_qa, not calculation).
QUESTION_CUES = {
    "how", "what", "when", "why", "which", "where",
    "define", "defined", "explain",
    "bagaimana", "apa", "apakah", "kapan", "mengapa", "kenapa", "berapa",
    "menentukan", "jelaskan", "dimana",
}

# Numeric assignment pattern: variable = number (e.g. L=100, a=0.6, n: 4)
NUM_ASSIGN = re.compile(r"[A-Za-z_]\w*\s*[=:]\s*-?\d")

# Domain-specific composite terms that imply numeric computation.
# IMPORTANT: These only trigger calculation when combined with NUM_ASSIGN.
_CALC_TERMS = (
    "section modulus",
    "moment of inertia",
    "frame spacing",
    "jarak gading",
    "modulus penampang",
    "plate thickness of",
    "threshold",
    "ambang",
    "kecepatan",
    "speed threshold",
)


def classify(query: str, history: list[dict] | None = None) -> Intent:
    """Heuristic intent classification. Cheap and deterministic.

    4-branch logic (first match wins):
    1) has_num AND (has_imper OR topical_hit) -> Intent(calculation, high, heuristic)
    2) has_imper AND NOT has_num AND NOT is_quest -> Intent(calculation, low, heuristic)
    3) is_quest AND NOT has_num AND NOT has_imper -> Intent(rules_qa, high, heuristic)
    4) else -> defer to LLM classifier (Intent(rules_qa, low, heuristic))

    Topical terms in _CALC_TERMS only trigger calculation when combined with NUM_ASSIGN.
    Word boundaries (\\b) prevent substring matches (e.g. "perhitungan" won't match "hitung").
    """
    q = (query or "").lower().strip()
    
    # Check for numeric assignment (e.g. L=100, a=0.6, n: 4)
    has_num = NUM_ASSIGN.search(q) is not None
    
    # Check for compute imperative with WORD BOUNDARIES (not substring)
    # Word boundary at the START only (not end): Indonesian interrogatives
    # commonly take a "-kah" suffix (berapakah, apakah, bagaimanakah) that
    # keeps the match inside a word-char region, so a trailing \b would
    # miss these forms and the heuristic would fall through to the LLM
    # fallback, which misroutes value-asking queries to the calc engine.
    has_imper = any(re.search(rf"\b{v}\w*", q) for v in COMPUTE_IMPERATIVE)

    # Check for question cues with WORD BOUNDARIES
    # Same boundary fix as has_imper: trailing \b dropped to handle -kah
    # suffix in Indonesian interrogatives.
    is_quest = any(re.search(rf"\b{w}\w*", q) for w in QUESTION_CUES)
    
    # Check for topical terms (only count with numeric assignment)
    has_topical = any(term in q for term in _CALC_TERMS)
    
    # Branch 1: has_num AND (has_imper OR topical hit) -> calculation (high)
    if has_num and (has_imper or has_topical):
        return Intent(kind="calculation", confidence="high", source="heuristic")
    
    # Branch 2: has_imper AND NOT has_num AND NOT is_quest -> calculation (low, ambiguous)
    if has_imper and not has_num and not is_quest:
        return Intent(kind="calculation", confidence="low", source="heuristic")
    
    # Branch 3: is_quest AND NOT has_num AND NOT has_imper -> rules_qa (high)
    if is_quest and not has_num and not has_imper:
        return Intent(kind="rules_qa", confidence="high", source="heuristic")
    
    # Branch 3b: table-targeted or value-lookup requests without compute imperatives
    has_table_cue = re.search(r"\b(?:table|tabel|chart|t\d+\.\d+)\b", q) is not None
    has_val_lookup = re.search(r"\b(?:for|untuk|of|dari|pada|dengan)\b.*\b\d+(?:[.,]\d+)?\b", q) is not None
    if has_table_cue or (has_val_lookup and not has_imper and not has_topical):
        return Intent(kind="rules_qa", confidence="high", source="heuristic")
    
    # Branch 4: defer to LLM classifier
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
