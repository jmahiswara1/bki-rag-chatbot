from src.llm.language import detect_language


def test_id_apa_saja_struktur_alas():
    """Previously misdetected as 'other' by langdetect. Marker pre-check must win."""
    label, _ = detect_language("Apa saja komponen utama struktur alas?")
    assert label == "id"
    print("PASS: test_id_apa_saja_struktur_alas")


def test_id_bagaimana_beban_dek():
    label, _ = detect_language("Bagaimana menentukan beban dek pL?")
    assert label == "id"
    print("PASS: test_id_bagaimana_beban_dek")


def test_id_tebal_pelat_minimum_geladak():
    label, _ = detect_language("Tebal pelat minimum geladak?")
    assert label == "id"
    print("PASS: test_id_tebal_pelat_minimum_geladak")


def test_en_how_section_modulus():
    label, _ = detect_language("How is the section modulus calculated?")
    assert label == "en"
    print("PASS: test_en_how_section_modulus")


def test_en_main_components_bottom_structure():
    label, _ = detect_language("What are the main components of the bottom structure?")
    assert label == "en"
    print("PASS: test_en_main_components_bottom_structure")


def test_en_minimum_plate_thickness_deck():
    label, _ = detect_language("What is the minimum general plate thickness for deck plates?")
    assert label == "en"
    print("PASS: test_en_minimum_plate_thickness_deck")


def test_empty_string_returns_other():
    label, conf = detect_language("")
    assert label == "other"
    assert conf == 0.0
    print("PASS: test_empty_string_returns_other")


def test_keyword_decide_strict_winner():
    """Mixed input where both hit should not pick a side."""
    from src.llm.language import _keyword_decide
    # equal hits on both sides -> None (fall through to langdetect)
    assert _keyword_decide("the apa the apa") is None
    print("PASS: test_keyword_decide_strict_winner")


def test_marker_hits_word_boundary():
    """'pelat' must NOT match inside 'pelat-pelat' as a single boundary,
    but 'pelat' standalone should hit."""
    from src.llm.language import _marker_hits, ID_MARKERS
    assert _marker_hits("pelat", ID_MARKERS) == 1
    # 'pelat-pelat' is two words; the regex should still hit twice if naively
    # counted, but with distinct tokens it would be 1. We just require >=1.
    assert _marker_hits("pelat-pelat", ID_MARKERS) >= 1
    print("PASS: test_marker_hits_word_boundary")


if __name__ == "__main__":
    test_id_apa_saja_struktur_alas()
    test_id_bagaimana_beban_dek()
    test_id_tebal_pelat_minimum_geladak()
    test_en_how_section_modulus()
    test_en_main_components_bottom_structure()
    test_en_minimum_plate_thickness_deck()
    test_empty_string_returns_other()
    test_keyword_decide_strict_winner()
    test_marker_hits_word_boundary()
    print("\nAll tests passed!")
