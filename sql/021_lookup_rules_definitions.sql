-- Migration 021: Deterministic coverage for two stable-fail v3 targets.

BEGIN;

-- 1. tsc_definition
INSERT INTO lookup_rules (
  topic, parameter, value_text, value_num, unit,
  section_no, paragraph_id, page_no, source_quote,
  trigger_terms, value_text_en, value_text_id,
  verified, verified_by, context_note
) VALUES (
  'tsc_definition',
  NULL,
  'Sarat scantling (TSC) adalah sarat musim panas dalam meter, diukur dari sisi atas lunas (top of keel), atau nilai lebih besar yang ditetapkan sebagai "scantling draught" (Sec 1 H.2.9, p.24).',
  NULL,
  NULL,
  1,
  'H.2.9',
  24,
  'Draught, T, is the summer draught, in metres, measured from top of keel, or a greater value if such a value has been specified as ''scantling draught''.',
  ARRAY['tsc', 'sarat scantling', 'sisi atas lunas', 'top of keel', 'titik ukur sarat'],
  'The scantling draught (TSC) is the summer draught, in metres, measured from top of keel, or a greater value if such a value has been specified as ''scantling draught'' (Sec 1 H.2.9, p.24).',
  'Sarat scantling (TSC) adalah sarat musim panas dalam meter, diukur dari sisi atas lunas (top of keel), atau nilai lebih besar yang ditetapkan sebagai "scantling draught" (Sec 1 H.2.9, p.24).',
  TRUE,
  'engineer',
  'Build 9: deterministic coverage for v3 holdout_tsc_measure_id. Avoids scantling-draught overlap with ship_length_l_definition anchor.'
);

-- 2. aluminium_steel_galvanic_insulation
INSERT INTO lookup_rules (
  topic, parameter, value_text, value_num, unit,
  section_no, paragraph_id, page_no, source_quote,
  trigger_terms, value_text_en, value_text_id,
  verified, verified_by, context_note
) VALUES (
  'aluminium_steel_galvanic_insulation',
  NULL,
  'Untuk mencegah korosi galvanik, material insulasi non-higroskopis harus diaplikasikan di antara baja dan aluminium pada sambungan baut (Sec 2 E.5.2, p.44).',
  NULL,
  NULL,
  2,
  'E.5.2',
  44,
  'To prevent galvanic corrosion a non-hygroscopic insulation material shall be applied between steel and aluminium when a bolted connection is used.',
  ARRAY['aluminium', 'paduan aluminium', 'galvanik', 'korosi galvanik', 'insulasi'],
  'To prevent galvanic corrosion, a non-hygroscopic insulation material shall be applied between steel and aluminium in a bolted connection (Sec 2 E.5.2, p.44).',
  'Untuk mencegah korosi galvanik, material insulasi non-higroskopis harus diaplikasikan di antara baja dan aluminium pada sambungan baut (Sec 2 E.5.2, p.44).',
  TRUE,
  'engineer',
  'Build 9: deterministic coverage for v3 holdout_alu_steel_galvanic_id. Requires aluminium/paduan aluminium trigger to avoid firing on steel-only corrosion queries.'
);

COMMIT;
