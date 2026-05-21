# CFD Correctness Philosophy

## Core statement

> A CFD case is not correct because it runs.
> A CFD case is correct only if it passes its explicit case contract.

## Verification vs validation

**Verification** answers: "Did we solve the equations right?"
- Mesh independence study performed.
- Discretization error characterized.
- Residuals reach target.
- Iteration / time-step convergence demonstrated.
- Code-level unit tests on solver wrappers pass.

**Validation** answers: "Did we solve the right equations?"
- Computed QoIs compared against measured / accepted reference values.
- Tolerance defined a priori, not chosen to make the case pass.
- Reference dataset cited and licensed.

Verification without validation is "I converged something." Validation without
verification is "It matched the answer once."

## What is NOT validation

- residual convergence alone
- mesh quality alone (`checkMesh` PASS)
- a single QoI value within tolerance with no mesh study
- agreement after the reference was chosen post-hoc
- agreement when the case contract was relaxed mid-run
- agreement when the AI advisor "explained" why outliers don't count

## Residual convergence is not physical validation

Residuals can go to machine zero on a physically nonsensical case (wrong BCs,
wrong units, wrong physics). Residual convergence is necessary but not
sufficient. The trust loop must record both `solver_contract.residual_targets`
and `solver_contract.qoi_stability`; the QoI stability gate catches the
"residuals look fine, QoI drifts" failure mode.

## Mesh quality is necessary but not sufficient

`checkMesh` passing means the mesh is geometrically usable. It does not mean
the mesh resolves the physics. Boundary-layer mesh adequacy + y+ targeting +
mesh independence study are required to claim "the mesh is appropriate to the
physics."

## Reference comparison is required for validation claims

A `trust_report.json` may not carry `validation_status: validated` unless:

- a reference dataset is cited (`reference_comparison.source` is non-empty)
- a tolerance was set before the run (`reference_comparison.tolerance` defined
  in `case_manifest.yaml`)
- the comparison artifact (`reference_comparison.csv`) exists and shows
  agreement within tolerance.

If any of those are missing, the report stays `not_validated`.

## Trust report status semantics

| status | meaning |
|---|---|
| PASS | every gate PASS, real solver, reference comparison within tolerance |
| WARN | recoverable issue noted; case may proceed but flag is recorded |
| FAIL | at least one gate fails outright |
| BLOCKED | external blocker prevents a gate from running |
| MOCKED | the solver and/or reference is mocked; not a validation result |

A trust report is allowed to be MOCKED. It is never allowed to be PASS based on
a mocked run. Tests enforce this.

## When an operator and the AI advisor disagree

The operator wins. The advisor records its opinion as a recommendation, not as a
modification to the case. The advisor never edits artifacts.
