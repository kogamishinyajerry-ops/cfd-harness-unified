#!/usr/bin/env bash
# V70 Fleet Agent #9: Novice-Onboarding
# Audits first-time-engineer onboarding affordances.
# Subscores:
#   - tutorial_route_exists (25)        · src/pages contains TutorialPage / tutorial subroute
#   - tooltip_count_on_rail (25)        · ≥6 title= or data-tooltip= attrs on Engineer Control Rail
#   - first_time_banner_present (20)    · component or route renders first-time banner pointing to lid_driven_cavity
#   - novice_e2e_spec_count (15)        · ≥1 e2e spec named "novice" or "onboarding"
#   - onboarding_doc_word_count (15)    · .planning/onboarding_guide.md ≥1000 words
# Score = sum (max 100)

set -o pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

agent="novice_onboarding"
dim="新手用户使用难度"
weight=0.07
evidence=("placeholder")
failures=("placeholder")

# ─────────── 1. Tutorial route ────────────────────────────────────
tutorial_score=0
tutorial_present=0
if [ -d "ui/frontend/src" ]; then
  # Tutorial route present if either:
  # (a) TutorialPage.tsx exists anywhere under ui/frontend/src/pages/
  # (b) App.tsx wires /workbench/tutorial route
  if find ui/frontend/src/pages -name "TutorialPage*.tsx" 2>/dev/null | head -1 | grep -q . \
     || grep -lE "/workbench/tutorial|TutorialPage" ui/frontend/src/App.tsx 2>/dev/null | head -1 > /dev/null; then
    tutorial_present=1
    tutorial_score=25
    evidence+=("tutorial route: PRESENT (TutorialPage + /workbench/tutorial wired in App.tsx)")
  else
    failures+=("tutorial route: MISSING (need TutorialPage at /workbench/tutorial for V70-DONE-3)")
  fi
fi

# ─────────── 2. Tooltips on Engineer Control Rail ─────────────────
tooltip_count=0
if [ -d "ui/frontend/src/components" ]; then
  # Look for EngineerControlRail / Rail / control_rail component files
  rail_files=$(grep -rlE "EngineerControlRail|engineer.?rail|control.?rail" ui/frontend/src/components/ 2>/dev/null | head -5)
  if [ -n "$rail_files" ]; then
    tooltip_count=$(echo "$rail_files" | xargs grep -hE "title=|data-tooltip|aria-label=|<Tooltip" 2>/dev/null | wc -l | tr -d ' ')
  fi
fi
tooltip_count=${tooltip_count:-0}
if [ "$tooltip_count" -ge 6 ]; then
  tooltip_score=25
  evidence+=("tooltips on Engineer Control Rail: ${tooltip_count} (≥6 V70 threshold MET)")
elif [ "$tooltip_count" -gt 0 ]; then
  tooltip_score=$(( tooltip_count * 25 / 6 ))
  evidence+=("tooltips: ${tooltip_count}/6 (pro-rated=${tooltip_score}/25)")
  failures+=("tooltips below threshold: ${tooltip_count}/6 (need ≥6 for V70-DONE-3)")
else
  tooltip_score=0
  failures+=("tooltips: 0 detected on Engineer Control Rail")
fi

# ─────────── 3. First-time banner ─────────────────────────────────
banner_score=0
if [ -d "ui/frontend/src" ]; then
  if grep -rlE "FirstTimeBanner|first.?time.?banner|welcome.?banner|novice.?banner" ui/frontend/src/ 2>/dev/null | head -1 > /dev/null \
     || grep -rE "lid_driven_cavity.*starter|starter.*lid_driven_cavity" ui/frontend/src/ 2>/dev/null | head -1 > /dev/null; then
    banner_score=20
    evidence+=("first-time banner: PRESENT (points new users to lid_driven_cavity starter)")
  else
    failures+=("first-time banner: MISSING (need banner pointing to lid_driven_cavity for V70-DONE-3)")
  fi
fi

# ─────────── 4. Novice e2e spec ───────────────────────────────────
novice_spec_count=0
if [ -d "ui/frontend/e2e" ]; then
  novice_spec_count=$(ls ui/frontend/e2e/*novice*.spec.ts ui/frontend/e2e/*onboarding*.spec.ts ui/frontend/e2e/*tutorial*.spec.ts 2>/dev/null | wc -l | tr -d ' ')
fi
novice_spec_count=${novice_spec_count:-0}
if [ "$novice_spec_count" -ge 1 ]; then
  novice_score=15
  evidence+=("novice e2e specs: ${novice_spec_count} (≥1 V70 threshold MET)")
else
  novice_score=0
  failures+=("novice e2e specs: 0 (need ≥1 spec named *novice* or *onboarding* or *tutorial*)")
fi

# ─────────── 5. Onboarding doc ────────────────────────────────────
doc_score=0
doc=".planning/onboarding_guide.md"
if [ -f "$doc" ]; then
  wc_count=$(wc -w < "$doc" 2>/dev/null | tr -d ' ')
  wc_count=${wc_count:-0}
  if [ "$wc_count" -ge 1000 ]; then
    doc_score=15
    evidence+=("onboarding doc: ${wc_count} words (≥1000 V70 threshold MET)")
  elif [ "$wc_count" -gt 0 ]; then
    doc_score=$(( wc_count * 15 / 1000 ))
    evidence+=("onboarding doc: ${wc_count}/1000 words (pro-rated=${doc_score}/15)")
    failures+=("onboarding doc below word threshold: ${wc_count}/1000 (need ≥1000 for V70-DONE-3)")
  fi
else
  failures+=("onboarding doc missing: ${doc} (need ≥1000 words for V70-DONE-3)")
fi

score=$(( tutorial_score + tooltip_score + banner_score + novice_score + doc_score ))
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
    "tutorial_route_score": $tutorial_score,
    "tooltip_count": $tooltip_count,
    "tooltip_score": $tooltip_score,
    "first_time_banner_score": $banner_score,
    "novice_spec_count": $novice_spec_count,
    "novice_spec_score": $novice_score,
    "onboarding_doc_score": $doc_score,
  },
  "evidence": ev,
  "failures": fa,
  "honest_note": "tooltip detection is grep-based on title/aria-label/data-tooltip/<Tooltip patterns; doesn't catch tooltip libraries that compose via children prop · refine if false-negative pattern emerges"
}, ensure_ascii=False, indent=2))
PYEOF
