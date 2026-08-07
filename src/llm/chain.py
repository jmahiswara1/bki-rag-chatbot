import hashlib
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Iterator

from src.calc.engine import calculate
from src.calc.registry import diagnose_selection, search_formulas, select_formula
from src.core.config import settings
from src.core.db import get_client
from src.core.models import Intent, RetrievedChunk
from src.llm import lookup as _lookup
from src.llm import prompts
from src.llm.glossary import apply_glossary
from src.llm.client import chat, chat_stream
from src.llm.intent import classify, classify_with_llm
from src.llm.language import detect_language
from src.llm.modes import MODES
from src.retrieval.domain_scorer import apply_domain_scores, detect_ship_type
from src.retrieval.query import retrieve_context
from src.retrieval.table_selector import select_table_row
from src.retrieval.contradiction_detect import build_conflict_annotation


@dataclass
class ChainResult:
    answer: str
    sources: list[RetrievedChunk]
    intent: Intent
    language: str
    timings: dict[str, float] = field(default_factory=dict)
    en_query: str = ""
    expanded: list[str] = field(default_factory=list)
    rejected: bool = False
    reject_reason: str = ""
    lookup_match: object = None
    diagnostics: dict[str, object] = field(default_factory=dict)
    lookup_status: str = "none"


@dataclass
class PipelineState:
    """Hasil pre-answer pipeline (shared by chain_answer and chain_answer_stream).

    short_circuit_msg: non-empty if the call should NOT stream a real answer
        (calc stub or guardrail reject). The stream generator yields this as
        a single token and returns.
    """
    lang: str
    intent: Intent
    en_query: str
    expanded: list[str]
    candidates: list[RetrievedChunk]
    rejected: bool
    reject_reason: str
    timings: dict[str, float]
    mode_cfg: object
    short_circuit_msg: str = ""
    is_pre_answer_only: bool = False
    lookup_match: object = None
    table_evidence: str = ""  # selected table row evidence for context
    lookup_evidence: str = ""  # injected lookup fact for LLM (skip RAG)
    skip_retrieval: bool = False  # when True, skip retrieval + use lookup_evidence only
    diagnostics: dict[str, object] = field(default_factory=dict)
    lookup_status: str = "none"
    lookup_source: RetrievedChunk | None = None
    calc_evidence: str = ""  # verified calculation result handed to the LLM


@dataclass
class ChainStreamResult:
    """Final metadata yielded as ("done", payload) at end of stream."""
    answer: str
    sources: list[RetrievedChunk]
    intent: Intent
    language: str
    timings: dict[str, float]
    en_query: str = ""
    expanded: list[str] = field(default_factory=list)
    rejected: bool = False
    reject_reason: str = ""
    token_count: int = 0
    lookup_match: object = None
    diagnostics: dict[str, object] = field(default_factory=dict)
    lookup_status: str = "none"


# ---------------------------------------------------------------------------
# Query condense cache — eliminates nondeterminism from _translate_condense.
# GPU float-nondet on qwen2.5:3b-instruct (temp=0.0, seed=0) still produces
# en_query variance across runs. Caching per (version, lang, mode, query_text)
# makes retrieval fully deterministic across processes (TUI + main.py).
# ---------------------------------------------------------------------------

CONDENSE_CACHE_VERSION = 4

_SQL_CACHE_GET = (
    "SELECT en_query FROM query_condense_cache "
    "WHERE query_hash = :hash AND condense_version = :ver"
)
_SQL_CACHE_PUT = (
    "INSERT INTO query_condense_cache "
    "(query_hash, normalized_query, language, mode, condense_version, en_query) "
    "VALUES (:hash, :norm, :lang, :mode, :ver, :en_query) "
    "ON CONFLICT (query_hash) DO NOTHING"
)


def _normalize_for_cache(text: str) -> str:
    """Normalize query text for cache key: strip + collapse whitespace + casefold."""
    return re.sub(r"\s+", " ", text.strip()).casefold()


def _cache_hash(lang: str, mode: str, normalized: str) -> str:
    raw = f"{CONDENSE_CACHE_VERSION}|{lang}|{mode}|{normalized}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _condense_cache_get(query: str, lang: str, mode: str) -> str | None:
    """Return cached en_query or None on miss / Supabase error."""
    try:
        norm = _normalize_for_cache(query)
        h = _cache_hash(lang, mode, norm)
        client = get_client()
        res = client.table("query_condense_cache") \
            .select("en_query") \
            .eq("query_hash", h) \
            .eq("condense_version", CONDENSE_CACHE_VERSION) \
            .execute()
        if res.data and len(res.data) > 0:
            return res.data[0]["en_query"]
    except Exception:
        pass
    return None


def _condense_cache_put(query: str, lang: str, mode: str, en_query: str) -> None:
    """Store en_query in cache. Errors are silently ignored."""
    try:
        norm = _normalize_for_cache(query)
        h = _cache_hash(lang, mode, norm)
        client = get_client()
        client.table("query_condense_cache").upsert({
            "query_hash": h,
            "normalized_query": norm,
            "language": lang,
            "mode": mode,
            "condense_version": CONDENSE_CACHE_VERSION,
            "en_query": en_query,
        }, on_conflict="query_hash").execute()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Post-condense canonicalization — deterministic locale fix after LLM condense.
# Build 25: geladak depan → forward deck is moved OUT of pre-LLM glossary
# into this source-aware post-pass. The LLM receives pure Indonesian so it
# does not get confused by mixed ID/EN input (which was the trigger for
# bulwark → bilge keel hallucination). After the LLM produces an English
# condensed query, we scan the ORIGINAL query for the phrase "geladak depan"
# and, if found, fix up location expressions the LLM may have hallucinated
# (e.g. "on the dock", "in front of the deck") to "forward deck".
# ---------------------------------------------------------------------------

# Regex that matches common LLM location mistranslations for geladak depan.
# These are the hallmarks of the qwen2.5:3b "dock" / "in front of" fallacy.
# Each pattern matches the ENTIRE locative phrase so we can replace it with
# the canonical "on the forward deck" — not just swap the noun while keeping
# the wrong preposition.

_GELADAK_DEPAN_TRIGGER = re.compile(r"\bgeladak\s+depan\b", re.IGNORECASE)

# Preposition + "the dock" (captures: on/at/in front of/in + the dock)
_DOCK_PHRASE = re.compile(
    r"\b(?:in\s+front\s+of|on|at|in)\s+(?:the\s+)?[dw]ock\b",
    re.IGNORECASE,
)

# "in front of the deck" (deck without "forward" qualifier)
_FRONT_DECK_PHRASE = re.compile(
    r"\bin\s+front\s+of\s+(?:the\s+)?deck\b",
    re.IGNORECASE,
)

# "in front of the forward deck" — prep is correct (in front of) but
# semantically wrong vs original "di geladak depan" which means ON the deck
_FRONT_FWD_DECK = re.compile(
    r"\bin\s+front\s+of\s+(?:the\s+)?forward\s+deck\b",
    re.IGNORECASE,
)

_FORWARD_DECK = re.compile(
    r"\bforward\s+deck\b",
    re.IGNORECASE,
)


def canonicalize_condensed_query(original_query: str, en_query: str) -> str:
    """Deterministic post-condense canonicalization for geladak depan locale.

    Only activates when the original Indonesian query contains the exact
    phrase 'geladak depan'. Without this trigger the en_query is returned
    untouched — no global word replacement, no topic-noun scan.

    When triggered, replaces entire locative phrases that the LLM may have
    hallucinated (on/at/in front of the dock, in front of the deck) with
    the canonical 'on the forward deck'. Already-correct 'on the forward deck'
    or 'on forward deck' is left unchanged (idempotent).
    """
    if not _GELADAK_DEPAN_TRIGGER.search(original_query):
        return en_query

    out = en_query
    if _FRONT_FWD_DECK.search(out):
        out = _FRONT_FWD_DECK.sub("on the forward deck", out)
    elif _FRONT_DECK_PHRASE.search(out):
        out = _FRONT_DECK_PHRASE.sub("on the forward deck", out)
    elif _DOCK_PHRASE.search(out) and not _FORWARD_DECK.search(out):
        out = _DOCK_PHRASE.sub("on the forward deck", out)
    return out


# ---------------------------------------------------------------------------
# Build 41: fore/aft direction canonicalization. The 3B condense step is
# told to keep the glossary-substituted English verbatim, but sometimes it
# still swaps direction (e.g. original 'bagian buritan' -> 'at the bow').
# This deterministic post-pass fixes the direction whenever the ORIGINAL
# query pins an aft/forward location and the condensed query drifted the
# other way. Only activates on a direction-pinned trigger; never does a
# global word swap.
# ---------------------------------------------------------------------------

