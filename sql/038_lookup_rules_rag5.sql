-- 038_lookup_rules_rag5.sql
-- Safety-net lookup rules for the notebookLM 5-QA RAG-strengthening batch
-- (Build 45). Values PDF-verified against data/bki_hull_2026.pdf:
--
--   1. lubricating_oil_circulating_tank_shell  Sec 8  p.212 5.2.2
--        "The lubricating oil circulating tanks are to be separated from
--         the shell by at least 500 mm."
--   2. indonesian_flag_cofferdam_accommodation  Sec 12 p.258 5.2.1 footnote
--        "For Indonesian flag ship, the cofferdams are also required between
--         accommodation spaces and oil tanks."
--   3. wheel_house_top_min_load                 Sec 4  p.126 5.2
--        "For exposed wheel house tops the load is not to be taken less
--         than p = 2,5 [kN/m2]."

BEGIN;

DELETE FROM lookup_rules WHERE topic IN (
  'lubricating_oil_circulating_tank_shell',
  'indonesian_flag_cofferdam_accommodation',
  'wheel_house_top_min_load'
);

INSERT INTO lookup_rules (
  topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
  section_no, paragraph_id, page_no, source_quote,
  trigger_terms, context_note,
  verified, verified_by, verified_at
) VALUES
(
  'lubricating_oil_circulating_tank_shell', NULL,
  'Tangki sirkulasi minyak lumas (lubricating oil circulating tanks) harus dipisahkan dari kulit lambung kapal dengan jarak sekurang-kurangnya 500 mm.',
  'The lubricating oil circulating tanks are to be separated from the shell by at least 500 mm.',
  'Tangki sirkulasi minyak lumas (lubricating oil circulating tanks) harus dipisahkan dari kulit lambung kapal dengan jarak sekurang-kurangnya 500 mm.',
  500.0, 'mm', 8, 'B.5.2.2', 212,
  'The lubricating oil circulating tanks are to be separated from the shell by at least 500 mm.',
  ARRAY['lubricating oil circulating tank', 'lubricating oil circulating tanks', 'circulating tanks', 'circulating tank', 'tangki sirkulasi minyak lumas', 'tangki sirkulasi', 'sirkulasi minyak lumas', 'separated from the shell', 'dipisahkan dari kulit lambung', 'kulit lambung', '500 mm', '500'],
  'Sec 8 B.5.2.2 p212: lubricating oil circulating tanks separated from the shell by at least 500 mm.',
  true, 'bki-rag-qa', now()
),
(
  'indonesian_flag_cofferdam_accommodation', NULL,
  'Untuk kapal berbendera Indonesia, cofferdam juga wajib disediakan untuk memisahkan antara ruang akomodasi (accommodation spaces) dan tangki-tangki minyak (oil tanks).',
  'For Indonesian flag ships, cofferdams are also required between accommodation spaces and oil tanks.',
  'Untuk kapal berbendera Indonesia, cofferdam juga wajib disediakan untuk memisahkan antara ruang akomodasi (accommodation spaces) dan tangki-tangki minyak (oil tanks).',
  NULL, NULL, 12, 'A.5.2.1', 258,
  'For Indonesian flag ship, the cofferdams are also required between accommodation spaces and oil tanks.',
  ARRAY['indonesian flag', 'indonesian flag ship', 'indonesian-flagged', 'berbendera indonesia', 'bendera indonesia', 'kapal berbendera indonesia', 'cofferdam', 'cofferdams', 'sekat pembatas ganda', 'akomodasi', 'accommodation', 'oil tanks', 'tangki minyak'],
  'Sec 12 A.5.2.1 footnote p258: Indonesian-flag ships also require cofferdams between accommodation spaces and oil tanks.',
  true, 'bki-rag-qa', now()
),
(
  'wheel_house_top_min_load', NULL,
  'Beban desain minimum untuk area atap ruang kemudi yang terbuka (exposed wheel house tops) tidak boleh diambil kurang dari 2,5 kN/m².',
  'For exposed wheel house tops the load is not to be taken less than p = 2,5 kN/m2.',
  'Beban desain minimum untuk area atap ruang kemudi yang terbuka (exposed wheel house tops) tidak boleh diambil kurang dari 2,5 kN/m².',
  2.5, 'kN/m2', 4, 'C.5.2', 126,
  'For exposed wheel house tops the load is not to be taken less than p = 2,5 [kN/m2].',
  ARRAY['wheel house top', 'wheel house tops', 'atap ruang kemudi', 'exposed wheel house', 'exposed wheel house tops', 'beban desain minimum', 'minimum design load', '2.5', '2,5', 'kN/m2'],
  'Sec 4 C.5.2 p126: minimum design load for exposed wheel house tops is 2,5 kN/m2.',
  true, 'bki-rag-qa', now()
);

COMMIT;
