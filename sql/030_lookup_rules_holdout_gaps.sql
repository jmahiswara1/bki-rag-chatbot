-- 030_lookup_rules_holdout_gaps.sql
-- Verified lookup coverage for three held-out Hull rule topics.

BEGIN;

DELETE FROM lookup_rules WHERE topic IN (
  'superstructure_corrosion_addition',
  'windows_side_scuttles_iso_test',
  'dredger_bottom_transverse_spacing'
);

INSERT INTO lookup_rules (
  topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
  section_no, paragraph_id, page_no, source_quote,
  trigger_terms, context_note,
  verified, verified_by, verified_at
) VALUES
(
  'superstructure_corrosion_addition', NULL,
  'tK = 1,0 mm untuk pelat superstruktur dengan ketebalan 10 mm atau kurang.',
  'For superstructure plating with thickness 10 mm or less, the corrosion addition tK is 1.0 mm.',
  'Untuk pelat superstruktur dengan ketebalan 10 mm atau kurang, penambahan korosi tK adalah 1,0 mm.',
  1.0, 'mm', 3, 'L.2', 119,
  'tK = 1,0 [mm] for t'' ≤ 10 mm.',
  ARRAY['corrosion addition', 'corrosion allowance', 'tK', 'superstructure plating', 'superstructure deck', 'pelat superstruktur', 'pelat bangunan atas', '10 mm'],
  'Sec 3 K/L.2: direct table value for superstructure plating at t'' ≤ 10 mm. Do not substitute the shell-plating formula.',
  true, 'bki-rag-eval', now()
),
(
  'windows_side_scuttles_iso_test', NULL,
  'Jendela dan side scuttles harus diuji sesuai standar ISO yang relevan, yaitu ISO 1751 dan ISO 3903.',
  'Windows and side scuttles have to be tested in accordance with the respective ISO standards 1751 and 3903.',
  'Jendela dan side scuttles harus diuji sesuai standar ISO yang relevan, yaitu ISO 1751 dan ISO 3903.',
  NULL, NULL, 22, 'E.4.6', 465,
  'Windows and side scuttles have to be tested in accordance with the respective ISO standards 1751 and 3903.',
  ARRAY['windows', 'side scuttles', 'windows and side scuttles', 'ISO standards', 'ISO 1751', 'ISO 3903', 'jendela', 'side scuttle'],
  'Sec 22 E.4.6: testing standards for windows and side scuttles.',
  true, 'bki-rag-eval', now()
),
(
  'dredger_bottom_transverse_spacing', NULL,
  'Pada kapal keruk dengan dasar tunggal berkonstruksi memanjang, jarak umum transverses dasar tidak boleh melebihi 3,6 m.',
  'For single-bottom longitudinally framed dredgers, the general spacing of bottom transverses is not to exceed 3.6 m.',
  'Pada kapal keruk dengan dasar tunggal berkonstruksi memanjang, jarak umum transverses dasar tidak boleh melebihi 3,6 m.',
  3.6, 'm', 32, 'H', 647,
  'Distance of bottom transverses not to exceed 3.6 m.',
  ARRAY['dredger', 'dredgers', 'bottom transverses', 'transverses dasar', 'single bottom', 'dasar tunggal', '3.6', '3,6'],
  'Sec 32 H: maximum general spacing for bottom transverses on dredgers.',
  true, 'bki-rag-eval', now()
);

COMMIT;
