-- 035_lookup_rules_aspect_precision_rollback.sql

BEGIN;

UPDATE lookup_rules
SET trigger_terms = ARRAY[
  'barge', 'collision bulkhead', '0,05Lcon', '0,08Lcon',
  'tongkang', 'sekat tubrukan', 'pontoon'
],
context_note = 'Distinct from collision_bulkhead_position (ships). Barge Lcon < 90 m extends range to 0,13Lcon. Need discrimination in lookup.py.',
verified_at = now()
WHERE topic = 'collision_bulkhead_barge';

COMMIT;
