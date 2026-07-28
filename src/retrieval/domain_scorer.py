import re

from src.core.models import RetrievedChunk

# Ship type keyword → (section_no, boost)
# Generic/structural sections (1-22, 35-38) are intentionally absent — they
# apply to all ship types and should not be penalized. Only ship-type-specific
# sections receive a boost so they outrank competing generic narratives.
_SHIP_TYPE_SECTION: dict[str, tuple[int, float]] = {
    "container ship": (39, 2.0),
    "bulk carrier":   (23, 2.0),
    "ore carrier":    (23, 2.0),
    "tanker":         (24, 2.0),
    "passenger ship": (29, 2.0),
    "tug":            (27, 2.0),
    "fishing vessel": (28, 2.0),
    "dredger":        (32, 2.0),
    "barge":          (31, 2.0),
    "pontoon":        (31, 2.0),
    "supply vessel":  (34, 2.0),
    "chemical":       (25, 2.0),
    "liquefied gas":  (26, 2.0),
    "floating dock":  (33, 2.0),
}

# Canonical section titles for display.
_SHIP_TYPE_LABEL: dict[str, str] = {
    "container ship": "Sec 39 (Container Ships)",
    "bulk carrier":   "Sec 23 (Bulk Carriers)",
    "ore carrier":    "Sec 23 (Bulk Carriers)",
    "tanker":         "Sec 24 (Tankers)",
    "passenger ship": "Sec 29 (Passenger Ships)",
    "tug":            "Sec 27 (Tugs)",
    "fishing vessel": "Sec 28 (Fishing Vessels)",
    "dredger":        "Sec 32 (Dredgers)",
    "barge":          "Sec 31 (Barges & Pontoons)",
    "pontoon":        "Sec 31 (Barges & Pontoons)",
    "supply vessel":  "Sec 34 (Supply Vessels)",
    "chemical":       "Sec 25 (Chemical Carriers)",
    "liquefied gas":  "Sec 26 (Liquefied Gas Carriers)",
    "floating dock":  "Sec 33 (Floating Docks)",
}


def detect_ship_type(query: str) -> str | None:
    """Detect the ship type mentioned in the query.
    
    Returns the first matching ship type key, or None if no known ship type
    is mentioned in the query.
    """
    query_lower = query.lower()
    # Sort by length descending so longer (more specific) names like
    # "liquefied gas" or "passenger ship" take priority over "gas" or "ship".
    for ship_type in sorted(_SHIP_TYPE_SECTION, key=len, reverse=True):
        if ship_type in query_lower:
            return ship_type
    return None


def apply_domain_scores(
    chunks: list[RetrievedChunk],
    ship_type: str,
) -> list[RetrievedChunk]:
    """Boost chunks from the section that is specific to the query's ship type.
    
    Only boosts; never penalizes. Generic structural sections are left at their
    reranked score so they remain available when the general rule is the best
    answer. Ship-type-specific sections get a +boost so they outrank competing
    narratives from unrelated ship-type sections.
    
    Returns a new list re-sorted by score descending (caller should re-assign).
    """
    entry = _SHIP_TYPE_SECTION.get(ship_type)
    if entry is not None:
        target_section, boost = entry
        for chunk in chunks:
            if chunk.section_no == target_section:
                chunk.score += boost
        
    chunks.sort(key=lambda c: c.score, reverse=True)
    return chunks


def domain_boost_meta(ship_type: str) -> dict | None:
    """Return metadata about the applied boost for debug/audit."""
    entry = _SHIP_TYPE_SECTION.get(ship_type)
    if entry is None:
        return None
    target_section, boost = entry
    return {
        "ship_type": ship_type,
        "target_section": target_section,
        "boost": boost,
        "label": _SHIP_TYPE_LABEL.get(ship_type, f"Sec {target_section}"),
    }
