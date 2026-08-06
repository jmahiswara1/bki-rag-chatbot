-- 034_lookup_rules_precision_rollback.sql

BEGIN;

UPDATE lookup_rules
SET trigger_terms = ARRAY[
  'bulwark plating', 'pelat kubu-kubu', 'pelat bulwark',
  'ketebalan bulwark', 'bulwark', 'kubu-kubu', '7.5', '7,5'
],
context_note = 'Sec 34 p668: supply-vessel bulwark plating minimum thickness.',
verified_at = now()
WHERE topic = 'supply_bulwark_plating_thickness';

COMMIT;
