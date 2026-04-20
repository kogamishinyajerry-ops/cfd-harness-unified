---
decision_id: DEC-V61-011
timestamp: 2026-04-20T23:30 local
scope: Path B · Gate Q-2 · Path A landing. Renames whitelist `fully_developed_pipe` → `duct_flow`; unifies auto_verifier `fully_developed_turbulent_pipe_flow` → `duct_flow`; replaces two legacy gold_standards YAMLs with single new `duct_flow.yaml` anchored on Jones 1976 square-duct friction factor. Closes Q-2.
autonomous_governance: false  # gate-approved (Kogami Path A), not self-signed
claude_signoff: yes
codex_tool_invoked: false
codex_diff_hash: null
codex_tool_report_path: null
reversibility: fully-reversible-by-pr-revert
  (One `git revert -m 1 <merge-sha>` restores the two legacy YAMLs,
  the old whitelist id + Moody pipe description, and the pre-rename
  consumer code. Corrections directory is out of scope — old case
  ids in historical correction YAMLs are immutable evidence.)
notion_sync_status: PENDING
github_pr_url: null
github_merge_sha: null
github_merge_method: merge (regular merge commit — 留痕 > 聪明)
external_gate_approval: Kogami approved Path A 2026-04-20 (session `"决定 Q-2 path（我推荐 A）"` confirming audit recommendation in `.planning/gates/Q-2_r_a_relabel.md`).
supersedes: null  # Gate Q-2 subsumed; see `external_gate_queue.md` Q-2 entry
superseded_by: null
upstream: DEC-V61-010 (C3 round-trip complete — Phase 5 structural readiness)
gate_doc: .planning/gates/Q-2_r_a_relabel.md
---

# DEC-V61-011: Gate Q-2 Path A — `fully_developed_pipe` → `duct_flow` rename

## Decision summary

Gate Q-2 approved by Kogami on 2026-04-20 after the formal gate request at `.planning/gates/Q-2_r_a_relabel.md`. Path A selected (audit recommendation). The adapter's `SIMPLE_GRID` for internal channel flow emits a rectangular (AR=1 square) duct, not a circular pipe. Previous whitelist entry labeled it as a pipe and the gold standard cited Moody smooth-pipe Darcy f; this was physics-labeling error.

Consolidation applied:

