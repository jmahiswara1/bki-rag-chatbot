-- 008_lookup_rules_bilingual.sql
-- Bilingual body columns (value_text_en, value_text_id) for deterministic
-- language-aware lookup short-circuit answers (commit "fix: return lookup
-- answers in the query language").
--
-- Mirrors 004/005/006/007 style.  Idempotent (IF NOT EXISTS) + explicit
-- UPDATE for the 11 verified rows.  No DDL on existing data.
alter table lookup_rules add column if not exists value_text_en text;
alter table lookup_rules add column if not exists value_text_id text;
update lookup_rules set value_text_id = value_text where value_text_id is null;
-- restricted_service_modulus_reduction (3 rows, one per parameter)
update lookup_rules set value_text_en = 'For restricted ocean service, the required section modulus may be reduced by 5% (Sec 5 C.2.1).' where topic = 'restricted_service_modulus_reduction' and parameter = 'P';
update lookup_rules set value_text_en = 'For coasting service, the required section modulus may be reduced by 15% (Sec 5 C.2.1).' where topic = 'restricted_service_modulus_reduction' and parameter = 'L';
update lookup_rules set value_text_en = 'For sheltered water service, the required section modulus may be reduced by 25% (Sec 5 C.2.1).' where topic = 'restricted_service_modulus_reduction' and parameter = 'T';
-- forepeak_stringer_spacing
update lookup_rules set value_text_en = 'In the forepeak, the spacing between tiers of beams or side stringers is not to exceed 2.6 m (Sec 9 A.5.2.1).' where topic = 'forepeak_stringer_spacing';
-- tug_winch_drum_diameter
update lookup_rules set value_text_en = 'For towing winches on tugs, the drum barrel diameter is to be at least 14 times the towline diameter (Sec 27 C.5.2.3).' where topic = 'tug_winch_drum_diameter';
-- fire_door_closing_time (2 rows)
update lookup_rules set value_text_en = 'Hinged fire doors are to be capable of closing within 40 seconds (Sec 22 C.6.6.2).' where topic = 'fire_door_closing_time' and parameter = 'hinged';
update lookup_rules set value_text_en = 'Power-operated sliding fire doors are to close at a speed of 0.1 to 0.2 m/s (Sec 22 C.6.6.2).' where topic = 'fire_door_closing_time' and parameter = 'sliding';
-- bulwark_guardrail_min_height
update lookup_rules set value_text_en = 'The minimum height of bulwarks or guard rails is 1.0 m (Sec 6 K.2).' where topic = 'bulwark_guardrail_min_height';
-- ship_length_l_definition
update lookup_rules set value_text_en = 'The rule length L is measured on the scantling-draught waterline from the foreside of the stem to the after side of the rudder post (or centre of the rudder stock where there is no rudder post), and is not less than 96% nor more than 97% of the extreme length on that waterline (Sec 1 H.2.1).' where topic = 'ship_length_l_definition';
-- depth_to_length_ratio
update lookup_rules set value_text_en = 'The depth H is generally not to be less than L/16 for unlimited and restricted ocean service, L/18 for coasting service, and L/19 for sheltered-water service (Sec 1 A.1).' where topic = 'depth_to_length_ratio';
-- main_vertical_zone_dimension
update lookup_rules set value_text_en = 'On any deck, the average length and width of a main vertical zone is generally not to exceed 40 m; it may be extended to a maximum of 48 m only if the total area of the main vertical zone does not exceed 1600 m^2 on that deck (Sec 22 B.2.1).' where topic = 'main_vertical_zone_dimension';
