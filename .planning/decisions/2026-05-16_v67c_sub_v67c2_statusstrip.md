---
decision_id: DEC-V67-C-sub-V67C2-statusstrip
title: V67-C.2 · StatusStrip 4-field live indicators (Done dim #2 MET) · B120
status: Accepted
parent_dec: DEC-V67-C-charter
phase: V67-C
notion_sync_status: pending
predecessor: DEC-V67-C-sub-V67C1-topbar-6field
batch: B120
confidence: high
autonomous_governance: true
verdict: SUB_DEC_LANDED
v_row_landed: none
substrate: ui/frontend/src/pages/workbench/step_panel_shell/StatusStrip.tsx (30→130 LOC) + StatusStrip.test.tsx (40→128 LOC)
---

# DEC-V67-C-sub-V67C2-statusstrip · V67-C.2 · B120

## 1 · Decision

Expand StatusStrip from 2 fields to 4 live indicators per Blueprint v3 §4 + V67-C charter Done dim #2.

## 2 · Changes

### StatusStrip.tsx (30 → 130 LOC)

| # | Field | Prop | Default | Test ID |
|---|---|---|---|---|
| 1 | last action | `lastAction?: string \| null` | "—" | `status-strip-last-action` |
| 2 | validation | `validation?: string \| null` | null (omitted) | `status-strip-validation` |
| 3 | progress | `currentStep?: number / totalSteps?: number / stepStatus?: "idle"\|"running"\|"done"\|"error"` | null/5/idle | `status-strip-progress` |
| 4 | trust state | `trustState?: "PASS"\|"PASS_WITH_DISCLAIMER"\|"FAIL"\|"PENDING" \| null` | null (omitted) | `status-strip-trust-state` |

**Visual design**:
- Truncating lastAction left + flex-1 (takes available space)
- Right cluster: progress · trust · validation · separated by surface-700 dots
- Status icons: `○` idle / `●` running / `✓` done / `✗` error
- Trust shorthand: ✓ / ✓* / ✗ / —

**Backward-compat**: Legacy `lastAction` + `validation` semantics preserved exactly. New 3 props are all optional with null defaults that omit the field entirely.

### StatusStrip.test.tsx (40 → 128 LOC)

11 unit tests covering:
1-4. Legacy lastAction + validation behavior preserved (4 tests)
5. progress indicator rendered when currentStep + stepStatus provided
6. stepStatus 4 variants (idle/running/done/error → ○/●/✓/✗)
7. progress omitted when currentStep=null
8. custom totalSteps respected
9. trustState 4 variants
10. trustState omitted when null
11. all 4 fields rendered together

Run result: `npx vitest run StatusStrip.test.tsx` → **11/11 PASS** (1.13s).

## 3 · Done dim impact

- **V67-C-DONE-2**: ❌ → **✅ MET**

## 4 · 4Q gate

| Q | A |
|---|---|
| LLM offline | ✓ Pure render; no LLM dependency |
| Artifacts | ✓ Component + test + this sub-DEC |
| TrustGate | ✓ trustState prop surfaces 4-state trust visibility |
| AI advisory-only | ✓ No MUTATING_ROUTES diff |

## 5 · v2.3 compliance

- DEC scope: sub-DEC (single component refactor + test)
- Codex 1-sync-trigger: NOT triggered
- Kogami opt-in: NOT invoked
- Confidence: high (11/11 tests PASS)
- Counter: B120 autonomous_governance=true · +1

## 6 · Out of scope for V67-C.2

- StepPanelShell call-site wiring to feed `currentStep` from URL `?step=N` + `stepStatus` from active step's React Query state (deferred to V67-C.3 Engineer Control Rail integration)
- Trust state real backend wiring (deferred to V67-C.6 data wiring)

— Claude Code (Opus 4.7 1M) · B120 · V67-C.2 · 2026-05-16
