# M3.7 milestone close · workbench chrome de-hardcoding (B7) · 2026-05-25

> Parent: DEC-V61-202 (Workbench Dynamic-Guided) M-track
> Cycles: 1 (chrome blueprint gating fix)
> Closing commit: `272e02b` fix(workbench): M3.7 cycle 1
> Deliverable: chrome now reflects case identity at all 6 workbench steps

## TL;DR

The M3.6 real-CAD demo exposed B7 — workbench chrome (top bar / left tree / KpiStrip) showing "项目 APU 航通风 · 案例 R-042 · R-042_ApuVent · 17 零件 / 2 待采纳 / 2.0 包裹尺寸 / 18.76 流体域体积" regardless of actual case_id. Root cause: 3 components (TopBarV4 / LeftRailV4 / KpiStripV4) gated their blueprint-vs-case path on `activeStep === "geometry"` alone, ignoring caseId. 9 LOC functional change across 3 files closed it. Cross-step verification on `circular_cylinder_wake` confirmed all chrome elements now case-driven; 79/79 V4 unit tests still pass.

## Counter table

| Cycle | Goal | LOC delta | Tests | Codex round | Confidence | Outcome |
|---|---|---|---|---|---|---|
| 1 | Gate blueprint mode on absence of caseId | +19 -4 (9 LOC functional + 13 LOC comments/inline rationale) | 79 V4 unit tests PASS + 4 cross-step screenshot spot-checks | 0 | high | All chrome case-driven · 0 regressions · 0 post-R3 defects |

`autonomous_governance_counter_v61` +1.

## What worked

