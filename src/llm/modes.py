from dataclasses import dataclass

from src.core.config import settings


@dataclass(frozen=True)
class ModeConfig:
    name: str
    model: str
    top_k: int
    rerank: bool
    temperature: float
    answer_style: str = "detailed"


MODES = {
    # default: rerank ON, top_k=8, temp=0.2, detailed (multi-paragraph) answer
    "default": ModeConfig(
        "default", settings.default_model,
        top_k=8, rerank=True, temperature=0.2, answer_style="detailed",
    ),
    # fast: no rerank, top_k=4, temp=0.3, concise answer
    "fast": ModeConfig(
        "fast", settings.fast_model,
        top_k=4, rerank=False, temperature=0.3, answer_style="concise",
    ),
}
