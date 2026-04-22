---
decision_id: DEC-V61-035
timestamp: 2026-04-22T09:35 local
scope: |
  Correction DEC for the PASS-washing defect surfaced by user deep-review
  2026-04-22. Minimum fix only: (1) flip default-run resolution from
  `reference` → `audit_real_run` so the case verdict reflects
  solver-in-the-loop truth; (2) relabel the /learn visual-only section
  so it no longer positions itself as "real simulation output = validated"
  — it is now explicitly marked "未完成金标准验证 / Visual evidence only /
  cannot be read as computed-PASS".

  Does NOT attempt the larger structural fixes user listed (hard gates for
  missing quantities / unit mismatch / velocity-magnitude sanity /
  k-epsilon-blowup / stuck residuals; per-case dedicated validation plots
  for BFS Xr/H, cylinder drag FFT+St, TFP Cf(x), channel u+/y+, impinging
  Nu(r), NACA Cp(x), convection T+Nu). Those land as subsequent DECs
  under Phase 8 (see "Follow-up queue" below).
autonomous_governance: true
claude_signoff: yes
codex_tool_invoked: pending (will invoke post-commit)
codex_rounds: 0
codex_verdict: pending
codex_tool_report_path: []
counter_status: |
  v6.1 autonomous_governance counter 20 → 21. Sub-threshold for RETRO
  cadence rule #2 next fire; RETRO-V61-002 (counter=20) already covered
  the broader Phase 7 Sprint 1 arc — this correction is small-scope.
reversibility: fully-reversible-by-pr-revert
  (4 files changed: 1 adapter-less service, 1 frontend, 2 tests. Revert
  restores the prior default-run-= reference behavior. Not byte-
  reproducibility-sensitive.)
notion_sync_status: pending
github_pr_url: null (direct-to-main)
github_merge_sha: pending
github_merge_method: direct commit on main
external_gate_self_estimated_pass_rate: 0.70
  (Straightforward correctness fix with two updated tests. Low surface
  area. Codex invocation post-merge acceptable per RETRO-V61-001 rule;
  pre-merge not required at 0.70.)
supersedes: null
superseded_by: null
upstream: |
  - User deep-review 2026-04-22: "当前 UI 不能作为'计算通过'的验收展示。"
  - DEC-V61-024 (original curator rule: "prefer reference_pass so default
    view shows PASS narrative") — THIS decision reverses that default
    direction in light of the audit-real-run evidence now available.
  - DEC-V61-034 (Tier C visual-only fan-out) — this correction tightens
    the framing Tier C established.
---

# DEC-V61-035: Honest default-run + visual-only re-labeling

## Why now

User 2026-04-22 deep-review opened 10 cases, cross-checked
`audit_real_run` verdicts against what the UI displayed, and found:

1. **PASS-washing**: `validation_report.py::_pick_default_run_id`
   unconditionally preferred `reference` category → the case-card
   `contract_status` showed curated narrative PASS/HAZARD even when
   the *real-solver* `audit_real_run` was FAIL. Six cases
   (BFS, TFP, plane_channel, RBC, DHC, duct, impinging_jet) displayed
   as PASS while their audit_real_run was FAIL with 80-440% deviation.
2. **Over-endorsement**: the /learn visual-only section banner text
   read "真实仿真输出 … 不是占位图" — technically true but positions
   the panel as validation evidence when those 9 cases are explicitly
   NOT gold-covered and their audit_real_run is FAIL.

The root diagnosis is correct. The minimum fix is small.

## What landed (this DEC)

### 1. `ui/backend/services/validation_report.py::_pick_default_run_id`
- Priority order changed from `reference → any → legacy` to
  `audit_real_run → reference → any → legacy`.
- When an audit_real_run exists (all 10 whitelist cases post-DEC-V61-034),
  it is the default, surfacing the honest solver-in-the-loop verdict.
- Reference remains as fallback when audit_real_run is absent (e.g., new
  cases onboarded but not yet integration-tested).

### 2. `ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx::ScientificComparisonReportSection`
- Heading changed: "仿真结果云图 · OpenFOAM Simulation Fields" →
  "仿真场图 · Visual evidence only · 未完成金标准验证".
- Info banner changed from blue "真实仿真输出" to amber
  "⚠ 未通过金标准验证 … 不能作为'计算已通过'的结论依据".
- Banner text now explicitly directs reader to Run Inspector →
  audit_real_run for the actual measurement.actual vs gold.expected
  comparison.

### 3. Test updates
- `test_validation_report_default_prefers_reference_pass_when_curated`
  renamed + inverted → `test_validation_report_default_prefers_audit_real_run`.
  Asserts TFP default now returns audit_real_run Cf = 0.0076 (FAIL),
  not the curated reference_pass Cf = 0.00423 (PASS).
- `test_dashboard_has_cases_and_summary` updated: dashboard summary
  now expects `fail_cases >= 1` (honest) instead of `hazard_cases >= 1`
  (the old curated path).

## What is NOT in this DEC (follow-up queue)

User's deep-review listed 5 structural integrity issues:

1. **Hard gates on comparator extraction** — missing target quantity,
   unit/dimension mismatch, velocity-magnitude > N× inlet scale,
   negative/overflow k-epsilon, continuity-error blowup, stuck residuals.
   Currently the comparator accepts `U_residual_magnitude=0.044` as a
   stand-in for `Xr/H=6.26` (BFS) — that should be FAIL not +0.48%.
2. **Per-case dedicated validation plots** — |U| contour is too generic;
   each case needs its physics-specific plot (BFS Xr/H, cylinder drag
   time-series + FFT → St, TFP Cf(x) + Spalding overlay, channel u+/y+
   log-layer, impinging Nu(r), NACA Cp(x), convection T-field + Nu
   extraction, RBC plume/roll pattern).
3. **Convergence attestation** — OpenFOAM finishing ≠ physical convergence.
   Need post-run attestation: continuity drift, field-magnitude sanity,
   turbulence-field positivity, steady-residual floor vs gold tolerance.
4. **LDC verdict unification** — comparison-report shows PARTIAL
   (11/17 tolerance pass), /validation-report now shows FAIL (audit scalar
   +370.48%). Either reconcile the scalar metric with the profile verdict,
   or surface both explicitly.
5. **UI split into 3 tiers** — Reference demo / Audit solver run /
   Visual evidence only, with clear per-tier semantics.

These are **Phase 8** scope (new milestone). Will author:
- DEC-V61-036: Hard comparator gates (missing-quantity → FAIL)
- DEC-V61-037: Per-case validation plots (7 new renderers)
- DEC-V61-038: Convergence attestor
- DEC-V61-039: LDC verdict reconciliation
- DEC-V61-040: UI 3-tier semantics

## Regression

`PYTHONPATH=. .venv/bin/pytest ui/backend/tests/ -q` → **142/142 passed**
after updating 2 tests. The test pre-existing BEFORE this DEC correctly
captured the curated PASS narrative — updating the assertions documents
that we are intentionally reversing that behavior.

## Counter + retrospective

Counter 20 → 21. No new retro (RETRO-V61-002 covered the Phase 7 arc
at counter 20 three hours ago). If this kicks off Phase 8 physics-debt
work and counter reaches 30, RETRO-V61-003 fires per cadence rule #2.

## Related

- DEC-V61-024 (original default = reference curator rule) — reversed here
- DEC-V61-034 (Tier C) — this corrects Tier C's framing without undoing
  the fan-out
- RETRO-V61-002 (counter 20 retro) — open question #2 ("should 7 FAIL
  cases be Phase 8 physics-debt DECs?") now has explicit answer: YES
