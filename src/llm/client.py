from typing import Iterator, Optional

import ollama

from src.core.config import settings


def _options(
    num_ctx: int,
    temperature: float,
    max_tokens: Optional[int] = None,
    think: bool = False,
    keep_alive: str | int = "5m",
) -> dict:
    # Build Ollama options dict. num_ctx is mandatory per HANDOFF Fase 3 req #7.
    # think=False is the safe default; reasoning models place output in
    # resp["message"]["thinking"] when think=True, leaving content="" for
    # non-streaming callers. Utility calls must pass think=False (AGENTS.md).
    # keep_alive: keep model loaded for N duration so qwen3.5:4b does not
    # unload between calls on a 4GB-VRAM box (Fase 3 closeout: Test G robustness).
    opt: dict = {"temperature": temperature, "num_ctx": num_ctx, "keep_alive": keep_alive}
    if max_tokens is not None:
        opt["num_predict"] = max_tokens
    opt["think"] = think
    return opt


def chat(
    model: str,
    messages: list[dict],
    *,
    num_ctx: int = settings.num_ctx,
    temperature: float = 0.2,
    max_tokens: Optional[int] = None,
    think: bool = False,
    keep_alive: str | int = "5m",
) -> str:
    # Non-streaming chat. Explicit num_ctx per Fase 3 req #7.
    # Used for condense/translate, intent fallback, and multi-query expansion.
    # Default think=False per AGENTS.md hard rule (utility calls disable thinking).
    client = ollama.Client(host=settings.ollama_host)
    resp = client.chat(
        model=model,
        messages=messages,
        options=_options(num_ctx, temperature, max_tokens, think=think, keep_alive=keep_alive),
        stream=False,
    )
    return resp["message"]["content"]


def chat_stream(
    model: str,
    messages: list[dict],
    temperature: float,
    *,
    num_ctx: int = settings.num_ctx,
    max_tokens: Optional[int] = None,
    think: bool = False,
    keep_alive: str | int = "5m",
) -> Iterator[str]:
    # Streaming chat. Yields response tokens for the user-facing answer.
    # Default think=False so reasoning-model tokens do not leak to the user.
    client = ollama.Client(host=settings.ollama_host)
    stream = client.chat(
        model=model,
        messages=messages,
        options=_options(num_ctx, temperature, max_tokens, think=think, keep_alive=keep_alive),
        stream=True,
    )
    for part in stream:
        yield part["message"]["content"]