- **Subagent survey paid off immediately**: spawned `Explore` subagent with focused prompt on the V4 shell. Returned inventory + data path + smallest-impact plan in ~5k tokens. Three target files + line numbers identified without me having to grep manually. Saved an estimated 8-10 minutes of exploration.
- **Spike-class scope honored**: 9 LOC functional change spread over 3 files, plus inline rationale comments. No DEC, no Codex, no Kogami. v2.3 round-1 loosen pattern continues to fit perfectly.
- **Cross-step spot-checks caught zero regressions**: probed circular_cylinder_wake at geometry / mesh / physics / boundary. All show case-driven chrome. No bleed-through of blueprint mode into non-geometry steps (which they weren't using anyway, but always good to verify).
- **Visual spot-check workflow self-reinforcing**: M3.6 instituted `--use-gl=swiftshader` on the spot-check tool; M3.7 used the same tool to validate. The methodology compounds.
- **One-cycle close**: B7 was a focused gating bug. Cycle 1 nailed it. No need for iterations.

## What hurt / blind spots

- **B7 was visible in EVERY screenshot since M3.4**: every spot-check that closed M3.4 / M3.5 / M3.6 had "R-042_ApuVent" / "APU 航通风" / "17 零件" in plain sight. None of the cycle closures flagged it. The pattern was so consistent that the eye tuned it out. Reminder: visual spot-check is necessary but not sufficient — without a checklist of "what SHOULD be case-specific", static-mock pollution can hide for cycles.
- **No backlog finding template existed**: B7 was filed in the M3.6 retro free-form. Future cosmetic findings should land in `.planning/backlog/` with a uniform schema (severity / repro / fix-class hypothesis) so they aggregate cleanly.
- **Three components needed the same fix**: TopBarV4 / LeftRailV4 / KpiStripV4 each had their own copy of `activeStep === "geometry" ? null : caseId`. DRY-able into a shared `useEffectiveCaseId(caseId, activeStep)` hook. Deferred — not blocking, would be a janitorial cycle.

## v2.3 governance check

| Rule | Cycle 1 |
|---|---|
| Spike-class scope (≤30 LOC functional) | ✅ 9 LOC functional |
| Codex review trigger hit? | ❌ no security · no signing · no schema · pure UI gating |
| Kogami invoked? | ❌ no charter / no governance-rule-change |
| Notion sync? | not yet (session-end batch · only Accepted DECs) |
| Surface-scan mandatory? | optional · touched 3 V4 shell files that are owners of their own blueprint gates |
| Counter charge? | +1 (autonomous) |
| post-R3 defect? | 0 |

四问门控 (advisor-not-driver):
- LLM 离线可跑? ✅ pure UI gating logic
- artifacts canonical? ✅ 3 source files + 3 desktop spot-check PNGs + retro
- TrustGate? N/A
- AI 仅 advisory? ✅ chrome is presentational

## What this enables

- **Demo recordings now case-authentic**: future runs of `m35_workbench_demo.mjs` on any canonical fixture will show the case's actual identity in chrome. M3.6 demo .webm is now technically outdated (still shows APU labels in its frames) — a re-record on the same `circular_cylinder_wake` case would be a clean replacement, but not blocking the milestone.
- **Spot-check baseline reset**: the "APU mock pollution" was so common in every screenshot that it constituted noise floor. With B7 closed, future spot-checks have a much higher signal — any APU labels appearing in a non-blueprint context will be a real defect.
- **Real case dogfooding now possible**: previously, opening any case in the workbench at step=geometry would mislead with APU labels. Engineers can now stage their case + see immediate case-specific feedback in chrome.

## Open questions / deferred

- **Re-record M3.6 demo on circular_cylinder_wake post-B7?** The .webm shipped in M3.6 cycle 1 still shows pre-fix APU chrome in non-geometry steps where the issue was visible. Marginal value — the chrome fix isn't itself "the demo". Defer until a real demo deliverable refresh is needed.
- **DRY the 3-copies-of-same-gate pattern**: `useEffectiveCaseId(caseId, activeStep)` hook. Deferred — janitorial, no business value.
- **Verify B7 fix on DoE step**: I didn't probe step=doe because DoE was intentionally left as blueprint-only (no case-specific DoE data exists yet). If/when DoE gets per-case wiring, the same pattern will need to apply.
- **Workbench-basics fixture vs imported manifest patches inconsistency** (carried over from M3.6 retro): `circular_cylinder_wake` basics says 7 patches; bottom KpiStrip shows 6 边界面. Acceptable for now; cleanup if/when basics + manifest get cross-validated.

## Session accumulator (post-M3.7 · 6 milestones · uninterrupted run)

| Milestone | Cycles | Deliverable | Confidence |
|---|---|---|---|
| M3.2 | 7 (incl. 4 prior · 3 this run) | Playwright dogfood E2E (7 tests) | high |
| M3.3 | 3 | Real-user UX validation arc + spot-check methodology | high |
| M3.4 | 5 | Geometry empty-state + B6 cascade-clear | high |
| M3.5 | 2 | Demo recording (overlay-injected · 73s) | high |
| M3.6 | 1 | Real-CAD demo iteration (cylinder render · 72s) | high |
| M3.7 | 1 | Workbench chrome de-hardcoding (B7) | high |
| **Total** | **19 cycles** | **23 commits ahead of origin/main** | **0 post-R3 defects** |

## Next milestone candidates

1. **M3.8 = M4 charter scoping**: long deferred. What comes after Step 7 Post → solver_run / results / report / Notion sync. Strategic. Likely needs Kogami opt-in. Substantial — multi-day scope.
2. **M3.8 = B4 sidebar dead-space**: last open P3 from M3.2 visual audit. Lightest cycle. ~5-15 LOC.
3. **M3.8 = re-record M3.6 demo post-B7**: refresh .webm with case-authentic chrome. ~30-min cycle.
4. **M3.8 = DRY useEffectiveCaseId hook**: extract the 3-times-repeated gating pattern. Janitorial. ~20-30 LOC.
5. **Stop · session-end batch sync**: 23 commits, 6 milestones, time to land Notion DEC sync + session summary.

Default if user 30 秒不开口: walk forward with #5 (session-end stop) — six milestones in a single run is a lot of accumulated work; Notion archive + RESUME.md update would seal the session for clean handoff.
