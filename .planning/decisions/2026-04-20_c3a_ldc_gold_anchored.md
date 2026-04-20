---
decision_id: DEC-V61-007
timestamp: 2026-04-20T21:45 local
scope: Path B · C3a · LDC gold-anchored sampleDict (first of 3 C3 PRs). Adds _load_gold_reference_values + _emit_gold_anchored_points_sampledict helpers and switches LDC generator from `type uniform nPoints 16` to `type points` at exact Ghia 1982 y-coordinates when task name matches whitelist. Fallback path preserved for non-whitelist test fixtures.
autonomous_governance: true
claude_signoff: yes
codex_tool_invoked: false
codex_diff_hash: null
codex_tool_report_path: null
reversibility: fully-reversible-by-pr-revert
  (One `git revert -m 1 912b2ce1` restores the hardcoded uniform-16
  sampleDict and removes the two new helpers. The 13 new tests revert
  with them. No whitelist or gold_standards touches — pure generator
  infrastructure.)
notion_sync_status: synced 2026-04-20T21:50 (https://www.notion.so/348c68942bed819cb241ef53d17200c3) — Decisions DB page created with Scope=Project, Status=Accepted, Canonical Follow-up=PR #7 URL
github_pr_url: https://github.com/kogamishinyajerry-ops/cfd-harness-unified/pull/7
github_merge_sha: f0264a13bd0b3d57d4e357940b20956a21260755
github_merge_method: merge (regular merge commit — 留痕 > 聪明)
external_gate_self_estimated_pass_rate: 95%
  (Pure src/ + tests/ change on DEC-V61-003 autonomous turf. Backwards-
  compatible fallback preserves all 158 baseline tests. Adds 13 new
  tests covering both the gold-anchored path and the fallback. Design
  doc docs/c3_sampling_strategy_design.md pre-landed and unchanged —
  implementation matches the §3.1 specification.)
supersedes: null
superseded_by: null
upstream: DEC-V61-004 (C1 alias layer — complementary to this sampling-location fix)
design_doc: docs/c3_sampling_strategy_design.md
---

# DEC-V61-007: C3a · LDC gold-anchored sampleDict

## Decision summary

First of three planned C3 PRs per `docs/c3_sampling_strategy_design.md`. Replaces the LDC case generator's hardcoded `type uniform nPoints 16` sampleDict with `type points` containing exact Ghia 1982 y-coordinates (0.0625, 0.125, 0.5, 0.75, 1.0) along the centerline x=0.5.

Two module-level helpers added to `src/foam_agent_adapter.py`:
- `_load_gold_reference_values(task_name, whitelist_path=None)` — loads `gold_standard.reference_values` from `knowledge/whitelist.yaml` matching on `case.id` or `case.name`. Returns None (not raises) on missing file / malformed YAML / unknown name / empty ref list.
- `_emit_gold_anchored_points_sampledict(case_dir, set_name, physical_points, fields, axis, header_comment)` — writes `system/sampleDict` with a single `type points` set at the supplied coordinates. Raises `ValueError` on empty points; otherwise silent.

These helpers will be reused by C3b (NACA `surfaces` function-object) and C3c (Impinging Jet `wallHeatFlux` function-object) in the next two PRs.

## Problem this closes

C1 (DEC-V61-004) closed the **key-naming** mismatch channel via `CANONICAL_ALIASES`. C3 closes the **sampling-location** mismatch channel:

- Previously: Ghia's 5 specific y-coords (0.0625, 0.125, 0.5, 0.75, 1.0) had NO coincidence with the uniform 16-point grid (y = 0, 1/15, 2/15, …, 1). Comparator had to interpolate, introducing a sampling-grid error term indistinguishable from solver error.
- Now: solver samples AT the gold points. Comparator lookup is exact. Any remaining deviation is purely solver physics / mesh convergence.

## 禁区 compliance

| Area | Touched? |
|---|---|
| `src/` (DEC-V61-003 autonomous turf) | YES — helpers + LDC generator |
| `tests/` | YES — +13 tests |
| `knowledge/gold_standards/**` | NOT TOUCHED |
| `knowledge/whitelist.yaml` | NOT TOUCHED (read-only access) |
| Notion DB destruction | NOT TOUCHED (one new page) |

## Regression

```
pytest tests/test_foam_agent_adapter.py tests/test_result_comparator.py \
       tests/test_task_runner.py tests/test_e2e_mock.py \
       tests/test_correction_recorder.py tests/test_knowledge_db.py \
       tests/test_auto_verifier -q
→ 171 passed in 0.98s
```

158 baseline + 13 new C3a tests:
- `TestLoadGoldReferenceValues` × 6 (id match, name match, unknown, missing file, bad YAML, empty ref list)
- `TestEmitGoldAnchoredPointsSampleDict` × 4 (all points written, multiple fields, empty raises, header comment)
- `TestLidDrivenCavityGoldAnchoredSampling` × 3 (gold-anchored path with whitelist id, fallback with synthetic name, display-name match)

## Backwards compatibility

Critical: existing `make_task()` test fixture uses `name="test"` which is NOT in whitelist. This triggers the fallback path → uniform 16-point dict preserved → all 3 existing LDC tests (`test_generate_lid_driven_cavity_creates_files`, `test_generate_lid_driven_cavity_default_lid_velocity`, `test_generate_lid_driven_cavity_sample_dict`) pass unchanged.

## Next steps

1. **C3b** — NACA 0012 surfaces function-object on airfoil patch + 1D arclength interpolator for Cp. ~150 LOC, ~10 new tests. Will land as DEC-V61-008.
2. **C3c** — Impinging Jet wallHeatFlux function-object on impingement plate + Nu-from-q conversion. ~180 LOC, ~10 new tests. Will land as DEC-V61-009.
3. After all 3 C3 PRs: dashboard full-stack validation (§5d, currently blocked on Docker daemon).

## Note on DEC numbering

The original Gate Q-new hold plan earmarked DEC-V61-007 for Case 9/10 literature re-source. Since that remains blocked (both Behnad 2013 and Chaivat 2006 papers behind Elsevier paywall, user confirmed 2026-04-20 "PDF 搞不到, 先 hold, 跳过"), DEC-V61-007 is reassigned to C3a. The Case 9/10 re-source, if/when it happens, will take the next available slot (DEC-V61-010 or later).
