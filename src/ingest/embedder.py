import ollama

from src.core.config import settings


def embed(text: str) -> list[float]:
    # bge-m3 dense embedding, 1024 dims, runs on CPU.
    client = ollama.Client(host=settings.ollama_host)
    resp = client.embeddings(model=settings.embed_model, prompt=text)
    return resp["embedding"]


def embed_batch(texts: list[str]) -> list[list[float]]:
    return [embed(t) for t in texts]
