# Artifacts — flat_plate_rans_sst

## What lives here

The trust harness writes per-run evidence artifacts to this directory:

- `geometry_report.json` — geometry audit (Phase 0 mocked / Phase 1+ real)
- `mesh_report.json` — mesh audit (cell count, y+, skewness)
- `bc_audit.json` — boundary-condition audit against `case_manifest.yaml`
- `solver.log` — combined stdout+stderr from the OpenFOAM solver run (Phase 1 step 2c)
- `residuals.csv` — iteration-by-iteration residuals parsed from `solver.log`
- `qoi.csv` — extracted quantities of interest (Cf, Cd, etc.)
- `reference_comparison.csv` — QoI vs. reference data
- `trust_report.json` — aggregated gate status across the whole trust loop

## Provenance rule

A `trust_report.json` that cites a missing artifact MUST be treated as invalid.
The cockpit's `F-08` filter and `test_pass_event_evidence_paths_exist_on_disk`
enforce this contract: every PASS event must reference an evidence path that
exists on disk.

## Mocked execution

In Phase 0 the solver is mocked. When mocked, `trust_report.json` carries:

- `solver_execution: mocked`
- `validation_status: not_validated`

and the limitations array explicitly states no validation is claimed.

## Reproducing

```bash
cfdtrust run cases/flat_plate_rans_sst
cfdtrust report cases/flat_plate_rans_sst
```

This README is itself an evidence artifact for `PH0-CASE-001` and must remain
present (its deletion is a regression that the F-08 filter will surface).
