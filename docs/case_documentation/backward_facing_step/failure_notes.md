# Failure notes — backward_facing_step

> Free-form yaml/markdown — not a P4 KOM schema artifact.

## FM-BFS-1: Single-block adapter produced flat channel (no step)

- **Tag**: `geometry_metadata_lie`
- **Trigger**: pre-DEC-V61-052 adapter generated `channel_height = 1.125·H`, single block — produced a flat duct with no step at all
- **Symptom**: solver converged but the field had no recirculation; Xr extraction undefined; YAML claimed 1.125 expansion ratio but the mesh was a flat channel
- **Detected**: DEC-V61-051 audit (2026-04-23 era)
- **Status**: RESOLVED — DEC-V61-052 rewrote the adapter to a 3-block topology (inlet H_inlet=8H + downstream channel H=9H), producing a real BFS field (15154 pts, 0 points in step void, |U|_max = 1.04·U_bulk)

## FM-BFS-2: k-ε divergence to 1e+30

- **Tag**: `solver_blowup_unbounded`
- **Trigger**: kEpsilon RAS model + unbounded scheme + no wall function → k and ε diverged to 1e+30 within hundreds of iterations
- **Symptom**: ATTEST_HAZARD on residual checks; no useful field emitted
- **Detected**: pre-DEC-V61-052
- **Status**: RESOLVED — DEC-V61-052 round 2c switched default RAS model to kOmegaSST + bounded linearUpwind + Spalding wall function. kEpsilon retained as `wrong_model` diagnostic via boundary_conditions.turbulence_model override (Xr/H = 3.99, -36.3% miss).

## FM-BFS-3: Misaligned Xr probe

- **Tag**: `extraction_probe_geometry_drift`
- **Trigger**: Xr extractor sampled along a y-coordinate that did not coincide with the lower wall after the geometry rewrite
- **Symptom**: Xr returned 0 or arbitrary values
- **Detected**: DEC-V61-052 round 2 audit
- **Status**: RESOLVED — Round 3 (Codex r2 #1) landed wall-shear τ_x zero-crossing extractor reading `lower_wall` patch face values from the allPatches VTK; cross-checked by near-wall Ux proxy (4-digit agreement)

## FM-BFS-4: No wall-shear measurement in earlier extractor

- **Tag**: `missing_wall_quantity`
- **Trigger**: Earlier Xr extraction inferred reattachment from u-velocity sign change in cell centres rather than wall shear
- **Symptom**: cell-centre method is mesh-resolution-dependent and noisier than wall-face τ_x sign change
- **Detected**: DEC-V61-052 round 3
- **Status**: RESOLVED — wall-shear extractor is now authoritative; cell-centre method remains as cross-check

## Pattern themes

- **geometry_metadata_lie**: YAML / whitelist claims geometry G but adapter generates G' that passes type checks. Recurs at LDC (mesh cell count placeholder), duct_flow (pipe→duct rename), impinging_jet (planar slice not axisymmetric). P4 should encode `geometry_assumption_validator: callable` that asserts mesh shape matches declared topology.
- **solver_blowup_unbounded**: aggressive schemes + unphysical RANS configuration → divergence. P4 PreFlight gate should include scalar-field bounds check before t > 0.
- **extraction_probe_geometry_drift**: extractor coordinates hardcoded to a previous mesh layout. Suggests P4 extractors should declare `mesh_topology_dependency` and re-validate when adapter geometry changes.
