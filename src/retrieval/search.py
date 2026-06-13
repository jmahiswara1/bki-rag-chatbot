import time

import httpx

from src.cli.exceptions import RetrievalError
from src.core.db import get_client
from src.core.models import RetrievedChunk

# Exceptions that warrant a retry (transient network / server reset).
_RETRYABLE = (httpx.RemoteProtocolError, httpx.ConnectError, httpx.ReadError)
_RETRY_DELAYS = (0.5, 1.0, 2.0)  # exponential backoff in seconds


def hybrid_search(
    query_embedding: list[float],
    fts_query_text: str,
    top_k: int = 8,
) -> list[RetrievedChunk]:
    """Call the Supabase RPC match_chunks (RRF hybrid search) with retry.

    Retries up to 3 times on transient httpx connection/protocol errors with
    exponential backoff (0.5s, 1.0s, 2.0s). get_client() is lru_cached so the
    Supabase client instance is reused across calls.
    """
    last_exc: Exception | None = None
    for attempt, delay in enumerate((*_RETRY_DELAYS, None), start=1):
        try:
            client = get_client()
            res = client.rpc(
                "match_chunks",
                {
                    "query_embedding": query_embedding,
                    "query_text": fts_query_text,
                    "match_count": top_k,
                },
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
        except _RETRYABLE as exc:
            last_exc = exc
            if delay is None:
                break
            print(f"  [hybrid_search] attempt {attempt} failed ({type(exc).__name__}), retrying in {delay}s")
            time.sleep(delay)
    raise RetrievalError(f"hybrid_search failed after {len(_RETRY_DELAYS)+1} attempts") from last_exc
