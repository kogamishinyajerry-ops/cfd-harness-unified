# Phase 9 Model Routing v3.x Baseline Plan

## Status

- Phase: `9`
- Task anchor: `Phase 9b - Model Routing v3.x baseline capture plan`
- Prepared on: `2026-04-17`
- Document type: `design / planning`
- Scope of this artifact: `planning only — no runtime changes`
- Supersedes: `docs/governance/PHASE9_MODEL_ROUTING_BASELINE_PLAN.md` (v3.1-era, pre-replay)

---

## v3.1 vs v3.x Delta Analysis

The governing policy file `docs/governance/MODEL_ROUTING_POLICY.md` **does not exist** in the repo.
The v3.1 baseline is therefore reconstructed from the pre-replay governance plan and the
replay manifest. The table below captures every dimension that changed between the v3.1
draft state and the v3.x post-replay state.

| Dimension | v3.1 (pre-replay governance plan) | v3.x (post-SY-1 replay) |
|---|---|---|
| Policy basis | `MODEL_ROUTING_POLICY.md` — absent; derived from `.claude/MODEL_ROUTING.md` (Solo Mode, v1.3) | Same policy basis; Solo Mode variance explicitly tracked |
| Routing scope | Implicit single-track (solo execution) | Explicit 3-track separation: EX-1 / PL-1 / SY-1 |
| Metric set | 7 metrics (prompt_tokens, completion_tokens, wall_clock_latency_s, quality_score, determinism_grade, override_rate, scope_violation_count) | 8 metrics — adds `estimated_cost_usd` |
| Latency threshold | Single threshold: `<= 180s` (planning/sync) | Per-track thresholds: SY-1/PL-1 `<= 180s`, EX-1 `<= 300s` |
| Quality threshold | `>= 4.0/5.0` (global) | Same `>= 4.0/5.0`; now anchored to a 5-dimension rubric |
| Cost measurement | Not defined | `estimated_cost_usd` added — must be derivable from token counts + pricing table |
| Determinism | Stated as required, no capture method | Normalized diff protocol: strip timestamps/sessionIDs/temp paths before compare |
| Override tracking | `<= 10%` stated | Same rate; SY-1 marks as N/A (sync slice — no routing decisions made) |
| Baseline readings | None captured | SY-1 captured: quality=5.0, determinism=PASS, scope_violation=0 |
| Acceptance gate | Not defined | D4 gate defined: SY-1 trigger stops drafting until Opus review |
| Governance annotation | None | Note added to `docs/governance/PHASE9_MODEL_ROUTING_BASELINE_PLAN.md`: policy file missing |

### Key Architectural Shift

**v3.1** treated routing policy as implicit Solo Mode behavior with no formal track separation.

**v3.x** formalizes three bounded replay tracks and requires each to be measured independently
against per-track thresholds. The orchestrator/executor split assumed in the original policy
is acknowledged as **not yet active** (Solo Mode in use); variance between documented and
actual route is recorded, not silently ignored.

---

## Metric Glossary (v3.x — 8 metrics)

| Metric | Unit | Definition | Capture source | v3.1 threshold | v3.x threshold |
|---|---|---|---|---|---|
| `prompt_tokens` | tokens | Input tokens consumed for one bounded replay slice | provider/app usage export | record, no drop | record, no drop |
| `completion_tokens` | tokens | Output tokens consumed for one bounded replay slice | provider/app usage export | record, no drop | record, no drop |
| `estimated_cost_usd` | USD | Derived from token counts x active pricing table at run time | billing sheet or pricing snapshot | not defined | must be derivable for every measured slice |
| `wall_clock_latency_s` | seconds | End-to-end time from dispatch start to artifact-ready output | command timestamps + task log | `<= 180s` global | **per-track** (see Replay Set) |
| `quality_score` | 1-5 rubric | Average of 5-dimension rubric (see Quality Rubric section) | human rubric + acceptance checklist | `>= 4.0/5.0` | `>= 4.0/5.0` (global floor) |
| `determinism_grade` | pass/fail | Same replay slice yields structurally identical output on rerun | artifact hash or normalized diff | PASS | PASS (all tracks) |
| `override_rate` | percent | Fraction of slices requiring manual reroute or model-role correction | session log + routing notes | `<= 10%` | `<= 10%` (EX-1 / PL-1 only; N/A for SY-1) |
| `scope_violation_count` | count | Times slice touches forbidden paths or crosses gate boundaries | git diff + task notes | `0` | `0` (all tracks) |

