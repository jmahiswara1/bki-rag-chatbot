"""Tests for calculation engine (Fase 4a).

All tests use in-memory Formula objects, no database required.
"""
import pytest

from src.calc.engine import (
    CalculationResult,
    _evaluate_formula,
    _parse_variables,
    calculate,
)
from src.calc.registry import rank_formulas
from src.core.models import Formula, Variable


class TestParseVariables:
    """Tests for _parse_variables function."""

    def test_simple_assignment(self):
        """Test simple L=100 format."""
        formula = Formula(
            code="TEST",
            title="Test",
            section_no=1,
            expression="L",
            variables=[Variable(symbol="L", name="Length", unit="m")],
        )
        parsed, missing, warnings = _parse_variables("L=100", formula)
        assert parsed == {"L": 100.0}
        assert missing == []
        assert warnings == []

    def test_assignment_with_spaces(self):
        """Test L = 100 m format with spaces and unit."""
        formula = Formula(
            code="TEST",
            title="Test",
            section_no=1,
            expression="L",
            variables=[Variable(symbol="L", name="Length", unit="m")],
        )
        parsed, missing, warnings = _parse_variables("L = 100 m", formula)
        assert parsed == {"L": 100.0}
        assert missing == []
        assert warnings == []

    def test_colon_separator(self):
        """Test L : 100.5 format with colon."""
        formula = Formula(
            code="TEST",
            title="Test",
            section_no=1,
            expression="L",
            variables=[Variable(symbol="L", name="Length", unit="m")],
        )
        parsed, missing, warnings = _parse_variables("L : 100.5", formula)
        assert parsed == {"L": 100.5}
        assert missing == []
        assert warnings == []

    def test_comma_decimal_normalization(self):
        """Test 1,5 -> 1.5 comma to dot conversion."""
        formula = Formula(
            code="TEST",
            title="Test",
            section_no=1,
            expression="L",
            variables=[Variable(symbol="L", name="Length", unit="m")],
        )
        parsed, missing, warnings = _parse_variables("L=1,5", formula)
        assert parsed == {"L": 1.5}
        assert missing == []

    def test_missing_variable(self):
        """Test missing required variable."""
        formula = Formula(
            code="TEST",
            title="Test",
            section_no=1,
            expression="L * W",
            variables=[
                Variable(symbol="L", name="Length", unit="m"),
                Variable(symbol="W", name="Width", unit="m"),
            ],
        )
        parsed, missing, warnings = _parse_variables("L=100", formula)
        assert parsed == {"L": 100.0}
        assert len(missing) == 1
        assert missing[0].symbol == "W"

    def test_non_numeric_value_skipped(self):
        """Test non-numeric values are skipped."""
        formula = Formula(
            code="TEST",
            title="Test",
            section_no=1,
            expression="L",
            variables=[Variable(symbol="L", name="Length", unit="m")],
        )
        parsed, missing, warnings = _parse_variables("L=abc", formula)
        assert parsed == {}
        assert len(missing) == 1

    def test_case_insensitive_matching(self):
        """Test case-insensitive variable matching."""
        formula = Formula(
            code="TEST",
            title="Test",
            section_no=1,
            expression="L",
            variables=[Variable(symbol="L", name="Length", unit="m")],
        )
        # Test lowercase
        parsed, missing, warnings = _parse_variables("l=100", formula)
        assert parsed == {"L": 100.0}
        
        # Test by name
        parsed, missing, warnings = _parse_variables("length=100", formula)
        assert parsed == {"L": 100.0}
        
        # Test mixed case
        parsed, missing, warnings = _parse_variables("LENGTH=100", formula)
        assert parsed == {"L": 100.0}

    def test_unit_mismatch_warning(self):
        """Test unit mismatch generates warning but doesn't convert."""
        formula = Formula(
            code="TEST",
            title="Test",
            section_no=1,
            expression="L",
            variables=[Variable(symbol="L", name="Length", unit="m")],
        )
        parsed, missing, warnings = _parse_variables("L=100 cm", formula)
        assert parsed == {"L": 100.0}  # Value used as-is
        assert len(warnings) == 1
        assert "cm" in warnings[0]
        assert "m" in warnings[0]

    def test_multiple_variables(self):
        """Test parsing multiple variables."""
        formula = Formula(
            code="TEST",
            title="Test",
            section_no=1,
            expression="L * W * H",
            variables=[
                Variable(symbol="L", name="Length", unit="m"),
                Variable(symbol="W", name="Width", unit="m"),
                Variable(symbol="H", name="Height", unit="m"),
            ],
        )
        parsed, missing, warnings = _parse_variables(
            "L=100 m, W=50 m, H=10 m", formula
        )
        assert parsed == {"L": 100.0, "W": 50.0, "H": 10.0}
        assert missing == []

    def test_optional_variable(self):
        """Test optional (non-required) variable."""
        formula = Formula(
            code="TEST",
            title="Test",
            section_no=1,
            expression="L",
            variables=[
                Variable(symbol="L", name="Length", unit="m", required=True),
                Variable(symbol="W", name="Width", unit="m", required=False),
            ],
        )
        parsed, missing, warnings = _parse_variables("L=100", formula)
        assert parsed == {"L": 100.0}
        assert missing == []  # W is optional


