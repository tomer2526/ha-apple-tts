#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/tomer2526/ha-apple-tts.git}"
BRANCH="${BRANCH:-main}"
CONFIG_DIR="${1:-/config}"

if ! command -v git >/dev/null 2>&1; then
  echo "git is required" >&2
  exit 1
fi

TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

echo "Cloning ${REPO_URL} (${BRANCH})..."
git clone --depth 1 --branch "${BRANCH}" "${REPO_URL}" "${TMP_DIR}/repo"

SRC_DIR="${TMP_DIR}/repo/custom_components/apple_tts"
DST_DIR="${CONFIG_DIR}/custom_components/apple_tts"

if [[ ! -d "${SRC_DIR}" ]]; then
  echo "source directory not found: ${SRC_DIR}" >&2
  exit 1
fi

mkdir -p "${CONFIG_DIR}/custom_components"
rm -rf "${DST_DIR}"
cp -R "${SRC_DIR}" "${DST_DIR}"

echo "Installed integration to: ${DST_DIR}"
echo "Next step: restart Home Assistant"
