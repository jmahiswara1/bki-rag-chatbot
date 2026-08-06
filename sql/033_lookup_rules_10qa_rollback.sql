-- 033_lookup_rules_10qa_rollback.sql
-- Rollback for sql/033_lookup_rules_10qa.sql: remove the 8 added lookup topics.

BEGIN;

DELETE FROM lookup_rules WHERE topic IN (
  'machinery_casing_min_thickness',
  'supply_stowrack_heel_angle',
  'supply_bulwark_plating_thickness',
  'cargo_pump_room_skylight',
  'mooring_winch_brake_holding',
  'warping_drum_chock_distance',
  'sauna_door_opening_direction',
  'cargo_hold_bulkhead_min_thickness',
  'emergency_release_activation_time'
);

COMMIT;
