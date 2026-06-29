-- 014_lookup_rules_sea_water_density.sql
-- Deterministic lookup for sea water density (rho).
-- Mirrors 011/012/013 style: idempotent, verified-only.
begin;
delete from lookup_rules where topic in (
    'sea_water_density'
);
insert into lookup_rules
    (topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
     section_no, paragraph_id, page_no, source_quote, trigger_terms, context_note,
     verified, verified_by, verified_at)
values
('sea_water_density', null,
  'Massa jenis air laut yang digunakan dalam BKI Rules for Hull adalah 1,025 t/m^3, sesuai Sec 21 F. Nilai ini dipakai, misalnya, pada perhitungan displacement moulded dan tekanan air laut.',
  'The density of sea water used in the BKI Rules for Hull is 1.025 t/m^3, as defined in Sec 21 F. It is applied, for example, in moulded displacement and sea pressure calculations.',
  'Massa jenis air laut yang digunakan dalam BKI Rules for Hull adalah 1,025 t/m^3, sesuai Sec 21 F. Nilai ini dipakai, misalnya, pada perhitungan displacement moulded dan tekanan air laut.',
  1.025, 't/m^3',
  21, 'F.5.3.1', 472,
  'rho = density of sea water (1,025 t/m3)',
  array['sea water density','seawater density','density of sea water','sea water','seawater','massa jenis air laut','densitas air laut','berat jenis air laut','air laut'],
  'Discrete value 1,025 t/m^3 (BKI standard sea water density) for displacement and pressure calculations per Sec 21 F.5.3.1. Do not use 1,0 t/m^3 (that is a fresh-water/lower-bound context).',
  true, 'akashi', now());
commit;
