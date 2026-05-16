#!/usr/bin/env bash
# V74 Fleet Agent #13 (NEW): Data Fidelity & Auditability
# V74 target: force canonical run_id + provenance hashes + gold-delta + audit-pkg
# to surface as first-class UI affordances (industrial software DNA).
#
# Score axes (each 25):
#   - run_id_visible · TopBar shows backend run_id with data-source=live
#   - gold_delta_visible · TrustGate renders ≥3 per-point gold-delta rows
#   - audit_package_downloadable · download wire exists in TruthChain
#   - byte_repro_hash_visible · 4 provenance-hash chips in TruthChain
set -o pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

agent="data_fidelity"
dim="数据保真度与可审计性"
weight=0.06
evidence=("placeholder")
failures=("placeholder")

v3_dir="ui/frontend/src/pages/workbench/v3"

# 1 · run_id_visible (25)
# Pattern: topbar component has data-testid="topbar-run-id" + data-source="live"
runid_score=0
if grep -rE 'data-testid="topbar-run-id"' "$v3_dir" > /dev/null 2>&1 && \
   grep -rE 'data-source="live"' "$v3_dir/components/TopBarV3.tsx" > /dev/null 2>&1; then
  runid_score=25
  evidence+=("run_id surfaces in TopBar with data-source=live (FULL=25/25)")
elif grep -rE 'data-testid="topbar-run-id"' "$v3_dir" > /dev/null 2>&1; then
  runid_score=12
  evidence+=("run_id testid present but data-source not 'live' (12/25)")
else
  failures+=("TopBar lacks data-testid='topbar-run-id' (V74.3)")
fi

# 2 · gold_delta_visible (25)
# Pattern: TrustGate / GoldDelta panel renders rows w/ data-testid="gold-delta-row"
delta_count=0
delta_count=$(grep -rE "gold-delta-row|trustgate-point-" "$v3_dir" 2>/dev/null | wc -l | tr -d ' ')
delta_score=0
if [ "${delta_count:-0}" -ge 3 ]; then
  delta_score=25
  evidence+=("gold-delta rows: ${delta_count} references (FULL=25/25)")
elif [ "${delta_count:-0}" -gt 0 ]; then
  delta_score=$(( delta_count * 25 / 3 ))
  if [ "$delta_score" -gt 25 ]; then delta_score=25; fi
  evidence+=("gold-delta rows: ${delta_count}/3 (pro-rated=${delta_score}/25)")
else
  failures+=("0 gold-delta rows in v3 (V74.4)")
fi

# 3 · audit_package_downloadable (25)
# Pattern: TruthChain or any v3 surface has a download wire to audit-package
pkg_score=0
if grep -rE "audit-package|auditPackage|buildAuditPackage|audit-package-download" "$v3_dir" > /dev/null 2>&1; then
  pkg_score=25
  evidence+=("audit-package download wire detected in v3 (FULL=25/25)")
else
  failures+=("audit-package download wire missing from v3 (V74.5)")
fi

# 4 · byte_repro_hash_visible (25)
# Pattern: 4 hash chips in TruthChain (corpus_sha / solver_version / mesh_sha / gold_sha)
hash_count=0
hash_count=$(grep -rE "data-testid=\"provenance-hash-(corpus|solver|mesh|gold)\"" "$v3_dir" 2>/dev/null | wc -l | tr -d ' ')
hash_score=0
if [ "${hash_count:-0}" -ge 4 ]; then
  hash_score=25
  evidence+=("4 provenance-hash chips present (FULL=25/25)")
elif [ "${hash_count:-0}" -gt 0 ]; then
  hash_score=$(( hash_count * 25 / 4 ))
  if [ "$hash_score" -gt 25 ]; then hash_score=25; fi
  evidence+=("provenance-hash chips: ${hash_count}/4 (pro-rated=${hash_score}/25)")
else
  failures+=("0 provenance-hash chips in TruthChain (V74.3)")
fi

evidence=("${evidence[@]:1}")
failures=("${failures[@]:1}")
score=$(( runid_score + delta_score + pkg_score + hash_score ))
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
    "run_id_visible": $runid_score,
    "gold_delta_visible": $delta_score,
    "audit_package_downloadable": $pkg_score,
    "byte_repro_hash_visible": $hash_score,
    "gold_delta_row_count": ${delta_count:-0},
    "provenance_hash_count": ${hash_count:-0},
  },
  "evidence": ev,
  "failures": fa,
  "honest_note": "V74 NEW pillar 13 · forces canonical run_id + provenance hashes + gold delta + audit pkg as first-class UI · industrial DNA"
}, ensure_ascii=False, indent=2))
PYEOF
