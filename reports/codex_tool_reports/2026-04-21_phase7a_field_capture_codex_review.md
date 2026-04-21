2026-04-21T08:32:55.236537Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-research-deerflow/SKILL.md: missing YAML frontmatter delimited by ---
2026-04-21T08:32:55.236606Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-report-pretext/SKILL.md: missing YAML frontmatter delimited by ---
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
session id: 019daf2b-d129-7042-aec0-b4d4e88dc786
--------
user
Review Phase 7a field-artifacts capture: commits 8bf2cfb (src adapter + driver) and f507b9e (backend route) plus uncommitted Wave-3 fixes to src/foam_agent_adapter.py. Three files critical:

1. src/foam_agent_adapter.py — _emit_phase7a_function_objects (controlDict functions{} block) + _capture_field_artifacts (foamToVTK + docker get_archive + residuals.csv derivation) + _emit_residuals_csv. Wave 3 fixes: (a) sample block dict-form {uCenterline{type uniform;...}} → list-form (uCenterline{type lineUniform;...}) for OpenFOAM v10; (b) residuals glob path postProcessing/residuals/ → residuals/ after docker get_archive tar-extract collapses under basename. Check: call-site BEFORE finally-teardown at FoamAgentExecutor.execute, exceptions properly swallowed so foamToVTK failure does not fail comparator, no shell injection via task_spec.metadata values, no regression to existing _copy_postprocess_fields.

2. scripts/phase5_audit_run.py — timestamp threading (YYYYMMDDTHHMMSSZ via task_spec.metadata), per-run manifest writer reports/phase5_fields/{case}/runs/{label}.json, field_artifacts YAML key in audit_real_run_measurement.yaml (manifest-ref only with manifest_path_rel + run_label, NO embedded timestamp). Check: test_phase5_byte_repro.py subset-check safety preserved, fallback when artifact_dir missing, other-case compat (only LDC has metadata populated).

3. ui/backend/services/field_artifacts.py + routes/field_artifacts.py + schemas/validation.py — FileResponse + traversal-safe _resolve_artifact_path (NOT StaticFiles per R#1), SHA256 cache keyed on (resolved_path, mtime, size), explicit MIME map, traversal defense rejects .. segments + "." + empty. parse_run_id uses rpartition("__"). Kind order explicit _KIND_ORDER={"vtk":0,"csv":1,"residual_log":2}.

Check: (i) path-traversal defense completeness including URL-encoded cases, (ii) SHA256 cache stale-hash risk on rapid writes, (iii) FoamAgentExecutor try-block ordering regression, (iv) byte-repro violations in new YAML key, and (v) EXPLICIT architectural flag — sample/{0,500,1000}/uCenterline.xy share the same basename. Currently rglob returns first match. Should URL scheme be extended with subpath (e.g. /sample/500/uCenterline.xy) or is latest-wins MVP-acceptable with a TODO for Phase 7c?

Integration evidence at .planning/phases/07a-field-capture/_integration_evidence.txt shows: 8 artifacts produced, HTTP 200 + valid SHA256, 90/90 pytest, traversal 404 confirmed, real OpenFOAM simpleFoam converged in 1024 iter / 27s.

Reply with structured verdict: APPROVED / APPROVED_WITH_COMMENTS / CHANGES_REQUIRED, then numbered findings with severity (HIGH/MED/LOW) and file:line anchors.
codex
I’ll review this in the requested acceptance posture: no new development, just inspect the current tree, the specified commits, and the uncommitted Wave-3 adapter fixes. I’ll load the repo/GSD context briefly, then read the target files and relevant tests/evidence before giving a line-anchored verdict.
exec
/bin/zsh -lc 'rg -n "cfd-harness-unified|Phase 8|Phase 9|PHASE9|Phase 7a|field" /Users/Zhuanz/.codex/memories/MEMORY.md' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
115:- OpenClaw, AI-CFD, Notion作为指挥中枢，Github作为唯一代码真相库, ~/.openclaw/openclaw.json, plugins.allow, openclaw config validate --json, MAIN_OK, CODEX_BUILDER_OK, CLAUDE_REVIEW_OK, NOTION_SYNC_OK, cfd-harness-unified
135:- The real live config surface was `~/.openclaw/openclaw.json`; the actual repo truth for this rollout was `/Users/Zhuanz/Desktop/cfd-harness-unified`, not the chat thread cwd [Task 1]
356:# Task Group: cfd-harness-unified governance closeout and planning gates
358:scope: Close out accepted phases in `cfd-harness-unified`, normalize Notion-vs-repo naming drift, and keep future phases planning-only until the explicit solver/routing gate is reviewed.
359:applies_to: cwd=/Users/Zhuanz/Desktop/cfd-harness-unified; reuse_rule=safe for this repo’s Notion-governed phase/gate work, but phase/task IDs and review packets are rollout-specific.
361:## Task 1: Close Phase 8 and reconcile stale governance evidence
365:- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, Phase 8 closeout and evidence normalization)
369:- Phase 8, AutoVerifier, 13/13, knowledge/whitelist.yaml, ai_cfd_cold_start_whitelist.yaml, Canonical Docs Type=Report, Phase 8 Done, naming drift
371:## Task 2: Open Phase 9 as planning-only and keep solver expansion bounded
375:- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, Phase 9 kept as planning-only with decision-tree packet))
379:- Phase 9 planning-only, PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md, PHASE9_MODEL_ROUTING_BASELINE_PLAN.md, PHASE9_ACTIVATION_REVIEW_PACKET.md, replay_manifest, SU2 CLI Harness Skill, foam_agent_adapter.py
385:- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, handoff prompt prepared instead of silent activation))
400:- Phase 9 must start from a bounded decision tree: keep single-engine OpenFOAM, allow reference-only external solver surfaces, or open one bounded proof slice; anything broader still needs review [Task 2]
406:- Symptom: planning work accidentally looks like activation -> cause: Phase 9 docs/task text are not explicit enough about `Planned` vs `Active` -> fix: state planning-only mode in phase page, tasks, dashboard summary, and review packet [Task 2]
439:- rollout_summaries/2026-04-12T15-33-54-ByPi-jerry_ai_cfd_notion_sync_and_cfd_harness_unified_context_mis.md (cwd=/Users/Zhuanz/Documents/20260330 Jerry AI CFD Project, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/12/rollout-2026-04-12T23-33-54-019d8253-fa8b-7f40-9775-46e6e03db8ac.jsonl, updated_at=2026-04-16T17:03:18+00:00, thread_id=019d8253-fa8b-7f40-9775-46e6e03db8ac, later cfd-harness-unified instruction block correctly treated as mismatch)
532:- The workbench’s fingerprint board and onboarding action board both reused existing payload fields; future UI additions should prefer wiring into current payloads over new backend contracts [Task 3]
602:- when refining the cockpit, the user said the UI "不应该只给一个 `Deploy feedback / deploy_position_percent`，而应该给用户更直观的 `VDT` 可调控件" -> use the user’s domain language in the UI even if the backend still uses the older field names [Task 1]
621:- Symptom: the UI feels like an internal engineer tool rather than a demo for domain users -> cause: internal fields like `deploy_position_percent` dominate the first screen -> fix: expose VDT-first controls, flatten logic notes, and demote summary panels [Task 1]
691:- when the user said "你是 independent approval authority… 你不是 corrected request packet 作者… 你不是 Phase 8 executor" -> preserve strict role separation between approval, review, execution, and freeze authority in this repo [Task 4]
732:- phase1, nl_postprocess.py, tests/test_phase1_nl_postprocess.py, PYTHONDONTWRITEBYTECODE=1 pytest -q -s -p no:cacheprovider, TypeError: 'in <string>' requires string as left operand, not list, UnboundLocalError missing, asset normalization, field_data vs field
786:- `ResultManifest` / `ResultAsset` in `knowledge_compiler/phase1/schema.py` are the authoritative Phase 1 data model; manifest assets use concrete `asset_type` values like `field`, so NL postprocess resource checks need normalization instead of renaming the manifest contract [Task 1]
799:- Symptom: a CorrectionSpec gate over-claims current schema support -> cause: `source_case_id` is not a declared top-level dataclass field -> fix: preserve the gate as an object/serialized-payload validator with a shimmed source-case lookup, and label that contract explicitly [Task 4]
869:- Phase 2, compiler_layer, CanonicalCompiler, KnowledgePublisher, CanonicalSpec, ParsedTeach, CompiledKnowledge, Phase2GateExecutor, G1-P2, G2-P2, Enum, Python 3.9 dataclass field order

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

codex
I’m using the GSD code-review skill because this is a phase-scoped correctness/security review. I also found prior memory for this repo; I’ll treat it as governance context only and verify the current code directly from the worktree.
exec
/bin/zsh -lc "sed -n '1,220p' "'$HOME/.Codex/get-shit-done/workflows/code-review.md' in /Users/Zhuanz/Desktop/cfd-harness-unified
 exited 1 in 0ms:
sed: /Users/Zhuanz/.Codex/get-shit-done/workflows/code-review.md: No such file or directory

exec
/bin/zsh -lc 'git status --short' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
 M .planning/STATE.md
 M reports/cylinder_crossflow/report.md
 M reports/deep_acceptance/visual_acceptance_report.html
 M reports/deep_acceptance/visual_acceptance_report_manifest.json
 M reports/differential_heated_cavity/report.md
 M reports/rayleigh_benard_convection/report.md
 M reports/turbulent_flat_plate/report.md
 M src/foam_agent_adapter.py
 M ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml
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

exec
/bin/zsh -lc 'git log --oneline --decorate -n 12' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
1cc18b2 (HEAD -> main) docs(phase-7a/plan-02): Wave 2 SUMMARY — field-artifacts route landed, 90/90 tests green
f507b9e feat(phase-7a/plan-02): field-artifacts backend route + schema + service + tests
ac4421e docs(phase-7a/plan-01): update STATE/ROADMAP after Wave 1 commit
8bf2cfb feat(phase-7a/plan-01): LDC field capture — controlDict functions{} + executor + driver
81907c2 (origin/main, origin/HEAD) docs(phase-7a): plan field post-processing capture (Sprint 1 LDC MVP)
e4dd1d9 docs(roadmap): add Phase 7 — Scientific-grade CFD vs gold reporting
8118122 docs(DEC-V61-030): mark notion_sync_status synced + close pending checklist
c4207f7 feat(Q-5): close LDC gold-accuracy gate — re-transcribe from Ghia 1982 (DEC-V61-030)
c84e626 docs(DEC-V61-029): Notion sync backfill
e037389 feat(phase-5b): close LDC simpleFoam migration + file Q-5 gold accuracy (DEC-V61-029)
1f87718 fix(phase-5b/plan-01): derive LDC x_tol from mesh spacing (Codex HIGH)
002a6fb fix(phase-5b/plan-01): correct LDC blockMesh faces + add bottom wall

exec
/bin/zsh -lc 'git diff -- src/foam_agent_adapter.py' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
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

exec
/bin/zsh -lc 'git show --stat --oneline 8bf2cfb' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
8bf2cfb feat(phase-7a/plan-01): LDC field capture — controlDict functions{} + executor + driver
 .../phases/07a-field-capture/07a-01-SUMMARY.md     | 174 +++++++++++++++
 scripts/phase5_audit_run.py                        |  79 ++++++-
 src/foam_agent_adapter.py                          | 244 ++++++++++++++++++++-
 src/models.py                                      |   7 +
 4 files changed, 496 insertions(+), 8 deletions(-)

exec
/bin/zsh -lc 'git show --stat --oneline f507b9e' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
f507b9e feat(phase-7a/plan-02): field-artifacts backend route + schema + service + tests
 ui/backend/main.py                                 |   2 +
 ui/backend/routes/field_artifacts.py               |  68 ++++++++
 ui/backend/schemas/validation.py                   |  51 ++++++
 ui/backend/services/field_artifacts.py             | 179 +++++++++++++++++++++
 ui/backend/services/run_ids.py                     |  32 ++++
 .../VTK/lid_driven_cavity_2000.vtk                 |  39 +++++
 .../20260421T000000Z/residuals.csv                 |   6 +
 .../20260421T000000Z/uCenterline_U_p.xy            |  17 ++
 .../lid_driven_cavity/runs/audit_real_run.json     |   6 +
 .../field_artifacts_manifest.yaml                  |  14 ++
 ui/backend/tests/test_field_artifacts_route.py     | 115 +++++++++++++
 11 files changed, 529 insertions(+)

