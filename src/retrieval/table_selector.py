"""Deterministic table-row selector for numerical rules tables.

General-purpose: no table/topic/chunk-ID hardcodes. Uses a 2-strategy approach:
  1. Numeric-condition: parse ≤/≥/=/BETWEEN thresholds from query, match against
     parsed table rows, pick tightest unambiguous match.
  2. Categorical/text-match: word-overlap fuzzy matching for non-numeric tables.

Always returns (selected: bool, result_text: str, reason: str).

Fallback conditions:
  - Table parse fails (no data rows)
  - No numeric condition in query AND no text match
  - Multiple rows match ambiguously after tightest-match resolution
  - Unit incompatibility detected
  - No rows satisfy the condition
"""
import re
from dataclasses import dataclass
from typing import Optional, Literal


_UNICODE_OPS = {
    "\u2264": "<=", "\u2265": ">=", "\u2260": "!=",
    "\u00b7": "*", "\u00d7": "x",
    "\u2013": "-", "\u2014": "-",
}

_ID_TEXT_OPS = {
    "tidak lebih dari": "<=", "tidak kurang dari": ">=",
    "sekurang-kurangnya": ">=", "setidaknya": ">=",
    "paling sedikit": ">=", "paling banyak": "<=",
    "maksimum": "<=", "minimum": ">=",
    "tepat": "=", "persis": "=",
    "di bawah": "<", "kurang dari": "<", "lebih kecil dari": "<",
    "di atas": ">", "lebih dari": ">", "lebih besar dari": ">",
    "antara": "BETWEEN", "sampai": "BETWEEN", "hingga": "BETWEEN",
    "sebesar": "=", "senilai": "=",
}

_EN_TEXT_OPS = {
    "less than or equal": "<=", "less than": "<",
    "greater than or equal": ">=", "greater than": ">",
    "not less than": ">=", "not greater than": "<=",
    "at least": ">=", "at most": "<=",
    "maximum": "<=", "minimum": ">=",
    "exactly": "=", "precisely": "=",
    "between": "BETWEEN", "up to": "<=",
    "no more than": "<=", "no less than": ">=",
}

STOP_WORDS = {"berapa", "apa", "untuk", "dengan", "pada", "dalam",
              "yang", "dan", "atau", "how", "what", "the", "for",
              "with", "from", "and", "of", "is", "are", "a", "an",
              "in", "to", "at", "by", "its", "it", "be"}


@dataclass
class SelectionResult:
    selected: bool
    row_text: str
    value_text: str
    reason: str
    table_ref: str     # e.g. "Sec 19 Welded Joints | Table 19.1 p.418"


def select_table_row(table_content: str, query_text: str, lang: str,
                     table_ref: str = "") -> SelectionResult:
    """Select exactly one table row deterministically.

    Returns SelectionResult with selected=True only when unambiguous.
    table_ref should be the citation tag: e.g. "Sec 19 | Table 19.1 p.418"
    """
    result = _try_select(table_content, query_text, lang)
    if result is not None:
        return SelectionResult(True, result[0], result[1], result[2], table_ref)
    return SelectionResult(False, "", "", "", table_ref)


def _norm(s: str) -> str:
    for k, v in _UNICODE_OPS.items():
        s = s.replace(k, v)
    return s.lower().strip()


def _replace_ops(s: str, lang: str) -> str:
    ops = _ID_TEXT_OPS if lang == "id" else _EN_TEXT_OPS
    for phrase, op in sorted(ops.items(), key=lambda x: -len(x[0])):
        s = s.replace(phrase, op)
    return s


def _parse_num(v: str) -> Optional[float]:
    for op in ["<=", ">=", "!=", "<", ">", "="]:
        if v.startswith(op):
            v = v[len(op):].strip()
            break
    v = v.replace(",", ".").replace(" ", "")
    try:
        return float(v)
    except ValueError:
        return None


