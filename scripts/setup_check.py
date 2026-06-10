import ollama
import shutil

from src.core.config import settings
from src.core.db import get_client


def check_ollama():
    client = ollama.Client(host=settings.ollama_host)
    models = client.list().get("models", [])
    names = [m.get("model") or m.get("name", "") for m in models]
    for required in [settings.embed_model, settings.default_model, settings.fast_model, settings.vlm_model]:
        ok = any(n.startswith(required) for n in names)
        status = "OK" if ok else f"MISSING (run: ollama pull {required})"
        print(f"[ollama] {required}: {status}")


def check_supabase():
    if not settings.supabase_url.startswith("https://"):
        print("[supabase] URL FAILED: Must start with https:// (REST API)")
        return
    try:
        client = get_client()
        client.table("chunks").select("id").limit(1).execute()
        client.table("formulas").select("id").limit(1).execute()
        print("[supabase] connection + tables (chunks, formulas): OK")
    except Exception as e:
        print(f"[supabase] FAILED: {e}")

def check_tesseract():
    cmd = settings.tesseract_cmd or shutil.which("tesseract")
    if cmd:
        print("[tesseract] OK")
    else:
        print("[tesseract] MISSING (install tesseract or set TESSERACT_CMD)")


if __name__ == "__main__":
    check_ollama()
    check_supabase()
    check_tesseract()
