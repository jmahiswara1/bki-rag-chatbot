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
    LookupRule(
        topic="depth_to_length_ratio",
        parameter=None,
        value_text=(
            "Kedalaman (depth H) kapal tidak boleh kurang dari: L/16 untuk "
            "Unlimited Range of Service dan P (Restricted Ocean Service); "
            "L/18 untuk L (Coasting Service); L/19 untuk T (Sheltered Water "
            "Service)."
        ),
        value_num=None,
        unit=None,
        section_no=1,
        paragraph_id="A.1",
        page_no=17,
        source_quote=(
            "The Rules apply to seagoing steel ships classed A100 whose "
            "breadth to depth ratio is within the range common for seagoing "
            "ships and the depth H of which is not less than: L/16 for "
            "Unlimited Range of Service and P (Restricted Ocean Service); "
            "L/18 for L (Coasting Service); L/19 for T (Sheltered Water "
            "Service)."
        ),
        trigger_terms=(
            "depth to length ratio", "kedalaman terhadap panjang",
            "rasio kedalaman", "ratio of depth", "breadth to depth",
            "depth h", "minimum depth", "kedalaman minimum",
            "range of service", "l/16", "l/18", "l/19",
        ),
        context_note="BKI Sec 1 A.1 (Validity, Equivalence).",
    ),
    LookupRule(
        topic="main_vertical_zone_dimension",
        parameter=None,
        value_text=(
            "Panjang dan lebar rata-rata main vertical zone pada tiap "
            "geladak umumnya tidak boleh melebihi 40 m. Perpanjangan "
            "hingga maksimum 48 m hanya diizinkan bila total luas main "
            "vertical zone tidak melebihi 1600 m2 pada tiap geladak "
            "(Sec 22 B.2.1)."
        ),
        value_num=40,
        unit="m",
        section_no=22,
        paragraph_id="B.2.1",
        page_no=489,
        source_quote=(
            "The hull, superstructures and deckhouses are to be subdivided "
            "into main vertical zones the average length and width of "
            "which on any deck is generally not to exceed 40 m."
        ),
        trigger_terms=(
            "main vertical zone", "main vertical zones",
            "zona vertikal utama", "mvz",
            "average length", "panjang rata-rata",
            "maximum length", "panjang maksimum",
            "length and width", "panjang dan lebar",
        ),
        context_note=(
            "General limit 40 m; 48 m extension only if total zone area "
            "<= 1600 m2 per deck. Do not assume the 48 m extension applies."
        ),
    ),
    LookupRule(
        topic="probability_factor_fq",
        parameter=None,
        value_text="fQ = 1,000 at standard Q=10^-8",
        value_text_en="The probability factor fQ depends on the probability level Q (Table 4.2): fQ = 1.000 at Q = 10^-8.",
        value_text_id="Faktor probabilitas fQ bergantung pada level probabilitas Q (Table 4.2): fQ = 1,000 pada Q = 10^-8.",
        value_num=1.0, unit=None,
        section_no=4, paragraph_id="E.1", page_no=131,
        source_quote="fQ = probability factor depending on probability level Q as outline in Table 4.2.",
        trigger_terms=("probability factor","faktor probabilitas","probability level",
                       "level probabilitas","fq","table 4.2","tabel 4.2",
                       "probability factor fq"),
        context_note="Discrete table; standard Q=10^-8 -> fQ=1,000.",
    ),
    LookupRule(
        topic="material_factor_k",
        parameter=None,
        value_text="k = 1,0 untuk baja kekuatan normal (ReH=235)",
        value_text_en="The material factor k depends on the steel nominal upper yield strength ReH (Table 2.1, Sec 2 B): k = 1.0 for ReH=235, 0.78 at 315, 0.72 at 355, 0.66 at 390, 0.62 at 460.",
        value_text_id="Faktor material k bergantung pada tegangan luluh atas nominal baja ReH (Table 2.1, Sec 2 B): k = 1,0 untuk ReH=235.",
        value_num=1.0, unit=None,
        section_no=2, paragraph_id="B.2", page_no=32,
        source_quote="The material factor k in the formulae of the following Sections is to be taken 1,0 for normal strength hull structural steel.",
        trigger_terms=("material factor","faktor material","material factor k",
                       "faktor material k","reh","tegangan luluh","yield strength"),
        context_note="Discrete table per ReH; 235->1,0; 315->0,78; 355->0,72; 390->0,66 (0,68); 460->0,62.",
    ),
    LookupRule(
        topic="modulus_of_elasticity",
        parameter="steel",
        value_text="Modulus elastisitas (modulus Young) E untuk baja = 2,06 x 10^5 N/mm^2",
        value_text_en="The modulus of elasticity (Young's modulus) E for hull structural steel is 2.06 x 10^5 N/mm^2.",
        value_text_id="Modulus elastisitas (modulus Young) E untuk baja = 2,06 x 10^5 N/mm^2.",
        value_num=206000.0, unit="N/mm^2",
        section_no=3, paragraph_id="F.5.1.6", page_no=85,
        source_quote="E = Young's modulus = 2,06 . 10^5 [N/mm2] for steel",
        trigger_terms=("modulus of elasticity","young's modulus","modulus elastisitas",
                       "elastic modulus","elasticity","elastisitas","young",
                       "steel","baja"),
        context_note="Discrete value 2,06e5 N/mm^2 for hull steel per Sec 3 F.5.1.6.",
    ),
    LookupRule(
        topic="modulus_of_elasticity",
        parameter="aluminium",
        value_text="Modulus elastisitas (modulus Young) E untuk paduan aluminium = 70000 N/mm^2",
        value_text_en="For aluminium alloys, the Young's modulus (E) is 70000 N/mm^2.",
        value_text_id="Untuk paduan aluminium, modulus elastisitas (Young) E adalah 70000 N/mm^2.",
        value_num=70000, unit="N/mm^2",
        section_no=2, paragraph_id="D.1.7", page_no=43,
        source_quote="the Young's modulus for aluminium alloys (E) is equal to 70000 N/mm2",
        trigger_terms=("modulus of elasticity","young's modulus","modulus elastisitas",
                       "elastic modulus","elasticity","elastisitas","young",
                       "aluminium","aluminum","alumunium",
                       "paduan aluminium","aluminium alloy","70000"),
        context_note="Discrete value 70000 N/mm^2 for aluminium alloys per Sec 2 D.1.7.",
    ),
    LookupRule(
        topic="sea_water_density",
        parameter=None,
        value_text="Massa jenis air laut = 1,025 t/m^3",
        value_text_en="The density of sea water used in the BKI Rules for Hull is 1.025 t/m^3.",
        value_text_id="Massa jenis air laut yang digunakan dalam BKI Rules for Hull adalah 1,025 t/m^3.",
        value_num=1.025, unit="t/m^3",
        section_no=21, paragraph_id="F.5.3.1", page_no=472,
        source_quote="rho = density of sea water (1,025 t/m3)",
        trigger_terms=("sea water density","seawater density","density of sea water",
                       "sea water","seawater",
                       "massa jenis air laut","densitas air laut",
                       "berat jenis air laut","air laut"),
        context_note="Discrete value 1,025 t/m^3 for sea water per Sec 21 F.5.3.1.",
    ),
    LookupRule(
        topic="hatch_min_thickness_single_skin",
        parameter=None,
        value_text="Single-skin hatch cover: t = 6,5 . a + tK [mm]; tmin = 5,0 + tK [mm] for project cargo (Sec 17 B.5.1.1, p.363).",
        value_text_en="Single-skin hatch cover: t = 6.5 . a + tK [mm]; tmin = 5.0 + tK [mm] for project cargo (Sec 17 B.5.1.1, p.363).",
        value_text_id="Pelat penutup palka kulit tunggal (single-skin hatch cover): t = 6,5 . a + tK [mm]; tmin = 5,0 + tK [mm] untuk project cargo (Sec 17 B.5.1.1, p.363).",
        value_num=6.5, unit="mm",
        section_no=17, paragraph_id="B.5.1.1", page_no=363,
        source_quote="t = 6,5 . a + tK [mm] If project cargo is intended to be carried on a hatch cover tmin = 5,0 + tK [mm]",
        trigger_terms=("palka kulit tunggal", "pelat penutup palka kulit tunggal",
                       "single skin", "single-skin"),
        context_note="Build 8: deterministic coverage for v3_single_skin_hatch (was F/P/P). Single-skin hatch cover formula per Sec 17 B.5.1.1.",
    ),
    LookupRule(
        topic="access_hatch_min_width",
        parameter=None,
        value_text="Access hatchways shall have a clear width of at least 600 x 600 mm (Sec 17 A.1.10, p.375).",
        value_text_en="Access hatchways shall have a clear width of at least 600 x 600 mm (Sec 17 A.1.10, p.375).",
        value_text_id="Bukaan palka akses (access hatchways) harus memiliki clear width minimum 600 x 600 mm (Sec 17 A.1.10, p.375).",
        value_num=600, unit="mm",
        section_no=17, paragraph_id="A.1.10", page_no=375,
        source_quote="Access hatchways shall have a clear width of at least 600 x 600 mm.",
        trigger_terms=("bukaan palka akses", "palka akses",
                       "access hatchway", "access hatch", "clear width"),
        context_note="Build 8: deterministic coverage for v3_access_hatch_width. Access hatchway clear width per Sec 17 A.1.10.",
    ),
    LookupRule(
        topic="tsc_definition",
        parameter=None,
        value_text="Sarat scantling (TSC) adalah sarat musim panas dalam meter, diukur dari sisi atas lunas (top of keel), atau nilai lebih besar yang ditetapkan sebagai \"scantling draught\" (Sec 1 H.2.9, p.24).",
        value_text_en="The scantling draught (TSC) is the summer draught, in metres, measured from top of keel, or a greater value if such a value has been specified as 'scantling draught' (Sec 1 H.2.9, p.24).",
        value_text_id="Sarat scantling (TSC) adalah sarat musim panas dalam meter, diukur dari sisi atas lunas (top of keel), atau nilai lebih besar yang ditetapkan sebagai \"scantling draught\" (Sec 1 H.2.9, p.24).",
        value_num=None, unit=None,
        section_no=1, paragraph_id="H.2.9", page_no=24,
        source_quote="Draught, T, is the summer draught, in metres, measured from top of keel, or a greater value if such a value has been specified as 'scantling draught'.",
        trigger_terms=("tsc", "sarat scantling", "sisi atas lunas", "top of keel", "titik ukur sarat"),
        context_note="Build 9: deterministic coverage for v3_tsc_measure_id. Avoids 'scantling draught' alone to prevent over-fire on ship_length_l_definition.",
    ),
    LookupRule(
        topic="aluminium_steel_galvanic_insulation",
        parameter=None,
        value_text="Untuk mencegah korosi galvanik, material insulasi non-higroskopis harus diaplikasikan di antara baja dan aluminium pada sambungan baut (Sec 2 E.5.2, p.44).",
        value_text_en="To prevent galvanic corrosion, a non-hygroscopic insulation material shall be applied between steel and aluminium in a bolted connection (Sec 2 E.5.2, p.44).",
        value_text_id="Untuk mencegah korosi galvanik, material insulasi non-higroskopis harus diaplikasikan di antara baja dan aluminium pada sambungan baut (Sec 2 E.5.2, p.44).",
        value_num=None, unit=None,
        section_no=2, paragraph_id="E.5.2", page_no=44,
        source_quote="To prevent galvanic corrosion a non-hygroscopic insulation material shall be applied between steel and aluminium when a bolted connection is used.",
        trigger_terms=("aluminium", "paduan aluminium", "galvanik", "korosi galvanik", "insulasi"),
        context_note="Build 9: deterministic coverage for v3_alu_steel_galvanic_id. Requires aluminium/paduan aluminium trigger to avoid over-fire on v2 steel-only corrosion queries.",
    ),
    LookupRule(
        topic="supply_deck_thickness",
        parameter=None,
        value_text="The thickness of deck plating is not to be taken less than 8,0 mm (for pL >= 40 kN/m2)",
        value_num=8.0, unit="mm",
        section_no=29, paragraph_id="F.4", page_no=668,
        source_quote="The thickness of deck plating is not to be taken less than 8,0 mm. In areas for the stowage of heavy cargoes the thickness of deck plating is to be suitably increased.",
        trigger_terms=("supply vessel", "deck plating", "8,0", "mm", "kapal suplai", "tebal geladak"),
        context_note="Build 10 (Bagian A): supply_deck_thickness misfire-guard.",
    ),
    LookupRule(
        topic="tanker_strake_width",
        parameter=None,
        value_text="The top and bottom strakes of the longitudinal bulkheads are to have a width of not less than 0,1H",
        value_num=0.1, unit="H",
        section_no=24, paragraph_id="A.10.1.2", page_no=604,
        source_quote="The top and bottom strakes of the longitudinal bulkheads are to have a width of not less than 0,1H, and their thickness is not to be less than: top strake of plating: tmin = 0,75 x deck thickness; bottom strake of plating: tmin = 0,75 x bottom thickness",
        trigger_terms=("tanker", "strake", "longitudinal bulkhead", "0,1H", "lebar strake", "sekat memanjang"),
        context_note="Build 10 (Bagian A): tanker_strake_width misfire-guard.",
    ),
    LookupRule(
        topic="anchor_vhhp_max_mass",
        parameter=None,
        value_text="The VHHP anchor mass is generally not to exceed 1500 kg (Sec 18 C.5, p.389).",
        value_num=1500, unit="kg",
        section_no=18, paragraph_id="C.5", page_no=389,
        source_quote="The VHHP anchor mass is generally not to exceed 1500 kg.",
        trigger_terms=("VHHP", "maximum mass", "massa maksimum", "maksimum", "mass", "massa", "massa jangkar", "anchor mass", "1500 kg", "maximum"),
        context_note="Build 13: anchor VHHP max mass.",
    ),
    LookupRule(
        topic="anchor_hhp_mass_reduction",
        parameter=None,
        value_text="When HHP anchors are used as bower anchors, the mass of each anchor may be 75% of the mass required for ordinary stockless bower anchors in Table 18.2 (Sec 18 C.4, p.389).",
        value_num=75, unit="%",
        section_no=18, paragraph_id="C.4", page_no=389,
        source_quote="When HHP anchors are used as bower anchors, the mass of each anchor may be 75% of the mass required for ordinary stockless bower anchors in the Table 18.2.",
        trigger_terms=("HHP", "75%", "mass reduction", "reduksi massa", "bower", "stockless", "mass", "massa", "reduced", "reduksi", "percentage", "persen", "massa jangkar", "anchor mass"),
        context_note="Build 13: HHP bower anchor mass reduction 75%.",
    ),
    LookupRule(
        topic="anchor_holding_power",
        parameter="hhp",
        value_text="Daya cengkeram minimum jangkar High Holding Power (HHP) paling sedikit dua kali jangkar stockless biasa dengan massa yang sama (Sec 18 C.4, p.389).",
        value_text_en="The minimum holding power of a High Holding Power (HHP) anchor is at least twice that of an ordinary stockless anchor of the same mass (Sec 18 C.4, p.389).",
        value_text_id="Daya cengkeram minimum jangkar High Holding Power (HHP) paling sedikit dua kali jangkar stockless biasa dengan massa yang sama (Sec 18 C.4, p.389).",
        value_num=None, unit=None,
        section_no=18, paragraph_id="C.4", page_no=389,
        source_quote="A 'high holding power' anchor is an anchor with a holding power of at least twice that of an ordinary stockless anchor of the same mass.",
        trigger_terms=("holding power", "daya cengkeram", "HHP", "two times", "twice", "dua kali", "kali lipat"),
        context_note="Discrete value: at least twice the holding power of ordinary stockless anchor.",
    ),
    LookupRule(
        topic="anchor_holding_power",
        parameter="vhhp",
        value_text="Daya cengkeram minimum jangkar Very High Holding Power (VHHP) paling sedikit empat kali jangkar stockless biasa dengan massa yang sama (Sec 18 C.5, p.389).",
        value_text_en="The minimum holding power of a Very High Holding Power (VHHP) anchor is at least four times that of an ordinary stockless anchor of the same mass (Sec 18 C.5, p.389).",
        value_text_id="Daya cengkeram minimum jangkar Very High Holding Power (VHHP) paling sedikit empat kali jangkar stockless biasa dengan massa yang sama (Sec 18 C.5, p.389).",
        value_num=None, unit=None,
        section_no=18, paragraph_id="C.5", page_no=389,
        source_quote="A 'very high holding power' anchor is an anchor with a holding power of at least four times that of an ordinary stockless anchor of the same mass.",
        trigger_terms=("holding power", "daya cengkeram", "VHHP", "four times", "empat kali"),
        context_note="Discrete value: at least four times the holding power of ordinary stockless anchor.",
    ),
    LookupRule(
        topic="rudder_force_coefficient",
        parameter="c1",
        value_text="Faktor tipe kapal c1 = 0,9 untuk bulk carrier dan tanker >50.000t (Sec 14 A.100, p.280).",
        value_text_en="Ship type factor c1 = 0.9 for bulk carriers and tankers >50,000t (Sec 14 A.100, p.280).",
        value_text_id="Faktor tipe kapal c1 = 0,9 untuk bulk carrier dan tanker >50.000t (Sec 14 A.100, p.280).",
        value_num=0.9, unit=None,
        section_no=14, paragraph_id="A.100", page_no=280,
        source_quote="c1 = factor for the ship type: = 1,0 in general = 0,9 for bulk carriers and tankers having a displacement of more than 50 000 ton = 1,7 for tugs and trawlers",
        trigger_terms=("rudder force coefficient", "c1", "ship type factor", "faktor tipe kapal", "bulk carrier", "tanker", "50000", "50 000"),
        context_note="Build 17: c1 = 0.9 for bulk carriers/tankers >50,000t.",
    ),
    LookupRule(
        topic="rudder_force_coefficient",
        parameter="c4",
        value_text="Faktor susunan kemudi c4 = 1,5 untuk kemudi di luar propeller jet (Sec 14 A.4.3, p.281).",
        value_text_en="Rudder arrangement factor c4 = 1.5 for rudders outside the propeller jet (Sec 14 A.4.3, p.281).",
        value_text_id="Faktor susunan kemudi c4 = 1,5 untuk kemudi di luar propeller jet (Sec 14 A.4.3, p.281).",
        value_num=1.5, unit=None,
        section_no=14, paragraph_id="A.4.3", page_no=281,
        source_quote="c4 = factor for the rudder arrangement: = 1,0 for rudders in the propeller jet = 1,5 for rudders outside the propeller jet",
        trigger_terms=("rudder force coefficient", "c4", "rudder arrangement", "faktor susunan kemudi", "propeller jet", "di luar", "outside", "semburan"),
        context_note="Build 17: c4 = 1.5 outside propeller jet.",
    ),
    LookupRule(
        topic="fatigue_correction_factor",
        parameter=None,
        value_text="Faktor koreksi fatik c = 0,15 untuk sambungan las siklus tegangan variabel (Sec 20 B.3.2.4, p.446).",
        value_text_en="Fatigue correction factor c = 0.15 for welded joints with variable stress cycles (Sec 20 B.3.2.4, p.446).",
        value_text_id="Faktor koreksi fatik c = 0,15 untuk sambungan las siklus tegangan variabel (Sec 20 B.3.2.4, p.446).",
        value_num=0.15, unit=None,
        section_no=20, paragraph_id="B.3.2.4", page_no=446,
        source_quote="c = 0 for welded joints subjected to constant stress cycles (stress range spectrum C) = 0,15 welded joints subjected to variable stress cycles (corresponding to stress range spectrum A or B)",
        trigger_terms=("fatigue correction factor", "faktor koreksi fatik", "correction factor c", "faktor koreksi c", "0.15", "0,15", "variable stress", "tegangan variabel", "welded joints", "sambungan las"),
        context_note="Build 17: c = 0.15 for welded joints with variable stress cycles.",
    ),
]


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


