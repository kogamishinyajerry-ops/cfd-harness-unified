---
decision_id: DEC-V68-A.2
title: V68-A.2 · TopBar real data wiring · useCaseStatus React Query hook backs 4 dynamic fields
status: Accepted
parent_dec: DEC-V68-A-charter
phase: V68-A
notion_sync_status: pending
predecessor: DEC-V68-A.1
batch: B128
confidence: med
autonomous_governance: true
verdict: SUB_DEC_LANDED
v_row_landed: none (sub-DEC)
substrate: V68-A charter §4 Done dim #2 + §5 sub-DEC V68-A.2 · builds on V68-A.1 MSW substrate
---

# DEC-V68-A.2 · TopBar real data wiring

## 1 · Decision

Wire the 4 dynamic TopBar fields (truthSource/trustGate/auditPct/llmOffline)
through a new `useCaseStatus` React Query hook against `GET /api/cases/:id/status`
(MSW-mocked in dev/e2e, real backend in prod).

**Done dim #2 (TopBar real data wiring) → FULL-MET** at sub-DEC landing.

## 2 · Rationale · why wiring now (after MSW)

V67-C.1 landed TopBar's 6-field UI *shape*. StepPanelShell:488 then called
`<TopBar caseId={caseId} />` — caller passed **only caseId**, so the other 5
fields fell through to their blueprint-safe defaults (PENDING/unknown/null).
This satisfied the V67-C SCAFFOLDING bar but left the data path inert.

V68-A.2 closes that loop: the hook normalises backend snake_case (truth_source
/ trust_gate / audit_pct / llm_offline) into TopBar's camelCase props vocab,
clamps invalid/missing values to blueprint defaults, and threads V130
invariant (`llmOffline` defaults to true when unspecified — offline-first
guarantee never escalates to a transient backend hiccup).

MSW (V68-A.1) is the substrate that makes this hook exerciseable without a
real fastapi server during dev/e2e/visual baseline runs.

## 3 · Implementation

### Files added (2 NEW)

- `ui/frontend/src/pages/workbench/step_panel_shell/useCaseStatus.ts` (~105 LOC)
  Exports `useCaseStatus(caseId)` returning `{ status, isLoading, isError }`
  with `status` already normalised + clamped. Also exports pure
  `normalizeCaseStatus(caseId, raw)` for testability without React Query.
- `ui/frontend/src/pages/workbench/step_panel_shell/__tests__/useCaseStatus.test.ts`
  9 normalization tests covering: undefined raw → defaults · trust_gate maps ·
  audit_pct clamping (out-of-range → null) · truth_source kebab+snake variants ·
  V130 llmOffline-defaults-to-true invariant · unknown trust_gate fallback ·
  last_action/validation pass-through.

### Files modified (1)

- `ui/frontend/src/pages/workbench/StepPanelShell.tsx`
  Added `import { useCaseStatus }` + `const { status: caseStatus } = useCaseStatus(caseId)`
  + replaced `<TopBar caseId={caseId} />` with full 5-prop call.

## 4 · Test evidence

- `vitest run useCaseStatus.test.ts`: **9/9 PASS**
- `vitest run` (full suite): **351/351 PASS** (was 342, +9 from new tests)
- `npx tsc --noEmit`: 0 errors (after fixing 2 TS2322 about empty-string
  union narrowing in TRUTH_SOURCE_MAP / TRUST_GATE_MAP lookups)
- V132 baseline unchanged · no new mutating routes

## 5 · v2.3 governance compliance

- **DEC scope**: sub-DEC (crosses `useCaseStatus.ts` + `StepPanelShell.tsx` +
  vitest path · 3 shared paths threshold MET → full DEC, not spike-class)
- **Codex 1-sync-trigger**: NOT applicable (no auth / signing / security
  boundary · GET-only data path)
- **Kogami opt-in**: NOT invoked
- **Confidence**: med (React Query + new normalization logic ·
  9-test coverage)
- **Counter**: B128 autonomous_governance=true · +1

## 6 · 4Q gate

| Q | A | Justification |
|---|---|---|
| LLM offline · workbench full pipeline | ✓ YES | `useCaseStatus` falls back to safe defaults when `/status` 404s · UI never blocks on backend hiccup |
| Artifacts produced | ✓ YES | useCaseStatus.ts + test file + DEC + StepPanelShell call-site change |
| TrustGate / completeness / audit trail | ✓ YES | TopBar `trustGate` flips per backend audit verdict; `auditPct` rolls 0→100 from `/api/cases/:id/status` mock |
| AI advisory-only · no mutating route | ✓ YES | hook only issues `GET /api/cases/:id/status` · V132 MUTATING_ROUTES = 9 unchanged |

## 7 · What this LANDS for V68-A close

- Done dim #2 TopBar real data wiring: **FULL-MET**
- 4 TopBar dynamic fields now actually move with backend data (mocked or real)
- Substrate verified for V68-A.5 e2e to assert `trustGate` progression Import→Solve

## 8 · Out of scope

- **NOT** mutating `/api/cases/:id/status` (V132 baseline locked · advisor-only)
- **NOT** wiring StepBody-internal status (V68-A.3 territory)
- **NOT** viewport mode dispatcher (V68-A.4 territory)

— Claude Code (Opus 4.7 1M) · B128 · V68-A.2 TopBar real data wiring · 2026-05-16
