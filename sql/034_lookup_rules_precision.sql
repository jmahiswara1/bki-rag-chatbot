-- 034_lookup_rules_precision.sql
-- Require supply-vessel context for the supply-specific bulwark rule.

BEGIN;

UPDATE lookup_rules
SET trigger_terms = ARRAY[
  'bulwark plating', 'pelat kubu-kubu', 'pelat bulwark',
  'ketebalan bulwark', 'bulwark', 'kubu-kubu', '7.5', '7,5',
  'supply vessel', 'supply vessels', 'kapal suplai'
],
context_note = 'Sec 34 p668: supply-vessel bulwark plating minimum thickness; supply-vessel context is required to select this rule.',
verified_at = now()
WHERE topic = 'supply_bulwark_plating_thickness';

COMMIT;
