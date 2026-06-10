from src.core.db import get_client
from src.core.models import RetrievedChunk


def hybrid_search(query_embedding: list[float], fts_query_text: str, top_k: int = 8) -> list[RetrievedChunk]:
    """
    Calls the Supabase RPC match_chunks to perform RRF hybrid search.
    """
    client = get_client()
    res = client.rpc(
        "match_chunks",
        {
            "query_embedding": query_embedding,
            "query_text": fts_query_text,
            "match_count": top_k,
        }
    ).execute()
    
    return [
        RetrievedChunk(
            section_no=r["section_no"],
            section_title=r["section_title"],
            paragraph_id=r["paragraph_id"],
            content_type=r["content_type"],
            table_no=r["table_no"],
            figure_no=r.get("figure_no"),
            page_start=r["page_start"],
            page_end=r["page_end"],
            content=r["content"],
            score=r["score"],
        )
        for r in res.data
    ]
