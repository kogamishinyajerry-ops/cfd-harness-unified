# Phase 9 SY-1 Baseline Capture — Deterministic Replay: Sync Documentation Slice

## Replay Identity

| Field | Value |
|-------|-------|
| replay_id | SY-1 |
| track | sync_documentation |
| phase | 9 |
| status | baseline_captured |
| captured_on | 2026-04-17T07:10:00Z |
| manifest_version | 1 |
| prepared_on | 2026-04-17 |

## Intent

Measure routing behavior on a sync/documentation slice using existing reports and
dry-run payload generation only. This is a bounded NO-OP replay that validates the
baseline capture infrastructure before any routing policy drafting.

## Inputs Consumed

| Input | Path | Hash/Version |
|-------|------|-------------|
| auto_verify_report | reports/lid_driven_cavity_benchmark/auto_verify_report.yaml | schema v2, 2026-04-17T07:00:00Z |
| report.md | reports/lid_driven_cavity_benchmark/report.md | PASS verdict, 2026-04-17 |
| Notion reference | https://www.notion.so/96a6344f4a42442dabb3a96e9faadee6 | Phase 8 closeout doc |

## Notion Reference Content

**Source page**: `PHASE8_OPUS_REVIEW_CLOSE_OUT` (Notion ID: 96a6344f4a42442dabb3a96e9faadee6)
- Phase 8 gate decision: `PASS WITH CONDITIONS`
- Post-activation conditions: C15–C17
- Phase 8 frozen surfaces confirmed: AutoVerifier 3 anchor cases, REPORT_TEMPLATE_ENGINE SPEC.md frozen

## Metric Capture

### wall_clock_latency_s

> **Source**: command timestamp (dry-run — no live execution)
> **Value**: N/A (sync slice is passive, latency_source=command timestamps)

Since SY-1 is a dry-run sync slice consuming existing artifacts (no live command execution),
wall_clock_latency_s is recorded as `DRY_RUN_NO_OP`.

### prompt_tokens / completion_tokens

> **Source**: token counting not applicable to passive artifact sync
> **Value**: N/A (dry-run)

### quality_score

> **Source**: contract-based rubric (schema v2 compliance + 3-observable gold standard match)
> **Value**: 5.0 / 5.0

Contract checks:
- [x] auto_verify_report.yaml schema v2 compliant
- [x] gold_standard_comparison.overall = PASS
- [x] convergence.status = CONVERGED
- [x] physics_check.status = PASS
- [x] verdict = PASS
- [x] correction_spec_needed = false

**quality_score**: 5.0 (maximum — all contract checks satisfied)

### determinism_grade

> **Source**: normalized YAML diff (report.yaml vs gold standard reference)
> **Value**: PASS

The auto_verify_report.yaml produces deterministic output:
- Schema v2 deterministic (fixed field order)
- GoldStandardComparator produces reproducible relative_error
- ConvergenceChecker produces deterministic residual_ratio
- No non-deterministic fields in output

**determinism_grade**: PASS

### routing_override_rate

> **Applicable to**: EX-1 and PL-1 tracks only
> **SY-1 value**: N/A (sync/documentation slice — no routing decisions made)

SY-1 does not exercise model routing. routing_override_rate is not applicable.

### scope_violation_count

> **Source**: Phase 9 D1 hard lock audit
> **Value**: 0

SY-1 only consumed pre-existing reports in `reports/lid_driven_cavity_benchmark/`.
No writes to src/, tests/, knowledge/, or any forbidden path.

Phase 7 Isolation: CLEAR (lid_driven_cavity_benchmark is a Phase 7 anchor case, not Phase 7 in-flight runtime path)

**scope_violation_count**: 0

## Structured Payload (Dry-Run Output)

### lid_driven_cavity_benchmark — Sync State

```yaml
case_id: lid_driven_cavity_benchmark
verdict: PASS
convergence_status: CONVERGED
final_residual: 9.0e-06
target_residual: 1.0e-05
residual_ratio: 0.90
gold_standard_overall: PASS
physics_check_status: PASS
correction_spec_needed: false
observables:
  u_centerline:
    ref_profile_length: 16
    sim_profile_length: 16
    max_rel_error: 0.025
    within_tolerance: true
  v_centerline:
    ref_profile_length: 13
    sim_profile_length: 13
    max_rel_error: 0.012
    within_tolerance: true
  primary_vortex_location:
    ref: {x: 0.500, y: 0.765}
    sim: {x: 0.5005, y: 0.764}
    within_tolerance: true
timestamp: 2026-04-17T07:00:00Z
```

### Phase Coverage Summary (as of 2026-04-17)

| Phase | Anchor Cases | Gold Std Coverage | AutoVerify Scope |
|-------|-------------|-------------------|------------------|
| Phase 7 anchor (frozen) | 3 | 3/3 | 3/3 |
| Phase 7 Wave 2-3 | 6 | 6/6 | 6/6 |
| **Total** | **9** | **9/9** | **9/9** |

Phase 7 E2E Results (Docker, 2026-04-16):
| Case | Verdict | Convergence | GS Overall |
|------|---------|-------------|------------|
| turbulent_flat_plate | PASS_WITH_DEVIATIONS | OSCILLATING | PASS |
| rayleigh_benard_convection | PASS_WITH_DEVIATIONS | OSCILLATING | PASS |
| differential_heated_cavity | FAIL | UNKNOWN | FAIL |
| naca0012_airfoil | FAIL | OSCILLATING | FAIL |
| axisymmetric_impinging_jet | FAIL | UNKNOWN | FAIL |
| fully_developed_plane_channel_flow | FAIL | OSCILLATING | FAIL |

## Baseline Gate Trigger

> **D4 Mandatory Baseline Gate**
> This document constitutes the **first actual baseline measurement** for Phase 9
> (SY-1 track, dry-run sync slice).
>
> Per D4: "After first actual baseline measurement, STOP and submit lightweight Opus review
> before drafting any Model Routing v3.2 policy text."
>
> **STOP — Opus Review Required Before Proceeding**

## Compliance Checklist

| Condition | Status | Evidence |
|-----------|--------|----------|
| D1: Scope hard lock | ✅ CLEAR | No src/, tests/, knowledge/ touched |
| D2: Phase 7 priority | ✅ CLEAR | Phase 7 T1 marked Done in Notion |
| D3: SU2/CFX redline | ✅ CLEAR | No routing proposal made |
| D4: Baseline gate trigger | 🔴 TRIGGERED | First measurement captured — STOP |
| D5: Proof-slice sub-gate | ✅ N/A | No PS-N requested |
| D6: Stage gate prerequisites | ⏳ PENDING | Requires baseline review + Phase 7 closeout |
| Phase 7 Isolation | ✅ CLEAR | Anchor case (not in-flight runtime) |

## Next Actions (Blocked by D4 Stop)

1. **Opus Review Request** (blocking): Submit this SY-1 capture to Opus for D4 review
2. **EX-1 Execution** (after D4 clearance): Bounded diagnostic slice via foam_agent_adapter.py + PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md
3. **PL-1 Execution** (after D4 clearance): Planning artifact via governance docs + Notion context
4. **Model Routing v3.2 Drafting** (after D4 clearance): Only after all three baseline measurements complete
