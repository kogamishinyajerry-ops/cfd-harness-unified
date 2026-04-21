---
decision_id: DEC-V61-034
timestamp: 2026-04-21T22:30 local
scope: |
  Phase 7c Sprint 2 **Tier C** (visual-only) fan-out: expand real OpenFOAM
  post-processing evidence from LDC-only to all 10 whitelist cases on the
  `/learn/{case}` commercial-demo surface. User deep-acceptance feedback
  2026-04-21 evening: "我的每个 case 的 report 区域，仍然没有真实的仿真
  结果里提取出来的流场云图等等重要信息".

  Tier C goal (per user directive "C then B"): every case shows a real
  |U| contour + residual-convergence plot from an actual OpenFOAM run.
  Gold-overlay verdict + profile + GCI stay LDC-only for now (Tier B,
  future DEC).

  Impact: 8 of 10 cases now render real evidence on /learn/{case}. 1 case
  (rayleigh_benard_convection) still in integration batch at DEC author
  time; 1 case (circular_cylinder_wake) has a pre-existing foamToVTK
  container issue under investigation by subagent (see
  reports/codex_tool_reports/cylinder_wake_diagnosis.md when closed).

autonomous_governance: true
  (Multi-file frontend (LearnCaseDetailPage.tsx) + user-UX-critique-after
  trigger + new API contract (`GET /renders/{filename:path}`) → Codex
  mandatory per RETRO-V61-001 triggers. adapter untouched in this DEC;
  all changes contained to phase5_audit_run.py + render_case_report.py +
  comparison_report.{py,route} + LearnCaseDetailPage.tsx.)
claude_signoff: yes
codex_tool_invoked: true
codex_rounds: 2
codex_round_1_verdict: CHANGES_REQUIRED
codex_round_1_findings:
  - CRITICAL: visual-only cases 500 on /comparison-report HTML + /comparison-report.pdf + /comparison-report/build endpoints. build_report_context returns visual_only=True with metrics=None / paper=None, but render_report_html() rendered the gold-overlay Jinja template unconditionally, dereferencing metrics.max_dev_pct and paper.title → UndefinedError → 500. Fix (Option A per Codex) applied — raise ReportError in render_report_html and render_report_pdf for visual-only cases (before weasyprint import in PDF path) → routes map to 404. Added 3 tests covering the new 404 behavior.
codex_round_2_verdict: APPROVED_WITH_COMMENTS
codex_round_2_findings:
  - NON-BLOCKING: visual-only guard in render_report_pdf was inside the `output_path is None` branch, so caller-supplied output_path callers would skip the guard. Not a route issue (routes always pass None) but a service invariant gap. Tightening applied — ctx + guard hoisted above the branch so both call paths hit the guard.
codex_verdict: APPROVED_WITH_COMMENTS (after 2 rounds; 1 CR→fix→approved, 1 non-blocking nit→fix→invariant tightened)
codex_tool_report_path:
  - reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round1.md
  - reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round2.md
counter_status: |
  v6.1 autonomous_governance counter 19 → 20.
  (Triggers RETRO-V61-001 retrospective cadence rule #2 "counter ≥ 20 →
  arc-size retro mandatory". Retro will land in
  .planning/retrospectives/ alongside this DEC.)
reversibility: fully-reversible-by-pr-revert
  (Tier C is additive: reverting restores LDC-only visible state.
  VISUAL_ONLY_CASES + _REPORT_SUPPORTED_CASES expansion is pure opt-in
  switch; no existing gold-overlay behavior changes. Artifacts under
  reports/phase5_fields/*/ and reports/phase5_renders/*/ remain valid
  evidence regardless of code-level revert.)
