-- 016_lookup_rules_outfit_misc.sql
-- Add 4 verified lookup rules: cargo hatch coaming, ventilator coaming,
-- aluminium Poisson's ratio, collision bulkhead position.
-- Mirrors 011/012/013/014/015 style: idempotent (DELETE+INSERT), verified-only.
begin;
-- Ensure idempotency: remove existing rows for these topics if present.
delete from lookup_rules
  where topic in (
    'cargo_hatch_coaming_height',
    'ventilator_coaming_height',
    'poisson_ratio_aluminium',
    'collision_bulkhead_position'
  );

-- 1) cargo_hatch_coaming_height (Sec 17 A.2.2, p.347)
insert into lookup_rules
    (topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
     section_no, paragraph_id, page_no, source_quote, trigger_terms, context_note,
     verified, verified_by, verified_at)
values
('cargo_hatch_coaming_height', null,
  'Tinggi minimum coaming palka kargo di atas geladak: 600 mm untuk position 1 dan 450 mm untuk position 2 (Sec 17 A.2.2).',
  'The minimum height of cargo hatch coamings above the deck is: 600 mm in position 1 and 450 mm in position 2 (Sec 17 A.2.2).',
  'Tinggi minimum coaming palka kargo di atas geladak: 600 mm untuk position 1 dan 450 mm untuk position 2 (Sec 17 A.2.2).',
  null, null,
  17, 'A.2.2', 347,
  'Hatchways are to have coamings, the minimum height of which above the deck is to be as follows: In position 1: 600 mm; In position 2: 450 mm',
  array['hatch coaming','cargo hatch','coaming height','hatchway coaming','coaming palka','palka kargo','tutup palka','tinggi coaming','600 mm','450 mm','hatch cover'],
  -- Note: 'tutup palka' and 'hatch cover' intentionally EXCLUDED from triggers
  -- (removed in a follow-up update) because they caused false-fire on hose-test
  -- queries. See scripts/_fix_anchors.py.
  'Two-position rule (position 1 vs position 2 per Sec 1 H.6.7). Single row covers both positions to avoid misfire.',
  true, 'akashi', now());

-- 2) ventilator_coaming_height (Sec 21 G.1.1, p.475)
insert into lookup_rules
    (topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
     section_no, paragraph_id, page_no, source_quote, trigger_terms, context_note,
     verified, verified_by, verified_at)
values
('ventilator_coaming_height', null,
  'Tinggi minimum coaming ventilator di atas geladak: paling sedikit 900 mm untuk position 1 dan paling sedikit 760 mm untuk position 2 (Sec 21 G.1.1).',
  'The minimum height of ventilator coamings above the deck is: at least 900 mm in position 1 and at least 760 mm in position 2 (Sec 21 G.1.1).',
  'Tinggi minimum coaming ventilator di atas geladak: paling sedikit 900 mm untuk position 1 dan paling sedikit 760 mm untuk position 2 (Sec 21 G.1.1).',
  null, null,
  21, 'G.1.1', 475,
  'Ventilators in position 1 are to have coamings of a height of at least 900 mm above the deck; in position 2 the coamings are to be of at least 760 mm above the deck.',
  array['ventilator coaming','coaming ventilator','ventilator','coaming height','tinggi coaming','900 mm','760 mm'],
  'Two-position rule. Verified position-2 = 760 mm from PDF p.475 (PDF text extraction drops the "2" in "in position 2" but the 760 mm value is unambiguous per the rule).',
  true, 'akashi', now());

-- 3) poisson_ratio_aluminium (Sec 2 D.1.7, p.43)
insert into lookup_rules
    (topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
     section_no, paragraph_id, page_no, source_quote, trigger_terms, context_note,
     verified, verified_by, verified_at)
values
('poisson_ratio_aluminium', null,
  'Untuk paduan aluminium, rasio Poisson (nu) adalah 0,33. Modulus Young (E) untuk paduan aluminium adalah 70000 N/mm2 (kecuali disepakati lain) (Sec 2 D.1.7).',
  'For aluminium alloys, the Poisson''s ratio (nu) is 0.33. The Young''s modulus (E) for aluminium alloys is 70000 N/mm2 (unless otherwise agreed) (Sec 2 D.1.7).',
  'Untuk paduan aluminium, rasio Poisson (nu) adalah 0,33. Modulus Young (E) untuk paduan aluminium adalah 70000 N/mm2 (kecuali disepakati lain) (Sec 2 D.1.7).',
  0.33, null,
  2, 'D.1.7', 43,
  'the Young''s modulus for aluminium alloys (E) is equal to 70000 N/mm2 and the Poisson''s ratio (nu) equal to 0,33.',
  array['poisson',"poisson's ratio",'poisson ratio','rasio poisson','aluminium','aluminum','alumunium','paduan aluminium','aluminium alloy','0,33','0.33','0, 33'],
  'Applies to aluminium alloys only; the document does not state Poisson''s ratio for steel explicitly. Verified from PDF p.43 D.1.7 (chunker cut at D.1.2 and omitted this paragraph).',
  true, 'akashi', now());

-- 4) collision_bulkhead_position (Sec 11 A.2.1.1, p.247)
insert into lookup_rules
    (topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
     section_no, paragraph_id, page_no, source_quote, trigger_terms, context_note,
     verified, verified_by, verified_at)
values
('collision_bulkhead_position', null,
  'Sekat tubrukan harus ditempatkan pada jarak dari forward perpendicular tidak kurang dari 0,05Lc atau 10 m (yang lebih kecil), dan tidak lebih dari 0,08Lc atau 0,05Lc + 3,0 m (yang lebih besar) (Sec 11 A.2.1.1).',
  'A collision bulkhead shall be located at a distance from the forward perpendicular of not less than 0.05Lc or 10 m (whichever is the less), and not more than 0.08Lc or 0.05Lc + 3.0 m (whichever is the greater) (Sec 11 A.2.1.1).',
  'Sekat tubrukan harus ditempatkan pada jarak dari forward perpendicular tidak kurang dari 0,05Lc atau 10 m (yang lebih kecil), dan tidak lebih dari 0,08Lc atau 0,05Lc + 3,0 m (yang lebih besar) (Sec 11 A.2.1.1).',
  null, null,
  11, 'A.2.1.1', 247,
  'A collision bulkhead shall be located at a distance from the forward perpendicular of not less than 0,05Lc or 10 m, whichever is the less, and ... not more than 0,08Lc or 0,05Lc + 3,0 m, whichever is the greater.',
  array['collision bulkhead','sekat tubrukan','sekat tabrakan','forward perpendicular','0,05Lc','0,08Lc','0.05Lc','0.08Lc','10 m','3,0 m','3.0 m','Lc'],
  'Range rule (lower bound = min(0.05Lc, 10m); upper bound = max(0.08Lc, 0.05Lc + 3.0m)). Discrimination from forepeak_stringer_spacing required.',
  true, 'akashi', now());

commit;
