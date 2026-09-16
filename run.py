# -*- coding: utf-8 -*-
"""Start NEO PANEL after install.py."""
from __future__ import annotations

import io
import os
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
VENV_PY = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _read_env(key: str, default: str) -> str:
    env_file = ROOT / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip() or default
    return os.environ.get(key, default)


def _panel_url(host: str, port: str) -> str:
    if host in {"127.0.0.1", "localhost"}:
        return f"http://127.0.0.1:{port}"
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return f"http://{ip}:{port}"
    except OSError:
        return f"http://{host}:{port}"


def main() -> None:
    os.environ.setdefault("PYTHONUTF8", "1")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    else:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    py = VENV_PY if VENV_PY.is_file() else Path(sys.executable)
    if not VENV_PY.is_file():
        print("Сначала выполни: python3 install.py")
        raise SystemExit(1)

    host = _read_env("HOST", "127.0.0.1" if os.name == "nt" else "0.0.0.0")
    port = _read_env("PORT", "8000")
    os.chdir(ROOT)
    print("Админ-панель:", _panel_url(host, port))
    print("Остановка: Ctrl+C")
    raise SystemExit(
        subprocess.call(
            [
                str(py),
                "-m",
                "uvicorn",
                "app.main:app",
                "--app-dir",
                str(BACKEND),
                "--host",
                host,
                "--port",
                port,
            ]
        )
    )


if __name__ == "__main__":
    main()
