"""Textual UI entrypoint for the local BKI Hull chatbot."""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from typing import Any

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.events import Key, Resize
from textual.message import Message
from textual.widgets import Button, Footer, Header, Label, Markdown, Static, TextArea

from src.llm.chain import chain_answer_stream
from src.llm.modes import MODES


@dataclass
class ChatTurn:
    role: str
    content: str
    sources: list[dict[str, Any]] | None = None
    timings: dict[str, float] | None = None


class TokenReceived(Message):
    def __init__(self, text: str) -> None:
        super().__init__()
        self.text = text


class StatusReceived(Message):
    def __init__(self, status: str) -> None:
        super().__init__()
        self.status = status


class AnswerReceived(Message):
    def __init__(self, result: Any) -> None:
        super().__init__()
        self.result = result


class StreamFailed(Message):
    def __init__(self, error: Exception) -> None:
        super().__init__()
        self.error = error


class Composer(TextArea):
    class Submitted(Message):
        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text

    def _resize_to_content(self) -> None:
        """Grow with the visible lines (1..3), scroll the viewport when full."""
        rows = max(1, self.document.line_count)
        self.styles.height = min(3, rows)
        if rows > 3:
            self.scroll_end()
        else:
            self.scroll_home()
        self.scroll_cursor_visible()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        self._resize_to_content()

    def on_mount(self) -> None:
        super().on_mount()
        self._resize_to_content()

    async def _on_key(self, event: Key) -> None:
        if event.key == "shift+enter":
            event.prevent_default()
            event.stop()
            self.insert("\n")
            self._resize_to_content()
            return
        if event.key in {"enter", "ctrl+m"}:
            event.prevent_default()
            event.stop()
            self.post_message(self.Submitted(self.text))
            return
        await super()._on_key(event)


