import os
os.environ.setdefault("USE_TF", "0")
os.environ['TF_USE_LEGACY_KERAS'] = '1'

from transformers import AutoModelForSequenceClassification

from FlagEmbedding import FlagReranker
from src.core.config import settings
from src.core.models import RetrievedChunk

_reranker = None


def _build_reranker() -> FlagReranker:
    """Construct FlagReranker, forcing low_cpu_mem_usage for the weight load.

    FlagReranker loads the model via AutoModelForSequenceClassification.
    from_pretrained with the DEFAULT safetensors mmap path, which crashed with
    a Windows access violation (0xC0000005) when loading the ~2.2 GB weights
    on a low-disk box. Loading with low_cpu_mem_usage=True uses a non-mmap
    path that does not crash (verified locally). The patch is transient: it is
    restored right after construction so no other transformers call site is
    affected.
    """
    original = AutoModelForSequenceClassification.from_pretrained

    def _patched(cls, *args, **kwargs):
        kwargs.setdefault("low_cpu_mem_usage", True)
        return original(cls, *args, **kwargs)

    AutoModelForSequenceClassification.from_pretrained = _patched
    try:
        return FlagReranker(settings.reranker_model, use_fp16=False)
    finally:
        AutoModelForSequenceClassification.from_pretrained = original


def get_reranker() -> FlagReranker:
    global _reranker
    if _reranker is None:
        # Lazy load BAAI/bge-reranker-v2-m3 globally on CPU
        _reranker = _build_reranker()
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
