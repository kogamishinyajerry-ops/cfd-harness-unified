# Phase 8a Opus 4.6 Review Package

## Gate Authority

- Reviewer: `Opus 4.6`
- Package prepared on: `2026-04-17`
- Requested decision: `approve or reject implementation start for Task 8a-2`
- Current task boundary: `docs/specs`, `docs/design`, `docs/gates`, `knowledge/gold_standards/*.yaml`
- Stop rule: `do not begin implementation until Opus result is pasted back`

## 1. Architecture Overview

AutoVerifier is proposed as an additive post-execution verification layer with three independent checks:

1. `L1 ResidualChecker`
2. `L2 GoldStandardChecker`
3. `L3 PhysicalPlausibilityChecker`

The system keeps existing Phase 1-7 behavior stable by introducing a future optional `post_execute_hook` seam rather than replacing the current `TaskRunner` path in this task.

Key design properties:

- `suggest-only`, never auto-applies corrections
- explicit per-observable tolerance ownership
- contract-normalized Gold Standard aliases for OF-01/02/03
- file-based handoff to later `Report Engine`

## 2. Scope

### In Scope For Task 8a-1

- [docs/specs/AUTO_VERIFIER_SPEC.md](/Users/Zhuanz/Desktop/cfd-harness-unified/docs/specs/AUTO_VERIFIER_SPEC.md)
- [docs/design/AUTO_VERIFIER_ARCHITECTURE.md](/Users/Zhuanz/Desktop/cfd-harness-unified/docs/design/AUTO_VERIFIER_ARCHITECTURE.md)
- [docs/gates/PHASE8A_OPUS_REVIEW_PACKAGE.md](/Users/Zhuanz/Desktop/cfd-harness-unified/docs/gates/PHASE8A_OPUS_REVIEW_PACKAGE.md)
- Contract alias Gold Standards:
  - [lid_driven_cavity_benchmark.yaml](/Users/Zhuanz/Desktop/cfd-harness-unified/knowledge/gold_standards/lid_driven_cavity_benchmark.yaml)
  - [backward_facing_step_steady.yaml](/Users/Zhuanz/Desktop/cfd-harness-unified/knowledge/gold_standards/backward_facing_step_steady.yaml)
  - [cylinder_crossflow.yaml](/Users/Zhuanz/Desktop/cfd-harness-unified/knowledge/gold_standards/cylinder_crossflow.yaml)

### Explicitly Out Of Scope For Task 8a-1

- `src/`
- `tests/`
- `templates/`
- `reports/`
- `knowledge/skill_index.yaml`

### If Approved, Task 8a-2 May Proceed On

- `src/auto_verifier/`
- `tests/test_auto_verifier/`
- `reports/*/auto_verify_report.yaml`

## 3. Risk Assessment

### R1. Tolerance Misclassification

Risk:
AutoVerifier may mislabel valid CFD output as failing if tolerances are implicit or inherited inconsistently.

Mitigation:
The gate package establishes explicit observable-level tolerances in contract-aligned YAML aliases for OF-01/02/03 and binds the fallback order in the spec.

### R2. Contract Path Drift Versus Repo Reality

Risk:
The Notion contract references filenames and structures that do not exactly match the current repo.

Mitigation:
This task introduces additive contract alias YAML files rather than rewriting legacy multi-document Gold Standards. That preserves backward compatibility and gives implementation a stable input surface.

### R3. Phase 8 Scope Creep

Risk:
AutoVerifier design may sprawl into report templating, skill indexing, or automatic correction execution.

Mitigation:
Task scope is fenced by allowed paths only. The review package calls out exact out-of-scope modules, and the design locks `suggest-only` as a hard rule.

### R4. Integration Regression

Risk:
Future implementation may overreach into current `TaskRunner` behavior and destabilize Phase 1-7 flows.

Mitigation:
The architecture defines an additive optional hook boundary. No runtime file is modified in this task, and Opus is asked to review the seam before implementation begins.

## 4. Recommendation

Recommendation to Opus:

- `APPROVE WITH CONDITIONS` if the additive hook boundary is accepted and contract alias YAML is accepted as the Phase 8a canonical input surface.
- `REJECT` if Opus requires a different integration seam or rejects the alias-file normalization strategy.

