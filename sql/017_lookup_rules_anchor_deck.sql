-- 017_lookup_rules_anchor_deck.sql
-- Convert 2 flaky rules_qa facts (HHP/VHHP holding power) + add 1 new fact
-- (accommodation deck min thickness, Sec 29 E.2) to deterministic lookup_rules.
-- Idempotent (DELETE+INSERT like 016), verified-only.
begin;
delete from lookup_rules
  where topic in (
    'anchor_holding_power',
    'accommodation_deck_min_thickness'
  );

-- 1) anchor_holding_power, parameter='hhp' (Sec 18 C.4, IACS UR A1.4.1.2, p.389)
insert into lookup_rules
    (topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
     section_no, paragraph_id, page_no, source_quote, trigger_terms, context_note,
     verified, verified_by, verified_at)
values
('anchor_holding_power', 'hhp',
  'Daya cengkeram minimum jangkar High Holding Power (HHP) paling sedikit dua kali jangkar stockless biasa bermassa sama (Sec 18 C.4, IACS UR A1.4.1.2).',
  'The minimum holding power of a High Holding Power (HHP) anchor is at least twice that of an ordinary stockless anchor of the same mass (Sec 18 C.4, IACS UR A1.4.1.2).',
  'Daya cengkeram minimum jangkar High Holding Power (HHP) paling sedikit dua kali jangkar stockless biasa bermassa sama (Sec 18 C.4, IACS UR A1.4.1.2).',
  2.0, 'x stockless',
  18, 'C.4', 389,
  'A ''high holding power'' anchor is an anchor with a holding power of at least twice that of an ordinary stockless anchor of the same mass.',
  array['holding power','anchor','stockless','HHP','jangkar','daya cengkeram','stockless anchor','jangkar stockless','jangkar hhp'],
  -- Note: trigger_terms tightened (see scripts/_fix_overmatch.py) to
  -- ['holding power','daya cengkeram','HHP']. Generic 'anchor',
  -- 'stockless', 'jangkar' excluded to prevent over-match on mass / other
  -- aspect queries (e.g. "VHHP max mass", "HHP mass reduction %").
  'Multi-parameter topic (hhp vs vhhp). Param token: HHP (acronym, word-boundary matched). VHHP is substring of HHP context but discriminated by param_tokens in src/llm/lookup.py.',
  true, 'akashi', now());

-- 2) anchor_holding_power, parameter='vhhp' (Sec 18 C.5, IACS UR A1.4.1.3, p.389)
insert into lookup_rules
    (topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
     section_no, paragraph_id, page_no, source_quote, trigger_terms, context_note,
     verified, verified_by, verified_at)
values
('anchor_holding_power', 'vhhp',
  'Daya cengkeram minimum jangkar Very High Holding Power (VHHP) paling sedikit empat kali jangkar stockless biasa bermassa sama, atau paling sedikit dua kali jangkar HHP yang sudah disetujui bermassa sama (Sec 18 C.5, IACS UR A1.4.1.3).',
  'The minimum holding power of a Very High Holding Power (VHHP) anchor is at least four times that of an ordinary stockless anchor of the same mass, or at least twice that of a previously approved HHP anchor of the same mass (Sec 18 C.5, IACS UR A1.4.1.3).',
  'Daya cengkeram minimum jangkar Very High Holding Power (VHHP) paling sedikit empat kali jangkar stockless biasa bermassa sama, atau paling sedikit dua kali jangkar HHP yang sudah disetujui bermassa sama (Sec 18 C.5, IACS UR A1.4.1.3).',
  4.0, 'x stockless',
  18, 'C.5', 389,
  'A ''very high holding power'' anchor is an anchor with a holding power of at least four times that of an ordinary stockless anchor of the same mass. ... at least four times that of an ordinary stockless anchor or at least twice that of a previously approved HHP anchor of the same mass.',
  array['holding power','anchor','stockless','VHHP','jangkar','daya cengkeram','stockless anchor','jangkar stockless','jangkar vhhp'],
  -- Note: trigger_terms tightened (see scripts/_fix_overmatch.py) to
  -- ['holding power','daya cengkeram','VHHP'] for the same reason as hhp.
  'Multi-parameter topic. Param token: VHHP (acronym, word-boundary matched). Must be checked before HHP to avoid misfire since "high holding power" is substring of "very high holding power".',
  true, 'akashi', now());

-- 3) accommodation_deck_min_thickness (Sec 29 E.2, p.646)
-- Single row covering both values (5,0 inside, 5,5 exposed w/ sheathing).
insert into lookup_rules
    (topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
     section_no, paragraph_id, page_no, source_quote, trigger_terms, context_note,
     verified, verified_by, verified_at)
values
('accommodation_deck_min_thickness', null,
  'Tebal minimum geladak akomodasi dan bangunan atas: tmin = 5,0 mm untuk geladak di dalam; tmin = 5,5 mm untuk geladak terpapar cuaca bila dipasang effective sheathing (Sec 29 E.2).',
  'The following minimum thicknesses tmin for accommodation and superstructure decks have to be observed: tmin = 5.0 mm for decks inside; tmin = 5.5 mm for decks exposed to weather, if effective sheathing is provided (Sec 29 E.2).',
  'Tebal minimum geladak akomodasi dan bangunan atas: tmin = 5,0 mm untuk geladak di dalam; tmin = 5,5 mm untuk geladak terpapar cuaca bila dipasang effective sheathing (Sec 29 E.2).',
  null, null,
  29, 'E.2', 646,
  'The following minimum thicknesses tmin for accommodation and superstructure decks have to be observed: tmin = 5,0 [mm] for decks inside; tmin = 5,5 [mm] for decks exposed to weather, if effective sheathing is provided.',
  array['accommodation deck','superstructure deck','geladak akomodasi','geladak bangunan atas','sheathing','tmin','minimum thickness','tebal minimum','5,0','5,5'],
  'Applies to Sec 29 (Passenger and Special Purpose Ships) accommodation/superstructure decks only. Distinct from Sec 7 general deck plating rules (rules_deck_min_id).',
  true, 'akashi', now());

commit;