class TestEvaluateFormula:
    """Tests for _evaluate_formula function."""

    def test_simple_expression(self):
        """Test simple expression evaluation."""
        formula = Formula(
            code="TEST",
            title="Test",
            section_no=1,
            expression="L * 2",
            variables=[Variable(symbol="L", name="Length", unit="m")],
        )
        result, substituted = _evaluate_formula(formula, {"L": 100.0})
        assert result == 200.0
        assert "200" in substituted

    def test_sqrt_function(self):
        """Test sqrt function."""
        formula = Formula(
            code="TEST",
            title="Test",
            section_no=1,
            expression="sqrt(L)",
            variables=[Variable(symbol="L", name="Length", unit="m")],
        )
        result, substituted = _evaluate_formula(formula, {"L": 100.0})
        assert abs(result - 10.0) < 0.0001

    def test_power_operator(self):
        """Test ** power operator (explicit, not ^)."""
        formula = Formula(
            code="TEST",
            title="Test",
            section_no=1,
            expression="L ** 2",
            variables=[Variable(symbol="L", name="Length", unit="m")],
        )
        result, substituted = _evaluate_formula(formula, {"L": 10.0})
        assert result == 100.0

    def test_complex_expression(self):
        """Test complex expression with multiple operations."""
        formula = Formula(
            code="TEST",
            title="Test",
            section_no=1,
            expression="sqrt(L) * W + H",
            variables=[
                Variable(symbol="L", name="Length", unit="m"),
                Variable(symbol="W", name="Width", unit="m"),
                Variable(symbol="H", name="Height", unit="m"),
            ],
        )
        result, substituted = _evaluate_formula(
            formula, {"L": 100.0, "W": 2.0, "H": 5.0}
        )
        # sqrt(100) * 2 + 5 = 10 * 2 + 5 = 25
        assert result == 25.0

    def test_symbol_collision_I(self):
        """CRITICAL: Test I as variable (not imaginary unit)."""
        formula = Formula(
            code="TEST",
            title="Test",
            section_no=1,
            expression="I * 2",
            variables=[Variable(symbol="I", name="Moment of Inertia", unit="m4")],
        )
        result, substituted = _evaluate_formula(formula, {"I": 100.0})
        # Must use input value 100, not sympy's imaginary unit
        assert result == 200.0
        assert "200" in substituted

    def test_symbol_collision_E(self):
        """CRITICAL: Test E as variable (not Euler's number)."""
        formula = Formula(
            code="TEST",
            title="Test",
            section_no=1,
            expression="E * L",
            variables=[
                Variable(symbol="E", name="Modulus of Elasticity", unit="Pa"),
                Variable(symbol="L", name="Length", unit="m"),
            ],
        )
        result, substituted = _evaluate_formula(formula, {"E": 200e9, "L": 2.0})
        # Must use input value 200e9, not sympy's E (Euler's number)
        assert result == 400e9

    def test_symbol_collision_multiple(self):
        """CRITICAL: Test multiple symbol collisions (I, E, N)."""
        formula = Formula(
            code="TEST",
            title="Test",
            section_no=1,
            expression="I * E / N",
            variables=[
                Variable(symbol="I", name="Moment of Inertia", unit="m4"),
                Variable(symbol="E", name="Modulus", unit="Pa"),
                Variable(symbol="N", name="Factor", unit="-"),
            ],
        )
        result, substituted = _evaluate_formula(
            formula, {"I": 100.0, "E": 200.0, "N": 2.0}
        )
        # 100 * 200 / 2 = 10000
        assert result == 10000.0

    def test_division_by_zero(self):
        """CRITICAL: Test division by zero handling."""
        formula = Formula(
            code="TEST",
            title="Test",
            section_no=1,
            expression="L / W",
            variables=[
                Variable(symbol="L", name="Length", unit="m"),
                Variable(symbol="W", name="Width", unit="m"),
            ],
        )
        with pytest.raises(ValueError, match="Pembagian nol|tak hingga"):
            _evaluate_formula(formula, {"L": 100.0, "W": 0.0})

    def test_infinite_result(self):
        """Test infinite result detection."""
        formula = Formula(
            code="TEST",
            title="Test",
            section_no=1,
            expression="1 / L",
            variables=[Variable(symbol="L", name="Length", unit="m")],
        )
        with pytest.raises(ValueError, match="Pembagian nol|tak hingga"):
            _evaluate_formula(formula, {"L": 0.0})

    def test_unknown_symbol_error(self):
        """Test unknown symbol in expression."""
        formula = Formula(
            code="TEST",
            title="Test",
            section_no=1,
            expression="L * X",  # X not in variables
            variables=[Variable(symbol="L", name="Length", unit="m")],
        )
        with pytest.raises(ValueError, match="unknown symbols"):
            _evaluate_formula(formula, {"L": 100.0})

    def test_invalid_expression(self):
        """Test invalid expression syntax."""
        formula = Formula(
            code="TEST",
            title="Test",
            section_no=1,
            expression="L +* W",  # Invalid syntax
            variables=[
                Variable(symbol="L", name="Length", unit="m"),
                Variable(symbol="W", name="Width", unit="m"),
            ],
        )
        with pytest.raises(ValueError, match="Failed to parse"):
            _evaluate_formula(formula, {"L": 100.0, "W": 50.0})


