-- 037_lookup_rules_dredger_aground_rollback.sql

BEGIN;

DELETE FROM lookup_rules WHERE topic = 'dredger_bottom_transverse_spacing_aground';

COMMIT;
