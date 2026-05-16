#!/usr/bin/env bash
# V68-B Fleet Agent #5: E2E Smoke (tightened vs V68-A)
# V68-B criteria:
#   - backend_import(20) · fastapi app constructs
#   - backend_http_probe(15) · uvicorn boots + /api/cases responds 200 (NEW)
#   - frontend_build(30)
#   - typecheck(15)
#   - lint(20)
set -o pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

agent="e2e_smoke"
dim="端到端 pipeline"
weight=0.10
evidence=("placeholder")
failures=("placeholder")

backend_import_pass=0
backend_http_pass=0
build_pass=0
tc_pass=0
lint_pass=0

# Backend import smoke: FastAPI app constructs without errors
if uv run python -c "from ui.backend.main import app; print('ok')" > /tmp/v68b_smoke_be.log 2>&1; then
  backend_import_pass=1
  evidence+=("backend FastAPI app import: PASS")
else
  tail=$(tail -3 /tmp/v68b_smoke_be.log | tr '\n' ' ')
  failures+=("backend import FAILED · tail: ${tail}")
fi

# Backend HTTP probe (V68-B addition): boot uvicorn briefly and probe /api/cases
if [ "$backend_import_pass" -eq 1 ]; then
  # Pick a free port to avoid colliding with any running backend.
  probe_port=$(python3 -c "import socket; s=socket.socket(); s.bind(('127.0.0.1',0)); print(s.getsockname()[1]); s.close()")
  uv run uvicorn ui.backend.main:app --port "$probe_port" --host 127.0.0.1 > /tmp/v68b_smoke_uvicorn.log 2>&1 &
  uv_pid=$!
  # Poll up to ~5s for the server to bind.
  for i in 1 2 3 4 5 6 7 8 9 10; do
    if curl -fsS "http://127.0.0.1:${probe_port}/api/cases" > /tmp/v68b_smoke_curl.log 2>&1; then
      backend_http_pass=1
      break
    fi
    sleep 0.5
  done
  kill "$uv_pid" 2>/dev/null
  wait "$uv_pid" 2>/dev/null
  if [ "$backend_http_pass" -eq 1 ]; then
    bytes=$(wc -c < /tmp/v68b_smoke_curl.log | tr -d ' ')
    evidence+=("backend HTTP /api/cases probe: PASS (port=${probe_port} · ${bytes} bytes)")
  else
    tail=$(tail -3 /tmp/v68b_smoke_uvicorn.log | tr '\n' ' ')
    failures+=("backend HTTP /api/cases probe FAILED · port=${probe_port} · tail: ${tail}")
  fi
else
  failures+=("backend HTTP probe skipped (app import already failed)")
fi

# Frontend smoke: build + typecheck + lint
if [ -d "ui/frontend/node_modules" ]; then
  cd ui/frontend
  if npm run build > /tmp/v68b_build.log 2>&1; then
    build_pass=1
    bundle_kb=$(du -sk dist 2>/dev/null | awk '{print $1}' || echo "?")
    evidence+=("frontend build: PASS (dist=${bundle_kb}KB)")
  else
    tail=$(tail -3 /tmp/v68b_build.log | tr '\n' ' ')
    failures+=("frontend build FAILED · tail: ${tail}")
  fi

  if npm run typecheck > /tmp/v68b_smoke_tc.log 2>&1; then
    tc_pass=1
    evidence+=("typecheck: PASS")
  else
    err=$(grep -cE "error TS" /tmp/v68b_smoke_tc.log 2>/dev/null || echo 0)
    failures+=("typecheck: ${err} TS errors")
  fi

  if npm run lint > /tmp/v68b_smoke_lint.log 2>&1; then
    lint_pass=1
    evidence+=("lint: PASS")
  else
    err=$(grep -cE " error " /tmp/v68b_smoke_lint.log 2>/dev/null || echo 0)
    failures+=("lint: ${err} errors")
  fi
  cd - > /dev/null
else
  failures+=("ui/frontend/node_modules absent · run 'npm install' first")
fi

evidence=("${evidence[@]:1}")
failures=("${failures[@]:1}")

score=$(( backend_import_pass * 20 + backend_http_pass * 15 + build_pass * 30 + tc_pass * 15 + lint_pass * 20 ))

python3 - <<PYEOF
import json
ev_raw = """$(printf '%s\n' "${evidence[@]+"${evidence[@]}"}")"""
fa_raw = """$(printf '%s\n' "${failures[@]+"${failures[@]}"}")"""
ev = [l for l in ev_raw.split("\n") if l.strip()]
fa = [l for l in fa_raw.split("\n") if l.strip()]
print(json.dumps({
  "agent": "$agent",
  "dim": "$dim",
  "weight": $weight,
  "score": $score,
  "subscores": {
    "backend_import": $backend_import_pass,
    "backend_http_probe": $backend_http_pass,
    "frontend_build": $build_pass,
    "typecheck": $tc_pass,
    "lint": $lint_pass,
  },
  "evidence": ev,
  "failures": fa,
  "honest_note": "V68-B added live HTTP probe (uvicorn boots + /api/cases responds 200); per-iter smoke still excludes OpenFOAM heavy run (dogfood_loop.py reserved for arc-close gate)"
}, ensure_ascii=False, indent=2))
PYEOF
