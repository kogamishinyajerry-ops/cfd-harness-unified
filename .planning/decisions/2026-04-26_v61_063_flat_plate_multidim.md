---
decision_id: DEC-V61-063
title: Turbulent Flat Plate Type II multi-dim validation · Blasius laminar contract · case 4 · v2.0 fourth-apply
status: METHODOLOGY_COMPLETE_PHYSICS_FIDELITY_GAP_DOCUMENTED (2026-04-26 · Stages 0+A.1..A.5+R1+F1+F2+R2+A.6+A.7+B+R3 code-complete · Codex R1 CHANGES_REQUIRED → R2 APPROVE → R3 APPROVE_WITH_COMMENTS · Stage B v3 live OpenFOAM run solver-converged on laminar contract · physics-fidelity gates FAIL by 10-30% across all 4 HARD_GATED observables due to top-wall channel-domain mismatch · domain/BC fix queued as DEC-V61-064 per Codex R3 ACCEPT disposition)
supersedes_gate: none
intake_ref: .planning/intake/DEC-V61-063_turbulent_flat_plate.yaml
methodology_version: "v2.0 (fourth-apply, post-V61-053 first-apply + V61-057 second-apply + V61-058 third-apply)"
case_type: II  # 1 primary scalar + 3 secondary observables (Cf(x) profile + K_x invariant + δ_99(x))
commits_in_scope:
  # Stage 0 — intake + Codex pre-Stage-A plan review (skipped — V61-058 precedent)
  - 2ce0ba5 intake(flat_plate): DEC-V61-063 Stage 0 · v1 draft
  # Stage A — methodology + adapter + gold YAML + alias parity
  - 21b4b16 [shared] register src.flat_plate_extractors in plane SSOT
  - 2b52248 A.1(flat_plate): secondary observable extractors module (34 tests)
  - 2577b28 A.2(flat_plate): multi-x Cf profile extraction in adapter (5 tests)
  - a35777b A.3(flat_plate): wire enrich_cf_profile in adapter (4 tests)
  - ac60303 A.4(flat_plate): gold YAML observables expansion + dict-shape emits (3 tests)
  - fb61bdb A.5(flat_plate): Execution→Evaluation alias parity (8 tests)
  - 4059438 intake(flat_plate): mark Stage A COMPLETE + queue Codex round 1
  # Codex R1 verbatim fixes (CHANGES_REQUIRED → fix → R2 APPROVE)
  - c59cff1 fix(flat_plate): F1 gate on measured mean_K not constant canonical_K
  - 070037f fix(flat_plate): F2 emit cf_sign_flip audit keys
  - 26c68b4 docs(flat_plate): Codex R1+R2 reports + Stage B kickoff active
  # Stage B post-R3 RETRO-V61-053 case-gen fixes (live-run-only defects)
  - 0722c8c A.6(flat_plate): case-gen consults whitelist turbulence_model
  - 66f0e42 A.7(flat_plate): laminar-aware _generate_steady_internal_flow
  # Codex R3 disposition review + closeout
  # commit hash assigned at commit time
codex_verdict: APPROVE_WITH_COMMENTS (round 3, methodology + case-gen + disposition scope). 3-round Codex arc — R1 CHANGES_REQUIRED (F1 HIGH gate-tautology + F2 MED sign-flip-warning-only, both fixed verbatim c59cff1 + 070037f) → R2 APPROVE (no residual, both Codex-reproduced repros now fail-as-expected) → R3 APPROVE_WITH_COMMENTS (A.6 + A.7 + Stage B v3 disposition · 1 MED D1 doc-wording, fixed verbatim in this commit). Per F1-M2 strict, APPROVE_WITH_COMMENTS at R3 closes the methodology + case-gen scope as code-complete. Stage B v3 hard-gate FAIL is the genuine measurement outcome (not a methodology defect) — Codex R3 explicitly directed disposition=ACCEPT and queueing V61-064 for the structural top-wall/freestream BC fix.
autonomous_governance: true
autonomous_governance_counter_v61: 43  # incremented from V61-058's 42
external_gate_self_estimated_pass_rate: 0.45
external_gate_self_estimated_pass_rate_source: .planning/intake/DEC-V61-063_turbulent_flat_plate.yaml §7
external_gate_actual_outcome_partial: |
  3-round Codex arc, final R3 verdict APPROVE_WITH_COMMENTS. R1 ACTUAL=0% (CHANGES_REQUIRED, 2 findings F1+F2) vs estimated 0.45 — overestimated; F1 specifically (hard-gate against constant value) was a categorical methodology miss that no SNR test could have caught. R2 ACTUAL=100% (APPROVE, 0 residuals) — F1+F2 fixes both verbatim, Codex reproduced both acceptance scenarios independently. R3 ACTUAL=80% (APPROVE_WITH_COMMENTS, 1 D1 doc-wording residual) vs estimated 0.40 (R3 was unplanned in original budget — added under RETRO-V61-053 post-R3 protocol after Stage B v1 exposed pre-existing case-gen defects).