notion_sync_status: synced 2026-04-21 (https://www.notion.so/DEC-V61-034-Phase-7c-Sprint-2-Tier-C-visual-only-fan-out-to-9-non-LDC-cases-349c68942bed81e0a3c4cc37a2242fd1)
github_pr_url: null (direct-to-main per Phase 7a + 7bc + 7bde precedent)
github_merge_sha: 4ee3fc2 (infrastructure) + a70796a (batch 1) + 02cd686 (batch 2 + 2D-plane fix)
github_merge_method: 3 commits direct-to-main
external_gate_self_estimated_pass_rate: 0.55
  (Higher than DEC-V61-033's 0.45 because: (a) no byte-reproducibility-
  sensitive path touched, (b) no adapter edit, (c) path-containment
  already validated in DEC-V61-033 pattern. Still below 70% because
  new route + new backend code path + multi-file frontend have strong
  Codex track record of surfacing subtle issues. Will update after
  Codex returns.)
supersedes: null
superseded_by: null
upstream: |
  - DEC-V61-031 (Phase 7a field capture — foamToVTK + artifact staging, case-agnostic)
  - DEC-V61-032 (Phase 7b MVP + 7c MVP + 7f MVP — LDC gold-overlay path)
  - DEC-V61-033 (Phase 7b polish + 7d GCI + 7e L4 — infrastructure primed for fan-out)
  - User deep-acceptance 2026-04-21: "每个 case 的 report 区域，仍然没有真实的仿真结果"
---

# DEC-V61-034: Phase 7c Sprint 2 Tier C — visual-only fan-out to 9 non-LDC cases

## Why now

Previous DEC-V61-033 explicitly deferred Phase 7c Sprint 2 because it needed
per-case OpenFOAM integration runs × 9 + custom gold-overlay plumbing per
case (BFS reattachment, cylinder Strouhal, TFP Cf-Spalding, DHC Nu-Ra, NACA
Cp curve, etc.) — that is real per-case physics work worth hours each.

User verified on `/learn/{case}` that 9 of 10 cases still showed static
placeholder PNGs (`ui/frontend/public/flow-fields/{case}/*.png` — hand-made
sketches, not simulation output). The commercial-demo surface therefore
was undersold: only LDC showed real evidence.

Two tiers were offered to the user 2026-04-21:
- **Tier C (visual-only)**: every case shows a real |U| contour + residuals
  PNG from an actual OpenFOAM run, no gold-overlay plumbing required.
  Cheap to land (hours, not days).
- **Tier B (full report)**: per-case gold-overlay machinery (profile overlay,
  pointwise deviation, GCI, 8-section report template). Expensive
  (~3-5hr per case × 9 cases).

User elected **Tier C then B** — close the "no real evidence" gap fastest
for all cases, then iterate to Tier B later if desired.

## What landed

### 1. Adapter-less opt-in (scripts/phase5_audit_run.py)
`_PHASE7A_OPTED_IN` expanded from `{"lid_driven_cavity"}` to ALL 10
whitelist cases. The executor's `_capture_field_artifacts` (introduced by
DEC-V61-031) is case-agnostic — it runs `foamToVTK -latestTime -noZero
-allPatches` inside the container + tars VTK/log/postProcessing back to
the host. Opting in just required flipping the frozenset; no adapter
surgery needed.

### 2. Renderer generalization (scripts/render_case_report.py, ~330 LOC changed)

- **Case sets split**: `GOLD_OVERLAY_CASES = {ldc}` + `VISUAL_ONLY_CASES =
  {9 others}`; `RENDER_SUPPORTED_CASES` is the union.
- **Per-mode renderer list**: gold-overlay mode runs all 5 renderers
  (profile + deviation + Plotly JSON + residuals + contour); visual-only
  mode runs just residuals + contour.
- **Residuals fallback**: `_parse_residuals_from_log(log_path)` regex-
  extracts initial residuals per `Time =` marker when
  `postProcessing/residuals/0/residuals.dat` is absent. Handles both
  pure-numeric (`Time = 0.0125`) and `Time = 35s` (simpleFoam steady)
  formats. Every captured run produces a log → every run plots residuals.
- **Contour 3-tier fallback** (`render_contour_u_magnitude_png`):
  1. Structured grid (LDC 129×129): contourf + streamplot, publication style.
  2. Unstructured tricontourf + sparse quiver overlay (BFS, channel, etc.).
  3. Scatter (final): for qhull-singular geometries (e.g. NACA0012 after
     divergence → all cells collinear).
- **2D-plane auto-detect** (`_pick_2d_plane`): picks the two coordinate
  axes with non-degenerate variance. NACA0012 is meshed in x-z (Cy ≈ 0),
  not x-y; previous LDC-style code assumed x-y and qhull failed. Now
  handles any extrusion direction.
- **Diverged-solution guard**: clips |U| to 99th percentile + replaces
  non-finite with zero before triangulation so overflow cells don't
  saturate colormap or crash qhull.

### 3. Backend visual-only context (ui/backend/services/comparison_report.py)

- `_GOLD_OVERLAY_CASES` + `_VISUAL_ONLY_CASES` split (mirrors renderer).
- New `_build_visual_only_context(case_id, run_label, timestamp, artifact_dir)`
  returns reduced context: `{visual_only: True, case_id, run_label,
  timestamp, renders: {contour_png_rel, residuals_png_rel}, solver,
  commit_sha, verdict: None, paper: None, metrics: None, gci: None, ...}`.
  Template + frontend detect `visual_only` and suppress gold-dependent
  sections.
- `build_report_context` dispatches to visual-only branch for
  `_VISUAL_ONLY_CASES` after the shared `_load_run_manifest` +
  `_validated_timestamp` + containment check steps.

### 4. Render-serving route (ui/backend/routes/comparison_report.py)

