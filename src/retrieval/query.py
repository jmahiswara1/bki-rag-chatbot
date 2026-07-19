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
) -> list[RetrievedChunk]:
    """Retrieve chunks based on the mode.

    Args:
        query_text: original user query (any language). Kept for back-compat
            when en_query and multi_queries are None.
        mode: 'default' (rerank, top 8 from 20) or 'fast' (no rerank, top 4).
        fts_query: text for the FTS branch (English, translated). Defaults to
            query_text when None.
        en_query: English version of the query. Used to build the vector
            embedding (so the vector branch sees English, matching FTS).
        multi_queries: optional list of paraphrased English queries. When
            provided, their embeddings are averaged with the en_query embedding
            to form a single robust vector for one RPC call.
    """
    fts_query_text = fts_query if fts_query is not None else query_text

    if en_query is not None and multi_queries:
        vectors = embed_batch([en_query, *multi_queries])
        query_embedding = _mean_vectors(vectors)
    elif en_query is not None:
        query_embedding = embed(en_query)
    else:
        # Back-compat path: original code used query_text directly.
        query_embedding = embed(query_text)

    if mode == "fast":
        # Fast mode: small match_count, no reranking
        candidates = hybrid_search(query_embedding, fts_query_text, top_k=4)
    else:
        # Default mode: higher match_count for recall, then rerank for precision
        candidates = hybrid_search(query_embedding, fts_query_text, top_k=20)
        
    # Build 32b: Hot-patch mislabeled Table 35.2 chunk (chunk 1208 in DB,
    # identified by its unique content signature).
    for c in candidates:
        if (c.table_no == "35.1" and c.content_type == "table"
                and '"COLL"-Notation | v*' in c.content):
            c.table_no = "35.2"
            c.content = c.content.replace("| Table 35.1]", "| Table 35.2]", 1)
            
    if mode == "fast":
        return candidates
    return rerank_chunks(fts_query_text, candidates, top_k=8)
