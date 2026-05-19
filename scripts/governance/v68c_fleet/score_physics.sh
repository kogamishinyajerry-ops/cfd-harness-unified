#!/usr/bin/env bash
# V68-C Fleet Agent #2: Physics Validator (tightened vs V68-B)
# V68-C criteria:
#   - mass_balance(40) · backend mass balance regression tests pass
#   - v_corpus_shape(20) · V10x DECs + advisor rule files exist
#   - bc_routes_intact(15) · case_bc.py imports clean
#   - whitelist_count(25) · /api/cases LIST returns ≥11 (10 baseline + case_002a from V68-C.3)
# Score = mass_balance + corpus + bc_routes + whitelist_count
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

# V68-C whitelist count assertion · target ≥11 after case_002a entry lands
whitelist_pass=0
whitelist_count=0
whitelist_count=$(PYTHONPATH=. uv run python -c "
from ui.backend.services.validation_report import list_cases
print(len(list_cases()))
" 2>/dev/null | tail -1 | tr -d ' \n' || echo 0)
whitelist_count=${whitelist_count:-0}
if [ "$whitelist_count" -ge 11 ]; then
  whitelist_pass=1
  evidence+=("whitelist count: ${whitelist_count} (≥11 V68-C threshold MET)")
else
  failures+=("whitelist count: ${whitelist_count} (need ≥11 for V68-C close · case_002a entry pending)")
fi

evidence=("${evidence[@]:1}")
failures=("${failures[@]:1}")

score=$(( massbal_pass * 40 + corpus_pass * 20 + bc_routes_pass * 15 + whitelist_pass * 25 ))

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
    "whitelist_count": $whitelist_count,
    "whitelist_pass": $whitelist_pass,
  },
  "evidence": ev,
  "failures": fa,
  "honest_note": "V67-C is UI work; physics regression scope = mass_balance + corpus shape + BC route import. checkmesh runner test was relocated outside tests/ and not run by this agent."
}, ensure_ascii=False, indent=2))
PYEOF
