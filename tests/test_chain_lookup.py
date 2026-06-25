"""Integration tests for lookup-first chain integration (Fase C).

Tests that chain_answer() short-circuits through lookup_rules before
hitting retrieval/LLM.  All tests use monkeypatching — no live DB,
no Ollama, no Supabase.
"""
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, r"E:\Project\bki-rag-chatbot")

from src.core.models import Intent
from src.llm import chain
from src.llm.lookup import LookupRule, LookupMatch


# ---------------------------------------------------------------------------
# Fixture: same 8 verified rules from the DB seed (matching tests/test_lookup.py)
# ---------------------------------------------------------------------------

_FIXTURE_RULES: list[LookupRule] = [
    LookupRule(
        topic="restricted_service_modulus_reduction", parameter="P",
        value_text="5%", value_num=5, unit="%",
        section_no=5, paragraph_id="C.2.1", page_no=147,
        source_quote="For ships classed for a restricted range of service, the minimum section modulus may be reduced as follows: P (Restricted Ocean Service): by 5%; L (Coasting Service): by 15%; T (Sheltered Water Service): by 25%.",
        trigger_terms=("restricted service", "restricted range of service", "section modulus",
                       "modulus reduction", "reduced", "servis terbatas", "modulus penampang",
                       "dikurangi", "restricted ocean", "P"),
    ),
    LookupRule(
        topic="restricted_service_modulus_reduction", parameter="L",
        value_text="15%", value_num=15, unit="%",
        section_no=5, paragraph_id="C.2.1", page_no=147,
        source_quote="For ships classed for a restricted range of service, the minimum section modulus may be reduced as follows: P (Restricted Ocean Service): by 5%; L (Coasting Service): by 15%; T (Sheltered Water Service): by 25%.",
        trigger_terms=("restricted service", "restricted range of service", "section modulus",
                       "modulus reduction", "reduced", "servis terbatas", "modulus penampang",
                       "dikurangi", "coasting service", "L"),
    ),
    LookupRule(
        topic="restricted_service_modulus_reduction", parameter="T",
        value_text="25%", value_num=25, unit="%",
        section_no=5, paragraph_id="C.2.1", page_no=147,
        source_quote="For ships classed for a restricted range of service, the minimum section modulus may be reduced as follows: P (Restricted Ocean Service): by 5%; L (Coasting Service): by 15%; T (Sheltered Water Service): by 25%.",
        trigger_terms=("restricted service", "restricted range of service", "section modulus",
                       "modulus reduction", "reduced", "servis terbatas", "modulus penampang",
                       "dikurangi", "sheltered water", "T"),
    ),
    LookupRule(
        topic="forepeak_stringer_spacing", parameter=None,
        value_text="tidak lebih dari 2,6 m (diukur vertikal)", value_num=2.6, unit="m",
        section_no=9, paragraph_id="A.5.2.1", page_no=228,
        source_quote="Forward of the collision bulkhead, tiers of beams (beams at every other frame) generally spaced not more than 2,6 m apart, measured vertically, are to be arranged below the lowest deck within the forepeak.",
        trigger_terms=("forepeak", "fore peak", "collision bulkhead", "tiers of beams",
                       "stringer", "stringer plate", "senta", "haluan", "ceruk haluan",
                       "spacing", "jarak", "2,6 m"),
    ),
    LookupRule(
        topic="tug_winch_drum_diameter", parameter=None,
        value_text="tidak kurang dari 14 x diameter towrope", value_num=14, unit="x",
        section_no=27, paragraph_id="C.5.2.3", page_no=630,
        source_quote="The diameter of the winch drum is to be not less than 14 times the towrope diameter.",
        trigger_terms=("winch drum", "towrope", "tow rope", "towline", "tug", "tunda",
                       "derek tunda", "winch", "diameter drum", "14 times"),
    ),
    LookupRule(
        topic="fire_door_closing_time", parameter="hinged",
        value_text="tidak lebih dari 40 s dan tidak kurang dari 10 s", value_num=40, unit="s",
        section_no=22, paragraph_id="C.6.6.2", page_no=494,
        source_quote="The approximate time of closure for hinged fire doors shall be no more than 40 s and no less than 10 s from the beginning of their movement with the ship in upright position.",
        trigger_terms=("fire door", "hinged", "time of closure", "closing time",
                       "pintu kebakaran", "engsel", "waktu penutupan", "40 s"),
    ),
    LookupRule(
        topic="fire_door_closing_time", parameter="sliding",
        value_text="0,1 - 0,2 m/s", value_num=None, unit="m/s",
        section_no=22, paragraph_id="C.6.6.2", page_no=494,
        source_quote="The approximate uniform rate of closure for sliding fire doors shall be of no more than 0,2 m/s and no less than 0,1 m/s with the ship in the upright position.",
        trigger_terms=("fire door", "sliding", "rate of closure", "pintu kebakaran",
                       "geser", "sorong", "m/s"),
    ),
    LookupRule(
        topic="bulwark_guardrail_min_height", parameter=None,
        value_text="tidak kurang dari 1,0 m", value_num=1.0, unit="m",
        section_no=6, paragraph_id="K.2", page_no=191,
        source_quote="The bulwark height or height of guard rail is not to be less than 1,0 m, the lesser height may be approved if adequate protection is provided.",
        trigger_terms=("bulwark", "guard rail", "guardrail", "railing", "height", "tinggi",
                       "pagar pelindung", "timber deck cargo", "muatan kayu", "geladak", "1,0 m"),
    ),
    LookupRule(
        topic="ship_length_l_definition", parameter=None,
        value_text="Panjang aturan (rule length) L adalah jarak dalam meter, diukur pada garis air saat sarat skantling (scantling draught), dari sisi depan linggi haluan (foreside of stem) sampai sisi belakang tongkat kemudi (rudder post), atau ke pusat poros kemudi (rudder stock) bila tidak ada rudder post. L tidak boleh kurang dari 96% dan tidak perlu lebih dari 97% panjang ekstrem pada garis air saat sarat skantling.",
        value_num=None, unit=None,
        section_no=1, paragraph_id="H.2.1", page_no=22,
        source_quote="The rule length L is the distance in metres, measured on the waterline at the scantling draught from the foreside of stem to the after side of the rudder post, or the centre of the rudder stock if there is no rudder post. L is not to be less than 96% and need not be greater than 97% of the extreme length on the waterline at the scantling draught.",
        trigger_terms=("length L", "rule length", "rule length L",
                       "definisi panjang kapal", "panjang kapal L", "panjang aturan",
                       "definisi L", "panjang L", "scantling draught",
                       "foreside of stem", "rudder post", "rudder stock",
                       "96%", "97%", "definition of length", "L"),
    ),
]


