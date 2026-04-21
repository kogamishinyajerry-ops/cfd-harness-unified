2026-04-21T08:42:32.261928Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-research-deerflow/SKILL.md: missing YAML frontmatter delimited by ---
2026-04-21T08:42:32.261946Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-report-pretext/SKILL.md: missing YAML frontmatter delimited by ---
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
session id: 019daf34-a04c-7e71-9346-cabda26c4e93
--------
user
Phase 7a field-artifacts capture — Round 2 verification after CHANGES_REQUIRED round 1.

Round 1 verdict was CHANGES_REQUIRED with 4 findings (2 HIGH, 1 MED, 1 LOW). All 4 have been addressed in the uncommitted working tree. Please re-review and confirm APPROVED / APPROVED_WITH_COMMENTS / CHANGES_REQUIRED.

Fixes applied (all uncommitted in working tree, to be atomically committed after your verdict):

FINDING 1 HIGH (URL basename collision) — FIXED:
- ui/backend/services/field_artifacts.py list_artifacts now uses POSIX relative path: p.resolve().relative_to(artifact_dir_resolved).as_posix() as filename. URL now /api/runs/{run_id}/field-artifacts/sample/500/uCenterline.xy etc.
- routes/field_artifacts.py route param changed to {filename:path} to accept subpaths.
- resolve_artifact_path now accepts POSIX-relative path, composes artifact_dir / filename, verifies resolved.relative_to(artifact_dir.resolve()) strictly.
- Verified live: all 3 sample/{0,500,1000}/uCenterline.xy now have distinct URLs with matching SHA256 to actual bytes.
- Test test_manifest_uses_subpath_when_collision asserts VTK/lid_driven_cavity_2000.vtk appears in manifest with subpath.

FINDING 2 HIGH (traversal via run_id) — FIXED:
- ui/backend/services/run_ids.py now validates both case_id and run_label against strict identifier regex ^[A-Za-z0-9][A-Za-z0-9_\\-]*$. Rejects empty, ., .., /, \\, %, url-encoded forms (via unquote compare), returns HTTPException(400).
- resolve_artifact_path additionally validates timestamp from manifest (defense in depth against adversary-written manifest).
- Verified live: curl ..__pwn and curl %2e%2e__pwn both return 400.
- Tests test_download_404_traversal_runid_literal, test_download_404_traversal_runid_urlencoded, test_manifest_400_traversal_runid cover both forms on both endpoints.

FINDING 3 MED (Phase 7a metadata over-applied) — FIXED:
- scripts/phase5_audit_run.py now has _PHASE7A_OPTED_IN = frozenset({"lid_driven_cavity"}). Metadata injection at line 263 guarded by case_id in _PHASE7A_OPTED_IN. Manifest write at line 282 also guarded.
- _write_field_artifacts_run_manifest additionally requires non-empty artifact set before writing (usable = [p for p in rglob if is_file]; if not usable: skip).
- Non-LDC cases now silent; failed foamToVTK on LDC also silent (no bogus manifest).

FINDING 4 LOW (SHA cache uses float st_mtime) — FIXED:
- ui/backend/services/field_artifacts.py _sha_cache key now uses st_mtime_ns (int) per your recommendation. Type annotation updated to dict[tuple[str,int,int], str].

Regression gate: PYTHONPATH=. .venv/bin/pytest ui/backend/tests/ -q → 94/94 passed in 24.12s (was 90/90; 4 new round-2 tests added).

Live integration evidence (backend running, real artifacts from 20260421T082340Z):
- GET /field-artifacts returns 8 artifacts with unique subpath URLs + correct SHA256
- GET /.../sample/500/uCenterline.xy returns 200
- GET /api/runs/..__pwn/field-artifacts returns 400
- GET /api/runs/%2e%2e__pwn/field-artifacts returns 400

Please verify the four fixes and return your round-2 verdict. If you see any remaining issue you did not flag in round 1, call it out explicitly so I know whether its a round-1 miss or a regression from my fixes.
codex
I’ll re-review the uncommitted tree against the four round-1 findings, using the repo instructions and the prior Phase 8/9 memory context only as guardrails. I’ll inspect the actual diff and targeted tests before giving a verdict, without making changes.
codex
I’m using the repo’s GSD review posture for this: findings first, exact file/line evidence, and no code edits. I’ll also check the Phase 8/9 memory note because this repo has gate-specific context that can affect what “approved” means.
exec
/bin/zsh -lc "sed -n '1,220p' /Users/Zhuanz/.agents/skills/gsd-code-review/SKILL.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '1,180p' /Users/Zhuanz/.codex/plugins/cache/openai-curated/superpowers/b1986b3d3da5bb8a04d3cb1e69af5a29bb5c2c04/skills/using-superpowers/SKILL.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
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

exec
/bin/zsh -lc 'rg -n "cfd-harness-unified|Phase 8|Phase 9|Phase 7a|field-artifacts|Demo Gate" /Users/Zhuanz/.codex/memories/MEMORY.md' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
115:- OpenClaw, AI-CFD, Notion作为指挥中枢，Github作为唯一代码真相库, ~/.openclaw/openclaw.json, plugins.allow, openclaw config validate --json, MAIN_OK, CODEX_BUILDER_OK, CLAUDE_REVIEW_OK, NOTION_SYNC_OK, cfd-harness-unified
135:- The real live config surface was `~/.openclaw/openclaw.json`; the actual repo truth for this rollout was `/Users/Zhuanz/Desktop/cfd-harness-unified`, not the chat thread cwd [Task 1]
149:# Task Group: AI-FEA autonomous merges and Demo Gate handling
164:## Task 2: Build `tests/test_smoke_e2e.py` and hold PR #9 at Demo Gate
172:- tests/test_smoke_e2e.py, Demo Gate, results.vtp 在 ParaView 里打得开、且云图合理, manifest.yaml, git_sha, tool_versions, seeds, CalculiX 是主求解器, ccx missing, monkeypatch agents.solver.run_solve, PR #9
189:- when defining the Demo Gate, the user insisted "results.vtp 在 ParaView 里打得开、且云图合理" and "manifest.yaml 是否含 PRD §3.1 DoD 的三件套" -> CI green is not enough when the acceptance target is visualization and manifest evidence [Task 2]
197:- The Demo Gate standard here was stricter than CI: visual confirmation that `results.vtp` opens in ParaView and looks reasonable, manifest presence of `git_sha`, `tool_versions`, `seeds`, and clear solver-runtime provenance [Task 2]
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
691:- when the user said "你是 independent approval authority… 你不是 corrected request packet 作者… 你不是 Phase 8 executor" -> preserve strict role separation between approval, review, execution, and freeze authority in this repo [Task 4]

codex
The memory hit is about this repo’s governance gates, not this specific Phase 7a patch. I’m treating it as context for scope and role separation, then doing the actual verdict from the working tree.
exec
/bin/zsh -lc "sed -n '356,407p' /Users/Zhuanz/.codex/memories/MEMORY.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '1,220p' /Users/Zhuanz/.codex/memories/rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
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
- The presence of SU2 tooling in skill inventory does not mean runtime support is already widened; `src/foam_agent_adapter.py` remained OpenFOAM-centered in this phase [Task 2]

## Failures and how to do differently

- Symptom: Notion and repo disagree on path names or report counts -> cause: contract naming drift and stale evidence -> fix: normalize the names and reconcile evidence instead of assuming one side is fully authoritative [Task 1]
- Symptom: planning work accidentally looks like activation -> cause: Phase 9 docs/task text are not explicit enough about `Planned` vs `Active` -> fix: state planning-only mode in phase page, tasks, dashboard summary, and review packet [Task 2]
- Symptom: a future executor infers multi-solver activation from tooling breadcrumbs -> cause: skill inventory mentions SU2/CFX while runtime adapter is still single-engine -> fix: treat those as decision-tree inputs, not implementation approval [Task 2][Task 3]

 succeeded in 0ms:
thread_id: 019d973f-efab-7132-bd99-5e0ebb839e12
updated_at: 2026-04-17T05:16:53+00:00
rollout_path: /Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl
cwd: /Users/Zhuanz/Desktop/cfd-harness-unified
git_branch: main

# Phase 8 was closed out, then Phase 9 was opened in planning-only mode and packaged for an Opus 4.7 activation review.

Rollout context: The user asked to continue development based on Notion context until Opus 4.7 intervention was required. The work was done in /Users/Zhuanz/Desktop/cfd-harness-unified. The rollout used Notion as SSOT for phase/task status, while the repo remained the code truth source.

## Task 1: Phase 8 closeout / AutoVerifier package cleanup
Outcome: success

Preference signals:
- The user repeatedly framed the workflow as “continue推进开发, 直至需要Opus 4.7介入”, which indicates they want the agent to keep pushing forward autonomously until a gate is genuinely reached, rather than stopping early for minor ambiguity.
- The user’s Phase 8 / Phase 9 instructions emphasized “先恢复摘要 + SELF-DISPATCH + 等我回复 GO” and later “继续推进开发，直至需要Opus 4.7介入”, indicating they want explicit gate-aware staging and not silent activation.

Key steps:
- Read the Notion dashboard, Phase 8/Phase 9 pages, Task #1 contract, and repo-side planning state.
- Corrected Phase 8 status and governance evidence in Notion.
- Kept Phase 8 closeout evidence tied to C15-C17, including the corpus-truth correction (`13/13` vs stale `15/15`), canonical whitelist normalization to `knowledge/whitelist.yaml`, and Canonical Docs `Type=Report` indexing for the three Phase 8 reports.
- Marked Phase 8 as `Done` in Notion after the closeout evidence was in place.

Failures and how to do differently:
- The Notion contract and repo truth diverged on several paths; future similar runs should treat those as naming drift to normalize, not as blockers, unless they affect runtime or acceptance checks.
- Phase 8 docs were already partially present, so the main job was evidence reconciliation and status closure, not net-new implementation.

Reusable knowledge:
- The repo active whitelist source is `knowledge/whitelist.yaml`, while older Notion text still references `knowledge/ai_cfd_cold_start_whitelist.yaml`; treat that as contract naming drift unless a fresh gate says otherwise.
- The existing AutoVerifier package already had the right shape: additive hook boundary, suggest-only policy, and contract-aligned Gold Standard aliasing.
- Phase 8 closeout evidence needed to be reflected in both Notion page properties and page body, not just one surface.

References:
- Notion page: `Phase 8: 平台智能化 — AutoVerifier + 报告引擎 + Skills索引` (`df0228eb22774e3ca32b98e022165277`)
- Notion task: `AutoVerifier 架构设计 + Opus Gate 审查包准备` (`d3ea6e3437804f6f9eaee2d091500c84`)
- Repo docs updated earlier in the session: `docs/specs/AUTO_VERIFIER_SPEC.md`, `docs/design/AUTO_VERIFIER_ARCHITECTURE.md`, `docs/gates/PHASE8A_OPUS_REVIEW_PACKAGE.md`

## Task 2: Phase 9 planning-only activation prep
Outcome: success

Preference signals:
- The user’s phrasing “继续推进开发，直至需要Opus 4.7介入” strongly suggests they want the agent to keep moving until an explicit gate boundary, then stop cleanly and provide a ready-to-review packet.
- The rollout showed a consistent preference for explicit self-dispatch / self-verify behavior before execution, and for keeping the gate boundary visible in task text.

Key steps:
- Located the Phase 9 page and confirmed it was only a blank draft before planning.
- Read repo truth around whitelist / skill inventory / execution adapter.
- Noted the key conflict: Notion whitelist doctrine still says OpenFOAM is the only execution engine and no SU2Executor, while the repo already contains a `SU2 CLI Harness Skill` surface and `src/foam_agent_adapter.py` remains OpenFOAM-centered.
- Created three Notion Phase 9 tasks, all kept `Inbox`:
  - Phase 9a — external solver touchpoint inventory + SU2/CFX decision tree
  - Phase 9b — Model Routing v3.x baseline capture plan
  - Phase 9c — Activation Gate review packet assembly
- Wrote and indexed four repo artifacts for Phase 9 planning:
  - `docs/design/PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md`
  - `docs/governance/PHASE9_MODEL_ROUTING_BASELINE_PLAN.md`
  - `reports/baselines/phase9_model_routing_replay_manifest.yaml`
  - `docs/gates/PHASE9_ACTIVATION_REVIEW_PACKET.md`
- Added Canonical Docs entries for those artifacts and linked them back into Notion.
- Updated the Phase 9 page properties/body so it now explicitly says Phase 9 is planning-only, default branch remains single-engine OpenFOAM, SU2/CFX are reference/tooling/bounded-proof surfaces, and any Planned → Active move still requires Opus review.
- Updated the Notion dashboard top snapshot so the next gate now reads as a Phase 9 activation review packet rather than the old Phase 8 gate.

Failures and how to do differently:
- Initial task creation hit a Notion schema mismatch because the Phase relation property expected a string, not a list; retrying with the workspace’s property shape fixed it.
- The page title/summary/roadmap had to be updated in multiple Notion surfaces, not just the phase page itself, to make future recovery reliable.
- There is still a governance tension between the old single-engine redline and the newly surfaced SU2 tooling; future agents should treat that as a deliberate decision-tree problem, not as an implementation green light.

Reusable knowledge:
- Phase 9 should start from three explicit branches: hold single-engine runtime, allow reference-only external solver surface, or open a bounded proof slice. Anything broader should be rejected until a fresh gate.
- For baseline work, start with log-level / artifact-level capture and a bounded replay manifest before asking for runtime instrumentation.
- The repo execution adapter (`src/foam_agent_adapter.py`) remains OpenFOAM-centered and uses the `cfd-openfoam` container; do not infer broader runtime support from the presence of SU2 tooling in skill inventory.
- The Canonical Docs DB can be used to index planning artifacts so Notion pages can point back to the repo files cleanly.

