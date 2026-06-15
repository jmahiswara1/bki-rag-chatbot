# tests/manual/smoke_calc_live.py
# Manual smoke test for the calculation short-circuit, end-to-end.
# Requires local Ollama and Supabase reachable. Run from repo root:
#   python -m tests.manual.smoke_calc_live

from src.llm.chain import chain_answer_stream

CASES = [
    ("calc dot", "Hitung tebal pelat dek dengan a=0.6, pL=10, k=1, tK=1", "~3.30 mm"),
    ("calc comma", "Hitung tebal pelat dek dengan a=0,6, pL=10, k=1, tK=1", "~3.30 mm (cek koma)"),
    ("calc web", "Berapa tebal web floor plate dengan h=400", "7.0 mm"),
    ("calc speed", "Ambang kecepatan forecastle dengan L=100", "16 kn"),
    ("edge div0", "Hitung beban roda dengan Q=100, n=0", "warning, no crash"),
    ("edge default", "Hitung beban roda dengan Q=100, n=4", "25 kN (av default 0)"),
    ("ambiguous", "Berapa tebal pelat?", "clarify / list, no bogus calc"),
]


def run(query, mode="default"):
    result = None
    statuses = []
    for kind, payload in chain_answer_stream(query, mode=mode):
        if kind == "status":
            statuses.append(payload)
        elif kind == "done":
            result = payload
    return statuses, result


def main():
    for label, query, expected in CASES:
        print("=" * 72)
        print(f"[{label}] {query}")
        print(f"  expect: {expected}")
        try:
            statuses, result = run(query)
        except Exception as e:
            print(f"  EXCEPTION: {type(e).__name__}: {e}")
            continue
        if result is None:
            print(f"  no done result; statuses={statuses}")
            continue
        intent = getattr(result.intent, "kind", result.intent)
        print(f"  intent={intent} rejected={result.rejected} reason={result.reject_reason}")
        print(f"  answer={result.answer!r}")


if __name__ == "__main__":
    main()
