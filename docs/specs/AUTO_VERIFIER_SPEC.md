# AutoVerifier MVP Spec

## Status

- Phase: 8a
- Objective: AI self-correction verification + auto-report generation
- Gate: Opus 4.6 architecture review required before implementation
- Delivery mode: suggest-only; no automatic correction persistence when AutoVerifier is enabled
- File scope:
  - New: `src/auto_verifier/`
  - New: `tests/test_auto_verifier/`
  - Minimal additive wiring: `src/task_runner.py`

## Problem

Current validation is too shallow for Phase 8:

1. `TaskRunner` validates only one whitelist gold observable.
2. `ResultComparator` is single-observable and partially schema-aware.
3. `TaskRunner` auto-saves `CorrectionSpec` on failure, which conflicts with Phase 8 human-gated correction policy.
4. There is no three-layer verification report.
5. Richer gold standards already exist under `knowledge/gold_standards/*.yaml` but are not used by the runtime path.

## Current Repo Findings

- `TaskRunner.run_task()` currently does:
  1. execute CFD
  2. load one gold standard from `KnowledgeDB.load_gold_standard()`
  3. run one `ResultComparator.compare()`
  4. if failed, immediately create and persist a `CorrectionSpec`
- `KnowledgeDB.load_gold_standard()` only reads the embedded whitelist gold entry.
- `knowledge/gold_standards/*.yaml` uses multi-document YAML and contains broader observable coverage than the whitelist.
- `FoamAgentExecutor._parse_solver_log()` already exposes:
  - residual snapshots
  - `u_centerline`
  - `reattachment_length`
  - `nusselt_number`
  - coordinate arrays for sampled profiles
- `ErrorAttributor` already encodes a useful residual heuristic:
  - `max_residual < 1e-3` with deviations suggests mesh/physics mismatch
  - `max_residual > 1e-3` suggests solver/BC instability
- Important pitfall:
  - `ErrorAttributor` key-coverage currently uses rendered deviation labels like `u_centerline[y=0.5000]`
  - AutoVerifier must keep canonical observable IDs separate from human-facing point labels to avoid false schema-mismatch attribution

## Goals

- Add a three-layer verification pass:
  1. residual convergence
  2. Gold Standard numerical comparison
  3. physical plausibility
- Make `lid_driven_cavity` the anchor case.
- Cross-validate architecture on OF-02/03.
  - MVP assumption: OF-02=`backward_facing_step`, OF-03=`circular_cylinder_wake`
- Generate a structured in-memory report and Markdown report text.
- Generate correction suggestions only.
- Require human confirmation before any `CorrectionSpec` is saved.
- Preserve Phase 1-7 behavior when AutoVerifier is disabled.
- Keep test coverage for new code at or above 80%.

## Non-Goals

- No automatic case mutation.
- No automatic replay.
- No automatic `KnowledgeDB.save_correction()` in AutoVerifier suggest-only mode.
- No mandatory Notion schema change in Phase 8a.
- No full extractor expansion for every gold observable in Phase 8a.

## Proposed Package Layout

```text
src/auto_verifier/
  __init__.py
  auto_verifier.py
  models.py
  protocols.py
  gold_loader.py
  tolerance_registry.py
  residual_checker.py
  gold_standard_checker.py
  physical_plausibility_checker.py
  correction_suggester.py
  report_renderer.py

tests/test_auto_verifier/
  test_models.py
  test_gold_loader.py
  test_residual_checker.py
  test_gold_standard_checker.py
  test_physical_plausibility_checker.py
  test_correction_suggester.py
  test_auto_verifier.py
  test_task_runner_integration.py
```

## Core Design

### 1. AutoVerifier Orchestrator

`AutoVerifier` is the single entry point and the default `post_execute_hook` implementation.

Responsibilities:

- load the full gold bundle for the current case
- run all three checkers in fixed order
- aggregate checker outputs into one report
- generate suggest-only correction drafts
- render Markdown summary
- expose `__call__()` so it can plug directly into `TaskRunner`

Public shape:

