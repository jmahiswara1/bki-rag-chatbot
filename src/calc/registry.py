import re

from src.core.db import get_client
from src.core.models import Formula, Variable


# Synonym map for Indonesian/English terms (case-insensitive)
SYNONYM_MAP = {
    "penumpu tengah": "centre girder",
    "penumpu": "girder",
    "tengah": "centre",
    "tebal": "thickness",
    "pelat": "plate",
    "web": "web",
    "web plate": "web plate",
}


def get_formula(code: str) -> Formula | None:
    """Load a curated, verified formula by code.
    
    Args:
        code: Formula code (e.g., "EXAMPLE_PLATE_THICKNESS")
        
    Returns:
        Formula object if found and verified, None otherwise
    """
    client = get_client()
    resp = (
        client.table("formulas")
        .select("*")
        .eq("code", code)
        .eq("verified", True)  # Only return verified formulas
        .limit(1)
        .execute()
    )
    if not resp.data:
        return None
    row = resp.data[0]
    return _row_to_formula(row)


def list_verified_formulas() -> list[Formula]:
    """Return all verified formulas.
    
    Returns:
        List of Formula objects where verified=True
    """
    client = get_client()
    resp = (
        client.table("formulas")
        .select("*")
        .eq("verified", True)
        .execute()
    )
    return [_row_to_formula(row) for row in resp.data]


def rank_formulas(query: str, formulas: list[Formula]) -> list[tuple[Formula, float]]:
    """Rank formulas by weighted token overlap with query (pure, offline-testable).
    
    Args:
        query: User query string
        formulas: List of Formula objects to rank
        
    Returns:
        List of (Formula, score) tuples sorted by score descending.
        Score is weighted token overlap + synonym bonus + variable match bonus.
    """
    # Remove name=value patterns from query before matching
    clean_query = re.sub(r"\w+\s*[=:]\s*[\d.,]+\s*\w*?", "", query, flags=re.IGNORECASE).lower()
    
    # Extract keywords from cleaned query
    query_keywords = set(re.findall(r"\w+", clean_query))
    
    # Extract variable names from query (for variable matching bonus)
    var_pattern = r"(\w+)\s*[=:]\s*[\d.,]+\s*\w*?"
    query_var_names = set(re.findall(var_pattern, query, flags=re.IGNORECASE))
    
    # Apply synonym expansion to query keywords
    expanded_keywords = set(query_keywords)
    for indo_term, eng_term in SYNONYM_MAP.items():
        if indo_term in clean_query:
            # Add English synonym keywords
            expanded_keywords.update(eng_term.split())
    
    scored_formulas = []
    for formula in formulas:
        # Combine title, code, and notes for matching
        text_to_match = f"{formula.code} {formula.title} {formula.notes or ''}".lower()
        formula_keywords = set(re.findall(r"\w+", text_to_match))
        
        # Calculate weighted overlap score (longer words = higher weight)
        overlap = expanded_keywords & formula_keywords
        score = sum(len(word) for word in overlap)
        
        # Synonym bonus: if query contains Indonesian term that maps to formula's English term
        for indo_term, eng_term in SYNONYM_MAP.items():
            if indo_term in clean_query and eng_term in text_to_match:
                score += 15  # Big bonus for synonym match
        
        # Variable match bonus: if query provides variables that match formula's variables
        formula_var_symbols = {var.symbol.lower() for var in formula.variables}
        formula_var_names = {var.name.lower() for var in formula.variables}
        var_match_count = len(query_var_names & (formula_var_symbols | formula_var_names))
        score += var_match_count * 10  # Big bonus for variable matches
        
        if score > 0:
            scored_formulas.append((formula, score))
    
    # Sort by score (descending)
    scored_formulas.sort(key=lambda x: x[1], reverse=True)
    return scored_formulas


def _parse_query_var_names(query: str) -> set[str]:
    """Return lowercased variable SYMBOLS extracted from the query's name=value pairs.

    Pure, offline. Works with comma decimals ('a=0,6') and unit suffixes ('L=100 m').
    Only SYMBOLS are needed; numeric values are not validated here.
    """
    pattern = r"(\w+)\s*[=:]\s*[\d.,]+"
    return {m.group(1).lower() for m in re.finditer(pattern, query, flags=re.IGNORECASE)}


def _required_vars(f: Formula) -> set[str]:
    """Lowercased set of variable symbols the user MUST supply (no default + required)."""
    return {v.symbol.lower() for v in f.variables if v.required and v.default is None}


def _coverage(f: Formula, provided: set[str]) -> int:
    """How many of the formula's variables (required + optional) the user provided."""
    return len({v.symbol.lower() for v in f.variables} & provided)


def _title_direct_match(f: Formula, query_keywords: set[str]) -> int:
    """Count query keywords that appear verbatim in the formula's title.

    This is a stronger signal than synonym-expanded overlap: "minimum" in the
    query matching "Minimum" in DECK_PLATING_MIN's title is a direct semantic
    match, while "pelat" -> "plate" via SYNONYM_MAP is a weaker expansion.
    Used by select_formula as the primary tiebreaker among satisfiable
    candidates, so that a direct title hit beats a synonym-only match.
    """
    title_tokens = set(re.findall(r"\w+", f.title.lower()))
    return len(query_keywords & title_tokens)


