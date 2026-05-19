#!/usr/bin/env bash
# V78 Fleet Agent #3: UX / Playability (V78 TIGHTENED · 100% specs PASS)
# V78 change vs V71: flow_completion full credit ONLY when 100% specs PASS
# (was: ≥17 of N PASS). Forces full playwright suite green.
#
# This is the V73.1-fragility-detection-gap closure (3-retro carry).
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
  cd ui/frontend
  if npx playwright test --reporter=json > /tmp/v78_pw.json 2>/tmp/v78_pw.stderr; then
    pw_exit=0
  else
    pw_exit=$?
  fi

  pass_total=$(python3 - <<'PYEOF'
import json
try:
    d = json.load(open("/tmp/v78_pw.json"))
    def walk(suites):
        for s in suites:
            for sp in s.get("specs", []):
                for t in sp.get("tests", []):
                    yield t
            yield from walk(s.get("suites", []))
    tests = list(walk(d.get("suites", [])))
    total = len(tests)
    passed = sum(
        1 for t in tests
        if all(r.get("status") == "passed" for r in t.get("results", []))
    )
    print(f"{passed} {total}")
except Exception as exc:
    print(f"0 0 # parse error: {exc}")
PYEOF
)
  passed=$(echo "$pass_total" | awk '{print $1}')
  total=$(echo "$pass_total" | awk '{print $2}')

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
    else
      no_blocker_score=0
      failures+=("blocker: ${blockers} click/timeout patterns in stderr")
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
  },
  "evidence": ev,
  "failures": fa,
  "honest_note": "V78 TIGHTENED · flow_completion requires 100% specs PASS (was ≥17) · 3-arc deferred V73.1-fragility-gap closed"
}, ensure_ascii=False, indent=2))
PYEOF