```python
class AutoVerifier:
    def verify(
        self,
        task_spec: TaskSpec,
        exec_result: ExecutionResult,
        legacy_comparison: Optional[ComparisonResult] = None,
    ) -> AutoVerificationReport: ...

    def __call__(
        self,
        task_spec: TaskSpec,
        exec_result: ExecutionResult,
        comparison_result: Optional[ComparisonResult] = None,
        correction_spec: Optional[CorrectionSpec] = None,
    ) -> AutoVerificationReport: ...
```

### 2. Checker Contract

Use `Protocol`, not ABC.

```python
@runtime_checkable
class VerificationChecker(Protocol):
    def run(
        self,
        task_spec: TaskSpec,
        exec_result: ExecutionResult,
        gold_bundle: GoldStandardBundle,
    ) -> CheckerReport: ...
```

Each checker returns a `CheckerReport`, never raises for expected domain gaps. Unsupported observables should surface as `SKIP` or `WARN`, not crash the pipeline.

### 3. Data Model

#### Enums

- `VerificationStatus`
  - `PASS`
  - `WARN`
  - `FAIL`
  - `SKIP`

- `CheckerKind`
  - `RESIDUAL`
  - `GOLD_STANDARD`
  - `PHYSICAL_PLAUSIBILITY`

- `ToleranceMode`
  - `RELATIVE`
  - `ABSOLUTE`
  - `HYBRID`

#### Dataclasses

```python
@dataclass
class ToleranceSpec:
    mode: ToleranceMode
    relative: Optional[float] = None
    absolute: Optional[float] = None
    absolute_floor: Optional[float] = None
    min_coverage: float = 1.0

@dataclass
class GoldObservable:
    case_id: str
    quantity: str
    observable_id: str
    reference_values: List[Dict[str, Any]]
    tolerance: ToleranceSpec
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GoldStandardBundle:
    case_id: str
    observables: List[GoldObservable]
    source_path: Optional[str] = None
    used_whitelist_fallback: bool = False

@dataclass
class VerificationIssue:
    checker: CheckerKind
    observable_id: str
    display_label: str
    status: VerificationStatus
    message: str
    expected: Optional[Any] = None
    actual: Optional[Any] = None
    tolerance: Optional[Any] = None
    relative_error: Optional[float] = None
    evidence: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

@dataclass
class CheckerReport:
    checker: CheckerKind
    status: VerificationStatus
    summary: str
    issues: List[VerificationIssue] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CorrectionSuggestion:
    suggestion_id: str
    correction_spec: CorrectionSpec
    source_checkers: List[CheckerKind]
    confidence: float
    rationale: str
    requires_human_confirmation: bool = True
    persisted: bool = False

@dataclass
class AutoVerificationReport:
    case_id: str
    task_name: str
    status: VerificationStatus
    checker_reports: List[CheckerReport]
    suggestions: List[CorrectionSuggestion]
    summary: str
    markdown_report: str
```

## Gold Bundle Loading

### Problem

Current runtime only loads whitelist-embedded single-observable gold data. AutoVerifier must use the richer multi-document files under `knowledge/gold_standards/`.

### Design

`gold_loader.py` resolves case data in this order:

1. Resolve canonical `case_id` from `KnowledgeDB.get_execution_chain(task_spec.name)`
2. Try `knowledge/gold_standards/<case_id>.yaml`
3. Load all documents with `yaml.safe_load_all()`
4. Convert each document into `GoldObservable`
5. If no file exists, fallback to `KnowledgeDB.load_gold_standard()` and wrap it as a single-observable bundle

### Important Rule

Do not modify `KnowledgeDB` in Phase 8a. Keep bundle loading local to `src/auto_verifier/` to avoid Phase 1-7 regression risk.

## Tolerance Resolution

### Precedence

Tolerance resolution order:

1. future explicit structured tolerance in YAML, if added later
2. case-specific `tolerance_registry`
3. legacy YAML `tolerance` float
4. quantity-family default

### Canonical Tolerance Standards

