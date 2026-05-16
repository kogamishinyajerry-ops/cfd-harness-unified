#!/usr/bin/env bash
# V67-C Fleet Agent #5: E2E Smoke
# dogfood_loop.py + frontend build + typecheck + lint
# Score = smoke(40) + frontend_build(30) + typecheck(20) + lint(10)
set -o pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

agent="e2e_smoke"
dim="端到端 pipeline"
weight=0.10
evidence=()
failures=()

smoke_pass=0
build_pass=0
tc_pass=0
lint_pass=0

smoke_path="scripts/smoke/dogfood_loop.py"
if [ -f "$smoke_path" ]; then
  if uv run python "$smoke_path" --dry-run 2>/tmp/v67c_smoke.log; then
    smoke_pass=1
    evidence+=("dogfood smoke: PASS (dry-run · $smoke_path)")
  else
    failures+=("dogfood smoke: FAIL · see /tmp/v67c_smoke.log (tail: $(tail -3 /tmp/v67c_smoke.log | tr '\n' ' '))")
  fi
else
  failures+=("smoke script not found: $smoke_path")
fi

if [ -d "ui/frontend" ]; then
  cd ui/frontend
  if npm run build > /tmp/v67c_build.log 2>&1; then
    build_pass=1
    bundle_kb=$(du -sk dist 2>/dev/null | awk '{print $1}' || echo "?")
    evidence+=("frontend build: PASS (dist=${bundle_kb}KB)")
  else
    failures+=("frontend build: FAIL · see /tmp/v67c_build.log")
  fi

  if npm run typecheck > /dev/null 2>&1; then
    tc_pass=1
    evidence+=("typecheck: PASS (re-verified)")
  else
    failures+=("typecheck: FAIL (re-check)")
  fi

  if npm run lint > /dev/null 2>&1; then
    lint_pass=1
    evidence+=("lint: PASS (re-verified)")
  else
    failures+=("lint: FAIL (re-check)")
  fi
  cd - > /dev/null
fi

score=$(( smoke_pass * 40 + build_pass * 30 + tc_pass * 20 + lint_pass * 10 ))

python3 - <<PYEOF
import json
print(json.dumps({
  "agent": "$agent",
  "dim": "$dim",
  "weight": $weight,
  "score": $score,
  "subscores": {
    "smoke": $smoke_pass,
    "frontend_build": $build_pass,
    "typecheck": $tc_pass,
    "lint": $lint_pass,
  },
  "evidence": $(printf '%s\n' "${evidence[@]}" | jq -R . | jq -sc .),
  "failures": $(printf '%s\n' "${failures[@]}" | jq -R . | jq -sc .)
}, ensure_ascii=False, indent=2))
PYEOF
