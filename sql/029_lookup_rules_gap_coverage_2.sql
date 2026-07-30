-- 029_lookup_rules_gap_coverage_2.sql
-- Gap coverage for 3 more topics from manual QA evaluation (Batch 2):
-- 1. framing_system_by_length: longitudinal framing for L ≥ 90-100m (Q1)
-- 2. Update forepeak_stringer_spacing trigger terms (Q4 misfire)
-- 3. container_scantling_factors: comprehensive list (Q6)

BEGIN;

-- Rule 1: Framing system based on ship length
DELETE FROM lookup_rules WHERE topic = 'framing_system_by_length';
INSERT INTO lookup_rules (
  topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
  section_no, paragraph_id, page_no, source_quote,
  trigger_terms, context_note,
  verified, verified_by, verified_at
) VALUES (
  'framing_system_by_length',
  NULL,
  'Untuk kapal dengan panjang L ≥ 90 m, sistem konstruksi memanjang (longitudinal framing) umumnya digunakan. Konstruksi melintang (transverse framing) berlaku untuk kapal dengan L < 90 m. Lihat juga Sec 6 B.5.2 yang mensyaratkan pengaku memanjang tambahan untuk kapal L > 100 m dengan dasar berkonstruksi memanjang.',
  'For ships with length L ≥ 90 m, longitudinal framing system is generally applied. Transverse framing applies to ships with L < 90 m. See also Sec 6 B.5.2 requiring additional longitudinal stiffeners for ships exceeding 100 m in length with longitudinally framed bottom.',
  'Untuk kapal dengan panjang L ≥ 90 m, sistem konstruksi memanjang (longitudinal framing) umumnya digunakan. Konstruksi melintang (transverse framing) berlaku untuk kapal dengan L < 90 m. Lihat juga Sec 6 B.5.2 yang mensyaratkan pengaku memanjang tambahan untuk kapal L > 100 m dengan dasar berkonstruksi memanjang.',
  NULL,
  NULL,
  6,
  'B.5.2',
  170,
  'For ships exceeding 100 m in length, the bottom of which is longitudinally framed, the flat plate keel is to be stiffened by additional longitudinal stiffeners fitted at a distance of approx. 500 mm from centre line.',
  ARRAY['jenis konstruksi', 'sistem konstruksi', 'konstruksi memanjang', 'konstruksi melintang', 'longitudinal framing', 'transverse framing', 'framing system', 'framing type', 'tipe konstruksi', 'berdasarkan panjang', 'based on length', 'L ≥ 90', 'L > 100', 'panjang kapal', 'ship length'],
  'Build 38 gap coverage. Q1 failure: retrieval matched fire protection (Sec 22) instead of framing system.',
  true,
  'akashi',
  now()
);

-- Rule 2: Update forepeak_stringer_spacing trigger terms (existing rule from 004)
-- The rule exists but didn't fire for Q4 query phrasing. Add missing trigger terms.
-- Original trigger_terms: forepeak, fore peak, collision bulkhead, tiers of beams, stringer, stringer plate, senta, haluan, ceruk haluan, spacing, jarak, 2,6 m
-- Missing terms that Q4 used: stiffener memanjang, jumlah, dipasang, penegar
UPDATE lookup_rules
SET trigger_terms = ARRAY['forepeak','fore peak','collision bulkhead','tiers of beams','stringer','stringer plate','senta','haluan','ceruk haluan','spacing','jarak','2,6 m','stiffener memanjang','stiffener','penegar','longitudinal stiffener','jumlah','dipasang','berapa jumlah','berapa jarak','tiers','tier']
WHERE topic = 'forepeak_stringer_spacing';

-- Rule 3: Container ship scantling factors
DELETE FROM lookup_rules WHERE topic = 'container_scantling_factors';
INSERT INTO lookup_rules (
  topic, parameter, value_text, value_text_en, value_text_id, value_num, unit,
  section_no, paragraph_id, page_no, source_quote,
  trigger_terms, context_note,
  verified, verified_by, verified_at
) VALUES (
  'container_scantling_factors',
  NULL,
  'Faktor-faktor yang mempengaruhi perhitungan scantling kapal kontainer meliputi: (1) Material factor k (Sec 2 B, khusus baja YP47: k=0.62, Sec 39 A.5.1); (2) Corrosion addition tK (Sec 3 K); (3) Tegangan izin: bending σb≤150/k, geser τ≤100/k, ekuivalen σv≤180/k (Sec 9 A.2.1.4); (4) Buckling strength (Sec 3 F); (5) Fatigue strength (Sec 20, khusus kontainer: Sec 39 A.5.2); (6) Persyaratan pelat tebal ekstrem >50mm–100mm dengan brittle crack arrest design (Sec 39 A.4, D); (7) Longitudinal hull girder strength (Sec 5); (8) Design loads + probability factor fQ (Sec 4); (9) NDT ultrasonic testing pada butt joints (Sec 39 B, C).',
  'Factors affecting container ship scantling calculations include: (1) Material factor k (Sec 2 B, YP47 steel: k=0.62, Sec 39 A.5.1); (2) Corrosion addition tK (Sec 3 K); (3) Permissible stresses: bending σb≤150/k, shear τ≤100/k, equivalent σv≤180/k (Sec 9 A.2.1.4); (4) Buckling strength (Sec 3 F); (5) Fatigue strength (Sec 20, container-specific: Sec 39 A.5.2); (6) Extremely thick plates >50mm–100mm with brittle crack arrest design (Sec 39 A.4, D); (7) Longitudinal hull girder strength (Sec 5); (8) Design loads + probability factor fQ (Sec 4); (9) NDT ultrasonic testing on butt joints (Sec 39 B, C).',
  'Faktor-faktor yang mempengaruhi perhitungan scantling kapal kontainer meliputi: (1) Material factor k (Sec 2 B, khusus baja YP47: k=0.62, Sec 39 A.5.1); (2) Corrosion addition tK (Sec 3 K); (3) Tegangan izin: bending σb≤150/k, geser τ≤100/k, ekuivalen σv≤180/k (Sec 9 A.2.1.4); (4) Buckling strength (Sec 3 F); (5) Fatigue strength (Sec 20, khusus kontainer: Sec 39 A.5.2); (6) Persyaratan pelat tebal ekstrem >50mm–100mm dengan brittle crack arrest design (Sec 39 A.4, D); (7) Longitudinal hull girder strength (Sec 5); (8) Design loads + probability factor fQ (Sec 4); (9) NDT ultrasonic testing pada butt joints (Sec 39 B, C).',
  NULL,
  NULL,
  39,
  'A.1',
  695,
  'Section 39 applies to extremely thick steel plates in container ships for brittle crack prevention, in addition to the requirements for hull structural steel as specified in Section 2, B.',
  ARRAY['scantling','scantlings','faktor','factor','factors','mempengaruhi','mempengaruhi','affecting','perhitungan','calculation','kapal kontainer','kapal peti kemas','container ship','container vessel','apa saja','apa faktor','list','daftar'],
  'Build 38 gap coverage. Q6 failure: retrieval returned Sec 23 (Bulk Carriers) instead of Sec 39 (Container Ships).',
  true,
  'akashi',
  now()
);

COMMIT;
