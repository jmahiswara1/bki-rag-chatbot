-- 003_seed_formulas.sql
-- Template seed untuk tabel formulas (kalkulator terkurasi).
-- PENTING: baris di bawah hanya CONTOH STRUKTUR, bukan rumus BKI resmi.
--   - expression memakai sintaks yang dipahami sympy (operator: + - * / **, fungsi: sqrt(), dst).
--   - variables: objek JSON { simbol: { desc, unit } } untuk slot filling di CLI.
--   - result_unit: satuan hasil akhir.
--   - verified: set true HANYA setelah rumus dicek manual terhadap dokumen sumber.
-- Ganti setiap baris dengan rumus asli + nilai section/paragraph/page yang benar,
-- lalu set verified = true.

insert into formulas
  (code, title, section_no, paragraph_id, page_no, expression, variables, result_unit, notes, verified)
values
  (
    'EXAMPLE_PLATE_THICKNESS',
    'Contoh: tebal pelat minimum (PLACEHOLDER)',
    3,
    '3.F.2',
    null,
    'c * sqrt(L)',
    '{
       "c": {"desc": "koefisien material", "unit": "-"},
       "L": {"desc": "panjang kapal", "unit": "m"}
     }'::jsonb,
    'mm',
    'PLACEHOLDER. Ganti expression dan variables dengan rumus asli dari Rules.',
    false
  ),
  (
    'EXAMPLE_SECTION_MODULUS',
    'Contoh: section modulus (PLACEHOLDER)',
    5,
    '5.B.1',
    null,
    'k * L**2 * B * (Cb + 0.7)',
    '{
       "k": {"desc": "faktor material", "unit": "-"},
       "L": {"desc": "panjang kapal", "unit": "m"},
       "B": {"desc": "lebar kapal", "unit": "m"},
       "Cb": {"desc": "koefisien blok", "unit": "-"}
     }'::jsonb,
    'cm3',
    'PLACEHOLDER. Ganti dengan rumus asli dan verifikasi terhadap contoh perhitungan di Rules.',
    false
  )
on conflict (code) do update set
  title        = excluded.title,
  section_no   = excluded.section_no,
  paragraph_id = excluded.paragraph_id,
  page_no      = excluded.page_no,
  expression   = excluded.expression,
  variables    = excluded.variables,
  result_unit  = excluded.result_unit,
  notes        = excluded.notes,
  verified     = excluded.verified;
