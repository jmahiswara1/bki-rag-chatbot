"""Fase 5a test: streaming answer chain (fondasi CLI + tuntaskan G).

Validates chain_answer_stream end-to-end:
  Test 1: EN in-domain, 3 runs (1 full + 2 reuse retrieval). All 3 must be
          non-empty AND contain a citation pattern.
  Test 2: ID in-domain, result.language == "id" (field, not substring),
          non-empty, citable.
  Test 3: OOD query, result.rejected == True.
  Test 4: intent=calculation, result.answer contains "Fase 4" or "Calculation".
"""
import re
import sys
import time

import torch
torch.set_num_threads(8)
print(f"torch threads: {torch.get_num_threads()}", flush=True)

sys.stdout.reconfigure(encoding='utf-8')

from src.llm.chain import (
    ChainStreamResult,
    PipelineState,
    chain_answer_stream,
    _pre_answer_pipeline,
    _stream_from_state,
)
from src.llm.prompts import format_citation


results: list[tuple[str, bool, str]] = []


def record(name: str, passed: bool, note: str = "") -> None:
    results.append((name, passed, note))
    flag = "PASS" if passed else "FAIL"
    print(f"  [{flag}] {name}  {note}", flush=True)


def banner(title: str) -> None:
    print(flush=True)
    print("=" * 70, flush=True)
    print(title, flush=True)
    print("=" * 70, flush=True)


def _consume(gen):
    """Drain a chain_answer_stream / _stream_from_state generator.

    Returns (answer_text, status_events, result). result is the
    ChainStreamResult yielded as ("done", payload).
    """
    tokens: list[str] = []
    status_events: list[str] = []
    result: ChainStreamResult | None = None
    for kind, payload in gen:
        if kind == "status":
            status_events.append(payload)
        elif kind == "token":
            tokens.append(payload)
        elif kind == "done":
            result = payload
    return "".join(tokens), status_events, result


# Citation regex tolerates 4 forms built by format_citation:
# Use the shared citation regex from prompts (single source of truth;
# tolerates both with-comma and no-comma formats; checks grounding, not punctuation).
from src.llm.prompts import CITATION_RE as _CITATION_RE


# ---------------------------------------------------------------------------
banner("Test 1: EN in-domain, 1x full stream + 2x reuse retrieval")
# ---------------------------------------------------------------------------
T1_Q = "What is the minimum plate thickness for shell plating?"
print(f"Query: {T1_Q}", flush=True)
t1_t0 = time.time()
run1_answer, run1_status, run1_result = _consume(chain_answer_stream(T1_Q, mode="default"))
t1_elapsed = time.time() - t1_t0
print(f"  run 1 (full)  : tokens={run1_result.token_count if run1_result else 0} "
      f"sources={len(run1_result.sources) if run1_result else 0} "
      f"lang={run1_result.language if run1_result else '?'} "
      f"rejected={run1_result.rejected if run1_result else '?'} "
      f"timings={run1_result.timings if run1_result else '?'}",
      flush=True)
print(f"           status_events: {run1_status}", flush=True)
print(f"           answer[:200]: {run1_answer[:200]!r}", flush=True)

# Reuse retrieval: run pipeline once, then stream 2x from the same state.
print("  Reusing pipeline state for runs 2 and 3...", flush=True)
t_state = time.time()
state = _pre_answer_pipeline(T1_Q, history=None, mode="default")
print(f"  pre_answer_pipeline state built in {time.time()-t_state:.1f}s "
      f"(intent={state.intent.kind}, candidates={len(state.candidates)}, "
      f"rejected={state.rejected})", flush=True)

run2_answer, run2_status, run2_result = _consume(_stream_from_state(T1_Q, state))
print(f"  run 2 (reuse) : tokens={run2_result.token_count if run2_result else 0} "
      f"sources={len(run2_result.sources) if run2_result else 0} "
      f"lang={run2_result.language if run2_result else '?'} "
      f"rejected={run2_result.rejected if run2_result else '?'}",
      flush=True)
print(f"           status_events: {run2_status}", flush=True)
print(f"           answer[:200]: {run2_answer[:200]!r}", flush=True)

run3_answer, run3_status, run3_result = _consume(_stream_from_state(T1_Q, state))
print(f"  run 3 (reuse) : tokens={run3_result.token_count if run3_result else 0} "
      f"sources={len(run3_result.sources) if run3_result else 0} "
      f"lang={run3_result.language if run3_result else '?'} "
      f"rejected={run3_result.rejected if run3_result else '?'}",
      flush=True)
print(f"           status_events: {run3_status}", flush=True)
print(f"           answer[:200]: {run3_answer[:200]!r}", flush=True)

# Assertions: 3/3 non-empty + 3/3 citable.
def _ok_run(label, ans, res):
    has_text = bool(ans and ans.strip())
    has_cit = bool(_CITATION_RE.search(ans))
    return has_text, has_cit, res

t1_pass = True
t1_notes = []
for label, ans, res in [
    ("run1", run1_answer, run1_result),
    ("run2", run2_answer, run2_result),
    ("run3", run3_answer, run3_result),
]:
    has_text, has_cit, _ = _ok_run(label, ans, res)
    note = f"{label}: text={has_text} cit={has_cit}"
    t1_notes.append(note)
    if not (has_text and has_cit):
        t1_pass = False