class ChatApp(App[None]):
    """A single-process, responsive terminal chat application."""

    TITLE = "BKI Hull"
    CSS_PATH = "styles.tcss"
    BINDINGS = [
        ("ctrl+c", "confirm_quit", "Quit"),
        ("ctrl+l", "clear_chat", "Clear"),
        ("ctrl+y", "copy_last", "Copy answer"),
        ("ctrl+s", "toggle_sources", "Sources"),
    ]

    def __init__(self, mode: str = "default") -> None:
        super().__init__()
        self.mode = mode
        self.turns: list[ChatTurn] = []
        self.last_answer = ""
        self.last_sources: list[Any] = []
        self.streaming = False
        self._stream_buffer = ""
        self._streaming_widget: Markdown | None = None
        self._loading_widget: Static | None = None
        self._loading_started_at = 0.0
        self._loading_phase = "retrieving context"
        self._loading_frame = 0
        self._loading_timer = None
        self._sources_widget: Markdown | None = None
        self._quit_confirm_until = 0.0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="app-body"):
            with Vertical(id="sidebar"):
                yield Label("BKI HULL", id="brand")
                yield Static("Local rules assistant\nHull 2026", id="tagline")
                yield Button("+ New conversation", id="new-chat", variant="primary")
                yield Label("SESSION", classes="section-label")
                yield Static("Current conversation", id="session-label")
                yield Static("\nReady when you are.", id="sidebar-note")
            with Vertical(id="chat-column"):
                with VerticalScroll(id="transcript"):
                    yield Static(
                        "Ask about BKI Rules for Hull 2026.\n\n"
                        "Answers are grounded in the local rules database and show their sources.",
                        id="welcome",
                    )
                with Vertical(id="composer-row"):
                    with Vertical(id="composer-box"):
                        yield Composer(
                            text="",
                            placeholder="Ask BKI Hull rules...",
                            id="composer",
                            soft_wrap=True,
                            show_line_numbers=False,
                        )
                        with Horizontal(id="composer-actions"):
                            yield Static("Enter send · Shift+Enter newline", id="composer-hint")
                            yield Button("Send", id="send", variant="primary")
                with Horizontal(id="status-row"):
                    yield Label(f"mode: {self.mode}", id="mode-status")
                    yield Label("● services checking...", id="service-status")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#composer", TextArea).focus()

    def on_resize(self, event: Resize) -> None:
        """Collapse secondary controls when the terminal becomes narrow."""
        sidebar = self.query_one("#sidebar")
        sidebar.display = event.size.width > 90

    def on_composer_submitted(self, event: Composer.Submitted) -> None:
        self._submit(event.text)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "send":
            if self.streaming:
                self.action_stop()
            else:
                self._submit(self.query_one("#composer", TextArea).text)
        elif event.button.id == "new-chat":
            self.action_clear_chat()

    def _submit(self, value: str) -> None:
        value = value.strip()
        if not value or self.streaming:
            return
        if value.startswith("/"):
            self._command(value)
            self.query_one("#composer", TextArea).text = ""
            return
        self.query_one("#composer", TextArea).text = ""
        self.turns.append(ChatTurn("user", value))
        self._append_markdown(f"**You**\n\n{value}", "user-turn")
        self.streaming = True
        self._stream_buffer = ""
        self.query_one("#send", Button).disabled = True
        self.query_one("#send", Button).label = "■"
        self.query_one("#send", Button).disabled = False
        self._create_loading_widget()
        self._create_streaming_widget()
        self._run_query(value, list(self.turns))

    def _command(self, value: str) -> None:
        parts = value[1:].split(maxsplit=1)
        command = parts[0].lower() if parts else ""
        arg = parts[1].strip() if len(parts) > 1 else ""
        if command in {"exit", "quit"}:
            self.exit()
        elif command == "clear":
            self.action_clear_chat()
        elif command == "source":
            self.action_toggle_sources()
        elif command == "mode" and arg in MODES:
            self.mode = arg
            self.query_one("#mode-status", Label).update(f"mode: {arg}")
        elif command == "help":
            self._append_markdown(
                "**Commands**\n\n`/mode default`, `/mode fast`, `/source`, `/clear`, `/help`, `/exit`",
                "system-turn",
            )
        else:
            self._append_markdown(f"Unknown command: `{value}`", "system-turn")

    @work(thread=True, exclusive=True)
    def _run_query(self, query: str, history: list[ChatTurn]) -> None:
        backend_history = [
            {"role": turn.role, "content": turn.content}
            for turn in history[:-1]
        ]
        try:
            for kind, payload in chain_answer_stream(query, mode=self.mode, history=backend_history):
                if kind == "status":
                    self.post_message(StatusReceived(payload))
                elif kind == "token" and payload:
                    self.post_message(TokenReceived(payload))
                elif kind == "done":
                    self.post_message(AnswerReceived(payload))
                    return
            self.post_message(StreamFailed(RuntimeError("stream ended without an answer")))
        except Exception as error:
            self.post_message(StreamFailed(error))

    def on_token_received(self, event: TokenReceived) -> None:
        self._stream_buffer += event.text
        self._render_streaming()

    def on_status_received(self, event: StatusReceived) -> None:
        phase = {
            "pre_answer": "retrieving context",
            "answer_streaming": "generating answer",
        }.get(event.status, event.status.replace("_", " "))
        self._loading_phase = phase
        self._update_loading_widget()

    def on_answer_received(self, event: AnswerReceived) -> None:
        result = event.result
        answer = result.answer or self._stream_buffer
        self.last_answer = answer
        self.last_sources = list(result.sources or [])
        self.turns.append(ChatTurn("assistant", answer, self.last_sources, result.timings))
        self._remove_loading_widget()
        self._remove_streaming_widget()
        self._append_answer(result)
        self._finish_stream()

    def on_stream_failed(self, event: StreamFailed) -> None:
        self._remove_loading_widget()
        self._remove_streaming_widget()
        self._append_markdown(f"**Error**\n\n`{event.error}`", "error-turn")
        self._finish_stream()

    def _append_answer(self, result: Any) -> None:
        body = result.answer or "(no answer)"
        footer = ""
        if result.timings:
            total = result.timings.get("total")
            if total is not None:
                footer = f"\n\n---\n\n`{result.language}` · `{total:.1f}s`"
        self._append_markdown(f"**BKI**\n\n{body}{footer}", "assistant-turn")
        if result.sources and not result.rejected:
            self._append_sources(result.sources)

    def _append_markdown(self, content: str, class_name: str) -> None:
        transcript = self.query_one("#transcript", VerticalScroll)
        transcript.mount(Markdown(content, classes=class_name))
        transcript.scroll_end(animate=False)

    def _create_streaming_widget(self) -> None:
        """Mount one streaming widget; subsequent tokens only update it."""
        transcript = self.query_one("#transcript", VerticalScroll)
        self._streaming_widget = Markdown(
            "**BKI** · generating...\n\n...",
            classes="streaming-turn",
        )
        transcript.mount(self._streaming_widget)
        transcript.scroll_end(animate=False)

    def _create_loading_widget(self) -> None:
        transcript = self.query_one("#transcript", VerticalScroll)
        self._loading_started_at = time.monotonic()
        self._loading_frame = 0
        self._loading_phase = "retrieving context"
        self._loading_widget = Static(classes="loading-turn")
        transcript.mount(self._loading_widget)
        self._update_loading_widget()
        self._loading_timer = self.set_interval(0.35, self._tick_loading)
        transcript.scroll_end(animate=False)

    def _tick_loading(self) -> None:
        if self._loading_widget is None:
            return
        self._loading_frame = (self._loading_frame + 1) % 4
        self._update_loading_widget()

    def _update_loading_widget(self) -> None:
        if self._loading_widget is None:
            return
        frames = (".", "..", "...", "..")
        elapsed = int(time.monotonic() - self._loading_started_at)
        self._loading_widget.update(
            f"BKI  {frames[self._loading_frame]} {self._loading_phase}... {elapsed:02d}s"
        )

    def _remove_loading_widget(self) -> None:
        if self._loading_timer is not None:
            self._loading_timer.pause()
            self._loading_timer = None
        if self._loading_widget is not None:
            self._loading_widget.remove()
            self._loading_widget = None

    def _remove_streaming_widget(self) -> None:
        if self._streaming_widget is not None:
            self._streaming_widget.remove()
            self._streaming_widget = None

    def _append_sources(self, sources: list[Any]) -> None:
        self._remove_sources_widget()
        lines = ["**Sources**\n"]
        for index, source in enumerate(sources, 1):
            page = f"p.{source.page_start}" if source.page_start == source.page_end else f"pp.{source.page_start}-{source.page_end}"
            citation = f"Sec {source.section_no}"
            if source.paragraph_id:
                citation += f" | {source.paragraph_id}"
            lines.append(f"{index}. `{citation} {page}`  {source.section_title}")
        transcript = self.query_one("#transcript", VerticalScroll)
        self._sources_widget = Markdown("\n".join(lines), classes="sources-turn")
        transcript.mount(self._sources_widget)
        transcript.scroll_end(animate=False)

    def _remove_sources_widget(self) -> None:
        if self._sources_widget is not None:
            self._sources_widget.remove()
            self._sources_widget = None

    def _render_streaming(self) -> None:
        if self._streaming_widget is None:
            self._create_streaming_widget()
        self._streaming_widget.update(
            f"**BKI** · generating...\n\n{self._stream_buffer or '...'}"
        )

    def _finish_stream(self) -> None:
        self.streaming = False
        self._stream_buffer = ""
        self.query_one("#send", Button).disabled = False
        self.query_one("#send", Button).label = "Send"
        self.query_one("#composer", TextArea).focus()

    def action_stop(self) -> None:
        # The core generator is synchronous; worker cancellation prevents new
        # output and the UI remains usable. The backend process is unchanged.
        self.workers.cancel_all()
        self._remove_loading_widget()
        self._remove_streaming_widget()
        self._append_markdown("**Interrupted**", "system-turn")
        self._finish_stream()

    def action_confirm_quit(self) -> None:
        """Require a second Ctrl+C within two seconds to quit."""
        now = time.monotonic()
        if now <= self._quit_confirm_until:
            self.exit()
            return
        self._quit_confirm_until = now + 2.0
        self.notify("Press Ctrl+C again to quit", timeout=2.0)

    def action_clear_chat(self) -> None:
        self.turns.clear()
        self.last_answer = ""
        self.last_sources = []
        self._remove_sources_widget()
        transcript = self.query_one("#transcript", VerticalScroll)
        transcript.remove_children()
        transcript.mount(Static("New conversation started.", id="welcome"))

    def action_copy_last(self) -> None:
        if self.last_answer:
            self.copy_to_clipboard(self.last_answer)
            self.notify("Answer copied")

    def action_toggle_sources(self) -> None:
        if self.last_sources:
            self._append_sources(self.last_sources)
        else:
            self.notify("No sources for the last answer")


def main() -> None:
    parser = argparse.ArgumentParser(prog="bki-hull")
    parser.add_argument("--mode", choices=sorted(MODES), default="default")
    args = parser.parse_args()
    ChatApp(mode=args.mode).run()


if __name__ == "__main__":
    main()
