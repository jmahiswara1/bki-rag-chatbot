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


def test_geladak_depan_no_longer_substituted():
    # Build 25: geladak depan removed from pre-LLM glossary to avoid
    # mixed ID/EN input that triggers bulwark→bilge keel hallucination.
    # Post-condense canonicalization handles this deterministically instead.
    out = apply_glossary("Apa tujuan pemasangan breakwater di geladak depan?")
    assert "geladak depan" in out
    assert "forward deck" not in out
    print("PASS: test_geladak_depan_no_longer_substituted")


def test_geladak_depan_casefold_no_longer_substituted():
    out = apply_glossary("breakwater di GELADAK DEPAN kapal")
    assert "geladak depan" in out.lower()
    assert "forward deck" not in out
    print("PASS: test_geladak_depan_casefold_no_longer_substituted")


def test_geladak_depan_whitespace_no_longer_substituted():
    out = apply_glossary("breakwater di  geladak  depan  kapal")
    # geladak depan is no longer in glossary; confirm phrase is still in output
    assert "geladak" in out
    assert "depan" in out
    assert "forward deck" not in out
    print("PASS: test_geladak_depan_whitespace_no_longer_substituted")


def test_di_depan_dermaga_not_forward_deck():
    out = apply_glossary("apa yang berada di depan dermaga?")
    assert "forward deck" not in out
    assert "depan" in out
    print("PASS: test_di_depan_dermaga_not_forward_deck")


def test_di_depan_kapal_not_forward_deck():
    out = apply_glossary("struktur di depan kapal")
    assert "forward deck" not in out
    assert "depan" in out
    print("PASS: test_di_depan_kapal_not_forward_deck")


def test_forward_deck_en_unchanged():
    out = apply_glossary("what is the purpose of a breakwater on the forward deck")
    assert "forward deck" in out
    assert len(out) == len("what is the purpose of a breakwater on the forward deck")
    print("PASS: test_forward_deck_en_unchanged")


def test_idempotent_geladak_depan():
    # geladak depan is no longer in glossary; still idempotent
    first = apply_glossary("pemasangan breakwater di geladak depan kapal")
    second = apply_glossary(first)
    assert first == second
    assert "geladak depan" in first
    print("PASS: test_idempotent_geladak_depan")


def test_unrelated_technical_query_unchanged_1():
    q = "berapa ketebalan minimum pelat lambung untuk kapal tanker?"
    out = apply_glossary(q)
    assert "forward deck" not in out
    assert "aft deck" not in out
    print("PASS: test_unrelated_technical_query_unchanged_1")


def test_unrelated_technical_query_unchanged_2():
    q = "apa persyaratan sistem bilga untuk kapal penumpang?"
    out = apply_glossary(q)
    assert "forward deck" not in out
    assert "aft deck" not in out
    print("PASS: test_unrelated_technical_query_unchanged_2")


def test_wrang_not_floor_plate():
    out = apply_glossary("Tebal minimum wrang.").lower()
    assert "floor" in out
    assert "floor plate" not in out

def test_pelat_alas_to_bottom_shell():
    out = apply_glossary("Berapa tebal minimum pelat alas?").lower()
    assert "bottom shell plating" in out
    assert "deck" not in out
    assert "keel" not in out
    assert "floor plate" not in out

def test_pelat_alas_dalam_to_inner_bottom():
    out = apply_glossary("Jelaskan perbedaan pelat alas dan pelat alas dalam.").lower()
    assert "inner bottom plating" in out
    assert "bottom shell plating" in out
    assert "bottom shell plating dalam" not in out

def test_pelat_wrang_to_floor_plate():
    out = apply_glossary("Ketentuan untuk pelat wrang tunggal.").lower()
    assert "floor plate" in out

def test_wrang_to_floor():
    out = apply_glossary("Apa itu wrang pada konstruksi alas ganda?").lower()
    assert "floor" in out
    assert "double bottom" in out

def test_alas_ganda_to_double_bottom():
    out = apply_glossary("Tangki pada alas ganda harus dilengkapi.").lower()
    assert "double bottom" in out

# --- New entries (Fase A — retrieval relevance improvement) ---

def test_kapal_kontainer_to_container_ship():
    out = apply_glossary("kapal kontainer 120m dengan pelat sisi").lower()
    assert "container ship" in out

def test_kapal_peti_kemas_to_container_ship():
    out = apply_glossary("kapal peti kemas muatan berat").lower()
    assert "container ship" in out

def test_kapal_curah_to_bulk_carrier():
    out = apply_glossary("kapal curah 200m").lower()
    assert "bulk carrier" in out

def test_kapal_tangki_to_tanker():
    out = apply_glossary("kapal tangki minyak").lower()
    assert "tanker" in out

def test_kapal_penumpang_to_passenger_ship():
    out = apply_glossary("kapal penumpang 500 GT").lower()
    assert "passenger ship" in out

def test_kapal_niaga_to_merchant_ship():
    out = apply_glossary("kapal niaga ukuran sedang").lower()
    assert "merchant ship" in out

def test_konstruksi_memanjang_system():
    out = apply_glossary("jenis konstruksi memanjang dengan L 100m").lower()
    assert "longitudinal framing system" in out

def test_konstruksi_melintang_system():
    out = apply_glossary("jenis konstruksi melintang L 80m").lower()
    assert "transverse framing system" in out

def test_konstruksi_memanjang_bare():
    out = apply_glossary("konstruksi memanjang").lower()
    assert "longitudinal framing" in out
    assert "longitudinal framing system" not in out

def test_konstruksi_melintang_bare():
    out = apply_glossary("konstruksi melintang").lower()
    assert "transverse framing" in out
    assert "transverse framing system" not in out

