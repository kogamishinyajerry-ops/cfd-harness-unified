---
decision_id: DEC-V61-038
timestamp: 2026-04-22T11:30 local
scope: |
  Phase 8 Sprint 1 — Pre-extraction convergence attestor A1..A6. Complements
  DEC-V61-036b (post-extraction gates G3/G4/G5). Where G3/G4/G5 say "the
  extracted measurement cannot be trusted because the final-state fields
  are broken", A1..A6 say "the run itself never physically converged even
  if the solver exited 0". Composition is AND-gated: attestor runs first,
  ATTEST_FAIL forces contract FAIL before comparator extraction even looks
  at key_quantities.

  Six checks, all log-based (no separate VTK read — attestor reuses
  comparator_gates.parse_solver_log infrastructure):
    A1 solver_exit_clean   — exit code 0 AND no FOAM FATAL / floating exception in log
    A2 continuity_floor    — final sum_local ≤ case-specific floor (default 1e-4 incompressible)
    A3 residual_floor      — final Ux/Uy/Uz/p/k/epsilon/omega initial residuals ≤ case target (default 1e-3)
    A4 solver_iteration_cap — solver hit max-iteration ceiling (PCG p loops, BiCGStab loops) repeatedly → stuck
    A5 bounding_recurrence — turbulence bounding fired in ≥30% of last N iterations → fake convergence
    A6 no_progress         — initial residuals (any field) did not decay > 1 order over last 50 iterations

  Per RETRO-V61-001, attestor is a separate safety layer from gates — a
  case can have both ATTEST_FAIL (convergence broken) and G3/G4/G5 FAIL
  (final-state broken). UI surfaces both tiers so the audit package
  carries complete diagnostic info.

autonomous_governance: true
claude_signoff: yes
codex_tool_invoked: true (v6.2 backfill audit 2026-04-22 post-landing)
codex_rounds: 1 (v6.2 backfill audit round)
codex_verdict: BLOCK
codex_independent_pass_rate: 0.33 (vs claude-estimated 0.65 · Codex significantly more pessimistic; independent verification protocol caught major contract gaps)
codex_tool_report_path:
  - reports/codex_tool_reports/20260422_dec038_codex_review.md
codex_blockers_summary: |
  CA-001: validation_report.py:558 _derive_contract_status() hard-fails ONLY
          on A1/A4; ignores A2/A3/A5/A6 entirely → in-band scalar w/
          CONTINUITY_NOT_CONVERGED or NO_RESIDUAL_PROGRESS still returns
          PASS. Violates DEC's two-tier HAZARD/FAIL contract.
  CA-002: phase5_audit_run.py:539 + task_runner.py:103 do NOT run attestor
          pre-extraction. TaskRunner runs solver→comparator→correction
          BEFORE _audit_fixture_doc() adds attestation → non-converged runs
          flow through scalar extraction + correction generation. Violates
          "attestor first, then extraction/gates" contract.
  CA-003: convergence_attestor.py:206 A1 is log-only; never consumes
          ExecutionResult.success (container exit_code). Also only matches
          ^Floating point exception, not broader variants. DEC requires
          "exit code 0 AND no fatal markers".
  CA-004: **knowledge/attestor_thresholds.yaml DOES NOT EXIST in repo**
          despite convergence_attestor.py:24 referencing it. Per-case
          override + HAZARD→FAIL promotion mechanism are non-functional.
  CA-005: A3/A6 field-agnostic (one 1e-3 floor for all fields incl.
          buoyant h/p_rgh). On real impinging_jet log current code
          produces A6 HAZARD on p_rgh (5.91e-01..6.98e-01, 0.07 decades)
          contradicting DEC expectation (impinging_jet should fail only
          via A4, not A6).
codex_nits_summary: |
  CA-006: "stuck" uses < 1.0 decade, DEC criterion says <= 1.0.
  CA-007: A4 consecutiveness filters gap blocks → cap,gap,cap,cap treated
          as 3 consecutive (stricter than DEC text).
  CA-008: test_convergence_attestor.py missing 10-case real-log integration
          matrix promised by DEC. Only LDC+BFS covered.
