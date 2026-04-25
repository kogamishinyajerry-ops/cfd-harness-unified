# DEC-V61-063 Stage B kickoff

**Status:** UNBLOCKED — Codex round 2 returned `APPROVE` 2026-04-25.
**Round 1:** `CHANGES_REQUIRED` (F1 HIGH + F2 MEDIUM); both fixed verbatim
(`c59cff1`, `070037f`).
**Round 2:** `APPROVE` (no residual findings, 88 tests across alias-parity +
adapter + extractor green; 98k tokens).
**Reports:** `reports/codex_tool_reports/dec_v61_063_round1_review.md` +
`...round2_review.md`.
**Codex budget consumed:** 2 of 4. Remaining: 2 (post-R3 RETRO-V61-053
addendum still applies for live-run-only defects).

## 1. Run command

```bash
.venv/bin/python scripts/phase5_audit_run.py turbulent_flat_plate \
  2>&1 | tee reports/phase5_audit/dec_v61_063_stage_b_live_run_v1.log
```

This drives `FoamAgentExecutor` against the live OpenFOAM Docker container,
writes audit fixture to
`ui/backend/tests/fixtures/runs/turbulent_flat_plate/audit_real_run_measurement.yaml`
and the raw run JSON to
`reports/phase5_audit/<timestamp>_turbulent_flat_plate_raw_run.json`.

## 2. Acceptance criteria (Stage B PASS)

The live run output must satisfy ALL of:

### 2a. Adapter emit completeness
- [ ] `cf_x_profile` — list of (x, Cf) tuples, ≥2 samples
- [ ] `cf_x_profile_points` — list of {"x", "Cf"} dicts, parity with tuple
- [ ] `cf_x_profile_n_samples` ≥ 2
- [ ] `cf_extractor_path == "wall_gradient_v1"`
- [ ] `cf_spalding_fallback_activated == False` (laminar contract — fallback
      MUST NOT fire per `physics_contract.physics_precondition[3]`)
- [ ] `cf_blasius_invariant_canonical_K` populated (scalar)
- [ ] `cf_blasius_invariant_n_samples` ≥ 2
- [ ] `cf_enrichment_path == "enrich_cf_profile_v1_inline"`
- [ ] `delta_99_at_x_0p5` populated (scalar)
- [ ] `delta_99_at_x_1` populated (scalar)
- [ ] `delta_99_x_profile` — list of {"x", "value"} dicts, len == 2
- [ ] `cf_skin_friction` (back-compat) populated, ≈ Cf at x=0.5 in profile

### 2b. Comparator verdicts (gold-standard-comparator)
- [ ] `cf_skin_friction` rel_error < 10%
- [ ] `cf_x_profile_points` profile rel_error < 10% at each ref x
- [ ] `cf_blasius_invariant_canonical_K` rel_error < 10%
- [ ] `delta_99_x_profile` profile rel_error < 10% at each ref x
- [ ] Overall verdict: `PASS` (all 4 HARD_GATED observables within tol)

### 2c. Numerical sanity
- [ ] Solver converged: residuals reported, not divergent
- [ ] No `cf_blasius_invariant_error` key in emit
- [ ] No `delta_99_at_x_*_error` keys in emit
- [ ] No `delta_99_at_x_*_missing_u_line` flags (full coverage at x ∈ {0.5, 1.0})
- [ ] `cf_blasius_invariant_rel_spread` ≤ 0.05 (Blasius invariant tightness;
      intake §6 risk `blasius_invariant_extreme_sensitivity_to_inlet_drift`)

## 3. Failure modes (each maps to a §6 risk register entry)

| Symptom | Risk flag | Mitigation |
|---|---|---|
| `cf_spalding_fallback_activated == True` | `spalding_fallback_silent_fire` | Investigate why wall-gradient gave Cf > 0.01; likely mesh/BC/regime mismatch. The fallback firing under laminar contract is a HARD STOP. |
| `cf_blasius_invariant_rel_spread > 0.05` | `blasius_invariant_extreme_sensitivity_to_inlet_drift` | Inlet-velocity drift, mesh-induced acceleration, or x_origin offset. Inspect U_inf at x=0.25 vs x=1.0; may need to widen `x_min` filter. |
| `cf_x_profile_n_samples < 2` | `cf_extractor_x_aliasing` | x_tol too tight or mesh sparser than expected at target x's. Inspect cell density at x ∈ {0.25, 0.5, 0.75, 1.0}. |
| Solver diverges | `openfoam_version_emitter_api_drift` HIGH | Check `constant/momentumTransport` filename + simpleFoam config drift. Sub-arc per V61-059 precedent. |
| `delta_99_at_x_*_error` (profile fails to reach 0.99·U_∞) | mesh under-resolved at far-wall | Check ncy + grading; intake §3a.evidence_ref claims 80 ycells with 4:1 grading is sufficient. |

## 4. Rollback plan

If Stage B fails after R3 (Codex APPROVE on Stage A code but live run breaks):
1. Capture full log + raw_run JSON in `reports/phase5_audit/`.
2. Tag as a post-R3 defect per RETRO-V61-053 protocol — addendum required.
3. Classify defect type:
   - **accessor/attribute-dereference**: code review missed a structure mismatch
     (Codex blind spot for emit-shape correctness on real OpenFOAM output)
   - **runtime-emergent**: solver divergence, mesh issue, OpenFOAM API drift
4. Open a sub-arc DEC if remediation needs >100 LOC across >2 files
   (V61-059 Stage B sub-arc precedent).

## 5. Stage E (closeout) preconditions

After Stage B PASS:
- [ ] Frontend Compare-tab anchor cards (deferred per intake §3b)
- [ ] DEC-V61-063 frontmatter: `notion_sync_status`, `codex_tool_report_path`
- [ ] V61-063 closeout retro (counter +1, post-R3 defect addendum if any)
- [ ] Notion sync of DEC-V61-063 page
- [ ] STATE.md update with V61-063 landed
- [ ] external_gate_queue.md update if any external gates queued

## 6. Decision points

| Branch | Action |
|---|---|
| Codex round 1 = APPROVE | Execute §1 immediately |
| Codex round 1 = APPROVE_WITH_COMMENTS, comments ≤2 LOC verbatim | Land verbatim, execute §1 |
| Codex round 1 = APPROVE_WITH_COMMENTS, comments larger | Address as round 1.5, re-confirm with codex (round 2 budget) |
| Codex round 1 = CHANGES_REQUIRED | Address findings → round 2 (4-round budget remaining = 3) |
| Codex consumes 4 rounds without APPROVE | Halt + human review per RETRO-V61-053 |
