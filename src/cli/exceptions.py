"""Custom exceptions for BKI RAG Chatbot CLI.

Exception hierarchy:
    CLIError (base)
    ├── OllamaUnavailable
    ├── SupabaseUnavailable
    └── RetrievalError
"""


class CLIError(Exception):
    """Base exception for CLI-specific errors."""
    pass


class OllamaUnavailable(CLIError):
    """Ollama service is not reachable or not responding."""
    pass


class SupabaseUnavailable(CLIError):
    """Supabase service is not reachable or authentication failed."""
    pass


class RetrievalError(CLIError):
    """Retrieval pipeline failed (after retries exhausted)."""
    pass
