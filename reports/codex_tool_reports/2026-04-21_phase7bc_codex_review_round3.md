2026-04-21T09:43:50.065373Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-research-deerflow/SKILL.md: missing YAML frontmatter delimited by ---
2026-04-21T09:43:50.065393Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-report-pretext/SKILL.md: missing YAML frontmatter delimited by ---
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
session id: 019daf6c-b432-7940-a722-65c154fd66f0
--------
user
Phase 7b+7c+7f round 3 verification.

Round 2 MED + LOW follow-ups applied:
- MED: render_report_pdf containment now runs BEFORE import weasyprint. PDF output_path validated against resolved reports_root = _REPO_ROOT/reports/phase5_reports/; raises ReportError if escape detected, regardless of WeasyPrint availability.
- MED: route layer now catches BOTH ImportError AND OSError → 503 with detailed message naming DYLD_FALLBACK_LIBRARY_PATH + brew deps. Applies to both /comparison-report.pdf GET and /comparison-report/build POST.
- LOW: added 2 CI-safe route-level synthetic-tree tests in test_comparison_report_route.py — _synth_route_tree fixture monkeypatches service module globals (_REPO_ROOT, _FIELDS_ROOT, _RENDERS_ROOT, _GOLD_ROOT, _FIXTURE_ROOT) so route integration (TestClient → route → service → template) exercises 200 path without needing real OpenFOAM artifacts. test_html_200_end_to_end_synthetic asserts all 8 section markers in response. test_context_json_end_to_end_synthetic asserts JSON context has expected shape.

Verification: PYTHONPATH=. .venv/bin/pytest ui/backend/tests/ -q → 112/112 passed (was 110/110; +2 synthetic route tests). test_pdf_output_path_contained still passes because containment is now pre-WeasyPrint.

Please confirm round-1 findings are now fully closed:
- HIGH (path containment) — closed round 1
- MED (silent error swallow) — closed round 1 (frontend)
- MED-round2 (containment-before-import + OSError→503) — closed round 2
- LOW (CI-safe route success tests) — closed round 2

Reply APPROVED / APPROVED_WITH_COMMENTS / CHANGES_REQUIRED.
codex
Reviewing the round-2 follow-ups as an independent verification pass. I’m checking the relevant service, route, and test files first, then I’ll run the targeted verification needed to confirm whether the round-1 findings are actually closed.
exec
/bin/zsh -lc 'rg -n "cfd-harness-unified|Phase 7|comparison_report|weasyprint|DYLD_FALLBACK_LIBRARY_PATH|test_comparison_report_route|pdf_output_path_contained|comparison-report" /Users/Zhuanz/.codex/memories/MEMORY.md' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
115:- OpenClaw, AI-CFD, Notion作为指挥中枢，Github作为唯一代码真相库, ~/.openclaw/openclaw.json, plugins.allow, openclaw config validate --json, MAIN_OK, CODEX_BUILDER_OK, CLAUDE_REVIEW_OK, NOTION_SYNC_OK, cfd-harness-unified
135:- The real live config surface was `~/.openclaw/openclaw.json`; the actual repo truth for this rollout was `/Users/Zhuanz/Desktop/cfd-harness-unified`, not the chat thread cwd [Task 1]
356:# Task Group: cfd-harness-unified governance closeout and planning gates
358:scope: Close out accepted phases in `cfd-harness-unified`, normalize Notion-vs-repo naming drift, and keep future phases planning-only until the explicit solver/routing gate is reviewed.
359:applies_to: cwd=/Users/Zhuanz/Desktop/cfd-harness-unified; reuse_rule=safe for this repo’s Notion-governed phase/gate work, but phase/task IDs and review packets are rollout-specific.
365:- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, Phase 8 closeout and evidence normalization)
375:- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, Phase 9 kept as planning-only with decision-tree packet))
385:- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, handoff prompt prepared instead of silent activation))
439:- rollout_summaries/2026-04-12T15-33-54-ByPi-jerry_ai_cfd_notion_sync_and_cfd_harness_unified_context_mis.md (cwd=/Users/Zhuanz/Documents/20260330 Jerry AI CFD Project, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/12/rollout-2026-04-12T23-33-54-019d8253-fa8b-7f40-9775-46e6e03db8ac.jsonl, updated_at=2026-04-16T17:03:18+00:00, thread_id=019d8253-fa8b-7f40-9775-46e6e03db8ac, later cfd-harness-unified instruction block correctly treated as mismatch)
808:## Task 1: Build Phase 7.1 Protocol + factory + fallback on the real repo contract
882:- `Phase6_PLAN.md` is the authoritative design anchor for the repo’s Phase 7 solver path and the sequence `7.1 Protocol + Factory`, `7.1b case generator`, `7.2 OpenFOAMDockerExecutor`, `7.3 SU2DockerExecutor` [Task 1][Task 2]

exec
/bin/zsh -lc 'pwd && git status --short && rg --files | rg "comparison_report|test_comparison_report_route|comparison-report|report"' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
/Users/Zhuanz/Desktop/cfd-harness-unified
 M reports/cylinder_crossflow/report.md
 M reports/deep_acceptance/visual_acceptance_report.html
 M reports/deep_acceptance/visual_acceptance_report_manifest.json
 M reports/differential_heated_cavity/report.md
 M reports/rayleigh_benard_convection/report.md
 M reports/turbulent_flat_plate/report.md
 M ui/backend/main.py
 M ui/frontend/public/flow-fields/circular_cylinder_wake/strouhal_curve.png
 M ui/frontend/public/flow-fields/lid_driven_cavity/centerline_profiles.png
 M ui/frontend/public/flow-fields/lid_driven_cavity/stream_function.png
 M ui/frontend/public/flow-fields/plane_channel_flow/wall_profile.png
 M ui/frontend/public/flow-fields/rayleigh_benard_convection/nu_ra_scaling.png
 M ui/frontend/public/flow-fields/turbulent_flat_plate/blasius_profile.png
 M ui/frontend/public/flow-fields/turbulent_flat_plate/cf_comparison.png
 M ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx
?? .claude/
?? .gitignore.patch.stale.1776663560182166739
?? knowledge/corrections/
?? reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md
?? reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md
?? reports/codex_tool_reports/2026-04-21_phase7bc_render_report_codex_review.md
?? reports/deep_acceptance/20260421_000138_visual_acceptance_package.md
?? reports/deep_acceptance/20260421_000139_visual_acceptance_package.md
?? reports/deep_acceptance/20260421_000231_visual_acceptance_package.md
?? reports/deep_acceptance/20260421_000232_visual_acceptance_package.md
?? reports/deep_acceptance/visual_acceptance_report_20260421_000138.html
?? reports/deep_acceptance/visual_acceptance_report_20260421_000139.html
?? reports/deep_acceptance/visual_acceptance_report_20260421_000231.html
?? reports/deep_acceptance/visual_acceptance_report_20260421_000232.html
?? reports/phase5_audit/20260421T081929Z_lid_driven_cavity_raw.json
?? reports/phase5_audit/20260421T082305Z_lid_driven_cavity_raw.json
?? reports/phase5_audit/20260421T082408Z_lid_driven_cavity_raw.json
?? reports/phase5_fields/
?? reports/phase5_renders/
?? reports/phase5_reports/
?? scripts/render_case_report.py
?? ui/backend/routes/comparison_report.py
?? ui/backend/services/comparison_report.py
?? ui/backend/templates/
?? ui/backend/tests/test_comparison_report_route.py
?? ui/backend/tests/test_comparison_report_service.py
?? ui/frontend/vite.config.sandbox.ts.stale.1776667726
?? ui/frontend/vite.config.sandbox.ts.timestamp-1776667276256-33cd5f0862292.mjs
src/report_engine/contract_dashboard.py
src/report_engine/schemas.py
src/report_engine/generator.py
src/report_engine/__init__.py
src/report_engine/visual_acceptance.py
src/report_engine/data_collector.py
reports/lid_driven_cavity_benchmark/auto_verify_report.yaml
reports/lid_driven_cavity_benchmark/report.md
reports/lid_driven_cavity_benchmark/case_completion_report.md
reports/axisymmetric_impinging_jet/auto_verify_report.yaml
reports/axisymmetric_impinging_jet/report.md
reports/ex1_004_passing_cases_physics_contract/slice_metrics.yaml
reports/phase5_audit/20260421T061902Z_lid_driven_cavity_raw.json
reports/phase5_audit/20260421T082408Z_lid_driven_cavity_raw.json
reports/phase5_audit/20260421T032048Z_turbulent_flat_plate_raw.json
reports/phase5_audit/20260421T034718Z_naca0012_airfoil_raw.json
reports/phase5_audit/20260421T031945Z_lid_driven_cavity_raw.json
reports/phase5_audit/20260421T055344Z_lid_driven_cavity_raw.json
reports/phase5_audit/20260421T032016Z_circular_cylinder_wake_raw.json
reports/phase5_audit/20260421T041243Z_rayleigh_benard_convection_raw.json
reports/phase5_audit/20260421T063445Z_lid_driven_cavity_raw.json
reports/phase5_audit/20260421T031952Z_backward_facing_step_raw.json
reports/phase5_audit/20260421T034439Z_plane_channel_flow_raw.json
reports/phase5_audit/20260421T043230Z_lid_driven_cavity_raw.json
reports/phase5_audit/20260421T032120Z_duct_flow_raw.json
reports/phase5_audit/20260421T063729Z_lid_driven_cavity_raw.json
reports/phase5_audit/20260421T031919Z_lid_driven_cavity_raw.json
reports/phase5_audit/20260421T060128Z_lid_driven_cavity_raw.json
reports/phase5_audit/20260421T043525Z_lid_driven_cavity_raw.json
reports/phase5_audit/20260421T082305Z_lid_driven_cavity_raw.json
reports/phase5_audit/20260421T043849Z_lid_driven_cavity_raw.json
reports/phase5_audit/20260421T033741Z_differential_heated_cavity_raw.json
reports/phase5_audit/20260421T054449Z_lid_driven_cavity_raw.json
reports/phase5_audit/20260421T055039Z_lid_driven_cavity_raw.json
reports/phase5_audit/20260421T034702Z_impinging_jet_raw.json
reports/phase5_audit/20260421T081929Z_lid_driven_cavity_raw.json
reports/ex1_g3_cylinder_restructure/fix_plan_packet.md
reports/cylinder_crossflow/auto_verify_report.yaml
reports/cylinder_crossflow/report.md
reports/cylinder_crossflow/case_completion_report.md
reports/differential_heated_cavity/report.html
reports/differential_heated_cavity/figures/02_mesh.svg
reports/differential_heated_cavity/figures/_render.py
reports/differential_heated_cavity/figures/03_residuals.svg
reports/differential_heated_cavity/figures/05_nu_ra_scaling.svg
reports/differential_heated_cavity/figures/01_geometry.svg
reports/differential_heated_cavity/figures/04_nu_timeline.svg
reports/differential_heated_cavity/auto_verify_report.yaml
reports/differential_heated_cavity/report.md
reports/baselines/phase9_model_routing_replay_manifest.yaml
reports/baselines/SY-1_deterministic_replay_capture.md
reports/ex1_003_gold_standard_physics_contract/slice_metrics.yaml
reports/deep_acceptance/contract_status_dashboard_manifest.json
reports/deep_acceptance/visual_acceptance_report_20260421_000232.html
reports/deep_acceptance/contract_status_dashboard.html
reports/deep_acceptance/assets/backward_facing_step_steady_cad.png
reports/deep_acceptance/assets/cylinder_crossflow_cfd.png
reports/deep_acceptance/assets/naca0012_airfoil_cad.png
reports/deep_acceptance/assets/differential_heated_cavity_benchmark.png
reports/deep_acceptance/assets/naca0012_airfoil_cfd.png
reports/deep_acceptance/assets/lid_driven_cavity_benchmark_benchmark.png
reports/deep_acceptance/assets/cylinder_crossflow_cad.png
reports/deep_acceptance/assets/cylinder_crossflow_benchmark.png
reports/deep_acceptance/assets/backward_facing_step_steady_cfd.png
reports/deep_acceptance/assets/naca0012_airfoil_benchmark.png
reports/deep_acceptance/assets/lid_driven_cavity_benchmark_cad.png
reports/deep_acceptance/assets/differential_heated_cavity_cad.png
reports/deep_acceptance/assets/backward_facing_step_steady_benchmark.png
reports/deep_acceptance/assets/lid_driven_cavity_benchmark_cfd.png
reports/deep_acceptance/assets/differential_heated_cavity_cfd.png
reports/deep_acceptance/visual_acceptance_report.html
reports/deep_acceptance/2026-04-18_adwm_session_acceptance_packet.md
reports/deep_acceptance/20260421_000139_visual_acceptance_package.md
reports/deep_acceptance/contract_status_dashboard_20260420_013835.html
reports/deep_acceptance/visual_acceptance_report_manifest.json
reports/deep_acceptance/2026-04-18_contract_status_dashboard.md
reports/deep_acceptance/20260421_000138_visual_acceptance_package.md
reports/deep_acceptance/20260421_000232_visual_acceptance_package.md
reports/deep_acceptance/visual_acceptance_report_20260420_011828.html
reports/deep_acceptance/20260420_011828_visual_acceptance_package.md
reports/deep_acceptance/visual_acceptance_report_20260421_000139.html
reports/deep_acceptance/visual_acceptance_report_20260421_000138.html
reports/deep_acceptance/20260421_000231_visual_acceptance_package.md
reports/deep_acceptance/visual_acceptance_report_20260421_000231.html
reports/naca0012_airfoil/diagnostic_v1.md
reports/naca0012_airfoil/fix_plan_packet.md
reports/naca0012_airfoil/auto_verify_report.yaml
reports/naca0012_airfoil/wave3_closeout_v2.md
reports/naca0012_airfoil/report.md
reports/naca0012_airfoil/artifacts/checkmesh_postfix.log
reports/naca0012_airfoil/artifacts/cp_postproc_audit.md
reports/naca0012_airfoil/artifacts/fvSchemes.copy
reports/naca0012_airfoil/artifacts/checkmesh.log
reports/naca0012_airfoil/artifacts/fvSolution.copy
reports/naca0012_airfoil/artifacts/omega_init_audit.md
reports/naca0012_airfoil/artifacts/checkmesh_pathH.log
reports/naca0012_airfoil/artifacts/yplus_postfix.csv
reports/naca0012_airfoil/artifacts/yplus_profile.csv
reports/naca0012_airfoil/artifacts/fv_recent_changes.md
reports/ex1_006_attributor_audit_concern/slice_metrics.yaml
reports/ex1_002_cli_tests/slice_metrics.yaml
reports/post_phase5_acceptance/2026-04-21_part2_raw_results.json
reports/post_phase5_acceptance/2026-04-21_ui_infra_validation.md
reports/post_phase5_acceptance/2026-04-21_part2_solver_runs.md
reports/ex1_008_dhc_mean_nu/fix_plan_packet.md
reports/turbulent_flat_plate/auto_verify_report.yaml
reports/turbulent_flat_plate/report.md
reports/backward_facing_step_steady/auto_verify_report.yaml
reports/backward_facing_step_steady/report.md
reports/backward_facing_step_steady/case_completion_report.md
reports/rayleigh_benard_convection/auto_verify_report.yaml
reports/rayleigh_benard_convection/report.md
scripts/generate_visual_acceptance_report.py
scripts/render_case_report.py
scripts/generate_reports.py
reports/sy1_variance_slices/variance_summary.md
reports/sy1_variance_slices/sy1_002_bfs_sync_payload.yaml
reports/sy1_variance_slices/sy1_003_cylinder_sync_payload.yaml
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md
reports/codex_tool_reports/2026-04-21_pr5c2_m3_review.md
reports/codex_tool_reports/2026-04-21_pr22_duct_dispatch_review.md
reports/codex_tool_reports/2026-04-21_pr20_foam_adapter_review.md
reports/codex_tool_reports/2026-04-21_pr23_build_fingerprint_review.md
reports/codex_tool_reports/2026-04-21_pr5d1_closure_review.md
reports/codex_tool_reports/2026-04-21_phase7bc_render_report_codex_review.md
reports/codex_tool_reports/2026-04-21_pr21_bfs_guard_review.md
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md
reports/codex_tool_reports/2026-04-21_pr5c1_codex_followup_review.md
reports/codex_tool_reports/2026-04-21_pr5c_hmac_review.md
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md
reports/codex_tool_reports/README.md
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md
reports/codex_tool_reports/2026-04-21_pr5d_screen6_review.md
reports/phase5_reports/lid_driven_cavity/20260421T082340Z/audit_real_run_comparison_report.pdf
reports/ex1_first_slice/diagnostic_memo.md
reports/ex1_first_slice/slice_metrics.yaml
reports/ex1_009_spalding_fallback_audit/fix_plan_packet.md
reports/ex1_009_spalding_fallback_audit/slice_metrics.yaml
reports/phase5_fields/lid_driven_cavity/runs/audit_real_run.json
reports/ex1_010_cylinder_canonical_band_audit/fix_plan_packet.md
reports/ex1_010_cylinder_canonical_band_audit/slice_metrics.yaml
templates/case_report.md.j2
reports/phase5_renders/lid_driven_cavity/20260421T082340Z/contour_u_magnitude.png
reports/phase5_renders/lid_driven_cavity/20260421T082340Z/profile_u_centerline.plotly.json
reports/phase5_renders/lid_driven_cavity/20260421T082340Z/residuals.png
reports/phase5_renders/lid_driven_cavity/20260421T082340Z/pointwise_deviation.png
reports/phase5_renders/lid_driven_cavity/20260421T082340Z/profile_u_centerline.png
reports/ex1_007_dhc_mesh_refinement/blockmesh_smoke_check.md
reports/ex1_007_dhc_mesh_refinement/run_dhc_blockmesh_check.py
reports/ex1_007_dhc_mesh_refinement/measurement_result.yaml
reports/ex1_007_dhc_mesh_refinement/consumer_side_mini_review.md
reports/ex1_007_dhc_mesh_refinement/slice_metrics.yaml
reports/ex1_007_dhc_mesh_refinement/run_dhc_measurement.py
reports/fully_developed_plane_channel_flow/auto_verify_report.yaml
reports/fully_developed_plane_channel_flow/report.md
reports/ex1_005_whitelist_coverage_and_mini_review/methodology_mini_review.md
reports/ex1_005_whitelist_coverage_and_mini_review/slice_metrics.yaml
ui/backend/tests/test_comparison_report_route.py
ui/backend/tests/test_validation_report.py
reports/phase5_renders/lid_driven_cavity/runs/audit_real_run.json
ui/backend/tests/test_comparison_report_service.py
ui/backend/templates/comparison_report.html.j2
ui/backend/services/validation_report.py
ui/backend/services/comparison_report.py
tests/test_report_engine/test_generate_reports_cli.py
tests/test_report_engine/conftest.py
tests/test_report_engine/__init__.py
ui/backend/routes/comparison_report.py
tests/test_report_engine/test_visual_acceptance_report.py
tests/test_report_engine/test_report_engine.py
tests/test_report_engine/test_contract_dashboard_report.py

