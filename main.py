#!/usr/bin/env python3
"""Dev launcher for the game platform.

Runs the Django backend and the Next.js frontend together from one command:

    python main.py                # backend + frontend
    python main.py --backend      # backend only
    python main.py --frontend     # frontend only
    python main.py --no-migrate   # skip the initial `manage.py migrate`
    python main.py --install      # install backend + frontend deps first, then run

Press Ctrl+C once to stop everything.

The backend uses the virtualenv at backend/.venv when present (SQLite +
in-memory channel layer for dev), otherwise the interpreter running this script.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
IS_WINDOWS = os.name == "nt"

COLORS = {"backend": "\033[36m", "frontend": "\033[35m"}
RESET = "\033[0m"


def backend_python() -> str:
    """Backend virtualenv interpreter, falling back to the current one."""
    if IS_WINDOWS:
        candidates = [
            BACKEND / ".venv" / "Scripts" / "python.exe",
            BACKEND / "venv" / "Scripts" / "python.exe",
        ]
    else:
        candidates = [
            BACKEND / ".venv" / "bin" / "python",
            BACKEND / "venv" / "bin" / "python",
        ]
    for c in candidates:
        if c.exists():
            return str(c)
    return sys.executable


def npm_cmd() -> str:
    cmd = shutil.which("npm.cmd" if IS_WINDOWS else "npm") or shutil.which("npm")
    if not cmd:
        sys.exit("npm not found on PATH — install Node.js to run the frontend.")
    return cmd


def _pump(name: str, stream) -> None:
    """Forward a child's output line-by-line with a coloured [name] prefix."""
    prefix = f"{COLORS.get(name, '')}[{name}]{RESET} "
    for line in iter(stream.readline, ""):
        sys.stdout.write(prefix + line)
        sys.stdout.flush()
    stream.close()


def spawn(name: str, cmd: list[str], cwd: Path) -> subprocess.Popen:
    print(f"{COLORS.get(name, '')}[{name}]{RESET} starting: {' '.join(cmd)}")
    kwargs = {}
    if IS_WINDOWS:
        # Own process group so we can kill the whole tree (npm -> node -> ...).
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        **kwargs,
    )
    threading.Thread(target=_pump, args=(name, proc.stdout), daemon=True).start()
    return proc


def terminate(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    if IS_WINDOWS:
        # taskkill /T also reaps the node children npm spawns.
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            capture_output=True,
        )
    else:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def run_blocking(name: str, cmd: list[str], cwd: Path) -> None:
    """Run a step (install/migrate) to completion, aborting on failure."""
    print(f"{COLORS.get(name, '')}[{name}]{RESET} {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(cwd))
    if result.returncode != 0:
        sys.exit(f"[{name}] '{' '.join(cmd)}' failed (exit {result.returncode})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the game platform locally.")
    parser.add_argument("--backend", action="store_true", help="run backend only")
    parser.add_argument("--frontend", action="store_true", help="run frontend only")
    parser.add_argument("--no-migrate", action="store_true", help="skip migrate")
    parser.add_argument("--install", action="store_true", help="install deps first")
    args = parser.parse_args()

    # No selector -> run both.
    run_backend = args.backend or not args.frontend
    run_frontend = args.frontend or not args.backend

    if IS_WINDOWS:
        os.system("")  # enable ANSI colour handling in legacy consoles

    py = backend_python()

    if args.install:
        if run_backend:
            run_blocking("backend", [py, "-m", "pip", "install", "-r",
                                     str(BACKEND / "requirements.txt")], BACKEND)
        if run_frontend:
            run_blocking("frontend", [npm_cmd(), "install"], FRONTEND)

    if run_backend and not args.no_migrate:
        run_blocking("backend", [py, "manage.py", "migrate"], BACKEND)

    procs: dict[str, subprocess.Popen] = {}
    if run_backend:
        procs["backend"] = spawn("backend", [py, "manage.py", "runserver"], BACKEND)
    if run_frontend:
        procs["frontend"] = spawn("frontend", [npm_cmd(), "run", "dev"], FRONTEND)

    if run_backend:
        print("\nBackend  -> http://localhost:8000/api/  (admin at /admin/)")
    if run_frontend:
        print("Frontend -> http://localhost:3000")
    print("Press Ctrl+C to stop.\n")

    try:
        while procs:
            for name, proc in list(procs.items()):
                code = proc.poll()
                if code is not None:
                    print(f"\n[{name}] exited with code {code} — shutting down.")
                    del procs[name]
                    raise KeyboardInterrupt
            time.sleep(0.3)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        for proc in procs.values():
            terminate(proc)


if __name__ == "__main__":
    main()
