# Phase 9 Activation Review Package

> **CANONICAL.** This Package is the authoritative Phase 9 activation artifact
> under D4 gate verdict C1 (2026-04-18, self-Gate). The 169-line
> [PHASE9_ACTIVATION_REVIEW_PACKET.md](PHASE9_ACTIVATION_REVIEW_PACKET.md)
> is retained as a non-canonical supplement capturing the original
> review-intent framing.

## Gate Authority

- Reviewer: `Opus 4.7`
- Package prepared on: `2026-04-17`
- Requested decision: `activate or reject Phase 9`
- Current phase status: `Planned`
- Package purpose: `consolidate prerequisite completion evidence C18-C23 for the Phase 9 activation gate`
- Stop rule: `do not move Phase 9 from Planned to Active until Opus result is pasted back`

## 1. Gate Status

Phase 9 is `review-ready` but not yet active. The repo evidence shows that the Phase 9
opening work is still fenced to `planning only` and `planning_only` artifacts:

- [docs/design/PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md](/Users/Zhuanz/Desktop/cfd-harness-unified/docs/design/PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md)
- [docs/governance/PHASE9_MODEL_ROUTING_BASELINE_PLAN.md](/Users/Zhuanz/Desktop/cfd-harness-unified/docs/governance/PHASE9_MODEL_ROUTING_BASELINE_PLAN.md)
- [reports/baselines/phase9_model_routing_replay_manifest.yaml](/Users/Zhuanz/Desktop/cfd-harness-unified/reports/baselines/phase9_model_routing_replay_manifest.yaml)
- [docs/gates/PHASE9_ACTIVATION_REVIEW_PACKET.md](/Users/Zhuanz/Desktop/cfd-harness-unified/docs/gates/PHASE9_ACTIVATION_REVIEW_PACKET.md)

Readiness summary:

- Gate readiness: `READY FOR OPUS REVIEW`
- Runtime mutation status: `none`
- Default runtime posture: `single-engine OpenFOAM remains the default branch`
- External solver posture: `SU2 reference-only`, `CFX hold`
- Activation mode requested: `PASS WITH CONDITIONS`

Review note:
The repo does not persist literal `C18-C23` tags. This package normalizes those six
activation prerequisites into a deterministic evidence ledger so Opus can audit them
against local files rather than memory or Notion-only labels.

## 2. Evidence Sources

### Primary Activation Artifacts

- [docs/design/PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md](/Users/Zhuanz/Desktop/cfd-harness-unified/docs/design/PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md)
- [docs/governance/PHASE9_MODEL_ROUTING_BASELINE_PLAN.md](/Users/Zhuanz/Desktop/cfd-harness-unified/docs/governance/PHASE9_MODEL_ROUTING_BASELINE_PLAN.md)
- [reports/baselines/phase9_model_routing_replay_manifest.yaml](/Users/Zhuanz/Desktop/cfd-harness-unified/reports/baselines/phase9_model_routing_replay_manifest.yaml)
- [docs/gates/PHASE9_ACTIVATION_REVIEW_PACKET.md](/Users/Zhuanz/Desktop/cfd-harness-unified/docs/gates/PHASE9_ACTIVATION_REVIEW_PACKET.md)

### Repo-Truth Anchors

- [knowledge/skill_index.yaml](/Users/Zhuanz/Desktop/cfd-harness-unified/knowledge/skill_index.yaml)
- [src/foam_agent_adapter.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/foam_agent_adapter.py)
- [docs/gates/PHASE8A_OPUS_REVIEW_PACKAGE.md](/Users/Zhuanz/Desktop/cfd-harness-unified/docs/gates/PHASE8A_OPUS_REVIEW_PACKAGE.md)

### Notion References Captured In Repo

- Phase page: `45c8b97397ca46f2bef61795d9110715`
- Task `9a`: `345c68942bed814693d8dd9b76efb4f6`
- Task `9b`: `345c68942bed819cac7dd572b80ea8db`
- Task `9c`: `345c68942bed8176a085d09f23930a12`

## 3. C18-C23 Completion Ledger

