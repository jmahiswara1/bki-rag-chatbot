-- 001_init.sql
-- Skema awal BKI Hull RAG Chatbot.
-- Jalankan file ini lebih dulu, lalu 002_match_chunks.sql.

create extension if not exists vector;

-- Potongan dokumen yang di-embed dan disimpan untuk retrieval.
create table if not exists chunks (
  id            bigint generated always as identity primary key,
  section_no    int  not null,
  section_title text not null,
  paragraph_id  text,
  content_type  text not null
                check (content_type in ('narrative','table','formula','figure')),
  table_no      text,
  figure_no     text,
  page_start    int  not null,
  page_end      int  not null,
  content       text not null,
  embedding     vector(1024),
  fts           tsvector generated always as
                  (to_tsvector('english', coalesce(content, ''))) stored,
  created_at    timestamptz not null default now()
);

create index if not exists chunks_embedding_idx
  on chunks using hnsw (embedding vector_cosine_ops);

create index if not exists chunks_fts_idx
  on chunks using gin (fts);

create index if not exists chunks_section_idx
  on chunks (section_no);

create index if not exists chunks_paragraph_idx
  on chunks (paragraph_id);

-- Rumus terkurasi dan terverifikasi untuk kalkulator deterministik.
create table if not exists formulas (
  id           bigint generated always as identity primary key,
  code         text unique not null,
  title        text not null,
  section_no   int  not null,
  paragraph_id text,
  page_no      int,
  expression   text not null,
  variables    jsonb not null,
  result_unit  text,
  notes        text,
  verified     boolean not null default false
);

create index if not exists formulas_section_idx
  on formulas (section_no);
