-- 033_lookup_rules_10qa.sql
-- Deterministic lookup coverage for 8 frequently-asked Hull rule topics,
-- all values PDF-verified against data/bki_hull_2026.pdf (BKI Rules for Hull
-- Pt.1, Vol.II, January 2026 Edition).
--
-- Verified facts (page references are the physical PDF pages):
--   1. machinery space casing walls/tops min 5.0 mm   Sec 27 p627
--   2. supply-vessel deck-cargo stowracks heel 30 deg Sec 34 p668
--   3. supply-vessel bulwark plating min 7.5 mm       Sec 34 p668
--   4. cargo pump room skylights: steel, no glass      Sec 22 p542
--   5. mooring winch brake holding 80% MBLSD           Sec 18 p406
--   6. warping drums max 20 m from chock               Sec 18 p407
--   7. sauna door opens outwards by pushing            Sec 22 p503
--   8. cargo hold bulkhead (bulk carrier) min 9.0 mm   Sec 23 B.8.2 p554
--
-- Topics already covered elsewhere: dredger_bottom_transverse_spacing
-- (sql/030, 3.6 m), towing_winch_holding_capacity (sql/027, 80% Fmin),
-- tug_winch_drum_diameter (sql/004, 14 x).

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

INSERT INTO lookup_rules (
  topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
  section_no, paragraph_id, page_no, source_quote,
  trigger_terms, context_note, verified, verified_by, verified_at
) VALUES
(
  'machinery_casing_min_thickness', NULL,
  'Ketebalan pelat dinding casing (casing walls) dan bagian atas casing (casing tops) kamar mesin tidak boleh kurang dari 5,0 mm.',
  'The plate thickness of the casing walls and casing tops is not to be less than 5,0 mm.',
  'Ketebalan pelat dinding casing (casing walls) dan bagian atas casing (casing tops) kamar mesin tidak boleh kurang dari 5,0 mm.',
  5.0, 'mm', 27, NULL, 627,
  'The plate thickness of the casing walls and casing tops is not to be less than 5,0 mm.',
  ARRAY['casing walls', 'casing tops', 'machinery space casing', 'casing kamar mesin', 'casing', 'dinding casing', 'bagian atas casing', '5.0', '5,0'],
  'Sec 27 p627: minimum plate thickness of machinery space casing walls and tops.',
  true, 'bki-rag-qa', now()
),
(
  'supply_stowrack_heel_angle', NULL,
  'Rak penyimpanan kargo geladak (stowracks) pada kapal suplai harus dirancang untuk menahan beban pada sudut kemiringan (angle of heel) sebesar 30°.',
  'On-deck stowracks for deck cargo on supply vessels are to be designed for a load at an angle of heel of 30°.',
  'Rak penyimpanan kargo geladak (stowracks) pada kapal suplai harus dirancang untuk menahan beban pada sudut kemiringan (angle of heel) sebesar 30°.',
  30.0, 'deg', 34, NULL, 668,
  'On deck stowracks for deck cargo are to be fitted which are effectively attached to the deck. The stowracks are to be designed for a load at an angle of heel of 30°.',
  ARRAY['stowracks', 'stowrack', 'deck cargo', 'stow rack', 'kargo geladak', 'sudut kemiringan', 'angle of heel', 'rak penyimpanan', '30'],
  'Sec 34 p668: stowracks on deck for deck cargo designed for angle of heel of 30°.',
  true, 'bki-rag-qa', now()
),
(
  'supply_bulwark_plating_thickness', NULL,
  'Ketebalan pelat kubu-kubu (bulwark plating) pada kapal suplai tidak boleh kurang dari 7,5 mm.',
  'The thickness of the bulwark plating is not to be less than 7,5 mm.',
  'Ketebalan pelat kubu-kubu (bulwark plating) pada kapal suplai tidak boleh kurang dari 7,5 mm.',
  7.5, 'mm', 34, NULL, 668,
  'The thickness of the bulwark plating is not to be less than 7,5 mm.',
  ARRAY['bulwark plating', 'pelat kubu-kubu', 'pelat bulwark', 'ketebalan bulwark', 'bulwark', 'kubu-kubu', '7.5', '7,5'],
  'Sec 34 p668: supply-vessel bulwark plating minimum thickness.',
  true, 'bki-rag-qa', now()
),
(
  'cargo_pump_room_skylight', NULL,
  'Jendela atap (skylights) pada kamar pompa kargo harus terbuat dari baja, tidak boleh mengandung kaca, dan harus dapat ditutup dari luar kamar pompa.',
  'Skylights to cargo pump rooms shall be of steel, shall not contain any glass and shall be capable of being closed from outside the pump room.',
  'Jendela atap (skylights) pada kamar pompa kargo harus terbuat dari baja, tidak boleh mengandung kaca, dan harus dapat ditutup dari luar kamar pompa.',
  NULL, NULL, 22, NULL, 542,
  'Skylights to cargo pump rooms shall be of steel, shall not contain any glass and shall be capable of being closed from outside the pump room.',
  ARRAY['skylights', 'skylight', 'cargo pump rooms', 'cargo pump room', 'kamar pompa kargo', 'jendela atap', 'glass', 'kaca'],
  'Sec 22 p542: cargo pump room skylights must be steel, no glass, closable from outside.',
  true, 'bki-rag-qa', now()
),
(
  'mooring_winch_brake_holding', NULL,
  'Rem derek tambat (mooring winches) harus memiliki kapasitas penahanan (holding capacity) yang cukup untuk mencegah terulurnya tali ketika tegangan tali mencapai 80% dari beban putus minimum desain kapal (ship design minimum breaking load, MBLSD).',
  'Each winch should be fitted with brakes the holding capacity of which is sufficient to prevent unreeling of the mooring line when the rope tension is equal to 80% of the ship design minimum breaking load of the mooring line.',
  'Rem derek tambat (mooring winches) harus memiliki kapasitas penahanan (holding capacity) yang cukup untuk mencegah terulurnya tali ketika tegangan tali mencapai 80% dari beban putus minimum desain kapal (ship design minimum breaking load, MBLSD).',
  80.0, '% MBLSD', 18, NULL, 406,
  'Each winch should be fitted with brakes the holding capacity of which is sufficient to prevent unreeling of the mooring line when the rope tension is equal to 80% of the ship design minimum breaking load of the mooring line.',
  ARRAY['mooring winches', 'mooring winch', 'derek tambat', 'brake', 'rem derek', 'brakes', 'holding capacity', 'kapasitas penahanan', 'unreel', 'terulur', 'rope tension', 'tegangan tali', '80%', 'MBLSD', 'minimum breaking load'],
  'Sec 18 p406: mooring winch brake holding capacity vs 80% MBLSD. Distinct from towing winch holding capacity (Sec 27 C.5.3.1).',
  true, 'bki-rag-qa', now()
),
(
  'warping_drum_chock_distance', NULL,
  'Tromol gulung (warping drums) sebaiknya ditempatkan tidak lebih dari 20 m dari lubang tali (chock), diukur sepanjang jalur tali.',
  'Warping drums should preferably be positioned not more than 20 m away from the chock, measured along the lead of the rope.',
  'Tromol gulung (warping drums) sebaiknya ditempatkan tidak lebih dari 20 m dari lubang tali (chock), diukur sepanjang jalur tali.',
  20.0, 'm', 18, NULL, 407,
  'Warping drums should preferably be positioned not more than 20 m away from the chock, measured along the lead of the rope.',
  ARRAY['warping drums', 'warping drum', 'tromol gulung', 'chock', 'lubang tali', '20 m', 'lead of the rope', 'jalur tali', 'posisi'],
  'Sec 18 p407: recommended maximum distance of warping drums from chock (20 m).',
  true, 'bki-rag-qa', now()
),
(
  'sauna_door_opening_direction', NULL,
  'Pintu ruang sauna harus dapat membuka ke arah luar dengan cara didorong.',
  'The sauna door shall open outwards by pushing.',
  'Pintu ruang sauna harus dapat membuka ke arah luar dengan cara didorong.',
  NULL, NULL, 22, NULL, 503,
  'The sauna door shall open outwards by pushing.',
  ARRAY['sauna door', 'sauna', 'pintu sauna', 'ruang sauna', 'open outwards', 'membuka ke luar', 'pushing', 'didorong', 'arah bukaan'],
  'Sec 22 p503: sauna door opens outwards by pushing.',
  true, 'bki-rag-qa', now()
),
(
  'cargo_hold_bulkhead_min_thickness', NULL,
  'Ketebalan pelat sekat ruang muat kargo (cargo hold bulkheads) pada kapal curah dalam kondisi apa pun tidak boleh kurang dari 9,0 mm.',
  'The scantlings of the cargo hold bulkheads are not to be less than those required for a watertight bulkhead. The plate thickness is in no case to be taken less than 9,0 mm.',
  'Ketebalan pelat sekat ruang muat kargo (cargo hold bulkheads) pada kapal curah dalam kondisi apa pun tidak boleh kurang dari 9,0 mm.',
  9.0, 'mm', 23, 'B.8.2', 554,
  'The plate thickness is in no case to be taken less than 9,0 mm.',
  ARRAY['cargo hold bulkheads', 'cargo hold bulkhead', 'sekat ruang muat', 'sekat ruang muat kargo', 'bulk carrier', 'kapal curah', '9.0', '9,0', 'bulkheads'],
  'Sec 23 B.8.2 p554: minimum absolute plate thickness for cargo hold bulkheads on bulk carriers.',
  true, 'bki-rag-qa', now()
),
(
  'emergency_release_activation_time', NULL,
  'Sistem rilis darurat (emergency release system) pada derek tunda harus berfungsi secepat yang wajar dan dalam waktu maksimum 3 detik setelah diaktifkan.',
  'The emergency release system is to function as quickly as is reasonably practicable and within a maximum of three seconds after activation.',
  'Sistem rilis darurat (emergency release system) pada derek tunda harus berfungsi secepat yang wajar dan dalam waktu maksimum 3 detik setelah diaktifkan.',
  3.0, 's', 27, 'C.6.2.4', 632,
  'The emergency release system is to function as quickly as is reasonably practicable and within a maximum of three seconds after activation.',
  ARRAY['emergency release system', 'emergency release systems', 'sistem rilis darurat', 'emergency release', 'rilis darurat', 'activation', 'setelah diaktifkan', 'after activation', 'three seconds', '3 detik', 'three seconds after'],
  'Sec 27 C.6.2.4 p632: emergency release must function within max three seconds after activation.',
  true, 'bki-rag-qa', now()
);

COMMIT;
