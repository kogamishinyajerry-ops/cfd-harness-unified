---
decision_id: DEC-V61-021
timestamp: 2026-04-21T06:15 local
scope: P6-TD-001 fix. BFS reattachment_length extractor was publishing physically-impossible negative values (§5d Part-2 observed -5.38) when the solver ran under-converged. Root cause: the zero-crossing scanner in both `_extract_bfs_reattachment` static method and the inline path in `_parse_solver_log` had no sanity check that the detected x coordinate was downstream of the step (x > 0). Fix adds the guard + emits `reattachment_detection_upstream_artifact`/`_rejected_x` producer flags for downstream audit transparency.
autonomous_governance: true
claude_signoff: yes
codex_tool_invoked: true
codex_diff_hash: 67b129e29b27518be7c3e6f0d8f4d6e4e5a95f6b
codex_tool_report_path: reports/codex_tool_reports/2026-04-21_pr21_bfs_guard_review.md
codex_verdict: pending (round 7 running — 2026-04-21T06:15 kicked off)
counter_status: "v6.1 autonomous_governance counter 1 → 2 (under new telemetry-only governance; threshold ≥20 for next retro)."
reversibility: fully-reversible-by-pr-revert
  (One `git revert -m 1 67b129e` restores the unsafe publish-any-x
  behavior. No cross-dependency with other PRs.)
notion_sync_status: pending (Codex round 7 verdict awaiting)
github_pr_url: https://github.com/kogamishinyajerry-ops/cfd-harness-unified/pull/21
github_merge_sha: 67b129e29b27518be7c3e6f0d8f4d6e4e5a95f6b
github_merge_method: merge (regular merge commit — 留痕 > 聪明)
external_gate_self_estimated_pass_rate: 94%
  (Narrow physical-plausibility guard on both extractor paths. New test
  replays the §5d Part-2 failure mode; existing valid-detection test
  extended. No change to well-converged behavior. Residual 6%:
  hypothetical edge case where legitimate reattachment is at x = 0
  exactly — treated as rejected under strict `> 0` check; could be
  loosened to `>= 0` if a case for it surfaces.)
supersedes: null
superseded_by: null
upstream: §5d Part-2 acceptance report (2026-04-21_part2_solver_runs.md)
---

# DEC-V61-021: P6-TD-001 — BFS reattachment upstream-artifact guard

## Decision summary

Narrow correctness fix. Both BFS reattachment extractor paths now
reject non-physical upstream (x ≤ 0) detections and emit producer
flags for downstream audit transparency.

## Changes

- `src/foam_agent_adapter.py`:
  - `_extract_bfs_reattachment` (line ~7362): if `reattachment_x > 0` →
    publish `reattachment_length`; else emit
    `reattachment_detection_upstream_artifact=true` +
    `reattachment_detection_rejected_x=<raw>`.
  - Inline BFS path in `_parse_solver_log` (line ~6869): same guard.
- `tests/test_foam_agent_adapter.py`:
  - `test_parse_solver_log_extracts_bfs_reattachment_from_raw_sample`
    extended — asserts no upstream flag on valid detection.
  - New `test_bfs_reattachment_rejects_upstream_detection_with_producer_flag`
    replays §5d Part-2 failure (Ux zero-crossing at x ≈ -4.58).

## Regression

- 95/95 test_foam_agent_adapter.py
- Full 9-file matrix 328/1skip (baseline 327 + 1 new test)
- Frontend tsc unaffected (no UI touched)

## Governance

- Turf: `src/foam_agent_adapter.py` autonomous (>5 LOC → Codex trigger)
- Self-estimate 94% → post-merge Codex round 7 queued

## Follow-ups

None from this fix. Narrowly scoped to BFS. The broader observation —
"extractors may publish physically implausible numbers under under-
converged solver runs" — is worth a cross-cutting audit but too large
for this DEC.
