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
    default_model: str = os.getenv("DEFAULT_MODEL", "qwen2.5:7b-instruct")
    fast_model: str = os.getenv("FAST_MODEL", "qwen2.5:3b-instruct")


settings = Settings()
