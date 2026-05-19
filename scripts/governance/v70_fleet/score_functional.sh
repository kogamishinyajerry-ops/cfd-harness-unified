#!/usr/bin/env bash
# V70 Fleet Agent #6: Functional Checklist
# V70 target: 6/6 sub-DECs LANDED + 9/9 Done dims MET (expanded from V69 4/7)
# Score = (LANDED/6 * 70) + (Done/9 * 30)
set -o pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

agent="functional"
dim="功能完整度"
weight=0.08
evidence=("placeholder")
failures=("placeholder")

sub_dec_dir=".planning/decisions"
landed=0
for f in $(ls "$sub_dec_dir"/2026-05-*_v70_sub_*.md 2>/dev/null); do
  if grep -qE "^status: Accepted$" "$f"; then
    landed=$((landed + 1))
    evidence+=("LANDED: $(basename "$f")")
  fi
done

done_met=0
arc_goal=".planning/V70_ARC_GOAL.md"
if [ -f "$arc_goal" ]; then
  done_met=$(grep -cE "^- \[x\] \*\*V70-DONE-[1-9]" "$arc_goal" 2>/dev/null | head -1 | tr -d ' \n')
  done_met=${done_met:-0}
  evidence+=("Done dims MET: ${done_met}/9 (from $arc_goal)")
else
  failures+=("V70_ARC_GOAL.md not yet authored · Done dims = 0/9 honest baseline")
fi

score=$(( landed * 70 / 6 + done_met * 30 / 9 ))
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
    "landed_sub_dec_count": $landed,
    "landed_sub_dec_total": 6,
    "done_dim_met": $done_met,
    "done_dim_total": 9,
  },
  "evidence": ev,
  "failures": fa
}, ensure_ascii=False, indent=2))
PYEOF
