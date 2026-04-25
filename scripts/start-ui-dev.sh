#!/usr/bin/env bash
# Starts the CFD Harness UI dev stack (Phase 0..4 MVP):
#   - FastAPI backend on :8000 (uvicorn w/ reload)        [CFD_BACKEND_PORT overrides]
#   - Vite dev server on :5180 (React + HMR, proxies /api) [CFD_FRONTEND_PORT overrides]
#
# Prereqs (one-time):
#   pip install -e ".[ui,dev]"
#   (cd ui/frontend && npm install)
#
# Ctrl-C stops both.

set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ -n "${VIRTUAL_ENV:-}" ]]; then
  echo "→ using virtualenv: ${VIRTUAL_ENV}"
fi

# uvicorn can be installed as a Python module without a bin/uvicorn shim on
# PATH (e.g. user-site installs, Homebrew Python layouts). Detect the module
# rather than the binary, and invoke via `python3 -m`.
if ! python3 -c "import uvicorn" 2>/dev/null; then
  echo "✗ uvicorn Python module not found. Install with: pip install -e '.[ui]'" >&2
  exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "✗ npm not found. Install Node.js >=20 first." >&2
  exit 1
fi

# Ports are overridable so the dev stack can coexist with other projects
# that are already using 8000/5180. 5180 chosen over the Vite default 5173
# to avoid silent "opened the wrong app" incidents when multiple React
# projects live on the same dev box (see 2026-04-22 convergence round).
: "${CFD_BACKEND_PORT:=8000}"
: "${CFD_FRONTEND_PORT:=5180}"

BACKEND_LOG="$(mktemp -t cfd-ui-backend.XXXXXX)"
FRONTEND_LOG="$(mktemp -t cfd-ui-frontend.XXXXXX)"
echo "→ backend log:  $BACKEND_LOG"
echo "→ frontend log: $FRONTEND_LOG"

# --reload-dir scoping (2026-04-25): default --reload watches the entire
# repo. Line B test runs constantly mutate tests/ + src/ files, which
# triggers reload churn and eventually kills the server (observed:
# repeated WatchFiles → "Invalid HTTP request received" → process death,
# leaving the UI gold-validation report unreachable while frontend still
# served stale HTML). Scope reload to ui/backend only — that is the only
# directory whose changes the dev backend actually needs to pick up.
# Other watched paths (templates / static) explicit-add as needed.
python3 -m uvicorn ui.backend.main:app \
  --reload \
  --reload-dir ui/backend \
  --host 127.0.0.1 --port "$CFD_BACKEND_PORT" \
  >"$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
echo "→ backend PID:  $BACKEND_PID  (http://127.0.0.1:$CFD_BACKEND_PORT/api/docs)"

(cd ui/frontend && npm run dev -- --host 127.0.0.1 --port "$CFD_FRONTEND_PORT") \
  >"$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
echo "→ frontend PID: $FRONTEND_PID  (http://127.0.0.1:$CFD_FRONTEND_PORT)"

cleanup() {
  echo ""
  echo "→ stopping frontend (PID $FRONTEND_PID) and backend (PID $BACKEND_PID)…"
  kill "$FRONTEND_PID" 2>/dev/null || true
  kill "$BACKEND_PID" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo ""
echo "→ visit:  http://127.0.0.1:$CFD_FRONTEND_PORT"
echo "→ API:    http://127.0.0.1:$CFD_BACKEND_PORT/api/docs"
echo "→ Ctrl-C to stop."
echo ""
echo "→ tailing logs (press Ctrl-C to stop):"

tail -n +1 -F "$BACKEND_LOG" "$FRONTEND_LOG"
