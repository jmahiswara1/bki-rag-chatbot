from langdetect import DetectorFactory, detect_langs

# Deterministic output across runs (HANDOFF Fase 3 req #3 fail-safe).
DetectorFactory.seed = 42

# Confidence threshold: below this we treat as 'other' and force translation.
_CONFIDENCE_THRESHOLD = 0.70


def detect_language(text: str) -> tuple[str, float]:
    """Detect query language. Returns (label, confidence).

    label in {"en", "id", "other"}.
    Fail-safe contract (Fase 3 req #3): if detection is uncertain or fails,
    the label is "other" and the caller MUST translate rather than skip.
    """
    if not text or not text.strip():
        return "other", 0.0
    try:
        results = detect_langs(text)
    except Exception:
        return "other", 0.0
    if not results:
        return "other", 0.0
    top = results[0]
    if top.lang in ("en", "id") and top.prob >= _CONFIDENCE_THRESHOLD:
        return top.lang, top.prob
    return "other", top.prob
