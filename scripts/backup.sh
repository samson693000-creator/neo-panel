#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="${DIR}/backups"
KEEP_DAYS=14

mkdir -p "$BACKUP_DIR"
cd "$DIR"
source .env

STAMP=$(date +%Y%m%d-%H%M%S)
FILE="${BACKUP_DIR}/db-${STAMP}.sql.gz"

docker compose exec -T db \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --clean \
  | gzip > "$FILE"

echo "Backup created: $FILE"
find "$BACKUP_DIR" -name 'db-*.sql.gz' -mtime "+${KEEP_DAYS}" -delete
