#!/usr/bin/env bash
# V70 Fleet Agent #10: Industrial-UI-Benchmark
# Audits the workbench against top commercial CFD GUIs.
# Subscores:
#   - benchmark_doc_present (30)     · .planning/benchmarks/industrial_ui_benchmark.md present
#   - axes_evaluated (15)            · benchmark doc covers ≥6 axes (info density / shortcuts / panel docking /
#                                       design tokens / accessibility / dark mode / scientific typography)
#   - gui_competitors_compared (10)  · ≥3 GUIs (ANSYS Fluent / STAR-CCM+ / SimScale / Simcenter / OpenFOAM-GUI)
#   - improvements_landed (25)       · ≥3 improvements LANDED in code
#   - benchmark_baselines (10)       · ≥2 new visual baselines lock V70 UI improvements
#   - honest_findings_present (10)   · doc contains explicit "Commercial GUIs better at X" finding (anti-marketing)
# Score = sum (max 100)

set -o pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

agent="industrial_ui"
dim="工业UI对标"
weight=0.07
evidence=("placeholder")
failures=("placeholder")

# ─────────── 1. Benchmark doc presence ────────────────────────────
doc_score=0
doc=".planning/benchmarks/industrial_ui_benchmark.md"
if [ -f "$doc" ]; then
  doc_score=30
  evidence+=("benchmark doc: ${doc} present")
else
  failures+=("benchmark doc missing: ${doc} (V70-DONE-4)")
fi

# ─────────── 2. Axes evaluated ────────────────────────────────────
axes_score=0
axes_count=0
if [ -f "$doc" ]; then
  # Count distinct evaluation axes (case-insensitive match on common axis names)
  axes_count=$(grep -ioE "information density|shortcut|panel docking|design token|accessibility|dark mode|scientific typography|color palette|navigation|keyboard" "$doc" 2>/dev/null | sort -u | wc -l | tr -d ' ')
fi
axes_count=${axes_count:-0}
if [ "$axes_count" -ge 6 ]; then
  axes_score=15
  evidence+=("benchmark axes evaluated: ${axes_count} (≥6 V70 threshold MET)")
elif [ "$axes_count" -gt 0 ]; then
  axes_score=$(( axes_count * 15 / 6 ))
  evidence+=("benchmark axes: ${axes_count}/6 (pro-rated=${axes_score}/15)")
  failures+=("benchmark axes below threshold: ${axes_count}/6 (need ≥6 for V70 close)")
fi

# ─────────── 3. GUI competitors ───────────────────────────────────
gui_score=0
gui_count=0
if [ -f "$doc" ]; then
  gui_count=$(grep -ioE "ansys fluent|star.ccm|simscale|simcenter|openfoam.gui|comsol|cradle|paraview" "$doc" 2>/dev/null | sort -u | wc -l | tr -d ' ')
fi
gui_count=${gui_count:-0}
if [ "$gui_count" -ge 3 ]; then
  gui_score=10
  evidence+=("GUI competitors compared: ${gui_count} (≥3 V70 threshold MET)")
elif [ "$gui_count" -gt 0 ]; then
  gui_score=$(( gui_count * 10 / 3 ))
  evidence+=("GUI competitors: ${gui_count}/3 (pro-rated=${gui_score}/10)")
  failures+=("GUI competitors below threshold: ${gui_count}/3 (need ≥3 for V70 close)")
fi

# ─────────── 4. Improvements LANDED ───────────────────────────────
# Look for V70-tagged improvements in code: comment-based audit
# Match `V70 UI improvement` / `V70-UI-IMPROVEMENT-` / `// V70-DONE-4` tags
improvements_count=0
if [ -d "ui/frontend/src" ]; then
  improvements_count=$(grep -rohE "V70.UI.IMPROVEMENT|V70.DONE.4|v70.industrial.ui" ui/frontend/src/ 2>/dev/null | wc -l | tr -d ' ')
fi
improvements_count=${improvements_count:-0}
if [ "$improvements_count" -ge 3 ]; then
  improvements_score=25
  evidence+=("UI improvements LANDED: ${improvements_count} (≥3 V70 threshold MET · tag: V70-UI-IMPROVEMENT)")
elif [ "$improvements_count" -gt 0 ]; then
  improvements_score=$(( improvements_count * 25 / 3 ))
  evidence+=("UI improvements: ${improvements_count}/3 (pro-rated=${improvements_score}/25)")
  failures+=("UI improvements below threshold: ${improvements_count}/3 LANDED (need ≥3 tagged V70-UI-IMPROVEMENT for V70-DONE-4)")
else
  improvements_score=0
  failures+=("UI improvements: 0 tagged V70-UI-IMPROVEMENT in code")
fi

# ─────────── 5. Benchmark visual baselines ────────────────────────
benchmark_baselines=0
baseline_dir="ui/frontend/__visual_baselines__/chromium/visual-baseline.spec.ts-snapshots"
if [ -d "$baseline_dir" ]; then
  # V70 baselines = files numbered 19-22 (since V69 closed at 18)
  benchmark_baselines=$(ls "$baseline_dir"/{19,20,21,22}-*.png 2>/dev/null | wc -l | tr -d ' ')
fi
benchmark_baselines=${benchmark_baselines:-0}
if [ "$benchmark_baselines" -ge 2 ]; then
  benchmark_score=10
  evidence+=("V70 UI baselines: ${benchmark_baselines} (19..22) (≥2 V70 threshold MET)")
else
  benchmark_score=$(( benchmark_baselines * 10 / 2 ))
  failures+=("V70 UI baselines: ${benchmark_baselines}/2 (need ≥2 for V70-DONE-4)")
fi

# ─────────── 6. Honest findings (anti-marketing) ──────────────────
honest_score=0
if [ -f "$doc" ]; then
  # Doc must contain honest "commercial GUI is better at X" admission to count
  if grep -ioE "ansys.*better|star.ccm.*better|simscale.*better|commercial.*better at|workbench.*lacks|workbench.*missing|gap vs commercial|behind commercial" "$doc" 2>/dev/null | head -1 > /dev/null; then
    honest_score=10
    evidence+=("benchmark doc carries honest 'commercial better at X' admission (anti-marketing gate MET)")
  else
    failures+=("benchmark doc lacks honest commercial-better admission · failing anti-marketing gate (per V70 charter §6 reverse-stop)")
  fi
fi

score=$(( doc_score + axes_score + gui_score + improvements_score + benchmark_score + honest_score ))
if [ "$score" -gt 100 ]; then score=100; fi

evidence=("${evidence[@]:1}")
failures=("${failures[@]:1}")

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
    "benchmark_doc_score": $doc_score,
    "axes_count": $axes_count,
    "axes_score": $axes_score,
    "gui_count": $gui_count,
    "gui_score": $gui_score,
    "improvements_count": $improvements_count,
    "improvements_score": $improvements_score,
    "benchmark_baselines_count": $benchmark_baselines,
    "benchmark_baselines_score": $benchmark_score,
    "honest_findings_score": $honest_score,
  },
  "evidence": ev,
  "failures": fa,
  "honest_note": "anti-marketing gate: this agent intentionally requires the benchmark doc to admit commercial-GUI strengths. self-promotional benchmark docs fail honest_findings subscore."
}, ensure_ascii=False, indent=2))
PYEOF
