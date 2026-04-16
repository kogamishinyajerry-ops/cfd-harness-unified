# Phase 8a Opus 4.6 Architecture Review Package

## Gate Authority
- **Reviewer**: Opus 4.6 (manual)
- **Package Prepared**: 2026-04-16
- **Spec**: `docs/specs/AUTO_VERIFIER_SPEC.md` (672 lines, exists)
- **Architecture Doc**: `docs/design/AUTO_VERIFIER_ARCHITECTURE.md` (exists)

---

## 1. Architecture Overview

### AutoVerifier: 3-Layer Verification Engine

AutoVerifier is an additive verification layer that wraps TaskRunner execution. It provides three independent verification layers and a correction suggestion engine:

```
TaskRunner
  └─► post_execute_hook (Optional[PostExecuteHook])
       └─► AutoVerifier.__call__(task_spec, exec_result, comparison_result, correction_spec)
            ├─► GoldStandardBundleLoader.load(case_id)
            │    ├─► knowledge/gold_standards/{case_id}.yaml (multi-doc)
            │    └─► KnowledgeDB.load_gold_standard() (fallback)
            ├─► ResidualChecker.run()      → CheckerReport(L1, RESIDUAL)
            ├─► GoldStandardChecker.run()   → CheckerReport(L2, GOLD_STANDARD)
            ├─► PhysicalPlausibilityChecker.run() → CheckerReport(L3, PHYSICAL_PLAUSIBILITY)
            ├─► CorrectionSuggester.suggest(checker_reports)
            │    └─► List[CorrectionSuggestion] (persisted=False, requires_human_confirmation=True)
            └─► ReportRenderer.render()
                 └─► markdown_report + YAML file
```

### Three-Layer Verification

| Layer | Checker | Output Statuses | Purpose |
|-------|---------|-----------------|---------|
| L1 | `ResidualChecker` | `CONVERGED / OSCILLATING / DIVERGED / UNKNOWN` | Solver convergence |
| L2 | `GoldStandardChecker` | `PASS / PASS_WITH_DEVIATIONS / FAIL / SKIPPED` | Numerical accuracy vs reference data |
| L3 | `PhysicalPlausibilityChecker` | `PASS / WARN / FAIL` | Domain sanity checks |

### Verdict Aggregation Logic

```
if any(L1=DIVERGED): verdict = FAIL
elif L1=UNKNOWN and L2=FAIL: verdict = FAIL
elif L2=PASS and L1=CONVERGED and L3=PASS: verdict = PASS
elif L2=PASS_WITH_DEVIATIONS or L3=WARN: verdict = PASS_WITH_DEVIATIONS
else: verdict = FAIL
```

### Suggest-Only Correction Policy

AutoVerifier **never** calls `KnowledgeDB.save_correction()`. All `CorrectionSuggestion` objects have:
- `requires_human_confirmation = True`
- `persisted = False` (never auto-set to True)

This preserves the Phase 8 human gate: human must explicitly confirm before any `CorrectionSpec` is applied.

### Integration Model: Additive Only

AutoVerifier plugs into `TaskRunner` via an optional `post_execute_hook`. The hook is a Protocol (not ABC), enabling duck typing. Existing callers with `TaskRunner()` continue unchanged — both default to legacy behavior.

---

## 2. Scope (In/Out)

### SI-1: In Scope — AutoVerifier Core
- `src/auto_verifier/__init__.py` — Public API exports
- `src/auto_verifier/models.py` — GoldObservable, GoldStandardBundle, ToleranceSpec, CheckerReport, CorrectionSuggestion, VerificationIssue, CheckerKind, VerificationStatus, ToleranceMode
- `src/auto_verifier/protocols.py` — VerificationChecker Protocol, PostExecuteHook Protocol
- `src/auto_verifier/gold_loader.py` — GoldStandardBundleLoader with multi-doc YAML + KnowledgeDB fallback
- `src/auto_verifier/tolerance_registry.py` — Canonical observable tolerances
- `src/auto_verifier/residual_checker.py` — L1 convergence checker
- `src/auto_verifier/gold_standard_checker.py` — L2 numerical comparison (scalar + profile with y-aware interpolation)
- `src/auto_verifier/physical_plausibility_checker.py` — L3 domain sanity
- `src/auto_verifier/correction_suggester.py` — Suggest-only correction drafts
- `src/auto_verifier/report_renderer.py` — Markdown + YAML report output
- `tests/test_auto_verifier/` — 7 test files targeting ≥80% branch coverage

