-- Rollback for migration 030_lookup_rules_holdout_gaps.sql

BEGIN;

DELETE FROM lookup_rules WHERE topic IN (
  'superstructure_corrosion_addition',
  'windows_side_scuttles_iso_test',
  'dredger_bottom_transverse_spacing'
);

COMMIT;
