#!/usr/bin/env bash
# V71 Fleet Agent #10: Industrial-UI-Benchmark (extended)
# Audits the workbench against top commercial CFD GUIs + v3 blueprint compliance.
#
# V70 subscores (carried forward · re-weighted):
#   - benchmark_doc_present (20)    · .planning/benchmarks/industrial_ui_benchmark.md
#   - axes_evaluated (8)            · ≥6 axes
#   - gui_competitors_compared (8)  · ≥3 GUIs
#   - honest_findings_present (8)   · anti-marketing gate
#
# V71 NEW subscores:
#   - v3_route_mounts (16)          · WorkbenchShellV3 route exists + mounts
#   - v71_ui_tags (12)              · ≥6 V71-UI tagged components/files
#   - v71_baselines (16)            · ≥8 V71 baselines (numbered 23-30)
#   - blueprint_index_exists (4)    · .planning/blueprints/v3/INDEX.md present
#   - v3_palette_compliance (8)     · sand-coral #b78b65 referenced ≥3 places · single accent
#
# Score = sum (max 100)

set -o pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

agent="industrial_ui"
dim="工业UI对标"
weight=0.07
evidence=("placeholder")
failures=("placeholder")

# ─────────── V70 carry-forward subscores ─────────────────────────────

# 1. Benchmark doc presence (20)
doc_score=0
doc=".planning/benchmarks/industrial_ui_benchmark.md"
if [ -f "$doc" ]; then
  doc_score=20
  evidence+=("benchmark doc: ${doc} present (V70)")
else
  failures+=("benchmark doc missing: ${doc}")
fi

# 2. Axes evaluated (8)
axes_count=0
if [ -f "$doc" ]; then
  axes_count=$(grep -ioE "information density|shortcut|panel docking|design token|accessibility|dark mode|scientific typography|color palette|navigation|keyboard" "$doc" 2>/dev/null | sort -u | wc -l | tr -d ' ')
fi
axes_count=${axes_count:-0}
if [ "$axes_count" -ge 6 ]; then
  axes_score=8
  evidence+=("benchmark axes: ${axes_count} (≥6 threshold MET)")
else
  axes_score=$(( axes_count * 8 / 6 ))
  failures+=("benchmark axes: ${axes_count}/6")
fi

# 3. GUI competitors (8)
gui_count=0
if [ -f "$doc" ]; then
  gui_count=$(grep -ioE "ansys fluent|star.ccm|simscale|simcenter|openfoam.gui|comsol|cradle|paraview" "$doc" 2>/dev/null | sort -u | wc -l | tr -d ' ')
fi
gui_count=${gui_count:-0}
if [ "$gui_count" -ge 3 ]; then
  gui_score=8
  evidence+=("GUI competitors: ${gui_count} (≥3 threshold MET)")
else
  gui_score=$(( gui_count * 8 / 3 ))
  failures+=("GUI competitors: ${gui_count}/3")
fi

# 4. Honest findings (8)
honest_score=0
if [ -f "$doc" ]; then
  if grep -ioE "ansys.*better|star.ccm.*better|simscale.*better|commercial.*better at|workbench.*lacks|workbench.*missing|gap vs commercial|behind commercial" "$doc" 2>/dev/null | head -1 > /dev/null; then
    honest_score=8
    evidence+=("benchmark doc: anti-marketing gate MET (honest 'commercial better at X' admission found)")
  else
    failures+=("benchmark doc: anti-marketing gate FAILED (no honest admission)")
  fi
fi

# ─────────── V71 NEW subscores ───────────────────────────────────────

# 5. v3 route mounts (16)
v3_route_score=0
v3_routes=0
if [ -d "ui/frontend/src" ]; then
  # Look for /workbench/v3 route declarations OR WorkbenchShellV3 component imports
  v3_routes=$(grep -rohE "/workbench/v3|WorkbenchShellV3" ui/frontend/src/ 2>/dev/null | sort -u | wc -l | tr -d ' ')
fi
v3_routes=${v3_routes:-0}
if [ "$v3_routes" -ge 2 ]; then
  v3_route_score=16
  evidence+=("v3 route mounts: ${v3_routes} (≥2 V71 threshold MET · /workbench/v3 + WorkbenchShellV3)")
elif [ "$v3_routes" -gt 0 ]; then
  v3_route_score=$(( v3_routes * 16 / 2 ))
  evidence+=("v3 route mounts: ${v3_routes}/2 (pro-rated=${v3_route_score}/16)")
  failures+=("v3 route mounts below threshold: ${v3_routes}/2 (need ≥2 for V71-DONE-1)")
