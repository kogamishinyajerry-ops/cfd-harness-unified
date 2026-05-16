#!/usr/bin/env bash
# V72 Fleet Agent #11 (NEW): Interaction Polish
# V72 target: keyboard navigation + motion design + focus management + a11y
# Score axes:
#   - keyboard_nav (30) · Tab/Shift+Tab/Esc/⌘K spec PASS
#   - motion_polish (25) · transition-* classes count in v3 components
#   - focus_management (25) · aria-* + role + tabindex coverage
#   - reduced_motion_respect (20) · prefers-reduced-motion query usage
set -o pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

agent="interaction_polish"
dim="交互体验"
weight=0.07
evidence=("placeholder")
failures=("placeholder")

v3_dir="ui/frontend/src/pages/workbench/v3"
keyboard_spec="ui/frontend/e2e/v3-keyboard-nav.spec.ts"

# 1 · keyboard_nav (30) · spec presence + tests pass
kbd_score=0
if [ ! -f "$keyboard_spec" ]; then
  failures+=("keyboard nav spec missing: $keyboard_spec")
else
  cd ui/frontend
  if npx playwright test v3-keyboard-nav.spec.ts --reporter=json > /tmp/v72_kbd.json 2>/tmp/v72_kbd.stderr; then
    pw_exit=0
  else
    pw_exit=$?
  fi
  read passed total <<<"$(python3 - <<'PYEOF'
import json
try:
    d = json.load(open("/tmp/v72_kbd.json"))
    def walk(s):
        for x in s:
            for sp in x.get("specs", []):
                for t in sp.get("tests", []):
                    yield t
            yield from walk(x.get("suites", []))
    items = list(walk(d.get("suites", [])))
    total = len(items)
    passed = sum(1 for t in items if all(r.get("status") == "passed" for r in t.get("results", [])))
    print(f"{passed} {total}")
except Exception as exc:
    print(f"0 0 # parse error: {exc}")
PYEOF
)"
  if [ "${total:-0}" -ge 4 ] && [ "${passed:-0}" -eq "${total:-0}" ]; then
    kbd_score=30
    evidence+=("keyboard nav: ${passed}/${total} PASS (FULL=30/30)")
  elif [ "${passed:-0}" -gt 0 ]; then
    kbd_score=$(( passed * 30 / 4 ))
    if [ "$kbd_score" -gt 30 ]; then kbd_score=30; fi
    evidence+=("keyboard nav: ${passed}/${total} PASS (pro-rated=${kbd_score}/30)")
  else
    failures+=("keyboard nav 0 passing tests")
  fi
  cd - > /dev/null
fi

# 2 · motion_polish (25) · transition class usage in v3 components
motion_count=0
if [ -d "$v3_dir" ]; then
  motion_count=$(grep -r -E "transition-|duration-|ease-|animate-" "$v3_dir" 2>/dev/null | wc -l | tr -d ' ')
fi
motion_score=0
if [ "${motion_count:-0}" -ge 12 ]; then
  motion_score=25
  evidence+=("motion polish: ${motion_count} transition usages (FULL=25/25)")
elif [ "${motion_count:-0}" -gt 0 ]; then
  motion_score=$(( motion_count * 25 / 12 ))
  if [ "$motion_score" -gt 25 ]; then motion_score=25; fi
  evidence+=("motion polish: ${motion_count}/12 transitions (pro-rated=${motion_score}/25)")
else
  failures+=("0 transition classes in v3 components")
fi

# 3 · focus_management (25) · aria-* / role / tabindex coverage in v3
focus_count=0
if [ -d "$v3_dir" ]; then
  focus_count=$(grep -r -E "aria-(label|labelledby|describedby|expanded|hidden|live)|role=|tabIndex" "$v3_dir" 2>/dev/null | wc -l | tr -d ' ')
fi
focus_score=0
if [ "${focus_count:-0}" -ge 20 ]; then
  focus_score=25
  evidence+=("focus management: ${focus_count} ARIA/role/tabIndex usages (FULL=25/25)")
elif [ "${focus_count:-0}" -gt 0 ]; then
  focus_score=$(( focus_count * 25 / 20 ))
  if [ "$focus_score" -gt 25 ]; then focus_score=25; fi
  evidence+=("focus management: ${focus_count}/20 (pro-rated=${focus_score}/25)")
else
  failures+=("0 ARIA/role/tabIndex in v3 components")
fi

# 4 · reduced_motion_respect (20) · prefers-reduced-motion media query usage
rm_score=0
rm_count=$(grep -rE "motion-(reduce|safe)|prefers-reduced-motion" "$v3_dir" ui/frontend/src/styles 2>/dev/null | wc -l | tr -d ' ')
if [ "${rm_count:-0}" -ge 2 ]; then
  rm_score=20
  evidence+=("reduced-motion: ${rm_count} prefers-reduced-motion usages (FULL=20/20)")
elif [ "${rm_count:-0}" -gt 0 ]; then
  rm_score=10
  evidence+=("reduced-motion: ${rm_count}/2 usage (pro-rated=10/20)")
else
  failures+=("0 prefers-reduced-motion respect")
fi

evidence=("${evidence[@]:1}")
failures=("${failures[@]:1}")
score=$(( kbd_score + motion_score + focus_score + rm_score ))
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
    "keyboard_nav": $kbd_score,
    "motion_polish": $motion_score,
    "focus_management": $focus_score,
    "reduced_motion_respect": $rm_score,
    "transition_count": ${motion_count:-0},
    "aria_role_count": ${focus_count:-0},
  },
  "evidence": ev,
  "failures": fa,
  "honest_note": "V72 NEW pillar · 11th dimension · per user mandate '交互模式'"
}, ensure_ascii=False, indent=2))
PYEOF
