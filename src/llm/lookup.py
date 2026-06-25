"""Deterministic lookup from lookup_rules table (Fase B).

Pure-function matching layer. No LLM, no embedding, no mutation.
designed for Fase C integration into the pre-answer pipeline.
"""

import re
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LookupRule:
    """One row from the verified lookup_rules table."""
    topic: str
    parameter: str | None
    value_text: str
    value_num: float | None
    unit: str | None
    section_no: int
    paragraph_id: str | None
    page_no: int | None
    source_quote: str
    trigger_terms: tuple[str, ...]
    context_note: str | None = None


@dataclass(frozen=True)
class LookupMatch:
    """Successful match result."""
    rule: LookupRule
    matched_terms: tuple[str, ...]
    score: int


# ---------------------------------------------------------------------------
# Parameter disambiguation tokens
# ---------------------------------------------------------------------------

PARAM_TOKENS: dict[str, dict[str, list[str]]] = {
    "restricted_service_modulus_reduction": {
        "P": ["restricted ocean", "P"],
        "L": ["coasting service", "L"],
        "T": ["sheltered water", "T"],
    },
    "fire_door_closing_time": {
        "hinged": ["hinged", "engsel"],
        "sliding": ["sliding", "geser", "sorong"],
    },
}

# Topics that have multiple parameter rows — must be disambiguated via
# PARAM_TOKENS match. Single-parameter topics (null param or unique topic)
# skip this check.
_MULTI_PARAM_TOPICS: frozenset[str] = frozenset(PARAM_TOKENS.keys())

_PARAM_BONUS: int = 2


# ---------------------------------------------------------------------------
# Anchor terms (per-topic). Required for a topic to be eligible.
#
# The trigger_terms sets in lookup_rules include some generic phrases
# (e.g. "haluan", "collision bulkhead", "tinggi") that overlap across
# topics and with general narrative queries. The anchor gate enforces
# that the query carries at least ONE topic-distinctive phrase before
# trigger matching is even allowed, eliminating false positives on
# near-miss questions (e.g. "depth/L ratio" must not fire restricted
# service, "collision bulkhead position" must not fire forepeak).
#
# Anchor phrases are designed from the actual trigger_terms + golden-set
# positive queries so each anchor appears in the corresponding positive
# query AND is absent from the documented negative queries.
# ---------------------------------------------------------------------------
ANCHOR_TERMS: dict[str, tuple[str, ...]] = {
    # restricted service (Sec 5): modulus reduction percentages P/L/T.
    # Generics banned: "range of service", bare "l", bare "service".
    "restricted_service_modulus_reduction": (
        "section modulus",
        "modulus penampang",
        "reduction",
        "reduksi",
        "restricted ocean",
        "coasting service",
        "sheltered water",
    ),
    # forepeak (Sec 9): tiers of beams / stringer spacing.
    # Generics banned: "collision bulkhead", "forward", bare "haluan".
    "forepeak_stringer_spacing": (
        "tiers of beams",
        "stringer",
        "forepeak",
        "ceruk haluan",
        "beam spacing",
    ),
    # tug winch drum (Sec 27): winch drum vs towrope.
    "tug_winch_drum_diameter": (
        "winch",
        "drum",
        "towing",
        "tow line",
    ),
    # fire door closing time / rate (Sec 22).
    "fire_door_closing_time": (
        "fire door",
        "pintu kebakaran",
        "closing time",
        "waktu penutupan",
    ),
    # bulwark / guard rail minimum height (Sec 6).
    "bulwark_guardrail_min_height": (
        "bulwark",
        "guard rail",
        "guardrail",
    ),
    # ship rule length L definition (Sec 1 H.2.1).
    # Generics banned: bare "length l" / bare "panjang l".
    "ship_length_l_definition": (
        "rule length",
        "definisi panjang kapal",
        "definition of ship length",
        "panjang aturan",
        "scantling draught",
        "foreside of stem",
        "rudder post",
    ),
}
# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Lowercase, replace punctuation with spaces, collapse whitespace."""
    s = text.lower()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _term_matches(normalized_search: str, term: str) -> bool:
    """Check if a single trigger term matches the search text.

    Short tokens (≤2 chars) must match as whole words (word boundary).
    Longer tokens and multi-word phrases match as substrings.
    """
    term = _normalize(term)
    if " " not in term and len(term) <= 2:
        return bool(re.search(r"\b" + re.escape(term) + r"\b", normalized_search))
    return term in normalized_search


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_verified_rules(client) -> list[LookupRule]:
    """Load all verified rows from lookup_rules via a Supabase client.

    The client is passed in; this module never reads .env or creates its own
    connection. Only verified=True rows are returned.
    """
    resp = client.table("lookup_rules").select("*").eq("verified", True).execute()
    rules: list[LookupRule] = []

    for row in resp.data:
        topic = row.get("topic")
        source_quote = row.get("source_quote")
        section_no = row.get("section_no")
        trigger_terms = row.get("trigger_terms")

        if not topic or not isinstance(topic, str):
            raise ValueError(f"lookup_rules row {row.get('id')}: missing or invalid topic")
        if not source_quote or not isinstance(source_quote, str):
            raise ValueError(f"lookup_rules row {row.get('id')}: missing or invalid source_quote")
        if not isinstance(section_no, int):
            raise ValueError(f"lookup_rules row {row.get('id')}: section_no must be int, got {type(section_no)}")
        if not trigger_terms or not isinstance(trigger_terms, list) or len(trigger_terms) == 0:
            raise ValueError(f"lookup_rules row {row.get('id')}: trigger_terms must be a non-empty list")

        rules.append(LookupRule(
            topic=topic,
            parameter=row.get("parameter"),
            value_text=row.get("value_text", ""),
            value_num=row.get("value_num"),
            unit=row.get("unit"),
            section_no=section_no,
            paragraph_id=row.get("paragraph_id"),
            page_no=row.get("page_no"),
            source_quote=source_quote,
            trigger_terms=tuple(trigger_terms),
            context_note=row.get("context_note"),
        ))

    if not rules:
        raise RuntimeError("No verified rows found in lookup_rules")

    return rules


