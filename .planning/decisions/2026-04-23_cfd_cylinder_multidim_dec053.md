---
decision_id: DEC-V61-053
title: circular_cylinder_wake Type I multi-dim validation · LDC-style iteration loop · case 3 · v2.0 first-apply
status: IN_PROGRESS_DEMONSTRATION_GRADE (2026-04-24 · Batches A+B1+B2+B3+C+D code-complete · 3 Codex rounds F1-M2-clean on B1-C scope + Codex R4 APPROVE_WITH_COMMENTS on Batch D + 6 live-run fixes · live audit fixture populated 3 of 4 Type I gates · u_mean_centerline gate fix landed in fdfa98a, pending attempt-7 regen · precision-limited at 10s endTime, gold-grade requires future endTime bump DEC)
supersedes_gate: none
intake_ref: .planning/intake/DEC-V61-053_circular_cylinder_wake.yaml
methodology_version: "v2.0 (first-apply, not retroactive · see Notion methodology page §8/§9)"
commits_in_scope:
  - 505c022 docs(dec): DEC-V61-053 · Stage 0 intake + scaffold (v2.0 first-apply)
  - 5aebd56 docs(dec): intake v2 · Codex pre-Stage-A plan review APPROVE_PLAN_WITH_CHANGES
  - a50d522 feat(cylinder): Batch A · gold YAML hygiene + decisions documented
  - 63c11cb feat(cylinder): Batch B1a · laminar threading + domain grow + block scaling
  - f1a9cf3 feat(cylinder): Batch B1b · cylinderCenterline runtime sampling + assertion tests
  - bcf9f6a feat(cylinder): Batch B2 · centerline u_deficit extractor + semantics doc resolution
  - de6ee62 fix(cylinder): Codex round-1 response · 1H+3M+1L findings addressed
  - c8387ec feat(cylinder): Batch B3 · wire centerline extractor into adapter pipeline
  - 6b783f5 feat(preflight): Batch C · multi-scalar preflight gate for Type I cases
  - e7c7500 fix(cylinder): round-2 response · py3.9 f-string syntax + 3 doc sync
  - 0168c96 docs(dec): Round 3 APPROVE · B1+B2+B3+C F1-M2-clean
  - 2a7d5e4 docs(retro): RETRO-V61-053 · Python version parity + 3-round Codex calibration
  - 05faba8 feat(cylinder): Batch D backend · 4-scalar anchor emission in Compare-tab context
  - 90b5829 feat(cylinder): Batch D frontend · 4-scalar anchor cards in Compare-tab
  - 592922c feat(cylinder): Batch D karman_shedding generator · honest skip-guard
  - d3ffc06 fix(cylinder): Batch B1a bug — self._db did not exist on FoamAgentExecutor (live-run find)
  - 35f3278 fix(cylinder): live-run solver tuning — PCG p + endTime 10s + maxCo 1.0
  - e8b92ed fix(cylinder): live-run defect #3 — extractor gating + sort bug
  - dc0fc5f feat(cylinder): Batch D karman_shedding.png lands · real live-solver VTK
  - c81c0aa fix(cylinder): endTime-aware trim for extractors
  - ae64f73 feat(cylinder): live-run attempt 6 SUCCESS · 3/4 gates extracted
  - fdfa98a fix(cylinder): live-run defect #6 — cylinderCenterline FO missing executeControl
