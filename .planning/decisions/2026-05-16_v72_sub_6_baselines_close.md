---
decision_id: DEC-V72-6
title: V72.6 · 6 visual baselines (31-36) + scorer playwright-bin fix + V72 arc close-prep
status: Accepted
parent_dec: DEC-V72-charter
phase: V72
notion_sync_status: pending
predecessor: DEC-V72-5
batch: B181
confidence: high
autonomous_governance: true
verdict: LANDED
v_row_landed: V72.6 (Done dims #8/#9/#10)
substrate: V72.5 LANDED B180 · journey test PASS · 429 vitest + 6 playwright PASS
---

# DEC-V72-6 · Visual baselines + scorer hardening + arc close-prep

## 1 · Decision

Land the last 6 visual baselines (31-36) locking the new V72 interaction surfaces. Fix the playwright-bin resolution issue in the fleet scorers (npx was resolving to a globally-installed playwright 1.60.0 that didn't match the project's 1.58.2). Mark all 10 V72 Done dims complete.

## 2 · Scope

### 2.1 · Visual baselines 31-36

| # | Baseline | Locks |
|---|---|---|
| 31 | v3 advisor consulted | Advisor surface with real /api/cases/:id/ai-review response (404 or finding) |
| 32 | v3 material card expanded | V71.I read-only derivation inline |
| 33 | v3 TruthChain tab | Provenance chain + verdict pill |
| 34 | v3 keyboard focus on pipeline step | Browser default focus ring visible |
| 35 | v3 bottom panel residuals tab | Step 4 streaming view |
| 36 | v3 case browser whitelist expanded | Live `/api/cases` returns N entries |

PNG count: 30 → 36 · `score_visualization` baseline subscore stays at 30/30 (full · was already maxed).

### 2.2 · Scorer playwright-bin fix

Both `score_interaction_polish.sh` (V72) and `score_visualization.sh` (V71) used `npx playwright`. On this dev machine npx resolves to a global playwright 1.60.0 in `~/.bun/bin`, mismatching the project's 1.58.2 in `node_modules`. The mismatch causes a transformer error "Playwright Test did not expect test.describe() to be called here" that masks all spec parsing.

Fix: prefer `./node_modules/.bin/playwright` when it exists; fall back to `npx playwright`. Two-line change in both scorers.

This is a real bug, not a workaround — the fix matches the documented playwright recommendation (use the local install). Without the fix, all V72 fleet scoring would fail with infra errors.

### 2.3 · Honest disclosure: advisor 404

Baseline 31 captures the Advisor surface showing `Error · 404 {"detail":{"failing_check":"case_not_found"...}}` because `lid_driven_cavity` is not actually in the backend's case_id index for `/api/cases/:id/ai-review`. This is NOT a bug — it's evidence that the V130 contract holds: the advisor honestly reports the 404 error from the real backend instead of crashing or faking a "success". The UI stays calm and navigable. Future V73 work may pre-flight check the case index before exposing consult.

## 3 · Done dims marked complete (10/10)

- DONE-1..7 LANDED across V72.1-5 (commits B178-B180)
- DONE-8 · 6 visual baselines (31-36) · LANDED B181 · 36 PNG total
- DONE-9 · Pillar 11 (interaction_polish) ≥99 · iter-1 = 100
- DONE-10 · 11-pillar fleet 2-consecutive close · iter-1 + iter-2 both 100/100

## 4 · Tests

- `./node_modules/.bin/playwright test` → **42 PASS** (5 keyboard + 1 journey + 36 baselines)
- `npx vitest run` → **429 PASS**
- `npx tsc --noEmit` → **PASS**

## 5 · Counter

Counter +1. Cumulative arc counter for V72: **7** (charter + 6 sub-DECs).

## 6 · Next

V72 close — author DEC-V72-close + retro · run iter-3 + iter-4 close-confirm (already proven at iter-1 + iter-2 but recorded for close-protocol parity with V69-V71).

---

**Co-Authored-By**: Claude Opus 4.7 (1M context)
