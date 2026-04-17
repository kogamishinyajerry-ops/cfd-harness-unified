# AutoVerifier Spec v2.0 (Contract)

## Status

- Phase: `8a-1`
- Contract task: `AutoVerifier 架构设计 + Opus Gate 审查包准备`
- Prepared on: `2026-04-17`
- Gate: `STOP after this document package and wait for manual Opus 4.6 review`
- Delivery mode: `suggest-only`
- Scope anchor: `OF-01 lid_driven_cavity`, `OF-02 backward_facing_step`, `OF-03 circular_cylinder_wake`

## Scope

- `[S-1]` L1 residual convergence check: parse OpenFOAM residual evidence and classify convergence status.
- `[S-2]` L2 Gold Standard numerical comparison: evaluate every observable against explicit case tolerances.
- `[S-3]` L3 physical plausibility check: detect mass-balance, boundary-condition, and order-of-magnitude issues.
- `[S-4]` CorrectionSpec suggestion generation: produce structured suggestions when the final verdict is not `PASS`.
- `[S-5]` Verification report output: emit deterministic YAML output plus a human-readable summary for downstream reporting.

## Non-goals

- `[NG-1]` Auto-apply any CorrectionSpec to a case.
- `[NG-2]` Replace or mutate the execution pipeline in Phase 1-7.
- `[NG-3]` Introduce multi-solver support or any new LLM dependency.
- `[NG-4]` Perform real-time monitoring or streaming verification during a solver run.

## Input Schema

```yaml
input:
  case_id:
    type: string
    required: true
    constraints:
      - matches a whitelist entry in the current repo whitelist source
      - for Phase 8a the required anchor set is:
        - lid_driven_cavity_benchmark
        - backward_facing_step_steady
        - cylinder_crossflow
    notes:
      - the current repo stores active whitelist data in knowledge/whitelist.yaml
      - Notion contract references the same logical whitelist as knowledge/ai_cfd_cold_start_whitelist.yaml

  log_file:
    type: file_path
    required: true
    constraints:
      - file exists
      - UTF-8 text
      - contains parseable residual lines or solver summary markers
    source: "{case_dir}/log.{solver}"

  post_processing_dir:
    type: directory_path
    required: false
    constraints:
      - if present, may contain residual or sampled field evidence
      - absence must not crash verification
    source: "{case_dir}/postProcessing/"

  gold_standard_file:
    type: file_path
    required: true
    constraints:
      - valid YAML
      - contains top-level observables list
      - each observables[] item includes name, ref_value, tolerance
    source: "knowledge/gold_standards/{contract_case_id}.yaml"

  sim_results:
    type: mapping
    required: true
    constraints:
      - keys are canonical observable names
      - values are finite scalar values, profile lists, or structured mappings
    source: "TaskRunner execution result key_quantities"
```

## Output Schema

```yaml
output:
  auto_verify_report:
    type: object
    guaranteed: true
    sink: "reports/{case_id}/auto_verify_report.yaml"
    schema:
      case_id:
        type: string
      timestamp:
        type: string
        format: iso-8601
      convergence:
        type: object
        schema:
          status:
            type: string
            enum:
              - CONVERGED
              - OSCILLATING
              - DIVERGED
              - UNKNOWN
          final_residual:
            type: number|null
          target_residual:
            type: number
          residual_ratio:
            type: number|null
      gold_standard_comparison:
        type: object
        schema:
          overall:
            type: string
            enum:
              - PASS
              - PASS_WITH_DEVIATIONS
              - FAIL
              - SKIPPED
          observables:
            type: list
            items:
              name: string
              ref_value: any
              sim_value: any
              rel_error: number|null
              abs_error: number|null
              tolerance: any
              within_tolerance: boolean
      physics_check:
        type: object
        schema:
          status:
            type: string
            enum:
              - PASS
              - WARN
              - FAIL
          warnings:
            type: list
            items: string
      verdict:
        type: string
        enum:
          - PASS
          - PASS_WITH_DEVIATIONS
          - FAIL
      correction_spec_needed:
        type: boolean
      correction_spec:
        type: object|null
        schema:
          primary_cause:
            type: string
            enum:
              - mesh_resolution
              - boundary_condition
              - turbulence_model
              - solver_settings
              - time_stepping
              - unknown
          confidence:
            type: string
            enum:
              - HIGH
              - MEDIUM
              - LOW
          suggested_correction:
            type: string
```

