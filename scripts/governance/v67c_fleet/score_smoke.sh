#!/usr/bin/env bash
# V67-C Fleet Agent #5: E2E Smoke
# Backend FastAPI import smoke + frontend build + typecheck + lint.
# (dogfood_loop.py is a heavy OpenFOAM smoke — not run per-iter; reserved for
#  major arc-close gates only. This agent ensures the integration surface
#  always builds + types cleanly + lints cleanly, which is the per-iter
#  smoke obligation for V67-C UI work.)
# Score = backend_import(30) + frontend_build(40) + typecheck(15) + lint(15)
set -o pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

agent="e2e_smoke"
dim="端到端 pipeline"
weight=0.10
evidence=("placeholder")  # init non-empty for set-u safety
failures=("placeholder")

backend_import_pass=0
build_pass=0
tc_pass=0
lint_pass=0

# Backend import smoke: FastAPI app constructs without errors
if uv run python -c "from ui.backend.main import app; print('ok')" > /tmp/v67c_smoke_be.log 2>&1; then
  backend_import_pass=1
  evidence+=("backend FastAPI app import: PASS")
else
  tail=$(tail -3 /tmp/v67c_smoke_be.log | tr '\n' ' ')
  failures+=("backend import FAILED · tail: ${tail}")
fi

# Frontend smoke: build + typecheck + lint (re-validates from quality but cheap)
if [ -d "ui/frontend/node_modules" ]; then
  cd ui/frontend
  if npm run build > /tmp/v67c_build.log 2>&1; then
    build_pass=1
    bundle_kb=$(du -sk dist 2>/dev/null | awk '{print $1}' || echo "?")
    evidence+=("frontend build: PASS (dist=${bundle_kb}KB)")
  else
    tail=$(tail -3 /tmp/v67c_build.log | tr '\n' ' ')
    failures+=("frontend build FAILED · tail: ${tail}")
  fi

  if npm run typecheck > /tmp/v67c_smoke_tc.log 2>&1; then
    tc_pass=1
    evidence+=("typecheck: PASS")
  else
    err=$(grep -cE "error TS" /tmp/v67c_smoke_tc.log 2>/dev/null || echo 0)
    failures+=("typecheck: ${err} TS errors")
  fi

  if npm run lint > /tmp/v67c_smoke_lint.log 2>&1; then
    lint_pass=1
    evidence+=("lint: PASS")
  else
    err=$(grep -cE " error " /tmp/v67c_smoke_lint.log 2>/dev/null || echo 0)
    failures+=("lint: ${err} errors")
  fi
  cd - > /dev/null
else
  failures+=("ui/frontend/node_modules absent · run 'npm install' first")
fi

# Drop placeholder elements
evidence=("${evidence[@]:1}")
failures=("${failures[@]:1}")

score=$(( backend_import_pass * 30 + build_pass * 40 + tc_pass * 15 + lint_pass * 15 ))

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
    "frontend_build": $build_pass,
    "typecheck": $tc_pass,
    "lint": $lint_pass,
  },
  "evidence": ev,
  "failures": fa,
  "honest_note": "OpenFOAM heavy smoke (dogfood_loop.py) deferred to arc-close gate; per-iter smoke = integration-surface integrity only"
}, ensure_ascii=False, indent=2))
PYEOF
