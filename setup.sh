#!/usr/bin/env bash
# One-link installer: curl -fsSL https://raw.githubusercontent.com/samson693000-creator/neo-panel/main/setup.sh | bash
set -euo pipefail

REPO="https://github.com/samson693000-creator/neo-panel.git"
DIR="${NEO_PANEL_DIR:-$HOME/neo-panel}"

export DEBIAN_FRONTEND=noninteractive
export PYTHONUTF8=1

need_root() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    echo "[ERR] Нужны права root. Запусти от root или поставь sudo."
    exit 1
  fi
}

echo "============================================"
echo "  NEO PANEL // AUTO INSTALL"
echo "============================================"

if command -v apt-get >/dev/null 2>&1; then
  need_root apt-get update -y
  need_root apt-get install -y git curl ca-certificates python3 python3-venv python3-pip
else
  echo "[ERR] Поддерживается Ubuntu/Debian (apt-get)."
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERR] python3 не установлен"
  exit 1
fi

node_major=0
if command -v node >/dev/null 2>&1; then
  node_major="$(node -v | sed 's/v//' | cut -d. -f1)"
fi
if [ "$node_major" -lt 18 ] 2>/dev/null || ! command -v npm >/dev/null 2>&1; then
  echo "Ставлю Node.js 20..."
  if [ "$(id -u)" -eq 0 ]; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  else
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  fi
  need_root apt-get install -y nodejs
fi

if [ -d "$DIR/.git" ]; then
  echo "Обновляю $DIR"
  git -C "$DIR" pull --ff-only
else
  if [ -e "$DIR" ] && [ ! -d "$DIR/.git" ]; then
    echo "[ERR] Папка $DIR уже есть и это не git-репозиторий."
    echo "Удали её или задай другой путь: NEO_PANEL_DIR=/opt/neo-panel bash setup.sh"
    exit 1
  fi
  echo "Клонирую репозиторий в $DIR"
  git clone "$REPO" "$DIR"
fi

cd "$DIR"
rm -rf .venv
python3 install.py
