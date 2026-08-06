# IMPORTANT (HANDOFF gotcha #2, Fase 3 carryover):
# On Windows, importing FlagEmbedding (via .rerank) BEFORE supabase
# (via .search) avoids a silent C-extension import-order crash (exit 1, no
# traceback). The order below is fragile. Keep rerank imports above search
# imports; do not reorder.

from src.core.models import RetrievedChunk
from src.ingest.embedder import embed, embed_batch
from src.retrieval.rerank import rerank_chunks
from src.retrieval.search import hybrid_search


def _mean_vectors(vecs: list[list[float]]) -> list[float]:
    # Average multi-query embeddings into a single vector (Fase 3).
    import numpy as np
    arr = np.array(vecs, dtype="float32")
    return arr.mean(axis=0).tolist()


def retrieve_context(
    query_text: str,
    mode: str = "default",
    *,
    fts_query: str | None = None,
    en_query: str | None = None,
    multi_queries: list[str] | None = None,
    vector_query: str | None = None,
) -> list[RetrievedChunk]:
    """Retrieve chunks based on the mode.

    Args:
        query_text: original user query (any language). Kept for back-compat
            when en_query and multi_queries are None.
        mode: 'default' (rerank, top 8 from 30) or 'fast' (no rerank, top 4).
        fts_query: text for the FTS branch (English, translated). Defaults to
            query_text when None.
        en_query: English version of the query. Used to build the vector
            embedding when vector_query is None.
        multi_queries: optional list of paraphrased English queries. When
            provided, their embeddings are averaged with the en_query embedding
            to form a single robust vector for one RPC call.
        vector_query: optional text for the vector branch ONLY (Build 41).
            When set, the embedding is built from this (typically the ORIGINAL
            user query in its source language) so a mistranslated en_query
            cannot drift the semantic direction (e.g. buritan -> 'bow').
            The FTS branch still uses fts_query/en_query as the English anchor.
    """
    fts_query_text = fts_query if fts_query is not None else query_text
    vector_source = vector_query if vector_query is not None else en_query

    if vector_source is not None and multi_queries:
        vectors = embed_batch([vector_source, *multi_queries])
        query_embedding = _mean_vectors(vectors)
    elif vector_source is not None:
        query_embedding = embed(vector_source)
    else:
        # Back-compat path: original code used query_text directly.
        query_embedding = embed(query_text)

    if mode == "fast":
        # Fast mode: small match_count, no reranking
        candidates = hybrid_search(query_embedding, fts_query_text, top_k=4)
    else:
        # Default mode: higher match_count for recall, then rerank for precision
        candidates = hybrid_search(query_embedding, fts_query_text, top_k=30)
        
    if mode == "fast":
        return candidates
    return rerank_chunks(fts_query_text, candidates, top_k=8)
