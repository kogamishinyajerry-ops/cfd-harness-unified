---
decision_id: DEC-V61-022
timestamp: 2026-04-21T06:25 local
scope: P6-TD-002 fix. `_extract_flat_plate_cf` was running on duct_flow cases because both TFP and duct_flow declare `geometry_type: SIMPLE_GRID` and share Re. Inside the extractor, Spalding fallback returns `0.0576 / (0.5*Re)**0.2` — parameter-independent once Re is fixed. §5d Part-2 observed both cases returning `cf_skin_friction = 0.007600365566051871` to 10 decimals. Fix adds a `hydraulic_diameter`-presence dispatch guard so duct_flow no longer falls through to the wrong extractor; instead it emits `duct_flow_extractor_missing`/`_hydraulic_diameter` producer flags pending a proper `_extract_duct_friction_factor` (queued as P6-TD-003).
autonomous_governance: true
claude_signoff: yes
codex_tool_invoked: true
codex_diff_hash: 36e3249<FULL_SHA_TO_CONFIRM>
codex_tool_report_path: reports/codex_tool_reports/2026-04-21_pr22_duct_dispatch_review.md
codex_verdict: CHANGES_REQUIRED → RESOLVED by PR #27 (round 8; 1 Blocking finding on fragile dispatcher signal — `hydraulic_diameter` in `boundary_conditions` is not invariant across TaskSpec constructor paths. PR #27 (merge `7bbbeb2`) replaced with canonical name-based `_is_duct_flow_case()` helper + fail-closed `duct_flow_hydraulic_diameter_missing` flag + integration test using KnowledgeDB.list_whitelist_cases(). Naming note from round 8 also applied: `duct_flow_extractor_missing` → `duct_flow_extractor_pending`.)
counter_status: "v6.1 autonomous_governance counter 2 → 3."
reversibility: fully-reversible-by-pr-revert
  (One `git revert -m 1 <merge>` restores the original flat-plate
  dispatch for duct_flow. Fixtures produced by the §5d Part-2 batch
  were already in git at that point; they don't depend on this PR.)
notion_sync_status: synced 2026-04-21 (https://www.notion.so/DEC-V61-022-P6-TD-002-duct_flow-dispatch-guard-349c68942bed818ab52df137841b1cf9)
github_pr_url: https://github.com/kogamishinyajerry-ops/cfd-harness-unified/pull/22
github_merge_sha: <to-fill-after-merge>
github_merge_method: merge (regular merge commit — 留痕 > 聪明)
external_gate_self_estimated_pass_rate: 91%
  (Guard based on `hydraulic_diameter` presence. New tests cover duct-
  shape + flat-plate-shape regression. Residual 9%: future duct case
  might forget to declare hydraulic_diameter in boundary_conditions →
  silently re-routes to flat plate extractor. Acceptable for now;
  P6-TD-003 will introduce a positive duct extractor that makes the
  guard less load-bearing.)
supersedes: null
superseded_by: null
upstream: §5d Part-2 acceptance report (2026-04-21_part2_solver_runs.md);
  DEC-V61-021 (parallel P6 fix, no cross-dep)
followup: P6-TD-003 (implement `_extract_duct_friction_factor` targeting
  Darcy-Weisbach friction_factor = 0.0185 per duct_flow gold standard)
---

# DEC-V61-022: P6-TD-002 — duct_flow dispatch guard

## Root cause

Dispatcher at line ~7025 in `src/foam_agent_adapter.py`:

```python
elif geom == GeometryType.SIMPLE_GRID and task_spec.Re is not None and task_spec.Re >= 2300:
    key_quantities = self._extract_flat_plate_cf(...)
```

Routes any `(SIMPLE_GRID + Re ≥ 2300)` task to the flat-plate extractor.
Inside, the Spalding fallback at line ~7731 computes
`Cf = 0.0576 / (0.5*Re)**0.2`, which is parameter-independent once Re
is fixed. TFP and duct_flow both declare Re=50000 in their execution
chains → identical Cf to 10 decimals.

Duct_flow's canonical observable (per `knowledge/gold_standards/duct_flow.yaml`)
is Darcy-Weisbach **friction_factor = 0.0185**, NOT skin-friction Cf —
so reusing the flat-plate extractor is semantically wrong regardless of
the numerical coincidence.

## Fix

Dispatcher tests for `hydraulic_diameter` absence in
`task_spec.boundary_conditions` before calling `_extract_flat_plate_cf`.
Duct cases have it, flat plate doesn't. When `hydraulic_diameter` IS
present, a new branch emits:

- `duct_flow_extractor_missing: true`
- `duct_flow_hydraulic_diameter: <value>`

Audit surfaces see "no measurement + explicit shape-detected reason"
instead of a shared Spalding reference.

## Regression

- 97/97 test_foam_agent_adapter.py
- Full matrix 330/1skip (baseline 328 + 2 new tests)

## Follow-up

**P6-TD-003**: implement `_extract_duct_friction_factor` targeting
Darcy-Weisbach `friction_factor = dp/dx * D_h / (0.5 * rho * U_bulk^2)`.
Gold reference 0.0185 at Re=50000 per duct_flow.yaml.

## Codex round 8

Queued to run after round 7 completes. Trigger: `foam_agent_adapter.py`
>5 LOC + byte-repro-adjacent path (the flag values feed into signed
bundle measurement fields).