def match_lookup(
    query_id: str,
    query_en: str,
    rules: list[LookupRule],
    min_matches: int = 2,
) -> LookupMatch | None:
    """Match a query pair against the lookup_rules via trigger_terms.

    Combines the Indonesian and English queries into one search text.
    Normalises case/whitespace/punctuation.  Short trigger tokens (≤2 chars)
    must match as whole words; longer terms match as substrings.

    Topic-distinctive ANCHOR_TERMS gate: for topics registered in
    ANCHOR_TERMS the query MUST carry at least one anchor phrase before
    trigger matching runs. Topics not in ANCHOR_TERMS fall through to
    the legacy behaviour. Kills false-positives on near-miss narrative
    queries (e.g. "depth/L ratio" must not fire restricted_service).

    Multi-parameter topics require at least one PARAM_TOKENS disambiguation
    token to match.  Ties return None.

    Returns LookupMatch(None) if no rule meets the threshold.
    """
    if not rules:
        return None

    search_text = _normalize(f"{query_id} {query_en}")

    candidates: list[tuple[LookupRule, tuple[str, ...], int, int]] = []
    # candidate = (rule, matched_terms, total_score, param_bonus)

    for rule in rules:
        # Anchor gate: skip rules whose topic requires an anchor but the
        # query does not carry any of the topic-distinctive phrases.
        topic_anchors = ANCHOR_TERMS.get(rule.topic)
        if topic_anchors is not None:
            anchor_hit = any(
                _term_matches(search_text, anchor) for anchor in topic_anchors
            )
            if not anchor_hit:
                continue

        matched: list[str] = []
        base_score = 0
        for term in rule.trigger_terms:
            if _term_matches(search_text, term):
                matched.append(term)
                base_score += 1

        param_bonus = 0
        is_multi = rule.topic in _MULTI_PARAM_TOPICS
        if is_multi and rule.parameter:
            param_list = PARAM_TOKENS.get(rule.topic, {}).get(rule.parameter, [])
            for pt in param_list:
                if _term_matches(search_text, pt):
                    param_bonus += _PARAM_BONUS

        total = base_score + param_bonus
        if total >= min_matches:
            candidates.append((rule, tuple(matched), total, param_bonus))

    if not candidates:
        return None

    candidates.sort(key=lambda c: c[2], reverse=True)
    best = candidates[0]

    # Tie at the top -> ambiguous
    if len(candidates) > 1 and candidates[1][2] == best[2]:
        return None

    # Multi-parameter topics: require at least one disambiguation token
    if best[0].topic in _MULTI_PARAM_TOPICS and best[3] == 0:
        return None

    return LookupMatch(rule=best[0], matched_terms=best[1], score=best[2])
