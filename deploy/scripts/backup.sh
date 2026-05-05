#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/paper2real"
BACKUP_DIR="${APP_DIR}/backups"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

mkdir -p "${BACKUP_DIR}"

tar -czf "${BACKUP_DIR}/paper2real-${STAMP}.tar.gz" \
  -C "${APP_DIR}" \
  paper_trader.db \
  data/reports \
  data/raw \
  data/processed \
  .env

find "${BACKUP_DIR}" -type f -name "paper2real-*.tar.gz" -mtime +14 -delete

echo "Backup written: ${BACKUP_DIR}/paper2real-${STAMP}.tar.gz"
