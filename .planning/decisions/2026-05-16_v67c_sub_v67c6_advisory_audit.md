---
decision_id: DEC-V67-C-sub-V67C6-advisory-audit
title: V67-C.6 · AI advisory-only audit (Done dim #6 MET) · B121
status: Accepted
parent_dec: DEC-V67-C-charter
phase: V67-C
notion_sync_status: pending
predecessor: DEC-V67-C-sub-V67C2-statusstrip
batch: B121
confidence: high
autonomous_governance: true
verdict: SUB_DEC_LANDED
v_row_landed: none
substrate: scripts/governance/v67c_fleet/audit_ai_advisory.sh + .planning/scores/V67-C_advisory_audit_b121.md
---

# DEC-V67-C-sub-V67C6-advisory-audit · V67-C.6 · B121

## 1 · Decision

Land V67-C-DONE-6 (AI panel strict advisory-only) via an executable audit script that verifies 4 invariants:

1. **AIAdvisorPanel.tsx** contains 0 mutation patterns (`POST/PUT/DELETE` HTTP methods, `useMutation`, `onMutate`, `onApply`, `"Apply"` button text)
2. **AICoachPanel.tsx** contains 0 mutation patterns (same pattern set)
3. **MUTATING_ROUTES** registry count = **9** (baseline locked at V67-C charter B117 · per V132 contract)
4. **KNOWN_MUTATION_FUNCTIONS** registry count = **12** (baseline locked at V67-C charter B117)

## 2 · Audit run (initial baseline)

```
===== V67-C.6 AI advisory-only audit =====
ran: 2026-05-16T06:51:21Z
commit: 15eda3d

✓ ui/frontend/src/pages/workbench/step_panel_shell/AIAdvisorPanel.tsx · 0 mutation patterns
✓ ui/frontend/src/pages/workbench/step_panel_shell/AICoachPanel.tsx · 0 mutation patterns
✓ MUTATING_ROUTES = 9 (matches baseline 9)
✓ KNOWN_MUTATION_FUNCTIONS = 12 (matches baseline 12)

VERDICT: PASS · 0 violations · V67-C-DONE-6 invariant intact
```

**Result**: 4/4 invariants PASS. Done dim #6 MET.

## 3 · Implementation

### `scripts/governance/v67c_fleet/audit_ai_advisory.sh` (NEW · 75 LOC)

Bash audit script:
- `BASELINE_MUTATING_ROUTES=9` · locked at V67-C charter B117
- `BASELINE_MUTATION_FUNCTIONS=12` · locked at V67-C charter B117
- Greps both AI panels for mutation patterns
- Compares registry counts vs baselines
- Exits 0 on PASS, 1 on FAIL (CI-ready)
- Distinct from fleet score agents (this is a governance gate, not a fleet dimension)

### Output

Audit report: `.planning/scores/V67-C_advisory_audit_b121.md` (verbatim audit stdout).

## 4 · Done dim impact

- **V67-C-DONE-6**: ❌ → **✅ MET** (audit script PASS · 4/4 invariants intact)

## 5 · Score implication

V67-C-DONE-6 MET advances **functional** agent score from `1/8` to `2/8` Done dims:
- Pre: 1/6 LANDED + 1/8 Done = (11.7 + 3.75) = 15 → rounded 15
- Post (V67-C.0/.1/.2/.6 LANDED + Done dims 1/2/6 MET): 4/6 LANDED + 3/8 Done = (46.7 + 11.25) = 57.95 → rounded 57

## 6 · 4Q gate

| Q | A |
|---|---|
| LLM offline | ✓ Audit is pure grep + bash; no LLM dependency |
| Artifacts | ✓ audit_ai_advisory.sh + audit report + this sub-DEC |
| TrustGate | ✓ VERDICT line surfaces 4 invariant states |
| AI advisory-only | ✓ **This sub-DEC EXISTS specifically to enforce this** |

## 7 · v2.3 compliance

- DEC scope: sub-DEC (single audit script + report)
- Codex 1-sync-trigger: NOT triggered (audit script · no security boundary)
- Kogami opt-in: NOT invoked
- Confidence: high (audit verbatim output + 4/4 invariants PASS)
- Counter: B121 autonomous_governance=true · +1

## 8 · Future runs

This audit script must be re-run by any future sub-DEC that:
- Adds a new AI panel (e.g., new advisor surface)
- Modifies AIAdvisorPanel.tsx or AICoachPanel.tsx
- Touches `ui/backend/services/ai_actions/mutating_routes.py`
- Adds a new mutating backend route (must be reflected in baseline update)

If baseline shifts intentionally (e.g., new MUTATING_ROUTE adds a legitimate
mutation), update `BASELINE_MUTATING_ROUTES` constant in the script via a
new sub-DEC citing the upstream charter or DEC justification.

— Claude Code (Opus 4.7 1M) · B121 · V67-C.6 · 2026-05-16
