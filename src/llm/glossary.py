"""Deterministic ID->EN substitution for BKI domain terms before translation.

Targets are verified against the Rules corpus so retrieval matches the
source text. Order is longest-phrase-first so compounds win over parts.
"""
import re

# (id_phrase, en_term) ordered longest/most-specific first.
GLOSSARY = (
    ("tinggi lambung timbul", "freeboard"),
    ("lambung timbul", "freeboard"),
    ("tinggi bebas", "freeboard"),
    ("sekat tubrukan", "collision bulkhead"),
    ("garis tegak haluan", "forward perpendicular"),
    ("garis tegak buritan", "aft perpendicular"),
    ("garis tegak", "perpendicular"),
    ("ceruk haluan", "forepeak"),
    ("ceruk buritan", "afterpeak"),
    ("pintu kebakaran", "fire door"),
    ("ambang palka", "hatch coaming"),
    ("bukaan palka", "hatch opening"),
    ("tutup palka", "hatch cover"),
    ("palka", "hatch"),
    ("gading besar", "web frame"),
    ("senta sisi", "stringer"),
    ("senta", "stringer"),
    ("pelat geladak", "deck plating"),
    ("pelat dek", "deck plating"),
    ("gading", "frame"),
    ("sekat", "bulkhead"),
    ("ceruk", "peak"),
)

_PATTERNS = tuple(
    (re.compile(r"\b" + re.escape(src) + r"\b", re.IGNORECASE), dst)
    for src, dst in GLOSSARY
)


def apply_glossary(query: str) -> str:
    """Replace known BKI domain phrases with corpus-verified English terms.

    Pure and deterministic. Compound phrases are applied first so that
    'tinggi bebas' -> 'freeboard' while bare 'tinggi' is left untouched
    (it is not a key) and therefore never becomes 'freeboard'.
    """
    out = query
    for pattern, dst in _PATTERNS:
        out = pattern.sub(dst, out)
    return out
