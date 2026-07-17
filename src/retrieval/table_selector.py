"""Deterministic table-row selector for numerical rules tables — SAFE EDITION.

Safety-gated: semantic topic check → unit normalization → numeric match.
Categorical/text matching disabled — reserved for future design.
No LLM, no table/topic hardcodes.
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

STOP_WORDS = {
    "berapa", "apa", "untuk", "dengan", "pada", "dalam", "yang", "dan", "atau",
    "how", "what", "the", "for", "with", "from", "and", "of", "is", "are",
    "a", "an", "in", "to", "at", "by", "its", "it", "be",
}

GENERIC_WORDS = {
    "table", "rule", "rules", "requirement", "requirements",
    "minimum", "maximum", "factor", "factors", "condition", "conditions",
    "element", "elements", "member", "members", "category", "categories",
    "following", "below", "above", "according",
    "mm", "cm", "m", "kg", "t", "deg",
}

_UNIT_WORDS = {"mm", "cm", "m", "kg", "t", "inch", "in", "%", "n/mm2", "n/mm²", "deg", "°c"}


def _norm(s: str) -> str:
    for k, v in _UNICODE_OPS.items():
        s = s.replace(k, v)
    return s.lower().strip()


def _replace_ops(s: str, lang: str) -> str:
    ops = _ID_TEXT_OPS if lang == "id" else _EN_TEXT_OPS
    for phrase, op in sorted(ops.items(), key=lambda x: -len(x[0])):
        s = s.replace(phrase, op)
    return s


@dataclass
class SelectionResult:
    selected: bool
    row_text: str
    value_text: str
    reason: str
    table_ref: str


# ═══════════════════════════════════════════════════════════════════
# Unit normalization
# ═══════════════════════════════════════════════════════════════════

_LENGTH_CONV = {"mm": 1.0, "cm": 10.0, "m": 1000.0, "inch": 25.4, "in": 25.4}

_DIMENSION_MAP = {
    "mm": "length", "cm": "length", "m": "length", "inch": "length", "in": "length",
    "%": "percent", "percent": "percent", "persen": "percent",
    "kg": "mass", "t": "mass", "ton": "mass",
    "n/mm2": "pressure", "n/mm²": "pressure",
    "deg": "angle", "°c": "temperature", "celsius": "temperature",
    "kn": "force", "n": "force",
    "dwt": "mass",
}


def _extract_unit(s: str) -> Optional[str]:
    s = s.lower().strip()
    # Find units in brackets, or as word token, or paired with a number.
    m = re.search(r"\[(mm|cm|m|%|t|deg|kg|kn|n|dwt)\]", s)
    if m:
        return m.group(1)
    m = re.search(r"\b(n/mm[²2]|°c|inch)\b", s)
    if m:
        raw = m.group(1).lower()
        return {"persen": "%", "percent": "%"}.get(raw, raw)
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(mm|cm|m|%|kg|t|deg|kn|n|dwt)\b", s)
    if m:
        return m.group(2).lower()
    m = re.search(r"\bpercent\b|\bpersen\b", s)
    if m:
        return "%"
    m = re.search(r"\b(\d+(?:[.,]\d+)?)(%)\b", s)
    if m:
        return "%"
    return None


def _dimension(unit: Optional[str]) -> Optional[str]:
    if unit is None:
        return None
    return _DIMENSION_MAP.get(unit)


def _to_mm(value: float, unit: str) -> Optional[float]:
    """Convert length value to mm. Returns None for unsupported/non-length units."""
    dim = _dimension(unit)
    if dim == "length":
        factor = _LENGTH_CONV.get(unit)
        return value * factor if factor is not None else None
    return None


def _convert_value(value: float, query_unit: Optional[str], table_unit: Optional[str]) -> Optional[float]:
    """Convert query value into table-compatible value. Returns None if incompatible."""
    if query_unit is None and table_unit is None:
        return value
    if query_unit is None or table_unit is None:
        if query_unit is None and table_unit is not None:
            # Query has no unit, table has unit → check if table is length,
            # query might imply mm from parameter name context. But unitless+
            # unit mismatch is NOT safe. Fallback.
            return None
        return None
    qd = _dimension(query_unit)
    td = _dimension(table_unit)
    if qd is None or td is None:
        return None
    if qd != td:
        return None
    if qd == "length":
        return _to_mm(value, query_unit)
    if qd == "percent":
        return value
    if qd == "mass":
        return value
    return value


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


# ═══════════════════════════════════════════════════════════════════
# Semantic topic gate
# ═══════════════════════════════════════════════════════════════════

def _discriminative_tokens(text: str) -> set[str]:
    """Extract discriminative technical words from text, excluding stop/generic words."""
    words = set()
    for w in re.findall(r"\b\w+\b", text.lower()):
        w = w.strip(".,:;()[]\"'")
        if not w or len(w) < 2:
            continue
        if w in STOP_WORDS:
            continue
        if w in GENERIC_WORDS:
            continue
        words.add(w)
    # Also include multi-digit tokens and units (may not match \w)
    for m in re.finditer(r"\b(\d{2,})\b", text.lower()):
        words.add(m.group(1))
    return words


def _semantic_overlap(query_text: str, table_header_text: str) -> int:
    """Count number of discriminative NON-UNIT tokens shared between query and table headers.

    Unit tokens (mm, cm, m, etc.) are explicitly excluded — they establish
    dimension compatibility but NOT semantic topic. A table about velocity
    in [mm/s] shares the unit 'mm' with a query about plate thickness in mm,
    but that does not make them semantically related.
    """
    q_tokens = _discriminative_tokens(query_text)
    h_tokens = _discriminative_tokens(table_header_text)
    shared = q_tokens & h_tokens
    # Remove unit-only tokens from the overlap count
    non_unit = shared - _UNIT_WORDS
    return len(non_unit)


# ═══════════════════════════════════════════════════════════════════
# Condition parsing
# ═══════════════════════════════════════════════════════════════════

def _parse_query_condition(query: str, lang: str):
    """Parse numeric condition + unit from query. Returns (op, value, v2, unit) or None."""
    q = _norm(query)
    q = _replace_ops(q, lang)
    # Find the first numeric value
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(\S*)", q)
    if not m:
        return None
    val1 = float(m.group(1).replace(",", "."))
    suffix = m.group(2).strip().lower()
    # Try to extract a known unit from suffix
    KNOWN_UNITS = ["n/mm2", "n/mm²", "°c", "inch", "percent", "persen",
                   "dwt", "kn", "mm", "cm", "m", "%", "kg", "t", "deg", "n"]
    unit = None
    for ku in KNOWN_UNITS:
        if suffix.startswith(ku):
            unit = ku
            break
    UNIT_ALIASES = {"persen": "%", "percent": "%", "in": "inch", "°c": "deg"}
    if unit:
        unit = UNIT_ALIASES.get(unit, unit)
    # Parse operator from prefix
    val_start = m.start()
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
    return op, val1, None, unit


def _parse_row_cond(cell: str):
    c = _norm(cell)
    # Strip leading variable prefix: "T <= 500" → "<= 500"
    stripped = re.sub(r"^[a-z_][a-z0-9_]*\s*", "", c)
    
    text_ops = [("or less", "<="), ("or fewer", "<="), ("or below", "<"),
                ("or more", ">="), ("or greater", ">="), ("or above", ">")]
    for to, so in text_ops:
        if to in stripped:
            v = _parse_num(stripped.split(to)[0].strip())
            return so, v
    for op in [">=", "<=", "!=", "<", ">", "="]:
        if stripped.startswith(op):
            return op, _parse_num(stripped[len(op):].strip())
    # Compound: "500 < T <= 1500" → try both bounds, use the <= as primary
    m_compound = re.search(r"(\S+)\s*<\s*[a-z_]+\s*<=\s*(\d+[.,]?\d*)", c)
    if m_compound:
        return "<=", _parse_num(m_compound.group(2))
    # Single inequality with variable: "T <= 500" → strip variable, retry
    stripped2 = re.sub(r"^.*?([<>=]+)\s*", r"\1", c)
    for op in [">=", "<=", "!=", "<", ">", "="]:
        if stripped2.startswith(op):
            return op, _parse_num(stripped2[len(op):].strip())
    v = _parse_num(c)
    if v is not None:
        return "=", v
    return None, None


def _eval_condition(query_val: float, row_op: Optional[str], row_val: Optional[float]) -> bool:
    if row_op is None or row_val is None:
        return False
    if row_op in ("<=", "<"):
        return query_val <= row_val
    elif row_op in (">=", ">"):
        return query_val >= row_val
    elif row_op == "=":
        return abs(query_val - row_val) < 1e-6
    return False


def _tightest(candidates, qop):
    valid = [c for c in candidates if c[1] is not None]
    if not valid:
        return None
    if qop in ("<=", "<", "="):
        return min(valid, key=lambda x: x[1])
    return max(valid, key=lambda x: x[1])


def _table_header_line(table_content: str) -> str:
    """Extract the first data line (headers) for semantic matching."""
    lines = [l for l in table_content.split("\n") if l.strip() and not l.startswith("[")]
    return lines[0] if lines else ""


# ═══════════════════════════════════════════════════════════════════
# Table-level selection (refactored from _try_select)
# ═══════════════════════════════════════════════════════════════════

def _parse_table(table_content: str):
    """Parse pipe-delimited table into (headers, rows, cond_col, val_col). Returns None tuples on failure."""
    lines = [l for l in table_content.split("\n") if l.strip() and not l.startswith("[")]
    if len(lines) < 2:
        return None, None, None, None
    headers = [h.strip() for h in re.split(r"\s*\|\s*", lines[0])]
    rows = []
    for line in lines[1:]:
        cells = [c.strip() for c in re.split(r"\s*\|\s*", line)]
        if all(c == "" for c in cells):
            continue
        rows.append(cells)
    if not rows or len(headers) < 2:
        return None, None, None, None
    # Determine condition column: prefer column with comparison operators (≠ =)
    cond_col = 0
    found_in_ci0 = False
    for ci in range(len(headers)):
        has_comp_op = False
        has_any = False
        for row in rows:
            if ci >= len(row):
                continue
            op, val = _parse_row_cond(row[ci])
            if op is not None and val is not None:
                has_any = True
                if op != "=":
                    has_comp_op = True
        if has_comp_op:
            cond_col = ci
            break
        elif has_any:
            if ci == 0:
                found_in_ci0 = True
            elif not found_in_ci0:
                cond_col = ci
                found_in_ci0 = True
            break
        elif has_any and cond_col == 0 and ci > 0:
            # First column with any parseable numeric wins
            cond_col = ci
    val_col = cond_col + 1 if cond_col + 1 < len(headers) else 0
    return headers, rows, cond_col, val_col


def _table_condition_unit(table_content: str) -> Optional[str]:
    """Extract unit from table's condition column header."""
    parsed = _parse_table(table_content)
    if parsed[0] is None:
        return None
    headers, _, cond_col, _ = parsed
    if cond_col >= len(headers):
        return None
    return _extract_unit(headers[cond_col])


