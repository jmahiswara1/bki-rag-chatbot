"""Build 29c — Safe tests for deterministic table-row selector.

Categorical/text-matching is DISABLED. Only numeric + unit-compatible + semantic-gated.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.retrieval.table_selector import select_table_row


class TestThresholdUpperBound:
    def test_plate_6mm_selects_leq8(self):
        tbl = "Plate thickness t [mm] | Minimum inner bending radius r [mm]\n" \
              "≤ 4 | 1,0 · t\n≤ 8 | 1,5 · t\n≤ 12 | 2,0 · t\n≤ 24 | 3,0 · t\n> 24 | 5,0 · t"
        r = select_table_row(tbl, "What is the minimum bending radius for a plate with thickness 6 mm?",
                             "en", "Sec 19 | Table 19.1 p.418")
        assert r.selected
        assert "1,5" in r.value_text

    def test_plate_30mm_selects_gt24(self):
        tbl = "Plate thickness t [mm] | Radius r [mm]\n≤ 4 | 1,0\n≤ 8 | 1,5\n≤ 24 | 3,0\n> 24 | 5,0"
        r = select_table_row(tbl, "bending radius for 30 mm plate", "en", "")
        assert r.selected
        assert "5,0" in r.value_text

    def test_plate_4mm_exact_boundary(self):
        tbl = "Thickness [mm] | Radius\n≤ 4 | 1,0\n≤ 8 | 1,5"
        r = select_table_row(tbl, "radius for thickness exactly 4 mm", "en", "")
        assert r.selected
        assert "1,0" in r.value_text


class TestThresholdLowerBound:
    def test_freeing_port_80pct(self):
        tbl = "Breadth [%] | Freeing port area [%]\n40 or less | 20\n75 or more | 10"
        r = select_table_row(tbl, "freeing port area for hatchway breadth 80%", "en", "")
        assert r.selected
        assert r.value_text == "10"

    def test_freeing_port_30pct(self):
        tbl = "Breadth [%] | Freeing port area [%]\n40 or less | 20\n75 or more | 10"
        r = select_table_row(tbl, "freeing port area for 30% breadth", "en", "")
        assert r.selected
        assert r.value_text == "20"


class TestUnitConversion:
    def test_cm_to_mm(self):
        tbl = "Plate thickness t [mm] | Radius r [mm]\n≤ 4 | 1,0\n≤ 8 | 1,5\n≤ 12 | 2,0"
        r = select_table_row(tbl, "radius for 0.6 cm plate", "en", "")
        assert r.selected
        assert "1,5" in r.value_text  # 0.6 cm = 6 mm → ≤8 → 1,5

    def test_m_to_mm(self):
        tbl = "Thickness t [mm] | Value\n≤ 4 | a\n≤ 8 | b\n≤ 12 | c"
        r = select_table_row(tbl, "value for 0.006 m", "en", "")
        assert r.selected
        assert r.value_text == "b"  # 0.006 m = 6 mm → ≤8

    def test_percent_stays_percent(self):
        tbl = "Breadth [%] | Area\n40 or less | 20\n75 or more | 10"
        r = select_table_row(tbl, "area for 30%", "en", "")
        assert r.selected
        assert r.value_text == "20"

    def test_comma_decimal(self):
        tbl = "Thickness t [mm] | Value\n≤ 4 | a\n≤ 8 | b"
        r = select_table_row(tbl, "value for 6,0 mm", "id", "")
        assert r.selected
        assert r.value_text == "b"


class TestUnitSafety:
    def test_unknown_query_unit_fallback(self):
        tbl = "Thickness t [mm] | Value\n≤ 4 | a"
        r = select_table_row(tbl, "value for 6 firkins", "en", "")
        assert not r.selected

    def test_missing_query_unit_dimensioned_table_fallback(self):
        tbl = "Thickness t [mm] | Value\n≤ 4 | a"
        r = select_table_row(tbl, "value for thickness 6", "en", "")
        assert not r.selected

    def test_incompatible_dimension_fallback(self):
        tbl = "Thickness t [mm] | Value\n≤ 4 | a"
        r = select_table_row(tbl, "value for 30%", "en", "")
        assert not r.selected

    def test_length_vs_temperature_fallback(self):
        tbl = "Temperature [°C] | Grade\n≤ 100 | A"
        r = select_table_row(tbl, "grade for 50 mm", "en", "")
        assert not r.selected


class TestSemanticGate:
    def test_bending_radius_matches_thickness_table(self):
        tbl = "Plate thickness t [mm] | Radius r [mm]\n≤ 4 | 1,0"
        r = select_table_row(tbl, "bending radius for 3 mm plate thickness", "en", "")
        assert r.selected

    def test_bending_radius_rejects_velocity_table(self):
        tbl = "Velocity v [mm/s] | Factor\n≤ 4 | 100\n≤ 8 | 200"
        r = select_table_row(tbl, "bending radius for 3 mm", "en", "")
        assert not r.selected  # semantic mismatch: bending+radius vs velocity+factor, mm alone not enough

    def test_generic_query_unitless_table(self):
        tbl = "Number of cross ties | nc\n0 | 1,0\n1 | 0,5"
        r = select_table_row(tbl, "nc for 0 cross ties", "en", "")
        assert r.selected  # "cross"+"ties"+"nc" are discriminative

    def test_too_generic_query_fallback(self):
        tbl = "X [mm] | Y\n≤ 4 | a\n≤ 8 | b"
        r = select_table_row(tbl, "value for 3 mm", "en", "")
        assert not r.selected  # no discriminative tokens in headers or query — "value"+"mm" both too generic


class TestAmbiguousFallback:
    def test_cross_ties_2_fallback(self):
        tbl = "Cross ties | nc\n0 | 1,0\n1 | 0,5\n3 | 0,3\n≥ 3 | 0,2"
        r = select_table_row(tbl, "nc for 2 cross ties", "en", "")
        assert not r.selected

    def test_freeing_port_50pct_fallback(self):
        tbl = "Breadth [%] | Freeing port area [%]\n40 or less | 20\n75 or more | 10"
        r = select_table_row(tbl, "freeing port area for 50% breadth", "en", "")
        assert not r.selected


class TestCategoricalDisabled:
    """All categorical queries must fallback — disabled in Build 29c."""

    def test_lignum_vitae_fallback(self):
        tbl = "Material | Bearing pressure q [N/mm2]\n" \
              "lignum vitae | 2,5\nsynthetic material | 5,5"
        r = select_table_row(tbl, "bearing pressure for lignum vitae", "en", "")
        assert not r.selected

    def test_synthetic_material_fallback(self):
        tbl = "Material | Bearing pressure q [N/mm2]\n" \
              "lignum vitae | 2,5\nsynthetic material | 5,5"
        r = select_table_row(tbl, "pressure for synthetic materials", "en", "")
        assert not r.selected

    def test_steel_not_stem(self):
        tbl = "Steel material grade | Factor\nA | 1,0\nB | 0,8"
        r = select_table_row(tbl, "factor for stem", "en", "")
        assert not r.selected

    def test_deck_not_deckhouse(self):
        tbl = "Deck plating | Thickness\n10 | 20"
        r = select_table_row(tbl, "thickness for deckhouse", "en", "")
        assert not r.selected

    def test_bulkhead_not_bulwark(self):
        tbl = "Bulkhead class | Thickness\nA-60 | 12"
        r = select_table_row(tbl, "thickness for bulwark", "en", "")
        assert not r.selected


class TestIdempotence:
    def test_deterministic_same_result(self):
        tbl = "Thickness [mm] | Radius\n≤ 4 | 1,0\n≤ 8 | 1,5"
        r1 = select_table_row(tbl, "radius for thickness 6 mm", "en", "")
        r2 = select_table_row(tbl, "radius for thickness 6 mm", "en", "")
        assert r1.selected == r2.selected and r1.value_text == r2.value_text


class TestMalformedTableFallback:
    def test_empty_content(self):
        assert not select_table_row("", "value for 5 mm", "en", "").selected

    def test_only_header(self):
        assert not select_table_row("Thickness | Radius", "value for 5 mm", "en", "").selected


class TestCitation:
    def test_table_ref_in_result(self):
        tbl = "Thickness [mm] | Radius\n≤ 4 | 1,0"
        r = select_table_row(tbl, "radius for 3 mm", "en", "Sec 19 p.418")
        assert r.selected
        assert r.table_ref == "Sec 19 p.418" or r.table_ref == "Sec 19 Welded Joints | Table 19.1 p.418"


class TestAdditionalTables:
    """Tables 2.1, 27.1, 27.2 (new — corpus-expanded breadth)."""

    def test_table_21_material_factor(self):
        tbl = "R [N/mm2] eH | k\n315 | 0,78\n355 | 0,72\n390 | 0,66\n460 | 0,62"
        r = select_table_row(tbl, "what is k for yield stress 355 N/mm2", "en", "")
        assert r.selected
        assert r.value_text == "0,72"

    def test_table_271_test_force_mid(self):
        tbl = ("Design force T [kN] | Test force PL [kN]\n"
               "T <= 500 | 2 * T\n"
               "500 < T <= 1500 | T + 500\n"
               "1500 < T | 1,33 * T")
        r = select_table_row(tbl, "test force for 800 kN", "en", "")
        assert r.selected
        assert "T + 500" in r.value_text

    def test_table_271_test_force_low(self):
        tbl = ("Design force T [kN] | Test force PL [kN]\n"
               "T <= 500 | 2 * T\n"
               "500 < T <= 1500 | T + 500\n"
               "1500 < T | 1,33 * T")
        r = select_table_row(tbl, "test force PL for design force 300 kN", "en", "")
        assert r.selected
        assert "2 * T" in r.value_text

    def test_table_242_chafe_chain(self):
        tbl = "Vessel size [DWT] | Chafe chain size [mm]\n<= 100000 | 76\n> 100000 | 76"
        r = select_table_row(tbl, "chafe chain size for 120000 DWT vessel", "en", "")
        assert r.selected
        assert r.value_text == "76"

    def test_table_271_kN_unit_ID(self):
        tbl = ("Design force T [kN] | Test force PL [kN]\n"
               "T <= 500 | 2 * T\n"
               "500 < T <= 1500 | T + 500\n"
               "1500 < T | 1,33 * T")
        r = select_table_row(tbl, "test force untuk design force 800 kN", "id", "")
        assert r.selected
        assert "T + 500" in r.value_text
    def test_10cm_plate_selects_gt24(self):
        tbl = "Plate thickness t [mm] | Radius r [mm]\n≤ 4 | 1,0\n≤ 8 | 1,5\n≤ 12 | 2,0\n≤ 24 | 3,0\n> 24 | 5,0"
        r = select_table_row(tbl, "bending radius for 10 cm plate thickness", "en", "")
        assert r.selected
        assert "5,0" in r.value_text  # 10 cm = 100 mm → >24 → 5,0·t


# ════════════════════════════════════════════════════════════════════
# Build 30 — compound-range predicate coverage
# All fixtures grounded in verified corpus rows (Tables 27.1, 24.2, 39.1)
# or corpus-pattern synthetic tables derived from Tables 19.1, 21.2,
# 9.1, 2.1. No table/page/section/chunk hardcodes in production logic.
# ════════════════════════════════════════════════════════════════════

class TestCompoundRangeTwoSided:
    """a < x ≤ b — Table 27.1 Sec 27 (verbatim source)."""

    T271 = ("Design force T [kN] | Test force PL [kN]\n"
            "T ≤ 500 | 2 · T\n"
            "500 < T ≤ 1500 | T + 500\n"
            "1500 < T | 1,33 · T")

    def test_below_lower_bound(self):
        r = select_table_row(self.T271, "test force for design force 300 kN", "en", "")
        assert r.selected and "2 · T" in r.value_text

    def test_equal_lower_bound_500(self):
        # 500 ∈ ≤500 (inclusive lower of row1); row2 is exclusive at 500
        r = select_table_row(self.T271, "test force for design force exactly 500 kN", "en", "")
        assert r.selected and "2 · T" in r.value_text

    def test_inside_range(self):
        r = select_table_row(self.T271, "test force for design force 800 kN", "en", "")
        assert r.selected and "T + 500" in r.value_text

    def test_equal_upper_bound_1500(self):
        r = select_table_row(self.T271, "test force for design force exactly 1500 kN", "en", "")
        assert r.selected and "T + 500" in r.value_text

    def test_above_upper_bound(self):
        r = select_table_row(self.T271, "test force for design force 2000 kN", "en", "")
        assert r.selected and "1,33 · T" in r.value_text

    def test_id_inside_range(self):
        r = select_table_row(self.T271, "test force untuk design force 800 kN", "id", "")
        assert r.selected and "T + 500" in r.value_text

    def test_id_exact_1500(self):
        r = select_table_row(self.T271, "test force untuk design force tepat 1500 kN", "id", "")
        assert r.selected and "T + 500" in r.value_text

    def test_decimal_comma(self):
        r = select_table_row(self.T271, "test force for design force 1200,5 kN", "en", "")
        assert r.selected and "T + 500" in r.value_text


class TestCompoundTwoOpNoVariable:
    """> a ≤ b — Table 24.2 row 2 (verbatim source, two-op without variable)."""

    T242 = ("Vessel size [tdw] | SWL [kN]\n"
            "≤ 100000 | 2000\n"
            "> 100000 ≤ 150000 | 2500\n"
            "> 150000 | 3500")

    def test_below_first_boundary(self):
        r = select_table_row(self.T242, "SWL for 90000 dwt", "en", "")
        assert r.selected and r.value_text == "2000"

    def test_equal_first_boundary_inclusive(self):
        # 100000 ∈ ≤100000 row (inclusive), not >100000
        r = select_table_row(self.T242, "SWL for exactly 100000 dwt", "en", "")
        assert r.selected and r.value_text == "2000"

    def test_inside_compound(self):
        r = select_table_row(self.T242, "SWL for 120000 dwt", "en", "")
        assert r.selected and r.value_text == "2500"

    def test_equal_upper_boundary_inclusive(self):
        r = select_table_row(self.T242, "SWL for exactly 150000 dwt", "en", "")
        assert r.selected and r.value_text == "2500"

    def test_above_upper(self):
        r = select_table_row(self.T242, "SWL for 200000 dwt", "en", "")
        assert r.selected and r.value_text == "3500"

    def test_id_inside_compound(self):
        r = select_table_row(self.T242, "SWL untuk kapal 120000 dwt", "id", "")
        assert r.selected and r.value_text == "2500"


class TestCompoundExclusiveExclusive:
    """a < x < b — derived from Table 39.1 Sec 39 grammar (two-sided exclusive).

    NOTE: the full 3-column T39.1 (categorical row label + range + value)
    is classified UNSUPPORTED in the Build 30 inventory (multiple
    parseable numeric/categorical columns). These tests use a 2-column
    reduction that isolates the exclusive-exclusive grammar shape — the
    grammar is verified verbatim, the multi-column ambiguity is a
    separate concern handled by TestCompoundMultipleConditionColumns.
    """

    T391 = ("Plate thickness t [mm] | Brittle crack arrest steel requirement\n"
            "50 < t < 100 | Steel grade KI-E36 or 40 with suffix BCA1")

    def test_inside_exclusive_range(self):
        r = select_table_row(self.T391, "brittle crack arrest steel for plate thickness 75 mm", "en", "")
        assert r.selected and "BCA1" in r.value_text

    def test_lower_exclusive_boundary_falls_back(self):
        # 50 is exclusive on the lower bound → no row contains 50
        r = select_table_row(self.T391, "brittle crack arrest steel for plate thickness exactly 50 mm", "en", "")
        assert not r.selected

    def test_upper_exclusive_boundary_falls_back(self):
        r = select_table_row(self.T391, "brittle crack arrest steel for plate thickness exactly 100 mm", "en", "")
        assert not r.selected

    def test_id_inside_exclusive(self):
        r = select_table_row(self.T391, "brittle crack arrest steel untuk plate thickness 60 mm", "id", "")
        assert r.selected and "BCA1" in r.value_text


class TestCompoundBoundaryInclusivity:
    """Synthetic corpus-pattern tables (derived from Tables 19.1, 21.2)."""

    SYN_BEND = ("Plate thickness t [mm] | Minimum inner bending radius r [mm]\n"
                "t ≤ 4 | 1,0 · t\n"
                "4 < t ≤ 8 | 1,5 · t\n"
                "8 < t ≤ 12 | 2,0 · t\n"
                "12 < t ≤ 24 | 3,0 · t\n"
                "t > 24 | 5,0 · t")

    SYN_FREE = ("Breadth of hatchway [%] | Area of freeing ports [%]\n"
                "b ≤ 40 | 20\n"
                "40 < b < 75 | 15\n"
                "b ≥ 75 | 10")

    def test_syn_bend_equal_lower(self):
        r = select_table_row(self.SYN_BEND, "minimum bending radius for plate thickness exactly 4 mm", "en", "")
        assert r.selected and "1,0 · t" in r.value_text

    def test_syn_bend_equal_upper(self):
        r = select_table_row(self.SYN_BEND, "minimum bending radius for plate thickness exactly 8 mm", "en", "")
        assert r.selected and "1,5 · t" in r.value_text

    def test_syn_bend_unit_conversion_cm(self):
        r = select_table_row(self.SYN_BEND, "minimum bending radius for 0.6 cm plate", "en", "")
        assert r.selected and "1,5 · t" in r.value_text

    def test_syn_bend_unit_conversion_m(self):
        r = select_table_row(self.SYN_BEND, "minimum bending radius for 0.006 m plate", "en", "")
        assert r.selected and "1,5 · t" in r.value_text

    def test_syn_free_mixed_inclusive_exclusive_lower_eq(self):
        # 40 ∈ b≤40 row (inclusive), not 40<b<75
        r = select_table_row(self.SYN_FREE, "freeing port area for hatchway breadth exactly 40%", "en", "")
        assert r.selected and r.value_text == "20"

    def test_syn_free_mixed_inclusive_exclusive_upper_eq(self):
        # 75 ∈ b≥75 row (inclusive), not 40<b<75
        r = select_table_row(self.SYN_FREE, "freeing port area for hatchway breadth exactly 75%", "en", "")
        assert r.selected and r.value_text == "10"

    def test_syn_free_inside_exclusive(self):
        r = select_table_row(self.SYN_FREE, "freeing port area for hatchway breadth 50%", "en", "")
        assert r.selected and r.value_text == "15"


class TestCompoundUnorderedRows:
    """Determinism must not depend on row order."""

    def test_unordered_compound_rows(self):
        ordered = ("Thickness t [mm] | Factor\n"
                   "t ≤ 4 | a\n"
                   "4 < t ≤ 8 | b\n"
                   "t > 8 | c")
        reversed_rows = ("Thickness t [mm] | Factor\n"
                         "t > 8 | c\n"
                         "4 < t ≤ 8 | b\n"
                         "t ≤ 4 | a")
        r1 = select_table_row(ordered, "factor for thickness 6 mm", "en", "")
        r2 = select_table_row(reversed_rows, "factor for thickness 6 mm", "en", "")
        assert r1.selected and r2.selected
        assert r1.value_text == r2.value_text == "b"


class TestCompoundOverlapGapFallback:
    """True overlaps, gaps, and duplicate ranges MUST fall back."""

    def test_overlapping_compound_and_one_sided_falls_back(self):
        # 9 mm matches both "t ≤ 10" and "8 < t ≤ 20" → true overlap
        tbl = ("Thickness t [mm] | Factor\n"
               "t ≤ 10 | a\n"
               "8 < t ≤ 20 | b\n"
               "t > 20 | c")
        r = select_table_row(tbl, "factor for thickness 9 mm", "en", "")
        assert not r.selected

    def test_overlapping_compound_unambiguous_path_still_works(self):
        # 15 mm matches only "8 < t ≤ 20" → single match, OK
        tbl = ("Thickness t [mm] | Factor\n"
               "t ≤ 10 | a\n"
               "8 < t ≤ 20 | b\n"
               "t > 20 | c")
        r = select_table_row(tbl, "factor for thickness 15 mm", "en", "")
        assert r.selected and r.value_text == "b"

    def test_gap_between_ranges_falls_back(self):
        # 15 mm in the gap (10, 20] → no row matches
        tbl = ("Thickness t [mm] | Factor\n"
               "t ≤ 10 | a\n"
               "20 < t ≤ 30 | b\n"
               "t > 30 | c")
        r = select_table_row(tbl, "factor for thickness 15 mm", "en", "")
        assert not r.selected

    def test_contradictory_bounds_fall_back(self):
        # lower > upper → predicate is None → parse fails → fallback
        tbl = ("Thickness t [mm] | Factor\n10 < t ≤ 5 | a")
        r = select_table_row(tbl, "factor for thickness 7 mm", "en", "")
        assert not r.selected

    def test_duplicate_equivalent_ranges_tightest_tie_falls_back(self):
        # Two identical one-sided rows → tightest tie → fallback
        tbl = ("Thickness t [mm] | Factor\n≤ 8 | a\n≤ 8 | b")
        r = select_table_row(tbl, "factor for thickness 6 mm", "en", "")
        assert not r.selected


class TestCompoundMultipleConditionColumns:
    """Multiple inequality-bearing columns → ambiguous → fallback."""

    def test_two_ineq_columns_fall_back(self):
        tbl = ("Thickness t [mm] | Depth d [mm] | Factor\n"
               "≤ 10 | ≤ 50 | a\n"
               "10 < t ≤ 20 | 50 < d ≤ 100 | b")
        r = select_table_row(tbl, "factor for thickness 15 mm", "en", "")
        assert not r.selected

    def test_explicit_var_two_ineq_columns_fall_back(self):
        tbl = ("Thickness t [mm] | Width w [mm] | Factor\n"
               "t ≤ 10 | w ≤ 100 | a\n"
               "10 < t ≤ 20 | 100 < w ≤ 200 | b")
        r = select_table_row(tbl, "factor for thickness 15 mm", "en", "")
        assert not r.selected


class TestCompoundMalformedPredicateFallback:
    """Rows the parser cannot read never get selected."""

    def test_malformed_row_only_falls_back(self):
        # The single data row is contradictory → predicate None → no match
        tbl = "Thickness t [mm] | Factor\n10 < t ≤ 5 | a"
        r = select_table_row(tbl, "factor for thickness 7 mm", "en", "")
        assert not r.selected

    def test_mixed_direction_compound_falls_back(self):
        # "5 > t ≤ 20" mixes directions → None
        tbl = "Thickness t [mm] | Factor\n5 > t ≤ 20 | a"
        r = select_table_row(tbl, "factor for thickness 7 mm", "en", "")
        assert not r.selected


class TestCompoundUnitAndSemanticSafety:
    """Compound path inherits the same unit + semantic gates as Build 29."""

    def test_missing_query_unit_on_compound_falls_back(self):
        tbl = ("Design force T [kN] | Test force PL [kN]\n"
               "T ≤ 500 | 2 · T\n500 < T ≤ 1500 | T + 500\n1500 < T | 1,33 · T")
        r = select_table_row(tbl, "test force for design force 800", "en", "")
        assert not r.selected

    def test_incompatible_unit_on_compound_falls_back(self):
        tbl = ("Design force T [kN] | Test force PL [kN]\n"
               "T ≤ 500 | 2 · T\n500 < T ≤ 1500 | T + 500\n1500 < T | 1,33 · T")
        r = select_table_row(tbl, "test force for design force 800 mm", "en", "")
        assert not r.selected

    def test_wrong_topic_compound_falls_back(self):
        # semantic mismatch: bending query vs velocity table (compound variant)
        tbl = ("Velocity v [mm/s] | Factor\nv ≤ 4 | 100\n4 < v ≤ 8 | 200\nv > 8 | 300")
        r = select_table_row(tbl, "bending radius for plate 6 mm", "en", "")
        assert not r.selected

    def test_generic_query_compound_falls_back(self):
        tbl = ("Plate thickness t [mm] | Factor\n"
               "t ≤ 4 | a\n4 < t ≤ 8 | b")
        r = select_table_row(tbl, "value for 6 mm", "en", "")
        assert not r.selected


class TestCompoundProvenancePreservation:
    """Selected row_text and table_ref are preserved verbatim."""

    def test_row_text_and_ref_preserved(self):
        tbl = ("Design force T [kN] | Test force PL [kN]\n"
               "T ≤ 500 | 2 · T\n500 < T ≤ 1500 | T + 500\n1500 < T | 1,33 · T")
        r = select_table_row(tbl, "test force for 800 kN", "en", "Sec 27 | Table 27.1 p.628")
        assert r.selected
        assert r.table_ref == "Sec 27 | Table 27.1 p.628"
        assert "500 < T ≤ 1500" in r.row_text or "500 < t ≤ 1500" in r.row_text.lower()


class TestCompoundBackwardCompat:
    """Build 29 single-threshold behavior must remain unchanged."""

    def test_nested_single_threshold_tightest(self):
        # Build 29 pattern: nested one-sided thresholds resolve by tightest
        tbl = ("Plate thickness t [mm] | Radius r [mm]\n"
               "≤ 4 | 1,0\n≤ 8 | 1,5\n≤ 12 | 2,0\n≤ 24 | 3,0\n> 24 | 5,0")
        r = select_table_row(tbl, "bending radius for plate 6 mm", "en", "")
        assert r.selected and "1,5" in r.value_text

    def test_cold_bending_t10_regression(self):
        # Exact cold-bending t=10 mm regression from Build 29
        tbl = ("Plate thickness t [mm] | Minimum inner bending radius r [mm]\n"
               "≤ 4 | 1,0 · t\n≤ 8 | 1,5 · t\n≤ 12 | 2,0 · t\n≤ 24 | 3,0 · t\n> 24 | 5,0 · t")
        r = select_table_row(tbl, "bending radius for plate thickness 10 mm", "en", "")
        assert r.selected and "2,0 · t" in r.value_text

    def test_freeing_port_80pct_build29(self):
        tbl = "Breadth [%] | Freeing port area [%]\n40 or less | 20\n75 or more | 10"
        r = select_table_row(tbl, "freeing port area for hatchway breadth 80%", "en", "")
        assert r.selected and r.value_text == "10"

    def test_categorical_disabled_lignum_vitae(self):
        tbl = ("Material | Bearing pressure q [N/mm2]\n"
               "lignum vitae | 2,5\nsynthetic material | 5,5")
        r = select_table_row(tbl, "bearing pressure for lignum vitae", "en", "")
        assert not r.selected


class TestCompoundIdempotence:
    def test_compound_deterministic_repeated(self):
        tbl = ("Design force T [kN] | Test force PL [kN]\n"
               "T ≤ 500 | 2 · T\n500 < T ≤ 1500 | T + 500\n1500 < T | 1,33 · T")
        r1 = select_table_row(tbl, "test force for 800 kN", "en", "")
        r2 = select_table_row(tbl, "test force for 800 kN", "en", "")
        r3 = select_table_row(tbl, "test force for 800 kN", "en", "")
        assert r1.selected == r2.selected == r3.selected
        assert r1.value_text == r2.value_text == r3.value_text
