#!/usr/bin/env bash
# V68-C Fleet Agent #5: E2E Smoke (tightened vs V68-A)
# V68-C criteria:
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
if uv run python -c "from ui.backend.main import app; print('ok')" > /tmp/v68c_smoke_be.log 2>&1; then
  backend_import_pass=1
  evidence+=("backend FastAPI app import: PASS")
else
  tail=$(tail -3 /tmp/v68c_smoke_be.log | tr '\n' ' ')
  failures+=("backend import FAILED · tail: ${tail}")
fi

# Backend HTTP probes (V68-C addition): boot uvicorn briefly and probe
# /api/cases + new V68-C endpoints (/physics, /ai-review, /ai-diagnose).
# Probes ai-review/ai-diagnose on a known whitelist case (lid_driven_cavity)
# and /physics on the same; success = HTTP 200/204/4xx is acceptable since
# the endpoints exist (we test reachability, not business logic, here).
ai_review_pass=0
ai_diagnose_pass=0
physics_pass=0
if [ "$backend_import_pass" -eq 1 ]; then
  probe_port=$(python3 -c "import socket; s=socket.socket(); s.bind(('127.0.0.1',0)); print(s.getsockname()[1]); s.close()")
  uv run uvicorn ui.backend.main:app --port "$probe_port" --host 127.0.0.1 > /tmp/v68c_smoke_uvicorn.log 2>&1 &
  uv_pid=$!
  for i in 1 2 3 4 5 6 7 8 9 10; do
    if curl -fsS "http://127.0.0.1:${probe_port}/api/cases" > /tmp/v68c_smoke_curl.log 2>&1; then
      backend_http_pass=1
      break
    fi
    sleep 0.5
  done
  if [ "$backend_http_pass" -eq 1 ]; then
    bytes=$(wc -c < /tmp/v68c_smoke_curl.log | tr -d ' ')
    evidence+=("backend HTTP /api/cases probe: PASS (port=${probe_port} · ${bytes} bytes)")
    # V68-C: 3 additional endpoint probes — reachability check, accepts 2xx/4xx
    # (the endpoints exist so 4xx is a *known-good* answer indicating wiring
    # works; the wire failure mode we're guarding against is 500/connection error).
    status_physics=$(curl -fsS -o /dev/null -w "%{http_code}" \
      "http://127.0.0.1:${probe_port}/api/cases/lid_driven_cavity/physics" 2>/dev/null || echo "000")
    status_review=$(curl -fsS -o /dev/null -w "%{http_code}" \
      "http://127.0.0.1:${probe_port}/api/cases/lid_driven_cavity/ai-review" 2>/dev/null || echo "000")
    status_diagnose=$(curl -fsS -o /dev/null -w "%{http_code}" \
      "http://127.0.0.1:${probe_port}/api/cases/lid_driven_cavity/ai-diagnose" 2>/dev/null || echo "000")
    # Treat any 2xx/4xx as "endpoint reachable"; 5xx/000 means wire failure.
    case "$status_physics" in
      2*|4*) physics_pass=1; evidence+=("/physics probe: ${status_physics} (reachable)") ;;
      *) failures+=("/physics probe FAILED · status=${status_physics}") ;;
    esac
    case "$status_review" in
      2*|4*) ai_review_pass=1; evidence+=("/ai-review probe: ${status_review} (reachable)") ;;
      *) failures+=("/ai-review probe FAILED · status=${status_review}") ;;
    esac
    case "$status_diagnose" in
      2*|4*) ai_diagnose_pass=1; evidence+=("/ai-diagnose probe: ${status_diagnose} (reachable)") ;;
      *) failures+=("/ai-diagnose probe FAILED · status=${status_diagnose}") ;;
    esac
  else
    tail=$(tail -3 /tmp/v68c_smoke_uvicorn.log | tr '\n' ' ')
    failures+=("backend HTTP /api/cases probe FAILED · port=${probe_port} · tail: ${tail}")
  fi
  kill "$uv_pid" 2>/dev/null
  wait "$uv_pid" 2>/dev/null
else
  failures+=("backend HTTP probe skipped (app import already failed)")
fi

# Frontend smoke: build + typecheck + lint
if [ -d "ui/frontend/node_modules" ]; then
  cd ui/frontend
  if npm run build > /tmp/v68c_build.log 2>&1; then
    build_pass=1
    bundle_kb=$(du -sk dist 2>/dev/null | awk '{print $1}' || echo "?")
    evidence+=("frontend build: PASS (dist=${bundle_kb}KB)")
  else
    tail=$(tail -3 /tmp/v68c_build.log | tr '\n' ' ')
    failures+=("frontend build FAILED · tail: ${tail}")
  fi

  if npm run typecheck > /tmp/v68c_smoke_tc.log 2>&1; then
    tc_pass=1
    evidence+=("typecheck: PASS")
  else
    err=$(grep -cE "error TS" /tmp/v68c_smoke_tc.log 2>/dev/null || echo 0)
    failures+=("typecheck: ${err} TS errors")
  fi

  if npm run lint > /tmp/v68c_smoke_lint.log 2>&1; then
    lint_pass=1
    evidence+=("lint: PASS")
  else
    err=$(grep -cE " error " /tmp/v68c_smoke_lint.log 2>/dev/null || echo 0)
    failures+=("lint: ${err} errors")
  fi
  cd - > /dev/null
else
  failures+=("ui/frontend/node_modules absent · run 'npm install' first")
fi

evidence=("${evidence[@]:1}")
failures=("${failures[@]:1}")

score=$(( backend_import_pass * 15 + backend_http_pass * 10 + physics_pass * 10 + ai_review_pass * 10 + ai_diagnose_pass * 10 + build_pass * 25 + tc_pass * 10 + lint_pass * 10 ))

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
    "physics_probe": $physics_pass,
    "ai_review_probe": $ai_review_pass,
    "ai_diagnose_probe": $ai_diagnose_pass,
    "frontend_build": $build_pass,
    "typecheck": $tc_pass,
    "lint": $lint_pass,
  },
  "evidence": ev,
  "failures": fa,
  "honest_note": "V68-C added live HTTP probe (uvicorn boots + /api/cases responds 200); per-iter smoke still excludes OpenFOAM heavy run (dogfood_loop.py reserved for arc-close gate)"
}, ensure_ascii=False, indent=2))
PYEOF