def select_formula(
    query: str,
    candidates: list[Formula],
) -> tuple[Formula | None, list[tuple[Formula, float]]]:
    """Pick the most likely formula for a calculation query.

    Pure, offline, deterministic. Uses VARIABLE COMPLETENESS as the primary
    disambiguator and the existing text-overlap score (from rank_formulas) as
    the secondary tiebreaker. This replaces the brittle 1.5x score-margin gate
    that failed on exact-tie cases like 'Hitung tebal minimum pelat dek kedua
    dengan L=100, k=1' (3-way tie at score 44).

    Args:
        query: User query string (original language; L=100 / a=0,6 etc preserved).
        candidates: List of Formula objects (typically search_formulas(query) output).

    Returns:
        (best, ranked) where:
        - best: the single formula to auto-select, OR None to request clarification.
        - ranked: the working list to render in the clarification message
          (the satisfiable subset when non-empty, else the full text-ranked list).

    Decision:
      1) Build provided = set of variable symbols parsed from query.
      2) ranked = rank_formulas(query, candidates) -- pure text overlap.
      3) satisfied = [(f, s) in ranked if required(f) and required(f) <= provided]
           (i.e. the user supplied EVERY required variable for that formula).
      4) If satisfied is non-empty:
           - sort by (coverage desc, text_score desc).
           - best = satisfied[0].
           - UNLESS a 2nd entry has the SAME coverage AND the SAME text_score
             (a true ambiguity), auto-select best and return (best, satisfied).
           - Otherwise return (None, satisfied) for clarification.
      5) If no formula's required vars are satisfied, return (None, ranked)
           so the user sees the full ranked list (the calc engine will ask
           for missing variables later).
    """
    provided = _parse_query_var_names(query)
    ranked = rank_formulas(query, candidates)

    # Extract query keywords (cleaned, lowercased) for the title-match signal.
    clean_query = re.sub(r"\w+\s*[=:]\s*[\d.,]+\s*\w*?", "", query, flags=re.IGNORECASE).lower()
    query_keywords = set(re.findall(r"\w+", clean_query))

    satisfied: list[tuple[Formula, float]] = []
    for f, s in ranked:
        req = _required_vars(f)
        if req and req <= provided:
            satisfied.append((f, s))

    if satisfied:
        # Sort key (descending): (title_direct_match, text_score, coverage).
        #
        # 1) title_direct_match: how many of the user's query words appear
        #    verbatim in the formula's title. A direct match like "minimum"
        #    in DECK_PLATING_MIN's title beats a synonym-only expansion like
        #    "ceruk" -> "peak" for FLOOR_PEAK_THICKNESS, so this is the
        #    strongest signal among the satisfiable set.
        # 2) text_score: from rank_formulas (includes synonym expansion and
        #    variable-match bonus). Used as the primary signal when no
        #    formula has a direct title match (e.g. floor_peak query with
        #    only synonym matches).
        # 3) coverage: how many of the formula's variables the user supplied.
        #    Tiebreaker for cases where both title match and text score tie.
        satisfied.sort(
            key=lambda fs: (
                _title_direct_match(fs[0], query_keywords),
                fs[1],
                _coverage(fs[0], provided),
            ),
            reverse=True,
        )
        best_f, best_s = satisfied[0]
        if len(satisfied) >= 2:
            sec_f, sec_s = satisfied[1]
            if (best_s == sec_s
                    and _coverage(best_f, provided) == _coverage(sec_f, provided)
                    and _title_direct_match(best_f, query_keywords)
                        == _title_direct_match(sec_f, query_keywords)):
                # True ambiguity: two candidates both fully satisfiable with the
                # same coverage and same text score. Ask the user.
                return None, satisfied
        return best_f, satisfied

    # Nothing fully satisfiable: surface the full ranked list.
    return None, ranked


def search_formulas(query: str) -> list[Formula]:
    """Search formulas by keyword overlap on title and notes.
    
    Args:
        query: User query string (should be English for best results)
        
    Returns:
        List of Formula objects sorted by relevance (weighted keyword overlap + variable match).
        If top candidate clearly dominates (score >= 1.5x second place), return only that one.
        Otherwise return all candidates for user clarification.
    """
    # Get all verified formulas
    formulas = list_verified_formulas()
    
    if not formulas:
        return []
    
    # Rank formulas using pure ranking function
    scored_formulas = rank_formulas(query, formulas)
    
    if not scored_formulas:
        return []
    
    # Auto-select if top candidate clearly dominates (score >= 1.5x second place)
    if len(scored_formulas) == 1:
        return [scored_formulas[0][0]]
    
    top_score = scored_formulas[0][1]
    second_score = scored_formulas[1][1]
    
    if top_score >= 1.5 * second_score:
        # Clear winner - return only top candidate
        return [scored_formulas[0][0]]
    
    # Multiple close candidates - return all for user clarification
    return [formula for formula, score in scored_formulas]


def _row_to_formula(row: dict) -> Formula:
    """Convert database row to Formula object.
    
    Args:
        row: Database row dict with variables as JSON
        
    Returns:
        Formula object with properly constructed Variable objects
    """
    # Explicitly construct Variable objects (not positional)
    variables = []
    for v in row["variables"]:
        variables.append(
            Variable(
                symbol=v["symbol"],
                name=v["name"],
                unit=v["unit"],
                required=v.get("required", True),
                default=v.get("default")
            )
        )
    
    return Formula(
        code=row["code"],
        title=row["title"],
        section_no=row["section_no"],
        expression=row["expression"],
        variables=variables,
        paragraph_id=row.get("paragraph_id"),
        page_no=row.get("page_no"),
        result_unit=row.get("result_unit"),
        notes=row.get("notes")
    )
