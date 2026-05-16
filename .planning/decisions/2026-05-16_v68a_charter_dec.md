---
decision_id: DEC-V68-A-charter
title: V68-A "Workbench Depth & Real-Usability" arc charter · upgrade V67-C SCAFFOLDING-MET dims to FULL-MET · Pillar 6 90→95 · ≥99 fleet mandate
status: Accepted
parent_dec: DEC-V67-C-close
phase: V68-A
notion_sync_status: pending
predecessor: DEC-V67-C-close
batch: B126
confidence: high
autonomous_governance: true
verdict: ARC_CHARTER_ACCEPTED
v_row_landed: none (charter)
substrate: V67-C close DEC §9 follow-on queue (V67-C.3.1/.4.1/.5.1/.6.1/.7.1) consolidated into V68-A
---

# DEC-V68-A-charter · V68-A "Workbench Depth & Real-Usability"

## 1 · Decision

Launch successor arc **V68-A "Workbench Depth & Real-Usability"** consolidating 5 V67-C follow-on sub-DECs (.3.1/.4.1/.5.1/.6.1/.7.1) plus MSW backend mocking and end-to-end flow. **Upgrade V67-C's 4 SCAFFOLDING-MET Done dims (4/5/7 + step-body Power) to FULL-MET** via real behaviors (not just scaffolding).

User mandate (continuation of V67-C): *"专门测试子 agent · 真实测评 · 使用手感 · 可视化追踪 · 99 分以上"*. V68-A makes "使用手感" + "可视化追踪" verifiable through MSW-backed real flows (not just spec presence).

## 2 · Rationale · why depth now

V67-C closed at min(7)=100 / weighted=100 BUT 4 of 8 Done dims were SCAFFOLDING-MET (spec files present + structure in place, but no real backend-driven flow). User's stated emphasis on "真实测评 · 使用手感" demands the next step: **upgrade scaffolding → real behaviors**.

V68-A makes the difference between:
- V67-C state: "workbench-index loads · TopBar testids present" (scaffolding)
- V68-A target: "navigate Import→Mesh→BC→Solve→Results with TopBar audit% rolling forward · TrustGate flipping per step · viewport mode switching geometry/mesh/BC/field/residuals/report-grid with mocked data" (real flow)

Pillar 6 ceiling: 90 → **95** (+5 raw · +0.5 weighted) is small per-pillar but **delivers the actual UX value** charter committed to.

## 3 · North Star

> "工程师打开 `/workbench/case/<demo>`，5-step pipeline 全程可达（MSW mock backend）· TopBar 4 字段实时更新（truthSource/trustGate/auditPct/llmOffline）· Viewport mode 6 状态切换（geometry/mesh/BC/field/residuals/report-grid）· Beginner/Power toggle 实际控制 5 step body 高级区显隐 · 8 个 canonical UI 状态有 pixel-diff baseline · 全流程 Playwright e2e PASS"

## 4 · Done Definition (7 dims · all required for V68-A close)

