# ARC-GOAL · V73 v3 Advisor Reconciliation + A11y Runtime + Multi-Case + Backend-Integration Pillar · **ACTIVE 2026-05-16**

> **Charter**: `.planning/decisions/2026-05-16_v73_charter_dec.md` (Accepted B183)
> **Predecessor**: DEC-V72-close (11-pillar 100/100 · B181)
> **NEW Pillar 12**: 后端集成健康 (Backend Integration Health) · 4 subscores
> **Target**: 12-pillar min ≥99 · 2-consecutive close gate

## North Star

Engineer opens `/workbench/v3/case/lid_driven_cavity?step=3`, clicks Advisor tab → instead of a raw "Error · 404 case_not_found" the surface shows: **"AI Advisor reviews user-imported cases against the corpus. This whitelist case has its existing validation under the TruthChain tab →"**. At Step 5, a multi-case ribbon shows this case vs 4 canonical references side-by-side. The whole shell passes an axe-core WCAG audit with zero violations.

## Done dim checklist (11 dims · simplified · all required)

- [x] **V72-DONE-1..10 carry** — verify no regression on close-confirm iter
- [x] **V73-DONE-11 · Composite** — Pillar 12 = **100** AND advisor reconciliation LANDED (V73.1) AND axe-core **0 violations** on Step 1/3/5 (V73.2) AND multi-case ribbon mounts (V73.3) AND VerdictPill DRY (V73.4) AND Step5Inspector live `/completeness` (V73.5)

## Sub-DEC progress

- [x] **V73.1 · Advisor pre-flight UI fix** — whitelist case shows explanation, not 404 (LANDED B184 · `advisor-whitelist-explanation` testid · 430/430)
- [x] **V73.2 · axe-core runtime a11y audit** — `@axe-core/playwright` integrated · Step 1/3/5 PASS 0 violations (LANDED B185 · 4 substrate fixes: contrast / role / tablist / id)
- [x] **V73.3 · Multi-case comparison ribbon** — Step 5 strip with 4 references (LANDED B186 · `multi-case-ribbon` testid · real /api/cases wire)
- [x] **V73.4 · VerdictPill DRY** — single primitive · 2 call sites (LANDED B187 · `verdict-pill` testid · normalizeVerdict)
- [ ] **V73.5 · Pillar 12 scorer wired** — `score_backend_integration.sh` already authored
- [x] **V73.6 · 8 visual baselines (37-44) + close + retro** (LANDED B189 · 44/44 PASS · close DEC + retro written · iter-3 100/100)

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
| 0 (V73 baseline) | 2026-05-16 | 80 | 99.32 | interaction_polish (wcag_runtime missing) | charter LANDED · pillar 12 = 96 substrate · 11 carry V72 100 | V73_iter_0.md |
| 1 | 2026-05-17 | **100** | 109.32 | (all 100) | V73.1+2+3+4+5 LANDED · CLOSE_ELIGIBLE | V73_iter_1.md |
| 2 | 2026-05-17 | **100** | 109.32 | (all 100) | stability re-confirm · CLOSE_CONFIRMED (2-consec) | V73_iter_2.md |
| 3 | 2026-05-17 | **100** | 109.32 | (all 100) | + 8 visual baselines · 44/44 PASS · 3-consec margin | V73_iter_3.md |

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