---

## Baseline Readings (v3.1 — from replay manifest)

Source: `reports/baselines/phase9_model_routing_replay_manifest.yaml`

### SY-1 (Sync / Documentation Track) — Captured 2026-04-17T07:10:00Z

| Metric | Value | Notes |
|---|---|---|
| `wall_clock_latency_s` | `DRY_RUN_NO_OP` | Sync slice is passive; no live execution |
| `prompt_tokens` | N/A | Dry-run — no live token consumption |
| `completion_tokens` | N/A | Dry-run — no live token consumption |
| `estimated_cost_usd` | N/A | Dry-run — no cost incurred |
| `quality_score` | **5.0 / 5.0** | All 5 rubric dimensions satisfied |
| `determinism_grade` | **PASS** | Schema v2 deterministic; no non-deterministic fields |
| `override_rate` | N/A | Sync/documentation slice — no routing decisions |
| `scope_violation_count` | **0** | Phase 7 isolation: CLEAR |

Contract checks (all satisfied):
- `auto_verify_report.yaml` schema v2 compliant
- `gold_standard_comparison.overall = PASS`
- `convergence.status = CONVERGED`
- `physics_check.status = PASS`
- `verdict = PASS`
- `correction_spec_needed = false`

### PL-1 (Planning / Governance Track) — Not yet captured

Status: pending D4 gate clearance.

### EX-1 (Execution-Diagnostic Track) — Not yet captured

Status: pending D4 gate clearance.

---

## Replay Set (v3.x)

Three bounded tracks. All use frozen repo/Notion inputs. No live solver mutation.

### Track EX-1 — Execution-Diagnostic Slice

- **Intent**: measure routing on a bounded engineering/diagnostic task
- **Inputs**:
  - `src/foam_agent_adapter.py`
  - `docs/design/PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md`
  - `docs/gates/PHASE8A_OPUS_REVIEW_PACKAGE.md`
- **Expected output**: one bounded diagnostic memo or fix-plan artifact
- **Latency threshold**: `<= 300s` (execution slice — longer bound)
- **Cost capture required**: yes
- **Override rate applicable**: yes
- **Determinism check**: rerun and compare normalized markdown
- **Status**: awaiting D4 clearance

### Track PL-1 — Planning / Governance Slice

- **Intent**: measure routing on a contract-writing or decision-packaging task
- **Inputs**:
  - `docs/design/PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md`
  - `docs/governance/PHASE9_MODEL_ROUTING_BASELINE_PLAN.md`
  - Notion Phase 9 context
- **Expected output**: one planning artifact or activation-ready summary
- **Latency threshold**: `<= 180s`
- **Cost capture required**: yes
- **Override rate applicable**: yes
- **Determinism check**: rerun and compare normalized markdown
- **Status**: awaiting D4 clearance

### Track SY-1 — Sync / Documentation Slice

- **Intent**: measure routing on structured documentation or Notion-sync work
- **Inputs**:
  - `reports/lid_driven_cavity_benchmark/auto_verify_report.yaml`
  - `reports/lid_driven_cavity_benchmark/report.md`
  - Notion Phase 8 closeout
