# Benchmark Matrix

Owned by `benchmark-director`. Lists cases the project will ship, in priority order.

| case_id | family | purpose | phase | reference status |
|---|---|---|---|---|
| `flat_plate_rans_sst` | canonical_rans_verification | most-cited k-omega SST verification; minimum viable trust loop | Phase 0–1 | placeholder (OQ-0001) |
| `bump_in_channel_rans` | canonical_rans_verification | second SST verification benchmark; tests pressure-gradient handling | Phase 2 | planned |
| `backward_facing_step` | canonical_separated_flow | classic separation case; exercises mesh and BC discipline | Phase 2 | planned |
| `naca0012_rans` | external_aero_rans | tests external aero conventions (Reynolds, AoA, force coefficients) | Phase 3 | planned |
| `motorbike_workflow_smoke_test` | workflow_smoke | OpenFOAM tutorial-grade workflow exerciser; **not** a scientific validation case | Phase 1 | n/a (workflow only) |

## Status meanings

- **placeholder**: case manifest exists, reference dataset not selected
- **planned**: case is on the roadmap, no manifest yet
- **finalized**: reference dataset cited and licensed
- **workflow_smoke**: case exists only to exercise the harness end-to-end; no validation claim is made

## Hard constraints

1. **motorbike is NOT validation.** It is a workflow smoke test. Any trust_report
   for motorbike must keep `validation_status: not_validated` regardless of how
   pretty its residuals look.
2. **No new case is added without a reference plan.** Adding a benchmark without
   a path to its reference dataset is wishful thinking.
3. **No reference dataset is "selected after the run."** If the reference is
   chosen post-hoc, the case is invalid.

## Sequencing rationale

- flat plate first: minimum case to exercise every gate of the trust loop.
- motorbike second: proves the harness can drive OpenFOAM workflows end-to-end.
- bump in channel + backward-facing step: two physically richer cases that catch
  failure modes flat plate cannot expose (pressure gradient, separation).
- NACA0012 last among canonical: introduces external-aero conventions that the
  harness must learn to express in `case_manifest.yaml`.
