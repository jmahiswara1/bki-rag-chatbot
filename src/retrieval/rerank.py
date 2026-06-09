from src.core.models import RetrievedChunk


def rerank(query: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    # Used in default mode. Phase 2: add a cross-encoder or LLM reranker.
    # Identity passthrough for now.
    return chunks