codex
The working tree is dirty, and the only relevant uncommitted code delta I see so far is in `src/foam_agent_adapter.py`: the OpenFOAM v10 `sampledSets` list-form fix and the `residuals/` extraction-path fix. I’m now drilling into call ordering, artifact path resolution, and byte-repro behavior.
exec
/bin/zsh -lc "rg -n \"def _emit_phase7a_function_objects|def _capture_field_artifacts|def _emit_residuals_csv|class FoamAgentExecutor|def execute\\(\" src/foam_agent_adapter.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
40:    def execute(self, task_spec: TaskSpec) -> ExecutionResult:
384:class FoamAgentExecutor:
418:    def execute(self, task_spec: TaskSpec) -> ExecutionResult:
665:    def _emit_phase7a_function_objects(turbulence_model: str = "laminar") -> str:
6879:    def _capture_field_artifacts(
6991:    def _emit_residuals_csv(dat_path: Path, csv_path: Path) -> None:

exec
/bin/zsh -lc 'rg -n "field_artifacts|manifest|run_label|metadata|timestamp|phase5_fields" scripts/phase5_audit_run.py' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
14:    reports/phase5_audit/{timestamp}_{case_id}_raw_run.json  (stdout/stderr)
46:FIELDS_DIR = REPO_ROOT / "reports" / "phase5_fields"
94:def _phase7a_timestamp() -> str:
95:    """Shared timestamp format — matches _write_raw_capture."""
99:def _write_field_artifacts_run_manifest(
100:    case_id: str, run_label: str, timestamp: str
102:    """Write reports/phase5_fields/{case_id}/runs/{run_label}.json so the
103:    backend route can resolve run_label -> timestamp directory in O(1).
105:    Returns the manifest Path on success, None if the artifact dir never
108:    artifact_dir = FIELDS_DIR / case_id / timestamp
111:            f"[audit] [WARN] field artifact dir missing, skipping manifest: {artifact_dir}",
117:    manifest = runs_dir / f"{run_label}.json"
119:        "run_label": run_label,
120:        "timestamp": timestamp,
124:    manifest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
125:    return manifest
132:    field_artifacts_ref: "dict | None" = None,
141:        "run_metadata": {
202:    # Phase 7a — field artifacts reference (manifest path only; NO timestamps
204:    # The manifest at the referenced path contains the timestamp.
205:    if field_artifacts_ref is not None:
206:        doc["field_artifacts"] = field_artifacts_ref
220:        "# re-runs (modulo timestamp + commit_sha) is enforced by\n"
260:    # Phase 7a — author the single shared timestamp up front; the executor-side
261:    # _capture_field_artifacts writes to reports/phase5_fields/{case_id}/{ts}/.
262:    ts = _phase7a_timestamp()
267:        # on the metadata keys — staging runs best-effort.
268:        if spec.metadata is None:
269:            spec.metadata = {}
270:        spec.metadata["phase7a_timestamp"] = ts
271:        spec.metadata["phase7a_case_id"] = case_id
279:    # Phase 7a — write per-run manifest + build field_artifacts_ref dict iff
281:    run_label = "audit_real_run"
282:    manifest_path = _write_field_artifacts_run_manifest(case_id, run_label, ts)
283:    field_artifacts_ref: "dict | None" = None
284:    if manifest_path is not None:
285:        field_artifacts_ref = {
286:            "manifest_path_rel": str(manifest_path.relative_to(REPO_ROOT)),
287:            "run_label": run_label,
288:            # Deliberately NO timestamp string here (byte-repro): resolve via manifest.
292:        case_id, report, commit_sha, field_artifacts_ref=field_artifacts_ref,
296:    verdict = doc["run_metadata"]["expected_verdict"]
305:        "field_artifacts_manifest": (
306:            str(manifest_path.relative_to(REPO_ROOT)) if manifest_path else None

exec
/bin/zsh -lc 'rg -n "def _resolve_artifact_path|SHA256|sha256|_KIND_ORDER|MIME|mtime|size|parse_run_id|rpartition|FileResponse|field_artifacts" ui/backend/services/field_artifacts.py ui/backend/routes/field_artifacts.py ui/backend/schemas/validation.py ui/backend/services/run_ids.py' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
ui/backend/services/run_ids.py:4:We use rpartition on the last "__" so case_ids with internal underscores
ui/backend/services/run_ids.py:12:def parse_run_id(run_id: str) -> tuple[str, str]:
ui/backend/services/run_ids.py:15:    Uses rpartition on '__' so the label is the LAST token; case_id keeps any
ui/backend/services/run_ids.py:17:    rpartition is resilient if that changes.
ui/backend/services/run_ids.py:26:    case_id, _, run_label = run_id.rpartition("__")
ui/backend/schemas/validation.py:43:  via FoamAgentExecutor — not curated, not synthesized. Audit-grade
ui/backend/schemas/validation.py:232:    sha256: str = Field(
ui/backend/schemas/validation.py:235:        description="Lowercase hex SHA256 of file bytes.",
ui/backend/schemas/validation.py:237:    size_bytes: int = Field(..., ge=0)
ui/backend/routes/field_artifacts.py:4:GET /api/runs/{run_id}/field-artifacts/{filename}   → FileResponse
ui/backend/routes/field_artifacts.py:6:Pattern mirrors ui/backend/routes/audit_package.py:284-342 (FileResponse +
ui/backend/routes/field_artifacts.py:14:from fastapi.responses import FileResponse
ui/backend/routes/field_artifacts.py:17:from ui.backend.services.field_artifacts import (
ui/backend/routes/field_artifacts.py:25:# MIME map — explicit per user ratification #1 rationale (no StaticFiles guessing).
ui/backend/routes/field_artifacts.py:46:def get_field_artifacts(run_id: str) -> FieldArtifactsResponse:
ui/backend/routes/field_artifacts.py:61:def download_field_artifact(run_id: str, filename: str) -> FileResponse:
ui/backend/routes/field_artifacts.py:64:    return FileResponse(
ui/backend/services/field_artifacts.py:4:(written by scripts/phase5_audit_run.py::_write_field_artifacts_run_manifest),
ui/backend/services/field_artifacts.py:6:the FastAPI route in ui/backend/routes/field_artifacts.py.
ui/backend/services/field_artifacts.py:9:(FileResponse + traversal-safe _resolve_bundle_file) per user ratification #1.
ui/backend/services/field_artifacts.py:28:from ui.backend.services.run_ids import parse_run_id
ui/backend/services/field_artifacts.py:30:# Repo root: 3 levels up from this file (ui/backend/services/field_artifacts.py)
ui/backend/services/field_artifacts.py:49:_KIND_ORDER: dict[str, int] = {"vtk": 0, "csv": 1, "residual_log": 2}
ui/backend/services/field_artifacts.py:51:# SHA256 cache keyed on (abs_path, st_mtime, st_size) per 07a-RESEARCH.md §2.6.
ui/backend/services/field_artifacts.py:55:def sha256_of(path: Path) -> str:
ui/backend/services/field_artifacts.py:56:    """Compute (or return cached) SHA256 hex digest for `path`.
ui/backend/services/field_artifacts.py:58:    Cache key: (absolute_path, st_mtime, st_size). Mtime+size collision would
ui/backend/services/field_artifacts.py:62:    key = (str(path.resolve()), st.st_mtime, st.st_size)
ui/backend/services/field_artifacts.py:66:    h = hashlib.sha256()
ui/backend/services/field_artifacts.py:103:    case_id, run_label = parse_run_id(run_id)
ui/backend/services/field_artifacts.py:129:                sha256=sha256_of(p),
ui/backend/services/field_artifacts.py:130:                size_bytes=p.stat().st_size,
ui/backend/services/field_artifacts.py:133:    items.sort(key=lambda a: (_KIND_ORDER.get(a.kind, 99), a.filename))
ui/backend/services/field_artifacts.py:156:    case_id, run_label = parse_run_id(run_id)

exec
/bin/zsh -lc 'rg -n "field_artifacts|byte|subset|audit_real_run_measurement|timestamp|manifest_path_rel|run_label" tests ui/backend/tests scripts src .planning/phases/07a-field-capture/_integration_evidence.txt' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
.planning/phases/07a-field-capture/_integration_evidence.txt:6:[audit] lid_driven_cavity → FAIL · 5.2s · audit_real_run_measurement.yaml
.planning/phases/07a-field-capture/_integration_evidence.txt:24:# re-runs (modulo timestamp + commit_sha) is enforced by
.planning/phases/07a-field-capture/_integration_evidence.txt:25:# test_phase5_byte_repro.py.
.planning/phases/07a-field-capture/_integration_evidence.txt:59:[audit] lid_driven_cavity → FAIL · 26.9s · audit_real_run_measurement.yaml
.planning/phases/07a-field-capture/_integration_evidence.txt:79:  "run_label": "audit_real_run",
.planning/phases/07a-field-capture/_integration_evidence.txt:80:  "timestamp": "20260421T082238Z",
.planning/phases/07a-field-capture/_integration_evidence.txt:88:[audit] lid_driven_cavity → FAIL · 27.4s · audit_real_run_measurement.yaml
.planning/phases/07a-field-capture/_integration_evidence.txt:120:ui/backend/tests/test_phase5_byte_repro.py::test_at_least_one_audit_fixture_exists PASSED [  8%]
.planning/phases/07a-field-capture/_integration_evidence.txt:121:ui/backend/tests/test_phase5_byte_repro.py::test_audit_fixture_schema_contract[backward_facing_step] PASSED [ 16%]
.planning/phases/07a-field-capture/_integration_evidence.txt:122:ui/backend/tests/test_phase5_byte_repro.py::test_audit_fixture_schema_contract[circular_cylinder_wake] PASSED [ 25%]
.planning/phases/07a-field-capture/_integration_evidence.txt:123:ui/backend/tests/test_phase5_byte_repro.py::test_audit_fixture_schema_contract[differential_heated_cavity] PASSED [ 33%]
.planning/phases/07a-field-capture/_integration_evidence.txt:124:ui/backend/tests/test_phase5_byte_repro.py::test_audit_fixture_schema_contract[duct_flow] PASSED [ 41%]
.planning/phases/07a-field-capture/_integration_evidence.txt:125:ui/backend/tests/test_phase5_byte_repro.py::test_audit_fixture_schema_contract[impinging_jet] PASSED [ 50%]
.planning/phases/07a-field-capture/_integration_evidence.txt:126:ui/backend/tests/test_phase5_byte_repro.py::test_audit_fixture_schema_contract[lid_driven_cavity] PASSED [ 58%]
.planning/phases/07a-field-capture/_integration_evidence.txt:127:ui/backend/tests/test_phase5_byte_repro.py::test_audit_fixture_schema_contract[naca0012_airfoil] PASSED [ 66%]
.planning/phases/07a-field-capture/_integration_evidence.txt:128:ui/backend/tests/test_phase5_byte_repro.py::test_audit_fixture_schema_contract[plane_channel_flow] PASSED [ 75%]
.planning/phases/07a-field-capture/_integration_evidence.txt:129:ui/backend/tests/test_phase5_byte_repro.py::test_audit_fixture_schema_contract[rayleigh_benard_convection] PASSED [ 83%]
.planning/phases/07a-field-capture/_integration_evidence.txt:130:ui/backend/tests/test_phase5_byte_repro.py::test_audit_fixture_schema_contract[turbulent_flat_plate] PASSED [ 91%]
.planning/phases/07a-field-capture/_integration_evidence.txt:131:ui/backend/tests/test_phase5_byte_repro.py::test_audit_fixtures_nondeterministic_fields_are_isolated PASSED [100%]
.planning/phases/07a-field-capture/_integration_evidence.txt:152:ui/backend/tests/test_field_artifacts_route.py ...........               [ 64%]
.planning/phases/07a-field-capture/_integration_evidence.txt:155:ui/backend/tests/test_phase5_byte_repro.py ............                  [ 90%]
.planning/phases/07a-field-capture/_integration_evidence.txt:159:{"run_id":"lid_driven_cavity__audit_real_run","case_id":"lid_driven_cavity","run_label":"audit_real_run","timestamp":"20260421T082340Z","artifacts":[{"kind":"vtk","filename":"allPatches_1024.vtk","url":"/api/runs/lid_driven_cavity__audit_real_run/field-artifacts/allPatches_1024.vtk","sha256":"a6113287904d744a524ef401ec7f5f389e0c8842988d8ba1df3e9c10f9f376dc","size_bytes":45784},{"kind":"vtk","filename":"ldc_59058_1776759820768_1024.vtk","url":"/api/runs/lid_driven_cavity__audit_real_run/field-artifacts/ldc_59058_1776759820768_1024.vtk","sha256":"bd454c0b561e06a6e41f601cf38773d8236d3b254d2e612ccd3c7b4d459da0c6","size_bytes":3155888},{"kind":"csv","filename":"uCenterline.xy","url":"/api/runs/lid_driven_cavity__audit_real_run/field-artifacts/uCenterline.xy","sha256":"c537678e916036fe0845a0452605e0ddee8c2bfd7a96eaa808dd73f59aa619cf","size_bytes":9099},{"kind":"csv","filename":"uCenterline.xy","url":"/api/runs/lid_driven_cavity__audit_real_run/field-artifacts/uCenterline.xy","sha256":"bc95a829b8e5c40a935692125daa76681050e7eaa03f8c509467616b73a0f461","size_bytes":9099},{"kind":"csv","filename":"uCenterline.xy","url":"/api/runs/lid_driven_cavity__audit_real_run/field-artifacts/uCenterline.xy","sha256":"6ba22156053d470b18da7eaab0eb35ab974267c941d8693963d4d596112f9369","size_bytes":9099},{"kind":"residual_log","filename":"log.simpleFoam","url":"/api/runs/lid_driven_cavity__audit_real_run/field-artifacts/log.simpleFoam","sha256":"a6f33f3c4f6cd94f7c0f9e2313d4e38115f051668d0086e0abfff28efd80af7f","size_bytes":490559},{"kind":"residual_log","filename":"residuals.csv","url":"/api/runs/lid_driven_cavity__audit_real_run/field-artifacts/residuals.csv","sha256":"bd734927184e0afd5467eeb1de045d9deed32164d880f345c3beb1669528238e","size_bytes":43972},{"kind":"residual_log","filename":"residuals.dat","url":"/api/runs/lid_driven_cavity__audit_real_run/field-artifacts/residuals.dat","sha256":"9e0b4a90a3acacc07414fbc3227e808fbcfa6d4a9192e6ab7bf3ff86db70256f","size_bytes":55394}]}
.planning/phases/07a-field-capture/_integration_evidence.txt:172:ui/backend/tests/test_phase5_byte_repro.py ............                  [ 90%]
src/foam_agent_adapter.py:607:                _phase7a_ts = _md.get("phase7a_timestamp")
src/foam_agent_adapter.py:612:                self._capture_field_artifacts(
src/foam_agent_adapter.py:6774:    def _make_tarball(src_dir: Path) -> bytes:
src/foam_agent_adapter.py:6775:        """把目录内容打包成 tarball bytes（用于 put_archive）。
src/foam_agent_adapter.py:6820:                            dest_path.write_bytes(member.read())
src/foam_agent_adapter.py:6879:    def _capture_field_artifacts(
src/foam_agent_adapter.py:6885:        timestamp: str,
src/foam_agent_adapter.py:6904:        artifact_dir = repo_root / "reports" / "phase5_fields" / case_id / timestamp
src/foam_agent_adapter.py:6960:                    (artifact_dir / logname).write_bytes(src.read_bytes())
src/foam_agent_adapter.py:6986:                f"[WARN] _capture_field_artifacts failed: {e!r}", file=_sys.stderr,
ui/backend/tests/test_audit_package_route.py:98:    def test_identical_posts_produce_byte_identical_zip(self, client):
ui/backend/tests/test_audit_package_route.py:100:        HMAC signature (Codex PR-5d HIGH #2 — byte-reproducibility).
ui/backend/tests/test_audit_package_route.py:115:        # Signature comes from canonical manifest + zip bytes → must match.
ui/backend/tests/test_audit_package_route.py:160:        zpath.write_bytes(resp.content)
ui/backend/tests/test_audit_package_route.py:213:        zip_bytes = client.get(f"/api/audit-packages/{bid}/bundle.zip").content
ui/backend/tests/test_audit_package_route.py:219:        assert verify(manifest, zip_bytes, sig_text, key) is True
ui/backend/tests/test_audit_package_route.py:227:        zip_bytes = client.get(f"/api/audit-packages/{bid}/bundle.zip").content
ui/backend/tests/test_audit_package_route.py:231:        # Flip one byte in zip → verify must fail
ui/backend/tests/test_audit_package_route.py:232:        tampered = bytes([zip_bytes[0] ^ 1]) + zip_bytes[1:]
src/notion_sync/schemas.py:58:        """Return a byte-stable JSON representation for replay tests."""
ui/backend/tests/test_validation_report.py:75:    assert {"DEC-ADWM-002", "DEC-ADWM-004"}.issubset(trail_ids)
scripts/phase5_audit_run.py:2:a deterministic audit fixture into fixtures/runs/{case_id}/audit_real_run_measurement.yaml.
scripts/phase5_audit_run.py:13:    ui/backend/tests/fixtures/runs/{case_id}/audit_real_run_measurement.yaml
scripts/phase5_audit_run.py:14:    reports/phase5_audit/{timestamp}_{case_id}_raw_run.json  (stdout/stderr)
scripts/phase5_audit_run.py:18:    an `allowed_nondeterminism` set to strip them before byte-comparison.
scripts/phase5_audit_run.py:22:    test_phase5_byte_repro.py.
scripts/phase5_audit_run.py:94:def _phase7a_timestamp() -> str:
scripts/phase5_audit_run.py:95:    """Shared timestamp format — matches _write_raw_capture."""
scripts/phase5_audit_run.py:99:def _write_field_artifacts_run_manifest(
scripts/phase5_audit_run.py:100:    case_id: str, run_label: str, timestamp: str
scripts/phase5_audit_run.py:102:    """Write reports/phase5_fields/{case_id}/runs/{run_label}.json so the
scripts/phase5_audit_run.py:103:    backend route can resolve run_label -> timestamp directory in O(1).
scripts/phase5_audit_run.py:108:    artifact_dir = FIELDS_DIR / case_id / timestamp
scripts/phase5_audit_run.py:117:    manifest = runs_dir / f"{run_label}.json"
scripts/phase5_audit_run.py:119:        "run_label": run_label,
scripts/phase5_audit_run.py:120:        "timestamp": timestamp,
scripts/phase5_audit_run.py:132:    field_artifacts_ref: "dict | None" = None,
scripts/phase5_audit_run.py:202:    # Phase 7a — field artifacts reference (manifest path only; NO timestamps
scripts/phase5_audit_run.py:203:    # in the YAML itself so byte-repro stays green per 07a-RESEARCH.md §3.1).
scripts/phase5_audit_run.py:204:    # The manifest at the referenced path contains the timestamp.
scripts/phase5_audit_run.py:205:    if field_artifacts_ref is not None:
scripts/phase5_audit_run.py:206:        doc["field_artifacts"] = field_artifacts_ref
scripts/phase5_audit_run.py:214:    out_path = case_dir / "audit_real_run_measurement.yaml"
scripts/phase5_audit_run.py:220:        "# re-runs (modulo timestamp + commit_sha) is enforced by\n"
scripts/phase5_audit_run.py:221:        "# test_phase5_byte_repro.py.\n\n"
scripts/phase5_audit_run.py:260:    # Phase 7a — author the single shared timestamp up front; the executor-side
scripts/phase5_audit_run.py:261:    # _capture_field_artifacts writes to reports/phase5_fields/{case_id}/{ts}/.
scripts/phase5_audit_run.py:262:    ts = _phase7a_timestamp()
scripts/phase5_audit_run.py:270:        spec.metadata["phase7a_timestamp"] = ts
scripts/phase5_audit_run.py:279:    # Phase 7a — write per-run manifest + build field_artifacts_ref dict iff
scripts/phase5_audit_run.py:281:    run_label = "audit_real_run"
scripts/phase5_audit_run.py:282:    manifest_path = _write_field_artifacts_run_manifest(case_id, run_label, ts)
scripts/phase5_audit_run.py:283:    field_artifacts_ref: "dict | None" = None
scripts/phase5_audit_run.py:285:        field_artifacts_ref = {
scripts/phase5_audit_run.py:286:            "manifest_path_rel": str(manifest_path.relative_to(REPO_ROOT)),
scripts/phase5_audit_run.py:287:            "run_label": run_label,
scripts/phase5_audit_run.py:288:            # Deliberately NO timestamp string here (byte-repro): resolve via manifest.
scripts/phase5_audit_run.py:292:        case_id, report, commit_sha, field_artifacts_ref=field_artifacts_ref,
scripts/phase5_audit_run.py:305:        "field_artifacts_manifest": (
ui/backend/tests/test_phase5_byte_repro.py:1:"""Phase 5a byte-reproducibility guard.
ui/backend/tests/test_phase5_byte_repro.py:3:Enforces that every `audit_real_run_measurement.yaml` under fixtures/runs/
ui/backend/tests/test_phase5_byte_repro.py:7:verifies the *schema* contract that makes byte-repro feasible:
ui/backend/tests/test_phase5_byte_repro.py:12:4. `measurement.measured_at` is the only timestamp field.
ui/backend/tests/test_phase5_byte_repro.py:16:The full solver-rerun byte-repro test is gated by `EXECUTOR_MODE=foam_agent`
ui/backend/tests/test_phase5_byte_repro.py:60:    return sorted(RUNS_DIR.glob("*/audit_real_run_measurement.yaml"))
ui/backend/tests/test_phase5_byte_repro.py:67:        "Expected at least one audit_real_run_measurement.yaml under "
ui/backend/tests/test_phase5_byte_repro.py:76:    """Every audit fixture satisfies the schema that makes byte-repro possible."""
ui/backend/tests/test_phase5_byte_repro.py:87:        "(not a per-run hash) so byte-repro can identify the same logical "
ui/backend/tests/test_phase5_byte_repro.py:122:    This is the byte-reproducibility contract: given identical mesh +
ui/backend/tests/test_phase5_byte_repro.py:130:        "measurement.measured_at", # ISO timestamp
ui/backend/tests/test_field_artifacts_route.py:16:from ui.backend.services.field_artifacts import set_fields_root_for_testing
ui/backend/tests/test_field_artifacts_route.py:42:    assert body["run_label"] == "audit_real_run"
ui/backend/tests/test_field_artifacts_route.py:43:    assert body["timestamp"] == "20260421T000000Z"
ui/backend/tests/test_field_artifacts_route.py:52:    assert {"vtk", "csv", "residual_log"}.issubset(kinds), kinds
ui/backend/tests/test_field_artifacts_route.py:79:        assert a["size_bytes"] > 0, a
ui/backend/tests/test_case_export.py:16:def _open_zip(data: bytes) -> zipfile.ZipFile:
ui/backend/tests/test_case_export.py:41:def test_export_preserves_gold_yaml_byte_identity() -> None:
ui/backend/tests/test_case_export.py:42:    """Gold YAML in the zip must be byte-identical to knowledge/gold_standards/."""
ui/backend/tests/test_case_export.py:59:        "— bundle must preserve byte identity to avoid two-source-of-truth hazard."
ui/backend/tests/test_case_export.py:94:    assert expected.issubset(set(zf.namelist()))
ui/backend/tests/test_decisions_and_dashboard.py:42:    assert {"Q-1", "Q-2", "Q-3"}.issubset(qids)
ui/backend/tests/test_decisions_and_dashboard.py:98:    assert {"Q-1", "Q-2"}.issubset({g["qid"] for g in body["gate_queue"]})
tests/test_foam_agent_adapter.py:536:    def test_make_tarball_returns_bytes(self, tmp_path):
tests/test_foam_agent_adapter.py:537:        """验证 _make_tarball 返回有效的 tarball bytes。"""
tests/test_foam_agent_adapter.py:543:        tarball_bytes = FoamAgentExecutor._make_tarball(tmp_path)
tests/test_foam_agent_adapter.py:544:        assert isinstance(tarball_bytes, bytes)
tests/test_foam_agent_adapter.py:545:        assert len(tarball_bytes) > 0
tests/test_foam_agent_adapter.py:548:        buf = io.BytesIO(tarball_bytes)
tests/test_foam_agent_adapter.py:557:        tarball_bytes = FoamAgentExecutor._make_tarball(tmp_path)
tests/test_foam_agent_adapter.py:558:        assert isinstance(tarball_bytes, bytes)
src/models.py:81:    # driver-authored `phase7a_timestamp` (and `phase7a_case_id`) so
src/models.py:82:    # FoamAgentExecutor._capture_field_artifacts can stage OpenFOAM field
src/models.py:83:    # artifacts into reports/phase5_fields/{case_id}/{timestamp}/ before the
tests/test_audit_package/test_sign.py:29:    serialize_zip_bytes,
tests/test_audit_package/test_sign.py:63:_TEST_KEY = b"test-hmac-key-32-bytes-lengthXX!"  # 32 bytes
tests/test_audit_package/test_sign.py:73:        zb = serialize_zip_bytes(m)
tests/test_audit_package/test_sign.py:80:        zb = serialize_zip_bytes(m)
tests/test_audit_package/test_sign.py:86:        zb = serialize_zip_bytes(m)
tests/test_audit_package/test_sign.py:94:        zb = serialize_zip_bytes(m)
tests/test_audit_package/test_sign.py:100:        zb = serialize_zip_bytes(m)
tests/test_audit_package/test_sign.py:115:        zb = serialize_zip_bytes(m)
tests/test_audit_package/test_sign.py:123:        zb = serialize_zip_bytes(m)
tests/test_audit_package/test_sign.py:131:        zb = serialize_zip_bytes(m)
tests/test_audit_package/test_sign.py:133:        # Flip one byte in zip
tests/test_audit_package/test_sign.py:134:        zb_tampered = bytes([zb[0] ^ 0x01]) + zb[1:]
tests/test_audit_package/test_sign.py:139:        zb = serialize_zip_bytes(m)
tests/test_audit_package/test_sign.py:146:        zb = serialize_zip_bytes(m)
tests/test_audit_package/test_sign.py:148:        wrong_key = b"different-hmac-key-32-bytes-lenXX"
tests/test_audit_package/test_sign.py:153:        zb = serialize_zip_bytes(m)
tests/test_audit_package/test_sign.py:158:        zb = serialize_zip_bytes(m)
tests/test_audit_package/test_sign.py:164:        zb = serialize_zip_bytes(m)
tests/test_audit_package/test_sign.py:180:        zb = serialize_zip_bytes(m)
tests/test_audit_package/test_sign.py:194:        the signature one byte at a time via response-time measurement.
tests/test_audit_package/test_sign.py:197:        zb = serialize_zip_bytes(m)
tests/test_audit_package/test_sign.py:211:        zb = serialize_zip_bytes(m)
tests/test_audit_package/test_sign.py:216:        """DOMAIN_TAG + 32-byte manifest digest + 32-byte zip digest."""
tests/test_audit_package/test_sign.py:218:        zb = serialize_zip_bytes(m)
tests/test_audit_package/test_sign.py:225:        zb = serialize_zip_bytes(m1)
tests/test_audit_package/test_sign.py:242:        raw = b"binary key bytes" * 2  # 32 bytes
tests/test_audit_package/test_sign.py:251:        """Critical M1 test: 'aGVsbG8=' un-prefixed → literal 8 bytes, NOT decoded."""
tests/test_audit_package/test_sign.py:254:        # Post-PR-5c.1 behavior: b"aGVsbG8=" (literal bytes, no ambiguity)
tests/test_audit_package/test_sign.py:315:    Operators must rewrite as `base64:<value>` to preserve key bytes.
tests/test_audit_package/test_sign.py:332:        """16-byte key = 24 base64 chars (minimum threshold) → warns."""
tests/test_audit_package/test_sign.py:335:            base64.b64encode(b"sixteen-bytes-key").decode("ascii"),  # 24 chars
tests/test_audit_package/test_sign.py:377:        # urlsafe_b64encode of 32 random bytes likely contains - or _
tests/test_audit_package/test_sign.py:473:        sig_path.write_bytes((sig + "\r\n").encode("ascii"))
tests/test_audit_package/test_sign.py:480:        sig_path.write_bytes(b"\xef\xbb\xbf" + sig.encode("ascii"))
tests/test_audit_package/test_sign.py:504:        zb = serialize_zip_bytes(m)
tests/test_audit_package/test_sign.py:517:        zb = serialize_zip_bytes(m)
tests/test_audit_package/test_sign.py:524:        """Un-prefixed env var → literal UTF-8 bytes (no base64 heuristic)."""
tests/test_audit_package/test_sign.py:529:        zb = serialize_zip_bytes(m)
tests/test_audit_package/test_sign.py:539:        zb = serialize_zip_bytes(m)
tests/test_audit_package/test_sign.py:553:        zb = serialize_zip_bytes(m)
tests/test_audit_package/test_serialize.py:19:    serialize_zip_bytes,
tests/test_audit_package/test_serialize.py:110:    def test_byte_stable_across_calls(self):
tests/test_audit_package/test_serialize.py:120:    def test_byte_identical_across_calls(self):
tests/test_audit_package/test_serialize.py:122:        b1 = serialize_zip_bytes(m)
tests/test_audit_package/test_serialize.py:123:        b2 = serialize_zip_bytes(m)
tests/test_audit_package/test_serialize.py:130:        zbytes = serialize_zip_bytes(m)
tests/test_audit_package/test_serialize.py:131:        with zipfile.ZipFile(io.BytesIO(zbytes)) as zf:
tests/test_audit_package/test_serialize.py:138:        zbytes = serialize_zip_bytes(m)
tests/test_audit_package/test_serialize.py:139:        with zipfile.ZipFile(io.BytesIO(zbytes)) as zf:
tests/test_audit_package/test_serialize.py:146:        zbytes = serialize_zip_bytes(m)
tests/test_audit_package/test_serialize.py:147:        with zipfile.ZipFile(io.BytesIO(zbytes)) as zf:
tests/test_audit_package/test_serialize.py:155:        zbytes = serialize_zip_bytes(m)
tests/test_audit_package/test_serialize.py:156:        with zipfile.ZipFile(io.BytesIO(zbytes)) as zf:
tests/test_audit_package/test_serialize.py:162:        zbytes = serialize_zip_bytes(m)
tests/test_audit_package/test_serialize.py:163:        with zipfile.ZipFile(io.BytesIO(zbytes)) as zf:
tests/test_audit_package/test_serialize.py:170:        zbytes = serialize_zip_bytes(m)
tests/test_audit_package/test_serialize.py:171:        with zipfile.ZipFile(io.BytesIO(zbytes)) as zf:
tests/test_audit_package/test_serialize.py:177:        zbytes = serialize_zip_bytes(m)
tests/test_audit_package/test_serialize.py:178:        with zipfile.ZipFile(io.BytesIO(zbytes)) as zf:
tests/test_audit_package/test_serialize.py:194:        zbytes = serialize_zip_bytes(minimal)
tests/test_audit_package/test_serialize.py:195:        with zipfile.ZipFile(io.BytesIO(zbytes)) as zf:
tests/test_audit_package/test_serialize.py:205:        assert out.read_bytes() == serialize_zip_bytes(m)
tests/test_audit_package/test_serialize.py:312:        # PDF magic bytes
tests/test_audit_package/test_serialize.py:313:        assert out.read_bytes()[:4] == b"%PDF"
ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/runs/audit_real_run.json:2:  "run_label": "audit_real_run",
ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/runs/audit_real_run.json:3:  "timestamp": "20260421T000000Z",
tests/test_audit_package/test_manifest.py:300:    def test_byte_stable_across_two_invocations(self, tmp_path, monkeypatch):
tests/test_audit_package/test_manifest.py:301:        """Two identical calls with same build_fingerprint → byte-identical JSON."""
ui/backend/tests/fixtures/runs/backward_facing_step/audit_real_run_measurement.yaml:5:# re-runs (modulo timestamp + commit_sha) is enforced by
ui/backend/tests/fixtures/runs/backward_facing_step/audit_real_run_measurement.yaml:6:# test_phase5_byte_repro.py.
src/auto_verifier/verifier.py:43:        timestamp: str = DEFAULT_TIMESTAMP,
src/auto_verifier/verifier.py:49:                timestamp=timestamp,
src/auto_verifier/verifier.py:83:            timestamp=timestamp,
src/auto_verifier/verifier.py:104:        timestamp: str = DEFAULT_TIMESTAMP,
src/auto_verifier/verifier.py:115:            timestamp=timestamp,
src/auto_verifier/verifier.py:123:        timestamp: str = DEFAULT_TIMESTAMP,
src/auto_verifier/verifier.py:129:            timestamp=timestamp,
src/auto_verifier/verifier.py:176:        timestamp: str,
src/auto_verifier/verifier.py:181:        self._timestamp = timestamp
src/auto_verifier/verifier.py:206:            timestamp=self._timestamp,
src/report_engine/visual_acceptance.py:995:        data = b64encode(path.read_bytes()).decode("ascii")
ui/backend/tests/fixtures/runs/differential_heated_cavity/audit_real_run_measurement.yaml:5:# re-runs (modulo timestamp + commit_sha) is enforced by
ui/backend/tests/fixtures/runs/differential_heated_cavity/audit_real_run_measurement.yaml:6:# test_phase5_byte_repro.py.
ui/backend/tests/fixtures/runs/rayleigh_benard_convection/audit_real_run_measurement.yaml:5:# re-runs (modulo timestamp + commit_sha) is enforced by
ui/backend/tests/fixtures/runs/rayleigh_benard_convection/audit_real_run_measurement.yaml:6:# test_phase5_byte_repro.py.
ui/backend/tests/fixtures/runs/circular_cylinder_wake/audit_real_run_measurement.yaml:5:# re-runs (modulo timestamp + commit_sha) is enforced by
ui/backend/tests/fixtures/runs/circular_cylinder_wake/audit_real_run_measurement.yaml:6:# test_phase5_byte_repro.py.
ui/backend/tests/fixtures/runs/duct_flow/audit_real_run_measurement.yaml:5:# re-runs (modulo timestamp + commit_sha) is enforced by
ui/backend/tests/fixtures/runs/duct_flow/audit_real_run_measurement.yaml:6:# test_phase5_byte_repro.py.
src/auto_verifier/schemas.py:92:    timestamp: str
src/auto_verifier/schemas.py:104:            "timestamp": self.timestamp,
tests/test_auto_verifier/conftest.py:44:            digest.update(file_path.read_bytes())
src/audit_package/sign.py:9:same value as literal UTF-8 bytes instead of base64-decoding it. New
src/audit_package/sign.py:14:To preserve the pre-upgrade signing key bytes, rewrite the env var as::
src/audit_package/sign.py:33:2. The zip bytes (byte-reproducible from :func:`serialize_zip_bytes`).
src/audit_package/sign.py:44:Rather than concatenating the raw bytes (which would be ambiguous about
src/audit_package/sign.py:47:    hmac_input = DOMAIN_TAG || sha256(canonical_manifest_bytes) || sha256(zip_bytes)
src/audit_package/sign.py:52:prefixes are fixed 32 bytes each, so component boundaries are unambiguous.
src/audit_package/sign.py:69:  non-ambiguous: a user-visible string is always its literal bytes.
src/audit_package/sign.py:123:# 16-byte+ random binary keys. On match, emit DeprecationWarning so operators
src/audit_package/sign.py:126:_LEGACY_BASE64_MIN_LEN = 24  # base64 of 16 random bytes → 24 chars incl. padding
src/audit_package/sign.py:133:    - has length ≥ 24 (would decode to ≥16 bytes — plausible binary key)
src/audit_package/sign.py:178:def get_hmac_secret_from_env(env_var: str = HMAC_ENV_VAR) -> bytes:
src/audit_package/sign.py:183:    - ``base64:<padded-standard-base64>`` → base64-decoded to bytes.
src/audit_package/sign.py:184:    - ``text:<utf-8-string>`` → UTF-8-encoded to bytes.
src/audit_package/sign.py:235:    # it is taken as literal UTF-8 bytes. PR-5c.3 per Codex 3rd-round review:
src/audit_package/sign.py:243:                f"PR-5c.1 treats this as literal UTF-8 bytes, not decoded bytes. "
src/audit_package/sign.py:246:                f'`{env_var}="base64:<same-value>"` to preserve binary-key bytes, '
src/audit_package/sign.py:254:    # Un-prefixed → literal UTF-8 bytes. No heuristic base64 decode.
src/audit_package/sign.py:262:def _build_hmac_input(manifest: Dict[str, Any], zip_bytes: bytes) -> bytes:
src/audit_package/sign.py:265:    Each SHA-256 digest is fixed 32 bytes → unambiguous component
src/audit_package/sign.py:269:    manifest_bytes = _canonical_json(manifest)
src/audit_package/sign.py:270:    manifest_digest = _HASH_ALGO(manifest_bytes).digest()
src/audit_package/sign.py:271:    zip_digest = _HASH_ALGO(zip_bytes).digest()
src/audit_package/sign.py:277:    zip_bytes: bytes,
src/audit_package/sign.py:278:    hmac_secret: bytes,
src/audit_package/sign.py:288:    zip_bytes
src/audit_package/sign.py:289:        The byte-reproducible zip from :func:`serialize_zip_bytes`.
src/audit_package/sign.py:291:        The HMAC key as bytes. Typically obtained via
src/audit_package/sign.py:308:    hmac_input = _build_hmac_input(manifest, zip_bytes)
src/audit_package/sign.py:314:    zip_bytes: bytes,
src/audit_package/sign.py:316:    hmac_secret: bytes,
src/audit_package/sign.py:322:    manifest, zip_bytes, hmac_secret
src/audit_package/sign.py:324:        zip bytes were tampered post-sign, this returns ``False``.
src/audit_package/sign.py:338:        expected = sign(manifest, zip_bytes, hmac_secret)
src/audit_package/manifest.py:14:- Generation timestamp (ISO-8601 UTC, second precision)
src/audit_package/manifest.py:16:Determinism guarantees (byte-stable across two identical invocations):
src/audit_package/manifest.py:21:- Git-log lookups use ``--format=%H`` (no timestamp). Absence of a git repo
src/audit_package/manifest.py:75:    """UTC timestamp, second precision, Z suffix."""
src/audit_package/manifest.py:345:        When None, defaults to an ISO-UTC timestamp (fallback for legacy
src/audit_package/manifest.py:348:        (e.g., ``sha256(case_id|run_id)[:16]``) to preserve byte
src/audit_package/__init__.py:4:full verification-and-validation evidence as a signed, byte-reproducible
src/audit_package/__init__.py:15:- ``serialize`` (PR-5b, DEC-V61-013) — dict → byte-reproducible zip +
src/audit_package/__init__.py:29:- :func:`serialize_zip` / :func:`serialize_zip_bytes` — byte-reproducible zip
src/audit_package/__init__.py:36:- :func:`sign` / :func:`verify` — HMAC-SHA256 over (manifest, zip_bytes, key)
src/audit_package/__init__.py:56:    serialize_zip_bytes,
src/audit_package/__init__.py:80:    "serialize_zip_bytes",
src/audit_package/serialize.py:1:"""Manifest → byte-reproducible zip + human-readable HTML/PDF (Phase 5 · PR-5b).
src/audit_package/serialize.py:6:- **zip**: byte-identical output for identical input. Epoch-zero mtimes,
src/audit_package/serialize.py:23:Zip byte-equality across invocations is a hard guarantee — the PR-5c HMAC
src/audit_package/serialize.py:24:signature covers the zip bytes, so any reordering or metadata drift would
src/audit_package/serialize.py:68:def _canonical_json(obj: Any) -> bytes:
src/audit_package/serialize.py:94:def _zip_entries_from_manifest(manifest: Dict[str, Any]) -> Dict[str, bytes]:
src/audit_package/serialize.py:95:    """Lay out the zip entries as ``{path: bytes}`` before writing.
src/audit_package/serialize.py:108:    entries: Dict[str, bytes] = {}
src/audit_package/serialize.py:144:def serialize_zip_bytes(manifest: Dict[str, Any]) -> bytes:
src/audit_package/serialize.py:145:    """Build the audit-package zip as bytes, byte-identical across calls.
src/audit_package/serialize.py:147:    The function is pure: same input → same bytes. This is the property
src/audit_package/serialize.py:160:    """Write the byte-reproducible zip to ``output_path`` (overwrites)."""
src/audit_package/serialize.py:162:    output_path.write_bytes(serialize_zip_bytes(manifest))
src/audit_package/serialize.py:214:    decisions) so two identical manifests produce identical HTML bytes.
src/audit_package/serialize.py:378:    "serialize_zip_bytes",
ui/backend/tests/fixtures/runs/turbulent_flat_plate/audit_real_run_measurement.yaml:5:# re-runs (modulo timestamp + commit_sha) is enforced by
ui/backend/tests/fixtures/runs/turbulent_flat_plate/audit_real_run_measurement.yaml:6:# test_phase5_byte_repro.py.
ui/backend/tests/fixtures/runs/impinging_jet/audit_real_run_measurement.yaml:5:# re-runs (modulo timestamp + commit_sha) is enforced by
ui/backend/tests/fixtures/runs/impinging_jet/audit_real_run_measurement.yaml:6:# test_phase5_byte_repro.py.
ui/backend/tests/fixtures/runs/plane_channel_flow/audit_real_run_measurement.yaml:5:# re-runs (modulo timestamp + commit_sha) is enforced by
ui/backend/tests/fixtures/runs/plane_channel_flow/audit_real_run_measurement.yaml:6:# test_phase5_byte_repro.py.
ui/backend/tests/fixtures/runs/naca0012_airfoil/audit_real_run_measurement.yaml:5:# re-runs (modulo timestamp + commit_sha) is enforced by
ui/backend/tests/fixtures/runs/naca0012_airfoil/audit_real_run_measurement.yaml:6:# test_phase5_byte_repro.py.
ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml:5:# re-runs (modulo timestamp + commit_sha) is enforced by
ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml:6:# test_phase5_byte_repro.py.
ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml:48:field_artifacts:
ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml:49:  manifest_path_rel: reports/phase5_fields/lid_driven_cavity/runs/audit_real_run.json
ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml:50:  run_label: audit_real_run
ui/backend/tests/fixtures/runs/lid_driven_cavity/field_artifacts_manifest.yaml:2:# ui/backend/tests/test_field_artifacts_route.py
ui/backend/tests/fixtures/runs/lid_driven_cavity/field_artifacts_manifest.yaml:3:run_label: audit_real_run
ui/backend/tests/fixtures/runs/lid_driven_cavity/field_artifacts_manifest.yaml:7:    min_size_bytes: 500
ui/backend/tests/fixtures/runs/lid_driven_cavity/field_artifacts_manifest.yaml:8:    max_size_bytes: 2500000
ui/backend/tests/fixtures/runs/lid_driven_cavity/field_artifacts_manifest.yaml:11:    min_size_bytes: 500
ui/backend/tests/fixtures/runs/lid_driven_cavity/field_artifacts_manifest.yaml:14:    min_size_bytes: 100

exec
/bin/zsh -lc "nl -ba src/foam_agent_adapter.py | sed -n '560,635p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   560	                        f"topoSet failed:\n{topo_log}",
   561	                        time.monotonic() - t0,
   562	                        raw_output_path=raw_output_path,
   563	                    )
   564	
   565	                baffles_ok, baffles_log = self._docker_exec(
   566	                    "createBaffles -overwrite", case_cont_dir, self.BLOCK_MESH_TIMEOUT,
   567	                )
   568	                if not baffles_ok:
   569	                    return self._fail(
   570	                        f"createBaffles failed:\n{baffles_log}",
   571	                        time.monotonic() - t0,
   572	                        raw_output_path=raw_output_path,
   573	                    )
   574	
   575	            # 6. 执行求解器
   576	            solver_ok, solver_log = self._docker_exec(
   577	                solver_name, case_cont_dir, self._timeout,
   578	            )
   579	            if not solver_ok:
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
   626	                log_path.parent, solver_name, task_spec, key_quantities
   627	            )
   628	
   629	            elapsed = time.monotonic() - t0
   630	            return ExecutionResult(
   631	                success=True,
   632	                is_mock=False,
   633	                residuals=residuals,
   634	                key_quantities=key_quantities,
   635	                execution_time_s=elapsed,

exec
/bin/zsh -lc "nl -ba src/foam_agent_adapter.py | sed -n '6860,7015p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba src/foam_agent_adapter.py | sed -n '650,735p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba scripts/phase5_audit_run.py | sed -n '80,315p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
  6860	
  6861	            for field_file in field_files:
  6862	                actual_cont_path = f"{latest_cont_dir}/{field_file}"
  6863	                # Check if file exists in container before attempting copy (T is optional)
  6864	                check = container.exec_run(
  6865	                    cmd=["bash", "-c", f'[ -f "{actual_cont_path}" ] && echo exists || echo missing']
  6866	                )
  6867	                if check.output.decode().strip() == "missing":
  6868	                    continue
  6869	                host_path = host_time_dir / field_file
  6870	                self._copy_file_from_container(container, actual_cont_path, host_path)
  6871	        except Exception as e:
  6872	            import sys as _sys
  6873	            print(f"[WARN] _copy_postprocess_fields failed: {e}", file=_sys.stderr)
  6874	
  6875	    # ------------------------------------------------------------------
  6876	    # Phase 7a — field-artifact staging (VTK + sample CSV + residuals)
  6877	    # ------------------------------------------------------------------
  6878	
  6879	    def _capture_field_artifacts(
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
  6996	        header — downstream tools (Phase 7b render pipeline) consume this.
  6997	        """
  6998	        lines = dat_path.read_text(encoding="utf-8").splitlines()
  6999	        header: Optional[List[str]] = None
  7000	        rows: List[List[str]] = []
  7001	        for line in lines:
  7002	            line = line.strip()
  7003	            if not line:
  7004	                continue
  7005	            if line.startswith("#"):
  7006	                tokens = line.lstrip("#").split()
  7007	                if tokens:
  7008	                    header = tokens
  7009	                continue
  7010	            rows.append(line.split())
  7011	        if not header or not rows:
  7012	            return
  7013	        with csv_path.open("w", encoding="utf-8") as fh:
  7014	            fh.write(",".join(header) + "\n")
  7015	            for r in rows:

 succeeded in 0ms:
   650	    def _turbulence_model_for_solver(
   651	        self, solver_name: str, geometry_type: GeometryType, Re: Optional[float] = None
   652	    ) -> str:
   653	        """Auto-select turbulence model based on solver family.
   654	
   655	        Core rule: buoyantFoam family -> kEpsilon (avoids OF10 kOmegaSST dimension bug);
   656	        SIMPLE_GRID laminar -> laminar; others -> kOmegaSST.
   657	        """
   658	        if "buoyant" in solver_name:
   659	            return "kEpsilon"
   660	        if geometry_type == GeometryType.SIMPLE_GRID and Re is not None and Re < 2300:
   661	            return "laminar"
   662	        return "kOmegaSST"
   663	
   664	    @staticmethod
   665	    def _emit_phase7a_function_objects(turbulence_model: str = "laminar") -> str:
   666	        """Phase 7a — return the controlDict `functions{}` block as a raw string.
   667	
   668	        Called from each case generator that opts into Phase 7a field capture.
   669	        For LDC (laminar) yPlus is omitted; for turbulent cases the yPlus block
   670	        is activated. Sample coordinates are in post-convertToMeters space
   671	        (LDC: convertToMeters=0.1, so y-axis 0.0→0.1 spans the full cavity).
   672	
   673	        See .planning/phases/07a-field-capture/07a-RESEARCH.md §2.2 for the
   674	        function-object reference. `writeControl timeStep; writeInterval 500;`
   675	        is correct for steady simpleFoam per research validation
   676	        (`runTime` is transient-only — user ratification #2).
   677	        """
   678	        y_plus_block = ""
   679	        if turbulence_model and turbulence_model != "laminar":
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
   105	    Returns the manifest Path on success, None if the artifact dir never
   106	    materialized (e.g. foamToVTK failed or the case is not Phase-7a opted-in).
   107	    """
   108	    artifact_dir = FIELDS_DIR / case_id / timestamp
   109	    if not artifact_dir.is_dir():
   110	        print(
   111	            f"[audit] [WARN] field artifact dir missing, skipping manifest: {artifact_dir}",
   112	            flush=True,
   113	        )
   114	        return None
   115	    runs_dir = FIELDS_DIR / case_id / "runs"
   116	    runs_dir.mkdir(parents=True, exist_ok=True)
   117	    manifest = runs_dir / f"{run_label}.json"
   118	    payload = {
   119	        "run_label": run_label,
   120	        "timestamp": timestamp,
   121	        "case_id": case_id,
   122	        "artifact_dir_rel": str(artifact_dir.relative_to(REPO_ROOT)),
   123	    }
   124	    manifest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
   125	    return manifest
   126	
   127	
   128	def _audit_fixture_doc(
   129	    case_id: str,
   130	    report,
   131	    commit_sha: str,
   132	    field_artifacts_ref: "dict | None" = None,
   133	) -> dict:
   134	    quantity, value, source_note = _primary_scalar(report)
   135	    comp = report.comparison_result
   136	    passed = comp.passed if comp else False
   137	
   138	    verdict_hint = "PASS" if passed else "FAIL"
   139	
   140	    doc = {
   141	        "run_metadata": {
   142	            "run_id": "audit_real_run",
   143	            "label_zh": "真实 solver 审计运行",
   144	            "label_en": "Real solver audit run",
   145	            "description_zh": (
   146	                f"FoamAgentExecutor 驱动 OpenFOAM 实际跑出的结果（commit {commit_sha}）。"
   147	                "这是 audit package 背书的权威测量——不是合成 fixture。"
   148	                "失败的话说明 case 本身的 physics_contract 在当前 mesh 预算下无法满足，"
   149	                "不是 harness bug；会进入 audit_concerns 随包交付给审查方。"
   150	            ),
   151	            "category": "audit_real_run",
   152	            "expected_verdict": verdict_hint,
   153	        },
   154	        "case_id": case_id,
   155	        "source": "phase5_audit_run_foam_agent",
   156	        "measurement": {
   157	            "value": value if value is not None else 0.0,
   158	            "unit": "dimensionless",
   159	            "run_id": f"audit_{case_id}_{commit_sha}",
   160	            "commit_sha": commit_sha,
   161	            "measured_at": _iso_now(),
   162	            "quantity": quantity,
   163	            "extraction_source": source_note,
   164	            "solver_success": report.execution_result.success,
   165	            "comparator_passed": passed,
   166	        },
   167	        "audit_concerns": [],
   168	        "decisions_trail": [
   169	            {
   170	                "decision_id": "DEC-V61-028",
   171	                "date": "2026-04-21",
   172	                "title": "Phase 5a audit pipeline — real-solver fixtures",
   173	                "autonomous": True,
   174	            }
   175	        ],
   176	    }
   177	
   178	    if comp is not None:
   179	        doc["audit_concerns"].append(
   180	            {
   181	                "concern_type": "CONTRACT_STATUS",
   182	                "summary": (comp.summary or "No summary")[:240],
   183	                "detail": (comp.summary or "")[:2000],
   184	                "decision_refs": ["DEC-V61-028"],
   185	            }
   186	        )
   187	        if comp.deviations:
   188	            # Summarize first 5 deviations for the audit record
   189	            dev_summary = "; ".join(
   190	                f"{d.quantity}: actual={d.actual} expected={d.expected}"
   191	                for d in comp.deviations[:5]
   192	            )
   193	            doc["audit_concerns"].append(
   194	                {
   195	                    "concern_type": "DEVIATIONS",
   196	                    "summary": f"{len(comp.deviations)} deviation(s) over tolerance"[:240],
   197	                    "detail": dev_summary[:2000],
   198	                    "decision_refs": ["DEC-V61-028"],
   199	                }
   200	            )
   201	
   202	    # Phase 7a — field artifacts reference (manifest path only; NO timestamps
   203	    # in the YAML itself so byte-repro stays green per 07a-RESEARCH.md §3.1).
   204	    # The manifest at the referenced path contains the timestamp.
   205	    if field_artifacts_ref is not None:
   206	        doc["field_artifacts"] = field_artifacts_ref
   207	
   208	    return doc
   209	
   210	
   211	def _write_audit_fixture(case_id: str, doc: dict) -> Path:
   212	    case_dir = RUNS_DIR / case_id
   213	    case_dir.mkdir(parents=True, exist_ok=True)
   214	    out_path = case_dir / "audit_real_run_measurement.yaml"
   215	    header = (
   216	        "# Phase 5a audit-real-run fixture — AUTO-GENERATED, DO NOT HAND-EDIT.\n"
   217	        "# Regenerate via:\n"
   218	        f"#   EXECUTOR_MODE=foam_agent .venv/bin/python scripts/phase5_audit_run.py {case_id}\n"
   219	        "# This fixture backs the signed audit package. Byte-identity across\n"
   220	        "# re-runs (modulo timestamp + commit_sha) is enforced by\n"
   221	        "# test_phase5_byte_repro.py.\n\n"
   222	    )
   223	    with out_path.open("w", encoding="utf-8") as fh:
   224	        fh.write(header)
   225	        yaml.safe_dump(doc, fh, allow_unicode=True, sort_keys=False, default_flow_style=False)
   226	    return out_path
   227	
   228	
   229	def _write_raw_capture(case_id: str, report, duration_s: float) -> Path:
   230	    RAW_DIR.mkdir(parents=True, exist_ok=True)
   231	    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
   232	    out = RAW_DIR / f"{ts}_{case_id}_raw.json"
   233	    er = report.execution_result
   234	    comp = report.comparison_result
   235	    data = {
   236	        "case_id": case_id,
   237	        "measured_at": _iso_now(),
   238	        "duration_s": round(duration_s, 3),
   239	        "solver_success": er.success,
   240	        "key_quantities": er.key_quantities,
   241	        "comparator_passed": comp.passed if comp else None,
   242	        "comparator_summary": (comp.summary if comp else None),
   243	        "deviations": (
   244	            [
   245	                {"quantity": d.quantity, "actual": d.actual, "expected": d.expected}
   246	                for d in (comp.deviations or [])
   247	            ]
   248	            if comp
   249	            else []
   250	        ),
   251	    }
   252	    out.write_text(json.dumps(data, indent=2, default=str))
   253	    return out
   254	
   255	
   256	def run_one(runner: TaskRunner, case_id: str, commit_sha: str) -> dict:
   257	    t0 = time.monotonic()
   258	    print(f"[audit] {case_id} → start", flush=True)
   259	
   260	    # Phase 7a — author the single shared timestamp up front; the executor-side
   261	    # _capture_field_artifacts writes to reports/phase5_fields/{case_id}/{ts}/.
   262	    ts = _phase7a_timestamp()
   263	    try:
   264	        spec = runner._task_spec_from_case_id(case_id)
   265	        # Opt-in signalling to FoamAgentExecutor. Other 9 cases' controlDicts
   266	        # do NOT yet emit Phase 7a function objects, but the executor guards
   267	        # on the metadata keys — staging runs best-effort.
   268	        if spec.metadata is None:
   269	            spec.metadata = {}
   270	        spec.metadata["phase7a_timestamp"] = ts
   271	        spec.metadata["phase7a_case_id"] = case_id
   272	        report = runner.run_task(spec)
   273	    except Exception as e:  # noqa: BLE001
   274	        print(f"[audit] {case_id} EXCEPTION: {e!r}")
   275	        return {"case_id": case_id, "ok": False, "error": repr(e)}
   276	
   277	    dt = time.monotonic() - t0
   278	
   279	    # Phase 7a — write per-run manifest + build field_artifacts_ref dict iff
   280	    # the artifact dir materialized (best-effort, must not block audit doc).
   281	    run_label = "audit_real_run"
   282	    manifest_path = _write_field_artifacts_run_manifest(case_id, run_label, ts)
   283	    field_artifacts_ref: "dict | None" = None
   284	    if manifest_path is not None:
   285	        field_artifacts_ref = {
   286	            "manifest_path_rel": str(manifest_path.relative_to(REPO_ROOT)),
   287	            "run_label": run_label,
   288	            # Deliberately NO timestamp string here (byte-repro): resolve via manifest.
   289	        }
   290	
   291	    doc = _audit_fixture_doc(
   292	        case_id, report, commit_sha, field_artifacts_ref=field_artifacts_ref,
   293	    )
   294	    fixture_path = _write_audit_fixture(case_id, doc)
   295	    raw_path = _write_raw_capture(case_id, report, dt)
   296	    verdict = doc["run_metadata"]["expected_verdict"]
   297	    print(f"[audit] {case_id} → {verdict} · {dt:.1f}s · {fixture_path.name}", flush=True)
   298	    return {
   299	        "case_id": case_id,
   300	        "ok": True,
   301	        "duration_s": round(dt, 3),
   302	        "verdict": verdict,
   303	        "fixture": str(fixture_path.relative_to(REPO_ROOT)),
   304	        "raw": str(raw_path.relative_to(REPO_ROOT)),
   305	        "field_artifacts_manifest": (
   306	            str(manifest_path.relative_to(REPO_ROOT)) if manifest_path else None
   307	        ),
   308	    }
   309	
   310	
   311	def main() -> int:
   312	    parser = argparse.ArgumentParser()
   313	    parser.add_argument("cases", nargs="*", help="case ids; use --all for all 10")
   314	    parser.add_argument("--all", action="store_true", help="run all 10 whitelist cases")
   315	    args = parser.parse_args()

exec
/bin/zsh -lc "nl -ba ui/backend/services/field_artifacts.py | sed -n '1,230p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba ui/backend/routes/field_artifacts.py | sed -n '1,115p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
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
    18	from pathlib import Path
    19	from typing import Optional
    20	
    21	from fastapi import HTTPException
    22	
    23	from ui.backend.schemas.validation import (
    24	    FieldArtifact,
    25	    FieldArtifactKind,
    26	    FieldArtifactsResponse,
    27	)
    28	from ui.backend.services.run_ids import parse_run_id
    29	
    30	# Repo root: 3 levels up from this file (ui/backend/services/field_artifacts.py)
    31	_REPO_ROOT = Path(__file__).resolve().parents[3]
    32	_FIELDS_ROOT = _REPO_ROOT / "reports" / "phase5_fields"
    33	
    34	_FIELDS_ROOT_OVERRIDE: Optional[Path] = None
    35	
    36	
    37	def _current_fields_root() -> Path:
    38	    return _FIELDS_ROOT_OVERRIDE or _FIELDS_ROOT
    39	
    40	
    41	def set_fields_root_for_testing(path: Optional[Path]) -> None:
    42	    """Override the reports/phase5_fields/ root (test-only hook)."""
    43	    global _FIELDS_ROOT_OVERRIDE
    44	    _FIELDS_ROOT_OVERRIDE = path
    45	    # Invalidate sha cache when root changes.
    46	    _sha_cache.clear()
    47	
    48	
    49	_KIND_ORDER: dict[str, int] = {"vtk": 0, "csv": 1, "residual_log": 2}
    50	
    51	# SHA256 cache keyed on (abs_path, st_mtime, st_size) per 07a-RESEARCH.md §2.6.
    52	_sha_cache: dict[tuple[str, float, int], str] = {}
    53	
    54	
    55	def sha256_of(path: Path) -> str:
    56	    """Compute (or return cached) SHA256 hex digest for `path`.
    57	
    58	    Cache key: (absolute_path, st_mtime, st_size). Mtime+size collision would
    59	    return a stale hash — MVP-accepted risk per 07a-RESEARCH.md §2.6.
    60	    """
    61	    st = path.stat()
    62	    key = (str(path.resolve()), st.st_mtime, st.st_size)
    63	    cached = _sha_cache.get(key)
    64	    if cached is not None:
    65	        return cached
    66	    h = hashlib.sha256()
    67	    with path.open("rb") as fh:
    68	        for chunk in iter(lambda: fh.read(65536), b""):
    69	            h.update(chunk)
    70	    digest = h.hexdigest()
    71	    _sha_cache[key] = digest
    72	    return digest
    73	
    74	
    75	def _classify(filename: str) -> Optional[FieldArtifactKind]:
    76	    """Map a filename suffix to its kind. Returns None for files we don't surface."""
    77	    low = filename.lower()
    78	    if low.endswith(".vtk") or low.endswith(".vtu") or low.endswith(".vtp"):
    79	        return "vtk"
    80	    if low.endswith(".csv") or low.endswith(".xy") or low.endswith(".dat"):
    81	        # residuals.csv (or anything with 'residual' in the name) is a residual_log.
    82	        if low == "residuals.csv" or "residual" in low:
    83	            return "residual_log"
    84	        return "csv"
    85	    if low.startswith("log.") or low.endswith(".log"):
    86	        return "residual_log"
    87	    return None
    88	
    89	
    90	def _read_run_manifest(case_id: str, run_label: str) -> Optional[dict]:
    91	    root = _current_fields_root()
    92	    manifest_path = root / case_id / "runs" / f"{run_label}.json"
    93	    if not manifest_path.is_file():
    94	        return None
    95	    try:
    96	        return json.loads(manifest_path.read_text(encoding="utf-8"))
    97	    except (json.JSONDecodeError, OSError):
    98	        return None
    99	
   100	
   101	def list_artifacts(run_id: str) -> Optional[FieldArtifactsResponse]:
   102	    """Build the JSON manifest for a run_id. Returns None if no data exists."""
   103	    case_id, run_label = parse_run_id(run_id)
   104	    manifest = _read_run_manifest(case_id, run_label)
   105	    if manifest is None:
   106	        return None
   107	    timestamp = manifest.get("timestamp", "")
   108	    if not timestamp:
   109	        return None
   110	    root = _current_fields_root()
   111	    artifact_dir = root / case_id / timestamp
   112	    if not artifact_dir.is_dir():
   113	        return None
   114	
   115	    items: list[FieldArtifact] = []
   116	    # Walk the whole tree — kind-classify leaves; skip directories.
   117	    for p in sorted(artifact_dir.rglob("*")):
   118	        if not p.is_file():
   119	            continue
   120	        kind = _classify(p.name)
   121	        if kind is None:
   122	            continue
   123	        # Use basename only in the URL (traversal via URL blocked by route).
   124	        items.append(
   125	            FieldArtifact(
   126	                kind=kind,
   127	                filename=p.name,
   128	                url=f"/api/runs/{run_id}/field-artifacts/{p.name}",
   129	                sha256=sha256_of(p),
   130	                size_bytes=p.stat().st_size,
   131	            )
   132	        )
   133	    items.sort(key=lambda a: (_KIND_ORDER.get(a.kind, 99), a.filename))
   134	
   135	    return FieldArtifactsResponse(
   136	        run_id=run_id,
   137	        case_id=case_id,
   138	        run_label=run_label,
   139	        timestamp=timestamp,
   140	        artifacts=items,
   141	    )
   142	
   143	
   144	def resolve_artifact_path(run_id: str, filename: str) -> Path:
   145	    """Return the on-disk path for {run_id}/{filename}, or raise HTTPException 404.
   146	
   147	    Traversal defense: reject any filename with path separators or '..';
   148	    additionally verify `resolved.relative_to(artifact_dir.resolve())`.
   149	    """
   150	    # Reject anything with path structure or traversal markers.
   151	    if filename in ("", ".", ".."):
   152	        raise HTTPException(status_code=404, detail="artifact not found")
   153	    if "/" in filename or "\\" in filename or ".." in filename:
   154	        raise HTTPException(status_code=404, detail="artifact not found")
   155	
   156	    case_id, run_label = parse_run_id(run_id)
   157	    manifest = _read_run_manifest(case_id, run_label)
   158	    if manifest is None:
   159	        raise HTTPException(status_code=404, detail="artifact not found")
   160	    timestamp = manifest.get("timestamp", "")
   161	    if not timestamp:
   162	        raise HTTPException(status_code=404, detail="artifact not found")
   163	
   164	    root = _current_fields_root()
   165	    artifact_dir = root / case_id / timestamp
   166	    if not artifact_dir.is_dir():
   167	        raise HTTPException(status_code=404, detail="artifact not found")
   168	
   169	    # We serve basenames; files may live in subdirs (VTK/x.vtk). Walk and match.
   170	    # This mirrors audit_package.py's traversal defense.
   171	    for p in artifact_dir.rglob(filename):
   172	        try:
   173	            resolved = p.resolve()
   174	            resolved.relative_to(artifact_dir.resolve())
   175	        except (ValueError, OSError):
   176	            continue
   177	        if resolved.is_file() and resolved.name == filename:
   178	            return resolved
   179	    raise HTTPException(status_code=404, detail="artifact not found")

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
    58	    "/runs/{run_id}/field-artifacts/{filename}",
    59	    tags=["field-artifacts"],
    60	)
    61	def download_field_artifact(run_id: str, filename: str) -> FileResponse:
    62	    """Serve a single field artifact file. Traversal-safe."""
    63	    path = resolve_artifact_path(run_id, filename)  # raises HTTPException(404)
    64	    return FileResponse(
    65	        path,
    66	        media_type=_media_type_for(path),
    67	        filename=path.name,
    68	    )

exec
/bin/zsh -lc "nl -ba ui/backend/tests/test_field_artifacts_route.py | sed -n '1,180p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba ui/backend/schemas/validation.py | sed -n '210,255p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba ui/backend/services/run_ids.py | sed -n '1,80p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
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

 succeeded in 0ms:
     1	"""Phase 7a — run_id parsing helper.
     2	
     3	Per user ratification #5 (2026-04-21): run_id = "{case_id}__{run_label}".
     4	We use rpartition on the last "__" so case_ids with internal underscores
     5	(e.g. 'lid_driven_cavity') still parse correctly (07a-RESEARCH.md §2.7).
     6	"""
     7	from __future__ import annotations
     8	
     9	from fastapi import HTTPException
    10	
    11	
    12	def parse_run_id(run_id: str) -> tuple[str, str]:
    13	    """Parse 'lid_driven_cavity__audit_real_run' → ('lid_driven_cavity', 'audit_real_run').
    14	
    15	    Uses rpartition on '__' so the label is the LAST token; case_id keeps any
    16	    internal underscores. Labels today are simple identifiers without '__';
    17	    rpartition is resilient if that changes.
    18	
    19	    Raises HTTPException(400) on malformed input.
    20	    """
    21	    if "__" not in run_id:
    22	        raise HTTPException(
    23	            status_code=400,
    24	            detail=f"run_id must match '{{case}}__{{label}}': got {run_id!r}",
    25	        )
    26	    case_id, _, run_label = run_id.rpartition("__")
    27	    if not case_id or not run_label:
    28	        raise HTTPException(
    29	            status_code=400,
    30	            detail=f"run_id has empty case_id or label: {run_id!r}",
    31	        )
    32	    return case_id, run_label

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
   104	    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts/lid_driven_cavity_2000.vtk")
   105	    assert r.status_code == 200, r.text
   106	
   107	
   108	def test_download_404_traversal(client: TestClient) -> None:
   109	    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts/..%2F..%2Fetc%2Fpasswd")
   110	    assert r.status_code == 404, r.text
   111	
   112	
   113	def test_download_404_missing(client: TestClient) -> None:
   114	    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts/does_not_exist.csv")
   115	    assert r.status_code == 404, r.text

exec
/bin/zsh -lc "nl -ba .planning/phases/07a-field-capture/_integration_evidence.txt | sed -n '150,164p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba ui/backend/tests/test_phase5_byte_repro.py | sed -n '1,165p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   150	ui/backend/tests/test_case_export.py .............                       [ 43%]
   151	ui/backend/tests/test_decisions_and_dashboard.py ........                [ 52%]
   152	ui/backend/tests/test_field_artifacts_route.py ...........               [ 64%]
   153	ui/backend/tests/test_grid_convergence_monotonicity.py ..........        [ 75%]
   154	ui/backend/tests/test_health.py .                                        [ 76%]
   155	ui/backend/tests/test_phase5_byte_repro.py ............                  [ 90%]
   156	ui/backend/tests/test_validation_report.py .........                     [100%]
   157	
   158	============================= 90 passed in 24.21s ==============================
   159	{"run_id":"lid_driven_cavity__audit_real_run","case_id":"lid_driven_cavity","run_label":"audit_real_run","timestamp":"20260421T082340Z","artifacts":[{"kind":"vtk","filename":"allPatches_1024.vtk","url":"/api/runs/lid_driven_cavity__audit_real_run/field-artifacts/allPatches_1024.vtk","sha256":"a6113287904d744a524ef401ec7f5f389e0c8842988d8ba1df3e9c10f9f376dc","size_bytes":45784},{"kind":"vtk","filename":"ldc_59058_1776759820768_1024.vtk","url":"/api/runs/lid_driven_cavity__audit_real_run/field-artifacts/ldc_59058_1776759820768_1024.vtk","sha256":"bd454c0b561e06a6e41f601cf38773d8236d3b254d2e612ccd3c7b4d459da0c6","size_bytes":3155888},{"kind":"csv","filename":"uCenterline.xy","url":"/api/runs/lid_driven_cavity__audit_real_run/field-artifacts/uCenterline.xy","sha256":"c537678e916036fe0845a0452605e0ddee8c2bfd7a96eaa808dd73f59aa619cf","size_bytes":9099},{"kind":"csv","filename":"uCenterline.xy","url":"/api/runs/lid_driven_cavity__audit_real_run/field-artifacts/uCenterline.xy","sha256":"bc95a829b8e5c40a935692125daa76681050e7eaa03f8c509467616b73a0f461","size_bytes":9099},{"kind":"csv","filename":"uCenterline.xy","url":"/api/runs/lid_driven_cavity__audit_real_run/field-artifacts/uCenterline.xy","sha256":"6ba22156053d470b18da7eaab0eb35ab974267c941d8693963d4d596112f9369","size_bytes":9099},{"kind":"residual_log","filename":"log.simpleFoam","url":"/api/runs/lid_driven_cavity__audit_real_run/field-artifacts/log.simpleFoam","sha256":"a6f33f3c4f6cd94f7c0f9e2313d4e38115f051668d0086e0abfff28efd80af7f","size_bytes":490559},{"kind":"residual_log","filename":"residuals.csv","url":"/api/runs/lid_driven_cavity__audit_real_run/field-artifacts/residuals.csv","sha256":"bd734927184e0afd5467eeb1de045d9deed32164d880f345c3beb1669528238e","size_bytes":43972},{"kind":"residual_log","filename":"residuals.dat","url":"/api/runs/lid_driven_cavity__audit_real_run/field-artifacts/residuals.dat","sha256":"9e0b4a90a3acacc07414fbc3227e808fbcfa6d4a9192e6ab7bf3ff86db70256f","size_bytes":55394}]}
   160	--http_status=200
   161	download_status=200
   162	Time,Ux,Uy,p
   163	0,N/A,N/A
   164	1,1.000000e+00,9.978487e-01,1.000000e+00

 succeeded in 0ms:
     1	"""Phase 5a byte-reproducibility guard.
     2	
     3	Enforces that every `audit_real_run_measurement.yaml` under fixtures/runs/
     4	parses to a stable shape and that its non-deterministic fields are the only
     5	things that vary across re-runs. The test does NOT actually re-run the
     6	solver (that would be a minutes-scale integration test); instead it
     7	verifies the *schema* contract that makes byte-repro feasible:
     8	
     9	1. Every audit fixture has exactly the expected top-level keys.
    10	2. `run_metadata.run_id == "audit_real_run"` (not a per-run hash).
    11	3. `measurement.run_id` and `measurement.commit_sha` track the commit.
    12	4. `measurement.measured_at` is the only timestamp field.
    13	5. YAML dump is stable (sort_keys=False; default_flow_style=False; same
    14	   key ordering as what scripts/phase5_audit_run.py writes).
    15	
    16	The full solver-rerun byte-repro test is gated by `EXECUTOR_MODE=foam_agent`
    17	and lives in `tests/integration/` (not collected by default pytest run).
    18	"""
    19	
    20	from __future__ import annotations
    21	
    22	from pathlib import Path
    23	
    24	import pytest
    25	import yaml
    26	
    27	REPO_ROOT = Path(__file__).resolve().parents[3]
    28	RUNS_DIR = REPO_ROOT / "ui" / "backend" / "tests" / "fixtures" / "runs"
    29	
    30	_REQUIRED_TOP_KEYS = {
    31	    "run_metadata",
    32	    "case_id",
    33	    "source",
    34	    "measurement",
    35	    "audit_concerns",
    36	    "decisions_trail",
    37	}
    38	_REQUIRED_METADATA_KEYS = {
    39	    "run_id",
    40	    "label_zh",
    41	    "label_en",
    42	    "description_zh",
    43	    "category",
    44	    "expected_verdict",
    45	}
    46	_REQUIRED_MEASUREMENT_KEYS = {
    47	    "value",
    48	    "unit",
    49	    "run_id",
    50	    "commit_sha",
    51	    "measured_at",
    52	    "quantity",
    53	    "extraction_source",
    54	    "solver_success",
    55	    "comparator_passed",
    56	}
    57	
    58	
    59	def _audit_fixtures() -> list[Path]:
    60	    return sorted(RUNS_DIR.glob("*/audit_real_run_measurement.yaml"))
    61	
    62	
    63	def test_at_least_one_audit_fixture_exists():
    64	    """Phase 5a must produce at least one audit fixture for us to gate on."""
    65	    fixtures = _audit_fixtures()
    66	    assert fixtures, (
    67	        "Expected at least one audit_real_run_measurement.yaml under "
    68	        "fixtures/runs/*/. Regenerate via: "
    69	        "EXECUTOR_MODE=foam_agent .venv/bin/python "
    70	        "scripts/phase5_audit_run.py --all"
    71	    )
    72	
    73	
    74	@pytest.mark.parametrize("path", _audit_fixtures(), ids=lambda p: p.parent.name)
    75	def test_audit_fixture_schema_contract(path: Path):
    76	    """Every audit fixture satisfies the schema that makes byte-repro possible."""
    77	    with path.open("r", encoding="utf-8") as fh:
    78	        doc = yaml.safe_load(fh)
    79	
    80	    assert isinstance(doc, dict), f"{path.name} should parse to a dict"
    81	    missing = _REQUIRED_TOP_KEYS - set(doc.keys())
    82	    assert not missing, f"{path} missing top-level keys: {missing}"
    83	
    84	    md = doc["run_metadata"]
    85	    assert md["run_id"] == "audit_real_run", (
    86	        f"{path} run_metadata.run_id must be literally 'audit_real_run' "
    87	        "(not a per-run hash) so byte-repro can identify the same logical "
    88	        f"run across commits; got {md['run_id']!r}"
    89	    )
    90	    md_missing = _REQUIRED_METADATA_KEYS - set(md.keys())
    91	    assert not md_missing, f"{path} run_metadata missing: {md_missing}"
    92	    assert md["category"] == "audit_real_run", (
    93	        f"{path} category must be 'audit_real_run'; got {md['category']!r}"
    94	    )
    95	    assert md["expected_verdict"] in {"PASS", "FAIL", "HAZARD", "UNKNOWN"}, (
    96	        f"{path} expected_verdict must be a known ContractStatus; "
    97	        f"got {md['expected_verdict']!r}"
    98	    )
    99	
   100	    m = doc["measurement"]
   101	    m_missing = _REQUIRED_MEASUREMENT_KEYS - set(m.keys())
   102	    assert not m_missing, f"{path} measurement missing: {m_missing}"
   103	
   104	    case_id = path.parent.name
   105	    assert doc["case_id"] == case_id, (
   106	        f"{path} case_id field {doc['case_id']!r} must match parent dir {case_id!r}"
   107	    )
   108	    assert m["run_id"].startswith(f"audit_{case_id}_"), (
   109	        f"{path} measurement.run_id must start with audit_{case_id}_; "
   110	        f"got {m['run_id']!r}"
   111	    )
   112	    assert len(m["commit_sha"]) >= 7, (
   113	        f"{path} commit_sha must be at least 7 chars; got {m['commit_sha']!r}"
   114	    )
   115	    assert isinstance(m["solver_success"], bool)
   116	    assert isinstance(m["comparator_passed"], bool)
   117	
   118	
   119	def test_audit_fixtures_nondeterministic_fields_are_isolated():
   120	    """The exact set of fields that vary across re-runs must be bounded.
   121	
   122	    This is the byte-reproducibility contract: given identical mesh +
   123	    schemes + fvSolution, simpleFoam is deterministic. Only the fields
   124	    listed here may differ between two re-runs. Anything else differing
   125	    is a regression we want to catch.
   126	    """
   127	    allowed_nondeterministic = {
   128	        "measurement.run_id",      # contains commit_sha suffix
   129	        "measurement.commit_sha",  # commit at time of run
   130	        "measurement.measured_at", # ISO timestamp
   131	        "run_metadata.description_zh",  # contains commit_sha in prose
   132	    }
   133	    # This test documents the contract; it doesn't enforce anything at
   134	    # runtime since we have a single fixture per case. The integration
   135	    # test that actually re-runs the solver lives separately.
   136	    assert allowed_nondeterministic == {
   137	        "measurement.run_id",
   138	        "measurement.commit_sha",
   139	        "measurement.measured_at",
   140	        "run_metadata.description_zh",
   141	    }, "If you widen this set, justify in a DEC and update the audit PDF caveat."

exec
/bin/zsh -lc "nl -ba ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml | sed -n '40,55p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
    40	    u_centerline[y=0.8125]: actual=0.1391738750000001 expected=0.15538'
    41	  decision_refs:
    42	  - DEC-V61-028
    43	decisions_trail:
    44	- decision_id: DEC-V61-028
    45	  date: '2026-04-21'
    46	  title: Phase 5a audit pipeline — real-solver fixtures
    47	  autonomous: true
    48	field_artifacts:
    49	  manifest_path_rel: reports/phase5_fields/lid_driven_cavity/runs/audit_real_run.json
    50	  run_label: audit_real_run

codex
A concrete issue is emerging in the backend path surface: `filename` is guarded, but `run_id` parsing accepts `.` / `..` as a case id and then builds filesystem paths from it. I’m checking whether that is practically reachable through the route and whether the duplicate `uCenterline.xy` basename also causes an observable API mismatch.
exec
/bin/zsh -lc "find reports/phase5_fields -maxdepth 5 -type f | sed -n '1,120p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc 'find ui/backend/tests/fixtures/phase7a_sample_fields -maxdepth 5 -type f -print | sort' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
reports/phase5_fields/lid_driven_cavity/20260421T082340Z/residuals/0/residuals.dat
reports/phase5_fields/lid_driven_cavity/20260421T082340Z/log.simpleFoam
reports/phase5_fields/lid_driven_cavity/20260421T082340Z/VTK/allPatches/allPatches_1024.vtk
reports/phase5_fields/lid_driven_cavity/20260421T082340Z/VTK/ldc_59058_1776759820768_1024.vtk
reports/phase5_fields/lid_driven_cavity/20260421T082340Z/residuals.csv
reports/phase5_fields/lid_driven_cavity/20260421T082340Z/sample/0/uCenterline.xy
reports/phase5_fields/lid_driven_cavity/20260421T082340Z/sample/500/uCenterline.xy
reports/phase5_fields/lid_driven_cavity/20260421T082340Z/sample/1000/uCenterline.xy
reports/phase5_fields/lid_driven_cavity/runs/audit_real_run.json

 succeeded in 0ms:
ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/20260421T000000Z/VTK/lid_driven_cavity_2000.vtk
ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/20260421T000000Z/residuals.csv
ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/20260421T000000Z/uCenterline_U_p.xy
ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/runs/audit_real_run.json

exec
/bin/zsh -lc "find reports/phase5_fields/lid_driven_cavity -maxdepth 5 -type f -name 'uCenterline.xy' -print" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
reports/phase5_fields/lid_driven_cavity/20260421T082340Z/sample/0/uCenterline.xy
reports/phase5_fields/lid_driven_cavity/20260421T082340Z/sample/500/uCenterline.xy
reports/phase5_fields/lid_driven_cavity/20260421T082340Z/sample/1000/uCenterline.xy

exec
/bin/zsh -lc "find reports -maxdepth 3 -type f -path '*/runs/*.json' -print | sed -n '1,40p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
exec
/bin/zsh -lc ".venv/bin/python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
import json
from fastapi.testclient import TestClient
from ui.backend.main import app
from ui.backend.services.field_artifacts import set_fields_root_for_testing

with TemporaryDirectory() as d:
    root = Path(d) / 'fields'
    # Normal root is /tmp/.../fields. case_id='..' makes manifest path root/../runs/pwn.json
    outside_runs = root.parent / 'runs'
    outside_artifacts = root.parent / 'outside_artifacts'
    outside_runs.mkdir(parents=True)
    outside_artifacts.mkdir(parents=True)
    (outside_artifacts / 'leak.csv').write_text('secret\\n', encoding='utf-8')
    (outside_runs / 'pwn.json').write_text(json.dumps({
        'run_label': 'pwn',
        'timestamp': 'outside_artifacts',
        'case_id': '..',
        'artifact_dir_rel': 'irrelevant',
    }), encoding='utf-8')
    set_fields_root_for_testing(root)
    try:
        c = TestClient(app)
        r = c.get('/api/runs/..__pwn/field-artifacts')
        print('manifest', r.status_code, r.text[:240])
        r2 = c.get('/api/runs/..__pwn/field-artifacts/leak.csv')
        print('download', r2.status_code, r2.text[:80])
    finally:
        set_fields_root_for_testing(None)
PY" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 294ms:
manifest 404 {"detail":"no field artifacts for run_id='..__pwn'"}
download 404 {"detail":"artifact not found"}

exec
/bin/zsh -lc ".venv/bin/python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
import json
from ui.backend.services.field_artifacts import set_fields_root_for_testing, list_artifacts, resolve_artifact_path

with TemporaryDirectory() as d:
    root = Path(d) / 'fields'
    outside_runs = root.parent / 'runs'
    outside_artifacts = root.parent / 'outside_artifacts'
    outside_runs.mkdir(parents=True)
    outside_artifacts.mkdir(parents=True)
    (outside_artifacts / 'leak.csv').write_text('secret\\n', encoding='utf-8')
    (outside_runs / 'pwn.json').write_text(json.dumps({'timestamp':'outside_artifacts'}), encoding='utf-8')
    set_fields_root_for_testing(root)
    try:
        print('manifest path exists', (root/'..'/'runs'/'pwn.json').resolve(), (root/'..'/'runs'/'pwn.json').is_file())
        print('artifact dir exists', (root/'..'/'outside_artifacts').resolve(), (root/'..'/'outside_artifacts').is_dir())
        print(list_artifacts('..__pwn'))
        print(resolve_artifact_path('..__pwn','leak.csv'))
    finally:
        set_fields_root_for_testing(None)
PY" in /Users/Zhuanz/Desktop/cfd-harness-unified
 exited 1 in 131ms:
Traceback (most recent call last):
  File "<stdin>", line 19, in <module>
  File "/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/field_artifacts.py", line 159, in resolve_artifact_path
manifest path exists /private/var/folders/q4/859yhpgn6x3fx6kv4mj5gmv40000gp/T/tmpn85aqqye/runs/pwn.json False
artifact dir exists /private/var/folders/q4/859yhpgn6x3fx6kv4mj5gmv40000gp/T/tmpn85aqqye/outside_artifacts False
None
    raise HTTPException(status_code=404, detail="artifact not found")
fastapi.exceptions.HTTPException: 404: artifact not found

exec
/bin/zsh -lc ".venv/bin/python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
import json
from fastapi.testclient import TestClient
from ui.backend.main import app
from ui.backend.services.field_artifacts import set_fields_root_for_testing, list_artifacts, resolve_artifact_path

with TemporaryDirectory() as d:
    root = Path(d) / 'fields'
    root.mkdir()
    outside_runs = root.parent / 'runs'
    outside_artifacts = root.parent / 'outside_artifacts'
    outside_runs.mkdir(parents=True)
    outside_artifacts.mkdir(parents=True)
    (outside_artifacts / 'leak.csv').write_text('secret\\n', encoding='utf-8')
    (outside_runs / 'pwn.json').write_text(json.dumps({'timestamp':'outside_artifacts'}), encoding='utf-8')
    set_fields_root_for_testing(root)
    try:
        print('service manifest', list_artifacts('..__pwn'))
        print('service path', resolve_artifact_path('..__pwn','leak.csv'))
        c = TestClient(app)
        r = c.get('/api/runs/..__pwn/field-artifacts')
        print('route manifest', r.status_code, r.text[:240])
        r2 = c.get('/api/runs/..__pwn/field-artifacts/leak.csv')
        print('route download', r2.status_code, r2.text[:80])
    finally:
        set_fields_root_for_testing(None)
PY" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 231ms:
service manifest run_id='..__pwn' case_id='..' run_label='pwn' timestamp='outside_artifacts' artifacts=[FieldArtifact(kind='csv', filename='leak.csv', url='/api/runs/..__pwn/field-artifacts/leak.csv', sha256='b37e50cedcd3e3f1ff64f4afc0422084ae694253cf399326868e07a35f4a45fb', size_bytes=7)]
service path /private/var/folders/q4/859yhpgn6x3fx6kv4mj5gmv40000gp/T/tmp__8txxyu/outside_artifacts/leak.csv
route manifest 200 {"run_id":"..__pwn","case_id":"..","run_label":"pwn","timestamp":"outside_artifacts","artifacts":[{"kind":"csv","filename":"leak.csv","url":"/api/runs/..__pwn/field-artifacts/leak.csv","sha256":"b37e50cedcd3e3f1ff64f4afc0422084ae694253cf399
route download 200 secret


exec
/bin/zsh -lc "nl -ba src/foam_agent_adapter.py | sed -n '400,455p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba src/foam_agent_adapter.py | sed -n '635,650p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   400	    def __init__(
   401	        self,
   402	        work_dir: Optional[str] = None,
   403	        container_name: Optional[str] = None,
   404	        ncx: int = 40,
   405	        ncy: int = 20,
   406	    ) -> None:
   407	        self._work_dir = Path(work_dir or self.DEFAULT_WORK_DIR)
   408	        self._container_name = container_name or self.CONTAINER_NAME
   409	        self._timeout = self.SOLVER_TIMEOUT
   410	        self._docker_client: Any = None
   411	        self._ncx = ncx
   412	        self._ncy = ncy
   413	
   414	    # ------------------------------------------------------------------
   415	    # Public interface
   416	    # ------------------------------------------------------------------
   417	
   418	    def execute(self, task_spec: TaskSpec) -> ExecutionResult:
   419	        t0 = time.monotonic()
   420	
   421	        # 1. Python docker SDK available?
   422	        if not _DOCKER_AVAILABLE:
   423	            return self._fail(
   424	                "Docker Python SDK not installed. Real-solver execution "
   425	                "requires the cfd-real-solver optional deps. Install with: "
   426	                "`.venv/bin/pip install -e '.[cfd-real-solver]'` (or "
   427	                "`pip install 'docker>=7.0'`). "
   428	                "MockExecutor remains available for unit-test paths "
   429	                "(EXECUTOR_MODE=mock).",
   430	                time.monotonic() - t0,
   431	            )
   432	
   433	        # 2. Docker daemon reachable and container running?
   434	        try:
   435	            self._docker_client = docker.from_env()
   436	            container = self._docker_client.containers.get(self._container_name)
   437	            if container.status != "running":
   438	                raise docker.errors.DockerException(
   439	                    f"Container '{self._container_name}' is not running "
   440	                    f"(status={container.status})."
   441	                )
   442	        except docker.errors.DockerException as exc:
   443	            # `docker.errors.NotFound` is a subclass of DockerException; use
   444	            # isinstance dispatch so tests that mock only DockerException
   445	            # don't trip on a missing/non-class NotFound attribute.
   446	            not_found_cls = getattr(docker.errors, "NotFound", None)
   447	            try:
   448	                is_not_found = (
   449	                    isinstance(not_found_cls, type)
   450	                    and isinstance(exc, not_found_cls)
   451	                )
   452	            except TypeError:
   453	                is_not_found = False
   454	            if is_not_found:
   455	                return self._fail(

 succeeded in 0ms:
   635	                execution_time_s=elapsed,
   636	                raw_output_path=raw_output_path,
   637	            )
   638	
   639	        finally:
   640	            # 清理临时 case 目录（Python 3.9 兼容，不使用 missing_ok）
   641	            try:
   642	                shutil.rmtree(case_host_dir)
   643	            except FileNotFoundError:
   644	                pass
   645	
   646	    # ------------------------------------------------------------------
   647	    # Case file generation (Lid-Driven Cavity)
   648	    # ------------------------------------------------------------------
   649	
   650	    def _turbulence_model_for_solver(

exec
/bin/zsh -lc "nl -ba src/foam_agent_adapter.py | sed -n '7010,7040p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc 'rg -n "finally|case_host_dir|shutil.rmtree|TemporaryDirectory|cleanup|tear" src/foam_agent_adapter.py' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
  7010	            rows.append(line.split())
  7011	        if not header or not rows:
  7012	            return
  7013	        with csv_path.open("w", encoding="utf-8") as fh:
  7014	            fh.write(",".join(header) + "\n")
  7015	            for r in rows:
  7016	                fh.write(",".join(r) + "\n")
  7017	
  7018	    # ------------------------------------------------------------------
  7019	    # Log parsing
  7020	    # ------------------------------------------------------------------
  7021	
  7022	    def _parse_solver_log(self, log_path: Path, solver_name: str = "icoFoam", task_spec: Optional[TaskSpec] = None) -> Tuple[Dict[str, float], Dict[str, Any]]:
  7023	        """解析 solver log 文件，提取最终（末次迭代）残差和关键物理量。
  7024	
  7025	        Args:
  7026	            log_path: log 文件路径
  7027	            solver_name: "icoFoam" 或 "simpleFoam" 或 "buoyantFoam"
  7028	            task_spec: 任务规格，用于 case-specific 物理量解释
  7029	
  7030	        Returns:
  7031	            (residuals, key_quantities)
  7032	        """
  7033	        if not log_path.exists():
  7034	            return {}, {}
  7035	
  7036	        text = log_path.read_text(encoding="utf-8", errors="replace")
  7037	
  7038	        residuals: Dict[str, float] = {}
  7039	        key_quantities: Dict[str, Any] = {}
  7040	

 succeeded in 0ms:
479:        case_host_dir = self._work_dir / case_id
482:            case_host_dir.mkdir(parents=True, exist_ok=True)
489:        raw_output_path = str(case_host_dir)
494:                self._generate_backward_facing_step(case_host_dir, task_spec)
497:                self._generate_natural_convection_cavity(case_host_dir, task_spec)
502:                    self._generate_steady_internal_channel(case_host_dir, task_spec)
509:                    self._generate_circular_cylinder_wake(case_host_dir, task_spec, turbulence_model)
515:                self._generate_airfoil_flow(case_host_dir, task_spec, turbulence_model)
517:                self._generate_impinging_jet(case_host_dir, task_spec)
525:                    self._generate_lid_driven_cavity(case_host_dir, task_spec)
532:                    self._generate_steady_internal_flow(case_host_dir, task_spec, turbulence_model)
534:                self._generate_lid_driven_cavity(case_host_dir, task_spec)
597:            self._copy_postprocess_fields(container, case_cont_dir, case_host_dir)
600:            #      BEFORE the finally-block tears down case_host_dir.
615:                    case_host_dir,
621:            log_path = case_host_dir / f"log.{solver_name}"
639:        finally:
642:                shutil.rmtree(case_host_dir)
6827:        self, container: Any, case_cont_dir: str, case_host_dir: Path
6859:            host_time_dir = case_host_dir / latest_time
6883:        case_host_dir: Path,
6888:        before the finally-block tears down case_host_dir.
6958:                src = case_host_dir / logname

exec
/bin/zsh -lc "nl -ba src/foam_agent_adapter.py | sed -n '470,545p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   470	        except Exception as exc:
   471	            return self._fail(
   472	                f"Unexpected error initialising Docker client / container: "
   473	                f"{exc!r}",
   474	                time.monotonic() - t0,
   475	            )
   476	
   477	        # 3. 准备临时 case 目录
   478	        case_id = f"ldc_{os.getpid()}_{int(time.time() * 1000)}"
   479	        case_host_dir = self._work_dir / case_id
   480	        case_cont_dir = f"/tmp/cfd-harness-cases/{case_id}"
   481	        try:
   482	            case_host_dir.mkdir(parents=True, exist_ok=True)
   483	        except Exception as exc:
   484	            return self._fail(
   485	                f"Cannot create case directory: {exc}",
   486	                time.monotonic() - t0,
   487	            )
   488	
   489	        raw_output_path = str(case_host_dir)
   490	
   491	        try:
   492	            # 4. 根据几何类型生成 case 文件
   493	            if task_spec.geometry_type == GeometryType.BACKWARD_FACING_STEP:
   494	                self._generate_backward_facing_step(case_host_dir, task_spec)
   495	                solver_name = "simpleFoam"
   496	            elif task_spec.geometry_type == GeometryType.NATURAL_CONVECTION_CAVITY:
   497	                self._generate_natural_convection_cavity(case_host_dir, task_spec)
   498	                solver_name = "buoyantFoam"
   499	            elif task_spec.geometry_type == GeometryType.BODY_IN_CHANNEL:
   500	                # 路由: INTERNAL (Plane Channel Flow DNS) → icoFoam laminar; EXTERNAL (Circular Cylinder Wake) → pimpleFoam
   501	                if task_spec.flow_type == FlowType.INTERNAL:
   502	                    self._generate_steady_internal_channel(case_host_dir, task_spec)
   503	                    solver_name = "icoFoam"
   504	                else:
   505	                    solver_name = "pimpleFoam"
   506	                    turbulence_model = self._turbulence_model_for_solver(
   507	                        solver_name, task_spec.geometry_type, task_spec.Re
   508	                    )
   509	                    self._generate_circular_cylinder_wake(case_host_dir, task_spec, turbulence_model)
   510	            elif task_spec.geometry_type == GeometryType.AIRFOIL:
   511	                solver_name = "simpleFoam"
   512	                turbulence_model = self._turbulence_model_for_solver(
   513	                    solver_name, task_spec.geometry_type, task_spec.Re
   514	                )
   515	                self._generate_airfoil_flow(case_host_dir, task_spec, turbulence_model)
   516	            elif task_spec.geometry_type == GeometryType.IMPINGING_JET:
   517	                self._generate_impinging_jet(case_host_dir, task_spec)
   518	                solver_name = "buoyantFoam"
   519	            elif task_spec.geometry_type == GeometryType.SIMPLE_GRID:
   520	                # LDC: canonical name match, no Re-heuristic (Codex MEDIUM: the
   521	                # `Re < 2300` fallback was too broad — any SIMPLE_GRID laminar
   522	                # case would get routed through the cavity generator, silent
   523	                # wrong-physics risk).
   524	                if self._is_lid_driven_cavity_case(task_spec, "simpleFoam"):
   525	                    self._generate_lid_driven_cavity(case_host_dir, task_spec)
   526	                    solver_name = "simpleFoam"
   527	                else:
   528	                    solver_name = "simpleFoam"
   529	                    turbulence_model = self._turbulence_model_for_solver(
   530	                        solver_name, task_spec.geometry_type, task_spec.Re
   531	                    )
   532	                    self._generate_steady_internal_flow(case_host_dir, task_spec, turbulence_model)
   533	            else:
   534	                self._generate_lid_driven_cavity(case_host_dir, task_spec)
   535	                solver_name = "simpleFoam"
   536	
   537	            # 5. 执行 blockMesh
   538	            blockmesh_ok, blockmesh_log = self._docker_exec(
   539	                "blockMesh", case_cont_dir, self.BLOCK_MESH_TIMEOUT,
   540	            )
   541	            if not blockmesh_ok:
   542	                return self._fail(
   543	                    f"blockMesh failed:\n{blockmesh_log}",
   544	                    time.monotonic() - t0,
   545	                    raw_output_path=raw_output_path,

exec
/bin/zsh -lc "rg -n \"_emit_phase7a_function_objects|functions|controlDict\" src/foam_agent_adapter.py | sed -n '1,80p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
665:    def _emit_phase7a_function_objects(turbulence_model: str = "laminar") -> str:
666:        """Phase 7a — return the controlDict `functions{}` block as a raw string.
690:            "\nfunctions\n"
808:        # 3. system/controlDict (Phase 7a: functions{} block injected before fence)
823:    object      controlDict;
861:        (case_dir / "system" / "controlDict").write_text(
863:            + self._emit_phase7a_function_objects(turbulence_model="laminar")
1210:        # 3. system/controlDict — simpleFoam, steady-state
1211:        (case_dir / "system" / "controlDict").write_text(
1226:    object      controlDict;
2082:        # 5. system/controlDict — buoyantSimpleFoam
2103:    object      controlDict;
2143:        (case_dir / "system" / "controlDict").write_text(
3220:        # 3. system/controlDict
3221:        (case_dir / "system" / "controlDict").write_text(
3236:    object      controlDict;
3616:        # system/controlDict
3617:        (case_dir / "system" / "controlDict").write_text(
3632:    object      controlDict;
4517:        # system/controlDict — pimpleFoam transient
4518:        (case_dir / "system" / "controlDict").write_text(
4533:    object      controlDict;
5189:        (case_dir / "system" / "controlDict").write_text(
5203:    object      controlDict;
5225:functions
6064:        (case_dir / "system" / "controlDict").write_text(
6079:    object      controlDict;
6364:        # 0/nut — turbulent viscosity with wall functions on the airfoil patch

exec
/bin/zsh -lc "nl -ba src/foam_agent_adapter.py | sed -n '790,870p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   790	\\*---------------------------------------------------------------------------*/
   791	FoamFile
   792	{
   793	    version     2.0;
   794	    format      ascii;
   795	    class       dictionary;
   796	    location    "constant";
   797	    object      momentumTransport;
   798	}
   799	// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
   800	
   801	simulationType  laminar;
   802	
   803	// ************************************************************************* //
   804	""",
   805	            encoding="utf-8",
   806	        )
   807	
   808	        # 3. system/controlDict (Phase 7a: functions{} block injected before fence)
   809	        _controldict_head = """\
   810	/*--------------------------------*- C++ -*---------------------------------*\\
   811	| =========                 |                                                 |
   812	| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
   813	|  \\\\    /   O peration     | Version:  10                                    |
   814	|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
   815	|    \\\\/     M anipulation  |                                                 |
   816	\\*---------------------------------------------------------------------------*/
   817	FoamFile
   818	{
   819	    version     2.0;
   820	    format      ascii;
   821	    class       dictionary;
   822	    location    "system";
   823	    object      controlDict;
   824	}
   825	// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
   826	
   827	application     simpleFoam;
   828	
   829	startFrom       startTime;
   830	
   831	startTime       0;
   832	
   833	stopAt          endTime;
   834	
   835	endTime         2000;
   836	
   837	deltaT          1;
   838	
   839	writeControl    timeStep;
   840	
   841	writeInterval   2000;
   842	
   843	purgeWrite      0;
   844	
   845	writeFormat     ascii;
   846	
   847	writePrecision  6;
   848	
   849	writeCompression off;
   850	
   851	timeFormat      general;
   852	
   853	timePrecision   6;
   854	
   855	runTimeModifiable true;
   856	"""
   857	        _controldict_tail = "\n// ************************************************************************* //\n"
   858	        # LDC is laminar per constant/momentumTransport emitted above; pass through
   859	        # turbulence_model kwarg so the helper suppresses the yPlus block. Future
   860	        # turbulent generators (Phase 7c Sprint-2) will pass their own model string.
   861	        (case_dir / "system" / "controlDict").write_text(
   862	            _controldict_head
   863	            + self._emit_phase7a_function_objects(turbulence_model="laminar")
   864	            + _controldict_tail,
   865	            encoding="utf-8",
   866	        )
   867	
   868	        # 4. system/fvSchemes
   869	        (case_dir / "system" / "fvSchemes").write_text(
   870	            """\

exec
/bin/zsh -lc ".venv/bin/python - <<'PY'
from ui.backend.services.field_artifacts import list_artifacts, resolve_artifact_path, sha256_of
run_id='lid_driven_cavity__audit_real_run'
resp=list_artifacts(run_id)
if not resp:
    print('no manifest')
else:
    for a in resp.artifacts:
        if a.filename == 'uCenterline.xy':
            p=resolve_artifact_path(run_id, a.filename)
            print(a.filename, a.sha256, '->', p, sha256_of(p), 'match=', a.sha256 == sha256_of(p))
PY" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 133ms:
uCenterline.xy c537678e916036fe0845a0452605e0ddee8c2bfd7a96eaa808dd73f59aa619cf -> /Users/Zhuanz/Desktop/cfd-harness-unified/reports/phase5_fields/lid_driven_cavity/20260421T082340Z/sample/0/uCenterline.xy c537678e916036fe0845a0452605e0ddee8c2bfd7a96eaa808dd73f59aa619cf match= True
uCenterline.xy bc95a829b8e5c40a935692125daa76681050e7eaa03f8c509467616b73a0f461 -> /Users/Zhuanz/Desktop/cfd-harness-unified/reports/phase5_fields/lid_driven_cavity/20260421T082340Z/sample/0/uCenterline.xy c537678e916036fe0845a0452605e0ddee8c2bfd7a96eaa808dd73f59aa619cf match= False
uCenterline.xy 6ba22156053d470b18da7eaab0eb35ab974267c941d8693963d4d596112f9369 -> /Users/Zhuanz/Desktop/cfd-harness-unified/reports/phase5_fields/lid_driven_cavity/20260421T082340Z/sample/0/uCenterline.xy c537678e916036fe0845a0452605e0ddee8c2bfd7a96eaa808dd73f59aa619cf match= False

exec
/bin/zsh -lc "nl -ba /Users/Zhuanz/.codex/memories/MEMORY.md | sed -n '356,380p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
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


