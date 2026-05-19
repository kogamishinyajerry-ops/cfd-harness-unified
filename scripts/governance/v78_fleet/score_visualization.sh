#!/usr/bin/env bash
# V78 Fleet Agent #4: Visualization Tracking (V78 EXTENDED · SSIM-aware)
# V78 changes vs V71:
#   - PNG count threshold raised: 30 → 76 (V77 captured · all green)
#   - NEW subscore ssim_tool_present (10) · scripts/visual/ssim_compare.py works
#   - Existing subscores rebalanced: render 35, mode 25, baseline 30, ssim 10
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
ssim_script="scripts/visual/ssim_compare.py"

render_score=0
mode_score=0
baseline_score=0
ssim_score=0

# Visual baseline: count PNG files
png_count=0
if [ -d "$baseline_dir" ]; then
  png_count=$(find "$baseline_dir" -type f -name "*.png" 2>/dev/null | wc -l | tr -d ' ')
  # V78 threshold raised: ≥76 (was 30 in V71) — reflects full V77 baseline set
  if [ "${png_count:-0}" -ge 76 ]; then
    baseline_score=30
    evidence+=("visual baseline: ${png_count} PNG files (FULL=30/30 · V78 raised threshold to 76)")
  elif [ "${png_count:-0}" -gt 0 ]; then
    baseline_score=$(( png_count * 30 / 76 ))
    if [ "$baseline_score" -gt 30 ]; then baseline_score=30; fi
    evidence+=("visual baseline: ${png_count}/76 (pro-rated=${baseline_score}/30)")
    failures+=("V78 tightened: ${png_count}/76 PNG (need 76 for FULL)")
  else
    failures+=("visual baseline empty: 0 PNG files in ${baseline_dir}")
  fi
else
  failures+=("visual baseline dir missing: ${baseline_dir}")
fi

# V78 NEW · ssim_tool_present (10)
# Verifies scripts/visual/ssim_compare.py exists AND self-pair returns SSIM=1.0
if [ -f "$ssim_script" ]; then
  # Pick the first baseline as a sanity-check pair
  sample_png=$(find "$baseline_dir" -type f -name "*.png" 2>/dev/null | head -1)
  if [ -n "$sample_png" ]; then
    ssim_output=$(PYTHONPATH=. uv run python "$ssim_script" "$sample_png" "$sample_png" 2>&1 || true)
    if echo "$ssim_output" | grep -q "SSIM=1\.00000 PASS"; then
      ssim_score=10
      evidence+=("SSIM tool present + self-consistency PASS (FULL=10/10)")
    else
      ssim_score=5
      failures+=("SSIM tool present but self-pair check unexpected: ${ssim_output}")
    fi
  else
    ssim_score=5
    evidence+=("SSIM tool present, no baseline to test against (5/10)")
  fi
else
  failures+=("V78.2 SSIM tool missing: ${ssim_script}")
fi

# Spec presence + runs (existing logic, slight reweight)
passed=0
total=0
viz_specific_pass=0
viz_specific_total=0
if [ ! -d "$pw_dir" ]; then
  failures+=("e2e dir missing: ${pw_dir}")
elif [ ! -f "$viz_spec" ] || [ ! -f "$truth_spec" ]; then
  failures+=("missing viz specs: viewport-mode.spec.ts or truth-chain.spec.ts")
else
  cd ui/frontend
  pw_bin="./node_modules/.bin/playwright"
  if [ ! -x "$pw_bin" ]; then pw_bin="npx playwright"; fi
  if $pw_bin test viewport-mode.spec.ts truth-chain.spec.ts --reporter=json > /tmp/v78_viz.json 2>/tmp/v78_viz.stderr; then
    pw_exit=0
  else
    pw_exit=$?
  fi

  read passed total viz_specific_pass viz_specific_total <<<"$(python3 - <<'PYEOF'
import json
try:
    d = json.load(open("/tmp/v78_viz.json"))
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
    # render: 35 (was 40)
    render_score=$(python3 -c "print(round($passed / $total * 35))")
    evidence+=("viz+truth specs: ${passed}/${total} PASS (render=${render_score}/35)")

    # mode: 25 (was 30)
    if [ "${viz_specific_pass:-0}" -ge 4 ]; then
      mode_score=25
      evidence+=("viewport-mode: ${viz_specific_pass} PASS ≥4 threshold (FULL=25/25)")
    elif [ "${viz_specific_pass:-0}" -gt 0 ]; then
      mode_score=$(( viz_specific_pass * 25 / 4 ))
      evidence+=("viewport-mode: ${viz_specific_pass}/4 (pro-rated=${mode_score}/25)")
    else
      failures+=("viewport-mode: 0 specs PASS")
    fi
  fi
  cd - > /dev/null
fi

evidence=("${evidence[@]:1}")
failures=("${failures[@]:1}")
score=$((render_score + mode_score + baseline_score + ssim_score))
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
    "ssim_tool_present": $ssim_score,
    "png_snapshot_count": ${png_count:-0},
    "viewport_mode_specs_pass": ${viz_specific_pass:-0},
  },
  "evidence": ev,
  "failures": fa,
  "honest_note": "V78 EXTENDED · pillar 4 adds ssim_tool_present (10pts) · baseline threshold raised 30→76 · existing rebalanced · 5-arc SSIM tooling carry CLOSED"
}, ensure_ascii=False, indent=2))
PYEOF
