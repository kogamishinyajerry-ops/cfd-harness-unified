#!/usr/bin/env bash
# V77 Fleet Agent #16 (NEW): Real-time Solver Observability
# V77 target: close 7-arc-aged SSE residuals bookmark from V71.L.
# Industrial CAE table-stakes: Fluent Residual Monitor / STAR-CCM+ convergence plotter.
#
# Score axes (each 25):
#   - sse_event_stream · EventSource hook + typed payloads
#   - residual_live_update · 6 per-variable live testids (p / U_x / U_y / U_z / k / omega)
#   - solver_state_stream · running/converged/diverged badge
#   - inflight_residual_display · last-N ticker
#
# Template-friendly regex inherited from V76 bootstrap.
set -o pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

agent="real_time_solver_observability"
dim="实时求解器可观察性"
weight=0.06
evidence=("placeholder")
failures=("placeholder")

v3_dir="ui/frontend/src/pages/workbench/v3"
hooks_dir="ui/frontend/src/hooks"
src_dir="ui/frontend/src"

# Template-friendly testid regex
tid_re() {
  local tag="$1"
  echo "data-testid=[\"\\\`{][^\"\\\`}]*${tag}"
}

# 1 · sse_event_stream (25)
# Looks for EventSource use AND a useSseResidualStream-shaped hook OR a
# sse-stream-status testid in the v3 surface.
sse_hook_count=0
sse_hook_count=$(grep -rE "useSseResidualStream|EventSource\\(|new EventSource" "$src_dir" 2>/dev/null | wc -l | tr -d ' ')
sse_status_count=0
sse_status_count=$(grep -rE "$(tid_re 'sse-stream-status')" "$v3_dir" 2>/dev/null | wc -l | tr -d ' ')
sse_score=0
if [ "${sse_hook_count:-0}" -ge 3 ] && [ "${sse_status_count:-0}" -ge 1 ]; then
  sse_score=25
  evidence+=("sse_event_stream: ${sse_hook_count} hook refs + ${sse_status_count} status testid (FULL=25/25)")
elif [ "${sse_hook_count:-0}" -gt 0 ] || [ "${sse_status_count:-0}" -gt 0 ]; then
  sse_score=12
  evidence+=("sse_event_stream: partial (hook=${sse_hook_count} status=${sse_status_count}) (pro-rated=12/25)")
else
  failures+=("0 SSE substrate (no EventSource + no sse-stream-status testid)")
fi

# 2 · residual_live_update (25)
# Want 6 distinct testids: residual-live-p / U_x / U_y / U_z / k / omega.
# Count distinct literal occurrences.
rl_count=0
rl_count=$(grep -rE "$(tid_re 'residual-live-')" "$v3_dir" 2>/dev/null | wc -l | tr -d ' ')
rl_score=0
if [ "${rl_count:-0}" -ge 6 ]; then
  rl_score=25
  evidence+=("residual_live_update: ${rl_count} per-var testids (FULL=25/25)")
elif [ "${rl_count:-0}" -gt 0 ]; then
  rl_score=$(( rl_count * 25 / 6 ))
  if [ "$rl_score" -gt 25 ]; then rl_score=25; fi
  evidence+=("residual_live_update: ${rl_count}/6 (pro-rated=${rl_score}/25)")
else
  failures+=("0 residual-live-{var} testids (V77.2 not landed)")
fi

# 3 · solver_state_stream (25)
ss_count=0
ss_count=$(grep -rE "$(tid_re 'solver-state-badge')" "$v3_dir" 2>/dev/null | wc -l | tr -d ' ')
ss_score=0
if [ "${ss_count:-0}" -ge 1 ]; then
  ss_score=25
  evidence+=("solver_state_stream: ${ss_count} state-badge testid (FULL=25/25)")
else
  failures+=("0 solver-state-badge testid (V77.3 not landed)")
fi

# 4 · inflight_residual_display (25)
ir_count=0
ir_count=$(grep -rE "$(tid_re 'solver-inflight-residual')" "$v3_dir" 2>/dev/null | wc -l | tr -d ' ')
ir_score=0
if [ "${ir_count:-0}" -ge 1 ]; then
  ir_score=25
  evidence+=("inflight_residual_display: ${ir_count} ticker testid (FULL=25/25)")
else
  failures+=("0 solver-inflight-residual testid (V77.4 not landed)")
fi

evidence=("${evidence[@]:1}")
failures=("${failures[@]:1}")
score=$(( sse_score + rl_score + ss_score + ir_score ))
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
    "sse_event_stream": $sse_score,
    "residual_live_update": $rl_score,
    "solver_state_stream": $ss_score,
    "inflight_residual_display": $ir_score,
    "sse_hook_count": ${sse_hook_count:-0},
    "sse_status_count": ${sse_status_count:-0},
    "residual_live_count": ${rl_count:-0},
    "state_badge_count": ${ss_count:-0},
    "inflight_count": ${ir_count:-0},
  },
  "evidence": ev,
  "failures": fa,
  "honest_note": "V77 NEW pillar 16 · forces SSE residual streaming · closes 7-arc-aged V71.L bookmark · industrial parity with Fluent/STAR-CCM+ convergence monitors"
}, ensure_ascii=False, indent=2))
PYEOF
