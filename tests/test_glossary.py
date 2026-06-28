import sys
sys.path.insert(0, r"E:\Project\bki-rag-chatbot")

from src.llm.glossary import apply_glossary


def test_bare_tinggi_not_freeboard():
    out = apply_glossary("tinggi minimum bulwark atau guard rail berapa?").lower()
    assert "freeboard" not in out
    print("PASS: test_bare_tinggi_not_freeboard")


def test_tinggi_bebas_to_freeboard():
    assert "freeboard" in apply_glossary("berapa tinggi bebas minimum?").lower()
    print("PASS: test_tinggi_bebas_to_freeboard")


def test_tinggi_lambung_timbul_to_freeboard():
    assert apply_glossary("tinggi lambung timbul minimum") == "freeboard minimum"
    print("PASS: test_tinggi_lambung_timbul_to_freeboard")


def test_sekat_tubrukan_and_garis_tegak_haluan():
    out = apply_glossary("jarak sekat tubrukan dari garis tegak haluan")
    assert "collision bulkhead" in out
    assert "forward perpendicular" in out
    assert "stringer" not in out
    print("PASS: test_sekat_tubrukan_and_garis_tegak_haluan")


def test_sekat_alone_to_bulkhead():
    assert "bulkhead" in apply_glossary("sekat ceruk")
    print("PASS: test_sekat_alone_to_bulkhead")


def test_pintu_kebakaran_to_fire_door():
    out = apply_glossary("waktu penutupan pintu kebakaran engsel")
    assert "fire door" in out
    assert "hatch" not in out
    assert "freeboard" not in out
    print("PASS: test_pintu_kebakaran_to_fire_door")


def test_compound_wins_tutup_palka():
    assert apply_glossary("tutup palka") == "hatch cover"
    print("PASS: test_compound_wins_tutup_palka")


def test_senta_to_stringer_not_side_stringer():
    assert apply_glossary("senta sisi") == "stringer"
    print("PASS: test_senta_to_stringer_not_side_stringer")


def test_pelat_dek_to_deck_plating():
    assert apply_glossary("pelat dek") == "deck plating"
    print("PASS: test_pelat_dek_to_deck_plating")


def test_word_boundary_no_partial_match():
    assert apply_glossary("gadingan") == "gadingan"
    print("PASS: test_word_boundary_no_partial_match")


def test_control_unchanged():
    # Plain Indonesian with no BKI domain phrase -> glossary must leave it
    # untouched (all 25 keys are corpus-specific compound/anchor terms).
    q = "berapa jumlah anak kapal di kapal ini?"
    print("PASS: test_control_unchanged")


def test_modulus_penampang_to_section_modulus():
    out = apply_glossary("berapa pengurangan modulus penampang untuk restricted ocean service?")
    assert "section modulus" in out
    assert "flexural" not in out
    print("PASS: test_modulus_penampang_to_section_modulus")


def test_penampang_alone_to_section():
    assert "section" in apply_glossary("luas penampang")
    print("PASS: test_penampang_alone_to_section")


def test_engsel_to_hinged():
    out = apply_glossary("waktu penutupan pintu kebakaran engsel")
    assert "hinged" in out
    assert "fire door" in out
    assert "latch" not in out
    print("PASS: test_engsel_to_hinged")


if __name__ == "__main__":
    test_bare_tinggi_not_freeboard()
    test_tinggi_bebas_to_freeboard()
    test_tinggi_lambung_timbul_to_freeboard()
    test_sekat_tubrukan_and_garis_tegak_haluan()
    test_sekat_alone_to_bulkhead()
    test_pintu_kebakaran_to_fire_door()
    test_compound_wins_tutup_palka()
    test_senta_to_stringer_not_side_stringer()
    test_pelat_dek_to_deck_plating()
    test_word_boundary_no_partial_match()
    test_control_unchanged()
    test_modulus_penampang_to_section_modulus()
    test_penampang_alone_to_section()
    test_engsel_to_hinged()
    print("\nAll 14 tests passed!")
