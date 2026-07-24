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
    "alas": "bottom",
    "dasar": "bottom",
    "bawah": "bottom",
    "sisi": "side",
    "kulit": "shell",
    "kulit luar": "shell",
    "lambung": "shell",
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
    # Clean up synonyms map to better reflect title words
    for indo_term, eng_term in SYNONYM_MAP.items():
        if indo_term in clean_query:
            # Add English synonym keywords
            expanded_keywords.update(eng_term.split())
            # For bottom plating / side plating, inject specific keywords to help matching
            if indo_term in ["alas", "dasar", "bawah", "kulit", "kulit luar", "sisi", "lambung"]:
                expanded_keywords.add("plating")
                if indo_term in ["alas", "dasar", "bawah"]:
                    expanded_keywords.add("bottom")
                if indo_term in ["sisi"]:
                    expanded_keywords.add("side")
                if indo_term in ["kulit", "kulit luar", "lambung"]:
                    expanded_keywords.add("shell")
    
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
            # Add length penalty/bonus to prefer formulas that don't have too many unmet variables
            # FLOOR_PEAK_THICKNESS has 1 variable (L) which is met, so it gets a huge bonus in _coverage,
            # but we want bottom plating to win if "dasar" or "alas" is in the query.
            if formula.code in ["BOTTOM_PLATING_L_LESS_90", "BOTTOM_PLATING_L_GREATER_90"] and ("bottom" in expanded_keywords or "shell" in expanded_keywords):
                score += 30
            if formula.code in ["SIDE_PLATING_L_LESS_90", "SIDE_PLATING_L_GREATER_90"] and ("side" in expanded_keywords or "shell" in expanded_keywords):
                score += 30
            scored_formulas.append((formula, score))
    
    # Sort by score (descending)
    scored_formulas.sort(key=lambda x: x[1], reverse=True)
    return scored_formulas


def _parse_query_var_names(query: str) -> set[str]:
    """Return lowercased variable SYMBOLS extracted from the query's name=value pairs.

    Pure, offline. Works with comma decimals ('a=0,6') and unit suffixes ('L=100 m').
    Also matches trailing parentheses from raw query ('b)=600').
    Only SYMBOLS are needed; numeric values are not validated here.
    """
    pattern = r"(\w+)[\)]?\s*[=:]\s*[\d.,]+"
    found = {m.group(1).lower() for m in re.finditer(pattern, query, flags=re.IGNORECASE)}

    nl_aliases = {
        "jarak penegar": "a",
        "stiffener spacing": "a",
        "spacing": "a",
        "jarak gading": "a",
    }
    
    for alias, symbol in nl_aliases.items():
        alias_pattern = re.escape(alias) + r"[\s=:]+[\d.,]+"
        if re.search(alias_pattern, query, flags=re.IGNORECASE):
            found.add(symbol.lower())

    return found


def _required_vars(f: Formula) -> set[str]:
    """Lowercased set of variable symbols the user MUST supply (no default + required).
    For formulaSIDE_PLATING_L_GREATER_90, pS1 is optional so it's not strictly required.
    """
    req = set()
    for v in f.variables:
        if v.required and v.default is None:
            if f.code == "SIDE_PLATING_L_GREATER_90" and v.symbol.lower() == "ps1":
                continue
            req.add(v.symbol.lower())
    return req


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

    Args:
        query: User query string (original language; L=100 / a=0,6 etc preserved).
        candidates: List of Formula objects (typically search_formulas(query) output).

    Returns:
        (best, ranked) where:
        - best: the single formula to auto-select, OR None to request clarification.
        - ranked: the working list to render in the clarification message.
    """
    ranked = rank_formulas(query, candidates)

    # Extract query keywords (cleaned, lowercased) for the title-match signal.
    clean_query = re.sub(r"\w+\s*[=:]\s*[\d.,]+\s*\w*?", "", query, flags=re.IGNORECASE).lower()

    # 1. Check for domain keywords
    is_bottom = any(kw in clean_query for kw in ["alas", "dasar", "bawah", "bottom"])
    is_side = any(kw in clean_query for kw in ["sisi", "side"])
    is_deck = any(kw in clean_query for kw in ["dek", "geladak", "deck"])
    
    is_shell = any(kw in clean_query for kw in ["kulit", "lambung", "shell"]) or is_bottom or is_side

    # If domain is strictly identified, restrict candidates
    if is_shell and not is_deck:
        filtered_ranked = []
        for f, s in ranked:
            if "WHEEL_LOAD" in f.code or "FLOOR" in f.code or "DECK" in f.code or "CENTRE" in f.code or "FORECASTLE" in f.code or "FRAME" in f.code:
                pass
            else:
                filtered_ranked.append((f, s))
        if filtered_ranked:
            ranked = filtered_ranked
            
    if is_deck and not is_shell:
        filtered_ranked = []
        for f, s in ranked:
            if "BOTTOM" in f.code or "SIDE" in f.code or "FLOOR" in f.code or "CENTRE" in f.code or "FORECASTLE" in f.code or "FRAME" in f.code:
                pass
            else:
                filtered_ranked.append((f, s))
        if filtered_ranked:
            ranked = filtered_ranked

    if not ranked:
        return None, []

    # 2. Extract L value to determine branching for bottom/side plating
    l_val = None
    l_match = re.search(r"L\s*[=:]\s*([\d.,]+)", query, flags=re.IGNORECASE)
    if l_match:
        try:
            l_val = float(l_match.group(1).replace(",", "."))
        except ValueError:
            pass

    if is_bottom and not is_side:
        if l_val is not None:
            code_target = "BOTTOM_PLATING_L_GREATER_90" if l_val >= 90 else "BOTTOM_PLATING_L_LESS_90"
            for f, s in ranked:
                if f.code == code_target:
                    return f, ranked
    elif is_side and not is_bottom:
        if l_val is not None:
            code_target = "SIDE_PLATING_L_GREATER_90" if l_val >= 90 else "SIDE_PLATING_L_LESS_90"
            for f, s in ranked:
                if f.code == code_target:
                    return f, ranked

    # If the top score clearly dominates, select it
    top_f, top_s = ranked[0]
    if len(ranked) == 1:
        return top_f, ranked
    
    sec_f, sec_s = ranked[1]
    
    # Re-introduce the provided coverage tiebreaker for exact ties, but only for fallback
    # The old `select_formula` primarily relied on coverage to solve exact ties (like FLOOR_PEAK 44 vs FLOOR_WEB 44)
    # If the scores are identical or very close, use coverage to break the tie
    if abs(top_s - sec_s) < 5:
        provided = _parse_query_var_names(query)
        top_cov = _coverage(top_f, provided)
        sec_cov = _coverage(sec_f, provided)
        if top_cov > sec_cov:
            return top_f, ranked
        elif sec_cov > top_cov:
            return sec_f, ranked
    
    if top_s >= sec_s + 6 or top_s >= 1.1 * sec_s:
        return top_f, ranked

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
    
    if top_score > second_score + 25:
        # Clear winner by margin
        return [scored_formulas[0][0]]
        
    if top_score >= 1.5 * second_score:
        # Clear winner by ratio
        return [scored_formulas[0][0]]
    
    # Return top 4 candidates to avoid overwhelming the user
    return [formula for formula, score in scored_formulas[:4]]


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
