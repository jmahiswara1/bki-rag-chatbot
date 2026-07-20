BEGIN;

DELETE FROM lookup_rules WHERE topic = 'towing_winch_holding_capacity';
INSERT INTO lookup_rules (
  topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
  section_no, paragraph_id, page_no, source_quote,
  trigger_terms, context_note,
  verified, verified_by, verified_at
) VALUES (
  'towing_winch_holding_capacity',
  NULL,
  'Kapasitas penahan (holding capacity) dari towing winch (tali tunda pada lapisan pertama) harus 80% dari beban putus minimum Fmin tali tunda.',
  'The holding capacity of the towing winch (towrope in the first layer) shall correspond to 80% of the minimum breaking load Fmin of the towrope.',
  'Kapasitas penahan (holding capacity) dari towing winch (tali tunda pada lapisan pertama) harus 80% dari beban putus minimum Fmin tali tunda.',
  80,
  '% Fmin',
  27,
  'C.5.3.1',
  630,
  'The holding capacity of the towing winch (towrope in the first layer) shall correspond to 80% of the minimum breaking load Fmin of the towrope.',
  ARRAY['towing winch', 'holding capacity', 'kapasitas penahan', 'winch tunda', 'holding', 'capacity', 'kapasitas', 'penahan', 'towing', 'winch', 'towrope', 'tali tunda', 'first layer', 'lapisan pertama'],
  'Build 36 gap coverage. Distinct from tug_winch_drum_diameter.',
  true,
  'akashi',
  now()
);

COMMIT;