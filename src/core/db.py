from functools import lru_cache

from supabase import Client, create_client

from src.cli.exceptions import SupabaseUnavailable
from src.core.config import settings


@lru_cache
def get_client() -> Client:
    """Get cached Supabase client. Raises SupabaseUnavailable on error."""
    if not settings.supabase_url or not settings.supabase_key:
        raise SupabaseUnavailable("SUPABASE_URL and SUPABASE_KEY must be set in .env")
    try:
        return create_client(settings.supabase_url, settings.supabase_key)
    except Exception as e:
        raise SupabaseUnavailable(f"Failed to create Supabase client: {e}") from e


def ping_supabase() -> None:
    """Verify Supabase connectivity with a lightweight query.
    
    Raises SupabaseUnavailable if connection fails.
    """
    try:
        client = get_client()
        # Lightweight ping: select 1 row from chunks table
        client.table("chunks").select("id").limit(1).execute()
    except SupabaseUnavailable:
        raise  # Re-raise if already our exception type
    except Exception as e:
        raise SupabaseUnavailable(f"Supabase ping failed: {e}") from e