# Original-query triggers that pin AFT location.
_AFT_TRIGGER = re.compile(r"\bburitan\b|bagian\s+buritan|di\s+buritan", re.IGNORECASE)
# Original-query triggers that pin FORWARD location.
_FWD_TRIGGER = re.compile(r"\bhaluan\b|bagian\s+haluan|di\s+haluan|geladak\s+depan", re.IGNORECASE)

# en_query phrases that mean FORWARD (wrong when original pinned AFT).
_FWD_PHRASES = (
    re.compile(r"\bat\s+the\s+bow\b", re.IGNORECASE),
    re.compile(r"\bin\s+the\s+bow\b", re.IGNORECASE),
    re.compile(r"\bforward\b", re.IGNORECASE),
    re.compile(r"\bbow\b", re.IGNORECASE),
)
# en_query phrases that mean AFT (wrong when original pinned FORWARD).
_AFT_PHRASES = (
    re.compile(r"\bat\s+the\s+stern\b", re.IGNORECASE),
    re.compile(r"\bin\s+the\s+stern\b", re.IGNORECASE),
    re.compile(r"\bstern\b", re.IGNORECASE),
    re.compile(r"\baft\b", re.IGNORECASE),
)

# Follow-up markers are intentionally conservative. A complete new technical
# question should not inherit unrelated prior topics just because a history
# list exists; only explicit references to prior context enable condensation.
_FOLLOW_UP_QUERY = re.compile(
    r"(?:\b(?:kalau|jika|bila|yang\s+tadi|sebelumnya|tersebut|yang\s+sama|"
    r"bagaimana\s+dengan|bagaimana\s+kalau|what\s+about|how\s+about|"
    r"the\s+previous|the\s+same|above|also\s+for)\b|"
    r"\b(?:ini|itu)\b\s*(?:berlaku|juga|sama)|"
    r"^(?:dan|lalu|kemudian)\b)",
    re.IGNORECASE,
)


def query_needs_history(query: str, history: list[dict] | None) -> bool:
    """Return whether *query* is an explicit follow-up needing history.

    Standalone technical questions are deliberately isolated from previous
    turns. This prevents a small condense model from copying an earlier
    question into ``en_query``. Short continuation-style queries and explicit
    references such as ``L=150`` or ``bagaimana dengan tanker`` still use
    history.
    """
    if not history:
        return False

    text = (query or "").strip()
    if not text:
        return True

    if _FOLLOW_UP_QUERY.search(text):
        return True

    # A bare variable/value request is normally a continuation of the prior
    # turn, not a new document question.
    if re.fullmatch(
        r"(?:[A-Za-z][A-Za-z0-9_ ]{0,20}\s*[=:]\s*[-+]?\d+(?:[.,]\d+)?\s*(?:m|mm|kN|MPa|%)?)",
        text,
        re.IGNORECASE,
    ):
        return True

    # A sufficiently complete question is standalone unless it explicitly
    # contains one of the follow-up references above.
    return False


def canonicalize_direction_query(original_query: str, en_query: str) -> str:
    """Deterministic post-condense canonicalization for fore/aft direction.

    - If the ORIGINAL query pins an AFT location and the condensed query
      drifted to a FORWARD phrase, replace the FORWARD phrase with 'aft'.
    - If the ORIGINAL query pins a FORWARD location and the condensed query
      drifted to an AFT phrase, replace it with 'forward'.
    - Otherwise return en_query untouched.
    """
    pinned_aft = _AFT_TRIGGER.search(original_query) is not None
    pinned_fwd = _FWD_TRIGGER.search(original_query) is not None

    out = en_query
    if pinned_aft:
        for pat in _FWD_PHRASES:
            if pat.search(out):
                out = pat.sub("aft", out)
                break
    if pinned_fwd:
        for pat in _AFT_PHRASES:
            if pat.search(out):
                out = pat.sub("forward", out)
                break
    return out


_FIDELITY_STOP_WORDS = frozenset(
    "a an and are as at be by for from how in is it of on or the to what when "
    "where which who why with yang dan atau untuk pada dengan dalam dari apa "
    "berapa bagaimana apakah di ke yang ini itu kapal menurut aturan harus "
    "does do not is not was were shall should can may the".split()
)
_TECHNICAL_FIDELITY_HINTS = frozenset(
    "aluminium alloy emergency release system corrosion addition manholes "
    "cargo tank dry spaces bulwark plating superstructure bulkhead thickness "
    "towing winch mooring dredger tanker structure hull kapal pelat sekat "
    "tangki lambung baja paduan".split()
)


def _fidelity_tokens(text: str) -> set[str]:
    """Return meaningful tokens used by the conservative condense validator."""
    normalized = re.sub(r"[^\w.=/%+-]", " ", (text or "").casefold())
    tokens = set(re.findall(r"[a-z\d][a-z\d._/%+-]*", normalized))
    return {
        token for token in tokens
        if token not in _FIDELITY_STOP_WORDS
        and (len(token) >= 4 or any(ch.isdigit() for ch in token))
    }


def validate_en_query_fidelity(original_query: str, en_query: str) -> tuple[bool, str]:
    """Check that a condensed query still represents the current question.

    This is deliberately a conservative lexical guard, not a second semantic
    model call. The glossary creates a bilingual bridge for Indonesian terms;
    the validator then requires meaningful subject/parameter overlap. A query
    from an earlier turn (for example ``emergency release``) has no overlap
    with a new aluminium/manhole question and is rejected.
    """
    glossary_query = apply_glossary(original_query)
    original = _fidelity_tokens(glossary_query)
    condensed = _fidelity_tokens(en_query)
    if not condensed:
        return False, "empty_condensed_query"
    if not original:
        return True, "no_fidelity_tokens"

    # Very generic utility text has no reliable subject token to compare. Do
    # not reject it solely because an English paraphrase shares no literal
    # token; technical Indonesian queries normally pass through the glossary
    # and therefore are validated below.
    if (
        glossary_query.casefold() == (original_query or "").casefold()
        and not any(ch.isdigit() for ch in original_query)
        and not original & _TECHNICAL_FIDELITY_HINTS
    ):
        return True, "generic_query"

    required_numbers = {
        token for token in original if any(ch.isdigit() for ch in token)
    }
    missing_numbers = required_numbers - condensed
    if missing_numbers:
        return False, f"missing_parameters:{','.join(sorted(missing_numbers))}"

    overlap = original & condensed
    # A meaningful overlap is required for technical queries. One shared
    # subject token is enough here because glossary/canonicalization can split
    # a bilingual compound differently (``geladak depan`` -> ``forward deck``).
    # The zero-overlap case is the important failure mode: it catches a
    # condensed question copied from an unrelated previous turn.
    minimum_overlap = 1
    if len(overlap) < minimum_overlap:
        return False, f"topic_drift:overlap={','.join(sorted(overlap)) or 'none'}"
    return True, "ok"


def _build_en_fallback(query: str, history: list[dict] | None) -> str:
    """Deterministic English fallback when the 3B condense model fails to
    translate a follow-up question (e.g. 'Kalau L=150 m ...').

    Builds a compact English query from:
      - ship_type + numeric facts extracted from history, and
      - glossary-stabilized terms of the current query.
    This is not a full translation, but it carries the discriminating EN
    tokens (ship type, structural term, numeric parameters) needed by FTS
    and the cross-lingual vector branch.
    """
    parts: list[str] = []

    facts = _extract_history_facts(history, query)
    if facts:
        for fact in facts.split(", "):
            key, _, value = fact.partition("=")
            if key == "ship_type" and value:
                parts.append(value)
            elif key and value and any(ch.isdigit() for ch in value):
                parts.append(f"{key}={value}")

    # Prefer the FIRST user turn for structural terms: it is the full
    # self-contained question that introduced the topic (e.g. bulk carrier
    # plate floor spacing). Glossary-stabilize it to extract EN terms.
    subject_source = query
    if history:
        first_user = next(
            (h.get("content", "") for h in history if h.get("role") == "user"),
            "",
        )
        if first_user:
            subject_source = first_user + " " + query

    glossary = apply_glossary(subject_source)
    # Keep meaningful EN tokens (length>=4) from the glossary-stabilized text,
    # but drop pure function words and common Indonesian remains.
    _drop = {
        "kalau", "apakah", "kemungkinan", "berubah", "dengan", "untuk",
        "pada", "yang", "antara", "bagaimanakah", "bagaimana", "kapal",
        "pelatnya", "panjang", "jarak", "ini", "itu", "harus", "akan",
        "dan", "atau", "dari", "menggunakan", "baja", "standar",
        "sistem", "rangka", "maksimum", "saja", "yang",
        "berapakah", "berapa", "adakah", "apakah", "kapalnya", "wrangnya",
        "pelat", "perubahan", "jarak", "antar", "adanya", "perlu",
        "seri", "diizinkan", "digunakan", "struktur", "lambung", "saja",
        "aturan", "ketentuan", "menurut", "kepada", "maka", "tersebut",
        "dengan", "untuk", "pada", "dan", "atau", "dari", "yang",
    }
    tokens = [t for t in re.findall(r"[A-Za-z]{4,}", glossary)
              if t.casefold() not in _drop]
    seen: set[str] = set()
    for t in tokens:
        t = t.casefold()
        if t in seen:
            continue
        seen.add(t)
        parts.append(t)

    if not parts:
        return glossary
    return " ".join(parts)


