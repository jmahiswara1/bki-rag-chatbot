-- 004_lookup_rules.sql
-- Deterministic single-value rule lookup. See PRD lookup_rules.
-- Idempotent: safe to re-run.

create table if not exists lookup_rules (
    id            bigserial primary key,
    topic         text not null,
    parameter     text,
    value_text    text not null,
    value_num     double precision,
    unit          text,
    section_no    int not null,
    paragraph_id  text,
    page_no       int,
    source_quote  text not null,
    trigger_terms text[] not null,
    context_note  text,
    verified      boolean not null default false,
    verified_by   text,
    verified_at   timestamptz
);

create index if not exists idx_lookup_rules_topic on lookup_rules (topic);
create index if not exists idx_lookup_rules_verified on lookup_rules (verified);
create unique index if not exists uq_lookup_rules_topic_param
    on lookup_rules (topic, coalesce(parameter, ''));

begin;

delete from lookup_rules where topic in (
    'restricted_service_modulus_reduction',
    'forepeak_stringer_spacing',
    'tug_winch_drum_diameter',
    'fire_door_closing_time',
    'bulwark_guardrail_min_height'
);

insert into lookup_rules
    (topic, parameter, value_text, value_num, unit, section_no, paragraph_id, page_no, source_quote, trigger_terms, context_note, verified, verified_by, verified_at)
values
-- json-017: restricted service section modulus reduction (3 rows)
('restricted_service_modulus_reduction', 'P', '5%', 5, '%', 5, 'C.2.1', 147,
  'For ships classed for a restricted range of service, the minimum section modulus may be reduced as follows: P (Restricted Ocean Service): by 5%; L (Coasting Service): by 15%; T (Sheltered Water Service): by 25%.',
  array['restricted service','restricted range of service','section modulus','modulus reduction','reduced','servis terbatas','modulus penampang','dikurangi','restricted ocean','P'],
  null, true, 'PDF Rules for Hull 2026 (mentor-verified)', now()),
('restricted_service_modulus_reduction', 'L', '15%', 15, '%', 5, 'C.2.1', 147,
  'For ships classed for a restricted range of service, the minimum section modulus may be reduced as follows: P (Restricted Ocean Service): by 5%; L (Coasting Service): by 15%; T (Sheltered Water Service): by 25%.',
  array['restricted service','restricted range of service','section modulus','modulus reduction','reduced','servis terbatas','modulus penampang','dikurangi','coasting service','L'],
  null, true, 'PDF Rules for Hull 2026 (mentor-verified)', now()),
('restricted_service_modulus_reduction', 'T', '25%', 25, '%', 5, 'C.2.1', 147,
  'For ships classed for a restricted range of service, the minimum section modulus may be reduced as follows: P (Restricted Ocean Service): by 5%; L (Coasting Service): by 15%; T (Sheltered Water Service): by 25%.',
  array['restricted service','restricted range of service','section modulus','modulus reduction','reduced','servis terbatas','modulus penampang','dikurangi','sheltered water','T'],
  null, true, 'PDF Rules for Hull 2026 (mentor-verified)', now()),
-- text-004: forepeak tiers of beams / stringer spacing (single)
('forepeak_stringer_spacing', null, 'tidak lebih dari 2,6 m (diukur vertikal)', 2.6, 'm', 9, 'A.5.2.1', 228,
  'Forward of the collision bulkhead, tiers of beams (beams at every other frame) generally spaced not more than 2,6 m apart, measured vertically, are to be arranged below the lowest deck within the forepeak.',
  array['forepeak','fore peak','collision bulkhead','tiers of beams','stringer','stringer plate','senta','haluan','ceruk haluan','spacing','jarak','2,6 m'],
  'Aturan forepeak (fwd collision bulkhead). After peak juga 2,6 m (A.5.2.3).', true, 'PDF Rules for Hull 2026 (mentor-verified)', now()),
-- json-003: tug winch drum diameter (single)
('tug_winch_drum_diameter', null, 'tidak kurang dari 14 x diameter towrope', 14, 'x', 27, 'C.5.2.3', 630,
  'The diameter of the winch drum is to be not less than 14 times the towrope diameter.',
  array['winch drum','towrope','tow rope','towline','tug','tunda','derek tunda','winch','diameter drum','14 times'],
  null, true, 'PDF Rules for Hull 2026 (mentor-verified)', now()),
-- json-016: fire door closing time (2 rows)
('fire_door_closing_time', 'hinged', 'tidak lebih dari 40 s dan tidak kurang dari 10 s', 40, 's', 22, 'C.6.6.2', 494,
  'The approximate time of closure for hinged fire doors shall be no more than 40 s and no less than 10 s from the beginning of their movement with the ship in upright position.',
  array['fire door','hinged','time of closure','closing time','pintu kebakaran','engsel','waktu penutupan','40 s'],
  null, true, 'PDF Rules for Hull 2026 (mentor-verified)', now()),
('fire_door_closing_time', 'sliding', '0,1 - 0,2 m/s', null, 'm/s', 22, 'C.6.6.2', 494,
  'The approximate uniform rate of closure for sliding fire doors shall be of no more than 0,2 m/s and no less than 0,1 m/s with the ship in the upright position.',
  array['fire door','sliding','rate of closure','pintu kebakaran','geser','sorong','m/s'],
  null, true, 'PDF Rules for Hull 2026 (mentor-verified)', now()),
-- json-014: bulwark / guard rail minimum height (single)
('bulwark_guardrail_min_height', null, 'tidak kurang dari 1,0 m', 1.0, 'm', 6, 'K.2', 191,
  'The bulwark height or height of guard rail is not to be less than 1,0 m, the lesser height may be approved if adequate protection is provided.',
  array['bulwark','guard rail','guardrail','railing','height','tinggi','pagar pelindung','timber deck cargo','muatan kayu','geladak','1,0 m'],
  'Aturan umum bulwark/guard rail. BKI tidak punya tinggi khusus timber deck cargo; aturan ini yang berlaku.', true, 'PDF Rules for Hull 2026 (mentor-verified)', now());

commit;
