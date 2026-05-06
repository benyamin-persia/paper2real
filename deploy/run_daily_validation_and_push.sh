#!/bin/sh
set -eu

# Host-side runner for TrueNAS/Docker deployments.
# It runs the report inside the app container, then commits and pushes only the
# two safe validation report files from the host Git checkout.

APP_DIR="${PAPER2REAL_APP_DIR:-/mnt/dl/dl/paper2real}"
CONTAINER="${PAPER2REAL_CONTAINER:-paper2real}"
REMOTE_URL="${PAPER2REAL_GIT_REMOTE:-git@github.com:benyamin-persia/paper2real.git}"
BRANCH="${PAPER2REAL_GIT_BRANCH:-main}"

SAFE_JSON="data/reports/daily_validation_report.json"
SAFE_MD="data/reports/daily_validation_report.md"
SAFE_FILES="$SAFE_JSON $SAFE_MD"

cd "$APP_DIR"
mkdir -p data/logs

echo "[daily-validation] $(date -u '+%Y-%m-%dT%H:%M:%SZ') running report"
docker exec -e DAILY_VALIDATION_AUTOPUSH=false "$CONTAINER" sh -lc 'cd /app && python daily_validation_report.py'

echo "[daily-validation] validating report safety flags"
docker exec "$CONTAINER" sh -lc 'cd /app && python - <<'"'"'PY'"'"'
import json
from pathlib import Path
p = Path("data/reports/daily_validation_report.json")
d = json.loads(p.read_text(encoding="utf-8"))
if not d.get("download_zip_safe") or not d.get("secrets_excluded"):
    raise SystemExit("unsafe download ZIP or secret exclusion check failed; aborting Git push")
print("report_safe=true")
PY'

if [ ! -d .git ]; then
  echo "[daily-validation] initializing host Git checkout"
  git init
  git remote add origin "$REMOTE_URL"
  if [ -f "$HOME/.ssh/paper2real_deploy" ]; then
    git config core.sshCommand "ssh -i $HOME/.ssh/paper2real_deploy -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
  fi
  git fetch origin "$BRANCH"
  git reset --mixed "origin/$BRANCH"
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  git remote add origin "$REMOTE_URL"
fi

git config user.name "${PAPER2REAL_GIT_USER_NAME:-Paper2Real Monitor}"
git config user.email "${PAPER2REAL_GIT_USER_EMAIL:-paper2real-monitor@users.noreply.github.com}"
if [ -f "$HOME/.ssh/paper2real_deploy" ]; then
  git config core.sshCommand "ssh -i $HOME/.ssh/paper2real_deploy -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
fi

PRE_STAGED="$(git diff --cached --name-only)"
if [ -n "$PRE_STAGED" ]; then
  echo "$PRE_STAGED" | while IFS= read -r path; do
    case "$path" in
      "$SAFE_JSON"|"$SAFE_MD") ;;
      *)
        echo "[daily-validation] unsafe pre-existing staged file: $path" >&2
        exit 1
        ;;
    esac
  done
fi

git add -- $SAFE_FILES

STAGED="$(git diff --cached --name-only)"
if [ -z "$STAGED" ]; then
  echo "[daily-validation] no report changes to push"
  exit 0
fi

echo "$STAGED" | while IFS= read -r path; do
  case "$path" in
    "$SAFE_JSON"|"$SAFE_MD") ;;
    *)
      git reset -- $SAFE_FILES >/dev/null 2>&1 || true
      echo "[daily-validation] unsafe staged file: $path" >&2
      exit 1
      ;;
  esac
done

echo "[daily-validation] staged files:"
git status --short

git commit -m "Update daily validation report" -- $SAFE_FILES
git push origin "$BRANCH"
echo "[daily-validation] pushed safe validation reports"
