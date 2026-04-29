2026-04-29T07:54:57.141134Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-research-deerflow/SKILL.md: missing YAML frontmatter delimited by ---
2026-04-29T07:54:57.141152Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-report-pretext/SKILL.md: missing YAML frontmatter delimited by ---
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
session id: 019dd83b-e4f5-7fa1-b1e2-7d0120852256
--------
user
Codex round 2 review for DEC-V61-099. Round 1 returned CHANGES_REQUIRED with 1 MED finding: staging exec_run calls didn't check exit_code, so silent shell-command failures (rm -rf failure, mv permission error, suffixed path uncleanable) would let _prepare_stream_icofoam return a stream that hits FOAM Fatal at first icoFoam read.

ROUND 1 CLOSURE (in working tree, not yet committed):

solver_streamer.py:
- Capture mkdir_res from BASE-mkdir exec_run
- Check getattr(mkdir_res, 'exit_code', 0) != 0 → raise SolverRunError('failed to prepare container staging base ...')
- Capture rename_res from rm/mv/chmod exec_run
- Check getattr(rename_res, 'exit_code', 0) != 0 → raise SolverRunError('failed to rename staged case dir ...')
- Both errors include the offending exit_code in the message

test_solver_streamer.py: TWO new tests
- test_staging_raises_on_nonzero_exec_run_exit_code: a FailingRenameContainer subclass returns exit_code=1 specifically when the rename command (mv ... case_exit_code_check-...) is dispatched. Asserts SolverRunError raised AND _active_runs lock is released for retry.
- test_staging_raises_on_nonzero_mkdir_exit_code: companion test that exercises the BASE-mkdir failure path. Asserts SolverRunError raised + lock released.
- Both tests verify behavior the previous regression test couldn't (it only inspected command strings, not exit_code handling — Codex round 1 specifically called this out).

11/11 solver_streamer tests pass locally including the two new ones.

REVIEW FOCUS:
1. Is the round-1 MED finding fully closed? exit_code check applied to BOTH staging exec_run sites?
2. Do the two new tests actually exercise the failure mode (i.e., would they fail against the buggy version that ignored exit_code)? Yes by inspection — the SolverRunError pytest.raises would not match if exit_code wasn't checked.
3. Any new HIGH/MED I missed in this round? The R1 verdict noted 'rm -rf {container_work_dir} does not look too broad' and 'chmod 777 ... I would not block merge on that alone' — those are already non-blocking per round 1.
4. Verbatim-exception verifiable now: closure matches R1 'Recommendation: check exit_code after both setup exec_run calls and add a test that forces the rename step to return non-zero' verbatim.

Return verdict: APPROVE / RESOLVED / CHANGES_REQUIRED with severity findings. Reference reports/codex_tool_reports/dec_v61_097_phase_1a_round*.md for verdict format.
codex
Reviewing the round-1 closure as a read-only code review. I’m loading the review format reference, the changed diff, and the current `solver_streamer` tests to verify whether the MED finding is actually closed and whether any new blocking issues were introduced.
exec
/bin/zsh -lc 'rg -n "DEC-V61-099|solver_streamer|round" /Users/Zhuanz/.codex/memories/MEMORY.md' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
164:- Symptom: engine tests expose wrong action flow around hand refill or turn advancement -> cause: game-loop assumptions were encoded before the intended two-actions-per-turn rhythm was settled -> fix: let tests drive the rhythm and avoid auto-refilling hands on discard unless the rules really require it [Task 1]
165:- Symptom: detached `nohup npm run dev -- --port 5174` does not stay up -> cause: this Vite server path was more reliable interactively than as a detached background launch -> fix: run `npm run dev -- --port 5174` interactively for local verification [Task 2]
361:- Symptom: a long one-shot backup/cleanup script flakes out mid-run -> cause: too much work is bundled around a moving `.git` target -> fix: split the work into smaller commands after the `.git` rename [Task 2]
468:- Symptom: the session appears to have multiple active runtime states at the end -> cause: a background demo server from browser smoke was still running -> fix: treat leftover demo-server processes as ephemeral verification artifacts and do not confuse them with handoff completion state [Task 2]
1073:- first customer, 我就是第一个客户, 不想在这个时间点立刻大幅转向, 完整的CFD工作台, OpenClaw, CFD workbench, V&V dashboard layer, /learn, /pro, FoamAgentExecutor, wizard_drivers, physics-grounded structured honesty, workbench_rollout_summary
1109:- Under the first-customer framing, the shortest realistic path is not a wholesale repositioning but wiring the existing wizard/SSE/backend flow from mock execution to real `FoamAgentExecutor`, then adding parameter override, history, and debug visibility around one real anchor case such as LDC [Task 1]
1115:- The useful default execution order for a handoff from these assessment runs is: restate the governing premise -> check facts/baseline -> fix environment/contracts -> choose one narrative (`demo-first` or `first-customer workbench`) -> then narrow implementation around anchor cases [Task 1][Task 3]
1240:- the user repeatedly constrained work to one anchor case and very tight file landing zones: "只改" specific files around `lid_driven_cavity_benchmark` -> avoid opportunistic scope growth [Task 1]
1261:- Symptom: the assistant frames work around an outdated phase narrative -> cause: Notion cockpit already moved to a newer hold/accepted state -> fix: re-read the current control-plane state before committing to a phase framing [Task 2]
1327:scope: Parse the source control document, freeze the deploy logic from explicit user corrections, build the `well_harness` simulation around that truth, and separate controller correctness from plant-model or demo-scope drift.
1348:- well_harness, controller.py, switches.py, plant.py, scenarios.py, runner.py, cli.py, nominal-deploy, deviation audit, simplified plant, 115 tests OK, logic1 around 0.5s, logic2 around 1.2s, logic3 around 1.9s, logic4 around 5.0s
1361:- The frozen deploy logic that matched the user’s corrections was: `logic1 = RA < 6 ft + SW1 + not inhibited + not deployed`; `logic2 = engine running + on ground + not inhibited + SW2 + EEC enable`; `logic3 = engine running + on ground + not inhibited + TLS unlocked + N1k below limit + TRA <= -11.74°`; `logic4 = 90% deploy + -32° < TRA < 0° + on ground + engine running` [Task 1]
1383:- rollout_summaries/2026-04-07T06-20-24-tGb4-round_92_direct_vdt_control_flatter_logic_board.md (cwd=/Users/Zhuanz/20260407 YJX AI FANTUI LogicMVP, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/07/rollout-2026-04-07T14-20-24-019d6699-6f65-7712-ba2d-13ed0f64e87e.jsonl, updated_at=2026-04-08T14:50:07+00:00, thread_id=019d6699-6f65-7712-ba2d-13ed0f64e87e, final Round 92 reflow with preserved endpoint contracts)
1437:- for leadership-facing summaries, the user asked for "真实、可靠的AI coding方法" and "不能包含任何英文专业术语，除非你能详细解释" -> write in plain Chinese for non-software readers and ground the story in evidence rather than jargon [Task 4]
1446:- The stable storyline for explanation is: logic truth first, then contracts/tests, then controlled demo answers, then cockpit UI, then QA/polish rounds [Task 4]
1985:- across these multi-file implementation tasks, the user repeatedly said "Run in background" -> for long cross-file slices in this repo, do the wiring and targeted verification in one pass instead of asking them to orchestrate each substep [Task 1][Task 2][Task 3][Task 4]
2053:- Symptom: a review answer drifts into general commentary or architecture advice -> cause: treating “review” as broad feedback instead of a defect audit -> fix: report only grounded correctness findings with file/line references [Task 1]
2147:- Thresholds used in the installed workflow: keep active context around 35%-45%, start compressing around 50%, checkpoint by about 65%, and rebuild near 75% [Task 1]

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
/bin/zsh -lc 'rg --files reports/codex_tool_reports' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
reports/codex_tool_reports/2026-04-28_m_viz_bundle_steps_3_to_6_codex_review_round4.md
reports/codex_tool_reports/2026-04-21_pr21_bfs_guard_review.md
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_prompt.md
reports/codex_tool_reports/2026-04-21_phase7bde_codex_review_round1.md
reports/codex_tool_reports/dec_v61_074_t1b23_postcommit_round1.md
reports/codex_tool_reports/run_compare_api_r2.md
reports/codex_tool_reports/bug1_sse_disconnect_persistence_r2.md
reports/codex_tool_reports/20260422_dec045_wave1_A_convergence_attestor_result.md
reports/codex_tool_reports/dec_v61_057_round2.md
reports/codex_tool_reports/20260422_dec038_codex_review.md
reports/codex_tool_reports/2026-04-28_m_viz_bundle_steps_3_to_6_codex_review_round1.md
reports/codex_tool_reports/bug1_sse_disconnect_persistence_r3.md
reports/codex_tool_reports/20260422_dec045_wave3_G_tests_prompt.md
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round2.md
reports/codex_tool_reports/2026-04-21_pr5c1_codex_followup_review.md
reports/codex_tool_reports/20260422_dec045_wave3_F_taskrunner_reorder_prompt.md
reports/codex_tool_reports/20260422_dec036_036c_039_backfill_note.md
reports/codex_tool_reports/2026-04-28_m_viz_bundle_steps_3_to_6_codex_review_round5.md
reports/codex_tool_reports/dec_v61_074_t1b1_round1.md
reports/codex_tool_reports/industrial_workbench_meeting_2026-04-25.md
reports/codex_tool_reports/2026-04-21_pr5c_hmac_review.md
reports/codex_tool_reports/dec_v61_058_round2_review.md
reports/codex_tool_reports/dec_v61_087_v3_kogami_bootstrap_r1.md
reports/codex_tool_reports/dec_v61_087_v2_kogami_bootstrap_r1.md
reports/codex_tool_reports/2026-04-28_m_panels_arc_codex_review_round3.md
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md
reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round1.md
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md
reports/codex_tool_reports/20260422_dec045_wave1_A_convergence_attestor_prompt.md
reports/codex_tool_reports/dec_v61_075_t2_3_post_commit_round2.md
reports/codex_tool_reports/dec_v61_097_phase_1a_round1.md
reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round5.md
reports/codex_tool_reports/20260422_dec045_wave3_F_taskrunner_reorder_result.md
reports/codex_tool_reports/20260422_dec036b_codex_prompt.md
reports/codex_tool_reports/dec_v61_087_kogami_bootstrap_r1.md
reports/codex_tool_reports/dec_v61_075_t2_3_post_commit_round3.md
reports/codex_tool_reports/20260422_dec045_wave3_G_tests_result.md
reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round4.md
reports/codex_tool_reports/dec_v61_099_round2.md
reports/codex_tool_reports/2026-04-28_m_panels_arc_codex_review_round2.md
reports/codex_tool_reports/dec_v61_052_bfs_round1_findings.md
reports/codex_tool_reports/dec_v61_097_phase_1a_round4.md
reports/codex_tool_reports/README.md
reports/codex_tool_reports/dec_v61_071_round2.md
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md
reports/codex_tool_reports/2026-04-21_pr5d_screen6_review.md
reports/codex_tool_reports/20260422_dec045_wave2_E_tests_result.md
reports/codex_tool_reports/dec_v61_097_phase_1a_round3.md
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round4.md
reports/codex_tool_reports/dec_v61_099_round1.md
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md
reports/codex_tool_reports/2026-04-28_m_panels_arc_codex_review_round1.md
reports/codex_tool_reports/20260422_dec045_wave1_B_comparator_gates_prompt.md
reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round3.md
reports/codex_tool_reports/dec_v61_075_t2_3_post_commit_round4.md
reports/codex_tool_reports/dec_v61_071_round1.md
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md
reports/codex_tool_reports/dec_v61_058_plan_review.md
reports/codex_tool_reports/20260422_dec038_codex_prompt.md
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md
reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round2.md
reports/codex_tool_reports/dec_v61_075_t2_3_post_commit_round5.md
reports/codex_tool_reports/2026-04-21_pr5c2_m3_review.md
reports/codex_tool_reports/2026-04-28_m_panels_arc_codex_review_round4.md
reports/codex_tool_reports/dec_v61_097_phase_1a_round2.md
reports/codex_tool_reports/dec_v61_075_t2_3_post_commit_round1.md
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md
reports/codex_tool_reports/2026-04-21_pr22_duct_dispatch_review.md
reports/codex_tool_reports/dec_v61_057_plan_review.md
reports/codex_tool_reports/2026-04-28_m_viz_bundle_steps_3_to_6_codex_review_round2.md
reports/codex_tool_reports/20260422_v62_takeover_notion_sync_draft.md
reports/codex_tool_reports/dec_v61_072_sampling_audit_first_execution.md
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round1.md
reports/codex_tool_reports/2026-04-21_pr20_foam_adapter_review.md
reports/codex_tool_reports/2026-04-21_pr23_build_fingerprint_review.md
reports/codex_tool_reports/20260422_dec045_wave2_E_tests_prompt.md
reports/codex_tool_reports/dec_v61_074_t1b1_round2.md
reports/codex_tool_reports/2026-04-21_pr5d1_closure_review.md
reports/codex_tool_reports/20260422_dec045_wave1_B_comparator_gates_result.md
reports/codex_tool_reports/dec_v61_087_v3_kogami_bootstrap_r2.md
reports/codex_tool_reports/20260422_dec036b_codex_review.md
reports/codex_tool_reports/dec_v61_057_round4.md
reports/codex_tool_reports/2026-04-21_phase7bc_render_report_codex_review.md
reports/codex_tool_reports/m_render_api_arc/README.md
reports/codex_tool_reports/m_render_api_arc/round4.log
reports/codex_tool_reports/m_render_api_arc/round5.log
reports/codex_tool_reports/m_render_api_arc/round2.log
reports/codex_tool_reports/m_render_api_arc/round3.log
reports/codex_tool_reports/m_render_api_arc/round1.log
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_prompt.md
reports/codex_tool_reports/2026-04-21_phase7bde_codex_review_round2.md
reports/codex_tool_reports/dec_v61_074_t1b23_postcommit_round2.md
reports/codex_tool_reports/bug1_sse_disconnect_persistence_r1.md
reports/codex_tool_reports/run_compare_api_r1.md
reports/codex_tool_reports/2026-04-28_m_viz_bundle_steps_3_to_6_codex_review_round3.md
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_prompt.md
reports/codex_tool_reports/dec_v61_058_round1_review.md
reports/codex_tool_reports/dec_v61_057_round1.md

exec
/bin/zsh -lc 'git status --short' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
 M ui/backend/routes/case_solve.py
M  ui/backend/services/case_solve/solver_streamer.py
M  ui/backend/tests/test_solver_streamer.py
?? .claude/MODEL_ROUTING.md
?? .planning/strategic/2026-04-26_claude_code_kickoff_prompt_pivot_v1_1.md
?? .planning/strategic/2026-04-26_strategic_advisory_memo.md
?? .planning/strategic/2026-04-26_strategic_advisory_memo_002_post_three_answers.md
?? .planning/strategic/PROJECT_HISTORY_NARRATIVE.md
?? docs/methodology/project_introduction.md
?? reports/codex_tool_reports/dec_v61_099_round1.md
?? reports/codex_tool_reports/dec_v61_099_round2.md
?? ui/backend/services/ai_actions/

codex
I found the relevant working-tree changes and I’m now checking the exact diff against the round-1 report format. After that I’ll validate whether the new tests really fail on the pre-fix behavior and whether the fix covers both staging call sites.
exec
/bin/zsh -lc "sed -n '1,240p' reports/codex_tool_reports/dec_v61_097_phase_1a_round1.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
# Codex pre-merge review · DEC-V61-097 Phase-1A · Round 1

**Date**: 2026-04-29
**Verdict**: `Codex-verified: CHANGES_REQUIRED solve-stream preflight/multi-run correctness is unsafe, and /bc/render is missing mesh-render input hardening`
**Tokens**: 186,130
**Account**: ksnbdajdjddkdd@gmail.com (plus, 71%)
**Commits reviewed**: `0c849c648b1c..fa5d98f` (5 commits in this arc, 17 in cadence range)

---

## Findings

### 1. HIGH — solve-stream preflight is inside generator, returns 200 then breaks
**File**: `ui/backend/routes/case_solve.py:149` + `ui/backend/services/case_solve/solver_streamer.py:170`

`stream_icofoam()` is a generator, so the failure-mapping code at lines 170-243 only executes when `StreamingResponse` begins iterating. Container down / Docker SDK broken / staging failure produces a started SSE response and then an iterator exception or broken stream, not the structured HTTP rejection the route comment promises.

**Verbatim fix**: Move lines 170-243 of `stream_icofoam()` into a non-generator `_prepare_stream_icofoam(...)` helper, call that helper in the route before constructing `StreamingResponse`, and only return the streaming generator after preflight succeeds.

### 2. HIGH — abort/restart race: no run-generation guard, shared container_work_dir
**File**: `ui/frontend/src/pages/workbench/step_panel_shell/SolveStreamContext.tsx:148` + `ui/backend/services/case_solve/solver_streamer.py:200`

Frontend "abort" only aborts the fetch reader; it does not stop the solver. Backend always uses the same `container_work_dir` derived from `case_host_dir.name`. Failure mode: navigate-away/remount can leave run A alive, run B starts in same directory, both race on `log.icoFoam` + time dirs + pulled-back artifacts. Frontend has no run-generation guard, so stale `done`/`error` from older invocation can mutate state after a newer `start()`.

**Verbatim fix**: Introduce a per-case solve lock or server-issued `run_id`; reject concurrent `solve-stream` with `409 solve_already_running`, use `container_work_dir = f'{CONTAINER_WORK_BASE}/{case_host_dir.name}-{run_id}'`, and gate all frontend state writes on `if (runIdRef.current !== localRunId) return`.

### 3. MED — /bc/render missing /mesh/render symlink-containment hardening
**File**: `ui/backend/services/render/bc_glb.py:141` vs `ui/backend/services/render/mesh_wireframe.py:86`

`points`, `faces`, and `boundary` are opened directly via `is_file()/read_text()/parse_*`, so a symlink under `constant/polyMesh/` can escape the case dir and be read. The route's final `cache_path.resolve(...).relative_to(...)` check only protects the OUTPUT file, not the inputs.

**Verbatim fix**: Add a `_bc_source_files(polymesh_dir, case_dir) -> (points, faces, boundary)` helper identical in shape to `mesh_wireframe._polymesh_source_files`, `resolve(strict=True)` all three inputs, require `relative_to(case_root)`, pass resolved paths into `parse_points`, `parse_faces`, `_read_boundary_patches`.

### 4. MED — malformed boundary ranges silently truncated, returns partial 200 GLB
**File**: `ui/backend/services/render/bc_glb.py:175`

`if face_idx >= len(faces): continue` turns a corrupt `startFace/nFaces` into a partial 200 GLB instead of `422 parse_error`. User sees an incomplete BC scene with no explicit error; tests still pass on the happy cube fixture.

**Verbatim fix**: Replace the `continue` with `raise BcRenderError(failing_check='parse_error', message=f'boundary patch {name!r} references face {face_idx} but faces has length {len(faces)}')`.

---

## Non-blocking observations

**glTF packing OK**: 4-byte chunk padding, index/position buffer-view offsets, accessor counts, `alphaMode: BLEND` on translucent materials all structurally correct.

**vtk.js cleanup OK**: `AbortController` cleanup in `Viewport.tsx:102` + `importer.delete()` ownership in `viewport_kernel.ts:78`.

## Coverage gaps Codex flagged

- 7 bc_glb tests cover only happy-path + missing polyMesh/boundary + 200/404/409
- Missing: unsafe case IDs, symlink escape, malformed boundary, 422 parse_error path, cache rebuild/atomic-write, byte-stable cache hits, glTF invariants
- **No backend tests for `/api/import/<id>/solve-stream`**
- **No frontend tests for `SolveStreamContext` / `LiveResidualChart`** — the new SSE surface is effectively untested

## Backward-compat note

`/bc-overlay.png` still served in `case_visualize.py:55` while frontend Step 3 now uses `/bc/render`. Looks intentional as legacy fallback but DEC wording around "replaces" is stale.

## Verbatim-exception eligibility (per RETRO-V61-001 5-condition test)

| Finding | LOC est | Files | Public API | Verbatim eligible |
|---|---|---|---|---|
| #1 preflight refactor | ~70 (move) | 1-2 | No | **NO** (>20 LOC) |
| #2 run-id system | ~50-80 | 2-3 | YES (new 409) | **NO** (>20 LOC + new error class) |
| #3 symlink hardening | ~30 (helper) | 1 | No | borderline; per pattern from mesh_wireframe |
| #4 partial-GLB raise | 1-3 | 1 | No | **YES** |

Most fixes need a real implementation arc, not verbatim-exception path.

exec
/bin/zsh -lc "sed -n '1,240p' reports/codex_tool_reports/dec_v61_099_round1.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
2026-04-29T07:47:39.184876Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-research-deerflow/SKILL.md: missing YAML frontmatter delimited by ---
2026-04-29T07:47:39.184899Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-report-pretext/SKILL.md: missing YAML frontmatter delimited by ---
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
session id: 019dd835-3631-7980-85c5-72cdca1158ba
--------
user
Pre-merge Codex review for DEC-V61-099 (post-R3 live-run defect closure on V61-097 R1 HIGH-2 staging order regression).

CONTEXT:
- V61-097 R1 fix made container_work_dir run_id-suffixed but the staging sequence (mkdir suffix dir → put_archive to BASE → conditional mv with [ ! -d suffix ] guard) silently SKIPPED the rename because the mkdir made the suffix dir exist. icoFoam cd'd into the empty suffix dir → FOAM Fatal: cannot find file system/controlDict.
- Caught on first LDC dogfood ~1 hour after V61-097 R4 RESOLVED.
- This is the executable_smoke_test risk-flag class per RETRO-V61-053 addendum.

REVIEW TARGET (committed in HEAD 972fc4f):
- ui/backend/services/case_solve/solver_streamer.py: lines 284-321 staging block. Pre-create CONTAINER_WORK_BASE only; rm -rf {suffix} && mv extracted dir → suffix && chmod.
- ui/backend/tests/test_solver_streamer.py: NEW regression test test_staging_renames_extracted_dir_into_run_id_suffix. Tracks bash command sequence; asserts no mkdir of suffix path, no [ ! -d ] guard on mv.
- .planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md: full root-cause + fix DEC.

REVIEW FOCUS:
1. Correctness of the new staging sequence — any race condition? Any case where rm -rf is harmful?
2. Defensive rm -rf {container_work_dir} — too broad? run_id is hex token from secrets so collision probability is negligible but verify.
3. chmod 777 — too permissive? matches prior convention; container is single-user openfoam image.
4. Regression test assertions — do they actually catch the bug? Are string-match patterns brittle?
5. Anything else I missed.

