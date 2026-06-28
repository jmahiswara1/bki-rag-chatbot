import sys
import time
from dataclasses import dataclass, field
from typing import Iterator

from src.calc.engine import calculate
from src.calc.registry import search_formulas, select_formula
from src.core.config import settings
from src.core.models import Intent, RetrievedChunk
from src.llm import lookup as _lookup
from src.llm import prompts
from src.llm.glossary import apply_glossary
from src.llm.client import chat, chat_stream
from src.llm.intent import classify, classify_with_llm
from src.llm.language import detect_language
from src.llm.modes import MODES
from src.retrieval.query import retrieve_context


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
                    message = calc_result.message
                else:
                    formula_list = "\n".join([
                        f"  - {f.title} (Sec {f.section_no})"
                        for f, _score in clarification_list
                    ])
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
    if mode == "default":
        en_query = _translate_condense(query, history, temperature=mode_cfg.temperature)
    else:
        if lang == "en" and not history:
            en_query = query
        else:
            en_query = _translate_condense(query, history, temperature=mode_cfg.temperature)
    timings["translate"] = time.time() - t

    # 4.5. lookup-first (before retrieval — deterministic short-circuit)
    t = time.time()
    lookup_match = None
    if mode == "default" and intent.kind == "rules_qa":
        try:
            rules = _get_lookup_rules()
            if rules:
                lookup_match = _lookup.match_lookup(
                    query_id=query, query_en=en_query, rules=rules,
                )
            if lookup_match is not None:
                msg = _format_lookup_answer(lookup_match, lang)
                timings["lookup"] = time.time() - t
                return PipelineState(
                    lang=lang,
                    intent=intent,
                    en_query=en_query,
                    expanded=[],
                    candidates=[],
                    rejected=False,
                    reject_reason="",
                    timings=timings,
                    mode_cfg=mode_cfg,
                    short_circuit_msg=msg,
                    is_pre_answer_only=True,
                    lookup_match=lookup_match,
                )
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
    if mode == "default" and settings.enable_multi_query:
        t = time.time()
        raw = _expand(en_query, temperature=mode_cfg.temperature)
        expanded = _parse_multi_query(raw, n=settings.expand_n_queries)
        timings["expand"] = time.time() - t

    # 6. retrieve
    t = time.time()
    candidates = retrieve_context(
        query_text=query,
        mode=mode,
        fts_query=en_query,
        en_query=en_query,
        multi_queries=expanded if expanded else None,
    )
    timings["retrieve"] = time.time() - t

    # 7. guardrail (default only)
    rejected = False
    reject_reason = ""
    short_circuit_msg = ""
    is_pre_answer_only = False
    if mode == "default" and candidates:
        candidates, rejected, reject_reason = _apply_guardrail(candidates)
    if not candidates:
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
    )
    state.timings["answer"] = time.time() - t
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
        ))
        return

    yield ("status", "answer_streaming")
    messages = _build_answer_messages(query, state.candidates, state.lang, answer_style=state.mode_cfg.answer_style)
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
    fallback_used = False
    if not final_text.strip():
        # Safeguard: 1x non-stream retry (re-uses _build_answer_messages + client.chat).
        # Mirrors _answer's retry-then-fallback pattern but only fires once here.
        print(
            f"  [chain.chain_answer_stream] WARNING: stream produced 0 tokens, "
            f"falling back to 1x non-stream chat (model={state.mode_cfg.model})",
            file=sys.stderr,
            flush=True,
        )
        final_text = _answer_fallback_non_stream(query, state.candidates, state.lang, state.mode_cfg, answer_style=state.mode_cfg.answer_style)
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
        ))
        return

    yield ("status", "answer_streaming")
    messages = _build_answer_messages(query, state.candidates, state.lang, answer_style=state.mode_cfg.answer_style)
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
        final_text = _answer_fallback_non_stream(query, state.candidates, state.lang, state.mode_cfg, answer_style=state.mode_cfg.answer_style)
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