| Observable | Comparison Mode | Standard | Phase 8a Support |
| --- | --- | --- | --- |
| `lid_driven_cavity:u_centerline` | profile, interpolate on `y` | relative 5%, min coverage 0.8 | Required |
| `lid_driven_cavity:v_centerline` | profile, interpolate on `y` | relative 5%, min coverage 0.8 | Optional |
| `lid_driven_cavity:primary_vortex_location:vortex_center_x` | scalar | absolute 0.05 | Optional |
| `lid_driven_cavity:primary_vortex_location:vortex_center_y` | scalar | absolute 0.05 | Optional |
| `lid_driven_cavity:primary_vortex_location:u_min` | scalar | relative 5% | Optional |
| `backward_facing_step:reattachment_length` | scalar | relative 10%, absolute floor 0.25 | Required |
| `backward_facing_step:cd_mean` | scalar | relative 10% | Optional |
| `backward_facing_step:pressure_recovery` | multi-scalar | relative 10% | Optional |
| `backward_facing_step:velocity_profile_reattachment` | profile on `(x_H,y_H)` | relative 10% | Optional |
| `circular_cylinder_wake:strouhal_number` | scalar | relative 5% | Required |
| `circular_cylinder_wake:cd_mean` | scalar | relative 5% | Optional |
| `circular_cylinder_wake:cl_rms` | scalar | relative 5% | Optional |
| `circular_cylinder_wake:u_mean_centerline` | profile on `x_D` | relative 5% | Optional |
| `differential_heated_cavity:nusselt_number` | scalar | relative 15% | Supported if present |
| `rayleigh_benard_convection:nusselt_number` | scalar | relative 15% | Supported if present |
| `impinging_jet:nusselt_number` | profile on `r_over_d` | relative 15% | Optional |
| `fully_developed_pipe:friction_factor` | scalar | relative 8% | Optional |
| `plane_channel_flow:u_mean_profile` | profile on `y_plus` | relative 5% | Optional |
| `turbulent_flat_plate:cf_skin_friction` | profile on `x_over_c` | relative 10% | Optional |
| `naca0012_airfoil:pressure_coefficient` | profile on `x_over_c` | relative 20% | Optional |

### Family Defaults

- benchmark profiles: 5%
- engineering separated-flow observables: 10%
- friction factor: 8%
- thermal Nusselt observables: 15%
- airfoil Cp distributions: 20%

## Checker Design

### ResidualChecker

Purpose:

- assess whether solver residuals indicate acceptable numerical convergence for MVP
- provide advisory evidence even when Gold Standard passes

Important limitation:

- current executor exposes residual snapshots, not full residual histories
- Phase 8a therefore checks terminal residual state only

Rules:

- steady cases:
  - `PASS` if `max_residual <= 1e-4`
  - `WARN` if `1e-4 < max_residual <= 1e-3`
  - `FAIL` if `max_residual > 1e-3`
- transient cases:
  - `PASS` if `max_residual <= 1e-3`
  - `WARN` if `1e-3 < max_residual <= 1e-2`
  - `FAIL` if `max_residual > 1e-2`
- missing residuals:
  - `WARN`, not `FAIL`

Outputs:

- `max_residual`
- `field_residuals`
- `residual_basis="terminal_snapshot"`
- recommended tags:
  - `solver_controls`
  - `delta_t`
  - `relaxation`
  - `iteration_budget`

### GoldStandardChecker

Purpose:

- compare current execution output against the full case gold bundle
- support more than one observable per case
- produce synthetic `ComparisonResult` for correction suggestion generation

Comparison modes:

1. scalar
2. profile
3. compound

#### Scalar mode

For single-value observables such as:

- `strouhal_number`
- `reattachment_length`
- `nusselt_number`
- `friction_factor`
- `cd_mean`
- `cl_rms`

#### Profile mode

Generalize current `ResultComparator` interpolation logic:

- identify the axis key from reference rows:
  - `x`
  - `y`
  - `x_H`
  - `y_H`
  - `x_D`
  - `x_over_c`
  - `y_plus`
  - `r_over_d`
