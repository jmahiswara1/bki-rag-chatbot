-- Rollback for migration 031_lookup_rules_holdout_definitions.sql

BEGIN;

DELETE FROM lookup_rules WHERE topic IN (
  'weather_deck_definition',
  'doubling_plate_tank_permission'
);

COMMIT;