### SI-2: In Scope — Additive TaskRunner Integration
- `src/task_runner.py` — Add `post_execute_hook: Optional[PostExecuteHook] = None` and `correction_policy: str = "legacy_auto_save"` to `__init__`
- `src/models.py` — Add `verification_report: Optional[AutoVerificationReport] = None` to `RunReport` (additive field)
- No existing `src/*.py` core logic modified

### OUT OF SCOPE (Explicit)
- `src/report_engine/` — belongs to Phase 8b (Report Template Engine)
- `templates/` — belongs to Phase 8b
- `knowledge/skill_index.yaml` — belongs to Phase 8c (Skill Index)
- `knowledge/schemas/` — belongs to Phase 8c (GS Schema), already done
- Knowledge graphs / LaTeX reports / auto-correction
- New solver support beyond existing FoamAgentExecutor coverage

---

## 3. Risk Assessment

### R1: Tolerance Standards Imprecise
**Risk**: YAML gold standards may lack explicit `tolerance` fields; hardcoded fallback tolerances may not match the physical regime.

**Mitigation**: `ToleranceRegistry` provides canonical values from the SPEC (e.g., `lid_driven_cavity:u_centerline → RELATIVE 5%`). Resolution order:
1. Explicit structured tolerance in YAML
2. Case-specific `ToleranceRegistry` entry
3. Legacy YAML float tolerance
4. Quantity-family default

**Evidence**: `docs/design/AUTO_VERIFIER_ARCHITECTURE.md` Table: Tolerance Registry lists 9 canonical observables with exact values.

### R2: Gold Standard YAML Schema Mismatch
**Risk**: YAML files may use different field names than what `GoldStandardChecker` expects (`value` vs `Nu`/`Cp`/`Cf`).

**Mitigation**: `GoldStandardBundleLoader` normalizes all reference values to `GoldObservable.reference_values` which accepts both `value` and per-component keys (`u`, `v`, `T`, etc.). KnowledgeDB fallback wraps whitelist data as single-observable bundle.

**Evidence**: `docs/specs/AUTO_VERIFIER_SPEC.md` lines 190-198 define `GoldStandardBundle` with `List[GoldObservable]`. Each `GoldObservable` has `quantity` + normalized reference_values.

### R3: Phase 8 Scope Creep
**Risk**: AutoVerifier implementation expands to cover auto-correction, report engine, or skill loading.

**Mitigation**: Reject conditions REJ-1 through REJ-6 are enforceable. Forbidden files list explicitly excludes `src/report_engine/`, `templates/`, `knowledge/skill_index.yaml`, `knowledge/schemas/`. CHK-11 (`git diff | grep forbidden`) validates this.

**Evidence**: Notion Task contract REJ-3: "修改了禁止文件 — 检查: CHK-11". Forbidden list includes `src/orchestrator/task_runner.py` (only post_execute_hook integration allowed).

### R4: Protocol-Based Duck Typing Obscures Errors
**Risk**: `VerificationChecker` Protocol allows any object with `run()` method; type errors surface only at runtime.

**Mitigation**: `@runtime_checkable` on Protocol enables `isinstance()` checks. Each checker returns `CheckerReport` — never raises for expected domain gaps. Unsupported observables surface as `SKIP`, not crashes.

**Evidence**: `docs/specs/AUTO_VERIFIER_SPEC.md` lines 137-145: `VerificationChecker` Protocol definition + "Unsupported observables should surface as SKIP or WARN, not crash the pipeline."

### R5: Suggest-Only Policy Bypass
**Risk**: Future maintainer accidentally adds auto-persistence inside AutoVerifier.

