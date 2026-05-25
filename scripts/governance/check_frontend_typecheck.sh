#!/usr/bin/env bash
# Frontend TypeScript build gate (DEC-V61-203).
#
# Blocks a commit when `tsc -b` (the same typecheck `npm run build` runs) fails
# for ui/frontend. Wired in .pre-commit-config.yaml with
#   files: ^ui/frontend/.*\.(ts|tsx)$  · pass_filenames: false
# so it only fires when frontend TS/TSX is actually staged, not on every commit.
#
# Why this exists: a prior session marked "7 milestones closed" while
# ui/frontend was RED on `tsc -b` (TopBarV4 step-union error). No gate caught
# it; it surfaced a session later (fixed in M3.11). This makes a broken
# frontend build un-committable.
#
# Override (audited via shell history): `SKIP=frontend-typecheck git commit ...`
# or `git commit --no-verify`.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
FE_DIR="$REPO_ROOT/ui/frontend"
TSC="$FE_DIR/node_modules/.bin/tsc"

# Fresh checkout without `npm install` → cannot typecheck. Warn, do not block
# (blocking here would punish a dependency-install gap, not a code defect).
if [ ! -x "$TSC" ]; then
  echo "⚠ frontend-typecheck: $TSC not found — run 'npm install' in ui/frontend." >&2
  echo "  Skipping the build gate (not blocking on a missing toolchain)." >&2
  exit 0
fi

cd "$FE_DIR"
if "$TSC" -b; then
  exit 0
fi

echo "" >&2
echo "✗ frontend-typecheck: 'tsc -b' failed in ui/frontend." >&2
echo "  Fix the type errors above before committing." >&2
echo "  Intentional override: SKIP=frontend-typecheck git commit ...  (or --no-verify)" >&2
exit 1
