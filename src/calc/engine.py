import re
from dataclasses import dataclass, field

import sympy
from sympy.parsing.sympy_parser import parse_expr, standard_transformations

from src.core.models import Formula, Variable


@dataclass
class CalculationResult:
    """Result from calculation engine."""
    success: bool
    message: str
    formula: Formula | None = None
    result: float | None = None
    result_unit: str = ""
    substituted_expr: str = ""
    parsed_values: dict[str, float] = field(default_factory=dict)
    missing_vars: list[Variable] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: str = ""


def _parse_variables(
    query: str, formula: Formula
) -> tuple[dict[str, float], list[Variable], list[str]]:
    """Parse variables from query string.
    
    Args:
        query: User query containing variable assignments
        formula: Formula object with variable definitions
        
    Returns:
        tuple: (parsed_values, missing_vars, warnings)
            - parsed_values: dict mapping symbol -> float value
            - missing_vars: list of required Variables not found in query
            - warnings: list of warning messages (e.g., unit mismatch)
    """
    # Regex: variable_name = value [unit]
    # Examples: "L=100", "L = 100 m", "L : 100.5", "panjang = 100"
    # Use negative lookahead to avoid matching a word as unit if followed by = or :
    pattern = r"(\w+)\s*[=:]\s*([\d.,]+)(?:\s+(\w+)(?!\s*[=:]))?"
    matches = re.findall(pattern, query, re.IGNORECASE)
    
    parsed_values: dict[str, float] = {}
    warnings: list[str] = []
    
    for var_name, value_str, unit in matches:
        # Normalize decimal: "1,5" -> "1.5" (comma -> dot)
        value_str = value_str.replace(",", ".")
        
        try:
            value = float(value_str)
        except ValueError:
            # Skip non-numeric values
            continue
        
        # Match to formula variable (case-insensitive on symbol or name)
        matched_var = None
        for var in formula.variables:
            if (var.symbol.lower() == var_name.lower() or 
                var.name.lower() == var_name.lower()):
                matched_var = var
                break
        
        if matched_var:
            parsed_values[matched_var.symbol] = value
            
            # Unit check: warning only, don't auto-convert
            if unit and matched_var.unit and unit.lower() != matched_var.unit.lower():
                warnings.append(
                    f"Unit '{unit}' for {matched_var.symbol} doesn't match "
                    f"expected '{matched_var.unit}'. Using value as-is."
                )
    
    # Find missing required variables
    missing_vars = [
        var for var in formula.variables
        if var.required and var.symbol not in parsed_values
    ]
    
    return parsed_values, missing_vars, warnings


def _evaluate_formula(
    formula: Formula, values: dict[str, float]
) -> tuple[float, str]:
    """Evaluate formula with given values using sympy.
    
    Args:
        formula: Formula object with expression
        values: dict mapping symbol -> float value
        
    Returns:
        tuple: (result, substituted_expr)
            - result: float result
            - substituted_expr: string representation of substituted expression
            
    Raises:
        ValueError: If evaluation fails (division by zero, invalid expression, etc.)
    """
    # MUST-FIX: Build explicit symbol table to avoid sympy constant conflicts
    # sympy has built-in constants: I (imaginary), E (Euler), N, pi, S, O
    # BKI uses I=moment of inertia, E=modulus, N, etc. -> must not conflict
    local_dict = {var.symbol: sympy.Symbol(var.symbol) for var in formula.variables}
    
    # Parse expression with explicit local_dict
    try:
        expr = parse_expr(
            formula.expression,
            local_dict=local_dict,
            transformations=standard_transformations
        )
    except Exception as e:
        raise ValueError(f"Failed to parse expression: {e}")
    
    # Validate: expr.free_symbols must be subset of our local_dict symbols
    expected_symbols = set(local_dict.values())
    if not expr.free_symbols.issubset(expected_symbols):
        unknown = expr.free_symbols - expected_symbols
        raise ValueError(f"Expression contains unknown symbols: {unknown}")
    
    # Substitute values using Symbol objects (not string keys)
    subs_dict = {local_dict[k]: v for k, v in values.items() if k in local_dict}
    substituted = expr.subs(subs_dict)
    substituted_str = str(substituted)
    
    # Evaluate to float
    result_expr = substituted.evalf()
    
    # MUST-FIX: Separate checks for unsubstituted symbols vs non-finite results
    # Check for unsubstituted symbols first (more specific error)
    if result_expr.free_symbols:
        unsubstituted = sorted(str(s) for s in result_expr.free_symbols)
        raise ValueError(
            f"Variabel belum punya nilai: {', '.join(unsubstituted)}. "
            "Please provide values for these variables."
        )
    
    # Check for non-finite results (zoo, oo, nan)
    # sympy doesn't raise ZeroDivisionError, it returns zoo/oo/nan
    # Use "is not True" to catch both False and None
    if result_expr.is_finite is not True:
        raise ValueError(
            "Pembagian nol / hasil tak hingga. "
            "Please check variable values."
        )
    
    try:
        result = float(result_expr)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Failed to convert result to float: {e}")
    
    return result, substituted_str


