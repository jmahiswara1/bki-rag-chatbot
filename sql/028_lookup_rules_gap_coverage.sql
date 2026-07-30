-- 028_lookup_rules_gap_coverage.sql
-- Gap coverage for 3 topics that failed in manual QA evaluation:
-- 1. SPM bow chain stopper chain size (Sec 24)
-- 2. Aluminium helideck fire protection (Sec 22)
-- 3. IW underwater hull corrosion protection (Sec 37 + Sec 38)

BEGIN;

-- Rule 1: SPM bow chain stopper chain size
DELETE FROM lookup_rules WHERE topic = 'spm_bow_chain_stopper_chain_size';
INSERT INTO lookup_rules (
  topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
  section_no, paragraph_id, page_no, source_quote,
  trigger_terms, context_note,
  verified, verified_by, verified_at
) VALUES (
  'spm_bow_chain_stopper_chain_size',
  NULL,
  'Untuk sistem Single Point Mooring (SPM), satu atau dua penahan rantai haluan (bow chain stoppers) harus dipasang dan mampu menerima rantai stud-link standar 76 mm (chafing chain).',
  'For Single Point Mooring (SPM) systems, one or two bow chain stoppers are to be fitted, capable to accept a standard 76 mm stud-link chain (chafing chain).',
  'Untuk sistem Single Point Mooring (SPM), satu atau dua penahan rantai haluan (bow chain stoppers) harus dipasang dan mampu menerima rantai stud-link standar 76 mm (chafing chain).',
  76,
  'mm',
  24,
  'L.2.1.1',
  615,
  'One or two bow chain stoppers are to be fitted, capable to accept a standard 76 mm stud-link chain (chafing chain, as defined in the OCIMF "Recommendations for Equipment Employed in the Mooring of Ships at Single Point Moorings").',
  ARRAY['stud-link chain', 'stud link chain', 'rantai stud-link', 'rantai stud link', 'SPM', 'single point mooring', 'penahan rantai haluan', 'bow chain stopper', 'chain stopper', 'bow stopper', 'chafing chain', 'ukuran rantai', 'chain size'],
  'Build 37 gap coverage. Fixed-size 76 mm for all vessel sizes. SWL varies per Table 24.2.',
  true,
  'akashi',
  now()
);

-- Rule 2: Aluminium helideck fire protection
DELETE FROM lookup_rules WHERE topic = 'aluminium_helideck_fire_protection';
INSERT INTO lookup_rules (
  topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
  section_no, paragraph_id, page_no, source_quote,
  trigger_terms, context_note,
  verified, verified_by, verified_at
) VALUES (
  'aluminium_helideck_fire_protection',
  NULL,
  'Jika helideck dibangun dari aluminium atau logam titik leleh rendah lainnya, ketentuan berikut harus dipenuhi: (1) Jika platform kantilever, setelah setiap kebakaran harus dilakukan analisis struktural; (2) Jika platform di atas deckhouse, top dan bulkhead di bawahnya tidak boleh memiliki bukaan, semua jendela harus dilengkapi steel shutters, peralatan pemadam sesuai Rules for Machinery Installations Sec.12, dan analisis struktural setelah kebakaran; (3) Harus disediakan akses keluar utama dan darurat yang terpisah sejauh mungkin.',
  'If an aluminium or other low melting metal construction is used for the helideck: (1) If cantilevered, after each fire a structural analysis shall be performed; (2) If located above a deckhouse, the deckhouse top and bulkheads below shall have no openings, all windows shall have steel shutters, fire-fighting equipment per Machinery Installations Rules Sec.12, and structural analysis after each fire; (3) A main and an emergency means of escape shall be provided, located as far apart as practicable.',
  'Jika helideck dibangun dari aluminium atau logam titik leleh rendah lainnya, ketentuan berikut harus dipenuhi: (1) Jika platform kantilever, setelah setiap kebakaran harus dilakukan analisis struktural; (2) Jika platform di atas deckhouse, top dan bulkhead di bawahnya tidak boleh memiliki bukaan, semua jendela harus dilengkapi steel shutters, peralatan pemadam sesuai Rules for Machinery Installations Sec.12, dan analisis struktural setelah kebakaran; (3) Harus disediakan akses keluar utama dan darurat yang terpisah sejauh mungkin.',
  NULL,
  NULL,
  22,
  'G.1',
  545,
  'If an aluminium or other low melting metal construction will be allowed, the following provisions shall be satisfied: 1.1 If the platform is cantilevered over the side of the ship, after each fire on the ship or on the platform, the platform shall undergo a structural analysis to determine its suitability for further use. 1.2 If the platform is located above the ship''s deckhouse or similar structure, the following conditions shall be satisfied: 1.2.1 the deckhouse top and bulkheads under the platform shall have no openings; 1.2.2 all windows under the platform shall be provided with steel shutters; 1.2.3 the required fire-fighting equipment shall be in accordance with the requirements of Rules for Machinery Installations (Pt.1, Vol.III) Sec.12. 1.2.4 after each fire on the platform or in close proximity, the platform shall undergo a structural analysis to determine its suitability for further use. 1.3 A helideck shall be provided with both a main and an emergency means of escape and access for fire fighting and rescue personnel.',
  ARRAY['helideck', 'helipad', 'helicopter deck', 'helicopter', 'landing area', 'aluminium', 'aluminum', 'paduan aluminium', 'aluminium alloy', 'logam dengan titik leleh rendah', 'low melting point', 'low melting metal', 'titik leleh rendah', 'bukan ekuivalen baja', 'not steel equivalent', 'perlindungan kebakaran struktural', 'structural fire protection', 'helikopter'],
  'Build 37 gap coverage. Q2 failure: retrieval missed Sec 22.G.1 intro paragraph.',
  true,
  'akashi',
  now()
);

