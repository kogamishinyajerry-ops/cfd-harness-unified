---
decision_id: DEC-V68-B.1
title: V68-B.1 · Backend dev bootstrap · start-ui-dev.sh readiness wait + 5 readiness probe tests + MSW retire-default verified
status: Accepted
parent_dec: DEC-V68-B-charter
phase: V68-B
notion_sync_status: pending
predecessor: DEC-V68-B-charter
batch: B134
confidence: med
autonomous_governance: true
verdict: SUB_DEC_LANDED
v_row_landed: none (sub-DEC)
substrate: V68-B charter §4 Done dim #1 + §5 sub-DEC V68-B.1
---

# DEC-V68-B.1 · Backend dev bootstrap

## 1 · Decision

Land V68-B.1 by:
- Adding backend-readiness wait loop to `scripts/start-ui-dev.sh` (12 polls × 0.5s) before launching vite — so vite proxy doesn't ECONNREFUSED on first /api/* request.
- Adding 5 readiness-probe pytest cases verifying: app construction · routes registered · /api/cases LIST returns ≥10 corpus cases · /api/cases/:id GET returns real metadata · /api/cases/:id/completeness returns real audit · unknown ID returns 404.
- Confirming MSW retire-default semantics: `main.tsx` `enableMocksIfRequested()` correctly gated by `import.meta.env.VITE_MSW === "1"` (already true since V68-A.1 · re-asserted as part of V68-B.1 acceptance).

**Done dim #1 (Backend dev bootstrap) → FULL-MET** at sub-DEC landing.

## 2 · Rationale · why readiness probe now

V68-A's e2e logs showed `[vite] http proxy error: /api/cases/v68a-demo/mesh/render · ECONNREFUSED 127.0.0.1:8000`. This was *cosmetic* in V68-A (MSW intercepted before vite proxy), but in V68-B it's a *real failure* — the workbench depends on backend responsiveness from first page load.

`start-ui-dev.sh` previously launched fastapi + vite concurrently with no synchronization. The 12-poll × 0.5s wait gives uvicorn time to bind + import heavy modules (FreeCAD/trimesh) before vite starts proxying.

The 5 pytest readiness probes act as a *pre-flight contract* — if these break, V68-B integration is unhealthy regardless of how the e2e fares.

## 3 · Implementation

### Files modified (1)

- `scripts/start-ui-dev.sh`
  - Added 12-poll × 0.5s curl loop on `/api/cases` between launching uvicorn and launching vite
  - "backend ready (took N polls × 0.5s)" diagnostic printed on success
  - Best-effort: if backend still isn't answering after ~6s, frontend launches anyway (uvicorn might be slow on heavy module imports; vite HMR can re-proxy once backend responds)

### Files added (1 NEW)

- `ui/backend/tests/test_v68b_readiness_probe.py` (5 tests)
  - `test_app_imports_and_constructs` — app.title == "CFD Harness UI Backend"; `/api/cases` + `/api/cases/{case_id}` both in `app.router.routes`
  - `test_cases_list_returns_corpus` — `GET /api/cases` returns ≥10 entries · canonical IDs `lid_driven_cavity`/`backward_facing_step`/`naca0012_airfoil` present
  - `test_case_detail_returns_real_metadata` — `GET /api/cases/lid_driven_cavity` returns `solver=icoFoam` + `parameters.Re`
  - `test_case_completeness_returns_real_audit` — `GET /api/cases/:id/completeness` 200 + `case_id` field
  - `test_unknown_case_returns_404` — unknown ID resolves to 404 (real error path, not mock 200)

## 4 · Test evidence

- `PYTHONPATH=. pytest ui/backend/tests/test_v68b_readiness_probe.py`: **5/5 PASS** (1.06s)
- `bash scripts/governance/v68b_fleet/score_smoke.sh` (post-V68-B.1): smoke score **100/100** with backend_http_probe subscore=1 (uvicorn boots + curl `/api/cases` returns 200)
- MSW gate verified by code inspection: `main.tsx:23-28` `enableMocksIfRequested()` returns early when `import.meta.env.VITE_MSW !== "1"`; MSW handlers + worker only `import()` when opt-in flag set

## 5 · v2.3 governance compliance

- **DEC scope**: sub-DEC (crosses scripts/ + ui/backend/tests/ + verified main.tsx; ≥3 shared paths)
- **Codex 1-sync-trigger**: NOT applicable (no auth/signing/security boundary)
- **Kogami opt-in**: NOT invoked
- **Confidence**: med (port handling + concurrent process bootstrap)
- **Counter**: B134 autonomous_governance=true · +1

## 6 · 4Q gate

| Q | A | Justification |
|---|---|---|
| LLM offline | ✓ YES | start-ui-dev.sh launches local fastapi + vite · no LLM dep |
| Artifacts produced | ✓ YES | start-ui-dev.sh diff + readiness probe test file + DEC |
| TrustGate / audit | ✓ YES | backend /completeness endpoint return shape verified via probe |
| Advisor-only · no mutating route | ✓ YES | all probes GET-only · V132 MUTATING_ROUTES = 9 unchanged |

## 7 · What this LANDS for V68-B close

- Done dim #1 Backend dev bootstrap: **FULL-MET**
- Backend HTTP probe in fleet smoke now passes deterministically
- Substrate for V68-B.2 (UI wired to real /api/cases) verified contract-shape-wise

## 8 · Out of scope

- **NOT** removing MSW entirely (still opt-in for offline-airplane dev + isolation specs)
- **NOT** touching V132 MUTATING_ROUTES
- **NOT** adding auth (no security boundary)

— Claude Code (Opus 4.7 1M) · B134 · V68-B.1 backend bootstrap · 2026-05-16