**Mitigation**: `CorrectionSuggestion.persisted = False` is a hard invariant — setter logs error and raises if ever set to True within AutoVerifier package. REJ-5 grep check: `grep -r 'apply_correction\|auto_apply\|write_case_config' src/auto_verifier/` must be empty.

**Evidence**: Notion REJ-5: "AutoVerifier 中包含自动应用 CorrectionSpec 的代码".

---

## 4. Recommendation

**IMPLEMENT** with the following binding conditions:

| Condition | Description | Gate Check |
|-----------|-------------|------------|
| RC-1 | Test coverage ≥ 80% for `src/auto_verifier/` | `pytest --cov-fail-under=80` |
| RC-2 | `correction_suggester.py` never calls `KnowledgeDB.save_correction()` | Grep REJ-5 check |
| RC-3 | `src/task_runner.py` core logic unchanged — only additive fields | CHK-11 |
| RC-4 | AutoVerifier never auto-applies corrections (persisted always False) | REJ-5 |
| RC-5 | All 6 reject conditions (REJ-1 through REJ-6) are enforceable in CI | CHK-* matrix |
| RC-6 | L1/L2/L3 checker outputs are independent (no cross-layer state mutation) | Unit tests |

---

## 5. Key Design Decisions

### DD-1: Protocol (not ABC) for VerificationChecker

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

**Rationale**: Duck typing allows any object with the right `run()` method. ABC forces inheritance. Enables simpler testing (mock objects) and avoids diamond inheritance issues. The `@runtime_checkable` decorator enables `isinstance()` validation for debugging.

**Source**: `docs/specs/AUTO_VERIFIER_SPEC.md` lines 137-145.

### DD-2: GoldStandardBundle (not Whitelist-Only)

```python
@dataclass
class GoldStandardBundle:
    case_id: str
    observables: List[GoldObservable]  # one per YAML document
    source_path: Optional[str] = None
    used_whitelist_fallback: bool = False
```

**Rationale**: Current `KnowledgeDB.load_gold_standard()` only reads embedded single-observable whitelist data. New `GoldStandardBundleLoader` reads full multi-document YAML files under `knowledge/gold_standards/`, enabling richer observable coverage per case.

**Fallback chain**:
1. Try `knowledge/gold_standards/{case_id}.yaml`
2. Load all documents with `yaml.safe_load_all()`
3. Convert each document to `GoldObservable`
4. If no file, fallback to `KnowledgeDB.load_gold_standard()` wrapped as single-observable bundle

**Source**: `docs/design/AUTO_VERIFIER_ARCHITECTURE.md` Section 2.

### DD-3: Canonical observable_id vs display_label Separation

```python
@dataclass
class VerificationIssue:
    observable_id: str   # canonical: "lid_driven_cavity:u_centerline"
    display_label: str   # human-facing: "u_centerline[y=0.5000]"
```

**Rationale**: `ErrorAttributor` uses rendered labels like `u_centerline[y=0.5000]`. AutoVerifier must not confuse these human-facing point labels with canonical IDs. Suggestion generation and coverage checks must use `observable_id` only.

**Critical rule** (SPEC line 405): "Suggestion generation and coverage checks must use `observable_id`, not `display_label`."

### DD-4: Suggest-Only Correction Policy

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

**Rationale**: AutoVerifier never calls `KnowledgeDB.save_correction()`. All suggestions require human confirmation. This preserves the Phase 8 human gate: human must explicitly confirm before any `CorrectionSpec` is applied.

**Critical rule**: `persisted = False` is a hard invariant within `src/auto_verifier/`. Any setter that attempts to set it to True must log an error and raise.

### DD-5: Additive TaskRunner Integration

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

**Rationale**: Backward compatibility — existing callers with `TaskRunner()` continue to work unchanged (both default to legacy behavior). When `post_execute_hook=AutoVerifier(...)` and `correction_policy="suggest_only"`, AutoVerifier runs but never auto-persists.

**Backward compatibility**: `TaskRunner()` with no hook → existing Phase 1-7 behavior. `TaskRunner(post_execute_hook=AutoVerifier(), correction_policy="suggest_only")` → AutoVerifier active, no auto-save.

