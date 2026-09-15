# -*- coding: utf-8 -*-
"""One-command installer for NEO PANEL (bot + admin)."""
from __future__ import annotations

import argparse
import io
import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PLACEHOLDER_PASSWORDS = {
    "",
    "change_me_now_123",
    "change_me",
    "admin12345",
    "please_generate_a_long_random_secret_string",
}
VENV = ROOT / ".venv"
DATA = ROOT / "data"
FRONTEND = ROOT / "frontend"
BACKEND = ROOT / "backend"
CREDENTIALS = DATA / "credentials.txt"


def _utf8_stdio() -> None:
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    else:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def die(message: str, code: int = 1) -> None:
    print(f"[ERR] {message}", file=sys.stderr)
    raise SystemExit(code)


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print(">", " ".join(cmd))
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        cmd,
        cwd=cwd or ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        die(f"команда завершилась с кодом {result.returncode}: {' '.join(cmd)}")


def venv_python() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def read_env_value(key: str) -> str:
    env_file = ROOT / ".env"
    if not env_file.is_file():
        return ""
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip()
    return ""


def write_env(username: str, password: str) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    db_path = (DATA / "bot.db").as_posix()
    secret = secrets.token_hex(32)
    encryption = secrets.token_urlsafe(32)
    text = f"""POSTGRES_USER=botuser
POSTGRES_PASSWORD={secrets.token_hex(16)}
POSTGRES_DB=botdb
DATABASE_URL=sqlite+aiosqlite:///{db_path}

REDIS_URL=redis://localhost:6379/0

SECRET_KEY={secret}
ENCRYPTION_KEY={encryption}

ADMIN_USERNAME={username}
ADMIN_PASSWORD={password}

DOMAIN=localhost
ACME_EMAIL=admin@example.com

CORS_ORIGINS=http://127.0.0.1:8000,http://localhost:8000,http://localhost:5173,http://localhost:8080
HOST=127.0.0.1
PORT=8000
"""
    (ROOT / ".env").write_text(text, encoding="utf-8", newline="\n")
    CREDENTIALS.write_text(
        f"url=http://127.0.0.1:8000\nusername={username}\npassword={password}\n",
        encoding="utf-8",
        newline="\n",
    )


def print_access(username: str, password: str, created: bool) -> None:
    print()
    print("=" * 46)
    print("  NEO PANEL // УСТАНОВКА ЗАВЕРШЕНА")
    print("=" * 46)
    print("Админ-панель:  http://127.0.0.1:8000")
    print(f"Логин:         {username}")
    print(f"Пароль:        {password}")
    print("=" * 46)
    if created:
        print("Сохраните пароль. После входа его и логин")
        print("можно сменить в разделе «Аккаунт».")
        print(f"Копия записана в {CREDENTIALS}")
    else:
        print("Файл .env уже был. Если пароль меняли в админке —")
        print("входите новыми данными, а не этими.")
    print("Повторный запуск:  python run.py")
    print("=" * 46)


def main() -> None:
    _utf8_stdio()
    parser = argparse.ArgumentParser(description="Установка NEO PANEL")
    parser.add_argument("--no-start", action="store_true", help="только поставить, не запускать сервер")
    args = parser.parse_args()

    if sys.version_info < (3, 10):
        die("Нужен Python 3.10 или новее")

    node = shutil.which("node")
    npm = shutil.which("npm")
    if not node or not npm:
        die("Нужен Node.js (с npm): https://nodejs.org")

    print("Python:", sys.version.split()[0])
    run([node, "-v"])
    run([npm, "-v"])

    if not VENV.exists():
        print("Создаю виртуальное окружение...")
        run([sys.executable, "-m", "venv", str(VENV)])

    py = venv_python()
    if not py.is_file():
        die(f"не найден интерпретатор venv: {py}")

    run([str(py), "-m", "pip", "install", "--upgrade", "pip"])
    run([str(py), "-m", "pip", "install", "-r", str(BACKEND / "requirements.txt")])

    print("Собираю админ-панель...")
    run([npm, "install"], cwd=FRONTEND)
    run([npm, "run", "build"], cwd=FRONTEND)
    if not (FRONTEND / "dist" / "index.html").is_file():
        die("сборка frontend не создала dist/index.html")

    env_file = ROOT / ".env"
    existing_password = read_env_value("ADMIN_PASSWORD")
    existing_secret = read_env_value("SECRET_KEY")
    needs_secrets = (
        not env_file.is_file()
        or existing_password in PLACEHOLDER_PASSWORDS
        or existing_secret in PLACEHOLDER_PASSWORDS
    )
    created = needs_secrets
    if created:
        username = read_env_value("ADMIN_USERNAME") or "admin"
        password = secrets.token_urlsafe(12)
        write_env(username, password)
        print(".env создан (логин и пароль сгенерированы)")
    else:
        username = read_env_value("ADMIN_USERNAME") or "admin"
        password = read_env_value("ADMIN_PASSWORD") or "(см. .env / админку)"
        print(".env уже есть — пароль не перезаписываю")

    print_access(username, password, created)

    if args.no_start:
        return

    print("Запускаю сервер. Остановка: Ctrl+C")
    os.chdir(ROOT)
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