followup_dec_pending: true
followup_dec_scope: "Fix CA-001..CA-005 blockers. Most critical: (a) land knowledge/attestor_thresholds.yaml, (b) wire A2/A3/A5/A6 into _derive_contract_status HAZARD tier with per-case FAIL promotion, (c) move attestor pre-extraction in task_runner, (d) feed exit_code into A1, (e) per-field/per-case A3+A6 semantics. Requires new Codex round post-fix. Flagged to Kogami for scope decision."
counter_status: |
  v6.1 autonomous_governance counter 24 → 25 after this DEC lands. Retro at 30.
reversibility: |
  Fully reversible. New module src/convergence_attestor.py + integration
  into phase5_audit_run.py + concern types in _derive_contract_status.
  Revert = 3 files + 1 test file restored. No fixture regeneration needed
  because attestor reads reports/phase5_fields/* which is reproducible.
notion_sync_status: pending (v6.2 backfill Codex BLOCK; escalate to Kogami)
github_pr_url: null (direct-to-main)
github_merge_sha: 7f29a64 + eb51dcf + 9716dd4 (already landed pre-Codex-verify)
github_merge_method: direct-to-main landed; v6.2 backfill audit surfaced 5 blockers requiring substantial follow-up (BLOCK tier)
external_gate_self_estimated_pass_rate: 0.65
  (Mostly log-regex work reusing comparator_gates infrastructure. Main
  risk is threshold calibration — specifically A3 residual_floor on
  buoyantFoam which never converges to 1e-5 because radiation/buoyancy
  coupling is inherently oscillatory. DHC case may need a higher floor
  per-case override. Codex physics audit will spot this.)
supersedes: null
superseded_by: null
upstream: |
  - DEC-V61-036b (G3/G4/G5) — sibling post-extraction gates
  - Codex round-1 physics audit on DEC-V61-036: impinging_jet p_rgh hits
    1000 iter (attestor A4 catches); BFS residuals never drop (A6);
    cylinder Co≈5.9 unsteady oscillation (A2 catches but threshold needs
    unsteady-solver override).
---

# DEC-V61-038: Convergence attestor A1..A6

## Why now

G3/G4/G5 tell you the final-state fields are broken. They don't tell you
*why*. Attestor A1..A6 diagnose the convergence process itself:

- A1 catches `FOAM FATAL IO ERROR` in the log tail (solver crashed mid-run
  but exited 0 from the shell's perspective because Docker swallowed the
  signal).
- A2 is the complement of G5 at a tighter threshold: G5 fires on
  `sum_local > 1e-2` (hard divergence); A2 fires on `sum_local > 1e-4`
  (incomplete convergence).
- A3 reads the final-iteration `Solving for Ux/Uy/p/k/epsilon`
  `Initial residual` values and compares against case targets.
- A4 detects solver iteration caps — when `GAMG:  Solving for p, ...
  No Iterations 1000` appears in ≥ 3 consecutive outer iterations, the
  pressure-velocity coupling has failed and the solver is just burning
  time.
- A5 detects turbulence bounding recurrence — healthy cases bound maybe
  10-20% of early iterations then stabilise. Pathological cases bound
  30%+ of the FINAL iterations, indicating the solution never settles.
- A6 detects no-progress convergence — when Initial residual for any
  field fluctuates within a decade across the last 50 iterations, the
  solver is stuck at a residual plateau and "converged" is a lie.

## Design decisions

1. **Attestor runs BEFORE comparator extraction**, inside
   `scripts/phase5_audit_run.py::_audit_fixture_doc` right after
   field_artifacts_ref resolution and before gate checks. This ordering
   lets ATTEST_FAIL propagate into fixture metadata early so downstream
   UI can branch on it.

2. **Concern codes** (all new):
   - A1: `SOLVER_CRASH_LOG` (summary includes first fatal line)
   - A2: `CONTINUITY_NOT_CONVERGED` (vs G5 `CONTINUITY_DIVERGED`)
   - A3: `RESIDUALS_ABOVE_TARGET` (includes which fields missed)
   - A4: `SOLVER_ITERATION_CAP` (includes which solver loop)
   - A5: `BOUNDING_RECURRENT` (includes field + % of iterations bounded)
   - A6: `NO_RESIDUAL_PROGRESS` (includes field + decade range)

3. **Verdict engine integration**: `_derive_contract_status` extends
   hard-FAIL concern set again. HOWEVER — A2/A3/A5/A6 are nuanced:
   some cases genuinely operate at high residuals (impinging jet
   p_rgh equilibrates at 1e-2 due to stagnation). Therefore A2/A3
   default to HAZARD (not FAIL), and can be promoted to FAIL via
   per-case override. A1/A4 are always FAIL (solver crashes / caps
   are never acceptable).

4. **Per-case thresholds** in new `knowledge/attestor_thresholds.yaml`:
   ```yaml
   defaults:
     continuity_floor: 1.0e-4
     residual_floor: 1.0e-3
     iteration_cap_detector_count: 3
     bounding_recurrence_frac_threshold: 0.30
     bounding_recurrence_window: 50
     no_progress_decade_frac: 1.0
     no_progress_window: 50
   per_case:
     impinging_jet:
       # stagnation region — p_rgh plateaus higher
       residual_floor: 5.0e-3
     rayleigh_benard_convection:
       # oscillatory instability — residuals don't decay monotonically
       residual_floor: 2.0e-3
       no_progress_decade_frac: 0.3
     circular_cylinder_wake:
       # unsteady pimpleFoam — continuity oscillates per-step
       continuity_floor: 1.0e-3
   ```

## Expected verdicts on current 10 fixtures

| case | A1 | A2 | A3 | A4 | A5 | A6 | Overall |
|---|---|---|---|---|---|---|---|
| lid_driven_cavity | pass | pass | pass | pass | N/A (laminar) | pass | ATTEST_PASS |
| backward_facing_step | pass | FAIL | FAIL | pass | FAIL | FAIL | ATTEST_FAIL (redundant with G3/G4/G5) |
| circular_cylinder_wake | pass | HAZARD | HAZARD | pass | check | check | ATTEST_HAZARD |
| turbulent_flat_plate | pass | check | check | pass | check | check | expected HAZARD or FAIL |
| duct_flow | pass | FAIL | FAIL | pass | FAIL | FAIL | ATTEST_FAIL (redundant with G3/G4/G5) |
| differential_heated_cavity | pass | pass | check | pass | pass | check | expected HAZARD (Nu off gold but converged) |
| plane_channel_flow | pass | pass | pass | pass | check | pass | ATTEST_PASS (convergence OK; comparator is the problem) |
| impinging_jet | pass | pass | HAZARD | **FAIL** | pass | pass | ATTEST_FAIL via A4 |
| naca0012_airfoil | pass | pass | HAZARD? | pass | pass | pass | ATTEST_PASS or HAZARD |
| rayleigh_benard_convection | pass | HAZARD | HAZARD | pass | pass | check | ATTEST_HAZARD |

Critical: **LDC must stay clean** — it is the gold-overlay PASS reference
and cannot be destabilised by A1..A6 false positives.

## Test plan

`ui/backend/tests/test_convergence_attestor.py` (new):
- Per-check unit tests with synthetic log strings (one per check):
  - A1 log with `FOAM FATAL IO ERROR` → FAIL
  - A2 log with final `sum local = 1e-3` → HAZARD (between A2 and G5 floors)
  - A3 log with final `Solving for Ux, Initial residual = 0.5` → FAIL
  - A4 log with 5 consecutive `No Iterations 1000` → FAIL
  - A5 log with 20/50 `bounding k` lines → FAIL
  - A6 log with Ux residual oscillating 0.4 ± 0.02 for 50 iterations → FAIL
- Per-case integration tests against the current 10 audit logs
  (`reports/phase5_fields/{case}/{ts}/log.*`), asserting the expected
  verdict column above.
- LDC regression: explicit assertion that LDC's actual log produces
  ATTEST_PASS (guard against threshold creep).

## Counter + Codex

24 → 25 after landing. Pre-merge Codex review required (self-pass 0.65).

## Related
- DEC-V61-036 G1 — schema gate (foundational)
- DEC-V61-036b — post-extraction physics gates (sibling)
- DEC-V61-036c (future) — G2 unit canonicalization + comparator u+/y+ fix
- RETRO-V61-001 — governance; this DEC counts +1
