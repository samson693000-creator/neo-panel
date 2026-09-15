#!/usr/bin/env bash
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: $0 backups/db-YYYYMMDD-HHMMSS.sql.gz"
  exit 1
fi

DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR"
source .env

read -rp "Data will be overwritten. Continue? (yes/no): " CONFIRM
[ "$CONFIRM" = "yes" ] || exit 0

gunzip -c "$1" | docker compose exec -T db \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"

docker compose restart backend
echo "Restore finished"