# ---------------------------------------------------------------------------
# ID query → expected en_query map (so test can mock _translate_condense)
# We mock translate so the lookup's query_en gets the right English terms.
# Without mocking, the test would need Ollama for translation.
# ---------------------------------------------------------------------------

_TRANSLATIONS: dict[str, str] = {
    "tinggi minimum bulwark atau guard rail berapa?": "bulwark guard rail minimum height",
    "waktu penutupan pintu kebakaran engsel berapa?": "hinged fire door closing time",
    "fire door closing time": "fire door closing time",
    "apa kapasitas oli mesin?": "what is the engine oil capacity?",
    "berapa jarak senta di ceruk haluan?": "forepeak stringer spacing collision bulkhead",
    "diameter drum winch tug minimal berapa kali diameter towrope?": "tug winch drum diameter towrope 14 times",
    "Bagaimana definisi panjang kapal L dalam aturan ini?": "rule length L definition scantling draught foreside of stem rudder post",
}


def _fake_translate(query, history, *, temperature) -> str:
    return _TRANSLATIONS.get(query, query)


def _make_patches():
    """Return dict of common patches for tests that need mock RAG path.

    - _get_lookup_rules -> fixture rules (no DB)
    - _translate_condense -> fake translations (no Ollama)
    """
    return {
        "src.llm.chain._get_lookup_rules": lambda: list(_FIXTURE_RULES),
        "src.llm.chain._translate_condense": _fake_translate,
    }


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

