# Failure notes — lid_driven_cavity

> Free-form yaml/markdown — not a P4 KOM schema artifact.
> Captures observed failure modes for downstream FailurePattern schema design.

## FM-LDC-1: Phase 0 synthesized gold (retired)

- **Tag**: `synthesized_gold_no_cross_check`
- **Trigger**: gold-value transcription without cross-verifying against the cited paper
- **Symptom**: prior `u_centerline` claimed Ghia 1982 authorship but reported u = +0.025 at y=0.5; Ghia actual is -0.20581 (sign-error + value-error)
- **Detected**: Phase 5a real-solver run (2026-04-21, DEC-V61-030)
- **Status**: RESOLVED — Q-5 Path A re-transcribed Ghia Table I to the harness's 17-point uniform y grid

## FM-LDC-2: Mislabeled v_centerline axis

- **Tag**: `axis_label_swapped`
- **Trigger**: Ghia Table II data indexed by "y" instead of "x" along the horizontal centerline
- **Symptom**: arbitrary-looking values not matching Ghia at either y-index or x-index
- **Detected**: 2026-04-23 (DEC-V61-050 batch 1)
- **Status**: RESOLVED — replaced with Ghia native 17-point non-uniform x grid + exact Table II v values

## FM-LDC-3: Mis-aligned primary vortex coordinates

- **Tag**: `geometry_misalignment`
- **Trigger**: previous gold reported (x=0.5, y=0.765) for primary vortex at Re=100, doesn't match Ghia Table III (0.6172, 0.7344)
- **Detected**: 2026-04-23 (DEC-V61-050 batch 3)
- **Status**: RESOLVED — wired 2D-argmin-of-ψ extractor (`ui/backend/services/psi_extraction.py`) integrating ψ = ∫₀^y U_x dy' on 129² resampling; smoke-tested to within 0.23% on |ψ_min|

## FM-LDC-4: Stream-function noise floor swallows secondary vortices

- **Tag**: `extraction_noise_floor_dominated`
- **Trigger**: corner eddies BL/BR have ψ_gold ~1e-6 / ~1e-5; the trapezoidal ∫ U_x dy' + pyvista resampling produces a wall-closure residual ≈ 3.4e-3 on the 20260421T082340Z fixture
- **Symptom**: argmax-found coordinates land near Ghia coords by coincidence of noise; physics not validated
- **Detected**: Codex round 1 MED #2 (2026-04-23, DEC-V61-050 batch 4)
- **Status**: ACKNOWLEDGED — comparator now gates `all_pass` on `signal_to_residual_ratio ≥ 3.0` (correctly reports `all_pass=False` for both eddies). True validation would require a Poisson solve `∇²ψ = -ω_z` with ψ=0 walls, OR OpenFOAM-native ψ sampling at the fixture mesh — both deferred to a future DEC.

## FM-LDC-5: Mesh-cell-count Phase 0 placeholder

- **Tag**: `mesh_metadata_placeholder`
- **Trigger**: `mesh_info.cells = 64800` from a Phase 0 placeholder did not match the 129×129 = 16641 Ghia mesh
- **Detected**: 2026-04-23 (DEC-V61-050 batch 1)
- **Status**: RESOLVED — corrected to 16641 across all four observable blocks (u_centerline, v_centerline, primary_vortex_location, secondary_vortices)

## Pattern themes (input to P4 FailurePattern schema)

- **synthesized_gold_no_cross_check**: gold values transcribed without checking the source — recurs across multiple cases (LDC, plane_channel, naca0012). Suggests P4 should have `gold_value_provenance: "transcribed_from_paper" | "synthesized" | "engineering_estimate"` field.
- **extraction_noise_floor_dominated**: when measurement quantity is many orders of magnitude smaller than the integration error, the comparator's "match within tolerance" can be coincidence. Suggests P4 needs a `signal_to_noise_floor` precondition for each observable.
- **axis_label_swapped** / **geometry_misalignment**: low-level metadata bugs that pass type-checks but produce silent wrong physics. Suggests P4 schema should encode `coordinate_axis` and `physical_meaning` per reference-value entry.
