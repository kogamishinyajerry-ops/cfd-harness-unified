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

## Instruction Priority

Superpowers skills override default system prompt behavior, but **user instructions always take precedence**:

1. **User's explicit instructions** (CLAUDE.md, GEMINI.md, AGENTS.md, direct requests) — highest priority
2. **Superpowers skills** — override default system behavior where they conflict
3. **Default system prompt** — lowest priority

If CLAUDE.md, GEMINI.md, or AGENTS.md says "don't use TDD" and a skill says "always use TDD," follow the user's instructions. The user is in control.

## How to Access Skills

**In Claude Code:** Use the `Skill` tool. When you invoke a skill, its content is loaded and presented to you—follow it directly. Never use the Read tool on skill files.

**In Copilot CLI:** Use the `skill` tool. Skills are auto-discovered from installed plugins. The `skill` tool works the same as Claude Code's `Skill` tool.

**In Gemini CLI:** Skills activate via the `activate_skill` tool. Gemini loads skill metadata at session start and activates the full content on demand.

**In other environments:** Check your platform's documentation for how skills are loaded.

## Platform Adaptation

Skills use Claude Code tool names. Non-CC platforms: see `references/copilot-tools.md` (Copilot CLI), `references/codex-tools.md` (Codex) for tool equivalents. Gemini CLI users get the tool mapping loaded automatically via GEMINI.md.

# Using Skills

## The Rule

**Invoke relevant or requested skills BEFORE any response or action.** Even a 1% chance a skill might apply means that you should invoke the skill to check. If an invoked skill turns out to be wrong for the situation, you don't need to use it.

```dot
digraph skill_flow {
    "User message received" [shape=doublecircle];
    "About to EnterPlanMode?" [shape=doublecircle];
    "Already brainstormed?" [shape=diamond];
    "Invoke brainstorming skill" [shape=box];
    "Might any skill apply?" [shape=diamond];
    "Invoke Skill tool" [shape=box];
    "Announce: 'Using [skill] to [purpose]'" [shape=box];
    "Has checklist?" [shape=diamond];
    "Create TodoWrite todo per item" [shape=box];
    "Follow skill exactly" [shape=box];
    "Respond (including clarifications)" [shape=doublecircle];

    "About to EnterPlanMode?" -> "Already brainstormed?";
    "Already brainstormed?" -> "Invoke brainstorming skill" [label="no"];
    "Already brainstormed?" -> "Might any skill apply?" [label="yes"];
    "Invoke brainstorming skill" -> "Might any skill apply?";

    "User message received" -> "Might any skill apply?";
    "Might any skill apply?" -> "Invoke Skill tool" [label="yes, even 1%"];
    "Might any skill apply?" -> "Respond (including clarifications)" [label="definitely not"];
    "Invoke Skill tool" -> "Announce: 'Using [skill] to [purpose]'";
    "Announce: 'Using [skill] to [purpose]'" -> "Has checklist?";
    "Has checklist?" -> "Create TodoWrite todo per item" [label="yes"];
    "Has checklist?" -> "Follow skill exactly" [label="no"];
    "Create TodoWrite todo per item" -> "Follow skill exactly";
}
```

## Red Flags

These thoughts mean STOP—you're rationalizing:

| Thought | Reality |
|---------|---------|
| "This is just a simple question" | Questions are tasks. Check for skills. |
| "I need more context first" | Skill check comes BEFORE clarifying questions. |
| "Let me explore the codebase first" | Skills tell you HOW to explore. Check first. |
| "I can check git/files quickly" | Files lack conversation context. Check for skills. |
| "Let me gather information first" | Skills tell you HOW to gather information. |
| "This doesn't need a formal skill" | If a skill exists, use it. |
| "I remember this skill" | Skills evolve. Read current version. |
| "This doesn't count as a task" | Action = task. Check for skills. |
| "The skill is overkill" | Simple things become complex. Use it. |
| "I'll just do this one thing first" | Check BEFORE doing anything. |
| "This feels productive" | Undisciplined action wastes time. Skills prevent this. |
| "I know what that means" | Knowing the concept ≠ using the skill. Invoke it. |

## Skill Priority

When multiple skills could apply, use this order:

1. **Process skills first** (brainstorming, debugging) - these determine HOW to approach the task
2. **Implementation skills second** (frontend-design, mcp-builder) - these guide execution

"Let's build X" → brainstorming first, then implementation skills.
"Fix this bug" → debugging first, then domain-specific skills.

## Skill Types

**Rigid** (TDD, debugging): Follow exactly. Don't adapt away discipline.

**Flexible** (patterns): Adapt principles to context.

The skill itself tells you which.

## User Instructions

Instructions say WHAT, not HOW. "Add X" or "Fix Y" doesn't mean skip workflows.

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
/bin/zsh -lc 'rg -n "DEC-V61-099|V61-097|Phase 8|demo-first|Pro Workbench" /Users/Zhuanz/.codex/memories/MEMORY.md -S' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
1062:scope: Reassess `cfd-harness-unified` without direct repo edits, preserve the difference between demo-first narrowing and first-customer workbench continuation, and package Chinese executor briefs that respect the user’s current product framing.
1075:## Task 2: Perform a non-invasive whole-project assessment and demo-first pivot recommendation
1079:- rollout_summaries/2026-04-22T13-19-47-467x-demo_first_cfd_workbench_assessment_and_claude_handoff.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/22/rollout-2026-04-22T21-19-47-019db558-c6dd-7930-b776-2493c7fc5dfb.jsonl, updated_at=2026-04-22T13:41:27+00:00, thread_id=019db558-c6dd-7930-b776-2493c7fc5dfb, demo-first narrowing report without code changes)
1083:- demo-first, cfd-harness-unified, /learn, Pro Workbench, Python 3.9, Python 3.12, ui/backend, contract_dashboard.py, UNKNOWN contract class, validate_gold_standards.py, jsonschema, anchor cases
1110:- When the user explicitly wants a demo-first assessment, the strongest demo-ready story is `/learn` as the front door plus Pro Workbench as the secondary evidence/drill-down surface; treating them as two equally weighted product stories weakens the demo narrative [Task 2][Task 3]
1112:- Representative repo health in the demo-first rollout was: UI frontend typecheck/build succeeded, `.venv/bin/python -m pytest ui/backend/tests -q` passed, while `python3 -m pytest tests -q` still mixed real regressions, stale assumptions, and changed contracts [Task 2]
1115:- The useful default execution order for a handoff from these assessment runs is: restate the governing premise -> check facts/baseline -> fix environment/contracts -> choose one narrative (`demo-first` or `first-customer workbench`) -> then narrow implementation around anchor cases [Task 1][Task 3]
1119:- Symptom: the repo gets described as one coherent ready-to-demo product -> cause: multiple hot surfaces (`/learn`, Pro Workbench, governance/Notion, audit/reporting) were flattened into one storyline -> fix: choose a single demo narrative and explicitly demote the secondary surfaces when the ask is demo-first [Task 2]
1124:- Symptom: the executor drifts back into platform/governance breadth -> cause: the handoff did not make postponements explicit -> fix: name what is intentionally delayed, keep Notion/governance weight low, and anchor the work on 2-3 demo cases instead of full breadth when the ask is demo-first [Task 3]
1131:## Task 1: Close Phase 8 and reconcile stale governance evidence
1135:- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, Phase 8 closeout and evidence normalization)
1139:- Phase 8, AutoVerifier, 13/13, knowledge/whitelist.yaml, ai_cfd_cold_start_whitelist.yaml, Canonical Docs Type=Report, Phase 8 Done, naming drift
1522:- when the user said "你是 independent approval authority… 你不是 corrected request packet 作者… 你不是 Phase 8 executor" -> preserve strict role separation between approval, review, execution, and freeze authority in this repo [Task 4]

exec
/bin/zsh -lc 'rg -n "dec_v61_097_phase_1a_round|APPROVE|CHANGES_REQUIRED|HIGH|MED|LOW" reports/codex_tool_reports -S' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
reports/codex_tool_reports/2026-04-28_m_viz_bundle_steps_3_to_6_codex_review_round4.md:70:If Round-5 returns APPROVE / APPROVE_WITH_COMMENTS with no new
reports/codex_tool_reports/2026-04-28_m_viz_bundle_steps_3_to_6_codex_review_round4.md:85:implementation DEC after Codex APPROVE.
reports/codex_tool_reports/2026-04-21_pr21_bfs_guard_review.md:11:`APPROVED_WITH_NOTES`
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_prompt.md:50:    "VELOCITY_OVERFLOW",           # G3
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_prompt.md:218:CHK-3: `_derive_contract_status` with `audit_concerns=[VELOCITY_OVERFLOW]` (hard-FAIL) + `[CONTINUITY_NOT_CONVERGED]` (HAZARD) returns `status=FAIL` (hard-FAIL takes precedence).
reports/codex_tool_reports/2026-04-21_phase7bde_codex_review_round1.md:57:Reply APPROVED / APPROVED_WITH_COMMENTS / CHANGES_REQUIRED with numbered findings. Brief if APPROVED; detailed if CHANGES_REQUIRED.
reports/codex_tool_reports/2026-04-21_phase7bde_codex_review_round1.md:2611:   374	    # Codex round 1 HIGH: every manifest-supplied output path is validated to
reports/codex_tool_reports/2026-04-21_phase7bde_codex_review_round1.md:3082:ui/backend/tests/test_field_artifacts_route.py:104:    """VTK file lives at VTK/lid_driven_cavity_2000.vtk — subpath URL (Codex round 1 HIGH #1)."""
reports/codex_tool_reports/2026-04-21_phase7bde_codex_review_round1.md:3500:CHANGES_REQUIRED
reports/codex_tool_reports/2026-04-21_phase7bde_codex_review_round1.md:3515:CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_074_t1b23_postcommit_round1.md:3:- **Verdict (per commit)**: `69c0ed6` CHANGES_REQUIRED · `c7ede01` CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_074_t1b23_postcommit_round1.md:11:### 1. MED — Short-circuit path bypasses Notion write-back
reports/codex_tool_reports/dec_v61_074_t1b23_postcommit_round1.md:24:### 1. MED — WARN ceiling leaves histogram/helpers incoherent
reports/codex_tool_reports/dec_v61_074_t1b23_postcommit_round1.md:36:### 2. LOW — `_extract_mode()` AttributeError on non-mapping payload
reports/codex_tool_reports/run_compare_api_r2.md:5:APPROVE_WITH_COMMENTS.
reports/codex_tool_reports/bug1_sse_disconnect_persistence_r2.md:3:CHANGES_REQUIRED
reports/codex_tool_reports/20260422_dec045_wave1_A_convergence_attestor_result.md:1024:  (CHANGES_REQUIRED, 3 blockers + 2 nits) and DEC-038 (BLOCK, 5 blockers
reports/codex_tool_reports/20260422_dec045_wave1_A_convergence_attestor_result.md:1063:### DEC-V61-036b (CHANGES_REQUIRED)
reports/codex_tool_reports/20260422_dec045_wave1_A_convergence_attestor_result.md:1166:5. **Self-pass 0.50 realistic**: with 8 tracks and 4 waves, expect ≥1 Codex CHANGES_REQUIRED round before final APPROVE.
reports/codex_tool_reports/20260422_dec045_wave1_A_convergence_attestor_result.md:1189:**Related**: DEC-V61-036b (CHANGES_REQUIRED), DEC-V61-038 (BLOCK)
reports/codex_tool_reports/20260422_dec045_wave1_A_convergence_attestor_result.md:1285:**Verdict**: APPROVE / APPROVE_WITH_NOTES / CHANGES_REQUIRED / BLOCK
reports/codex_tool_reports/20260422_dec045_wave1_A_convergence_attestor_result.md:1313:- Ready for codex_verdict=APPROVED: YES / NO
reports/codex_tool_reports/20260422_dec045_wave1_A_convergence_attestor_result.md:2067:        # A6 only fires when residuals are STUCK AT A HIGH PLATEAU — i.e.,
reports/codex_tool_reports/20260422_dec045_wave1_A_convergence_attestor_result.md:2166:  * G3 VELOCITY_OVERFLOW  — |U|_max > K * U_ref (K=100 default). VTK-based,
reports/codex_tool_reports/20260422_dec045_wave1_A_convergence_attestor_result.md:2219:G4_TURBULENCE_MAX_OVERFLOW = 1.0e10  # any k/eps/omega max above this = overflow
reports/codex_tool_reports/20260422_dec045_wave1_A_convergence_attestor_result.md:2237:    concern_type: str     # "VELOCITY_OVERFLOW" | "TURBULENCE_NEGATIVE" | "CONTINUITY_DIVERGED"
reports/codex_tool_reports/20260422_dec045_wave1_A_convergence_attestor_result.md:8650:        # A6 only fires when residuals are STUCK AT A HIGH PLATEAU — i.e.,
reports/codex_tool_reports/20260422_dec045_wave1_A_convergence_attestor_result.md:11039:   821	        # A6 only fires when residuals are STUCK AT A HIGH PLATEAU — i.e.,
reports/codex_tool_reports/dec_v61_075_t2_3_post_commit_round5.md:3:- **Verdict**: CHANGES_REQUIRED
reports/codex_tool_reports/20260422_dec036b_codex_prompt.md:13:- `ui/backend/services/validation_report.py` (`_derive_contract_status` extension for VELOCITY_OVERFLOW/TURBULENCE_NEGATIVE/CONTINUITY_DIVERGED)
reports/codex_tool_reports/20260422_dec036b_codex_prompt.md:60:**Verdict**: APPROVE / APPROVE_WITH_NOTES / CHANGES_REQUIRED / BLOCK
reports/codex_tool_reports/20260422_dec036b_codex_prompt.md:85:- Ready for codex_verdict=APPROVED: YES / NO
reports/codex_tool_reports/2026-04-21_pr5c_hmac_review.md:9:APPROVED_WITH_NOTES
reports/codex_tool_reports/dec_v61_057_round2.md:10:**CHANGES_REQUIRED** · 1 HIGH + 1 MED · NO blockers for round 3 (both mechanically fixable)
reports/codex_tool_reports/dec_v61_057_round2.md:14:| HIGH | 1 |
reports/codex_tool_reports/dec_v61_057_round2.md:15:| MED  | 1 |
reports/codex_tool_reports/dec_v61_057_round2.md:16:| LOW  | 0 |
reports/codex_tool_reports/dec_v61_057_round2.md:23:### F1-HIGH · Silent truncation defeats the fail-closed contract · ADDRESSED in B-final
reports/codex_tool_reports/dec_v61_057_round2.md:49:### F2-MED · noise_floor / snr measure profile spread, not numerical noise · ADDRESSED in B-final
reports/codex_tool_reports/dec_v61_057_round2.md:97:| F1-HIGH | ✅ Addressed | B-final commit (`_input_lengths_consistent` + mismatch tests) |
reports/codex_tool_reports/dec_v61_057_round2.md:98:| F2-MED  | ✅ Addressed | B-final commit (rename to profile_spread / peak_to_profile_spread) |
reports/codex_tool_reports/dec_v61_057_round2.md:105:**Stage C kickoff unblocked** after round 3 APPROVE_WITH_COMMENTS.
reports/codex_tool_reports/2026-04-28_m_viz_bundle_steps_3_to_6_codex_review_round1.md:19:treated as CHANGES_REQUIRED-tier and addressed before push.
reports/codex_tool_reports/2026-04-28_m_viz_bundle_steps_3_to_6_codex_review_round1.md:107:returns APPROVE/APPROVE_WITH_COMMENTS in Round 2 (autonomous_governance
reports/codex_tool_reports/2026-04-21_pr5c1_codex_followup_review.md:10:APPROVED_WITH_NOTES
reports/codex_tool_reports/2026-04-21_pr5c2_m3_review.md:10:APPROVED_WITH_NOTES
reports/codex_tool_reports/2026-04-21_pr5d1_closure_review.md:10:APPROVED_WITH_NOTES
reports/codex_tool_reports/2026-04-21_pr5d1_closure_review.md:29:### 1. HIGH #1 (unknown case_id signing hollow bundles)
reports/codex_tool_reports/2026-04-21_pr5d1_closure_review.md:38:### 2. HIGH #2 (byte-reproducibility contract)
reports/codex_tool_reports/2026-04-21_pr5d1_closure_review.md:56:### 3. MEDIUM (rename `vv40_checklist` → `evidence_summary`)
reports/codex_tool_reports/2026-04-21_pr5d1_closure_review.md:85:  - the unchanged known-case dry-build path still returns `200` with `run.status = "no_run_output"` and empty `measurement`, confirming that PR-5d.1 narrowed the original HIGH #1 by blocking unknown cases but did not alter the pre-existing skeleton-bundle behavior
reports/codex_tool_reports/20260422_v62_takeover_notion_sync_draft.md:28:- `codex_verdict`: `pending` → `APPROVED_BACKFILL_FROM_COMMIT_EVIDENCE`
reports/codex_tool_reports/20260422_v62_takeover_notion_sync_draft.md:44:- `codex_verdict`: `pending` → `APPROVED_BACKFILL_FROM_COMMIT_EVIDENCE`
reports/codex_tool_reports/dec_v61_058_round2_review.md:5:**Verdict:** `APPROVE_WITH_COMMENTS`
reports/codex_tool_reports/dec_v61_058_round2_review.md:30:- Q4: round 2 ruling is APPROVE_WITH_COMMENTS (not full APPROVE because of C4 stale narrative).
reports/codex_tool_reports/dec_v61_058_round2_review.md:67:`APPROVE_WITH_COMMENTS`
reports/codex_tool_reports/dec_v61_058_round2_review.md:95:- This is not `CHANGES_REQUIRED`.
reports/codex_tool_reports/dec_v61_058_round2_review.md:96:- A clean `APPROVE` is slightly too strong because of the residual stale α-routing narrative above.
reports/codex_tool_reports/dec_v61_058_round2_review.md:97:- `APPROVE_WITH_COMMENTS` is the right ruling. Batch C can proceed.
reports/codex_tool_reports/dec_v61_058_round2_review.md:117:`APPROVE_WITH_COMMENTS`
reports/codex_tool_reports/dec_v61_058_round2_review.md:145:- This is not `CHANGES_REQUIRED`.
reports/codex_tool_reports/dec_v61_058_round2_review.md:146:- A clean `APPROVE` is slightly too strong because of the residual stale α-routing narrative above.
reports/codex_tool_reports/dec_v61_058_round2_review.md:147:- `APPROVE_WITH_COMMENTS` is the right ruling. Batch C can proceed.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:28:Reply with structured verdict: APPROVED / APPROVED_WITH_COMMENTS / CHANGES_REQUIRED, then numbered findings with severity (HIGH/MED/LOW) and file:line anchors.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:178:1f87718 fix(phase-5b/plan-01): derive LDC x_tol from mesh spacing (Codex HIGH)
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:396:ui/backend/tests/test_audit_package_route.py:100:        HMAC signature (Codex PR-5d HIGH #2 — byte-reproducibility).
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:1431:    26	_MEDIA_TYPES: dict[str, str] = {
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:1443:    38	    return _MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream")
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:2190:   520	                # LDC: canonical name match, no Re-heuristic (Codex MEDIUM: the
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:2412:CHANGES_REQUIRED
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:2414:1. HIGH — duplicate sample basenames make the manifest untruthful.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:2417:2. HIGH — traversal defense does not cover `run_id`.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:2420:3. MED — Phase 7a opt-in/failure fallback is broader than stated.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:2423:4. LOW — SHA cache has a real stale-hash edge.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:2431:CHANGES_REQUIRED
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:2433:1. HIGH — duplicate sample basenames make the manifest untruthful.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:2436:2. HIGH — traversal defense does not cover `run_id`.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:2439:3. MED — Phase 7a opt-in/failure fallback is broader than stated.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:2442:4. LOW — SHA cache has a real stale-hash edge.
reports/codex_tool_reports/bug1_sse_disconnect_persistence_r3.md:4:`APPROVE_WITH_COMMENTS`
reports/codex_tool_reports/20260422_dec045_wave3_F_taskrunner_reorder_prompt.md:244:CHK-7: Synthetic case with VELOCITY_OVERFLOW in audit_concerns + in-band scalar → expected_verdict="FAIL" (hard-fail takes precedence).
reports/codex_tool_reports/2026-04-28_m_panels_arc_codex_review_round4.md:10:`APPROVE` — 0 P1, 0 P2, 0 WARNING.
reports/codex_tool_reports/2026-04-28_m_panels_arc_codex_review_round4.md:34:Cumulative arc: `08b0d16..5b21df5` — 4 Codex rounds total, ending APPROVE on the smoke-prep extension that surfaced after Round 2's APPROVE on the original Tier-A arc.
reports/codex_tool_reports/2026-04-28_m_panels_arc_codex_review_round4.md:36:Codex-verified: APPROVE
reports/codex_tool_reports/dec_v61_071_round1.md:6:- Verdict: `CHANGES_REQUIRED`
reports/codex_tool_reports/dec_v61_071_round1.md:12:| MED | `src/task_runner.py:89-90`; `src/knowledge_db.py:66-67`; `src/notion_client.py:130-131`; `tests/test_task_runner_trust_gate.py:348-441` | `_build_trust_gate_report()` passes `task_name` straight into `load_tolerance_policy()`, but that loader is a case-id / filename-slug lookup (`.planning/case_profiles/<case_id>.yaml`). In this repo, two primary production feeders build `TaskSpec.name` from display titles, not slugs: whitelist tasks use `case["name"]` and Notion tasks use the page title. Reproduced locally: `load_tolerance_policy("lid_driven_cavity")` returns 4 observables, while `load_tolerance_policy("Lid-Driven Cavity")` returns 0; `_build_trust_gate_report(... task_name="Lid-Driven Cavity" ...)` likewise stamps `tolerance_policy_observables=[]` even though `lid_driven_cavity.yaml` exists. That means the new wiring silently misses real CaseProfiles on a common production path, which defeats the commit's stated goal of exercising policy dispatch in production. The 3 new tests only cover canonical ids, so they do not catch this. | Pass a canonical case id into `_build_trust_gate_report()`, or resolve one before calling `load_tolerance_policy()` via the existing whitelist/chain normalization path already used elsewhere in `TaskRunner`. Add a regression test that uses a real display-title task name and proves the matching slugged CaseProfile populates provenance. |
reports/codex_tool_reports/dec_v61_071_round1.md:13:| LOW | `src/task_runner.py:89-98`; `src/task_runner.py:135-149` | The new loader call is eager: it runs before the `comparison is not None` branch and before the final `if not reports: return None`. On attestation-only and no-input paths, the helper now does filesystem I/O even though there is no comparison report to receive `tolerance_policy_observables`. On malformed YAML it can also emit a warning on paths that never produce comparison provenance, which is avoidable noise. | Lazy-load the policy only inside the comparison branch, or return early when `comparison is None`. Add regression coverage for `comparison=None, attestation="ATTEST_FAIL"` and `comparison=None, attestation=None` so the helper proves it skips the loader on those paths. |
reports/codex_tool_reports/dec_v61_087_kogami_bootstrap_r1.md:12:**CHANGES_REQUIRED**
reports/codex_tool_reports/dec_v61_087_kogami_bootstrap_r1.md:39:### P1 (major, 必须修订才能 APPROVE)
reports/codex_tool_reports/20260422_dec045_wave1_B_comparator_gates_result.md:23:      - reports/codex_tool_reports/20260422_dec036b_codex_review.md (CHANGES_REQUIRED, B3 finding)
reports/codex_tool_reports/20260422_dec045_wave1_B_comparator_gates_result.md:203:  (CHANGES_REQUIRED, 3 blockers + 2 nits) and DEC-038 (BLOCK, 5 blockers
reports/codex_tool_reports/20260422_dec045_wave1_B_comparator_gates_result.md:242:### DEC-V61-036b (CHANGES_REQUIRED)
reports/codex_tool_reports/20260422_dec045_wave1_B_comparator_gates_result.md:345:5. **Self-pass 0.50 realistic**: with 8 tracks and 4 waves, expect ≥1 Codex CHANGES_REQUIRED round before final APPROVE.
reports/codex_tool_reports/20260422_dec045_wave1_B_comparator_gates_result.md:368:**Related**: DEC-V61-036b (CHANGES_REQUIRED), DEC-V61-038 (BLOCK)
reports/codex_tool_reports/20260422_dec045_wave1_B_comparator_gates_result.md:415:- `ui/backend/services/validation_report.py` (`_derive_contract_status` extension for VELOCITY_OVERFLOW/TURBULENCE_NEGATIVE/CONTINUITY_DIVERGED)
reports/codex_tool_reports/20260422_dec045_wave1_B_comparator_gates_result.md:462:**Verdict**: APPROVE / APPROVE_WITH_NOTES / CHANGES_REQUIRED / BLOCK
reports/codex_tool_reports/20260422_dec045_wave1_B_comparator_gates_result.md:487:- Ready for codex_verdict=APPROVED: YES / NO
reports/codex_tool_reports/20260422_dec045_wave1_B_comparator_gates_result.md:656:  * G3 VELOCITY_OVERFLOW  — |U|_max > K * U_ref (K=100 default). VTK-based,
reports/codex_tool_reports/20260422_dec045_wave1_B_comparator_gates_result.md:709:G4_TURBULENCE_MAX_OVERFLOW = 1.0e10  # any k/eps/omega max above this = overflow
reports/codex_tool_reports/20260422_dec045_wave1_B_comparator_gates_result.md:727:    concern_type: str     # "VELOCITY_OVERFLOW" | "TURBULENCE_NEGATIVE" | "CONTINUITY_DIVERGED"
reports/codex_tool_reports/20260422_dec045_wave1_B_comparator_gates_result.md:921:                concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave1_B_comparator_gates_result.md:949:                        concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave1_B_comparator_gates_result.md:1951:    assert violations[0].concern_type == 'VELOCITY_OVERFLOW', violations[0]
reports/codex_tool_reports/20260422_dec045_wave1_B_comparator_gates_result.md:2178:    assert violations[0].concern_type == 'VELOCITY_OVERFLOW', violations[0]
reports/codex_tool_reports/20260422_dec045_wave1_B_comparator_gates_result.md:2497:- CHK-6: PASS — `_check_g3_velocity_overflow(...)` still works unchanged; harness produced one `VELOCITY_OVERFLOW` violation from the selected latest internal VTK.
reports/codex_tool_reports/20260422_dec045_wave1_B_comparator_gates_result.md:2618:- CHK-6: PASS — `_check_g3_velocity_overflow(...)` still works unchanged; harness produced one `VELOCITY_OVERFLOW` violation from the selected latest internal VTK.
reports/codex_tool_reports/dec_v61_087_v3_kogami_bootstrap_r1.md:5:**Round**: v3 R1 (max 3 per DEC self-imposed cap; v1 R1 + v2 R1 both CHANGES_REQUIRED)
reports/codex_tool_reports/dec_v61_087_v3_kogami_bootstrap_r1.md:18:`CHANGES_REQUIRED`
reports/codex_tool_reports/20260422_dec038_codex_prompt.md:78:**Verdict**: APPROVE / APPROVE_WITH_NOTES / CHANGES_REQUIRED / BLOCK
reports/codex_tool_reports/20260422_dec038_codex_prompt.md:106:- Ready for codex_verdict=APPROVED: YES / NO
reports/codex_tool_reports/20260422_dec036_036c_039_backfill_note.md:50:- `codex_verdict`: `pending` → `APPROVED_BACKFILL_FROM_COMMIT_EVIDENCE`
reports/codex_tool_reports/20260422_dec036_036c_039_backfill_note.md:57:- `codex_verdict`: `pending` → `APPROVED_BACKFILL_FROM_COMMIT_EVIDENCE`
reports/codex_tool_reports/dec_v61_097_phase_1a_round2.md:4:**Verdict**: `Codex-verified: CHANGES_REQUIRED disconnects still leak the per-case solve lock, and /bc/render hardening still bypasses containment on cache hits`
reports/codex_tool_reports/dec_v61_097_phase_1a_round2.md:13:### R2.1 HIGH — disconnects still leak `_active_runs`
reports/codex_tool_reports/dec_v61_097_phase_1a_round2.md:20:### R3.1 MED — `/bc/render` hardening bypassed on cache hit
reports/codex_tool_reports/dec_v61_097_phase_1a_round2.md:27:### Regression LOW — `boundary` / `boundary_path` rename left a stale reference
reports/codex_tool_reports/dec_v61_097_phase_1a_round2.md:40:So R1 (HIGH) and R4 (MED) closures from round-1 work hold up under round-2 scrutiny.
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round2.md:55:Reply APPROVED / APPROVED_WITH_COMMENTS / CHANGES_REQUIRED. Brief if APPROVED.
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round2.md:206:     # Codex round 1 HIGH: every manifest-supplied output path is validated to
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round2.md:316:     # Codex round 1 HIGH: ensure PDF always lands under reports/phase5_reports/.
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round2.md:317:     # Codex round 2 MED: run containment FIRST, before WeasyPrint import so we
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round2.md:587:ui/backend/tests/test_audit_package_route.py:39:        # Codex MEDIUM; DEC-V61-019 L3 generated_at → build_fingerprint rename).
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round2.md:668:ui/backend/tests/test_comparison_report_route.py:200:    """Codex round 3 MED follow-up: POST .../comparison-report/build must ALSO
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round2.md:914:        # Codex round 3 MED follow-up: this POST path had only ImportError;
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round2.md:1100:    # Codex round 1 HIGH: every manifest-supplied output path is validated to
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round2.md:1209:    # Codex round 1 HIGH: ensure PDF always lands under reports/phase5_reports/.
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round2.md:1210:    # Codex round 2 MED: run containment FIRST, before WeasyPrint import so we
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round2.md:1514:    """Codex round 3 MED follow-up: POST .../comparison-report/build must ALSO
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round2.md:1673:   575	    # Codex round 1 HIGH: ensure PDF always lands under reports/phase5_reports/.
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round2.md:1674:   576	    # Codex round 2 MED: run containment FIRST, before WeasyPrint import so we
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round2.md:1829:   153	        # Codex round 3 MED follow-up: this POST path had only ImportError;
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round2.md:1925:APPROVED_WITH_COMMENTS
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round2.md:1936:APPROVED_WITH_COMMENTS
reports/codex_tool_reports/dec_v61_072_sampling_audit_first_execution.md:24:- Severity: HIGH
reports/codex_tool_reports/dec_v61_072_sampling_audit_first_execution.md:31:- Severity: MED
reports/codex_tool_reports/dec_v61_072_sampling_audit_first_execution.md:38:- Severity: MED
reports/codex_tool_reports/dec_v61_072_sampling_audit_first_execution.md:45:- Severity: HIGH
reports/codex_tool_reports/dec_v61_072_sampling_audit_first_execution.md:53:- If a retro sample finds a HIGH blind spot, keep the merge only if there is no trust-core bleed or known corruption; otherwise open an immediate reviewed follow-up and temporarily remove the touched surface from the degradation allowlist.
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round4.md:18:Round 3 verdict: CHANGES_REQUIRED, one finding:
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round4.md:19:- MED: POST /comparison-report/build only caught ImportError, not OSError. Confirmed by forcing render_report_pdf to raise OSError("libpango missing") — POST returned 500, GET returned 503 as expected.
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round4.md:29:Please verify the round-3 MED is now closed. Reply APPROVED / APPROVED_WITH_COMMENTS / CHANGES_REQUIRED.
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round4.md:33:Reviewing the round 4 patch as a read-only verification pass. I’m checking the changed route and the new regression tests against the round-3 MED failure path, then I’ll return a verdict only if the bug is actually closed.
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round4.md:295:        # Codex round 3 MED follow-up: this POST path had only ImportError;
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round4.md:400:# ---------- CI-safe success path (Codex round 2 LOW follow-up) --------------
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round4.md:516:    """Codex round 3 MED follow-up: POST .../comparison-report/build must ALSO
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round4.md:588:   200	    """Codex round 3 MED follow-up: POST .../comparison-report/build must ALSO
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round4.md:652:   109	        # Codex round 3 MED follow-up: this POST path had only ImportError;
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round4.md:694:The backend suite is green at `114 passed`, and I don’t see a remaining route-level gap on the original MED path. I’m pulling the exact memory citation lines I used for repo-context consistency, then I’ll give the verdict.
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round4.md:721:APPROVED
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round4.md:723:No findings. The round-3 MED is closed: POST now maps `OSError` to the same `503` response path as GET in [ui/backend/routes/comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/routes/comparison_report.py:96), and the new regressions in [ui/backend/tests/test_comparison_report_route.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparison_report_route.py:184) cover both synthetic `OSError` cases.
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round4.md:733:APPROVED
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round4.md:735:No findings. The round-3 MED is closed: POST now maps `OSError` to the same `503` response path as GET in [ui/backend/routes/comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/routes/comparison_report.py:96), and the new regressions in [ui/backend/tests/test_comparison_report_route.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparison_report_route.py:184) cover both synthetic `OSError` cases.
reports/codex_tool_reports/dec_v61_087_v2_kogami_bootstrap_r1.md:5:**Round**: v2 R1 (max 3 per DEC self-imposed cap; v1 R1 produced CHANGES_REQUIRED)
reports/codex_tool_reports/dec_v61_087_v2_kogami_bootstrap_r1.md:18:`CHANGES_REQUIRED`
reports/codex_tool_reports/dec_v61_087_v2_kogami_bootstrap_r1.md:50:   The hard boundary now explicitly bans Kogami self-approval of its own agent prompt, brief script, invoke wrapper, trigger rules, and counter rules, and requires both user ratification and Codex APPROVE (`.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:459-463`). This is strict enough for the original v1 finding.
reports/codex_tool_reports/dec_v61_075_t2_3_post_commit_round3.md:3:- **Verdict**: CHANGES_REQUIRED
reports/codex_tool_reports/20260422_dec045_wave1_B_comparator_gates_prompt.md:9:      - reports/codex_tool_reports/20260422_dec036b_codex_review.md (CHANGES_REQUIRED, B3 finding)
reports/codex_tool_reports/dec_v61_087_v3_kogami_bootstrap_r2.md:5:**Round**: v3 R2 (max 3 per DEC self-imposed cap; v3 R1 was CHANGES_REQUIRED "worth an R2")
reports/codex_tool_reports/dec_v61_087_v3_kogami_bootstrap_r2.md:14:`APPROVE_WITH_COMMENTS`
reports/codex_tool_reports/dec_v61_087_v3_kogami_bootstrap_r2.md:74:`APPROVE_WITH_COMMENTS`。给绿灯进入 W0 implementation。
reports/codex_tool_reports/2026-04-28_m_viz_bundle_steps_3_to_6_codex_review_round5.md:65:P2 → P3) as the bundle stabilizes. Round 6 expectation: APPROVE or
reports/codex_tool_reports/dec_v61_075_t2_3_post_commit_round1.md:3:- **Verdict**: CHANGES_REQUIRED
reports/codex_tool_reports/20260422_dec038_codex_review.md:92:**Verdict**: APPROVE / APPROVE_WITH_NOTES / CHANGES_REQUIRED / BLOCK
reports/codex_tool_reports/20260422_dec038_codex_review.md:120:- Ready for codex_verdict=APPROVED: YES / NO
reports/codex_tool_reports/20260422_dec038_codex_review.md:388:Opus Gate: ⚠️ APPROVED WITH CONDITIONS (2026-04-13) — CFDJerry (T0 proxy)
reports/codex_tool_reports/20260422_dec038_codex_review.md:476:Opus Gate: ✅ APPROVED (2026-04-13) — 5/5 criteria, 10/10 tasks, 103 tests
reports/codex_tool_reports/20260422_dec038_codex_review.md:508:Opus Gate: ✅ APPROVED (2026-04-13)
reports/codex_tool_reports/20260422_dec038_codex_review.md:711:- **Concern code**: `VELOCITY_OVERFLOW`
reports/codex_tool_reports/20260422_dec038_codex_review.md:740:    concern_type: str   # VELOCITY_OVERFLOW / TURBULENCE_NEGATIVE / CONTINUITY_DIVERGED
reports/codex_tool_reports/20260422_dec038_codex_review.md:773:extends its G1 hard-FAIL concern set to include `VELOCITY_OVERFLOW`,
reports/codex_tool_reports/20260422_dec038_codex_review.md:803:- `test_validation_report_fails_on_gate_concern` — fixture with VELOCITY_OVERFLOW concern → contract_status FAIL
reports/codex_tool_reports/20260422_dec038_codex_review.md:854:- Status: COMPLETE (DEC-V61-031, 2026-04-21). 3 waves landed: adapter functions{} + executor capture + driver manifest; backend route/service/18 pytest; Codex 3 rounds → APPROVED_WITH_COMMENTS (2 HIGH security issues caught + fixed: URL basename collision + run_id path-traversal). Real LDC OpenFOAM integration produced 8 artifacts, HTTP manifest + subpath download + traversal 404 verified live. 97/97 pytest. v6.1 counter 16→17.
reports/codex_tool_reports/20260422_dec038_codex_review.md:879:- Status: **SPRINT 1 + SPRINT 2 TIER C COMPLETE** — DEC-V61-032 (LDC MVP) + DEC-V61-034 (Tier C visual-only fan-out to 9 cases, 2026-04-21). 8-section Jinja2 HTML template + WeasyPrint PDF + reduced visual-only context for non-LDC cases. Codex 4 + 2 rounds (both APPROVED). Tier B Sprint 2 (per-case gold-overlay for 9 cases) remains future work.
reports/codex_tool_reports/20260422_dec038_codex_review.md:917:- Status: **MVP COMPLETE (LDC)** — DEC-V61-032, 2026-04-21. `LearnCaseDetailPage.tsx::ScientificComparisonReportSection` fetches `/api/cases/{id}/runs/audit_real_run/comparison-report/context`, renders verdict card + metrics grid + iframe embed of HTML report + "Open in new window" + "Download PDF" buttons. Graceful 404→hide / 5xx→error banner distinction (Codex round 1 MED fix). iframe `sandbox=""` strict. Fan-out to 9 other cases deferred to 7c Sprint 2.
reports/codex_tool_reports/20260422_dec038_codex_review.md:1570:   430	        # A6 only fires when residuals are STUCK AT A HIGH PLATEAU — i.e.,
reports/codex_tool_reports/20260422_dec038_codex_review.md:2178:   250	    OR empty. Codex round 1 MED #3 (2026-04-21): require a NON-empty artifact
reports/codex_tool_reports/20260422_dec038_codex_review.md:3159:   563	    #   G3  VELOCITY_OVERFLOW           — |U|_max > 100·U_ref
reports/codex_tool_reports/20260422_dec038_codex_review.md:3169:   573	        "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec038_codex_review.md:3375:   297	                        concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec038_codex_review.md:3435:   357	        if _exceeds_threshold(f_max, G4_TURBULENCE_MAX_OVERFLOW):
reports/codex_tool_reports/20260422_dec038_codex_review.md:3442:   364	                        f"(> {G4_TURBULENCE_MAX_OVERFLOW:.0g})"
reports/codex_tool_reports/20260422_dec038_codex_review.md:3447:   369	                        f"{G4_TURBULENCE_MAX_OVERFLOW:.0g}. For realistic "
reports/codex_tool_reports/20260422_dec038_codex_review.md:3455:   377	                        "threshold": G4_TURBULENCE_MAX_OVERFLOW,
reports/codex_tool_reports/20260422_dec038_codex_review.md:3564:     4	  * G3 VELOCITY_OVERFLOW  — |U|_max > K * U_ref (K=100 default). VTK-based,
reports/codex_tool_reports/20260422_dec038_codex_review.md:3617:    57	G4_TURBULENCE_MAX_OVERFLOW = 1.0e10  # any k/eps/omega max above this = overflow
reports/codex_tool_reports/20260422_dec038_codex_review.md:3635:    75	    concern_type: str     # "VELOCITY_OVERFLOW" | "TURBULENCE_NEGATIVE" | "CONTINUITY_DIVERGED"
reports/codex_tool_reports/20260422_dec038_codex_review.md:3829:   269	                concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec038_codex_review.md:3908:.planning/STATE.md:354:| axisymmetric_impinging_jet | PASS_WITH_DEVIATIONS | UNKNOWN (FOAM FATAL) | PASS | adapter_version_mismatch (HIGH) |
reports/codex_tool_reports/20260422_dec038_codex_review.md:3911:.planning/STATE.md:1272:- DEC-038 attestor round 2: APPROVED_WITH_COMMENTS on `eb51dcf` (fixes + A2/G5 split-brain + ATTEST_NOT_APPLICABLE)
reports/codex_tool_reports/20260422_dec038_codex_review.md:4755:   529	    # Codex round 1 MED #3: only inject metadata for opted-in cases — other 9
reports/codex_tool_reports/20260422_dec038_codex_review.md:4774:   548	    # contents (best-effort, must not block audit doc). MED #3 gating above.
reports/codex_tool_reports/20260422_dec038_codex_review.md:5985:- **Ready for codex_verdict=APPROVED**: NO
reports/codex_tool_reports/20260422_dec038_codex_review.md:6038:- **Ready for codex_verdict=APPROVED**: NO
reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round2.md:3:- **Verdict**: CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round2.md:32:R3 introduced 2 new findings (P2 TaskRunner notes drop, P3 unsafe `hasattr`); R4 introduced 2 new (legacy path symmetry, Notion summary persistence); R5 APPROVE. Rolled into commit b2ea911.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:18:Round 2 verdict was CHANGES_REQUIRED with one remaining HIGH:
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:42:Please verify the round-2 HIGH is now closed and return APPROVED / APPROVED_WITH_COMMENTS / CHANGES_REQUIRED.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:44:If you see any new issue: call it out. Round-1 findings #1, #3, #4 and round-2 HIGH should all be closed; confirm or refute.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:224:+# Codex round 2 HIGH (2026-04-21): timestamp shape gate. The manifest is
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:240:+# Codex round 1 LOW #4 (2026-04-21): use st_mtime_ns (int) not st_mtime (float)
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:269:+    Codex round 2 HIGH (2026-04-21): previously the LIST endpoint read
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:322:+    # Codex round 1 HIGH #1 (2026-04-21): use POSIX relative path as filename
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:350:+    after Codex round 1 HIGH #1 fix. Traversal defense:
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:383:+    # Codex round 2 HIGH: both LIST and DOWNLOAD go through the shared
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:420:+    """VTK file lives at VTK/lid_driven_cavity_2000.vtk — subpath URL (Codex round 1 HIGH #1)."""
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:432:+    """Codex round 1 HIGH #2: traversal via run_id literal '..' must be rejected."""
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:438:+    """Codex round 1 HIGH #2: url-encoded '%2e%2e' traversal must also be rejected."""
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:444:+    """Codex round 1 HIGH #2: manifest endpoint also guards run_id segments."""
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:450:+    """Codex round 1 HIGH #1: filename field uses POSIX relative path so
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:460:+    """Codex round 2 HIGH: an adversary-written manifest with
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:524:    24	# Codex round 2 HIGH (2026-04-21): timestamp shape gate. The manifest is
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:559:    59	# Codex round 1 LOW #4 (2026-04-21): use st_mtime_ns (int) not st_mtime (float)
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:613:   113	    Codex round 2 HIGH (2026-04-21): previously the LIST endpoint read
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:664:   164	    # Codex round 1 HIGH #1 (2026-04-21): use POSIX relative path as filename
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:698:   198	    after Codex round 1 HIGH #1 fix. Traversal defense:
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:719:   219	    # Codex round 2 HIGH: both LIST and DOWNLOAD go through the shared
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:767:    26	_MEDIA_TYPES: dict[str, str] = {
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:779:    38	    return _MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream")
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:806:    65	    `sample/500/uCenterline.xy` (Codex round 1 HIGH #1 fix — 3 sample
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:834:    17	# Codex round 1 HIGH #2 (2026-04-21): traversal via run_id reproduced with
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:865:    48	    pattern to prevent path-traversal attacks (Codex round 1 HIGH #2).
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1164:ui/backend/services/field_artifacts.py:24:# Codex round 2 HIGH (2026-04-21): timestamp shape gate. The manifest is
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1327:./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3307:- HIGH: `GET /api/runs/{run_id}/field-artifacts` still trusts the manifest `timestamp` before walking and hashing files. In [field_artifacts.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/field_artifacts.py:109), `list_artifacts()` only checks that `timestamp` is non-empty, then builds `artifact_dir = root / case_id / timestamp` and recursively hashes classified files. The download path validates `timestamp` later, but the listing path does not. I reproduced this with a temp manifest using `timestamp="../../outside"`: listing returned an outside `residuals.csv` with size/hash, while download correctly returned `404`.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1328:./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3309:This is a round-1 miss / incomplete application of the round-1 HIGH #2 hardening, not a regression from the basename-collision fix. The fix should share the same validated artifact-dir resolver between `list_artifacts()` and `resolve_artifact_path()`, ideally enforcing the generated timestamp shape like `YYYYMMDDTHHMMSSZ`, and add a regression test for malicious manifest timestamps on the manifest endpoint.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1329:./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3325:- HIGH: `GET /api/runs/{run_id}/field-artifacts` still trusts the manifest `timestamp` before walking and hashing files. In [field_artifacts.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/field_artifacts.py:109), `list_artifacts()` only checks that `timestamp` is non-empty, then builds `artifact_dir = root / case_id / timestamp` and recursively hashes classified files. The download path validates `timestamp` later, but the listing path does not. I reproduced this with a temp manifest using `timestamp="../../outside"`: listing returned an outside `residuals.csv` with size/hash, while download correctly returned `404`.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1330:./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3327:This is a round-1 miss / incomplete application of the round-1 HIGH #2 hardening, not a regression from the basename-collision fix. The fix should share the same validated artifact-dir resolver between `list_artifacts()` and `resolve_artifact_path()`, ideally enforcing the generated timestamp shape like `YYYYMMDDTHHMMSSZ`, and add a regression test for malicious manifest timestamps on the manifest endpoint.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1386:+    `sample/500/uCenterline.xy` (Codex round 1 HIGH #1 fix — 3 sample
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1409:+# Codex round 1 HIGH #2 (2026-04-21): traversal via run_id reproduced with
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1439:+    pattern to prevent path-traversal attacks (Codex round 1 HIGH #2).
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1499:CHANGES_REQUIRED
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1501:1. HIGH — duplicate sample basenames make the manifest untruthful.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1504:2. HIGH — traversal defense does not cover `run_id`.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1507:3. MED — Phase 7a opt-in/failure fallback is broader than stated.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1510:4. LOW — SHA cache has a real stale-hash edge.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1518:CHANGES_REQUIRED
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1520:1. HIGH — duplicate sample basenames make the manifest untruthful.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1523:2. HIGH — traversal defense does not cover `run_id`.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1526:3. MED — Phase 7a opt-in/failure fallback is broader than stated.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1529:4. LOW — SHA cache has a real stale-hash edge.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1542:+    # Codex round 1 HIGH #2: also validate timestamp from manifest (an adversary
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1581:**Verdict: CHANGES_REQUIRED**
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1584:- HIGH: `GET /api/runs/{run_id}/field-artifacts` still trusts the manifest `timestamp` before walking and hashing files. In [field_artifacts.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/field_artifacts.py:109), `list_artifacts()` only checks that `timestamp` is non-empty, then builds `artifact_dir = root / case_id / timestamp` and recursively hashes classified files. The download path validates `timestamp` later, but the listing path does not. I reproduced this with a temp manifest using `timestamp="../../outside"`: listing returned an outside `residuals.csv` with size/hash, while download correctly returned `404`.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1586:This is a round-1 miss / incomplete application of the round-1 HIGH #2 hardening, not a regression from the basename-collision fix. The fix should share the same validated artifact-dir resolver between `list_artifacts()` and `resolve_artifact_path()`, ideally enforcing the generated timestamp shape like `YYYYMMDDTHHMMSSZ`, and add a regression test for malicious manifest timestamps on the manifest endpoint.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1599:**Verdict: CHANGES_REQUIRED**
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1602:- HIGH: `GET /api/runs/{run_id}/field-artifacts` still trusts the manifest `timestamp` before walking and hashing files. In [field_artifacts.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/field_artifacts.py:109), `list_artifacts()` only checks that `timestamp` is non-empty, then builds `artifact_dir = root / case_id / timestamp` and recursively hashes classified files. The download path validates `timestamp` later, but the listing path does not. I reproduced this with a temp manifest using `timestamp="../../outside"`: listing returned an outside `residuals.csv` with size/hash, while download correctly returned `404`.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1604:This is a round-1 miss / incomplete application of the round-1 HIGH #2 hardening, not a regression from the basename-collision fix. The fix should share the same validated artifact-dir resolver between `list_artifacts()` and `resolve_artifact_path()`, ideally enforcing the generated timestamp shape like `YYYYMMDDTHHMMSSZ`, and add a regression test for malicious manifest timestamps on the manifest endpoint.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1617:/bin/zsh -lc 'rg -n "''^(## |# |-|Findings|HIGH|MEDIUM|LOW|CHANGES_REQUIRED|APPROVED|Round|round|#1|#3|#4)" reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md | tail -n 120' in /Users/Zhuanz/Desktop/cfd-harness-unified
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1727:reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3307:- HIGH: `GET /api/runs/{run_id}/field-artifacts` still trusts the manifest `timestamp` before walking and hashing files. In [field_artifacts.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/field_artifacts.py:109), `list_artifacts()` only checks that `timestamp` is non-empty, then builds `artifact_dir = root / case_id / timestamp` and recursively hashes classified files. The download path validates `timestamp` later, but the listing path does not. I reproduced this with a temp manifest using `timestamp="../../outside"`: listing returned an outside `residuals.csv` with size/hash, while download correctly returned `404`.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1733:reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3325:- HIGH: `GET /api/runs/{run_id}/field-artifacts` still trusts the manifest `timestamp` before walking and hashing files. In [field_artifacts.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/field_artifacts.py:109), `list_artifacts()` only checks that `timestamp` is non-empty, then builds `artifact_dir = root / case_id / timestamp` and recursively hashes classified files. The download path validates `timestamp` later, but the listing path does not. I reproduced this with a temp manifest using `timestamp="../../outside"`: listing returned an outside `residuals.csv` with size/hash, while download correctly returned `404`.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1754:+    OR empty. Codex round 1 MED #3 (2026-04-21): require a NON-empty artifact
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1779:+# Codex round 1 MED #3 (2026-04-21): gate Phase 7a metadata injection to
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1792:+    # Codex round 1 MED #3: only inject metadata for opted-in cases — other 9
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1818:+    # contents (best-effort, must not block audit doc). MED #3 gating above.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:2074:   106	    OR empty. Codex round 1 MED #3 (2026-04-21): require a NON-empty artifact
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:2106:   138	# Codex round 1 MED #3 (2026-04-21): gate Phase 7a metadata injection to
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:2137:   278	    # Codex round 1 MED #3: only inject metadata for opted-in cases — other 9
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:2156:   297	    # contents (best-effort, must not block audit doc). MED #3 gating above.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:2295:   104	    """VTK file lives at VTK/lid_driven_cavity_2000.vtk — subpath URL (Codex round 1 HIGH #1)."""
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:2306:   115	    """Codex round 1 HIGH #2: traversal via run_id literal '..' must be rejected."""
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:2312:   121	    """Codex round 1 HIGH #2: url-encoded '%2e%2e' traversal must also be rejected."""
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:2318:   127	    """Codex round 1 HIGH #2: manifest endpoint also guards run_id segments."""
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:2324:   133	    """Codex round 1 HIGH #1: filename field uses POSIX relative path so
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:2334:   143	    """Codex round 2 HIGH: an adversary-written manifest with
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:2583:APPROVED_WITH_COMMENTS
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:2585:Round-2 HIGH is closed. `list_artifacts()` and `resolve_artifact_path()` now both go through `_resolve_artifact_dir()`, and the malicious `timestamp="../../outside"` case returns 404 for both list and download. The added regression is present and covered by the backend suite.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:2599:APPROVED_WITH_COMMENTS
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:2601:Round-2 HIGH is closed. `list_artifacts()` and `resolve_artifact_path()` now both go through `_resolve_artifact_dir()`, and the malicious `timestamp="../../outside"` case returns 404 for both list and download. The added regression is present and covered by the backend suite.
reports/codex_tool_reports/2026-04-28_m_panels_arc_codex_review_round3.md:10:`CHANGES_REQUIRED` — 1 P1, 1 WARNING, 0 P2.
reports/codex_tool_reports/2026-04-28_m_panels_arc_codex_review_round3.md:31:A signed audit package referencing an imported draft would mislead regulatory reviewers — no gold reference, no validation contract, no provenance (the original Codex PR-5d HIGH #1 reason for that gate).
reports/codex_tool_reports/2026-04-28_m_panels_arc_codex_review_round3.md:57:Codex-verified: CHANGES_REQUIRED
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:1642:src/convergence_attestor.py:821:        # A6 only fires when residuals are STUCK AT A HIGH PLATEAU — i.e.,
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:1752:**Verdict**: APPROVE / APPROVE_WITH_NOTES / CHANGES_REQUIRED / BLOCK
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:1780:- Ready for codex_verdict=APPROVED: YES / NO
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:1969:        # A6 only fires when residuals are STUCK AT A HIGH PLATEAU — i.e.,
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:2126:    #   G3  VELOCITY_OVERFLOW           — |U|_max > 100·U_ref
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:2137:        "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:2705:                concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:5661:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:6132:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:6534:        # A6 only fires when residuals are STUCK AT A HIGH PLATEAU — i.e.,
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:6588:    #   G3  VELOCITY_OVERFLOW           — |U|_max > 100·U_ref
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:6599:        "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:6794:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:7291:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:7785:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:8317:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:8900:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:9408:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:9989:1570:   430	        # A6 only fires when residuals are STUCK AT A HIGH PLATEAU — i.e.,
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:10112:3908:.planning/STATE.md:354:| axisymmetric_impinging_jet | PASS_WITH_DEVIATIONS | UNKNOWN (FOAM FATAL) | PASS | adapter_version_mismatch (HIGH) |
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:10115:3911-.planning/STATE.md:1272:- DEC-038 attestor round 2: APPROVED_WITH_COMMENTS on `eb51dcf` (fixes + A2/G5 split-brain + ATTEST_NOT_APPLICABLE)
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:10343:5985-- **Ready for codex_verdict=APPROVED**: NO
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:10390:6038-- **Ready for codex_verdict=APPROVED**: NO
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:10569:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:11082:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:11661:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:12181:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:12700:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:13238:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:13770:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:14332:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:14869:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:15406:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:15941:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:16473:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:17005:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:17581:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:18285:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:18817:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:19382:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:19922:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:20438:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:20948:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:21463:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:21973:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:22483:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:22993:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:23544:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave4_H_a6_promote_result.md:24096:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/dec_v61_074_t1b1_round1.md:3:- **Verdict**: CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_074_t1b1_round1.md:11:### 1. HIGH — `executor.contract_hash` is class-identity, not spec-derived
reports/codex_tool_reports/dec_v61_075_t2_3_post_commit_round4.md:3:- **Verdict**: CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round3.md:3:- **Verdict**: CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round3.md:30:R4 introduced 2 new findings (legacy-path symmetry + Notion summary persistence); R5 APPROVE. Rolled into commit b2ea911.
reports/codex_tool_reports/dec_v61_058_plan_review.md:21:| F1 | HIGH | §1 Classification | Rework the gate set so Type I is backed by 3 genuinely physical families, or explicitly downgrade before Stage A. | The draft itself says `Cp_at_xoc_0p5_upper` is from the same α=0 run as `Cd_at_alpha_zero` and `y_plus_max_on_aerofoil` is a wall-resolution probe, not a physics observable; that is not enough for a 3-family Type I claim. [intake](/Users/Zhuanz/Desktop/cfd-s2-naca/.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:53), [intake](/Users/Zhuanz/Desktop/cfd-s2-naca/.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:61), [intake](/Users/Zhuanz/Desktop/cfd-s2-naca/.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:66) |
reports/codex_tool_reports/dec_v61_058_plan_review.md:22:| F2 | HIGH | §4 Risk Flags / §7 Batch B1 | Lock α handling to one canonical `case_id` (`naca0012_airfoil`) with explicit `alpha_deg` routing and sign convention; remove the unresolved `_alpha_4/_alpha_8` whitelist-id branch unless verifier/report/case-profile routing is also expanded. | The intake leaves this unresolved, but current routing is keyed on the canonical case id. [intake](/Users/Zhuanz/Desktop/cfd-s2-naca/.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:168), [intake](/Users/Zhuanz/Desktop/cfd-s2-naca/.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:170), [intake](/Users/Zhuanz/Desktop/cfd-s2-naca/.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:413), [knowledge_db.py](/Users/Zhuanz/Desktop/cfd-s2-naca/src/knowledge_db.py:66), [config.py](/Users/Zhuanz/Desktop/cfd-s2-naca/src/auto_verifier/config.py:55) |
reports/codex_tool_reports/dec_v61_058_plan_review.md:23:| F3 | MED | §4 `wall_function_validity_at_re_3e6` | Correct the y+ derivation and stop using the current estimate as justification for family-counting or a hard 300 upper bound. | The text says `u_tau ≈ U_inf·sqrt(Cf/2)` but numerically evaluates it as `sqrt(0.004)`; that overstates `y+_min`. [intake](/Users/Zhuanz/Desktop/cfd-s2-naca/.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:217), [intake](/Users/Zhuanz/Desktop/cfd-s2-naca/.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:218) |
reports/codex_tool_reports/dec_v61_058_plan_review.md:24:| F4 | MED | §2 References / Batch A | Replace broad source labels with exact source conditions: paper + table/figure + Mach + transition state + α row. Also repair the current gold provenance mismatch in Batch A. | The intake cites Ladson/Abbott/Gregory broadly, while the current gold still carries uncertain `Thomas 1979 / Lada & Gostling 2007` provenance. [intake](/Users/Zhuanz/Desktop/cfd-s2-naca/.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:94), [intake](/Users/Zhuanz/Desktop/cfd-s2-naca/.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:99), [intake](/Users/Zhuanz/Desktop/cfd-s2-naca/.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:399), [naca0012_airfoil.yaml](/Users/Zhuanz/Desktop/cfd-s2-naca/knowledge/gold_standards/naca0012_airfoil.yaml:3) |
reports/codex_tool_reports/dec_v61_058_plan_review.md:25:| F5 | MED | §7 Batch B3 | Keep `y_plus_max_on_aerofoil` advisory/measured in v2; do not pre-commit it to `HARD_GATED [11,300]` while the same intake also argues `[11,500] PROVISIONAL`. | Internal conflict between risk-flag mitigation and Batch B3 scope. [intake](/Users/Zhuanz/Desktop/cfd-s2-naca/.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:225), [intake](/Users/Zhuanz/Desktop/cfd-s2-naca/.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:430) |
reports/codex_tool_reports/dec_v61_058_plan_review.md:26:| F6 | MED | §9 Stage E | Add close conditions for CaseProfile update, canonical α routing proof, and sign-convention smoke assertions (`α=+8° -> Cl>0`, `α=0° -> |Cl|` sanity bound). | The intake itself says the CaseProfile needs updating, but the close checklist does not require it. [intake](/Users/Zhuanz/Desktop/cfd-s2-naca/.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:149), [intake](/Users/Zhuanz/Desktop/cfd-s2-naca/.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:464), [case_profile](/Users/Zhuanz/Desktop/cfd-s2-naca/.planning/case_profiles/naca0012_airfoil.yaml:12) |
reports/codex_tool_reports/dec_v61_058_plan_review.md:53:`Q8.` Verdict: `(a) `0.30` is optimistic for v1`, `(b) `2 HIGH + 2 MED + 2 LOW` understates the medium findings.` My round-1 expectation for v1 is closer to `2 HIGH + 3-4 MED + 0-1 LOW`: Type-I family failure, α-routing architecture, y+ math/family misuse, source specificity, and close-condition gaps.
reports/codex_tool_reports/dec_v61_058_plan_review.md:70:| F1 | HIGH | §1 Classification | Rework the gate set so Type I is backed by 3 genuinely physical families, or explicitly downgrade before Stage A. | The draft itself says `Cp_at_xoc_0p5_upper` is from the same α=0 run as `Cd_at_alpha_zero` and `y_plus_max_on_aerofoil` is a wall-resolution probe, not a physics observable; that is not enough for a 3-family Type I claim. [intake](/Users/Zhuanz/Desktop/cfd-s2-naca/.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:53), [intake](/Users/Zhuanz/Desktop/cfd-s2-naca/.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:61), [intake](/Users/Zhuanz/Desktop/cfd-s2-naca/.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:66) |
reports/codex_tool_reports/dec_v61_058_plan_review.md:71:| F2 | HIGH | §4 Risk Flags / §7 Batch B1 | Lock α handling to one canonical `case_id` (`naca0012_airfoil`) with explicit `alpha_deg` routing and sign convention; remove the unresolved `_alpha_4/_alpha_8` whitelist-id branch unless verifier/report/case-profile routing is also expanded. | The intake leaves this unresolved, but current routing is keyed on the canonical case id. [intake](/Users/Zhuanz/Desktop/cfd-s2-naca/.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:168), [intake](/Users/Zhuanz/Desktop/cfd-s2-naca/.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:170), [intake](/Users/Zhuanz/Desktop/cfd-s2-naca/.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:413), [knowledge_db.py](/Users/Zhuanz/Desktop/cfd-s2-naca/src/knowledge_db.py:66), [config.py](/Users/Zhuanz/Desktop/cfd-s2-naca/src/auto_verifier/config.py:55) |
reports/codex_tool_reports/dec_v61_058_plan_review.md:72:| F3 | MED | §4 `wall_function_validity_at_re_3e6` | Correct the y+ derivation and stop using the current estimate as justification for family-counting or a hard 300 upper bound. | The text says `u_tau ≈ U_inf·sqrt(Cf/2)` but numerically evaluates it as `sqrt(0.004)`; that overstates `y+_min`. [intake](/Users/Zhuanz/Desktop/cfd-s2-naca/.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:217), [intake](/Users/Zhuanz/Desktop/cfd-s2-naca/.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:218) |
reports/codex_tool_reports/dec_v61_058_plan_review.md:73:| F4 | MED | §2 References / Batch A | Replace broad source labels with exact source conditions: paper + table/figure + Mach + transition state + α row. Also repair the current gold provenance mismatch in Batch A. | The intake cites Ladson/Abbott/Gregory broadly, while the current gold still carries uncertain `Thomas 1979 / Lada & Gostling 2007` provenance. [intake](/Users/Zhuanz/Desktop/cfd-s2-naca/.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:94), [intake](/Users/Zhuanz/Desktop/cfd-s2-naca/.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:99), [intake](/Users/Zhuanz/Desktop/cfd-s2-naca/.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:399), [naca0012_airfoil.yaml](/Users/Zhuanz/Desktop/cfd-s2-naca/knowledge/gold_standards/naca0012_airfoil.yaml:3) |
reports/codex_tool_reports/dec_v61_058_plan_review.md:74:| F5 | MED | §7 Batch B3 | Keep `y_plus_max_on_aerofoil` advisory/measured in v2; do not pre-commit it to `HARD_GATED [11,300]` while the same intake also argues `[11,500] PROVISIONAL`. | Internal conflict between risk-flag mitigation and Batch B3 scope. [intake](/Users/Zhuanz/Desktop/cfd-s2-naca/.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:225), [intake](/Users/Zhuanz/Desktop/cfd-s2-naca/.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:430) |
reports/codex_tool_reports/dec_v61_058_plan_review.md:75:| F6 | MED | §9 Stage E | Add close conditions for CaseProfile update, canonical α routing proof, and sign-convention smoke assertions (`α=+8° -> Cl>0`, `α=0° -> |Cl|` sanity bound). | The intake itself says the CaseProfile needs updating, but the close checklist does not require it. [intake](/Users/Zhuanz/Desktop/cfd-s2-naca/.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:149), [intake](/Users/Zhuanz/Desktop/cfd-s2-naca/.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:464), [case_profile](/Users/Zhuanz/Desktop/cfd-s2-naca/.planning/case_profiles/naca0012_airfoil.yaml:12) |
reports/codex_tool_reports/dec_v61_058_plan_review.md:102:`Q8.` Verdict: `(a) `0.30` is optimistic for v1`, `(b) `2 HIGH + 2 MED + 2 LOW` understates the medium findings.` My round-1 expectation for v1 is closer to `2 HIGH + 3-4 MED + 0-1 LOW`: Type-I family failure, α-routing architecture, y+ math/family misuse, source specificity, and close-condition gaps.
reports/codex_tool_reports/20260422_dec045_wave3_G_tests_result.md:2831:    OR empty. Codex round 1 MED #3 (2026-04-21): require a NON-empty artifact
reports/codex_tool_reports/20260422_dec045_wave3_G_tests_result.md:4488:    #   G3  VELOCITY_OVERFLOW           — |U|_max > 100·U_ref
reports/codex_tool_reports/20260422_dec045_wave3_G_tests_result.md:4499:        "VELOCITY_OVERFLOW",
reports/codex_tool_reports/2026-04-28_m_panels_arc_codex_review_round1.md:11:`CHANGES_REQUIRED` — 2 P2 findings, 0 P1, 0 P3.
reports/codex_tool_reports/dec_v61_099_round1.md:16:Pre-merge Codex review for DEC-V61-099 (post-R3 live-run defect closure on V61-097 R1 HIGH-2 staging order regression).
reports/codex_tool_reports/dec_v61_099_round1.md:35:Return verdict in standard format: APPROVE / CHANGES_REQUIRED with severity-classified findings (HIGH/MED/LOW). Reference reports/codex_tool_reports/dec_v61_097_phase_1a_round*.md for verdict format.
reports/codex_tool_reports/dec_v61_099_round1.md:50:ui/backend/tests/test_solver_streamer.py:257:    after V61-097 R4 RESOLVED). The V61-097 round-1 HIGH-2 fix introduced
reports/codex_tool_reports/dec_v61_099_round1.md:67:ui/backend/services/case_solve/solver_streamer.py:278:        # Codex round-1 HIGH-2: container_work_dir is now run_id-suffixed
reports/codex_tool_reports/dec_v61_099_round1.md:81:reports/codex_tool_reports/dec_v61_097_phase_1a_round1.md:1:# Codex pre-merge review · DEC-V61-097 Phase-1A · Round 1
reports/codex_tool_reports/dec_v61_099_round1.md:82:reports/codex_tool_reports/dec_v61_097_phase_1a_round1.md:16:`stream_icofoam()` is a generator, so the failure-mapping code at lines 170-243 only executes when `StreamingResponse` begins iterating. Container down / Docker SDK broken / staging failure produces a started SSE response and then an iterator exception or broken stream, not the structured HTTP rejection the route comment promises.
reports/codex_tool_reports/dec_v61_099_round1.md:83:reports/codex_tool_reports/dec_v61_097_phase_1a_round1.md:20:### 2. HIGH — abort/restart race: no run-generation guard, shared container_work_dir
reports/codex_tool_reports/dec_v61_099_round1.md:84:reports/codex_tool_reports/dec_v61_097_phase_1a_round1.md:23:Frontend "abort" only aborts the fetch reader; it does not stop the solver. Backend always uses the same `container_work_dir` derived from `case_host_dir.name`. Failure mode: navigate-away/remount can leave run A alive, run B starts in same directory, both race on `log.icoFoam` + time dirs + pulled-back artifacts. Frontend has no run-generation guard, so stale `done`/`error` from older invocation can mutate state after a newer `start()`.
reports/codex_tool_reports/dec_v61_099_round1.md:85:reports/codex_tool_reports/dec_v61_097_phase_1a_round1.md:25:**Verbatim fix**: Introduce a per-case solve lock or server-issued `run_id`; reject concurrent `solve-stream` with `409 solve_already_running`, use `container_work_dir = f'{CONTAINER_WORK_BASE}/{case_host_dir.name}-{run_id}'`, and gate all frontend state writes on `if (runIdRef.current !== localRunId) return`.
reports/codex_tool_reports/dec_v61_099_round1.md:86:reports/codex_tool_reports/dec_v61_097_phase_1a_round4.md:1:# Codex pre-merge review · DEC-V61-097 Phase-1A · Round 4 (closure)
reports/codex_tool_reports/dec_v61_099_round1.md:87:reports/codex_tool_reports/dec_v61_097_phase_1a_round4.md:19:The DEC-V61-097 Phase-1A LDC end-to-end demo arc went through 4 Codex rounds before closure:
reports/codex_tool_reports/dec_v61_099_round1.md:88:reports/codex_tool_reports/dec_v61_097_phase_1a_round4.md:43:DEC-V61-097 self-estimated 55% pre-Codex. Actual: needed 4 rounds before APPROVE/RESOLVED. Calibration drift = -55% (4 rounds vs. predicted ≤2). Logging in next retrospective per the methodology.
reports/codex_tool_reports/dec_v61_099_round1.md:89:reports/codex_tool_reports/dec_v61_097_phase_1a_round2.md:1:# Codex pre-merge review · DEC-V61-097 Phase-1A · Round 2
reports/codex_tool_reports/dec_v61_099_round1.md:100:reports/codex_tool_reports/dec_v61_097_phase_1a_round3.md:1:# Codex pre-merge review · DEC-V61-097 Phase-1A · Round 3
reports/codex_tool_reports/dec_v61_099_round1.md:105:reports/codex_tool_reports/dec_v61_099_round1.md:16:Pre-merge Codex review for DEC-V61-099 (post-R3 live-run defect closure on V61-097 R1 HIGH-2 staging order regression).
reports/codex_tool_reports/dec_v61_099_round1.md:155:.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:3:title: M-PANELS Phase-1A · post-R3 live-run defect closure — solver_streamer staging order regression (V61-097 R1 HIGH-2 interaction)
reports/codex_tool_reports/dec_v61_099_round1.md:164:.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:66:that corrects the staging order introduced in V61-097 round 1 HIGH-2
reports/codex_tool_reports/dec_v61_099_round1.md:167:.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:74:V61-097 round 1 HIGH-2 fix made `container_work_dir` run_id-suffixed
reports/codex_tool_reports/dec_v61_099_round1.md:174:.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md:104:run-generation guard, shared `container_work_dir`" as HIGH-2.
reports/codex_tool_reports/dec_v61_099_round1.md:214:.planning/reviews/kogami/blind_control_v61_087_v1_2026-04-27/review.json:1:{"verdict":"APPROVE_WITH_COMMENTS","summary":"DEC-V61-087 v3 is a substantive, well-reasoned governance evolution that correctly addresses the v1/v2 failure modes identified by Codex and grounds its isolation contract in empirically verified flag behavior. The decision-arc coherence with RETRO-V61-001 (counter rules), Pivot Charter §4.7 (CLASS framework), and DEC-V61-073 (sampling audit/anti-drift) is strong, and the honest residual-risk enumeration in §3.5 plus the Tier-2 escalation triggers in §3.6 make this a falsifiable governance contract rather than a self-congratulatory one. Findings below are P1/P2 — none block ratification, but two should be addressed before W1 implementation begins.","findings":[{"severity":"P1","title":"Q1 canary verification method underspecified for the actual leak vector","problem":"§Open Questions Q1 (in v1 form) was the dominant unknown that v3 claims to have resolved via `--tools \"\"`. But the W0 dry-run described in `empirical_probes_completed` and the `Q1 canary regression test (monthly cron)` referenced in §3.6 and kogami_triggers.md §Tier 1 → Tier 2 are not specified concretely in the DEC itself. Specifically: (a) what canary token(s) are seeded into which input channels (cwd files? memory_paths target? env?), (b) what constitutes a 'leak' for sampling purposes (substring? embedding similarity? metadata-only?), (c) what is the sample-size n for monthly cron and how does it interact with the §3.5(3) `--tools \"\"` semantic-change risk acceptance. Without this specified in the DEC, the load-bearing 'physical capability removal' claim depends on an unspecified test, and Tier-2 escalation triggers can't be evaluated.","position":"§3.6 + Acceptance Criteria Q1 evidence","recommendation":"Add a §3.7 'Q1 canary specification' subsection (or expand AC item Q1) listing: (a) ≥3 distinct canary tokens placed in (i) project CLAUDE.md content, (ii) memory_paths.auto target file, (iii) env var; (b) leak definition = exact-substring match of any canary in subprocess `.result`; (c) n=5 runs per month minimum, all 5 must show 0 hits; (d) re-run mandatory on any `claude` CLI version change. Reference this section from §3.6 and from kogami_triggers.md Tier-2 list."},{"severity":"P1","title":"§4.4 paraphrase-laundering residual risk lacks a closure metric","problem":"§4.4 honestly acknowledges that regex blacklist + structured YAML can be defeated by paraphrase ('prior review identified a blocker'). The mitigation is described as 'sampling audit on accumulated review history can detect systematic paraphrase pattern' and Tier-2 escalation 'can include' ≥3 paraphrase instances. But (a) no concrete sampling cadence is specified (interval? sample size?), (b) the trigger uses 'can include' (advisory) rather than a binding count, (c) no owner is assigned. This is the same anti-pattern §10.5 was created to fix for §10 治理降级 — a falsifiability hole in an advisory rule. Without a concrete sampling rule, the §4.4 'improved, not closed' position drifts toward 'closed by hope'.","position":"§4.4 Honest residual risk paragraph + kogami_triggers.md §Strategic package authoring","recommendation":"Bind paraphrase-laundering audit to the existing §10.5 sampling-audit infrastructure: every Nth Kogami review (e.g., N=10) is sampled by the human reviewer (CFDJerry or external Opus session) for paraphrase patterns in author-supplied `rationale` fields. ≥3 confirmed paraphrase instances within a 30-review window → Tier-2 escalation MANDATORY (not advisory). Record cadence in §4.4 + cross-link from kogami_counter_rules.md §5.5."},{"severity":"P2","title":"Hard Boundary anti-self-approval rule has a recursion gap","problem":"kogami_triggers.md §Hard Boundary lists 7 files (P-1 through P-5 plus this file and kogami_counter_rules.md) that Kogami cannot self-approve. But DEC-V61-087 itself is the governance contract that establishes this boundary. A future DEC modifying DEC-V61-087's §3 (isolation contract) is not explicitly listed in the Hard Boundary file paths — only the implementation artifacts are. A clever framing ('we're not modifying P-1, just amending DEC-V61-087 §3 to relax which flags are required') could route around the rule. The DEC §4.2 'must NOT trigger' list mentions 'Kogami's own P-1/.../P-5 modifications' but not 'modifications to DEC-V61-087 itself or successor DECs that re-architect Kogami'.","position":"§4.2 must-NOT trigger list, last bullet · kogami_triggers.md §Hard Boundary file list","recommendation":"Extend the Hard Boundary to include 'any DEC whose `parent_dec` includes DEC-V61-087 OR whose subject is the Kogami isolation contract / counter rules / trigger rules'. Update both the DEC §4.2 enumeration and kogami_triggers.md §Hard Boundary. This closes the meta-recursion: Kogami v3.1 / v4 cannot self-approve its own governance evolution."},{"severity":"P2","title":"Counter provenance logic conflates Interpretation A and B without a binding tiebreaker","problem":"`autonomous_governance_counter_v61_provenance` says 'Interpretation B (STATE.md = SSOT, established by V61-086 provenance precedent), this DEC advances 52 → 53. Strict-bookkeeping Interpretation A would also yield 53 in this case (no intermediate silent advances since V61-075), so both interpretations agree here.' This is fine for V61-087 specifically but defers the actual choice. If a future DEC has divergent A/B values, there is no binding rule. RETRO-V61-001 says counter is pure telemetry, but provenance disputes are still live (V61-080/081/082/FORENSIC-FLAKE silent advances per STATE.md last_updated). Kogami's counter rules document (§5.6 Q4 dry-run) verifies historical compatibility but doesn't codify which interpretation is canonical going forward.","position":"frontmatter `autonomous_governance_counter_v61_provenance` + kogami_counter_rules.md §5.6","recommendation":"Either (a) add a one-line ratification in §5 of DEC-V61-087: 'Interpretation B (STATE.md last_updated = SSOT) is canonical going forward per V61-086 precedent', OR (b) open a follow-up DEC explicitly choosing. Without canonicalization, any future arc with intermediate silent advances will re-litigate. Low-cost fix; high value for future audit clarity."},{"severity":"P3","title":"Process Note's GSD-bypass justification is sound but creates a precedent worth flagging","problem":"§Process Note explains why this DEC didn't go through `/gsd-discuss-phase` (project's main-line is workbench-closed-loop M1-M4 COMPLETE; no governance phase exists in ROADMAP.md). The reasoning is correct. But this is the second governance-class artifact bypass in a row (DEC-V61-073 sampling audit was similar; ADR-002 W2 G-9 was similar per RETRO-V61-005). A pattern is forming where governance evolution lives outside the GSD phase model. This isn't wrong, but it's worth surfacing as a meta-question for the next arc-size retro.","position":"§Process Note","recommendation":"Add one sentence: 'If governance-class DECs continue to accumulate outside the GSD phase model (DEC-V61-073, ADR-002, this DEC), open a follow-up retro at counter ≥ 60 to evaluate whether ROADMAP.md should add a standing 'governance' phase or whether the current pattern is deliberate.' No action needed for V61-087 itself."}],"strategic_assessment":"Decision-arc coherence: STRONG. v3 directly consumes the v1/v2 Codex failures (prompt-contract not enforceable → process boundary still leaky → physical capability removal via `--tools \"\"`), with each failure mode acknowledged honestly in §Why. The W0 empirical fixes (cwd switch, stdin prompt) show real iteration, not paper-over. Compatibility with RETRO-V61-001 counter rules verified via Q4 dry-run; compatibility with DEC-V61-073 §10.5 sampling audit infrastructure is implicit (kogami_triggers.md Tier-2 list mentions Q5 keyword sampling but doesn't formally bind to §10.5). Roadmap fit: NEUTRAL-TO-POSITIVE. Workbench main-line M1-M4 is COMPLETE per ROADMAP.md, so this governance work doesn't compete with user-facing delivery. The ~1030 LOC estimate (mostly docs) is proportionate; the W0/W1/W2/W3/W4 staging with explicit user-ACK gates between waves is consistent with §10.4 Line-A/B isolation discipline. Retrospective completeness: STRONG. §3.5 enumerates 6 honest residual risks; §3.6 specifies Tier-2 escalation triggers; §Risks table covers 7 distinct failure modes with mitigations. Out-of-scope hygiene: STRONG. §Out of Scope explicitly lists 8 items including the recursion guard (Kogami doesn't review its own reviews) and the counter non-inflation invariant. The Hard Boundary in kogami_triggers.md correctly anticipates anti-self-approval but has a recursion gap (Finding P2 above). Risk-vs-benefit framing: SOUND. Notion-Opus replacement value (faster turnaround, tool access, automatic provenance) is real; the cost (loss of cross-model independence) is honestly acknowledged as 'Codex stays for code-layer; Kogami covers strategic-layer with same-model-but-different-process'. The Tier-1 → Tier-2 escalation path means this is a reversible, falsifiable bet rather than a one-way door.","recommended_next":"merge"}
reports/codex_tool_reports/bug1_sse_disconnect_persistence_r1.md:1:verdict: CHANGES_REQUIRED
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md:938:  (CHANGES_REQUIRED, 3 blockers + 2 nits) and DEC-038 (BLOCK, 5 blockers
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md:977:### DEC-V61-036b (CHANGES_REQUIRED)
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md:1080:5. **Self-pass 0.50 realistic**: with 8 tracks and 4 waves, expect ≥1 Codex CHANGES_REQUIRED round before final APPROVE.
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md:1103:**Related**: DEC-V61-036b (CHANGES_REQUIRED), DEC-V61-038 (BLOCK)
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md:1239:_BFS_BLOWUP_TAIL = """\
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md:1265:    log = _write_log(tmp_path, _BFS_BLOWUP_TAIL)
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md:1287:    log = _write_log(tmp_path, _BFS_BLOWUP_TAIL)
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md:1320:    log = _write_log(tmp_path, _BFS_BLOWUP_TAIL)
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md:1356:    log = _write_log(tmp_path, _BFS_BLOWUP_TAIL)
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md:1360:    assert g3[0].concern_type == "VELOCITY_OVERFLOW"
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md:1426:    """Fixture with VELOCITY_OVERFLOW concern must hard-FAIL the verdict."""
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md:1450:            concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md:1457:    # DEC-V61-036b: VELOCITY_OVERFLOW overrides a "within band" comparator PASS.
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md:1489:      - reports/codex_tool_reports/20260422_dec036b_codex_review.md (CHANGES_REQUIRED, B3 finding)
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md:1669:  (CHANGES_REQUIRED, 3 blockers + 2 nits) and DEC-038 (BLOCK, 5 blockers
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md:1920:  * G3 VELOCITY_OVERFLOW  — |U|_max > K * U_ref (K=100 default). VTK-based,
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md:1973:G4_TURBULENCE_MAX_OVERFLOW = 1.0e10  # any k/eps/omega max above this = overflow
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md:1991:    concern_type: str     # "VELOCITY_OVERFLOW" | "TURBULENCE_NEGATIVE" | "CONTINUITY_DIVERGED"
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md:2462:                concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md:2490:                        concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md:2550:        if _exceeds_threshold(f_max, G4_TURBULENCE_MAX_OVERFLOW):
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md:2557:                        f"(> {G4_TURBULENCE_MAX_OVERFLOW:.0g})"
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md:2562:                        f"{G4_TURBULENCE_MAX_OVERFLOW:.0g}. For realistic "
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md:2570:                        "threshold": G4_TURBULENCE_MAX_OVERFLOW,
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md:3192:        # A6 only fires when residuals are STUCK AT A HIGH PLATEAU — i.e.,
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md:5442:    40	_BFS_BLOWUP_TAIL = """\
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md:5492:    90	    log = _write_log(tmp_path, _BFS_BLOWUP_TAIL)
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md:5514:   112	    log = _write_log(tmp_path, _BFS_BLOWUP_TAIL)
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md:5547:   145	    log = _write_log(tmp_path, _BFS_BLOWUP_TAIL)
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md:5583:   181	    log = _write_log(tmp_path, _BFS_BLOWUP_TAIL)
reports/codex_tool_reports/20260422_dec045_wave1_C_tests_result.md:5587:   185	    assert g3[0].concern_type == "VELOCITY_OVERFLOW"
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:16:Phase 7a field-artifacts capture — Round 2 verification after CHANGES_REQUIRED round 1.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:18:Round 1 verdict was CHANGES_REQUIRED with 4 findings (2 HIGH, 1 MED, 1 LOW). All 4 have been addressed in the uncommitted working tree. Please re-review and confirm APPROVED / APPROVED_WITH_COMMENTS / CHANGES_REQUIRED.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:22:FINDING 1 HIGH (URL basename collision) — FIXED:
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:29:FINDING 2 HIGH (traversal via run_id) — FIXED:
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:35:FINDING 3 MED (Phase 7a metadata over-applied) — FIXED:
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:40:FINDING 4 LOW (SHA cache uses float st_mtime) — FIXED:
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:804:Opus Gate: ⚠️ APPROVED WITH CONDITIONS (2026-04-13) — CFDJerry (T0 proxy)
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:892:Opus Gate: ✅ APPROVED (2026-04-13) — 5/5 criteria, 10/10 tasks, 103 tests
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:924:Opus Gate: ✅ APPROVED (2026-04-13)
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1229:ui/backend/services/run_ids.py:17:# Codex round 1 HIGH #2 (2026-04-21): traversal via run_id reproduced with
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1285:ui/backend/tests/test_field_artifacts_route.py:115:    """Codex round 1 HIGH #2: traversal via run_id literal '..' must be rejected."""
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1286:ui/backend/tests/test_field_artifacts_route.py:127:    """Codex round 1 HIGH #2: manifest endpoint also guards run_id segments."""
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1389:+    `sample/500/uCenterline.xy` (Codex round 1 HIGH #1 fix — 3 sample
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1407:+# Codex round 1 LOW #4 (2026-04-21): use st_mtime_ns (int) not st_mtime (float)
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1430:+    # Codex round 1 HIGH #1 (2026-04-21): use POSIX relative path as filename
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1459:+    after Codex round 1 HIGH #1 fix. Traversal defense:
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1487:+    # Codex round 1 HIGH #2: also validate timestamp from manifest (an adversary
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1540:+# Codex round 1 HIGH #2 (2026-04-21): traversal via run_id reproduced with
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1570:+    pattern to prevent path-traversal attacks (Codex round 1 HIGH #2).
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1591:+    """VTK file lives at VTK/lid_driven_cavity_2000.vtk — subpath URL (Codex round 1 HIGH #1)."""
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1603:+    """Codex round 1 HIGH #2: traversal via run_id literal '..' must be rejected."""
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1609:+    """Codex round 1 HIGH #2: url-encoded '%2e%2e' traversal must also be rejected."""
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1615:+    """Codex round 1 HIGH #2: manifest endpoint also guards run_id segments."""
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1621:+    """Codex round 1 HIGH #1: filename field uses POSIX relative path so
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1648:+    OR empty. Codex round 1 MED #3 (2026-04-21): require a NON-empty artifact
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1673:+# Codex round 1 MED #3 (2026-04-21): gate Phase 7a metadata injection to
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1686:+    # Codex round 1 MED #3: only inject metadata for opted-in cases — other 9
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1712:+    # contents (best-effort, must not block audit doc). MED #3 gating above.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1840:    26	_MEDIA_TYPES: dict[str, str] = {
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1852:    38	    return _MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream")
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1879:    65	    `sample/500/uCenterline.xy` (Codex round 1 HIGH #1 fix — 3 sample
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1942:    52	# Codex round 1 LOW #4 (2026-04-21): use st_mtime_ns (int) not st_mtime (float)
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:2009:   119	    # Codex round 1 HIGH #1 (2026-04-21): use POSIX relative path as filename
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:2044:   154	    after Codex round 1 HIGH #1 fix. Traversal defense:
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:2071:   181	    # Codex round 1 HIGH #2: also validate timestamp from manifest (an adversary
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:2202:   104	    """VTK file lives at VTK/lid_driven_cavity_2000.vtk — subpath URL (Codex round 1 HIGH #1)."""
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:2213:   115	    """Codex round 1 HIGH #2: traversal via run_id literal '..' must be rejected."""
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:2219:   121	    """Codex round 1 HIGH #2: url-encoded '%2e%2e' traversal must also be rejected."""
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:2225:   127	    """Codex round 1 HIGH #2: manifest endpoint also guards run_id segments."""
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:2231:   133	    """Codex round 1 HIGH #1: filename field uses POSIX relative path so
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:2273:   106	    OR empty. Codex round 1 MED #3 (2026-04-21): require a NON-empty artifact
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:2305:   138	# Codex round 1 MED #3 (2026-04-21): gate Phase 7a metadata injection to
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:2445:   278	    # Codex round 1 MED #3: only inject metadata for opted-in cases — other 9
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:2464:   297	    # contents (best-effort, must not block audit doc). MED #3 gating above.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:2528:    17	# Codex round 1 HIGH #2 (2026-04-21): traversal via run_id reproduced with
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:2559:    48	    pattern to prevent path-traversal attacks (Codex round 1 HIGH #2).
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3185:+# Codex round 1 LOW #4 (2026-04-21): use st_mtime_ns (int) not st_mtime (float)
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3208:+    # Codex round 1 HIGH #1 (2026-04-21): use POSIX relative path as filename
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3237:+    after Codex round 1 HIGH #1 fix. Traversal defense:
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3265:+    # Codex round 1 HIGH #2: also validate timestamp from manifest (an adversary
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3304:**Verdict: CHANGES_REQUIRED**
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3307:- HIGH: `GET /api/runs/{run_id}/field-artifacts` still trusts the manifest `timestamp` before walking and hashing files. In [field_artifacts.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/field_artifacts.py:109), `list_artifacts()` only checks that `timestamp` is non-empty, then builds `artifact_dir = root / case_id / timestamp` and recursively hashes classified files. The download path validates `timestamp` later, but the listing path does not. I reproduced this with a temp manifest using `timestamp="../../outside"`: listing returned an outside `residuals.csv` with size/hash, while download correctly returned `404`.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3309:This is a round-1 miss / incomplete application of the round-1 HIGH #2 hardening, not a regression from the basename-collision fix. The fix should share the same validated artifact-dir resolver between `list_artifacts()` and `resolve_artifact_path()`, ideally enforcing the generated timestamp shape like `YYYYMMDDTHHMMSSZ`, and add a regression test for malicious manifest timestamps on the manifest endpoint.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3322:**Verdict: CHANGES_REQUIRED**
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3325:- HIGH: `GET /api/runs/{run_id}/field-artifacts` still trusts the manifest `timestamp` before walking and hashing files. In [field_artifacts.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/field_artifacts.py:109), `list_artifacts()` only checks that `timestamp` is non-empty, then builds `artifact_dir = root / case_id / timestamp` and recursively hashes classified files. The download path validates `timestamp` later, but the listing path does not. I reproduced this with a temp manifest using `timestamp="../../outside"`: listing returned an outside `residuals.csv` with size/hash, while download correctly returned `404`.
reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:3327:This is a round-1 miss / incomplete application of the round-1 HIGH #2 hardening, not a regression from the basename-collision fix. The fix should share the same validated artifact-dir resolver between `list_artifacts()` and `resolve_artifact_path()`, ideally enforcing the generated timestamp shape like `YYYYMMDDTHHMMSSZ`, and add a regression test for malicious manifest timestamps on the manifest endpoint.
reports/codex_tool_reports/2026-04-28_m_viz_bundle_steps_3_to_6_codex_review_round3.md:99:implementation DEC after Codex APPROVE.
reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round4.md:3:- **Verdict**: CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round4.md:30:R5 APPROVE. Bundle landed at commit b2ea911.
reports/codex_tool_reports/dec_v61_058_round1_review.md:5:**Verdict:** `CHANGES_REQUIRED`
reports/codex_tool_reports/dec_v61_058_round1_review.md:45:1. **Verdict**: APPROVE / APPROVE_WITH_COMMENTS / CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_058_round1_review.md:49:5. **Blocking vs non-blocking findings** (CHANGES_REQUIRED needs ≥1 blocking)
reports/codex_tool_reports/dec_v61_074_t1b23_postcommit_round2.md:3:- **Verdict**: APPROVE_WITH_COMMENTS · 0 blocking findings (R1's 3 defects all closed)
reports/codex_tool_reports/2026-04-21_pr22_duct_dispatch_review.md:3:Verdict: `CHANGES_REQUIRED`
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round1.md:84:Reply APPROVED / APPROVED_WITH_COMMENTS / CHANGES_REQUIRED with numbered findings. If APPROVED brief. If CHANGES_REQUIRED detailed with file:line refs.
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round1.md:626:   153	        # Codex round 3 MED follow-up: this POST path had only ImportError;
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round1.md:678:    31	# Codex round 1 HIGH (2026-04-21): strict shape gate on manifest-supplied
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round1.md:754:   107	    """Codex round 1 HIGH: reject any manifest-supplied timestamp that doesn't
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round1.md:1668:   466	    # Codex round 1 HIGH: every manifest-supplied output path is validated to
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round1.md:1761:   559	    # Codex round 1 HIGH: ensure PDF always lands under reports/phase5_reports/.
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round1.md:1762:   560	    # Codex round 2 MED: run containment FIRST, before WeasyPrint import so we
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round1.md:2991:ui/backend/tests/test_comparison_report_route.py:200:    """Codex round 3 MED follow-up: POST .../comparison-report/build must ALSO
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round1.md:3024:ui/backend/tests/test_comparison_report_route.py:200:    """Codex round 3 MED follow-up: POST .../comparison-report/build must ALSO
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round1.md:3448:  1309	  // Codex round 1 MED (2026-04-21): distinguish 404/400 (case not opted-in
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round1.md:3951:    17	# Codex round 1 HIGH #2 (2026-04-21): traversal via run_id reproduced with
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round1.md:3982:    48	    pattern to prevent path-traversal attacks (Codex round 1 HIGH #2).
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round1.md:4037:    32	# Codex round 1 HIGH (2026-04-21): enforce exact timestamp shape before
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round1.md:4102:    97	    Codex round 1 HIGH: enforce _TIMESTAMP_RE shape on the manifest value so a
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round1.md:4311:    84	# ---------- CI-safe success path (Codex round 2 LOW follow-up) --------------
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round1.md:4427:   200	    """Codex round 3 MED follow-up: POST .../comparison-report/build must ALSO
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round1.md:4914:   106	    OR empty. Codex round 1 MED #3 (2026-04-21): require a NON-empty artifact
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round1.md:5019:ui/backend/services/field_artifacts.py:24:# Codex round 2 HIGH (2026-04-21): timestamp shape gate. The manifest is
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round1.md:5041:ui/backend/services/comparison_report.py:107:    """Codex round 1 HIGH: reject any manifest-supplied timestamp that doesn't
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round1.md:5186:ui/backend/tests/test_comparison_report_service.py:116:    """Codex round 1 HIGH: manifest with timestamp='../../outside' must be rejected."""
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round1.md:5544:CHANGES_REQUIRED
reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round1.md:5564:CHANGES_REQUIRED
reports/codex_tool_reports/20260422_dec045_wave2_E_tests_prompt.md:56:5. **test_hard_fail_precedes_hazard_tier**: audit_concerns=[VELOCITY_OVERFLOW (hard-FAIL), CONTINUITY_NOT_CONVERGED (HAZARD-tier)]. Assert status=="FAIL" (hard-FAIL wins).
reports/codex_tool_reports/2026-04-21_phase7bc_render_report_codex_review.md:49:Reply APPROVED / APPROVED_WITH_COMMENTS / CHANGES_REQUIRED with numbered findings + severity.
reports/codex_tool_reports/2026-04-21_phase7bc_render_report_codex_review.md:224:Opus Gate: ⚠️ APPROVED WITH CONDITIONS (2026-04-13) — CFDJerry (T0 proxy)
reports/codex_tool_reports/2026-04-21_phase7bc_render_report_codex_review.md:312:Opus Gate: ✅ APPROVED (2026-04-13) — 5/5 criteria, 10/10 tasks, 103 tests
reports/codex_tool_reports/2026-04-21_phase7bc_render_report_codex_review.md:344:Opus Gate: ✅ APPROVED (2026-04-13)
reports/codex_tool_reports/2026-04-21_phase7bc_render_report_codex_review.md:451:- Status: COMPLETE (DEC-V61-031, 2026-04-21). 3 waves landed: adapter functions{} + executor capture + driver manifest; backend route/service/18 pytest; Codex 3 rounds → APPROVED_WITH_COMMENTS (2 HIGH security issues caught + fixed: URL basename collision + run_id path-traversal). Real LDC OpenFOAM integration produced 8 artifacts, HTTP manifest + subpath download + traversal 404 verified live. 97/97 pytest. v6.1 counter 16→17.
reports/codex_tool_reports/2026-04-21_phase7bc_render_report_codex_review.md:2084:# Codex round 1 HIGH #2 (2026-04-21): traversal via run_id reproduced with
reports/codex_tool_reports/2026-04-21_phase7bc_render_report_codex_review.md:2115:    pattern to prevent path-traversal attacks (Codex round 1 HIGH #2).
reports/codex_tool_reports/2026-04-21_phase7bc_render_report_codex_review.md:4392:CHANGES_REQUIRED
reports/codex_tool_reports/2026-04-21_phase7bc_render_report_codex_review.md:4394:1. HIGH — Manifest-derived filesystem paths are trusted without containment checks, and the PDF path makes that trust exploitable. [`comparison_report.py:257`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:257>) takes `run_manifest["timestamp"]` verbatim, [`comparison_report.py:296`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:296>) returns `renders_manifest["outputs"][key]` verbatim, and [`comparison_report.py:376`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:376>) renders the HTML with `base_url=_REPO_ROOT`. That means a tampered `runs/{label}.json` can steer reads outside `reports/phase5_fields`, a tampered renders manifest can point `<img src>` at arbitrary local image/SVG paths for WeasyPrint to load, and [`comparison_report.py:372`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:372>) can write the generated PDF outside `reports/phase5_reports`. The same timestamp trust exists on the render side in [`render_case_report.py:72`](</Users/Zhuanz/Desktop/cfd-harness-unified/scripts/render_case_report.py:72>) and [`render_case_report.py:91`](</Users/Zhuanz/Desktop/cfd-harness-unified/scripts/render_case_report.py:91>). This needs strict segment validation or `resolve()` + root-prefix checks before approval.
reports/codex_tool_reports/2026-04-21_phase7bc_render_report_codex_review.md:4396:2. MEDIUM — The `/learn` embed hides real backend failures as if the case were simply “not opted in.” [`LearnCaseDetailPage.tsx:1283`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1283>) throws on any non-200, but [`LearnCaseDetailPage.tsx:1300`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1300>) returns `null` for all errors. So a 500, malformed JSON, or regression in the report service silently removes the section from `/learn`, which is the opposite of the “scientific-grade evidence surface” honesty this phase is trying to provide. Hide only 404/unsupported-case; show an explicit error state for other statuses.
reports/codex_tool_reports/2026-04-21_phase7bc_render_report_codex_review.md:4398:3. LOW — The new route tests do not actually protect this surface in a clean checkout/CI, and I could not find any service-level `comparison_report` tests to cover the gap. [`test_comparison_report_route.py:15`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparison_report_route.py:15>) documents that the success path depends on `.gitignored` local artifacts, and [`test_comparison_report_route.py:26`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparison_report_route.py:26>) plus [`test_comparison_report_route.py:47`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparison_report_route.py:47>) just `return` when those artifacts are absent. So the automation does not exercise the successful HTML/context path, template rendering, or manifest-path handling.
reports/codex_tool_reports/2026-04-21_phase7bc_render_report_codex_review.md:4408:CHANGES_REQUIRED
reports/codex_tool_reports/2026-04-21_phase7bc_render_report_codex_review.md:4410:1. HIGH — Manifest-derived filesystem paths are trusted without containment checks, and the PDF path makes that trust exploitable. [`comparison_report.py:257`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:257>) takes `run_manifest["timestamp"]` verbatim, [`comparison_report.py:296`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:296>) returns `renders_manifest["outputs"][key]` verbatim, and [`comparison_report.py:376`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:376>) renders the HTML with `base_url=_REPO_ROOT`. That means a tampered `runs/{label}.json` can steer reads outside `reports/phase5_fields`, a tampered renders manifest can point `<img src>` at arbitrary local image/SVG paths for WeasyPrint to load, and [`comparison_report.py:372`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:372>) can write the generated PDF outside `reports/phase5_reports`. The same timestamp trust exists on the render side in [`render_case_report.py:72`](</Users/Zhuanz/Desktop/cfd-harness-unified/scripts/render_case_report.py:72>) and [`render_case_report.py:91`](</Users/Zhuanz/Desktop/cfd-harness-unified/scripts/render_case_report.py:91>). This needs strict segment validation or `resolve()` + root-prefix checks before approval.
reports/codex_tool_reports/2026-04-21_phase7bc_render_report_codex_review.md:4412:2. MEDIUM — The `/learn` embed hides real backend failures as if the case were simply “not opted in.” [`LearnCaseDetailPage.tsx:1283`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1283>) throws on any non-200, but [`LearnCaseDetailPage.tsx:1300`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1300>) returns `null` for all errors. So a 500, malformed JSON, or regression in the report service silently removes the section from `/learn`, which is the opposite of the “scientific-grade evidence surface” honesty this phase is trying to provide. Hide only 404/unsupported-case; show an explicit error state for other statuses.
reports/codex_tool_reports/2026-04-21_phase7bc_render_report_codex_review.md:4414:3. LOW — The new route tests do not actually protect this surface in a clean checkout/CI, and I could not find any service-level `comparison_report` tests to cover the gap. [`test_comparison_report_route.py:15`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparison_report_route.py:15>) documents that the success path depends on `.gitignored` local artifacts, and [`test_comparison_report_route.py:26`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparison_report_route.py:26>) plus [`test_comparison_report_route.py:47`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparison_report_route.py:47>) just `return` when those artifacts are absent. So the automation does not exercise the successful HTML/context path, template rendering, or manifest-path handling.
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:64:    "VELOCITY_OVERFLOW",           # G3
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:232:CHK-3: `_derive_contract_status` with `audit_concerns=[VELOCITY_OVERFLOW]` (hard-FAIL) + `[CONTINUITY_NOT_CONVERGED]` (HAZARD) returns `status=FAIL` (hard-FAIL takes precedence).
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:411:- Status: COMPLETE (DEC-V61-031, 2026-04-21). 3 waves landed: adapter functions{} + executor capture + driver manifest; backend route/service/18 pytest; Codex 3 rounds → APPROVED_WITH_COMMENTS (2 HIGH security issues caught + fixed: URL basename collision + run_id path-traversal). Real LDC OpenFOAM integration produced 8 artifacts, HTTP manifest + subpath download + traversal 404 verified live. 97/97 pytest. v6.1 counter 16→17.
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:436:- Status: **SPRINT 1 + SPRINT 2 TIER C COMPLETE** — DEC-V61-032 (LDC MVP) + DEC-V61-034 (Tier C visual-only fan-out to 9 cases, 2026-04-21). 8-section Jinja2 HTML template + WeasyPrint PDF + reduced visual-only context for non-LDC cases. Codex 4 + 2 rounds (both APPROVED). Tier B Sprint 2 (per-case gold-overlay for 9 cases) remains future work.
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:474:- Status: **MVP COMPLETE (LDC)** — DEC-V61-032, 2026-04-21. `LearnCaseDetailPage.tsx::ScientificComparisonReportSection` fetches `/api/cases/{id}/runs/audit_real_run/comparison-report/context`, renders verdict card + metrics grid + iframe embed of HTML report + "Open in new window" + "Download PDF" buttons. Graceful 404→hide / 5xx→error banner distinction (Codex round 1 MED fix). iframe `sandbox=""` strict. Fan-out to 9 other cases deferred to 7c Sprint 2.
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:540:Opus Gate: ⚠️ APPROVED WITH CONDITIONS (2026-04-13) — CFDJerry (T0 proxy)
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:628:Opus Gate: ✅ APPROVED (2026-04-13) — 5/5 criteria, 10/10 tasks, 103 tests
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:660:Opus Gate: ✅ APPROVED (2026-04-13)
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:868:  (CHANGES_REQUIRED, 3 blockers + 2 nits) and DEC-038 (BLOCK, 5 blockers
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:907:### DEC-V61-036b (CHANGES_REQUIRED)
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:1010:5. **Self-pass 0.50 realistic**: with 8 tracks and 4 waves, expect ≥1 Codex CHANGES_REQUIRED round before final APPROVE.
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:1033:**Related**: DEC-V61-036b (CHANGES_REQUIRED), DEC-V61-038 (BLOCK)
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:1046:    OR empty. Codex round 1 MED #3 (2026-04-21): require a NON-empty artifact
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:1325:    # Codex round 1 MED #3: only inject metadata for opted-in cases — other 9
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:1344:    # contents (best-effort, must not block audit doc). MED #3 gating above.
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:2158:  # RENAMED from `fully_developed_pipe` per Gate Q-2 Path A (DEC-V61-011, 2026-04-20).
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:2366:    #   G3  VELOCITY_OVERFLOW           — |U|_max > 100·U_ref
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:2376:        "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:3187:  * G3 VELOCITY_OVERFLOW  — |U|_max > K * U_ref (K=100 default). VTK-based,
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:3240:G4_TURBULENCE_MAX_OVERFLOW = 1.0e10  # any k/eps/omega max above this = overflow
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:3258:    concern_type: str     # "VELOCITY_OVERFLOW" | "TURBULENCE_NEGATIVE" | "CONTINUITY_DIVERGED"
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:3685:src/comparator_gates.py:4:  * G3 VELOCITY_OVERFLOW  — |U|_max > K * U_ref (K=100 default). VTK-based,
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:3751:ui/backend/services/comparison_report.py:466:    # Codex round 1 HIGH: every manifest-supplied output path is validated to
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:3929:ui/backend/services/validation_report.py:563:    #   G3  VELOCITY_OVERFLOW           — |U|_max > 100·U_ref
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:4243:ui/backend/tests/test_field_artifacts_route.py:104:    """VTK file lives at VTK/lid_driven_cavity_2000.vtk — subpath URL (Codex round 1 HIGH #1)."""
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:4485:- `ui/backend/services/validation_report.py` (`_derive_contract_status` extension for VELOCITY_OVERFLOW/TURBULENCE_NEGATIVE/CONTINUITY_DIVERGED)
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:4532:**Verdict**: APPROVE / APPROVE_WITH_NOTES / CHANGES_REQUIRED / BLOCK
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:4557:- Ready for codex_verdict=APPROVED: YES / NO
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:5802:codex_verdict: CHANGES_REQUIRED
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:5834:notion_sync_status: pending (v6.2 backfill Codex CHANGES_REQUIRED; flag to Kogami)
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:5887:- **Concern code**: `VELOCITY_OVERFLOW`
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:5916:    concern_type: str   # VELOCITY_OVERFLOW / TURBULENCE_NEGATIVE / CONTINUITY_DIVERGED
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:5949:extends its G1 hard-FAIL concern set to include `VELOCITY_OVERFLOW`,
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:5979:- `test_validation_report_fails_on_gate_concern` — fixture with VELOCITY_OVERFLOW concern → contract_status FAIL
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:6018:reports/codex_tool_reports/20260422_dec036b_codex_review.md:567:  * G3 VELOCITY_OVERFLOW  — |U|_max > K * U_ref (K=100 default). VTK-based,
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:6033:reports/codex_tool_reports/20260422_dec036b_codex_review.md:1752:    #   G3  VELOCITY_OVERFLOW           — |U|_max > 100·U_ref
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:6049:reports/codex_tool_reports/20260422_dec036b_codex_review.md:2938:/bin/zsh -lc 'rg -n "u_ref|U_ref|boundary_conditions|check_all_gates|_derive_contract_status|VELOCITY_OVERFLOW|TURBULENCE_NEGATIVE|CONTINUITY_DIVERGED" -S scripts/phase5_audit_run.py src/comparator_gates.py ui/backend/services/validation_report.py ui/backend/tests/test_comparator_gates_g3_g4_g5.py' in /Users/Zhuanz/Desktop/cfd-harness-unified
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:6061:reports/codex_tool_reports/20260422_dec036b_codex_review.md:2965:ui/backend/services/validation_report.py:563:    #   G3  VELOCITY_OVERFLOW           — |U|_max > 100·U_ref
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:6063:reports/codex_tool_reports/20260422_dec036b_codex_review.md:2978:src/comparator_gates.py:4:  * G3 VELOCITY_OVERFLOW  — |U|_max > K * U_ref (K=100 default). VTK-based,
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:6149:reports/codex_tool_reports/20260422_dec036b_codex_review.md:4725:   563	    #   G3  VELOCITY_OVERFLOW           — |U|_max > 100·U_ref
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:6236:reports/codex_tool_reports/20260422_dec036b_codex_review.md:5150:src/comparator_gates.py:4:  * G3 VELOCITY_OVERFLOW  — |U|_max > K * U_ref (K=100 default). VTK-based,
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:7253:reports/codex_tool_reports/20260422_dec036b_codex_review.md:5148:/bin/zsh -lc "rg -n \"read_final_velocity_max|synthetic_vtk|VELOCITY_OVERFLOW.*VTK|pyvista\" ui/backend/tests tests src | sed -n '1,200p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:7581:reports/codex_tool_reports/20260422_dec045_wave1_B_comparator_gates_result.md:2497:- CHK-6: PASS — `_check_g3_velocity_overflow(...)` still works unchanged; harness produced one `VELOCITY_OVERFLOW` violation from the selected latest internal VTK.
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:7589:reports/codex_tool_reports/20260422_dec045_wave1_B_comparator_gates_result.md:2618:- CHK-6: PASS — `_check_g3_velocity_overflow(...)` still works unchanged; harness produced one `VELOCITY_OVERFLOW` violation from the selected latest internal VTK.
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:8045:status3 = _derive_contract_status(gs, measurement, [], [AuditConcern(concern_type='VELOCITY_OVERFLOW', summary='', detail='', decision_refs=[]), AuditConcern(concern_type='CONTINUITY_NOT_CONVERGED', summary='', detail='', decision_refs=[])])
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:8120:status3 = _derive_contract_status(gs, measurement, [], [AuditConcern(concern_type='VELOCITY_OVERFLOW', summary='', detail='', decision_refs=[]), AuditConcern(concern_type='CONTINUITY_NOT_CONVERGED', summary='', detail='', decision_refs=[])])
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:8247:status3 = _derive_contract_status(gs, measurement, [], [AuditConcern(concern_type='VELOCITY_OVERFLOW', summary='', detail='', decision_refs=[]), AuditConcern(concern_type='CONTINUITY_NOT_CONVERGED', summary='', detail='', decision_refs=[])])
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:8555:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:8821:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:8872:    #   G3  VELOCITY_OVERFLOW           — |U|_max > 100·U_ref
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:8883:        "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:9115:    OR empty. Codex round 1 MED #3 (2026-04-21): require a NON-empty artifact
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:9572:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:9623:    # contents (best-effort, must not block audit doc). MED #3 gating above.
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:9903:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:10178:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:10484:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:10761:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:11033:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:11308:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:11583:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:11619:/bin/zsh -lc "rg -n \"_derive_contract_status|phase5_audit_run|VELOCITY_OVERFLOW|CONTINUITY_NOT_CONVERGED|RESIDUALS_ABOVE_TARGET\" ui/backend/tests -g '*.py'" in /Users/Zhuanz/Desktop/cfd-harness-unified
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:11625:ui/backend/tests/test_comparator_gates_g3_g4_g5.py:185:    assert g3[0].concern_type == "VELOCITY_OVERFLOW"
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:11626:ui/backend/tests/test_comparator_gates_g3_g4_g5.py:327:    """Fixture with VELOCITY_OVERFLOW concern must hard-FAIL the verdict."""
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:11628:ui/backend/tests/test_comparator_gates_g3_g4_g5.py:351:            concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:11630:ui/backend/tests/test_comparator_gates_g3_g4_g5.py:358:    # DEC-V61-036b: VELOCITY_OVERFLOW overrides a "within band" comparator PASS.
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:11659:checks['CHK-3'] = _derive_contract_status(ref, in_band, [], [AuditConcern(concern_type='VELOCITY_OVERFLOW', summary='', detail='', decision_refs=[]), AuditConcern(concern_type='CONTINUITY_NOT_CONVERGED', summary='', detail='', decision_refs=[])])
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:11943:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:12238:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:12514:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:12800:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:13074:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:13372:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:13411:   563	    #   G3  VELOCITY_OVERFLOW           — |U|_max > 100·U_ref
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:13422:   574	        "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:13990:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:14267:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:14705:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:14758:- `CHK-3`: PASS. `VELOCITY_OVERFLOW` + `CONTINUITY_NOT_CONVERGED` still returns `FAIL`; hard-fail precedence is intact.
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:15014:         "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_D_hazard_tier_uref_result.md:15068:- `CHK-3`: PASS. `VELOCITY_OVERFLOW` + `CONTINUITY_NOT_CONVERGED` still returns `FAIL`; hard-fail precedence is intact.
reports/codex_tool_reports/2026-04-21_phase7bde_codex_review_round2.md:16:Round 2 review: Phase 7b-polish + 7d + 7e bundle. Round 1 returned CHANGES_REQUIRED with 3 findings; all 3 fixes applied. Uncommitted in /Users/Zhuanz/Desktop/cfd-harness-unified working tree.
reports/codex_tool_reports/2026-04-21_phase7bde_codex_review_round2.md:53:Reply APPROVED / APPROVED_WITH_COMMENTS / CHANGES_REQUIRED. Brief if APPROVED.
reports/codex_tool_reports/2026-04-21_phase7bde_codex_review_round2.md:1831:    31	# Codex round 1 HIGH (2026-04-21): strict shape gate on manifest-supplied
reports/codex_tool_reports/2026-04-21_phase7bde_codex_review_round2.md:1891:    91	    """Codex round 1 HIGH: reject any manifest-supplied timestamp that doesn't
reports/codex_tool_reports/2026-04-21_phase7bde_codex_review_round2.md:2441:   378	    # Codex round 1 HIGH: every manifest-supplied output path is validated to
reports/codex_tool_reports/2026-04-21_phase7bde_codex_review_round2.md:2798:APPROVED_WITH_COMMENTS
reports/codex_tool_reports/2026-04-21_phase7bde_codex_review_round2.md:2810:APPROVED_WITH_COMMENTS
reports/codex_tool_reports/20260422_dec036b_codex_review.md:27:- `ui/backend/services/validation_report.py` (`_derive_contract_status` extension for VELOCITY_OVERFLOW/TURBULENCE_NEGATIVE/CONTINUITY_DIVERGED)
reports/codex_tool_reports/20260422_dec036b_codex_review.md:74:**Verdict**: APPROVE / APPROVE_WITH_NOTES / CHANGES_REQUIRED / BLOCK
reports/codex_tool_reports/20260422_dec036b_codex_review.md:99:- Ready for codex_verdict=APPROVED: YES / NO
reports/codex_tool_reports/20260422_dec036b_codex_review.md:452:- **Concern code**: `VELOCITY_OVERFLOW`
reports/codex_tool_reports/20260422_dec036b_codex_review.md:481:    concern_type: str   # VELOCITY_OVERFLOW / TURBULENCE_NEGATIVE / CONTINUITY_DIVERGED
reports/codex_tool_reports/20260422_dec036b_codex_review.md:514:extends its G1 hard-FAIL concern set to include `VELOCITY_OVERFLOW`,
reports/codex_tool_reports/20260422_dec036b_codex_review.md:544:- `test_validation_report_fails_on_gate_concern` — fixture with VELOCITY_OVERFLOW concern → contract_status FAIL
reports/codex_tool_reports/20260422_dec036b_codex_review.md:567:  * G3 VELOCITY_OVERFLOW  — |U|_max > K * U_ref (K=100 default). VTK-based,
reports/codex_tool_reports/20260422_dec036b_codex_review.md:620:G4_TURBULENCE_MAX_OVERFLOW = 1.0e10  # any k/eps/omega max above this = overflow
reports/codex_tool_reports/20260422_dec036b_codex_review.md:638:    concern_type: str     # "VELOCITY_OVERFLOW" | "TURBULENCE_NEGATIVE" | "CONTINUITY_DIVERGED"
reports/codex_tool_reports/20260422_dec036b_codex_review.md:916:                concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec036b_codex_review.md:944:                        concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec036b_codex_review.md:1004:        if _exceeds_threshold(f_max, G4_TURBULENCE_MAX_OVERFLOW):
reports/codex_tool_reports/20260422_dec036b_codex_review.md:1011:                        f"(> {G4_TURBULENCE_MAX_OVERFLOW:.0g})"
reports/codex_tool_reports/20260422_dec036b_codex_review.md:1016:                        f"{G4_TURBULENCE_MAX_OVERFLOW:.0g}. For realistic "
reports/codex_tool_reports/20260422_dec036b_codex_review.md:1024:                        "threshold": G4_TURBULENCE_MAX_OVERFLOW,
reports/codex_tool_reports/20260422_dec036b_codex_review.md:1083:    OR empty. Codex round 1 MED #3 (2026-04-21): require a NON-empty artifact
reports/codex_tool_reports/20260422_dec036b_codex_review.md:1588:    # Codex round 1 MED #3: only inject metadata for opted-in cases — other 9
reports/codex_tool_reports/20260422_dec036b_codex_review.md:1607:    # contents (best-effort, must not block audit doc). MED #3 gating above.
reports/codex_tool_reports/20260422_dec036b_codex_review.md:1752:    #   G3  VELOCITY_OVERFLOW           — |U|_max > 100·U_ref
reports/codex_tool_reports/20260422_dec036b_codex_review.md:1762:        "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec036b_codex_review.md:2666:_BFS_BLOWUP_TAIL = """\
reports/codex_tool_reports/20260422_dec036b_codex_review.md:2692:    log = _write_log(tmp_path, _BFS_BLOWUP_TAIL)
reports/codex_tool_reports/20260422_dec036b_codex_review.md:2714:    log = _write_log(tmp_path, _BFS_BLOWUP_TAIL)
reports/codex_tool_reports/20260422_dec036b_codex_review.md:2747:    log = _write_log(tmp_path, _BFS_BLOWUP_TAIL)
reports/codex_tool_reports/20260422_dec036b_codex_review.md:2783:    log = _write_log(tmp_path, _BFS_BLOWUP_TAIL)
reports/codex_tool_reports/20260422_dec036b_codex_review.md:2787:    assert g3[0].concern_type == "VELOCITY_OVERFLOW"
reports/codex_tool_reports/20260422_dec036b_codex_review.md:2855:    """Fixture with VELOCITY_OVERFLOW concern must hard-FAIL the verdict."""
reports/codex_tool_reports/20260422_dec036b_codex_review.md:2879:            concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec036b_codex_review.md:2886:    # DEC-V61-036b: VELOCITY_OVERFLOW overrides a "within band" comparator PASS.
reports/codex_tool_reports/20260422_dec036b_codex_review.md:2938:/bin/zsh -lc 'rg -n "u_ref|U_ref|boundary_conditions|check_all_gates|_derive_contract_status|VELOCITY_OVERFLOW|TURBULENCE_NEGATIVE|CONTINUITY_DIVERGED" -S scripts/phase5_audit_run.py src/comparator_gates.py ui/backend/services/validation_report.py ui/backend/tests/test_comparator_gates_g3_g4_g5.py' in /Users/Zhuanz/Desktop/cfd-harness-unified
reports/codex_tool_reports/20260422_dec036b_codex_review.md:2948:ui/backend/tests/test_comparator_gates_g3_g4_g5.py:158:    assert g3[0].concern_type == "VELOCITY_OVERFLOW"
reports/codex_tool_reports/20260422_dec036b_codex_review.md:2953:ui/backend/tests/test_comparator_gates_g3_g4_g5.py:224:    """Fixture with VELOCITY_OVERFLOW concern must hard-FAIL the verdict."""
reports/codex_tool_reports/20260422_dec036b_codex_review.md:2955:ui/backend/tests/test_comparator_gates_g3_g4_g5.py:248:            concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec036b_codex_review.md:2957:ui/backend/tests/test_comparator_gates_g3_g4_g5.py:255:    # DEC-V61-036b: VELOCITY_OVERFLOW overrides a "within band" comparator PASS.
reports/codex_tool_reports/20260422_dec036b_codex_review.md:2965:ui/backend/services/validation_report.py:563:    #   G3  VELOCITY_OVERFLOW           — |U|_max > 100·U_ref
reports/codex_tool_reports/20260422_dec036b_codex_review.md:2968:ui/backend/services/validation_report.py:573:        "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec036b_codex_review.md:2978:src/comparator_gates.py:4:  * G3 VELOCITY_OVERFLOW  — |U|_max > K * U_ref (K=100 default). VTK-based,
reports/codex_tool_reports/20260422_dec036b_codex_review.md:2982:src/comparator_gates.py:75:    concern_type: str     # "VELOCITY_OVERFLOW" | "TURBULENCE_NEGATIVE" | "CONTINUITY_DIVERGED"
reports/codex_tool_reports/20260422_dec036b_codex_review.md:2986:src/comparator_gates.py:269:                concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec036b_codex_review.md:2991:src/comparator_gates.py:297:                        concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec036b_codex_review.md:3327:  # RENAMED from `fully_developed_pipe` per Gate Q-2 Path A (DEC-V61-011, 2026-04-20).
reports/codex_tool_reports/20260422_dec036b_codex_review.md:3589:   269	                concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec036b_codex_review.md:3617:   297	                        concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec036b_codex_review.md:3836:    37	_BFS_BLOWUP_TAIL = """\
reports/codex_tool_reports/20260422_dec036b_codex_review.md:3862:    63	    log = _write_log(tmp_path, _BFS_BLOWUP_TAIL)
reports/codex_tool_reports/20260422_dec036b_codex_review.md:3884:    85	    log = _write_log(tmp_path, _BFS_BLOWUP_TAIL)
reports/codex_tool_reports/20260422_dec036b_codex_review.md:3917:   118	    log = _write_log(tmp_path, _BFS_BLOWUP_TAIL)
reports/codex_tool_reports/20260422_dec036b_codex_review.md:3953:   154	    log = _write_log(tmp_path, _BFS_BLOWUP_TAIL)
reports/codex_tool_reports/20260422_dec036b_codex_review.md:3957:   158	    assert g3[0].concern_type == "VELOCITY_OVERFLOW"
reports/codex_tool_reports/20260422_dec036b_codex_review.md:4023:   224	    """Fixture with VELOCITY_OVERFLOW concern must hard-FAIL the verdict."""
reports/codex_tool_reports/20260422_dec036b_codex_review.md:4047:   248	            concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec036b_codex_review.md:4054:   255	    # DEC-V61-036b: VELOCITY_OVERFLOW overrides a "within band" comparator PASS.
reports/codex_tool_reports/20260422_dec036b_codex_review.md:4725:   563	    #   G3  VELOCITY_OVERFLOW           — |U|_max > 100·U_ref
reports/codex_tool_reports/20260422_dec036b_codex_review.md:4735:   573	        "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec036b_codex_review.md:4973:   548	    # contents (best-effort, must not block audit doc). MED #3 gating above.
reports/codex_tool_reports/20260422_dec036b_codex_review.md:5148:/bin/zsh -lc "rg -n \"read_final_velocity_max|synthetic_vtk|VELOCITY_OVERFLOW.*VTK|pyvista\" ui/backend/tests tests src | sed -n '1,200p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
reports/codex_tool_reports/20260422_dec036b_codex_review.md:5150:src/comparator_gates.py:4:  * G3 VELOCITY_OVERFLOW  — |U|_max > K * U_ref (K=100 default). VTK-based,
reports/codex_tool_reports/20260422_dec036b_codex_review.md:5224:**Verdict**: CHANGES_REQUIRED  
reports/codex_tool_reports/20260422_dec036b_codex_review.md:5256:- Ready for `codex_verdict=APPROVED`: NO
reports/codex_tool_reports/20260422_dec036b_codex_review.md:5270:**Verdict**: CHANGES_REQUIRED  
reports/codex_tool_reports/20260422_dec036b_codex_review.md:5302:- Ready for `codex_verdict=APPROVED`: NO
reports/codex_tool_reports/2026-04-21_pr23_build_fingerprint_review.md:10:`APPROVED_WITH_NOTES`
reports/codex_tool_reports/dec_v61_057_round1.md:10:**CHANGES_REQUIRED** · 2 blockers for Batch B · NO_GO
reports/codex_tool_reports/dec_v61_057_round1.md:14:| HIGH | 2 |
reports/codex_tool_reports/dec_v61_057_round1.md:15:| MED  | 1 |
reports/codex_tool_reports/dec_v61_057_round1.md:16:| LOW  | 0 |
reports/codex_tool_reports/dec_v61_057_round1.md:20:### F1-HIGH · Supported DHC alias still falls through to old AR=2.0/RAS path · ADDRESSED in A.5
reports/codex_tool_reports/dec_v61_057_round1.md:38:### F2-HIGH · Lineage repair stops at report.md · DEFERRED to Stage A.6
reports/codex_tool_reports/dec_v61_057_round1.md:56:### F3-MED · RBC 2:1 rectangle semantic mismatch · DEFERRED to round-2 followup
reports/codex_tool_reports/dec_v61_057_round1.md:76:| F1-HIGH | ✅ Addressed | Stage A.5 commit 3283135 (alias normalization) |
reports/codex_tool_reports/dec_v61_057_round1.md:77:| F2-HIGH | ⏸ Deferred | Stage A.6 (retire DHC-special HTML path) — not blocking Stage B physics |
reports/codex_tool_reports/dec_v61_057_round1.md:78:| F3-MED  | ⏸ Deferred | Round-2 followup or separate DEC (RBC geometry semantic) |
reports/codex_tool_reports/2026-04-28_m_panels_arc_codex_review_round2.md:13:`APPROVE` — 0 P1, 0 P2, 0 P3.
reports/codex_tool_reports/2026-04-28_m_panels_arc_codex_review_round2.md:33:Codex-verified: APPROVE
reports/codex_tool_reports/dec_v61_057_plan_review.md:14:| HIGH | 3 |
reports/codex_tool_reports/dec_v61_057_plan_review.md:15:| MED  | 2 |
reports/codex_tool_reports/dec_v61_057_plan_review.md:16:| LOW  | 1 |
reports/codex_tool_reports/dec_v61_057_plan_review.md:21:### F1-HIGH · Canonical DHC contract is not actually established before extractor work
reports/codex_tool_reports/dec_v61_057_plan_review.md:51:### F2-HIGH · Report drift is mis-scoped; the stale source is `auto_verify_report.yaml`, not `report.md`
reports/codex_tool_reports/dec_v61_057_plan_review.md:74:### F3-HIGH · `stream_function_max` declared before scaling and gate status are correctly defined
reports/codex_tool_reports/dec_v61_057_plan_review.md:89:### F4-MED · Type-I independence claim overstated
reports/codex_tool_reports/dec_v61_057_plan_review.md:102:### F5-MED · Round budget too optimistic
reports/codex_tool_reports/dec_v61_057_plan_review.md:112:### F6-LOW · Strict template hygiene inconsistent
reports/codex_tool_reports/dec_v61_057_plan_review.md:128:All 6 required edits applied. v2 intake committed; Codex re-review pending to confirm APPROVE_PLAN_WITH_CHANGES (or APPROVE_PLAN). Stage A on hold until re-review verdict.
reports/codex_tool_reports/dec_v61_057_round4.md:11:**APPROVE_WITH_COMMENTS** · 1 MED + 1 LOW · NO Stage E blocker
reports/codex_tool_reports/dec_v61_057_round4.md:15:| HIGH | 0 |
reports/codex_tool_reports/dec_v61_057_round4.md:16:| MED  | 1 |
reports/codex_tool_reports/dec_v61_057_round4.md:17:| LOW  | 1 |
reports/codex_tool_reports/dec_v61_057_round4.md:25:### F1-MED · DHC observables[] gold schema not wired into preflight scalar gate · ADDRESSED
reports/codex_tool_reports/dec_v61_057_round4.md:53:### F2-LOW · Legacy markdown report still treats advisory as hard-gated · ADDRESSED
reports/codex_tool_reports/dec_v61_057_round4.md:73:  LOW severity).
reports/codex_tool_reports/dec_v61_057_round4.md:98:| F1-MED  | ✅ Addressed | this commit (preflight schema_v2 normalization + 4 regression tests) |
reports/codex_tool_reports/dec_v61_057_round4.md:99:| F2-LOW  | ✅ Addressed | this commit (`_build_template_context` HARD_GATED filter) |
reports/codex_tool_reports/dec_v61_074_t1b1_round2.md:3:- **Verdict**: APPROVE_WITH_COMMENTS (R1 HIGH closed)
reports/codex_tool_reports/dec_v61_074_t1b1_round2.md:9:## R1 HIGH finding · CLOSED
reports/codex_tool_reports/dec_v61_074_t1b1_round2.md:17:### 1. LOW — Stale inline comment at manifest.py:467
reports/codex_tool_reports/dec_v61_074_t1b1_round2.md:31:## LOW closure
reports/codex_tool_reports/dec_v61_074_t1b1_round2.md:33:LOW finding closed verbatim within RETRO-V61-001 5-condition exception (≤20 LOC, 1 file, no API surface change, diff-level Codex match) — inline comment swap landed in the same commit `f599129` (attribution-misaligned per DEC addendum).
reports/codex_tool_reports/2026-04-28_m_viz_bundle_steps_3_to_6_codex_review_round2.md:76:If Round-3 returns APPROVE / APPROVE_WITH_COMMENTS with no new
reports/codex_tool_reports/2026-04-21_pr20_foam_adapter_review.md:10:APPROVED_WITH_NOTES
reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round1.md:3:- **Verdict**: CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round1.md:26:R2 introduced 2 new findings (P2/P3 below); R3, R4 each introduced more cross-system findings; R5 returned APPROVE. Rolled into commit b2ea911.
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:18:Round 2 MED + LOW follow-ups applied:
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:19:- MED: render_report_pdf containment now runs BEFORE import weasyprint. PDF output_path validated against resolved reports_root = _REPO_ROOT/reports/phase5_reports/; raises ReportError if escape detected, regardless of WeasyPrint availability.
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:20:- MED: route layer now catches BOTH ImportError AND OSError → 503 with detailed message naming DYLD_FALLBACK_LIBRARY_PATH + brew deps. Applies to both /comparison-report.pdf GET and /comparison-report/build POST.
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:21:- LOW: added 2 CI-safe route-level synthetic-tree tests in test_comparison_report_route.py — _synth_route_tree fixture monkeypatches service module globals (_REPO_ROOT, _FIELDS_ROOT, _RENDERS_ROOT, _GOLD_ROOT, _FIXTURE_ROOT) so route integration (TestClient → route → service → template) exercises 200 path without needing real OpenFOAM artifacts. test_html_200_end_to_end_synthetic asserts all 8 section markers in response. test_context_json_end_to_end_synthetic asserts JSON context has expected shape.
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:26:- HIGH (path containment) — closed round 1
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:27:- MED (silent error swallow) — closed round 1 (frontend)
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:28:- MED-round2 (containment-before-import + OSError→503) — closed round 2
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:29:- LOW (CI-safe route success tests) — closed round 2
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:31:Reply APPROVED / APPROVED_WITH_COMMENTS / CHANGES_REQUIRED.
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:304:    31	# Codex round 1 HIGH (2026-04-21): strict shape gate on manifest-supplied
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:364:    91	    """Codex round 1 HIGH: reject any manifest-supplied timestamp that doesn't
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:847:    84	# ---------- CI-safe success path (Codex round 2 LOW follow-up) --------------
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:955:     5	round-1 HIGH containment guards.
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:1066:   116	    """Codex round 1 HIGH: manifest with timestamp='../../outside' must be rejected."""
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:1087:   137	    """Codex round 1 HIGH: img src in renders manifest must be inside renders root."""
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:1125:   175	    """Codex round 1 HIGH: caller-supplied output_path must stay under reports/phase5_reports/."""
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:1148:    16	Phase 7b+7c+7f round 2 verification after CHANGES_REQUIRED round 1.
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:1151:    19	- HIGH: Manifest-derived paths (timestamp + renders outputs + PDF output) trusted without containment.
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:1152:    20	- MEDIUM: /learn embed silently swallows ALL errors, not just 404.
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:1153:    21	- LOW: Route tests skip on missing artifacts; no service-level unit tests.
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:1157:    25	1. HIGH closure — three lines of defense added:
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:1162:    30	2. MEDIUM closure — ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx ScientificComparisonReportSection now distinguishes error cases:
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:1167:    35	3. LOW closure — new test_comparison_report_service.py with 7 CI-safe unit tests:
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:1506:   345	    # Codex round 1 HIGH: every manifest-supplied output path is validated to
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:1597:   436	    # Codex round 1 HIGH: ensure PDF always lands under reports/phase5_reports/.
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:1598:   437	    # Codex round 2 MED: run containment FIRST, before WeasyPrint import so we
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:2025:+  // Codex round 1 MED (2026-04-21): distinguish 404/400 (case not opted-in
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:2350:    32	# Codex round 1 HIGH (2026-04-21): enforce exact timestamp shape before
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:2398:    80	    Codex round 1 HIGH: enforce _TIMESTAMP_RE shape on the manifest value so a
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:2713:ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1300:  // Codex round 1 MED (2026-04-21): distinguish 404/400 (case not opted-in
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:2751:  1300	  // Codex round 1 MED (2026-04-21): distinguish 404/400 (case not opted-in
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:2819:CHANGES_REQUIRED
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:2821:- MED: `POST /api/cases/{case_id}/runs/{run_label}/comparison-report/build` is still not fixed. In [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/routes/comparison_report.py:103) the build route catches only `ImportError`; it does not catch `OSError`, and [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/routes/comparison_report.py:108) still returns the old generic `"WeasyPrint unavailable"` detail instead of the detailed 503 message claimed for round 2. I reproduced this directly by forcing `render_report_pdf()` to raise `OSError("libpango missing")`: `GET .../comparison-report.pdf` returned `503` as intended, but `POST .../comparison-report/build` returned `500 Internal Server Error`.
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:2824:- HIGH path containment: closed in [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:298), [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:347), and [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:440).
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:2825:- MED frontend silent swallow: closed in [LearnCaseDetailPage.tsx](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1303).
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:2826:- LOW CI-safe route success coverage: present in [test_comparison_report_route.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparison_report_route.py:94).
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:2836:CHANGES_REQUIRED
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:2838:- MED: `POST /api/cases/{case_id}/runs/{run_label}/comparison-report/build` is still not fixed. In [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/routes/comparison_report.py:103) the build route catches only `ImportError`; it does not catch `OSError`, and [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/routes/comparison_report.py:108) still returns the old generic `"WeasyPrint unavailable"` detail instead of the detailed 503 message claimed for round 2. I reproduced this directly by forcing `render_report_pdf()` to raise `OSError("libpango missing")`: `GET .../comparison-report.pdf` returned `503` as intended, but `POST .../comparison-report/build` returned `500 Internal Server Error`.
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:2841:- HIGH path containment: closed in [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:298), [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:347), and [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:440).
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:2842:- MED frontend silent swallow: closed in [LearnCaseDetailPage.tsx](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1303).
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round3.md:2843:- LOW CI-safe route success coverage: present in [test_comparison_report_route.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparison_report_route.py:94).
reports/codex_tool_reports/dec_v61_097_phase_1a_round4.md:4:**Verdict**: `Codex-verified: RESOLVED round-3 HIGH closed; no regression found in reviewed slice`
reports/codex_tool_reports/dec_v61_097_phase_1a_round4.md:15:> Codex-verified: RESOLVED round-3 HIGH closed; no regression found in reviewed slice
reports/codex_tool_reports/dec_v61_097_phase_1a_round4.md:23:| 1 | CHANGES_REQUIRED | 4 (2 HIGH preflight + run_id, 2 MED bc_glb hardening) | `d657bed` |
reports/codex_tool_reports/dec_v61_097_phase_1a_round4.md:24:| 2 | CHANGES_REQUIRED | 3 (HIGH GeneratorExit leak, MED cache-hit bypass, LOW boundary rename) | `3ddc098` |
reports/codex_tool_reports/dec_v61_097_phase_1a_round4.md:25:| 3 | CHANGES_REQUIRED | 1 (HIGH start yield outside outer try) | `f3809fc` |
reports/codex_tool_reports/dec_v61_097_phase_1a_round4.md:43:DEC-V61-097 self-estimated 55% pre-Codex. Actual: needed 4 rounds before APPROVE/RESOLVED. Calibration drift = -55% (4 rounds vs. predicted ≤2). Logging in next retrospective per the methodology.
reports/codex_tool_reports/dec_v61_071_round2.md:7:- Verdict: `APPROVE_WITH_COMMENTS`
reports/codex_tool_reports/dec_v61_052_bfs_round1_findings.md:1:VERDICT: APPROVE | APPROVE_WITH_COMMENTS | CHANGES_REQUIRED | RETRACT
reports/codex_tool_reports/dec_v61_052_bfs_round1_findings.md:4:  #1 [HIGH|MED|LOW] <title>
reports/codex_tool_reports/dec_v61_052_bfs_round1_findings.md:18:VERDICT: CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_052_bfs_round1_findings.md:22:#1 [HIGH] Audit Xr is extracted from the wrong probe path
reports/codex_tool_reports/dec_v61_052_bfs_round1_findings.md:27:#2 [HIGH] Preflight marks an outside-tolerance scalar as “safe to visualize”
reports/codex_tool_reports/dec_v61_052_bfs_round1_findings.md:32:#3 [MED] Near-wall Ux zero-crossing is a useful proxy, not the true reattachment observable
reports/codex_tool_reports/dec_v61_052_bfs_round1_findings.md:37:#4 [MED] The -37% Xr miss should not be attributed to “known k-epsilon envelope” yet
reports/codex_tool_reports/dec_v61_052_bfs_round1_findings.md:42:#5 [LOW] Convergence is stable, but metric stationarity is not yet demonstrated
reports/codex_tool_reports/dec_v61_052_bfs_round1_findings.md:50:VERDICT: CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_052_bfs_round1_findings.md:54:#1 [HIGH] Audit Xr is extracted from the wrong probe path
reports/codex_tool_reports/dec_v61_052_bfs_round1_findings.md:59:#2 [HIGH] Preflight marks an outside-tolerance scalar as “safe to visualize”
reports/codex_tool_reports/dec_v61_052_bfs_round1_findings.md:64:#3 [MED] Near-wall Ux zero-crossing is a useful proxy, not the true reattachment observable
reports/codex_tool_reports/dec_v61_052_bfs_round1_findings.md:69:#4 [MED] The -37% Xr miss should not be attributed to “known k-epsilon envelope” yet
reports/codex_tool_reports/dec_v61_052_bfs_round1_findings.md:74:#5 [LOW] Convergence is stable, but metric stationarity is not yet demonstrated
reports/codex_tool_reports/2026-04-21_pr5d_screen6_review.md:10:CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round5.md:3:- **Verdict**: APPROVE
reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round5.md:27:| R1 | CHANGES_REQUIRED | 1 | P2 |
reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round5.md:28:| R2 | CHANGES_REQUIRED | 2 | P2 + P3 |
reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round5.md:29:| R3 | CHANGES_REQUIRED | 2 | P2 + P3 |
reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round5.md:30:| R4 | CHANGES_REQUIRED | 2 | P2-A + P2-B |
reports/codex_tool_reports/dec_v61_075_t2_1_t2_2_pre_merge_round5.md:31:| R5 | APPROVE | 0 | — |
reports/codex_tool_reports/20260422_dec045_wave2_E_tests_result.md:70:5. **test_hard_fail_precedes_hazard_tier**: audit_concerns=[VELOCITY_OVERFLOW (hard-FAIL), CONTINUITY_NOT_CONVERGED (HAZARD-tier)]. Assert status=="FAIL" (hard-FAIL wins).
reports/codex_tool_reports/20260422_dec045_wave2_E_tests_result.md:1937:    "VELOCITY_OVERFLOW",           # G3
reports/codex_tool_reports/20260422_dec045_wave2_E_tests_result.md:2105:CHK-3: `_derive_contract_status` with `audit_concerns=[VELOCITY_OVERFLOW]` (hard-FAIL) + `[CONTINUITY_NOT_CONVERGED]` (HAZARD) returns `status=FAIL` (hard-FAIL takes precedence).
reports/codex_tool_reports/20260422_dec045_wave2_E_tests_result.md:2218:    #   G3  VELOCITY_OVERFLOW           — |U|_max > 100·U_ref
reports/codex_tool_reports/20260422_dec045_wave2_E_tests_result.md:2229:        "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_E_tests_result.md:2505:    # contents (best-effort, must not block audit doc). MED #3 gating above.
reports/codex_tool_reports/20260422_dec045_wave2_E_tests_result.md:3093:            concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_E_tests_result.md:3100:    # DEC-V61-036b: VELOCITY_OVERFLOW overrides a "within band" comparator PASS.
reports/codex_tool_reports/20260422_dec045_wave2_E_tests_result.md:4140:        # A6 only fires when residuals are STUCK AT A HIGH PLATEAU — i.e.,
reports/codex_tool_reports/20260422_dec045_wave2_E_tests_result.md:4473:+                concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_E_tests_result.md:4723:+                concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_E_tests_result.md:4977:+                concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_E_tests_result.md:5244:+                concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_E_tests_result.md:5518:+                concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_E_tests_result.md:5773:+                concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_E_tests_result.md:6093:+                concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_E_tests_result.md:6417:+                concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_E_tests_result.md:6751:+                concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_E_tests_result.md:7030:   137	                concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_E_tests_result.md:7451:+                concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_E_tests_result.md:7768:+                concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_E_tests_result.md:8092:+                concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_E_tests_result.md:8441:+                concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave2_E_tests_result.md:8803:+                concern_type="VELOCITY_OVERFLOW",
reports/codex_tool_reports/dec_v61_097_phase_1a_round3.md:4:**Verdict**: `Codex-verified: CHANGES_REQUIRED immediate disconnect after the first start SSE still bypasses the new finally and leaks _active_runs`
reports/codex_tool_reports/dec_v61_097_phase_1a_round3.md:13:### HIGH — `start` yield was OUTSIDE the new outer try/finally
reports/codex_tool_reports/dec_v61_097_phase_1a_round3.md:31:So R3.1 (cache-hit symlink containment) and the LOW regression (boundary→boundary_path rename) are both confirmed closed. Only the SSE finally-coverage gap remains.
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:16:Phase 7b+7c+7f round 2 verification after CHANGES_REQUIRED round 1.
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:19:- HIGH: Manifest-derived paths (timestamp + renders outputs + PDF output) trusted without containment.
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:20:- MEDIUM: /learn embed silently swallows ALL errors, not just 404.
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:21:- LOW: Route tests skip on missing artifacts; no service-level unit tests.
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:25:1. HIGH closure — three lines of defense added:
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:30:2. MEDIUM closure — ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx ScientificComparisonReportSection now distinguishes error cases:
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:35:3. LOW closure — new test_comparison_report_service.py with 7 CI-safe unit tests:
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:447:# Codex round 1 HIGH (2026-04-21): strict shape gate on manifest-supplied
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:507:    """Codex round 1 HIGH: reject any manifest-supplied timestamp that doesn't
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:714:# Codex round 1 HIGH (2026-04-21): enforce exact timestamp shape before
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:762:    Codex round 1 HIGH: enforce _TIMESTAMP_RE shape on the manifest value so a
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:1258:round-1 HIGH containment guards.
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:1369:    """Codex round 1 HIGH: manifest with timestamp='../../outside' must be rejected."""
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:1390:    """Codex round 1 HIGH: img src in renders manifest must be inside renders root."""
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:1428:    """Codex round 1 HIGH: caller-supplied output_path must stay under reports/phase5_reports/."""
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:1591:1300:  // Codex round 1 MED (2026-04-21): distinguish 404/400 (case not opted-in
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:1608:     5	round-1 HIGH containment guards.
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:1719:   116	    """Codex round 1 HIGH: manifest with timestamp='../../outside' must be rejected."""
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:1740:   137	    """Codex round 1 HIGH: img src in renders manifest must be inside renders root."""
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:1778:   175	    """Codex round 1 HIGH: caller-supplied output_path must stay under reports/phase5_reports/."""
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:1818:    31	# Codex round 1 HIGH (2026-04-21): strict shape gate on manifest-supplied
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:1878:    91	    """Codex round 1 HIGH: reject any manifest-supplied timestamp that doesn't
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:2222:   345	    # Codex round 1 HIGH: every manifest-supplied output path is validated to
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:2312:   435	    # Codex round 1 HIGH: ensure PDF always lands under reports/phase5_reports/
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:2415:  1300	  // Codex round 1 MED (2026-04-21): distinguish 404/400 (case not opted-in
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:2537:32:# Codex round 1 HIGH (2026-04-21): enforce exact timestamp shape before
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:2821:   175	    """Codex round 1 HIGH: caller-supplied output_path must stay under reports/phase5_reports/."""
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:2837:    80	    Codex round 1 HIGH: enforce _TIMESTAMP_RE shape on the manifest value so a
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:2869:1. MEDIUM: the new PDF containment path is not fully verified and the PDF endpoints still 500 when WeasyPrint native libs are unavailable. In [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:432), `import weasyprint` runs before the `reports_root` containment check that starts at [line 437](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:437). The route only catches `ImportError` in [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/routes/comparison_report.py:72) and [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/routes/comparison_report.py:95), but on this machine the failure is `OSError`, so both PDF endpoints returned 500 and the new test at [test_comparison_report_service.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparison_report_service.py:174) failed before it ever exercised the containment guard.
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:2871:2. LOW: the original low-severity coverage gap is only partially closed. The new service tests are useful, but the route success-path tests still early-return when artifacts are missing, so CI still does not exercise the HTML/context 200-path route integration. See [test_comparison_report_route.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparison_report_route.py:26) and [test_comparison_report_route.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparison_report_route.py:47).
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:2874:- HIGH: closed in code. Timestamp shape-gating, field-artifact containment, render-path validation, and PDF output containment are present in [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:90), [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:298), [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:344), and mirrored in [render_case_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/scripts/render_case_report.py:77).
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:2875:- MEDIUM: closed in code. The `/learn` surface now hides only 400/404 and shows a visible banner for other failures in [LearnCaseDetailPage.tsx](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1299).
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:2876:- LOW: not fully closed. Service-level unit coverage was added, but route-level success coverage still depends on local artifacts.
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:2888:1. MEDIUM: the new PDF containment path is not fully verified and the PDF endpoints still 500 when WeasyPrint native libs are unavailable. In [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:432), `import weasyprint` runs before the `reports_root` containment check that starts at [line 437](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:437). The route only catches `ImportError` in [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/routes/comparison_report.py:72) and [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/routes/comparison_report.py:95), but on this machine the failure is `OSError`, so both PDF endpoints returned 500 and the new test at [test_comparison_report_service.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparison_report_service.py:174) failed before it ever exercised the containment guard.
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:2890:2. LOW: the original low-severity coverage gap is only partially closed. The new service tests are useful, but the route success-path tests still early-return when artifacts are missing, so CI still does not exercise the HTML/context 200-path route integration. See [test_comparison_report_route.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparison_report_route.py:26) and [test_comparison_report_route.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparison_report_route.py:47).
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:2893:- HIGH: closed in code. Timestamp shape-gating, field-artifact containment, render-path validation, and PDF output containment are present in [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:90), [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:298), [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:344), and mirrored in [render_case_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/scripts/render_case_report.py:77).
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:2894:- MEDIUM: closed in code. The `/learn` surface now hides only 400/404 and shows a visible banner for other failures in [LearnCaseDetailPage.tsx](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1299).
reports/codex_tool_reports/2026-04-21_phase7bc_codex_review_round2.md:2895:- LOW: not fully closed. Service-level unit coverage was added, but route-level success coverage still depends on local artifacts.
reports/codex_tool_reports/m_render_api_arc/round5.log:47:If clean: APPROVE or APPROVE_WITH_COMMENTS.
reports/codex_tool_reports/m_render_api_arc/round5.log:61:Verdict: APPROVE | APPROVE_WITH_COMMENTS | CHANGES_REQUIRED
reports/codex_tool_reports/m_render_api_arc/round5.log:2358:Verdict: APPROVE
reports/codex_tool_reports/m_render_api_arc/round5.log:2371:Verdict: APPROVE
reports/codex_tool_reports/dec_v61_097_phase_1a_round1.md:4:**Verdict**: `Codex-verified: CHANGES_REQUIRED solve-stream preflight/multi-run correctness is unsafe, and /bc/render is missing mesh-render input hardening`
reports/codex_tool_reports/dec_v61_097_phase_1a_round1.md:13:### 1. HIGH — solve-stream preflight is inside generator, returns 200 then breaks
reports/codex_tool_reports/dec_v61_097_phase_1a_round1.md:20:### 2. HIGH — abort/restart race: no run-generation guard, shared container_work_dir
reports/codex_tool_reports/dec_v61_097_phase_1a_round1.md:27:### 3. MED — /bc/render missing /mesh/render symlink-containment hardening
reports/codex_tool_reports/dec_v61_097_phase_1a_round1.md:34:### 4. MED — malformed boundary ranges silently truncated, returns partial 200 GLB
reports/codex_tool_reports/m_render_api_arc/round2.log:18:This is the **Round 2** review. Round 1 returned CHANGES_REQUIRED with 6 findings (2 P1 + 4 P2).
reports/codex_tool_reports/m_render_api_arc/round2.log:104:Verdict: APPROVE | APPROVE_WITH_COMMENTS | CHANGES_REQUIRED
reports/codex_tool_reports/m_render_api_arc/round2.log:107:Be terse. If everything is clean and APPROVE, say so without padding.
reports/codex_tool_reports/m_render_api_arc/round2.log:549:    Codex Round 1 returned CHANGES_REQUIRED with 6 findings (2 P1 + 4 P2);
reports/codex_tool_reports/m_render_api_arc/round2.log:669:    Codex Round 1 returned CHANGES_REQUIRED with 6 findings (2 P1 + 4 P2);
reports/codex_tool_reports/m_render_api_arc/round2.log:847:    Codex Round 1 returned CHANGES_REQUIRED with 6 findings (2 P1 + 4 P2);
reports/codex_tool_reports/m_render_api_arc/round2.log:964:    Codex Round 1 returned CHANGES_REQUIRED with 6 findings (2 P1 + 4 P2);
reports/codex_tool_reports/m_render_api_arc/round2.log:1100:    Codex Round 1 returned CHANGES_REQUIRED with 6 findings (2 P1 + 4 P2);
reports/codex_tool_reports/m_render_api_arc/round2.log:4064:    # (R1 LOW) flagged that 3.1.0-3.1.5 admit versions with published
reports/codex_tool_reports/m_render_api_arc/round2.log:4389:Verdict: CHANGES_REQUIRED
reports/codex_tool_reports/m_render_api_arc/round2.log:4412:Verdict: CHANGES_REQUIRED
reports/codex_tool_reports/m_render_api_arc/README.md:11:| 1 | CHANGES_REQUIRED | 6 (2 P1 · 4 P2) | symlink escape · dead-code fallback · TOCTOU · face-OOB · importer leak · eager bundle |
reports/codex_tool_reports/m_render_api_arc/README.md:12:| 2 | CHANGES_REQUIRED | 5 verified · F3 partial · +F7 P3 (chunk-load) | residual TOCTOU window · chunk-load normalization gap |
reports/codex_tool_reports/m_render_api_arc/README.md:13:| 3 | CHANGES_REQUIRED | F7 verified · F3 still partial | concurrent-reader (replace, unlink) window |
reports/codex_tool_reports/m_render_api_arc/README.md:14:| 4 | CHANGES_REQUIRED | F3 closed BUT regression introduced | `source.stat()` raw `FileNotFoundError` + temp leak |
reports/codex_tool_reports/m_render_api_arc/README.md:15:| 5 | **APPROVE** ✓ | All 7 findings closed · parity verified | merge-ready |
reports/codex_tool_reports/m_render_api_arc/round4.log:49:If everything is clean: APPROVE.
reports/codex_tool_reports/m_render_api_arc/round4.log:63:Verdict: APPROVE | APPROVE_WITH_COMMENTS | CHANGES_REQUIRED
reports/codex_tool_reports/m_render_api_arc/round4.log:2602:Verdict: CHANGES_REQUIRED
reports/codex_tool_reports/m_render_api_arc/round4.log:2615:Verdict: CHANGES_REQUIRED
reports/codex_tool_reports/m_render_api_arc/round3.log:20:Round 2 verdict: CHANGES_REQUIRED. 5 verified, 1 partial, 1 new finding.
reports/codex_tool_reports/m_render_api_arc/round3.log:50:If everything is clean, just say APPROVE. Be terse.
reports/codex_tool_reports/m_render_api_arc/round3.log:65:Verdict: APPROVE | APPROVE_WITH_COMMENTS | CHANGES_REQUIRED
reports/codex_tool_reports/m_render_api_arc/round3.log:1533:Verdict: CHANGES_REQUIRED
reports/codex_tool_reports/m_render_api_arc/round3.log:1546:Verdict: CHANGES_REQUIRED
reports/codex_tool_reports/dec_v61_075_t2_3_post_commit_round2.md:3:- **Verdict**: CHANGES_REQUIRED
reports/codex_tool_reports/20260422_dec045_wave3_F_taskrunner_reorder_result.md:258:CHK-7: Synthetic case with VELOCITY_OVERFLOW in audit_concerns + in-band scalar → expected_verdict="FAIL" (hard-fail takes precedence).
reports/codex_tool_reports/20260422_dec045_wave3_F_taskrunner_reorder_result.md:2065:    # Codex round 1 MED #3: only inject metadata for opted-in cases — other 9
reports/codex_tool_reports/20260422_dec045_wave3_F_taskrunner_reorder_result.md:2084:    # contents (best-effort, must not block audit doc). MED #3 gating above.
reports/codex_tool_reports/20260422_dec045_wave3_F_taskrunner_reorder_result.md:2193:- `ui/backend/services/validation_report.py` (`_derive_contract_status` extension for VELOCITY_OVERFLOW/TURBULENCE_NEGATIVE/CONTINUITY_DIVERGED)
reports/codex_tool_reports/20260422_dec045_wave3_F_taskrunner_reorder_result.md:2240:**Verdict**: APPROVE / APPROVE_WITH_NOTES / CHANGES_REQUIRED / BLOCK
reports/codex_tool_reports/20260422_dec045_wave3_F_taskrunner_reorder_result.md:2265:- Ready for codex_verdict=APPROVED: YES / NO
reports/codex_tool_reports/20260422_dec045_wave3_F_taskrunner_reorder_result.md:2482:**Verdict**: APPROVE / APPROVE_WITH_NOTES / CHANGES_REQUIRED / BLOCK
reports/codex_tool_reports/20260422_dec045_wave3_F_taskrunner_reorder_result.md:2510:- Ready for codex_verdict=APPROVED: YES / NO
reports/codex_tool_reports/20260422_dec045_wave3_F_taskrunner_reorder_result.md:4322:    #   G3  VELOCITY_OVERFLOW           — |U|_max > 100·U_ref
reports/codex_tool_reports/20260422_dec045_wave3_F_taskrunner_reorder_result.md:4333:        "VELOCITY_OVERFLOW",
reports/codex_tool_reports/20260422_dec045_wave3_F_taskrunner_reorder_result.md:4700:tests/test_report_engine/test_report_engine.py:96:        correction_spec={"primary_cause": "mesh_resolution", "confidence": "LOW", "suggested_correction": "Refine"},
reports/codex_tool_reports/20260422_dec045_wave3_F_taskrunner_reorder_result.md:5263:    OR empty. Codex round 1 MED #3 (2026-04-21): require a NON-empty artifact
reports/codex_tool_reports/20260422_dec045_wave3_F_taskrunner_reorder_result.md:11370:    ('fail', [AuditConcern(concern_type='VELOCITY_OVERFLOW', summary='fail')]),
reports/codex_tool_reports/20260422_dec045_wave3_F_taskrunner_reorder_result.md:15932:- `CHK-7` PASS: direct `.venv` `_derive_contract_status` check with `VELOCITY_OVERFLOW` returns `FAIL`.
reports/codex_tool_reports/20260422_dec045_wave3_F_taskrunner_reorder_result.md:16325:- `CHK-7` PASS: direct `.venv` `_derive_contract_status` check with `VELOCITY_OVERFLOW` returns `FAIL`.
reports/codex_tool_reports/m_render_api_arc/round1.log:88:Verdict (canonical trailer): APPROVE | APPROVE_WITH_COMMENTS | CHANGES_REQUIRED
reports/codex_tool_reports/m_render_api_arc/round1.log:370:  v61_094_acceptance: confirmed (M-VIZ closed 2026-04-28 · commit 36c4a78 · Step-7 visual smoke PASSED · Codex APPROVE_WITH_COMMENTS at round 5 + verbatim halt)
reports/codex_tool_reports/m_render_api_arc/round1.log:4422:ui/backend/services/run_ids.py:17:# Codex round 1 HIGH #2 (2026-04-21): traversal via run_id reproduced with
reports/codex_tool_reports/m_render_api_arc/round1.log:4584:ui/backend/tests/test_field_artifacts_route.py:115:    """Codex round 1 HIGH #2: traversal via run_id literal '..' must be rejected."""
reports/codex_tool_reports/m_render_api_arc/round1.log:4585:ui/backend/tests/test_field_artifacts_route.py:127:    """Codex round 1 HIGH #2: manifest endpoint also guards run_id segments."""
reports/codex_tool_reports/m_render_api_arc/round1.log:6245:reports/codex_tool_reports/codex_audit_0208929.log:5682:./reports/codex_tool_reports/2026-04-21_phase7bc_render_report_codex_review.md:4394:1. HIGH — Manifest-derived filesystem paths are trusted without containment checks, and the PDF path makes that trust exploitable. [`comparison_report.py:257`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:257>) takes `run_manifest["timestamp"]` verbatim, [`comparison_report.py:296`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:296>) returns `renders_manifest["outputs"][key]` verbatim, and [`comparison_report.py:376`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:376>) renders the HTML with `base_url=_REPO_ROOT`. That means a tampered `runs/{label}.json` can steer reads outside `reports/phase5_fields`, a tampered renders manifest can point `<img src>` at arbitrary local image/SVG paths for WeasyPrint to load, and [`comparison_report.py:372`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:372>) can write the generated PDF outside `reports/phase5_reports`. The same timestamp trust exists on the render side in [`render_case_report.py:72`](</Users/Zhuanz/Desktop/cfd-harness-unified/scripts/render_case_report.py:72>) and [`render_case_report.py:91`](</Users/Zhuanz/Desktop/cfd-harness-unified/scripts/render_case_report.py:91>). This needs strict segment validation or `resolve()` + root-prefix checks before approval.
reports/codex_tool_reports/m_render_api_arc/round1.log:6246:reports/codex_tool_reports/codex_audit_0208929.log:5684:./reports/codex_tool_reports/2026-04-21_phase7bc_render_report_codex_review.md:4410:1. HIGH — Manifest-derived filesystem paths are trusted without containment checks, and the PDF path makes that trust exploitable. [`comparison_report.py:257`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:257>) takes `run_manifest["timestamp"]` verbatim, [`comparison_report.py:296`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:296>) returns `renders_manifest["outputs"][key]` verbatim, and [`comparison_report.py:376`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:376>) renders the HTML with `base_url=_REPO_ROOT`. That means a tampered `runs/{label}.json` can steer reads outside `reports/phase5_fields`, a tampered renders manifest can point `<img src>` at arbitrary local image/SVG paths for WeasyPrint to load, and [`comparison_report.py:372`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:372>) can write the generated PDF outside `reports/phase5_reports`. The same timestamp trust exists on the render side in [`render_case_report.py:72`](</Users/Zhuanz/Desktop/cfd-harness-unified/scripts/render_case_report.py:72>) and [`render_case_report.py:91`](</Users/Zhuanz/Desktop/cfd-harness-unified/scripts/render_case_report.py:91>). This needs strict segment validation or `resolve()` + root-prefix checks before approval.
reports/codex_tool_reports/m_render_api_arc/round1.log:6349:reports/codex_tool_reports/2026-04-21_phase7bc_render_report_codex_review.md:4394:1. HIGH — Manifest-derived filesystem paths are trusted without containment checks, and the PDF path makes that trust exploitable. [`comparison_report.py:257`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:257>) takes `run_manifest["timestamp"]` verbatim, [`comparison_report.py:296`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:296>) returns `renders_manifest["outputs"][key]` verbatim, and [`comparison_report.py:376`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:376>) renders the HTML with `base_url=_REPO_ROOT`. That means a tampered `runs/{label}.json` can steer reads outside `reports/phase5_fields`, a tampered renders manifest can point `<img src>` at arbitrary local image/SVG paths for WeasyPrint to load, and [`comparison_report.py:372`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:372>) can write the generated PDF outside `reports/phase5_reports`. The same timestamp trust exists on the render side in [`render_case_report.py:72`](</Users/Zhuanz/Desktop/cfd-harness-unified/scripts/render_case_report.py:72>) and [`render_case_report.py:91`](</Users/Zhuanz/Desktop/cfd-harness-unified/scripts/render_case_report.py:91>). This needs strict segment validation or `resolve()` + root-prefix checks before approval.
reports/codex_tool_reports/m_render_api_arc/round1.log:6350:reports/codex_tool_reports/2026-04-21_phase7bc_render_report_codex_review.md:4410:1. HIGH — Manifest-derived filesystem paths are trusted without containment checks, and the PDF path makes that trust exploitable. [`comparison_report.py:257`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:257>) takes `run_manifest["timestamp"]` verbatim, [`comparison_report.py:296`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:296>) returns `renders_manifest["outputs"][key]` verbatim, and [`comparison_report.py:376`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:376>) renders the HTML with `base_url=_REPO_ROOT`. That means a tampered `runs/{label}.json` can steer reads outside `reports/phase5_fields`, a tampered renders manifest can point `<img src>` at arbitrary local image/SVG paths for WeasyPrint to load, and [`comparison_report.py:372`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:372>) can write the generated PDF outside `reports/phase5_reports`. The same timestamp trust exists on the render side in [`render_case_report.py:72`](</Users/Zhuanz/Desktop/cfd-harness-unified/scripts/render_case_report.py:72>) and [`render_case_report.py:91`](</Users/Zhuanz/Desktop/cfd-harness-unified/scripts/render_case_report.py:91>). This needs strict segment validation or `resolve()` + root-prefix checks before approval.
reports/codex_tool_reports/m_render_api_arc/round1.log:7140:.planning/decisions/2026-04-21_phase7a_field_capture.md:37:  - HIGH: list_artifacts() didn't validate manifest timestamp before enumerating — timestamp='../../outside' caused list to hash files outside reports/phase5_fields/. FIXED by extracting _resolve_artifact_dir() shared helper with _TIMESTAMP_RE = r'^\d{8}T\d{6}Z$' shape gate; both list and download paths now route through it.
reports/codex_tool_reports/m_render_api_arc/round1.log:7166:.planning/decisions/2026-04-21_phase7bc_render_and_report.md:34:  - HIGH: Manifest-derived filesystem paths (timestamp + renders outputs + PDF output_path) trusted without containment — tampered runs/{label}.json or renders manifest could steer reads outside reports/phase5_fields/, WeasyPrint base_url could pull arbitrary images into PDF, PDF writes could escape reports/phase5_reports/.
reports/codex_tool_reports/m_render_api_arc/round1.log:7385:# Codex round 2 HIGH (2026-04-21): timestamp shape gate. The manifest is
reports/codex_tool_reports/m_render_api_arc/round1.log:7420:# Codex round 1 LOW #4 (2026-04-21): use st_mtime_ns (int) not st_mtime (float)
reports/codex_tool_reports/m_render_api_arc/round1.log:7474:    Codex round 2 HIGH (2026-04-21): previously the LIST endpoint read
reports/codex_tool_reports/m_render_api_arc/round1.log:7529:    # Codex round 1 HIGH #1 (2026-04-21): use POSIX relative path as filename
reports/codex_tool_reports/m_render_api_arc/round1.log:7569:    after Codex round 1 HIGH #1 fix. Traversal defense:
reports/codex_tool_reports/m_render_api_arc/round1.log:9045:    24	# Codex round 2 HIGH (2026-04-21): timestamp shape gate. The manifest is
reports/codex_tool_reports/m_render_api_arc/round1.log:9080:    59	# Codex round 1 LOW #4 (2026-04-21): use st_mtime_ns (int) not st_mtime (float)
reports/codex_tool_reports/m_render_api_arc/round1.log:9134:   113	    Codex round 2 HIGH (2026-04-21): previously the LIST endpoint read
reports/codex_tool_reports/m_render_api_arc/round1.log:9189:   168	    # Codex round 1 HIGH #1 (2026-04-21): use POSIX relative path as filename
reports/codex_tool_reports/m_render_api_arc/round1.log:10175:Verdict (canonical trailer): CHANGES_REQUIRED
reports/codex_tool_reports/m_render_api_arc/round1.log:10215:Verdict (canonical trailer): CHANGES_REQUIRED

codex
I’ve confirmed the target files and the existing verdict style. Next I’m reading the exact staging block, the new regression test, and the surrounding run-id / cleanup code to see whether the fix is merely syntactically right or actually safe under the existing concurrency model.
exec
/bin/zsh -lc "nl -ba ui/backend/services/case_solve/solver_streamer.py | sed -n '240,380p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
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
   295	            container.exec_run(
   296	                cmd=[
   297	                    "bash",
   298	                    "-c",
   299	                    f"mkdir -p {CONTAINER_WORK_BASE} && chmod 777 {CONTAINER_WORK_BASE}",
   300	                ]
   301	            )
   302	            ok = container.put_archive(
   303	                path=CONTAINER_WORK_BASE,
   304	                data=_make_tarball(case_host_dir),
   305	            )
   306	            if not ok:
   307	                raise SolverRunError(
   308	                    "failed to stage case for streaming icoFoam"
   309	                )
   310	            # Atomically rename the extracted dir into the run_id-suffixed
   311	            # name. run_id is unique per run so the destination cannot
   312	            # collide with an in-flight peer; defensively `rm -rf` first
   313	            # to clear any orphan from a prior abandoned run whose
   314	            # finally cleanup didn't run (process kill, container restart).
   315	            container.exec_run(
   316	                cmd=[
   317	                    "bash",
   318	                    "-c",
   319	                    f"rm -rf {container_work_dir} && "
   320	                    f"mv {CONTAINER_WORK_BASE}/{case_id} {container_work_dir} && "
   321	                    f"chmod 777 {container_work_dir}",
   322	                ]
   323	            )
   324	        except docker.errors.DockerException as exc:
   325	            raise SolverRunError(
   326	                f"docker SDK error preparing container workspace: {exc}"
   327	            ) from exc
   328	
   329	        # Spawn icoFoam. ``stdbuf -oL`` line-buffers stdout so PISO
   330	        # iterations arrive promptly instead of in 4KB chunks.
   331	        bash_cmd = (
   332	            "source /opt/openfoam10/etc/bashrc && "
   333	            f"cd {container_work_dir} && "
   334	            "stdbuf -oL -eL icoFoam 2>&1"
   335	        )
   336	        try:
   337	            exec_result = container.exec_run(
   338	                cmd=["bash", "-c", bash_cmd],
   339	                stream=True,
   340	                demux=False,
   341	            )
   342	        except docker.errors.DockerException as exc:
   343	            raise SolverRunError(f"docker SDK error invoking icoFoam: {exc}") from exc
   344	    except BaseException:
   345	        # Any failure during preflight releases the lock so the user
   346	        # can retry. The generator path takes ownership of the lock
   347	        # release on its own try/finally.
   348	        _release_run(case_id, run_id)
   349	        raise
   350	
   351	    return _PreparedStream(
   352	        case_host_dir=case_host_dir,
   353	        run_id=run_id,
   354	        container=container,
   355	        container_work_dir=container_work_dir,
   356	        exec_result=exec_result,
   357	    )
   358	
   359	
   360	def stream_icofoam(
   361	    *,
   362	    case_host_dir: Path | None = None,
   363	    container_name: str = CONTAINER_NAME,
   364	    prepared: _PreparedStream | None = None,
   365	) -> Iterator[bytes]:
   366	    """Run icoFoam with streamed output. Yields SSE-formatted bytes
   367	    that an EventSource client can consume directly.
   368	
   369	    Two call shapes:
   370	
   371	    * ``stream_icofoam(prepared=<_PreparedStream>)`` — preferred path
   372	      used by the route. Preflight has already happened in
   373	      :func:`_prepare_stream_icofoam`; this function only consumes the
   374	      already-spawned exec result.
   375	    * ``stream_icofoam(case_host_dir=...)`` — legacy entrypoint kept
   376	      for tests + the blocking variant's parity. Internally calls
   377	      ``_prepare_stream_icofoam`` then delegates.
   378	
   379	    The first SSE event is always ``start`` with ``{"run_id": ...}``
   380	    so the frontend can stamp every subsequent state-write with the

exec
/bin/zsh -lc "nl -ba ui/backend/services/case_solve/solver_streamer.py | sed -n '1,120p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
     1	"""Streaming variant of :mod:`solver_runner` for live UI feedback.
     2	
     3	The blocking ``run_icofoam`` waits ~60s before returning a single
     4	SolveSummary. The user reported (2026-04-29) that watching a spinner
     5	for 60s with no feedback is unacceptable — Step 4 should "实时监控
     6	求解器的残差图". This module runs icoFoam with
     7	``container.exec_run(stream=True)`` so log lines arrive incrementally;
     8	each parseable line becomes an SSE event the UI can consume.
     9	
    10	Protocol (one event per parseable line, plus a final summary):
    11	
    12	* ``time``       — start of a new PISO timestep. ``{"t": 0.005}``
    13	* ``residual``   — one solver-iteration residual line.
    14	                   ``{"field": "p"|"Ux"|"Uy"|"Uz", "init": 0.5,
    15	                       "final": 0.001, "iters": 21, "t": 0.005}``
    16	* ``continuity`` — PISO continuity-error closing line.
    17	                   ``{"sum_local": 1e-6, "global": 1e-19, "t": 0.005}``
    18	* ``done``       — end of run. ``{"converged": true, ...SolveSummary}``
    19	* ``error``      — fatal error mid-run. ``{"detail": "..."}``
    20	
    21	This stream-based design also dovetails with the SSE frontend: the
    22	React component subscribes via ``EventSource`` and renders a live
    23	chart instead of waiting for a static PNG render at the end.
    24	"""
    25	from __future__ import annotations
    26	
    27	import io
    28	import json
    29	import re
    30	import secrets
    31	import shutil
    32	import tarfile
    33	import threading
    34	from collections.abc import Iterator
    35	from dataclasses import dataclass
    36	from pathlib import Path
    37	from typing import Any
    38	
    39	from ui.backend.services.meshing_gmsh.to_foam import (
    40	    CONTAINER_NAME,
    41	    CONTAINER_WORK_BASE,
    42	    _extract_tarball,
    43	    _make_tarball,
    44	)
    45	
    46	
    47	# Reuse parsers from solver_runner so the SSE summary at the end
    48	# matches what the blocking endpoint would have returned.
    49	from .solver_runner import (
    50	    SolverRunError,
    51	    SolverRunResult,
    52	    _is_converged,
    53	    _parse_log,
    54	)
    55	
    56	
    57	class SolveAlreadyRunning(SolverRunError):
    58	    """Raised when a prior solve for the same case_id is still active.
    59	
    60	    Codex round-1 HIGH-2: prior to the run_id system, a navigate-away
    61	    or remount could leave run A's icoFoam alive while run B started
    62	    in the same container_work_dir; both runs would race on
    63	    log.icoFoam and the time directories. Now the route returns 409
    64	    when this happens and the user retries after the prior run exits.
    65	    """
    66	
    67	
    68	# Codex round-1 HIGH-2: per-case lock so concurrent solves cannot
    69	# share container_work_dir + log path. Sync threading lock is
    70	# appropriate because FastAPI runs the sync generator in a worker
    71	# thread (StreamingResponse iterates the generator from the worker).
    72	_runs_lock = threading.Lock()
    73	_active_runs: dict[str, str] = {}  # case_id → run_id
    74	
    75	
    76	def _claim_run(case_id: str) -> str:
    77	    """Allocate a run_id for ``case_id``; raise if one is already in flight."""
    78	    with _runs_lock:
    79	        if case_id in _active_runs:
    80	            raise SolveAlreadyRunning(
    81	                f"solve already running for case {case_id!r} "
    82	                f"(run_id={_active_runs[case_id]})"
    83	            )
    84	        run_id = secrets.token_hex(6)  # 12-char hex, plenty for collision-free
    85	        _active_runs[case_id] = run_id
    86	    return run_id
    87	
    88	
    89	def _release_run(case_id: str, run_id: str) -> None:
    90	    """Drop the in-flight registration. Idempotent if run_id mismatches."""
    91	    with _runs_lock:
    92	        if _active_runs.get(case_id) == run_id:
    93	            del _active_runs[case_id]
    94	
    95	
    96	# Line-level patterns (single-line variants of solver_runner regexes).
    97	_TIME_LINE = re.compile(r"^Time\s*=\s*([0-9.eE+-]+)s?\s*$")
    98	_RES_U_LINE = re.compile(
    99	    r"smoothSolver:\s+Solving for U([xyz]),\s+Initial residual\s*=\s*"
   100	    r"([0-9.eE+-]+),\s+Final residual\s*=\s*([0-9.eE+-]+),\s+"
   101	    r"No Iterations\s+(\d+)"
   102	)
   103	_RES_P_LINE = re.compile(
   104	    r"DICPCG:\s+Solving for p,\s+Initial residual\s*=\s*"
   105	    r"([0-9.eE+-]+),\s+Final residual\s*=\s*([0-9.eE+-]+),\s+"
   106	    r"No Iterations\s+(\d+)"
   107	)
   108	_CONT_LINE = re.compile(
   109	    r"time step continuity errors\s*:\s*sum local\s*=\s*"
   110	    r"([0-9.eE+-]+),\s+global\s*=\s*([0-9.eE+-]+)"
   111	)
   112	_FOAM_FATAL = re.compile(r"^--> FOAM FATAL ERROR")
   113	
   114	
   115	def _sse(event: str, data: dict[str, Any]) -> bytes:
   116	    """Format an SSE message. Each event has its own ``event:`` line so
   117	    EventSource clients can subscribe to specific event types.
   118	    """
   119	    payload = json.dumps(data, separators=(",", ":"))
   120	    return f"event: {event}\ndata: {payload}\n\n".encode("utf-8")

exec
/bin/zsh -lc "nl -ba ui/backend/services/case_solve/solver_streamer.py | sed -n '380,570p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   380	    so the frontend can stamp every subsequent state-write with the
   381	    matching run generation (HIGH-2 frontend half).
   382	
   383	    Failures DURING the run land as in-stream ``error`` events; the
   384	    HTTP status stays 200 because the stream has already started.
   385	    """
   386	    if prepared is None:
   387	        if case_host_dir is None:
   388	            raise TypeError(
   389	                "stream_icofoam requires either prepared= or case_host_dir="
   390	            )
   391	        prepared = _prepare_stream_icofoam(
   392	            case_host_dir=case_host_dir, container_name=container_name
   393	        )
   394	
   395	    case_host_dir = prepared.case_host_dir
   396	    run_id = prepared.run_id
   397	    container = prepared.container
   398	    container_work_dir = prepared.container_work_dir
   399	    exec_result = prepared.exec_result
   400	
   401	    # Lazy-import docker.errors for the catch blocks below; the
   402	    # ImportError path is unreachable here because preflight succeeded.
   403	    import docker.errors  # type: ignore[import-not-found]
   404	
   405	    # Buffer + line-by-line parse + accumulate full log on host.
   406	    log_dest = case_host_dir / "log.icoFoam"
   407	    log_buf = io.BytesIO()
   408	    line_buf = b""
   409	    current_time: list[float | None] = [None]
   410	    last_p: list[float | None] = [None]
   411	    fatal_seen: list[bool] = [False]
   412	
   413	    # Codex rounds 2 & 3: wrap the ENTIRE generator body (including the
   414	    # very first `start` yield) in an outer try/finally so a
   415	    # GeneratorExit raised at ANY yield point — client disconnect on
   416	    # the first event, FastAPI shutdown, mid-stream abort — releases
   417	    # the per-case run lock and cleans up the container work dir.
   418	    # Round 2 fixed the mid-loop case; round 3 caught that the start
   419	    # yield was still OUTSIDE the try, so an immediate disconnect after
   420	    # the very first SSE byte was still leaking _active_runs.
   421	    try:
   422	        # FIRST event: announce the run_id so the frontend can guard
   423	        # state writes against stale runs. MUST stay inside the outer
   424	        # try so a GeneratorExit on this yield still hits the finally.
   425	        yield _sse("start", {"run_id": run_id, "case_id": case_host_dir.name})
   426	
   427	        # Stream icoFoam output line-by-line.
   428	        try:
   429	            for chunk in exec_result.output:
   430	                if not chunk:
   431	                    continue
   432	                log_buf.write(chunk)
   433	                # Append chunk to the line buffer, split on \n, parse
   434	                # each complete line. The trailing partial line stays
   435	                # in the buffer for the next chunk.
   436	                line_buf += chunk
   437	                while b"\n" in line_buf:
   438	                    raw_line, _, line_buf = line_buf.partition(b"\n")
   439	                    try:
   440	                        line_str = raw_line.decode("utf-8", errors="replace")
   441	                    except Exception:  # noqa: BLE001
   442	                        continue
   443	                    yield from _parse_line_to_events(
   444	                        line_str,
   445	                        current_time=current_time,
   446	                        last_p=last_p,
   447	                        fatal_seen=fatal_seen,
   448	                    )
   449	        except Exception as exc:  # noqa: BLE001 — stream interruption
   450	            yield _sse("error", {"detail": f"stream interrupted: {exc}"})
   451	            # Don't re-raise — let the done event below close the
   452	            # stream cleanly; the client will see error then
   453	            # done(converged=false).
   454	
   455	        # Flush the trailing partial line.
   456	        if line_buf:
   457	            try:
   458	                line_str = line_buf.decode("utf-8", errors="replace")
   459	                yield from _parse_line_to_events(
   460	                    line_str,
   461	                    current_time=current_time,
   462	                    last_p=last_p,
   463	                    fatal_seen=fatal_seen,
   464	                )
   465	            except Exception:  # noqa: BLE001
   466	                pass
   467	
   468	        # Persist the full log on the host so downstream tools (the
   469	        # /residual-history.png renderer, the audit package, etc) can
   470	        # read it.
   471	        try:
   472	            log_dest.write_bytes(log_buf.getvalue())
   473	        except OSError as exc:
   474	            yield _sse(
   475	                "error",
   476	                {"detail": f"failed to persist log on host: {exc}"},
   477	            )
   478	
   479	        # Pull time directories back for the results extractor.
   480	        pulled: list[str] = []
   481	        try:
   482	            ls_out = container.exec_run(
   483	                cmd=[
   484	                    "bash",
   485	                    "-c",
   486	                    f"cd {container_work_dir} && ls -d [0-9]* 2>/dev/null",
   487	                ]
   488	            )
   489	            time_dirs_raw = ls_out.output.decode(errors="replace").strip().split()
   490	            for td in time_dirs_raw:
   491	                try:
   492	                    bits, _ = container.get_archive(f"{container_work_dir}/{td}")
   493	                    _extract_tarball(b"".join(bits), case_host_dir)
   494	                    pulled.append(td)
   495	                except docker.errors.DockerException:
   496	                    continue
   497	        except docker.errors.DockerException as exc:
   498	            yield _sse(
   499	                "error",
   500	                {"detail": f"docker SDK error pulling time dirs: {exc}"},
   501	            )
   502	        except (OSError, tarfile.TarError) as exc:
   503	            yield _sse(
   504	                "error",
   505	                {"detail": f"host fault pulling time dirs: {exc}"},
   506	            )
   507	
   508	        # Final summary event — mirrors SolverRunResult shape.
   509	        parsed = _parse_log(log_buf.getvalue().decode("utf-8", errors="replace"))
   510	        converged = _is_converged(parsed) and not fatal_seen[0]
   511	        summary = {
   512	            "case_id": case_host_dir.name,
   513	            "end_time_reached": float(parsed["end_time_reached"]),
   514	            "last_initial_residual_p": parsed["p"],
   515	            "last_initial_residual_U": [
   516	                parsed["Ux"],
   517	                parsed["Uy"],
   518	                parsed["Uz"],
   519	            ],
   520	            "last_continuity_error": parsed["continuity"],
   521	            "n_time_steps_written": len(pulled),
   522	            "time_directories": sorted(pulled, key=lambda s: float(s)),
   523	            "wall_time_s": float(parsed["wall_clock"]),
   524	            "converged": converged,
   525	        }
   526	        yield _sse("done", summary)
   527	    finally:
   528	        # Always release the per-case run lock and (best-effort) clean
   529	        # up the container work dir, even on GeneratorExit (client
   530	        # disconnect mid-stream) or any other exception above.
   531	        _release_run(case_host_dir.name, run_id)
   532	        try:
   533	            container.exec_run(
   534	                cmd=["bash", "-c", f"rm -rf {container_work_dir}"]
   535	            )
   536	        except Exception:  # noqa: BLE001 — best-effort cleanup
   537	            pass

exec
/bin/zsh -lc "nl -ba ui/backend/tests/test_solver_streamer.py | sed -n '220,360p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   220	def test_run_id_suffixes_container_work_dir(tmp_path, monkeypatch):
   221	    """The container_work_dir must be run_id-suffixed so concurrent
   222	    abandoned runs cannot collide on log.icoFoam or time directories.
   223	    """
   224	    from ui.backend.services.case_solve import solver_streamer
   225	    from ui.backend.services.case_solve.solver_streamer import (
   226	        _active_runs,
   227	        _prepare_stream_icofoam,
   228	        _release_run,
   229	    )
   230	
   231	    case_dir = tmp_path / "case_suffix"
   232	    case_dir.mkdir()
   233	    _stage_minimal_case(case_dir)
   234	    container = _FakeContainer(status="running", exec_lines=[])
   235	    _install_fake_docker(monkeypatch, container)
   236	
   237	    # Use a fixed run_id so the assertion is deterministic.
   238	    forced_run_id = "deadbeefcafe"
   239	    try:
   240	        prepared = _prepare_stream_icofoam(
   241	            case_host_dir=case_dir, run_id=forced_run_id
   242	        )
   243	        assert prepared.run_id == forced_run_id
   244	        assert prepared.container_work_dir.endswith(
   245	            f"case_suffix-{forced_run_id}"
   246	        )
   247	    finally:
   248	        _release_run("case_suffix", forced_run_id)
   249	    assert "case_suffix" not in _active_runs
   250	
   251	
   252	# ────────── Post-R3 live-run defect (DEC-V61-099): staging order ──────────
   253	
   254	
   255	def test_staging_renames_extracted_dir_into_run_id_suffix(tmp_path, monkeypatch):
   256	    """Post-R3 live-run defect (DEC-V61-099 · caught on first LDC dogfood
   257	    after V61-097 R4 RESOLVED). The V61-097 round-1 HIGH-2 fix introduced
   258	    a run_id-suffixed container_work_dir but the staging sequence
   259	    silently bypassed the rename:
   260	
   261	      1. ``mkdir -p {container_work_dir}``  ← suffix dir pre-created
   262	      2. ``put_archive(path={CONTAINER_WORK_BASE})``  ← extracts as
   263	         ``{BASE}/{case_id}`` (un-suffixed)
   264	      3. ``if [ -d {BASE}/{case_id} ] && [ ! -d {container_work_dir} ];
   265	            then mv ... fi``  ← guard FALSE because step 1 just created
   266	            the suffix dir → ``mv`` SKIPPED → suffix dir stays empty
   267	
   268	    icoFoam then ``cd``'d into the empty suffix dir and FOAM-Fatal'd
   269	    on missing ``system/controlDict``.
   270	
   271	    Codex's static review missed this in V61-097 because the staging
   272	    test (``test_run_id_suffixes_container_work_dir``) only asserted the
   273	    PATH STRING and the mock ``put_archive`` returned True without
   274	    simulating actual extract. This test pins the failure mode by
   275	    tracking the bash command sequence.
   276	
   277	    Per RETRO-V61-053 addendum: this is the ``executable_smoke_test``
   278	    risk-flag class — runtime-emergent, not visible to static review.
   279	    """
   280	    from ui.backend.services.case_solve.solver_streamer import (
   281	        _prepare_stream_icofoam,
   282	        _release_run,
   283	    )
   284	
   285	    case_dir = tmp_path / "case_staging_regression"
   286	    case_dir.mkdir()
   287	    _stage_minimal_case(case_dir)
   288	
   289	    # Track every bash command sent to exec_run so we can assert the
   290	    # staging sequence is correct.
   291	    bash_commands: list[str] = []
   292	
   293	    class TrackingContainer(_FakeContainer):
   294	        def exec_run(self, cmd, stream=False, demux=False):  # noqa: ARG002
   295	            if isinstance(cmd, list) and len(cmd) >= 3 and cmd[0] == "bash":
   296	                bash_commands.append(cmd[2])
   297	            return super().exec_run(cmd, stream=stream, demux=demux)
   298	
   299	    container = TrackingContainer(status="running", exec_lines=[])
   300	    _install_fake_docker(monkeypatch, container)
   301	
   302	    forced_run_id = "regtest9999"
   303	    suffix_path_fragment = f"case_staging_regression-{forced_run_id}"
   304	    try:
   305	        prepared = _prepare_stream_icofoam(
   306	            case_host_dir=case_dir, run_id=forced_run_id
   307	        )
   308	        assert prepared.container_work_dir.endswith(suffix_path_fragment)
   309	    finally:
   310	        _release_run("case_staging_regression", forced_run_id)
   311	
   312	    # Assertion 1: there is exactly ONE mkdir command before put_archive,
   313	    # and it must NOT pre-create the run_id-suffixed dir (the buggy
   314	    # version did, which is what neutered the subsequent mv).
   315	    mkdir_cmds = [c for c in bash_commands if "mkdir -p" in c]
   316	    assert mkdir_cmds, "expected at least one mkdir during staging"
   317	    pre_archive_mkdirs = [
   318	        c for c in mkdir_cmds if suffix_path_fragment in c
   319	    ]
   320	    assert not pre_archive_mkdirs, (
   321	        f"REGRESSION: staging pre-created the run_id-suffixed dir via "
   322	        f"mkdir -p — this is the V61-099 bug because the subsequent mv "
   323	        f"is silently skipped under the [ ! -d suffix ] guard. "
   324	        f"Offending command(s): {pre_archive_mkdirs}"
   325	    )
   326	
   327	    # Assertion 2: the rename of the extracted {case_id} dir into the
   328	    # run_id-suffixed name must be UNCONDITIONAL (no [ ! -d ] guard
   329	    # against the suffix dir, since under V61-099 the suffix dir does
   330	    # not pre-exist for the same-run claim).
   331	    mv_cmds = [c for c in bash_commands if " mv " in c and suffix_path_fragment in c]
   332	    assert mv_cmds, (
   333	        f"expected an `mv` command renaming the extracted dir into "
   334	        f"the run_id-suffixed name; got commands: {bash_commands}"
   335	    )
   336	    for mv in mv_cmds:
   337	        assert "[ ! -d" not in mv, (
   338	            f"REGRESSION: rename guarded by [ ! -d {{suffix_dir}} ] — "
   339	            f"this is what allowed V61-099 to silently skip the rename "
   340	            f"after the (now-removed) pre-create mkdir. mv command: {mv!r}"
   341	        )
   342	
   343	
   344	# ────────── Codex round-2 R2.1: GeneratorExit must release the lock ──────────
   345	
   346	
   347	def test_generator_close_releases_run_id_after_first_yield(
   348	    tmp_path, monkeypatch
   349	):
   350	    """Codex round-3 finding: closing the generator IMMEDIATELY after
   351	    the first `start` SSE — without ever entering the streaming loop —
   352	    used to bypass the outer try/finally because the start yield was
   353	    OUTSIDE it. Round 3 moved the yield inside; this test pins down
   354	    the exact failure mode Codex flagged.
   355	    """
   356	    from ui.backend.services.case_solve.solver_streamer import (
   357	        _active_runs,
   358	        _prepare_stream_icofoam,
   359	        stream_icofoam,
   360	    )

exec
/bin/zsh -lc "sed -n '1,120p' reports/codex_tool_reports/dec_v61_097_phase_1a_round1.md && printf '\\n---\\n' && sed -n '1,120p' reports/codex_tool_reports/dec_v61_097_phase_1a_round4.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
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

---
# Codex pre-merge review · DEC-V61-097 Phase-1A · Round 4 (closure)

**Date**: 2026-04-29
**Verdict**: `Codex-verified: RESOLVED round-3 HIGH closed; no regression found in reviewed slice`
**Tokens**: 46,868 (terse round-4 confirmation per RETRO-V61-001 verbatim-exception path)
**Account**: mahbubaamyrss@gmail.com (plus, 84% pre-run)
**Commits reviewed**: round-3 closure commit `f3809fc` on top of arc `001f778..fa5d98f → d657bed → 3ddc098 → f3809fc`

---

## Codex's confirmation

> No findings. `solver_streamer.py:415` now puts the `start` yield inside the outer `try`, and the `finally` block at `:521` now covers `GeneratorExit` on that first yield. `test_solver_streamer.py:255` consumes exactly one `start` event and then `gen.close()`, so it hits the previously missed failure mode; the renamed mid-loop test remains complementary. I found no other `yield` points in `stream_icofoam()` outside the outer `try`.

> Codex-verified: RESOLVED round-3 HIGH closed; no regression found in reviewed slice

## Arc summary

The DEC-V61-097 Phase-1A LDC end-to-end demo arc went through 4 Codex rounds before closure:

| Round | Verdict | Findings | Closure commit |
|-------|---------|----------|----------------|
| 1 | CHANGES_REQUIRED | 4 (2 HIGH preflight + run_id, 2 MED bc_glb hardening) | `d657bed` |
| 2 | CHANGES_REQUIRED | 3 (HIGH GeneratorExit leak, MED cache-hit bypass, LOW boundary rename) | `3ddc098` |
| 3 | CHANGES_REQUIRED | 1 (HIGH start yield outside outer try) | `f3809fc` |
| 4 | **RESOLVED** | 0 | this commit |

## Files in this round

- `ui/backend/services/case_solve/solver_streamer.py` — start yield moved inside outer try/finally
- `ui/backend/tests/test_solver_streamer.py` — split into `_after_first_yield` + `_mid_loop` tests; the new test pins down the exact failure mode round 2 missed

## Test coverage (after full arc)

- `test_bc_glb.py` — 12 tests (incl. symlink rejection, parse_error, cache-hit symlink rejection, empty boundary)
- `test_solver_streamer.py` — 8 tests (incl. preflight raises before yield, run_id collision, mid-loop GeneratorExit, immediate-yield GeneratorExit)
- `test_mesh_wireframe.py` — 25 tests (existing)
- `test_field_sample.py` — 20 tests (existing)
- Total: 65/65 backend; 103/103 frontend

## Self-pass-rate calibration (per RETRO-V61-001)

DEC-V61-097 self-estimated 55% pre-Codex. Actual: needed 4 rounds before APPROVE/RESOLVED. Calibration drift = -55% (4 rounds vs. predicted ≤2). Logging in next retrospective per the methodology.

The arc-size recommendation worked: each round's findings were progressively narrower (4 → 3 → 1 → 0), and the verbatim-exception path was used in round 4 (single-finding, ≤8 LOC, no API change).

exec
/bin/zsh -lc "git show --stat --oneline --decorate=short HEAD && echo '---' && git show --unified=60 --no-ext-diff --no-color HEAD -- ui/backend/services/case_solve/solver_streamer.py ui/backend/tests/test_solver_streamer.py .planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
972fc4f (HEAD -> main) docs(strategic): workbench long-horizon roadmap proposal v1
 ...6-04-29_v61_099_phase_1a_post_r3_staging_fix.md | 224 ++++++++++
 .../workbench_long_horizon_roadmap_2026-04-29.md   | 458 +++++++++++++++++++++
 ui/backend/services/case_solve/solver_streamer.py  |  32 +-
 ui/backend/tests/test_solver_streamer.py           |  92 +++++
 4 files changed, 793 insertions(+), 13 deletions(-)
---
commit 972fc4fd2c3a097dbcf77b8719cdd633ad42136e
Author: claude-opus47-app <claude-opus47-app@anthropic.com>
Date:   Wed Apr 29 15:44:13 2026 +0800

    docs(strategic): workbench long-horizon roadmap proposal v1
    
    Single-user CFD automation workbench with self-evolution as
    strategic centerpiece. Proposes 14 milestones (M9-M22) across 3
    eras after Charter Addendum 3 §4.c (M-VIZ → M-RENDER-API →
    M-PANELS → M-AI-COPILOT → M7 → M8) closes.
    
    CFDJerry direction 2026-04-29: "暂时不考虑成熟SaaS，先作为单用户的
    CFD自动化工作台...能配合人类工程师完成任意的简单3D几何的全流程仿真
    设置、仿真、后处理、归档、学习…这样整个项目就可以运转起来了，真正
    意义上获得了自进化能力"
    
    Era 1 LOOP SPINE (M9-M14): any simple 3D geom end-to-end
    - M9 Tier-B AI · M10 STEP/IGES · M11 Mesh Wizard · M12 Multi-physics
    - M13 Post-processing v1 · M14 Auto V&V (TrustGate per-run + GCI)
    
    Era 2 ARCHIVE+LEARN (M15-M18): the strategic differentiator
    - M15 P4 KO integration (CaseProfile + SimulationObject +
      ExecutionArtifacts + Provenance emit per workbench run)
    - M16 FailurePattern · M17 CorrectionPattern · M18 Similarity
    
    Era 3 ENGINEER EFFICIENCY (M19-M22): per-case friction reduction
    - M19 Recipe library · M20 Comparison view · M21 Re-run on geom Δ
    - M22 LLM dialog + engineer journal (Pivot Charter §1 P3+)
    
    Explicitly DROPPED: SaaS · multi-tenancy · cloud bursting · DOE ·
    adjoint optimization · plugin marketplace · workbench-as-library.
    
    Critical path: Era 1 closes the loop for one case at a time;
    Era 2 enables self-evolution; Era 3 maximizes engineer efficiency.
    Minimum viable self-evolving system = Era 1 + M15 + M16 + M18
    (skip M17, skip Era 3) ≈ 10 milestones, ~6 months at V61-097 pace.
    
    Status: PROPOSAL · Counter NOT incremented (planning artifact, not a
    DEC). Each milestone becomes its own kickoff DEC at startup
    (V61-094/095/096/098 pattern). M9 kickoff sequenced after
    M-AI-COPILOT closes (~2026-05-12).
    
    Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>

diff --git a/.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md b/.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md
new file mode 100644
index 0000000..77d496a
--- /dev/null
+++ b/.planning/decisions/2026-04-29_v61_099_phase_1a_post_r3_staging_fix.md
@@ -0,0 +1,224 @@
+---
+decision_id: DEC-V61-099
+title: M-PANELS Phase-1A · post-R3 live-run defect closure — solver_streamer staging order regression (V61-097 R1 HIGH-2 interaction)
+status: Active (2026-04-29 · post-R3 live-run defect per RETRO-V61-053 addendum methodology · Codex pre-merge mandatory per RETRO-V61-001 "OpenFOAM solver 报错修复" trigger · CFDJerry caught on first LDC dogfood after V61-097 R4 RESOLVED commit `c49fd11`)
+authored_by: Claude Code Opus 4.7 (1M context)
+authored_at: 2026-04-29
+authored_under: V61-097 closure arc · post-R3 defect class per RETRO-V61-053 addendum
+parent_decisions:
+  - DEC-V61-097 (M-PANELS Phase-1A LDC end-to-end demo · closed 2026-04-29 commit c49fd11 · Codex 4-round arc RESOLVED · this DEC closes a DEFECT INTRODUCED IN ROUND 1 of that arc)
+  - RETRO-V61-001 (risk-tier triggers · OpenFOAM solver bug fix mandates Codex pre-merge)
+  - RETRO-V61-053 addendum (post-R3 live-run defect methodology · executable_smoke_test risk-flag class)
+parent_artifacts:
+  - reports/codex_tool_reports/dec_v61_097_phase_1a_round1.md (round 1 verdict where the buggy fix originated)
+  - reports/codex_tool_reports/dec_v61_097_phase_1a_round4.md (round 4 RESOLVED · static review missed the runtime defect)
+implementation_paths:
+  - ui/backend/services/case_solve/solver_streamer.py (MODIFIED · staging order at lines 284-321 · pre-create BASE only · unconditional mv with rm -rf guard)
+  - ui/backend/tests/test_solver_streamer.py (MODIFIED · NEW test_staging_renames_extracted_dir_into_run_id_suffix regression test · tracks bash command sequence)
+notion_sync_status: pending
+autonomous_governance: true
+codex_review_required: true
+codex_review_phase: pre-merge (RETRO-V61-001 "OpenFOAM solver 报错修复" trigger · post-R3 defect raises stakes)
+codex_triggers:
+  - OpenFOAM solver 报错修复 (FOAM Fatal Error: cannot find file system/controlDict)
+  - Phase E2E 批量测试中超过 3 个 case 连续失败 — N/A (single-case dogfood failure but post-R3 elevates priority)
+  - solver_streamer.py modification > 5 LOC
+kogami_review:
+  required: false
+  rationale: |
+    Post-R3 closure of a defect within an already-Codex-blessed arc.
+    Per V61-094 P2 #1 bounding clause (Accepted 2026-04-28): no
+    charter modification, no line-A extension, counter <20 since
+    RETRO-V61-005, no risk-tier change. Self-check 4 conditions all NO.
+break_freeze_required: true
+break_freeze_rationale: |
+  Bug fix to V61-097 BREAK_FREEZE'd code (slot 2/3 already consumed
+  by V61-096 + V61-097 arc). This fix RIDES UNDER V61-097's existing
+  BREAK_FREEZE — does NOT consume new quota. Per Pivot Charter
+  Addendum 3 §5: bug fixes within an Accepted arc do not consume
+  fresh slots. Quota count: still 2/3 → 3/3 after M-AI-COPILOT
+  arc closes (this DEC does not change the projection).
+self_estimated_pass_rate: 80
+self_estimated_pass_rate_calibration: |
+  Higher than typical (V61-097 was 55%) because:
+  - Fix is structurally simple: mkdir BASE only + unconditional mv +
+    defensive rm -rf. ≤15 LOC.
+  - Regression test pins the exact failure mode by tracking bash
+    command sequence — Codex can verify the test catches the bug
+    by examining the assertions.
+  - No new public API. No new dependency. No cross-track contract.
+  - The 5-condition verbatim-exception path FAILS (this is a NEW
+    finding not derived from a Codex round, condition 1 fails;
+    PR body cannot reference a Codex round closure, condition 5
+    fails) → full Codex pre-merge review required, not verbatim.
+  Calibration risk: Codex may flag (a) the rm -rf as overly broad
+  (suggest narrower removal); (b) chmod 777 as too permissive;
+  (c) the regression test's string-matching assertions as fragile
+  to future refactor. All three are reasonable findings — would
+  cost a round 2.
+counter_v61: 64
+counter_v61_delta_since_retro: 13  # since RETRO-V61-005
+---
+
+## Decision
+
+Apply a 15-LOC fix to `ui/backend/services/case_solve/solver_streamer.py`
+that corrects the staging order introduced in V61-097 round 1 HIGH-2
+(run_id-suffixed `container_work_dir`). Add a regression test
+(`test_staging_renames_extracted_dir_into_run_id_suffix`) that pins
+the exact failure mode by tracking the bash command sequence sent to
+the container.
+
+## Root cause
+
+V61-097 round 1 HIGH-2 fix made `container_work_dir` run_id-suffixed
+to prevent abandoned-run collisions. The staging sequence was:
+
+```python
+# BUGGY:
+container.exec_run(cmd=["bash", "-c",
+    f"mkdir -p {container_work_dir} && chmod 777 {container_work_dir}"])  # ❶
+ok = container.put_archive(path=CONTAINER_WORK_BASE, data=...)             # ❷
+container.exec_run(cmd=["bash", "-c",
+    f"if [ -d {CONTAINER_WORK_BASE}/{case_id} ] && "
+    f"[ ! -d {container_work_dir} ]; then "
+    f"mv {CONTAINER_WORK_BASE}/{case_id} {container_work_dir}; fi"])       # ❸
+```
+
+❶ pre-creates the suffixed dir as an empty real directory.
+❷ extracts the tarball, which lands as `{BASE}/{case_id}` (un-suffixed,
+   since the tarball's top-level dir is named after the host case dir).
+❸ guards the rename with `[ ! -d {container_work_dir} ]` — but ❶ just
+   created it, so the guard is FALSE → `mv` is silently SKIPPED.
+
+End state:
+- `{BASE}/{case_id}/` (un-suffixed): contains the actual case files
+- `{BASE}/{case_id}-{run_id}/` (suffixed): empty
+- icoFoam `cd`'s into the empty suffixed dir → **FOAM Fatal: cannot
+  find file system/controlDict**
+
+## Why Codex's static review missed this
+
+The V61-097 round-1 verdict file (`reports/codex_tool_reports/
+dec_v61_097_phase_1a_round1.md`) flagged "abort/restart race — no
+run-generation guard, shared `container_work_dir`" as HIGH-2.
+
+The fix Claude applied for HIGH-2 was correct in concept (run_id
+suffix + per-case lock + run_id surfaced via SSE `start` event), but
+the BASH sequence interaction (mkdir + put_archive + conditional mv)
+was a runtime-emergent failure mode that the test suite did not
+exercise:
+
+- `test_run_id_suffixes_container_work_dir` (line 220-249) only
+  checked that `prepared.container_work_dir.endswith(...)` — string
+  assertion, not file-system behavior.
+- The `_FakeContainer.put_archive` mock returned `True` without
+  simulating the actual extract behavior. The mock had no notion of
+  WHERE the tarball would land, so it couldn't surface the
+  ❶-❷-❸ interaction.
+- Codex rounds 2/3/4 never re-examined the staging sequence because
+  rounds 2/3 closed the GeneratorExit + cache-hit symlink + start
+  yield findings — orthogonal to staging.
+
+This is the **`executable_smoke_test` blind-spot class** documented
+in RETRO-V61-053 addendum: defects that require a real execution
+environment (Docker container actually running put_archive +
+icoFoam) to surface, regardless of how thorough static review is.
+
+## The fix
+
+```python
+# FIXED:
+container.exec_run(cmd=["bash", "-c",
+    f"mkdir -p {CONTAINER_WORK_BASE} && chmod 777 {CONTAINER_WORK_BASE}"])  # ❶'
+ok = container.put_archive(path=CONTAINER_WORK_BASE, data=...)              # ❷
+container.exec_run(cmd=["bash", "-c",
+    f"rm -rf {container_work_dir} && "
+    f"mv {CONTAINER_WORK_BASE}/{case_id} {container_work_dir} && "
+    f"chmod 777 {container_work_dir}"])                                      # ❸'
+```
+
+Changes:
+- ❶' pre-creates ONLY the BASE (idempotent), not the suffixed dir.
+- ❸' is unconditional: `rm -rf {container_work_dir}` defensively
+  clears any orphan from a prior abandoned run (process kill, container
+  restart) whose `finally` cleanup didn't run; then `mv` always
+  succeeds because the destination doesn't exist.
+- `chmod 777` moves into ❸' (it was applied to the wrong path in ❶
+  anyway — the suffixed dir didn't actually receive the case files).
+
+## Why this fix is safe
+
+- run_id is unique per `_claim_run` (hex token from secrets module),
+  so no in-flight peer can hold the same suffixed path → no race
+  between concurrent runs that the `rm -rf` could harm.
+- The `_finally` cleanup path at solver_streamer.py:528 already does
+  `rm -rf {container_work_dir}` — the fix's defensive rm just
+  duplicates that cleanup at a known safe time (start of new run,
+  after the run_id is uniquely claimed).
+- Container-internal scope only — `{CONTAINER_WORK_BASE}` is
+  `/tmp/cfd-harness-cases-mesh` inside the cfd-openfoam Docker, not
+  a host path.
+
+## The regression test
+
+Added `test_staging_renames_extracted_dir_into_run_id_suffix` in
+`ui/backend/tests/test_solver_streamer.py`. Tracks every `bash -c`
+command sent to `exec_run` and asserts:
+
+1. **No mkdir pre-creates the run_id-suffixed dir.** This catches
+   the V61-099 bug because the buggy version's mkdir included the
+   suffix.
+2. **The mv is unconditional** (no `[ ! -d {suffix_dir} ]` guard).
+   This catches any future regression that re-introduces the guard.
+
+Test passes against the fixed code; would fail against the buggy
+code (verified by inspection of the assertion logic).
+
+## Governance
+
+- **Codex pre-merge review**: MANDATORY. Triggers per RETRO-V61-001:
+  - "OpenFOAM solver 报错修复" (FOAM Fatal Error: cannot find file)
+  - "solver_streamer.py modification > 5 LOC" (this fix is ~15 LOC)
+- **Verbatim exception**: NOT applicable. Conditions 1 and 5 fail
+  (this is a NEW finding from live run, not a Codex round closure).
+- **§11.1 BREAK_FREEZE**: rides under V61-097's existing slot 2/3.
+  Bug fixes within Accepted arcs do NOT consume fresh quota per
+  Pivot Charter Addendum 3 §5.
+- **Counter**: +1 (63 → 64). `autonomous_governance: true`.
+- **Kogami**: NOT triggered (V61-094 P2 #1 bounding clause · 4-condition
+  self-check passes).
+- **RETRO addendum**: required per RETRO-V61-053 methodology. Will
+  add to next RETRO entry as a `hidden_defects_caught_post_R3` row,
+  with `executable_smoke_test` risk-flag tagged.
+
+## Lessons for future arcs
+
+1. **Mock fidelity**: `_FakeContainer.put_archive` returning True
+   without simulating extract was the single point that allowed this
+   to slip. Future Docker-mock test suites should track destination
+   paths AND simulate extract semantics, OR fail loudly when called
+   without that fidelity.
+2. **Bash command sequence audit**: when staging logic spans 3+
+   exec_run calls with shared filesystem state, add a regression
+   test that asserts the SEQUENCE not just individual commands.
+3. **Live-run smoke before R4 RESOLVED**: per RETRO-V61-053
+   addendum, every Codex APPROVE arc should ideally have at least
+   one live-run smoke test before the arc is declared closed. V61-097
+   was declared RESOLVED based on static analysis only (Codex round 4
+   confirmed no findings) — first live run surfaced this defect ~1
+   hour after the push to origin/main.
+
+## Linked artifacts
+
+- DEC-V61-097 (predecessor · closed `c49fd11`) — this DEC closes a
+  defect originating in V61-097 round 1
+- RETRO-V61-053 addendum (post-R3 defect methodology) — captures
+  the `executable_smoke_test` risk-flag class this defect belongs to
+- M-AI-COPILOT (DEC-V61-098 · Active) — implementation arc currently
+  in flight; this fix lands BEFORE M-AI-COPILOT Step 2 backend
+  skeleton to avoid mixing concerns
+- Workbench long-horizon roadmap (proposal at
+  `.planning/strategic/workbench_long_horizon_roadmap_2026-04-29.md`) —
+  M9 (Tier-B AI) and beyond depend on Phase-1A staging being
+  trustworthy on arbitrary STL geometries
diff --git a/ui/backend/services/case_solve/solver_streamer.py b/ui/backend/services/case_solve/solver_streamer.py
index f01de49..36c2c98 100644
--- a/ui/backend/services/case_solve/solver_streamer.py
+++ b/ui/backend/services/case_solve/solver_streamer.py
@@ -225,151 +225,157 @@ def _prepare_stream_icofoam(
     ``exec_run(stream=True)``. All of these can raise
     :class:`SolverRunError` (or its :class:`SolveAlreadyRunning`
     subclass) — the route layer catches and translates to HTTP 4xx/5xx
     BEFORE returning the StreamingResponse.
 
     On any failure here, the run_id is released so a retry can claim
     it again.
     """
     if not case_host_dir.is_dir():
         raise SolverRunError(f"case dir not found: {case_host_dir}")
     if not (case_host_dir / "system" / "controlDict").is_file():
         raise SolverRunError(
             f"no system/controlDict at {case_host_dir} — run "
             "setup-bc first."
         )
 
     case_id = case_host_dir.name
     if run_id is None:
         run_id = _claim_run(case_id)
     else:
         # Caller-supplied run_id (tests). Still register so concurrent
         # callers see the in-flight state.
         with _runs_lock:
             if case_id in _active_runs:
                 raise SolveAlreadyRunning(
                     f"solve already running for case {case_id!r} "
                     f"(run_id={_active_runs[case_id]})"
                 )
             _active_runs[case_id] = run_id
 
     try:
         try:
             import docker  # type: ignore[import-not-found]
             import docker.errors  # type: ignore[import-not-found]
         except ImportError as exc:
             raise SolverRunError(
                 "docker SDK is not installed."
             ) from exc
 
         try:
             client = docker.from_env()
             container = client.containers.get(container_name)
             if container.status != "running":
                 raise SolverRunError(
                     f"container '{container_name}' is not running."
                 )
         except docker.errors.NotFound as exc:
             raise SolverRunError(
                 f"container '{container_name}' not found."
             ) from exc
         except docker.errors.DockerException as exc:
             raise SolverRunError(f"docker init failed: {exc}") from exc
 
         # Codex round-1 HIGH-2: container_work_dir is now run_id-suffixed
         # so concurrent runs (in spite of the lock, e.g. abandoned runs
         # whose lock entry was cleared by /finally) cannot collide on
         # log.icoFoam or the time directories.
         container_work_dir = f"{CONTAINER_WORK_BASE}/{case_id}-{run_id}"
 
         try:
+            # Pre-create the BASE only — NOT the run_id-suffixed work
+            # dir. The earlier version pre-created `{container_work_dir}`
+            # via `mkdir -p` then guarded the rename with `[ ! -d
+            # {container_work_dir} ]`, which silently skipped the `mv`
+            # because `mkdir -p` had just made the dir exist. Result:
+            # extracted case files stayed under `{CONTAINER_WORK_BASE}/
+            # {case_id}` (unsuffixed), the suffixed dir stayed empty,
+            # icoFoam `cd`d into the empty dir → FOAM Fatal: cannot
+            # find file system/controlDict. Caught post-R3 (V61-097
+            # round 4 RESOLVED) on the first live LDC dogfood run.
             container.exec_run(
                 cmd=[
                     "bash",
                     "-c",
-                    f"mkdir -p {container_work_dir} && chmod 777 {container_work_dir}",
+                    f"mkdir -p {CONTAINER_WORK_BASE} && chmod 777 {CONTAINER_WORK_BASE}",
                 ]
             )
-            # Stage the case files under the run_id-suffixed dir. We
-            # tar from case_host_dir, but extract under container_work_dir
-            # whose basename matches case_host_dir.name only if run_id
-            # is empty — so we send the tarball to a parent path and
-            # rename. Simpler: send to CONTAINER_WORK_BASE then move.
             ok = container.put_archive(
                 path=CONTAINER_WORK_BASE,
                 data=_make_tarball(case_host_dir),
             )
             if not ok:
                 raise SolverRunError(
                     "failed to stage case for streaming icoFoam"
                 )
-            # Rename the extracted dir from <case_id> to <case_id>-<run_id>.
-            # Use mv so the rename is atomic even if multiple runs land
-            # close together; if the source already vanished (parallel
-            # rename), `mv` returns non-zero and we fall through.
+            # Atomically rename the extracted dir into the run_id-suffixed
+            # name. run_id is unique per run so the destination cannot
+            # collide with an in-flight peer; defensively `rm -rf` first
+            # to clear any orphan from a prior abandoned run whose
+            # finally cleanup didn't run (process kill, container restart).
             container.exec_run(
                 cmd=[
                     "bash",
                     "-c",
-                    f"if [ -d {CONTAINER_WORK_BASE}/{case_id} ] && "
-                    f"[ ! -d {container_work_dir} ]; then "
-                    f"mv {CONTAINER_WORK_BASE}/{case_id} {container_work_dir}; fi",
+                    f"rm -rf {container_work_dir} && "
+                    f"mv {CONTAINER_WORK_BASE}/{case_id} {container_work_dir} && "
+                    f"chmod 777 {container_work_dir}",
                 ]
             )
         except docker.errors.DockerException as exc:
             raise SolverRunError(
                 f"docker SDK error preparing container workspace: {exc}"
             ) from exc
 
         # Spawn icoFoam. ``stdbuf -oL`` line-buffers stdout so PISO
         # iterations arrive promptly instead of in 4KB chunks.
         bash_cmd = (
             "source /opt/openfoam10/etc/bashrc && "
             f"cd {container_work_dir} && "
             "stdbuf -oL -eL icoFoam 2>&1"
         )
         try:
             exec_result = container.exec_run(
                 cmd=["bash", "-c", bash_cmd],
                 stream=True,
                 demux=False,
             )
         except docker.errors.DockerException as exc:
             raise SolverRunError(f"docker SDK error invoking icoFoam: {exc}") from exc
     except BaseException:
         # Any failure during preflight releases the lock so the user
         # can retry. The generator path takes ownership of the lock
         # release on its own try/finally.
         _release_run(case_id, run_id)
         raise
 
     return _PreparedStream(
         case_host_dir=case_host_dir,
         run_id=run_id,
         container=container,
         container_work_dir=container_work_dir,
         exec_result=exec_result,
     )
 
 
 def stream_icofoam(
     *,
     case_host_dir: Path | None = None,
     container_name: str = CONTAINER_NAME,
     prepared: _PreparedStream | None = None,
 ) -> Iterator[bytes]:
     """Run icoFoam with streamed output. Yields SSE-formatted bytes
     that an EventSource client can consume directly.
 
     Two call shapes:
 
     * ``stream_icofoam(prepared=<_PreparedStream>)`` — preferred path
       used by the route. Preflight has already happened in
       :func:`_prepare_stream_icofoam`; this function only consumes the
       already-spawned exec result.
     * ``stream_icofoam(case_host_dir=...)`` — legacy entrypoint kept
       for tests + the blocking variant's parity. Internally calls
       ``_prepare_stream_icofoam`` then delegates.
 
     The first SSE event is always ``start`` with ``{"run_id": ...}``
     so the frontend can stamp every subsequent state-write with the
     matching run generation (HIGH-2 frontend half).
diff --git a/ui/backend/tests/test_solver_streamer.py b/ui/backend/tests/test_solver_streamer.py
index 5183a6f..b10c0d0 100644
--- a/ui/backend/tests/test_solver_streamer.py
+++ b/ui/backend/tests/test_solver_streamer.py
@@ -192,120 +192,212 @@ def test_concurrent_run_rejected(tmp_path, monkeypatch):
         with pytest.raises(SolveAlreadyRunning, match="already running"):
             _claim_run(case_id)
     finally:
         _release_run(case_id, run_id)
     assert case_id not in _active_runs
 
 
 def test_release_run_is_idempotent_on_mismatch():
     """Releasing a run_id that doesn't match the active one is a no-op
     (defensive: protects against a stale generator's finally clause
     racing with a freshly-claimed run).
     """
     from ui.backend.services.case_solve.solver_streamer import (
         _active_runs,
         _claim_run,
         _release_run,
     )
 
     case_id = "case_idem"
     run_id_a = _claim_run(case_id)
     # Release with a different run_id — must NOT clear the active entry.
     _release_run(case_id, "wrong_run_id")
     assert _active_runs.get(case_id) == run_id_a
     # Real release works.
     _release_run(case_id, run_id_a)
     assert case_id not in _active_runs
 
 
 def test_run_id_suffixes_container_work_dir(tmp_path, monkeypatch):
     """The container_work_dir must be run_id-suffixed so concurrent
     abandoned runs cannot collide on log.icoFoam or time directories.
     """
     from ui.backend.services.case_solve import solver_streamer
     from ui.backend.services.case_solve.solver_streamer import (
         _active_runs,
         _prepare_stream_icofoam,
         _release_run,
     )
 
     case_dir = tmp_path / "case_suffix"
     case_dir.mkdir()
     _stage_minimal_case(case_dir)
     container = _FakeContainer(status="running", exec_lines=[])
     _install_fake_docker(monkeypatch, container)
 
     # Use a fixed run_id so the assertion is deterministic.
     forced_run_id = "deadbeefcafe"
     try:
         prepared = _prepare_stream_icofoam(
             case_host_dir=case_dir, run_id=forced_run_id
         )
         assert prepared.run_id == forced_run_id
         assert prepared.container_work_dir.endswith(
             f"case_suffix-{forced_run_id}"
         )
     finally:
         _release_run("case_suffix", forced_run_id)
     assert "case_suffix" not in _active_runs
 
 
+# ────────── Post-R3 live-run defect (DEC-V61-099): staging order ──────────
+
+
+def test_staging_renames_extracted_dir_into_run_id_suffix(tmp_path, monkeypatch):
+    """Post-R3 live-run defect (DEC-V61-099 · caught on first LDC dogfood
+    after V61-097 R4 RESOLVED). The V61-097 round-1 HIGH-2 fix introduced
+    a run_id-suffixed container_work_dir but the staging sequence
+    silently bypassed the rename:
+
+      1. ``mkdir -p {container_work_dir}``  ← suffix dir pre-created
+      2. ``put_archive(path={CONTAINER_WORK_BASE})``  ← extracts as
+         ``{BASE}/{case_id}`` (un-suffixed)
+      3. ``if [ -d {BASE}/{case_id} ] && [ ! -d {container_work_dir} ];
+            then mv ... fi``  ← guard FALSE because step 1 just created
+            the suffix dir → ``mv`` SKIPPED → suffix dir stays empty
+
+    icoFoam then ``cd``'d into the empty suffix dir and FOAM-Fatal'd
+    on missing ``system/controlDict``.
+
+    Codex's static review missed this in V61-097 because the staging
+    test (``test_run_id_suffixes_container_work_dir``) only asserted the
+    PATH STRING and the mock ``put_archive`` returned True without
+    simulating actual extract. This test pins the failure mode by
+    tracking the bash command sequence.
+
+    Per RETRO-V61-053 addendum: this is the ``executable_smoke_test``
+    risk-flag class — runtime-emergent, not visible to static review.
+    """
+    from ui.backend.services.case_solve.solver_streamer import (
+        _prepare_stream_icofoam,
+        _release_run,
+    )
+
+    case_dir = tmp_path / "case_staging_regression"
+    case_dir.mkdir()
+    _stage_minimal_case(case_dir)
+
+    # Track every bash command sent to exec_run so we can assert the
+    # staging sequence is correct.
+    bash_commands: list[str] = []
+
+    class TrackingContainer(_FakeContainer):
+        def exec_run(self, cmd, stream=False, demux=False):  # noqa: ARG002
+            if isinstance(cmd, list) and len(cmd) >= 3 and cmd[0] == "bash":
+                bash_commands.append(cmd[2])
+            return super().exec_run(cmd, stream=stream, demux=demux)
+
+    container = TrackingContainer(status="running", exec_lines=[])
+    _install_fake_docker(monkeypatch, container)
+
+    forced_run_id = "regtest9999"
+    suffix_path_fragment = f"case_staging_regression-{forced_run_id}"
+    try:
+        prepared = _prepare_stream_icofoam(
+            case_host_dir=case_dir, run_id=forced_run_id
+        )
+        assert prepared.container_work_dir.endswith(suffix_path_fragment)
+    finally:
+        _release_run("case_staging_regression", forced_run_id)
+
+    # Assertion 1: there is exactly ONE mkdir command before put_archive,
+    # and it must NOT pre-create the run_id-suffixed dir (the buggy
+    # version did, which is what neutered the subsequent mv).
+    mkdir_cmds = [c for c in bash_commands if "mkdir -p" in c]
+    assert mkdir_cmds, "expected at least one mkdir during staging"
+    pre_archive_mkdirs = [
+        c for c in mkdir_cmds if suffix_path_fragment in c
+    ]
+    assert not pre_archive_mkdirs, (
+        f"REGRESSION: staging pre-created the run_id-suffixed dir via "
+        f"mkdir -p — this is the V61-099 bug because the subsequent mv "
+        f"is silently skipped under the [ ! -d suffix ] guard. "
+        f"Offending command(s): {pre_archive_mkdirs}"
+    )
+
+    # Assertion 2: the rename of the extracted {case_id} dir into the
+    # run_id-suffixed name must be UNCONDITIONAL (no [ ! -d ] guard
+    # against the suffix dir, since under V61-099 the suffix dir does
+    # not pre-exist for the same-run claim).
+    mv_cmds = [c for c in bash_commands if " mv " in c and suffix_path_fragment in c]
+    assert mv_cmds, (
+        f"expected an `mv` command renaming the extracted dir into "
+        f"the run_id-suffixed name; got commands: {bash_commands}"
+    )
+    for mv in mv_cmds:
+        assert "[ ! -d" not in mv, (
+            f"REGRESSION: rename guarded by [ ! -d {{suffix_dir}} ] — "
+            f"this is what allowed V61-099 to silently skip the rename "
+            f"after the (now-removed) pre-create mkdir. mv command: {mv!r}"
+        )
+
+
 # ────────── Codex round-2 R2.1: GeneratorExit must release the lock ──────────
 
 
 def test_generator_close_releases_run_id_after_first_yield(
     tmp_path, monkeypatch
 ):
     """Codex round-3 finding: closing the generator IMMEDIATELY after
     the first `start` SSE — without ever entering the streaming loop —
     used to bypass the outer try/finally because the start yield was
     OUTSIDE it. Round 3 moved the yield inside; this test pins down
     the exact failure mode Codex flagged.
     """
     from ui.backend.services.case_solve.solver_streamer import (
         _active_runs,
         _prepare_stream_icofoam,
         stream_icofoam,
     )
 
     case_dir = tmp_path / "case_immediate_close"
     case_dir.mkdir()
     _stage_minimal_case(case_dir)
 
     # Empty exec_lines so even one extra next() would still happen,
     # but we close right after the first start yield.
     container = _FakeContainer(status="running", exec_lines=[])
     _install_fake_docker(monkeypatch, container)
 
     prepared = _prepare_stream_icofoam(case_host_dir=case_dir)
     assert "case_immediate_close" in _active_runs
     gen = stream_icofoam(prepared=prepared)
 
     # Consume ONLY the start event, then close. Generator is suspended
     # exactly on the start yield — the failure mode round 2 missed.
     first = next(gen)
     assert first.startswith(b"event: start"), "first event should be the start event"
     gen.close()  # raises GeneratorExit at the start yield
 
     assert "case_immediate_close" not in _active_runs, (
         "GeneratorExit on the start yield must release the run lock"
     )
 
 
 def test_generator_close_releases_run_id_mid_loop(tmp_path, monkeypatch):
     """Round-2 R2.1: closing the generator mid-streaming-loop must also
     release. Complementary to the immediate-disconnect test above.
     """
     from ui.backend.services.case_solve.solver_streamer import (
         _active_runs,
         _prepare_stream_icofoam,
         stream_icofoam,
     )
 
     case_dir = tmp_path / "case_disconnect"
     case_dir.mkdir()
     _stage_minimal_case(case_dir)
 
     lines = [b"Time = 0.005s\n"] * 200
     container = _FakeContainer(status="running", exec_lines=lines)
     _install_fake_docker(monkeypatch, container)
 

codex
I’m into the behavioral edge now. The main questions are whether this patch actually checks staging success, and whether the new test would fail for the real regression instead of only for one particular shell-string spelling.
exec
/bin/zsh -lc "nl -ba ui/backend/tests/test_solver_streamer.py | sed -n '1,220p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
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
   121	
   122	    class NotFound(DockerException):
   123	        pass
   124	
   125	    fake_errors.DockerException = DockerException
   126	    fake_errors.NotFound = NotFound
   127	    fake_docker.errors = fake_errors
   128	
   129	    def from_env():
   130	        client = _FakeClient(None)
   131	
   132	        def get_missing(name):
   133	            raise NotFound(f"no such container: {name}")
   134	
   135	        client.containers = types.SimpleNamespace(get=get_missing)
   136	        return client
   137	
   138	    fake_docker.from_env = from_env
   139	    monkeypatch.setitem(sys.modules, "docker", fake_docker)
   140	    monkeypatch.setitem(sys.modules, "docker.errors", fake_errors)
   141	
   142	    with pytest.raises(SolverRunError, match="not found"):
   143	        _prepare_stream_icofoam(case_host_dir=case_dir)
   144	
   145	
   146	def test_preflight_releases_run_id_on_failure(tmp_path, monkeypatch):
   147	    """If preflight fails after _claim_run, the run_id must be released
   148	    so the user can retry. Otherwise a single bad config would lock
   149	    the case forever.
   150	    """
   151	    from ui.backend.services.case_solve.solver_streamer import (
   152	        SolverRunError,
   153	        _active_runs,
   154	        _prepare_stream_icofoam,
   155	    )
   156	
   157	    case_dir = tmp_path / "case_release"
   158	    case_dir.mkdir()
   159	    _stage_minimal_case(case_dir)
   160	    # Container exists but status='exited' → triggers the inner
   161	    # SolverRunError("not running") AFTER claim_run, exercising the
   162	    # outer except BaseException → _release_run path.
   163	    container = _FakeContainer(status="exited")
   164	    _install_fake_docker(monkeypatch, container)
   165	
   166	    with pytest.raises(SolverRunError, match="not running"):
   167	        _prepare_stream_icofoam(case_host_dir=case_dir)
   168	    assert "case_release" not in _active_runs, (
   169	        "preflight failure must release the run_id"
   170	    )
   171	
   172	
   173	# ────────── HIGH-2: concurrent runs rejected ──────────
   174	
   175	
   176	def test_concurrent_run_rejected(tmp_path, monkeypatch):
   177	    """A second _prepare_stream_icofoam for the same case while the
   178	    first is still in-flight must raise SolveAlreadyRunning so the
   179	    route returns HTTP 409.
   180	    """
   181	    from ui.backend.services.case_solve.solver_streamer import (
   182	        SolveAlreadyRunning,
   183	        _active_runs,
   184	        _claim_run,
   185	        _release_run,
   186	    )
   187	
   188	    # Manually claim a run to simulate one already in-flight.
   189	    case_id = "case_concurrent"
   190	    run_id = _claim_run(case_id)
   191	    try:
   192	        with pytest.raises(SolveAlreadyRunning, match="already running"):
   193	            _claim_run(case_id)
   194	    finally:
   195	        _release_run(case_id, run_id)
   196	    assert case_id not in _active_runs
   197	
   198	
   199	def test_release_run_is_idempotent_on_mismatch():
   200	    """Releasing a run_id that doesn't match the active one is a no-op
   201	    (defensive: protects against a stale generator's finally clause
   202	    racing with a freshly-claimed run).
   203	    """
   204	    from ui.backend.services.case_solve.solver_streamer import (
   205	        _active_runs,
   206	        _claim_run,
   207	        _release_run,
   208	    )
   209	
   210	    case_id = "case_idem"
   211	    run_id_a = _claim_run(case_id)
   212	    # Release with a different run_id — must NOT clear the active entry.
   213	    _release_run(case_id, "wrong_run_id")
   214	    assert _active_runs.get(case_id) == run_id_a
   215	    # Real release works.
   216	    _release_run(case_id, run_id_a)
   217	    assert case_id not in _active_runs
   218	
   219	
   220	def test_run_id_suffixes_container_work_dir(tmp_path, monkeypatch):

exec
/bin/zsh -lc "rg -n \"exec_run\\(|put_archive\\(|_FakeContainer|exit_code|chmod 777|CONTAINER_WORK_BASE|case_host_dir.name|case_id =|token_hex\\(\" ui/backend/services ui/backend/tests -S" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
ui/backend/services/run_history.py:10:            verdict.json       — pass/fail + exit_code + summary
ui/backend/services/run_history.py:110:    exit_code: int,
ui/backend/services/run_history.py:143:        "exit_code": exit_code,
ui/backend/services/run_history.py:192:        exit_code=int(verdict.get("exit_code", -1)),
ui/backend/services/run_history.py:293:        exit_code=int(verdict.get("exit_code", -1)),
ui/backend/tests/test_geometry_render_route.py:67:    case_id = "imported_2026-04-28T00-00-00Z_cube0001"
ui/backend/tests/test_geometry_render_route.py:92:    case_id = f"imported_2026-04-28T00-00-00Z_{fixture_label}"
ui/backend/tests/test_geometry_render_route.py:111:    case_id = "imported_2026-04-28T00-00-00Z_notrisurface"
ui/backend/tests/test_geometry_render_route.py:120:    case_id = "imported_2026-04-28T00-00-00Z_emptytrisurface"
ui/backend/tests/test_geometry_render_route.py:141:    case_id = "imported_2026-04-28T00-00-00Z_uppercase"
ui/backend/services/run_compare.py:16:          - verdict_diff (success a vs b, exit_code a vs b)
ui/backend/services/run_compare.py:252:            "exit_code": detail_a.exit_code,
ui/backend/services/run_compare.py:261:            "exit_code": detail_b.exit_code,
ui/backend/services/run_compare.py:272:            "exit_code_changed": detail_a.exit_code != detail_b.exit_code,
ui/backend/services/comparison_report.py:688:    if case_id == "backward_facing_step":
ui/backend/services/comparison_report.py:748:    if case_id == "circular_cylinder_wake":
ui/backend/services/comparison_report.py:870:    if case_id == "differential_heated_cavity":
ui/backend/services/comparison_report.py:1332:        "case_display_name": "Lid-Driven Cavity (Re=100)" if case_id == "lid_driven_cavity" else case_id,
ui/backend/tests/test_wizard_drivers.py:163:        exit_code=0,
ui/backend/tests/test_wizard_drivers.py:175:def test_real_driver_unknown_case_id_emits_run_done_with_exit_code_2() -> None:
ui/backend/tests/test_wizard_drivers.py:184:    assert last["exit_code"] == 2
ui/backend/tests/test_wizard_drivers.py:208:    assert last["exit_code"] == 0
ui/backend/tests/test_wizard_drivers.py:225:    with exit_code=1, level=error, summarising the exception type."""
ui/backend/tests/test_wizard_drivers.py:232:    assert last["exit_code"] == 1
ui/backend/tests/test_wizard_drivers.py:239:def test_real_driver_execution_result_failure_uses_result_exit_code() -> None:
ui/backend/tests/test_wizard_drivers.py:240:    """ExecutionResult.success=False with explicit exit_code=137 (OOM kill)
ui/backend/tests/test_wizard_drivers.py:241:    must be mirrored into run_done.exit_code rather than coerced to 1."""
ui/backend/tests/test_wizard_drivers.py:245:        exit_code=137,  # OOM kill convention
ui/backend/tests/test_wizard_drivers.py:252:    assert last["exit_code"] == 137
ui/backend/tests/test_wizard_drivers.py:353:    assert events[-1]["exit_code"] == 0
ui/backend/tests/test_wizard_drivers.py:388:    correct exit_code, key_quantities + residuals copied through."""
ui/backend/tests/test_wizard_drivers.py:404:    assert kw["exit_code"] == 0
ui/backend/tests/test_wizard_drivers.py:416:    success=False, exit_code=1, error_message populated."""
ui/backend/tests/test_wizard_drivers.py:425:    assert kw["exit_code"] == 1
ui/backend/tests/test_wizard_drivers.py:458:    assert events[-1]["exit_code"] == 0
ui/backend/tests/test_wizard_drivers.py:584:        exit_code=1,
ui/backend/tests/test_wizard_drivers.py:615:    assert run_done["exit_code"] == 1
ui/backend/tests/test_wizard_drivers.py:630:    assert run_done["exit_code"] == 0
ui/backend/tests/test_cases_route.py:86:    case_id = "imported_2026-04-28T11-39-46Z_a4d3db45"
ui/backend/tests/test_cases_route.py:128:    case_id = "imported_2026-04-28T11-39-46Z_a4d3db45"
ui/backend/tests/test_cases_route.py:142:    case_id = "imported_2026-04-28T11-39-46Z_a4d3db45"
ui/backend/tests/test_meshing_gmsh.py:446:    fake_container.exec_run.return_value = MagicMock(exit_code=0, output=b"ok")
ui/backend/tests/test_meshing_gmsh.py:869:    case_id = "imported_2026-04-28T00-00-00Z_racecase"
ui/backend/tests/test_meshing_gmsh.py:905:    fake_container.exec_run.return_value = MagicMock(exit_code=0, output=b"ok")
ui/backend/tests/test_meshing_gmsh.py:1049:    fake_container.exec_run.return_value = MagicMock(exit_code=0, output=b"ok")
ui/backend/tests/test_meshing_gmsh.py:1092:    fake_container.exec_run.return_value = MagicMock(exit_code=0, output=b"ok")
ui/backend/tests/test_meshing_gmsh.py:1125:    fake_container.exec_run.return_value = MagicMock(exit_code=0, output=b"ok")
ui/backend/services/wizard_drivers.py:311:def _classify_failure(text: str | None, _exit_code: int | None = None) -> str:
ui/backend/services/wizard_drivers.py:448:      - case_id not in whitelist → run_done with exit_code=2, level=error
ui/backend/services/wizard_drivers.py:450:        phase_done status=fail + run_done with exit_code=1, level=error
ui/backend/services/wizard_drivers.py:451:      - ExecutionResult.success=False → phase_done status=fail, exit_code
ui/backend/services/wizard_drivers.py:452:        mirrors result.exit_code if set else 1
ui/backend/services/wizard_drivers.py:453:      - Success → phase_done status=ok + run_done with exit_code=0
ui/backend/services/wizard_drivers.py:515:                "exit_code": 2, "level": "error",
ui/backend/services/wizard_drivers.py:565:                        exit_code=130,  # conventional SIGINT-style code
ui/backend/services/wizard_drivers.py:590:                        f"{type(exc).__name__}: {err_str}", _exit_code=1
ui/backend/services/wizard_drivers.py:599:                        exit_code=1,
ui/backend/services/wizard_drivers.py:614:                        res.error_message, _exit_code=res.exit_code
ui/backend/services/wizard_drivers.py:622:                    exit_code = res.exit_code if res.exit_code is not None else 0
ui/backend/services/wizard_drivers.py:626:                    exit_code = res.exit_code if res.exit_code is not None else 1
ui/backend/services/wizard_drivers.py:634:                    exit_code=exit_code,
ui/backend/services/wizard_drivers.py:709:                        "exit_code": 130,
ui/backend/services/wizard_drivers.py:729:                f"{type(exc).__name__}: {err_str}", _exit_code=1
ui/backend/services/wizard_drivers.py:758:                "exit_code": 1, "level": "error",
ui/backend/services/wizard_drivers.py:796:                result.error_message, _exit_code=result.exit_code
ui/backend/services/wizard_drivers.py:810:            exit_code = result.exit_code if result.exit_code is not None else 0
ui/backend/services/wizard_drivers.py:822:            exit_code = result.exit_code if result.exit_code is not None else 1
ui/backend/services/wizard_drivers.py:837:            "exit_code": exit_code,
ui/backend/tests/test_run_history.py:72:        exit_code=0,
ui/backend/tests/test_run_history.py:90:    assert verdict["exit_code"] == 0
ui/backend/tests/test_run_history.py:102:    assert row.exit_code == 0
ui/backend/tests/test_run_history.py:123:            exit_code=0,
ui/backend/tests/test_run_history.py:150:        success=True, exit_code=0, verdict_summary="ok",
ui/backend/tests/test_run_history.py:201:            exit_code=0,
ui/backend/tests/test_run_history.py:218:    assert recent[0].case_id == "circular_cylinder_wake"
ui/backend/tests/test_run_history.py:235:            exit_code=0,
ui/backend/tests/test_run_history.py:261:        exit_code=137,
ui/backend/tests/test_run_history.py:271:    assert detail.exit_code == 137
ui/backend/services/render/bc_glb.py:391:        f".tmp.{secrets.token_hex(4)}{target.suffix}"
ui/backend/tests/test_wizard_route.py:45:    case_id = "wizard_test_first_cavity"
ui/backend/tests/test_wizard_route.py:86:    case_id = "wizard_test_bad_template"
ui/backend/tests/test_wizard_route.py:101:    case_id = "wizard_test_pipe"
ui/backend/tests/test_wizard_route.py:151:    """Round-3 Q13 schema audit: the level / stream / exit_code fields are
ui/backend/tests/test_wizard_route.py:164:    assert mock_ev.exit_code is None
ui/backend/tests/test_wizard_route.py:175:    # phase_done with exit_code (subprocess wait result)
ui/backend/tests/test_wizard_route.py:179:        exit_code=0,
ui/backend/tests/test_wizard_route.py:181:    assert done_ev.exit_code == 0
ui/backend/tests/test_wizard_route.py:196:    assert "exit_code" not in payload
ui/backend/tests/test_wizard_route.py:211:    case_id = "wizard_test_preview_match"
ui/backend/tests/test_wizard_route.py:253:    case_id = "wizard_test_nan"
ui/backend/tests/test_wizard_route.py:273:    case_id = "wizard_test_inf"
ui/backend/tests/test_wizard_route.py:289:    case_id = "wizard_test_below_min"
ui/backend/tests/test_wizard_route.py:307:    case_id = "wizard_test_above_max"
ui/backend/tests/test_wizard_route.py:326:    case_id = "wizard_test_extra_keys"
ui/backend/tests/test_wizard_route.py:352:    case_id = "wizard_test_typo"
ui/backend/tests/test_wizard_route.py:379:    case_id = "wizard_test_clean_keys"
ui/backend/tests/test_wizard_route.py:398:    case_id = "wizard_test_create_validates"
ui/backend/tests/test_wizard_route.py:419:    case_id = "preview_should_not_write_to_disk"
ui/backend/tests/test_run_compare.py:52:        exit_code=0,
ui/backend/tests/test_run_compare.py:72:        exit_code=0,
ui/backend/tests/test_run_compare.py:135:    # Both runs succeeded with exit_code 0
ui/backend/tests/test_run_compare.py:137:    assert out["verdict_diff"]["exit_code_changed"] is False
ui/backend/tests/test_run_compare.py:162:        source_origin="whitelist", success=True, exit_code=0,
ui/backend/tests/test_run_compare.py:171:        source_origin="whitelist", success=True, exit_code=0,
ui/backend/tests/test_run_compare.py:196:        source_origin="whitelist", success=True, exit_code=0,
ui/backend/tests/test_run_compare.py:205:        source_origin="whitelist", success=True, exit_code=0,
ui/backend/tests/test_run_compare.py:245:        source_origin="whitelist", success=True, exit_code=0,
ui/backend/tests/test_run_compare.py:254:        source_origin="whitelist", success=True, exit_code=0,
ui/backend/tests/test_run_compare.py:284:        source_origin="whitelist", success=True, exit_code=0,
ui/backend/tests/test_run_compare.py:293:        source_origin="whitelist", success=True, exit_code=0,
ui/backend/tests/test_run_compare.py:362:        source_origin="whitelist", success=True, exit_code=0,
ui/backend/tests/test_run_compare.py:385:            source_origin="whitelist", success=True, exit_code=0,
ui/backend/tests/test_convergence_attestor.py:59:        exit_code=0,
ui/backend/tests/test_convergence_attestor.py:410:def test_a1_exit_code_false_forces_fail(tmp_path: Path) -> None:
ui/backend/tests/test_convergence_attestor.py:414:        execution_result=SimpleNamespace(success=False, exit_code=139),
ui/backend/tests/test_convergence_attestor.py:417:    assert result.evidence["exit_code"] == 139
ui/backend/tests/test_convergence_attestor.py:424:        execution_result=SimpleNamespace(success=True, exit_code=0),
ui/backend/tests/test_convergence_attestor.py:437:        execution_result=SimpleNamespace(success=True, exit_code=0),
ui/backend/services/render/field_sample.py:253:        f".tmp.{secrets.token_hex(4)}{target.suffix}"
ui/backend/services/case_solve/solver_streamer.py:7:``container.exec_run(stream=True)`` so log lines arrive incrementally;
ui/backend/services/case_solve/solver_streamer.py:41:    CONTAINER_WORK_BASE,
ui/backend/services/case_solve/solver_streamer.py:84:        run_id = secrets.token_hex(6)  # 12-char hex, plenty for collision-free
ui/backend/services/case_solve/solver_streamer.py:225:    ``exec_run(stream=True)``. All of these can raise
ui/backend/services/case_solve/solver_streamer.py:241:    case_id = case_host_dir.name
ui/backend/services/case_solve/solver_streamer.py:282:        container_work_dir = f"{CONTAINER_WORK_BASE}/{case_id}-{run_id}"
ui/backend/services/case_solve/solver_streamer.py:290:            # extracted case files stayed under `{CONTAINER_WORK_BASE}/
ui/backend/services/case_solve/solver_streamer.py:295:            container.exec_run(
ui/backend/services/case_solve/solver_streamer.py:299:                    f"mkdir -p {CONTAINER_WORK_BASE} && chmod 777 {CONTAINER_WORK_BASE}",
ui/backend/services/case_solve/solver_streamer.py:302:            ok = container.put_archive(
ui/backend/services/case_solve/solver_streamer.py:303:                path=CONTAINER_WORK_BASE,
ui/backend/services/case_solve/solver_streamer.py:315:            container.exec_run(
ui/backend/services/case_solve/solver_streamer.py:320:                    f"mv {CONTAINER_WORK_BASE}/{case_id} {container_work_dir} && "
ui/backend/services/case_solve/solver_streamer.py:321:                    f"chmod 777 {container_work_dir}",
ui/backend/services/case_solve/solver_streamer.py:337:            exec_result = container.exec_run(
ui/backend/services/case_solve/solver_streamer.py:425:        yield _sse("start", {"run_id": run_id, "case_id": case_host_dir.name})
ui/backend/services/case_solve/solver_streamer.py:482:            ls_out = container.exec_run(
ui/backend/services/case_solve/solver_streamer.py:512:            "case_id": case_host_dir.name,
ui/backend/services/case_solve/solver_streamer.py:531:        _release_run(case_host_dir.name, run_id)
ui/backend/services/case_solve/solver_streamer.py:533:            container.exec_run(
ui/backend/services/case_solve/solver_runner.py:23:    CONTAINER_WORK_BASE,
ui/backend/services/case_solve/solver_runner.py:187:    container_work_dir = f"{CONTAINER_WORK_BASE}/{case_host_dir.name}"
ui/backend/services/case_solve/solver_runner.py:192:        container.exec_run(
ui/backend/services/case_solve/solver_runner.py:197:                f"chmod 777 {container_work_dir}",
ui/backend/services/case_solve/solver_runner.py:200:        ok = container.put_archive(
ui/backend/services/case_solve/solver_runner.py:201:            path=CONTAINER_WORK_BASE,
ui/backend/services/case_solve/solver_runner.py:227:        exec_result = container.exec_run(cmd=["bash", "-c", bash_cmd])
ui/backend/services/case_solve/solver_runner.py:231:    # Always pull the log first, even if exit_code != 0 — we need it
ui/backend/services/case_solve/solver_runner.py:241:        # (gmshToFoam used a similar dance — here case_host_dir.name is
ui/backend/services/case_solve/solver_runner.py:260:    if exec_result.exit_code != 0:
ui/backend/services/case_solve/solver_runner.py:262:            f"icoFoam exited with code {exec_result.exit_code}; "
ui/backend/services/case_solve/solver_runner.py:275:        ls_out = container.exec_run(
ui/backend/services/case_solve/solver_runner.py:303:        case_id=case_host_dir.name,
ui/backend/services/case_annotations/_yaml_io.py:175:    file_case_id = data.get("case_id")
ui/backend/services/batch_matrix.py:87:    case_id = case_row["id"]
ui/backend/services/render/mesh_wireframe.py:155:        f".tmp.{secrets.token_hex(4)}{target.suffix}"
ui/backend/services/case_scaffold/template_clone.py:66:    rand = rand_hex if rand_hex is not None else secrets.token_hex(4)
ui/backend/services/case_scaffold/template_clone.py:67:    case_id = f"imported_{when}_{rand}"
ui/backend/tests/test_solver_streamer.py:23:class _FakeContainer:
ui/backend/tests/test_solver_streamer.py:30:    def exec_run(self, cmd, stream: bool = False, demux: bool = False):  # noqa: D401, ARG002
ui/backend/tests/test_solver_streamer.py:35:        return types.SimpleNamespace(output=b"", exit_code=0)
ui/backend/tests/test_solver_streamer.py:37:    def put_archive(self, path, data):  # noqa: ARG002
ui/backend/tests/test_solver_streamer.py:163:    container = _FakeContainer(status="exited")
ui/backend/tests/test_solver_streamer.py:189:    case_id = "case_concurrent"
ui/backend/tests/test_solver_streamer.py:210:    case_id = "case_idem"
ui/backend/tests/test_solver_streamer.py:234:    container = _FakeContainer(status="running", exec_lines=[])
ui/backend/tests/test_solver_streamer.py:262:      2. ``put_archive(path={CONTAINER_WORK_BASE})``  ← extracts as
ui/backend/tests/test_solver_streamer.py:293:    class TrackingContainer(_FakeContainer):
ui/backend/tests/test_solver_streamer.py:294:        def exec_run(self, cmd, stream=False, demux=False):  # noqa: ARG002
ui/backend/tests/test_solver_streamer.py:297:            return super().exec_run(cmd, stream=stream, demux=demux)
ui/backend/tests/test_solver_streamer.py:368:    container = _FakeContainer(status="running", exec_lines=[])
ui/backend/tests/test_solver_streamer.py:401:    container = _FakeContainer(status="running", exec_lines=lines)
ui/backend/services/meshing_gmsh/to_foam.py:24:CONTAINER_WORK_BASE = "/tmp/cfd-harness-cases-mesh"
ui/backend/services/meshing_gmsh/to_foam.py:157:    container_work_dir = f"{CONTAINER_WORK_BASE}/{case_host_dir.name}"
ui/backend/services/meshing_gmsh/to_foam.py:163:        container.exec_run(
ui/backend/services/meshing_gmsh/to_foam.py:164:            cmd=["bash", "-c", f"mkdir -p {container_work_dir} && chmod 777 {container_work_dir}"]
ui/backend/services/meshing_gmsh/to_foam.py:166:        archive_ok = container.put_archive(
ui/backend/services/meshing_gmsh/to_foam.py:167:            path=CONTAINER_WORK_BASE,
ui/backend/services/meshing_gmsh/to_foam.py:185:            f"case dir vanished while building tarball for {case_host_dir.name}: {exc}"
ui/backend/services/meshing_gmsh/to_foam.py:194:            f"failed to build gmshToFoam tarball for {case_host_dir.name} "
ui/backend/services/meshing_gmsh/to_foam.py:210:        exec_result = container.exec_run(cmd=["bash", "-c", bash_cmd])
ui/backend/services/meshing_gmsh/to_foam.py:245:    if exec_result.exit_code != 0:
ui/backend/services/meshing_gmsh/to_foam.py:247:            f"gmshToFoam exit_code={exec_result.exit_code}; see "
ui/backend/tests/test_case_scaffold.py:125:    assert result.case_id == "imported_2026-04-27T12-00-00Z_deadbeef"
ui/backend/tests/test_mesh_wireframe.py:159:    case_id = "imported_2026-04-28T00-00-00Z_oob_face"
ui/backend/tests/test_mesh_wireframe.py:185:    case_id = "imported_2026-04-28T00-00-00Z_polymesh_symlink"
ui/backend/tests/test_mesh_wireframe.py:275:    case_id = "imported_2026-04-28T00-00-00Z_meshhit"
ui/backend/tests/test_mesh_wireframe.py:290:    case_id = "imported_2026-04-28T00-00-00Z_meshinval"
ui/backend/tests/test_mesh_wireframe.py:318:    case_id = "imported_2026-04-28T00-00-00Z_nomesh"
ui/backend/tests/test_mesh_wireframe.py:327:    case_id = "imported_2026-04-28T00-00-00Z_garbage"
ui/backend/tests/test_mesh_wireframe.py:343:    case_id = "imported_2026-04-28T00-00-00Z_cubemesh"
ui/backend/tests/test_mesh_wireframe.py:363:    case_id = "imported_2026-04-28T00-00-00Z_nopolymesh"
ui/backend/tests/test_mesh_wireframe.py:372:    case_id = "imported_2026-04-28T00-00-00Z_garbagemesh"
ui/backend/tests/test_mesh_wireframe.py:385:    case_id = "imported_2026-04-28T00-00-00Z_cachebyteequal"
ui/backend/tests/test_mesh_wireframe.py:398:    case_id = "imported_2026-04-28T00-00-00Z_atomicmesh"
ui/backend/tests/test_comparison_report_visual_only.py:238:    case_id = "circular_cylinder_wake"
ui/backend/tests/test_comparison_report_visual_only.py:388:    case_id = "differential_heated_cavity"
ui/backend/tests/test_geometry_render_glb.py:71:    case_id = "imported_2026-04-28T00-00-00Z_cube0001"
ui/backend/tests/test_geometry_render_glb.py:94:    case_id = f"imported_2026-04-28T00-00-00Z_{fixture_label}"
ui/backend/tests/test_geometry_render_glb.py:108:    case_id = "imported_2026-04-28T00-00-00Z_cachehit"
ui/backend/tests/test_geometry_render_glb.py:123:    case_id = "imported_2026-04-28T00-00-00Z_status"
ui/backend/tests/test_geometry_render_glb.py:136:    case_id = "imported_2026-04-28T00-00-00Z_invalidate"
ui/backend/tests/test_geometry_render_glb.py:159:    case_id = "imported_2026-04-28T00-00-00Z_atomic"
ui/backend/tests/test_geometry_render_glb.py:184:    case_id = "imported_2026-04-28T00-00-00Z_nostl"
ui/backend/tests/test_geometry_render_glb.py:197:    case_id = "imported_2026-04-28T00-00-00Z_garbage"
ui/backend/tests/test_geometry_render_glb.py:214:    case_id = "imported_2026-04-28T00-00-00Z_upper"
ui/backend/tests/test_geometry_render_glb.py:232:    case_id = "imported_2026-04-28T00-00-00Z_stl_symlink"
ui/backend/services/render/geometry_glb.py:135:        f".tmp.{secrets.token_hex(4)}{target.suffix}"
ui/backend/tests/test_phase5_byte_repro.py:104:    case_id = path.parent.name
ui/backend/services/case_visualize/velocity_slice.py:34:    CONTAINER_WORK_BASE,
ui/backend/services/case_visualize/velocity_slice.py:184:    container_work_dir = f"{CONTAINER_WORK_BASE}/{case_host_dir.name}"
ui/backend/services/case_visualize/velocity_slice.py:188:        container.exec_run(
ui/backend/services/case_visualize/velocity_slice.py:192:                f"mkdir -p {container_work_dir} && chmod 777 {container_work_dir}",
ui/backend/services/case_visualize/velocity_slice.py:195:        ok = container.put_archive(
ui/backend/services/case_visualize/velocity_slice.py:196:            path=CONTAINER_WORK_BASE,
ui/backend/services/case_visualize/velocity_slice.py:214:        result = container.exec_run(cmd=["bash", "-c", bash_cmd])
ui/backend/services/case_visualize/velocity_slice.py:217:    if result.exit_code != 0:
ui/backend/services/case_visualize/velocity_slice.py:219:            f"postProcess exited {result.exit_code}: "
ui/backend/tests/test_field_sample.py:93:    case_id = "imported_2026-04-28T00-00-00Z_field"
ui/backend/tests/test_field_sample.py:110:    case_id = "imported_2026-04-28T00-00-00Z_fieldhit"
ui/backend/tests/test_field_sample.py:124:    case_id = "imported_2026-04-28T00-00-00Z_fieldinval"
ui/backend/tests/test_field_sample.py:156:    case_id = "imported_2026-04-28T00-00-00Z_norun"
ui/backend/tests/test_field_sample.py:164:    case_id = "imported_2026-04-28T00-00-00Z_nofield"
ui/backend/tests/test_field_sample.py:176:    case_id = "imported_2026-04-28T00-00-00Z_uniform"
ui/backend/tests/test_field_sample.py:191:    case_id = "imported_2026-04-28T00-00-00Z_garbagefield"
ui/backend/tests/test_field_sample.py:203:    case_id = "imported_2026-04-28T00-00-00Z_trav"
ui/backend/tests/test_field_sample.py:214:    case_id = "imported_2026-04-28T00-00-00Z_travf"
ui/backend/tests/test_field_sample.py:231:    case_id = "imported_2026-04-28T00-00-00Z_source_vanish"
ui/backend/tests/test_field_sample.py:269:    case_id = "imported_2026-04-28T00-00-00Z_pre_replace_race"
ui/backend/tests/test_field_sample.py:309:    case_id = "imported_2026-04-28T00-00-00Z_symlink"
ui/backend/tests/test_field_sample.py:329:    case_id = "imported_2026-04-28T00-00-00Z_routefield"
ui/backend/tests/test_field_sample.py:353:    case_id = "imported_2026-04-28T00-00-00Z_route_uniform"
ui/backend/tests/test_field_sample.py:368:    case_id = "imported_2026-04-28T00-00-00Z_routecachehit"
ui/backend/tests/test_field_sample.py:385:    case_id = "imported_2026-04-28T00-00-00Z_scientific"
ui/backend/tests/test_field_sample.py:412:    case_id = "imported_2026-04-28T00-00-00Z_mismatch"

exec
/bin/zsh -lc "python - <<'PY'
from pathlib import Path
import inspect
from ui.backend.services.meshing_gmsh import to_foam
print('CONTAINER_WORK_BASE =', to_foam.CONTAINER_WORK_BASE)
PY" in /Users/Zhuanz/Desktop/cfd-harness-unified
 exited 1 in 0ms:
Traceback (most recent call last):
  File "<stdin>", line 3, in <module>
  File "/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/meshing_gmsh/__init__.py", line 27, in <module>
    from .pipeline import MeshResult, mesh_imported_case
  File "/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/meshing_gmsh/pipeline.py", line 20, in <module>
    from ui.backend.services.case_drafts import is_safe_case_id
  File "/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/case_drafts.py", line 27, in <module>
    import yaml
ModuleNotFoundError: No module named 'yaml'

exec
/bin/zsh -lc 'pytest -q ui/backend/tests/test_solver_streamer.py -q' in /Users/Zhuanz/Desktop/cfd-harness-unified
 exited 4 in 176ms:
ImportError while loading conftest '/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/conftest.py'.
ui/backend/tests/conftest.py:7: in <module>
    import trimesh
E   ModuleNotFoundError: No module named 'trimesh'

exec
/bin/zsh -lc "nl -ba ui/backend/services/case_solve/solver_runner.py | sed -n '180,285p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   180	    except docker.errors.NotFound as exc:
   181	        raise SolverRunError(
   182	            f"container '{container_name}' not found."
   183	        ) from exc
   184	    except docker.errors.DockerException as exc:
   185	        raise SolverRunError(f"docker client init failed: {exc}") from exc
   186	
   187	    container_work_dir = f"{CONTAINER_WORK_BASE}/{case_host_dir.name}"
   188	
   189	    try:
   190	        # Stage the host case dir into the container, retagged for
   191	        # openfoam UID. Mirrors gmshToFoam staging — same retag pattern.
   192	        container.exec_run(
   193	            cmd=[
   194	                "bash",
   195	                "-c",
   196	                f"mkdir -p {container_work_dir} && "
   197	                f"chmod 777 {container_work_dir}",
   198	            ]
   199	        )
   200	        ok = container.put_archive(
   201	            path=CONTAINER_WORK_BASE,
   202	            data=_make_tarball(case_host_dir),
   203	        )
   204	        if not ok:
   205	            raise SolverRunError(
   206	                f"failed to stage case into container at {container_work_dir}"
   207	            )
   208	    except docker.errors.DockerException as exc:
   209	        raise SolverRunError(
   210	            f"docker SDK error preparing container workspace: {exc}"
   211	        ) from exc
   212	    except FileNotFoundError as exc:
   213	        raise SolverRunError(
   214	            f"case dir vanished while staging: {exc}"
   215	        ) from exc
   216	    except OSError as exc:
   217	        raise SolverRunError(
   218	            f"host filesystem fault staging case: {exc}"
   219	        ) from exc
   220	
   221	    bash_cmd = (
   222	        "source /opt/openfoam10/etc/bashrc && "
   223	        f"cd {container_work_dir} && "
   224	        "icoFoam > log.icoFoam 2>&1"
   225	    )
   226	    try:
   227	        exec_result = container.exec_run(cmd=["bash", "-c", bash_cmd])
   228	    except docker.errors.DockerException as exc:
   229	        raise SolverRunError(f"docker SDK error invoking icoFoam: {exc}") from exc
   230	
   231	    # Always pull the log first, even if exit_code != 0 — we need it
   232	    # for the rejection message.
   233	    log_dest = case_host_dir / "log.icoFoam"
   234	    try:
   235	        bits, _ = container.get_archive(f"{container_work_dir}/log.icoFoam")
   236	        _extract_tarball(
   237	            b"".join(bits),
   238	            case_host_dir.parent,
   239	        )
   240	        # The tarball lays the file at <case_host_dir>.parent/log.icoFoam
   241	        # (gmshToFoam used a similar dance — here case_host_dir.name is
   242	        # the archived top-level entry, so the file lands inside
   243	        # case_host_dir already if it was at the case root; otherwise
   244	        # flatten).
   245	        if not log_dest.exists():
   246	            stray = case_host_dir.parent / "log.icoFoam"
   247	            if stray.exists():
   248	                stray.replace(log_dest)
   249	    except Exception:  # noqa: BLE001 — best-effort log retrieval
   250	        try:
   251	            log_dest.write_text(
   252	                "(log file could not be retrieved from container)\n",
   253	                encoding="utf-8",
   254	            )
   255	        except OSError as exc:
   256	            raise SolverRunError(
   257	                f"failed to persist fallback icoFoam log at {log_dest}: {exc}"
   258	            ) from exc
   259	
   260	    if exec_result.exit_code != 0:
   261	        raise SolverRunError(
   262	            f"icoFoam exited with code {exec_result.exit_code}; "
   263	            f"see {log_dest} for full output."
   264	        )
   265	
   266	    log_text = log_dest.read_text(errors="replace")
   267	    parsed = _parse_log(log_text)
   268	    converged = _is_converged(parsed)
   269	
   270	    # Pull time directories back to the host. The container produced
   271	    # /tmp/.../<case>/<time>/ for each writeInterval; mirror them onto
   272	    # the host case dir so results_extractor can read them.
   273	    pulled: list[str] = []
   274	    try:
   275	        ls_out = container.exec_run(
   276	            cmd=[
   277	                "bash",
   278	                "-c",
   279	                f"cd {container_work_dir} && ls -d [0-9]* 2>/dev/null",
   280	            ]
   281	        )
   282	        time_dirs_raw = ls_out.output.decode(errors="replace").strip().split()
   283	        for td in time_dirs_raw:
   284	            try:
   285	                bits, _ = container.get_archive(f"{container_work_dir}/{td}")

exec
/bin/zsh -lc 'rg -n "is_safe_case_id|safe_case_id|case_dir =|user_drafts|imported_" ui/backend/services ui/backend/routes ui/backend/tests -S' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
ui/backend/tests/test_geometry_render_route.py:46:    """Redirect the IMPORTED_DIR template to tmp_path so tests don't pollute
ui/backend/tests/test_geometry_render_route.py:47:    the repo's user_drafts/imported/ tree."""
ui/backend/tests/test_geometry_render_route.py:48:    drafts = tmp_path / "user_drafts"
ui/backend/tests/test_geometry_render_route.py:52:    monkeypatch.setattr(template_clone, "IMPORTED_DIR", imported)
ui/backend/tests/test_geometry_render_route.py:56:def _stage_case(imported_root: Path, case_id: str, stl_bytes: bytes) -> Path:
ui/backend/tests/test_geometry_render_route.py:58:    case_dir = imported_root / case_id
ui/backend/tests/test_geometry_render_route.py:67:    case_id = "imported_2026-04-28T00-00-00Z_cube0001"
ui/backend/tests/test_geometry_render_route.py:92:    case_id = f"imported_2026-04-28T00-00-00Z_{fixture_label}"
ui/backend/tests/test_geometry_render_route.py:106:    response = client.get("/api/cases/imported_unknown_case/geometry/stl")
ui/backend/tests/test_geometry_render_route.py:111:    case_id = "imported_2026-04-28T00-00-00Z_notrisurface"
ui/backend/tests/test_geometry_render_route.py:120:    case_id = "imported_2026-04-28T00-00-00Z_emptytrisurface"
ui/backend/tests/test_geometry_render_route.py:128:def test_get_case_stl_404_for_unsafe_case_id():
ui/backend/tests/test_geometry_render_route.py:141:    case_id = "imported_2026-04-28T00-00-00Z_uppercase"
ui/backend/tests/test_geometry_render_route.py:143:    case_dir = isolated_imported / case_id
ui/backend/services/grid_convergence.py:215:    case_dir = base / case_id
ui/backend/routes/case_visualize.py:20:from ui.backend.services.case_drafts import is_safe_case_id
ui/backend/routes/case_visualize.py:21:from ui.backend.services.case_scaffold import IMPORTED_DIR
ui/backend/routes/case_visualize.py:36:    if not is_safe_case_id(case_id):
ui/backend/routes/case_visualize.py:38:    case_dir = IMPORTED_DIR / case_id
ui/backend/routes/case_visualize.py:60:    case_dir = _resolve(case_id)
ui/backend/routes/case_visualize.py:74:    case_dir = _resolve(case_id)
ui/backend/routes/case_visualize.py:91:    case_dir = _resolve(case_id)
ui/backend/tests/test_wizard_drivers.py:281:    """M2 contract: when ui/backend/user_drafts/{case_id}.yaml exists, the
ui/backend/tests/test_wizard_drivers.py:290:    drafts_root = tmp_path / "ui" / "backend" / "user_drafts"
ui/backend/tests/test_wizard_drivers.py:308:    # we monkeypatch the user_drafts directory location by patching
ui/backend/tests/test_wizard_drivers.py:320:        draft_path = tmp_path / "ui" / "backend" / "user_drafts" / f"{case_id}.yaml"
ui/backend/services/comparison_report.py:544:    case_dir = _FIXTURE_ROOT / case_id
ui/backend/routes/case_editor.py:8:Writes land in ``ui/backend/user_drafts/`` — NEVER in
ui/backend/tests/test_wizard_route.py:4:(+ user_drafts side effect), and SSE phase stream framing.
ui/backend/tests/test_wizard_route.py:44:def test_create_draft_writes_to_user_drafts_and_returns_yaml() -> None:
ui/backend/tests/test_wizard_route.py:413:def test_preview_does_not_write_user_drafts() -> None:
ui/backend/tests/test_wizard_route.py:417:    on params. If preview also wrote a draft, the user_drafts dir would
ui/backend/services/case_scaffold/bc_injector.py:14:from .manifest_writer import SOURCE_ORIGIN_IMPORTED_USER
ui/backend/services/case_scaffold/bc_injector.py:119:| Source: {SOURCE_ORIGIN_IMPORTED_USER} · Origin: {origin_filename}                            |
ui/backend/services/case_scaffold/bc_injector.py:131:        name imported_geometry;
ui/backend/routes/mesh_imported.py:17:from ui.backend.services.meshing_gmsh import MeshResult, mesh_imported_case
ui/backend/routes/mesh_imported.py:58:def mesh_imported_route(
ui/backend/routes/mesh_imported.py:69:        result = mesh_imported_case(case_id, mesh_mode=request.mesh_mode)
ui/backend/tests/test_meshing_gmsh.py:24:    run_gmsh_on_imported_case,
ui/backend/tests/test_meshing_gmsh.py:28:    mesh_imported_case,
ui/backend/tests/test_meshing_gmsh.py:72:    result = run_gmsh_on_imported_case(
ui/backend/tests/test_meshing_gmsh.py:90:        run_gmsh_on_imported_case(
ui/backend/tests/test_meshing_gmsh.py:100:def test_mesh_imported_case_unsafe_id_rejects():
ui/backend/tests/test_meshing_gmsh.py:102:        mesh_imported_case("../etc/passwd")
ui/backend/tests/test_meshing_gmsh.py:106:def test_mesh_imported_case_missing_dir_rejects():
ui/backend/tests/test_meshing_gmsh.py:108:        mesh_imported_case("imported_2099-01-01T00-00-00Z_deadbeef")
ui/backend/tests/test_meshing_gmsh.py:112:def test_mesh_imported_case_cap_exceeded_path_clean(tmp_path: Path, monkeypatch):
ui/backend/tests/test_meshing_gmsh.py:118:    case_dir = tmp_path / "imported_TEST_capcheck"
ui/backend/tests/test_meshing_gmsh.py:134:    monkeypatch.setattr(pipeline_mod, "_resolve_imported_case", fake_resolve)
ui/backend/tests/test_meshing_gmsh.py:136:        pipeline_mod, "run_gmsh_on_imported_case", lambda **kw: fake_result
ui/backend/tests/test_meshing_gmsh.py:147:        mesh_imported_case("imported_TEST_capcheck", mesh_mode="power")
ui/backend/tests/test_meshing_gmsh.py:165:        # run_gmsh_on_imported_case but raises plain Exception from
ui/backend/tests/test_meshing_gmsh.py:395:    case_dir = tmp_path / "imported_TEST_dockerfail"
ui/backend/tests/test_meshing_gmsh.py:419:    case_dir = tmp_path / "no_msh_here"
ui/backend/tests/test_meshing_gmsh.py:432:    case_dir = tmp_path / "imported_TEST_dock"
ui/backend/tests/test_meshing_gmsh.py:466:    """The public run_gmsh_on_imported_case wrapper spawns a child
ui/backend/tests/test_meshing_gmsh.py:480:    result = runner_mod.run_gmsh_on_imported_case(
ui/backend/tests/test_meshing_gmsh.py:502:        runner_mod.run_gmsh_on_imported_case(
ui/backend/tests/test_meshing_gmsh.py:664:        runner_mod.run_gmsh_on_imported_case(
ui/backend/tests/test_meshing_gmsh.py:859:def test_resolve_imported_case_handles_concurrent_triSurface_deletion(
ui/backend/tests/test_meshing_gmsh.py:869:    case_id = "imported_2026-04-28T00-00-00Z_racecase"
ui/backend/tests/test_meshing_gmsh.py:870:    case_dir = tmp_path / "imported" / case_id
ui/backend/tests/test_meshing_gmsh.py:875:    monkeypatch.setattr(pipeline_mod, "IMPORTED_DIR", tmp_path / "imported")
ui/backend/tests/test_meshing_gmsh.py:887:        pipeline_mod._resolve_imported_case(case_id)
ui/backend/tests/test_meshing_gmsh.py:899:    case_dir = tmp_path / "imported_TEST_tarball_race"
ui/backend/tests/test_meshing_gmsh.py:1042:    case_dir = tmp_path / "imported_TEST_log_fallback_race"
ui/backend/tests/test_meshing_gmsh.py:1086:    case_dir = tmp_path / "imported_TEST_tarball_oserror"
ui/backend/tests/test_meshing_gmsh.py:1119:    case_dir = tmp_path / "imported_TEST_polymesh_copyback"
ui/backend/tests/test_meshing_gmsh.py:1173:    case_dir = tmp_path / "imported_TEST_msh_stat_eacces"
ui/backend/services/case_scaffold/manifest_writer.py:2:``user_drafts/{case_id}.yaml`` (consumed by case_drafts / case_editor).
ui/backend/services/case_scaffold/manifest_writer.py:22:SOURCE_ORIGIN_IMPORTED_USER = "imported_user"
ui/backend/services/case_scaffold/manifest_writer.py:54:        "source_origin": SOURCE_ORIGIN_IMPORTED_USER,
ui/backend/services/case_scaffold/manifest_writer.py:73:    imported_case_dir: Path,
ui/backend/services/case_scaffold/manifest_writer.py:83:    # Try to express imported_case_dir relative to repo root for portability.
ui/backend/services/case_scaffold/manifest_writer.py:87:        rel_imported = imported_case_dir.relative_to(REPO_ROOT).as_posix()
ui/backend/services/case_scaffold/manifest_writer.py:89:        rel_imported = imported_case_dir.as_posix()
ui/backend/services/case_scaffold/manifest_writer.py:96:        # source_origin == imported_user guard in wizard_drivers; M7 will
ui/backend/services/case_scaffold/manifest_writer.py:103:        "source_origin": SOURCE_ORIGIN_IMPORTED_USER,  # M5.0 schema-additive field
ui/backend/services/case_scaffold/manifest_writer.py:105:        "imported_case_dir": rel_imported,
ui/backend/services/case_scaffold/manifest_writer.py:116:                "id": "imported_fluid",
ui/backend/services/case_scaffold/manifest_writer.py:144:    imported_case_dir: Path,
ui/backend/services/case_scaffold/manifest_writer.py:153:        imported_case_dir=imported_case_dir,
ui/backend/services/case_scaffold/__init__.py:3:Public entry: :func:`scaffold_imported_case`. Given a clean ingest report
ui/backend/services/case_scaffold/__init__.py:5:case directory tree under ``ui/backend/user_drafts/imported/{case_id}/``
ui/backend/services/case_scaffold/__init__.py:7:case YAML at ``ui/backend/user_drafts/{case_id}.yaml`` so the existing
ui/backend/services/case_scaffold/__init__.py:14:    SOURCE_ORIGIN_IMPORTED_USER,
ui/backend/services/case_scaffold/__init__.py:20:    IMPORTED_DIR,
ui/backend/services/case_scaffold/__init__.py:22:    allocate_imported_case_id,
ui/backend/services/case_scaffold/__init__.py:23:    create_imported_case_dir,
ui/backend/services/case_scaffold/__init__.py:24:    scaffold_imported_case,
ui/backend/services/case_scaffold/__init__.py:29:    "IMPORTED_DIR",
ui/backend/services/case_scaffold/__init__.py:30:    "SOURCE_ORIGIN_IMPORTED_USER",
ui/backend/services/case_scaffold/__init__.py:32:    "allocate_imported_case_id",
ui/backend/services/case_scaffold/__init__.py:33:    "create_imported_case_dir",
ui/backend/services/case_scaffold/__init__.py:34:    "scaffold_imported_case",
ui/backend/tests/test_convergence_attestor.py:688:    case_dir = _FIELDS / case
ui/backend/tests/test_case_editor.py:21:    monkeypatch.setattr(case_drafts, "DRAFTS_DIR", tmp_path / "user_drafts")
ui/backend/services/case_scaffold/template_clone.py:5:    ui/backend/user_drafts/{case_id}.yaml          ← editor-facing case YAML
ui/backend/services/case_scaffold/template_clone.py:6:    ui/backend/user_drafts/imported/{case_id}/
ui/backend/services/case_scaffold/template_clone.py:11:The editor-facing ``user_drafts/{case_id}.yaml`` keeps M5.0 fully
ui/backend/services/case_scaffold/template_clone.py:30:from ui.backend.services.case_drafts import is_safe_case_id
ui/backend/services/case_scaffold/template_clone.py:38:DRAFTS_DIR = REPO_ROOT / "ui" / "backend" / "user_drafts"
ui/backend/services/case_scaffold/template_clone.py:39:IMPORTED_DIR = DRAFTS_DIR / "imported"
ui/backend/services/case_scaffold/template_clone.py:45:    imported_case_dir: Path     # user_drafts/imported/{case_id}/
ui/backend/services/case_scaffold/template_clone.py:46:    triSurface_path: Path       # imported_case_dir / triSurface / origin_filename
ui/backend/services/case_scaffold/template_clone.py:47:    shm_stub_path: Path         # imported_case_dir / system / snappyHexMeshDict.stub
ui/backend/services/case_scaffold/template_clone.py:48:    manifest_path: Path         # imported_case_dir / case_manifest.yaml
ui/backend/services/case_scaffold/template_clone.py:49:    case_yaml_path: Path        # user_drafts / {case_id}.yaml
ui/backend/services/case_scaffold/template_clone.py:52:def allocate_imported_case_id(
ui/backend/services/case_scaffold/template_clone.py:58:    Format: ``imported_YYYY-MM-DDTHH-MM-SSZ_XXXXXXXX`` (UTC; ``-`` rather
ui/backend/services/case_scaffold/template_clone.py:60:    guard in ``case_drafts.is_safe_case_id``).
ui/backend/services/case_scaffold/template_clone.py:67:    case_id = f"imported_{when}_{rand}"
ui/backend/services/case_scaffold/template_clone.py:68:    if not is_safe_case_id(case_id):
ui/backend/services/case_scaffold/template_clone.py:73:def create_imported_case_dir(case_id: str) -> Path:
ui/backend/services/case_scaffold/template_clone.py:75:    if not is_safe_case_id(case_id):
ui/backend/services/case_scaffold/template_clone.py:77:    root = IMPORTED_DIR / case_id
ui/backend/services/case_scaffold/template_clone.py:94:def scaffold_imported_case(
ui/backend/services/case_scaffold/template_clone.py:110:            "scaffold_imported_case called with non-empty report.errors: "
ui/backend/services/case_scaffold/template_clone.py:114:    cid = case_id or allocate_imported_case_id(now=now)
ui/backend/services/case_scaffold/template_clone.py:116:    root = create_imported_case_dir(cid)
ui/backend/services/case_scaffold/template_clone.py:142:        imported_case_dir=root,
ui/backend/services/case_scaffold/template_clone.py:148:        imported_case_dir=root,
ui/backend/routes/case_solve.py:33:from ui.backend.services.case_drafts import is_safe_case_id
ui/backend/routes/case_solve.py:34:from ui.backend.services.case_scaffold import IMPORTED_DIR
ui/backend/routes/case_solve.py:54:    if not is_safe_case_id(case_id):
ui/backend/routes/case_solve.py:62:    case_dir = IMPORTED_DIR / case_id
ui/backend/routes/case_solve.py:83:    case_dir = _resolve_case_dir(case_id)
ui/backend/routes/case_solve.py:138:    case_dir = _resolve_case_dir(case_id)
ui/backend/routes/case_solve.py:211:    case_dir = _resolve_case_dir(case_id)
ui/backend/routes/case_solve.py:272:    case_dir = _resolve_case_dir(case_id)
ui/backend/tests/test_import_geometry_route.py:22:    drafts = tmp_path / "user_drafts"
ui/backend/tests/test_import_geometry_route.py:25:    monkeypatch.setattr(template_clone, "IMPORTED_DIR", imported)
ui/backend/tests/test_import_geometry_route.py:37:    assert body["case_id"].startswith("imported_")
ui/backend/tests/test_case_scaffold.py:13:    allocate_imported_case_id,
ui/backend/tests/test_case_scaffold.py:14:    create_imported_case_dir,
ui/backend/tests/test_case_scaffold.py:15:    scaffold_imported_case,
ui/backend/tests/test_case_scaffold.py:32:    """Redirect DRAFTS_DIR + IMPORTED_DIR to tmp_path so tests don't pollute repo."""
ui/backend/tests/test_case_scaffold.py:33:    drafts = tmp_path / "user_drafts"
ui/backend/tests/test_case_scaffold.py:36:    monkeypatch.setattr(template_clone, "IMPORTED_DIR", imported)
ui/backend/tests/test_case_scaffold.py:63:    cid = allocate_imported_case_id(now=fixed, rand_hex="abcd1234")
ui/backend/tests/test_case_scaffold.py:64:    assert cid == "imported_2026-04-27T15-30-45Z_abcd1234"
ui/backend/tests/test_case_scaffold.py:68:    cid = allocate_imported_case_id()
ui/backend/tests/test_case_scaffold.py:69:    assert cid.startswith("imported_")
ui/backend/tests/test_case_scaffold.py:90:def test_create_imported_case_dir_creates_subdirs(isolated_drafts):
ui/backend/tests/test_case_scaffold.py:92:    cid = "imported_2026-04-27T00-00-00Z_aaaaaaaa"
ui/backend/tests/test_case_scaffold.py:93:    root = create_imported_case_dir(cid)
ui/backend/tests/test_case_scaffold.py:99:def test_create_imported_case_dir_is_idempotent(isolated_drafts):
ui/backend/tests/test_case_scaffold.py:100:    cid = "imported_2026-04-27T00-00-00Z_bbbbbbbb"
ui/backend/tests/test_case_scaffold.py:101:    create_imported_case_dir(cid)
ui/backend/tests/test_case_scaffold.py:102:    create_imported_case_dir(cid)  # second call must not raise
ui/backend/tests/test_case_scaffold.py:105:def test_create_imported_case_dir_rejects_unsafe_id(isolated_drafts):
ui/backend/tests/test_case_scaffold.py:107:        create_imported_case_dir("../traversal_attempt")
ui/backend/tests/test_case_scaffold.py:117:    result = scaffold_imported_case(
ui/backend/tests/test_case_scaffold.py:122:        case_id="imported_2026-04-27T12-00-00Z_deadbeef",
ui/backend/tests/test_case_scaffold.py:125:    assert result.case_id == "imported_2026-04-27T12-00-00Z_deadbeef"
ui/backend/tests/test_case_scaffold.py:126:    assert result.imported_case_dir == imported / result.case_id
ui/backend/tests/test_case_scaffold.py:140:    control_dict = result.imported_case_dir / "system" / "controlDict"
ui/backend/tests/test_case_scaffold.py:151:    result = scaffold_imported_case(
ui/backend/tests/test_case_scaffold.py:171:    assert manifest["source_origin"] == "imported_user"
ui/backend/tests/test_case_scaffold.py:181:    result = scaffold_imported_case(
ui/backend/tests/test_case_scaffold.py:194:    assert parsed["source_origin"] == "imported_user"
ui/backend/tests/test_case_scaffold.py:197:    assert "imported_case_dir" in parsed
ui/backend/tests/test_case_scaffold.py:207:        scaffold_imported_case(
ui/backend/routes/import_geometry.py:23:from ui.backend.services.case_scaffold import scaffold_imported_case
ui/backend/routes/import_geometry.py:126:    result = scaffold_imported_case(
ui/backend/routes/geometry_render.py:6:Both routes share path-traversal defense (``is_safe_case_id`` + post-
ui/backend/routes/geometry_render.py:8:(``user_drafts/imported/{case_id}/triSurface/*.stl``). The /render
ui/backend/routes/geometry_render.py:17:from ui.backend.services.case_drafts import is_safe_case_id
ui/backend/routes/geometry_render.py:46:    if not is_safe_case_id(case_id):
ui/backend/routes/geometry_render.py:49:    imported_root = template_clone.IMPORTED_DIR / case_id
ui/backend/routes/geometry_render.py:50:    triSurface_dir = imported_root / "triSurface"
ui/backend/routes/geometry_render.py:67:        resolved.relative_to(template_clone.IMPORTED_DIR.resolve())
ui/backend/routes/geometry_render.py:101:        resolved.relative_to(template_clone.IMPORTED_DIR.resolve())
ui/backend/routes/geometry_render.py:136:        resolved.relative_to(template_clone.IMPORTED_DIR.resolve())
ui/backend/routes/geometry_render.py:178:        resolved.relative_to(template_clone.IMPORTED_DIR.resolve())
ui/backend/routes/geometry_render.py:222:        resolved.relative_to(template_clone.IMPORTED_DIR.resolve())
ui/backend/tests/test_grid_convergence_gci.py:128:    case_dir = tmp_path / "nonexistent_case"
ui/backend/services/wizard.py:5:to the existing user_drafts store.
ui/backend/services/wizard.py:338:    """Render YAML from template + write to user_drafts via existing
ui/backend/services/wizard_drivers.py:11:    events. Whitelist defaults only; M2 wires user_drafts overrides.
ui/backend/services/wizard_drivers.py:199:#   1. ui/backend/user_drafts/{case_id}.yaml — what /workbench/case/{id}/edit
ui/backend/services/wizard_drivers.py:351:      1. ``ui/backend/user_drafts/{case_id}.yaml`` (single-case YAML doc as
ui/backend/services/wizard_drivers.py:375:    # 1. Try user_drafts first (M2 override surface).
ui/backend/services/wizard_drivers.py:376:    draft_path = repo_root / "ui" / "backend" / "user_drafts" / f"{case_id}.yaml"
ui/backend/services/wizard_drivers.py:402:                f"case_id {case_id!r} not in user_drafts nor knowledge/whitelist.yaml"
ui/backend/services/wizard_drivers.py:409:    if entry.get("source_origin") == "imported_user":
ui/backend/services/wizard_drivers.py:412:            "imported_user) — the run path is not implemented until M7. "
ui/backend/services/wizard_drivers.py:491:                "(RealSolverDriver — user_drafts override → whitelist fallback)"
ui/backend/tests/test_demo_fixtures_route.py:84:    assert body["case_id"].startswith("imported_")
ui/backend/services/render/bc_glb.py:33:from ui.backend.services.case_drafts import is_safe_case_id
ui/backend/services/render/bc_glb.py:89:def _imported_case_dir(case_id: str) -> Path:
ui/backend/services/render/bc_glb.py:90:    return template_clone.IMPORTED_DIR / case_id
ui/backend/services/render/bc_glb.py:101:    outside IMPORTED_DIR. This helper mirrors
ui/backend/services/render/bc_glb.py:399:    if not is_safe_case_id(case_id):
ui/backend/services/render/bc_glb.py:404:    case_dir = _imported_case_dir(case_id)
ui/backend/tests/test_mesh_imported_route.py:19:        "/api/import/imported_2099-01-01T00-00-00Z_deadbeef/mesh",
ui/backend/tests/test_mesh_imported_route.py:27:def test_mesh_route_unsafe_case_id_returns_404():
ui/backend/tests/test_mesh_imported_route.py:28:    # Path-traversal attempts are caught by is_safe_case_id; the URL
ui/backend/tests/test_mesh_imported_route.py:54:        case_id="imported_TEST_route",
ui/backend/tests/test_mesh_imported_route.py:65:    with patch.object(route_mod, "mesh_imported_case", return_value=fake):
ui/backend/tests/test_mesh_imported_route.py:67:            "/api/import/imported_TEST_route/mesh",
ui/backend/tests/test_mesh_imported_route.py:73:    assert body["case_id"] == "imported_TEST_route"
ui/backend/tests/test_mesh_imported_route.py:89:    with patch.object(route_mod, "mesh_imported_case", side_effect=err):
ui/backend/tests/test_mesh_imported_route.py:91:            "/api/import/imported_TEST_overcap/mesh",
ui/backend/tests/test_mesh_imported_route.py:103:    with patch.object(route_mod, "mesh_imported_case", side_effect=err):
ui/backend/tests/test_mesh_imported_route.py:105:            "/api/import/imported_TEST_diverge/mesh",
ui/backend/tests/test_solver_streamer.py:96:    case_dir = tmp_path / "case_001"
ui/backend/tests/test_solver_streamer.py:112:    case_dir = tmp_path / "case_001"
ui/backend/tests/test_solver_streamer.py:157:    case_dir = tmp_path / "case_release"
ui/backend/tests/test_solver_streamer.py:231:    case_dir = tmp_path / "case_suffix"
ui/backend/tests/test_solver_streamer.py:285:    case_dir = tmp_path / "case_staging_regression"
ui/backend/tests/test_solver_streamer.py:362:    case_dir = tmp_path / "case_immediate_close"
ui/backend/tests/test_solver_streamer.py:396:    case_dir = tmp_path / "case_disconnect"
ui/backend/tests/test_field_artifacts_route.py:147:    case_dir = fields_root / "lid_driven_cavity"
ui/backend/tests/test_field_artifacts_route.py:168:    case_dir = fields_root / "lid_driven_cavity" / "20260421T000000Z"
ui/backend/tests/test_field_artifacts_route.py:203:    case_dir = fields_root / "lid_driven_cavity"
ui/backend/tests/test_mesh_wireframe.py:94:    drafts = tmp_path / "user_drafts"
ui/backend/tests/test_mesh_wireframe.py:98:    monkeypatch.setattr(template_clone, "IMPORTED_DIR", imported)
ui/backend/tests/test_mesh_wireframe.py:159:    case_id = "imported_2026-04-28T00-00-00Z_oob_face"
ui/backend/tests/test_mesh_wireframe.py:160:    case_dir = isolated_imported / case_id
ui/backend/tests/test_mesh_wireframe.py:185:    case_id = "imported_2026-04-28T00-00-00Z_polymesh_symlink"
ui/backend/tests/test_mesh_wireframe.py:186:    case_dir = isolated_imported / case_id
ui/backend/tests/test_mesh_wireframe.py:275:    case_id = "imported_2026-04-28T00-00-00Z_meshhit"
ui/backend/tests/test_mesh_wireframe.py:276:    case_dir = isolated_imported / case_id
ui/backend/tests/test_mesh_wireframe.py:290:    case_id = "imported_2026-04-28T00-00-00Z_meshinval"
ui/backend/tests/test_mesh_wireframe.py:291:    case_dir = isolated_imported / case_id
ui/backend/tests/test_mesh_wireframe.py:307:        build_mesh_wireframe_glb("imported_unknown")
ui/backend/tests/test_mesh_wireframe.py:311:def test_build_mesh_wireframe_glb_404_for_unsafe_case_id(isolated_imported: Path):
ui/backend/tests/test_mesh_wireframe.py:318:    case_id = "imported_2026-04-28T00-00-00Z_nomesh"
ui/backend/tests/test_mesh_wireframe.py:327:    case_id = "imported_2026-04-28T00-00-00Z_garbage"
ui/backend/tests/test_mesh_wireframe.py:328:    case_dir = isolated_imported / case_id
ui/backend/tests/test_mesh_wireframe.py:343:    case_id = "imported_2026-04-28T00-00-00Z_cubemesh"
ui/backend/tests/test_mesh_wireframe.py:344:    case_dir = isolated_imported / case_id
ui/backend/tests/test_mesh_wireframe.py:358:    response = client.get("/api/cases/imported_unknown/mesh/render")
ui/backend/tests/test_mesh_wireframe.py:363:    case_id = "imported_2026-04-28T00-00-00Z_nopolymesh"
ui/backend/tests/test_mesh_wireframe.py:372:    case_id = "imported_2026-04-28T00-00-00Z_garbagemesh"
ui/backend/tests/test_mesh_wireframe.py:373:    case_dir = isolated_imported / case_id
ui/backend/tests/test_mesh_wireframe.py:385:    case_id = "imported_2026-04-28T00-00-00Z_cachebyteequal"
ui/backend/tests/test_mesh_wireframe.py:386:    case_dir = isolated_imported / case_id
ui/backend/tests/test_mesh_wireframe.py:398:    case_id = "imported_2026-04-28T00-00-00Z_atomicmesh"
ui/backend/tests/test_mesh_wireframe.py:399:    case_dir = isolated_imported / case_id
ui/backend/services/case_drafts.py:3:Phase 1 Case Editor persists edits to ``ui/backend/user_drafts/{case_id}.yaml``.
ui/backend/services/case_drafts.py:11:    1. ``ui/backend/user_drafts/{case_id}.yaml`` — last saved draft
ui/backend/services/case_drafts.py:35:DRAFTS_DIR = REPO_ROOT / "ui" / "backend" / "user_drafts"
ui/backend/services/case_drafts.py:56:def is_safe_case_id(case_id: str) -> bool:
ui/backend/services/case_drafts.py:62:    if not is_safe_case_id(case_id):
ui/backend/services/case_drafts.py:70:    Order: (1) user_drafts/{case_id}.yaml if it exists, else
ui/backend/services/render/field_sample.py:14:    <imported_case_dir>/{run_id}/{name}        (M5.1 OpenFOAM time-dir)
ui/backend/services/render/field_sample.py:27:    <imported_case_dir>/.render_cache/field-{run_id}-{name}.bin
ui/backend/services/render/field_sample.py:40:from ui.backend.services.case_drafts import is_safe_case_id
ui/backend/services/render/field_sample.py:78:def _imported_case_dir(case_id: str) -> Path:
ui/backend/services/render/field_sample.py:79:    return template_clone.IMPORTED_DIR / case_id
ui/backend/services/render/field_sample.py:85:    is_safe_case_id is too narrow (no dot allowed) for OpenFOAM run_ids
ui/backend/services/render/field_sample.py:113:    if not is_safe_case_id(case_id):
ui/backend/services/render/field_sample.py:118:    case_dir = _imported_case_dir(case_id)
ui/backend/services/render/field_sample.py:142:    # is_safe_case_id + segment validators stop literal traversal in URL
ui/backend/services/render/field_sample.py:144:    # pointing outside IMPORTED_DIR would still let us read+transcode an
ui/backend/services/render/field_sample.py:295:    case_dir = _imported_case_dir(case_id)
ui/backend/services/meshing_gmsh/gmsh_runner.py:3:The route invokes :func:`run_gmsh_on_imported_case` after M5.0's ingest
ui/backend/services/meshing_gmsh/gmsh_runner.py:329:def run_gmsh_on_imported_case(
ui/backend/tests/test_bc_glb.py:116:    drafts = tmp_path / "user_drafts"
ui/backend/tests/test_bc_glb.py:120:    monkeypatch.setattr(template_clone, "IMPORTED_DIR", imported)
ui/backend/tests/test_bc_glb.py:144:    case_dir = isolated_imported / "case_001"
ui/backend/tests/test_bc_glb.py:175:    case_dir = isolated_imported / "case_001"
ui/backend/tests/test_bc_glb.py:187:    case_dir = isolated_imported / "case_001"
ui/backend/tests/test_bc_glb.py:195:    case_dir = isolated_imported / "case_001"
ui/backend/tests/test_bc_glb.py:208:    case_dir = isolated_imported / "case_001"
ui/backend/tests/test_bc_glb.py:226:    case_dir = isolated_imported / "case_001"
ui/backend/tests/test_bc_glb.py:248:    case_dir = isolated_imported / "case_001"
ui/backend/tests/test_bc_glb.py:270:    case_dir = isolated_imported / "case_001"
ui/backend/tests/test_bc_glb.py:307:    case_dir = isolated_imported / "case_001"
ui/backend/tests/test_bc_glb.py:332:    case_dir = isolated_imported / "case_001"
ui/backend/tests/test_bc_glb.py:363:    case_dir = isolated_imported / "case_001"
ui/backend/services/render/mesh_wireframe.py:9:    <imported_case_dir>/.render_cache/mesh.glb
ui/backend/services/render/mesh_wireframe.py:14:    2. <case_dir>/<imported_case_id>/constant/polyMesh/{points,faces}
ui/backend/services/render/mesh_wireframe.py:15:       — fallback for cases scaffolded under user_drafts/imported/
ui/backend/services/render/mesh_wireframe.py:29:from ui.backend.services.case_drafts import is_safe_case_id
ui/backend/services/render/mesh_wireframe.py:64:def _imported_case_dir(case_id: str) -> Path:
ui/backend/services/render/mesh_wireframe.py:65:    return template_clone.IMPORTED_DIR / case_id
ui/backend/services/render/mesh_wireframe.py:94:    arbitrary file outside IMPORTED_DIR.
ui/backend/services/render/mesh_wireframe.py:218:    if not is_safe_case_id(case_id):
ui/backend/services/render/mesh_wireframe.py:223:    case_dir = _imported_case_dir(case_id)
ui/backend/services/meshing_gmsh/pipeline.py:20:from ui.backend.services.case_drafts import is_safe_case_id
ui/backend/services/meshing_gmsh/pipeline.py:21:from ui.backend.services.case_scaffold import IMPORTED_DIR
ui/backend/services/meshing_gmsh/pipeline.py:27:    run_gmsh_on_imported_case,
ui/backend/services/meshing_gmsh/pipeline.py:63:def _resolve_imported_case(case_id: str) -> tuple[Path, Path]:
ui/backend/services/meshing_gmsh/pipeline.py:65:    if not is_safe_case_id(case_id):
ui/backend/services/meshing_gmsh/pipeline.py:69:    case_dir = IMPORTED_DIR / case_id
ui/backend/services/meshing_gmsh/pipeline.py:102:def mesh_imported_case(
ui/backend/services/meshing_gmsh/pipeline.py:114:    case_dir, stl_path = _resolve_imported_case(case_id)
ui/backend/services/meshing_gmsh/pipeline.py:118:        gmsh_result: GmshRunResult = run_gmsh_on_imported_case(
ui/backend/services/render/geometry_glb.py:9:    <imported_case_dir>/.render_cache/geometry.glb
ui/backend/services/render/geometry_glb.py:29:from ui.backend.services.case_drafts import is_safe_case_id
ui/backend/services/render/geometry_glb.py:64:def _imported_case_dir(case_id: str) -> Path:
ui/backend/services/render/geometry_glb.py:65:    return template_clone.IMPORTED_DIR / case_id
ui/backend/services/render/geometry_glb.py:78:    redirect us to an arbitrary file outside IMPORTED_DIR.
ui/backend/services/render/geometry_glb.py:211:    if not is_safe_case_id(case_id):
ui/backend/services/render/geometry_glb.py:216:    case_dir = _imported_case_dir(case_id)
ui/backend/tests/test_geometry_render_glb.py:48:    """Redirect the IMPORTED_DIR template to tmp_path so cache dirs and
ui/backend/tests/test_geometry_render_glb.py:50:    drafts = tmp_path / "user_drafts"
ui/backend/tests/test_geometry_render_glb.py:54:    monkeypatch.setattr(template_clone, "IMPORTED_DIR", imported)
ui/backend/tests/test_geometry_render_glb.py:58:def _stage_case(imported_root: Path, case_id: str, stl_bytes: bytes) -> Path:
ui/backend/tests/test_geometry_render_glb.py:59:    case_dir = imported_root / case_id
ui/backend/tests/test_geometry_render_glb.py:71:    case_id = "imported_2026-04-28T00-00-00Z_cube0001"
ui/backend/tests/test_geometry_render_glb.py:94:    case_id = f"imported_2026-04-28T00-00-00Z_{fixture_label}"
ui/backend/tests/test_geometry_render_glb.py:108:    case_id = "imported_2026-04-28T00-00-00Z_cachehit"
ui/backend/tests/test_geometry_render_glb.py:123:    case_id = "imported_2026-04-28T00-00-00Z_status"
ui/backend/tests/test_geometry_render_glb.py:136:    case_id = "imported_2026-04-28T00-00-00Z_invalidate"
ui/backend/tests/test_geometry_render_glb.py:159:    case_id = "imported_2026-04-28T00-00-00Z_atomic"
ui/backend/tests/test_geometry_render_glb.py:173:    response = client.get("/api/cases/imported_unknown_case/geometry/render")
ui/backend/tests/test_geometry_render_glb.py:177:def test_get_case_geometry_render_404_for_unsafe_case_id():
ui/backend/tests/test_geometry_render_glb.py:184:    case_id = "imported_2026-04-28T00-00-00Z_nostl"
ui/backend/tests/test_geometry_render_glb.py:197:    case_id = "imported_2026-04-28T00-00-00Z_garbage"
ui/backend/tests/test_geometry_render_glb.py:214:    case_id = "imported_2026-04-28T00-00-00Z_upper"
ui/backend/tests/test_geometry_render_glb.py:215:    case_dir = isolated_imported / case_id
ui/backend/tests/test_geometry_render_glb.py:232:    case_id = "imported_2026-04-28T00-00-00Z_stl_symlink"
ui/backend/tests/test_geometry_render_glb.py:233:    case_dir = isolated_imported / case_id
ui/backend/services/meshing_gmsh/__init__.py:3:Public entry: :func:`mesh_imported_case`. Given an imported case_id (one
ui/backend/services/meshing_gmsh/__init__.py:4:already scaffolded by M5.0's ``scaffold_imported_case``), generate a 3D
ui/backend/services/meshing_gmsh/__init__.py:26:from .gmsh_runner import GmshRunResult, run_gmsh_on_imported_case
ui/backend/services/meshing_gmsh/__init__.py:27:from .pipeline import MeshResult, mesh_imported_case
ui/backend/services/meshing_gmsh/__init__.py:38:    "mesh_imported_case",
ui/backend/services/meshing_gmsh/__init__.py:39:    "run_gmsh_on_imported_case",
ui/backend/tests/test_field_sample.py:81:    drafts = tmp_path / "user_drafts"
ui/backend/tests/test_field_sample.py:85:    monkeypatch.setattr(template_clone, "IMPORTED_DIR", imported)
ui/backend/tests/test_field_sample.py:93:    case_id = "imported_2026-04-28T00-00-00Z_field"
ui/backend/tests/test_field_sample.py:94:    case_dir = isolated_imported / case_id
ui/backend/tests/test_field_sample.py:110:    case_id = "imported_2026-04-28T00-00-00Z_fieldhit"
ui/backend/tests/test_field_sample.py:111:    case_dir = isolated_imported / case_id
ui/backend/tests/test_field_sample.py:124:    case_id = "imported_2026-04-28T00-00-00Z_fieldinval"
ui/backend/tests/test_field_sample.py:125:    case_dir = isolated_imported / case_id
ui/backend/tests/test_field_sample.py:145:        build_field_payload("imported_unknown", "run_001", "p")
ui/backend/tests/test_field_sample.py:149:def test_build_field_payload_404_for_unsafe_case_id(isolated_imported: Path):
ui/backend/tests/test_field_sample.py:156:    case_id = "imported_2026-04-28T00-00-00Z_norun"
ui/backend/tests/test_field_sample.py:164:    case_id = "imported_2026-04-28T00-00-00Z_nofield"
ui/backend/tests/test_field_sample.py:165:    case_dir = isolated_imported / case_id
ui/backend/tests/test_field_sample.py:176:    case_id = "imported_2026-04-28T00-00-00Z_uniform"
ui/backend/tests/test_field_sample.py:177:    case_dir = isolated_imported / case_id
ui/backend/tests/test_field_sample.py:191:    case_id = "imported_2026-04-28T00-00-00Z_garbagefield"
ui/backend/tests/test_field_sample.py:192:    case_dir = isolated_imported / case_id
ui/backend/tests/test_field_sample.py:203:    case_id = "imported_2026-04-28T00-00-00Z_trav"
ui/backend/tests/test_field_sample.py:214:    case_id = "imported_2026-04-28T00-00-00Z_travf"
ui/backend/tests/test_field_sample.py:231:    case_id = "imported_2026-04-28T00-00-00Z_source_vanish"
ui/backend/tests/test_field_sample.py:232:    case_dir = isolated_imported / case_id
ui/backend/tests/test_field_sample.py:269:    case_id = "imported_2026-04-28T00-00-00Z_pre_replace_race"
ui/backend/tests/test_field_sample.py:270:    case_dir = isolated_imported / case_id
ui/backend/tests/test_field_sample.py:309:    case_id = "imported_2026-04-28T00-00-00Z_symlink"
ui/backend/tests/test_field_sample.py:310:    case_dir = isolated_imported / case_id
ui/backend/tests/test_field_sample.py:329:    case_id = "imported_2026-04-28T00-00-00Z_routefield"
ui/backend/tests/test_field_sample.py:330:    case_dir = isolated_imported / case_id
ui/backend/tests/test_field_sample.py:348:    response = client.get("/api/cases/imported_unknown/results/run_001/field/p")
ui/backend/tests/test_field_sample.py:353:    case_id = "imported_2026-04-28T00-00-00Z_route_uniform"
ui/backend/tests/test_field_sample.py:354:    case_dir = isolated_imported / case_id
ui/backend/tests/test_field_sample.py:368:    case_id = "imported_2026-04-28T00-00-00Z_routecachehit"
ui/backend/tests/test_field_sample.py:369:    case_dir = isolated_imported / case_id
ui/backend/tests/test_field_sample.py:385:    case_id = "imported_2026-04-28T00-00-00Z_scientific"
ui/backend/tests/test_field_sample.py:386:    case_dir = isolated_imported / case_id
ui/backend/tests/test_field_sample.py:412:    case_id = "imported_2026-04-28T00-00-00Z_mismatch"
ui/backend/tests/test_field_sample.py:413:    case_dir = isolated_imported / case_id
ui/backend/routes/demo_fixtures.py:8:(``scaffold_imported_case``) the regular drag-drop path uses.
ui/backend/routes/demo_fixtures.py:28:from ui.backend.services.case_scaffold import scaffold_imported_case
ui/backend/routes/demo_fixtures.py:229:    result = scaffold_imported_case(
ui/backend/services/validation_report.py:187:    case_dir = RUNS_DIR / case_id
ui/backend/services/validation_report.py:864:def _load_imported_draft(case_id: str) -> dict[str, Any] | None:
ui/backend/services/validation_report.py:869:    flow scaffolds cases under ``ui/backend/user_drafts/{case_id}.yaml``,
ui/backend/services/validation_report.py:873:    allowlist mirrored from ``case_drafts.is_safe_case_id``.
ui/backend/services/validation_report.py:877:    draft = REPO_ROOT / "ui" / "backend" / "user_drafts" / f"{case_id}.yaml"
ui/backend/services/validation_report.py:885:def _synthesize_imported_detail(case_id: str, draft: dict[str, Any]) -> CaseDetail:
ui/backend/services/validation_report.py:923:        draft = _load_imported_draft(case_id)
ui/backend/services/validation_report.py:926:        return _synthesize_imported_detail(case_id, draft)
ui/backend/tests/test_cases_route.py:19:from ui.backend.services.case_scaffold import scaffold_imported_case, template_clone
ui/backend/tests/test_cases_route.py:35:    """Redirect DRAFTS_DIR + IMPORTED_DIR + REPO_ROOT-derived draft path to tmp."""
ui/backend/tests/test_cases_route.py:36:    drafts = tmp_path / "user_drafts"
ui/backend/tests/test_cases_route.py:40:    monkeypatch.setattr(template_clone, "IMPORTED_DIR", imported)
ui/backend/tests/test_cases_route.py:42:    # validation_report._load_imported_draft reads via REPO_ROOT, so
ui/backend/tests/test_cases_route.py:44:    # ui/backend/user_drafts tree we'll set up.
ui/backend/tests/test_cases_route.py:46:    fake_drafts = fake_repo / "ui" / "backend" / "user_drafts"
ui/backend/tests/test_cases_route.py:63:def _seed_imported_draft(fake_drafts: Path, case_id: str) -> None:
ui/backend/tests/test_cases_route.py:78:def test_get_case_falls_through_to_imported_draft_via_http(isolated_drafts) -> None:
ui/backend/tests/test_cases_route.py:86:    case_id = "imported_2026-04-28T11-39-46Z_a4d3db45"
ui/backend/tests/test_cases_route.py:87:    _seed_imported_draft(fake_drafts, case_id)
ui/backend/tests/test_cases_route.py:103:    """Cases in neither whitelist nor user_drafts still 404 through the route."""
ui/backend/tests/test_cases_route.py:121:def test_audit_package_refuses_imported_case_ids(isolated_drafts, monkeypatch) -> None:
ui/backend/tests/test_cases_route.py:128:    case_id = "imported_2026-04-28T11-39-46Z_a4d3db45"
ui/backend/tests/test_cases_route.py:129:    _seed_imported_draft(fake_drafts, case_id)
ui/backend/tests/test_cases_route.py:142:    case_id = "imported_2026-04-28T11-39-46Z_a4d3db45"
ui/backend/tests/test_cases_route.py:143:    _seed_imported_draft(fake_drafts, case_id)
ui/backend/tests/test_cases_route.py:153:def test_get_case_e2e_imported_via_scaffold(isolated_drafts) -> None:
ui/backend/tests/test_cases_route.py:167:    result = scaffold_imported_case(
ui/backend/tests/test_cases_route.py:175:    # isolated_drafts), but validation_report._load_imported_draft reads

exec
/bin/zsh -lc "rg -n \"_prepare_stream_icofoam\\(|stream_icofoam\\(|SolveAlreadyRunning|solve-stream\" ui/backend -S" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
ui/backend/services/case_solve/solver_streamer.py:57:class SolveAlreadyRunning(SolverRunError):
ui/backend/services/case_solve/solver_streamer.py:80:            raise SolveAlreadyRunning(
ui/backend/services/case_solve/solver_streamer.py:215:def _prepare_stream_icofoam(
ui/backend/services/case_solve/solver_streamer.py:226:    :class:`SolverRunError` (or its :class:`SolveAlreadyRunning`
ui/backend/services/case_solve/solver_streamer.py:249:                raise SolveAlreadyRunning(
ui/backend/services/case_solve/solver_streamer.py:360:def stream_icofoam(
ui/backend/services/case_solve/solver_streamer.py:371:    * ``stream_icofoam(prepared=<_PreparedStream>)`` — preferred path
ui/backend/services/case_solve/solver_streamer.py:375:    * ``stream_icofoam(case_host_dir=...)`` — legacy entrypoint kept
ui/backend/services/case_solve/solver_streamer.py:391:        prepared = _prepare_stream_icofoam(
ui/backend/tests/test_solver_streamer.py:101:        _prepare_stream_icofoam(case_host_dir=case_dir)
ui/backend/tests/test_solver_streamer.py:143:        _prepare_stream_icofoam(case_host_dir=case_dir)
ui/backend/tests/test_solver_streamer.py:167:        _prepare_stream_icofoam(case_host_dir=case_dir)
ui/backend/tests/test_solver_streamer.py:178:    first is still in-flight must raise SolveAlreadyRunning so the
ui/backend/tests/test_solver_streamer.py:182:        SolveAlreadyRunning,
ui/backend/tests/test_solver_streamer.py:192:        with pytest.raises(SolveAlreadyRunning, match="already running"):
ui/backend/tests/test_solver_streamer.py:240:        prepared = _prepare_stream_icofoam(
ui/backend/tests/test_solver_streamer.py:305:        prepared = _prepare_stream_icofoam(
ui/backend/tests/test_solver_streamer.py:371:    prepared = _prepare_stream_icofoam(case_host_dir=case_dir)
ui/backend/tests/test_solver_streamer.py:373:    gen = stream_icofoam(prepared=prepared)
ui/backend/tests/test_solver_streamer.py:404:    prepared = _prepare_stream_icofoam(case_host_dir=case_dir)
ui/backend/tests/test_solver_streamer.py:406:    gen = stream_icofoam(prepared=prepared)
ui/backend/routes/case_solve.py:45:    SolveAlreadyRunning,
ui/backend/routes/case_solve.py:125:    "/import/{case_id}/solve-stream",
ui/backend/routes/case_solve.py:159:        prepared = _prepare_stream_icofoam(case_host_dir=case_dir)
ui/backend/routes/case_solve.py:160:    except SolveAlreadyRunning as exc:
ui/backend/routes/case_solve.py:189:        stream_icofoam(prepared=prepared),

exec
/bin/zsh -lc 'git status --short' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
?? .claude/MODEL_ROUTING.md
?? .planning/strategic/2026-04-26_claude_code_kickoff_prompt_pivot_v1_1.md
?? .planning/strategic/2026-04-26_strategic_advisory_memo.md
?? .planning/strategic/2026-04-26_strategic_advisory_memo_002_post_three_answers.md
?? .planning/strategic/PROJECT_HISTORY_NARRATIVE.md
?? docs/methodology/project_introduction.md
?? reports/codex_tool_reports/dec_v61_099_round1.md
?? ui/backend/schemas/ai_action.py
?? ui/backend/services/case_annotations/

exec
/bin/zsh -lc "sed -n '1,120p' reports/codex_tool_reports/dec_v61_099_round1.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba ui/backend/services/case_drafts.py | sed -n '50,90p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
    50	
    51	
    52	def _ensure_drafts_dir() -> None:
    53	    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    54	
    55	
    56	def is_safe_case_id(case_id: str) -> bool:
    57	    """Path-traversal guard: case_id must be alphanum + ``_`` + ``-`` only."""
    58	    return all(c.isalnum() or c in ("_", "-") for c in case_id) and bool(case_id)
    59	
    60	
    61	def _draft_path(case_id: str) -> Path:
    62	    if not is_safe_case_id(case_id):
    63	        raise ValueError(f"unsafe case_id: {case_id!r}")
    64	    return DRAFTS_DIR / f"{case_id}.yaml"
    65	
    66	
    67	def get_case_yaml(case_id: str) -> DraftSource:
    68	    """Return the current editor source for a case.
    69	
    70	    Order: (1) user_drafts/{case_id}.yaml if it exists, else
    71	    (2) knowledge/whitelist.yaml entry dumped as standalone YAML doc.
    72	    """
    73	    draft = _draft_path(case_id)
    74	    if draft.exists():
    75	        return DraftSource(
    76	            yaml_text=draft.read_text(encoding="utf-8"),
    77	            origin="draft",
    78	            draft_path=str(draft),
    79	        )
    80	    whitelist = _load_whitelist()
    81	    case = whitelist.get(case_id)
    82	    if case is None:
    83	        return DraftSource(yaml_text="", origin="missing", draft_path=None)
    84	    dumped = yaml.safe_dump(
    85	        case, sort_keys=False, default_flow_style=False, allow_unicode=True
    86	    )
    87	    return DraftSource(yaml_text=dumped, origin="whitelist", draft_path=None)
    88	
    89	
    90	def lint_case_yaml(yaml_text: str) -> LintResult:

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

exec
/bin/zsh -lc "nl -ba ui/backend/routes/case_solve.py | sed -n '1,220p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
     1	"""Phase-1A LDC solve routes (DEC-V61-097).
     2	
     3	Three POST/GET endpoints:
     4	
     5	* ``POST /api/import/{case_id}/setup-bc`` — split polyMesh + author dicts.
     6	* ``POST /api/import/{case_id}/solve`` — run icoFoam in cfd-openfoam.
     7	* ``GET  /api/cases/{case_id}/results-summary`` — parse final U field.
     8	
     9	These wire the missing back half of the M-PANELS demo flow that
    10	DEC-V61-096 deferred to M-AI-COPILOT / M7-redefined / M-VIZ.results.
    11	The deferral is now lifted (per user direction 2026-04-29: full demo
    12	end-to-end on the LDC fixture).
    13	
    14	Scope: LDC only. The cylinder + naca0012 demos require an external-
    15	flow pipeline (blockMesh + sHM) that is NOT shipped here; their
    16	demo buttons remain "import + mesh only" pending Phase-2.
    17	"""
    18	from __future__ import annotations
    19	
    20	from pathlib import Path
    21	
    22	from fastapi import APIRouter, HTTPException
    23	from fastapi.responses import StreamingResponse
    24	
    25	from ui.backend.schemas.case_solve import (
    26	    ResultsRejection,
    27	    ResultsSummaryWire,
    28	    SetupBcRejection,
    29	    SetupBcSummary,
    30	    SolveRejection,
    31	    SolveSummary,
    32	)
    33	from ui.backend.services.case_drafts import is_safe_case_id
    34	from ui.backend.services.case_scaffold import IMPORTED_DIR
    35	from ui.backend.services.case_solve import (
    36	    BCSetupError,
    37	    ResultsExtractError,
    38	    SolverRunError,
    39	    extract_results_summary,
    40	    run_icofoam,
    41	    setup_ldc_bc,
    42	    stream_icofoam,
    43	)
    44	from ui.backend.services.case_solve.solver_streamer import (
    45	    SolveAlreadyRunning,
    46	    _prepare_stream_icofoam,
    47	)
    48	
    49	
    50	router = APIRouter()
    51	
    52	
    53	def _resolve_case_dir(case_id: str) -> Path:
    54	    if not is_safe_case_id(case_id):
    55	        raise HTTPException(
    56	            status_code=400,
    57	            detail=SetupBcRejection(
    58	                failing_check="bad_case_id",
    59	                detail=f"unsafe case_id: {case_id!r}",
    60	            ).model_dump(),
    61	        )
    62	    case_dir = IMPORTED_DIR / case_id
    63	    if not case_dir.is_dir():
    64	        raise HTTPException(
    65	            status_code=404,
    66	            detail=SetupBcRejection(
    67	                failing_check="case_not_found",
    68	                detail=f"imported case {case_id!r} not found",
    69	            ).model_dump(),
    70	        )
    71	    return case_dir
    72	
    73	
    74	@router.post(
    75	    "/import/{case_id}/setup-bc",
    76	    response_model=SetupBcSummary,
    77	    tags=["case-solve"],
    78	)
    79	def setup_bc(case_id: str) -> SetupBcSummary:
    80	    """Split gmshToFoam's single patch into ``lid`` + ``fixedWalls`` and
    81	    author OpenFOAM dicts for icoFoam Re=100. Idempotent.
    82	    """
    83	    case_dir = _resolve_case_dir(case_id)
    84	    try:
    85	        result = setup_ldc_bc(case_dir, case_id=case_id)
    86	    except BCSetupError as exc:
    87	        msg = str(exc)
    88	        # Distinguish user-geometry rejection from backend faults.
    89	        if "axis-aligned cube" in msg or "no boundary faces match" in msg:
    90	            raise HTTPException(
    91	                status_code=400,
    92	                detail=SetupBcRejection(
    93	                    failing_check="not_an_ldc_cube",
    94	                    detail=msg,
    95	                ).model_dump(),
    96	            ) from exc
    97	        if "no constant/polyMesh" in msg or "boundary file" in msg:
    98	            raise HTTPException(
    99	                status_code=409,
   100	                detail=SetupBcRejection(
   101	                    failing_check="mesh_missing",
   102	                    detail=msg,
   103	                ).model_dump(),
   104	            ) from exc
   105	        raise HTTPException(
   106	            status_code=500,
   107	            detail=SetupBcRejection(
   108	                failing_check="write_failed",
   109	                detail=msg,
   110	            ).model_dump(),
   111	        ) from exc
   112	
   113	    return SetupBcSummary(
   114	        case_id=result.case_id,
   115	        n_lid_faces=result.n_lid_faces,
   116	        n_wall_faces=result.n_wall_faces,
   117	        lid_velocity=result.lid_velocity,
   118	        nu=result.nu,
   119	        reynolds=result.reynolds,
   120	        written_files=list(result.written_files),
   121	    )
   122	
   123	
   124	@router.post(
   125	    "/import/{case_id}/solve-stream",
   126	    tags=["case-solve"],
   127	)
   128	def solve_stream(case_id: str) -> StreamingResponse:
   129	    """Run icoFoam with **live** SSE streaming so the UI can update a
   130	    residual chart in real time.
   131	
   132	    Setup failures (case missing, bc not setup, container down) raise
   133	    HTTPException BEFORE the first byte is yielded — those become
   134	    HTTP 4xx/5xx with the same shape as the blocking ``/solve`` route.
   135	    Failures DURING the run land as in-stream ``error`` events; the
   136	    HTTP status stays 200 because the stream has already started.
   137	    """
   138	    case_dir = _resolve_case_dir(case_id)
   139	
   140	    # Validate eagerly so we can return a real HTTP error code instead
   141	    # of a 200-with-error-event. The streamer also checks these but
   142	    # raising here gives the route a chance to attach the structured
   143	    # SolveRejection contract.
   144	    if not (case_dir / "system" / "controlDict").is_file():
   145	        raise HTTPException(
   146	            status_code=409,
   147	            detail=SolveRejection(
   148	                failing_check="bc_not_setup",
   149	                detail=f"no system/controlDict at {case_dir}",
   150	            ).model_dump(),
   151	        )
   152	
   153	    # Codex round-1 HIGH-1: preflight must run BEFORE we hand a
   154	    # generator to StreamingResponse. ``_prepare_stream_icofoam`` is a
   155	    # plain function (not a generator), so any SolverRunError raised
   156	    # here surfaces as an HTTPException synchronously — instead of as
   157	    # a 200 response with a torn iterator.
   158	    try:
   159	        prepared = _prepare_stream_icofoam(case_host_dir=case_dir)
   160	    except SolveAlreadyRunning as exc:
   161	        # HIGH-2: a prior run for this case is still active. Reject
   162	        # with 409 so the client can wait + retry.
   163	        raise HTTPException(
   164	            status_code=409,
   165	            detail=SolveRejection(
   166	                failing_check="solve_already_running",
   167	                detail=str(exc),
   168	            ).model_dump(),
   169	        ) from exc
   170	    except SolverRunError as exc:
   171	        msg = str(exc)
   172	        if "container" in msg.lower() and (
   173	            "not running" in msg.lower() or "not found" in msg.lower()
   174	        ):
   175	            status = 503
   176	            failing = "container_unavailable"
   177	        else:
   178	            status = 502
   179	            failing = "post_stage_failed"
   180	        raise HTTPException(
   181	            status_code=status,
   182	            detail=SolveRejection(
   183	                failing_check=failing,
   184	                detail=msg,
   185	            ).model_dump(),
   186	        ) from exc
   187	
   188	    return StreamingResponse(
   189	        stream_icofoam(prepared=prepared),
   190	        media_type="text/event-stream",
   191	        headers={
   192	            # SSE wants no buffering by intermediaries; declare
   193	            # explicitly so reverse proxies (nginx etc) flush each
   194	            # event instead of accumulating.
   195	            "Cache-Control": "no-cache, no-transform",
   196	            "X-Accel-Buffering": "no",
   197	            "Connection": "keep-alive",
   198	        },
   199	    )
   200	
   201	
   202	@router.post(
   203	    "/import/{case_id}/solve",
   204	    response_model=SolveSummary,
   205	    tags=["case-solve"],
   206	)
   207	def solve(case_id: str) -> SolveSummary:
   208	    """Run icoFoam inside the cfd-openfoam container. Blocks until the
   209	    solver finishes (≈60s wall-time for the default LDC config).
   210	    """
   211	    case_dir = _resolve_case_dir(case_id)
   212	    try:
   213	        result = run_icofoam(case_host_dir=case_dir)
   214	    except SolverRunError as exc:
   215	        msg = str(exc)
   216	        if "no system/controlDict" in msg:
   217	            raise HTTPException(
   218	                status_code=409,
   219	                detail=SolveRejection(
   220	                    failing_check="bc_not_setup",

codex
CHANGES_REQUIRED

1. MED — staging still treats shell-command failure as success. In [solver_streamer.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/case_solve/solver_streamer.py:295) and [solver_streamer.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/case_solve/solver_streamer.py:315), both non-stream `container.exec_run(...)` calls ignore `exit_code`; the code only catches Docker transport exceptions. If `rm -rf && mv && chmod` returns non-zero because the extracted `{case_id}` dir is missing, the rename fails, or permissions are wrong, `_prepare_stream_icofoam()` still returns a prepared stream and the route emits `200` SSE instead of rejecting preflight. The new regression test stays blind to that path because [_FakeContainer.exec_run](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_solver_streamer.py:30) hardcodes `exit_code=0`, and [test_staging_renames_extracted_dir_into_run_id_suffix](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_solver_streamer.py:255) only inspects command strings. This leaves a real staging-failure hole in the same surface this DEC is closing. Recommendation: check `exit_code` after both setup `exec_run` calls and add a test that forces the rename step to return non-zero.

Assumptions / non-blockers

- I do not see a new race in `rm -rf {suffix} && mv {base}/{case_id} {suffix}` itself under the current model. Route input is constrained by [case_drafts.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/case_drafts.py:56), run ids are generated at [solver_streamer.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/case_solve/solver_streamer.py:84), and the path stays under container-local `/tmp/cfd-harness-cases-mesh`.
- `rm -rf {container_work_dir}` does not look too broad for the route-backed path for the same reason above; the remaining risk is not collision, it is silent command failure.
- `chmod 777` is permissive but consistent with existing container-staging convention in [solver_runner.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/case_solve/solver_runner.py:192) and [to_foam.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/meshing_gmsh/to_foam.py:163). I would not block merge on that alone in this single-user image.
- I did not run `pytest` in this shell because test bootstrap currently fails on missing `trimesh`, and direct repo imports also hit missing `yaml`.


tokens used
122,874
CHANGES_REQUIRED

1. MED — staging still treats shell-command failure as success. In [solver_streamer.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/case_solve/solver_streamer.py:295) and [solver_streamer.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/case_solve/solver_streamer.py:315), both non-stream `container.exec_run(...)` calls ignore `exit_code`; the code only catches Docker transport exceptions. If `rm -rf && mv && chmod` returns non-zero because the extracted `{case_id}` dir is missing, the rename fails, or permissions are wrong, `_prepare_stream_icofoam()` still returns a prepared stream and the route emits `200` SSE instead of rejecting preflight. The new regression test stays blind to that path because [_FakeContainer.exec_run](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_solver_streamer.py:30) hardcodes `exit_code=0`, and [test_staging_renames_extracted_dir_into_run_id_suffix](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_solver_streamer.py:255) only inspects command strings. This leaves a real staging-failure hole in the same surface this DEC is closing. Recommendation: check `exit_code` after both setup `exec_run` calls and add a test that forces the rename step to return non-zero.

Assumptions / non-blockers

- I do not see a new race in `rm -rf {suffix} && mv {base}/{case_id} {suffix}` itself under the current model. Route input is constrained by [case_drafts.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/case_drafts.py:56), run ids are generated at [solver_streamer.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/case_solve/solver_streamer.py:84), and the path stays under container-local `/tmp/cfd-harness-cases-mesh`.
- `rm -rf {container_work_dir}` does not look too broad for the route-backed path for the same reason above; the remaining risk is not collision, it is silent command failure.
- `chmod 777` is permissive but consistent with existing container-staging convention in [solver_runner.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/case_solve/solver_runner.py:192) and [to_foam.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/meshing_gmsh/to_foam.py:163). I would not block merge on that alone in this single-user image.
- I did not run `pytest` in this shell because test bootstrap currently fails on missing `trimesh`, and direct repo imports also hit missing `yaml`.