-- Rule 3: IW underwater hull corrosion protection
DELETE FROM lookup_rules WHERE topic = 'iw_underwater_hull_corrosion';
INSERT INTO lookup_rules (
  topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
  section_no, paragraph_id, page_no, source_quote,
  trigger_terms, context_note,
  verified, verified_by, verified_at
) VALUES (
  'iw_underwater_hull_corrosion',
  NULL,
  'Untuk kapal dengan Notasi Kelas IW (In-Water Survey), sistem perlindungan korosi bawah air wajib terdiri dari: (1) Sistem coating tanpa anti-fouling dengan ketebalan film kering minimum 250 μm pada seluruh permukaan, kompatibel dengan cathodic protection, dan sesuai untuk pembersihan mekanis bawah air; (2) Cathodic protection (sacrificial anodes atau impressed current) didesain untuk minimal satu periode docking, dengan rapat arus proteksi minimal 10 mA/m² untuk baja; (3) Coating berbasis epoxy, polyurethane, atau polyvinyl chloride dianggap sesuai.',
  'For vessels with IW (In-Water Survey) Class Notation, the underwater hull corrosion protection system shall consist of: (1) A coating system without anti-fouling with a minimum dry film thickness of 250 μm on the complete surface, compatible with cathodic protection, and suitable for mechanical underwater cleaning; (2) Cathodic protection (sacrificial anodes or impressed current) designed for at least one docking period, with a protection current density of at least 10 mA/m² for steel; (3) Coatings based on epoxy, polyurethane, and polyvinyl chloride are considered suitable.',
  'Untuk kapal dengan Notasi Kelas IW (In-Water Survey), sistem perlindungan korosi bawah air wajib terdiri dari: (1) Sistem coating tanpa anti-fouling dengan ketebalan film kering minimum 250 μm pada seluruh permukaan, kompatibel dengan cathodic protection, dan sesuai untuk pembersihan mekanis bawah air; (2) Cathodic protection (sacrificial anodes atau impressed current) didesain untuk minimal satu periode docking, dengan rapat arus proteksi minimal 10 mA/m² untuk baja; (3) Coating berbasis epoxy, polyurethane, atau polyvinyl chloride dianggap sesuai.',
  NULL,
  NULL,
  38,
  'H.1.1',
  693,
  'Vessels intended to be assigned the Class Notation IW (In-Water Survey) shall provide a suitable corrosion protection system for the underwater hull, consisting of coating and cathodic protection.',
  ARRAY['in-water survey', 'in water survey', 'IW', 'underwater hull', 'lambung bawah air', 'corrosion protection', 'perlindungan korosi', 'coating', 'pelapisan', 'cathodic protection', 'sacrificial anode', 'impressed current', 'ICCP', 'anoda korban', 'arus tanding', 'notasi kelas', 'class notation', '250 μm', 'ketebalan film', 'film thickness', 'epoxy', 'polyurethane'],
  'Build 37 gap coverage. Q3 failure: retrieval only got Sec 38 H.1.4, missed Sec 37 B.1 and Sec 38 H.1.1-H.1.5 details.',
  true,
  'akashi',
  now()
);

COMMIT;