## Core Formulas

| ID | Name | Formula | Use |
| --- | --- | --- | --- |
| `F-1` | Relative error | `epsilon_rel = abs(v_sim - v_ref) / abs(v_ref)` | Default scalar or profile-point comparison |
| `F-2` | Absolute error fallback | `epsilon_abs = abs(v_sim - v_ref)` | Used when `abs(v_ref) < 1e-12` |
| `F-3` | Residual ratio | `R_ratio = r_final / r_target` | L1 convergence decision |
| `F-4` | Residual delta | `delta_r_i = r_i - r_(i-1)` | Trend detection across final iterations |
| `F-5` | Oscillation ratio | `osc = count(delta_r_i > 0) / N` | Detect repeated residual rebound |
| `F-6` | Mass imbalance | `delta_m = abs(m_dot_in - m_dot_out) / m_dot_in` | L3 conservation sanity check |

## Threshold Table

| ID | Parameter | Threshold | Decision rule | Source |
| --- | --- | --- | --- | --- |
| `TH-1` | Residual ratio `R_ratio` | `<= 1.0` | `CONVERGED` if true | OpenFOAM engineering practice |
| `TH-2` | Default target residual | `1e-5` | Case may override | controlDict-aligned default |
| `TH-3` | Oscillation ratio `osc` | `> 0.4` | `OSCILLATING` if true over final window | Project heuristic |
| `TH-4` | Residual window size `N` | `20` steps | Final-window trend analysis | Configurable project default |
| `TH-5` | Default relative tolerance | `5%` | Observable passes if `epsilon_rel <= 0.05` | Gold Standard default |
| `TH-6` | Zero-reference absolute tolerance | `1e-6` | Pass if `epsilon_abs <= 1e-6` | Engineering precision floor |
| `TH-7` | Mass imbalance `delta_m` | `<= 1%` pass, `<= 5%` warn, otherwise fail | L3 conservation classification | CFD practice |
| `TH-8` | Pass-with-deviations cutoff | `>= 70%` observables pass | `PASS_WITH_DEVIATIONS` if true and not full pass | Project definition |
| `TH-9` | Divergence detection | `r_final > 10 * r_initial` | `DIVERGED` if true | OpenFOAM engineering practice |

Threshold registry lines for contract grep checks:

TH-1: residual_ratio <= 1.0
TH-2: target_residual_default = 1e-5
TH-3: oscillation_ratio > 0.4
TH-4: residual_window = 20
TH-5: default_relative_tolerance = 0.05
TH-6: zero_reference_absolute_tolerance = 1e-6
TH-7: mass_imbalance_pass_warn_fail = 0.01 / 0.05
TH-8: pass_with_deviations_cutoff = 0.70
TH-9: divergence_if_final_gt_10x_initial

## Error Handling Matrix