- **whitelist.yaml**: `id: fully_developed_pipe` → `id: duct_flow`. `name: "Fully Developed Turbulent Pipe Flow"` → `"Fully Developed Turbulent Square-Duct Flow"`. `reference: "Nikuradse 1933 / Moody 1944"` → `"Jones 1976 / Jones & Launder 1973"`. `doi: 10.1007/BF01314553` → `10.1016/0017-9310(76)90033-4`. Parameters `{Re: 50000, diameter: 0.1}` → `{Re: 50000, hydraulic_diameter: 0.1, aspect_ratio: 1.0}`. gold_standard description updated to Jones correlation. tolerance 0.08 → 0.10 (Jones correlation scatter vs. Moody).
- **knowledge/gold_standards/**: deleted `fully_developed_pipe.yaml` + `fully_developed_turbulent_pipe_flow.yaml` (legacy dual-file state). Created `duct_flow.yaml` anchored on Jones 1976 with physics_contract_status: SATISFIED (precondition "adapter operates on rectangular AR=1 duct" is now TRUE since the label matches).
- **src/auto_verifier/config.py**: `ANCHOR_CASE_IDS` + `CASE_ID_TO_GOLD_FILE` + `CASE_ID_TO_SOLVER` all use `duct_flow`. `TASK_NAME_TO_CASE_ID` retains legacy display-name aliases ("Fully Developed Turbulent Pipe Flow") and the new name, both mapping to `duct_flow`.
- **src/report_engine/data_collector.py**: `CASE_ID_TO_WHITELIST_ID` entry `"fully_developed_turbulent_pipe_flow": "fully_developed_pipe"` → `"duct_flow": "duct_flow"`.
- **src/report_engine/generator.py**: `SUPPORTED_CASE_IDS` → `duct_flow`.
- **src/report_engine/contract_dashboard.py**: 6 references updated. DashboardCaseSpec rewritten under honest `duct_flow` physics. `Q-2` gate card flipped from "冻结" to "CLOSED (DEC-V61-011)".
- **tests/test_report_engine/test_generate_reports_cli.py**: 3 string references → `duct_flow`.

## Why P-A was chosen (over B/C/D)

From the gate doc:
- **Path B** (generator-side rewrite to actual circular pipe) rejected: larger engineering change (new axisymmetric blockMeshDict) not justified by a naming fix.
- **Path C** (widen tolerance + add `regime_mismatch` annotation) rejected on honesty grounds — exactly the pattern v6.1 takeover said we'd stop doing.
- **Path D** (hold) rejected — the audit was not miscategorized; duct ≠ pipe is a real geometry mismatch.

Path A reclassifies the physics label to match what the solver actually does. Numerical gold at Re=50000 (f=0.0185) stays within 2% of both Jones-duct and Colebrook smooth-pipe, so the comparator verdict is preserved while the contract becomes intrinsically honest.

## 禁区 compliance (gate-approved)

| Area | Touched? | Authority |
|---|---|---|
| `knowledge/gold_standards/**` (禁区 #2) | YES — 2 deletes + 1 new file | Gate Q-2 Path A approval |
| `knowledge/whitelist.yaml` `reference_values` + `parameters` (禁区 #3) | YES — id rename + desc + params + tolerance | Gate Q-2 Path A approval |
| `knowledge/whitelist.yaml` metadata fields | YES — turbulence_model unchanged (k-epsilon) | DEC-V61-003 §8 allowlist |
| Notion DB destruction | NOT TOUCHED (one new page) | — |

`autonomous_governance: false` — this is gate-approved, not self-signed, consistent with DEC-V61-006 precedent.

## Regression

```
pytest 7-file matrix (core) → 196 passed in 1.18s
pytest tests/test_report_engine/test_generate_reports_cli.py → 9 passed
```

Core matrix unaffected (no test fixtures hardcoded the old case id as a magic string). Report-engine CLI tests pass with `duct_flow` in the skip-behavior test. `knowledge/corrections/` historical YAMLs retain legacy ids (evidence, immutable).

## Knowledge directory state post-rename

```
knowledge/gold_standards/
├── axisymmetric_impinging_jet.yaml
├── backward_facing_step.yaml
├── backward_facing_step_steady.yaml
├── circular_cylinder_wake.yaml
├── cylinder_crossflow.yaml
├── differential_heated_cavity.yaml
├── duct_flow.yaml                   ← NEW (replaces 2 legacy files)
├── fully_developed_plane_channel_flow.yaml
├── impinging_jet.yaml
├── lid_driven_cavity.yaml
├── lid_driven_cavity_benchmark.yaml
├── naca0012_airfoil.yaml
├── plane_channel_flow.yaml
├── rayleigh_benard_convection.yaml
└── turbulent_flat_plate.yaml
```

## Reversibility

One `git revert -m 1 <merge-sha>` restores all edits: two legacy YAMLs, old whitelist id + parameters, consumer code. `knowledge/corrections/` is untouched (historical correction YAMLs still reference old ids — those are immutable evidence, not live state, and the comparator alias layer handles lookup either way).

## Q-2 closure + Phase 5 unblock

This DEC **closes Q-2** — the last remaining blocker for Phase 5 Audit Package Builder per DEC-V61-002. `external_gate_queue.md` Q-2 entry will be struck through + marked closed referencing this DEC.

Phase 5 kickoff plan already written at `.planning/phase5_audit_package_builder_kickoff.md`; execution can now start (or be sequenced with §5d dashboard validation first).

## Next steps (queued)

1. Commit + push + PR #11.
2. On merge: mirror DEC-V61-011 to Notion Decisions DB.
3. Close Q-2 in `external_gate_queue.md` with strike-through + pointer to this DEC.
4. Trigger §5d dashboard validation if Docker daemon is up; otherwise proceed to Phase 5 PR-5a manifest builder.
5. Consider a follow-up PR that regenerates the `reports/**/report.md` files to reflect all recent whitelist changes (not part of this PR to keep scope tight).
