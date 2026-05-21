# Negative tests — flat_plate_rans_sst

Negative tests are seeded *bad* cases that the trust loop MUST catch.
A trust harness without negative tests is just a green-light generator.

## Planned seeded bad cases (Phase 1)

Each subdirectory below will contain a deliberately broken variant of the
flat plate case manifest and/or artifacts. The trust loop is expected to
return `FAIL` or `WARN` for each.

1. `missing_wall_patch/` — `geometry_contract.required_patches` omits `wall`
2. `inlet_outlet_swapped/` — inlet/outlet BCs swapped
3. `wrong_unit_scale/` — geometry declared in `mm` when manifest says `SI`
4. `coarse_mesh/` — checkMesh produces unacceptable non-orthogonality
5. `bad_nonorthogonality/` — synthetic mesh report with `max_non_orthogonality > 75`
6. `wrong_turbulence_bc/` — `kqRWallFunction` swapped for `fixedValue`
7. `missing_turbulence_field/` — `bc_contract.turbulence_fields` missing `omega`
8. `residual_converged_but_qoi_unstable/` — residuals look fine, QoI window drifts
9. `missing_reference_comparison/` — `reference_comparison.status: missing`
10. `AI_explanation_without_evidence/` — AI advisor claim with no artifact pointer

## Phase 0 status

**Scaffold only.** None of the above subdirectories are populated yet.
Tests in `tests/test_negative_cases.py` assert that the harness *would* fail
on a manifest with missing required sections. Real seeded subdirectories
land in Phase 2.