| ID | Scenario | Detection | Handling action | Output consequence |
| --- | --- | --- | --- | --- |
| `ERR-1` | Missing or empty log file | file absent or size `== 0` | Skip direct residual parse | `convergence.status = UNKNOWN`, final verdict may fail |
| `ERR-2` | Missing Gold Standard data | no contract YAML or empty observables | Skip L2 comparison | `gold_standard_comparison.overall = SKIPPED` |
| `ERR-3` | Missing simulated observable | `observable.name not in sim_results` | Mark observable failed | Counts against pass ratio |
| `ERR-4` | Zero reference value | `abs(v_ref) < 1e-12` | Switch to `F-2` + `TH-6` | `rel_error = null`, `abs_error` populated |
| `ERR-5` | Non-finite simulation value | NaN or Inf | Mark observable failed and warn | Counts against pass ratio |
| `ERR-6` | Unparseable residual history | regex or parser failure | Keep L1 non-fatal | `convergence.status = UNKNOWN` |
| `ERR-7` | Missing postProcessing directory | directory absent | Fall back to log-only evidence | No crash |
| `ERR-8` | Missing inlet or outlet data | no boundary evidence for L3 | Skip conservation sub-check | `physics_check.status` may downgrade to `WARN` |

## Determinism

- Identical inputs must produce identical outputs except for the `timestamp` field.
- No randomness is permitted anywhere in AutoVerifier.
- Floating-point comparisons must use stable numeric tolerances and explicit formula selection.
- Canonical observable names and human-readable display labels must remain separate so that attribution logic never confuses profile point labels with schema keys.

## Test Matrix

| ID | Test | Input focus | Expected outcome | Type |
| --- | --- | --- | --- | --- |
| `T-1` | `test_l1_converged` | monotonic residual drop | `CONVERGED` | unit |
| `T-2` | `test_l1_oscillating` | >40% positive deltas | `OSCILLATING` | unit |
| `T-3` | `test_l1_diverged` | residual blow-up | `DIVERGED` | unit |
| `T-4` | `test_l1_missing_log` | absent log file | `UNKNOWN` + warning | unit |
| `T-5` | `test_l2_all_pass` | all observables within tolerance | overall `PASS` | unit |
| `T-6` | `test_l2_partial_pass` | 3/4 observables pass | `PASS_WITH_DEVIATIONS` | unit |
| `T-7` | `test_l2_fail` | low pass ratio | overall `FAIL` | unit |
| `T-8` | `test_l2_zero_ref` | zero reference value | absolute-error path | unit |
| `T-9` | `test_l2_nan_sim` | non-finite simulation value | failed observable + warning | unit |
| `T-10` | `test_l3_mass_conserved` | low mass imbalance | `PASS` | unit |
| `T-11` | `test_l3_mass_warning` | medium mass imbalance | `WARN` | unit |
| `T-12` | `test_l3_mass_fail` | high mass imbalance | `FAIL` | unit |
| `T-13` | `test_correction_spec_generated` | non-pass verdict | suggestion emitted | unit |
| `T-14` | `test_correction_spec_not_generated` | pass verdict | no suggestion | unit |
| `T-15` | `test_e2e_lid_driven_cavity` | OF-01 Docker evidence | valid report file | e2e |
| `T-16` | `test_e2e_backward_facing_step` | OF-02 Docker evidence | valid report file | e2e |
| `T-17` | `test_e2e_cylinder_crossflow` | OF-03 Docker evidence | valid report file | e2e |
| `T-18` | `test_report_yaml_schema` | any generated report | schema-valid YAML | unit |

## Integration Points

| ID | Module | Interface | Call direction | Notes |
| --- | --- | --- | --- | --- |
| `INT-1` | `TaskRunner` | `post_execute_hook(task_spec, exec_result, comparison_result, correction_spec) -> AutoVerificationReport` | `TaskRunner -> AutoVerifier` | Additive hook only; no mandatory Phase 1-7 rewrite |
| `INT-2` | `KnowledgeDB` | `get_gold_standard(case_id) -> Gold bundle or fallback record` | `AutoVerifier -> KnowledgeDB` | Loader may wrap legacy data when contract YAML is absent |
| `INT-3` | `Report Engine` | `load_auto_verify(case_id) -> AutoVerificationReport` | `Report Engine -> AutoVerifier output` | File-based handoff via YAML |
| `INT-4` | `Notion Sync` | `update_task_status(task_url, verify_result)` | `AutoVerifier output -> Notion sync layer` | Verdict only; no autonomous gate crossing |
