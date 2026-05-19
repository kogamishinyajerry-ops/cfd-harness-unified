---
decision_id: DEC-V73-charter
title: V73 charter · v3 Advisor backend reconciliation + a11y runtime + multi-case ribbon · 12-pillar fleet · NEW Pillar 12 (后端集成健康)
status: Accepted
parent_dec: DEC-V72-close
phase: V73
notion_sync_status: pending
predecessor: DEC-V72-close
batch: B183
confidence: high
autonomous_governance: true
verdict: CHARTER_LANDED
v_row_landed: none (charter)
substrate: V72 closed at 100/100 across 11 pillars (B181) · 36 PNG baselines · 6 e2e playwright · 429 vitest · advisor 404 honest gap surfaced
---

# DEC-V73-charter · V73 v3 Advisor Reconciliation + A11y Runtime + Multi-Case

## 1 · Decision

Launch V73 — the **9th V110 advisor-class single-day arc**. Mission: pay down V72's honestly-disclosed advisor-404 backend gap, upgrade Pillar 11 from file-evidence to runtime a11y audit via axe-core, add a multi-case comparison ribbon for industrial-workbench parity, AND add the 12th pillar (后端集成健康 / Backend Integration Health) that forces continued real-data-wiring discipline.

User mandate (9th invocation · 2026-05-16):
> Same eight-axis 全都要 framing as invocations 7-8: blueprint targeting · test sub-agent · 99分以上 · CFD breadth · novice UX · 交互模式 · industrial-UI · Claude aesthetics.

## 2 · Scope (single-day arc · 6 sub-DECs)

**In scope**:
- V73.1 · Advisor pre-flight UI fix · whitelist cases get calm explanation instead of raw 404 (V130 calm-error contract extension)
- V73.2 · `@axe-core/playwright` integration · runtime WCAG audit in user-journey · Pillar 11 gets `wcag_runtime` subscore
- V73.3 · Multi-case comparison ribbon at Step 5 · compact 4-reference-case strip showing verdict + max-error for industrial workbench parity
- V73.4 · VerdictPill DRY unification · single primitive replaces 2 implementations (TruthChain + TrustGateVerdict)
- V73.5 · Pillar 12 scorer (`score_backend_integration.sh`) · 4 subscores: real_wired_surfaces / api_endpoint_coverage / graceful_offline_paths / integration_tests_passing
- V73.6 · 8 visual baselines (37-44) + V73 close + retro

