# ARC-GOAL · V68-C AI Advisor Integration & Material Wiring · **ACTIVE 2026-05-16**

> **Charter**: `.planning/decisions/2026-05-16_v68c_charter_dec.md` (Accepted B139 · 2026-05-16)
> **Predecessor**: DEC-V68-B-close (B138 · 79.50 weighted · Pillar 6 97, Pillar 7 82)
> **Target**: Pillar 6 97→98 + Pillar 7 82→85 · weighted +0.25 ceiling
> **User mandate**: "全都要" · C+F core, E metadata-only, D continued spike

## North Star (charter §3 verbatim)

> "工程师打开 `/workbench/case/naca0012_airfoil?step=3`，看到 MaterialCard 真实显示 `constant/physicalProperties` (icoFoam → transportProperties: `nu=1e-3`) + `constant/momentumTransport` (laminar)。打开 ProposalCard，点 [审 review] 真实 GET /ai-review · 返回 review verdict + comments；点 [诊 diagnose] 真实 GET /ai-diagnose · 返回 diagnosis + 建议。两个 AI 路由 LLM-offline 时仍返回 graceful 'advisor offline' 状态，UI 不挂。case_002a APU bay 在 `/workbench` index 可见，标 `⏳ gold pending`，点开能跳到对应 case page (即便 gold 还没补完)。OpenFOAM-WASM iter-2 spike 记录 docker-based emsdk 路径 + 进一步的 dep triage。"

## Done dim checklist (7 dims · all required for V68-C close · FULL delivery only)

- [x] **V68-C-DONE-1 · M3 MaterialCard real-data wiring** — `usePhysicsState` hook hits `/api/cases/:id/physics` · MaterialCard renders material + regime · committed (200) + reference (404→CaseDetail fallback) · 21 new vitest · B141
- [ ] **V68-C-DONE-2 · ProposalCard AI review real route** — Real `/ai-review` returns ReviewResponse · displayed in ProposalCard
- [ ] **V68-C-DONE-3 · ProposalCard AI diagnose real route** — Real `/ai-diagnose` returns DiagnoseResponse
- [ ] **V68-C-DONE-4 · LLM-offline graceful fallback** — AI hooks return 'advisor offline' state on 503/500 · UI doesn't crash · V130 preserved · 4 fallback tests
- [ ] **V68-C-DONE-5 · case_002a APU bay metadata entry** — Whitelist includes case_002a with `case_kind=imported_user`+`gold_pending=true` · listable + disclaimer surfaces
- [ ] **V68-C-DONE-6 · E2E against real backend (extended)** — 41+ e2e PASS (+4 V68-C cases: physics + ai-review + ai-diagnose + case_002a)
- [ ] **V68-C-DONE-7 · Pillar 6 ≥98 + Pillar 7 ≥85 dual re-anchor + V68-D continued spike** — SCORING-FRAMEWORK.md updated + iter-2 WASM spike artifact

## Sub-DEC progress

- [x] **V68-C.1 · MaterialCard real-data wiring** — usePhysicsState hook + Step 3 surface · B141
- [ ] **V68-C.2 · ProposalCard AI advisor real route** — ai-review + ai-diagnose wired + 4 fallback tests
- [ ] **V68-C.3 · case_002a APU bay metadata entry** — whitelist YAML + gold_pending flag
- [ ] **V68-C.4 · E2E + V68-D iter-2 spike + close** — 4 new playwright + docker emsdk + close DEC
- (V68-D iter-2 spike inside .4 · spike-class · doesn't count as sub-DEC)

## Fleet criteria (further tightened vs V68-B)

| # | Agent | V68-B criteria | V68-C criteria |
|---|---|---|---|
| 1 | Code Quality | binary 100 | (unchanged) |
| 2 | Physics | mass_balance+corpus+bc | **+ whitelist count ≥11** (10 baseline + case_002a) |
| 3 | UX/Playability | ≥7 specs PASS | **≥9 specs PASS** for FULL flow=60 |
| 4 | Visualization | ≥4 viewport + ≥12 PNG | **≥4 viewport + ≥16 PNG** (+4 V68-C states) |
| 5 | Smoke | + backend HTTP /api/cases | **+ /physics + /ai-review + /ai-diagnose probes** (3 new) |
| 6 | Functional | 4/4 LANDED + 7/7 Done | (unchanged formula) |
| 7 | Stability | vitest flake | (unchanged) |

## Iteration tracker

| Iter | Date | min(7) | weighted | Lowest dim | Notes | Score report |
|---|---|---|---|---|---|---|
| 0 (V68-C baseline) | 2026-05-16 | TBD | TBD | TBD | charter LANDED · 0/4 sub-DECs · 0/7 Done · expected drops: viz (12<16 pro-rated), smoke (3 probes need verification), physics (whitelist 10<11) | `.planning/scores/V68-C_iter_0.md` |

## Reverse-stop log

- V132 `MUTATING_ROUTES` net diff > 0
- physics route 404s on non-imported cases (might affect whitelist-only cases)
- ai-review or ai-diagnose route returns 500 (backend logic break)
- case_002a integration breaks existing 10-case whitelist tests
- pixel-diff 0.01 threshold causes existing baselines to fail on rerun
- V68-D iter-2 spike reveals catastrophic blocker (docker daemon broken)

## Counter telemetry

- V68-C charter: B139
- V68-C.1: B140 estimated
- Subsequent: B141-B144 estimated

— V68-C ARC-GOAL · 2026-05-16
