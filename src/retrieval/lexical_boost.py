"""Deterministic lexical-anchor boost for retrieval candidates (Build 45).

Reranking with a cross-encoder is strong but sometimes promotes near-miss
narrative chunks over the chunk that carries the exact distinctive phrase a
question is asking about (e.g. the "For Indonesian flag ship" cofferdam
footnote, or the "lubricating oil circulating tanks ... at least 500 mm"
clause). This module applies a small, deterministic score boost to any
candidate whose content contains the verbatim high-precision phrase that the
query explicitly requests.

Design rules:
- Boost ONLY when the query carries the distinctive trigger phrase. A generic
  "cofferdam" question must not boost the Indonesian-flag footnote.
- Boost ONLY chunks whose content contains the target phrase (ID or EN form).
- Weights are modest (+1.5) so genuinely-similar near-miss chunks stay ahead
  when the boost does not apply, but the verbatim-bearing chunk outranks
  plausible-but-wrong neighbours by a clear margin.
- Applied to BOTH modes after reranking (default) / retrieval (fast), in the
  same spot as domain scores.
"""

import re
from dataclasses import dataclass

from src.core.models import RetrievedChunk


@dataclass(frozen=True)
class LexicalBoostRule:
    """One (query_trigger -> content_target) boost rule."""
    name: str
    query_patterns: tuple[re.Pattern, ...]
    content_patterns: tuple[re.Pattern, ...]
    weight: float = 1.5


def _rx(*pats: str) -> tuple[re.Pattern, ...]:
    return tuple(re.compile(p, re.IGNORECASE) for p in pats)


# (name, query triggers, content targets)
_RAW_RULES: list[tuple[str, tuple[str, ...], tuple[str, ...]]] = [
    (
        "indonesian_flag_cofferdam",
        (
            r"\bindonesian\s*[- ]?flag(?:ged)?\b",
            r"\bberbendera\s+indonesia\b",
            r"\bbendera\s+indonesia\b",
        ),
        (
            r"\bindonesian\s+flag\b",
            r"\bbendera\s+indonesia\b",
        ),
    ),
    (
        "circulating_tank_shell",
        (
            r"\bcirculating\s+tanks?\b",
            r"\btangki\s+sirkulasi\b",
        ),
        (
            r"\bcirculating\s+tanks\b",
            r"\b500\s*mm\b",
        ),
    ),
    (
        "wheel_house_top_load",
        (
            r"\bwheel\s+house\s+tops?\b",
            r"\batap\s+ruang\s+kemudi\b",
        ),
        (
            r"\bwheel\s+house\s+tops\b",
        ),
    ),
    (
        "fire_door_gap",
        (
            r"\bgap\b.{0,25}\bdoor\b",
            r"\bdoor\b.{0,25}\bgap\b",
            r"\bcelah\b.{0,25}\bpintu\b",
            r"\bpintu\b.{0,25}\bcelah\b",
        ),
        (
            r"\bgap\s+under\s+the\s+door\b",
            r"\b12\s*mm\b",
        ),
    ),
    (
        "brittle_crack_thick_plates",
        (
            r"\bbrittle\s+crack\b",
            r"\bretak\s+getas\b",
            r"\bextremely\s+thick\b",
            r"\bsangat\s+tebal\b",
        ),
        (
            r"\bbrittle\s+crack\b",
            r"\bextremely\s+thick\b",
            r"\bover\s+50\s*mm\b",
            r"\b50\s*mm\b.*\b100\s*mm\b",
        ),
    ),
]

LEXICAL_BOOST_RULES: tuple[LexicalBoostRule, ...] = tuple(
    LexicalBoostRule(name=name, query_patterns=_rx(*q), content_patterns=_rx(*c))
    for name, q, c in _RAW_RULES
)


def _query_triggers(query: str) -> set[str]:
    """Return the set of boost-rule names whose query trigger is present."""
    hits: set[str] = set()
    for rule in LEXICAL_BOOST_RULES:
        if any(p.search(query) for p in rule.query_patterns):
            hits.add(rule.name)
    return hits


def apply_lexical_boosts(
    chunks: list[RetrievedChunk],
    query_id: str,
    query_en: str,
) -> list[RetrievedChunk]:
    """Boost candidate chunks whose content carries the verbatim phrase that
    the query explicitly requests.

    Deterministic. Modifies chunk.score in place and re-sorts descending.
    Returns the same list (re-sorted) for chaining.
    """
    if not chunks:
        return chunks

    search_text = f"{query_id or ''} {query_en or ''}"
    active = _query_triggers(search_text)
    if not active:
        return chunks

    for chunk in chunks:
        for rule in LEXICAL_BOOST_RULES:
            if rule.name not in active:
                continue
            if any(p.search(chunk.content) for p in rule.content_patterns):
                chunk.score += rule.weight

    chunks.sort(key=lambda c: c.score, reverse=True)
    return chunks
