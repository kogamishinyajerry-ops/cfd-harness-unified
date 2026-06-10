#!/usr/bin/env bash
# V67-C Fleet Agent #7: Stability
# Repeated vitest runs (N=3) — detect flake. Memory growth via repeated build.
# Score = 100 - confirmed_fail*30 - mem_growth_pct*5 (clip [0,100])
#
# V92 (DEC-V92-charter D1 · confirm-on-retry): a failing run gets exactly
# ONE isolation retry. Penalty only on CONFIRMED fail (initial FAIL + retry
# FAIL). Transient flake (retry PASS) = telemetry subscore, 0 penalty.
# Closes V90/V91 retro Open Q #1 (1-vote-veto on 1-in-N statistical noise).
# STABILITY_TEST_CMD env overrides the test command (testability hook).
set -o pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

agent="stability"
dim="稳定性"
weight=0.08
evidence=()
failures=()

flake_count=0            # V92: confirmed fails only
transient_flake_count=0  # V92: retry-cleared noise (0 penalty, audited)
runs=3
results=()
test_cmd="${STABILITY_TEST_CMD:-npm run test}"

if [ -d "ui/frontend" ]; then
  cd ui/frontend
  for i in 1 2 3; do
    if bash -c "$test_cmd" > "/tmp/v67c_stability_run_${i}.log" 2>&1; then
      results+=("run${i}=PASS")
    else
      # V92 confirm-on-retry: single isolation retry before penalizing
      if bash -c "$test_cmd" > "/tmp/v67c_stability_run_${i}_retry.log" 2>&1; then
        results+=("run${i}=TRANSIENT(retry PASS)")
        transient_flake_count=$((transient_flake_count + 1))
      else
        results+=("run${i}=CONFIRMED_FAIL")
        flake_count=$((flake_count + 1))
      fi
    fi
  done

  if [ "$flake_count" -eq 0 ]; then
    if [ "$transient_flake_count" -eq 0 ]; then
      evidence+=("stability: ${runs}/${runs} vitest runs PASS · no flake")
    else
      evidence+=("stability: 0 confirmed fail · ${transient_flake_count} transient flake(s) retry-cleared (V92 confirm-on-retry · 0 penalty · audited)")
    fi
  else
    failures+=("stability: ${flake_count}/${runs} runs CONFIRMED FAIL · " "${results[@]}")
  fi
  if [ "$transient_flake_count" -ge 2 ]; then
    failures+=("V92 D4 guard: transient_flake_count=${transient_flake_count} ≥ 2 → mandatory mini-retro entry")
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
    "transient_flake_count": $transient_flake_count,
    "memory_growth_pct": $mem_growth_pct,
  },
  "evidence": $(printf '%s\n' "${evidence[@]}" | jq -R . | jq -sc .),
  "failures": $(printf '%s\n' "${failures[@]}" | jq -R . | jq -sc .)
}, ensure_ascii=False, indent=2))
PYEOF
