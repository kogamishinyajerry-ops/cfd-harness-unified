# Case Contract Specification

The case contract is a machine-readable description of every assumption a CFD case
depends on. It lives in `case_manifest.yaml` at the case directory's root and is
validated by `src/cfdtrust/schemas/case_manifest.schema.json`.

## Required top-level fields

| field | type | purpose |
|---|---|---|
| `case_id` | string | unique within the repo |
| `case_family` | string | groups cases (e.g. `canonical_rans_verification`) |
| `solver_backend` | `openfoam` \| `mocked` | which adapter will run |
| `solver` | string | e.g. `simpleFoam`, `pimpleFoam` |
| `physics` | object | regime, fluid, turbulence model, compressibility, steadiness |
| `geometry_contract` | object | required patches, dimensionality, units |
| `mesh_contract` | object | checkMesh, BL, y+, quality thresholds |
| `bc_contract` | object | inlet, outlet, wall, turbulence_fields |
| `solver_contract` | object | residual targets, max iterations, QoI stability |
| `qoi` | array | quantities of interest, kind, units, tolerance |
| `reference_comparison` | object | dataset status, source, tolerance |
| `required_artifacts` | array | which files the trust loop must emit |

## Rules

1. **Every assumption is explicit.** "Of course we use SI" is not allowed; declare it.
2. **Tolerances exist before runs.** `qoi[].tolerance` and `reference_comparison.tolerance`
   are part of the contract, not chosen after the fact.
3. **Required patches are listed.** Geometry audit will check each one.
4. **Turbulence fields are listed.** BC audit will check each one.
5. **QoI stability is explicit.** The solver gate checks the QoI over a window of
   iterations, not just terminal residuals.

## Anti-patterns

- "I'll add turbulence fields later" — the contract must be complete before run.
- "Tolerance to be determined" — TBD is not a tolerance.
- "Reference dataset same as the last case" — must be cited explicitly.

## Evolution

When a contract field needs to be added or changed:

1. The system-architect updates `case_manifest.schema.json`.
2. The cfd-vv-director ratifies the change in `DECISION_LOG.md`.
3. Existing cases that fail the new schema are visibly broken until repaired.

The contract is a covenant. We do not retroactively soften it to make cases pass.