- **Expected output**: one dry-run sync summary or structured payload
- **Latency threshold**: `<= 180s`
- **Cost capture required**: yes (but dry-run produces N/A)
- **Override rate applicable**: no (N/A for sync slice)
- **Determinism check**: rerun and compare normalized yaml/json
- **Status**: baseline captured — D4 gate triggered, Opus review required

---

## Capture Source Specification

| Metric | Primary source | Fallback | Notes |
|---|---|---|---|
| `prompt_tokens` / `completion_tokens` | provider/app usage export | command-line metering (`--usage` flag) | Must be captured per-slice, not aggregated |
| `estimated_cost_usd` | token counts x pricing table snapshot | billing sheet | Pricing table version must be recorded with each reading |
| `wall_clock_latency_s` | command timestamps (dispatch start → artifact-ready) | task log entries | SY-1 is DRY_RUN_NO_OP — no live clock |
| `quality_score` | 5-dimension rubric (see below) | n/a | All 5 dimensions must be scored independently |
| `determinism_grade` | normalized diff (strip timestamps/sessionIDs/temp paths) | artifact hash (byte-identical fallback) | Any non-deterministic field must be listed and normalized, not ignored |
| `override_rate` | session log + routing notes | manual annotation | SY-1 is N/A |
| `scope_violation_count` | git diff + task notes | manual audit | Hard 0 — any violation stops the slice |

---

## Quality Rubric (v3.x — 5 dimensions, each 1-5)

Score every replay slice on all five dimensions. Final `quality_score` = average.

| Dimension | 1 | 3 | 5 |
|---|---|---|---|
| **Contract fidelity** | Output violates scope or crosses gate bounds | Output partially within scope | Output fully within allowed scope |
| **Evidence use** | Output ignores repo/Notion truth | Output partially grounded | Output grounded in named repo/Notion sources |
| **Actionability** | Output cannot drive next step | Output partially actionable | Output is directly usable for the next step |
| **Risk handling** | Gates, forbidden paths, or stop rules violated | Partial compliance | All gates, forbidden paths, and stop rules respected |
| **Clarity** | Output requires significant interpretation | Partially clear | Artifact is self-contained and understandable |

**Floor**: `quality_score >= 4.0/5.0` required for acceptance. Any single dimension scored 1 disqualifies the slice.

---

## Acceptance Thresholds

### Per-Track Thresholds

| Track | `wall_clock_latency_s` max | `quality_score` min | `determinism_grade` | `override_rate` max | `scope_violation_count` max |
|---|---|---|---|---|---|
| EX-1 | 300s | 4.0 | PASS | 10% | 0 |
| PL-1 | 180s | 4.0 | PASS | 10% | 0 |
| SY-1 | 180s (DRY_RUN_NO_OP accepted) | 4.0 | PASS | N/A | 0 |

### Cost Anomaly Threshold

Any slice where `estimated_cost_usd` deviates more than **20%** from the expected cost
for the same track's token estimate should be flagged for review before acceptance.

### Override Rate Interpretation

- `0-5%`: Expected for a mature routing policy — minor corrections only
- `5-10%`: Acceptable; document the correction categories
- `> 10%`: Stop and review — routing policy is misaligned with task distribution
- `N/A`: Track SY-1 (sync/documentation) — no routing decisions made

### Determinism Failure Protocol

If a slice fails determinism (output differs on rerun):
1. Identify the non-deterministic field(s)
2. Normalize the field(s) and re-evaluate
3. If normalization is not possible, flag as `NON_DETERMINISTIC` and exclude from baseline
4. Document the field(s) and cause in the capture report

### Physics-Validity Precheck Schema (post D4+ verdict 2026-04-18, C2 blocking)

Every EX-1 slice that touches solver config, comparator logic, or gold-standard contracts MUST record a `physics_validity_precheck` block in `slice_metrics.yaml`. This closes the methodology gap exposed by EX-1-002 (R-C pivot) where a code-bounded remediation had an unmet physics precondition that would have produced a false PASS.

Required schema:

```yaml
physics_validity_precheck:
  performed: true | false
  preconditions_enumerated:
    - "<natural-language precondition>"
    - ...
  all_satisfied: true | false
  evidence_refs:
    - "<file:line or commit hash establishing each precondition's state>"
```

Enforcement rules (auto-judged at acceptance time, OR-combined):

1. `performed == false` → `determinism_grade = FAIL` (the slice failed to do the precheck, not to be deterministic — but by contract we treat missing-precheck as a determinism class failure since reruns cannot be distinguished from physics-invalid output).
2. `performed == true AND all_satisfied == false AND override_rate < 1.0` → `determinism_grade = FAIL`. Landing a remediation with unmet preconditions without an honest abort is an undetected-invalidity class, graver than a missing precheck.
3. `performed == true AND all_satisfied == false AND override_rate == 1.0` → slice accepted as honest abort (the EX-1-002 pattern). Commit message MUST cite `file:line` evidence for at least one unmet precondition; absence of such citation triggers rule 4.
4. `override_rate == 1.0` without `file:line` citation in commit body → slice `scope_violation_count` auto-set to 1, **not** counted toward rolling `override_rate` (prevents "override=1.0 as universal excuse").

Tracks where the block is REQUIRED: EX-1 always. PL-1 when the slice touches solver/physics contracts (otherwise optional). SY-1 optional — sync slices rarely touch physics.

### Rolling Override Rate Thresholds (post D4+ verdict, supersedes bare 10% rule for EX-1)

EX-1 triggers methodology Gate on ANY of:

1. Rolling average `> 0.30` at `n >= 4` slices (baseline rule)
2. Two consecutive slices with `override_rate >= 0.5` at any n (pattern rule)
3. Attempt to commit an EX-1 slice while prior `physics_validity_precheck` schema is not present in its `slice_metrics.yaml` (blocking rule — pre-commit local check)
4. Any pivot whose abandoned preconditions are not enumerated in the diagnostic memo or metrics (behavioral rule)

At `n == 5` EX-1 slices with no hard rule triggered, a lightweight methodology mini-review is still run (does NOT freeze the track) to re-examine the `physics_precondition` annotations in EX-1-001 memo §4 against observed implementation experience.

---

## Solo Mode Variance Tracking

The v3.1 policy assumes an orchestrator/executor split. Current operation is Codex Solo Mode.
Every baseline capture must record:

| Field | Value |
|---|---|
| `documented_route` | What the policy says should happen (per `.claude/MODEL_ROUTING.md` v1.3) |
| `actual_route` | What the current Solo Mode actually does |
| `variance` | Whether the difference is temporary (Solo Mode) or governance-significant |

This prevents treating a temporary operating mode as an implicit policy rewrite.

---

## Governance Annotations

### Note to `docs/governance/PHASE9_MODEL_ROUTING_BASELINE_PLAN.md`

> **Annotation added 2026-04-17**: The policy file `docs/governance/MODEL_ROUTING_POLICY.md`
> referenced as v3.1 basis does not exist in the repo. The v3.1 baseline is reconstructed
> from `docs/governance/PHASE9_MODEL_ROUTING_BASELINE_PLAN.md` (pre-replay governance plan)
> and `reports/baselines/phase9_model_routing_replay_manifest.yaml`. This document
> (`docs/design/PHASE9_MODEL_ROUTING_V3X_BASELINE_PLAN.md`) serves as the v3.x baseline
> plan and should be referenced as the authoritative tracking document for Phase 9b.

---

## Non-Goals

- do not change `MODEL_ROUTING_POLICY` during planning (policy file absent — do not fabricate policy text)
- do not add new model SDK dependencies
- do not add runtime instrumentation before activation approval
- do not couple baseline capture to Phase 7 in-flight code edits
- do not treat Solo Mode as an implicit policy rewrite

---

*Baseline plan: v3.x — Phase 9b, 2026-04-17*