notion_sync_status: "synced 2026-04-26T00:24 · Status=Accepted (page_id=34dc6894-2bed-8185-9ff4-f65210c5f3e7, URL=https://www.notion.so/DEC-V61-063-Turbulent-Flat-Plate-Type-II-multi-dim-validation-methodology-v2-0-fourth-apply-34dc68942bed81859ff4f65210c5f3e7). Body: headline callout + 3-round Codex arc + Stage B v1→v2→v3 iteration table + RETRO-V61-053 post-R3 defect addendum + methodology v2.0 fourth-apply calibration table + counter calibration + GitHub artifact links + V61-064 follow-up callout."
codex_tool_report_path:
  - reports/codex_tool_reports/dec_v61_063_round1_review.md
  - reports/codex_tool_reports/dec_v61_063_round2_review.md
  - reports/codex_tool_reports/dec_v61_063_round3_review.md
post_r3_defect_addendum_path: .planning/intake/DEC-V61-063_stage_b_v3_disposition.md
related_decisions:
  - DEC-V61-006  # B-class metadata correction: case is laminar Blasius (predates V61-063)
  - DEC-V61-053  # Cylinder R1 whitelist-first dispatch pattern (mirrored in A.6)
  - DEC-V61-057  # Type II precedent (DHC) — observable schema pattern
  - DEC-V61-058  # Type II precedent (NACA) — methodology v2.0 third-apply
  - DEC-V61-064  # PROPOSED follow-up — flat-plate domain/BC structural fix
risk_flags_at_close:
  cf_extractor_x_aliasing: RESOLVED (max(spacings) floor + per-x x_tol verified in Stage B v3)
  spalding_fallback_silent_fire: RESOLVED (cf_spalding_fallback_count=0 in v3, F2 audit key stamps the inactive-state)
  blasius_invariant_extreme_sensitivity_to_inlet_drift: RESOLVED-POSITIVE (rel_spread=0.037 << 5% threshold; invariant tight in measured profile)
  stage_b_runtime_budget: RESOLVED (14.5s wall, well under 5min budget)
  openfoam_version_emitter_api_drift: RESOLVED (no API drift surfaced; A.7 fixed pre-existing laminar dispatch)
  executable_smoke_test: RESOLVED (Stage B v3 solver_success=True, all 28 key_quantities populated)
  solver_stability_on_novel_geometry: OPEN-DEFERRED (top-wall mismatch — V61-064 scope)
---

# DEC-V61-063 · Turbulent Flat Plate Multi-Dim Validation · Blasius Laminar Contract

## Summary

Add Type II multi-dimensional validation observables for the
`turbulent_flat_plate` whitelist case (case 4 of 10), under the
V61-006 corrected laminar Blasius regime. Extends the back-compat
single-scalar `cf_skin_friction` gate with 3 new HARD_GATED
observables: `cf_x_profile_points` (Cf(x) profile at 4 streamwise
positions), `cf_blasius_invariant_mean_K` (measured K_x = Cf·√Re_x
similarity invariant), `delta_99_x_profile` (boundary-layer thickness
at 2 streamwise positions). Adds machine-visible audit keys
(`cf_extractor_path`, `cf_enrichment_path`, `cf_spalding_fallback_*`,
`cf_sign_flip_*`).

## Outcome

| Stage | Verdict | Evidence |
|---|---|---|
| A.1-A.5 (methodology + alias parity) | PASS | 58 tests green; Codex R2 APPROVE on synthetic Blasius-consistent data |
| Codex R1 → R2 verbatim fixes | RESOLVED | F1 (mean_K vs canonical_K) + F2 (sign-flip audit) — both Codex-reproduced |
| A.6 + A.7 (live-run readiness) | RESOLVED | Whitelist-first dispatch + laminar-aware case-gen; 64 tests green |
| Stage B v3 live OpenFOAM | FAIL_PHYSICS_BORDERLINE | Solver converged, gates correctly reject 10-30% rel_error from top-wall mismatch |
| Codex R3 disposition | APPROVE_WITH_COMMENTS | Validates methodology + case-gen + disposition; queues V61-064 |

## Stage B v3 measured values

