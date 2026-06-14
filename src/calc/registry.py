import re

from src.core.db import get_client
from src.core.models import Formula, Variable


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


def search_formulas(query: str) -> list[Formula]:
    """Search formulas by keyword overlap on title and notes.
    
    Args:
        query: User query string (should be English for best results)
        
    Returns:
        List of Formula objects sorted by relevance (weighted keyword overlap + variable match).
        If top candidate clearly dominates (score >= 1.1x second place), return only that one.
        Otherwise return all candidates for user clarification.
    """
    # Get all verified formulas
    formulas = list_verified_formulas()
    
    if not formulas:
        return []
    
    # Remove name=value patterns from query before matching
    clean_query = re.sub(r"\w+\s*[=:]\s*[\d.,]+\s*\w*?", "", query, flags=re.IGNORECASE)
    
    # Extract keywords from cleaned query (lowercase, split on non-word chars)
    query_keywords = set(re.findall(r"\w+", clean_query.lower()))
    
    # Extract variable names from query (for variable matching bonus)
    var_pattern = r"(\w+)\s*[=:]\s*[\d.,]+\s*\w*?"
    query_var_names = set(re.findall(var_pattern, query, flags=re.IGNORECASE))
    
    # Score each formula by weighted keyword overlap + variable match bonus
    scored_formulas = []
    for formula in formulas:
        # Combine title and notes for matching
        text_to_match = f"{formula.title} {formula.notes or ''}".lower()
        formula_keywords = set(re.findall(r"\w+", text_to_match))
        
        # Calculate weighted overlap score
        overlap = query_keywords & formula_keywords
        score = sum(len(word) for word in overlap)
        
        # Variable match bonus: if query provides variables that match formula's variables
        formula_var_symbols = {var.symbol.lower() for var in formula.variables}
        formula_var_names = {var.name.lower() for var in formula.variables}
        var_match_count = len(query_var_names & (formula_var_symbols | formula_var_names))
        score += var_match_count * 10  # Big bonus for variable matches
        
        if score > 0:
            scored_formulas.append((score, formula))
    
    if not scored_formulas:
        return []
    
    # Sort by score (descending)
    scored_formulas.sort(key=lambda x: x[0], reverse=True)
    
    # Auto-select if top candidate clearly dominates (score >= 1.1x second place)
    if len(scored_formulas) == 1:
        return [scored_formulas[0][1]]
    
    top_score = scored_formulas[0][0]
    second_score = scored_formulas[1][0]
    
    if top_score >= 1.1 * second_score:
        # Clear winner - return only top candidate
        return [scored_formulas[0][1]]
    
    # Multiple close candidates - return all for user clarification
    return [formula for score, formula in scored_formulas]


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
