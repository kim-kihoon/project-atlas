#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG="$ROOT/config/atlas_east_asia.json"
export PYTHONPATH="$ROOT/.runtime/dggal${PYTHONPATH:+:$PYTHONPATH}"
export DYLD_LIBRARY_PATH="$ROOT/.runtime/dggal/bin${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"
STAGE="${1:-all}"
if [[ "$STAGE" == "global-validate" ]]; then
  if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 is required for the global-readiness audit." >&2
    exit 2
  fi
  python3 "$ROOT/scripts/validate_global_readiness.py" --config "$CONFIG"
  exit $?
fi

if [[ -n "${QGIS_PROCESS:-}" ]]; then
  QGIS_BIN="$QGIS_PROCESS"
elif command -v qgis_process >/dev/null 2>&1; then
  QGIS_BIN="$(command -v qgis_process)"
else
  QGIS_BIN=""
  for app in /Applications/QGIS*.app "$HOME"/Applications/QGIS*.app; do
    candidate="$app/Contents/MacOS/qgis_process"
    if [[ -x "$candidate" ]]; then
      QGIS_BIN="$candidate"
      break
    fi
  done
fi

if [[ -z "$QGIS_BIN" || ! -x "$QGIS_BIN" ]]; then
  echo "QGIS Processing executable not found." >&2
  echo "Install QGIS LTR 3.44 or set QGIS_PROCESS to qgis_process." >&2
  exit 2
fi

CONTENTS="$(cd "$(dirname "$QGIS_BIN")/.." && pwd)"
export PROJ_DATA="${PROJ_DATA:-$CONTENTS/Resources/qgis/proj}"
export GDAL_DATA="${GDAL_DATA:-$CONTENTS/Resources/qgis/gdal}"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"

run_algorithm() {
  local script="$1"
  "$QGIS_BIN" run "$ROOT/scripts/$script" -- "CONFIG=$CONFIG"
}

case "$STAGE" in
  build)
    run_algorithm build_country_registry.py
    run_algorithm build_east_asia_map.py
    ;;
  borders)
    run_algorithm refresh_border_presentation.py
    ;;
  registry)
    run_algorithm build_country_registry.py
    ;;
  validate)
    run_algorithm validate_east_asia_map.py
    grep -Fq 'Overall result: **PASS**' "$ROOT/reports/east_asia_validation_report.md"
    ;;
  export)
    run_algorithm export_for_unreal.py
    ;;
  all)
    run_algorithm build_country_registry.py
    run_algorithm build_east_asia_map.py
    run_algorithm validate_east_asia_map.py
    grep -Fq 'Overall result: **PASS**' "$ROOT/reports/east_asia_validation_report.md"
    run_algorithm export_for_unreal.py
    ;;
  *)
    echo "Usage: $0 {all|registry|build|borders|validate|global-validate|export}" >&2
    exit 2
    ;;
esac