codex
I’ve confirmed this is the right repo and there are unrelated dirty/untracked files in the worktree, so I’m treating this as a read-only review pass. Next I’m reading the current comparison-report implementation and the prior review notes to verify that the fixes match the actual failure modes, not just the stated intent.
exec
/bin/zsh -lc "nl -ba ui/backend/services/comparison_report.py | sed -n '1,260p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
     1	"""Phase 7c — CFD vs Gold comparison report service.
     2	
     3	Renders an 8-section HTML report for a given (case_id, run_label), using:
     4	- Phase 7a field artifacts at reports/phase5_fields/{case}/{ts}/
     5	- Phase 7b rendered figures at reports/phase5_renders/{case}/{ts}/
     6	- knowledge/gold_standards/{case}.yaml gold reference
     7	- ui/backend/tests/fixtures/runs/{case}/mesh_{20,40,80,160}_measurement.yaml for grid convergence
     8	
     9	Backend route: ui/backend/routes/comparison_report.py calls `render_report_html`
    10	and `render_report_pdf` from this module. No DOM / no JS — static HTML + PNG
    11	inlined assets referenced by file:// for WeasyPrint PDF, served via FileResponse
    12	or embedded iframe on frontend.
    13	
    14	Design: report_html is a self-contained string (no asset URLs pointing to
    15	/api/... — uses file:// for PDF rendering and relative paths for HTML serving).
    16	"""
    17	from __future__ import annotations
    18	
    19	import datetime
    20	import json
    21	import math
    22	import re
    23	import subprocess
    24	from pathlib import Path
    25	from typing import Any, Optional
    26	
    27	import numpy as np
    28	import yaml
    29	from jinja2 import Environment, FileSystemLoader, select_autoescape
    30	
    31	# Codex round 1 HIGH (2026-04-21): strict shape gate on manifest-supplied
    32	# timestamp and artifact paths. Mirrors ui/backend/services/field_artifacts.py
    33	# defense-in-depth pattern so tampered runs/{label}.json cannot steer reads
    34	# outside reports/phase5_fields/ or writes outside reports/phase5_reports/.
    35	_TIMESTAMP_RE = re.compile(r"^\d{8}T\d{6}Z$")
    36	
    37	_MODULE_DIR = Path(__file__).resolve().parent
    38	_REPO_ROOT = _MODULE_DIR.parents[2]
    39	_TEMPLATES = _MODULE_DIR.parent / "templates"
    40	_FIELDS_ROOT = _REPO_ROOT / "reports" / "phase5_fields"
    41	_RENDERS_ROOT = _REPO_ROOT / "reports" / "phase5_renders"
    42	_GOLD_ROOT = _REPO_ROOT / "knowledge" / "gold_standards"
    43	_FIXTURE_ROOT = _REPO_ROOT / "ui" / "backend" / "tests" / "fixtures" / "runs"
    44	
    45	_REPORT_SUPPORTED_CASES = frozenset({"lid_driven_cavity"})
    46	
    47	_env = Environment(
    48	    loader=FileSystemLoader(str(_TEMPLATES)),
    49	    autoescape=select_autoescape(["html", "htm"]),
    50	)
    51	
    52	
    53	class ReportError(Exception):
    54	    """Recoverable — caller should 404 or return partial payload."""
    55	
    56	
    57	# ---------------------------------------------------------------------------
    58	# Data assembly
    59	# ---------------------------------------------------------------------------
    60	
    61	
    62	def _run_manifest_path(case_id: str, run_label: str) -> Path:
    63	    return _FIELDS_ROOT / case_id / "runs" / f"{run_label}.json"
    64	
    65	
    66	def _renders_manifest_path(case_id: str, run_label: str) -> Path:
    67	    return _RENDERS_ROOT / case_id / "runs" / f"{run_label}.json"
    68	
    69	
    70	def _load_run_manifest(case_id: str, run_label: str) -> dict:
    71	    p = _run_manifest_path(case_id, run_label)
    72	    if not p.is_file():
    73	        raise ReportError(f"no run manifest for {case_id}/{run_label}")
    74	    data = json.loads(p.read_text(encoding="utf-8"))
    75	    if not isinstance(data, dict):
    76	        raise ReportError(f"run manifest not an object: {p}")
    77	    return data
    78	
    79	
    80	def _load_renders_manifest(case_id: str, run_label: str) -> Optional[dict]:
    81	    p = _renders_manifest_path(case_id, run_label)
    82	    if not p.is_file():
    83	        return None
    84	    data = json.loads(p.read_text(encoding="utf-8"))
    85	    if not isinstance(data, dict):
    86	        return None
    87	    return data
    88	
    89	
    90	def _validated_timestamp(ts: Any) -> Optional[str]:
    91	    """Codex round 1 HIGH: reject any manifest-supplied timestamp that doesn't
    92	    match the exact YYYYMMDDTHHMMSSZ shape. Blocks '../../outside' etc."""
    93	    if not isinstance(ts, str) or not _TIMESTAMP_RE.match(ts):
    94	        return None
    95	    return ts
    96	
    97	
    98	def _safe_rel_under(candidate: str, root: Path) -> Optional[str]:
    99	    """Return `candidate` if it resolves under `root`, else None.
   100	
   101	    Used to validate manifest-supplied output file paths before they flow
   102	    into template `img src`. Prevents a tampered renders manifest from
   103	    pointing WeasyPrint base_url resolution at arbitrary local files
   104	    (which would then be embedded into PDFs as image data URLs).
   105	    """
   106	    if not isinstance(candidate, str) or not candidate:
   107	        return None
   108	    if candidate.startswith("/") or "\\" in candidate or ".." in candidate.split("/"):
   109	        return None
   110	    try:
   111	        resolved = (_REPO_ROOT / candidate).resolve(strict=False)
   112	        resolved.relative_to(root.resolve())
   113	    except (ValueError, OSError):
   114	        return None
   115	    return candidate
   116	
   117	
   118	def _load_ldc_gold() -> tuple[list[float], list[float], dict]:
   119	    gold_path = _GOLD_ROOT / "lid_driven_cavity.yaml"
   120	    if not gold_path.is_file():
   121	        raise ReportError(f"gold file missing: {gold_path}")
   122	    docs = list(yaml.safe_load_all(gold_path.read_text(encoding="utf-8")))
   123	    u_doc = next(
   124	        (d for d in docs if isinstance(d, dict) and d.get("quantity") == "u_centerline"),
   125	        None,
   126	    )
   127	    if u_doc is None:
   128	        raise ReportError("no u_centerline doc in LDC gold")
   129	    ys: list[float] = []
   130	    us: list[float] = []
   131	    for entry in u_doc.get("reference_values", []):
   132	        if isinstance(entry, dict):
   133	            y = entry.get("y")
   134	            u = entry.get("value") or entry.get("u")
   135	            if y is not None and u is not None:
   136	                ys.append(float(y))
   137	                us.append(float(u))
   138	    return ys, us, u_doc
   139	
   140	
   141	def _load_sample_xy(path: Path) -> tuple[np.ndarray, np.ndarray]:
   142	    rows = []
   143	    for line in path.read_text(encoding="utf-8").splitlines():
   144	        s = line.strip()
   145	        if not s or s.startswith("#"):
   146	            continue
   147	        parts = s.split()
   148	        try:
   149	            rows.append([float(parts[0]), float(parts[1])])
   150	        except (ValueError, IndexError):
   151	            continue
   152	    if not rows:
   153	        raise ReportError(f"empty sample: {path}")
   154	    arr = np.array(rows)
   155	    return arr[:, 0], arr[:, 1]
   156	
   157	
   158	def _latest_sample_iter(artifact_dir: Path) -> Path:
   159	    sample_root = artifact_dir / "sample"
   160	    if not sample_root.is_dir():
   161	        raise ReportError(f"sample/ missing under {artifact_dir}")
   162	    iters = sorted(
   163	        (d for d in sample_root.iterdir() if d.is_dir() and d.name.isdigit()),
   164	        key=lambda d: int(d.name),
   165	    )
   166	    if not iters:
   167	        raise ReportError(f"no sample iter dirs under {sample_root}")
   168	    return iters[-1]
   169	
   170	
   171	def _compute_metrics(
   172	    y_sim: np.ndarray, u_sim: np.ndarray,
   173	    y_gold: list[float], u_gold: list[float],
   174	    tolerance_pct: float,
   175	) -> dict[str, Any]:
   176	    """Compute L2/Linf/RMS + per-point |dev|% + pass count."""
   177	    y_sim_norm = y_sim / max(float(y_sim.max()), 1e-12)
   178	    u_sim_interp = np.interp(np.array(y_gold), y_sim_norm, u_sim)
   179	    u_gold_arr = np.array(u_gold)
   180	    diff = u_sim_interp - u_gold_arr
   181	
   182	    denom = np.where(np.abs(u_gold_arr) < 1e-9, 1e-9, np.abs(u_gold_arr))
   183	    dev_pct = 100.0 * np.abs(diff) / denom
   184	    n_total = len(u_gold_arr)
   185	    n_pass = int((dev_pct < tolerance_pct).sum())
   186	
   187	    return {
   188	        "l2": float(np.sqrt(np.mean(diff ** 2))),
   189	        "linf": float(np.max(np.abs(diff))),
   190	        "rms": float(np.sqrt(np.mean(diff ** 2))),  # alias
   191	        "max_dev_pct": float(dev_pct.max()) if n_total else 0.0,
   192	        "n_pass": n_pass,
   193	        "n_total": n_total,
   194	        "per_point_dev_pct": dev_pct.tolist(),
   195	    }
   196	
   197	
   198	def _parse_residuals_csv(path: Path) -> dict[str, Any]:
   199	    if not path.is_file():
   200	        return {"total_iter": 0, "final_ux": None, "note": None}
   201	    lines = path.read_text(encoding="utf-8").splitlines()
   202	    if len(lines) < 2:
   203	        return {"total_iter": 0, "final_ux": None, "note": None}
   204	    header = [c.strip() for c in lines[0].split(",")]
   205	    last = None
   206	    count = 0
   207	    for ln in lines[1:]:
   208	        parts = [c.strip() for c in ln.split(",")]
   209	        if len(parts) != len(header):
   210	            continue
   211	        last = parts
   212	        count += 1
   213	    final_ux = None
   214	    if last is not None and len(last) > 1 and last[1].upper() != "N/A":
   215	        try:
   216	            final_ux = float(last[1])
   217	        except ValueError:
   218	            pass
   219	    note = None
   220	    if final_ux is not None and final_ux > 1e-3:
   221	        note = (f"注意：Ux 终值 {final_ux:.2e} 大于 1e-3 — "
   222	                f"收敛可能未达稳态。建议增加 endTime 或降低 residualControl。")
   223	    return {"total_iter": count, "final_ux": final_ux, "note": note}
   224	
   225	
   226	def _load_grid_convergence(case_id: str, gold_y: list[float], gold_u: list[float]) -> tuple[list[dict], str]:
   227	    """Read mesh_20/40/80/160_measurement.yaml fixtures, build table rows."""
   228	    rows: list[dict] = []
   229	    # LDC fixtures compare at y≈0.0625 (first gold point >0).
   230	    sample_y = 0.0625
   231	    try:
   232	        sample_gold = next(u for y, u in zip(gold_y, gold_u) if abs(y - sample_y) < 1e-3)
   233	    except StopIteration:
   234	        sample_gold = gold_u[1] if len(gold_u) > 1 else 0.0
   235	
   236	    case_dir = _FIXTURE_ROOT / case_id
   237	    meshes = [("mesh_20", 20), ("mesh_40", 40), ("mesh_80", 80), ("mesh_160", 160)]
   238	    for name, _n in meshes:
   239	        path = case_dir / f"{name}_measurement.yaml"
   240	        if not path.is_file():
   241	            continue
   242	        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
   243	        meas = doc.get("measurement", {}) if isinstance(doc, dict) else {}
   244	        val = meas.get("value")
   245	        if val is None:
   246	            continue
   247	        try:
   248	            val_f = float(val)
   249	        except (ValueError, TypeError):
   250	            continue
   251	        denom = abs(sample_gold) if abs(sample_gold) > 1e-9 else 1e-9
   252	        dev_pct = 100.0 * abs(val_f - sample_gold) / denom
   253	        if dev_pct < 5.0:
   254	            verdict, cls = "PASS", "pass"
   255	        elif dev_pct < 10.0:
   256	            verdict, cls = "WARN", "warn"
   257	        else:
   258	            verdict, cls = "FAIL", "fail"
   259	        rows.append({
   260	            "mesh": name,

exec
/bin/zsh -lc "nl -ba /Users/Zhuanz/.codex/memories/MEMORY.md | sed -n '356,375p;808,890p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   356	# Task Group: cfd-harness-unified governance closeout and planning gates
   357	
   358	scope: Close out accepted phases in `cfd-harness-unified`, normalize Notion-vs-repo naming drift, and keep future phases planning-only until the explicit solver/routing gate is reviewed.
   359	applies_to: cwd=/Users/Zhuanz/Desktop/cfd-harness-unified; reuse_rule=safe for this repo’s Notion-governed phase/gate work, but phase/task IDs and review packets are rollout-specific.
   360	
   361	## Task 1: Close Phase 8 and reconcile stale governance evidence
   362	
   363	### rollout_summary_files
   364	
   365	- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, Phase 8 closeout and evidence normalization)
   366	
   367	### keywords
   368	
   369	- Phase 8, AutoVerifier, 13/13, knowledge/whitelist.yaml, ai_cfd_cold_start_whitelist.yaml, Canonical Docs Type=Report, Phase 8 Done, naming drift
   370	
   371	## Task 2: Open Phase 9 as planning-only and keep solver expansion bounded
   372	
   373	### rollout_summary_files
   374	
   375	- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, Phase 9 kept as planning-only with decision-tree packet))
   808	## Task 1: Build Phase 7.1 Protocol + factory + fallback on the real repo contract
   809	
   810	### rollout_summary_files
   811	
   812	- rollout_summaries/2026-04-09T09-03-23-PPG9-phase_7_1_solver_executor_protocol_factory_fallback.md (cwd=/Users/Zhuanz/Desktop/notion-cfd-harness, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/09/rollout-2026-04-09T17-03-23-019d717b-5dd9-76d3-bb58-5ca66d112f19.jsonl, updated_at=2026-04-09T09:11:05+00:00, thread_id=019d717b-5dd9-76d3-bb58-5ca66d112f19, Protocol/factory/fallback foundation)
   813	
   814	### keywords
   815	
   816	- Protocol not ABC, SolverExecutor, ExecutorFactory, simulate_benchmark_output, config/solver.yaml, openfoam-docker, su2-docker, is_mock is an OUTPUT property, 36 passed
   817	
   818	## Task 2: Add template-based OpenFOAM case generation and Docker-backed execution
   819	
   820	### rollout_summary_files
   821	
   822	- rollout_summaries/2026-04-09T09-12-50-JARi-phase_7_1b_openfoam_case_generator.md (cwd=/Users/Zhuanz/Desktop/notion-cfd-harness, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/09/rollout-2026-04-09T17-12-50-019d7184-05b7-7a23-a1c3-7569afea2380.jsonl, updated_at=2026-04-09T09:42:35+00:00, thread_id=019d7184-05b7-7a23-a1c3-7569afea2380, three-case template generator)
   823	- rollout_summaries/2026-04-09T09-46-14-BhcD-phase7_2_openfoam_docker_executor.md (cwd=/Users/Zhuanz/Desktop/notion-cfd-harness, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/09/rollout-2026-04-09T17-46-14-019d71a2-994b-7bd2-ac2a-e32421ff628b.jsonl, updated_at=2026-04-09T09:51:40+00:00, thread_id=019d71a2-994b-7bd2-ac2a-e32421ff628b, Docker executor integrated against actual protocol)
   824	
   825	### keywords
   826	
   827	- OpenFOAMCaseGenerator, templates/openfoam, BENCH-01, BENCH-07, BENCH-04, icoFoam, simpleFoam, pimpleFoam, OpenFOAMDockerExecutor, docker info, os.getuid getgid, 1759 passed
   828	
   829	## Task 3: Replace VAWT/NACA wiring with BENCH-04 cylinder wake consistently
   830	
   831	### rollout_summary_files
   832	
   833	- rollout_summaries/2026-04-09T07-12-18-UxQc-replace_vawt_naca_with_bench04_cylinder_wake.md (cwd=/Users/Zhuanz/Desktop/notion-cfd-harness, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/09/rollout-2026-04-09T15-12-18-019d7115-a9bc-72f1-81b8-1dd12bf59d78.jsonl, updated_at=2026-04-09T07:30:29+00:00, thread_id=019d7115-a9bc-72f1-81b8-1dd12bf59d78, benchmark replacement completed with full suite green)
   834	
   835	### keywords
   836	
   837	- BENCH-04, Circular Cylinder Wake, Williamson 1996, bench_cylinder_wake.py, circular_cylinder_wake_re100_vortex_street, grep -r VAWT NACA, 1742 passed
   838	
   839	## Task 4: Verify prerequisites and diagnose why the correction loop still does not affect Phase 3 reasoning
   840	
   841	### rollout_summary_files
   842	
   843	- rollout_summaries/2026-04-09T05-55-36-cJjP-phase3_permission_level_explore_prereq_checker.md (cwd=/Users/Zhuanz/Desktop/notion-cfd-harness, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/09/rollout-2026-04-09T13-55-36-019d70cf-72ea-7431-88b4-d12728b1df01.jsonl, updated_at=2026-04-09T06:01:49+00:00, thread_id=019d70cf-72ea-7431-88b4-d12728b1df01, EXPLORE path and prerequisite checker)
   844	- rollout_summaries/2026-04-09T07-32-38-hVV6-m3_correction_feedback_loop_verification.md (cwd=/Users/Zhuanz/Desktop/notion-cfd-harness, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/09/rollout-2026-04-09T15-32-38-019d7128-4828-7812-b2c0-4c7e082e70c0.jsonl, updated_at=2026-04-09T07:42:51+00:00, thread_id=019d7128-4828-7812-b2c0-4c7e082e70c0, read-only L1/L2/L3 verification)
   845	- rollout_summaries/2026-04-09T07-43-42-GddW-phase2d_phase3_correction_feedback_loop_fix.md (cwd=/Users/Zhuanz/Desktop/notion-cfd-harness, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/09/rollout-2026-04-09T15-43-42-019d7132-6af3-7731-9cb9-0c889571c5d4.jsonl, updated_at=2026-04-09T07:59:09+00:00, thread_id=019d7132-6af3-7731-9cb9-0c889571c5d4, attempted fix and gap mapping)
   846	
   847	### keywords
   848	
   849	- PermissionLevel.EXPLORE, TrialRunner default executor mock, check_prerequisites.py, KnowledgeManager.extract_knowledge expects CorrectionRecord, CorrectionRecordingStageExecutor stub, similarity_before = 0.996007, matched_patterns_after = []
   850	
   851	## Task 5: Preserve implementation intent when Phase 3 postprocess work is blocked by read-only patch rejection
   852	
   853	### rollout_summary_files
   854	
   855	- rollout_summaries/2026-04-08T07-04-25-HXCI-phase3_postprocess_runner_readonly_blocked.md (cwd=/Users/Zhuanz/Desktop/notion-cfd-harness, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/08/rollout-2026-04-08T15-04-25-019d6be8-177f-7432-8b92-9411107a5014.jsonl, updated_at=2026-04-08T07:12:33+00:00, thread_id=019d6be8-177f-7432-8b92-9411107a5014, implementation plan preserved but no files created)
   856	
   857	### keywords
   858	
   859	- postprocess_runner, nl_postprocess, visualization_engine, result_manifest, result_asset, patch-rejected, writing outside of the project; rejected by user approval settings, read-only, OpenFOAM
   860	
   861	## Task 6: Preserve the requested Phase 2 compiler-layer contract even when implementation proof is missing
   862	
   863	### rollout_summary_files
   864	
   865	- rollout_summaries/2026-04-08T04-16-56-PF81-phase2_compiler_layer_request.md (cwd=/Users/Zhuanz/Desktop/notion-cfd-harness, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/08/rollout-2026-04-08T12-16-56-019d6b4e-c1f7-7f03-90b7-174d50e18ead.jsonl, updated_at=2026-04-08T04:17:06+00:00, thread_id=019d6b4e-c1f7-7f03-90b7-174d50e18ead, contract/spec memory only; outcome unverified)
   866	
   867	### keywords
   868	
   869	- Phase 2, compiler_layer, CanonicalCompiler, KnowledgePublisher, CanonicalSpec, ParsedTeach, CompiledKnowledge, Phase2GateExecutor, G1-P2, G2-P2, Enum, Python 3.9 dataclass field order
   870	
   871	## User preferences
   872	
   873	- across these multi-file implementation tasks, the user repeatedly said "Run in background" -> for long cross-file slices in this repo, do the wiring and targeted verification in one pass instead of asking them to orchestrate each substep [Task 1][Task 2][Task 3][Task 4]
   874	- for solver/execution work, the user repeatedly specified exact design constraints such as "Use Protocol (not ABC)", separate solver classes, config-driven fallback, and exact case IDs -> preserve those constraints instead of smoothing them into a generic abstraction [Task 1][Task 2]
   875	- when debugging the correction loop, the user said "Priority: Verify L2 first" and "Do NOT make changes yet — just investigate and report findings" -> inspect the real consumer path before patching recorder completeness or downstream semantics [Task 4]
   876	- for evidence tasks, the user explicitly wanted "actual code evidence, not assumptions" -> source/tests beat comments or plan text in this repo [Task 4]
   877	- when the user asked `实现 Postprocess Runner 组件`, the expectation was direct implementation rather than a long design memo -> code the component if writable, and if not, report the exact blocker plus intended file surfaces [Task 5]
   878	- for schema/compiler work, the user asked to "参考 phase2/teach_layer 的风格", use "Enum 而非字符串常量", include "详细的注释和文档字符串", and respect "Python 3.9 dataclass 字段顺序" -> mirror the existing layer style and type discipline instead of introducing a new contract shape [Task 6]
   879	
   880	## Reusable knowledge
   881	
   882	- `Phase6_PLAN.md` is the authoritative design anchor for the repo’s Phase 7 solver path and the sequence `7.1 Protocol + Factory`, `7.1b case generator`, `7.2 OpenFOAMDockerExecutor`, `7.3 SU2DockerExecutor` [Task 1][Task 2]
   883	- The repo’s real solver contract is `setup(case_dir) -> None`, `execute(config) -> SolverResult`, `validate() -> bool`; prompts that sketch other signatures need to be adapted to `solver_protocol.py`, not copied literally [Task 1][Task 2]
   884	- `BENCH-01`, `BENCH-07`, and `BENCH-04` are the supported OpenFOAM presets, and `BENCH-04` already had a usable whitelist/demo identity as `circular_cylinder_wake_re100_vortex_street` [Task 2][Task 3]
   885	- `PermissionLevel.EXPLORE` exists and can use an injected real executor, but `TrialRunner`’s default executor path is still mock, so EXPLORE does not by itself imply real execution [Task 4]
   886	- The real correction-loop break was L2: Phase 3 does not consume Phase 2c corrections in a way that changes similarity/decomposition, `CorrectionRecordingStageExecutor` was still a stub, and some tests were passing with the wrong data type (`dict` instead of `CorrectionRecord`) [Task 4]
   887	- The intended Phase 3 postprocess runner should reuse Phase 1 primitives: `NLPostprocessExecutor`, `VisualizationEngine.execute_visualization()`, `ResultDirectoryParser`, and `ResultManifest` / `ResultAsset`, while adding a Phase 3 wrapper and re-exporting it via `knowledge_compiler/phase3/__init__.py` [Task 5]
   888	- The current Phase 1 parser has OpenFOAM asset gaps (`0/p`, `0/U`), so any future Phase 3 postprocess wrapper needs an augmentation layer rather than a naive pass-through [Task 5]
   889	- The requested Phase 2 compiler contract is already specific enough to route future work: `CanonicalCompiler.compile`, `compile_batch`, `merge_specs`, plus `KnowledgePublisher.publish`, `run_gates`, and `verify`, with ordered `G1-P2` then `G2-P2` execution through `Phase2GateExecutor` [Task 6]
   890	

