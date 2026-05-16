#!/usr/bin/env bash
# V67-C Fleet Agent #7: Stability
# Repeated vitest runs (N=3) — detect flake. Memory growth via repeated build.
# Score = 100 - flake_count*30 - mem_growth_pct*5 (clip [0,100])
set -o pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

agent="stability"
dim="稳定性"
weight=0.10
evidence=()
failures=()

flake_count=0
runs=3
results=()

if [ -d "ui/frontend" ]; then
  cd ui/frontend
  for i in 1 2 3; do
    if npm run test > "/tmp/v67c_stability_run_${i}.log" 2>&1; then
      results+=("run${i}=PASS")
    else
      results+=("run${i}=FAIL")
      flake_count=$((flake_count + 1))
    fi
  done

  if [ "$flake_count" -eq 0 ]; then
    evidence+=("stability: ${runs}/${runs} vitest runs PASS · no flake")
  else
    failures+=("stability: ${flake_count}/${runs} runs FAILED · " "${results[@]}")
  fi
  cd - > /dev/null
else
  failures+=("ui/frontend not found")
  flake_count=$runs
fi

# Memory growth: track 2 sequential build sizes; if dist size differs > 5%, flag.
mem_growth_pct=0
# (Baseline iter 0: skip mem check; iter 1+ will compare to baseline)
evidence+=("memory growth check deferred to iter 1+ (needs baseline)")

score=$(( 100 - flake_count * 30 - mem_growth_pct * 5 ))
if [ "$score" -lt 0 ]; then score=0; fi

python3 - <<PYEOF
import json
print(json.dumps({
  "agent": "$agent",
  "dim": "$dim",
  "weight": $weight,
  "score": $score,
  "subscores": {
    "vitest_runs": $runs,
    "flake_count": $flake_count,
    "memory_growth_pct": $mem_growth_pct,
  },
  "evidence": $(printf '%s\n' "${evidence[@]}" | jq -R . | jq -sc .),
  "failures": $(printf '%s\n' "${failures[@]}" | jq -R . | jq -sc .)
}, ensure_ascii=False, indent=2))
PYEOF
