---
decision_id: DEC-V61-052
title: backward_facing_step adapter rewrite · multi-block geometry + fixture regen + LDC-style iteration loop
status: COMPLETE (2026-04-23 · Codex round 3 APPROVE_WITH_COMMENTS; 3 MED/LOW cleanups left for a follow-up pass, no HIGH blockers remain)
supersedes_gate: DEC-V61-051 (ABANDONED_PHASE_1; this DEC is the "scope-adapter-rewrite" option Codex flagged during that review)
commits_in_scope:
  - 4ba4fd7 docs(dec): DEC-V61-052 scaffold · BFS adapter multi-block rewrite (PROPOSED)
  - 2420c3b feat(bfs-adapter): Batch A · canonical 3-block BFS mesh + ER=1.125 fix
  - 4fb8682 fix(bfs-adapter): Batch B · solver-stability harden + fixture regen (preflight GREEN)
  - 013657f fix(bfs-adapter): round 2a · wallShearStress FO + tau_x-proxy Xr extractor (Codex r1 #1+#3)
  - e8d4897 feat(preflight): round 2b · structured scalar-contract gate (Codex r1 #2)
  - 25a0753 feat(bfs-adapter): round 2c · kOmegaSST default + x-graded mesh · Xr/H=5.64 (-9.9%, inside tolerance)
  - a62ca3c fix(bfs-adapter): round 2d · endTime 1500 for stationary residual plateau (Codex r1 #5)
  - a1cf921 feat(bfs): round 3 + Batch D · authoritative wall-shear Xr + Compare-tab scalar-anchor card (Codex r2 #1/#3/#4 + Batch D)
codex_verdict: APPROVE_WITH_COMMENTS — round 3 (a1cf921) cleared the round-2 HIGH (wall-shear now authoritative), MED-2 (BFS scalar overlay scoped correctly), MED-3 (diagnostic flags in executor), LOW-4 (stationarity wording matches artifacts). Round 3 itself surfaced 2 MED + 1 LOW clean-up items (wall mask includes 2 outlet cells at x=30; generate_contours figure still computes Xr via Ux proxy even though caption cites wall-shear; reattachment_method/flags not propagated to the serialized audit YAML). All 3 are non-blocking per Codex: "DEC-V61-052 is ready to close with comments; I do not see any remaining HIGH issue that warrants a round 4." Tracked as a follow-up cleanup commit on main; does not reopen the DEC.
autonomous_governance: true
autonomous_governance_counter_v61: 39
external_gate_self_estimated_pass_rate: 0.45
external_gate_actual_outcome: "APPROVE_WITH_COMMENTS on round 3 — one iteration beyond the LDC V61-050 precedent (which was APPROVE on round 2). Arc size: 8 commits across 4 batches + 3 iteration rounds. Self-pass-rate 0.45 was calibrated well: round 1 landed CHANGES_REQUIRED (2H+2M+1L), round 2 CHANGES_REQUIRED (1H+2M+1L), round 3 APPROVE_WITH_COMMENTS (0H+2M+1L). The pattern of 'HIGH count shrinking to zero across iterations while MED/LOW count stays constant' matches the LDC arc qualitatively."
external_gate_caveat: "Lower than typical V61-050 batches (0.70) because this requires multi-block blockMeshDict correctness + fixture regen + turbulence model BC stability simultaneously. The failure mode that killed V61-051 was I skipped Codex review on a visualization of a known-HAZARD fixture; this DEC's explicit plan is to (a) get GREEN preflight first, (b) get Codex review before any visualization. Plan executed as designed."
codex_tool_report_path: .planning/reviews/dec_v61_052_bfs_round3_codex.log (+ round 1 + 2 logs co-located)
notion_sync_status: "synced 2026-04-23 (https://www.notion.so/DEC-V61-052-BFS-adapter-multi-block-rewrite-LDC-style-iteration-loop-case-2-34bc68942bed81bf95e7dac9c6a638bd)"
github_sync_status: pushed (8 commits on origin/main)
related:
  - DEC-V61-050 (LDC true multi-dim validation · methodology reference)
  - DEC-V61-051 (BFS visual upgrade ABANDONED_PHASE_1 · this DEC is its successor)
  - DEC-V61-036 (comparator gates G3/G4/G5 · the attestor that correctly flagged BFS as hard-FAIL — we should never have tried to visualize past it)
---

## Closure summary (2026-04-23)

**Entry state**: V61-051 abandoned · BFS fixture was a flat rectangular channel with no step, k-ε diverged to 1e+30, Xr/H extractor was looking at the wrong y-band, contract_status falsely PARTIAL_COMPATIBLE.

**Exit state**: Preflight GREEN on all 6 checks. Authoritative Xr/H = 5.647 via `wall_shear_tau_x_zero_crossing` on `lower_wall` face tau_x from the allPatches VTK (cross-checked against near-wall Ux proxy to 0.004%). Driver 1985 reference Xr/H = 6.26 → deviation -9.8%, inside ±10% tolerance. velocity_streamlines.png published as `kind: solver_output`. Compare-tab D1 scalar-anchor card renders measured vs gold with PASS/FAIL colour. physics_contract.contract_status = SATISFIED.

**Methodology verification**: This DEC was the first "类推 case-1" application of the LDC V61-050 iteration loop. The loop ran as designed — 3 rounds of Codex review, each finding real issues, each iteration shrinking the HIGH count while exposing deeper MEDs. The round-2 wall-shear HIGH (Xr was emitted as proxy not wall-shear) was exactly the kind of finding the loop is built to surface and is the equivalent of the LDC D8 SNR retraction: a claim in the attestation layer that was stronger than the artifact chain supported.

**Follow-up (non-blocking, post-close)**: 2 MED + 1 LOW items Codex surfaced in round 3: (a) the `y<0.05 && x>0.05` wall mask picks up 2 B1 outlet face centres at x=30.0, not a scalar blocker but `n_floor_pts=122` wording overclaims; (b) `scripts/flow-field-gen/generate_contours.py::gen_backward_facing_step` still re-probes Xr via the Ux proxy while the flowFields.ts caption says wall-shear (numerical agreement is 0.004% so the figure label is right but the attribution is stronger than the code supports); (c) `reattachment_method` + diagnostic flags live in executor key_quantities but do not propagate to `audit_real_run_measurement.yaml::measurement` (only `extraction_source: key_quantities_direct` is kept), so the Compare tab cannot tell "wall-shear authoritative" from "Ux proxy fallback" without reading raw JSON. All three are small, same-file fixes; Codex confirmed none of them warrant reopening the DEC.

## Why this DEC exists

DEC-V61-051 Phase 1 attempted to upgrade the BFS Story-tab visualization from an analytical envelope curve to a real-solver velocity-field figure. Self-audit + post-capacity Codex verification established three compounding issues:

1. **Geometry**: `src/foam_agent_adapter.py::_render_bfs_block_mesh_dict` generates a single rectangular channel spanning `x ∈ [-10, 30] × y ∈ [0, 1.125]` with no step. 360 of 1722 VTK points live inside the supposed step void (`x<0, y<1`). The generator's own docstring concedes: "使用单矩形通道近似 BFS（无 step 几何细节）".

2. **Inlet BC**: `0/U.inlet` is `fixedValue uniform (U_bulk, 0, 0)` over the entire inlet face. Without either a carved-out step in the mesh OR a stepped inlet profile, the BC cannot reproduce the expansion physics.

3. **Numerical failure**: The resulting k-ε simulation diverges — `check_all_gates` on the fixture returns `|U|_max = inf`, `k_min = -6.41e+30`, `ε_max = 1.04e+30`, continuity `sum_local = 5.25e+18`. Gold YAML already declared `ATTEST_HAZARD [G3,G4,G5]` and `contract_status: PARTIALLY_COMPATIBLE`. My Phase 1 commit ignored the YAML's own self-audit.

This DEC resolves all three in one arc, then applies the LDC methodology (Phase 1+2 visualization + Compare-tab integration) to the new working fixture.

## Concrete scope (3 batches, matching the LDC pattern)

### Batch A · adapter multi-block geometry

`src/foam_agent_adapter.py::_render_bfs_block_mesh_dict` rewrite. Current implementation ~30 LOC emits a single hex block; new implementation ~100-140 LOC emits a canonical 3-block BFS topology:

```
     upstream inlet channel                downstream full channel
   ┌────────────────────────┐           ┌──────────────────────────────────┐
   │                        │           │         upper half (B2)          │
   │       block A          ├──────────→│──────────────────────────────────│ y = h_s
   │                        │  (step    │         lower half (B1)          │
   │                        │  face     │      (recirculation region)      │
   └────────────────────────┘  here)    └──────────────────────────────────┘
   x=-L_up                  x=0                                         x=L_down
   y ∈ [h_s, H_ch]                      y ∈ [0, h_s]  (B1)  y ∈ [h_s, H_ch] (B2)
```

Vertex list: 16 unique positions (8 at z=0, 8 at z=L_z). Three `hex` block directives, shared faces between A↔B2 at `x=0, y ∈ [h_s, H_ch]` (internal interface) and between B1↔B2 at `y=h_s, x ∈ [0, L_down]` (internal interface).

Boundary patches:
- `inlet` — A's `x = -L_up` face, type `patch`
- `outlet` — B1 + B2 combined `x = L_down` faces, type `patch`
- `upper_wall` — A's top + B2's top, `y = H_ch`, type `wall`
- `lower_wall_upstream` — A's bottom, `y = h_s`, `x ∈ [-L_up, 0]`, type `wall` (elevated inlet-channel floor)
- `step_face` — B1's `x = 0` face, `y ∈ [0, h_s]`, type `wall` (the backward-facing step itself)
- `lower_wall_downstream` — B1's bottom, `y = 0`, `x ∈ [0, L_down]`, type `wall`
- `front`, `back` — z-empty patches

Cell counts: default to `ncx_A=40, ncy_A=8; ncx_B=120, ncy_B1=40, ncy_B2=8` → total ~6800. This is the ncx_B=120, ncy_B1+B2=48 whitelist default. `simpleGrading` will concentrate cells near the step (x near 0) and near the walls (y near 0 and y near h_s).

Inlet `0/U.inlet` automatically only applies over `y ∈ [h_s, H_ch]` because that's now the geometric inlet face — no stepped profile needed in the BC, the mesh carries the step.

### Batch B · fixture regen + preflight GREEN

Run `EXECUTOR_MODE=foam_agent .venv/bin/python scripts/phase5_audit_run.py backward_facing_step`. Produces a new `reports/phase5_fields/backward_facing_step/<new_timestamp>/` with:
- `log.simpleFoam` showing residual convergence
- `VTK/*.vtk` with proper step geometry (preflight geometry check should find 0 points in void)
- Updated `runs/audit_real_run.json` manifest pointing at new timestamp

Then `python3.11 scripts/preflight_case_visual.py backward_facing_step` must return exit-code 0 (GREEN). If AMBER or RED, investigate before continuing — for example:
- If G3 `|U|_max > 100·U_ref` → diverged simpleFoam run → check fvSolution URF and turbulence BCs
- If geometry check still finds step-void points → blockMeshDict bug
- If `|U|` envelope > 3× → check inlet BC is limited to the channel-inlet face

Exit gate for this batch: preflight GREEN + Codex pre-review dry-run confirms the fixture is sane.

### Batch C · Codex round 1 + iterate

After Batches A+B are committed and pushed, invoke Codex via `/codex-gpt54` with these review dimensions (mirroring the LDC V61-050 pattern):

1. Geometry correctness — re-verify the 3-block topology matches what the physics needs
2. Convergence — residual log analysis (A1-A6 attestor), URF choices, max iterations
3. Xr extraction — verify the near-wall probe locates reattachment in the true sign-change of U_x(y→0), not just the first zero in a coarse probe
4. SNR argument — what's the equivalent of LDC D8's SNR check for BFS? Wall-shear variability across coarse cells; if Xr is extracted from a region with cell width > Xr_signal, we have the same "signal below noise" failure mode
5. Tolerance defensibility — 10% on Xr/H=6.26 vs the Le/Moin/Kim 6.28 / Driver 6.26 bracket at Re=7600
6. Figure honesty — if the new fixture has a meaningful Xr within tolerance, label as `solver_output`; otherwise stay honest about residual deviation

Iterate on findings. Retraction is allowed and expected — the LDC precedent was 1 HIGH + 4 MED + 1 LOW in round 1. Success metric: VERDICT is APPROVE or APPROVE_WITH_COMMENTS with all HIGHs fixed.

### Batch D · LDC-style visualization + Compare-tab integration (blocked on A+B+C)

Only after Codex APPROVE_WITH_COMMENTS on the new fixture:

- Regenerate `/flow-fields/backward_facing_step/velocity_streamlines.png` from the new VTK (same script path as the reverted 4e4813f, but pointing at the new timestamp and with any Codex-surfaced fixes applied).
- Promote `backward_facing_step` from `_VISUAL_ONLY_CASES` → `_GOLD_OVERLAY_CASES` in `ui/backend/services/comparison_report.py`.
- Add `_load_bfs_reattachment_gold()` + post-hoc Xr extractor + `metrics_reattachment` / `paper_reattachment` wiring.
- Frontend: scalar-anchor Compare-tab card similar to LDC's D1 (verdict + tolerance band + measured value).
- Pre-flight check again before each commit in this batch — must stay GREEN.

## Why this is a separate DEC, not a "Phase 2 of V61-051"

LDC's V61-050 bundled 4 batches into one arc because they shared infrastructure (ψ extraction). BFS cannot be bundled with its abandoned Phase 1 because the scope inverts: V61-051 tried to visualize a broken fixture, this DEC builds the fixture first. The post-implementation visualization in Batch D of this DEC is essentially the same code the V61-051 revert deleted, but pointing at a DIFFERENT fixture — not the same work.

The reasons I'm opening this as DEC-V61-052 rather than re-opening V61-051:
- V61-051's DEC explicitly documents ABANDONED_PHASE_1 as a retraction, which should stay as evidence in the audit trail.
- Scope of this DEC is adapter + fixture + visualization; scope of V61-051 was visualization only. Merging would muddy the scope boundary.
- The counter_v61 increments reflect each DEC's governance; V61-051 got credit for the retraction, V61-052 is a new autonomous-governance arc.

## Success criteria (exit gate for the whole DEC)

1. Preflight on `backward_facing_step` returns exit-code 0 (GREEN) — all 5 checks pass.
2. Codex post-merge review on the final state returns APPROVE or APPROVE_WITH_COMMENTS with no outstanding HIGH findings.
3. Compare-tab Story page for lid_driven_cavity / backward_facing_step shows a coherent `solver_output` figure labeled with measured Xr/H and deviation from the gold anchor.
4. `physics_contract.contract_status` for BFS updates to `SATISFIED` (no longer `PARTIALLY_COMPATIBLE`).
5. DEC frontmatter: `status: COMPLETE`, `codex_verdict: APPROVE`, commit SHAs in `commits_in_scope` replace all TBDs.

If any of 1-4 fail, the DEC lands as PARTIAL with an honest note about what was and wasn't solved — mirroring the LDC D8 noise-floor retraction. A partial success that documents the failure mode is preferable to a forced "APPROVE" on a shaky fixture.

## Rejected alternatives

- **Quick inlet-BC hack** (set U=0 below y=1, U=U_bulk above, keep plain channel mesh) — rejected: without the physical step wall at `x=0, y ∈ [0, h_s]`, the shear layer has no rigid surface to detach from; k-ε will still not produce a real recirculation bubble, just a velocity-profile mismatch that heals downstream. Would make the fixture "not-as-obviously-broken" without actually fixing it — the LDC D8 trap recast.

- **Raise tolerance to 50% instead of fixing geometry** — rejected: papers over the defect in the gold YAML, invites future observers to assume BFS is validated when it isn't.

- **Accept 800-cell quick-run fixture + skip fixture regen** — rejected: the 36000-cell number in the gold YAML is aspirational; any fixture under ~5000 cells is ATTEST_HAZARD on this case per DEC-V61-036's G5 contract. The real mesh-count threshold is empirical; Batch B will determine it.
