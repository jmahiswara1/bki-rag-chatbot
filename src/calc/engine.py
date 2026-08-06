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
    # 2. Natural Language Parsing for Aliases
    nl_aliases = {
        "jarak penegar": "a",
        "stiffener spacing": "a",
        "jarak gading": "a",
        "frame spacing": "a",
        "nilai b": "a",  # BKI notation: b = stiffener spacing
        "nilai a": "a",
        "jarak jepit": "l",  # unsupported span
        "spacing": "a", # Add back generic spacing for cases like "spacing 0.6 m"
    }
    
    parsed_values: dict[str, float] = {}
    warnings: list[str] = []
    
    # Track the start/end indexes of aliases matched so we don't accidentally match part of them again in general variables
    alias_matched_ranges = []
    
    for alias, symbol in nl_aliases.items():
        # Build 42: 'nilai b' / stiffener-spacing aliases normally map to 'a',
        # but the slenderness formula uses symbol 'b' directly. Prefer the
        # formula's own 'b' variable when present.
        if symbol == "a" and any(v.symbol.lower() == "b" for v in formula.variables):
            symbol = "b"
        # alias [optional =:] value [optional unit]
        # Changed value group to include optional negative sign
        alias_pattern = re.escape(alias) + r"[\s=:]+(-?\d+(?:[.,]\d+)?)(?:\s+([a-zA-Z0-9/^*-]+)(?!\w*\s*[=:]))?"
        for match in re.finditer(alias_pattern, query, flags=re.IGNORECASE):
            value_str = match.group(1).replace(",", ".")
            unit = match.group(2)
            try:
                value = float(value_str)
            except ValueError:
                continue
                
            alias_matched_ranges.append(match.span())
                
            matched_var = None
            for var in formula.variables:
                if var.symbol.lower() == symbol.lower():
                    matched_var = var
                    break
                    
            if matched_var and matched_var.symbol not in parsed_values:
                if matched_var.symbol.lower() == 'a':
                    if unit and unit.lower() == 'mm':
                        value = value / 1000.0
                    elif unit and unit.lower() == 'm':
                        pass # explicit meter, do nothing
                    elif not unit:
                        if value <= 2.0:
                            warnings.append(f"Asumsi: 'a' tanpa satuan ditafsirkan sebagai meter (a={value} m). Sertakan 'mm' bila maksudnya milimeter.")
                        else:
                            value = value / 1000.0
                            warnings.append(f"Asumsi: 'a'={value*1000} terlalu besar untuk meter; ditafsirkan sebagai mm (a={value} m). Sertakan satuan untuk memastikan.")
                parsed_values[matched_var.symbol] = value
                
                if unit and matched_var.unit and unit.lower() != matched_var.unit.lower():
                    if not (matched_var.symbol.lower() == 'a' and unit.lower() == 'mm'):
                        warnings.append(
                            f"Unit '{unit}' for {matched_var.symbol} doesn't match "
                            f"expected '{matched_var.unit}'. Using value as-is."
                        )

    # General Variable parsing
    # Use negative lookahead to avoid matching a word as unit if followed by = or :
    # Also explicitly prevent common calculation keywords (like 'spacing') from being parsed as units
    # Changed (?!\s*[=:]) to (?!\w*\s*[=:]) to prevent matching partial words as units
    # Changed value group from [\d.,]+ to -?\d+(?:[.,]\d+)? to capture optional negative sign
    pattern = r"(\w+)[\)]?\s*[=:]\s*(-?\d+(?:[.,]\d+)?)(?:\s+(?!spacing|jarak|pelat|alas|sisi|bawah|atas|mild|steel|baja|standar|lunak|kapal|minimum|maksimum|nilai|shell|plating|bottom|side|deck|hatch|plate)([a-zA-Z0-9/^*-]+)(?!\w*\s*[=:]))?"
    
    for match in re.finditer(pattern, query, re.IGNORECASE):
        # Skip if this match falls entirely inside an alias match (e.g. "spacing 0.6 m" inside "stiffener spacing 0.6 m")
        # to prevent double parsing or grabbing pieces of it
        start, end = match.span()
        if any(a_start <= start and end <= a_end for a_start, a_end in alias_matched_ranges):
            continue
            
        var_name = match.group(1)
        value_str = match.group(2)
        unit = match.group(3)
        
        # Normalize decimal: "1,5" -> "1.5" (comma -> dot)
        value_str = value_str.replace(",", ".")
        
        try:
            value = float(value_str)
        except ValueError:
            # Skip non-numeric values
            continue
        
        # Match to formula variable (case-insensitive on symbol or name)
        matched_var = None
        # Hard-coded symbol aliases for BKI variable notation:
        # b = stiffener spacing (mapped to 'a' when formula has 'a' but not 'b')
        _symbol_aliases = {"b": "a"}
        has_b_variable = any(v.symbol.lower() == "b" for v in formula.variables)
        effective_name = var_name.lower() if has_b_variable else _symbol_aliases.get(var_name.lower(), var_name)
        for var in formula.variables:
            if (var.symbol.lower() == effective_name.lower() or 
                var.name.lower() == var_name.lower()):
                matched_var = var
                
                # Unit conversion specifically for 'a' (stiffener spacing) which is expected in 'm'
                if matched_var.symbol.lower() == 'a' and matched_var.symbol not in parsed_values:
                    if unit and unit.lower() == 'mm':
                        value = value / 1000.0
                    elif unit and unit.lower() == 'm':
                        pass # explicit meter, do nothing
                    elif not unit:
                        # Unitless assumption logic
                        if value <= 2.0:
                            warnings.append(f"Asumsi: 'a' tanpa satuan ditafsirkan sebagai meter (a={value} m). Sertakan 'mm' bila maksudnya milimeter.")
                        else:
                            value = value / 1000.0
                            warnings.append(f"Asumsi: 'a'={value*1000} terlalu besar untuk meter; ditafsirkan sebagai mm (a={value} m). Sertakan satuan untuk memastikan.")
                
                break
        
        if matched_var and matched_var.symbol not in parsed_values:
            parsed_values[matched_var.symbol] = value
            
            # Unit check: warning only, don't auto-convert (except 'a' which we just handled)
            if unit and matched_var.unit and unit.lower() != matched_var.unit.lower():
                # Don't warn again if we just handled 'a'
                if not (matched_var.symbol.lower() == 'a' and unit.lower() == 'mm'):
                    warnings.append(
                        f"Unit '{unit}' for {matched_var.symbol} doesn't match "
                        f"expected '{matched_var.unit}'. Using value as-is."
                    )

    # 3. Handle specific domain semantics (P1 fixes)
    # k (steel grade)
    k_explicit = False
    if 'k' in parsed_values:
        k_explicit = True
    elif re.search(r"high\s*tensile|ht", query, re.IGNORECASE):
        # High tensile but no explicit k: DO NOT default to 1.0
        # Will handle this below by not setting a default for k
        pass
    elif re.search(r"mild\s*steel|baja\s*lunak", query, re.IGNORECASE):
        parsed_values['k'] = 1.0
        # NO warning here, because user explicitly requested mild steel.
    
    # nf (framing system)
    nf_explicit = False
    if 'nf' in parsed_values:
        nf_explicit = True
    elif re.search(r"longitudinal|membujur", query, re.IGNORECASE):
        parsed_values['nf'] = 0.83
        warnings.append("Sistem gading memanjang (longitudinal framing) -> nf=0.83.")
    elif re.search(r"transverse|melintang", query, re.IGNORECASE):
        parsed_values['nf'] = 1.0
        warnings.append("Sistem gading melintang (transverse framing) -> nf=1.0.")

    # Find missing required variables
    missing_vars = []
    for var in formula.variables:
        if not var.required:
            continue
        # Allow pS1 to be missing for SIDE_PLATING_L_GREATER_90
        if formula.code == "SIDE_PLATING_L_GREATER_90" and var.symbol == "pS1":
            continue
        # If it has a default, we already filled it, so it's not missing
        if var.default is not None:
            continue
        if var.symbol not in parsed_values:
            missing_vars.append(var)
    
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
        # If var has a default, fill it (even if required=True, meaning it's a required input but has a sensible default we can use if not provided)
        if (var.symbol not in parsed_values and var.default is not None):
            if var.symbol == 'k' and re.search(r"high\s*tensile|ht", query, re.IGNORECASE):
                # Don't apply default k=1.0 if high tensile is mentioned
                continue
            
            parsed_values[var.symbol] = var.default
            
            # Add warnings for implicit defaults
            if var.symbol == 'nf':
                warnings.append("Asumsi: nf=1.0 (transverse). Sebutkan 'longitudinal' untuk nf=0.83.")
            elif var.symbol == 'k':
                warnings.append("Asumsi: k=1.0 (mild steel).")
            elif var.symbol == 'tK':
                warnings.append(f"Asumsi: tK={var.default} mm (corrosion addition standar).")
                
    # Sanity-bound for 'a'
    if 'a' in parsed_values:
        a_m = parsed_values['a']
        if not (0.1 <= a_m <= 2.0):
             return CalculationResult(
                success=False,
                message=f"Nilai 'a' ({a_m} m) di luar rentang wajar [0.1, 2.0] m. Mohon koreksi nilai atau berikan satuan (mm/m) yang jelas.",
                formula=formula,
                parsed_values=parsed_values,
                missing_vars=[],
                warnings=warnings
             )
    
    # Custom message for missing k when high tensile is mentioned
    if 'k' not in parsed_values and re.search(r"high\s*tensile|\bht\b", query, re.IGNORECASE):
        # We need to block the missing_vars check and return a custom message
        missing_vars = [v for v in missing_vars if v.symbol != 'k']
        return CalculationResult(
            success=False,
            message="Anda menyebutkan 'high tensile' / 'HT', namun nilai material factor (k) tidak diberikan.\nMohon sebutkan nilai k atau tegangan luluh (ReH), contoh:\n- ReH 315 -> k = 0.78\n- ReH 355 -> k = 0.72\nAtau tulis 'k=0.78' secara eksplisit.",
            formula=formula,
            parsed_values=parsed_values,
            missing_vars=missing_vars,
            warnings=warnings
        )
        
    # Sanity-bounds & validasi untuk pB (Bottom Load)
    if 'pB' in parsed_values:
        pB_val = parsed_values['pB']
        if pB_val <= 0:
            return CalculationResult(
                success=False,
                message=f"Nilai pB harus positif (> 0, tekanan desain). Nilai yang diberikan: {pB_val}",
                formula=formula,
                parsed_values=parsed_values,
                missing_vars=[],
                warnings=warnings
            )
        # Ambang wajar pB: jarang tekanan beban alas melampaui 1000 kN/m2 (setara ~100m head air) pada kapal kargo komersial standar.
        if pB_val > 1000:
            warnings.append(f"Perhatian: Nilai pB={pB_val} sangat besar (implausibel). Mohon periksa kembali input Anda.")

    
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
        # Special handling for pS1 in SIDE_PLATING_L_GREATER_90
        # If pS1 is missing but pS is present, evaluate without the tS3 branch
        if formula.code == "SIDE_PLATING_L_GREATER_90" and "pS1" not in parsed_values:
            # We must strip the pS1 term from the Max function string before parsing
            # Original: Max(..., ..., 18.3 * nf * a * sqrt(pS1 / (190.8/k)) + tK)
            expr_str = "Max(18.3 * nf * a * sqrt(pS / (176.1/k)) + tK, 1.21 * a * sqrt(pS * k) + tK)"
            local_dict = {var.symbol: sympy.Symbol(var.symbol) for var in formula.variables if var.symbol != 'pS1'}
            try:
                expr = parse_expr(expr_str, local_dict=local_dict, transformations=standard_transformations)
                subs_dict = {local_dict[k]: v for k, v in parsed_values.items() if k in local_dict}
                substituted = expr.subs(subs_dict)
                substituted_expr = str(substituted)
                result_expr = substituted.evalf()
                
                if result_expr.free_symbols:
                    unsubstituted = sorted(str(s) for s in result_expr.free_symbols)
                    raise ValueError(
                        f"Variabel belum punya nilai: {', '.join(unsubstituted)}. "
                        "Please provide values for these variables."
                    )
                if result_expr.is_finite is not True:
                    raise ValueError(
                        "Pembagian nol / hasil tak hingga. "
                        "Please check variable values."
                    )
                result = float(result_expr)
                warnings.append("Catatan: tS3 dilewati (pS1 tidak diberikan)")
            except Exception as e:
                raise ValueError(f"Failed to evaluate modified expression for missing pS1: {e}")
        else:
            result, substituted_expr = _evaluate_formula(formula, parsed_values)
        
        # Build citation
        citation = f"(Sec {formula.section_no}"
        if formula.paragraph_id:
            citation += f" | {formula.paragraph_id}"
        if formula.page_no:
            citation += f", p.{formula.page_no}"
        citation += ")"
        
        # Format result message. Use a locale-friendly decimal form: strip
        # trailing zeros and use a comma for fractional values so '6.0000'
        # is not misread as 6000 (thousands separator). Whole values keep
        # the comma for BKI-style readability (e.g. '6,0').
        result_rounded = round(result, 3)
        if result_rounded == int(result_rounded):
            result_str = f"{int(result_rounded)},0"
        else:
            result_str = str(result_rounded).replace(".", ",")
        unit_str = formula.result_unit or ""
        substitution_str = str(substituted_expr)
        
        message = (
            f"Calculation result:\n"
            f"Formula: {formula.expression}\n"
            f"Substitution: {substitution_str}\n"
            f"Result: {result_str} {unit_str}\n\n"
            f"Source: {citation}"
        )
        
        # Add formula notes if present (applicability limits, etc.)
        if formula.notes:
            message += f"\n\nNote: {formula.notes}"
            
        # Ambang wajar ketebalan pelat: tebal lambung/alas kapal pada umumnya di bawah 50mm, jarang di atas 100mm.
        if result > 100:
            warnings.append(f"Perhatian: Hasil perhitungan tebal pelat sangat besar ({result_str} {unit_str}). Nilai mungkin implausibel, periksa input Anda.")
        
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
