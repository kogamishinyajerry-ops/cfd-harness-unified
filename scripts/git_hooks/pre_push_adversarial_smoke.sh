#!/usr/bin/env bash
# Pre-push hook: run adversarial smoke suite when backend hot-path code changed.
#
# Operationalizes RETRO-V61-053's executable_smoke_test risk_flag. Catches
# post-R3 defects (Codex APPROVE'd code that fails at runtime) before they
# leave the local machine. Defect 8 (iter06 symmetry constraint type) was
# the prototype case for this discipline.
#
# Install (project-local, non-blocking until you opt in):
#   ln -s ../../scripts/git_hooks/pre_push_adversarial_smoke.sh .git/hooks/pre-push
#
# Or chain it into an existing pre-push:
#   bash scripts/git_hooks/pre_push_adversarial_smoke.sh
#
# Bypass for one push (use sparingly):
#   CFD_SMOKE_OVERRIDE=1 git push
#
# Tunables:
#   CFD_BACKEND_URL    backend URL (default http://127.0.0.1:8003)
#   CFD_SMOKE_FILTER   pass --filter <pattern> to run_smoke.py (default: all)
#   CFD_SMOKE_OVERRIDE skip the smoke run for this push only

set -euo pipefail

if [ "${CFD_SMOKE_OVERRIDE:-}" = "1" ]; then
  echo "✗ adversarial smoke OVERRIDDEN (CFD_SMOKE_OVERRIDE=1) — record why in commit body or DEC."
  exit 0
fi

# Detect whether the push includes commits that touch the backend hot path.
# Scope: import / mesh / BC mapper / case_solve route layer. Adjust the regex
# when new hot-path modules land.
HOTPATH_REGEX='ui/backend/(services/(meshing_gmsh|case_solve|geometry_ingest)|routes/(import_geometry|mesh_imported|case_solve))'

# git pre-push gives us refspecs on stdin; if we're invoked manually (no stdin),
# fall back to comparing against the upstream branch.
CHANGED=""
if [ -t 0 ]; then
  upstream=$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || echo "")
  if [ -n "$upstream" ]; then
    CHANGED=$(git diff --name-only "${upstream}..HEAD" || true)
  else
    CHANGED=$(git diff --name-only HEAD~..HEAD || true)
  fi
else
  while read -r local_ref local_sha remote_ref remote_sha; do
    [ -z "$local_sha" ] && continue
    [ "$local_sha" = "0000000000000000000000000000000000000000" ] && continue
    if [ "$remote_sha" = "0000000000000000000000000000000000000000" ]; then
      # New branch — diff against merge-base with main if available.
      base=$(git merge-base "$local_sha" main 2>/dev/null || echo "$local_sha~")
    else
      base="$remote_sha"
    fi
    CHANGED+=$'\n'$(git diff --name-only "$base".."$local_sha" 2>/dev/null || true)
  done
fi

if ! echo "$CHANGED" | grep -qE "$HOTPATH_REGEX"; then
  exit 0  # no hot-path changes; skip smoke
fi

echo "⚙  Backend hot-path changed — running adversarial smoke suite."
echo "   (override with CFD_SMOKE_OVERRIDE=1 if you've already validated locally.)"

REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT"

# Activate venv if present.
if [ -f .venv/bin/activate ]; then
  # shellcheck source=/dev/null
  source .venv/bin/activate
fi

BASE_URL=${CFD_BACKEND_URL:-http://127.0.0.1:8003}
FILTER_ARGS=()
[ -n "${CFD_SMOKE_FILTER:-}" ] && FILTER_ARGS+=(--filter "$CFD_SMOKE_FILTER")

# Verify backend is up before running (better error than letting the runner
# bail with "network error").
if ! curl -fsS -m 5 "$BASE_URL/api/health" > /dev/null; then
  echo "✗ backend not reachable at $BASE_URL/api/health"
  echo "  start it with: uvicorn ui.backend.main:app --host 127.0.0.1 --port 8003"
  echo "  or override CFD_BACKEND_URL"
  exit 1
fi

if ! python tools/adversarial/run_smoke.py --base-url "$BASE_URL" "${FILTER_ARGS[@]}"; then
  echo ""
  echo "✗ adversarial smoke FAILED"
  echo "  fix the regression OR bypass with: CFD_SMOKE_OVERRIDE=1 git push"
  echo "  (record the bypass reason in your commit body or a DEC)"
  exit 1
fi

echo "✓ adversarial smoke passed."
