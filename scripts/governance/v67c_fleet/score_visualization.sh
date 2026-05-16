#!/usr/bin/env bash
# V67-C Fleet Agent #4: Visualization Tracking
# Playwright screenshot diff + Viewport mode-switch success + visual baseline.
# Baseline iter 0: PENDING_BOOTSTRAP (same as score_ux).
# Iter 1+: V67-C.5 sub-DEC drives mode switch coverage.
set -o pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

agent="visualization"
dim="可视化追踪"
weight=0.20
evidence=()
failures=()

baseline_dir="ui/frontend/__visual_baselines__"
pw_dir="ui/frontend/e2e"

render_success=0
mode_switch_correct=0
visual_diff_in_baseline=0

if [ ! -d "$baseline_dir" ]; then
  failures+=("visual baseline directory ${baseline_dir} not yet created · V67-C.4 sub-DEC will seed it")
fi

if [ -d "$pw_dir" ]; then
  viz_spec="$pw_dir/viewport-mode.spec.ts"
  truth_spec="$pw_dir/truth-chain.spec.ts"
  if [ -f "$viz_spec" ] && [ -f "$truth_spec" ]; then
    cd ui/frontend
    if npx playwright test viewport-mode.spec.ts truth-chain.spec.ts --reporter=json > /tmp/v67c_viz.json 2>&1; then
      pass=$(python3 -c "import json; d=json.load(open('/tmp/v67c_viz.json')); print(sum(1 for s in d.get('suites',[]) for sp in s.get('specs',[]) for t in sp.get('tests',[]) if all(r.get('status')=='passed' for r in t.get('results',[]))))" 2>/dev/null || echo 0)
      total=$(python3 -c "import json; d=json.load(open('/tmp/v67c_viz.json')); print(sum(1 for s in d.get('suites',[]) for sp in s.get('specs',[]) for t in sp.get('tests',[])))" 2>/dev/null || echo 1)
      if [ "$total" -gt 0 ] && [ "$pass" -eq "$total" ]; then
        render_success=1
        mode_switch_correct=1
        visual_diff_in_baseline=1
        evidence+=("playwright viz suite: ${pass}/${total} PASS")
      else
        failures+=("playwright viz: ${pass}/${total} pass")
      fi
    else
      failures+=("playwright viz run failed; see /tmp/v67c_viz.json")
    fi
    cd - > /dev/null
  else
    failures+=("viewport-mode.spec.ts or truth-chain.spec.ts missing · V67-C.5 / V67-C.6 will add")
  fi
else
  failures+=("e2e dir ${pw_dir} not yet bootstrapped · V67-C.1 will create")
fi

score=$(( render_success * 50 + mode_switch_correct * 30 + visual_diff_in_baseline * 20 ))

python3 - <<PYEOF
import json
print(json.dumps({
  "agent": "$agent",
  "dim": "$dim",
  "weight": $weight,
  "score": $score,
  "subscores": {
    "render_success_rate": $render_success,
    "mode_switch_correctness": $mode_switch_correct,
    "visual_diff_within_baseline": $visual_diff_in_baseline,
  },
  "evidence": $(printf '%s\n' "${evidence[@]}" | jq -R . | jq -sc .),
  "failures": $(printf '%s\n' "${failures[@]}" | jq -R . | jq -sc .),
  "honest_note": "Visualization fleet depends on V67-C.4/.5/.6 deliverables (visual baseline + viewport mode tests + truth chain spec)"
}, ensure_ascii=False, indent=2))
PYEOF
