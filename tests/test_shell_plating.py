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

@pytest.fixture
def side_greater_90():
    return Formula(
        code='SIDE_PLATING_L_GREATER_90',
        title='Side shell plating thickness (L >= 90m)',
        section_no=6,
        expression='Max(18.3 * nf * a * sqrt(pS / (176.1/k)) + tK, 1.21 * a * sqrt(pS * k) + tK, 18.3 * nf * a * sqrt(pS1 / (190.8/k)) + tK)',
        variables=[
            Variable(symbol='L', name='Length of ship', unit='m', required=True),
            Variable(symbol='pS', name='Side load', unit='kN/m2', required=True),
            Variable(symbol='pS1', name='Side load 1', unit='kN/m2', required=True),
            Variable(symbol='a', name='Stiffener spacing', unit='m', required=True),
            Variable(symbol='k', name='Material factor', unit='', required=True, default=1.0),
            Variable(symbol='nf', name='Framing factor', unit='', required=True, default=1.0),
            Variable(symbol='tK', name='Corrosion addition', unit='mm', required=True, default=1.5)
        ]
    )

def test_shell_plating_bottom(bottom_greater_90):
    query = "L = 100, pB = 60, a = 600 mm"
    res = calculate(query, bottom_greater_90)
    assert res.success is True
    assert "Auto-converted 'a' from mm to m: 0.6 m" in res.message
    # a=0.6, pB=60, k=1, tK=1.5, nf=1
    # max(18.3 * 1 * 0.6 * sqrt(60 / 200.2) + 1.5, 1.21 * 0.6 * sqrt(60) + 1.5)
    # max(10.98 * 0.5474 + 1.5, 0.726 * 7.745 + 1.5) = max(7.51, 7.12) = 7.51
    assert 7.50 < res.result < 7.52

def test_shell_plating_side_missing_pS1(side_greater_90):
    query = "L = 100, pS = 60, a = 600 mm, k = 1"
    res = calculate(query, side_greater_90)
    assert res.success is True
    assert "Catatan: tS3 dilewati" in res.message

def test_shell_plating_side_with_pS1(side_greater_90):
    query = "L = 100, pS = 60, pS1 = 80, a = 600 mm, k = 1"
    res = calculate(query, side_greater_90)
    assert res.success is True
    assert "Catatan: tS3 dilewati" not in res.message
    # Check that pS1 branch was taken (which gives larger value)
    assert 8.6 < res.result < 8.7

def test_shell_plating_missing_pB(bottom_greater_90):
    query = "L = 100, a = 600 mm"
    res = calculate(query, bottom_greater_90)
    assert res.success is False
    assert "Missing required variables" in res.message
    assert "pB (Bottom load)" in res.message
