#!/bin/sh
set -eu

APP_DIR="${PAPER2REAL_APP_DIR:-/mnt/dl/dl/paper2real}"
RUNNER="$APP_DIR/deploy/run_daily_validation_and_push.sh"
LOG_FILE="$APP_DIR/data/logs/daily_validation_cron.log"
MARKER="paper2real_daily_validation_6h"

mkdir -p "$APP_DIR/data/logs"
chmod +x "$RUNNER" 2>/dev/null || true

CRON_LINE="0 */6 * * * /bin/sh $RUNNER >> $LOG_FILE 2>&1 # $MARKER"

(crontab -l 2>/dev/null | grep -v "$MARKER" || true; echo "$CRON_LINE") | crontab -

echo "Installed cron:"
crontab -l | grep "$MARKER"
