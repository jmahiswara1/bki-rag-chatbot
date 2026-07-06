-- Migration 020: Hatch coverage lookup rules (Build 8).
-- Adds deterministic coverage for v3 single_skin_hatch and access_hatch_width.
-- Both verified verbatim against data/bki_hull_2026.pdf via fitz.

BEGIN;

-- 1. single-skin hatch cover minimum plate thickness
--    Sec 17 B.5.1.1 (Top plating) p.363:
--    "t = 6,5 . a + tK [mm] If project cargo is intended to be carried on
--    a hatch cover tmin = 5,0 + tK [mm]."
INSERT INTO lookup_rules (
  topic, parameter, value_text, value_num, unit,
  section_no, paragraph_id, page_no, source_quote,
  trigger_terms, value_text_en, value_text_id,
  verified, verified_by
) VALUES (
  'hatch_min_thickness_single_skin',
  NULL,
  'Single-skin hatch cover: t = 6,5 . a + tK [mm]; tmin = 5,0 + tK [mm] for project cargo (Sec 17 B.5.1.1, p.363).',
  6.5,
  'mm',
  17,
  'B.5.1.1',
  363,
  't = 6,5 . a + tK [mm] If project cargo is intended to be carried on a hatch cover tmin = 5,0 + tK [mm]',
  ARRAY[
    'palka kulit tunggal',
    'pelat penutup palka kulit tunggal',
    'single skin',
    'single-skin'
  ],
  'Single-skin hatch cover: t = 6.5 . a + tK [mm]; tmin = 5.0 + tK [mm] for project cargo (Sec 17 B.5.1.1, p.363).',
  'Pelat penutup palka kulit tunggal (single-skin hatch cover): t = 6,5 . a + tK [mm]; tmin = 5,0 + tK [mm] untuk project cargo (Sec 17 B.5.1.1, p.363).',
  TRUE,
  'engineer'
);

-- 2. Access hatchway minimum clear width
--    Sec 17 A.1.10 p.375:
--    "Access hatchways shall have a clear width of at least 600 x 600 mm."
INSERT INTO lookup_rules (
  topic, parameter, value_text, value_num, unit,
  section_no, paragraph_id, page_no, source_quote,
  trigger_terms, value_text_en, value_text_id,
  verified, verified_by
) VALUES (
  'access_hatch_min_width',
  NULL,
  'Access hatchways shall have a clear width of at least 600 x 600 mm (Sec 17 A.1.10, p.375).',
  600,
  'mm',
  17,
  'A.1.10',
  375,
  'Access hatchways shall have a clear width of at least 600 x 600 mm.',
  ARRAY[
    'bukaan palka akses',
    'palka akses',
    'access hatchway',
    'access hatch',
    'clear width'
  ],
  'Access hatchways shall have a clear width of at least 600 x 600 mm (Sec 17 A.1.10, p.375).',
  'Bukaan palka akses (access hatchways) harus memiliki clear width minimum 600 x 600 mm (Sec 17 A.1.10, p.375).',
  TRUE,
  'engineer'
);

COMMIT;
