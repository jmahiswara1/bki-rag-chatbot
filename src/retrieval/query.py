from src.core.models import RetrievedChunk
from src.ingest.embedder import embed
from src.retrieval.rerank import rerank_chunks
from src.retrieval.search import hybrid_search

def retrieve_context(query_text: str, mode: str = "default") -> list[RetrievedChunk]:
    """
    Retrieve chunks based on the mode.
    Fast mode: no reranking, top 4.
    Default mode: reranking, top 8 from pool of 20.
    """
    query_embedding = embed(query_text)
    
    # Phase 3 will handle ID->EN translation for FTS. For now, use raw query_text.
    fts_query_text = query_text
    
    if mode == "fast":
        # Fast mode: small match_count, no reranking
        return hybrid_search(query_embedding, fts_query_text, top_k=4)
    else:
        # Default mode: higher match_count for recall, then rerank for precision
        candidate_chunks = hybrid_search(query_embedding, fts_query_text, top_k=20)
        return rerank_chunks(query_text, candidate_chunks, top_k=8)