# ═══════════════════════════════════════════════════════════════════
# Main safe selector
# ═══════════════════════════════════════════════════════════════════

_MIN_SEMANTIC_OVERLAP = 1


def _try_select_one_table(table_content: str, query: str, lang: str):
    """Core safe selection for a single table. Returns (row_cell, value, label) or None.

    Safety gates (in order):
      1. Table parse: headers + rows must exist.
      2. Numeric condition: query must have extractable numeric condition + unit.
      3. Unit compatibility: query unit must be same dimension as table condition unit.
      4. Value conversion: query value converted to table unit.
      5. Semantic overlap: at least _MIN_SEMANTIC_OVERLAP discriminative tokens shared.
      6. Row matching: at least one row satisfies condition.
      7. Tightest unambiguous match.
    """
    parsed = _parse_table(table_content)
    if parsed[0] is None:
        return None
    headers, rows, cond_col, val_col = parsed

    cond = _parse_query_condition(query, lang)
    if cond is None:
        return None
    op, v1, _, query_unit = cond

    table_unit = _table_condition_unit(table_content)

    # Unit compatibility
    if query_unit and table_unit:
        qd = _dimension(query_unit)
        td = _dimension(table_unit)
        if qd is None or td is None:
            return None
        if qd != td:
            return None
    elif query_unit and not table_unit:
        return None
    # Unitless query + unitless table: OK, but require strong semantic overlap
    elif not query_unit and not table_unit:
        pass  # unitless path

    # Convert query value to table-compatible
    if query_unit and table_unit:
        qd = _dimension(query_unit)
        if qd == "length":
            conv = _to_mm(v1, query_unit)
            if conv is None:
                return None
            v1_norm = conv
        elif qd == "percent":
            v1_norm = v1
        else:
            v1_norm = v1
    elif not query_unit and not table_unit:
        v1_norm = v1
    else:
        return None

    # 5. Semantic overlap: query discriminative tokens must overlap table header tokens
    header_text = " ".join(headers)
    overlap = _semantic_overlap(query, header_text)
    if overlap < _MIN_SEMANTIC_OVERLAP:
        return None

    candidates = []
    for ri, row in enumerate(rows):
        if len(row) <= cond_col:
            continue
        rop, rv = _parse_row_cond(row[cond_col])
        if rop is None or rv is None:
            continue
        if _eval_condition(v1_norm, rop, rv):
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
    val_text = row[val_col] if val_col < len(row) else ""
    return row[cond_col], val_text, f"matched: {row[cond_col]} satisfies {op} {v1}"


def select_table_row(table_content: str, query_text: str, lang: str,
                     table_ref: str = "") -> SelectionResult:
    """Select exactly one table row deterministically (safe, numeric-only).

    Categorical/text-matching is DISABLED — reserved for future ontology design.
    Returns SelectionResult with selected=True only when all safety gates pass.
    """
    result = _try_select_one_table(table_content, query_text, lang)
    if result is not None:
        return SelectionResult(True, result[0], result[1], result[2], table_ref)
    return SelectionResult(False, "", "", "fallback", table_ref)
