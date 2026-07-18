#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

"$PYTHON_BIN" -m pip install \
  --requirement "$ROOT/requirements-dggs.txt" \
  --target "$ROOT/.runtime/dggal" \
  --upgrade

echo "Installed the pinned DGGS runtime at $ROOT/.runtime/dggal"
