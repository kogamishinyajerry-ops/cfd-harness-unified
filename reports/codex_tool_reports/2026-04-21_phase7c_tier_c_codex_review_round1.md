2026-04-21T15:10:28.387859Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-research-deerflow/SKILL.md: missing YAML frontmatter delimited by ---
2026-04-21T15:10:28.388176Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-report-pretext/SKILL.md: missing YAML frontmatter delimited by ---
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
session id: 019db097-c978-74d2-b056-e22eaf0e9d8e
--------
user
Post-merge review: DEC-V61-034 Phase 7c Sprint 2 Tier C visual-only fan-out + cylinder_wake foamToVTK fix. Merged to main as commit 575db8f at /Users/Zhuanz/Desktop/cfd-harness-unified.

This review was triggered per RETRO-V61-001 Codex-per-risky-PR baseline:
- multi-file frontend (LearnCaseDetailPage.tsx) ✓
- adapter change >5 LOC (src/foam_agent_adapter.py, ~19 LOC) ✓
- user-UX-critique-after trigger ("仍然没有真实的仿真结果") ✓
- new API contract (GET /renders/{filename:path}) ✓
- OpenFOAM foamToVTK fix (cylinder_wake SEGV in OF10) ✓

self-estimated pass-rate 0.55 → post-merge Codex is allowed per rule.

## Summary of changes across commits 4ee3fc2 + a70796a + 02cd686 + 575db8f

1. scripts/phase5_audit_run.py: _PHASE7A_OPTED_IN expanded from {ldc} to all 10 whitelist cases.

2. scripts/render_case_report.py (~330 LOC modified):
   - GOLD_OVERLAY_CASES vs VISUAL_ONLY_CASES split.
   - render_all dispatches to different renderer lists per mode.
   - NEW _parse_residuals_from_log(log_path): regex fallback when residuals.csv missing. Handles "Time = N" AND "Time = 35s" formats.
   - NEW _render_structured_contour() / _render_unstructured_contour() helpers.
   - NEW _pick_2d_plane(Cx,Cy,Cz,U): auto-detect 2D plane (NACA0012 meshed in x-z, not x-y).
   - Contour 3-tier fallback: structured → tricontourf+quiver → scatter (qhull failure).
   - NaN/inf guard: replace non-finite with 0, clip to 99th percentile before triangulation.

3. ui/backend/services/comparison_report.py:
   - _GOLD_OVERLAY_CASES + _VISUAL_ONLY_CASES; union = _REPORT_SUPPORTED_CASES.
   - NEW _build_visual_only_context(): reduced context dict (visual_only: True, no metrics/paper/GCI, just renders + solver + commit_sha). Solver detection by log.<solver> file presence.
   - build_report_context dispatches to visual-only for VISUAL_ONLY_CASES after shared load+timestamp+containment.

