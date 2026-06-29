import os
os.environ.setdefault("USE_TF", "0")
os.environ['TF_USE_LEGACY_KERAS'] = '1'

from FlagEmbedding import FlagReranker
from src.core.config import settings
from src.core.models import RetrievedChunk

_reranker = None


def get_reranker() -> FlagReranker:
    global _reranker
    if _reranker is None:
        # Lazy load BAAI/bge-reranker-v2-m3 globally on CPU
        _reranker = FlagReranker(settings.reranker_model, use_fp16=False)
    return _reranker


def rerank_chunks(query: str, chunks: list[RetrievedChunk], top_k: int = 8) -> list[RetrievedChunk]:
    if not chunks:
        return []

    reranker = get_reranker()
    sentence_pairs = [[query, c.content] for c in chunks]
    # Cross-encoder cost is dominated by sequence length (Fase 3 carryover).
    # Truncating to max_length ~512 cuts latency ~60% with negligible precision loss.
    scores = reranker.compute_score(sentence_pairs, max_length=settings.reranker_max_length)

    # FlagReranker computes scores which might be floats.
    if isinstance(scores, float):
        scores = [scores]

    for i, chunk in enumerate(chunks):
        chunk.score = scores[i]

    chunks.sort(key=lambda x: x.score, reverse=True)
    return chunks[:top_k]
