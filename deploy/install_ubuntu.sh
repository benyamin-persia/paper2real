#!/usr/bin/env bash
set -euo pipefail

APP_USER="paper2real"
APP_DIR="/opt/paper2real"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script with sudo."
  exit 1
fi

apt-get update
apt-get install -y \
  python3 python3-venv python3-pip \
  git curl ca-certificates \
  nodejs npm \
  libnss3 libatk-bridge2.0-0 libxkbcommon0 libxcomposite1 libxdamage1 \
  libxrandr2 libgbm1 libasound2t64 libpangocairo-1.0-0 libgtk-3-0

if ! id "${APP_USER}" >/dev/null 2>&1; then
  useradd --system --create-home --shell /bin/bash "${APP_USER}"
fi

mkdir -p "${APP_DIR}"
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"

echo "Copy the project into ${APP_DIR}, then run:"
echo "  sudo -u ${APP_USER} python3 -m venv ${APP_DIR}/venv"
echo "  sudo -u ${APP_USER} ${APP_DIR}/venv/bin/pip install --upgrade pip"
echo "  sudo -u ${APP_USER} ${APP_DIR}/venv/bin/pip install -r ${APP_DIR}/requirements.txt"
echo "  sudo -u ${APP_USER} ${APP_DIR}/venv/bin/python -m playwright install chromium"
echo "  cd ${APP_DIR} && sudo -u ${APP_USER} npm install"
echo "  sudo cp ${APP_DIR}/deploy/systemd/*.service ${APP_DIR}/deploy/systemd/*.timer /etc/systemd/system/"
echo "  sudo chmod +x ${APP_DIR}/deploy/scripts/backup.sh"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl enable --now paper2real.service paper2real-evaluator.timer paper2real-backup.timer"
