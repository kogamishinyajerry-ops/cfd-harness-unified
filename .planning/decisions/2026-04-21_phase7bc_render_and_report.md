---
decision_id: DEC-V61-032
timestamp: 2026-04-21T19:00 local
scope: |
  Close Phase 7b (render pipeline) + Phase 7c-MVP (8-section CFD vs Gold
  HTML/PDF comparison report) + Phase 7f-MVP (frontend live embed on
  /learn/{case}). These three sub-phases together turn the Phase 7a
  data-capture foundation into the user-visible "scientific-grade evidence"
  that the Phase 7 ROADMAP was scoped to deliver.

  Impact: user visiting /learn/lid_driven_cavity now sees (1) a verdict
  card with PASS/PARTIAL/FAIL + max|dev|% + L2 + L∞ + n_pass/n_total
  metrics, (2) an iframe-embedded 8-section HTML report with the real
  Ghia-vs-sim profile overlay + color-coded pointwise deviation +
  residual convergence + grid-convergence table + solver metadata, and
  (3) download-PDF button producing a 622 KB print-ready audit document.
  The /learn case-detail page no longer shows only static placeholder
  flow-field PNGs — it shows real OpenFOAM-produced evidence.

  Phase 7d (Richardson GCI) and Phase 7e (L4 signed-zip embedding) are
  numerical refinement + audit-package integration; neither changes what
  the user sees, so both are deferred past this delivery checkpoint.