def calculate(query: str, formula: Formula) -> CalculationResult:
    """Calculate result for given formula using values parsed from query.
    
    Args:
        query: User query containing variable assignments
        formula: Formula object to evaluate
        
    Returns:
        CalculationResult with success status and details
    """
    # Parse variables from query
    parsed_values, missing_vars, warnings = _parse_variables(query, formula)
    
    # FIX #2a: Fill default values for optional variables that weren't provided
    for var in formula.variables:
        if (not var.required and 
            var.symbol not in parsed_values and 
            var.default is not None):
            parsed_values[var.symbol] = var.default
    
    # Check for missing required variables
    if missing_vars:
        missing_list = "\n".join([
            f"  - {var.symbol} ({var.name}): {var.unit}"
            for var in missing_vars
        ])
        
        # Build example input
        example_parts = []
        for var in formula.variables:
            example_parts.append(f"{var.symbol} = [value] {var.unit}")
        example = ", ".join(example_parts)
        
        message = (
            f"Missing required variables:\n{missing_list}\n\n"
            f"Example input: {example}"
        )
        
        if warnings:
            message += "\n\nWarnings:\n" + "\n".join(f"  - {w}" for w in warnings)
        
        return CalculationResult(
            success=False,
            message=message,
            formula=formula,
            parsed_values=parsed_values,
            missing_vars=missing_vars,
            warnings=warnings
        )
    
    # Evaluate formula
    try:
        result, substituted_expr = _evaluate_formula(formula, parsed_values)
        
        # Build citation
        citation = f"(Sec {formula.section_no}"
        if formula.paragraph_id:
            citation += f" | {formula.paragraph_id}"
        if formula.page_no:
            citation += f", p.{formula.page_no}"
        citation += ")"
        
        # Format result message
        result_str = f"{result:.4f}"
        unit_str = formula.result_unit or ""
        
        message = (
            f"Calculation result:\n"
            f"Formula: {formula.expression}\n"
            f"Substitution: {substituted_expr}\n"
            f"Result: {result_str} {unit_str}\n\n"
            f"Source: {citation}"
        )
        
        if warnings:
            message += "\n\nPeringatan:\n" + "\n".join(f"  - {w}" for w in warnings)
        
        return CalculationResult(
            success=True,
            message=message,
            formula=formula,
            result=result,
            result_unit=formula.result_unit or "",
            substituted_expr=substituted_expr,
            parsed_values=parsed_values,
            warnings=warnings
        )
    except ValueError as e:
        return CalculationResult(
            success=False,
            message=f"Calculation error: {e}",
            formula=formula,
            parsed_values=parsed_values,
            warnings=warnings,
            error=str(e)
        )
