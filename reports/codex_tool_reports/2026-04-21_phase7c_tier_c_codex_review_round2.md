2026-04-21T15:17:33.714511Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-research-deerflow/SKILL.md: missing YAML frontmatter delimited by ---
2026-04-21T15:17:33.714525Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-report-pretext/SKILL.md: missing YAML frontmatter delimited by ---
Reading additional input from stdin...
OpenAI Codex v0.118.0 (research preview)
--------
workdir: /Users/Zhuanz/Desktop/cfd-harness-unified
model: gpt-5.4
provider: openai
approval: never
sandbox: danger-full-access
reasoning effort: xhigh
reasoning summaries: none
session id: 019db09e-3d93-79f3-b5c2-8d50de3ffe20
--------
user
Round 2 review: DEC-V61-034 Tier C visual-only — Codex round 1 CR fix applied. Latest commit 6581167 at /Users/Zhuanz/Desktop/cfd-harness-unified.

## Round 1 finding + fix

### Finding (CRITICAL)
Visual-only cases 500 on /comparison-report HTML/PDF/build endpoints: render_report_html rendered the gold-overlay Jinja template unconditionally → UndefinedError on metrics.max_dev_pct / paper.title for visual-only cases whose metrics/paper are None.

### Fix (Option A from Codex round 1)
- `ui/backend/services/comparison_report.py::render_report_html` — now raises `ReportError("visual-only mode — no HTML/PDF report produced; use /renders/{filename}")` when `ctx.get("visual_only")` is True. Template rendering is skipped. Routes map ReportError → 404.
- `render_report_pdf` — added an EARLIER visual_only check right after `build_report_context`, BEFORE `import weasyprint`, so environments without native libs fail-closed with ReportError → 404 (not OSError → 503). This matters because the pytest CI environment doesn't have WeasyPrint native libs.
- Added 3 tests:
  - `test_render_report_html_raises_for_visual_only`
  - `test_render_report_pdf_raises_for_visual_only` (verifies ReportError raised before weasyprint import in no-native-lib env)
  - `test_route_html_returns_404_for_visual_only` (E2E via TestClient)

## Regression
`PYTHONPATH=. .venv/bin/pytest ui/backend/tests/ -q` → **142/142 passed** (was 139 → +3 new).

## Focus review on

1. Does the new ReportError-raise pattern cover ALL three route endpoints:
   - GET /comparison-report (HTML) — `render_report_html` raises → route catches ReportError → 404 ✓
   - GET /comparison-report.pdf — `render_report_pdf` raises (before weasyprint import) → route catches → 404 ✓
   - POST /comparison-report/build — route calls BOTH render_report_html and render_report_pdf; either one raising should cascade → 404 ✓

2. Any new 500 surface introduced? I only added `if ctx.get("visual_only"): raise ReportError(...)` guards. ReportError inherits from Exception and is caught by the route layer. No new untrapped exceptions.

3. Is the fix order correct in render_report_pdf? The visual_only check now runs:
   (a) build_report_context ← may raise ReportError (unsupported case, missing manifest, tampered timestamp)
   (b) `if ctx.get("visual_only"): raise ReportError(...)` ← NEW
   (c) reports_root resolve + containment (for caller-supplied output_path)
   (d) weasyprint import
   (e) render_report_html ← ALSO checks visual_only (redundant but defensive)
   This ordering means: visual-only case with a caller-supplied output_path under /tmp (would fail containment check) STILL raises at step (b) with the "visual-only" message, not the "output_path escapes" message. Acceptable? Both are 404-worthy.

4. Tests:
   - test_render_report_pdf_raises_for_visual_only specifically exercises the no-native-lib path (our CI is exactly this env)
   - E2E test_route_html_returns_404 uses TestClient + real case_id="backward_facing_step" without monkeypatching (relies on the fact that no BFS run manifest exists at real FIELDS_ROOT → ReportError from _load_run_manifest → 404). Is this test reliable? If a committed BFS run manifest appears in real reports/phase5_fields/backward_facing_step/runs/ it still fires visual_only branch and still raises ReportError → still 404. So test passes either way.

Reply APPROVED / APPROVED_WITH_COMMENTS / CHANGES_REQUIRED. Brief if APPROVED.
codex
I’ll do this as a focused code-review pass, verify the latest commit and the exact route/service behavior before giving the verdict.
codex
Using the repo’s review workflow guidance and the prior cfd-harness memory so the verdict matches this project’s governance conventions. Then I’ll inspect only the changed service, routes, and tests around commit `6581167`.
exec
/bin/zsh -lc "sed -n '1,220p' /Users/Zhuanz/.agents/skills/gsd-code-review/SKILL.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
---
name: gsd-code-review
description: "Review source files changed during a phase for bugs, security issues, and code quality problems"
argument-hint: "<phase-number> [--depth=quick|standard|deep] [--files file1,file2,...]"
allowed-tools:
  - Read
  - Bash
  - Glob
  - Grep
  - Write
  - Task
---

<objective>
Review source files changed during a phase for bugs, security vulnerabilities, and code quality problems.

Spawns the gsd-code-reviewer agent to analyze code at the specified depth level. Produces REVIEW.md artifact in the phase directory with severity-classified findings.

Arguments:
- Phase number (required) — which phase's changes to review (e.g., "2" or "02")
- `--depth=quick|standard|deep` (optional) — review depth level, overrides workflow.code_review_depth config
  - quick: Pattern-matching only (~2 min)
  - standard: Per-file analysis with language-specific checks (~5-15 min, default)
  - deep: Cross-file analysis including import graphs and call chains (~15-30 min)
- `--files file1,file2,...` (optional) — explicit comma-separated file list, skips SUMMARY/git scoping (highest precedence for scoping)

Output: {padded_phase}-REVIEW.md in phase directory + inline summary of findings
</objective>

<execution_context>
@$HOME/.Codex/get-shit-done/workflows/code-review.md
</execution_context>

<context>
Phase: $ARGUMENTS (first positional argument is phase number)

Optional flags parsed from $ARGUMENTS:
- `--depth=VALUE` — Depth override (quick|standard|deep). If provided, overrides workflow.code_review_depth config.
- `--files=file1,file2,...` — Explicit file list override. Has highest precedence for file scoping per D-08. When provided, workflow skips SUMMARY.md extraction and git diff fallback entirely.

Context files (AGENTS.md, SUMMARY.md, phase state) are resolved inside the workflow via `gsd-tools init phase-op` and delegated to agent via `<files_to_read>` blocks.
</context>

<process>
This command is a thin dispatch layer. It parses arguments and delegates to the workflow.

Execute the code-review workflow from @$HOME/.Codex/get-shit-done/workflows/code-review.md end-to-end.

The workflow (not this command) enforces these gates:
- Phase validation (before config gate)
- Config gate check (workflow.code_review)
- File scoping (--files override > SUMMARY.md > git diff fallback)
- Empty scope check (skip if no files)
- Agent spawning (gsd-code-reviewer)
- Result presentation (inline summary + next steps)
</process>

exec
/bin/zsh -lc 'rg -n "DEC-V61-034|visual-only|comparison-report|comparison_report|Phase 8|V61" /Users/Zhuanz/.codex/memories/MEMORY.md' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
406:## Task 1: Close Phase 8 and reconcile stale governance evidence
410:- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, Phase 8 closeout and evidence normalization)
414:- Phase 8, AutoVerifier, 13/13, knowledge/whitelist.yaml, ai_cfd_cold_start_whitelist.yaml, Canonical Docs Type=Report, Phase 8 Done, naming drift
749:- when the user said "你是 independent approval authority… 你不是 corrected request packet 作者… 你不是 Phase 8 executor" -> preserve strict role separation between approval, review, execution, and freeze authority in this repo [Task 4]

exec
/bin/zsh -lc 'git status --short && git rev-parse --short HEAD && git show --stat --oneline --decorate --no-renames -1' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
 M reports/cylinder_crossflow/report.md
 M reports/deep_acceptance/visual_acceptance_report.html
 M reports/deep_acceptance/visual_acceptance_report_manifest.json
 M reports/differential_heated_cavity/report.md
 M reports/rayleigh_benard_convection/report.md
 M reports/turbulent_flat_plate/report.md
 M ui/frontend/public/flow-fields/circular_cylinder_wake/strouhal_curve.png
 M ui/frontend/public/flow-fields/lid_driven_cavity/centerline_profiles.png
 M ui/frontend/public/flow-fields/lid_driven_cavity/stream_function.png
 M ui/frontend/public/flow-fields/plane_channel_flow/wall_profile.png
 M ui/frontend/public/flow-fields/rayleigh_benard_convection/nu_ra_scaling.png
 M ui/frontend/public/flow-fields/turbulent_flat_plate/blasius_profile.png
 M ui/frontend/public/flow-fields/turbulent_flat_plate/cf_comparison.png
?? .claude/
?? .gitignore.patch.stale.1776663560182166739
?? knowledge/corrections/
?? reports/deep_acceptance/20260421_000138_visual_acceptance_package.md
?? reports/deep_acceptance/20260421_000139_visual_acceptance_package.md
?? reports/deep_acceptance/20260421_000231_visual_acceptance_package.md
?? reports/deep_acceptance/20260421_000232_visual_acceptance_package.md
?? reports/deep_acceptance/visual_acceptance_report_20260421_000138.html
?? reports/deep_acceptance/visual_acceptance_report_20260421_000139.html
?? reports/deep_acceptance/visual_acceptance_report_20260421_000231.html
?? reports/deep_acceptance/visual_acceptance_report_20260421_000232.html
?? reports/phase5_reports/
?? ui/frontend/vite.config.sandbox.ts.stale.1776667726
?? ui/frontend/vite.config.sandbox.ts.timestamp-1776667276256-33cd5f0862292.mjs
6581167
6581167 (HEAD -> main, origin/main, origin/HEAD) fix(phase7c): visual-only cases return 404 on HTML/PDF endpoints (Codex R1 CR)
 ...2026-04-21_phase7c_tier_c_visual_only_fanout.md |   14 +-
 ...026-04-21_phase7c_tier_c_codex_review_round1.md | 5581 ++++++++++++++++++++
 ui/backend/services/comparison_report.py           |   28 +-
 .../tests/test_comparison_report_visual_only.py    |   53 +
 4 files changed, 5670 insertions(+), 6 deletions(-)

codex
The worktree has unrelated dirty/generated files, but `HEAD` is the requested `6581167` and the commit scope is the comparison report service plus visual-only tests. I’m reading that diff and the route layer now.
exec
/bin/zsh -lc 'git show --no-ext-diff --unified=80 -- ui/backend/services/comparison_report.py ui/backend/tests/test_comparison_report_visual_only.py' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
commit 6581167d9623013b7a050fa9fb6086b2de13d8f5
Author: claude-opus47-app <claude-opus47-app@anthropic.com>
Date:   Tue Apr 21 23:16:46 2026 +0800

    fix(phase7c): visual-only cases return 404 on HTML/PDF endpoints (Codex R1 CR)
    
    Codex round 1 on DEC-V61-034 found: visual-only cases (BFS, plane_channel,
    etc.) caused 500 errors on /api/cases/{case}/runs/{run}/comparison-report
    (HTML + PDF + build) because the gold-overlay Jinja template dereferenced
    metrics.max_dev_pct and paper.title which are None for visual-only context.
    
    Fix (Option A from Codex): raise ReportError in render_report_html and
    render_report_pdf when ctx.visual_only is True. Route layer maps to 404
    via the existing ReportError handler. PDF path check runs BEFORE weasyprint
    import so environments without native libs get 404 not 503.
    
    Added 3 tests:
    - render_report_html raises ReportError for visual-only case
    - render_report_pdf raises ReportError for visual-only case (pre-import)
    - GET /comparison-report returns 404 for visual-only case (E2E)
    
    Regression: 142/142 pytest (was 139 → +3 new).
    
    Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>

