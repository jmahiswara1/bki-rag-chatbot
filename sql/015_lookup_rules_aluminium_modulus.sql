-- 015_lookup_rules_aluminium_modulus.sql
-- Refactor modulus_of_elasticity to (topic, parameter) split: steel vs aluminium.
-- Mirrors 011/012/013/014 style: idempotent, verified-only.
begin;
-- 1) Remove the old single-row steel entry (topic=modulus_of_elasticity_steel).
delete from lookup_rules where topic = 'modulus_of_elasticity_steel';
-- 2) Insert steel row with parameter='steel'.
insert into lookup_rules
    (topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
     section_no, paragraph_id, page_no, source_quote, trigger_terms, context_note,
     verified, verified_by, verified_at)
values
('modulus_of_elasticity', 'steel',
  'Modulus elastisitas (modulus Young) E untuk baja struktur lambung adalah 2,06 x 10^5 N/mm^2 (setara 206000 N/mm^2), sesuai Sec 3 F. Nilai berbeda berlaku untuk paduan aluminium.',
  'The modulus of elasticity (Young''s modulus) E for hull structural steel is 2.06 x 10^5 N/mm^2 (equivalently 206000 N/mm^2), as defined in Sec 3 F. A different value applies to aluminium alloys.',
  'Modulus elastisitas (modulus Young) E untuk baja struktur lambung adalah 2,06 x 10^5 N/mm^2 (setara 206000 N/mm^2), sesuai Sec 3 F. Nilai berbeda berlaku untuk paduan aluminium.',
  206000.0, 'N/mm^2',
  3, 'F.5.1.6', 85,
  'E = Young''s modulus = 2,06 . 10^5 [N/mm2] for steel',
  array['modulus of elasticity','young''s modulus','modulus elastisitas','elastic modulus','elasticity','elastisitas','young','steel','baja'],
  'Discrete value 2,06e5 N/mm^2 (206000 N/mm^2) for hull structural steel per Sec 3 F.5.1.6; aluminium uses different value.',
  true, 'akashi', now());
-- 3) Insert aluminium row with parameter='aluminium'.
insert into lookup_rules
    (topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
     section_no, paragraph_no, page_no, source_quote, trigger_terms, context_note,
     verified, verified_by, verified_at)
values
('modulus_of_elasticity', 'aluminium',
  'Untuk paduan aluminium, modulus elastisitas (Young) E adalah 70000 N/mm2 (kecuali disepakati lain).',
  'For aluminium alloys, the Young''s modulus (E) is 70000 N/mm2 (unless otherwise agreed).',
  'Untuk paduan aluminium, modulus elastisitas (Young) E adalah 70000 N/mm2 (kecuali disepakati lain).',
  70000, 'N/mm^2',
  2, 'D.1.7', 43,
  'the Young''s modulus for aluminium alloys (E) is equal to 70000 N/mm2',
  array['modulus of elasticity','young''s modulus','modulus elastisitas','elastic modulus','elasticity','elastisitas','young','aluminium','aluminum','alumunium','paduan aluminium','aluminium alloy','70000'],
  'Discrete value 70000 N/mm^2 for aluminium alloys per Sec 2 D.1.7; applies unless otherwise agreed.',
  true, 'akashi', now());
commit;