def _validated_condensed_query(
    original_query: str,
    candidate: str,
    *,
    validate: bool = True,
) -> tuple[str, str]:
    """Canonicalize a candidate and fall back when fidelity validation fails."""
    candidate = canonicalize_condensed_query(original_query, candidate)
    candidate = canonicalize_direction_query(original_query, candidate)
    if not validate:
        return candidate, "validation_skipped"

    # Direct utility callers without a language/mode context retain the
    # existing behavior; the pipeline supplies both and enables the guard.
    if not original_query.strip() or not candidate.strip():
        return candidate, "validation_skipped"

    valid, reason = validate_en_query_fidelity(original_query, candidate)
    if valid:
        return candidate, reason

    fallback = apply_glossary(original_query)
    fallback = canonicalize_condensed_query(original_query, fallback)
    fallback = canonicalize_direction_query(original_query, fallback)
    return fallback, f"fallback:{reason}"


def _pre_answer_pipeline(
    query: str,
    history: list[dict] | None,
    mode: str,
) -> PipelineState:
    """Run the Fase 3 pre-answer pipeline synchronously.

    Mirrors chain_answer's pre-answer steps exactly so the two functions
    stay behavior-equivalent for everything except the final answer emission.
    """
    timings: dict[str, float] = {}
    history = history or []
    mode_cfg = MODES[mode]
    diagnostics: dict[str, object] = {
        "original_query": query,
        "history_used": False,
        "en_query": "",
        "condense_valid": True,
        "condense_reason": "not_run",
        "lookup_topic": None,
        "retrieval_query": None,
        "retrieval_fallback": False,
        "lookup_status": "none",
        "crosscheck_reason": "not_run",
    }
    lookup_source: RetrievedChunk | None = None
    lookup_status = "none"

    # 1. detect language
    t = time.time()
    lang, _lang_conf = detect_language(query)
    timings["detect_lang"] = time.time() - t

    # 2. intent (+LLM fallback for default mode)
    t = time.time()
    intent = classify(query, history)
    if intent.confidence == "low" and mode == "default":
        intent = classify_with_llm(query, temperature=mode_cfg.temperature)
    timings["intent"] = time.time() - t

    # 2.5. OOD pre-check must run before calculation short-circuit too.
    # An out-of-scope query can still be phrased as a calculation request.
    ood_reject_msg = _check_ood_query(query, lang)
    if ood_reject_msg:
        timings.setdefault("answer", 0.0)
        return PipelineState(
            lang=lang,
            intent=intent,
            en_query="",
            expanded=[],
            candidates=[],
            rejected=True,
            reject_reason="ood_keyword",
            timings=timings,
            mode_cfg=mode_cfg,
            short_circuit_msg=ood_reject_msg,
            is_pre_answer_only=True,
        )

    # 3. calc short-circuit
    if intent.kind == "calculation":
        t = time.time()
        
        # Use the ORIGINAL query (in the user's language) for formula matching.
        # SYNONYM_MAP in registry.py maps Indonesian terms ("penumpu tengah"
        # -> "centre girder", "tebal" -> "thickness", etc.) to English
        # equivalents used in formula titles. Translating first strips those
        # terms and weakens the rank (e.g. ID query "Hitung tebal web
        # penumpu tengah dengan L=100" scores 99 vs 57; translated to EN
        # drops to 39 vs 27, failing the 1.5x margin). The original query
        # is also passed to calculate() for variable parsing (preserves
        # "L=100", "a=0,6" formats).
        candidate_formulas = search_formulas(query)
        
        # Determine message based on confidence and candidates
        if intent.confidence == "low":
            # Ambiguous intent: ALWAYS show clarification list, even if 1 formula
            if not candidate_formulas:
                message = (
                    "I couldn't find a matching formula for your calculation request. "
                    "Please try rephrasing your question or check if the formula is available in the database."
                )
            else:
                formula_list = "\n".join([
                    f"  - {f.title} (Sec {f.section_no})"
                    for f in candidate_formulas
                ])
                message = (
                    f"I found {len(candidate_formulas)} matching formula(s):\n{formula_list}\n\n"
                    "Please specify which formula you'd like to use by providing its section number or title."
                )
        else:
            # High confidence: use rank_formulas for ranking and auto-select
            if not candidate_formulas:
                message = (
                    "I couldn't find a matching formula for your calculation request. "
                    "Please try rephrasing your question or check if the formula is available in the database."
                )
            else:
                # Auto-select using VARIABLE COMPLETENESS as the primary
                # disambiguator. The old 1.5x score-margin gate failed on
                # exact ties (3 of 4 calc failures were exact score ties).
                # select_formula filters by required-var satisfaction first,
                # then picks the best by text-score + coverage tiebreak.
                best, clarification_list = select_formula(query, candidate_formulas)
                if best is not None:
                    calc_result = calculate(query, best)
                    if calc_result.success:
                        # A successful calculation still reaches the LLM so the
                        # answer is phrased naturally; the NUMBER is fixed and
                        # verified by sympy, so the LLM must not change it.
                        calc_evidence = calc_result.message
                        timings["calc"] = time.time() - t
                        diagnostics["calc_formula"] = best.code
                        diagnostics["calc_result"] = calc_result.result
                        return PipelineState(
                            lang=lang,
                            intent=intent,
                            en_query="",
                            expanded=[],
                            candidates=[],
                            rejected=False,
                            reject_reason="",
                            timings=timings,
                            mode_cfg=mode_cfg,
                            short_circuit_msg="",
                            is_pre_answer_only=False,
                            calc_evidence=calc_evidence,
                            diagnostics=diagnostics,
                        )
                    message = calc_result.message
                else:
                    formula_list = "\n".join([
                        f"  - {f.title} (Sec {f.section_no})"
                        for f, _score in clarification_list
                    ])
                    diagnostic = diagnose_selection(clarification_list, query, lang)
                    if diagnostic:
                        message = (
                            f"I found {len(clarification_list)} matching formula(s):\n{formula_list}\n\n"
                            f"{diagnostic}"
                        )
                    else:
                        message = (
                            f"I found {len(clarification_list)} matching formula(s):\n{formula_list}\n\n"
                            "Please specify which formula you'd like to use by providing its section number or title."
                        )
        
        timings["calc"] = time.time() - t
        return PipelineState(
            lang=lang,
            intent=intent,
            en_query="",
            expanded=[],
            candidates=[],
            rejected=False,
            reject_reason="",
            timings=timings,
            mode_cfg=mode_cfg,
            short_circuit_msg=message,
            is_pre_answer_only=True,
        )

    # 4. translate + condense
    t = time.time()
    needs_history = query_needs_history(query, history)
    condense_history = history if needs_history else []
    diagnostics["history_used"] = needs_history
    # T7-DEF3 (P4): Unified bypass for EN queries.
    # If the user explicitly asks in English AND there is no history (stand-alone),
    # bypass _translate_condense entirely. This prevents qwen2.5 from mistranslating
    # the EN query into ID. This applies uniformly to BOTH default and fast modes.
    if lang == "en" and not needs_history:
        en_query = query
    else:
        en_query = _translate_condense(
            query,
            condense_history,
            temperature=mode_cfg.temperature,
            mode=mode,
            lang=lang,
        )
    # Validate at the pipeline boundary as well as inside the helper. This
    # protects callers/tests that replace the condense helper and, more
    # importantly, guarantees retrieval and lookup never consume a drifted
    # query from an earlier turn.
    en_query, _condense_reason = _validated_condensed_query(query, en_query)
    # Fase 8/44: the 3B condense model sometimes returns the query still in
    # Indonesian (especially short follow-ups like 'Kalau L=150 m ...'). The
    # fidelity check passes because lexical tokens overlap, but the FTS/vector
    # branch needs English. Detect the resulting language; if it is still ID
    # for an originally-ID query, replace it with a deterministic EN fallback.
    if lang == "id":
        try:
            from src.llm.language import detect_language as _dl
            if _dl(en_query)[0] == "id":
                # Use condense_history (already filtered for standalone queries),
                # never the raw history, so a prior topic cannot leak in.
                fallback = _build_en_fallback(query, condense_history)
                diagnostics["condense_reason"] = f"lang_fallback:{_condense_reason}"
                en_query = fallback
        except Exception:
            pass
    diagnostics["en_query"] = en_query
    diagnostics["condense_reason"] = _condense_reason
    diagnostics["condense_valid"] = not _condense_reason.startswith("fallback:")
    # Keep one explicit, validated query for every downstream retrieval
    # consumer. No raw LLM condense result may reach FTS, reranking helpers,
    # table selection, or contradiction detection.
    retrieval_query = en_query
    timings["translate"] = time.time() - t

    # 4.5. lookup-first (before retrieval — saves evidence for LLM context)
    t = time.time()
    lookup_match = None
    lookup_evidence = ""
    skip_retrieval = False
    if mode == "default" and intent.kind == "rules_qa":
        try:
            rules = _get_lookup_rules()
            if rules:
                lookup_match = _lookup.match_lookup(
                    query_id=query, query_en=en_query, rules=rules,
                )
            if lookup_match is not None:
                precise, precision_reason = _lookup.validate_lookup_precision(
                    query_id=query,
                    query_en=en_query,
                    match=lookup_match,
                )
                diagnostics["lookup_precision"] = precision_reason
                if not precise:
                    lookup_match = None
            if lookup_match is not None:
                lookup_evidence = _format_lookup_evidence(lookup_match, lang)
                lookup_status = "candidate"
                diagnostics["lookup_topic"] = lookup_match.rule.topic
        except Exception as exc:
            print(
                f"  [chain] WARNING: lookup match failed, falling back to RAG "
                f"({type(exc).__name__}: {exc})",
                file=sys.stderr,
                flush=True,
            )
    timings["lookup"] = time.time() - t

    # 5. multi-query expansion (gated)
    expanded: list[str] = []
    if mode == "default" and settings.enable_multi_query and not skip_retrieval:
        t = time.time()
        raw = _expand(en_query, temperature=mode_cfg.temperature)
        expanded = _parse_multi_query(raw, n=settings.expand_n_queries)
        timings["expand"] = time.time() - t

    # 6. retrieve
    candidates: list[RetrievedChunk] = []
    if skip_retrieval:
        t = time.time()
        timings["retrieve"] = time.time() - t
        timings["domain_score"] = 0.0
        timings["contradiction"] = 0.0
        table_evidence = ""
        # Lookup match: surface the verified source as a RetrievedChunk so
        # the CLI Sources panel and /source command show where the answer
        # came from, even though retrieval is skipped.
        if lookup_match is not None:
            rule = lookup_match.rule
            desc = _LOOKUP_DESC.get(rule.topic, {}).get(rule.parameter)
            if desc is not None:
                # desc = (id_text, en_text); _LOOKUP_DESC may be referenced
                # before its module-level definition in some call paths, so
                # fall back to the topic name if unavailable.
                title = desc[0] if lang == "id" else desc[1]
            else:
                title = rule.topic
            candidates = [
                RetrievedChunk(
                    section_no=rule.section_no,
                    section_title=title,
                    paragraph_id=rule.paragraph_id,
                    content_type="lookup",
                    table_no=None,
                    figure_no=None,
                    page_start=rule.page_no or 0,
                    page_end=rule.page_no or 0,
                    content=rule.localized_text(lang),
                    score=float(lookup_match.score),
                )
            ]
            lookup_source = candidates[0]
    else:
        t = time.time()
        diagnostics["retrieval_query"] = retrieval_query
        diagnostics["retrieval_fallback"] = _condense_reason.startswith("fallback:")
        # Build 41: the vector branch embeds a glossary-stabilized query so
        # Indonesian domain terms ('geladak bangunan atas' -> 'superstructure
        # deck', 'bagian buritan' -> 'aft part') match the EN chunk text.
        # Raw ID queries retrieve Sec 29 poorly (cross-lingual gap); using
        # the raw query directly made it WORSE for recall. The glossary
        # substitution preserves direction (aft/forward) deterministically.
        # The FTS branch still uses en_query as the English term anchor.
        vector_q = apply_glossary(query) if lang == "id" else None
        candidates = retrieve_context(
            query_text=query,
            mode=mode,
            fts_query=retrieval_query,
            en_query=retrieval_query,
            multi_queries=expanded if expanded else None,
            vector_query=vector_q,
        )
        timings["retrieve"] = time.time() - t

        if lookup_match is not None:
            rule_section = lookup_match.rule.section_no
            crosscheck_candidates = list(candidates)
            same_section = any(c.section_no == rule_section for c in crosscheck_candidates)
            if same_section:
                lookup_status = "confirmed"
                diagnostics["crosscheck_reason"] = "matching_section"
                crosscheck_note = "[DOCUMENT CROSS-CHECK — CONSISTENT]\n"
            else:
                lookup_status = "supported" if not crosscheck_candidates else "conflict"
                diagnostics["crosscheck_reason"] = (
                    "no_retrieval_hits" if not crosscheck_candidates
                    else "no_matching_section"
                )
                crosscheck_note = (
                    "[LOOKUP VERIFIED — NO CROSS-CHECK HIT]\n"
                    if not crosscheck_candidates
                    else "[DOCUMENT CROSS-CHECK — CONFLICT]\n"
                )
            lookup_evidence += (
                f"\n{crosscheck_note}"
                "The lookup fact is a candidate evidence source. "
                "Use it only when the current question context agrees; "
                "do not silently override conflicting document context.\n"
            )
            rule = lookup_match.rule
            lookup_source = RetrievedChunk(
                section_no=rule.section_no,
                section_title=rule.topic,
                paragraph_id=rule.paragraph_id,
                content_type="lookup",
                table_no=None,
                figure_no=None,
                page_start=rule.page_no or 0,
                page_end=rule.page_no or 0,
                content=rule.localized_text(lang),
                score=float(lookup_match.score),
            )
            candidates = [lookup_source, *candidates]
            diagnostics["lookup_status"] = lookup_status

        # 6.1. domain-aware scoring
        t = time.time()
        if retrieval_query and mode == "default" and candidates:
            ship_type = detect_ship_type(retrieval_query)
            if ship_type:
                candidates = apply_domain_scores(candidates, ship_type)
        timings["domain_score"] = time.time() - t

        # 6.5. deterministic table-row selection
        table_evidence = ""
        if retrieval_query and candidates:
            table_candidates = [(i, c) for i, c in enumerate(candidates) if c.content_type == "table"]
            safe_selections = []
            for rank, c in table_candidates:
                tag = f"[Sec {c.section_no}"
                if c.paragraph_id:
                    tag += f" | {c.paragraph_id}"
                if c.table_no:
                    tag += f" | Table {c.table_no}"
                tag += f" | p.{c.page_start}]" if c.page_start == c.page_end else f" | pp.{c.page_start}-{c.page_end}]"
                sel = select_table_row(c.content, retrieval_query, "en", table_ref=tag)
                if sel.selected:
                    safe_selections.append((rank, sel))
            if len(safe_selections) == 1:
                rank, sel = safe_selections[0]
                table_evidence = (
                    f"\n[TABLE ROW SELECTED from {sel.table_ref}]\n"
                    f"Condition: {sel.reason}\n"
                    f"Row: {sel.row_text}\n"
                    f"Value: {sel.value_text}\n"
                )
                candidates[rank].score += 3.0
                candidates.sort(key=lambda c: c.score, reverse=True)

        # 6.6. contradiction detection
        t = time.time()
        if retrieval_query and mode == "default" and len(candidates) > 1:
            anno = build_conflict_annotation(candidates, retrieval_query)
            if anno:
                table_evidence = (table_evidence or "") + anno
        timings["contradiction"] = time.time() - t

    # 7. guardrail (default only)
    rejected = False
    reject_reason = ""
    short_circuit_msg = ""
    is_pre_answer_only = False
    if mode == "default" and candidates and not skip_retrieval:
        candidates, rejected, reject_reason = _apply_guardrail(candidates)
    if not candidates and not skip_retrieval:
        if lang == "id":
            short_circuit_msg = (
                "Konteks yang tersedia tidak cukup untuk menjawab pertanyaan ini "
                "berdasarkan BKI Rules for Hull 2026."
            )
        else:
            short_circuit_msg = (
                "The available context is insufficient to answer this question "
                "based on the BKI Rules for Hull 2026."
            )
        is_pre_answer_only = True
        timings.setdefault("answer", 0.0)

    return PipelineState(
        lang=lang,
        intent=intent,
        en_query=en_query,
        expanded=expanded,
        candidates=candidates,
        rejected=rejected,
        reject_reason=reject_reason,
        timings=timings,
        mode_cfg=mode_cfg,
        short_circuit_msg=short_circuit_msg,
        is_pre_answer_only=is_pre_answer_only,
        table_evidence=table_evidence,
        lookup_match=lookup_match,
        lookup_evidence=lookup_evidence,
        skip_retrieval=skip_retrieval,
        diagnostics=diagnostics,
        lookup_status=lookup_status,
        lookup_source=lookup_source,
    )