- map actual coordinates via registry, not naming guesses alone
- if coordinates are available, compare by interpolation
- if coordinates are missing but lengths match, fallback to positional comparison
- if the observable is required and no actual payload exists, return `FAIL`
- if the observable is optional and no actual payload exists, return `SKIP`

#### Compound mode

Used for `primary_vortex_location`.

Rules:

- compare named components independently
- preserve component-level labels
- use absolute tolerance for coordinates
- use relative tolerance for velocity magnitude components

### Canonical ID Rule

Each failure must carry both:

- `observable_id`
  - e.g. `lid_driven_cavity:u_centerline`
- `display_label`
  - e.g. `u_centerline[y=0.5000]`

Suggestion generation and coverage checks must use `observable_id`, not `display_label`.

### PhysicalPlausibilityChecker

Purpose:

- catch obvious physically invalid outputs even when residuals are small
- provide cheap domain sanity checks before suggesting corrections

Rule tiers:

#### Generic rules

- no `NaN` or `Inf` in residuals or key quantities
- coordinate/value arrays must have matching lengths
- positive-only observables must remain positive:
  - `reattachment_length`
  - `nusselt_number`
  - `friction_factor`
  - `cd_mean`
  - `cl_rms`

#### Lid-Driven Cavity rules

- top-lid velocity implied by `u_centerline` near the top wall should be approximately 1.0 within ±0.15
- centerline velocity should cross from negative to positive exactly once between lower and upper cavity regions
- values should remain bounded in a plausible cavity range, default `-1.5 <= u <= 1.5`

#### Backward-Facing Step rules

- `reattachment_length` must be positive
- `reattachment_length` should stay in a broad engineering band, default `0 < Xr/H < 20`

#### Circular Cylinder Wake rules

- `strouhal_number` must lie in `[0.1, 0.3]`
- `cd_mean > 0`
- `cl_rms > 0` when present
- if `u_mean_centerline` exists, wake deficit should decay downstream

Status policy:

- plausibility violations are `FAIL`
- missing optional observables are `SKIP`
- unsupported case-rule sets are `SKIP`

## Correction Suggestion Generation

### Requirement

AutoVerifier must suggest only. It must not call `KnowledgeDB.save_correction()`.

### Design

`correction_suggester.py` builds `CorrectionSuggestion` objects.

Generation order:

1. gold checker failures
2. residual failures
3. physical plausibility failures

### Reuse Strategy

When gold checker produces a synthetic `ComparisonResult`:

- reuse existing `CorrectionRecorder.record()`
- reuse existing `ErrorAttributor.attribute()`
- wrap the returned `CorrectionSpec` inside `CorrectionSuggestion`
- enrich `evidence` and `rationale` with residual/plausibility findings

When only residual/plausibility fails exist and no gold deviation exists:

- create a draft `CorrectionSpec` manually
- prefer:
  - `ErrorType.CONVERGENCE_FAILURE` for residual failures
  - `ErrorType.OTHER` for plausibility-only failures
- mark all such drafts as:
  - `requires_human_confirmation=True`
  - `persisted=False`

### Explicit Rule

AutoVerifier never writes to `knowledge/corrections/`.
Human approval is a separate action outside Phase 8a.

## Report Rendering

`report_renderer.py` produces:

1. structured `AutoVerificationReport`
2. Markdown text for humans

Markdown sections:

- case summary
- overall status
- per-checker status
- failed/warned observables
- suggested corrections
- next human actions

Example summary line:

```text
AutoVerifier: FAIL | residual=WARN | gold=FAIL | plausibility=PASS | suggestions=1
```

## TaskRunner Integration

### Problem

There is no hook abstraction today.

### Proposed Additive Interface

Add an optional `post_execute_hook` and a correction policy.

```python
@runtime_checkable
class PostExecuteHook(Protocol):
    def __call__(
        self,
        task_spec: TaskSpec,
        exec_result: ExecutionResult,
        comparison_result: Optional[ComparisonResult],
        correction_spec: Optional[CorrectionSpec],
    ) -> Optional[AutoVerificationReport]: ...
```