| # | Done dim | Threshold | Verification |
|---|---|---|---|
| 1 | MSW backend mocking | /api/* endpoints mocked at network layer · /workbench/case/{id} renders without real backend | `src/mocks/handlers.ts` + Playwright + verified via SPA render |
| 2 | TopBar real data wiring | 4 dynamic fields (truthSource/trustGate/auditPct/llmOffline) feed from useCaseStatus hook | `useCaseStatus.test.ts` + visual snapshot diff < 0.1% |
| 3 | Step body Power-mode adoption | 5 step bodies gate advanced section behind isPower · Beginner shows preset · Power reveals advanced | 5 step body tests · 1 e2e test toggling mode mid-flow |
| 4 | Viewport mode dispatcher | 6 modes (geometry/mesh-wireframe/BC-faces/field-slice/residuals/report-grid) · mode-state surfaces in viewport · ≤200ms switch | viewport mode dispatcher test + e2e test |
| 5 | Visual snapshot baseline | 8 canonical UI states · `toHaveScreenshot()` baseline files committed · diff < 0.1% on stable runs | `__visual_baselines__/chromium/*-snapshots/` ≥8 PNG files |
| 6 | End-to-end 5-step flow | Import→Mesh→BC→Solve→Results · all 5 steps reachable · CompletenessCard updates · TopBar trustGate progresses | `e2e/full-flow.spec.ts` · ≥5 step navigations |
| 7 | Pillar 6 ≥95 re-anchor | scoring framework v1.0 Pillar 6 anchor language matches `95-100` zone | V68-A close DEC §10 |

**Close gate**: 7/7 Done dims MET via FULL delivery (no SCAFFOLDING-MET discount) + fleet min(7) ≥99 for 2 consecutive iter.

## 5 · Sub-DEC seeds (5 sub-DECs · serial sequencing)

### V68-A.1 · MSW bootstrap
- npm install msw + create handlers + service worker
- 4 mocked endpoints minimum
- LOC est: ~120 prod + 40 test
- Confidence: med

### V68-A.2 · TopBar real data wiring
- useCaseStatus React Query hook + StepPanelShell call-site update
- Wire 4 TopBar fields from hook
- LOC est: ~150 prod + 80 test
- Confidence: med

### V68-A.3 · Step body Power-mode disclosure (5 step bodies)
- Step1Import/Step2Mesh/Step3SetupBC/Step4SolveRun/Step5ResultsView each gated section
- LOC est: ~200 prod (40 × 5) + 100 test
- Confidence: med

### V68-A.4 · Viewport mode dispatcher + visual baseline
- 6-mode dispatcher in StepPanelShell wired to step body active mode
- Visual snapshot baseline generation (`--update-snapshots`)
- LOC est: ~150 prod + 80 test + 8 PNG baselines
- Confidence: med

### V68-A.5 · End-to-end 5-step flow + close
- Full Playwright e2e Import→Mesh→BC→Solve→Results
- Mode toggle + CompletenessCard + TopBar progression verified
- LOC est: ~200 test (mostly e2e specs)
- Confidence: med

## 6 · 7-agent fleet (v68a_fleet/ clone with tighter criteria)

Reuse fleet pattern from V67-C with stricter thresholds:

| # | Agent | V67-C criteria | V68-A criteria (tighter) |
|---|---|---|---|
| 1 Code Quality | typecheck+lint+vitest binary | (unchanged) |
| 2 Physics | mass_balance+corpus+bc_routes | (unchanged) |
| 3 UX/Playability | spec pass ratio | **≥5 specs PASS** required for 100 |
| 4 Visualization | viewport+truth specs · baseline dir exists | **≥4 viewport-mode specs PASS** + **≥6 snapshot PNG files exist** |
| 5 Smoke | backend import + build + tc + lint | (unchanged) |
| 6 Functional | LANDED + Done dim count | thresholds: 5/5 LANDED + 7/7 Done |
| 7 Stability | vitest flake | (unchanged) |

Score formulas unchanged; thresholds tightened to require real coverage.

## 7 · Iteration loop (mandatory · same as V67-C)

Identical iteration loop as V67-C charter §7. Reverse-stop triggers (charter §11) unchanged.

## 8 · v2.3 governance compliance

- DEC scope: charter (governance-rule-change-adjacent · 5 sub-DECs · UI work)
- Codex 1-sync-trigger: NOT applicable (UI + frontend tests + mocking · no security boundary)
- Kogami opt-in: NOT invoked (user autonomous mandate continues)
- Confidence: high (charter)
- Counter: B126 autonomous_governance=true · +1

## 9 · 4Q gate baseline answers

| Q | A | Justification |
|---|---|---|
| LLM offline · workbench full pipeline | ✓ YES | MSW mock + frontend rendering · no LLM dependency; AI panel still advisory-only |
| Artifacts produced | ✓ YES | MSW handlers + e2e specs + snapshots + sub-DECs + iter scores |
| TrustGate / completeness / audit trail | ✓ YES | TopBar `trustGate` dynamic · audit% rolls forward · CompletenessCard updates |
| AI advisory-only · no mutating route | ✓ YES | V132 MUTATING_ROUTES baseline still 9 · audit re-runs each iter |

## 10 · Out of scope (explicit non-goals)

- **NOT** real backend integration (MSW only · real backend wiring is post-V68 territory)
- **NOT** real OpenFOAM solver invocation in browser tests (mocked)
- **NOT** touching Pillar 1/3/4/5/7 (frozen — those advance in separate arcs)
- **NOT** introducing LLM dependency
- **NOT** adding new mutating routes (V132 baseline locked)

## 11 · Predicted trajectory

- iter 0 (baseline): min(7)=100, weighted=100 (V67-C close state)
- iter 1 (V68-A.1 MSW + fleet retune): expected min still 100 if fleet pre-tuned; **functional drops** because fleet now requires LANDED V68-A sub-DECs (0/5) + Done dims (0/7) = functional 0
- iter 2-5: sub-DEC LANDED + Done dim MET incrementally
- iter 6+: ≥99 for 2 consecutive

V68-A may temporarily REGRESS functional score in iter 1 because criteria tighten. This is **honest** — V67-C's 100/100 was against V67-C charter criteria, not V68-A's.

— Claude Code (Opus 4.7 1M) · B126 · V68-A charter · 2026-05-16
