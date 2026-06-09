import ollama

from src.core.config import settings
from src.core.db import get_client


def check_ollama():
    client = ollama.Client(host=settings.ollama_host)
    models = client.list().get("models", [])
    names = [m.get("model") or m.get("name", "") for m in models]
    for required in [settings.embed_model, settings.default_model, settings.fast_model]:
        ok = any(n.startswith(required) for n in names)
        status = "OK" if ok else f"MISSING (run: ollama pull {required})"
        print(f"[ollama] {required}: {status}")


def check_supabase():
    try:
        client = get_client()
        client.table("chunks").select("id").limit(1).execute()
        print("[supabase] connection + chunks table: OK")
    except Exception as e:
        print(f"[supabase] FAILED: {e}")


if __name__ == "__main__":
    check_ollama()
    check_supabase()
