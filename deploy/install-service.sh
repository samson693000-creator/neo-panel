#!/usr/bin/env bash
# Keep NEO PANEL running after SSH/PuTTY disconnect.
# Usage: bash deploy/install-service.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)"
PY="$DIR/.venv/bin/python"
BACKEND="$DIR/backend"
UNIT="/etc/systemd/system/neo-panel.service"
HOST="0.0.0.0"
PORT="8000"

if [ -f "$DIR/.env" ]; then
  env_port="$(grep '^PORT=' "$DIR/.env" | cut -d= -f2- | tr -d '\r')"
  if [ -n "${env_port:-}" ]; then
    PORT="$env_port"
  fi
fi

if [ ! -x "$PY" ]; then
  echo "[ERR] Сначала установи проект: python3 install.py --no-start"
  echo "Не найден $PY"
  exit 1
fi

if [ "$(id -u)" -ne 0 ]; then
  if command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
  else
    echo "[ERR] Нужен root или sudo"
    exit 1
  fi
else
  SUDO=""
fi

run() {
  if [ -n "$SUDO" ]; then
    sudo "$@"
  else
    "$@"
  fi
}

pkill -f "uvicorn app.main:app" >/dev/null 2>&1 || true

run tee "$UNIT" >/dev/null <<EOF
[Unit]
Description=NEO PANEL Telegram bot and admin
After=network.target

[Service]
Type=simple
WorkingDirectory=$DIR
Environment=PYTHONUTF8=1
EnvironmentFile=-$DIR/.env
ExecStart=$PY -m uvicorn app.main:app --app-dir $BACKEND --host $HOST --port $PORT
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

run systemctl daemon-reload
run systemctl enable neo-panel
run systemctl restart neo-panel
sleep 1
run systemctl --no-pager --full status neo-panel || true

echo
echo "Сервис neo-panel включён. Консоль PuTTY можно закрывать."
echo "Статус:   systemctl status neo-panel"
echo "Логи:     journalctl -u neo-panel -f"
echo "Стоп:     systemctl stop neo-panel"
echo "Старт:    systemctl start neo-panel"
