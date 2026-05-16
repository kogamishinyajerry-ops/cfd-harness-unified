#!/usr/bin/env bash
# V67-C Fleet Agent #6: Functional Checklist
# Counts LANDED V67-C sub-DECs + Done dim MET.
# Score = (LANDED_sub_DEC_count / 6) * 70 + (Done_dim_MET / 8) * 30
set -o pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

agent="functional"
dim="功能完整度"
weight=0.10
evidence=()
failures=()

# Count LANDED V67-C sub-DECs (Status=Accepted in frontmatter, in .planning/decisions/)
sub_dec_dir=".planning/decisions"
landed=0
for f in $(ls "$sub_dec_dir"/2026-05-*_v67c_sub_*.md 2>/dev/null); do
  if grep -qE "^status: Accepted$" "$f"; then
    landed=$((landed + 1))
    evidence+=("LANDED: $(basename "$f")")
  fi
done

# Done dim MET — read from this arc's tracking file (lives in ARC-GOAL.md once V67-C ARC-GOAL written; baseline counts as 0)
done_met=0
arc_goal=".planning/V67C_ARC_GOAL.md"
if [ -f "$arc_goal" ]; then
  done_met=$(grep -cE "^\- \[x\] \*\*V67-C-DONE-[1-8]" "$arc_goal" 2>/dev/null | tr -d ' ' || echo 0)
  evidence+=("Done dims MET: ${done_met}/8 (from $arc_goal)")
else
  failures+=("V67C_ARC_GOAL.md not yet authored · Done dims = 0/8 honest baseline")
fi

score=$(( landed * 70 / 6 + done_met * 30 / 8 ))

python3 - <<PYEOF
import json
print(json.dumps({
  "agent": "$agent",
  "dim": "$dim",
  "weight": $weight,
  "score": $score,
  "subscores": {
    "landed_sub_dec_count": $landed,
    "landed_sub_dec_total": 6,
    "done_dim_met": $done_met,
    "done_dim_total": 8,
  },
  "evidence": $(printf '%s\n' "${evidence[@]}" | jq -R . | jq -sc .),
  "failures": $(printf '%s\n' "${failures[@]}" | jq -R . | jq -sc .)
}, ensure_ascii=False, indent=2))
PYEOF