record("T1: 3x stream, all non-empty + citable",
       t1_pass, "; ".join(t1_notes))
print(f"  T1 total elapsed: {t1_elapsed:.1f}s", flush=True)


# ---------------------------------------------------------------------------
banner("Test 2: ID in-domain, full stream, language=id field + citable")
# ---------------------------------------------------------------------------
T2_Q = "berapa ketebalan minimum pelat lambung kapal?"
print(f"Query: {T2_Q}", flush=True)
t2_t0 = time.time()
t2_answer, t2_status, t2_result = _consume(chain_answer_stream(T2_Q, mode="default"))
t2_elapsed = time.time() - t2_t0
print(f"  tokens={t2_result.token_count if t2_result else 0} "
      f"sources={len(t2_result.sources) if t2_result else 0} "
      f"lang={t2_result.language if t2_result else '?'} "
      f"rejected={t2_result.rejected if t2_result else '?'} "
      f"timings={t2_result.timings if t2_result else '?'}",
      flush=True)
print(f"  status_events: {t2_status}", flush=True)
print(f"  answer[:200]: {t2_answer[:200]!r}", flush=True)

t2_text = bool(t2_answer and t2_answer.strip())
t2_cit = bool(_CITATION_RE.search(t2_answer))
t2_lang_field = (t2_result.language == "id") if t2_result else False
t2_pass = t2_text and t2_cit and t2_lang_field
record("T2: ID in-domain, language=id, non-empty, citable",
       t2_pass,
       f"text={t2_text} cit={t2_cit} lang_field={t2_result.language if t2_result else '?'}")
print(f"  T2 elapsed: {t2_elapsed:.1f}s", flush=True)


# ---------------------------------------------------------------------------
banner("Test 3: OOD query, must be rejected (default mode)")
# ---------------------------------------------------------------------------
T3_Q = "Bagaimana cara membuat kue coklat?"
print(f"Query: {T3_Q}", flush=True)
t3_t0 = time.time()
t3_answer, t3_status, t3_result = _consume(chain_answer_stream(T3_Q, mode="default"))
t3_elapsed = time.time() - t3_t0
print(f"  tokens={t3_result.token_count if t3_result else 0} "
      f"sources={len(t3_result.sources) if t3_result else 0} "
      f"lang={t3_result.language if t3_result else '?'} "
      f"rejected={t3_result.rejected if t3_result else '?'} "
      f"reject_reason={t3_result.reject_reason if t3_result else '?'} "
      f"timings={t3_result.timings if t3_result else '?'}",
      flush=True)
print(f"  status_events: {t3_status}", flush=True)
print(f"  answer: {t3_answer!r}", flush=True)

# The reject message string (mirror bahasa) was set in chain.py; assert
# the actual text is present (informational, not blocking).
t3_rejected = (t3_result.rejected is True) if t3_result else False
t3_pass = t3_rejected
record("T3: OOD rejected (rejected=True)",
       t3_pass,
       f"rejected={t3_rejected} reason={t3_result.reject_reason if t3_result else 'n/a'}")
print(f"  T3 elapsed: {t3_elapsed:.1f}s", flush=True)


# ---------------------------------------------------------------------------
banner("Test 4: intent=calculation, must yield Fase 4 stub message")
# ---------------------------------------------------------------------------
T4_Q = "hitung modulus penampang untuk balok longitudinal"
print(f"Query: {T4_Q}", flush=True)
t4_t0 = time.time()
t4_answer, t4_status, t4_result = _consume(chain_answer_stream(T4_Q, mode="default"))
t4_elapsed = time.time() - t4_t0
print(f"  tokens={t4_result.token_count if t4_result else 0} "
      f"sources={len(t4_result.sources) if t4_result else 0} "
      f"lang={t4_result.language if t4_result else '?'} "
      f"intent={t4_result.intent if t4_result else '?'} "
      f"rejected={t4_result.rejected if t4_result else '?'} "
      f"timings={t4_result.timings if t4_result else '?'}",
      flush=True)
print(f"  status_events: {t4_status}", flush=True)
print(f"  answer: {t4_answer!r}", flush=True)

t4_intent_calc = (t4_result.intent.kind == "calculation") if t4_result else False
t4_msg = "Fase 4" in t4_answer or "Calculation" in t4_answer
t4_pass = t4_intent_calc and t4_msg
record("T4: calculation intent, stub message contains Fase 4 / Calculation",
       t4_pass,
       f"intent={t4_result.intent.kind if t4_result else '?'} stub_msg={t4_msg}")
print(f"  T4 elapsed: {t4_elapsed:.1f}s", flush=True)


# ---------------------------------------------------------------------------
banner("SUMMARY")
# ---------------------------------------------------------------------------
passed = sum(1 for _, p, _ in results if p)
failed = sum(1 for _, p, _ in results if not p)
total = len(results)
for name, p, note in results:
    flag = "PASS" if p else "FAIL"
    print(f"  [{flag}] {name}", flush=True)
print(f"\n{passed}/{total} passed, {failed} failed", flush=True)
sys.exit(0 if failed == 0 else 1)
