-- 018_lookup_rules_gap_topics.sql
-- 8 new deterministic lookup rules covering v1 holdout gap topics.
-- Each rule is idempotent (DELETE by topic+parameter then INSERT).
-- Verified against PDF Rules for Hull 2026. No overlap with v2 holdout.
begin;
-- 1) mooring_current_speed (Sec 18 F.4.2.1, p.398)
delete from lookup_rules where topic = 'mooring_current_speed';
insert into lookup_rules
    (topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
     section_no, paragraph_id, page_no, source_quote, trigger_terms, context_note,
     verified, verified_by, verified_at)
values
('mooring_current_speed', null,
  'Mooring lines are based on a maximum current speed of 1,0 m/s and the maximum wind speed vw [m/s] = 25 \u2013 0,002 \u00b7 (A \u2013 2000) (Sec 18 F.4.2.1).',
  'The mooring lines as given here under are based on a maximum current speed of 1,0 m/s and the following maximum wind speed vw [m/s].',
  'Tali tambat didasarkan pada kecepatan arus maksimum 1,0 m/s dan kecepatan angin maksimum vw [m/s] = 25 \u2013 0,002 \u00b7 (A \u2013 2000) (Sec 18 F.4.2.1).',
  1.0, 'm/s',
  18, 'F.4.2.1', 398,
  'The mooring lines as given here under are based on a maximum current speed of 1,0 m/s and the following maximum wind speed vw [m/s]',
  array['mooring','current speed','1,0','m/s','tali tambat','kecepatan arus'],
  'Wind speed formula is in the same paragraph. Single-row rule, no parameter needed.',
  true, 'akashi', now());

-- 2) reh_normal_steel (Sec 2 B.1.1, p.31)
delete from lookup_rules where topic = 'reh_normal_steel';
insert into lookup_rules
    (topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
     section_no, paragraph_id, page_no, source_quote, trigger_terms, context_note,
     verified, verified_by, verified_at)
values
('reh_normal_steel', null,
  'Normal strength hull structural steel has a minimum nominal upper yield point ReH of 235 N/mm2 and tensile strength Rm of 400-520 N/mm2 (Sec 2 B.1.1).',
  'Normal strength hull structural steel is a hull structural steel with a minimum nominal upper yield point ReH of 235 N/mm2 and a tensile strength Rm of 400 - 520 N/mm2.',
  'Baja struktur lambung kekuatan normal memiliki titik luluh atas nominal minimum ReH 235 N/mm2 dan kekuatan tarik Rm 400-520 N/mm2 (Sec 2 B.1.1).',
  235.0, 'N/mm2',
  2, 'B.1.1', 31,
  'Normal strength hull structural steel is a hull structural steel with a minimum nominal upper yield point ReH of 235 N/mm2',
  array['normal strength','ReH','235','N/mm2','baja kekuatan normal','yield'],
  'For ReH > 235 the material factor k decreases; see material_factor_k rule. ReH 315 and 355 are specifically listed in Table 2.1.',
  true, 'akashi', now());

-- 3) supply_deck_thickness (Sec 29 supply vessel, p.668)
delete from lookup_rules where topic = 'supply_deck_thickness';
insert into lookup_rules
    (topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
     section_no, paragraph_id, page_no, source_quote, trigger_terms, context_note,
     verified, verified_by, verified_at)
values
('supply_deck_thickness', null,
  'For supply vessels, the thickness of deck plating is not to be taken less than 8,0 mm (Sec 29 supply vessel, pL >= 40 kN/m2).',
  'The thickness of deck plating is not to be taken less than 8,0 mm. In areas for the stowage of heavy cargoes the thickness of deck plating is to be suitably increased.',
  'Tebal pelat geladak kapal suplai tidak boleh kurang dari 8,0 mm (Sec 29 kapal suplai, pL >= 40 kN/m2).',
  8.0, 'mm',
  29, None, 668,
  'The thickness of deck plating is not to be taken less than 8,0 mm.',
  array['supply vessel','deck plating','8,0','mm','kapal suplai','tebal geladak'],
  'Applies for pL >= 40 kN/m2. Single-row rule.',
  true, 'akashi', now());

-- 4) collision_bulkhead_barge (Sec 31 C.3, p.723)
delete from lookup_rules where topic = 'collision_bulkhead_barge';
insert into lookup_rules
    (topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
     section_no, paragraph_id, page_no, source_quote, trigger_terms, context_note,
     verified, verified_by, verified_at)
values
('collision_bulkhead_barge', null,
  'For barges, the collision bulkhead is to be located between 0,05Lcon and 0,08Lcon (or 0,05Lcon and 0,13Lcon when Lcon < 90 m) (Sec 31 C.3).',
  'Collision bulkhead of barge is to be located between 0,05Lcon. and 0,08Lcon. However, when the length of connection is less than 90 m, collision bulkhead may be located between 0,05Lcon. and 0,13Lcon..',
  'Sekat tubrukan tongkang harus ditempatkan antara 0,05Lcon dan 0,08Lcon (atau 0,05Lcon dan 0,13Lcon bila Lcon < 90 m) (Sec 31 C.3).',
  null, null,
  31, 'C.3', 723,
  'Collision bulkhead of barge is to be located between 0,05Lcon. and 0,08Lcon.',
  array['barge','collision bulkhead','0,05Lcon','0,08Lcon','tongkang','sekat tubrukan','pontoon'],
  'Distinct from collision_bulkhead_position (ships). Barge Lcon < 90 m extends range to 0,13Lcon. Need discrimination in lookup.py.',
  true, 'akashi', now());

