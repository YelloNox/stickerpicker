#!/usr/bin/env bash
set -euo pipefail
REPO_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
for arg in "$@"; do
  if [[ "$arg" == "--dry-run" || "$arg" == "--help" || "$arg" == "-h" ]]; then
    exec "${TAGGER_PYTHON:-python3}" "$REPO_DIR/scripts/tag-stickers.py" "$@"
  fi
done
if [[ ! -x "$REPO_DIR/.venv-tagger/bin/python" ]]; then
  bash "$REPO_DIR/scripts/setup-tagger.sh" "${TAGGER_BACKEND:-rocm}"
fi
exec "$REPO_DIR/.venv-tagger/bin/python" "$REPO_DIR/scripts/tag-stickers.py" "$@"