autonomous_governance: true
  (New scripts/render_case_report.py is autonomous-allowed new file.
  ui/backend/services|routes/comparison_report.py + templates/*.j2 +
  LearnCaseDetailPage.tsx edits are multi-file backend + user-facing
  documentation + frontend → Codex mandatory per RETRO-V61-001. Codex
  rounds completed with APPROVED.)
claude_signoff: yes
codex_tool_invoked: true
codex_rounds: 4
codex_round_1_verdict: CHANGES_REQUIRED
codex_round_1_findings:
  - HIGH: Manifest-derived filesystem paths (timestamp + renders outputs + PDF output_path) trusted without containment — tampered runs/{label}.json or renders manifest could steer reads outside reports/phase5_fields/, WeasyPrint base_url could pull arbitrary images into PDF, PDF writes could escape reports/phase5_reports/.
  - MEDIUM: Frontend ScientificComparisonReportSection silently returned null for ALL errors not just 404/400, hiding 500s and network failures from operators.
  - LOW: New route tests `return` silently when local artifacts missing — CI never exercised 200 path.
codex_round_2_verdict: CHANGES_REQUIRED
codex_round_2_findings:
  - MED: PDF containment check ran AFTER `import weasyprint`, so on hosts where WeasyPrint native libs fail to load (e.g. macOS missing DYLD_FALLBACK_LIBRARY_PATH) the containment guard never executed and the route returned 500 instead of catching OSError → 503. Route layer only caught ImportError.
  - LOW: Route 200-path coverage still depends on local artifacts in clean CI.
codex_round_3_verdict: CHANGES_REQUIRED
codex_round_3_findings:
  - MED: GET .../comparison-report.pdf correctly mapped OSError→503, but POST .../comparison-report/build only caught ImportError → returned 500 on the exact same native-lib load failure. Asymmetric error handling between the two PDF endpoints.
codex_round_4_verdict: APPROVED
codex_tool_report_path:
  - reports/codex_tool_reports/2026-04-21_phase7bc_render_report_codex_review.md
  - reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md
  - reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md
  - reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round4.md
codex_verdict: APPROVED (after 4 rounds)
counter_status: |
  v6.1 autonomous_governance counter 17 → 18.
  DEC-V61-032 autonomous_governance=true (multi-file backend + frontend +
  user-facing docs → Codex mandatory). All 3 round-1 findings and 2
  subsequent follow-ups closed by round 4.
reversibility: fully-reversible-by-pr-revert
  (Single atomic commit. Revert restores Phase 7a-only state. Renderer
  and report service are additive; no existing code path changed
  behaviorally outside of LearnCaseDetailPage adding a new section.)
notion_sync_status: synced 2026-04-21 (https://www.notion.so/DEC-V61-032-Phase-7b-7c-MVP-7f-MVP-scientific-grade-CFD-vs-gold-reporting-349c68942bed81949a64d2f806580c6e)
github_pr_url: null (direct-to-main per Phase 7a precedent)
github_merge_sha: pending
github_merge_method: direct commit on main
external_gate_self_estimated_pass_rate: 0.35
  (Actual: CHANGES_REQUIRED × 3 then APPROVED. Self-estimated 0.35 honest
  — path-containment surfaces have a 0% round-1 pass rate across both
  Phase 7a and 7c per Codex calibration. RETRO-V61-002 datapoint:
  new filesystem-backed rendering / report pipelines should default to
  0.30-0.40 pass estimate and plan for 2-3 Codex rounds minimum.)
supersedes: null
superseded_by: null
upstream: |
  - DEC-V61-031 (Phase 7a field capture — produces artifacts consumed by 7b renderer and 7c report)
  - Phase 7 ROADMAP entry commit e4dd1d9 (proposed 6 sub-phases)
---

# DEC-V61-032: Phase 7b + 7c-MVP + 7f-MVP — scientific-grade CFD vs gold reporting

## Why now

User deep-acceptance feedback explicitly diagnosed the gap:
> "所有的 case 都没有真实的仿真结果后处理云图，也没有科研级的 CFD vs gold case 的报告，
> 这导致了你的 report 非常单薄，没有说服力。"

Phase 7a landed the data-capture. 7b + 7c + 7f together close the user-
visible gap by turning that data into (a) figures, (b) a structured 8-
section document, and (c) embedded evidence on the student-facing /learn
surface. User directive: "根据你的规划，一直推进下去，直至你觉得完备".

## What landed

### Phase 7b — Render pipeline (new: `scripts/render_case_report.py`, ~400 LOC)
- matplotlib + plotly + numpy + yaml deps added.
- Reads Phase 7a artifacts (VTK + sample CSV + residuals.csv) and produces
  5 outputs per run to `reports/phase5_renders/{case}/{ts}/`:
  - `profile_u_centerline.png` — sim solid line vs Ghia 1982 red dots
  - `profile_u_centerline.plotly.json` — interactive JSON for frontend
  - `residuals.png` — log-y Ux/Uy/p convergence history
  - `pointwise_deviation.png` — color-coded bar chart per gold y-point
    (green <5%, yellow 5-10%, red >10%)
  - `contour_u_magnitude.png` — centerline strip slice (full 2D VTK
    contour deferred to 7b polish)
- Emits `reports/phase5_renders/{case}/runs/{label}.json` manifest.
- LDC-only via `RENDER_SUPPORTED_CASES = {"lid_driven_cavity"}` opt-in.
- Codex round 1 HIGH fix: `_TIMESTAMP_RE = r"^\d{8}T\d{6}Z$"` shape gate
  on manifest-supplied timestamp; containment check after compose.

### Phase 7c-MVP — Comparison report (new: service + route + template + 13 tests)
- `ui/backend/services/comparison_report.py` (~360 LOC) — builds context dict
  from LDC gold YAML (multi-doc `safe_load_all`) + sim sample .xy +
  residuals.csv + mesh_{20,40,80,160} fixtures. Computes L2/L∞/RMS/max |dev|%
  per Ghia point. Verdict logic: all-pass → PASS, ≥60% → PARTIAL (honest
  for LDC 11/17 state), else FAIL.
- `ui/backend/templates/comparison_report.html.j2` — 8 sections with
  gradient verdict card, paper citation, image references, tables. Strict
  Jinja2 autoescape.
- `ui/backend/routes/comparison_report.py` — 4 endpoints:
  - `GET  /api/cases/{c}/runs/{r}/comparison-report`        → HTML
  - `GET  /api/cases/{c}/runs/{r}/comparison-report/context`→ JSON raw ctx
  - `GET  /api/cases/{c}/runs/{r}/comparison-report.pdf`    → WeasyPrint PDF FileResponse
  - `POST /api/cases/{c}/runs/{r}/comparison-report/build`  → rebuild
- Traversal defense: reuses Phase 7a `_validate_segment` from run_ids.py.
- PDF: 622 KB valid PDF 1.7 for LDC, all 8 sections rendered with
  images resolved via WeasyPrint `base_url=_REPO_ROOT`.

### Phase 7f-MVP — Frontend live embed (LearnCaseDetailPage.tsx +162 LOC)
- New `ScientificComparisonReportSection` React component in StoryTab.
- Fetches `/api/cases/{id}/runs/audit_real_run/comparison-report/context`.
- Silently hides on 404/400 (case not opted-in); shows ErrorCallout banner
  on any other HTTP error (Codex round 1 MED fix).
- Renders verdict card with metrics grid + iframe embed of HTML report +
  "Open in new window" + "Download PDF" buttons.
- iframe `sandbox=""` (strict — no scripts, no same-origin) per Codex
  confirmation that sandbox="" is the right level.

### Codex-driven hardening (4 rounds, path-containment focus)

Round 1 HIGH — path traversal via manifest-supplied values. Fixed by:
- `_TIMESTAMP_RE` shape gate in both comparison_report.py and render_case_report.py
- `_safe_rel_under(path, root)` validator for renders_manifest outputs —
  rejects non-string, empty, absolute, backslash, `..` segments, and any
  path that fails `.resolve().relative_to(root)`
- Non-object JSON run_manifest rejected early
- PDF `output_path` must `.resolve().relative_to(reports_root)` — both
  default path and caller-supplied path

Round 2 MED — containment check must precede WeasyPrint import; OSError
(libgobject load failure) must also → 503, not 500. Fixed by moving
containment check before `import weasyprint` and catching `(ImportError, OSError)`
in GET route.

Round 3 MED — POST /build route had asymmetric error handling (only
ImportError). Fixed by making POST match GET pattern.

Round 4: APPROVED.

## Verification

| Check | Result |
|---|---|
| Backend pytest | ✅ **114/114** (was 97/97 pre-7bc; +17 new comparison_report + render tests) |
| Frontend tsc --noEmit | ✅ clean |
| Live HTML endpoint | ✅ 200, 7.7 KB, 8 §§ markers present |
| Live PDF endpoint | ✅ 200, 622 KB valid PDF 1.7 |
| Live traversal | ✅ 400 on `..__pwn`, 400 on URL-encoded `%2e%2e__pwn` |
| CI-safe synthetic route tests | ✅ 4 tests (HTML 200, context 200, GET PDF 503-on-OSError, POST build 503-on-OSError) |
| Service unit tests | ✅ 7 tests (happy path, 8 sections, 4 traversal/non-object variants, PDF containment) |
| Codex 4 rounds | ✅ APPROVED |

## Honest residuals

1. **Contour is 1D centerline slice, not full 2D VTK**. Full 2D U magnitude
   contour with streamlines requires parsing the VTK volume via the `vtk`
   Python package, deferred to Phase 7b polish. Caption on the rendered
   figure honestly says "Phase 7b MVP" and "full 2D VTK contour deferred".
2. **LDC-only**. 9 other whitelist cases are not yet opted-in via
   `RENDER_SUPPORTED_CASES` or `_REPORT_SUPPORTED_CASES`. Phase 7c Sprint-2
   fan-out will unlock them.
3. **Phase 7d (Richardson GCI) not yet done**. Grid-convergence table in
   report §7 shows raw |dev|% monotone convergence but no formal observed
   order of accuracy `p_obs` nor GCI_21/32. Deferred.
4. **Phase 7e (L4 signed-zip embedding) not yet done**. PDF + PNG are not
   yet in the HMAC-signed audit-package zip; users can download PDF
   separately via the dedicated endpoint but it's outside the signed
   artifact set.
5. **Dev-env requirement**: macOS hosts without `DYLD_FALLBACK_LIBRARY_PATH`
   set will get 503 on the PDF endpoints. Informative error message now
   surfaces the fix.

## Delta

| Metric | Pre-7bc | Post-7bc |
|---|---|---|
| Backend pytest | 97/97 | **114/114** (+17) |
| /learn/lid_driven_cavity user-visible evidence | static flow-field PNGs | **live 8-section report with verdict card + profile overlay + color-coded deviation + residuals + grid convergence** |
| PDF audit document | absent | **622 KB print-ready** via `/comparison-report.pdf` |
| Path-containment coverage | manifest values trusted | **2-layer validation** (shape gate + resolve/relative_to) |
| v6.1 counter | 17 | **18** |

## Pending closure

- [x] Phase 7b renderer landed + smoke-tested on real LDC artifacts
- [x] Phase 7c HTML+PDF rendering working (622 KB PDF with 8 §§)
- [x] Phase 7f frontend ScientificComparisonReportSection embedded
- [x] Codex 4 rounds → APPROVED
- [x] 114/114 pytest green
- [x] Atomic git commit (df8e0e2)
- [x] Notion sync DEC-V61-032 (https://www.notion.so/DEC-V61-032-Phase-7b-7c-MVP-7f-MVP-scientific-grade-CFD-vs-gold-reporting-349c68942bed81949a64d2f806580c6e)
- [x] ROADMAP Phase 7b/7c/7f status markers (done in commit df8e0e2)
- [x] STATE.md S-009 entry (done in commit df8e0e2)
