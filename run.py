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


def _detect_ipv4() -> str:
    found: list[str] = []
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2)
        sock.connect(("8.8.8.8", 80))
        found.append(sock.getsockname()[0])
        sock.close()
    except OSError:
        pass
    try:
        out = subprocess.check_output(
            ["hostname", "-I"], text=True, encoding="utf-8", errors="replace", timeout=3
        )
        found.extend(out.split())
    except (OSError, subprocess.SubprocessError):
        pass
    for url in ("https://api.ipify.org", "https://ifconfig.me/ip"):
        try:
            import urllib.request

            with urllib.request.urlopen(url, timeout=4) as resp:
                found.append(resp.read().decode("utf-8", errors="replace").strip())
            break
        except OSError:
            continue
    for ip in found:
        if (
            ip
            and ip.count(".") == 3
            and not ip.startswith("127.")
            and not ip.startswith("0.")
        ):
            return ip
    return ""


def _panel_url(port: str) -> str:
    if os.name == "nt":
        return f"http://127.0.0.1:{port}"
    ip = _detect_ipv4()
    return f"http://{ip or 'IP_СЕРВЕРА'}:{port}"


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

    host = "127.0.0.1" if os.name == "nt" else "0.0.0.0"
    port = _read_env("PORT", "8000")
    os.chdir(ROOT)
    print("Админ-панель:", _panel_url(port))
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