codex_verdict: APPROVE_WITH_COMMENTS (round 4, Batch D + 6 live-run fixes). Arc now 4 Codex rounds — R1 CHANGES_REQUIRED (1H+3M+1L) → R2 CHANGES_REQUIRED (1 py3.9 + 3 doc sync) → R3 APPROVE (clean on B1-C) → R4 APPROVE_WITH_COMMENTS (0H+1M+4L on Batch D + live-run fix chain). Under F1-M2 strict, APPROVE_WITH_COMMENTS is not clean-close — V61-053 lands as demonstration-grade; a gold-grade follow-up DEC should bump CYLINDER_ENDTIME_S from 10s → 60s or 200s and re-run for attempt-7 to populate u_mean_centerline + tighten St precision from ΔSt~20% to ΔSt~3%.
autonomous_governance: true
autonomous_governance_counter_v61: 40
external_gate_self_estimated_pass_rate: 0.30
external_gate_self_estimated_pass_rate_source: .planning/intake/DEC-V61-053_circular_cylinder_wake.yaml
external_gate_actual_outcome_partial: "4-round Codex arc, APPROVE_WITH_COMMENTS at R4. R1 pass rate ACTUAL=0% (CHANGES_REQUIRED, 5 findings) vs estimated 0.30. SIX post-R3 runtime-emergent defects surfaced via live OpenFOAM audit fixture regen campaign (6 attempts, 4 completed), ALL FIXED: (1) d3ffc06 self._db.get_execution_chain accessor bug · (2) 35f3278 GAMG+GaussSeidel p-divergence → PCG+DIC · (3) e8b92ed cylinder extractor gated on U/Cx/Cy field-file existence · (4) e8b92ed _copy_postprocess_fields sort-key lexical bug on decimal time dirs · (5) c81c0aa transient_trim defaults sized for 200s not 10s · (6) fdfa98a cylinderCenterline FO missing executeControl. Attempt-6 live run produced real physics: strouhal_number=0.138 (16% dev vs gold 0.165 — expected at 10s endTime with ΔSt~20% uncertainty from FFT Δf limit), cd_mean=1.379 (3.7% dev), cl_rms=0.081. u_mean_centerline gate populates on next attempt-7 regen. Codex R4 verdict: APPROVE_WITH_COMMENTS (0H+1M+4L) — all MED/LOW items addressed in follow-on commits (CYLINDER_ENDTIME_S single source of truth, secondary_scalars in fixture, karman_shedding label pimpleFoam, frontmatter refresh). All 6 defects are runtime-only — no static review can catch accessor bugs on unexercised object graphs, solver divergence on novel geometry + BC combos, or FO config syntax that registers-but-never-fires. Strongest evidence to date for the executable_smoke_test + solver_stability_on_novel_geometry + missing_execute_control_on_FO risk flag patterns now codified in .planning/intake/TEMPLATE.yaml. RETRO-V61-053 addendum captures all 6 as a distinct blind-spot category, separate from Codex round counts."
external_gate_caveat: "Type I DEC (4 scalar gates). Adapter already has forceCoeffs/FFT (DEC-V61-041), but measurement surface + u_mean_centerline extractor are net-new. See intake.yaml risk_flags. Codex log archive: reports/codex_tool_reports/dec_v61_053_{round1,round2,round3}.log. Live-run log archive: reports/phase5_audit/live_cylinder_run_20260424*.log"
codex_tool_report_path: reports/codex_tool_reports/dec_v61_053_round4.log (+ plan_review + round1 + round2 + round3 co-located)
notion_sync_status: synced 2026-04-24T02:55 · Status=Proposed (page_id=34cc6894-2bed-8168-ae98-f0657705f630, URL=https://www.notion.so/DEC-V61-053-circular_cylinder_wake-Type-I-multi-dim-validation-LDC-style-iteration-case-3-v2-34cc68942bed8168ae98f0657705f630). Methodology page §10 appended (static vs dynamic review addendum). PENDING re-sync to flip Status→Complete after Batch D audit fixture regen completes + Codex R4 verification.
github_sync_status: pushed (17 commits on origin/main · 10-commit pre-R3 arc + 2 post-R3 Batch D + 1 generator + 2 live-run fixes + 2 docs)
related:
  - DEC-V61-050 (LDC true multi-dim · Type I precedent · 4 rounds)
  - DEC-V61-052 (BFS · Type II precedent · 5 rounds incl. F1-M2 back-fill)
  - DEC-V61-041 (cylinder forceCoeffs FFT · retires canonical_st hardcode)
  - DEC-V61-036 (comparator gates G3/G4/G5 — canonical-band shortcut detector)
---

## Stage 0 · Case Intake (F1-M1 v2.0 hard gate)

Signed intake: [`.planning/intake/DEC-V61-053_circular_cylinder_wake.yaml`](../intake/DEC-V61-053_circular_cylinder_wake.yaml).

Key determinations:
- **case_type = I** (4 independent scalar gates: St, Cd_mean, Cl_rms, u_mean_centerline)
- **primary_gate_count = 4**
- **codex_budget_rounds = 3** soft target, **round 4 health check**, **round 6 force abandon** (F6-M1)
- **estimated_pass_rate_round1 = 0.30** (new u_mean_centerline extractor + stale measurement surface + multi-dim UI are net-new surface area)

**In-scope observables**: strouhal_number, cd_mean, cl_rms, u_mean_centerline @ x/D ∈ {1, 2, 3, 5}.
**Out-of-scope** (enforced by §3b): 3D effects, Re sweep, blockage correction, GCI study, inlet-turbulence sweep.

## Entry state (2026-04-23, before Stage A)

**Adapter**: forceCoeffs FO + `src.cylinder_strouhal_fft.emit_strouhal` already emit St/Cd/Cl via `key_quantities` (per DEC-V61-041). Good.

**Audit fixture**: `ui/backend/tests/fixtures/runs/circular_cylinder_wake/audit_real_run_measurement.yaml` currently surfaces `measurement.quantity = U_max_approx`, `measurement.value = 4.93502e-06`, `extraction_source: key_quantities_fallback`. Wrong primary scalar.

**Gold YAML**: `knowledge/gold_standards/circular_cylinder_wake.yaml` declares 4 observables; `contract_status = COMPATIBLE_WITH_SILENT_PASS_HAZARD` — documentation debt (hazard retired in DEC-V61-041).

**u_mean_centerline extractor**: does not exist. 4th observable is net-new code.

**Frontend**: `circular_cylinder_wake` sits in `_VISUAL_ONLY_CASES` → Tier C contour+residuals only; no Compare-tab scalar cards. flowFields.ts has `strouhal_curve.png` (analytical_visual) but no solver_output figure (unlike BFS `velocity_streamlines.png`).

**Preflight**: not yet wired for cylinder scalar gates.

## Stage A plan (revised per Codex pre-Stage-A review · intake v2)

Codex pre-Stage-A plan review at commit 505c022: **APPROVE_PLAN_WITH_CHANGES**
(see [reports/codex_tool_reports/dec_v61_053_plan_review.log](../../reports/codex_tool_reports/dec_v61_053_plan_review.log)).
Two plan-level defects caught pre-code:
1. Blockage claim was **false** — adapter uses 2D/8D/2.5D → 20% blockage, not <5%
2. **laminar_contract_vs_RAS_default mismatch** — whitelist says laminar, adapter silently uses kOmegaSST

Intake updated to v2 with 7 required edits. Batch B split into B1/B2/B3; Batch D gains its own preflight gate.

Full batch table in intake.yaml `batch_plan`. Summary:

- **Batch A** · gold YAML hygiene + domain/turbulence decisions (resolve blockage a/b/c, laminar a/b, cylinder_crossflow.yaml fate)
- **Batch B1** · adapter · sampleDict emission + forceCoeffs axis assertion (+ decisions applied)
- **Batch B2** · u_mean_centerline extractor (new module + unit tests on mock)
- **Batch B3** · audit fixture primary-scalar surfacing (St as primary, not U_max_approx)
- **Batch C** · preflight multi-scalar gate (4 gates GREEN)
- **Batch D** · Compare-tab multi-dim + solver_output figure + **Batch D preflight gate** (catches 122→119-class caption staleness)

**Codex cadence** (4 rounds budgeted per F6-M1):
- Round 0 (done, 2026-04-23): plan sanity — APPROVE_PLAN_WITH_CHANGES
- Round 1: post-Batch A close + Batch B1/B2 review
- Round 2: post-Batch B3/C close (all extractors → audit → preflight pipeline)
- Round 3: post-Batch D close (UI + provenance)
- Round 4: F6-M1 round-4 health check (halt_risk_flag if CHANGES_REQUIRED)

**Self-pass tracking** (intake predicts 0.30; RETRO-V61-001 requires pre-merge Codex if ≤ 70%):
- MUST pre-merge Codex review before any batch lands on main.

## Out-of-scope follow-ups (tracked, not this DEC)

- Re-sweep validation against Williamson 1996 St(Re) curve — separate DEC
- 3D span-wise shedding at Re > 180 — separate DEC
- GCI mesh-convergence study for cylinder — belongs to Phase 5 GCI protocol DEC

## Methodology notes

V61-053 is the **first DEC to exercise methodology v2.0 end-to-end**:
- F1-M1 (Stage 0 intake) satisfied via intake.yaml
- F1-M2 (two-tier close) will be evaluated at Stage E
- F5-M1 (Type I hard gate) signed pre-Stage-A
- F6-M1 (round 4 health / round 6 force abandon) codified in intake

V61-052 was retroactively compliant; V61-053 is natively compliant. Any
deviation from the intake (e.g. wanting to add a 5th observable mid-arc)
MUST open a new DEC.
