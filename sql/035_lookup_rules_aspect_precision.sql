-- 035_lookup_rules_aspect_precision.sql
-- Add explicit position qualifiers to the barge collision-bulkhead rule.
-- Runtime validation in src/llm/lookup.py remains the authoritative aspect gate.

BEGIN;

UPDATE lookup_rules
SET trigger_terms = ARRAY[
  'barge', 'barges', 'pontoon', 'tongkang', 'pusher-barge',
  'collision bulkhead', 'sekat tubrukan', 'sekat tabrakan',
  'located', 'location', 'position', 'posisi', 'lokasi',
  '0,05Lcon', '0,08Lcon', '0,13Lcon'
],
context_note = 'Position rule for barge collision bulkheads. Runtime aspect validation rejects spacing/thickness questions and falls through to chunk retrieval.',
verified_at = now()
WHERE topic = 'collision_bulkhead_barge';

COMMIT;