def test_sea_water_density_matches():
    match_en = match_lookup(
        query_id="",
        query_en="what is the density of sea water?",
        rules=_RULES,
    )
    assert match_en is not None
    assert match_en.rule.topic == "sea_water_density"
    assert match_en.rule.section_no == 21
    assert match_en.rule.paragraph_id == "F.5.3.1"
    match_id = match_lookup(
        query_id="berapa massa jenis air laut?",
        query_en="",
        rules=_RULES,
    )
    assert match_id is not None
    assert match_id.rule.topic == "sea_water_density"
    print("PASS: test_sea_water_density_matches")


def test_sea_water_density_rejects_cargo_density():
    match = match_lookup(
        query_id="berapa massa jenis muatan curah di palka?",
        query_en="",
        rules=_RULES,
    )
    if match is not None:
        assert match.rule.topic != "sea_water_density"
    print("PASS: test_sea_water_density_rejects_cargo_density")


def test_modulus_of_elasticity_matches():
    match_en = match_lookup(
        query_id="",
        query_en="what is the modulus of elasticity of steel?",
        rules=_RULES,
    )
    assert match_en is not None
    assert match_en.rule.topic == "modulus_of_elasticity"
    assert match_en.rule.parameter == "steel"
    assert match_en.rule.section_no == 3
    assert match_en.rule.paragraph_id == "F.5.1.6"
    match_id = match_lookup(
        query_id="berapa modulus elastisitas baja?",
        query_en="",
        rules=_RULES,
    )
    assert match_id is not None
    assert match_id.rule.topic == "modulus_of_elasticity"
    assert match_id.rule.parameter == "steel"
    print("PASS: test_modulus_of_elasticity_matches")


