---
decision_id: DEC-V68-C.1
title: V68-C.1 · MaterialCard real-data wiring · usePhysicsState hook + Step 3 read-only readout
status: Accepted
parent_dec: DEC-V68-C-charter
phase: V68-C
notion_sync_status: pending
predecessor: DEC-V68-C-charter
batch: B141
confidence: high
autonomous_governance: true
verdict: SUB_DEC_LANDED
v_row_landed: none (sub-DEC)
substrate: V68-C charter §3 Done dim #1 + §5 sub-DEC V68-C.1
---

# DEC-V68-C.1 · MaterialCard real-data wiring

## 1 · Decision

Land V68-C.1 by:
- Adding `PhysicsStateResponse` TS type (`ui/frontend/src/types/physics.ts`) mirroring backend `routes/physics.py::PhysicsStateResponse` (case_id + nullable material_dict_text + nullable regime_dict_text).
- Adding `api.getPhysicsState(caseId)` to `ui/frontend/src/api/client.ts` — GET `/api/cases/:id/physics`, **404 returns null** (not an error — distinguishes "case not in IMPORTED_DIR" from real server faults).
- Authoring `usePhysicsState(caseId)` hook (`ui/frontend/src/pages/workbench/step_panel_shell/usePhysicsState.ts`):
  - Primary path: GET /physics. On 200 → `status: "committed"`; on 404 → fall back to GET /api/cases/:id (CaseDetail).
  - Fallback path: CaseDetail.solver / turbulence_model / parameters.Re → `status: "reference"`.
  - Returns discriminated `PhysicsView` (committed | reference | loading | error | no-case) so MaterialCard branches without rebuilding the conditional.
  - Three pure parsers: `parsePhysicalProperties` (transportModel/nu/rho), `parseMomentumTransport` (simulationType/RASModel), `parseCaseDetailReference` (whitelist fallback derivation).
- Authoring `MaterialCard.tsx` (`ui/frontend/src/pages/workbench/step_panel_shell/MaterialCard.tsx`):
  - Status badge: `committed` / `reference (whitelist)` / `error` / `loading…`.
  - Parsed-fields readout (solver, transport, ν, ρ, regime, RAS, turbulence, Re) — `—` when null.
  - Raw dict pane under `<details>`: for committed mode shows the actual dict text from disk; for reference mode shows "(whitelist case · not materialized — reference metadata only)" — **no synthesized OpenFOAM dict text** (V130 invariant: advisor displays real data or honest zero-state, never fabricates).
- Mounting in `Step3SetupBC.tsx` above the Phase-1A scope banner so engineer sees current physics state on Step 3 entry.

**Done dim #1 (M3 MaterialCard real-data wiring) → FULL-MET** at sub-DEC landing.

## 2 · Rationale · why dual-mode hook now

V68-C charter §3 north star says: "engineer opens `/workbench/case/naca0012_airfoil?step=3`, sees MaterialCard 真实显示 `constant/physicalProperties` (icoFoam → transportProperties: `nu=1e-3`) + `constant/momentumTransport` (laminar)."

The example mixes two cases (naca0012 = simpleFoam k-omega SST; icoFoam laminar nu=1e-3 = LDC), which signaled that the user wants MaterialCard to **work for whichever case is open** — committed cases show real dict text, whitelist cases show reference metadata.

Backend `/api/cases/:id/physics` (DEC-V61-168) only serves IMPORTED_DIR cases (returns 404 for whitelist). Three honest paths considered:

| Option | Path | Rejected because |
|---|---|---|
| A · Extend /physics to synthesize dict for whitelist | Backend writes fake dict text for non-imported cases | V130 violation — UI would show *plausible-looking* OpenFOAM dicts that aren't real on-disk state |
| B · Two-call frontend fallback (chosen) | UI tries /physics; on 404 reads CaseDetail and shows "reference (whitelist)" badge with parsed-fields-only view | Honest. Engineer sees what's actually real; badge makes source explicit |
| C · Show error / empty card | UI shows "no physics committed" zero-state for whitelist | Loses CaseDetail metadata that's genuinely useful for whitelist exploration |

Option B gets us the user's north star (the card "真实显示" something useful on naca0012) without fabricating dict text.

