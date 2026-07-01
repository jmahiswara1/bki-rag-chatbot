from langdetect import DetectorFactory, detect_langs

# Deterministic output across runs (HANDOFF Fase 3 req #3 fail-safe).
DetectorFactory.seed = 42

# Confidence threshold: below this we treat as 'other' and force translation.
_CONFIDENCE_THRESHOLD = 0.70

# Word-boundary keyword markers used as a deterministic pre-check BEFORE
# langdetect. langdetect is unreliable on short single-sentence queries
# (e.g. "Apa saja komponen utama struktur alas?" was mislabeled as 'so'
# then 'other'). A marker hit is a much stronger signal than a
# probabilistic language model on a 5-10 word string.
ID_MARKERS = frozenset({
    "apa", "saja", "yang", "untuk", "dengan", "bagaimana", "kapan", "mengapa",
    "kenapa", "berapa", "adalah", "dan", "atau", "dari", "pada", "ini", "itu",
    "tidak", "akan", "harus", "tebal", "pelat", "gading", "dek", "geladak",
    "aturan", "ketentuan", "struktur", "alas", "ceruk", "penumpu", "jarak",
    "beban", "minimum",
    # Added (language-detect bugfix): common BKI-rules ID query words.
    # "definisi" / "menurut" appear in definitional ID queries and are
    # absent from EN queries, so they strengthen the ID signal when EN
    # words in book titles ("BKI Rules for Hull") would otherwise dominate
    # the marker count.
    "definisi", "menurut",
})
EN_MARKERS = frozenset({
    "the", "what", "how", "is", "are", "of", "for", "with", "when", "which",
    "thickness", "plate", "frame", "deck", "rules", "section", "minimum",
    "load", "spacing", "girder",
})


def _marker_hits(text: str, markers: frozenset) -> int:
    """Count distinct marker words present in text (word-boundary, case-insensitive)."""
    import re as _re
    n = 0
    for m in markers:
        if _re.search(rf"\b{_re.escape(m)}\b", text, flags=_re.IGNORECASE):
            n += 1
    return n


def _keyword_decide(text: str) -> "str | None":
    """Return 'id' / 'en' / None based on keyword marker counts.

    Strict inequality avoids false confidence on empty / mixed inputs.
    """
    id_hits = _marker_hits(text, ID_MARKERS)
    en_hits = _marker_hits(text, EN_MARKERS)
    if id_hits > en_hits and id_hits > 0:
        return "id"
    if en_hits > id_hits and en_hits > 0:
        return "en"
    return None


def _strip_neutral(text: str) -> str:
    """Remove content inside quotes and parentheses before marker counting.

    Quoted phrases ("Length L", "Rules for Hull") and parenthesised
    references ((HHP), (IACS UR A1.4.1.2)) are language-neutral technical
    tokens and book titles; counting their inner words as language markers
    causes false EN hits on otherwise-ID queries.
    """
    import re as _re
    return _re.sub(r'"[^"]*"|' + chr(39) + r'[^' + chr(39) + r']*' + chr(39) + r'|\([^)]*\)|\[[^\]]*\]', ' ', text)


def detect_language(text: str) -> tuple[str, float]:
    """Detect query language. Returns (label, confidence).

    label in {"en", "id", "other"}.
    Fail-safe contract (Fase 3 req #3): if detection is uncertain or fails,
    the caller MUST translate rather than skip.

    Order of decision:
    1) Keyword pre-check (deterministic, word-boundary). Strict winner -> done.
    2) langdetect with the 0.70 threshold (existing behavior).
    3) If langdetect returns a non-en/id label OR fails, default to 'id'
       only if any ID_MARKER is present; otherwise keep 'en' as the
       conservative default for BKI Rules (English source docs).
    """
    if not text or not text.strip():
        return "other", 0.0

    # Strip quoted/parenthesised content so their words do not count as
    # language markers. Applied to both the keyword pre-check and the
    # langdetect fallback so the signal is consistent.
    text_neutral = _strip_neutral(text)

    # 1) Keyword pre-check (deterministic, strongest signal for short queries).
    kw = _keyword_decide(text_neutral)
    if kw is not None:
        return kw, 1.0

    # 2) langdetect fallback.
    try:
        results = detect_langs(text_neutral)
    except Exception:
        # langdetect failed; use marker presence as last resort.
        return ("id" if _marker_hits(text_neutral, ID_MARKERS) > 0 else "en"), 0.0
    if not results:
        return ("id" if _marker_hits(text_neutral, ID_MARKERS) > 0 else "en"), 0.0
    top = results[0]
    if top.lang in ("en", "id") and top.prob >= _CONFIDENCE_THRESHOLD:
        return top.lang, top.prob
    # 3) langdetect returned something we don't trust. Prefer 'id' if any
    # ID marker is present (the user clearly is writing Indonesian in this
    # domain). Otherwise fall back to 'en' (English source docs default).
    if _marker_hits(text_neutral, ID_MARKERS) > 0:
        return "id", top.prob
    return "en", top.prob