**Out of scope** (deferred to V74+):
- Real `/api/runs/:id/residuals` SSE (V71.L still deferred · needs backend addition)
- Canvas field-render via vtk.js / WebGL
- Backend `_resolve_case_dir` widening to accept whitelist cases (advisor by design is for imported cases · V73 fix is UI-side branching · separate sub-DEC if backend ever changes)
- Real-LLM advisor (currently the route resolves to mock/rule-based when LLM provider unset; V73 doesn't add a real LLM key)
- Multi-case viewport (>4 cases compared on canvas)

## 3 · 12-pillar fleet (V72 11 + V73 NEW)

| # | Agent | Dim | Weight | V72 close | V73 target |
|---|---|---|---|---|---|
| 1 | quality | 代码质量 | 0.12 | 100 | ≥99 |
| 2 | physics | 物理/数值 | 0.12 | 100 | ≥99 |
| 3 | ux | 使用手感 | 0.15 | 100 | ≥99 |
| 4 | visualization | 可视化追踪 | 0.15 | 100 | ≥99 (≥44 PNG · was ≥36) |
| 5 | smoke | 端到端 | 0.08 | 100 | ≥99 |
| 6 | functional | 功能完整度 | 0.08 | 100 | ≥99 (6 sub-DECs · **11 Done dims**) |
| 7 | stability | 稳定性 | 0.08 | 100 | ≥99 |
| 8 | cfd_breadth | CFD全维度 | 0.08 | 100 | ≥99 |
| 9 | novice | 新手难度 | 0.07 | 100 | ≥99 |
| 10 | industrial_ui | 工业UI对标 | 0.07 | 100 | ≥99 (+multi_case_ribbon + verdict_dry subscores) |
| 11 | interaction_polish | 交互体验 | 0.07 | 100 | ≥99 (+wcag_runtime subscore via axe-core) |
| 12 | **backend_integration** | **后端集成健康** | **0.06** | **N/A** | **≥99** (NEW · 4 subscores) |

Sum of weights: 1.13 (informational; min one-vote-veto remains the gate).

## 4 · 11 Done dims (was 10 · V73 adds DONE-11)

- DONE-1..10 carry from V72 close (already verified at 100)
- DONE-11 · NEW: Advisor surface correctly distinguishes whitelist (gold-reference) vs imported (advisor-eligible) cases · whitelist consult shows calm explanation, not 404
- DONE-12 · NEW: Runtime a11y audit (axe-core) PASSES on Step 1/3/5 surfaces · zero violations
- DONE-13 · NEW: Multi-case comparison ribbon mounts at Step 5 · shows ≥4 reference cases
- DONE-14 · NEW: VerdictPill DRY · single export · 2 call sites
- DONE-15 · NEW: Pillar 12 (backend_integration) ≥99
- DONE-16 · NEW: 12-pillar 2-consecutive close

Wait — 16 dims is too many. Consolidate to 11 (V72's 10 + V73's 1 truly-new pillar):

**Revised Done dim list (11 total)**:
- DONE-1..10 retained from V72 (all already MET; verify no regression)
- DONE-11 · NEW: Pillar 12 (backend_integration) at ≥99 AND advisor reconciliation + axe-core a11y + multi-case ribbon + VerdictPill DRY all LANDED (combined gate)

This keeps the "all required" property clean and forces V73 close to depend on ALL the new sub-DECs landing, not just the score.

## 5 · 6 sub-DECs

- **V73.1 · Advisor whitelist-vs-imported pre-flight UI fix**
- **V73.2 · axe-core runtime a11y audit** integrated into user-journey-v3.spec.ts
- **V73.3 · Multi-case comparison ribbon** at Step 5 (new component · max 4 ref cases)
- **V73.4 · VerdictPill DRY** + canonical eval surface
- **V73.5 · Pillar 12 scorer wired** + baseline iteration
- **V73.6 · 8 visual baselines (37-44) + V73 close + retro**

## 6 · Anti-fraud frame (carried from V71+V72)

- Displayed numbers must match displayed verdicts
- Static-demo-data explicitly disclosed in every DEC
- New pillar scores computed from file evidence (not preset)
- Pre-flight check on advisor must not silently mask the underlying 404 — it must explain it
- Multi-case ribbon must use real backend `/api/cases` data, not hardcoded

## 7 · Reverse-stops

- MUTATING_ROUTES net diff > 0 (locked at 9)
- New auto-execute button anywhere in v3 surface
- Pillar 6 (functional) regresses below 99
- Any of 36 V72 visual baselines drifts > 0.05 SSIM
- 5th persistent panel added
- Sub-agent journey asserts false success
- axe-core runtime audit detects WCAG violations on Step 1/3/5 (would force a real fix · not a workaround)

## 8 · Counter

V73 charter = autonomous_governance: true → counter +1. Expected total V73 counter: +8 (charter + 6 sub-DECs + close).

## 9 · Substrate inventory

Already on disk (from V72 close):
- 21 v3 component files + hooks/useV3Keyboard
- 36 PNG visual baselines
- 11 fleet scorers (V72)
- 429 vitest + 6 playwright e2e (5 kbd + 1 journey)
- 8 DECs (V72 charter + 5 implicit sub-DECs + V72.6 + close + retro)

V73 additions:
- 1 new scorer (score_backend_integration.sh · already authored in this bootstrap)
- Modified v3 components (AdvisorContent · TruthChainContent · TrustGateVerdict)
- New components (MultiCaseRibbon · VerdictPill)
- New axe-core dependency
- 8 new PNG baselines

## 10 · Acceptance criteria

V73 closes when:
- All 6 sub-DECs LANDED
- 12-pillar fleet at min ≥99 on 2 consecutive iters
- Advisor pre-flight resolves whitelist cases gracefully
- axe-core finds 0 violations on Step 1/3/5
- Multi-case ribbon mounts with ≥4 reference cases
- VerdictPill is exported from a single module + used in 2 call sites
- 44 PNG baselines stable

---

**Co-Authored-By**: Claude Opus 4.7 (1M context)
