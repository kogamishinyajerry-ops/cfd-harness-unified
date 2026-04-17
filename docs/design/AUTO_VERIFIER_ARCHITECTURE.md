# AutoVerifier Architecture Design

## Status

- Task: `AutoVerifier 架构设计 + Opus Gate 审查包准备`
- Phase: `8a-1`
- Prepared on: `2026-04-17`
- Scope of this task: design documents plus contract-aligned Gold Standard aliases
- Code changes in this task: `none`

## Architecture Overview

```text
TaskRunner
  -> execute CFD
  -> compare legacy gold standard as-is (existing behavior remains untouched)
  -> optional post_execute_hook(...)
       -> AutoVerifier
            -> ContractGoldLoader
                 -> contract alias YAML (OF-01/02/03)
                 -> legacy multi-document YAML fallback
            -> ResidualChecker
            -> GoldStandardChecker
            -> PhysicalPlausibilityChecker
            -> VerdictAggregator
            -> CorrectionSuggester (suggest-only)
            -> AutoVerifyReportWriter
                 -> reports/{case_id}/auto_verify_report.yaml
```

## Contract Alias Map

This task resolves the repo-versus-contract filename drift without touching legacy runtime files.

| Contract-facing file | Legacy repo source | Intent |
| --- | --- | --- |
| `knowledge/gold_standards/lid_driven_cavity_benchmark.yaml` | `knowledge/gold_standards/lid_driven_cavity.yaml` | Aggregate OF-01 observables into one contract YAML |
| `knowledge/gold_standards/backward_facing_step_steady.yaml` | `knowledge/gold_standards/backward_facing_step.yaml` | Aggregate OF-02 observables into one contract YAML |
| `knowledge/gold_standards/cylinder_crossflow.yaml` | `knowledge/gold_standards/circular_cylinder_wake.yaml` | Aggregate OF-03 observables into one contract YAML |

The alias files are additive shims for Phase 8 design and verification. Legacy multi-document YAML remains intact so Phase 1-7 behavior is not disturbed.

## Core Components

### AutoVerifier Orchestrator

- Single entry point for Phase 8 verification.
- Runs L1, L2, and L3 in a fixed order.
- Aggregates findings into one report object.
- Emits correction suggestions only when the final verdict is not `PASS`.

### ContractGoldLoader

- Prefers contract alias YAML for OF-01/02/03.
- Falls back to legacy Gold Standard YAML when alias files do not yet exist for a case.
- Normalizes observables into a single internal structure:
  - `name`
  - `ref_value`
  - `tolerance`
  - `unit`
  - `metadata`

### ResidualChecker

- Reads `log_file` and optional residual evidence under `postProcessing`.
- Classifies `CONVERGED`, `OSCILLATING`, `DIVERGED`, or `UNKNOWN`.
- Never raises on expected data gaps.

### GoldStandardChecker

- Compares every required observable from the contract Gold Standard file.
- Supports scalar observables and profile/list observables.
- Uses explicit per-observable tolerances from the contract alias YAML whenever present.

### PhysicalPlausibilityChecker

- Performs mass-balance, boundary-consistency, and scale sanity checks.
- Produces `PASS`, `WARN`, or `FAIL`.
- Can emit warnings without blocking the rest of the report.

### VerdictAggregator

- Combines L1, L2, and L3 results using the threshold table defined in the spec.
- Keeps layer outputs independent so that every failure remains attributable.

### CorrectionSuggester

- Converts non-pass findings into structured suggestions.
- Does not persist, replay, or mutate case configuration.
- Always marks output as human-confirmed workflow only.

## post_execute_hook Interface

The gate package needs a concrete additive seam. The proposed interface is:

```python
from typing import Optional, Protocol

class PostExecuteHook(Protocol):
    def __call__(
        self,
        task_spec,
        exec_result,
        comparison_result: Optional[object],
        correction_spec: Optional[object],
    ) -> object:
        ...
```

Design rules:

- The hook is optional.
- Existing `TaskRunner()` behavior remains unchanged when no hook is supplied.
- AutoVerifier runs after execution evidence is available, not during solver runtime.
- Suggest-only policy remains outside the legacy auto-save path until Opus approves implementation details.

## Data Contracts

### Input Contract

- `case_id` must be one of the contract anchor cases for Phase 8a.
- `gold_standard_file` must expose a top-level `observables` list.
- Each `observables[]` item must include:
  - `name`
  - `ref_value`
  - `tolerance`

### Output Contract

- The output file is `reports/{case_id}/auto_verify_report.yaml`.
- The report must always include:
  - `convergence`
  - `gold_standard_comparison`
  - `physics_check`
  - `verdict`
  - `correction_spec_needed`

## Tolerance Resolution

Resolution order is explicit to avoid silent threshold drift:

1. Observable-level tolerance in the contract alias YAML.
2. Legacy observable tolerance from the multi-document YAML source.
3. Threshold defaults from `AUTO_VERIFIER_SPEC.md`.

Anchor case defaults approved for this gate package:

| Case | Observable family | Default tolerance |
| --- | --- | --- |
| `lid_driven_cavity_benchmark` | centerline profiles, vortex summary | `5%` |
| `backward_facing_step_steady` | reattachment, pressure recovery, profiles | `10%` |
| `cylinder_crossflow` | Strouhal, coefficients, wake profile | `5%` |

## Boundary And Compatibility Rules

- Task `8a-1` does not modify `src/`, `tests/`, `templates/`, or `reports/`.
- Legacy Gold Standard YAML files remain untouched.
- No auto-correction is allowed.
- No new model dependency is introduced.
- No existing Phase 1-7 execution path is replaced by this task.

## Testing Strategy

Implementation is deferred to `8a-2`, but the design package fixes the required coverage target and test inventory now:

- Unit tests for L1, L2, L3, suggestion generation, and schema validation.
- E2E tests for OF-01, OF-02, and OF-03 using existing Docker evidence.
- Coverage target for `src/auto_verifier/`: `>= 80%`.
- Forbidden-file regression check on every implementation run.

## Gate Readiness Summary

- Contract paths are normalized without disturbing legacy files.
- The additive integration seam is defined.
- Tolerance ownership is explicit.
- Suggest-only policy is locked.
- The next step is Opus review, not implementation.
