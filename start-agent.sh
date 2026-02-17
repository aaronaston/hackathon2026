#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ ! -d ".venv" ]]; then
  echo "No .venv found. Creating it now..."
  scripts/setup_venv.sh
fi

source .venv/bin/activate

if [[ -f ".env" ]]; then
  set -a
  source .env
  set +a
fi

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "OPENAI_API_KEY is not set. Add it to .env and rerun."
  echo "Example: OPENAI_API_KEY=sk-..."
  exit 1
fi

exec python3 scripts/patient_index_agent.py
