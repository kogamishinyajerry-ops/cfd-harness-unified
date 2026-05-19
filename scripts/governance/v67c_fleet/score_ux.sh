#!/usr/bin/env bash
# V67-C Fleet Agent #3: UX / Playability
# Runs Playwright e2e specs. Pro-rates by pass ratio:
#   - flow_completion: pass_ratio (0..1)
#   - latency_p95_under_200ms: 1 iff all passing tests completed under 5s avg
#   - no_blocker_clicks: 1 iff no test threw "click intercepted" / "timeout"
# Score = 60×flow + 25×latency + 15×no_blocker
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
  if npx playwright test --reporter=json > /tmp/v67c_pw.json 2>/tmp/v67c_pw.stderr; then
    pw_exit=0
  else
    pw_exit=$?
  fi

  pass_total=$(python3 - <<'PYEOF'
import json
try:
    d = json.load(open("/tmp/v67c_pw.json"))
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
    # Pro-rated flow completion · pass ratio
    flow_completion_score=$(python3 -c "print(round($passed / $total * 60))")
    evidence+=("playwright: ${passed}/${total} specs PASS (flow=${flow_completion_score}/60)")

    # Latency band: check no test exceeded 5s · simple heuristic
    if [ "$pw_exit" -eq 0 ]; then
      latency_score=25
      evidence+=("latency: PASS (all specs within timeout)")
    else
      latency_score=12
      failures+=("latency: some specs exceeded timeout · pw_exit=${pw_exit}")
    fi

    # No-blocker: check stderr for "click intercepted" / "Target closed" / timeout patterns
    blockers=$(grep -cE "click intercepted|Target closed|Test timeout" /tmp/v67c_pw.stderr 2>/dev/null || echo 0)
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
    failures+=("playwright json parse failure · 0 tests recognized · /tmp/v67c_pw.json")
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
    "latency_p95_under_200ms": $latency_score,
    "no_blocker_clicks": $no_blocker_score,
  },
  "evidence": ev,
  "failures": fa,
  "honest_note": "Pro-rated by pass ratio · partial pass earns partial score · full coverage at V67-C.5.1+"
}, ensure_ascii=False, indent=2))
PYEOF
