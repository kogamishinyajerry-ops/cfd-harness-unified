# AutoVerifier Architecture Design

## Status
- Phase: 8a Planning
- Spec: `docs/specs/AUTO_VERIFIER_SPEC.md`
- Implementation: Pending Opus 4.6 Gate

## Architecture

```
TaskRunner
  └─► post_execute_hook (Optional[PostExecuteHook])
       └─► AutoVerifier.__call__(task_spec, exec_result, comparison_result, correction_spec)
            ├─► GoldStandardBundleLoader.load(case_id)
            │    ├─► knowledge/gold_standards/{case_id}.yaml (multi-doc)
            │    └─► KnowledgeDB.load_gold_standard() (fallback)
            ├─► ResidualChecker.run(task_spec, exec_result, gold_bundle)
            │    └─► CheckerReport(RESIDUAL, status, issues)
            ├─► GoldStandardChecker.run(task_spec, exec_result, gold_bundle)
            │    ├─► scalar comparison (strouhal, reattachment_length, nusselt_number...)
            │    ├─► profile comparison with y-aware interpolation (u_centerline...)
            │    └─► CheckerReport(GOLD_STANDARD, status, issues)
            ├─► PhysicalPlausibilityChecker.run(task_spec, exec_result, gold_bundle)
            │    └─► CheckerReport(PHYSICAL_PLAUSIBILITY, status, issues)
            ├─► CorrectionSuggester.suggest(checker_reports)
            │    └─► List[CorrectionSuggestion] (persisted=False, requires_human_confirmation=True)
            └─► ReportRenderer.render(auto_verification_report)
                 └─► markdown_report + YAML file
```

## Package Layout

```
src/auto_verifier/
  __init__.py           # AutoVerifier, AutoVerificationReport, VerificationStatus, CheckerKind
  models.py             # GoldObservable, GoldStandardBundle, VerificationIssue,
                        # CheckerReport, CorrectionSuggestion, ToleranceSpec, ToleranceMode
  protocols.py          # VerificationChecker (runtime_checkable Protocol)
  gold_loader.py         # GoldStandardBundleLoader
  tolerance_registry.py   # ToleranceRegistry (canonical observable tolerances)
  residual_checker.py    # ResidualChecker implements VerificationChecker
  gold_standard_checker.py  # GoldStandardChecker implements VerificationChecker
  physical_plausibility_checker.py  # PhysicalPlausibilityChecker
  correction_suggester.py    # CorrectionSuggester
  report_renderer.py         # ReportRenderer
```

## Core Design Decisions

### 1. Protocol vs ABC

Using `@runtime_checkable Protocol` instead of ABC:

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

Rationale: duck typing allows any object with the right `run()` method. ABC forces inheritance. Enables simpler testing (mock objects) and avoids diamond inheritance issues.

### 2. GoldStandardBundle vs Whitelist-Only

```python
@dataclass
class GoldStandardBundle:
    case_id: str
    observables: List[GoldObservable]  # one per YAML document
    source_path: Optional[str] = None
    used_whitelist_fallback: bool = False
```

Current `KnowledgeDB.load_gold_standard()` only reads embedded single-observable whitelist data. New `GoldStandardBundleLoader` reads full multi-document YAML files under `knowledge/gold_standards/`, enabling richer observable coverage.

**Fallback chain:**
1. Try `knowledge/gold_standards/{case_id}.yaml`
2. Load all documents with `yaml.safe_load_all()`
3. Convert each document to `GoldObservable`
4. If no file, fallback to `KnowledgeDB.load_gold_standard()` wrapped as single-observable bundle

### 3. Canonical Observable ID vs Display Label

Each `VerificationIssue` carries both:
- `observable_id`: `lid_driven_cavity:u_centerline` (canonical, for suggestion generation)
- `display_label`: `u_centerline[y=0.5000]` (human-facing)

Critical because `ErrorAttributor` uses rendered labels like `u_centerline[y=0.5000]`. AutoVerifier must not confuse these human-facing labels with canonical IDs.