def chain_answer(
    query: str,
    history: list[dict] | None = None,
    mode: str = "default",
) -> ChainResult:
    """Non-streaming end-to-end Fase 3 pipeline. See HANDOFF Section 8.

    Behavior is IDENTICAL to the pre-refactor version. Refactored to share
    the pre-answer pipeline with chain_answer_stream.
    """
    state = _pre_answer_pipeline(query, history, mode)

    if state.is_pre_answer_only:
        return ChainResult(
            answer=state.short_circuit_msg,
            sources=[],
            intent=state.intent,
            language=state.lang,
            timings=state.timings,
            rejected=state.rejected,
            reject_reason=state.reject_reason,
            en_query=state.en_query,
            expanded=state.expanded,
            lookup_match=state.lookup_match,
            diagnostics=state.diagnostics,
            lookup_status=state.lookup_status,
        )

    t = time.time()
    answer = _answer(
        query,
        state.candidates,
        state.lang,
        model=state.mode_cfg.model,
        temperature=state.mode_cfg.temperature,
        think=False,
        answer_style=state.mode_cfg.answer_style,
        table_evidence=state.table_evidence,
        lookup_evidence=state.lookup_evidence,
        calc_evidence=state.calc_evidence,
    )
    return ChainResult(
        answer=answer,
        sources=state.candidates,
        intent=state.intent,
        language=state.lang,
        timings=state.timings,
        en_query=state.en_query,
        expanded=state.expanded,
        rejected=state.rejected,
        reject_reason=state.reject_reason,
        lookup_match=state.lookup_match,
        diagnostics=state.diagnostics,
        lookup_status=state.lookup_status,
    )


