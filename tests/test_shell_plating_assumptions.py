import pytest
from src.calc.engine import calculate
from src.core.models import Formula, Variable

@pytest.fixture
def bottom_greater_90():
    return Formula(
        code='BOTTOM_PLATING_L_GREATER_90',
        title='Bottom shell plating thickness (L >= 90m)',
        section_no=6,
        expression='Max(18.3 * nf * a * sqrt(pB / (200.2/k)) + tK, 1.21 * a * sqrt(pB * k) + tK)',
        variables=[
            Variable(symbol='L', name='Length of ship', unit='m', required=True),
            Variable(symbol='pB', name='Bottom load', unit='kN/m2', required=True),
            Variable(symbol='a', name='Stiffener spacing', unit='m', required=True),
            Variable(symbol='k', name='Material factor', unit='', required=True, default=1.0),
            Variable(symbol='nf', name='Framing factor', unit='', required=True, default=1.0),
            Variable(symbol='tK', name='Corrosion addition', unit='mm', required=True, default=1.5)
        ]
    )

def test_a_no_unit_small_assumes_meter(bottom_greater_90):
    query = "L = 100, pB = 60, a = 0.6"
    res = calculate(query, bottom_greater_90)
    assert res.success is True
    assert res.parsed_values['a'] == 0.6
    assert 7.50 < res.result < 7.52
    assert any("a=0.6 m" in w and "tanpa satuan ditafsirkan sebagai meter" in w for w in res.warnings)

def test_a_no_unit_large_assumes_mm(bottom_greater_90):
    query = "L = 100, pB = 60, a = 600"
    res = calculate(query, bottom_greater_90)
    assert res.success is True
    assert res.parsed_values['a'] == 0.6
    assert 7.50 < res.result < 7.52
    assert any("terlalu besar untuk meter; ditafsirkan sebagai mm" in w for w in res.warnings)

def test_a_explicit_mm(bottom_greater_90):
    query = "L = 100, pB = 60, a = 600 mm"
    res = calculate(query, bottom_greater_90)
    assert res.success is True
    assert res.parsed_values['a'] == 0.6
    assert 7.50 < res.result < 7.52
    # No unit ambiguitiy warning
    assert not any("tanpa satuan ditafsirkan" in w for w in res.warnings)

def test_framing_longitudinal(bottom_greater_90):
    query = "L = 100, pB = 60, a = 600 mm, longitudinal framing"
    res = calculate(query, bottom_greater_90)
    assert res.success is True
    assert res.parsed_values['nf'] == 0.83
    # Check that longitudinal result is smaller
    assert 7.12 < res.result < 7.13
    assert any("longitudinal framing" in w.lower() for w in res.warnings)

def test_framing_transverse_explicit(bottom_greater_90):
    query = "L = 100, pB = 60, a = 600 mm, transverse"
    res = calculate(query, bottom_greater_90)
    assert res.success is True
    assert res.parsed_values['nf'] == 1.0
    assert 7.50 < res.result < 7.52

def test_framing_missing_assumes_transverse(bottom_greater_90):
    query = "L = 100, pB = 60, a = 600 mm"
    res = calculate(query, bottom_greater_90)
    assert res.success is True
    assert res.parsed_values['nf'] == 1.0
    assert 7.50 < res.result < 7.52
    assert any("Asumsi: nf=1.0" in w for w in res.warnings)

def test_high_tensile_missing_k_rejects(bottom_greater_90):
    query = "L = 100, pB = 60, a = 600 mm, high tensile"
    res = calculate(query, bottom_greater_90)
    assert res.success is False
    assert "nilai material factor (k) tidak diberikan" in res.message

def test_mild_steel(bottom_greater_90):
    query = "L = 100, pB = 60, a = 600 mm, mild steel"
    res = calculate(query, bottom_greater_90)
    assert res.success is True
    assert res.parsed_values['k'] == 1.0
    assert 7.50 < res.result < 7.52
    assert not any("k=1.0 (mild steel)" in w for w in res.warnings)

def test_no_grade_default_k(bottom_greater_90):
    query = "L = 100, pB = 60, a = 600 mm"
    res = calculate(query, bottom_greater_90)
    assert res.success is True
    assert res.parsed_values['k'] == 1.0
    assert 7.50 < res.result < 7.52
    assert any("k=1.0 (mild steel)" in w for w in res.warnings)

def test_k_explicit(bottom_greater_90):
    query = "L = 100, pB = 60, a = 600 mm, k = 0.78, high tensile"
    res = calculate(query, bottom_greater_90)
    assert res.success is True
    assert res.parsed_values['k'] == 0.78
    assert 6.80 < res.result < 6.81

def test_a_out_of_bounds(bottom_greater_90):
    query = "L = 100, pB = 60, a = 2.5 m"
    res = calculate(query, bottom_greater_90)
    assert res.success is False
    assert "luar rentang wajar" in res.message

def test_pB_negative_rejected(bottom_greater_90):
    query = "L = 100, pB = -60, a = 600 mm"
    res = calculate(query, bottom_greater_90)
    assert res.success is False
    assert res.parsed_values['pB'] == -60.0
    assert "Nilai pB harus positif" in res.message

def test_pB_zero_rejected(bottom_greater_90):
    query = "L = 100, pB = 0, a = 600 mm"
    res = calculate(query, bottom_greater_90)
    assert res.success is False
    assert res.parsed_values['pB'] == 0.0
    assert "Nilai pB harus positif" in res.message

def test_pB_extreme_warned(bottom_greater_90):
    query = "L = 100, pB = 99999, a = 600 mm"
    res = calculate(query, bottom_greater_90)
    assert res.success is True
    assert res.parsed_values['pB'] == 99999.0
    assert any("pB=99999.0 sangat besar (implausibel)" in w for w in res.warnings)
    assert any("tebal pelat sangat besar" in w for w in res.warnings)

def test_pB_normal_no_warnings(bottom_greater_90):
    query = "L = 100, pB = 60, a = 600 mm, mild steel"
    res = calculate(query, bottom_greater_90)
    assert res.success is True
    assert res.parsed_values['pB'] == 60.0
    assert not any("sangat besar (implausibel)" in w for w in res.warnings)
    assert not any("tebal pelat sangat besar" in w for w in res.warnings)
    assert 7.50 < res.result < 7.52

