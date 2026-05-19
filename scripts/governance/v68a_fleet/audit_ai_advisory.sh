#!/usr/bin/env bash
# V67-C.6 advisory-only audit · cross-checks:
#   1. AI panels (frontend) contain 0 mutation patterns (POST/PUT/DELETE/Apply/onMutate/useMutation)
#   2. MUTATING_ROUTES registry count matches charter baseline (=9 at V67-C.0 commit)
#   3. KNOWN_MUTATION_FUNCTIONS count matches charter baseline (=12)
#   4. No "Apply" button in AI panel JSX
#
# This is a *governance* audit, distinct from the fleet score agents. Run
# manually for any V67-C sub-DEC that touches AI panels OR mutating routes.
set -o pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

# Baselines locked at V67-C charter (B117 · 2026-05-16)
BASELINE_MUTATING_ROUTES=9
BASELINE_MUTATION_FUNCTIONS=12

ai_panels=(
  "ui/frontend/src/pages/workbench/step_panel_shell/AIAdvisorPanel.tsx"
  "ui/frontend/src/pages/workbench/step_panel_shell/AICoachPanel.tsx"
)

errors=0
results=()

# 1. AI panels mutation-pattern grep
for p in "${ai_panels[@]}"; do
  if [ ! -f "$p" ]; then
    results+=("✗ MISSING: $p")
    errors=$((errors + 1))
    continue
  fi
  hits=$(grep -cE 'method:\s*"(POST|PUT|DELETE)"|useMutation|onMutate|onApply|"Apply"' "$p" 2>/dev/null || echo 0)
  # Strip non-digit garbage
  hits=$(echo "$hits" | head -1 | tr -d ' \n')
  hits=${hits:-0}
  if [ "$hits" -eq 0 ]; then
    results+=("✓ $p · 0 mutation patterns")
  else
    results+=("✗ $p · ${hits} mutation pattern(s) detected")
    errors=$((errors + 1))
  fi
done

# 2. MUTATING_ROUTES count
mutating_routes_file="ui/backend/services/ai_actions/mutating_routes.py"
if [ -f "$mutating_routes_file" ]; then
  current_routes=$(grep -cE '^\s*\("(POST|PUT|DELETE)' "$mutating_routes_file" | head -1 | tr -d ' \n')
  current_routes=${current_routes:-0}
  if [ "$current_routes" -eq "$BASELINE_MUTATING_ROUTES" ]; then
    results+=("✓ MUTATING_ROUTES = ${current_routes} (matches baseline ${BASELINE_MUTATING_ROUTES})")
  else
    delta=$((current_routes - BASELINE_MUTATING_ROUTES))
    results+=("⚠ MUTATING_ROUTES = ${current_routes} (baseline ${BASELINE_MUTATING_ROUTES} · delta ${delta})")
    if [ "$delta" -gt 0 ]; then
      errors=$((errors + 1))
      results+=("  → NET INCREASE = automatic P1 per V67-C charter §11 reverse-stop")
    fi
  fi
else
  results+=("✗ MISSING: $mutating_routes_file")
  errors=$((errors + 1))
fi

# 3. KNOWN_MUTATION_FUNCTIONS count
if [ -f "$mutating_routes_file" ]; then
  current_fns=$(grep -cE '^\s*\("ui\.backend\.' "$mutating_routes_file" | head -1 | tr -d ' \n')
  current_fns=${current_fns:-0}
  if [ "$current_fns" -eq "$BASELINE_MUTATION_FUNCTIONS" ]; then
    results+=("✓ KNOWN_MUTATION_FUNCTIONS = ${current_fns} (matches baseline ${BASELINE_MUTATION_FUNCTIONS})")
  else
    delta=$((current_fns - BASELINE_MUTATION_FUNCTIONS))
    results+=("⚠ KNOWN_MUTATION_FUNCTIONS = ${current_fns} (baseline ${BASELINE_MUTATION_FUNCTIONS} · delta ${delta})")
    if [ "$delta" -gt 0 ]; then
      errors=$((errors + 1))
    fi
  fi
fi

# Output
echo "===== V67-C.6 AI advisory-only audit ====="
echo "ran: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "commit: $(git rev-parse --short HEAD)"
echo ""
for r in "${results[@]}"; do echo "$r"; done
echo ""
if [ "$errors" -eq 0 ]; then
  echo "VERDICT: PASS · 0 violations · V67-C-DONE-6 invariant intact"
  exit 0
else
  echo "VERDICT: FAIL · ${errors} violations · V67-C-DONE-6 invariant BROKEN"
  exit 1
fi
