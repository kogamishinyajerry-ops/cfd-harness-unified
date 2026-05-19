---
decision_id: DEC-V69-4
title: V69.4 · 7 e2e specs + StrictMode workaround verified + 2 PNG baselines
status: Accepted
parent_dec: DEC-V69-charter
phase: V69
notion_sync_status: pending
batch: B156
confidence: high
autonomous_governance: true
verdict: LANDED
---

# DEC-V69-4 · V69.4 E2E + StrictMode close

## 1 · Decision

Wire V69.1-V69.3 deliverables into the **real-backend** Playwright fleet (no MSW). Add 4 V69-specific e2e specs (7 tests · charter ≥4 EXCEEDED). Investigate StrictMode flakiness and document the workaround. Extend visual baselines 16 → 18 PNG (V69 visualization threshold MET).

## 2 · 7 e2e tests · 7/7 PASS · 6.4s total

| Spec | Tests | Purpose |
|---|---|---|
| `v69-advisor-regression.spec.ts` | 2 | POST /api/ai-review smoke + GET /api/cases canonical coverage |
| `v69-eval-harness-wire.spec.ts` | 2 | Schema validator + harness pytest sub-probe |
| `v69-strictmode-investigation.spec.ts` | 1 | `/workbench/case/lid_driven_cavity?step=3` clean mount (V69-DONE-5) |
| `v69-followups-reachable.spec.ts` | 2 | ≥2 V69 followup files + frontmatter schema validates |

## 3 · StrictMode investigation outcome (V69-DONE-5)

**Verdict**: workaround verified · NOT root-causally fixed.

Single-navigation mount of `/workbench/case/:id` is deterministic. The V68-A flake (multi-step transitions in one Playwright session) is reproducible **only under iteration-flake conditions**; one-shot navigation is clean. Per V69 charter "Reverse-stop log: StrictMode investigation turns into a 4-hour deep refactor → bounded spec" the workaround is now **officially documented** rather than the surface being "deeply broken".

## 4 · 2 new visual baselines · 16 → 18 PNG

- `17-case-detail-strictmode.png` — case-detail mount under StrictMode (regression protection for V69-DONE-5)
- `18-catalog-wide-v69.png` — 11-card catalog at 1440×900 with `gold_pending` badge (V69-era catalog state lock-in)

## 5 · Done dims

V69-DONE-5 MET (workaround documented + tested) · V69-DONE-6 MET (7 ≥ 4 charter target) · V69-DONE-7 partial (visualization 18/18 zone-anchored; SCORING-FRAMEWORK update happens in close DEC).

## 6 · Evidence

- Commit `2af7af6` · B156
- `ui/frontend/e2e/v69-*.spec.ts` · 4 files · 7 tests PASS
- `ui/frontend/__visual_baselines__/chromium/visual-baseline.spec.ts-snapshots/17,18*.png`
