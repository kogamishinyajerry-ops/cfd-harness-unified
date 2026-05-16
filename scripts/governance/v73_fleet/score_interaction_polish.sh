#!/usr/bin/env bash
# V73 Fleet Agent #11 (extended from V72): Interaction Polish
# V73 changes: 4 subscores → 5 subscores · adds wcag_runtime (axe-core).
# Weights redistributed: 25 + 20 + 20 + 15 + 20 = 100.
#
# Score axes:
#   - keyboard_nav (25 · was 30 in V72) · Tab/Shift+Tab/Esc/⌘K spec PASS
#   - motion_polish (20 · was 25) · transition-* classes in v3 components
#   - focus_management (20 · was 25) · aria-* + role + tabindex coverage
#   - reduced_motion_respect (15 · was 20) · prefers-reduced-motion usage
#   - wcag_runtime (20 · NEW) · @axe-core/playwright runtime audit PASS
set -o pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

agent="interaction_polish"
dim="交互体验"
weight=0.07
evidence=("placeholder")
failures=("placeholder")

v3_dir="ui/frontend/src/pages/workbench/v3"
keyboard_spec="ui/frontend/e2e/v3-keyboard-nav.spec.ts"
a11y_spec="ui/frontend/e2e/v3-a11y-audit.spec.ts"

# 1 · keyboard_nav (25)
kbd_score=0
if [ ! -f "$keyboard_spec" ]; then
  failures+=("keyboard nav spec missing: $keyboard_spec")
else
  cd ui/frontend
  pw_bin="./node_modules/.bin/playwright"
  if [ ! -x "$pw_bin" ]; then pw_bin="npx playwright"; fi
  if $pw_bin test v3-keyboard-nav.spec.ts --reporter=json > /tmp/v73_kbd.json 2>/tmp/v73_kbd.stderr; then
    pw_exit=0
  else
    pw_exit=$?
  fi
  read passed total <<<"$(python3 - <<'PYEOF'
import json
try:
    d = json.load(open("/tmp/v73_kbd.json"))
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
    kbd_score=25
    evidence+=("keyboard nav: ${passed}/${total} PASS (FULL=25/25)")
  elif [ "${passed:-0}" -gt 0 ]; then
    kbd_score=$(( passed * 25 / 4 ))
    if [ "$kbd_score" -gt 25 ]; then kbd_score=25; fi
    evidence+=("keyboard nav: ${passed}/${total} PASS (pro-rated=${kbd_score}/25)")
  else
    failures+=("keyboard nav 0 passing tests")
  fi
  cd - > /dev/null
fi

# 2 · motion_polish (20)
motion_count=0
if [ -d "$v3_dir" ]; then
  motion_count=$(grep -r -E "transition-|duration-|ease-|animate-" "$v3_dir" 2>/dev/null | wc -l | tr -d ' ')
fi
motion_score=0
if [ "${motion_count:-0}" -ge 12 ]; then
  motion_score=20
  evidence+=("motion polish: ${motion_count} transition usages (FULL=20/20)")
elif [ "${motion_count:-0}" -gt 0 ]; then
  motion_score=$(( motion_count * 20 / 12 ))
  if [ "$motion_score" -gt 20 ]; then motion_score=20; fi
  evidence+=("motion polish: ${motion_count}/12 (pro-rated=${motion_score}/20)")
else
  failures+=("0 transition classes in v3 components")
fi

# 3 · focus_management (20)
focus_count=0
if [ -d "$v3_dir" ]; then
  focus_count=$(grep -r -E "aria-(label|labelledby|describedby|expanded|hidden|live|selected|controls|pressed)|role=|tabIndex" "$v3_dir" 2>/dev/null | wc -l | tr -d ' ')
fi
focus_score=0
if [ "${focus_count:-0}" -ge 20 ]; then
  focus_score=20
  evidence+=("focus management: ${focus_count} ARIA/role/tabIndex usages (FULL=20/20)")
elif [ "${focus_count:-0}" -gt 0 ]; then
  focus_score=$(( focus_count * 20 / 20 ))
  if [ "$focus_score" -gt 20 ]; then focus_score=20; fi
  evidence+=("focus management: ${focus_count}/20 (pro-rated=${focus_score}/20)")
else
  failures+=("0 ARIA/role/tabIndex in v3 components")
fi

# 4 · reduced_motion_respect (15)
rm_score=0
rm_count=$(grep -rE "motion-(reduce|safe)|prefers-reduced-motion" "$v3_dir" ui/frontend/src/styles 2>/dev/null | wc -l | tr -d ' ')
if [ "${rm_count:-0}" -ge 2 ]; then
  rm_score=15
  evidence+=("reduced-motion: ${rm_count} prefers-reduced-motion usages (FULL=15/15)")
elif [ "${rm_count:-0}" -gt 0 ]; then
  rm_score=8
  evidence+=("reduced-motion: ${rm_count}/2 (pro-rated=8/15)")
else
  failures+=("0 prefers-reduced-motion respect")
fi

# 5 · wcag_runtime (20 · NEW for V73) · axe-core spec PASSES with 0 violations
wcag_score=0
if [ ! -f "$a11y_spec" ]; then
  failures+=("axe-core a11y spec missing: $a11y_spec (V73.2 sub-DEC)")
else
  cd ui/frontend
  pw_bin="./node_modules/.bin/playwright"
  if [ ! -x "$pw_bin" ]; then pw_bin="npx playwright"; fi
  if $pw_bin test v3-a11y-audit.spec.ts --reporter=json > /tmp/v73_a11y.json 2>/tmp/v73_a11y.stderr; then
    a11y_exit=0
  else
    a11y_exit=$?
  fi
  read passed total <<<"$(python3 - <<'PYEOF'
import json
try:
    d = json.load(open("/tmp/v73_a11y.json"))
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
  if [ "${total:-0}" -ge 3 ] && [ "${passed:-0}" -eq "${total:-0}" ]; then
    wcag_score=20
    evidence+=("axe-core runtime a11y: ${passed}/${total} PASS · 0 WCAG violations (FULL=20/20)")
  elif [ "${passed:-0}" -gt 0 ]; then
    wcag_score=$(( passed * 20 / 3 ))
    if [ "$wcag_score" -gt 20 ]; then wcag_score=20; fi
    evidence+=("axe-core: ${passed}/${total} PASS (pro-rated=${wcag_score}/20)")
  else
    failures+=("axe-core runtime: 0 passing surfaces")
  fi
  cd - > /dev/null
fi

evidence=("${evidence[@]:1}")
failures=("${failures[@]:1}")
score=$(( kbd_score + motion_score + focus_score + rm_score + wcag_score ))
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
    "wcag_runtime": $wcag_score,
    "transition_count": ${motion_count:-0},
    "aria_role_count": ${focus_count:-0},
  },
  "evidence": ev,
  "failures": fa,
  "honest_note": "V73 extension of V72 pillar 11 · 4 subscores → 5 · adds wcag_runtime via axe-core"
}, ensure_ascii=False, indent=2))
PYEOF