---

## 6. Integration Points (Additive, Backward Compatible)

### 6.1 TaskRunner Changes (Minimal, Additive Only)

**File**: `src/task_runner.py`

```python
from typing import Optional, Protocol, runtime_checkable

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
        self._post_execute_hook = post_execute_hook
        self._correction_policy = correction_policy
        # ... existing init unchanged ...
```

**In `run_task()` method, after execution and comparison**:
```python
verification_report = None
if self._post_execute_hook is not None:
    verification_report = self._post_execute_hook(
        task_spec, exec_result, comparison_result, correction_spec
    )

summary = self._build_summary(
    task_spec, exec_result, comparison_result,
    correction_spec, verification_report
)
```

**No existing method signatures changed. No existing logic modified.**

### 6.2 RunReport Changes (Additive Field Only)

**File**: `src/models.py`

```python
@dataclass
class RunReport:
    # ... existing fields unchanged ...
    verification_report: Optional[AutoVerificationReport] = None  # NEW field
```

This is the ONLY change to existing `src/models.py`. No existing fields modified.

### 6.3 Package Layout (New Files Only)

```
src/auto_verifier/           ← NEW package (10 files)
tests/test_auto_verifier/    ← NEW test package (7 files)
```

No existing `src/*.py` files are modified except `src/task_runner.py` (additive) and `src/models.py` (additive field only).

### 6.4 Backward Compatibility Evidence

| Scenario | Behavior | Verified By |
|----------|----------|-------------|
| `TaskRunner()` | No hook, legacy auto-save | Existing tests pass unchanged |
| `TaskRunner(post_execute_hook=None)` | Same as above | CHK-11: no core logic modified |
| `TaskRunner(post_execute_hook=AutoVerifier())` | Hook runs, no auto-save | REJ-5 grep check |
| All 121 existing tests | Still pass | `pytest tests/ -q` → 121/121 |

---

## 7. Reject Conditions (REJ-1 through REJ-6)

These are the 6 enforceable reject conditions from the Notion AutoVerifier MVP task contract:

| ID | Condition | Enforceable Check |
|----|-----------|------------------|
| **REJ-1** | Test coverage < 80% | `pytest tests/test_auto_verifier/ --cov=src/auto_verifier/ --cov-fail-under=80` → exit code 0 |
| **REJ-2** | Any E2E report missing or schema invalid | CHK-7/8/9: `yaml.safe_load()` + `assert 'verdict' in ['PASS','PASS_WITH_DEVIATIONS','FAIL']` |
| **REJ-3** | Forbidden files modified | CHK-11: `git diff --name-only HEAD \| grep -c 'src/orchestrator/\|src/report_engine/\|templates/\|knowledge/skill_index\|knowledge/schemas/'` → 0 |
| **REJ-4** | Test count < 18 | CHK-10: `pytest --collect-only -q \| tail -1` → ≥ 18 tests |
| **REJ-5** | AutoVerifier contains auto-apply CorrectionSpec code | `grep -r 'apply_correction\|auto_apply\|write_case_config' src/auto_verifier/` → empty |
| **REJ-6** | Opus Gate not yet passed before implementation | DEP-2 status = "User confirmed PASS" |

**REJ-5 Specific Grep Patterns** (to be verified in CI):
```bash
# Must return zero matches
grep -r 'apply_correction\|auto_apply\|write_case_config\|KnowledgeDB.*save' src/auto_verifier/
grep -r 'persisted\s*=\s*True' src/auto_verifier/
```

---

## 8. Spec Cross-Reference

| Document | Path | Lines | Status |
|----------|------|-------|--------|
| AutoVerifier MVP Spec | `docs/specs/AUTO_VERIFIER_SPEC.md` | 672 | ✅ EXISTS |
| Architecture Design | `docs/design/AUTO_VERIFIER_ARCHITECTURE.md` | 187 | ✅ EXISTS |
| This Gate Package | `docs/gates/PHASE8A_OPUS_REVIEW_PACKAGE.md` | — | 📋 THIS FILE |

### Key Spec Sections

