import asyncio
import time

from src.tui.app import ChatApp, Composer, StatusReceived, TokenReceived


def test_textual_layout_and_responsive_resize():
    async def scenario():
        app = ChatApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert app.query_one("#composer", Composer)
            assert app.query_one("#sidebar").display

            await pilot.resize_terminal(70, 24)
            await pilot.pause()
            assert not app.query_one("#sidebar").display

    asyncio.run(scenario())


def test_composer_supports_multiline_shift_enter_and_submit():
    async def scenario():
        app = ChatApp()
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            composer = app.query_one("#composer", Composer)
            composer.focus()
            composer.text = ""
            await pilot.press("shift+enter")
            await pilot.pause()
            assert composer.text == "\n"
            composer.text = "hello\nworld"
            await pilot.press("enter")
            await pilot.pause()
            assert composer.text == ""

    asyncio.run(scenario())


def test_composer_grows_to_max_three_lines():
    async def scenario():
        app = ChatApp()
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            composer = app.query_one("#composer", Composer)
            composer.text = "line1"
            await pilot.pause()
            assert composer.styles.height.value == 1
            composer.text = "line1\nline2\nline3"
            await pilot.pause()
            assert composer.styles.height.value == 3
            composer.text = "line1\nline2\nline3\nline4\nline5"
            await pilot.pause()
            assert composer.styles.height.value == 3

    asyncio.run(scenario())


def test_streaming_and_loading_are_single_widgets():
    async def scenario():
        app = ChatApp()
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            app._create_loading_widget()
            app._create_streaming_widget()
            app.post_message(StatusReceived("answer_streaming"))
            app.post_message(TokenReceived("first"))
            app.post_message(TokenReceived(" second"))
            await pilot.pause()
            assert len(app.query(".loading-turn")) == 1
            assert len(app.query(".streaming-turn")) == 1
            assert app._streaming_widget is not None
            assert app._stream_buffer == "first second"
            assert app.query_one("#send").label == "Send"

    asyncio.run(scenario())


def test_source_panel_is_not_duplicated():
    async def scenario():
        app = ChatApp()
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            app._append_sources([])
            await pilot.pause()
            app._append_sources([])
            await pilot.pause()
            assert len(app.query(".sources-turn")) == 1

    asyncio.run(scenario())


def test_ctrl_c_requires_confirmation_before_quit():
    async def scenario():
        app = ChatApp()
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            app.action_confirm_quit()
            await pilot.pause()
            assert app._quit_confirm_until > time.monotonic()
            assert app.is_running
            app.action_confirm_quit()
            await pilot.pause()
            assert not app.is_running

    asyncio.run(scenario())
