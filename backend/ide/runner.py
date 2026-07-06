"""
Code execution for the IDE terminal.

The IDE's Run button executes ``python main.py``. This module provides a
DEV executor that runs the project's files in a throwaway temp directory with a
wall-clock timeout and captured output.

SECURITY: this dev executor is NOT a secure sandbox — it runs code with the
server's own privileges. Production must run untrusted code in an isolated
runtime (Docker + gVisor, or a service like Judge0). That hardened multi-language
runtime (Python/C/C++/…) is Phase 8; this module is the seam it plugs into.
Only Python is wired up here; other languages return a "needs sandbox" notice.
"""

import os
import subprocess
import sys
import tempfile

from .languages import runtime_for

RUN_TIMEOUT_SECONDS = 10
MAX_OUTPUT_CHARS = 20000
ENTRY = "main.py"
WEB_ENTRIES = ("index.html", "index.htm")


class RunResult:
    def __init__(self, stdout="", stderr="", exit_code=0, timed_out=False):
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.timed_out = timed_out

    def as_dict(self):
        return {
            "command": f"python {ENTRY}",
            "stdout": self.stdout[:MAX_OUTPUT_CHARS],
            "stderr": self.stderr[:MAX_OUTPUT_CHARS],
            "exit_code": self.exit_code,
            "timed_out": self.timed_out,
        }


def run_python(files: dict) -> RunResult:
    """Run ``python main.py`` over ``files`` (path -> content). Returns output."""
    if ENTRY not in files:
        return RunResult(stderr=f"{ENTRY} not found. Create a {ENTRY} to run.", exit_code=1)

    with tempfile.TemporaryDirectory(prefix="gp-run-") as tmp:
        for path, content in files.items():
            # Guard against path escapes from crafted file names.
            dest = os.path.abspath(os.path.join(tmp, path))
            if os.path.commonpath([tmp]) != os.path.commonpath([tmp, dest]):
                continue
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "w", encoding="utf-8") as fh:
                fh.write(content)

        try:
            proc = subprocess.run(
                [sys.executable, ENTRY],
                cwd=tmp,
                capture_output=True,
                text=True,
                timeout=RUN_TIMEOUT_SECONDS,
                # Minimal environment; no inherited secrets.
                env={"PATH": os.environ.get("PATH", ""), "PYTHONUNBUFFERED": "1"},
            )
            return RunResult(proc.stdout, proc.stderr, proc.returncode)
        except subprocess.TimeoutExpired as exc:
            out = exc.stdout or ""
            if isinstance(out, bytes):
                out = out.decode(errors="replace")
            return RunResult(out, f"Execution timed out after {RUN_TIMEOUT_SECONDS}s.", 124, True)


def _web_entry(files: dict) -> str | None:
    """Shallowest ``index.html`` in the project (root preferred)."""
    for name in WEB_ENTRIES:
        if name in files:
            return name
    best, best_depth = None, 1_000_000
    for path in files:
        base = path.rsplit("/", 1)[-1].lower()
        if base in WEB_ENTRIES:
            depth = path.count("/")
            if depth < best_depth:
                best, best_depth = path, depth
    return best


def run_project(files: dict) -> dict:
    """Decide how a project runs and return a mode-tagged result.

    * A web project (has an ``index.html``) runs live in the browser webview —
      no server execution; the client renders it CodePen-style. We just tell the
      frontend which entry to preview.
    * ``main.py`` runs in the server terminal.
    * Rust/C/C++ compile to WebAssembly and need the Phase-8 sandbox runtime.
    """
    entry = _web_entry(files)
    if entry:
        return {
            "mode": "preview", "entry": entry,
            "command": f"live-server → {entry}",
            "stdout": "", "stderr": "", "exit_code": 0, "timed_out": False,
        }

    if ENTRY in files:
        result = run_python(files).as_dict()
        result["mode"] = "terminal"
        result["entry"] = ENTRY
        return result

    if any(runtime_for(p) == "compiled" for p in files):
        return {
            "mode": "terminal", "entry": "",
            "command": "build",
            "stdout": "",
            "stderr": ("Rust / C / C++ build & run needs the sandbox runtime (Phase 8). "
                       "These compile to WebAssembly for the game engine's near-native speed."),
            "exit_code": 1, "timed_out": False,
        }

    return {
        "mode": "terminal", "entry": "",
        "command": "run",
        "stdout": "",
        "stderr": ("Nothing to run. Add an index.html to preview it live in the webview, "
                   "or a main.py to run in the terminal."),
        "exit_code": 1, "timed_out": False,
    }