def chain_answer_stream(
    query: str,
    mode: str = "default",
    history: list[dict] | None = None,
) -> Iterator[tuple[str, object]]:
    """Streaming end-to-end Fase 3 pipeline.

    Yields tuples (kind, payload) where kind in {"status", "token", "done"}:
      - ("status", str): pipeline event for CLI spinner / progress
      - ("token",  str): one token of the answer (or the full pre-answer msg)
      - ("done",   ChainStreamResult): final metadata; yielded last.

    Pre-answer short-circuits (calc stub, guardrail reject) yield exactly one
    ("token", short_circuit_msg) followed by ("done", ...). The stream then
    ends; the caller never has to read a second token.

    Real answer path streams via chat_stream with think=False, num_ctx=8192.
    If the model emits no tokens (defense-in-depth safeguard, should be rare
    with the locked qwen2.5:3b-instruct answer model), falls back to ONE
    non-streaming chat call to surface an answer; the fallback is yielded as
    a single ("token", ...) before ("done", ...).
    """
    t_total = time.time()
    state = _pre_answer_pipeline(query, history, mode)

    if state.is_pre_answer_only:
        yield ("status", "pre_answer")
        yield ("token", state.short_circuit_msg)
        state.timings["total"] = time.time() - t_total
        yield ("done", ChainStreamResult(
            answer=state.short_circuit_msg,
            sources=[],
            intent=state.intent,
            language=state.lang,
            timings=state.timings,
            en_query=state.en_query,
            expanded=state.expanded,
            rejected=state.rejected,
            reject_reason=state.reject_reason,
            token_count=0,
            lookup_match=state.lookup_match,
            diagnostics=state.diagnostics,
            lookup_status=state.lookup_status,
        ))
        return

    yield ("status", "answer_streaming")
    messages = _build_answer_messages(query, state.candidates, state.lang,
                                       answer_style=state.mode_cfg.answer_style,
                                       table_evidence=state.table_evidence,
                                       lookup_evidence=state.lookup_evidence,
                                       calc_evidence=state.calc_evidence)
    accumulated: list[str] = []
    t_stream = time.time()
    try:
        for token in chat_stream(
            state.mode_cfg.model,
            messages,
            state.mode_cfg.temperature,
            num_ctx=settings.num_ctx,
            think=False,
        ):
            if token:
                accumulated.append(token)
                yield ("token", token)
    except Exception as exc:
        print(
            f"  [chain._stream_from_state] ERROR: stream exception "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
            flush=True,
        )
        yield ("status", f"stream_error:{type(exc).__name__}")
    state.timings["stream"] = time.time() - t_stream

    final_text = "".join(accumulated)
    if not final_text.strip():
        print(
            f"  [chain._stream_from_state] WARNING: stream produced 0 tokens, "
            f"falling back to 1x non-stream chat",
            file=sys.stderr,
            flush=True,
        )
        final_text = _answer_fallback_non_stream(query, state.candidates, state.lang, state.mode_cfg, answer_style=state.mode_cfg.answer_style, lookup_evidence=state.lookup_evidence, calc_evidence=state.calc_evidence)
        if final_text and final_text.strip():
            fallback_used = True
            yield ("token", final_text)
    state.timings["total"] = time.time() - t_total

    yield ("done", ChainStreamResult(
        answer=final_text,
        sources=state.candidates,
        intent=state.intent,
        language=state.lang,
        timings=state.timings,
        en_query=state.en_query,
        expanded=state.expanded,
        rejected=state.rejected,
        reject_reason=state.reject_reason,
        token_count=len(accumulated),
        lookup_match=state.lookup_match,
        diagnostics=state.diagnostics,
        lookup_status=state.lookup_status,
    ))


def _stream_from_state(
    query: str,
    state: PipelineState,
) -> Iterator[tuple[str, object]]:
    """Run ONLY the streaming answer step from a pre-computed PipelineState.

    Used by tests to reuse retrieval/translate/guardrail across multiple
    stream runs of the same query (avoids re-paying the heavy pipeline cost
    just to test streaming reliability). NOT for production callers.
    """
    t_total = time.time()
    if state.is_pre_answer_only:
        yield ("status", "pre_answer")
        yield ("token", state.short_circuit_msg)
        state.timings["total"] = time.time() - t_total
        yield ("done", ChainStreamResult(
            answer=state.short_circuit_msg,
            sources=[],
            intent=state.intent,
            language=state.lang,
            timings=state.timings,
            en_query=state.en_query,
            expanded=state.expanded,
            rejected=state.rejected,
            reject_reason=state.reject_reason,
            token_count=0,
            lookup_match=state.lookup_match,
            diagnostics=state.diagnostics,
        ))
        return

    yield ("status", "answer_streaming")
    messages = _build_answer_messages(query, state.candidates, state.lang,
                                       answer_style=state.mode_cfg.answer_style,
                                       table_evidence=state.table_evidence,
                                       lookup_evidence=state.lookup_evidence,
                                       calc_evidence=state.calc_evidence)
    accumulated: list[str] = []
    t_stream = time.time()
    try:
        for token in chat_stream(
            state.mode_cfg.model,
            messages,
            state.mode_cfg.temperature,
            num_ctx=settings.num_ctx,
            think=False,
        ):
            if token:
                accumulated.append(token)
                yield ("token", token)
    except Exception as exc:
        print(
            f"  [chain.chain_answer_stream] ERROR: stream exception "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
            flush=True,
        )
        yield ("status", f"stream_error:{type(exc).__name__}")
    state.timings["stream"] = time.time() - t_stream

    final_text = "".join(accumulated)
    if not final_text.strip():
        print(
            f"  [chain.chain_answer_stream] WARNING: stream produced 0 tokens, "
            f"falling back to 1x non-stream chat (model={state.mode_cfg.model})",
            file=sys.stderr,
            flush=True,
        )
        final_text = _answer_fallback_non_stream(query, state.candidates, state.lang, state.mode_cfg, answer_style=state.mode_cfg.answer_style, lookup_evidence=state.lookup_evidence, calc_evidence=state.calc_evidence)
        if final_text and final_text.strip():
            yield ("token", final_text)
    state.timings["total"] = time.time() - t_total
    yield ("done", ChainStreamResult(
        answer=final_text,
        sources=state.candidates,
        intent=state.intent,
        language=state.lang,
        timings=state.timings,
        en_query=state.en_query,
        expanded=state.expanded,
        rejected=state.rejected,
        reject_reason=state.reject_reason,
        token_count=len(accumulated),
        lookup_match=state.lookup_match,
        diagnostics=state.diagnostics,
    ))


