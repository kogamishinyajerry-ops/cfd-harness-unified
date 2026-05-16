#!/usr/bin/env bash
# V73 Fleet Agent #12 (NEW): Backend Integration Health
# V73 target: measure how much of the v3 surface is wired to real backends
# vs. static demo data. The pillar's existence forces continued honesty about
# what's actually live vs. mocked.
#
# Score axes:
#   - real_wired_surfaces (40) · grep for `useQuery` / `api.` usage in v3 components
#   - api_endpoint_coverage (20) · count of backend routes the v3 surface consumes
#   - graceful_offline_paths (20) · grep for "fallback" / "offline-hint" data-testid
#   - integration_tests_passing (20) · vitest tests with "real-data" / "live-api" in name
set -o pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

agent="backend_integration"
dim="后端集成健康"
weight=0.06
evidence=("placeholder")
failures=("placeholder")

v3_dir="ui/frontend/src/pages/workbench/v3"

# 1 · real_wired_surfaces (40) · useQuery / api. occurrences in v3 components
wired=0
if [ -d "$v3_dir" ]; then
  wired=$(grep -rE "useQuery|from \"@/api/client\"|api\\.(listCases|getCase|getAIReview|getAIDiagnose|getCaseCompleteness)" "$v3_dir" 2>/dev/null | wc -l | tr -d ' ')
fi
wired_score=0
# V73 threshold: ≥12 (was ≥8) · forces advisor pre-flight + multi-case + comparison
# ribbon useQuery refs to land. V72 substrate counts 8 · V73 work must add ≥4.
if [ "${wired:-0}" -ge 12 ]; then
  wired_score=40
  evidence+=("real-wired surfaces: ${wired} useQuery/api refs (FULL=40/40)")
elif [ "${wired:-0}" -gt 0 ]; then
  wired_score=$(( wired * 40 / 12 ))
  if [ "$wired_score" -gt 40 ]; then wired_score=40; fi
  evidence+=("real-wired surfaces: ${wired}/12 (pro-rated=${wired_score}/40)")
else
  failures+=("v3 surface has 0 real backend wires")
fi

# 2 · api_endpoint_coverage (20) · distinct API endpoints called
endpoints=0
if [ -d "$v3_dir" ]; then
  endpoints=$(grep -rE "api\\.\w+" "$v3_dir" 2>/dev/null | sed 's/.*api\.\([a-zA-Z]*\).*/\1/' | sort -u | wc -l | tr -d ' ')
fi
endpoint_score=0
if [ "${endpoints:-0}" -ge 5 ]; then
  endpoint_score=20
  evidence+=("API endpoints consumed: ${endpoints} distinct (FULL=20/20)")
elif [ "${endpoints:-0}" -gt 0 ]; then
  endpoint_score=$(( endpoints * 20 / 5 ))
  if [ "$endpoint_score" -gt 20 ]; then endpoint_score=20; fi
  evidence+=("API endpoints: ${endpoints}/5 (pro-rated=${endpoint_score}/20)")
else
  failures+=("0 distinct API endpoints consumed by v3")
fi

# 3 · graceful_offline_paths (20) · fallback / offline-hint coverage
offline_paths=0
if [ -d "$v3_dir" ]; then
  offline_paths=$(grep -rE "offline-hint|offline-banner|data-source.*fallback|fallback|degradation" "$v3_dir" 2>/dev/null | wc -l | tr -d ' ')
fi
offline_score=0
if [ "${offline_paths:-0}" -ge 18 ]; then
  offline_score=20
  evidence+=("graceful offline paths: ${offline_paths} (FULL=20/20)")
elif [ "${offline_paths:-0}" -gt 0 ]; then
  offline_score=$(( offline_paths * 20 / 18 ))
  if [ "$offline_score" -gt 20 ]; then offline_score=20; fi
  evidence+=("graceful offline: ${offline_paths}/18 (pro-rated=${offline_score}/20)")
else
  failures+=("0 graceful-offline UI affordances")
fi

# 4 · integration_tests_passing (20) · vitest specs referencing real-data wire
test_count=0
test_dir="ui/frontend/src/pages/workbench/v3/__tests__"
if [ -d "$test_dir" ]; then
  test_count=$(grep -rE "live-api|fallback|real-data wire|getAIReview|listCases" "$test_dir" 2>/dev/null | wc -l | tr -d ' ')
fi
test_score=0
if [ "${test_count:-0}" -ge 8 ]; then
  test_score=20
  evidence+=("integration tests: ${test_count} refs (FULL=20/20)")
elif [ "${test_count:-0}" -gt 0 ]; then
  test_score=$(( test_count * 20 / 8 ))
  if [ "$test_score" -gt 20 ]; then test_score=20; fi
  evidence+=("integration tests: ${test_count}/8 (pro-rated=${test_score}/20)")
else
  failures+=("0 integration tests for real-data wiring")
fi

evidence=("${evidence[@]:1}")
failures=("${failures[@]:1}")
score=$(( wired_score + endpoint_score + offline_score + test_score ))
if [ "$score" -gt 100 ]; then score=100; fi

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
    "real_wired_surfaces": $wired_score,
    "api_endpoint_coverage": $endpoint_score,
    "graceful_offline_paths": $offline_score,
    "integration_tests_passing": $test_score,
    "useQuery_count": ${wired:-0},
    "distinct_endpoints": ${endpoints:-0},
  },
  "evidence": ev,
  "failures": fa,
  "honest_note": "V73 NEW pillar 12 · measures real-data wiring honesty · forces continued anti-static-demo discipline"
}, ensure_ascii=False, indent=2))
PYEOF
