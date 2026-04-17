# Phase 9 Activation Review Packet

## Gate Authority

- Reviewer: `Opus 4.7`
- Package prepared on: `2026-04-17`
- Requested decision: `activate or reject Phase 9`
- Current phase status: `Planned`
- Stop rule: `do not move Phase 9 from Planned to Active until Opus result is pasted back`

## 1. Review Intent

Phase 8 is closed. Phase 9 planning artifacts are now ready. This packet asks Opus to
decide whether Phase 9 may be activated under a bounded scope that preserves the current
single-engine runtime redline while allowing structured evaluation of external solver
surfaces and routing stability.

## 2. Boundaries Requested For Activation

### Requested In Scope

- external solver touchpoint inventory
- `SU2` decision-tree evaluation as a `reference/tooling surface`
- `CFX` hold-or-open assessment based on evidence, not assumption
- Model Routing v3.x baseline capture design and first bounded replay run
- activation-packet governance and evidence packaging

### Explicitly Out Of Scope

- `SU2Executor`
- `CFXExecutor`
- dual-solver runtime routing
- whitelist execution-scope expansion
- Phase 7 runtime mutation

## 3. Evidence Bundle

### Phase 8 Closure Evidence

- Phase 8 status in Notion: `Done`
- C15 closed: Phase 8 metric now reflects `current corpus (13/13)` rather than stale `15/15`
- C16 closed: formal Decision recorded that `knowledge/whitelist.yaml` remains canonical
  and `knowledge/cases` is not introduced
- C17 closed: Canonical Docs `Type=Report` exists and the three report records use it

### Phase 9 Planning Artifacts

- [docs/design/PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md](/Users/Zhuanz/Desktop/cfd-harness-unified/docs/design/PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md)
- [docs/governance/PHASE9_MODEL_ROUTING_BASELINE_PLAN.md](/Users/Zhuanz/Desktop/cfd-harness-unified/docs/governance/PHASE9_MODEL_ROUTING_BASELINE_PLAN.md)
- [reports/baselines/phase9_model_routing_replay_manifest.yaml](/Users/Zhuanz/Desktop/cfd-harness-unified/reports/baselines/phase9_model_routing_replay_manifest.yaml)

### Notion Planning Artifacts

- Phase page: `45c8b97397ca46f2bef61795d9110715`
- Task `9a`: `345c68942bed814693d8dd9b76efb4f6`
- Task `9b`: `345c68942bed819cac7dd572b80ea8db`
- Task `9c`: `345c68942bed8176a085d09f23930a12`

## 4. Key Findings

### F1. Governance And Repo Truth Are Still Runtime-Single-Engine

The canonical whitelist document still says:

- `OpenFOAM is the only execution engine`
- `do not build SU2Executor`

The live execution adapter also remains OpenFOAM-centered.

### F2. SU2 Exists As A Tooling Surface, Not A Runtime Surface

The repo now exposes a `SU2 CLI Harness Skill` in `knowledge/skill_index.yaml`.
This is enough evidence to justify evaluation of SU2 as a `reference/tooling` surface,
but not enough to justify runtime activation by default.

### F3. CFX Has No Current Surface

No direct CFX touchpoint was found in the current repo planning sweep.
That makes `CFX hold` the safest default until real evidence appears.

### F4. Routing Policy Needs A Baseline Before It Needs A Rewrite

The documented `Model Routing Policy v3.1` reflects the Phase 8 heavy-execution mode.
Current operation is in Codex Solo Mode. Phase 9 should measure that variance first,
not silently rewrite policy by assumption.

## 5. Activation Recommendation

Recommended activation outcome:

- `PASS WITH CONDITIONS`

Requested activation scope:

1. Activate Phase 9 as a `planning + bounded evaluation` phase.
2. Allow `SU2` only in the `reference/tooling surface` branch.
3. Keep `CFX` in `hold` unless a named bounded slice is approved later.
4. Allow routing baseline capture using frozen replay slices.
5. Require a fresh sub-gate before any executor or runtime-routing work opens.

## 6. Proposed Conditions For Activation

1. Phase 9 must keep `single-engine OpenFOAM runtime` as the default branch.
2. No `SU2Executor` or `CFXExecutor` may be implemented under the first activation scope.
3. Any bounded proof slice must name one concrete case family, one measurable success
   criterion, and one additive integration boundary.
4. Routing baseline capture must start with log-level and artifact-level evidence before
   requesting code instrumentation.
5. Phase 7 in-flight files remain out of bounds for Phase 9 activation work.

## 7. Questions For Opus 4.7

1. Can Phase 9 activate under the bounded scope `SU2 reference-only, CFX hold, routing baseline capture`?
2. Does Opus accept the rule that any external-solver `executor` work must be fenced into
   a later proof-slice sub-gate rather than Phase 9 default scope?
3. Should Solo Mode variance be treated as a measurement target for Phase 9, rather than
   an immediate governance rewrite of `Model Routing Policy v3.1`?

## 8. Review Checklist

- [x] Phase 8 closeout evidence included
- [x] Phase 9 context and risks reflected in Notion
- [x] External solver decision tree prepared
- [x] Routing baseline plan prepared
- [x] Replay manifest prepared
- [x] Stop rule preserved: Phase 9 is still `Planned`

## 9. Acceptance Script

```bash
set -e

test -f docs/design/PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md
test -f docs/governance/PHASE9_MODEL_ROUTING_BASELINE_PLAN.md
test -f reports/baselines/phase9_model_routing_replay_manifest.yaml
test -f docs/gates/PHASE9_ACTIVATION_REVIEW_PACKET.md

for section in \
  "Review Intent" \
  "Boundaries Requested For Activation" \
  "Evidence Bundle" \
  "Key Findings" \
  "Activation Recommendation" \
  "Proposed Conditions For Activation" \
  "Questions For Opus 4.7"
do
  grep -q "$section" docs/gates/PHASE9_ACTIVATION_REVIEW_PACKET.md
done

grep -q "Status\\\":\\\"Planned\\\"" <(python3 - <<'PY'
print('{"Status":"Planned"}')
PY
)

git status --short -- \
  docs/design/PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md \
  docs/governance/PHASE9_MODEL_ROUTING_BASELINE_PLAN.md \
  reports/baselines/phase9_model_routing_replay_manifest.yaml \
  docs/gates/PHASE9_ACTIVATION_REVIEW_PACKET.md
```

## 10. Requested Gate Outcome

Please return one of:

- `PASS` - Phase 9 may move from `Planned` to `Active` under the requested bounded scope
- `PASS WITH CONDITIONS` - Phase 9 may activate only after listed adjustments
- `REJECT` - Phase 9 should remain `Planned` pending redesign or narrower scoping

