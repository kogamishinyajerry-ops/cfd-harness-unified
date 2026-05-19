---
decision_id: DEC-V68-A.1
title: V68-A.1 · MSW bootstrap · /api/* network-layer mocking for frontend dev + e2e + visual baseline
status: Accepted
parent_dec: DEC-V68-A-charter
phase: V68-A
notion_sync_status: pending
predecessor: DEC-V68-A-charter
batch: B127
confidence: med
autonomous_governance: true
verdict: SUB_DEC_LANDED
v_row_landed: none (sub-DEC)
substrate: V68-A charter §4 Done dim #1 + §5 sub-DEC V68-A.1
---

# DEC-V68-A.1 · MSW bootstrap

## 1 · Decision

Install **MSW 2.14.6** at the network layer + wire 7 mock handlers covering
the `/workbench/case/{id}` SPA render path. Opt-in via `VITE_MSW=1` env flag;
production builds skip MSW entirely.

**Done dim #1 (MSW backend mocking) → FULL-MET** at sub-DEC landing.

## 2 · Rationale · why MSW now

V67-C close DEC §3 explicitly deferred MSW to V68-A because StepPanelShell
needs `/api/cases/{id}` to render anything beyond the SPA shell. Without
MSW, `/workbench/case/{id}` is 404-empty in e2e + visual baseline runs;
with MSW the full 5-step pipeline becomes reachable for the FIRST time
in dev/test environments.

MSW operates at the Service Worker layer (browser) + Node msw/node layer
(vitest), so test code can `import handlers` without spinning a real
fastapi server. This is the substrate that unlocks V68-A.2/.3/.4/.5.

## 3 · Implementation

### Files added (3 NEW + 1 worker)

- `ui/frontend/src/mocks/handlers.ts` (~100 LOC) — 7 `http.get(...)` handlers:
  1. `GET /api/cases/:caseId` — case metadata + 5-step state machine
  2. `GET /api/cases/:caseId/status` — TopBar 4-field source (truthSource /
     trustGate / auditPct / llmOffline)
  3. `GET /api/cases/:caseId/geometry/render` — geometry artifact descriptor
  4. `GET /api/cases/:caseId/geometry/stl` — minimal ASCII STL blob
  5. `GET /api/cases/:caseId/mesh/render` — mesh wireframe descriptor
  6. `GET /api/cases/:caseId/bc/render` — boundary patch list
  7. `GET /api/import/stl` — bootstrap probe
- `ui/frontend/src/mocks/browser.ts` (~10 LOC) — `setupWorker(...handlers)`
- `ui/frontend/src/mocks/__tests__/handlers.test.ts` — 3 shape tests
- `ui/frontend/public/mockServiceWorker.js` (349 LOC · `npx msw init` output)

### Files modified (1)

- `ui/frontend/src/main.tsx` — `enableMocksIfRequested()` gated on
  `import.meta.env.VITE_MSW === "1"`; never runs in production build

### Dependency added (1)

- `msw@^2.14.6` (devDependency)

## 4 · Test evidence

- `vitest run src/mocks/__tests__/handlers.test.ts`: 3/3 PASS
- `vitest run` (full suite): **342/342 PASS** (was 339, +3 for MSW shape tests)
- `npx tsc --noEmit`: 0 errors
- `npm run build`: clean build · 820 modules transformed
- MSW does NOT mutate any of V132's 9 MUTATING_ROUTES (all handlers are
  `http.get` · advisor-only invariant preserved)

## 5 · v2.3 governance compliance

- **DEC scope**: sub-DEC (crosses `src/mocks/` + `src/main.tsx` + `public/` +
  vitest path · ≥3 shared paths threshold MET → full DEC, not spike-class)
- **Codex 1-sync-trigger**: NOT applicable (no auth / signing / security
  boundary · pure dev-only network mock)
- **Kogami opt-in**: NOT invoked (user autonomous mandate continues)
- **Confidence**: med (new dependency · service worker registration semantics)
- **Counter**: B127 autonomous_governance=true · +1

## 6 · 4Q gate

| Q | A | Justification |
|---|---|---|
| LLM offline · workbench full pipeline | ✓ YES | MSW is the substrate that **enables** LLM-offline workbench (no real backend needed) |
| Artifacts produced | ✓ YES | handlers.ts + browser.ts + handlers.test.ts + mockServiceWorker.js + DEC |
| TrustGate / completeness / audit trail | ✓ YES | `/api/cases/:id/status` mock returns `trust_gate: "audit-passing"` + `audit_pct: 87` — TopBar wiring (V68-A.2) consumes these |
| AI advisory-only · no mutating route | ✓ YES | all 7 handlers are `http.get` · V132 MUTATING_ROUTES = 9 unchanged |

## 7 · What this LANDS for V68-A close

- Done dim #1 MSW backend mocking: **FULL-MET** (was 0/7 before this sub-DEC)
- Substrate for V68-A.2 (TopBar real data wiring via useCaseStatus)
- Substrate for V68-A.5 (e2e Import→Mesh→BC→Solve→Results against mocked backend)

## 8 · Out of scope (explicit non-goals)

- **NOT** mocking POST/PATCH/DELETE (V132 baseline locked)
- **NOT** mocking solver step real-time updates (V68-A.5 territory)
- **NOT** Beginner/Power toggle wiring (V68-A.3 territory)
- **NOT** viewport mode dispatcher (V68-A.4 territory)

— Claude Code (Opus 4.7 1M) · B127 · V68-A.1 MSW bootstrap · 2026-05-16