# ---------------------------------------------------------------------------
# Private utility helpers (unchanged from previous version, kept for reuse).
# ---------------------------------------------------------------------------

# --- lookup-first helpers (Fase C) ---

_lookup_cache: list[_lookup.LookupRule] | None = None


def _get_lookup_rules() -> list[_lookup.LookupRule]:
    """Lazy-load verified lookup_rules from Supabase, cached for session lifetime."""
    global _lookup_cache
    if _lookup_cache is not None:
        return _lookup_cache
    try:
        from src.core.db import get_client
        _lookup_cache = _lookup.load_verified_rules(get_client())
    except Exception as exc:
        print(
            f"  [chain] WARNING: failed to load lookup_rules, "
            f"lookup will be disabled ({type(exc).__name__}: {exc})",
            file=sys.stderr,
            flush=True,
        )
        _lookup_cache = []
    return _lookup_cache


# Natural-language topic descriptors per (topic, parameter) for answer formatting.
_LOOKUP_DESC: dict[str, dict[str | None, tuple[str, str]]] = {
    "restricted_service_modulus_reduction": {
        "P": (
            "pengurangan minimum section modulus untuk Restricted Ocean Service (P) sebesar",
            "the minimum section modulus reduction for Restricted Ocean Service (P) is",
        ),
        "L": (
            "pengurangan minimum section modulus untuk Coasting Service (L) sebesar",
            "the minimum section modulus reduction for Coasting Service (L) is",
        ),
        "T": (
            "pengurangan minimum section modulus untuk Sheltered Water Service (T) sebesar",
            "the minimum section modulus reduction for Sheltered Water Service (T) is",
        ),
    },
    "forepeak_stringer_spacing": {
        None: (
            "jarak vertikal tiers of beams/stringer di forepeak (ceruk haluan) adalah",
            "the vertical spacing of tiers of beams/stringers in the forepeak is",
        ),
    },
    "tug_winch_drum_diameter": {
        None: (
            "diameter drum winch kapal tunda adalah",
            "the tug boat winch drum diameter is",
        ),
    },
    "fire_door_closing_time": {
        "hinged": (
            "waktu penutupan pintu kebakaran engsel adalah",
            "the hinged fire door closing time is",
        ),
        "sliding": (
            "laju penutupan pintu kebakaran geser adalah",
            "the sliding fire door closure rate is",
        ),
    },
    "bulwark_guardrail_min_height": {
        None: (
            "tinggi minimum bulwark atau guard rail adalah",
            "the minimum bulwark or guard rail height is",
        ),
    },
    "ship_length_l_definition": {
        None: (
            "definisi panjang L adalah",
            "the definition of length L is",
        ),
    },
    "depth_to_length_ratio": {
        None: (
            "rasio kedalaman minimum terhadap panjang (depth-to-length ratio) adalah",
            "the minimum depth-to-length ratio is",
        ),
    },
    "spm_bow_chain_stopper_chain_size": {
        None: (
            "ukuran standar rantai stud-link untuk bow chain stopper pada sistem SPM adalah",
            "the standard stud-link chain size for bow chain stoppers in SPM systems is",
        ),
    },
    "aluminium_helideck_fire_protection": {
        None: (
            "syarat perlindungan kebakaran untuk helideck berbahan aluminium atau logam titik leleh rendah adalah",
            "the fire protection requirements for helidecks made of aluminium or low melting point metal are",
        ),
    },
    "iw_underwater_hull_corrosion": {
        None: (
            "sistem perlindungan korosi untuk lambung bawah air kapal dengan Notasi Kelas IW adalah",
            "the corrosion protection system for the underwater hull of IW Class Notation vessels is",
        ),
    },
    "framing_system_by_length": {
        None: (
            "sistem konstruksi yang digunakan berdasarkan panjang kapal adalah",
            "the framing system to use based on ship length is",
        ),
    },
    "container_scantling_factors": {
        None: (
            "faktor-faktor yang mempengaruhi perhitungan scantling kapal kontainer adalah",
            "the factors affecting container ship scantling calculations are",
        ),
    },
    "machinery_casing_min_thickness": {
        None: (
            "ketebalan pelat dinding casing dan bagian atas casing kamar mesin tidak boleh kurang dari",
            "the plate thickness of the machinery space casing walls and casing tops is not to be less than",
        ),
    },
    "supply_stowrack_heel_angle": {
        None: (
            "rak penyimpanan kargo geladak (stowracks) pada kapal suplai harus dirancang untuk menahan beban pada sudut kemiringan sebesar",
            "on-deck stowracks for deck cargo on supply vessels are to be designed for a load at an angle of heel of",
        ),
    },
    "supply_bulwark_plating_thickness": {
        None: (
            "ketebalan pelat kubu-kubu (bulwark plating) pada kapal suplai tidak boleh kurang dari",
            "the supply-vessel bulwark plating thickness is not to be less than",
        ),
    },
    "cargo_pump_room_skylight": {
        None: (
            "ketentuan jendela atap (skylights) pada kamar pompa kargo adalah",
            "the requirements for cargo pump room skylights are",
        ),
    },
    "mooring_winch_brake_holding": {
        None: (
            "rem derek tambat (mooring winches) harus memiliki kapasitas penahanan yang cukup untuk mencegah terulurnya tali ketika tegangan tali mencapai",
            "the mooring winch brake holding capacity must prevent unreeling of the mooring line when the rope tension reaches",
        ),
    },
    "warping_drum_chock_distance": {
        None: (
            "tromol gulung (warping drums) sebaiknya ditempatkan tidak lebih dari",
            "warping drums should preferably be positioned not more than",
        ),
    },
    "sauna_door_opening_direction": {
        None: (
            "ketentuan arah bukaan pintu ruang sauna adalah",
            "the sauna door opening direction requirement is",
        ),
    },
    "cargo_hold_bulkhead_min_thickness": {
        None: (
            "ketebalan pelat sekat ruang muat kargo (cargo hold bulkheads) pada kapal curah dalam kondisi apa pun tidak boleh kurang dari",
            "the cargo hold bulkhead plate thickness on bulk carriers is in no case to be taken less than",
        ),
    },
    "emergency_release_activation_time": {
        None: (
            "sistem rilis darurat (emergency release system) pada derek tunda harus berfungsi secepat yang wajar dan dalam waktu maksimum",
            "the emergency release system is to function as quickly as is reasonably practicable and within a maximum of",
        ),
    },
}


def _format_lookup_answer(match: _lookup.LookupMatch, lang: str) -> str:
    """Format a deterministic lookup answer with citation."""
    rule = match.rule
    is_id = lang == "id"
    body = rule.localized_text(lang).strip()
    while body.endswith("."):
        body = body[:-1].rstrip()
    body = body + "."
    para = f" {rule.paragraph_id}" if rule.paragraph_id else ""
    page = f"p.{rule.page_no}" if rule.page_no is not None else ""

    if is_id:
        return (
            f"Berdasarkan BKI Rules for Hull 2026: {body}\n"
            f"Sumber: Sec {rule.section_no}{para}, {page}.\n"
            f"Kutipan: \"" + rule.source_quote + "\""
        )
    else:
        return (
            f"According to BKI Rules for Hull 2026: {body}\n"
            f"Source: Sec {rule.section_no}{para}, {page}.\n"
            f"Quote: \"" + rule.source_quote + "\""
        )



# --- existing chain helpers ---