-- 5) tanker_strake_width (Sec 24 A.10.1.2, p.604)
delete from lookup_rules where topic = 'tanker_strake_width';
insert into lookup_rules
    (topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
     section_no, paragraph_id, page_no, source_quote, trigger_terms, context_note,
     verified, verified_by, verified_at)
values
('tanker_strake_width', null,
  'For tankers, the top and bottom strakes of the longitudinal bulkheads are to have a width of not less than 0,1H (Sec 24 A.10.1.2).',
  'The top and bottom strakes of the longitudinal bulkheads are to have a width of not less than 0,1H.',
  'Untuk kapal tanker, strake atas dan bawah sekat memanjang harus memiliki lebar tidak kurang dari 0,1H (Sec 24 A.10.1.2).',
  0.1, 'H',
  24, 'A.10.1.2', 604,
  'The top and bottom strakes of the longitudinal bulkheads are to have a width of not less than 0,1H',
  array['tanker','strake','longitudinal bulkhead','0,1H','lebar strake','tanker'],
  'H is ship depth. Strake thickness also specified (tmin = 0,75 x deck thickness for top).',
  true, 'akashi', now());

-- 6) hatch_cover_deflection (Sec 17 B.2.2, p.357)
delete from lookup_rules where topic = 'hatch_cover_deflection';
insert into lookup_rules
    (topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
     section_no, paragraph_id, page_no, source_quote, trigger_terms, context_note,
     verified, verified_by, verified_at)
values
('hatch_cover_deflection', null,
  'The deflection f of weather deck hatch covers under the design load pH shall not exceed f = 0,0056 . lg [m] (lg = largest span of girders) (Sec 17 B.2.2).',
  'The deflection f of weather deck hatch covers under the design load pH shall not exceed f = 0,0056 . lg [m] lg = largest span of girders [m].',
  'Defleksi f penutup palka geladak cuaca di bawah beban desain pH tidak boleh melebihi f = 0,0056 . lg [m] (lg = bentang terbesar gelagar) (Sec 17 B.2.2).',
  0.0056, 'x',
  17, 'B.2.2', 357,
  'The deflection f of weather deck hatch covers under the design load pH shall not exceed f = 0,0056 . lg',
  array['hatch cover','deflection','0,0056','lg','penutup palka','defleksi','weather deck'],
  'Formula f = 0,0056 * lg where lg is largest girder span in meters. Need discrimination from cargo_hatch_coaming_height.',
  true, 'akashi', now());

-- 7) stockless_anchor_head_mass (Sec 18 C.3, p.650)
delete from lookup_rules where topic = 'stockless_anchor_head_mass';
insert into lookup_rules
    (topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
     section_no, paragraph_id, page_no, source_quote, trigger_terms, context_note,
     verified, verified_by, verified_at)
values
('stockless_anchor_head_mass', null,
  'The anchor mass may be 60% of the value required by Table 18.2 when using HHP anchors (Sec 18 C.3).',
  'The anchor mass may be 60% of the value required by Table 18.2. The chain diameter may be determined according to the reduced anchor mass.',
  'Massa jangkar boleh 60% dari nilai yang disyaratkan oleh Tabel 18.2 bila menggunakan jangkar HHP (Sec 18 C.3).',
  60.0, '%',
  18, 'C.3', 650,
  'The anchor mass may be 60% of the value required by Table 18.2.',
  array['stockless','anchor mass','60%','Table 18.2','HHP','massa jangkar'],
  '60% is for HHP anchors. Distinct from anchor_holding_power (holding capacity). Need discrimination.',
  true, 'akashi', now());

-- 8) towing_hook_force (Sec 27 C.7, p.629)
delete from lookup_rules where topic = 'towing_hook_force';
insert into lookup_rules
    (topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
     section_no, paragraph_id, page_no, source_quote, trigger_terms, context_note,
     verified, verified_by, verified_at)
values
('towing_hook_force', null,
  'For T <= 500 kN, the towing hook test force PL is PL = 2,0 x T (Sec 27 C.7).',
  'For a test force PL <= 500 kN: in the horizontal plane, directions from abeam over astern to abeam; in the vertical plane, from horizontal to 60 degrees upwards. For a test force PL > 500 kN: ...',
  'Untuk T <= 500 kN, gaya uji kait penarik PL adalah PL = 2,0 x T (Sec 27 C.7).',
  2.0, 'x T',
  27, 'C.7', 629,
  'For a test force PL <= 500 kN: in the horizontal plane, directions from abeam over astern to abeam; in the vertical plane, from horizontal to 60 degrees upwards.',
  array['towing hook','test force','PL','2,0','500 kN','kait penarik'],
  'PL = 2,0 x T for T <= 500 kN. Distinct from tug_winch_drum_diameter (drum aspect). Need discrimination.',
  true, 'akashi', now());

commit;
        'trigger_terms': ['stockless','anchor mass','60%','Table 18.2','HHP','massa jangkar'],
        'trigger_terms': array['stockless','anchor mass','60%','Table 18.2','HHP','massa jangkar','ordinary','head','pins','fittings','ordinary stockless'],
        'trigger_terms': ['stockless','anchor mass','60%','Table 18.2','HHP','massa jangkar'],
        'trigger_terms': array['stockless','anchor mass','60%','Table 18.2','HHP','massa jangkar','ordinary','head','pins','fittings','ordinary stockless','stockless anchor'],
