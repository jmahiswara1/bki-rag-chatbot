-- Migration 022: Deterministic lookup coverage for two golden anchor mass facts.
-- VHHP anchor max mass (1500 kg) and HHP bower anchor mass reduction (75% of stockless).
-- Both from Section 18. Converts rules_qa generation entries to deterministic lookup.

BEGIN;

-- 1. anchor_vhhp_max_mass (Sec 18 C.5, p.389)
DELETE FROM lookup_rules WHERE topic = 'anchor_vhhp_max_mass';
INSERT INTO lookup_rules (
  topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
  section_no, paragraph_id, page_no, source_quote,
  trigger_terms, context_note,
  verified, verified_by
) VALUES (
  'anchor_vhhp_max_mass',
  NULL,
  'Massa jangkar VHHP umumnya tidak boleh melebihi 1500 kg (Sec 18 C.5, p.389).',
  'The VHHP anchor mass is generally not to exceed 1500 kg (Sec 18 C.5, p.389).',
  'Massa jangkar VHHP umumnya tidak boleh melebihi 1500 kg (Sec 18 C.5, p.389).',
  1500, 'kg',
  18,
  'C.5',
  389,
  'The VHHP anchor mass is generally not to exceed 1500 kg.',
  ARRAY['VHHP', 'maximum mass', 'massa maksimum', 'maksimum', 'mass', 'massa', 'massa jangkar', 'anchor mass', '1500 kg', 'maximum'],
  'Build 13: deterministic coverage for golden rules_anchor_vhhp_mass_id. Distinct from anchor_holding_power (holding capacity) via EXCLUDE_TERMS.',
  TRUE,
  'engineer'
);

-- 2. anchor_hhp_mass_reduction (Sec 18 C.4, p.389)
DELETE FROM lookup_rules WHERE topic = 'anchor_hhp_mass_reduction';
INSERT INTO lookup_rules (
  topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
  section_no, paragraph_id, page_no, source_quote,
  trigger_terms, context_note,
  verified, verified_by
) VALUES (
  'anchor_hhp_mass_reduction',
  NULL,
  'Bila jangkar HHP digunakan sebagai jangkar bower, massa tiap jangkar boleh 75% dari massa yang disyaratkan untuk jangkar bower stockless biasa di Tabel 18.2 (Sec 18 C.4, p.389).',
  'When HHP anchors of proven holding ability are used as bower anchors, the mass of each anchor may be 75% of the mass required for ordinary stockless bower anchors in Table 18.2 (Sec 18 C.4, p.389).',
  'Bila jangkar HHP digunakan sebagai jangkar bower, massa tiap jangkar boleh 75% dari massa yang disyaratkan untuk jangkar bower stockless biasa di Tabel 18.2 (Sec 18 C.4, p.389).',
  75, '%',
  18,
  'C.4',
  389,
  'When special type of anchors designated ''high holding power anchor'' of proven superior holding ability are used as bower anchors, the mass of each anchor may be 75% of the mass required for ordinary stockless bower anchors in the Table 18.2.',
  ARRAY['HHP', '75%', 'mass reduction', 'reduksi massa', 'bower', 'stockless', 'mass', 'massa', 'reduced', 'reduksi', 'percentage', 'persen', 'massa jangkar', 'anchor mass'],
  'Build 13: deterministic coverage for golden rules_anchor_hhp_reduce_en. Distinct from stockless_anchor_head_mass (60% heads) and anchor_holding_power (holding capacity) via EXCLUDE_TERMS and anchor gate.',
  TRUE,
  'engineer'
);

COMMIT;
