-- 002_match_chunks.sql
-- Hybrid search: gabungan ranking vektor (cosine) dan full-text (ts_rank)
-- dengan Reciprocal Rank Fusion (RRF). Jalankan setelah 001_init.sql.

create or replace function match_chunks(
  query_embedding vector(1024),
  query_text      text,
  match_count     int default 8,
  rrf_k           int default 50
)
returns table (
  id            bigint,
  section_no    int,
  section_title text,
  paragraph_id  text,
  content_type  text,
  table_no      text,
  figure_no     text,
  page_start    int,
  page_end      int,
  content       text,
  score         float
)
language sql stable
as $$
  with vector_ranked as (
    select
      c.id,
      row_number() over (
        order by c.embedding <=> query_embedding
      ) as rank
    from chunks c
    where c.embedding is not null
    order by c.embedding <=> query_embedding
    limit greatest(match_count * 4, 40)
  ),
  fts_ranked as (
    select
      c.id,
      row_number() over (
        order by ts_rank(c.fts, websearch_to_tsquery('english', query_text)) desc
      ) as rank
    from chunks c
    where c.fts @@ websearch_to_tsquery('english', query_text)
    limit greatest(match_count * 4, 40)
  ),
  fused as (
    select
      coalesce(v.id, f.id) as id,
      coalesce(1.0 / (rrf_k + v.rank), 0.0)
        + coalesce(1.0 / (rrf_k + f.rank), 0.0) as score
    from vector_ranked v
    full outer join fts_ranked f on v.id = f.id
  )
  select
    c.id,
    c.section_no,
    c.section_title,
    c.paragraph_id,
    c.content_type,
    c.table_no,
    c.figure_no,
    c.page_start,
    c.page_end,
    c.content,
    fused.score
  from fused
  join chunks c on c.id = fused.id
  order by fused.score desc
  limit match_count;
$$;
