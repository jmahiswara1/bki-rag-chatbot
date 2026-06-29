-- 012_lookup_rules_material_factor_k.sql
-- Deterministic lookup for material factor k (Table 2.1, Sec 2 B.2).
-- Mirrors 008/011 style: idempotent, verified-only.
begin;
delete from lookup_rules where topic in (
    'material_factor_k'
);
insert into lookup_rules
    (topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
     section_no, paragraph_id, page_no, source_quote, trigger_terms, context_note,
     verified, verified_by, verified_at)
values
('material_factor_k', null,
  'Faktor material k bergantung pada tegangan luluh atas nominal baja ReH (Table 2.1, Sec 2 B): k = 1,0 untuk baja kekuatan normal (ReH = 235 N/mm^2); 0,78 pada 315; 0,72 pada 355; 0,66 pada 390 (0,68 bila tanpa fatigue assessment); dan 0,62 pada 460. Untuk nilai luluh lain antara 235 dan 390 (selain 315 dan 355), k = 295/(ReH + 60) (Sec 2 B.2).',
  'The material factor k depends on the steel nominal upper yield strength ReH (Table 2.1, Sec 2 B): k = 1.0 for normal-strength steel (ReH = 235 N/mm^2), 0.78 at 315, 0.72 at 355, 0.66 at 390 (0.68 if no fatigue assessment is performed), and 0.62 at 460. For other yields between 235 and 390 (excluding 315 and 355), k = 295/(ReH + 60) (Sec 2 B.2).',
  'Faktor material k bergantung pada tegangan luluh atas nominal baja ReH (Table 2.1, Sec 2 B): k = 1,0 untuk baja kekuatan normal (ReH = 235 N/mm^2); 0,78 pada 315; 0,72 pada 355; 0,66 pada 390 (0,68 bila tanpa fatigue assessment); dan 0,62 pada 460. Untuk nilai luluh lain antara 235 dan 390 (selain 315 dan 355), k = 295/(ReH + 60) (Sec 2 B.2).',
  1.0, null,
  2, 'B.2', 32,
  'The material factor k in the formulae of the following Sections is to be taken 1,0 for normal strength hull structural steel.',
  array['material factor','faktor material','material factor k','faktor material k','reh','tegangan luluh','yield strength'],
  'Discrete table per ReH (Table 2.1): 235->1,0; 315->0,78; 355->0,72; 390->0,66 (0,68 without fatigue assessment); 460->0,62. Intermediate: k=295/(ReH+60).',
  true, 'akashi', now());
commit;