exec
/bin/zsh -lc "nl -ba ui/backend/routes/comparison_report.py | sed -n '1,260p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
     1	"""Phase 7c — CFD vs Gold comparison report route.
     2	
     3	GET  /api/cases/{case_id}/runs/{run_label}/comparison-report         → HTML
     4	GET  /api/cases/{case_id}/runs/{run_label}/comparison-report.pdf     → PDF
     5	POST /api/cases/{case_id}/runs/{run_label}/comparison-report/build   → rebuild PDF + return manifest
     6	
     7	Uses FileResponse pattern per Phase 7a user ratification #1 (no StaticFiles).
     8	"""
     9	from __future__ import annotations
    10	
    11	from pathlib import Path
    12	
    13	from fastapi import APIRouter, HTTPException
    14	from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
    15	
    16	from ui.backend.services.comparison_report import (
    17	    ReportError,
    18	    build_report_context,
    19	    render_report_html,
    20	    render_report_pdf,
    21	)
    22	from ui.backend.services.run_ids import _validate_segment
    23	
    24	router = APIRouter()
    25	
    26	
    27	def _validate_ids(case_id: str, run_label: str) -> None:
    28	    """Reuse Phase 7a traversal defense on case_id + run_label segments."""
    29	    _validate_segment(case_id, "case_id")
    30	    _validate_segment(run_label, "run_label")
    31	
    32	
    33	@router.get(
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
    96	@router.post(
    97	    "/cases/{case_id}/runs/{run_label}/comparison-report/build",
    98	    tags=["comparison-report"],
    99	)
   100	def build_comparison_report(case_id: str, run_label: str) -> JSONResponse:
   101	    """Force-rebuild HTML + PDF, return manifest."""
   102	    _validate_ids(case_id, run_label)
   103	    try:
   104	        html = render_report_html(case_id, run_label)
   105	        pdf_path = render_report_pdf(case_id, run_label)
   106	    except ReportError as e:
   107	        raise HTTPException(status_code=404, detail=str(e))
   108	    except ImportError:
   109	        raise HTTPException(status_code=503, detail="WeasyPrint unavailable")
   110	    return JSONResponse({
   111	        "case_id": case_id,
   112	        "run_label": run_label,
   113	        "pdf_path": str(pdf_path),
   114	        "html_bytes": len(html),
   115	    })

exec
/bin/zsh -lc "nl -ba ui/backend/tests/test_comparison_report_route.py | sed -n '1,260p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
     1	"""Phase 7c — comparison report route tests.
     2	
     3	Guards route-level behavior: 200 on valid case/run, 404 on missing, 400 on
     4	traversal attempts. Actual HTML content is covered by unit tests of the
     5	service module.
     6	"""
     7	from __future__ import annotations
     8	
     9	from fastapi.testclient import TestClient
    10	
    11	from ui.backend.main import app
    12	
    13	client = TestClient(app)
    14	
    15	# These tests run against the real reports/phase5_fields/lid_driven_cavity/
    16	# artifact set which is .gitignored. In CI (no artifacts), they should 404 —
    17	# which is fine, they'll be re-collected on developer machines.
    18	
    19	
    20	def _has_ldc_artifacts() -> bool:
    21	    from pathlib import Path
    22	    manifest = Path("reports/phase5_fields/lid_driven_cavity/runs/audit_real_run.json")
    23	    return manifest.is_file()
    24	
    25	
    26	def test_html_200_when_artifacts_present() -> None:
    27	    if not _has_ldc_artifacts():
    28	        return  # skip silently on CI-style clean checkout
    29	    r = client.get("/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report")
    30	    assert r.status_code == 200, r.text
    31	    body = r.text
    32	    # 8 section markers from the Jinja template.
    33	    for marker in [
    34	        "参考文献",           # §2
    35	        "中心线 profile",      # §3
    36	        "逐点偏差分布",        # §4
    37	        "流场 contour",        # §5
    38	        "残差收敛历史",        # §6
    39	        "网格收敛",            # §7
    40	        "求解器元数据",        # §8
    41	    ]:
    42	        assert marker in body, f"missing section marker: {marker}"
    43	    # Verdict card must be present.
    44	    assert "verdict-card" in body
    45	
    46	
    47	def test_context_200_when_artifacts_present() -> None:
    48	    if not _has_ldc_artifacts():
    49	        return
    50	    r = client.get(
    51	        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report/context",
    52	    )
    53	    assert r.status_code == 200, r.text
    54	    d = r.json()
    55	    assert d["case_id"] == "lid_driven_cavity"
    56	    assert d["run_label"] == "audit_real_run"
    57	    assert "metrics" in d
    58	    assert d["metrics"]["n_total"] > 0
    59	    assert d["verdict"] in ("PASS", "PARTIAL", "FAIL")
    60	
    61	
    62	def test_html_404_unknown_case() -> None:
    63	    r = client.get("/api/cases/nonexistent_case/runs/audit_real_run/comparison-report")
    64	    assert r.status_code == 404
    65	
    66	
    67	def test_html_400_traversal_case_id() -> None:
    68	    r = client.get("/api/cases/..__pwn/runs/audit_real_run/comparison-report")
    69	    assert r.status_code == 400
    70	
    71	
    72	def test_html_400_traversal_run_label() -> None:
    73	    r = client.get("/api/cases/lid_driven_cavity/runs/..__pwn/comparison-report")
    74	    assert r.status_code == 400
    75	
    76	
    77	def test_context_400_urlencoded_traversal() -> None:
    78	    r = client.get(
    79	        "/api/cases/%2e%2e__pwn/runs/audit_real_run/comparison-report/context",
    80	    )
    81	    assert r.status_code == 400
    82	
    83	
    84	# ---------- CI-safe success path (Codex round 2 LOW follow-up) --------------
    85	# Builds a synthetic tree and monkeypatches module globals so CI without
    86	# real OpenFOAM artifacts still exercises the 200 path end-to-end.
    87	
    88	import json
    89	from pathlib import Path as _P
    90	
    91	import pytest as _pytest
    92	
    93	
    94	@_pytest.fixture
    95	def _synth_route_tree(tmp_path: _P, monkeypatch):
    96	    case = "lid_driven_cavity"
    97	    ts = "20260421T000000Z"
    98	    fields_root = tmp_path / "reports" / "phase5_fields"
    99	    renders_root = tmp_path / "reports" / "phase5_renders"
   100	    (fields_root / case / ts / "sample" / "1000").mkdir(parents=True)
   101	    (fields_root / case / ts / "sample" / "1000" / "uCenterline.xy").write_text(
   102	        "# y Ux Uy Uz p\n0 0 0 0 0\n0.5 -0.2 0 0 0\n1.0 1.0 0 0 0\n",
   103	        encoding="utf-8",
   104	    )
   105	    (fields_root / case / ts / "residuals.csv").write_text(
   106	        "Time,Ux,Uy,p\n1,1.0,1.0,1.0\n2,0.1,0.1,0.1\n", encoding="utf-8",
   107	    )
   108	    (fields_root / case / "runs").mkdir(parents=True)
   109	    (fields_root / case / "runs" / "audit_real_run.json").write_text(
   110	        json.dumps({"timestamp": ts, "case_id": case, "run_label": "audit_real_run"}),
   111	        encoding="utf-8",
   112	    )
   113	    (renders_root / case / ts).mkdir(parents=True)
   114	    for n in ["profile_u_centerline.png", "pointwise_deviation.png",
   115	              "contour_u_magnitude.png", "residuals.png"]:
   116	        (renders_root / case / ts / n).write_bytes(b"\x89PNG\r\n\x1a\n")
   117	    (renders_root / case / "runs").mkdir(parents=True)
   118	    (renders_root / case / "runs" / "audit_real_run.json").write_text(
   119	        json.dumps({
   120	            "case_id": case, "run_label": "audit_real_run", "timestamp": ts,
   121	            "outputs": {
   122	                "profile_png": f"reports/phase5_renders/{case}/{ts}/profile_u_centerline.png",
   123	                "pointwise_deviation_png": f"reports/phase5_renders/{case}/{ts}/pointwise_deviation.png",
   124	                "contour_u_magnitude_png": f"reports/phase5_renders/{case}/{ts}/contour_u_magnitude.png",
   125	                "residuals_png": f"reports/phase5_renders/{case}/{ts}/residuals.png",
   126	            },
   127	        }),
   128	        encoding="utf-8",
   129	    )
   130	    gold = tmp_path / "knowledge" / "gold_standards"
   131	    gold.mkdir(parents=True)
   132	    (gold / "lid_driven_cavity.yaml").write_text(
   133	        "quantity: u_centerline\n"
   134	        "reference_values:\n"
   135	        "  - y: 0.0\n    u: 0.0\n"
   136	        "  - y: 0.5\n    u: -0.20581\n"
   137	        "  - y: 1.0\n    u: 1.0\n"
   138	        "tolerance: 0.05\n"
   139	        "source: Ghia 1982\n"
   140	        "literature_doi: 10.1016/0021-9991(82)90058-4\n",
   141	        encoding="utf-8",
   142	    )
   143	    fixtures = tmp_path / "ui" / "backend" / "tests" / "fixtures" / "runs" / case
   144	    fixtures.mkdir(parents=True)
   145	    for m, v in (("mesh_20", -0.055), ("mesh_40", -0.048),
   146	                 ("mesh_80", -0.044), ("mesh_160", -0.042)):
   147	        (fixtures / f"{m}_measurement.yaml").write_text(
   148	            f"measurement:\n  value: {v}\n", encoding="utf-8",
   149	        )
   150	    from ui.backend.services import comparison_report as svc
   151	    monkeypatch.setattr(svc, "_REPO_ROOT", tmp_path)
   152	    monkeypatch.setattr(svc, "_FIELDS_ROOT", fields_root)
   153	    monkeypatch.setattr(svc, "_RENDERS_ROOT", renders_root)
   154	    monkeypatch.setattr(svc, "_GOLD_ROOT", gold)
   155	    monkeypatch.setattr(svc, "_FIXTURE_ROOT",
   156	                        tmp_path / "ui" / "backend" / "tests" / "fixtures" / "runs")
   157	    yield tmp_path
   158	
   159	
   160	def test_html_200_end_to_end_synthetic(_synth_route_tree) -> None:
   161	    """CI-safe: route → service → template with monkeypatched roots."""
   162	    r = client.get(
   163	        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report",
   164	    )
   165	    assert r.status_code == 200, r.text
   166	    # Verify all 8 sections rendered.
   167	    for marker in ["参考文献", "中心线 profile", "逐点偏差分布",
   168	                   "流场 contour", "残差收敛历史", "网格收敛",
   169	                   "求解器元数据"]:
   170	        assert marker in r.text, marker
   171	
   172	
   173	def test_context_json_end_to_end_synthetic(_synth_route_tree) -> None:
   174	    r = client.get(
   175	        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report/context",
   176	    )
   177	    assert r.status_code == 200, r.text
   178	    d = r.json()
   179	    assert d["case_id"] == "lid_driven_cavity"
   180	    assert d["timestamp"] == "20260421T000000Z"
   181	    assert d["metrics"]["n_total"] == 3

exec
/bin/zsh -lc "nl -ba ui/backend/tests/test_comparison_report_service.py | sed -n '1,320p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md | sed -n '1,220p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
     1	"""Phase 7c — comparison_report service unit tests (CI-safe, no real artifacts).
     2	
     3	Builds a synthetic artifact tree in tmp_path, monkeypatches the module's root
     4	constants, exercises render_report_html + build_report_context + the Codex
     5	round-1 HIGH containment guards.
     6	"""
     7	from __future__ import annotations
     8	
     9	import json
    10	from pathlib import Path
    11	
    12	import pytest
    13	
    14	
    15	@pytest.fixture
    16	def synthetic_tree(tmp_path: pytest.TempPathFactory, monkeypatch):
    17	    """Build a minimal Phase-7a-and-7b-compatible artifact tree in tmp_path."""
    18	    root = tmp_path
    19	    case = "lid_driven_cavity"
    20	    ts = "20260421T000000Z"
    21	
    22	    fields_root = root / "reports" / "phase5_fields"
    23	    renders_root = root / "reports" / "phase5_renders"
    24	    case_fields = fields_root / case / ts
    25	    (case_fields / "sample" / "1000").mkdir(parents=True)
    26	    (case_fields / "sample" / "1000" / "uCenterline.xy").write_text(
    27	        "#   y   U_x   U_y   U_z   p\n"
    28	        "0     0      0     0    0.5\n"
    29	        "0.5  -0.2    0     0    0.5\n"
    30	        "1.0   1.0    0     0    0.5\n",
    31	        encoding="utf-8",
    32	    )
    33	    (case_fields / "residuals.csv").write_text(
    34	        "Time,Ux,Uy,p\n0,N/A,N/A,N/A\n1,1.0,1.0,1.0\n2,0.1,0.1,0.1\n",
    35	        encoding="utf-8",
    36	    )
    37	    (fields_root / case / "runs").mkdir(parents=True)
    38	    (fields_root / case / "runs" / "audit_real_run.json").write_text(
    39	        json.dumps({"timestamp": ts, "case_id": case, "run_label": "audit_real_run"}),
    40	        encoding="utf-8",
    41	    )
    42	
    43	    # Minimal render outputs (empty PNGs are fine for containment checks).
    44	    renders_case = renders_root / case / ts
    45	    renders_case.mkdir(parents=True)
    46	    for name in ["profile_u_centerline.png", "pointwise_deviation.png",
    47	                 "contour_u_magnitude.png", "residuals.png"]:
    48	        (renders_case / name).write_bytes(b"\x89PNG\r\n\x1a\n")  # 8-byte stub
    49	    (renders_root / case / "runs").mkdir(parents=True)
    50	    (renders_root / case / "runs" / "audit_real_run.json").write_text(
    51	        json.dumps({
    52	            "case_id": case, "run_label": "audit_real_run", "timestamp": ts,
    53	            "outputs": {
    54	                "profile_png": f"reports/phase5_renders/{case}/{ts}/profile_u_centerline.png",
    55	                "pointwise_deviation_png": f"reports/phase5_renders/{case}/{ts}/pointwise_deviation.png",
    56	                "contour_u_magnitude_png": f"reports/phase5_renders/{case}/{ts}/contour_u_magnitude.png",
    57	                "residuals_png": f"reports/phase5_renders/{case}/{ts}/residuals.png",
    58	            },
    59	        }),
    60	        encoding="utf-8",
    61	    )
    62	
    63	    # Minimal LDC gold YAML in tmp_path/knowledge/gold_standards/.
    64	    gold_dir = root / "knowledge" / "gold_standards"
    65	    gold_dir.mkdir(parents=True)
    66	    (gold_dir / "lid_driven_cavity.yaml").write_text(
    67	        "quantity: u_centerline\n"
    68	        "reference_values:\n"
    69	        "  - y: 0.0\n    u: 0.0\n"
    70	        "  - y: 0.5\n    u: -0.20581\n"
    71	        "  - y: 1.0\n    u: 1.0\n"
    72	        "tolerance: 0.05\n"
    73	        "source: Ghia Ghia Shin 1982 Table I Re=100\n"
    74	        "literature_doi: 10.1016/0021-9991(82)90058-4\n",
    75	        encoding="utf-8",
    76	    )
    77	
    78	    # Minimal mesh_{20,40,80,160} fixtures for grid-convergence table.
    79	    fixture_case = root / "ui" / "backend" / "tests" / "fixtures" / "runs" / case
    80	    fixture_case.mkdir(parents=True)
    81	    for mesh, val in (("mesh_20", -0.055), ("mesh_40", -0.048),
    82	                      ("mesh_80", -0.044), ("mesh_160", -0.042)):
    83	        (fixture_case / f"{mesh}_measurement.yaml").write_text(
    84	            f"measurement:\n  value: {val}\n", encoding="utf-8",
    85	        )
    86	
    87	    from ui.backend.services import comparison_report as svc
    88	    monkeypatch.setattr(svc, "_REPO_ROOT", root)
    89	    monkeypatch.setattr(svc, "_FIELDS_ROOT", fields_root)
    90	    monkeypatch.setattr(svc, "_RENDERS_ROOT", renders_root)
    91	    monkeypatch.setattr(svc, "_GOLD_ROOT", gold_dir)
    92	    monkeypatch.setattr(svc, "_FIXTURE_ROOT", root / "ui" / "backend" / "tests" / "fixtures" / "runs")
    93	
    94	    return {"root": root, "case": case, "ts": ts, "svc": svc}
    95	
    96	
    97	def test_build_context_happy_path(synthetic_tree) -> None:
    98	    svc = synthetic_tree["svc"]
    99	    ctx = svc.build_report_context("lid_driven_cavity", "audit_real_run")
   100	    assert ctx["case_id"] == "lid_driven_cavity"
   101	    assert ctx["timestamp"] == "20260421T000000Z"
   102	    assert ctx["metrics"]["n_total"] == 3
   103	    assert ctx["verdict"] in ("PASS", "PARTIAL", "FAIL")
   104	
   105	
   106	def test_render_html_contains_8_sections(synthetic_tree) -> None:
   107	    svc = synthetic_tree["svc"]
   108	    html = svc.render_report_html("lid_driven_cavity", "audit_real_run")
   109	    for marker in ["参考文献", "中心线 profile", "逐点偏差分布",
   110	                   "流场 contour", "残差收敛历史", "网格收敛",
   111	                   "求解器元数据"]:
   112	        assert marker in html, f"missing §: {marker}"
   113	
   114	
   115	def test_rejects_tampered_manifest_timestamp(synthetic_tree) -> None:
   116	    """Codex round 1 HIGH: manifest with timestamp='../../outside' must be rejected."""
   117	    svc = synthetic_tree["svc"]
   118	    root = synthetic_tree["root"]
   119	    # Overwrite manifest with malicious timestamp.
   120	    m = root / "reports" / "phase5_fields" / "lid_driven_cavity" / "runs" / "audit_real_run.json"
   121	    m.write_text(json.dumps({"timestamp": "../../../../tmp/evil"}), encoding="utf-8")
   122	    with pytest.raises(svc.ReportError, match="invalid timestamp"):
   123	        svc.build_report_context("lid_driven_cavity", "audit_real_run")
   124	
   125	
   126	def test_rejects_non_matching_timestamp_shape(synthetic_tree) -> None:
   127	    """Timestamp must match exact YYYYMMDDTHHMMSSZ regex."""
   128	    svc = synthetic_tree["svc"]
   129	    root = synthetic_tree["root"]
   130	    m = root / "reports" / "phase5_fields" / "lid_driven_cavity" / "runs" / "audit_real_run.json"
   131	    m.write_text(json.dumps({"timestamp": "2026-04-21"}), encoding="utf-8")
   132	    with pytest.raises(svc.ReportError):
   133	        svc.build_report_context("lid_driven_cavity", "audit_real_run")
   134	
   135	
   136	def test_rejects_tampered_renders_manifest_output_path(synthetic_tree) -> None:
   137	    """Codex round 1 HIGH: img src in renders manifest must be inside renders root."""
   138	    svc = synthetic_tree["svc"]
   139	    root = synthetic_tree["root"]
   140	    # Overwrite renders manifest with escape path.
   141	    rm = root / "reports" / "phase5_renders" / "lid_driven_cavity" / "runs" / "audit_real_run.json"
   142	    rm.write_text(
   143	        json.dumps({
   144	            "case_id": "lid_driven_cavity", "run_label": "audit_real_run",
   145	            "timestamp": "20260421T000000Z",
   146	            "outputs": {
   147	                "profile_png": "../../../../etc/passwd",
   148	                "pointwise_deviation_png": "/etc/passwd",
   149	                "contour_u_magnitude_png": "reports/phase5_renders/lid_driven_cavity/20260421T000000Z/contour_u_magnitude.png",
   150	                "residuals_png": "reports/phase5_renders/lid_driven_cavity/20260421T000000Z/residuals.png",
   151	            },
   152	        }),
   153	        encoding="utf-8",
   154	    )
   155	    ctx = svc.build_report_context("lid_driven_cavity", "audit_real_run")
   156	    # Escaped paths must be scrubbed to empty; the template will skip empty src.
   157	    assert ctx["renders"]["profile_png_rel"] in ("", None) \
   158	        or "etc/passwd" not in ctx["renders"]["profile_png_rel"]
   159	    assert "etc/passwd" not in ctx["renders"]["pointwise_png_rel"]
   160	    # Safe entries retained.
   161	    assert "reports/phase5_renders" in ctx["renders"]["contour_png_rel"]
   162	
   163	
   164	def test_rejects_non_object_run_manifest(synthetic_tree) -> None:
   165	    """Codex round 2 (7a precedent): non-object JSON must fail closed."""
   166	    svc = synthetic_tree["svc"]
   167	    root = synthetic_tree["root"]
   168	    m = root / "reports" / "phase5_fields" / "lid_driven_cavity" / "runs" / "audit_real_run.json"
   169	    m.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")
   170	    with pytest.raises(svc.ReportError, match="not an object"):
   171	        svc.build_report_context("lid_driven_cavity", "audit_real_run")
   172	
   173	
   174	def test_pdf_output_path_contained(synthetic_tree, tmp_path: Path) -> None:
   175	    """Codex round 1 HIGH: caller-supplied output_path must stay under reports/phase5_reports/."""
   176	    svc = synthetic_tree["svc"]
   177	    # Attempt to write PDF outside the reports tree.
   178	    evil = tmp_path / "outside" / "evil.pdf"
   179	    with pytest.raises(svc.ReportError, match="escapes reports_root"):
   180	        svc.render_report_pdf("lid_driven_cavity", "audit_real_run", output_path=evil)

 succeeded in 0ms:
     1	2026-04-21T09:38:05.271280Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-research-deerflow/SKILL.md: missing YAML frontmatter delimited by ---
     2	2026-04-21T09:38:05.271297Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-report-pretext/SKILL.md: missing YAML frontmatter delimited by ---
     3	Reading additional input from stdin...
     4	OpenAI Codex v0.118.0 (research preview)
     5	--------
     6	workdir: /Users/Zhuanz/Desktop/cfd-harness-unified
     7	model: gpt-5.4
     8	provider: openai
     9	approval: never
    10	sandbox: danger-full-access
    11	reasoning effort: xhigh
    12	reasoning summaries: none
    13	session id: 019daf67-75e6-7791-ad64-68e5aa8679da
    14	--------
    15	user
    16	Phase 7b+7c+7f round 2 verification after CHANGES_REQUIRED round 1.
    17	
    18	Round 1 findings (3):
    19	- HIGH: Manifest-derived paths (timestamp + renders outputs + PDF output) trusted without containment.
    20	- MEDIUM: /learn embed silently swallows ALL errors, not just 404.
    21	- LOW: Route tests skip on missing artifacts; no service-level unit tests.
    22	
    23	Round 2 fixes (all uncommitted):
    24	
    25	1. HIGH closure — three lines of defense added:
    26	   (a) ui/backend/services/comparison_report.py: `_TIMESTAMP_RE = r"^\d{8}T\d{6}Z$"` shape gate + `_validated_timestamp()` helper. build_report_context raises ReportError if timestamp fails shape gate. Containment check via `.resolve().relative_to(_FIELDS_ROOT/case_id)` after composing artifact_dir. Non-object JSON run_manifest also rejected.
    27	   (b) Renders manifest output paths now pass through `_safe_rel_under(candidate, _RENDERS_ROOT)` which rejects: non-string, empty, absolute paths, backslashes, `..` segments, and paths that fail `resolve().relative_to(renders_root)`. Fallback path discovery uses same validator.
    28	   (c) render_report_pdf: `reports_root = _REPO_ROOT/"reports"/"phase5_reports"` resolved at top; output_path (caller-supplied or default) must `.resolve().relative_to(reports_root)` or ReportError. scripts/render_case_report.py mirrors the shape gate + containment check.
    29	
    30	2. MEDIUM closure — ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx ScientificComparisonReportSection now distinguishes error cases:
    31	   - status 404 or 400 → silent hide (case not opted-in / malformed run_id)
    32	   - any other status OR network error → visible `ErrorCallout` banner with HTTP status + truncated error message
    33	   This preserves "case not supported = clean hide" UX while exposing real regressions.
    34	
    35	3. LOW closure — new test_comparison_report_service.py with 7 CI-safe unit tests:
    36	   - synthetic_tree fixture builds minimal Phase 7a+7b artifact tree in tmp_path and monkeypatches module-level root constants
    37	   - test_build_context_happy_path: full success path exercised without real solver artifacts
    38	   - test_render_html_contains_8_sections: all §2-§8 markers assert
    39	   - test_rejects_tampered_manifest_timestamp: `../../../tmp/evil` → ReportError
    40	   - test_rejects_non_matching_timestamp_shape: `2026-04-21` (wrong format) → ReportError
    41	   - test_rejects_tampered_renders_manifest_output_path: `../../../etc/passwd` scrubbed to empty or non-matching
    42	   - test_rejects_non_object_run_manifest: JSON array → ReportError match "not an object"
    43	   - test_pdf_output_path_contained: caller-supplied output_path outside reports_root → ReportError match "escapes reports_root"
    44	
    45	Regression gate: PYTHONPATH=. .venv/bin/pytest ui/backend/tests/ -q → 110/110 passed (was 103/103; +7 service tests). Live smoke on restarted backend: HTML 200, PDF 200 (622KB valid PDF), traversal ..__pwn → 400.
    46	
    47	Please verify all 3 round-1 findings are closed. Flag any missed edge cases.
    48	codex
    49	Reviewing the Phase 7b/7c/7f round-2 fixes as a correctness pass, not new development. I’m starting with the relevant repo/memory context, then I’ll inspect the changed files and run the targeted verification that matters for the three round-1 findings.
    50	exec
    51	/bin/zsh -lc "sed -n '1,220p' /Users/Zhuanz/.codex/plugins/cache/openai-curated/superpowers/b1986b3d3da5bb8a04d3cb1e69af5a29bb5c2c04/skills/using-superpowers/SKILL.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
    52	 succeeded in 0ms:
    53	---
    54	name: using-superpowers
    55	description: Use when starting any conversation - establishes how to find and use skills, requiring Skill tool invocation before ANY response including clarifying questions
    56	---
    57	
    58	<SUBAGENT-STOP>
    59	If you were dispatched as a subagent to execute a specific task, skip this skill.
    60	</SUBAGENT-STOP>
    61	
    62	<EXTREMELY-IMPORTANT>
    63	If you think there is even a 1% chance a skill might apply to what you are doing, you ABSOLUTELY MUST invoke the skill.
    64	
    65	IF A SKILL APPLIES TO YOUR TASK, YOU DO NOT HAVE A CHOICE. YOU MUST USE IT.
    66	
    67	This is not negotiable. This is not optional. You cannot rationalize your way out of this.
    68	</EXTREMELY-IMPORTANT>
    69	
    70	## Instruction Priority
    71	
    72	Superpowers skills override default system prompt behavior, but **user instructions always take precedence**:
    73	
    74	1. **User's explicit instructions** (CLAUDE.md, GEMINI.md, AGENTS.md, direct requests) — highest priority
    75	2. **Superpowers skills** — override default system behavior where they conflict
    76	3. **Default system prompt** — lowest priority
    77	
    78	If CLAUDE.md, GEMINI.md, or AGENTS.md says "don't use TDD" and a skill says "always use TDD," follow the user's instructions. The user is in control.
    79	
    80	## How to Access Skills
    81	
    82	**In Claude Code:** Use the `Skill` tool. When you invoke a skill, its content is loaded and presented to you—follow it directly. Never use the Read tool on skill files.
    83	
    84	**In Copilot CLI:** Use the `skill` tool. Skills are auto-discovered from installed plugins. The `skill` tool works the same as Claude Code's `Skill` tool.
    85	
    86	**In Gemini CLI:** Skills activate via the `activate_skill` tool. Gemini loads skill metadata at session start and activates the full content on demand.
    87	
    88	**In other environments:** Check your platform's documentation for how skills are loaded.
    89	
    90	## Platform Adaptation
    91	
    92	Skills use Claude Code tool names. Non-CC platforms: see `references/copilot-tools.md` (Copilot CLI), `references/codex-tools.md` (Codex) for tool equivalents. Gemini CLI users get the tool mapping loaded automatically via GEMINI.md.
    93	
    94	# Using Skills
    95	
    96	## The Rule
    97	
    98	**Invoke relevant or requested skills BEFORE any response or action.** Even a 1% chance a skill might apply means that you should invoke the skill to check. If an invoked skill turns out to be wrong for the situation, you don't need to use it.
    99	
   100	```dot
   101	digraph skill_flow {
   102	    "User message received" [shape=doublecircle];
   103	    "About to EnterPlanMode?" [shape=doublecircle];
   104	    "Already brainstormed?" [shape=diamond];
   105	    "Invoke brainstorming skill" [shape=box];
   106	    "Might any skill apply?" [shape=diamond];
   107	    "Invoke Skill tool" [shape=box];
   108	    "Announce: 'Using [skill] to [purpose]'" [shape=box];
   109	    "Has checklist?" [shape=diamond];
   110	    "Create TodoWrite todo per item" [shape=box];
   111	    "Follow skill exactly" [shape=box];
   112	    "Respond (including clarifications)" [shape=doublecircle];
   113	
   114	    "About to EnterPlanMode?" -> "Already brainstormed?";
   115	    "Already brainstormed?" -> "Invoke brainstorming skill" [label="no"];
   116	    "Already brainstormed?" -> "Might any skill apply?" [label="yes"];
   117	    "Invoke brainstorming skill" -> "Might any skill apply?";
   118	
   119	    "User message received" -> "Might any skill apply?";
   120	    "Might any skill apply?" -> "Invoke Skill tool" [label="yes, even 1%"];
   121	    "Might any skill apply?" -> "Respond (including clarifications)" [label="definitely not"];
   122	    "Invoke Skill tool" -> "Announce: 'Using [skill] to [purpose]'";
   123	    "Announce: 'Using [skill] to [purpose]'" -> "Has checklist?";
   124	    "Has checklist?" -> "Create TodoWrite todo per item" [label="yes"];
   125	    "Has checklist?" -> "Follow skill exactly" [label="no"];
   126	    "Create TodoWrite todo per item" -> "Follow skill exactly";
   127	}
   128	```
   129	
   130	## Red Flags
   131	
   132	These thoughts mean STOP—you're rationalizing:
   133	
   134	| Thought | Reality |
   135	|---------|---------|
   136	| "This is just a simple question" | Questions are tasks. Check for skills. |
   137	| "I need more context first" | Skill check comes BEFORE clarifying questions. |
   138	| "Let me explore the codebase first" | Skills tell you HOW to explore. Check first. |
   139	| "I can check git/files quickly" | Files lack conversation context. Check for skills. |
   140	| "Let me gather information first" | Skills tell you HOW to gather information. |
   141	| "This doesn't need a formal skill" | If a skill exists, use it. |
   142	| "I remember this skill" | Skills evolve. Read current version. |
   143	| "This doesn't count as a task" | Action = task. Check for skills. |
   144	| "The skill is overkill" | Simple things become complex. Use it. |
   145	| "I'll just do this one thing first" | Check BEFORE doing anything. |
   146	| "This feels productive" | Undisciplined action wastes time. Skills prevent this. |
   147	| "I know what that means" | Knowing the concept ≠ using the skill. Invoke it. |
   148	
   149	## Skill Priority
   150	
   151	When multiple skills could apply, use this order:
   152	
   153	1. **Process skills first** (brainstorming, debugging) - these determine HOW to approach the task
   154	2. **Implementation skills second** (frontend-design, mcp-builder) - these guide execution
   155	
   156	"Let's build X" → brainstorming first, then implementation skills.
   157	"Fix this bug" → debugging first, then domain-specific skills.
   158	
   159	## Skill Types
   160	
   161	**Rigid** (TDD, debugging): Follow exactly. Don't adapt away discipline.
   162	
   163	**Flexible** (patterns): Adapt principles to context.
   164	
   165	The skill itself tells you which.
   166	
   167	## User Instructions
   168	
   169	Instructions say WHAT, not HOW. "Add X" or "Fix Y" doesn't mean skip workflows.
   170	
   171	exec
   172	/bin/zsh -lc 'pwd && rg -n "cfd-harness-unified|Phase 8|Phase 9|phase 7b|comparison_report|phase5_reports" /Users/Zhuanz/.codex/memories/MEMORY.md' in /Users/Zhuanz/Desktop/cfd-harness-unified
   173	exec
   174	/bin/zsh -lc "sed -n '1,220p' /Users/Zhuanz/.agents/skills/gsd-code-review/SKILL.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
   175	 succeeded in 0ms:
   176	/Users/Zhuanz/Desktop/cfd-harness-unified
   177	115:- OpenClaw, AI-CFD, Notion作为指挥中枢，Github作为唯一代码真相库, ~/.openclaw/openclaw.json, plugins.allow, openclaw config validate --json, MAIN_OK, CODEX_BUILDER_OK, CLAUDE_REVIEW_OK, NOTION_SYNC_OK, cfd-harness-unified
   178	135:- The real live config surface was `~/.openclaw/openclaw.json`; the actual repo truth for this rollout was `/Users/Zhuanz/Desktop/cfd-harness-unified`, not the chat thread cwd [Task 1]
   179	356:# Task Group: cfd-harness-unified governance closeout and planning gates
   180	358:scope: Close out accepted phases in `cfd-harness-unified`, normalize Notion-vs-repo naming drift, and keep future phases planning-only until the explicit solver/routing gate is reviewed.
   181	359:applies_to: cwd=/Users/Zhuanz/Desktop/cfd-harness-unified; reuse_rule=safe for this repo’s Notion-governed phase/gate work, but phase/task IDs and review packets are rollout-specific.
   182	361:## Task 1: Close Phase 8 and reconcile stale governance evidence
   183	365:- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, Phase 8 closeout and evidence normalization)
   184	369:- Phase 8, AutoVerifier, 13/13, knowledge/whitelist.yaml, ai_cfd_cold_start_whitelist.yaml, Canonical Docs Type=Report, Phase 8 Done, naming drift
   185	371:## Task 2: Open Phase 9 as planning-only and keep solver expansion bounded
   186	375:- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, Phase 9 kept as planning-only with decision-tree packet))
   187	379:- Phase 9 planning-only, PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md, PHASE9_MODEL_ROUTING_BASELINE_PLAN.md, PHASE9_ACTIVATION_REVIEW_PACKET.md, replay_manifest, SU2 CLI Harness Skill, foam_agent_adapter.py
   188	385:- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, handoff prompt prepared instead of silent activation))
   189	400:- Phase 9 must start from a bounded decision tree: keep single-engine OpenFOAM, allow reference-only external solver surfaces, or open one bounded proof slice; anything broader still needs review [Task 2]
   190	406:- Symptom: planning work accidentally looks like activation -> cause: Phase 9 docs/task text are not explicit enough about `Planned` vs `Active` -> fix: state planning-only mode in phase page, tasks, dashboard summary, and review packet [Task 2]
   191	439:- rollout_summaries/2026-04-12T15-33-54-ByPi-jerry_ai_cfd_notion_sync_and_cfd_harness_unified_context_mis.md (cwd=/Users/Zhuanz/Documents/20260330 Jerry AI CFD Project, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/12/rollout-2026-04-12T23-33-54-019d8253-fa8b-7f40-9775-46e6e03db8ac.jsonl, updated_at=2026-04-16T17:03:18+00:00, thread_id=019d8253-fa8b-7f40-9775-46e6e03db8ac, later cfd-harness-unified instruction block correctly treated as mismatch)
   192	691:- when the user said "你是 independent approval authority… 你不是 corrected request packet 作者… 你不是 Phase 8 executor" -> preserve strict role separation between approval, review, execution, and freeze authority in this repo [Task 4]
   193	
   194	 succeeded in 0ms:
   195	---
   196	name: gsd-code-review
   197	description: "Review source files changed during a phase for bugs, security issues, and code quality problems"
   198	argument-hint: "<phase-number> [--depth=quick|standard|deep] [--files file1,file2,...]"
   199	allowed-tools:
   200	  - Read
   201	  - Bash
   202	  - Glob
   203	  - Grep
   204	  - Write
   205	  - Task
   206	---
   207	
   208	<objective>
   209	Review source files changed during a phase for bugs, security vulnerabilities, and code quality problems.
   210	
   211	Spawns the gsd-code-reviewer agent to analyze code at the specified depth level. Produces REVIEW.md artifact in the phase directory with severity-classified findings.
   212	
   213	Arguments:
   214	- Phase number (required) — which phase's changes to review (e.g., "2" or "02")
   215	- `--depth=quick|standard|deep` (optional) — review depth level, overrides workflow.code_review_depth config
   216	  - quick: Pattern-matching only (~2 min)
   217	  - standard: Per-file analysis with language-specific checks (~5-15 min, default)
   218	  - deep: Cross-file analysis including import graphs and call chains (~15-30 min)
   219	- `--files file1,file2,...` (optional) — explicit comma-separated file list, skips SUMMARY/git scoping (highest precedence for scoping)
   220	