def test_chain_lookup_match_bulwark_short_circuits_rag():
    """Bulwark query must match lookup and NOT call retrieve or LLM."""
    retrieve_called = []

    def fake_retrieve(*args, **kwargs):
        retrieve_called.append(True)
        return []

    answer_called = []

    def fake_answer(*args, **kwargs):
        answer_called.append(True)
        return "LLM ANSWER"

    patches = {
        **_make_patches(),
        "src.llm.chain.retrieve_context": fake_retrieve,
        "src.llm.chain._answer": fake_answer,
        "src.llm.chain._answer_fallback_non_stream": fake_answer,
    }

    with patch.multiple(chain, **{k.split(".")[-1] if "." in k else k: v for k, v in patches.items()}):
        patches2 = {k: v for k, v in patches.items()}
        import src.llm.chain as chain_mod

        with patch.multiple(
            "src.llm.chain",
            _get_lookup_rules=patches["src.llm.chain._get_lookup_rules"],
            _translate_condense=patches["src.llm.chain._translate_condense"],
            retrieve_context=fake_retrieve,
            _answer=fake_answer,
            _answer_fallback_non_stream=fake_answer,
        ):
            result = chain_mod.chain_answer("tinggi minimum bulwark atau guard rail berapa?")

    assert result is not None
    assert "1,0 m" in result.answer
    assert "Sec 6" in result.answer
    assert "K.2" in result.answer
    assert "p.191" in result.answer
    assert result.lookup_match is not None
    assert result.lookup_match.rule.topic == "bulwark_guardrail_min_height"
    assert len(retrieve_called) == 0, "retrieve_context should NOT be called when lookup matches"
    assert len(answer_called) == 0, "LLM _answer should NOT be called when lookup matches"
    print("PASS: test_chain_lookup_match_bulwark_short_circuits_rag")


def test_chain_lookup_match_fire_door_hinged():
    """Hinged fire door query must match lookup with correct param and cite Sec 22."""
    retrieve_called = []

    def fake_retrieve(*args, **kwargs):
        retrieve_called.append(True)
        return []

    def fake_answer(*args, **kwargs):
        return "LLM ANSWER"

    with patch.multiple(
        "src.llm.chain",
        _get_lookup_rules=lambda: list(_FIXTURE_RULES),
        _translate_condense=_fake_translate,
        retrieve_context=fake_retrieve,
        _answer=fake_answer,
        _answer_fallback_non_stream=fake_answer,
    ):
        result = chain.chain_answer("waktu penutupan pintu kebakaran engsel berapa?")

    assert result is not None
    assert "40" in result.answer
    assert "10" in result.answer
    assert "Sec 22" in result.answer
    assert "C.6.6.2" in result.answer
    assert "p.494" in result.answer
    assert result.lookup_match is not None
    assert result.lookup_match.rule.parameter == "hinged"
    assert len(retrieve_called) == 0
    print("PASS: test_chain_lookup_match_fire_door_hinged")


def test_chain_lookup_none_falls_back_to_rag():
    """Non-matching query must fall through to retrieval + LLM."""
    retrieve_called = []

    from src.core.models import RetrievedChunk

    _dummy_chunk = RetrievedChunk(
        section_no=1, section_title="General", paragraph_id=None,
        content_type="narrative", table_no=None, figure_no=None,
        page_start=1, page_end=2, content="dummy content", score=0.8,
    )

    def fake_retrieve(*args, **kwargs):
        retrieve_called.append(True)
        return [_dummy_chunk]

    answer_called = []

    def fake_answer(*args, **kwargs):
        answer_called.append(True)
        return "FALLBACK ANSWER"

    with patch.multiple(
        "src.llm.chain",
        _get_lookup_rules=lambda: list(_FIXTURE_RULES),
        _translate_condense=_fake_translate,
        retrieve_context=fake_retrieve,
        _answer=fake_answer,
        _answer_fallback_non_stream=fake_answer,
    ):
        result = chain.chain_answer("apa kapasitas oli mesin?")

    assert result is not None
    assert result.lookup_match is None
    assert len(retrieve_called) == 1, "retrieve_context must be called when lookup returns None"
    assert len(answer_called) >= 1, "LLM _answer must be called when lookup returns None"
    print("PASS: test_chain_lookup_none_falls_back_to_rag")


