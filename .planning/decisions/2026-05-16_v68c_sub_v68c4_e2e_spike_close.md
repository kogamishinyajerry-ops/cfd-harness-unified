---
decision_id: DEC-V68-C.4
title: V68-C.4 · 4 E2E specs + V68-D iter-2 WASM spike + 4 visual baselines · arc close
status: Accepted
parent_dec: DEC-V68-C-charter
phase: V68-C
notion_sync_status: pending
predecessor: DEC-V68-C-charter
batch: B147-B148
confidence: high
autonomous_governance: true
verdict: SUB_DEC_LANDED
v_row_landed: none (sub-DEC)
substrate: V68-C charter §3 Done dim #6 + §5 sub-DEC V68-C.4 + §3 Done dim #7-spike
---

# DEC-V68-C.4 · E2E + iter-2 spike + arc close

## 1 · Decision

Land V68-C.4 by:
- Authoring 4 new playwright e2e specs (6 tests total) verifying V68-C surfaces against real fastapi backend:
  - `v68c-material-card.spec.ts` (1 test) — catalog reachability + V68-C.1/C.3 integration
  - `v68c-ai-review.spec.ts` (1 test) — SPA renders against real backend without pageerror post-V68-C.2 refactor
  - `v68c-ai-diagnose.spec.ts` (2 tests) — backend GET /ai-review + /ai-diagnose routes wired (4xx not 5xx)
  - `v68c-apu-bay-catalog.spec.ts` (2 tests) — GET /api/cases returns 11 entries with case_002a; workbench index renders ⏳ gold pending badge
- Adding 4 visual baselines (12 → 16 PNG, hitting V68-C charter §4 threshold):
  - `13-index-with-apu-bay.png` (catalog index with case_002a card)
  - `14-apu-bay-card-cropped.png` (APU bay card detail)
  - `15-index-fullpage.png` (full 11-card layout)
  - `16-rail-control.png` (viewport-mode rail · V68-A→C regression proof)
- Authoring V68-D iter-2 WASM feasibility spike (`.planning/research/openfoam_wasm_feasibility_iter2.md`):
  - Docker daemon health probed (HEALTHY v29.2.1 OSType linux)
  - Docker-based emsdk path upgraded alternative → recommended (audit-grade reproducibility · CI portability)
  - Engineering-week estimate narrowed 14-22 → 12-19 weeks via parmetis + paraview triage
  - 3 new dependencies surfaced (kahip / cgal / fmt) without changing bottom line
  - 5-question go/no-go decision tree for future V68-D arc; iter-2 conclusion: defer (zero current "yes" answers)
  - **NO compilation attempted · NO image pulled** — spike-class per v2.3 governance

**Done dim mapping**:
- **DONE-6 · E2E against real backend (extended)** → **MET** at this sub-DEC (43 e2e total · 37 prior + 6 V68-C all PASS · V68-C charter §4 target ≥41 EXCEEDED)
- **DONE-7-spike · V68-D iter-2 continued spike** → **MET** at this sub-DEC (iter-2 artifact archived; arc-close authoring §3 below provides Pillar 6/7 re-anchor)

## 2 · Rationale · why 6 e2e tests (not exactly 4)

V68-C charter §3 said "+4 V68-C cases". The natural test boundary cut the V68-C.3 work into 2 tests (route reachability + workbench badge render) because they exercise different layers — fragmenting one into one spec would have made each less honest. The V68-C.2 work also cut into 2 tests (SPA render + backend wire). Total 6 tests in 4 spec files; charter intent (covering all V68-C surfaces) preserved without forcing a 1:1 spec:test mapping.

## 3 · Rationale · why visual baselines despite no UI churn in V68-C.1/.2