def _format_lookup_evidence(match: object, lang: str) -> str:
    """Render a lookup match as a [LOOKUP VERIFIED] context block for the LLM.
    
    Injected before RAG chunks so the LLM treats it as primary authoritative
    source while still having access to supporting RAG context.
    """
    rule = match.rule
    is_id = lang == "id"
    body = rule.localized_text(lang).strip()
    while body.endswith("."):
        body = body[:-1].rstrip()
    body = body + "."
    para = f" {rule.paragraph_id}" if rule.paragraph_id else ""
    page = f"p.{rule.page_no}" if rule.page_no is not None else ""
    citation = f"(Sec {rule.section_no}{para}, {page})" if page else f"(Sec {rule.section_no}{para})"

    if is_id:
        return (
            "\n[LOOKUP VERIFIED — PRIMARY SOURCE]\n"
            f"Fakta terverifikasi BKI Rules: {body} {citation}\n"
            f"Kutipan verbatim: \"" + rule.source_quote + "\"\n"
            "Gunakan HANYA citation di atas. Jangan membuat section/halaman baru.\n"
            "[/LOOKUP VERIFIED]\n"
        )
    else:
        return (
            "\n[LOOKUP VERIFIED — PRIMARY SOURCE]\n"
            f"Verified BKI Rules fact: {body} {citation}\n"
            f"Verbatim quote: \"" + rule.source_quote + "\"\n"
            "Use ONLY the citation above. Do NOT invent a different section or page.\n"
            "[/LOOKUP VERIFIED]\n"
        )


def _extract_history_facts(history: list[dict] | None, query: str) -> str:
    """Extract key=value facts and ship type from conversation history.

    Merges all user+assistant messages, then detects:
    - Variable assignments: L=120, H=8.5, b=600, B=20, etc.
    - Ship type via detect_ship_type()

    Most-recent-wins: facts are scanned in priority order
    (1) the CURRENT query, (2) the previous user message, (3) the whole
    history, and deduplicated by variable key — so a follow-up like
    "kalau L=150?" or "kalau ini kapal tanker?" correctly overrides the
    value/type established earlier in the conversation.

    Returns a comma-separated string for the translate prompt prefix,
    or empty string if nothing is found.
    """
    if not history:
        return ""
    latest_user = next(
        (h.get("content", "") for h in reversed(history)
         if h.get("role") == "user"),
        "",
    )
    all_text = " ".join(h.get("content", "") for h in history) + " " + query

    def _extract(text: str) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        for m in re.finditer(
            r'(?<!\w)([LHBbTtatKknfQ]\w{0,4})\s*[=:]\s*(\d+[.,]?\d*)\s*(m|mm|kN|MPa|N/mm2|%|t)?',
            text,
        ):
            unit = m.group(3) or ""
            out.append((m.group(1), f"{m.group(1)}={m.group(2)}{unit}"))
        return out

    seen: set[str] = set()
    facts: list[str] = []
    for text in (query, latest_user, all_text):
        for key, fact in _extract(text):
            if key not in seen:
                seen.add(key)
                facts.append(fact)

    query_en = apply_glossary(query)
    ship = (
        detect_ship_type(query_en)
        or detect_ship_type(apply_glossary(latest_user))
        or detect_ship_type(all_text)
    )
    if ship:
        facts.append(f"ship_type={ship}")
    return ", ".join(facts)


def _translate_condense(query, history, *, temperature, mode=None, lang=None) -> str:
    # Utility call: always fast_model + think=False (AGENTS.md hard rule).
    # Non-streaming; num_ctx is passed by client.chat default.
    # Pin temperature to 0.0: translate is a deterministic utility call
    # (the prompt itself does the work; sampling is not needed). The
    # hard-coded 0.0 also stops en_query variance across runs (manual-QA
    # showed 11/26 cases had en_query drift at temperature=0.1). The
    # HARD prompt rules ("Preserve formula symbols verbatim", etc.) prevent
    # topic-drift; low temperature is not the lever.
    # When mode and lang are provided, the result is cached in Supabase
    # (query_condense_cache) so identical query text always produces the
    # same en_query across processes (TUI + main.py).
    history = history or []  # accept None from direct callers (e.g. test scripts)
    # Multi-turn follow-ups are context-dependent: the cache key does NOT
    # include history, so the same query text in a different conversation
    # would reuse a stale en_query. Bypass the cache whenever history exists.
    is_multi_turn = bool(history)
    if not is_multi_turn and mode is not None and lang is not None:
        cached = _condense_cache_get(query, lang, mode)
        if cached is not None:
            out_c, reason = _validated_condensed_query(
                query,
                cached,
                validate=mode is not None and lang is not None,
            )
            # A stale cache row may contain a complete answer to an unrelated
            # earlier topic. Do not return its fallback here: bypass the row,
            # regenerate from the current query, and replace it only with a
            # validated result.
            if not reason.startswith("fallback:"):
                return out_c
    # Deterministic ID->EN substitution for BKI domain phrases before the LLM
    # call. Keeps the corpus-verified terms (e.g. 'sekat tubrukan' ->
    # 'collision bulkhead') pinned so qwen2.5:3b does not hallucinate
    # 'freeboard' / 'hatch cover' / 'side stringer' from a thin glossary
    # priming in the system prompt.
    query_pre = apply_glossary(query)
    # Extract persistent facts (L, H, B, ship type) from history so
    # the LLM can fold them into a self-contained English question.
    history_prefix = _extract_history_facts(history, query)
    if history_prefix:
        query_pre = f"[From conversation history: {history_prefix}] {query_pre}"
    messages = [{"role": "system", "content": prompts.TRANSLATE_CONDENSE_SYSTEM}]
    # Multi-turn: feed the model only the PREVIOUS USER messages (the prior
    # questions), never the assistant answers. Assistant answers are long,
    # cite-heavy ("Sec 6 | B.4.3 p.103") and a small 3B model tends to echo
    # those citations as the rewrite instead of producing an English question.
    # The extracted facts prefix + prior questions give enough context.
    for h in history:
        if is_multi_turn and h.get("role") == "assistant":
            continue
        messages.append(h)
    messages.append({"role": "user", "content": query_pre})
    out = chat(
        settings.fast_model,
        messages,
        temperature=0.0,
        max_tokens=settings.translate_max_tokens,
        think=False,
    )
    result = _clean_one_liner(out)
    en_query = result if result else query_pre  # fall back to substituted query if LLM empty
    en_query, _reason = _validated_condensed_query(
        query,
        en_query,
        validate=mode is not None and lang is not None,
    )
    if not is_multi_turn and mode is not None and lang is not None:
        _condense_cache_put(query, lang, mode, en_query)
    return en_query


def _expand(en_query, *, temperature) -> list[str]:
    # Utility call: always fast_model + think=False (AGENTS.md hard rule).
    # Non-streaming; num_ctx is passed by client.chat default.
    # Called only when settings.enable_multi_query is True.
    messages = [
        {"role": "system", "content": prompts.EXPAND_SYSTEM},
        {"role": "user", "content": f"Query: {en_query}"},
    ]
    out = chat(
        settings.fast_model,
        messages,
        temperature=temperature,
        max_tokens=settings.translate_max_tokens,
        think=False,
    )
    return out.splitlines()


def _parse_multi_query(lines: list[str], n: int) -> list[str]:
    """Defensive parser. Drop empties, strip list prefixes/dashes/quotes, dedup, cap at n."""
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        s = line.strip()
        # Strip common list prefixes: "1.", "1)", "-", "*", quotes
        s = s.lstrip("0123456789.-)* \\t")
        s = s.strip().strip('"').strip("'").strip()
        if not s or len(s) < 4:
            continue
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
        if len(out) >= n:
            break
    return out


def _clean_one_liner(text: str) -> str:
    s = text.strip()
    s = s.strip('"').strip("'").strip()
    for prefix in ("rewritten query:", "english query:", "query:", "answer:"):
        if s.lower().startswith(prefix):
            s = s[len(prefix):].strip()
    for line in s.splitlines():
        line = line.strip()
        if line:
            return line
    return s


def _language_name(lang: str) -> str:
    """Map a short language label to a human-readable name for the model.

    id -> "Bahasa Indonesia"
    en -> "English"
    other -> fall back to "the same language the user is writing in"
        (the caller passes the raw query script decision; here we just
        tell the model to follow the user's own language).
    """
    if lang == "id":
        return "Bahasa Indonesia"
    if lang == "en":
        return "English"
    return "the same language the user is writing in (do not switch)"


