# -*- coding: utf-8 -*-
"""One-command installer for NEO PANEL (bot + admin)."""
from __future__ import annotations

import argparse
import io
import os
import secrets
import shutil
import socket
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


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> int:
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
    if check and result.returncode != 0:
        die(f"команда завершилась с кодом {result.returncode}: {' '.join(cmd)}")
    return result.returncode


def is_root() -> bool:
    return hasattr(os, "geteuid") and os.geteuid() == 0


def apt_cmd(args: list[str]) -> list[str]:
    apt = shutil.which("apt-get")
    if not apt:
        die(
            "На этом сервере нет python3-venv. Установи вручную:\n"
            "  sudo apt-get update && sudo apt-get install -y python3-venv python3-pip"
        )
    prefix: list[str] = []
    if not is_root():
        sudo = shutil.which("sudo")
        if not sudo:
            die(
                "Нужны права root. Выполни:\n"
                "  sudo apt-get update && sudo apt-get install -y python3-venv python3-pip\n"
                "  rm -rf .venv && python3 install.py"
            )
        prefix = [sudo]
    return prefix + [apt] + args


def install_apt_packages(packages: list[str]) -> None:
    print("Ставлю системные пакеты:", ", ".join(packages))
    run(apt_cmd(["update", "-y"]))
    run(apt_cmd(["install", "-y", *packages]))


def venv_python() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def venv_ready() -> bool:
    py = venv_python()
    if not py.is_file():
        return False
    probe = subprocess.run(
        [str(py), "-c", "import ensurepip, pip"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return probe.returncode == 0


def systemd_available() -> bool:
    return (
        os.name != "nt"
        and shutil.which("systemctl") is not None
        and Path("/run/systemd/system").exists()
    )


def install_systemd_service(py: Path, host: str, port: int) -> None:
    script = ROOT / "deploy" / "install-service.sh"
    if not script.is_file():
        die("нет deploy/install-service.sh")
    run(["bash", str(script)])


def bind_host() -> str:
    return "127.0.0.1" if os.name == "nt" else "0.0.0.0"


def detect_ipv4() -> str:
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


def public_url(port: int) -> str:
    if os.name == "nt":
        return f"http://127.0.0.1:{port}"
    ip = detect_ipv4()
    return f"http://{ip or 'IP_СЕРВЕРА'}:{port}"


def patch_env_listen(host: str, port: int) -> None:
    env_file = ROOT / ".env"
    if not env_file.is_file():
        return
    lines = []
    has_host = False
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("HOST="):
            lines.append(f"HOST={host}")
            has_host = True
        elif line.startswith("PORT="):
            lines.append(f"PORT={port}")
        else:
            lines.append(line)
    if not has_host:
        lines.append(f"HOST={host}")
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def ensure_venv() -> Path:
    if VENV.exists() and not venv_ready():
        print("Виртуальное окружение битое — удаляю и создаю заново")
        shutil.rmtree(VENV, ignore_errors=True)

    if not VENV.exists():
        print("Создаю виртуальное окружение...")
        code = run([sys.executable, "-m", "venv", str(VENV)], check=False)
        if code != 0 or not venv_ready():
            if os.name == "nt":
                die("Не удалось создать venv. Переустанови Python с галкой pip/venv.")
            print("python3-venv не установлен — ставлю пакет")
            shutil.rmtree(VENV, ignore_errors=True)
            install_apt_packages(["python3-venv", "python3-pip"])
            run([sys.executable, "-m", "venv", str(VENV)])

    py = venv_python()
    if not py.is_file():
        die(f"не найден интерпретатор venv: {py}")
    return py


def ensure_node() -> tuple[str, str]:
    node = shutil.which("node")
    npm = shutil.which("npm")
    if node and npm:
        return node, npm
    if os.name == "nt":
        die("Нужен Node.js (с npm): https://nodejs.org")
    print("Node.js не найден — ставлю nodejs и npm")
    install_apt_packages(["nodejs", "npm"])
    node = shutil.which("node")
    npm = shutil.which("npm")
    if not node or not npm:
        die("Не удалось поставить Node.js. Установи: apt-get install -y nodejs npm")
    return node, npm


def read_env_value(key: str) -> str:
    env_file = ROOT / ".env"
    if not env_file.is_file():
        return ""
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip()
    return ""


def write_env(username: str, password: str, host: str, port: int) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    db_path = (DATA / "bot.db").as_posix()
    secret = secrets.token_hex(32)
    encryption = secrets.token_urlsafe(32)
    panel = public_url(port)
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

CORS_ORIGINS=http://127.0.0.1:{port},http://localhost:{port},{panel}
HOST={host}
PORT={port}
"""
    (ROOT / ".env").write_text(text, encoding="utf-8", newline="\n")
    CREDENTIALS.write_text(
        f"url={panel}\nusername={username}\npassword={password}\n",
        encoding="utf-8",
        newline="\n",
    )


def print_access(username: str, password: str, created: bool, panel: str) -> None:
    print()
    print("=" * 46)
    print("  NEO PANEL // УСТАНОВКА ЗАВЕРШЕНА")
    print("=" * 46)
    print(f"Админ-панель:  {panel}")
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
    if os.name != "nt":
        print("Если страница не открывается снаружи — открой порт 8000")
        print("в файрволе панели VPS.")
    print("Повторный запуск в консоли:  python3 run.py")
    print("Фон (после закрытия PuTTY):  bash deploy/install-service.sh")
    print("=" * 46)


def main() -> None:
    _utf8_stdio()
    parser = argparse.ArgumentParser(description="Установка NEO PANEL")
    parser.add_argument("--no-start", action="store_true", help="только поставить, не запускать сервер")
    parser.add_argument(
        "--foreground",
        action="store_true",
        help="запустить в этой консоли, а не через systemd",
    )
    args = parser.parse_args()

    if sys.version_info < (3, 10):
        die("Нужен Python 3.10 или новее")

    host = bind_host()
    port = 8000
    panel = public_url(port)

    node, npm = ensure_node()
    print("Python:", sys.version.split()[0])
    run([node, "-v"])
    run([npm, "-v"])

    py = ensure_venv()

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
        write_env(username, password, host, port)
        print(".env создан (логин и пароль сгенерированы)")
    else:
        username = read_env_value("ADMIN_USERNAME") or "admin"
        password = read_env_value("ADMIN_PASSWORD") or "(см. .env / админку)"
        print(".env уже есть — пароль не перезаписываю")
        port_raw = read_env_value("PORT")
        if port_raw.isdigit():
            port = int(port_raw)
        host = bind_host()
        patch_env_listen(host, port)
        print(f"Сервер будет слушать {host}:{port}")
    panel = public_url(port)

    print_access(username, password, created, panel)

    if args.no_start:
        return

    if systemd_available() and not args.foreground:
        print("Ставлю systemd-сервис, чтобы панель жила после закрытия PuTTY...")
        install_systemd_service(py, host, port)
        print(f"Готово. Админка: {panel}")
        return

    print("Запускаю сервер в этой консоли. Остановка: Ctrl+C")
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
                host,
                "--port",
                str(port),
            ]
        )
    )


if __name__ == "__main__":
    main()
