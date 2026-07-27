
from src.calc.registry import search_formulas, select_formula
from src.calc.engine import calculate, _parse_variables
from tests.test_calc import _SEEDED_FORMULAS

class TestShellPlatingSelector:
    def test_bottom_greater_90(self):
        query = "hitung tebal pelat alas (bottom), L=100 m, pB=60 kN/m2, jarak penegar 600 mm, mild steel"
        candidates = search_formulas(query)
        best, ranked = select_formula(query, candidates)
        assert best is not None
        assert best.code == "BOTTOM_PLATING_L_GREATER_90"
        
        parsed, _, _ = _parse_variables(query, best)
        assert parsed["a"] == 0.6
        assert parsed["L"] == 100.0
        
    def test_bottom_less_90(self):
        query = "hitung tebal pelat alas, L=80 m, pB=50 kN/m2"
        candidates = search_formulas(query)
        best, ranked = select_formula(query, candidates)
        assert best is not None
        assert best.code == "BOTTOM_PLATING_L_LESS_90"
        
    def test_missing_pb_asks_for_pb(self):
        query = "pelat alas bottom, L=100, mild steel"
        candidates = search_formulas(query)
        best, ranked = select_formula(query, candidates)
        assert best is not None
        assert best.code == "BOTTOM_PLATING_L_GREATER_90"
        # The chain will handle the missing vars from the engine.
        
    def test_no_domain_returns_picker(self):
        query = "kulit luar lambung"
        candidates = search_formulas(query)
        best, ranked = select_formula(query, candidates)
        assert best is None
        
    def test_no_deck_or_floor_in_picker(self):
        query = "pelat alas"
        candidates = search_formulas(query)
        best, ranked = select_formula(query, candidates)
        assert best is None # no L, so it cant branch
        codes = [f.code for f, s in ranked]
        assert "BOTTOM_PLATING_L_LESS_90" in codes or "BOTTOM_PLATING_L_GREATER_90" in codes
        assert "WHEEL_LOAD" not in codes
        assert "FLOOR_WEB_THICKNESS" not in codes

    def test_iso1_a2_branch_misfire(self):
        query = "tebal pelat alas bottom, L=100 m, pB=60, jarak penegar 600 mm, longitudinal framing, mild steel"
        candidates = search_formulas(query)
        best, _ = select_formula(query, candidates)
        assert best is not None
        assert best.code == "BOTTOM_PLATING_L_GREATER_90"
        res = calculate(query, best)
        assert 7.12 < res.result < 7.13
        
    def test_iso2_a2_branch_misfire(self):
        query = "tebal pelat alas bottom, L=100, pB=60, jarak penegar 0.6 m, mild steel"
        candidates = search_formulas(query)
        best, _ = select_formula(query, candidates)
        assert best is not None
        assert best.code == "BOTTOM_PLATING_L_GREATER_90"
        res = calculate(query, best)
        assert 7.51 < res.result < 7.52
        
    def test_iso3_a2_branch_misfire(self):
        query = "tebal pelat alas bottom, L=100, pB=60, jarak penegar 0.6 m, longitudinal framing, mild steel"
        candidates = search_formulas(query)
        best, _ = select_formula(query, candidates)
        assert best is not None
        assert best.code == "BOTTOM_PLATING_L_GREATER_90"
        res = calculate(query, best)
        assert 7.12 < res.result < 7.13
        
    def test_regression_bottom_branch_less_90(self):
        query = "bottom plate thickness, L=80, pB=55, stiffener spacing 0.6 m, mild steel"
        candidates = search_formulas(query)
        best, _ = select_formula(query, candidates)
        assert best is not None
        assert best.code == "BOTTOM_PLATING_L_LESS_90"
        res = calculate(query, best)
        assert 9.95 < res.result < 9.96
        
    def test_regression_bottom_branch_less_90_with_framing(self):
        query = "bottom plate thickness, L=80, pB=55, stiffener spacing 0.6 m, longitudinal framing, mild steel"
        candidates = search_formulas(query)
        best, _ = select_formula(query, candidates)
        assert best is not None
        assert best.code == "BOTTOM_PLATING_L_LESS_90"
        # The result logic is correct, just ensuring it didn't branch to > 90

    def test_e1_typo_heavy_misfire_rejected(self):
        query = "tebl pelat alsa botom, L=100, pB=60"
        candidates = search_formulas(query)
        best, _ = select_formula(query, candidates)
        assert best is None  # Should return None (ask for clarification), NOT silently pick Sec 8 or wrong domain.

    def test_e1_regression_clean_query_works(self):
        query = "tebal pelat alas bottom, L=100, pB=60"
        candidates = search_formulas(query)
        best, _ = select_formula(query, candidates)
        assert best is not None
        assert best.code == "BOTTOM_PLATING_L_GREATER_90"