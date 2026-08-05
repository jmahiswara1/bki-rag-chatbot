-- 031_lookup_rules_holdout_definitions.sql
-- Deterministic coverage for held-out definition and permission questions.

BEGIN;

DELETE FROM lookup_rules WHERE topic IN (
  'weather_deck_definition',
  'doubling_plate_tank_permission'
);

INSERT INTO lookup_rules (
  topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
  section_no, paragraph_id, page_no, source_quote,
  trigger_terms, context_note,
  verified, verified_by, verified_at
) VALUES
(
  'weather_deck_definition', NULL,
  'Semua geladak bebas dan bagian geladak yang terpapar laut didefinisikan sebagai geladak cuaca.',
  'All free decks and parts of decks exposed to the sea are defined as weather deck.',
  'Semua geladak bebas dan bagian geladak yang terpapar laut didefinisikan sebagai geladak cuaca.',
  NULL, NULL, 7, 'C.1.5', 203,
  'All free decks and parts of decks exposed to the sea are defined as weather deck.',
  ARRAY['weather deck', 'geladak cuaca', 'free decks', 'free deck', 'exposed to the sea', 'terpapar laut'],
  'Sec 7 C.1.5: definition of weather deck.',
  true, 'bki-rag-eval', now()
),
(
  'doubling_plate_tank_permission', NULL,
  'Doubling plates tidak diizinkan dipasang di dalam tangki untuk muatan cairan yang mudah terbakar, kecuali pelat collar dan doubling kecil untuk fittings seperti pemanas tangki atau fittings tangga.',
  'Doubling plates are not permitted in tanks for flammable liquids, except collar plates and small doublings for fittings such as tank heating fittings or ladder fittings.',
  'Pelat ganda tidak diizinkan dipasang di dalam tangki untuk muatan cairan yang mudah terbakar, kecuali pelat collar dan pelat ganda kecil untuk fittings seperti pemanas tangki atau fittings tangga.',
  NULL, NULL, 19, 'A.3.2.6', 592,
  'Doubling plates are not permitted in tanks for flammable liquids, except collar plates and small doublings for fittings like tank heating fittings or fitting for ladder.',
  ARRAY['doubling plates', 'doubling plate', 'pelat ganda', 'flammable liquid', 'flammable liquids', 'muatan cairan mudah terbakar'],
  'Sec 19 A.3.2.6: restriction and exceptions for doubling plates in tanks.',
  true, 'bki-rag-eval', now()
);

COMMIT;