def test_chain_lookup_ambiguous_fire_door_falls_back():
    """Ambiguous 'fire door closing time' (no hinged/sliding) must fall back."""
    retrieve_called = []

    from src.core.models import RetrievedChunk
    from src.core.models import Intent

    _dummy_chunk = RetrievedChunk(
        section_no=1, section_title="General", paragraph_id=None,
        content_type="narrative", table_no=None, figure_no=None,
        page_start=1, page_end=2, content="dummy content", score=0.8,
    )

    def fake_retrieve(*args, **kwargs):
        retrieve_called.append(True)
        return [_dummy_chunk]

    answer_called = []

    def fake_answer(*args, **kwargs):
        answer_called.append(True)
        return "FALLBACK ANSWER FOR AMBIGUOUS"

    with patch.multiple(
        "src.llm.chain",
        _get_lookup_rules=lambda: list(_FIXTURE_RULES),
            _translate_condense=lambda q, h, *, temperature: q,
        retrieve_context=fake_retrieve,
        _answer=fake_answer,
        _answer_fallback_non_stream=fake_answer,
        classify_with_llm=lambda q, *, temperature: Intent(kind="rules_qa", confidence="high", source="llm"),
    ):
        result = chain.chain_answer("fire door closing time")

    assert result is not None
    assert result.lookup_match is None, "Ambiguous query must not produce a lookup match"
    assert len(retrieve_called) == 1
    assert len(answer_called) >= 1
    print("PASS: test_chain_lookup_ambiguous_fire_door_falls_back")


def test_lookup_match_answer_format_id():
    """Verify _format_lookup_answer produces Indonesian answer with citation."""
    rule = LookupRule(
        topic="bulwark_guardrail_min_height", parameter=None,
        value_text="tidak kurang dari 1,0 m", value_num=1.0, unit="m",
        section_no=6, paragraph_id="K.2", page_no=191,
        source_quote="The bulwark height or height of guard rail is not to be less than 1,0 m.",
        trigger_terms=("bulwark",),
    )
    match = LookupMatch(rule=rule, matched_terms=("bulwark",), score=2)
    answer = chain._format_lookup_answer(match, "id")
    assert "Berdasarkan BKI Rules for Hull 2026" in answer
    assert "tidak kurang dari 1,0 m" in answer
    assert "Sumber:" in answer
    assert "Sec 6" in answer
    assert "K.2" in answer
    assert "p.191" in answer
    assert "Kutipan:" in answer
    assert "The bulwark height" in answer
    print("PASS: test_lookup_match_answer_format_id")


def test_lookup_match_answer_format_en():
    """Verify _format_lookup_answer produces English answer with citation."""
    rule = LookupRule(
        topic="tug_winch_drum_diameter", parameter=None,
        value_text="not less than 14 x towrope diameter", value_num=14, unit="x",
        section_no=27, paragraph_id="C.5.2.3", page_no=630,
        source_quote="The diameter of the winch drum is to be not less than 14 times the towrope diameter.",
        trigger_terms=("winch drum",),
    )
    match = LookupMatch(rule=rule, matched_terms=("winch drum",), score=2)
    answer = chain._format_lookup_answer(match, "en")
    assert "According to BKI Rules for Hull 2026" in answer
    assert "not less than 14 x towrope diameter" in answer
    assert "Source:" in answer
    assert "Sec 27" in answer
    assert "C.5.2.3" in answer
    assert "p.630" in answer
    assert "Quote:" in answer
    print("PASS: test_lookup_match_answer_format_en")


