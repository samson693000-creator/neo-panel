#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}"
echo "  ============================================"
echo "        NEO PANEL // AI BOT INSTALLER"
echo "  ============================================"
echo -e "${NC}"

command -v docker >/dev/null 2>&1 || { echo -e "${RED}Docker not found${NC}"; exit 1; }
if ! docker compose version >/dev/null 2>&1; then
  echo -e "${RED}Docker Compose v2 required${NC}"
  exit 1
fi

if [ -f .env ]; then
  echo "File .env already exists - skip generation."
else
  read -rp "Domain (Enter = localhost): " DOMAIN
  DOMAIN=${DOMAIN:-localhost}
  read -rp "Email for Let's Encrypt: " ACME_EMAIL
  ACME_EMAIL=${ACME_EMAIL:-admin@example.com}
  read -rp "Admin login [admin]: " ADMIN_USERNAME
  ADMIN_USERNAME=${ADMIN_USERNAME:-admin}
  read -rsp "Admin password (min 8 chars): " ADMIN_PASSWORD
  echo

  if [ ${#ADMIN_PASSWORD} -lt 8 ]; then
    echo -e "${RED}Password too short${NC}"
    exit 1
  fi

  DB_PASS=$(openssl rand -hex 16)
  SECRET_KEY=$(openssl rand -hex 32)
  ENCRYPTION_KEY=$(openssl rand -base64 32 | tr '+/' '-_')

  cat > .env <<EOF
POSTGRES_USER=botuser
POSTGRES_PASSWORD=${DB_PASS}
POSTGRES_DB=botdb
DATABASE_URL=postgresql+asyncpg://botuser:${DB_PASS}@db:5432/botdb

REDIS_URL=redis://redis:6379/0

SECRET_KEY=${SECRET_KEY}
ENCRYPTION_KEY=${ENCRYPTION_KEY}

ADMIN_USERNAME=${ADMIN_USERNAME}
ADMIN_PASSWORD=${ADMIN_PASSWORD}

DOMAIN=${DOMAIN}
ACME_EMAIL=${ACME_EMAIL}
CORS_ORIGINS=https://${DOMAIN},http://${DOMAIN}
EOF

  chmod 600 .env
  echo -e "${GREEN}.env created${NC}"
fi

docker compose build
docker compose up -d
sleep 8
docker compose ps

DOMAIN_VALUE=$(grep '^DOMAIN=' .env | cut -d= -f2-)
ADMIN_USER=$(grep '^ADMIN_USERNAME=' .env | cut -d= -f2-)
ADMIN_PASS=$(grep '^ADMIN_PASSWORD=' .env | cut -d= -f2-)
if [ "$DOMAIN_VALUE" = "localhost" ]; then
  PANEL_URL="http://localhost:8080"
else
  PANEL_URL="https://${DOMAIN_VALUE}"
fi

echo
echo "============================================"
echo "  NEO PANEL // УСТАНОВКА ЗАВЕРШЕНА"
echo "============================================"
echo "Админ-панель: ${PANEL_URL}"
echo "Логин:        ${ADMIN_USER}"
echo "Пароль:       ${ADMIN_PASS}"
echo "============================================"
echo "После входа логин и пароль можно сменить в разделе «Аккаунт»."