else
  failures+=("v3 route mounts: 0 (need /workbench/v3 route + WorkbenchShellV3 component for V71-DONE-1)")
fi

# 6. V71-UI tags (12)
v71_ui_tags=0
if [ -d "ui/frontend/src" ]; then
  v71_ui_tags=$(grep -rohE "V71.UI|V71-UI|V71.SHELL|V71-SHELL" ui/frontend/src/ 2>/dev/null | wc -l | tr -d ' ')
fi
v71_ui_tags=${v71_ui_tags:-0}
if [ "$v71_ui_tags" -ge 6 ]; then
  v71_ui_score=12
  evidence+=("V71-UI tags in code: ${v71_ui_tags} (≥6 V71 threshold MET)")
elif [ "$v71_ui_tags" -gt 0 ]; then
  v71_ui_score=$(( v71_ui_tags * 12 / 6 ))
  failures+=("V71-UI tags below threshold: ${v71_ui_tags}/6")
else
  v71_ui_score=0
  failures+=("V71-UI tags: 0 (need ≥6 V71-UI/V71-SHELL tags in code for V71-DONE-9)")
fi

# 7. V71 baselines 23-30 (16)
v71_baselines=0
baseline_dir="ui/frontend/__visual_baselines__/chromium/visual-baseline.spec.ts-snapshots"
if [ -d "$baseline_dir" ]; then
  v71_baselines=$(ls "$baseline_dir"/{23,24,25,26,27,28,29,30}-*.png 2>/dev/null | wc -l | tr -d ' ')
fi
v71_baselines=${v71_baselines:-0}
if [ "$v71_baselines" -ge 8 ]; then
  v71_baseline_score=16
  evidence+=("V71 baselines (23-30): ${v71_baselines}/8 (V71-DONE-7 MET)")
elif [ "$v71_baselines" -gt 0 ]; then
  v71_baseline_score=$(( v71_baselines * 16 / 8 ))
  failures+=("V71 baselines: ${v71_baselines}/8 (need ≥8 for V71-DONE-7)")
else
  v71_baseline_score=0
  failures+=("V71 baselines: 0/8 (need ≥8 for V71-DONE-7 · numbered 23-30)")
fi

# 8. Blueprint INDEX exists (4)
blueprint_index_score=0
if [ -f ".planning/blueprints/v3/INDEX.md" ]; then
  blueprint_index_score=4
  evidence+=(".planning/blueprints/v3/INDEX.md present (visual SSOT)")
else
  failures+=("blueprint INDEX.md missing")
fi

# 9. v3 palette compliance (8)
# Sand-coral #b78b65 must appear ≥3 times in frontend (used as accent)
v3_palette_score=0
palette_refs=0
if [ -d "ui/frontend/src" ]; then
  palette_refs=$(grep -rohE "b78b65|#B78B65" ui/frontend/src/ ui/frontend/tailwind.config.ts 2>/dev/null | wc -l | tr -d ' ')
fi
palette_refs=${palette_refs:-0}
if [ "$palette_refs" -ge 3 ]; then
  v3_palette_score=8
  evidence+=("v3 palette: sand-coral #b78b65 referenced ${palette_refs} times (≥3 MET)")
elif [ "$palette_refs" -gt 0 ]; then
  v3_palette_score=$(( palette_refs * 8 / 3 ))
  failures+=("v3 palette: sand-coral referenced ${palette_refs}/3 times")
else
  failures+=("v3 palette: sand-coral #b78b65 not referenced (need ≥3 places in tokens/styles)")
fi

# ─────────── Aggregate ───────────────────────────────────────────────

score=$(( doc_score + axes_score + gui_score + honest_score + v3_route_score + v71_ui_score + v71_baseline_score + blueprint_index_score + v3_palette_score ))
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
    "axes_score": $axes_score,
    "gui_score": $gui_score,
    "honest_score": $honest_score,
    "v3_route_mounts_count": $v3_routes,
    "v3_route_score": $v3_route_score,
    "v71_ui_tags_count": $v71_ui_tags,
    "v71_ui_score": $v71_ui_score,
    "v71_baselines_count": $v71_baselines,
    "v71_baselines_score": $v71_baseline_score,
    "blueprint_index_score": $blueprint_index_score,
    "v3_palette_refs": $palette_refs,
    "v3_palette_score": $v3_palette_score,
  },
  "evidence": ev,
  "failures": fa,
  "honest_note": "V71 industrial-UI agent tightened with v3 blueprint compliance subscores · still enforces V70 anti-marketing gate · expects v3 route + 6 V71-UI tags + 8 baselines + blueprint INDEX + palette compliance"
}, ensure_ascii=False, indent=2))
PYEOF
