-- 032_lookup_rules_bottom_shell_formulas.sql
-- Deterministic formula coverage for Section 6 bottom shell branches.

BEGIN;

DELETE FROM lookup_rules WHERE topic IN (
  'bottom_shell_formula_l_less_90',
  'bottom_shell_formula_l_greater_90'
);

INSERT INTO lookup_rules (
  topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
  section_no, paragraph_id, page_no, source_quote,
  trigger_terms, context_note, verified, verified_by, verified_at
) VALUES
(
  'bottom_shell_formula_l_less_90', NULL,
  'Untuk kapal dengan L < 90 m, tebal pelat dasar lambung minimum adalah tB1 = 1,9 · nf · a · √(pB · k) + tK [mm].',
  'For ships with L < 90 m, the minimum bottom shell plating thickness is tB1 = 1.9 · nf · a · √(pB · k) + tK [mm].',
  'Untuk kapal dengan L < 90 m, tebal pelat dasar lambung minimum adalah tB1 = 1,9 · nf · a · √(pB · k) + tK [mm].',
  NULL, 'mm', 6, 'B.1.1', 167,
  '1.9 · nf · a · √(pB · k) + tK [mm].',
  ARRAY['bottom shell plating', 'bottom plating', 'bottom shell', 'pelat dasar lambung', 'pelat kulit dasar', 'pelat alas', '1.9', '1,9', 'pB', 'bottom load'],
  'Section 6 B.1.1. Applies to ships with L < 90 m.', true, 'bki-rag-eval', now()
),
(
  'bottom_shell_formula_l_greater_90', NULL,
  'Untuk kapal dengan L ≥ 90 m, tebal pelat dasar lambung minimum adalah nilai terbesar dari tB1 = 18,3 · nf · a · √(pB / (200,2/k)) + tK dan tB2 = 1,21 · a · √(pB · k) + tK [mm].',
  'For ships with L ≥ 90 m, the minimum bottom shell plating thickness is the greater of tB1 = 18.3 · nf · a · √(pB / (200.2/k)) + tK and tB2 = 1.21 · a · √(pB · k) + tK [mm].',
  'Untuk kapal dengan L ≥ 90 m, tebal pelat dasar lambung minimum adalah nilai terbesar dari tB1 = 18,3 · nf · a · √(pB / (200,2/k)) + tK dan tB2 = 1,21 · a · √(pB · k) + tK [mm].',
  NULL, 'mm', 6, 'B.1.2', 167,
  'Max(18.3 · nf · a · √(pB / (200.2/k)) + tK, 1.21 · a · √(pB · k) + tK).',
  ARRAY['bottom shell plating', 'bottom plating', 'bottom shell', 'pelat dasar lambung', 'pelat kulit dasar', 'pelat alas', '18.3', '18,3', 'pB', 'bottom load'],
  'Section 6 B.1.2. Applies to ships with L ≥ 90 m.', true, 'bki-rag-eval', now()
);

COMMIT;