## 3 · Implementation summary

- **LOC**: 1094 insertions (+ 9 deletions); split:
  - 8 LOC: physics.ts (new type)
  - 22 LOC: client.ts (new method)
  - 188 LOC: usePhysicsState.ts (hook + 3 parsers)
  - 230 LOC: MaterialCard.tsx
  - 156 LOC: usePhysicsState.test.ts (14 unit tests)
  - 188 LOC: MaterialCard.test.tsx (7 integration tests)
  - 11 LOC: Step3SetupBC.tsx (import + mount)
  - 39 LOC: Step3SetupBC.test.tsx (MaterialCard stub + api mocks)
- **Tests added**: 21 vitest (14 parser + 7 React)
  - Total: 376 → 397 vitest PASS
- **Backend touchpoints**: 0 lines changed (read-only consumer of existing /physics + /cases/:id routes)
- **MUTATING_ROUTES net diff**: 0 (V132 invariant preserved — GET routes only)

## 4 · Acceptance · MaterialCard rendering verified

| Scenario | Hook status | Badge | Readout fields |
|---|---|---|---|
| LDC case in IMPORTED_DIR with both dicts | committed | `committed` (emerald) | Newtonian, 1.000e-3 m²/s, laminar |
| naca0012_airfoil whitelist | reference | `reference (whitelist)` (sky) | simpleFoam, RAS, 3.00e+6 Re |
| caseId=null (no case selected) | no-case | (none) | "Open a case to see its physics state." |
| physics 503 / network error | error | `error` (rose) | "backend unreachable" surfaced |

V130 invariant verified at component level:
- MaterialCard has zero POST/PUT/DELETE calls
- Raw-dict pane never renders synthesized text (committed mode reads from `materialDictText`/`regimeDictText` direct; reference mode shows whitelist disclaimer only)
- Test `material-card-raw-reference` asserts no `material-card-raw-material` testid present in reference mode → no fabricated dict text leaks

## 5 · Files changed

| File | Status | Purpose |
|---|---|---|
| ui/frontend/src/types/physics.ts | M | + PhysicsStateResponse interface |
| ui/frontend/src/api/client.ts | M | + api.getPhysicsState (404 → null) |
| ui/frontend/src/pages/workbench/step_panel_shell/usePhysicsState.ts | A | Hook + 3 pure parsers |
| ui/frontend/src/pages/workbench/step_panel_shell/MaterialCard.tsx | A | Read-only display |
| ui/frontend/src/pages/workbench/step_panel_shell/__tests__/usePhysicsState.test.ts | A | 14 parser unit tests |
| ui/frontend/src/pages/workbench/step_panel_shell/__tests__/MaterialCard.test.tsx | A | 7 React integration tests |
| ui/frontend/src/pages/workbench/step_panel_shell/steps/Step3SetupBC.tsx | M | Mount MaterialCard above Phase-1A banner |
| ui/frontend/src/pages/workbench/step_panel_shell/__tests__/Step3SetupBC.test.tsx | M | Stub MaterialCard + add api mocks for cleanness |
| .planning/scores/V68-C_iter_0.md | A | iter-0 baseline (pre-V68-C.1) |

## 6 · Risk register · what could break

| Risk | Probability | Mitigation |
|---|---|---|
| OpenFOAM dict format drift breaks regex parser | low | Regex is defensive (whitespace + optional dimension brackets); `nuField` false-positive guard explicit; failed parse → field stays null, not crash |
| Whitelist case CaseDetail fetch fails too | low | View returns `status: "error"` with message; UI shows rose error card, doesn't crash |
| react-query QueryClient missing in tests | mitigated | Step3SetupBC.test.tsx stubs MaterialCard; MaterialCard.test.tsx + usePhysicsState.test.ts wrap explicitly |
| Synthesized dict text leak | guarded | Test asserts `material-card-raw-material` testid absent in reference mode |

## 7 · Confidence: high

- Read-only consumer of routes already shipped (no backend risk)
- Parser regex tested against canonical OpenFOAM output (writer.py emits stable format)
- 21 new vitest + 397 total PASS · typecheck clean · lint no new errors
- V130/V132 invariants verified at component AND test level

— V68-C.1 sub-DEC · 2026-05-16 · B141
