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
    # qwen3:4b & qwen3.5:4b rejected for 4GB VRAM (thinking models; Ollama ignores
    # think=False -> empty content 33-55%; CPU offload ~400-600s/answer). See PRD.
    # Locked to qwen2.5:3b-instruct for both modes (detailed/concise via modes.py).
    default_model: str = os.getenv("DEFAULT_MODEL", "qwen2.5:3b-instruct")
    fast_model: str = os.getenv("FAST_MODEL", "qwen2.5:3b-instruct")
    num_ctx: int = int(os.getenv("NUM_CTX", "8192"))
    tesseract_cmd: str = os.getenv("TESSERACT_CMD", "")
    reranker_model: str = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
    vlm_model: str = os.getenv("VLM_MODEL", "moondream")
    pdf_path: str = os.getenv("PDF_PATH", "data/bki_hull_2026.pdf")
    # Fase 3 settings
    reranker_max_length: int = int(os.getenv("RERANKER_MAX_LENGTH", "512"))
    translate_max_tokens: int = int(os.getenv("TRANSLATE_MAX_TOKENS", "200"))
    expand_n_queries: int = int(os.getenv("EXPAND_N_QUERIES", "2"))
    guardrail_top_gap: float = float(os.getenv("GUARDRAIL_TOP_GAP", "0.5"))
    guardrail_min_top_score: float = float(os.getenv("GUARDRAIL_MIN_TOP_SCORE", "-2.0"))
    # Multi-query expansion gate. Default False (single-query path).
    # Set to True in .env to enable averaged multi-query embedding.
    enable_multi_query: bool = os.getenv("ENABLE_MULTI_QUERY", "false").lower() == "true"

settings = Settings()