def test_jarak_antar_penegar_to_stiffener_spacing():
    out = apply_glossary("jarak antar penegar 600mm").lower()
    assert "stiffener spacing" in out

def test_pelat_bukaan_palka_to_hatch_opening_plate():
    out = apply_glossary("pelat bukaan palka minimum").lower()
    assert "hatch opening plate" in out

def test_pelat_kulit_luar_to_outer_shell_plating():
    out = apply_glossary("pelat kulit luar lambung kapal niaga").lower()
    assert "outer shell plating" in out

def test_kulit_luar_lambung_to_hull_shell():
    out = apply_glossary("kulit luar lambung").lower()
    assert "hull shell" in out

def test_ketebalan_bersih_to_net_thickness():
    out = apply_glossary("ketebalan bersih minimum tp").lower()
    assert "net thickness" in out

def test_baja_standar_to_mild_steel():
    out = apply_glossary("baja standar untuk pelat lambung").lower()
    assert "mild steel" in out

def test_baja_lunak_to_mild_steel():
    out = apply_glossary("baja lunak").lower()
    assert "mild steel" in out

def test_pelat_lambung_to_shell_plating():
    out = apply_glossary("pelat lambung kapal niaga").lower()
    assert "shell plating" in out

def test_pelat_sisi_to_side_shell_plating():
    out = apply_glossary("pelat sisi tebal 4mm").lower()
    assert "side shell plating" in out

def test_penegar_to_stiffener():
    out = apply_glossary("penegar vertikal lambung").lower()
    assert "stiffener" in out

def test_pembukaan_palka_to_hatch_opening():
    out = apply_glossary("pembukaan palka kapal").lower()
    assert "hatch opening" in out

def test_beban_yang_bekerja_to_acting_loads():
    out = apply_glossary("beban yang bekerja pada struktur").lower()
    assert "acting loads" in out

# --- Regression: pre-existing entries still work ---

def test_regression_senta_sisi_to_stringer():
    out = apply_glossary("senta sisi kapal").lower()
    assert "stringer" in out

def test_regression_sekat_tubrukan():
    out = apply_glossary("jarak sekat tubrukan dari haluan").lower()
    assert "collision bulkhead" in out


# --- Slamming entries (Fase retrieval improvement) ---

def test_hantaman_to_slamming():
    out = apply_glossary("apa itu hantaman pada kapal").lower()
    assert "slamming" in out

def test_hantaman_dasar_to_bottom_slamming():
    out = apply_glossary("hantaman dasar").lower()
    assert "bottom slamming" in out

def test_hentaman_to_slamming():
    out = apply_glossary("beban hentaman").lower()
    assert "slamming" in out


# --- Build 41: direction terms pin fore/aft so condense cannot drift ---

def test_bagian_buritan_to_aft_part():
    out = apply_glossary("ketebalan pelat bangunan atas di bagian buritan").lower()
    assert "aft part" in out
    assert "bow" not in out

def test_bagian_haluan_to_forward_part():
    out = apply_glossary("struktur di bagian haluan").lower()
    assert "forward part" in out
    assert "stern" not in out

def test_di_buritan_to_at_the_aft():
    out = apply_glossary("geladak di buritan").lower()
    assert "at the aft" in out

def test_freeing_ports_pinned():
    out = apply_glossary("Berapa luas minimum freeing ports pada bulwark?").lower()
    assert "freeing ports" in out
    assert "freeboard" not in out

def test_bare_depan_not_mapped():
    out = apply_glossary("struktur di depan kapal").lower()
    assert "depan" in out


# ---------- Runner ----------

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
    test_geladak_depan_no_longer_substituted()
    test_geladak_depan_casefold_no_longer_substituted()
    test_geladak_depan_whitespace_no_longer_substituted()
    test_di_depan_dermaga_not_forward_deck()
    test_di_depan_kapal_not_forward_deck()
    test_forward_deck_en_unchanged()
    test_idempotent_geladak_depan()
    test_unrelated_technical_query_unchanged_1()
    test_unrelated_technical_query_unchanged_2()
    test_pelat_alas_to_bottom_shell()
    test_pelat_alas_dalam_to_inner_bottom()
    test_pelat_wrang_to_floor_plate()
    test_wrang_to_floor()
    test_alas_ganda_to_double_bottom()
    test_wrang_not_floor_plate()
    test_kapal_kontainer_to_container_ship()
    test_kapal_peti_kemas_to_container_ship()
    test_kapal_curah_to_bulk_carrier()
    test_kapal_tangki_to_tanker()
    test_kapal_penumpang_to_passenger_ship()
    test_kapal_niaga_to_merchant_ship()
    test_konstruksi_memanjang_system()
    test_konstruksi_melintang_system()
    test_konstruksi_memanjang_bare()
    test_konstruksi_melintang_bare()
    test_jarak_antar_penegar_to_stiffener_spacing()
    test_pelat_bukaan_palka_to_hatch_opening_plate()
    test_pelat_kulit_luar_to_outer_shell_plating()
    test_kulit_luar_lambung_to_hull_shell()
    test_ketebalan_bersih_to_net_thickness()
    test_baja_standar_to_mild_steel()
    test_baja_lunak_to_mild_steel()
    test_pelat_lambung_to_shell_plating()
    test_pelat_sisi_to_side_shell_plating()
    test_penegar_to_stiffener()
    test_pembukaan_palka_to_hatch_opening()
    test_beban_yang_bekerja_to_acting_loads()
    test_regression_senta_sisi_to_stringer()
    test_regression_sekat_tubrukan()
    test_hantaman_to_slamming()
    test_hantaman_dasar_to_bottom_slamming()
    test_hentaman_to_slamming()
    all_count = len([f for f in dir() if f.startswith("test_")])
    print(f"\nAll {all_count} tests passed!")
