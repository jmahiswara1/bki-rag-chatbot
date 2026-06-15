"""Golden evaluation harness for BKI RAG chatbot.

Loads eval/golden_set.yaml, runs each entry through chain_answer_stream,
computes metrics, and reports results.

Usage:
    python -m eval.run_eval              # run all entries
    python -m eval.run_eval --ids a,b,c  # run specific entry ids
"""
import argparse
import re
import sys
import time

import yaml

from src.llm.chain import chain_answer_stream


# ---------- Metrics ----------

def classify_entry(entry: dict) -> str:
    """Classify entry into metric category."""
    if entry.get("expected_result"):
        return "calc-value"
    if entry.get("expect_error"):
        return "calc-error"
    if entry.get("expect_clarification"):
        return "calc-clarify"
    if entry.get("should_reject"):
        return "guardrail"
    return "rules_qa"


def eval_calc_value(result, entry: dict) -> tuple[bool, str]:
    """Evaluate calculation with expected numeric result."""
    answer = result.answer or ""
    
    # Parse "Result: X unit" from answer
    match = re.search(r"Result:\s*([\d.]+)\s*(\w+)", answer, re.IGNORECASE)
    if not match:
        return False, "no Result: line found"
    
    value = float(match.group(1))
    unit = match.group(2).lower()
    
    expected = entry["expected_result"]
    exp_value = expected["value"]
    exp_unit = expected["unit"].lower()
    tol = expected.get("tol", 0.01)
    
    if abs(value - exp_value) > tol:
        return False, f"value {value} != {exp_value} (tol={tol})"
    
    if unit != exp_unit:
        return False, f"unit {unit} != {exp_unit}"
    
    return True, ""


def eval_calc_error(result, entry: dict) -> tuple[bool, str]:
    """Evaluate calculation error (division by zero)."""
    answer = result.answer or ""
    # Check for division-by-zero message
    if "Pembagian nol / hasil tak hingga" in answer or "division by zero" in answer.lower():
        return True, ""
    return False, "no division-by-zero message found"


def eval_calc_clarify(result, entry: dict) -> tuple[bool, str]:
    """Evaluate calculation clarification (multiple formulas listed)."""
    answer = result.answer or ""
    # Check for clarification message
    if "matching formulas" in answer.lower() or "matching formula" in answer.lower():
        return True, ""
    return False, "no clarification message found"


def _norm(s: str) -> str:
    """Normalize string for keyword matching: lowercase and comma->dot."""
    return s.lower().replace(",", ".")


def eval_rules_qa(result, entry: dict) -> tuple[bool, str]:
    """Evaluate rules Q&A entry.
    
    PASS criteria: retrieval_hit AND lang_ok (keyword NOT a gate).
    Keyword matching is computed separately for reporting only.
    """
    failures = []
    
    # Check retrieval hit
    expected_sources = entry.get("expected_sources", [])
    retrieval_hit = True
    if expected_sources:
        expected_sections = {s["section_no"] for s in expected_sources}
        result_sections = {s.section_no for s in result.sources}
        if not (expected_sections & result_sections):
            retrieval_hit = False
            failures.append(f"retrieval miss: expected {expected_sections}, got {result_sections}")
    
    # Check language
    lang_ok = result.language == entry.get("lang")
    if not lang_ok:
        failures.append(f"lang {result.language} != {entry.get('lang')}")
    
    # PASS = retrieval_hit AND lang_ok (keyword NOT a gate)
    if failures:
        return False, "; ".join(failures)
    return True, ""


def eval_rules_qa_keywords(result, entry: dict) -> bool:
    """Check keyword matching separately for reporting (not used for PASS)."""
    must_include = entry.get("must_include", [])
    answer = result.answer or ""
    answer_norm = _norm(answer)
    return all(_norm(kw) in answer_norm for kw in must_include)


def eval_guardrail(result, entry: dict) -> tuple[bool, str]:
    """Evaluate guardrail rejection."""
    if result.rejected:
        return True, ""
    return False, "not rejected"


# ---------- Main ----------

