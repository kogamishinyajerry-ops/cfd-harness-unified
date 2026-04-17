# Phase 9 Model Routing v3.x Baseline Plan

## Status

- Phase: `9`
- Task anchor: `Phase 9b - Model Routing v3.x baseline capture plan`
- Prepared on: `2026-04-17`
- Scope of this artifact: `planning only`
- Runtime changes in this artifact: `none`

## Objective

Define a reproducible baseline plan for routing performance without changing the current
runtime during planning. The plan must be good enough to support a future Opus activation
review and precise enough to detect whether the documented routing policy and the actual
operating mode have diverged.

## Baseline Questions

1. What does `cost` mean for routing in a way that can be measured consistently?
2. What is the acceptable `latency` for bounded execution, planning, and sync slices?
3. How do we judge `quality` without relying on vague statements like `better`?
4. How do we measure `determinism` and `human override rate` in a routing workflow?
5. How do we compare documented routing policy against the current Solo Mode reality?

## Metric Glossary

| Metric | Unit | Definition | Capture source | Initial threshold |
| --- | --- | --- | --- | --- |
| `prompt_tokens` | tokens | Input tokens consumed for one bounded replay slice | provider/app logs or agent-side usage export | record, do not drop |
| `completion_tokens` | tokens | Output tokens consumed for one bounded replay slice | provider/app logs or agent-side usage export | record, do not drop |
| `estimated_cost_usd` | USD | Price derived from token counts and the active pricing table at run time | billing sheet or explicit pricing snapshot | must be derivable for every measured slice |
| `wall_clock_latency_s` | seconds | End-to-end time from dispatch start to artifact-ready output | command timestamps and task log | `<= 180s` for planning/sync slices, `<= 300s` for diagnostic slices |
| `quality_score` | 1-5 rubric | Review score against task contract, bounded scope, and evidence quality | human rubric + acceptance checklist | `>= 4.0/5.0` |
| `determinism_grade` | pass/fail | Same replay slice yields structurally identical outputs twice | artifact hash or normalized diff | `PASS` for all planning artifacts |
| `override_rate` | percent | Fraction of slices requiring manual reroute or model-role correction | session log and routing notes | `<= 10%` |
| `scope_violation_count` | count | Number of times a replay slice touches forbidden paths or crosses gate bounds | git diff + task notes | `0` |

## Replay Set Design

The replay set should stay bounded and reuse frozen inputs already present in the repo or
Notion. It should not depend on live mutation of Phase 7 runtime state.

### Track A - Execution-Diagnostic Slice

- Intent: measure routing on a bounded engineering/diagnostic task
- Frozen input sources:
  - `src/foam_agent_adapter.py`
  - one existing Docker/E2E evidence bundle
  - one existing acceptance contract
- Example shape:
  - identify whether a named diagnostic question can be answered without widening scope

### Track B - Planning / Governance Slice

- Intent: measure routing on a contract-writing or decision-packaging task
- Frozen input sources:
  - Phase page
  - task contracts
  - existing gate ruling
- Example shape:
  - produce or update one bounded planning artifact

### Track C - Sync / Documentation Slice

- Intent: measure routing on structured documentation or Notion-sync work
- Frozen input sources:
  - `report.md`
  - `auto_verify_report.yaml`
  - Canonical Docs schema
- Example shape:
  - generate or validate a sync-ready summary without changing runtime code

## Capture Matrix

| Replay ID | Track | Inputs | Expected output | Determinism check | Notes |
| --- | --- | --- | --- | --- | --- |
| `EX-1` | Execution-diagnostic | frozen repo files + bounded task question | one diagnostic memo or bounded fix plan | rerun and compare normalized markdown | avoid live solver execution during baseline planning |
| `PL-1` | Planning/governance | Phase 9 contract + whitelist redline + gate context | one planning artifact | rerun and compare normalized markdown | ideal for routing-policy comparison |
| `SY-1` | Sync/documentation | existing `report.md` and `auto_verify_report.yaml` | one sync-ready summary or dry-run payload | rerun and compare normalized yaml/json | must preserve `suggest-only` wording |

## Quality Rubric

Score every replay slice on a 1-5 scale using the same rubric:

1. `Contract fidelity` - did the output stay within allowed scope?
2. `Evidence use` - did the output ground itself in repo/Notion truth?
3. `Actionability` - can the output be used directly for the next step?
4. `Risk handling` - were gates, forbidden paths, and stop rules respected?
5. `Clarity` - is the artifact understandable without extra interpretation?

The final `quality_score` is the average of these five dimensions.

## Determinism Rules

- normalize timestamps, absolute temporary paths, and session IDs before comparison
- compare either byte-identical output or normalized structural equality
- any nondeterministic field must be explicitly listed and normalized, not ignored ad hoc

## Solo Mode Variance

The documented Phase 8 routing policy (`v3.1`) assumes an orchestrator/executor split.
Current operation is in Codex Solo Mode. The baseline must therefore record:

- `documented route`: what the policy says should happen
- `actual route`: what the current operating mode actually does
- `variance`: where the two differ and whether that difference is temporary or governance-significant

This avoids treating a temporary operating mode as an implicit policy rewrite.

## Recommendation

Start Phase 9 with `log-level capture + bounded replay artifacts` rather than code
instrumentation. Only add runtime instrumentation if the first bounded baseline run shows
that one or more metrics cannot be derived reliably from existing logs, artifact hashes,
and task execution notes.

## Non-Goals

- change `MODEL_ROUTING_POLICY` during planning
- add new model SDK dependencies
- add runtime instrumentation before activation approval
- couple baseline capture to Phase 7 in-flight code edits

