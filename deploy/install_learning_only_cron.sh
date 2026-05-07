#!/bin/sh
set -eu

APP_DIR="${PAPER2REAL_APP_DIR:-/mnt/dl/dl/paper2real}"
RUNNER="$APP_DIR/deploy/run_learning_only_scan.sh"
LOG_FILE="$APP_DIR/data/logs/learning_only_cron.log"
MARKER="paper2real_learning_only_1h"

mkdir -p "$APP_DIR/data/logs"
chmod +x "$RUNNER" 2>/dev/null || true

CRON_LINE="0 * * * * /bin/sh $RUNNER >> $LOG_FILE 2>&1 # $MARKER"

(crontab -l 2>/dev/null | grep -v "$MARKER" || true; echo "$CRON_LINE") | crontab -

echo "Installed cron:"
crontab -l | grep "$MARKER"
