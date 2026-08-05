-- Rollback for migration 032_lookup_rules_bottom_shell_formulas.sql

BEGIN;

DELETE FROM lookup_rules WHERE topic IN (
  'bottom_shell_formula_l_less_90',
  'bottom_shell_formula_l_greater_90'
);

COMMIT;
