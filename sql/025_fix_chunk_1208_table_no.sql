-- sql/025_fix_chunk_1208_table_no.sql
-- Build 33b: permanent fix for mislabeled Table 35.2 chunk.
-- Chunk 1208 contains "COLL-Notation | v* [kn] crmin" (Table 35.2 speed thresholds)
-- but was mislabeled as Table 35.1. This migration corrects the metadata.
-- Idiom: idempotent UPDATE with WHERE guard; safe to re-run.
--
-- Hot-patch removed in commit 292ff30 (src/retrieval/query.py).
-- This migration makes the fix durable across re-provision/re-ingest.

-- Verify before applying:
-- SELECT id, table_no, LEFT(content, 60) FROM chunks WHERE id = 1208;
-- Expected: table_no = 35.1

UPDATE chunks
SET table_no = '35.2',
    content = replace(content, '| Table 35.1]', '| Table 35.2]')
WHERE id = 1208
  AND table_no = '35.1'
  AND content_type = 'table';

-- Verify after applying:
-- SELECT id, table_no, LEFT(content, 60) FROM chunks WHERE id = 1208;
-- Expected: table_no = 35.2, content starts with "[Sec 35 ... | Table 35.2]"

-- ── ROLLBACK ──
-- UPDATE chunks
-- SET table_no = '35.1',
--     content = replace(content, '| Table 35.2]', '| Table 35.1]')
-- WHERE id = 1208
--   AND table_no = '35.2';
