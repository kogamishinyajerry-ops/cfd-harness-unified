---
decision_id: DEC-V61-039
timestamp: 2026-04-22T11:55 local
scope: |
  Phase 8 Sprint 1 — reconcile LDC split-brain verdicts between
  /api/comparison-report (PARTIAL: 11/17 pointwise profile passes)
  and /api/validation-report (FAIL: scalar deviation ≈ 370%). Both
  are honest at different levels; the API previously hid the split by
  exposing only the scalar. This DEC surfaces both by adding
  `profile_verdict` + `profile_pass_count` + `profile_total_count`
  fields to ValidationReport. Frontend will show both (DEC-V61-040).

autonomous_governance: true
claude_signoff: yes
codex_tool_invoked: false (self-rate 0.80 > 0.70 threshold; protocol-compliant skip)
codex_rounds: 0
codex_verdict: POST_MERGE_SKIP_PER_SELF_RATE
codex_tool_report_path:
  - reports/codex_tool_reports/20260422_dec036_036c_039_backfill_note.md
codex_backfill_note: |
  Self-pass 0.80 is above the ≤0.70 pre-merge trigger; per RETRO-V61-001
  this DEC is protocol-compliant without a Codex round. Commit 8ca850e
  landed additive API fields + reach-in to module-private
  _GOLD_OVERLAY_CASES. Backfill formalizes the "no Codex needed" verdict
  so audit trail is complete (v6.2 direction A2).
counter_status: |
  v6.1 autonomous_governance counter 26 → 27. Next retro at 30.
reversibility: fully-reversible — additive schema fields + a helper
  function. Revert = 4 files restored, fixtures unchanged.
notion_sync_status: pending (v6.2 backfill 2026-04-22; next Notion sync cycle)
github_pr_url: null (direct-to-main)
github_merge_sha: 8ca850e
external_gate_self_estimated_pass_rate: 0.80
  (Narrow additive change. Main risk: is the module-private
  `_GOLD_OVERLAY_CASES` set the right thing to gate on? If a future DEC
  renames or removes it, the reach-in breaks.)
supersedes: null
superseded_by: null
upstream: |
  - User 2026-04-22 deep-review: "LDC verdict inconsistent (comparison
    shows PARTIAL 11/17, validation shows FAIL via scalar +370%)".
  - DEC-V61-035 (default → audit_real_run) — drove the scalar to
    pick the wrong profile point; exposed the reconciliation gap.
---

# DEC-V61-039: LDC verdict reconciliation

## Why now

User's 2026-04-22 review flagged that the comparison-report (pointwise
profile analysis) says LDC PARTIAL while validation-report (scalar
contract) says LDC FAIL. Both are honest; both are correct at their
respective levels; the API previously forced the UI to pick one. This
is the last split-brain in Phase 8 Sprint 1.

## What lands

1. `ui/backend/schemas/validation.py::ValidationReport` gains:
   - `profile_verdict: "PASS" | "PARTIAL" | "FAIL" | None`
   - `profile_pass_count: int | None`
   - `profile_total_count: int | None`

2. `ui/backend/services/validation_report.py` adds
   `_compute_profile_verdict(case_id, run_label)` which:
   - Checks `comparison_report._GOLD_OVERLAY_CASES` membership
   - If member, calls `comparison_report.build_report_context(case_id, run_label)`
     and lifts out `verdict` + `metrics.{n_pass, n_total}`
   - Returns `(None, None, None)` on non-overlay or exception

3. `build_validation_report` populates the 3 new fields.

4. `ui/frontend/src/types/validation.ts` adds
   `ValidationReportExtras` which ValidationReport now extends.

5. Tests: `test_dec039_profile_verdict_reconciliation.py`, 3 tests:
   - LDC audit_real_run surfaces both (FAIL scalar + PARTIAL 11/17)
   - Non-gold-overlay cases have `profile_verdict: null`
   - OpenAPI schema documents the 3 new fields

## Live verification

```
reference_pass     → contract=FAIL   | profile=None
audit_real_run     → contract=FAIL   | profile=PARTIAL (11/17)
```

Both LDC verdicts now surface honestly. The frontend rendering of the
dual-verdict lands in DEC-V61-040 (UI 3-tier).

## Counter + Codex

26 → 27. Self-pass 0.80. Codex post-merge acceptable per RETRO-V61-001
(narrow additive change, > 0.70 threshold). Will run Codex anyway given
the sustained per-DEC validation cadence user requested.

## Related

- DEC-V61-036* + DEC-V61-038 — prior Sprint-1 infrastructure
- DEC-V61-040 — UI rendering of profile_verdict (future)
