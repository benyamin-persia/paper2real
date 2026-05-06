#!/bin/sh
set -eu

# Host-side runner for TrueNAS/Docker deployments.
# It runs the report inside the app container, then commits and pushes only the
# two safe validation report files from the host Git checkout.

APP_DIR="${PAPER2REAL_APP_DIR:-/mnt/dl/dl/paper2real}"
CONTAINER="${PAPER2REAL_CONTAINER:-paper2real}"
REMOTE_URL="${PAPER2REAL_GIT_REMOTE:-git@github.com:benyamin-persia/paper2real.git}"
BRANCH="${PAPER2REAL_GIT_BRANCH:-main}"
GIT_DIR="${PAPER2REAL_GIT_DIR:-$HOME/.paper2real_validation_git}"

SAFE_JSON="data/reports/daily_validation_report.json"
SAFE_MD="data/reports/daily_validation_report.md"
SAFE_FILES="$SAFE_JSON $SAFE_MD"

cd "$APP_DIR"
mkdir -p data/logs

git_cmd() {
  git --git-dir "$GIT_DIR" --work-tree "$APP_DIR" "$@"
}

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

if [ ! -d "$GIT_DIR" ]; then
  echo "[daily-validation] initializing host Git metadata"
  git init --bare "$GIT_DIR"
  git_cmd remote add origin "$REMOTE_URL"
  if [ -f "$HOME/.ssh/paper2real_deploy" ]; then
    git_cmd config core.sshCommand "ssh -i $HOME/.ssh/paper2real_deploy -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
  fi
  git_cmd fetch origin "$BRANCH"
  git_cmd update-ref "refs/heads/$BRANCH" "refs/remotes/origin/$BRANCH"
  git_cmd symbolic-ref HEAD "refs/heads/$BRANCH"
  git_cmd reset --mixed "$BRANCH" >/dev/null
fi

if ! git_cmd remote get-url origin >/dev/null 2>&1; then
  git_cmd remote add origin "$REMOTE_URL"
fi

git_cmd config user.name "${PAPER2REAL_GIT_USER_NAME:-Paper2Real Monitor}"
git_cmd config user.email "${PAPER2REAL_GIT_USER_EMAIL:-paper2real-monitor@users.noreply.github.com}"
if [ -f "$HOME/.ssh/paper2real_deploy" ]; then
  git_cmd config core.sshCommand "ssh -i $HOME/.ssh/paper2real_deploy -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
fi

git_cmd fetch origin "$BRANCH"
git_cmd reset --mixed "origin/$BRANCH" >/dev/null

PRE_STAGED="$(git_cmd diff --cached --name-only)"
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

git_cmd add -- $SAFE_FILES

STAGED="$(git_cmd diff --cached --name-only)"
if [ -z "$STAGED" ]; then
  echo "[daily-validation] no report changes to push"
  exit 0
fi

echo "$STAGED" | while IFS= read -r path; do
  case "$path" in
    "$SAFE_JSON"|"$SAFE_MD") ;;
    *)
      git_cmd reset -- $SAFE_FILES >/dev/null 2>&1 || true
      echo "[daily-validation] unsafe staged file: $path" >&2
      exit 1
      ;;
  esac
done

echo "[daily-validation] staged files:"
git_cmd status --short -- $SAFE_FILES

git_cmd commit -m "Update daily validation report" -- $SAFE_FILES
git_cmd push origin "HEAD:$BRANCH"
echo "[daily-validation] pushed safe validation reports"