def main():
    # Configure UTF-8 output to handle Unicode characters (e.g. ℓ, σ, etc.)
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8')
    
    parser = argparse.ArgumentParser(description="BKI RAG chatbot golden evaluation")
    parser.add_argument("--ids", type=str, help="Comma-separated entry ids to run")
    parser.add_argument("--debug", action="store_true", help="Print raw diagnostic fields, skip scoring")
    args = parser.parse_args()
    
    # Load golden set
    with open("eval/golden_set.yaml", "r", encoding="utf-8") as f:
        entries = yaml.safe_load(f)
    
    # Filter by ids if specified
    if args.ids:
        ids = set(args.ids.split(","))
        entries = [e for e in entries if e["id"] in ids]
    
    print(f"Running {len(entries)} entries...\n")
    
    results = []
    total_time = 0.0
    
    for entry in entries:
        entry_id = entry["id"]
        category = classify_entry(entry)
        
        print(f"[{entry_id}] {entry['question'][:60]}...")
        
        try:
            t0 = time.time()
            # Consume stream to get final result
            result = None
            for kind, payload in chain_answer_stream(entry["question"], mode="default"):
                if kind == "done":
                    result = payload
                    break
            
            elapsed = time.time() - t0
            total_time += elapsed
            
            if result is None:
                results.append({
                    "id": entry_id,
                    "category": category,
                    "pass": False,
                    "reason": "no result from stream",
                    "elapsed": elapsed,
                })
                print(f"  FAIL: no result\n")
                continue
            
            # Debug mode: print raw fields, skip scoring
            if args.debug:
                print(f"  id: {entry_id}")
                print(f"  intent: kind={result.intent.kind}, confidence={result.intent.confidence}, source={result.intent.source}")
                print(f"  rejected: {result.rejected}, reject_reason: {result.reject_reason or '(none)'}")
                print(f"  language: {result.language}, en_query: {result.en_query[:100] if result.en_query else '(none)'}")
                print(f"  len(sources): {len(result.sources)}")
                if result.sources:
                    top_sources = [(s.section_no, round(s.score, 3)) for s in result.sources[:8]]
                    print(f"  top sources: {top_sources}")
                else:
                    print(f"  top sources: []")
                answer_preview = result.answer[:200] if result.answer else "(empty)"
                print(f"  answer (first 200 chars): {answer_preview}")
                print()
                continue
            
            # Evaluate based on category
            keyword_ok = None
            if category == "calc-value":
                passed, reason = eval_calc_value(result, entry)
            elif category == "calc-error":
                passed, reason = eval_calc_error(result, entry)
            elif category == "calc-clarify":
                passed, reason = eval_calc_clarify(result, entry)
            elif category == "rules_qa":
                passed, reason = eval_rules_qa(result, entry)
                keyword_ok = eval_rules_qa_keywords(result, entry)
            elif category == "guardrail":
                passed, reason = eval_guardrail(result, entry)
            else:
                passed, reason = False, f"unknown category: {category}"
            
            results.append({
                "id": entry_id,
                "category": category,
                "pass": passed,
                "reason": reason,
                "elapsed": elapsed,
                "keyword_ok": keyword_ok,
            })
            
            status = "PASS" if passed else "FAIL"
            print(f"  {status}: {reason}\n")
            
        except Exception as e:
            results.append({
                "id": entry_id,
                "category": category,
                "pass": False,
                "reason": f"exception: {e}",
                "elapsed": 0.0,
            })
            print(f"  FAIL: exception: {e}\n")
    
    # ---------- Summary ----------
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    # Per-category summary
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"pass": 0, "total": 0, "total_time": 0.0}
        categories[cat]["total"] += 1
        categories[cat]["total_time"] += r["elapsed"]
        if r["pass"]:
            categories[cat]["pass"] += 1
    
    print("\nPer-category:")
    for cat in sorted(categories.keys()):
        c = categories[cat]
        rate = c["pass"] / c["total"] * 100 if c["total"] > 0 else 0
        avg_time = c["total_time"] / c["total"] if c["total"] > 0 else 0
        print(f"  {cat:20s}: {c['pass']:2d}/{c['total']:2d} ({rate:5.1f}%)  avg={avg_time:.1f}s")
    
    # Rules Q&A breakdown
    rules_results = [r for r in results if r["category"] == "rules_qa"]
    if rules_results:
        print("\nRules Q&A breakdown:")
        retrieval_hits = 0
        lang_ok_count = 0
        keyword_ok_count = 0
        for r in rules_results:
            # Check retrieval and language from reason string
            reason = r["reason"]
            if "retrieval miss" not in reason:
                retrieval_hits += 1
            if "lang" not in reason:
                lang_ok_count += 1
            # Use stored keyword_ok value
            if r.get("keyword_ok"):
                keyword_ok_count += 1
        
        total_rules = len(rules_results)
        print(f"  retrieval-hit: {retrieval_hits}/{total_rules} ({retrieval_hits/total_rules*100:.1f}%)")
        print(f"  language-match: {lang_ok_count}/{total_rules} ({lang_ok_count/total_rules*100:.1f}%)")
        print(f"  keyword-match: {keyword_ok_count}/{total_rules} ({keyword_ok_count/total_rules*100:.1f}%)")
    
    # Overall
    total_pass = sum(1 for r in results if r["pass"])
    total_entries = len(results)
    overall_rate = total_pass / total_entries * 100 if total_entries > 0 else 0
    avg_total_time = total_time / total_entries if total_entries > 0 else 0
    
    print(f"\nOverall: {total_pass}/{total_entries} ({overall_rate:.1f}%)  avg={avg_total_time:.1f}s")
    
    # Failures table
    failures = [r for r in results if not r["pass"]]
    if failures:
        print(f"\nFAILURES ({len(failures)}):")
        for r in failures:
            print(f"  {r['id']:40s} [{r['category']:15s}] {r['reason']}")
    
    print(f"\nTotal runtime: {total_time:.1f}s")


if __name__ == "__main__":
    main()
