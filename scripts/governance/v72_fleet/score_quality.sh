#!/usr/bin/env bash
# V67-C Fleet Agent #1: Code Quality
# Runs frontend typecheck + lint + vitest. Output JSON.
# Score = typecheck(30) + lint(20) + vitest(50) — all 0 or full marks
# (binary at this granularity; iter 1+ refines to pass-rate weighting).
set -o pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

agent="code_quality"
dim="代码质量"
weight=0.12
evidence=()
failures=()

typecheck_pass=0
lint_pass=0
vitest_pass=0
vitest_passed=0
vitest_total=0

if [ -d "ui/frontend" ]; then
  cd ui/frontend

  if npm run typecheck > /tmp/v67c_typecheck.log 2>&1; then
    typecheck_pass=1
    evidence+=("typecheck: PASS (tsc --noEmit clean)")
  else
    err_count=$(grep -cE "error TS" /tmp/v67c_typecheck.log 2>/dev/null || echo 0)
    failures+=("typecheck: ${err_count} TS errors · see /tmp/v67c_typecheck.log")
  fi

  if npm run lint > /tmp/v67c_lint.log 2>&1; then
    lint_pass=1
    evidence+=("lint: PASS (eslint clean)")
  else
    err_count=$(grep -cE "error" /tmp/v67c_lint.log 2>/dev/null || echo 0)
    failures+=("lint: ${err_count} errors · see /tmp/v67c_lint.log")
  fi

  if npm run test > /tmp/v67c_vitest.log 2>&1; then
    vitest_pass=1
    line=$(grep -E "Tests +[0-9]+ passed" /tmp/v67c_vitest.log | tail -1)
    vitest_passed=$(echo "$line" | grep -oE "[0-9]+ passed" | head -1 | grep -oE "[0-9]+" || echo 0)
    evidence+=("vitest: PASS (${vitest_passed} tests · /tmp/v67c_vitest.log)")
  else
    fail_count=$(grep -cE "FAIL " /tmp/v67c_vitest.log 2>/dev/null || echo "?")
    failures+=("vitest: ${fail_count} suites failed · see /tmp/v67c_vitest.log")
  fi

  cd - > /dev/null
else
  failures+=("ui/frontend not found")
fi

score=$(( typecheck_pass * 30 + lint_pass * 20 + vitest_pass * 50 ))

# JSON output (jq -c via heredoc)
python3 - <<PYEOF
import json
print(json.dumps({
  "agent": "$agent",
  "dim": "$dim",
  "weight": $weight,
  "score": $score,
  "subscores": {
    "typecheck": $typecheck_pass,
    "lint": $lint_pass,
    "vitest": $vitest_pass,
    "vitest_passed_count": "$vitest_passed",
  },
  "evidence": $(printf '%s\n' "${evidence[@]}" | jq -R . | jq -sc .),
  "failures": $(printf '%s\n' "${failures[@]}" | jq -R . | jq -sc .),
  "honest_note": "subscores binary at iter 0; refine to pass-rate weighting at iter 1+ if vitest fails partially"
}, ensure_ascii=False, indent=2))
PYEOF