def _translate_condense(query, history, *, temperature) -> str:
    # Utility call: always fast_model + think=False (AGENTS.md hard rule).
    # Non-streaming; num_ctx is passed by client.chat default.
    # Pin temperature to 0.0: translate is a deterministic utility call
    # (the prompt itself does the work; sampling is not needed). The
    # hard-coded 0.0 also stops en_query variance across runs (manual-QA
    # showed 11/26 cases had en_query drift at temperature=0.1). The
    # HARD prompt rules ("Preserve formula symbols verbatim", etc.) prevent
    # topic-drift; low temperature is not the lever.
    history = history or []  # accept None from direct callers (e.g. test scripts)
    # Deterministic ID->EN substitution for BKI domain phrases before the LLM
    # call. Keeps the corpus-verified terms (e.g. 'sekat tubrukan' ->
    # 'collision bulkhead') pinned so qwen2.5:3b does not hallucinate
    # 'freeboard' / 'hatch cover' / 'side stringer' from a thin glossary
    # priming in the system prompt.
    query_pre = apply_glossary(query)
    messages = [{"role": "system", "content": prompts.TRANSLATE_CONDENSE_SYSTEM}]
    for h in history:
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
    return result if result else query_pre  # fall back to substituted query if LLM empty


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
    gap = top - second
    if gap < settings.guardrail_top_gap and top <= 0:
        return [], True, f"flat_distribution(gap={gap:.3f})"
    return chunks, False, ""


def _build_answer_messages(
    query: str,
    chunks: list[RetrievedChunk],
    language: str,
    answer_style: str = "detailed",
) -> list[dict]:
    """Build a FRESH messages list for one _answer call.

    Critical: a new list is constructed every call to prevent cross-call
    accumulation of history. With num_ctx=8192 on a 4GB-VRAM box, accidental
    accumulation would silently truncate the system prompt or context window.
    """
    context = prompts.build_context(chunks)
    style = prompts.answer_style_instruction(answer_style)
    target = _language_name(language)
    if language == "id":
        user_msg = (
            f"TARGET LANGUAGE: Bahasa Indonesia. Hard rule: jawab HANYA dalam Bahasa Indonesia. Jangan gunakan bahasa lain.\n\n"
            f"Konteks:\\n{context}\\n\\n"
            f"Pertanyaan: {query}\\n\\n"
            f"{style}"
        )
    else:
        user_msg = (
            f"TARGET LANGUAGE: {target}. Hard rule: respond ONLY in {target}. Never use any other language.\n\n"
            f"Context:\\n{context}\\n\\n"
            f"Question: {query}\\n\\n"
            f"{style}"
        )
    return [
        {"role": "system", "content": prompts.SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]


def _answer_fallback_non_stream(query, chunks, language, mode_cfg, answer_style: str = "detailed") -> str:
    """Single non-stream chat call used as a fallback when the streaming
    path produces zero tokens. Returns the model's content (may be empty
    if Ollama also returns empty for the non-stream call)."""
    messages = _build_answer_messages(query, chunks, language, answer_style=answer_style)
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
) -> str:
    """Final user-facing answer with empty-response safeguard.

    Builds a fresh messages list per call (no cross-call accumulation).
    If the model returns an empty content (e.g. context overflow, transient
    generation glitch), retries ONCE with the same payload before returning
    a clear fallback. Never returns a silent empty string.
    """
    messages = _build_answer_messages(query, chunks, language, answer_style=answer_style)
    out = chat(model, messages, temperature=temperature, think=think)
    if out and out.strip():
        return out

    # Single retry. qwen3.5:4b occasionally returns "" on the first call after
    # heavy prior load; the second call usually succeeds without changing the
    # prompt. If still empty, log and return an explicit fallback.
    print(
        f"  [chain._answer] WARNING: empty content on first try, retrying once "
        f"(model={model} lang={language} chunks={len(chunks)})",
        file=sys.stderr,
        flush=True,
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