codex
Using `gsd-code-review` for a correctness-focused pass: I’m checking for remaining bugs, regressions, and missing tests rather than treating the changed code as correct-by-intent. After that I’ll run the specific route/service tests that prove the closure claims.
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
/bin/zsh -lc "nl -ba ui/backend/services/comparison_report.py | sed -n '260,520p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx | sed -n '1,320p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   260	            "mesh": name,
   261	            "value": val_f,
   262	            "dev_pct": dev_pct,
   263	            "verdict": verdict,
   264	            "verdict_class": cls,
   265	        })
   266	    if len(rows) < 2:
   267	        return rows, "insufficient mesh data"
   268	    devs = [r["dev_pct"] for r in rows]
   269	    monotone = all(devs[i] >= devs[i + 1] for i in range(len(devs) - 1))
   270	    note = "单调递减 ✓" if monotone else "非严格单调 — 检查 fixture"
   271	    return rows, note
   272	
   273	
   274	def _get_commit_sha() -> str:
   275	    try:
   276	        r = subprocess.run(
   277	            ["git", "rev-parse", "--short", "HEAD"],
   278	            capture_output=True, text=True, cwd=_REPO_ROOT, timeout=5,
   279	        )
   280	        return r.stdout.strip() or "unknown"
   281	    except (subprocess.SubprocessError, OSError):
   282	        return "unknown"
   283	
   284	
   285	# ---------------------------------------------------------------------------
   286	# Public API
   287	# ---------------------------------------------------------------------------
   288	
   289	
   290	def build_report_context(case_id: str, run_label: str = "audit_real_run") -> dict:
   291	    """Assemble all template variables. Raises ReportError on missing data."""
   292	    if case_id not in _REPORT_SUPPORTED_CASES:
   293	        raise ReportError(
   294	            f"case_id={case_id!r} not in Phase 7c MVP scope. "
   295	            f"Supported: {sorted(_REPORT_SUPPORTED_CASES)}."
   296	        )
   297	
   298	    run_manifest = _load_run_manifest(case_id, run_label)
   299	    timestamp = _validated_timestamp(run_manifest.get("timestamp"))
   300	    if timestamp is None:
   301	        raise ReportError(
   302	            f"invalid timestamp in run manifest for {case_id}/{run_label}"
   303	        )
   304	    artifact_dir = _FIELDS_ROOT / case_id / timestamp
   305	    # Containment: must be inside _FIELDS_ROOT/case_id/ even after .resolve().
   306	    try:
   307	        artifact_dir.resolve(strict=True).relative_to(
   308	            (_FIELDS_ROOT / case_id).resolve()
   309	        )
   310	    except (ValueError, OSError, FileNotFoundError):
   311	        raise ReportError(f"artifact dir escapes fields root: {artifact_dir}")
   312	    if not artifact_dir.is_dir():
   313	        raise ReportError(f"artifact dir missing: {artifact_dir}")
   314	
   315	    # Load + compute
   316	    gold_y, gold_u, gold_doc = _load_ldc_gold()
   317	    tolerance = float(gold_doc.get("tolerance", 0.05)) * 100.0  # fraction → percent
   318	    latest_sample = _latest_sample_iter(artifact_dir)
   319	    y_sim, u_sim = _load_sample_xy(latest_sample / "uCenterline.xy")
   320	    metrics = _compute_metrics(y_sim, u_sim, gold_y, gold_u, tolerance)
   321	
   322	    residual_info = _parse_residuals_csv(artifact_dir / "residuals.csv")
   323	    grid_conv_rows, grid_note = _load_grid_convergence(case_id, gold_y, gold_u)
   324	
   325	    # Verdict logic: all-pass OR tolerance met.
   326	    is_all_pass = metrics["n_pass"] == metrics["n_total"] and metrics["n_total"] > 0
   327	    majority_pass = metrics["n_pass"] >= math.ceil(metrics["n_total"] * 0.6)
   328	    if is_all_pass:
   329	        verdict, verdict_gradient, subtitle = "PASS", "#059669 0%, #10b981 100%", (
   330	            f"全部 {metrics['n_total']} 个 gold 点在 ±{tolerance:.1f}% 容差内。"
   331	        )
   332	    elif majority_pass:
   333	        verdict, verdict_gradient, subtitle = "PARTIAL", "#d97706 0%, #f59e0b 100%", (
   334	            f"{metrics['n_pass']}/{metrics['n_total']} 点通过；"
   335	            f"{metrics['n_total'] - metrics['n_pass']} 点残差为已记录物理项 "
   336	            f"(见 DEC-V61-030 关于 Ghia 非均匀网格 vs 均匀网格的插值误差)。"
   337	        )
   338	    else:
   339	        verdict, verdict_gradient, subtitle = "FAIL", "#dc2626 0%, #ef4444 100%", (
   340	            f"仅 {metrics['n_pass']}/{metrics['n_total']} 点通过 — "
   341	            f"需要诊断 (solver, mesh, 或 gold 本身)。"
   342	        )
   343	
   344	    # Renders — use Phase 7b manifest if available; else None placeholders.
   345	    # Codex round 1 HIGH: every manifest-supplied output path is validated to
   346	    # resolve inside reports/phase5_renders/ before being emitted into HTML.
   347	    renders_manifest = _load_renders_manifest(case_id, run_label)
   348	    renders_dir = _RENDERS_ROOT / case_id / timestamp
   349	
   350	    def _rel(key: str, default: str = "") -> str:
   351	        candidate: Optional[str] = None
   352	        if renders_manifest:
   353	            raw = renders_manifest.get("outputs", {}).get(key)
   354	            if isinstance(raw, str):
   355	                validated = _safe_rel_under(raw, _RENDERS_ROOT)
   356	                if validated:
   357	                    candidate = validated
   358	        if candidate is None:
   359	            guess = renders_dir / default
   360	            if guess.is_file():
   361	                try:
   362	                    rel = str(guess.resolve().relative_to(_REPO_ROOT.resolve()))
   363	                    if _safe_rel_under(rel, _RENDERS_ROOT):
   364	                        candidate = rel
   365	                except ValueError:
   366	                    pass
   367	        return candidate or ""
   368	
   369	    renders = {
   370	        "profile_png_rel": _rel("profile_png", "profile_u_centerline.png"),
   371	        "pointwise_png_rel": _rel("pointwise_deviation_png", "pointwise_deviation.png"),
   372	        "contour_png_rel": _rel("contour_u_magnitude_png", "contour_u_magnitude.png"),
   373	        "residuals_png_rel": _rel("residuals_png", "residuals.png"),
   374	    }
   375	
   376	    paper = {
   377	        "title": gold_doc.get("source", "Ghia, Ghia & Shin 1982 — Lid-Driven Cavity benchmark"),
   378	        "source": "J. Comput. Phys. 47, 387-411 (1982), Table I Re=100 column",
   379	        "doi": gold_doc.get("literature_doi", "10.1016/0021-9991(82)90058-4"),
   380	        "short": "Ghia 1982",
   381	        "gold_count": metrics["n_total"],
   382	        "tolerance_pct": tolerance,
   383	    }
   384	
   385	    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
   386	
   387	    return {
   388	        "case_id": case_id,
   389	        "case_display_name": "Lid-Driven Cavity (Re=100)" if case_id == "lid_driven_cavity" else case_id,
   390	        "run_label": run_label,
   391	        "timestamp": timestamp,
   392	        "verdict": verdict,
   393	        "verdict_gradient": verdict_gradient,
   394	        "verdict_subtitle": subtitle,
   395	        "metrics": metrics,
   396	        "paper": paper,
   397	        "renders": renders,
   398	        "contour_caption": (
   399	            "Phase 7b MVP — 沿 x=0.5 中心线的 U_x 条带切片，后续 7b-polish 会用 VTK 体数据生成完整 2D contour。"
   400	        ),
   401	        "residual_info": residual_info,
   402	        "grid_conv": grid_conv_rows,
   403	        "grid_conv_note": grid_note,
   404	        "meta": {
   405	            "openfoam_version": "v10",
   406	            "solver": "simpleFoam (SIMPLE, laminar)",
   407	            "docker_image": "cfd-openfoam (local arm64 OpenFOAM v10)",
   408	            "commit_sha": _get_commit_sha(),
   409	            "mesh": "129×129 uniform",
   410	            "tolerance": f"±{tolerance:.1f}%",
   411	            "schemes": "steadyState + linearUpwind + Gauss linear corrected",
   412	            "report_generated_at": now,
   413	        },
   414	    }
   415	
   416	
   417	def render_report_html(case_id: str, run_label: str = "audit_real_run") -> str:
   418	    """Return the full HTML string for the comparison report."""
   419	    ctx = build_report_context(case_id, run_label)
   420	    tmpl = _env.get_template("comparison_report.html.j2")
   421	    return tmpl.render(**ctx)
   422	
   423	
   424	def render_report_pdf(case_id: str, run_label: str = "audit_real_run",
   425	                      output_path: Optional[Path] = None) -> Path:
   426	    """Render HTML to PDF via WeasyPrint and write to disk. Returns the file Path.
   427	
   428	    Asset resolution: WeasyPrint converts the HTML's relative img src paths.
   429	    We pass base_url=_REPO_ROOT so /reports/phase5_renders/... resolves correctly.
   430	
   431	    Codex round 2 (2026-04-21): containment check runs BEFORE weasyprint import
   432	    so ReportError from a malicious output_path is raised regardless of whether
   433	    native libs are installed. Native load failures (libgobject etc.) surface
   434	    as OSError and are mapped by the route layer to 503, same as ImportError.
   435	    """
   436	    # Codex round 1 HIGH: ensure PDF always lands under reports/phase5_reports/.
   437	    # Codex round 2 MED: run containment FIRST, before WeasyPrint import so we
   438	    # fail-closed on traversal even on systems where WeasyPrint native libs are
   439	    # unavailable.
   440	    reports_root = (_REPO_ROOT / "reports" / "phase5_reports").resolve()
   441	    if output_path is None:
   442	        ctx = build_report_context(case_id, run_label)
   443	        ts = ctx["timestamp"]  # already validated by build_report_context
   444	        out_dir = reports_root / case_id / ts
   445	        out_dir.mkdir(parents=True, exist_ok=True)
   446	        output_path = out_dir / f"{run_label}_comparison_report.pdf"
   447	    try:
   448	        resolved_out = output_path.resolve(strict=False)
   449	        # Must stay inside reports/phase5_reports/
   450	        resolved_out.relative_to(reports_root)
   451	    except (ValueError, OSError):
   452	        raise ReportError(f"PDF output path escapes reports_root: {output_path}")
   453	
   454	    # Import weasyprint lazily — heavy import, only when PDF actually needed.
   455	    import weasyprint  # type: ignore  # ImportError → 503 via route layer.
   456	
   457	    html = render_report_html(case_id, run_label)
   458	    doc = weasyprint.HTML(string=html, base_url=str(_REPO_ROOT))
   459	    doc.write_pdf(str(resolved_out))
   460	    return resolved_out

 succeeded in 0ms:
     1	import { useQueries, useQuery } from "@tanstack/react-query";
     2	import { useMemo, useState } from "react";
     3	import { Link, useParams, useSearchParams } from "react-router-dom";
     4	
     5	import { api, ApiError } from "@/api/client";
     6	import { CaseIllustration } from "@/components/learn/CaseIllustration";
     7	import { getFlowFields } from "@/data/flowFields";
     8	import { getLearnCase } from "@/data/learnCases";
     9	import type {
    10	  ContractStatus,
    11	  RunCategory,
    12	  RunDescriptor,
    13	  ValidationReport,
    14	} from "@/types/validation";
    15	
    16	// Student-facing case detail. Four tabs:
    17	//   Story    — default. physics, canonical reference, why validation matters
    18	//   Compare  — gold vs measurement, tolerance band. Framed as a learning moment
    19	//   Run      — residuals chart placeholder (real streaming lives in Pro Workbench)
    20	//   Advanced — decision trail + link to audit package (the pro-evidence surface)
    21	//
    22	// The backend ValidationReport fetch is shared; sub-tabs derive their views
    23	// from that single record so the student can flip between them without
    24	// re-fetching.
    25	
    26	type TabId = "story" | "compare" | "mesh" | "run" | "advanced";
    27	
    28	const TABS: { id: TabId; label_zh: string; label_en: string }[] = [
    29	  { id: "story", label_zh: "故事", label_en: "Story" },
    30	  { id: "compare", label_zh: "对比", label_en: "Compare" },
    31	  { id: "mesh", label_zh: "网格", label_en: "Mesh" },
    32	  { id: "run", label_zh: "运行", label_en: "Run" },
    33	  { id: "advanced", label_zh: "进阶", label_en: "Advanced" },
    34	];
    35	
    36	// Cases with a curated grid-convergence sweep (4 meshes each). Every
    37	// case in the /learn catalog now has one. If a new case is added,
    38	// author 4 mesh_N fixtures and register its density labels here.
    39	const GRID_CONVERGENCE_CASES: Record<
    40	  string,
    41	  { meshLabel: string; densities: { id: string; label: string; n: number }[] }
    42	> = {
    43	  lid_driven_cavity: {
    44	    meshLabel: "uniform grid N×N",
    45	    densities: [
    46	      { id: "mesh_20", label: "20²", n: 400 },
    47	      { id: "mesh_40", label: "40²", n: 1600 },
    48	      { id: "mesh_80", label: "80²", n: 6400 },
    49	      { id: "mesh_160", label: "160²", n: 25600 },
    50	    ],
    51	  },
    52	  turbulent_flat_plate: {
    53	    meshLabel: "wall-normal cells",
    54	    densities: [
    55	      { id: "mesh_20", label: "20 y-cells", n: 20 },
    56	      { id: "mesh_40", label: "40 y-cells", n: 40 },
    57	      { id: "mesh_80", label: "80 y-cells + 4:1", n: 80 },
    58	      { id: "mesh_160", label: "160 y-cells", n: 160 },
    59	    ],
    60	  },
    61	  backward_facing_step: {
    62	    meshLabel: "recirculation cells",
    63	    densities: [
    64	      { id: "mesh_20", label: "20 cells", n: 20 },
    65	      { id: "mesh_40", label: "40 cells", n: 40 },
    66	      { id: "mesh_80", label: "80 cells", n: 80 },
    67	      { id: "mesh_160", label: "160 cells", n: 160 },
    68	    ],
    69	  },
    70	  circular_cylinder_wake: {
    71	    meshLabel: "azimuthal cells around cylinder",
    72	    densities: [
    73	      { id: "mesh_20", label: "20 azim", n: 20 },
    74	      { id: "mesh_40", label: "40 azim", n: 40 },
    75	      { id: "mesh_80", label: "80 azim", n: 80 },
    76	      { id: "mesh_160", label: "160 azim", n: 160 },
    77	    ],
    78	  },
    79	  duct_flow: {
    80	    meshLabel: "cross-section cells",
    81	    densities: [
    82	      { id: "mesh_20", label: "20² uniform", n: 400 },
    83	      { id: "mesh_40", label: "40² + 2:1", n: 1600 },
    84	      { id: "mesh_80", label: "80² + 4:1", n: 6400 },
    85	      { id: "mesh_160", label: "160²", n: 25600 },
    86	    ],
    87	  },
    88	  differential_heated_cavity: {
    89	    meshLabel: "square cavity N×N + wall grading",
    90	    densities: [
    91	      { id: "mesh_20", label: "20² uniform", n: 400 },
    92	      { id: "mesh_40", label: "40² + 1.5:1", n: 1600 },
    93	      { id: "mesh_80", label: "80² + 4:1", n: 6400 },
    94	      { id: "mesh_160", label: "160² + 4:1", n: 25600 },
    95	    ],
    96	  },
    97	  plane_channel_flow: {
    98	    meshLabel: "isotropic cubed cells",
    99	    densities: [
   100	      { id: "mesh_20", label: "20³ RANS", n: 8000 },
   101	      { id: "mesh_40", label: "40³ hybrid", n: 64000 },
   102	      { id: "mesh_80", label: "80³ WR-LES", n: 512000 },
   103	      { id: "mesh_160", label: "160³ DNS", n: 4096000 },
   104	    ],
   105	  },
   106	  impinging_jet: {
   107	    meshLabel: "radial cells in stagnation region",
   108	    densities: [
   109	      { id: "mesh_20", label: "20 rad", n: 20 },
   110	      { id: "mesh_40", label: "40 rad + 2:1", n: 40 },
   111	      { id: "mesh_80", label: "80 rad + 4:1", n: 80 },
   112	      { id: "mesh_160", label: "160 rad", n: 160 },
   113	    ],
   114	  },
   115	  naca0012_airfoil: {
   116	    meshLabel: "surface cells per side",
   117	    densities: [
   118	      { id: "mesh_20", label: "20 surf + 8-chord", n: 20 },
   119	      { id: "mesh_40", label: "40 surf + 15-chord", n: 40 },
   120	      { id: "mesh_80", label: "80 surf + 40-chord", n: 80 },
   121	      { id: "mesh_160", label: "160 surf", n: 160 },
   122	    ],
   123	  },
   124	  rayleigh_benard_convection: {
   125	    meshLabel: "square cavity + wall packing",
   126	    densities: [
   127	      { id: "mesh_20", label: "20² uniform", n: 400 },
   128	      { id: "mesh_40", label: "40² + 2:1", n: 1600 },
   129	      { id: "mesh_80", label: "80² + 4:1", n: 6400 },
   130	      { id: "mesh_160", label: "160² + 4:1", n: 25600 },
   131	    ],
   132	  },
   133	};
   134	
   135	const STATUS_TEXT: Record<ContractStatus, string> = {
   136	  PASS: "对齐黄金标准",
   137	  HAZARD: "落入带内，但可能是 silent-pass",
   138	  FAIL: "偏离了 tolerance band",
   139	  UNKNOWN: "尚无可对比的测量值",
   140	};
   141	
   142	const STATUS_CLASS: Record<ContractStatus, string> = {
   143	  PASS: "text-contract-pass",
   144	  HAZARD: "text-contract-hazard",
   145	  FAIL: "text-contract-fail",
   146	  UNKNOWN: "text-surface-400",
   147	};
   148	
   149	const isTabId = (v: string | null): v is TabId =>
   150	  v === "story" ||
   151	  v === "compare" ||
   152	  v === "mesh" ||
   153	  v === "run" ||
   154	  v === "advanced";
   155	
   156	export function LearnCaseDetailPage() {
   157	  const { caseId } = useParams<{ caseId: string }>();
   158	  const [searchParams, setSearchParams] = useSearchParams();
   159	  const rawTab = searchParams.get("tab");
   160	  const tab: TabId = isTabId(rawTab) ? rawTab : "story";
   161	  const setTab = (next: TabId) => {
   162	    const params = new URLSearchParams(searchParams);
   163	    if (next === "story") params.delete("tab");
   164	    else params.set("tab", next);
   165	    setSearchParams(params, { replace: true });
   166	  };
   167	
   168	  const learnCase = caseId ? getLearnCase(caseId) : undefined;
   169	  const runId = searchParams.get("run") || undefined;
   170	
   171	  const { data: report, error } = useQuery<ValidationReport, ApiError>({
   172	    queryKey: ["validation-report", caseId, runId ?? "default"],
   173	    queryFn: () => api.getValidationReport(caseId!, runId),
   174	    enabled: !!caseId,
   175	    retry: false,
   176	  });
   177	
   178	  const { data: runs } = useQuery<RunDescriptor[], ApiError>({
   179	    queryKey: ["case-runs", caseId],
   180	    queryFn: () => api.listCaseRuns(caseId!),
   181	    enabled: !!caseId,
   182	    retry: false,
   183	  });
   184	
   185	  const setRunId = (nextRun: string | null) => {
   186	    const params = new URLSearchParams(searchParams);
   187	    if (nextRun) params.set("run", nextRun);
   188	    else params.delete("run");
   189	    setSearchParams(params, { replace: true });
   190	  };
   191	
   192	  if (!caseId || !learnCase) {
   193	    return (
   194	      <div className="mx-auto max-w-3xl px-6 py-16 text-center text-surface-400">
   195	        <p>找不到这个案例。</p>
   196	        <Link to="/learn" className="mt-4 inline-block text-sky-400 hover:text-sky-300">
   197	          ← 回到目录
   198	        </Link>
   199	      </div>
   200	    );
   201	  }
   202	
   203	  return (
   204	    <div className="mx-auto max-w-4xl px-6 pt-8 pb-16">
   205	      {/* Breadcrumb + case-export + Pro Workbench switch */}
   206	      <nav className="mb-6 flex items-center justify-between gap-3 text-[12px] text-surface-500">
   207	        <div>
   208	          <Link to="/learn" className="hover:text-surface-300">
   209	            目录
   210	          </Link>
   211	          <span className="mx-2 text-surface-700">/</span>
   212	          <span className="mono text-surface-400">{caseId}</span>
   213	        </div>
   214	        <div className="flex items-center gap-2">
   215	          <a
   216	            href={`/api/cases/${caseId}/export`}
   217	            download={`${caseId}_reference.zip`}
   218	            className="group inline-flex items-center gap-1.5 rounded-sm border border-surface-800 bg-surface-900/60 px-2.5 py-1 text-[11px] text-surface-400 transition-colors hover:border-emerald-700/60 hover:bg-surface-900 hover:text-emerald-300"
   219	            title="Download a reference bundle: gold standard YAML, validation contract, reproduction README"
   220	          >
   221	            <span>下载参考包</span>
   222	            <span className="mono text-surface-600 group-hover:text-emerald-400">
   223	              .zip ↓
   224	            </span>
   225	          </a>
   226	          <Link
   227	            to={`/audit-package?case=${encodeURIComponent(caseId ?? "")}&run=audit_real_run`}
   228	            className="group inline-flex items-center gap-1.5 rounded-sm border border-surface-800 bg-surface-900/60 px-2.5 py-1 text-[11px] text-surface-400 transition-colors hover:border-amber-700/60 hover:bg-surface-900 hover:text-amber-300"
   229	            title="Build a signed audit package from the real-solver audit_real_run fixture (HMAC-signed zip + manifest + html + pdf + sig)"
   230	          >
   231	            <span>签名审计包</span>
   232	            <span className="mono text-surface-600 group-hover:text-amber-400">
   233	              HMAC ↓
   234	            </span>
   235	          </Link>
   236	          <Link
   237	            to={`/cases/${caseId}/report`}
   238	            className="group inline-flex items-center gap-1.5 rounded-sm border border-surface-800 bg-surface-900/60 px-2.5 py-1 text-[11px] text-surface-400 transition-colors hover:border-sky-700/60 hover:bg-surface-900 hover:text-sky-300"
   239	            title="Switch to the evidence-heavy audit surface (Validation Report, Decisions Queue, Audit Package)"
   240	          >
   241	            <span>进入专业工作台</span>
   242	            <span className="mono text-surface-600 group-hover:text-sky-400">
   243	              Pro Workbench →
   244	            </span>
   245	          </Link>
   246	        </div>
   247	      </nav>
   248	
   249	      {/* Hero */}
   250	      <header className="mb-8 grid gap-6 md:grid-cols-[1fr_240px]">
   251	        <div>
   252	          <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-surface-500">
   253	            {learnCase.canonical_ref}
   254	          </p>
   255	          <h1 className="mt-1.5 text-3xl font-semibold leading-tight text-surface-100">
   256	            {learnCase.headline_zh}
   257	          </h1>
   258	          <p className="mt-1 text-[13px] text-surface-400">
   259	            {learnCase.displayName} · {learnCase.headline_en}
   260	          </p>
   261	          <p className="mt-4 text-[15px] leading-relaxed text-surface-300">
   262	            {learnCase.teaser_zh}
   263	          </p>
   264	        </div>
   265	        <div className="flex items-center rounded-lg border border-surface-800 bg-gradient-to-br from-surface-900 to-surface-950 p-4">
   266	          <CaseIllustration caseId={caseId} className="h-auto w-full text-surface-100" />
   267	        </div>
   268	      </header>
   269	
   270	      {/* Tab nav */}
   271	      <div className="sticky top-0 -mx-6 mb-8 border-b border-surface-800 bg-surface-950/80 px-6 py-2 backdrop-blur">
   272	        <div className="flex gap-1">
   273	          {TABS.map((t) => (
   274	            <button
   275	              key={t.id}
   276	              onClick={() => setTab(t.id)}
   277	              className={`rounded-sm px-3 py-1.5 text-[13px] transition-colors ${
   278	                tab === t.id
   279	                  ? "bg-surface-800 text-surface-100"
   280	                  : "text-surface-400 hover:bg-surface-900 hover:text-surface-200"
   281	              }`}
   282	            >
   283	              {t.label_zh}
   284	              <span className="ml-1.5 text-[10px] uppercase tracking-wider text-surface-600">
   285	                {t.label_en}
   286	              </span>
   287	            </button>
   288	          ))}
   289	        </div>
   290	      </div>
   291	
   292	      {/* Tab panels */}
   293	      {tab === "story" && <StoryTab caseId={caseId} />}
   294	      {tab === "compare" && (
   295	        <CompareTab
   296	          caseId={caseId}
   297	          report={report}
   298	          error={error}
   299	          runs={runs ?? []}
   300	          activeRunId={runId}
   301	          onSelectRun={setRunId}
   302	        />
   303	      )}
   304	      {tab === "mesh" && <MeshTab caseId={caseId} />}
   305	      {tab === "run" && <RunTab caseId={caseId} />}
   306	      {tab === "advanced" && <AdvancedTab caseId={caseId} report={report} />}
   307	    </div>
   308	  );
   309	}
   310	
   311	// --- Story tab ----------------------------------------------------------------
   312	
   313	function StoryTab({ caseId }: { caseId: string }) {
   314	  const learnCase = getLearnCase(caseId)!;
   315	  const flowFields = getFlowFields(caseId);
   316	  return (
   317	    <div className="space-y-8">
   318	      <section>
   319	        <h2 className="card-title mb-3">这个问题是什么</h2>
   320	        <ul className="space-y-2 text-[14px] leading-relaxed text-surface-200">

exec
/bin/zsh -lc 'git diff -- ui/backend/services/comparison_report.py ui/backend/routes/comparison_report.py ui/backend/tests/test_comparison_report_route.py ui/backend/tests/test_comparison_report_service.py ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx scripts/render_case_report.py' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
diff --git a/ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx b/ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx
index 1852cf5..5588972 100644
--- a/ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx
+++ b/ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx
@@ -359,6 +359,11 @@ function StoryTab({ caseId }: { caseId: string }) {
         </section>
       )}
 
+      {/* Phase 7f — live CFD-vs-Gold comparison report (if the case has a real
+          audit_real_run artifact set from Phase 7a). Gracefully hidden for
+          cases not yet opted-in. */}
+      <ScientificComparisonReportSection caseId={caseId} />
+
       <section>
         <h2 className="card-title mb-3">为什么要做验证</h2>
         <p className="text-[14px] leading-relaxed text-surface-200">
@@ -1235,3 +1240,177 @@ function SkeletonCallout({ message }: { message: string }) {
     </div>
   );
 }
