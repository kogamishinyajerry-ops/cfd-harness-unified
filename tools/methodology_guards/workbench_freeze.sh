#!/usr/bin/env bash
# §11.1 · Workbench feature freeze (DEC-V61-072 + RETRO-V61-005 · 2026-04-26)
#
# Reject diffs that add files under `ui/backend/services/workbench_*` or
# `ui/frontend/pages/workbench/*` unless the commit message contains
# `BREAK_FREEZE: <rationale>` AND the rationale references an active DEC.
#
# Authority: Methodology v2.0 §11.1 (active provisional · pending CFDJerry sign-off
# in Decisions DB). Co-lands with DEC-V61-072 sampling audit findings: §10.5.4a
# 5 audit-required surfaces explicitly include Workbench because Codex audit
# returned DEGRADATION_RULE_AT_RISK on the M1-M4 + 3-extension arc.
#
# Active until: P4 KOM (Knowledge Object Model) Draft promotes to Active via
# SPEC_PROMOTION_GATE. After that, Workbench schema stabilizes against KOM,
# and this freeze retires (replaced by per-schema gates).
#
# Usage:
#   pre-commit hook (recommended)
#   tools/methodology_guards/workbench_freeze.sh
#
# Exit codes:
#   0 = no Workbench paths touched OR BREAK_FREEZE escape with active DEC
#   1 = Workbench paths touched without proper BREAK_FREEZE escape
#   2 = invocation error (no git, etc.)

set -euo pipefail

# Paths to freeze (per §11.1 scope)
FREEZE_PATTERNS=(
    "ui/backend/services/workbench_"
    "ui/frontend/pages/workbench/"
    "ui/frontend/src/pages/workbench/"
)

# Detect git repo
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "[workbench_freeze] error: not inside a git repo" >&2
    exit 2
fi

# Get diff against staged or HEAD (whichever has changes)
diff_output=$(git diff --cached --name-only --diff-filter=AM 2>/dev/null || true)
if [ -z "$diff_output" ]; then
    # Fallback for ad-hoc invocation outside pre-commit
    diff_output=$(git diff HEAD --name-only --diff-filter=AM 2>/dev/null || true)
fi

if [ -z "$diff_output" ]; then
    exit 0  # nothing to check
fi

# Find any frozen paths in diff
frozen_files=()
while IFS= read -r path; do
    for pattern in "${FREEZE_PATTERNS[@]}"; do
        case "$path" in
            *"$pattern"*) frozen_files+=("$path") ;;
        esac
    done
done <<< "$diff_output"

if [ ${#frozen_files[@]} -eq 0 ]; then
    exit 0
fi

# Frozen paths touched — check commit message for escape
commit_msg_file="${1:-.git/COMMIT_EDITMSG}"
if [ ! -f "$commit_msg_file" ]; then
    # Pre-commit stage — message file doesn't exist yet
    echo "[workbench_freeze] BLOCK: Workbench paths touched in this commit:" >&2
    printf '  %s\n' "${frozen_files[@]}" >&2
    echo "[workbench_freeze] §11.1 Workbench feature freeze active until P4 KOM promotes." >&2
    echo "[workbench_freeze] To break freeze: add 'BREAK_FREEZE: <rationale referencing DEC-V61-XXX>' to commit message." >&2
    echo "[workbench_freeze] Note: pre-commit stage cannot read the commit message; the actual gate fires at commit-msg stage." >&2
    exit 0  # pre-commit warns; commit-msg blocks
fi

if grep -qE "^BREAK_FREEZE:.*DEC-V61-[0-9]+" "$commit_msg_file"; then
    echo "[workbench_freeze] BREAK_FREEZE escape detected with DEC reference. Allowed." >&2
    exit 0
fi

echo "[workbench_freeze] BLOCK: Workbench paths touched without BREAK_FREEZE escape:" >&2
printf '  %s\n' "${frozen_files[@]}" >&2
echo "" >&2
echo "[workbench_freeze] §11.1 Workbench feature freeze (DEC-V61-072 + RETRO-V61-005)." >&2
echo "[workbench_freeze] Active until P4 KOM Draft → Active via SPEC_PROMOTION_GATE." >&2
echo "" >&2
echo "[workbench_freeze] To unblock, add to commit message:" >&2
echo "    BREAK_FREEZE: <rationale referencing DEC-V61-XXX>" >&2
echo "" >&2
echo "[workbench_freeze] Three escape hatches in 30-day window auto-trigger §11.1 review retro." >&2
exit 1