class TestCalculate:
    """Tests for calculate function."""

    def test_successful_calculation(self):
        """Test complete calculation with all variables."""
        formula = Formula(
            code="TEST",
            title="Test Formula",
            section_no=3,
            paragraph_id="3.F.2",
            page_no=45,
            expression="L * W",
            variables=[
                Variable(symbol="L", name="Length", unit="m"),
                Variable(symbol="W", name="Width", unit="m"),
            ],
            result_unit="m2",
        )
        result = calculate("L=100 m, W=50 m", formula)
        
        assert result.success is True
        assert result.result == 5000.0
        assert result.result_unit == "m2"
        assert result.parsed_values == {"L": 100.0, "W": 50.0}
        assert "5000.0000" in result.message
        assert "Sec 3" in result.message
        assert "3.F.2" in result.message

    def test_missing_variables(self):
        """Test calculation with missing required variables."""
        formula = Formula(
            code="TEST",
            title="Test Formula",
            section_no=1,
            expression="L * W * H",
            variables=[
                Variable(symbol="L", name="Length", unit="m"),
                Variable(symbol="W", name="Width", unit="m"),
                Variable(symbol="H", name="Height", unit="m"),
            ],
        )
        result = calculate("L=100", formula)
        
        assert result.success is False
        assert result.result is None
        assert len(result.missing_vars) == 2
        assert "Missing required variables" in result.message
        assert "W" in result.message
        assert "H" in result.message
        assert "Example input" in result.message

    def test_calculation_error(self):
        """Test calculation with evaluation error."""
        formula = Formula(
            code="TEST",
            title="Test Formula",
            section_no=1,
            expression="L / W",
            variables=[
                Variable(symbol="L", name="Length", unit="m"),
                Variable(symbol="W", name="Width", unit="m"),
            ],
        )
        result = calculate("L=100 W=0", formula)
        
        assert result.success is False
        assert result.result is None
        assert result.error  # Error message should not be empty
        assert "pembagian" in result.error.lower() or "nol" in result.error.lower()
        assert "Pembagian nol" in result.message or "nol" in result.message.lower()

    def test_with_unit_warnings(self):
        """Test calculation with unit mismatch warnings."""
        formula = Formula(
            code="TEST",
            title="Test Formula",
            section_no=1,
            expression="L * W",
            variables=[
                Variable(symbol="L", name="Length", unit="m"),
                Variable(symbol="W", name="Width", unit="m"),
            ],
            result_unit="m2",
        )
        result = calculate("L=100 cm, W=50 ft", formula)
        
        assert result.success is True
        assert result.result == 5000.0  # Values used as-is
        assert "Peringatan" in result.message
        assert "cm" in result.message
        assert "ft" in result.message
        assert len(result.warnings) == 2