### 4. Suggest-Only Correction Policy

```python
@dataclass
class CorrectionSuggestion:
    suggestion_id: str
    correction_spec: CorrectionSpec
    source_checkers: List[CheckerKind]
    confidence: float
    rationale: str
    requires_human_confirmation: bool = True
    persisted: bool = False  # NEVER auto-set to True
```

**Critical rule**: AutoVerifier never calls `KnowledgeDB.save_correction()`. All suggestions require human confirmation.

### 5. Three-Layer Verification

| Layer | Purpose | Output |
|-------|---------|--------|
| L1 Residual | Solver convergence | CONVERGED / OSCILLATING / DIVERGED / UNKNOWN |
| L2 Gold Standard | Numerical accuracy vs reference data | PASS / PASS_WITH_DEVIATIONS / FAIL / SKIPPED |
| L3 Physical Plausibility | Domain sanity checks | PASS / WARN / FAIL |

### 6. Additive TaskRunner Integration

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

class TaskRunner:
    def __init__(
        self,
        ...existing_params...,
        post_execute_hook: Optional[PostExecuteHook] = None,
        correction_policy: str = "legacy_auto_save",
    ) -> None:
```

**Backward compatibility**: existing callers with `TaskRunner()` continue to work unchanged (both default to existing behavior).

## Tolerance Registry

| Observable | Mode | Value |
|------------|------|-------|
| `lid_driven_cavity:u_centerline` | RELATIVE | 5% |
| `backward_facing_step:reattachment_length` | HYBRID | 10%, floor 0.25 |
| `circular_cylinder_wake:strouhal_number` | RELATIVE | 5% |
| `differential_heated_cavity:nusselt_number` | RELATIVE | 15% |
| `rayleigh_benard_convection:nusselt_number` | RELATIVE | 15% |
| `impinging_jet:nusselt_number` | RELATIVE | 15% |
| `turbulent_flat_plate:cf_skin_friction` | RELATIVE | 10% |
| `plane_channel_flow:u_mean_profile` | RELATIVE | 5% |
| `naca0012_airfoil:pressure_coefficient` | RELATIVE | 20% |

## Verdict Aggregation Logic

```
if any(L1=DIVERGED): verdict = FAIL
elif L1=UNKNOWN and L2=FAIL: verdict = FAIL
elif L2=PASS and L1=CONVERGED and L3=PASS: verdict = PASS
elif L2=PASS_WITH_DEVIATIONS or L3=WARN: verdict = PASS_WITH_DEVIATIONS
else: verdict = FAIL
```

## Testing Strategy

| Test File | Coverage Target |
|-----------|---------------|
| `test_gold_loader.py` | GoldStandardBundleLoader multi-doc + fallback |
| `test_residual_checker.py` | Steady/transient thresholds + missing residuals |
| `test_gold_standard_checker.py` | Scalar + profile + compound + missing required |
| `test_physical_plausibility_checker.py` | Generic + LDC + BFS + cylinder rules |
| `test_correction_suggester.py` | Suggest-only + no persistence side effects |
| `test_auto_verifier.py` | Orchestration + status aggregation + rendering |
| `test_task_runner_integration.py` | Legacy unchanged + suggest-only no save |

Target: branch coverage ≥ 80% for `src/auto_verifier/`.

## Existing Dependencies Reused

- `src/result_comparator.py`: `_compare_scalar` and `_compare_profile` logic reused in `GoldStandardChecker`
- `src/error_attributor.py`: `ErrorAttributor.attribute()` reused in `CorrectionSuggester`
- `src/correction_recorder.py`: `CorrectionRecorder.record()` reused in `CorrectionSuggester`
- `knowledge/gold_standards/*.yaml`: existing Gold Standard YAML files
- `src/models.py`: `ExecutionResult`, `TaskSpec`, `ComparisonResult`, `CorrectionSpec`
