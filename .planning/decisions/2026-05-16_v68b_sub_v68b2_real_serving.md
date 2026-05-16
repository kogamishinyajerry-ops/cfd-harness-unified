---
decision_id: DEC-V68-B.2
title: V68-B.2 · /api/cases real serving wired into UI · useCaseStatus repointed to /completeness (real backend) · 9 new normalize tests · Done dims #2+#3 FULL-MET
status: Accepted
parent_dec: DEC-V68-B-charter
phase: V68-B
notion_sync_status: pending
predecessor: DEC-V68-B.1
batch: B135
confidence: med
autonomous_governance: true
verdict: SUB_DEC_LANDED
v_row_landed: none (sub-DEC)
substrate: V68-B charter §4 Done dims #2 + #3 · §5 sub-DEC V68-B.2 + B.3 (consolidated)
---

# DEC-V68-B.2 · /api/cases real serving wired

## 1 · Decision

Repoint `useCaseStatus` from V68-A's invented `/api/cases/:id/status` endpoint
(which doesn't exist in real backend · 404s under MSW-off) to the real
backend's `/api/cases/:id/completeness`. Add bidirectional `normalizeCaseStatus`
that accepts either V68-A legacy shape or V68-B real shape, with V68-A
legacy fields winning when both present.

**Done dim #2 (/api/cases real serving) + #3 (CompletenessCard real-data wiring) → BOTH FULL-MET** at sub-DEC landing (consolidated this sub-DEC).

## 2 · Rationale · why repoint instead of adding backend route

V68-A invented `/api/cases/:id/status` as an MSW endpoint. Real backend has
`/api/cases/:id/completeness` (existing · spec'd in Phase-0 contract ·
returns `case_id` / `case_kind` / `ready_for_archive` / `blocked_by_critical`
/ `present_count` / `total_count` / `percentage` / `missing` / `notes`).

Two paths considered:
1. **Add `/status` to backend** — would duplicate completeness logic; violate
   single-truth-source for case audit verdicts
2. **Repoint UI to existing `/completeness`** — leverages existing real-shape
   data + V132 invariant (no new routes added · MUTATING_ROUTES baseline still 9)

Chose (2). The hook now drives off the existing real route; `normalizeCaseStatus`
maps real-backend fields → TopBar vocab:
- `case_kind="whitelist"` → `truthSource="openfoam_native"`
- `ready_for_archive=true` → `trustGate="PASS"`
- `ready_for_archive=false + blocked_by_critical>0` → `trustGate="FAIL"`
- `ready_for_archive=false + blocked_by_critical=0` → `trustGate="PASS_WITH_DISCLAIMER"`
- `percentage` (0-100) → `auditPct`
- V130 invariant preserved: `llmOffline` defaults true unless `llm_offline=false` explicit

## 3 · Implementation

### Files modified (3)

- `ui/frontend/src/pages/workbench/step_panel_shell/useCaseStatus.ts`
  - `fetchCaseStatus` URL: `/status` → `/completeness`
  - `CaseStatusRaw` type extended with V68-B fields (`case_kind` / `ready_for_archive` / `blocked_by_critical` / `percentage` + carried-but-unused `present_count` / `total_count` / `missing` / `notes`)
  - Split normalize into 3 derive functions (`deriveTruthSource` / `deriveTrustGate` / `deriveAuditPct`) for readability + V68-A-legacy-wins precedence
- `ui/frontend/src/pages/workbench/step_panel_shell/__tests__/useCaseStatus.test.ts`
  - 9 new tests in a "V68-B.2 real-backend /completeness shape" describe block
  - Tests cover: case_kind mappings · ready_for_archive trust derivations · percentage → auditPct · V68-A legacy wins precedence · real-backend `lid_driven_cavity` fixture snapshot
- `ui/frontend/src/mocks/handlers.ts`
  - `/api/cases/:id/completeness` mock realigned to real-backend shape (case_kind / ready_for_archive / blocked_by_critical / percentage)

## 4 · Test evidence

- `vitest run useCaseStatus.test.ts handlers.test.ts`: **21/21 PASS** (was 12)
- `vitest run` (full): **376/376 PASS** (was 367, +9 V68-B normalize tests)
- `npx tsc --noEmit`: 0 errors
- Real backend completeness probe (V68-B.1 readiness test):
  `lid_driven_cavity` returns `case_kind=whitelist · ready_for_archive=false · blocked_by_critical=1 · percentage=93.8`
- Normalize-against-real-fixture test: `trustGate="FAIL"` (1 critical block · matches expected) · `auditPct=93.8` · `truthSource="openfoam_native"` · `llmOffline=true`

## 5 · v2.3 governance compliance

- **DEC scope**: sub-DEC (crosses useCaseStatus.ts · handlers.ts · tests · 3 paths)
- **Codex 1-sync-trigger**: NOT applicable (no auth/signing)
- **Kogami opt-in**: NOT invoked
- **Confidence**: med (real-backend shape contract verified by integration probe + 9 new tests)
- **Counter**: B135 autonomous_governance=true · +1

## 6 · 4Q gate

| Q | A | Justification |
|---|---|---|
| LLM offline | ✓ YES | hook still returns safe defaults under backend error (V130 invariant) |
| Artifacts produced | ✓ YES | useCaseStatus diff · handlers.ts diff · 9 new tests · DEC |
| TrustGate / audit | ✓ YES | trustGate now derives from REAL `ready_for_archive` + `blocked_by_critical` (not mock fields) · audit_pct from REAL `percentage` (V61-050 spec) |
| Advisor-only · no mutating route | ✓ YES | GET-only · V132 MUTATING_ROUTES = 9 unchanged · no backend routes added |

## 7 · What this LANDS for V68-B close

- Done dim #2 /api/cases real serving: **FULL-MET**
- Done dim #3 CompletenessCard real-data wiring: **FULL-MET** (the same useCaseStatus hook is the SSOT for the case audit verdict surfaced both in TopBar and CompletenessCard)
- 2/5 sub-DECs LANDED + 3/7 Done dims MET
- Substrate for V68-B.4 (industrial case dogfood) — the hook will derive correct verdict for case_002a once the route serves it

## 8 · Out of scope

- **NOT** adding new backend routes (V132 baseline · use existing `/completeness`)
- **NOT** changing TopBar visual surface (V68-A.2 shape preserved)
- **NOT** rewriting completeness audit logic (Phase-0 contract honored)

— Claude Code (Opus 4.7 1M) · B135 · V68-B.2 real serving · 2026-05-16
