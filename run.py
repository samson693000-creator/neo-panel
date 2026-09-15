# -*- coding: utf-8 -*-
"""Start NEO PANEL after install.py."""
from __future__ import annotations

import io
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
VENV_PY = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def main() -> None:
    os.environ.setdefault("PYTHONUTF8", "1")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    else:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    py = VENV_PY if VENV_PY.is_file() else Path(sys.executable)
    os.chdir(ROOT)
    print("Админ-панель: http://127.0.0.1:8000")
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
                "127.0.0.1",
                "--port",
                "8000",
            ]
        )
    )


if __name__ == "__main__":
    main()