def test_chain_lookup_match_forepeak_stringer():
    """Forepeak stringer spacing query must match lookup directly."""
    retrieve_called = []

    def fake_retrieve(*args, **kwargs):
        retrieve_called.append(True)
        return []

    def fake_answer(*args, **kwargs):
        return "LLM ANSWER"

    with patch.multiple(
        "src.llm.chain",
        _get_lookup_rules=lambda: list(_FIXTURE_RULES),
        _translate_condense=_fake_translate,
        retrieve_context=fake_retrieve,
        _answer=fake_answer,
        _answer_fallback_non_stream=fake_answer,
    ):
        result = chain.chain_answer("berapa jarak senta di ceruk haluan?")

    assert result is not None
    assert "2,6 m" in result.answer
    assert "Sec 9" in result.answer
    assert "A.5.2.1" in result.answer
    assert "p.228" in result.answer
    assert result.lookup_match is not None
    assert result.lookup_match.rule.topic == "forepeak_stringer_spacing"
    assert len(retrieve_called) == 0
    print("PASS: test_chain_lookup_match_forepeak_stringer")


def test_chain_lookup_match_tug_winch_drum():
    """Tug winch drum query must match lookup directly."""
    retrieve_called = []

    def fake_retrieve(*args, **kwargs):
        retrieve_called.append(True)
        return []

    def fake_answer(*args, **kwargs):
        return "LLM ANSWER"

    with patch.multiple(
        "src.llm.chain",
        _get_lookup_rules=lambda: list(_FIXTURE_RULES),
        _translate_condense=_fake_translate,
        retrieve_context=fake_retrieve,
        _answer=fake_answer,
        _answer_fallback_non_stream=fake_answer,
    ):
        result = chain.chain_answer(
            "diameter drum winch tug minimal berapa kali diameter towrope?"
        )

    assert result is not None
    assert "14" in result.answer
    assert "Sec 27" in result.answer
    assert "p.630" in result.answer
    assert result.lookup_match is not None
    assert result.lookup_match.rule.topic == "tug_winch_drum_diameter"
    assert len(retrieve_called) == 0
    print("PASS: test_chain_lookup_match_tug_winch_drum")


def test_chain_lookup_match_ship_length_l():
    """Ship length L definition query must match lookup and cite Sec 1 / H.2.1 / p.22."""
    retrieve_called = []

    def fake_retrieve(*args, **kwargs):
        retrieve_called.append(True)
        return []

    def fake_answer(*args, **kwargs):
        return "LLM ANSWER"

    with patch.multiple(
        "src.llm.chain",
        _get_lookup_rules=lambda: list(_FIXTURE_RULES),
        _translate_condense=_fake_translate,
        retrieve_context=fake_retrieve,
        _answer=fake_answer,
        _answer_fallback_non_stream=fake_answer,
    ):
        result = chain.chain_answer(
            "Bagaimana definisi panjang kapal L dalam aturan ini?"
        )

    assert result is not None
    assert "Sec 1" in result.answer
    assert "H.2.1" in result.answer
    assert "p.22" in result.answer
    assert "96%" in result.answer
    assert "97%" in result.answer
    assert result.lookup_match is not None
    assert result.lookup_match.rule.topic == "ship_length_l_definition"
    assert result.lookup_match.rule.section_no == 1
    assert result.lookup_match.rule.paragraph_id == "H.2.1"
    assert result.lookup_match.rule.page_no == 22
    assert len(retrieve_called) == 0, "retrieve_context should NOT be called when lookup matches"
    print("PASS: test_chain_lookup_match_ship_length_l")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_chain_lookup_match_bulwark_short_circuits_rag()
    test_chain_lookup_match_fire_door_hinged()
    test_chain_lookup_none_falls_back_to_rag()
    test_chain_lookup_ambiguous_fire_door_falls_back()
    test_lookup_match_answer_format_id()
    test_lookup_match_answer_format_en()
    test_chain_lookup_match_forepeak_stringer()
    test_chain_lookup_match_tug_winch_drum()
    test_chain_lookup_match_ship_length_l()
    print("\nAll 9 tests passed!")
