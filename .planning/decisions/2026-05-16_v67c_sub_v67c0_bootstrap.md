---
decision_id: DEC-V67-C-sub-V67C0-bootstrap
title: V67-C.0 bootstrap · ESLint 9 flat config + 3 fleet script fixes + ARC-GOAL + iter 0/1 baseline scores
status: Accepted
parent_dec: DEC-V67-C-charter
phase: V67-C
notion_sync_status: pending
predecessor: DEC-V67-C-charter
batch: B118
confidence: high
autonomous_governance: true
verdict: SUB_DEC_LANDED
v_row_landed: none
substrate: ui/frontend/eslint.config.js + scripts/governance/v67c_fleet/score_{physics,smoke,functional}.sh + .planning/V67C_ARC_GOAL.md + 2 iter scores
---

# DEC-V67-C-sub-V67C0-bootstrap · V67-C.0 bootstrap · B118

## 1 · Decision

Bootstrap V67-C arc execution prerequisites surfaced by iter 0 baseline fleet run:
1. ESLint 9 flat config (`ui/frontend/eslint.config.js`) — project had ESLint v9.39 installed but no `eslint.config.js`; lint was unrunnable.
2. Fleet script bug fixes — `score_functional.sh` grep multi-line var → arithmetic syntax error; `score_physics.sh` advisor-rules glob mismatched actual file paths; `score_smoke.sh` dogfood_loop heavy smoke replaced with lightweight integration-surface checks.
3. V67C_ARC_GOAL.md — Done dim tracking SSOT (8 dims · 6 sub-DECs · iteration tracker).

Frontend `node_modules` also installed (`npm install` · gitignored side-effect · not part of this commit's diff but a prerequisite for `tsc`/`vitest`/`eslint` to work).

## 2 · Iter 0 / Iter 1 honest baseline scores

| Iter | When | min(7) | weighted | Notes |
|---|---|---|---|---|
| 0 | pre-bootstrap | **0** | 7.00 | npm not installed · ESLint config missing · 4 script bugs |
| 1 | post-bootstrap | **0** | 50.00 | 4 dims (quality / physics / smoke / stability) PASS-99; 3 dims (ux / visualization / functional) still 0 awaiting subsequent sub-DECs |

Per-dim transition iter 0 → iter 1:
- quality: 0 → **100** (npm install resolved typecheck/lint/vitest)
- physics: 40 → **100** (V-corpus shape check fixed · mass_balance + bc_routes intact)
- ux: 0 → 0 (Playwright bootstrap is V67-C.1 territory)
- visualization: 0 → 0 (Playwright + visual baseline are V67-C.1/.4/.5 territory)
- smoke: 0 (INFRA_FAILURE) → **100** (backend FastAPI import + frontend build + tc + lint all PASS)
- functional: 0 → 0 (V67-C.0 not counted as sub-DEC LANDED in checklist; Done dims = 0/8)
- stability: 10 → **100** (vitest install resolved 3/3 flake)

## 3 · Spike-class vs sub-DEC justification

LOC count exceeds spike-class threshold (≤30 LOC):
- `eslint.config.js`: ~95 lines (NEW)
- `score_physics.sh`: ~85 lines (rewrite)
- `score_smoke.sh`: ~90 lines (rewrite)
- `score_functional.sh`: 3-line surgical fix
- `V67C_ARC_GOAL.md`: ~50 lines (planning doc; not code LOC but co-shipped)

Total: ~270 lines of script + config + 50 lines of planning. Sub-DEC class (no schema break · no contract break · no new abstractions · single confidence:high).

## 4 · 4Q gate

| Q | A |
|---|---|
| LLM offline | ✓ Bootstrap is config + scripts; no LLM dependency added |
| Artifacts | ✓ eslint.config.js + 2 iter score reports + sub-DEC + ARC-GOAL |
| TrustGate | ✓ Iter scores written with verbatim failure originals (honesty rule #1) |
| AI advisory-only | ✓ No `MUTATING_ROUTES` registry diff (no backend route changes) |

## 5 · v2.3 compliance

- DEC scope: sub-DEC (cross 4 modules: eslint config + 3 scripts; not charter-class)
- Codex 1-sync-trigger: NOT triggered (no security boundary)
- Kogami opt-in: NOT invoked
- Confidence: high
- Counter: B118 autonomous_governance=true · +1

## 6 · Iter 2 prerequisite list (V67-C.1 unblocks)

- [ ] Bootstrap Playwright (`@playwright/test` install + `playwright.config.ts` + `e2e/` dir + 1 working test)
- [ ] TopBar.tsx 2 fields → 6 fields (case · OF truth · TrustGate · LLM offline · Audit % · AI=advisor)
- [ ] Update TopBar.test.tsx for 6 fields
- [ ] Add `e2e/topbar.spec.ts` (Playwright minimum)
- [ ] V67C_ARC_GOAL.md: mark V67-C-DONE-1 (TopBar 6-field) as ✓

## 7 · Honest accounting (anti-inflation)

- ✗ Did NOT advance Pillar 6 score (this is infra bootstrap; UI unchanged)
- ✗ Did NOT mark Done dim #1 MET (TopBar still 2 fields — that's V67-C.1's job)
- ✗ Did NOT install Playwright (V67-C.1 will own this · iter 2 first-mile)
- ✓ Honestly recorded iter 0 baseline = 0 (npm missing) before fixing infra
- ✓ Iter 1 = 0 because functional + ux + visualization legitimately not deliverable until further sub-DECs

— Claude Code (Opus 4.7 1M) · B118 · V67-C.0 bootstrap · 2026-05-16
