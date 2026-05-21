# Validation Policy

Governs when a `trust_report.json` is allowed to claim `validation_status: validated`.

## Pre-conditions for `validation_status: validated`

All of the following must hold:

1. `solver_execution == "real"` — no mocked solver.
2. `case_manifest.yaml > reference_comparison.status == "finalized"`.
3. A reference dataset is cited in `cases/<case>/reference/provenance.md` with
   source URL or DOI, license, and date of access.
4. `qoi.csv` and `reference_comparison.csv` exist and are populated with real values.
5. Every declared QoI in `case_manifest.yaml > qoi[]` is present in
   `reference_comparison.csv` with `within_tolerance == True`.
6. A mesh independence study exists at `cases/<case>/artifacts/mesh_independence.md`.
7. The `solver_contract.qoi_stability` gate passes (QoIs stable over the declared
   iteration window within `relative_drift_tolerance`).
8. Red Team has filed a passing review for the case in `docs/status/red_team_<case>.md`.

If any of (1)–(8) is missing, `validation_status` stays one of `not_validated`,
`partial`, or `unknown`.

## What cannot promote a report to `validated`

- residuals reaching target alone
- `checkMesh` PASS alone
- agreement with a dataset selected after the run
- a `case_manifest.yaml` whose tolerance was widened mid-run
- the AI advisor declaring the result reasonable
- the operator's intuition

## What downgrade rules apply

A previously `validated` report **must** be downgraded if:

- the reference dataset is found to be misapplied (units, regime, etc.)
- the mesh independence study is found to be insufficient
- the case manifest tolerances were silently widened
- the solver wrapper changed without a re-run

Downgrade goes through `DECISION_LOG.md` and is reflected in PROGRESS.md.

## Mocked is not partial

`MOCKED` does not mean "almost validated." A mocked report has no scientific
weight. It exists only to demonstrate the trust loop infrastructure.