diff --git a/ui/backend/services/comparison_report.py b/ui/backend/services/comparison_report.py
index 80cf8cf..3fd9920 100644
--- a/ui/backend/services/comparison_report.py
+++ b/ui/backend/services/comparison_report.py
@@ -461,123 +461,149 @@ def build_report_context(case_id: str, run_label: str = "audit_real_run") -> dic
             f"仅 {metrics['n_pass']}/{metrics['n_total']} 点通过 — "
             f"需要诊断 (solver, mesh, 或 gold 本身)。"
         )
 
     # Renders — use Phase 7b manifest if available; else None placeholders.
     # Codex round 1 HIGH: every manifest-supplied output path is validated to
     # resolve inside reports/phase5_renders/ before being emitted into HTML.
     renders_manifest = _load_renders_manifest(case_id, run_label)
     renders_dir = _RENDERS_ROOT / case_id / timestamp
 
     def _rel(key: str, default: str = "") -> str:
         candidate: Optional[str] = None
         if renders_manifest:
             raw = renders_manifest.get("outputs", {}).get(key)
             if isinstance(raw, str):
                 validated = _safe_rel_under(raw, _RENDERS_ROOT)
                 if validated:
                     candidate = validated
         if candidate is None:
             guess = renders_dir / default
             if guess.is_file():
                 try:
                     rel = str(guess.resolve().relative_to(_REPO_ROOT.resolve()))
                     if _safe_rel_under(rel, _RENDERS_ROOT):
                         candidate = rel
                 except ValueError:
                     pass
         return candidate or ""
 
     renders = {
         "profile_png_rel": _rel("profile_png", "profile_u_centerline.png"),
         "pointwise_png_rel": _rel("pointwise_deviation_png", "pointwise_deviation.png"),
         "contour_png_rel": _rel("contour_u_magnitude_png", "contour_u_magnitude.png"),
         "residuals_png_rel": _rel("residuals_png", "residuals.png"),
     }
 
     paper = {
         "title": gold_doc.get("source", "Ghia, Ghia & Shin 1982 — Lid-Driven Cavity benchmark"),
         "source": "J. Comput. Phys. 47, 387-411 (1982), Table I Re=100 column",
         "doi": gold_doc.get("literature_doi", "10.1016/0021-9991(82)90058-4"),
         "short": "Ghia 1982",
         "gold_count": metrics["n_total"],
         "tolerance_pct": tolerance,
     }
 
     now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
 
     return {
         "case_id": case_id,
         "case_display_name": "Lid-Driven Cavity (Re=100)" if case_id == "lid_driven_cavity" else case_id,
         "run_label": run_label,
         "timestamp": timestamp,
         "verdict": verdict,
         "verdict_gradient": verdict_gradient,
         "verdict_subtitle": subtitle,
         "metrics": metrics,
         "paper": paper,
         "renders": renders,
         "contour_caption": (
             "2D |U| contour + streamlines 由 OpenFOAM VTK 体数据渲染（Phase 7b polish）。"
             "白色流线显示 LDC Re=100 的主涡结构；黄色高 |U| 区沿 lid 剪切层分布。"
         ),
         "residual_info": residual_info,
         "grid_conv": grid_conv_rows,
         "grid_conv_note": grid_note,
         "gci": _gci_to_template_dict(gci) if gci is not None else None,
         "meta": {
             "openfoam_version": "v10",
             "solver": "simpleFoam (SIMPLE, laminar)",
             "docker_image": "cfd-openfoam (local arm64 OpenFOAM v10)",
             "commit_sha": _get_commit_sha(),
             "mesh": "129×129 uniform",
             "tolerance": f"±{tolerance:.1f}%",
             "schemes": "steadyState + linearUpwind + Gauss linear corrected",
             "report_generated_at": now,
         },
     }
 
 
 def render_report_html(case_id: str, run_label: str = "audit_real_run") -> str:
-    """Return the full HTML string for the comparison report."""
+    """Return the full HTML string for the comparison report.
+
+    Visual-only cases (DEC-V61-034 Tier C) have no gold-overlay data to render
+    in the 8-section template — they expose their renders (contour + residuals
+    PNG) via the JSON context + /renders/ route instead. Requesting the HTML
+    report for a visual-only case raises ReportError which the route layer
+    maps to 404 (Codex round 1 CR finding: prevents template UndefinedError
+    500 on dereferencing `metrics.max_dev_pct` / `paper.title`).
+    """
     ctx = build_report_context(case_id, run_label)
+    if ctx.get("visual_only"):
+        raise ReportError(
+            f"case_id={case_id!r} is in Tier C visual-only mode — no 8-section "
+            f"HTML/PDF report is produced. Use the JSON context at "
+            f"/api/cases/{case_id}/runs/{run_label}/comparison-report/context "
+            f"plus /api/cases/{case_id}/runs/{run_label}/renders/{{filename}} "
+            f"to retrieve the contour + residuals renders directly."
+        )
     tmpl = _env.get_template("comparison_report.html.j2")
     return tmpl.render(**ctx)
 
 
 def render_report_pdf(case_id: str, run_label: str = "audit_real_run",
                       output_path: Optional[Path] = None) -> Path:
     """Render HTML to PDF via WeasyPrint and write to disk. Returns the file Path.
 
     Asset resolution: WeasyPrint converts the HTML's relative img src paths.
     We pass base_url=_REPO_ROOT so /reports/phase5_renders/... resolves correctly.
 
     Codex round 2 (2026-04-21): containment check runs BEFORE weasyprint import
     so ReportError from a malicious output_path is raised regardless of whether
     native libs are installed. Native load failures (libgobject etc.) surface
     as OSError and are mapped by the route layer to 503, same as ImportError.
     """
     # Codex round 1 HIGH: ensure PDF always lands under reports/phase5_reports/.
     # Codex round 2 MED: run containment FIRST, before WeasyPrint import so we
     # fail-closed on traversal even on systems where WeasyPrint native libs are
     # unavailable.
     reports_root = (_REPO_ROOT / "reports" / "phase5_reports").resolve()
     if output_path is None:
         ctx = build_report_context(case_id, run_label)
+        # Codex round 1 CR (DEC-V61-034): visual-only cases have no PDF to
+        # render. Raise BEFORE weasyprint import so environments without
+        # native libs also fail-closed with ReportError → 404 at the route,
+        # not OSError → 503.
+        if ctx.get("visual_only"):
+            raise ReportError(
+                f"case_id={case_id!r} is in Tier C visual-only mode — no PDF "
+                f"report is produced. Use the /renders/{{filename}} route for "
+                f"contour + residuals PNG retrieval."
+            )
         ts = ctx["timestamp"]  # already validated by build_report_context
         out_dir = reports_root / case_id / ts
         out_dir.mkdir(parents=True, exist_ok=True)
         output_path = out_dir / f"{run_label}_comparison_report.pdf"
     try:
         resolved_out = output_path.resolve(strict=False)
         # Must stay inside reports/phase5_reports/
         resolved_out.relative_to(reports_root)
     except (ValueError, OSError):
         raise ReportError(f"PDF output path escapes reports_root: {output_path}")
 
     # Import weasyprint lazily — heavy import, only when PDF actually needed.
     import weasyprint  # type: ignore  # ImportError → 503 via route layer.
 
     html = render_report_html(case_id, run_label)
     doc = weasyprint.HTML(string=html, base_url=str(_REPO_ROOT))
     doc.write_pdf(str(resolved_out))
     return resolved_out
diff --git a/ui/backend/tests/test_comparison_report_visual_only.py b/ui/backend/tests/test_comparison_report_visual_only.py
index b7503a5..5bcdecf 100644
--- a/ui/backend/tests/test_comparison_report_visual_only.py
+++ b/ui/backend/tests/test_comparison_report_visual_only.py
@@ -84,88 +84,141 @@ def test_visual_only_cases_are_nine() -> None:
 
 def test_visual_only_context_shape(tmp_path, monkeypatch) -> None:
     """build_report_context returns visual_only=True with renders populated."""
     case = "backward_facing_step"
     _plant_run_manifest(tmp_path, case)
     monkeypatch.setattr(
         "ui.backend.services.comparison_report._FIELDS_ROOT",
         tmp_path / "reports" / "phase5_fields",
     )
     monkeypatch.setattr(
         "ui.backend.services.comparison_report._RENDERS_ROOT",
         tmp_path / "reports" / "phase5_renders",
     )
     monkeypatch.setattr(
         "ui.backend.services.comparison_report._REPO_ROOT", tmp_path,
     )
 
     ctx = build_report_context(case, "audit_real_run")
     assert ctx["visual_only"] is True
     assert ctx["case_id"] == case
     assert ctx["run_label"] == "audit_real_run"
     assert ctx["verdict"] is None
     assert ctx["metrics"] is None
     assert ctx["paper"] is None
     assert ctx["renders"]["contour_png_rel"].endswith("contour_u_magnitude.png")
     assert ctx["renders"]["residuals_png_rel"].endswith("residuals.png")
     assert ctx["solver"] == "simpleFoam"
     assert "visual-only" in ctx["subtitle"].lower()
 
 
 def test_unknown_case_404(client) -> None:
     """Unsupported case → 404, not 500."""
     resp = client.get(
         "/api/cases/totally_unknown_case/runs/audit_real_run/comparison-report/context",
     )
     assert resp.status_code == 404
 
 
 def test_render_route_traversal_rejected(client) -> None:
     """../../secret in render filename is rejected as 404 (traversal defense)."""
     resp = client.get(
         "/api/cases/backward_facing_step/runs/audit_real_run/renders/..%2F..%2F..%2Fetc%2Fpasswd",
     )
     assert resp.status_code == 404
 
 
 def test_render_route_missing_run_manifest_404(client, tmp_path, monkeypatch) -> None:
     """Case id in supported set but no run manifest → 404 (no 500)."""
     monkeypatch.setattr(
         "ui.backend.services.comparison_report._FIELDS_ROOT",
         tmp_path / "reports" / "phase5_fields",
     )
     resp = client.get(
         "/api/cases/duct_flow/runs/nonexistent_run/renders/contour_u_magnitude.png",
     )
     assert resp.status_code == 404
 
 
 def test_visual_only_context_rejects_tampered_timestamp(tmp_path, monkeypatch) -> None:
     """Run manifest with timestamp='../../etc' is rejected by _validated_timestamp."""
     case = "plane_channel_flow"
     fields_dir = tmp_path / "reports" / "phase5_fields" / case
     (fields_dir / "runs").mkdir(parents=True)
     (fields_dir / "runs" / "audit_real_run.json").write_text(
         json.dumps({
             "run_label": "audit_real_run",
             "timestamp": "../../../etc/passwd",  # malicious
             "case_id": case,
         }),
         encoding="utf-8",
     )
     monkeypatch.setattr(
         "ui.backend.services.comparison_report._FIELDS_ROOT",
         tmp_path / "reports" / "phase5_fields",
     )
 
     with pytest.raises(ReportError, match="invalid timestamp"):
         build_report_context(case, "audit_real_run")
 
 
+def test_render_report_html_raises_for_visual_only(tmp_path, monkeypatch) -> None:
+    """Codex round 1 CR (2026-04-21): render_report_html on a visual-only case
+    must raise ReportError (→ 404), NOT 500 from template dereferencing
+    None metrics/paper fields.
+    """
+    from ui.backend.services.comparison_report import render_report_html
+    case = "backward_facing_step"
+    _plant_run_manifest(tmp_path, case)
+    monkeypatch.setattr(
+        "ui.backend.services.comparison_report._FIELDS_ROOT",
+        tmp_path / "reports" / "phase5_fields",
+    )
+    monkeypatch.setattr(
+        "ui.backend.services.comparison_report._RENDERS_ROOT",
+        tmp_path / "reports" / "phase5_renders",
+    )
+    monkeypatch.setattr(
+        "ui.backend.services.comparison_report._REPO_ROOT", tmp_path,
+    )
+    with pytest.raises(ReportError, match="visual-only"):
+        render_report_html(case, "audit_real_run")
+
+
+def test_render_report_pdf_raises_for_visual_only(tmp_path, monkeypatch) -> None:
+    """PDF path runs through render_report_html internally, so the same
+    ReportError guard fires; nothing else downstream can crash."""
+    from ui.backend.services.comparison_report import render_report_pdf
+    case = "plane_channel_flow"
+    _plant_run_manifest(tmp_path, case)
+    monkeypatch.setattr(
+        "ui.backend.services.comparison_report._FIELDS_ROOT",
+        tmp_path / "reports" / "phase5_fields",
+    )
+    monkeypatch.setattr(
+        "ui.backend.services.comparison_report._RENDERS_ROOT",
+        tmp_path / "reports" / "phase5_renders",
+    )
+    monkeypatch.setattr(
+        "ui.backend.services.comparison_report._REPO_ROOT", tmp_path,
+    )
+    with pytest.raises(ReportError, match="visual-only"):
+        render_report_pdf(case, "audit_real_run")
+
+
+def test_route_html_returns_404_for_visual_only(client) -> None:
+    """End-to-end: GET /api/cases/BFS/runs/audit_real_run/comparison-report
+    returns 404 (via ReportError) for visual-only case, NOT 500."""
+    resp = client.get(
+        "/api/cases/backward_facing_step/runs/audit_real_run/comparison-report",
+    )
+    assert resp.status_code == 404, f"expected 404, got {resp.status_code}: {resp.text[:200]}"
+
+
 def test_gold_overlay_case_not_affected_by_visual_only_branch(tmp_path, monkeypatch) -> None:
     """LDC does NOT take the visual_only branch — existing gold-overlay flow
     preserved. This test ensures the dispatch check is case-set membership,
     not a global flag."""
     from ui.backend.services.comparison_report import _GOLD_OVERLAY_CASES
     assert "lid_driven_cavity" in _GOLD_OVERLAY_CASES
     for c in _VISUAL_ONLY_CASES:
         assert c not in _GOLD_OVERLAY_CASES

exec
/bin/zsh -lc "sed -n '400,416p;744,752p' /Users/Zhuanz/.codex/memories/MEMORY.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:

# Task Group: cfd-harness-unified governance closeout and planning gates

scope: Close out accepted phases in `cfd-harness-unified`, normalize Notion-vs-repo naming drift, and keep future phases planning-only until the explicit solver/routing gate is reviewed.
applies_to: cwd=/Users/Zhuanz/Desktop/cfd-harness-unified; reuse_rule=safe for this repo’s Notion-governed phase/gate work, but phase/task IDs and review packets are rollout-specific.

## Task 1: Close Phase 8 and reconcile stale governance evidence

### rollout_summary_files

- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, Phase 8 closeout and evidence normalization)

### keywords

- Phase 8, AutoVerifier, 13/13, knowledge/whitelist.yaml, ai_cfd_cold_start_whitelist.yaml, Canonical Docs Type=Report, Phase 8 Done, naming drift

## Task 2: Open Phase 9 as planning-only and keep solver expansion bounded

