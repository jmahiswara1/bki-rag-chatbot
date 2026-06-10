import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_key: str = os.getenv("SUPABASE_KEY", "")
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    embed_model: str = os.getenv("EMBED_MODEL", "bge-m3")
    embed_dim: int = int(os.getenv("EMBED_DIM", "1024"))
    default_model: str = os.getenv("DEFAULT_MODEL", "qwen3.5:4b")
    fast_model: str = os.getenv("FAST_MODEL", "qwen2.5:3b-instruct")
    num_ctx: int = int(os.getenv("NUM_CTX", "8192"))
    tesseract_cmd: str = os.getenv("TESSERACT_CMD", "")
    reranker_model: str = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
    vlm_model: str = os.getenv("VLM_MODEL", "moondream")
    pdf_path: str = os.getenv("PDF_PATH", "data/bki_hull_2026.pdf")


settings = Settings()
