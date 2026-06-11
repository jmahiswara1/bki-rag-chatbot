import time
from dataclasses import dataclass, field

from src.calc.engine import calculate
from src.core.config import settings
from src.core.models import Intent, RetrievedChunk
from src.llm import prompts
from src.llm.client import chat
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


def chain_answer(
    query: str,
    history: list[dict] | None = None,
    mode: str = "default",
) -> ChainResult:
    """End-to-end Fase 3 pipeline. See HANDOFF Section 8.

    Pipeline:
      detect_lang -> intent (heuristic, LLM fallback default-only) ->
      [calc short-circuit] -> translate+condense (default: always; fast: skip
      only if high-conf EN + no history) -> multi-query expand (default only,
      gated by settings.enable_multi_query) ->
      retrieve (en_query drives FTS, averaged vector when multi-query enabled) ->
      [rerank inside retrieve_context, default only] -> guardrail (default
      only, because cross-encoder scores only exist there) -> answer.
    """
    timings: dict[str, float] = {}
    history = history or []
    mode_cfg = MODES[mode]

    # 1. detect language of the ORIGINAL query (used for answer language mirror)
    t = time.time()
    lang, _lang_conf = detect_language(query)
    timings["detect_lang"] = time.time() - t

    # 2. intent classification: heuristic first; LLM fallback only for default
    t = time.time()
    intent = classify(query, history)
    if intent.confidence == "low" and mode == "default":
        intent = classify_with_llm(query, temperature=mode_cfg.temperature)
    timings["intent"] = time.time() - t

    # 3. calculation intent short-circuits to Fase 4 stub (no retrieval, no LLM math)
    if intent.kind == "calculation":
        t = time.time()
        calc = calculate(query, intent=intent)
        timings["calc"] = time.time() - t
        return ChainResult(
            answer=calc.message,
            sources=[],
            intent=intent,
            language=lang,
            timings=timings,
        )

    # 4. translate + condense.
    #    Default mode: NEVER skip (Fase 3 req #3 fail-safe).
    #    Fast mode: skip only if high-confidence English AND no history.
    t = time.time()
    if mode == "default":
        en_query = _translate_condense(query, history, temperature=mode_cfg.temperature)
    else:
        if lang == "en" and not history:
            en_query = query
        else:
            en_query = _translate_condense(query, history, temperature=mode_cfg.temperature)
    timings["translate"] = time.time() - t

    # 5. multi-query expansion (default mode only, gated by settings.enable_multi_query).
    #    Keep the expand functions for future experiments; just skip the call when gated.
    expanded: list[str] = []
    if mode == "default" and settings.enable_multi_query:
        t = time.time()
        raw = _expand(en_query, temperature=mode_cfg.temperature)
        expanded = _parse_multi_query(raw, n=settings.expand_n_queries)
        timings["expand"] = time.time() - t

    # 6. retrieve (retrieve_context handles rerank for default mode internally)
    t = time.time()
    candidates = retrieve_context(
        query_text=query,
        mode=mode,
        fts_query=en_query,
        en_query=en_query,
        multi_queries=expanded if expanded else None,
    )
    timings["retrieve"] = time.time() - t

    # 7. guardrail — DEFAULT MODE ONLY (Fase 3 req #5).
    #    Fast mode has no cross-encoder scores (rerank skipped) so the
    #    relative-gap guardrail would be meaningless.
    rejected = False
    reject_reason = ""
    if mode == "default" and candidates:
        candidates, rejected, reject_reason = _apply_guardrail(candidates)

    # 8. answer
    if not candidates:
        if lang == "id":
            answer = "Konteks yang tersedia tidak cukup untuk menjawab pertanyaan ini berdasarkan BKI Rules for Hull 2026."
        else:
            answer = "The available context is insufficient to answer this question based on the BKI Rules for Hull 2026."
    else:
        t = time.time()
        answer = _answer(query, candidates, lang, model=mode_cfg.model, temperature=mode_cfg.temperature, think=False)
        timings["answer"] = time.time() - t

    return ChainResult(
        answer=answer,
        sources=candidates,
        intent=intent,
        language=lang,
        timings=timings,
        en_query=en_query,
        expanded=expanded,
        rejected=rejected,
        reject_reason=reject_reason,
    )


def _translate_condense(query, history, *, temperature) -> str:
    # Utility call: always fast_model + think=False (AGENTS.md hard rule).
    # Non-streaming; num_ctx is passed by client.chat default.
    history = history or []  # accept None from direct callers (e.g. test scripts)
    messages = [{"role": "system", "content": prompts.TRANSLATE_CONDENSE_SYSTEM}]
    for h in history:
        messages.append(h)
    messages.append({"role": "user", "content": query})
    out = chat(
        settings.fast_model,
        messages,
        temperature=temperature,
        max_tokens=settings.translate_max_tokens,
        think=False,
    )
    result = _clean_one_liner(out)
    return result if result else query  # fall back to original if LLM produced nothing


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


def _build_answer_messages(query: str, chunks: list[RetrievedChunk], language: str) -> list[dict]:
    """Build a FRESH messages list for one _answer call.

    Critical: a new list is constructed every call to prevent cross-call
    accumulation of history. With num_ctx=8192 on a 4GB-VRAM box, accidental
    accumulation would silently truncate the system prompt or context window.
    """
    context = prompts.build_context(chunks)
    if language == "id":
        user_msg = (
            f"Konteks:\\n{context}\\n\\n"
            f"Pertanyaan: {query}\\n\\n"
            f"Jawab dalam Bahasa Indonesia. Setiap klaim harus menyertakan sitasi "
            f"format (Sec N | paragraph_id, p.XX). Jika konteks tidak cukup, katakan begitu."
        )
    else:
        user_msg = (
            f"Context:\\n{context}\\n\\n"
            f"Question: {query}\\n\\n"
            f"Answer in English. Every claim must include a citation in the format "
            f"(Sec N | paragraph_id, p.XX). If the context is insufficient, say so."
        )
    return [
        {"role": "system", "content": prompts.SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]


def _answer(query, chunks, language, *, model, temperature, think: bool = False) -> str:
    """Final user-facing answer with empty-response safeguard.

    Builds a fresh messages list per call (no cross-call accumulation).
    If the model returns an empty content (e.g. context overflow, transient
    generation glitch), retries ONCE with the same payload before returning
    a clear fallback. Never returns a silent empty string.
    """
    messages = _build_answer_messages(query, chunks, language)
    out = chat(model, messages, temperature=temperature, think=think)
    if out and out.strip():
        return out

    # Single retry. qwen3.5:4b occasionally returns "" on the first call after
    # heavy prior load; the second call usually succeeds without changing the
    # prompt. If still empty, log and return an explicit fallback.
    import sys
    print(
        f"  [chain._answer] WARNING: empty content on first try, retrying once "
        f"(model={model} lang={language} chunks={len(chunks)})",
        file=sys.stderr,
        flush=True,
    )
    messages_retry = _build_answer_messages(query, chunks, language)
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