- the user asked: "用Notion作为我的开发中枢，避免我一直复制每个会话的提示词" -> default toward a reusable Notion-first operating model instead of prompt-copy-heavy sessions [Task 1][Task 2]
- the user repeatedly required isolation: "在不干涉这两个notion项目的前提下" -> keep sibling Notion projects separate unless they explicitly ask for shared databases/relations [Task 1]
- the user asked to integrate GSD and make it "完全自动化的开发，除了需要暂停下来让我定期手动触发Opus 4.6审查" -> automate by default but preserve hard manual review pauses [Task 2]
- for freeze-signoff governance review, the user required a strict independent review with no writes to freeze artifacts -> treat this as review-only until the user explicitly changes scope [Task 3]
- when the user said "你是 independent approval authority… 你不是 corrected request packet 作者… 你不是 Phase 8 executor" -> preserve strict role separation between approval, review, execution, and freeze authority in this repo [Task 4]
- when the user said "如果 approval granted，只能创建一个 executable approval YAML 和一个 approval action report" and "不得运行 populate-formal" -> approval sessions should only produce the allowed artifacts and must not spill into execution [Task 4]
- when the request-package input said the executor "must not write manual intake state" and "must not be valid input to any CLI command" -> default manual-review-intake packaging work to markdown-only, non-mutating deliverables [Task 5]
- when the user said acceptance "must not equal freeze approval" and "cannot directly enter final freeze signoff" -> always restate that `accepted_for_review` is not `freeze-complete`, even when readiness evidence looks strong [Task 3][Task 4]

