"""Test Section 6: Core Query Paths (live services required).

Tests:
- Normal query -> streaming answer + sources
- Calculation query -> stub message, no sources, no crash
- Out-of-domain query -> guardrail rejection
"""
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

PASS = 0
FAIL = 0

def check(label: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {label}")
    else:
        FAIL += 1
        msg = f"  [FAIL] {label}"
        if detail:
            msg += f"  -- {detail}"
        print(msg)


from src.llm.chain import chain_answer_stream, ChainStreamResult

def run_query(query: str, mode: str = "default", history: list | None = None):
    """Run chain_answer_stream and collect the final result."""
    gen = chain_answer_stream(query, mode=mode, history=history)
    tokens = []
    final = None
    for kind, payload in gen:
        if kind == "token":
            tokens.append(payload)
        elif kind == "done":
            final = payload
    return "".join(tokens), final


# ======================================================================
print("=" * 60)
print("SECTION 6: Jalur Query Inti (Live)")
print("=" * 60)

# 6a: Normal query
print("\n--- 6a: Normal domain query ---")
print("  Query: 'What is the minimum plate thickness for shell plating?'")
t0 = time.time()
text, result = run_query("What is the minimum plate thickness for shell plating?")
elapsed = time.time() - t0
print(f"  Answer ({len(text)} chars, {elapsed:.1f}s): {text[:200]}...")

check("Normal query: has answer text", len(text) > 20, f"len={len(text)}")
check("Normal query: result is ChainStreamResult", isinstance(result, ChainStreamResult))
check("Normal query: has sources", result is not None and len(result.sources) > 0,
      f"sources={len(result.sources) if result else 0}")
check("Normal query: not rejected", result is not None and not result.rejected,
      f"rejected={result.rejected if result else '?'}")
check("Normal query: has timings", result is not None and bool(result.timings),
      f"timings={result.timings if result else '?'}")
check("Normal query: intent is rules_qa",
      result is not None and result.intent is not None and result.intent.kind == "rules_qa",
      f"intent={result.intent if result else '?'}")
if result and result.sources:
    print(f"  Sources ({len(result.sources)}):")
    for i, s in enumerate(result.sources[:3], 1):
        print(f"    {i}. Sec {s.section_no} | {s.section_title} | p.{s.page_start}")

# 6b: Calculation query
print("\n--- 6b: Calculation query ---")
print("  Query: 'hitung modulus penampang balok T dengan b=200mm h=400mm'")
t0 = time.time()
text, result = run_query("hitung modulus penampang balok T dengan b=200mm h=400mm")
elapsed = time.time() - t0
print(f"  Response ({len(text)} chars, {elapsed:.1f}s): {text[:300]}")

check("Calc query: has response text", len(text) > 10, f"len={len(text)}")
check("Calc query: result exists", result is not None)
if result:
    check("Calc query: intent is calculation",
          result.intent is not None and result.intent.kind == "calculation",
          f"intent={result.intent}")
    check("Calc query: no sources (empty list)", len(result.sources) == 0,
          f"sources={len(result.sources)}")
    check("Calc query: not rejected", not result.rejected)
    check("Calc query: mentions Fase 4 or stub", "fase 4" in text.lower() or "phase 4" in text.lower()
          or "pending" in text.lower() or "belum" in text.lower() or "calculation" in text.lower(),
          f"text={text[:200]}")

# 6c: Out-of-domain query
print("\n--- 6c: Out-of-domain query ---")
print("  Query: 'Bagaimana cara membuat kue coklat?'")
t0 = time.time()
text, result = run_query("Bagaimana cara membuat kue coklat?")
elapsed = time.time() - t0
print(f"  Response ({len(text)} chars, {elapsed:.1f}s): {text[:300]}")

check("OOD query: has response", len(text) > 10, f"len={len(text)}")
check("OOD query: result exists", result is not None)
if result:
    check("OOD query: rejected OR insufficient context",
          result.rejected or "insufficient" in text.lower() or "tidak cukup" in text.lower()
          or "tidak dapat" in text.lower() or "bki" in text.lower(),
          f"rejected={result.rejected}, text={text[:200]}")

# 6d: Fast mode query
print("\n--- 6d: Fast mode query ---")
print("  Query: 'What is buckling?' (mode=fast)")
t0 = time.time()
text, result = run_query("What is buckling?", mode="fast")
elapsed = time.time() - t0
print(f"  Answer ({len(text)} chars, {elapsed:.1f}s): {text[:200]}...")

check("Fast mode: has answer", len(text) > 10, f"len={len(text)}")
check("Fast mode: result exists", result is not None)
if result:
    check("Fast mode: not rejected", not result.rejected)

# ======================================================================
# SUMMARY
print("\n" + "=" * 60)
total = PASS + FAIL
print(f"RESULTS: {PASS} passed, {FAIL} failed, {total} total")
print("=" * 60)
if FAIL > 0:
    sys.exit(1)
