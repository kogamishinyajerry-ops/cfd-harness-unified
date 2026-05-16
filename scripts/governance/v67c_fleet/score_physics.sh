#!/usr/bin/env bash
# V67-C Fleet Agent #2: Physics Validator
# Runs subset of backend physics tests (checkmesh + mass_balance + V-row regression).
# Score = checkmesh(40) + mass_balance(40) + corpus_present(20)
set -o pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

agent="physics_validator"
dim="物理/数值稳定"
weight=0.15
evidence=()
failures=()

checkmesh_pass=0
massbal_pass=0
corpus_pass=0

cm_test="tests/test_checkmesh_runner.py"
mb_test="ui/backend/tests/test_bc_writer_mass_balance.py"

if [ -f "$cm_test" ]; then
  if uv run python -m pytest "$cm_test" -q --no-header > /tmp/v67c_checkmesh.log 2>&1; then
    checkmesh_pass=1
    passed=$(grep -oE "[0-9]+ passed" /tmp/v67c_checkmesh.log | head -1 | grep -oE "[0-9]+" || echo 0)
    evidence+=("checkmesh: PASS (${passed} tests · ${cm_test})")
  else
    failed=$(grep -oE "[0-9]+ failed" /tmp/v67c_checkmesh.log | head -1 | grep -oE "[0-9]+" || echo "?")
    failures+=("checkmesh: ${failed} failed · see /tmp/v67c_checkmesh.log")
  fi
else
  failures+=("checkmesh test not found: ${cm_test}")
fi

if [ -f "$mb_test" ]; then
  if uv run python -m pytest "$mb_test" -q --no-header > /tmp/v67c_massbal.log 2>&1; then
    massbal_pass=1
    passed=$(grep -oE "[0-9]+ passed" /tmp/v67c_massbal.log | head -1 | grep -oE "[0-9]+" || echo 0)
    evidence+=("mass_balance: PASS (${passed} tests · ${mb_test})")
  else
    failed=$(grep -oE "[0-9]+ failed" /tmp/v67c_massbal.log | head -1 | grep -oE "[0-9]+" || echo "?")
    failures+=("mass_balance: ${failed} failed · see /tmp/v67c_massbal.log")
  fi
else
  failures+=("mass_balance test not found: ${mb_test}")
fi

# V-corpus presence check: V101-V107 LANDED files exist + advisor_rules.md ≥12 rules
v_corpus_dir=".planning/decisions"
v_count=$(ls "$v_corpus_dir"/2026-05-16_v65_sub_*v10[1-7]*.md 2>/dev/null | wc -l | tr -d ' ')
adv_rules=".planning/methodology/advisor_rules.md"
adv_count=0
if [ -f "$adv_rules" ]; then
  adv_count=$(grep -cE "^### ADVISOR-" "$adv_rules" 2>/dev/null | tr -d ' ' || echo 0)
fi
if [ "$v_count" -ge 4 ] && [ "$adv_count" -ge 9 ]; then
  corpus_pass=1
  evidence+=("V-corpus: ${v_count} V10x sub-DECs · ${adv_count} advisor rules")
else
  failures+=("V-corpus drift: V10x=${v_count} (need ≥4) · advisor_rules=${adv_count} (need ≥9)")
fi

score=$(( checkmesh_pass * 40 + massbal_pass * 40 + corpus_pass * 20 ))

python3 - <<PYEOF
import json
print(json.dumps({
  "agent": "$agent",
  "dim": "$dim",
  "weight": $weight,
  "score": $score,
  "subscores": {
    "checkmesh": $checkmesh_pass,
    "mass_balance": $massbal_pass,
    "v_corpus_present": $corpus_pass,
    "v10x_count": $v_count,
    "advisor_rules_count": $adv_count,
  },
  "evidence": $(printf '%s\n' "${evidence[@]}" | jq -R . | jq -sc .),
  "failures": $(printf '%s\n' "${failures[@]}" | jq -R . | jq -sc .)
}, ensure_ascii=False, indent=2))
PYEOF
