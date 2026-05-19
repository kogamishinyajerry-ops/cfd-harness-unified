#!/usr/bin/env bash
# V68-C Fleet Agent #6: Functional Checklist
# V68-C target: 4/4 sub-DECs LANDED + 7/7 Done dims MET
# (charter §5 originally listed 5 sub-DECs; V68-C.3 CompletenessCard real-data
#  wiring was consolidated into V68-C.2 because both consume the same
#  useCaseStatus hook as SSOT. Close DEC §11 documents the consolidation.
#  The Done dim count (7/7 FULL-MET) remains the SSOT for scope completion;
#  sub-DEC count tracks process artifacts only.)
# Score = (LANDED/4 * 70) + (Done/7 * 30)
set -o pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

agent="functional"
dim="功能完整度"
weight=0.10
evidence=("placeholder")
failures=("placeholder")

sub_dec_dir=".planning/decisions"
landed=0
for f in $(ls "$sub_dec_dir"/2026-05-*_v68c_sub_*.md 2>/dev/null); do
  if grep -qE "^status: Accepted$" "$f"; then
    landed=$((landed + 1))
    evidence+=("LANDED: $(basename "$f")")
  fi
done

done_met=0
arc_goal=".planning/V68C_ARC_GOAL.md"
if [ -f "$arc_goal" ]; then
  done_met=$(grep -cE "^- \[x\] \*\*V68-C-DONE-[1-7]" "$arc_goal" 2>/dev/null | head -1 | tr -d ' \n')
  done_met=${done_met:-0}
  evidence+=("Done dims MET: ${done_met}/7 (from $arc_goal)")
else
  failures+=("V68C_ARC_GOAL.md not yet authored · Done dims = 0/7 honest baseline")
fi

score=$(( landed * 70 / 4 + done_met * 30 / 7 ))
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
    "landed_sub_dec_total": 4,
    "done_dim_met": $done_met,
    "done_dim_total": 7,
  },
  "evidence": ev,
  "failures": fa
}, ensure_ascii=False, indent=2))
PYEOF