def test_modulus_of_elasticity_rejects_section_modulus():
    match = match_lookup(
        query_id="",
        query_en="what is the section modulus of the forepeak stringer?",
        rules=_RULES,
    )
    if match is not None:
        assert match.rule.topic != "modulus_of_elasticity"
    print("PASS: test_modulus_of_elasticity_rejects_section_modulus")


def test_modulus_of_elasticity_steel_still_matches():
    match = match_lookup(
        query_id="",
        query_en="what is the modulus of elasticity?",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "modulus_of_elasticity"
    assert match.rule.parameter == "steel"
    assert match.rule.value_num == 206000.0
    assert match.rule.section_no == 3
    print("PASS: test_modulus_of_elasticity_steel_still_matches")


def test_modulus_of_elasticity_aluminium_matches():
    match_en = match_lookup(
        query_id="",
        query_en="What is the Young's modulus of aluminium alloys?",
        rules=_RULES,
    )
    assert match_en is not None
    assert match_en.rule.topic == "modulus_of_elasticity"
    assert match_en.rule.parameter == "aluminium"
    assert match_en.rule.value_num == 70000
    assert match_en.rule.section_no == 2
    assert match_en.rule.paragraph_id == "D.1.7"
    match_id = match_lookup(
        query_id="modulus elastisitas paduan aluminium",
        query_en="",
        rules=_RULES,
    )
    assert match_id is not None
    assert match_id.rule.topic == "modulus_of_elasticity"
    assert match_id.rule.parameter == "aluminium"
    print("PASS: test_modulus_of_elasticity_aluminium_matches")


def test_modulus_aluminium_not_returns_steel():
    match = match_lookup(
        query_id="",
        query_en="What is the Young's modulus of aluminium alloys?",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.parameter == "aluminium"
    assert match.rule.value_num == 70000
    assert match.rule.value_num != 206000
    print("PASS: test_modulus_aluminium_not_returns_steel")


def test_material_factor_k_matches_on_k_query_id():
    match = match_lookup(
        query_id="berapa faktor material k untuk baja dengan tegangan luluh 355 N/mm2?",
        query_en="what is the material factor k for steel with yield strength 355 N/mm2?",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "material_factor_k"
    assert match.rule.section_no == 2
    assert match.rule.paragraph_id == "B.2"
    assert "0.72" in match.rule.value_text_en
    print("PASS: test_material_factor_k_matches_on_k_query_id")


def test_material_factor_k_rejects_without_anchor():
    match = match_lookup(
        query_id="",
        query_en="what is the fire door closing time for hinged door?",
        rules=_RULES,
    )
    if match is not None:
        assert match.rule.topic != "material_factor_k"
    print("PASS: test_material_factor_k_rejects_without_anchor")


def test_probability_factor_matches_on_fq_query_id():
    match = match_lookup(
        query_id="Berapa nilai faktor probabilitas fQ pada level probabilitas skantling standar?",
        query_en="what is the value of probability factor fQ at standard scantling probability level?",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "probability_factor_fq"
    assert match.rule.section_no == 4
    assert match.rule.paragraph_id == "E.1"
    assert "1.000" in match.rule.value_text_en
    print("PASS: test_probability_factor_matches_on_fq_query_id")


def test_probability_factor_rejects_without_anchor():
    match = match_lookup(
        query_id="",
        query_en="what is the section modulus reduction for coasting service?",
        rules=_RULES,
    )
    if match is not None:
        assert match.rule.topic != "probability_factor_fq"
    print("PASS: test_probability_factor_rejects_without_anchor")

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
# Build 8: single-skin hatch + access hatch coverage tests
# ---------------------------------------------------------------------------
def test_match_single_skin_hatch_id():
    """ID query on single-skin hatch cover must match the new rule."""
    match = match_lookup(
        query_id="Berapakah ketebalan minimum dari pelat penutup palka kulit tunggal (single skin hatch covers)?",
        query_en="",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "hatch_min_thickness_single_skin"
    assert match.rule.section_no == 17
    assert match.rule.paragraph_id == "B.5.1.1"
    assert match.rule.page_no == 363
    assert match.rule.value_num == 6.5
    print("PASS: test_match_single_skin_hatch_id")
def test_match_single_skin_hatch_en():
    """EN query on single skin hatch cover must match the new rule."""
    match = match_lookup(
        query_id="",
        query_en="minimum thickness for single skin hatch cover plating",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "hatch_min_thickness_single_skin"
    print("PASS: test_match_single_skin_hatch_en")
def test_single_skin_hatch_rejects_hatch_corrosion_query():
    """The single-skin rule must NOT fire on hatch corrosion queries."""
    match = match_lookup(
        query_id="",
        query_en="corrosion addition tK for hatch covers in general for weather deck cargo hatches of all bulk carriers",
        rules=_RULES,
    )
    if match is not None:
        assert match.rule.topic != "hatch_min_thickness_single_skin"
    print("PASS: test_single_skin_hatch_rejects_hatch_corrosion_query")
def test_single_skin_hatch_rejects_hatch_deflection_query():
    """The single-skin rule must NOT fire on hatch deflection queries."""
    match = match_lookup(
        query_id="",
        query_en="maximum allowed deflection for weather deck hatch covers under the design load pH",
        rules=_RULES,
    )
    if match is not None:
        assert match.rule.topic != "hatch_min_thickness_single_skin"
    print("PASS: test_single_skin_hatch_rejects_hatch_deflection_query")
def test_single_skin_hatch_rejects_unrelated_query():
    """The single-skin rule must NOT fire on unrelated queries."""
    match = match_lookup(
        query_id="",
        query_en="what is the density of sea water?",
        rules=_RULES,
    )
    if match is not None:
        assert match.rule.topic != "hatch_min_thickness_single_skin"
    print("PASS: test_single_skin_hatch_rejects_unrelated_query")
def test_match_access_hatch_width_id():
    """ID query on access hatchway must match the new rule."""
    match = match_lookup(
        query_id="Berapakah dimensi bersih (clear width) minimum untuk bukaan palka akses (access hatchways)?",
        query_en="",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "access_hatch_min_width"
    assert match.rule.section_no == 17
    assert match.rule.paragraph_id == "A.1.10"
    assert match.rule.page_no == 375
    assert match.rule.value_num == 600
    print("PASS: test_match_access_hatch_width_id")
def test_match_access_hatch_width_en():
    """EN query on access hatchway must match the new rule."""
    match = match_lookup(
        query_id="",
        query_en="minimum clear width of access hatchway shall be 600 x 600",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "access_hatch_min_width"
    print("PASS: test_match_access_hatch_width_en")
def test_access_hatch_rejects_hatch_corrosion_query():
    """The access-hatch rule must NOT fire on hatch corrosion queries."""
    match = match_lookup(
        query_id="",
        query_en="corrosion addition tK for hatch covers in general",
        rules=_RULES,
    )
    if match is not None:
        assert match.rule.topic != "access_hatch_min_width"
    print("PASS: test_access_hatch_rejects_hatch_corrosion_query")
def test_access_hatch_rejects_single_skin_query():
    """The access-hatch rule must NOT fire on single-skin hatch queries."""
    match = match_lookup(
        query_id="",
        query_en="minimum thickness for single skin hatch cover plating",
        rules=_RULES,
    )
    if match is not None:
        assert match.rule.topic != "access_hatch_min_width"
    print("PASS: test_access_hatch_rejects_single_skin_query")
# Build 9: tsc_definition + aluminium_steel_galvanic_insulation tests
# ---------------------------------------------------------------------------
def test_match_tsc_definition_id():
    """ID query on TSC measurement must match the new rule."""
    match = match_lookup(
        query_id="Di manakah letak pengukuran sarat scantling (TSC) dilakukan?",
        query_en="",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "tsc_definition"
    assert match.rule.section_no == 1
    assert match.rule.paragraph_id == "H.2.9"
    assert match.rule.page_no == 24
    assert "sisi atas lunas" in match.rule.value_text_id
    print("PASS: test_match_tsc_definition_id")
def test_tsc_definition_rejects_length_l_query():
    """The TSC rule must NOT fire on Length L definition queries."""
    match = match_lookup(
        query_id="Bagaimana definisi panjang kapal L dalam aturan ini?",
        query_en="",
        rules=_RULES,
    )
    if match is not None:
        assert match.rule.topic != "tsc_definition"
    print("PASS: test_tsc_definition_rejects_length_l_query")
def test_tsc_definition_rejects_v2_para_length_l():
    """The TSC rule must NOT fire on v2_para_length_l_measure_id."""
    match = match_lookup(
        query_id="Pada garis air dan sarat mana pengukuran Panjang Aturan?",
        query_en="",
        rules=_RULES,
    )
    if match is not None:
        assert match.rule.topic != "tsc_definition"
    print("PASS: test_tsc_definition_rejects_v2_para_length_l")
def test_match_alu_steel_galvanic_insulation_id():
    """ID query on aluminium-steel insulation must match the new rule."""
    match = match_lookup(
        query_id="Pada sambungan struktur baut antara paduan aluminium dan baja, apa yang harus diaplikasikan untuk mencegah korosi galvanik?",
        query_en="",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "aluminium_steel_galvanic_insulation"
    assert match.rule.section_no == 2
    assert match.rule.paragraph_id == "E.5.2"
    assert match.rule.page_no == 44
    assert "insulasi" in match.rule.value_text_id
    print("PASS: test_match_alu_steel_galvanic_insulation_id")
def test_alu_steel_rejects_v2_cathodic_protection():
    """The alu_steel rule must NOT fire on v2_cathodic_protection (galvanic anodes)."""
    match = match_lookup(
        query_id="",
        query_en="What material for galvanic anodes in sea chest?",
        rules=_RULES,
    )
    if match is not None:
        assert match.rule.topic != "aluminium_steel_galvanic_insulation"
    print("PASS: test_alu_steel_rejects_v2_cathodic_protection")
def test_alu_steel_rejects_v2_corrosion_addition_steel():
    """The alu_steel rule must NOT fire on v2_corrosion_addition_steel_id."""
    match = match_lookup(
        query_id="Bagaimana penambahan korosi diterapkan?",
        query_en="",
        rules=_RULES,
    )
    if match is not None:
        assert match.rule.topic != "aluminium_steel_galvanic_insulation"
    print("PASS: test_alu_steel_rejects_v2_corrosion_addition_steel")
def test_alu_steel_rejects_hatch_corrosion_query():
    """The alu_steel rule must NOT fire on hatch_corrosion_addition queries."""
    match = match_lookup(
        query_id="",
        query_en="corrosion addition tK for hatch covers in general for weather deck cargo hatches of all bulk carriers",
        rules=_RULES,
    )
    if match is not None:
        assert match.rule.topic != "aluminium_steel_galvanic_insulation"
    print("PASS: test_alu_steel_rejects_hatch_corrosion_query")
def test_access_hatch_rejects_unrelated_query():
    """The access-hatch rule must NOT fire on unrelated queries."""
    match = match_lookup(
        query_id="",
        query_en="what is the engine oil capacity?",
        rules=_RULES,
    )
    if match is not None:
        assert match.rule.topic != "access_hatch_min_width"
    print("PASS: test_access_hatch_rejects_unrelated_query")
# ---------------------------------------------------------------------------
# Anchor gate tests (Fase E precision fix)
# ---------------------------------------------------------------------------

def test_anchor_gate_accepts_forepeak_when_anchor_present():
    match = match_lookup(
        query_id="berapa jarak senta di ceruk haluan?",
        query_en="",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "forepeak_stringer_spacing"
    print("PASS: test_anchor_gate_accepts_forepeak_when_anchor_present")


def test_anchor_gate_rejects_forepeak_on_collision_bulkhead_position():
    match = match_lookup(
        query_id="Di manakah posisi sekat tubrukan (collision bulkhead) diukur dari garis tegak haluan?",
        query_en="where is the collision bulkhead position measured from the fore part",
        rules=_RULES,
    )
    assert match is None
    print("PASS: test_anchor_gate_rejects_forepeak_on_collision_bulkhead_position")


def test_anchor_gate_rejects_restricted_and_lengthL_on_depth_ratio():
    """The depth-ratio query now FIRES depth_to_length_ratio (added in same
    batch).  Restricted-service and ship-length rules must NOT win:
    no anchor match for them, depth rule's anchor ('rasio kedalaman' /
    'kedalaman terhadap panjang') is present.
    """
    match = match_lookup(
        query_id="Berapakah batas minimum rasio kedalaman terhadap panjang L untuk kapal di daerah pelayaran tidak terbatas?",
        query_en="minimum ratio of depth to length L for ships in unrestricted navigation areas",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "depth_to_length_ratio"
    assert "L/16" in match.rule.value_text
    print("PASS: test_anchor_gate_rejects_restricted_and_lengthL_on_depth_ratio")
def test_depth_rule_matches_on_depth_ratio_query_id():
    match = match_lookup(
        query_id="Berapakah batas minimum rasio kedalaman terhadap panjang L untuk kapal di daerah pelayaran tidak terbatas?",
        query_en="",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "depth_to_length_ratio"
    assert match.rule.section_no == 1
    assert match.rule.paragraph_id == "A.1"
    assert "L/16" in match.rule.value_text
    assert "L/18" in match.rule.value_text
    print("PASS: test_depth_rule_matches_on_depth_ratio_query_id")


def test_depth_rule_matches_on_depth_ratio_query_en():
    test_anchor_gate_rejects_bulwark_on_freeboard_query()
    test_anchor_gate_rejects_fire_door_on_plain_door_query()
    test_anchor_gate_rejects_length_l_on_freeboard_query()
    test_anchor_gate_rejects_restricted_on_generic_modulus_query()
    match = match_lookup(
        query_id="",
        query_en="What is the minimum depth to length ratio for ships in unlimited range of service?",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "depth_to_length_ratio"
    assert "L/16" in match.rule.value_text
    print("PASS: test_depth_rule_matches_on_depth_ratio_query_en")


def test_depth_rule_does_not_match_on_restricted_query():
    match = match_lookup(
        query_id="",
        query_en="what is the restricted ocean service P section modulus reduction?",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "restricted_service_modulus_reduction"
    print("PASS: test_depth_rule_does_not_match_on_restricted_query")


def test_depth_rule_does_not_match_on_length_l_query():
    match = match_lookup(
        query_id="",
        query_en="What is the rule length L in these rules?",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "ship_length_l_definition"
    print("PASS: test_depth_rule_does_not_match_on_length_l_query")


def test_mvz_rule_matches_on_mvz_length_query_id():
    match = match_lookup(
        query_id="berapa panjang maksimum rata-rata main vertical zone?",
        query_en="maximum average length of a main vertical zone",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "main_vertical_zone_dimension"
    assert match.rule.section_no == 22
    assert match.rule.paragraph_id == "B.2.1"
    assert match.rule.page_no == 489
    assert "40" in match.rule.value_text
    print("PASS: test_mvz_rule_matches_on_mvz_length_query_id")


def test_mvz_rule_does_not_match_on_freeboard_query():
    match = match_lookup(
        query_id="Berapa tinggi lambung timbul minimum kapal?",
        query_en="what is the minimum freeboard of the ship?",
        rules=_RULES,
    )
    if match is not None:
        assert match.rule.topic != "main_vertical_zone_dimension"
    print("PASS: test_mvz_rule_does_not_match_on_freeboard_query")


def test_mvz_anchor_gate_rejects_without_anchor():
    match = match_lookup(
        query_id="berapa panjang maksimum kapal?",
        query_en="what is the maximum length of the ship",
        rules=_RULES,
    )
    if match is not None:
        assert match.rule.topic != "main_vertical_zone_dimension"
    print("PASS: test_mvz_anchor_gate_rejects_without_anchor")
    print("PASS: test_depth_rule_does_not_match_on_length_l_query")


# ---------------------------------------------------------------------------

def test_anchor_gate_rejects_bulwark_on_freeboard_query():
    match = match_lookup(
        query_id="Berapa tinggi lambung timbul minimum kapal?",
        query_en="",
        rules=_RULES,
    )
    assert match is None or match.rule.topic != "bulwark_guardrail_min_height"
    print("PASS: test_anchor_gate_rejects_bulwark_on_freeboard_query")


def test_anchor_gate_rejects_fire_door_on_plain_door_query():
    match = match_lookup(
        query_id="Berapa tinggi minimum pintu kabin akomodasi?",
        query_en="",
        rules=_RULES,
    )
    assert match is None or match.rule.topic != "fire_door_closing_time"
    print("PASS: test_anchor_gate_rejects_fire_door_on_plain_door_query")


def test_anchor_gate_rejects_length_l_on_freeboard_query():
    match = match_lookup(
        query_id="Berapa tinggi lambung timbul minimum kapal?",
        query_en="what is the minimum freeboard of the ship?",
        rules=_RULES,
    )
    assert match is None or match.rule.topic != "ship_length_l_definition"
    print("PASS: test_anchor_gate_rejects_length_l_on_freeboard_query")


def test_anchor_gate_rejects_restricted_on_generic_modulus_query():
    match = match_lookup(
        query_id="",
        query_en="section modulus formula for frames",
        rules=_RULES,
    )
    assert match is None or match.rule.topic != "restricted_service_modulus_reduction"
    print("PASS: test_anchor_gate_rejects_restricted_on_generic_modulus_query")



def test_match_supply_deck_thickness_id_correct_fire():
    match = match_lookup(
        query_id="Untuk kapal suplai (supply vessels), berapakah ketebalan pelat geladak minimum yang disyaratkan?",
        query_en="",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "supply_deck_thickness"
    assert match.rule.value_num == 8.0
    assert match.rule.unit == "mm"
    print("PASS: test_match_supply_deck_thickness_id_correct_fire")


def test_match_supply_deck_thickness_en_correct_fire():
    match = match_lookup(
        query_id="",
        query_en="supply vessel deck plating thickness 8,0 mm minimum",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "supply_deck_thickness"
    print("PASS: test_match_supply_deck_thickness_en_correct_fire")


def test_supply_deck_thickness_rejects_engine_room_query():
    match = match_lookup(
        query_id="lokasi akses ruang mesin kapal suplai",
        query_en="",
        rules=_RULES,
    )
    assert match is None
    print("PASS: test_supply_deck_thickness_rejects_engine_room_query")


def test_supply_deck_thickness_rejects_ventilation_query():
    match = match_lookup(
        query_id="posisi pipa udara/ventilasi di geladak cuaca kapal suplai",
        query_en="",
        rules=_RULES,
    )
    assert match is None
    print("PASS: test_supply_deck_thickness_rejects_ventilation_query")


def test_match_tanker_strake_width_en_correct_fire():
    match = match_lookup(
        query_id="",
        query_en="In tankers, what is the minimum required width for the top and bottom strakes of longitudinal bulkheads?",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "tanker_strake_width"
    print("PASS: test_match_tanker_strake_width_en_correct_fire")


def test_match_tanker_strake_width_id_correct_fire():
    match = match_lookup(
        query_id="tanker lebar strake atas bawah sekat memanjang",
        query_en="",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "tanker_strake_width"
    print("PASS: test_match_tanker_strake_width_id_correct_fire")


def test_tanker_strake_width_rejects_passageway_query():
    match = match_lookup(
        query_id="dimensi under-deck passageway tanker",
        query_en="",
        rules=_RULES,
    )
    assert match is None
    print("PASS: test_tanker_strake_width_rejects_passageway_query")


def test_tanker_strake_width_rejects_stl_room_query():
    match = match_lookup(
        query_id="lokasi ruang STL (Submerged Turret Loading) kapal tanker",
        query_en="",
        rules=_RULES,
    )
    assert match is None
    print("PASS: test_tanker_strake_width_rejects_stl_room_query")


def test_match_bulwark_guardrail_height_correct_fire_id():
    match = match_lookup(
        query_id="tinggi minimum bulwark atau guard rail berapa?",
        query_en="",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "bulwark_guardrail_min_height"
    print("PASS: test_match_bulwark_guardrail_height_correct_fire_id")


def test_match_bulwark_guardrail_height_correct_fire_en():
    match = match_lookup(
        query_id="",
        query_en="minimum height of guard rail",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "bulwark_guardrail_min_height"
    print("PASS: test_match_bulwark_guardrail_height_correct_fire_en")


def test_bulwark_guardrail_rejects_sill_query():
    match = match_lookup(
        query_id="sill height bukaan akses enclosed superstructure",
        query_en="",
        rules=_RULES,
    )
    assert match is None
    print("PASS: test_bulwark_guardrail_rejects_sill_query")


def test_match_alu_steel_insulation_correct_fire_id():
    match = match_lookup(
        query_id="Pada sambungan struktur baut antara paduan aluminium dan baja, apa yang harus diaplikasikan untuk mencegah korosi galvanik?",
        query_en="",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "aluminium_steel_galvanic_insulation"
    print("PASS: test_match_alu_steel_insulation_correct_fire_id")


def test_match_alu_steel_insulation_correct_fire_id_alt():
    match = match_lookup(
        query_id="material insulasi apa yang diaplikasikan untuk mencegah korosi galvanik antara baja dan aluminium",
        query_en="",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "aluminium_steel_galvanic_insulation"
    print("PASS: test_match_alu_steel_insulation_correct_fire_id_alt")


def test_alu_steel_insulation_rejects_fire_test_query():
    match = match_lookup(
        query_id="tes api suhu kenaikan suhu aluminium fire test",
        query_en="",
        rules=_RULES,
    )
    assert match is None
    print("PASS: test_alu_steel_insulation_rejects_fire_test_query")


# ---------------------------------------------------------------------------
# Build 13: anchor mass facts (VHHP 1500 kg, HHP 75% mass reduction)
# ---------------------------------------------------------------------------

def test_anchor_vhhp_max_mass_fires_on_mass_query_id():
    match = match_lookup(
        query_id="Berapa massa maksimum yang diizinkan untuk jangkar VHHP?",
        query_en="",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "anchor_vhhp_max_mass"
    assert match.rule.value_num == 1500
    assert match.rule.unit == "kg"
    assert match.rule.section_no == 18
    print("PASS: test_anchor_vhhp_max_mass_fires_on_mass_query_id")


def test_anchor_vhhp_max_mass_fires_on_mass_query_en():
    match = match_lookup(
        query_id="",
        query_en="What is the maximum mass allowed for a VHHP anchor?",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "anchor_vhhp_max_mass"
    print("PASS: test_anchor_vhhp_max_mass_fires_on_mass_query_en")


def test_anchor_vhhp_max_mass_rejects_holding_power_query():
    match = match_lookup(
        query_id="",
        query_en="What is the holding power of a VHHP anchor compared to a stockless anchor?",
        rules=_RULES,
    )
    if match is not None:
        assert match.rule.topic != "anchor_vhhp_max_mass"
    print("PASS: test_anchor_vhhp_max_mass_rejects_holding_power_query")


def test_anchor_vhhp_max_mass_rejects_stockless_only_query():
    match = match_lookup(
        query_id="",
        query_en="What is the holding power of an ordinary stockless anchor?",
        rules=_RULES,
    )
    if match is not None:
        assert match.rule.topic != "anchor_vhhp_max_mass"
    print("PASS: test_anchor_vhhp_max_mass_rejects_stockless_only_query")


def test_anchor_hhp_mass_reduction_fires_on_reduction_query_id():
    match = match_lookup(
        query_id="Menurut Section 18, berapa persen massa jangkar stockless yang menjadi massa minimum jangkar bower High Holding Power (HHP)?",
        query_en="",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "anchor_hhp_mass_reduction"
    assert match.rule.value_num == 75
    assert match.rule.unit == "%"
    assert match.rule.section_no == 18
    print("PASS: test_anchor_hhp_mass_reduction_fires_on_reduction_query_id")


def test_anchor_hhp_mass_reduction_fires_on_reduction_query_en():
    match = match_lookup(
        query_id="",
        query_en="For High Holding Power (HHP) bower anchors, the mass of each anchor may be reduced to what percentage of the ordinary stockless bower anchor mass, per Section 18?",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "anchor_hhp_mass_reduction"
    print("PASS: test_anchor_hhp_mass_reduction_fires_on_reduction_query_en")


def test_anchor_hhp_mass_reduction_rejects_holding_power_query():
    match = match_lookup(
        query_id="",
        query_en="What is the holding power of a High Holding Power anchor?",
        rules=_RULES,
    )
    if match is not None:
        assert match.rule.topic != "anchor_hhp_mass_reduction"
    print("PASS: test_anchor_hhp_mass_reduction_rejects_holding_power_query")


def test_anchor_hhp_mass_reduction_rejects_head_mass_query():
    match = match_lookup(
        query_id="",
        query_en="What is the minimum mass of the heads of ordinary stockless anchors including pins and fittings?",
        rules=_RULES,
    )
    if match is not None:
        assert match.rule.topic != "anchor_hhp_mass_reduction"
    print("PASS: test_anchor_hhp_mass_reduction_rejects_head_mass_query")


# ---------------------------------------------------------------------------
# Build 15: paraphrase trigger coverage (depth/length ratio + HHP holding power)
# ---------------------------------------------------------------------------

def test_depth_ratio_paraphrase_id_fires():
    match = match_lookup(
        query_id="Berapa batas minimum perbandingan H/L untuk kapal samudra?",
        query_en="What is the minimum height to length ratio for ocean ships?",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "depth_to_length_ratio"
    print("PASS: test_depth_ratio_paraphrase_id_fires")


def test_depth_ratio_paraphrase_en_fires():
    match = match_lookup(
        query_id="What is the lower bound for the depth-to-length ratio for ocean-going vessels?",
        query_en="What is the lower bound for the depth-to-length ratio for ocean-going vessels?",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "depth_to_length_ratio"
    print("PASS: test_depth_ratio_paraphrase_en_fires")


def test_depth_ratio_anti_misfire_generic_ocean_query():
    match = match_lookup(
        query_id="Apa itu kapal samudra?",
        query_en="What is an ocean-going ship?",
        rules=_RULES,
    )
    if match is not None:
        assert match.rule.topic != "depth_to_length_ratio"
    print("PASS: test_depth_ratio_anti_misfire_generic_ocean_query")


def test_anchor_hhp_paraphrase_id_fires():
    match = match_lookup(
        query_id="Berapa kali lipat daya jangkar HHP dibanding jangkar stockless standar?",
        query_en="By what factor does the HHP anchor holding power exceed the standard stockless anchor?",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "anchor_holding_power"
    assert match.rule.parameter == "hhp"
    print("PASS: test_anchor_hhp_paraphrase_id_fires")


def test_anchor_hhp_paraphrase_crossfire_mass_reduction_rejected():
    match = match_lookup(
        query_id="Berapa kali lipat pengurangan massa jangkar HHP?",
        query_en="By what factor is the HHP anchor mass reduced?",
        rules=_RULES,
    )
    if match is not None:
        assert match.rule.topic != "anchor_holding_power"
    print("PASS: test_anchor_hhp_paraphrase_crossfire_mass_reduction_rejected")


def test_anchor_hhp_paraphrase_crossfire_vhhp_mass_rejected():
    match = match_lookup(
        query_id="Berapa kali lipat massa jangkar VHHP yang diizinkan?",
        query_en="By what factor is the VHHP anchor mass limited?",
        rules=_RULES,
    )
    if match is not None:
        assert match.rule.topic != "anchor_holding_power"
    print("PASS: test_anchor_hhp_paraphrase_crossfire_vhhp_mass_rejected")


# ---------------------------------------------------------------------------
# Build 17: rudder force coefficients (c1, c4) + fatigue correction factor
# ---------------------------------------------------------------------------

def test_rudder_c1_fires_on_bulk_carrier_query():
    match = match_lookup(
        query_id="Berapa faktor tipe kapal c1 untuk bulk carrier pada perhitungan kemudi?",
        query_en="What is the ship type c1 factor for bulk carrier in rudder calculation?",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "rudder_force_coefficient"
    assert match.rule.parameter == "c1"
    assert match.rule.value_num == 0.9
    assert match.rule.section_no == 14
    print("PASS: test_rudder_c1_fires_on_bulk_carrier_query")


def test_rudder_c4_fires_on_outside_query():
    match = match_lookup(
        query_id="Berapa faktor susunan kemudi c4 untuk kemudi di luar semburan baling-baling?",
        query_en="What is the rudder arrangement factor c4 for rudders outside the propeller jet?",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "rudder_force_coefficient"
    assert match.rule.parameter == "c4"
    assert match.rule.value_num == 1.5
    assert match.rule.section_no == 14
    print("PASS: test_rudder_c4_fires_on_outside_query")


def test_rudder_c1_rejects_c4_query():
    match = match_lookup(
        query_id="Berapa faktor susunan kemudi c4 untuk kemudi di luar semburan?",
        query_en="What is the rudder arrangement factor c4 outside propeller jet?",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.parameter == "c4"
    print("PASS: test_rudder_c1_rejects_c4_query")


def test_rudder_horn_shear_not_fires_rudder_coefficient():
    match = match_lookup(
        query_id="Berapa batas tegangan geser maksimum pada tanduk kemudi?",
        query_en="What is the maximum shear stress limit in the rudder horn?",
        rules=_RULES,
    )
    if match is not None:
        assert match.rule.topic != "rudder_force_coefficient"
    print("PASS: test_rudder_horn_shear_not_fires_rudder_coefficient")


def test_fatigue_c_fires_on_variable_stress_query():
    match = match_lookup(
        query_id="Berapa nilai faktor koreksi c untuk sambungan las yang mengalami siklus tegangan variabel?",
        query_en="What is the correction factor c for welded joints experiencing variable stress cycles?",
        rules=_RULES,
    )
    assert match is not None
    assert match.rule.topic == "fatigue_correction_factor"
    assert match.rule.value_num == 0.15
    assert match.rule.section_no == 20
    print("PASS: test_fatigue_c_fires_on_variable_stress_query")


def test_fatigue_c_rejects_rudder_query():
    match = match_lookup(
        query_id="Berapa faktor tipe kapal c1?",
        query_en="What is the ship type factor c1?",
        rules=_RULES,
    )
    if match is not None:
        assert match.rule.topic != "fatigue_correction_factor"
    print("PASS: test_fatigue_c_rejects_rudder_query")


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
    # Anchor gate tests
    test_anchor_gate_accepts_forepeak_when_anchor_present()
    test_anchor_gate_rejects_forepeak_on_collision_bulkhead_position()
    test_anchor_gate_rejects_restricted_and_lengthL_on_depth_ratio()
    test_anchor_gate_rejects_bulwark_on_freeboard_query()
    test_anchor_gate_rejects_fire_door_on_plain_door_query()
    test_anchor_gate_rejects_length_l_on_freeboard_query()
    test_anchor_gate_rejects_restricted_on_generic_modulus_query()
    # Depth rule
    test_depth_rule_matches_on_depth_ratio_query_id()
    test_depth_rule_matches_on_depth_ratio_query_en()
    test_depth_rule_does_not_match_on_restricted_query()
    test_depth_rule_does_not_match_on_length_l_query()
    # MVZ rule
    test_mvz_rule_matches_on_mvz_length_query_id()
    test_mvz_rule_does_not_match_on_freeboard_query()
    # Build 8: single-skin + access hatch rules
    test_match_single_skin_hatch_id()
    test_match_single_skin_hatch_en()
    test_single_skin_hatch_rejects_hatch_corrosion_query()
    test_single_skin_hatch_rejects_hatch_deflection_query()
    test_single_skin_hatch_rejects_unrelated_query()
    test_match_access_hatch_width_id()
    test_match_access_hatch_width_en()
    test_access_hatch_rejects_hatch_corrosion_query()
    test_access_hatch_rejects_single_skin_query()
    test_access_hatch_rejects_unrelated_query()
    test_access_hatch_rejects_unrelated_query()
    # Build 9: tsc_definition + aluminium_steel_galvanic_insulation tests
    test_match_tsc_definition_id()
    test_tsc_definition_rejects_length_l_query()
    test_tsc_definition_rejects_v2_para_length_l()
    test_match_alu_steel_galvanic_insulation_id()
    test_alu_steel_rejects_v2_cathodic_protection()
    test_alu_steel_rejects_v2_corrosion_addition_steel()
    test_alu_steel_rejects_hatch_corrosion_query()
    test_mvz_anchor_gate_rejects_without_anchor()
    # Build 10: misfire-guard tests
    test_match_supply_deck_thickness_id_correct_fire()
    test_match_supply_deck_thickness_en_correct_fire()
    test_supply_deck_thickness_rejects_engine_room_query()
    test_supply_deck_thickness_rejects_ventilation_query()
    test_match_tanker_strake_width_en_correct_fire()
    test_match_tanker_strake_width_id_correct_fire()
    test_tanker_strake_width_rejects_passageway_query()
    test_tanker_strake_width_rejects_stl_room_query()
    test_match_bulwark_guardrail_height_correct_fire_id()
    test_match_bulwark_guardrail_height_correct_fire_en()
    test_bulwark_guardrail_rejects_sill_query()
    test_match_alu_steel_insulation_correct_fire_id()
    test_match_alu_steel_insulation_correct_fire_id_alt()
    test_alu_steel_insulation_rejects_fire_test_query()
    # Build 13: anchor mass facts
    test_anchor_vhhp_max_mass_fires_on_mass_query_id()
    test_anchor_vhhp_max_mass_fires_on_mass_query_en()
    test_anchor_vhhp_max_mass_rejects_holding_power_query()
    test_anchor_vhhp_max_mass_rejects_stockless_only_query()
    test_anchor_hhp_mass_reduction_fires_on_reduction_query_id()
    test_anchor_hhp_mass_reduction_fires_on_reduction_query_en()
    test_anchor_hhp_mass_reduction_rejects_holding_power_query()
    test_anchor_hhp_mass_reduction_rejects_head_mass_query()
    # Build 15: paraphrase trigger coverage
    test_depth_ratio_paraphrase_id_fires()
    test_depth_ratio_paraphrase_en_fires()
    test_depth_ratio_anti_misfire_generic_ocean_query()
    test_anchor_hhp_paraphrase_id_fires()
    test_anchor_hhp_paraphrase_crossfire_mass_reduction_rejected()
    test_anchor_hhp_paraphrase_crossfire_vhhp_mass_rejected()
    # Build 17: rudder and fatigue factor tests
    test_rudder_c1_fires_on_bulk_carrier_query()
    test_rudder_c4_fires_on_outside_query()
    test_rudder_c1_rejects_c4_query()
    test_rudder_horn_shear_not_fires_rudder_coefficient()
    test_fatigue_c_fires_on_variable_stress_query()
    test_fatigue_c_rejects_rudder_query()
    print("\nAll 73 tests passed!")

