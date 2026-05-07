#!/bin/sh
set -eu

APP_DIR="${PAPER2REAL_APP_DIR:-/mnt/dl/dl/paper2real}"
APP_URL="${PAPER2REAL_APP_URL:-http://127.0.0.1:8000}"
CONTAINER="${PAPER2REAL_CONTAINER:-paper2real}"
LOCK_DIR="${PAPER2REAL_LEARNING_LOCK:-/tmp/paper2real_learning_only_scan.lock}"
LOG_SOURCE="learning_only_cron"

mkdir -p "$APP_DIR/data/logs"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "[learning-only] $(date -u '+%Y-%m-%dT%H:%M:%SZ') learning_only_scan_skipped_overlap"
  docker exec "$CONTAINER" sh -lc 'cd /app && python - <<'"'"'PY'"'"'
import trader
trader.init_db()
trader.log_event(
    "WARNING",
    "learning_only_scan_skipped_overlap",
    "Learning-only scan skipped because previous run is still active.",
    source="learning_only_cron",
    status="skipped",
    metadata={"scan_mode": "learning_only"},
)
PY' >/dev/null 2>&1 || true
  exit 0
fi

cleanup() {
  rmdir "$LOCK_DIR" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "[learning-only] $(date -u '+%Y-%m-%dT%H:%M:%SZ') running learning-only scan"
curl -fsS -X POST "$APP_URL/learning-only-scan"
echo
echo "[learning-only] completed"
