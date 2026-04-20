#!/usr/bin/env bash
# Starts the CFD Harness UI dev stack (Phase 0..4 MVP):
#   - FastAPI backend on :8000 (uvicorn w/ reload)
#   - Vite dev server on :5173 (React + HMR, proxies /api → :8000)
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

if ! command -v uvicorn >/dev/null 2>&1; then
  echo "✗ uvicorn not found. Install with: pip install -e '.[ui]'" >&2
  exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "✗ npm not found. Install Node.js >=20 first." >&2
  exit 1
fi

BACKEND_LOG="$(mktemp -t cfd-ui-backend.XXXXXX)"
FRONTEND_LOG="$(mktemp -t cfd-ui-frontend.XXXXXX)"
echo "→ backend log:  $BACKEND_LOG"
echo "→ frontend log: $FRONTEND_LOG"

uvicorn ui.backend.main:app --reload --host 127.0.0.1 --port 8000 \
  >"$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
echo "→ backend PID:  $BACKEND_PID  (http://127.0.0.1:8000/api/docs)"

(cd ui/frontend && npm run dev -- --host 127.0.0.1 --port 5173) \
  >"$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
echo "→ frontend PID: $FRONTEND_PID  (http://127.0.0.1:5173)"

cleanup() {
  echo ""
  echo "→ stopping frontend (PID $FRONTEND_PID) and backend (PID $BACKEND_PID)…"
  kill "$FRONTEND_PID" 2>/dev/null || true
  kill "$BACKEND_PID" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo ""
echo "→ visit:  http://127.0.0.1:5173"
echo "→ API:    http://127.0.0.1:8000/api/docs"
echo "→ Ctrl-C to stop."
echo ""
echo "→ tailing logs (press Ctrl-C to stop):"

tail -n +1 -F "$BACKEND_LOG" "$FRONTEND_LOG"
