"""REPL-level mutable state shared between app.py and render.py.

Living in its own module to break the circular import between the REPL
loop (app.py) and the per-turn renderer (render.py): render.py needs to
read state.mode to know which ModeConfig to use, and app.py owns the
state lifetime.
"""
from dataclasses import dataclass, field
@dataclass
class AppState:
    """Mutable REPL state. Persists across turns until REPL exits.
    Fields are added incrementally by later phases; Fase 5b only
    consumes state.mode and writes state.history.
    """
    mode: str = "default"
    # Accumulated per-turn messages (well-formed: user + assistant alternating).
    # Windowing to 3-turns is deferred to Fase 5c.
    history: list[dict] = field(default_factory=list)
