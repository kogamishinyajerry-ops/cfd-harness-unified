---
decision_id: DEC-V61-204
title: M4 charter — Post-Step-7 closed loop wired into the V4 shell
status: Accepted
parent_dec: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED (M3.x guided construction arc · Accepted)
phase: M4 cycle 1 (charter scoping · continuation session 2026-05-25)
notion_sync_status: synced 2026-05-25 (https://www.notion.so/36bc68942bed813c8b1fd6ea8a1550a7)
autonomous_governance: false
confidence: high
date: 2026-05-25
ratified_by: user (approved M4 development 2026-05-25) + Kogami APPROVE_WITH_COMMENTS (review.md, 2026-05-25, recommended:merge)
kogami_review: .planning/reviews/kogami/m4_post_step7_charter_2026-05-25/review.md
---

# DEC-V61-204 · M4 charter — Post-Step-7 closed loop in V4

## TL;DR

Wire the V4 workbench's Step-6/7 (solver/post) to the **existing** backend
run→results→report pipeline. A surface-scan found that pipeline is **~95% already
built** (for the now-retired V3/M-PANELS wizard) but never connected to the
consolidated V4 shell. M4 is a **focused 3-4 cycle wiring + validation
milestone, NOT a multi-day net-new build.**

## Surface-scan finding (the reason the charter is small)

Per Explore agent + targeted verification (2026-05-25):

| Capability | State | Evidence |
|---|---|---|
| Solver run | ✅ EXISTS | `POST /api/import/{id}/solve` (case_solve.py) + run-history routes; `api.solve()` in client.ts:836 |
| Results harvest | ✅ EXISTS + wired | `/residual-series`, `/results-summary`, `/report-bundle`; V4 ModeRendererPost shows residual chart + convergence gauge via `useResidualSeries` |
| Report generation | ✅ EXISTS | matplotlib 4-figure bundle (`/report-bundle`) + PDF comparison report (weasyprint) |
| **V4 run-trigger** | ❌ **MISSING** | no V4 component calls `api.solve()` — the trigger lived in the retired V3/M-PANELS wizard; V4 (the only shell now) has no "Run" affordance |
| **report-bundle in V4** | ❌ **MISSING** | 0 references to `report-bundle` under `ui/frontend/src/pages/workbench/v4/` — the matplotlib figures aren't surfaced in V4 Post |
| Notion runtime sync | ❌ MISSING (out of scope) | forbidden by DEC-V61-130 advisor-not-driver (no runtime mutation); deferred post-M4 |

## Theme

Close the post-construction loop **inside the V4 shell**: from a built case, an
engineer clicks Run → solver executes (existing backend) → results refresh →
report figures display — all without leaving V4. This finishes the V3→V4
consolidation, which carried the *display* of results into V4 but left the *run
trigger* and the *report-bundle figures* behind.

## In scope

- **C1 (this DEC)**: charter + surface-scan + Kogami strategic review.
- **C2 · V4 run-trigger**: an engineer-initiated "运行求解 / Run" affordance in the
  V4 Step-6/7 surface → `api.solve(caseId)` → run status + auto-refresh of
  results on completion. **Engineer-initiated only** (AI never auto-runs).
- **C3 · V4 report-bundle display**: surface the `/report-bundle` matplotlib
  figures (contour-streamlines / pressure / vorticity / centerline) in V4 Post,
  as canonical artifacts (PNG URLs from the backend, provenance-labelled).
- **C4 · end-to-end dogfood + close retro**: V4 walk on a real case
  (circular_cylinder_wake or lid_driven_cavity): build → Run → results → report,
  scripted + visual spot-check.

## Out of scope

- **Notion runtime sync** — advisor-not-driver (DEC-V61-130) forbids runtime
  mutation; remains a deferred, user-triggered, planning-side concern.
- New solver / results / report **engines** — all exist; M4 is wiring only.
- GPU/CPU/temp telemetry placeholders in ModeRendererSolver — no backend source;
  net-new instrumentation is its own future milestone, not M4.
- V3 / M-PANELS revival — those routes are retired by design.

## Expected cycles

3-4 (C2 run-trigger · C3 report display · C4 dogfood+retro; C2/C3 may split if
the run-status UX needs SSE wiring vs the existing blocking `/solve`).

## Close criterion (explicit pass condition · folds Kogami [P3] C4)

C4 dogfood `passes: true` iff ALL hold (borrowing the harness `passes` field —
COMPLETED ≠ passes):
1. From the V4 workbench on a real backend case (circular_cylinder_wake or
   lid_driven_cavity), an engineer clicks Run → `/solve` returns exit_code 0.
2. Step-7 results refresh: `/residual-series` source flips to `log`/`runs`
   (not `empty`) and `/results-summary` returns finite U-magnitude stats.
3. Report-bundle figures render in V4 Post **OR** (matplotlib-absent build) V4
   shows the explicit "report unavailable on this build" state — never a crash.
4. No regression to the M3.x guided-construction flow (existing V4 vitest green).
Verified by a dogfood script (asserts 1-4 programmatically) + a visual
spot-check screenshot in the close retro.

## Four-question gate (V130)

- **LLM offline / runs?** ✅ the solve is a backend Docker call (`EXECUTOR_MODE`),
  no LLM; the whole loop runs LLM-offline.
- **Artifacts canonical?** ✅ run artifacts (measurement.yaml), residual series,
  VTP, matplotlib PNG bundle — all file-backed.
- **TrustGate explainable?** ✅ run provenance + residual source labels
  ("log" / "runs" / "empty") already surfaced; report figures carry cache-version
  provenance.
- **AI advisory-only?** ✅ the Run is an **engineer-initiated button click**; AI
  never triggers a solve. Same engineer-initiated pattern as the M3.0 PATCH loop.

## Decided defaults (folds Kogami [P2] "open questions lack decision criteria")

Kogami flagged the C2/C3 questions as deferred without criteria. Resolved as
defaults (C2 may deviate only with a commit-message rationale):

1. **Run-status UX** → **blocking call + spinner + run-history poll** (NOT SSE).
   Rationale: `/solve` is already blocking (~60s); the SSE path
   (`/api/wizard/run/:id/stream`) is V3-wizard-era and adds wiring for marginal
   UX. Revisit only if the blocking UX tests poorly in C4 dogfood.
2. **Run affordance location** → **Step-6 (solver) topbar CTA**, reusing the
   M3.0 `topbar_cta` dynamic-frame pattern (engineer-initiated, advisory-clean).
   Not Step-7 (post is read-only results).
3. **Report-bundle** → **inline figures in Step-7 Post when the backend reports
   them available**; the `/report-bundle` route already skips matplotlib
   gracefully on stock `.[ui]` builds, so V4 renders a "report unavailable on
   this build" state otherwise (folds Kogami [P2] matplotlib env dependency —
   no crash, no hard dep). No separate "generate" gate.

## Gating (folds Kogami [P3] parent-DEC gate)

C2 starts only with this charter at **Status=Accepted** (now true) and parent
**DEC-V61-202 Accepted** (already true). Implementation cycles are sub-DECs /
spike-class under this charter per v2.3.

## Rollback

Charter-only DEC; no code yet. To unwind: mark Status=Rejected (or Superseded);
no implementation has been committed.

## Kogami strategic review (2026-05-25)

`APPROVE_WITH_COMMENTS` · recommended: merge ·
`.planning/reviews/kogami/m4_post_step7_charter_2026-05-25/review.md`. Assessment:
coherent arc, on-roadmap, strong out-of-scope hygiene (Notion correctly excluded
per DEC-V61-130), 4/4 four-question gate, no self-modification/manipulation,
clean rollback. 4 findings (2×P2 + 2×P3) all foldable — folded above; Kogami
explicitly noted "none warrant a re-charter." Q1 canary PASS 5/5 (claude CLI
2.1.138→2.1.150 re-verified, baseline updated).
