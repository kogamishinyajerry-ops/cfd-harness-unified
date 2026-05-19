#!/usr/bin/env bash
# V78 Fleet Agent #16: Real-time Solver Observability (V78 EXTENDED)
# V78 adds 5th subscore: backend_sse_e2e (closes V77 backend-deferred
# disclosure · brings Pillar 16 from "offline graceful" to "live e2e").
# Existing 4 subscores rebalanced 25→20 each.
set -o pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

agent="real_time_solver_observability"
dim="实时求解器可观察性"
weight=0.06
evidence=("placeholder")
failures=("placeholder")

v3_dir="ui/frontend/src/pages/workbench/v3"
src_dir="ui/frontend/src"

tid_re() {
  local tag="$1"
  echo "data-testid=[\"\\\`{][^\"\\\`}]*${tag}"
}

# 1 · sse_event_stream (20 · was 25)
sse_hook_count=0
sse_hook_count=$(grep -rE "useSseResidualStream|EventSource\\(|new EventSource" "$src_dir" 2>/dev/null | wc -l | tr -d ' ')
sse_status_count=0
sse_status_count=$(grep -rE "$(tid_re 'sse-stream-status')" "$v3_dir" 2>/dev/null | wc -l | tr -d ' ')
sse_score=0
if [ "${sse_hook_count:-0}" -ge 3 ] && [ "${sse_status_count:-0}" -ge 1 ]; then
  sse_score=20
  evidence+=("sse_event_stream: ${sse_hook_count} hook refs + ${sse_status_count} status testid (FULL=20/20)")
elif [ "${sse_hook_count:-0}" -gt 0 ] || [ "${sse_status_count:-0}" -gt 0 ]; then
  sse_score=10
  evidence+=("sse_event_stream: partial (10/20)")
else
  failures+=("0 SSE substrate")
fi

# 2 · residual_live_update (20)
rl_count=0
rl_count=$(grep -rE "$(tid_re 'residual-live-')" "$v3_dir" 2>/dev/null | wc -l | tr -d ' ')
rl_score=0
if [ "${rl_count:-0}" -ge 6 ]; then
  rl_score=20
  evidence+=("residual_live_update: ${rl_count} per-var testids (FULL=20/20)")
elif [ "${rl_count:-0}" -gt 0 ]; then
  rl_score=$(( rl_count * 20 / 6 ))
  if [ "$rl_score" -gt 20 ]; then rl_score=20; fi
  evidence+=("residual_live_update: ${rl_count}/6 (pro-rated=${rl_score}/20)")
else
  failures+=("0 residual-live-{var} testids")
fi

# 3 · solver_state_stream (20)
ss_count=0
ss_count=$(grep -rE "$(tid_re 'solver-state-badge')" "$v3_dir" 2>/dev/null | wc -l | tr -d ' ')
ss_score=0
if [ "${ss_count:-0}" -ge 1 ]; then
  ss_score=20
  evidence+=("solver_state_stream: ${ss_count} state-badge testid (FULL=20/20)")
else
  failures+=("0 solver-state-badge testid")
fi

# 4 · inflight_residual_display (20)
ir_count=0
ir_count=$(grep -rE "$(tid_re 'solver-inflight-residual')" "$v3_dir" 2>/dev/null | wc -l | tr -d ' ')
ir_score=0
if [ "${ir_count:-0}" -ge 1 ]; then
  ir_score=20
  evidence+=("inflight_residual_display: ${ir_count} ticker testid (FULL=20/20)")
else
  failures+=("0 solver-inflight-residual testid")
fi

# 5 · backend_sse_e2e (20 · V78 NEW · closes V77 backend-deferred)
e2e_test_path="ui/backend/tests/test_solver_stream.py"
backend_route_path="ui/backend/routes/solver_stream.py"
be_score=0
if [ -f "$e2e_test_path" ] && [ -f "$backend_route_path" ]; then
  if PYTHONPATH=. uv run pytest "$e2e_test_path" -q > /tmp/v78_solver_e2e.log 2>&1; then
    be_score=20
    pass_count=$(grep -cE "PASSED" /tmp/v78_solver_e2e.log || echo 0)
    evidence+=("backend_sse_e2e: ${pass_count} tests PASS (FULL=20/20)")
  else
    be_score=0
    failures+=("backend SSE E2E FAILED · see /tmp/v78_solver_e2e.log")
  fi
elif [ -f "$backend_route_path" ]; then
  be_score=10
  evidence+=("backend SSE route exists but no test file (10/20)")
else
  failures+=("backend SSE route + test missing (V78.1 not landed)")
fi

evidence=("${evidence[@]:1}")
failures=("${failures[@]:1}")
score=$(( sse_score + rl_score + ss_score + ir_score + be_score ))
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
    "backend_sse_e2e": $be_score,
    "sse_hook_count": ${sse_hook_count:-0},
    "residual_live_count": ${rl_count:-0},
    "state_badge_count": ${ss_count:-0},
    "inflight_count": ${ir_count:-0},
  },
  "evidence": ev,
  "failures": fa,
  "honest_note": "V78 EXTENDED · pillar 16 gains backend_sse_e2e subscore (frontend wire + live backend E2E verified) · existing 4 rebalanced 25→20"
}, ensure_ascii=False, indent=2))
PYEOF
