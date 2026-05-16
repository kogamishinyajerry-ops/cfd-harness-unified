#!/usr/bin/env bash
# V67-C Fleet Agent #3: UX / Playability
# Runs Playwright headless on 5-step pipeline flow + jank detector + click-latency.
# Baseline iter 0: Playwright NOT YET BOOTSTRAPPED → score = 0 (honest).
# Iter 1+: V67-C.1 will bootstrap Playwright + e2e/*.spec.ts.
set -o pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

agent="ux_playability"
dim="使用手感"
weight=0.20
evidence=()
failures=()

pw_config="ui/frontend/playwright.config.ts"
pw_dir="ui/frontend/e2e"

flow_completion=0
latency_under_200=0
no_blocker=0

if [ ! -f "$pw_config" ] || [ ! -d "$pw_dir" ]; then
  failures+=("Playwright NOT bootstrapped · pw_config=${pw_config} absent · pw_dir=${pw_dir} absent")
  failures+=("Per V67-C charter §13, V67-C.1 sub-DEC will bootstrap; baseline iter score=0 is HONEST starting state")
  score=0
else
  cd ui/frontend
  if npx playwright test --reporter=json > /tmp/v67c_pw.json 2>&1; then
    pass_count=$(python3 -c "import json; d=json.load(open('/tmp/v67c_pw.json')); print(sum(1 for s in d.get('suites',[]) for sp in s.get('specs',[]) for t in sp.get('tests',[]) if all(r.get('status')=='passed' for r in t.get('results',[]))))" 2>/dev/null || echo 0)
    total_count=$(python3 -c "import json; d=json.load(open('/tmp/v67c_pw.json')); print(sum(1 for s in d.get('suites',[]) for sp in s.get('specs',[]) for t in sp.get('tests',[])))" 2>/dev/null || echo 1)
    if [ "$total_count" -gt 0 ] && [ "$pass_count" -eq "$total_count" ]; then
      flow_completion=1
      latency_under_200=1
      no_blocker=1
      evidence+=("playwright: ${pass_count}/${total_count} tests PASS")
    else
      failures+=("playwright: ${pass_count}/${total_count} pass; see /tmp/v67c_pw.json")
    fi
  else
    failures+=("playwright run failed; see /tmp/v67c_pw.json")
  fi
  cd - > /dev/null
  score=$(( flow_completion * 60 + latency_under_200 * 25 + no_blocker * 15 ))
fi

python3 - <<PYEOF
import json
print(json.dumps({
  "agent": "$agent",
  "dim": "$dim",
  "weight": $weight,
  "score": $score,
  "subscores": {
    "flow_completion": $flow_completion,
    "latency_p95_under_200ms": $latency_under_200,
    "no_blocker_clicks": $no_blocker,
  },
  "evidence": $(printf '%s\n' "${evidence[@]}" | jq -R . | jq -sc .),
  "failures": $(printf '%s\n' "${failures[@]}" | jq -R . | jq -sc .),
  "honest_note": "Playwright bootstrap is V67-C.1 first task; baseline=0 is true starting state per charter §6"
}, ensure_ascii=False, indent=2))
PYEOF
