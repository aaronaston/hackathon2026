#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ ! -d ".venv" ]]; then
  echo "No .venv found. Creating it now..."
  scripts/setup_venv.sh
fi

source .venv/bin/activate

# Load only OPENAI_API_KEY from .env as data (do not execute the file).
if [[ -z "${OPENAI_API_KEY:-}" && -f ".env" ]]; then
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line#"${line%%[![:space:]]*}"}"
    [[ -z "$line" || "$line" == \#* ]] && continue
    [[ "$line" == export\ * ]] && line="${line#export }"

    if [[ "$line" == OPENAI_API_KEY=* ]]; then
      value="${line#OPENAI_API_KEY=}"
      value="${value%$'\r'}"

      if [[ "$value" == \"*\" && "$value" == *\" ]]; then
        value="${value:1:-1}"
      elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
        value="${value:1:-1}"
      fi

      export OPENAI_API_KEY="$value"
      break
    fi
  done < ".env"
fi

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "OPENAI_API_KEY is not set. Add it to .env and rerun."
  echo "Example: OPENAI_API_KEY=sk-..."
  exit 1
fi

exec python3 scripts/patient_index_agent.py
