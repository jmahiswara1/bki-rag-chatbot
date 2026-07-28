import re
from collections import defaultdict

from src.core.models import RetrievedChunk

_NUM_VALUE_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(mm|m|kN|MPa|N/mm2|%|t|kg)\b")

_SKIP_WORDS = {
    "the", "a", "an", "and", "or", "of", "for", "with", "in", "on", "to",
    "is", "are", "what", "how", "minimum", "maximum", "ships", "ship",
    "vessel", "vessels", "structures", "plate", "plating", "rules", "bki",
}


def detect_contradictions(
    candidates: list[RetrievedChunk],
    query: str,
) -> list[tuple[str, list[int]]] | None:
    """Detect if chunks from different sections mention values in the same unit.

    Returns a list of (unit, [sorted section_nos]) for each unit that appears
    in 2+ different sections, or None if no conflicts detected.
    """
    sections_with_unit: dict[str, set[int]] = defaultdict(set)
    for c in candidates:
        for m in _NUM_VALUE_RE.finditer(c.content):
            sections_with_unit[m.group(2)].add(c.section_no)
    conflicts = [
        (unit, sorted(sections))
        for unit, sections in sections_with_unit.items()
        if len(sections) >= 2
    ]
    return conflicts if conflicts else None


def _section_word_overlap(section_title: str, query: str) -> int:
    """Count non-generic words shared between section title and query."""
    title_terms = set(section_title.lower().split()) - _SKIP_WORDS
    query_terms = set(query.lower().split()) - _SKIP_WORDS
    return len(title_terms & query_terms)


def build_conflict_annotation(
    candidates: list[RetrievedChunk],
    query: str,
) -> str:
    """Build annotation telling the LLM to prefer the most relevant section.

    Returns empty string if no contradiction is detected or if only 1 section
    has numeric values in the candidates.
    """
    conflicts = detect_contradictions(candidates, query)
    if not conflicts:
        return ""

    conflicting_sections: set[int] = set()
    for _unit, sec_nos in conflicts:
        conflicting_sections.update(sec_nos)

    if len(conflicting_sections) < 2:
        return ""

    best = max(candidates, key=lambda c: _section_word_overlap(c.section_title, query))
    sections_str = ", ".join(f"Sec {s}" for s in sorted(conflicting_sections))
    return (
        "\n[CONTRADICTION ANNOTATION]\n"
        "Multiple sections mention numeric values for the same measurement"
        f" type: {sections_str}.\n"
        "These sections address different conditions (position, ship type,"
        " service).\n"
        f"PRIMARY SOURCE: Sec {best.section_no}"
        f" ({best.section_title})"
        " — most relevant to this query.\n"
        "Use the primary source values as the main answer. Mention other"
        " sections only briefly as secondary context explaining why their"
        " values differ.\n"
        "[/CONTRADICTION ANNOTATION]"
    )
