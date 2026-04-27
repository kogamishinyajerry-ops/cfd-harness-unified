#!/usr/bin/env bash
# W2 acceptance: P-2.5 strategic package validator on 8 manual samples
# Per DEC-V61-087 Acceptance Criteria.
# 4 valid (1 with P2-T2 milestone whitelist exemption) → exit 0
# 4 invalid (1 missing field, 1 enum out of range, 1 string too long, 1 rationale with \bP0\b) → exit 1

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VALIDATOR="$SCRIPT_DIR/validate_strategic_package.py"
TMP=$(mktemp -d /tmp/p25_test_XXXXXX)
trap "rm -rf $TMP" EXIT

PASS=0
FAIL=0

run_case() {
    local name="$1"
    local expected="$2"   # "pass" or "reject"
    local intent="$3"
    local risk="$4"

    local intent_file="$TMP/${name}_intent.md"
    local risk_file="$TMP/${name}_risk.md"
    echo "$intent" > "$intent_file"
    echo "$risk" > "$risk_file"

    if python3 "$VALIDATOR" --intent "$intent_file" --risk "$risk_file" > /tmp/p25_out 2>&1; then
        actual="pass"
    else
        actual="reject"
    fi

    if [[ "$actual" == "$expected" ]]; then
        echo "  ✓ [$name] expected=$expected actual=$actual"
        PASS=$((PASS+1))
    else
        echo "  ✗ [$name] expected=$expected actual=$actual"
        cat /tmp/p25_out | sed 's/^/      /'
        FAIL=$((FAIL+1))
    fi
}

echo "=== P-2.5 strategic package validator · 8 manual samples ==="
echo ""
echo "--- 4 valid samples ---"

# Valid #1: minimal valid package
run_case "v1_minimal" "pass" \
"roadmap_milestone: M2
business_goal: Add edit-page UX to workbench
affected_subsystems:
  - frontend EditPage
  - backend case editor" \
"risk_class: low
reversibility: easy
blast_radius: bounded"

# Valid #2: with rationale (no blacklist hits)
run_case "v2_with_rationale" "pass" \
"roadmap_milestone: M3
business_goal: Persist run history per case
affected_subsystems:
  - run_history service
  - reports tree
  - frontend
rationale: |
  Users need durable history to compare runs over time. Implementation reuses existing reports tree." \
"risk_class: medium
reversibility: medium
blast_radius: bounded
rationale: |
  Adds new write domain reports/{case}/runs/. Rollback by deleting created dirs."

# Valid #3: P2-T2 milestone (whitelist exemption — should NOT trigger \\bP[0-3]\\b)
run_case "v3_p2_t2_milestone" "pass" \
"roadmap_milestone: P2-T2
business_goal: Substantialize docker_openfoam executor mode
affected_subsystems:
  - foam_agent_adapter
  - docker_openfoam executor" \
"risk_class: medium
reversibility: medium
blast_radius: bounded"

# Valid #4: nested milestone with .suffix
run_case "v4_nested_milestone" "pass" \
"roadmap_milestone: P2-T1.b
business_goal: Land ExecutorMode skeleton
affected_subsystems:
  - executor base class
  - mode dispatch" \
"risk_class: low
reversibility: easy
blast_radius: bounded"

echo ""
echo "--- 4 invalid samples ---"

# Invalid #1: missing required field (no business_goal)
run_case "i1_missing_field" "reject" \
"roadmap_milestone: M1
affected_subsystems:
  - thing one" \
"risk_class: low
reversibility: easy
blast_radius: bounded"

# Invalid #2: enum out of range (risk_class: critical)
run_case "i2_enum_oor" "reject" \
"roadmap_milestone: M1
business_goal: Some goal
affected_subsystems:
  - thing one" \
"risk_class: critical
reversibility: easy
blast_radius: bounded"

# Invalid #3: business_goal too long (>50 words)
LONG_GOAL=$(python3 -c "print('word ' * 60)")
run_case "i3_too_long" "reject" \
"roadmap_milestone: M1
business_goal: $LONG_GOAL
affected_subsystems:
  - thing one" \
"risk_class: low
reversibility: easy
blast_radius: bounded"

# Invalid #4: rationale contains \\bP0\\b
run_case "i4_blacklist_p0" "reject" \
"roadmap_milestone: M1
business_goal: Fix something
affected_subsystems:
  - thing one
rationale: This addresses the P0 issue raised earlier." \
"risk_class: low
reversibility: easy
blast_radius: bounded"

echo ""
echo "=== summary ==="
echo "  pass: $PASS / 8"
echo "  fail: $FAIL / 8"

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
exit 0
