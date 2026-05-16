# ARC-GOAL · V67-C Product Workbench UI Build-out · **ACTIVE 2026-05-16**

> **Charter**: `.planning/decisions/2026-05-16_v67c_charter_dec.md` (Accepted B117 · 2026-05-16)
> **Predecessor**: DEC-V67-D-extension (B116 · 75.30 weighted)
> **Target**: Pillar 6 Engineer UX 55→90+ · weighted +3.5 ceiling · fleet min(7) ≥99
> **User mandate**: 全权开发 · 7-agent testing fleet · 绝对诚实评分 · 迭代到 ≥99 分

## North Star (charter §3 verbatim)

> "工程师打开 `/workbench/case/{id}`，5-step spine 视觉清晰可点，TopBar 6 字段全可见，Engineer Control Rail 整合到位，Viewport mode 流畅切换，AI panel 严格 advisory-only，30 分钟从 Import 走到 Results 不卡顿不困惑。"

## Done dim checklist (8 dims · all required for V67-C close)

- [x] **V67-C-DONE-1 · TopBar 6-field information density** — case · OF truth · TrustGate · LLM offline · Audit % · AI=advisor (all 6 visible + tested) · evidence: `TopBar.test.tsx` 9/9 PASS · `e2e/topbar.spec.ts` bootstrap · TopBar.tsx 50→180 LOC chip-based 6-field layout
- [x] **V67-C-DONE-2 · StatusStrip live indicators** — 4 fields (lastAction · progress + step status · trustState · validation) · evidence: `StatusStrip.test.tsx` 11/11 PASS · StatusStrip.tsx 30→130 LOC
- [x] **V67-C-DONE-3 · Engineer Control Rail integrated** — Beginner/Power toggle in TaskPanel header (xs · 14 tests PASS) · CompletenessCard top of scroll region (existing) · BeginnerPowerProvider wired at App.tsx root · localStorage + cross-tab sync · evidence: `BeginnerPowerToggle.test.tsx` 14/14 PASS · step-body advanced-disclosure adoption deferred to V67-C.3.1 follow-on
- [ ] **V67-C-DONE-4 · 5-step spine visual polish** — step status icons (✓/●/○) · transition animations · Apple-tier consistency · evidence: visual diff baseline + Playwright transition test
- [ ] **V67-C-DONE-5 · Viewport mode switching** — geometry/mesh/BC/field/residuals/report-grid · ≤200ms transition · evidence: `Viewport.test.tsx` + `e2e/viewport-mode.spec.ts`
- [x] **V67-C-DONE-6 · AI panel strict advisory-only** — 0 mutation patterns in AI panels · MUTATING_ROUTES = 9 (baseline) · KNOWN_MUTATION_FUNCTIONS = 12 (baseline) · evidence: `scripts/governance/v67c_fleet/audit_ai_advisory.sh` VERDICT PASS · audit report `.planning/scores/V67-C_advisory_audit_b121.md`
- [ ] **V67-C-DONE-7 · Truth Chain visibility across 5 steps** — TopBar "OF truth" updates · audit % rolls forward · TrustGate state surfaces · evidence: `e2e/truth-chain.spec.ts` full-flow
- [ ] **V67-C-DONE-8 · Pillar 6 ≥90 re-anchor** — scoring framework v1.0 Pillar 6 anchor language matches `90-100` zone · evidence: V67-C close DEC §10

## Sub-DEC progress

- [x] **V67-C.0 · Bootstrap** (sub-DEC) — npm install + ESLint 9 flat config + 3 fleet script fixes + ARC-GOAL · commit `19253bf` · B118
- [x] **V67-C.1 · TopBar 6-field upgrade** — Done dim #1 MET · TopBar.tsx 50→180 LOC + TopBar.test.tsx 9 tests + Playwright bootstrap (`playwright.config.ts` + `e2e/topbar.spec.ts`) · B119
- [x] **V67-C.2 · StatusStrip live indicators** — Done dim #2 MET · StatusStrip.tsx 30→130 LOC + 11 tests · B120
- [x] **V67-C.3 · Engineer Control Rail (partial)** — BeginnerPowerContext + Toggle + App Provider wire + TaskPanel header render + 14 tests · B122 · step-body adoption → V67-C.3.1
- [ ] **V67-C.4 · 5-step spine visual polish** — Done dim #4 · ~150 prod + 100 test + visual baseline
- [ ] **V67-C.5 · Viewport mode switching** — Done dim #5 · ~180 prod + 140 test
- [x] **V67-C.6 · AI panel advisory-only audit** — Done dim #6 MET · `audit_ai_advisory.sh` 75 LOC · 4/4 invariants PASS · B121 (Truth-chain e2e deferred to V67-C.6.1)

## Iteration tracker

| Iter | Date | min(7) | Lowest dim | Notes | Score report |
|---|---|---|---|---|---|
| 0 (baseline) | 2026-05-16 | 0 | quality+ux+visualization+smoke+functional all 0 | npm install missing · fleet bugs discovered | `.planning/scores/V67-C_iter_0.md` |

## Reverse-stop log (must surface to user if any below trigger)

- V132 `MUTATING_ROUTES` net diff > 0
- Beginner mode breaks step body rendering
- Persona dogfood drift (LDC-only testing)
- Plateau over 5 iter with max-min < 5
- Codex round cap=3 on any 1-sync-trigger PR

(none triggered yet · iter 0 baseline)

## Counter telemetry

- V67-C charter: B117
- V67-C.0 bootstrap: B118 (this commit landing chain)
- Subsequent batches: B119-B130 estimated

— V67-C ARC-GOAL · 2026-05-16