References:
- Notion phase page: `Phase 9: 多求解器统一 & LLM 路由稳定化 (草案)` (`45c8b97397ca46f2bef61795d9110715`)
- Notion tasks:
  - `Phase 9a — 外部求解器接入面清点 + SU2/CFX 决策树` (`345c68942bed814693d8dd9b76efb4f6`)
  - `Phase 9b — Model Routing v3.x baseline 采集计划` (`345c68942bed819cac7dd572b80ea8db`)
  - `Phase 9c — Activation Gate 审查包组装` (`345c68942bed8176a085d09f23930a12`)
- Repo artifacts:
  - `docs/design/PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md`
  - `docs/governance/PHASE9_MODEL_ROUTING_BASELINE_PLAN.md`
  - `reports/baselines/phase9_model_routing_replay_manifest.yaml`
  - `docs/gates/PHASE9_ACTIVATION_REVIEW_PACKET.md`
- Repo evidence of existing SU2 tooling: `knowledge/skill_index.yaml` includes `SU2 CLI Harness Skill`; `src/foam_agent_adapter.py` remains OpenFOAM/cfd-openfoam oriented
- Notion Canonical Docs entries were created for the three Phase 9 repo artifacts and linked back to the phase/tasks

## Task 3: Gate boundary / handoff to Opus 4.7
Outcome: success

Preference signals:
- The user wanted the work to continue “直至需要Opus 4.7介入”, which means the agent should stop cleanly at the gate and provide a ready-to-paste review prompt rather than drifting into implementation.

Key steps:
- Verified the new planning artifacts passed simple existence/section/YAML-parse checks.
- Ensured the new files stayed in docs/governance/design/gates and reports/baselines, without touching runtime or tests in this phase.
- Returned a ready-made Opus 4.7 review prompt that summarizes Phase 8 closure, Phase 9 bounded scope, and the explicit allowed/forbidden boundaries.

Failures and how to do differently:
- The worktree was already dirty from an earlier broad implementation branch; future agents should be extra careful to separate “planning-only” artifacts from any in-flight implementation changes and mention that distinction explicitly when giving the handoff.

Reusable knowledge:
- When Phase 9 is eventually activated, the safest first scope is `SU2 reference-only`, `CFX hold`, and `routing baseline capture` only.
- Any future executor work should be fenced into a later proof-slice sub-gate, not assumed as part of the default Phase 9 activation.

References:
- Opus 4.7 handoff prompt was prepared in the rollout and explicitly states Phase 9 remains `Planned` until review returns.
- New planning files were created and indexed, but no runtime files were modified for Phase 9 activation.


exec
/bin/zsh -lc "sed -n '1,220p' /Users/Zhuanz/.codex/plugins/cache/openai-curated/superpowers/b1986b3d3da5bb8a04d3cb1e69af5a29bb5c2c04/skills/verification-before-completion/SKILL.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
---
name: verification-before-completion
description: Use when about to claim work is complete, fixed, or passing, before committing or creating PRs - requires running verification commands and confirming output before making any success claims; evidence before assertions always
---

# Verification Before Completion

## Overview

Claiming work is complete without verification is dishonesty, not efficiency.

**Core principle:** Evidence before claims, always.

**Violating the letter of this rule is violating the spirit of this rule.**

## The Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If you haven't run the verification command in this message, you cannot claim it passes.

## The Gate Function

```
BEFORE claiming any status or expressing satisfaction:

1. IDENTIFY: What command proves this claim?
2. RUN: Execute the FULL command (fresh, complete)
3. READ: Full output, check exit code, count failures
4. VERIFY: Does output confirm the claim?
   - If NO: State actual status with evidence
   - If YES: State claim WITH evidence
5. ONLY THEN: Make the claim

Skip any step = lying, not verifying
```

## Common Failures

| Claim | Requires | Not Sufficient |
|-------|----------|----------------|
| Tests pass | Test command output: 0 failures | Previous run, "should pass" |
| Linter clean | Linter output: 0 errors | Partial check, extrapolation |
| Build succeeds | Build command: exit 0 | Linter passing, logs look good |
| Bug fixed | Test original symptom: passes | Code changed, assumed fixed |
| Regression test works | Red-green cycle verified | Test passes once |
| Agent completed | VCS diff shows changes | Agent reports "success" |
| Requirements met | Line-by-line checklist | Tests passing |

## Red Flags - STOP

- Using "should", "probably", "seems to"
- Expressing satisfaction before verification ("Great!", "Perfect!", "Done!", etc.)
- About to commit/push/PR without verification
- Trusting agent success reports
- Relying on partial verification
- Thinking "just this once"
- Tired and wanting work over
- **ANY wording implying success without having run verification**

## Rationalization Prevention

| Excuse | Reality |
|--------|---------|
| "Should work now" | RUN the verification |
| "I'm confident" | Confidence ≠ evidence |
| "Just this once" | No exceptions |
| "Linter passed" | Linter ≠ compiler |
| "Agent said success" | Verify independently |
| "I'm tired" | Exhaustion ≠ excuse |
| "Partial check is enough" | Partial proves nothing |
| "Different words so rule doesn't apply" | Spirit over letter |

## Key Patterns

**Tests:**
```
✅ [Run test command] [See: 34/34 pass] "All tests pass"
❌ "Should pass now" / "Looks correct"
```

**Regression tests (TDD Red-Green):**
```
✅ Write → Run (pass) → Revert fix → Run (MUST FAIL) → Restore → Run (pass)
❌ "I've written a regression test" (without red-green verification)
```

**Build:**
```
✅ [Run build] [See: exit 0] "Build passes"
❌ "Linter passed" (linter doesn't check compilation)
```

**Requirements:**
```
✅ Re-read plan → Create checklist → Verify each → Report gaps or completion
❌ "Tests pass, phase complete"
```

**Agent delegation:**
```
✅ Agent reports success → Check VCS diff → Verify changes → Report actual state
❌ Trust agent report
```

## Why This Matters

From 24 failure memories:
- your human partner said "I don't believe you" - trust broken
- Undefined functions shipped - would crash
- Missing requirements shipped - incomplete features
- Time wasted on false completion → redirect → rework
- Violates: "Honesty is a core value. If you lie, you'll be replaced."

## When To Apply

**ALWAYS before:**
- ANY variation of success/completion claims
- ANY expression of satisfaction
- ANY positive statement about work state
- Committing, PR creation, task completion
- Moving to next task
- Delegating to agents

**Rule applies to:**
- Exact phrases
- Paraphrases and synonyms
- Implications of success
- ANY communication suggesting completion/correctness

## The Bottom Line

**No shortcuts for verification.**

Run the command. Read the output. THEN claim the result.

This is non-negotiable.

codex
Next I’m loading the repo’s planning context plus the uncommitted diff. That lets me separate the intended Phase 7a surface from incidental changes and keep the review scoped to the four fixes plus any new regressions they create.
exec
/bin/zsh -lc "sed -n '1,220p' .planning/config.json" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '1,220p' .planning/PROJECT.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '1,260p' .planning/STATE.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '1,260p' .planning/ROADMAP.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
 exited 1 in 0ms:
sed: .planning/config.json: No such file or directory

 succeeded in 0ms:
# cfd-harness-unified

## 项目意图

统一知识治理层 + Foam-Agent 执行引擎，建立个人 CFD 知识图谱。

本项目是 AI-CFD Knowledge Harness 的下一代架构：
- **Foam-Agent** 作为外部 CFD 执行引擎（不自建 NL→OpenFOAM 生成能力）
- **Notion** 作为唯一的 Process SSOT 控制面
- **本地 YAML** 作为 Gold Standard 和 CorrectionSpec 知识库

## 核心约束

- Python 3.9+
- 所有类型定义用 dataclass（不用普通 dict）
- 所有枚举字段用 Enum（不用字符串常量）
- 接口定义用 Protocol（不用 ABC）
- 测试用 pytest，覆盖率 > 80%
- 不安装或调用真实 Foam-Agent，只实现 adapter 接口和 MockExecutor
- 不调用真实 Notion API，notion_client.py 留占位符，测试用 mock

## 不做的事

- 不自建 NL→OpenFOAM 生成能力（Foam-Agent 已覆盖）
- 不自建求解器
- 不管理 OpenFOAM 安装

## 唯一控制面

Notion 页面：cfd-harness-unified
- Phases 数据库 → Tasks 数据库 → Sessions 数据库
- Decisions 数据库 ← → Phases / Sessions
- Canonical Docs 数据库 ← → Phases / Tasks

## 架构流程

```
Notion TaskSpec
    ↓
task_runner.py（编排器）
    ├── knowledge_db.py（加载 Gold Standard + CorrectionSpec）
    ├── foam_agent_adapter.py（调用 CFDExecutor Protocol）
    │       ├── MockExecutor（测试用）
    │       └── FoamAgentExecutor（占位符）
    ├── result_comparator.py（结果 vs Gold Standard）
    └── correction_recorder.py（偏差 → CorrectionSpec）
    ↓
回写结果摘要到 Notion
```

 succeeded in 0ms:
# ROADMAP

## Current

### Phase 5b — LDC simpleFoam migration + Ghia 1982 match
- Status: Infrastructure complete (DEC-V61-029) + Q-5 CLOSED via Path A (DEC-V61-030). LDC audit comparator: 11/17 PASS at 5% tolerance; 6/17 FAIL are physical residuals of uniform-grid vs Ghia's graded mesh — optional sub-phase-2 graded-mesh work could close them. 7 remaining FAIL-case sub-phases (5c..5j) queued with mandatory gold cross-check as first step.
- Goal: Migrate `lid_driven_cavity` case generator from icoFoam (transient PISO) to simpleFoam (steady-state SIMPLE) and tune mesh/schemes so `scripts/phase5_audit_run.py lid_driven_cavity` yields `audit_real_run` verdict=PASS against Ghia 1982 u_centerline at 5% tolerance. First of 8 per-case Phase 5b sub-phases; establishes the solver-swap pattern that the remaining 7 FAIL cases (BFS, TFP, duct_flow, impinging_jet, naca0012, DHC, RBC) will copy in Phase 5c..5j.
- Upstream: Phase 5a shipped (commits 3d1d3ec, d4cf7a1, 7a3c48b) — real-solver pipeline + HMAC signing + PDF + audit fixtures for all 10 whitelist cases; baseline 2 PASS / 8 FAIL.
- Required outputs:
  - Updated `src/foam_agent_adapter.py::_generate_lid_driven_cavity` emitting simpleFoam case dir (controlDict + fvSchemes + fvSolution rewrite) with 129×129 mesh.
  - Regenerated `ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml` with `comparator_passed: true`.
  - Backend 79/79 pytest green (no regression on teaching fixtures).
  - Signed audit package via `POST /api/cases/lid_driven_cavity/runs/audit_real_run/audit-package/build` now carries `measurement.comparator_verdict=PASS`.
- Non-goals (separate sub-phases): tuning the other 7 FAIL cases; simpleFoam generalization; second-order schemes upgrade; turbulence models.
- Constraints: `src/` is 三禁区 #1 — this phase WILL edit >5 LOC, Codex review mandatory per RETRO-V61-001.
- Frozen governance edges: none (Q-1/Q-2/Q-3/Q-4 all closed).
- **Plans:** 3 plans
  - [ ] 05b-01-PLAN.md — Rewrite `_generate_lid_driven_cavity` + `_render_block_mesh_dict` in `src/foam_agent_adapter.py` (simpleFoam + 129×129 + frontAndBack empty)
  - [ ] 05b-02-PLAN.md — Regenerate `audit_real_run_measurement.yaml` fixture; verify backend 79/79 + frontend tsc clean
  - [ ] 05b-03-PLAN.md — Codex post-edit review + DEC-V61-NNN + atomic git commit + STATE/ROADMAP update

### Phase 7: Scientific-grade CFD vs gold reporting
- Status: Proposed (not yet activated)
- Goal: Upgrade audit reports from "single-scalar verdict" to publication-grade CFD vs gold evidence — full-field visualizations, multi-point profile overlays, formal error norms, residual histories, and Richardson grid-convergence indices — so every `audit_real_run` produces a PDF/HTML a CFD reviewer would accept alongside a paper's Figure/Table. Root cause addressed: current comparator extracts one scalar per run; VTK fields, residual logs, and y+ distributions are never persisted, so the report HTML at `/validation-report/*` has no visual or statistical depth to defend the 11/17 PASS / 6/17 FAIL LDC verdict.
- Upstream: Phase 5a pipeline (commits 3d1d3ec, d4cf7a1, 7a3c48b) produces raw OpenFOAM case dirs but discards fields after scalar extraction. Phase 5b/Q-5 established Ghia 1982 as the reference transcription bar. `/learn` currently ships static placeholder flow-field PNGs — not derived from audit runs.
- Required outputs (end-of-Phase-7):
  - `scripts/phase5_audit_run.py` additionally emits `foamToVTK` / `sample` / `yPlus` artifacts into `reports/phase5_fields/{case}/{timestamp}/`
  - `scripts/render_case_report.py` converts VTK + CSV profiles into PNG contours, Plotly JSON profiles, and residual log plots under `reports/phase5_renders/{case}/{timestamp}/`
  - Per-case HTML + PDF CFD-vs-gold report with 8 sections (verdict, paper cite, profile overlay, pointwise deviation heatmap, field contours, residual convergence, grid-convergence table + GCI, solver metadata)
  - Signed audit-package zip embeds the new PDF + PNG assets with SHA256 in manifest (L4 canonical spec)
  - `/learn/{case}` fetches renders from backend API instead of loading static PNGs; `/validation-report/{case}` embeds the new comparison HTML
