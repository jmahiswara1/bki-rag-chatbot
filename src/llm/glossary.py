"""Deterministic ID->EN substitution for BKI domain terms before translation.

Targets are verified against the Rules corpus so retrieval matches the
source text. Order is longest-phrase-first so compounds win over parts.
"""
import re

# (id_phrase, en_term) ordered longest/most-specific first.
GLOSSARY = (
    # Ship type terms — longest/most-specific first
    ("jenis konstruksi melintang", "transverse framing system"),
    ("jenis konstruksi memanjang", "longitudinal framing system"),
    ("konstruksi melintang", "transverse framing"),
    ("konstruksi memanjang", "longitudinal framing"),
    ("jarak antar penegar", "stiffener spacing"),
    ("pelat bukaan palka", "hatch opening plate"),
    ("pelat kulit luar", "outer shell plating"),
    ("kulit luar lambung", "hull shell"),
    ("ketebalan bersih", "net thickness"),
    ("beban yang bekerja", "acting loads"),
    ("kapal peti kemas", "container ship"),
    ("kapal kontainer", "container ship"),
    ("kapal penumpang", "passenger ship"),
    ("pembukaan palka", "hatch opening"),
    ("kapal tangki", "tanker"),
    ("kapal curah", "bulk carrier"),
    ("kapal niaga", "merchant ship"),
    ("hantaman dasar", "bottom slamming"),
    ("hantaman", "slamming"),
    ("hentaman", "slamming"),
    # Pre-existing entries
    ("tinggi lambung timbul", "freeboard"),
    ("lambung timbul", "freeboard"),
    ("pelat lambung", "shell plating"),
    ("tinggi bebas", "freeboard"),
    ("sekat tubrukan", "collision bulkhead"),
    ("baja standar", "mild steel"),
    ("modulus penampang", "section modulus"),
    ("garis tegak haluan", "forward perpendicular"),
    ("garis tegak buritan", "aft perpendicular"),
    ("pelat sisi", "side shell plating"),
    ("garis tegak", "perpendicular"),
    ("ceruk haluan", "forepeak"),
    ("ceruk buritan", "afterpeak"),
    ("pintu kebakaran", "fire door"),
    ("ambang palka", "hatch coaming"),
    ("bukaan palka", "hatch opening"),
    ("tutup palka", "hatch cover"),
    ("baja lunak", "mild steel"),
    ("gading besar", "web frame"),
    ("senta sisi", "stringer"),
    ("pelat geladak", "deck plating"),
    ("pelat dek", "deck plating"),
    ("penegar", "stiffener"),
    ("senta", "stringer"),
    ("gading", "frame"),
    # Bottom and floor construction terms (Sec 6, Sec 8)
    ("pelat alas dalam", "inner bottom plating"),
    ("pelat wrang", "floor plate"),
    ("pelat alas", "bottom shell plating"),
    ("alas ganda", "double bottom"),
    ("wrang", "floor"),
    ("sekat", "bulkhead"),
    ("penampang", "section"),
    ("engsel", "hinged"),
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
