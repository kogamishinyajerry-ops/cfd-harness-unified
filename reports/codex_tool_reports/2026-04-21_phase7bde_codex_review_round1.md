2026-04-21T12:00:44.711425Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-research-deerflow/SKILL.md: missing YAML frontmatter delimited by ---
2026-04-21T12:00:44.711444Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-report-pretext/SKILL.md: missing YAML frontmatter delimited by ---
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
session id: 019dafea-12ae-7371-8a78-a5f61d8e5c98
--------
user
Review Phase 7b-polish + 7d (Richardson GCI) + 7e (L4 signed-zip) bundle. All uncommitted in working tree at /Users/Zhuanz/Desktop/cfd-harness-unified.

This is byte-reproducibility-sensitive + touches src/audit_package/manifest.py + serialize.py (三禁区 #1 + 2) → Codex mandatory per RETRO-V61-001.

## Phase 7b polish (2D VTK contour)
- scripts/render_case_report.py: new _find_latest_vtk() helper + render_contour_u_magnitude_png() now parses OpenFOAM volume VTK via PyVista, extracts cell-centered U + Cx/Cy, reshapes into 129×129 grid, renders matplotlib contourf + streamplot. Falls back to MVP 1D strip on parse failure. Uses np.linspace to rebuild 1D x/y axes (avoids float-precision jitter in VTK cell centers that trips streamplot equality check).

## Phase 7d (Richardson GCI)
- ui/backend/services/grid_convergence.py (NEW, ~220 LOC): Celik 2008 / Roache 1994. Handles uniform r (p_obs = |ln(|eps_32/eps_21|)| / ln(r)), non-uniform r (Celik iterative), oscillating signs (eps_21*eps_32<0 → note), converged-to-precision (|eps|<1e-14 → note). GCI_21 + GCI_32 with Fs=1.25 (3-grid). Asymptotic-range check: GCI_21 / (r^p * GCI_32) ∈ [0.8, 1.25]. Uses Celik Eq.4 denominator (refined/downstream solution).
- ui/backend/services/comparison_report.py: build_report_context computes GCI via compute_gci_from_fixtures() + _gci_to_template_dict() helper.
- ui/backend/templates/comparison_report.html.j2: §7 renders sub-table with p_obs, Richardson f_h→0, GCI_21, GCI_32, asymptotic-range verdict.
- New test_grid_convergence_gci.py with 7 tests.
- LDC live: p_obs=1.00, GCI_32=5.68%, asymptotic_range_ok=True.

## Phase 7e (L4 signed-zip embedding)
- src/audit_package/manifest.py: new _PHASE7_TIMESTAMP_RE + _collect_phase7_artifacts(). build_manifest() has include_phase7: bool = True kwarg; when True AND artifacts exist, manifest gains "phase7" top-level key with {schema_level: "L4", entries: [...], total_files, total_bytes}.
- src/audit_package/serialize.py: _zip_entries_from_manifest reads manifest["phase7"]["entries"] and adds every file to the zip at its zip_path. Defense-in-depth containment: every resolved disk_path must stay under repo_root.
- docs/specs/audit_package_canonical_L4.md: full spec.
- ui/backend/tests/test_audit_package_phase7e.py: 8 tests.
- Live-verified: 14 files embedded. Bundle 1.97 MB. Two consecutive POST audit-package/build produced IDENTICAL zip SHA256 (39990076bfb634d0...) + IDENTICAL HMAC (a80a549c3d90590d...).

## Regression gate
PYTHONPATH=. .venv/bin/pytest ui/backend/tests/ -q → 129/129 passed (was 121/121; +8 Phase 7e tests).

## Focus review on (byte-reproducibility is critical)

1. **Byte-repro threat: phase7 entry ordering in zip**. manifest.phase7.entries sorted by zip_path. serialize._zip_entries_from_manifest inserts these keys, then sorted(entries.keys()) in serialize_zip_bytes. Verify NO case where same inputs → different byte output. Check: (a) dict insertion order + sorted() interplay; (b) os.walk / rglob determinism — uses sorted(case_ts_dir.rglob("*")); (c) SHA256 deterministic.

2. **Security: path traversal in phase7 collection**. _collect_phase7_artifacts validates timestamp shape + verifies each file resolves under sanctioned roots. serialize.py re-validates (re-resolve + relative_to repo_root). Any symlink inside a sanctioned root pointing outside? Check test_collect_phase7_rejects_tampered_timestamp.

3. **Size cap 50MB**: silent-skip via p.stat().st_size > 50*1024*1024. Should skipped files be recorded for audit completeness, or is silent OK?

4. **GCI edge cases**:
   - r_21 ≠ r_32 by >5%: Celik iterative. Bounded 50 iters? Always converges? Divergence → p_guess=None handled cleanly?
   - Celik Eq.4 denominator uses medium.value / fine.value; guard abs(x) > 1e-12 returns inf if exactly 0 — downstream safe?
   - Oscillating sign-flip correctly → p_obs=None.

5. **Non-LDC cases**: include_phase7=True DEFAULT. For 9 other whitelist cases not opted in, _collect_phase7_artifacts returns None → no "phase7" key. Graceful for existing consumers? (existing audit_package tests still pass.)

6. **L4 spec + test coverage alignment**: spec claims 1.97 MB bundle; tests verify fixture-scale. Sufficient?

Reply APPROVED / APPROVED_WITH_COMMENTS / CHANGES_REQUIRED with numbered findings. Brief if APPROVED; detailed if CHANGES_REQUIRED.
codex
Reviewing the Phase 7b/7d/7e bundle as a correctness and reproducibility audit, not as implementation work. I’m pulling the repo-specific memory note plus the changed files and targeted tests first, then I’ll check the byte-stability, path-containment, and GCI edge-case claims against the actual code.
exec
/bin/zsh -lc 'rg -n "cfd-harness-unified|Phase 8|Phase 9|audit_package|Richardson|phase7" /Users/Zhuanz/.codex/memories/MEMORY.md' in /Users/Zhuanz/Desktop/cfd-harness-unified
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
658:- rollout_summaries/2026-04-07T14-48-14-t3g6-post_phase7_final_freeze_signoff_governance_planning_review.md (cwd=/Users/Zhuanz/20260402 AI ControlLogicMaster, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/07/rollout-2026-04-07T22-48-14-019d686a-5f10-79f2-9918-ff5cdc98e6aa.jsonl, updated_at=2026-04-08T15:13:06+00:00, thread_id=019d686a-5f10-79f2-9918-ff5cdc98e6aa, initial rejection then accepted rerun after README/docs routing fix)
668:- rollout_summaries/2026-04-07T13-59-35-aTNv-post_phase7_corrected_inventory_approval_and_freeze_signoff.md (cwd=/Users/Zhuanz/20260402 AI ControlLogicMaster, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/07/rollout-2026-04-07T21-59-35-019d683d-d22a-7590-9bc5-612efced3d79.jsonl, updated_at=2026-04-08T13:29:34+00:00, thread_id=019d683d-d22a-7590-9bc5-612efced3d79, corrected-inventory approval action with explicit no-execution boundary)
669:- rollout_summaries/2026-04-02T16-11-48-lkTw-aplh_post_phase7_manual_review_intake_action_review.md (cwd=/Users/Zhuanz/20260402 AI ControlLogicMaster, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/03/rollout-2026-04-03T00-11-48-019d4ef7-13d3-7311-a159-a08420027a5a.jsonl, updated_at=2026-04-08T12:29:35+00:00, thread_id=019d4ef7-13d3-7311-a159-a08420027a5a, manual intake accepted but explicitly not freeze approval)
679:- rollout_summaries/2026-04-02T18-05-38-tXWd-post_phase7_manual_review_intake_request_package.md (cwd=/Users/Zhuanz/20260402 AI ControlLogicMaster, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/03/rollout-2026-04-03T02-05-38-019d4f5f-4b79-7e92-8037-4ad30697428d.jsonl, updated_at=2026-04-08T01:38:10+00:00, thread_id=019d4f5f-4b79-7e92-8037-4ad30697428d, markdown-only request packet plus review input)
691:- when the user said "你是 independent approval authority… 你不是 corrected request packet 作者… 你不是 Phase 8 executor" -> preserve strict role separation between approval, review, execution, and freeze authority in this repo [Task 4]
823:- rollout_summaries/2026-04-09T09-46-14-BhcD-phase7_2_openfoam_docker_executor.md (cwd=/Users/Zhuanz/Desktop/notion-cfd-harness, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/09/rollout-2026-04-09T17-46-14-019d71a2-994b-7bd2-ac2a-e32421ff628b.jsonl, updated_at=2026-04-09T09:51:40+00:00, thread_id=019d71a2-994b-7bd2-ac2a-e32421ff628b, Docker executor integrated against actual protocol)

exec
/bin/zsh -lc "sed -n '1,220p' /Users/Zhuanz/.codex/plugins/cache/openai-curated/superpowers/b1986b3d3da5bb8a04d3cb1e69af5a29bb5c2c04/skills/using-superpowers/SKILL.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '1,260p' /Users/Zhuanz/.agents/skills/gsd-code-review/SKILL.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
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

codex
Using `gsd-code-review` as the review workflow, with repo memory only as a light guardrail for this repo’s governance context. I’m scoping the actual uncommitted diff now so the review is anchored to changed lines, not the phase summary.
exec
/bin/zsh -lc 'git diff --stat -- scripts/render_case_report.py ui/backend/services/grid_convergence.py ui/backend/services/comparison_report.py ui/backend/templates/comparison_report.html.j2 src/audit_package/manifest.py src/audit_package/serialize.py ui/backend/tests/test_grid_convergence_gci.py ui/backend/tests/test_audit_package_phase7e.py docs/specs/audit_package_canonical_L4.md' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
 scripts/render_case_report.py                  |  93 ++++++++++++---
 src/audit_package/manifest.py                  | 149 +++++++++++++++++++++++++
 src/audit_package/serialize.py                 |  31 +++++
 ui/backend/services/comparison_report.py       |  33 +++++-
 ui/backend/templates/comparison_report.html.j2 |  45 +++++++-
 5 files changed, 335 insertions(+), 16 deletions(-)

exec
/bin/zsh -lc 'git diff -- scripts/render_case_report.py ui/backend/services/grid_convergence.py ui/backend/services/comparison_report.py ui/backend/templates/comparison_report.html.j2 src/audit_package/manifest.py src/audit_package/serialize.py ui/backend/tests/test_grid_convergence_gci.py ui/backend/tests/test_audit_package_phase7e.py docs/specs/audit_package_canonical_L4.md' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
diff --git a/scripts/render_case_report.py b/scripts/render_case_report.py
index 96c11fa..63bf31a 100644
--- a/scripts/render_case_report.py
+++ b/scripts/render_case_report.py
@@ -364,39 +364,104 @@ def render_pointwise_deviation_png(
     return out
 
 
+def _find_latest_vtk(artifact_dir: Path) -> Optional[Path]:
+    """Return the highest-iteration VTK volume file (not the allPatches one)."""
+    vtk_root = artifact_dir / "VTK"
+    if not vtk_root.is_dir():
+        return None
+    # Volume VTK files are at VTK/*.vtk (direct children); boundary data is under VTK/allPatches/.
+    candidates = sorted(
+        p for p in vtk_root.glob("*.vtk") if p.is_file()
+    )
+    return candidates[-1] if candidates else None
+
+
 def render_contour_u_magnitude_png(
     case_id: str,
     artifact_dir: Path,
     renders_dir: Path,
 ) -> Path:
-    """LDC MVP contour: uses the sample/{iter}/uCenterline.xy which is a 1D profile
-    along x=0.5 centerline. For a true 2D contour we'd need to parse the full VTK
-    volume, which requires the `vtk` package — deferred to Phase 7b polish.
+    """2D U-magnitude contour + streamlines from the real VTK volume (Phase 7b polish).
+
+    Phase 7b polish (2026-04-21): parse the actual OpenFOAM volume VTK via PyVista,
+    project onto a 129×129 XY grid (LDC is pseudo-2D, one cell thick in z),
+    compute |U| = sqrt(Ux² + Uy²), render contourf + streamlines via matplotlib.
 
-    Instead, render a stylized 1D heatmap strip showing U_x(y) along the centerline.
-    This is honestly labeled as "centerline slice" not "full field contour".
+    Fallback to the old 1D centerline strip if PyVista/VTK parsing fails.
     """
+    out = renders_dir / "contour_u_magnitude.png"
+    vtk_path = _find_latest_vtk(artifact_dir)
+    if vtk_path is not None:
+        try:
+            import pyvista as pv
+            pv.OFF_SCREEN = True
+            mesh = pv.read(str(vtk_path))
+            # Cell-centered U vector and cell centroid coords.
+            cd = mesh.cell_data
+            if "U" not in cd or "Cx" not in cd or "Cy" not in cd:
+                raise RenderError(f"VTK missing U/Cx/Cy: {vtk_path}")
+            U = np.asarray(cd["U"])
+            Cx = np.asarray(cd["Cx"])
+            Cy = np.asarray(cd["Cy"])
+            n = U.shape[0]
+            # LDC: 129×129 uniform → infer grid dim from n.
+            side = int(round(n ** 0.5))
+            if side * side != n:
+                raise RenderError(f"VTK cell count {n} not square grid")
+            # Sort by (y, x) to pack into (side, side) array.
+            order = np.lexsort((Cx, Cy))
+            Ux = U[order, 0].reshape(side, side)
+            Uy = U[order, 1].reshape(side, side)
+            x = Cx[order].reshape(side, side)
+            y = Cy[order].reshape(side, side)
+            mag = np.sqrt(Ux ** 2 + Uy ** 2)
+            # Normalize coords to y/L domain.
+            lid = max(float(y.max()), 1e-12)
+            xn = x / lid
+            yn = y / lid
+
+            # streamplot needs 1D evenly-spaced vectors. OpenFOAM VTK cell
+            # centers have tiny float-precision jitter; rebuild from bounds.
+            x_min, x_max = float(xn.min()), float(xn.max())
+            y_min, y_max = float(yn.min()), float(yn.max())
+            x1d = np.linspace(x_min, x_max, side)
+            y1d = np.linspace(y_min, y_max, side)
+            fig, ax = plt.subplots(figsize=(6.5, 6))
+            cf = ax.contourf(x1d, y1d, mag, levels=20, cmap="viridis")
+            ax.streamplot(x1d, y1d, Ux, Uy, density=1.1, color="white",
+                          linewidth=0.6, arrowsize=0.8)
+            ax.set_aspect("equal")
+            ax.set_xlabel("x / L")
+            ax.set_ylabel("y / L")
+            ax.set_title(
+                f"{case_id} — |U| contour + streamlines (Phase 7b polish)\n"
+                f"129×129 mesh, simpleFoam steady, Re=100"
+            )
+            cbar = fig.colorbar(cf, ax=ax, fraction=0.045, pad=0.04)
+            cbar.set_label("|U| / U_lid")
+            fig.savefig(out)
+            plt.close(fig)
+            return out
+        except Exception as e:  # noqa: BLE001 — fall back to MVP strip
+            print(f"[render] [WARN] VTK parse failed ({e}); falling back to centerline strip",
+                  file=sys.stderr)
+
+    # Fallback — Phase 7b MVP behavior (1D strip) if VTK parse fails.
     latest = _latest_sample_iter(artifact_dir)
     y_sim, u_sim = _load_sample_xy(latest / "uCenterline.xy")
     y_norm = y_sim / max(y_sim.max(), 1e-12)
-
     fig, ax = plt.subplots(figsize=(4, 6))
-    # Tile the 1D profile horizontally to make a strip heatmap visible.
     strip = np.tile(u_sim.reshape(-1, 1), (1, 20))
     im = ax.imshow(
-        strip,
-        aspect="auto",
-        origin="lower",
+        strip, aspect="auto", origin="lower",
         extent=[0, 1, float(y_norm.min()), float(y_norm.max())],
-        cmap="RdBu_r",
-        vmin=-1.0, vmax=1.0,
+        cmap="RdBu_r", vmin=-1.0, vmax=1.0,
     )
     ax.set_xlabel("(tile axis)")
     ax.set_ylabel("y / L")
-    ax.set_title(f"{case_id} — U_x centerline slice\n(Phase 7b MVP — full 2D VTK contour\ndeferred to 7b-polish)")
+    ax.set_title(f"{case_id} — U_x centerline slice (VTK parse failed, MVP fallback)")
     cbar = fig.colorbar(im, ax=ax, fraction=0.08, pad=0.04)
     cbar.set_label("U_x / U_lid")
-    out = renders_dir / "contour_u_magnitude.png"
     fig.savefig(out)
     plt.close(fig)
     return out
diff --git a/src/audit_package/manifest.py b/src/audit_package/manifest.py
index c927508..61fbed8 100644
--- a/src/audit_package/manifest.py
+++ b/src/audit_package/manifest.py
@@ -33,6 +33,7 @@ Non-goals for PR-5a:
 from __future__ import annotations
 
 import datetime as _dt
+import hashlib
 import subprocess
 from pathlib import Path
 from typing import Any, Dict, List, Optional, Sequence
@@ -301,6 +302,146 @@ def _extract_first_heading(text: str) -> Optional[str]:
 # Public builder
 # ---------------------------------------------------------------------------
 
+# --- Phase 7e (DEC-V61-033, L4): embed Phase 7 artifacts into signed zip ---
+
+# Deterministic YYYYMMDDTHHMMSSZ shape for run timestamps (mirrors 7a/7b/7c gates).
+import re as _re
+_PHASE7_TIMESTAMP_RE = _re.compile(r"^\d{8}T\d{6}Z$")
+
+
+def _sha256_of_file(path: Path) -> str:
+    h = hashlib.sha256()
+    with path.open("rb") as f:
+        for chunk in iter(lambda: f.read(65536), b""):
+            h.update(chunk)
+    return h.hexdigest()
+
+
+def _collect_phase7_artifacts(
+    case_id: str, run_id: str, repo_root: Path
+) -> Optional[Dict[str, Any]]:
+    """Collect Phase 7a/7b/7c artifacts for (case, run) into a manifest section.
+
+    Returns dict with ``entries`` = sorted list of {zip_path, disk_path, sha256,
+    size_bytes} dicts + ``schema_level: "L4"``. Returns None when no Phase 7
+    artifacts exist for this run.
+
+    Byte-reproducibility preserved:
+    - Disk paths derive from deterministic timestamp folders.
+    - SHA256 of each file is stable.
+    - Entry list is sorted by ``zip_path``.
+    - Manifest embeds hashes, not bytes — serialize.py then reads the files.
+
+    Security: timestamp values read from Phase 7a/7b manifests are validated
+    against _PHASE7_TIMESTAMP_RE (defense-in-depth against manifest tampering,
+    mirrors Phase 7a `_TIMESTAMP_RE` + Phase 7c `_resolve_artifact_dir`).
+    """
+    import json as _json
+    fields_root = repo_root / "reports" / "phase5_fields" / case_id
+    renders_root = repo_root / "reports" / "phase5_renders" / case_id
+    reports_root = repo_root / "reports" / "phase5_reports" / case_id
+
+    entries: List[Dict[str, Any]] = []
+
+    def _add(path: Path, zip_path: str) -> None:
+        """Add a file to entries list if it exists, validates under a sanctioned root."""
+        if not path.is_file():
+            return
+        try:
+            resolved = path.resolve(strict=True)
+        except (OSError, FileNotFoundError):
+            return
+        # Every zip entry must resolve under one of the three Phase 7 roots.
+        ok = False
+        for root in (fields_root, renders_root, reports_root):
+            try:
+                resolved.relative_to(root.resolve())
+                ok = True
+                break
+            except (ValueError, OSError):
+                continue
+        if not ok:
+            return
+        entries.append({
+            "zip_path": zip_path,
+            "disk_path_rel": str(path.relative_to(repo_root)),
+            "sha256": _sha256_of_file(path),
+            "size_bytes": path.stat().st_size,
+        })
+
+    # Phase 7a — field artifacts (VTK + sample + residuals).
+    f_manifest = fields_root / "runs" / f"{run_id}.json"
+    if f_manifest.is_file():
+        try:
+            f_data = _json.loads(f_manifest.read_text(encoding="utf-8"))
+        except (ValueError, OSError):
+            f_data = None
+        if isinstance(f_data, dict):
+            ts = f_data.get("timestamp")
+            if isinstance(ts, str) and _PHASE7_TIMESTAMP_RE.match(ts):
+                case_ts_dir = fields_root / ts
+                if case_ts_dir.is_dir():
+                    for p in sorted(case_ts_dir.rglob("*")):
+                        if not p.is_file():
+                            continue
+                        try:
+                            rel = p.resolve().relative_to(case_ts_dir.resolve()).as_posix()
+                        except (ValueError, OSError):
+                            continue
+                        # Skip huge non-essential files to keep zip sane.
+                        if p.suffix.lower() == ".vtk" and p.stat().st_size > 50 * 1024 * 1024:
+                            continue
+                        _add(p, f"phase7/field_artifacts/{rel}")
+
+    # Phase 7b — renders.
+    r_manifest = renders_root / "runs" / f"{run_id}.json"
+    if r_manifest.is_file():
+        try:
+            r_data = _json.loads(r_manifest.read_text(encoding="utf-8"))
+        except (ValueError, OSError):
+            r_data = None
+        if isinstance(r_data, dict):
+            ts = r_data.get("timestamp")
+            if isinstance(ts, str) and _PHASE7_TIMESTAMP_RE.match(ts):
+                r_ts_dir = renders_root / ts
+                if r_ts_dir.is_dir():
+                    for p in sorted(r_ts_dir.rglob("*")):
+                        if not p.is_file():
+                            continue
+                        try:
+                            rel = p.resolve().relative_to(r_ts_dir.resolve()).as_posix()
+                        except (ValueError, OSError):
+                            continue
+                        _add(p, f"phase7/renders/{rel}")
+
+    # Phase 7c — HTML + PDF comparison report. Report dir is keyed by the
+    # same timestamp (7c service writes under reports/phase5_reports/{case}/{ts}/).
+    # Pull the timestamp from the 7a manifest (authoritative).
+    if f_manifest.is_file():
+        try:
+            f_data = _json.loads(f_manifest.read_text(encoding="utf-8"))
+        except (ValueError, OSError):
+            f_data = None
+        if isinstance(f_data, dict):
+            ts = f_data.get("timestamp")
+            if isinstance(ts, str) and _PHASE7_TIMESTAMP_RE.match(ts):
+                pdf = reports_root / ts / f"{run_id}_comparison_report.pdf"
+                if pdf.is_file():
+                    _add(pdf, "phase7/comparison_report.pdf")
+
+    if not entries:
+        return None
+
+    entries.sort(key=lambda d: d["zip_path"])
+    return {
+        "schema_level": "L4",
+        "canonical_spec": "docs/specs/audit_package_canonical_L4.md",
+        "entries": entries,
+        "total_files": len(entries),
+        "total_bytes": sum(e["size_bytes"] for e in entries),
+    }
+
+
 def build_manifest(
     *,
     case_id: str,
@@ -313,6 +454,7 @@ def build_manifest(
     audit_concerns: Optional[Sequence[Dict[str, Any]]] = None,
     build_fingerprint: Optional[str] = None,
     solver_name: Optional[str] = None,
+    include_phase7: bool = True,
 ) -> Dict[str, Any]:
     """Assemble the audit-package manifest for a single case + run.
 
@@ -428,4 +570,11 @@ def build_manifest(
         "measurement": measurement_section,
         "decision_trail": decision_trail,
     }
+    # Phase 7e (DEC-V61-033): L4 schema — embed Phase 7 artifacts (field
+    # captures, renders, comparison report PDF) into the signed zip.
+    # Only attached when include_phase7=True AND artifacts exist for this run.
+    if include_phase7:
+        phase7 = _collect_phase7_artifacts(case_id, run_id, repo_root)
+        if phase7 is not None:
+            manifest["phase7"] = phase7
     return manifest
diff --git a/src/audit_package/serialize.py b/src/audit_package/serialize.py
index 1abb7b5..1894fce 100644
--- a/src/audit_package/serialize.py
+++ b/src/audit_package/serialize.py
@@ -138,6 +138,37 @@ def _zip_entries_from_manifest(manifest: Dict[str, Any]) -> Dict[str, bytes]:
         body = f"decision_id: {did}\ntitle: {title}\nrelative_path: {path}\n"
         entries[f"decisions/{did}.txt"] = body.encode("utf-8")
 
+    # Phase 7e (DEC-V61-033, L4): embed Phase 7 artifacts if manifest carries
+    # the phase7 section. Each entry's file is read verbatim and SHA256 has
+    # already been pre-computed by the manifest builder — zip is byte-stable
+    # as long as the source files on disk are byte-stable (they are: fixed
+    # OpenFOAM output, deterministic renders, deterministic PDF per input).
+    phase7 = manifest.get("phase7")
+    if isinstance(phase7, dict):
+        import pathlib as _pl
+        repo_root = _pl.Path(__file__).resolve().parents[2]
+        phase7_entries = phase7.get("entries") or []
+        for entry in phase7_entries:
+            if not isinstance(entry, dict):
+                continue
+            zip_path = entry.get("zip_path")
+            disk_rel = entry.get("disk_path_rel")
+            if not isinstance(zip_path, str) or not isinstance(disk_rel, str):
+                continue
+            disk_path = repo_root / disk_rel
+            if not disk_path.is_file():
+                continue
+            try:
+                # Defense-in-depth: ensure resolved path stays under repo root.
+                resolved = disk_path.resolve(strict=True)
+                resolved.relative_to(repo_root.resolve())
+            except (ValueError, OSError, FileNotFoundError):
+                continue
+            try:
+                entries[zip_path] = resolved.read_bytes()
+            except OSError:
+                continue
+
     return entries
 
 
diff --git a/ui/backend/services/comparison_report.py b/ui/backend/services/comparison_report.py
index c1072ec..ac4af95 100644
--- a/ui/backend/services/comparison_report.py
+++ b/ui/backend/services/comparison_report.py
@@ -271,6 +271,29 @@ def _load_grid_convergence(case_id: str, gold_y: list[float], gold_u: list[float
     return rows, note
 
 
+def _gci_to_template_dict(gci: Any) -> dict:
+    """Flatten a RichardsonGCI dataclass into a JSON-serializable dict for the template."""
+    return {
+        "coarse_label": gci.coarse.label,
+        "coarse_n": gci.coarse.n_cells_1d,
+        "coarse_value": gci.coarse.value,
+        "medium_label": gci.medium.label,
+        "medium_n": gci.medium.n_cells_1d,
+        "medium_value": gci.medium.value,
+        "fine_label": gci.fine.label,
+        "fine_n": gci.fine.n_cells_1d,
+        "fine_value": gci.fine.value,
+        "r_21": gci.r_21,
+        "r_32": gci.r_32,
+        "p_obs": gci.p_obs,
+        "f_extrapolated": gci.f_extrapolated,
+        "gci_21_pct": gci.gci_21 * 100 if gci.gci_21 is not None else None,
+        "gci_32_pct": gci.gci_32 * 100 if gci.gci_32 is not None else None,
+        "asymptotic_range_ok": gci.asymptotic_range_ok,
+        "note": gci.note,
+    }
+
+
 def _get_commit_sha() -> str:
     try:
         r = subprocess.run(
@@ -321,6 +344,12 @@ def build_report_context(case_id: str, run_label: str = "audit_real_run") -> dic
 
     residual_info = _parse_residuals_csv(artifact_dir / "residuals.csv")
     grid_conv_rows, grid_note = _load_grid_convergence(case_id, gold_y, gold_u)
+    # Phase 7d: Richardson extrapolation + GCI over the finest 3 meshes.
+    try:
+        from ui.backend.services.grid_convergence import compute_gci_from_fixtures
+        gci = compute_gci_from_fixtures(case_id, fixture_root=_FIXTURE_ROOT)
+    except (ValueError, ImportError):
+        gci = None
 
     # Verdict logic: all-pass OR tolerance met.
     is_all_pass = metrics["n_pass"] == metrics["n_total"] and metrics["n_total"] > 0
@@ -396,11 +425,13 @@ def build_report_context(case_id: str, run_label: str = "audit_real_run") -> dic
         "paper": paper,
         "renders": renders,
         "contour_caption": (
-            "Phase 7b MVP — 沿 x=0.5 中心线的 U_x 条带切片，后续 7b-polish 会用 VTK 体数据生成完整 2D contour。"
+            "2D |U| contour + streamlines 由 OpenFOAM VTK 体数据渲染（Phase 7b polish）。"
+            "白色流线显示 LDC Re=100 的主涡结构；黄色高 |U| 区沿 lid 剪切层分布。"
         ),
         "residual_info": residual_info,
         "grid_conv": grid_conv_rows,
         "grid_conv_note": grid_note,
+        "gci": _gci_to_template_dict(gci) if gci is not None else None,
         "meta": {
             "openfoam_version": "v10",
             "solver": "simpleFoam (SIMPLE, laminar)",
diff --git a/ui/backend/templates/comparison_report.html.j2 b/ui/backend/templates/comparison_report.html.j2
index 75f2412..5863d55 100644
--- a/ui/backend/templates/comparison_report.html.j2
+++ b/ui/backend/templates/comparison_report.html.j2
@@ -137,8 +137,51 @@
   </tbody>
 </table>
 <p style="color:#6b7280; font-size:0.88em; margin-top:0.5em;">
-  单调收敛: {{ grid_conv_note }} · Richardson p_obs (观察阶数) 延后到 Phase 7d。
+  单调收敛: {{ grid_conv_note }}
 </p>
+
+{% if gci %}
+<h3 style="font-size:1.05em; margin-top:1.2em; color:#374151;">Richardson extrapolation + GCI (Celik 2008, Roache 1994)</h3>
+<table>
+  <tbody>
+    <tr><th>3-grid input</th><td class="mono">
+      {{ gci.coarse_label }} (N={{ gci.coarse_n }}) = {{ '%.4f'|format(gci.coarse_value) }},
+      {{ gci.medium_label }} (N={{ gci.medium_n }}) = {{ '%.4f'|format(gci.medium_value) }},
+      {{ gci.fine_label }} (N={{ gci.fine_n }}) = {{ '%.4f'|format(gci.fine_value) }}
+    </td></tr>
+    <tr><th>Refinement ratios</th><td class="mono">r₂₁ = {{ '%.3f'|format(gci.r_21) }}, r₃₂ = {{ '%.3f'|format(gci.r_32) }}</td></tr>
+    <tr><th>Observed order p_obs</th><td class="mono">
+      {% if gci.p_obs is not none %}{{ '%.4f'|format(gci.p_obs) }}{% else %}undefined ({{ gci.note }}){% endif %}
+    </td></tr>
+    <tr><th>Richardson f_h→0</th><td class="mono">
+      {% if gci.f_extrapolated is not none %}{{ '%.6f'|format(gci.f_extrapolated) }}{% else %}n/a{% endif %}
+    </td></tr>
+    <tr><th>GCI₂₁ (coarse→medium)</th><td class="mono">
+      {% if gci.gci_21_pct is not none %}{{ '%.3f'|format(gci.gci_21_pct) }}%{% else %}n/a{% endif %}
+    </td></tr>
+    <tr><th>GCI₃₂ (medium→fine)</th><td class="mono">
+      {% if gci.gci_32_pct is not none %}<strong>{{ '%.3f'|format(gci.gci_32_pct) }}%</strong>{% else %}n/a{% endif %}
+      <span style="color:#6b7280; margin-left:0.5em; font-size:0.85em;">
+        ← 最细网格解的数值不确定度带
+      </span>
+    </td></tr>
+    <tr><th>Asymptotic range</th><td>
+      {% if gci.asymptotic_range_ok %}
+        <span style="color:#059669; font-weight:600;">✓ within asymptotic range</span>
+      {% elif gci.asymptotic_range_ok is false %}
+        <span style="color:#d97706;">⚠ not yet asymptotic — {{ gci.note }}</span>
+      {% else %}
+        <span style="color:#9ca3af;">n/a</span>
+      {% endif %}
+    </td></tr>
+  </tbody>
+</table>
+<p style="color:#6b7280; font-size:0.82em; margin-top:0.4em; font-style:italic;">
+  Fs=1.25 (3-grid safety factor). Reference: Celik et al. 2008 "Procedure for
+  Estimation and Reporting of Uncertainty Due to Discretization in CFD Applications",
+  J. Fluids Eng. 130(7), ASME V&V 20 standard.
+</p>
+{% endif %}
 {% else %}
 <p style="color:#9ca3af; font-style:italic;">网格收敛数据暂未加载。</p>
 {% endif %}

exec
/bin/zsh -lc 'git status --short' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
 M reports/cylinder_crossflow/report.md
 M reports/deep_acceptance/visual_acceptance_report.html
 M reports/deep_acceptance/visual_acceptance_report_manifest.json
 M reports/differential_heated_cavity/report.md
 M reports/rayleigh_benard_convection/report.md
 M reports/turbulent_flat_plate/report.md
 M scripts/render_case_report.py
 M src/audit_package/manifest.py
 M src/audit_package/serialize.py
 M ui/backend/services/comparison_report.py
 M ui/backend/templates/comparison_report.html.j2
 M ui/frontend/public/flow-fields/circular_cylinder_wake/strouhal_curve.png
 M ui/frontend/public/flow-fields/lid_driven_cavity/centerline_profiles.png
 M ui/frontend/public/flow-fields/lid_driven_cavity/stream_function.png
 M ui/frontend/public/flow-fields/plane_channel_flow/wall_profile.png
 M ui/frontend/public/flow-fields/rayleigh_benard_convection/nu_ra_scaling.png
 M ui/frontend/public/flow-fields/turbulent_flat_plate/blasius_profile.png
 M ui/frontend/public/flow-fields/turbulent_flat_plate/cf_comparison.png
?? .claude/
?? .gitignore.patch.stale.1776663560182166739
?? docs/specs/audit_package_canonical_L4.md
?? knowledge/corrections/
?? reports/codex_tool_reports/2026-04-21_phase7bde_codex_review.md
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
?? ui/backend/services/grid_convergence.py
?? ui/backend/tests/test_audit_package_phase7e.py
?? ui/backend/tests/test_grid_convergence_gci.py
?? ui/frontend/vite.config.sandbox.ts.stale.1776667726
?? ui/frontend/vite.config.sandbox.ts.timestamp-1776667276256-33cd5f0862292.mjs

codex
I have the core diff. Next step is line-by-line inspection of `manifest.py`, `serialize.py`, the new GCI service, and the targeted tests, because the main risks here are in the exact control flow and boundary guards rather than the phase summary.
exec
/bin/zsh -lc "nl -ba src/audit_package/manifest.py | sed -n '1,260p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
     1	"""Manifest builder for audit-package bundles (Phase 5 · PR-5a).
     2	
     3	Produces a deterministic nested dict capturing everything a regulated-industry
     4	reviewer needs to reconstruct a V&V claim:
     5	
     6	- Case metadata (whitelist entry verbatim + git-pinned)
     7	- Gold standard (full physics_contract + observables + git-pinned)
     8	- Run inputs (controlDict / blockMeshDict / fvSchemes / fvSolution / 0/ fields)
     9	- Run outputs (log tail + final residuals + postProcessing/sets output)
    10	- Measurement (key_quantities from comparator)
    11	- Comparator verdict + audit concerns
    12	- Decision trail (DEC-V61-* referencing this case or its legacy aliases)
    13	- Git repo commit SHA at manifest-build time
    14	- Generation timestamp (ISO-8601 UTC, second precision)
    15	
    16	Determinism guarantees (byte-stable across two identical invocations):
    17	- All dict keys sort via ``json.dumps(..., sort_keys=True)`` in serializers.
    18	- Timestamps are caller-injectable; when auto-generated they use UTC second
    19	  precision.
    20	- File paths stored as repo-relative POSIX strings.
    21	- Git-log lookups use ``--format=%H`` (no timestamp). Absence of a git repo
    22	  yields ``None`` rather than raising — the manifest still builds.
    23	- Decision-trail discovery is deterministic: glob sorted, body-grep matched.
    24	
    25	Non-goals for PR-5a:
    26	- HMAC signing (PR-5c).
    27	- Zip/PDF serialization (PR-5b).
    28	- UI wiring (PR-5d).
    29	- OpenFOAM solver invocation (out of scope; caller provides run_output_dir
    30	  pointing at already-completed output from FoamAgentExecutor or MockExecutor).
    31	"""
    32	
    33	from __future__ import annotations
    34	
    35	import datetime as _dt
    36	import hashlib
    37	import subprocess
    38	from pathlib import Path
    39	from typing import Any, Dict, List, Optional, Sequence
    40	
    41	import yaml
    42	
    43	SCHEMA_VERSION = 1
    44	
    45	_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
    46	_WHITELIST_PATH = _REPO_ROOT / "knowledge" / "whitelist.yaml"
    47	_GOLD_STANDARDS_ROOT = _REPO_ROOT / "knowledge" / "gold_standards"
    48	_DECISIONS_ROOT = _REPO_ROOT / ".planning" / "decisions"
    49	
    50	# Run-input files collected verbatim when present. Order-stable list.
    51	_RUN_INPUT_FILES = (
    52	    "system/controlDict",
    53	    "system/blockMeshDict",
    54	    "system/fvSchemes",
    55	    "system/fvSolution",
    56	    "system/sampleDict",
    57	    "constant/physicalProperties",
    58	    "constant/transportProperties",
    59	    "constant/turbulenceProperties",
    60	    "constant/g",
    61	)
    62	
    63	# Common initial-field filenames under 0/
    64	_INITIAL_FIELD_FILES = ("U", "p", "T", "k", "epsilon", "omega", "nut", "alphat")
    65	
    66	# Number of log lines tail-read for solver_log_tail. Keeps manifest size bounded
    67	# while preserving final residuals + completion banner.
    68	_LOG_TAIL_LINES = 120
    69	
    70	
    71	# ---------------------------------------------------------------------------
    72	# Time helpers (caller-injectable for test determinism)
    73	# ---------------------------------------------------------------------------
    74	
    75	def _default_now_utc() -> str:
    76	    """UTC timestamp, second precision, Z suffix."""
    77	    return _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    78	
    79	
    80	# ---------------------------------------------------------------------------
    81	# Git helpers
    82	# ---------------------------------------------------------------------------
    83	
    84	def _git_sha_for_path(path: Path, repo_root: Path) -> Optional[str]:
    85	    """Return the SHA of the latest commit touching ``path``.
    86	
    87	    Uses ``git log -1 --format=%H -- <path>``. Returns None if git is
    88	    unavailable, the path has no commit history, or the repo is shallow
    89	    beyond this file. Never raises — the manifest still builds.
    90	    """
    91	    if not path.exists():
    92	        return None
    93	    try:
    94	        relative = path.relative_to(repo_root)
    95	    except ValueError:
    96	        relative = path
    97	    try:
    98	        result = subprocess.run(
    99	            ["git", "log", "-1", "--format=%H", "--", str(relative)],
   100	            cwd=str(repo_root),
   101	            capture_output=True,
   102	            text=True,
   103	            timeout=5,
   104	            check=False,
   105	        )
   106	    except (OSError, subprocess.SubprocessError):
   107	        return None
   108	    sha = (result.stdout or "").strip()
   109	    return sha if sha else None
   110	
   111	
   112	def _git_repo_head_sha(repo_root: Path) -> Optional[str]:
   113	    """Return HEAD SHA of repo_root's repo. None if git unavailable."""
   114	    try:
   115	        result = subprocess.run(
   116	            ["git", "rev-parse", "HEAD"],
   117	            cwd=str(repo_root),
   118	            capture_output=True,
   119	            text=True,
   120	            timeout=5,
   121	            check=False,
   122	        )
   123	    except (OSError, subprocess.SubprocessError):
   124	        return None
   125	    sha = (result.stdout or "").strip()
   126	    return sha if sha else None
   127	
   128	
   129	# ---------------------------------------------------------------------------
   130	# Knowledge loaders
   131	# ---------------------------------------------------------------------------
   132	
   133	def _load_whitelist_entry(
   134	    case_id: str,
   135	    whitelist_path: Path,
   136	    legacy_aliases: Sequence[str] = (),
   137	) -> Optional[Dict[str, Any]]:
   138	    """Pull the full case dict from whitelist.yaml by id OR legacy alias."""
   139	    if not whitelist_path.exists():
   140	        return None
   141	    try:
   142	        data = yaml.safe_load(whitelist_path.read_text(encoding="utf-8")) or {}
   143	    except (yaml.YAMLError, OSError):
   144	        return None
   145	    candidates = (case_id, *legacy_aliases)
   146	    for case in data.get("cases", []):
   147	        if case.get("id") in candidates:
   148	            return case
   149	    return None
   150	
   151	
   152	def _load_gold_standard(
   153	    case_id: str,
   154	    gold_root: Path,
   155	    legacy_aliases: Sequence[str] = (),
   156	) -> Optional[Dict[str, Any]]:
   157	    """Load the gold_standards YAML for case_id or any legacy alias."""
   158	    if not gold_root.is_dir():
   159	        return None
   160	    for candidate in (case_id, *legacy_aliases):
   161	        path = gold_root / f"{candidate}.yaml"
   162	        if path.exists():
   163	            try:
   164	                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
   165	                if isinstance(data, dict):
   166	                    return data
   167	            except (yaml.YAMLError, OSError):
   168	                continue
   169	    return None
   170	
   171	
   172	# ---------------------------------------------------------------------------
   173	# Run-output loaders
   174	# ---------------------------------------------------------------------------
   175	
   176	def _read_text_if_exists(path: Path) -> Optional[str]:
   177	    """Read UTF-8 text from path; return None if absent or unreadable."""
   178	    if not path.is_file():
   179	        return None
   180	    try:
   181	        return path.read_text(encoding="utf-8", errors="replace")
   182	    except OSError:
   183	        return None
   184	
   185	
   186	def _load_run_inputs(run_output_dir: Path) -> Dict[str, Any]:
   187	    """Collect verbatim OpenFOAM input files into a dict keyed by path."""
   188	    inputs: Dict[str, Any] = {}
   189	    for rel in _RUN_INPUT_FILES:
   190	        text = _read_text_if_exists(run_output_dir / rel)
   191	        if text is not None:
   192	            inputs[rel] = text
   193	    # Initial fields under 0/
   194	    initial_fields: Dict[str, str] = {}
   195	    zero_dir = run_output_dir / "0"
   196	    if zero_dir.is_dir():
   197	        for field_name in _INITIAL_FIELD_FILES:
   198	            text = _read_text_if_exists(zero_dir / field_name)
   199	            if text is not None:
   200	                initial_fields[field_name] = text
   201	    if initial_fields:
   202	        inputs["0/"] = initial_fields
   203	    return inputs
   204	
   205	
   206	def _load_run_outputs(run_output_dir: Path) -> Dict[str, Any]:
   207	    """Solver log tail + postProcessing/sets/ listing + final residuals."""
   208	    outputs: Dict[str, Any] = {}
   209	
   210	    # Solver log — scan for common names
   211	    for log_name in ("log.simpleFoam", "log.icoFoam", "log.pimpleFoam",
   212	                     "log.buoyantFoam", "log.buoyantBoussinesqSimpleFoam"):
   213	        log_path = run_output_dir / log_name
   214	        if log_path.is_file():
   215	            try:
   216	                lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
   217	            except OSError:
   218	                continue
   219	            outputs["solver_log_name"] = log_name
   220	            outputs["solver_log_tail"] = "\n".join(lines[-_LOG_TAIL_LINES:])
   221	            break
   222	
   223	    # postProcessing/sets/ directory listing (not full content — that'd bloat
   224	    # the manifest; zip bundle in PR-5b will include the files verbatim).
   225	    pp_sets = run_output_dir / "postProcessing" / "sets"
   226	    if pp_sets.is_dir():
   227	        sets_files: List[str] = []
   228	        for time_dir in sorted(pp_sets.iterdir()):
   229	            if time_dir.is_dir():
   230	                for f in sorted(time_dir.iterdir()):
   231	                    if f.is_file():
   232	                        sets_files.append(
   233	                            str(f.relative_to(run_output_dir)).replace("\\", "/")
   234	                        )
   235	        if sets_files:
   236	            outputs["postProcessing_sets_files"] = sets_files
   237	
   238	    return outputs
   239	
   240	
   241	# ---------------------------------------------------------------------------
   242	# Decision trail
   243	# ---------------------------------------------------------------------------
   244	
   245	def _load_decision_trail(
   246	    case_id: str,
   247	    decisions_root: Path,
   248	    legacy_aliases: Sequence[str] = (),
   249	) -> List[Dict[str, str]]:
   250	    """Find DEC-V61-* / DEC-ADWM-* records that mention case_id or aliases.
   251	
   252	    Returns a deterministic sorted list of ``{"decision_id", "title",
   253	    "relative_path"}`` dicts. Matches are body-grep against the full file.
   254	    """
   255	    if not decisions_root.is_dir():
   256	        return []
   257	    needles = (case_id, *legacy_aliases)
   258	    trail: List[Dict[str, str]] = []
   259	    for md in sorted(decisions_root.glob("*.md")):
   260	        try:

exec
/bin/zsh -lc "nl -ba src/audit_package/manifest.py | sed -n '520,680p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   520	    # Resolve the actual gold file path for SHA pinning. Prefer canonical;
   521	    # fall back to legacy.
   522	    gold_file_path: Optional[Path] = None
   523	    for candidate in (case_id, *extended_aliases):
   524	        p = _GOLD_STANDARDS_ROOT / f"{candidate}.yaml"
   525	        if p.exists():
   526	            gold_file_path = p
   527	            break
   528	
   529	    git_section: Dict[str, Optional[str]] = {
   530	        "repo_commit_sha": _git_repo_head_sha(repo_root),
   531	        "whitelist_commit_sha": _git_sha_for_path(_WHITELIST_PATH, repo_root),
   532	        "gold_standard_commit_sha": (
   533	            _git_sha_for_path(gold_file_path, repo_root) if gold_file_path else None
   534	        ),
   535	    }
   536	
   537	    run_section: Dict[str, Any] = {"run_id": run_id}
   538	    if solver_name:
   539	        run_section["solver"] = solver_name
   540	    if run_output_dir is not None and run_output_dir.is_dir():
   541	        run_section["status"] = "output_present"
   542	        run_section["output_dir"] = str(run_output_dir)
   543	        inputs = _load_run_inputs(run_output_dir)
   544	        if inputs:
   545	            run_section["inputs"] = inputs
   546	        outputs = _load_run_outputs(run_output_dir)
   547	        if outputs:
   548	            run_section["outputs"] = outputs
   549	    else:
   550	        run_section["status"] = "no_run_output"
   551	
   552	    measurement_section: Dict[str, Any] = {
   553	        "key_quantities": dict(measurement or {}),
   554	        "comparator_verdict": comparator_verdict,
   555	        "audit_concerns": list(audit_concerns or []),
   556	    }
   557	
   558	    manifest: Dict[str, Any] = {
   559	        "schema_version": SCHEMA_VERSION,
   560	        "manifest_id": f"{case_id}-{run_id}",
   561	        "build_fingerprint": build_fingerprint or _default_now_utc(),
   562	        "git": git_section,
   563	        "case": {
   564	            "id": case_id,
   565	            "legacy_ids": list(extended_aliases),
   566	            "whitelist_entry": whitelist_entry,
   567	            "gold_standard": gold_standard,
   568	        },
   569	        "run": run_section,
   570	        "measurement": measurement_section,
   571	        "decision_trail": decision_trail,
   572	    }
   573	    # Phase 7e (DEC-V61-033): L4 schema — embed Phase 7 artifacts (field
   574	    # captures, renders, comparison report PDF) into the signed zip.
   575	    # Only attached when include_phase7=True AND artifacts exist for this run.
   576	    if include_phase7:
   577	        phase7 = _collect_phase7_artifacts(case_id, run_id, repo_root)
   578	        if phase7 is not None:
   579	            manifest["phase7"] = phase7
   580	    return manifest

exec
/bin/zsh -lc "nl -ba src/audit_package/manifest.py | sed -n '260,520p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   260	        try:
   261	            text = md.read_text(encoding="utf-8", errors="replace")
   262	        except OSError:
   263	            continue
   264	        if not any(needle in text for needle in needles):
   265	            continue
   266	        decision_id = _extract_frontmatter_field(text, "decision_id")
   267	        title = _extract_first_heading(text)
   268	        trail.append({
   269	            "decision_id": decision_id or md.stem,
   270	            "title": title or md.stem,
   271	            "relative_path": str(md.relative_to(decisions_root.parent.parent)).replace("\\", "/"),
   272	        })
   273	    # Sort by decision_id for stability
   274	    trail.sort(key=lambda entry: entry["decision_id"])
   275	    return trail
   276	
   277	
   278	def _extract_frontmatter_field(text: str, field: str) -> Optional[str]:
   279	    """Pull a top-level YAML frontmatter field (between ``---`` fences)."""
   280	    lines = text.splitlines()
   281	    if not lines or lines[0].strip() != "---":
   282	        return None
   283	    for i, line in enumerate(lines[1:], start=1):
   284	        if line.strip() == "---":
   285	            break
   286	        stripped = line.strip()
   287	        if stripped.startswith(f"{field}:"):
   288	            value = stripped[len(field) + 1:].strip()
   289	            return value.strip('"\'') or None
   290	    return None
   291	
   292	
   293	def _extract_first_heading(text: str) -> Optional[str]:
   294	    """First ``# Heading`` after optional frontmatter."""
   295	    for line in text.splitlines():
   296	        if line.startswith("# "):
   297	            return line[2:].strip()
   298	    return None
   299	
   300	
   301	# ---------------------------------------------------------------------------
   302	# Public builder
   303	# ---------------------------------------------------------------------------
   304	
   305	# --- Phase 7e (DEC-V61-033, L4): embed Phase 7 artifacts into signed zip ---
   306	
   307	# Deterministic YYYYMMDDTHHMMSSZ shape for run timestamps (mirrors 7a/7b/7c gates).
   308	import re as _re
   309	_PHASE7_TIMESTAMP_RE = _re.compile(r"^\d{8}T\d{6}Z$")
   310	
   311	
   312	def _sha256_of_file(path: Path) -> str:
   313	    h = hashlib.sha256()
   314	    with path.open("rb") as f:
   315	        for chunk in iter(lambda: f.read(65536), b""):
   316	            h.update(chunk)
   317	    return h.hexdigest()
   318	
   319	
   320	def _collect_phase7_artifacts(
   321	    case_id: str, run_id: str, repo_root: Path
   322	) -> Optional[Dict[str, Any]]:
   323	    """Collect Phase 7a/7b/7c artifacts for (case, run) into a manifest section.
   324	
   325	    Returns dict with ``entries`` = sorted list of {zip_path, disk_path, sha256,
   326	    size_bytes} dicts + ``schema_level: "L4"``. Returns None when no Phase 7
   327	    artifacts exist for this run.
   328	
   329	    Byte-reproducibility preserved:
   330	    - Disk paths derive from deterministic timestamp folders.
   331	    - SHA256 of each file is stable.
   332	    - Entry list is sorted by ``zip_path``.
   333	    - Manifest embeds hashes, not bytes — serialize.py then reads the files.
   334	
   335	    Security: timestamp values read from Phase 7a/7b manifests are validated
   336	    against _PHASE7_TIMESTAMP_RE (defense-in-depth against manifest tampering,
   337	    mirrors Phase 7a `_TIMESTAMP_RE` + Phase 7c `_resolve_artifact_dir`).
   338	    """
   339	    import json as _json
   340	    fields_root = repo_root / "reports" / "phase5_fields" / case_id
   341	    renders_root = repo_root / "reports" / "phase5_renders" / case_id
   342	    reports_root = repo_root / "reports" / "phase5_reports" / case_id
   343	
   344	    entries: List[Dict[str, Any]] = []
   345	
   346	    def _add(path: Path, zip_path: str) -> None:
   347	        """Add a file to entries list if it exists, validates under a sanctioned root."""
   348	        if not path.is_file():
   349	            return
   350	        try:
   351	            resolved = path.resolve(strict=True)
   352	        except (OSError, FileNotFoundError):
   353	            return
   354	        # Every zip entry must resolve under one of the three Phase 7 roots.
   355	        ok = False
   356	        for root in (fields_root, renders_root, reports_root):
   357	            try:
   358	                resolved.relative_to(root.resolve())
   359	                ok = True
   360	                break
   361	            except (ValueError, OSError):
   362	                continue
   363	        if not ok:
   364	            return
   365	        entries.append({
   366	            "zip_path": zip_path,
   367	            "disk_path_rel": str(path.relative_to(repo_root)),
   368	            "sha256": _sha256_of_file(path),
   369	            "size_bytes": path.stat().st_size,
   370	        })
   371	
   372	    # Phase 7a — field artifacts (VTK + sample + residuals).
   373	    f_manifest = fields_root / "runs" / f"{run_id}.json"
   374	    if f_manifest.is_file():
   375	        try:
   376	            f_data = _json.loads(f_manifest.read_text(encoding="utf-8"))
   377	        except (ValueError, OSError):
   378	            f_data = None
   379	        if isinstance(f_data, dict):
   380	            ts = f_data.get("timestamp")
   381	            if isinstance(ts, str) and _PHASE7_TIMESTAMP_RE.match(ts):
   382	                case_ts_dir = fields_root / ts
   383	                if case_ts_dir.is_dir():
   384	                    for p in sorted(case_ts_dir.rglob("*")):
   385	                        if not p.is_file():
   386	                            continue
   387	                        try:
   388	                            rel = p.resolve().relative_to(case_ts_dir.resolve()).as_posix()
   389	                        except (ValueError, OSError):
   390	                            continue
   391	                        # Skip huge non-essential files to keep zip sane.
   392	                        if p.suffix.lower() == ".vtk" and p.stat().st_size > 50 * 1024 * 1024:
   393	                            continue
   394	                        _add(p, f"phase7/field_artifacts/{rel}")
   395	
   396	    # Phase 7b — renders.
   397	    r_manifest = renders_root / "runs" / f"{run_id}.json"
   398	    if r_manifest.is_file():
   399	        try:
   400	            r_data = _json.loads(r_manifest.read_text(encoding="utf-8"))
   401	        except (ValueError, OSError):
   402	            r_data = None
   403	        if isinstance(r_data, dict):
   404	            ts = r_data.get("timestamp")
   405	            if isinstance(ts, str) and _PHASE7_TIMESTAMP_RE.match(ts):
   406	                r_ts_dir = renders_root / ts
   407	                if r_ts_dir.is_dir():
   408	                    for p in sorted(r_ts_dir.rglob("*")):
   409	                        if not p.is_file():
   410	                            continue
   411	                        try:
   412	                            rel = p.resolve().relative_to(r_ts_dir.resolve()).as_posix()
   413	                        except (ValueError, OSError):
   414	                            continue
   415	                        _add(p, f"phase7/renders/{rel}")
   416	
   417	    # Phase 7c — HTML + PDF comparison report. Report dir is keyed by the
   418	    # same timestamp (7c service writes under reports/phase5_reports/{case}/{ts}/).
   419	    # Pull the timestamp from the 7a manifest (authoritative).
   420	    if f_manifest.is_file():
   421	        try:
   422	            f_data = _json.loads(f_manifest.read_text(encoding="utf-8"))
   423	        except (ValueError, OSError):
   424	            f_data = None
   425	        if isinstance(f_data, dict):
   426	            ts = f_data.get("timestamp")
   427	            if isinstance(ts, str) and _PHASE7_TIMESTAMP_RE.match(ts):
   428	                pdf = reports_root / ts / f"{run_id}_comparison_report.pdf"
   429	                if pdf.is_file():
   430	                    _add(pdf, "phase7/comparison_report.pdf")
   431	
   432	    if not entries:
   433	        return None
   434	
   435	    entries.sort(key=lambda d: d["zip_path"])
   436	    return {
   437	        "schema_level": "L4",
   438	        "canonical_spec": "docs/specs/audit_package_canonical_L4.md",
   439	        "entries": entries,
   440	        "total_files": len(entries),
   441	        "total_bytes": sum(e["size_bytes"] for e in entries),
   442	    }
   443	
   444	
   445	def build_manifest(
   446	    *,
   447	    case_id: str,
   448	    run_id: str,
   449	    run_output_dir: Optional[Path] = None,
   450	    repo_root: Path = _REPO_ROOT,
   451	    legacy_case_ids: Sequence[str] = (),
   452	    measurement: Optional[Dict[str, Any]] = None,
   453	    comparator_verdict: Optional[str] = None,
   454	    audit_concerns: Optional[Sequence[Dict[str, Any]]] = None,
   455	    build_fingerprint: Optional[str] = None,
   456	    solver_name: Optional[str] = None,
   457	    include_phase7: bool = True,
   458	) -> Dict[str, Any]:
   459	    """Assemble the audit-package manifest for a single case + run.
   460	
   461	    Parameters
   462	    ----------
   463	    case_id
   464	        Whitelist case id (post-rename canonical, e.g., ``"duct_flow"``).
   465	    run_id
   466	        Caller-supplied run identifier. Expected to be deterministic for
   467	        reproducible bundles — e.g., hash of (case_id + input SHAs).
   468	    run_output_dir
   469	        Directory containing OpenFOAM outputs (produced by FoamAgentExecutor
   470	        or MockExecutor). When None, the manifest's ``run.status`` becomes
   471	        ``"no_run_output"`` and inputs/outputs sections are omitted — this
   472	        is a legitimate shape for MOCK / dry-build bundles.
   473	    repo_root
   474	        Repository root for knowledge lookups and git SHA pinning.
   475	    legacy_case_ids
   476	        Old case ids that may appear in whitelist, gold files, or decision
   477	        records (for rename histories like ``fully_developed_pipe`` →
   478	        ``duct_flow`` per DEC-V61-011).
   479	    measurement, comparator_verdict, audit_concerns
   480	        Populated by the caller from the comparator's output. All optional;
   481	        defaults to a skeleton with None/empty.
   482	    build_fingerprint
   483	        Deterministic identifier for this manifest. Renamed from
   484	        ``generated_at`` per Codex round-5 L3 finding
   485	        (DEC-V61-019): the value is derived from inputs rather than
   486	        wall-clock time, so ``generated_at`` was a misleading label.
   487	        When None, defaults to an ISO-UTC timestamp (fallback for legacy
   488	        callers that did not yet switch to deterministic derivation).
   489	        Production callers should pass a deterministic string
   490	        (e.g., ``sha256(case_id|run_id)[:16]``) to preserve byte
   491	        reproducibility.
   492	    solver_name
   493	        When known (typically from whitelist), recorded at ``run.solver``
   494	        even if ``run_output_dir`` is None.
   495	
   496	    Returns
   497	    -------
   498	    dict
   499	        Nested manifest dict. See module docstring for schema.
   500	    """
   501	    aliases = tuple(legacy_case_ids)
   502	
   503	    whitelist_entry = _load_whitelist_entry(case_id, _WHITELIST_PATH, aliases)
   504	    gold_standard = _load_gold_standard(case_id, _GOLD_STANDARDS_ROOT, aliases)
   505	
   506	    # If the gold file declares legacy_case_ids, fold them into alias set so
   507	    # the decision-trail grep catches pre-rename DEC records too.
   508	    extended_aliases: List[str] = list(aliases)
   509	    if gold_standard:
   510	        gold_legacy = gold_standard.get("legacy_case_ids")
   511	        if isinstance(gold_legacy, list):
   512	            for legacy in gold_legacy:
   513	                if isinstance(legacy, str) and legacy not in extended_aliases:
   514	                    extended_aliases.append(legacy)
   515	
   516	    decision_trail = _load_decision_trail(
   517	        case_id, _DECISIONS_ROOT, tuple(extended_aliases)
   518	    )
   519	
   520	    # Resolve the actual gold file path for SHA pinning. Prefer canonical;

exec
/bin/zsh -lc "nl -ba src/audit_package/serialize.py | sed -n '1,260p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba ui/backend/services/grid_convergence.py | sed -n '1,320p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
     1	"""Manifest → byte-reproducible zip + human-readable HTML/PDF (Phase 5 · PR-5b).
     2	
     3	Given a manifest dict from :func:`src.audit_package.manifest.build_manifest`,
     4	this module serializes it two ways:
     5	
     6	- **zip**: byte-identical output for identical input. Epoch-zero mtimes,
     7	  canonical path ordering, no system metadata, deterministic compression.
     8	  This is the machine-verifiable evidence bundle that PR-5c HMAC-signs.
     9	
    10	- **HTML**: semantic human-readable render of the manifest. Rendered
    11	  inline from a string template (no Jinja, no external CDN) so the output
    12	  is deterministic and reviewable without network access.
    13	
    14	- **PDF**: optional; wraps the HTML output via weasyprint. Requires native
    15	  libs (``pango``, ``cairo``, ``libgobject``) which on macOS are installed
    16	  via ``brew install weasyprint``. When unavailable, :func:`serialize_pdf`
    17	  raises :class:`PdfBackendUnavailable` with actionable install instructions
    18	  rather than silently falling back — the auditor should know when PDF
    19	  generation is skipped.
    20	
    21	Determinism
    22	-----------
    23	Zip byte-equality across invocations is a hard guarantee — the PR-5c HMAC
    24	signature covers the zip bytes, so any reordering or metadata drift would
    25	invalidate signatures between identical runs. Enforced via:
    26	
    27	- ``ZipInfo.date_time = (1980, 1, 1, 0, 0, 0)`` (smallest zip epoch).
    28	- ``ZipInfo.external_attr = 0o644 << 16`` for files, ``0o755 << 16`` for
    29	  directories. No setuid/setgid/sticky.
    30	- Entries added in sorted path order.
    31	- ``compress_type = ZIP_DEFLATED`` with compresslevel 6 (zlib default).
    32	- No zip comment, no extra fields.
    33	
    34	HTML is rendered by f-string concatenation in sorted-key order at every
    35	dict level, so equivalent manifests produce equivalent HTML.
    36	
    37	Non-goals
    38	---------
    39	- HMAC signing → PR-5c / DEC-V61-014.
    40	- Solver invocation → out of scope entirely (caller provides manifest).
    41	- JSON schema validation → not needed internally; would only matter if an
    42	  external consumer parsed the dict.
    43	"""
    44	
    45	from __future__ import annotations
    46	
    47	import html as _html
    48	import io
    49	import json
    50	import zipfile
    51	from pathlib import Path
    52	from typing import Any, Dict, Optional, Tuple
    53	
    54	# ---------------------------------------------------------------------------
    55	# Zip determinism constants
    56	# ---------------------------------------------------------------------------
    57	
    58	_ZIP_EPOCH: Tuple[int, int, int, int, int, int] = (1980, 1, 1, 0, 0, 0)
    59	_FILE_PERM = 0o644 << 16
    60	_DIR_PERM = 0o755 << 16
    61	_COMPRESS_LEVEL = 6  # zlib default
    62	
    63	
    64	# ---------------------------------------------------------------------------
    65	# Canonical JSON (shared by zip + signing in PR-5c)
    66	# ---------------------------------------------------------------------------
    67	
    68	def _canonical_json(obj: Any) -> bytes:
    69	    """JSON encode with sorted keys, UTF-8, \\n terminator.
    70	
    71	    The trailing newline is canonical — a manifest is a line-oriented
    72	    record, easier to diff + paginate. ``ensure_ascii=False`` preserves
    73	    non-ASCII identifiers in the decision trail.
    74	    """
    75	    text = json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2)
    76	    return (text + "\n").encode("utf-8")
    77	
    78	
    79	# ---------------------------------------------------------------------------
    80	# Deterministic zip
    81	# ---------------------------------------------------------------------------
    82	
    83	def _fixed_zipinfo(name: str, *, is_dir: bool = False) -> zipfile.ZipInfo:
    84	    """Build a zero-metadata ZipInfo with epoch mtime + fixed permissions."""
    85	    info = zipfile.ZipInfo(filename=name, date_time=_ZIP_EPOCH)
    86	    info.external_attr = _DIR_PERM if is_dir else _FILE_PERM
    87	    info.create_system = 3  # UNIX — prevents OS-dependent drift
    88	    if is_dir:
    89	        info.external_attr |= 0x10  # MS-DOS directory flag
    90	    info.compress_type = zipfile.ZIP_DEFLATED
    91	    return info
    92	
    93	
    94	def _zip_entries_from_manifest(manifest: Dict[str, Any]) -> Dict[str, bytes]:
    95	    """Lay out the zip entries as ``{path: bytes}`` before writing.
    96	
    97	    Layout:
    98	
    99	    - ``manifest.json`` — canonical JSON dump of the full manifest dict.
   100	    - ``case/whitelist_entry.json`` — whitelist case dict (canonical JSON).
   101	    - ``case/gold_standard.json`` — gold standard dict (canonical JSON).
   102	    - ``run/inputs/<path>`` — each verbatim solver input file.
   103	    - ``run/outputs/solver_log_tail.txt`` — solver log tail (if present).
   104	    - ``decisions/DEC-*.txt`` — one-line pointer per decision-trail entry.
   105	
   106	    All paths are POSIX-style; no leading slash; no Windows separators.
   107	    """
   108	    entries: Dict[str, bytes] = {}
   109	
   110	    entries["manifest.json"] = _canonical_json(manifest)
   111	
   112	    case = manifest.get("case") or {}
   113	    if case.get("whitelist_entry"):
   114	        entries["case/whitelist_entry.json"] = _canonical_json(case["whitelist_entry"])
   115	    if case.get("gold_standard"):
   116	        entries["case/gold_standard.json"] = _canonical_json(case["gold_standard"])
   117	
   118	    run = manifest.get("run") or {}
   119	    run_inputs = run.get("inputs") or {}
   120	    for rel_path, content in sorted(run_inputs.items()):
   121	        if rel_path == "0/" and isinstance(content, dict):
   122	            for field_name, field_body in sorted(content.items()):
   123	                if isinstance(field_body, str):
   124	                    entries[f"run/inputs/0/{field_name}"] = field_body.encode("utf-8")
   125	        elif isinstance(content, str):
   126	            entries[f"run/inputs/{rel_path}"] = content.encode("utf-8")
   127	
   128	    run_outputs = run.get("outputs") or {}
   129	    log_tail = run_outputs.get("solver_log_tail")
   130	    if isinstance(log_tail, str):
   131	        entries["run/outputs/solver_log_tail.txt"] = log_tail.encode("utf-8")
   132	
   133	    decisions = manifest.get("decision_trail") or []
   134	    for decision in decisions:
   135	        did = decision.get("decision_id") or "UNKNOWN"
   136	        title = decision.get("title") or ""
   137	        path = decision.get("relative_path") or ""
   138	        body = f"decision_id: {did}\ntitle: {title}\nrelative_path: {path}\n"
   139	        entries[f"decisions/{did}.txt"] = body.encode("utf-8")
   140	
   141	    # Phase 7e (DEC-V61-033, L4): embed Phase 7 artifacts if manifest carries
   142	    # the phase7 section. Each entry's file is read verbatim and SHA256 has
   143	    # already been pre-computed by the manifest builder — zip is byte-stable
   144	    # as long as the source files on disk are byte-stable (they are: fixed
   145	    # OpenFOAM output, deterministic renders, deterministic PDF per input).
   146	    phase7 = manifest.get("phase7")
   147	    if isinstance(phase7, dict):
   148	        import pathlib as _pl
   149	        repo_root = _pl.Path(__file__).resolve().parents[2]
   150	        phase7_entries = phase7.get("entries") or []
   151	        for entry in phase7_entries:
   152	            if not isinstance(entry, dict):
   153	                continue
   154	            zip_path = entry.get("zip_path")
   155	            disk_rel = entry.get("disk_path_rel")
   156	            if not isinstance(zip_path, str) or not isinstance(disk_rel, str):
   157	                continue
   158	            disk_path = repo_root / disk_rel
   159	            if not disk_path.is_file():
   160	                continue
   161	            try:
   162	                # Defense-in-depth: ensure resolved path stays under repo root.
   163	                resolved = disk_path.resolve(strict=True)
   164	                resolved.relative_to(repo_root.resolve())
   165	            except (ValueError, OSError, FileNotFoundError):
   166	                continue
   167	            try:
   168	                entries[zip_path] = resolved.read_bytes()
   169	            except OSError:
   170	                continue
   171	
   172	    return entries
   173	
   174	
   175	def serialize_zip_bytes(manifest: Dict[str, Any]) -> bytes:
   176	    """Build the audit-package zip as bytes, byte-identical across calls.
   177	
   178	    The function is pure: same input → same bytes. This is the property
   179	    PR-5c's HMAC signature depends on.
   180	    """
   181	    entries = _zip_entries_from_manifest(manifest)
   182	    buf = io.BytesIO()
   183	    with zipfile.ZipFile(buf, mode="w", allowZip64=False) as zf:
   184	        for path in sorted(entries.keys()):
   185	            info = _fixed_zipinfo(path, is_dir=False)
   186	            zf.writestr(info, entries[path], compresslevel=_COMPRESS_LEVEL)
   187	    return buf.getvalue()
   188	
   189	
   190	def serialize_zip(manifest: Dict[str, Any], output_path: Path) -> None:
   191	    """Write the byte-reproducible zip to ``output_path`` (overwrites)."""
   192	    output_path.parent.mkdir(parents=True, exist_ok=True)
   193	    output_path.write_bytes(serialize_zip_bytes(manifest))
   194	
   195	
   196	# ---------------------------------------------------------------------------
   197	# HTML render
   198	# ---------------------------------------------------------------------------
   199	
   200	_CSS = """\
   201	body { font-family: -apple-system, system-ui, sans-serif; max-width: 960px;
   202	       margin: 2em auto; padding: 0 1em; color: #222; line-height: 1.45; }
   203	h1 { border-bottom: 2px solid #333; padding-bottom: 0.3em; }
   204	h2 { margin-top: 1.8em; color: #444; }
   205	h3 { margin-top: 1.2em; color: #555; font-size: 1.05em; }
   206	table { border-collapse: collapse; width: 100%; margin: 0.5em 0 1em; }
   207	th, td { border: 1px solid #ccc; padding: 6px 10px; text-align: left; vertical-align: top; font-size: 0.92em; }
   208	th { background: #f0f0f0; font-weight: 600; }
   209	code, pre { font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
   210	           background: #f5f5f5; padding: 1px 4px; border-radius: 3px; font-size: 0.9em; }
   211	pre { padding: 10px; overflow-x: auto; white-space: pre-wrap; word-wrap: break-word; }
   212	.verdict-pass { color: #0a7d2d; font-weight: 600; }
   213	.verdict-fail { color: #b42318; font-weight: 600; }
   214	.verdict-hazard { color: #b07007; font-weight: 600; }
   215	.meta { color: #666; font-size: 0.85em; }
   216	ul.decisions li { margin: 0.3em 0; }
   217	"""
   218	
   219	
   220	def _esc(value: Any) -> str:
   221	    return _html.escape(str(value), quote=True)
   222	
   223	
   224	def _render_kv_table(data: Dict[str, Any]) -> str:
   225	    rows = []
   226	    for k in sorted(data.keys()):
   227	        rows.append(f"<tr><th>{_esc(k)}</th><td>{_esc(data[k])}</td></tr>")
   228	    return "<table>\n" + "\n".join(rows) + "\n</table>"
   229	
   230	
   231	def _render_verdict(verdict: Optional[str]) -> str:
   232	    if verdict == "PASS":
   233	        return '<span class="verdict-pass">PASS</span>'
   234	    if verdict == "FAIL":
   235	        return '<span class="verdict-fail">FAIL</span>'
   236	    if verdict == "HAZARD":
   237	        return '<span class="verdict-hazard">HAZARD</span>'
   238	    return _esc(verdict or "UNKNOWN")
   239	
   240	
   241	def render_html(manifest: Dict[str, Any]) -> str:
   242	    """Render a deterministic semantic HTML document from the manifest.
   243	
   244	    Output order is fixed (header → git → case → run → measurement →
   245	    decisions) so two identical manifests produce identical HTML bytes.
   246	    """
   247	    manifest_id = _esc(manifest.get("manifest_id") or "UNKNOWN")
   248	    build_fingerprint = _esc(manifest.get("build_fingerprint") or "")
   249	    schema_version = _esc(manifest.get("schema_version") or "")
   250	
   251	    git = manifest.get("git") or {}
   252	    git_rows = "\n".join(
   253	        f"<tr><th>{_esc(k)}</th><td><code>{_esc(git.get(k) or '—')}</code></td></tr>"
   254	        for k in sorted(git.keys())
   255	    )
   256	
   257	    case = manifest.get("case") or {}
   258	    case_id = _esc(case.get("id") or "UNKNOWN")
   259	    legacy_ids = case.get("legacy_ids") or []
   260	    legacy_html = (

 succeeded in 0ms:
     1	"""Phase 7d — Richardson extrapolation + Grid Convergence Index (GCI).
     2	
     3	Per Roache 1994 (J. Fluids Eng. 116, 405-413) and Celik et al. 2008
     4	(ASME V&V 20 standard). Given three successively-refined mesh solutions
     5	f_1 (coarse), f_2 (medium), f_3 (fine) with refinement ratios r_21 = h_2/h_1,
     6	r_32 = h_3/h_2:
     7	
     8	    p_obs = |ln(|(f_3 - f_2)/(f_2 - f_1)|)| / ln(r)    (uniform r)
     9	
    10	    ε_21 = |f_2 - f_1|/|f_1|
    11	    GCI_21 = Fs * ε_21 / (r_21^p - 1)       (coarse-to-medium uncertainty)
    12	    GCI_32 = Fs * ε_32 / (r_32^p - 1)       (medium-to-fine uncertainty)
    13	
    14	Fs = safety factor (1.25 for 3-grid, 3.0 for 2-grid).
    15	
    16	We consume the mesh_20/40/80/160 fixtures already at
    17	`ui/backend/tests/fixtures/runs/{case}/mesh_{N}_measurement.yaml`.
    18	These are 4 meshes; we compute GCI over the finest three (40/80/160)
    19	which is standard practice, and return auxiliary info for the coarsest.
    20	
    21	This is pure numerical code — no Docker, no src/ touch, no 三禁区.
    22	"""
    23	from __future__ import annotations
    24	
    25	import math
    26	from dataclasses import dataclass
    27	from pathlib import Path
    28	from typing import Optional
    29	
    30	import yaml
    31	
    32	_REPO_ROOT = Path(__file__).resolve().parents[3]
    33	_FIXTURE_ROOT = _REPO_ROOT / "ui" / "backend" / "tests" / "fixtures" / "runs"
    34	
    35	
    36	@dataclass(frozen=True)
    37	class MeshSolution:
    38	    label: str          # e.g. "mesh_40"
    39	    n_cells_1d: int     # e.g. 40 (for an N×N×1 LDC mesh)
    40	    value: float        # the scalar comparator quantity
    41	
    42	
    43	@dataclass(frozen=True)
    44	class RichardsonGCI:
    45	    """Output of Richardson + GCI computation on three successive meshes.
    46	
    47	    Follows Celik et al. 2008 nomenclature: subscripts 1/2/3 go
    48	    coarse-to-fine, so r_21 = h_2/h_1 with r > 1 means refined.
    49	    """
    50	    coarse: MeshSolution        # f_1
    51	    medium: MeshSolution        # f_2
    52	    fine: MeshSolution          # f_3
    53	    r_21: float                 # refinement ratio coarse → medium
    54	    r_32: float                 # medium → fine
    55	    p_obs: Optional[float]      # observed order of accuracy
    56	    f_extrapolated: Optional[float]   # Richardson extrapolation to h→0
    57	    e_21: float                 # relative change coarse→medium
    58	    e_32: float                 # relative change medium→fine
    59	    gci_21: Optional[float]     # coarse-mesh uncertainty band
    60	    gci_32: Optional[float]     # fine-mesh uncertainty band
    61	    asymptotic_range_ok: Optional[bool]  # True if GCI_32 * r^p ≈ GCI_21 within 1.25x
    62	    note: str                   # human-readable diagnostic
    63	
    64	
    65	_FS_THREE_GRID = 1.25
    66	
    67	
    68	def compute_richardson_gci(
    69	    coarse: MeshSolution,
    70	    medium: MeshSolution,
    71	    fine: MeshSolution,
    72	) -> RichardsonGCI:
    73	    """Compute Richardson extrapolation + GCI for three solutions.
    74	
    75	    Handles degenerate cases:
    76	    - (f_2 - f_1) ≈ 0 → no refinement signal, p_obs undefined
    77	    - oscillating signs (f_3 - f_2) and (f_2 - f_1) opposite → p_obs flagged note
    78	    - non-uniform refinement ratio — uses average per Celik §2.3
    79	    """
    80	    # Celik 2008 convention: r = h_coarse / h_fine > 1 with h ∝ 1/N for uniform meshes.
    81	    # So r_21 = h_1/h_2 = N_2/N_1 (medium cells / coarse cells) must be > 1.
    82	    r_21 = medium.n_cells_1d / coarse.n_cells_1d
    83	    r_32 = fine.n_cells_1d / medium.n_cells_1d
    84	    if r_21 <= 1 or r_32 <= 1:
    85	        raise ValueError(
    86	            f"meshes not monotonically refined: "
    87	            f"n_1d = {coarse.n_cells_1d}, {medium.n_cells_1d}, {fine.n_cells_1d}"
    88	        )
    89	
    90	    eps_21 = medium.value - coarse.value
    91	    eps_32 = fine.value - medium.value
    92	
    93	    # Celik 2008 Eq. 4: approximate relative error uses the REFINED solution
    94	    # (downstream value) as denominator, not the upstream.
    95	    e_21 = abs(eps_21 / medium.value) if abs(medium.value) > 1e-12 else float("inf")
    96	    e_32 = abs(eps_32 / fine.value) if abs(fine.value) > 1e-12 else float("inf")
    97	
    98	    p_obs: Optional[float] = None
    99	    f_ext: Optional[float] = None
   100	    gci_21: Optional[float] = None
   101	    gci_32: Optional[float] = None
   102	    asymptotic_ok: Optional[bool] = None
   103	    note = "ok"
   104	
   105	    # Observed order requires non-trivial refinement signal on both stages.
   106	    if abs(eps_21) < 1e-14 or abs(eps_32) < 1e-14:
   107	        note = "solution converged to within numerical precision on coarse triple; p_obs undefined"
   108	    elif eps_21 * eps_32 < 0:
   109	        note = (
   110	            "oscillating convergence (sign flip between refinement stages) "
   111	            "— Richardson formula does not directly apply; p_obs omitted"
   112	        )
   113	    else:
   114	        # Uniform refinement ratio case (r_21 = r_32): simple log-ratio.
   115	        # Non-uniform: use Celik §2.3 fixed-point iteration. We'll pick the
   116	        # simple form when ratios agree within 5%; else iterate.
   117	        ratio_diff = abs(r_21 - r_32) / r_21
   118	        if ratio_diff < 0.05:
   119	            r = 0.5 * (r_21 + r_32)
   120	            ratio = eps_32 / eps_21
   121	            if abs(ratio) > 1e-300:
   122	                p_obs = abs(math.log(abs(ratio))) / math.log(r)
   123	        else:
   124	            # Celik iterative method: p from ln(|eps_32 - sign*r_32^p|/|r_21^p * eps_21 - sign|)
   125	            # Simplified iteration (Celik Eq. 2 + 3).
   126	            sign = 1.0 if eps_32 * eps_21 > 0 else -1.0
   127	            p_guess = 2.0
   128	            for _ in range(50):
   129	                try:
   130	                    q = math.log(
   131	                        (r_21 ** p_guess - sign) / (r_32 ** p_guess - sign)
   132	                    )
   133	                    new_p = (1.0 / math.log(r_21)) * abs(
   134	                        math.log(abs(eps_32 / eps_21)) + q
   135	                    )
   136	                except (ValueError, ZeroDivisionError):
   137	                    p_guess = None
   138	                    break
   139	                if abs(new_p - p_guess) < 1e-6:
   140	                    p_guess = new_p
   141	                    break
   142	                p_guess = new_p
   143	            if p_guess is not None and p_guess > 0:
   144	                p_obs = p_guess
   145	
   146	        if p_obs is not None and p_obs > 0:
   147	            # Richardson extrapolation to h → 0.
   148	            r_fine = r_32
   149	            denom = r_fine ** p_obs - 1.0
   150	            if abs(denom) > 1e-12:
   151	                f_ext = fine.value + (fine.value - medium.value) / denom
   152	            # GCI (Roache 1994 / Celik 2008 Eq. 5).
   153	            gci_21 = _FS_THREE_GRID * e_21 / (r_21 ** p_obs - 1.0)
   154	            gci_32 = _FS_THREE_GRID * e_32 / (r_32 ** p_obs - 1.0)
   155	            # Asymptotic range check: GCI_21 / (r^p * GCI_32) ≈ 1 (±25% typical).
   156	            if gci_32 and gci_32 > 0:
   157	                ratio = gci_21 / (r_21 ** p_obs * gci_32)
   158	                asymptotic_ok = 0.8 <= ratio <= 1.25
   159	                if not asymptotic_ok:
   160	                    note = (
   161	                        f"not in asymptotic range (GCI ratio = {ratio:.3f}; "
   162	                        f"target ≈ 1.0 ±25%)"
   163	                    )
   164	
   165	    return RichardsonGCI(
   166	        coarse=coarse, medium=medium, fine=fine,
   167	        r_21=r_21, r_32=r_32,
   168	        p_obs=p_obs, f_extrapolated=f_ext,
   169	        e_21=e_21, e_32=e_32,
   170	        gci_21=gci_21, gci_32=gci_32,
   171	        asymptotic_range_ok=asymptotic_ok,
   172	        note=note,
   173	    )
   174	
   175	
   176	def load_mesh_solutions_from_fixtures(
   177	    case_id: str,
   178	    mesh_labels: tuple[str, ...] = ("mesh_20", "mesh_40", "mesh_80", "mesh_160"),
   179	    fixture_root: Optional[Path] = None,
   180	) -> list[MeshSolution]:
   181	    """Read mesh_N_measurement.yaml fixtures into MeshSolution records."""
   182	    base = fixture_root or _FIXTURE_ROOT
   183	    case_dir = base / case_id
   184	    out: list[MeshSolution] = []
   185	    for lbl in mesh_labels:
   186	        p = case_dir / f"{lbl}_measurement.yaml"
   187	        if not p.is_file():
   188	            continue
   189	        doc = yaml.safe_load(p.read_text(encoding="utf-8"))
   190	        if not isinstance(doc, dict):
   191	            continue
   192	        meas = doc.get("measurement", {})
   193	        val = meas.get("value")
   194	        if val is None:
   195	            continue
   196	        try:
   197	            v = float(val)
   198	        except (ValueError, TypeError):
   199	            continue
   200	        # Derive 1D cell count from label (e.g. "mesh_40" → 40).
   201	        try:
   202	            n = int(lbl.split("_")[-1])
   203	        except ValueError:
   204	            continue
   205	        out.append(MeshSolution(label=lbl, n_cells_1d=n, value=v))
   206	    return out
   207	
   208	
   209	def compute_gci_from_fixtures(
   210	    case_id: str,
   211	    fixture_root: Optional[Path] = None,
   212	) -> Optional[RichardsonGCI]:
   213	    """Convenience wrapper: load fixtures + compute GCI over finest 3 meshes.
   214	
   215	    Returns None if fewer than 3 solutions available.
   216	    Raises ValueError if the finest 3 aren't monotonically refined.
   217	    """
   218	    sols = load_mesh_solutions_from_fixtures(case_id, fixture_root=fixture_root)
   219	    if len(sols) < 3:
   220	        return None
   221	    # Sort coarse → fine by n_cells_1d ascending, pick last 3.
   222	    sols = sorted(sols, key=lambda s: s.n_cells_1d)
   223	    coarse, medium, fine = sols[-3], sols[-2], sols[-1]
   224	    return compute_richardson_gci(coarse, medium, fine)

exec
/bin/zsh -lc "nl -ba ui/backend/tests/test_audit_package_phase7e.py | sed -n '1,320p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba scripts/render_case_report.py | sed -n '360,500p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
     1	"""Phase 7e (DEC-V61-033, L4) — audit-package Phase 7 artifact embedding tests.
     2	
     3	Guards:
     4	- When Phase 7 artifacts exist, manifest.phase7 is populated and the signed
     5	  zip contains them at phase7/* paths with byte-identical content.
     6	- When Phase 7 artifacts are absent, manifest.phase7 is omitted; signed zip
     7	  is unchanged (backward-compatible with pre-L4 audit packages).
     8	- Byte-reproducibility: two calls to build_manifest + serialize_zip with the
     9	  same inputs produce identical bytes (HMAC-stable).
    10	- Tampered Phase 7 manifest (invalid timestamp) → phase7 key absent, not 500.
    11	"""
    12	from __future__ import annotations
    13	
    14	import hashlib
    15	import json
    16	from pathlib import Path
    17	from typing import Tuple
    18	
    19	import pytest
    20	
    21	from src.audit_package.manifest import (
    22	    _PHASE7_TIMESTAMP_RE,
    23	    _collect_phase7_artifacts,
    24	    build_manifest,
    25	)
    26	from src.audit_package.serialize import (
    27	    _zip_entries_from_manifest,
    28	    serialize_zip_bytes,
    29	)
    30	
    31	
    32	# ---------- Test fixture helpers --------------------------------------------
    33	
    34	def _setup_phase7_tree(
    35	    tmp_path: Path, case_id: str = "lid_driven_cavity", run_id: str = "audit_real_run",
    36	    timestamp: str = "20260421T000000Z",
    37	) -> Tuple[Path, str]:
    38	    """Build a minimal Phase 7 artifact tree under tmp_path/reports/."""
    39	    fields = tmp_path / "reports" / "phase5_fields" / case_id
    40	    renders = tmp_path / "reports" / "phase5_renders" / case_id
    41	    reports = tmp_path / "reports" / "phase5_reports" / case_id
    42	    (fields / timestamp / "sample" / "1000").mkdir(parents=True)
    43	    (fields / timestamp / "sample" / "1000" / "uCenterline.xy").write_text(
    44	        "# y Ux Uy Uz p\n0 0 0 0 0\n0.5 -0.2 0 0 0\n1.0 1.0 0 0 0\n",
    45	        encoding="utf-8",
    46	    )
    47	    (fields / timestamp / "residuals.csv").write_text(
    48	        "Time,Ux,Uy,p\n1,1,1,1\n2,0.1,0.1,0.1\n", encoding="utf-8",
    49	    )
    50	    (fields / "runs").mkdir(parents=True)
    51	    (fields / "runs" / f"{run_id}.json").write_text(
    52	        json.dumps({"timestamp": timestamp, "case_id": case_id, "run_label": run_id}),
    53	        encoding="utf-8",
    54	    )
    55	    (renders / timestamp).mkdir(parents=True)
    56	    for n in ("profile_u_centerline.png", "residuals.png"):
    57	        (renders / timestamp / n).write_bytes(b"\x89PNG\r\n\x1a\nfake")
    58	    (renders / "runs").mkdir(parents=True)
    59	    (renders / "runs" / f"{run_id}.json").write_text(
    60	        json.dumps({"timestamp": timestamp, "case_id": case_id, "run_label": run_id,
    61	                    "outputs": {}}),
    62	        encoding="utf-8",
    63	    )
    64	    (reports / timestamp).mkdir(parents=True)
    65	    (reports / timestamp / f"{run_id}_comparison_report.pdf").write_bytes(
    66	        b"%PDF-1.7\n%fake pdf for test\n%%EOF\n",
    67	    )
    68	    return tmp_path, timestamp
    69	
    70	
    71	# ---------- _collect_phase7_artifacts unit tests ----------------------------
    72	
    73	def test_collect_phase7_happy_path(tmp_path) -> None:
    74	    _setup_phase7_tree(tmp_path)
    75	    phase7 = _collect_phase7_artifacts("lid_driven_cavity", "audit_real_run", tmp_path)
    76	    assert phase7 is not None
    77	    assert phase7["schema_level"] == "L4"
    78	    zip_paths = [e["zip_path"] for e in phase7["entries"]]
    79	    # Sorted alphabetically.
    80	    assert zip_paths == sorted(zip_paths)
    81	    # Contains field artifacts + renders + PDF.
    82	    assert any(z.startswith("phase7/field_artifacts/") for z in zip_paths)
    83	    assert any(z.startswith("phase7/renders/") for z in zip_paths)
    84	    assert "phase7/comparison_report.pdf" in zip_paths
    85	    # Every entry has a valid sha256.
    86	    for e in phase7["entries"]:
    87	        assert isinstance(e["sha256"], str)
    88	        assert len(e["sha256"]) == 64
    89	
    90	
    91	def test_collect_phase7_no_artifacts_returns_none(tmp_path) -> None:
    92	    result = _collect_phase7_artifacts("nonexistent_case", "nonexistent_run", tmp_path)
    93	    assert result is None
    94	
    95	
    96	def test_collect_phase7_rejects_tampered_timestamp(tmp_path) -> None:
    97	    """Malicious runs/{run}.json with timestamp='../../outside' must not leak files."""
    98	    _setup_phase7_tree(tmp_path)
    99	    # Overwrite the 7a manifest with a traversal attempt.
   100	    m = tmp_path / "reports" / "phase5_fields" / "lid_driven_cavity" / "runs" / "audit_real_run.json"
   101	    m.write_text(json.dumps({"timestamp": "../../etc"}), encoding="utf-8")
   102	    # Plant a would-be leak target (shouldn't be included).
   103	    leak = tmp_path / "etc" / "passwd_fake"
   104	    leak.parent.mkdir(parents=True)
   105	    leak.write_text("root:x:0:0\n", encoding="utf-8")
   106	    # Also invalidate the 7b manifest to test both paths.
   107	    mr = tmp_path / "reports" / "phase5_renders" / "lid_driven_cavity" / "runs" / "audit_real_run.json"
   108	    mr.write_text(json.dumps({"timestamp": "../../etc"}), encoding="utf-8")
   109	    phase7 = _collect_phase7_artifacts("lid_driven_cavity", "audit_real_run", tmp_path)
   110	    # Every entry (if any) must have zip_path under phase7/ — no leaks.
   111	    if phase7 is not None:
   112	        for e in phase7["entries"]:
   113	            assert e["zip_path"].startswith("phase7/"), e
   114	            assert "passwd" not in e["disk_path_rel"]
   115	            assert "/etc/" not in e["disk_path_rel"]
   116	
   117	
   118	def test_timestamp_regex_shape_gate() -> None:
   119	    for ok in ("20260421T000000Z", "20991231T235959Z"):
   120	        assert _PHASE7_TIMESTAMP_RE.match(ok)
   121	    for bad in ("2026-04-21", "../../evil", "", "abc", "20260421",
   122	                "20260421T000000z", "20260421T000000", "20260421 000000Z"):
   123	        assert _PHASE7_TIMESTAMP_RE.match(bad) is None
   124	
   125	
   126	# ---------- Integration: build_manifest + serialize_zip ----------------------
   127	
   128	def test_build_manifest_embeds_phase7(tmp_path) -> None:
   129	    _setup_phase7_tree(tmp_path)
   130	    manifest = build_manifest(
   131	        case_id="lid_driven_cavity",
   132	        run_id="audit_real_run",
   133	        repo_root=tmp_path,
   134	        include_phase7=True,
   135	    )
   136	    assert "phase7" in manifest
   137	    assert manifest["phase7"]["schema_level"] == "L4"
   138	
   139	
   140	def test_build_manifest_opt_out_phase7(tmp_path) -> None:
   141	    """Backward compat: include_phase7=False suppresses the key entirely."""
   142	    _setup_phase7_tree(tmp_path)
   143	    manifest = build_manifest(
   144	        case_id="lid_driven_cavity",
   145	        run_id="audit_real_run",
   146	        repo_root=tmp_path,
   147	        include_phase7=False,
   148	    )
   149	    assert "phase7" not in manifest
   150	
   151	
   152	def test_zip_contains_phase7_entries(tmp_path, monkeypatch) -> None:
   153	    """serialize_zip must pick up phase7 entries and include them at the
   154	    declared zip_path. Requires repo_root in serialize.py to be tmp_path."""
   155	    _setup_phase7_tree(tmp_path)
   156	    manifest = build_manifest(
   157	        case_id="lid_driven_cavity",
   158	        run_id="audit_real_run",
   159	        repo_root=tmp_path,
   160	    )
   161	    # serialize.py hardcodes repo_root = parents[2] of its own file — we need
   162	    # to exercise _zip_entries_from_manifest directly with disk paths pointing
   163	    # at our tmp_path. Easiest: monkeypatch the repo_root lookup.
   164	    import src.audit_package.serialize as ser
   165	    real_entries_fn = ser._zip_entries_from_manifest
   166	
   167	    def _patched_entries(m):
   168	        import pathlib
   169	        entries = {}
   170	        # Re-implement inline with tmp_path repo_root.
   171	        entries["manifest.json"] = ser._canonical_json(m)
   172	        phase7 = m.get("phase7")
   173	        if isinstance(phase7, dict):
   174	            for entry in phase7.get("entries") or []:
   175	                if not isinstance(entry, dict):
   176	                    continue
   177	                zp = entry.get("zip_path")
   178	                dr = entry.get("disk_path_rel")
   179	                if not isinstance(zp, str) or not isinstance(dr, str):
   180	                    continue
   181	                p = tmp_path / dr
   182	                if p.is_file():
   183	                    entries[zp] = p.read_bytes()
   184	        return entries
   185	
   186	    monkeypatch.setattr(ser, "_zip_entries_from_manifest", _patched_entries)
   187	    zip_bytes = ser.serialize_zip_bytes(manifest)
   188	
   189	    import io, zipfile
   190	    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
   191	        names = zf.namelist()
   192	        phase7_names = [n for n in names if n.startswith("phase7/")]
   193	        assert len(phase7_names) >= 3  # at least PDF + 1 render + 1 field artifact
   194	        assert "phase7/comparison_report.pdf" in names
   195	        # Verify byte-identical embedded content.
   196	        pdf_bytes = zf.read("phase7/comparison_report.pdf")
   197	        assert pdf_bytes == (tmp_path / "reports" / "phase5_reports" /
   198	                             "lid_driven_cavity" / "20260421T000000Z" /
   199	                             "audit_real_run_comparison_report.pdf").read_bytes()
   200	
   201	
   202	def test_byte_reproducibility_with_phase7(tmp_path) -> None:
   203	    """Two consecutive build_manifest + serialize_zip_bytes calls with the
   204	    same Phase 7 artifacts must produce byte-identical zips."""
   205	    _setup_phase7_tree(tmp_path)
   206	    # Both calls use the same tmp_path repo_root.
   207	    m1 = build_manifest(
   208	        case_id="lid_driven_cavity", run_id="audit_real_run",
   209	        build_fingerprint="deadbeefdeadbeef",
   210	        repo_root=tmp_path,
   211	    )
   212	    m2 = build_manifest(
   213	        case_id="lid_driven_cavity", run_id="audit_real_run",
   214	        build_fingerprint="deadbeefdeadbeef",
   215	        repo_root=tmp_path,
   216	    )
   217	    # manifest dicts equal → canonical JSON equal.
   218	    assert m1 == m2
   219	    # phase7 SHA256s identical.
   220	    sha1 = [e["sha256"] for e in m1["phase7"]["entries"]]
   221	    sha2 = [e["sha256"] for e in m2["phase7"]["entries"]]
   222	    assert sha1 == sha2

 succeeded in 0ms:
   360	    )
   361	    out = renders_dir / "pointwise_deviation.png"
   362	    fig.savefig(out)
   363	    plt.close(fig)
   364	    return out
   365	
   366	
   367	def _find_latest_vtk(artifact_dir: Path) -> Optional[Path]:
   368	    """Return the highest-iteration VTK volume file (not the allPatches one)."""
   369	    vtk_root = artifact_dir / "VTK"
   370	    if not vtk_root.is_dir():
   371	        return None
   372	    # Volume VTK files are at VTK/*.vtk (direct children); boundary data is under VTK/allPatches/.
   373	    candidates = sorted(
   374	        p for p in vtk_root.glob("*.vtk") if p.is_file()
   375	    )
   376	    return candidates[-1] if candidates else None
   377	
   378	
   379	def render_contour_u_magnitude_png(
   380	    case_id: str,
   381	    artifact_dir: Path,
   382	    renders_dir: Path,
   383	) -> Path:
   384	    """2D U-magnitude contour + streamlines from the real VTK volume (Phase 7b polish).
   385	
   386	    Phase 7b polish (2026-04-21): parse the actual OpenFOAM volume VTK via PyVista,
   387	    project onto a 129×129 XY grid (LDC is pseudo-2D, one cell thick in z),
   388	    compute |U| = sqrt(Ux² + Uy²), render contourf + streamlines via matplotlib.
   389	
   390	    Fallback to the old 1D centerline strip if PyVista/VTK parsing fails.
   391	    """
   392	    out = renders_dir / "contour_u_magnitude.png"
   393	    vtk_path = _find_latest_vtk(artifact_dir)
   394	    if vtk_path is not None:
   395	        try:
   396	            import pyvista as pv
   397	            pv.OFF_SCREEN = True
   398	            mesh = pv.read(str(vtk_path))
   399	            # Cell-centered U vector and cell centroid coords.
   400	            cd = mesh.cell_data
   401	            if "U" not in cd or "Cx" not in cd or "Cy" not in cd:
   402	                raise RenderError(f"VTK missing U/Cx/Cy: {vtk_path}")
   403	            U = np.asarray(cd["U"])
   404	            Cx = np.asarray(cd["Cx"])
   405	            Cy = np.asarray(cd["Cy"])
   406	            n = U.shape[0]
   407	            # LDC: 129×129 uniform → infer grid dim from n.
   408	            side = int(round(n ** 0.5))
   409	            if side * side != n:
   410	                raise RenderError(f"VTK cell count {n} not square grid")
   411	            # Sort by (y, x) to pack into (side, side) array.
   412	            order = np.lexsort((Cx, Cy))
   413	            Ux = U[order, 0].reshape(side, side)
   414	            Uy = U[order, 1].reshape(side, side)
   415	            x = Cx[order].reshape(side, side)
   416	            y = Cy[order].reshape(side, side)
   417	            mag = np.sqrt(Ux ** 2 + Uy ** 2)
   418	            # Normalize coords to y/L domain.
   419	            lid = max(float(y.max()), 1e-12)
   420	            xn = x / lid
   421	            yn = y / lid
   422	
   423	            # streamplot needs 1D evenly-spaced vectors. OpenFOAM VTK cell
   424	            # centers have tiny float-precision jitter; rebuild from bounds.
   425	            x_min, x_max = float(xn.min()), float(xn.max())
   426	            y_min, y_max = float(yn.min()), float(yn.max())
   427	            x1d = np.linspace(x_min, x_max, side)
   428	            y1d = np.linspace(y_min, y_max, side)
   429	            fig, ax = plt.subplots(figsize=(6.5, 6))
   430	            cf = ax.contourf(x1d, y1d, mag, levels=20, cmap="viridis")
   431	            ax.streamplot(x1d, y1d, Ux, Uy, density=1.1, color="white",
   432	                          linewidth=0.6, arrowsize=0.8)
   433	            ax.set_aspect("equal")
   434	            ax.set_xlabel("x / L")
   435	            ax.set_ylabel("y / L")
   436	            ax.set_title(
   437	                f"{case_id} — |U| contour + streamlines (Phase 7b polish)\n"
   438	                f"129×129 mesh, simpleFoam steady, Re=100"
   439	            )
   440	            cbar = fig.colorbar(cf, ax=ax, fraction=0.045, pad=0.04)
   441	            cbar.set_label("|U| / U_lid")
   442	            fig.savefig(out)
   443	            plt.close(fig)
   444	            return out
   445	        except Exception as e:  # noqa: BLE001 — fall back to MVP strip
   446	            print(f"[render] [WARN] VTK parse failed ({e}); falling back to centerline strip",
   447	                  file=sys.stderr)
   448	
   449	    # Fallback — Phase 7b MVP behavior (1D strip) if VTK parse fails.
   450	    latest = _latest_sample_iter(artifact_dir)
   451	    y_sim, u_sim = _load_sample_xy(latest / "uCenterline.xy")
   452	    y_norm = y_sim / max(y_sim.max(), 1e-12)
   453	    fig, ax = plt.subplots(figsize=(4, 6))
   454	    strip = np.tile(u_sim.reshape(-1, 1), (1, 20))
   455	    im = ax.imshow(
   456	        strip, aspect="auto", origin="lower",
   457	        extent=[0, 1, float(y_norm.min()), float(y_norm.max())],
   458	        cmap="RdBu_r", vmin=-1.0, vmax=1.0,
   459	    )
   460	    ax.set_xlabel("(tile axis)")
   461	    ax.set_ylabel("y / L")
   462	    ax.set_title(f"{case_id} — U_x centerline slice (VTK parse failed, MVP fallback)")
   463	    cbar = fig.colorbar(im, ax=ax, fraction=0.08, pad=0.04)
   464	    cbar.set_label("U_x / U_lid")
   465	    fig.savefig(out)
   466	    plt.close(fig)
   467	    return out
   468	
   469	
   470	# ---------------------------------------------------------------------------
   471	# Orchestration
   472	# ---------------------------------------------------------------------------
   473	
   474	
   475	def render_all(case_id: str, run_label: str = "audit_real_run") -> dict:
   476	    """Render all 7b MVP figures for a given case/run. Returns {name: path, ...}."""
   477	    if case_id not in RENDER_SUPPORTED_CASES:
   478	        raise RenderError(
   479	            f"case_id={case_id!r} not opted-in for Phase 7b rendering. "
   480	            f"Supported: {sorted(RENDER_SUPPORTED_CASES)}. "
   481	            f"Other cases unlock in Phase 7c Sprint-2."
   482	        )
   483	    timestamp = _resolve_run_timestamp(case_id, run_label)
   484	    artifact_dir = _artifact_dir(case_id, timestamp)
   485	    renders_dir = _renders_dir(case_id, timestamp)
   486	
   487	    outputs: dict[str, Path] = {}
   488	    renderers = [
   489	        ("profile_png", render_profile_png),
   490	        ("profile_plotly_json", render_profile_plotly_json),
   491	        ("residuals_png", render_residuals_png),
   492	        ("pointwise_deviation_png", render_pointwise_deviation_png),
   493	        ("contour_u_magnitude_png", render_contour_u_magnitude_png),
   494	    ]
   495	    errors: dict[str, str] = {}
   496	    for name, fn in renderers:
   497	        try:
   498	            outputs[name] = fn(case_id, artifact_dir, renders_dir)
   499	        except Exception as e:  # noqa: BLE001  — keep batch alive
   500	            errors[name] = f"{type(e).__name__}: {e}"

exec
/bin/zsh -lc "nl -ba docs/specs/audit_package_canonical_L4.md | sed -n '1,260p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba ui/backend/tests/test_grid_convergence_gci.py | sed -n '1,260p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
     1	# Audit Package Canonical JSON Spec — L4
     2	
     3	**Status:** Active (DEC-V61-033, 2026-04-21)
     4	**Supersedes:** `audit_package_canonical_L3.md` (DEC-V61-023, generated_at → build_fingerprint rename)
     5	**Superseded by:** *(none)*
     6	
     7	## Change from L3 → L4
     8	
     9	L4 adds a new optional top-level key `"phase7"` to the manifest dict. When
    10	present, the signed zip carries an extra tree under `phase7/` containing real
    11	post-processing artifacts from Phase 7a/7b/7c:
    12	
    13	- `phase7/comparison_report.pdf`      — 8-section CFD-vs-Gold HTML/PDF from Phase 7c
    14	- `phase7/renders/*.png`              — 2D U-magnitude contour + streamlines, profile overlay, pointwise deviation, residuals (Phase 7b)
    15	- `phase7/renders/*.plotly.json`      — interactive profile figure (Phase 7b)
    16	- `phase7/field_artifacts/VTK/*.vtk`  — raw OpenFOAM volume + boundary VTK (Phase 7a)
    17	- `phase7/field_artifacts/sample/{iter}/*.xy`  — sampled centerline profiles per iteration (Phase 7a)
    18	- `phase7/field_artifacts/residuals.csv`       — parsed residual convergence history (Phase 7a)
    19	- `phase7/field_artifacts/residuals/0/residuals.dat` — raw OpenFOAM residuals function-object output
    20	- `phase7/field_artifacts/log.simpleFoam`      — full solver log
    21	
    22	## Manifest `phase7` schema
    23	
    24	```json
    25	{
    26	  "phase7": {
    27	    "schema_level": "L4",
    28	    "canonical_spec": "docs/specs/audit_package_canonical_L4.md",
    29	    "entries": [
    30	      {
    31	        "zip_path":         "phase7/comparison_report.pdf",
    32	        "disk_path_rel":    "reports/phase5_reports/lid_driven_cavity/20260421T082340Z/audit_real_run_comparison_report.pdf",
    33	        "sha256":           "945bba9d...",
    34	        "size_bytes":       622078
    35	      }
    36	    ],
    37	    "total_files": 14,
    38	    "total_bytes": 4740367
    39	  }
    40	}
    41	```
    42	
    43	**Rules:**
    44	
    45	- `entries` is sorted alphabetically by `zip_path`.
    46	- `zip_path` values all start with `phase7/`.
    47	- `sha256` is the full 64-hex-char hash of the file at `disk_path_rel`.
    48	- `disk_path_rel` is repo-relative POSIX style; always resolves under one of
    49	  `reports/phase5_fields/{case}/`, `reports/phase5_renders/{case}/`, or
    50	  `reports/phase5_reports/{case}/` — enforced in `_collect_phase7_artifacts`.
    51	- The key is **optional**. Audit packages built before Phase 7 produced any
    52	  artifacts, or with `include_phase7=False`, omit the key entirely.
    53	
    54	## Byte-reproducibility contract
    55	
    56	L4 preserves the L3 byte-reproducibility guarantee:
    57	
    58	- Two `build_audit_package` calls with the same `(case_id, run_id)` against
    59	  the same repo state produce byte-identical `bundle.zip` and therefore
    60	  identical HMAC signatures.
    61	- Enabled by: sorted zip entry order (`phase7/...` entries sort between
    62	  `manifest.json` and `decisions/*.txt`); epoch mtime on every entry
    63	  (1980-01-01 per `_fixed_zipinfo`); deterministic compression level.
    64	- `phase7` artifact file contents themselves are deterministic for a given
    65	  OpenFOAM run timestamp: the VTK/sample/residual files are frozen by the
    66	  driver at run time; re-rendering Phase 7b produces byte-identical PNGs
    67	  given fixed matplotlib rcParams; Phase 7c HTML is a pure function of
    68	  (gold, artifact bytes).
    69	
    70	**Live-verified 2026-04-21:** two consecutive `POST audit-package/build`
    71	calls for `lid_driven_cavity/audit_real_run` produced identical
    72	`bundle.zip` SHA256 (`39990076bfb634d0...`) and identical HMAC signatures
    73	(`a80a549c3d905908...`).
    74	
    75	## Security: manifest-path traversal defense
    76	
    77	The `phase7` section is built from on-disk state but every value flowing
    78	into `zip_path` / `disk_path_rel` is validated:
    79	
    80	1. **Timestamp gate**: `runs/{run_id}.json::timestamp` must match
    81	   `^\d{8}T\d{6}Z$` (`_PHASE7_TIMESTAMP_RE`). Tampered values (e.g.
    82	   `../../outside`, URL-encoded traversal) are rejected before any
    83	   filesystem composition.
    84	2. **Per-entry root containment**: each collected file's resolved path
    85	   must be inside one of the three Phase 7 roots or the entry is silently
    86	   dropped.
    87	3. **Serialize-time re-check**: `serialize._zip_entries_from_manifest`
    88	   re-resolves each `disk_path_rel` and verifies it's under `repo_root`
    89	   before reading bytes — a tampered manifest between build_manifest and
    90	   serialize_zip still can't exfiltrate outside-repo files.
    91	
    92	This mirrors the 7a and 7c path-traversal defenses established in
    93	DEC-V61-031 and DEC-V61-032.
    94	
    95	## Size characteristics
    96	
    97	For a typical LDC simpleFoam run at 129×129 mesh:
    98	
    99	| Component                          | Size   |
   100	|------------------------------------|--------|
   101	| `phase7/field_artifacts/VTK/*.vtk` | ~3.2 MB (volume + 45 KB boundary) |
   102	| `phase7/field_artifacts/log.simpleFoam` | ~490 KB |
   103	| `phase7/field_artifacts/sample/*/uCenterline.xy` (×3 iters) | ~27 KB |
   104	| `phase7/field_artifacts/residuals*.csv/.dat`     | ~100 KB |
   105	| `phase7/renders/*.png`             | ~290 KB (4 figures) |
   106	| `phase7/renders/*.plotly.json`     | ~12 KB |
   107	| `phase7/comparison_report.pdf`     | ~622 KB |
   108	| **L4 signed-zip total**            | **~1.97 MB** (was ~260 KB at L3) |
   109	
   110	Very large VTK blobs (> 50 MB) are skipped automatically to keep the zip
   111	from ballooning for high-resolution runs; the skipped file is not an error.
   112	
   113	## Backward compatibility
   114	
   115	L3 consumers (verifiers that don't know about `phase7`) continue to
   116	function — they see the new top-level key and JSON-lenient parsers ignore
   117	unknown keys. HMAC signature generation uses the canonical JSON over the
   118	full manifest dict including `phase7`, so signature matches require
   119	L4-aware re-building.
   120	
   121	## Reference implementation
   122	
   123	- Manifest builder: `src/audit_package/manifest.py::_collect_phase7_artifacts`
   124	- Zip serializer:   `src/audit_package/serialize.py::_zip_entries_from_manifest`
   125	- HMAC signing:     `src/audit_package/sign.py::sign` (unchanged from L3)
   126	- Tests:            `ui/backend/tests/test_audit_package_phase7e.py` (8 tests)
   127	
   128	## Related decisions
   129	
   130	- DEC-V61-023 — L3 `generated_at` → `build_fingerprint` rename
   131	- DEC-V61-031 — Phase 7a field capture (source of field_artifacts/)
   132	- DEC-V61-032 — Phase 7b/7c/7f render + report (source of renders/ + comparison_report.pdf)
   133	- DEC-V61-033 — Phase 7d + 7e — this spec

 succeeded in 0ms:
     1	"""Phase 7d — Richardson GCI unit tests."""
     2	from __future__ import annotations
     3	
     4	import math
     5	
     6	import pytest
     7	
     8	from ui.backend.services.grid_convergence import (
     9	    MeshSolution,
    10	    RichardsonGCI,
    11	    compute_richardson_gci,
    12	    compute_gci_from_fixtures,
    13	)
    14	
    15	
    16	def test_second_order_synthetic() -> None:
    17	    """Synthetic data: f_h = f_exact + C * h^2 (formal 2nd-order).
    18	    With finer meshes (errors << 1), we land in asymptotic range.
    19	    f_exact = 1.0, C = 0.001 (small correction).
    20	    """
    21	    import math as _m
    22	    def fh(h):
    23	        return 1.0 + 0.001 * h ** 2
    24	    coarse = MeshSolution("mesh_40", 40, fh(1 / 40))
    25	    medium = MeshSolution("mesh_80", 80, fh(1 / 80))
    26	    fine = MeshSolution("mesh_160", 160, fh(1 / 160))
    27	    gci = compute_richardson_gci(coarse, medium, fine)
    28	    assert gci.r_21 == pytest.approx(2.0)
    29	    assert gci.r_32 == pytest.approx(2.0)
    30	    assert gci.p_obs is not None
    31	    assert gci.p_obs == pytest.approx(2.0, abs=1e-4)
    32	    assert gci.f_extrapolated is not None
    33	    assert gci.f_extrapolated == pytest.approx(1.0, abs=1e-9)
    34	    assert gci.asymptotic_range_ok is True  # small errors → asymptotic
    35	
    36	
    37	def test_first_order_synthetic() -> None:
    38	    """f_h = 1.0 + 0.5 * h with h = 0.1, 0.05, 0.025 → p_obs = 1.0."""
    39	    coarse = MeshSolution("m10", 10, 1.0 + 0.5 * 0.1)
    40	    medium = MeshSolution("m20", 20, 1.0 + 0.5 * 0.05)
    41	    fine = MeshSolution("m40", 40, 1.0 + 0.5 * 0.025)
    42	    gci = compute_richardson_gci(coarse, medium, fine)
    43	    assert gci.p_obs == pytest.approx(1.0, abs=1e-6)
    44	
    45	
    46	def test_rejects_non_monotone_refinement() -> None:
    47	    coarse = MeshSolution("big", 40, 1.0)
    48	    medium = MeshSolution("small", 20, 1.1)
    49	    fine = MeshSolution("mid", 30, 1.05)
    50	    with pytest.raises(ValueError, match="not monotonically refined"):
    51	        compute_richardson_gci(coarse, medium, fine)
    52	
    53	
    54	def test_oscillating_convergence_note() -> None:
    55	    """When eps_21 and eps_32 have opposite signs, p_obs is undefined."""
    56	    coarse = MeshSolution("c", 10, 1.0)
    57	    medium = MeshSolution("m", 20, 1.5)  # +0.5
    58	    fine = MeshSolution("f", 40, 1.2)    # -0.3 (opposite direction)
    59	    gci = compute_richardson_gci(coarse, medium, fine)
    60	    assert gci.p_obs is None
    61	    assert "oscillating" in gci.note
    62	
    63	
    64	def test_converged_to_precision_note() -> None:
    65	    """When eps is below numerical precision, p_obs is undefined."""
    66	    coarse = MeshSolution("c", 10, 1.0)
    67	    medium = MeshSolution("m", 20, 1.0)
    68	    fine = MeshSolution("f", 40, 1.0)
    69	    gci = compute_richardson_gci(coarse, medium, fine)
    70	    assert gci.p_obs is None
    71	    assert "precision" in gci.note.lower() or "converged" in gci.note.lower()
    72	
    73	
    74	def test_ldc_fixtures_end_to_end() -> None:
    75	    """Against the real LDC mesh_N fixtures (40/80/160): expect sensible p_obs + GCI."""
    76	    gci = compute_gci_from_fixtures("lid_driven_cavity")
    77	    assert gci is not None
    78	    assert gci.p_obs is not None
    79	    assert 0.5 < gci.p_obs < 2.5, f"p_obs out of expected range: {gci.p_obs}"
    80	    assert gci.gci_32 is not None
    81	    # GCI should be in percent-range (not absurd).
    82	    assert 0 < gci.gci_32 < 1.0
    83	
    84	
    85	def test_returns_none_on_insufficient_fixtures(tmp_path) -> None:
    86	    """Graceful: if <3 mesh fixtures exist, returns None not raises."""
    87	    case_dir = tmp_path / "nonexistent_case"
    88	    case_dir.mkdir()
    89	    (case_dir / "mesh_40_measurement.yaml").write_text(
    90	        "measurement:\n  value: 1.0\n", encoding="utf-8",
    91	    )
    92	    result = compute_gci_from_fixtures("nonexistent_case", fixture_root=tmp_path)
    93	    assert result is None

exec
/bin/zsh -lc "nl -ba ui/backend/services/comparison_report.py | sed -n '250,460p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
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
   274	def _gci_to_template_dict(gci: Any) -> dict:
   275	    """Flatten a RichardsonGCI dataclass into a JSON-serializable dict for the template."""
   276	    return {
   277	        "coarse_label": gci.coarse.label,
   278	        "coarse_n": gci.coarse.n_cells_1d,
   279	        "coarse_value": gci.coarse.value,
   280	        "medium_label": gci.medium.label,
   281	        "medium_n": gci.medium.n_cells_1d,
   282	        "medium_value": gci.medium.value,
   283	        "fine_label": gci.fine.label,
   284	        "fine_n": gci.fine.n_cells_1d,
   285	        "fine_value": gci.fine.value,
   286	        "r_21": gci.r_21,
   287	        "r_32": gci.r_32,
   288	        "p_obs": gci.p_obs,
   289	        "f_extrapolated": gci.f_extrapolated,
   290	        "gci_21_pct": gci.gci_21 * 100 if gci.gci_21 is not None else None,
   291	        "gci_32_pct": gci.gci_32 * 100 if gci.gci_32 is not None else None,
   292	        "asymptotic_range_ok": gci.asymptotic_range_ok,
   293	        "note": gci.note,
   294	    }
   295	
   296	
   297	def _get_commit_sha() -> str:
   298	    try:
   299	        r = subprocess.run(
   300	            ["git", "rev-parse", "--short", "HEAD"],
   301	            capture_output=True, text=True, cwd=_REPO_ROOT, timeout=5,
   302	        )
   303	        return r.stdout.strip() or "unknown"
   304	    except (subprocess.SubprocessError, OSError):
   305	        return "unknown"
   306	
   307	
   308	# ---------------------------------------------------------------------------
   309	# Public API
   310	# ---------------------------------------------------------------------------
   311	
   312	
   313	def build_report_context(case_id: str, run_label: str = "audit_real_run") -> dict:
   314	    """Assemble all template variables. Raises ReportError on missing data."""
   315	    if case_id not in _REPORT_SUPPORTED_CASES:
   316	        raise ReportError(
   317	            f"case_id={case_id!r} not in Phase 7c MVP scope. "
   318	            f"Supported: {sorted(_REPORT_SUPPORTED_CASES)}."
   319	        )
   320	
   321	    run_manifest = _load_run_manifest(case_id, run_label)
   322	    timestamp = _validated_timestamp(run_manifest.get("timestamp"))
   323	    if timestamp is None:
   324	        raise ReportError(
   325	            f"invalid timestamp in run manifest for {case_id}/{run_label}"
   326	        )
   327	    artifact_dir = _FIELDS_ROOT / case_id / timestamp
   328	    # Containment: must be inside _FIELDS_ROOT/case_id/ even after .resolve().
   329	    try:
   330	        artifact_dir.resolve(strict=True).relative_to(
   331	            (_FIELDS_ROOT / case_id).resolve()
   332	        )
   333	    except (ValueError, OSError, FileNotFoundError):
   334	        raise ReportError(f"artifact dir escapes fields root: {artifact_dir}")
   335	    if not artifact_dir.is_dir():
   336	        raise ReportError(f"artifact dir missing: {artifact_dir}")
   337	
   338	    # Load + compute
   339	    gold_y, gold_u, gold_doc = _load_ldc_gold()
   340	    tolerance = float(gold_doc.get("tolerance", 0.05)) * 100.0  # fraction → percent
   341	    latest_sample = _latest_sample_iter(artifact_dir)
   342	    y_sim, u_sim = _load_sample_xy(latest_sample / "uCenterline.xy")
   343	    metrics = _compute_metrics(y_sim, u_sim, gold_y, gold_u, tolerance)
   344	
   345	    residual_info = _parse_residuals_csv(artifact_dir / "residuals.csv")
   346	    grid_conv_rows, grid_note = _load_grid_convergence(case_id, gold_y, gold_u)
   347	    # Phase 7d: Richardson extrapolation + GCI over the finest 3 meshes.
   348	    try:
   349	        from ui.backend.services.grid_convergence import compute_gci_from_fixtures
   350	        gci = compute_gci_from_fixtures(case_id, fixture_root=_FIXTURE_ROOT)
   351	    except (ValueError, ImportError):
   352	        gci = None
   353	
   354	    # Verdict logic: all-pass OR tolerance met.
   355	    is_all_pass = metrics["n_pass"] == metrics["n_total"] and metrics["n_total"] > 0
   356	    majority_pass = metrics["n_pass"] >= math.ceil(metrics["n_total"] * 0.6)
   357	    if is_all_pass:
   358	        verdict, verdict_gradient, subtitle = "PASS", "#059669 0%, #10b981 100%", (
   359	            f"全部 {metrics['n_total']} 个 gold 点在 ±{tolerance:.1f}% 容差内。"
   360	        )
   361	    elif majority_pass:
   362	        verdict, verdict_gradient, subtitle = "PARTIAL", "#d97706 0%, #f59e0b 100%", (
   363	            f"{metrics['n_pass']}/{metrics['n_total']} 点通过；"
   364	            f"{metrics['n_total'] - metrics['n_pass']} 点残差为已记录物理项 "
   365	            f"(见 DEC-V61-030 关于 Ghia 非均匀网格 vs 均匀网格的插值误差)。"
   366	        )
   367	    else:
   368	        verdict, verdict_gradient, subtitle = "FAIL", "#dc2626 0%, #ef4444 100%", (
   369	            f"仅 {metrics['n_pass']}/{metrics['n_total']} 点通过 — "
   370	            f"需要诊断 (solver, mesh, 或 gold 本身)。"
   371	        )
   372	
   373	    # Renders — use Phase 7b manifest if available; else None placeholders.
   374	    # Codex round 1 HIGH: every manifest-supplied output path is validated to
   375	    # resolve inside reports/phase5_renders/ before being emitted into HTML.
   376	    renders_manifest = _load_renders_manifest(case_id, run_label)
   377	    renders_dir = _RENDERS_ROOT / case_id / timestamp
   378	
   379	    def _rel(key: str, default: str = "") -> str:
   380	        candidate: Optional[str] = None
   381	        if renders_manifest:
   382	            raw = renders_manifest.get("outputs", {}).get(key)
   383	            if isinstance(raw, str):
   384	                validated = _safe_rel_under(raw, _RENDERS_ROOT)
   385	                if validated:
   386	                    candidate = validated
   387	        if candidate is None:
   388	            guess = renders_dir / default
   389	            if guess.is_file():
   390	                try:
   391	                    rel = str(guess.resolve().relative_to(_REPO_ROOT.resolve()))
   392	                    if _safe_rel_under(rel, _RENDERS_ROOT):
   393	                        candidate = rel
   394	                except ValueError:
   395	                    pass
   396	        return candidate or ""
   397	
   398	    renders = {
   399	        "profile_png_rel": _rel("profile_png", "profile_u_centerline.png"),
   400	        "pointwise_png_rel": _rel("pointwise_deviation_png", "pointwise_deviation.png"),
   401	        "contour_png_rel": _rel("contour_u_magnitude_png", "contour_u_magnitude.png"),
   402	        "residuals_png_rel": _rel("residuals_png", "residuals.png"),
   403	    }
   404	
   405	    paper = {
   406	        "title": gold_doc.get("source", "Ghia, Ghia & Shin 1982 — Lid-Driven Cavity benchmark"),
   407	        "source": "J. Comput. Phys. 47, 387-411 (1982), Table I Re=100 column",
   408	        "doi": gold_doc.get("literature_doi", "10.1016/0021-9991(82)90058-4"),
   409	        "short": "Ghia 1982",
   410	        "gold_count": metrics["n_total"],
   411	        "tolerance_pct": tolerance,
   412	    }
   413	
   414	    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
   415	
   416	    return {
   417	        "case_id": case_id,
   418	        "case_display_name": "Lid-Driven Cavity (Re=100)" if case_id == "lid_driven_cavity" else case_id,
   419	        "run_label": run_label,
   420	        "timestamp": timestamp,
   421	        "verdict": verdict,
   422	        "verdict_gradient": verdict_gradient,
   423	        "verdict_subtitle": subtitle,
   424	        "metrics": metrics,
   425	        "paper": paper,
   426	        "renders": renders,
   427	        "contour_caption": (
   428	            "2D |U| contour + streamlines 由 OpenFOAM VTK 体数据渲染（Phase 7b polish）。"
   429	            "白色流线显示 LDC Re=100 的主涡结构；黄色高 |U| 区沿 lid 剪切层分布。"
   430	        ),
   431	        "residual_info": residual_info,
   432	        "grid_conv": grid_conv_rows,
   433	        "grid_conv_note": grid_note,
   434	        "gci": _gci_to_template_dict(gci) if gci is not None else None,
   435	        "meta": {
   436	            "openfoam_version": "v10",
   437	            "solver": "simpleFoam (SIMPLE, laminar)",
   438	            "docker_image": "cfd-openfoam (local arm64 OpenFOAM v10)",
   439	            "commit_sha": _get_commit_sha(),
   440	            "mesh": "129×129 uniform",
   441	            "tolerance": f"±{tolerance:.1f}%",
   442	            "schemes": "steadyState + linearUpwind + Gauss linear corrected",
   443	            "report_generated_at": now,
   444	        },
   445	    }
   446	
   447	
   448	def render_report_html(case_id: str, run_label: str = "audit_real_run") -> str:
   449	    """Return the full HTML string for the comparison report."""
   450	    ctx = build_report_context(case_id, run_label)
   451	    tmpl = _env.get_template("comparison_report.html.j2")
   452	    return tmpl.render(**ctx)
   453	
   454	
   455	def render_report_pdf(case_id: str, run_label: str = "audit_real_run",
   456	                      output_path: Optional[Path] = None) -> Path:
   457	    """Render HTML to PDF via WeasyPrint and write to disk. Returns the file Path.
   458	
   459	    Asset resolution: WeasyPrint converts the HTML's relative img src paths.
   460	    We pass base_url=_REPO_ROOT so /reports/phase5_renders/... resolves correctly.

codex
I’ve narrowed the diff to the lines that can actually affect bundle bytes or safety. I’m checking two things now: real call sites/consumers for `build_manifest(include_phase7=True)` defaults, and whether any unchanged serializer/report code makes the new assumptions unsafe.
exec
/bin/zsh -lc "nl -ba ui/backend/tests/test_audit_package_phase7e.py | sed -n '200,340p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   200	
   201	
   202	def test_byte_reproducibility_with_phase7(tmp_path) -> None:
   203	    """Two consecutive build_manifest + serialize_zip_bytes calls with the
   204	    same Phase 7 artifacts must produce byte-identical zips."""
   205	    _setup_phase7_tree(tmp_path)
   206	    # Both calls use the same tmp_path repo_root.
   207	    m1 = build_manifest(
   208	        case_id="lid_driven_cavity", run_id="audit_real_run",
   209	        build_fingerprint="deadbeefdeadbeef",
   210	        repo_root=tmp_path,
   211	    )
   212	    m2 = build_manifest(
   213	        case_id="lid_driven_cavity", run_id="audit_real_run",
   214	        build_fingerprint="deadbeefdeadbeef",
   215	        repo_root=tmp_path,
   216	    )
   217	    # manifest dicts equal → canonical JSON equal.
   218	    assert m1 == m2
   219	    # phase7 SHA256s identical.
   220	    sha1 = [e["sha256"] for e in m1["phase7"]["entries"]]
   221	    sha2 = [e["sha256"] for e in m2["phase7"]["entries"]]
   222	    assert sha1 == sha2

exec
/bin/zsh -lc "find reports/phase5_fields -maxdepth 4 -type f | rg '/VTK/|runs/.+json|residuals|uCenterline|log\\.simpleFoam' | sed -n '1,200p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
reports/phase5_fields/lid_driven_cavity/20260421T082340Z/log.simpleFoam
reports/phase5_fields/lid_driven_cavity/20260421T082340Z/VTK/ldc_59058_1776759820768_1024.vtk
reports/phase5_fields/lid_driven_cavity/20260421T082340Z/residuals.csv
reports/phase5_fields/lid_driven_cavity/runs/audit_real_run.json

exec
/bin/zsh -lc "rg -n \"build_manifest\\(|serialize_zip_bytes\\(|phase7|include_phase7|audit-package/build|audit_package\" -S src ui | sed -n '1,260p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
src/audit_package/sign.py:32:1. The manifest dict (canonical JSON form from :mod:`audit_package.serialize`).
src/audit_package/sign.py:205:            "src/audit_package/sign.py module docstring for the rotation procedure."
ui/backend/services/field_artifacts.py:8:File-serve pattern mirrors ui/backend/routes/audit_package.py:284-342
src/audit_package/manifest.py:309:_PHASE7_TIMESTAMP_RE = _re.compile(r"^\d{8}T\d{6}Z$")
src/audit_package/manifest.py:320:def _collect_phase7_artifacts(
src/audit_package/manifest.py:336:    against _PHASE7_TIMESTAMP_RE (defense-in-depth against manifest tampering,
src/audit_package/manifest.py:381:            if isinstance(ts, str) and _PHASE7_TIMESTAMP_RE.match(ts):
src/audit_package/manifest.py:394:                        _add(p, f"phase7/field_artifacts/{rel}")
src/audit_package/manifest.py:405:            if isinstance(ts, str) and _PHASE7_TIMESTAMP_RE.match(ts):
src/audit_package/manifest.py:415:                        _add(p, f"phase7/renders/{rel}")
src/audit_package/manifest.py:427:            if isinstance(ts, str) and _PHASE7_TIMESTAMP_RE.match(ts):
src/audit_package/manifest.py:430:                    _add(pdf, "phase7/comparison_report.pdf")
src/audit_package/manifest.py:438:        "canonical_spec": "docs/specs/audit_package_canonical_L4.md",
src/audit_package/manifest.py:445:def build_manifest(
src/audit_package/manifest.py:457:    include_phase7: bool = True,
src/audit_package/manifest.py:575:    # Only attached when include_phase7=True AND artifacts exist for this run.
src/audit_package/manifest.py:576:    if include_phase7:
src/audit_package/manifest.py:577:        phase7 = _collect_phase7_artifacts(case_id, run_id, repo_root)
src/audit_package/manifest.py:578:        if phase7 is not None:
src/audit_package/manifest.py:579:            manifest["phase7"] = phase7
ui/backend/tests/test_audit_package_route.py:26:    """POST /api/cases/{id}/runs/{rid}/audit-package/build."""
ui/backend/tests/test_audit_package_route.py:29:        resp = client.post("/api/cases/duct_flow/runs/r1/audit-package/build")
ui/backend/tests/test_audit_package_route.py:47:        resp = client.post("/api/cases/duct_flow/runs/r1/audit-package/build")
ui/backend/tests/test_audit_package_route.py:53:        resp = client.post("/api/cases/duct_flow/runs/r1/audit-package/build")
ui/backend/tests/test_audit_package_route.py:59:        resp = client.post("/api/cases/duct_flow/runs/r1/audit-package/build")
ui/backend/tests/test_audit_package_route.py:78:        resp = client.post("/api/cases/duct_flow/runs/r1/audit-package/build")
ui/backend/tests/test_audit_package_route.py:94:        resp = client.post("/api/cases/nonexistent_case/runs/r1/audit-package/build")
ui/backend/tests/test_audit_package_route.py:108:        r1 = client.post("/api/cases/duct_flow/runs/r1/audit-package/build")
ui/backend/tests/test_audit_package_route.py:109:        r2 = client.post("/api/cases/duct_flow/runs/r1/audit-package/build")
ui/backend/tests/test_audit_package_route.py:124:        r1 = client.post("/api/cases/duct_flow/runs/r1/audit-package/build")
ui/backend/tests/test_audit_package_route.py:125:        r2 = client.post("/api/cases/duct_flow/runs/r2/audit-package/build")
ui/backend/tests/test_audit_package_route.py:131:        resp = client.post("/api/cases/duct_flow/runs/r1/audit-package/build")
ui/backend/tests/test_audit_package_route.py:141:        resp = client.post("/api/cases/duct_flow/runs/r1/audit-package/build")
ui/backend/tests/test_audit_package_route.py:206:        from src.audit_package import verify
ui/backend/tests/test_audit_package_route.py:208:        resp = client.post("/api/cases/duct_flow/runs/verify-test/audit-package/build")
ui/backend/tests/test_audit_package_route.py:223:        from src.audit_package import verify
ui/backend/tests/test_audit_package_route.py:225:        resp = client.post("/api/cases/duct_flow/runs/tamper-test/audit-package/build")
ui/backend/tests/test_audit_package_route.py:246:            "/api/cases/lid_driven_cavity/runs/audit_real_run/audit-package/build"
ui/backend/tests/test_audit_package_route.py:276:            "/api/cases/lid_driven_cavity/runs/no_such_run_xyz/audit-package/build"
ui/backend/schemas/audit_package.py:45:    """Returned by POST /cases/{id}/runs/{rid}/audit-package/build."""
src/audit_package/serialize.py:3:Given a manifest dict from :func:`src.audit_package.manifest.build_manifest`,
src/audit_package/serialize.py:142:    # the phase7 section. Each entry's file is read verbatim and SHA256 has
src/audit_package/serialize.py:146:    phase7 = manifest.get("phase7")
src/audit_package/serialize.py:147:    if isinstance(phase7, dict):
src/audit_package/serialize.py:150:        phase7_entries = phase7.get("entries") or []
src/audit_package/serialize.py:151:        for entry in phase7_entries:
src/audit_package/serialize.py:175:def serialize_zip_bytes(manifest: Dict[str, Any]) -> bytes:
src/audit_package/serialize.py:193:    output_path.write_bytes(serialize_zip_bytes(manifest))
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
ui/backend/routes/field_artifacts.py:6:Pattern mirrors ui/backend/routes/audit_package.py:284-342 (FileResponse +
ui/backend/main.py:32:        POST   /api/cases/{id}/runs/{rid}/audit-package/build
ui/backend/main.py:47:    audit_package,
ui/backend/main.py:67:        "See docs/product_thesis.md + .planning/phase5_audit_package_builder_kickoff.md."
ui/backend/main.py:89:app.include_router(audit_package.router, prefix="/api", tags=["audit-package"])
ui/backend/routes/audit_package.py:3:    POST /api/cases/{case_id}/runs/{run_id}/audit-package/build
ui/backend/routes/audit_package.py:17:  :func:`audit_package.get_hmac_secret_from_env`. In dev, the sample
ui/backend/routes/audit_package.py:44:from src.audit_package import (
ui/backend/routes/audit_package.py:56:from ui.backend.schemas.audit_package import (
ui/backend/routes/audit_package.py:68:# Staging dir is repo-local but gitignored (ui/backend/.audit_package_staging/).
ui/backend/routes/audit_package.py:71:_STAGING_ROOT = _REPO_ROOT / "ui" / "backend" / ".audit_package_staging"
ui/backend/routes/audit_package.py:140:    "/cases/{case_id}/runs/{run_id}/audit-package/build",
ui/backend/routes/audit_package.py:143:def build_audit_package(case_id: str, run_id: str) -> AuditPackageBuildResponse:
ui/backend/routes/audit_package.py:197:    manifest = build_manifest(
ui/backend/routes/audit_package.py:241:            "See src/audit_package/serialize.py for install instructions."
src/models.py:81:    # driver-authored `phase7a_timestamp` (and `phase7a_case_id`) so
ui/frontend/src/api/client.ts:21:import type { AuditPackageBuildResponse } from "@/types/audit_package";
ui/frontend/src/api/client.ts:109:      `/api/cases/${encodeURIComponent(caseId)}/runs/${encodeURIComponent(runId)}/audit-package/build`,
ui/frontend/src/pages/AuditPackagePage.tsx:24:import type { AuditPackageBuildResponse } from "@/types/audit_package";
ui/frontend/src/types/audit_package.ts:2:// Mirrors ui/backend/schemas/audit_package.py.
ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/runs/audit_real_run.json:5:  "artifact_dir_rel": "ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/20260421T000000Z"
ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/20260421T000000Z/uCenterline_U_p.xy:1:# raw-format sample output — Phase7a LDC stub fixture
ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/20260421T000000Z/VTK/lid_driven_cavity_2000.vtk:2:Phase7a LDC stub fixture -- DO NOT USE FOR SCIENCE
ui/backend/tests/test_audit_package_phase7e.py:4:- When Phase 7 artifacts exist, manifest.phase7 is populated and the signed
ui/backend/tests/test_audit_package_phase7e.py:5:  zip contains them at phase7/* paths with byte-identical content.
ui/backend/tests/test_audit_package_phase7e.py:6:- When Phase 7 artifacts are absent, manifest.phase7 is omitted; signed zip
ui/backend/tests/test_audit_package_phase7e.py:10:- Tampered Phase 7 manifest (invalid timestamp) → phase7 key absent, not 500.
ui/backend/tests/test_audit_package_phase7e.py:21:from src.audit_package.manifest import (
ui/backend/tests/test_audit_package_phase7e.py:22:    _PHASE7_TIMESTAMP_RE,
ui/backend/tests/test_audit_package_phase7e.py:23:    _collect_phase7_artifacts,
ui/backend/tests/test_audit_package_phase7e.py:26:from src.audit_package.serialize import (
ui/backend/tests/test_audit_package_phase7e.py:34:def _setup_phase7_tree(
ui/backend/tests/test_audit_package_phase7e.py:71:# ---------- _collect_phase7_artifacts unit tests ----------------------------
ui/backend/tests/test_audit_package_phase7e.py:73:def test_collect_phase7_happy_path(tmp_path) -> None:
ui/backend/tests/test_audit_package_phase7e.py:74:    _setup_phase7_tree(tmp_path)
ui/backend/tests/test_audit_package_phase7e.py:75:    phase7 = _collect_phase7_artifacts("lid_driven_cavity", "audit_real_run", tmp_path)
ui/backend/tests/test_audit_package_phase7e.py:76:    assert phase7 is not None
ui/backend/tests/test_audit_package_phase7e.py:77:    assert phase7["schema_level"] == "L4"
ui/backend/tests/test_audit_package_phase7e.py:78:    zip_paths = [e["zip_path"] for e in phase7["entries"]]
ui/backend/tests/test_audit_package_phase7e.py:82:    assert any(z.startswith("phase7/field_artifacts/") for z in zip_paths)
ui/backend/tests/test_audit_package_phase7e.py:83:    assert any(z.startswith("phase7/renders/") for z in zip_paths)
ui/backend/tests/test_audit_package_phase7e.py:84:    assert "phase7/comparison_report.pdf" in zip_paths
ui/backend/tests/test_audit_package_phase7e.py:86:    for e in phase7["entries"]:
ui/backend/tests/test_audit_package_phase7e.py:91:def test_collect_phase7_no_artifacts_returns_none(tmp_path) -> None:
ui/backend/tests/test_audit_package_phase7e.py:92:    result = _collect_phase7_artifacts("nonexistent_case", "nonexistent_run", tmp_path)
ui/backend/tests/test_audit_package_phase7e.py:96:def test_collect_phase7_rejects_tampered_timestamp(tmp_path) -> None:
ui/backend/tests/test_audit_package_phase7e.py:98:    _setup_phase7_tree(tmp_path)
ui/backend/tests/test_audit_package_phase7e.py:109:    phase7 = _collect_phase7_artifacts("lid_driven_cavity", "audit_real_run", tmp_path)
ui/backend/tests/test_audit_package_phase7e.py:110:    # Every entry (if any) must have zip_path under phase7/ — no leaks.
ui/backend/tests/test_audit_package_phase7e.py:111:    if phase7 is not None:
ui/backend/tests/test_audit_package_phase7e.py:112:        for e in phase7["entries"]:
ui/backend/tests/test_audit_package_phase7e.py:113:            assert e["zip_path"].startswith("phase7/"), e
ui/backend/tests/test_audit_package_phase7e.py:120:        assert _PHASE7_TIMESTAMP_RE.match(ok)
ui/backend/tests/test_audit_package_phase7e.py:123:        assert _PHASE7_TIMESTAMP_RE.match(bad) is None
ui/backend/tests/test_audit_package_phase7e.py:128:def test_build_manifest_embeds_phase7(tmp_path) -> None:
ui/backend/tests/test_audit_package_phase7e.py:129:    _setup_phase7_tree(tmp_path)
ui/backend/tests/test_audit_package_phase7e.py:130:    manifest = build_manifest(
ui/backend/tests/test_audit_package_phase7e.py:134:        include_phase7=True,
ui/backend/tests/test_audit_package_phase7e.py:136:    assert "phase7" in manifest
ui/backend/tests/test_audit_package_phase7e.py:137:    assert manifest["phase7"]["schema_level"] == "L4"
ui/backend/tests/test_audit_package_phase7e.py:140:def test_build_manifest_opt_out_phase7(tmp_path) -> None:
ui/backend/tests/test_audit_package_phase7e.py:141:    """Backward compat: include_phase7=False suppresses the key entirely."""
ui/backend/tests/test_audit_package_phase7e.py:142:    _setup_phase7_tree(tmp_path)
ui/backend/tests/test_audit_package_phase7e.py:143:    manifest = build_manifest(
ui/backend/tests/test_audit_package_phase7e.py:147:        include_phase7=False,
ui/backend/tests/test_audit_package_phase7e.py:149:    assert "phase7" not in manifest
ui/backend/tests/test_audit_package_phase7e.py:152:def test_zip_contains_phase7_entries(tmp_path, monkeypatch) -> None:
ui/backend/tests/test_audit_package_phase7e.py:153:    """serialize_zip must pick up phase7 entries and include them at the
ui/backend/tests/test_audit_package_phase7e.py:155:    _setup_phase7_tree(tmp_path)
ui/backend/tests/test_audit_package_phase7e.py:156:    manifest = build_manifest(
ui/backend/tests/test_audit_package_phase7e.py:164:    import src.audit_package.serialize as ser
ui/backend/tests/test_audit_package_phase7e.py:172:        phase7 = m.get("phase7")
ui/backend/tests/test_audit_package_phase7e.py:173:        if isinstance(phase7, dict):
ui/backend/tests/test_audit_package_phase7e.py:174:            for entry in phase7.get("entries") or []:
ui/backend/tests/test_audit_package_phase7e.py:187:    zip_bytes = ser.serialize_zip_bytes(manifest)
ui/backend/tests/test_audit_package_phase7e.py:192:        phase7_names = [n for n in names if n.startswith("phase7/")]
ui/backend/tests/test_audit_package_phase7e.py:193:        assert len(phase7_names) >= 3  # at least PDF + 1 render + 1 field artifact
ui/backend/tests/test_audit_package_phase7e.py:194:        assert "phase7/comparison_report.pdf" in names
ui/backend/tests/test_audit_package_phase7e.py:196:        pdf_bytes = zf.read("phase7/comparison_report.pdf")
ui/backend/tests/test_audit_package_phase7e.py:202:def test_byte_reproducibility_with_phase7(tmp_path) -> None:
ui/backend/tests/test_audit_package_phase7e.py:205:    _setup_phase7_tree(tmp_path)
ui/backend/tests/test_audit_package_phase7e.py:207:    m1 = build_manifest(
ui/backend/tests/test_audit_package_phase7e.py:212:    m2 = build_manifest(
ui/backend/tests/test_audit_package_phase7e.py:219:    # phase7 SHA256s identical.
ui/backend/tests/test_audit_package_phase7e.py:220:    sha1 = [e["sha256"] for e in m1["phase7"]["entries"]]
ui/backend/tests/test_audit_package_phase7e.py:221:    sha2 = [e["sha256"] for e in m2["phase7"]["entries"]]
ui/backend/tests/test_field_artifacts_route.py:4:ui/backend/tests/fixtures/phase7a_sample_fields/ via
ui/backend/tests/test_field_artifacts_route.py:18:_FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "phase7a_sample_fields"

exec
/bin/zsh -lc "find reports/phase5_reports -maxdepth 4 -type f | sed -n '1,120p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
reports/phase5_reports/lid_driven_cavity/20260421T082340Z/audit_real_run_comparison_report.pdf

exec
/bin/zsh -lc "find reports/phase5_renders -maxdepth 4 -type f | sed -n '1,120p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
reports/phase5_renders/lid_driven_cavity/20260421T082340Z/profile_u_centerline.png
reports/phase5_renders/lid_driven_cavity/20260421T082340Z/pointwise_deviation.png
reports/phase5_renders/lid_driven_cavity/20260421T082340Z/residuals.png
reports/phase5_renders/lid_driven_cavity/20260421T082340Z/profile_u_centerline.plotly.json
reports/phase5_renders/lid_driven_cavity/20260421T082340Z/contour_u_magnitude.png
reports/phase5_renders/lid_driven_cavity/runs/audit_real_run.json

exec
/bin/zsh -lc "nl -ba ui/backend/tests/test_audit_package_route.py | sed -n '230,320p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba ui/backend/routes/audit_package.py | sed -n '180,240p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   230	
   231	        # Flip one byte in zip → verify must fail
   232	        tampered = bytes([zip_bytes[0] ^ 1]) + zip_bytes[1:]
   233	        key = b"route-test-dev-secret"
   234	        assert verify(manifest, tampered, sig_text, key) is False
   235	
   236	
   237	class TestAuditRealRunWiring:
   238	    """Phase 5a: real-solver fixture data wires into the signed manifest."""
   239	
   240	    def test_audit_real_run_populates_measurement(self, client):
   241	        """When run_id=audit_real_run, the manifest carries real solver data,
   242	        not a skeleton."""
   243	        import json
   244	
   245	        resp = client.post(
   246	            "/api/cases/lid_driven_cavity/runs/audit_real_run/audit-package/build"
   247	        )
   248	        assert resp.status_code == 200
   249	        bid = resp.json()["bundle_id"]
   250	        manifest = json.loads(
   251	            client.get(f"/api/audit-packages/{bid}/manifest.json").content
   252	        )
   253	        # measurement section must be populated from the audit fixture
   254	        m = manifest.get("measurement", {})
   255	        assert m.get("comparator_verdict") in {"PASS", "FAIL"}, (
   256	            f"audit_real_run must land a verdict; got {m.get('comparator_verdict')!r}"
   257	        )
   258	        kq = m.get("key_quantities", {})
   259	        assert "value" in kq, "measurement.key_quantities missing 'value'"
   260	        assert "quantity" in kq, "measurement.key_quantities missing 'quantity'"
   261	        assert kq.get("solver_success") is True, (
   262	            "real-solver fixture should report solver_success=True"
   263	        )
   264	        # audit_concerns must flow through
   265	        concerns = m.get("audit_concerns", [])
   266	        assert concerns, "audit_real_run should surface audit_concerns"
   267	        concern_types = {c.get("concern_type") for c in concerns}
   268	        assert "CONTRACT_STATUS" in concern_types
   269	
   270	    def test_unknown_run_id_still_builds_with_empty_measurement(self, client):
   271	        """Back-compat: non-audit run_ids still produce a valid (signed) bundle
   272	        with an empty measurement section — old behavior preserved."""
   273	        import json
   274	
   275	        resp = client.post(
   276	            "/api/cases/lid_driven_cavity/runs/no_such_run_xyz/audit-package/build"
   277	        )
   278	        assert resp.status_code == 200
   279	        bid = resp.json()["bundle_id"]
   280	        manifest = json.loads(
   281	            client.get(f"/api/audit-packages/{bid}/manifest.json").content
   282	        )
   283	        m = manifest.get("measurement", {})
   284	        assert m.get("key_quantities") == {}, (
   285	            "skeleton manifest should have empty key_quantities"
   286	        )
   287	        assert m.get("comparator_verdict") is None

 succeeded in 0ms:
   180	        f"{case_id}|{run_id}".encode("utf-8")
   181	    ).hexdigest()[:16]
   182	
   183	    # Wire audit-real-run fixture data into the manifest when available.
   184	    # Phase 5a: when run_id identifies an audit_real_run measurement (captured
   185	    # by scripts/phase5_audit_run.py), pull its measurement + verdict +
   186	    # audit_concerns into the manifest so the signed bundle reflects the
   187	    # actual solver output rather than a skeleton.
   188	    run_doc = _load_run_measurement(case_id, run_id) or {}
   189	    measurement_doc = run_doc.get("measurement") or None
   190	    audit_concerns_doc = run_doc.get("audit_concerns") or None
   191	    comparator_verdict_doc: str | None = None
   192	    if measurement_doc is not None:
   193	        comparator_verdict_doc = (
   194	            "PASS" if measurement_doc.get("comparator_passed") else "FAIL"
   195	        )
   196	
   197	    manifest = build_manifest(
   198	        case_id=case_id,
   199	        run_id=run_id,
   200	        build_fingerprint=build_fingerprint,
   201	        measurement=measurement_doc,
   202	        comparator_verdict=comparator_verdict_doc,
   203	        audit_concerns=audit_concerns_doc,
   204	    )
   205	
   206	    # Stage.
   207	    bundle_id = uuid.uuid4().hex
   208	    bundle_dir = _STAGING_ROOT / bundle_id
   209	    bundle_dir.mkdir(parents=True, exist_ok=True)
   210	
   211	    zip_path = bundle_dir / "bundle.zip"
   212	    html_path = bundle_dir / "bundle.html"
   213	    pdf_path = bundle_dir / "bundle.pdf"
   214	    sig_path = bundle_dir / "bundle.sig"
   215	    manifest_path = bundle_dir / "manifest.json"
   216	
   217	    # Serialize zip + HTML (mandatory).
   218	    serialize_zip(manifest, zip_path)
   219	    html_path.write_text(render_html(manifest), encoding="utf-8")
   220	
   221	    # Persist a standalone manifest.json (the zip also has it; this is
   222	    # a convenience for reviewers who just want the JSON).
   223	    import json as _json
   224	    manifest_path.write_text(
   225	        _json.dumps(manifest, sort_keys=True, ensure_ascii=False, indent=2) + "\n",
   226	        encoding="utf-8",
   227	    )
   228	
   229	    # Serialize PDF (optional — depends on weasyprint native libs).
   230	    pdf_available = False
   231	    pdf_error: str | None = None
   232	    if is_pdf_backend_available():
   233	        try:
   234	            serialize_pdf(manifest, pdf_path)
   235	            pdf_available = True
   236	        except PdfBackendUnavailable as e:
   237	            pdf_error = str(e)
   238	    else:
   239	        pdf_error = (
   240	            "weasyprint native libs unavailable on this host. "

exec
/bin/zsh -lc "rg -n \"VTK|writeVTK|foamToVTK|_find_latest_vtk|artifact_dir_rel|phase7a_timestamp|residuals.csv\" src ui scripts -S | sed -n '1,260p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
ui/backend/services/field_artifacts.py:90:        # residuals.csv (or anything with 'residual' in the name) is a residual_log.
ui/backend/services/field_artifacts.py:91:        if low == "residuals.csv" or "residual" in low:
src/foam_agent_adapter.py:599:            # 7.5. [Phase 7a] Stage field artifacts (VTK + sample CSV + residuals)
src/foam_agent_adapter.py:607:                _phase7a_ts = _md.get("phase7a_timestamp")
src/foam_agent_adapter.py:6876:    # Phase 7a — field-artifact staging (VTK + sample CSV + residuals)
src/foam_agent_adapter.py:6890:        Mirrors _copy_postprocess_fields. Runs foamToVTK inside the container,
src/foam_agent_adapter.py:6891:        then uses docker `get_archive` to pull VTK/, postProcessing/sample/,
src/foam_agent_adapter.py:6908:            # (a) foamToVTK — -allPatches merges patches into a single file.
src/foam_agent_adapter.py:6912:                "foamToVTK -latestTime -noZero -allPatches",
src/foam_agent_adapter.py:6918:                    f"[WARN] foamToVTK -allPatches failed, retrying without: {log[:200]}",
src/foam_agent_adapter.py:6922:                    "foamToVTK -latestTime -noZero", case_cont_dir, 120,
src/foam_agent_adapter.py:6926:                    f"[WARN] foamToVTK failed, field capture skipped: {log[:200]}",
src/foam_agent_adapter.py:6934:            for sub in ("VTK", "postProcessing/sample", "postProcessing/residuals"):
src/foam_agent_adapter.py:6963:            # (d) Derive residuals.csv from residuals/0/residuals.dat if present.
src/foam_agent_adapter.py:6973:                    self._emit_residuals_csv(
src/foam_agent_adapter.py:6975:                        artifact_dir / "residuals.csv",
src/foam_agent_adapter.py:6979:                        f"[WARN] residuals.csv derivation failed: {e!r}",
src/foam_agent_adapter.py:6991:    def _emit_residuals_csv(dat_path: Path, csv_path: Path) -> None:
ui/backend/services/comparison_report.py:198:def _parse_residuals_csv(path: Path) -> dict[str, Any]:
ui/backend/services/comparison_report.py:345:    residual_info = _parse_residuals_csv(artifact_dir / "residuals.csv")
ui/backend/services/comparison_report.py:428:            "2D |U| contour + streamlines 由 OpenFOAM VTK 体数据渲染（Phase 7b polish）。"
scripts/render_case_report.py:21:No PyVista / no VTK parser needed for MVP — uses the sample CSV directly.
scripts/render_case_report.py:139:def _load_residuals_csv(path: Path) -> tuple[np.ndarray, dict[str, np.ndarray]]:
scripts/render_case_report.py:140:    """Load residuals.csv written by _capture_field_artifacts.
scripts/render_case_report.py:301:    csv = artifact_dir / "residuals.csv"
scripts/render_case_report.py:303:        raise RenderError(f"residuals.csv missing: {csv}")
scripts/render_case_report.py:304:    iters, fields = _load_residuals_csv(csv)
scripts/render_case_report.py:367:def _find_latest_vtk(artifact_dir: Path) -> Optional[Path]:
scripts/render_case_report.py:368:    """Return the highest-iteration VTK volume file (not the allPatches one)."""
scripts/render_case_report.py:369:    vtk_root = artifact_dir / "VTK"
scripts/render_case_report.py:372:    # Volume VTK files are at VTK/*.vtk (direct children); boundary data is under VTK/allPatches/.
scripts/render_case_report.py:384:    """2D U-magnitude contour + streamlines from the real VTK volume (Phase 7b polish).
scripts/render_case_report.py:386:    Phase 7b polish (2026-04-21): parse the actual OpenFOAM volume VTK via PyVista,
scripts/render_case_report.py:390:    Fallback to the old 1D centerline strip if PyVista/VTK parsing fails.
scripts/render_case_report.py:393:    vtk_path = _find_latest_vtk(artifact_dir)
scripts/render_case_report.py:402:                raise RenderError(f"VTK missing U/Cx/Cy: {vtk_path}")
scripts/render_case_report.py:410:                raise RenderError(f"VTK cell count {n} not square grid")
scripts/render_case_report.py:423:            # streamplot needs 1D evenly-spaced vectors. OpenFOAM VTK cell
scripts/render_case_report.py:446:            print(f"[render] [WARN] VTK parse failed ({e}); falling back to centerline strip",
scripts/render_case_report.py:449:    # Fallback — Phase 7b MVP behavior (1D strip) if VTK parse fails.
scripts/render_case_report.py:462:    ax.set_title(f"{case_id} — U_x centerline slice (VTK parse failed, MVP fallback)")
scripts/phase5_audit_run.py:94:def _phase7a_timestamp() -> str:
scripts/phase5_audit_run.py:107:    set — an empty directory from a failed foamToVTK must not produce a
scripts/phase5_audit_run.py:117:    # Count usable leaf files (foamToVTK output, samples, residuals).
scripts/phase5_audit_run.py:132:        "artifact_dir_rel": str(artifact_dir.relative_to(REPO_ROOT)),
scripts/phase5_audit_run.py:280:    ts = _phase7a_timestamp()
scripts/phase5_audit_run.py:286:            spec.metadata["phase7a_timestamp"] = ts
ui/backend/tests/test_comparison_report_route.py:105:    (fields_root / case / ts / "residuals.csv").write_text(
ui/backend/tests/test_field_artifacts_route.py:95:def test_download_residuals_csv_200(client: TestClient) -> None:
ui/backend/tests/test_field_artifacts_route.py:96:    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts/residuals.csv")
ui/backend/tests/test_field_artifacts_route.py:99:    fixture = _FIXTURE_ROOT / "lid_driven_cavity" / "20260421T000000Z" / "residuals.csv"
ui/backend/tests/test_field_artifacts_route.py:104:    """VTK file lives at VTK/lid_driven_cavity_2000.vtk — subpath URL (Codex round 1 HIGH #1)."""
ui/backend/tests/test_field_artifacts_route.py:105:    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts/VTK/lid_driven_cavity_2000.vtk")
ui/backend/tests/test_field_artifacts_route.py:116:    r = client.get("/api/runs/..__pwn/field-artifacts/residuals.csv")
ui/backend/tests/test_field_artifacts_route.py:122:    r = client.get("/api/runs/%2e%2e__pwn/field-artifacts/residuals.csv")
ui/backend/tests/test_field_artifacts_route.py:134:    subdir-nested files don't collide on basename. The fixture VTK lives in
ui/backend/tests/test_field_artifacts_route.py:135:    a VTK/ subdir; its filename in the manifest must include that subpath."""
ui/backend/tests/test_field_artifacts_route.py:139:    assert "VTK/lid_driven_cavity_2000.vtk" in vtk_names, vtk_names
ui/backend/tests/test_field_artifacts_route.py:172:    (case_dir / "residuals.csv").write_text("Time,Ux\n1,0.5\n", encoding="utf-8")
ui/backend/tests/test_field_artifacts_route.py:189:        assert "residuals.csv" in names, names
src/models.py:81:    # driver-authored `phase7a_timestamp` (and `phase7a_case_id`) so
ui/backend/tests/test_audit_package_phase7e.py:47:    (fields / timestamp / "residuals.csv").write_text(
ui/backend/tests/test_comparison_report_service.py:33:    (case_fields / "residuals.csv").write_text(
src/audit_package/manifest.py:372:    # Phase 7a — field artifacts (VTK + sample + residuals).
ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/runs/audit_real_run.json:5:  "artifact_dir_rel": "ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/20260421T000000Z"
ui/backend/schemas/validation.py:209:- vtk: OpenFOAM foamToVTK output (binary, ~1 MB/case for 129x129 LDC)
ui/backend/schemas/validation.py:212:- residual_log: residuals.csv (derived from OpenFOAM `residuals` function
ui/backend/tests/fixtures/runs/lid_driven_cavity/field_artifacts_manifest.yaml:12:  - filename: residuals.csv

exec
/bin/zsh -lc "python - <<'PY'
from pathlib import Path
import io, zipfile, hashlib
from src.audit_package.manifest import build_manifest
from src.audit_package.serialize import serialize_zip_bytes
m = build_manifest(case_id='lid_driven_cavity', run_id='audit_real_run', repo_root=Path('.').resolve(), build_fingerprint='fixed')
zb = serialize_zip_bytes(m)
print('zip len', len(zb), 'sha256', hashlib.sha256(zb).hexdigest())
with zipfile.ZipFile(io.BytesIO(zb)) as zf:
    names = zf.namelist()
    print('phase7 count', len([n for n in names if n.startswith('phase7/')]))
    print('\\n'.join(names[:40]))
PY" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "python - <<'PY'
from pathlib import Path
from src.audit_package.manifest import _collect_phase7_artifacts
phase7 = _collect_phase7_artifacts('lid_driven_cavity','audit_real_run',Path('.').resolve())
print('phase7 present:', phase7 is not None)
if phase7:
    print('total_files', phase7['total_files'])
    print('total_bytes', phase7['total_bytes'])
    for e in phase7['entries']:
        print(e['zip_path'], e['disk_path_rel'], e['size_bytes'])
PY" in /Users/Zhuanz/Desktop/cfd-harness-unified
 exited 127 in 0ms:
zsh:1: command not found: python

 exited 127 in 0ms:
zsh:1: command not found: python

codex
The local tree shows the real LDC Phase 7 artifacts, which lets me validate assumptions against the actual file layout instead of only fixtures. I also found the route still calls `build_manifest()` with the new default, so consumer-compatibility has to be judged against live route behavior, not just unit tests.
exec
/bin/zsh -lc "nl -ba src/foam_agent_adapter.py | sed -n '6880,6965p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
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

exec
/bin/zsh -lc "python3 - <<'PY'
from pathlib import Path
from src.audit_package.manifest import _collect_phase7_artifacts
phase7 = _collect_phase7_artifacts('lid_driven_cavity','audit_real_run',Path('.').resolve())
print('phase7 present:', phase7 is not None)
if phase7:
    print('total_files', phase7['total_files'])
    print('total_bytes', phase7['total_bytes'])
    for e in phase7['entries']:
        print(e['zip_path'], e['disk_path_rel'], e['size_bytes'])
PY" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
phase7 present: True
total_files 14
total_bytes 4740367
phase7/comparison_report.pdf reports/phase5_reports/lid_driven_cavity/20260421T082340Z/audit_real_run_comparison_report.pdf 622078
phase7/field_artifacts/VTK/allPatches/allPatches_1024.vtk reports/phase5_fields/lid_driven_cavity/20260421T082340Z/VTK/allPatches/allPatches_1024.vtk 45784
phase7/field_artifacts/VTK/ldc_59058_1776759820768_1024.vtk reports/phase5_fields/lid_driven_cavity/20260421T082340Z/VTK/ldc_59058_1776759820768_1024.vtk 3155888
phase7/field_artifacts/log.simpleFoam reports/phase5_fields/lid_driven_cavity/20260421T082340Z/log.simpleFoam 490559
phase7/field_artifacts/residuals.csv reports/phase5_fields/lid_driven_cavity/20260421T082340Z/residuals.csv 43972
phase7/field_artifacts/residuals/0/residuals.dat reports/phase5_fields/lid_driven_cavity/20260421T082340Z/residuals/0/residuals.dat 55394
phase7/field_artifacts/sample/0/uCenterline.xy reports/phase5_fields/lid_driven_cavity/20260421T082340Z/sample/0/uCenterline.xy 9099
phase7/field_artifacts/sample/1000/uCenterline.xy reports/phase5_fields/lid_driven_cavity/20260421T082340Z/sample/1000/uCenterline.xy 9099
phase7/field_artifacts/sample/500/uCenterline.xy reports/phase5_fields/lid_driven_cavity/20260421T082340Z/sample/500/uCenterline.xy 9099
phase7/renders/contour_u_magnitude.png reports/phase5_renders/lid_driven_cavity/20260421T082340Z/contour_u_magnitude.png 156127
phase7/renders/pointwise_deviation.png reports/phase5_renders/lid_driven_cavity/20260421T082340Z/pointwise_deviation.png 35549
phase7/renders/profile_u_centerline.plotly.json reports/phase5_renders/lid_driven_cavity/20260421T082340Z/profile_u_centerline.plotly.json 12154
phase7/renders/profile_u_centerline.png reports/phase5_renders/lid_driven_cavity/20260421T082340Z/profile_u_centerline.png 43949
phase7/renders/residuals.png reports/phase5_renders/lid_driven_cavity/20260421T082340Z/residuals.png 51616

exec
/bin/zsh -lc "python3 - <<'PY'
from pathlib import Path
import io, zipfile, hashlib
from src.audit_package.manifest import build_manifest
from src.audit_package.serialize import serialize_zip_bytes
m = build_manifest(case_id='lid_driven_cavity', run_id='audit_real_run', repo_root=Path('.').resolve(), build_fingerprint='fixed')
zb = serialize_zip_bytes(m)
print('zip len', len(zb), 'sha256', hashlib.sha256(zb).hexdigest())
with zipfile.ZipFile(io.BytesIO(zb)) as zf:
    names = zf.namelist()
    print('phase7 count', len([n for n in names if n.startswith('phase7/')]))
    for n in names:
        if n.startswith('phase7/'):
            print(n)
PY" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc 'PYTHONPATH=. .venv/bin/pytest ui/backend/tests/test_grid_convergence_gci.py ui/backend/tests/test_audit_package_phase7e.py ui/backend/tests/test_audit_package_route.py -q' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 291ms:
zip len 1978453 sha256 f53717c0dd1b62cb4f4c6b0eaac8af37b74ac2d4275172958dc98b5e448760aa
phase7 count 14
phase7/comparison_report.pdf
phase7/field_artifacts/VTK/allPatches/allPatches_1024.vtk
phase7/field_artifacts/VTK/ldc_59058_1776759820768_1024.vtk
phase7/field_artifacts/log.simpleFoam
phase7/field_artifacts/residuals.csv
phase7/field_artifacts/residuals/0/residuals.dat
phase7/field_artifacts/sample/0/uCenterline.xy
phase7/field_artifacts/sample/1000/uCenterline.xy
phase7/field_artifacts/sample/500/uCenterline.xy
phase7/renders/contour_u_magnitude.png
phase7/renders/pointwise_deviation.png
phase7/renders/profile_u_centerline.plotly.json
phase7/renders/profile_u_centerline.png
phase7/renders/residuals.png

 succeeded in 3032ms:
============================= test session starts ==============================
platform darwin -- Python 3.12.13, pytest-9.0.3, pluggy-1.6.0
rootdir: /Users/Zhuanz/Desktop/cfd-harness-unified
configfile: pyproject.toml
plugins: mock-3.15.1, cov-7.1.0, anyio-4.13.0
collected 35 items

ui/backend/tests/test_grid_convergence_gci.py .......                    [ 20%]
ui/backend/tests/test_audit_package_phase7e.py ........                  [ 42%]
ui/backend/tests/test_audit_package_route.py ....................        [100%]

============================== 35 passed in 2.74s ==============================

codex
The targeted tests are running clean so far, which narrows this to review findings rather than an obvious red failure. I’m finishing the route-level audit now, because the risky defects here are the ones tests can miss: incorrect “latest VTK” selection, spec drift, or a manifest/zip mismatch under edge conditions.
exec
/bin/zsh -lc "python3 - <<'PY'
from ui.backend.services.grid_convergence import MeshSolution, compute_richardson_gci

def fh(n,p=2,C=0.1,exact=1.0):
    h=1/n
    return exact + C*h**p
for triple in [(30,50,100),(20,50,160),(40,80,160),(33,67,133)]:
    c,m,f=triple
    g=compute_richardson_gci(MeshSolution('c',c,fh(c)), MeshSolution('m',m,fh(m)), MeshSolution('f',f,fh(f)))
    print(triple, 'r', g.r_21, g.r_32, 'p', g.p_obs, 'gci21', g.gci_21, 'gci32', g.gci_32, 'note', g.note)
PY" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "python3 - <<'PY'
from ui.backend.services.grid_convergence import MeshSolution, compute_richardson_gci
# try a family of nonuniform same-sign cases for convergence stability
for c,m,f in [(10,14,20),(10,15,31),(10,16,50),(11,17,29),(10,12,13)]:
    try:
        def fh(n):
            return 1+0.3*(1/n)**1.7
        g=compute_richardson_gci(MeshSolution('c',c,fh(c)),MeshSolution('m',m,fh(m)),MeshSolution('f',f,fh(f)))
        print((c,m,f),'r',round(g.r_21,4),round(g.r_32,4),'p',g.p_obs,'note',g.note)
    except Exception as e:
        print((c,m,f),'ERR',type(e).__name__,e)
PY" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "python3 - <<'PY'
from ui.backend.services.grid_convergence import MeshSolution, compute_richardson_gci
# denominator zero-ish / zero-value scenarios
cases=[
    (MeshSolution('c',10,1.0),MeshSolution('m',20,0.0),MeshSolution('f',40,0.1)),
    (MeshSolution('c',10,1.0),MeshSolution('m',20,0.5),MeshSolution('f',40,0.0)),
    (MeshSolution('c',10,0.0),MeshSolution('m',20,0.1),MeshSolution('f',40,0.2)),
]
for i,(c,m,f) in enumerate(cases,1):
    g=compute_richardson_gci(c,m,f)
    print('case',i,'p',g.p_obs,'e21',g.e_21,'e32',g.e_32,'g21',g.gci_21,'g32',g.gci_32,'asym',g.asymptotic_range_ok,'note',g.note)
PY" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
(30, 50, 100) r 1.6666666666666667 2.0 p 2.965848942781002 gci21 2.5041190141960844e-05 gci32 5.504249206133181e-06 note ok
(20, 50, 160) r 2.5 3.2 p 2.6961645595974675 gci21 2.4241708067725252e-05 gci32 2.049590595084792e-06 note ok
(40, 80, 160) r 2.0 2.0 p 1.9999999999794982 gci21 1.9530944829357853e-05 gci32 4.882793426750269e-06 note ok
(33, 67, 133) r 2.0303030303030303 1.9850746268656716 p 2.0534779501665987 gci21 2.6495000701000994e-05 gci32 6.729683206646405e-06 note ok

 succeeded in 0ms:
case 1 p None e21 inf e32 1.0 g21 None g32 None asym None note oscillating convergence (sign flip between refinement stages) — Richardson formula does not directly apply; p_obs omitted
case 2 p 0.0 e21 1.0 e32 inf g21 None g32 None asym None note ok
case 3 p 0.0 e21 1.0 e32 0.5 g21 None g32 None asym None note ok

 succeeded in 0ms:
(10, 14, 20) r 1.4 1.4286 p 1.5266929115293222 note ok
(10, 15, 31) r 1.5 2.0667 p 5.204827623882957 note ok
(10, 16, 50) ERR OverflowError (34, 'Result too large')
(11, 17, 29) r 1.5455 1.7059 p 2.152547193755249 note ok
(10, 12, 13) r 1.2 1.0833 p 0.964605667812544 note ok

exec
/bin/zsh -lc "python3 - <<'PY'
from pathlib import Path
import hashlib
from src.audit_package.manifest import build_manifest
from src.audit_package.serialize import serialize_zip_bytes
root = Path('.').resolve()
for i in (1,2):
    m = build_manifest(case_id='lid_driven_cavity', run_id='audit_real_run', repo_root=root, build_fingerprint='fixed')
    z = serialize_zip_bytes(m)
    print(i, hashlib.sha256(z).hexdigest())
PY" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 528ms:
1 61427be3048dcd3e758880a5ebc7068411a24ab9db31368fb558fc4f4a85e9c2
2 61427be3048dcd3e758880a5ebc7068411a24ab9db31368fb558fc4f4a85e9c2

exec
/bin/zsh -lc 'rg -n "_REPORT_SUPPORTED_CASES|RENDER_SUPPORTED_CASES" ui/backend/services/comparison_report.py scripts/render_case_report.py' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
scripts/render_case_report.py:65:RENDER_SUPPORTED_CASES = frozenset({"lid_driven_cavity"})
scripts/render_case_report.py:477:    if case_id not in RENDER_SUPPORTED_CASES:
scripts/render_case_report.py:480:            f"Supported: {sorted(RENDER_SUPPORTED_CASES)}. "
ui/backend/services/comparison_report.py:45:_REPORT_SUPPORTED_CASES = frozenset({"lid_driven_cavity"})
ui/backend/services/comparison_report.py:315:    if case_id not in _REPORT_SUPPORTED_CASES:
ui/backend/services/comparison_report.py:318:            f"Supported: {sorted(_REPORT_SUPPORTED_CASES)}."

codex
I’ve got one concrete correctness defect already: the non-uniform GCI iteration can overflow instead of degrading cleanly, and the current tests miss that branch entirely. I’m checking one last potential bundle integrity issue now: whether `build_manifest(repo_root=...)` and `serialize_zip_bytes()` stay consistent without the test monkeypatch.
exec
/bin/zsh -lc "python3 - <<'PY'
from ui.backend.services.grid_convergence import MeshSolution, compute_richardson_gci
# concrete overflow reproducer for non-uniform ratios
c = MeshSolution('c', 10, 1 + 0.3*(1/10)**1.7)
m = MeshSolution('m', 16, 1 + 0.3*(1/16)**1.7)
f = MeshSolution('f', 50, 1 + 0.3*(1/50)**1.7)
try:
    g = compute_richardson_gci(c,m,f)
    print('returned', g)
except Exception as e:
    print(type(e).__name__, str(e))
PY" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "python3 - <<'PY'
from ui.backend.services.grid_convergence import MeshSolution, compute_richardson_gci
# zero-order plateau reproducer
c = MeshSolution('c',10,1.0)
m = MeshSolution('m',20,0.5)
f = MeshSolution('f',40,0.0)
g = compute_richardson_gci(c,m,f)
print('p_obs', g.p_obs, 'gci21', g.gci_21, 'gci32', g.gci_32, 'note', g.note)
PY" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
p_obs 0.0 gci21 None gci32 None note ok

 succeeded in 0ms:
OverflowError (34, 'Result too large')

exec
/bin/zsh -lc "python3 - <<'PY'
from pathlib import Path
import tempfile, io, zipfile
from src.audit_package.manifest import build_manifest
from src.audit_package.serialize import serialize_zip_bytes
from ui.backend.tests.test_audit_package_phase7e import _setup_phase7_tree
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    _setup_phase7_tree(root)
    m = build_manifest(case_id='lid_driven_cavity', run_id='audit_real_run', repo_root=root, build_fingerprint='fixed')
    zb = serialize_zip_bytes(m)
    with zipfile.ZipFile(io.BytesIO(zb)) as zf:
        names = zf.namelist()
        phase7 = [n for n in names if n.startswith('phase7/')]
        print('manifest phase7 entries', len(m.get('phase7', {}).get('entries', [])))
        print('zip phase7 entries', len(phase7))
        print('names', phase7)
PY" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 204ms:
manifest phase7 entries 5
zip phase7 entries 0
names []

exec
/bin/zsh -lc "nl -ba /Users/Zhuanz/.codex/memories/MEMORY.md | sed -n '356,406p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
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
   381	## Task 3: Stop cleanly at the Opus 4.7 activation gate
   382	
   383	### rollout_summary_files
   384	
   385	- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, handoff prompt prepared instead of silent activation))
   386	
   387	### keywords
   388	
   389	- Opus 4.7 activation review, self-dispatch, planning-only, single-engine OpenFOAM, SU2 reference-only, CFX hold, review packet
   390	
   391	## User preferences
   392	
   393	- when working this repo, the user phrased the boundary as "继续推进开发，直至需要Opus 4.7介入" -> keep executing autonomously until a real gate is reached, then stop with a ready review packet [Task 1][Task 2][Task 3]
   394	- the rollout also showed a preference for explicit gate-aware staging rather than silent activation -> preserve the planning-only vs active distinction clearly in Notion and repo docs [Task 2][Task 3]
   395	
   396	## Reusable knowledge
   397	
   398	- Notion phase/task closure here requires updating both page properties and page body text; one surface alone leaves stale recovery state [Task 1]
   399	- `knowledge/whitelist.yaml` is the active whitelist source; older references to `knowledge/ai_cfd_cold_start_whitelist.yaml` are naming drift to normalize, not a fresh design change [Task 1]
   400	- Phase 9 must start from a bounded decision tree: keep single-engine OpenFOAM, allow reference-only external solver surfaces, or open one bounded proof slice; anything broader still needs review [Task 2]
   401	- The presence of SU2 tooling in skill inventory does not mean runtime support is already widened; `src/foam_agent_adapter.py` remained OpenFOAM-centered in this phase [Task 2]
   402	
   403	## Failures and how to do differently
   404	
   405	- Symptom: Notion and repo disagree on path names or report counts -> cause: contract naming drift and stale evidence -> fix: normalize the names and reconcile evidence instead of assuming one side is fully authoritative [Task 1]
   406	- Symptom: planning work accidentally looks like activation -> cause: Phase 9 docs/task text are not explicit enough about `Planned` vs `Active` -> fix: state planning-only mode in phase page, tasks, dashboard summary, and review packet [Task 2]

codex
CHANGES_REQUIRED

1. `phase7` zip embedding is inconsistent whenever `build_manifest(..., repo_root=...)` is used outside the real repo root. [manifest.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/audit_package/manifest.py:365) stores `disk_path_rel` relative to the caller’s `repo_root`, but [serialize.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/audit_package/serialize.py:148) reconstructs paths from `Path(__file__).resolve().parents[2]` instead of the same root. I reproduced this with the existing tmp-repo helper: the manifest had 5 `phase7` entries, the real zip had 0. The current test masks it by monkeypatching `_zip_entries_from_manifest` in [test_audit_package_phase7e.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_audit_package_phase7e.py:152) and never exercises real zip serialization in [test_audit_package_phase7e.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_audit_package_phase7e.py:202). That can produce a signed bundle whose embedded `manifest.json` advertises files the zip does not actually contain.

2. The advertised non-uniform-r GCI path can still hard-fail. In [grid_convergence.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/grid_convergence.py:127), the fixed-point loop only catches `ValueError`/`ZeroDivisionError`; `r ** p_guess` can raise `OverflowError` before the 50-iteration bound helps. Concrete reproducer: meshes `(10, 16, 50)` with monotone `f_h = 1 + 0.3 h^1.7` raise `OverflowError: (34, 'Result too large')`. [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:347) only suppresses `ValueError`/`ImportError`, so this becomes a report-generation 500 instead of a clean `gci=None` / diagnostic note. No test in [test_grid_convergence_gci.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_grid_convergence_gci.py:16) covers that branch.

3. The GCI diagnostics are misleading when `p_obs == 0.0`. In [grid_convergence.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/grid_convergence.py:146), exact zero order falls through with `note="ok"`, but the `> 0` guard suppresses Richardson extrapolation and both GCI values. Example: `(1.0, 0.5, 0.0)` returns `p_obs=0.0`, `gci_21=None`, `gci_32=None`, `note="ok"`. That is not an honest edge-case report.

I did not find a live repo-root byte-ordering or path-containment defect in the current LDC path: `sorted(rglob)`, `entries.sort`, and `sorted(entries.keys())` are enough for deterministic ordering here, and two local rebuilds with fixed `build_fingerprint` produced the same zip SHA256. The direct symlink-escape case inside sanctioned roots also looks blocked by the resolve+`relative_to` checks. Targeted regression run passed: `PYTHONPATH=. .venv/bin/pytest ui/backend/tests/test_grid_convergence_gci.py ui/backend/tests/test_audit_package_phase7e.py ui/backend/tests/test_audit_package_route.py -q` → 35 passed.

The `>50 MB` VTK silent-skip is not the main blocker, but it is currently non-auditable: reviewers cannot distinguish “not produced” from “produced then intentionally dropped” unless skipped files are surfaced in manifest metadata.


tokens used
101,484
CHANGES_REQUIRED

1. `phase7` zip embedding is inconsistent whenever `build_manifest(..., repo_root=...)` is used outside the real repo root. [manifest.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/audit_package/manifest.py:365) stores `disk_path_rel` relative to the caller’s `repo_root`, but [serialize.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/audit_package/serialize.py:148) reconstructs paths from `Path(__file__).resolve().parents[2]` instead of the same root. I reproduced this with the existing tmp-repo helper: the manifest had 5 `phase7` entries, the real zip had 0. The current test masks it by monkeypatching `_zip_entries_from_manifest` in [test_audit_package_phase7e.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_audit_package_phase7e.py:152) and never exercises real zip serialization in [test_audit_package_phase7e.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_audit_package_phase7e.py:202). That can produce a signed bundle whose embedded `manifest.json` advertises files the zip does not actually contain.

2. The advertised non-uniform-r GCI path can still hard-fail. In [grid_convergence.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/grid_convergence.py:127), the fixed-point loop only catches `ValueError`/`ZeroDivisionError`; `r ** p_guess` can raise `OverflowError` before the 50-iteration bound helps. Concrete reproducer: meshes `(10, 16, 50)` with monotone `f_h = 1 + 0.3 h^1.7` raise `OverflowError: (34, 'Result too large')`. [comparison_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:347) only suppresses `ValueError`/`ImportError`, so this becomes a report-generation 500 instead of a clean `gci=None` / diagnostic note. No test in [test_grid_convergence_gci.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_grid_convergence_gci.py:16) covers that branch.

3. The GCI diagnostics are misleading when `p_obs == 0.0`. In [grid_convergence.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/grid_convergence.py:146), exact zero order falls through with `note="ok"`, but the `> 0` guard suppresses Richardson extrapolation and both GCI values. Example: `(1.0, 0.5, 0.0)` returns `p_obs=0.0`, `gci_21=None`, `gci_32=None`, `note="ok"`. That is not an honest edge-case report.

I did not find a live repo-root byte-ordering or path-containment defect in the current LDC path: `sorted(rglob)`, `entries.sort`, and `sorted(entries.keys())` are enough for deterministic ordering here, and two local rebuilds with fixed `build_fingerprint` produced the same zip SHA256. The direct symlink-escape case inside sanctioned roots also looks blocked by the resolve+`relative_to` checks. Targeted regression run passed: `PYTHONPATH=. .venv/bin/pytest ui/backend/tests/test_grid_convergence_gci.py ui/backend/tests/test_audit_package_phase7e.py ui/backend/tests/test_audit_package_route.py -q` → 35 passed.

The `>50 MB` VTK silent-skip is not the main blocker, but it is currently non-auditable: reviewers cannot distinguish “not produced” from “produced then intentionally dropped” unless skipped files are surfaced in manifest metadata.


