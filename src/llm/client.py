import ollama

from src.core.config import settings


def chat_stream(model: str, messages: list[dict], temperature: float):
    # Yield response tokens for streaming output in the CLI.
    client = ollama.Client(host=settings.ollama_host)
    stream = client.chat(
        model=model,
        messages=messages,
        options={
            "temperature": temperature,
            "num_ctx": settings.num_ctx,
        },
        stream=True,
    )
    for part in stream:
        yield part["message"]["content"]