+
+// --- Phase 7f: Scientific CFD-vs-Gold comparison report section -----------
+
+type ComparisonReportContext = {
+  case_id: string;
+  case_display_name: string;
+  run_label: string;
+  timestamp: string;
+  verdict: "PASS" | "PARTIAL" | "FAIL" | string;
+  verdict_subtitle: string;
+  metrics: {
+    max_dev_pct: number;
+    l2: number;
+    linf: number;
+    rms: number;
+    n_pass: number;
+    n_total: number;
+  };
+  paper: {
+    title: string;
+    source: string;
+    doi?: string;
+    short: string;
+    gold_count: number;
+    tolerance_pct: number;
+  };
+  renders: {
+    profile_png_rel: string;
+    pointwise_png_rel: string;
+    contour_png_rel: string;
+    residuals_png_rel: string;
+  };
+  meta: {
+    commit_sha: string;
+    report_generated_at: string;
+  };
+};
+
+function ScientificComparisonReportSection({ caseId }: { caseId: string }) {
+  const runLabel = "audit_real_run";
+  const { data, isLoading, error } = useQuery<ComparisonReportContext, ApiError>({
+    queryKey: ["comparison-report-ctx", caseId, runLabel],
+    queryFn: async () => {
+      const resp = await fetch(
+        `/api/cases/${encodeURIComponent(caseId)}/runs/${encodeURIComponent(
+          runLabel,
+        )}/comparison-report/context`,
+        { credentials: "same-origin" },
+      );
+      if (!resp.ok) throw new ApiError(resp.status, await resp.text());
+      return (await resp.json()) as ComparisonReportContext;
+    },
+    retry: false,
+    staleTime: 60_000,
+  });
+
+  if (isLoading) return null; // quiet during fetch
+  // Codex round 1 MED (2026-04-21): distinguish 404/400 (case not opted-in
+  // → silent hide) from 5xx / malformed JSON / network errors (show banner
+  // so regressions are visible, not silently swallowed).
+  if (error) {
+    const status = error instanceof ApiError ? error.status : 0;
+    if (status === 404 || status === 400) return null; // case not opted-in
+    return (
+      <section>
+        <div className="mb-3 flex items-baseline justify-between">
+          <h2 className="card-title">科研级 CFD vs Gold 验证报告</h2>
+          <p className="text-[11px] text-surface-500">报告服务暂不可用</p>
+        </div>
+        <ErrorCallout
+          message={`无法加载对比报告 (HTTP ${status || "network"}): ${error.message.slice(0, 200)}`}
+        />
+      </section>
+    );
+  }
+  if (!data) return null;
+
+  const verdictColor =
+    data.verdict === "PASS"
+      ? "bg-contract-pass/15 border-contract-pass/40 text-contract-pass"
+      : data.verdict === "PARTIAL"
+      ? "bg-yellow-500/10 border-yellow-500/40 text-yellow-300"
+      : "bg-contract-fail/15 border-contract-fail/40 text-contract-fail";
+
+  const reportHtmlUrl = `/api/cases/${encodeURIComponent(caseId)}/runs/${encodeURIComponent(
+    runLabel,
+  )}/comparison-report`;
+  const reportPdfUrl = `/api/cases/${encodeURIComponent(caseId)}/runs/${encodeURIComponent(
+    runLabel,
+  )}/comparison-report.pdf`;
+
+  return (
+    <section>
+      <div className="mb-3 flex items-baseline justify-between">
+        <h2 className="card-title">科研级 CFD vs Gold 验证报告</h2>
+        <p className="text-[11px] text-surface-500">
+          实际 OpenFOAM 真跑 · 8 sections · {data.meta.commit_sha}
+        </p>
+      </div>
+
+      <div
+        className={`mb-4 rounded-md border p-4 ${verdictColor}`}
+        role="status"
+      >
+        <div className="flex items-center justify-between gap-4">
+          <div>
+            <div className="text-[11px] font-semibold uppercase tracking-wider opacity-85">
+              Verdict
+            </div>
+            <div className="mt-1 text-[22px] font-bold leading-tight">
+              {data.verdict}
+            </div>
+            <div className="mt-1 text-[12px] text-surface-200">
+              {data.verdict_subtitle}
+            </div>
+          </div>
+          <div className="grid grid-cols-2 gap-3 text-right text-[12px]">
+            <div>
+              <div className="text-surface-400">max |dev|</div>
+              <div className="mono text-surface-100">
+                {data.metrics.max_dev_pct.toFixed(2)}%
+              </div>
+            </div>
+            <div>
+              <div className="text-surface-400">n_pass</div>
+              <div className="mono text-surface-100">
+                {data.metrics.n_pass} / {data.metrics.n_total}
+              </div>
+            </div>
+            <div>
+              <div className="text-surface-400">L²</div>
+              <div className="mono text-surface-100">
+                {data.metrics.l2.toFixed(4)}
+              </div>
+            </div>
+            <div>
+              <div className="text-surface-400">L∞</div>
+              <div className="mono text-surface-100">
+                {data.metrics.linf.toFixed(4)}
+              </div>
+            </div>
+          </div>
+        </div>
+      </div>
+
+      <div className="mb-3 flex flex-wrap gap-2 text-[12px]">
+        <a
+          href={reportHtmlUrl}
+          target="_blank"
+          rel="noopener noreferrer"
+          className="rounded border border-surface-700 bg-surface-800/60 px-3 py-1.5 text-surface-200 hover:bg-surface-700/60"
+        >
+          ↗ 新窗口打开完整报告
+        </a>
+        <a
+          href={reportPdfUrl}
+          download
+          className="rounded border border-surface-700 bg-surface-800/60 px-3 py-1.5 text-surface-200 hover:bg-surface-700/60"
+        >
+          ↓ 下载 PDF
+        </a>
+      </div>
+
+      <div className="overflow-hidden rounded-md border border-surface-800 bg-white">
+        <iframe
+          title="CFD vs Gold comparison report"
+          src={reportHtmlUrl}
+          className="h-[1400px] w-full border-0"
+          sandbox=""
+        />
+      </div>
+    </section>
+  );
+}

