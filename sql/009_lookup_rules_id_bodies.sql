-- 009_lookup_rules_id_bodies.sql
-- Complete Indonesian answer bodies (fragments -> full sentences).
-- Mirrors 008 bilingual.  Only touches value_text_id columns; no other
-- columns affected.  Idempotent (re-runnable).

-- restricted_service_modulus_reduction (3 rows)
update lookup_rules set value_text_id = 'Untuk daerah pelayaran terbatas samudera (Restricted Ocean Service / P), modulus penampang yang disyaratkan dapat dikurangi sebesar 5% (Sec 5 C.2.1).' where topic = 'restricted_service_modulus_reduction' and parameter = 'P';
update lookup_rules set value_text_id = 'Untuk daerah pelayaran pantai (Coasting Service / L), modulus penampang yang disyaratkan dapat dikurangi sebesar 15% (Sec 5 C.2.1).' where topic = 'restricted_service_modulus_reduction' and parameter = 'L';
update lookup_rules set value_text_id = 'Untuk daerah pelayaran perairan tenang (Sheltered Water Service / T), modulus penampang yang disyaratkan dapat dikurangi sebesar 25% (Sec 5 C.2.1).' where topic = 'restricted_service_modulus_reduction' and parameter = 'T';

-- forepeak_stringer_spacing
update lookup_rules set value_text_id = 'Pada ceruk haluan (forepeak), jarak antar tingkat balok atau senta sisi tidak boleh melebihi 2,6 m (Sec 9 A.5.2.1).' where topic = 'forepeak_stringer_spacing';

-- tug_winch_drum_diameter
update lookup_rules set value_text_id = 'Untuk winch tunda pada kapal tunda, diameter barel drum harus paling sedikit 14 kali diameter tali tunda (Sec 27 C.5.2.3).' where topic = 'tug_winch_drum_diameter';

-- fire_door_closing_time (2 rows)
update lookup_rules set value_text_id = 'Pintu kebakaran berengsel (hinged) harus mampu menutup dalam waktu sekitar 40 detik (Sec 22 C.6.6.2).' where topic = 'fire_door_closing_time' and parameter = 'hinged';
update lookup_rules set value_text_id = 'Pintu kebakaran geser bertenaga (sliding) harus menutup dengan kecepatan 0,1 sampai 0,2 m/s (Sec 22 C.6.6.2).' where topic = 'fire_door_closing_time' and parameter = 'sliding';

-- bulwark_guardrail_min_height
update lookup_rules set value_text_id = 'Tinggi minimum bulwark atau pagar pengaman (guard rail) adalah 1,0 m (Sec 6 K.2).' where topic = 'bulwark_guardrail_min_height';

-- ship_length_l_definition
update lookup_rules set value_text_id = 'Panjang aturan L diukur pada garis air sarat skantling dari sisi depan linggi haluan sampai sisi belakang tongkat kemudi (atau pusat poros kemudi bila tidak ada tongkat kemudi), dan tidak kurang dari 96% serta tidak lebih dari 97% panjang ekstrem pada garis air tersebut (Sec 1 H.2.1).' where topic = 'ship_length_l_definition';
