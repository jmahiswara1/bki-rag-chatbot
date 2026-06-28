-- 007_lookup_rules_mvz.sql
-- Deterministic lookup for main vertical zone dimension (Fase Q5 MVZ).
-- Mirrors 004/005/006 style: idempotent, verified-only.
--
-- DB was migrated manually by mentor before this file was committed.  This
-- file exists purely for version control: re-running it is safe and
-- upserts the same single row.  No schema change.
begin;
delete from lookup_rules where topic in (
    'main_vertical_zone_dimension'
);
insert into lookup_rules
    (topic, parameter, value_text, value_num, unit, section_no, paragraph_id, page_no, source_quote, trigger_terms, context_note, verified, verified_by, verified_at)
values
-- Q5 MVZ: max length of MVZ on any deck (Sec 22 B.2.1, absolute p.489)
('main_vertical_zone_dimension', null,
  'Panjang dan lebar rata-rata main vertical zone pada tiap geladak umumnya tidak boleh melebihi 40 m. Perpanjangan hingga maksimum 48 m hanya diizinkan bila total luas main vertical zone tidak melebihi 1600 m2 pada tiap geladak (Sec 22 B.2.1).',
  40, 'm',
  22, 'B.2.1', 489,
  'The hull, superstructures and deckhouses are to be subdivided into main vertical zones the average length and width of which on any deck is generally not to exceed 40 m.',
  array['main vertical zone','main vertical zones','zona vertikal utama','mvz','average length','panjang rata-rata','maximum length','panjang maksimum','length and width','panjang dan lebar'],
  'General limit 40 m; 48 m extension only if total zone area <= 1600 m2 per deck. Do not assume the 48 m extension applies.',
  true, 'akashi', now());
commit;