class TestOptionalVariableDefaults:
    """Tests for optional variable default values (FIX #2a)."""

    def test_optional_var_with_default(self):
        """Test optional var with default is used when not provided."""
        formula = Formula(
            code="TEST",
            title="Test Formula",
            section_no=1,
            expression="L * W",
            variables=[
                Variable(symbol="L", name="Length", unit="m", required=True),
                Variable(symbol="W", name="Width", unit="m", required=False, default=1.0),
            ],
            result_unit="m2",
        )
        result = calculate("L=100", formula)
        
        assert result.success is True
        assert result.result == 100.0  # L=100 * W=1.0 (default)
        assert result.parsed_values == {"L": 100.0, "W": 1.0}
        assert result.missing_vars == []

    def test_optional_var_without_default_in_expression(self):
        """Test optional var without default in expression raises 'belum punya nilai'."""
        formula = Formula(
            code="TEST",
            title="Test Formula",
            section_no=1,
            expression="L * W",
            variables=[
                Variable(symbol="L", name="Length", unit="m", required=True),
                Variable(symbol="W", name="Width", unit="m", required=False, default=None),
            ],
        )
        result = calculate("L=100", formula)
        
        assert result.success is False
        assert "belum punya nilai" in result.error
        assert "W" in result.error
        # Should NOT say "pembagian nol" because W is not substituted
        assert "pembagian nol" not in result.error.lower()

    def test_optional_var_without_default_provided(self):
        """Test optional var without default works when provided."""
        formula = Formula(
            code="TEST",
            title="Test Formula",
            section_no=1,
            expression="L * W",
            variables=[
                Variable(symbol="L", name="Length", unit="m", required=True),
                Variable(symbol="W", name="Width", unit="m", required=False, default=None),
            ],
            result_unit="m2",
        )
        result = calculate("L=100 W=50", formula)
        
        assert result.success is True
        assert result.result == 5000.0
        assert result.parsed_values == {"L": 100.0, "W": 50.0}


class TestWarningSurface:
    """Tests for warning surfacing (FIX #1)."""

    def test_warnings_in_result(self):
        """Test warnings are stored in CalculationResult.warnings."""
        formula = Formula(
            code="TEST",
            title="Test Formula",
            section_no=1,
            expression="L * W",
            variables=[
                Variable(symbol="L", name="Length", unit="m"),
                Variable(symbol="W", name="Width", unit="m"),
            ],
            result_unit="m2",
        )
        result = calculate("L=100 cm, W=50 ft", formula)
        
        assert result.success is True
        assert len(result.warnings) == 2
        assert any("cm" in w for w in result.warnings)
        assert any("ft" in w for w in result.warnings)

    def test_warnings_in_message(self):
        """Test warnings appear in message for success case."""
        formula = Formula(
            code="TEST",
            title="Test Formula",
            section_no=1,
            expression="L * W",
            variables=[
                Variable(symbol="L", name="Length", unit="m"),
                Variable(symbol="W", name="Width", unit="m"),
            ],
            result_unit="m2",
        )
        result = calculate("L=100 cm, W=50", formula)
        
        assert result.success is True
        assert "Peringatan" in result.message
        assert "cm" in result.message
        assert len(result.warnings) == 1

    def test_warnings_in_missing_vars_case(self):
        """Test warnings are stored even when missing vars."""
        formula = Formula(
            code="TEST",
            title="Test Formula",
            section_no=1,
            expression="L * W",
            variables=[
                Variable(symbol="L", name="Length", unit="m"),
                Variable(symbol="W", name="Width", unit="m"),
            ],
        )
        result = calculate("L=100 cm", formula)
        
        assert result.success is False
        assert len(result.missing_vars) == 1
        assert result.missing_vars[0].symbol == "W"
        assert len(result.warnings) == 1
        assert "cm" in result.warnings[0]