Binding conditions for implementation start:

1. AutoVerifier remains `suggest-only`.
2. Task 8a-2 must stay inside `src/auto_verifier/`, `tests/test_auto_verifier/`, and report output paths.
3. Coverage for new module must be `>= 80%`.
4. No Phase 1-7 runtime path may be broken to satisfy Phase 8.

## 5. Acceptance Script

The following script is the gate package validation script for Task 8a-1:

Review note:
Task `8a-1` is validated on its owned artifacts only. Phase 7 may have parallel in-flight edits elsewhere in the repo, and those files are out of scope for this architecture gate.

```bash
set -e

test -f docs/specs/AUTO_VERIFIER_SPEC.md
test -f docs/design/AUTO_VERIFIER_ARCHITECTURE.md
test -f docs/gates/PHASE8A_OPUS_REVIEW_PACKAGE.md

for f in \
  knowledge/gold_standards/lid_driven_cavity_benchmark.yaml \
  knowledge/gold_standards/backward_facing_step_steady.yaml \
  knowledge/gold_standards/cylinder_crossflow.yaml
do
  python3 - "$f" <<'PY'
import sys, yaml
path = sys.argv[1]
gs = yaml.safe_load(open(path))
assert "observables" in gs
assert all("name" in o for o in gs["observables"])
assert all("ref_value" in o for o in gs["observables"])
assert all("tolerance" in o for o in gs["observables"])
print(f"{path}: PASS")
PY
done

for section in "Input Schema" "Output Schema" "Core Formulas" "Threshold Table" \
               "Error Handling Matrix" "Determinism" "Test Matrix" "Integration Points"
do
  grep -q "$section" docs/specs/AUTO_VERIFIER_SPEC.md
done

for section in "Architecture Overview" "Scope" "Risk Assessment" "Recommendation"
do
  grep -q "$section" docs/gates/PHASE8A_OPUS_REVIEW_PACKAGE.md
done

git status --short --untracked-files=all -- \
  docs/specs/AUTO_VERIFIER_SPEC.md \
  docs/design/AUTO_VERIFIER_ARCHITECTURE.md \
  docs/gates/PHASE8A_OPUS_REVIEW_PACKAGE.md \
  knowledge/gold_standards/lid_driven_cavity_benchmark.yaml \
  knowledge/gold_standards/backward_facing_step_steady.yaml \
  knowledge/gold_standards/cylinder_crossflow.yaml
```

## 6. Regression Evidence

Evidence captured for this gate package:

- Task-owned delta is limited to design docs plus OF-01/02/03 contract alias YAML files.
- The spec now contains the contract sections required by the Notion acceptance checks.
- Contract alias Gold Standard YAML files exist for OF-01/02/03 and include explicit observable tolerances.
- Legacy Gold Standard YAML files remain present and untouched.
- The active repo whitelist source is `knowledge/whitelist.yaml`; the Notion task still references `knowledge/ai_cfd_cold_start_whitelist.yaml`, which is treated here as contract naming drift rather than an implementation blocker.

## 7. Questions For Opus

1. Is the contract alias strategy for OF-01/02/03 accepted as the canonical Phase 8a input surface?
2. Is the proposed optional `post_execute_hook` seam acceptable as the additive integration boundary for 8a-2?
3. Does Opus want any stricter condition before opening implementation, beyond the four binding conditions listed above?

## 8. Requested Gate Outcome

Please return one of:

- `PASS` — implementation may start under the documented constraints
- `PASS WITH CONDITIONS` — implementation may start only after listed adjustments
- `REJECT` — redesign required before Task 8a-2

## 9. Drift Closed Record

- `2026-04-17` — Opus condition `C3` closed.
- Notion contract reference for the active repo whitelist is normalized to `knowledge/whitelist.yaml`.
- Phase 8a implementation used the repo truth source without modifying any Phase 1-7 runtime path.

## 10. Known Debt

- `2026-04-17` — `src/notion_client.py` still collides with the third-party `notion-client` package name during full-repo test collection.
- This debt predates Task `8a-2` and remained explicitly out of scope for `8b-1`.
- Recommended follow-up: handle via a dedicated Decision and a bounded rename or packaging fix, rather than folding it into Report Engine work.
