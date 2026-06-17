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
    # default: rerank ON, top_k=8, temp=0.0 (deterministic), detailed answer.
    # temp=0.0 for the final-answer LLM is intentional: manual QA over 26
    # questions showed 25/26 NONDETERMINISTIC at temp=0.2. Retrieval is
    # already deterministic post-embedding, and utility calls
    # (classify_with_llm, _expand) also benefit from temp=0.0. _translate_condense
    # is unaffected -- it caps its own temperature at 0.1 internally.
    "default": ModeConfig(
        "default", settings.default_model,
        top_k=8, rerank=True, temperature=0.0, answer_style="detailed",
    ),
    # fast: no rerank, top_k=4, temp=0.3, concise answer
    "fast": ModeConfig(
        "fast", settings.fast_model,
        top_k=4, rerank=False, temperature=0.3, answer_style="concise",
    ),
}