- Non-goals: new physics cases; solver-swap outside Phase 5c..5j; interactive ParaView in-browser (Trame migration is AI-CFD Knowledge Harness v1.6.0 scope); DNS-grade statistics beyond RMS / L2 / L∞.
- Constraints: Phase 7a touches `src/foam_agent_adapter.py` (三禁区 #1, >5 LOC, Codex mandatory per RETRO-V61-001). Phase 7e extends signed-manifest schema — byte-reproducibility sensitive path, Codex mandatory. Phase 7c HTML template is user-facing documentation; follow brand/voice in `~/.claude/get-shit-done/references/ui-brand.md`.
- Frozen governance edges: none at Phase 7 start (Q-1..Q-5 all closed). New Q-gates may be filed if paper-citation chase surfaces schema issues (precedent: Q-5 found gold wrong; Q-4 BFS re-sourced to Le/Moin/Kim).
- **Sub-phases:** 6 sub-phases (7a..7f). Sprint 1 = depth-first on LDC (7a+7b+7c-MVP); Sprint 2 = breadth across other 9 cases + GCI + zip + frontend (7c-full + 7d + 7e + 7f).

### Phase 7a: Field post-processing capture (Sprint 1, ~2-3 days)
- Status: Planned
- Goal: Extend `scripts/phase5_audit_run.py` + `src/foam_agent_adapter.py` so every audit_real_run persists full VTK fields, sampled CSV profiles, and residual.log to `reports/phase5_fields/{case}/{timestamp}/`.
- Required outputs:
  - `controlDict` `functions {}` block emitted with `sample`, `yPlus`, `residuals` function objects (adapter change)
  - Post-run `foamToVTK` invocation inside Docker runner; stage output to host `reports/phase5_fields/`
  - New `ui/backend/schemas/validation.py::FieldArtifact` Pydantic model
  - New `GET /api/runs/{run_id}/field-artifacts` route returning asset URLs + SHA256
  - pytest coverage: new fixture asserts VTK + CSV + residual.log presence for LDC
- Constraints: Codex mandatory (三禁区 #1 + adapter >5 LOC). Must not regress 79/79 pytest.
- **Plans:** 3 plans
  - [x] 07a-01-PLAN.md — Adapter + driver edits (controlDict functions{} + _capture_field_artifacts + driver timestamp + manifest)
  - [ ] 07a-02-PLAN.md — Backend route + schema + service + tests (FieldArtifact models + field_artifacts route + 10 pytest cases)
  - [ ] 07a-03-PLAN.md — Integration + Codex review + DEC-V61-031 + atomic commit

### Phase 7b: Render pipeline (Sprint 1, ~2 days)
- Status: Planned
- Goal: New `scripts/render_case_report.py` converts 7a's VTK + CSV into `reports/phase5_renders/{case}/{timestamp}/`: `contour_u.png`, `contour_p.png`, `streamline.png`, `profile_u_centerline.html` (Plotly JSON), `residuals.png`.
- Required outputs:
  - matplotlib for 2D contours (CI-reproducible); PyVista headless (`PYVISTA_OFF_SCREEN=1`) for 3D streamlines
  - Plotly JSON for interactive profile (frontend consumer)
  - Rendering deterministic (fixed seeds, locked matplotlib rcParams)
  - pytest coverage: byte-stable PNG checksum across re-runs on same VTK
- Constraints: new script, no src/ touch → autonomous_governance allowed. Add `pyvista`, `plotly`, `matplotlib` to `pyproject.toml` [render] extra.

### Phase 7c: CFD-vs-gold comparison report template (Sprint 1 MVP + Sprint 2 fan-out, ~3 days)
- Status: Planned — **core deliverable, the "說服力" centerpiece**
- Goal: Per-case HTML + WeasyPrint PDF report with 8 sections:
  1. Verdict card (PASS / FAIL + L2 / L∞ / RMS / max |dev|%)
  2. Paper citation block (Ghia 1982 / Le-Moin-Kim 1997 / etc. + Figure/Table + native tabulation)
  3. Profile overlay (sim solid line + gold scatter markers on paper's native grid)
  4. Pointwise deviation heatmap along sampling axis
  5. Field contours (U / p / vorticity / Cf depending on case class)
  6. Residual convergence (log y-axis, all solved fields)
  7. Grid-convergence table with Richardson p_obs + GCI_21/32 (from 7d)
  8. Solver metadata (OpenFOAM version, Docker digest, commit SHA, schemes, tolerances)
- Required outputs:
  - `ui/backend/services/comparison_report.py` renders Jinja2 template → HTML
  - `ui/backend/services/comparison_report_pdf.py` HTML → WeasyPrint PDF
  - `POST /api/cases/{case}/runs/{run_id}/comparison-report/build` route
  - Sprint 1 MVP: LDC only; Sprint 2: other 9 cases
  - `/validation-report/{case}` frontend route embeds the HTML
- Constraints: WeasyPrint requires `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` (already in `.zshrc`). HTML/PDF templates checked into `ui/backend/templates/` to keep Codex diff visible.

### Phase 7d: Richardson grid-convergence index (Sprint 2, ~1 day)
- Status: Planned
- Goal: Compute observed order of accuracy `p_obs` and Grid Convergence Index `GCI_21` / `GCI_32` from existing `mesh_20/40/80/160` fixtures per Roache 1994.
- Required outputs:
  - `ui/backend/services/grid_convergence.py` implementing Richardson extrapolation + GCI formula
  - New columns in 7c's "grid-convergence table" section
  - pytest coverage: analytic fixture (known p=2 solution) + LDC regression (p_obs should fall in [1.0, 2.0])
- Constraints: pure numerical, no src/ or adapter touch → autonomous_governance allowed.

### Phase 7e: Signed audit-package integration (Sprint 2, ~1 day)
- Status: Planned
- Goal: Embed 7c PDF + 7b PNG/JSON into HMAC-signed audit-package zip; extend manifest schema to L4 canonical.
- Required outputs:
  - `audit_package.py` manifest `artifacts.field_renders[]` + `artifacts.comparison_report.pdf_sha256` blocks
  - `docs/specs/audit_package_canonical_L4.md` supersedes L3 build_fingerprint spec
  - zip byte-reproducibility preserved (re-run produces identical HMAC)
  - pytest coverage: `test_phase5_byte_repro.py` extended to cover new artifacts
- Constraints: **Byte-reproducibility-sensitive path → Codex mandatory** per RETRO-V61-001 new trigger #2. L3→L4 schema rename touches manifest builder + signer + verifier → ≥3 files → Codex mandatory per RETRO-V61-001 new trigger #3.

### Phase 7f: Frontend render consumption (Sprint 2, ~1 day)
- Status: Planned
- Goal: Replace static placeholder flow-field PNGs in `/learn/{case}` with live fetches from 7a's `/api/runs/{run_id}/field-artifacts` + 7b's `/api/runs/{run_id}/renders`.
- Required outputs:
  - `ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx` flow-field block fetches real renders; falls back to reference-run renders if the slider mesh has no artifacts yet
  - `ui/frontend/src/pages/ValidationReportPage.tsx` embeds 7c HTML via iframe or direct component
  - frontend tsc --noEmit clean; visual acceptance via dev server
- Constraints: multi-file frontend change → Codex mandatory per existing trigger. Must not regress the 3 deep-link buttons added in commit 7a3c48b.

### Phase 8 — Delivery hardening
- Status: Active (legacy lane)
- Goal: keep the visual acceptance surface reproducible, cache-resilient, and synced to GitHub/Notion without crossing external-gate boundaries.
- Required outputs: canonical HTML, timestamped snapshot HTML, machine-readable manifest, deep acceptance package, synced control-plane records.
- Frozen governance edges: `Q-1 DHC gold-reference`, `Q-2 R-A-relabel`.

### Phase 9 — Planning only
- Status: Planned
- Goal: comparator/model-routing follow-on work after a fresh activation review.
- Rule: no Phase 9 activation work starts until Phase 8 hardening closes and external-gate constraints are explicitly reviewed.

## Completed

- Phase 1–7: completed and retained as historical implementation/archive context in `.planning/STATE.md`.
- Phase 8 baseline reporting upgrade: landed up to `088e2a3`, including Chinese-first visual acceptance deck and raster evidence panels.

 succeeded in 0ms:
---
gsd_state_version: 1.0
milestone: v1.6.0
milestone_name: milestone
status: unknown
last_updated: "2026-04-21T08:17:39.182Z"
progress:
  total_phases: 7
  completed_phases: 0
  total_plans: 3
  completed_plans: 2
  percent: 67
---

driving_model: claude-opus47-app (Sole Primary Driver under Model Routing v6.1; Codex GPT-5.4-xhigh demoted to Heterogeneous Code Tool, invoked on demand for the three-禁区 src/ · tests/ · knowledge/gold_standards/ perimeter. Notion Gate retained only for 4 hard-floor守护者 duties.)
tier: T3-Orchestrator
last_updated: "2026-04-21T08:30"
session: S-003p OPEN (v6.1 takeover landing + state reconciliation + visual-acceptance iteration audit + Path B UI-MVP Phase 0). Supersedes S-003o. v6.1 cutover: joint Codex↔Claude co-primary (v6.0) retired; Claude APP is now sole primary driver with codex-as-tool access pattern. Hard boundaries remain frozen: Q-1 (DHC gold Path P-1/P-2) and Q-2 (R-A-relabel pipe_flow→duct_flow). Q-3 Notion backfill CLOSED 2026-04-19 / re-closed 2026-04-20 (MCP online). **2026-04-20 pivot — Path B elected (DEC-V61-002)**: project reframes from R&D-harness to Agentic V&V-first commercial workbench; 6-phase MVP begins with Phase 0 (FastAPI backend + Vite/React frontend + Screen 4 Validation Report). Phase 9 "fresh activation review" hold is superseded — Phase 9 scope rolls into the Path-B phase plan.

# Phase Status

current_phase: **Path B — Phase 1..4 UI MVP** (Case Editor + Decisions Queue + Run Monitor + Dashboard) — LANDED on feat/ui-mvp-phase-1-to-4, DEC-V61-003 drafted, PR #3 pending
phase_status: ui/backend ✅ (21/21 pytest green — case_editor 6, decisions/run_monitor/dashboard 8, existing 7) · ui/frontend ✅ (tsc --noEmit clean, vite build ~232KB js gz / ~4KB css gz, 122 modules) · CodeMirror 6 YAML editor + 4-col Kanban + SSE residual streaming + 10-case matrix Dashboard all wired · scripts/start-ui-dev.sh + README UI quickstart + pyproject [ui] dep group landed · Phase 0 PR #2 merged as 6ae6d0b5 · DEC-V61-002 Notion-mirrored
next_phase: Path B — Phase 5 (Audit Package Builder)
next_phase_status: 🔒 BLOCKED on external Gate — Q-1 (DHC gold accuracy) + Q-2 (R-A-relabel pipe→duct) must resolve before signed audit packages can emit (per DEC-V61-002 + DEC-V61-003)
autonomous_governance_counter_v61: 3 (DEC-V61-001 cutover + DEC-V61-002 Path B + DEC-V61-003 Phase 1..4) · hard-floor-4 threshold ≥ 10 still has 7 slots of runway

legacy_phase: Phase 8 — COMPLETE (delivery hardening + control-plane sync; 2026-04-20)
legacy_next_phase_hold: Phase 9 planning-only review is SUPERSEDED by Path B phase plan; Q-1 / Q-2 remain visible in external_gate_queue.md and do not block Path B phases 0..4 (will re-enter at Phase 5 audit-package-signing gate if still open).

Path B phase-plan (DEC-V61-002): P0 UI MVP ⇒ P1 Case Editor ⇒ P2 Decisions Queue ⇒ P3 Run Monitor ⇒ P4 Dashboard ⇒ P5 Audit Package Builder.

Phase 5 Notion: `341c6894-2bed-81c4-9a22-eb6773a6e47c` → Done ✅ (2026-04-15)
Phase 6 Notion: TBD

# Phase 3 — COMPLETE

Phase 3 Notion: `341c6894-2bed-81b8-baa2-eccd49f4993a`

Opus Gate: ⚠️ APPROVED WITH CONDITIONS (2026-04-13) — CFDJerry (T0 proxy)

- Blocking Conditions: C1+C2 DONE
- Non-blocking (Phase 4 scope): C3 (归因链 P0), C4 (3 Docker E2E), C5 (DB cleanup)

Success Criteria:

1. task_runner E2E 闭环验证 (10 cases 全量执行) — ✅ DONE
2. CorrectionSpec 自动生成率 >80% — ⚠️ 70% Mock / >80% expected Docker
3. 知识库自我进化验证 — ✅ DONE (versioning confirmed)
4. 误差自动归因链验证 — ⏳ Deferred to Phase 4 P1

Phase 3 Tasks:

- [P0] 全量E2E闭环验证 — ✅ Done (10/10 executed, 3/10 passed)
- [P0] CorrectionSpec 进化机制 — ✅ Done (versioning confirmed, LDC 3 versions)
- [P1] 误差自动归因链 — ⏳ Ready (deferred to Phase 4)

Phase 3 E2E Results (MockExecutor):
| Case | Execute | Compare | Correction |
|------|---------|---------|------------|
| Lid-Driven Cavity | ✅ | ❌ value_deviation | ✅ |
| Backward-Facing Step | ✅ | ❌ key_mismatch | ✅ |
| Circular Cylinder Wake | ✅ | ✅ | — |
| Turbulent Flat Plate | ✅ | ❌ key_mismatch | ✅ |
| Fully Developed Pipe Flow | ✅ | ❌ key_mismatch | ✅ |
| Differential Heated Cavity | ✅ | ✅ | — |
| Plane Channel Flow (DNS) | ✅ | ❌ key_mismatch | ✅ |
| Axisymmetric Impinging Jet | ✅ | ❌ key_mismatch | ✅ |
| NACA 0012 Airfoil | ✅ | ❌ key_mismatch | ✅ |
| Rayleigh-Bénard Convection | ✅ | ✅ | — |
**TOTAL** | **10/10** | **3/10** | **7** |

CorrectionSpec 70% Root Cause (Session S-002c):

- 6/7: key_mismatch (flow_type preset vs case-specific quantity)
- 1/7: value_deviation (LDC preset vs Ghia 1982 reference)

Phase 4 Conditions (from Gate):

- C3: 误差自动归因链 → Phase 4 P0 (no deferral)
- C4: 3 Docker E2E (LDC/BFS/NC Cavity)
- C5: Phases DB cleanup (Phase 3 Gate archived ✅)

Phase 4 Conditions (from Gate):

- C3: 误差自动归因链 ✅ DONE (AttributionReport + ErrorAttributor)
- C4: 3 Docker E2E ✅ DONE (T2-D implemented: sampleDict + postProcessing解析)
- C5: Phases DB cleanup ✅ DONE

# Phase 4 — IN PROGRESS

Phase 4 Objective: 误差自动归因链 + 真实 Docker E2E 验证

Phase 4 Tasks (Gate Conditions):

- [P0] 误差自动归因链 — ✅ DONE (AttributionReport dataclass + ErrorAttributor engine)
- [P0] 3 Docker E2E (LDC/BFS/NC Cavity) — ✅ DONE
  - LDC: postProcess writeObjects+writeCellCentres 提取 uCenterline → u_centerline 映射
  - BFS: postProcess 提取 wallProfile → reattachment_length 计算 (Ux零交点)
  - NC Cavity: postProcess 提取 midPlaneT → nusselt_number 计算
- [P2] T2-D: OpenFOAM sample utility — ✅ DONE (postProcess替代方案实现完成)
  - system/sampleDict 添加到 LDC/BFS/NC Cavity generators
  - postProcess -funcs '(writeObjects writeCellCentres)' -latestTime 执行
  - _parse_writeobjects_fields 解析场文件并 case-specific 映射到 Gold Standard quantity 名称
  - _copy_postprocess_fields 复制 postProcess 输出到宿主机
- [P1] >80% CorrectionSpec 真实执行验证 — ✅ B1 DONE (LDC Docker E2E 完成)
  - B1 Evidence Chain: solver log → field output → key_quantities → ComparisonResult → AttributionReport
  - nu bug fixed: nu=0.1/Re → Re=100 时 nu=0.001 (之前硬编码 0.01 = Re=10)
  - ResultComparator y-aware interpolation: Gold Standard y 位置线性插值后比较
  - AttributionReport 正确识别 mesh 为 primary cause (coarse mesh → 347% rel_err at Re=100)

Phase 4 B1 Evidence Chain (LDC Re=100 Docker):
| 步骤 | 状态 | 证据 |
|------|------|------|
| Docker 真实执行 | ✅ | success=True, is_mock=False, 7.8s |
| 场提取 (postProcess) | ✅ | u_centerline[17 values], y_centerline[17 values] |
| Gold Standard 对比 | ⚠️ 5 deviations | y-aware interpolation, max 347% @ y=0.5 |
| AttributionReport | ✅ | chain_complete=True, primary=mesh, conf=50% |

Phase 4 B1 Root Cause (BFS/NC Cavity 同理):

- 20×20 mesh 太粗：Re=100 需要更密网格捕捉 secondary vortex
- 修正: nu bug → Re=100 物理量提取正确, u_max≈0.61 合理 (应为 1.0)
- 剩余误差: mesh 分辨率不足 (AttributionReport 建议 ncx/ncy 加倍)

# Phase 2 — COMPLETE

Opus Gate: ✅ APPROVED (2026-04-13) — 5/5 criteria, 10/10 tasks, 103 tests

Success Criteria:

1. ✅ 10+ 成功案例配置模板入库 (10 cases in whitelist.yaml)
2. ✅ 知识库覆盖 3+ geometry 类型 (6 geometry types)
3. ✅ 每条含完整 geometry→turbulence→BC→mesh→result 链路 (10 chains enriched with solver/turbulence_model)
4. ✅ 知识查询 API 可用 (query_cases, get_execution_chain, list_turbulence_models, list_solver_for_geometry)
5. ✅ CorrectionSpec 自动生成 E2E 验证 (Done)

Phase 2 Tasks:

- Backward-Facing Step (Grid Refinement Study) [P1] ✅ Done
- NACA 0012 Airfoil External Flow [P1] ✅ Done
- Verify CorrectionSpec Auto-Generation [P1] ✅ Done
- Natural Convection Cavity (Dhir 2001) [P2] ✅ Done

Phase 2 完成项:

- FoamAgentExecutor BFS support ✅ — single-block rectangular channel, ncx/ncy parameterizable
- FoamAgentExecutor NATURAL_CONVECTION_CAVITY ✅ — buoyantSimpleFoam, 3.97s execution
- Knowledge Query API ✅ — query_cases, get_execution_chain, list_turbulence_models, list_solver_for_geometry
- Knowledge base whitelist.yaml ✅ — expanded to 10 cases (3→10), 6 geometry types
- GeometryType enum 扩展 ✅ — NATURAL_CONVECTION_CAVITY, AIRFOIL, IMPINGING_JET
- FoamAgentExecutor ncx/ncy 参数化 ✅ — 网格无关性研究可用

Phase 2 剩余工作:

- T2-D: Add OpenFOAM sample utility for u_centerline / Xr extraction — ✅ DONE (Phase 4 T2-D, postProcess替代方案)

# Phase 1 — COMPLETE

Opus Gate: ✅ APPROVED (2026-04-13)

- E2E 闭环: Lid-Driven Cavity + Circular Cylinder Wake ✅
- CorrectionSpec 自动生成: ✅ 已测试
- D-001: Deferred to Phase 2+ (internal token sufficient)

# Code Health

tests_passing: 121
tests_total: 120
coverage: 91%
src_loc: 560
git_repo: ✅ kogamishinyajerry-ops/cfd-harness-unified

# Open Decisions

| ID | Topic | Status |
|----|-------|--------|
| D-001 | Notion API token 类型 | ✅ Closed (Deferred to Phase 2+) |
| D-002 | FoamAgentExecutor Docker | ✅ Done |
| D-003 | git repo 独立仓库 | ✅ Done |

# Known Risks

- R1: ✅ notion_client 真实 API
- R2: ⚠️ 容器 cfd-openfoam 必须运行
- R3: ✅ Gold Standards Ghia 1982 / Driver 1985 / Williamson 1996

# Session Summary

S-001: Phase 0 + Phase 1 完成
S-002: Phase 2 启动 — Full Benchmark Suite

# Next Action

Phase 6 COMPLETE (2026-04-16T20:53):

- ✅ turbulent_flat_plate: Docker E2E PASS, cf_skin_friction=0.0027, Gold Std PASS
- ✅ plane_channel_flow: Docker E2E PASS, u_mean_profile, Gold Std PASS
- ✅ rayleigh_benard_convection: FIXED + Docker E2E PASS, nusselt_number=10.5
- ✅ naca0012_airfoil: AIRFOIL fvSolution fix (p-relax 0.3, lower URFs), Docker E2E PASS 286s
- ✅ impinging_jet: Docker E2E PASS, nusselt_number=0.0042, 157s
- ✅ All 121 tests passing
- ⏳ Phase 8 AutoVerifier: SPEC.md ✅, 等待 Opus 4.6 Gate 架构审查

Phase 4 B1 完成 (2026-04-13):

- ✅ nu bug fixed: nu=0.1/Re (was 0.01 hardcoded)
- ✅ y-aware interpolation in ResultComparator
- ✅ LDC Docker E2E 完整证据链: 7.8s exec → u_centerline[17pts] → ComparisonResult → AttributionReport
- ⚠️ LDC comparison: 5/5 deviations (coarse mesh → primary vortex正确, secondary vortex未捕捉)
- ✅ AttributionReport 正确识别 mesh 为 primary cause

Phase 4 C4: BFS + NC Cavity Docker E2E 待验证

Phase 4 C4 Verification (S-002c 续):

- NC Cavity: ✅ Docker E2E SUCCESS (buoyantFoam + Boussinesq, 11s, success=True)
  - 根因: perfectGas/hConst 热力学配置与 buoyantFoam 不兼容
  - 修复: → Boussinesq approximation (equationOfState Boussinesq, rho0=1.177, beta=3e-3)
  - 修复: constant/g 添加 dimensions [0 1 -2 0 0 0 0]
  - 修复: 0/p_rgh 缺失 → 添加 dimensions [1 -1 -2 0 0 0 0], internalField uniform 0
  - 修复: 0/k, 0/omega 缺失 (kOmegaSST 必需) → 添加
  - 修复: fvSchemes 缺少 div(phi,K), div(phi,h) → 添加
  - 修复: fvSolution 缺少 h/hFinal, p_rgh/p_rghFinal solver → 添加
  - 修复: PIMPLE 缺少 pRefCell → 添加
- BFS: ✅ Docker E2E SUCCESS (simpleFoam, 514s, U_residual_magnitude extracted)
  - 注: 简化矩形通道几何导致 reattachment_length 与实际 BFS 有偏差 (预期行为)
- LDC: ✅ Docker E2E SUCCESS (icoFoam, 7.8s, from prior session)
- 3 Docker E2E 全量验证: ✅ 104 tests passing

# Phase 5 — COMPLETE

Phase 5 Notion: `341c6894-2bed-81c4-9a22-eb6773a6e47c` → Done ✅ (2026-04-15)
Phase 5 Objective: 多案例交叉验证 + 知识体系加固

Phase 5 Tasks:

- [T1] 多案例批量E2E验证 — ✅ Done (目标>80%通过率: 9/9 pipeline pass, 4/9 Gold Standard Mock)
- [T2] Gold Standard覆盖率提升 — ✅ Done (8/10 YAML → 10/10 YAML 建设中)
- [T3] 误差模式自动归类 — ✅ Done (2026-04-15)

Phase 5 T3 Implementation (2026-04-15):

- src/error_attributor.py: 5 new ErrorTypes wired into error_type_scores + structured deviation matcher
  - COMPARATOR_SCHEMA_MISMATCH (actual=None) → 0.8 confidence
  - GEOMETRY_MODEL_MISMATCH (reattachment_length on BFS/SIMPLE_GRID) → 0.75
  - INSUFFICIENT_TRANSIENT_SAMPLING (TRANSIENT without strouhal) → 0.75
  - PARAMETER_PLUMBING_MISMATCH (Ra/Re_tau with deviations) → 0.7
  - BUOYANT_ENERGY_SETUP_INCOMPLETE: T/p_rgh/alphat field errors → buoyant_energy_setup_incomplete cause
  - Bug fix: prgh → p_rgh in buoyant_setup regex
- src/correction_recorder.py: 4 structured _infer_error_type branches + 5 new dict entries
- tests/test_error_attributor.py: 7 test cases (all passing)
- 120 tests passing (was 104)

Phase 5 Gaps:

- Gold Standard 数值通过率 44% (仅 Mock 模式)
- Docker 真实执行尚未全量覆盖
- 2 个新 Gold Standard YAML 待写入 (naca0012_airfoil, fully_developed_pipe)


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
/bin/zsh -lc 'git diff --stat' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
 .planning/STATE.md                                 |   6 +-
 reports/cylinder_crossflow/report.md               |   2 +-
 .../deep_acceptance/visual_acceptance_report.html  |  14 ++--
 .../visual_acceptance_report_manifest.json         |  10 +--
 reports/differential_heated_cavity/report.md       |  14 ++--
 reports/rayleigh_benard_convection/report.md       |   2 +-
 reports/turbulent_flat_plate/report.md             |  12 ++--
 scripts/phase5_audit_run.py                        |  43 +++++++++---
 src/foam_agent_adapter.py                          |  22 ++++--
 ui/backend/routes/field_artifacts.py               |  10 ++-
 ui/backend/services/field_artifacts.py             |  75 ++++++++++++++-------
 ui/backend/services/run_ids.py                     |  33 +++++++++
 .../audit_real_run_measurement.yaml                |  11 +--
 ui/backend/tests/test_field_artifacts_route.py     |  33 ++++++++-
 .../circular_cylinder_wake/strouhal_curve.png      | Bin 58628 -> 58684 bytes
 .../lid_driven_cavity/centerline_profiles.png      | Bin 59848 -> 59884 bytes
 .../lid_driven_cavity/stream_function.png          | Bin 138859 -> 138849 bytes
 .../plane_channel_flow/wall_profile.png            | Bin 54582 -> 54685 bytes
 .../rayleigh_benard_convection/nu_ra_scaling.png   | Bin 70766 -> 70843 bytes
 .../turbulent_flat_plate/blasius_profile.png       | Bin 44653 -> 44660 bytes
 .../turbulent_flat_plate/cf_comparison.png         | Bin 67943 -> 67880 bytes
 21 files changed, 207 insertions(+), 80 deletions(-)

codex
The current tree has many unrelated or generated changes, but the Phase 7a review surface is clear: the backend route/service, run-id validation, audit driver, adapter artifact capture, and route tests. I’m now reading those files with line numbers so any verdict is tied to actual code, not the fix summary.
exec
/bin/zsh -lc "sed -n '1,240p' .planning/codebase/ARCHITECTURE.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '1,220p' .planning/codebase/STACK.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
 exited 1 in 0ms:
sed: .planning/codebase/ARCHITECTURE.md: No such file or directory

 exited 1 in 0ms:
sed: .planning/codebase/STACK.md: No such file or directory

exec
/bin/zsh -lc "sed -n '1,220p' .planning/codebase/CONVENTIONS.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
 exited 1 in 0ms:
sed: .planning/codebase/CONVENTIONS.md: No such file or directory

exec
/bin/zsh -lc 'rg --files .planning | sort' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
.planning/PHASE0_CONTEXT_PACK.md
.planning/PROJECT.md
.planning/ROADMAP.md
.planning/STATE.md
.planning/adwm/2026-04-18_activation_plan.md
.planning/d4_plus_rules.yaml
.planning/decisions/2026-04-18_adwm_activation.md
.planning/decisions/2026-04-18_ex1_008_fuse.md
.planning/decisions/2026-04-18_ex1_008_self_approve.md
.planning/decisions/2026-04-18_ex1_009_self_approve.md
.planning/decisions/2026-04-18_ex1_010_self_approve.md
.planning/decisions/2026-04-18_ex1_g3_self_approve.md
.planning/decisions/2026-04-20_a_class_metadata.md
.planning/decisions/2026-04-20_b_class_gold_remediation.md
.planning/decisions/2026-04-20_c3_result_harvest.md
.planning/decisions/2026-04-20_c3a_ldc_gold_anchored.md
.planning/decisions/2026-04-20_c3b_naca_surfaces.md
.planning/decisions/2026-04-20_c3c_impinging_jet.md
.planning/decisions/2026-04-20_c_class_c1_c2.md
.planning/decisions/2026-04-20_path_b_ui_mvp.md
.planning/decisions/2026-04-20_phase_1_to_4_mvp.md
.planning/decisions/2026-04-20_q2_r_a_relabel_path_a.md
.planning/decisions/2026-04-20_v61_cutover.md
.planning/decisions/2026-04-21_phase5_5a_manifest_builder.md
.planning/decisions/2026-04-21_phase5_5b_serialize.md
.planning/decisions/2026-04-21_phase5_5c1_codex_fixes.md
.planning/decisions/2026-04-21_phase5_5c2_m3_mitigation.md
.planning/decisions/2026-04-21_phase5_5c3_warning_class.md
.planning/decisions/2026-04-21_phase5_5c_hmac_sign.md
.planning/decisions/2026-04-21_phase5_5d1_codex_followup.md
.planning/decisions/2026-04-21_phase5_5d_screen6_ui.md
.planning/decisions/2026-04-21_phase5b_ldc_simplefoam_migration.md
.planning/decisions/2026-04-21_phase5b_q5_ldc_gold_closure.md
.planning/decisions/2026-04-21_phase6_foam_adapter_docker_dep.md
.planning/decisions/2026-04-21_phase6_l3_build_fingerprint_rename.md
.planning/decisions/2026-04-21_phase6_td001_bfs_reattachment.md
.planning/decisions/2026-04-21_phase6_td002_duct_flow_dispatch.md
.planning/decisions/2026-04-21_phase6_td024_learn_teaching_runs.md
.planning/decisions/2026-04-21_phase6_td025_learn_full_coverage.md
.planning/decisions/2026-04-21_phase6_td026_learn_mesh_slider.md
.planning/decisions/2026-04-21_phase6_td027_learn_full_depth.md
.planning/decisions/2026-04-21_phase6_td028_q4_bfs_closure.md
.planning/external_gate_queue.md
.planning/gates/Q-2_r_a_relabel.md
.planning/gates/Q-new_whitelist_remediation.md
.planning/handoffs/2026-04-20_claude_code_kickoff.md
.planning/handoffs/2026-04-20_claude_code_mid_session_stop.md
.planning/handoffs/2026-04-21_new_session_kickoff.md
.planning/handoffs/2026-04-21_session_end_kickoff.md
.planning/phase5_audit_package_builder_kickoff.md
.planning/phases/05b-ldc-simplefoam/05b-01-PLAN.md
.planning/phases/05b-ldc-simplefoam/05b-01-SUMMARY.md
.planning/phases/05b-ldc-simplefoam/05b-02-PLAN.md
.planning/phases/05b-ldc-simplefoam/05b-02-SUMMARY.md
.planning/phases/05b-ldc-simplefoam/05b-03-PLAN.md
.planning/phases/05b-ldc-simplefoam/05b-CONTEXT.md
.planning/phases/05b-ldc-simplefoam/05b-RESEARCH.md
.planning/phases/07a-field-capture/07a-01-PLAN.md
.planning/phases/07a-field-capture/07a-01-SUMMARY.md
.planning/phases/07a-field-capture/07a-02-PLAN.md
.planning/phases/07a-field-capture/07a-02-SUMMARY.md
.planning/phases/07a-field-capture/07a-03-PLAN.md
.planning/phases/07a-field-capture/07a-03-SUMMARY.md
.planning/phases/07a-field-capture/07a-CONTEXT.md
.planning/phases/07a-field-capture/07a-RESEARCH.md
.planning/phases/07a-field-capture/_integration_evidence.txt
.planning/retrospectives/2026-04-21_pr22_changes_required_incident_retro.md
.planning/retrospectives/2026-04-21_v61_counter16_retrospective.md
.planning/sessions/S-001_PHASE0_COMPLETE.md

exec
/bin/zsh -lc "rg -n \"field_artifacts|FieldArtifact|resolve_run_parts|parse_run_id|run_id\" ui/backend scripts src tests -g '*.py'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
ui/backend/services/field_artifacts.py:4:(written by scripts/phase5_audit_run.py::_write_field_artifacts_run_manifest),
ui/backend/services/field_artifacts.py:6:the FastAPI route in ui/backend/routes/field_artifacts.py.
ui/backend/services/field_artifacts.py:24:    FieldArtifact,
ui/backend/services/field_artifacts.py:25:    FieldArtifactKind,
ui/backend/services/field_artifacts.py:26:    FieldArtifactsResponse,
ui/backend/services/field_artifacts.py:28:from ui.backend.services.run_ids import parse_run_id
ui/backend/services/field_artifacts.py:30:# Repo root: 3 levels up from this file (ui/backend/services/field_artifacts.py)
ui/backend/services/field_artifacts.py:77:def _classify(filename: str) -> Optional[FieldArtifactKind]:
ui/backend/services/field_artifacts.py:103:def list_artifacts(run_id: str) -> Optional[FieldArtifactsResponse]:
ui/backend/services/field_artifacts.py:104:    """Build the JSON manifest for a run_id. Returns None if no data exists."""
ui/backend/services/field_artifacts.py:105:    case_id, run_label = parse_run_id(run_id)
ui/backend/services/field_artifacts.py:117:    items: list[FieldArtifact] = []
ui/backend/services/field_artifacts.py:131:            FieldArtifact(
ui/backend/services/field_artifacts.py:134:                url=f"/api/runs/{run_id}/field-artifacts/{rel}",
ui/backend/services/field_artifacts.py:141:    return FieldArtifactsResponse(
ui/backend/services/field_artifacts.py:142:        run_id=run_id,
ui/backend/services/field_artifacts.py:150:def resolve_artifact_path(run_id: str, filename: str) -> Path:
ui/backend/services/field_artifacts.py:151:    """Return the on-disk path for {run_id}/{filename}, or raise HTTPException 404.
ui/backend/services/field_artifacts.py:174:    case_id, run_label = parse_run_id(run_id)
scripts/p2_acceptance_run.py:103:            "run_id": f"p2_acc_{case_id}_{commit_sha}",
src/foam_agent_adapter.py:612:                self._capture_field_artifacts(
src/foam_agent_adapter.py:6879:    def _capture_field_artifacts(
src/foam_agent_adapter.py:6986:                f"[WARN] _capture_field_artifacts failed: {e!r}", file=_sys.stderr,
scripts/phase5_audit_run.py:99:def _write_field_artifacts_run_manifest(
scripts/phase5_audit_run.py:148:    field_artifacts_ref: "dict | None" = None,
scripts/phase5_audit_run.py:158:            "run_id": "audit_real_run",
scripts/phase5_audit_run.py:175:            "run_id": f"audit_{case_id}_{commit_sha}",
scripts/phase5_audit_run.py:221:    if field_artifacts_ref is not None:
scripts/phase5_audit_run.py:222:        doc["field_artifacts"] = field_artifacts_ref
scripts/phase5_audit_run.py:277:    # _capture_field_artifacts writes to reports/phase5_fields/{case_id}/{ts}/.
scripts/phase5_audit_run.py:295:    # Phase 7a — write per-run manifest + build field_artifacts_ref dict iff
scripts/phase5_audit_run.py:300:        _write_field_artifacts_run_manifest(case_id, run_label, ts)
scripts/phase5_audit_run.py:304:    field_artifacts_ref: "dict | None" = None
scripts/phase5_audit_run.py:306:        field_artifacts_ref = {
scripts/phase5_audit_run.py:313:        case_id, report, commit_sha, field_artifacts_ref=field_artifacts_ref,
scripts/phase5_audit_run.py:326:        "field_artifacts_manifest": (
ui/backend/services/run_ids.py:1:"""Phase 7a — run_id parsing helper.
ui/backend/services/run_ids.py:3:Per user ratification #5 (2026-04-21): run_id = "{case_id}__{run_label}".
ui/backend/services/run_ids.py:17:# Codex round 1 HIGH #2 (2026-04-21): traversal via run_id reproduced with
ui/backend/services/run_ids.py:40:def parse_run_id(run_id: str) -> tuple[str, str]:
ui/backend/services/run_ids.py:52:    if "__" not in run_id:
ui/backend/services/run_ids.py:55:            detail=f"run_id must match '{{case}}__{{label}}': got {run_id!r}",
ui/backend/services/run_ids.py:57:    case_id, _, run_label = run_id.rpartition("__")
ui/backend/services/run_ids.py:61:            detail=f"run_id has empty case_id or label: {run_id!r}",
tests/test_audit_package/test_sign.py:57:        "run": {"run_id": "r1", "status": "no_run_output"},
src/audit_package/manifest.py:307:    run_id: str,
src/audit_package/manifest.py:323:    run_id
src/audit_package/manifest.py:348:        (e.g., ``sha256(case_id|run_id)[:16]``) to preserve byte
src/audit_package/manifest.py:395:    run_section: Dict[str, Any] = {"run_id": run_id}
src/audit_package/manifest.py:418:        "manifest_id": f"{case_id}-{run_id}",
src/models.py:82:    # FoamAgentExecutor._capture_field_artifacts can stage OpenFOAM field
src/audit_package/serialize.py:240:    run_id = _esc(run.get("run_id") or "—")
src/audit_package/serialize.py:242:    run_kv = {"run_id": run_id, "status": run_status, "solver": solver}
ui/backend/routes/validation.py:20:    run_id: str | None = Query(
ui/backend/routes/validation.py:36:            * ui/backend/tests/fixtures/runs/{case_id}/{run_id}_measurement.yaml
ui/backend/routes/validation.py:40:    report = build_validation_report(case_id, run_id=run_id)
ui/backend/routes/validation.py:46:                + (f", run_id='{run_id}'" if run_id else "")
tests/test_audit_package/test_serialize.py:55:            "run_id": "r1",
tests/test_audit_package/test_serialize.py:190:            "run": {"run_id": "y", "status": "no_run_output"},
tests/test_audit_package/test_manifest.py:242:            run_id="abc123",
tests/test_audit_package/test_manifest.py:272:            run_id="run_xyz",
tests/test_audit_package/test_manifest.py:290:            run_id="m1",
tests/test_audit_package/test_manifest.py:309:            run_id="stable",
tests/test_audit_package/test_manifest.py:337:            run_id="dt",
tests/test_audit_package/test_manifest.py:353:            run_id="r1",
tests/test_audit_package/test_manifest.py:369:            run_id="r1",
ui/backend/routes/field_artifacts.py:3:GET /api/runs/{run_id}/field-artifacts              → JSON manifest
ui/backend/routes/field_artifacts.py:4:GET /api/runs/{run_id}/field-artifacts/{filename}   → FileResponse
ui/backend/routes/field_artifacts.py:16:from ui.backend.schemas.validation import FieldArtifactsResponse
ui/backend/routes/field_artifacts.py:17:from ui.backend.services.field_artifacts import (
ui/backend/routes/field_artifacts.py:42:    "/runs/{run_id}/field-artifacts",
ui/backend/routes/field_artifacts.py:43:    response_model=FieldArtifactsResponse,
ui/backend/routes/field_artifacts.py:46:def get_field_artifacts(run_id: str) -> FieldArtifactsResponse:
ui/backend/routes/field_artifacts.py:47:    """List field artifacts for a given run_id = '{case}__{run_label}'."""
ui/backend/routes/field_artifacts.py:48:    resp = list_artifacts(run_id)
ui/backend/routes/field_artifacts.py:52:            detail=f"no field artifacts for run_id={run_id!r}",
ui/backend/routes/field_artifacts.py:58:    "/runs/{run_id}/field-artifacts/{filename:path}",
ui/backend/routes/field_artifacts.py:61:def download_field_artifact(run_id: str, filename: str) -> FileResponse:
ui/backend/routes/field_artifacts.py:69:    path = resolve_artifact_path(run_id, filename)  # raises HTTPException(404)
ui/backend/routes/audit_package.py:3:    POST /api/cases/{case_id}/runs/{run_id}/audit-package/build
ui/backend/routes/audit_package.py:140:    "/cases/{case_id}/runs/{run_id}/audit-package/build",
ui/backend/routes/audit_package.py:143:def build_audit_package(case_id: str, run_id: str) -> AuditPackageBuildResponse:
ui/backend/routes/audit_package.py:144:    """Build a signed audit package bundle for (case_id, run_id).
ui/backend/routes/audit_package.py:180:        f"{case_id}|{run_id}".encode("utf-8")
ui/backend/routes/audit_package.py:184:    # Phase 5a: when run_id identifies an audit_real_run measurement (captured
ui/backend/routes/audit_package.py:188:    run_doc = _load_run_measurement(case_id, run_id) or {}
ui/backend/routes/audit_package.py:199:        run_id=run_id,
ui/backend/routes/audit_package.py:263:        run_id=run_id,
ui/backend/main.py:53:    field_artifacts,
ui/backend/main.py:90:app.include_router(field_artifacts.router, prefix="/api", tags=["field-artifacts"])
ui/backend/tests/test_field_artifacts_route.py:16:from ui.backend.services.field_artifacts import set_fields_root_for_testing
ui/backend/tests/test_field_artifacts_route.py:40:    assert body["run_id"] == _RUN_ID
ui/backend/tests/test_field_artifacts_route.py:87:def test_manifest_400_or_404_malformed_run_id(client: TestClient) -> None:
ui/backend/tests/test_field_artifacts_route.py:89:    # parse_run_id raises 400; some FastAPI versions wrap as 422. Accept 400 or 404.
ui/backend/tests/test_field_artifacts_route.py:115:    """Codex round 1 HIGH #2: traversal via run_id literal '..' must be rejected."""
ui/backend/tests/test_field_artifacts_route.py:127:    """Codex round 1 HIGH #2: manifest endpoint also guards run_id segments."""
ui/backend/schemas/validation.py:39:  sweep (run_id convention `mesh_<N>` — e.g. `mesh_20`, `mesh_80`). These
ui/backend/schemas/validation.py:54:    run_id: str = Field(..., description="stable id within the case")
ui/backend/schemas/validation.py:156:    run_id: str | None = None
ui/backend/schemas/validation.py:206:FieldArtifactKind = Literal["vtk", "csv", "residual_log"]
ui/backend/schemas/validation.py:207:"""Kind of artifact surfaced by GET /api/runs/{run_id}/field-artifacts.
ui/backend/schemas/validation.py:219:class FieldArtifact(BaseModel):
ui/backend/schemas/validation.py:222:    Paths are served via GET /api/runs/{run_id}/field-artifacts/{filename}
ui/backend/schemas/validation.py:226:    kind: FieldArtifactKind
ui/backend/schemas/validation.py:230:        description="Download URL under /api/runs/{run_id}/field-artifacts/{filename}",
ui/backend/schemas/validation.py:240:class FieldArtifactsResponse(BaseModel):
ui/backend/schemas/validation.py:241:    """Response for GET /api/runs/{run_id}/field-artifacts."""
ui/backend/schemas/validation.py:243:    run_id: str
ui/backend/schemas/validation.py:250:    artifacts: list[FieldArtifact]
ui/backend/tests/test_decisions_and_dashboard.py:92:    # under_resolved / wrong_model runs, surfaced via `run_id=...`.
ui/backend/tests/test_audit_package_route.py:34:            "bundle_id", "manifest_id", "case_id", "run_id", "build_fingerprint",
ui/backend/tests/test_audit_package_route.py:43:        assert body["run_id"] == "r1"
ui/backend/tests/test_audit_package_route.py:99:        """Two POSTs with same (case_id, run_id) → same ZIP SHA-256 + same
ui/backend/tests/test_audit_package_route.py:113:        # build_fingerprint is derived from (case_id, run_id) → must match.
ui/backend/tests/test_audit_package_route.py:122:    def test_different_run_ids_produce_different_bundles(self, client):
ui/backend/tests/test_audit_package_route.py:123:        """Sanity guard: distinct run_ids still diverge (no hash collision)."""
ui/backend/tests/test_audit_package_route.py:241:        """When run_id=audit_real_run, the manifest carries real solver data,
ui/backend/tests/test_audit_package_route.py:270:    def test_unknown_run_id_still_builds_with_empty_measurement(self, client):
ui/backend/tests/test_audit_package_route.py:271:        """Back-compat: non-audit run_ids still produce a valid (signed) bundle
ui/backend/services/validation_report.py:180:    run_id ascending. Empty list if the directory doesn't exist.
ui/backend/services/validation_report.py:188:def _run_id_from_path(p: Path) -> str:
ui/backend/services/validation_report.py:215:    Within a category, sort by run_id ascending (mesh_20 before
ui/backend/services/validation_report.py:217:    Legacy `{case_id}_measurement.yaml` is exposed as run_id='legacy'
ui/backend/services/validation_report.py:228:        run_id = md.get("run_id") or _run_id_from_path(path)
ui/backend/services/validation_report.py:231:                run_id=run_id,
ui/backend/services/validation_report.py:232:                label_zh=md.get("label_zh") or run_id.replace("_", " "),
ui/backend/services/validation_report.py:244:            if r.run_id.startswith("mesh_"):
ui/backend/services/validation_report.py:246:                    n = int(r.run_id.split("_", 1)[1])
ui/backend/services/validation_report.py:249:                return (cat_rank, n, r.run_id)
ui/backend/services/validation_report.py:250:            return (cat_rank, 0, r.run_id)
ui/backend/services/validation_report.py:259:                run_id="legacy",
ui/backend/services/validation_report.py:273:def _load_run_measurement(case_id: str, run_id: str) -> dict[str, Any] | None:
ui/backend/services/validation_report.py:275:    when run_id=='legacy'."""
ui/backend/services/validation_report.py:276:    if run_id == "legacy":
ui/backend/services/validation_report.py:278:    candidate = RUNS_DIR / case_id / f"{run_id}_measurement.yaml"
ui/backend/services/validation_report.py:285:def _pick_default_run_id(case_id: str) -> str | None:
ui/backend/services/validation_report.py:293:            return r.run_id
ui/backend/services/validation_report.py:295:        return runs[0].run_id
ui/backend/services/validation_report.py:539:        run_id=m.get("run_id"),
ui/backend/services/validation_report.py:557:        default_run_id = _pick_default_run_id(cid)
ui/backend/services/validation_report.py:559:            _load_run_measurement(cid, default_run_id) if default_run_id else None
ui/backend/services/validation_report.py:578:            run_doc = _load_run_measurement(cid, r.run_id)
ui/backend/services/validation_report.py:638:    run_id: str | None = None,
ui/backend/services/validation_report.py:643:    - If `run_id` is None, resolves to the first 'reference' run (so
ui/backend/services/validation_report.py:647:    - If `run_id` is provided but doesn't exist, returns None (treat
ui/backend/services/validation_report.py:656:    if run_id is None:
ui/backend/services/validation_report.py:657:        resolved_run_id = _pick_default_run_id(case_id)
ui/backend/services/validation_report.py:659:        resolved_run_id = run_id
ui/backend/services/validation_report.py:661:    if resolved_run_id is None:
ui/backend/services/validation_report.py:665:        measurement_doc = _load_run_measurement(case_id, resolved_run_id)
ui/backend/services/validation_report.py:666:        if measurement_doc is None and run_id is not None:
ui/backend/services/validation_report.py:667:            # User explicitly asked for an unknown run_id.
ui/backend/tests/test_grid_convergence_monotonicity.py:54:def _load_measurement(case_id: str, run_id: str) -> float:
ui/backend/tests/test_grid_convergence_monotonicity.py:55:    path = FIXTURES_ROOT / case_id / f"{run_id}_measurement.yaml"
ui/backend/tests/test_validation_report.py:57:        "/api/validation-report/differential_heated_cavity?run_id=real_incident"
ui/backend/tests/test_validation_report.py:83:        "/api/validation-report/circular_cylinder_wake?run_id=real_incident"
ui/backend/tests/test_validation_report.py:101:        "/api/validation-report/turbulent_flat_plate?run_id=real_incident"
ui/backend/tests/test_validation_report.py:129:def test_validation_report_rejects_unknown_run_id(client: TestClient) -> None:
ui/backend/tests/test_validation_report.py:131:        "/api/validation-report/turbulent_flat_plate?run_id=does_not_exist"
ui/backend/tests/test_validation_report.py:140:    assert any(r["run_id"] == "reference_pass" for r in runs)
ui/backend/tests/test_validation_report.py:141:    assert any(r["run_id"] == "real_incident" for r in runs)
ui/backend/tests/test_validation_report.py:142:    categories = {r["run_id"]: r["category"] for r in runs}
ui/backend/tests/test_validation_report.py:148:    order = [r["run_id"] for r in runs]
ui/backend/tests/test_phase5_byte_repro.py:10:2. `run_metadata.run_id == "audit_real_run"` (not a per-run hash).
ui/backend/tests/test_phase5_byte_repro.py:11:3. `measurement.run_id` and `measurement.commit_sha` track the commit.
ui/backend/tests/test_phase5_byte_repro.py:39:    "run_id",
ui/backend/tests/test_phase5_byte_repro.py:49:    "run_id",
ui/backend/tests/test_phase5_byte_repro.py:85:    assert md["run_id"] == "audit_real_run", (
ui/backend/tests/test_phase5_byte_repro.py:86:        f"{path} run_metadata.run_id must be literally 'audit_real_run' "
ui/backend/tests/test_phase5_byte_repro.py:88:        f"run across commits; got {md['run_id']!r}"
ui/backend/tests/test_phase5_byte_repro.py:108:    assert m["run_id"].startswith(f"audit_{case_id}_"), (
ui/backend/tests/test_phase5_byte_repro.py:109:        f"{path} measurement.run_id must start with audit_{case_id}_; "
ui/backend/tests/test_phase5_byte_repro.py:110:        f"got {m['run_id']!r}"
ui/backend/tests/test_phase5_byte_repro.py:128:        "measurement.run_id",      # contains commit_sha suffix
ui/backend/tests/test_phase5_byte_repro.py:137:        "measurement.run_id",
ui/backend/schemas/audit_package.py:50:    run_id: str
ui/backend/schemas/audit_package.py:54:            "Deterministic 16-hex identifier derived from (case_id, run_id). "

exec
/bin/zsh -lc 'git diff -- ui/backend/services/field_artifacts.py ui/backend/routes/field_artifacts.py ui/backend/services/run_ids.py ui/backend/tests/test_field_artifacts_route.py' in /Users/Zhuanz/Desktop/cfd-harness-unified
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
diff --git a/ui/backend/services/field_artifacts.py b/ui/backend/services/field_artifacts.py
index 002634b..8de864f 100644
--- a/ui/backend/services/field_artifacts.py
+++ b/ui/backend/services/field_artifacts.py
@@ -48,18 +48,20 @@ def set_fields_root_for_testing(path: Optional[Path]) -> None:
 
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
@@ -114,18 +116,22 @@ def list_artifacts(run_id: str) -> Optional[FieldArtifactsResponse]:
 
     items: list[FieldArtifact] = []
     # Walk the whole tree — kind-classify leaves; skip directories.
+    # Codex round 1 HIGH #1 (2026-04-21): use POSIX relative path as filename
+    # so sample/0/uCenterline.xy, sample/500/uCenterline.xy, sample/1000/... are
+    # unique URLs (previously all collapsed to basename and hashes lied).
+    artifact_dir_resolved = artifact_dir.resolve()
     for p in sorted(artifact_dir.rglob("*")):
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
@@ -144,13 +150,25 @@ def list_artifacts(run_id: str) -> Optional[FieldArtifactsResponse]:
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
+        raise HTTPException(status_code=404, detail="artifact not found")
+    decoded = _unquote(filename)
+    if decoded != filename:
+        # Double-encoding attempt — be strict.
+        raise HTTPException(status_code=404, detail="artifact not found")
+    if "\\" in filename or filename.startswith("/"):
         raise HTTPException(status_code=404, detail="artifact not found")
-    if "/" in filename or "\\" in filename or ".." in filename:
+    parts = filename.split("/")
+    if any(p in ("", ".", "..") for p in parts):
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
diff --git a/ui/backend/tests/test_field_artifacts_route.py b/ui/backend/tests/test_field_artifacts_route.py
index f24ab36..28b8a0b 100644
--- a/ui/backend/tests/test_field_artifacts_route.py
+++ b/ui/backend/tests/test_field_artifacts_route.py
@@ -101,15 +101,44 @@ def test_download_residuals_csv_200(client: TestClient) -> None:
 
 
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
 def test_download_404_missing(client: TestClient) -> None:
     r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts/does_not_exist.csv")
     assert r.status_code == 404, r.text

exec
/bin/zsh -lc 'git diff -- scripts/phase5_audit_run.py src/foam_agent_adapter.py ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml' in /Users/Zhuanz/Desktop/cfd-harness-unified
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

codex
The first-pass diff shows the four stated fix areas are present. I’m going to run the backend regression gate fresh and, in parallel, inspect the exact line-numbered implementation for path resolution, manifest writing, and the new tests.
exec
/bin/zsh -lc "nl -ba ui/backend/services/field_artifacts.py | sed -n '1,240p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba ui/backend/routes/field_artifacts.py | sed -n '1,140p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba ui/backend/tests/test_field_artifacts_route.py | sed -n '1,180p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
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
    51	# SHA256 cache keyed on (abs_path, st_mtime_ns, st_size).
    52	# Codex round 1 LOW #4 (2026-04-21): use st_mtime_ns (int) not st_mtime (float)
    53	# so rapid-write timestamp collisions within a float's precision are avoided.
    54	_sha_cache: dict[tuple[str, int, int], str] = {}
    55	
    56	
    57	def sha256_of(path: Path) -> str:
    58	    """Compute (or return cached) SHA256 hex digest for `path`.
    59	
    60	    Cache key: (absolute_path, st_mtime_ns, st_size). Nanosecond-precision
    61	    mtime catches rapid-write edge cases that float st_mtime would miss.
    62	    """
    63	    st = path.stat()
    64	    key = (str(path.resolve()), st.st_mtime_ns, st.st_size)
    65	    cached = _sha_cache.get(key)
    66	    if cached is not None:
    67	        return cached
    68	    h = hashlib.sha256()
    69	    with path.open("rb") as fh:
    70	        for chunk in iter(lambda: fh.read(65536), b""):
    71	            h.update(chunk)
    72	    digest = h.hexdigest()
    73	    _sha_cache[key] = digest
    74	    return digest
    75	
    76	
    77	def _classify(filename: str) -> Optional[FieldArtifactKind]:
    78	    """Map a filename suffix to its kind. Returns None for files we don't surface."""
    79	    low = filename.lower()
    80	    if low.endswith(".vtk") or low.endswith(".vtu") or low.endswith(".vtp"):
    81	        return "vtk"
    82	    if low.endswith(".csv") or low.endswith(".xy") or low.endswith(".dat"):
    83	        # residuals.csv (or anything with 'residual' in the name) is a residual_log.
    84	        if low == "residuals.csv" or "residual" in low:
    85	            return "residual_log"
    86	        return "csv"
    87	    if low.startswith("log.") or low.endswith(".log"):
    88	        return "residual_log"
    89	    return None
    90	
    91	
    92	def _read_run_manifest(case_id: str, run_label: str) -> Optional[dict]:
    93	    root = _current_fields_root()
    94	    manifest_path = root / case_id / "runs" / f"{run_label}.json"
    95	    if not manifest_path.is_file():
    96	        return None
    97	    try:
    98	        return json.loads(manifest_path.read_text(encoding="utf-8"))
    99	    except (json.JSONDecodeError, OSError):
   100	        return None
   101	
   102	
   103	def list_artifacts(run_id: str) -> Optional[FieldArtifactsResponse]:
   104	    """Build the JSON manifest for a run_id. Returns None if no data exists."""
   105	    case_id, run_label = parse_run_id(run_id)
   106	    manifest = _read_run_manifest(case_id, run_label)
   107	    if manifest is None:
   108	        return None
   109	    timestamp = manifest.get("timestamp", "")
   110	    if not timestamp:
   111	        return None
   112	    root = _current_fields_root()
   113	    artifact_dir = root / case_id / timestamp
   114	    if not artifact_dir.is_dir():
   115	        return None
   116	
   117	    items: list[FieldArtifact] = []
   118	    # Walk the whole tree — kind-classify leaves; skip directories.
   119	    # Codex round 1 HIGH #1 (2026-04-21): use POSIX relative path as filename
   120	    # so sample/0/uCenterline.xy, sample/500/uCenterline.xy, sample/1000/... are
   121	    # unique URLs (previously all collapsed to basename and hashes lied).
   122	    artifact_dir_resolved = artifact_dir.resolve()
   123	    for p in sorted(artifact_dir.rglob("*")):
   124	        if not p.is_file():
   125	            continue
   126	        kind = _classify(p.name)
   127	        if kind is None:
   128	            continue
   129	        rel = p.resolve().relative_to(artifact_dir_resolved).as_posix()
   130	        items.append(
   131	            FieldArtifact(
   132	                kind=kind,
   133	                filename=rel,
   134	                url=f"/api/runs/{run_id}/field-artifacts/{rel}",
   135	                sha256=sha256_of(p),
   136	                size_bytes=p.stat().st_size,
   137	            )
   138	        )
   139	    items.sort(key=lambda a: (_KIND_ORDER.get(a.kind, 99), a.filename))
   140	
   141	    return FieldArtifactsResponse(
   142	        run_id=run_id,
   143	        case_id=case_id,
   144	        run_label=run_label,
   145	        timestamp=timestamp,
   146	        artifacts=items,
   147	    )
   148	
   149	
   150	def resolve_artifact_path(run_id: str, filename: str) -> Path:
   151	    """Return the on-disk path for {run_id}/{filename}, or raise HTTPException 404.
   152	
   153	    `filename` may be a POSIX relative path (e.g. `sample/500/uCenterline.xy`)
   154	    after Codex round 1 HIGH #1 fix. Traversal defense:
   155	    - reject empty, '.', '..', backslash, url-encoded '..'
   156	    - reject absolute paths (leading '/')
   157	    - reject any '..' segment
   158	    - verify `resolved.relative_to(artifact_dir.resolve())`
   159	    """
   160	    from urllib.parse import unquote as _unquote
   161	
   162	    if not filename or filename in (".", ".."):
   163	        raise HTTPException(status_code=404, detail="artifact not found")
   164	    decoded = _unquote(filename)
   165	    if decoded != filename:
   166	        # Double-encoding attempt — be strict.
   167	        raise HTTPException(status_code=404, detail="artifact not found")
   168	    if "\\" in filename or filename.startswith("/"):
   169	        raise HTTPException(status_code=404, detail="artifact not found")
   170	    parts = filename.split("/")
   171	    if any(p in ("", ".", "..") for p in parts):
   172	        raise HTTPException(status_code=404, detail="artifact not found")
   173	
   174	    case_id, run_label = parse_run_id(run_id)
   175	    manifest = _read_run_manifest(case_id, run_label)
   176	    if manifest is None:
   177	        raise HTTPException(status_code=404, detail="artifact not found")
   178	    timestamp = manifest.get("timestamp", "")
   179	    if not timestamp:
   180	        raise HTTPException(status_code=404, detail="artifact not found")
   181	    # Codex round 1 HIGH #2: also validate timestamp from manifest (an adversary
   182	    # who writes an adjacent manifest could point timestamp at outside_artifacts).
   183	    if ("/" in timestamp or "\\" in timestamp or ".." in timestamp
   184	            or timestamp in ("", ".", "..")):
   185	        raise HTTPException(status_code=404, detail="artifact not found")
   186	
   187	    root = _current_fields_root()
   188	    root_resolved = root.resolve()
   189	    artifact_dir = root / case_id / timestamp
   190	    if not artifact_dir.is_dir():
   191	        raise HTTPException(status_code=404, detail="artifact not found")
   192	    try:
   193	        artifact_dir.resolve().relative_to(root_resolved)
   194	    except ValueError:
   195	        raise HTTPException(status_code=404, detail="artifact not found")
   196	
   197	    # Compose target and verify it stays inside artifact_dir.
   198	    target = (artifact_dir / filename)
   199	    try:
   200	        resolved = target.resolve(strict=True)
   201	        resolved.relative_to(artifact_dir.resolve())
   202	    except (ValueError, OSError, FileNotFoundError):
   203	        raise HTTPException(status_code=404, detail="artifact not found")
   204	    if not resolved.is_file():
   205	        raise HTTPException(status_code=404, detail="artifact not found")
   206	    return resolved

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
   142	def test_download_404_missing(client: TestClient) -> None:
   143	    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts/does_not_exist.csv")
   144	    assert r.status_code == 404, r.text

exec
/bin/zsh -lc "nl -ba scripts/phase5_audit_run.py | sed -n '80,340p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
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
   141	_PHASE7A_OPTED_IN: frozenset[str] = frozenset({"lid_driven_cavity"})
   142	
   143	
   144	def _audit_fixture_doc(
   145	    case_id: str,
   146	    report,
   147	    commit_sha: str,
   148	    field_artifacts_ref: "dict | None" = None,
   149	) -> dict:
   150	    quantity, value, source_note = _primary_scalar(report)
   151	    comp = report.comparison_result
   152	    passed = comp.passed if comp else False
   153	
   154	    verdict_hint = "PASS" if passed else "FAIL"
   155	
   156	    doc = {
   157	        "run_metadata": {
   158	            "run_id": "audit_real_run",
   159	            "label_zh": "真实 solver 审计运行",
   160	            "label_en": "Real solver audit run",
   161	            "description_zh": (
   162	                f"FoamAgentExecutor 驱动 OpenFOAM 实际跑出的结果（commit {commit_sha}）。"
   163	                "这是 audit package 背书的权威测量——不是合成 fixture。"
   164	                "失败的话说明 case 本身的 physics_contract 在当前 mesh 预算下无法满足，"
   165	                "不是 harness bug；会进入 audit_concerns 随包交付给审查方。"
   166	            ),
   167	            "category": "audit_real_run",
   168	            "expected_verdict": verdict_hint,
   169	        },
   170	        "case_id": case_id,
   171	        "source": "phase5_audit_run_foam_agent",
   172	        "measurement": {
   173	            "value": value if value is not None else 0.0,
   174	            "unit": "dimensionless",
   175	            "run_id": f"audit_{case_id}_{commit_sha}",
   176	            "commit_sha": commit_sha,
   177	            "measured_at": _iso_now(),
   178	            "quantity": quantity,
   179	            "extraction_source": source_note,
   180	            "solver_success": report.execution_result.success,
   181	            "comparator_passed": passed,
   182	        },
   183	        "audit_concerns": [],
   184	        "decisions_trail": [
   185	            {
   186	                "decision_id": "DEC-V61-028",
   187	                "date": "2026-04-21",
   188	                "title": "Phase 5a audit pipeline — real-solver fixtures",
   189	                "autonomous": True,
   190	            }
   191	        ],
   192	    }
   193	
   194	    if comp is not None:
   195	        doc["audit_concerns"].append(
   196	            {
   197	                "concern_type": "CONTRACT_STATUS",
   198	                "summary": (comp.summary or "No summary")[:240],
   199	                "detail": (comp.summary or "")[:2000],
   200	                "decision_refs": ["DEC-V61-028"],
   201	            }
   202	        )
   203	        if comp.deviations:
   204	            # Summarize first 5 deviations for the audit record
   205	            dev_summary = "; ".join(
   206	                f"{d.quantity}: actual={d.actual} expected={d.expected}"
   207	                for d in comp.deviations[:5]
   208	            )
   209	            doc["audit_concerns"].append(
   210	                {
   211	                    "concern_type": "DEVIATIONS",
   212	                    "summary": f"{len(comp.deviations)} deviation(s) over tolerance"[:240],
   213	                    "detail": dev_summary[:2000],
   214	                    "decision_refs": ["DEC-V61-028"],
   215	                }
   216	            )
   217	
   218	    # Phase 7a — field artifacts reference (manifest path only; NO timestamps
   219	    # in the YAML itself so byte-repro stays green per 07a-RESEARCH.md §3.1).
   220	    # The manifest at the referenced path contains the timestamp.
   221	    if field_artifacts_ref is not None:
   222	        doc["field_artifacts"] = field_artifacts_ref
   223	
   224	    return doc
   225	
   226	
   227	def _write_audit_fixture(case_id: str, doc: dict) -> Path:
   228	    case_dir = RUNS_DIR / case_id
   229	    case_dir.mkdir(parents=True, exist_ok=True)
   230	    out_path = case_dir / "audit_real_run_measurement.yaml"
   231	    header = (
   232	        "# Phase 5a audit-real-run fixture — AUTO-GENERATED, DO NOT HAND-EDIT.\n"
   233	        "# Regenerate via:\n"
   234	        f"#   EXECUTOR_MODE=foam_agent .venv/bin/python scripts/phase5_audit_run.py {case_id}\n"
   235	        "# This fixture backs the signed audit package. Byte-identity across\n"
   236	        "# re-runs (modulo timestamp + commit_sha) is enforced by\n"
   237	        "# test_phase5_byte_repro.py.\n\n"
   238	    )
   239	    with out_path.open("w", encoding="utf-8") as fh:
   240	        fh.write(header)
   241	        yaml.safe_dump(doc, fh, allow_unicode=True, sort_keys=False, default_flow_style=False)
   242	    return out_path
   243	
   244	
   245	def _write_raw_capture(case_id: str, report, duration_s: float) -> Path:
   246	    RAW_DIR.mkdir(parents=True, exist_ok=True)
   247	    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
   248	    out = RAW_DIR / f"{ts}_{case_id}_raw.json"
   249	    er = report.execution_result
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
   331	
   332	def main() -> int:
   333	    parser = argparse.ArgumentParser()
   334	    parser.add_argument("cases", nargs="*", help="case ids; use --all for all 10")
   335	    parser.add_argument("--all", action="store_true", help="run all 10 whitelist cases")
   336	    args = parser.parse_args()
   337	
   338	    if os.environ.get("EXECUTOR_MODE", "").lower() != "foam_agent":
   339	        print("ERROR: set EXECUTOR_MODE=foam_agent", file=sys.stderr)
   340	        return 2

exec
/bin/zsh -lc "nl -ba ui/backend/services/run_ids.py | sed -n '1,140p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
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
exec
/bin/zsh -lc "nl -ba src/foam_agent_adapter.py | sed -n '560,640p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
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

exec
/bin/zsh -lc "nl -ba src/foam_agent_adapter.py | sed -n '6860,7005p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
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

exec
/bin/zsh -lc "nl -ba src/foam_agent_adapter.py | sed -n '660,740p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
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
   736	        """生成 Lid-Driven Cavity 最小 OpenFOAM case 文件。"""
   737	        (case_dir / "system").mkdir(parents=True, exist_ok=True)
   738	        (case_dir / "constant").mkdir(parents=True, exist_ok=True)
   739	        (case_dir / "0").mkdir(parents=True, exist_ok=True)
   740	

exec
/bin/zsh -lc 'find reports/phase5_fields/lid_driven_cavity -maxdepth 3 -type f | sort | tail -80' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
reports/phase5_fields/lid_driven_cavity/20260421T082340Z/VTK/ldc_59058_1776759820768_1024.vtk
reports/phase5_fields/lid_driven_cavity/20260421T082340Z/log.simpleFoam
reports/phase5_fields/lid_driven_cavity/20260421T082340Z/residuals.csv
reports/phase5_fields/lid_driven_cavity/runs/audit_real_run.json

exec
/bin/zsh -lc 'rg --files ui/backend/tests/fixtures/phase7a_sample_fields reports/phase5_fields | sort' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
reports/phase5_fields/lid_driven_cavity/20260421T082340Z/VTK/allPatches/allPatches_1024.vtk
reports/phase5_fields/lid_driven_cavity/20260421T082340Z/VTK/ldc_59058_1776759820768_1024.vtk
reports/phase5_fields/lid_driven_cavity/20260421T082340Z/log.simpleFoam
reports/phase5_fields/lid_driven_cavity/20260421T082340Z/residuals.csv
reports/phase5_fields/lid_driven_cavity/20260421T082340Z/residuals/0/residuals.dat
reports/phase5_fields/lid_driven_cavity/20260421T082340Z/sample/0/uCenterline.xy
reports/phase5_fields/lid_driven_cavity/20260421T082340Z/sample/1000/uCenterline.xy
reports/phase5_fields/lid_driven_cavity/20260421T082340Z/sample/500/uCenterline.xy
reports/phase5_fields/lid_driven_cavity/runs/audit_real_run.json
ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/20260421T000000Z/VTK/lid_driven_cavity_2000.vtk
ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/20260421T000000Z/residuals.csv
ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/20260421T000000Z/uCenterline_U_p.xy
ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/runs/audit_real_run.json

 succeeded in 24330ms:
============================= test session starts ==============================
platform darwin -- Python 3.12.13, pytest-9.0.3, pluggy-1.6.0
rootdir: /Users/Zhuanz/Desktop/cfd-harness-unified
configfile: pyproject.toml
plugins: mock-3.15.1, cov-7.1.0, anyio-4.13.0
collected 94 items

ui/backend/tests/test_audit_package_route.py ....................        [ 21%]
ui/backend/tests/test_case_editor.py ......                              [ 27%]
ui/backend/tests/test_case_export.py .............                       [ 41%]
ui/backend/tests/test_decisions_and_dashboard.py ........                [ 50%]
ui/backend/tests/test_field_artifacts_route.py ...............           [ 65%]
ui/backend/tests/test_grid_convergence_monotonicity.py ..........        [ 76%]
ui/backend/tests/test_health.py .                                        [ 77%]
ui/backend/tests/test_phase5_byte_repro.py ............                  [ 90%]
ui/backend/tests/test_validation_report.py .........                     [100%]

============================= 94 passed in 24.12s ==============================

codex
One risk is emerging in the manifest listing path: the download resolver now validates manifest timestamps, but the listing endpoint appears to trust the same timestamp before walking the artifact directory. I’m checking that with a throwaway temp root so I can distinguish a theoretical concern from a reproducible leak.
exec
/bin/zsh -lc "PYTHONPATH=. .venv/bin/python - <<'PY'
from pathlib import Path
from ui.backend.services.field_artifacts import list_artifacts, sha256_of
run_id = 'lid_driven_cavity__audit_real_run'
resp = list_artifacts(run_id)
print('status', 'returned' if resp else 'none')
if resp:
    print('count', len(resp.artifacts))
    print('timestamp', resp.timestamp)
    for a in resp.artifacts:
        print(a.kind, a.filename, a.url, a.sha256[:16], a.size_bytes)
PY" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "PYTHONPATH=. .venv/bin/python - <<'PY'
import json
import tempfile
from pathlib import Path
from ui.backend.services.field_artifacts import list_artifacts, resolve_artifact_path, set_fields_root_for_testing
from fastapi import HTTPException

with tempfile.TemporaryDirectory() as td:
    base = Path(td)
    root = base / 'fields'
    case = root / 'lid_driven_cavity'
    runs = case / 'runs'
    runs.mkdir(parents=True)
    outside = base / 'outside'
    outside.mkdir()
    secret = outside / 'residuals.csv'
    secret.write_text('iter,Ux\\n0,secret\\n', encoding='utf-8')
    (runs / 'audit_real_run.json').write_text(json.dumps({
        'run_label': 'audit_real_run',
        'case_id': 'lid_driven_cavity',
        'timestamp': '../../outside',
    }), encoding='utf-8')
    set_fields_root_for_testing(root)
    try:
        resp = list_artifacts('lid_driven_cavity__audit_real_run')
        print('list_status', 'returned' if resp else 'none')
        if resp:
            print('timestamp', resp.timestamp)
            print('artifacts', [(a.filename, a.size_bytes, a.sha256[:12]) for a in resp.artifacts])
        try:
            resolve_artifact_path('lid_driven_cavity__audit_real_run', 'residuals.csv')
            print('download_status returned')
        except HTTPException as exc:
            print('download_status', exc.status_code)
    finally:
        set_fields_root_for_testing(None)
PY" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 160ms:
list_status returned
timestamp ../../outside
artifacts [('residuals.csv', 17, 'd60ab8be91ff')]
download_status 404

 succeeded in 165ms:
status returned
count 8
timestamp 20260421T082340Z
vtk VTK/allPatches/allPatches_1024.vtk /api/runs/lid_driven_cavity__audit_real_run/field-artifacts/VTK/allPatches/allPatches_1024.vtk a6113287904d744a 45784
vtk VTK/ldc_59058_1776759820768_1024.vtk /api/runs/lid_driven_cavity__audit_real_run/field-artifacts/VTK/ldc_59058_1776759820768_1024.vtk bd454c0b561e06a6 3155888
csv sample/0/uCenterline.xy /api/runs/lid_driven_cavity__audit_real_run/field-artifacts/sample/0/uCenterline.xy c537678e916036fe 9099
csv sample/1000/uCenterline.xy /api/runs/lid_driven_cavity__audit_real_run/field-artifacts/sample/1000/uCenterline.xy bc95a829b8e5c40a 9099
csv sample/500/uCenterline.xy /api/runs/lid_driven_cavity__audit_real_run/field-artifacts/sample/500/uCenterline.xy 6ba22156053d470b 9099
residual_log log.simpleFoam /api/runs/lid_driven_cavity__audit_real_run/field-artifacts/log.simpleFoam a6f33f3c4f6cd94f 490559
residual_log residuals.csv /api/runs/lid_driven_cavity__audit_real_run/field-artifacts/residuals.csv bd734927184e0afd 43972
residual_log residuals/0/residuals.dat /api/runs/lid_driven_cavity__audit_real_run/field-artifacts/residuals/0/residuals.dat 9e0b4a90a3acacc0 55394

codex
Fresh backend tests are green: `94 passed in 24.12s`. The live artifact listing also returns the expected 8 entries with POSIX subpath URLs, including all three `sample/{0,500,1000}/uCenterline.xy` files. One listing-side traversal gap remains, so I’m gathering exact citation ranges and then I’ll return the verdict.
exec
/bin/zsh -lc "nl -ba /Users/Zhuanz/.codex/memories/MEMORY.md | sed -n '356,407p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
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
   407	- Symptom: a future executor infers multi-solver activation from tooling breadcrumbs -> cause: skill inventory mentions SU2/CFX while runtime adapter is still single-engine -> fix: treat those as decision-tree inputs, not implementation approval [Task 2][Task 3]

exec
/bin/zsh -lc "nl -ba /Users/Zhuanz/.codex/memories/rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md | sed -n '61,110p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba /Users/Zhuanz/.codex/memories/rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md | sed -n '1,40p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
    61	
    62	Failures and how to do differently:
    63	- Initial task creation hit a Notion schema mismatch because the Phase relation property expected a string, not a list; retrying with the workspace’s property shape fixed it.
    64	- The page title/summary/roadmap had to be updated in multiple Notion surfaces, not just the phase page itself, to make future recovery reliable.
    65	- There is still a governance tension between the old single-engine redline and the newly surfaced SU2 tooling; future agents should treat that as a deliberate decision-tree problem, not as an implementation green light.
    66	
    67	Reusable knowledge:
    68	- Phase 9 should start from three explicit branches: hold single-engine runtime, allow reference-only external solver surface, or open a bounded proof slice. Anything broader should be rejected until a fresh gate.
    69	- For baseline work, start with log-level / artifact-level capture and a bounded replay manifest before asking for runtime instrumentation.
    70	- The repo execution adapter (`src/foam_agent_adapter.py`) remains OpenFOAM-centered and uses the `cfd-openfoam` container; do not infer broader runtime support from the presence of SU2 tooling in skill inventory.
    71	- The Canonical Docs DB can be used to index planning artifacts so Notion pages can point back to the repo files cleanly.
    72	
    73	References:
    74	- Notion phase page: `Phase 9: 多求解器统一 & LLM 路由稳定化 (草案)` (`45c8b97397ca46f2bef61795d9110715`)
    75	- Notion tasks:
    76	  - `Phase 9a — 外部求解器接入面清点 + SU2/CFX 决策树` (`345c68942bed814693d8dd9b76efb4f6`)
    77	  - `Phase 9b — Model Routing v3.x baseline 采集计划` (`345c68942bed819cac7dd572b80ea8db`)
    78	  - `Phase 9c — Activation Gate 审查包组装` (`345c68942bed8176a085d09f23930a12`)
    79	- Repo artifacts:
    80	  - `docs/design/PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md`
    81	  - `docs/governance/PHASE9_MODEL_ROUTING_BASELINE_PLAN.md`
    82	  - `reports/baselines/phase9_model_routing_replay_manifest.yaml`
    83	  - `docs/gates/PHASE9_ACTIVATION_REVIEW_PACKET.md`
    84	- Repo evidence of existing SU2 tooling: `knowledge/skill_index.yaml` includes `SU2 CLI Harness Skill`; `src/foam_agent_adapter.py` remains OpenFOAM/cfd-openfoam oriented
    85	- Notion Canonical Docs entries were created for the three Phase 9 repo artifacts and linked back to the phase/tasks
    86	
    87	## Task 3: Gate boundary / handoff to Opus 4.7
    88	Outcome: success
    89	
    90	Preference signals:
    91	- The user wanted the work to continue “直至需要Opus 4.7介入”, which means the agent should stop cleanly at the gate and provide a ready-to-paste review prompt rather than drifting into implementation.
    92	
    93	Key steps:
    94	- Verified the new planning artifacts passed simple existence/section/YAML-parse checks.
    95	- Ensured the new files stayed in docs/governance/design/gates and reports/baselines, without touching runtime or tests in this phase.
    96	- Returned a ready-made Opus 4.7 review prompt that summarizes Phase 8 closure, Phase 9 bounded scope, and the explicit allowed/forbidden boundaries.
    97	
    98	Failures and how to do differently:
    99	- The worktree was already dirty from an earlier broad implementation branch; future agents should be extra careful to separate “planning-only” artifacts from any in-flight implementation changes and mention that distinction explicitly when giving the handoff.
   100	
   101	Reusable knowledge:
   102	- When Phase 9 is eventually activated, the safest first scope is `SU2 reference-only`, `CFX hold`, and `routing baseline capture` only.
   103	- Any future executor work should be fenced into a later proof-slice sub-gate, not assumed as part of the default Phase 9 activation.
   104	
   105	References:
   106	- Opus 4.7 handoff prompt was prepared in the rollout and explicitly states Phase 9 remains `Planned` until review returns.
   107	- New planning files were created and indexed, but no runtime files were modified for Phase 9 activation.
   108	

 succeeded in 0ms:
     1	thread_id: 019d973f-efab-7132-bd99-5e0ebb839e12
     2	updated_at: 2026-04-17T05:16:53+00:00
     3	rollout_path: /Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl
     4	cwd: /Users/Zhuanz/Desktop/cfd-harness-unified
     5	git_branch: main
     6	
     7	# Phase 8 was closed out, then Phase 9 was opened in planning-only mode and packaged for an Opus 4.7 activation review.
     8	
     9	Rollout context: The user asked to continue development based on Notion context until Opus 4.7 intervention was required. The work was done in /Users/Zhuanz/Desktop/cfd-harness-unified. The rollout used Notion as SSOT for phase/task status, while the repo remained the code truth source.
    10	
    11	## Task 1: Phase 8 closeout / AutoVerifier package cleanup
    12	Outcome: success
    13	
    14	Preference signals:
    15	- The user repeatedly framed the workflow as “continue推进开发, 直至需要Opus 4.7介入”, which indicates they want the agent to keep pushing forward autonomously until a gate is genuinely reached, rather than stopping early for minor ambiguity.
    16	- The user’s Phase 8 / Phase 9 instructions emphasized “先恢复摘要 + SELF-DISPATCH + 等我回复 GO” and later “继续推进开发，直至需要Opus 4.7介入”, indicating they want explicit gate-aware staging and not silent activation.
    17	
    18	Key steps:
    19	- Read the Notion dashboard, Phase 8/Phase 9 pages, Task #1 contract, and repo-side planning state.
    20	- Corrected Phase 8 status and governance evidence in Notion.
    21	- Kept Phase 8 closeout evidence tied to C15-C17, including the corpus-truth correction (`13/13` vs stale `15/15`), canonical whitelist normalization to `knowledge/whitelist.yaml`, and Canonical Docs `Type=Report` indexing for the three Phase 8 reports.
    22	- Marked Phase 8 as `Done` in Notion after the closeout evidence was in place.
    23	
    24	Failures and how to do differently:
    25	- The Notion contract and repo truth diverged on several paths; future similar runs should treat those as naming drift to normalize, not as blockers, unless they affect runtime or acceptance checks.
    26	- Phase 8 docs were already partially present, so the main job was evidence reconciliation and status closure, not net-new implementation.
    27	
    28	Reusable knowledge:
    29	- The repo active whitelist source is `knowledge/whitelist.yaml`, while older Notion text still references `knowledge/ai_cfd_cold_start_whitelist.yaml`; treat that as contract naming drift unless a fresh gate says otherwise.
    30	- The existing AutoVerifier package already had the right shape: additive hook boundary, suggest-only policy, and contract-aligned Gold Standard aliasing.
    31	- Phase 8 closeout evidence needed to be reflected in both Notion page properties and page body, not just one surface.
    32	
    33	References:
    34	- Notion page: `Phase 8: 平台智能化 — AutoVerifier + 报告引擎 + Skills索引` (`df0228eb22774e3ca32b98e022165277`)
    35	- Notion task: `AutoVerifier 架构设计 + Opus Gate 审查包准备` (`d3ea6e3437804f6f9eaee2d091500c84`)
    36	- Repo docs updated earlier in the session: `docs/specs/AUTO_VERIFIER_SPEC.md`, `docs/design/AUTO_VERIFIER_ARCHITECTURE.md`, `docs/gates/PHASE8A_OPUS_REVIEW_PACKAGE.md`
    37	
    38	## Task 2: Phase 9 planning-only activation prep
    39	Outcome: success
    40	

exec
/bin/zsh -lc "git diff -- ui/backend/services/field_artifacts.py | sed -n '1,220p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
diff --git a/ui/backend/services/field_artifacts.py b/ui/backend/services/field_artifacts.py
index 002634b..8de864f 100644
--- a/ui/backend/services/field_artifacts.py
+++ b/ui/backend/services/field_artifacts.py
@@ -48,18 +48,20 @@ def set_fields_root_for_testing(path: Optional[Path]) -> None:
 
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
@@ -114,18 +116,22 @@ def list_artifacts(run_id: str) -> Optional[FieldArtifactsResponse]:
 
     items: list[FieldArtifact] = []
     # Walk the whole tree — kind-classify leaves; skip directories.
+    # Codex round 1 HIGH #1 (2026-04-21): use POSIX relative path as filename
+    # so sample/0/uCenterline.xy, sample/500/uCenterline.xy, sample/1000/... are
+    # unique URLs (previously all collapsed to basename and hashes lied).
+    artifact_dir_resolved = artifact_dir.resolve()
     for p in sorted(artifact_dir.rglob("*")):
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
@@ -144,13 +150,25 @@ def list_artifacts(run_id: str) -> Optional[FieldArtifactsResponse]:
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
+        raise HTTPException(status_code=404, detail="artifact not found")
+    decoded = _unquote(filename)
+    if decoded != filename:
+        # Double-encoding attempt — be strict.
+        raise HTTPException(status_code=404, detail="artifact not found")
+    if "\\" in filename or filename.startswith("/"):
         raise HTTPException(status_code=404, detail="artifact not found")
-    if "/" in filename or "\\" in filename or ".." in filename:
+    parts = filename.split("/")
+    if any(p in ("", ".", "..") for p in parts):
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


