# Negative Test Policy

A trust harness without negative tests is a green-light generator.

## Definition

A negative test is a deliberately broken variant of a real case for which the
expected outcome of the trust loop is `FAIL` or `WARN`. The variant is sealed
in `cases/<case>/negative_tests/<defect>/` and exercised by `pytest`.

## Required defect classes (must be covered by Phase 2)

1. **Schema-breaking defects** — required field removed or malformed.
2. **Patch-name defects** — `wall` patch missing or renamed.
3. **Unit-system defects** — units inconsistent with declared `unit_system`.
4. **Mesh-quality defects** — `max_non_orthogonality > 75` or skewness violation.
5. **Wall-treatment defects** — wall function swapped for inappropriate type.
6. **Turbulence-field defects** — declared turbulence field missing from BCs.
7. **Convergence-illusion defects** — residuals converge but QoI window drifts.
8. **Reference-missing defects** — `reference_comparison.status == missing`.
9. **AI-hallucination defects** — advisor output references an artifact that does not exist.

## Verdict expectations

For each defect, the trust loop must produce a specific verdict:

| defect class | expected gate to FAIL/WARN |
|---|---|
| schema-breaking | `validate-manifest` exits non-zero |
| patch-name | `gates.geometry_contract.status == FAIL` |
| unit-system | `gates.geometry_contract.status == FAIL` or WARN |
| mesh-quality | `gates.mesh_contract.status == FAIL` |
| wall-treatment | `gates.bc_contract.status == FAIL` |
| turbulence-field | `gates.bc_contract.status == FAIL` |
| convergence-illusion | `gates.solver_execution.status == WARN` or FAIL via qoi_stability |
| reference-missing | `gates.reference_comparison.status == FAIL` |
| AI-hallucination | Red Team review catches it; an automated check is added once the advisor lands |

## Process

1. `benchmark-director` writes the broken manifest / artifact.
2. `test-red-team` writes the pytest test asserting the expected verdict.
3. `engineering-director` includes the test in CI.
4. `project-governor` accepts the addition to the matrix in `DECISION_LOG.md`.

## Anti-patterns

- "We don't need negative tests because the schema is strict enough" — schemas
  do not catch convergence-illusion or AI-hallucination defects.
- "We'll add negative tests after the first real validation" — too late.
- "Negative tests are flaky" — if they are, the harness is flaky; fix the harness.
