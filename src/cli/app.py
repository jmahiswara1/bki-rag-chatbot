from rich.console import Console

from src.cli.commands import HELP_TEXT
from src.llm.modes import MODES

console = Console()


def run():
    # Phase 5: REPL loop with prompt_toolkit input, mode switch,
    # retrieval + streaming chat, and source display.
    console.print("[bold]BKI Hull RAG[/bold]  (mode: default)")
    console.print(HELP_TEXT)
    raise NotImplementedError("Phase 5: implement the interactive CLI loop")
