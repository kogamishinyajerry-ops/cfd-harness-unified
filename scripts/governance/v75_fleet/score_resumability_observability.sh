#!/usr/bin/env bash
# V75 Fleet Agent #14 (NEW): Resumability & Observability
# V75 target: force engineer-trust signals — error boundaries, real loading
# skeletons, URL state resumability, and TopBar observability indicator.
# (Industrial-software DNA · CATIA, STAR-CCM+, Solidworks, Bloomberg DNA.)
#
# Score axes (each 25):
#   - error_boundary_coverage · ≥3 data-testid="error-boundary-*"
#   - loading_skeleton_coverage · ≥4 data-testid="skeleton-*" surfaces
#   - url_state_resumability · ≥3 search-param sync sites (tab|btab|view)
#   - observability_indicator · TopBar data-testid="observability-*"
set -o pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

agent="resumability_observability"
dim="可恢复性与可观察性"
weight=0.06
evidence=("placeholder")
failures=("placeholder")

v3_dir="ui/frontend/src/pages/workbench/v3"

# 1 · error_boundary_coverage (25)
eb_count=0
eb_count=$(grep -rE "data-testid=\"error-boundary-" "$v3_dir" 2>/dev/null | wc -l | tr -d ' ')
eb_score=0
if [ "${eb_count:-0}" -ge 3 ]; then
  eb_score=25
  evidence+=("error boundaries: ${eb_count} testid'd surfaces (FULL=25/25)")
elif [ "${eb_count:-0}" -gt 0 ]; then
  eb_score=$(( eb_count * 25 / 3 ))
  if [ "$eb_score" -gt 25 ]; then eb_score=25; fi
  evidence+=("error boundaries: ${eb_count}/3 (pro-rated=${eb_score}/25)")
else
  failures+=("0 error boundaries in v3 (V75.1)")
fi

# 2 · loading_skeleton_coverage (25)
sk_count=0
sk_count=$(grep -rE "data-testid=\"skeleton-" "$v3_dir" 2>/dev/null | wc -l | tr -d ' ')
sk_score=0
if [ "${sk_count:-0}" -ge 4 ]; then
  sk_score=25
  evidence+=("loading skeletons: ${sk_count} testid'd (FULL=25/25)")
elif [ "${sk_count:-0}" -gt 0 ]; then
  sk_score=$(( sk_count * 25 / 4 ))
  if [ "$sk_score" -gt 25 ]; then sk_score=25; fi
  evidence+=("loading skeletons: ${sk_count}/4 (pro-rated=${sk_score}/25)")
else
  failures+=("0 loading skeletons in v3 (V75.2)")
fi

# 3 · url_state_resumability (25)
# Pattern: useSearchParams / searchParams.get|set + named keys tab|btab|view
url_count=0
url_count=$(grep -rE "searchParams\\.(get|set)\\(\"(tab|btab|view)\"|useSearchParams" "$v3_dir" 2>/dev/null | wc -l | tr -d ' ')
url_score=0
if [ "${url_count:-0}" -ge 3 ]; then
  url_score=25
  evidence+=("URL state resumability: ${url_count} sync sites (FULL=25/25)")
elif [ "${url_count:-0}" -gt 0 ]; then
  url_score=$(( url_count * 25 / 3 ))
  if [ "$url_score" -gt 25 ]; then url_score=25; fi
  evidence+=("URL state resumability: ${url_count}/3 (pro-rated=${url_score}/25)")
else
  failures+=("0 URL state sync sites in v3 (V75.3)")
fi

# 4 · observability_indicator (25)
obs_count=0
obs_count=$(grep -rE "data-testid=\"observability-" "$v3_dir" 2>/dev/null | wc -l | tr -d ' ')
obs_score=0
if [ "${obs_count:-0}" -ge 2 ]; then
  # Need both TTFB + inflight count = 2 distinct testids
  obs_score=25
  evidence+=("observability: ${obs_count} indicators (FULL=25/25)")
elif [ "${obs_count:-0}" -gt 0 ]; then
  obs_score=12
  evidence+=("observability: ${obs_count}/2 (pro-rated=12/25)")
else
  failures+=("0 observability indicators in v3 (V75.4)")
fi

evidence=("${evidence[@]:1}")
failures=("${failures[@]:1}")
score=$(( eb_score + sk_score + url_score + obs_score ))
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
    "error_boundary_coverage": $eb_score,
    "loading_skeleton_coverage": $sk_score,
    "url_state_resumability": $url_score,
    "observability_indicator": $obs_score,
    "error_boundary_count": ${eb_count:-0},
    "skeleton_count": ${sk_count:-0},
    "url_sync_sites": ${url_count:-0},
    "observability_count": ${obs_count:-0},
  },
  "evidence": ev,
  "failures": fa,
  "honest_note": "V75 NEW pillar 14 · forces engineer-trust signals (error boundaries / skeletons / URL state / observability) · CATIA/STAR-CCM+/Bloomberg DNA"
}, ensure_ascii=False, indent=2))
PYEOF
