#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 "${SCRIPT_DIR}/stop_tts_server.py" || true
exec "${SCRIPT_DIR}/start_tts.sh"
