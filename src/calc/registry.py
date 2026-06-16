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
