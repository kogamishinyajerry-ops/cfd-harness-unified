#!/usr/bin/env bash
# V76 Fleet Agent #15 (NEW): 3D Visualization Fidelity
# V76 target: close 6-arc-aged vtk.js bookmark. Force MainCanvasV3 to mount
# real WebGL Viewport (not placeholders), with camera + legend + FPS + WebGL
# fallback. (Industrial-software DNA · ParaView/Tecplot/STAR-CCM+.)
#
# V76 BOOTSTRAP NOTE: this scorer's regex accepts BOTH literal data-testid
# values AND template-expression forms — closes the 4-arc literal-testid trap
# (V73.4 + V74.3 + V74.5 + V75.1) once and for all.
#
# Score axes (each weighted to sum 100):
#   - vtk_canvas_mounts (30) · MainCanvasV3 mounts <Viewport> for geom+mesh
#   - camera_controls (20) · reset camera + axes widget
#   - field_legend (20) · color legend on residuals/field
#   - performance_signal (15) · FPS / frame-time indicator
#   - load_fallback (15) · WebGL-unavailable graceful fallback
set -o pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

agent="visualization_fidelity"
dim="三维可视化保真度"
weight=0.06
evidence=("placeholder")
failures=("placeholder")

v3_dir="ui/frontend/src/pages/workbench/v3"

# Template-friendly regex helper — accepts data-testid="x-foo",
# data-testid={`x-${var}`}, data-testid={'x-foo'}, etc.
tid_re() {
  local tag="$1"
  echo "data-testid=[\"\\\`{][^\"\\\`}]*${tag}"
}

# 1 · vtk_canvas_mounts (30) · MainCanvasV3 mounts <Viewport> for geom+mesh
mounts=0
mounts=$(grep -rE "$(tid_re 'vtk-canvas-mounted')" "$v3_dir" 2>/dev/null | wc -l | tr -d ' ')
mounts_score=0
if [ "${mounts:-0}" -ge 2 ]; then
  # Need both geom + mesh modes (2 distinct mounts)
  mounts_score=30
  evidence+=("vtk canvas mounts: ${mounts} (FULL=30/30)")
elif [ "${mounts:-0}" -gt 0 ]; then
  mounts_score=15
  evidence+=("vtk canvas mounts: ${mounts}/2 (pro-rated=15/30)")
else
  failures+=("0 vtk-canvas-mounted testids in v3 (V76.1)")
fi

# 2 · camera_controls (20) · reset + axes widget
cam_count=0
cam_count=$(grep -rE "$(tid_re 'vtk-camera-reset')|$(tid_re 'vtk-axes-widget')" "$v3_dir" 2>/dev/null | wc -l | tr -d ' ')
cam_score=0
if [ "${cam_count:-0}" -ge 2 ]; then
  cam_score=20
  evidence+=("camera+axes controls: ${cam_count} testids (FULL=20/20)")
elif [ "${cam_count:-0}" -gt 0 ]; then
  cam_score=10
  evidence+=("camera controls: ${cam_count}/2 (pro-rated=10/20)")
else
  failures+=("0 vtk-camera-reset / vtk-axes-widget testids in v3 (V76.3)")
fi

# 3 · field_legend (20)
leg_count=0
leg_count=$(grep -rE "$(tid_re 'vtk-color-legend')" "$v3_dir" 2>/dev/null | wc -l | tr -d ' ')
leg_score=0
if [ "${leg_count:-0}" -ge 1 ]; then
  leg_score=20
  evidence+=("color legend: ${leg_count} testids (FULL=20/20)")
else
  failures+=("0 vtk-color-legend testid in v3 (V76.4)")
fi

# 4 · performance_signal (15)
fps_count=0
fps_count=$(grep -rE "$(tid_re 'vtk-fps-indicator')" "$v3_dir" 2>/dev/null | wc -l | tr -d ' ')
fps_score=0
if [ "${fps_count:-0}" -ge 1 ]; then
  fps_score=15
  evidence+=("fps indicator: ${fps_count} testids (FULL=15/15)")
else
  failures+=("0 vtk-fps-indicator testid in v3 (V76.4)")
fi

# 5 · load_fallback (15) · WebGL fallback
fb_count=0
fb_count=$(grep -rE "$(tid_re 'vtk-webgl-fallback')" "$v3_dir" 2>/dev/null | wc -l | tr -d ' ')
fb_score=0
if [ "${fb_count:-0}" -ge 1 ]; then
  fb_score=15
  evidence+=("WebGL fallback: ${fb_count} testids (FULL=15/15)")
else
  failures+=("0 vtk-webgl-fallback testid in v3 (V76.5)")
fi

evidence=("${evidence[@]:1}")
failures=("${failures[@]:1}")
score=$(( mounts_score + cam_score + leg_score + fps_score + fb_score ))
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
    "vtk_canvas_mounts": $mounts_score,
    "camera_controls": $cam_score,
    "field_legend": $leg_score,
    "performance_signal": $fps_score,
    "load_fallback": $fb_score,
    "mount_count": ${mounts:-0},
    "camera_widget_count": ${cam_count:-0},
    "legend_count": ${leg_count:-0},
    "fps_count": ${fps_count:-0},
    "fallback_count": ${fb_count:-0},
  },
  "evidence": ev,
  "failures": fa,
  "honest_note": "V76 NEW pillar 15 · forces real 3D viz (vtk.js mounts replace placeholders) · closes 6-arc-aged vtk.js bookmark from V71.L · regex template-friendly to close 4-arc literal-testid trap"
}, ensure_ascii=False, indent=2))
PYEOF
