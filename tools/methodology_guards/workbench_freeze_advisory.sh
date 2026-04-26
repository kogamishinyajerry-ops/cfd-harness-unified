#!/usr/bin/env bash
# §11.1 advisory wrapper · DEC-V61-073 A6
#
# Wraps tools/methodology_guards/workbench_freeze.sh in WARN-only mode for the
# dogfood window (2026-04-25 → 2026-05-19). Never blocks commits; emits the
# freeze script's stderr to surface the warning, then exits 0.
#
# After 2026-05-19 dogfood window expires, the wire-up flips from this
# advisory wrapper to the strict freeze script directly (BLOCK on missing
# BREAK_FREEZE escape).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STRICT_SCRIPT="${SCRIPT_DIR}/workbench_freeze.sh"

if [ ! -x "$STRICT_SCRIPT" ]; then
    exit 0
fi

if "$STRICT_SCRIPT" "$@" 2>&1 | sed 's/^/[workbench_freeze ADVISORY] /'; then
    exit 0
fi

echo "[workbench_freeze ADVISORY] §11.1 freeze would have blocked. Advisory mode (dogfood window 2026-04-25 → 2026-05-19) lets this through." >&2
echo "[workbench_freeze ADVISORY] After 2026-05-19, this wrapper flips to strict mode." >&2
exit 0
