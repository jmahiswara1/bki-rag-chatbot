-- Migration 023: Persistent cache for condensed English queries.
-- Eliminates nondeterminism from _translate_condense (LLM float-nondet on GPU).
-- Cache is shared across processes: TUI and main.py see identical en_query.

BEGIN;

CREATE TABLE IF NOT EXISTS query_condense_cache (
    query_hash    TEXT PRIMARY KEY,
    normalized_query TEXT NOT NULL,
    language      TEXT NOT NULL,
    mode          TEXT NOT NULL,
    condense_version INTEGER NOT NULL,
    en_query      TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMIT;
