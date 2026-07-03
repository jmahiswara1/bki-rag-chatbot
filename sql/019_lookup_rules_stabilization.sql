-- Migration 019: Stabilization of lookup_rules.
-- Scope (Build 7D, pasca-presentasi):
--   1. CORRECT towing_hook_force: source_quote and page_no were pointing
--      at Sec 27 C.3.5.2 (p.629, test force DIRECTIONS), NOT the formula
--      location Sec 27 C Table 27.1 (p.628). Update both to Table 27.1
--      verbatim; expand value_text to cover the full Table 27.1 ranges
--      so the rule no longer gives the impression of a partial formula
--      that is not what the PDF says.
--   2. NEW hatch_corrosion_addition (parameter nonbulk, 1,0 mm) - target
--      v1 holdout_hatch_tk_nonbulk_id. Verbatim from Table 17.1 (p.350):
--      "Weather deck cargo hatches of all other ship types - Internal
--      structure of double skin hatch covers and closed box girders - 1,0".
--   3. NEW hatch_corrosion_addition (parameter bulk, 2,0 mm) - target v1
--      holdout_hatch_tk_bulk_en. Verbatim from Table 17.1 (p.350):
--      "Weather deck cargo hatches of all bulk carriers, self-unloading
--      bulk carriers, ore carriers and combination carriers - Hatch
--      covers in general - 2,0".
-- Verbatim PDF quotes used; page numbers verified against data/bki_hull_2026.pdf.

BEGIN;

-- 1. towing_hook_force: CORRECT
UPDATE lookup_rules SET
  value_text     = 'Gaya uji PL = 2,0 . T (untuk T kurang dari atau sama dengan 500 kN); PL = T + 500 kN (untuk 500<T kurang dari atau sama dengan 1500 kN); PL = 1,33 . T (untuk T > 1500 kN) (Sec 27 C Tabel 27.1).',
  value_text_id  = 'Gaya uji PL = 2,0 . T (untuk T kurang dari atau sama dengan 500 kN); PL = T + 500 kN (untuk 500<T kurang dari atau sama dengan 1500 kN); PL = 1,33 . T (untuk T > 1500 kN) (Sec 27 C Tabel 27.1).',
  value_text_en  = 'Test force PL = 2.0 . T (for T less than or equal to 500 kN); PL = T + 500 kN (for 500<T less than or equal to 1500 kN); PL = 1.33 . T (for T > 1500 kN) (Sec 27 C Table 27.1).',
  source_quote   = 'T <=500: 2 . T; 500 < T <=1500: T + 500; 1500 < T: 1,33 . T (Table 27.1 p.628).',
  page_no        = 628,
  context_note   = 'Verbatim Table 27.1 (Sec 27 C, p.628). page_no corrected from 629 to 628 (629 is C.3.5.2 test force DIRECTIONS, not the formula).'
WHERE topic = 'towing_hook_force';

-- 2. hatch_corrosion_addition, parameter=nonbulk
INSERT INTO lookup_rules (
  topic, parameter, value_text, value_num, unit,
  section_no, paragraph_id, page_no, source_quote,
  trigger_terms, value_text_en, value_text_id,
  verified, verified_by
) VALUES (
  'hatch_corrosion_addition',
  'nonbulk',
  'tK = 1,0 mm untuk struktur internal penutup palka kulit ganda weather deck cargo hatches selain tipe kapal curah (Sec 17 B Tabel 17.1).',
  1.0,
  'mm',
  17,
  'B',
  350,
  'Weather deck cargo hatches of all other ship types - Internal structure of double skin hatch covers and closed box girders - 1,0 (Table 17.1 p.350).',
  ARRAY[
    'corrosion addition', 'tambahan korosi', 'corrosion addition tK',
    'corrosion addition hatch', 'hatch corrosion',
    'tk palka', 'tk hatch', 'penutup palka'
  ],
  'tK = 1.0 mm for internal structure of double skin hatch covers for non-bulk weather deck cargo hatches (Sec 17 B Table 17.1).',
  'tK = 1,0 mm untuk struktur internal penutup palka kulit ganda weather deck cargo hatches selain tipe kapal curah (Sec 17 B Tabel 17.1).',
  TRUE,
  'build7d'
);

-- 3. hatch_corrosion_addition, parameter=bulk
INSERT INTO lookup_rules (
  topic, parameter, value_text, value_num, unit,
  section_no, paragraph_id, page_no, source_quote,
  trigger_terms, value_text_en, value_text_id,
  verified, verified_by
) VALUES (
  'hatch_corrosion_addition',
  'bulk',
  'tK = 2,0 mm untuk hatch covers in general weather deck cargo hatches tipe kapal curah (bulk carrier) (Sec 17 B Tabel 17.1).',
  2.0,
  'mm',
  17,
  'B',
  350,
  'Weather deck cargo hatches of all bulk carriers, self-unloading bulk carriers, ore carriers and combination carriers - Hatch covers in general - 2,0 (Table 17.1 p.350).',
  ARRAY[
    'corrosion addition', 'tambahan korosi', 'corrosion addition tK',
    'corrosion addition hatch', 'hatch corrosion',
    'tk palka', 'tk hatch', 'penutup palka'
  ],
  'tK = 2.0 mm for hatch covers in general for weather deck cargo hatches of bulk carriers (Sec 17 B Table 17.1).',
  'tK = 2,0 mm untuk hatch covers in general weather deck cargo hatches tipe kapal curah (bulk carrier) (Sec 17 B Tabel 17.1).',
  TRUE,
  'build7d'
);

COMMIT;
