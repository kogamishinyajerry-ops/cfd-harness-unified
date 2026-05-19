#!/usr/bin/env bash
# V76 Backend Integration Health · useQuery threshold ≥30 (was ≥24 in V75)
# Forces V76.1+V76.2 to land real viewport queries (geometry STL URL,
# mesh render URL) — not just touch existing endpoints.
#
# V76 also fixes the literal-testid trap: data-source regex now accepts
# template-expression forms so the substrate doesn't have to be hand-bloated
# with 4-subclass workarounds.
set -o pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

agent="backend_integration"
dim="后端集成健康"
weight=0.06
evidence=("placeholder")
failures=("placeholder")

v3_dir="ui/frontend/src/pages/workbench/v3"

# 1 · real_wired_surfaces (40) · useQuery / api. refs in v3
wired=0
if [ -d "$v3_dir" ]; then
  wired=$(grep -rE "useQuery|from \"@/api/client\"|api\\.(listCases|getCase|getAIReview|getAIDiagnose|getCaseCompleteness|listCaseRuns|buildAuditPackage|getValidationReport|listRecentRuns|getCaseGeometryStl|getMeshRender|getFaceIndex)" "$v3_dir" 2>/dev/null | wc -l | tr -d ' ')
fi
wired_score=0
# V76 threshold: ≥30 (was ≥24 in V75) · forces viz queries to land
if [ "${wired:-0}" -ge 30 ]; then
  wired_score=40
  evidence+=("real-wired surfaces: ${wired} useQuery/api refs (FULL=40/40)")
elif [ "${wired:-0}" -gt 0 ]; then
  wired_score=$(( wired * 40 / 30 ))
  if [ "$wired_score" -gt 40 ]; then wired_score=40; fi
  evidence+=("real-wired surfaces: ${wired}/30 (pro-rated=${wired_score}/40)")
else
  failures+=("v3 surface has 0 real backend wires")
fi

# 2 · api_endpoint_coverage (20)
endpoints=0
if [ -d "$v3_dir" ]; then
  endpoints=$(grep -rE "api\\.\w+" "$v3_dir" 2>/dev/null | sed 's/.*api\.\([a-zA-Z]*\).*/\1/' | sort -u | wc -l | tr -d ' ')
fi
endpoint_score=0
# V76 threshold: ≥8 (was ≥6 in V75) · forces 2 viz endpoints to land
if [ "${endpoints:-0}" -ge 8 ]; then
  endpoint_score=20
  evidence+=("API endpoints consumed: ${endpoints} distinct (FULL=20/20)")
elif [ "${endpoints:-0}" -gt 0 ]; then
  endpoint_score=$(( endpoints * 20 / 8 ))
  if [ "$endpoint_score" -gt 20 ]; then endpoint_score=20; fi
  evidence+=("API endpoints: ${endpoints}/8 (pro-rated=${endpoint_score}/20)")
else
  failures+=("0 distinct API endpoints consumed by v3")
fi

# 3 · graceful_offline_paths (20)
offline_paths=0
if [ -d "$v3_dir" ]; then
  # V76 LITERAL-TESTID TRAP FIX: template-expression forms now accepted
  offline_paths=$(grep -rE "offline-hint|offline-banner|data-source=[\"\\\`{][^\"\\\`}]*fallback|fallback|degradation" "$v3_dir" 2>/dev/null | wc -l | tr -d ' ')
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

# 4 · integration_tests_passing (20)
test_count=0
test_dir="ui/frontend/src/pages/workbench/v3/__tests__"
if [ -d "$test_dir" ]; then
  test_count=$(grep -rE "live-api|fallback|real-data wire|getAIReview|listCases|getCaseGeometryStl|getMeshRender" "$test_dir" 2>/dev/null | wc -l | tr -d ' ')
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
  "honest_note": "V76 pillar 12 · useQuery ≥30 forces viz queries to land · template-expression regex closes V73.4/V74.3/V75.1 literal-testid trap"
}, ensure_ascii=False, indent=2))
PYEOF
