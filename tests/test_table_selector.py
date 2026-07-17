"""Build 29 — Tests for deterministic table-row selector."""
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
        assert "≤ 8" in r.row_text

    def test_plate_30mm_selects_gt24(self):
        tbl = "Plate thickness t [mm] | Radius r [mm]\n≤ 4 | 1,0\n≤ 8 | 1,5\n≤ 24 | 3,0\n> 24 | 5,0"
        r = select_table_row(tbl, "bending radius for 30 mm plate", "en", "")
        assert r.selected
        assert "5,0" in r.value_text

    def test_plate_4mm_exact_boundary(self):
        tbl = "Thickness | Radius\n≤ 4 | 1,0\n≤ 8 | 1,5"
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


class TestExactMatch:
    def test_cross_ties_zero(self):
        tbl = "Cross ties | nc\n0 | 1,0\n1 | 0,5\n3 | 0,3\n≥ 3 | 0,2"
        r = select_table_row(tbl, "nc for 0 cross ties", "en", "")
        assert r.selected
        assert r.value_text == "1,0"


class TestAmbiguousFallback:
    def test_cross_ties_2_fallback(self):
        tbl = "Cross ties | nc\n0 | 1,0\n1 | 0,5\n3 | 0,3\n≥ 3 | 0,2"
        r = select_table_row(tbl, "nc for 2 cross ties", "en", "")
        assert not r.selected

    def test_freeing_port_50pct_fallback(self):
        tbl = "Breadth [%] | Freeing port area [%]\n40 or less | 20\n75 or more | 10"
        r = select_table_row(tbl, "freeing port area for 50% breadth", "en", "")
        assert not r.selected


class TestCategoricalTextMatch:
    def test_lignum_vitae(self):
        tbl = "Material | Bearing pressure q [N/mm2]\n" \
              "lignum vitae | 2,5\nwhite metal | 4,5\nsynthetic material > 60 shore | 5,5\nSteel, bronze | 7,0"
        r = select_table_row(tbl, "bearing pressure for lignum vitae", "en", "")
        assert r.selected
        assert "2,5" in r.value_text

    def test_synthetic_material(self):
        tbl = "Material | Bearing pressure q [N/mm2]\n" \
              "lignum vitae | 2,5\nwhite metal | 4,5\nsynthetic material with hardness greater than 60 shore | 5,5\nSteel bronze | 7,0"
        r = select_table_row(tbl, "What is the bearing pressure for synthetic materials?", "en", "")
        assert r.selected
        assert "5,5" in r.value_text


class TestIDLanguage:
    def test_bending_radius_id(self):
        tbl = "Tebal pelat t [mm] | Radius tekuk minimum r [mm]\n" \
              "≤ 4 | 1,0 · t\n≤ 8 | 1,5 · t\n≤ 12 | 2,0 · t"
        r = select_table_row(tbl, "Berapa radius tekuk minimum untuk pelat 6 mm?", "id", "")
        assert r.selected
        assert "1,5" in r.value_text


class TestIdempotence:
    def test_deterministic_same_result(self):
        tbl = "Thickness | Radius\n≤ 4 | 1,0\n≤ 8 | 1,5"
        r1 = select_table_row(tbl, "radius for thickness 6 mm", "en", "")
        r2 = select_table_row(tbl, "radius for thickness 6 mm", "en", "")
        assert r1.selected == r2.selected
        assert r1.value_text == r2.value_text

    def test_deterministic_fallback_same(self):
        tbl = "X | Y\n0 | a\n1 | b"
        r1 = select_table_row(tbl, "value for x=2", "en", "")
        r2 = select_table_row(tbl, "value for x=2", "en", "")
        assert not r1.selected
        assert not r2.selected


class TestMalformedTableFallback:
    def test_empty_content(self):
        r = select_table_row("", "value for 5", "en", "")
        assert not r.selected

    def test_only_header(self):
        r = select_table_row("Thickness | Radius", "value for 5", "en", "")
        assert not r.selected


class TestCitation:
    def test_table_ref_in_result(self):
        tbl = "Thickness | Radius\n≤ 4 | 1,0"
        r = select_table_row(tbl, "radius for 3 mm", "en",
                             "Sec 19 Welded Joints | Table 19.1 p.418")
        assert r.table_ref == "Sec 19 Welded Joints | Table 19.1 p.418"