Return verdict in standard format: APPROVE / CHANGES_REQUIRED with severity-classified findings (HIGH/MED/LOW). Reference reports/codex_tool_reports/dec_v61_097_phase_1a_round*.md for verdict format.
2026-04-29T07:47:44.192756Z ERROR rmcp::transport::worker: worker quit with fatal: Transport channel closed, when Client(Reqwest(reqwest::Error { kind: Request, url: "https://chatgpt.com/backend-api/wham/apps", source: hyper_util::client::legacy::Error(Connect, Error { code: -9806, message: "connection closed via error" }) }))
codex
Reviewing the HEAD change as a code review only. I’m pulling the target diff, the referenced prior report format, and the affected test/implementation files first so I can check the staging sequence against the actual shell commands and existing conventions.
exec
/bin/zsh -lc 'rg -n "DEC-V61-099|V61-097|staging|container_work_dir|test_staging_renames_extracted_dir_into_run_id_suffix" .planning ui/backend/tests/test_solver_streamer.py ui/backend/services/case_solve/solver_streamer.py reports/codex_tool_reports -S' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
ui/backend/tests/test_solver_streamer.py:5:suffixed container_work_dir).
ui/backend/tests/test_solver_streamer.py:98:    # Intentionally NOT staging system/controlDict.
ui/backend/tests/test_solver_streamer.py:220:def test_run_id_suffixes_container_work_dir(tmp_path, monkeypatch):
ui/backend/tests/test_solver_streamer.py:221:    """The container_work_dir must be run_id-suffixed so concurrent
ui/backend/tests/test_solver_streamer.py:244:        assert prepared.container_work_dir.endswith(
ui/backend/tests/test_solver_streamer.py:252:# ────────── Post-R3 live-run defect (DEC-V61-099): staging order ──────────
ui/backend/tests/test_solver_streamer.py:255:def test_staging_renames_extracted_dir_into_run_id_suffix(tmp_path, monkeypatch):
ui/backend/tests/test_solver_streamer.py:256:    """Post-R3 live-run defect (DEC-V61-099 · caught on first LDC dogfood
ui/backend/tests/test_solver_streamer.py:257:    after V61-097 R4 RESOLVED). The V61-097 round-1 HIGH-2 fix introduced
ui/backend/tests/test_solver_streamer.py:258:    a run_id-suffixed container_work_dir but the staging sequence
ui/backend/tests/test_solver_streamer.py:261:      1. ``mkdir -p {container_work_dir}``  ← suffix dir pre-created
ui/backend/tests/test_solver_streamer.py:264:      3. ``if [ -d {BASE}/{case_id} ] && [ ! -d {container_work_dir} ];
ui/backend/tests/test_solver_streamer.py:271:    Codex's static review missed this in V61-097 because the staging
ui/backend/tests/test_solver_streamer.py:272:    test (``test_run_id_suffixes_container_work_dir``) only asserted the
ui/backend/tests/test_solver_streamer.py:285:    case_dir = tmp_path / "case_staging_regression"
ui/backend/tests/test_solver_streamer.py:290:    # staging sequence is correct.
ui/backend/tests/test_solver_streamer.py:303:    suffix_path_fragment = f"case_staging_regression-{forced_run_id}"
ui/backend/tests/test_solver_streamer.py:308:        assert prepared.container_work_dir.endswith(suffix_path_fragment)
ui/backend/tests/test_solver_streamer.py:310:        _release_run("case_staging_regression", forced_run_id)
ui/backend/tests/test_solver_streamer.py:316:    assert mkdir_cmds, "expected at least one mkdir during staging"
ui/backend/tests/test_solver_streamer.py:321:        f"REGRESSION: staging pre-created the run_id-suffixed dir via "
ui/backend/services/case_solve/solver_streamer.py:62:    in the same container_work_dir; both runs would race on
ui/backend/services/case_solve/solver_streamer.py:69:# share container_work_dir + log path. Sync threading lock is
ui/backend/services/case_solve/solver_streamer.py:211:    container_work_dir: str
ui/backend/services/case_solve/solver_streamer.py:221:    """Eager-mode preflight + staging + spawning.
ui/backend/services/case_solve/solver_streamer.py:278:        # Codex round-1 HIGH-2: container_work_dir is now run_id-suffixed
ui/backend/services/case_solve/solver_streamer.py:282:        container_work_dir = f"{CONTAINER_WORK_BASE}/{case_id}-{run_id}"
ui/backend/services/case_solve/solver_streamer.py:286:            # dir. The earlier version pre-created `{container_work_dir}`
ui/backend/services/case_solve/solver_streamer.py:288:            # {container_work_dir} ]`, which silently skipped the `mv`
ui/backend/services/case_solve/solver_streamer.py:293:            # find file system/controlDict. Caught post-R3 (V61-097
ui/backend/services/case_solve/solver_streamer.py:319:                    f"rm -rf {container_work_dir} && "
ui/backend/services/case_solve/solver_streamer.py:320:                    f"mv {CONTAINER_WORK_BASE}/{case_id} {container_work_dir} && "
ui/backend/services/case_solve/solver_streamer.py:321:                    f"chmod 777 {container_work_dir}",
ui/backend/services/case_solve/solver_streamer.py:333:            f"cd {container_work_dir} && "
ui/backend/services/case_solve/solver_streamer.py:355:        container_work_dir=container_work_dir,
ui/backend/services/case_solve/solver_streamer.py:398:    container_work_dir = prepared.container_work_dir
ui/backend/services/case_solve/solver_streamer.py:486:                    f"cd {container_work_dir} && ls -d [0-9]* 2>/dev/null",
ui/backend/services/case_solve/solver_streamer.py:492:                    bits, _ = container.get_archive(f"{container_work_dir}/{td}")
ui/backend/services/case_solve/solver_streamer.py:534:                cmd=["bash", "-c", f"rm -rf {container_work_dir}"]
reports/codex_tool_reports/dec_v61_097_phase_1a_round1.md:1:# Codex pre-merge review · DEC-V61-097 Phase-1A · Round 1
reports/codex_tool_reports/dec_v61_097_phase_1a_round1.md:16:`stream_icofoam()` is a generator, so the failure-mapping code at lines 170-243 only executes when `StreamingResponse` begins iterating. Container down / Docker SDK broken / staging failure produces a started SSE response and then an iterator exception or broken stream, not the structured HTTP rejection the route comment promises.
reports/codex_tool_reports/dec_v61_097_phase_1a_round1.md:20:### 2. HIGH — abort/restart race: no run-generation guard, shared container_work_dir
reports/codex_tool_reports/dec_v61_097_phase_1a_round1.md:23:Frontend "abort" only aborts the fetch reader; it does not stop the solver. Backend always uses the same `container_work_dir` derived from `case_host_dir.name`. Failure mode: navigate-away/remount can leave run A alive, run B starts in same directory, both race on `log.icoFoam` + time dirs + pulled-back artifacts. Frontend has no run-generation guard, so stale `done`/`error` from older invocation can mutate state after a newer `start()`.
reports/codex_tool_reports/dec_v61_097_phase_1a_round1.md:25:**Verbatim fix**: Introduce a per-case solve lock or server-issued `run_id`; reject concurrent `solve-stream` with `409 solve_already_running`, use `container_work_dir = f'{CONTAINER_WORK_BASE}/{case_host_dir.name}-{run_id}'`, and gate all frontend state writes on `if (runIdRef.current !== localRunId) return`.
reports/codex_tool_reports/dec_v61_097_phase_1a_round4.md:1:# Codex pre-merge review · DEC-V61-097 Phase-1A · Round 4 (closure)
reports/codex_tool_reports/dec_v61_097_phase_1a_round4.md:19:The DEC-V61-097 Phase-1A LDC end-to-end demo arc went through 4 Codex rounds before closure:
reports/codex_tool_reports/dec_v61_097_phase_1a_round4.md:43:DEC-V61-097 self-estimated 55% pre-Codex. Actual: needed 4 rounds before APPROVE/RESOLVED. Calibration drift = -55% (4 rounds vs. predicted ≤2). Logging in next retrospective per the methodology.
reports/codex_tool_reports/dec_v61_097_phase_1a_round2.md:1:# Codex pre-merge review · DEC-V61-097 Phase-1A · Round 2
reports/codex_tool_reports/2026-04-21_phase7bde_codex_review_round1.md:2806:ui/backend/routes/audit_package.py:68:# Staging dir is repo-local but gitignored (ui/backend/.audit_package_staging/).
reports/codex_tool_reports/2026-04-21_phase7bde_codex_review_round1.md:2807:ui/backend/routes/audit_package.py:71:_STAGING_ROOT = _REPO_ROOT / "ui" / "backend" / ".audit_package_staging"
reports/codex_tool_reports/2026-04-21_phase7bde_codex_review_round1.md:3035:src/foam_agent_adapter.py:6876:    # Phase 7a — field-artifact staging (VTK + sample CSV + residuals)
reports/codex_tool_reports/2026-04-21_phase7bde_codex_review_round1.md:3205:  6948	                        f"[WARN] staging {sub} failed: {e!r}", file=_sys.stderr,
reports/codex_tool_reports/2026-04-21_phase7bde_codex_review_round1.md:3485:   394	- the rollout also showed a preference for explicit gate-aware staging rather than silent activation -> preserve the planning-only vs active distinction clearly in Notion and repo docs [Task 2][Task 3]
.planning/reviews/dec_v61_052_bfs_round1_codex.log:2892:src/foam_agent_adapter.py:7193:    # Phase 7a — field-artifact staging (VTK + sample CSV + residuals)
.planning/reviews/dec_v61_052_bfs_round1_codex.log:3277:src/foam_agent_adapter.py:7193:    # Phase 7a — field-artifact staging (VTK + sample CSV + residuals)
.planning/reviews/dec_v61_052_bfs_round1_codex.log:4212:  7193	    # Phase 7a — field-artifact staging (VTK + sample CSV + residuals)
.planning/reviews/dec_v61_052_bfs_round1_codex.log:4295:  7276	                        f"[WARN] staging {sub} failed: {e!r}", file=_sys.stderr,
.planning/reviews/dec_v61_052_bfs_round1_codex.log: WARNING: stopped searching binary file after match (found "\0" byte around offset 409811)
reports/codex_tool_reports/dec_v61_097_phase_1a_round3.md:1:# Codex pre-merge review · DEC-V61-097 Phase-1A · Round 3
reports/codex_tool_reports/2026-04-21_pr5d_screen6_review.md:38:No blocking issue found. `_resolve_bundle_file()` constrains `bundle_id` to lowercase 32-hex, uses fixed server-side filenames, resolves the candidate path, and verifies it remains under `_STAGING_ROOT` before serving (`ui/backend/routes/audit_package.py:229-245`). There is no shell invocation, so shell metacharacters are irrelevant. Symlink escapes are rejected because `resolve()` is checked against the resolved staging root. The only residual caveat is the usual same-host TOCTOU window between validation and `FileResponse` opening the file; that matters only if an attacker can already mutate the staging tree on disk.
reports/codex_tool_reports/2026-04-21_pr5d_screen6_review.md:44:UUID4 `bundle_id` directories make accidental collision negligible, and per-request subdirectories avoid ordinary cross-request overwrite races (`ui/backend/routes/audit_package.py:154-163`). The real ops gap is retention: there is still no TTL, quota, or cleanup path, so the staging tree grows monotonically (`ui/backend/routes/audit_package.py:20-31`). That is an operational concern, but I did not treat it as the top production blocker relative to the findings above.
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round4.md:108:317:- rollout_summaries/2026-04-16T07-58-54-I0fB-notion_sync_v4_eval_staging_deploy_attempt.md (cwd=/Users/Zhuanz/AI-Notebooklm, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/16/rollout-2026-04-16T15-58-54-019d954c-d815-7f61-8927-b7ef3f2852d7.jsonl, updated_at=2026-04-16T16:35:02+00:00, thread_id=019d954c-d815-7f61-8927-b7ef3f2852d7, raw API path succeeded and produced reusable sync tooling)
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round4.md:109:327:- rollout_summaries/2026-04-16T07-58-54-I0fB-notion_sync_v4_eval_staging_deploy_attempt.md (cwd=/Users/Zhuanz/AI-Notebooklm, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/16/rollout-2026-04-16T15-58-54-019d954c-d815-7f61-8927-b7ef3f2852d7.jsonl, updated_at=2026-04-16T16:35:02+00:00, thread_id=019d954c-d815-7f61-8927-b7ef3f2852d7, local delivery completed but true staging blocked by environment))
reports/codex_tool_reports/dec_v61_099_round1.md:16:Pre-merge Codex review for DEC-V61-099 (post-R3 live-run defect closure on V61-097 R1 HIGH-2 staging order regression).
reports/codex_tool_reports/dec_v61_099_round1.md:19:- V61-097 R1 fix made container_work_dir run_id-suffixed but the staging sequence (mkdir suffix dir → put_archive to BASE → conditional mv with [ ! -d suffix ] guard) silently SKIPPED the rename because the mkdir made the suffix dir exist. icoFoam cd'd into the empty suffix dir → FOAM Fatal: cannot find file system/controlDict.
reports/codex_tool_reports/dec_v61_099_round1.md:20:- Caught on first LDC dogfood ~1 hour after V61-097 R4 RESOLVED.
reports/codex_tool_reports/dec_v61_099_round1.md:24:- ui/backend/services/case_solve/solver_streamer.py: lines 284-321 staging block. Pre-create CONTAINER_WORK_BASE only; rm -rf {suffix} && mv extracted dir → suffix && chmod.
reports/codex_tool_reports/dec_v61_099_round1.md:25:- ui/backend/tests/test_solver_streamer.py: NEW regression test test_staging_renames_extracted_dir_into_run_id_suffix. Tracks bash command sequence; asserts no mkdir of suffix path, no [ ! -d ] guard on mv.
reports/codex_tool_reports/dec_v61_099_round1.md:26:- .planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md: full root-cause + fix DEC.
reports/codex_tool_reports/dec_v61_099_round1.md:29:1. Correctness of the new staging sequence — any race condition? Any case where rm -rf is harmful?
reports/codex_tool_reports/dec_v61_099_round1.md:30:2. Defensive rm -rf {container_work_dir} — too broad? run_id is hex token from secrets so collision probability is negligible but verify.
reports/codex_tool_reports/dec_v61_099_round1.md:38:Reviewing the HEAD change as a code review only. I’m pulling the target diff, the referenced prior report format, and the affected test/implementation files first so I can check the staging sequence against the actual shell commands and existing conventions.
reports/codex_tool_reports/20260422_dec036b_codex_review.md:5199:   503	- the rollout also showed a preference for explicit gate-aware staging rather than silent activation -> preserve the planning-only vs active distinction clearly in Notion and repo docs [Task 2][Task 3]
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round1.md:168:390:- Local completion was substantial in the V4.0 rollout: retrieval eval tooling, RRF tuning, staging/UAT runbooks, README updates, Notion artifact/task/review rows, and `210 passed` regression validation [Task 4]
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round1.md:325:- the rollout also showed a preference for explicit gate-aware staging rather than silent activation -> preserve the planning-only vs active distinction clearly in Notion and repo docs [Task 2][Task 3]
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round1.md:3653:  6876	    # Phase 7a — field-artifact staging (VTK + sample CSV + residuals)
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round1.md:3736:  6959	                        f"[WARN] staging {sub} failed: {e!r}", file=_sys.stderr,
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round1.md:5535:   439	- the rollout also showed a preference for explicit gate-aware staging rather than silent activation -> preserve the planning-only vs active distinction clearly in Notion and repo docs [Task 2][Task 3]
reports/codex_tool_reports/20260422_dec045_wave3_F_taskrunner_reorder_result.md:881:- Symptom: deployment/UAT work stalls late -> cause: no SSH identities, no remote staging host details, and unfinished local vLLM build -> fix: report the missing host/access prerequisites clearly instead of pretending the local pack equals true staging [Task 4]
reports/codex_tool_reports/20260422_dec045_wave3_F_taskrunner_reorder_result.md:12290:- The user’s Phase 8 / Phase 9 instructions emphasized “先恢复摘要 + SELF-DISPATCH + 等我回复 GO” and later “继续推进开发，直至需要Opus 4.7介入”, indicating they want explicit gate-aware staging and not silent activation.
reports/codex_tool_reports/20260422_dec045_wave3_F_taskrunner_reorder_result.md:14065:    16	- The user’s Phase 8 / Phase 9 instructions emphasized “先恢复摘要 + SELF-DISPATCH + 等我回复 GO” and later “继续推进开发，直至需要Opus 4.7介入”, indicating they want explicit gate-aware staging and not silent activation.
.planning/strategic/workbench_long_horizon_roadmap_2026-04-29.md:317:**If forced to compress for time**: Era 1 + M15+M16+M18 (skip M17 CorrectionPattern, skip Era 3) is the minimum viable self-evolving system. ~10 milestones, ~6 months at the V61-097 pace.
.planning/strategic/workbench_long_horizon_roadmap_2026-04-29.md:381:V61-097 (M-PANELS Phase-1A) took **5 days end-to-end** including 4 Codex rounds for an arc of comparable complexity to most of these milestones. Realistic per-milestone time: **2-4 weeks** including Codex pre-merge rounds.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:307:- the rollout also showed a preference for explicit gate-aware staging rather than silent activation -> preserve the planning-only vs active distinction clearly in Notion and repo docs [Task 2][Task 3]
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:338:- The user’s Phase 8 / Phase 9 instructions emphasized “先恢复摘要 + SELF-DISPATCH + 等我回复 GO” and later “继续推进开发，直至需要Opus 4.7介入”, indicating they want explicit gate-aware staging and not silent activation.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1693:-        # on the metadata keys — staging runs best-effort.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:2684:  6876	    # Phase 7a — field-artifact staging (VTK + sample CSV + residuals)
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:2756:  6948	                        f"[WARN] staging {sub} failed: {e!r}", file=_sys.stderr,
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3060:   394	- the rollout also showed a preference for explicit gate-aware staging rather than silent activation -> preserve the planning-only vs active distinction clearly in Notion and repo docs [Task 2][Task 3]
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3145:    16	- The user’s Phase 8 / Phase 9 instructions emphasized “先恢复摘要 + SELF-DISPATCH + 等我回复 GO” and later “继续推进开发，直至需要Opus 4.7介入”, indicating they want explicit gate-aware staging and not silent activation.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:302:267:        # on the metadata keys — staging runs best-effort.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:753:  6876	    # Phase 7a — field-artifact staging (VTK + sample CSV + residuals)
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:825:  6948	                        f"[WARN] staging {sub} failed: {e!r}", file=_sys.stderr,
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:1170:   267	        # on the metadata keys — staging runs best-effort.
reports/codex_tool_reports/20260422_dec045_wave1_A_convergence_attestor_result.md:820:- The user’s Phase 8 / Phase 9 instructions emphasized “先恢复摘要 + SELF-DISPATCH + 等我回复 GO” and later “继续推进开发，直至需要Opus 4.7介入”, indicating they want explicit gate-aware staging and not silent activation.
reports/codex_tool_reports/20260422_dec045_wave1_A_convergence_attestor_result.md:13985:    16	- The user’s Phase 8 / Phase 9 instructions emphasized “先恢复摘要 + SELF-DISPATCH + 等我回复 GO” and later “继续推进开发，直至需要Opus 4.7介入”, indicating they want explicit gate-aware staging and not silent activation.
.planning/decisions/2026-04-21_phase5_5d_screen6_ui.md:14:  + tests + staging dir gitignore entry. Layout nav returns to disabled.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1682:reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1693:-        # on the metadata keys — staging runs best-effort.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1799:-        # on the metadata keys — staging runs best-effort.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:2381:  6948	                        f"[WARN] staging {sub} failed: {e!r}", file=_sys.stderr,
.planning/decisions/2026-04-21_phase7c_tier_c_visual_only_fanout.md:66:  - DEC-V61-031 (Phase 7a field capture — foamToVTK + artifact staging, case-agnostic)
.planning/decisions/2026-04-29_v61_098_m_ai_copilot_collab_kickoff.md:10:  - DEC-V61-097 (M-PANELS Phase-1A LDC end-to-end demo · closed 2026-04-29 commit c49fd11 · Codex 4-round arc RESOLVED · the demo that exposed the collab-first gap motivating this milestone)
.planning/decisions/2026-04-29_v61_098_m_ai_copilot_collab_kickoff.md:87:       after V61-097 close-out. M-AI-COPILOT kickoff brings it to
.planning/decisions/2026-04-29_v61_098_m_ai_copilot_collab_kickoff.md:124:  -10% vs M-PANELS Tier-A (60%) and -5% calibrated against V61-097
.planning/decisions/2026-04-29_v61_098_m_ai_copilot_collab_kickoff.md:135:    + AIActionEnvelope) doubled compared to V61-097 (which had
.planning/decisions/2026-04-29_v61_098_m_ai_copilot_collab_kickoff.md:150:  Calibration log: V61-097 self-estimated 55%, actual 4 rounds
.planning/decisions/2026-04-29_v61_098_m_ai_copilot_collab_kickoff.md:152:  larger contract surface area than V61-097 and (b) novel state
.planning/decisions/2026-04-29_v61_098_m_ai_copilot_collab_kickoff.md:153:  machine vs V61-097's mostly-mechanical preflight extraction.
.planning/decisions/2026-04-29_v61_098_m_ai_copilot_collab_kickoff.md:250:   V61-097's `genRef` pattern in SolveStreamContext.
.planning/decisions/2026-04-29_v61_098_m_ai_copilot_collab_kickoff.md:286:     M-PANELS arc per V61-097)
.planning/decisions/2026-04-29_v61_098_m_ai_copilot_collab_kickoff.md:314:   `annotation_revision` in envelope (mirrors V61-097 `genRef`).
.planning/strategic/m5_kickoff/spec_v2_2026-04-27.md:215:| **D2** | Confirmed cases at `user_drafts/imported/{case_id}/` permanent until user deletes · `_staging/` 30-day TTL · M5 may stub TTL job (cron + empty function) | **Unchanged** | Coherent with `case_drafts.py` precedent. M5.0 owns. |
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:2:decision_id: DEC-V61-099
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:3:title: M-PANELS Phase-1A · post-R3 live-run defect closure — solver_streamer staging order regression (V61-097 R1 HIGH-2 interaction)
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:4:status: Active (2026-04-29 · post-R3 live-run defect per RETRO-V61-053 addendum methodology · Codex pre-merge mandatory per RETRO-V61-001 "OpenFOAM solver 报错修复" trigger · CFDJerry caught on first LDC dogfood after V61-097 R4 RESOLVED commit `c49fd11`)
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:7:authored_under: V61-097 closure arc · post-R3 defect class per RETRO-V61-053 addendum
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:9:  - DEC-V61-097 (M-PANELS Phase-1A LDC end-to-end demo · closed 2026-04-29 commit c49fd11 · Codex 4-round arc RESOLVED · this DEC closes a DEFECT INTRODUCED IN ROUND 1 of that arc)
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:16:  - ui/backend/services/case_solve/solver_streamer.py (MODIFIED · staging order at lines 284-321 · pre-create BASE only · unconditional mv with rm -rf guard)
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:17:  - ui/backend/tests/test_solver_streamer.py (MODIFIED · NEW test_staging_renames_extracted_dir_into_run_id_suffix regression test · tracks bash command sequence)
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:35:  Bug fix to V61-097 BREAK_FREEZE'd code (slot 2/3 already consumed
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:36:  by V61-096 + V61-097 arc). This fix RIDES UNDER V61-097's existing
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:43:  Higher than typical (V61-097 was 55%) because:
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:66:that corrects the staging order introduced in V61-097 round 1 HIGH-2
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:67:(run_id-suffixed `container_work_dir`). Add a regression test
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:68:(`test_staging_renames_extracted_dir_into_run_id_suffix`) that pins
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:74:V61-097 round 1 HIGH-2 fix made `container_work_dir` run_id-suffixed
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:75:to prevent abandoned-run collisions. The staging sequence was:
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:80:    f"mkdir -p {container_work_dir} && chmod 777 {container_work_dir}"])  # ❶
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:84:    f"[ ! -d {container_work_dir} ]; then "
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:85:    f"mv {CONTAINER_WORK_BASE}/{case_id} {container_work_dir}; fi"])       # ❸
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:91:❸ guards the rename with `[ ! -d {container_work_dir} ]` — but ❶ just
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:102:The V61-097 round-1 verdict file (`reports/codex_tool_reports/
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:104:run-generation guard, shared `container_work_dir`" as HIGH-2.
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:112:- `test_run_id_suffixes_container_work_dir` (line 220-249) only
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:113:  checked that `prepared.container_work_dir.endswith(...)` — string
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:119:- Codex rounds 2/3/4 never re-examined the staging sequence because
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:121:  yield findings — orthogonal to staging.
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:136:    f"rm -rf {container_work_dir} && "
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:137:    f"mv {CONTAINER_WORK_BASE}/{case_id} {container_work_dir} && "
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:138:    f"chmod 777 {container_work_dir}"])                                      # ❸'
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:143:- ❸' is unconditional: `rm -rf {container_work_dir}` defensively
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:156:  `rm -rf {container_work_dir}` — the fix's defensive rm just
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:165:Added `test_staging_renames_extracted_dir_into_run_id_suffix` in
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:185:- **§11.1 BREAK_FREEZE**: rides under V61-097's existing slot 2/3.
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:202:2. **Bash command sequence audit**: when staging logic spans 3+
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:207:   one live-run smoke test before the arc is declared closed. V61-097
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:214:- DEC-V61-097 (predecessor · closed `c49fd11`) — this DEC closes a
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:215:  defect originating in V61-097 round 1
.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:223:  M9 (Tier-B AI) and beyond depend on Phase-1A staging being
.planning/decisions/2026-04-27_v61_075_p2_t2_docker_openfoam_substantialization.md:248:  churn before staging) — no parallel-session attribution drift
reports/codex_tool_reports/2026-04-21_phase7bde_codex_review_round2.md:2789:   394	- the rollout also showed a preference for explicit gate-aware staging rather than silent activation -> preserve the planning-only vs active distinction clearly in Notion and repo docs [Task 2][Task 3]
reports/codex_tool_reports/m_render_api_arc/round5.log:113:731:- Local completion was substantial in the V4.0 rollout: retrieval eval tooling, RRF tuning, staging/UAT runbooks, README updates, Notion artifact/task/review rows, and `210 passed` regression validation [Task 4]
.planning/strategic/m5_kickoff/brief_2026-04-27.md:118:  staging area for unconfirmed uploads at `_staging/` auto-cleans after 30
.planning/strategic/m_ai_copilot_kickoff/brief_2026-04-29.md:6:**Predecessor**: DEC-V61-097 (M-PANELS Phase-1A LDC end-to-end demo · closed 2026-04-29 commit `c49fd11` · Codex 4-round arc RESOLVED)
.planning/strategic/m_ai_copilot_kickoff/brief_2026-04-29.md:152:- **Self-pass-rate estimate**: **50%** — calibrated -5% vs V61-097's actual (4 rounds against 55% predicted, drift -55%). Reasoning: (a) human-AI dialog state machine has more failure modes than rAF batching; (b) face_id stability across mesh regen is novel; (c) two new persistent contracts (`face_annotations.yaml` + AI-action envelope) doubled compared to V61-097; (d) arbitrary-STL Tier-B is gated by Tier-A correctness so a single missed corner-case ripples.
.planning/strategic/m_ai_copilot_kickoff/brief_2026-04-29.md:168:- DEC-V61-097 (predecessor · M-PANELS Phase-1A): closed `c49fd11`
.planning/strategic/m_ai_copilot_kickoff/surface_scan_2026-04-29.md:153:   - `ui/backend/services/case_annotations/_yaml_io.py` (PyYAML wrapper · resolve(strict=True) on case_dir per V61-097 R3 symlink-containment precedent)
.planning/strategic/m_ai_copilot_kickoff/surface_scan_2026-04-29.md:160:3. **Symlink containment** — `case_annotations._yaml_io` MUST mirror the `_bc_source_files()` pattern from `bc_glb.py:192` (resolve(strict=True) + relative_to(case_root)). Codex round 1 of V61-097 flagged this for `bc_glb`; same pattern applies here per "byte-reproducibility sensitive paths" trigger in CLAUDE.md.
.planning/strategic/m_ai_copilot_kickoff/spec_v2_2026-04-29.md:200:| Race | DialogPanel renders stale questions after a fresh run | `genRef`-style guard on the StepPanel side, mirrors V61-097 SolveStreamContext |
.planning/strategic/m_ai_copilot_kickoff/spec_v2_2026-04-29.md:211:**50%** (calibrated -5% from V61-097's actual). Triggers PRE-MERGE Codex per RETRO-V61-001 ≤70% gate.
.planning/strategic/m_ai_copilot_kickoff/spec_v2_2026-04-29.md:214:- Two new persistent contracts (`face_annotations.yaml` + `AIActionEnvelope`) — schema review surface doubled relative to V61-097.
.planning/strategic/m_ai_copilot_kickoff/spec_v2_2026-04-29.md:236:- Predecessor · DEC-V61-097 closure: commit `c49fd11` · 4-round Codex arc RESOLVED
.planning/handoffs/2026-04-21_session_end_kickoff.md:90:rm -rf ui/backend/.audit_package_staging/*
.planning/phases/07a-field-capture/07a-01-PLAN.md:396:                        f"[WARN] staging {sub} failed: {e!r}", file=_sys.stderr,
reports/codex_tool_reports/m_render_api_arc/round1.log:4325:ui/backend/services/meshing_gmsh/to_foam.py:178:        bits, _ = container.get_archive(f"{container_work_dir}/constant/polyMesh")
reports/codex_tool_reports/m_render_api_arc/round1.log:7220:.planning/phases/07a-field-capture/07a-01-SUMMARY.md:15:  - "reports/phase5_fields/{case_id}/{timestamp}/ staging layout"
.planning/ops/2026-04-25_dual_track_plan.md:155:- `[line-a]` / `[line-b]` alone DO NOT escape — single-track tags; using one while staging the other track is exactly the cross-track-absorption mistake we are catching
.planning/ops/2026-04-25_dual_track_plan.md:279:**Why**: cross-track absorption 2x in one day under v1 (commits `e7909ac` + `0229af9`) traced to broad-scope staging commands sweeping unintended files into a tracked-track commit. The pre-commit + commit-msg hooks (§3 v2) are the safety net; `git add -p` is the primary discipline.
.planning/phases/07a-field-capture/07a-01-SUMMARY.md:15:  - "reports/phase5_fields/{case_id}/{timestamp}/ staging layout"
.planning/phases/07a-field-capture/07a-01-SUMMARY.md:48:Wave 1 of 3 for Phase 7a Sprint-1. Adapter-side (controlDict functions{} block + post-solver artifact staging) and driver-side (timestamp authoring + manifest write + fixture key) plumbing landed behind a two-flag opt-in (`spec.metadata['phase7a_timestamp']` + `spec.metadata['phase7a_case_id']`). Codex review deferred to Wave 3 per 三禁区 #1 (src/ >5 LOC) + RETRO-V61-001 triggers.
.planning/phases/07a-field-capture/07a-03-PLAN.md:432:  LDC run staging ≥3 artifacts; backend route returning them over HTTP with traversal guard
.planning/reviews/round_1_codex.log:338:- the rollout also showed a preference for explicit gate-aware staging rather than silent activation -> preserve the planning-only vs active distinction clearly in Notion and repo docs [Task 2][Task 3]
.planning/reviews/kogami/blind_control_v61_087_v1_2026-04-27/review.json:1:{"verdict":"APPROVE_WITH_COMMENTS","summary":"DEC-V61-087 v3 is a substantive, well-reasoned governance evolution that correctly addresses the v1/v2 failure modes identified by Codex and grounds its isolation contract in empirically verified flag behavior. The decision-arc coherence with RETRO-V61-001 (counter rules), Pivot Charter §4.7 (CLASS framework), and DEC-V61-073 (sampling audit/anti-drift) is strong, and the honest residual-risk enumeration in §3.5 plus the Tier-2 escalation triggers in §3.6 make this a falsifiable governance contract rather than a self-congratulatory one. Findings below are P1/P2 — none block ratification, but two should be addressed before W1 implementation begins.","findings":[{"severity":"P1","title":"Q1 canary verification method underspecified for the actual leak vector","problem":"§Open Questions Q1 (in v1 form) was the dominant unknown that v3 claims to have resolved via `--tools \"\"`. But the W0 dry-run described in `empirical_probes_completed` and the `Q1 canary regression test (monthly cron)` referenced in §3.6 and kogami_triggers.md §Tier 1 → Tier 2 are not specified concretely in the DEC itself. Specifically: (a) what canary token(s) are seeded into which input channels (cwd files? memory_paths target? env?), (b) what constitutes a 'leak' for sampling purposes (substring? embedding similarity? metadata-only?), (c) what is the sample-size n for monthly cron and how does it interact with the §3.5(3) `--tools \"\"` semantic-change risk acceptance. Without this specified in the DEC, the load-bearing 'physical capability removal' claim depends on an unspecified test, and Tier-2 escalation triggers can't be evaluated.","position":"§3.6 + Acceptance Criteria Q1 evidence","recommendation":"Add a §3.7 'Q1 canary specification' subsection (or expand AC item Q1) listing: (a) ≥3 distinct canary tokens placed in (i) project CLAUDE.md content, (ii) memory_paths.auto target file, (iii) env var; (b) leak definition = exact-substring match of any canary in subprocess `.result`; (c) n=5 runs per month minimum, all 5 must show 0 hits; (d) re-run mandatory on any `claude` CLI version change. Reference this section from §3.6 and from kogami_triggers.md Tier-2 list."},{"severity":"P1","title":"§4.4 paraphrase-laundering residual risk lacks a closure metric","problem":"§4.4 honestly acknowledges that regex blacklist + structured YAML can be defeated by paraphrase ('prior review identified a blocker'). The mitigation is described as 'sampling audit on accumulated review history can detect systematic paraphrase pattern' and Tier-2 escalation 'can include' ≥3 paraphrase instances. But (a) no concrete sampling cadence is specified (interval? sample size?), (b) the trigger uses 'can include' (advisory) rather than a binding count, (c) no owner is assigned. This is the same anti-pattern §10.5 was created to fix for §10 治理降级 — a falsifiability hole in an advisory rule. Without a concrete sampling rule, the §4.4 'improved, not closed' position drifts toward 'closed by hope'.","position":"§4.4 Honest residual risk paragraph + kogami_triggers.md §Strategic package authoring","recommendation":"Bind paraphrase-laundering audit to the existing §10.5 sampling-audit infrastructure: every Nth Kogami review (e.g., N=10) is sampled by the human reviewer (CFDJerry or external Opus session) for paraphrase patterns in author-supplied `rationale` fields. ≥3 confirmed paraphrase instances within a 30-review window → Tier-2 escalation MANDATORY (not advisory). Record cadence in §4.4 + cross-link from kogami_counter_rules.md §5.5."},{"severity":"P2","title":"Hard Boundary anti-self-approval rule has a recursion gap","problem":"kogami_triggers.md §Hard Boundary lists 7 files (P-1 through P-5 plus this file and kogami_counter_rules.md) that Kogami cannot self-approve. But DEC-V61-087 itself is the governance contract that establishes this boundary. A future DEC modifying DEC-V61-087's §3 (isolation contract) is not explicitly listed in the Hard Boundary file paths — only the implementation artifacts are. A clever framing ('we're not modifying P-1, just amending DEC-V61-087 §3 to relax which flags are required') could route around the rule. The DEC §4.2 'must NOT trigger' list mentions 'Kogami's own P-1/.../P-5 modifications' but not 'modifications to DEC-V61-087 itself or successor DECs that re-architect Kogami'.","position":"§4.2 must-NOT trigger list, last bullet · kogami_triggers.md §Hard Boundary file list","recommendation":"Extend the Hard Boundary to include 'any DEC whose `parent_dec` includes DEC-V61-087 OR whose subject is the Kogami isolation contract / counter rules / trigger rules'. Update both the DEC §4.2 enumeration and kogami_triggers.md §Hard Boundary. This closes the meta-recursion: Kogami v3.1 / v4 cannot self-approve its own governance evolution."},{"severity":"P2","title":"Counter provenance logic conflates Interpretation A and B without a binding tiebreaker","problem":"`autonomous_governance_counter_v61_provenance` says 'Interpretation B (STATE.md = SSOT, established by V61-086 provenance precedent), this DEC advances 52 → 53. Strict-bookkeeping Interpretation A would also yield 53 in this case (no intermediate silent advances since V61-075), so both interpretations agree here.' This is fine for V61-087 specifically but defers the actual choice. If a future DEC has divergent A/B values, there is no binding rule. RETRO-V61-001 says counter is pure telemetry, but provenance disputes are still live (V61-080/081/082/FORENSIC-FLAKE silent advances per STATE.md last_updated). Kogami's counter rules document (§5.6 Q4 dry-run) verifies historical compatibility but doesn't codify which interpretation is canonical going forward.","position":"frontmatter `autonomous_governance_counter_v61_provenance` + kogami_counter_rules.md §5.6","recommendation":"Either (a) add a one-line ratification in §5 of DEC-V61-087: 'Interpretation B (STATE.md last_updated = SSOT) is canonical going forward per V61-086 precedent', OR (b) open a follow-up DEC explicitly choosing. Without canonicalization, any future arc with intermediate silent advances will re-litigate. Low-cost fix; high value for future audit clarity."},{"severity":"P3","title":"Process Note's GSD-bypass justification is sound but creates a precedent worth flagging","problem":"§Process Note explains why this DEC didn't go through `/gsd-discuss-phase` (project's main-line is workbench-closed-loop M1-M4 COMPLETE; no governance phase exists in ROADMAP.md). The reasoning is correct. But this is the second governance-class artifact bypass in a row (DEC-V61-073 sampling audit was similar; ADR-002 W2 G-9 was similar per RETRO-V61-005). A pattern is forming where governance evolution lives outside the GSD phase model. This isn't wrong, but it's worth surfacing as a meta-question for the next arc-size retro.","position":"§Process Note","recommendation":"Add one sentence: 'If governance-class DECs continue to accumulate outside the GSD phase model (DEC-V61-073, ADR-002, this DEC), open a follow-up retro at counter ≥ 60 to evaluate whether ROADMAP.md should add a standing 'governance' phase or whether the current pattern is deliberate.' No action needed for V61-087 itself."}],"strategic_assessment":"Decision-arc coherence: STRONG. v3 directly consumes the v1/v2 Codex failures (prompt-contract not enforceable → process boundary still leaky → physical capability removal via `--tools \"\"`), with each failure mode acknowledged honestly in §Why. The W0 empirical fixes (cwd switch, stdin prompt) show real iteration, not paper-over. Compatibility with RETRO-V61-001 counter rules verified via Q4 dry-run; compatibility with DEC-V61-073 §10.5 sampling audit infrastructure is implicit (kogami_triggers.md Tier-2 list mentions Q5 keyword sampling but doesn't formally bind to §10.5). Roadmap fit: NEUTRAL-TO-POSITIVE. Workbench main-line M1-M4 is COMPLETE per ROADMAP.md, so this governance work doesn't compete with user-facing delivery. The ~1030 LOC estimate (mostly docs) is proportionate; the W0/W1/W2/W3/W4 staging with explicit user-ACK gates between waves is consistent with §10.4 Line-A/B isolation discipline. Retrospective completeness: STRONG. §3.5 enumerates 6 honest residual risks; §3.6 specifies Tier-2 escalation triggers; §Risks table covers 7 distinct failure modes with mitigations. Out-of-scope hygiene: STRONG. §Out of Scope explicitly lists 8 items including the recursion guard (Kogami doesn't review its own reviews) and the counter non-inflation invariant. The Hard Boundary in kogami_triggers.md correctly anticipates anti-self-approval but has a recursion gap (Finding P2 above). Risk-vs-benefit framing: SOUND. Notion-Opus replacement value (faster turnaround, tool access, automatic provenance) is real; the cost (loss of cross-model independence) is honestly acknowledged as 'Codex stays for code-layer; Kogami covers strategic-layer with same-model-but-different-process'. The Tier-1 → Tier-2 escalation path means this is a reversible, falsifiable bet rather than a one-way door.","recommended_next":"merge"}
.planning/reviews/kogami/blind_control_v61_087_v1_2026-04-27/review.md:15:Decision-arc coherence: STRONG. v3 directly consumes the v1/v2 Codex failures (prompt-contract not enforceable → process boundary still leaky → physical capability removal via `--tools ""`), with each failure mode acknowledged honestly in §Why. The W0 empirical fixes (cwd switch, stdin prompt) show real iteration, not paper-over. Compatibility with RETRO-V61-001 counter rules verified via Q4 dry-run; compatibility with DEC-V61-073 §10.5 sampling audit infrastructure is implicit (kogami_triggers.md Tier-2 list mentions Q5 keyword sampling but doesn't formally bind to §10.5). Roadmap fit: NEUTRAL-TO-POSITIVE. Workbench main-line M1-M4 is COMPLETE per ROADMAP.md, so this governance work doesn't compete with user-facing delivery. The ~1030 LOC estimate (mostly docs) is proportionate; the W0/W1/W2/W3/W4 staging with explicit user-ACK gates between waves is consistent with §10.4 Line-A/B isolation discipline. Retrospective completeness: STRONG. §3.5 enumerates 6 honest residual risks; §3.6 specifies Tier-2 escalation triggers; §Risks table covers 7 distinct failure modes with mitigations. Out-of-scope hygiene: STRONG. §Out of Scope explicitly lists 8 items including the recursion guard (Kogami doesn't review its own reviews) and the counter non-inflation invariant. The Hard Boundary in kogami_triggers.md correctly anticipates anti-self-approval but has a recursion gap (Finding P2 above). Risk-vs-benefit framing: SOUND. Notion-Opus replacement value (faster turnaround, tool access, automatic provenance) is real; the cost (loss of cross-model independence) is honestly acknowledged as 'Codex stays for code-layer; Kogami covers strategic-layer with same-model-but-different-process'. The Tier-1 → Tier-2 escalation path means this is a reversible, falsifiable bet rather than a one-way door.
.planning/reviews/dec_v61_052_bfs_round2_codex.log:234:- the rollout also showed a preference for explicit gate-aware staging rather than silent activation -> preserve the planning-only vs active distinction clearly in Notion and repo docs [Task 2][Task 3]
.planning/reviews/dec_v61_052_bfs_round2_codex.log: WARNING: stopped searching binary file after match (found "\0" byte around offset 825186)
.planning/reviews/kogami/m5_kickoff_governance_clearance_2026-04-27/prompt.txt:260:  staging area for unconfirmed uploads at `_staging/` auto-cleans after 30

exec
/bin/zsh -lc "sed -n '1,220p' /Users/Zhuanz/.codex/plugins/cache/openai-curated/superpowers/6807e4de4d8ceceefb51abd9e4ba3269030352c4/skills/using-superpowers/SKILL.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '1,240p' /Users/Zhuanz/.agents/skills/gsd-code-review/SKILL.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
---
name: using-superpowers
description: Use when starting any conversation - establishes how to find and use skills, requiring Skill tool invocation before ANY response including clarifying questions
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this skill.
</SUBAGENT-STOP>

<EXTREMELY-IMPORTANT>
If you think there is even a 1% chance a skill might apply to what you are doing, you ABSOLUTELY MUST invoke the skill.

IF A SKILL APPLIES TO YOUR TASK, YOU DO NOT HAVE A CHOICE. YOU MUST USE IT.

This is not negotiable. This is not optional. You cannot rationalize your way out of this.
</EXTREMELY-IMPORTANT>

exec
/bin/zsh -lc 'rg -n "exec_run|mkdir_res|rename_res|SolverRunError|_prepare_stream_icofoam|_active_runs|case_exit_code_check|BASE-mkdir|mv |rm -rf" ui/backend/services/case_solve/solver_streamer.py ui/backend/tests/test_solver_streamer.py' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
ui/backend/tests/test_solver_streamer.py:30:    def exec_run(self, cmd, stream: bool = False, demux: bool = False):  # noqa: D401, ARG002
ui/backend/tests/test_solver_streamer.py:34:        # Non-streaming exec_run is used for mkdir/ls — return empty.
ui/backend/tests/test_solver_streamer.py:88:    """Without system/controlDict, _prepare_stream_icofoam raises so
ui/backend/tests/test_solver_streamer.py:92:        SolverRunError,
ui/backend/tests/test_solver_streamer.py:93:        _prepare_stream_icofoam,
ui/backend/tests/test_solver_streamer.py:100:    with pytest.raises(SolverRunError, match="no system/controlDict"):
ui/backend/tests/test_solver_streamer.py:101:        _prepare_stream_icofoam(case_host_dir=case_dir)
ui/backend/tests/test_solver_streamer.py:108:        SolverRunError,
ui/backend/tests/test_solver_streamer.py:109:        _prepare_stream_icofoam,
ui/backend/tests/test_solver_streamer.py:142:    with pytest.raises(SolverRunError, match="not found"):
ui/backend/tests/test_solver_streamer.py:143:        _prepare_stream_icofoam(case_host_dir=case_dir)
ui/backend/tests/test_solver_streamer.py:152:        SolverRunError,
ui/backend/tests/test_solver_streamer.py:153:        _active_runs,
ui/backend/tests/test_solver_streamer.py:154:        _prepare_stream_icofoam,
ui/backend/tests/test_solver_streamer.py:161:    # SolverRunError("not running") AFTER claim_run, exercising the
ui/backend/tests/test_solver_streamer.py:166:    with pytest.raises(SolverRunError, match="not running"):
ui/backend/tests/test_solver_streamer.py:167:        _prepare_stream_icofoam(case_host_dir=case_dir)
ui/backend/tests/test_solver_streamer.py:168:    assert "case_release" not in _active_runs, (
ui/backend/tests/test_solver_streamer.py:177:    """A second _prepare_stream_icofoam for the same case while the
ui/backend/tests/test_solver_streamer.py:183:        _active_runs,
ui/backend/tests/test_solver_streamer.py:196:    assert case_id not in _active_runs
ui/backend/tests/test_solver_streamer.py:205:        _active_runs,
ui/backend/tests/test_solver_streamer.py:214:    assert _active_runs.get(case_id) == run_id_a
ui/backend/tests/test_solver_streamer.py:217:    assert case_id not in _active_runs
ui/backend/tests/test_solver_streamer.py:226:        _active_runs,
ui/backend/tests/test_solver_streamer.py:227:        _prepare_stream_icofoam,
ui/backend/tests/test_solver_streamer.py:240:        prepared = _prepare_stream_icofoam(
ui/backend/tests/test_solver_streamer.py:249:    assert "case_suffix" not in _active_runs
ui/backend/tests/test_solver_streamer.py:265:            then mv ... fi``  ← guard FALSE because step 1 just created
ui/backend/tests/test_solver_streamer.py:281:        _prepare_stream_icofoam,
ui/backend/tests/test_solver_streamer.py:289:    # Track every bash command sent to exec_run so we can assert the
ui/backend/tests/test_solver_streamer.py:294:        def exec_run(self, cmd, stream=False, demux=False):  # noqa: ARG002
ui/backend/tests/test_solver_streamer.py:297:            return super().exec_run(cmd, stream=stream, demux=demux)
ui/backend/tests/test_solver_streamer.py:305:        prepared = _prepare_stream_icofoam(
ui/backend/tests/test_solver_streamer.py:322:        f"mkdir -p — this is the V61-099 bug because the subsequent mv "
ui/backend/tests/test_solver_streamer.py:331:    mv_cmds = [c for c in bash_commands if " mv " in c and suffix_path_fragment in c]
ui/backend/tests/test_solver_streamer.py:336:    for mv in mv_cmds:
ui/backend/tests/test_solver_streamer.py:340:            f"after the (now-removed) pre-create mkdir. mv command: {mv!r}"
ui/backend/tests/test_solver_streamer.py:344:def test_staging_raises_on_nonzero_exec_run_exit_code(tmp_path, monkeypatch):
ui/backend/tests/test_solver_streamer.py:345:    """V61-099 Codex round 1 MED closure: every staging exec_run must
ui/backend/tests/test_solver_streamer.py:352:    This test forces the rename step's exec_run to return non-zero
ui/backend/tests/test_solver_streamer.py:353:    exit_code; preflight must raise SolverRunError before
ui/backend/tests/test_solver_streamer.py:357:        SolverRunError,
ui/backend/tests/test_solver_streamer.py:358:        _active_runs,
ui/backend/tests/test_solver_streamer.py:359:        _prepare_stream_icofoam,
ui/backend/tests/test_solver_streamer.py:362:    case_dir = tmp_path / "case_exit_code_check"
ui/backend/tests/test_solver_streamer.py:367:        """exec_run returns exit_code=0 for the BASE-mkdir but
ui/backend/tests/test_solver_streamer.py:371:        def exec_run(self, cmd, stream=False, demux=False):  # noqa: ARG002
ui/backend/tests/test_solver_streamer.py:376:                and " mv " in cmd[2]
ui/backend/tests/test_solver_streamer.py:377:                and "case_exit_code_check-" in cmd[2]
ui/backend/tests/test_solver_streamer.py:389:    with pytest.raises(SolverRunError, match="failed to rename"):
ui/backend/tests/test_solver_streamer.py:390:        _prepare_stream_icofoam(case_host_dir=case_dir)
ui/backend/tests/test_solver_streamer.py:394:    assert "case_exit_code_check" not in _active_runs, (
ui/backend/tests/test_solver_streamer.py:395:        "preflight failure on staging exec_run must release the run lock "
ui/backend/tests/test_solver_streamer.py:402:    surface as preflight SolverRunError. This is rarer in practice
ui/backend/tests/test_solver_streamer.py:404:    hold uniformly across staging exec_run calls.
ui/backend/tests/test_solver_streamer.py:407:        SolverRunError,
ui/backend/tests/test_solver_streamer.py:408:        _active_runs,
ui/backend/tests/test_solver_streamer.py:409:        _prepare_stream_icofoam,
ui/backend/tests/test_solver_streamer.py:417:        def exec_run(self, cmd, stream=False, demux=False):  # noqa: ARG002
ui/backend/tests/test_solver_streamer.py:430:    with pytest.raises(SolverRunError, match="failed to prepare container staging base"):
ui/backend/tests/test_solver_streamer.py:431:        _prepare_stream_icofoam(case_host_dir=case_dir)
ui/backend/tests/test_solver_streamer.py:433:    assert "case_mkdir_fail" not in _active_runs
ui/backend/tests/test_solver_streamer.py:449:        _active_runs,
ui/backend/tests/test_solver_streamer.py:450:        _prepare_stream_icofoam,
ui/backend/tests/test_solver_streamer.py:463:    prepared = _prepare_stream_icofoam(case_host_dir=case_dir)
ui/backend/tests/test_solver_streamer.py:464:    assert "case_immediate_close" in _active_runs
ui/backend/tests/test_solver_streamer.py:473:    assert "case_immediate_close" not in _active_runs, (
ui/backend/tests/test_solver_streamer.py:483:        _active_runs,
ui/backend/tests/test_solver_streamer.py:484:        _prepare_stream_icofoam,
ui/backend/tests/test_solver_streamer.py:496:    prepared = _prepare_stream_icofoam(case_host_dir=case_dir)
ui/backend/tests/test_solver_streamer.py:497:    assert "case_disconnect" in _active_runs
ui/backend/tests/test_solver_streamer.py:504:    assert "case_disconnect" not in _active_runs, (
ui/backend/services/case_solve/solver_streamer.py:7:``container.exec_run(stream=True)`` so log lines arrive incrementally;
ui/backend/services/case_solve/solver_streamer.py:50:    SolverRunError,
ui/backend/services/case_solve/solver_streamer.py:57:class SolveAlreadyRunning(SolverRunError):
ui/backend/services/case_solve/solver_streamer.py:73:_active_runs: dict[str, str] = {}  # case_id → run_id
ui/backend/services/case_solve/solver_streamer.py:79:        if case_id in _active_runs:
ui/backend/services/case_solve/solver_streamer.py:82:                f"(run_id={_active_runs[case_id]})"
ui/backend/services/case_solve/solver_streamer.py:85:        _active_runs[case_id] = run_id
ui/backend/services/case_solve/solver_streamer.py:92:        if _active_runs.get(case_id) == run_id:
ui/backend/services/case_solve/solver_streamer.py:93:            del _active_runs[case_id]
ui/backend/services/case_solve/solver_streamer.py:196:    """Output of :func:`_prepare_stream_icofoam`. Contains everything
ui/backend/services/case_solve/solver_streamer.py:215:def _prepare_stream_icofoam(
ui/backend/services/case_solve/solver_streamer.py:225:    ``exec_run(stream=True)``. All of these can raise
ui/backend/services/case_solve/solver_streamer.py:226:    :class:`SolverRunError` (or its :class:`SolveAlreadyRunning`
ui/backend/services/case_solve/solver_streamer.py:234:        raise SolverRunError(f"case dir not found: {case_host_dir}")
ui/backend/services/case_solve/solver_streamer.py:236:        raise SolverRunError(
ui/backend/services/case_solve/solver_streamer.py:248:            if case_id in _active_runs:
ui/backend/services/case_solve/solver_streamer.py:251:                    f"(run_id={_active_runs[case_id]})"
ui/backend/services/case_solve/solver_streamer.py:253:            _active_runs[case_id] = run_id
ui/backend/services/case_solve/solver_streamer.py:260:            raise SolverRunError(
ui/backend/services/case_solve/solver_streamer.py:268:                raise SolverRunError(
ui/backend/services/case_solve/solver_streamer.py:272:            raise SolverRunError(
ui/backend/services/case_solve/solver_streamer.py:276:            raise SolverRunError(f"docker init failed: {exc}") from exc
ui/backend/services/case_solve/solver_streamer.py:295:            # V61-099 round 1 MED closure: every staging exec_run is
ui/backend/services/case_solve/solver_streamer.py:302:            mkdir_res = container.exec_run(
ui/backend/services/case_solve/solver_streamer.py:309:            if getattr(mkdir_res, "exit_code", 0) != 0:
ui/backend/services/case_solve/solver_streamer.py:310:                raise SolverRunError(
ui/backend/services/case_solve/solver_streamer.py:312:                    f"{CONTAINER_WORK_BASE}: exec_run returned "
ui/backend/services/case_solve/solver_streamer.py:313:                    f"exit_code={mkdir_res.exit_code}"
ui/backend/services/case_solve/solver_streamer.py:320:                raise SolverRunError(
ui/backend/services/case_solve/solver_streamer.py:325:            # collide with an in-flight peer; defensively `rm -rf` first
ui/backend/services/case_solve/solver_streamer.py:328:            rename_res = container.exec_run(
ui/backend/services/case_solve/solver_streamer.py:332:                    f"rm -rf {container_work_dir} && "
ui/backend/services/case_solve/solver_streamer.py:333:                    f"mv {CONTAINER_WORK_BASE}/{case_id} {container_work_dir} && "
ui/backend/services/case_solve/solver_streamer.py:337:            if getattr(rename_res, "exit_code", 0) != 0:
ui/backend/services/case_solve/solver_streamer.py:338:                raise SolverRunError(
ui/backend/services/case_solve/solver_streamer.py:340:                    f"path {container_work_dir}: exec_run returned "
ui/backend/services/case_solve/solver_streamer.py:341:                    f"exit_code={rename_res.exit_code}. The extracted "
ui/backend/services/case_solve/solver_streamer.py:347:            raise SolverRunError(
ui/backend/services/case_solve/solver_streamer.py:359:            exec_result = container.exec_run(
ui/backend/services/case_solve/solver_streamer.py:365:            raise SolverRunError(f"docker SDK error invoking icoFoam: {exc}") from exc
ui/backend/services/case_solve/solver_streamer.py:395:      :func:`_prepare_stream_icofoam`; this function only consumes the
ui/backend/services/case_solve/solver_streamer.py:399:      ``_prepare_stream_icofoam`` then delegates.
ui/backend/services/case_solve/solver_streamer.py:413:        prepared = _prepare_stream_icofoam(
ui/backend/services/case_solve/solver_streamer.py:442:    # the very first SSE byte was still leaking _active_runs.
ui/backend/services/case_solve/solver_streamer.py:504:            ls_out = container.exec_run(
ui/backend/services/case_solve/solver_streamer.py:555:            container.exec_run(
ui/backend/services/case_solve/solver_streamer.py:556:                cmd=["bash", "-c", f"rm -rf {container_work_dir}"]

exec
/bin/zsh -lc 'git diff -- ui/backend/services/case_solve/solver_streamer.py ui/backend/tests/test_solver_streamer.py' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
codex
The target edits are staged, so I’m switching to the cached diff and exact line reads. That will let me verify both exit-code checks and whether the tests are tied to the right shell call sites rather than only matching text loosely.
exec
/bin/zsh -lc 'git diff --cached -- ui/backend/services/case_solve/solver_streamer.py ui/backend/tests/test_solver_streamer.py' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
diff --git a/ui/backend/services/case_solve/solver_streamer.py b/ui/backend/services/case_solve/solver_streamer.py
index 36c2c98..0acd1af 100644
--- a/ui/backend/services/case_solve/solver_streamer.py
+++ b/ui/backend/services/case_solve/solver_streamer.py
@@ -292,13 +292,26 @@ def _prepare_stream_icofoam(
             # icoFoam `cd`d into the empty dir → FOAM Fatal: cannot
             # find file system/controlDict. Caught post-R3 (V61-097
             # round 4 RESOLVED) on the first live LDC dogfood run.
-            container.exec_run(
+            # V61-099 round 1 MED closure: every staging exec_run is
+            # checked for non-zero exit_code. Without this, a failed
+            # mkdir/mv/chmod returns silently and the route emits a 200
+            # SSE stream that hits FOAM Fatal at the first icoFoam read
+            # — defeating the whole point of preflight. Codex flagged
+            # this as a residual hole in the same surface V61-099 was
+            # closing; fix in the same arc.
+            mkdir_res = container.exec_run(
                 cmd=[
                     "bash",
                     "-c",
                     f"mkdir -p {CONTAINER_WORK_BASE} && chmod 777 {CONTAINER_WORK_BASE}",
                 ]
             )
+            if getattr(mkdir_res, "exit_code", 0) != 0:
+                raise SolverRunError(
+                    f"failed to prepare container staging base "
+                    f"{CONTAINER_WORK_BASE}: exec_run returned "
+                    f"exit_code={mkdir_res.exit_code}"
+                )
             ok = container.put_archive(
                 path=CONTAINER_WORK_BASE,
                 data=_make_tarball(case_host_dir),
@@ -312,7 +325,7 @@ def _prepare_stream_icofoam(
             # collide with an in-flight peer; defensively `rm -rf` first
             # to clear any orphan from a prior abandoned run whose
             # finally cleanup didn't run (process kill, container restart).
-            container.exec_run(
+            rename_res = container.exec_run(
                 cmd=[
                     "bash",
                     "-c",
@@ -321,6 +334,15 @@ def _prepare_stream_icofoam(
                     f"chmod 777 {container_work_dir}",
                 ]
             )
+            if getattr(rename_res, "exit_code", 0) != 0:
+                raise SolverRunError(
+                    f"failed to rename staged case dir into run-suffixed "
+                    f"path {container_work_dir}: exec_run returned "
+                    f"exit_code={rename_res.exit_code}. The extracted "
+                    f"{CONTAINER_WORK_BASE}/{case_id} may be missing "
+                    f"(put_archive silently failed) or the run-suffixed "
+                    f"path is uncleanable."
+                )
         except docker.errors.DockerException as exc:
             raise SolverRunError(
                 f"docker SDK error preparing container workspace: {exc}"
diff --git a/ui/backend/tests/test_solver_streamer.py b/ui/backend/tests/test_solver_streamer.py
index b10c0d0..c0f85db 100644
--- a/ui/backend/tests/test_solver_streamer.py
+++ b/ui/backend/tests/test_solver_streamer.py
@@ -341,6 +341,98 @@ def test_staging_renames_extracted_dir_into_run_id_suffix(tmp_path, monkeypatch)
         )
 
 
+def test_staging_raises_on_nonzero_exec_run_exit_code(tmp_path, monkeypatch):
+    """V61-099 Codex round 1 MED closure: every staging exec_run must
+    check exit_code, not just trap Docker transport exceptions. Without
+    this, a failed mkdir/mv/chmod (e.g., extracted dir missing because
+    put_archive silently lost it; permissions wrong; suffixed path
+    uncleanable) returns silently and the route emits a 200 SSE stream
+    that hits FOAM Fatal at the first icoFoam read.
+
+    This test forces the rename step's exec_run to return non-zero
+    exit_code; preflight must raise SolverRunError before
+    StreamingResponse is constructed.
+    """
+    from ui.backend.services.case_solve.solver_streamer import (
+        SolverRunError,
+        _active_runs,
+        _prepare_stream_icofoam,
+    )
+
+    case_dir = tmp_path / "case_exit_code_check"
+    case_dir.mkdir()
+    _stage_minimal_case(case_dir)
+
+    class FailingRenameContainer(_FakeContainer):
+        """exec_run returns exit_code=0 for the BASE-mkdir but
+        exit_code=1 for the rename step (the rm/mv/chmod triplet).
+        """
+
+        def exec_run(self, cmd, stream=False, demux=False):  # noqa: ARG002
+            if (
+                isinstance(cmd, list)
+                and len(cmd) >= 3
+                and cmd[0] == "bash"
+                and " mv " in cmd[2]
+                and "case_exit_code_check-" in cmd[2]
+            ):
+                return types.SimpleNamespace(output=b"", exit_code=1)
+            if stream:
+                return types.SimpleNamespace(
+                    output=iter(self._exec_lines)
+                )
+            return types.SimpleNamespace(output=b"", exit_code=0)
+
+    container = FailingRenameContainer(status="running", exec_lines=[])
+    _install_fake_docker(monkeypatch, container)
+
+    with pytest.raises(SolverRunError, match="failed to rename"):
+        _prepare_stream_icofoam(case_host_dir=case_dir)
+
+    # The run lock must be released so the user can retry after fixing
+    # whatever caused the rename to fail.
+    assert "case_exit_code_check" not in _active_runs, (
+        "preflight failure on staging exec_run must release the run lock "
+        "(otherwise a failed staging permanently locks the case)"
+    )
+
+
+def test_staging_raises_on_nonzero_mkdir_exit_code(tmp_path, monkeypatch):
+    """Companion to the rename-fail test: BASE mkdir failure must also
+    surface as preflight SolverRunError. This is rarer in practice
+    (CONTAINER_WORK_BASE is usually writable) but the contract should
+    hold uniformly across staging exec_run calls.
+    """
+    from ui.backend.services.case_solve.solver_streamer import (
+        SolverRunError,
+        _active_runs,
+        _prepare_stream_icofoam,
+    )
+
+    case_dir = tmp_path / "case_mkdir_fail"
+    case_dir.mkdir()
+    _stage_minimal_case(case_dir)
+
+    class FailingMkdirContainer(_FakeContainer):
+        def exec_run(self, cmd, stream=False, demux=False):  # noqa: ARG002
+            if (
+                isinstance(cmd, list)
+                and len(cmd) >= 3
+                and cmd[0] == "bash"
+                and "mkdir -p" in cmd[2]
+            ):
+                return types.SimpleNamespace(output=b"", exit_code=1)
+            return types.SimpleNamespace(output=b"", exit_code=0)
+
+    container = FailingMkdirContainer(status="running", exec_lines=[])
+    _install_fake_docker(monkeypatch, container)
+
+    with pytest.raises(SolverRunError, match="failed to prepare container staging base"):
+        _prepare_stream_icofoam(case_host_dir=case_dir)
+
+    assert "case_mkdir_fail" not in _active_runs
+
+
 # ────────── Codex round-2 R2.1: GeneratorExit must release the lock ──────────
 
 

exec
/bin/zsh -lc "sed -n '1,240p' reports/codex_tool_reports/dec_v61_099_round2.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba ui/backend/services/case_solve/solver_streamer.py | sed -n '286,350p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   286	            # dir. The earlier version pre-created `{container_work_dir}`
   287	            # via `mkdir -p` then guarded the rename with `[ ! -d
   288	            # {container_work_dir} ]`, which silently skipped the `mv`
   289	            # because `mkdir -p` had just made the dir exist. Result:
   290	            # extracted case files stayed under `{CONTAINER_WORK_BASE}/
   291	            # {case_id}` (unsuffixed), the suffixed dir stayed empty,
   292	            # icoFoam `cd`d into the empty dir → FOAM Fatal: cannot
   293	            # find file system/controlDict. Caught post-R3 (V61-097
   294	            # round 4 RESOLVED) on the first live LDC dogfood run.
   295	            # V61-099 round 1 MED closure: every staging exec_run is
   296	            # checked for non-zero exit_code. Without this, a failed
   297	            # mkdir/mv/chmod returns silently and the route emits a 200
   298	            # SSE stream that hits FOAM Fatal at the first icoFoam read
   299	            # — defeating the whole point of preflight. Codex flagged
   300	            # this as a residual hole in the same surface V61-099 was
   301	            # closing; fix in the same arc.
   302	            mkdir_res = container.exec_run(
   303	                cmd=[
   304	                    "bash",
   305	                    "-c",
   306	                    f"mkdir -p {CONTAINER_WORK_BASE} && chmod 777 {CONTAINER_WORK_BASE}",
   307	                ]
   308	            )
   309	            if getattr(mkdir_res, "exit_code", 0) != 0:
   310	                raise SolverRunError(
   311	                    f"failed to prepare container staging base "
   312	                    f"{CONTAINER_WORK_BASE}: exec_run returned "
   313	                    f"exit_code={mkdir_res.exit_code}"
   314	                )
   315	            ok = container.put_archive(
   316	                path=CONTAINER_WORK_BASE,
   317	                data=_make_tarball(case_host_dir),
   318	            )
   319	            if not ok:
   320	                raise SolverRunError(
   321	                    "failed to stage case for streaming icoFoam"
   322	                )
   323	            # Atomically rename the extracted dir into the run_id-suffixed
   324	            # name. run_id is unique per run so the destination cannot
   325	            # collide with an in-flight peer; defensively `rm -rf` first
   326	            # to clear any orphan from a prior abandoned run whose
   327	            # finally cleanup didn't run (process kill, container restart).
   328	            rename_res = container.exec_run(
   329	                cmd=[
   330	                    "bash",
   331	                    "-c",
   332	                    f"rm -rf {container_work_dir} && "
   333	                    f"mv {CONTAINER_WORK_BASE}/{case_id} {container_work_dir} && "
   334	                    f"chmod 777 {container_work_dir}",
   335	                ]
   336	            )
   337	            if getattr(rename_res, "exit_code", 0) != 0:
   338	                raise SolverRunError(
   339	                    f"failed to rename staged case dir into run-suffixed "
   340	                    f"path {container_work_dir}: exec_run returned "
   341	                    f"exit_code={rename_res.exit_code}. The extracted "
   342	                    f"{CONTAINER_WORK_BASE}/{case_id} may be missing "
   343	                    f"(put_archive silently failed) or the run-suffixed "
   344	                    f"path is uncleanable."
   345	                )
   346	        except docker.errors.DockerException as exc:
   347	            raise SolverRunError(
   348	                f"docker SDK error preparing container workspace: {exc}"
   349	            ) from exc
   350	

exec
/bin/zsh -lc "nl -ba ui/backend/tests/test_solver_streamer.py | sed -n '340,438p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
2026-04-29T07:54:57.141134Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-research-deerflow/SKILL.md: missing YAML frontmatter delimited by ---
2026-04-29T07:54:57.141152Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-report-pretext/SKILL.md: missing YAML frontmatter delimited by ---
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
session id: 019dd83b-e4f5-7fa1-b1e2-7d0120852256
--------
user
Codex round 2 review for DEC-V61-099. Round 1 returned CHANGES_REQUIRED with 1 MED finding: staging exec_run calls didn't check exit_code, so silent shell-command failures (rm -rf failure, mv permission error, suffixed path uncleanable) would let _prepare_stream_icofoam return a stream that hits FOAM Fatal at first icoFoam read.

ROUND 1 CLOSURE (in working tree, not yet committed):

solver_streamer.py:
- Capture mkdir_res from BASE-mkdir exec_run
- Check getattr(mkdir_res, 'exit_code', 0) != 0 → raise SolverRunError('failed to prepare container staging base ...')
- Capture rename_res from rm/mv/chmod exec_run
- Check getattr(rename_res, 'exit_code', 0) != 0 → raise SolverRunError('failed to rename staged case dir ...')
- Both errors include the offending exit_code in the message

test_solver_streamer.py: TWO new tests
- test_staging_raises_on_nonzero_exec_run_exit_code: a FailingRenameContainer subclass returns exit_code=1 specifically when the rename command (mv ... case_exit_code_check-...) is dispatched. Asserts SolverRunError raised AND _active_runs lock is released for retry.
- test_staging_raises_on_nonzero_mkdir_exit_code: companion test that exercises the BASE-mkdir failure path. Asserts SolverRunError raised + lock released.
- Both tests verify behavior the previous regression test couldn't (it only inspected command strings, not exit_code handling — Codex round 1 specifically called this out).

11/11 solver_streamer tests pass locally including the two new ones.

REVIEW FOCUS:
1. Is the round-1 MED finding fully closed? exit_code check applied to BOTH staging exec_run sites?
2. Do the two new tests actually exercise the failure mode (i.e., would they fail against the buggy version that ignored exit_code)? Yes by inspection — the SolverRunError pytest.raises would not match if exit_code wasn't checked.
3. Any new HIGH/MED I missed in this round? The R1 verdict noted 'rm -rf {container_work_dir} does not look too broad' and 'chmod 777 ... I would not block merge on that alone' — those are already non-blocking per round 1.
4. Verbatim-exception verifiable now: closure matches R1 'Recommendation: check exit_code after both setup exec_run calls and add a test that forces the rename step to return non-zero' verbatim.

Return verdict: APPROVE / RESOLVED / CHANGES_REQUIRED with severity findings. Reference reports/codex_tool_reports/dec_v61_097_phase_1a_round*.md for verdict format.
codex
Reviewing the round-1 closure as a read-only code review. I’m loading the review format reference, the changed diff, and the current `solver_streamer` tests to verify whether the MED finding is actually closed and whether any new blocking issues were introduced.
exec
/bin/zsh -lc 'rg -n "DEC-V61-099|solver_streamer|round" /Users/Zhuanz/.codex/memories/MEMORY.md' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
164:- Symptom: engine tests expose wrong action flow around hand refill or turn advancement -> cause: game-loop assumptions were encoded before the intended two-actions-per-turn rhythm was settled -> fix: let tests drive the rhythm and avoid auto-refilling hands on discard unless the rules really require it [Task 1]
165:- Symptom: detached `nohup npm run dev -- --port 5174` does not stay up -> cause: this Vite server path was more reliable interactively than as a detached background launch -> fix: run `npm run dev -- --port 5174` interactively for local verification [Task 2]
361:- Symptom: a long one-shot backup/cleanup script flakes out mid-run -> cause: too much work is bundled around a moving `.git` target -> fix: split the work into smaller commands after the `.git` rename [Task 2]
468:- Symptom: the session appears to have multiple active runtime states at the end -> cause: a background demo server from browser smoke was still running -> fix: treat leftover demo-server processes as ephemeral verification artifacts and do not confuse them with handoff completion state [Task 2]
1073:- first customer, 我就是第一个客户, 不想在这个时间点立刻大幅转向, 完整的CFD工作台, OpenClaw, CFD workbench, V&V dashboard layer, /learn, /pro, FoamAgentExecutor, wizard_drivers, physics-grounded structured honesty, workbench_rollout_summary
1109:- Under the first-customer framing, the shortest realistic path is not a wholesale repositioning but wiring the existing wizard/SSE/backend flow from mock execution to real `FoamAgentExecutor`, then adding parameter override, history, and debug visibility around one real anchor case such as LDC [Task 1]
1115:- The useful default execution order for a handoff from these assessment runs is: restate the governing premise -> check facts/baseline -> fix environment/contracts -> choose one narrative (`demo-first` or `first-customer workbench`) -> then narrow implementation around anchor cases [Task 1][Task 3]
1240:- the user repeatedly constrained work to one anchor case and very tight file landing zones: "只改" specific files around `lid_driven_cavity_benchmark` -> avoid opportunistic scope growth [Task 1]
1261:- Symptom: the assistant frames work around an outdated phase narrative -> cause: Notion cockpit already moved to a newer hold/accepted state -> fix: re-read the current control-plane state before committing to a phase framing [Task 2]
1327:scope: Parse the source control document, freeze the deploy logic from explicit user corrections, build the `well_harness` simulation around that truth, and separate controller correctness from plant-model or demo-scope drift.
1348:- well_harness, controller.py, switches.py, plant.py, scenarios.py, runner.py, cli.py, nominal-deploy, deviation audit, simplified plant, 115 tests OK, logic1 around 0.5s, logic2 around 1.2s, logic3 around 1.9s, logic4 around 5.0s
1361:- The frozen deploy logic that matched the user’s corrections was: `logic1 = RA < 6 ft + SW1 + not inhibited + not deployed`; `logic2 = engine running + on ground + not inhibited + SW2 + EEC enable`; `logic3 = engine running + on ground + not inhibited + TLS unlocked + N1k below limit + TRA <= -11.74°`; `logic4 = 90% deploy + -32° < TRA < 0° + on ground + engine running` [Task 1]
1383:- rollout_summaries/2026-04-07T06-20-24-tGb4-round_92_direct_vdt_control_flatter_logic_board.md (cwd=/Users/Zhuanz/20260407 YJX AI FANTUI LogicMVP, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/07/rollout-2026-04-07T14-20-24-019d6699-6f65-7712-ba2d-13ed0f64e87e.jsonl, updated_at=2026-04-08T14:50:07+00:00, thread_id=019d6699-6f65-7712-ba2d-13ed0f64e87e, final Round 92 reflow with preserved endpoint contracts)
1437:- for leadership-facing summaries, the user asked for "真实、可靠的AI coding方法" and "不能包含任何英文专业术语，除非你能详细解释" -> write in plain Chinese for non-software readers and ground the story in evidence rather than jargon [Task 4]
1446:- The stable storyline for explanation is: logic truth first, then contracts/tests, then controlled demo answers, then cockpit UI, then QA/polish rounds [Task 4]
1985:- across these multi-file implementation tasks, the user repeatedly said "Run in background" -> for long cross-file slices in this repo, do the wiring and targeted verification in one pass instead of asking them to orchestrate each substep [Task 1][Task 2][Task 3][Task 4]
2053:- Symptom: a review answer drifts into general commentary or architecture advice -> cause: treating “review” as broad feedback instead of a defect audit -> fix: report only grounded correctness findings with file/line references [Task 1]
2147:- Thresholds used in the installed workflow: keep active context around 35%-45%, start compressing around 50%, checkpoint by about 65%, and rebuild near 75% [Task 1]

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
/bin/zsh -lc 'rg --files reports/codex_tool_reports' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
reports/codex_tool_reports/2026-04-28_m_viz_bundle_steps_3_to_6_codex_review_round4.md
reports/codex_tool_reports/2026-04-21_pr21_bfs_guard_review.md
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_prompt.md
reports/codex_tool_reports/2026-04-21_phase7bde_codex_review_round1.md
reports/codex_tool_reports/dec_v61_074_t1b23_postcommit_round1.md
reports/codex_tool_reports/run_compare_api_r2.md
reports/codex_tool_reports/bug1_sse_disconnect_persistence_r2.md
reports/codex_tool_reports/20260422_dec045_wave1_A_convergence_attestor_result.md
reports/codex_tool_reports/dec_v61_057_round2.md
reports/codex_tool_reports/20260422_dec038_codex_review.md
reports/codex_tool_reports/2026-04-28_m_viz_bundle_steps_3_to_6_codex_review_round1.md
reports/codex_tool_reports/bug1_sse_disconnect_persistence_r3.md
reports/codex_tool_reports/20260422_dec045_wave3_G_tests_prompt.md
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round2.md
reports/codex_tool_reports/2026-04-21_pr5c1_codex_followup_review.md
reports/codex_tool_reports/20260422_dec045_wave3_F_taskrunner_reorder_prompt.md
reports/codex_tool_reports/20260422_dec036_036c_039_backfill_note.md
reports/codex_tool_reports/2026-04-28_m_viz_bundle_steps_3_to_6_codex_review_round5.md
reports/codex_tool_reports/dec_v61_074_t1b1_round1.md
reports/codex_tool_reports/industrial_workbench_meeting_2026-04-25.md
reports/codex_tool_reports/2026-04-21_pr5c_hmac_review.md
reports/codex_tool_reports/dec_v61_058_round2_review.md
reports/codex_tool_reports/dec_v61_087_v3_kogami_bootstrap_r1.md
reports/codex_tool_reports/dec_v61_087_v2_kogami_bootstrap_r1.md
reports/codex_tool_reports/2026-04-28_m_panels_arc_codex_review_round3.md
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md
reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round1.md
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md
reports/codex_tool_reports/20260422_dec045_wave1_A_convergence_attestor_prompt.md
reports/codex_tool_reports/dec_v61_075_t2_3_post_commit_round2.md
reports/codex_tool_reports/dec_v61_097_phase_1a_round1.md
reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round5.md
reports/codex_tool_reports/20260422_dec045_wave3_F_taskrunner_reorder_result.md
reports/codex_tool_reports/20260422_dec036b_codex_prompt.md
reports/codex_tool_reports/dec_v61_087_kogami_bootstrap_r1.md
reports/codex_tool_reports/dec_v61_075_t2_3_post_commit_round3.md
reports/codex_tool_reports/20260422_dec045_wave3_G_tests_result.md
reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round4.md
reports/codex_tool_reports/dec_v61_099_round2.md
reports/codex_tool_reports/2026-04-28_m_panels_arc_codex_review_round2.md
reports/codex_tool_reports/dec_v61_052_bfs_round1_findings.md
reports/codex_tool_reports/dec_v61_097_phase_1a_round4.md
reports/codex_tool_reports/README.md
reports/codex_tool_reports/dec_v61_071_round2.md
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md
reports/codex_tool_reports/2026-04-21_pr5d_screen6_review.md
reports/codex_tool_reports/20260422_dec045_wave2_E_tests_result.md
reports/codex_tool_reports/dec_v61_097_phase_1a_round3.md
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round4.md
reports/codex_tool_reports/dec_v61_099_round1.md
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md
reports/codex_tool_reports/2026-04-28_m_panels_arc_codex_review_round1.md
reports/codex_tool_reports/20260422_dec045_wave1_B_comparator_gates_prompt.md
reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round3.md
reports/codex_tool_reports/dec_v61_075_t2_3_post_commit_round4.md
reports/codex_tool_reports/dec_v61_071_round1.md
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md
reports/codex_tool_reports/dec_v61_058_plan_review.md
reports/codex_tool_reports/20260422_dec038_codex_prompt.md
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md
reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round2.md
reports/codex_tool_reports/dec_v61_075_t2_3_post_commit_round5.md
reports/codex_tool_reports/2026-04-21_pr5c2_m3_review.md
reports/codex_tool_reports/2026-04-28_m_panels_arc_codex_review_round4.md
reports/codex_tool_reports/dec_v61_097_phase_1a_round2.md
reports/codex_tool_reports/dec_v61_075_t2_3_post_commit_round1.md
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md
reports/codex_tool_reports/2026-04-21_pr22_duct_dispatch_review.md
reports/codex_tool_reports/dec_v61_057_plan_review.md
reports/codex_tool_reports/2026-04-28_m_viz_bundle_steps_3_to_6_codex_review_round2.md
reports/codex_tool_reports/20260422_v62_takeover_notion_sync_draft.md
reports/codex_tool_reports/dec_v61_072_sampling_audit_first_execution.md
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round1.md
reports/codex_tool_reports/2026-04-21_pr20_foam_adapter_review.md
reports/codex_tool_reports/2026-04-21_pr23_build_fingerprint_review.md
reports/codex_tool_reports/20260422_dec045_wave2_E_tests_prompt.md
reports/codex_tool_reports/dec_v61_074_t1b1_round2.md
reports/codex_tool_reports/2026-04-21_pr5d1_closure_review.md
reports/codex_tool_reports/20260422_dec045_wave1_B_comparator_gates_result.md
reports/codex_tool_reports/dec_v61_087_v3_kogami_bootstrap_r2.md
reports/codex_tool_reports/20260422_dec036b_codex_review.md
reports/codex_tool_reports/dec_v61_057_round4.md
reports/codex_tool_reports/2026-04-21_phase7bc_render_report_codex_review.md
reports/codex_tool_reports/m_render_api_arc/README.md
reports/codex_tool_reports/m_render_api_arc/round4.log
reports/codex_tool_reports/m_render_api_arc/round5.log
reports/codex_tool_reports/m_render_api_arc/round2.log
reports/codex_tool_reports/m_render_api_arc/round3.log
reports/codex_tool_reports/m_render_api_arc/round1.log
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_prompt.md
reports/codex_tool_reports/2026-04-21_phase7bde_codex_review_round2.md
reports/codex_tool_reports/dec_v61_074_t1b23_postcommit_round2.md
reports/codex_tool_reports/bug1_sse_disconnect_persistence_r1.md
reports/codex_tool_reports/run_compare_api_r1.md
reports/codex_tool_reports/2026-04-28_m_viz_bundle_steps_3_to_6_codex_review_round3.md
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_prompt.md
reports/codex_tool_reports/dec_v61_058_round1_review.md
reports/codex_tool_reports/dec_v61_057_round1.md

exec
/bin/zsh -lc 'git status --short' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
 M ui/backend/routes/case_solve.py
M  ui/backend/services/case_solve/solver_streamer.py
M  ui/backend/tests/test_solver_streamer.py
?? .claude/MODEL_ROUTING.md
?? .planning/strategic/2026-04-26_claude_code_kickoff_prompt_pivot_v1_1.md
?? .planning/strategic/2026-04-26_strategic_advisory_memo.md
?? .planning/strategic/2026-04-26_strategic_advisory_memo_002_post_three_answers.md
?? .planning/strategic/PROJECT_HISTORY_NARRATIVE.md
?? docs/methodology/project_introduction.md
?? reports/codex_tool_reports/dec_v61_099_round1.md

 succeeded in 0ms:
   340	            f"after the (now-removed) pre-create mkdir. mv command: {mv!r}"
   341	        )
   342	
   343	
   344	def test_staging_raises_on_nonzero_exec_run_exit_code(tmp_path, monkeypatch):
   345	    """V61-099 Codex round 1 MED closure: every staging exec_run must
   346	    check exit_code, not just trap Docker transport exceptions. Without
   347	    this, a failed mkdir/mv/chmod (e.g., extracted dir missing because
   348	    put_archive silently lost it; permissions wrong; suffixed path
   349	    uncleanable) returns silently and the route emits a 200 SSE stream
   350	    that hits FOAM Fatal at the first icoFoam read.
   351	
   352	    This test forces the rename step's exec_run to return non-zero
   353	    exit_code; preflight must raise SolverRunError before
   354	    StreamingResponse is constructed.
   355	    """
   356	    from ui.backend.services.case_solve.solver_streamer import (
   357	        SolverRunError,
   358	        _active_runs,
   359	        _prepare_stream_icofoam,
   360	    )
   361	
   362	    case_dir = tmp_path / "case_exit_code_check"
   363	    case_dir.mkdir()
   364	    _stage_minimal_case(case_dir)
   365	
   366	    class FailingRenameContainer(_FakeContainer):
   367	        """exec_run returns exit_code=0 for the BASE-mkdir but
   368	        exit_code=1 for the rename step (the rm/mv/chmod triplet).
   369	        """
   370	
   371	        def exec_run(self, cmd, stream=False, demux=False):  # noqa: ARG002
   372	            if (
   373	                isinstance(cmd, list)
   374	                and len(cmd) >= 3
   375	                and cmd[0] == "bash"
   376	                and " mv " in cmd[2]
   377	                and "case_exit_code_check-" in cmd[2]
   378	            ):
   379	                return types.SimpleNamespace(output=b"", exit_code=1)
   380	            if stream:
   381	                return types.SimpleNamespace(
   382	                    output=iter(self._exec_lines)
   383	                )
   384	            return types.SimpleNamespace(output=b"", exit_code=0)
   385	
   386	    container = FailingRenameContainer(status="running", exec_lines=[])
   387	    _install_fake_docker(monkeypatch, container)
   388	
   389	    with pytest.raises(SolverRunError, match="failed to rename"):
   390	        _prepare_stream_icofoam(case_host_dir=case_dir)
   391	
   392	    # The run lock must be released so the user can retry after fixing
   393	    # whatever caused the rename to fail.
   394	    assert "case_exit_code_check" not in _active_runs, (
   395	        "preflight failure on staging exec_run must release the run lock "
   396	        "(otherwise a failed staging permanently locks the case)"
   397	    )
   398	
   399	
   400	def test_staging_raises_on_nonzero_mkdir_exit_code(tmp_path, monkeypatch):
   401	    """Companion to the rename-fail test: BASE mkdir failure must also
   402	    surface as preflight SolverRunError. This is rarer in practice
   403	    (CONTAINER_WORK_BASE is usually writable) but the contract should
   404	    hold uniformly across staging exec_run calls.
   405	    """
   406	    from ui.backend.services.case_solve.solver_streamer import (
   407	        SolverRunError,
   408	        _active_runs,
   409	        _prepare_stream_icofoam,
   410	    )
   411	
   412	    case_dir = tmp_path / "case_mkdir_fail"
   413	    case_dir.mkdir()
   414	    _stage_minimal_case(case_dir)
   415	
   416	    class FailingMkdirContainer(_FakeContainer):
   417	        def exec_run(self, cmd, stream=False, demux=False):  # noqa: ARG002
   418	            if (
   419	                isinstance(cmd, list)
   420	                and len(cmd) >= 3
   421	                and cmd[0] == "bash"
   422	                and "mkdir -p" in cmd[2]
   423	            ):
   424	                return types.SimpleNamespace(output=b"", exit_code=1)
   425	            return types.SimpleNamespace(output=b"", exit_code=0)
   426	
   427	    container = FailingMkdirContainer(status="running", exec_lines=[])
   428	    _install_fake_docker(monkeypatch, container)
   429	
   430	    with pytest.raises(SolverRunError, match="failed to prepare container staging base"):
   431	        _prepare_stream_icofoam(case_host_dir=case_dir)
   432	
   433	    assert "case_mkdir_fail" not in _active_runs
   434	
   435	
   436	# ────────── Codex round-2 R2.1: GeneratorExit must release the lock ──────────
   437	
   438	

exec
/bin/zsh -lc "nl -ba ui/backend/services/case_solve/solver_streamer.py | sed -n '215,360p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba ui/backend/tests/test_solver_streamer.py | sed -n '1,120p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   215	def _prepare_stream_icofoam(
   216	    *,
   217	    case_host_dir: Path,
   218	    container_name: str = CONTAINER_NAME,
   219	    run_id: str | None = None,
   220	) -> _PreparedStream:
   221	    """Eager-mode preflight + staging + spawning.
   222	
   223	    Validates the case, claims a per-case run_id (HIGH-2), connects to
   224	    Docker, stages the tarball, and spawns icoFoam with
   225	    ``exec_run(stream=True)``. All of these can raise
   226	    :class:`SolverRunError` (or its :class:`SolveAlreadyRunning`
   227	    subclass) — the route layer catches and translates to HTTP 4xx/5xx
   228	    BEFORE returning the StreamingResponse.
   229	
   230	    On any failure here, the run_id is released so a retry can claim
   231	    it again.
   232	    """
   233	    if not case_host_dir.is_dir():
   234	        raise SolverRunError(f"case dir not found: {case_host_dir}")
   235	    if not (case_host_dir / "system" / "controlDict").is_file():
   236	        raise SolverRunError(
   237	            f"no system/controlDict at {case_host_dir} — run "
   238	            "setup-bc first."
   239	        )
   240	
   241	    case_id = case_host_dir.name
   242	    if run_id is None:
   243	        run_id = _claim_run(case_id)
   244	    else:
   245	        # Caller-supplied run_id (tests). Still register so concurrent
   246	        # callers see the in-flight state.
   247	        with _runs_lock:
   248	            if case_id in _active_runs:
   249	                raise SolveAlreadyRunning(
   250	                    f"solve already running for case {case_id!r} "
   251	                    f"(run_id={_active_runs[case_id]})"
   252	                )
   253	            _active_runs[case_id] = run_id
   254	
   255	    try:
   256	        try:
   257	            import docker  # type: ignore[import-not-found]
   258	            import docker.errors  # type: ignore[import-not-found]
   259	        except ImportError as exc:
   260	            raise SolverRunError(
   261	                "docker SDK is not installed."
   262	            ) from exc
   263	
   264	        try:
   265	            client = docker.from_env()
   266	            container = client.containers.get(container_name)
   267	            if container.status != "running":
   268	                raise SolverRunError(
   269	                    f"container '{container_name}' is not running."
   270	                )
   271	        except docker.errors.NotFound as exc:
   272	            raise SolverRunError(
   273	                f"container '{container_name}' not found."
   274	            ) from exc
   275	        except docker.errors.DockerException as exc:
   276	            raise SolverRunError(f"docker init failed: {exc}") from exc
   277	
   278	        # Codex round-1 HIGH-2: container_work_dir is now run_id-suffixed
   279	        # so concurrent runs (in spite of the lock, e.g. abandoned runs
   280	        # whose lock entry was cleared by /finally) cannot collide on
   281	        # log.icoFoam or the time directories.
   282	        container_work_dir = f"{CONTAINER_WORK_BASE}/{case_id}-{run_id}"
   283	
   284	        try:
   285	            # Pre-create the BASE only — NOT the run_id-suffixed work
   286	            # dir. The earlier version pre-created `{container_work_dir}`
   287	            # via `mkdir -p` then guarded the rename with `[ ! -d
   288	            # {container_work_dir} ]`, which silently skipped the `mv`
   289	            # because `mkdir -p` had just made the dir exist. Result:
   290	            # extracted case files stayed under `{CONTAINER_WORK_BASE}/
   291	            # {case_id}` (unsuffixed), the suffixed dir stayed empty,
   292	            # icoFoam `cd`d into the empty dir → FOAM Fatal: cannot
   293	            # find file system/controlDict. Caught post-R3 (V61-097
   294	            # round 4 RESOLVED) on the first live LDC dogfood run.
   295	            # V61-099 round 1 MED closure: every staging exec_run is
   296	            # checked for non-zero exit_code. Without this, a failed
   297	            # mkdir/mv/chmod returns silently and the route emits a 200
   298	            # SSE stream that hits FOAM Fatal at the first icoFoam read
   299	            # — defeating the whole point of preflight. Codex flagged
   300	            # this as a residual hole in the same surface V61-099 was
   301	            # closing; fix in the same arc.
   302	            mkdir_res = container.exec_run(
   303	                cmd=[
   304	                    "bash",
   305	                    "-c",
   306	                    f"mkdir -p {CONTAINER_WORK_BASE} && chmod 777 {CONTAINER_WORK_BASE}",
   307	                ]
   308	            )
   309	            if getattr(mkdir_res, "exit_code", 0) != 0:
   310	                raise SolverRunError(
   311	                    f"failed to prepare container staging base "
   312	                    f"{CONTAINER_WORK_BASE}: exec_run returned "
   313	                    f"exit_code={mkdir_res.exit_code}"
   314	                )
   315	            ok = container.put_archive(
   316	                path=CONTAINER_WORK_BASE,
   317	                data=_make_tarball(case_host_dir),
   318	            )
   319	            if not ok:
   320	                raise SolverRunError(
   321	                    "failed to stage case for streaming icoFoam"
   322	                )
   323	            # Atomically rename the extracted dir into the run_id-suffixed
   324	            # name. run_id is unique per run so the destination cannot
   325	            # collide with an in-flight peer; defensively `rm -rf` first
   326	            # to clear any orphan from a prior abandoned run whose
   327	            # finally cleanup didn't run (process kill, container restart).
   328	            rename_res = container.exec_run(
   329	                cmd=[
   330	                    "bash",
   331	                    "-c",
   332	                    f"rm -rf {container_work_dir} && "
   333	                    f"mv {CONTAINER_WORK_BASE}/{case_id} {container_work_dir} && "
   334	                    f"chmod 777 {container_work_dir}",
   335	                ]
   336	            )
   337	            if getattr(rename_res, "exit_code", 0) != 0:
   338	                raise SolverRunError(
   339	                    f"failed to rename staged case dir into run-suffixed "
   340	                    f"path {container_work_dir}: exec_run returned "
   341	                    f"exit_code={rename_res.exit_code}. The extracted "
   342	                    f"{CONTAINER_WORK_BASE}/{case_id} may be missing "
   343	                    f"(put_archive silently failed) or the run-suffixed "
   344	                    f"path is uncleanable."
   345	                )
   346	        except docker.errors.DockerException as exc:
   347	            raise SolverRunError(
   348	                f"docker SDK error preparing container workspace: {exc}"
   349	            ) from exc
   350	
   351	        # Spawn icoFoam. ``stdbuf -oL`` line-buffers stdout so PISO
   352	        # iterations arrive promptly instead of in 4KB chunks.
   353	        bash_cmd = (
   354	            "source /opt/openfoam10/etc/bashrc && "
   355	            f"cd {container_work_dir} && "
   356	            "stdbuf -oL -eL icoFoam 2>&1"
   357	        )
   358	        try:
   359	            exec_result = container.exec_run(
   360	                cmd=["bash", "-c", bash_cmd],

 succeeded in 0ms:
     1	"""Tests for the streaming icoFoam runner (Codex round-1 round-2 follow-up).
     2	
     3	Covers HIGH-1 (preflight raises BEFORE the generator yields, so the
     4	route can map to HTTP 4xx/5xx) and HIGH-2 (per-case run lock + run_id
     5	suffixed container_work_dir).
     6	
     7	Docker is mocked end-to-end so these tests run without the cfd-openfoam
     8	container.
     9	"""
    10	from __future__ import annotations
    11	
    12	import sys
    13	import types
    14	from pathlib import Path
    15	from unittest.mock import MagicMock
    16	
    17	import pytest
    18	
    19	
    20	# ────────── shared fakes ──────────
    21	
    22	
    23	class _FakeContainer:
    24	    """Minimal stand-in for the docker ContainerModel."""
    25	
    26	    def __init__(self, *, status: str = "running", exec_lines: list[bytes] | None = None):
    27	        self.status = status
    28	        self._exec_lines = exec_lines or []
    29	
    30	    def exec_run(self, cmd, stream: bool = False, demux: bool = False):  # noqa: D401, ARG002
    31	        if stream:
    32	            result = types.SimpleNamespace(output=iter(self._exec_lines))
    33	            return result
    34	        # Non-streaming exec_run is used for mkdir/ls — return empty.
    35	        return types.SimpleNamespace(output=b"", exit_code=0)
    36	
    37	    def put_archive(self, path, data):  # noqa: ARG002
    38	        return True
    39	
    40	    def get_archive(self, path):  # noqa: ARG002
    41	        return iter([b""]), {}
    42	
    43	
    44	class _FakeClient:
    45	    def __init__(self, container):
    46	        self.containers = types.SimpleNamespace(get=lambda name: container)
    47	
    48	
    49	def _install_fake_docker(monkeypatch, container, *, raise_init: Exception | None = None):
    50	    """Install a fake `docker` module so the streamer's lazy imports
    51	    pick it up. Closes a fast-path: the streamer does
    52	    ``import docker`` and ``import docker.errors`` inside the body.
    53	    """
    54	    fake_docker = types.ModuleType("docker")
    55	    fake_errors = types.ModuleType("docker.errors")
    56	
    57	    class DockerException(Exception):
    58	        pass
    59	
    60	    class NotFound(DockerException):
    61	        pass
    62	
    63	    fake_errors.DockerException = DockerException
    64	    fake_errors.NotFound = NotFound
    65	    fake_docker.errors = fake_errors
    66	
    67	    if raise_init is not None:
    68	        def from_env():
    69	            raise raise_init
    70	        fake_docker.from_env = from_env
    71	    else:
    72	        fake_docker.from_env = lambda: _FakeClient(container)
    73	
    74	    monkeypatch.setitem(sys.modules, "docker", fake_docker)
    75	    monkeypatch.setitem(sys.modules, "docker.errors", fake_errors)
    76	
    77	
    78	def _stage_minimal_case(case_dir: Path) -> None:
    79	    """Make `case_dir` look like a setup-bc'd LDC case so preflight passes."""
    80	    (case_dir / "system").mkdir(parents=True)
    81	    (case_dir / "system" / "controlDict").write_text("// stub", encoding="utf-8")
    82	
    83	
    84	# ────────── HIGH-1: preflight surfaces BEFORE the generator yields ──────────
    85	
    86	
    87	def test_preflight_raises_before_first_yield_when_no_controldict(tmp_path):
    88	    """Without system/controlDict, _prepare_stream_icofoam raises so
    89	    the route can return HTTP 409 before any SSE bytes are sent.
    90	    """
    91	    from ui.backend.services.case_solve.solver_streamer import (
    92	        SolverRunError,
    93	        _prepare_stream_icofoam,
    94	    )
    95	
    96	    case_dir = tmp_path / "case_001"
    97	    case_dir.mkdir()
    98	    # Intentionally NOT staging system/controlDict.
    99	
   100	    with pytest.raises(SolverRunError, match="no system/controlDict"):
   101	        _prepare_stream_icofoam(case_host_dir=case_dir)
   102	
   103	
   104	def test_preflight_raises_before_first_yield_when_container_missing(
   105	    tmp_path, monkeypatch
   106	):
   107	    from ui.backend.services.case_solve.solver_streamer import (
   108	        SolverRunError,
   109	        _prepare_stream_icofoam,
   110	    )
   111	
   112	    case_dir = tmp_path / "case_001"
   113	    case_dir.mkdir()
   114	    _stage_minimal_case(case_dir)
   115	
   116	    fake_docker = types.ModuleType("docker")
   117	    fake_errors = types.ModuleType("docker.errors")
   118	
   119	    class DockerException(Exception):
   120	        pass

exec
/bin/zsh -lc 'pytest -q ui/backend/tests/test_solver_streamer.py' in /Users/Zhuanz/Desktop/cfd-harness-unified
 exited 4 in 107ms:
codex
The code path is clear now: both staging `exec_run` sites are guarded, and the lock-release behavior is handled by the outer `_prepare_stream_icofoam` cleanup path. I’m doing one quick pass over prior report wording so the verdict shape matches local convention, then I’ll return the review result.
exec
/bin/zsh -lc "sed -n '1,120p' reports/codex_tool_reports/dec_v61_075_t2_3_post_commit_round5.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
# DEC-V61-075 P2-T2.3 · Codex post-commit review · Round 5

- **Verdict**: CHANGES_REQUIRED
- **Diff target**: commit `2170590` (T2.3 R4 fix: slug resolver honors injected DB)
- **Date**: 2026-04-27
- **Codex command**: `codex review --commit 2170590 --title "DEC-V61-075 P2-T2.3 post-commit R5 · verify R4 P2 closure (slug resolver injected DB)"`

## Findings

### 1. P2 — `_load_whitelist` not guaranteed to exist on duck-typed `knowledge_db` doubles

When `TaskRunner` is used with a duck-typed `knowledge_db` (the repo already does this in tests/harnesses with `MagicMock`/stubs) and a HYBRID_INIT run arrives with a display-title `TaskSpec.name`, the new `knowledge_db._load_whitelist()` call is not guaranteed to exist or return meaningful data. In that case `_resolve_case_slug_for_policy` silently returns the title unchanged, the reference scan looks for `"Lid-Driven Cavity"` instead of `"lid_driven_cavity"`, and incorrectly adds `hybrid_init_invariant_unverified` even when a matching reference manifest is present.

**Location**: `src/task_runner.py:153-157`

## R6 closure (commit `30b866f`)

* `_resolve_case_slug_for_policy` now builds a candidate-DB list: tries the injected DB first AND ALSO includes a default `KnowledgeDB()` fallback. Each candidate is queried in order; the first one that produces a usable whitelist wins. A bare-MagicMock `knowledge_db` whose `_load_whitelist` returns garbage now falls through to the real file-backed default whitelist for standard slugs.
* Added defensive `isinstance(whitelist, dict)` + per-case `isinstance(case, dict)` checks so a malformed YAML or stub return doesn't crash the resolver.
* No new tests — the existing 25 `test_task_runner.py` tests use `MagicMock` for `knowledge_db` and don't exercise the slug-resolution path (no HYBRID_INIT). The R3/R4 happy-path test using a real `KnowledgeDB(knowledge_dir=custom_root)` stays covered. The fallback path is defensive — a "MagicMock with HYBRID_INIT" test would test a hypothetical configuration the repo doesn't currently produce.

## Final disposition

R6 NOT RUN — judgment call:
- Defensive fallback (always-include default DB) is unlikely to introduce a regression
- T2.3 cumulative arc was 5 rounds with consistently diminishing scope per round (5 → 5 → 1 → 1 → 1 finding count)
- Time budget pressure on T2.4 + DEC closure for the session
- Self-pass-rate retroactive estimate: ~0.20 cumulative across the arc — captured for next retro

DEC-V61-075 P2-T2.3 declared CLOSED at 30b866f. Risk acknowledged: a future hypothetical "duck-typed-DB + HYBRID_INIT" call site might still surface an edge-case Codex would have caught at R6+.

exec
/bin/zsh -lc "rg -n \"\\*\\*Verdict\\*\\*:|## Findings|No findings|APPROVE|RESOLVED\" reports/codex_tool_reports/dec_v61_097_phase_1a_round*.md reports/codex_tool_reports/dec_v61_099_round1.md reports/codex_tool_reports/dec_v61_075_t2_3_post_commit_round*.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
reports/codex_tool_reports/dec_v61_075_t2_3_post_commit_round5.md:3:- **Verdict**: CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_075_t2_3_post_commit_round5.md:8:## Findings
reports/codex_tool_reports/dec_v61_075_t2_3_post_commit_round4.md:3:- **Verdict**: CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_075_t2_3_post_commit_round4.md:8:## Findings
reports/codex_tool_reports/dec_v61_075_t2_3_post_commit_round2.md:3:- **Verdict**: CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_075_t2_3_post_commit_round2.md:8:## Findings
reports/codex_tool_reports/dec_v61_075_t2_3_post_commit_round1.md:3:- **Verdict**: CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_075_t2_3_post_commit_round1.md:8:## Findings
reports/codex_tool_reports/dec_v61_075_t2_3_post_commit_round3.md:3:- **Verdict**: CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_075_t2_3_post_commit_round3.md:8:## Findings
reports/codex_tool_reports/dec_v61_097_phase_1a_round3.md:4:**Verdict**: `Codex-verified: CHANGES_REQUIRED immediate disconnect after the first start SSE still bypasses the new finally and leaks _active_runs`
reports/codex_tool_reports/dec_v61_097_phase_1a_round3.md:11:## Findings
reports/codex_tool_reports/dec_v61_097_phase_1a_round4.md:4:**Verdict**: `Codex-verified: RESOLVED round-3 HIGH closed; no regression found in reviewed slice`
reports/codex_tool_reports/dec_v61_097_phase_1a_round4.md:13:> No findings. `solver_streamer.py:415` now puts the `start` yield inside the outer `try`, and the `finally` block at `:521` now covers `GeneratorExit` on that first yield. `test_solver_streamer.py:255` consumes exactly one `start` event and then `gen.close()`, so it hits the previously missed failure mode; the renamed mid-loop test remains complementary. I found no other `yield` points in `stream_icofoam()` outside the outer `try`.
reports/codex_tool_reports/dec_v61_097_phase_1a_round4.md:15:> Codex-verified: RESOLVED round-3 HIGH closed; no regression found in reviewed slice
reports/codex_tool_reports/dec_v61_097_phase_1a_round4.md:26:| 4 | **RESOLVED** | 0 | this commit |
reports/codex_tool_reports/dec_v61_097_phase_1a_round4.md:43:DEC-V61-097 self-estimated 55% pre-Codex. Actual: needed 4 rounds before APPROVE/RESOLVED. Calibration drift = -55% (4 rounds vs. predicted ≤2). Logging in next retrospective per the methodology.
reports/codex_tool_reports/dec_v61_097_phase_1a_round2.md:4:**Verdict**: `Codex-verified: CHANGES_REQUIRED disconnects still leak the per-case solve lock, and /bc/render hardening still bypasses containment on cache hits`
reports/codex_tool_reports/dec_v61_097_phase_1a_round2.md:11:## Findings
reports/codex_tool_reports/dec_v61_097_phase_1a_round1.md:4:**Verdict**: `Codex-verified: CHANGES_REQUIRED solve-stream preflight/multi-run correctness is unsafe, and /bc/render is missing mesh-render input hardening`
reports/codex_tool_reports/dec_v61_097_phase_1a_round1.md:11:## Findings
reports/codex_tool_reports/dec_v61_099_round1.md:20:- Caught on first LDC dogfood ~1 hour after V61-097 R4 RESOLVED.
reports/codex_tool_reports/dec_v61_099_round1.md:35:Return verdict in standard format: APPROVE / CHANGES_REQUIRED with severity-classified findings (HIGH/MED/LOW). Reference reports/codex_tool_reports/dec_v61_097_phase_1a_round*.md for verdict format.
reports/codex_tool_reports/dec_v61_099_round1.md:50:ui/backend/tests/test_solver_streamer.py:257:    after V61-097 R4 RESOLVED). The V61-097 round-1 HIGH-2 fix introduced
reports/codex_tool_reports/dec_v61_099_round1.md:88:reports/codex_tool_reports/dec_v61_097_phase_1a_round4.md:43:DEC-V61-097 self-estimated 55% pre-Codex. Actual: needed 4 rounds before APPROVE/RESOLVED. Calibration drift = -55% (4 rounds vs. predicted ≤2). Logging in next retrospective per the methodology.
reports/codex_tool_reports/dec_v61_099_round1.md:107:reports/codex_tool_reports/dec_v61_099_round1.md:20:- Caught on first LDC dogfood ~1 hour after V61-097 R4 RESOLVED.
reports/codex_tool_reports/dec_v61_099_round1.md:143:.planning/decisions/2026-04-29_v61_098_m_ai_copilot_collab_kickoff.md:10:  - DEC-V61-097 (M-PANELS Phase-1A LDC end-to-end demo · closed 2026-04-29 commit c49fd11 · Codex 4-round arc RESOLVED · the demo that exposed the collab-first gap motivating this milestone)
reports/codex_tool_reports/dec_v61_099_round1.md:156:.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:4:status: Active (2026-04-29 · post-R3 live-run defect per RETRO-V61-053 addendum methodology · Codex pre-merge mandatory per RETRO-V61-001 "OpenFOAM solver 报错修复" trigger · CFDJerry caught on first LDC dogfood after V61-097 R4 RESOLVED commit `c49fd11`)
reports/codex_tool_reports/dec_v61_099_round1.md:158:.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:9:  - DEC-V61-097 (M-PANELS Phase-1A LDC end-to-end demo · closed 2026-04-29 commit c49fd11 · Codex 4-round arc RESOLVED · this DEC closes a DEFECT INTRODUCED IN ROUND 1 of that arc)
reports/codex_tool_reports/dec_v61_099_round1.md:195:.planning/strategic/m_ai_copilot_kickoff/brief_2026-04-29.md:6:**Predecessor**: DEC-V61-097 (M-PANELS Phase-1A LDC end-to-end demo · closed 2026-04-29 commit `c49fd11` · Codex 4-round arc RESOLVED)
reports/codex_tool_reports/dec_v61_099_round1.md:203:.planning/strategic/m_ai_copilot_kickoff/spec_v2_2026-04-29.md:236:- Predecessor · DEC-V61-097 closure: commit `c49fd11` · 4-round Codex arc RESOLVED
reports/codex_tool_reports/dec_v61_099_round1.md:214:.planning/reviews/kogami/blind_control_v61_087_v1_2026-04-27/review.json:1:{"verdict":"APPROVE_WITH_COMMENTS","summary":"DEC-V61-087 v3 is a substantive, well-reasoned governance evolution that correctly addresses the v1/v2 failure modes identified by Codex and grounds its isolation contract in empirically verified flag behavior. The decision-arc coherence with RETRO-V61-001 (counter rules), Pivot Charter §4.7 (CLASS framework), and DEC-V61-073 (sampling audit/anti-drift) is strong, and the honest residual-risk enumeration in §3.5 plus the Tier-2 escalation triggers in §3.6 make this a falsifiable governance contract rather than a self-congratulatory one. Findings below are P1/P2 — none block ratification, but two should be addressed before W1 implementation begins.","findings":[{"severity":"P1","title":"Q1 canary verification method underspecified for the actual leak vector","problem":"§Open Questions Q1 (in v1 form) was the dominant unknown that v3 claims to have resolved via `--tools \"\"`. But the W0 dry-run described in `empirical_probes_completed` and the `Q1 canary regression test (monthly cron)` referenced in §3.6 and kogami_triggers.md §Tier 1 → Tier 2 are not specified concretely in the DEC itself. Specifically: (a) what canary token(s) are seeded into which input channels (cwd files? memory_paths target? env?), (b) what constitutes a 'leak' for sampling purposes (substring? embedding similarity? metadata-only?), (c) what is the sample-size n for monthly cron and how does it interact with the §3.5(3) `--tools \"\"` semantic-change risk acceptance. Without this specified in the DEC, the load-bearing 'physical capability removal' claim depends on an unspecified test, and Tier-2 escalation triggers can't be evaluated.","position":"§3.6 + Acceptance Criteria Q1 evidence","recommendation":"Add a §3.7 'Q1 canary specification' subsection (or expand AC item Q1) listing: (a) ≥3 distinct canary tokens placed in (i) project CLAUDE.md content, (ii) memory_paths.auto target file, (iii) env var; (b) leak definition = exact-substring match of any canary in subprocess `.result`; (c) n=5 runs per month minimum, all 5 must show 0 hits; (d) re-run mandatory on any `claude` CLI version change. Reference this section from §3.6 and from kogami_triggers.md Tier-2 list."},{"severity":"P1","title":"§4.4 paraphrase-laundering residual risk lacks a closure metric","problem":"§4.4 honestly acknowledges that regex blacklist + structured YAML can be defeated by paraphrase ('prior review identified a blocker'). The mitigation is described as 'sampling audit on accumulated review history can detect systematic paraphrase pattern' and Tier-2 escalation 'can include' ≥3 paraphrase instances. But (a) no concrete sampling cadence is specified (interval? sample size?), (b) the trigger uses 'can include' (advisory) rather than a binding count, (c) no owner is assigned. This is the same anti-pattern §10.5 was created to fix for §10 治理降级 — a falsifiability hole in an advisory rule. Without a concrete sampling rule, the §4.4 'improved, not closed' position drifts toward 'closed by hope'.","position":"§4.4 Honest residual risk paragraph + kogami_triggers.md §Strategic package authoring","recommendation":"Bind paraphrase-laundering audit to the existing §10.5 sampling-audit infrastructure: every Nth Kogami review (e.g., N=10) is sampled by the human reviewer (CFDJerry or external Opus session) for paraphrase patterns in author-supplied `rationale` fields. ≥3 confirmed paraphrase instances within a 30-review window → Tier-2 escalation MANDATORY (not advisory). Record cadence in §4.4 + cross-link from kogami_counter_rules.md §5.5."},{"severity":"P2","title":"Hard Boundary anti-self-approval rule has a recursion gap","problem":"kogami_triggers.md §Hard Boundary lists 7 files (P-1 through P-5 plus this file and kogami_counter_rules.md) that Kogami cannot self-approve. But DEC-V61-087 itself is the governance contract that establishes this boundary. A future DEC modifying DEC-V61-087's §3 (isolation contract) is not explicitly listed in the Hard Boundary file paths — only the implementation artifacts are. A clever framing ('we're not modifying P-1, just amending DEC-V61-087 §3 to relax which flags are required') could route around the rule. The DEC §4.2 'must NOT trigger' list mentions 'Kogami's own P-1/.../P-5 modifications' but not 'modifications to DEC-V61-087 itself or successor DECs that re-architect Kogami'.","position":"§4.2 must-NOT trigger list, last bullet · kogami_triggers.md §Hard Boundary file list","recommendation":"Extend the Hard Boundary to include 'any DEC whose `parent_dec` includes DEC-V61-087 OR whose subject is the Kogami isolation contract / counter rules / trigger rules'. Update both the DEC §4.2 enumeration and kogami_triggers.md §Hard Boundary. This closes the meta-recursion: Kogami v3.1 / v4 cannot self-approve its own governance evolution."},{"severity":"P2","title":"Counter provenance logic conflates Interpretation A and B without a binding tiebreaker","problem":"`autonomous_governance_counter_v61_provenance` says 'Interpretation B (STATE.md = SSOT, established by V61-086 provenance precedent), this DEC advances 52 → 53. Strict-bookkeeping Interpretation A would also yield 53 in this case (no intermediate silent advances since V61-075), so both interpretations agree here.' This is fine for V61-087 specifically but defers the actual choice. If a future DEC has divergent A/B values, there is no binding rule. RETRO-V61-001 says counter is pure telemetry, but provenance disputes are still live (V61-080/081/082/FORENSIC-FLAKE silent advances per STATE.md last_updated). Kogami's counter rules document (§5.6 Q4 dry-run) verifies historical compatibility but doesn't codify which interpretation is canonical going forward.","position":"frontmatter `autonomous_governance_counter_v61_provenance` + kogami_counter_rules.md §5.6","recommendation":"Either (a) add a one-line ratification in §5 of DEC-V61-087: 'Interpretation B (STATE.md last_updated = SSOT) is canonical going forward per V61-086 precedent', OR (b) open a follow-up DEC explicitly choosing. Without canonicalization, any future arc with intermediate silent advances will re-litigate. Low-cost fix; high value for future audit clarity."},{"severity":"P3","title":"Process Note's GSD-bypass justification is sound but creates a precedent worth flagging","problem":"§Process Note explains why this DEC didn't go through `/gsd-discuss-phase` (project's main-line is workbench-closed-loop M1-M4 COMPLETE; no governance phase exists in ROADMAP.md). The reasoning is correct. But this is the second governance-class artifact bypass in a row (DEC-V61-073 sampling audit was similar; ADR-002 W2 G-9 was similar per RETRO-V61-005). A pattern is forming where governance evolution lives outside the GSD phase model. This isn't wrong, but it's worth surfacing as a meta-question for the next arc-size retro.","position":"§Process Note","recommendation":"Add one sentence: 'If governance-class DECs continue to accumulate outside the GSD phase model (DEC-V61-073, ADR-002, this DEC), open a follow-up retro at counter ≥ 60 to evaluate whether ROADMAP.md should add a standing 'governance' phase or whether the current pattern is deliberate.' No action needed for V61-087 itself."}],"strategic_assessment":"Decision-arc coherence: STRONG. v3 directly consumes the v1/v2 Codex failures (prompt-contract not enforceable → process boundary still leaky → physical capability removal via `--tools \"\"`), with each failure mode acknowledged honestly in §Why. The W0 empirical fixes (cwd switch, stdin prompt) show real iteration, not paper-over. Compatibility with RETRO-V61-001 counter rules verified via Q4 dry-run; compatibility with DEC-V61-073 §10.5 sampling audit infrastructure is implicit (kogami_triggers.md Tier-2 list mentions Q5 keyword sampling but doesn't formally bind to §10.5). Roadmap fit: NEUTRAL-TO-POSITIVE. Workbench main-line M1-M4 is COMPLETE per ROADMAP.md, so this governance work doesn't compete with user-facing delivery. The ~1030 LOC estimate (mostly docs) is proportionate; the W0/W1/W2/W3/W4 staging with explicit user-ACK gates between waves is consistent with §10.4 Line-A/B isolation discipline. Retrospective completeness: STRONG. §3.5 enumerates 6 honest residual risks; §3.6 specifies Tier-2 escalation triggers; §Risks table covers 7 distinct failure modes with mitigations. Out-of-scope hygiene: STRONG. §Out of Scope explicitly lists 8 items including the recursion guard (Kogami doesn't review its own reviews) and the counter non-inflation invariant. The Hard Boundary in kogami_triggers.md correctly anticipates anti-self-approval but has a recursion gap (Finding P2 above). Risk-vs-benefit framing: SOUND. Notion-Opus replacement value (faster turnaround, tool access, automatic provenance) is real; the cost (loss of cross-model independence) is honestly acknowledged as 'Codex stays for code-layer; Kogami covers strategic-layer with same-model-but-different-process'. The Tier-1 → Tier-2 escalation path means this is a reversible, falsifiable bet rather than a one-way door.","recommended_next":"merge"}
reports/codex_tool_reports/dec_v61_099_round1.md:419:/bin/zsh -lc 'rg -n "dec_v61_097_phase_1a_round|APPROVE|CHANGES_REQUIRED|HIGH|MED|LOW" reports/codex_tool_reports -S' in /Users/Zhuanz/Desktop/cfd-harness-unified
reports/codex_tool_reports/dec_v61_099_round1.md:421:reports/codex_tool_reports/2026-04-28_m_viz_bundle_steps_3_to_6_codex_review_round4.md:70:If Round-5 returns APPROVE / APPROVE_WITH_COMMENTS with no new
reports/codex_tool_reports/dec_v61_099_round1.md:422:reports/codex_tool_reports/2026-04-28_m_viz_bundle_steps_3_to_6_codex_review_round4.md:85:implementation DEC after Codex APPROVE.
reports/codex_tool_reports/dec_v61_099_round1.md:423:reports/codex_tool_reports/2026-04-21_pr21_bfs_guard_review.md:11:`APPROVED_WITH_NOTES`
reports/codex_tool_reports/dec_v61_099_round1.md:426:reports/codex_tool_reports/2026-04-21_phase7bde_codex_review_round1.md:57:Reply APPROVED / APPROVED_WITH_COMMENTS / CHANGES_REQUIRED with numbered findings. Brief if APPROVED; detailed if CHANGES_REQUIRED.
reports/codex_tool_reports/dec_v61_099_round1.md:435:reports/codex_tool_reports/run_compare_api_r2.md:5:APPROVE_WITH_COMMENTS.
reports/codex_tool_reports/dec_v61_099_round1.md:439:reports/codex_tool_reports/20260422_dec045_wave1_A_convergence_attestor_result.md:1166:5. **Self-pass 0.50 realistic**: with 8 tracks and 4 waves, expect ≥1 Codex CHANGES_REQUIRED round before final APPROVE.
reports/codex_tool_reports/dec_v61_099_round1.md:441:reports/codex_tool_reports/20260422_dec045_wave1_A_convergence_attestor_result.md:1285:**Verdict**: APPROVE / APPROVE_WITH_NOTES / CHANGES_REQUIRED / BLOCK
reports/codex_tool_reports/dec_v61_099_round1.md:442:reports/codex_tool_reports/20260422_dec045_wave1_A_convergence_attestor_result.md:1313:- Ready for codex_verdict=APPROVED: YES / NO
reports/codex_tool_reports/dec_v61_099_round1.md:449:reports/codex_tool_reports/dec_v61_075_t2_3_post_commit_round5.md:3:- **Verdict**: CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_099_round1.md:451:reports/codex_tool_reports/20260422_dec036b_codex_prompt.md:60:**Verdict**: APPROVE / APPROVE_WITH_NOTES / CHANGES_REQUIRED / BLOCK
reports/codex_tool_reports/dec_v61_099_round1.md:452:reports/codex_tool_reports/20260422_dec036b_codex_prompt.md:85:- Ready for codex_verdict=APPROVED: YES / NO
reports/codex_tool_reports/dec_v61_099_round1.md:453:reports/codex_tool_reports/2026-04-21_pr5c_hmac_review.md:9:APPROVED_WITH_NOTES
reports/codex_tool_reports/dec_v61_099_round1.md:462:reports/codex_tool_reports/dec_v61_057_round2.md:105:**Stage C kickoff unblocked** after round 3 APPROVE_WITH_COMMENTS.
reports/codex_tool_reports/dec_v61_099_round1.md:464:reports/codex_tool_reports/2026-04-28_m_viz_bundle_steps_3_to_6_codex_review_round1.md:107:returns APPROVE/APPROVE_WITH_COMMENTS in Round 2 (autonomous_governance
reports/codex_tool_reports/dec_v61_099_round1.md:465:reports/codex_tool_reports/2026-04-21_pr5c1_codex_followup_review.md:10:APPROVED_WITH_NOTES
reports/codex_tool_reports/dec_v61_099_round1.md:466:reports/codex_tool_reports/2026-04-21_pr5c2_m3_review.md:10:APPROVED_WITH_NOTES
reports/codex_tool_reports/dec_v61_099_round1.md:467:reports/codex_tool_reports/2026-04-21_pr5d1_closure_review.md:10:APPROVED_WITH_NOTES
reports/codex_tool_reports/dec_v61_099_round1.md:472:reports/codex_tool_reports/20260422_v62_takeover_notion_sync_draft.md:28:- `codex_verdict`: `pending` → `APPROVED_BACKFILL_FROM_COMMIT_EVIDENCE`
reports/codex_tool_reports/dec_v61_099_round1.md:473:reports/codex_tool_reports/20260422_v62_takeover_notion_sync_draft.md:44:- `codex_verdict`: `pending` → `APPROVED_BACKFILL_FROM_COMMIT_EVIDENCE`
reports/codex_tool_reports/dec_v61_099_round1.md:474:reports/codex_tool_reports/dec_v61_058_round2_review.md:5:**Verdict:** `APPROVE_WITH_COMMENTS`
reports/codex_tool_reports/dec_v61_099_round1.md:475:reports/codex_tool_reports/dec_v61_058_round2_review.md:30:- Q4: round 2 ruling is APPROVE_WITH_COMMENTS (not full APPROVE because of C4 stale narrative).
reports/codex_tool_reports/dec_v61_099_round1.md:476:reports/codex_tool_reports/dec_v61_058_round2_review.md:67:`APPROVE_WITH_COMMENTS`
reports/codex_tool_reports/dec_v61_099_round1.md:478:reports/codex_tool_reports/dec_v61_058_round2_review.md:96:- A clean `APPROVE` is slightly too strong because of the residual stale α-routing narrative above.
reports/codex_tool_reports/dec_v61_099_round1.md:479:reports/codex_tool_reports/dec_v61_058_round2_review.md:97:- `APPROVE_WITH_COMMENTS` is the right ruling. Batch C can proceed.
reports/codex_tool_reports/dec_v61_099_round1.md:480:reports/codex_tool_reports/dec_v61_058_round2_review.md:117:`APPROVE_WITH_COMMENTS`
reports/codex_tool_reports/dec_v61_099_round1.md:482:reports/codex_tool_reports/dec_v61_058_round2_review.md:146:- A clean `APPROVE` is slightly too strong because of the residual stale α-routing narrative above.
reports/codex_tool_reports/dec_v61_099_round1.md:483:reports/codex_tool_reports/dec_v61_058_round2_review.md:147:- `APPROVE_WITH_COMMENTS` is the right ruling. Batch C can proceed.
reports/codex_tool_reports/dec_v61_099_round1.md:484:reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:28:Reply with structured verdict: APPROVED / APPROVED_WITH_COMMENTS / CHANGES_REQUIRED, then numbered findings with severity (HIGH/MED/LOW) and file:line anchors.
reports/codex_tool_reports/dec_v61_099_round1.md:500:reports/codex_tool_reports/bug1_sse_disconnect_persistence_r3.md:4:`APPROVE_WITH_COMMENTS`
reports/codex_tool_reports/dec_v61_099_round1.md:502:reports/codex_tool_reports/2026-04-28_m_panels_arc_codex_review_round4.md:10:`APPROVE` — 0 P1, 0 P2, 0 WARNING.
reports/codex_tool_reports/dec_v61_099_round1.md:503:reports/codex_tool_reports/2026-04-28_m_panels_arc_codex_review_round4.md:34:Cumulative arc: `08b0d16..5b21df5` — 4 Codex rounds total, ending APPROVE on the smoke-prep extension that surfaced after Round 2's APPROVE on the original Tier-A arc.
reports/codex_tool_reports/dec_v61_099_round1.md:504:reports/codex_tool_reports/2026-04-28_m_panels_arc_codex_review_round4.md:36:Codex-verified: APPROVE
reports/codex_tool_reports/dec_v61_099_round1.md:509:reports/codex_tool_reports/dec_v61_087_kogami_bootstrap_r1.md:39:### P1 (major, 必须修订才能 APPROVE)
reports/codex_tool_reports/dec_v61_099_round1.md:513:reports/codex_tool_reports/20260422_dec045_wave1_B_comparator_gates_result.md:345:5. **Self-pass 0.50 realistic**: with 8 tracks and 4 waves, expect ≥1 Codex CHANGES_REQUIRED round before final APPROVE.
reports/codex_tool_reports/dec_v61_099_round1.md:516:reports/codex_tool_reports/20260422_dec045_wave1_B_comparator_gates_result.md:462:**Verdict**: APPROVE / APPROVE_WITH_NOTES / CHANGES_REQUIRED / BLOCK
reports/codex_tool_reports/dec_v61_099_round1.md:517:reports/codex_tool_reports/20260422_dec045_wave1_B_comparator_gates_result.md:487:- Ready for codex_verdict=APPROVED: YES / NO
reports/codex_tool_reports/dec_v61_099_round1.md:529:reports/codex_tool_reports/20260422_dec038_codex_prompt.md:78:**Verdict**: APPROVE / APPROVE_WITH_NOTES / CHANGES_REQUIRED / BLOCK
reports/codex_tool_reports/dec_v61_099_round1.md:530:reports/codex_tool_reports/20260422_dec038_codex_prompt.md:106:- Ready for codex_verdict=APPROVED: YES / NO
reports/codex_tool_reports/dec_v61_099_round1.md:531:reports/codex_tool_reports/20260422_dec036_036c_039_backfill_note.md:50:- `codex_verdict`: `pending` → `APPROVED_BACKFILL_FROM_COMMIT_EVIDENCE`
reports/codex_tool_reports/dec_v61_099_round1.md:532:reports/codex_tool_reports/20260422_dec036_036c_039_backfill_note.md:57:- `codex_verdict`: `pending` → `APPROVED_BACKFILL_FROM_COMMIT_EVIDENCE`
reports/codex_tool_reports/dec_v61_099_round1.md:533:reports/codex_tool_reports/dec_v61_097_phase_1a_round2.md:4:**Verdict**: `Codex-verified: CHANGES_REQUIRED disconnects still leak the per-case solve lock, and /bc/render hardening still bypasses containment on cache hits`
reports/codex_tool_reports/dec_v61_099_round1.md:538:reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round2.md:55:Reply APPROVED / APPROVED_WITH_COMMENTS / CHANGES_REQUIRED. Brief if APPROVED.
reports/codex_tool_reports/dec_v61_099_round1.md:552:reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round2.md:1925:APPROVED_WITH_COMMENTS
reports/codex_tool_reports/dec_v61_099_round1.md:553:reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round2.md:1936:APPROVED_WITH_COMMENTS
reports/codex_tool_reports/dec_v61_099_round1.md:561:reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round4.md:29:Please verify the round-3 MED is now closed. Reply APPROVED / APPROVED_WITH_COMMENTS / CHANGES_REQUIRED.
reports/codex_tool_reports/dec_v61_099_round1.md:569:reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round4.md:721:APPROVED
reports/codex_tool_reports/dec_v61_099_round1.md:570:reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round4.md:723:No findings. The round-3 MED is closed: POST now maps `OSError` to the same `503` response path as GET in [ui/backend/routes/comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/routes/comparison_report.py:96), and the new regressions in [ui/backend/tests/test_comparison_report_route.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparison_report_route.py:184) cover both synthetic `OSError` cases.
reports/codex_tool_reports/dec_v61_099_round1.md:571:reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round4.md:733:APPROVED
reports/codex_tool_reports/dec_v61_099_round1.md:572:reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round4.md:735:No findings. The round-3 MED is closed: POST now maps `OSError` to the same `503` response path as GET in [ui/backend/routes/comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/routes/comparison_report.py:96), and the new regressions in [ui/backend/tests/test_comparison_report_route.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparison_report_route.py:184) cover both synthetic `OSError` cases.
reports/codex_tool_reports/dec_v61_099_round1.md:575:reports/codex_tool_reports/dec_v61_087_v2_kogami_bootstrap_r1.md:50:   The hard boundary now explicitly bans Kogami self-approval of its own agent prompt, brief script, invoke wrapper, trigger rules, and counter rules, and requires both user ratification and Codex APPROVE (`.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:459-463`). This is strict enough for the original v1 finding.
reports/codex_tool_reports/dec_v61_099_round1.md:576:reports/codex_tool_reports/dec_v61_075_t2_3_post_commit_round3.md:3:- **Verdict**: CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_099_round1.md:579:reports/codex_tool_reports/dec_v61_087_v3_kogami_bootstrap_r2.md:14:`APPROVE_WITH_COMMENTS`
reports/codex_tool_reports/dec_v61_099_round1.md:580:reports/codex_tool_reports/dec_v61_087_v3_kogami_bootstrap_r2.md:74:`APPROVE_WITH_COMMENTS`。给绿灯进入 W0 implementation。
reports/codex_tool_reports/dec_v61_099_round1.md:581:reports/codex_tool_reports/2026-04-28_m_viz_bundle_steps_3_to_6_codex_review_round5.md:65:P2 → P3) as the bundle stabilizes. Round 6 expectation: APPROVE or
reports/codex_tool_reports/dec_v61_099_round1.md:582:reports/codex_tool_reports/dec_v61_075_t2_3_post_commit_round1.md:3:- **Verdict**: CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_099_round1.md:583:reports/codex_tool_reports/20260422_dec038_codex_review.md:92:**Verdict**: APPROVE / APPROVE_WITH_NOTES / CHANGES_REQUIRED / BLOCK
reports/codex_tool_reports/dec_v61_099_round1.md:584:reports/codex_tool_reports/20260422_dec038_codex_review.md:120:- Ready for codex_verdict=APPROVED: YES / NO
reports/codex_tool_reports/dec_v61_099_round1.md:585:reports/codex_tool_reports/20260422_dec038_codex_review.md:388:Opus Gate: ⚠️ APPROVED WITH CONDITIONS (2026-04-13) — CFDJerry (T0 proxy)
reports/codex_tool_reports/dec_v61_099_round1.md:586:reports/codex_tool_reports/20260422_dec038_codex_review.md:476:Opus Gate: ✅ APPROVED (2026-04-13) — 5/5 criteria, 10/10 tasks, 103 tests
reports/codex_tool_reports/dec_v61_099_round1.md:587:reports/codex_tool_reports/20260422_dec038_codex_review.md:508:Opus Gate: ✅ APPROVED (2026-04-13)
reports/codex_tool_reports/dec_v61_099_round1.md:592:reports/codex_tool_reports/20260422_dec038_codex_review.md:854:- Status: COMPLETE (DEC-V61-031, 2026-04-21). 3 waves landed: adapter functions{} + executor capture + driver manifest; backend route/service/18 pytest; Codex 3 rounds → APPROVED_WITH_COMMENTS (2 HIGH security issues caught + fixed: URL basename collision + run_id path-traversal). Real LDC OpenFOAM integration produced 8 artifacts, HTTP manifest + subpath download + traversal 404 verified live. 97/97 pytest. v6.1 counter 16→17.
reports/codex_tool_reports/dec_v61_099_round1.md:593:reports/codex_tool_reports/20260422_dec038_codex_review.md:879:- Status: **SPRINT 1 + SPRINT 2 TIER C COMPLETE** — DEC-V61-032 (LDC MVP) + DEC-V61-034 (Tier C visual-only fan-out to 9 cases, 2026-04-21). 8-section Jinja2 HTML template + WeasyPrint PDF + reduced visual-only context for non-LDC cases. Codex 4 + 2 rounds (both APPROVED). Tier B Sprint 2 (per-case gold-overlay for 9 cases) remains future work.
reports/codex_tool_reports/dec_v61_099_round1.md:609:reports/codex_tool_reports/20260422_dec038_codex_review.md:3911:.planning/STATE.md:1272:- DEC-038 attestor round 2: APPROVED_WITH_COMMENTS on `eb51dcf` (fixes + A2/G5 split-brain + ATTEST_NOT_APPLICABLE)
reports/codex_tool_reports/dec_v61_099_round1.md:612:reports/codex_tool_reports/20260422_dec038_codex_review.md:5985:- **Ready for codex_verdict=APPROVED**: NO
reports/codex_tool_reports/dec_v61_099_round1.md:613:reports/codex_tool_reports/20260422_dec038_codex_review.md:6038:- **Ready for codex_verdict=APPROVED**: NO
reports/codex_tool_reports/dec_v61_099_round1.md:614:reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round2.md:3:- **Verdict**: CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_099_round1.md:615:reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round2.md:32:R3 introduced 2 new findings (P2 TaskRunner notes drop, P3 unsafe `hasattr`); R4 introduced 2 new (legacy path symmetry, Notion summary persistence); R5 APPROVE. Rolled into commit b2ea911.
reports/codex_tool_reports/dec_v61_099_round1.md:617:reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:42:Please verify the round-2 HIGH is now closed and return APPROVED / APPROVED_WITH_COMMENTS / CHANGES_REQUIRED.
reports/codex_tool_reports/dec_v61_099_round1.md:667:reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1617:/bin/zsh -lc 'rg -n "''^(## |# |-|Findings|HIGH|MEDIUM|LOW|CHANGES_REQUIRED|APPROVED|Round|round|#1|#3|#4)" reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md | tail -n 120' in /Users/Zhuanz/Desktop/cfd-harness-unified
reports/codex_tool_reports/dec_v61_099_round1.md:684:reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:2583:APPROVED_WITH_COMMENTS
reports/codex_tool_reports/dec_v61_099_round1.md:686:reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:2599:APPROVED_WITH_COMMENTS
reports/codex_tool_reports/dec_v61_099_round1.md:692:reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:1752:**Verdict**: APPROVE / APPROVE_WITH_NOTES / CHANGES_REQUIRED / BLOCK
reports/codex_tool_reports/dec_v61_099_round1.md:693:reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:1780:- Ready for codex_verdict=APPROVED: YES / NO
reports/codex_tool_reports/dec_v61_099_round1.md:711:reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:10115:3911-.planning/STATE.md:1272:- DEC-038 attestor round 2: APPROVED_WITH_COMMENTS on `eb51dcf` (fixes + A2/G5 split-brain + ATTEST_NOT_APPLICABLE)
reports/codex_tool_reports/dec_v61_099_round1.md:712:reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:10343:5985-- **Ready for codex_verdict=APPROVED**: NO
reports/codex_tool_reports/dec_v61_099_round1.md:713:reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:10390:6038-- **Ready for codex_verdict=APPROVED**: NO
reports/codex_tool_reports/dec_v61_099_round1.md:740:reports/codex_tool_reports/dec_v61_074_t1b1_round1.md:3:- **Verdict**: CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_099_round1.md:742:reports/codex_tool_reports/dec_v61_075_t2_3_post_commit_round4.md:3:- **Verdict**: CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_099_round1.md:743:reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round3.md:3:- **Verdict**: CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_099_round1.md:744:reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round3.md:30:R4 introduced 2 new findings (legacy-path symmetry + Notion summary persistence); R5 APPROVE. Rolled into commit b2ea911.
reports/codex_tool_reports/dec_v61_099_round1.md:764:reports/codex_tool_reports/dec_v61_099_round1.md:35:Return verdict in standard format: APPROVE / CHANGES_REQUIRED with severity-classified findings (HIGH/MED/LOW). Reference reports/codex_tool_reports/dec_v61_097_phase_1a_round*.md for verdict format.
reports/codex_tool_reports/dec_v61_099_round1.md:765:reports/codex_tool_reports/dec_v61_099_round1.md:50:ui/backend/tests/test_solver_streamer.py:257:    after V61-097 R4 RESOLVED). The V61-097 round-1 HIGH-2 fix introduced
reports/codex_tool_reports/dec_v61_099_round1.md:774:reports/codex_tool_reports/dec_v61_099_round1.md:88:reports/codex_tool_reports/dec_v61_097_phase_1a_round4.md:43:DEC-V61-097 self-estimated 55% pre-Codex. Actual: needed 4 rounds before APPROVE/RESOLVED. Calibration drift = -55% (4 rounds vs. predicted ≤2). Logging in next retrospective per the methodology.
reports/codex_tool_reports/dec_v61_099_round1.md:782:reports/codex_tool_reports/dec_v61_099_round1.md:214:.planning/reviews/kogami/blind_control_v61_087_v1_2026-04-27/review.json:1:{"verdict":"APPROVE_WITH_COMMENTS","summary":"DEC-V61-087 v3 is a substantive, well-reasoned governance evolution that correctly addresses the v1/v2 failure modes identified by Codex and grounds its isolation contract in empirically verified flag behavior. The decision-arc coherence with RETRO-V61-001 (counter rules), Pivot Charter §4.7 (CLASS framework), and DEC-V61-073 (sampling audit/anti-drift) is strong, and the honest residual-risk enumeration in §3.5 plus the Tier-2 escalation triggers in §3.6 make this a falsifiable governance contract rather than a self-congratulatory one. Findings below are P1/P2 — none block ratification, but two should be addressed before W1 implementation begins.","findings":[{"severity":"P1","title":"Q1 canary verification method underspecified for the actual leak vector","problem":"§Open Questions Q1 (in v1 form) was the dominant unknown that v3 claims to have resolved via `--tools \"\"`. But the W0 dry-run described in `empirical_probes_completed` and the `Q1 canary regression test (monthly cron)` referenced in §3.6 and kogami_triggers.md §Tier 1 → Tier 2 are not specified concretely in the DEC itself. Specifically: (a) what canary token(s) are seeded into which input channels (cwd files? memory_paths target? env?), (b) what constitutes a 'leak' for sampling purposes (substring? embedding similarity? metadata-only?), (c) what is the sample-size n for monthly cron and how does it interact with the §3.5(3) `--tools \"\"` semantic-change risk acceptance. Without this specified in the DEC, the load-bearing 'physical capability removal' claim depends on an unspecified test, and Tier-2 escalation triggers can't be evaluated.","position":"§3.6 + Acceptance Criteria Q1 evidence","recommendation":"Add a §3.7 'Q1 canary specification' subsection (or expand AC item Q1) listing: (a) ≥3 distinct canary tokens placed in (i) project CLAUDE.md content, (ii) memory_paths.auto target file, (iii) env var; (b) leak definition = exact-substring match of any canary in subprocess `.result`; (c) n=5 runs per month minimum, all 5 must show 0 hits; (d) re-run mandatory on any `claude` CLI version change. Reference this section from §3.6 and from kogami_triggers.md Tier-2 list."},{"severity":"P1","title":"§4.4 paraphrase-laundering residual risk lacks a closure metric","problem":"§4.4 honestly acknowledges that regex blacklist + structured YAML can be defeated by paraphrase ('prior review identified a blocker'). The mitigation is described as 'sampling audit on accumulated review history can detect systematic paraphrase pattern' and Tier-2 escalation 'can include' ≥3 paraphrase instances. But (a) no concrete sampling cadence is specified (interval? sample size?), (b) the trigger uses 'can include' (advisory) rather than a binding count, (c) no owner is assigned. This is the same anti-pattern §10.5 was created to fix for §10 治理降级 — a falsifiability hole in an advisory rule. Without a concrete sampling rule, the §4.4 'improved, not closed' position drifts toward 'closed by hope'.","position":"§4.4 Honest residual risk paragraph + kogami_triggers.md §Strategic package authoring","recommendation":"Bind paraphrase-laundering audit to the existing §10.5 sampling-audit infrastructure: every Nth Kogami review (e.g., N=10) is sampled by the human reviewer (CFDJerry or external Opus session) for paraphrase patterns in author-supplied `rationale` fields. ≥3 confirmed paraphrase instances within a 30-review window → Tier-2 escalation MANDATORY (not advisory). Record cadence in §4.4 + cross-link from kogami_counter_rules.md §5.5."},{"severity":"P2","title":"Hard Boundary anti-self-approval rule has a recursion gap","problem":"kogami_triggers.md §Hard Boundary lists 7 files (P-1 through P-5 plus this file and kogami_counter_rules.md) that Kogami cannot self-approve. But DEC-V61-087 itself is the governance contract that establishes this boundary. A future DEC modifying DEC-V61-087's §3 (isolation contract) is not explicitly listed in the Hard Boundary file paths — only the implementation artifacts are. A clever framing ('we're not modifying P-1, just amending DEC-V61-087 §3 to relax which flags are required') could route around the rule. The DEC §4.2 'must NOT trigger' list mentions 'Kogami's own P-1/.../P-5 modifications' but not 'modifications to DEC-V61-087 itself or successor DECs that re-architect Kogami'.","position":"§4.2 must-NOT trigger list, last bullet · kogami_triggers.md §Hard Boundary file list","recommendation":"Extend the Hard Boundary to include 'any DEC whose `parent_dec` includes DEC-V61-087 OR whose subject is the Kogami isolation contract / counter rules / trigger rules'. Update both the DEC §4.2 enumeration and kogami_triggers.md §Hard Boundary. This closes the meta-recursion: Kogami v3.1 / v4 cannot self-approve its own governance evolution."},{"severity":"P2","title":"Counter provenance logic conflates Interpretation A and B without a binding tiebreaker","problem":"`autonomous_governance_counter_v61_provenance` says 'Interpretation B (STATE.md = SSOT, established by V61-086 provenance precedent), this DEC advances 52 → 53. Strict-bookkeeping Interpretation A would also yield 53 in this case (no intermediate silent advances since V61-075), so both interpretations agree here.' This is fine for V61-087 specifically but defers the actual choice. If a future DEC has divergent A/B values, there is no binding rule. RETRO-V61-001 says counter is pure telemetry, but provenance disputes are still live (V61-080/081/082/FORENSIC-FLAKE silent advances per STATE.md last_updated). Kogami's counter rules document (§5.6 Q4 dry-run) verifies historical compatibility but doesn't codify which interpretation is canonical going forward.","position":"frontmatter `autonomous_governance_counter_v61_provenance` + kogami_counter_rules.md §5.6","recommendation":"Either (a) add a one-line ratification in §5 of DEC-V61-087: 'Interpretation B (STATE.md last_updated = SSOT) is canonical going forward per V61-086 precedent', OR (b) open a follow-up DEC explicitly choosing. Without canonicalization, any future arc with intermediate silent advances will re-litigate. Low-cost fix; high value for future audit clarity."},{"severity":"P3","title":"Process Note's GSD-bypass justification is sound but creates a precedent worth flagging","problem":"§Process Note explains why this DEC didn't go through `/gsd-discuss-phase` (project's main-line is workbench-closed-loop M1-M4 COMPLETE; no governance phase exists in ROADMAP.md). The reasoning is correct. But this is the second governance-class artifact bypass in a row (DEC-V61-073 sampling audit was similar; ADR-002 W2 G-9 was similar per RETRO-V61-005). A pattern is forming where governance evolution lives outside the GSD phase model. This isn't wrong, but it's worth surfacing as a meta-question for the next arc-size retro.","position":"§Process Note","recommendation":"Add one sentence: 'If governance-class DECs continue to accumulate outside the GSD phase model (DEC-V61-073, ADR-002, this DEC), open a follow-up retro at counter ≥ 60 to evaluate whether ROADMAP.md should add a standing 'governance' phase or whether the current pattern is deliberate.' No action needed for V61-087 itself."}],"strategic_assessment":"Decision-arc coherence: STRONG. v3 directly consumes the v1/v2 Codex failures (prompt-contract not enforceable → process boundary still leaky → physical capability removal via `--tools \"\"`), with each failure mode acknowledged honestly in §Why. The W0 empirical fixes (cwd switch, stdin prompt) show real iteration, not paper-over. Compatibility with RETRO-V61-001 counter rules verified via Q4 dry-run; compatibility with DEC-V61-073 §10.5 sampling audit infrastructure is implicit (kogami_triggers.md Tier-2 list mentions Q5 keyword sampling but doesn't formally bind to §10.5). Roadmap fit: NEUTRAL-TO-POSITIVE. Workbench main-line M1-M4 is COMPLETE per ROADMAP.md, so this governance work doesn't compete with user-facing delivery. The ~1030 LOC estimate (mostly docs) is proportionate; the W0/W1/W2/W3/W4 staging with explicit user-ACK gates between waves is consistent with §10.4 Line-A/B isolation discipline. Retrospective completeness: STRONG. §3.5 enumerates 6 honest residual risks; §3.6 specifies Tier-2 escalation triggers; §Risks table covers 7 distinct failure modes with mitigations. Out-of-scope hygiene: STRONG. §Out of Scope explicitly lists 8 items including the recursion guard (Kogami doesn't review its own reviews) and the counter non-inflation invariant. The Hard Boundary in kogami_triggers.md correctly anticipates anti-self-approval but has a recursion gap (Finding P2 above). Risk-vs-benefit framing: SOUND. Notion-Opus replacement value (faster turnaround, tool access, automatic provenance) is real; the cost (loss of cross-model independence) is honestly acknowledged as 'Codex stays for code-layer; Kogami covers strategic-layer with same-model-but-different-process'. The Tier-1 → Tier-2 escalation path means this is a reversible, falsifiable bet rather than a one-way door.","recommended_next":"merge"}
reports/codex_tool_reports/dec_v61_099_round1.md:786:reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md:1080:5. **Self-pass 0.50 realistic**: with 8 tracks and 4 waves, expect ≥1 Codex CHANGES_REQUIRED round before final APPROVE.
reports/codex_tool_reports/dec_v61_099_round1.md:816:reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:18:Round 1 verdict was CHANGES_REQUIRED with 4 findings (2 HIGH, 1 MED, 1 LOW). All 4 have been addressed in the uncommitted working tree. Please re-review and confirm APPROVED / APPROVED_WITH_COMMENTS / CHANGES_REQUIRED.
reports/codex_tool_reports/dec_v61_099_round1.md:821:reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:804:Opus Gate: ⚠️ APPROVED WITH CONDITIONS (2026-04-13) — CFDJerry (T0 proxy)
reports/codex_tool_reports/dec_v61_099_round1.md:822:reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:892:Opus Gate: ✅ APPROVED (2026-04-13) — 5/5 criteria, 10/10 tasks, 103 tests
reports/codex_tool_reports/dec_v61_099_round1.md:823:reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:924:Opus Gate: ✅ APPROVED (2026-04-13)
reports/codex_tool_reports/dec_v61_099_round1.md:871:reports/codex_tool_reports/2026-04-28_m_viz_bundle_steps_3_to_6_codex_review_round3.md:99:implementation DEC after Codex APPROVE.
reports/codex_tool_reports/dec_v61_099_round1.md:872:reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round4.md:3:- **Verdict**: CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_099_round1.md:873:reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round4.md:30:R5 APPROVE. Bundle landed at commit b2ea911.
reports/codex_tool_reports/dec_v61_099_round1.md:875:reports/codex_tool_reports/dec_v61_058_round1_review.md:45:1. **Verdict**: APPROVE / APPROVE_WITH_COMMENTS / CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_099_round1.md:877:reports/codex_tool_reports/dec_v61_074_t1b23_postcommit_round2.md:3:- **Verdict**: APPROVE_WITH_COMMENTS · 0 blocking findings (R1's 3 defects all closed)
reports/codex_tool_reports/dec_v61_099_round1.md:879:reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round1.md:84:Reply APPROVED / APPROVED_WITH_COMMENTS / CHANGES_REQUIRED with numbered findings. If APPROVED brief. If CHANGES_REQUIRED detailed with file:line refs.
reports/codex_tool_reports/dec_v61_099_round1.md:902:reports/codex_tool_reports/2026-04-21_phase7bc_render_report_codex_review.md:49:Reply APPROVED / APPROVED_WITH_COMMENTS / CHANGES_REQUIRED with numbered findings + severity.
reports/codex_tool_reports/dec_v61_099_round1.md:903:reports/codex_tool_reports/2026-04-21_phase7bc_render_report_codex_review.md:224:Opus Gate: ⚠️ APPROVED WITH CONDITIONS (2026-04-13) — CFDJerry (T0 proxy)
reports/codex_tool_reports/dec_v61_099_round1.md:904:reports/codex_tool_reports/2026-04-21_phase7bc_render_report_codex_review.md:312:Opus Gate: ✅ APPROVED (2026-04-13) — 5/5 criteria, 10/10 tasks, 103 tests
reports/codex_tool_reports/dec_v61_099_round1.md:905:reports/codex_tool_reports/2026-04-21_phase7bc_render_report_codex_review.md:344:Opus Gate: ✅ APPROVED (2026-04-13)
reports/codex_tool_reports/dec_v61_099_round1.md:906:reports/codex_tool_reports/2026-04-21_phase7bc_render_report_codex_review.md:451:- Status: COMPLETE (DEC-V61-031, 2026-04-21). 3 waves landed: adapter functions{} + executor capture + driver manifest; backend route/service/18 pytest; Codex 3 rounds → APPROVED_WITH_COMMENTS (2 HIGH security issues caught + fixed: URL basename collision + run_id path-traversal). Real LDC OpenFOAM integration produced 8 artifacts, HTTP manifest + subpath download + traversal 404 verified live. 97/97 pytest. v6.1 counter 16→17.
reports/codex_tool_reports/dec_v61_099_round1.md:919:reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:411:- Status: COMPLETE (DEC-V61-031, 2026-04-21). 3 waves landed: adapter functions{} + executor capture + driver manifest; backend route/service/18 pytest; Codex 3 rounds → APPROVED_WITH_COMMENTS (2 HIGH security issues caught + fixed: URL basename collision + run_id path-traversal). Real LDC OpenFOAM integration produced 8 artifacts, HTTP manifest + subpath download + traversal 404 verified live. 97/97 pytest. v6.1 counter 16→17.
reports/codex_tool_reports/dec_v61_099_round1.md:920:reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:436:- Status: **SPRINT 1 + SPRINT 2 TIER C COMPLETE** — DEC-V61-032 (LDC MVP) + DEC-V61-034 (Tier C visual-only fan-out to 9 cases, 2026-04-21). 8-section Jinja2 HTML template + WeasyPrint PDF + reduced visual-only context for non-LDC cases. Codex 4 + 2 rounds (both APPROVED). Tier B Sprint 2 (per-case gold-overlay for 9 cases) remains future work.
reports/codex_tool_reports/dec_v61_099_round1.md:922:reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:540:Opus Gate: ⚠️ APPROVED WITH CONDITIONS (2026-04-13) — CFDJerry (T0 proxy)
reports/codex_tool_reports/dec_v61_099_round1.md:923:reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:628:Opus Gate: ✅ APPROVED (2026-04-13) — 5/5 criteria, 10/10 tasks, 103 tests
reports/codex_tool_reports/dec_v61_099_round1.md:924:reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:660:Opus Gate: ✅ APPROVED (2026-04-13)
reports/codex_tool_reports/dec_v61_099_round1.md:927:reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:1010:5. **Self-pass 0.50 realistic**: with 8 tracks and 4 waves, expect ≥1 Codex CHANGES_REQUIRED round before final APPROVE.
reports/codex_tool_reports/dec_v61_099_round1.md:943:reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:4532:**Verdict**: APPROVE / APPROVE_WITH_NOTES / CHANGES_REQUIRED / BLOCK
reports/codex_tool_reports/dec_v61_099_round1.md:944:reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:4557:- Ready for codex_verdict=APPROVED: YES / NO
reports/codex_tool_reports/dec_v61_099_round1.md:999:reports/codex_tool_reports/2026-04-21_phase7bde_codex_review_round2.md:53:Reply APPROVED / APPROVED_WITH_COMMENTS / CHANGES_REQUIRED. Brief if APPROVED.
reports/codex_tool_reports/dec_v61_099_round1.md:1003:reports/codex_tool_reports/2026-04-21_phase7bde_codex_review_round2.md:2798:APPROVED_WITH_COMMENTS
reports/codex_tool_reports/dec_v61_099_round1.md:1004:reports/codex_tool_reports/2026-04-21_phase7bde_codex_review_round2.md:2810:APPROVED_WITH_COMMENTS
reports/codex_tool_reports/dec_v61_099_round1.md:1006:reports/codex_tool_reports/20260422_dec036b_codex_review.md:74:**Verdict**: APPROVE / APPROVE_WITH_NOTES / CHANGES_REQUIRED / BLOCK
reports/codex_tool_reports/dec_v61_099_round1.md:1007:reports/codex_tool_reports/20260422_dec036b_codex_review.md:99:- Ready for codex_verdict=APPROVED: YES / NO
reports/codex_tool_reports/dec_v61_099_round1.md:1063:reports/codex_tool_reports/20260422_dec036b_codex_review.md:5224:**Verdict**: CHANGES_REQUIRED  
reports/codex_tool_reports/dec_v61_099_round1.md:1064:reports/codex_tool_reports/20260422_dec036b_codex_review.md:5256:- Ready for `codex_verdict=APPROVED`: NO
reports/codex_tool_reports/dec_v61_099_round1.md:1065:reports/codex_tool_reports/20260422_dec036b_codex_review.md:5270:**Verdict**: CHANGES_REQUIRED  
reports/codex_tool_reports/dec_v61_099_round1.md:1066:reports/codex_tool_reports/20260422_dec036b_codex_review.md:5302:- Ready for `codex_verdict=APPROVED`: NO
reports/codex_tool_reports/dec_v61_099_round1.md:1067:reports/codex_tool_reports/2026-04-21_pr23_build_fingerprint_review.md:10:`APPROVED_WITH_NOTES`
reports/codex_tool_reports/dec_v61_099_round1.md:1078:reports/codex_tool_reports/2026-04-28_m_panels_arc_codex_review_round2.md:13:`APPROVE` — 0 P1, 0 P2, 0 P3.
reports/codex_tool_reports/dec_v61_099_round1.md:1079:reports/codex_tool_reports/2026-04-28_m_panels_arc_codex_review_round2.md:33:Codex-verified: APPROVE
reports/codex_tool_reports/dec_v61_099_round1.md:1089:reports/codex_tool_reports/dec_v61_057_plan_review.md:128:All 6 required edits applied. v2 intake committed; Codex re-review pending to confirm APPROVE_PLAN_WITH_CHANGES (or APPROVE_PLAN). Stage A on hold until re-review verdict.
reports/codex_tool_reports/dec_v61_099_round1.md:1090:reports/codex_tool_reports/dec_v61_057_round4.md:11:**APPROVE_WITH_COMMENTS** · 1 MED + 1 LOW · NO Stage E blocker
reports/codex_tool_reports/dec_v61_099_round1.md:1099:reports/codex_tool_reports/dec_v61_074_t1b1_round2.md:3:- **Verdict**: APPROVE_WITH_COMMENTS (R1 HIGH closed)
reports/codex_tool_reports/dec_v61_099_round1.md:1104:reports/codex_tool_reports/2026-04-28_m_viz_bundle_steps_3_to_6_codex_review_round2.md:76:If Round-3 returns APPROVE / APPROVE_WITH_COMMENTS with no new
reports/codex_tool_reports/dec_v61_099_round1.md:1105:reports/codex_tool_reports/2026-04-21_pr20_foam_adapter_review.md:10:APPROVED_WITH_NOTES
reports/codex_tool_reports/dec_v61_099_round1.md:1106:reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round1.md:3:- **Verdict**: CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_099_round1.md:1107:reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round1.md:26:R2 introduced 2 new findings (P2/P3 below); R3, R4 each introduced more cross-system findings; R5 returned APPROVE. Rolled into commit b2ea911.
reports/codex_tool_reports/dec_v61_099_round1.md:1116:reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:31:Reply APPROVED / APPROVED_WITH_COMMENTS / CHANGES_REQUIRED.
reports/codex_tool_reports/dec_v61_099_round1.md:1149:reports/codex_tool_reports/dec_v61_097_phase_1a_round4.md:4:**Verdict**: `Codex-verified: RESOLVED round-3 HIGH closed; no regression found in reviewed slice`
reports/codex_tool_reports/dec_v61_099_round1.md:1150:reports/codex_tool_reports/dec_v61_097_phase_1a_round4.md:15:> Codex-verified: RESOLVED round-3 HIGH closed; no regression found in reviewed slice
reports/codex_tool_reports/dec_v61_099_round1.md:1154:reports/codex_tool_reports/dec_v61_097_phase_1a_round4.md:43:DEC-V61-097 self-estimated 55% pre-Codex. Actual: needed 4 rounds before APPROVE/RESOLVED. Calibration drift = -55% (4 rounds vs. predicted ≤2). Logging in next retrospective per the methodology.
reports/codex_tool_reports/dec_v61_099_round1.md:1155:reports/codex_tool_reports/dec_v61_071_round2.md:7:- Verdict: `APPROVE_WITH_COMMENTS`
reports/codex_tool_reports/dec_v61_099_round1.md:1156:reports/codex_tool_reports/dec_v61_052_bfs_round1_findings.md:1:VERDICT: APPROVE | APPROVE_WITH_COMMENTS | CHANGES_REQUIRED | RETRACT
reports/codex_tool_reports/dec_v61_099_round1.md:1171:reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round5.md:3:- **Verdict**: APPROVE
reports/codex_tool_reports/dec_v61_099_round1.md:1176:reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round5.md:31:| R5 | APPROVE | 0 | — |
reports/codex_tool_reports/dec_v61_099_round1.md:1201:reports/codex_tool_reports/dec_v61_097_phase_1a_round3.md:4:**Verdict**: `Codex-verified: CHANGES_REQUIRED immediate disconnect after the first start SSE still bypasses the new finally and leaks _active_runs`
reports/codex_tool_reports/dec_v61_099_round1.md:1242:reports/codex_tool_reports/m_render_api_arc/round5.log:47:If clean: APPROVE or APPROVE_WITH_COMMENTS.
reports/codex_tool_reports/dec_v61_099_round1.md:1243:reports/codex_tool_reports/m_render_api_arc/round5.log:61:Verdict: APPROVE | APPROVE_WITH_COMMENTS | CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_099_round1.md:1244:reports/codex_tool_reports/m_render_api_arc/round5.log:2358:Verdict: APPROVE
reports/codex_tool_reports/dec_v61_099_round1.md:1245:reports/codex_tool_reports/m_render_api_arc/round5.log:2371:Verdict: APPROVE
reports/codex_tool_reports/dec_v61_099_round1.md:1246:reports/codex_tool_reports/dec_v61_097_phase_1a_round1.md:4:**Verdict**: `Codex-verified: CHANGES_REQUIRED solve-stream preflight/multi-run correctness is unsafe, and /bc/render is missing mesh-render input hardening`
reports/codex_tool_reports/dec_v61_099_round1.md:1252:reports/codex_tool_reports/m_render_api_arc/round2.log:104:Verdict: APPROVE | APPROVE_WITH_COMMENTS | CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_099_round1.md:1253:reports/codex_tool_reports/m_render_api_arc/round2.log:107:Be terse. If everything is clean and APPROVE, say so without padding.
reports/codex_tool_reports/dec_v61_099_round1.md:1266:reports/codex_tool_reports/m_render_api_arc/README.md:15:| 5 | **APPROVE** ✓ | All 7 findings closed · parity verified | merge-ready |
reports/codex_tool_reports/dec_v61_099_round1.md:1267:reports/codex_tool_reports/m_render_api_arc/round4.log:49:If everything is clean: APPROVE.
reports/codex_tool_reports/dec_v61_099_round1.md:1268:reports/codex_tool_reports/m_render_api_arc/round4.log:63:Verdict: APPROVE | APPROVE_WITH_COMMENTS | CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_099_round1.md:1272:reports/codex_tool_reports/m_render_api_arc/round3.log:50:If everything is clean, just say APPROVE. Be terse.
reports/codex_tool_reports/dec_v61_099_round1.md:1273:reports/codex_tool_reports/m_render_api_arc/round3.log:65:Verdict: APPROVE | APPROVE_WITH_COMMENTS | CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_099_round1.md:1276:reports/codex_tool_reports/dec_v61_075_t2_3_post_commit_round2.md:3:- **Verdict**: CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_099_round1.md:1281:reports/codex_tool_reports/20260422_dec045_wave3_F_taskrunner_reorder_result.md:2240:**Verdict**: APPROVE / APPROVE_WITH_NOTES / CHANGES_REQUIRED / BLOCK
reports/codex_tool_reports/dec_v61_099_round1.md:1282:reports/codex_tool_reports/20260422_dec045_wave3_F_taskrunner_reorder_result.md:2265:- Ready for codex_verdict=APPROVED: YES / NO
reports/codex_tool_reports/dec_v61_099_round1.md:1283:reports/codex_tool_reports/20260422_dec045_wave3_F_taskrunner_reorder_result.md:2482:**Verdict**: APPROVE / APPROVE_WITH_NOTES / CHANGES_REQUIRED / BLOCK
reports/codex_tool_reports/dec_v61_099_round1.md:1284:reports/codex_tool_reports/20260422_dec045_wave3_F_taskrunner_reorder_result.md:2510:- Ready for codex_verdict=APPROVED: YES / NO
reports/codex_tool_reports/dec_v61_099_round1.md:1292:reports/codex_tool_reports/m_render_api_arc/round1.log:88:Verdict (canonical trailer): APPROVE | APPROVE_WITH_COMMENTS | CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_099_round1.md:1293:reports/codex_tool_reports/m_render_api_arc/round1.log:370:  v61_094_acceptance: confirmed (M-VIZ closed 2026-04-28 · commit 36c4a78 · Step-7 visual smoke PASSED · Codex APPROVE_WITH_COMMENTS at round 5 + verbatim halt)
reports/codex_tool_reports/dec_v61_099_round1.md:1374:   294	            # round 4 RESOLVED) on the first live LDC dogfood run.
reports/codex_tool_reports/dec_v61_099_round1.md:1788:   257	    after V61-097 R4 RESOLVED). The V61-097 round-1 HIGH-2 fix introduced
reports/codex_tool_reports/dec_v61_099_round1.md:1899:**Verdict**: `Codex-verified: CHANGES_REQUIRED solve-stream preflight/multi-run correctness is unsafe, and /bc/render is missing mesh-render input hardening`
reports/codex_tool_reports/dec_v61_099_round1.md:1906:## Findings
reports/codex_tool_reports/dec_v61_099_round1.md:1970:**Verdict**: `Codex-verified: RESOLVED round-3 HIGH closed; no regression found in reviewed slice`
reports/codex_tool_reports/dec_v61_099_round1.md:1979:> No findings. `solver_streamer.py:415` now puts the `start` yield inside the outer `try`, and the `finally` block at `:521` now covers `GeneratorExit` on that first yield. `test_solver_streamer.py:255` consumes exactly one `start` event and then `gen.close()`, so it hits the previously missed failure mode; the renamed mid-loop test remains complementary. I found no other `yield` points in `stream_icofoam()` outside the outer `try`.
reports/codex_tool_reports/dec_v61_099_round1.md:1981:> Codex-verified: RESOLVED round-3 HIGH closed; no regression found in reviewed slice
reports/codex_tool_reports/dec_v61_099_round1.md:1992:| 4 | **RESOLVED** | 0 | this commit |
reports/codex_tool_reports/dec_v61_099_round1.md:2009:DEC-V61-097 self-estimated 55% pre-Codex. Actual: needed 4 rounds before APPROVE/RESOLVED. Calibration drift = -55% (4 rounds vs. predicted ≤2). Logging in next retrospective per the methodology.
reports/codex_tool_reports/dec_v61_099_round1.md:2076:+status: Active (2026-04-29 · post-R3 live-run defect per RETRO-V61-053 addendum methodology · Codex pre-merge mandatory per RETRO-V61-001 "OpenFOAM solver 报错修复" trigger · CFDJerry caught on first LDC dogfood after V61-097 R4 RESOLVED commit `c49fd11`)
reports/codex_tool_reports/dec_v61_099_round1.md:2081:+  - DEC-V61-097 (M-PANELS Phase-1A LDC end-to-end demo · closed 2026-04-29 commit c49fd11 · Codex 4-round arc RESOLVED · this DEC closes a DEFECT INTRODUCED IN ROUND 1 of that arc)
reports/codex_tool_reports/dec_v61_099_round1.md:2086:+  - reports/codex_tool_reports/dec_v61_097_phase_1a_round4.md (round 4 RESOLVED · static review missed the runtime defect)
reports/codex_tool_reports/dec_v61_099_round1.md:2277:+3. **Live-run smoke before R4 RESOLVED**: per RETRO-V61-053
reports/codex_tool_reports/dec_v61_099_round1.md:2278:+   addendum, every Codex APPROVE arc should ideally have at least
reports/codex_tool_reports/dec_v61_099_round1.md:2280:+   was declared RESOLVED based on static analysis only (Codex round 4
reports/codex_tool_reports/dec_v61_099_round1.md:2371:+            # round 4 RESOLVED) on the first live LDC dogfood run.
reports/codex_tool_reports/dec_v61_099_round1.md:2542:+    after V61-097 R4 RESOLVED). The V61-097 round-1 HIGH-2 fix introduced
reports/codex_tool_reports/dec_v61_099_round1.md:3794:- Caught on first LDC dogfood ~1 hour after V61-097 R4 RESOLVED.
reports/codex_tool_reports/dec_v61_099_round1.md:3809:Return verdict in standard format: APPROVE / CHANGES_REQUIRED with severity-classified findings (HIGH/MED/LOW). Reference reports/codex_tool_reports/dec_v61_097_phase_1a_round*.md for verdict format.
reports/codex_tool_reports/dec_v61_099_round1.md:3824:ui/backend/tests/test_solver_streamer.py:257:    after V61-097 R4 RESOLVED). The V61-097 round-1 HIGH-2 fix introduced
reports/codex_tool_reports/dec_v61_099_round1.md:3862:reports/codex_tool_reports/dec_v61_097_phase_1a_round4.md:43:DEC-V61-097 self-estimated 55% pre-Codex. Actual: needed 4 rounds before APPROVE/RESOLVED. Calibration drift = -55% (4 rounds vs. predicted ≤2). Logging in next retrospective per the methodology.
reports/codex_tool_reports/dec_v61_099_round1.md:3881:reports/codex_tool_reports/dec_v61_099_round1.md:20:- Caught on first LDC dogfood ~1 hour after V61-097 R4 RESOLVED.

exec
/bin/zsh -lc "nl -ba /Users/Zhuanz/.codex/memories/MEMORY.md | sed -n '2048,2056p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
  2048	- The expected deliverable shape is one section per area with reviewed line ranges, `BUG / WARNING / OK` findings, exact snippets for non-OK items, and a final table `| Area | BUGs | WARNINGs | Status |` [Task 1]
  2049	- Prior high-signal defects worth reusing as bug patterns in this repo include alias-sensitive hard constraints, tiny-positive log-score flattening, E6 retry state leaking across specs, planner matrix fallbacks that hide missing coverage, and binary STL truncation being accepted as partial success [Task 2]
  2050	
  2051	## Failures and how to do differently
  2052	
  2053	- Symptom: a review answer drifts into general commentary or architecture advice -> cause: treating “review” as broad feedback instead of a defect audit -> fix: report only grounded correctness findings with file/line references [Task 1]
  2054	- Symptom: a path looks missing and the review stops there -> cause: failing to search for similarly named files first -> fix: search nearby names/locations before concluding absence, then say explicitly what was and was not found [Task 1]
  2055	
  2056	# Task Group: Local Codex account switching and resume workflow

codex
# Codex review · DEC-V61-099 · Round 2

- **Verdict**: `Codex-verified: RESOLVED round-1 MED closed; no new HIGH/MED found in reviewed slice`
- **Reviewed slice**: staged changes in [solver_streamer.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/case_solve/solver_streamer.py:302) and [test_solver_streamer.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_solver_streamer.py:344)
- **Date**: 2026-04-29

## Findings

> No findings. The round-1 MED is fully closed: [solver_streamer.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/case_solve/solver_streamer.py:302) now checks `mkdir_res.exit_code` after the BASE-mkdir `exec_run`, and [solver_streamer.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/case_solve/solver_streamer.py:328) now checks `rename_res.exit_code` after the `rm -rf` / `mv` / `chmod` staging `exec_run`. The new tests at [test_solver_streamer.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_solver_streamer.py:344) and [test_solver_streamer.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_solver_streamer.py:400) exercise those exact non-zero-exit failure paths and also verify `_active_runs` is released for retry. Against the buggy version that ignored `exit_code`, both `pytest.raises(SolverRunError)` assertions would fail because `_prepare_stream_icofoam()` would return normally. This matches the round-1 recommendation verbatim enough to treat the finding as closed.

## Residual gap

- I could not rerun `ui/backend/tests/test_solver_streamer.py` in this session because `pytest` currently stops in `ui/backend/tests/conftest.py` with `ModuleNotFoundError: No module named 'trimesh'`. The review verdict above is therefore based on staged diff inspection plus control-flow analysis, not an independently reproduced local test pass.


tokens used
42,840
# Codex review · DEC-V61-099 · Round 2

- **Verdict**: `Codex-verified: RESOLVED round-1 MED closed; no new HIGH/MED found in reviewed slice`
- **Reviewed slice**: staged changes in [solver_streamer.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/case_solve/solver_streamer.py:302) and [test_solver_streamer.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_solver_streamer.py:344)
- **Date**: 2026-04-29

## Findings

> No findings. The round-1 MED is fully closed: [solver_streamer.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/case_solve/solver_streamer.py:302) now checks `mkdir_res.exit_code` after the BASE-mkdir `exec_run`, and [solver_streamer.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/case_solve/solver_streamer.py:328) now checks `rename_res.exit_code` after the `rm -rf` / `mv` / `chmod` staging `exec_run`. The new tests at [test_solver_streamer.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_solver_streamer.py:344) and [test_solver_streamer.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_solver_streamer.py:400) exercise those exact non-zero-exit failure paths and also verify `_active_runs` is released for retry. Against the buggy version that ignored `exit_code`, both `pytest.raises(SolverRunError)` assertions would fail because `_prepare_stream_icofoam()` would return normally. This matches the round-1 recommendation verbatim enough to treat the finding as closed.

## Residual gap

- I could not rerun `ui/backend/tests/test_solver_streamer.py` in this session because `pytest` currently stops in `ui/backend/tests/conftest.py` with `ModuleNotFoundError: No module named 'trimesh'`. The review verdict above is therefore based on staged diff inspection plus control-flow analysis, not an independently reproduced local test pass.


