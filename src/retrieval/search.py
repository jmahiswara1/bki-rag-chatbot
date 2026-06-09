from src.core.db import get_client
from src.core.models import RetrievedChunk
from src.ingest.embedder import embed


def search(query: str, top_k: int = 8) -> list[RetrievedChunk]:
    # Hybrid retrieval via the match_chunks RPC (vector + full-text, RRF).
    client = get_client()
    emb = embed(query)
    resp = client.rpc(
        "match_chunks",
        {"query_embedding": emb, "query_text": query, "match_count": top_k},
    ).execute()
    return [
        RetrievedChunk(
            section_no=r["section_no"],
            section_title=r["section_title"],
            paragraph_id=r["paragraph_id"],
            content_type=r["content_type"],
            table_no=r["table_no"],
            page_start=r["page_start"],
            page_end=r["page_end"],
            content=r["content"],
            score=r["score"],
        )
        for r in resp.data
    ]
