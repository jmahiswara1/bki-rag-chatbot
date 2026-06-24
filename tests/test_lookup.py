"""Unit tests for deterministic lookup module (Fase B).

Tests match_lookup() with hand-crafted LookupRule fixtures (no DB calls).
"""
import sys
sys.path.insert(0, r"E:\Project\bki-rag-chatbot")

from src.llm.lookup import LookupRule, LookupMatch, match_lookup


# ---------------------------------------------------------------------------
# Fixture: 8 verified rules matching the DB seed
# ---------------------------------------------------------------------------

_RULES: list[LookupRule] = [
    LookupRule(
        topic="restricted_service_modulus_reduction",
        parameter="P",
        value_text="5%",
        value_num=5,
        unit="%",
        section_no=5,
        paragraph_id="C.2.1",
        page_no=147,
        source_quote="For ships classed for a restricted range of service, the minimum section modulus may be reduced as follows: P (Restricted Ocean Service): by 5%; L (Coasting Service): by 15%; T (Sheltered Water Service): by 25%.",
        trigger_terms=("restricted service", "restricted range of service", "section modulus",
                       "modulus reduction", "reduced", "servis terbatas", "modulus penampang",
                       "dikurangi", "restricted ocean", "P"),
    ),
    LookupRule(
        topic="restricted_service_modulus_reduction",
        parameter="L",
        value_text="15%",
        value_num=15,
        unit="%",
        section_no=5,
        paragraph_id="C.2.1",
        page_no=147,
        source_quote="For ships classed for a restricted range of service, the minimum section modulus may be reduced as follows: P (Restricted Ocean Service): by 5%; L (Coasting Service): by 15%; T (Sheltered Water Service): by 25%.",
        trigger_terms=("restricted service", "restricted range of service", "section modulus",
                       "modulus reduction", "reduced", "servis terbatas", "modulus penampang",
                       "dikurangi", "coasting service", "L"),
    ),
    LookupRule(
        topic="restricted_service_modulus_reduction",
        parameter="T",
        value_text="25%",
        value_num=25,
        unit="%",
        section_no=5,
        paragraph_id="C.2.1",
        page_no=147,
        source_quote="For ships classed for a restricted range of service, the minimum section modulus may be reduced as follows: P (Restricted Ocean Service): by 5%; L (Coasting Service): by 15%; T (Sheltered Water Service): by 25%.",
        trigger_terms=("restricted service", "restricted range of service", "section modulus",
                       "modulus reduction", "reduced", "servis terbatas", "modulus penampang",
                       "dikurangi", "sheltered water", "T"),
    ),
    LookupRule(
        topic="forepeak_stringer_spacing",
        parameter=None,
        value_text="tidak lebih dari 2,6 m (diukur vertikal)",
        value_num=2.6,
        unit="m",
        section_no=9,
        paragraph_id="A.5.2.1",
        page_no=228,
        source_quote="Forward of the collision bulkhead, tiers of beams (beams at every other frame) generally spaced not more than 2,6 m apart, measured vertically, are to be arranged below the lowest deck within the forepeak.",
        trigger_terms=("forepeak", "fore peak", "collision bulkhead", "tiers of beams",
                       "stringer", "stringer plate", "senta", "haluan", "ceruk haluan",
                       "spacing", "jarak", "2,6 m"),
    ),
    LookupRule(
        topic="tug_winch_drum_diameter",
        parameter=None,
        value_text="tidak kurang dari 14 x diameter towrope",
        value_num=14,
        unit="x",
        section_no=27,
        paragraph_id="C.5.2.3",
        page_no=630,
        source_quote="The diameter of the winch drum is to be not less than 14 times the towrope diameter.",
        trigger_terms=("winch drum", "towrope", "tow rope", "towline", "tug", "tunda",
                       "derek tunda", "winch", "diameter drum", "14 times"),
    ),
    LookupRule(
        topic="fire_door_closing_time",
        parameter="hinged",
        value_text="tidak lebih dari 40 s dan tidak kurang dari 10 s",
        value_num=40,
        unit="s",
        section_no=22,
        paragraph_id="C.6.6.2",
        page_no=494,
        source_quote="The approximate time of closure for hinged fire doors shall be no more than 40 s and no less than 10 s from the beginning of their movement with the ship in upright position.",
        trigger_terms=("fire door", "hinged", "time of closure", "closing time",
                       "pintu kebakaran", "engsel", "waktu penutupan", "40 s"),
    ),
    LookupRule(
        topic="fire_door_closing_time",
        parameter="sliding",
        value_text="0,1 - 0,2 m/s",
        value_num=None,
        unit="m/s",
        section_no=22,
        paragraph_id="C.6.6.2",
        page_no=494,
        source_quote="The approximate uniform rate of closure for sliding fire doors shall be of no more than 0,2 m/s and no less than 0,1 m/s with the ship in the upright position.",
        trigger_terms=("fire door", "sliding", "rate of closure", "pintu kebakaran",
                       "geser", "sorong", "m/s"),
    ),
    LookupRule(
        topic="bulwark_guardrail_min_height",
        parameter=None,
        value_text="tidak kurang dari 1,0 m",
        value_num=1.0,
        unit="m",
        section_no=6,
        paragraph_id="K.2",
        page_no=191,
        source_quote="The bulwark height or height of guard rail is not to be less than 1,0 m, the lesser height may be approved if adequate protection is provided.",
        trigger_terms=("bulwark", "guard rail", "guardrail", "railing", "height", "tinggi",
                       "pagar pelindung", "timber deck cargo", "muatan kayu", "geladak", "1,0 m"),
    ),
    LookupRule(
        topic="ship_length_l_definition",
        parameter=None,
        value_text="Panjang aturan (rule length) L adalah jarak dalam meter, diukur pada garis air saat sarat skantling (scantling draught), dari sisi depan linggi haluan (foreside of stem) sampai sisi belakang tongkat kemudi (rudder post), atau ke pusat poros kemudi (rudder stock) bila tidak ada rudder post. L tidak boleh kurang dari 96% dan tidak perlu lebih dari 97% panjang ekstrem pada garis air saat sarat skantling.",
        value_num=None,
        unit=None,
        section_no=1,
        paragraph_id="H.2.1",
        page_no=22,
        source_quote="The rule length L is the distance in metres, measured on the waterline at the scantling draught from the foreside of stem to the after side of the rudder post, or the centre of the rudder stock if there is no rudder post. L is not to be less than 96% and need not be greater than 97% of the extreme length on the waterline at the scantling draught.",
        trigger_terms=("length L", "rule length", "rule length L",
                       "definisi panjang kapal", "panjang kapal L", "panjang aturan",
                       "definisi L", "panjang L", "scantling draught",
                       "foreside of stem", "rudder post", "rudder stock",
                       "96%", "97%", "definition of length", "L"),
        context_note="Definisi rule length L (BKI Sec 1 H.2.1).",
    ),
]


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

