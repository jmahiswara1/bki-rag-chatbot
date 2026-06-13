"""REPL-level mutable state shared between app.py and render.py.

Living in its own module to break the circular import between the REPL
loop (app.py) and the per-turn renderer (render.py): render.py needs to
read state.mode to know which ModeConfig to use, and app.py owns the
state lifetime.
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.llm.chain import ChainStreamResult

from dataclasses import dataclass, field


@dataclass
class AppState:
    """Mutable REPL state. Persists across turns until REPL exits.
    
    Fields:
        mode: Current answer mode (default/fast)
        history: Accumulated conversation messages (user + assistant alternating)
        last_result: Result from the last successful turn (for /source command)
    """
    mode: str = "default"
    # Accumulated per-turn messages (well-formed: user + assistant alternating).
    # Windowing: only last 3 turns (6 messages) sent to chain.
    history: list[dict] = field(default_factory=list)
    # Result from last successful turn (for /source command).
    # None if no turns yet, or last turn was short-circuit (rejected/calc-stub).
    last_result: "ChainStreamResult | None" = None