| Condition | Status | Closure meaning | Evidence | Completion summary |
| --- | --- | --- | --- | --- |
| `C18` | `COMPLETE` | Gate remains frozen and reviewable | `PHASE9_ACTIVATION_REVIEW_PACKET.md`, replay manifest `status: planning_only`, task `9a/9b` artifacts marked `planning only` | Phase 9 is still `Planned`, stop rule is intact, and no activation drift is visible in repo artifacts |
| `C19` | `COMPLETE` | Task `9a` repo truth inventory and solver decision tree are prepared | `PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md` | SU2/CFX branch logic, plane separation, default branch, and stop conditions are documented |
| `C20` | `COMPLETE` | Task `9b` routing baseline design is prepared | `PHASE9_MODEL_ROUTING_BASELINE_PLAN.md` | Metrics, thresholds, replay set, determinism rules, and Solo Mode variance capture are defined |
| `C21` | `COMPLETE` | Task `9c` activation packaging and replay manifest are prepared | `PHASE9_ACTIVATION_REVIEW_PACKET.md`, `phase9_model_routing_replay_manifest.yaml`, this package | Activation evidence is assembled, replay slices are frozen, and governance review inputs are packaged |
| `C22` | `COMPLETE` | Default scope boundary is locked before activation | decision tree, activation packet, replay manifest notes | OpenFOAM remains default runtime, `SU2Executor` and `CFXExecutor` stay closed, Phase 7 runtime edits stay out of bounds |
| `C23` | `COMPLETE` | Parallel execution rules and Opus re-review triggers are locked | baseline plan, decision tree, replay manifest | Only bounded frozen slices may run in parallel; any execution-plane expansion requires a fresh Opus gate |

## 4. Task Completion Summary

### Task 9a - External Solver Touchpoint Inventory + SU2/CFX Decision Tree

- Status: `artifact complete`
- Deliverable: [docs/design/PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md](/Users/Zhuanz/Desktop/cfd-harness-unified/docs/design/PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md)
- Completion evidence:
  - repo-truth inventory recorded for execution plane, skill inventory, whitelist policy, and CFX absence
  - `SU2` is explicitly limited to `reference/tooling surface`
  - `CFX` is explicitly kept in `hold`
  - any `executor` opening is deferred to a later bounded sub-gate

### Task 9b - Model Routing v3.x Baseline Capture Plan

- Status: `artifact complete`
- Deliverable: [docs/governance/PHASE9_MODEL_ROUTING_BASELINE_PLAN.md](/Users/Zhuanz/Desktop/cfd-harness-unified/docs/governance/PHASE9_MODEL_ROUTING_BASELINE_PLAN.md)
- Completion evidence:
  - routing metrics are defined for `cost`, `latency`, `quality`, `determinism`, `override_rate`, and `scope_violation_count`
  - replay tracks `EX-1`, `PL-1`, and `SY-1` are bounded and frozen
  - baseline logic records `documented route` versus `actual route` for Solo Mode variance
  - runtime instrumentation is explicitly deferred until evidence shows it is required

### Task 9c - Activation Governance And Evidence Packaging

- Status: `artifact complete`
- Deliverables:
  - [docs/gates/PHASE9_ACTIVATION_REVIEW_PACKET.md](/Users/Zhuanz/Desktop/cfd-harness-unified/docs/gates/PHASE9_ACTIVATION_REVIEW_PACKET.md)
  - [docs/gates/PHASE9_ACTIVATION_REVIEW_PACKAGE.md](/Users/Zhuanz/Desktop/cfd-harness-unified/docs/gates/PHASE9_ACTIVATION_REVIEW_PACKAGE.md)
  - [reports/baselines/phase9_model_routing_replay_manifest.yaml](/Users/Zhuanz/Desktop/cfd-harness-unified/reports/baselines/phase9_model_routing_replay_manifest.yaml)
- Completion evidence:
  - activation decision request is packaged for `Opus 4.7`
  - stop rule and current phase state are restated in the gate docs
  - frozen replay slices and thresholds are bundled for bounded post-approval execution

## 5. SU2 / CFX Decisions

### SU2 Decision

- Decision: `allow only as reference/tooling surface`
- Evidence basis:
  - [knowledge/skill_index.yaml](/Users/Zhuanz/Desktop/cfd-harness-unified/knowledge/skill_index.yaml) contains `su2_harness`
  - [docs/design/PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md](/Users/Zhuanz/Desktop/cfd-harness-unified/docs/design/PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md) classifies `SU2` under `Branch B - reference-only external surface`
- Binding implication:
  - `SU2` may support discovery, benchmarking, comparison, or evidence gathering
  - `SU2` may not open runtime routing or `SU2Executor` work under default activation scope

### CFX Decision

- Decision: `hold`
- Evidence basis:
  - no first-class `CFX` touchpoint is recorded in the repo scan
  - [docs/design/PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md](/Users/Zhuanz/Desktop/cfd-harness-unified/docs/design/PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md) classifies `CFX` under the hold branch
- Binding implication:
  - no `CFX` runtime or executor work may open under default activation scope
  - any attempt to open `CFX` work must first produce a bounded proof-slice proposal and return to Opus

### Runtime Default