class TestErrorMessageSeparation:
    """Tests for error message separation (FIX #2b)."""

    def test_real_division_by_zero(self):
        """Test real division by zero gives 'tak hingga' message."""
        formula = Formula(
            code="TEST",
            title="Test Formula",
            section_no=1,
            expression="L / W",
            variables=[
                Variable(symbol="L", name="Length", unit="m"),
                Variable(symbol="W", name="Width", unit="m"),
            ],
        )
        result = calculate("L=100 W=0", formula)
        
        assert result.success is False
        assert "pembagian nol" in result.error.lower() or "tak hingga" in result.error.lower()
        # Should NOT say "belum punya nilai" because both vars are provided
        assert "belum punya nilai" not in result.error

    def test_unsubstituted_var_message(self):
        """Test unsubstituted var gives 'belum punya nilai' message."""
        formula = Formula(
            code="TEST",
            title="Test Formula",
            section_no=1,
            expression="L * W * H",
            variables=[
                Variable(symbol="L", name="Length", unit="m", required=True),
                Variable(symbol="W", name="Width", unit="m", required=True),
                Variable(symbol="H", name="Height", unit="m", required=False, default=None),
            ],
        )
        result = calculate("L=100 W=50", formula)
        
        assert result.success is False
        assert "belum punya nilai" in result.error
        assert "H" in result.error
        # Should NOT say "pembagian nol" because this is not a division issue
        assert "pembagian nol" not in result.error.lower()


class TestRankFormulas:
    """Tests for rank_formulas function (offline formula matching)."""

    def test_centre_girder_web_selection(self):
        """Test rank_formulas picks CENTRE_GIRDER_WEB for 'tebal web penumpu tengah'."""
        # Create in-memory formula list with CENTRE_GIRDER_WEB and other formulas
        formulas = [
            Formula(
                code="CENTRE_GIRDER_WEB",
                title="Centre girder web thickness",
                section_no=8,
                expression="0.07*L + 5.5",
                variables=[Variable(symbol="L", name="Rule length", unit="m")],
                paragraph_id="A.2.2.1",
                page_no=208,
                result_unit="mm",
                notes="Centre girder web plate thickness",
            ),
            Formula(
                code="FLOOR_WEB_THICKNESS",
                title="Floor plate web thickness",
                section_no=8,
                expression="h/100 + 3.0",
                variables=[Variable(symbol="h", name="Web height", unit="mm")],
                paragraph_id="A.1.2",
                page_no=208,
                result_unit="mm",
                notes="Floor plate web plate thickness",
            ),
            Formula(
                code="FLOOR_PEAK_THICKNESS",
                title="Floor plate thickness in peaks",
                section_no=8,
                expression="0.035*L + 5.0",
                variables=[Variable(symbol="L", name="Rule length", unit="m")],
                paragraph_id="A.1.2.3",
                page_no=208,
                result_unit="mm",
                notes="Floor plate thickness in fore peak and aft peak",
            ),
        ]
        
        query = "Hitung tebal web penumpu tengah dengan L=100"
        ranked = rank_formulas(query, formulas)
        
        # CENTRE_GIRDER_WEB should be ranked first due to synonym match
        # "penumpu tengah" -> "centre girder" synonym
        assert len(ranked) > 0
        assert ranked[0][0].code == "CENTRE_GIRDER_WEB"
        # Should have high score due to synonym match
        assert ranked[0][1] > 10  # Synonym bonus is 15
        
        # Second place should have lower score
        if len(ranked) >= 2:
            assert ranked[1][1] < ranked[0][1]

    def test_empty_formula_list(self):
        """Test rank_formulas with empty formula list."""
        ranked = rank_formulas("test query", [])
        assert ranked == []

    def test_no_match(self):
        """Test rank_formulas with no matching formulas."""
        formulas = [
            Formula(
                code="TEST",
                title="Test Formula",
                section_no=1,
                expression="L",
                variables=[Variable(symbol="L", name="Length", unit="m")],
            ),
        ]
        ranked = rank_formulas("completely unrelated query", formulas)
        assert ranked == []