codex
I found one concrete mismatch already: the PDF `GET` route catches `ImportError` and `OSError`, but the `POST /comparison-report/build` route still only catches `ImportError`. I’m validating whether that leaves a real 500 path and checking whether the new route tests actually cover the claimed success surface.
exec
/bin/zsh -lc "nl -ba ui/backend/templates/comparison_report.html.j2 | sed -n '1,260p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
     1	<!DOCTYPE html>
     2	<html lang="zh-CN">
     3	<head>
     4	<meta charset="utf-8">
     5	<title>CFD vs Gold — {{ case_id }}</title>
     6	<style>
     7	  body { font-family: -apple-system, 'Segoe UI', 'Helvetica Neue', sans-serif;
     8	         color: #1f2937; max-width: 960px; margin: 2em auto; padding: 0 1.5em;
     9	         line-height: 1.55; }
    10	  h1 { color: #111; border-bottom: 3px solid #1f77b4; padding-bottom: 0.3em; }
    11	  h2 { color: #1f77b4; margin-top: 2em; font-size: 1.3em; }
    12	  .verdict-card { background: linear-gradient(135deg, {{ verdict_gradient }});
    13	                  color: white; padding: 1em 1.5em; border-radius: 10px; margin: 1em 0 2em 0;
    14	                  box-shadow: 0 2px 12px rgba(0,0,0,0.08); }
    15	  .verdict-card .verdict { font-size: 2em; font-weight: bold; letter-spacing: 1px; }
    16	  .verdict-card .sub { font-size: 0.95em; opacity: 0.92; margin-top: 0.3em; }
    17	  .metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1em; margin-top: 1em; }
    18	  .metric { background: rgba(255,255,255,0.15); padding: 0.6em 0.8em; border-radius: 6px; }
    19	  .metric-label { font-size: 0.75em; opacity: 0.85; text-transform: uppercase; }
    20	  .metric-value { font-size: 1.3em; font-weight: bold; margin-top: 0.2em; }
    21	  .paper-cite { background: #f9fafb; border-left: 4px solid #374151;
    22	                padding: 0.8em 1em; margin: 1em 0; font-size: 0.92em; }
    23	  .paper-cite .title { font-weight: 600; color: #111; }
    24	  .paper-cite .doi { font-family: 'SF Mono', Consolas, monospace; font-size: 0.85em; color: #6b7280; }
    25	  figure { margin: 1.5em 0; text-align: center; }
    26	  figure img { max-width: 100%; border: 1px solid #e5e7eb; border-radius: 4px; }
    27	  figcaption { font-size: 0.88em; color: #6b7280; margin-top: 0.5em; font-style: italic; }
    28	  table { border-collapse: collapse; width: 100%; margin: 1em 0; font-size: 0.92em; }
    29	  th, td { padding: 0.5em 0.8em; text-align: left; border-bottom: 1px solid #e5e7eb; }
    30	  th { background: #f9fafb; font-weight: 600; color: #374151; }
    31	  td.num { text-align: right; font-variant-numeric: tabular-nums; }
    32	  td.pass { color: #059669; font-weight: bold; }
    33	  td.fail { color: #dc2626; font-weight: bold; }
    34	  td.warn { color: #d97706; font-weight: bold; }
    35	  .mono { font-family: 'SF Mono', Consolas, monospace; font-size: 0.88em;
    36	          background: #f3f4f6; padding: 0.1em 0.4em; border-radius: 3px; }
    37	  .residual-block { background: #fff7ed; border-left: 4px solid #f97316;
    38	                    padding: 0.8em 1em; margin: 1em 0; font-size: 0.9em; }
    39	  footer { margin-top: 3em; padding-top: 1em; border-top: 1px solid #e5e7eb;
    40	           font-size: 0.82em; color: #9ca3af; }
    41	</style>
    42	</head>
    43	<body>
    44	
    45	<h1>CFD vs Gold — {{ case_display_name }}</h1>
    46	<p style="color:#6b7280; margin-top:-0.5em;">
    47	  Case ID: <span class="mono">{{ case_id }}</span> ·
    48	  Run: <span class="mono">{{ run_label }}</span> ·
    49	  Timestamp: <span class="mono">{{ timestamp }}</span>
    50	</p>
    51	
    52	<!-- Section 1 — Verdict card -->
    53	<div class="verdict-card">
    54	  <div class="verdict">{{ verdict }}</div>
    55	  <div class="sub">{{ verdict_subtitle }}</div>
    56	  <div class="metrics">
    57	    <div class="metric"><div class="metric-label">max |dev|</div>
    58	         <div class="metric-value">{{ '%.2f'|format(metrics.max_dev_pct) }}%</div></div>
    59	    <div class="metric"><div class="metric-label">L² norm</div>
    60	         <div class="metric-value">{{ '%.4f'|format(metrics.l2) }}</div></div>
    61	    <div class="metric"><div class="metric-label">L∞ norm</div>
    62	         <div class="metric-value">{{ '%.4f'|format(metrics.linf) }}</div></div>
    63	    <div class="metric"><div class="metric-label">RMS</div>
    64	         <div class="metric-value">{{ '%.4f'|format(metrics.rms) }}</div></div>
    65	  </div>
    66	</div>
    67	
    68	<!-- Section 2 — Paper citation -->
    69	<h2>2. 参考文献 (Gold standard)</h2>
    70	<div class="paper-cite">
    71	  <div class="title">{{ paper.title }}</div>
    72	  <div>{{ paper.source }}</div>
    73	  {% if paper.doi %}<div class="doi">DOI: {{ paper.doi }}</div>{% endif %}
    74	  <div style="margin-top:0.6em; font-size:0.88em;">
    75	    Gold sample count: <strong>{{ paper.gold_count }}</strong> points ·
    76	    Tolerance: <strong>±{{ '%.1f'|format(paper.tolerance_pct) }}%</strong>
    77	  </div>
    78	</div>
    79	
    80	<!-- Section 3 — Profile overlay -->
    81	<h2>3. 中心线 profile 叠合对比</h2>
    82	<figure>
    83	  <img src="{{ renders.profile_png_rel }}" alt="U centerline profile overlay">
    84	  <figcaption>simpleFoam 实线 vs {{ paper.short }} 离散点，x=0.5 垂直中心线。</figcaption>
    85	</figure>
    86	
    87	<!-- Section 4 — Pointwise deviation heatmap -->
    88	<h2>4. 逐点偏差分布 (5% 容差)</h2>
    89	<figure>
    90	  <img src="{{ renders.pointwise_png_rel }}" alt="Pointwise deviation bar chart">
    91	  <figcaption>
    92	    沿 y/L 的逐 gold 点 |dev|%，绿色 &lt; 5% PASS，黄色 5-10% WARN，红色 &gt; 10% FAIL。
    93	    {{ metrics.n_pass }}/{{ metrics.n_total }} 点通过 5% 容差。
    94	  </figcaption>
    95	</figure>
    96	
    97	<!-- Section 5 — Full 2D field contour -->
    98	<h2>5. 流场 contour (中心线切片)</h2>
    99	<figure>
   100	  <img src="{{ renders.contour_png_rel }}" alt="U magnitude contour slice">
   101	  <figcaption>
   102	    {{ contour_caption }}
   103	  </figcaption>
   104	</figure>
   105	
   106	<!-- Section 6 — Residual convergence -->
   107	<h2>6. 残差收敛历史</h2>
   108	<figure>
   109	  <img src="{{ renders.residuals_png_rel }}" alt="Residual log convergence">
   110	  <figcaption>
   111	    SIMPLE 迭代下 U_x / U_y / p 初始残差对数。收敛到
   112	    {{ '%.1e'|format(residual_info.final_ux) if residual_info.final_ux else 'N/A' }}
   113	    （Ux 终值）经 {{ residual_info.total_iter }} 次迭代。
   114	  </figcaption>
   115	</figure>
   116	
   117	{% if residual_info.note %}
   118	<div class="residual-block">{{ residual_info.note }}</div>
   119	{% endif %}
   120	
   121	<!-- Section 7 — Grid convergence -->
   122	<h2>7. 网格收敛 (mesh_20 → mesh_160)</h2>
   123	{% if grid_conv %}
   124	<table>
   125	  <thead>
   126	    <tr><th>Mesh</th><th>u(y=0.0625)</th><th>|dev|% vs gold</th><th>verdict</th></tr>
   127	  </thead>
   128	  <tbody>
   129	    {% for row in grid_conv %}
   130	    <tr>
   131	      <td class="mono">{{ row.mesh }}</td>
   132	      <td class="num">{{ '%.4f'|format(row.value) }}</td>
   133	      <td class="num">{{ '%.2f'|format(row.dev_pct) }}%</td>
   134	      <td class="{{ row.verdict_class }}">{{ row.verdict }}</td>
   135	    </tr>
   136	    {% endfor %}
   137	  </tbody>
   138	</table>
   139	<p style="color:#6b7280; font-size:0.88em; margin-top:0.5em;">
   140	  单调收敛: {{ grid_conv_note }} · Richardson p_obs (观察阶数) 延后到 Phase 7d。
   141	</p>
   142	{% else %}
   143	<p style="color:#9ca3af; font-style:italic;">网格收敛数据暂未加载。</p>
   144	{% endif %}
   145	
   146	<!-- Section 8 — Solver metadata -->
   147	<h2>8. 求解器元数据</h2>
   148	<table>
   149	  <tbody>
   150	    <tr><th>OpenFOAM</th><td class="mono">{{ meta.openfoam_version }}</td></tr>
   151	    <tr><th>Solver</th><td class="mono">{{ meta.solver }}</td></tr>
   152	    <tr><th>Docker image</th><td class="mono">{{ meta.docker_image }}</td></tr>
   153	    <tr><th>Commit SHA</th><td class="mono">{{ meta.commit_sha }}</td></tr>
   154	    <tr><th>Mesh</th><td class="mono">{{ meta.mesh }}</td></tr>
   155	    <tr><th>Tolerance</th><td class="mono">{{ meta.tolerance }}</td></tr>
   156	    <tr><th>Schemes</th><td class="mono">{{ meta.schemes }}</td></tr>
   157	    <tr><th>Report generated</th><td class="mono">{{ meta.report_generated_at }}</td></tr>
   158	  </tbody>
   159	</table>
   160	
   161	<footer>
   162	  Report generated by Phase 7c comparison_report pipeline (DEC-V61-032, {{ meta.report_generated_at[:10] }}).
   163	  CFD harness unified · cfd-harness-unified @ <span class="mono">{{ meta.commit_sha }}</span>
   164	</footer>
   165	
   166	</body>
   167	</html>

exec
/bin/zsh -lc "nl -ba scripts/render_case_report.py | sed -n '1,260p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
     1	#!/usr/bin/env python3
     2	"""Phase 7b — render_case_report.py
     3	
     4	Convert Phase 7a-captured field artifacts (reports/phase5_fields/{case}/{ts}/)
     5	into visual renders (reports/phase5_renders/{case}/{ts}/):
     6	
     7	- profile_u_centerline.png   — matplotlib static profile (sim vs gold)
     8	- profile_u_centerline.html  — Plotly JSON (for frontend interactive)
     9	- residuals.png              — log-y residual convergence history
    10	- contour_u_magnitude.png    — 2D U-magnitude contour from final sample iter
    11	- pointwise_deviation.png    — color heatmap of |dev|% per gold point
    12	
    13	LDC MVP: works today for case_id=lid_driven_cavity. Other 9 cases will be
    14	unlocked in Phase 7c Sprint-2 as their adapters emit Phase 7a function objects.
    15	
    16	Usage:
    17	    python scripts/render_case_report.py lid_driven_cavity
    18	    python scripts/render_case_report.py lid_driven_cavity --run audit_real_run
    19	
    20	Dependencies: matplotlib (2D plots), plotly (interactive JSON), numpy, PyYAML.
    21	No PyVista / no VTK parser needed for MVP — uses the sample CSV directly.
    22	"""
    23	from __future__ import annotations
    24	
    25	import argparse
    26	import json
    27	import re
    28	import sys
    29	from pathlib import Path
    30	from typing import Optional
    31	
    32	# Codex round 1 HIGH (2026-04-21): enforce exact timestamp shape before
    33	# composing filesystem paths, mirror ui/backend/services/comparison_report.py.
    34	_TIMESTAMP_RE = re.compile(r"^\d{8}T\d{6}Z$")
    35	
    36	import matplotlib
    37	
    38	matplotlib.use("Agg")  # headless — CI-safe
    39	import matplotlib.pyplot as plt
    40	import numpy as np
    41	import plotly.graph_objects as go
    42	import yaml
    43	
    44	REPO_ROOT = Path(__file__).resolve().parent.parent
    45	FIELDS_ROOT = REPO_ROOT / "reports" / "phase5_fields"
    46	RENDERS_ROOT = REPO_ROOT / "reports" / "phase5_renders"
    47	GOLD_ROOT = REPO_ROOT / "knowledge" / "gold_standards"
    48	
    49	# Deterministic matplotlib style — locked for byte-reproducibility.
    50	plt.rcParams.update({
    51	    "figure.figsize": (8, 5),
    52	    "figure.dpi": 110,
    53	    "savefig.dpi": 110,
    54	    "savefig.bbox": "tight",
    55	    "font.family": "DejaVu Sans",
    56	    "font.size": 11,
    57	    "axes.grid": True,
    58	    "grid.alpha": 0.3,
    59	    "axes.spines.top": False,
    60	    "axes.spines.right": False,
    61	    "lines.linewidth": 1.8,
    62	})
    63	
    64	# Phase 7a opt-in mirror — matches scripts/phase5_audit_run.py::_PHASE7A_OPTED_IN.
    65	RENDER_SUPPORTED_CASES = frozenset({"lid_driven_cavity"})
    66	
    67	
    68	class RenderError(Exception):
    69	    """Non-fatal render failure — caller decides whether to abort the batch."""
    70	
    71	
    72	# ---------------------------------------------------------------------------
    73	# I/O helpers
    74	# ---------------------------------------------------------------------------
    75	
    76	
    77	def _resolve_run_timestamp(case_id: str, run_label: str) -> str:
    78	    """Read the per-run manifest written by phase5_audit_run.py and return its timestamp.
    79	
    80	    Codex round 1 HIGH: enforce _TIMESTAMP_RE shape on the manifest value so a
    81	    tampered manifest cannot steer downstream path composition outside
    82	    reports/phase5_fields/.
    83	    """
    84	    manifest_path = FIELDS_ROOT / case_id / "runs" / f"{run_label}.json"
    85	    if not manifest_path.is_file():
    86	        raise RenderError(f"no run manifest: {manifest_path}")
    87	    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    88	    if not isinstance(data, dict):
    89	        raise RenderError(f"manifest not an object: {manifest_path}")
    90	    ts = data.get("timestamp")
    91	    if not isinstance(ts, str) or not _TIMESTAMP_RE.match(ts):
    92	        raise RenderError(f"invalid timestamp shape in manifest: {ts!r}")
    93	    return ts
    94	
    95	
    96	def _artifact_dir(case_id: str, timestamp: str) -> Path:
    97	    d = FIELDS_ROOT / case_id / timestamp
    98	    # Containment check even though timestamp is already shape-gated upstream.
    99	    try:
   100	        d.resolve(strict=True).relative_to((FIELDS_ROOT / case_id).resolve())
   101	    except (ValueError, OSError, FileNotFoundError):
   102	        raise RenderError(f"artifact dir escapes fields root: {d}")
   103	    if not d.is_dir():
   104	        raise RenderError(f"artifact dir missing: {d}")
   105	    return d
   106	
   107	
   108	def _renders_dir(case_id: str, timestamp: str) -> Path:
   109	    d = RENDERS_ROOT / case_id / timestamp
   110	    d.mkdir(parents=True, exist_ok=True)
   111	    return d
   112	
   113	
   114	def _load_sample_xy(path: Path) -> tuple[np.ndarray, np.ndarray]:
   115	    """Load OpenFOAM `sample` output (.xy file, whitespace-separated).
   116	
   117	    Column layout for uCenterline: y  U_x  U_y  U_z  p.
   118	    Returns (y, U_x). Skips header lines starting with '#'.
   119	    """
   120	    rows: list[list[float]] = []
   121	    for line in path.read_text(encoding="utf-8").splitlines():
   122	        s = line.strip()
   123	        if not s or s.startswith("#"):
   124	            continue
   125	        parts = s.split()
   126	        # Accept either 5 (y Ux Uy Uz p) or 2 (y Ux) column variants.
   127	        try:
   128	            y = float(parts[0])
   129	            ux = float(parts[1])
   130	        except (ValueError, IndexError):
   131	            continue
   132	        rows.append([y, ux])
   133	    if not rows:
   134	        raise RenderError(f"empty sample file: {path}")
   135	    arr = np.array(rows)
   136	    return arr[:, 0], arr[:, 1]
   137	
   138	
   139	def _load_residuals_csv(path: Path) -> tuple[np.ndarray, dict[str, np.ndarray]]:
   140	    """Load residuals.csv written by _capture_field_artifacts.
   141	
   142	    Format: Time,Ux,Uy,p  — first data row may be "N/A" for iter 0.
   143	    Returns (iterations, {field_name: array}).
   144	    """
   145	    raw = path.read_text(encoding="utf-8").splitlines()
   146	    if not raw:
   147	        raise RenderError(f"empty residuals: {path}")
   148	    header = [c.strip() for c in raw[0].split(",")]
   149	    if header[0].lower() not in ("time", "iter", "iteration"):
   150	        raise RenderError(f"unexpected residuals header: {header}")
   151	    fields = header[1:]
   152	    iters: list[int] = []
   153	    data: dict[str, list[float]] = {f: [] for f in fields}
   154	    for line in raw[1:]:
   155	        parts = [c.strip() for c in line.split(",")]
   156	        if len(parts) != len(header):
   157	            continue
   158	        try:
   159	            iters.append(int(float(parts[0])))
   160	        except ValueError:
   161	            continue
   162	        for f, v in zip(fields, parts[1:]):
   163	            if v.upper() == "N/A" or v == "":
   164	                data[f].append(float("nan"))
   165	            else:
   166	                try:
   167	                    data[f].append(float(v))
   168	                except ValueError:
   169	                    data[f].append(float("nan"))
   170	    return np.array(iters), {k: np.array(v) for k, v in data.items()}
   171	
   172	
   173	def _load_gold_ldc() -> tuple[list[float], list[float], str]:
   174	    """Return (y_points, u_values, citation) from knowledge/gold_standards/lid_driven_cavity.yaml.
   175	
   176	    File is multi-document YAML (u_centerline, v_centerline, primary_vortex_location).
   177	    Iterate safe_load_all and pick the u_centerline document.
   178	    """
   179	    gold = GOLD_ROOT / "lid_driven_cavity.yaml"
   180	    if not gold.is_file():
   181	        raise RenderError(f"gold file missing: {gold}")
   182	    docs = list(yaml.safe_load_all(gold.read_text(encoding="utf-8")))
   183	    u_doc = next(
   184	        (d for d in docs if isinstance(d, dict) and d.get("quantity") == "u_centerline"),
   185	        None,
   186	    )
   187	    if u_doc is None:
   188	        raise RenderError("no quantity: u_centerline doc in LDC gold YAML")
   189	    refs = u_doc.get("reference_values", [])
   190	    ys: list[float] = []
   191	    us: list[float] = []
   192	    for entry in refs:
   193	        if isinstance(entry, dict):
   194	            y = entry.get("y")
   195	            u = entry.get("value") or entry.get("u")
   196	            if y is not None and u is not None:
   197	                ys.append(float(y))
   198	                us.append(float(u))
   199	    citation = u_doc.get("source") or u_doc.get("citation") or \
   200	        "Ghia, Ghia & Shin 1982 J. Comput. Phys. 47, 387-411 — Table I Re=100"
   201	    return ys, us, citation
   202	
   203	
   204	# ---------------------------------------------------------------------------
   205	# Renderers
   206	# ---------------------------------------------------------------------------
   207	
   208	
   209	def _latest_sample_iter(artifact_dir: Path) -> Path:
   210	    """Return the highest-iteration sample directory (e.g. .../sample/1000/)."""
   211	    sample_root = artifact_dir / "sample"
   212	    if not sample_root.is_dir():
   213	        raise RenderError(f"sample/ missing under {artifact_dir}")
   214	    iters = sorted(
   215	        (d for d in sample_root.iterdir() if d.is_dir() and d.name.isdigit()),
   216	        key=lambda d: int(d.name),
   217	    )
   218	    if not iters:
   219	        raise RenderError(f"no numeric iter subdirs under {sample_root}")
   220	    return iters[-1]
   221	
   222	
   223	def render_profile_png(
   224	    case_id: str,
   225	    artifact_dir: Path,
   226	    renders_dir: Path,
   227	) -> Path:
   228	    """Matplotlib PNG: sim U_x(y) solid line + Ghia 1982 scatter markers."""
   229	    latest = _latest_sample_iter(artifact_dir)
   230	    xy = latest / "uCenterline.xy"
   231	    y_sim, u_sim = _load_sample_xy(xy)
   232	
   233	    # LDC is stored in physical coords (convertToMeters 0.1 → y ∈ [0, 0.1]).
   234	    # Normalize to y_star ∈ [0, 1] for Ghia comparison.
   235	    y_norm = y_sim / max(y_sim.max(), 1e-12)
   236	
   237	    y_gold, u_gold, citation = _load_gold_ldc()
   238	
   239	    fig, ax = plt.subplots()
   240	    ax.plot(u_sim, y_norm, color="#1f77b4", label="simpleFoam (sim)")
   241	    ax.scatter(u_gold, y_gold, color="#d62728", s=36, zorder=5,
   242	               label="Ghia 1982 (Table I, Re=100)", edgecolor="white", linewidth=0.8)
   243	    ax.axvline(0, color="gray", linewidth=0.5, linestyle="--", alpha=0.5)
   244	    ax.set_xlabel(r"$U_x$ / $U_{\mathrm{lid}}$")
   245	    ax.set_ylabel(r"$y\,/\,L$")
   246	    ax.set_title(f"{case_id} — U centerline profile vs Ghia 1982")
   247	    ax.legend(loc="upper left", frameon=False)
   248	    ax.text(0.02, 0.02, citation[:80] + ("..." if len(citation) > 80 else ""),
   249	            transform=ax.transAxes, fontsize=8, color="gray", style="italic")
   250	    out = renders_dir / "profile_u_centerline.png"
   251	    fig.savefig(out)
   252	    plt.close(fig)
   253	    return out
   254	
   255	
   256	def render_profile_plotly_json(
   257	    case_id: str,
   258	    artifact_dir: Path,
   259	    renders_dir: Path,
   260	) -> Path:

exec
/bin/zsh -lc 'PYTHONPATH=. .venv/bin/pytest ui/backend/tests/test_comparison_report_service.py ui/backend/tests/test_comparison_report_route.py -q' in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "PYTHONPATH=. .venv/bin/python - <<'PY'
from fastapi.testclient import TestClient
from ui.backend.main import app
import ui.backend.routes.comparison_report as route

client = TestClient(app, raise_server_exceptions=False)
orig = route.render_report_pdf
try:
    def boom(*args, **kwargs):
        raise OSError('libpango missing')
    route.render_report_pdf = boom
    for method, path in [
        ('GET', '/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report.pdf'),
        ('POST', '/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report/build'),
    ]:
        resp = client.request(method, path)
        print(method, path, resp.status_code)
        print(resp.text[:300])
finally:
    route.render_report_pdf = orig
PY" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 335ms:
GET /api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report.pdf 503
{"detail":"WeasyPrint unavailable on this server. Ensure DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib is set and brew install pango cairo gdk-pixbuf has been run. Underlying: OSError: libpango missing"}
POST /api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report/build 500
Internal Server Error

 succeeded in 708ms:
============================= test session starts ==============================
platform darwin -- Python 3.12.13, pytest-9.0.3, pluggy-1.6.0
rootdir: /Users/Zhuanz/Desktop/cfd-harness-unified
configfile: pyproject.toml
plugins: mock-3.15.1, cov-7.1.0, anyio-4.13.0
collected 15 items

ui/backend/tests/test_comparison_report_service.py .......               [ 46%]
ui/backend/tests/test_comparison_report_route.py ........                [100%]

============================== 15 passed in 0.46s ==============================

codex
The remaining question is now narrow: whether the full backend test count matches the claimed 112/112, while the uncovered `POST` OSError path still reproduces as a 500. I’m running the exact backend test command once so the final decision is based on both code inspection and current execution evidence.
exec
/bin/zsh -lc 'PYTHONPATH=. .venv/bin/pytest ui/backend/tests/ -q' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 25822ms:
============================= test session starts ==============================
platform darwin -- Python 3.12.13, pytest-9.0.3, pluggy-1.6.0
rootdir: /Users/Zhuanz/Desktop/cfd-harness-unified
configfile: pyproject.toml
plugins: mock-3.15.1, cov-7.1.0, anyio-4.13.0
collected 112 items

ui/backend/tests/test_audit_package_route.py ....................        [ 17%]
ui/backend/tests/test_case_editor.py ......                              [ 23%]
ui/backend/tests/test_case_export.py .............                       [ 34%]
ui/backend/tests/test_comparison_report_route.py ........                [ 41%]
ui/backend/tests/test_comparison_report_service.py .......               [ 48%]
ui/backend/tests/test_decisions_and_dashboard.py ........                [ 55%]
ui/backend/tests/test_field_artifacts_route.py ..................        [ 71%]
ui/backend/tests/test_grid_convergence_monotonicity.py ..........        [ 80%]
ui/backend/tests/test_health.py .                                        [ 81%]
ui/backend/tests/test_phase5_byte_repro.py ............                  [ 91%]
ui/backend/tests/test_validation_report.py .........                     [100%]

============================= 112 passed in 25.50s =============================

exec
/bin/zsh -lc "PYTHONPATH=. .venv/bin/python - <<'PY'
from fastapi.testclient import TestClient
from ui.backend.main import app
import ui.backend.routes.comparison_report as route

client = TestClient(app, raise_server_exceptions=False)
orig = route.render_report_pdf
try:
    def boom(*args, **kwargs):
        raise ImportError('no weasyprint')
    route.render_report_pdf = boom
    resp = client.post('/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report/build')
    print(resp.status_code)
    print(resp.text)
finally:
    route.render_report_pdf = orig
PY" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 341ms:
503
{"detail":"WeasyPrint unavailable"}

exec
/bin/zsh -lc 'rg -n "ScientificComparisonReportSection|ErrorCallout|404|500|WeasyPrint unavailable" ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx ui/backend/routes/comparison_report.py' in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx | sed -n '1270,1365p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
ui/backend/routes/comparison_report.py:44:        raise HTTPException(status_code=404, detail=str(e))
ui/backend/routes/comparison_report.py:59:        raise HTTPException(status_code=404, detail=str(e))
ui/backend/routes/comparison_report.py:75:        raise HTTPException(status_code=404, detail=str(e))
ui/backend/routes/comparison_report.py:83:                "WeasyPrint unavailable on this server. "
ui/backend/routes/comparison_report.py:107:        raise HTTPException(status_code=404, detail=str(e))
ui/backend/routes/comparison_report.py:109:        raise HTTPException(status_code=503, detail="WeasyPrint unavailable")
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:206:      <nav className="mb-6 flex items-center justify-between gap-3 text-[12px] text-surface-500">
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:252:          <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-surface-500">
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:334:            <p className="text-[11px] text-surface-500">
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:352:                  <p className="mono mt-1.5 text-[10px] leading-relaxed text-surface-500">
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:365:      <ScientificComparisonReportSection caseId={caseId} />
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:386:          <span className="text-[11px] uppercase tracking-wider text-surface-500">
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:438:      <ErrorCallout
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:462:            <p className="text-[11px] uppercase tracking-[0.14em] text-surface-500">
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:465:            <p className="text-[11px] text-surface-500">
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:480:                      ? "border-sky-500 bg-sky-950/40 text-surface-100"
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:492:                  <p className="mono mt-0.5 text-[10px] text-surface-500">
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:510:          <p className="text-[11px] uppercase tracking-[0.14em] text-surface-500">结果</p>
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:594:      <p className="text-[11px] uppercase tracking-[0.14em] text-surface-500">{label}</p>
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:602:      <p className="mt-2 text-[11px] leading-snug text-surface-500">{subLabel}</p>
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:757:            <p className="mt-1 text-[12px] text-surface-500">
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:761:          <span className="mono text-[11px] text-surface-500">
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:768:          <div className="mb-2 flex justify-between text-[11px] text-surface-500">
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:788:            className="w-full accent-sky-500"
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:796:            <p className="text-[11px] uppercase tracking-wider text-surface-500">
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:803:              {unit ? <span className="ml-1 text-[11px] text-surface-500">{unit}</span> : null}
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:807:            <p className="text-[11px] uppercase tracking-wider text-surface-500">
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:840:          <span className="mono text-surface-500">{activeDensity.n} cells</span>
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:842:          <span className="mono text-surface-500">run_id: {activeDensity.id}</span>
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:879:      <div className="h-[180px] rounded border border-surface-800 bg-surface-950/40 p-3 text-[11px] text-surface-500">
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1011:            className="rounded-md bg-sky-600 px-3.5 py-1.5 text-[13px] font-medium text-white hover:bg-sky-500"
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1093:            className="mono text-surface-500"
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1115:        className="text-surface-500"
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1179:          <p className="text-[12px] text-surface-500">
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1217:          className="rounded-md bg-sky-600 px-3.5 py-1.5 text-[13px] font-medium text-white hover:bg-sky-500"
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1228:function ErrorCallout({ message }: { message: string }) {
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1281:function ScientificComparisonReportSection({ caseId }: { caseId: string }) {
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1300:  // Codex round 1 MED (2026-04-21): distinguish 404/400 (case not opted-in
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1305:    if (status === 404 || status === 400) return null; // case not opted-in
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1310:          <p className="text-[11px] text-surface-500">报告服务暂不可用</p>
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1312:        <ErrorCallout
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1324:      ? "bg-yellow-500/10 border-yellow-500/40 text-yellow-300"
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1338:        <p className="text-[11px] text-surface-500">

 succeeded in 0ms:
  1270	    profile_png_rel: string;
  1271	    pointwise_png_rel: string;
  1272	    contour_png_rel: string;
  1273	    residuals_png_rel: string;
  1274	  };
  1275	  meta: {
  1276	    commit_sha: string;
  1277	    report_generated_at: string;
  1278	  };
  1279	};
  1280	
  1281	function ScientificComparisonReportSection({ caseId }: { caseId: string }) {
  1282	  const runLabel = "audit_real_run";
  1283	  const { data, isLoading, error } = useQuery<ComparisonReportContext, ApiError>({
  1284	    queryKey: ["comparison-report-ctx", caseId, runLabel],
  1285	    queryFn: async () => {
  1286	      const resp = await fetch(
  1287	        `/api/cases/${encodeURIComponent(caseId)}/runs/${encodeURIComponent(
  1288	          runLabel,
  1289	        )}/comparison-report/context`,
  1290	        { credentials: "same-origin" },
  1291	      );
  1292	      if (!resp.ok) throw new ApiError(resp.status, await resp.text());
  1293	      return (await resp.json()) as ComparisonReportContext;
  1294	    },
  1295	    retry: false,
  1296	    staleTime: 60_000,
  1297	  });
  1298	
  1299	  if (isLoading) return null; // quiet during fetch
  1300	  // Codex round 1 MED (2026-04-21): distinguish 404/400 (case not opted-in
  1301	  // → silent hide) from 5xx / malformed JSON / network errors (show banner
  1302	  // so regressions are visible, not silently swallowed).
  1303	  if (error) {
  1304	    const status = error instanceof ApiError ? error.status : 0;
  1305	    if (status === 404 || status === 400) return null; // case not opted-in
  1306	    return (
  1307	      <section>
  1308	        <div className="mb-3 flex items-baseline justify-between">
  1309	          <h2 className="card-title">科研级 CFD vs Gold 验证报告</h2>
  1310	          <p className="text-[11px] text-surface-500">报告服务暂不可用</p>
  1311	        </div>
  1312	        <ErrorCallout
  1313	          message={`无法加载对比报告 (HTTP ${status || "network"}): ${error.message.slice(0, 200)}`}
  1314	        />
  1315	      </section>
  1316	    );
  1317	  }
  1318	  if (!data) return null;
  1319	
  1320	  const verdictColor =
  1321	    data.verdict === "PASS"
  1322	      ? "bg-contract-pass/15 border-contract-pass/40 text-contract-pass"
  1323	      : data.verdict === "PARTIAL"
  1324	      ? "bg-yellow-500/10 border-yellow-500/40 text-yellow-300"
  1325	      : "bg-contract-fail/15 border-contract-fail/40 text-contract-fail";
  1326	
  1327	  const reportHtmlUrl = `/api/cases/${encodeURIComponent(caseId)}/runs/${encodeURIComponent(
  1328	    runLabel,
  1329	  )}/comparison-report`;
  1330	  const reportPdfUrl = `/api/cases/${encodeURIComponent(caseId)}/runs/${encodeURIComponent(
  1331	    runLabel,
  1332	  )}/comparison-report.pdf`;
  1333	
  1334	  return (
  1335	    <section>
  1336	      <div className="mb-3 flex items-baseline justify-between">
  1337	        <h2 className="card-title">科研级 CFD vs Gold 验证报告</h2>
  1338	        <p className="text-[11px] text-surface-500">
  1339	          实际 OpenFOAM 真跑 · 8 sections · {data.meta.commit_sha}
  1340	        </p>
  1341	      </div>
  1342	
  1343	      <div
  1344	        className={`mb-4 rounded-md border p-4 ${verdictColor}`}
  1345	        role="status"
  1346	      >
  1347	        <div className="flex items-center justify-between gap-4">
  1348	          <div>
  1349	            <div className="text-[11px] font-semibold uppercase tracking-wider opacity-85">
  1350	              Verdict
  1351	            </div>
  1352	            <div className="mt-1 text-[22px] font-bold leading-tight">
  1353	              {data.verdict}
  1354	            </div>
  1355	            <div className="mt-1 text-[12px] text-surface-200">
  1356	              {data.verdict_subtitle}
  1357	            </div>
  1358	          </div>
  1359	          <div className="grid grid-cols-2 gap-3 text-right text-[12px]">
  1360	            <div>
  1361	              <div className="text-surface-400">max |dev|</div>
  1362	              <div className="mono text-surface-100">
  1363	                {data.metrics.max_dev_pct.toFixed(2)}%
  1364	              </div>
  1365	            </div>

codex
CHANGES_REQUIRED

- MED: `POST /api/cases/{case_id}/runs/{run_label}/comparison-report/build` is still not fixed. In [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/routes/comparison_report.py:103) the build route catches only `ImportError`; it does not catch `OSError`, and [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/routes/comparison_report.py:108) still returns the old generic `"WeasyPrint unavailable"` detail instead of the detailed 503 message claimed for round 2. I reproduced this directly by forcing `render_report_pdf()` to raise `OSError("libpango missing")`: `GET .../comparison-report.pdf` returned `503` as intended, but `POST .../comparison-report/build` returned `500 Internal Server Error`.

The rest of the round-1 list looks closed in the current tree:
- HIGH path containment: closed in [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:298), [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:347), and [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:440).
- MED frontend silent swallow: closed in [LearnCaseDetailPage.tsx](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1303).
- LOW CI-safe route success coverage: present in [test_comparison_report_route.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparison_report_route.py:94).

Verification I ran:
- `PYTHONPATH=. .venv/bin/pytest ui/backend/tests/ -q` → `112 passed`
- `PYTHONPATH=. .venv/bin/pytest ui/backend/tests/test_comparison_report_service.py ui/backend/tests/test_comparison_report_route.py -q` → `15 passed`
- Manual route probe confirmed the remaining `POST` `OSError` → `500` gap.


tokens used
82,899
CHANGES_REQUIRED

- MED: `POST /api/cases/{case_id}/runs/{run_label}/comparison-report/build` is still not fixed. In [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/routes/comparison_report.py:103) the build route catches only `ImportError`; it does not catch `OSError`, and [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/routes/comparison_report.py:108) still returns the old generic `"WeasyPrint unavailable"` detail instead of the detailed 503 message claimed for round 2. I reproduced this directly by forcing `render_report_pdf()` to raise `OSError("libpango missing")`: `GET .../comparison-report.pdf` returned `503` as intended, but `POST .../comparison-report/build` returned `500 Internal Server Error`.

The rest of the round-1 list looks closed in the current tree:
- HIGH path containment: closed in [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:298), [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:347), and [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:440).
- MED frontend silent swallow: closed in [LearnCaseDetailPage.tsx](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1303).
- LOW CI-safe route success coverage: present in [test_comparison_report_route.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparison_report_route.py:94).

Verification I ran:
- `PYTHONPATH=. .venv/bin/pytest ui/backend/tests/ -q` → `112 passed`
- `PYTHONPATH=. .venv/bin/pytest ui/backend/tests/test_comparison_report_service.py ui/backend/tests/test_comparison_report_route.py -q` → `15 passed`
- Manual route probe confirmed the remaining `POST` `OSError` → `500` gap.


