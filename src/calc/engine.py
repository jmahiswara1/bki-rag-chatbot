import sympy


def evaluate(expression: str, values: dict) -> float:
    # Deterministic compute. The LLM never does the arithmetic.
    # expression e.g. "c*sqrt(p)*a"; values maps symbol -> number.
    expr = sympy.sympify(expression)
    return float(expr.subs(values))
