from typing import Iterator, Optional

import httpx
import ollama

from src.cli.exceptions import OllamaUnavailable
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


def check_ollama_available() -> None:
    """Verify Ollama connectivity and model availability.
    
    Raises OllamaUnavailable if:
    - Cannot connect to Ollama server
    - Required models are not available
    
    Returns None on success.
    """
    try:
        client = ollama.Client(host=settings.ollama_host)
        models_response = client.list()
        
        # Extract model names from response
        # Shape: ListResponse with .models attribute containing list of Model objects
        # Each Model has .model attribute (str) like "qwen2.5:3b-instruct" or "bge-m3:latest"
        available_models = []
        if hasattr(models_response, 'models'):
            for model_obj in models_response.models:
                if hasattr(model_obj, 'model'):
                    available_models.append(model_obj.model)
        
        # Check required models (loose matching: strip :latest, use startswith)
        required_models = [
            settings.default_model,
            settings.embed_model,
        ]
        
        for required in required_models:
            # Strip :latest suffix for comparison
            required_base = required.replace(":latest", "")
            
            # Check if any available model matches (startswith or exact match)
            found = False
            for available in available_models:
                available_base = available.replace(":latest", "")
                if available_base == required_base or available_base.startswith(required_base):
                    found = True
                    break
            
            if not found:
                raise OllamaUnavailable(
                    f"Required model '{required}' not found in Ollama. "
                    f"Available: {available_models}"
                )
    
    except (httpx.ConnectError, ConnectionError, httpx.HTTPError) as e:
        raise OllamaUnavailable(f"Cannot connect to Ollama at {settings.ollama_host}: {e}") from e
    except Exception as e:
        # Fallback catch-all for unexpected errors
        raise OllamaUnavailable(f"Ollama check failed: {e}") from e


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
    try:
        resp = client.chat(
            model=model,
            messages=messages,
            options=_options(num_ctx, temperature, max_tokens, think=think, keep_alive=keep_alive),
            stream=False,
        )
        return resp["message"]["content"]
    except (httpx.ConnectError, httpx.RemoteProtocolError, httpx.TimeoutException, ollama.ResponseError) as e:
        raise OllamaUnavailable(f"Ollama chat failed: {e}") from e


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
    try:
        stream = client.chat(
            model=model,
            messages=messages,
            options=_options(num_ctx, temperature, max_tokens, think=think, keep_alive=keep_alive),
            stream=True,
        )
        for part in stream:
            yield part["message"]["content"]
    except (httpx.ConnectError, httpx.RemoteProtocolError, httpx.TimeoutException, ollama.ResponseError) as e:
        raise OllamaUnavailable(f"Ollama streaming failed: {e}") from e