- **Spec Section 3** (Problem): Documents 5 gaps in current validation (lines 1-45)
- **Spec Section 5** (Core Design): VerificationChecker Protocol (lines 137-145), GoldStandardBundle (lines 190-198)
- **Spec Section 6** (Gold Bundle Loading): Multi-doc YAML loader + KnowledgeDB fallback (lines 227-248)
- **Spec Section 7** (Tolerance Resolution): Precedence order + canonical table (lines 249-310)
- **Spec Section 8** (TaskRunner Integration): post_execute_hook + correction_policy (lines 520-600)
- **Spec Section 9** (Test Plan): 18-test matrix with branch coverage ≥ 80% target (lines 601-672)

### Gold Standard YAML Files

| File | Observables | Format | Status |
|------|-------------|--------|--------|
| `lid_driven_cavity.yaml` | u_centerline, v_centerline, primary_vortex | multi-doc | ✅ 3 docs |
| `backward_facing_step.yaml` | reattachment_length, cd_mean, pressure_recovery, velocity_profile | multi-doc | ✅ 4 docs |
| `circular_cylinder_wake.yaml` | strouhal_number, cd_mean, cl_rms, u_mean_centerline | multi-doc | ✅ 4 docs |
| `differential_heated_cavity.yaml` | nusselt_number | multi-doc | ✅ 1 doc |
| `impinging_jet.yaml` | nusselt_number | multi-doc | ✅ 1 doc |
| `natural_convection_cavity.yaml` | nusselt_number | multi-doc | ✅ 1 doc |
| `rayleigh_benard_convection.yaml` | nusselt_number | multi-doc | ✅ 1 doc |
| `turbulent_flat_plate.yaml` | cf_skin_friction | multi-doc | ✅ 1 doc |
| `plane_channel_flow.yaml` | u_mean_profile | multi-doc | ✅ 1 doc |
| `naca0012_airfoil.yaml` | pressure_coefficient | multi-doc | ✅ 1 doc |

**Validation**: `python scripts/validate_gold_standards.py` → 10/10 PASS ✅

---

## 9. Acceptance Criteria for Opus Gate

The Opus Gate passes if and only if all of the following are satisfied:

### Gate Pass Conditions

| # | Criterion | Evidence Required |
|---|-----------|-------------------|
| G-1 | **Architecture is sound** | Protocol-based, additive integration, suggest-only correction, 3-layer verification all correctly specified |
| G-2 | **Reject conditions are enforceable** | REJ-1 through REJ-6 each have a CI-verifiable check (grep, pytest --cov, yaml schema validation) |
| G-3 | **Risk mitigations are adequate** | R1 (ToleranceRegistry), R2 (GoldStandardBundle fallback), R3 (forbidden files + CHK-11) all have concrete mitigations in the spec |
| G-4 | **Integration is backward compatible** | Existing `TaskRunner()` works unchanged; all 121 existing tests pass |
| G-5 | **No auto-apply correction bypass** | REJ-5 grep returns empty; `persisted = False` is a hard invariant |
| G-6 | **Scope boundaries are enforceable** | Forbidden files list is concrete and grep-verifiable in CI |

### Opus 4.6 Decision

```
Gate Decision: _______________
Reviewer Notes: _______________
Binding Conditions (if IMPLEMENT): _______________
Date: _______________
```

### Post-Gate Actions (if APPROVED)

1. Create branch: `git checkout -b phase8a-auto-verifier`
2. Implement `src/auto_verifier/` package in order:
   - `models.py` → `protocols.py` → `gold_loader.py` → `tolerance_registry.py`
   - `residual_checker.py` → `gold_standard_checker.py` → `physical_plausibility_checker.py`
   - `correction_suggester.py` → `report_renderer.py` → `__init__.py`
3. Additive TaskRunner wiring (only `__init__` params + `run_task` hook call)
4. Write `tests/test_auto_verifier/` — 7 files, ≥18 tests, ≥80% branch coverage
5. Run CHK-* acceptance checks
6. Generate OF-01/02/03 auto_verify_report.yaml files
7. Create PR → Code review → Merge