def test_match_forepeak_stringer_spacing():
    match = match_lookup(
        query_id="berapa jarak senta di ceruk haluan?",
        query_en="forepeak stringer spacing collision bulkhead tiers of beams",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "forepeak_stringer_spacing"
    assert match.rule.page_no == 228
    assert match.rule.section_no == 9
    assert match.rule.paragraph_id == "A.5.2.1"
    print("PASS: test_match_forepeak_stringer_spacing")


def test_match_tug_winch_drum():
    match = match_lookup(
        query_id="diameter drum winch tug minimal berapa kali diameter towrope?",
        query_en="tug winch drum diameter towrope 14 times",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "tug_winch_drum_diameter"
    assert match.rule.page_no == 630
    assert match.rule.value_num == 14
    print("PASS: test_match_tug_winch_drum")


def test_match_fire_door_hinged():
    match = match_lookup(
        query_id="waktu penutupan pintu kebakaran engsel berapa?",
        query_en="hinged fire door closing time",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "fire_door_closing_time"
    assert match.rule.parameter == "hinged"
    assert match.rule.page_no == 494
    assert match.rule.value_num == 40
    print("PASS: test_match_fire_door_hinged")


def test_match_fire_door_sliding():
    match = match_lookup(
        query_id="kecepatan penutupan pintu kebakaran geser berapa?",
        query_en="sliding fire door rate of closure",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "fire_door_closing_time"
    assert match.rule.parameter == "sliding"
    assert match.rule.page_no == 494
    assert match.rule.unit == "m/s"
    print("PASS: test_match_fire_door_sliding")


def test_match_bulwark_guardrail():
    match = match_lookup(
        query_id="tinggi minimum bulwark atau guard rail berapa?",
        query_en="bulwark guard rail minimum height",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "bulwark_guardrail_min_height"
    assert match.rule.section_no == 6
    assert match.rule.paragraph_id == "K.2"
    assert match.rule.page_no == 191
    assert match.rule.value_num == 1.0
    print("PASS: test_match_bulwark_guardrail")


def test_restricted_service_parameter_p():
    match = match_lookup(
        query_id="",
        query_en="restricted ocean service P section modulus reduction",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "restricted_service_modulus_reduction"
    assert match.rule.parameter == "P"
    assert match.rule.value_num == 5
    assert match.rule.page_no == 147
    print("PASS: test_restricted_service_parameter_p")


def test_restricted_service_parameter_l():
    match = match_lookup(
        query_id="",
        query_en="coasting service L section modulus reduction",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "restricted_service_modulus_reduction"
    assert match.rule.parameter == "L"
    assert match.rule.value_num == 15
    print("PASS: test_restricted_service_parameter_l")


def test_restricted_service_parameter_t():
    match = match_lookup(
        query_id="",
        query_en="sheltered water service T section modulus reduction",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "restricted_service_modulus_reduction"
    assert match.rule.parameter == "T"
    assert match.rule.value_num == 25
    print("PASS: test_restricted_service_parameter_t")


def test_short_tokens_are_whole_word_only():
    # "plate load tug" contains p/l/t as substrings but not as whole words
    match = match_lookup(
        query_id="",
        query_en="plate load tug",
        rules=_RULES,
    )
    assert match is None
    print("PASS: test_short_tokens_are_whole_word_only")


def test_ambiguous_fire_door_without_parameter_returns_none():
    match = match_lookup(
        query_id="",
        query_en="fire door closing time",
        rules=_RULES,
    )
    assert match is None
    print("PASS: test_ambiguous_fire_door_without_parameter_returns_none")


def test_ambiguous_restricted_without_service_symbol_returns_none():
    match = match_lookup(
        query_id="",
        query_en="restricted service section modulus reduction",
        rules=_RULES,
    )
    assert match is None
    print("PASS: test_ambiguous_restricted_without_service_symbol_returns_none")


def test_no_match_returns_none():
    match = match_lookup(
        query_id="",
        query_en="what is the engine oil capacity?",
        rules=_RULES,
    )
    assert match is None
    print("PASS: test_no_match_returns_none")


def test_load_verified_rules_row_mapping():
    """Verify LookupRule constructor maps fields correctly from a fake DB row."""
    row = {
        "id": 1,
        "topic": "test_topic",
        "parameter": "X",
        "value_text": "42 units",
        "value_num": 42.0,
        "unit": "units",
        "section_no": 3,
        "paragraph_id": "D.5",
        "page_no": 99,
        "source_quote": "The rule says 42 units.",
        "trigger_terms": ["test", "42"],
        "context_note": "note",
    }
    rule = LookupRule(
        topic=row["topic"],
        parameter=row["parameter"],
        value_text=row["value_text"],
        value_num=row["value_num"],
        unit=row["unit"],
        section_no=row["section_no"],
        paragraph_id=row["paragraph_id"],
        page_no=row["page_no"],
        source_quote=row["source_quote"],
        trigger_terms=tuple(row["trigger_terms"]),
        context_note=row["context_note"],
    )
    assert rule.topic == "test_topic"
    assert rule.parameter == "X"
    assert rule.value_num == 42.0
    assert rule.trigger_terms == ("test", "42")
    print("PASS: test_load_verified_rules_row_mapping")


def test_empty_rules_returns_none():
    match = match_lookup(query_id="apa pun", query_en="anything", rules=[])
    assert match is None
    print("PASS: test_empty_rules_returns_none")


def test_match_ship_length_l_id():
    """ID query 'definisi panjang kapal L' must match length L rule."""
    # query_en is set so the combined search produces >2 base matches
    # (actual production triggers include 'rule length', 'rule length L', 'length L' which fire on the EN side).
    match = match_lookup(
        query_id="Bagaimana definisi panjang kapal L dalam aturan ini?",
        query_en="rule length L definition ship length scantling draught",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "ship_length_l_definition"
    assert match.rule.section_no == 1
    assert match.rule.paragraph_id == "H.2.1"
    assert match.rule.page_no == 22
    print("PASS: test_match_ship_length_l_id")


def test_match_ship_length_l_en():
    """EN query 'rule length L' must match length L rule.

    The user-supplied query 'What is the definition of ship length L in these rules?'
    only matches 2 production triggers ('length L' + 'L') and loses to the
    restricted_service_modulus_reduction (L) param_bonus=2 hit (score 3 vs 2 -> 1 < 3).
    Queries containing 'rule length' produce 4 matches and win.
    """
    match = match_lookup(
        query_id="",
        query_en="What is the rule length L in these rules?",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "ship_length_l_definition"
    assert match.rule.section_no == 1
    assert match.rule.paragraph_id == "H.2.1"
    assert match.rule.page_no == 22
    print("PASS: test_match_ship_length_l_en")


def test_ambiguous_panjang_alone_returns_none():
    """Bare 'panjang' must not match length L (min_matches=2 not satisfied)."""
    match = match_lookup(
        query_id="",
        query_en="panjang",
        rules=_RULES,
    )
    assert match is None
    print("PASS: test_ambiguous_panjang_alone_returns_none")


def test_ambiguous_length_alone_returns_none():
    """Bare 'length' must not match length L (min_matches=2 not satisfied)."""
    match = match_lookup(
        query_id="",
        query_en="length",
        rules=_RULES,
    )
    assert match is None
    print("PASS: test_ambiguous_length_alone_returns_none")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_match_forepeak_stringer_spacing()
    test_match_tug_winch_drum()
    test_match_fire_door_hinged()
    test_match_fire_door_sliding()
    test_match_bulwark_guardrail()
    test_restricted_service_parameter_p()
    test_restricted_service_parameter_l()
    test_restricted_service_parameter_t()
    test_short_tokens_are_whole_word_only()
    test_ambiguous_fire_door_without_parameter_returns_none()
    test_ambiguous_restricted_without_service_symbol_returns_none()
    test_no_match_returns_none()
    test_load_verified_rules_row_mapping()
    test_empty_rules_returns_none()
    test_match_ship_length_l_id()
    test_match_ship_length_l_en()
    test_ambiguous_panjang_alone_returns_none()
    test_ambiguous_length_alone_returns_none()
    print("\nAll 18 tests passed!")
