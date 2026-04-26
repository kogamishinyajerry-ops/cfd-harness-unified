#!/usr/bin/env bash
# §11.4 · Workbench quarterly commit quota (DEC-V61-072 + RETRO-V61-005 · 2026-04-26)
#
# Across any rolling 90-day window, no more than 30 commits may land on
# `origin/main` whose primary path is `ui/backend/services/workbench_*` or
# `ui/frontend/pages/workbench/*`.
#
# Severity:
# - >25 commits in 90 days → WARN (yellow flag)
# - >30 commits in 90 days → BLOCK (hard fail)
#
# Authority: Methodology v2.0 §11.4 (active provisional · pending CFDJerry sign-off).
#
# Usage:
#   tools/methodology_guards/workbench_quota_check.sh
#   tools/methodology_guards/workbench_quota_check.sh --warn-only
#
# Exit codes:
#   0 = quota OK (≤25)
#   1 = WARN tier (26-30) — soft warn, proceed
#   2 = BLOCK tier (>30) — hard fail unless --warn-only
#   3 = invocation error

set -euo pipefail

WARN_THRESHOLD=25
BLOCK_THRESHOLD=30
WINDOW_DAYS=90

WARN_ONLY=0
if [ "${1:-}" = "--warn-only" ]; then
    WARN_ONLY=1
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "[workbench_quota] error: not inside a git repo" >&2
    exit 3
fi

# Count commits in the rolling 90-day window touching workbench paths
since_date=$(date -u -v-${WINDOW_DAYS}d +%Y-%m-%d 2>/dev/null || date -u --date="${WINDOW_DAYS} days ago" +%Y-%m-%d)

count=$(git log --since="$since_date" --pretty=format:'%H' -- \
    'ui/backend/services/workbench_*' \
    'ui/frontend/pages/workbench/*' \
    'ui/frontend/src/pages/workbench/*' \
    2>/dev/null | wc -l | tr -d ' ')

echo "[workbench_quota] Rolling ${WINDOW_DAYS}-day window since ${since_date}: ${count} commits"

if [ "$count" -gt "$BLOCK_THRESHOLD" ]; then
    echo "[workbench_quota] BLOCK: ${count} > ${BLOCK_THRESHOLD} commits" >&2
    echo "[workbench_quota] §11.4 Workbench quarterly quota exceeded." >&2
    echo "[workbench_quota] Override: signed Opus 4.7 Gate ruling extends quota by +5; ≤+10/quarter." >&2
    if [ "$WARN_ONLY" -eq 1 ]; then
        exit 1  # demote BLOCK to WARN
    fi
    exit 2
fi

if [ "$count" -gt "$WARN_THRESHOLD" ]; then
    echo "[workbench_quota] WARN: ${count} > ${WARN_THRESHOLD} commits (soft warn, ${BLOCK_THRESHOLD}-commit hard limit nears)" >&2
    exit 1
fi

echo "[workbench_quota] OK (${count} ≤ ${WARN_THRESHOLD})"
exit 0
