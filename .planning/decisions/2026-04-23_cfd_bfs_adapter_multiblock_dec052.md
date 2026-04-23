---
decision_id: DEC-V61-052
title: backward_facing_step adapter rewrite · multi-block geometry + fixture regen + LDC-style iteration loop
status: PROPOSED (scope committed · implementation follows in subsequent commits within this DEC)
supersedes_gate: DEC-V61-051 (ABANDONED_PHASE_1; this DEC is the "scope-adapter-rewrite" option Codex flagged during that review)
commits_in_scope:
  - TBD draft: adapter multi-block blockMeshDict generator
  - TBD draft: fixture regen via phase5_audit_run.py (yields new timestamp under reports/phase5_fields/backward_facing_step/)
  - TBD audit: preflight_case_visual.py must flip BFS from RED → GREEN
  - TBD Codex round 1: post-merge review with retry-on-capacity + honest iteration
  - TBD round-N fixes: whatever Codex surfaces (LDC precedent was HIGH + 4 MED + 1 LOW)
  - TBD LDC-style visualization: real |U|+streamlines figure from the NEW fixture, matching the post-DEC-V61-051 pattern we discarded
  - TBD Compare-tab wiring: promote to _GOLD_OVERLAY_CASES and surface Xr as scalar-anchor dimension
codex_verdict: (pending — loop starts on the first implementation commit)
autonomous_governance: true
autonomous_governance_counter_v61: 39
external_gate_self_estimated_pass_rate: 0.45
external_gate_caveat: "Lower than typical V61-050 batches (0.70) because this requires multi-block blockMeshDict correctness + fixture regen + turbulence model BC stability simultaneously. The failure mode that killed V61-051 was I skipped Codex review on a visualization of a known-HAZARD fixture; this DEC's explicit plan is to (a) get GREEN preflight first, (b) get Codex review before any visualization."
codex_tool_report_path: (pending round 1)
notion_sync_status: pending
github_sync_status: pending
related:
  - DEC-V61-050 (LDC true multi-dim validation · methodology reference)
  - DEC-V61-051 (BFS visual upgrade ABANDONED_PHASE_1 · this DEC is its successor)
  - DEC-V61-036 (comparator gates G3/G4/G5 · the attestor that correctly flagged BFS as hard-FAIL — we should never have tried to visualize past it)
---

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
