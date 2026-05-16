#!/usr/bin/env bash
# V68-A Fleet Agent #3: UX / Playability (tightened vs V67-C)
# V68-A criteria:
#   - flow_completion (60) · ≥5 specs PASS required for FULL · pro-rated below
#   - latency_band (25) · pw_exit 0 within timeouts
#   - no_blocker (15) · no click-intercepted / timeout in stderr
set -o pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

agent="ux_playability"
dim="使用手感"
weight=0.20
evidence=("placeholder")
failures=("placeholder")

pw_config="ui/frontend/playwright.config.ts"
pw_dir="ui/frontend/e2e"

flow_completion_score=0
latency_score=0
no_blocker_score=0

if [ ! -f "$pw_config" ] || [ ! -d "$pw_dir" ]; then
  failures+=("Playwright NOT bootstrapped · ${pw_config} or ${pw_dir} missing")
else
  cd ui/frontend
  if npx playwright test --reporter=json > /tmp/v68a_pw.json 2>/tmp/v68a_pw.stderr; then
    pw_exit=0
  else
    pw_exit=$?
  fi

  pass_total=$(python3 - <<'PYEOF'
import json
try:
    d = json.load(open("/tmp/v68a_pw.json"))
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
    # V68-B (tightened): ≥7 specs PASS for FULL flow_score=60 · pro-rated otherwise
    if [ "$passed" -ge 7 ]; then
      flow_completion_score=60
      evidence+=("playwright: ${passed} specs PASS ≥7 threshold (FULL=60/60)")
    else
      flow_completion_score=$(( passed * 60 / 7 ))
      evidence+=("playwright: ${passed}/7 PASS threshold (pro-rated=${flow_completion_score}/60 · ${passed}/${total} total)")
      failures+=("ux below V68-B threshold: ${passed}/7 specs PASS (need ≥7 for V68-B close)")
    fi

    if [ "$pw_exit" -eq 0 ]; then
      latency_score=25
      evidence+=("latency: PASS (all specs within timeout)")
    else
      latency_score=12
      failures+=("latency: some specs exceeded timeout · pw_exit=${pw_exit}")
    fi

    blockers=$(grep -cE "click intercepted|Target closed|Test timeout" /tmp/v68a_pw.stderr 2>/dev/null || echo 0)
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
    failures+=("playwright json parse failure · 0 tests recognized · /tmp/v68a_pw.json")
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
  "honest_note": "V68-B tightened · ≥7 specs PASS for FULL · pro-rated below"
}, ensure_ascii=False, indent=2))
PYEOF