- Decision: `preserve single-engine OpenFOAM runtime`
- Evidence basis:
  - [src/foam_agent_adapter.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/foam_agent_adapter.py) remains OpenFOAM-centered and targets `cfd-openfoam`
  - the decision tree and activation packet both preserve OpenFOAM as the default activation branch

## 6. Default Scope Boundaries

### Default In Scope

- external solver touchpoint inventory
- `SU2` reference-only evaluation
- `CFX` hold-or-open assessment based on evidence
- model routing v3.x baseline capture design
- frozen replay execution after approval within `EX-1`, `PL-1`, `SY-1`
- activation governance, evidence packaging, and bounded summary artifacts

### Default Out Of Scope

- `SU2Executor`
- `CFXExecutor`
- dual-solver runtime routing
- whitelist execution-scope expansion
- changes to `task_runner`, `foam_agent_adapter`, or execution-side schemas
- runtime instrumentation before activation approval
- coupling Phase 9 work to Phase 7 in-flight runtime edits

### Default Boundary Rule

If work crosses from the `reference/evaluation plane` into the `execution plane`, it is
no longer in the default Phase 9 activation scope and must stop for a fresh Opus review.

## 7. Parallel Execution Rules

Phase 9 may use bounded parallelism only inside the planning and evidence lanes already
defined by the replay manifest and baseline plan.

Binding rules:

1. Only frozen replay slices `EX-1`, `PL-1`, and `SY-1` may be opened in parallel.
2. Parallel slices must reuse existing repo or Notion inputs; they may not depend on live
   mutation of runtime state.
3. No parallel slice may mutate `src/`, `tests/`, or `knowledge` runtime paths before
   Opus activation approval.
4. No parallel slice may touch Phase 7 in-flight runtime files.
5. Parallel execution is limited to planning, governance, documentation, dry-run sync, or
   bounded diagnostic memo generation.
6. Any slice that starts requiring solver scheduling, runtime I/O, or new executor logic
   must stop and escalate to a sub-gate.
7. Determinism must remain checkable by normalized diff or structural comparison for every
   replay slice.

## 8. Opus Review Triggers

### Activation Trigger

The activation review may be triggered now because `C18-C23` are packaged as complete and
the repo still preserves the stop rule and planning-only boundary.

### Mandatory Re-Review Triggers

Return to Opus before proceeding if any of the following becomes true:

1. a proposal names `SU2Executor` or `CFXExecutor`
2. a proposal changes runtime routing to select a non-OpenFOAM solver for execution
3. a proposal touches `task_runner`, `foam_agent_adapter`, or execution-side schemas
4. a proposal opens `CFX` beyond `hold`
5. a proof slice cannot stay bounded to one named case family, one measurable success
   criterion, and one additive integration boundary
6. baseline capture cannot derive required metrics from logs and artifacts and requests new
   runtime instrumentation
7. a slice starts touching Phase 7 in-flight runtime files
8. a proposal broadens from a bounded proof slice into general `multi-solver support`

## 9. Requested Gate Outcome

Recommended gate result:

- `PASS WITH CONDITIONS`

Requested activation posture:

1. Activate Phase 9 as `planning + bounded evaluation`.
2. Preserve `single-engine OpenFOAM runtime` as the default branch.
3. Allow `SU2` only as `reference/tooling surface`.
4. Keep `CFX` in `hold`.
5. Allow replay/baseline work only inside frozen bounded slices.
6. Require a fresh Opus sub-gate before any execution-plane expansion.

## 10. Acceptance Script

```bash
set -e

test -f docs/design/PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md
test -f docs/governance/PHASE9_MODEL_ROUTING_BASELINE_PLAN.md
test -f reports/baselines/phase9_model_routing_replay_manifest.yaml
test -f docs/gates/PHASE9_ACTIVATION_REVIEW_PACKET.md
test -f docs/gates/PHASE9_ACTIVATION_REVIEW_PACKAGE.md

for section in \
  "Gate Status" \
  "C18-C23 Completion Ledger" \
  "Task Completion Summary" \
  "SU2 / CFX Decisions" \
  "Default Scope Boundaries" \
  "Parallel Execution Rules" \
  "Opus Review Triggers"
do
  grep -q "$section" docs/gates/PHASE9_ACTIVATION_REVIEW_PACKAGE.md
done

grep -q "status: planning_only" reports/baselines/phase9_model_routing_replay_manifest.yaml
grep -q "Task anchor: \`Phase 9a" docs/design/PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md
grep -q "Task anchor: \`Phase 9b" docs/governance/PHASE9_MODEL_ROUTING_BASELINE_PLAN.md
grep -q "Current phase status: \`Planned\`" docs/gates/PHASE9_ACTIVATION_REVIEW_PACKAGE.md
```
