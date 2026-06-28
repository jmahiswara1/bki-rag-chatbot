-- 006_lookup_rules_depth_ratio.sql
-- Deterministic lookup for depth-to-length ratio H >= L/n by range of service
-- (Fase E extension).  Mirrors 004/005 style: idempotent, verified-only.
--
-- DB was migrated manually by mentor before this file was committed.  This
-- file exists purely for version control: re-running it is safe and
-- upserts the same single row.  No schema change.

begin;

delete from lookup_rules where topic in (
    'depth_to_length_ratio'
);

insert into lookup_rules
    (topic, parameter, value_text, value_num, unit, section_no, paragraph_id, page_no, source_quote, trigger_terms, context_note, verified, verified_by, verified_at)
values
-- depth H >= L/n by range of service (single, text -- the L/16/L/18/L/19 set is
-- conveyed verbatim in value_text)
('depth_to_length_ratio', null,
  'Kedalaman (depth H) kapal tidak boleh kurang dari: L/16 untuk Unlimited Range of Service dan P (Restricted Ocean Service); L/18 untuk L (Coasting Service); L/19 untuk T (Sheltered Water Service). Kedalaman lebih kecil dapat diterima bila dibuktikan kesetaraan kekuatan, kekakuan, dan keselamatan kapal.',
  null, null,
  1, 'A.1', 17,
  'The Rules apply to seagoing steel ships classed A100 whose breadth to depth ratio is within the range common for seagoing ships and the depth H of which is not less than: - L/16 for Unlimited Range of Service and P (Restricted Ocean Service) - L/18 for L (Coasting Service) - L/19 for T (Sheltered Water Service).',
  array['depth to length ratio','kedalaman terhadap panjang','rasio kedalaman','ratio of depth','breadth to depth','depth h','minimum depth','kedalaman minimum','range of service','l/16','l/18','l/19'],
  'BKI Rules Pt.1 Vol.II Sec 1 A.1 (Validity, Equivalence). Minimum depth-to-length ratio by range of service.',
  true, 'PDF Rules for Hull 2026 (mentor-verified)', now());

commit;
