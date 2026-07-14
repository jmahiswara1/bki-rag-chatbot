-- sql/024_lookup_rules_rudder_fatigue.sql
-- Build 17: deterministic lookup rules for rudder force coefficients (c1, c4)
-- and fatigue correction factor (c) to close ID-side generation gap.
-- Idiom: DELETE-then-INSERT for each (topic, parameter) pair.

-- Rudder force coefficient c1 = 0.9 (bulk carriers/tankers >50,000t)
DELETE FROM lookup_rules WHERE topic = 'rudder_force_coefficient' AND parameter = 'c1';

INSERT INTO lookup_rules (topic, parameter, value_text, value_text_en, value_text_id,
    value_num, unit, section_no, paragraph_id, page_no,
    source_quote, trigger_terms, context_note, verified)
VALUES (
    'rudder_force_coefficient',
    'c1',
    'Faktor tipe kapal c1 = 0,9 untuk bulk carrier dan tanker dengan displacement lebih dari 50.000 ton (Sec 14 A.100, p.280). Nilai 1,0 untuk umum, 1,7 untuk tugs dan trawlers.',
    'The ship type factor c1 = 0.9 for bulk carriers and tankers having a displacement of more than 50,000 ton (Sec 14 A.100, p.280). 1.0 in general, 1.7 for tugs and trawlers.',
    'Faktor tipe kapal c1 = 0,9 untuk bulk carrier dan tanker dengan displacement lebih dari 50.000 ton (Sec 14 A.100, p.280).',
    0.9,
    NULL,
    14,
    'A.100',
    280,
    'c1 = factor for the ship type: = 1,0 in general = 0,9 for bulk carriers and tankers having a displacement of more than 50 000 ton = 1,7 for tugs and trawlers',
    ARRAY['rudder force coefficient', 'c1', 'ship type factor', 'faktor tipe kapal', 'bulk carrier', 'tanker', '50000', '50 000'],
    'Ship type factor c1 per Sec 14 A.100. 0.9 for bulk carriers/tankers >50,000t displacement.',
    TRUE
);

-- Rudder force coefficient c4 = 1.5 (outside propeller jet)
DELETE FROM lookup_rules WHERE topic = 'rudder_force_coefficient' AND parameter = 'c4';

INSERT INTO lookup_rules (topic, parameter, value_text, value_text_en, value_text_id,
    value_num, unit, section_no, paragraph_id, page_no,
    source_quote, trigger_terms, context_note, verified)
VALUES (
    'rudder_force_coefficient',
    'c4',
    'Faktor susunan kemudi c4 = 1,5 untuk kemudi di luar semburan baling-baling (propeller jet) (Sec 14 A.4.3, p.281). Nilai 1,0 untuk kemudi di dalam propeller jet.',
    'The rudder arrangement factor c4 = 1.5 for rudders outside the propeller jet (Sec 14 A.4.3, p.281). 1.0 for rudders in the propeller jet.',
    'Faktor susunan kemudi c4 = 1,5 untuk kemudi di luar semburan baling-baling (propeller jet) (Sec 14 A.4.3, p.281).',
    1.5,
    NULL,
    14,
    'A.4.3',
    281,
    'c4 = factor for the rudder arrangement: = 1,0 for rudders in the propeller jet = 1,5 for rudders outside the propeller jet',
    ARRAY['rudder force coefficient', 'c4', 'rudder arrangement', 'faktor susunan kemudi', 'propeller jet', 'di luar', 'outside', 'semburan'],
    'Rudder arrangement factor c4 per Sec 14 A.4.3. 1.5 outside propeller jet, 1.0 inside.',
    TRUE
);

-- Fatigue correction factor c = 0.15 (variable stress welded joints)
DELETE FROM lookup_rules WHERE topic = 'fatigue_correction_factor' AND parameter IS NULL;

INSERT INTO lookup_rules (topic, parameter, value_text, value_text_en, value_text_id,
    value_num, unit, section_no, paragraph_id, page_no,
    source_quote, trigger_terms, context_note, verified)
VALUES (
    'fatigue_correction_factor',
    NULL,
    'Faktor koreksi fatik c = 0,15 untuk sambungan las dengan siklus tegangan variabel (stress range spectrum A atau B) (Sec 20 B.3.2.4, p.446). c = 0 untuk siklus tegangan konstan, c = 0,3 untuk base material tidak dilas.',
    'The fatigue correction factor c = 0.15 for welded joints subjected to variable stress cycles (stress range spectrum A or B) (Sec 20 B.3.2.4, p.446). c = 0 for constant stress cycles, c = 0.3 for unwelded base material.',
    'Faktor koreksi fatik c = 0,15 untuk sambungan las dengan siklus tegangan variabel (Sec 20 B.3.2.4, p.446).',
    0.15,
    NULL,
    20,
    'B.3.2.4',
    446,
    'c = 0 for welded joints subjected to constant stress cycles (stress range spectrum C) = 0,15 welded joints subjected to variable stress cycles (corresponding to stress range spectrum A or B)',
    ARRAY['fatigue correction factor', 'faktor koreksi fatik', 'correction factor c', 'faktor koreksi c', '0.15', '0,15', 'variable stress', 'tegangan variabel', 'welded joints', 'sambungan las'],
    'Fatigue correction factor c per Sec 20 B.3.2.4. 0.15 for welded joints with variable stress cycles.',
    TRUE
);
