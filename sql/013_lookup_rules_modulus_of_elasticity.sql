-- 013_lookup_rules_modulus_of_elasticity.sql
-- Deterministic lookup for Young's modulus E of hull structural steel.
-- Mirrors 008/011/012 style: idempotent, verified-only.
begin;
delete from lookup_rules where topic in (
    'modulus_of_elasticity_steel'
);
insert into lookup_rules
    (topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
     section_no, paragraph_id, page_no, source_quote, trigger_terms, context_note,
     verified, verified_by, verified_at)
values
('modulus_of_elasticity_steel', null,
  'Modulus elastisitas (modulus Young) E untuk baja struktur lambung adalah 2,06 x 10^5 N/mm^2 (setara 206000 N/mm^2), sesuai Sec 3 F. Nilai berbeda berlaku untuk paduan aluminium.',
  'The modulus of elasticity (Young''s modulus) E for hull structural steel is 2.06 x 10^5 N/mm^2 (equivalently 206000 N/mm^2), as defined in Sec 3 F. A different value applies to aluminium alloys.',
  'Modulus elastisitas (modulus Young) E untuk baja struktur lambung adalah 2,06 x 10^5 N/mm^2 (setara 206000 N/mm^2), sesuai Sec 3 F. Nilai berbeda berlaku untuk paduan aluminium.',
  206000.0, 'N/mm^2',
  3, 'F.5.1.6', 85,
  'E = Young''s modulus = 2,06 . 10^5 [N/mm2] for steel',
  array['modulus of elasticity','young modulus','youngs modulus','elastic modulus','modulus elastisitas','modulus young','e for steel'],
  'Discrete value 2,06e5 N/mm^2 (206000 N/mm^2) for hull structural steel per Sec 3 F.5.1.6; aluminium uses different value.',
  true, 'akashi', now());
commit;
  array['modulus of elasticity','young modulus','youngs modulus','elastic modulus','modulus elastisitas','modulus young','e for steel','elasticity'],
  array['modulus of elasticity','young modulus','youngs modulus','elastic modulus','modulus elastisitas','modulus young','e for steel','elasticity','elastisitas','young'],
