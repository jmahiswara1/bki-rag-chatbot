from rich.console import Console
"""Fase 5b REPL CLI (int).
Scope (5b):
  - argparse launch arg --mode {default,fast}
  - prompt_toolkit PromptSession loop
  - per-turn render via render.render_turn
  - exit on Ctrl-D / 'exit' / 'quit'
  - Ctrl-C inside a turn: print '(cancelled)' and stay in REPL
  - history: append user + assistant (well-formed)
Deferred:
  - /mode, /source, /clear, /help -> 5c
  - history windowing (3 turns)   -> 5c
  - full error handling             -> 5d
"""
import argparse
import sys

from prompt_toolkit import PromptSession
from rich.console import Console
from rich.rule import Rule

from src.cli.render import render_turn
from src.cli.state import AppState
from src.llm.modes import MODES


def _parse_args(argv: list[str] | None = None) -> str:
    p = argparse.ArgumentParser(prog="bki-rag", add_help=True)
    p.add_argument("--mode", choices=sorted(MODES.keys()), default="default")
    args = p.parse_args(argv)
    return args.mode


def _print_header(console: Console, mode: str) -> None:
    cfg = MODES[mode]
    console.print(
        f"[bold]BKI Hull RAG[/bold]  mode={mode}  "
        f"model={cfg.model}  rerank={cfg.rerank}"
    )
    console.print(
        "[dim]exit: Ctrl-D, 'exit', or 'quit' | "
        "/commands deferred to 5c | full error handling deferred to 5d[/dim]"
    )
    console.print()


def run(argv: list[str] | None = None) -> None:
    """Entry point invoked by main.py with sys.argv[1:]."""
    # Force UTF-8 on stdio so model output containing ≥, σ, ·, √, etc.
    # does not crash Windows cp1252. Best-effort; ignored if the running
    # Python does not support reconfigure (e.g. some embedded interpreters).
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    console = Console()
    mode = _parse_args(argv)
    if mode not in MODES:
        # argparse already rejects unknown choices; this is a defense-in-depth.
        raise SystemExit(f"unknown mode: {mode!r}")
    state = AppState(mode=mode)
    session: PromptSession[str] = PromptSession("> ")

    _print_header(console, mode)

    while True:
        try:
            text = session.prompt()
        except KeyboardInterrupt:
            # Ctrl-C while idle: ignore and redraw prompt.
            continue
        except EOFError:
            # Ctrl-D / Ctrl-Z+Enter: graceful exit.
            break

        text = text.strip()
        if not text:
            continue
        if text in ("exit", "quit"):
            break
        # /commands deferred to 5c; ignore silently for now.
        if text.startswith("/"):
            console.print("[dim](/commands deferred to 5c)[/dim]")
            continue

        # Well-formed turn: append user, render, append assistant.
        state.history.append({"role": "user", "content": text})
        try:
            result = render_turn(text, state, console=console)
        except KeyboardInterrupt:
            # Per spec: Ctrl-C during render must not kill the REPL.
            console.print("[dim](cancelled)[/dim]")
            console.print()
            # Remove the orphaned user turn to keep history well-formed.
            if state.history and state.history[-1].get("role") == "user":
                state.history.pop()
            console.print(Rule(style="dim"))
            continue
        if result is not None and result.answer:
            state.history.append({"role": "assistant", "content": result.answer})
        console.print(Rule(style="dim"))
