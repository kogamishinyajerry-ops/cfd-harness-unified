---
decision_id: DEC-V68-B.5
title: V68-B.5 · Playwright e2e against real fastapi backend · MSW off · 37/37 PASS · Done #6 FULL-MET
status: Accepted
parent_dec: DEC-V68-B-charter
phase: V68-B
notion_sync_status: pending
predecessor: DEC-V68-B.4
batch: B137
confidence: med
autonomous_governance: true
verdict: SUB_DEC_LANDED
v_row_landed: none (sub-DEC)
substrate: V68-B charter §4 Done dim #6 · §5 sub-DEC V68-B.5
---

# DEC-V68-B.5 · Playwright e2e against real fastapi backend

## 1 · Decision

Repoint Playwright `webServer` from V68-A single-process (`npm run dev`
with `VITE_MSW=1`) to **dual-process**:
1. fastapi backend via `uv run uvicorn ui.backend.main:app --port 8001`
2. vite frontend via `npm run dev` with `CFD_BACKEND_PORT=8001`

MSW is OFF (no `VITE_MSW` env). E2E now exercises the full
real-backend stack.

**Done dim #6 (E2E against real backend) → FULL-MET** at sub-DEC landing.

## 2 · Rationale · why dual-webServer

V68-A's `webServer: { ..., env: { VITE_MSW: "1" } }` was a single process
that intercepted requests at the browser SW layer. The V68-A logs showed
`ECONNREFUSED 127.0.0.1:8000` because the dev backend wasn't running ·
MSW just masked it.

V68-B's contract is "real backend serves real data" — playwright must
spawn both. Playwright's `webServer` accepts an array; the entries spawn
in parallel and both ports' readiness is polled before tests start.

Backend on **port 8001** (not 8000) so it doesn't collide with a
developer's already-running `start-ui-dev.sh` (which defaults to 8000).
`CFD_BACKEND_PORT=8001` env on vite makes the proxy redirect /api → 8001.

## 3 · Implementation

### Files modified (1)

- `ui/frontend/playwright.config.ts`
  - `webServer: { ... }` (singular object) → `webServer: [ { ... }, { ... } ]` (array)
  - Backend entry: `uv run uvicorn ui.backend.main:app --port 8001 --host 127.0.0.1` · `url: http://127.0.0.1:8001/api/cases` · `cwd: ../../` (relative to playwright.config.ts location)
  - Frontend entry: `npm run dev -- --port 5173` · `env: { CFD_BACKEND_PORT: "8001" }` · MSW intentionally OFF

## 4 · Test evidence

- `playwright test --reporter=line` against new dual-webServer: **37/37 PASS** (22.9s)
  - topbar.spec.ts: 3/3 (V67-C inherited · hardened in V68-A.4)
  - truth-chain.spec.ts: 2/2 (V67-C inherited)
  - viewport-mode.spec.ts: 7/7 (V68-A.4)
  - visual-baseline.spec.ts: 12/12 (V68-A.4 8 + V68-B.4 4 · all at 0.01 threshold)
  - full-flow.spec.ts: 7/7 (V68-A.5)
  - industrial-dogfood.spec.ts: 6/6 (V68-B.4)
- No `ECONNREFUSED` in test output (real backend responds)
- Backend ready-probe: playwright auto-polls `http://127.0.0.1:8001/api/cases` until 200 before launching tests

## 5 · v2.3 governance compliance

- **DEC scope**: sub-DEC (playwright config change · ≥3 paths affected: config + e2e specs + .planning/research)
- **Codex 1-sync-trigger**: NOT applicable (test infra · no auth/signing)
- **Kogami opt-in**: NOT invoked
- **Confidence**: med (concurrent webServer + backend readiness polling)
- **Counter**: B137 autonomous_governance=true · +1

## 6 · 4Q gate

| Q | A | Justification |
|---|---|---|
| LLM offline | ✓ YES | real backend = real fastapi · no LLM in pipeline |
| Artifacts produced | ✓ YES | playwright.config.ts diff + DEC |
| TrustGate / audit | ✓ YES | e2e drives useCaseStatus → real `/completeness` → real trustGate (no mock interception) |
| Advisor-only · no mutating route | ✓ YES | GET-only flow · V132 MUTATING_ROUTES = 9 unchanged |

## 7 · What this LANDS for V68-B close

- Done dim #6 E2E against real backend: **FULL-MET**
- 4/5 sub-DECs LANDED + 6/7 Done dims MET
- Spike V68-B.6 separately landed (research artifact only · doesn't count toward 5/5)
- Only Done dim #7 (Pillar 6 ≥97 re-anchor) remains · ratified by V68-B close DEC §10

## 8 · Out of scope

- **NOT** running OpenFOAM solver during e2e (heavy compute · per-iter smoke is integration-surface only · V68-B.6 spike documents WASM path deferral)
- **NOT** adding new e2e specs against real-backend (existing 37 cover the contract)

— Claude Code (Opus 4.7 1M) · B137 · V68-B.5 real-backend e2e · 2026-05-16
