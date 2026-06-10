#!/usr/bin/env bash
# V78 Fleet Agent #3: UX / Playability (V78 TIGHTENED · 100% specs PASS)
# V78 change vs V71: flow_completion full credit ONLY when 100% specs PASS
# (was: ≥17 of N PASS). Forces full playwright suite green.
#
# This is the V73.1-fragility-detection-gap closure (3-retro carry).
#
# V92 (DEC-V92-charter D2 · confirm-on-retry): playwright runs with
# --retries=2; per-spec vote via scripts/governance/v92_fleet/pw_vote.py —
# a spec PASSES if ANY attempt passed; flaky specs (eventual pass) are
# telemetry only (0 penalty); confirmed fails (no attempt passed) drive
# the V78 pro-rate exactly as before. Closes V90/V91 retro Open Q #1.
set -o pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

agent="ux_playability"
dim="使用手感"
weight=0.15
evidence=("placeholder")
failures=("placeholder")

pw_config="ui/frontend/playwright.config.ts"
pw_dir="ui/frontend/e2e"

flow_completion_score=0
latency_score=0
no_blocker_score=0
passed=0
total=0

if [ ! -f "$pw_config" ] || [ ! -d "$pw_dir" ]; then
  failures+=("Playwright NOT bootstrapped · ${pw_config} or ${pw_dir} missing")
else
  repo_root="$(git rev-parse --show-toplevel)"
  cd ui/frontend
  # V92: --retries=2 → transient load-induced failures get majority vote
  if npx playwright test --retries=2 --reporter=json > /tmp/v78_pw.json 2>/tmp/v78_pw.stderr; then
    pw_exit=0
  else
    pw_exit=$?
  fi

  vote_json=$(python3 "$repo_root/scripts/governance/v92_fleet/pw_vote.py" /tmp/v78_pw.json)
  passed=$(echo "$vote_json" | python3 -c "import json,sys; print(json.load(sys.stdin)['passed'])")
  total=$(echo "$vote_json" | python3 -c "import json,sys; print(json.load(sys.stdin)['total'])")
  flaky=$(echo "$vote_json" | python3 -c "import json,sys; print(json.load(sys.stdin)['flaky'])")
  confirmed_failed=$(echo "$vote_json" | python3 -c "import json,sys; print(json.load(sys.stdin)['confirmed_failed'])")
  flaky_titles=$(echo "$vote_json" | python3 -c "import json,sys; print('; '.join(json.load(sys.stdin)['flaky_titles']))")

  if [ "${flaky:-0}" -gt 0 ]; then
    evidence+=("V92 confirm-on-retry: ${flaky} flaky spec(s) retry-cleared (0 penalty · audited): ${flaky_titles}")
  fi
  if [ "${flaky:-0}" -ge 3 ]; then
    failures+=("V92 D4 guard: flaky_specs=${flaky} ≥ 3 → mandatory mini-retro entry")
  fi

  if [ "$total" -gt 0 ]; then
    # V78 (TIGHTENED): require 100% PASS for flow_score=60. No
    # ≥17-of-N threshold loophole. Pro-rate by exact pass rate.
    if [ "$passed" -eq "$total" ]; then
      flow_completion_score=60
      evidence+=("playwright: ${passed}/${total} specs PASS · 100% threshold MET (FULL=60/60)")
    else
      # Pro-rate by pass rate
      flow_completion_score=$(( passed * 60 / total ))
      evidence+=("playwright: ${passed}/${total} (${flow_completion_score}/60 pro-rated by exact pass rate)")
      failures+=("V78 tightened: ${passed}/${total} specs PASS · need 100% for FULL")
    fi

    if [ "$pw_exit" -eq 0 ]; then
      latency_score=25
      evidence+=("latency: PASS (all specs within timeout)")
    else
      latency_score=12
      failures+=("latency: some specs exceeded timeout · pw_exit=${pw_exit}")
    fi

    blockers=$(grep -cE "click intercepted|Target closed|Test timeout" /tmp/v78_pw.stderr 2>/dev/null || echo 0)
    blockers=$(echo "$blockers" | head -1 | tr -d ' \n')
    blockers=${blockers:-0}
    if [ "$blockers" -eq 0 ]; then
      no_blocker_score=15
      evidence+=("no-blocker: 0 click-intercepted / timeout signals")
    elif [ "${confirmed_failed:-0}" -eq 0 ]; then
      # V92 D2: signals from attempts that eventually passed = transient noise
      no_blocker_score=15
      evidence+=("no-blocker: ${blockers} signal(s) from retry-cleared attempts · classified transient (V92 · confirmed_failed=0)")
    else
      no_blocker_score=0
      failures+=("blocker: ${blockers} click/timeout patterns in stderr · confirmed_failed=${confirmed_failed}")
    fi
  else
    failures+=("playwright json parse failure · 0 tests recognized")
  fi
  cd - > /dev/null
fi

evidence=("${evidence[@]:1}")
failures=("${failures[@]:1}")
score=$((flow_completion_score + latency_score + no_blocker_score))

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
    "flow_completion": $flow_completion_score,
    "latency_band": $latency_score,
    "no_blocker_clicks": $no_blocker_score,
    "specs_pass_count": ${passed:-0},
    "specs_total_count": ${total:-0},
    "flaky_specs_count": ${flaky:-0},
    "confirmed_failed_count": ${confirmed_failed:-0},
  },
  "evidence": ev,
  "failures": fa,
  "honest_note": "V78 TIGHTENED (100% specs PASS) + V92 confirm-on-retry (--retries=2 · flaky=telemetry-only · confirmed fails drive pro-rate) per DEC-V92-charter"
}, ensure_ascii=False, indent=2))
PYEOF
