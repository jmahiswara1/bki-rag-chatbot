"""Fase 5c REPL CLI with slash-commands and history windowing.

Scope (5c):
  - argparse launch arg --mode {default,fast}
  - prompt_toolkit PromptSession loop with completer
  - per-turn render via render.render_turn
  - slash-commands: /help, /mode, /source, /clear, /exit, /quit
  - history windowing: last 3 turns (6 messages) sent to chain
  - Ctrl-C inside a turn: print '(cancelled)' and stay in REPL
  
Deferred:
  - full error handling             -> 5d
"""
import argparse
import sys

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import NestedCompleter
from rich.console import Console
from rich.rule import Rule

from src.cli.commands import HELP_TEXT, parse_command
from src.cli.render import excerpt, render_turn
from src.cli.state import AppState
from src.llm.modes import MODES
from src.llm.prompts import format_citation


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
        "[dim]exit: Ctrl-D, 'exit', or 'quit' | type /help for commands[/dim]"
    )
    console.print()


def _handle_mode_command(arg: str, state: AppState, console: Console) -> None:
    """Handle /mode [default|fast] command."""
    if not arg:
        # Show current mode
        console.print(f"[dim]Current mode: {state.mode}[/dim]")
        return
    
    if arg in MODES:
        state.mode = arg
        console.print(f"[dim]Mode changed to: {arg}[/dim]")
    else:
        console.print(f"[red](unknown mode: {arg})[/red]")


def _handle_source_command(state: AppState, console: Console) -> None:
    """Handle /source command - show sources from last turn."""
    if state.last_result is None or not state.last_result.sources:
        console.print("[dim](no sources yet)[/dim]")
        return
    
    console.print("[bold]Sources from last answer:[/bold]")
    for i, src in enumerate(state.last_result.sources, 1):
        citation = format_citation(src)
        excerpt_text = excerpt(src.content)
        # Truncate excerpt for display
        if len(excerpt_text) > 100:
            excerpt_text = excerpt_text[:100] + "..."
        console.print(f"  {i}. {citation}")
        console.print(f"     [dim]{excerpt_text}[/dim]")


def _handle_clear_command(state: AppState, console: Console) -> None:
    """Handle /clear command - clear conversation history."""
    state.history.clear()
    state.last_result = None
    console.print("[dim](history cleared)[/dim]")


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
    
    # Setup completer for slash commands
    completer = NestedCompleter.from_nested_dict({
        '/help': None,
        '/mode': {'default': None, 'fast': None},
        '/source': None,
        '/clear': None,
        '/exit': None,
        '/quit': None,
    })
    
    session: PromptSession[str] = PromptSession("> ", completer=completer)

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
        
        # Handle slash commands
        if text.startswith("/"):
            cmd_name, cmd_arg = parse_command(text)
            if cmd_name == "help":
                console.print(HELP_TEXT)
            elif cmd_name == "mode":
                _handle_mode_command(cmd_arg, state, console)
            elif cmd_name == "source":
                _handle_source_command(state, console)
            elif cmd_name == "clear":
                _handle_clear_command(state, console)
            elif cmd_name in ("exit", "quit"):
                break
            else:
                console.print(f"[red](unknown command: /{cmd_name})[/red]")
            continue

        # Well-formed turn: render, then append to history if successful.
        # History windowing: send last 3 turns (6 messages) to chain.
        windowed_history = state.history[-6:] if len(state.history) > 6 else state.history
        
        try:
            result = render_turn(text, state, console=console, history=windowed_history)
        except KeyboardInterrupt:
            # Per spec: Ctrl-C during render must not kill the REPL.
            console.print("[dim](cancelled)[/dim]")
            console.print()
            # Don't append anything to history on cancel.
            continue
        
        # Only append to history if we got a successful result with answer and sources.
        # Robust filter: don't append short-circuit turns (rejected/calc-stub/no-sources).
        if result is not None and result.answer and result.sources and not result.rejected:
            state.history.append({"role": "user", "content": text})
            state.history.append({"role": "assistant", "content": result.answer})
            state.last_result = result
        
        console.print(Rule(style="dim"))
