-- 028_rollback.sql

BEGIN;

DELETE FROM lookup_rules WHERE topic = 'spm_bow_chain_stopper_chain_size';
DELETE FROM lookup_rules WHERE topic = 'aluminium_helideck_fire_protection';
DELETE FROM lookup_rules WHERE topic = 'iw_underwater_hull_corrosion';

COMMIT;
