2026-04-21T08:48:31.121969Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-research-deerflow/SKILL.md: missing YAML frontmatter delimited by ---
2026-04-21T08:48:31.121988Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-report-pretext/SKILL.md: missing YAML frontmatter delimited by ---
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
session id: 019daf3a-1c19-7231-a7e0-1cdcb8eec790
--------
user
Phase 7a field-artifacts — Round 3 verification.

Round 2 verdict was CHANGES_REQUIRED with one remaining HIGH:
"GET /api/runs/{run_id}/field-artifacts still trusts the manifest timestamp before walking and hashing files — list_artifacts() only checks timestamp is non-empty. Reproduced with temp manifest using timestamp=../../outside."

Round 3 fix applied (uncommitted working tree):

1. Extracted shared validated resolver _resolve_artifact_dir(case_id, run_label) -> Optional[Path] in ui/backend/services/field_artifacts.py. It:
   - Reads manifest (already limited by parse_run_id traversal defense)
   - Enforces _TIMESTAMP_RE = re.compile(r"^\\d{8}T\\d{6}Z$") — EXACT YYYYMMDDTHHMMSSZ shape. Any other value (including ../../outside, empty, non-string, url-encoded) returns None.
   - Resolves root / case_id / timestamp path, verifies .resolve().relative_to(root.resolve()) succeeds — containment check.
   - Returns None on any failure.

2. Both list_artifacts() AND resolve_artifact_path() now go through _resolve_artifact_dir first. The divergence you flagged is eliminated — there is only one code path for timestamp → on-disk dir.

3. list_artifacts() simplified: if _resolve_artifact_dir returns None → return None (404). No more independent manifest.get(timestamp, "") + artifact_dir composition.

4. resolve_artifact_path() simplified: removes its own duplicate timestamp/root checks; uses the shared resolver then just verifies filename stays under the already-validated artifact_dir.

5. Regression test added: test_list_rejects_malicious_manifest_timestamp. It builds a temp fields_root with:
   - case_dir/runs/audit_real_run.json containing timestamp="../../outside"
   - outside/leaked.csv as the would-be leak target
   Asserts: GET /field-artifacts → 404 (no enumeration), GET /field-artifacts/leaked.csv → 404.

Regression gate: PYTHONPATH=. .venv/bin/pytest ui/backend/tests/ -q → 95/95 passed (was 94/94; 1 new round-3 test). 16 tests in test_field_artifacts_route.py (was 15).

Please verify the round-2 HIGH is now closed and return APPROVED / APPROVED_WITH_COMMENTS / CHANGES_REQUIRED.

If you see any new issue: call it out. Round-1 findings #1, #3, #4 and round-2 HIGH should all be closed; confirm or refute.
codex
I’ll verify this as an independent review, not implement new changes. I’ll first load the relevant repo context and the modified route/service/tests, then run the focused regression gate before giving a verdict.
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
/bin/zsh -lc 'rg -n "cfd-harness-unified|Phase 7a|field-artifacts|PHASE9|SU2 reference-only" /Users/Zhuanz/.codex/memories/MEMORY.md' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
115:- OpenClaw, AI-CFD, Notion作为指挥中枢，Github作为唯一代码真相库, ~/.openclaw/openclaw.json, plugins.allow, openclaw config validate --json, MAIN_OK, CODEX_BUILDER_OK, CLAUDE_REVIEW_OK, NOTION_SYNC_OK, cfd-harness-unified
135:- The real live config surface was `~/.openclaw/openclaw.json`; the actual repo truth for this rollout was `/Users/Zhuanz/Desktop/cfd-harness-unified`, not the chat thread cwd [Task 1]
356:# Task Group: cfd-harness-unified governance closeout and planning gates
358:scope: Close out accepted phases in `cfd-harness-unified`, normalize Notion-vs-repo naming drift, and keep future phases planning-only until the explicit solver/routing gate is reviewed.
359:applies_to: cwd=/Users/Zhuanz/Desktop/cfd-harness-unified; reuse_rule=safe for this repo’s Notion-governed phase/gate work, but phase/task IDs and review packets are rollout-specific.
365:- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, Phase 8 closeout and evidence normalization)
375:- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, Phase 9 kept as planning-only with decision-tree packet))
379:- Phase 9 planning-only, PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md, PHASE9_MODEL_ROUTING_BASELINE_PLAN.md, PHASE9_ACTIVATION_REVIEW_PACKET.md, replay_manifest, SU2 CLI Harness Skill, foam_agent_adapter.py
385:- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, handoff prompt prepared instead of silent activation))
389:- Opus 4.7 activation review, self-dispatch, planning-only, single-engine OpenFOAM, SU2 reference-only, CFX hold, review packet
439:- rollout_summaries/2026-04-12T15-33-54-ByPi-jerry_ai_cfd_notion_sync_and_cfd_harness_unified_context_mis.md (cwd=/Users/Zhuanz/Documents/20260330 Jerry AI CFD Project, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/12/rollout-2026-04-12T23-33-54-019d8253-fa8b-7f40-9775-46e6e03db8ac.jsonl, updated_at=2026-04-16T17:03:18+00:00, thread_id=019d8253-fa8b-7f40-9775-46e6e03db8ac, later cfd-harness-unified instruction block correctly treated as mismatch)

codex
I’m using the repo’s `gsd-code-review` review workflow as the closest local instruction match, scoped to the field-artifacts fix. The memory hit only affects repo/gate context; the actual verdict will come from current files and tests.
exec
/bin/zsh -lc "sed -n '356,390p' /Users/Zhuanz/.codex/memories/MEMORY.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
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

### rollout_summary_files

- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, Phase 9 kept as planning-only with decision-tree packet))

### keywords

- Phase 9 planning-only, PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md, PHASE9_MODEL_ROUTING_BASELINE_PLAN.md, PHASE9_ACTIVATION_REVIEW_PACKET.md, replay_manifest, SU2 CLI Harness Skill, foam_agent_adapter.py

## Task 3: Stop cleanly at the Opus 4.7 activation gate

### rollout_summary_files

- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, handoff prompt prepared instead of silent activation))

### keywords

- Opus 4.7 activation review, self-dispatch, planning-only, single-engine OpenFOAM, SU2 reference-only, CFX hold, review packet


exec
/bin/zsh -lc 'pwd && git status --short && git diff -- ui/backend/services/field_artifacts.py ui/backend/tests/test_field_artifacts_route.py' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
/Users/Zhuanz/Desktop/cfd-harness-unified
 M .planning/STATE.md
 M reports/cylinder_crossflow/report.md
 M reports/deep_acceptance/visual_acceptance_report.html
 M reports/deep_acceptance/visual_acceptance_report_manifest.json
 M reports/differential_heated_cavity/report.md
 M reports/rayleigh_benard_convection/report.md
 M reports/turbulent_flat_plate/report.md
 M scripts/phase5_audit_run.py
 M src/foam_agent_adapter.py
 M ui/backend/routes/field_artifacts.py
 M ui/backend/services/field_artifacts.py
 M ui/backend/services/run_ids.py
 M ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml
 M ui/backend/tests/test_field_artifacts_route.py
 M ui/frontend/public/flow-fields/circular_cylinder_wake/strouhal_curve.png
 M ui/frontend/public/flow-fields/lid_driven_cavity/centerline_profiles.png
 M ui/frontend/public/flow-fields/lid_driven_cavity/stream_function.png
 M ui/frontend/public/flow-fields/plane_channel_flow/wall_profile.png
 M ui/frontend/public/flow-fields/rayleigh_benard_convection/nu_ra_scaling.png
 M ui/frontend/public/flow-fields/turbulent_flat_plate/blasius_profile.png
 M ui/frontend/public/flow-fields/turbulent_flat_plate/cf_comparison.png
?? .claude/
?? .gitignore.patch.stale.1776663560182166739
?? .planning/phases/07a-field-capture/07a-03-SUMMARY.md
?? .planning/phases/07a-field-capture/_integration_evidence.txt
?? knowledge/corrections/
?? reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md
?? reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md
?? reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md
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
?? ui/frontend/vite.config.sandbox.ts.stale.1776667726
?? ui/frontend/vite.config.sandbox.ts.timestamp-1776667276256-33cd5f0862292.mjs
diff --git a/ui/backend/services/field_artifacts.py b/ui/backend/services/field_artifacts.py
index 002634b..5b162fb 100644
--- a/ui/backend/services/field_artifacts.py
+++ b/ui/backend/services/field_artifacts.py
@@ -15,11 +15,18 @@ from __future__ import annotations
 
 import hashlib
 import json
+import re
 from pathlib import Path
 from typing import Optional
 
 from fastapi import HTTPException
 
