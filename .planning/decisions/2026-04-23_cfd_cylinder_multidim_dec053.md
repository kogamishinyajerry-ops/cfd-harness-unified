---
decision_id: DEC-V61-053
title: circular_cylinder_wake Type I multi-dim validation · LDC-style iteration loop · case 3 · v2.0 first-apply
status: PROPOSED (2026-04-23 · Stage 0 intake signed · Stage A not yet entered)
supersedes_gate: none
intake_ref: .planning/intake/DEC-V61-053_circular_cylinder_wake.yaml
methodology_version: "v2.0 (first-apply, not retroactive · see Notion methodology page §8)"
commits_in_scope: []  # filled as batches land
codex_verdict: TBD
autonomous_governance: true
autonomous_governance_counter_v61: 40
external_gate_self_estimated_pass_rate: 0.30
external_gate_self_estimated_pass_rate_source: .planning/intake/DEC-V61-053_circular_cylinder_wake.yaml
external_gate_caveat: "Type I DEC (4 scalar gates). Adapter already has forceCoeffs/FFT (DEC-V61-041), but measurement surface + u_mean_centerline extractor are net-new. See intake.yaml risk_flags."
notion_sync_status: pending
github_sync_status: pending
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
