-- 005_lookup_rules_length_L.sql
-- Deterministic lookup for ship rule length L definition (Fase E).
-- Idempotent: safe to re-run. Mirrors 004_lookup_rules.sql style.

begin;

delete from lookup_rules where topic in (
    'ship_length_l_definition'
);

insert into lookup_rules
    (topic, parameter, value_text, value_num, unit, section_no, paragraph_id, page_no, source_quote, trigger_terms, context_note, verified, verified_by, verified_at)
values
-- ship length L definition (single, text — no numeric value)
('ship_length_l_definition', null,
  'Panjang aturan (rule length) L adalah jarak dalam meter, diukur pada garis air saat sarat skantling (scantling draught), dari sisi depan linggi haluan (foreside of stem) sampai sisi belakang tongkat kemudi (rudder post), atau ke pusat poros kemudi (rudder stock) bila tidak ada rudder post. L tidak boleh kurang dari 96% dan tidak perlu lebih dari 97% panjang ekstrem pada garis air saat sarat skantling.',
  null, null,
  1, 'H.2.1', 22,
  'The rule length L is the distance in metres, measured on the waterline at the scantling draught from the foreside of stem to the after side of the rudder post, or the centre of the rudder stock if there is no rudder post. L is not to be less than 96% and need not be greater than 97% of the extreme length on the waterline at the scantling draught.',
  array['length L','rule length','rule length L','definisi panjang kapal','panjang kapal L','panjang aturan','definisi L','panjang L','scantling draught','foreside of stem','rudder post','rudder stock','96%','97%','definition of length','L'],
  'Definisi rule length L (BKI Sec 1 H.2.1). Beda dengan Lc/L*/Ls yang bukan subjek rule ini.',
  true, 'PDF Rules for Hull 2026 (mentor-verified)', now());

commit;
