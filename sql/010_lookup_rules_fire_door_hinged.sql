-- 010_lookup_rules_fire_door_hinged.sql
-- Restore lower closing-time bound for hinged fire doors (10 s minimum).
-- The source_quote at Sec 22 C.6.6.2 p.494 states "no more than 40 
-- s and no less than 10 s".  The previous EN body ("within 40 seconds")
-- and ID body ("sekitar 40 detik") both omitted the lower bound and
-- used imprecise qualifiers.  This script restores both bounds.

update lookup_rules
   set value_text_en = 'Hinged fire doors are to be capable of fully closing in not more than 40 seconds and not less than 10 seconds (Sec 22 C.6.6.2).',
       value_text_id = 'Pintu kebakaran berengsel (hinged) harus mampu menutup penuh dalam waktu tidak lebih dari 40 detik dan tidak kurang dari 10 detik (Sec 22 C.6.6.2).'
 where topic = 'fire_door_closing_time'
   and parameter = 'hinged';
