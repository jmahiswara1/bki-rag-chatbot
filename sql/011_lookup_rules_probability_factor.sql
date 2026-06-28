-- 011_lookup_rules_probability_factor.sql
-- Deterministic lookup for probability factor fQ (Table 4.2).
-- Mirrors 004/005/006/007 style: idempotent, verified-only.

begin;

delete from lookup_rules where topic in (
    'probability_factor_fq'
);

insert into lookup_rules
    (topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
     section_no, paragraph_id, page_no, source_quote, trigger_terms, context_note,
     verified, verified_by, verified_at)
values
('probability_factor_fq', null,
  'Faktor probabilitas fQ bergantung pada level probabilitas Q (Table 4.2): fQ = 1,000 pada Q = 10^-8; 0,875 pada 10^-7; 0,750 pada 10^-6; 0,625 pada 10^-5; dan 0,500 pada 10^-4. Level probabilitas skantling standar adalah Q = 10^-8 sehingga fQ = 1,000 (Sec 4 E.1).',
  'The probability factor fQ depends on the probability level Q (Table 4.2): fQ = 1.000 at Q = 10^-8, 0.875 at 10^-7, 0.750 at 10^-6, 0.625 at 10^-5, and 0.500 at 10^-4. The standard scantling probability level is Q = 10^-8, giving fQ = 1.000 (Sec 4 E.1).',
  'Faktor probabilitas fQ bergantung pada level probabilitas Q (Table 4.2): fQ = 1,000 pada Q = 10^-8; 0,875 pada 10^-7; 0,750 pada 10^-6; 0,625 pada 10^-5; dan 0,500 pada 10^-4. Level probabilitas skantling standar adalah Q = 10^-8 sehingga fQ = 1,000 (Sec 4 E.1).',
  1.0, null,
  4, 'E.1', 131,
  'fQ = probability factor depending on probability level Q as outline in Table 4.2.',
  array['probability factor','faktor probabilitas','probability level','level probabilitas','fq','table 4.2','tabel 4.2','probability factor fq'],
  'Discrete table; standard scantling level Q=10^-8 gives fQ=1,000. fQ decreases for higher Q (reduced stress range).',
  true, 'akashi', now());

commit;
