from dataclasses import dataclass, field

import sympy


@dataclass
class CalculationResult:
    # Stub result returned by calculate() until Fase 4 lands the real engine.
    message: str
    values: dict = field(default_factory=dict)
    result: float | None = None
    unit: str = ""


def evaluate(expression: str, values: dict) -> float:
    # Deterministic compute. The LLM never does the arithmetic.
    # expression e.g. "c*sqrt(p)*a"; values maps symbol -> number.
    expr = sympy.sympify(expression)
    return float(expr.subs(values))


def calculate(query: str, *, intent=None) -> CalculationResult:
    """Fase 3 stub. The real slot-filling engine lands in Fase 4.

    Called by the chain when intent == 'calculation' so the LLM does NOT
    attempt to retrieve context or compute numbers itself.
    """
    return CalculationResult(
        message=(
            "Calculation engine is in Fase 4 (pending). "
            "Your request has been received but not yet executed."
        )
    )
