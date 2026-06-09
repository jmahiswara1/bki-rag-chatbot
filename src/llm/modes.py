from dataclasses import dataclass

from src.core.config import settings


@dataclass(frozen=True)
class ModeConfig:
    name: str
    model: str
    top_k: int
    rerank: bool
    temperature: float


MODES = {
    "default": ModeConfig("default", settings.default_model, top_k=8, rerank=True, temperature=0.2),
    "fast": ModeConfig("fast", settings.fast_model, top_k=4, rerank=False, temperature=0.3),
}
