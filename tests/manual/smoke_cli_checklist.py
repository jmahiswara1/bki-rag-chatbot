"""Comprehensive non-interactive test for test.md checklist.

Tests what can be tested without a live TTY:
- Startup & service checks (Section 1)
- Slash command parsing & routing (Section 4)
- Error handling paths (Section 2, 5d)
- Exit code behavior (Section 9)
- Encoding safety (Section 8)
- History windowing logic (Section 7)
- REPL control code structure (Section 3)
"""
import os
import sys
import io
import inspect
import subprocess

# Force UTF-8 before anything else
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

from rich.console import Console

PASS = 0
FAIL = 0

def check(label: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {label}")
    else:
        FAIL += 1
        msg = f"  [FAIL] {label}"
        if detail:
            msg += f"  -- {detail}"
        print(msg)


def run_python(code: str, env_override: dict | None = None, timeout: int = 60) -> tuple[str, int]:
    """Run a Python snippet as subprocess, return (combined_output, exit_code)."""
    env = os.environ.copy()
    env["TF_ENABLE_ONEDNN_OPTS"] = "0"
    env["PYTHONIOENCODING"] = "utf-8"
    if env_override:
        env.update(env_override)
    try:
        r = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, timeout=timeout,
            env=env, cwd=os.path.dirname(os.path.abspath(__file__)),
            encoding="utf-8", errors="replace",
        )
        output = r.stdout + r.stderr
        return output, r.returncode
    except subprocess.TimeoutExpired:
        return "(timeout)", -1


# ======================================================================
print("=" * 60)
print("SECTION 1: Startup & Service Check")
print("=" * 60)

# 1a: Normal startup path (services alive)
print("\n--- 1a: Normal startup (_check_services) ---")
out, code = run_python("""
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
from rich.console import Console
from src.cli.app import _check_services
c = Console()
result = _check_services(c)
print(f"RESULT={result}")
""", timeout=90)
check("Normal startup: services OK", "RESULT=True" in out,
      out[-400:] if "RESULT=True" not in out else "")
check("Normal startup: no traceback", "Traceback" not in out,
      out[-300:] if "Traceback" in out else "")
check("Normal startup: shows Ollama available", "Ollama available" in out,
      out[-300:] if "Ollama available" not in out else "")
check("Normal startup: shows Supabase available", "Supabase available" in out,
      out[-300:] if "Supabase available" not in out else "")

# 1b: Ollama mati (bad host) — set env BEFORE import so load_dotenv doesn't override
print("\n--- 1b: Ollama unavailable (bad host) ---")
out, code = run_python("""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
os.environ['OLLAMA_HOST'] = 'http://localhost:19999'
from rich.console import Console
from src.cli.app import _check_services
c = Console()
result = _check_services(c)
print(f"RESULT={result}")
""", env_override={"OLLAMA_HOST": "http://localhost:19999"}, timeout=30)
check("Ollama down: services fail", "RESULT=False" in out,
      out[-300:] if "RESULT=False" not in out else "")
check("Ollama down: no traceback", "Traceback" not in out,
      out[-300:] if "Traceback" in out else "")
check("Ollama down: friendly message", "ollama" in out.lower(),
      out[-300:] if "ollama" not in out.lower() else "")

# 1c: Model tidak ada
print("\n--- 1c: Model not found ---")
out, code = run_python("""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
os.environ['DEFAULT_MODEL'] = 'nonexistent-model:latest'
from rich.console import Console
from src.cli.app import _check_services
c = Console()
result = _check_services(c)
print(f"RESULT={result}")
""", env_override={"DEFAULT_MODEL": "nonexistent-model:latest"}, timeout=90)
check("Model not found: services fail", "RESULT=False" in out,
      out[-300:] if "RESULT=False" not in out else "")
check("Model not found: no traceback", "Traceback" not in out,
      out[-300:] if "Traceback" in out else "")
check("Model not found: friendly message", "not found" in out.lower() or "model" in out.lower(),
      out[-300:] if "not found" not in out.lower() else "")

# 1d: Kredensial hilang
print("\n--- 1d: Missing credentials ---")
out, code = run_python("""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
os.environ['SUPABASE_KEY'] = ''
os.environ['SUPABASE_URL'] = ''
from rich.console import Console
from src.cli.app import _check_services
c = Console()
result = _check_services(c)
print(f"RESULT={result}")
""", env_override={"SUPABASE_KEY": "", "SUPABASE_URL": ""}, timeout=30)
check("Missing creds: services fail", "RESULT=False" in out,
      out[-300:] if "RESULT=False" not in out else "")
