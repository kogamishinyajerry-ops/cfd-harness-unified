---
decision_id: DEC-V68-B-charter
title: V68-B "Real Backend & Industrial Dogfood" arc charter · MSW→fastapi swap + pixel-diff CI 0.01 + case_002a APU bay dogfood + OpenFOAM-WASM spike · Pillar 6 95→97 · ≥99 fleet mandate
status: Accepted
parent_dec: DEC-V68-A-close
phase: V68-B
notion_sync_status: pending
predecessor: DEC-V68-A-close
batch: B133
confidence: high
autonomous_governance: true
verdict: ARC_CHARTER_ACCEPTED
v_row_landed: none (charter)
substrate: V68-A close DEC §9 follow-on candidates · user mandate "全都要" (B+C+E + D-spike)
---

# DEC-V68-B-charter · V68-B "Real Backend & Industrial Dogfood"

## 1 · Decision

Launch successor arc **V68-B "Real Backend & Industrial Dogfood"** consolidating user-selected combined scope (B+C+E + D-spike):
- **B (real backend)**: fastapi serves real /api/cases/* data · MSW retired as default
- **C (pixel-diff CI)**: visual baseline threshold tightened 0.1 → 0.01
- **E (industrial dogfood)**: existing extended case (case_002a APU bay) reachable via /workbench/case/case_002a
- **D-spike (OpenFOAM-WASM)**: feasibility probe only · ≤30 LOC · NO actual solver compile

User mandate (continuation of V67-C / V68-A pattern): *"全权开发 · 7-agent fleet · 真实测评 · 使用手感 · 可视化追踪 · ≥99 分以上 · 一直迭代"*. V68-B closes the gap between V68-A "MSW-mocked workbench" → V68-B "real backend + real industrial case".

## 2 · Rationale · why real backend now

V68-A delivered FULL-MET on 7/7 Done dims but operated against MSW mocks (`VITE_MSW=1` opt-in). The "use手感" delivered was real *for the UI layer* but not yet wired to real data. V68-B closes the final mile:
- backend already exists (`uv run uvicorn ui.backend.main:app` verified bootable · `/api/cases` returns 10 whitelist cases · `/api/cases/lid_driven_cavity` returns full metadata)
- proxy errors observed in V68-A logs (`ECONNREFUSED 127.0.0.1:8000`) were *because backend wasn't running*, not because integration was broken
- gap = dev workflow + e2e workflow + industrial-case demonstration

Pillar 6 ceiling: 95 → **97** (+2 raw · +0.2 weighted · honest small lift because backend already plumbed; the value is dogfood + threshold rigor, not new infrastructure).

## 3 · North Star

> "工程师启动 `./scripts/start-ui-dev.sh` (起 fastapi + vite)，访问 `/workbench/case/case_002a` 看到 APU bay industrial case 真实加载 (geometry render · mesh stats · BC patches · 真实 audit verdict · CompletenessCard 真实数据)。pixel-diff CI gate 收紧到 0.01 阻挡视觉退化。Playwright e2e 跑通真实 backend 后的全流程。OpenFOAM-WASM spike 记录 emscripten 工具链 + WASM 编译 gap manifest 作为后续 arc 决策依据。"

## 4 · Done Definition (7 dims · all FULL-MET for V68-B close · same standard as V68-A)

| # | Done dim | Threshold | Verification |
|---|---|---|---|
| 1 | Backend dev bootstrap | `./scripts/start-ui-dev.sh` script · fastapi + vite both start · `/health` returns 200 · MSW retired as default (`VITE_MSW=1` still opt-in for tests) | start script + readiness probe vitest + 1 e2e against real backend |
| 2 | /api/cases real serving | LIST + GET + status/completeness all return corpus data (not mock) · 10 whitelist cases + case_002a APU bay reachable | `useCaseStatus` integration · backend smoke + 1 e2e |
| 3 | CompletenessCard real-data wiring | /api/cases/:id/completeness returns real audit verdict · MeshQualityCard reads polyMesh stats · ProposalCard reads ai_advisor route | integration tests · 1 e2e end-to-end |
| 4 | Industrial case dogfood (case_002a APU bay) | /workbench/case/case_002a renders · 5-step spine navigable · geometry artifact serves · audit verdict displayed · MSW path completely bypassed | `e2e/industrial-dogfood.spec.ts` 5+ tests PASS |
| 5 | pixel-diff CI gate (0.01 threshold) | `maxDiffPixelRatio: 0.01` (was 0.1) · all 8+ existing baselines re-validate · ≥4 new baselines for case_002a states | `e2e/visual-baseline.spec.ts` updated · 12+ PNG total |
| 6 | E2E against real backend | Playwright e2e runs against real fastapi backend (MSW disabled) · case_002a flow PASS · no proxy ECONNREFUSED | `playwright.config.ts` webServer change · ≥3 specs PASS |
| 7 | OpenFOAM-WASM spike + Pillar 6 ≥97 re-anchor | spike-class: emscripten check + WASM gap manifest written to `.planning/research/openfoam_wasm_feasibility.md` (≤30 LOC code change · NO actual compile) · Pillar 6 anchor language updated | V68-B close DEC §10 |

**Close gate**: 7/7 Done dims FULL-MET (no SCAFFOLDING discount) + fleet min(7) ≥99 for 2 consecutive iter.

## 5 · Sub-DEC seeds (5 sub-DECs + 1 spike-class commit)

### V68-B.1 · Backend bootstrap + dev startup script
- `scripts/start-ui-dev.sh` (NEW · starts fastapi + vite concurrently · port collision detection)
- main.tsx: MSW default OFF (`VITE_MSW=1` still opt-in for unit + isolation specs)
- Backend readiness probe vitest
- LOC est: ~80 prod + 30 test
- Confidence: med (port handling + concurrent process management)

### V68-B.2 · /api/cases real serving wired into UI
- WorkbenchIndexPage reads `/api/cases` directly (already does · verify no broken state under MSW-off)
- useCaseStatus path verified against real fastapi
- LOC est: ~40 prod + 60 test (mostly integration adjustments)
- Confidence: med

### V68-B.3 · CompletenessCard real-data wiring
- /api/cases/:id/completeness real-route confirmed serving
- CompletenessCard test against real-shape fixture (no MSW)
- LOC est: ~30 prod + 80 test
- Confidence: med

### V68-B.4 · Industrial case dogfood (case_002a APU bay) + pixel-diff CI gate
- `e2e/industrial-dogfood.spec.ts` (NEW · ≥5 tests)
- pixel-diff threshold 0.1 → 0.01 in playwright.config.ts
- 4 new baselines for case_002a-specific UI states
- LOC est: ~120 test + 4 PNG baselines
- Confidence: med (case_002a is a sandbox case · need to verify backend resolves its ID)

### V68-B.5 · E2E against real backend + close
- playwright.config.ts webServer command: `npm run dev` (no VITE_MSW=1)
- backend webServer co-process (fastapi)
- full-flow.spec.ts re-pointed to real backend
- V68-B close DEC + retro
- LOC est: ~50 config + e2e specs adjustments
- Confidence: med

### V68-B.6-spike · OpenFOAM-WASM feasibility (spike-class)
- Per v2.3 spike rules: ≤30 LOC + 1 test + commit message `confidence: <h/m/l>` + NO DEC needed
- Output: `.planning/research/openfoam_wasm_feasibility.md` with: emscripten version check · OpenFOAM C++ source dependency manifest · WASM compilation gap list · go/no-go recommendation for hypothetical V68-D arc
- Confidence: low (this is a research probe · expected answer is "needs multi-week dedicated arc")
- NOT counted toward 5/5 sub-DEC LANDED · counted as spike commit only

## 6 · 7-agent fleet (v68b_fleet/ clone with further tightened criteria)

| # | Agent | V68-A criteria | V68-B criteria (further tightened) |
|---|---|---|---|
| 1 Code Quality | typecheck+lint+vitest | (unchanged · still binary 100) |
| 2 Physics | mass_balance+corpus+bc_routes | (unchanged) |
| 3 UX/Playability | ≥5 specs PASS | **≥7 specs PASS** for FULL (V68-A had ≥5) |
| 4 Visualization | ≥4 viewport-mode + ≥6 PNG | **≥4 viewport-mode + ≥12 PNG** (V68-A had 8 · adds 4 case_002a states) |
| 5 Smoke | backend import + build + tc + lint | **+ backend HTTP probe** (fastapi /health returns 200) |
| 6 Functional | 5/5 LANDED + 7/7 Done | (unchanged formula · same 5+7 targets) |
| 7 Stability | vitest flake | (unchanged) |

Score formulas unchanged; thresholds tightened to require dogfood-real coverage.

## 7 · Iteration loop (mandatory · same as V67-C / V68-A pattern)

Identical iteration loop as V68-A charter §7. Reverse-stop triggers unchanged.

## 8 · v2.3 governance compliance

- DEC scope: charter (cross ≥3 paths: backend + frontend + e2e + fleet)
- Codex 1-sync-trigger: NOT applicable (backend already exists · no new auth/signing/security boundary)
- Kogami opt-in: NOT invoked (user autonomous mandate continues)
- Confidence: high (charter scope clear · backend bootability already proven)
- Counter: B133 autonomous_governance=true · +1
- **Spike-class clause**: V68-B.6 OpenFOAM-WASM spike is intentionally NOT a sub-DEC per v2.3 round-1 loosen. ≤30 LOC + 1 manifest file + commit message confidence trailer = sufficient governance footprint.

## 9 · 4Q gate baseline answers

| Q | A | Justification |
|---|---|---|
| LLM offline · workbench full pipeline | ✓ YES | real backend doesn't introduce LLM dep · advisor stays advisory-only |
| Artifacts produced | ✓ YES | start-script + backend integration + 5 sub-DECs + iter scores + WASM feasibility manifest |
| TrustGate / completeness / audit trail | ✓ YES | real /completeness route now drives TopBar audit% · TrustGate flips from real audit verdict (vs V68-A mock) |
| AI advisory-only · no mutating route | ✓ YES | V132 MUTATING_ROUTES baseline still 9 · audit re-runs each iter |

## 10 · Out of scope (explicit non-goals)

- **NOT** OpenFOAM-WASM actual compile (D-spike is research only · full D-arc deferred)
- **NOT** rewriting /api/cases routes (they exist and work · scope is wiring + dogfood)
- **NOT** touching V132 MUTATING_ROUTES (locked)
- **NOT** introducing LLM dependency
- **NOT** touching Pillar 1/2/3/4/5/7 anchors (frozen · V68-B advances Pillar 6 only)
- **NOT** new auth or signing semantics (no Codex 1-sync-trigger needed)

## 11 · Predicted trajectory

- iter 0 (post-charter baseline): functional drops to 0 (new criteria: 0/5 V68-B sub-DECs LANDED · 0/7 V68-B Done dims · visualization drops if PNG count <12 with new threshold)
- iter 1 (V68-B.1 bootstrap): functional partial · start script + MSW default off
- iter 2-4: sub-DECs land incrementally
- iter 5+: ≥99 for 2 consecutive · close ratified

V68-B may temporarily REGRESS overall score in iter 0 because criteria tighten. This is **honest** — V68-A's 100/100 was against V68-A criteria, not V68-B's.

## 12 · Failure modes to flag

If any below trigger during execution, **surface to user immediately**:
- fastapi backend won't start in dev (port conflict / dependency drift)
- case_002a routes 404 on real backend (corpus data missing)
- pixel-diff 0.01 threshold causes existing baselines to fail on stable rerun (font rendering across runs)
- Playwright + concurrent backend webServer hangs >2min
- OpenFOAM-WASM spike reveals emscripten toolchain catastrophically broken (e.g. xcode-select drift)

— Claude Code (Opus 4.7 1M) · B133 · V68-B charter · 2026-05-16