V68-C.1 added MaterialCard to Step3SetupBC (catalog-internal screen we can't easily snapshot under real backend due to known StrictMode flakiness · industrial-dogfood.spec.ts §11). V68-C.3 added a new card to the catalog index (snapshotable). V68-C.2 changed the AIAdvisorPanel state shape (catalog-internal). The 4 new baselines target what IS stably snapshotable post-V68-C:
- 2 baselines exercise the V68-C.3 UI change (index/card detail)
- 1 baseline (full-page) verifies the 11-card grid layout didn't regress
- 1 baseline (rail control) is a **deliberate regression-proof anchor** for the V68-A→C-stable substrate

Pixel-diff at 0.01 maxDiffPixelRatio · all 16 PNG re-run stable.

## 4 · Pillar 6 + Pillar 7 re-anchor

V68-C charter target: Pillar 6 97→98 + Pillar 7 82→85 · weighted +0.25 ceiling.

**Pillar 6 (Workbench Functional Completeness · 97 → 98)** evidence:
- M3 MaterialCard real-data wiring lands the read-only physics state surface that V68-A only had in PhysicsPanel-as-author form
- AI advisor offline graceful fallback removes the "advisor broken = workbench broken" UX cliff
- case_002a in the catalog: industrial substrate now FIRST-CLASS in browsing (not hidden behind charter knowledge)
- 43 e2e total against real backend (was 37) · 405 vitest PASS (was 376)

**Pillar 7 (Audit-Grade Trust Substrate · 82 → 85)** evidence:
- gold_pending flag is the **first explicit catalog-level audit-state honesty marker**. Pre-V68-C, the catalog implied "every listed case has a verified gold" — now it explicitly differentiates curated whitelist vs imported_user pending
- AI advisor offline state preserves V130 invariant under transient backend failure (no false confidence)
- 4 new visual baselines lock the audit-surface visual contract (badge + disclaimer must look the same on every CI run)
- batch_matrix + batch.csv filtering of gold_pending entries prevents AUDIT SIGNAL DILUTION — the trust-grade reports stay gold-anchored

## 5 · Implementation summary

- **e2e**: 6 new tests in 4 specs · 43 total · all PASS against real fastapi+vite dual-webServer
- **Visual baselines**: 4 new PNG · 16 total · 0.01 maxDiffPixelRatio · re-run stable
- **WASM spike**: 1 new research artifact (~3K words) · 0 LOC committed · 0 disk pull
- **MUTATING_ROUTES net diff**: 0 (V132 invariant preserved)
- **Test regression**: 405/405 vitest PASS · 43/43 playwright PASS · backend regression suite unchanged

## 6 · Files changed (this sub-DEC)

| File | Status | Purpose |
|---|---|---|
| ui/frontend/e2e/v68c-material-card.spec.ts | A | catalog reachability |
| ui/frontend/e2e/v68c-ai-review.spec.ts | A | SPA render against real backend |
| ui/frontend/e2e/v68c-ai-diagnose.spec.ts | A | route wire verification |
| ui/frontend/e2e/v68c-apu-bay-catalog.spec.ts | A | catalog + badge integration |
| ui/frontend/e2e/visual-baseline.spec.ts | M | +4 new spec entries |
| ui/frontend/__visual_baselines__/chromium/visual-baseline.spec.ts-snapshots/13-16-*.png | A | 4 new PNG |
| .planning/research/openfoam_wasm_feasibility_iter2.md | A | V68-D iter-2 spike artifact |
| .planning/scores/V68-C_iter_2.md | A | iter-2 fleet score |

## 7 · Honest scope · what's NOT in V68-C.4

- **No MaterialCard playwright deep-snapshot**: Step3SetupBC mounted at /workbench/case/:id has known StrictMode flakiness · vitest covers the surface integration with 21 tests
- **No AI advisor full-flow e2e**: would require a `case_002a` actually materialized in IMPORTED_DIR; deferred to future arc when imported_user materialization lands
- **No WASM compilation**: deliberate spike-class scope discipline

## 8 · Confidence: high

- All charter Done dims #1-7 MET (5 + 2-via-V68-A-inheritance + this sub-DEC's 2)
- 7-pillar fleet expected to hit min(7) ≥ 99 in iter-3 after this sub-DEC + close DEC land (functional 73 → 100)
- Pillar 6 + Pillar 7 progression evidenced (§4)
- Zero MUTATING_ROUTES drift · 43 e2e PASS · 405 vitest PASS · typecheck clean · lint 0 errors

— V68-C.4 sub-DEC · 2026-05-16 · B147+B148
