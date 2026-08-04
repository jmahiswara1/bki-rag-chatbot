-- 029_rollback.sql

BEGIN;

DELETE FROM lookup_rules WHERE topic = 'framing_system_by_length';
DELETE FROM lookup_rules WHERE topic = 'container_scantling_factors';

-- Restore original forepeak_stringer_spacing trigger terms
UPDATE lookup_rules
SET trigger_terms = ARRAY['forepeak','fore peak','collision bulkhead','tiers of beams','stringer','stringer plate','senta','haluan','ceruk haluan','spacing','jarak','2,6 m']
WHERE topic = 'forepeak_stringer_spacing';

COMMIT;
