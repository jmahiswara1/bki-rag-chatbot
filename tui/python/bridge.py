"""Python bridge for Ink TUI. Reads JSON from stdin, writes JSON to stdout.

Protocol:
  Input (from Node.js):
    {"type": "query", "content": "...", "mode": "default"}
    {"type": "mode", "content": "fast"}
    {"type": "clear"}
    {"type": "check_services"}
    {"type": "ping"}
    {"type": "cancel"}

  Output (to Node.js):
    {"type": "status", "content": "pre_answer"}
    {"type": "token", "content": "..."}
    {"type": "done", "answer": "...", "sources": [...], "language": "...", ...}
    {"type": "mode_changed", "content": "fast"}
    {"type": "cleared"}
    {"type": "services", "ollama": true, "supabase": true}
    {"type": "cancelled"}
    {"type": "pong"}
"""
import sys
import json
import os

# Force UTF-8 on stdio
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# Add project root to path so imports work regardless of cwd
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.cli.format import format_for_cli
from src.cli.state import AppState
from src.llm.chain import chain_answer_stream

# Cancel flag — set by handle_cancel(), checked by handle_query()
_cancelled = False

_EXCERPT_WIDTH = 120


def _final_text(result) -> str:
    """Return the answer text formatted for terminal display."""
    return format_for_cli(getattr(result, "answer", "") or "")


def _excerpt(text: str) -> str:
    """Strip context header dan truncate ke 120 char + ellipsis.
    Konsisten dengan CLI lama (src/cli/render.py)."""
    one_line = text

    # Strip leading "[...]" context header if present
    # Require a newline or whitespace immediately after "]"
    if one_line.startswith("["):
        end = one_line.find("]")
        if end != -1 and end + 1 < len(one_line) and one_line[end + 1] in ("\n", " "):
            one_line = one_line[end + 1:].lstrip("\n").lstrip()

    # Flatten ke single line
    one_line = one_line.replace("\n", " ").replace("\r", " ").strip()

    # Truncate ke 120 char + ellipsis
    if len(one_line) > _EXCERPT_WIDTH:
        return one_line[:_EXCERPT_WIDTH] + "\u2026"

    return one_line


def handle_query(msg: dict, state: AppState) -> None:
    global _cancelled
    _cancelled = False

    query = msg["content"]
    mode = msg.get("mode", state.mode)
    if mode != state.mode and mode in ("default", "fast"):
        state.mode = mode

    windowed = state.history[-6:] if len(state.history) > 6 else state.history

    try:
        for kind, payload in chain_answer_stream(query, mode=state.mode, history=windowed):
            if _cancelled:
                emit({"type": "cancelled"})
                break

            if kind == "status":
                emit({"type": "status", "content": payload})
            elif kind == "token":
                if payload:
                    emit({"type": "token", "content": payload})
            elif kind == "done":
                result = payload
                sources = []
                for s in (result.sources or []):
                    sources.append({
                        "section_no": s.section_no,
                        "section_title": s.section_title or "",
                        "paragraph_id": s.paragraph_id or "",
                        "page_start": s.page_start,
                        "page_end": s.page_end,
                        "content": _excerpt(s.content or ""),
                        "content_type": s.content_type or "",
                    })

                emit({
                    "type": "done",
                    "answer": result.answer or "",
                    "final": _final_text(result),
                    "sources": sources,
                    "language": result.language or "unknown",
                    "rejected": bool(result.rejected),
                    "reject_reason": result.reject_reason or "",
                    "timings": result.timings or {},
                })

                if result.answer and result.sources and not result.rejected:
                    state.history.append({"role": "user", "content": query})
                    state.history.append({"role": "assistant", "content": result.answer})
                break
    except Exception as e:
        if not _cancelled:
            emit({"type": "error", "content": str(e)})


def handle_mode(msg: dict, state: AppState) -> None:
    mode = msg.get("content", "")
    if mode in ("default", "fast"):
        state.mode = mode
        emit({"type": "mode_changed", "content": state.mode})
    else:
        emit({"type": "error", "content": f"Unknown mode: {mode}"})


def handle_clear(state: AppState) -> None:
    state.history.clear()
    state.last_result = None
    emit({"type": "cleared"})


def handle_cancel() -> None:
    global _cancelled
    _cancelled = True


def handle_check_services() -> None:
    ollama_ok = False
    supabase_ok = False

    try:
        from src.llm.client import check_ollama_available
        check_ollama_available()
        ollama_ok = True
    except Exception:
        pass

    try:
        from src.core.db import ping_supabase
        ping_supabase()
        supabase_ok = True
    except Exception:
        pass

    emit({"type": "services", "ollama": ollama_ok, "supabase": supabase_ok})

    # Also emit config info
    try:
        from src.core.config import settings
        emit({
            "type": "config",
            "model": settings.default_model,
            "mode": "default",
        })
    except Exception:
        pass


def emit(msg: dict) -> None:
    try:
        print(json.dumps(msg, ensure_ascii=False), flush=True)
    except Exception:
        pass


def main() -> None:
    state = AppState(mode="default")

    # Signal ready
    emit({"type": "ready"})

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue

        msg_type = msg.get("type", "")

        if msg_type == "query":
            handle_query(msg, state)
        elif msg_type == "mode":
            handle_mode(msg, state)
        elif msg_type == "clear":
            handle_clear(state)
        elif msg_type == "cancel":
            handle_cancel()
        elif msg_type == "check_services":
            handle_check_services()
        elif msg_type == "ping":
            emit({"type": "pong"})
        elif msg_type == "exit":
            break


if __name__ == "__main__":
    main()