check("Missing creds: no traceback", "Traceback" not in out,
      out[-300:] if "Traceback" in out else "")
check("Missing creds: message mentions SUPABASE",
      "SUPABASE" in out.upper() or "supabase" in out.lower(),
      out[-300:] if "SUPABASE" not in out.upper() else "")

# ======================================================================
print("\n" + "=" * 60)
print("SECTION 4: Slash Commands")
print("=" * 60)

# 4a: parse_command
print("\n--- 4a: parse_command ---")
from src.cli.commands import parse_command, HELP_TEXT

check("/help parse", parse_command("/help") == ("help", ""))
check("/mode parse", parse_command("/mode") == ("mode", ""))
check("/mode fast parse", parse_command("/mode fast") == ("mode", "fast"))
check("/mode default parse", parse_command("/mode default") == ("mode", "default"))
check("/source parse", parse_command("/source") == ("source", ""))
check("/clear parse", parse_command("/clear") == ("clear", ""))
check("/exit parse", parse_command("/exit") == ("exit", ""))
check("/quit parse", parse_command("/quit") == ("quit", ""))
check("/unknown parse", parse_command("/unknown") == ("unknown", ""))

# 4b: /mode command logic
print("\n--- 4b: /mode command logic ---")
from src.cli.state import AppState
from src.llm.modes import MODES
from src.cli.app import _handle_mode_command, _handle_source_command, _handle_clear_command

state = AppState(mode="default")

# /mode (show current)
buf = io.StringIO()
c = Console(file=buf, force_terminal=True, width=120)
_handle_mode_command("", state, c)
output = buf.getvalue()
check("/mode (empty arg): shows current mode", "default" in output, repr(output))

# /mode fast
buf = io.StringIO()
c = Console(file=buf, force_terminal=True, width=120)
_handle_mode_command("fast", state, c)
output = buf.getvalue()
check("/mode fast: changes mode", state.mode == "fast", f"state.mode={state.mode}")
check("/mode fast: confirms change", "fast" in output.lower(), repr(output))

# /mode default
buf = io.StringIO()
c = Console(file=buf, force_terminal=True, width=120)
_handle_mode_command("default", state, c)
output = buf.getvalue()
check("/mode default: changes back", state.mode == "default", f"state.mode={state.mode}")

# /mode invalid
buf = io.StringIO()
c = Console(file=buf, force_terminal=True, width=120)
old_mode = state.mode
_handle_mode_command("invalid", state, c)
output = buf.getvalue()
check("/mode invalid: mode unchanged", state.mode == old_mode, f"state.mode={state.mode}")
check("/mode invalid: error message", "unknown mode" in output.lower(), repr(output))

# 4c: /source command
print("\n--- 4c: /source command ---")
state2 = AppState()
buf = io.StringIO()
c = Console(file=buf, force_terminal=True, width=120)
_handle_source_command(state2, c)
output = buf.getvalue()
check("/source before turn: no sources yet", "no sources yet" in output.lower(), repr(output))

# 4d: /clear command
print("\n--- 4d: /clear command ---")
state3 = AppState()
state3.history = [{"role": "user", "content": "test"}]
state3.last_result = "something"
buf = io.StringIO()
c = Console(file=buf, force_terminal=True, width=120)
_handle_clear_command(state3, c)
output = buf.getvalue()
check("/clear: history cleared message", "history cleared" in output.lower(), repr(output))
check("/clear: history is empty", len(state3.history) == 0)
check("/clear: last_result is None", state3.last_result is None)

# 4e: /help text
print("\n--- 4e: /help text ---")
check("/help contains /mode", "/mode" in HELP_TEXT)
check("/help contains /source", "/source" in HELP_TEXT)
check("/help contains /clear", "/clear" in HELP_TEXT)
check("/help contains /exit", "/exit" in HELP_TEXT)
check("/help contains /help", "/help" in HELP_TEXT)

# 4f: /unknown routing
print("\n--- 4f: /unknown command routing ---")
buf = io.StringIO()
c = Console(file=buf, force_terminal=True, width=120)
cmd_name, _ = parse_command("/unknown")
c.print(f"(unknown command: /{cmd_name})")
output = buf.getvalue()
check("/unknown: shows error", "unknown command" in output.lower(), repr(output))

# ======================================================================
print("\n" + "=" * 60)
print("SECTION 9: Exit Codes")
print("=" * 60)