New `GET /api/cases/{case_id}/runs/{run_label}/renders/{filename:path}`
serves PNG / Plotly JSON via `FileResponse`. Path-containment defense
(resolve + `.relative_to(_RENDERS_ROOT / case_id)`), traversal rejection
(`..`, absolute paths, `\\`), MIME type discrimination.

### 5. Frontend visual-only branch (ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx)

`ScientificComparisonReportSection` detects `data.visual_only` and
renders a 2-column contour + residuals panel with a "Visual-only mode"
badge instead of the full verdict card + 8-section iframe embed. Images
served via new `/api/.../renders/{filename}` endpoint (keeps URL under
signed API surface, avoids FastAPI StaticFiles mount).

## Integration run results (10 cases)

| Case | Verdict | Duration | Renders | Notes |
|---|---|---|---|---|
| lid_driven_cavity | PARTIAL 11/17 | — | ✅ full (gold-overlay) | Pre-existing DEC-V61-032 |
| backward_facing_step | FAIL | 9.1s | ✅ contour + residuals | Diverged (kEpsilon issue) |
| plane_channel_flow | PASS | 426s | ✅ | Real convergent run |
| turbulent_flat_plate | FAIL | 35.8s | ✅ | Diverged (known kEpsilon config) |
| duct_flow | FAIL | 36s | ✅ | Diverged |
| differential_heated_cavity | FAIL | 1059s | ✅ | buoyantFoam slow + diverged |
| impinging_jet | FAIL | 152s | ✅ | Diverged |
| naca0012_airfoil | FAIL | 20s | ✅ (scatter fallback) | Diverged; qhull singular → scatter |
| rayleigh_benard_convection | (batch in-flight at DEC author time) | — | pending | |
| circular_cylinder_wake | PASS | 30.6s | ❌ foamToVTK failed | Subagent investigating |

**Verdict column note**: the 7 FAILs are NOT new regressions — they're
pre-existing solver config issues surfaced by the Tier C evidence capture
(per CLAUDE.md memory: TFP known `kEpsilon` convergence issue; NACA0012
known divergent; DHC Ra=1e10 underfunded mesh). The commercial-demo
surface now honestly shows that these cases need more work, which is
better than hiding behind pretty placeholder PNGs that implied everything
was passing.

## Test coverage (ui/backend/tests/test_comparison_report_visual_only.py, NEW)

7 tests added (0 removed):
- `test_visual_only_cases_are_nine` — set membership guards
- `test_visual_only_context_shape` — returned dict shape + key contents
- `test_unknown_case_404` — unsupported case → 404 not 500
- `test_render_route_traversal_rejected` — `..`-encoded URL → 404
- `test_render_route_missing_run_manifest_404` — no manifest → 404 graceful
- `test_visual_only_context_rejects_tampered_timestamp` — `timestamp=
  "../../../etc/passwd"` raises ReportError
- `test_gold_overlay_case_not_affected_by_visual_only_branch` — LDC still
  dispatches to full gold-overlay code path

Regression gate: `PYTHONPATH=. .venv/bin/pytest ui/backend/tests/ -q`
→ **139/139 passed** (was 132 → +7 new tests, 0 removed, 0 flakes).
Frontend `tsc --noEmit` clean.

## Honest residuals

- `circular_cylinder_wake` foamToVTK container failure — blocks contour
  for this one case. Subagent investigation launched; will land in
  follow-up commit with adapter fix (if small) or DEC-V61-035 (if
  substantive). Residuals plot will land from log-parse fallback once
  render is re-run.
- `rayleigh_benard_convection` batch run may still be in-flight at DEC
  commit time — will render + commit as a follow-up landing.
- 7 FAIL cases have diverged solvers — contour shows garbage fields
  honestly (NaN-clipped + percentile-capped), residuals show the
  non-converging trajectory. This is the point of Tier C: users see
  the truth.
- Tier B per-case gold-overlay reports remain future work (separate DEC
  if/when user prioritizes).

## Counter arc

Pre: counter 19 (DEC-V61-033).
Post: counter 20 (this DEC, autonomous_governance=true, Codex-mandatory
path — multi-file backend + frontend + new API contract).

**RETRO-V61-001 cadence trigger**: counter reaching 20 fires the arc-size
retrospective rule. Retro will land in `.planning/retrospectives/
RETRO-V61-002_counter_20_arc_size.md` alongside this DEC, covering:
Phase 7 Sprint 1 close, self-pass-rate calibration across DEC-V61-031
through DEC-V61-034, Codex economy summary, open questions for Tier B.

## Related

- DEC-V61-031, 032, 033 — Phase 7 precursors
- RETRO-V61-001 — governance trigger definitions (triggers #1 multi-file
  frontend + user-UX-critique invoked here)
- CLAUDE.md memory: cfd-harness-unified whitelist case pre-existing PASS/
  FAIL status
