#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ ! -d ".venv" ]]; then
  echo "No .venv found. Creating it now..."
  scripts/setup_venv.sh
fi

source .venv/bin/activate

exec python3 scripts/patient_web_app.py --host 127.0.0.1 --port 8080
