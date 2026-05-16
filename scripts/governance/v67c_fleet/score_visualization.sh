#!/usr/bin/env bash
# V67-C Fleet Agent #4: Visualization Tracking
# Checks 3 components:
#   - render_success_rate · viewport-mode.spec.ts + truth-chain.spec.ts pass ratio
#   - mode_switch_correctness · viewport-mode.spec.ts specifically passes
#   - visual_diff_within_baseline · __visual_baselines__/ exists
# Score = 50×render + 30×mode_switch + 20×baseline
set -o pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

agent="visualization"
dim="可视化追踪"
weight=0.20
evidence=("placeholder")
failures=("placeholder")

baseline_dir="ui/frontend/__visual_baselines__"
pw_dir="ui/frontend/e2e"
viz_spec="$pw_dir/viewport-mode.spec.ts"
truth_spec="$pw_dir/truth-chain.spec.ts"

render_score=0
mode_score=0
baseline_score=0

# Visual baseline directory check
if [ -d "$baseline_dir" ]; then
  baseline_score=20
  evidence+=("visual baseline dir present: ${baseline_dir}")
else
  failures+=("visual baseline dir missing: ${baseline_dir}")
fi

# Spec presence + runs
if [ ! -d "$pw_dir" ]; then
  failures+=("e2e dir missing: ${pw_dir}")
elif [ ! -f "$viz_spec" ] || [ ! -f "$truth_spec" ]; then
  failures+=("missing viz specs: viewport-mode.spec.ts or truth-chain.spec.ts")
else
  cd ui/frontend
  if npx playwright test viewport-mode.spec.ts truth-chain.spec.ts --reporter=json > /tmp/v67c_viz.json 2>/tmp/v67c_viz.stderr; then
    pw_exit=0
  else
    pw_exit=$?
  fi

  read passed total viz_specific_pass viz_specific_total <<<"$(python3 - <<'PYEOF'
import json
try:
    d = json.load(open("/tmp/v67c_viz.json"))
    def walk(suites):
        for s in suites:
            for sp in s.get("specs", []):
                for t in sp.get("tests", []):
                    yield s, sp, t
            yield from walk(s.get("suites", []))
    items = list(walk(d.get("suites", [])))
    total = len(items)
    passed = sum(
        1 for _, _, t in items
        if all(r.get("status") == "passed" for r in t.get("results", []))
    )
    # viewport-mode.spec.ts specific
    viz = [it for it in items if "viewport-mode" in (it[1].get("file", "") or "").lower()]
    viz_total = len(viz)
    viz_pass = sum(
        1 for _, _, t in viz
        if all(r.get("status") == "passed" for r in t.get("results", []))
    )
    print(f"{passed} {total} {viz_pass} {viz_total}")
except Exception as exc:
    print(f"0 0 0 0 # parse error: {exc}")
PYEOF
)"

  if [ "${total:-0}" -gt 0 ]; then
    render_score=$(python3 -c "print(round($passed / $total * 50))")
    evidence+=("viz specs: ${passed}/${total} PASS (render=${render_score}/50)")

    if [ "${viz_specific_total:-0}" -gt 0 ]; then
      mode_score=$(python3 -c "print(round($viz_specific_pass / $viz_specific_total * 30))")
      evidence+=("viewport-mode specs: ${viz_specific_pass}/${viz_specific_total} PASS (mode_switch=${mode_score}/30)")
    fi
  else
    failures+=("viz json parse failure or 0 tests")
  fi
  cd - > /dev/null
fi

evidence=("${evidence[@]:1}")
failures=("${failures[@]:1}")
score=$((render_score + mode_score + baseline_score))

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
    "render_success_rate": $render_score,
    "mode_switch_correctness": $mode_score,
    "visual_diff_within_baseline": $baseline_score,
  },
  "evidence": ev,
  "failures": fa,
  "honest_note": "Pro-rated · render + mode_switch from pass ratio · visual diff binary on baseline dir existence (full pixel-diff at V67-C.4.1)"
}, ensure_ascii=False, indent=2))
PYEOF