TaskRunner constructor additions:

```python
def __init__(
    ...,
    post_execute_hook: Optional[PostExecuteHook] = None,
    correction_policy: str = "legacy_auto_save",
) -> None:
```

Allowed `correction_policy` values:

- `"legacy_auto_save"`
- `"suggest_only"`

### Required Run Flow

```python
exec_result = self._executor.execute(task_spec)

comparison = existing legacy compare if gold exists
correction = None

if comparison failed:
    if correction_policy == "legacy_auto_save":
        correction = self._recorder.record(...)
        self._db.save_correction(correction)

verification_report = None
if self._post_execute_hook is not None:
    verification_report = self._post_execute_hook(
        task_spec,
        exec_result,
        comparison,
        correction,
    )

summary = self._build_summary(..., verification_report)
```

### Backward Compatibility Rule

- default behavior remains unchanged:
  - `post_execute_hook=None`
  - `correction_policy="legacy_auto_save"`
- AutoVerifier-enabled runs must use:
  - `post_execute_hook=AutoVerifier(...)`
  - `correction_policy="suggest_only"`

### RunReport Extension

Add one optional field:

```python
verification_report: Optional[AutoVerificationReport] = None
```

This is additive and should not break existing callers.

## MVP Case Support

### Required Phase 8a validation cases

- OF-01 `lid_driven_cavity`
  - required gold observable: `u_centerline`
- OF-02 `backward_facing_step`
  - required gold observable: `reattachment_length`
- OF-03 `circular_cylinder_wake`
  - required gold observable: `strouhal_number`

### Support policy

- if a required observable is missing from `ExecutionResult.key_quantities`, `GoldStandardChecker` returns `FAIL`
- if an optional observable is missing, `GoldStandardChecker` returns `SKIP`
- this prevents Phase 8a from failing purely because the repository already contains future-facing gold schemas

## Testing Strategy

Target:

- `pytest`
- branch coverage on `src/auto_verifier/`
- minimum coverage: 80%

Required tests:

1. `test_gold_loader.py`
   - multi-document YAML load
   - whitelist fallback
   - case-id resolution
2. `test_residual_checker.py`
   - steady thresholds
   - transient thresholds
   - missing residuals
3. `test_gold_standard_checker.py`
   - scalar compare
   - profile interpolation
   - compound compare
   - canonical `observable_id` vs `display_label`
   - required missing observable => `FAIL`
   - optional missing observable => `SKIP`
4. `test_physical_plausibility_checker.py`
   - generic finite-value rules
   - LDC rules
   - BFS rules
   - cylinder rules
5. `test_correction_suggester.py`
   - gold failure generates suggest-only `CorrectionSuggestion`
   - no persistence side effects
   - residual-only failure generates draft convergence suggestion
6. `test_auto_verifier.py`
   - checker orchestration
   - overall status aggregation
   - Markdown report rendering
7. `test_task_runner_integration.py`
   - legacy path unchanged when hook is absent
   - suggest-only mode does not call `save_correction`
   - summary contains AutoVerifier verdict

## Acceptance Criteria

Phase 8a is ready for implementation when:

- AutoVerifier can run as a `TaskRunner` post-execute hook.
- Legacy `TaskRunner` behavior is unchanged when AutoVerifier is disabled.
- AutoVerifier generates a three-layer report for the anchor case.
- AutoVerifier cross-validates on OF-02/03 without special-case hacks in `TaskRunner`.
- AutoVerifier generates human-gated correction suggestions only.
- No automatic correction persistence happens in suggest-only mode.
- New tests reach at least 80% coverage for `src/auto_verifier/`.

## Risks and Notes

- The repo does not currently contain explicit `OF-*` case identifiers; OF-02/03 mapping is an MVP assumption.
- Residual checking is limited by current executor output; Phase 8a uses terminal residual snapshots, not full convergence history.
- Many gold observables exist without current extraction support; required-vs-optional coverage must be explicit in the registry.
- `docs/specs/` does not exist yet and will need to be created when implementation starts.