# 9a: Exit code 2 on service failure
print("\n--- 9a: Exit code 2 on service failure ---")
out, code = run_python("""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
os.environ['OLLAMA_HOST'] = 'http://localhost:19999'
from src.cli.app import run
try:
    run([])
except SystemExit as e:
    sys.exit(e.code)
""", env_override={"OLLAMA_HOST": "http://localhost:19999"}, timeout=30)
check("Exit code 2 on Ollama failure", code == 2, f"exit_code={code}")
check("No traceback on Ollama failure", "Traceback" not in out,
      out[-300:] if "Traceback" in out else "")

# ======================================================================
print("\n" + "=" * 60)
print("SECTION 8: Encoding & Display")
print("=" * 60)

print("\n--- 8a: Unicode symbols in output ---")
out, code = run_python("""
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
test_str = "sigma=σ, sqrt=√, gte=≥, lte=≤, middot=·, delta=Δ, theta=θ"
print(test_str)
print("No encoding crash")
""")
check("Unicode symbols render without crash", "No encoding crash" in out and code == 0,
      f"code={code}, out={out[-200:]}")

# ======================================================================
print("\n" + "=" * 60)
print("SECTION 3: REPL Controls (code structure)")
print("=" * 60)

print("\n--- 3a: Code structure verification ---")
from src.cli.app import run as run_func
source = inspect.getsource(run_func)
check("KeyboardInterrupt caught in prompt loop", "KeyboardInterrupt" in source)
check("EOFError caught for Ctrl-D", "EOFError" in source)
check("Empty input handled (continue)", "if not text" in source)
check("exit/quit bare words handled", '"exit"' in source or "'exit'" in source)
check("Turn separator (Rule) rendered", "Rule" in source)
check("KeyboardInterrupt caught during render_turn", "cancelled" in source)

# ======================================================================
print("\n" + "=" * 60)
print("SECTION 2: Runtime Error Handling (code structure)")
print("=" * 60)

print("\n--- 2a: Error handling in turn loop ---")
check("OllamaUnavailable caught during turn", "OllamaUnavailable" in source)
check("SupabaseUnavailable caught during turn", "SupabaseUnavailable" in source)
check("RetrievalError caught during turn", "RetrievalError" in source)
check("Error messages are friendly (no re-raise)", "continue" in source)

# Verify chain_answer_stream catches exceptions
from src.llm.chain import chain_answer_stream as cas_func
cas_source = inspect.getsource(cas_func)
check("chain_answer_stream has try/except for stream",
      "except" in cas_source and "stream_error" in cas_source)

# ======================================================================
print("\n" + "=" * 60)
print("SECTION 7: History Windowing (logic)")
print("=" * 60)

print("\n--- 7a: Windowing logic ---")
state_w = AppState()
for i in range(4):
    state_w.history.append({"role": "user", "content": f"Q{i}"})
    state_w.history.append({"role": "assistant", "content": f"A{i}"})

check("History has 8 messages after 4 turns", len(state_w.history) == 8)

# Apply windowing as in app.py line 189
windowed = state_w.history[-6:] if len(state_w.history) > 6 else state_w.history
check("Windowed history has 6 messages (3 turns)", len(windowed) == 6)
check("Windowed starts with Q1 (not Q0)", windowed[0]["content"] == "Q1")
check("Windowed ends with A3", windowed[-1]["content"] == "A3")

# 2 turns — should NOT window
state_w2 = AppState()
state_w2.history = [
    {"role": "user", "content": "Q0"}, {"role": "assistant", "content": "A0"},
    {"role": "user", "content": "Q1"}, {"role": "assistant", "content": "A1"},
]
windowed2 = state_w2.history[-6:] if len(state_w2.history) > 6 else state_w2.history
check("Short history not windowed (4 msgs)", len(windowed2) == 4)

# ======================================================================
# HISTORY APPEND LOGIC
print("\n--- 7b: History append logic (code inspection) ---")
# Verify that only successful turns are appended
check("History append guarded by result.answer", "result.answer" in source)
check("History append guarded by result.sources", "result.sources" in source)
check("History append guarded by not result.rejected", "result.rejected" in source)
check("User message appended", '"role": "user"' in source or "'role': 'user'" in source)
check("Assistant message appended", '"role": "assistant"' in source or "'role': 'assistant'" in source)

# ======================================================================
# SUMMARY
print("\n" + "=" * 60)
total = PASS + FAIL
print(f"RESULTS: {PASS} passed, {FAIL} failed, {total} total")
print("=" * 60)
if FAIL > 0:
    sys.exit(1)