4. ui/backend/routes/comparison_report.py: NEW GET /cases/{case}/runs/{run}/renders/{filename:path}
   - Uses {filename:path} converter.
   - Path traversal defense: explicit `.. / / \` rejection + resolve+relative_to under _RENDERS_ROOT/case_id.
   - MIME discrimination: .png → image/png, .json → application/json, else octet-stream.
   - Missing run manifest → 404 (via _load_run_manifest raising ReportError).
   - Invalid timestamp → 404.

5. ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:
   - ComparisonReportContext type union (gold-overlay fields optional; new visual-only top-level fields: visual_only, subtitle, solver, commit_sha).
   - New branch in ScientificComparisonReportSection: detect visual_only, render 2-column contour + residuals panel, serve PNGs via /api/.../renders/ endpoint.
   - Gold-overlay branch unchanged (defensive guard: if !data.metrics || !data.meta, return null).

6. src/foam_agent_adapter.py (+19 LOC, adapter change):
   - Added -noFaceZones to both foamToVTK invocations in _capture_field_artifacts.
   - Changed error log truncation from log[:200] (head, banner-only) to log[-400:] (tail, captures SEGV stack trace + OF error).
   - Added 10-line comment block explaining the cylinder_wake cylinderBaffleZone SEGV pattern.

7. ui/backend/tests/test_comparison_report_visual_only.py (NEW, 7 tests): covers visual_only context shape, traversal rejection, tampered timestamp, 404 fallthrough, gold-overlay isolation.

Regression: 139/139 pytest green (was 132 → +7 new tests). Frontend tsc --noEmit clean.

## Focus review on

1. **Path containment in render route** (ui/backend/routes/comparison_report.py). The new GET /renders/{filename:path} route uses `{filename:path}` converter which allows / in filename. Defense steps:
   (a) explicit `.. split check` + `/ / \` prefix check
   (b) _load_run_manifest → get ts
   (c) _validated_timestamp → ^\d{8}T\d{6}Z$
   (d) target = _RENDERS_ROOT / case_id / ts / filename
   (e) resolve(strict=True) + relative_to(_RENDERS_ROOT/case_id)
   Any known bypass? Null bytes? URL-encoded ../? (Note: I test URL-encoded %2F in test_render_route_traversal_rejected and it returns 404 because {filename:path} decodes to ../../etc/passwd which starts with .. after split.)

2. **Visual-only context completeness**. Is the dict shape enough for any future consumer? Fields set: visual_only=True, case_id, run_label, timestamp, renders.{contour_png_rel,residuals_png_rel}, solver, commit_sha, verdict=None, verdict_gradient, subtitle, paper=None, metrics=None, gci=None, grid_convergence=None, deviations=None, residual_info=None, tolerance_percent=None. Any template (comparison_report.html.j2) currently relying on `metrics.max_dev_pct` or `paper.title` would crash — verify the template isn't rendered for visual-only cases. (Current flow: /learn frontend calls /comparison-report/context (JSON) not /comparison-report (HTML), so template rendering is NOT triggered for visual-only. But if someone opens /api/cases/BFS/runs/audit_real_run/comparison-report directly, what happens?)

3. **Adapter change safety** (src/foam_agent_adapter.py). `-noFaceZones` is a no-op for the 9 cases without faceZones. For cylinder_wake, it skips the cylinderBaffleZone VTK output — verify no downstream code in _parse_writeobjects_fields, _compute_key_quantities, or comparator extraction depends on faceZone VTK. Subagent claimed "cylinder wall is already emitted as a regular patch via -allPatches", but please verify the comparator key quantity extraction path (Strouhal? lift coefficient?) doesn't need the faceZone VTK.

4. **Frontend visual-only render URL construction**. `/api/cases/${caseId}/runs/${runLabel}/renders/${basename}` uses basename (e.g., "contour_u_magnitude.png") as a literal string — but the manifest actually has the full path like "reports/phase5_renders/case/ts/contour_u_magnitude.png". My frontend passes basename to the route endpoint which resolves it under the timestamped renders dir. This works because _load_run_manifest resolves the timestamp. Alternative attack: what if the frontend sends a more complex basename like "../../etc/passwd"? The route tests prove 404, but also verify browser-side URL encoding doesn't enable a bypass.

5. **Regex in _parse_residuals_from_log**. `iter_re = r"^Time\s*=\s*([0-9.eE+\-]+)s?\s*$"` — could this ReDoS or match unintended input? The regex is anchored ^$ with MULTILINE + quantified [0-9.eE+\-]+. Should be fine but worth a scan.

Reply APPROVED / APPROVED_WITH_COMMENTS / CHANGES_REQUIRED with numbered findings. If APPROVED brief. If CHANGES_REQUIRED detailed with file:line refs.
codex
I’ll treat this as a post-merge code review, not an implementation pass. I’m going to inspect the merged commit and the five named risk areas, then I’ll return a verdict with line-cited findings if anything is material.
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
/bin/zsh -lc 'rg -n "cfd-harness-unified|Phase 8|Phase 9|DEC-V61|RETRO-V61|post-merge|review" /Users/Zhuanz/.codex/memories/MEMORY.md' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
24:- codex-cli, gpt-5.4, xhigh, fast mode, priority processing, service_tier, codex debug models, additional_speed_tiers, ~/.codex/config.toml, codex exec, codex review, cx-auto
128:- when taking over an active repo, the user said "接手项目的开发" and "指挥Claude APP或者Claude CLI对项目进行深度开发优化" -> default to fixing the execution path and implementing, not staying in review/planning mode [Task 1][Task 2]
129:- when control-plane review would slow execution, the user said "决策权完全绕过Kogami和Notion里的Opus 4.7" -> if this workflow comes up again, own the local execution decisions instead of waiting on Notion-side approval unless a real gate appears [Task 1][Task 2]
160:- OpenClaw, AI-CFD, Notion作为指挥中枢，Github作为唯一代码真相库, ~/.openclaw/openclaw.json, plugins.allow, openclaw config validate --json, MAIN_OK, CODEX_BUILDER_OK, CLAUDE_REVIEW_OK, NOTION_SYNC_OK, cfd-harness-unified
176:- when naming available tools as "Codex、Claude code、Minimax", the user implicitly wanted explicit role assignment between these tool families -> future configs should assign conductor/builder/review/sync responsibilities instead of assuming a single generic agent [Task 1]
180:- The real live config surface was `~/.openclaw/openclaw.json`; the actual repo truth for this rollout was `/Users/Zhuanz/Desktop/cfd-harness-unified`, not the chat thread cwd [Task 1]
181:- The validated four-agent split was `main` as conductor, `codex-builder` for implementation/test/bugfix, `claude-review` for architecture/risk review, and `notion-sync` for spec translation/sync summaries, with separate workspaces and handoff/status artifacts under `project_state/openclaw-live-setup/` [Task 1]
184:- The usable routing at the end of the rollout was pragmatic: `main`, `codex-builder`, and `claude-review` ran on `claude-cli/opus-4.6`, while `notion-sync` used `deepseek/deepseek-chat`; Codex remained configured as fallback only [Task 2]
223:- rollout_summaries/2026-04-17T09-59-05-XzK5-ai_fea_adr006_autonomous_merges_smoke_e2e_demo_gate.md (cwd=/Users/Zhuanz/20260408 AI StructureAnalysis, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T17-59-05-019d9ae1-3a62-7232-9e44-28537fac30dd.jsonl, updated_at=2026-04-18T07:10:00+00:00, thread_id=019d9ae1-3a62-7232-9e44-28537fac30dd, review note appended without changing verdict)
227:- Review Summary, verdict unchanged, gate review note, AI-FEA-P0-10, results.vtp not visually validated, manifest contract incomplete
232:- when defining stop conditions, the user wrote "仅在以下三类情况写 REVIEW_REQUEST 到 Notion 并停机" -> stop only for ADR changes, repeated/unknown reviewer failures, or visual/demo milestones; do not create extra pauses [Task 1]
235:- when reviewing solver realism, the user said "CalculiX 是主求解器" -> future smoke/demo work must distinguish CI-safe stubs from a real solver path and must not over-claim a pass [Task 2]
243:- For milestone/demo PRs, `Review Summary` and final `Verdict` must stay separate; appending a gate review note to Notion is allowed while the PR stays open [Task 3]
248:- Symptom: CI is green but the demo gate is still not actually satisfied -> cause: the smoke test used stubs and the gate required human visual validation plus manifest-contract proof -> fix: stop at the demo gate, append a review note, and keep the PR unmerged until the human check is done [Task 2][Task 3]
305:- git status --short --branch, 287 passed, dirty worktree, .notion-cache, .planning, __pycache__, reviewable implementation path
313:- the user wanted a reviewable implementation path, so future similar runs should distinguish "suite green" from "ready to hand off" and clean or separate unrelated local artifacts before stopping [Task 5]
331:- Symptom: `287 passed` but the deliverable is still messy -> cause: local artifacts and unrelated files remained in the worktree -> fix: review the diff and clean/commit only intended changes before calling the branch handoff-ready [Task 5]
388:- `scripts/notion_sync.py` became the reusable AI-Notebooklm sync surface with `doctor`, `search`, `sync`, `writeback-phase`, `create-artifact`, `upsert-review`, and `upsert-task` commands [Task 3]
390:- Local completion was substantial in the V4.0 rollout: retrieval eval tooling, RRF tuning, staging/UAT runbooks, README updates, Notion artifact/task/review rows, and `210 passed` regression validation [Task 4]
401:# Task Group: cfd-harness-unified governance closeout and planning gates
403:scope: Close out accepted phases in `cfd-harness-unified`, normalize Notion-vs-repo naming drift, and keep future phases planning-only until the explicit solver/routing gate is reviewed.
404:applies_to: cwd=/Users/Zhuanz/Desktop/cfd-harness-unified; reuse_rule=safe for this repo’s Notion-governed phase/gate work, but phase/task IDs and review packets are rollout-specific.
406:## Task 1: Close Phase 8 and reconcile stale governance evidence
410:- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, Phase 8 closeout and evidence normalization)
414:- Phase 8, AutoVerifier, 13/13, knowledge/whitelist.yaml, ai_cfd_cold_start_whitelist.yaml, Canonical Docs Type=Report, Phase 8 Done, naming drift
416:## Task 2: Open Phase 9 as planning-only and keep solver expansion bounded
420:- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, Phase 9 kept as planning-only with decision-tree packet))
424:- Phase 9 planning-only, PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md, PHASE9_MODEL_ROUTING_BASELINE_PLAN.md, PHASE9_ACTIVATION_REVIEW_PACKET.md, replay_manifest, SU2 CLI Harness Skill, foam_agent_adapter.py
430:- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, handoff prompt prepared instead of silent activation))
434:- Opus 4.7 activation review, self-dispatch, planning-only, single-engine OpenFOAM, SU2 reference-only, CFX hold, review packet
438:- when working this repo, the user phrased the boundary as "继续推进开发，直至需要Opus 4.7介入" -> keep executing autonomously until a real gate is reached, then stop with a ready review packet [Task 1][Task 2][Task 3]
445:- Phase 9 must start from a bounded decision tree: keep single-engine OpenFOAM, allow reference-only external solver surfaces, or open one bounded proof slice; anything broader still needs review [Task 2]
451:- Symptom: planning work accidentally looks like activation -> cause: Phase 9 docs/task text are not explicit enough about `Planned` vs `Active` -> fix: state planning-only mode in phase page, tasks, dashboard summary, and review packet [Task 2]
484:- rollout_summaries/2026-04-12T15-33-54-ByPi-jerry_ai_cfd_notion_sync_and_cfd_harness_unified_context_mis.md (cwd=/Users/Zhuanz/Documents/20260330 Jerry AI CFD Project, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/12/rollout-2026-04-12T23-33-54-019d8253-fa8b-7f40-9775-46e6e03db8ac.jsonl, updated_at=2026-04-16T17:03:18+00:00, thread_id=019d8253-fa8b-7f40-9775-46e6e03db8ac, later cfd-harness-unified instruction block correctly treated as mismatch)
499:- bounded_action_plan, Phase1BoundedActionPlan, supported, clarification_needed, unsupported, result_output_surface, phase1_bounded_action_plan_only, local_review_surface, workbench upstream integration, narrow Phase 1 bounded planning boundary
505:- rollout_summaries/2026-04-02T04-41-46-kVGb-phase1_ui_distance_and_interactive_postprocess_workbench.md (cwd=/Users/Zhuanz/Documents/20260330 Jerry AI CFD Project, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/02/rollout-2026-04-02T12-41-46-019d4c7f-5489-7a63-be71-48d72549d01b.jsonl, updated_at=2026-04-07T19:00:24+00:00, thread_id=019d4c7f-5489-7a63-be71-48d72549d01b, static review seed distinguished from the desired interactive workbench)
509:- UI demo, 整个真实工作流程的UI界面, 不能只是静态UI, 自然语言交互, interactive_postprocess_workbench_v1, local_review_surface, phase1_report_review_seed_page.py, 37 passed, workflow visualization
520:- when accepted, the user wanted one concrete next step rather than options -> end this repo’s review/acceptance slices with a single next named direction [Task 1][Task 4]
530:- `local_review_surface/phase1_copilot_workbench.py` now consumes the real upstream `build_bounded_action_plan(...)` output, carries `action_plan_support_status` / `action_plan_note` / `action_plan_output_kind`, and should remain a local HTML-only, advisory-only surface [Task 4]
532:- The currently implemented UI surface is still a deterministic local HTML review seed; an NL-driven postprocess cockpit belongs to a separate governed proposal such as `interactive_postprocess_workbench_v1`, not to the already-accepted static Phase 1 path [Task 5]
541:- Symptom: a future agent overstates how close the repo is to a "real UI" -> cause: the deterministic review seed was mistaken for an interactive workbench -> fix: say clearly that the static Phase 1 chain is real and tested, but NL-triggered postprocessing and workflow control need a new governed phase [Task 5]
545:scope: Continue AI FANTUI LogicMVP automatically from `.planning` and Notion-synced state, keep the control tower current, and use approved/no-review gate state to decide whether to keep moving.
556:- AI FANTUI LogicMVP 控制塔, NOTION_API_KEY, gsd_notion_sync.py, prepare-opus-review, writeback timeout, stronger QA baseline, 175 tests OK, 10 demo smoke scenarios pass, 8/8 shared validation checks pass
582:- the user’s repeated instruction was: "根据Notion上下文、开发规则，继续全自动推进，不要停止，除非需要我手动让Opus 4.6介入审查" -> default to uninterrupted autonomous execution when the gate is approved, and only interrupt for manual Opus review [Task 2][Task 3]
665:- when reviewing the early demo, the user said "大量的文字全都放到页面次要的位置" and asked for a "简化版的拉杆" with "实时显示目前的拉杆相关的参数" -> default demo iterations to a visual-first cockpit with collapsed backstory, not prompt-first Q&A [Task 5]
688:scope: Build and sync an independent Notion control tower for AI ControlLogicMaster, integrate it with GSD automation, and treat freeze-signoff planning review as a strict read-only acceptance gate where navigation/routing text can block acceptance.
702:## Task 2: Upgrade the repo into a GSD-driven automated cockpit with manual Opus review pauses
716:- rollout_summaries/2026-04-07T14-48-14-t3g6-post_phase7_final_freeze_signoff_governance_planning_review.md (cwd=/Users/Zhuanz/20260402 AI ControlLogicMaster, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/07/rollout-2026-04-07T22-48-14-019d686a-5f10-79f2-9918-ff5cdc98e6aa.jsonl, updated_at=2026-04-08T15:13:06+00:00, thread_id=019d686a-5f10-79f2-9918-ff5cdc98e6aa, initial rejection then accepted rerun after README/docs routing fix)
720:- independent planning review, do not write acceptance_audit_log.yaml, do not modify freeze_gate_status.yaml, accepted_for_review, freeze-complete, docs incomplete, README routing, docs/README.md, MILESTONE_BOARD.md
727:- rollout_summaries/2026-04-02T16-11-48-lkTw-aplh_post_phase7_manual_review_intake_action_review.md (cwd=/Users/Zhuanz/20260402 AI ControlLogicMaster, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/03/rollout-2026-04-03T00-11-48-019d4ef7-13d3-7311-a159-a08420027a5a.jsonl, updated_at=2026-04-08T12:29:35+00:00, thread_id=019d4ef7-13d3-7311-a159-a08420027a5a, manual intake accepted but explicitly not freeze approval)
731:- FORMAL-POP-APPROVAL-20260407-002, 49 != 50, FormalPopulationExecutor, preflight_targets, manual_review_intake, accepted_for_review, pending_manual_decision, freeze-complete, checklist incomplete, freeze_gate_status hash
733:## Task 5: Create a non-executable manual review intake request package and keep routing pointed at independent review
737:- rollout_summaries/2026-04-02T18-05-38-tXWd-post_phase7_manual_review_intake_request_package.md (cwd=/Users/Zhuanz/20260402 AI ControlLogicMaster, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/03/rollout-2026-04-03T02-05-38-019d4f5f-4b79-7e92-8037-4ad30697428d.jsonl, updated_at=2026-04-08T01:38:10+00:00, thread_id=019d4f5f-4b79-7e92-8037-4ad30697428d, markdown-only request packet plus review input)
747:- the user asked to integrate GSD and make it "完全自动化的开发，除了需要暂停下来让我定期手动触发Opus 4.6审查" -> automate by default but preserve hard manual review pauses [Task 2]
748:- for freeze-signoff governance review, the user required a strict independent review with no writes to freeze artifacts -> treat this as review-only until the user explicitly changes scope [Task 3]
749:- when the user said "你是 independent approval authority… 你不是 corrected request packet 作者… 你不是 Phase 8 executor" -> preserve strict role separation between approval, review, execution, and freeze authority in this repo [Task 4]
751:- when the request-package input said the executor "must not write manual intake state" and "must not be valid input to any CLI command" -> default manual-review-intake packaging work to markdown-only, non-mutating deliverables [Task 5]
752:- when the user said acceptance "must not equal freeze approval" and "cannot directly enter final freeze signoff" -> always restate that `accepted_for_review` is not `freeze-complete`, even when readiness evidence looks strong [Task 3][Task 4]
761:- In freeze-governance review, README/docs/milestone-board routing is a real acceptance criterion; stale navigation can block acceptance even when substantive planning logic is correct [Task 3]
763:- `freeze_readiness_report.yaml` can show `formal_state: accepted_for_review`, `population_state: populated`, `validation_state: post-validated`, and `G6-E passed: true` while `freeze-readiness --dir artifacts` still fails on `Checklist Completed: Fail (Docs incomplete)`; that is planning evidence, not permission to sign off [Task 3][Task 4]
765:- The manual review intake request package in this repo is a non-executable artifact pair: `docs/POST_PHASE7_MANUAL_REVIEW_INTAKE_REQUEST.md` and `docs/POST_PHASE7_MANUAL_REVIEW_INTAKE_REQUEST_REVIEW_INPUT.md`, with README/docs routing updated so the next step is independent review rather than manual intake or freeze [Task 5]
772:- Symptom: a governance review package seems technically sound but still should not be accepted -> cause: operator-facing docs still route users to the wrong gate -> fix: verify README/docs index/milestone-board navigation before acceptance [Task 3]
774:- Symptom: a repo state labeled `accepted_for_review` is treated as manual signoff complete -> cause: manual intake acceptance, pending manual decision, and freeze completion were collapsed -> fix: keep those states distinct in reports, docs, and next-step selection [Task 3][Task 4]
775:- Symptom: a manual-review-intake packet accidentally starts behaving like an executable step -> cause: the request package, action review, and freeze flows were collapsed together -> fix: keep the packet markdown-only, keep `.aplh` state untouched, and re-read rendered README/docs routing after patching [Task 5]
931:- Phase 3, KnowledgeCompiler, orchestrator, TaskWizard, baseline freeze, publish_contract, diff_engine, benchmark validators, Opus review, task decomposition
943:- `BASELINE_MANIFEST.json` is the authoritative inventory for diff-engine work, and `publish_contract.md` plus `diff_engine.md` are the rule sources for automatic review triggers such as `EVIDENCE_EDIT` and `CHART_RULE_EDIT` [Task 4][Task 6]
951:- Symptom: Phase 3 planning overstates the readiness of the baseline -> cause: manifest counts or follow-up review items do not match the repo snapshot -> fix: start by reconciling the baseline inventory and missing follow-up items before decomposing new orchestrator work [Task 6]
1008:- g3_gate, GateConfig, trigger_gate, g4_gate, g5_gate, g6_gate, tests/test_p4_07_g3_gate.py, tests/test_p4_08_g4_g6_gates.py, trigger_code_review.sh, requests, yaml, numpy, matplotlib
1014:- rollout_summaries/2026-04-07T15-56-06-sCzN-p4_09_notion_reviews_sync.md (cwd=/Users/Zhuanz/Desktop/notion-cfd-harness, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/07/rollout-2026-04-07T23-56-06-019d68a8-8151-76c3-8c63-ea47fc4c3843.jsonl, updated_at=2026-04-07T16:09:37+00:00, thread_id=019d68a8-8151-76c3-8c63-ea47fc4c3843, Reviews DB sync with schema-aware mapping)
1239:# Task Group: notion-cfd-harness correctness-review contract
1241:scope: Perform read-only correctness reviews in `notion-cfd-harness` with line-cited findings only, no edits, no style commentary, and explicit handling for missing files or ambiguous paths.
1242:applies_to: cwd=/Users/Zhuanz/Desktop/notion-cfd-harness; reuse_rule=safe for review-style tasks in this repo family, but keep file targets and findings tied to the inspected checkout.
1244:## Task 1: Preserve the strict review-only deliverable format
1248:- rollout_summaries/2026-04-08T17-18-40-2J04-phase3_code_review_correctness_and_edge_cases.md (cwd=/Users/Zhuanz/Desktop/notion-cfd-harness, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/09/rollout-2026-04-09T01-18-40-019d6e1a-733a-7141-80bd-cb62aa056db8.jsonl, updated_at=2026-04-08T17:18:49+00:00, thread_id=019d6e1a-733a-7141-80bd-cb62aa056db8, review contract and formatting expectations)
1252:- read-only review, BUG WARNING OK, exact file path and line number, summary table, Do NOT refactor or change style, only report findings
1258:- rollout_summaries/2026-04-08T16-32-28-Z8XS-phase3_correctness_review_analogy_planner_cad.md (cwd=/Users/Zhuanz/Desktop/notion-cfd-harness, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/09/rollout-2026-04-09T00-32-28-019d6df0-25d0-7081-b84e-20b46a8ea338.jsonl, updated_at=2026-04-08T16:41:56+00:00, thread_id=019d6df0-25d0-7081-b84e-20b46a8ea338, concrete defects in analogy scoring, E6 relaxation, planner coverage, and STL parsing)
1266:- when the user asks for a review here, they mean it literally: "Do NOT refactor or change style — only flag genuine defects or missing guards" -> stay in correctness/edge-case/type-safety mode and avoid style commentary [Task 1][Task 2]
1269:- the user said "This is a read-only review. Only report findings" -> do not edit files in this workflow [Task 1]
1273:- The expected deliverable shape is one section per area with reviewed line ranges, `BUG / WARNING / OK` findings, exact snippets for non-OK items, and a final table `| Area | BUGs | WARNINGs | Status |` [Task 1]
1278:- Symptom: a review answer drifts into general commentary or architecture advice -> cause: treating “review” as broad feedback instead of a defect audit -> fix: report only grounded correctness findings with file/line references [Task 1]
1279:- Symptom: a path looks missing and the review stops there -> cause: failing to search for similarly named files first -> fix: search nearby names/locations before concluding absence, then say explicitly what was and was not found [Task 1]
1304:- /Applications/Codex.app/Contents/Resources/codex, codex exec, codex review, codex app, codex resume, cx-auto 20, CLAUDE.md, quota exhaustion, subprocess
1317:- Codex CLI itself is a normal local executable at `/Applications/Codex.app/Contents/Resources/codex`, and the available subprocess/session surfaces include `exec`, `review`, `resume`, and `app` [Task 2]
1359:- 直接复制给claude code的提示词, Opus 4.6, MiniMax, 不要从零开始, 不要推翻已有优化, GitHub integration, Claude Code on the web, scan.md, implement.md, fix.md, review-local.md, Claude March 2026 usage promotion

exec
/bin/zsh -lc 'git status --short' in /Users/Zhuanz/Desktop/cfd-harness-unified
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

exec
/bin/zsh -lc 'git show --stat --oneline --decorate --no-renames 575db8f' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
575db8f (HEAD -> main, origin/main, origin/HEAD) feat(phase7c): close Tier C fan-out + cylinder_wake foamToVTK fix (DEC-V61-034)
 ...2026-04-21_phase7c_tier_c_visual_only_fanout.md | 227 +++++++++++++++++++++
 .../2026-04-21_v61_counter20_retrospective.md      | 130 ++++++++++++
 ...0260421T150705Z_circular_cylinder_wake_raw.json |  14 ++
 .../runs/audit_real_run.json                       |   6 +
 .../20260421T150630Z/contour_u_magnitude.png       | Bin 0 -> 180613 bytes
 .../20260421T150630Z/residuals.png                 | Bin 0 -> 56265 bytes
 .../runs/audit_real_run.json                       |  11 +
 src/foam_agent_adapter.py                          |  19 +-
 .../audit_real_run_measurement.yaml                |  11 +-
 .../tests/test_comparison_report_visual_only.py    | 171 ++++++++++++++++
 10 files changed, 581 insertions(+), 8 deletions(-)

codex
I found the relevant repo memory and loaded the local GSD code-review instructions. The worktree is dirty with existing report/UI artifacts, so I’ll keep the review anchored to `HEAD`/commit `575db8f` and avoid touching files.
exec
/bin/zsh -lc "sed -n '401,445p' /Users/Zhuanz/.codex/memories/MEMORY.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
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

## User preferences

- when working this repo, the user phrased the boundary as "继续推进开发，直至需要Opus 4.7介入" -> keep executing autonomously until a real gate is reached, then stop with a ready review packet [Task 1][Task 2][Task 3]
- the rollout also showed a preference for explicit gate-aware staging rather than silent activation -> preserve the planning-only vs active distinction clearly in Notion and repo docs [Task 2][Task 3]

## Reusable knowledge

- Notion phase/task closure here requires updating both page properties and page body text; one surface alone leaves stale recovery state [Task 1]
- `knowledge/whitelist.yaml` is the active whitelist source; older references to `knowledge/ai_cfd_cold_start_whitelist.yaml` are naming drift to normalize, not a fresh design change [Task 1]
- Phase 9 must start from a bounded decision tree: keep single-engine OpenFOAM, allow reference-only external solver surfaces, or open one bounded proof slice; anything broader still needs review [Task 2]

exec
/bin/zsh -lc 'git show --name-only --format=fuller 575db8f' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
commit 575db8f717211871809d21e91836b5b83400ebb2
Author:     claude-opus47-app <claude-opus47-app@anthropic.com>
AuthorDate: Tue Apr 21 23:09:15 2026 +0800
Commit:     claude-opus47-app <claude-opus47-app@anthropic.com>
CommitDate: Tue Apr 21 23:09:15 2026 +0800

    feat(phase7c): close Tier C fan-out + cylinder_wake foamToVTK fix (DEC-V61-034)
    
    Tier C Sprint 2 visual-only fan-out complete for 9/10 cases.
    circular_cylinder_wake previously had foamToVTK SEGV in container
    (OF10 pointer bug: cylinderBaffleZone from createBaffles + phi
    interpolation onto post-baffle faceZone → segfault). Subagent
    diagnosed in 2.7min; fix is `-noFaceZones` flag — no-op for other
    9 cases, surgical one-token-per-line addition.
    
    Changes:
    - src/foam_agent_adapter.py (+19 LOC): -noFaceZones on both
      foamToVTK invocations + tail-truncate error log (log[-400:])
      since SEGV stack traces are at end, not banner head. >5 LOC
      adapter change triggers Codex mandatory (RETRO-V61-001).
    - ui/backend/tests/test_comparison_report_visual_only.py (NEW, 7 tests):
      visual-only context shape, traversal rejection, timestamp tampering,
      404 fallthrough, gold-overlay isolation.
    - .planning/decisions/2026-04-21_phase7c_tier_c_visual_only_fanout.md
      (NEW): DEC-V61-034, autonomous_governance=true, Codex invocation
      pending (post-merge per self-pass-rate ≤ 70%).
    - .planning/retrospectives/2026-04-21_v61_counter20_retrospective.md
      (NEW): RETRO-V61-002 per RETRO-V61-001 cadence rule #2 (counter
      ≥ 20 → arc-size retro). Covers Phase 7 Sprint 1 full arc
      (DEC-V61-020 → 034), self-pass calibration, Codex ROI.
    
    Integration result: cylinder_wake now PASS 35s with VTK captured,
    contour + residuals rendered. 10/10 cases in Tier C batch have
    real evidence visible on /learn/{case} (modulo RBC still running
    at commit time).
    
    Regression: 139/139 pytest (+7 new visual-only tests).
    v6.1 counter: 19 → 20.
    
    Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>

.planning/decisions/2026-04-21_phase7c_tier_c_visual_only_fanout.md
.planning/retrospectives/2026-04-21_v61_counter20_retrospective.md
reports/phase5_audit/20260421T150705Z_circular_cylinder_wake_raw.json
reports/phase5_fields/circular_cylinder_wake/runs/audit_real_run.json
reports/phase5_renders/circular_cylinder_wake/20260421T150630Z/contour_u_magnitude.png
reports/phase5_renders/circular_cylinder_wake/20260421T150630Z/residuals.png
reports/phase5_renders/circular_cylinder_wake/runs/audit_real_run.json
src/foam_agent_adapter.py
ui/backend/tests/fixtures/runs/circular_cylinder_wake/audit_real_run_measurement.yaml
ui/backend/tests/test_comparison_report_visual_only.py

exec
/bin/zsh -lc 'git show --stat --oneline --no-renames 4ee3fc2 a70796a 02cd686 575db8f' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
4ee3fc2 feat(phase7c): Tier C visual-only fan-out infrastructure (DEC-V61-034)
 .../20260421T081929Z_lid_driven_cavity_raw.json    |  10 +
 .../20260421T082305Z_lid_driven_cavity_raw.json    |  81 +++++
 .../20260421T082408Z_lid_driven_cavity_raw.json    |  81 +++++
 .../20260421T125646Z_backward_facing_step_raw.json |  25 ++
 .../backward_facing_step/runs/audit_real_run.json  |   6 +
 .../20260421T125637Z/contour_u_magnitude.png       | Bin 0 -> 32331 bytes
 .../20260421T125637Z/residuals.png                 | Bin 0 -> 56439 bytes
 .../backward_facing_step/runs/audit_real_run.json  |  11 +
 scripts/phase5_audit_run.py                        |  12 +-
 scripts/render_case_report.py                      | 334 ++++++++++++++++-----
 ui/backend/routes/comparison_report.py             |  44 +++
 ui/backend/services/comparison_report.py           |  92 +++++-
 .../audit_real_run_measurement.yaml                |  11 +-
 .../src/pages/learn/LearnCaseDetailPage.tsx        |  84 +++++-
 14 files changed, 699 insertions(+), 92 deletions(-)
a70796a feat(phase7c): Tier C batch 1 renders — 3 cases real contours
 .../20260421T130909Z_plane_channel_flow_raw.json   |  36 +++++++++++++++++++++
 .../20260421T130945Z_turbulent_flat_plate_raw.json |  21 ++++++++++++
 ...0260421T131015Z_circular_cylinder_wake_raw.json |  14 ++++++++
 .../20260421T131052Z_duct_flow_raw.json            |  24 ++++++++++++++
 .../duct_flow/runs/audit_real_run.json             |   6 ++++
 .../lid_driven_cavity/runs/audit_real_run.json     |   6 ++++
 .../plane_channel_flow/runs/audit_real_run.json    |   6 ++++
 .../turbulent_flat_plate/runs/audit_real_run.json  |   6 ++++
 .../20260421T131015Z/contour_u_magnitude.png       | Bin 0 -> 71708 bytes
 .../duct_flow/20260421T131015Z/residuals.png       | Bin 0 -> 64340 bytes
 .../duct_flow/runs/audit_real_run.json             |  11 +++++++
 .../20260421T082340Z/contour_u_magnitude.png       | Bin 0 -> 156127 bytes
 .../20260421T082340Z/pointwise_deviation.png       | Bin 0 -> 35549 bytes
 .../profile_u_centerline.plotly.json               |   1 +
 .../20260421T082340Z/profile_u_centerline.png      | Bin 0 -> 43949 bytes
 .../20260421T082340Z/residuals.png                 | Bin 0 -> 51616 bytes
 .../lid_driven_cavity/runs/audit_real_run.json     |  14 ++++++++
 .../20260421T130203Z/contour_u_magnitude.png       | Bin 0 -> 47009 bytes
 .../20260421T130203Z/residuals.png                 | Bin 0 -> 52263 bytes
 .../plane_channel_flow/runs/audit_real_run.json    |  11 +++++++
 .../20260421T130909Z/contour_u_magnitude.png       | Bin 0 -> 72041 bytes
 .../20260421T130909Z/residuals.png                 | Bin 0 -> 65076 bytes
 .../turbulent_flat_plate/runs/audit_real_run.json  |  11 +++++++
 .../runs/duct_flow/audit_real_run_measurement.yaml |  11 ++++---
 .../audit_real_run_measurement.yaml                |  11 ++++---
 .../audit_real_run_measurement.yaml                |  11 ++++---
 26 files changed, 188 insertions(+), 12 deletions(-)
02cd686 feat(phase7c): Tier C batch 2 renders (3 cases) + 2D-plane auto-detect
 ...421T142307Z_differential_heated_cavity_raw.json | 183 +++++++++
 .../20260421T142539Z_impinging_jet_raw.json        |  79 ++++
 .../20260421T142559Z_naca0012_airfoil_raw.json     | 453 +++++++++++++++++++++
 .../runs/audit_real_run.json                       |   6 +
 .../impinging_jet/runs/audit_real_run.json         |   6 +
 .../naca0012_airfoil/runs/audit_real_run.json      |   6 +
 .../20260421T131052Z/contour_u_magnitude.png       | Bin 0 -> 157423 bytes
 .../20260421T131052Z/residuals.png                 | Bin 0 -> 51538 bytes
 .../runs/audit_real_run.json                       |  11 +
 .../20260421T142307Z/contour_u_magnitude.png       | Bin 0 -> 148354 bytes
 .../impinging_jet/20260421T142307Z/residuals.png   | Bin 0 -> 74120 bytes
 .../impinging_jet/runs/audit_real_run.json         |  11 +
 .../20260421T142539Z/contour_u_magnitude.png       | Bin 0 -> 78512 bytes
 .../20260421T142539Z/residuals.png                 | Bin 0 -> 68393 bytes
 .../naca0012_airfoil/runs/audit_real_run.json      |  11 +
 scripts/render_case_report.py                      |  57 ++-
 .../audit_real_run_measurement.yaml                |  11 +-
 .../impinging_jet/audit_real_run_measurement.yaml  |  11 +-
 .../audit_real_run_measurement.yaml                |  11 +-
 19 files changed, 833 insertions(+), 23 deletions(-)
575db8f feat(phase7c): close Tier C fan-out + cylinder_wake foamToVTK fix (DEC-V61-034)
 ...2026-04-21_phase7c_tier_c_visual_only_fanout.md | 227 +++++++++++++++++++++
 .../2026-04-21_v61_counter20_retrospective.md      | 130 ++++++++++++
 ...0260421T150705Z_circular_cylinder_wake_raw.json |  14 ++
 .../runs/audit_real_run.json                       |   6 +
 .../20260421T150630Z/contour_u_magnitude.png       | Bin 0 -> 180613 bytes
 .../20260421T150630Z/residuals.png                 | Bin 0 -> 56265 bytes
 .../runs/audit_real_run.json                       |  11 +
 src/foam_agent_adapter.py                          |  19 +-
 .../audit_real_run_measurement.yaml                |  11 +-
 .../tests/test_comparison_report_visual_only.py    | 171 ++++++++++++++++
 10 files changed, 581 insertions(+), 8 deletions(-)

exec
/bin/zsh -lc "nl -ba ui/backend/services/comparison_report.py | sed -n '1,320p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
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
   161	                "brew install pango cairo gdk-pixbuf has been run. "
   162	                f"Underlying: {type(e).__name__}: {str(e)[:120]}"
   163	            ),
   164	        )
   165	    return JSONResponse({
   166	        "case_id": case_id,
   167	        "run_label": run_label,
   168	        "pdf_path": str(pdf_path),
   169	        "html_bytes": len(html),
   170	    })

exec
/bin/zsh -lc "nl -ba src/foam_agent_adapter.py | sed -n '1,260p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
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
    45	# DEC-V61-034 Tier C: gold-overlay MVP cases get the full 8-section report;
    46	# visual-only cases get a reduced 3-section report (Metadata + Contour + Residuals)
    47	# — real OpenFOAM evidence without the per-case gold-overlay plumbing.
    48	# _REPORT_SUPPORTED_CASES is the union; gate membership checks use this.
    49	_GOLD_OVERLAY_CASES = frozenset({"lid_driven_cavity"})
    50	_VISUAL_ONLY_CASES = frozenset({
    51	    "backward_facing_step",
    52	    "plane_channel_flow",
    53	    "turbulent_flat_plate",
    54	    "circular_cylinder_wake",
    55	    "impinging_jet",
    56	    "naca0012_airfoil",
    57	    "rayleigh_benard_convection",
    58	    "differential_heated_cavity",
    59	    "duct_flow",
    60	})
    61	_REPORT_SUPPORTED_CASES = _GOLD_OVERLAY_CASES | _VISUAL_ONLY_CASES
    62	
    63	_env = Environment(
    64	    loader=FileSystemLoader(str(_TEMPLATES)),
    65	    autoescape=select_autoescape(["html", "htm"]),
    66	)
    67	
    68	
    69	class ReportError(Exception):
    70	    """Recoverable — caller should 404 or return partial payload."""
    71	
    72	
    73	# ---------------------------------------------------------------------------
    74	# Data assembly
    75	# ---------------------------------------------------------------------------
    76	
    77	
    78	def _run_manifest_path(case_id: str, run_label: str) -> Path:
    79	    return _FIELDS_ROOT / case_id / "runs" / f"{run_label}.json"
    80	
    81	
    82	def _renders_manifest_path(case_id: str, run_label: str) -> Path:
    83	    return _RENDERS_ROOT / case_id / "runs" / f"{run_label}.json"
    84	
    85	
    86	def _load_run_manifest(case_id: str, run_label: str) -> dict:
    87	    p = _run_manifest_path(case_id, run_label)
    88	    if not p.is_file():
    89	        raise ReportError(f"no run manifest for {case_id}/{run_label}")
    90	    data = json.loads(p.read_text(encoding="utf-8"))
    91	    if not isinstance(data, dict):
    92	        raise ReportError(f"run manifest not an object: {p}")
    93	    return data
    94	
    95	
    96	def _load_renders_manifest(case_id: str, run_label: str) -> Optional[dict]:
    97	    p = _renders_manifest_path(case_id, run_label)
    98	    if not p.is_file():
    99	        return None
   100	    data = json.loads(p.read_text(encoding="utf-8"))
   101	    if not isinstance(data, dict):
   102	        return None
   103	    return data
   104	
   105	
   106	def _validated_timestamp(ts: Any) -> Optional[str]:
   107	    """Codex round 1 HIGH: reject any manifest-supplied timestamp that doesn't
   108	    match the exact YYYYMMDDTHHMMSSZ shape. Blocks '../../outside' etc."""
   109	    if not isinstance(ts, str) or not _TIMESTAMP_RE.match(ts):
   110	        return None
   111	    return ts
   112	
   113	
   114	def _safe_rel_under(candidate: str, root: Path) -> Optional[str]:
   115	    """Return `candidate` if it resolves under `root`, else None.
   116	
   117	    Used to validate manifest-supplied output file paths before they flow
   118	    into template `img src`. Prevents a tampered renders manifest from
   119	    pointing WeasyPrint base_url resolution at arbitrary local files
   120	    (which would then be embedded into PDFs as image data URLs).
   121	    """
   122	    if not isinstance(candidate, str) or not candidate:
   123	        return None
   124	    if candidate.startswith("/") or "\\" in candidate or ".." in candidate.split("/"):
   125	        return None
   126	    try:
   127	        resolved = (_REPO_ROOT / candidate).resolve(strict=False)
   128	        resolved.relative_to(root.resolve())
   129	    except (ValueError, OSError):
   130	        return None
   131	    return candidate
   132	
   133	
   134	def _load_ldc_gold() -> tuple[list[float], list[float], dict]:
   135	    gold_path = _GOLD_ROOT / "lid_driven_cavity.yaml"
   136	    if not gold_path.is_file():
   137	        raise ReportError(f"gold file missing: {gold_path}")
   138	    docs = list(yaml.safe_load_all(gold_path.read_text(encoding="utf-8")))
   139	    u_doc = next(
   140	        (d for d in docs if isinstance(d, dict) and d.get("quantity") == "u_centerline"),
   141	        None,
   142	    )
   143	    if u_doc is None:
   144	        raise ReportError("no u_centerline doc in LDC gold")
   145	    ys: list[float] = []
   146	    us: list[float] = []
   147	    for entry in u_doc.get("reference_values", []):
   148	        if isinstance(entry, dict):
   149	            y = entry.get("y")
   150	            u = entry.get("value") or entry.get("u")
   151	            if y is not None and u is not None:
   152	                ys.append(float(y))
   153	                us.append(float(u))
   154	    return ys, us, u_doc
   155	
   156	
   157	def _load_sample_xy(path: Path) -> tuple[np.ndarray, np.ndarray]:
   158	    rows = []
   159	    for line in path.read_text(encoding="utf-8").splitlines():
   160	        s = line.strip()
   161	        if not s or s.startswith("#"):
   162	            continue
   163	        parts = s.split()
   164	        try:
   165	            rows.append([float(parts[0]), float(parts[1])])
   166	        except (ValueError, IndexError):
   167	            continue
   168	    if not rows:
   169	        raise ReportError(f"empty sample: {path}")
   170	    arr = np.array(rows)
   171	    return arr[:, 0], arr[:, 1]
   172	
   173	
   174	def _latest_sample_iter(artifact_dir: Path) -> Path:
   175	    sample_root = artifact_dir / "sample"
   176	    if not sample_root.is_dir():
   177	        raise ReportError(f"sample/ missing under {artifact_dir}")
   178	    iters = sorted(
   179	        (d for d in sample_root.iterdir() if d.is_dir() and d.name.isdigit()),
   180	        key=lambda d: int(d.name),
   181	    )
   182	    if not iters:
   183	        raise ReportError(f"no sample iter dirs under {sample_root}")
   184	    return iters[-1]
   185	
   186	
   187	def _compute_metrics(
   188	    y_sim: np.ndarray, u_sim: np.ndarray,
   189	    y_gold: list[float], u_gold: list[float],
   190	    tolerance_pct: float,
   191	) -> dict[str, Any]:
   192	    """Compute L2/Linf/RMS + per-point |dev|% + pass count."""
   193	    y_sim_norm = y_sim / max(float(y_sim.max()), 1e-12)
   194	    u_sim_interp = np.interp(np.array(y_gold), y_sim_norm, u_sim)
   195	    u_gold_arr = np.array(u_gold)
   196	    diff = u_sim_interp - u_gold_arr
   197	
   198	    denom = np.where(np.abs(u_gold_arr) < 1e-9, 1e-9, np.abs(u_gold_arr))
   199	    dev_pct = 100.0 * np.abs(diff) / denom
   200	    n_total = len(u_gold_arr)
   201	    n_pass = int((dev_pct < tolerance_pct).sum())
   202	
   203	    return {
   204	        "l2": float(np.sqrt(np.mean(diff ** 2))),
   205	        "linf": float(np.max(np.abs(diff))),
   206	        "rms": float(np.sqrt(np.mean(diff ** 2))),  # alias
   207	        "max_dev_pct": float(dev_pct.max()) if n_total else 0.0,
   208	        "n_pass": n_pass,
   209	        "n_total": n_total,
   210	        "per_point_dev_pct": dev_pct.tolist(),
   211	    }
   212	
   213	
   214	def _parse_residuals_csv(path: Path) -> dict[str, Any]:
   215	    if not path.is_file():
   216	        return {"total_iter": 0, "final_ux": None, "note": None}
   217	    lines = path.read_text(encoding="utf-8").splitlines()
   218	    if len(lines) < 2:
   219	        return {"total_iter": 0, "final_ux": None, "note": None}
   220	    header = [c.strip() for c in lines[0].split(",")]
   221	    last = None
   222	    count = 0
   223	    for ln in lines[1:]:
   224	        parts = [c.strip() for c in ln.split(",")]
   225	        if len(parts) != len(header):
   226	            continue
   227	        last = parts
   228	        count += 1
   229	    final_ux = None
   230	    if last is not None and len(last) > 1 and last[1].upper() != "N/A":
   231	        try:
   232	            final_ux = float(last[1])
   233	        except ValueError:
   234	            pass
   235	    note = None
   236	    if final_ux is not None and final_ux > 1e-3:
   237	        note = (f"注意：Ux 终值 {final_ux:.2e} 大于 1e-3 — "
   238	                f"收敛可能未达稳态。建议增加 endTime 或降低 residualControl。")
   239	    return {"total_iter": count, "final_ux": final_ux, "note": note}
   240	
   241	
   242	def _load_grid_convergence(case_id: str, gold_y: list[float], gold_u: list[float]) -> tuple[list[dict], str]:
   243	    """Read mesh_20/40/80/160_measurement.yaml fixtures, build table rows."""
   244	    rows: list[dict] = []
   245	    # LDC fixtures compare at y≈0.0625 (first gold point >0).
   246	    sample_y = 0.0625
   247	    try:
   248	        sample_gold = next(u for y, u in zip(gold_y, gold_u) if abs(y - sample_y) < 1e-3)
   249	    except StopIteration:
   250	        sample_gold = gold_u[1] if len(gold_u) > 1 else 0.0
   251	
   252	    case_dir = _FIXTURE_ROOT / case_id
   253	    meshes = [("mesh_20", 20), ("mesh_40", 40), ("mesh_80", 80), ("mesh_160", 160)]
   254	    for name, _n in meshes:
   255	        path = case_dir / f"{name}_measurement.yaml"
   256	        if not path.is_file():
   257	            continue
   258	        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
   259	        meas = doc.get("measurement", {}) if isinstance(doc, dict) else {}
   260	        val = meas.get("value")
   261	        if val is None:
   262	            continue
   263	        try:
   264	            val_f = float(val)
   265	        except (ValueError, TypeError):
   266	            continue
   267	        denom = abs(sample_gold) if abs(sample_gold) > 1e-9 else 1e-9
   268	        dev_pct = 100.0 * abs(val_f - sample_gold) / denom
   269	        if dev_pct < 5.0:
   270	            verdict, cls = "PASS", "pass"
   271	        elif dev_pct < 10.0:
   272	            verdict, cls = "WARN", "warn"
   273	        else:
   274	            verdict, cls = "FAIL", "fail"
   275	        rows.append({
   276	            "mesh": name,
   277	            "value": val_f,
   278	            "dev_pct": dev_pct,
   279	            "verdict": verdict,
   280	            "verdict_class": cls,
   281	        })
   282	    if len(rows) < 2:
   283	        return rows, "insufficient mesh data"
   284	    devs = [r["dev_pct"] for r in rows]
   285	    monotone = all(devs[i] >= devs[i + 1] for i in range(len(devs) - 1))
   286	    note = "单调递减 ✓" if monotone else "非严格单调 — 检查 fixture"
   287	    return rows, note
   288	
   289	
   290	def _gci_to_template_dict(gci: Any) -> dict:
   291	    """Flatten a RichardsonGCI dataclass into a JSON-serializable dict for the template."""
   292	    return {
   293	        "coarse_label": gci.coarse.label,
   294	        "coarse_n": gci.coarse.n_cells_1d,
   295	        "coarse_value": gci.coarse.value,
   296	        "medium_label": gci.medium.label,
   297	        "medium_n": gci.medium.n_cells_1d,
   298	        "medium_value": gci.medium.value,
   299	        "fine_label": gci.fine.label,
   300	        "fine_n": gci.fine.n_cells_1d,
   301	        "fine_value": gci.fine.value,
   302	        "r_21": gci.r_21,
   303	        "r_32": gci.r_32,
   304	        "p_obs": gci.p_obs,
   305	        "f_extrapolated": gci.f_extrapolated,
   306	        "gci_21_pct": gci.gci_21 * 100 if gci.gci_21 is not None else None,
   307	        "gci_32_pct": gci.gci_32 * 100 if gci.gci_32 is not None else None,
   308	        "asymptotic_range_ok": gci.asymptotic_range_ok,
   309	        "note": gci.note,
   310	    }
   311	
   312	
   313	def _get_commit_sha() -> str:
   314	    try:
   315	        r = subprocess.run(
   316	            ["git", "rev-parse", "--short", "HEAD"],
   317	            capture_output=True, text=True, cwd=_REPO_ROOT, timeout=5,
   318	        )
   319	        return r.stdout.strip() or "unknown"
   320	    except (subprocess.SubprocessError, OSError):

 succeeded in 0ms:
     1	"""Foam-Agent 调用适配器：MockExecutor（测试）+ FoamAgentExecutor（真实）"""
     2	
     3	from __future__ import annotations
     4	
     5	import io
     6	import math
     7	import os
     8	import re
     9	import shutil
    10	import tarfile
    11	import time
    12	from pathlib import Path
    13	from typing import Any, Dict, List, Optional, Tuple
    14	
    15	from .models import CFDExecutor, ExecutionResult, FlowType, GeometryType, TaskSpec
    16	
    17	# ---------------------------------------------------------------------------
    18	# MockExecutor — unchanged, used for testing
    19	# ---------------------------------------------------------------------------
    20	
    21	
    22	class MockExecutor:
    23	    """测试专用执行器：is_mock=True，返回预设结果"""
    24	
    25	    _PRESET: Dict[str, Dict[str, Any]] = {
    26	        "INTERNAL": {
    27	            "residuals": {"p": 1e-6, "U": 1e-6},
    28	            "key_quantities": {"u_centerline": [0.0, -0.037, 0.025, 0.333, 1.0]},
    29	        },
    30	        "EXTERNAL": {
    31	            "residuals": {"p": 1e-5, "U": 1e-5},
    32	            "key_quantities": {"strouhal_number": 0.165, "cd_mean": 1.36},
    33	        },
    34	        "NATURAL_CONVECTION": {
    35	            "residuals": {"p": 1e-6, "T": 1e-7},
    36	            "key_quantities": {"nusselt_number": 4.52},
    37	        },
    38	    }
    39	
    40	    def execute(self, task_spec: TaskSpec) -> ExecutionResult:
    41	        preset = self._PRESET.get(task_spec.flow_type.value, self._PRESET["INTERNAL"])
    42	        return ExecutionResult(
    43	            success=True,
    44	            is_mock=True,
    45	            residuals=dict(preset["residuals"]),
    46	            key_quantities=dict(preset["key_quantities"]),
    47	            execution_time_s=0.01,
    48	            raw_output_path=None,
    49	        )
    50	
    51	
    52	# ---------------------------------------------------------------------------
    53	# FoamAgentExecutor — real adapter (Docker + OpenFOAM)
    54	# ---------------------------------------------------------------------------
    55	
    56	try:
    57	    import docker
    58	    import docker.errors
    59	    _DOCKER_AVAILABLE = True
    60	except ImportError:
    61	    _DOCKER_AVAILABLE = False
    62	    docker = None  # type: ignore
    63	
    64	
    65	# ---------------------------------------------------------------------------
    66	# Parameter plumbing pre-run assertion (P-B C2)
    67	# ---------------------------------------------------------------------------
    68	# Motivation: knowledge/corrections/ records 12 PARAMETER_PLUMBING_MISMATCH
    69	# events on DHC/Rayleigh-Bénard where solver silently executed at a fallback
    70	# Ra instead of the whitelist-declared Ra, producing Nu values 50-90% off and
    71	# looking indistinguishable from a physics bug in the deviation report.
    72	#
    73	# Rather than trust that task_spec.Ra flows correctly to every downstream
    74	# file (blockMesh, physicalProperties, g, BC files), we parse the generated
    75	# OpenFOAM dict files back from disk and recompute the effective Ra (or Re
    76	# for internal channel flows). If the round-tripped value drifts > 1% from
    77	# what task_spec declares, we raise loudly before burning CPU on a bogus run.
    78	#
    79	# Guards only the two highest-risk case builders: natural-convection cavity
    80	# (where Ra is derived from g, beta, dT, L, nu, Pr — five values that must
    81	# all plumb through) and steady internal channel (where Re → nu via Re=1/nu
    82	# in inlet-U=1 convention). Other builders take Re as a direct velocity
    83	# input and are less prone to silent drift.
    84	
    85	class ParameterPlumbingError(RuntimeError):
    86	    """Case-file round-trip verification failed — a declared parameter did
    87	    not survive the write pipeline. Raised BEFORE solver launch so operators
    88	    debug a 50ms regex failure instead of a 70s-per-step solver run that
    89	    silently hits the wrong operating point.
    90	    """
    91	
    92	
    93	_DICT_SCALAR_RE = re.compile(
    94	    r"^\s*(?P<key>[A-Za-z_][A-Za-z_0-9]*)"
    95	    r"(?:\s+\[[\d\s\-]+\])?"              # optional OpenFOAM dimensions
    96	    r"\s+(?P<value>-?\d+(?:\.\d+)?(?:[eE][\-+]?\d+)?)\s*;",
    97	    re.MULTILINE,
    98	)
    99	
   100	
   101	def _parse_dict_scalar(text: str, key: str) -> Optional[float]:
   102	    """Extract a top-level scalar assignment from an OpenFOAM dict file.
   103	
   104	    Matches both ``Pr 0.71;`` and ``nu [0 2 -1 0 0 0 0] 1e-5;`` forms.
   105	    Returns the numeric value or None if not found.
   106	    """
   107	    for match in _DICT_SCALAR_RE.finditer(text):
   108	        if match.group("key") == key:
   109	            try:
   110	                return float(match.group("value"))
   111	            except ValueError:
   112	                return None
   113	    return None
   114	
   115	
   116	_G_VECTOR_RE = re.compile(
   117	    r"value\s*(?:\[[\d\s\-]+\])?\s*\(\s*"
   118	    r"(-?\d+(?:\.\d+)?(?:[eE][\-+]?\d+)?)\s+"
   119	    r"(-?\d+(?:\.\d+)?(?:[eE][\-+]?\d+)?)\s+"
   120	    r"(-?\d+(?:\.\d+)?(?:[eE][\-+]?\d+)?)"
   121	    r"\s*\)\s*;"
   122	)
   123	
   124	
   125	def _parse_g_magnitude(text: str) -> Optional[float]:
   126	    """Extract |g| from a ``constant/g`` file's ``value (gx gy gz);``."""
   127	    match = _G_VECTOR_RE.search(text)
   128	    if match is None:
   129	        return None
   130	    try:
   131	        gx, gy, gz = (float(match.group(i)) for i in (1, 2, 3))
   132	    except ValueError:
   133	        return None
   134	    return math.sqrt(gx * gx + gy * gy + gz * gz)
   135	
   136	
   137	# ---------------------------------------------------------------------------
   138	# Gold-anchored sampleDict helpers (P-B C3)
   139	# ---------------------------------------------------------------------------
   140	# Motivation: case generators previously emitted `type uniform` sampleDicts
   141	# with arbitrary nPoints. Solver output lands on a regular grid that doesn't
   142	# coincide with `gold_standard.reference_values` coordinates, forcing the
   143	# comparator to interpolate or nearest-neighbor-lookup. This introduces a
   144	# sampling-grid error term indistinguishable from solver error in the final
   145	# verdict.
   146	#
   147	# C3 replaces uniform sampling with explicit `type points` sets anchored to
   148	# the exact coordinates in `knowledge/whitelist.yaml`. Solver samples AT the
   149	# gold points; comparator lookup is exact. Paired with C1 alias layer this
   150	# closes the full sampling-location mismatch channel.
   151	#
   152	# Per docs/c3_sampling_strategy_design.md the roll-out is per-case (LDC /
   153	# NACA / Impinging Jet), each with a different function-object choice based
   154	# on the physical quantity being sampled. These two helpers are the shared
   155	# abstraction used by all three generators.
   156	
   157	
   158	_DEFAULT_WHITELIST_PATH = Path(__file__).resolve().parent.parent / "knowledge" / "whitelist.yaml"
   159	
   160	
   161	def _load_gold_reference_values(
   162	    task_name: str,
   163	    *,
   164	    whitelist_path: Optional[Path] = None,
   165	) -> Optional[List[Dict[str, Any]]]:
   166	    """Load `gold_standard.reference_values` for the named case from whitelist.
   167	
   168	    Matches on either `case.id` or `case.name` (whichever equals task_name).
   169	    Returns None when the whitelist file is missing, unreadable, the case
   170	    isn't present, or reference_values is empty. Callers decide fallback
   171	    behavior — absence is not an error at this layer (many test fixtures
   172	    use synthetic task names not in whitelist).
   173	    """
   174	    import yaml  # local import to avoid module-load cost when unused
   175	
   176	    path = whitelist_path or _DEFAULT_WHITELIST_PATH
   177	    if not path.exists():
   178	        return None
   179	    try:
   180	        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
   181	    except (yaml.YAMLError, OSError):
   182	        return None
   183	
   184	    for case in data.get("cases", []):
   185	        if case.get("id") == task_name or case.get("name") == task_name:
   186	            gold = case.get("gold_standard") or {}
   187	            values = gold.get("reference_values")
   188	            if isinstance(values, list) and values:
   189	                return values
   190	            return None
   191	    return None
   192	
   193	
   194	def _emit_gold_anchored_points_sampledict(
   195	    case_dir: Path,
   196	    set_name: str,
   197	    physical_points: List[Tuple[float, float, float]],
   198	    fields: List[str],
   199	    *,
   200	    axis: str = "xyz",
   201	    header_comment: str = "",
   202	) -> None:
   203	    """Write `system/sampleDict` with a single `type points` set.
   204	
   205	    For C3 gold-anchored sampling: the points passed in should be the exact
   206	    physical-coord locations at which the gold_standard reference_values
   207	    were measured, so solver output lands on the comparison grid without
   208	    any interpolation error.
   209	
   210	    Parameters:
   211	        case_dir: OpenFOAM case directory (system/ must exist)
   212	        set_name: name of the sampling set (e.g., "uCenterline")
   213	        physical_points: list of (x, y, z) tuples in case coordinates
   214	        fields: OpenFOAM field names to sample (e.g., ["U"])
   215	        axis: output-file sort axis — "xyz" (raw order) or "y"/"x"/"z"
   216	        header_comment: optional extra comment line in the dict header
   217	    """
   218	    if not physical_points:
   219	        raise ValueError("physical_points must not be empty")
   220	    points_text = "\n".join(
   221	        f"            ({px:.12g} {py:.12g} {pz:.12g})"
   222	        for (px, py, pz) in physical_points
   223	    )
   224	    fields_text = " ".join(fields)
   225	    extra = f"|  {header_comment}\n" if header_comment else ""
   226	    (case_dir / "system" / "sampleDict").write_text(
   227	        f"""\
   228	/*--------------------------------*- C++ -*---------------------------------*\\
   229	|  sampleDict - gold-anchored point sampling (C3)                          |
   230	{extra}\\*---------------------------------------------------------------------------*/
   231	type            sets;
   232	libs            ("libsampling.so");
   233	
   234	interpolationScheme cellPoint;
   235	
   236	setFormat       raw;
   237	
   238	sets
   239	(
   240	    {set_name}
   241	    {{
   242	        type        points;
   243	        axis        {axis};
   244	        ordered     on;
   245	        points
   246	        (
   247	{points_text}
   248	        );
   249	    }}
   250	);
   251	
   252	fields          ({fields_text});
   253	
   254	// ************************************************************************* //
   255	""",
   256	        encoding="utf-8",
   257	    )
   258	
   259	
   260	# ---------------------------------------------------------------------------

exec
/bin/zsh -lc "nl -ba ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx | sed -n '1,280p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
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

exec
/bin/zsh -lc "nl -ba ui/backend/services/comparison_report.py | sed -n '320,620p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba ui/backend/templates/comparison_report.html.j2 | sed -n '1,260p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx | sed -n '280,760p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   320	    except (subprocess.SubprocessError, OSError):
   321	        return "unknown"
   322	
   323	
   324	# ---------------------------------------------------------------------------
   325	# Public API
   326	# ---------------------------------------------------------------------------
   327	
   328	
   329	def _build_visual_only_context(
   330	    case_id: str, run_label: str, timestamp: str, artifact_dir: Path,
   331	) -> dict:
   332	    """Tier C reduced context (DEC-V61-034): real contour + residuals PNGs from
   333	    the captured OpenFOAM artifacts, no gold overlay / verdict / GCI. The
   334	    frontend + template detect ``visual_only: True`` and suppress the
   335	    gold-dependent sections.
   336	    """
   337	    renders_manifest = _load_renders_manifest(case_id, run_label)
   338	    renders_dir = _RENDERS_ROOT / case_id / timestamp
   339	
   340	    def _rel(key: str, default: str = "") -> str:
   341	        candidate: Optional[str] = None
   342	        if renders_manifest:
   343	            raw = renders_manifest.get("outputs", {}).get(key)
   344	            if isinstance(raw, str):
   345	                validated = _safe_rel_under(raw, _RENDERS_ROOT)
   346	                if validated:
   347	                    candidate = validated
   348	        if candidate is None and default:
   349	            guess = renders_dir / default
   350	            if guess.is_file():
   351	                try:
   352	                    rel = str(guess.resolve().relative_to(_REPO_ROOT.resolve()))
   353	                    if _safe_rel_under(rel, _RENDERS_ROOT):
   354	                        candidate = rel
   355	                except ValueError:
   356	                    pass
   357	        return candidate or ""
   358	
   359	    renders = {
   360	        "contour_png_rel": _rel("contour_u_magnitude_png", "contour_u_magnitude.png"),
   361	        "residuals_png_rel": _rel("residuals_png", "residuals.png"),
   362	    }
   363	
   364	    # Detect solver name from which log.<solver> file exists in artifact dir.
   365	    solver = "unknown"
   366	    for cand in ("simpleFoam", "icoFoam", "pimpleFoam", "buoyantFoam"):
   367	        if (artifact_dir / f"log.{cand}").is_file():
   368	            solver = cand
   369	            break
   370	    commit_sha = _get_commit_sha()
   371	
   372	    return {
   373	        "visual_only": True,
   374	        "case_id": case_id,
   375	        "run_label": run_label,
   376	        "timestamp": timestamp,
   377	        "renders": renders,
   378	        "solver": solver,
   379	        "commit_sha": commit_sha,
   380	        "verdict": None,
   381	        "verdict_gradient": "#64748b 0%, #94a3b8 100%",
   382	        "subtitle": (
   383	            "Visual-only mode (DEC-V61-034 Tier C): real OpenFOAM field + "
   384	            "residual evidence captured; per-case gold-overlay plumbing pending "
   385	            "Phase 7c Sprint 2 (Tier B)."
   386	        ),
   387	        "paper": None,
   388	        "metrics": None,
   389	        "gci": None,
   390	        "grid_convergence": None,
   391	        "deviations": None,
   392	        "residual_info": None,
   393	        "tolerance_percent": None,
   394	    }
   395	
   396	
   397	def build_report_context(case_id: str, run_label: str = "audit_real_run") -> dict:
   398	    """Assemble all template variables. Raises ReportError on missing data."""
   399	    if case_id not in _REPORT_SUPPORTED_CASES:
   400	        raise ReportError(
   401	            f"case_id={case_id!r} not in Phase 7 report scope. "
   402	            f"Supported: {sorted(_REPORT_SUPPORTED_CASES)}."
   403	        )
   404	
   405	    run_manifest = _load_run_manifest(case_id, run_label)
   406	    timestamp = _validated_timestamp(run_manifest.get("timestamp"))
   407	    if timestamp is None:
   408	        raise ReportError(
   409	            f"invalid timestamp in run manifest for {case_id}/{run_label}"
   410	        )
   411	    artifact_dir = _FIELDS_ROOT / case_id / timestamp
   412	    # Containment: must be inside _FIELDS_ROOT/case_id/ even after .resolve().
   413	    try:
   414	        artifact_dir.resolve(strict=True).relative_to(
   415	            (_FIELDS_ROOT / case_id).resolve()
   416	        )
   417	    except (ValueError, OSError, FileNotFoundError):
   418	        raise ReportError(f"artifact dir escapes fields root: {artifact_dir}")
   419	    if not artifact_dir.is_dir():
   420	        raise ReportError(f"artifact dir missing: {artifact_dir}")
   421	
   422	    # Tier C: visual-only cases skip gold-overlay / verdict / GCI assembly.
   423	    if case_id in _VISUAL_ONLY_CASES:
   424	        return _build_visual_only_context(case_id, run_label, timestamp, artifact_dir)
   425	
   426	    # Load + compute
   427	    gold_y, gold_u, gold_doc = _load_ldc_gold()
   428	    tolerance = float(gold_doc.get("tolerance", 0.05)) * 100.0  # fraction → percent
   429	    latest_sample = _latest_sample_iter(artifact_dir)
   430	    y_sim, u_sim = _load_sample_xy(latest_sample / "uCenterline.xy")
   431	    metrics = _compute_metrics(y_sim, u_sim, gold_y, gold_u, tolerance)
   432	
   433	    residual_info = _parse_residuals_csv(artifact_dir / "residuals.csv")
   434	    grid_conv_rows, grid_note = _load_grid_convergence(case_id, gold_y, gold_u)
   435	    # Phase 7d: Richardson extrapolation + GCI over the finest 3 meshes.
   436	    try:
   437	        from ui.backend.services.grid_convergence import compute_gci_from_fixtures
   438	        gci = compute_gci_from_fixtures(case_id, fixture_root=_FIXTURE_ROOT)
   439	    except (ValueError, ImportError, OverflowError, ArithmeticError):
   440	        # Pathological mesh triples can still raise from deep math — the
   441	        # grid_convergence module already catches these internally on the
   442	        # documented branches, but belt-and-suspenders keeps report
   443	        # generation from 500'ing on a numerical corner we did not predict.
   444	        gci = None
   445	
   446	    # Verdict logic: all-pass OR tolerance met.
   447	    is_all_pass = metrics["n_pass"] == metrics["n_total"] and metrics["n_total"] > 0
   448	    majority_pass = metrics["n_pass"] >= math.ceil(metrics["n_total"] * 0.6)
   449	    if is_all_pass:
   450	        verdict, verdict_gradient, subtitle = "PASS", "#059669 0%, #10b981 100%", (
   451	            f"全部 {metrics['n_total']} 个 gold 点在 ±{tolerance:.1f}% 容差内。"
   452	        )
   453	    elif majority_pass:
   454	        verdict, verdict_gradient, subtitle = "PARTIAL", "#d97706 0%, #f59e0b 100%", (
   455	            f"{metrics['n_pass']}/{metrics['n_total']} 点通过；"
   456	            f"{metrics['n_total'] - metrics['n_pass']} 点残差为已记录物理项 "
   457	            f"(见 DEC-V61-030 关于 Ghia 非均匀网格 vs 均匀网格的插值误差)。"
   458	        )
   459	    else:
   460	        verdict, verdict_gradient, subtitle = "FAIL", "#dc2626 0%, #ef4444 100%", (
   461	            f"仅 {metrics['n_pass']}/{metrics['n_total']} 点通过 — "
   462	            f"需要诊断 (solver, mesh, 或 gold 本身)。"
   463	        )
   464	
   465	    # Renders — use Phase 7b manifest if available; else None placeholders.
   466	    # Codex round 1 HIGH: every manifest-supplied output path is validated to
   467	    # resolve inside reports/phase5_renders/ before being emitted into HTML.
   468	    renders_manifest = _load_renders_manifest(case_id, run_label)
   469	    renders_dir = _RENDERS_ROOT / case_id / timestamp
   470	
   471	    def _rel(key: str, default: str = "") -> str:
   472	        candidate: Optional[str] = None
   473	        if renders_manifest:
   474	            raw = renders_manifest.get("outputs", {}).get(key)
   475	            if isinstance(raw, str):
   476	                validated = _safe_rel_under(raw, _RENDERS_ROOT)
   477	                if validated:
   478	                    candidate = validated
   479	        if candidate is None:
   480	            guess = renders_dir / default
   481	            if guess.is_file():
   482	                try:
   483	                    rel = str(guess.resolve().relative_to(_REPO_ROOT.resolve()))
   484	                    if _safe_rel_under(rel, _RENDERS_ROOT):
   485	                        candidate = rel
   486	                except ValueError:
   487	                    pass
   488	        return candidate or ""
   489	
   490	    renders = {
   491	        "profile_png_rel": _rel("profile_png", "profile_u_centerline.png"),
   492	        "pointwise_png_rel": _rel("pointwise_deviation_png", "pointwise_deviation.png"),
   493	        "contour_png_rel": _rel("contour_u_magnitude_png", "contour_u_magnitude.png"),
   494	        "residuals_png_rel": _rel("residuals_png", "residuals.png"),
   495	    }
   496	
   497	    paper = {
   498	        "title": gold_doc.get("source", "Ghia, Ghia & Shin 1982 — Lid-Driven Cavity benchmark"),
   499	        "source": "J. Comput. Phys. 47, 387-411 (1982), Table I Re=100 column",
   500	        "doi": gold_doc.get("literature_doi", "10.1016/0021-9991(82)90058-4"),
   501	        "short": "Ghia 1982",
   502	        "gold_count": metrics["n_total"],
   503	        "tolerance_pct": tolerance,
   504	    }
   505	
   506	    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
   507	
   508	    return {
   509	        "case_id": case_id,
   510	        "case_display_name": "Lid-Driven Cavity (Re=100)" if case_id == "lid_driven_cavity" else case_id,
   511	        "run_label": run_label,
   512	        "timestamp": timestamp,
   513	        "verdict": verdict,
   514	        "verdict_gradient": verdict_gradient,
   515	        "verdict_subtitle": subtitle,
   516	        "metrics": metrics,
   517	        "paper": paper,
   518	        "renders": renders,
   519	        "contour_caption": (
   520	            "2D |U| contour + streamlines 由 OpenFOAM VTK 体数据渲染（Phase 7b polish）。"
   521	            "白色流线显示 LDC Re=100 的主涡结构；黄色高 |U| 区沿 lid 剪切层分布。"
   522	        ),
   523	        "residual_info": residual_info,
   524	        "grid_conv": grid_conv_rows,
   525	        "grid_conv_note": grid_note,
   526	        "gci": _gci_to_template_dict(gci) if gci is not None else None,
   527	        "meta": {
   528	            "openfoam_version": "v10",
   529	            "solver": "simpleFoam (SIMPLE, laminar)",
   530	            "docker_image": "cfd-openfoam (local arm64 OpenFOAM v10)",
   531	            "commit_sha": _get_commit_sha(),
   532	            "mesh": "129×129 uniform",
   533	            "tolerance": f"±{tolerance:.1f}%",
   534	            "schemes": "steadyState + linearUpwind + Gauss linear corrected",
   535	            "report_generated_at": now,
   536	        },
   537	    }
   538	
   539	
   540	def render_report_html(case_id: str, run_label: str = "audit_real_run") -> str:
   541	    """Return the full HTML string for the comparison report."""
   542	    ctx = build_report_context(case_id, run_label)
   543	    tmpl = _env.get_template("comparison_report.html.j2")
   544	    return tmpl.render(**ctx)
   545	
   546	
   547	def render_report_pdf(case_id: str, run_label: str = "audit_real_run",
   548	                      output_path: Optional[Path] = None) -> Path:
   549	    """Render HTML to PDF via WeasyPrint and write to disk. Returns the file Path.
   550	
   551	    Asset resolution: WeasyPrint converts the HTML's relative img src paths.
   552	    We pass base_url=_REPO_ROOT so /reports/phase5_renders/... resolves correctly.
   553	
   554	    Codex round 2 (2026-04-21): containment check runs BEFORE weasyprint import
   555	    so ReportError from a malicious output_path is raised regardless of whether
   556	    native libs are installed. Native load failures (libgobject etc.) surface
   557	    as OSError and are mapped by the route layer to 503, same as ImportError.
   558	    """
   559	    # Codex round 1 HIGH: ensure PDF always lands under reports/phase5_reports/.
   560	    # Codex round 2 MED: run containment FIRST, before WeasyPrint import so we
   561	    # fail-closed on traversal even on systems where WeasyPrint native libs are
   562	    # unavailable.
   563	    reports_root = (_REPO_ROOT / "reports" / "phase5_reports").resolve()
   564	    if output_path is None:
   565	        ctx = build_report_context(case_id, run_label)
   566	        ts = ctx["timestamp"]  # already validated by build_report_context
   567	        out_dir = reports_root / case_id / ts
   568	        out_dir.mkdir(parents=True, exist_ok=True)
   569	        output_path = out_dir / f"{run_label}_comparison_report.pdf"
   570	    try:
   571	        resolved_out = output_path.resolve(strict=False)
   572	        # Must stay inside reports/phase5_reports/
   573	        resolved_out.relative_to(reports_root)
   574	    except (ValueError, OSError):
   575	        raise ReportError(f"PDF output path escapes reports_root: {output_path}")
   576	
   577	    # Import weasyprint lazily — heavy import, only when PDF actually needed.
   578	    import weasyprint  # type: ignore  # ImportError → 503 via route layer.
   579	
   580	    html = render_report_html(case_id, run_label)
   581	    doc = weasyprint.HTML(string=html, base_url=str(_REPO_ROOT))
   582	    doc.write_pdf(str(resolved_out))
   583	    return resolved_out

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
   140	  单调收敛: {{ grid_conv_note }}
   141	</p>
   142	
   143	{% if gci %}
   144	<h3 style="font-size:1.05em; margin-top:1.2em; color:#374151;">Richardson extrapolation + GCI (Celik 2008, Roache 1994)</h3>
   145	<table>
   146	  <tbody>
   147	    <tr><th>3-grid input</th><td class="mono">
   148	      {{ gci.coarse_label }} (N={{ gci.coarse_n }}) = {{ '%.4f'|format(gci.coarse_value) }},
   149	      {{ gci.medium_label }} (N={{ gci.medium_n }}) = {{ '%.4f'|format(gci.medium_value) }},
   150	      {{ gci.fine_label }} (N={{ gci.fine_n }}) = {{ '%.4f'|format(gci.fine_value) }}
   151	    </td></tr>
   152	    <tr><th>Refinement ratios</th><td class="mono">r₂₁ = {{ '%.3f'|format(gci.r_21) }}, r₃₂ = {{ '%.3f'|format(gci.r_32) }}</td></tr>
   153	    <tr><th>Observed order p_obs</th><td class="mono">
   154	      {% if gci.p_obs is not none %}{{ '%.4f'|format(gci.p_obs) }}{% else %}undefined ({{ gci.note }}){% endif %}
   155	    </td></tr>
   156	    <tr><th>Richardson f_h→0</th><td class="mono">
   157	      {% if gci.f_extrapolated is not none %}{{ '%.6f'|format(gci.f_extrapolated) }}{% else %}n/a{% endif %}
   158	    </td></tr>
   159	    <tr><th>GCI₂₁ (coarse→medium)</th><td class="mono">
   160	      {% if gci.gci_21_pct is not none %}{{ '%.3f'|format(gci.gci_21_pct) }}%{% else %}n/a{% endif %}
   161	    </td></tr>
   162	    <tr><th>GCI₃₂ (medium→fine)</th><td class="mono">
   163	      {% if gci.gci_32_pct is not none %}<strong>{{ '%.3f'|format(gci.gci_32_pct) }}%</strong>{% else %}n/a{% endif %}
   164	      <span style="color:#6b7280; margin-left:0.5em; font-size:0.85em;">
   165	        ← 最细网格解的数值不确定度带
   166	      </span>
   167	    </td></tr>
   168	    <tr><th>Asymptotic range</th><td>
   169	      {% if gci.asymptotic_range_ok %}
   170	        <span style="color:#059669; font-weight:600;">✓ within asymptotic range</span>
   171	      {% elif gci.asymptotic_range_ok is false %}
   172	        <span style="color:#d97706;">⚠ not yet asymptotic — {{ gci.note }}</span>
   173	      {% else %}
   174	        <span style="color:#9ca3af;">n/a</span>
   175	      {% endif %}
   176	    </td></tr>
   177	  </tbody>
   178	</table>
   179	<p style="color:#6b7280; font-size:0.82em; margin-top:0.4em; font-style:italic;">
   180	  Fs=1.25 (3-grid safety factor). Reference: Celik et al. 2008 "Procedure for
   181	  Estimation and Reporting of Uncertainty Due to Discretization in CFD Applications",
   182	  J. Fluids Eng. 130(7), ASME V&V 20 standard.
   183	</p>
   184	{% endif %}
   185	{% else %}
   186	<p style="color:#9ca3af; font-style:italic;">网格收敛数据暂未加载。</p>
   187	{% endif %}
   188	
   189	<!-- Section 8 — Solver metadata -->
   190	<h2>8. 求解器元数据</h2>
   191	<table>
   192	  <tbody>
   193	    <tr><th>OpenFOAM</th><td class="mono">{{ meta.openfoam_version }}</td></tr>
   194	    <tr><th>Solver</th><td class="mono">{{ meta.solver }}</td></tr>
   195	    <tr><th>Docker image</th><td class="mono">{{ meta.docker_image }}</td></tr>
   196	    <tr><th>Commit SHA</th><td class="mono">{{ meta.commit_sha }}</td></tr>
   197	    <tr><th>Mesh</th><td class="mono">{{ meta.mesh }}</td></tr>
   198	    <tr><th>Tolerance</th><td class="mono">{{ meta.tolerance }}</td></tr>
   199	    <tr><th>Schemes</th><td class="mono">{{ meta.schemes }}</td></tr>
   200	    <tr><th>Report generated</th><td class="mono">{{ meta.report_generated_at }}</td></tr>
   201	  </tbody>
   202	</table>
   203	
   204	<footer>
   205	  Report generated by Phase 7c comparison_report pipeline (DEC-V61-032, {{ meta.report_generated_at[:10] }}).
   206	  CFD harness unified · cfd-harness-unified @ <span class="mono">{{ meta.commit_sha }}</span>
   207	</footer>
   208	
   209	</body>
   210	</html>

 succeeded in 0ms:
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
   321	          {learnCase.physics_bullets_zh.map((b, i) => (
   322	            <li key={i} className="flex gap-3">
   323	              <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-sky-400" aria-hidden />
   324	              <span>{b}</span>
   325	            </li>
   326	          ))}
   327	        </ul>
   328	      </section>
   329	
   330	      {flowFields.length > 0 && (
   331	        <section>
   332	          <div className="mb-3 flex items-baseline justify-between">
   333	            <h2 className="card-title">真实数据 · Data</h2>
   334	            <p className="text-[11px] text-surface-500">
   335	              每张图都直接来自文献精确解或公开实验表格
   336	            </p>
   337	          </div>
   338	          <div className="space-y-4">
   339	            {flowFields.map((ff) => (
   340	              <figure
   341	                key={ff.src}
   342	                className="overflow-hidden rounded-md border border-surface-800 bg-surface-900/30"
   343	              >
   344	                <img
   345	                  src={ff.src}
   346	                  alt={ff.caption_zh}
   347	                  className="w-full max-w-full"
   348	                  loading="lazy"
   349	                />
   350	                <figcaption className="border-t border-surface-800 px-4 py-3">
   351	                  <p className="text-[13px] text-surface-200">{ff.caption_zh}</p>
   352	                  <p className="mono mt-1.5 text-[10px] leading-relaxed text-surface-500">
   353	                    provenance: {ff.provenance}
   354	                  </p>
   355	                </figcaption>
   356	              </figure>
   357	            ))}
   358	          </div>
   359	        </section>
   360	      )}
   361	
   362	      {/* Phase 7f — live CFD-vs-Gold comparison report (if the case has a real
   363	          audit_real_run artifact set from Phase 7a). Gracefully hidden for
   364	          cases not yet opted-in. */}
   365	      <ScientificComparisonReportSection caseId={caseId} />
   366	
   367	      <section>
   368	        <h2 className="card-title mb-3">为什么要做验证</h2>
   369	        <p className="text-[14px] leading-relaxed text-surface-200">
   370	          {learnCase.why_validation_matters_zh}
   371	        </p>
   372	      </section>
   373	
   374	      <section>
   375	        <h2 className="card-title mb-3 text-amber-300">常见陷阱</h2>
   376	        <div className="rounded-md border border-amber-900/40 bg-amber-950/20 px-4 py-3">
   377	          <p className="text-[14px] leading-relaxed text-amber-100/85">
   378	            {learnCase.common_pitfall_zh}
   379	          </p>
   380	        </div>
   381	      </section>
   382	
   383	      <section>
   384	        <h2 className="card-title mb-3">可观察量</h2>
   385	        <div className="inline-flex items-center gap-2 rounded-md border border-surface-800 bg-surface-900/50 px-3 py-2">
   386	          <span className="text-[11px] uppercase tracking-wider text-surface-500">
   387	            canonical observable
   388	          </span>
   389	          <span className="mono text-[13px] text-surface-100">{learnCase.observable}</span>
   390	        </div>
   391	      </section>
   392	
   393	      <section>
   394	        <h2 className="card-title mb-3">参考文献</h2>
   395	        <p className="mono text-[13px] text-surface-300">{learnCase.canonical_ref}</p>
   396	      </section>
   397	    </div>
   398	  );
   399	}
   400	
   401	// --- Compare tab --------------------------------------------------------------
   402	
   403	const RUN_CATEGORY_LABEL: Record<RunCategory, string> = {
   404	  reference: "参考运行",
   405	  real_incident: "真实故障",
   406	  under_resolved: "欠分辨",
   407	  wrong_model: "错模型",
   408	  grid_convergence: "网格收敛",
   409	};
   410	
   411	const RUN_CATEGORY_COLOR: Record<RunCategory, string> = {
   412	  reference: "bg-emerald-900/40 text-emerald-200 border-emerald-800/60",
   413	  real_incident: "bg-amber-900/30 text-amber-200 border-amber-800/50",
   414	  under_resolved: "bg-orange-900/30 text-orange-200 border-orange-800/50",
   415	  wrong_model: "bg-rose-900/30 text-rose-200 border-rose-800/50",
   416	  grid_convergence: "bg-sky-900/30 text-sky-200 border-sky-800/50",
   417	};
   418	
   419	function CompareTab({
   420	  caseId,
   421	  report,
   422	  error,
   423	  runs,
   424	  activeRunId,
   425	  onSelectRun,
   426	}: {
   427	  caseId: string;
   428	  report: ValidationReport | undefined;
   429	  error: ApiError | null;
   430	  runs: RunDescriptor[];
   431	  activeRunId: string | undefined;
   432	  onSelectRun: (runId: string | null) => void;
   433	}) {
   434	  const learnCase = getLearnCase(caseId)!;
   435	
   436	  if (error) {
   437	    return (
   438	      <ErrorCallout
   439	        message={`后端没有为 ${caseId} 返回验证报告 (${error.status})`}
   440	      />
   441	    );
   442	  }
   443	  if (!report) {
   444	    return <SkeletonCallout message="正在从后端取回验证报告…" />;
   445	  }
   446	
   447	  const { gold_standard, measurement, contract_status, deviation_pct, tolerance_lower, tolerance_upper } = report;
   448	
   449	  // Which run is currently shown. If `activeRunId` is not set, the
   450	  // backend resolved the default (first reference run, then fallback).
   451	  // Highlight whichever run actually matches the loaded measurement.
   452	  const resolvedRun = runs.find((r) => r.run_id === measurement?.run_id)
   453	    ?? runs.find((r) => activeRunId ? r.run_id === activeRunId : r.category === "reference")
   454	    ?? runs[0];
   455	
   456	  return (
   457	    <div className="space-y-6">
   458	      {/* Run selector — only rendered when the case has curated runs */}
   459	      {runs.length > 0 && (
   460	        <section className="rounded-lg border border-surface-800 bg-surface-900/30 px-4 py-3">
   461	          <div className="mb-2 flex items-baseline justify-between">
   462	            <p className="text-[11px] uppercase tracking-[0.14em] text-surface-500">
   463	              选择一条 run
   464	            </p>
   465	            <p className="text-[11px] text-surface-500">
   466	              换一条运行 → 验证结果会不同 · 这就是"做对"和"数字碰巧对上"的区别
   467	            </p>
   468	          </div>
   469	          <div className="flex flex-wrap gap-2">
   470	            {runs.map((run) => {
   471	              const isActive =
   472	                (resolvedRun && resolvedRun.run_id === run.run_id) ||
   473	                activeRunId === run.run_id;
   474	              return (
   475	                <button
   476	                  key={run.run_id}
   477	                  onClick={() => onSelectRun(run.run_id)}
   478	                  className={`rounded-md border px-3 py-1.5 text-left text-[12px] transition-colors ${
   479	                    isActive
   480	                      ? "border-sky-500 bg-sky-950/40 text-surface-100"
   481	                      : "border-surface-700 bg-surface-900/40 text-surface-300 hover:border-surface-600"
   482	                  }`}
   483	                >
   484	                  <div className="flex items-center gap-2">
   485	                    <span
   486	                      className={`inline-flex rounded-sm border px-1.5 py-0.5 text-[10px] uppercase tracking-wider ${RUN_CATEGORY_COLOR[run.category]}`}
   487	                    >
   488	                      {RUN_CATEGORY_LABEL[run.category]}
   489	                    </span>
   490	                    <span className="font-medium">{run.label_zh}</span>
   491	                  </div>
   492	                  <p className="mono mt-0.5 text-[10px] text-surface-500">
   493	                    run_id={run.run_id} · 预期={run.expected_verdict}
   494	                  </p>
   495	                </button>
   496	              );
   497	            })}
   498	          </div>
   499	          {resolvedRun?.description_zh && (
   500	            <p className="mt-3 text-[12px] leading-relaxed text-surface-400">
   501	              {resolvedRun.description_zh}
   502	            </p>
   503	          )}
   504	        </section>
   505	      )}
   506	
   507	      {/* Verdict line */}
   508	      <section className="rounded-lg border border-surface-800 bg-surface-900/40 px-5 py-4">
   509	        <div className="flex items-baseline justify-between">
   510	          <p className="text-[11px] uppercase tracking-[0.14em] text-surface-500">结果</p>
   511	          <span className={`mono text-[12px] ${STATUS_CLASS[contract_status]}`}>
   512	            {contract_status}
   513	          </span>
   514	        </div>
   515	        <p className={`mt-1 text-[18px] font-medium ${STATUS_CLASS[contract_status]}`}>
   516	          {STATUS_TEXT[contract_status]}
   517	        </p>
   518	      </section>
   519	
   520	      {/* Gold vs measured */}
   521	      <section className="grid gap-4 md:grid-cols-2">
   522	        <StatBlock
   523	          label="黄金标准"
   524	          subLabel={gold_standard.citation}
   525	          value={gold_standard.ref_value}
   526	          unit={gold_standard.unit}
   527	          quantity={gold_standard.quantity}
   528	        />
   529	        <StatBlock
   530	          label="你的测量"
   531	          subLabel={measurement?.source ?? "—"}
   532	          value={measurement?.value ?? null}
   533	          unit={measurement?.unit ?? gold_standard.unit}
   534	          quantity={gold_standard.quantity}
   535	          accent
   536	        />
   537	      </section>
   538	
   539	      {/* Tolerance band */}
   540	      <section>
   541	        <h3 className="card-title mb-2">容差带</h3>
   542	        <ToleranceBand
   543	          goldValue={gold_standard.ref_value}
   544	          tolerancePct={gold_standard.tolerance_pct}
   545	          lower={tolerance_lower}
   546	          upper={tolerance_upper}
   547	          measured={measurement?.value ?? null}
   548	        />
   549	        {deviation_pct !== null && (
   550	          <p className="mt-3 text-[13px] text-surface-300">
   551	            偏差 <span className={`mono ${STATUS_CLASS[contract_status]}`}>
   552	              {deviation_pct > 0 ? "+" : ""}
   553	              {deviation_pct.toFixed(2)}%
   554	            </span>{" "}
   555	            · 容差宽度 ±{(gold_standard.tolerance_pct * 100).toFixed(1)}%
   556	          </p>
   557	        )}
   558	      </section>
   559	
   560	      {/* Learning angle — reframe FAIL/HAZARD as a teaching moment */}
   561	      <section className="rounded-md border border-sky-900/40 bg-sky-950/15 px-4 py-3">
   562	        <p className="mb-1 text-[11px] uppercase tracking-[0.14em] text-sky-300">
   563	          学习点 · Learning angle
   564	        </p>
   565	        <p className="text-[14px] leading-relaxed text-surface-200">
   566	          {learnCase.why_validation_matters_zh}
   567	        </p>
   568	      </section>
   569	    </div>
   570	  );
   571	}
   572	
   573	function StatBlock({
   574	  label,
   575	  subLabel,
   576	  value,
   577	  unit,
   578	  quantity,
   579	  accent,
   580	}: {
   581	  label: string;
   582	  subLabel: string;
   583	  value: number | null;
   584	  unit: string;
   585	  quantity: string;
   586	  accent?: boolean;
   587	}) {
   588	  return (
   589	    <div
   590	      className={`rounded-lg border px-5 py-4 ${
   591	        accent ? "border-sky-800/60 bg-sky-950/20" : "border-surface-800 bg-surface-900/40"
   592	      }`}
   593	    >
   594	      <p className="text-[11px] uppercase tracking-[0.14em] text-surface-500">{label}</p>
   595	      <p className="mono mt-3 text-[28px] font-medium leading-none text-surface-100">
   596	        {value === null ? "—" : value.toPrecision(4)}
   597	      </p>
   598	      <div className="mt-3 flex items-baseline justify-between text-[12px] text-surface-400">
   599	        <span className="mono">{quantity}</span>
   600	        <span>{unit || "—"}</span>
   601	      </div>
   602	      <p className="mt-2 text-[11px] leading-snug text-surface-500">{subLabel}</p>
   603	    </div>
   604	  );
   605	}
   606	
   607	function ToleranceBand({
   608	  goldValue,
   609	  lower,
   610	  upper,
   611	  measured,
   612	}: {
   613	  goldValue: number;
   614	  tolerancePct: number;
   615	  lower: number;
   616	  upper: number;
   617	  measured: number | null;
   618	}) {
   619	  // Compute a display range that includes gold, both tolerance bounds,
   620	  // and measured — with sensible margin. Clamp width to avoid division
   621	  // by zero for PASS cases where measured ≈ gold.
   622	  const values = [lower, upper, goldValue, measured].filter(
   623	    (v): v is number => v !== null && Number.isFinite(v),
   624	  );
   625	  const rawMin = Math.min(...values);
   626	  const rawMax = Math.max(...values);
   627	  const span = Math.max(rawMax - rawMin, Math.abs(goldValue) * 0.3, 0.01);
   628	  const padding = span * 0.2;
   629	  const displayMin = rawMin - padding;
   630	  const displayMax = rawMax + padding;
   631	  const toPct = (v: number) =>
   632	    ((v - displayMin) / (displayMax - displayMin)) * 100;
   633	
   634	  const goldX = toPct(goldValue);
   635	  const lowerX = toPct(lower);
   636	  const upperX = toPct(upper);
   637	  const measuredX = measured !== null ? toPct(measured) : null;
   638	  const measuredInside = measured !== null && measured >= lower && measured <= upper;
   639	
   640	  return (
   641	    <div className="relative mt-1">
   642	      {/* Track */}
   643	      <div className="relative h-2 rounded-full bg-surface-800">
   644	        {/* Tolerance band shading */}
   645	        <div
   646	          className="absolute top-0 h-2 rounded-full bg-sky-600/30"
   647	          style={{ left: `${lowerX}%`, width: `${upperX - lowerX}%` }}
   648	        />
   649	      </div>
   650	      {/* Gold marker */}
   651	      <div
   652	        className="absolute -top-1 flex h-4 -translate-x-1/2 flex-col items-center"
   653	        style={{ left: `${goldX}%` }}
   654	      >
   655	        <div className="h-4 w-px bg-surface-300" />
   656	      </div>
   657	      <div
   658	        className="absolute top-5 -translate-x-1/2 mono text-[10px] text-surface-400"
   659	        style={{ left: `${goldX}%` }}
   660	      >
   661	        gold
   662	      </div>
   663	      {/* Measurement marker (only if present) */}
   664	      {measuredX !== null && (
   665	        <>
   666	          <div
   667	            className="absolute -top-2 h-6 w-0.5 -translate-x-1/2 rounded-full"
   668	            style={{
   669	              left: `${Math.max(0, Math.min(100, measuredX))}%`,
   670	              background: measuredInside ? "#4ade80" : "#f87171",
   671	            }}
   672	          />
   673	          <div
   674	            className="absolute top-5 -translate-x-1/2 mono text-[10px]"
   675	            style={{
   676	              left: `${Math.max(0, Math.min(100, measuredX))}%`,
   677	              color: measuredInside ? "#4ade80" : "#f87171",
   678	            }}
   679	          >
   680	            measured
   681	          </div>
   682	        </>
   683	      )}
   684	      {/* Out-of-range indicator */}
   685	      {measuredX !== null && (measuredX < 0 || measuredX > 100) && (
   686	        <div
   687	          className={`absolute -top-3 mono text-[10px] ${measuredX < 0 ? "left-0" : "right-0"} text-contract-fail`}
   688	        >
   689	          {measuredX < 0 ? "← 远低于" : "远高于 →"}
   690	        </div>
   691	      )}
   692	    </div>
   693	  );
   694	}
   695	
   696	// --- Mesh tab (interactive grid-convergence slider) --------------------------
   697	
   698	function MeshTab({ caseId }: { caseId: string }) {
   699	  const sweep = GRID_CONVERGENCE_CASES[caseId];
   700	
   701	  // Unconditionally create state + queries so the hook call count stays
   702	  // stable regardless of whether this case has a sweep. (React will
   703	  // throw if hook count varies between renders.)
   704	  const densities = sweep?.densities ?? [];
   705	  const [idx, setIdx] = useState(densities.length > 1 ? 2 : 0);
   706	
   707	  const reports = useQueries({
   708	    queries: densities.map((d) => ({
   709	      queryKey: ["validation-report", caseId, d.id],
   710	      queryFn: () => api.getValidationReport(caseId, d.id),
   711	      enabled: !!caseId,
   712	      retry: false,
   713	      staleTime: 60_000,
   714	    })),
   715	  });
   716	
   717	  if (!sweep) {
   718	    return (
   719	      <div className="rounded-md border border-surface-800 bg-surface-900/40 p-6">
   720	        <p className="card-title mb-2">网格收敛演示尚未为此案例准备</p>
   721	        <p className="text-[13px] leading-relaxed text-surface-400">
   722	          这个案例目前只有一套默认网格的 fixture。目前有网格收敛 sweep 的案例：
   723	          <span className="mono ml-1 text-surface-300">
   724	            {Object.keys(GRID_CONVERGENCE_CASES).join(" · ")}
   725	          </span>
   726	        </p>
   727	      </div>
   728	    );
   729	  }
   730	
   731	  const active = reports[idx];
   732	  const activeReport = active?.data as ValidationReport | undefined;
   733	  const activeDensity = densities[idx];
   734	  const loading = reports.some((r) => r.isLoading);
   735	
   736	  // Map each density to its (value, verdict) — used for the sparkline.
   737	  const series = reports.map((r, i) => {
   738	    const rep = r.data as ValidationReport | undefined;
   739	    return {
   740	      idx: i,
   741	      label: densities[i].label,
   742	      value: rep?.measurement?.value,
   743	      status: rep?.contract_status ?? "UNKNOWN",
   744	    };
   745	  });
   746	
   747	  const goldRef = activeReport?.gold_standard?.ref_value;
   748	  const tol = activeReport?.gold_standard?.tolerance_pct;
   749	  const unit = activeReport?.gold_standard?.unit ?? "";
   750	
   751	  return (
   752	    <div className="space-y-6">
   753	      <section className="rounded-md border border-surface-800 bg-surface-900/40 p-6">
   754	        <div className="mb-4 flex items-baseline justify-between">
   755	          <div>
   756	            <h2 className="card-title">网格收敛演示 · Grid Convergence</h2>
   757	            <p className="mt-1 text-[12px] text-surface-500">
   758	              拖动滑块，实时看 {activeReport?.gold_standard?.quantity ?? "key quantity"} 如何随网格密度逼近 gold 值。
   759	            </p>
   760	          </div>

exec
/bin/zsh -lc 'rg -n "_capture_field_artifacts|foamToVTK|_parse_writeobjects_fields|_compute_key_quantities|key_quantities|strouhal|lift|faceZone|faceZones|force|coefficient|writeObjects" src/foam_agent_adapter.py' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
28:            "key_quantities": {"u_centerline": [0.0, -0.037, 0.025, 0.333, 1.0]},
32:            "key_quantities": {"strouhal_number": 0.165, "cd_mean": 1.36},
36:            "key_quantities": {"nusselt_number": 4.52},
46:            key_quantities=dict(preset["key_quantities"]),
273:# comparator keys (u_centerline / pressure_coefficient / nusselt_number)
587:            # writeObjects: 写出 U/p/phi 等场文件
591:                "postProcess -funcs '(writeObjects writeCellCentres)' -latestTime", case_cont_dir, 120,
612:                self._capture_field_artifacts(
622:            residuals, key_quantities = self._parse_solver_log(log_path, solver_name, task_spec)
624:            # 9. 从 writeObjects 输出的场文件提取 case-specific 关键物理量
625:            key_quantities = self._parse_writeobjects_fields(
626:                log_path.parent, solver_name, task_spec, key_quantities
634:                key_quantities=key_quantities,
4301:        # system/topoSetDict -- cylinder cellZone via cylinderToCell + faceZone for createBaffles
4389:        type    faceZoneSet;
4406:        # system/createBafflesDict -- converts internal faceZone to wall patch "cylinder"
4432:        type faceZone;
4977:        # Gravity = 0 (forced convection impinging jet, buoyancy negligible)
5128:        # Zero gravity (forced convection - buoyancy negligible compared to inertia)
6207:        # beta_star (0.09) is a closure coefficient, NOT the omega denominator constant.
6829:        """从容器内复制 postProcess -func writeObjects 输出的场文件到宿主机。
6879:    def _capture_field_artifacts(
6890:        Mirrors _copy_postprocess_fields. Runs foamToVTK inside the container,
6908:            # (a) foamToVTK — -allPatches merges patches into a single file.
6910:            #     createBaffles which leaves a cylinderBaffleZone faceZone; OF10
6911:            #     foamToVTK SEGVs when interpolating surfScalarField phi onto
6912:            #     the post-baffle faceZone (flux pointer inconsistent with
6914:            #     skips the faceZone write, which is not required downstream
6916:            #     No-op for the 9 cases that don't use faceZones.
6920:                "foamToVTK -latestTime -noZero -allPatches -noFaceZones",
6929:                    f"[WARN] foamToVTK -allPatches failed, retrying without: {log[-400:]}",
6933:                    "foamToVTK -latestTime -noZero -noFaceZones", case_cont_dir, 120,
6937:                    f"[WARN] foamToVTK failed, field capture skipped: {log[-400:]}",
6997:                f"[WARN] _capture_field_artifacts failed: {e!r}", file=_sys.stderr,
7042:            (residuals, key_quantities)
7050:        key_quantities: Dict[str, Any] = {}
7065:            # 从最终迭代提取速度分量残差用于 key_quantities
7075:                key_quantities["U_residual_magnitude"] = (ux_res ** 2 + uy_res ** 2) ** 0.5
7096:                key_quantities["U_max_approx"] = max(ux_res, abs(uy_res))
7142:                                    key_quantities[set_name] = vals
7144:                                    key_quantities[f"{set_name}_y"] = y_coords
7146:                                    key_quantities[f"{set_name}_x"] = x_coords
7165:                                    key_quantities[set_name] = vals
7166:                                    key_quantities[f"{set_name}_y"] = y_coords
7175:                if "uCenterline" in key_quantities:
7176:                    key_quantities["u_centerline"] = key_quantities["uCenterline"]
7177:                    del key_quantities["uCenterline"]
7178:                    if "uCenterline_y" in key_quantities:
7179:                        key_quantities["u_centerline_y"] = key_quantities["uCenterline_y"]
7180:                        del key_quantities["uCenterline_y"]
7184:                if "wallProfile" in key_quantities:
7185:                    x_coords = key_quantities.get("wallProfile_x", [])
7186:                    ux_vals = key_quantities.get("wallProfile", [])
7205:                            key_quantities["reattachment_length"] = reattachment_x / H
7207:                            key_quantities["reattachment_detection_upstream_artifact"] = True
7208:                            key_quantities["reattachment_detection_rejected_x"] = reattachment_x
7210:                    for k in list(key_quantities.keys()):
7212:                            del key_quantities[k]
7216:                if "midPlaneT" in key_quantities:
7217:                    T_vals = key_quantities.get("midPlaneT", [])
7218:                    y_coords = key_quantities.get("midPlaneT_y", [])
7232:                                key_quantities["nusselt_number"] = grad_T * L / dT_bulk
7234:                    for k in list(key_quantities.keys()):
7236:                            del key_quantities[k]
7238:        return residuals, key_quantities
7241:    # writeObjects field extraction
7244:    def _parse_writeobjects_fields(
7249:        key_quantities: Dict[str, Any],
7251:        """从 postProcess writeObjects 输出的场文件提取 case-specific 关键物理量。
7253:        postProcess -func writeObjects -latestTime 在最新时间目录写出:
7260:            key_quantities updated with u_centerline, reattachment_length, nusselt_number
7263:            return key_quantities
7275:            return key_quantities
7284:            return key_quantities
7294:            return key_quantities
7304:            key_quantities = self._extract_ldc_centerline(
7305:                cxs, cys, u_vecs, task_spec, key_quantities
7310:            key_quantities = self._extract_bfs_reattachment(
7311:                cxs, cys, u_vecs, task_spec, key_quantities
7320:                key_quantities = self._extract_nc_nusselt(
7321:                    cxs, cys, t_vals, task_spec, key_quantities
7326:            key_quantities = self._extract_plane_channel_profile(
7327:                cxs, cys, u_vecs, task_spec, key_quantities
7330:        # Circular Cylinder Wake: BODY_IN_CHANNEL + EXTERNAL -> strouhal_number
7335:                key_quantities = self._extract_cylinder_strouhal(
7336:                    cxs, cys, p_vals, task_spec, key_quantities
7362:            key_quantities["duct_flow_extractor_pending"] = True
7365:                key_quantities["duct_flow_hydraulic_diameter"] = hd
7371:                key_quantities["duct_flow_hydraulic_diameter_missing"] = True
7377:            key_quantities = self._extract_flat_plate_cf(
7378:                cxs, cys, u_vecs, task_spec, key_quantities
7386:                key_quantities = self._extract_jet_nusselt(
7387:                    cxs, cys, t_vals, task_spec, key_quantities
7390:        # Airfoil: AIRFOIL -> pressure_coefficient
7395:                key_quantities = self._extract_airfoil_cp(
7400:                    key_quantities,
7406:            key_quantities = self._try_populate_from_c3_sampledict(
7407:                case_dir, task_spec, key_quantities, solver_name
7410:        return key_quantities
7515:        key_quantities: Dict[str, Any],
7526:            return key_quantities
7534:            return key_quantities
7536:            return key_quantities
7537:        key_quantities["u_centerline"] = u_values
7538:        key_quantities["u_centerline_source"] = "sampleDict_direct"
7545:            key_quantities["u_centerline_y"] = y_values
7548:        return key_quantities
7554:        key_quantities: Dict[str, Any],
7557:        `pressure_coefficient` with Cp = (p - p_inf) / (0.5·ρ·U_inf²).
7565:            return key_quantities
7572:            return key_quantities
7586:            return key_quantities
7589:        key_quantities["pressure_coefficient"] = cp_entries
7590:        key_quantities["pressure_coefficient_source"] = "sampleDict_direct"
7591:        return key_quantities
7597:        key_quantities: Dict[str, Any],
7614:            return key_quantities
7621:            return key_quantities
7625:            return key_quantities
7639:            return key_quantities
7640:        key_quantities["nusselt_number"] = nu_profile[0]  # stagnation (smallest r)
7641:        key_quantities["nusselt_number_profile"] = nu_profile
7642:        key_quantities["nusselt_number_source"] = "sampleDict_direct"
7643:        return key_quantities
7649:        key_quantities: Dict[str, Any],
7662:            key_quantities = self._populate_ldc_centerline_from_sampledict(
7663:                case_dir, task_spec, key_quantities
7666:            key_quantities = self._populate_naca_cp_from_sampledict(
7667:                case_dir, task_spec, key_quantities
7670:            key_quantities = self._populate_ij_nusselt_from_sampledict(
7671:                case_dir, task_spec, key_quantities
7673:        return key_quantities
7681:        key_quantities: Dict[str, Any],
7715:            return key_quantities
7746:        key_quantities["u_centerline"] = u_centerline
7747:        key_quantities["u_centerline_y"] = ghia_y
7748:        return key_quantities
7756:        key_quantities: Dict[str, Any],
7776:            return key_quantities
7804:            key_quantities["reattachment_length"] = reattachment_x / H
7806:            key_quantities["reattachment_detection_upstream_artifact"] = True
7807:            key_quantities["reattachment_detection_rejected_x"] = reattachment_x
7809:        return key_quantities
7817:        key_quantities: Dict[str, Any],
7826:            return key_quantities
7863:            key_quantities["nusselt_number"] = (sum(wall_gradients) / len(wall_gradients)) * L / dT_bulk
7870:                key_quantities["midPlaneT"] = [T for _, T in mid_profile]
7871:                key_quantities["midPlaneT_y"] = [x for x, _ in mid_profile]
7873:        return key_quantities
7885:        key_quantities: Dict[str, Any],
7894:            return key_quantities
7914:            return key_quantities
7923:        key_quantities["u_mean_profile"] = u_norm
7924:        key_quantities["u_mean_profile_y"] = sorted_y
7925:        key_quantities["U_max_approx"] = u_max
7927:        return key_quantities
7934:    def _extract_cylinder_strouhal(
7939:        key_quantities: Dict[str, Any],
7943:        Gold Standard: strouhal_number ≈ 0.165 (Re=100, Williamson 1996)
7949:            return key_quantities
7959:            key_quantities["strouhal_number"] = canonical_st
7960:            key_quantities["strouhal_canonical_band_shortcut_fired"] = True
7974:            return key_quantities
7994:            key_quantities["p_rms_near_cylinder"] = p_rms
7995:            key_quantities["pressure_coefficient_rms_near_cylinder"] = cp_rms
7998:            key_quantities["strouhal_number"] = min(max(0.0, 0.165 * cp_rms), 0.3)
8000:        return key_quantities
8012:        key_quantities: Dict[str, Any],
8021:            return key_quantities
8130:            key_quantities["cf_skin_friction"] = Cf_mean
8131:            key_quantities["cf_location_x"] = x_target
8132:            key_quantities["cf_spalding_fallback_count"] = cf_spalding_fallback_count
8133:            key_quantities["cf_spalding_fallback_activated"] = cf_spalding_fallback_count > 0
8135:        return key_quantities
8147:        key_quantities: Dict[str, Any],
8156:            return key_quantities
8180:            return key_quantities
8197:                    key_quantities["nusselt_number"] = Nu_stag
8211:                key_quantities["nusselt_number_profile"] = Nu_profile
8213:        return key_quantities
8225:        key_quantities: Dict[str, Any],
8237:            return key_quantities
8245:            return key_quantities
8310:            key_quantities["pressure_coefficient_x"] = [x for x, _ in cp_profile]
8311:            key_quantities["pressure_coefficient"] = [cp for _, cp in cp_profile]
8313:        return key_quantities
8325:        key_quantities: Dict[str, Any],
8333:            return key_quantities
8360:            return key_quantities
8374:                key_quantities["nusselt_number"] = Nu
8375:                key_quantities["midPlaneT"] = [T for _, T in y_t_pairs]
8376:                key_quantities["midPlaneT_y"] = [y for y, _ in y_t_pairs]
8378:        return key_quantities
8380:        return key_quantities
8396:            key_quantities={},

codex
The first concrete risk I see is around the server-rendered HTML path: `build_report_context()` now admits visual-only cases, but the Jinja template still dereferences gold-overlay fields unconditionally. I’m going to verify that behavior instead of assuming the frontend-only route hides it.
exec
/bin/zsh -lc "nl -ba ui/backend/tests/test_comparison_report_visual_only.py | sed -n '1,260p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
     1	"""Phase 7c Tier C (DEC-V61-034) — visual-only context + render-serving route tests.
     2	
     3	Guards:
     4	- build_report_context returns visual_only=True for VISUAL_ONLY_CASES
     5	- Render route serves PNG with path-containment defense
     6	- Traversal attempts in render filename are rejected (404)
     7	- Missing case / run_label produces 404 (not 500)
     8	- Tampered run-manifest timestamp is rejected (404)
     9	"""
    10	from __future__ import annotations
    11	
    12	import json
    13	from pathlib import Path
    14	
    15	import pytest
    16	from fastapi.testclient import TestClient
    17	
    18	from ui.backend.main import app
    19	from ui.backend.services.comparison_report import (
    20	    _VISUAL_ONLY_CASES,
    21	    ReportError,
    22	    build_report_context,
    23	)
    24	
    25	
    26	@pytest.fixture
    27	def client() -> TestClient:
    28	    return TestClient(app)
    29	
    30	
    31	def _plant_run_manifest(
    32	    repo_root: Path, case_id: str, timestamp: str = "20260101T000000Z",
    33	) -> Path:
    34	    """Write a minimal Phase 7a runs/{label}.json + corresponding renders
    35	    manifest + both PNGs into reports/phase5_{fields,renders}/{case}/.
    36	    """
    37	    fields_dir = repo_root / "reports" / "phase5_fields" / case_id
    38	    renders_dir = repo_root / "reports" / "phase5_renders" / case_id
    39	    artifact_dir = fields_dir / timestamp
    40	    render_ts_dir = renders_dir / timestamp
    41	    artifact_dir.mkdir(parents=True, exist_ok=True)
    42	    render_ts_dir.mkdir(parents=True, exist_ok=True)
    43	    (fields_dir / "runs").mkdir(parents=True, exist_ok=True)
    44	    (fields_dir / "runs" / "audit_real_run.json").write_text(
    45	        json.dumps({
    46	            "run_label": "audit_real_run",
    47	            "timestamp": timestamp,
    48	            "case_id": case_id,
    49	            "artifact_dir_rel": str(artifact_dir.relative_to(repo_root)),
    50	        }),
    51	        encoding="utf-8",
    52	    )
    53	    (artifact_dir / "log.simpleFoam").write_text("Time = 1s\n", encoding="utf-8")
    54	    (render_ts_dir / "contour_u_magnitude.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
    55	    (render_ts_dir / "residuals.png").write_bytes(b"\x89PNG\r\n\x1a\nfake2")
    56	    (renders_dir / "runs").mkdir(parents=True, exist_ok=True)
    57	    (renders_dir / "runs" / "audit_real_run.json").write_text(
    58	        json.dumps({
    59	            "run_label": "audit_real_run",
    60	            "timestamp": timestamp,
    61	            "case_id": case_id,
    62	            "outputs": {
    63	                "contour_u_magnitude_png":
    64	                    f"reports/phase5_renders/{case_id}/{timestamp}/contour_u_magnitude.png",
    65	                "residuals_png":
    66	                    f"reports/phase5_renders/{case_id}/{timestamp}/residuals.png",
    67	            },
    68	        }),
    69	        encoding="utf-8",
    70	    )
    71	    return artifact_dir
    72	
    73	
    74	def test_visual_only_cases_are_nine() -> None:
    75	    """VISUAL_ONLY_CASES covers all 9 non-LDC whitelist cases per DEC-V61-034."""
    76	    assert "lid_driven_cavity" not in _VISUAL_ONLY_CASES
    77	    expected = {
    78	        "backward_facing_step", "plane_channel_flow", "turbulent_flat_plate",
    79	        "circular_cylinder_wake", "impinging_jet", "naca0012_airfoil",
    80	        "rayleigh_benard_convection", "differential_heated_cavity", "duct_flow",
    81	    }
    82	    assert _VISUAL_ONLY_CASES == expected
    83	
    84	
    85	def test_visual_only_context_shape(tmp_path, monkeypatch) -> None:
    86	    """build_report_context returns visual_only=True with renders populated."""
    87	    case = "backward_facing_step"
    88	    _plant_run_manifest(tmp_path, case)
    89	    monkeypatch.setattr(
    90	        "ui.backend.services.comparison_report._FIELDS_ROOT",
    91	        tmp_path / "reports" / "phase5_fields",
    92	    )
    93	    monkeypatch.setattr(
    94	        "ui.backend.services.comparison_report._RENDERS_ROOT",
    95	        tmp_path / "reports" / "phase5_renders",
    96	    )
    97	    monkeypatch.setattr(
    98	        "ui.backend.services.comparison_report._REPO_ROOT", tmp_path,
    99	    )
   100	
   101	    ctx = build_report_context(case, "audit_real_run")
   102	    assert ctx["visual_only"] is True
   103	    assert ctx["case_id"] == case
   104	    assert ctx["run_label"] == "audit_real_run"
   105	    assert ctx["verdict"] is None
   106	    assert ctx["metrics"] is None
   107	    assert ctx["paper"] is None
   108	    assert ctx["renders"]["contour_png_rel"].endswith("contour_u_magnitude.png")
   109	    assert ctx["renders"]["residuals_png_rel"].endswith("residuals.png")
   110	    assert ctx["solver"] == "simpleFoam"
   111	    assert "visual-only" in ctx["subtitle"].lower()
   112	
   113	
   114	def test_unknown_case_404(client) -> None:
   115	    """Unsupported case → 404, not 500."""
   116	    resp = client.get(
   117	        "/api/cases/totally_unknown_case/runs/audit_real_run/comparison-report/context",
   118	    )
   119	    assert resp.status_code == 404
   120	
   121	
   122	def test_render_route_traversal_rejected(client) -> None:
   123	    """../../secret in render filename is rejected as 404 (traversal defense)."""
   124	    resp = client.get(
   125	        "/api/cases/backward_facing_step/runs/audit_real_run/renders/..%2F..%2F..%2Fetc%2Fpasswd",
   126	    )
   127	    assert resp.status_code == 404
   128	
   129	
   130	def test_render_route_missing_run_manifest_404(client, tmp_path, monkeypatch) -> None:
   131	    """Case id in supported set but no run manifest → 404 (no 500)."""
   132	    monkeypatch.setattr(
   133	        "ui.backend.services.comparison_report._FIELDS_ROOT",
   134	        tmp_path / "reports" / "phase5_fields",
   135	    )
   136	    resp = client.get(
   137	        "/api/cases/duct_flow/runs/nonexistent_run/renders/contour_u_magnitude.png",
   138	    )
   139	    assert resp.status_code == 404
   140	
   141	
   142	def test_visual_only_context_rejects_tampered_timestamp(tmp_path, monkeypatch) -> None:
   143	    """Run manifest with timestamp='../../etc' is rejected by _validated_timestamp."""
   144	    case = "plane_channel_flow"
   145	    fields_dir = tmp_path / "reports" / "phase5_fields" / case
   146	    (fields_dir / "runs").mkdir(parents=True)
   147	    (fields_dir / "runs" / "audit_real_run.json").write_text(
   148	        json.dumps({
   149	            "run_label": "audit_real_run",
   150	            "timestamp": "../../../etc/passwd",  # malicious
   151	            "case_id": case,
   152	        }),
   153	        encoding="utf-8",
   154	    )
   155	    monkeypatch.setattr(
   156	        "ui.backend.services.comparison_report._FIELDS_ROOT",
   157	        tmp_path / "reports" / "phase5_fields",
   158	    )
   159	
   160	    with pytest.raises(ReportError, match="invalid timestamp"):
   161	        build_report_context(case, "audit_real_run")
   162	
   163	
   164	def test_gold_overlay_case_not_affected_by_visual_only_branch(tmp_path, monkeypatch) -> None:
   165	    """LDC does NOT take the visual_only branch — existing gold-overlay flow
   166	    preserved. This test ensures the dispatch check is case-set membership,
   167	    not a global flag."""
   168	    from ui.backend.services.comparison_report import _GOLD_OVERLAY_CASES
   169	    assert "lid_driven_cavity" in _GOLD_OVERLAY_CASES
   170	    for c in _VISUAL_ONLY_CASES:
   171	        assert c not in _GOLD_OVERLAY_CASES

exec
/bin/zsh -lc 'rg -n "type ComparisonReportContext|ScientificComparisonReportSection|visual_only|renderUrl|basename|renders/" ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
365:      <ScientificComparisonReportSection caseId={caseId} />
1246:type ComparisonReportContext = {
1254:  visual_only?: boolean;
1290:function ScientificComparisonReportSection({ caseId }: { caseId: string }) {
1332:  if (data.visual_only) {
1336:    const renderUrl = (rel: string | undefined, basename: string) => {
1338:      return `/api/cases/${encodeURIComponent(caseId)}/runs/${encodeURIComponent(runLabel)}/renders/${basename}`;
1340:    const contourUrl = renderUrl(data.renders.contour_png_rel, "contour_u_magnitude.png");
1341:    const residualsUrl = renderUrl(data.renders.residuals_png_rel, "residuals.png");

exec
/bin/zsh -lc "nl -ba src/foam_agent_adapter.py | sed -n '560,650p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
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
/bin/zsh -lc "rg -n \"comparison-report|comparison_report|render_report_html|TestClient|app =|include_router\" ui/backend/tests ui/backend -g '*.py'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
ui/backend/tests/test_audit_package_route.py:9:from fastapi.testclient import TestClient
ui/backend/tests/test_audit_package_route.py:21:def client() -> TestClient:
ui/backend/tests/test_audit_package_route.py:22:    return TestClient(app)
ui/backend/services/comparison_report.py:9:Backend route: ui/backend/routes/comparison_report.py calls `render_report_html`
ui/backend/services/comparison_report.py:540:def render_report_html(case_id: str, run_label: str = "audit_real_run") -> str:
ui/backend/services/comparison_report.py:543:    tmpl = _env.get_template("comparison_report.html.j2")
ui/backend/services/comparison_report.py:569:        output_path = out_dir / f"{run_label}_comparison_report.pdf"
ui/backend/services/comparison_report.py:580:    html = render_report_html(case_id, run_label)
ui/backend/tests/test_comparison_report_route.py:9:from fastapi.testclient import TestClient
ui/backend/tests/test_comparison_report_route.py:13:client = TestClient(app)
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
ui/backend/tests/test_comparison_report_route.py:193:        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report.pdf",
ui/backend/tests/test_comparison_report_route.py:200:    """Codex round 3 MED follow-up: POST .../comparison-report/build must ALSO
ui/backend/tests/test_comparison_report_route.py:202:    from ui.backend.routes import comparison_report as route_mod
ui/backend/tests/test_comparison_report_route.py:209:        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report/build",
ui/backend/tests/test_audit_package_route.py:9:from fastapi.testclient import TestClient
ui/backend/tests/test_audit_package_route.py:21:def client() -> TestClient:
ui/backend/tests/test_audit_package_route.py:22:    return TestClient(app)
ui/backend/main.py:51:    comparison_report,
ui/backend/main.py:60:app = FastAPI(
ui/backend/main.py:82:app.include_router(health.router,       prefix="/api", tags=["health"])
ui/backend/main.py:83:app.include_router(cases.router,        prefix="/api", tags=["cases"])
ui/backend/main.py:84:app.include_router(case_editor.router,  prefix="/api", tags=["case-editor"])
ui/backend/main.py:85:app.include_router(validation.router,   prefix="/api", tags=["validation"])
ui/backend/main.py:86:app.include_router(decisions.router,    prefix="/api", tags=["decisions"])
ui/backend/main.py:87:app.include_router(run_monitor.router,  prefix="/api", tags=["runs"])
ui/backend/main.py:88:app.include_router(dashboard.router,    prefix="/api", tags=["dashboard"])
ui/backend/main.py:89:app.include_router(audit_package.router, prefix="/api", tags=["audit-package"])
ui/backend/main.py:90:app.include_router(case_export.router,  prefix="/api", tags=["case-export"])
ui/backend/main.py:91:app.include_router(field_artifacts.router, prefix="/api", tags=["field-artifacts"])
ui/backend/main.py:92:app.include_router(comparison_report.router, prefix="/api", tags=["comparison-report"])
ui/backend/tests/test_comparison_report_route.py:9:from fastapi.testclient import TestClient
ui/backend/tests/test_comparison_report_route.py:13:client = TestClient(app)
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
ui/backend/tests/test_comparison_report_route.py:193:        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report.pdf",
ui/backend/tests/test_comparison_report_route.py:200:    """Codex round 3 MED follow-up: POST .../comparison-report/build must ALSO
ui/backend/tests/test_comparison_report_route.py:202:    from ui.backend.routes import comparison_report as route_mod
ui/backend/tests/test_comparison_report_route.py:209:        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report/build",
ui/backend/tests/test_decisions_and_dashboard.py:8:from fastapi.testclient import TestClient
ui/backend/tests/test_decisions_and_dashboard.py:12:client = TestClient(app)
ui/backend/tests/test_validation_report.py:11:from fastapi.testclient import TestClient
ui/backend/tests/test_validation_report.py:17:def client() -> TestClient:
ui/backend/tests/test_validation_report.py:18:    return TestClient(app)
ui/backend/tests/test_validation_report.py:21:def test_cases_index_contains_ten_entries(client: TestClient) -> None:
ui/backend/tests/test_validation_report.py:33:def test_case_detail_differential_heated_cavity(client: TestClient) -> None:
ui/backend/tests/test_validation_report.py:51:def test_validation_report_dhc_is_fail_with_hazard(client: TestClient) -> None:
ui/backend/tests/test_validation_report.py:78:def test_validation_report_cylinder_wake_is_hazard(client: TestClient) -> None:
ui/backend/tests/test_validation_report.py:96:def test_validation_report_turbulent_flat_plate_hazard(client: TestClient) -> None:
ui/backend/tests/test_validation_report.py:115:    client: TestClient,
ui/backend/tests/test_validation_report.py:129:def test_validation_report_rejects_unknown_run_id(client: TestClient) -> None:
ui/backend/tests/test_validation_report.py:136:def test_case_runs_endpoint_lists_reference_pass_first(client: TestClient) -> None:
ui/backend/tests/test_validation_report.py:159:def test_unknown_case_returns_404(client: TestClient) -> None:
ui/backend/tests/test_validation_report.py:11:from fastapi.testclient import TestClient
ui/backend/tests/test_validation_report.py:17:def client() -> TestClient:
ui/backend/tests/test_validation_report.py:18:    return TestClient(app)
ui/backend/tests/test_validation_report.py:21:def test_cases_index_contains_ten_entries(client: TestClient) -> None:
ui/backend/tests/test_validation_report.py:33:def test_case_detail_differential_heated_cavity(client: TestClient) -> None:
ui/backend/tests/test_validation_report.py:51:def test_validation_report_dhc_is_fail_with_hazard(client: TestClient) -> None:
ui/backend/tests/test_validation_report.py:78:def test_validation_report_cylinder_wake_is_hazard(client: TestClient) -> None:
ui/backend/tests/test_validation_report.py:96:def test_validation_report_turbulent_flat_plate_hazard(client: TestClient) -> None:
ui/backend/tests/test_validation_report.py:115:    client: TestClient,
ui/backend/tests/test_validation_report.py:129:def test_validation_report_rejects_unknown_run_id(client: TestClient) -> None:
ui/backend/tests/test_validation_report.py:136:def test_case_runs_endpoint_lists_reference_pass_first(client: TestClient) -> None:
ui/backend/tests/test_validation_report.py:159:def test_unknown_case_returns_404(client: TestClient) -> None:
ui/backend/tests/test_case_editor.py:8:from fastapi.testclient import TestClient
ui/backend/tests/test_case_editor.py:13:client = TestClient(app)
ui/backend/tests/test_comparison_report_visual_only.py:16:from fastapi.testclient import TestClient
ui/backend/tests/test_comparison_report_visual_only.py:19:from ui.backend.services.comparison_report import (
ui/backend/tests/test_comparison_report_visual_only.py:27:def client() -> TestClient:
ui/backend/tests/test_comparison_report_visual_only.py:28:    return TestClient(app)
ui/backend/tests/test_comparison_report_visual_only.py:90:        "ui.backend.services.comparison_report._FIELDS_ROOT",
ui/backend/tests/test_comparison_report_visual_only.py:94:        "ui.backend.services.comparison_report._RENDERS_ROOT",
ui/backend/tests/test_comparison_report_visual_only.py:98:        "ui.backend.services.comparison_report._REPO_ROOT", tmp_path,
ui/backend/tests/test_comparison_report_visual_only.py:117:        "/api/cases/totally_unknown_case/runs/audit_real_run/comparison-report/context",
ui/backend/tests/test_comparison_report_visual_only.py:133:        "ui.backend.services.comparison_report._FIELDS_ROOT",
ui/backend/tests/test_comparison_report_visual_only.py:156:        "ui.backend.services.comparison_report._FIELDS_ROOT",
ui/backend/tests/test_comparison_report_visual_only.py:168:    from ui.backend.services.comparison_report import _GOLD_OVERLAY_CASES
ui/backend/tests/test_health.py:5:from fastapi.testclient import TestClient
ui/backend/tests/test_health.py:11:    client = TestClient(app)
ui/backend/tests/test_comparison_report_service.py:1:"""Phase 7c — comparison_report service unit tests (CI-safe, no real artifacts).
ui/backend/tests/test_comparison_report_service.py:4:constants, exercises render_report_html + build_report_context + the Codex
ui/backend/tests/test_comparison_report_service.py:87:    from ui.backend.services import comparison_report as svc
ui/backend/tests/test_comparison_report_service.py:108:    html = svc.render_report_html("lid_driven_cavity", "audit_real_run")
ui/backend/tests/test_health.py:5:from fastapi.testclient import TestClient
ui/backend/tests/test_health.py:11:    client = TestClient(app)
ui/backend/tests/test_audit_package_phase7e.py:65:    (reports / timestamp / f"{run_id}_comparison_report.pdf").write_bytes(
ui/backend/tests/test_audit_package_phase7e.py:84:    assert "phase7/comparison_report.pdf" in zip_paths
ui/backend/tests/test_audit_package_phase7e.py:172:        assert "phase7/comparison_report.pdf" in names
ui/backend/tests/test_audit_package_phase7e.py:180:        pdf_bytes = zf.read("phase7/comparison_report.pdf")
ui/backend/tests/test_audit_package_phase7e.py:183:                             "audit_real_run_comparison_report.pdf").read_bytes()
ui/backend/tests/test_field_artifacts_route.py:13:from fastapi.testclient import TestClient
ui/backend/tests/test_field_artifacts_route.py:30:def client() -> TestClient:
ui/backend/tests/test_field_artifacts_route.py:31:    return TestClient(app)
ui/backend/tests/test_field_artifacts_route.py:36:def test_get_manifest_200(client: TestClient) -> None:
ui/backend/tests/test_field_artifacts_route.py:46:def test_manifest_three_artifacts(client: TestClient) -> None:
ui/backend/tests/test_field_artifacts_route.py:55:def test_manifest_ordering(client: TestClient) -> None:
ui/backend/tests/test_field_artifacts_route.py:68:def test_sha256_format(client: TestClient) -> None:
ui/backend/tests/test_field_artifacts_route.py:75:def test_manifest_sizes_positive(client: TestClient) -> None:
ui/backend/tests/test_field_artifacts_route.py:82:def test_manifest_404_missing_run(client: TestClient) -> None:
ui/backend/tests/test_field_artifacts_route.py:87:def test_manifest_400_or_404_malformed_run_id(client: TestClient) -> None:
ui/backend/tests/test_field_artifacts_route.py:95:def test_download_residuals_csv_200(client: TestClient) -> None:
ui/backend/tests/test_field_artifacts_route.py:103:def test_download_vtk_200(client: TestClient) -> None:
ui/backend/tests/test_field_artifacts_route.py:109:def test_download_404_traversal_filename(client: TestClient) -> None:
ui/backend/tests/test_field_artifacts_route.py:114:def test_download_404_traversal_runid_literal(client: TestClient) -> None:
ui/backend/tests/test_field_artifacts_route.py:120:def test_download_404_traversal_runid_urlencoded(client: TestClient) -> None:
ui/backend/tests/test_field_artifacts_route.py:126:def test_manifest_400_traversal_runid(client: TestClient) -> None:
ui/backend/tests/test_field_artifacts_route.py:132:def test_manifest_uses_subpath_when_collision(client: TestClient) -> None:
ui/backend/tests/test_field_artifacts_route.py:156:        c = TestClient(app)
ui/backend/tests/test_field_artifacts_route.py:184:        c = TestClient(app)
ui/backend/tests/test_field_artifacts_route.py:217:        c = TestClient(app)
ui/backend/tests/test_field_artifacts_route.py:228:def test_download_404_missing(client: TestClient) -> None:
ui/backend/tests/test_field_artifacts_route.py:13:from fastapi.testclient import TestClient
ui/backend/tests/test_field_artifacts_route.py:30:def client() -> TestClient:
ui/backend/tests/test_field_artifacts_route.py:31:    return TestClient(app)
ui/backend/tests/test_field_artifacts_route.py:36:def test_get_manifest_200(client: TestClient) -> None:
ui/backend/tests/test_field_artifacts_route.py:46:def test_manifest_three_artifacts(client: TestClient) -> None:
ui/backend/tests/test_field_artifacts_route.py:55:def test_manifest_ordering(client: TestClient) -> None:
ui/backend/tests/test_field_artifacts_route.py:68:def test_sha256_format(client: TestClient) -> None:
ui/backend/tests/test_field_artifacts_route.py:75:def test_manifest_sizes_positive(client: TestClient) -> None:
ui/backend/tests/test_field_artifacts_route.py:82:def test_manifest_404_missing_run(client: TestClient) -> None:
ui/backend/tests/test_field_artifacts_route.py:87:def test_manifest_400_or_404_malformed_run_id(client: TestClient) -> None:
ui/backend/tests/test_field_artifacts_route.py:95:def test_download_residuals_csv_200(client: TestClient) -> None:
ui/backend/tests/test_field_artifacts_route.py:103:def test_download_vtk_200(client: TestClient) -> None:
ui/backend/tests/test_field_artifacts_route.py:109:def test_download_404_traversal_filename(client: TestClient) -> None:
ui/backend/tests/test_field_artifacts_route.py:114:def test_download_404_traversal_runid_literal(client: TestClient) -> None:
ui/backend/tests/test_field_artifacts_route.py:120:def test_download_404_traversal_runid_urlencoded(client: TestClient) -> None:
ui/backend/tests/test_field_artifacts_route.py:126:def test_manifest_400_traversal_runid(client: TestClient) -> None:
ui/backend/tests/test_field_artifacts_route.py:132:def test_manifest_uses_subpath_when_collision(client: TestClient) -> None:
ui/backend/tests/test_field_artifacts_route.py:156:        c = TestClient(app)
ui/backend/tests/test_field_artifacts_route.py:184:        c = TestClient(app)
ui/backend/tests/test_field_artifacts_route.py:217:        c = TestClient(app)
ui/backend/tests/test_field_artifacts_route.py:228:def test_download_404_missing(client: TestClient) -> None:
ui/backend/tests/test_comparison_report_visual_only.py:16:from fastapi.testclient import TestClient
ui/backend/tests/test_comparison_report_visual_only.py:19:from ui.backend.services.comparison_report import (
ui/backend/tests/test_comparison_report_visual_only.py:27:def client() -> TestClient:
ui/backend/tests/test_comparison_report_visual_only.py:28:    return TestClient(app)
ui/backend/tests/test_comparison_report_visual_only.py:90:        "ui.backend.services.comparison_report._FIELDS_ROOT",
ui/backend/tests/test_comparison_report_visual_only.py:94:        "ui.backend.services.comparison_report._RENDERS_ROOT",
ui/backend/tests/test_comparison_report_visual_only.py:98:        "ui.backend.services.comparison_report._REPO_ROOT", tmp_path,
ui/backend/tests/test_comparison_report_visual_only.py:117:        "/api/cases/totally_unknown_case/runs/audit_real_run/comparison-report/context",
ui/backend/tests/test_comparison_report_visual_only.py:133:        "ui.backend.services.comparison_report._FIELDS_ROOT",
ui/backend/tests/test_comparison_report_visual_only.py:156:        "ui.backend.services.comparison_report._FIELDS_ROOT",
ui/backend/tests/test_comparison_report_visual_only.py:168:    from ui.backend.services.comparison_report import _GOLD_OVERLAY_CASES
ui/backend/tests/test_comparison_report_service.py:1:"""Phase 7c — comparison_report service unit tests (CI-safe, no real artifacts).
ui/backend/tests/test_comparison_report_service.py:4:constants, exercises render_report_html + build_report_context + the Codex
ui/backend/tests/test_comparison_report_service.py:87:    from ui.backend.services import comparison_report as svc
ui/backend/tests/test_comparison_report_service.py:108:    html = svc.render_report_html("lid_driven_cavity", "audit_real_run")
ui/backend/routes/comparison_report.py:3:GET  /api/cases/{case_id}/runs/{run_label}/comparison-report         → HTML
ui/backend/routes/comparison_report.py:4:GET  /api/cases/{case_id}/runs/{run_label}/comparison-report.pdf     → PDF
ui/backend/routes/comparison_report.py:5:POST /api/cases/{case_id}/runs/{run_label}/comparison-report/build   → rebuild PDF + return manifest
ui/backend/routes/comparison_report.py:16:from ui.backend.services.comparison_report import (
ui/backend/routes/comparison_report.py:19:    render_report_html,
ui/backend/routes/comparison_report.py:34:    "/cases/{case_id}/runs/{run_label}/comparison-report",
ui/backend/routes/comparison_report.py:36:    tags=["comparison-report"],
ui/backend/routes/comparison_report.py:38:def get_comparison_report_html(case_id: str, run_label: str) -> HTMLResponse:
ui/backend/routes/comparison_report.py:42:        html = render_report_html(case_id, run_label)
ui/backend/routes/comparison_report.py:49:    "/cases/{case_id}/runs/{run_label}/comparison-report/context",
ui/backend/routes/comparison_report.py:50:    tags=["comparison-report"],
ui/backend/routes/comparison_report.py:52:def get_comparison_report_context(case_id: str, run_label: str) -> JSONResponse:
ui/backend/routes/comparison_report.py:66:    "/cases/{case_id}/runs/{run_label}/comparison-report.pdf",
ui/backend/routes/comparison_report.py:67:    tags=["comparison-report"],
ui/backend/routes/comparison_report.py:69:def get_comparison_report_pdf(case_id: str, run_label: str) -> FileResponse:
ui/backend/routes/comparison_report.py:92:        filename=f"{case_id}__{run_label}__comparison_report.pdf",
ui/backend/routes/comparison_report.py:98:    tags=["comparison-report"],
ui/backend/routes/comparison_report.py:108:    from ui.backend.services.comparison_report import _RENDERS_ROOT, _load_run_manifest, _validated_timestamp  # noqa: PLC0415
ui/backend/routes/comparison_report.py:141:    "/cases/{case_id}/runs/{run_label}/comparison-report/build",
ui/backend/routes/comparison_report.py:142:    tags=["comparison-report"],
ui/backend/routes/comparison_report.py:144:def build_comparison_report(case_id: str, run_label: str) -> JSONResponse:
ui/backend/routes/comparison_report.py:148:        html = render_report_html(case_id, run_label)
ui/backend/tests/test_decisions_and_dashboard.py:8:from fastapi.testclient import TestClient
ui/backend/tests/test_decisions_and_dashboard.py:12:client = TestClient(app)
ui/backend/tests/test_case_editor.py:8:from fastapi.testclient import TestClient
ui/backend/tests/test_case_editor.py:13:client = TestClient(app)
ui/backend/tests/test_case_export.py:9:from fastapi.testclient import TestClient
ui/backend/tests/test_case_export.py:13:client = TestClient(app)
ui/backend/tests/test_case_export.py:9:from fastapi.testclient import TestClient
ui/backend/tests/test_case_export.py:13:client = TestClient(app)
ui/backend/tests/test_audit_package_phase7e.py:65:    (reports / timestamp / f"{run_id}_comparison_report.pdf").write_bytes(
ui/backend/tests/test_audit_package_phase7e.py:84:    assert "phase7/comparison_report.pdf" in zip_paths
ui/backend/tests/test_audit_package_phase7e.py:172:        assert "phase7/comparison_report.pdf" in names
ui/backend/tests/test_audit_package_phase7e.py:180:        pdf_bytes = zf.read("phase7/comparison_report.pdf")
ui/backend/tests/test_audit_package_phase7e.py:183:                             "audit_real_run_comparison_report.pdf").read_bytes()

exec
/bin/zsh -lc "nl -ba ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx | sed -n '1220,1455p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba src/foam_agent_adapter.py | sed -n '7240,7415p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba src/foam_agent_adapter.py | sed -n '6820,7010p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba src/foam_agent_adapter.py | sed -n '7930,8010p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
  7240	    # ------------------------------------------------------------------
  7241	    # writeObjects field extraction
  7242	    # ------------------------------------------------------------------
  7243	
  7244	    def _parse_writeobjects_fields(
  7245	        self,
  7246	        case_dir: Path,
  7247	        solver_name: str,
  7248	        task_spec: Optional[TaskSpec],
  7249	        key_quantities: Dict[str, Any],
  7250	    ) -> Dict[str, Any]:
  7251	        """从 postProcess writeObjects 输出的场文件提取 case-specific 关键物理量。
  7252	
  7253	        postProcess -func writeObjects -latestTime 在最新时间目录写出:
  7254	        - U: vector field (Ux, Uy, Uz) for each cell
  7255	        - Cx, Cy, Cz: cell centre coordinates
  7256	        - p: pressure field
  7257	        这些文件格式为 OpenFOAM internalField nonuniform List<...>。
  7258	
  7259	        Returns:
  7260	            key_quantities updated with u_centerline, reattachment_length, nusselt_number
  7261	        """
  7262	        if task_spec is None:
  7263	            return key_quantities
  7264	
  7265	        # 找到最新时间目录
  7266	        time_dirs = []
  7267	        for item in case_dir.iterdir():
  7268	            if item.is_dir():
  7269	                try:
  7270	                    t = float(item.name)
  7271	                    time_dirs.append((t, item))
  7272	                except ValueError:
  7273	                    pass
  7274	        if not time_dirs:
  7275	            return key_quantities
  7276	
  7277	        latest_t, latest_dir = max(time_dirs, key=lambda x: x[0])
  7278	
  7279	        # 检查是否有 U 和 Cx/Cy 文件
  7280	        u_path = latest_dir / "U"
  7281	        cx_path = latest_dir / "Cx"
  7282	        cy_path = latest_dir / "Cy"
  7283	        if not all(p.exists() for p in [u_path, cx_path, cy_path]):
  7284	            return key_quantities
  7285	
  7286	        # 读取场数据
  7287	        cxs = self._read_openfoam_scalar_field(cx_path)
  7288	        cys = self._read_openfoam_scalar_field(cy_path)
  7289	        cz_path = latest_dir / "Cz"
  7290	        czs = self._read_openfoam_scalar_field(cz_path) if cz_path.exists() else None
  7291	        u_vecs = self._read_openfoam_vector_field(u_path, len(cxs))
  7292	
  7293	        if len(cxs) != len(cys) or len(cxs) != len(u_vecs):
  7294	            return key_quantities
  7295	        if czs is not None and len(czs) != len(cxs):
  7296	            czs = None
  7297	
  7298	        geom = task_spec.geometry_type
  7299	        name_lower = task_spec.name.lower()
  7300	
  7301	        # LDC / CUSTOM: 提取 x=0.5 (normalized) 的中心线速度剖面
  7302	        # Covers: icoFoam+SIMPLE_GRID (explicit), name-based SIMPLE_GRID/CUSTOM, Re<2300
  7303	        if self._is_lid_driven_cavity_case(task_spec, solver_name):
  7304	            key_quantities = self._extract_ldc_centerline(
  7305	                cxs, cys, u_vecs, task_spec, key_quantities
  7306	            )
  7307	
  7308	        # BFS: 提取 y=0.5 (wall) 的速度剖面找再附着长度
  7309	        elif geom == GeometryType.BACKWARD_FACING_STEP:
  7310	            key_quantities = self._extract_bfs_reattachment(
  7311	                cxs, cys, u_vecs, task_spec, key_quantities
  7312	            )
  7313	
  7314	        # NC Cavity: 提取 mid-plane 温度剖面算 Nusselt number
  7315	        elif geom == GeometryType.NATURAL_CONVECTION_CAVITY:
  7316	            # buoyantFoam writes T (temperature) to disk; read it directly
  7317	            t_path = latest_dir / "T"
  7318	            if t_path.exists():
  7319	                t_vals = self._read_openfoam_scalar_field(t_path)
  7320	                key_quantities = self._extract_nc_nusselt(
  7321	                    cxs, cys, t_vals, task_spec, key_quantities
  7322	                )
  7323	
  7324	        # Plane Channel Flow DNS: BODY_IN_CHANNEL + INTERNAL -> u_mean_profile
  7325	        elif geom == GeometryType.BODY_IN_CHANNEL and task_spec.flow_type == FlowType.INTERNAL:
  7326	            key_quantities = self._extract_plane_channel_profile(
  7327	                cxs, cys, u_vecs, task_spec, key_quantities
  7328	            )
  7329	
  7330	        # Circular Cylinder Wake: BODY_IN_CHANNEL + EXTERNAL -> strouhal_number
  7331	        elif geom == GeometryType.BODY_IN_CHANNEL and task_spec.flow_type == FlowType.EXTERNAL:
  7332	            p_path = latest_dir / "p"
  7333	            if p_path.exists():
  7334	                p_vals = self._read_openfoam_scalar_field(p_path)
  7335	                key_quantities = self._extract_cylinder_strouhal(
  7336	                    cxs, cys, p_vals, task_spec, key_quantities
  7337	                )
  7338	
  7339	        # Turbulent Flat Plate: SIMPLE_GRID + Re>=2300 -> cf_skin_friction
  7340	        # P6-TD-002 guard: exclude duct_flow (also SIMPLE_GRID + Re>=2300).
  7341	        # Canonical observable for duct is Darcy-Weisbach friction_factor,
  7342	        # NOT skin-friction Cf. Before this guard, duct_flow fell through
  7343	        # to _extract_flat_plate_cf and the Spalding fallback
  7344	        # (0.0576/Re_x^0.2 with Re_x=0.5*Re) returned a Cf that depends
  7345	        # only on Re — identical to 10 decimals for any case sharing Re
  7346	        # with flat plate. §5d Part-2 acceptance observed TFP and duct_flow
  7347	        # both returning cf=0.007600365566051871 (Re=50000 for both).
  7348	        #
  7349	        # Round-8 correction: classification uses _is_duct_flow_case()
  7350	        # which prefers canonical task name identity and falls back to
  7351	        # hydraulic_diameter. This closes the list_whitelist_cases() path
  7352	        # where hydraulic_diameter stays under `parameters` and never
  7353	        # migrates into boundary_conditions.
  7354	        elif (
  7355	            self._is_duct_flow_case(task_spec)
  7356	            and task_spec.Re is not None
  7357	            and task_spec.Re >= 2300
  7358	        ):
  7359	            # Duct flow detected; no dedicated extractor yet (queued as
  7360	            # P6-TD-003). Emit producer flags so audit surfaces can
  7361	            # distinguish "duct pending" from "flat plate Spalding".
  7362	            key_quantities["duct_flow_extractor_pending"] = True
  7363	            hd = (task_spec.boundary_conditions or {}).get("hydraulic_diameter")
  7364	            if hd is not None:
  7365	                key_quantities["duct_flow_hydraulic_diameter"] = hd
  7366	            else:
  7367	                # Duct-identified via name but missing hydraulic_diameter
  7368	                # in BCs (list_whitelist_cases() path). Flag fail-closed so
  7369	                # downstream audit sees malformed-input explicitly rather
  7370	                # than a silent-reroute masquerading as a valid measurement.
  7371	                key_quantities["duct_flow_hydraulic_diameter_missing"] = True
  7372	        elif (
  7373	            geom == GeometryType.SIMPLE_GRID
  7374	            and task_spec.Re is not None
  7375	            and task_spec.Re >= 2300
  7376	        ):
  7377	            key_quantities = self._extract_flat_plate_cf(
  7378	                cxs, cys, u_vecs, task_spec, key_quantities
  7379	            )
  7380	
  7381	        # Impinging Jet: IMPINGING_JET -> nusselt_number
  7382	        elif geom == GeometryType.IMPINGING_JET:
  7383	            t_path = latest_dir / "T"
  7384	            if t_path.exists():
  7385	                t_vals = self._read_openfoam_scalar_field(t_path)
  7386	                key_quantities = self._extract_jet_nusselt(
  7387	                    cxs, cys, t_vals, task_spec, key_quantities
  7388	                )
  7389	
  7390	        # Airfoil: AIRFOIL -> pressure_coefficient
  7391	        elif geom == GeometryType.AIRFOIL:
  7392	            p_path = latest_dir / "p"
  7393	            if p_path.exists():
  7394	                p_vals = self._read_openfoam_scalar_field(p_path)
  7395	                key_quantities = self._extract_airfoil_cp(
  7396	                    cxs,
  7397	                    czs if czs is not None else cys,
  7398	                    p_vals,
  7399	                    task_spec,
  7400	                    key_quantities,
  7401	                )
  7402	
  7403	        # C3 result-harvest side: overwrite standard keys with gold-anchored
  7404	        # sampleDict output when present. No-op for MOCK / pre-C3 cases.
  7405	        if task_spec is not None:
  7406	            key_quantities = self._try_populate_from_c3_sampledict(
  7407	                case_dir, task_spec, key_quantities, solver_name
  7408	            )
  7409	
  7410	        return key_quantities
  7411	
  7412	    @staticmethod
  7413	    def _read_openfoam_scalar_field(filepath: Path) -> List[float]:
  7414	        """解析 OpenFOAM internalField nonuniform List<scalar> 文件。"""
  7415	        with filepath.open() as f:

 succeeded in 0ms:
  1220	        </Link>
  1221	      </div>
  1222	    </div>
  1223	  );
  1224	}
  1225	
  1226	// --- Shared callouts ----------------------------------------------------------
  1227	
  1228	function ErrorCallout({ message }: { message: string }) {
  1229	  return (
  1230	    <div className="rounded-md border border-contract-fail/40 bg-contract-fail/10 p-4 text-[13px] text-contract-fail">
  1231	      {message}
  1232	    </div>
  1233	  );
  1234	}
  1235	
  1236	function SkeletonCallout({ message }: { message: string }) {
  1237	  return (
  1238	    <div className="rounded-md border border-surface-800 bg-surface-900/30 p-4 text-[13px] text-surface-400">
  1239	      {message}
  1240	    </div>
  1241	  );
  1242	}
  1243	
  1244	// --- Phase 7f: Scientific CFD-vs-Gold comparison report section -----------
  1245	
  1246	type ComparisonReportContext = {
  1247	  // Shared across both modes.
  1248	  case_id: string;
  1249	  case_display_name?: string;
  1250	  run_label: string;
  1251	  timestamp: string;
  1252	  // Tier C marker: if true, this is a visual-only reduced context with
  1253	  // no gold-overlay / verdict / metrics / paper. Renders still populated.
  1254	  visual_only?: boolean;
  1255	  // Full (LDC gold-overlay) fields:
  1256	  verdict: "PASS" | "PARTIAL" | "FAIL" | string | null;
  1257	  verdict_subtitle?: string;
  1258	  subtitle?: string;
  1259	  metrics?: {
  1260	    max_dev_pct: number;
  1261	    l2: number;
  1262	    linf: number;
  1263	    rms: number;
  1264	    n_pass: number;
  1265	    n_total: number;
  1266	  } | null;
  1267	  paper?: {
  1268	    title: string;
  1269	    source: string;
  1270	    doi?: string;
  1271	    short: string;
  1272	    gold_count: number;
  1273	    tolerance_pct: number;
  1274	  } | null;
  1275	  renders: {
  1276	    profile_png_rel?: string;
  1277	    pointwise_png_rel?: string;
  1278	    contour_png_rel: string;
  1279	    residuals_png_rel: string;
  1280	  };
  1281	  meta?: {
  1282	    commit_sha: string;
  1283	    report_generated_at: string;
  1284	  };
  1285	  // Visual-only top-level fields:
  1286	  solver?: string;
  1287	  commit_sha?: string;
  1288	};
  1289	
  1290	function ScientificComparisonReportSection({ caseId }: { caseId: string }) {
  1291	  const runLabel = "audit_real_run";
  1292	  const { data, isLoading, error } = useQuery<ComparisonReportContext, ApiError>({
  1293	    queryKey: ["comparison-report-ctx", caseId, runLabel],
  1294	    queryFn: async () => {
  1295	      const resp = await fetch(
  1296	        `/api/cases/${encodeURIComponent(caseId)}/runs/${encodeURIComponent(
  1297	          runLabel,
  1298	        )}/comparison-report/context`,
  1299	        { credentials: "same-origin" },
  1300	      );
  1301	      if (!resp.ok) throw new ApiError(resp.status, await resp.text());
  1302	      return (await resp.json()) as ComparisonReportContext;
  1303	    },
  1304	    retry: false,
  1305	    staleTime: 60_000,
  1306	  });
  1307	
  1308	  if (isLoading) return null; // quiet during fetch
  1309	  // Codex round 1 MED (2026-04-21): distinguish 404/400 (case not opted-in
  1310	  // → silent hide) from 5xx / malformed JSON / network errors (show banner
  1311	  // so regressions are visible, not silently swallowed).
  1312	  if (error) {
  1313	    const status = error instanceof ApiError ? error.status : 0;
  1314	    if (status === 404 || status === 400) return null; // case not opted-in
  1315	    return (
  1316	      <section>
  1317	        <div className="mb-3 flex items-baseline justify-between">
  1318	          <h2 className="card-title">科研级 CFD vs Gold 验证报告</h2>
  1319	          <p className="text-[11px] text-surface-500">报告服务暂不可用</p>
  1320	        </div>
  1321	        <ErrorCallout
  1322	          message={`无法加载对比报告 (HTTP ${status || "network"}): ${error.message.slice(0, 200)}`}
  1323	        />
  1324	      </section>
  1325	    );
  1326	  }
  1327	  if (!data) return null;
  1328	
  1329	  // DEC-V61-034 Tier C: visual-only branch. No verdict card / iframe; just
  1330	  // show the real contour + residuals PNGs directly so every case has real
  1331	  // OpenFOAM evidence on the /learn page.
  1332	  if (data.visual_only) {
  1333	    // Serve PNGs via the /api route (with path-containment defense) rather
  1334	    // than raw /reports paths — keeps the visible URL under the signed API
  1335	    // surface and avoids needing a FastAPI StaticFiles mount.
  1336	    const renderUrl = (rel: string | undefined, basename: string) => {
  1337	      if (!rel) return null;
  1338	      return `/api/cases/${encodeURIComponent(caseId)}/runs/${encodeURIComponent(runLabel)}/renders/${basename}`;
  1339	    };
  1340	    const contourUrl = renderUrl(data.renders.contour_png_rel, "contour_u_magnitude.png");
  1341	    const residualsUrl = renderUrl(data.renders.residuals_png_rel, "residuals.png");
  1342	    return (
  1343	      <section>
  1344	        <div className="mb-3 flex items-baseline justify-between">
  1345	          <h2 className="card-title">科研级 CFD 仿真结果 (Visual-only)</h2>
  1346	          <p className="text-[11px] text-surface-500">
  1347	            实际 OpenFOAM 真跑 · {data.solver ?? "solver"} · {data.commit_sha ?? ""}
  1348	          </p>
  1349	        </div>
  1350	        <div className="mb-3 rounded-md border border-surface-700 bg-surface-900/40 p-3 text-[12px] text-surface-300">
  1351	          {data.subtitle ?? "Visual-only mode — gold-overlay verdict pending Phase 7c Sprint 2."}
  1352	        </div>
  1353	        <div className="grid gap-3 md:grid-cols-2">
  1354	          {contourUrl && (
  1355	            <div className="rounded-md border border-surface-800 bg-white p-2">
  1356	              <div className="mb-1 text-[11px] font-semibold text-surface-500 px-1">
  1357	                |U| 速度幅值云图
  1358	              </div>
  1359	              <img src={contourUrl} alt={`${caseId} |U| contour`} className="w-full" />
  1360	            </div>
  1361	          )}
  1362	          {residualsUrl && (
  1363	            <div className="rounded-md border border-surface-800 bg-white p-2">
  1364	              <div className="mb-1 text-[11px] font-semibold text-surface-500 px-1">
  1365	                残差收敛历史 (log scale)
  1366	              </div>
  1367	              <img src={residualsUrl} alt={`${caseId} residuals`} className="w-full" />
  1368	            </div>
  1369	          )}
  1370	          {!contourUrl && !residualsUrl && (
  1371	            <p className="text-[12px] text-surface-500">
  1372	              (artifact capture empty — re-run phase5 audit script for this case)
  1373	            </p>
  1374	          )}
  1375	        </div>
  1376	      </section>
  1377	    );
  1378	  }
  1379	
  1380	  // Gold-overlay mode (LDC today). Verdict card + iframe 8-section report.
  1381	  const verdictColor =
  1382	    data.verdict === "PASS"
  1383	      ? "bg-contract-pass/15 border-contract-pass/40 text-contract-pass"
  1384	      : data.verdict === "PARTIAL"
  1385	      ? "bg-yellow-500/10 border-yellow-500/40 text-yellow-300"
  1386	      : "bg-contract-fail/15 border-contract-fail/40 text-contract-fail";
  1387	
  1388	  const reportHtmlUrl = `/api/cases/${encodeURIComponent(caseId)}/runs/${encodeURIComponent(
  1389	    runLabel,
  1390	  )}/comparison-report`;
  1391	  const reportPdfUrl = `/api/cases/${encodeURIComponent(caseId)}/runs/${encodeURIComponent(
  1392	    runLabel,
  1393	  )}/comparison-report.pdf`;
  1394	
  1395	  // Defensive: if gold-overlay shape is missing fields, bail silently.
  1396	  if (!data.metrics || !data.meta) return null;
  1397	
  1398	  return (
  1399	    <section>
  1400	      <div className="mb-3 flex items-baseline justify-between">
  1401	        <h2 className="card-title">科研级 CFD vs Gold 验证报告</h2>
  1402	        <p className="text-[11px] text-surface-500">
  1403	          实际 OpenFOAM 真跑 · 8 sections · {data.meta.commit_sha}
  1404	        </p>
  1405	      </div>
  1406	
  1407	      <div
  1408	        className={`mb-4 rounded-md border p-4 ${verdictColor}`}
  1409	        role="status"
  1410	      >
  1411	        <div className="flex items-center justify-between gap-4">
  1412	          <div>
  1413	            <div className="text-[11px] font-semibold uppercase tracking-wider opacity-85">
  1414	              Verdict
  1415	            </div>
  1416	            <div className="mt-1 text-[22px] font-bold leading-tight">
  1417	              {data.verdict}
  1418	            </div>
  1419	            <div className="mt-1 text-[12px] text-surface-200">
  1420	              {data.verdict_subtitle}
  1421	            </div>
  1422	          </div>
  1423	          <div className="grid grid-cols-2 gap-3 text-right text-[12px]">
  1424	            <div>
  1425	              <div className="text-surface-400">max |dev|</div>
  1426	              <div className="mono text-surface-100">
  1427	                {data.metrics.max_dev_pct.toFixed(2)}%
  1428	              </div>
  1429	            </div>
  1430	            <div>
  1431	              <div className="text-surface-400">n_pass</div>
  1432	              <div className="mono text-surface-100">
  1433	                {data.metrics.n_pass} / {data.metrics.n_total}
  1434	              </div>
  1435	            </div>
  1436	            <div>
  1437	              <div className="text-surface-400">L²</div>
  1438	              <div className="mono text-surface-100">
  1439	                {data.metrics.l2.toFixed(4)}
  1440	              </div>
  1441	            </div>
  1442	            <div>
  1443	              <div className="text-surface-400">L∞</div>
  1444	              <div className="mono text-surface-100">
  1445	                {data.metrics.linf.toFixed(4)}
  1446	              </div>
  1447	            </div>
  1448	          </div>
  1449	        </div>
  1450	      </div>
  1451	
  1452	      <div className="mb-3 flex flex-wrap gap-2 text-[12px]">
  1453	        <a
  1454	          href={reportHtmlUrl}
  1455	          target="_blank"

 succeeded in 0ms:
  6820	                            dest_path.write_bytes(member.read())
  6821	                        break
  6822	        except Exception as e:
  6823	            import sys as _sys
  6824	            print(f"[WARN] _copy_file_from_container failed: {e}", file=_sys.stderr)
  6825	
  6826	    def _copy_postprocess_fields(
  6827	        self, container: Any, case_cont_dir: str, case_host_dir: Path
  6828	    ) -> None:
  6829	        """从容器内复制 postProcess -func writeObjects 输出的场文件到宿主机。
  6830	
  6831	        postProcess 在 latestTime 目录写出 U, Cx, Cy, (T) 等场文件，
  6832	        将这些文件复制到宿主机的对应时间目录。
  6833	        """
  6834	        try:
  6835	            # Find numeric time directories (exclude '0' - initial condition)
  6836	            result = container.exec_run(
  6837	                cmd=[
  6838	                    "bash",
  6839	                    "-c",
  6840	                    f'find "{case_cont_dir}" -maxdepth 1 -type d -name "[0-9]*" 2>/dev/null | grep -v "/0$" | sed "s|/$||" | sort -t/ -k1 -n | tail -1',
  6841	                ],
  6842	            )
  6843	            latest_cont_dir = result.output.decode().strip()
  6844	
  6845	            if not latest_cont_dir:
  6846	                return
  6847	
  6848	            # Verify it's a directory, not a file
  6849	            path_check = container.exec_run(
  6850	                cmd=["bash", "-c", f'if [ ! -d "{latest_cont_dir}" ]; then echo not_dir; fi']
  6851	            )
  6852	            if path_check.output.decode().strip() == "not_dir":
  6853	                return
  6854	
  6855	            latest_time = Path(latest_cont_dir).name
  6856	
  6857	            # 场文件：U 和 Cx/Cy 必选，Cz/T 按 case 需要复制。
  6858	            field_files = ["U", "p", "Cx", "Cy", "Cz", "T"]
  6859	            host_time_dir = case_host_dir / latest_time
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
  6909	            #     -noFaceZones: DEC-V61-034 Tier C, circular_cylinder_wake uses
  6910	            #     createBaffles which leaves a cylinderBaffleZone faceZone; OF10
  6911	            #     foamToVTK SEGVs when interpolating surfScalarField phi onto
  6912	            #     the post-baffle faceZone (flux pointer inconsistent with
  6913	            #     split owner/neighbour patches of the same name). -noFaceZones
  6914	            #     skips the faceZone write, which is not required downstream
  6915	            #     (the cylinder wall is already emitted as a regular patch).
  6916	            #     No-op for the 9 cases that don't use faceZones.
  6917	            #     Fallback without -allPatches if it trips empty-patch
  6918	            #     assertions (07a-RESEARCH.md §3.2).
  6919	            ok, log = self._docker_exec(
  6920	                "foamToVTK -latestTime -noZero -allPatches -noFaceZones",
  6921	                case_cont_dir,
  6922	                120,
  6923	            )
  6924	            if not ok:
  6925	                print(
  6926	                    # Tail slice: SEGV stack traces + OF error strings are at
  6927	                    # end-of-log, not the banner. 200-char head truncation
  6928	                    # hid the cylinder_wake SEGV for a full diagnosis cycle.
  6929	                    f"[WARN] foamToVTK -allPatches failed, retrying without: {log[-400:]}",
  6930	                    file=_sys.stderr,
  6931	                )
  6932	                ok, log = self._docker_exec(
  6933	                    "foamToVTK -latestTime -noZero -noFaceZones", case_cont_dir, 120,
  6934	                )
  6935	            if not ok:
  6936	                print(
  6937	                    f"[WARN] foamToVTK failed, field capture skipped: {log[-400:]}",
  6938	                    file=_sys.stderr,
  6939	                )
  6940	                return None
  6941	
  6942	            # (b) Tar + get_archive the three subtrees. Missing subtrees are
  6943	            #     fine (e.g. postProcessing/residuals only exists if the
  6944	            #     residuals function object was emitted).
  6945	            for sub in ("VTK", "postProcessing/sample", "postProcessing/residuals"):
  6946	                src_in_cont = f"{case_cont_dir}/{sub}"
  6947	                probe = container.exec_run(
  6948	                    cmd=["bash", "-c", f'[ -e "{src_in_cont}" ] && echo y || echo n'],
  6949	                )
  6950	                if probe.output.decode().strip() != "y":
  6951	                    continue
  6952	                try:
  6953	                    bits, _ = container.get_archive(src_in_cont)
  6954	                    buf = _io.BytesIO(b"".join(bits))
  6955	                    with _tarfile.open(fileobj=buf) as tar:
  6956	                        tar.extractall(path=artifact_dir)
  6957	                except Exception as e:  # noqa: BLE001
  6958	                    print(
  6959	                        f"[WARN] staging {sub} failed: {e!r}", file=_sys.stderr,
  6960	                    )
  6961	
  6962	            # (c) log.<solver> — already on host after _docker_exec.
  6963	            for logname in (
  6964	                "log.simpleFoam",
  6965	                "log.icoFoam",
  6966	                "log.buoyantFoam",
  6967	                "log.pimpleFoam",
  6968	            ):
  6969	                src = case_host_dir / logname
  6970	                if src.is_file():
  6971	                    (artifact_dir / logname).write_bytes(src.read_bytes())
  6972	                    break
  6973	
  6974	            # (d) Derive residuals.csv from residuals/0/residuals.dat if present.
  6975	            #     Per user ratification #3 — structured ASCII, no log regex.
  6976	            #     NOTE: container.get_archive('.../postProcessing/residuals')
  6977	            #     tar-extracts under basename `residuals/`, not the full
  6978	            #     `postProcessing/residuals/` path. Same applies to `sample/`.
  6979	            residuals_dat_candidates = list(
  6980	                artifact_dir.glob("residuals/*/residuals.dat")
  6981	            )
  6982	            if residuals_dat_candidates:
  6983	                try:
  6984	                    self._emit_residuals_csv(
  6985	                        residuals_dat_candidates[0],
  6986	                        artifact_dir / "residuals.csv",
  6987	                    )
  6988	                except Exception as e:  # noqa: BLE001
  6989	                    print(
  6990	                        f"[WARN] residuals.csv derivation failed: {e!r}",
  6991	                        file=_sys.stderr,
  6992	                    )
  6993	
  6994	            return artifact_dir
  6995	        except Exception as e:  # noqa: BLE001
  6996	            print(
  6997	                f"[WARN] _capture_field_artifacts failed: {e!r}", file=_sys.stderr,
  6998	            )
  6999	            return None
  7000	
  7001	    @staticmethod
  7002	    def _emit_residuals_csv(dat_path: Path, csv_path: Path) -> None:
  7003	        """Convert OpenFOAM v10 residuals function-object output to CSV.
  7004	
  7005	        The .dat format is whitespace-separated with a header line starting
  7006	        with `#`. We passthrough as CSV (comma-separated) with an explicit
  7007	        header — downstream tools (Phase 7b render pipeline) consume this.
  7008	        """
  7009	        lines = dat_path.read_text(encoding="utf-8").splitlines()
  7010	        header: Optional[List[str]] = None

 succeeded in 0ms:
  7930	    # Circular Cylinder Wake — 提取 Strouhal 数
  7931	    # ------------------------------------------------------------------
  7932	
  7933	    @staticmethod
  7934	    def _extract_cylinder_strouhal(
  7935	        cxs: List[float],
  7936	        cys: List[float],
  7937	        p_vals: List[float],
  7938	        task_spec: TaskSpec,
  7939	        key_quantities: Dict[str, Any],
  7940	    ) -> Dict[str, Any]:
  7941	        """Circular Cylinder Wake: 从压力场估计 Strouhal 数。
  7942	
  7943	        Gold Standard: strouhal_number ≈ 0.165 (Re=100, Williamson 1996)
  7944	        方法: 找到cylinder近场（cx≈0, cy≈0）压力，计算 RMS 脉动，
  7945	        从特征频率 f 估算 St = f*D/U。
  7946	        对于稳态/RANS 结果（无时间序列），用 RMS 压力作为替代指标。
  7947	        """
  7948	        if not cxs or not p_vals:
  7949	            return key_quantities
  7950	
  7951	        Re = float(task_spec.Re or 100.0)
  7952	        D = 0.1  # cylinder diameter used in _generate_body_in_channel
  7953	        U_ref = 1.0  # canonical inlet velocity for this case
  7954	        rho = 1.0
  7955	        q_ref = 0.5 * rho * U_ref**2
  7956	        canonical_st = 0.165 if 50.0 <= Re <= 200.0 else None
  7957	
  7958	        if canonical_st is not None:
  7959	            key_quantities["strouhal_number"] = canonical_st
  7960	            key_quantities["strouhal_canonical_band_shortcut_fired"] = True
  7961	
  7962	        # 找 cylinder 附近区域（cx≈0, cy≈0）
  7963	        cx_c = 0.0
  7964	        cy_c = 0.0
  7965	
  7966	        # 找 cylinder 表面附近（距中心 0.5D）压力
  7967	        p_near = []
  7968	        for i in range(min(len(cxs), len(cys), len(p_vals))):
  7969	            dist = ((cxs[i] - cx_c)**2 + (cys[i] - cy_c)**2)**0.5
  7970	            if 0.4 * D < dist < 0.6 * D:
  7971	                p_near.append(p_vals[i])
  7972	
  7973	        if not p_near:
  7974	            return key_quantities
  7975	
  7976	        p_mean = sum(p_near) / len(p_near)
  7977	        p_rms = (sum((p - p_mean)**2 for p in p_near) / len(p_near))**0.5
  7978	
  7979	        # Convert to fluctuating Cp so solver-dependent pressure offsets do not
  7980	        # dominate the fallback logic.
  7981	        if q_ref > 0:
  7982	            cp_fluctuations = [(p - p_mean) / q_ref for p in p_near]
  7983	            cp_rms = (sum(cp * cp for cp in cp_fluctuations) / len(cp_fluctuations))**0.5
  7984	        else:
  7985	            cp_rms = float("inf")
  7986	
  7987	        cp_is_reasonable = (
  7988	            math.isfinite(p_rms)
  7989	            and math.isfinite(cp_rms)
  7990	            and 0.0 <= cp_rms <= 10.0
  7991	        )
  7992	
  7993	        if cp_is_reasonable:
  7994	            key_quantities["p_rms_near_cylinder"] = p_rms
  7995	            key_quantities["pressure_coefficient_rms_near_cylinder"] = cp_rms
  7996	
  7997	        if canonical_st is None and cp_is_reasonable:
  7998	            key_quantities["strouhal_number"] = min(max(0.0, 0.165 * cp_rms), 0.3)
  7999	
  8000	        return key_quantities
  8001	
  8002	    # ------------------------------------------------------------------
  8003	    # Turbulent Flat Plate — 提取局部摩擦系数 Cf
  8004	    # ------------------------------------------------------------------
  8005	
  8006	    @staticmethod
  8007	    def _extract_flat_plate_cf(
  8008	        cxs: List[float],
  8009	        cys: List[float],
  8010	        u_vecs: List[Tuple],

exec
/bin/zsh -lc 'rg -n "_parse_residuals_from_log|iter_re|residual|_pick_2d_plane|tricontour|nan|isfinite|render_all|VISUAL_ONLY_CASES|GOLD_OVERLAY_CASES" scripts/render_case_report.py' in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba ui/backend/services/run_ids.py | sed -n '1,180p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
9:- residuals.png              — log-y residual convergence history
65:# GOLD_OVERLAY_CASES get the full 5-renderer treatment (profile overlay + deviation
66:# + Plotly JSON + residuals + 2D contour). VISUAL_ONLY_CASES (Tier C per DEC-V61-034)
67:# get only contour + residuals — every case shows real OpenFOAM evidence even
70:GOLD_OVERLAY_CASES = frozenset({"lid_driven_cavity"})
71:VISUAL_ONLY_CASES = frozenset({
82:RENDER_SUPPORTED_CASES = GOLD_OVERLAY_CASES | VISUAL_ONLY_CASES
156:def _load_residuals_csv(path: Path) -> tuple[np.ndarray, dict[str, np.ndarray]]:
157:    """Load residuals.csv written by _capture_field_artifacts.
164:        raise RenderError(f"empty residuals: {path}")
167:        raise RenderError(f"unexpected residuals header: {header}")
181:                data[f].append(float("nan"))
186:                    data[f].append(float("nan"))
312:def _parse_residuals_from_log(log_path: Path) -> tuple[np.ndarray, dict[str, np.ndarray]]:
313:    """Fallback: parse initial residuals per iteration out of the solver log.
315:    Tier C (DEC-V61-034) — when the `residuals` functionObject was not emitted
317:    writes one `Solving for X, Initial residual = <val>, ...` line per field
319:    gets a residuals plot regardless of controlDict shape.
327:    iter_re = re.compile(r"^Time\s*=\s*([0-9.eE+\-]+)s?\s*$", re.MULTILINE)
328:    # Per-field lines: `Solving for Ux, Initial residual = 1.23e-05, ...`
330:        r"Solving for (\w+), Initial residual = ([0-9.eE+\-]+)"
336:    time_matches = list(iter_re.finditer(text))
351:                # Only record the FIRST Initial residual per field per iter
368:        series = np.array([fd.get(f, np.nan) for _, fd in per_iter], dtype=float)
381:def render_residuals_png(
386:    """Matplotlib PNG: log-y residual convergence for Ux, Uy, p (+ T, k, epsilon for
389:    Prefers `residuals.csv` from the Phase 7a `residuals` functionObject. When
394:    csv = artifact_dir / "residuals.csv"
396:        iters, fields = _load_residuals_csv(csv)
401:                f"neither residuals.csv nor solver log found in {artifact_dir}"
403:        iters, fields = _parse_residuals_from_log(log_path)
417:        mask = np.isfinite(series) & (series > 0)
422:    ax.set_ylabel("Initial residual (log)")
423:    ax.set_title(f"{case_id} — solver residual convergence")
425:    out = renders_dir / "residuals.png"
545:    finite = np.isfinite(mag)
549:        vmax = float(np.nanpercentile(mag[finite], 99.0))
550:        if not np.isfinite(vmax) or vmax <= 0:
553:        Ux = np.where(np.isfinite(Ux), np.clip(Ux, -vmax, vmax), 0.0)
554:        Uy = np.where(np.isfinite(Uy), np.clip(Uy, -vmax, vmax), 0.0)
562:        cf = ax.tricontourf(triang, mag, levels=20, cmap="viridis")
564:        print(f"[render] [WARN] tricontourf failed ({e}); using scatter fallback",
581:    ax.set_title(f"{case_id} — |U| contour (unstructured tricontour + quiver)")
589:def _pick_2d_plane(
599:        arr = arr[np.isfinite(arr)]
622:    2. Unstructured: tricontourf on raw cell centroids + sparse quiver overlay —
646:            ax1, ax2, vel1, vel2, _, _ = _pick_2d_plane(Cx, Cy, Cz, U)
651:            # Fall through to unstructured tricontour.
687:def render_all(case_id: str, run_label: str = "audit_real_run") -> dict:
690:    GOLD_OVERLAY_CASES (LDC today) get the full 5-renderer treatment (profile
691:    vs gold, pointwise deviation, Plotly JSON, residuals, contour).
692:    VISUAL_ONLY_CASES (Tier C fan-out, DEC-V61-034) get just residuals +
706:    if case_id in GOLD_OVERLAY_CASES:
710:            ("residuals_png", render_residuals_png),
717:            ("residuals_png", render_residuals_png),
752:        render_all(args.case_id, args.run_label)

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
/bin/zsh -lc "nl -ba scripts/render_case_report.py | sed -n '1,220p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba ui/backend/tests/test_comparison_report_route.py | sed -n '1,240p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
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
    65	# GOLD_OVERLAY_CASES get the full 5-renderer treatment (profile overlay + deviation
    66	# + Plotly JSON + residuals + 2D contour). VISUAL_ONLY_CASES (Tier C per DEC-V61-034)
    67	# get only contour + residuals — every case shows real OpenFOAM evidence even
    68	# when per-case gold-overlay plumbing is not yet wired. RENDER_SUPPORTED_CASES is
    69	# the union (legacy name retained for test_audit_package_route.py references).
    70	GOLD_OVERLAY_CASES = frozenset({"lid_driven_cavity"})
    71	VISUAL_ONLY_CASES = frozenset({
    72	    "backward_facing_step",
    73	    "plane_channel_flow",
    74	    "turbulent_flat_plate",
    75	    "circular_cylinder_wake",
    76	    "impinging_jet",
    77	    "naca0012_airfoil",
    78	    "rayleigh_benard_convection",
    79	    "differential_heated_cavity",
    80	    "duct_flow",
    81	})
    82	RENDER_SUPPORTED_CASES = GOLD_OVERLAY_CASES | VISUAL_ONLY_CASES
    83	
    84	
    85	class RenderError(Exception):
    86	    """Non-fatal render failure — caller decides whether to abort the batch."""
    87	
    88	
    89	# ---------------------------------------------------------------------------
    90	# I/O helpers
    91	# ---------------------------------------------------------------------------
    92	
    93	
    94	def _resolve_run_timestamp(case_id: str, run_label: str) -> str:
    95	    """Read the per-run manifest written by phase5_audit_run.py and return its timestamp.
    96	
    97	    Codex round 1 HIGH: enforce _TIMESTAMP_RE shape on the manifest value so a
    98	    tampered manifest cannot steer downstream path composition outside
    99	    reports/phase5_fields/.
   100	    """
   101	    manifest_path = FIELDS_ROOT / case_id / "runs" / f"{run_label}.json"
   102	    if not manifest_path.is_file():
   103	        raise RenderError(f"no run manifest: {manifest_path}")
   104	    data = json.loads(manifest_path.read_text(encoding="utf-8"))
   105	    if not isinstance(data, dict):
   106	        raise RenderError(f"manifest not an object: {manifest_path}")
   107	    ts = data.get("timestamp")
   108	    if not isinstance(ts, str) or not _TIMESTAMP_RE.match(ts):
   109	        raise RenderError(f"invalid timestamp shape in manifest: {ts!r}")
   110	    return ts
   111	
   112	
   113	def _artifact_dir(case_id: str, timestamp: str) -> Path:
   114	    d = FIELDS_ROOT / case_id / timestamp
   115	    # Containment check even though timestamp is already shape-gated upstream.
   116	    try:
   117	        d.resolve(strict=True).relative_to((FIELDS_ROOT / case_id).resolve())
   118	    except (ValueError, OSError, FileNotFoundError):
   119	        raise RenderError(f"artifact dir escapes fields root: {d}")
   120	    if not d.is_dir():
   121	        raise RenderError(f"artifact dir missing: {d}")
   122	    return d
   123	
   124	
   125	def _renders_dir(case_id: str, timestamp: str) -> Path:
   126	    d = RENDERS_ROOT / case_id / timestamp
   127	    d.mkdir(parents=True, exist_ok=True)
   128	    return d
   129	
   130	
   131	def _load_sample_xy(path: Path) -> tuple[np.ndarray, np.ndarray]:
   132	    """Load OpenFOAM `sample` output (.xy file, whitespace-separated).
   133	
   134	    Column layout for uCenterline: y  U_x  U_y  U_z  p.
   135	    Returns (y, U_x). Skips header lines starting with '#'.
   136	    """
   137	    rows: list[list[float]] = []
   138	    for line in path.read_text(encoding="utf-8").splitlines():
   139	        s = line.strip()
   140	        if not s or s.startswith("#"):
   141	            continue
   142	        parts = s.split()
   143	        # Accept either 5 (y Ux Uy Uz p) or 2 (y Ux) column variants.
   144	        try:
   145	            y = float(parts[0])
   146	            ux = float(parts[1])
   147	        except (ValueError, IndexError):
   148	            continue
   149	        rows.append([y, ux])
   150	    if not rows:
   151	        raise RenderError(f"empty sample file: {path}")
   152	    arr = np.array(rows)
   153	    return arr[:, 0], arr[:, 1]
   154	
   155	
   156	def _load_residuals_csv(path: Path) -> tuple[np.ndarray, dict[str, np.ndarray]]:
   157	    """Load residuals.csv written by _capture_field_artifacts.
   158	
   159	    Format: Time,Ux,Uy,p  — first data row may be "N/A" for iter 0.
   160	    Returns (iterations, {field_name: array}).
   161	    """
   162	    raw = path.read_text(encoding="utf-8").splitlines()
   163	    if not raw:
   164	        raise RenderError(f"empty residuals: {path}")
   165	    header = [c.strip() for c in raw[0].split(",")]
   166	    if header[0].lower() not in ("time", "iter", "iteration"):
   167	        raise RenderError(f"unexpected residuals header: {header}")
   168	    fields = header[1:]
   169	    iters: list[int] = []
   170	    data: dict[str, list[float]] = {f: [] for f in fields}
   171	    for line in raw[1:]:
   172	        parts = [c.strip() for c in line.split(",")]
   173	        if len(parts) != len(header):
   174	            continue
   175	        try:
   176	            iters.append(int(float(parts[0])))
   177	        except ValueError:
   178	            continue
   179	        for f, v in zip(fields, parts[1:]):
   180	            if v.upper() == "N/A" or v == "":
   181	                data[f].append(float("nan"))
   182	            else:
   183	                try:
   184	                    data[f].append(float(v))
   185	                except ValueError:
   186	                    data[f].append(float("nan"))
   187	    return np.array(iters), {k: np.array(v) for k, v in data.items()}
   188	
   189	
   190	def _load_gold_ldc() -> tuple[list[float], list[float], str]:
   191	    """Return (y_points, u_values, citation) from knowledge/gold_standards/lid_driven_cavity.yaml.
   192	
   193	    File is multi-document YAML (u_centerline, v_centerline, primary_vortex_location).
   194	    Iterate safe_load_all and pick the u_centerline document.
   195	    """
   196	    gold = GOLD_ROOT / "lid_driven_cavity.yaml"
   197	    if not gold.is_file():
   198	        raise RenderError(f"gold file missing: {gold}")
   199	    docs = list(yaml.safe_load_all(gold.read_text(encoding="utf-8")))
   200	    u_doc = next(
   201	        (d for d in docs if isinstance(d, dict) and d.get("quantity") == "u_centerline"),
   202	        None,
   203	    )
   204	    if u_doc is None:
   205	        raise RenderError("no quantity: u_centerline doc in LDC gold YAML")
   206	    refs = u_doc.get("reference_values", [])
   207	    ys: list[float] = []
   208	    us: list[float] = []
   209	    for entry in refs:
   210	        if isinstance(entry, dict):
   211	            y = entry.get("y")
   212	            u = entry.get("value") or entry.get("u")
   213	            if y is not None and u is not None:
   214	                ys.append(float(y))
   215	                us.append(float(u))
   216	    citation = u_doc.get("source") or u_doc.get("citation") or \
   217	        "Ghia, Ghia & Shin 1982 J. Comput. Phys. 47, 387-411 — Table I Re=100"
   218	    return ys, us, citation
   219	
   220	

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
   182	
   183	
   184	def test_pdf_get_returns_503_on_oserror(_synth_route_tree, monkeypatch) -> None:
   185	    """Codex round 3: GET .../comparison-report.pdf must map OSError → 503."""
   186	    from ui.backend.routes import comparison_report as route_mod
   187	
   188	    def _raise_oserror(*a, **kw):
   189	        raise OSError("libpango missing (synthetic)")
   190	
   191	    monkeypatch.setattr(route_mod, "render_report_pdf", _raise_oserror)
   192	    r = client.get(
   193	        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report.pdf",
   194	    )
   195	    assert r.status_code == 503, r.text
   196	    assert "WeasyPrint unavailable" in r.json().get("detail", "")
   197	
   198	
   199	def test_pdf_build_post_returns_503_on_oserror(_synth_route_tree, monkeypatch) -> None:
   200	    """Codex round 3 MED follow-up: POST .../comparison-report/build must ALSO
   201	    map OSError → 503. Previously it returned 500 on native lib load failure."""
   202	    from ui.backend.routes import comparison_report as route_mod
   203	
   204	    def _raise_oserror(*a, **kw):
   205	        raise OSError("libpango missing (synthetic)")
   206	
   207	    monkeypatch.setattr(route_mod, "render_report_pdf", _raise_oserror)
   208	    r = client.post(
   209	        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report/build",
   210	    )
   211	    assert r.status_code == 503, r.text
   212	    assert "WeasyPrint unavailable" in r.json().get("detail", "")

exec
/bin/zsh -lc "nl -ba scripts/render_case_report.py | sed -n '520,735p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba scripts/render_case_report.py | sed -n '300,440p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   520	    cbar.set_label("|U|")
   521	    fig.savefig(out)
   522	    plt.close(fig)
   523	    return out
   524	
   525	
   526	def _render_unstructured_contour(
   527	    case_id: str, Ux: np.ndarray, Uy: np.ndarray, Cx: np.ndarray, Cy: np.ndarray,
   528	    out: Path,
   529	) -> Path:
   530	    """Robust fallback for unstructured / non-square meshes (BFS, cylinder wake,
   531	    airfoil, impinging jet, channel, etc.). Uses matplotlib.tri.Triangulation on
   532	    the raw cell-centroid cloud to render a filled |U| contour. Streamlines are
   533	    skipped (they need a regular grid); instead, a sparse velocity-arrow overlay
   534	    gives a sense of the vector field.
   535	
   536	    Handles divergent / diverged solutions robustly: clips |U| to a finite
   537	    percentile range so matplotlib doesn't choke on inf / extreme values
   538	    (common when a solver fails to converge and emits garbage last-iter fields).
   539	    """
   540	    import matplotlib.tri as mtri
   541	    with np.errstate(over="ignore", invalid="ignore"):
   542	        mag = np.sqrt(Ux ** 2 + Uy ** 2)
   543	    # Replace non-finite with 0 for triangulation + clip the tail at the 99th
   544	    # percentile of finite values so one runaway cell doesn't saturate colormap.
   545	    finite = np.isfinite(mag)
   546	    if not finite.any():
   547	        mag = np.zeros_like(mag)
   548	    else:
   549	        vmax = float(np.nanpercentile(mag[finite], 99.0))
   550	        if not np.isfinite(vmax) or vmax <= 0:
   551	            vmax = 1.0
   552	        mag = np.where(finite, np.clip(mag, 0.0, vmax), 0.0)
   553	        Ux = np.where(np.isfinite(Ux), np.clip(Ux, -vmax, vmax), 0.0)
   554	        Uy = np.where(np.isfinite(Uy), np.clip(Uy, -vmax, vmax), 0.0)
   555	    fig, ax = plt.subplots(figsize=(7.5, 5.5))
   556	    # Attempt Delaunay triangulation; qhull fails on degenerate/collinear
   557	    # geometries (e.g. NACA0012 after a solver divergence — all cells end up
   558	    # at boundary or coincident). Fall through to scatter on failure.
   559	    cf = None
   560	    try:
   561	        triang = mtri.Triangulation(Cx, Cy)
   562	        cf = ax.tricontourf(triang, mag, levels=20, cmap="viridis")
   563	    except Exception as e:
   564	        print(f"[render] [WARN] tricontourf failed ({e}); using scatter fallback",
   565	              file=sys.stderr)
   566	    if cf is None:
   567	        # Plain scatter-mag map — always works, no triangulation.
   568	        cf = ax.scatter(Cx, Cy, c=mag, s=8, cmap="viridis", edgecolors="none")
   569	    # Sparse quiver: ~40 arrows on a decimated lattice so large meshes stay readable.
   570	    n = len(Cx)
   571	    stride = max(1, int(np.sqrt(n) / 8))
   572	    idx = np.arange(0, n, stride)
   573	    ax.quiver(
   574	        Cx[idx], Cy[idx], Ux[idx], Uy[idx],
   575	        color="white", alpha=0.8, scale=None, width=0.0025,
   576	        headwidth=3.5, headlength=4.0,
   577	    )
   578	    ax.set_aspect("equal")
   579	    ax.set_xlabel("x [m]")
   580	    ax.set_ylabel("y [m]")
   581	    ax.set_title(f"{case_id} — |U| contour (unstructured tricontour + quiver)")
   582	    cbar = fig.colorbar(cf, ax=ax, fraction=0.03, pad=0.02)
   583	    cbar.set_label("|U| [m/s]")
   584	    fig.savefig(out)
   585	    plt.close(fig)
   586	    return out
   587	
   588	
   589	def _pick_2d_plane(
   590	    Cx: np.ndarray, Cy: np.ndarray, Cz: np.ndarray, U: np.ndarray,
   591	) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, str, str]:
   592	    """Return (axis1, axis2, vel1, vel2, label1, label2) for the 2D plane with
   593	    non-degenerate coordinate variance. Pseudo-2D CFD cases are typically one
   594	    cell thick in ONE of {x, y, z}; pick the two non-degenerate axes.
   595	
   596	    Fallback: (Cx, Cy) if all three look non-degenerate.
   597	    """
   598	    def _span(arr: np.ndarray) -> float:
   599	        arr = arr[np.isfinite(arr)]
   600	        if arr.size == 0:
   601	            return 0.0
   602	        return float(arr.max() - arr.min())
   603	
   604	    spans = [(_span(Cx), "x", Cx, U[:, 0]),
   605	             (_span(Cy), "y", Cy, U[:, 1]),
   606	             (_span(Cz), "z", Cz, U[:, 2])]
   607	    # Sort descending; pick the top two.
   608	    spans.sort(key=lambda s: s[0], reverse=True)
   609	    (_, l1, c1, v1), (_, l2, c2, v2) = spans[0], spans[1]
   610	    return c1, c2, v1, v2, l1, l2
   611	
   612	
   613	def render_contour_u_magnitude_png(
   614	    case_id: str,
   615	    artifact_dir: Path,
   616	    renders_dir: Path,
   617	) -> Path:
   618	    """2D U-magnitude contour from the real VTK volume.
   619	
   620	    Three-tier rendering path (tries each, falls through on failure):
   621	    1. Structured grid: LDC-style square mesh → contourf + streamplot (publication quality).
   622	    2. Unstructured: tricontourf on raw cell centroids + sparse quiver overlay —
   623	       works for BFS, cylinder wake, airfoil, impinging jet, channel, etc.
   624	    3. Scatter: final fallback when Delaunay triangulation fails (e.g. NACA0012
   625	       after solver divergence → singular/collinear geometry).
   626	
   627	    Auto-detects the 2D plane — not all cases are in the x-y plane (NACA0012
   628	    uses x-z, some use y-z); picks the two axes with non-degenerate variance.
   629	    """
   630	    out = renders_dir / "contour_u_magnitude.png"
   631	    vtk_path = _find_latest_vtk(artifact_dir)
   632	    if vtk_path is not None:
   633	        try:
   634	            import pyvista as pv
   635	            pv.OFF_SCREEN = True
   636	            mesh = pv.read(str(vtk_path))
   637	            cd = mesh.cell_data
   638	            if "U" not in cd or "Cx" not in cd or "Cy" not in cd:
   639	                raise RenderError(f"VTK missing U/Cx/Cy: {vtk_path}")
   640	            U = np.asarray(cd["U"])
   641	            Cx = np.asarray(cd["Cx"])
   642	            Cy = np.asarray(cd["Cy"])
   643	            Cz = np.asarray(cd["Cz"]) if "Cz" in cd else np.zeros_like(Cx)
   644	            # Auto-pick the 2D plane with non-degenerate variance so that
   645	            # cases meshed in x-z (NACA0012) or y-z still produce a contour.
   646	            ax1, ax2, vel1, vel2, _, _ = _pick_2d_plane(Cx, Cy, Cz, U)
   647	            # Try structured-grid path first (fast, publication-style).
   648	            result = _render_structured_contour(case_id, vel1, vel2, ax1, ax2, out)
   649	            if result is not None:
   650	                return result
   651	            # Fall through to unstructured tricontour.
   652	            return _render_unstructured_contour(case_id, vel1, vel2, ax1, ax2, out)
   653	        except Exception as e:  # noqa: BLE001 — try minimal fallback
   654	            print(f"[render] [WARN] VTK contour failed ({e}); trying sample-strip fallback",
   655	                  file=sys.stderr)
   656	
   657	    # Minimal fallback — only works if sample/{iter}/uCenterline.xy exists
   658	    # (LDC-only). Other cases without VTK or sample will raise.
   659	    try:
   660	        latest = _latest_sample_iter(artifact_dir)
   661	        y_sim, u_sim = _load_sample_xy(latest / "uCenterline.xy")
   662	    except Exception as e:  # noqa: BLE001
   663	        raise RenderError(f"no VTK and no sample fallback available: {e}")
   664	    y_norm = y_sim / max(y_sim.max(), 1e-12)
   665	    fig, ax = plt.subplots(figsize=(4, 6))
   666	    strip = np.tile(u_sim.reshape(-1, 1), (1, 20))
   667	    im = ax.imshow(
   668	        strip, aspect="auto", origin="lower",
   669	        extent=[0, 1, float(y_norm.min()), float(y_norm.max())],
   670	        cmap="RdBu_r", vmin=-1.0, vmax=1.0,
   671	    )
   672	    ax.set_xlabel("(tile axis)")
   673	    ax.set_ylabel("y / L")
   674	    ax.set_title(f"{case_id} — centerline slice (VTK parse failed, MVP fallback)")
   675	    cbar = fig.colorbar(im, ax=ax, fraction=0.08, pad=0.04)
   676	    cbar.set_label("U_x")
   677	    fig.savefig(out)
   678	    plt.close(fig)
   679	    return out
   680	
   681	
   682	# ---------------------------------------------------------------------------
   683	# Orchestration
   684	# ---------------------------------------------------------------------------
   685	
   686	
   687	def render_all(case_id: str, run_label: str = "audit_real_run") -> dict:
   688	    """Render figures for a given case/run. Returns {name: path, ...}.
   689	
   690	    GOLD_OVERLAY_CASES (LDC today) get the full 5-renderer treatment (profile
   691	    vs gold, pointwise deviation, Plotly JSON, residuals, contour).
   692	    VISUAL_ONLY_CASES (Tier C fan-out, DEC-V61-034) get just residuals +
   693	    contour — real OpenFOAM evidence without requiring per-case gold-overlay
   694	    plumbing.
   695	    """
   696	    if case_id not in RENDER_SUPPORTED_CASES:
   697	        raise RenderError(
   698	            f"case_id={case_id!r} not opted-in for Phase 7b rendering. "
   699	            f"Supported: {sorted(RENDER_SUPPORTED_CASES)}."
   700	        )
   701	    timestamp = _resolve_run_timestamp(case_id, run_label)
   702	    artifact_dir = _artifact_dir(case_id, timestamp)
   703	    renders_dir = _renders_dir(case_id, timestamp)
   704	
   705	    outputs: dict[str, Path] = {}
   706	    if case_id in GOLD_OVERLAY_CASES:
   707	        renderers = [
   708	            ("profile_png", render_profile_png),
   709	            ("profile_plotly_json", render_profile_plotly_json),
   710	            ("residuals_png", render_residuals_png),
   711	            ("pointwise_deviation_png", render_pointwise_deviation_png),
   712	            ("contour_u_magnitude_png", render_contour_u_magnitude_png),
   713	        ]
   714	    else:
   715	        # Tier C — visual-only mode.
   716	        renderers = [
   717	            ("residuals_png", render_residuals_png),
   718	            ("contour_u_magnitude_png", render_contour_u_magnitude_png),
   719	        ]
   720	    errors: dict[str, str] = {}
   721	    for name, fn in renderers:
   722	        try:
   723	            outputs[name] = fn(case_id, artifact_dir, renders_dir)
   724	        except Exception as e:  # noqa: BLE001  — keep batch alive
   725	            errors[name] = f"{type(e).__name__}: {e}"
   726	            print(f"[render] [WARN] {name} failed: {e}", file=sys.stderr)
   727	
   728	    # Write per-run renders manifest (mirrors phase5_fields/{case}/runs/{label}.json).
   729	    manifest_dir = RENDERS_ROOT / case_id / "runs"
   730	    manifest_dir.mkdir(parents=True, exist_ok=True)
   731	    manifest = {
   732	        "case_id": case_id,
   733	        "run_label": run_label,
   734	        "timestamp": timestamp,
   735	        "renders_dir_rel": str(renders_dir.relative_to(REPO_ROOT)),

 succeeded in 0ms:
   300	        yaxis_title="y / L",
   301	        template="plotly_white",
   302	        hovermode="closest",
   303	        margin=dict(l=50, r=20, t=50, b=50),
   304	    )
   305	    # Static JSON (no widget state). include_plotlyjs='cdn' on frontend side.
   306	    payload = fig.to_json()
   307	    out = renders_dir / "profile_u_centerline.plotly.json"
   308	    out.write_text(payload, encoding="utf-8")
   309	    return out
   310	
   311	
   312	def _parse_residuals_from_log(log_path: Path) -> tuple[np.ndarray, dict[str, np.ndarray]]:
   313	    """Fallback: parse initial residuals per iteration out of the solver log.
   314	
   315	    Tier C (DEC-V61-034) — when the `residuals` functionObject was not emitted
   316	    into controlDict (case generators that pre-date Phase 7a), OpenFOAM still
   317	    writes one `Solving for X, Initial residual = <val>, ...` line per field
   318	    per iteration into the solver log. Extract by regex so every captured run
   319	    gets a residuals plot regardless of controlDict shape.
   320	    """
   321	    if not log_path.is_file():
   322	        raise RenderError(f"solver log missing: {log_path}")
   323	    text = log_path.read_text(encoding="utf-8", errors="replace")
   324	    # Iteration boundaries marked by `Time = <iter>` or `Time = <iter>s` lines.
   325	    # simpleFoam / buoyantFoam steady-state writes `Time = 35s`; pimpleFoam
   326	    # transient writes `Time = 0.0125`. Accept both forms.
   327	    iter_re = re.compile(r"^Time\s*=\s*([0-9.eE+\-]+)s?\s*$", re.MULTILINE)
   328	    # Per-field lines: `Solving for Ux, Initial residual = 1.23e-05, ...`
   329	    solving_re = re.compile(
   330	        r"Solving for (\w+), Initial residual = ([0-9.eE+\-]+)"
   331	    )
   332	    # Walk the log sequentially; for each `Time = N` marker, collect all
   333	    # `Solving for X` lines up to the next marker.
   334	    per_iter: list[tuple[float, dict[str, float]]] = []
   335	    pos = 0
   336	    time_matches = list(iter_re.finditer(text))
   337	    if not time_matches:
   338	        raise RenderError(f"no 'Time =' markers in solver log: {log_path}")
   339	    for i, m in enumerate(time_matches):
   340	        try:
   341	            t = float(m.group(1))
   342	        except ValueError:
   343	            continue
   344	        start = m.end()
   345	        end = time_matches[i + 1].start() if i + 1 < len(time_matches) else len(text)
   346	        seg = text[start:end]
   347	        field_data: dict[str, float] = {}
   348	        for sm in solving_re.finditer(seg):
   349	            field, val = sm.group(1), sm.group(2)
   350	            try:
   351	                # Only record the FIRST Initial residual per field per iter
   352	                # (simpleFoam solves a field once per iteration).
   353	                if field not in field_data:
   354	                    field_data[field] = float(val)
   355	            except ValueError:
   356	                pass
   357	        if field_data:
   358	            per_iter.append((t, field_data))
   359	    if not per_iter:
   360	        raise RenderError(f"no 'Solving for X' lines in solver log: {log_path}")
   361	    iters = np.array([t for t, _ in per_iter])
   362	    # Collect union of field names; pad missing entries with NaN.
   363	    all_fields: set[str] = set()
   364	    for _, fd in per_iter:
   365	        all_fields.update(fd.keys())
   366	    fields: dict[str, np.ndarray] = {}
   367	    for f in sorted(all_fields):
   368	        series = np.array([fd.get(f, np.nan) for _, fd in per_iter], dtype=float)
   369	        fields[f] = series
   370	    return iters, fields
   371	
   372	
   373	def _find_latest_solver_log(artifact_dir: Path) -> Optional[Path]:
   374	    for logname in ("log.simpleFoam", "log.icoFoam", "log.pimpleFoam", "log.buoyantFoam"):
   375	        p = artifact_dir / logname
   376	        if p.is_file():
   377	            return p
   378	    return None
   379	
   380	
   381	def render_residuals_png(
   382	    case_id: str,
   383	    artifact_dir: Path,
   384	    renders_dir: Path,
   385	) -> Path:
   386	    """Matplotlib PNG: log-y residual convergence for Ux, Uy, p (+ T, k, epsilon for
   387	    turbulent / buoyant cases).
   388	
   389	    Prefers `residuals.csv` from the Phase 7a `residuals` functionObject. When
   390	    that file is absent (cases whose generator does not yet emit the
   391	    functionObject block), falls back to parsing the solver log — every
   392	    captured run has a log, so the plot is always renderable.
   393	    """
   394	    csv = artifact_dir / "residuals.csv"
   395	    if csv.is_file():
   396	        iters, fields = _load_residuals_csv(csv)
   397	    else:
   398	        log_path = _find_latest_solver_log(artifact_dir)
   399	        if log_path is None:
   400	            raise RenderError(
   401	                f"neither residuals.csv nor solver log found in {artifact_dir}"
   402	            )
   403	        iters, fields = _parse_residuals_from_log(log_path)
   404	
   405	    fig, ax = plt.subplots()
   406	    # Fixed palette for common fields; auto-assign from Tab10 for any others
   407	    # (k, epsilon, omega, T, alphat, h, nut) so buoyant/turbulent cases plot.
   408	    palette = {
   409	        "Ux": "#1f77b4", "Uy": "#2ca02c", "Uz": "#17becf",
   410	        "p": "#d62728", "p_rgh": "#ff7f0e", "T": "#9467bd",
   411	        "k": "#8c564b", "epsilon": "#e377c2", "omega": "#bcbd22",
   412	    }
   413	    tab_fallback = plt.cm.tab10.colors
   414	    for i, (name, series) in enumerate(sorted(fields.items())):
   415	        color = palette.get(name, tab_fallback[i % len(tab_fallback)])
   416	        # Use NaN-safe masking so iter-0 'N/A' doesn't break log plot.
   417	        mask = np.isfinite(series) & (series > 0)
   418	        if mask.sum() == 0:
   419	            continue
   420	        ax.semilogy(iters[mask], series[mask], color=color, label=name)
   421	    ax.set_xlabel("Iteration")
   422	    ax.set_ylabel("Initial residual (log)")
   423	    ax.set_title(f"{case_id} — solver residual convergence")
   424	    ax.legend(loc="upper right", frameon=False, fontsize=9)
   425	    out = renders_dir / "residuals.png"
   426	    fig.savefig(out)
   427	    plt.close(fig)
   428	    return out
   429	
   430	
   431	def render_pointwise_deviation_png(
   432	    case_id: str,
   433	    artifact_dir: Path,
   434	    renders_dir: Path,
   435	) -> Path:
   436	    """Bar chart of |dev|% per gold sample point (sim interpolated onto gold y-grid)."""
   437	    latest = _latest_sample_iter(artifact_dir)
   438	    y_sim, u_sim = _load_sample_xy(latest / "uCenterline.xy")
   439	    y_sim_norm = y_sim / max(y_sim.max(), 1e-12)
   440	

exec
/bin/zsh -lc "nl -ba scripts/phase5_audit_run.py | sed -n '1,180p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
     1	"""Phase 5a audit-run driver — runs a case via FoamAgentExecutor and writes
     2	a deterministic audit fixture into fixtures/runs/{case_id}/audit_real_run_measurement.yaml.
     3	
     4	Usage (from repo root):
     5	    EXECUTOR_MODE=foam_agent \\
     6	    .venv/bin/python scripts/phase5_audit_run.py <case_id> [<case_id>...]
     7	
     8	    # all cases:
     9	    EXECUTOR_MODE=foam_agent \\
    10	    .venv/bin/python scripts/phase5_audit_run.py --all
    11	
    12	Output:
    13	    ui/backend/tests/fixtures/runs/{case_id}/audit_real_run_measurement.yaml
    14	    reports/phase5_audit/{timestamp}_{case_id}_raw_run.json  (stdout/stderr)
    15	
    16	Determinism:
    17	    Timestamp + commit_sha are the only non-deterministic fields; tests use
    18	    an `allowed_nondeterminism` set to strip them before byte-comparison.
    19	    Numeric values from simpleFoam are deterministic given identical
    20	    mesh + schemes + fvSolution + initial conditions (we use steady-state
    21	    solvers for Phase 5a, no RNG). This property is enforced by
    22	    test_phase5_byte_repro.py.
    23	"""
    24	
    25	from __future__ import annotations
    26	
    27	import argparse
    28	import datetime
    29	import json
    30	import os
    31	import subprocess
    32	import sys
    33	import time
    34	from pathlib import Path
    35	
    36	import yaml
    37	
    38	REPO_ROOT = Path(__file__).resolve().parents[1]
    39	sys.path.insert(0, str(REPO_ROOT))
    40	
    41	from src.foam_agent_adapter import FoamAgentExecutor  # noqa: E402
    42	from src.task_runner import TaskRunner  # noqa: E402
    43	
    44	RUNS_DIR = REPO_ROOT / "ui" / "backend" / "tests" / "fixtures" / "runs"
    45	RAW_DIR = REPO_ROOT / "reports" / "phase5_audit"
    46	FIELDS_DIR = REPO_ROOT / "reports" / "phase5_fields"
    47	
    48	ALL_CASES = [
    49	    "lid_driven_cavity",
    50	    "backward_facing_step",
    51	    "circular_cylinder_wake",
    52	    "turbulent_flat_plate",
    53	    "duct_flow",
    54	    "differential_heated_cavity",
    55	    "plane_channel_flow",
    56	    "impinging_jet",
    57	    "naca0012_airfoil",
    58	    "rayleigh_benard_convection",
    59	]
    60	
    61	
    62	def _git_head_sha() -> str:
    63	    try:
    64	        out = subprocess.check_output(
    65	            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"], timeout=5
    66	        )
    67	        return out.decode().strip()[:7]
    68	    except Exception:
    69	        return "unknown"
    70	
    71	
    72	def _iso_now() -> str:
    73	    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    74	
    75	
    76	def _primary_scalar(report) -> tuple[str | None, float | None, str]:
    77	    comp = report.comparison_result
    78	    if comp is not None and comp.deviations:
    79	        first = comp.deviations[0]
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
   138	# DEC-V61-034 Tier C: opt in all 10 whitelist cases for Phase 7a field
   139	# capture. The executor's _capture_field_artifacts runs foamToVTK + stages
   140	# VTK / residuals / solver log for ANY case regardless of whether its
   141	# generator emits the controlDict functions{} block (residuals are
   142	# log-parsed in the renderer when the functionObject wasn't emitted).
   143	# LDC still gets the full gold-overlay report via its sample block; the
   144	# other 9 cases flow through Tier C visual-only rendering (contour + residuals).
   145	_PHASE7A_OPTED_IN: frozenset[str] = frozenset(ALL_CASES)
   146	
   147	
   148	def _audit_fixture_doc(
   149	    case_id: str,
   150	    report,
   151	    commit_sha: str,
   152	    field_artifacts_ref: "dict | None" = None,
   153	) -> dict:
   154	    quantity, value, source_note = _primary_scalar(report)
   155	    comp = report.comparison_result
   156	    passed = comp.passed if comp else False
   157	
   158	    verdict_hint = "PASS" if passed else "FAIL"
   159	
   160	    doc = {
   161	        "run_metadata": {
   162	            "run_id": "audit_real_run",
   163	            "label_zh": "真实 solver 审计运行",
   164	            "label_en": "Real solver audit run",
   165	            "description_zh": (
   166	                f"FoamAgentExecutor 驱动 OpenFOAM 实际跑出的结果（commit {commit_sha}）。"
   167	                "这是 audit package 背书的权威测量——不是合成 fixture。"
   168	                "失败的话说明 case 本身的 physics_contract 在当前 mesh 预算下无法满足，"
   169	                "不是 harness bug；会进入 audit_concerns 随包交付给审查方。"
   170	            ),
   171	            "category": "audit_real_run",
   172	            "expected_verdict": verdict_hint,
   173	        },
   174	        "case_id": case_id,
   175	        "source": "phase5_audit_run_foam_agent",
   176	        "measurement": {
   177	            "value": value if value is not None else 0.0,
   178	            "unit": "dimensionless",
   179	            "run_id": f"audit_{case_id}_{commit_sha}",
   180	            "commit_sha": commit_sha,

exec
/bin/zsh -lc "rg -n \"artifact_dir_rel|timestamp|reports/phase5_fields|phase7a|phase5_renders|audit_real_run\" scripts/phase5_audit_run.py src ui/backend -g '*.py'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
scripts/phase5_audit_run.py:2:a deterministic audit fixture into fixtures/runs/{case_id}/audit_real_run_measurement.yaml.
scripts/phase5_audit_run.py:13:    ui/backend/tests/fixtures/runs/{case_id}/audit_real_run_measurement.yaml
scripts/phase5_audit_run.py:14:    reports/phase5_audit/{timestamp}_{case_id}_raw_run.json  (stdout/stderr)
scripts/phase5_audit_run.py:94:def _phase7a_timestamp() -> str:
scripts/phase5_audit_run.py:95:    """Shared timestamp format — matches _write_raw_capture."""
scripts/phase5_audit_run.py:100:    case_id: str, run_label: str, timestamp: str
scripts/phase5_audit_run.py:102:    """Write reports/phase5_fields/{case_id}/runs/{run_label}.json so the
scripts/phase5_audit_run.py:103:    backend route can resolve run_label -> timestamp directory in O(1).
scripts/phase5_audit_run.py:110:    artifact_dir = FIELDS_DIR / case_id / timestamp
scripts/phase5_audit_run.py:130:        "timestamp": timestamp,
scripts/phase5_audit_run.py:132:        "artifact_dir_rel": str(artifact_dir.relative_to(REPO_ROOT)),
scripts/phase5_audit_run.py:162:            "run_id": "audit_real_run",
scripts/phase5_audit_run.py:171:            "category": "audit_real_run",
scripts/phase5_audit_run.py:222:    # Phase 7a — field artifacts reference (manifest path only; NO timestamps
scripts/phase5_audit_run.py:224:    # The manifest at the referenced path contains the timestamp.
scripts/phase5_audit_run.py:234:    out_path = case_dir / "audit_real_run_measurement.yaml"
scripts/phase5_audit_run.py:240:        "# re-runs (modulo timestamp + commit_sha) is enforced by\n"
scripts/phase5_audit_run.py:280:    # Phase 7a — author the single shared timestamp up front; the executor-side
scripts/phase5_audit_run.py:281:    # _capture_field_artifacts writes to reports/phase5_fields/{case_id}/{ts}/.
scripts/phase5_audit_run.py:284:    ts = _phase7a_timestamp()
scripts/phase5_audit_run.py:290:            spec.metadata["phase7a_timestamp"] = ts
scripts/phase5_audit_run.py:291:            spec.metadata["phase7a_case_id"] = case_id
scripts/phase5_audit_run.py:302:    run_label = "audit_real_run"
scripts/phase5_audit_run.py:313:            # Deliberately NO timestamp string here (byte-repro): resolve via manifest.
ui/backend/services/field_artifacts.py:3:Reads the per-run manifest at reports/phase5_fields/{case_id}/runs/{run_label}.json
ui/backend/services/field_artifacts.py:5:enumerates files in the pointed-to timestamp directory, and serves them via
ui/backend/services/field_artifacts.py:24:# Codex round 2 HIGH (2026-04-21): timestamp shape gate. The manifest is
ui/backend/services/field_artifacts.py:26:# timestamp='../../outside'). Require the exact YYYYMMDDTHHMMSSZ format the
ui/backend/services/field_artifacts.py:49:    """Override the reports/phase5_fields/ root (test-only hook)."""
ui/backend/services/field_artifacts.py:60:# so rapid-write timestamp collisions within a float's precision are avoided.
ui/backend/services/field_artifacts.py:114:    `timestamp` from the manifest and composed a path without validation,
ui/backend/services/field_artifacts.py:115:    letting a malicious manifest `timestamp='../../outside'` cause the
ui/backend/services/field_artifacts.py:116:    endpoint to enumerate + hash files outside reports/phase5_fields/.
ui/backend/services/field_artifacts.py:121:    - timestamp missing, wrong shape, or contains traversal markers
ui/backend/services/field_artifacts.py:123:    - artifact_dir.resolve() escapes reports/phase5_fields/{case_id}/
ui/backend/services/field_artifacts.py:132:    timestamp = manifest.get("timestamp", "")
ui/backend/services/field_artifacts.py:135:    if not isinstance(timestamp, str) or not _TIMESTAMP_RE.match(timestamp):
ui/backend/services/field_artifacts.py:142:    artifact_dir = root / case_id / timestamp
ui/backend/services/field_artifacts.py:156:    OR if the manifest's `timestamp` fails the shape/traversal gate."""
ui/backend/services/field_artifacts.py:164:    timestamp = manifest["timestamp"]  # guaranteed valid by resolver
ui/backend/services/field_artifacts.py:199:        timestamp=timestamp,
ui/backend/services/field_artifacts.py:230:    # timestamp-validated resolver. Download previously had its own checks;
ui/backend/services/comparison_report.py:4:- Phase 7a field artifacts at reports/phase5_fields/{case}/{ts}/
ui/backend/services/comparison_report.py:5:- Phase 7b rendered figures at reports/phase5_renders/{case}/{ts}/
ui/backend/services/comparison_report.py:32:# timestamp and artifact paths. Mirrors ui/backend/services/field_artifacts.py
ui/backend/services/comparison_report.py:34:# outside reports/phase5_fields/ or writes outside reports/phase5_reports/.
ui/backend/services/comparison_report.py:41:_RENDERS_ROOT = _REPO_ROOT / "reports" / "phase5_renders"
ui/backend/services/comparison_report.py:106:def _validated_timestamp(ts: Any) -> Optional[str]:
ui/backend/services/comparison_report.py:107:    """Codex round 1 HIGH: reject any manifest-supplied timestamp that doesn't
ui/backend/services/comparison_report.py:330:    case_id: str, run_label: str, timestamp: str, artifact_dir: Path,
ui/backend/services/comparison_report.py:338:    renders_dir = _RENDERS_ROOT / case_id / timestamp
ui/backend/services/comparison_report.py:376:        "timestamp": timestamp,
ui/backend/services/comparison_report.py:397:def build_report_context(case_id: str, run_label: str = "audit_real_run") -> dict:
ui/backend/services/comparison_report.py:406:    timestamp = _validated_timestamp(run_manifest.get("timestamp"))
ui/backend/services/comparison_report.py:407:    if timestamp is None:
ui/backend/services/comparison_report.py:409:            f"invalid timestamp in run manifest for {case_id}/{run_label}"
ui/backend/services/comparison_report.py:411:    artifact_dir = _FIELDS_ROOT / case_id / timestamp
ui/backend/services/comparison_report.py:424:        return _build_visual_only_context(case_id, run_label, timestamp, artifact_dir)
ui/backend/services/comparison_report.py:467:    # resolve inside reports/phase5_renders/ before being emitted into HTML.
ui/backend/services/comparison_report.py:469:    renders_dir = _RENDERS_ROOT / case_id / timestamp
ui/backend/services/comparison_report.py:512:        "timestamp": timestamp,
ui/backend/services/comparison_report.py:540:def render_report_html(case_id: str, run_label: str = "audit_real_run") -> str:
ui/backend/services/comparison_report.py:547:def render_report_pdf(case_id: str, run_label: str = "audit_real_run",
ui/backend/services/comparison_report.py:552:    We pass base_url=_REPO_ROOT so /reports/phase5_renders/... resolves correctly.
ui/backend/services/comparison_report.py:566:        ts = ctx["timestamp"]  # already validated by build_report_context
ui/backend/services/dashboard.py:72:            date=str(c.timestamp)[:10],
ui/backend/services/dashboard.py:80:        for c in sorted(decisions_snap.cards, key=lambda c: str(c.timestamp))
ui/backend/services/run_ids.py:41:    """Parse 'lid_driven_cavity__audit_real_run' → ('lid_driven_cavity', 'audit_real_run').
ui/backend/services/decisions.py:40:    timestamp: str
ui/backend/services/decisions.py:126:        timestamp=str(fm.get("timestamp") or path.stem[:10]),
ui/backend/services/validation_report.py:195:    "audit_real_run": 1,
src/foam_agent_adapter.py:603:            _phase7a_ts: Optional[str] = None
src/foam_agent_adapter.py:604:            _phase7a_cid: Optional[str] = None
src/foam_agent_adapter.py:607:                _phase7a_ts = _md.get("phase7a_timestamp")
src/foam_agent_adapter.py:608:                _phase7a_cid = _md.get("phase7a_case_id") or task_spec.name
src/foam_agent_adapter.py:610:                _phase7a_ts = None
src/foam_agent_adapter.py:611:            if _phase7a_ts and _phase7a_cid:
src/foam_agent_adapter.py:616:                    _phase7a_cid,
src/foam_agent_adapter.py:617:                    _phase7a_ts,
src/foam_agent_adapter.py:665:    def _emit_phase7a_function_objects(turbulence_model: str = "laminar") -> str:
src/foam_agent_adapter.py:863:            + self._emit_phase7a_function_objects(turbulence_model="laminar")
src/foam_agent_adapter.py:6885:        timestamp: str,
src/foam_agent_adapter.py:6904:        artifact_dir = repo_root / "reports" / "phase5_fields" / case_id / timestamp
ui/backend/tests/test_audit_package_route.py:240:    def test_audit_real_run_populates_measurement(self, client):
ui/backend/tests/test_audit_package_route.py:241:        """When run_id=audit_real_run, the manifest carries real solver data,
ui/backend/tests/test_audit_package_route.py:246:            "/api/cases/lid_driven_cavity/runs/audit_real_run/audit-package/build"
ui/backend/tests/test_audit_package_route.py:256:            f"audit_real_run must land a verdict; got {m.get('comparator_verdict')!r}"
ui/backend/tests/test_audit_package_route.py:266:        assert concerns, "audit_real_run should surface audit_concerns"
ui/backend/schemas/validation.py:27:    "audit_real_run",
ui/backend/schemas/validation.py:42:- audit_real_run: a measurement produced by an actual OpenFOAM solver run
ui/backend/schemas/validation.py:45:  artifacts preserved for decision traceability, audit_real_run are the
ui/backend/schemas/validation.py:215:Phase 7a captures these per audit_real_run; Phase 7b renders them to PNG/HTML.
ui/backend/schemas/validation.py:246:    timestamp: str = Field(
src/models.py:81:    # driver-authored `phase7a_timestamp` (and `phase7a_case_id`) so
src/models.py:83:    # artifacts into reports/phase5_fields/{case_id}/{timestamp}/ before the
ui/backend/tests/test_comparison_report_route.py:15:# These tests run against the real reports/phase5_fields/lid_driven_cavity/
ui/backend/tests/test_comparison_report_route.py:22:    manifest = Path("reports/phase5_fields/lid_driven_cavity/runs/audit_real_run.json")
ui/backend/tests/test_comparison_report_route.py:29:    r = client.get("/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report")
ui/backend/tests/test_comparison_report_route.py:51:        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report/context",
ui/backend/tests/test_comparison_report_route.py:56:    assert d["run_label"] == "audit_real_run"
ui/backend/tests/test_comparison_report_route.py:63:    r = client.get("/api/cases/nonexistent_case/runs/audit_real_run/comparison-report")
ui/backend/tests/test_comparison_report_route.py:68:    r = client.get("/api/cases/..__pwn/runs/audit_real_run/comparison-report")
ui/backend/tests/test_comparison_report_route.py:79:        "/api/cases/%2e%2e__pwn/runs/audit_real_run/comparison-report/context",
ui/backend/tests/test_comparison_report_route.py:99:    renders_root = tmp_path / "reports" / "phase5_renders"
ui/backend/tests/test_comparison_report_route.py:109:    (fields_root / case / "runs" / "audit_real_run.json").write_text(
ui/backend/tests/test_comparison_report_route.py:110:        json.dumps({"timestamp": ts, "case_id": case, "run_label": "audit_real_run"}),
ui/backend/tests/test_comparison_report_route.py:118:    (renders_root / case / "runs" / "audit_real_run.json").write_text(
ui/backend/tests/test_comparison_report_route.py:120:            "case_id": case, "run_label": "audit_real_run", "timestamp": ts,
ui/backend/tests/test_comparison_report_route.py:122:                "profile_png": f"reports/phase5_renders/{case}/{ts}/profile_u_centerline.png",
ui/backend/tests/test_comparison_report_route.py:123:                "pointwise_deviation_png": f"reports/phase5_renders/{case}/{ts}/pointwise_deviation.png",
ui/backend/tests/test_comparison_report_route.py:124:                "contour_u_magnitude_png": f"reports/phase5_renders/{case}/{ts}/contour_u_magnitude.png",
ui/backend/tests/test_comparison_report_route.py:125:                "residuals_png": f"reports/phase5_renders/{case}/{ts}/residuals.png",
ui/backend/tests/test_comparison_report_route.py:163:        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report",
ui/backend/tests/test_comparison_report_route.py:175:        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report/context",
ui/backend/tests/test_comparison_report_route.py:180:    assert d["timestamp"] == "20260421T000000Z"
ui/backend/tests/test_comparison_report_route.py:193:        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report.pdf",
ui/backend/tests/test_comparison_report_route.py:209:        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report/build",
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
ui/backend/schemas/audit_package.py:56:            "value is an opaque hash, not a wall-clock timestamp, so the "
ui/backend/schemas/decisions.py:17:    timestamp: str
ui/backend/tests/test_field_artifacts_route.py:4:ui/backend/tests/fixtures/phase7a_sample_fields/ via
ui/backend/tests/test_field_artifacts_route.py:18:_FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "phase7a_sample_fields"
ui/backend/tests/test_field_artifacts_route.py:19:_RUN_ID = "lid_driven_cavity__audit_real_run"
ui/backend/tests/test_field_artifacts_route.py:42:    assert body["run_label"] == "audit_real_run"
ui/backend/tests/test_field_artifacts_route.py:43:    assert body["timestamp"] == "20260421T000000Z"
ui/backend/tests/test_field_artifacts_route.py:151:    (case_dir / "runs" / "audit_real_run.json").write_text(
ui/backend/tests/test_field_artifacts_route.py:177:    (fields_root / "lid_driven_cavity" / "runs" / "audit_real_run.json").write_text(
ui/backend/tests/test_field_artifacts_route.py:178:        json.dumps({"timestamp": "20260421T000000Z",
ui/backend/tests/test_field_artifacts_route.py:180:                    "run_label": "audit_real_run"}), encoding="utf-8",
ui/backend/tests/test_field_artifacts_route.py:195:def test_list_rejects_malicious_manifest_timestamp(tmp_path: Path) -> None:
ui/backend/tests/test_field_artifacts_route.py:197:    timestamp='../../outside' must NOT cause the LIST endpoint to enumerate
ui/backend/tests/test_field_artifacts_route.py:198:    files outside reports/phase5_fields/. Previously download path was
ui/backend/tests/test_field_artifacts_route.py:210:    (case_dir / "runs" / "audit_real_run.json").write_text(
ui/backend/tests/test_field_artifacts_route.py:211:        json.dumps({"timestamp": "../../outside", "case_id": "lid_driven_cavity",
ui/backend/tests/test_field_artifacts_route.py:212:                    "run_label": "audit_real_run"}),
ui/backend/tests/test_field_artifacts_route.py:219:        # Must NOT return 200 with the leaked artifact — timestamp shape gate.
ui/backend/routes/audit_package.py:178:    # wall-clock timestamp but got an opaque 16-hex token.
ui/backend/routes/audit_package.py:184:    # Phase 5a: when run_id identifies an audit_real_run measurement (captured
ui/backend/tests/test_comparison_report_visual_only.py:8:- Tampered run-manifest timestamp is rejected (404)
ui/backend/tests/test_comparison_report_visual_only.py:32:    repo_root: Path, case_id: str, timestamp: str = "20260101T000000Z",
ui/backend/tests/test_comparison_report_visual_only.py:38:    renders_dir = repo_root / "reports" / "phase5_renders" / case_id
ui/backend/tests/test_comparison_report_visual_only.py:39:    artifact_dir = fields_dir / timestamp
ui/backend/tests/test_comparison_report_visual_only.py:40:    render_ts_dir = renders_dir / timestamp
ui/backend/tests/test_comparison_report_visual_only.py:44:    (fields_dir / "runs" / "audit_real_run.json").write_text(
ui/backend/tests/test_comparison_report_visual_only.py:46:            "run_label": "audit_real_run",
ui/backend/tests/test_comparison_report_visual_only.py:47:            "timestamp": timestamp,
ui/backend/tests/test_comparison_report_visual_only.py:49:            "artifact_dir_rel": str(artifact_dir.relative_to(repo_root)),
ui/backend/tests/test_comparison_report_visual_only.py:57:    (renders_dir / "runs" / "audit_real_run.json").write_text(
ui/backend/tests/test_comparison_report_visual_only.py:59:            "run_label": "audit_real_run",
ui/backend/tests/test_comparison_report_visual_only.py:60:            "timestamp": timestamp,
ui/backend/tests/test_comparison_report_visual_only.py:64:                    f"reports/phase5_renders/{case_id}/{timestamp}/contour_u_magnitude.png",
ui/backend/tests/test_comparison_report_visual_only.py:66:                    f"reports/phase5_renders/{case_id}/{timestamp}/residuals.png",
ui/backend/tests/test_comparison_report_visual_only.py:95:        tmp_path / "reports" / "phase5_renders",
ui/backend/tests/test_comparison_report_visual_only.py:101:    ctx = build_report_context(case, "audit_real_run")
ui/backend/tests/test_comparison_report_visual_only.py:104:    assert ctx["run_label"] == "audit_real_run"
ui/backend/tests/test_comparison_report_visual_only.py:117:        "/api/cases/totally_unknown_case/runs/audit_real_run/comparison-report/context",
ui/backend/tests/test_comparison_report_visual_only.py:125:        "/api/cases/backward_facing_step/runs/audit_real_run/renders/..%2F..%2F..%2Fetc%2Fpasswd",
ui/backend/tests/test_comparison_report_visual_only.py:142:def test_visual_only_context_rejects_tampered_timestamp(tmp_path, monkeypatch) -> None:
ui/backend/tests/test_comparison_report_visual_only.py:143:    """Run manifest with timestamp='../../etc' is rejected by _validated_timestamp."""
ui/backend/tests/test_comparison_report_visual_only.py:147:    (fields_dir / "runs" / "audit_real_run.json").write_text(
ui/backend/tests/test_comparison_report_visual_only.py:149:            "run_label": "audit_real_run",
ui/backend/tests/test_comparison_report_visual_only.py:150:            "timestamp": "../../../etc/passwd",  # malicious
ui/backend/tests/test_comparison_report_visual_only.py:160:    with pytest.raises(ReportError, match="invalid timestamp"):
ui/backend/tests/test_comparison_report_visual_only.py:161:        build_report_context(case, "audit_real_run")
ui/backend/routes/comparison_report.py:105:    under ``reports/phase5_renders/{case_id}/`` — belt-and-suspenders on top of
ui/backend/routes/comparison_report.py:108:    from ui.backend.services.comparison_report import _RENDERS_ROOT, _load_run_manifest, _validated_timestamp  # noqa: PLC0415
ui/backend/routes/comparison_report.py:116:    # Resolve the timestamped renders dir via the per-run manifest.
ui/backend/routes/comparison_report.py:121:    ts = _validated_timestamp(run_manifest.get("timestamp"))
ui/backend/routes/comparison_report.py:123:        raise HTTPException(status_code=404, detail="invalid run manifest timestamp")
src/auto_verifier/schemas.py:92:    timestamp: str
src/auto_verifier/schemas.py:104:            "timestamp": self.timestamp,
ui/backend/tests/test_comparison_report_service.py:23:    renders_root = root / "reports" / "phase5_renders"
ui/backend/tests/test_comparison_report_service.py:38:    (fields_root / case / "runs" / "audit_real_run.json").write_text(
ui/backend/tests/test_comparison_report_service.py:39:        json.dumps({"timestamp": ts, "case_id": case, "run_label": "audit_real_run"}),
ui/backend/tests/test_comparison_report_service.py:50:    (renders_root / case / "runs" / "audit_real_run.json").write_text(
ui/backend/tests/test_comparison_report_service.py:52:            "case_id": case, "run_label": "audit_real_run", "timestamp": ts,
ui/backend/tests/test_comparison_report_service.py:54:                "profile_png": f"reports/phase5_renders/{case}/{ts}/profile_u_centerline.png",
ui/backend/tests/test_comparison_report_service.py:55:                "pointwise_deviation_png": f"reports/phase5_renders/{case}/{ts}/pointwise_deviation.png",
ui/backend/tests/test_comparison_report_service.py:56:                "contour_u_magnitude_png": f"reports/phase5_renders/{case}/{ts}/contour_u_magnitude.png",
ui/backend/tests/test_comparison_report_service.py:57:                "residuals_png": f"reports/phase5_renders/{case}/{ts}/residuals.png",
ui/backend/tests/test_comparison_report_service.py:99:    ctx = svc.build_report_context("lid_driven_cavity", "audit_real_run")
ui/backend/tests/test_comparison_report_service.py:101:    assert ctx["timestamp"] == "20260421T000000Z"
ui/backend/tests/test_comparison_report_service.py:108:    html = svc.render_report_html("lid_driven_cavity", "audit_real_run")
ui/backend/tests/test_comparison_report_service.py:115:def test_rejects_tampered_manifest_timestamp(synthetic_tree) -> None:
ui/backend/tests/test_comparison_report_service.py:116:    """Codex round 1 HIGH: manifest with timestamp='../../outside' must be rejected."""
ui/backend/tests/test_comparison_report_service.py:119:    # Overwrite manifest with malicious timestamp.
ui/backend/tests/test_comparison_report_service.py:120:    m = root / "reports" / "phase5_fields" / "lid_driven_cavity" / "runs" / "audit_real_run.json"
ui/backend/tests/test_comparison_report_service.py:121:    m.write_text(json.dumps({"timestamp": "../../../../tmp/evil"}), encoding="utf-8")
ui/backend/tests/test_comparison_report_service.py:122:    with pytest.raises(svc.ReportError, match="invalid timestamp"):
ui/backend/tests/test_comparison_report_service.py:123:        svc.build_report_context("lid_driven_cavity", "audit_real_run")
ui/backend/tests/test_comparison_report_service.py:126:def test_rejects_non_matching_timestamp_shape(synthetic_tree) -> None:
ui/backend/tests/test_comparison_report_service.py:130:    m = root / "reports" / "phase5_fields" / "lid_driven_cavity" / "runs" / "audit_real_run.json"
ui/backend/tests/test_comparison_report_service.py:131:    m.write_text(json.dumps({"timestamp": "2026-04-21"}), encoding="utf-8")
ui/backend/tests/test_comparison_report_service.py:133:        svc.build_report_context("lid_driven_cavity", "audit_real_run")
ui/backend/tests/test_comparison_report_service.py:141:    rm = root / "reports" / "phase5_renders" / "lid_driven_cavity" / "runs" / "audit_real_run.json"
ui/backend/tests/test_comparison_report_service.py:144:            "case_id": "lid_driven_cavity", "run_label": "audit_real_run",
ui/backend/tests/test_comparison_report_service.py:145:            "timestamp": "20260421T000000Z",
ui/backend/tests/test_comparison_report_service.py:149:                "contour_u_magnitude_png": "reports/phase5_renders/lid_driven_cavity/20260421T000000Z/contour_u_magnitude.png",
ui/backend/tests/test_comparison_report_service.py:150:                "residuals_png": "reports/phase5_renders/lid_driven_cavity/20260421T000000Z/residuals.png",
ui/backend/tests/test_comparison_report_service.py:155:    ctx = svc.build_report_context("lid_driven_cavity", "audit_real_run")
ui/backend/tests/test_comparison_report_service.py:161:    assert "reports/phase5_renders" in ctx["renders"]["contour_png_rel"]
ui/backend/tests/test_comparison_report_service.py:168:    m = root / "reports" / "phase5_fields" / "lid_driven_cavity" / "runs" / "audit_real_run.json"
ui/backend/tests/test_comparison_report_service.py:171:        svc.build_report_context("lid_driven_cavity", "audit_real_run")
ui/backend/tests/test_comparison_report_service.py:180:        svc.render_report_pdf("lid_driven_cavity", "audit_real_run", output_path=evil)
ui/backend/tests/test_audit_package_phase7e.py:10:- Tampered Phase 7 manifest (invalid timestamp) → phase7 key absent, not 500.
ui/backend/tests/test_audit_package_phase7e.py:35:    tmp_path: Path, case_id: str = "lid_driven_cavity", run_id: str = "audit_real_run",
ui/backend/tests/test_audit_package_phase7e.py:36:    timestamp: str = "20260421T000000Z",
ui/backend/tests/test_audit_package_phase7e.py:40:    renders = tmp_path / "reports" / "phase5_renders" / case_id
ui/backend/tests/test_audit_package_phase7e.py:42:    (fields / timestamp / "sample" / "1000").mkdir(parents=True)
ui/backend/tests/test_audit_package_phase7e.py:43:    (fields / timestamp / "sample" / "1000" / "uCenterline.xy").write_text(
ui/backend/tests/test_audit_package_phase7e.py:47:    (fields / timestamp / "residuals.csv").write_text(
ui/backend/tests/test_audit_package_phase7e.py:52:        json.dumps({"timestamp": timestamp, "case_id": case_id, "run_label": run_id}),
ui/backend/tests/test_audit_package_phase7e.py:55:    (renders / timestamp).mkdir(parents=True)
ui/backend/tests/test_audit_package_phase7e.py:57:        (renders / timestamp / n).write_bytes(b"\x89PNG\r\n\x1a\nfake")
ui/backend/tests/test_audit_package_phase7e.py:60:        json.dumps({"timestamp": timestamp, "case_id": case_id, "run_label": run_id,
ui/backend/tests/test_audit_package_phase7e.py:64:    (reports / timestamp).mkdir(parents=True)
ui/backend/tests/test_audit_package_phase7e.py:65:    (reports / timestamp / f"{run_id}_comparison_report.pdf").write_bytes(
ui/backend/tests/test_audit_package_phase7e.py:68:    return tmp_path, timestamp
ui/backend/tests/test_audit_package_phase7e.py:75:    phase7 = _collect_phase7_artifacts("lid_driven_cavity", "audit_real_run", tmp_path)
ui/backend/tests/test_audit_package_phase7e.py:96:def test_collect_phase7_rejects_tampered_timestamp(tmp_path) -> None:
ui/backend/tests/test_audit_package_phase7e.py:97:    """Malicious runs/{run}.json with timestamp='../../outside' must not leak files."""
ui/backend/tests/test_audit_package_phase7e.py:100:    m = tmp_path / "reports" / "phase5_fields" / "lid_driven_cavity" / "runs" / "audit_real_run.json"
ui/backend/tests/test_audit_package_phase7e.py:101:    m.write_text(json.dumps({"timestamp": "../../etc"}), encoding="utf-8")
ui/backend/tests/test_audit_package_phase7e.py:107:    mr = tmp_path / "reports" / "phase5_renders" / "lid_driven_cavity" / "runs" / "audit_real_run.json"
ui/backend/tests/test_audit_package_phase7e.py:108:    mr.write_text(json.dumps({"timestamp": "../../etc"}), encoding="utf-8")
ui/backend/tests/test_audit_package_phase7e.py:109:    phase7 = _collect_phase7_artifacts("lid_driven_cavity", "audit_real_run", tmp_path)
ui/backend/tests/test_audit_package_phase7e.py:118:def test_timestamp_regex_shape_gate() -> None:
ui/backend/tests/test_audit_package_phase7e.py:132:        run_id="audit_real_run",
ui/backend/tests/test_audit_package_phase7e.py:145:        run_id="audit_real_run",
ui/backend/tests/test_audit_package_phase7e.py:161:        run_id="audit_real_run",
ui/backend/tests/test_audit_package_phase7e.py:183:                             "audit_real_run_comparison_report.pdf").read_bytes()
ui/backend/tests/test_audit_package_phase7e.py:197:        run_id="audit_real_run",
ui/backend/tests/test_audit_package_phase7e.py:216:        case_id="lid_driven_cavity", run_id="audit_real_run",
ui/backend/tests/test_audit_package_phase7e.py:221:        case_id="lid_driven_cavity", run_id="audit_real_run",
ui/backend/tests/test_phase5_byte_repro.py:3:Enforces that every `audit_real_run_measurement.yaml` under fixtures/runs/
ui/backend/tests/test_phase5_byte_repro.py:10:2. `run_metadata.run_id == "audit_real_run"` (not a per-run hash).
ui/backend/tests/test_phase5_byte_repro.py:12:4. `measurement.measured_at` is the only timestamp field.
ui/backend/tests/test_phase5_byte_repro.py:60:    return sorted(RUNS_DIR.glob("*/audit_real_run_measurement.yaml"))
ui/backend/tests/test_phase5_byte_repro.py:67:        "Expected at least one audit_real_run_measurement.yaml under "
ui/backend/tests/test_phase5_byte_repro.py:85:    assert md["run_id"] == "audit_real_run", (
ui/backend/tests/test_phase5_byte_repro.py:86:        f"{path} run_metadata.run_id must be literally 'audit_real_run' "
ui/backend/tests/test_phase5_byte_repro.py:92:    assert md["category"] == "audit_real_run", (
ui/backend/tests/test_phase5_byte_repro.py:93:        f"{path} category must be 'audit_real_run'; got {md['category']!r}"
ui/backend/tests/test_phase5_byte_repro.py:130:        "measurement.measured_at", # ISO timestamp
src/audit_package/manifest.py:14:- Generation timestamp (ISO-8601 UTC, second precision)
src/audit_package/manifest.py:21:- Git-log lookups use ``--format=%H`` (no timestamp). Absence of a git repo
src/audit_package/manifest.py:76:    """UTC timestamp, second precision, Z suffix."""
src/audit_package/manifest.py:307:# Deterministic YYYYMMDDTHHMMSSZ shape for run timestamps (mirrors 7a/7b/7c gates).
src/audit_package/manifest.py:330:    - Disk paths derive from deterministic timestamp folders.
src/audit_package/manifest.py:335:    Security: timestamp values read from Phase 7a/7b manifests are validated
src/audit_package/manifest.py:341:    renders_root = repo_root / "reports" / "phase5_renders" / case_id
src/audit_package/manifest.py:380:            ts = f_data.get("timestamp")
src/audit_package/manifest.py:404:            ts = r_data.get("timestamp")
src/audit_package/manifest.py:418:    # same timestamp (7c service writes under reports/phase5_reports/{case}/{ts}/).
src/audit_package/manifest.py:419:    # Pull the timestamp from the 7a manifest (authoritative).
src/audit_package/manifest.py:426:            ts = f_data.get("timestamp")
src/audit_package/manifest.py:487:        When None, defaults to an ISO-UTC timestamp (fallback for legacy

exec
/bin/zsh -lc "nl -ba scripts/render_case_report.py | sed -n '728,780p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   728	    # Write per-run renders manifest (mirrors phase5_fields/{case}/runs/{label}.json).
   729	    manifest_dir = RENDERS_ROOT / case_id / "runs"
   730	    manifest_dir.mkdir(parents=True, exist_ok=True)
   731	    manifest = {
   732	        "case_id": case_id,
   733	        "run_label": run_label,
   734	        "timestamp": timestamp,
   735	        "renders_dir_rel": str(renders_dir.relative_to(REPO_ROOT)),
   736	        "outputs": {k: str(p.relative_to(REPO_ROOT)) for k, p in outputs.items()},
   737	        "errors": errors,
   738	    }
   739	    manifest_path = manifest_dir / f"{run_label}.json"
   740	    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
   741	    print(f"[render] {case_id} → {len(outputs)}/{len(renderers)} outputs; manifest={manifest_path}")
   742	    return {"manifest": manifest_path, **outputs}
   743	
   744	
   745	def main(argv: Optional[list[str]] = None) -> int:
   746	    parser = argparse.ArgumentParser(description="Phase 7b render pipeline for CFD audit artifacts")
   747	    parser.add_argument("case_id", help="e.g. lid_driven_cavity")
   748	    parser.add_argument("--run", dest="run_label", default="audit_real_run",
   749	                        help="run_label (default: audit_real_run)")
   750	    args = parser.parse_args(argv)
   751	    try:
   752	        render_all(args.case_id, args.run_label)
   753	        return 0
   754	    except RenderError as e:
   755	        print(f"[render] FATAL {e}", file=sys.stderr)
   756	        return 1
   757	
   758	
   759	if __name__ == "__main__":
   760	    sys.exit(main())

exec
/bin/zsh -lc 'python3 -m pytest ui/backend/tests/test_comparison_report_visual_only.py -q' in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "python3 -c \"from fastapi.testclient import TestClient; from ui.backend.main import app; c=TestClient(app, raise_server_exceptions=False); r=c.get('/api/cases/backward_facing_step/runs/audit_real_run/comparison-report'); print(r.status_code); print(r.text[:500])\"" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "python3 -c \"from ui.backend.services.comparison_report import build_report_context; import json; c=build_report_context('backward_facing_step','audit_real_run'); print(json.dumps({k:c.get(k) for k in ['visual_only','case_id','run_label','timestamp','metrics','paper','meta','solver','commit_sha','renders']}, indent=2))\"" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 332ms:
{
  "visual_only": true,
  "case_id": "backward_facing_step",
  "run_label": "audit_real_run",
  "timestamp": "20260421T125637Z",
  "metrics": null,
  "paper": null,
  "meta": null,
  "solver": "simpleFoam",
  "commit_sha": "575db8f",
  "renders": {
    "contour_png_rel": "reports/phase5_renders/backward_facing_step/20260421T125637Z/contour_u_magnitude.png",
    "residuals_png_rel": "reports/phase5_renders/backward_facing_step/20260421T125637Z/residuals.png"
  }
}

 exited 1 in 896ms:
Traceback (most recent call last):
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pydantic/_internal/_typing_extra.py", line 254, in eval_type_backport
    return typing._eval_type(  # type: ignore
  File "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/typing.py", line 290, in _eval_type
    return t._evaluate(globalns, localns, recursive_guard)
  File "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/typing.py", line 546, in _evaluate
    eval(self.__forward_code__, globalns, localns),
  File "<string>", line 1, in <module>
TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/main.py", line 46, in <module>
    from ui.backend.routes import (
  File "/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/routes/audit_package.py", line 61, in <module>
    from ui.backend.services.validation_report import (  # noqa: SLF001
  File "/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/validation_report.py", line 25, in <module>
    from ui.backend.schemas.validation import (
  File "/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/schemas/validation.py", line 94, in <module>
    class GoldStandardReference(BaseModel):
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pydantic/_internal/_model_construction.py", line 197, in __new__
    set_model_fields(cls, bases, config_wrapper, types_namespace)
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pydantic/_internal/_model_construction.py", line 474, in set_model_fields
    fields, class_vars = collect_model_fields(cls, bases, config_wrapper, types_namespace, typevars_map=typevars_map)
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pydantic/_internal/_fields.py", line 131, in collect_model_fields
    type_hints = get_cls_type_hints_lenient(cls, types_namespace)
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pydantic/_internal/_typing_extra.py", line 226, in get_cls_type_hints_lenient
    hints[name] = eval_type_lenient(value, globalns, localns)
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pydantic/_internal/_typing_extra.py", line 238, in eval_type_lenient
    return eval_type_backport(value, globalns, localns)
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pydantic/_internal/_typing_extra.py", line 263, in eval_type_backport
    raise TypeError(
TypeError: You have a type annotation 'str | None' which makes use of newer typing features than are supported in your version of Python. To handle this error, you should either remove the use of new syntax or install the `eval_type_backport` package.

 exited 2 in 1101ms:
============================= test session starts ==============================
platform darwin -- Python 3.9.6, pytest-7.4.4, pluggy-1.6.0
rootdir: /Users/Zhuanz/Desktop/cfd-harness-unified
configfile: pyproject.toml
plugins: anyio-4.12.1, asyncio-0.23.5, mock-3.15.1, cov-4.1.0
asyncio: mode=strict
collected 0 items / 1 error

==================================== ERRORS ====================================
___ ERROR collecting ui/backend/tests/test_comparison_report_visual_only.py ____
../../Library/Python/3.9/lib/python/site-packages/pydantic/_internal/_typing_extra.py:254: in eval_type_backport
    return typing._eval_type(  # type: ignore
/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/typing.py:290: in _eval_type
    return t._evaluate(globalns, localns, recursive_guard)
/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/typing.py:546: in _evaluate
    eval(self.__forward_code__, globalns, localns),
<string>:1: in <module>
    ???
E   TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'

The above exception was the direct cause of the following exception:
ui/backend/tests/test_comparison_report_visual_only.py:18: in <module>
    from ui.backend.main import app
ui/backend/main.py:46: in <module>
    from ui.backend.routes import (
ui/backend/routes/audit_package.py:61: in <module>
    from ui.backend.services.validation_report import (  # noqa: SLF001
ui/backend/services/validation_report.py:25: in <module>
    from ui.backend.schemas.validation import (
ui/backend/schemas/validation.py:94: in <module>
    class GoldStandardReference(BaseModel):
../../Library/Python/3.9/lib/python/site-packages/pydantic/_internal/_model_construction.py:197: in __new__
    set_model_fields(cls, bases, config_wrapper, types_namespace)
../../Library/Python/3.9/lib/python/site-packages/pydantic/_internal/_model_construction.py:474: in set_model_fields
    fields, class_vars = collect_model_fields(cls, bases, config_wrapper, types_namespace, typevars_map=typevars_map)
../../Library/Python/3.9/lib/python/site-packages/pydantic/_internal/_fields.py:131: in collect_model_fields
    type_hints = get_cls_type_hints_lenient(cls, types_namespace)
../../Library/Python/3.9/lib/python/site-packages/pydantic/_internal/_typing_extra.py:226: in get_cls_type_hints_lenient
    hints[name] = eval_type_lenient(value, globalns, localns)
../../Library/Python/3.9/lib/python/site-packages/pydantic/_internal/_typing_extra.py:238: in eval_type_lenient
    return eval_type_backport(value, globalns, localns)
../../Library/Python/3.9/lib/python/site-packages/pydantic/_internal/_typing_extra.py:263: in eval_type_backport
    raise TypeError(
E   TypeError: You have a type annotation 'str | None' which makes use of newer typing features than are supported in your version of Python. To handle this error, you should either remove the use of new syntax or install the `eval_type_backport` package.
=========================== short test summary info ============================
ERROR ui/backend/tests/test_comparison_report_visual_only.py - TypeError: You...
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
=============================== 1 error in 0.73s ===============================

codex
The system `python3` is Python 3.9 here, so backend app import fails on existing `str | None` Pydantic annotations before it reaches this change. I’m switching to the repo interpreter if present, then I’ll rerun the targeted checks.
exec
/bin/zsh -lc 'ls -l .venv/bin/python' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
lrwxr-xr-x  1 Zhuanz  staff  83 Apr 18 21:20 .venv/bin/python -> /Users/Zhuanz/.local/share/uv/python/cpython-3.12-macos-aarch64-none/bin/python3.12

exec
/bin/zsh -lc '.venv/bin/python --version' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
Python 3.12.13

exec
/bin/zsh -lc 'rg -n "python_requires|requires-python|python =|target-version|python_version" pyproject.toml requirements*.txt setup.cfg tox.ini .python-version' in /Users/Zhuanz/Desktop/cfd-harness-unified
 exited 1 in 0ms:
zsh:1: no matches found: requirements*.txt

exec
/bin/zsh -lc '.venv/bin/python -m pytest ui/backend/tests/test_comparison_report_visual_only.py -q' in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc ".venv/bin/python -c \"from ui.backend.services.comparison_report import render_report_html; import traceback;\\ntry:\\n print(render_report_html('backward_facing_step','audit_real_run')[:500])\\nexcept Exception as e:\\n print(type(e).__name__, str(e)); traceback.print_exc(limit=2)\"" in /Users/Zhuanz/Desktop/cfd-harness-unified
 exited 1 in 0ms:
  File "<string>", line 1
    from ui.backend.services.comparison_report import render_report_html; import traceback;\ntry:\n print(render_report_html('backward_facing_step','audit_real_run')[:500])\nexcept Exception as e:\n print(type(e).__name__, str(e)); traceback.print_exc(limit=2)
                                                                                            ^
SyntaxError: unexpected character after line continuation character

exec
/bin/zsh -lc ".venv/bin/python -c \"from fastapi.testclient import TestClient; from ui.backend.main import app; c=TestClient(app, raise_server_exceptions=False); r=c.get('/api/cases/backward_facing_step/runs/audit_real_run/comparison-report'); print(r.status_code); print(r.text[:500])\"" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 614ms:
============================= test session starts ==============================
platform darwin -- Python 3.12.13, pytest-9.0.3, pluggy-1.6.0
rootdir: /Users/Zhuanz/Desktop/cfd-harness-unified
configfile: pyproject.toml
plugins: mock-3.15.1, cov-7.1.0, anyio-4.13.0
collected 7 items

ui/backend/tests/test_comparison_report_visual_only.py .......           [100%]

============================== 7 passed in 0.32s ===============================

 succeeded in 381ms:
500
Internal Server Error

exec
/bin/zsh -lc ".venv/bin/python -c \"from ui.backend.services.comparison_report import render_report_html; import traceback; exec(\\\"try:\\\\n    print(render_report_html('backward_facing_step','audit_real_run')[:500])\\\\nexcept Exception as e:\\\\n    print(type(e).__name__, str(e))\\\\n    traceback.print_exc(limit=6)\\\")\"" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 102ms:
exec
/bin/zsh -lc ".venv/bin/python -c \"from fastapi.testclient import TestClient; from ui.backend.main import app; c=TestClient(app, raise_server_exceptions=False);\\nfor p in ['contour_u_magnitude.png','residuals.png']:\\n r=c.get('/api/cases/backward_facing_step/runs/audit_real_run/renders/'+p); print(p, r.status_code, r.headers.get('content-type'), len(r.content))\"" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc ".venv/bin/python -c \"from fastapi.testclient import TestClient; from ui.backend.main import app; c=TestClient(app, raise_server_exceptions=False);\\npaths=['..%2F..%2Fetc%2Fpasswd','%2e%2e/%2e%2e/etc/passwd','%252e%252e%252fetc%252fpasswd','/etc/passwd','%2Fetc%2Fpasswd','contour_u_magnitude.png%00.png','runs/audit_real_run.json'];\\nfor p in paths:\\n r=c.get('/api/cases/backward_facing_step/runs/audit_real_run/renders/'+p); print(p, r.status_code, r.headers.get('content-type'), r.text[:80].replace('\\\\n',' '))\"" in /Users/Zhuanz/Desktop/cfd-harness-unified
 exited 1 in 0ms:
  File "<string>", line 1
    from fastapi.testclient import TestClient; from ui.backend.main import app; c=TestClient(app, raise_server_exceptions=False);\nfor p in ['contour_u_magnitude.png','residuals.png']:\n r=c.get('/api/cases/backward_facing_step/runs/audit_real_run/renders/'+p); print(p, r.status_code, r.headers.get('content-type'), len(r.content))
                                                                                                                                  ^
SyntaxError: unexpected character after line continuation character

 exited 1 in 0ms:
  File "<string>", line 1
    from fastapi.testclient import TestClient; from ui.backend.main import app; c=TestClient(app, raise_server_exceptions=False);\npaths=['..%2F..%2Fetc%2Fpasswd','%2e%2e/%2e%2e/etc/passwd','%252e%252e%252fetc%252fpasswd','/etc/passwd','%2Fetc%2Fpasswd','contour_u_magnitude.png%00.png','runs/audit_real_run.json'];\nfor p in paths:\n r=c.get('/api/cases/backward_facing_step/runs/audit_real_run/renders/'+p); print(p, r.status_code, r.headers.get('content-type'), r.text[:80].replace('\n',' '))
                                                                                                                                  ^
SyntaxError: unexpected character after line continuation character

exec
/bin/zsh -lc ".venv/bin/python -c \"from fastapi.testclient import TestClient; from ui.backend.main import app; c=TestClient(app, raise_server_exceptions=False); r=c.get('/api/cases/backward_facing_step/runs/audit_real_run/comparison-report/context'); print(r.status_code); print(r.json().get('visual_only'), r.json().get('renders'))\"" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 367ms:
200
True {'contour_png_rel': 'reports/phase5_renders/backward_facing_step/20260421T125637Z/contour_u_magnitude.png', 'residuals_png_rel': 'reports/phase5_renders/backward_facing_step/20260421T125637Z/residuals.png'}

exec
/bin/zsh -lc ".venv/bin/python -c \"from fastapi.testclient import TestClient; from ui.backend.main import app; c=TestClient(app, raise_server_exceptions=False); exec(\\\"for p in ['contour_u_magnitude.png','residuals.png']:\\\\n    r=c.get('/api/cases/backward_facing_step/runs/audit_real_run/renders/'+p)\\\\n    print(p, r.status_code, r.headers.get('content-type'), len(r.content))\\\")\"" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc ".venv/bin/python -c \"from fastapi.testclient import TestClient; from ui.backend.main import app; c=TestClient(app, raise_server_exceptions=False); exec(\\\"paths=['..%2F..%2Fetc%2Fpasswd','%2e%2e/%2e%2e/etc/passwd','%252e%252e%252fetc%252fpasswd','/etc/passwd','%2Fetc%2Fpasswd','contour_u_magnitude.png%00.png','runs/audit_real_run.json']\\\\nfor p in paths:\\\\n    r=c.get('/api/cases/backward_facing_step/runs/audit_real_run/renders/'+p)\\\\n    print(p, r.status_code, r.headers.get('content-type'), r.text[:80].replace(chr(10),' '))\\\")\"" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 349ms:
contour_u_magnitude.png 200 image/png 32331
residuals.png 200 image/png 56439

 succeeded in 355ms:
..%2F..%2Fetc%2Fpasswd 404 application/json {"detail":"invalid filename"}
%2e%2e/%2e%2e/etc/passwd 404 application/json {"detail":"invalid filename"}
%252e%252e%252fetc%252fpasswd 404 application/json {"detail":"invalid filename"}
/etc/passwd 404 application/json {"detail":"invalid filename"}
%2Fetc%2Fpasswd 404 application/json {"detail":"invalid filename"}
contour_u_magnitude.png%00.png 404 application/json {"detail":"render not found"}
runs/audit_real_run.json 404 application/json {"detail":"render not found"}

exec
/bin/zsh -lc "nl -ba /Users/Zhuanz/.codex/memories/MEMORY.md | sed -n '401,445p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
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
   417	
   418	### rollout_summary_files
   419	
   420	- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, Phase 9 kept as planning-only with decision-tree packet))
   421	
   422	### keywords
   423	
   424	- Phase 9 planning-only, PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md, PHASE9_MODEL_ROUTING_BASELINE_PLAN.md, PHASE9_ACTIVATION_REVIEW_PACKET.md, replay_manifest, SU2 CLI Harness Skill, foam_agent_adapter.py
   425	
   426	## Task 3: Stop cleanly at the Opus 4.7 activation gate
   427	
   428	### rollout_summary_files
   429	
   430	- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, handoff prompt prepared instead of silent activation))
   431	
   432	### keywords
   433	
   434	- Opus 4.7 activation review, self-dispatch, planning-only, single-engine OpenFOAM, SU2 reference-only, CFX hold, review packet
   435	
   436	## User preferences
   437	
   438	- when working this repo, the user phrased the boundary as "继续推进开发，直至需要Opus 4.7介入" -> keep executing autonomously until a real gate is reached, then stop with a ready review packet [Task 1][Task 2][Task 3]
   439	- the rollout also showed a preference for explicit gate-aware staging rather than silent activation -> preserve the planning-only vs active distinction clearly in Notion and repo docs [Task 2][Task 3]
   440	
   441	## Reusable knowledge
   442	
   443	- Notion phase/task closure here requires updating both page properties and page body text; one surface alone leaves stale recovery state [Task 1]
   444	- `knowledge/whitelist.yaml` is the active whitelist source; older references to `knowledge/ai_cfd_cold_start_whitelist.yaml` are naming drift to normalize, not a fresh design change [Task 1]
   445	- Phase 9 must start from a bounded decision tree: keep single-engine OpenFOAM, allow reference-only external solver surfaces, or open one bounded proof slice; anything broader still needs review [Task 2]

codex
CHANGES_REQUIRED

1. Visual-only cases 500 on the public HTML/build report paths.  
   `build_report_context()` now returns `visual_only=True` with `metrics=None` / `paper=None` for Tier C cases, but `render_report_html()` still renders the gold-overlay template unconditionally. The template dereferences `metrics.max_dev_pct` and `paper.title`, so direct `/api/cases/backward_facing_step/runs/audit_real_run/comparison-report` returns 500.  
   Repro: `.venv/bin/python` TestClient returned `500 Internal Server Error`; direct `render_report_html("backward_facing_step", "audit_real_run")` raises `jinja2.exceptions.UndefinedError: 'None' has no attribute 'max_dev_pct'`.  
   Relevant lines: [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:329), [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:540), [comparison_report.html.j2](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/templates/comparison_report.html.j2:58), [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/routes/comparison_report.py:38), [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/routes/comparison_report.py:144).  
   Fix direction: either make `/comparison-report`, `/comparison-report.pdf`, and `/comparison-report/build` return a controlled 404/501 for visual-only cases, or add a real `{% if visual_only %}` template branch before any gold-overlay field access.

Other focused checks:

- Render route containment: no external traversal bypass found in the inspected code or probes for encoded `../`, absolute paths, double-encoded traversal, or null bytes. Valid basenames returned 200.
- Frontend render URLs are not currently user-controlled; the visual-only branch ignores manifest path content except as a non-empty guard and sends fixed basenames.
- `-noFaceZones` looks safe for comparator extraction: the runtime key-quantity path uses copied `writeObjects` fields (`U`, `p`, `Cx`, `Cy`, `Cz`, `T`), not faceZone VTK. Cylinder Strouhal extraction reads cell pressure/centres and has the Re=100 canonical shortcut.
- `_parse_residuals_from_log()` regex is anchored and linear-looking; I did not see a ReDoS issue.

Verification run: `.venv/bin/python -m pytest ui/backend/tests/test_comparison_report_visual_only.py -q` passed `7/7`. System `python3` is 3.9 here and cannot import the app because existing Pydantic annotations require newer typing support, so I used the repo `.venv` Python 3.12.


tokens used
187,699
CHANGES_REQUIRED

1. Visual-only cases 500 on the public HTML/build report paths.  
   `build_report_context()` now returns `visual_only=True` with `metrics=None` / `paper=None` for Tier C cases, but `render_report_html()` still renders the gold-overlay template unconditionally. The template dereferences `metrics.max_dev_pct` and `paper.title`, so direct `/api/cases/backward_facing_step/runs/audit_real_run/comparison-report` returns 500.  
   Repro: `.venv/bin/python` TestClient returned `500 Internal Server Error`; direct `render_report_html("backward_facing_step", "audit_real_run")` raises `jinja2.exceptions.UndefinedError: 'None' has no attribute 'max_dev_pct'`.  
   Relevant lines: [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:329), [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:540), [comparison_report.html.j2](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/templates/comparison_report.html.j2:58), [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/routes/comparison_report.py:38), [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/routes/comparison_report.py:144).  
   Fix direction: either make `/comparison-report`, `/comparison-report.pdf`, and `/comparison-report/build` return a controlled 404/501 for visual-only cases, or add a real `{% if visual_only %}` template branch before any gold-overlay field access.

Other focused checks:

- Render route containment: no external traversal bypass found in the inspected code or probes for encoded `../`, absolute paths, double-encoded traversal, or null bytes. Valid basenames returned 200.
- Frontend render URLs are not currently user-controlled; the visual-only branch ignores manifest path content except as a non-empty guard and sends fixed basenames.
- `-noFaceZones` looks safe for comparator extraction: the runtime key-quantity path uses copied `writeObjects` fields (`U`, `p`, `Cx`, `Cy`, `Cz`, `T`), not faceZone VTK. Cylinder Strouhal extraction reads cell pressure/centres and has the Re=100 canonical shortcut.
- `_parse_residuals_from_log()` regex is anchored and linear-looking; I did not see a ReDoS issue.

Verification run: `.venv/bin/python -m pytest ui/backend/tests/test_comparison_report_visual_only.py -q` passed `7/7`. System `python3` is 3.9 here and cannot import the app because existing Pydantic annotations require newer typing support, so I used the repo `.venv` Python 3.12.


