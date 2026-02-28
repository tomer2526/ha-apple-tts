#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/tomer2526/ha-apple-tts.git}"
BRANCH="${BRANCH:-main}"
INSTALL_DIR="${1:-${HOME}/ha-apple-tts}"
ENABLE_AUTOSTART="${ENABLE_AUTOSTART:-1}"

if ! command -v git >/dev/null 2>&1; then
  echo "git is required" >&2
  exit 1
fi

if [[ -d "${INSTALL_DIR}/.git" ]]; then
  echo "Updating existing repo at ${INSTALL_DIR}..."
  git -C "${INSTALL_DIR}" fetch origin "${BRANCH}"
  git -C "${INSTALL_DIR}" checkout "${BRANCH}"
  git -C "${INSTALL_DIR}" pull --ff-only origin "${BRANCH}"
else
  echo "Cloning ${REPO_URL} (${BRANCH}) to ${INSTALL_DIR}..."
  git clone --depth 1 --branch "${BRANCH}" "${REPO_URL}" "${INSTALL_DIR}"
fi

SERVER_DIR="${INSTALL_DIR}/macos tts server"

if [[ ! -d "${SERVER_DIR}" ]]; then
  echo "server directory not found: ${SERVER_DIR}" >&2
  exit 1
fi

cd "${SERVER_DIR}"

if [[ -f "stop_tts_server.py" ]]; then
  python3 stop_tts_server.py >/dev/null 2>&1 || true
fi

chmod +x start_tts.sh install_launchagent.sh uninstall_launchagent.sh

if [[ "${ENABLE_AUTOSTART}" == "1" ]]; then
  ./install_launchagent.sh
  echo "macOS TTS server installed with autostart enabled."
else
  echo "Autostart disabled (ENABLE_AUTOSTART=${ENABLE_AUTOSTART})."
  echo "Run manually: cd \"${SERVER_DIR}\" && ./start_tts.sh"
fi

echo "Server path: ${SERVER_DIR}"