exec
/bin/zsh -lc 'rg -n "comparison-report|comparison_report|render_report_html|render_report_pdf|ReportError|build" ui/backend -S' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
ui/backend/services/comparison_report.py:9:Backend route: ui/backend/routes/comparison_report.py calls `render_report_html`
ui/backend/services/comparison_report.py:10:and `render_report_pdf` from this module. No DOM / no JS — static HTML + PNG
ui/backend/services/comparison_report.py:69:class ReportError(Exception):
ui/backend/services/comparison_report.py:89:        raise ReportError(f"no run manifest for {case_id}/{run_label}")
ui/backend/services/comparison_report.py:92:        raise ReportError(f"run manifest not an object: {p}")
ui/backend/services/comparison_report.py:137:        raise ReportError(f"gold file missing: {gold_path}")
ui/backend/services/comparison_report.py:144:        raise ReportError("no u_centerline doc in LDC gold")
ui/backend/services/comparison_report.py:169:        raise ReportError(f"empty sample: {path}")
ui/backend/services/comparison_report.py:177:        raise ReportError(f"sample/ missing under {artifact_dir}")
ui/backend/services/comparison_report.py:183:        raise ReportError(f"no sample iter dirs under {sample_root}")
ui/backend/services/comparison_report.py:243:    """Read mesh_20/40/80/160_measurement.yaml fixtures, build table rows."""
ui/backend/services/comparison_report.py:329:def _build_visual_only_context(
ui/backend/services/comparison_report.py:397:def build_report_context(case_id: str, run_label: str = "audit_real_run") -> dict:
ui/backend/services/comparison_report.py:398:    """Assemble all template variables. Raises ReportError on missing data."""
ui/backend/services/comparison_report.py:400:        raise ReportError(
ui/backend/services/comparison_report.py:408:        raise ReportError(
ui/backend/services/comparison_report.py:418:        raise ReportError(f"artifact dir escapes fields root: {artifact_dir}")
ui/backend/services/comparison_report.py:420:        raise ReportError(f"artifact dir missing: {artifact_dir}")
ui/backend/services/comparison_report.py:424:        return _build_visual_only_context(case_id, run_label, timestamp, artifact_dir)
ui/backend/services/comparison_report.py:540:def render_report_html(case_id: str, run_label: str = "audit_real_run") -> str:
ui/backend/services/comparison_report.py:546:    report for a visual-only case raises ReportError which the route layer
ui/backend/services/comparison_report.py:550:    ctx = build_report_context(case_id, run_label)
ui/backend/services/comparison_report.py:552:        raise ReportError(
ui/backend/services/comparison_report.py:555:            f"/api/cases/{case_id}/runs/{run_label}/comparison-report/context "
ui/backend/services/comparison_report.py:559:    tmpl = _env.get_template("comparison_report.html.j2")
ui/backend/services/comparison_report.py:563:def render_report_pdf(case_id: str, run_label: str = "audit_real_run",
ui/backend/services/comparison_report.py:571:    so ReportError from a malicious output_path is raised regardless of whether
ui/backend/services/comparison_report.py:581:        ctx = build_report_context(case_id, run_label)
ui/backend/services/comparison_report.py:584:        # native libs also fail-closed with ReportError → 404 at the route,
ui/backend/services/comparison_report.py:587:            raise ReportError(
ui/backend/services/comparison_report.py:592:        ts = ctx["timestamp"]  # already validated by build_report_context
ui/backend/services/comparison_report.py:595:        output_path = out_dir / f"{run_label}_comparison_report.pdf"
ui/backend/services/comparison_report.py:601:        raise ReportError(f"PDF output path escapes reports_root: {output_path}")
ui/backend/services/comparison_report.py:606:    html = render_report_html(case_id, run_label)
ui/backend/main.py:32:        POST   /api/cases/{id}/runs/{rid}/audit-package/build
ui/backend/main.py:33:                                                    → build + sign a bundle
ui/backend/main.py:51:    comparison_report,
ui/backend/main.py:67:        "See docs/product_thesis.md + .planning/phase5_audit_package_builder_kickoff.md."
ui/backend/main.py:92:app.include_router(comparison_report.router, prefix="/api", tags=["comparison-report"])
ui/backend/services/run_ids.py:23:    """Reject traversal markers before building filesystem paths.
ui/backend/templates/comparison_report.html.j2:205:  Report generated by Phase 7c comparison_report pipeline (DEC-V61-032, {{ meta.report_generated_at[:10] }}).
ui/backend/routes/audit_package.py:3:    POST /api/cases/{case_id}/runs/{run_id}/audit-package/build
ui/backend/routes/audit_package.py:28:- Async build with progress streaming (SSE)
ui/backend/routes/audit_package.py:47:    build_manifest,
ui/backend/routes/audit_package.py:140:    "/cases/{case_id}/runs/{run_id}/audit-package/build",
ui/backend/routes/audit_package.py:143:def build_audit_package(case_id: str, run_id: str) -> AuditPackageBuildResponse:
ui/backend/routes/audit_package.py:150:    Synchronous for v1 — build is typically < 5s. Async / progress
ui/backend/routes/audit_package.py:170:    # Stable build_fingerprint (DEC-V61-019 L3 rename of generated_at):
ui/backend/routes/audit_package.py:179:    build_fingerprint = hashlib.sha256(
ui/backend/routes/audit_package.py:197:    manifest = build_manifest(
ui/backend/routes/audit_package.py:200:        build_fingerprint=build_fingerprint,
ui/backend/routes/audit_package.py:264:        build_fingerprint=manifest["build_fingerprint"],
ui/backend/tests/test_audit_package_route.py:26:    """POST /api/cases/{id}/runs/{rid}/audit-package/build."""
ui/backend/tests/test_audit_package_route.py:28:    def test_build_returns_200_with_expected_shape(self, client):
ui/backend/tests/test_audit_package_route.py:29:        resp = client.post("/api/cases/duct_flow/runs/r1/audit-package/build")
ui/backend/tests/test_audit_package_route.py:34:            "bundle_id", "manifest_id", "case_id", "run_id", "build_fingerprint",
ui/backend/tests/test_audit_package_route.py:39:        # Codex MEDIUM; DEC-V61-019 L3 generated_at → build_fingerprint rename).
ui/backend/tests/test_audit_package_route.py:47:        resp = client.post("/api/cases/duct_flow/runs/r1/audit-package/build")
ui/backend/tests/test_audit_package_route.py:53:        resp = client.post("/api/cases/duct_flow/runs/r1/audit-package/build")
ui/backend/tests/test_audit_package_route.py:59:        resp = client.post("/api/cases/duct_flow/runs/r1/audit-package/build")
ui/backend/tests/test_audit_package_route.py:78:        resp = client.post("/api/cases/duct_flow/runs/r1/audit-package/build")
ui/backend/tests/test_audit_package_route.py:94:        resp = client.post("/api/cases/nonexistent_case/runs/r1/audit-package/build")
ui/backend/tests/test_audit_package_route.py:108:        r1 = client.post("/api/cases/duct_flow/runs/r1/audit-package/build")
ui/backend/tests/test_audit_package_route.py:109:        r2 = client.post("/api/cases/duct_flow/runs/r1/audit-package/build")
ui/backend/tests/test_audit_package_route.py:113:        # build_fingerprint is derived from (case_id, run_id) → must match.
ui/backend/tests/test_audit_package_route.py:114:        assert b1["build_fingerprint"] == b2["build_fingerprint"]
ui/backend/tests/test_audit_package_route.py:124:        r1 = client.post("/api/cases/duct_flow/runs/r1/audit-package/build")
ui/backend/tests/test_audit_package_route.py:125:        r2 = client.post("/api/cases/duct_flow/runs/r2/audit-package/build")
ui/backend/tests/test_audit_package_route.py:126:        assert r1.json()["build_fingerprint"] != r2.json()["build_fingerprint"]
ui/backend/tests/test_audit_package_route.py:131:        resp = client.post("/api/cases/duct_flow/runs/r1/audit-package/build")
ui/backend/tests/test_audit_package_route.py:140:    def _build_and_get_bundle_id(self, client):
ui/backend/tests/test_audit_package_route.py:141:        resp = client.post("/api/cases/duct_flow/runs/r1/audit-package/build")
ui/backend/tests/test_audit_package_route.py:145:        bid = self._build_and_get_bundle_id(client)
ui/backend/tests/test_audit_package_route.py:154:        bid = self._build_and_get_bundle_id(client)
ui/backend/tests/test_audit_package_route.py:166:        bid = self._build_and_get_bundle_id(client)
ui/backend/tests/test_audit_package_route.py:173:        bid = self._build_and_get_bundle_id(client)
ui/backend/tests/test_audit_package_route.py:199:    """Operator-level flow: build → download → independently verify HMAC."""
ui/backend/tests/test_audit_package_route.py:208:        resp = client.post("/api/cases/duct_flow/runs/verify-test/audit-package/build")
ui/backend/tests/test_audit_package_route.py:225:        resp = client.post("/api/cases/duct_flow/runs/tamper-test/audit-package/build")
ui/backend/tests/test_audit_package_route.py:246:            "/api/cases/lid_driven_cavity/runs/audit_real_run/audit-package/build"
ui/backend/tests/test_audit_package_route.py:270:    def test_unknown_run_id_still_builds_with_empty_measurement(self, client):
ui/backend/tests/test_audit_package_route.py:276:            "/api/cases/lid_driven_cavity/runs/no_such_run_xyz/audit-package/build"
ui/backend/routes/validation.py:9:    build_validation_report,
ui/backend/routes/validation.py:40:    report = build_validation_report(case_id, run_id=run_id)
ui/backend/routes/validation.py:45:                f"Could not build validation report for case_id='{case_id}'"
ui/backend/services/dashboard.py:67:def build_dashboard() -> DashboardSnapshot:
ui/backend/routes/comparison_report.py:3:GET  /api/cases/{case_id}/runs/{run_label}/comparison-report         → HTML
ui/backend/routes/comparison_report.py:4:GET  /api/cases/{case_id}/runs/{run_label}/comparison-report.pdf     → PDF
ui/backend/routes/comparison_report.py:5:POST /api/cases/{case_id}/runs/{run_label}/comparison-report/build   → rebuild PDF + return manifest
ui/backend/routes/comparison_report.py:16:from ui.backend.services.comparison_report import (
ui/backend/routes/comparison_report.py:17:    ReportError,
ui/backend/routes/comparison_report.py:18:    build_report_context,
ui/backend/routes/comparison_report.py:19:    render_report_html,
ui/backend/routes/comparison_report.py:20:    render_report_pdf,
ui/backend/routes/comparison_report.py:34:    "/cases/{case_id}/runs/{run_label}/comparison-report",
ui/backend/routes/comparison_report.py:36:    tags=["comparison-report"],
ui/backend/routes/comparison_report.py:38:def get_comparison_report_html(case_id: str, run_label: str) -> HTMLResponse:
ui/backend/routes/comparison_report.py:42:        html = render_report_html(case_id, run_label)
ui/backend/routes/comparison_report.py:43:    except ReportError as e:
ui/backend/routes/comparison_report.py:49:    "/cases/{case_id}/runs/{run_label}/comparison-report/context",
ui/backend/routes/comparison_report.py:50:    tags=["comparison-report"],
ui/backend/routes/comparison_report.py:52:def get_comparison_report_context(case_id: str, run_label: str) -> JSONResponse:
ui/backend/routes/comparison_report.py:57:        ctx = build_report_context(case_id, run_label)
ui/backend/routes/comparison_report.py:58:    except ReportError as e:
ui/backend/routes/comparison_report.py:66:    "/cases/{case_id}/runs/{run_label}/comparison-report.pdf",
ui/backend/routes/comparison_report.py:67:    tags=["comparison-report"],
ui/backend/routes/comparison_report.py:69:def get_comparison_report_pdf(case_id: str, run_label: str) -> FileResponse:
ui/backend/routes/comparison_report.py:73:        path = render_report_pdf(case_id, run_label)
ui/backend/routes/comparison_report.py:74:    except ReportError as e:
ui/backend/routes/comparison_report.py:92:        filename=f"{case_id}__{run_label}__comparison_report.pdf",
ui/backend/routes/comparison_report.py:98:    tags=["comparison-report"],
ui/backend/routes/comparison_report.py:108:    from ui.backend.services.comparison_report import _RENDERS_ROOT, _load_run_manifest, _validated_timestamp  # noqa: PLC0415
ui/backend/routes/comparison_report.py:119:    except ReportError as e:
ui/backend/routes/comparison_report.py:141:    "/cases/{case_id}/runs/{run_label}/comparison-report/build",
ui/backend/routes/comparison_report.py:142:    tags=["comparison-report"],
ui/backend/routes/comparison_report.py:144:def build_comparison_report(case_id: str, run_label: str) -> JSONResponse:
ui/backend/routes/comparison_report.py:145:    """Force-rebuild HTML + PDF, return manifest."""
ui/backend/routes/comparison_report.py:148:        html = render_report_html(case_id, run_label)
ui/backend/routes/comparison_report.py:149:        pdf_path = render_report_pdf(case_id, run_label)
ui/backend/routes/comparison_report.py:150:    except ReportError as e:
ui/backend/schemas/audit_package.py:1:"""Pydantic schemas for Screen 6 audit-package builder
ui/backend/schemas/audit_package.py:45:    """Returned by POST /cases/{id}/runs/{rid}/audit-package/build."""
ui/backend/schemas/audit_package.py:51:    build_fingerprint: str = Field(
ui/backend/tests/test_comparison_report_route.py:29:    r = client.get("/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report")
ui/backend/tests/test_comparison_report_route.py:51:        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report/context",
ui/backend/tests/test_comparison_report_route.py:63:    r = client.get("/api/cases/nonexistent_case/runs/audit_real_run/comparison-report")
ui/backend/tests/test_comparison_report_route.py:68:    r = client.get("/api/cases/..__pwn/runs/audit_real_run/comparison-report")
ui/backend/tests/test_comparison_report_route.py:73:    r = client.get("/api/cases/lid_driven_cavity/runs/..__pwn/comparison-report")
ui/backend/tests/test_comparison_report_route.py:79:        "/api/cases/%2e%2e__pwn/runs/audit_real_run/comparison-report/context",
ui/backend/tests/test_comparison_report_route.py:150:    from ui.backend.services import comparison_report as svc
ui/backend/tests/test_comparison_report_route.py:163:        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report",
ui/backend/tests/test_comparison_report_route.py:175:        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report/context",
ui/backend/tests/test_comparison_report_route.py:185:    """Codex round 3: GET .../comparison-report.pdf must map OSError → 503."""
ui/backend/tests/test_comparison_report_route.py:186:    from ui.backend.routes import comparison_report as route_mod
ui/backend/tests/test_comparison_report_route.py:191:    monkeypatch.setattr(route_mod, "render_report_pdf", _raise_oserror)
ui/backend/tests/test_comparison_report_route.py:193:        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report.pdf",
ui/backend/tests/test_comparison_report_route.py:199:def test_pdf_build_post_returns_503_on_oserror(_synth_route_tree, monkeypatch) -> None:
ui/backend/tests/test_comparison_report_route.py:200:    """Codex round 3 MED follow-up: POST .../comparison-report/build must ALSO
ui/backend/tests/test_comparison_report_route.py:202:    from ui.backend.routes import comparison_report as route_mod
ui/backend/tests/test_comparison_report_route.py:207:    monkeypatch.setattr(route_mod, "render_report_pdf", _raise_oserror)
ui/backend/tests/test_comparison_report_route.py:209:        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report/build",
ui/backend/services/validation_report.py:1:"""Validation-report assembly — reads YAML, builds the Screen 4 payload.
ui/backend/services/validation_report.py:6:    - build_validation_report() → GET /api/validation-report/{id}
ui/backend/services/validation_report.py:553:        # Use the same default-run resolution as build_validation_report so
ui/backend/services/validation_report.py:636:def build_validation_report(
ui/backend/tests/test_comparison_report_visual_only.py:4:- build_report_context returns visual_only=True for VISUAL_ONLY_CASES
ui/backend/tests/test_comparison_report_visual_only.py:19:from ui.backend.services.comparison_report import (
ui/backend/tests/test_comparison_report_visual_only.py:21:    ReportError,
ui/backend/tests/test_comparison_report_visual_only.py:22:    build_report_context,
ui/backend/tests/test_comparison_report_visual_only.py:86:    """build_report_context returns visual_only=True with renders populated."""
ui/backend/tests/test_comparison_report_visual_only.py:90:        "ui.backend.services.comparison_report._FIELDS_ROOT",
ui/backend/tests/test_comparison_report_visual_only.py:94:        "ui.backend.services.comparison_report._RENDERS_ROOT",
ui/backend/tests/test_comparison_report_visual_only.py:98:        "ui.backend.services.comparison_report._REPO_ROOT", tmp_path,
ui/backend/tests/test_comparison_report_visual_only.py:101:    ctx = build_report_context(case, "audit_real_run")
ui/backend/tests/test_comparison_report_visual_only.py:117:        "/api/cases/totally_unknown_case/runs/audit_real_run/comparison-report/context",
ui/backend/tests/test_comparison_report_visual_only.py:133:        "ui.backend.services.comparison_report._FIELDS_ROOT",
ui/backend/tests/test_comparison_report_visual_only.py:156:        "ui.backend.services.comparison_report._FIELDS_ROOT",
ui/backend/tests/test_comparison_report_visual_only.py:160:    with pytest.raises(ReportError, match="invalid timestamp"):
ui/backend/tests/test_comparison_report_visual_only.py:161:        build_report_context(case, "audit_real_run")
ui/backend/tests/test_comparison_report_visual_only.py:164:def test_render_report_html_raises_for_visual_only(tmp_path, monkeypatch) -> None:
ui/backend/tests/test_comparison_report_visual_only.py:165:    """Codex round 1 CR (2026-04-21): render_report_html on a visual-only case
ui/backend/tests/test_comparison_report_visual_only.py:166:    must raise ReportError (→ 404), NOT 500 from template dereferencing
ui/backend/tests/test_comparison_report_visual_only.py:169:    from ui.backend.services.comparison_report import render_report_html
ui/backend/tests/test_comparison_report_visual_only.py:173:        "ui.backend.services.comparison_report._FIELDS_ROOT",
ui/backend/tests/test_comparison_report_visual_only.py:177:        "ui.backend.services.comparison_report._RENDERS_ROOT",
ui/backend/tests/test_comparison_report_visual_only.py:181:        "ui.backend.services.comparison_report._REPO_ROOT", tmp_path,
ui/backend/tests/test_comparison_report_visual_only.py:183:    with pytest.raises(ReportError, match="visual-only"):
ui/backend/tests/test_comparison_report_visual_only.py:184:        render_report_html(case, "audit_real_run")
ui/backend/tests/test_comparison_report_visual_only.py:187:def test_render_report_pdf_raises_for_visual_only(tmp_path, monkeypatch) -> None:
ui/backend/tests/test_comparison_report_visual_only.py:188:    """PDF path runs through render_report_html internally, so the same
ui/backend/tests/test_comparison_report_visual_only.py:189:    ReportError guard fires; nothing else downstream can crash."""
ui/backend/tests/test_comparison_report_visual_only.py:190:    from ui.backend.services.comparison_report import render_report_pdf
ui/backend/tests/test_comparison_report_visual_only.py:194:        "ui.backend.services.comparison_report._FIELDS_ROOT",
ui/backend/tests/test_comparison_report_visual_only.py:198:        "ui.backend.services.comparison_report._RENDERS_ROOT",
ui/backend/tests/test_comparison_report_visual_only.py:202:        "ui.backend.services.comparison_report._REPO_ROOT", tmp_path,
ui/backend/tests/test_comparison_report_visual_only.py:204:    with pytest.raises(ReportError, match="visual-only"):
ui/backend/tests/test_comparison_report_visual_only.py:205:        render_report_pdf(case, "audit_real_run")
ui/backend/tests/test_comparison_report_visual_only.py:209:    """End-to-end: GET /api/cases/BFS/runs/audit_real_run/comparison-report
ui/backend/tests/test_comparison_report_visual_only.py:210:    returns 404 (via ReportError) for visual-only case, NOT 500."""
ui/backend/tests/test_comparison_report_visual_only.py:212:        "/api/cases/backward_facing_step/runs/audit_real_run/comparison-report",
ui/backend/tests/test_comparison_report_visual_only.py:221:    from ui.backend.services.comparison_report import _GOLD_OVERLAY_CASES
ui/backend/routes/dashboard.py:17:from ui.backend.services.dashboard import build_dashboard
ui/backend/routes/dashboard.py:24:    snap = build_dashboard()
ui/backend/routes/case_export.py:8:query the live harness; they'll still need to build their own
ui/backend/routes/case_export.py:185:def build_reference_bundle(case_id: str) -> bytes:
ui/backend/routes/case_export.py:221:    data = build_reference_bundle(case_id)
ui/backend/tests/test_audit_package_phase7e.py:8:- Byte-reproducibility: two calls to build_manifest + serialize_zip with the
ui/backend/tests/test_audit_package_phase7e.py:24:    build_manifest,
ui/backend/tests/test_audit_package_phase7e.py:65:    (reports / timestamp / f"{run_id}_comparison_report.pdf").write_bytes(
ui/backend/tests/test_audit_package_phase7e.py:84:    assert "phase7/comparison_report.pdf" in zip_paths
ui/backend/tests/test_audit_package_phase7e.py:126:# ---------- Integration: build_manifest + serialize_zip ----------------------
ui/backend/tests/test_audit_package_phase7e.py:128:def test_build_manifest_embeds_phase7(tmp_path) -> None:
ui/backend/tests/test_audit_package_phase7e.py:130:    manifest = build_manifest(
ui/backend/tests/test_audit_package_phase7e.py:140:def test_build_manifest_opt_out_phase7(tmp_path) -> None:
ui/backend/tests/test_audit_package_phase7e.py:143:    manifest = build_manifest(
ui/backend/tests/test_audit_package_phase7e.py:156:    drift between build_manifest's repo_root and serialize's repo_root
ui/backend/tests/test_audit_package_phase7e.py:159:    manifest = build_manifest(
ui/backend/tests/test_audit_package_phase7e.py:172:        assert "phase7/comparison_report.pdf" in names
ui/backend/tests/test_audit_package_phase7e.py:177:            "— repo_root drift between build_manifest and serialize"
ui/backend/tests/test_audit_package_phase7e.py:180:        pdf_bytes = zf.read("phase7/comparison_report.pdf")
ui/backend/tests/test_audit_package_phase7e.py:183:                             "audit_real_run_comparison_report.pdf").read_bytes()
ui/backend/tests/test_audit_package_phase7e.py:188:    did pass it to build_manifest, phase7 entries fail containment and
ui/backend/tests/test_audit_package_phase7e.py:195:    manifest = build_manifest(
ui/backend/tests/test_audit_package_phase7e.py:212:    """Two consecutive build_manifest + serialize_zip_bytes calls with the
ui/backend/tests/test_audit_package_phase7e.py:215:    m1 = build_manifest(
ui/backend/tests/test_audit_package_phase7e.py:217:        build_fingerprint="deadbeefdeadbeef",
ui/backend/tests/test_audit_package_phase7e.py:220:    m2 = build_manifest(
ui/backend/tests/test_audit_package_phase7e.py:222:        build_fingerprint="deadbeefdeadbeef",
ui/backend/tests/test_comparison_report_service.py:1:"""Phase 7c — comparison_report service unit tests (CI-safe, no real artifacts).
ui/backend/tests/test_comparison_report_service.py:4:constants, exercises render_report_html + build_report_context + the Codex
ui/backend/tests/test_comparison_report_service.py:87:    from ui.backend.services import comparison_report as svc
ui/backend/tests/test_comparison_report_service.py:97:def test_build_context_happy_path(synthetic_tree) -> None:
ui/backend/tests/test_comparison_report_service.py:99:    ctx = svc.build_report_context("lid_driven_cavity", "audit_real_run")
ui/backend/tests/test_comparison_report_service.py:108:    html = svc.render_report_html("lid_driven_cavity", "audit_real_run")
ui/backend/tests/test_comparison_report_service.py:122:    with pytest.raises(svc.ReportError, match="invalid timestamp"):
ui/backend/tests/test_comparison_report_service.py:123:        svc.build_report_context("lid_driven_cavity", "audit_real_run")
ui/backend/tests/test_comparison_report_service.py:132:    with pytest.raises(svc.ReportError):
ui/backend/tests/test_comparison_report_service.py:133:        svc.build_report_context("lid_driven_cavity", "audit_real_run")
ui/backend/tests/test_comparison_report_service.py:155:    ctx = svc.build_report_context("lid_driven_cavity", "audit_real_run")
ui/backend/tests/test_comparison_report_service.py:170:    with pytest.raises(svc.ReportError, match="not an object"):
ui/backend/tests/test_comparison_report_service.py:171:        svc.build_report_context("lid_driven_cavity", "audit_real_run")
ui/backend/tests/test_comparison_report_service.py:179:    with pytest.raises(svc.ReportError, match="escapes reports_root"):
ui/backend/tests/test_comparison_report_service.py:180:        svc.render_report_pdf("lid_driven_cavity", "audit_real_run", output_path=evil)

exec
/bin/zsh -lc "sed -n '1,240p' ui/backend/routes/comparison_report.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '300,630p' ui/backend/services/comparison_report.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '1,260p' ui/backend/tests/test_comparison_report_visual_only.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
"""Phase 7c — CFD vs Gold comparison report route.

GET  /api/cases/{case_id}/runs/{run_label}/comparison-report         → HTML
GET  /api/cases/{case_id}/runs/{run_label}/comparison-report.pdf     → PDF
POST /api/cases/{case_id}/runs/{run_label}/comparison-report/build   → rebuild PDF + return manifest

Uses FileResponse pattern per Phase 7a user ratification #1 (no StaticFiles).
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from ui.backend.services.comparison_report import (
    ReportError,
    build_report_context,
    render_report_html,
    render_report_pdf,
)
from ui.backend.services.run_ids import _validate_segment

router = APIRouter()


def _validate_ids(case_id: str, run_label: str) -> None:
    """Reuse Phase 7a traversal defense on case_id + run_label segments."""
    _validate_segment(case_id, "case_id")
    _validate_segment(run_label, "run_label")


@router.get(
    "/cases/{case_id}/runs/{run_label}/comparison-report",
    response_class=HTMLResponse,
    tags=["comparison-report"],
)
def get_comparison_report_html(case_id: str, run_label: str) -> HTMLResponse:
    """Return rendered HTML report (suitable for iframe embedding)."""
    _validate_ids(case_id, run_label)
    try:
        html = render_report_html(case_id, run_label)
    except ReportError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return HTMLResponse(html)


@router.get(
    "/cases/{case_id}/runs/{run_label}/comparison-report/context",
    tags=["comparison-report"],
)
def get_comparison_report_context(case_id: str, run_label: str) -> JSONResponse:
    """Return the raw template context as JSON (for frontend custom rendering
    if it wants to skip the server-rendered HTML and compose its own)."""
    _validate_ids(case_id, run_label)
    try:
        ctx = build_report_context(case_id, run_label)
    except ReportError as e:
        raise HTTPException(status_code=404, detail=str(e))
    # Strip non-JSON-serializable entries (e.g., numpy arrays).
    # per_point_dev_pct is already list(); metrics keys are all primitives.
    return JSONResponse(ctx)


@router.get(
    "/cases/{case_id}/runs/{run_label}/comparison-report.pdf",
    tags=["comparison-report"],
)
def get_comparison_report_pdf(case_id: str, run_label: str) -> FileResponse:
    """Render (or re-render) PDF and stream it back."""
    _validate_ids(case_id, run_label)
    try:
        path = render_report_pdf(case_id, run_label)
    except ReportError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (ImportError, OSError) as e:
        # ImportError: weasyprint package missing.
        # OSError: native dep (libgobject / libcairo / libpango) failed to load
        # on this host — typically macOS missing DYLD_FALLBACK_LIBRARY_PATH.
        raise HTTPException(
            status_code=503,
            detail=(
                "WeasyPrint unavailable on this server. "
                "Ensure DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib is set and "
                "brew install pango cairo gdk-pixbuf has been run. "
                f"Underlying: {type(e).__name__}: {str(e)[:120]}"
            ),
        )
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"{case_id}__{run_label}__comparison_report.pdf",
    )


@router.get(
    "/cases/{case_id}/runs/{run_label}/renders/{filename:path}",
    tags=["comparison-report"],
)
def get_render_file(case_id: str, run_label: str, filename: str) -> FileResponse:
    """Serve a render PNG / Plotly JSON for a given case/run — used by the
    Tier C (DEC-V61-034) visual-only branch on the /learn page.

    Path traversal defense: re-resolve the composed path and verify it stays
    under ``reports/phase5_renders/{case_id}/`` — belt-and-suspenders on top of
    _validate_segment + the filename:path converter.
    """
    from ui.backend.services.comparison_report import _RENDERS_ROOT, _load_run_manifest, _validated_timestamp  # noqa: PLC0415

    _validate_ids(case_id, run_label)
    # Disallow obvious traversal in filename (the segment validator runs on
    # case_id/run_label only; filename comes through the :path converter).
    if ".." in filename.split("/") or filename.startswith("/") or "\\" in filename:
        raise HTTPException(status_code=404, detail="invalid filename")

    # Resolve the timestamped renders dir via the per-run manifest.
    try:
        run_manifest = _load_run_manifest(case_id, run_label)
    except ReportError as e:
        raise HTTPException(status_code=404, detail=str(e))
    ts = _validated_timestamp(run_manifest.get("timestamp"))
    if ts is None:
        raise HTTPException(status_code=404, detail="invalid run manifest timestamp")

    target = (_RENDERS_ROOT / case_id / ts / filename)
    try:
        resolved = target.resolve(strict=True)
        resolved.relative_to((_RENDERS_ROOT / case_id).resolve())
    except (ValueError, OSError, FileNotFoundError):
        raise HTTPException(status_code=404, detail="render not found")
    # MIME guess — only images/JSON expected here.
    media = "application/octet-stream"
    if filename.endswith(".png"):
        media = "image/png"
    elif filename.endswith(".json"):
        media = "application/json"
    return FileResponse(resolved, media_type=media, filename=resolved.name)


@router.post(
    "/cases/{case_id}/runs/{run_label}/comparison-report/build",
    tags=["comparison-report"],
)
def build_comparison_report(case_id: str, run_label: str) -> JSONResponse:
    """Force-rebuild HTML + PDF, return manifest."""
    _validate_ids(case_id, run_label)
    try:
        html = render_report_html(case_id, run_label)
        pdf_path = render_report_pdf(case_id, run_label)
    except ReportError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (ImportError, OSError) as e:
        # Codex round 3 MED follow-up: this POST path had only ImportError;
        # native libgobject/libcairo/libpango load failures surface as OSError
        # on macOS when DYLD_FALLBACK_LIBRARY_PATH is missing.
        raise HTTPException(
            status_code=503,
            detail=(
                "WeasyPrint unavailable on this server. "
                "Ensure DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib is set and "
                "brew install pango cairo gdk-pixbuf has been run. "
                f"Underlying: {type(e).__name__}: {str(e)[:120]}"
            ),
        )
    return JSONResponse({
        "case_id": case_id,
        "run_label": run_label,
        "pdf_path": str(pdf_path),
        "html_bytes": len(html),
    })

 succeeded in 0ms:
        "fine_n": gci.fine.n_cells_1d,
        "fine_value": gci.fine.value,
        "r_21": gci.r_21,
        "r_32": gci.r_32,
        "p_obs": gci.p_obs,
        "f_extrapolated": gci.f_extrapolated,
        "gci_21_pct": gci.gci_21 * 100 if gci.gci_21 is not None else None,
        "gci_32_pct": gci.gci_32 * 100 if gci.gci_32 is not None else None,
        "asymptotic_range_ok": gci.asymptotic_range_ok,
        "note": gci.note,
    }


def _get_commit_sha() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=_REPO_ROOT, timeout=5,
        )
        return r.stdout.strip() or "unknown"
    except (subprocess.SubprocessError, OSError):
        return "unknown"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _build_visual_only_context(
    case_id: str, run_label: str, timestamp: str, artifact_dir: Path,
) -> dict:
    """Tier C reduced context (DEC-V61-034): real contour + residuals PNGs from
    the captured OpenFOAM artifacts, no gold overlay / verdict / GCI. The
    frontend + template detect ``visual_only: True`` and suppress the
    gold-dependent sections.
    """
    renders_manifest = _load_renders_manifest(case_id, run_label)
    renders_dir = _RENDERS_ROOT / case_id / timestamp

    def _rel(key: str, default: str = "") -> str:
        candidate: Optional[str] = None
        if renders_manifest:
            raw = renders_manifest.get("outputs", {}).get(key)
            if isinstance(raw, str):
                validated = _safe_rel_under(raw, _RENDERS_ROOT)
                if validated:
                    candidate = validated
        if candidate is None and default:
            guess = renders_dir / default
            if guess.is_file():
                try:
                    rel = str(guess.resolve().relative_to(_REPO_ROOT.resolve()))
                    if _safe_rel_under(rel, _RENDERS_ROOT):
                        candidate = rel
                except ValueError:
                    pass
        return candidate or ""

    renders = {
        "contour_png_rel": _rel("contour_u_magnitude_png", "contour_u_magnitude.png"),
        "residuals_png_rel": _rel("residuals_png", "residuals.png"),
    }

    # Detect solver name from which log.<solver> file exists in artifact dir.
    solver = "unknown"
    for cand in ("simpleFoam", "icoFoam", "pimpleFoam", "buoyantFoam"):
        if (artifact_dir / f"log.{cand}").is_file():
            solver = cand
            break
    commit_sha = _get_commit_sha()

    return {
        "visual_only": True,
        "case_id": case_id,
        "run_label": run_label,
        "timestamp": timestamp,
        "renders": renders,
        "solver": solver,
        "commit_sha": commit_sha,
        "verdict": None,
        "verdict_gradient": "#64748b 0%, #94a3b8 100%",
        "subtitle": (
            "Visual-only mode (DEC-V61-034 Tier C): real OpenFOAM field + "
            "residual evidence captured; per-case gold-overlay plumbing pending "
            "Phase 7c Sprint 2 (Tier B)."
        ),
        "paper": None,
        "metrics": None,
        "gci": None,
        "grid_convergence": None,
        "deviations": None,
        "residual_info": None,
        "tolerance_percent": None,
    }


def build_report_context(case_id: str, run_label: str = "audit_real_run") -> dict:
    """Assemble all template variables. Raises ReportError on missing data."""
    if case_id not in _REPORT_SUPPORTED_CASES:
        raise ReportError(
            f"case_id={case_id!r} not in Phase 7 report scope. "
            f"Supported: {sorted(_REPORT_SUPPORTED_CASES)}."
        )

    run_manifest = _load_run_manifest(case_id, run_label)
    timestamp = _validated_timestamp(run_manifest.get("timestamp"))
    if timestamp is None:
        raise ReportError(
            f"invalid timestamp in run manifest for {case_id}/{run_label}"
        )
    artifact_dir = _FIELDS_ROOT / case_id / timestamp
    # Containment: must be inside _FIELDS_ROOT/case_id/ even after .resolve().
    try:
        artifact_dir.resolve(strict=True).relative_to(
            (_FIELDS_ROOT / case_id).resolve()
        )
    except (ValueError, OSError, FileNotFoundError):
        raise ReportError(f"artifact dir escapes fields root: {artifact_dir}")
    if not artifact_dir.is_dir():
        raise ReportError(f"artifact dir missing: {artifact_dir}")

    # Tier C: visual-only cases skip gold-overlay / verdict / GCI assembly.
    if case_id in _VISUAL_ONLY_CASES:
        return _build_visual_only_context(case_id, run_label, timestamp, artifact_dir)

    # Load + compute
    gold_y, gold_u, gold_doc = _load_ldc_gold()
    tolerance = float(gold_doc.get("tolerance", 0.05)) * 100.0  # fraction → percent
    latest_sample = _latest_sample_iter(artifact_dir)
    y_sim, u_sim = _load_sample_xy(latest_sample / "uCenterline.xy")
    metrics = _compute_metrics(y_sim, u_sim, gold_y, gold_u, tolerance)

    residual_info = _parse_residuals_csv(artifact_dir / "residuals.csv")
    grid_conv_rows, grid_note = _load_grid_convergence(case_id, gold_y, gold_u)
    # Phase 7d: Richardson extrapolation + GCI over the finest 3 meshes.
    try:
        from ui.backend.services.grid_convergence import compute_gci_from_fixtures
        gci = compute_gci_from_fixtures(case_id, fixture_root=_FIXTURE_ROOT)
    except (ValueError, ImportError, OverflowError, ArithmeticError):
        # Pathological mesh triples can still raise from deep math — the
        # grid_convergence module already catches these internally on the
        # documented branches, but belt-and-suspenders keeps report
        # generation from 500'ing on a numerical corner we did not predict.
        gci = None

    # Verdict logic: all-pass OR tolerance met.
    is_all_pass = metrics["n_pass"] == metrics["n_total"] and metrics["n_total"] > 0
    majority_pass = metrics["n_pass"] >= math.ceil(metrics["n_total"] * 0.6)
    if is_all_pass:
        verdict, verdict_gradient, subtitle = "PASS", "#059669 0%, #10b981 100%", (
            f"全部 {metrics['n_total']} 个 gold 点在 ±{tolerance:.1f}% 容差内。"
        )
    elif majority_pass:
        verdict, verdict_gradient, subtitle = "PARTIAL", "#d97706 0%, #f59e0b 100%", (
            f"{metrics['n_pass']}/{metrics['n_total']} 点通过；"
            f"{metrics['n_total'] - metrics['n_pass']} 点残差为已记录物理项 "
            f"(见 DEC-V61-030 关于 Ghia 非均匀网格 vs 均匀网格的插值误差)。"
        )
    else:
        verdict, verdict_gradient, subtitle = "FAIL", "#dc2626 0%, #ef4444 100%", (
            f"仅 {metrics['n_pass']}/{metrics['n_total']} 点通过 — "
            f"需要诊断 (solver, mesh, 或 gold 本身)。"
        )

    # Renders — use Phase 7b manifest if available; else None placeholders.
    # Codex round 1 HIGH: every manifest-supplied output path is validated to
    # resolve inside reports/phase5_renders/ before being emitted into HTML.
    renders_manifest = _load_renders_manifest(case_id, run_label)
    renders_dir = _RENDERS_ROOT / case_id / timestamp

    def _rel(key: str, default: str = "") -> str:
        candidate: Optional[str] = None
        if renders_manifest:
            raw = renders_manifest.get("outputs", {}).get(key)
            if isinstance(raw, str):
                validated = _safe_rel_under(raw, _RENDERS_ROOT)
                if validated:
                    candidate = validated
        if candidate is None:
            guess = renders_dir / default
            if guess.is_file():
                try:
                    rel = str(guess.resolve().relative_to(_REPO_ROOT.resolve()))
                    if _safe_rel_under(rel, _RENDERS_ROOT):
                        candidate = rel
                except ValueError:
                    pass
        return candidate or ""

    renders = {
        "profile_png_rel": _rel("profile_png", "profile_u_centerline.png"),
        "pointwise_png_rel": _rel("pointwise_deviation_png", "pointwise_deviation.png"),
        "contour_png_rel": _rel("contour_u_magnitude_png", "contour_u_magnitude.png"),
        "residuals_png_rel": _rel("residuals_png", "residuals.png"),
    }

    paper = {
        "title": gold_doc.get("source", "Ghia, Ghia & Shin 1982 — Lid-Driven Cavity benchmark"),
        "source": "J. Comput. Phys. 47, 387-411 (1982), Table I Re=100 column",
        "doi": gold_doc.get("literature_doi", "10.1016/0021-9991(82)90058-4"),
        "short": "Ghia 1982",
        "gold_count": metrics["n_total"],
        "tolerance_pct": tolerance,
    }

    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")

    return {
        "case_id": case_id,
        "case_display_name": "Lid-Driven Cavity (Re=100)" if case_id == "lid_driven_cavity" else case_id,
        "run_label": run_label,
        "timestamp": timestamp,
        "verdict": verdict,
        "verdict_gradient": verdict_gradient,
        "verdict_subtitle": subtitle,
        "metrics": metrics,
        "paper": paper,
        "renders": renders,
        "contour_caption": (
            "2D |U| contour + streamlines 由 OpenFOAM VTK 体数据渲染（Phase 7b polish）。"
            "白色流线显示 LDC Re=100 的主涡结构；黄色高 |U| 区沿 lid 剪切层分布。"
        ),
        "residual_info": residual_info,
        "grid_conv": grid_conv_rows,
        "grid_conv_note": grid_note,
        "gci": _gci_to_template_dict(gci) if gci is not None else None,
        "meta": {
            "openfoam_version": "v10",
            "solver": "simpleFoam (SIMPLE, laminar)",
            "docker_image": "cfd-openfoam (local arm64 OpenFOAM v10)",
            "commit_sha": _get_commit_sha(),
            "mesh": "129×129 uniform",
            "tolerance": f"±{tolerance:.1f}%",
            "schemes": "steadyState + linearUpwind + Gauss linear corrected",
            "report_generated_at": now,
        },
    }


def render_report_html(case_id: str, run_label: str = "audit_real_run") -> str:
    """Return the full HTML string for the comparison report.

    Visual-only cases (DEC-V61-034 Tier C) have no gold-overlay data to render
    in the 8-section template — they expose their renders (contour + residuals
    PNG) via the JSON context + /renders/ route instead. Requesting the HTML
    report for a visual-only case raises ReportError which the route layer
    maps to 404 (Codex round 1 CR finding: prevents template UndefinedError
    500 on dereferencing `metrics.max_dev_pct` / `paper.title`).
    """
    ctx = build_report_context(case_id, run_label)
    if ctx.get("visual_only"):
        raise ReportError(
            f"case_id={case_id!r} is in Tier C visual-only mode — no 8-section "
            f"HTML/PDF report is produced. Use the JSON context at "
            f"/api/cases/{case_id}/runs/{run_label}/comparison-report/context "
            f"plus /api/cases/{case_id}/runs/{run_label}/renders/{{filename}} "
            f"to retrieve the contour + residuals renders directly."
        )
    tmpl = _env.get_template("comparison_report.html.j2")
    return tmpl.render(**ctx)


def render_report_pdf(case_id: str, run_label: str = "audit_real_run",
                      output_path: Optional[Path] = None) -> Path:
    """Render HTML to PDF via WeasyPrint and write to disk. Returns the file Path.

    Asset resolution: WeasyPrint converts the HTML's relative img src paths.
    We pass base_url=_REPO_ROOT so /reports/phase5_renders/... resolves correctly.

    Codex round 2 (2026-04-21): containment check runs BEFORE weasyprint import
    so ReportError from a malicious output_path is raised regardless of whether
    native libs are installed. Native load failures (libgobject etc.) surface
    as OSError and are mapped by the route layer to 503, same as ImportError.
    """
    # Codex round 1 HIGH: ensure PDF always lands under reports/phase5_reports/.
    # Codex round 2 MED: run containment FIRST, before WeasyPrint import so we
    # fail-closed on traversal even on systems where WeasyPrint native libs are
    # unavailable.
    reports_root = (_REPO_ROOT / "reports" / "phase5_reports").resolve()
    if output_path is None:
        ctx = build_report_context(case_id, run_label)
        # Codex round 1 CR (DEC-V61-034): visual-only cases have no PDF to
        # render. Raise BEFORE weasyprint import so environments without
        # native libs also fail-closed with ReportError → 404 at the route,
        # not OSError → 503.
        if ctx.get("visual_only"):
            raise ReportError(
                f"case_id={case_id!r} is in Tier C visual-only mode — no PDF "
                f"report is produced. Use the /renders/{{filename}} route for "
                f"contour + residuals PNG retrieval."
            )
        ts = ctx["timestamp"]  # already validated by build_report_context
        out_dir = reports_root / case_id / ts
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / f"{run_label}_comparison_report.pdf"
    try:
        resolved_out = output_path.resolve(strict=False)
        # Must stay inside reports/phase5_reports/
        resolved_out.relative_to(reports_root)
    except (ValueError, OSError):
        raise ReportError(f"PDF output path escapes reports_root: {output_path}")

    # Import weasyprint lazily — heavy import, only when PDF actually needed.
    import weasyprint  # type: ignore  # ImportError → 503 via route layer.

    html = render_report_html(case_id, run_label)
    doc = weasyprint.HTML(string=html, base_url=str(_REPO_ROOT))
    doc.write_pdf(str(resolved_out))
    return resolved_out

 succeeded in 0ms:
"""Phase 7c Tier C (DEC-V61-034) — visual-only context + render-serving route tests.

Guards:
- build_report_context returns visual_only=True for VISUAL_ONLY_CASES
- Render route serves PNG with path-containment defense
- Traversal attempts in render filename are rejected (404)
- Missing case / run_label produces 404 (not 500)
- Tampered run-manifest timestamp is rejected (404)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ui.backend.main import app
from ui.backend.services.comparison_report import (
    _VISUAL_ONLY_CASES,
    ReportError,
    build_report_context,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _plant_run_manifest(
    repo_root: Path, case_id: str, timestamp: str = "20260101T000000Z",
) -> Path:
    """Write a minimal Phase 7a runs/{label}.json + corresponding renders
    manifest + both PNGs into reports/phase5_{fields,renders}/{case}/.
    """
    fields_dir = repo_root / "reports" / "phase5_fields" / case_id
    renders_dir = repo_root / "reports" / "phase5_renders" / case_id
    artifact_dir = fields_dir / timestamp
    render_ts_dir = renders_dir / timestamp
    artifact_dir.mkdir(parents=True, exist_ok=True)
    render_ts_dir.mkdir(parents=True, exist_ok=True)
    (fields_dir / "runs").mkdir(parents=True, exist_ok=True)
    (fields_dir / "runs" / "audit_real_run.json").write_text(
        json.dumps({
            "run_label": "audit_real_run",
            "timestamp": timestamp,
            "case_id": case_id,
            "artifact_dir_rel": str(artifact_dir.relative_to(repo_root)),
        }),
        encoding="utf-8",
    )
    (artifact_dir / "log.simpleFoam").write_text("Time = 1s\n", encoding="utf-8")
    (render_ts_dir / "contour_u_magnitude.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
    (render_ts_dir / "residuals.png").write_bytes(b"\x89PNG\r\n\x1a\nfake2")
    (renders_dir / "runs").mkdir(parents=True, exist_ok=True)
    (renders_dir / "runs" / "audit_real_run.json").write_text(
        json.dumps({
            "run_label": "audit_real_run",
            "timestamp": timestamp,
            "case_id": case_id,
            "outputs": {
                "contour_u_magnitude_png":
                    f"reports/phase5_renders/{case_id}/{timestamp}/contour_u_magnitude.png",
                "residuals_png":
                    f"reports/phase5_renders/{case_id}/{timestamp}/residuals.png",
            },
        }),
        encoding="utf-8",
    )
    return artifact_dir


def test_visual_only_cases_are_nine() -> None:
    """VISUAL_ONLY_CASES covers all 9 non-LDC whitelist cases per DEC-V61-034."""
    assert "lid_driven_cavity" not in _VISUAL_ONLY_CASES
    expected = {
        "backward_facing_step", "plane_channel_flow", "turbulent_flat_plate",
        "circular_cylinder_wake", "impinging_jet", "naca0012_airfoil",
        "rayleigh_benard_convection", "differential_heated_cavity", "duct_flow",
    }
    assert _VISUAL_ONLY_CASES == expected


def test_visual_only_context_shape(tmp_path, monkeypatch) -> None:
    """build_report_context returns visual_only=True with renders populated."""
    case = "backward_facing_step"
    _plant_run_manifest(tmp_path, case)
    monkeypatch.setattr(
        "ui.backend.services.comparison_report._FIELDS_ROOT",
        tmp_path / "reports" / "phase5_fields",
    )
    monkeypatch.setattr(
        "ui.backend.services.comparison_report._RENDERS_ROOT",
        tmp_path / "reports" / "phase5_renders",
    )
    monkeypatch.setattr(
        "ui.backend.services.comparison_report._REPO_ROOT", tmp_path,
    )

    ctx = build_report_context(case, "audit_real_run")
    assert ctx["visual_only"] is True
    assert ctx["case_id"] == case
    assert ctx["run_label"] == "audit_real_run"
    assert ctx["verdict"] is None
    assert ctx["metrics"] is None
    assert ctx["paper"] is None
    assert ctx["renders"]["contour_png_rel"].endswith("contour_u_magnitude.png")
    assert ctx["renders"]["residuals_png_rel"].endswith("residuals.png")
    assert ctx["solver"] == "simpleFoam"
    assert "visual-only" in ctx["subtitle"].lower()


def test_unknown_case_404(client) -> None:
    """Unsupported case → 404, not 500."""
    resp = client.get(
        "/api/cases/totally_unknown_case/runs/audit_real_run/comparison-report/context",
    )
    assert resp.status_code == 404


def test_render_route_traversal_rejected(client) -> None:
    """../../secret in render filename is rejected as 404 (traversal defense)."""
    resp = client.get(
        "/api/cases/backward_facing_step/runs/audit_real_run/renders/..%2F..%2F..%2Fetc%2Fpasswd",
    )
    assert resp.status_code == 404


def test_render_route_missing_run_manifest_404(client, tmp_path, monkeypatch) -> None:
    """Case id in supported set but no run manifest → 404 (no 500)."""
    monkeypatch.setattr(
        "ui.backend.services.comparison_report._FIELDS_ROOT",
        tmp_path / "reports" / "phase5_fields",
    )
    resp = client.get(
        "/api/cases/duct_flow/runs/nonexistent_run/renders/contour_u_magnitude.png",
    )
    assert resp.status_code == 404


def test_visual_only_context_rejects_tampered_timestamp(tmp_path, monkeypatch) -> None:
    """Run manifest with timestamp='../../etc' is rejected by _validated_timestamp."""
    case = "plane_channel_flow"
    fields_dir = tmp_path / "reports" / "phase5_fields" / case
    (fields_dir / "runs").mkdir(parents=True)
    (fields_dir / "runs" / "audit_real_run.json").write_text(
        json.dumps({
            "run_label": "audit_real_run",
            "timestamp": "../../../etc/passwd",  # malicious
            "case_id": case,
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "ui.backend.services.comparison_report._FIELDS_ROOT",
        tmp_path / "reports" / "phase5_fields",
    )

    with pytest.raises(ReportError, match="invalid timestamp"):
        build_report_context(case, "audit_real_run")


def test_render_report_html_raises_for_visual_only(tmp_path, monkeypatch) -> None:
    """Codex round 1 CR (2026-04-21): render_report_html on a visual-only case
    must raise ReportError (→ 404), NOT 500 from template dereferencing
    None metrics/paper fields.
    """
    from ui.backend.services.comparison_report import render_report_html
    case = "backward_facing_step"
    _plant_run_manifest(tmp_path, case)
    monkeypatch.setattr(
        "ui.backend.services.comparison_report._FIELDS_ROOT",
        tmp_path / "reports" / "phase5_fields",
    )
    monkeypatch.setattr(
        "ui.backend.services.comparison_report._RENDERS_ROOT",
        tmp_path / "reports" / "phase5_renders",
    )
    monkeypatch.setattr(
        "ui.backend.services.comparison_report._REPO_ROOT", tmp_path,
    )
    with pytest.raises(ReportError, match="visual-only"):
        render_report_html(case, "audit_real_run")


def test_render_report_pdf_raises_for_visual_only(tmp_path, monkeypatch) -> None:
    """PDF path runs through render_report_html internally, so the same
    ReportError guard fires; nothing else downstream can crash."""
    from ui.backend.services.comparison_report import render_report_pdf
    case = "plane_channel_flow"
    _plant_run_manifest(tmp_path, case)
    monkeypatch.setattr(
        "ui.backend.services.comparison_report._FIELDS_ROOT",
        tmp_path / "reports" / "phase5_fields",
    )
    monkeypatch.setattr(
        "ui.backend.services.comparison_report._RENDERS_ROOT",
        tmp_path / "reports" / "phase5_renders",
    )
    monkeypatch.setattr(
        "ui.backend.services.comparison_report._REPO_ROOT", tmp_path,
    )
    with pytest.raises(ReportError, match="visual-only"):
        render_report_pdf(case, "audit_real_run")


def test_route_html_returns_404_for_visual_only(client) -> None:
    """End-to-end: GET /api/cases/BFS/runs/audit_real_run/comparison-report
    returns 404 (via ReportError) for visual-only case, NOT 500."""
    resp = client.get(
        "/api/cases/backward_facing_step/runs/audit_real_run/comparison-report",
    )
    assert resp.status_code == 404, f"expected 404, got {resp.status_code}: {resp.text[:200]}"


def test_gold_overlay_case_not_affected_by_visual_only_branch(tmp_path, monkeypatch) -> None:
    """LDC does NOT take the visual_only branch — existing gold-overlay flow
    preserved. This test ensures the dispatch check is case-set membership,
    not a global flag."""
    from ui.backend.services.comparison_report import _GOLD_OVERLAY_CASES
    assert "lid_driven_cavity" in _GOLD_OVERLAY_CASES
    for c in _VISUAL_ONLY_CASES:
        assert c not in _GOLD_OVERLAY_CASES

exec
/bin/zsh -lc "sed -n '160,225p' ui/backend/tests/test_comparison_report_route.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
def test_html_200_end_to_end_synthetic(_synth_route_tree) -> None:
    """CI-safe: route → service → template with monkeypatched roots."""
    r = client.get(
        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report",
    )
    assert r.status_code == 200, r.text
    # Verify all 8 sections rendered.
    for marker in ["参考文献", "中心线 profile", "逐点偏差分布",
                   "流场 contour", "残差收敛历史", "网格收敛",
                   "求解器元数据"]:
        assert marker in r.text, marker


def test_context_json_end_to_end_synthetic(_synth_route_tree) -> None:
    r = client.get(
        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report/context",
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["case_id"] == "lid_driven_cavity"
    assert d["timestamp"] == "20260421T000000Z"
    assert d["metrics"]["n_total"] == 3


def test_pdf_get_returns_503_on_oserror(_synth_route_tree, monkeypatch) -> None:
    """Codex round 3: GET .../comparison-report.pdf must map OSError → 503."""
    from ui.backend.routes import comparison_report as route_mod

    def _raise_oserror(*a, **kw):
        raise OSError("libpango missing (synthetic)")

    monkeypatch.setattr(route_mod, "render_report_pdf", _raise_oserror)
    r = client.get(
        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report.pdf",
    )
    assert r.status_code == 503, r.text
    assert "WeasyPrint unavailable" in r.json().get("detail", "")


def test_pdf_build_post_returns_503_on_oserror(_synth_route_tree, monkeypatch) -> None:
    """Codex round 3 MED follow-up: POST .../comparison-report/build must ALSO
    map OSError → 503. Previously it returned 500 on native lib load failure."""
    from ui.backend.routes import comparison_report as route_mod

    def _raise_oserror(*a, **kw):
        raise OSError("libpango missing (synthetic)")

    monkeypatch.setattr(route_mod, "render_report_pdf", _raise_oserror)
    r = client.post(
        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report/build",
    )
    assert r.status_code == 503, r.text
    assert "WeasyPrint unavailable" in r.json().get("detail", "")

codex
The route-level behavior matches the intended cascade so far: HTML catches `ReportError`, PDF catches `ReportError` before the WeasyPrint branch for normal route calls, and POST reaches `render_report_html` first. One mismatch I’m checking now is the service-level `output_path` path, because the current code only builds context before import when `output_path is None`.
exec
/bin/zsh -lc 'PYTHONPATH=. .venv/bin/pytest ui/backend/tests/test_comparison_report_visual_only.py ui/backend/tests/test_comparison_report_route.py -q' in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "PYTHONPATH=. .venv/bin/python - <<'PY'
from pathlib import Path
from fastapi.testclient import TestClient
from ui.backend.main import app

client = TestClient(app)
for method, url in [
    ('GET', '/api/cases/backward_facing_step/runs/audit_real_run/comparison-report'),
    ('GET', '/api/cases/backward_facing_step/runs/audit_real_run/comparison-report.pdf'),
    ('POST', '/api/cases/backward_facing_step/runs/audit_real_run/comparison-report/build'),
]:
    resp = getattr(client, method.lower())(url)
    print(method, url, resp.status_code, resp.text[:160].replace('\\n', ' '))
PY" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 341ms:
GET /api/cases/backward_facing_step/runs/audit_real_run/comparison-report 404 {"detail":"case_id='backward_facing_step' is in Tier C visual-only mode — no 8-section HTML/PDF report is produced. Use the JSON context at /api/cases/backward_
GET /api/cases/backward_facing_step/runs/audit_real_run/comparison-report.pdf 404 {"detail":"case_id='backward_facing_step' is in Tier C visual-only mode — no PDF report is produced. Use the /renders/{filename} route for contour + residuals P
POST /api/cases/backward_facing_step/runs/audit_real_run/comparison-report/build 404 {"detail":"case_id='backward_facing_step' is in Tier C visual-only mode — no 8-section HTML/PDF report is produced. Use the JSON context at /api/cases/backward_

 succeeded in 691ms:
============================= test session starts ==============================
platform darwin -- Python 3.12.13, pytest-9.0.3, pluggy-1.6.0
rootdir: /Users/Zhuanz/Desktop/cfd-harness-unified
configfile: pyproject.toml
plugins: mock-3.15.1, cov-7.1.0, anyio-4.13.0
collected 20 items

ui/backend/tests/test_comparison_report_visual_only.py ..........        [ 50%]
ui/backend/tests/test_comparison_report_route.py ..........              [100%]

============================== 20 passed in 0.48s ==============================

codex
Targeted comparison-report tests are green: 20 passed, and live TestClient probes return 404 for all three visual-only endpoints. I’m running the full backend test directory once to make the approval evidence match the reported regression scope.
exec
/bin/zsh -lc 'PYTHONPATH=. .venv/bin/pytest ui/backend/tests/ -q' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 25077ms:
============================= test session starts ==============================
platform darwin -- Python 3.12.13, pytest-9.0.3, pluggy-1.6.0
rootdir: /Users/Zhuanz/Desktop/cfd-harness-unified
configfile: pyproject.toml
plugins: mock-3.15.1, cov-7.1.0, anyio-4.13.0
collected 142 items

ui/backend/tests/test_audit_package_phase7e.py .........                 [  6%]
ui/backend/tests/test_audit_package_route.py ....................        [ 20%]
ui/backend/tests/test_case_editor.py ......                              [ 24%]
ui/backend/tests/test_case_export.py .............                       [ 33%]
ui/backend/tests/test_comparison_report_route.py ..........              [ 40%]
ui/backend/tests/test_comparison_report_service.py .......               [ 45%]
ui/backend/tests/test_comparison_report_visual_only.py ..........        [ 52%]
ui/backend/tests/test_decisions_and_dashboard.py ........                [ 58%]
ui/backend/tests/test_field_artifacts_route.py ..................        [ 71%]
ui/backend/tests/test_grid_convergence_gci.py .........                  [ 77%]
ui/backend/tests/test_grid_convergence_monotonicity.py ..........        [ 84%]
ui/backend/tests/test_health.py .                                        [ 85%]
ui/backend/tests/test_phase5_byte_repro.py ............                  [ 93%]
ui/backend/tests/test_validation_report.py .........                     [100%]

============================= 142 passed in 24.84s =============================

exec
/bin/zsh -lc "PYTHONPATH=. .venv/bin/python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from ui.backend.services import comparison_report as svc
from ui.backend.tests.test_comparison_report_visual_only import _plant_run_manifest

with TemporaryDirectory() as d:
    root = Path(d)
    _plant_run_manifest(root, 'backward_facing_step')
    old_repo, old_fields, old_renders = svc._REPO_ROOT, svc._FIELDS_ROOT, svc._RENDERS_ROOT
    try:
        svc._REPO_ROOT = root
        svc._FIELDS_ROOT = root / 'reports' / 'phase5_fields'
        svc._RENDERS_ROOT = root / 'reports' / 'phase5_renders'
        for label, out in [
            ('outside', root / 'tmp' / 'out.pdf'),
            ('inside', root / 'reports' / 'phase5_reports' / 'backward_facing_step' / '20260101T000000Z' / 'out.pdf'),
        ]:
            try:
                svc.render_report_pdf('backward_facing_step', 'audit_real_run', output_path=out)
            except Exception as e:
                print(label, type(e).__name__, str(e)[:140])
    finally:
        svc._REPO_ROOT, svc._FIELDS_ROOT, svc._RENDERS_ROOT = old_repo, old_fields, old_renders
PY" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 363ms:
outside ReportError PDF output path escapes reports_root: /var/folders/q4/859yhpgn6x3fx6kv4mj5gmv40000gp/T/tmpgogxar3_/tmp/out.pdf

-----

WeasyPrint could not import some external libraries. Please carefully follow the installation steps before reporting an issue:
https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation
https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#troubleshooting 

-----

inside OSError cannot load library 'libgobject-2.0-0': dlopen(libgobject-2.0-0, 0x0002): tried: 'libgobject-2.0-0' (no such file), '/System/Volumes/Preboot

exec
/bin/zsh -lc "nl -ba ui/backend/services/comparison_report.py | sed -n '540,610p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba ui/backend/routes/comparison_report.py | sed -n '34,160p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   540	def render_report_html(case_id: str, run_label: str = "audit_real_run") -> str:
   541	    """Return the full HTML string for the comparison report.
   542	
   543	    Visual-only cases (DEC-V61-034 Tier C) have no gold-overlay data to render
   544	    in the 8-section template — they expose their renders (contour + residuals
   545	    PNG) via the JSON context + /renders/ route instead. Requesting the HTML
   546	    report for a visual-only case raises ReportError which the route layer
   547	    maps to 404 (Codex round 1 CR finding: prevents template UndefinedError
   548	    500 on dereferencing `metrics.max_dev_pct` / `paper.title`).
   549	    """
   550	    ctx = build_report_context(case_id, run_label)
   551	    if ctx.get("visual_only"):
   552	        raise ReportError(
   553	            f"case_id={case_id!r} is in Tier C visual-only mode — no 8-section "
   554	            f"HTML/PDF report is produced. Use the JSON context at "
   555	            f"/api/cases/{case_id}/runs/{run_label}/comparison-report/context "
   556	            f"plus /api/cases/{case_id}/runs/{run_label}/renders/{{filename}} "
   557	            f"to retrieve the contour + residuals renders directly."
   558	        )
   559	    tmpl = _env.get_template("comparison_report.html.j2")
   560	    return tmpl.render(**ctx)
   561	
   562	
   563	def render_report_pdf(case_id: str, run_label: str = "audit_real_run",
   564	                      output_path: Optional[Path] = None) -> Path:
   565	    """Render HTML to PDF via WeasyPrint and write to disk. Returns the file Path.
   566	
   567	    Asset resolution: WeasyPrint converts the HTML's relative img src paths.
   568	    We pass base_url=_REPO_ROOT so /reports/phase5_renders/... resolves correctly.
   569	
   570	    Codex round 2 (2026-04-21): containment check runs BEFORE weasyprint import
   571	    so ReportError from a malicious output_path is raised regardless of whether
   572	    native libs are installed. Native load failures (libgobject etc.) surface
   573	    as OSError and are mapped by the route layer to 503, same as ImportError.
   574	    """
   575	    # Codex round 1 HIGH: ensure PDF always lands under reports/phase5_reports/.
   576	    # Codex round 2 MED: run containment FIRST, before WeasyPrint import so we
   577	    # fail-closed on traversal even on systems where WeasyPrint native libs are
   578	    # unavailable.
   579	    reports_root = (_REPO_ROOT / "reports" / "phase5_reports").resolve()
   580	    if output_path is None:
   581	        ctx = build_report_context(case_id, run_label)
   582	        # Codex round 1 CR (DEC-V61-034): visual-only cases have no PDF to
   583	        # render. Raise BEFORE weasyprint import so environments without
   584	        # native libs also fail-closed with ReportError → 404 at the route,
   585	        # not OSError → 503.
   586	        if ctx.get("visual_only"):
   587	            raise ReportError(
   588	                f"case_id={case_id!r} is in Tier C visual-only mode — no PDF "
   589	                f"report is produced. Use the /renders/{{filename}} route for "
   590	                f"contour + residuals PNG retrieval."
   591	            )
   592	        ts = ctx["timestamp"]  # already validated by build_report_context
   593	        out_dir = reports_root / case_id / ts
   594	        out_dir.mkdir(parents=True, exist_ok=True)
   595	        output_path = out_dir / f"{run_label}_comparison_report.pdf"
   596	    try:
   597	        resolved_out = output_path.resolve(strict=False)
   598	        # Must stay inside reports/phase5_reports/
   599	        resolved_out.relative_to(reports_root)
   600	    except (ValueError, OSError):
   601	        raise ReportError(f"PDF output path escapes reports_root: {output_path}")
   602	
   603	    # Import weasyprint lazily — heavy import, only when PDF actually needed.
   604	    import weasyprint  # type: ignore  # ImportError → 503 via route layer.
   605	
   606	    html = render_report_html(case_id, run_label)
   607	    doc = weasyprint.HTML(string=html, base_url=str(_REPO_ROOT))
   608	    doc.write_pdf(str(resolved_out))
   609	    return resolved_out

 succeeded in 0ms:
    34	    "/cases/{case_id}/runs/{run_label}/comparison-report",
    35	    response_class=HTMLResponse,
    36	    tags=["comparison-report"],
    37	)
    38	def get_comparison_report_html(case_id: str, run_label: str) -> HTMLResponse:
    39	    """Return rendered HTML report (suitable for iframe embedding)."""
    40	    _validate_ids(case_id, run_label)
    41	    try:
    42	        html = render_report_html(case_id, run_label)
    43	    except ReportError as e:
    44	        raise HTTPException(status_code=404, detail=str(e))
    45	    return HTMLResponse(html)
    46	
    47	
    48	@router.get(
    49	    "/cases/{case_id}/runs/{run_label}/comparison-report/context",
    50	    tags=["comparison-report"],
    51	)
    52	def get_comparison_report_context(case_id: str, run_label: str) -> JSONResponse:
    53	    """Return the raw template context as JSON (for frontend custom rendering
    54	    if it wants to skip the server-rendered HTML and compose its own)."""
    55	    _validate_ids(case_id, run_label)
    56	    try:
    57	        ctx = build_report_context(case_id, run_label)
    58	    except ReportError as e:
    59	        raise HTTPException(status_code=404, detail=str(e))
    60	    # Strip non-JSON-serializable entries (e.g., numpy arrays).
    61	    # per_point_dev_pct is already list(); metrics keys are all primitives.
    62	    return JSONResponse(ctx)
    63	
    64	
    65	@router.get(
    66	    "/cases/{case_id}/runs/{run_label}/comparison-report.pdf",
    67	    tags=["comparison-report"],
    68	)
    69	def get_comparison_report_pdf(case_id: str, run_label: str) -> FileResponse:
    70	    """Render (or re-render) PDF and stream it back."""
    71	    _validate_ids(case_id, run_label)
    72	    try:
    73	        path = render_report_pdf(case_id, run_label)
    74	    except ReportError as e:
    75	        raise HTTPException(status_code=404, detail=str(e))
    76	    except (ImportError, OSError) as e:
    77	        # ImportError: weasyprint package missing.
    78	        # OSError: native dep (libgobject / libcairo / libpango) failed to load
    79	        # on this host — typically macOS missing DYLD_FALLBACK_LIBRARY_PATH.
    80	        raise HTTPException(
    81	            status_code=503,
    82	            detail=(
    83	                "WeasyPrint unavailable on this server. "
    84	                "Ensure DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib is set and "
    85	                "brew install pango cairo gdk-pixbuf has been run. "
    86	                f"Underlying: {type(e).__name__}: {str(e)[:120]}"
    87	            ),
    88	        )
    89	    return FileResponse(
    90	        path,
    91	        media_type="application/pdf",
    92	        filename=f"{case_id}__{run_label}__comparison_report.pdf",
    93	    )
    94	
    95	
    96	@router.get(
    97	    "/cases/{case_id}/runs/{run_label}/renders/{filename:path}",
    98	    tags=["comparison-report"],
    99	)
   100	def get_render_file(case_id: str, run_label: str, filename: str) -> FileResponse:
   101	    """Serve a render PNG / Plotly JSON for a given case/run — used by the
   102	    Tier C (DEC-V61-034) visual-only branch on the /learn page.
   103	
   104	    Path traversal defense: re-resolve the composed path and verify it stays
   105	    under ``reports/phase5_renders/{case_id}/`` — belt-and-suspenders on top of
   106	    _validate_segment + the filename:path converter.
   107	    """
   108	    from ui.backend.services.comparison_report import _RENDERS_ROOT, _load_run_manifest, _validated_timestamp  # noqa: PLC0415
   109	
   110	    _validate_ids(case_id, run_label)
   111	    # Disallow obvious traversal in filename (the segment validator runs on
   112	    # case_id/run_label only; filename comes through the :path converter).
   113	    if ".." in filename.split("/") or filename.startswith("/") or "\\" in filename:
   114	        raise HTTPException(status_code=404, detail="invalid filename")
   115	
   116	    # Resolve the timestamped renders dir via the per-run manifest.
   117	    try:
   118	        run_manifest = _load_run_manifest(case_id, run_label)
   119	    except ReportError as e:
   120	        raise HTTPException(status_code=404, detail=str(e))
   121	    ts = _validated_timestamp(run_manifest.get("timestamp"))
   122	    if ts is None:
   123	        raise HTTPException(status_code=404, detail="invalid run manifest timestamp")
   124	
   125	    target = (_RENDERS_ROOT / case_id / ts / filename)
   126	    try:
   127	        resolved = target.resolve(strict=True)
   128	        resolved.relative_to((_RENDERS_ROOT / case_id).resolve())
   129	    except (ValueError, OSError, FileNotFoundError):
   130	        raise HTTPException(status_code=404, detail="render not found")
   131	    # MIME guess — only images/JSON expected here.
   132	    media = "application/octet-stream"
   133	    if filename.endswith(".png"):
   134	        media = "image/png"
   135	    elif filename.endswith(".json"):
   136	        media = "application/json"
   137	    return FileResponse(resolved, media_type=media, filename=resolved.name)
   138	
   139	
   140	@router.post(
   141	    "/cases/{case_id}/runs/{run_label}/comparison-report/build",
   142	    tags=["comparison-report"],
   143	)
   144	def build_comparison_report(case_id: str, run_label: str) -> JSONResponse:
   145	    """Force-rebuild HTML + PDF, return manifest."""
   146	    _validate_ids(case_id, run_label)
   147	    try:
   148	        html = render_report_html(case_id, run_label)
   149	        pdf_path = render_report_pdf(case_id, run_label)
   150	    except ReportError as e:
   151	        raise HTTPException(status_code=404, detail=str(e))
   152	    except (ImportError, OSError) as e:
   153	        # Codex round 3 MED follow-up: this POST path had only ImportError;
   154	        # native libgobject/libcairo/libpango load failures surface as OSError
   155	        # on macOS when DYLD_FALLBACK_LIBRARY_PATH is missing.
   156	        raise HTTPException(
   157	            status_code=503,
   158	            detail=(
   159	                "WeasyPrint unavailable on this server. "
   160	                "Ensure DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib is set and "

exec
/bin/zsh -lc "nl -ba ui/backend/tests/test_comparison_report_visual_only.py | sed -n '164,215p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   164	def test_render_report_html_raises_for_visual_only(tmp_path, monkeypatch) -> None:
   165	    """Codex round 1 CR (2026-04-21): render_report_html on a visual-only case
   166	    must raise ReportError (→ 404), NOT 500 from template dereferencing
   167	    None metrics/paper fields.
   168	    """
   169	    from ui.backend.services.comparison_report import render_report_html
   170	    case = "backward_facing_step"
   171	    _plant_run_manifest(tmp_path, case)
   172	    monkeypatch.setattr(
   173	        "ui.backend.services.comparison_report._FIELDS_ROOT",
   174	        tmp_path / "reports" / "phase5_fields",
   175	    )
   176	    monkeypatch.setattr(
   177	        "ui.backend.services.comparison_report._RENDERS_ROOT",
   178	        tmp_path / "reports" / "phase5_renders",
   179	    )
   180	    monkeypatch.setattr(
   181	        "ui.backend.services.comparison_report._REPO_ROOT", tmp_path,
   182	    )
   183	    with pytest.raises(ReportError, match="visual-only"):
   184	        render_report_html(case, "audit_real_run")
   185	
   186	
   187	def test_render_report_pdf_raises_for_visual_only(tmp_path, monkeypatch) -> None:
   188	    """PDF path runs through render_report_html internally, so the same
   189	    ReportError guard fires; nothing else downstream can crash."""
   190	    from ui.backend.services.comparison_report import render_report_pdf
   191	    case = "plane_channel_flow"
   192	    _plant_run_manifest(tmp_path, case)
   193	    monkeypatch.setattr(
   194	        "ui.backend.services.comparison_report._FIELDS_ROOT",
   195	        tmp_path / "reports" / "phase5_fields",
   196	    )
   197	    monkeypatch.setattr(
   198	        "ui.backend.services.comparison_report._RENDERS_ROOT",
   199	        tmp_path / "reports" / "phase5_renders",
   200	    )
   201	    monkeypatch.setattr(
   202	        "ui.backend.services.comparison_report._REPO_ROOT", tmp_path,
   203	    )
   204	    with pytest.raises(ReportError, match="visual-only"):
   205	        render_report_pdf(case, "audit_real_run")
   206	
   207	
   208	def test_route_html_returns_404_for_visual_only(client) -> None:
   209	    """End-to-end: GET /api/cases/BFS/runs/audit_real_run/comparison-report
   210	    returns 404 (via ReportError) for visual-only case, NOT 500."""
   211	    resp = client.get(
   212	        "/api/cases/backward_facing_step/runs/audit_real_run/comparison-report",
   213	    )
   214	    assert resp.status_code == 404, f"expected 404, got {resp.status_code}: {resp.text[:200]}"
   215	

exec
/bin/zsh -lc "nl -ba /Users/Zhuanz/.codex/memories/MEMORY.md | sed -n '400,416p;744,752p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   400	
   401	# Task Group: cfd-harness-unified governance closeout and planning gates
   402	
   403	scope: Close out accepted phases in `cfd-harness-unified`, normalize Notion-vs-repo naming drift, and keep future phases planning-only until the explicit solver/routing gate is reviewed.
   404	applies_to: cwd=/Users/Zhuanz/Desktop/cfd-harness-unified; reuse_rule=safe for this repo’s Notion-governed phase/gate work, but phase/task IDs and review packets are rollout-specific.
   405	
   406	## Task 1: Close Phase 8 and reconcile stale governance evidence
   407	
   408	### rollout_summary_files
   409	
   410	- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, Phase 8 closeout and evidence normalization)
   411	
   412	### keywords
   413	
   414	- Phase 8, AutoVerifier, 13/13, knowledge/whitelist.yaml, ai_cfd_cold_start_whitelist.yaml, Canonical Docs Type=Report, Phase 8 Done, naming drift
   415	
   416	## Task 2: Open Phase 9 as planning-only and keep solver expansion bounded
   744	
   745	- the user asked: "用Notion作为我的开发中枢，避免我一直复制每个会话的提示词" -> default toward a reusable Notion-first operating model instead of prompt-copy-heavy sessions [Task 1][Task 2]
   746	- the user repeatedly required isolation: "在不干涉这两个notion项目的前提下" -> keep sibling Notion projects separate unless they explicitly ask for shared databases/relations [Task 1]
   747	- the user asked to integrate GSD and make it "完全自动化的开发，除了需要暂停下来让我定期手动触发Opus 4.6审查" -> automate by default but preserve hard manual review pauses [Task 2]
   748	- for freeze-signoff governance review, the user required a strict independent review with no writes to freeze artifacts -> treat this as review-only until the user explicitly changes scope [Task 3]
   749	- when the user said "你是 independent approval authority… 你不是 corrected request packet 作者… 你不是 Phase 8 executor" -> preserve strict role separation between approval, review, execution, and freeze authority in this repo [Task 4]
   750	- when the user said "如果 approval granted，只能创建一个 executable approval YAML 和一个 approval action report" and "不得运行 populate-formal" -> approval sessions should only produce the allowed artifacts and must not spill into execution [Task 4]
   751	- when the request-package input said the executor "must not write manual intake state" and "must not be valid input to any CLI command" -> default manual-review-intake packaging work to markdown-only, non-mutating deliverables [Task 5]
   752	- when the user said acceptance "must not equal freeze approval" and "cannot directly enter final freeze signoff" -> always restate that `accepted_for_review` is not `freeze-complete`, even when readiness evidence looks strong [Task 3][Task 4]

codex
APPROVED_WITH_COMMENTS

No blocking findings for the route regression at `6581167`. The three reviewed endpoints now return 404 for visual-only BFS in live TestClient probes, and `PYTHONPATH=. .venv/bin/pytest ui/backend/tests/ -q` passes: `142 passed in 24.84s`.

One non-blocking correction: the packet’s `render_report_pdf` ordering is slightly broader than the code. The pre-WeasyPrint visual-only guard only runs when `output_path is None` in [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:580). Direct service calls with a caller-supplied `output_path` inside `reports/phase5_reports` still import WeasyPrint before `render_report_html` raises. This does not affect the three route endpoints, since they never pass `output_path`.

Route fix is acceptable as-is. To make the service invariant match the review packet exactly, move `ctx = build_report_context(...)` and the visual-only guard above the `if output_path is None` branch.


tokens used
124,439
APPROVED_WITH_COMMENTS

No blocking findings for the route regression at `6581167`. The three reviewed endpoints now return 404 for visual-only BFS in live TestClient probes, and `PYTHONPATH=. .venv/bin/pytest ui/backend/tests/ -q` passes: `142 passed in 24.84s`.

One non-blocking correction: the packet’s `render_report_pdf` ordering is slightly broader than the code. The pre-WeasyPrint visual-only guard only runs when `output_path is None` in [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:580). Direct service calls with a caller-supplied `output_path` inside `reports/phase5_reports` still import WeasyPrint before `render_report_html` raises. This does not affect the three route endpoints, since they never pass `output_path`.

Route fix is acceptable as-is. To make the service invariant match the review packet exactly, move `ctx = build_report_context(...)` and the visual-only guard above the `if output_path is None` branch.


