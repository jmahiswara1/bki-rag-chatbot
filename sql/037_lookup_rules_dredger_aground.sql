-- 037_lookup_rules_dredger_aground.sql
-- Dredgers operating while aground are governed by Sec 32 H.2.6.1: the
-- spacing of bottom transverses is NOT to exceed 1,8 m. This is stricter
-- than the general H.2.1 rule (3,6 m). Add a dedicated rule so aground
-- queries resolve to 1,8 m and the general rule is excluded for them.

BEGIN;

DELETE FROM lookup_rules WHERE topic = 'dredger_bottom_transverse_spacing_aground';

INSERT INTO lookup_rules (
  topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
  section_no, paragraph_id, page_no, source_quote,
  trigger_terms, context_note,
  verified, verified_by, verified_at
) VALUES (
  'dredger_bottom_transverse_spacing_aground',
  NULL,
  'Pada kapal keruk dengan dasar tunggal berkonstruksi memanjang yang dirancang atau diperkirakan akan beroperasi dalam kondisi kandas (aground), spasi transverses dasar tidak boleh melebihi 1,8 m.',
  'For single-bottom longitudinally framed dredgers intended or expected to operate while aground, the spacing of the bottom transverses is not to exceed 1,8 m.',
  'Pada kapal keruk dengan dasar tunggal berkonstruksi memanjang yang dirancang atau diperkirakan akan beroperasi dalam kondisi kandas (aground), spasi transverses dasar tidak boleh melebihi 1,8 m.',
  1.8, 'm', 32, 'H.2.6.1', 660,
  'The spacing of the bottom transverses as per 2.1 is not to exceed 1,8 m.',
  ARRAY['dredger', 'dredgers', 'bottom transverses', 'transverses dasar', 'single bottom', 'dasar tunggal', 'aground', 'kandas', '1.8', '1,8'],
  'Sec 32 H.2.6.1: aground-operation spacing (1,8 m). Distinct from the general H.2.1 rule (3,6 m).',
  true, 'bki-rag-qa', now()
);

COMMIT;
