#!/usr/bin/env bash
# V68-A Fleet Agent #4: Visualization Tracking (tightened vs V67-C)
# V68-A criteria:
#   - render_success_rate (40) · viewport-mode + truth-chain pass ratio
#   - mode_switch_correctness (30) · ≥4 viewport-mode specs PASS
#   - visual_diff_baseline (30) · ≥6 PNG snapshot files in __visual_baselines__/
# Score = render + mode_switch + baseline (max 100)
set -o pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

agent="visualization"
dim="可视化追踪"
weight=0.15
evidence=("placeholder")
failures=("placeholder")

baseline_dir="ui/frontend/__visual_baselines__"
pw_dir="ui/frontend/e2e"
viz_spec="$pw_dir/viewport-mode.spec.ts"
truth_spec="$pw_dir/truth-chain.spec.ts"

render_score=0
mode_score=0
baseline_score=0

# Visual baseline: count PNG files (≥6 required for FULL · pro-rated below)
png_count=0
if [ -d "$baseline_dir" ]; then
  png_count=$(find "$baseline_dir" -type f -name "*.png" 2>/dev/null | wc -l | tr -d ' ')
  if [ "${png_count:-0}" -ge 22 ]; then
    baseline_score=30
    evidence+=("visual baseline: ${png_count}/22 PNG files (FULL=30/30)")
  elif [ "${png_count:-0}" -gt 0 ]; then
    baseline_score=$(( png_count * 30 / 22 ))
    evidence+=("visual baseline: ${png_count}/22 PNG files (pro-rated=${baseline_score}/30)")
    failures+=("visual baseline incomplete: ${png_count}/22 PNG snapshot files (need ≥22 for V70 close)")
  else
    failures+=("visual baseline empty: 0 PNG files in ${baseline_dir} (need ≥22 for V70 close)")
  fi
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
  if npx playwright test viewport-mode.spec.ts truth-chain.spec.ts --reporter=json > /tmp/v68a_viz.json 2>/tmp/v68a_viz.stderr; then
    pw_exit=0
  else
    pw_exit=$?
  fi

  read passed total viz_specific_pass viz_specific_total <<<"$(python3 - <<'PYEOF'
import json
try:
    d = json.load(open("/tmp/v68a_viz.json"))
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
    # render: pro-rated up to 40
    render_score=$(python3 -c "print(round($passed / $total * 40))")
    evidence+=("viz+truth specs: ${passed}/${total} PASS (render=${render_score}/40)")

    # V68-A criteria: ≥4 viewport-mode specs PASS for full mode_score=30
    if [ "${viz_specific_pass:-0}" -ge 4 ]; then
      mode_score=30
      evidence+=("viewport-mode: ${viz_specific_pass} PASS ≥4 threshold (FULL=30/30)")
    elif [ "${viz_specific_pass:-0}" -gt 0 ]; then
      mode_score=$(( viz_specific_pass * 30 / 4 ))
      evidence+=("viewport-mode: ${viz_specific_pass}/4 PASS (pro-rated=${mode_score}/30)")
      failures+=("viewport-mode specs below threshold: ${viz_specific_pass}/4 (need ≥4 for V68-A.4 close)")
    else
      failures+=("viewport-mode: 0 specs PASS (need ≥4 for V68-A.4 close)")
    fi
  else
    failures+=("viz json parse failure or 0 tests")
  fi
  cd - > /dev/null
fi

evidence=("${evidence[@]:1}")
failures=("${failures[@]:1}")
score=$((render_score + mode_score + baseline_score))
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
    "render_success_rate": $render_score,
    "mode_switch_correctness": $mode_score,
    "visual_diff_baseline": $baseline_score,
    "png_snapshot_count": ${png_count:-0},
    "viewport_mode_specs_pass": ${viz_specific_pass:-0},
  },
  "evidence": ev,
  "failures": fa,
  "honest_note": "V70 tightened · ≥22 PNG snapshot files + ≥4 viewport-mode specs required for full score · pro-rated below threshold"
}, ensure_ascii=False, indent=2))
PYEOF
