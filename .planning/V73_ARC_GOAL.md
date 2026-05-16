# ARC-GOAL · V73 v3 Advisor Reconciliation + A11y Runtime + Multi-Case + Backend-Integration Pillar · **ACTIVE 2026-05-16**

> **Charter**: `.planning/decisions/2026-05-16_v73_charter_dec.md` (Accepted B183)
> **Predecessor**: DEC-V72-close (11-pillar 100/100 · B181)
> **NEW Pillar 12**: 后端集成健康 (Backend Integration Health) · 4 subscores
> **Target**: 12-pillar min ≥99 · 2-consecutive close gate

## North Star

Engineer opens `/workbench/v3/case/lid_driven_cavity?step=3`, clicks Advisor tab → instead of a raw "Error · 404 case_not_found" the surface shows: **"AI Advisor reviews user-imported cases against the corpus. This whitelist case has its existing validation under the TruthChain tab →"**. At Step 5, a multi-case ribbon shows this case vs 4 canonical references side-by-side. The whole shell passes an axe-core WCAG audit with zero violations.

## Done dim checklist (11 dims · simplified · all required)

- [x] **V72-DONE-1..10 carry** — verify no regression on close-confirm iter
- [ ] **V73-DONE-11 · Composite** — Pillar 12 ≥99 AND advisor reconciliation LANDED AND axe-core 0 violations AND multi-case ribbon mounts AND VerdictPill DRY

## Sub-DEC progress

- [x] **V73.1 · Advisor pre-flight UI fix** — whitelist case shows explanation, not 404 (LANDED B184 · `advisor-whitelist-explanation` testid · 430/430)
- [ ] **V73.2 · axe-core runtime a11y audit** — `@axe-core/playwright` integrated · Step 1/3/5 PASS 0 violations
- [ ] **V73.3 · Multi-case comparison ribbon** — Step 5 strip with 4 references
- [ ] **V73.4 · VerdictPill DRY** — single primitive · 2 call sites
- [ ] **V73.5 · Pillar 12 scorer wired** — `score_backend_integration.sh` already authored
- [ ] **V73.6 · 8 visual baselines (37-44) + close + retro**

## Fleet criteria (12 pillars · V73 NEW Pillar 12)

| # | Agent | V72 close | V73 |
|---|---|---|---|
| 1-9 | (carry) | 100 | unchanged |
| 4 | Visualization | 100 (36 PNG) | **≥44 PNG** |
| 10 | Industrial-UI | 100 | **+multi_case_ribbon + verdict_dry subscores** |
| 11 | Interaction-Polish | 100 | **+wcag_runtime subscore via axe-core** |
| 12 | **Backend-Integration** | **N/A** | **≥99** (NEW · 4 subscores) |

## Iteration tracker

| Iter | Date | min(12) | weighted | Lowest dim | Notes | Score report |
|---|---|---|---|---|---|---|
| 0 (V73 baseline) | 2026-05-16 | TBD | TBD | TBD | charter LANDED · pillar 12 NEW · 11 of 12 carry V72 100 | TBD |

## Reverse-stop log

- V132 MUTATING_ROUTES net diff > 0
- Any auto-execute button in any v3 surface
- Pillar 6 regression below 99
- Any of 36 V72 baselines drifts > 0.05 SSIM
- axe-core finds WCAG violations on Step 1/3/5
- Multi-case ribbon contains hardcoded data (must use real `/api/cases`)
- VerdictPill leaves duplicate implementations behind

## Counter telemetry

- V73 charter: B183
- V73.1: B184 estimated
- Subsequent: B185-B189 estimated

— V73 ARC-GOAL · 2026-05-16