def _apply_guardrail(chunks: list[RetrievedChunk]) -> tuple[list[RetrievedChunk], bool, str]:
    """Reject OOD only when cross-encoder confidence is genuinely low.

    Uses a relative gap (top vs second) AND a min-score floor.
    NOT an absolute-0 cutoff (HANDOFF issue #1).
    Calibrated on POST-translation scores (HANDOFF Section 8 update).
    Default-mode only (Fase 3 req #5) -- fast mode has no cross-encoder scores.
    """
    if not chunks:
        return [], True, "no_chunks"
    top = chunks[0].score
    second = chunks[1].score if len(chunks) > 1 else top
    if top < settings.guardrail_min_top_score:
        return [], True, f"top_below_min({top:.3f}<{settings.guardrail_min_top_score})"
    # Build 41: drop the `top <= 0` condition from flat_distribution. The
    # cross-encoder legitimately returns NEGATIVE scores for valid in-domain
    # pairs (e.g. -0.34 for a correct Sec 8 hit), and a small gap is normal
    # when several candidates are equally relevant. The absolute floor
    # (guardrail_min_top_score, -2.0) already rejects OOD queries; the gap
    # check without `top <= 0` would reject flat distributions even when the
    # top is clearly above the OOD floor. Removing `top <= 0` means in-domain
    # hits above the floor are always accepted, while OOD stays rejected by
    # the floor itself.
    gap = top - second
    if gap < settings.guardrail_top_gap and top < settings.guardrail_min_top_score + 0.5:
        return [], True, f"flat_distribution(gap={gap:.3f})"
    return chunks, False, ""


# Terms clearly outside scope of BKI Rules for Hull (Pt.1, Vol.II).
# These relate to electrical installations, machinery, inland waterways,
# welding procedure qualification, or other BKI volumes.
_OOD_KEYWORDS: list[str] = [
    "pompa pemadam", "fire pump",
    "panel distribusi listrik", "ip rating",
    "kapal sungai", "inland waterway",
    "penyeberangan",
    "wpqt", "welding procedure", "prosedur pengelasan",
    "kualifikasi las", "wps",
    "dynamic positioning", "dps kelas",
    "sistem permesinan", "redundansi mesin",
    "propeller", "baling-baling",
    "pedoman kelistrikan", "instalasi sprinkler",
    "sistem perpipaan",
]


def _check_ood_query(query: str, lang: str) -> str | None:
    """Return a rejection message if the query is clearly out-of-scope.

    Checks query (original language) + ignores case/whitespace.
    Returns None if the query appears to be in BKI hull scope.
    """
    query_lower = query.lower()
    for kw in _OOD_KEYWORDS:
        if kw in query_lower:
            if lang == "id":
                return (
                    "Pertanyaan ini di luar cakupan BKI Rules for Hull (Pt.1, Vol.II). "
                    "Dokumen ini hanya mencakup aturan struktur lambung kapal laut baja. "
                    "Silakan merujuk ke volume BKI yang sesuai."
                )
            else:
                return (
                    "This question is outside the scope of BKI Rules for Hull (Pt.1, Vol.II). "
                    "This document only covers hull structural rules for seagoing steel ships. "
                    "Please refer to the appropriate BKI volume."
                )
    return None


def _build_answer_messages(
    query: str,
    chunks: list[RetrievedChunk],
    language: str,
    answer_style: str = "detailed",
    table_evidence: str = "",
    lookup_evidence: str = "",
    calc_evidence: str = "",
) -> list[dict]:
    """Build a FRESH messages list for one _answer call.

    Critical: a new list is constructed every call to prevent cross-call
    accumulation of history. With num_ctx=8192 on a 4GB-VRAM box, accidental
    accumulation would silently truncate the system prompt or context window.
    """
    context = prompts.build_context(chunks, table_evidence=table_evidence)
    if lookup_evidence:
        context = lookup_evidence + "\n" + context
    if calc_evidence:
        calc_block = (
            "\n[CALCULATION RESULT — VERIFIED, DO NOT CHANGE THE NUMBER]\n"
            "The following value was computed deterministically by the rules "
            "engine. State it in natural language; do not recompute, approximate, "
            "or alter the numeric result.\n"
            f"{calc_evidence}\n"
            "[/CALCULATION RESULT]\n"
        )
        context = calc_block + "\n" + context
    style = prompts.answer_style_instruction(answer_style)
    target = _language_name(language)
    if language == "id":
        user_msg = (
            f"[[INTERNAL_INSTRUCTION — DO NOT REPEAT THIS SENTENCE: You MUST answer in Bahasa Indonesia only. Never use English. Never add a meta-instruction in your answer.]]\n\n"
            f"Konteks:\\n{context}\\n\\n"
            f"Pertanyaan: {query}\\n\\n"
            f"{style}\n\n"
            f"[[REMINDER — DO NOT ECHO: Jawab dalam Bahasa Indonesia.]]"
        )
    else:
        user_msg = (
            f"[[INTERNAL_INSTRUCTION — DO NOT REPEAT THIS SENTENCE: You MUST answer in English only. Never use another language. Never add a meta-instruction in your answer.]]\n\n"
            f"Context:\\n{context}\\n\\n"
            f"Question: {query}\\n\\n"
            f"{style}\n\n"
            f"[[REMINDER — DO NOT ECHO: Respond in English.]]"
        )
    return [
        {"role": "system", "content": prompts.SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]


def _answer_fallback_non_stream(query, chunks, language, mode_cfg, answer_style: str = "detailed", lookup_evidence: str = "", calc_evidence: str = "") -> str:
    """Single non-stream chat call used as a fallback when the streaming
    path produces zero tokens. Returns the model's content (may be empty
    if Ollama also returns empty for the non-stream call)."""
    messages = _build_answer_messages(query, chunks, language, answer_style=answer_style, lookup_evidence=lookup_evidence, calc_evidence=calc_evidence)
    out = chat(
        mode_cfg.model,
        messages,
        temperature=mode_cfg.temperature,
        think=False,
    )
    return out if out else ""


def _answer(
    query, chunks, language, *,
    model, temperature,
    think: bool = False,
    answer_style: str = "detailed",
    table_evidence: str = "",
    lookup_evidence: str = "",
    calc_evidence: str = "",
) -> str:
    """Final user-facing answer with empty-response safeguard.

    Builds a fresh messages list per call (no cross-call accumulation).
    If the model returns an empty content (e.g. context overflow, transient
    generation glitch), retries ONCE with the same payload before returning
    a clear fallback. Never returns a silent empty string.
    """
    messages = _build_answer_messages(query, chunks, language, answer_style=answer_style, table_evidence=table_evidence, lookup_evidence=lookup_evidence, calc_evidence=calc_evidence)
    out = chat(model, messages, temperature=temperature, think=think)
    if out and out.strip():
        return out

    # Single retry
    print(
        f"  [chain._answer] WARNING: empty content on first try, retrying once "
        f"(model={model} lang={language} chunks={len(chunks)})",
        file=sys.stderr,
        flush=True,
    )
    messages_retry = _build_answer_messages(query, chunks, language, answer_style=answer_style, table_evidence=table_evidence, lookup_evidence=lookup_evidence, calc_evidence=calc_evidence)
    out2 = chat(model, messages_retry, temperature=temperature, think=think)
    if out2 and out2.strip():
        return out2

    print(
        f"  [chain._answer] ERROR: empty content after retry, returning fallback",
        file=sys.stderr,
        flush=True,
    )
    if language == "id":
        return (
            "Maaf, model gagal menghasilkan jawaban dari konteks yang tersedia. "
            "Silakan coba ulang atau ajukan pertanyaan yang lebih spesifik "
            "(berdasarkan BKI Rules for Hull 2026)."
        )
    return (
        "Sorry, the model failed to produce an answer from the available context. "
        "Please try again or rephrase your question (BKI Rules for Hull 2026)."
    )
    messages_retry = _build_answer_messages(query, chunks, language, answer_style=answer_style)
    out2 = chat(model, messages_retry, temperature=temperature, think=think)
    if out2 and out2.strip():
        return out2

    print(
        f"  [chain._answer] ERROR: empty content after retry, returning fallback",
        file=sys.stderr,
        flush=True,
    )
    if language == "id":
        return (
            "Maaf, model gagal menghasilkan jawaban dari konteks yang tersedia. "
            "Silakan coba ulang atau ajukan pertanyaan yang lebih spesifik "
            "(berdasarkan BKI Rules for Hull 2026)."
        )
    return (
        "Sorry, the model failed to produce an answer from the available context. "
        "Please try again or rephrase your question (BKI Rules for Hull 2026)."
    )