| Observable | Measured | Reference | rel_error | Within 10% tol? |
|---|---|---|---|---|
| `cf_skin_friction` | 0.00465 | 0.00420 | 10.7% | ✗ (just over) |
| `cf_x_profile_points` (max) | per-x list | per-x list | 14.5% | ✗ (worst at x=1.0) |
| `cf_blasius_invariant_mean_K` | 0.736 | 0.664 | 10.9% | ✗ (just over) |
| `delta_99_x_profile` (max) | per-x list | per-x list | 30.1% | ✗ (BL too thin) |
| `cf_blasius_invariant_rel_spread` | 0.037 | (audit-only) | n/a | ✓ (well under 5%) |
| `cf_spalding_fallback_count` | 0 | 0 | n/a | ✓ (laminar contract honored) |
| `cf_sign_flip_count` | 0 | 0 | n/a | ✓ (clean orientation) |

per-x K_x: 0.698 → 0.735 → 0.751 → 0.760 (monotonic increasing — BL not
fully developed into Blasius similarity).

## Why this is a methodology success

1. **Gates have teeth.** Codex R1 reproduced a false-pass against the
   pre-A.5 `cf_blasius_invariant_canonical_K` constant gate. Post-A.5
   on the SAME synthetic emit: `PASS_WITH_DEVIATIONS` (not PASS), with
   the new `mean_K` gate firing rel_error 37.85%. F1 fix has the
   intended teeth.
2. **Live-run validation works.** Stage B v3 produced 28 distinct
   audit keys end-to-end (cf_x_profile, dict-shape comparator-facing
   profiles, Blasius invariant per-x K_x, δ_99 with rel_error tracking,
   Spalding/sign-flip audit flags). All flowed through
   `GoldStandardComparator` without manual reshaping.
3. **Audit transparency.** `cf_extractor_path = "wall_gradient_v1"` and
   `cf_enrichment_path = "enrich_cf_profile_v1_inline"` stamp every
   live run. Spalding fallback inactive (correct under laminar
   contract); sign flip inactive (correct orientation).
4. **Methodology v2.0 fourth-apply.** Closes the V61-053/057/058
   sequence — Type II with the multi-x invariant gate is now a
   reusable pattern.

## Why Stage B FAIL is the right verdict

The new V61-063 gates are correctly rejecting a borderline run. The
deviation is 10-30% and traces to a structural domain mismatch (top
wall = no-slip channel, not freestream flat plate) directly evidenced
in `src/foam_agent_adapter.py:4032,4510`. Per Codex R3:

> Close V61-063 as `FAIL_PHYSICS_BORDERLINE`, not
> `PASS_WITH_DEVIATIONS`. The validation work succeeded, but the live
> physics result genuinely failed tolerance.

The fix is structural execution-plane work outside V61-063's
extractor/comparator envelope. Queued as DEC-V61-064.

## Methodology v2.0 fourth-apply calibration

| Dimension | V61-053 1st | V61-057 2nd | V61-058 3rd | V61-063 4th |
|---|---|---|---|---|
| Codex rounds | 4 | 4 | 3 (pre-A + R1 + R2) | 3 (R1 + R2 + R3) |
| Pre-Stage-A review | none | informal | REQUEST_CHANGES (6 edits) | none (intake landed clean) |
| Live-run defects post-R3 | 6 | 0 | 2 plumbing + 1 physics | 2 case-gen (A.6 + A.7) + 1 physics (FAIL_PHYSICS_BORDERLINE) |
| Headline gate verdict | St ΔSt~20% (precision-limited) | Nu +0.44% PASS | Cl 40% under (FAIL) | mean_K 10.9% over (FAIL) |
| Closeout grade | demonstration_grade | headline_validated | methodology_complete_physics_fidelity_gap_documented | **methodology_complete_physics_fidelity_gap_documented** |

V61-063 confirms the post-R3 RETRO-V61-053 protocol works at scale: a
methodology success can coexist with a live-run physics-fidelity FAIL
when the gap traces to a structural defect outside the DEC's scope.
Continuing to iterate Stage B inside the DEC would be scope creep.

## Closeout disposition

DEC-V61-063 closes as `METHODOLOGY_COMPLETE_PHYSICS_FIDELITY_GAP_DOCUMENTED`.

Follow-up: **DEC-V61-064 (proposed)** addresses the structural
top-wall/freestream BC fix. Acceptance: same V61-063 gates + same
mesh, with `cf_blasius_invariant_mean_K` rel_error <10% on the
corrected domain. Optional **DEC-V61-065** if V61-064 still leaves
>10% mesh truncation residual.