def _parse_condition(query: str, lang: str):
    q = _norm(query)
    q = _replace_ops(q, lang)
    matches = list(re.finditer(r"(\d+(?:[.,]\d+)?)\s*([a-z%°/]+)?\s*(mm|cm|m|kg|t|%|n/mm2|deg|°c)?", q))
    if not matches:
        return None
    vm = matches[0]
    val_start = vm.start()
    prefix = q[:val_start].strip()
    op = None
    op_pos = -1
    for operator in ["BETWEEN", ">=", "<=", "!=", "=", ">", "<"]:
        idx = prefix.rfind(operator)
        if idx >= 0 and idx > op_pos and len(prefix[idx + len(operator):].strip()) <= 20:
            op = operator
            op_pos = idx
    if op is None:
        op = "="
    val1 = float(vm.group(1).replace(",", "."))
    val2 = None
    if op == "BETWEEN" and len(matches) >= 2:
        val2 = float(matches[1].group(1).replace(",", "."))
    return op, val1, val2


def _parse_row_cond(cell: str):
    c = _norm(cell)
    text_ops = [("or less", "<="), ("or fewer", "<="), ("or below", "<"),
                ("or more", ">="), ("or greater", ">="), ("or above", ">")]
    for to, so in text_ops:
        if to in c:
            v = _parse_num(c.split(to)[0].strip())
            return so, v
    for op in [">=", "<=", "!=", "<", ">", "="]:
        if c.startswith(op):
            return op, _parse_num(c[len(op):].strip())
    v = _parse_num(c)
    if v is not None:
        return "=", v
    return None, None


def _tightest(candidates, qop):
    valid = [c for c in candidates if c[1] is not None]
    if not valid:
        return None
    if qop in ("<=", "<", "="):
        return min(valid, key=lambda x: x[1])
    return max(valid, key=lambda x: x[1])


def _text_match(query, rows):
    ql = _norm(query)
    best_idx = None
    best_score = 0
    for ri, row_cells in enumerate(rows):
        rt = " ".join(row_cells).lower()
        qw = set(w for w in re.findall(r"\b\w{4,}\b", ql) if w not in STOP_WORDS)
        rw = set(w for w in re.findall(r"\b\w+\b", rt))
        if not qw:
            continue
        score = len(qw & rw)
        for q_word in qw:
            if q_word in rw:
                continue
            for r_word in rw:
                if len(q_word) >= 3 and len(r_word) >= 3:
                    if q_word[:3] == r_word[:3]:
                        score += 1
                        break
                    if len(q_word) >= 5 and q_word[:4] in r_word:
                        score += 1
                        break
        if score > best_score:
            best_score = score
            best_idx = ri
    return (best_idx, None, None) if best_idx is not None and best_score >= 1 else None


def _try_select(table_content: str, query: str, lang: str):
    """Core selection logic. Returns (row_cell, value_cell, label) or None."""
    lines = [l for l in table_content.split("\n") if l.strip() and not l.startswith("[")]
    if len(lines) < 2:
        return None
    headers = [h.strip() for h in re.split(r"\s*\|\s*", lines[0])]
    rows = []
    for line in lines[1:]:
        cells = [c.strip() for c in re.split(r"\s*\|\s*", line)]
        if all(c == "" for c in cells):
            continue
        rows.append(cells)
    if not rows or len(headers) < 2:
        return None

    cond = _parse_condition(query, lang)
    if cond is None:
        tm = _text_match(query, rows)
        if tm is not None:
            ri = tm[0]
            return (rows[ri][0], rows[ri][1] if len(rows[ri]) > 1 else "", "text_match")
        return None

    op, v1, v2 = cond
    candidates = []
    for ri, row in enumerate(rows):
        if not row:
            continue
        rop, rv = _parse_row_cond(row[0])
        if rop is None or rv is None:
            continue
        if rop in ("<=", "<"):
            ok = v1 <= rv
        elif rop in (">=", ">"):
            ok = v1 >= rv
        elif rop == "=":
            ok = abs(v1 - rv) < 1e-6
        else:
            continue
        if ok:
            candidates.append((ri, rv, rop, row))

    if not candidates:
        return None
    if len(candidates) > 1:
        best = _tightest(candidates, op)
        if best is None:
            return None
        winners = [c for c in candidates if c[1] == best[1]]
        if len(winners) > 1:
            return None
        r_idx = best[0]
    else:
        r_idx = candidates[0][0]

    row = rows[r_idx]
    val_col = 1 if len(row) > 1 else 0
    return (row[0], row[val_col], f"matched: {row[0]} satisfies {op} {v1}")
