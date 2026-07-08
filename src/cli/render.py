"""Per-turn renderer for the REPL.
Consumes the event stream from chain_answer_stream and renders it via
rich: spinner during pre-answer, streaming text during answer generation,
footer with mode/style/lang/timings, and a source panel (Sec | Title |
Para | Page | Type | Excerpt) for grounded answers.

Markup injection safety: every string that originates from the LLM or
from chunk content is wrapped in rich.text.Text(...) or
escaped. Only labels we own carry markup tags.
"""
from typing import Iterator
from rich.console import Console
from rich.live import Live
from rich.rule import Rule
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text
from src.cli.state import AppState
from src.llm.chain import ChainStreamResult, chain_answer_stream
from src.llm.modes import MODES
_TITLE_WIDTH = 18
_EXCERPT_WIDTH = 120
def _status_to_text(status: str) -> str:
    """Map a chain status event to a human label. Unknown statuses fall
    through to the raw payload so we never lose information.
    """
    if status == "pre_answer":
        return "  retrieving..."
    if status == "answer_streaming":
        return "  generating..."
    if status.startswith("stream_error:"):
        return f"  stream error: {status.split(':', 1)[1]}"
    return f"  {status}"
def _format_page(c) -> str:
    if c.page_start == c.page_end:
        return f"p.{c.page_start}"
    return f"pp.{c.page_start}-{c.page_end}"
def _excerpt(text: str) -> str:
    """Single-line excerpt; truncation uses an ellipsis char (safe in
    Text() -- no bracket interpretation (rich 13.x auto-escapes))."""
    # Strip a leading "[...]" context header if present, so the excerpt
    # does not repeat Sec/Title/Para already shown in their own columns.
    # Require a newline or whitespace immediately after "]" so we do not
    # truncate mid-sentence if the content is itself a single bracketed note.
    one_line = text
    if one_line.startswith("["):
        end = one_line.find("]")
        if end != -1 and end + 1 < len(one_line) and one_line[end + 1] in ("\n", " "):
            one_line = one_line[end + 1:].lstrip("\n").lstrip()
    one_line = one_line.replace("\n", " ").replace("\r", " ").strip()
    if len(one_line) > _EXCERPT_WIDTH:
        return one_line[:_EXCERPT_WIDTH] + "\u2026"
    return one_line


def excerpt(text: str) -> str:
    """Public API for _excerpt. Used by /source command."""
    return _excerpt(text)


def _truncate_title(title: str) -> str:
    if len(title) <= _TITLE_WIDTH:
        return title
    return title[: _TITLE_WIDTH - 1] + "\u2026"
def _render_source_panel(sources: list, console: Console) -> None:
    """Render sources table with a Rule separator. Sources are model-derived
    and may contain arbitrary characters; everything dynamic goes through
    Text with markup=False (or str() for purely numeric fields)."""
    console.print(Rule(f"Sources ({len(sources)})", style="dim cyan"))
    table = Table(
        box=None,
        show_header=True,
        header_style="bold",
    )
    table.add_column("Sec",     style="cyan",    no_wrap=True, width=6)
    table.add_column("Title",   style="magenta", no_wrap=True, width=_TITLE_WIDTH)
    table.add_column("Para",    style="dim",     no_wrap=True, width=12)
    table.add_column("Page",    style="dim",     no_wrap=True, width=8)
    table.add_column("Type",    style="dim",     no_wrap=True, width=10)
    table.add_column("Excerpt", style="",        no_wrap=False)
    for c in sources:
        table.add_row(
            Text(str(c.section_no)),
            Text(_truncate_title(c.section_title or "")),
            Text(c.paragraph_id or "-"),
            Text(_format_page(c)),
            Text(c.content_type or "-"),
            Text(_excerpt(c.content or "")),
        )
    console.print(table)
def _seconds_for(timings: dict, key: str) -> float | None:
    """Return timings[key] as float, or None if absent/non-numeric."""
    if not timings:
        return None
    v = timings.get(key)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
def _render_footer(result: ChainStreamResult, mode: str, console: Console) -> None:
    """Footer: mode | style | lang | answer=<stream-or-answer>s total=<total>s,
    plus rejected hint ONLY when applicable. The answer slot uses the
    streaming-path key 'stream' (or non-stream fallback 'answer'); the
    total slot is always present at the end of any chain run."""
    cfg = MODES[mode]
    timings = result.timings or {}
    ans_s = _seconds_for(timings, "stream")
    if ans_s is None:
        ans_s = _seconds_for(timings, "answer")
    total_s = _seconds_for(timings, "total")
    parts: list[str] = [f"mode={mode}", f"style={cfg.answer_style}", f"lang={result.language}"]
    if ans_s is not None:
        parts.append(f"answer={ans_s:.1f}s")
    if total_s is not None:
        parts.append(f"total={total_s:.1f}s")
    if result.rejected:
        parts.append(f"rejected: {result.reject_reason}")
    console.print(Rule("  ".join(parts), style="dim cyan"))
def render_turn(query: str, state: AppState, console: Console, history: list | None = None) -> ChainStreamResult:
    """Execute one REPL turn: stream the chain, render live, finalize.

    Args:
        query: User's question
        state: Application state (mode, etc.)
        console: Rich console for output
        history: Optional history to use (if None, uses state.history)

    Returns the final ChainStreamResult so the caller can update its
    history (well-formed user + assistant turn).
    """
    if history is None:
        history = state.history
    gen: Iterator = chain_answer_stream(query, mode=state.mode, history=history)
    accumulated: list[str] = []
    in_stream = False
    final: ChainStreamResult | None = None
    with Live(
        Spinner("dots", text="  retrieving..."),
        console=console,
        refresh_per_second=8,
        transient=True,
    ) as live:
        for kind, payload in gen:
            if kind == "status":
                live.update(Spinner("dots", text=_status_to_text(payload)))
            elif kind == "token":
                if not in_stream:
                    # First token: switch from spinner to live text render.
                    # We still keep the Live context so subsequent tokens update.
                    in_stream = True
                if payload:
                    accumulated.append(payload)
                live.update(Text("".join(accumulated)))
            elif kind == "done":
                final = payload
                break
        # Live exits transiently; below we re-print the final answer so it
        # stays visible (Live with transient=True erases the rendered frame).
    console.print()  # trailing newline after Live
    if final is None:
        console.print("[red]error:[/red] stream ended without a done event")
        # Caller will still append user turn; we surface a marker for assistant.
        return ChainStreamResult(
            answer="",
            sources=[],
            intent=None,  # type: ignore[arg-type]
            language="unknown",
            timings={},
        )
    # Final answer with Rule separator above. Use Text() because the
    # content is model-derived and may contain '[' / ']' which would
    # otherwise be interpreted as rich markup.
    console.print(Rule("Answer", style="dim cyan"))
    console.print(Text(final.answer or ""))
    # Source panel: WAJIB for grounded answers (sources non-kosong);
    # SKIP for calc stub and guardrail reject (sources == [] or rejected).
    if final.sources and not final.rejected:
        _render_source_panel(final.sources, console)
    elif final.rejected:
        # Reason lives in the footer; keep panel absent.
        pass
    # else (calc stub, sources=[]): nothing -- intentional, per spec.
    _render_footer(final, state.mode, console)
    return final
