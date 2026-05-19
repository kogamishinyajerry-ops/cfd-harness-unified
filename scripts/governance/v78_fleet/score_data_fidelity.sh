#!/usr/bin/env bash
# V78 Fleet Agent #13: Data Fidelity & Auditability (V78 EXTENDED)
# V78 adds 5th subscore: audit_package_e2e (closes V74.5 wire-unverified
# 4-arc carry). Existing 4 subscores rebalanced 25→20 each.
#
# Score axes (each 20 · total 100):
#   - run_id_visible
#   - gold_delta_visible
#   - audit_package_downloadable (UI wire only)
#   - byte_repro_hash_visible
#   - audit_package_e2e (V78 NEW · END-to-end test passes)
set -o pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

agent="data_fidelity"
dim="数据保真度与可审计性"
weight=0.06
evidence=("placeholder")
failures=("placeholder")

v3_dir="ui/frontend/src/pages/workbench/v3"

# 1 · run_id_visible (20 · was 25)
runid_score=0
if grep -rE 'data-testid="topbar-run-id"' "$v3_dir" > /dev/null 2>&1 && \
   grep -rE 'data-source="live"' "$v3_dir/components/TopBarV3.tsx" > /dev/null 2>&1; then
  runid_score=20
  evidence+=("run_id surfaces in TopBar with data-source=live (FULL=20/20)")
elif grep -rE 'data-testid="topbar-run-id"' "$v3_dir" > /dev/null 2>&1; then
  runid_score=10
  evidence+=("run_id testid present but data-source not 'live' (10/20)")
else
  failures+=("TopBar lacks data-testid='topbar-run-id' (V74.3)")
fi

# 2 · gold_delta_visible (20)
delta_count=0
delta_count=$(grep -rE "gold-delta-row|trustgate-point-" "$v3_dir" 2>/dev/null | wc -l | tr -d ' ')
delta_score=0
if [ "${delta_count:-0}" -ge 3 ]; then
  delta_score=20
  evidence+=("gold-delta rows: ${delta_count} references (FULL=20/20)")
elif [ "${delta_count:-0}" -gt 0 ]; then
  delta_score=$(( delta_count * 20 / 3 ))
  if [ "$delta_score" -gt 20 ]; then delta_score=20; fi
  evidence+=("gold-delta rows: ${delta_count}/3 (pro-rated=${delta_score}/20)")
else
  failures+=("0 gold-delta rows in v3 (V74.4)")
fi

# 3 · audit_package_downloadable (20 · UI wire only)
pkg_score=0
if grep -rE "audit-package|auditPackage|buildAuditPackage|audit-package-download" "$v3_dir" > /dev/null 2>&1; then
  pkg_score=20
  evidence+=("audit-package download wire detected in v3 (FULL=20/20)")
else
  failures+=("audit-package download wire missing from v3 (V74.5)")
fi

# 4 · byte_repro_hash_visible (20)
hash_count=0
hash_count=$(grep -rE "data-testid=\"provenance-hash-(corpus|solver|mesh|gold)\"" "$v3_dir" 2>/dev/null | wc -l | tr -d ' ')
hash_score=0
if [ "${hash_count:-0}" -ge 4 ]; then
  hash_score=20
  evidence+=("4 provenance-hash chips present (FULL=20/20)")
elif [ "${hash_count:-0}" -gt 0 ]; then
  hash_score=$(( hash_count * 20 / 4 ))
  if [ "$hash_score" -gt 20 ]; then hash_score=20; fi
  evidence+=("provenance-hash chips: ${hash_count}/4 (pro-rated=${hash_score}/20)")
else
  failures+=("0 provenance-hash chips in TruthChain (V74.3)")
fi

# 5 · audit_package_e2e (20 · V78 NEW · closes V74.5 4-arc carry)
e2e_test_path="tests/integration/test_audit_package_e2e.py"
e2e_score=0
if [ -f "$e2e_test_path" ]; then
  # Run the smoke; full credit only if all tests pass.
  if PYTHONPATH=. uv run pytest "$e2e_test_path" -q > /tmp/v78_audit_e2e.log 2>&1; then
    e2e_score=20
    pass_count=$(grep -cE "PASSED" /tmp/v78_audit_e2e.log || echo 0)
    evidence+=("audit-package E2E smoke: ${pass_count} tests PASS (FULL=20/20)")
  else
    e2e_score=0
    failures+=("audit-package E2E smoke FAILED · see /tmp/v78_audit_e2e.log")
  fi
else
  failures+=("audit-package E2E smoke test file missing: ${e2e_test_path}")
fi

evidence=("${evidence[@]:1}")
failures=("${failures[@]:1}")
score=$(( runid_score + delta_score + pkg_score + hash_score + e2e_score ))
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
    "audit_package_e2e": $e2e_score,
    "gold_delta_row_count": ${delta_count:-0},
    "provenance_hash_count": ${hash_count:-0},
  },
  "evidence": ev,
  "failures": fa,
  "honest_note": "V78 EXTENDED · pillar 13 gains audit_package_e2e subscore · existing 4 rebalanced 25→20 · V74.5 4-arc carry CLOSED"
}, ensure_ascii=False, indent=2))
PYEOF
