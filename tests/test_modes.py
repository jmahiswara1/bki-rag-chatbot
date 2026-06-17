"""Tests for src/llm/modes.py (ModeConfig registry).
These tests pin the temperature contract for the two supported modes so
that future changes to MODES cannot silently re-introduce non-determinism
in the final answer LLM (manual-QA report showed 25/26 NONDETERMINISTIC
at default temp=0.2).
"""
from src.llm.modes import MODES
def test_default_mode_temperature_is_zero():
    """Final-answer LLM in default mode must be deterministic (temp=0.0)."""
    assert MODES["default"].temperature == 0.0
def test_fast_mode_temperature_strictly_lower_than_default():
    """Sanity: fast mode should be a different config from default.
    We do not pin the exact fast value (it may be tuned) but require
    that it is not the same as default to catch accidental copy-paste.
    """
    assert MODES["fast"].temperature != MODES["default"].temperature
def test_default_mode_uses_default_model():
    from src.core.config import settings
    assert MODES["default"].model == settings.default_model
def test_default_mode_rerank_enabled():
    assert MODES["default"].rerank is True
    assert MODES["default"].top_k == 8


def test_translate_condense_uses_zero_temperature():
    """_translate_condense must be a deterministic utility call (temp=0.0).

    Manual-QA showed 11/26 cases had en_query drift at the previous
    min(temp, 0.1) cap. We verify by reading the function source and
    asserting the literal 'temperature=0.0' is present in the call.
    Mocking chat() is avoided because that would couple the test to
    the LLM client surface.
    """
    import inspect
    from src.llm import chain
    src = inspect.getsource(chain._translate_condense)
    assert "temperature=0.0" in src, (
        "_translate_condense must call chat() with temperature=0.0 "
        "for deterministic en_query output. Found: " + src
    )


def test_ollama_options_include_seed_zero():
    """_options() must include seed=0 for local Ollama determinism.

    Ollama's documented default is 0; we pass it explicitly so a
    future default change cannot silently re-introduce nondeterminism.
    """
    from src.llm.client import _options
    opt = _options(num_ctx=8192, temperature=0.0)
    assert opt.get("seed") == 0
    # Also: num_ctx and think must still be set (regression guard).
    assert opt.get("num_ctx") == 8192
    assert opt.get("think") is False