+# Codex round 2 HIGH (2026-04-21): timestamp shape gate. The manifest is
+# untrusted input (adversary could write an adjacent file with
+# timestamp='../../outside'). Require the exact YYYYMMDDTHHMMSSZ format the
+# driver emits; reject everything else on both LIST and DOWNLOAD paths.
+_TIMESTAMP_RE = re.compile(r"^\d{8}T\d{6}Z$")
+
 from ui.backend.schemas.validation import (
     FieldArtifact,
     FieldArtifactKind,
@@ -48,18 +55,20 @@ def set_fields_root_for_testing(path: Optional[Path]) -> None:
 
 _KIND_ORDER: dict[str, int] = {"vtk": 0, "csv": 1, "residual_log": 2}
 
-# SHA256 cache keyed on (abs_path, st_mtime, st_size) per 07a-RESEARCH.md §2.6.
-_sha_cache: dict[tuple[str, float, int], str] = {}
+# SHA256 cache keyed on (abs_path, st_mtime_ns, st_size).
+# Codex round 1 LOW #4 (2026-04-21): use st_mtime_ns (int) not st_mtime (float)
+# so rapid-write timestamp collisions within a float's precision are avoided.
+_sha_cache: dict[tuple[str, int, int], str] = {}
 
 
 def sha256_of(path: Path) -> str:
     """Compute (or return cached) SHA256 hex digest for `path`.
 
-    Cache key: (absolute_path, st_mtime, st_size). Mtime+size collision would
-    return a stale hash — MVP-accepted risk per 07a-RESEARCH.md §2.6.
+    Cache key: (absolute_path, st_mtime_ns, st_size). Nanosecond-precision
+    mtime catches rapid-write edge cases that float st_mtime would miss.
     """
     st = path.stat()
-    key = (str(path.resolve()), st.st_mtime, st.st_size)
+    key = (str(path.resolve()), st.st_mtime_ns, st.st_size)
     cached = _sha_cache.get(key)
     if cached is not None:
         return cached
@@ -98,34 +107,75 @@ def _read_run_manifest(case_id: str, run_label: str) -> Optional[dict]:
         return None
 
 
-def list_artifacts(run_id: str) -> Optional[FieldArtifactsResponse]:
-    """Build the JSON manifest for a run_id. Returns None if no data exists."""
-    case_id, run_label = parse_run_id(run_id)
+def _resolve_artifact_dir(case_id: str, run_label: str) -> Optional[Path]:
+    """Validated artifact-dir resolver shared by LIST and DOWNLOAD.
+
+    Codex round 2 HIGH (2026-04-21): previously the LIST endpoint read
+    `timestamp` from the manifest and composed a path without validation,
+    letting a malicious manifest `timestamp='../../outside'` cause the
+    endpoint to enumerate + hash files outside reports/phase5_fields/.
+    Both endpoints now go through this resolver.
+
+    Returns the resolved absolute Path on success, or None if:
+    - manifest missing / unreadable
+    - timestamp missing, wrong shape, or contains traversal markers
+    - artifact_dir does not exist
+    - artifact_dir.resolve() escapes reports/phase5_fields/{case_id}/
+    """
     manifest = _read_run_manifest(case_id, run_label)
     if manifest is None:
         return None
     timestamp = manifest.get("timestamp", "")
-    if not timestamp:
+    # Shape gate: accept only YYYYMMDDTHHMMSSZ. Rejects '..', '/', '\\', '.',
+    # url-encoded forms, and any other adversary-supplied value.
+    if not isinstance(timestamp, str) or not _TIMESTAMP_RE.match(timestamp):
         return None
     root = _current_fields_root()
+    try:
+        root_resolved = root.resolve()
+    except (OSError, RuntimeError):
+        return None
     artifact_dir = root / case_id / timestamp
     if not artifact_dir.is_dir():
         return None
+    try:
+        artifact_dir_resolved = artifact_dir.resolve()
+        # Must stay under root/case_id — additional containment check.
+        artifact_dir_resolved.relative_to(root_resolved)
+    except (ValueError, OSError):
+        return None
+    return artifact_dir_resolved
+
+
+def list_artifacts(run_id: str) -> Optional[FieldArtifactsResponse]:
+    """Build the JSON manifest for a run_id. Returns None if no data exists
+    OR if the manifest's `timestamp` fails the shape/traversal gate."""
+    case_id, run_label = parse_run_id(run_id)
+    artifact_dir_resolved = _resolve_artifact_dir(case_id, run_label)
+    if artifact_dir_resolved is None:
+        return None
+    manifest = _read_run_manifest(case_id, run_label)
+    if manifest is None:  # pragma: no cover — resolver already checked
+        return None
+    timestamp = manifest["timestamp"]  # guaranteed valid by resolver
 
     items: list[FieldArtifact] = []
     # Walk the whole tree — kind-classify leaves; skip directories.
-    for p in sorted(artifact_dir.rglob("*")):
+    # Codex round 1 HIGH #1 (2026-04-21): use POSIX relative path as filename
+    # so sample/0/uCenterline.xy, sample/500/uCenterline.xy, sample/1000/... are
+    # unique URLs (previously all collapsed to basename and hashes lied).
+    for p in sorted(artifact_dir_resolved.rglob("*")):
         if not p.is_file():
             continue
         kind = _classify(p.name)
         if kind is None:
             continue
-        # Use basename only in the URL (traversal via URL blocked by route).
+        rel = p.resolve().relative_to(artifact_dir_resolved).as_posix()
         items.append(
             FieldArtifact(
                 kind=kind,
-                filename=p.name,
-                url=f"/api/runs/{run_id}/field-artifacts/{p.name}",
+                filename=rel,
+                url=f"/api/runs/{run_id}/field-artifacts/{rel}",
                 sha256=sha256_of(p),
                 size_bytes=p.stat().st_size,
             )
@@ -144,36 +194,42 @@ def list_artifacts(run_id: str) -> Optional[FieldArtifactsResponse]:
 def resolve_artifact_path(run_id: str, filename: str) -> Path:
     """Return the on-disk path for {run_id}/{filename}, or raise HTTPException 404.
 
-    Traversal defense: reject any filename with path separators or '..';
-    additionally verify `resolved.relative_to(artifact_dir.resolve())`.
+    `filename` may be a POSIX relative path (e.g. `sample/500/uCenterline.xy`)
+    after Codex round 1 HIGH #1 fix. Traversal defense:
+    - reject empty, '.', '..', backslash, url-encoded '..'
+    - reject absolute paths (leading '/')
+    - reject any '..' segment
+    - verify `resolved.relative_to(artifact_dir.resolve())`
     """
-    # Reject anything with path structure or traversal markers.
-    if filename in ("", ".", ".."):
+    from urllib.parse import unquote as _unquote
+
+    if not filename or filename in (".", ".."):
         raise HTTPException(status_code=404, detail="artifact not found")
-    if "/" in filename or "\\" in filename or ".." in filename:
+    decoded = _unquote(filename)
+    if decoded != filename:
+        # Double-encoding attempt — be strict.
         raise HTTPException(status_code=404, detail="artifact not found")
-
-    case_id, run_label = parse_run_id(run_id)
-    manifest = _read_run_manifest(case_id, run_label)
-    if manifest is None:
+    if "\\" in filename or filename.startswith("/"):
         raise HTTPException(status_code=404, detail="artifact not found")
-    timestamp = manifest.get("timestamp", "")
-    if not timestamp:
+    parts = filename.split("/")
+    if any(p in ("", ".", "..") for p in parts):
         raise HTTPException(status_code=404, detail="artifact not found")
 
-    root = _current_fields_root()
-    artifact_dir = root / case_id / timestamp
-    if not artifact_dir.is_dir():
+    case_id, run_label = parse_run_id(run_id)
+    # Codex round 2 HIGH: both LIST and DOWNLOAD go through the shared
+    # timestamp-validated resolver. Download previously had its own checks;
+    # this consolidation removes divergence.
+    artifact_dir_resolved = _resolve_artifact_dir(case_id, run_label)
+    if artifact_dir_resolved is None:
         raise HTTPException(status_code=404, detail="artifact not found")
 
-    # We serve basenames; files may live in subdirs (VTK/x.vtk). Walk and match.
-    # This mirrors audit_package.py's traversal defense.
-    for p in artifact_dir.rglob(filename):
-        try:
-            resolved = p.resolve()
-            resolved.relative_to(artifact_dir.resolve())
-        except (ValueError, OSError):
-            continue
-        if resolved.is_file() and resolved.name == filename:
-            return resolved
-    raise HTTPException(status_code=404, detail="artifact not found")
+    # Compose target and verify it stays inside artifact_dir.
+    target = artifact_dir_resolved / filename
+    try:
+        resolved = target.resolve(strict=True)
+        resolved.relative_to(artifact_dir_resolved)
+    except (ValueError, OSError, FileNotFoundError):
+        raise HTTPException(status_code=404, detail="artifact not found")
+    if not resolved.is_file():
+        raise HTTPException(status_code=404, detail="artifact not found")
+    return resolved
diff --git a/ui/backend/tests/test_field_artifacts_route.py b/ui/backend/tests/test_field_artifacts_route.py
index f24ab36..13b79df 100644
--- a/ui/backend/tests/test_field_artifacts_route.py
+++ b/ui/backend/tests/test_field_artifacts_route.py
@@ -101,15 +101,77 @@ def test_download_residuals_csv_200(client: TestClient) -> None:
 
 
 def test_download_vtk_200(client: TestClient) -> None:
-    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts/lid_driven_cavity_2000.vtk")
+    """VTK file lives at VTK/lid_driven_cavity_2000.vtk — subpath URL (Codex round 1 HIGH #1)."""
+    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts/VTK/lid_driven_cavity_2000.vtk")
     assert r.status_code == 200, r.text
 
 
-def test_download_404_traversal(client: TestClient) -> None:
+def test_download_404_traversal_filename(client: TestClient) -> None:
     r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts/..%2F..%2Fetc%2Fpasswd")
     assert r.status_code == 404, r.text
 
 
+def test_download_404_traversal_runid_literal(client: TestClient) -> None:
+    """Codex round 1 HIGH #2: traversal via run_id literal '..' must be rejected."""
+    r = client.get("/api/runs/..__pwn/field-artifacts/residuals.csv")
+    assert r.status_code in (400, 404), r.text
+
+
+def test_download_404_traversal_runid_urlencoded(client: TestClient) -> None:
+    """Codex round 1 HIGH #2: url-encoded '%2e%2e' traversal must also be rejected."""
+    r = client.get("/api/runs/%2e%2e__pwn/field-artifacts/residuals.csv")
+    assert r.status_code in (400, 404), r.text
+
+
+def test_manifest_400_traversal_runid(client: TestClient) -> None:
+    """Codex round 1 HIGH #2: manifest endpoint also guards run_id segments."""
+    r = client.get("/api/runs/..__pwn/field-artifacts")
+    assert r.status_code in (400, 404), r.text
+
+
+def test_manifest_uses_subpath_when_collision(client: TestClient) -> None:
+    """Codex round 1 HIGH #1: filename field uses POSIX relative path so
+    subdir-nested files don't collide on basename. The fixture VTK lives in
+    a VTK/ subdir; its filename in the manifest must include that subpath."""
+    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts")
+    body = r.json()
+    vtk_names = {a["filename"] for a in body["artifacts"] if a["kind"] == "vtk"}
+    assert "VTK/lid_driven_cavity_2000.vtk" in vtk_names, vtk_names
+
+
+def test_list_rejects_malicious_manifest_timestamp(tmp_path: Path) -> None:
+    """Codex round 2 HIGH: an adversary-written manifest with
+    timestamp='../../outside' must NOT cause the LIST endpoint to enumerate
+    files outside reports/phase5_fields/. Previously download path was
+    guarded but list was not. Both now go through _resolve_artifact_dir."""
+    import json
+    # Build an isolated fields root with a malicious manifest.
+    fields_root = tmp_path / "fields"
+    case_dir = fields_root / "lid_driven_cavity"
+    (case_dir / "runs").mkdir(parents=True)
+    (case_dir / "20260421T000000Z").mkdir(parents=True)  # legit sibling
+    # Also plant a file outside the case to prove containment matters.
+    outside = tmp_path / "outside"
+    outside.mkdir()
+    (outside / "leaked.csv").write_text("secret\n", encoding="utf-8")
+    (case_dir / "runs" / "audit_real_run.json").write_text(
+        json.dumps({"timestamp": "../../outside", "case_id": "lid_driven_cavity",
+                    "run_label": "audit_real_run"}),
+        encoding="utf-8",
+    )
+    set_fields_root_for_testing(fields_root)
+    try:
+        c = TestClient(app)
+        r = c.get(f"/api/runs/{_RUN_ID}/field-artifacts")
+        # Must NOT return 200 with the leaked artifact — timestamp shape gate.
+        assert r.status_code == 404, r.text
+        # Download side also blocked.
+        r2 = c.get(f"/api/runs/{_RUN_ID}/field-artifacts/leaked.csv")
+        assert r2.status_code == 404, r2.text
+    finally:
+        set_fields_root_for_testing(_FIXTURE_ROOT)
+
+
 def test_download_404_missing(client: TestClient) -> None:
     r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts/does_not_exist.csv")
     assert r.status_code == 404, r.text

codex
The diff shows the shared resolver exists and the new malicious timestamp test is present. I’m checking the surrounding route and run-id parsing now, because the remaining risk is usually either path parameter decoding or a second code path bypassing the resolver.
exec
/bin/zsh -lc "nl -ba ui/backend/services/field_artifacts.py | sed -n '1,260p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
     1	"""Phase 7a — field artifact service.
     2	
     3	Reads the per-run manifest at reports/phase5_fields/{case_id}/runs/{run_label}.json
     4	(written by scripts/phase5_audit_run.py::_write_field_artifacts_run_manifest),
     5	enumerates files in the pointed-to timestamp directory, and serves them via
     6	the FastAPI route in ui/backend/routes/field_artifacts.py.
     7	
     8	File-serve pattern mirrors ui/backend/routes/audit_package.py:284-342
     9	(FileResponse + traversal-safe _resolve_bundle_file) per user ratification #1.
    10	
    11	Artifact ordering: sort by (kind_order, filename) with kind_order
    12	vtk=0 < csv=1 < residual_log=2 per user ratification #6.
    13	"""
    14	from __future__ import annotations
    15	
    16	import hashlib
    17	import json
    18	import re
    19	from pathlib import Path
    20	from typing import Optional
    21	
    22	from fastapi import HTTPException
    23	
    24	# Codex round 2 HIGH (2026-04-21): timestamp shape gate. The manifest is
    25	# untrusted input (adversary could write an adjacent file with
    26	# timestamp='../../outside'). Require the exact YYYYMMDDTHHMMSSZ format the
    27	# driver emits; reject everything else on both LIST and DOWNLOAD paths.
    28	_TIMESTAMP_RE = re.compile(r"^\d{8}T\d{6}Z$")
    29	
    30	from ui.backend.schemas.validation import (
    31	    FieldArtifact,
    32	    FieldArtifactKind,
    33	    FieldArtifactsResponse,
    34	)
    35	from ui.backend.services.run_ids import parse_run_id
    36	
    37	# Repo root: 3 levels up from this file (ui/backend/services/field_artifacts.py)
    38	_REPO_ROOT = Path(__file__).resolve().parents[3]
    39	_FIELDS_ROOT = _REPO_ROOT / "reports" / "phase5_fields"
    40	
    41	_FIELDS_ROOT_OVERRIDE: Optional[Path] = None
    42	
    43	
    44	def _current_fields_root() -> Path:
    45	    return _FIELDS_ROOT_OVERRIDE or _FIELDS_ROOT
    46	
    47	
    48	def set_fields_root_for_testing(path: Optional[Path]) -> None:
    49	    """Override the reports/phase5_fields/ root (test-only hook)."""
    50	    global _FIELDS_ROOT_OVERRIDE
    51	    _FIELDS_ROOT_OVERRIDE = path
    52	    # Invalidate sha cache when root changes.
    53	    _sha_cache.clear()
    54	
    55	
    56	_KIND_ORDER: dict[str, int] = {"vtk": 0, "csv": 1, "residual_log": 2}
    57	
    58	# SHA256 cache keyed on (abs_path, st_mtime_ns, st_size).
    59	# Codex round 1 LOW #4 (2026-04-21): use st_mtime_ns (int) not st_mtime (float)
    60	# so rapid-write timestamp collisions within a float's precision are avoided.
    61	_sha_cache: dict[tuple[str, int, int], str] = {}
    62	
    63	
    64	def sha256_of(path: Path) -> str:
    65	    """Compute (or return cached) SHA256 hex digest for `path`.
    66	
    67	    Cache key: (absolute_path, st_mtime_ns, st_size). Nanosecond-precision
    68	    mtime catches rapid-write edge cases that float st_mtime would miss.
    69	    """
    70	    st = path.stat()
    71	    key = (str(path.resolve()), st.st_mtime_ns, st.st_size)
    72	    cached = _sha_cache.get(key)
    73	    if cached is not None:
    74	        return cached
    75	    h = hashlib.sha256()
    76	    with path.open("rb") as fh:
    77	        for chunk in iter(lambda: fh.read(65536), b""):
    78	            h.update(chunk)
    79	    digest = h.hexdigest()
    80	    _sha_cache[key] = digest
    81	    return digest
    82	
    83	
    84	def _classify(filename: str) -> Optional[FieldArtifactKind]:
    85	    """Map a filename suffix to its kind. Returns None for files we don't surface."""
    86	    low = filename.lower()
    87	    if low.endswith(".vtk") or low.endswith(".vtu") or low.endswith(".vtp"):
    88	        return "vtk"
    89	    if low.endswith(".csv") or low.endswith(".xy") or low.endswith(".dat"):
    90	        # residuals.csv (or anything with 'residual' in the name) is a residual_log.
    91	        if low == "residuals.csv" or "residual" in low:
    92	            return "residual_log"
    93	        return "csv"
    94	    if low.startswith("log.") or low.endswith(".log"):
    95	        return "residual_log"
    96	    return None
    97	
    98	
    99	def _read_run_manifest(case_id: str, run_label: str) -> Optional[dict]:
   100	    root = _current_fields_root()
   101	    manifest_path = root / case_id / "runs" / f"{run_label}.json"
   102	    if not manifest_path.is_file():
   103	        return None
   104	    try:
   105	        return json.loads(manifest_path.read_text(encoding="utf-8"))
   106	    except (json.JSONDecodeError, OSError):
   107	        return None
   108	
   109	
   110	def _resolve_artifact_dir(case_id: str, run_label: str) -> Optional[Path]:
   111	    """Validated artifact-dir resolver shared by LIST and DOWNLOAD.
   112	
   113	    Codex round 2 HIGH (2026-04-21): previously the LIST endpoint read
   114	    `timestamp` from the manifest and composed a path without validation,
   115	    letting a malicious manifest `timestamp='../../outside'` cause the
   116	    endpoint to enumerate + hash files outside reports/phase5_fields/.
   117	    Both endpoints now go through this resolver.
   118	
   119	    Returns the resolved absolute Path on success, or None if:
   120	    - manifest missing / unreadable
   121	    - timestamp missing, wrong shape, or contains traversal markers
   122	    - artifact_dir does not exist
   123	    - artifact_dir.resolve() escapes reports/phase5_fields/{case_id}/
   124	    """
   125	    manifest = _read_run_manifest(case_id, run_label)
   126	    if manifest is None:
   127	        return None
   128	    timestamp = manifest.get("timestamp", "")
   129	    # Shape gate: accept only YYYYMMDDTHHMMSSZ. Rejects '..', '/', '\\', '.',
   130	    # url-encoded forms, and any other adversary-supplied value.
   131	    if not isinstance(timestamp, str) or not _TIMESTAMP_RE.match(timestamp):
   132	        return None
   133	    root = _current_fields_root()
   134	    try:
   135	        root_resolved = root.resolve()
   136	    except (OSError, RuntimeError):
   137	        return None
   138	    artifact_dir = root / case_id / timestamp
   139	    if not artifact_dir.is_dir():
   140	        return None
   141	    try:
   142	        artifact_dir_resolved = artifact_dir.resolve()
   143	        # Must stay under root/case_id — additional containment check.
   144	        artifact_dir_resolved.relative_to(root_resolved)
   145	    except (ValueError, OSError):
   146	        return None
   147	    return artifact_dir_resolved
   148	
   149	
   150	def list_artifacts(run_id: str) -> Optional[FieldArtifactsResponse]:
   151	    """Build the JSON manifest for a run_id. Returns None if no data exists
   152	    OR if the manifest's `timestamp` fails the shape/traversal gate."""
   153	    case_id, run_label = parse_run_id(run_id)
   154	    artifact_dir_resolved = _resolve_artifact_dir(case_id, run_label)
   155	    if artifact_dir_resolved is None:
   156	        return None
   157	    manifest = _read_run_manifest(case_id, run_label)
   158	    if manifest is None:  # pragma: no cover — resolver already checked
   159	        return None
   160	    timestamp = manifest["timestamp"]  # guaranteed valid by resolver
   161	
   162	    items: list[FieldArtifact] = []
   163	    # Walk the whole tree — kind-classify leaves; skip directories.
   164	    # Codex round 1 HIGH #1 (2026-04-21): use POSIX relative path as filename
   165	    # so sample/0/uCenterline.xy, sample/500/uCenterline.xy, sample/1000/... are
   166	    # unique URLs (previously all collapsed to basename and hashes lied).
   167	    for p in sorted(artifact_dir_resolved.rglob("*")):
   168	        if not p.is_file():
   169	            continue
   170	        kind = _classify(p.name)
   171	        if kind is None:
   172	            continue
   173	        rel = p.resolve().relative_to(artifact_dir_resolved).as_posix()
   174	        items.append(
   175	            FieldArtifact(
   176	                kind=kind,
   177	                filename=rel,
   178	                url=f"/api/runs/{run_id}/field-artifacts/{rel}",
   179	                sha256=sha256_of(p),
   180	                size_bytes=p.stat().st_size,
   181	            )
   182	        )
   183	    items.sort(key=lambda a: (_KIND_ORDER.get(a.kind, 99), a.filename))
   184	
   185	    return FieldArtifactsResponse(
   186	        run_id=run_id,
   187	        case_id=case_id,
   188	        run_label=run_label,
   189	        timestamp=timestamp,
   190	        artifacts=items,
   191	    )
   192	
   193	
   194	def resolve_artifact_path(run_id: str, filename: str) -> Path:
   195	    """Return the on-disk path for {run_id}/{filename}, or raise HTTPException 404.
   196	
   197	    `filename` may be a POSIX relative path (e.g. `sample/500/uCenterline.xy`)
   198	    after Codex round 1 HIGH #1 fix. Traversal defense:
   199	    - reject empty, '.', '..', backslash, url-encoded '..'
   200	    - reject absolute paths (leading '/')
   201	    - reject any '..' segment
   202	    - verify `resolved.relative_to(artifact_dir.resolve())`
   203	    """
   204	    from urllib.parse import unquote as _unquote
   205	
   206	    if not filename or filename in (".", ".."):
   207	        raise HTTPException(status_code=404, detail="artifact not found")
   208	    decoded = _unquote(filename)
   209	    if decoded != filename:
   210	        # Double-encoding attempt — be strict.
   211	        raise HTTPException(status_code=404, detail="artifact not found")
   212	    if "\\" in filename or filename.startswith("/"):
   213	        raise HTTPException(status_code=404, detail="artifact not found")
   214	    parts = filename.split("/")
   215	    if any(p in ("", ".", "..") for p in parts):
   216	        raise HTTPException(status_code=404, detail="artifact not found")
   217	
   218	    case_id, run_label = parse_run_id(run_id)
   219	    # Codex round 2 HIGH: both LIST and DOWNLOAD go through the shared
   220	    # timestamp-validated resolver. Download previously had its own checks;
   221	    # this consolidation removes divergence.
   222	    artifact_dir_resolved = _resolve_artifact_dir(case_id, run_label)
   223	    if artifact_dir_resolved is None:
   224	        raise HTTPException(status_code=404, detail="artifact not found")
   225	
   226	    # Compose target and verify it stays inside artifact_dir.
   227	    target = artifact_dir_resolved / filename
   228	    try:
   229	        resolved = target.resolve(strict=True)
   230	        resolved.relative_to(artifact_dir_resolved)
   231	    except (ValueError, OSError, FileNotFoundError):
   232	        raise HTTPException(status_code=404, detail="artifact not found")
   233	    if not resolved.is_file():
   234	        raise HTTPException(status_code=404, detail="artifact not found")
   235	    return resolved

exec
/bin/zsh -lc "nl -ba ui/backend/services/run_ids.py | sed -n '1,220p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba ui/backend/routes/field_artifacts.py | sed -n '1,220p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
     1	"""Phase 7a — field artifacts route.
     2	
     3	GET /api/runs/{run_id}/field-artifacts              → JSON manifest
     4	GET /api/runs/{run_id}/field-artifacts/{filename}   → FileResponse
     5	
     6	Pattern mirrors ui/backend/routes/audit_package.py:284-342 (FileResponse +
     7	path-resolver) per user ratification #1. No StaticFiles.
     8	"""
     9	from __future__ import annotations
    10	
    11	from pathlib import Path
    12	
    13	from fastapi import APIRouter, HTTPException
    14	from fastapi.responses import FileResponse
    15	
    16	from ui.backend.schemas.validation import FieldArtifactsResponse
    17	from ui.backend.services.field_artifacts import (
    18	    list_artifacts,
    19	    resolve_artifact_path,
    20	)
    21	
    22	router = APIRouter()
    23	
    24	
    25	# MIME map — explicit per user ratification #1 rationale (no StaticFiles guessing).
    26	_MEDIA_TYPES: dict[str, str] = {
    27	    ".vtk": "application/octet-stream",
    28	    ".vtu": "application/octet-stream",
    29	    ".vtp": "application/octet-stream",
    30	    ".csv": "text/csv",
    31	    ".xy":  "text/plain; charset=utf-8",
    32	    ".dat": "text/plain; charset=utf-8",
    33	    ".log": "text/plain; charset=utf-8",
    34	}
    35	
    36	
    37	def _media_type_for(path: Path) -> str:
    38	    return _MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream")
    39	
    40	
    41	@router.get(
    42	    "/runs/{run_id}/field-artifacts",
    43	    response_model=FieldArtifactsResponse,
    44	    tags=["field-artifacts"],
    45	)
    46	def get_field_artifacts(run_id: str) -> FieldArtifactsResponse:
    47	    """List field artifacts for a given run_id = '{case}__{run_label}'."""
    48	    resp = list_artifacts(run_id)
    49	    if resp is None:
    50	        raise HTTPException(
    51	            status_code=404,
    52	            detail=f"no field artifacts for run_id={run_id!r}",
    53	        )
    54	    return resp
    55	
    56	
    57	@router.get(
    58	    "/runs/{run_id}/field-artifacts/{filename:path}",
    59	    tags=["field-artifacts"],
    60	)
    61	def download_field_artifact(run_id: str, filename: str) -> FileResponse:
    62	    """Serve a single field artifact file. Traversal-safe.
    63	
    64	    The `{filename:path}` converter allows POSIX sub-paths like
    65	    `sample/500/uCenterline.xy` (Codex round 1 HIGH #1 fix — 3 sample
    66	    iteration dirs had basename collision). Traversal is defended in
    67	    resolve_artifact_path.
    68	    """
    69	    path = resolve_artifact_path(run_id, filename)  # raises HTTPException(404)
    70	    return FileResponse(
    71	        path,
    72	        media_type=_media_type_for(path),
    73	        filename=path.name,
    74	    )

 succeeded in 0ms:
     1	"""Phase 7a — run_id parsing helper.
     2	
     3	Per user ratification #5 (2026-04-21): run_id = "{case_id}__{run_label}".
     4	We use rpartition on the last "__" so case_ids with internal underscores
     5	(e.g. 'lid_driven_cavity') still parse correctly (07a-RESEARCH.md §2.7).
     6	"""
     7	from __future__ import annotations
     8	
     9	import re
    10	from urllib.parse import unquote
    11	
    12	from fastapi import HTTPException
    13	
    14	# Identifier pattern for case_id and run_label segments.
    15	# Allow alphanumerics, underscore, hyphen, dot. Explicitly REJECT path
    16	# separators, '..', leading dots, and percent/url-encoded traversal markers.
    17	# Codex round 1 HIGH #2 (2026-04-21): traversal via run_id reproduced with
    18	# '..__pwn' AND '%2e%2e__pwn' — guard both decoded and raw forms.
    19	_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-]*$")
    20	
    21	
    22	def _validate_segment(name: str, kind: str) -> None:
    23	    """Reject traversal markers before building filesystem paths.
    24	
    25	    Rejects: empty, '.', '..', anything containing '/', '\\', '%', or not
    26	    matching the strict identifier pattern. Also rejects URL-decoded forms
    27	    (in case middleware forgot to decode) so '%2e%2e' → '..' is caught.
    28	    """
    29	    if not name or name in (".", ".."):
    30	        raise HTTPException(status_code=400, detail=f"invalid {kind}")
    31	    decoded = unquote(name)
    32	    if decoded != name or decoded in (".", ".."):
    33	        raise HTTPException(status_code=400, detail=f"invalid {kind}")
    34	    if "/" in name or "\\" in name or ".." in name:
    35	        raise HTTPException(status_code=400, detail=f"invalid {kind}")
    36	    if not _SEGMENT_RE.match(name):
    37	        raise HTTPException(status_code=400, detail=f"invalid {kind}")
    38	
    39	
    40	def parse_run_id(run_id: str) -> tuple[str, str]:
    41	    """Parse 'lid_driven_cavity__audit_real_run' → ('lid_driven_cavity', 'audit_real_run').
    42	
    43	    Uses rpartition on '__' so the label is the LAST token; case_id keeps any
    44	    internal underscores. Labels today are simple identifiers without '__';
    45	    rpartition is resilient if that changes.
    46	
    47	    Both case_id and run_label are validated against a strict identifier
    48	    pattern to prevent path-traversal attacks (Codex round 1 HIGH #2).
    49	
    50	    Raises HTTPException(400) on malformed input.
    51	    """
    52	    if "__" not in run_id:
    53	        raise HTTPException(
    54	            status_code=400,
    55	            detail=f"run_id must match '{{case}}__{{label}}': got {run_id!r}",
    56	        )
    57	    case_id, _, run_label = run_id.rpartition("__")
    58	    if not case_id or not run_label:
    59	        raise HTTPException(
    60	            status_code=400,
    61	            detail=f"run_id has empty case_id or label: {run_id!r}",
    62	        )
    63	    _validate_segment(case_id, "case_id")
    64	    _validate_segment(run_label, "run_label")
    65	    return case_id, run_label

exec
/bin/zsh -lc 'PYTHONPATH=. .venv/bin/pytest ui/backend/tests/ -q' in /Users/Zhuanz/Desktop/cfd-harness-unified
codex
The current service no longer composes `root / case_id / timestamp` from an unvalidated timestamp in `list_artifacts()`. Both list and download reach `_resolve_artifact_dir()`, and `parse_run_id()` is strict enough that manifest lookup itself is not a traversal vector.
exec
/bin/zsh -lc "nl -ba ui/backend/schemas/validation.py | sed -n '1,260p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
     1	"""Schemas for case-index, case-detail, and validation-report responses.
     2	
     3	Kept deliberately small in Phase 0 — extended in Phase 1 when the
     4	Case Editor needs the full whitelist-case schema round-tripped.
     5	"""
     6	
     7	from __future__ import annotations
     8	
     9	from typing import Literal
    10	
    11	from pydantic import BaseModel, Field
    12	
    13	
    14	ContractStatus = Literal["PASS", "HAZARD", "FAIL", "UNKNOWN"]
    15	"""Three-state semantics: PASS (within tolerance, no hazard armed),
    16	HAZARD (within tolerance but a silent-pass hazard is armed), FAIL
    17	(outside tolerance OR contract precondition unmet). UNKNOWN when
    18	no measurement is available yet."""
    19	
    20	
    21	RunCategory = Literal[
    22	    "reference",
    23	    "real_incident",
    24	    "under_resolved",
    25	    "wrong_model",
    26	    "grid_convergence",
    27	    "audit_real_run",
    28	]
    29	"""Run category for multi-run validation demos:
    30	- reference: a run that SHOULD pass — curated from literature exact solutions
    31	  or published tables. Lets students see what "done right" looks like.
    32	- real_incident: the actual measurement our adapter produced in a specific
    33	  production incident. Preserved for auditability / decision traceability.
    34	- under_resolved: a run deliberately using insufficient mesh / short settle
    35	  time / low y+ — a teaching run that demonstrates why resolution matters.
    36	- wrong_model: a run using a physically-inappropriate turbulence / physics
    37	  model — demonstrates why model selection matters.
    38	- grid_convergence: a run at a specific mesh density within a convergence
    39	  sweep (run_id convention `mesh_<N>` — e.g. `mesh_20`, `mesh_80`). These
    40	  feed the interactive mesh-density slider; individually they're coarse /
    41	  fine snapshots, collectively they demonstrate asymptotic convergence.
    42	- audit_real_run: a measurement produced by an actual OpenFOAM solver run
    43	  via FoamAgentExecutor — not curated, not synthesized. Audit-grade
    44	  evidence. Distinguished from real_incident: incidents are historical
    45	  artifacts preserved for decision traceability, audit_real_run are the
    46	  current-authoritative solver outputs that back the signed audit
    47	  package. One per case per commit. Phase 5a onward.
    48	"""
    49	
    50	
    51	class RunDescriptor(BaseModel):
    52	    """One row of GET /api/cases/{id}/runs — lightweight list entry."""
    53	
    54	    run_id: str = Field(..., description="stable id within the case")
    55	    label_zh: str = Field(..., description="human label, Chinese primary")
    56	    label_en: str = Field("", description="optional English label")
    57	    description_zh: str = Field(
    58	        "",
    59	        description="what this run represents (what was curated/broken/observed)",
    60	    )
    61	    category: RunCategory
    62	    expected_verdict: ContractStatus = Field(
    63	        "UNKNOWN",
    64	        description="hint only — actual verdict is computed from the measurement",
    65	    )
    66	
    67	
    68	class RunSummary(BaseModel):
    69	    """Per-case run distribution — rendered as a small pill on catalog cards.
    70	
    71	    `total` counts every curated run (reference/real_incident/under_resolved/
    72	    wrong_model). `verdict_counts` breaks those down by expected_verdict,
    73	    letting the UI show "3 runs · 1 PASS · 2 FAIL" without refetching all
    74	    validation-reports."""
    75	
    76	    total: int = 0
    77	    verdict_counts: dict[str, int] = Field(default_factory=dict)
    78	
    79	
    80	class CaseIndexEntry(BaseModel):
    81	    """One row of GET /api/cases."""
    82	
    83	    case_id: str = Field(..., description="whitelist.yaml `id` field")
    84	    name: str = Field(..., description="human-readable case name")
    85	    flow_type: str
    86	    geometry_type: str
    87	    turbulence_model: str
    88	    has_gold_standard: bool
    89	    has_measurement: bool
    90	    run_summary: RunSummary = Field(default_factory=RunSummary)
    91	    contract_status: ContractStatus
    92	
    93	
    94	class GoldStandardReference(BaseModel):
    95	    """The anchor numeric + citation for a case."""
    96	
    97	    quantity: str
    98	    ref_value: float
    99	    unit: str = ""
   100	    tolerance_pct: float = Field(
   101	        ..., description="Fractional tolerance (0.15 = ±15%)"
   102	    )
   103	    citation: str
   104	    doi: str | None = None
   105	
   106	
   107	class Precondition(BaseModel):
   108	    """One physics_contract precondition row."""
   109	
   110	    condition: str
   111	    satisfied: bool
   112	    evidence_ref: str | None = None
   113	    consequence_if_unsatisfied: str | None = None
   114	
   115	
   116	class AuditConcern(BaseModel):
   117	    """An audit concern emitted by `error_attributor` or encoded in
   118	    the gold-standard `contract_status` narrative."""
   119	
   120	    concern_type: str = Field(
   121	        ...,
   122	        description=(
   123	            "Canonical type: COMPATIBLE_WITH_SILENT_PASS_HAZARD, "
   124	            "DEVIATION, PRECONDITION_UNMET, etc."
   125	        ),
   126	    )
   127	    summary: str = Field(..., description="One-line human-readable summary.")
   128	    detail: str | None = None
   129	    decision_refs: list[str] = Field(
   130	        default_factory=list,
   131	        description="IDs of related DEC-ADWM-* / DEC-V61-* records.",
   132	    )
   133	
   134	
   135	class DecisionLink(BaseModel):
   136	    """A chronological entry in the case's decision trail."""
   137	
   138	    decision_id: str
   139	    date: str
   140	    title: str
   141	    autonomous: bool
   142	
   143	
   144	class MeasuredValue(BaseModel):
   145	    """The extracted quantity from a solver run."""
   146	
   147	    value: float
   148	    unit: str = ""
   149	    source: str = Field(
   150	        ...,
   151	        description=(
   152	            "Where the measurement came from: 'slice_metrics.yaml' or "
   153	            "'fixture' or 'decision_record'."
   154	        ),
   155	    )
   156	    run_id: str | None = None
   157	    commit_sha: str | None = None
   158	    measured_at: str | None = None
   159	
   160	
   161	class CaseDetail(BaseModel):
   162	    """GET /api/cases/{case_id} payload."""
   163	
   164	    case_id: str
   165	    name: str
   166	    reference: str | None = None
   167	    doi: str | None = None
   168	    flow_type: str
   169	    geometry_type: str
   170	    compressibility: str | None = None
   171	    steady_state: str | None = None
   172	    solver: str | None = None
   173	    turbulence_model: str
   174	    parameters: dict[str, float | int | str] = Field(default_factory=dict)
   175	    gold_standard: GoldStandardReference | None = None
   176	    preconditions: list[Precondition] = Field(default_factory=list)
   177	    contract_status_narrative: str | None = None
   178	
   179	
   180	class ValidationReport(BaseModel):
   181	    """GET /api/validation-report/{case_id} payload — Screen 4 data."""
   182	
   183	    case: CaseDetail
   184	    gold_standard: GoldStandardReference
   185	    measurement: MeasuredValue | None = None
   186	    contract_status: ContractStatus
   187	    deviation_pct: float | None = Field(
   188	        None,
   189	        description=(
   190	            "(measured − ref) / ref × 100. None when no measurement is "
   191	            "available."
   192	        ),
   193	    )
   194	    within_tolerance: bool | None = None
   195	    tolerance_lower: float | None = None
   196	    tolerance_upper: float | None = None
   197	    audit_concerns: list[AuditConcern] = Field(default_factory=list)
   198	    preconditions: list[Precondition] = Field(default_factory=list)
   199	    decisions_trail: list[DecisionLink] = Field(default_factory=list)
   200	
   201	
   202	# ---------------------------------------------------------------------------
   203	# Phase 7a — Field Artifacts
   204	# ---------------------------------------------------------------------------
   205	
   206	FieldArtifactKind = Literal["vtk", "csv", "residual_log"]
   207	"""Kind of artifact surfaced by GET /api/runs/{run_id}/field-artifacts.
   208	
   209	- vtk: OpenFOAM foamToVTK output (binary, ~1 MB/case for 129x129 LDC)
   210	- csv: sampled profile data (e.g. uCenterline_U_p.xy from OpenFOAM `sets`
   211	  function object)
   212	- residual_log: residuals.csv (derived from OpenFOAM `residuals` function
   213	  object .dat output) or raw log.<solver>
   214	
   215	Phase 7a captures these per audit_real_run; Phase 7b renders them to PNG/HTML.
   216	"""
   217	
   218	
   219	class FieldArtifact(BaseModel):
   220	    """A single field artifact captured by Phase 7a.
   221	
   222	    Paths are served via GET /api/runs/{run_id}/field-artifacts/{filename}
   223	    (separate download endpoint; this struct carries metadata).
   224	    """
   225	
   226	    kind: FieldArtifactKind
   227	    filename: str = Field(..., description="Basename only; no directory segments.")
   228	    url: str = Field(
   229	        ...,
   230	        description="Download URL under /api/runs/{run_id}/field-artifacts/{filename}",
   231	    )
   232	    sha256: str = Field(
   233	        ...,
   234	        pattern=r"^[0-9a-f]{64}$",
   235	        description="Lowercase hex SHA256 of file bytes.",
   236	    )
   237	    size_bytes: int = Field(..., ge=0)
   238	
   239	
   240	class FieldArtifactsResponse(BaseModel):
   241	    """Response for GET /api/runs/{run_id}/field-artifacts."""
   242	
   243	    run_id: str
   244	    case_id: str
   245	    run_label: str
   246	    timestamp: str = Field(
   247	        ...,
   248	        description="YYYYMMDDTHHMMSSZ UTC — resolved via per-run manifest.",
   249	    )
   250	    artifacts: list[FieldArtifact]

exec
/bin/zsh -lc 'rg -n "FieldArtifact|field-artifacts|phase5_fields|timestamp" ui/backend/tests ui/backend/services ui/backend/routes scripts/phase5_audit_run.py' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
scripts/phase5_audit_run.py:14:    reports/phase5_audit/{timestamp}_{case_id}_raw_run.json  (stdout/stderr)
scripts/phase5_audit_run.py:46:FIELDS_DIR = REPO_ROOT / "reports" / "phase5_fields"
scripts/phase5_audit_run.py:94:def _phase7a_timestamp() -> str:
scripts/phase5_audit_run.py:95:    """Shared timestamp format — matches _write_raw_capture."""
scripts/phase5_audit_run.py:100:    case_id: str, run_label: str, timestamp: str
scripts/phase5_audit_run.py:102:    """Write reports/phase5_fields/{case_id}/runs/{run_label}.json so the
scripts/phase5_audit_run.py:103:    backend route can resolve run_label -> timestamp directory in O(1).
scripts/phase5_audit_run.py:110:    artifact_dir = FIELDS_DIR / case_id / timestamp
scripts/phase5_audit_run.py:130:        "timestamp": timestamp,
scripts/phase5_audit_run.py:218:    # Phase 7a — field artifacts reference (manifest path only; NO timestamps
scripts/phase5_audit_run.py:220:    # The manifest at the referenced path contains the timestamp.
scripts/phase5_audit_run.py:236:        "# re-runs (modulo timestamp + commit_sha) is enforced by\n"
scripts/phase5_audit_run.py:276:    # Phase 7a — author the single shared timestamp up front; the executor-side
scripts/phase5_audit_run.py:277:    # _capture_field_artifacts writes to reports/phase5_fields/{case_id}/{ts}/.
scripts/phase5_audit_run.py:280:    ts = _phase7a_timestamp()
scripts/phase5_audit_run.py:286:            spec.metadata["phase7a_timestamp"] = ts
scripts/phase5_audit_run.py:309:            # Deliberately NO timestamp string here (byte-repro): resolve via manifest.
ui/backend/services/field_artifacts.py:3:Reads the per-run manifest at reports/phase5_fields/{case_id}/runs/{run_label}.json
ui/backend/services/field_artifacts.py:5:enumerates files in the pointed-to timestamp directory, and serves them via
ui/backend/services/field_artifacts.py:24:# Codex round 2 HIGH (2026-04-21): timestamp shape gate. The manifest is
ui/backend/services/field_artifacts.py:26:# timestamp='../../outside'). Require the exact YYYYMMDDTHHMMSSZ format the
ui/backend/services/field_artifacts.py:31:    FieldArtifact,
ui/backend/services/field_artifacts.py:32:    FieldArtifactKind,
ui/backend/services/field_artifacts.py:33:    FieldArtifactsResponse,
ui/backend/services/field_artifacts.py:39:_FIELDS_ROOT = _REPO_ROOT / "reports" / "phase5_fields"
ui/backend/services/field_artifacts.py:49:    """Override the reports/phase5_fields/ root (test-only hook)."""
ui/backend/services/field_artifacts.py:60:# so rapid-write timestamp collisions within a float's precision are avoided.
ui/backend/services/field_artifacts.py:84:def _classify(filename: str) -> Optional[FieldArtifactKind]:
ui/backend/services/field_artifacts.py:114:    `timestamp` from the manifest and composed a path without validation,
ui/backend/services/field_artifacts.py:115:    letting a malicious manifest `timestamp='../../outside'` cause the
ui/backend/services/field_artifacts.py:116:    endpoint to enumerate + hash files outside reports/phase5_fields/.
ui/backend/services/field_artifacts.py:121:    - timestamp missing, wrong shape, or contains traversal markers
ui/backend/services/field_artifacts.py:123:    - artifact_dir.resolve() escapes reports/phase5_fields/{case_id}/
ui/backend/services/field_artifacts.py:128:    timestamp = manifest.get("timestamp", "")
ui/backend/services/field_artifacts.py:131:    if not isinstance(timestamp, str) or not _TIMESTAMP_RE.match(timestamp):
ui/backend/services/field_artifacts.py:138:    artifact_dir = root / case_id / timestamp
ui/backend/services/field_artifacts.py:150:def list_artifacts(run_id: str) -> Optional[FieldArtifactsResponse]:
ui/backend/services/field_artifacts.py:152:    OR if the manifest's `timestamp` fails the shape/traversal gate."""
ui/backend/services/field_artifacts.py:160:    timestamp = manifest["timestamp"]  # guaranteed valid by resolver
ui/backend/services/field_artifacts.py:162:    items: list[FieldArtifact] = []
ui/backend/services/field_artifacts.py:175:            FieldArtifact(
ui/backend/services/field_artifacts.py:178:                url=f"/api/runs/{run_id}/field-artifacts/{rel}",
ui/backend/services/field_artifacts.py:185:    return FieldArtifactsResponse(
ui/backend/services/field_artifacts.py:189:        timestamp=timestamp,
ui/backend/services/field_artifacts.py:220:    # timestamp-validated resolver. Download previously had its own checks;
ui/backend/routes/field_artifacts.py:3:GET /api/runs/{run_id}/field-artifacts              → JSON manifest
ui/backend/routes/field_artifacts.py:4:GET /api/runs/{run_id}/field-artifacts/{filename}   → FileResponse
ui/backend/routes/field_artifacts.py:16:from ui.backend.schemas.validation import FieldArtifactsResponse
ui/backend/routes/field_artifacts.py:42:    "/runs/{run_id}/field-artifacts",
ui/backend/routes/field_artifacts.py:43:    response_model=FieldArtifactsResponse,
ui/backend/routes/field_artifacts.py:44:    tags=["field-artifacts"],
ui/backend/routes/field_artifacts.py:46:def get_field_artifacts(run_id: str) -> FieldArtifactsResponse:
ui/backend/routes/field_artifacts.py:58:    "/runs/{run_id}/field-artifacts/{filename:path}",
ui/backend/routes/field_artifacts.py:59:    tags=["field-artifacts"],
ui/backend/services/dashboard.py:72:            date=str(c.timestamp)[:10],
ui/backend/services/dashboard.py:80:        for c in sorted(decisions_snap.cards, key=lambda c: str(c.timestamp))
ui/backend/routes/audit_package.py:178:    # wall-clock timestamp but got an opaque 16-hex token.
ui/backend/services/decisions.py:40:    timestamp: str
ui/backend/services/decisions.py:126:        timestamp=str(fm.get("timestamp") or path.stem[:10]),
ui/backend/tests/fixtures/runs/backward_facing_step/audit_real_run_measurement.yaml:5:# re-runs (modulo timestamp + commit_sha) is enforced by
ui/backend/tests/fixtures/runs/circular_cylinder_wake/audit_real_run_measurement.yaml:5:# re-runs (modulo timestamp + commit_sha) is enforced by
ui/backend/tests/test_field_artifacts_route.py:37:    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts")
ui/backend/tests/test_field_artifacts_route.py:43:    assert body["timestamp"] == "20260421T000000Z"
ui/backend/tests/test_field_artifacts_route.py:47:    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts")
ui/backend/tests/test_field_artifacts_route.py:57:    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts")
ui/backend/tests/test_field_artifacts_route.py:69:    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts")
ui/backend/tests/test_field_artifacts_route.py:76:    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts")
ui/backend/tests/test_field_artifacts_route.py:83:    r = client.get("/api/runs/nonexistent_case__no_run/field-artifacts")
ui/backend/tests/test_field_artifacts_route.py:88:    r = client.get("/api/runs/no_separator_here/field-artifacts")
ui/backend/tests/test_field_artifacts_route.py:96:    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts/residuals.csv")
ui/backend/tests/test_field_artifacts_route.py:105:    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts/VTK/lid_driven_cavity_2000.vtk")
ui/backend/tests/test_field_artifacts_route.py:110:    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts/..%2F..%2Fetc%2Fpasswd")
ui/backend/tests/test_field_artifacts_route.py:116:    r = client.get("/api/runs/..__pwn/field-artifacts/residuals.csv")
ui/backend/tests/test_field_artifacts_route.py:122:    r = client.get("/api/runs/%2e%2e__pwn/field-artifacts/residuals.csv")
ui/backend/tests/test_field_artifacts_route.py:128:    r = client.get("/api/runs/..__pwn/field-artifacts")
ui/backend/tests/test_field_artifacts_route.py:136:    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts")
ui/backend/tests/test_field_artifacts_route.py:142:def test_list_rejects_malicious_manifest_timestamp(tmp_path: Path) -> None:
ui/backend/tests/test_field_artifacts_route.py:144:    timestamp='../../outside' must NOT cause the LIST endpoint to enumerate
ui/backend/tests/test_field_artifacts_route.py:145:    files outside reports/phase5_fields/. Previously download path was
ui/backend/tests/test_field_artifacts_route.py:158:        json.dumps({"timestamp": "../../outside", "case_id": "lid_driven_cavity",
ui/backend/tests/test_field_artifacts_route.py:165:        r = c.get(f"/api/runs/{_RUN_ID}/field-artifacts")
ui/backend/tests/test_field_artifacts_route.py:166:        # Must NOT return 200 with the leaked artifact — timestamp shape gate.
ui/backend/tests/test_field_artifacts_route.py:169:        r2 = c.get(f"/api/runs/{_RUN_ID}/field-artifacts/leaked.csv")
ui/backend/tests/test_field_artifacts_route.py:176:    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts/does_not_exist.csv")
ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/runs/audit_real_run.json:3:  "timestamp": "20260421T000000Z",
ui/backend/tests/test_phase5_byte_repro.py:12:4. `measurement.measured_at` is the only timestamp field.
ui/backend/tests/test_phase5_byte_repro.py:130:        "measurement.measured_at", # ISO timestamp
ui/backend/tests/fixtures/runs/turbulent_flat_plate/audit_real_run_measurement.yaml:5:# re-runs (modulo timestamp + commit_sha) is enforced by
ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml:5:# re-runs (modulo timestamp + commit_sha) is enforced by
ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml:49:  manifest_path_rel: reports/phase5_fields/lid_driven_cavity/runs/audit_real_run.json
ui/backend/tests/fixtures/runs/impinging_jet/audit_real_run_measurement.yaml:5:# re-runs (modulo timestamp + commit_sha) is enforced by
ui/backend/tests/fixtures/runs/rayleigh_benard_convection/audit_real_run_measurement.yaml:5:# re-runs (modulo timestamp + commit_sha) is enforced by
ui/backend/tests/fixtures/runs/naca0012_airfoil/audit_real_run_measurement.yaml:5:# re-runs (modulo timestamp + commit_sha) is enforced by
ui/backend/tests/fixtures/runs/duct_flow/audit_real_run_measurement.yaml:5:# re-runs (modulo timestamp + commit_sha) is enforced by
ui/backend/tests/fixtures/runs/differential_heated_cavity/audit_real_run_measurement.yaml:5:# re-runs (modulo timestamp + commit_sha) is enforced by
ui/backend/tests/fixtures/runs/plane_channel_flow/audit_real_run_measurement.yaml:5:# re-runs (modulo timestamp + commit_sha) is enforced by

 succeeded in 24155ms:
============================= test session starts ==============================
platform darwin -- Python 3.12.13, pytest-9.0.3, pluggy-1.6.0
rootdir: /Users/Zhuanz/Desktop/cfd-harness-unified
configfile: pyproject.toml
plugins: mock-3.15.1, cov-7.1.0, anyio-4.13.0
collected 95 items

ui/backend/tests/test_audit_package_route.py ....................        [ 21%]
ui/backend/tests/test_case_editor.py ......                              [ 27%]
ui/backend/tests/test_case_export.py .............                       [ 41%]
ui/backend/tests/test_decisions_and_dashboard.py ........                [ 49%]
ui/backend/tests/test_field_artifacts_route.py ................          [ 66%]
ui/backend/tests/test_grid_convergence_monotonicity.py ..........        [ 76%]
ui/backend/tests/test_health.py .                                        [ 77%]
ui/backend/tests/test_phase5_byte_repro.py ............                  [ 90%]
ui/backend/tests/test_validation_report.py .........                     [100%]

============================= 95 passed in 23.95s ==============================

codex
The backend suite finished green: `95 passed`, including `test_field_artifacts_route.py` with 16 tests. I’m doing one final bypass scan for alternate imports/callers before I lock the verdict.
exec
/bin/zsh -lc "rg -n \"list_artifacts\\(|resolve_artifact_path\\(|_resolve_artifact_dir\\(|set_fields_root_for_testing\\(\" . --glob '"'!*.pyc'"' --glob '"'!__pycache__/**'"'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
./ui/backend/services/field_artifacts.py:48:def set_fields_root_for_testing(path: Optional[Path]) -> None:
./ui/backend/services/field_artifacts.py:110:def _resolve_artifact_dir(case_id: str, run_label: str) -> Optional[Path]:
./ui/backend/services/field_artifacts.py:150:def list_artifacts(run_id: str) -> Optional[FieldArtifactsResponse]:
./ui/backend/services/field_artifacts.py:154:    artifact_dir_resolved = _resolve_artifact_dir(case_id, run_label)
./ui/backend/services/field_artifacts.py:194:def resolve_artifact_path(run_id: str, filename: str) -> Path:
./ui/backend/services/field_artifacts.py:222:    artifact_dir_resolved = _resolve_artifact_dir(case_id, run_label)
./ui/backend/routes/field_artifacts.py:48:    resp = list_artifacts(run_id)
./ui/backend/routes/field_artifacts.py:69:    path = resolve_artifact_path(run_id, filename)  # raises HTTPException(404)
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:1265:    41	def set_fields_root_for_testing(path: Optional[Path]) -> None:
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:1325:   101	def list_artifacts(run_id: str) -> Optional[FieldArtifactsResponse]:
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:1368:   144	def resolve_artifact_path(run_id: str, filename: str) -> Path:
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:1453:    48	    resp = list_artifacts(run_id)
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:1468:    63	    path = resolve_artifact_path(run_id, filename)  # raises HTTPException(404)
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:1582:    24	    set_fields_root_for_testing(_FIXTURE_ROOT)
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:1584:    26	    set_fields_root_for_testing(None)
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:1910:    set_fields_root_for_testing(root)
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:1918:        set_fields_root_for_testing(None)
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:1939:    set_fields_root_for_testing(root)
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:1943:        print(list_artifacts('..__pwn'))
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:1944:        print(resolve_artifact_path('..__pwn','leak.csv'))
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:1946:        set_fields_root_for_testing(None)
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:1976:    set_fields_root_for_testing(root)
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:1978:        print('service manifest', list_artifacts('..__pwn'))
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:1979:        print('service path', resolve_artifact_path('..__pwn','leak.csv'))
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:1986:        set_fields_root_for_testing(None)
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:2338:resp=list_artifacts(run_id)
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:2344:            p=resolve_artifact_path(run_id, a.filename)
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:2396:    set_fields_root_for_testing(root)
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:2403:        set_fields_root_for_testing(None)
./ui/backend/tests/test_field_artifacts_route.py:24:    set_fields_root_for_testing(_FIXTURE_ROOT)
./ui/backend/tests/test_field_artifacts_route.py:26:    set_fields_root_for_testing(None)
./ui/backend/tests/test_field_artifacts_route.py:162:    set_fields_root_for_testing(fields_root)
./ui/backend/tests/test_field_artifacts_route.py:172:        set_fields_root_for_testing(_FIXTURE_ROOT)
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1199:ui/backend/services/field_artifacts.py:103:def list_artifacts(run_id: str) -> Optional[FieldArtifactsResponse]:
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1207:ui/backend/services/field_artifacts.py:150:def resolve_artifact_path(run_id: str, filename: str) -> Path:
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1265:ui/backend/routes/field_artifacts.py:48:    resp = list_artifacts(run_id)
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1269:ui/backend/routes/field_artifacts.py:69:    path = resolve_artifact_path(run_id, filename)  # raises HTTPException(404)
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1393:     path = resolve_artifact_path(run_id, filename)  # raises HTTPException(404)
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1400:@@ -48,18 +48,20 @@ def set_fields_root_for_testing(path: Optional[Path]) -> None:
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1426:@@ -114,18 +116,22 @@ def list_artifacts(run_id: str) -> Optional[FieldArtifactsResponse]:
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1452:@@ -144,13 +150,25 @@ def list_artifacts(run_id: str) -> Optional[FieldArtifactsResponse]:
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1453: def resolve_artifact_path(run_id: str, filename: str) -> Path:
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1483:@@ -160,20 +178,29 @@ def resolve_artifact_path(run_id: str, filename: str) -> Path:
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1862:    48	    resp = list_artifacts(run_id)
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1883:    69	    path = resolve_artifact_path(run_id, filename)  # raises HTTPException(404)
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1931:    41	def set_fields_root_for_testing(path: Optional[Path]) -> None:
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1993:   103	def list_artifacts(run_id: str) -> Optional[FieldArtifactsResponse]:
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:2040:   150	def resolve_artifact_path(run_id: str, filename: str) -> Path:
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:2122:    24	    set_fields_root_for_testing(_FIXTURE_ROOT)
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:2124:    26	    set_fields_root_for_testing(None)
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:2952:resp = list_artifacts(run_id)
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:2983:    set_fields_root_for_testing(root)
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:2985:        resp = list_artifacts('lid_driven_cavity__audit_real_run')
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:2991:            resolve_artifact_path('lid_driven_cavity__audit_real_run', 'residuals.csv')
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:2996:        set_fields_root_for_testing(None)
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3178:@@ -48,18 +48,20 @@ def set_fields_root_for_testing(path: Optional[Path]) -> None:
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3204:@@ -114,18 +116,22 @@ def list_artifacts(run_id: str) -> Optional[FieldArtifactsResponse]:
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3230:@@ -144,13 +150,25 @@ def list_artifacts(run_id: str) -> Optional[FieldArtifactsResponse]:
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3231: def resolve_artifact_path(run_id: str, filename: str) -> Path:
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3261:@@ -160,20 +178,29 @@ def resolve_artifact_path(run_id: str, filename: str) -> Path:
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3307:- HIGH: `GET /api/runs/{run_id}/field-artifacts` still trusts the manifest `timestamp` before walking and hashing files. In [field_artifacts.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/field_artifacts.py:109), `list_artifacts()` only checks that `timestamp` is non-empty, then builds `artifact_dir = root / case_id / timestamp` and recursively hashes classified files. The download path validates `timestamp` later, but the listing path does not. I reproduced this with a temp manifest using `timestamp="../../outside"`: listing returned an outside `residuals.csv` with size/hash, while download correctly returned `404`.
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3309:This is a round-1 miss / incomplete application of the round-1 HIGH #2 hardening, not a regression from the basename-collision fix. The fix should share the same validated artifact-dir resolver between `list_artifacts()` and `resolve_artifact_path()`, ideally enforcing the generated timestamp shape like `YYYYMMDDTHHMMSSZ`, and add a regression test for malicious manifest timestamps on the manifest endpoint.
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3325:- HIGH: `GET /api/runs/{run_id}/field-artifacts` still trusts the manifest `timestamp` before walking and hashing files. In [field_artifacts.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/field_artifacts.py:109), `list_artifacts()` only checks that `timestamp` is non-empty, then builds `artifact_dir = root / case_id / timestamp` and recursively hashes classified files. The download path validates `timestamp` later, but the listing path does not. I reproduced this with a temp manifest using `timestamp="../../outside"`: listing returned an outside `residuals.csv` with size/hash, while download correctly returned `404`.
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3327:This is a round-1 miss / incomplete application of the round-1 HIGH #2 hardening, not a regression from the basename-collision fix. The fix should share the same validated artifact-dir resolver between `list_artifacts()` and `resolve_artifact_path()`, ideally enforcing the generated timestamp shape like `YYYYMMDDTHHMMSSZ`, and add a regression test for malicious manifest timestamps on the manifest endpoint.
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:19:"GET /api/runs/{run_id}/field-artifacts still trusts the manifest timestamp before walking and hashing files — list_artifacts() only checks timestamp is non-empty. Reproduced with temp manifest using timestamp=../../outside."
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:23:1. Extracted shared validated resolver _resolve_artifact_dir(case_id, run_label) -> Optional[Path] in ui/backend/services/field_artifacts.py. It:
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:29:2. Both list_artifacts() AND resolve_artifact_path() now go through _resolve_artifact_dir first. The divergence you flagged is eliminated — there is only one code path for timestamp → on-disk dir.
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:31:3. list_artifacts() simplified: if _resolve_artifact_dir returns None → return None (404). No more independent manifest.get(timestamp, "") + artifact_dir composition.
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:33:4. resolve_artifact_path() simplified: removes its own duplicate timestamp/root checks; uses the shared resolver then just verifies filename stays under the already-validated artifact_dir.
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:233:@@ -48,18 +55,20 @@ def set_fields_root_for_testing(path: Optional[Path]) -> None:
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:263:-def list_artifacts(run_id: str) -> Optional[FieldArtifactsResponse]:
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:266:+def _resolve_artifact_dir(case_id: str, run_label: str) -> Optional[Path]:
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:307:+def list_artifacts(run_id: str) -> Optional[FieldArtifactsResponse]:
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:311:+    artifact_dir_resolved = _resolve_artifact_dir(case_id, run_label)
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:343:@@ -144,36 +194,42 @@ def list_artifacts(run_id: str) -> Optional[FieldArtifactsResponse]:
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:344: def resolve_artifact_path(run_id: str, filename: str) -> Path:
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:386:+    artifact_dir_resolved = _resolve_artifact_dir(case_id, run_label)
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:479:+    set_fields_root_for_testing(fields_root)
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:489:+        set_fields_root_for_testing(_FIXTURE_ROOT)
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:548:    48	def set_fields_root_for_testing(path: Optional[Path]) -> None:
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:610:   110	def _resolve_artifact_dir(case_id: str, run_label: str) -> Optional[Path]:
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:650:   150	def list_artifacts(run_id: str) -> Optional[FieldArtifactsResponse]:
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:654:   154	    artifact_dir_resolved = _resolve_artifact_dir(case_id, run_label)
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:694:   194	def resolve_artifact_path(run_id: str, filename: str) -> Path:
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:722:   222	    artifact_dir_resolved = _resolve_artifact_dir(case_id, run_label)
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:789:    48	    resp = list_artifacts(run_id)
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:810:    69	    path = resolve_artifact_path(run_id, filename)  # raises HTTPException(404)
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:887:The current service no longer composes `root / case_id / timestamp` from an unvalidated timestamp in `list_artifacts()`. Both list and download reach `_resolve_artifact_dir()`, and `parse_run_id()` is strict enough that manifest lookup itself is not a traversal vector.
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1181:ui/backend/services/field_artifacts.py:150:def list_artifacts(run_id: str) -> Optional[FieldArtifactsResponse]:

exec
/bin/zsh -lc 'git diff --stat -- ui/backend/services/field_artifacts.py ui/backend/routes/field_artifacts.py ui/backend/services/run_ids.py ui/backend/tests/test_field_artifacts_route.py ui/backend/schemas/validation.py' in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc 'git diff -- ui/backend/routes/field_artifacts.py ui/backend/services/run_ids.py ui/backend/schemas/validation.py' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
 ui/backend/routes/field_artifacts.py           |  10 +-
 ui/backend/services/field_artifacts.py         | 132 ++++++++++++++++++-------
 ui/backend/services/run_ids.py                 |  33 +++++++
 ui/backend/tests/test_field_artifacts_route.py |  66 ++++++++++++-
 4 files changed, 199 insertions(+), 42 deletions(-)

 succeeded in 0ms:
diff --git a/ui/backend/routes/field_artifacts.py b/ui/backend/routes/field_artifacts.py
index 77d6d6b..8b2ba88 100644
--- a/ui/backend/routes/field_artifacts.py
+++ b/ui/backend/routes/field_artifacts.py
@@ -55,11 +55,17 @@ def get_field_artifacts(run_id: str) -> FieldArtifactsResponse:
 
 
 @router.get(
-    "/runs/{run_id}/field-artifacts/{filename}",
+    "/runs/{run_id}/field-artifacts/{filename:path}",
     tags=["field-artifacts"],
 )
 def download_field_artifact(run_id: str, filename: str) -> FileResponse:
-    """Serve a single field artifact file. Traversal-safe."""
+    """Serve a single field artifact file. Traversal-safe.
+
+    The `{filename:path}` converter allows POSIX sub-paths like
+    `sample/500/uCenterline.xy` (Codex round 1 HIGH #1 fix — 3 sample
+    iteration dirs had basename collision). Traversal is defended in
+    resolve_artifact_path.
+    """
     path = resolve_artifact_path(run_id, filename)  # raises HTTPException(404)
     return FileResponse(
         path,
diff --git a/ui/backend/services/run_ids.py b/ui/backend/services/run_ids.py
index ba99513..73067ea 100644
--- a/ui/backend/services/run_ids.py
+++ b/ui/backend/services/run_ids.py
@@ -6,8 +6,36 @@ We use rpartition on the last "__" so case_ids with internal underscores
 """
 from __future__ import annotations
 
+import re
+from urllib.parse import unquote
+
 from fastapi import HTTPException
 
+# Identifier pattern for case_id and run_label segments.
+# Allow alphanumerics, underscore, hyphen, dot. Explicitly REJECT path
+# separators, '..', leading dots, and percent/url-encoded traversal markers.
+# Codex round 1 HIGH #2 (2026-04-21): traversal via run_id reproduced with
+# '..__pwn' AND '%2e%2e__pwn' — guard both decoded and raw forms.
+_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-]*$")
+
+
+def _validate_segment(name: str, kind: str) -> None:
+    """Reject traversal markers before building filesystem paths.
+
+    Rejects: empty, '.', '..', anything containing '/', '\\', '%', or not
+    matching the strict identifier pattern. Also rejects URL-decoded forms
+    (in case middleware forgot to decode) so '%2e%2e' → '..' is caught.
+    """
+    if not name or name in (".", ".."):
+        raise HTTPException(status_code=400, detail=f"invalid {kind}")
+    decoded = unquote(name)
+    if decoded != name or decoded in (".", ".."):
+        raise HTTPException(status_code=400, detail=f"invalid {kind}")
+    if "/" in name or "\\" in name or ".." in name:
+        raise HTTPException(status_code=400, detail=f"invalid {kind}")
+    if not _SEGMENT_RE.match(name):
+        raise HTTPException(status_code=400, detail=f"invalid {kind}")
+
 
 def parse_run_id(run_id: str) -> tuple[str, str]:
     """Parse 'lid_driven_cavity__audit_real_run' → ('lid_driven_cavity', 'audit_real_run').
@@ -16,6 +44,9 @@ def parse_run_id(run_id: str) -> tuple[str, str]:
     internal underscores. Labels today are simple identifiers without '__';
     rpartition is resilient if that changes.
 
+    Both case_id and run_label are validated against a strict identifier
+    pattern to prevent path-traversal attacks (Codex round 1 HIGH #2).
+
     Raises HTTPException(400) on malformed input.
     """
     if "__" not in run_id:
@@ -29,4 +60,6 @@ def parse_run_id(run_id: str) -> tuple[str, str]:
             status_code=400,
             detail=f"run_id has empty case_id or label: {run_id!r}",
         )
+    _validate_segment(case_id, "case_id")
+    _validate_segment(run_label, "run_label")
     return case_id, run_label

exec
/bin/zsh -lc 'tail -n 80 reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md && tail -n 80 reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   369	- Phase 8, AutoVerifier, 13/13, knowledge/whitelist.yaml, ai_cfd_cold_start_whitelist.yaml, Canonical Docs Type=Report, Phase 8 Done, naming drift
   370	
   371	## Task 2: Open Phase 9 as planning-only and keep solver expansion bounded
   372	
   373	### rollout_summary_files
   374	
   375	- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, Phase 9 kept as planning-only with decision-tree packet))
   376	
   377	### keywords
   378	
   379	- Phase 9 planning-only, PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md, PHASE9_MODEL_ROUTING_BASELINE_PLAN.md, PHASE9_ACTIVATION_REVIEW_PACKET.md, replay_manifest, SU2 CLI Harness Skill, foam_agent_adapter.py
   380	

exec
/bin/zsh -lc ".venv/bin/python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
import json
from fastapi.testclient import TestClient
from ui.backend.main import app
from ui.backend.services.field_artifacts import set_fields_root_for_testing

with TemporaryDirectory() as d:
    root = Path(d) / 'fields'; root.mkdir()
    (root.parent / 'runs').mkdir()
    out = root.parent / 'outside_artifacts'; out.mkdir()
    (out / 'leak.csv').write_text('secret\\n', encoding='utf-8')
    (root.parent / 'runs' / 'pwn.json').write_text(json.dumps({'timestamp':'outside_artifacts'}), encoding='utf-8')
    set_fields_root_for_testing(root)
    try:
        c = TestClient(app)
        for url in ['/api/runs/..__pwn/field-artifacts/leak.csv', '/api/runs/%2e%2e__pwn/field-artifacts/leak.csv']:
            r = c.get(url)
            print(url, r.status_code, r.text[:20])
    finally:
        set_fields_root_for_testing(None)
PY" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 187ms:
/api/runs/..__pwn/field-artifacts/leak.csv 200 secret

/api/runs/%2e%2e__pwn/field-artifacts/leak.csv 200 secret


codex
CHANGES_REQUIRED

1. HIGH — duplicate sample basenames make the manifest untruthful.
`ui/backend/services/field_artifacts.py:117`, `ui/backend/services/field_artifacts.py:123`, `ui/backend/services/field_artifacts.py:171` flatten all files to `p.name`, but `sample/0/uCenterline.xy`, `sample/500/uCenterline.xy`, and `sample/1000/uCenterline.xy` share one URL. Evidence at `.planning/phases/07a-field-capture/_integration_evidence.txt:159` shows three `uCenterline.xy` entries with different hashes and the same URL. I confirmed only the first file is downloadable; the later two advertised hashes do not match the bytes served. Extend the URL/manifest to carry subpath, or implement true latest-wins by listing only one deterministic latest artifact. A TODO alone is not acceptable while duplicate URLs remain.

2. HIGH — traversal defense does not cover `run_id`.
`ui/backend/services/run_ids.py:21` accepts `..__label`, then `ui/backend/services/field_artifacts.py:92` and `ui/backend/services/field_artifacts.py:164` build filesystem paths from that case id. `filename` is guarded, but `case_id`/`run_label` are not. I reproduced `200` responses for both literal `..__pwn` and URL-encoded `%2e%2e__pwn` against a temp fields root with an adjacent manifest. Reject `.`, `..`, empty, separators, and resolved paths outside the fields root for both manifest and artifact directories.

3. MED — Phase 7a opt-in/failure fallback is broader than stated.
`scripts/phase5_audit_run.py:263` populates Phase 7a metadata for every case, not only LDC. Separately, `src/foam_agent_adapter.py:6906` creates the artifact directory before `foamToVTK`; `scripts/phase5_audit_run.py:108` treats directory existence as success when writing the run manifest. A non-LDC run or failed `foamToVTK` can therefore leave an empty/bogus manifest and `field_artifacts` YAML key. Gate metadata to LDC/explicit opt-in and require a successful/nonempty artifact set before manifest write.

4. LOW — SHA cache has a real stale-hash edge.
`ui/backend/services/field_artifacts.py:51` keys on `(path, st_mtime, st_size)` via float `st_mtime` at `ui/backend/services/field_artifacts.py:62`. For immutable timestamped artifacts this is low risk, but audit-grade hash reporting should use `st_mtime_ns` at minimum, or avoid caching during active writes.

Checks that look OK: `_capture_field_artifacts` is called before teardown at `src/foam_agent_adapter.py:611`, after existing `_copy_postprocess_fields` at `src/foam_agent_adapter.py:597`; capture exceptions are swallowed; the OpenFOAM v10 sample block fix is correct; the LDC YAML `field_artifacts` key does not embed a timestamp.


tokens used
173,671
CHANGES_REQUIRED

1. HIGH — duplicate sample basenames make the manifest untruthful.
`ui/backend/services/field_artifacts.py:117`, `ui/backend/services/field_artifacts.py:123`, `ui/backend/services/field_artifacts.py:171` flatten all files to `p.name`, but `sample/0/uCenterline.xy`, `sample/500/uCenterline.xy`, and `sample/1000/uCenterline.xy` share one URL. Evidence at `.planning/phases/07a-field-capture/_integration_evidence.txt:159` shows three `uCenterline.xy` entries with different hashes and the same URL. I confirmed only the first file is downloadable; the later two advertised hashes do not match the bytes served. Extend the URL/manifest to carry subpath, or implement true latest-wins by listing only one deterministic latest artifact. A TODO alone is not acceptable while duplicate URLs remain.

2. HIGH — traversal defense does not cover `run_id`.
`ui/backend/services/run_ids.py:21` accepts `..__label`, then `ui/backend/services/field_artifacts.py:92` and `ui/backend/services/field_artifacts.py:164` build filesystem paths from that case id. `filename` is guarded, but `case_id`/`run_label` are not. I reproduced `200` responses for both literal `..__pwn` and URL-encoded `%2e%2e__pwn` against a temp fields root with an adjacent manifest. Reject `.`, `..`, empty, separators, and resolved paths outside the fields root for both manifest and artifact directories.

3. MED — Phase 7a opt-in/failure fallback is broader than stated.
`scripts/phase5_audit_run.py:263` populates Phase 7a metadata for every case, not only LDC. Separately, `src/foam_agent_adapter.py:6906` creates the artifact directory before `foamToVTK`; `scripts/phase5_audit_run.py:108` treats directory existence as success when writing the run manifest. A non-LDC run or failed `foamToVTK` can therefore leave an empty/bogus manifest and `field_artifacts` YAML key. Gate metadata to LDC/explicit opt-in and require a successful/nonempty artifact set before manifest write.

4. LOW — SHA cache has a real stale-hash edge.
`ui/backend/services/field_artifacts.py:51` keys on `(path, st_mtime, st_size)` via float `st_mtime` at `ui/backend/services/field_artifacts.py:62`. For immutable timestamped artifacts this is low risk, but audit-grade hash reporting should use `st_mtime_ns` at minimum, or avoid caching during active writes.

Checks that look OK: `_capture_field_artifacts` is called before teardown at `src/foam_agent_adapter.py:611`, after existing `_copy_postprocess_fields` at `src/foam_agent_adapter.py:597`; capture exceptions are swallowed; the OpenFOAM v10 sample block fix is correct; the LDC YAML `field_artifacts` key does not embed a timestamp.


         raise HTTPException(status_code=404, detail="artifact not found")
 
     case_id, run_label = parse_run_id(run_id)
@@ -160,20 +178,29 @@ def resolve_artifact_path(run_id: str, filename: str) -> Path:
     timestamp = manifest.get("timestamp", "")
     if not timestamp:
         raise HTTPException(status_code=404, detail="artifact not found")
+    # Codex round 1 HIGH #2: also validate timestamp from manifest (an adversary
+    # who writes an adjacent manifest could point timestamp at outside_artifacts).
+    if ("/" in timestamp or "\\" in timestamp or ".." in timestamp
+            or timestamp in ("", ".", "..")):
+        raise HTTPException(status_code=404, detail="artifact not found")
 
     root = _current_fields_root()
+    root_resolved = root.resolve()
     artifact_dir = root / case_id / timestamp
     if not artifact_dir.is_dir():
         raise HTTPException(status_code=404, detail="artifact not found")
+    try:
+        artifact_dir.resolve().relative_to(root_resolved)
+    except ValueError:
+        raise HTTPException(status_code=404, detail="artifact not found")
 
-    # We serve basenames; files may live in subdirs (VTK/x.vtk). Walk and match.
-    # This mirrors audit_package.py's traversal defense.
-    for p in artifact_dir.rglob(filename):
-        try:
-            resolved = p.resolve()
-            resolved.relative_to(artifact_dir.resolve())
-        except (ValueError, OSError):
-            continue
-        if resolved.is_file() and resolved.name == filename:
-            return resolved
-    raise HTTPException(status_code=404, detail="artifact not found")
+    # Compose target and verify it stays inside artifact_dir.
+    target = (artifact_dir / filename)
+    try:
+        resolved = target.resolve(strict=True)
+        resolved.relative_to(artifact_dir.resolve())
+    except (ValueError, OSError, FileNotFoundError):
+        raise HTTPException(status_code=404, detail="artifact not found")
+    if not resolved.is_file():
+        raise HTTPException(status_code=404, detail="artifact not found")
+    return resolved

codex
**Verdict: CHANGES_REQUIRED**

**Finding**
- HIGH: `GET /api/runs/{run_id}/field-artifacts` still trusts the manifest `timestamp` before walking and hashing files. In [field_artifacts.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/field_artifacts.py:109), `list_artifacts()` only checks that `timestamp` is non-empty, then builds `artifact_dir = root / case_id / timestamp` and recursively hashes classified files. The download path validates `timestamp` later, but the listing path does not. I reproduced this with a temp manifest using `timestamp="../../outside"`: listing returned an outside `residuals.csv` with size/hash, while download correctly returned `404`.

This is a round-1 miss / incomplete application of the round-1 HIGH #2 hardening, not a regression from the basename-collision fix. The fix should share the same validated artifact-dir resolver between `list_artifacts()` and `resolve_artifact_path()`, ideally enforcing the generated timestamp shape like `YYYYMMDDTHHMMSSZ`, and add a regression test for malicious manifest timestamps on the manifest endpoint.

Round-1 fix status:
- #1 URL basename collision: fixed. Live listing returns distinct `sample/0`, `sample/500`, `sample/1000` URLs.
- #2 run_id traversal: run_id validation and download-side timestamp validation are fixed, but listing-side timestamp traversal remains.
- #3 metadata over-application: fixed for LDC-only opt-in plus non-empty artifact dir guard.
- #4 SHA cache `st_mtime_ns`: fixed.

Verification run: `PYTHONPATH=. .venv/bin/pytest ui/backend/tests/ -q` -> `94 passed in 24.12s`.


tokens used
103,177
**Verdict: CHANGES_REQUIRED**

**Finding**
- HIGH: `GET /api/runs/{run_id}/field-artifacts` still trusts the manifest `timestamp` before walking and hashing files. In [field_artifacts.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/field_artifacts.py:109), `list_artifacts()` only checks that `timestamp` is non-empty, then builds `artifact_dir = root / case_id / timestamp` and recursively hashes classified files. The download path validates `timestamp` later, but the listing path does not. I reproduced this with a temp manifest using `timestamp="../../outside"`: listing returned an outside `residuals.csv` with size/hash, while download correctly returned `404`.

This is a round-1 miss / incomplete application of the round-1 HIGH #2 hardening, not a regression from the basename-collision fix. The fix should share the same validated artifact-dir resolver between `list_artifacts()` and `resolve_artifact_path()`, ideally enforcing the generated timestamp shape like `YYYYMMDDTHHMMSSZ`, and add a regression test for malicious manifest timestamps on the manifest endpoint.

Round-1 fix status:
- #1 URL basename collision: fixed. Live listing returns distinct `sample/0`, `sample/500`, `sample/1000` URLs.
- #2 run_id traversal: run_id validation and download-side timestamp validation are fixed, but listing-side timestamp traversal remains.
- #3 metadata over-application: fixed for LDC-only opt-in plus non-empty artifact dir guard.
- #4 SHA cache `st_mtime_ns`: fixed.

Verification run: `PYTHONPATH=. .venv/bin/pytest ui/backend/tests/ -q` -> `94 passed in 24.12s`.



exec
/bin/zsh -lc 'rg -n "''^(## |# |-|Findings|HIGH|MEDIUM|LOW|CHANGES_REQUIRED|APPROVED|Round|round|#1|#3|#4)" reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md | tail -n 120' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:962:- ✅ plane_channel_flow: Docker E2E PASS, u_mean_profile, Gold Std PASS
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:963:- ✅ rayleigh_benard_convection: FIXED + Docker E2E PASS, nusselt_number=10.5
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:964:- ✅ naca0012_airfoil: AIRFOIL fvSolution fix (p-relax 0.3, lower URFs), Docker E2E PASS 286s
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:965:- ✅ impinging_jet: Docker E2E PASS, nusselt_number=0.0042, 157s
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:966:- ✅ All 121 tests passing
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:967:- ⏳ Phase 8 AutoVerifier: SPEC.md ✅, 等待 Opus 4.6 Gate 架构审查
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:971:- ✅ nu bug fixed: nu=0.1/Re (was 0.01 hardcoded)
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:972:- ✅ y-aware interpolation in ResultComparator
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:973:- ✅ LDC Docker E2E 完整证据链: 7.8s exec → u_centerline[17pts] → ComparisonResult → AttributionReport
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:974:- ⚠️ LDC comparison: 5/5 deviations (coarse mesh → primary vortex正确, secondary vortex未捕捉)
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:975:- ✅ AttributionReport 正确识别 mesh 为 primary cause
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:981:- NC Cavity: ✅ Docker E2E SUCCESS (buoyantFoam + Boussinesq, 11s, success=True)
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:990:- BFS: ✅ Docker E2E SUCCESS (simpleFoam, 514s, U_residual_magnitude extracted)
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:992:- LDC: ✅ Docker E2E SUCCESS (icoFoam, 7.8s, from prior session)
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:993:- 3 Docker E2E 全量验证: ✅ 104 tests passing
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:995:# Phase 5 — COMPLETE
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1002:- [T1] 多案例批量E2E验证 — ✅ Done (目标>80%通过率: 9/9 pipeline pass, 4/9 Gold Standard Mock)
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1003:- [T2] Gold Standard覆盖率提升 — ✅ Done (8/10 YAML → 10/10 YAML 建设中)
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1004:- [T3] 误差模式自动归类 — ✅ Done (2026-04-15)
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1008:- src/error_attributor.py: 5 new ErrorTypes wired into error_type_scores + structured deviation matcher
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1015:- src/correction_recorder.py: 4 structured _infer_error_type branches + 5 new dict entries
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1016:- tests/test_error_attributor.py: 7 test cases (all passing)
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1017:- 120 tests passing (was 104)
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1021:- Gold Standard 数值通过率 44% (仅 Mock 模式)
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1022:- Docker 真实执行尚未全量覆盖
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1023:- 2 个新 Gold Standard YAML 待写入 (naca0012_airfoil, fully_developed_pipe)
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1374:--- a/ui/backend/routes/field_artifacts.py
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1380:-    "/runs/{run_id}/field-artifacts/{filename}",
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1385:-    """Serve a single field artifact file. Traversal-safe."""
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1398:--- a/ui/backend/services/field_artifacts.py
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1404:-# SHA256 cache keyed on (abs_path, st_mtime, st_size) per 07a-RESEARCH.md §2.6.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1405:-_sha_cache: dict[tuple[str, float, int], str] = {}
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1415:-    Cache key: (absolute_path, st_mtime, st_size). Mtime+size collision would
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1416:-    return a stale hash — MVP-accepted risk per 07a-RESEARCH.md §2.6.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1421:-    key = (str(path.resolve()), st.st_mtime, st.st_size)
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1440:-        # Use basename only in the URL (traversal via URL blocked by route).
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1445:-                filename=p.name,
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1446:-                url=f"/api/runs/{run_id}/field-artifacts/{p.name}",
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1456:-    Traversal defense: reject any filename with path separators or '..';
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1457:-    additionally verify `resolved.relative_to(artifact_dir.resolve())`.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1465:-    # Reject anything with path structure or traversal markers.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1466:-    if filename in ("", ".", ".."):
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1477:-    if "/" in filename or "\\" in filename or ".." in filename:
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1503:-    # We serve basenames; files may live in subdirs (VTK/x.vtk). Walk and match.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1504:-    # This mirrors audit_package.py's traversal defense.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1505:-    for p in artifact_dir.rglob(filename):
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1506:-        try:
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1507:-            resolved = p.resolve()
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1508:-            resolved.relative_to(artifact_dir.resolve())
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1509:-        except (ValueError, OSError):
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1510:-            continue
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1511:-        if resolved.is_file() and resolved.name == filename:
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1512:-            return resolved
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1513:-    raise HTTPException(status_code=404, detail="artifact not found")
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1526:--- a/ui/backend/services/run_ids.py
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1584:--- a/ui/backend/tests/test_field_artifacts_route.py
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1590:-    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts/lid_driven_cavity_2000.vtk")
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1596:-def test_download_404_traversal(client: TestClient) -> None:
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1639:--- a/scripts/phase5_audit_run.py
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1645:-    Returns the manifest Path on success, None if the artifact dir never
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1646:-    materialized (e.g. foamToVTK failed or the case is not Phase-7a opted-in).
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1691:-        # Opt-in signalling to FoamAgentExecutor. Other 9 cases' controlDicts
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1692:-        # do NOT yet emit Phase 7a function objects, but the executor guards
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1693:-        # on the metadata keys — staging runs best-effort.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1694:-        if spec.metadata is None:
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1695:-            spec.metadata = {}
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1696:-        spec.metadata["phase7a_timestamp"] = ts
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1697:-        spec.metadata["phase7a_case_id"] = case_id
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1710:-    # the artifact dir materialized (best-effort, must not block audit doc).
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1714:-    manifest_path = _write_field_artifacts_run_manifest(case_id, run_label, ts)
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1725:--- a/src/foam_agent_adapter.py
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1738:-            "        {\n"
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1742:-            "                type        uniform;\n"
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1749:-            "        }\n"
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1758:-            # (d) Derive residuals.csv from postProcessing/residuals/0/residuals.dat
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1759:-            #     if present. Per user ratification #3 — structured ASCII,
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1760:-            #     no log regex.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1767:-                artifact_dir.glob("postProcessing/residuals/*/residuals.dat")
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1774:--- a/ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1780:-  description_zh: FoamAgentExecutor 驱动 OpenFOAM 实际跑出的结果（commit c84e626）。这是 audit package
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1789:-  run_id: audit_lid_driven_cavity_c84e626
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1790:-  commit_sha: c84e626
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1791:-  measured_at: '2026-04-21T06:37:29Z'
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3176:--- a/ui/backend/services/field_artifacts.py
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3182:-# SHA256 cache keyed on (abs_path, st_mtime, st_size) per 07a-RESEARCH.md §2.6.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3183:-_sha_cache: dict[tuple[str, float, int], str] = {}
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3193:-    Cache key: (absolute_path, st_mtime, st_size). Mtime+size collision would
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3194:-    return a stale hash — MVP-accepted risk per 07a-RESEARCH.md §2.6.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3199:-    key = (str(path.resolve()), st.st_mtime, st.st_size)
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3218:-        # Use basename only in the URL (traversal via URL blocked by route).
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3223:-                filename=p.name,
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3224:-                url=f"/api/runs/{run_id}/field-artifacts/{p.name}",
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3234:-    Traversal defense: reject any filename with path separators or '..';
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3235:-    additionally verify `resolved.relative_to(artifact_dir.resolve())`.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3243:-    # Reject anything with path structure or traversal markers.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3244:-    if filename in ("", ".", ".."):
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3255:-    if "/" in filename or "\\" in filename or ".." in filename:
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3281:-    # We serve basenames; files may live in subdirs (VTK/x.vtk). Walk and match.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3282:-    # This mirrors audit_package.py's traversal defense.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3283:-    for p in artifact_dir.rglob(filename):
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3284:-        try:
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3285:-            resolved = p.resolve()
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3286:-            resolved.relative_to(artifact_dir.resolve())
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3287:-        except (ValueError, OSError):
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3288:-            continue
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3289:-        if resolved.is_file() and resolved.name == filename:
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3290:-            return resolved
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3291:-    raise HTTPException(status_code=404, detail="artifact not found")
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3307:- HIGH: `GET /api/runs/{run_id}/field-artifacts` still trusts the manifest `timestamp` before walking and hashing files. In [field_artifacts.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/field_artifacts.py:109), `list_artifacts()` only checks that `timestamp` is non-empty, then builds `artifact_dir = root / case_id / timestamp` and recursively hashes classified files. The download path validates `timestamp` later, but the listing path does not. I reproduced this with a temp manifest using `timestamp="../../outside"`: listing returned an outside `residuals.csv` with size/hash, while download correctly returned `404`.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3311:Round-1 fix status:
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3312:- #1 URL basename collision: fixed. Live listing returns distinct `sample/0`, `sample/500`, `sample/1000` URLs.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3313:- #2 run_id traversal: run_id validation and download-side timestamp validation are fixed, but listing-side timestamp traversal remains.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3314:- #3 metadata over-application: fixed for LDC-only opt-in plus non-empty artifact dir guard.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3315:- #4 SHA cache `st_mtime_ns`: fixed.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3325:- HIGH: `GET /api/runs/{run_id}/field-artifacts` still trusts the manifest `timestamp` before walking and hashing files. In [field_artifacts.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/field_artifacts.py:109), `list_artifacts()` only checks that `timestamp` is non-empty, then builds `artifact_dir = root / case_id / timestamp` and recursively hashes classified files. The download path validates `timestamp` later, but the listing path does not. I reproduced this with a temp manifest using `timestamp="../../outside"`: listing returned an outside `residuals.csv` with size/hash, while download correctly returned `404`.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3329:Round-1 fix status:
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3330:- #1 URL basename collision: fixed. Live listing returns distinct `sample/0`, `sample/500`, `sample/1000` URLs.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3331:- #2 run_id traversal: run_id validation and download-side timestamp validation are fixed, but listing-side timestamp traversal remains.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3332:- #3 metadata over-application: fixed for LDC-only opt-in plus non-empty artifact dir guard.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3333:- #4 SHA cache `st_mtime_ns`: fixed.

exec
/bin/zsh -lc "git diff -- scripts/phase5_audit_run.py src/foam_agent_adapter.py ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml | sed -n '1,260p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
diff --git a/scripts/phase5_audit_run.py b/scripts/phase5_audit_run.py
index da349d8..80cccfa 100644
--- a/scripts/phase5_audit_run.py
+++ b/scripts/phase5_audit_run.py
@@ -102,8 +102,10 @@ def _write_field_artifacts_run_manifest(
     """Write reports/phase5_fields/{case_id}/runs/{run_label}.json so the
     backend route can resolve run_label -> timestamp directory in O(1).
 
-    Returns the manifest Path on success, None if the artifact dir never
-    materialized (e.g. foamToVTK failed or the case is not Phase-7a opted-in).
+    Returns the manifest Path on success, None if the artifact dir is absent
+    OR empty. Codex round 1 MED #3 (2026-04-21): require a NON-empty artifact
+    set — an empty directory from a failed foamToVTK must not produce a
+    bogus manifest that the route will then 404-through.
     """
     artifact_dir = FIELDS_DIR / case_id / timestamp
     if not artifact_dir.is_dir():
@@ -112,6 +114,14 @@ def _write_field_artifacts_run_manifest(
             flush=True,
         )
         return None
+    # Count usable leaf files (foamToVTK output, samples, residuals).
+    usable = [p for p in artifact_dir.rglob("*") if p.is_file()]
+    if not usable:
+        print(
+            f"[audit] [WARN] field artifact dir empty, skipping manifest: {artifact_dir}",
+            flush=True,
+        )
+        return None
     runs_dir = FIELDS_DIR / case_id / "runs"
     runs_dir.mkdir(parents=True, exist_ok=True)
     manifest = runs_dir / f"{run_label}.json"
@@ -125,6 +135,12 @@ def _write_field_artifacts_run_manifest(
     return manifest
 
 
+# Codex round 1 MED #3 (2026-04-21): gate Phase 7a metadata injection to
+# case-ids whose case generators actually emit the functions{} block. Other 9
+# cases stay silent until Phase 7c Sprint-2 rolls their generators forward.
+_PHASE7A_OPTED_IN: frozenset[str] = frozenset({"lid_driven_cavity"})
+
+
 def _audit_fixture_doc(
     case_id: str,
     report,
@@ -259,16 +275,16 @@ def run_one(runner: TaskRunner, case_id: str, commit_sha: str) -> dict:
 
     # Phase 7a — author the single shared timestamp up front; the executor-side
     # _capture_field_artifacts writes to reports/phase5_fields/{case_id}/{ts}/.
+    # Codex round 1 MED #3: only inject metadata for opted-in cases — other 9
+    # case generators do not emit Phase 7a function objects yet.
     ts = _phase7a_timestamp()
     try:
         spec = runner._task_spec_from_case_id(case_id)
-        # Opt-in signalling to FoamAgentExecutor. Other 9 cases' controlDicts
-        # do NOT yet emit Phase 7a function objects, but the executor guards
-        # on the metadata keys — staging runs best-effort.
-        if spec.metadata is None:
-            spec.metadata = {}
-        spec.metadata["phase7a_timestamp"] = ts
-        spec.metadata["phase7a_case_id"] = case_id
+        if case_id in _PHASE7A_OPTED_IN:
+            if spec.metadata is None:
+                spec.metadata = {}
+            spec.metadata["phase7a_timestamp"] = ts
+            spec.metadata["phase7a_case_id"] = case_id
         report = runner.run_task(spec)
     except Exception as e:  # noqa: BLE001
         print(f"[audit] {case_id} EXCEPTION: {e!r}")
@@ -277,9 +293,14 @@ def run_one(runner: TaskRunner, case_id: str, commit_sha: str) -> dict:
     dt = time.monotonic() - t0
 
     # Phase 7a — write per-run manifest + build field_artifacts_ref dict iff
-    # the artifact dir materialized (best-effort, must not block audit doc).
+    # the case is opted-in AND the artifact dir materialized with non-empty
+    # contents (best-effort, must not block audit doc). MED #3 gating above.
     run_label = "audit_real_run"
-    manifest_path = _write_field_artifacts_run_manifest(case_id, run_label, ts)
+    manifest_path = (
+        _write_field_artifacts_run_manifest(case_id, run_label, ts)
+        if case_id in _PHASE7A_OPTED_IN
+        else None
+    )
     field_artifacts_ref: "dict | None" = None
     if manifest_path is not None:
         field_artifacts_ref = {
diff --git a/src/foam_agent_adapter.py b/src/foam_agent_adapter.py
index db896ef..80e2313 100644
--- a/src/foam_agent_adapter.py
+++ b/src/foam_agent_adapter.py
@@ -701,17 +701,23 @@ class FoamAgentExecutor:
             "\n"
             "        fields          (U p);\n"
             "\n"
+            # OpenFOAM 10 sampledSets requires `sets (...)` list-form and
+            # inner `type lineUniform;` (not `type uniform;`). Dict-form +
+            # `uniform` parses via foamDictionary but crashes at runtime with
+            # "Attempt to return dictionary entry as a primitive" inside
+            # Foam::functionObjects::sampledSets::read. Verified against
+            # /opt/openfoam10/etc/caseDicts/postProcessing/graphs/graphUniform.cfg.
             "        sets\n"
-            "        {\n"
+            "        (\n"
             "            uCenterline\n"
             "            {\n"
-            "                type        uniform;\n"
+            "                type        lineUniform;\n"
             "                axis        y;\n"
             "                start       (0.05 0.0   0.005);\n"
             "                end         (0.05 0.1   0.005);\n"
             "                nPoints     129;\n"
             "            }\n"
-            "        }\n"
+            "        );\n"
             "    }\n"
             "\n"
             "    residuals\n"
@@ -6954,11 +6960,13 @@ mergePatchPairs
                     (artifact_dir / logname).write_bytes(src.read_bytes())
                     break
 
-            # (d) Derive residuals.csv from postProcessing/residuals/0/residuals.dat
-            #     if present. Per user ratification #3 — structured ASCII,
-            #     no log regex.
+            # (d) Derive residuals.csv from residuals/0/residuals.dat if present.
+            #     Per user ratification #3 — structured ASCII, no log regex.
+            #     NOTE: container.get_archive('.../postProcessing/residuals')
+            #     tar-extracts under basename `residuals/`, not the full
+            #     `postProcessing/residuals/` path. Same applies to `sample/`.
             residuals_dat_candidates = list(
-                artifact_dir.glob("postProcessing/residuals/*/residuals.dat")
+                artifact_dir.glob("residuals/*/residuals.dat")
             )
             if residuals_dat_candidates:
                 try:
diff --git a/ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml b/ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml
index 3e87298..8d89d84 100644
--- a/ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml
+++ b/ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml
@@ -9,7 +9,7 @@ run_metadata:
   run_id: audit_real_run
   label_zh: 真实 solver 审计运行
   label_en: Real solver audit run
-  description_zh: FoamAgentExecutor 驱动 OpenFOAM 实际跑出的结果（commit c84e626）。这是 audit package
+  description_zh: FoamAgentExecutor 驱动 OpenFOAM 实际跑出的结果（commit 1cc18b2）。这是 audit package
     背书的权威测量——不是合成 fixture。失败的话说明 case 本身的 physics_contract 在当前 mesh 预算下无法满足，不是 harness
     bug；会进入 audit_concerns 随包交付给审查方。
   category: audit_real_run
@@ -19,9 +19,9 @@ source: phase5_audit_run_foam_agent
 measurement:
   value: -0.197225625
   unit: dimensionless
-  run_id: audit_lid_driven_cavity_c84e626
-  commit_sha: c84e626
-  measured_at: '2026-04-21T06:37:29Z'
+  run_id: audit_lid_driven_cavity_1cc18b2
+  commit_sha: 1cc18b2
+  measured_at: '2026-04-21T08:24:08Z'
   quantity: u_centerline[y=0.3750]
   extraction_source: comparator_deviation
   solver_success: true
@@ -45,3 +45,6 @@ decisions_trail:
   date: '2026-04-21'
   title: Phase 5a audit pipeline — real-solver fixtures
   autonomous: true
+field_artifacts:
+  manifest_path_rel: reports/phase5_fields/lid_driven_cavity/runs/audit_real_run.json
+  run_label: audit_real_run

exec
/bin/zsh -lc "nl -ba scripts/phase5_audit_run.py | sed -n '80,140p;250,330p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba src/foam_agent_adapter.py | sed -n '680,740p;6880,6945p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba ui/backend/tests/test_field_artifacts_route.py | sed -n '1,220p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   680	            y_plus_block = (
   681	                "\n    yPlus\n"
   682	                "    {\n"
   683	                "        type            yPlus;\n"
   684	                '        libs            ("libfieldFunctionObjects.so");\n'
   685	                "        writeControl    writeTime;\n"
   686	                "    }\n"
   687	            )
   688	
   689	        return (
   690	            "\nfunctions\n"
   691	            "{\n"
   692	            "    sample\n"
   693	            "    {\n"
   694	            "        type            sets;\n"
   695	            '        libs            ("libsampling.so");\n'
   696	            "        writeControl    timeStep;\n"
   697	            "        writeInterval   500;\n"
   698	            "\n"
   699	            "        interpolationScheme cellPoint;\n"
   700	            "        setFormat       raw;\n"
   701	            "\n"
   702	            "        fields          (U p);\n"
   703	            "\n"
   704	            # OpenFOAM 10 sampledSets requires `sets (...)` list-form and
   705	            # inner `type lineUniform;` (not `type uniform;`). Dict-form +
   706	            # `uniform` parses via foamDictionary but crashes at runtime with
   707	            # "Attempt to return dictionary entry as a primitive" inside
   708	            # Foam::functionObjects::sampledSets::read. Verified against
   709	            # /opt/openfoam10/etc/caseDicts/postProcessing/graphs/graphUniform.cfg.
   710	            "        sets\n"
   711	            "        (\n"
   712	            "            uCenterline\n"
   713	            "            {\n"
   714	            "                type        lineUniform;\n"
   715	            "                axis        y;\n"
   716	            "                start       (0.05 0.0   0.005);\n"
   717	            "                end         (0.05 0.1   0.005);\n"
   718	            "                nPoints     129;\n"
   719	            "            }\n"
   720	            "        );\n"
   721	            "    }\n"
   722	            "\n"
   723	            "    residuals\n"
   724	            "    {\n"
   725	            "        type            residuals;\n"
   726	            '        libs            ("libutilityFunctionObjects.so");\n'
   727	            "        writeControl    timeStep;\n"
   728	            "        writeInterval   1;\n"
   729	            "        fields          (U p);\n"
   730	            "    }\n"
   731	            f"{y_plus_block}"
   732	            "}\n"
   733	        )
   734	
   735	    def _generate_lid_driven_cavity(self, case_dir: Path, task_spec: TaskSpec) -> None:
   736	        """生成 Lid-Driven Cavity 最小 OpenFOAM case 文件。"""
   737	        (case_dir / "system").mkdir(parents=True, exist_ok=True)
   738	        (case_dir / "constant").mkdir(parents=True, exist_ok=True)
   739	        (case_dir / "0").mkdir(parents=True, exist_ok=True)
   740	
  6880	        self,
  6881	        container: Any,
  6882	        case_cont_dir: str,
  6883	        case_host_dir: Path,
  6884	        case_id: str,
  6885	        timestamp: str,
  6886	    ) -> Optional[Path]:
  6887	        """Phase 7a — stage OpenFOAM field artifacts out of the container
  6888	        before the finally-block tears down case_host_dir.
  6889	
  6890	        Mirrors _copy_postprocess_fields. Runs foamToVTK inside the container,
  6891	        then uses docker `get_archive` to pull VTK/, postProcessing/sample/,
  6892	        and postProcessing/residuals/ wholesale via a single tar stream.
  6893	        Also copies log.<solver> from the host case dir (already on host).
  6894	
  6895	        Returns the host-side artifact_dir on success, None on failure.
  6896	        Never raises — field capture is best-effort and must not fail the run
  6897	        (comparator scalar extraction still needs to succeed downstream).
  6898	        """
  6899	        import io as _io
  6900	        import sys as _sys
  6901	        import tarfile as _tarfile
  6902	
  6903	        repo_root = Path(__file__).resolve().parents[1]
  6904	        artifact_dir = repo_root / "reports" / "phase5_fields" / case_id / timestamp
  6905	        try:
  6906	            artifact_dir.mkdir(parents=True, exist_ok=True)
  6907	
  6908	            # (a) foamToVTK — -allPatches merges patches into a single file.
  6909	            #     Fallback without -allPatches if it trips empty-patch
  6910	            #     assertions (07a-RESEARCH.md §3.2).
  6911	            ok, log = self._docker_exec(
  6912	                "foamToVTK -latestTime -noZero -allPatches",
  6913	                case_cont_dir,
  6914	                120,
  6915	            )
  6916	            if not ok:
  6917	                print(
  6918	                    f"[WARN] foamToVTK -allPatches failed, retrying without: {log[:200]}",
  6919	                    file=_sys.stderr,
  6920	                )
  6921	                ok, log = self._docker_exec(
  6922	                    "foamToVTK -latestTime -noZero", case_cont_dir, 120,
  6923	                )
  6924	            if not ok:
  6925	                print(
  6926	                    f"[WARN] foamToVTK failed, field capture skipped: {log[:200]}",
  6927	                    file=_sys.stderr,
  6928	                )
  6929	                return None
  6930	
  6931	            # (b) Tar + get_archive the three subtrees. Missing subtrees are
  6932	            #     fine (e.g. postProcessing/residuals only exists if the
  6933	            #     residuals function object was emitted).
  6934	            for sub in ("VTK", "postProcessing/sample", "postProcessing/residuals"):
  6935	                src_in_cont = f"{case_cont_dir}/{sub}"
  6936	                probe = container.exec_run(
  6937	                    cmd=["bash", "-c", f'[ -e "{src_in_cont}" ] && echo y || echo n'],
  6938	                )
  6939	                if probe.output.decode().strip() != "y":
  6940	                    continue
  6941	                try:
  6942	                    bits, _ = container.get_archive(src_in_cont)
  6943	                    buf = _io.BytesIO(b"".join(bits))
  6944	                    with _tarfile.open(fileobj=buf) as tar:
  6945	                        tar.extractall(path=artifact_dir)

 succeeded in 0ms:
    80	        actual = first.actual
    81	        if isinstance(actual, dict) and "value" in actual:
    82	            return first.quantity, float(actual["value"]), "comparator_deviation"
    83	        if isinstance(actual, (int, float)):
    84	            return first.quantity, float(actual), "comparator_deviation"
    85	    kq = report.execution_result.key_quantities or {}
    86	    for k, v in kq.items():
    87	        if isinstance(v, (int, float)) and not isinstance(v, bool):
    88	            return k, float(v), "key_quantities_fallback"
    89	        if isinstance(v, dict) and "value" in v and isinstance(v["value"], (int, float)):
    90	            return k, float(v["value"]), "key_quantities_fallback"
    91	    return None, None, "no_numeric_quantity"
    92	
    93	
    94	def _phase7a_timestamp() -> str:
    95	    """Shared timestamp format — matches _write_raw_capture."""
    96	    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    97	
    98	
    99	def _write_field_artifacts_run_manifest(
   100	    case_id: str, run_label: str, timestamp: str
   101	) -> "Path | None":
   102	    """Write reports/phase5_fields/{case_id}/runs/{run_label}.json so the
   103	    backend route can resolve run_label -> timestamp directory in O(1).
   104	
   105	    Returns the manifest Path on success, None if the artifact dir is absent
   106	    OR empty. Codex round 1 MED #3 (2026-04-21): require a NON-empty artifact
   107	    set — an empty directory from a failed foamToVTK must not produce a
   108	    bogus manifest that the route will then 404-through.
   109	    """
   110	    artifact_dir = FIELDS_DIR / case_id / timestamp
   111	    if not artifact_dir.is_dir():
   112	        print(
   113	            f"[audit] [WARN] field artifact dir missing, skipping manifest: {artifact_dir}",
   114	            flush=True,
   115	        )
   116	        return None
   117	    # Count usable leaf files (foamToVTK output, samples, residuals).
   118	    usable = [p for p in artifact_dir.rglob("*") if p.is_file()]
   119	    if not usable:
   120	        print(
   121	            f"[audit] [WARN] field artifact dir empty, skipping manifest: {artifact_dir}",
   122	            flush=True,
   123	        )
   124	        return None
   125	    runs_dir = FIELDS_DIR / case_id / "runs"
   126	    runs_dir.mkdir(parents=True, exist_ok=True)
   127	    manifest = runs_dir / f"{run_label}.json"
   128	    payload = {
   129	        "run_label": run_label,
   130	        "timestamp": timestamp,
   131	        "case_id": case_id,
   132	        "artifact_dir_rel": str(artifact_dir.relative_to(REPO_ROOT)),
   133	    }
   134	    manifest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
   135	    return manifest
   136	
   137	
   138	# Codex round 1 MED #3 (2026-04-21): gate Phase 7a metadata injection to
   139	# case-ids whose case generators actually emit the functions{} block. Other 9
   140	# cases stay silent until Phase 7c Sprint-2 rolls their generators forward.
   250	    comp = report.comparison_result
   251	    data = {
   252	        "case_id": case_id,
   253	        "measured_at": _iso_now(),
   254	        "duration_s": round(duration_s, 3),
   255	        "solver_success": er.success,
   256	        "key_quantities": er.key_quantities,
   257	        "comparator_passed": comp.passed if comp else None,
   258	        "comparator_summary": (comp.summary if comp else None),
   259	        "deviations": (
   260	            [
   261	                {"quantity": d.quantity, "actual": d.actual, "expected": d.expected}
   262	                for d in (comp.deviations or [])
   263	            ]
   264	            if comp
   265	            else []
   266	        ),
   267	    }
   268	    out.write_text(json.dumps(data, indent=2, default=str))
   269	    return out
   270	
   271	
   272	def run_one(runner: TaskRunner, case_id: str, commit_sha: str) -> dict:
   273	    t0 = time.monotonic()
   274	    print(f"[audit] {case_id} → start", flush=True)
   275	
   276	    # Phase 7a — author the single shared timestamp up front; the executor-side
   277	    # _capture_field_artifacts writes to reports/phase5_fields/{case_id}/{ts}/.
   278	    # Codex round 1 MED #3: only inject metadata for opted-in cases — other 9
   279	    # case generators do not emit Phase 7a function objects yet.
   280	    ts = _phase7a_timestamp()
   281	    try:
   282	        spec = runner._task_spec_from_case_id(case_id)
   283	        if case_id in _PHASE7A_OPTED_IN:
   284	            if spec.metadata is None:
   285	                spec.metadata = {}
   286	            spec.metadata["phase7a_timestamp"] = ts
   287	            spec.metadata["phase7a_case_id"] = case_id
   288	        report = runner.run_task(spec)
   289	    except Exception as e:  # noqa: BLE001
   290	        print(f"[audit] {case_id} EXCEPTION: {e!r}")
   291	        return {"case_id": case_id, "ok": False, "error": repr(e)}
   292	
   293	    dt = time.monotonic() - t0
   294	
   295	    # Phase 7a — write per-run manifest + build field_artifacts_ref dict iff
   296	    # the case is opted-in AND the artifact dir materialized with non-empty
   297	    # contents (best-effort, must not block audit doc). MED #3 gating above.
   298	    run_label = "audit_real_run"
   299	    manifest_path = (
   300	        _write_field_artifacts_run_manifest(case_id, run_label, ts)
   301	        if case_id in _PHASE7A_OPTED_IN
   302	        else None
   303	    )
   304	    field_artifacts_ref: "dict | None" = None
   305	    if manifest_path is not None:
   306	        field_artifacts_ref = {
   307	            "manifest_path_rel": str(manifest_path.relative_to(REPO_ROOT)),
   308	            "run_label": run_label,
   309	            # Deliberately NO timestamp string here (byte-repro): resolve via manifest.
   310	        }
   311	
   312	    doc = _audit_fixture_doc(
   313	        case_id, report, commit_sha, field_artifacts_ref=field_artifacts_ref,
   314	    )
   315	    fixture_path = _write_audit_fixture(case_id, doc)
   316	    raw_path = _write_raw_capture(case_id, report, dt)
   317	    verdict = doc["run_metadata"]["expected_verdict"]
   318	    print(f"[audit] {case_id} → {verdict} · {dt:.1f}s · {fixture_path.name}", flush=True)
   319	    return {
   320	        "case_id": case_id,
   321	        "ok": True,
   322	        "duration_s": round(dt, 3),
   323	        "verdict": verdict,
   324	        "fixture": str(fixture_path.relative_to(REPO_ROOT)),
   325	        "raw": str(raw_path.relative_to(REPO_ROOT)),
   326	        "field_artifacts_manifest": (
   327	            str(manifest_path.relative_to(REPO_ROOT)) if manifest_path else None
   328	        ),
   329	    }
   330	

 succeeded in 0ms:
     1	"""Phase 7a — field artifacts route tests.
     2	
     3	Runs OFFLINE against the committed fixture at
     4	ui/backend/tests/fixtures/phase7a_sample_fields/ via
     5	set_fields_root_for_testing. Must NOT call the solver.
     6	"""
     7	from __future__ import annotations
     8	
     9	import re
    10	from pathlib import Path
    11	
    12	import pytest
    13	from fastapi.testclient import TestClient
    14	
    15	from ui.backend.main import app
    16	from ui.backend.services.field_artifacts import set_fields_root_for_testing
    17	
    18	_FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "phase7a_sample_fields"
    19	_RUN_ID = "lid_driven_cavity__audit_real_run"
    20	
    21	
    22	@pytest.fixture(autouse=True)
    23	def _point_fields_root_at_fixture():
    24	    set_fields_root_for_testing(_FIXTURE_ROOT)
    25	    yield
    26	    set_fields_root_for_testing(None)
    27	
    28	
    29	@pytest.fixture
    30	def client() -> TestClient:
    31	    return TestClient(app)
    32	
    33	
    34	# ---------- Manifest endpoint ----------
    35	
    36	def test_get_manifest_200(client: TestClient) -> None:
    37	    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts")
    38	    assert r.status_code == 200, r.text
    39	    body = r.json()
    40	    assert body["run_id"] == _RUN_ID
    41	    assert body["case_id"] == "lid_driven_cavity"
    42	    assert body["run_label"] == "audit_real_run"
    43	    assert body["timestamp"] == "20260421T000000Z"
    44	
    45	
    46	def test_manifest_three_artifacts(client: TestClient) -> None:
    47	    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts")
    48	    assert r.status_code == 200
    49	    artifacts = r.json()["artifacts"]
    50	    assert len(artifacts) >= 3, artifacts
    51	    kinds = {a["kind"] for a in artifacts}
    52	    assert {"vtk", "csv", "residual_log"}.issubset(kinds), kinds
    53	
    54	
    55	def test_manifest_ordering(client: TestClient) -> None:
    56	    """User ratification #6: sort by (kind_order, filename), vtk < csv < residual_log."""
    57	    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts")
    58	    assert r.status_code == 200
    59	    artifacts = r.json()["artifacts"]
    60	    order = {"vtk": 0, "csv": 1, "residual_log": 2}
    61	    keys = [(order[a["kind"]], a["filename"]) for a in artifacts]
    62	    assert keys == sorted(keys), keys
    63	
    64	
    65	_HEX64 = re.compile(r"^[0-9a-f]{64}$")
    66	
    67	
    68	def test_sha256_format(client: TestClient) -> None:
    69	    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts")
    70	    artifacts = r.json()["artifacts"]
    71	    for a in artifacts:
    72	        assert _HEX64.match(a["sha256"]), a
    73	
    74	
    75	def test_manifest_sizes_positive(client: TestClient) -> None:
    76	    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts")
    77	    artifacts = r.json()["artifacts"]
    78	    for a in artifacts:
    79	        assert a["size_bytes"] > 0, a
    80	
    81	
    82	def test_manifest_404_missing_run(client: TestClient) -> None:
    83	    r = client.get("/api/runs/nonexistent_case__no_run/field-artifacts")
    84	    assert r.status_code == 404, r.text
    85	
    86	
    87	def test_manifest_400_or_404_malformed_run_id(client: TestClient) -> None:
    88	    r = client.get("/api/runs/no_separator_here/field-artifacts")
    89	    # parse_run_id raises 400; some FastAPI versions wrap as 422. Accept 400 or 404.
    90	    assert r.status_code in (400, 404, 422), r.text
    91	
    92	
    93	# ---------- Download endpoint ----------
    94	
    95	def test_download_residuals_csv_200(client: TestClient) -> None:
    96	    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts/residuals.csv")
    97	    assert r.status_code == 200, r.text
    98	    assert r.headers["content-type"].startswith("text/csv")
    99	    fixture = _FIXTURE_ROOT / "lid_driven_cavity" / "20260421T000000Z" / "residuals.csv"
   100	    assert int(r.headers.get("content-length", "-1")) == fixture.stat().st_size
   101	
   102	
   103	def test_download_vtk_200(client: TestClient) -> None:
   104	    """VTK file lives at VTK/lid_driven_cavity_2000.vtk — subpath URL (Codex round 1 HIGH #1)."""
   105	    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts/VTK/lid_driven_cavity_2000.vtk")
   106	    assert r.status_code == 200, r.text
   107	
   108	
   109	def test_download_404_traversal_filename(client: TestClient) -> None:
   110	    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts/..%2F..%2Fetc%2Fpasswd")
   111	    assert r.status_code == 404, r.text
   112	
   113	
   114	def test_download_404_traversal_runid_literal(client: TestClient) -> None:
   115	    """Codex round 1 HIGH #2: traversal via run_id literal '..' must be rejected."""
   116	    r = client.get("/api/runs/..__pwn/field-artifacts/residuals.csv")
   117	    assert r.status_code in (400, 404), r.text
   118	
   119	
   120	def test_download_404_traversal_runid_urlencoded(client: TestClient) -> None:
   121	    """Codex round 1 HIGH #2: url-encoded '%2e%2e' traversal must also be rejected."""
   122	    r = client.get("/api/runs/%2e%2e__pwn/field-artifacts/residuals.csv")
   123	    assert r.status_code in (400, 404), r.text
   124	
   125	
   126	def test_manifest_400_traversal_runid(client: TestClient) -> None:
   127	    """Codex round 1 HIGH #2: manifest endpoint also guards run_id segments."""
   128	    r = client.get("/api/runs/..__pwn/field-artifacts")
   129	    assert r.status_code in (400, 404), r.text
   130	
   131	
   132	def test_manifest_uses_subpath_when_collision(client: TestClient) -> None:
   133	    """Codex round 1 HIGH #1: filename field uses POSIX relative path so
   134	    subdir-nested files don't collide on basename. The fixture VTK lives in
   135	    a VTK/ subdir; its filename in the manifest must include that subpath."""
   136	    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts")
   137	    body = r.json()
   138	    vtk_names = {a["filename"] for a in body["artifacts"] if a["kind"] == "vtk"}
   139	    assert "VTK/lid_driven_cavity_2000.vtk" in vtk_names, vtk_names
   140	
   141	
   142	def test_list_rejects_malicious_manifest_timestamp(tmp_path: Path) -> None:
   143	    """Codex round 2 HIGH: an adversary-written manifest with
   144	    timestamp='../../outside' must NOT cause the LIST endpoint to enumerate
   145	    files outside reports/phase5_fields/. Previously download path was
   146	    guarded but list was not. Both now go through _resolve_artifact_dir."""
   147	    import json
   148	    # Build an isolated fields root with a malicious manifest.
   149	    fields_root = tmp_path / "fields"
   150	    case_dir = fields_root / "lid_driven_cavity"
   151	    (case_dir / "runs").mkdir(parents=True)
   152	    (case_dir / "20260421T000000Z").mkdir(parents=True)  # legit sibling
   153	    # Also plant a file outside the case to prove containment matters.
   154	    outside = tmp_path / "outside"
   155	    outside.mkdir()
   156	    (outside / "leaked.csv").write_text("secret\n", encoding="utf-8")
   157	    (case_dir / "runs" / "audit_real_run.json").write_text(
   158	        json.dumps({"timestamp": "../../outside", "case_id": "lid_driven_cavity",
   159	                    "run_label": "audit_real_run"}),
   160	        encoding="utf-8",
   161	    )
   162	    set_fields_root_for_testing(fields_root)
   163	    try:
   164	        c = TestClient(app)
   165	        r = c.get(f"/api/runs/{_RUN_ID}/field-artifacts")
   166	        # Must NOT return 200 with the leaked artifact — timestamp shape gate.
   167	        assert r.status_code == 404, r.text
   168	        # Download side also blocked.
   169	        r2 = c.get(f"/api/runs/{_RUN_ID}/field-artifacts/leaked.csv")
   170	        assert r2.status_code == 404, r2.text
   171	    finally:
   172	        set_fields_root_for_testing(_FIXTURE_ROOT)
   173	
   174	
   175	def test_download_404_missing(client: TestClient) -> None:
   176	    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts/does_not_exist.csv")
   177	    assert r.status_code == 404, r.text

exec
/bin/zsh -lc "nl -ba src/foam_agent_adapter.py | sed -n '6940,6995p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
  6940	                    continue
  6941	                try:
  6942	                    bits, _ = container.get_archive(src_in_cont)
  6943	                    buf = _io.BytesIO(b"".join(bits))
  6944	                    with _tarfile.open(fileobj=buf) as tar:
  6945	                        tar.extractall(path=artifact_dir)
  6946	                except Exception as e:  # noqa: BLE001
  6947	                    print(
  6948	                        f"[WARN] staging {sub} failed: {e!r}", file=_sys.stderr,
  6949	                    )
  6950	
  6951	            # (c) log.<solver> — already on host after _docker_exec.
  6952	            for logname in (
  6953	                "log.simpleFoam",
  6954	                "log.icoFoam",
  6955	                "log.buoyantFoam",
  6956	                "log.pimpleFoam",
  6957	            ):
  6958	                src = case_host_dir / logname
  6959	                if src.is_file():
  6960	                    (artifact_dir / logname).write_bytes(src.read_bytes())
  6961	                    break
  6962	
  6963	            # (d) Derive residuals.csv from residuals/0/residuals.dat if present.
  6964	            #     Per user ratification #3 — structured ASCII, no log regex.
  6965	            #     NOTE: container.get_archive('.../postProcessing/residuals')
  6966	            #     tar-extracts under basename `residuals/`, not the full
  6967	            #     `postProcessing/residuals/` path. Same applies to `sample/`.
  6968	            residuals_dat_candidates = list(
  6969	                artifact_dir.glob("residuals/*/residuals.dat")
  6970	            )
  6971	            if residuals_dat_candidates:
  6972	                try:
  6973	                    self._emit_residuals_csv(
  6974	                        residuals_dat_candidates[0],
  6975	                        artifact_dir / "residuals.csv",
  6976	                    )
  6977	                except Exception as e:  # noqa: BLE001
  6978	                    print(
  6979	                        f"[WARN] residuals.csv derivation failed: {e!r}",
  6980	                        file=_sys.stderr,
  6981	                    )
  6982	
  6983	            return artifact_dir
  6984	        except Exception as e:  # noqa: BLE001
  6985	            print(
  6986	                f"[WARN] _capture_field_artifacts failed: {e!r}", file=_sys.stderr,
  6987	            )
  6988	            return None
  6989	
  6990	    @staticmethod
  6991	    def _emit_residuals_csv(dat_path: Path, csv_path: Path) -> None:
  6992	        """Convert OpenFOAM v10 residuals function-object output to CSV.
  6993	
  6994	        The .dat format is whitespace-separated with a header line starting
  6995	        with `#`. We passthrough as CSV (comma-separated) with an explicit

exec
/bin/zsh -lc 'rg -n "phase7a_timestamp|_capture_field_artifacts|phase7a_case_id|_phase7a_timestamp|_PHASE7A_OPTED_IN" src scripts tests ui/backend/tests -S' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
scripts/phase5_audit_run.py:94:def _phase7a_timestamp() -> str:
scripts/phase5_audit_run.py:141:_PHASE7A_OPTED_IN: frozenset[str] = frozenset({"lid_driven_cavity"})
scripts/phase5_audit_run.py:277:    # _capture_field_artifacts writes to reports/phase5_fields/{case_id}/{ts}/.
scripts/phase5_audit_run.py:280:    ts = _phase7a_timestamp()
scripts/phase5_audit_run.py:283:        if case_id in _PHASE7A_OPTED_IN:
scripts/phase5_audit_run.py:286:            spec.metadata["phase7a_timestamp"] = ts
scripts/phase5_audit_run.py:287:            spec.metadata["phase7a_case_id"] = case_id
scripts/phase5_audit_run.py:301:        if case_id in _PHASE7A_OPTED_IN
src/foam_agent_adapter.py:607:                _phase7a_ts = _md.get("phase7a_timestamp")
src/foam_agent_adapter.py:608:                _phase7a_cid = _md.get("phase7a_case_id") or task_spec.name
src/foam_agent_adapter.py:612:                self._capture_field_artifacts(
src/foam_agent_adapter.py:6879:    def _capture_field_artifacts(
src/foam_agent_adapter.py:6986:                f"[WARN] _capture_field_artifacts failed: {e!r}", file=_sys.stderr,
src/models.py:81:    # driver-authored `phase7a_timestamp` (and `phase7a_case_id`) so
src/models.py:82:    # FoamAgentExecutor._capture_field_artifacts can stage OpenFOAM field

exec
/bin/zsh -lc "nl -ba src/foam_agent_adapter.py | sed -n '580,625p'; nl -ba src/models.py | sed -n '70,90p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   580	                return self._fail(
   581	                    f"{solver_name} failed:\n{solver_log}",
   582	                    time.monotonic() - t0,
   583	                    raw_output_path=raw_output_path,
   584	                )
   585	
   586	            # 6.5. 执行 postProcess 提取完整场数据用于关键物理量计算
   587	            # writeObjects: 写出 U/p/phi 等场文件
   588	            # writeCellCentres: 写出 Cx/Cy/Cz cell center 坐标 (用于定位 probe 坐标)
   589	            # 注意: 用 -funcs '(...)' 而非 -func，OpenFOAM 才能识别多个 functionObject
   590	            post_ok, post_log = self._docker_exec(
   591	                "postProcess -funcs '(writeObjects writeCellCentres)' -latestTime", case_cont_dir, 120,
   592	            )
   593	            # postProcess 失败不阻塞主流程（后续解析会处理无数据的情况）
   594	
   595	            # 7. 复制 postProcess 输出的场文件到宿主机
   596	            # postProcess 写出到 latestTime 目录，需要复制回 host 才能解析
   597	            self._copy_postprocess_fields(container, case_cont_dir, case_host_dir)
   598	
   599	            # 7.5. [Phase 7a] Stage field artifacts (VTK + sample CSV + residuals)
   600	            #      BEFORE the finally-block tears down case_host_dir.
   601	            #      Best-effort: any failure MUST NOT fail the run — comparator
   602	            #      scalar extraction below still needs to succeed.
   603	            _phase7a_ts: Optional[str] = None
   604	            _phase7a_cid: Optional[str] = None
   605	            try:
   606	                _md = getattr(task_spec, "metadata", None) or {}
   607	                _phase7a_ts = _md.get("phase7a_timestamp")
   608	                _phase7a_cid = _md.get("phase7a_case_id") or task_spec.name
   609	            except Exception:
   610	                _phase7a_ts = None
   611	            if _phase7a_ts and _phase7a_cid:
   612	                self._capture_field_artifacts(
   613	                    container,
   614	                    case_cont_dir,
   615	                    case_host_dir,
   616	                    _phase7a_cid,
   617	                    _phase7a_ts,
   618	                )
   619	
   620	            # 8. 解析 log 文件
   621	            log_path = case_host_dir / f"log.{solver_name}"
   622	            residuals, key_quantities = self._parse_solver_log(log_path, solver_name, task_spec)
   623	
   624	            # 9. 从 writeObjects 输出的场文件提取 case-specific 关键物理量
   625	            key_quantities = self._parse_writeobjects_fields(
    70	    flow_type: FlowType
    71	    steady_state: SteadyState
    72	    compressibility: Compressibility
    73	    Re: Optional[float] = None
    74	    Ra: Optional[float] = None
    75	    Re_tau: Optional[float] = None
    76	    Ma: Optional[float] = None
    77	    boundary_conditions: Dict[str, Any] = field(default_factory=dict)
    78	    description: str = ""
    79	    notion_task_id: Optional[str] = None
    80	    # Phase 7a — optional per-run metadata bag. Currently carries the
    81	    # driver-authored `phase7a_timestamp` (and `phase7a_case_id`) so
    82	    # FoamAgentExecutor._capture_field_artifacts can stage OpenFOAM field
    83	    # artifacts into reports/phase5_fields/{case_id}/{timestamp}/ before the
    84	    # finally-block tears down the case dir. Default-None keeps the
    85	    # dataclass backward-compatible for all 79/79 existing tests.
    86	    metadata: Optional[Dict[str, Any]] = None
    87	
    88	
    89	@dataclass
    90	class ExecutionResult:

codex
The previous Round 1 status report is consistent with current code for #1, #3, and #4. I’m checking one malformed-manifest edge before finalizing, because the new resolver is supposed to fail closed on bad manifest data.
exec
/bin/zsh -lc ".venv/bin/python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
import json
from fastapi.testclient import TestClient
from ui.backend.main import app
from ui.backend.services.field_artifacts import set_fields_root_for_testing

with TemporaryDirectory() as d:
    fields = Path(d) / 'fields'
    case = fields / 'lid_driven_cavity'
    (case / 'runs').mkdir(parents=True)
    (case / '20260421T000000Z').mkdir(parents=True)
    ((case / '20260421T000000Z') / 'residuals.csv').write_text('x\\n', encoding='utf-8')
    for payload in ([\"not\", \"dict\"], {\"timestamp\": 123}, {\"timestamp\": \"../../outside\"}, {\"timestamp\": \"..%2Foutside\"}):
        (case / 'runs' / 'audit_real_run.json').write_text(json.dumps(payload), encoding='utf-8')
        set_fields_root_for_testing(fields)
        c = TestClient(app, raise_server_exceptions=False)
        r = c.get('/api/runs/lid_driven_cavity__audit_real_run/field-artifacts')
        print(type(payload).__name__, payload, '->', r.status_code)
set_fields_root_for_testing(None)
PY" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 240ms:
list ['not', 'dict'] -> 500
dict {'timestamp': 123} -> 404
dict {'timestamp': '../../outside'} -> 404
dict {'timestamp': '..%2Foutside'} -> 404

exec
/bin/zsh -lc ".venv/bin/python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
import json, os
from fastapi.testclient import TestClient
from ui.backend.main import app
from ui.backend.services.field_artifacts import set_fields_root_for_testing

with TemporaryDirectory() as d:
    base = Path(d)
    fields = base / 'fields'
    case = fields / 'lid_driven_cavity'
    ts = case / '20260421T000000Z'
    (case / 'runs').mkdir(parents=True)
    ts.mkdir(parents=True)
    outside = base / 'outside.csv'
    outside.write_text('secret\\n', encoding='utf-8')
    os.symlink(outside, ts / 'outside.csv')
    (case / 'runs' / 'audit_real_run.json').write_text(json.dumps({'timestamp': '20260421T000000Z'}), encoding='utf-8')
    set_fields_root_for_testing(fields)
    c = TestClient(app, raise_server_exceptions=False)
    for url in ['/api/runs/lid_driven_cavity__audit_real_run/field-artifacts', '/api/runs/lid_driven_cavity__audit_real_run/field-artifacts/outside.csv']:
        r = c.get(url)
        print(url, '->', r.status_code, r.text[:80])
set_fields_root_for_testing(None)
PY" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 225ms:
/api/runs/lid_driven_cavity__audit_real_run/field-artifacts -> 500 Internal Server Error
/api/runs/lid_driven_cavity__audit_real_run/field-artifacts/outside.csv -> 404 {"detail":"artifact not found"}

codex
APPROVED_WITH_COMMENTS

Round-2 HIGH is closed. `list_artifacts()` and `resolve_artifact_path()` now both go through `_resolve_artifact_dir()`, and the malicious `timestamp="../../outside"` case returns 404 for both list and download. The added regression is present and covered by the backend suite.

Round-1 status:
- #1 basename collision: closed. Manifest now carries POSIX subpaths and the route accepts `{filename:path}`.
- #3 metadata over-application: closed. Phase 7a metadata/manifest writing is gated to opted-in cases and requires a non-empty artifact dir.
- #4 SHA cache precision: closed. Cache key uses `st_mtime_ns`.

Verification run: `PYTHONPATH=. .venv/bin/pytest ui/backend/tests/ -q` -> `95 passed in 23.95s`.

One non-blocking hardening comment: malformed valid-JSON manifests that are not objects still 500 because `_resolve_artifact_dir()` assumes `manifest.get(...)` exists at [field_artifacts.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/field_artifacts.py:125). I also saw list 500 on an out-of-dir symlink inside the artifact tree at [field_artifacts.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/field_artifacts.py:173). Neither reopens the timestamp traversal issue, but both should fail closed to 404 in a cleanup pass.


tokens used
171,882
APPROVED_WITH_COMMENTS

Round-2 HIGH is closed. `list_artifacts()` and `resolve_artifact_path()` now both go through `_resolve_artifact_dir()`, and the malicious `timestamp="../../outside"` case returns 404 for both list and download. The added regression is present and covered by the backend suite.

Round-1 status:
- #1 basename collision: closed. Manifest now carries POSIX subpaths and the route accepts `{filename:path}`.
- #3 metadata over-application: closed. Phase 7a metadata/manifest writing is gated to opted-in cases and requires a non-empty artifact dir.
- #4 SHA cache precision: closed. Cache key uses `st_mtime_ns`.

Verification run: `PYTHONPATH=. .venv/bin/pytest ui/backend/tests/ -q` -> `95 passed in 23.95s`.

One non-blocking hardening comment: malformed valid-JSON manifests that are not objects still 500 because `_resolve_artifact_dir()` assumes `manifest.get(...)` exists at [field_artifacts.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/field_artifacts.py:125). I also saw list 500 on an out-of-dir symlink inside the artifact tree at [field_artifacts.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/field_artifacts.py:173). Neither reopens the timestamp traversal issue, but both should fail closed to 404 in a cleanup pass.


