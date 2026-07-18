"""Deterministic table-row selector for numerical rules tables — SAFE EDITION.

Safety-gated: semantic topic check → unit normalization → numeric match.
Categorical/text matching disabled — reserved for future design.
No LLM, no table/topic hardcodes.

Build 30: explicit predicate objects with two-sided (compound) range support.
A row condition is parsed into a Predicate (lower/upper bounds + inclusivity,
or an equality point). Selection evaluates the query value against BOTH
bounds; overlapping bounded ranges, gaps, duplicate ranges, and ambiguous
columns all fall back instead of speculating.

Build 30c: compound (two-sided) predicate path restricted to unambiguous
2-column tables. Multi-column tables (>2 logical columns) skip compound
rows but retain single-threshold selection (Build 29 behavior).
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
    "dwt": "mass", "tdw": "mass",
}


def _extract_unit(s: str) -> Optional[str]:
    s = s.lower().strip()
    # Find units in brackets, or as word token, or paired with a number.
    m = re.search(r"\[(mm|cm|m|%|t|deg|kg|kn|n|dwt|tdw)\]", s)
    if m:
        u = m.group(1)
        return "dwt" if u == "tdw" else u
    # Parenthesized units, e.g. "Thickness (mm)" (corpus attested in Sec 39)
    m = re.search(r"\((mm|cm|m|%|t|deg|kg|kn|n|dwt|tdw)\)", s)
    if m:
        u = m.group(1)
        return "dwt" if u == "tdw" else u
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
# Explicit row predicates (Build 30)
# ═══════════════════════════════════════════════════════════════════

_NUM = r"\d+(?:[.,]\d+)?"
_VAR = r"[a-z_][a-z0-9_]*"


@dataclass
class Predicate:
    """Explicit row predicate with two-sided bound support.

    lower/upper hold numeric bounds; lower_inc/upper_inc mark inclusivity.
    eq holds an equality point (bare-number rows). raw keeps the verbatim
    cell text for provenance/evidence.
    """
    raw: str
    lower: Optional[float] = None
    lower_inc: bool = False
    upper: Optional[float] = None
    upper_inc: bool = False
    eq: Optional[float] = None

    @property
    def is_point(self) -> bool:
        return self.eq is not None

    @property
    def is_compound(self) -> bool:
        return self.lower is not None and self.upper is not None

    def contains(self, v: float) -> bool:
        if self.eq is not None:
            return abs(v - self.eq) < 1e-6
        if self.lower is None and self.upper is None:
            return False
        if self.lower is not None:
            if self.lower_inc:
                if v < self.lower - 1e-9:
                    return False
            else:
                if v <= self.lower + 1e-9:
                    return False
        if self.upper is not None:
            if self.upper_inc:
                if v > self.upper + 1e-9:
                    return False
            else:
                if v >= self.upper - 1e-9:
                    return False
        return True

    def describe(self) -> str:
        if self.eq is not None:
            return f"= {self.eq}"
        lo = f"{'[' if self.lower_inc else '('}" \
             f"{self.lower if self.lower is not None else '-inf'}"
        hi = f"{self.upper if self.upper is not None else '+inf'}" \
             f"{']' if self.upper_inc else ')'}"
        return f"{lo}, {hi}"


def _parse_row_predicate(cell: str) -> Optional[Predicate]:
    """Parse a condition cell into a Predicate; None if ambiguous/malformed.

    Supported grammar (unicode-normalized, lowercase):
      a < x ≤ b        compound with explicit variable
      > a ≤ b          two-operator, no variable
      a < x            reverse single bound
      [x] op v         single bound with optional variable prefix
      v or less/more   textual bounds
      v                bare number → equality point
    Rejected (None): contradictory bounds, mixed directions, '!=',
    multiple numbers without operators, non-numeric text.
    """
    c = _norm(cell).strip()
    if not c:
        return None
    p = Predicate(raw=cell)

    # a < x ≤ b (explicit variable)
    m = re.fullmatch(rf"({_NUM})\s*(<=|<|>=|>)\s*{_VAR}\s*(<=|<|>=|>)\s*({_NUM})", c)
    if m:
        a, op1, op2, b = m.groups()
        a = _parse_num(a)
        b = _parse_num(b)
        if a is None or b is None:
            return None
        if op1 in ("<", "<=") and op2 in ("<", "<="):
            p.lower, p.lower_inc = a, op1 == "<="
            p.upper, p.upper_inc = b, op2 == "<="
        elif op1 in (">", ">=") and op2 in (">", ">="):
            p.lower, p.lower_inc = b, op2 == ">="
            p.upper, p.upper_inc = a, op1 == ">="
        else:
            return None  # mixed directions
        if p.lower > p.upper:
            return None  # contradictory
        return p

    # a < x (reverse single bound)
    m = re.fullmatch(rf"({_NUM})\s*(<=|<|>=|>)\s*{_VAR}", c)
    if m:
        a, op = m.groups()
        a = _parse_num(a)
        if a is None:
            return None
        if op == "<":
            p.lower, p.lower_inc = a, False
        elif op == "<=":
            p.lower, p.lower_inc = a, True
        elif op == ">":
            p.upper, p.upper_inc = a, False
        elif op == ">=":
            p.upper, p.upper_inc = a, True
        return p

    # op v op v (two operators, no variable) e.g. "> 100000 ≤ 150000"
    m = re.fullmatch(rf"(<=|<|>=|>)\s*({_NUM})\s+(<=|<|>=|>)\s*({_NUM})", c)
    if m:
        op1, a, op2, b = m.groups()
        a = _parse_num(a)
        b = _parse_num(b)
        if a is None or b is None:
            return None
        bounds = []
        for op, val in ((op1, a), (op2, b)):
            if op in ("<", "<="):
                bounds.append(("upper", val, op == "<="))
            else:
                bounds.append(("lower", val, op == ">="))
        lowers = [x for x in bounds if x[0] == "lower"]
        uppers = [x for x in bounds if x[0] == "upper"]
        if len(lowers) != 1 or len(uppers) != 1:
            return None
        p.lower, p.lower_inc = lowers[0][1], lowers[0][2]
        p.upper, p.upper_inc = uppers[0][1], uppers[0][2]
        if p.lower > p.upper:
            return None
        return p

    # textual suffixes: "40 or less", "75 or more"
    stripped = re.sub(rf"^{_VAR}\s*", "", c)
    for to, kind in (("or less", "upper_inc"), ("or fewer", "upper_inc"),
                     ("or below", "upper_exc"), ("or more", "lower_inc"),
                     ("or greater", "lower_inc"), ("or above", "lower_exc")):
        if to in stripped:
            v = _parse_num(stripped.split(to)[0].strip())
            if v is None:
                return None
            if kind == "upper_inc":
                p.upper, p.upper_inc = v, True
            elif kind == "upper_exc":
                p.upper, p.upper_inc = v, False
            elif kind == "lower_inc":
                p.lower, p.lower_inc = v, True
            else:
                p.lower, p.lower_inc = v, False
            return p

    # [x] op v
    m = re.fullmatch(rf"(<=|>=|!=|<|>|=)\s*({_NUM})", stripped)
    if m:
        op, v = m.groups()
        v = _parse_num(v)
        if v is None:
            return None
        if op == "<=":
            p.upper, p.upper_inc = v, True
        elif op == "<":
            p.upper, p.upper_inc = v, False
        elif op == ">=":
            p.lower, p.lower_inc = v, True
        elif op == ">":
            p.lower, p.lower_inc = v, False
        elif op == "=":
            p.eq = v
        else:
            return None  # '!=' unsupported
        return p

    # bare number → equality
    v = _parse_num(c)
    if v is not None:
        p.eq = v
        return p
    return None


def _parse_row_cond(cell: str):
    """Legacy adapter: reduce a predicate to a single (op, value) pair.

    Kept for backward compatibility with the single-threshold path and the
    existing table parser. Compound predicates collapse to their upper bound
    (same behavior as Build 29's lossy compound branch).
    """
    p = _parse_row_predicate(cell)
    if p is None:
        return None, None
    if p.eq is not None:
        return "=", p.eq
    if p.upper is not None:
        return ("<=", p.upper) if p.upper_inc else ("<", p.upper)
    if p.lower is not None:
        return (">=", p.lower) if p.lower_inc else (">", p.lower)
    return None, None


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


def _eval_condition(query_val: float, row_op: Optional[str], row_val: Optional[float]) -> bool:
    """Legacy single-bound evaluation, kept for reference/tests."""
    if row_op is None or row_val is None:
        return False
    if row_op in ("<=", "<"):
        return query_val <= row_val
    elif row_op in (">=", ">"):
        return query_val >= row_val
    elif row_op == "=":
        return abs(query_val - row_val) < 1e-6
    return False


def _tightest_match(preds: list[Predicate], matching: list[int]) -> Optional[int]:
    """Resolve multiple matched rows to a single row index, or None.

    Legitimate nesting of one-sided thresholds (≤4, ≤8, ≤12 …) resolves by
    the tightest bound. True ambiguity (tie, or a bounded two-sided range
    overlapping another matched row) returns None → caller falls back.
    """
    bounded = [i for i in matching if preds[i].is_compound]
    if bounded and len(matching) > 1:
        return None  # compound overlaps another matched row
    if len(bounded) > 1:
        return None
    uppers = [(preds[i].upper, i) for i in matching
              if preds[i].upper is not None]
    lowers = [(preds[i].lower, i) for i in matching
              if preds[i].lower is not None]
    if uppers:
        best = min(u for u, _ in uppers)
        winners = [i for u, i in uppers if u == best]
        return winners[0] if len(winners) == 1 else None
    if lowers:
        best = max(l for l, _ in lowers)
        winners = [i for l, i in lowers if l == best]
        return winners[0] if len(winners) == 1 else None
    return None


def _table_header_line(table_content: str) -> str:
    """Extract the first data line (headers) for semantic matching."""
    lines = [l for l in table_content.split("\n") if l.strip() and not l.startswith("[")]
    return lines[0] if lines else ""



from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple

@dataclass
class ColumnDescriptor:
    index: int
    parent_headers: List[str]
    leaf_header: str
    semantic_tokens: set[str]
    unit: Optional[str]
    dimension: Optional[str]
    source_text: str

def _is_data_line(cells: List[str]) -> bool:
    for c in cells:
        op, val = _parse_row_cond(c)
        if op is not None and val is not None:
            return True
    return False

def _parse_headers(lines: List[str]) -> Tuple[List[ColumnDescriptor], List[List[str]]]:
    hdr_lines = []
    data_lines = []
    
    is_data = False
    for l in lines:
        cells = [c.strip() for c in l.split("|")]
        if not is_data:
            is_data = _is_data_line(cells)
            
        if is_data:
            data_lines.append(cells)
        else:
            hdr_lines.append(cells)
            
    if not hdr_lines:
        return [], data_lines
        
    max_cols = max(len(h) for h in hdr_lines)
    for h in hdr_lines:
        while len(h) < max_cols:
            h.append("")
            
    cols = []
    for c_idx in range(max_cols):
        col_texts = []
        for r_idx in range(len(hdr_lines)):
            if c_idx < len(hdr_lines[r_idx]):
                cell = hdr_lines[r_idx][c_idx]
                if cell:
                    col_texts.append(cell)
        
        leaf = col_texts[-1] if col_texts else ""
        parents = col_texts[:-1] if len(col_texts) > 1 else []
        full_text = " ".join(col_texts)
        
        unit = None
        for t in col_texts:
            u = _extract_unit(t)
            if u:
                unit = u
                
        dim = _dimension(unit)
        tokens = _discriminative_tokens(full_text)
        
        cols.append(ColumnDescriptor(
            index=c_idx,
            parent_headers=parents,
            leaf_header=leaf,
            semantic_tokens=tokens,
            unit=unit,
            dimension=dim,
            source_text=full_text
        ))
    return cols, data_lines


def _parse_table(table_content: str):
    """Legacy compatible parser. Uses the hierarchical parser internally."""
    lines = [l for l in table_content.split("\n") if l.strip() and not l.startswith("[")]
    if len(lines) < 2:
        return None, None, None, None
        
    cols, data_lines = _parse_headers(lines)
    if not data_lines or not cols:
        # Fallback to simple split if no data rows found (prevent regression)
        headers = [h.strip() for h in re.split(r"\s*\|\s*", lines[0])]
        rows = []
        for line in lines[1:]:
            cells = [c.strip() for c in re.split(r"\s*\|\s*", line)]
            if all(c == "" for c in cells): continue
            rows.append(cells)
        if not rows or len(headers) < 2: return None, None, None, None
    else:
        headers = [c.source_text for c in cols]
        rows = data_lines
    
    ineq_cols = []
    numeric_cols = []
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
            ineq_cols.append(ci)
        elif has_any:
            numeric_cols.append(ci)
            
    if len(ineq_cols) > 1:
        return None, None, None, None
        
    if ineq_cols:
        cond_col = ineq_cols[0]
    elif numeric_cols:
        cond_col = numeric_cols[0]
    else:
        return None, None, None, None
        
    val_col = cond_col + 1 if cond_col + 1 < len(headers) else 0
    return headers, rows, cond_col, val_col


def _table_condition_unit(table_content: str) -> Optional[str]:
    parsed = _parse_table(table_content)
    if parsed[0] is None:
        return None
    headers, _, cond_col, _ = parsed
    if cond_col >= len(headers):
        return None
    return _extract_unit(headers[cond_col])


def _resolve_target(cols: List[ColumnDescriptor], query: str, cond_col_idx: int) -> Optional[int]:
    q_tokens = _discriminative_tokens(query)
    cond_tokens = cols[cond_col_idx].semantic_tokens
    
    target_q_tokens = q_tokens - cond_tokens
    
    candidates = []
    for c in cols:
        if c.index == cond_col_idx:
            continue
        overlap = c.semantic_tokens & target_q_tokens
        if overlap:
            candidates.append((c.index, overlap))
            
    if not candidates:
        return None
        
    candidates.sort(key=lambda x: len(x[1]), reverse=True)
    
    top_score = len(candidates[0][1])
    top_candidates = [c for c in candidates if len(c[1]) == top_score]
    
    if len(top_candidates) > 1:
        return None
        
    winner_tokens = top_candidates[0][1]
    for c in candidates[1:]:
        if not c[1].issubset(winner_tokens):
            return None
            
    return top_candidates[0][0]


_MIN_SEMANTIC_OVERLAP = 1

def _try_select_one_table(table_content: str, query: str, lang: str):
    parsed = _parse_table(table_content)
    if parsed[0] is None:
        return None
    headers, rows, cond_col, _ = parsed
    
    lines = [l for l in table_content.split("\n") if l.strip() and not l.startswith("[")]
    cols, _ = _parse_headers(lines)
    
    cond = _parse_query_condition(query, lang)
    if cond is None:
        return None
    op, v1, _, query_unit = cond
    
    table_unit = _table_condition_unit(table_content)
    
    if query_unit and table_unit:
        qd = _dimension(query_unit)
        td = _dimension(table_unit)
        if qd is None or td is None:
            return None
        if qd != td:
            return None
    elif query_unit and not table_unit:
        return None

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

    # Target Resolution
    if len(headers) == 2:
        val_col = 1 if cond_col == 0 else 0
        header_text = " ".join(headers)
        overlap = _semantic_overlap(query, header_text)
        if overlap < _MIN_SEMANTIC_OVERLAP:
            return None
    else:
        # Multi-column resolution
        if not cols:
            return None
        val_col_opt = _resolve_target(cols, query, cond_col)
        if val_col_opt is None:
            return None
        val_col = val_col_opt

    preds: list[Optional[Predicate]] = []
    for row in rows:
        if len(row) <= cond_col:
            preds.append(None)
            continue
        preds.append(_parse_row_predicate(row[cond_col]))

    matching = [ri for ri, p in enumerate(preds)
                if p is not None and p.contains(v1_norm)]
    if not matching:
        return None
    if len(matching) > 1:
        r_idx = _tightest_match([p for p in preds], matching)
        if r_idx is None:
            return None
    else:
        r_idx = matching[0]

    pred = preds[r_idx]
    
    if pred.is_compound and len(headers) != 2:
        pass
        
    row = rows[r_idx]
    val_text = row[val_col] if val_col < len(row) else ""
    return (row[cond_col], val_text,
            f"matched: {row[cond_col]} [{pred.describe()}] contains {op} {v1} -> col {val_col}")

def select_table_row(table_content: str, query_text: str, lang: str,
                     table_ref: str = "") -> SelectionResult:
    result = _try_select_one_table(table_content, query_text, lang)
    if result is not None:
        return SelectionResult(True, result[0], result[1], result[2], table_ref)
    return SelectionResult(False, "", "", "fallback", table_ref)
