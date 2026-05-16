#!/usr/bin/env bash
# V67-C Fleet Agent #2: Physics Validator
# Backend physics regression tests (mass_balance) + V-corpus shape check.
# checkmesh test was relocated (not under tests/) — V67-C scope is UI work,
# so physics regression is "did we break backend BC/mesh contracts?" only.
# Score = mass_balance(50) + v_corpus_shape(30) + bc_routes_intact(20)
set -o pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

agent="physics_validator"
dim="物理/数值稳定"
weight=0.15
evidence=("placeholder")
failures=("placeholder")

massbal_pass=0
corpus_pass=0
bc_routes_pass=0

# Mass balance regression
mb_test="ui/backend/tests/test_bc_writer_mass_balance.py"
if [ -f "$mb_test" ]; then
  if uv run python -m pytest "$mb_test" -q --no-header > /tmp/v67c_massbal.log 2>&1; then
    massbal_pass=1
    passed=$(grep -oE "[0-9]+ passed" /tmp/v67c_massbal.log | head -1 | grep -oE "[0-9]+" || echo 0)
    evidence+=("mass_balance: PASS (${passed} tests)")
  else
    fail=$(grep -oE "[0-9]+ failed" /tmp/v67c_massbal.log | head -1 | grep -oE "[0-9]+" || echo "?")
    failures+=("mass_balance: ${fail} failed · see /tmp/v67c_massbal.log")
  fi
else
  failures+=("mass_balance test missing: $mb_test")
fi

# V-corpus shape: count V10x sub-DECs + count advisor rule files + V66-B rules
v10x_count=$(ls .planning/decisions/2026-05-1[56]_v6[56]_sub_*v10[0-9]*.md 2>/dev/null | wc -l | tr -d ' ')
adv_files=$(ls .planning/methodology/advisor_*.md 2>/dev/null | wc -l | tr -d ' ')
adv_rules_in_v66b=$(grep -cE "^## RULE " .planning/methodology/advisor_rules_v66b_expansion.md 2>/dev/null | tr -d ' ' || echo 0)
if [ "$v10x_count" -ge 4 ] && [ "$adv_files" -ge 2 ] && [ "$adv_rules_in_v66b" -ge 3 ]; then
  corpus_pass=1
  evidence+=("V-corpus: ${v10x_count} V10x sub-DECs · ${adv_files} advisor_rule files · ${adv_rules_in_v66b} rules in V66-B expansion")
else
  failures+=("V-corpus drift: V10x=${v10x_count} (need ≥4) · adv_files=${adv_files} (need ≥2) · v66b_rules=${adv_rules_in_v66b} (need ≥3)")
fi

# BC routes intact: case_bc.py exists + tests pass
bc_route="ui/backend/routes/case_bc.py"
if [ -f "$bc_route" ]; then
  if uv run python -c "from ui.backend.routes import case_bc; print('ok')" > /tmp/v67c_bc_routes.log 2>&1; then
    bc_routes_pass=1
    evidence+=("case_bc route import: PASS")
  else
    failures+=("case_bc route import failed · see /tmp/v67c_bc_routes.log")
  fi
else
  failures+=("case_bc route missing: $bc_route")
fi

evidence=("${evidence[@]:1}")
failures=("${failures[@]:1}")

score=$(( massbal_pass * 50 + corpus_pass * 30 + bc_routes_pass * 20 ))

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
    "mass_balance": $massbal_pass,
    "v_corpus_shape": $corpus_pass,
    "bc_routes_intact": $bc_routes_pass,
    "v10x_count": $v10x_count,
    "advisor_files_count": $adv_files,
    "v66b_rules_count": $adv_rules_in_v66b,
  },
  "evidence": ev,
  "failures": fa,
  "honest_note": "V67-C is UI work; physics regression scope = mass_balance + corpus shape + BC route import. checkmesh runner test was relocated outside tests/ and not run by this agent."
}, ensure_ascii=False, indent=2))
PYEOF
