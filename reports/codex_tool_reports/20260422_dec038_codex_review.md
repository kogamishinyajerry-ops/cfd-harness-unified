2026-04-22T10:43:53.474292Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-research-deerflow/SKILL.md: missing YAML frontmatter delimited by ---
2026-04-22T10:43:53.474312Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-report-pretext/SKILL.md: missing YAML frontmatter delimited by ---
OpenAI Codex v0.118.0 (research preview)
--------
workdir: /Users/Zhuanz/Desktop/cfd-harness-unified
model: gpt-5.4
provider: openai
approval: never
sandbox: read-only
reasoning effort: xhigh
reasoning summaries: none
session id: 019db4ca-0c03-70e3-99a6-272d0612900f
--------
user
# Codex Pre-merge Review — DEC-V61-038 (Convergence Attestor A1..A6)

**Caller**: Claude Code Opus 4.7 (v6.2 Main Driver)
**Target DEC**: DEC-V61-038 — Pre-extraction convergence attestor A1 (solver_exit_clean), A2 (continuity_floor), A3 (residual_floor), A4 (solver_iteration_cap), A5 (bounding_recurrence), A6 (no_progress)
**Self-pass-rate**: 0.65 (≤0.70 triggers pre-merge Codex per RETRO-V61-001)
**Context**: Commits 7f29a64 + eb51dcf + 9716dd4 already landed to main; codex_verdict=pending; backfill pre-merge audit.

## Files to review

Primary:
- `src/convergence_attestor.py` (~609 LOC new CFD module)
- `scripts/phase5_audit_run.py` (attestor integration — runs BEFORE extraction)
- `ui/backend/services/validation_report.py` (new concern codes in hard-FAIL / HAZARD sets)
- `ui/backend/tests/test_convergence_attestor.py` (~394 LOC)
- `knowledge/attestor_thresholds.yaml` (per-case threshold overrides)

Context:
- `.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md` (full DEC with expected verdict table across 10 cases)
- `.planning/decisions/2026-04-22_phase8_dec036b_gates_g3_g4_g5.md` (sibling post-extraction gates)

## Review criteria (CFD physics + log parsing + threshold calibration)

### 1. A1 solver_exit_clean
- Detects `FOAM FATAL IO ERROR`, `FOAM FATAL ERROR`, `Floating exception`, etc.
- Is the regex robust across OpenFOAM versions (v2306/v2312/dev)?
- Docker-swallowed-signal case: does the check read log tail for error strings OR rely on shell exit code? Should be BOTH.

### 2. A2 continuity_floor
- Threshold 1e-4 default; per-case override for cylinder (1e-3 unsteady).
- Overlap with G5 (`sum_local > 1e-2`): A2 HAZARD window is (1e-4, 1e-2]; G5 FAIL is > 1e-2.
- Is the tier split correct? A2=HAZARD does NOT force FAIL — is this intended?

### 3. A3 residual_floor
- Per-field residual targets (Ux/Uy/Uz/p/k/epsilon/omega default 1e-3).
- Per-case overrides: impinging_jet p_rgh 5e-3 (stagnation plateau), rayleigh_benard 2e-3 (oscillatory).
- **Critical**: verify the A3 parser reads the FINAL iteration's `Solving for X, Initial residual = ...` — not an early iter.
- Is per-field threshold lookup correct when case has a field not in defaults (e.g., T for buoyant cases)?

### 4. A4 solver_iteration_cap
- Detects `No Iterations 1000` (or configured cap) in ≥N consecutive outer iterations (N=3 default).
- **Round-2 Codex BLOCKER** (per commit eb51dcf): A4 must detect `p_rgh` cap on buoyantFoam. Verify the regex handles both `GAMG:  Solving for p, ...` and `GAMG:  Solving for p_rgh, ...` variants.
- **Round-2 nit** (commit 9716dd4): PBiCGStab regex ordering — verify regex parses `PBiCGStab:  Solving for X, Initial residual = A, Final residual = B, No Iterations C` with correct field extraction (field name BEFORE numerics).
- Block-counting: "3 consecutive" means truly consecutive outer iterations, or at least 3 hits within last N iters? Spec says consecutive — verify implementation.

### 5. A5 bounding_recurrence
- Counts `bounding X,` lines in last 50 iterations; FAIL if ≥30%.
- Does the windowing correctly identify "last 50 iterations" — by iter number parsed from log, or by line-count scanning from EOF?
- Laminar cases (LDC, DHC): no bounding lines → 0% → pass. Verify.

### 6. A6 no_progress
- Initial residual for any field fluctuates within 1 decade across last 50 iters.
- Sensitive to field selection. Is p_rgh on impinging_jet expected to hit A6? Per spec: impinging_jet A4 fires, A6 does NOT (p_rgh hits cap but each inner cycle decays a decade).
- Verify decade calculation: log10(max/min) > 1.0 → progressing; ≤1.0 → stuck.

### 7. Verdict engine tier split
- A1, A4 → always FAIL (hard)
- A2, A3, A5, A6 → default HAZARD, promotable to FAIL per-case override
- Verify `_derive_contract_status` implements the two-tier logic correctly.
- What happens when multiple concerns fire (A1 FAIL + A3 HAZARD)? Overall = FAIL (max severity).

### 8. LDC regression guard (critical)
- LDC must produce ATTEST_PASS. Is there an explicit integration test reading real LDC log?
- What's the margin? If LDC's actual final p residual is 8e-4 and floor is 1e-3, one noisy run flips it to FAIL. Verify margin is ≥ 2×.

### 9. Per-case YAML robustness
- `knowledge/attestor_thresholds.yaml`: is missing-case handling safe (fall back to defaults silently)?
- Are YAML keys validated against a schema or just dict-lookup?

### 10. Ordering: attestor BEFORE gates
- Spec says attestor runs first, gates second. Does `phase5_audit_run.py` enforce this ordering?
- If attestor short-circuits (ATTEST_FAIL), do gates still run for diagnostic completeness, or skip? Diagnostic completeness is preferred (both tiers populate concerns[] even if verdict is final).

## Expected output format

```
# Codex Review Verdict — DEC-V61-038

**Verdict**: APPROVE / APPROVE_WITH_NOTES / CHANGES_REQUIRED / BLOCK
**Self-pass-rate delta**: claude-estimated=0.65 → codex-independent=0.XX

## Findings

### Must-fix (blocker)
- [finding id] [file:line] [description] [recommended fix]

### Should-fix (nit)
- [finding id] [file:line] [description]

## CFD physics audit per check
- A1: [analysis]
- A2: [analysis]
- A3: [analysis + per-case threshold review]
- A4: [analysis + regex robustness]
- A5: [analysis + window semantics]
- A6: [analysis + decade math]

## Regression guards
- LDC ATTEST_PASS: [pass/fail + margin]
- Tier-split implementation: [correct/incorrect]
- Attestor-before-gates ordering: [correct/incorrect]

## Backward-compat concerns
- [...]

## Recommendation
- Ready for codex_verdict=APPROVED: YES / NO
- If NO, required changes: [...]
```

Be strict. This attestor is the convergence-level defense; a false approval lets non-converged runs pass audit. Target 80-180 lines output.

codex
我会按预合并代码审查来做，重点核对 attestor 的日志解析、阈值分层和执行顺序，并先做一个轻量 memory pass 及代码上下文读取，避免跨仓库指令漂移。
exec
/bin/zsh -lc "sed -n '1,220p' /Users/Zhuanz/.codex/plugins/cache/openai-curated/superpowers/27651a43bf55185d924f7a1fc49043a0a8be65a0/skills/using-superpowers/SKILL.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '1,220p' /Users/Zhuanz/.agents/skills/gsd-code-review/SKILL.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
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
/bin/zsh -lc 'rg -n "cfd-harness-unified|Phase 8|convergence attestor|DEC-V61-038|attestor" /Users/Zhuanz/.codex/memories/MEMORY.md' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
224:- OpenClaw, AI-CFD, Notion作为指挥中枢，Github作为唯一代码真相库, ~/.openclaw/openclaw.json, plugins.allow, openclaw config validate --json, MAIN_OK, CODEX_BUILDER_OK, CLAUDE_REVIEW_OK, NOTION_SYNC_OK, cfd-harness-unified
244:- The real live config surface was `~/.openclaw/openclaw.json`; the actual repo truth for this rollout was `/Users/Zhuanz/Desktop/cfd-harness-unified`, not the chat thread cwd [Task 1]
465:# Task Group: cfd-harness-unified governance closeout and planning gates
467:scope: Close out accepted phases in `cfd-harness-unified`, normalize Notion-vs-repo naming drift, and keep future phases planning-only until the explicit solver/routing gate is reviewed.
468:applies_to: cwd=/Users/Zhuanz/Desktop/cfd-harness-unified; reuse_rule=safe for this repo’s Notion-governed phase/gate work, but phase/task IDs and review packets are rollout-specific.
470:## Task 1: Close Phase 8 and reconcile stale governance evidence
474:- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, Phase 8 closeout and evidence normalization)
478:- Phase 8, AutoVerifier, 13/13, knowledge/whitelist.yaml, ai_cfd_cold_start_whitelist.yaml, Canonical Docs Type=Report, Phase 8 Done, naming drift
484:- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, Phase 9 kept as planning-only with decision-tree packet))
494:- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, handoff prompt prepared instead of silent activation))
548:- rollout_summaries/2026-04-12T15-33-54-ByPi-jerry_ai_cfd_notion_sync_and_cfd_harness_unified_context_mis.md (cwd=/Users/Zhuanz/Documents/20260330 Jerry AI CFD Project, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/12/rollout-2026-04-12T23-33-54-019d8253-fa8b-7f40-9775-46e6e03db8ac.jsonl, updated_at=2026-04-16T17:03:18+00:00, thread_id=019d8253-fa8b-7f40-9775-46e6e03db8ac, later cfd-harness-unified instruction block correctly treated as mismatch)
813:- when the user said "你是 independent approval authority… 你不是 corrected request packet 作者… 你不是 Phase 8 executor" -> preserve strict role separation between approval, review, execution, and freeze authority in this repo [Task 4]

codex
我会按 `using-superpowers` 先做技能判定，再采用 `gsd-code-review` 的 findings-first 审查方式；这次不产出 REVIEW.md，只做行号级结论，因为当前任务是只读预合并审计。
exec
/bin/zsh -lc "sed -n '1,260p' "'$HOME/.Codex/get-shit-done/workflows/code-review.md' in /Users/Zhuanz/Desktop/cfd-harness-unified
 exited 1 in 0ms:
sed: /Users/Zhuanz/.Codex/get-shit-done/workflows/code-review.md: No such file or directory

exec
/bin/zsh -lc "pwd && rg --files .planning src scripts ui/backend/services ui/backend/tests knowledge | rg 'convergence_attestor|phase5_audit_run|validation_report|test_convergence_attestor|attestor_thresholds|2026-04-22_phase8_dec038_convergence_attestor|2026-04-22_phase8_dec036b_gates_g3_g4_g5'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
/Users/Zhuanz/Desktop/cfd-harness-unified
scripts/phase5_audit_run.py
src/convergence_attestor.py
ui/backend/services/validation_report.py
ui/backend/tests/test_validation_report.py
ui/backend/tests/test_convergence_attestor.py
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md
.planning/decisions/2026-04-22_phase8_dec036b_gates_g3_g4_g5.md

codex
我先把 DEC、当前 planning 状态和相关源码一起摊开，随后会针对 A1..A6 和 tier split 逐项交叉对照实现与测试，不靠提交说明做推断。
exec
/bin/zsh -lc "sed -n '1,220p' .planning/STATE.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
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

exec
/bin/zsh -lc "sed -n '1,220p' .planning/PROJECT.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
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

exec
/bin/zsh -lc "sed -n '1,260p' .planning/decisions/2026-04-22_phase8_dec036b_gates_g3_g4_g5.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
---
decision_id: DEC-V61-036b
timestamp: 2026-04-22T11:00 local
scope: |
  Phase 8 Sprint 1 — Hard comparator gates G3/G4/G5 bundled. Sibling DEC
  to DEC-V61-036 (G1 landed). Closes the "honest label, bad physics"
  PASS-washing flavor that G1 did not cover:
    - G3 velocity_overflow: |U|_max > 100·U_ref in last VTK (catches BFS
      U≈1e20, TFP U≈1.1e4).
    - G4 turbulence_negativity: k/epsilon/omega min < 0 at last solver
      iteration OR field max grossly above sanity scale (catches BFS
      epsilon max=1.03e+30, k min=-6.41e+30).
    - G5 continuity_divergence: |sum_local| > 1e-2 OR |cumulative| > 1.0
      (catches BFS sum_local=5.24e+18, cumulative=-1434.64).
  Per Codex round 1 (DEC-V61-036 review) these 3 gates share log-parse +
  VTK-read infrastructure and bundle cleanly. G2 (unit/profile), G6
  (stuck residuals), DEC-V61-038 (attestor) land separately.
autonomous_governance: true
claude_signoff: yes
codex_tool_invoked: pending (pre-merge required; self-pass-rate ≤ 0.70)
codex_rounds: 0
codex_verdict: pending
codex_tool_report_path: []
counter_status: |
  v6.1 autonomous_governance counter 22 → 23 (DEC-V61-036a G1) → 24
  (DEC-V61-036b G3/G4/G5). Next retro at counter=30.
reversibility: |
  Fully reversible. New module src/comparator_gates.py + integration
  calls in phase5_audit_run.py + concern types in _derive_contract_status.
  Revert = 4 files restored. No fixture regeneration required because
  the gates operate on reports/phase5_fields/* and log.simpleFoam which
  are themselves reproducible artifacts.
notion_sync_status: pending
github_pr_url: null (direct-to-main after Codex)
github_merge_sha: pending
github_merge_method: pre-merge Codex verdict required
external_gate_self_estimated_pass_rate: 0.60
  (Three new gates + new module + fixture-writer integration + concern
  schema extension. Threshold calibration is the main risk surface — too
  tight flips LDC to FAIL spuriously; too loose misses the blowups.
  Codex round 1 physics audit on DEC-036 provides ground-truth: gates
  MUST fire on BFS/duct/TFP/cylinder and MUST NOT fire on LDC.)
supersedes: null
superseded_by: null
upstream: |
  - DEC-V61-036 (G1 landed a9d0831 + b3ed913).
  - Codex round-1 CFD physics audit on DEC-V61-036 (2026-04-22):
    BFS + duct + TFP + cylinder fields catastrophic; needs G3+G4+G5.
  - RETRO-V61-001 cadence: gate bundling is OK if each gate has its own
    assertion + test, which this DEC honors.
---

# DEC-V61-036b: Gates G3 + G4 + G5

## Evidence (from Codex round-1 BFS log dump)

```
time step continuity errors : sum local = 5.24523e+18, global = -1328.63, cumulative = -1434.64
bounding epsilon, min: 7.38706e-17 max: 1.03929e+30 average: 1.37234e+27
bounding k, min: -6.41351e+30 max: 2.32895e+31 average: 1.39855e+29
```

BFS simpleFoam kEpsilon ran to `simpleFoam` exit=0 with continuity blown
up by 18 orders of magnitude and k/ε field magnitudes in the 1e+30 range.
Current harness prints "solver completed" and the comparator finds a
`reattachment_length` fallback = 0.04415 ≈ 0 against the gold 6.26, which
G1 now catches. But if a future regression emits `reattachment_length=6.26`
with the same field blowup (e.g., a hardcoded canonical value like
cylinder_wake's Strouhal at `foam_agent_adapter.py:7956`), G1 misses it.
G3/G4/G5 are the defense-in-depth layer.

## Gate definitions

### G3 velocity_overflow
- **Trigger**: `max(|U|)` over final-time VTK cell centres exceeds
  `K * U_ref` (K=100 default, per-case override in future).
- **U_ref**: resolved from `task_spec.boundary_conditions` (inlet U for
  internal, lid U for LDC, free-stream for external). When unresolvable,
  default 1.0 m/s and emit a WARN marker.
- **Fallback when VTK unavailable**: parse epsilon max from
  `bounding epsilon, min: X max: Y` log line at last iter. If Y > 1e+10,
  treat as proxy evidence of velocity overflow since ε ~ u³/L implies
  u ~ ε^(1/3) L^(1/3), and ε=1e+10 with L=O(1) means u=O(1e+3).
- **Decision**: FAIL (not WARN) — a solver that exits 0 with |U| > 100·U_ref
  is not physical.
- **Concern code**: `VELOCITY_OVERFLOW`

### G4 turbulence_negativity
- **Trigger**: any of k, epsilon, omega has a negative minimum at the
  **last reported** `bounding X, min: ..., max: ...` line in the log.
  Silent-clipping during early iters is OK (solver-internal bounding),
  but final-iteration negative values indicate an inconsistent state.
- **Additional trigger**: field max > 1e+10 for k or epsilon (sanity
  overflow, catches BFS case where positive values rocket without ever
  going negative at last iter).
- **Decision**: FAIL.
- **Concern code**: `TURBULENCE_NEGATIVE`

### G5 continuity_divergence
- **Trigger**: last-iteration `sum local` > 1e-2 OR `|cumulative|` > 1.0.
- **Rationale**: for steady incompressible SIMPLE/PISO, sum_local should
  decay to 1e-5 or better at convergence. sum_local=1e-2 already indicates
  the pressure-velocity coupling is broken; `|cumulative|>1.0` is a hard
  divergence signal.
- **Decision**: FAIL.
- **Concern code**: `CONTINUITY_DIVERGED`

## Implementation outline

### New module `src/comparator_gates.py` (~250 LOC)
```python
@dataclass
class GateViolation:
    gate_id: Literal["G3", "G4", "G5"]
    concern_type: str   # VELOCITY_OVERFLOW / TURBULENCE_NEGATIVE / CONTINUITY_DIVERGED
    summary: str
    detail: str
    evidence: dict      # threshold, observed, etc

def parse_solver_log(log_path: Path) -> LogStats:
    """Regex-extract final bounding lines, continuity line, FOAM FATAL
    detection, residual history."""

def read_final_velocity_max(vtk_dir: Path) -> float | None:
    """pyvista read of latest-time VTK; returns max |U| or None if
    unavailable (handled as WARN, not FAIL)."""

def check_all_gates(
    log_path: Path | None,
    vtk_dir: Path | None,
    U_ref: float,
) -> list[GateViolation]:
    violations = []
    log = parse_solver_log(log_path) if log_path and log_path.is_file() else None
    violations.extend(_check_g3_velocity_overflow(log, vtk_dir, U_ref))
    violations.extend(_check_g4_turbulence_negativity(log))
    violations.extend(_check_g5_continuity_divergence(log))
    return violations
```

### Integration at fixture-write time
`scripts/phase5_audit_run.py::_audit_fixture_doc` calls
`check_all_gates(log_path, vtk_dir, U_ref)` after G1 extraction and
stamps each violation as an `audit_concerns[]` entry.

### Verdict engine
`ui/backend/services/validation_report.py::_derive_contract_status`
extends its G1 hard-FAIL concern set to include `VELOCITY_OVERFLOW`,
`TURBULENCE_NEGATIVE`, `CONTINUITY_DIVERGED`.

## Backward compat — expected gate outcomes on current 10 fixtures

| case | G3 | G4 | G5 | current status | post-G1+G345 status |
|---|---|---|---|---|---|
| lid_driven_cavity | pass (|U|≈1.0) | skip (laminar) | pass (sum_local≈1e-6) | FAIL (6 profile pts) | FAIL (G1 ok; profile fails) |
| backward_facing_step | FAIL (ε max=1e+30) | FAIL (k min=-6e+30) | FAIL (cum=-1434) | FAIL via G1 | FAIL via G1+G3+G4+G5 (defense) |
| circular_cylinder_wake | FAIL (Co≈5.9) | FAIL | FAIL (cum≈15.5) | FAIL via G1 | FAIL via G1+G3/4/5 |
| turbulent_flat_plate | FAIL (U≈1.1e4) | FAIL (k≈2e8) | likely FAIL | FAIL (comparator) | FAIL (ditto) |
| duct_flow | FAIL | FAIL | FAIL | FAIL via G1 | FAIL via G1+G3/4/5 |
| differential_heated_cavity | pass (small U) | skip | pass | FAIL (+29%) | FAIL (unchanged) |
| plane_channel_flow | pass | FAIL? | pass? | FAIL via G1 | FAIL via G1 (+ maybe G4) |
| impinging_jet | check | check | depends on stuck res | FAIL (honest label) | FAIL; DEC-038 catches stuck res |
| naca0012_airfoil | pass | pass? | pass | FAIL (3 Cp pts) | FAIL (unchanged) |
| rayleigh_benard_convection | pass | skip | pass | FAIL (Nu+151%) | FAIL (unchanged) |

LDC must stay clean — critical backward-compat assertion.

## Tests

`ui/backend/tests/test_comparator_gates.py` (new):
- `test_g3_velocity_overflow_fail_synthetic_vtk` — crafted VTK with U=500, U_ref=1 → FAIL
- `test_g4_turbulence_negative_at_last_iter_fail` — log with final `bounding k, min: -5.0` → FAIL
- `test_g4_turbulence_max_overflow_fail` — log with `bounding epsilon, min: 1e-5, max: 1e+30` → FAIL
- `test_g5_sum_local_above_1e-2_fail` — log with `sum local = 0.5` → FAIL
- `test_g5_cumulative_above_1_fail` — log with `cumulative = -1434.64` → FAIL
- `test_gates_bfs_integration` — reads the real BFS audit log → 3 violations (G3 proxy + G4 + G5)
- `test_gates_ldc_no_fire` — reads a synthetic clean log → 0 violations
- `test_validation_report_fails_on_gate_concern` — fixture with VELOCITY_OVERFLOW concern → contract_status FAIL

## Counter + Codex

23 → 24. Pre-merge Codex review required (self-pass 0.60).

## Related
- DEC-V61-036 G1 (a9d0831 + b3ed913) — upstream; G1 + G3/4/5 compose AND-gated
- DEC-V61-038 (attestor) — complementary; A1-A6 run pre-extraction, G3/4/5 run post-extraction
- Codex round-1 physics audit on DEC-V61-036 — evidence source

exec
/bin/zsh -lc "sed -n '1,260p' .planning/ROADMAP.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
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
- Status: **SPRINT 1 COMPLETE** (2026-04-21, DEC-V61-031 → DEC-V61-034). All 6 sub-phases (7a..7f) delivered. Tier C visual-only fan-out covers 9 non-LDC cases with real |U| contours + residuals from actual OpenFOAM runs. Tier B per-case gold-overlay (full 8-section report for 9 cases) deferred as Sprint 2 polish (~30hr, user discretion). RETRO-V61-002 landed at counter=20.
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
- Status: COMPLETE (DEC-V61-031, 2026-04-21). 3 waves landed: adapter functions{} + executor capture + driver manifest; backend route/service/18 pytest; Codex 3 rounds → APPROVED_WITH_COMMENTS (2 HIGH security issues caught + fixed: URL basename collision + run_id path-traversal). Real LDC OpenFOAM integration produced 8 artifacts, HTTP manifest + subpath download + traversal 404 verified live. 97/97 pytest. v6.1 counter 16→17.
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
- Status: **COMPLETE incl. polish** (DEC-V61-032 MVP + DEC-V61-033 polish, 2026-04-21). `scripts/render_case_report.py` produces 5 outputs per LDC run. Polish landed: PyVista parse of OpenFOAM volume VTK → 129×129 matplotlib contourf + streamplot (publication-style primary vortex + streamline whorls). LDC-only via RENDER_SUPPORTED_CASES opt-in.
- Goal: New `scripts/render_case_report.py` converts 7a's VTK + CSV into `reports/phase5_renders/{case}/{timestamp}/`: `contour_u.png`, `contour_p.png`, `streamline.png`, `profile_u_centerline.html` (Plotly JSON), `residuals.png`.
- Required outputs:
  - matplotlib for 2D contours (CI-reproducible); PyVista headless (`PYVISTA_OFF_SCREEN=1`) for 3D streamlines
  - Plotly JSON for interactive profile (frontend consumer)
  - Rendering deterministic (fixed seeds, locked matplotlib rcParams)
  - pytest coverage: byte-stable PNG checksum across re-runs on same VTK
- Constraints: new script, no src/ touch → autonomous_governance allowed. Add `pyvista`, `plotly`, `matplotlib` to `pyproject.toml` [render] extra.

### Phase 7c: CFD-vs-gold comparison report template (Sprint 1 MVP + Sprint 2 fan-out, ~3 days)
- Status: **SPRINT 1 + SPRINT 2 TIER C COMPLETE** — DEC-V61-032 (LDC MVP) + DEC-V61-034 (Tier C visual-only fan-out to 9 cases, 2026-04-21). 8-section Jinja2 HTML template + WeasyPrint PDF + reduced visual-only context for non-LDC cases. Codex 4 + 2 rounds (both APPROVED). Tier B Sprint 2 (per-case gold-overlay for 9 cases) remains future work.
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
- Status: **COMPLETE** (DEC-V61-033, 2026-04-21). `ui/backend/services/grid_convergence.py` (~260 LOC, Celik 2008 + Roache 1994) + integration into §7 of 8-section comparison report. Degenerate-case branches: oscillating / converged-to-precision / non-uniform-r overflow / zero-order. 9 unit tests (synthetic 2nd/1st-order + edge-case rejection). LDC live result: p_obs=1.00, GCI_32=5.68%, asymptotic_range_ok=True. Codex round 1 found OverflowError on non-uniform r — fixed with try/except at every `r**p` site + ArithmeticError boundary in comparison_report.
- Goal: Compute observed order of accuracy `p_obs` and Grid Convergence Index `GCI_21` / `GCI_32` from existing `mesh_20/40/80/160` fixtures per Roache 1994.
- Required outputs:
  - `ui/backend/services/grid_convergence.py` implementing Richardson extrapolation + GCI formula
  - New columns in 7c's "grid-convergence table" section
  - pytest coverage: analytic fixture (known p=2 solution) + LDC regression (p_obs should fall in [1.0, 2.0])
- Constraints: pure numerical, no src/ or adapter touch → autonomous_governance allowed.

### Phase 7e: Signed audit-package integration (Sprint 2, ~1 day)
- Status: **COMPLETE** (DEC-V61-033, 2026-04-21). `src/audit_package/manifest.py` + `serialize.py` extended with L4 schema — `phase7` top-level key with {schema_level, canonical_spec, entries[], total_files, total_bytes}. `_PHASE7_TIMESTAMP_RE` shape gate + sanctioned-root containment + resolve+relative_to defense-in-depth. `docs/specs/audit_package_canonical_L4.md` spec. Codex round 1 found CRITICAL serialize/build_manifest repo_root drift (manifest advertised 5 phase7 entries while zip had 0 when non-default repo_root passed) — fixed via `serialize_zip_bytes(manifest, repo_root=None)` kwarg plumbing. 8 unit tests (happy path, traversal rejection, regex gate, opt-out, real-serialize byte equality, byte-reproducibility, repo_root mismatch hazard). Live-verified: 14 files in 1.97 MB bundle with byte-identical SHA256+HMAC across two consecutive builds.
- Goal: Embed 7c PDF + 7b PNG/JSON into HMAC-signed audit-package zip; extend manifest schema to L4 canonical.
- Required outputs:
  - `audit_package.py` manifest `artifacts.field_renders[]` + `artifacts.comparison_report.pdf_sha256` blocks
  - `docs/specs/audit_package_canonical_L4.md` supersedes L3 build_fingerprint spec
  - zip byte-reproducibility preserved (re-run produces identical HMAC)
  - pytest coverage: `test_phase5_byte_repro.py` extended to cover new artifacts
- Constraints: **Byte-reproducibility-sensitive path → Codex mandatory** per RETRO-V61-001 new trigger #2. L3→L4 schema rename touches manifest builder + signer + verifier → ≥3 files → Codex mandatory per RETRO-V61-001 new trigger #3.

### Phase 7f: Frontend render consumption (Sprint 2, ~1 day)
- Status: **MVP COMPLETE (LDC)** — DEC-V61-032, 2026-04-21. `LearnCaseDetailPage.tsx::ScientificComparisonReportSection` fetches `/api/cases/{id}/runs/audit_real_run/comparison-report/context`, renders verdict card + metrics grid + iframe embed of HTML report + "Open in new window" + "Download PDF" buttons. Graceful 404→hide / 5xx→error banner distinction (Codex round 1 MED fix). iframe `sandbox=""` strict. Fan-out to 9 other cases deferred to 7c Sprint 2.
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

exec
/bin/zsh -lc "sed -n '1,260p' .planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
---
decision_id: DEC-V61-038
timestamp: 2026-04-22T11:30 local
scope: |
  Phase 8 Sprint 1 — Pre-extraction convergence attestor A1..A6. Complements
  DEC-V61-036b (post-extraction gates G3/G4/G5). Where G3/G4/G5 say "the
  extracted measurement cannot be trusted because the final-state fields
  are broken", A1..A6 say "the run itself never physically converged even
  if the solver exited 0". Composition is AND-gated: attestor runs first,
  ATTEST_FAIL forces contract FAIL before comparator extraction even looks
  at key_quantities.

  Six checks, all log-based (no separate VTK read — attestor reuses
  comparator_gates.parse_solver_log infrastructure):
    A1 solver_exit_clean   — exit code 0 AND no FOAM FATAL / floating exception in log
    A2 continuity_floor    — final sum_local ≤ case-specific floor (default 1e-4 incompressible)
    A3 residual_floor      — final Ux/Uy/Uz/p/k/epsilon/omega initial residuals ≤ case target (default 1e-3)
    A4 solver_iteration_cap — solver hit max-iteration ceiling (PCG p loops, BiCGStab loops) repeatedly → stuck
    A5 bounding_recurrence — turbulence bounding fired in ≥30% of last N iterations → fake convergence
    A6 no_progress         — initial residuals (any field) did not decay > 1 order over last 50 iterations

  Per RETRO-V61-001, attestor is a separate safety layer from gates — a
  case can have both ATTEST_FAIL (convergence broken) and G3/G4/G5 FAIL
  (final-state broken). UI surfaces both tiers so the audit package
  carries complete diagnostic info.

autonomous_governance: true
claude_signoff: yes
codex_tool_invoked: pending (pre-merge required; self-pass-rate ≤ 0.70)
codex_rounds: 0
codex_verdict: pending
codex_tool_report_path: []
counter_status: |
  v6.1 autonomous_governance counter 24 → 25 after this DEC lands. Retro at 30.
reversibility: |
  Fully reversible. New module src/convergence_attestor.py + integration
  into phase5_audit_run.py + concern types in _derive_contract_status.
  Revert = 3 files + 1 test file restored. No fixture regeneration needed
  because attestor reads reports/phase5_fields/* which is reproducible.
notion_sync_status: pending
github_pr_url: null (direct-to-main after Codex)
github_merge_sha: pending
github_merge_method: pre-merge Codex verdict required
external_gate_self_estimated_pass_rate: 0.65
  (Mostly log-regex work reusing comparator_gates infrastructure. Main
  risk is threshold calibration — specifically A3 residual_floor on
  buoyantFoam which never converges to 1e-5 because radiation/buoyancy
  coupling is inherently oscillatory. DHC case may need a higher floor
  per-case override. Codex physics audit will spot this.)
supersedes: null
superseded_by: null
upstream: |
  - DEC-V61-036b (G3/G4/G5) — sibling post-extraction gates
  - Codex round-1 physics audit on DEC-V61-036: impinging_jet p_rgh hits
    1000 iter (attestor A4 catches); BFS residuals never drop (A6);
    cylinder Co≈5.9 unsteady oscillation (A2 catches but threshold needs
    unsteady-solver override).
---

# DEC-V61-038: Convergence attestor A1..A6

## Why now

G3/G4/G5 tell you the final-state fields are broken. They don't tell you
*why*. Attestor A1..A6 diagnose the convergence process itself:

- A1 catches `FOAM FATAL IO ERROR` in the log tail (solver crashed mid-run
  but exited 0 from the shell's perspective because Docker swallowed the
  signal).
- A2 is the complement of G5 at a tighter threshold: G5 fires on
  `sum_local > 1e-2` (hard divergence); A2 fires on `sum_local > 1e-4`
  (incomplete convergence).
- A3 reads the final-iteration `Solving for Ux/Uy/p/k/epsilon`
  `Initial residual` values and compares against case targets.
- A4 detects solver iteration caps — when `GAMG:  Solving for p, ...
  No Iterations 1000` appears in ≥ 3 consecutive outer iterations, the
  pressure-velocity coupling has failed and the solver is just burning
  time.
- A5 detects turbulence bounding recurrence — healthy cases bound maybe
  10-20% of early iterations then stabilise. Pathological cases bound
  30%+ of the FINAL iterations, indicating the solution never settles.
- A6 detects no-progress convergence — when Initial residual for any
  field fluctuates within a decade across the last 50 iterations, the
  solver is stuck at a residual plateau and "converged" is a lie.

## Design decisions

1. **Attestor runs BEFORE comparator extraction**, inside
   `scripts/phase5_audit_run.py::_audit_fixture_doc` right after
   field_artifacts_ref resolution and before gate checks. This ordering
   lets ATTEST_FAIL propagate into fixture metadata early so downstream
   UI can branch on it.

2. **Concern codes** (all new):
   - A1: `SOLVER_CRASH_LOG` (summary includes first fatal line)
   - A2: `CONTINUITY_NOT_CONVERGED` (vs G5 `CONTINUITY_DIVERGED`)
   - A3: `RESIDUALS_ABOVE_TARGET` (includes which fields missed)
   - A4: `SOLVER_ITERATION_CAP` (includes which solver loop)
   - A5: `BOUNDING_RECURRENT` (includes field + % of iterations bounded)
   - A6: `NO_RESIDUAL_PROGRESS` (includes field + decade range)

3. **Verdict engine integration**: `_derive_contract_status` extends
   hard-FAIL concern set again. HOWEVER — A2/A3/A5/A6 are nuanced:
   some cases genuinely operate at high residuals (impinging jet
   p_rgh equilibrates at 1e-2 due to stagnation). Therefore A2/A3
   default to HAZARD (not FAIL), and can be promoted to FAIL via
   per-case override. A1/A4 are always FAIL (solver crashes / caps
   are never acceptable).

4. **Per-case thresholds** in new `knowledge/attestor_thresholds.yaml`:
   ```yaml
   defaults:
     continuity_floor: 1.0e-4
     residual_floor: 1.0e-3
     iteration_cap_detector_count: 3
     bounding_recurrence_frac_threshold: 0.30
     bounding_recurrence_window: 50
     no_progress_decade_frac: 1.0
     no_progress_window: 50
   per_case:
     impinging_jet:
       # stagnation region — p_rgh plateaus higher
       residual_floor: 5.0e-3
     rayleigh_benard_convection:
       # oscillatory instability — residuals don't decay monotonically
       residual_floor: 2.0e-3
       no_progress_decade_frac: 0.3
     circular_cylinder_wake:
       # unsteady pimpleFoam — continuity oscillates per-step
       continuity_floor: 1.0e-3
   ```

## Expected verdicts on current 10 fixtures

| case | A1 | A2 | A3 | A4 | A5 | A6 | Overall |
|---|---|---|---|---|---|---|---|
| lid_driven_cavity | pass | pass | pass | pass | N/A (laminar) | pass | ATTEST_PASS |
| backward_facing_step | pass | FAIL | FAIL | pass | FAIL | FAIL | ATTEST_FAIL (redundant with G3/G4/G5) |
| circular_cylinder_wake | pass | HAZARD | HAZARD | pass | check | check | ATTEST_HAZARD |
| turbulent_flat_plate | pass | check | check | pass | check | check | expected HAZARD or FAIL |
| duct_flow | pass | FAIL | FAIL | pass | FAIL | FAIL | ATTEST_FAIL (redundant with G3/G4/G5) |
| differential_heated_cavity | pass | pass | check | pass | pass | check | expected HAZARD (Nu off gold but converged) |
| plane_channel_flow | pass | pass | pass | pass | check | pass | ATTEST_PASS (convergence OK; comparator is the problem) |
| impinging_jet | pass | pass | HAZARD | **FAIL** | pass | pass | ATTEST_FAIL via A4 |
| naca0012_airfoil | pass | pass | HAZARD? | pass | pass | pass | ATTEST_PASS or HAZARD |
| rayleigh_benard_convection | pass | HAZARD | HAZARD | pass | pass | check | ATTEST_HAZARD |

Critical: **LDC must stay clean** — it is the gold-overlay PASS reference
and cannot be destabilised by A1..A6 false positives.

## Test plan

`ui/backend/tests/test_convergence_attestor.py` (new):
- Per-check unit tests with synthetic log strings (one per check):
  - A1 log with `FOAM FATAL IO ERROR` → FAIL
  - A2 log with final `sum local = 1e-3` → HAZARD (between A2 and G5 floors)
  - A3 log with final `Solving for Ux, Initial residual = 0.5` → FAIL
  - A4 log with 5 consecutive `No Iterations 1000` → FAIL
  - A5 log with 20/50 `bounding k` lines → FAIL
  - A6 log with Ux residual oscillating 0.4 ± 0.02 for 50 iterations → FAIL
- Per-case integration tests against the current 10 audit logs
  (`reports/phase5_fields/{case}/{ts}/log.*`), asserting the expected
  verdict column above.
- LDC regression: explicit assertion that LDC's actual log produces
  ATTEST_PASS (guard against threshold creep).

## Counter + Codex

24 → 25 after landing. Pre-merge Codex review required (self-pass 0.65).

## Related
- DEC-V61-036 G1 — schema gate (foundational)
- DEC-V61-036b — post-extraction physics gates (sibling)
- DEC-V61-036c (future) — G2 unit canonicalization + comparator u+/y+ fix
- RETRO-V61-001 — governance; this DEC counts +1

exec
/bin/zsh -lc 'cat .planning/config.json' in /Users/Zhuanz/Desktop/cfd-harness-unified
 exited 1 in 0ms:
cat: .planning/config.json: No such file or directory

codex
我已经拿到 DEC 的预期矩阵和 sibling gate 定义。下一步直接读实现与测试，找“规范说的是 consecutive / final iteration / attestor first”，实现是否真的做到。
exec
/bin/zsh -lc "nl -ba src/convergence_attestor.py | sed -n '1,260p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
     1	"""DEC-V61-038: Pre-extraction convergence attestor A1..A6.
     2	
     3	Complements DEC-V61-036b (post-extraction gates G3/G4/G5). Where G3/G4/G5
     4	say "the extracted measurement cannot be trusted because the final-state
     5	fields are broken", A1..A6 say "the run itself never physically converged
     6	even if the solver exited 0".
     7	
     8	Composition with gates:
     9	    solver exit 0
    10	    → attestor.attest(log)    → ATTEST_PASS / HAZARD / FAIL
    11	    → if ATTEST_FAIL: contract FAIL (before extraction)
    12	    → else: comparator_gates.check_all_gates(log, vtk)
    13	    → if any gate: contract FAIL
    14	    → else: comparator verdict
    15	
    16	Checks:
    17	    A1 solver_exit_clean       — no FOAM FATAL / floating exception  → FAIL
    18	    A2 continuity_floor        — final sum_local ≤ case floor        → HAZARD
    19	    A3 residual_floor          — final initial residuals ≤ target    → HAZARD
    20	    A4 solver_iteration_cap    — pressure loop hit cap repeatedly    → FAIL
    21	    A5 bounding_recurrence     — turbulence bounding in last N iters → HAZARD
    22	    A6 no_residual_progress    — residuals stuck at plateau          → HAZARD
    23	
    24	A1/A4 are hard FAIL (solver crashes / caps never acceptable).
    25	A2/A3/A5/A6 default HAZARD; per-case thresholds can promote to FAIL
    26	via knowledge/attestor_thresholds.yaml (not shipped in this DEC —
    27	thresholds live in module constants; future DEC migrates to YAML).
    28	
    29	The attestor returns ATTEST_FAIL if ANY check FAILs; ATTEST_HAZARD if
    30	only HAZARD-tier checks fire; else ATTEST_PASS.
    31	"""
    32	
    33	from __future__ import annotations
    34	
    35	import re
    36	from dataclasses import dataclass, field
    37	from pathlib import Path
    38	from typing import Any, Literal, Optional
    39	
    40	from src.comparator_gates import parse_solver_log
    41	
    42	# ---------------------------------------------------------------------------
    43	# Thresholds (per-case override not wired in this DEC; defaults calibrated
    44	# from Codex round-1 physics audit + BFS/DHC/LDC real logs)
    45	# ---------------------------------------------------------------------------
    46	
    47	A2_CONTINUITY_FLOOR = 1.0e-4           # incompressible steady; G5 fires at 1e-2
    48	A3_RESIDUAL_FLOOR = 1.0e-3             # initial residual of any field
    49	# Codex DEC-038 round-1 BLOCKER 1: A4 regex must cover every pressure
    50	# solver + every pressure field name seen in the real audit logs.
    51	# - Solver types: GAMG, PCG, DICPCG, PBiCG, DILUPBiCGStab
    52	# - Pressure field names: p (incompressible), p_rgh (buoyant), pd
    53	# - Multi-corrector PIMPLE loops emit multiple pressure solves per Time=
    54	#   block; A4 must track BLOCKS not LINES (BLOCKER 2) so consecutive-hit
    55	#   semantics match the DEC's "3 consecutive time steps" intent.
    56	A4_PRESSURE_FIELD_RE = re.compile(
    57	    # Codex DEC-038 round-2 nit: PBiCGStab:... would not match PBiCG
    58	    # alternative because the next char after the 5-letter prefix is 'S'
    59	    # not ':'. List PBiCGStab before PBiCG so regex alternation picks the
    60	    # longer literal first.
    61	    r"(?:GAMG|DICPCG|PCG|PBiCGStab|PBiCG|DILUPBiCGStab|smoothSolver)\s*:\s*"
    62	    r"Solving for\s+(p(?:_rgh|d)?)\s*,"
    63	    r".+?No Iterations\s+(\d+)"
    64	)
    65	A4_ITERATION_CAP_VALUES = (1000, 999, 998)  # solver-reported caps
    66	A4_CONSECUTIVE = 3                     # how many consecutive time-step blocks = FAIL
    67	
    68	A5_BOUNDING_WINDOW = 50                # last N iterations to inspect
    69	A5_BOUNDING_RECURRENCE_FRAC = 0.30     # ≥ 30% of window bounded = HAZARD
    70	
    71	A6_PROGRESS_WINDOW = 50
    72	A6_PROGRESS_DECADE_FRAC = 1.0          # need > 1 decade decay over window
    73	
    74	
    75	AttestVerdict = Literal[
    76	    "ATTEST_PASS",
    77	    "ATTEST_HAZARD",
    78	    "ATTEST_FAIL",
    79	    "ATTEST_NOT_APPLICABLE",  # no log available (reference/visual_only tiers)
    80	]
    81	CheckVerdict = Literal["PASS", "HAZARD", "FAIL"]
    82	
    83	
    84	@dataclass
    85	class AttestorCheck:
    86	    """Single check outcome (A1..A6)."""
    87	
    88	    check_id: str              # "A1" .. "A6"
    89	    concern_type: str          # "SOLVER_CRASH_LOG" / "CONTINUITY_NOT_CONVERGED" / ...
    90	    verdict: CheckVerdict
    91	    summary: str
    92	    detail: str
    93	    evidence: dict = field(default_factory=dict)
    94	
    95	
    96	@dataclass
    97	class AttestationResult:
    98	    """Aggregate attestation: overall verdict + per-check breakdown.
    99	
   100	    `concerns` is the subset of checks whose verdict is HAZARD or FAIL
   101	    (PASS checks are not surfaced in the fixture to avoid clutter).
   102	    """
   103	
   104	    overall: AttestVerdict
   105	    checks: list[AttestorCheck] = field(default_factory=list)
   106	
   107	    @property
   108	    def concerns(self) -> list[AttestorCheck]:
   109	        return [c for c in self.checks if c.verdict != "PASS"]
   110	
   111	
   112	# ---------------------------------------------------------------------------
   113	# Per-check regexes (reuse parse_solver_log output where possible)
   114	# ---------------------------------------------------------------------------
   115	
   116	_INITIAL_RESIDUAL_RE = re.compile(
   117	    r"Solving for\s+(\w+),\s*Initial residual\s*=\s*([\deE+.\-]+),"
   118	    r"\s*Final residual\s*=\s*([\deE+.\-]+),\s*No Iterations\s+(\d+)"
   119	)
   120	
   121	_BOUNDING_LINE_RE = re.compile(r"^\s*bounding\s+(k|epsilon|omega|nuTilda|nut)\b")
   122	# OpenFOAM writes `Time = 123` on its own line AND as `Time = 123s` with
   123	# trailing `s`. Accept either form; trailing whitespace tolerated.
   124	_TIME_STEP_RE = re.compile(r"^Time\s*=\s*[\deE+.\-]+s?\s*$")
   125	
   126	
   127	def _parse_residual_timeline(log_path: Path) -> dict[str, list[float]]:
   128	    """Extract per-field Initial residual history across all iterations.
   129	
   130	    Returns {"Ux": [...], "Uy": [...], "p": [...], "k": [...], "epsilon": [...]}.
   131	    Order preserves the log's iteration order. Used by A3 + A6.
   132	    """
   133	    timeline: dict[str, list[float]] = {}
   134	    with log_path.open("r", encoding="utf-8", errors="replace") as fh:
   135	        for line in fh:
   136	            m = _INITIAL_RESIDUAL_RE.search(line)
   137	            if not m:
   138	                continue
   139	            field_name = m.group(1)
   140	            try:
   141	                r0 = float(m.group(2))
   142	            except ValueError:
   143	                continue
   144	            timeline.setdefault(field_name, []).append(r0)
   145	    return timeline
   146	
   147	
   148	def _parse_iteration_caps_per_block(log_path: Path) -> list[int]:
   149	    """Return per-`Time = ...` block the MAX pressure-solver iteration count
   150	    seen inside that block.
   151	
   152	    Codex DEC-038 round-1 BLOCKER 2: A4 must count consecutive TIME STEPS
   153	    (outer iterations), not consecutive solve lines — PIMPLE multi-corrector
   154	    loops emit ≥2 pressure solves per block and the prior line-based count
   155	    would false-fire after 1.5 blocks. Returns one entry per block; a
   156	    block's count is the worst (max) pressure iteration count seen in it.
   157	    Blocks with no pressure solve get -1 (skipped by A4).
   158	    """
   159	    per_block_max: list[int] = []
   160	    current_max: int = -1
   161	    seen_any = False
   162	    with log_path.open("r", encoding="utf-8", errors="replace") as fh:
   163	        for line in fh:
   164	            if _TIME_STEP_RE.match(line):
   165	                if seen_any:
   166	                    per_block_max.append(current_max)
   167	                current_max = -1
   168	                seen_any = True
   169	                continue
   170	            m = A4_PRESSURE_FIELD_RE.search(line)
   171	            if m:
   172	                try:
   173	                    count = int(m.group(2))
   174	                except ValueError:
   175	                    continue
   176	                if count > current_max:
   177	                    current_max = count
   178	        if seen_any:
   179	            per_block_max.append(current_max)
   180	    return per_block_max
   181	
   182	
   183	def _parse_bounding_lines_per_step(log_path: Path) -> list[set[str]]:
   184	    """Return list of sets, one per `Time =` block, containing fields that
   185	    bounded in that block. Used by A5.
   186	    """
   187	    blocks: list[set[str]] = [set()]
   188	    with log_path.open("r", encoding="utf-8", errors="replace") as fh:
   189	        for line in fh:
   190	            if _TIME_STEP_RE.match(line):
   191	                blocks.append(set())
   192	                continue
   193	            m = _BOUNDING_LINE_RE.match(line)
   194	            if m:
   195	                blocks[-1].add(m.group(1))
   196	    # Drop leading empty block before first `Time =`.
   197	    if blocks and not blocks[0]:
   198	        blocks.pop(0)
   199	    return blocks
   200	
   201	
   202	# ---------------------------------------------------------------------------
   203	# Individual checks
   204	# ---------------------------------------------------------------------------
   205	
   206	def _check_a1_solver_crash(log_path: Path) -> AttestorCheck:
   207	    stats = parse_solver_log(log_path)
   208	    if stats.fatal_detected:
   209	        return AttestorCheck(
   210	            check_id="A1",
   211	            concern_type="SOLVER_CRASH_LOG",
   212	            verdict="FAIL",
   213	            summary=(
   214	                stats.fatal_lines[0][:240] if stats.fatal_lines
   215	                else "FOAM FATAL detected in log"
   216	            ),
   217	            detail=(
   218	                "DEC-V61-038 A1: solver log contains a FOAM FATAL / IO ERROR / "
   219	                "floating exception marker. Even if the shell exit code was 0 "
   220	                "(which can happen under Docker signal handling), the solver's "
   221	                "own diagnostic says the run aborted abnormally. Any measurement "
   222	                "from this run is unreliable."
   223	            )[:2000],
   224	            evidence={"fatal_lines": stats.fatal_lines[:3]},
   225	        )
   226	    return AttestorCheck(
   227	        check_id="A1", concern_type="SOLVER_CRASH_LOG", verdict="PASS",
   228	        summary="no FOAM FATAL / floating exception in log",
   229	        detail="",
   230	    )
   231	
   232	
   233	def _check_a2_continuity_floor(log_path: Path) -> AttestorCheck:
   234	    stats = parse_solver_log(log_path)
   235	    sl = stats.final_continuity_sum_local
   236	    if sl is None:
   237	        return AttestorCheck(
   238	            check_id="A2", concern_type="CONTINUITY_NOT_CONVERGED", verdict="PASS",
   239	            summary="no continuity line in log (case may not report it)",
   240	            detail="",
   241	        )
   242	    if sl > A2_CONTINUITY_FLOOR:
   243	        # Codex DEC-038 round-1 A2/G5 split-brain comment: A2 stays strictly
   244	        # HAZARD here to avoid conflict with G5, which hard-FAILs
   245	        # `sum_local > 1e-2` on the gate side. Keeping A2 as HAZARD means
   246	        # the attestor tier is purely diagnostic; the FAIL call belongs to
   247	        # the gate layer. Previously A2 returned FAIL for >1e-2, but the
   248	        # verdict engine did not hard-FAIL on CONTINUITY_NOT_CONVERGED, so
   249	        # the semantics split across layers. Now A2 is always HAZARD-tier.
   250	        verdict: CheckVerdict = "HAZARD"
   251	        return AttestorCheck(
   252	            check_id="A2",
   253	            concern_type="CONTINUITY_NOT_CONVERGED",
   254	            verdict=verdict,
   255	            summary=(f"final sum_local={sl:.3g} > floor {A2_CONTINUITY_FLOOR:.0e}")[:240],
   256	            detail=(
   257	                f"DEC-V61-038 A2: incompressible steady continuity error at "
   258	                f"convergence should be ≤ {A2_CONTINUITY_FLOOR:.0e}. Observed "
   259	                f"final sum_local={sl:.6g}. Values between {A2_CONTINUITY_FLOOR:.0e} "
   260	                f"and 1e-2 are HAZARD (marginal convergence); >1e-2 is FAIL "

exec
/bin/zsh -lc "nl -ba src/convergence_attestor.py | sed -n '521,760p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   521	        "attestor_check_id": c.check_id,
   522	        "attestor_verdict": c.verdict,
   523	    }

exec
/bin/zsh -lc "nl -ba src/convergence_attestor.py | sed -n '261,520p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   261	                "(DEC-036b G5 also fires)."
   262	            )[:2000],
   263	            evidence={"sum_local": sl, "threshold": A2_CONTINUITY_FLOOR},
   264	        )
   265	    return AttestorCheck(
   266	        check_id="A2", concern_type="CONTINUITY_NOT_CONVERGED", verdict="PASS",
   267	        summary=f"final sum_local={sl:.3g} ≤ {A2_CONTINUITY_FLOOR:.0e}",
   268	        detail="",
   269	    )
   270	
   271	
   272	def _check_a3_residual_floor(log_path: Path) -> AttestorCheck:
   273	    timeline = _parse_residual_timeline(log_path)
   274	    if not timeline:
   275	        return AttestorCheck(
   276	            check_id="A3", concern_type="RESIDUALS_ABOVE_TARGET", verdict="PASS",
   277	            summary="no residual lines parsed from log",
   278	            detail="",
   279	        )
   280	    offenders: dict[str, float] = {}
   281	    for field_name, history in timeline.items():
   282	        last = history[-1]
   283	        if last > A3_RESIDUAL_FLOOR:
   284	            offenders[field_name] = last
   285	    if offenders:
   286	        sorted_off = sorted(offenders.items(), key=lambda kv: -kv[1])
   287	        summary = (
   288	            f"final residuals above {A3_RESIDUAL_FLOOR:.0e}: "
   289	            + ", ".join(f"{k}={v:.3g}" for k, v in sorted_off[:3])
   290	        )[:240]
   291	        return AttestorCheck(
   292	            check_id="A3", concern_type="RESIDUALS_ABOVE_TARGET",
   293	            verdict="HAZARD",
   294	            summary=summary,
   295	            detail=(
   296	                "DEC-V61-038 A3: at convergence, SIMPLE/PISO initial residuals "
   297	                f"should be ≤ {A3_RESIDUAL_FLOOR:.0e}. Fields listed above have "
   298	                "final-iteration Initial residuals exceeding that floor. This "
   299	                "may be physically expected for some cases (impinging_jet "
   300	                "p_rgh, RBC oscillatory modes) — HAZARD not FAIL until a "
   301	                "per-case override promotes it."
   302	            )[:2000],
   303	            evidence={"offenders": offenders, "threshold": A3_RESIDUAL_FLOOR},
   304	        )
   305	    return AttestorCheck(
   306	        check_id="A3", concern_type="RESIDUALS_ABOVE_TARGET", verdict="PASS",
   307	        summary=f"all residuals ≤ {A3_RESIDUAL_FLOOR:.0e}",
   308	        detail="",
   309	    )
   310	
   311	
   312	def _check_a4_iteration_cap(log_path: Path) -> AttestorCheck:
   313	    per_block = _parse_iteration_caps_per_block(log_path)
   314	    # Drop blocks with no pressure solve (current_max == -1).
   315	    blocks_with_solves = [b for b in per_block if b >= 0]
   316	    if not blocks_with_solves:
   317	        return AttestorCheck(
   318	            check_id="A4", concern_type="SOLVER_ITERATION_CAP", verdict="PASS",
   319	            summary="no pressure solver iteration counts in log",
   320	            detail="",
   321	        )
   322	    consecutive = 0
   323	    for b_max in blocks_with_solves:
   324	        if b_max in A4_ITERATION_CAP_VALUES or b_max >= 1000:
   325	            consecutive += 1
   326	            if consecutive >= A4_CONSECUTIVE:
   327	                return AttestorCheck(
   328	                    check_id="A4", concern_type="SOLVER_ITERATION_CAP",
   329	                    verdict="FAIL",
   330	                    summary=(
   331	                        f"pressure solver hit {b_max} iterations in "
   332	                        f"≥ {A4_CONSECUTIVE} consecutive time-step blocks"
   333	                    )[:240],
   334	                    detail=(
   335	                        "DEC-V61-038 A4: pressure-velocity solver loop is "
   336	                        f"hitting its iteration cap (~{b_max}) in at least "
   337	                        f"{A4_CONSECUTIVE} consecutive time-step blocks "
   338	                        "(Time = ... dividers). SIMPLE/PISO/PIMPLE coupling "
   339	                        "has effectively failed — the solver is burning CPU "
   340	                        "without reducing the residual. Hard FAIL."
   341	                    )[:2000],
   342	                    evidence={
   343	                        "consecutive_cap_blocks": consecutive,
   344	                        "final_cap_value": b_max,
   345	                        "total_blocks": len(blocks_with_solves),
   346	                    },
   347	                )
   348	        else:
   349	            consecutive = 0
   350	    return AttestorCheck(
   351	        check_id="A4", concern_type="SOLVER_ITERATION_CAP", verdict="PASS",
   352	        summary=f"pressure solver peaked at {max(blocks_with_solves)} iterations",
   353	        detail="",
   354	    )
   355	
   356	
   357	def _check_a5_bounding_recurrence(log_path: Path) -> AttestorCheck:
   358	    blocks = _parse_bounding_lines_per_step(log_path)
   359	    if len(blocks) < 5:
   360	        # Too few time steps to judge recurrence.
   361	        return AttestorCheck(
   362	            check_id="A5", concern_type="BOUNDING_RECURRENT", verdict="PASS",
   363	            summary=f"only {len(blocks)} time-step blocks parsed",
   364	            detail="",
   365	        )
   366	    window = blocks[-A5_BOUNDING_WINDOW:]
   367	    if not window:
   368	        return AttestorCheck(
   369	            check_id="A5", concern_type="BOUNDING_RECURRENT", verdict="PASS",
   370	            summary="no final-window blocks",
   371	            detail="",
   372	        )
   373	    per_field_frac: dict[str, float] = {}
   374	    for field_name in ("k", "epsilon", "omega", "nuTilda", "nut"):
   375	        bounded_count = sum(1 for b in window if field_name in b)
   376	        if bounded_count == 0:
   377	            continue
   378	        frac = bounded_count / len(window)
   379	        per_field_frac[field_name] = frac
   380	    offenders = {k: v for k, v in per_field_frac.items()
   381	                 if v >= A5_BOUNDING_RECURRENCE_FRAC}
   382	    if offenders:
   383	        top = max(offenders.items(), key=lambda kv: kv[1])
   384	        return AttestorCheck(
   385	            check_id="A5", concern_type="BOUNDING_RECURRENT",
   386	            verdict="HAZARD",
   387	            summary=(
   388	                f"{top[0]} bounded in {top[1]*100:.0f}% of last "
   389	                f"{len(window)} iterations (threshold "
   390	                f"{A5_BOUNDING_RECURRENCE_FRAC*100:.0f}%)"
   391	            )[:240],
   392	            detail=(
   393	                "DEC-V61-038 A5: turbulence field is being clipped in a large "
   394	                f"fraction of the FINAL {len(window)} iterations. Healthy "
   395	                "convergence shows bounding events in early transients then "
   396	                "stabilises. Recurrent bounding in the tail indicates the "
   397	                "solution never settles — 'converged' residuals are an artefact "
   398	                "of clipping, not physical equilibrium."
   399	            )[:2000],
   400	            evidence={"per_field_fraction": per_field_frac, "window": len(window)},
   401	        )
   402	    return AttestorCheck(
   403	        check_id="A5", concern_type="BOUNDING_RECURRENT", verdict="PASS",
   404	        summary=(
   405	            f"bounding fractions in last {len(window)} iters: "
   406	            + ", ".join(f"{k}={v:.0%}" for k, v in per_field_frac.items())
   407	            if per_field_frac else f"no bounding in last {len(window)} iters"
   408	        )[:240],
   409	        detail="",
   410	    )
   411	
   412	
   413	def _check_a6_no_progress(log_path: Path) -> AttestorCheck:
   414	    timeline = _parse_residual_timeline(log_path)
   415	    if not timeline:
   416	        return AttestorCheck(
   417	            check_id="A6", concern_type="NO_RESIDUAL_PROGRESS", verdict="PASS",
   418	            summary="no residuals parsed",
   419	            detail="",
   420	        )
   421	    offenders: dict[str, dict[str, float]] = {}
   422	    for field_name, history in timeline.items():
   423	        if len(history) < A6_PROGRESS_WINDOW:
   424	            continue
   425	        window = history[-A6_PROGRESS_WINDOW:]
   426	        lo = min(window)
   427	        hi = max(window)
   428	        if lo <= 0 or hi <= 0:
   429	            continue
   430	        # A6 only fires when residuals are STUCK AT A HIGH PLATEAU — i.e.,
   431	        # still above the A3 floor. If residuals have already decayed to
   432	        # convergence (< 1e-3), a small decade-range in the tail is just
   433	        # machine-noise fluctuation, not "stuck". Guard against this
   434	        # false positive (caught on LDC: Ux plateaued at 1e-5 with 0.02
   435	        # decades range — that's converged, not stuck).
   436	        if hi < A3_RESIDUAL_FLOOR:
   437	            continue
   438	        decades = math_log10(hi / lo) if hi > lo else 0.0
   439	        if decades < A6_PROGRESS_DECADE_FRAC:
   440	            offenders[field_name] = {"decades": decades, "lo": lo, "hi": hi}
   441	    if offenders:
   442	        worst = min(offenders.items(), key=lambda kv: kv[1]["decades"])
   443	        return AttestorCheck(
   444	            check_id="A6", concern_type="NO_RESIDUAL_PROGRESS",
   445	            verdict="HAZARD",
   446	            summary=(
   447	                f"{worst[0]} residual range over last "
   448	                f"{A6_PROGRESS_WINDOW} iters: "
   449	                f"{worst[1]['lo']:.2e} – {worst[1]['hi']:.2e} "
   450	                f"({worst[1]['decades']:.2f} decades)"
   451	            )[:240],
   452	            detail=(
   453	                "DEC-V61-038 A6: initial residuals for the fields listed "
   454	                f"above did not decay > {A6_PROGRESS_DECADE_FRAC:.1f} decade(s) "
   455	                f"over the last {A6_PROGRESS_WINDOW} iterations. Solver is "
   456	                "stuck at a plateau; any scalar extracted from this 'converged' "
   457	                "state is physically ambiguous."
   458	            )[:2000],
   459	            evidence={"offenders": offenders, "window": A6_PROGRESS_WINDOW},
   460	        )
   461	    return AttestorCheck(
   462	        check_id="A6", concern_type="NO_RESIDUAL_PROGRESS", verdict="PASS",
   463	        summary="all residual histories show > 1 decade decay in tail window",
   464	        detail="",
   465	    )
   466	
   467	
   468	def math_log10(x: float) -> float:
   469	    """log10 with a zero-guard. Inlined to avoid a dependency in this module."""
   470	    import math
   471	    if x <= 0:
   472	        return 0.0
   473	    return math.log10(x)
   474	
   475	
   476	# ---------------------------------------------------------------------------
   477	# Public entry point
   478	# ---------------------------------------------------------------------------
   479	
   480	def attest(log_path: Optional[Path]) -> AttestationResult:
   481	    """Run A1..A6 against a solver log; aggregate into an AttestationResult.
   482	
   483	    Codex DEC-038 round-1 comment C: distinguish "clean PASS" (log was
   484	    read, all checks pass) from "not applicable" (no log available).
   485	    Returns overall="ATTEST_NOT_APPLICABLE" when log_path is None or
   486	    absent — downstream can surface this as "no convergence evidence"
   487	    instead of misreading it as "convergence verified".
   488	    """
   489	    if log_path is None or not log_path.is_file():
   490	        return AttestationResult(overall="ATTEST_NOT_APPLICABLE", checks=[])
   491	
   492	    checks = [
   493	        _check_a1_solver_crash(log_path),
   494	        _check_a2_continuity_floor(log_path),
   495	        _check_a3_residual_floor(log_path),
   496	        _check_a4_iteration_cap(log_path),
   497	        _check_a5_bounding_recurrence(log_path),
   498	        _check_a6_no_progress(log_path),
   499	    ]
   500	
   501	    has_fail = any(c.verdict == "FAIL" for c in checks)
   502	    has_hazard = any(c.verdict == "HAZARD" for c in checks)
   503	    if has_fail:
   504	        overall: AttestVerdict = "ATTEST_FAIL"
   505	    elif has_hazard:
   506	        overall = "ATTEST_HAZARD"
   507	    else:
   508	        overall = "ATTEST_PASS"
   509	
   510	    return AttestationResult(overall=overall, checks=checks)
   511	
   512	
   513	def check_to_audit_concern_dict(c: AttestorCheck) -> dict[str, Any]:
   514	    """Serialize a non-PASS AttestorCheck as an audit_concerns[] entry."""
   515	    return {
   516	        "concern_type": c.concern_type,
   517	        "summary": c.summary,
   518	        "detail": c.detail,
   519	        "decision_refs": ["DEC-V61-038"],
   520	        "evidence": c.evidence,

exec
/bin/zsh -lc "nl -ba scripts/phase5_audit_run.py | sed -n '261,520p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba scripts/phase5_audit_run.py | sed -n '1,260p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   261	    # Count usable leaf files (foamToVTK output, samples, residuals).
   262	    usable = [p for p in artifact_dir.rglob("*") if p.is_file()]
   263	    if not usable:
   264	        print(
   265	            f"[audit] [WARN] field artifact dir empty, skipping manifest: {artifact_dir}",
   266	            flush=True,
   267	        )
   268	        return None
   269	    runs_dir = FIELDS_DIR / case_id / "runs"
   270	    runs_dir.mkdir(parents=True, exist_ok=True)
   271	    manifest = runs_dir / f"{run_label}.json"
   272	    payload = {
   273	        "run_label": run_label,
   274	        "timestamp": timestamp,
   275	        "case_id": case_id,
   276	        "artifact_dir_rel": str(artifact_dir.relative_to(REPO_ROOT)),
   277	    }
   278	    manifest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
   279	    return manifest
   280	
   281	
   282	# DEC-V61-034 Tier C: opt in all 10 whitelist cases for Phase 7a field
   283	# capture. The executor's _capture_field_artifacts runs foamToVTK + stages
   284	# VTK / residuals / solver log for ANY case regardless of whether its
   285	# generator emits the controlDict functions{} block (residuals are
   286	# log-parsed in the renderer when the functionObject wasn't emitted).
   287	# LDC still gets the full gold-overlay report via its sample block; the
   288	# other 9 cases flow through Tier C visual-only rendering (contour + residuals).
   289	_PHASE7A_OPTED_IN: frozenset[str] = frozenset(ALL_CASES)
   290	
   291	
   292	def _audit_fixture_doc(
   293	    case_id: str,
   294	    report,
   295	    commit_sha: str,
   296	    field_artifacts_ref: "dict | None" = None,
   297	    phase7a_timestamp: "str | None" = None,
   298	    u_ref: float = 1.0,
   299	) -> dict:
   300	    # DEC-V61-036 G1: load the gold's canonical quantity BEFORE extraction
   301	    # so the driver can strict-match (and hard-fail on miss) instead of
   302	    # silently substituting "first numeric".
   303	    expected_quantity = _gold_expected_quantity(case_id)
   304	    quantity, value, source_note = _primary_scalar(report, expected_quantity)
   305	    comp = report.comparison_result
   306	    passed = comp.passed if comp else False
   307	
   308	    # DEC-V61-036 G1: verdict hint must reflect the missing-quantity outcome.
   309	    # Prior behaviour tied verdict_hint to comp.passed alone, which showed
   310	    # "PASS" for runs that simply didn't measure the gold quantity.
   311	    if source_note == "no_numeric_quantity" or value is None:
   312	        verdict_hint = "FAIL"
   313	    else:
   314	        verdict_hint = "PASS" if passed else "FAIL"
   315	
   316	    # DEC-V61-036 G1: write measurement.value as literal null (None) when
   317	    # extractor missed; the verdict engine hard-FAILs on None. Do NOT coerce
   318	    # to 0.0 — that was the prior PASS-washing path.
   319	    measurement_value: float | None = value
   320	
   321	    doc = {
   322	        "run_metadata": {
   323	            "run_id": "audit_real_run",
   324	            "label_zh": "真实 solver 审计运行",
   325	            "label_en": "Real solver audit run",
   326	            "description_zh": (
   327	                f"FoamAgentExecutor 驱动 OpenFOAM 实际跑出的结果（commit {commit_sha}）。"
   328	                "这是 audit package 背书的权威测量——不是合成 fixture。"
   329	                "失败的话说明 case 本身的 physics_contract 在当前 mesh 预算下无法满足，"
   330	                "不是 harness bug；会进入 audit_concerns 随包交付给审查方。"
   331	            ),
   332	            "category": "audit_real_run",
   333	            "expected_verdict": verdict_hint,
   334	        },
   335	        "case_id": case_id,
   336	        "source": "phase5_audit_run_foam_agent",
   337	        "measurement": {
   338	            "value": measurement_value,
   339	            "unit": "dimensionless",
   340	            "run_id": f"audit_{case_id}_{commit_sha}",
   341	            "commit_sha": commit_sha,
   342	            "measured_at": _iso_now(),
   343	            "quantity": quantity,
   344	            "extraction_source": source_note,
   345	            "solver_success": report.execution_result.success,
   346	            "comparator_passed": passed,
   347	        },
   348	        "audit_concerns": [],
   349	        "decisions_trail": [
   350	            {
   351	                "decision_id": "DEC-V61-028",
   352	                "date": "2026-04-21",
   353	                "title": "Phase 5a audit pipeline — real-solver fixtures",
   354	                "autonomous": True,
   355	            },
   356	            {
   357	                "decision_id": "DEC-V61-036",
   358	                "date": "2026-04-22",
   359	                "title": "Hard comparator gate G1 (missing-target-quantity)",
   360	                "autonomous": True,
   361	            },
   362	        ],
   363	    }
   364	
   365	    # DEC-V61-036b G3/G4/G5 + DEC-V61-038 A1..A6: run pre-extraction
   366	    # attestor THEN post-extraction physics gates against the captured
   367	    # field artifacts + solver log. Attestor checks convergence process;
   368	    # gates check final-state sanity. Both emit audit_concerns[] entries
   369	    # that the verdict engine hard-FAILs on. Non-blocking on missing
   370	    # artifacts — both skip gracefully when log/VTK is unavailable.
   371	    if phase7a_timestamp is not None:
   372	        artifact_dir = FIELDS_DIR / case_id / phase7a_timestamp
   373	        solver_log: "Path | None" = None
   374	        if artifact_dir.is_dir():
   375	            log_candidates = sorted(artifact_dir.glob("log.*"))
   376	            if log_candidates:
   377	                solver_log = log_candidates[0]
   378	        vtk_dir = artifact_dir / "VTK" if artifact_dir.is_dir() else None
   379	
   380	        # DEC-V61-038 attestor — runs first, records overall verdict on the
   381	        # fixture for UI display + injects HAZARD/FAIL checks as concerns.
   382	        try:
   383	            attestation = attest(solver_log)
   384	            doc["attestation"] = {
   385	                "overall": attestation.overall,
   386	                "checks": [
   387	                    {
   388	                        "check_id": c.check_id,
   389	                        "verdict": c.verdict,
   390	                        "concern_type": c.concern_type,
   391	                        "summary": c.summary,
   392	                    }
   393	                    for c in attestation.checks
   394	                ],
   395	            }
   396	            for c in attestation.concerns:
   397	                doc["audit_concerns"].append(check_to_audit_concern_dict(c))
   398	        except Exception as exc:  # noqa: BLE001 — never crash the audit
   399	            print(
   400	                f"[audit] [WARN] attestor failed on {case_id}: {exc!r}",
   401	                flush=True,
   402	            )
   403	
   404	        # DEC-V61-036b gates — post-extraction physics checks.
   405	        try:
   406	            gate_violations = check_all_gates(
   407	                log_path=solver_log,
   408	                vtk_dir=vtk_dir if vtk_dir and vtk_dir.is_dir() else None,
   409	                U_ref=u_ref,
   410	            )
   411	            for v in gate_violations:
   412	                doc["audit_concerns"].append(violation_to_audit_concern_dict(v))
   413	        except Exception as exc:  # noqa: BLE001 — gates must not crash the audit
   414	            print(
   415	                f"[audit] [WARN] gates failed on {case_id}: {exc!r}", flush=True
   416	            )
   417	
   418	    # DEC-V61-036 G1: stamp a first-class concern when the extractor could
   419	    # not resolve the gold's quantity. The verdict engine hard-FAILs
   420	    # independently based on measurement.value is None, but embedding the
   421	    # concern in the fixture makes the audit package self-explaining.
   422	    if source_note == "no_numeric_quantity":
   423	        doc["audit_concerns"].append(
   424	            {
   425	                "concern_type": "MISSING_TARGET_QUANTITY",
   426	                "summary": (
   427	                    f"Extractor could not locate gold quantity "
   428	                    f"{quantity!r} in run key_quantities."
   429	                )[:240],
   430	                "detail": (
   431	                    "Gold standard expected a measurement of "
   432	                    f"{quantity!r} (with result_comparator alias resolution), "
   433	                    "but the case-specific extractor did not emit that key. "
   434	                    "Prior harness behaviour (pre-DEC-V61-036) silently "
   435	                    "substituted the first numeric key_quantities entry and "
   436	                    "compared it against the gold's tolerance band — that "
   437	                    "PASS-washing path is now closed. The adapter needs a "
   438	                    "case-specific extractor for this quantity; the verdict "
   439	                    "is hard-FAIL until that lands."
   440	                )[:2000],
   441	                "decision_refs": ["DEC-V61-036"],
   442	            }
   443	        )
   444	
   445	    if comp is not None:
   446	        doc["audit_concerns"].append(
   447	            {
   448	                "concern_type": "CONTRACT_STATUS",
   449	                "summary": (comp.summary or "No summary")[:240],
   450	                "detail": (comp.summary or "")[:2000],
   451	                "decision_refs": ["DEC-V61-028"],
   452	            }
   453	        )
   454	        if comp.deviations:
   455	            # Summarize first 5 deviations for the audit record
   456	            dev_summary = "; ".join(
   457	                f"{d.quantity}: actual={d.actual} expected={d.expected}"
   458	                for d in comp.deviations[:5]
   459	            )
   460	            doc["audit_concerns"].append(
   461	                {
   462	                    "concern_type": "DEVIATIONS",
   463	                    "summary": f"{len(comp.deviations)} deviation(s) over tolerance"[:240],
   464	                    "detail": dev_summary[:2000],
   465	                    "decision_refs": ["DEC-V61-028"],
   466	                }
   467	            )
   468	
   469	    # Phase 7a — field artifacts reference (manifest path only; NO timestamps
   470	    # in the YAML itself so byte-repro stays green per 07a-RESEARCH.md §3.1).
   471	    # The manifest at the referenced path contains the timestamp.
   472	    if field_artifacts_ref is not None:
   473	        doc["field_artifacts"] = field_artifacts_ref
   474	
   475	    return doc
   476	
   477	
   478	def _write_audit_fixture(case_id: str, doc: dict) -> Path:
   479	    case_dir = RUNS_DIR / case_id
   480	    case_dir.mkdir(parents=True, exist_ok=True)
   481	    out_path = case_dir / "audit_real_run_measurement.yaml"
   482	    header = (
   483	        "# Phase 5a audit-real-run fixture — AUTO-GENERATED, DO NOT HAND-EDIT.\n"
   484	        "# Regenerate via:\n"
   485	        f"#   EXECUTOR_MODE=foam_agent .venv/bin/python scripts/phase5_audit_run.py {case_id}\n"
   486	        "# This fixture backs the signed audit package. Byte-identity across\n"
   487	        "# re-runs (modulo timestamp + commit_sha) is enforced by\n"
   488	        "# test_phase5_byte_repro.py.\n\n"
   489	    )
   490	    with out_path.open("w", encoding="utf-8") as fh:
   491	        fh.write(header)
   492	        yaml.safe_dump(doc, fh, allow_unicode=True, sort_keys=False, default_flow_style=False)
   493	    return out_path
   494	
   495	
   496	def _write_raw_capture(case_id: str, report, duration_s: float) -> Path:
   497	    RAW_DIR.mkdir(parents=True, exist_ok=True)
   498	    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
   499	    out = RAW_DIR / f"{ts}_{case_id}_raw.json"
   500	    er = report.execution_result
   501	    comp = report.comparison_result
   502	    data = {
   503	        "case_id": case_id,
   504	        "measured_at": _iso_now(),
   505	        "duration_s": round(duration_s, 3),
   506	        "solver_success": er.success,
   507	        "key_quantities": er.key_quantities,
   508	        "comparator_passed": comp.passed if comp else None,
   509	        "comparator_summary": (comp.summary if comp else None),
   510	        "deviations": (
   511	            [
   512	                {"quantity": d.quantity, "actual": d.actual, "expected": d.expected}
   513	                for d in (comp.deviations or [])
   514	            ]
   515	            if comp
   516	            else []
   517	        ),
   518	    }
   519	    out.write_text(json.dumps(data, indent=2, default=str))
   520	    return out

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
    43	from src.result_comparator import _lookup_with_alias  # noqa: E402
    44	from src.comparator_gates import (  # noqa: E402
    45	    check_all_gates,
    46	    violation_to_audit_concern_dict,
    47	)
    48	from src.convergence_attestor import (  # noqa: E402
    49	    attest,
    50	    check_to_audit_concern_dict,
    51	)
    52	
    53	RUNS_DIR = REPO_ROOT / "ui" / "backend" / "tests" / "fixtures" / "runs"
    54	RAW_DIR = REPO_ROOT / "reports" / "phase5_audit"
    55	FIELDS_DIR = REPO_ROOT / "reports" / "phase5_fields"
    56	
    57	ALL_CASES = [
    58	    "lid_driven_cavity",
    59	    "backward_facing_step",
    60	    "circular_cylinder_wake",
    61	    "turbulent_flat_plate",
    62	    "duct_flow",
    63	    "differential_heated_cavity",
    64	    "plane_channel_flow",
    65	    "impinging_jet",
    66	    "naca0012_airfoil",
    67	    "rayleigh_benard_convection",
    68	]
    69	
    70	
    71	def _git_head_sha() -> str:
    72	    try:
    73	        out = subprocess.check_output(
    74	            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"], timeout=5
    75	        )
    76	        return out.decode().strip()[:7]
    77	    except Exception:
    78	        return "unknown"
    79	
    80	
    81	def _iso_now() -> str:
    82	    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    83	
    84	
    85	def _gold_expected_quantity(case_id: str) -> str | None:
    86	    """Load `quantity` from knowledge/gold_standards/{case_id}.yaml.
    87	
    88	    Returns the canonical gold quantity name (e.g. "reattachment_length",
    89	    "friction_factor"). Used by DEC-V61-036 G1 to gate extraction — the
    90	    driver must compare measured value against this exact key (with
    91	    result_comparator alias resolution), not against "first numeric".
    92	    """
    93	    gold_path = REPO_ROOT / "knowledge" / "gold_standards" / f"{case_id}.yaml"
    94	    if not gold_path.is_file():
    95	        return None
    96	    try:
    97	        with gold_path.open("r", encoding="utf-8") as fh:
    98	            docs = list(yaml.safe_load_all(fh))
    99	    except Exception:
   100	        return None
   101	    # Flat schema: top-level `quantity:` key in the first non-empty doc.
   102	    # observables[] schema: first observable's `name`.
   103	    for doc in docs:
   104	        if not isinstance(doc, dict):
   105	            continue
   106	        q = doc.get("quantity")
   107	        if isinstance(q, str) and q.strip():
   108	            return q.strip()
   109	        obs = doc.get("observables")
   110	        if isinstance(obs, list) and obs:
   111	            first = obs[0]
   112	            if isinstance(first, dict):
   113	                name = first.get("name")
   114	                if isinstance(name, str) and name.strip():
   115	                    return name.strip()
   116	    return None
   117	
   118	
   119	def _primary_scalar(
   120	    report, expected_quantity: str | None = None
   121	) -> tuple[str | None, float | None, str]:
   122	    """Extract the primary scalar for the audit fixture.
   123	
   124	    DEC-V61-036 G1: when `expected_quantity` is provided, this function
   125	    requires the run to emit exactly that quantity (with alias resolution)
   126	    — it no longer falls back to "first numeric key_quantities entry".
   127	
   128	    Priority:
   129	      1. comparator.deviations entry whose `quantity` matches expected_quantity
   130	      2. key_quantities lookup via `_lookup_with_alias(kq, expected_quantity)`
   131	      3. (expected_quantity, None, "no_numeric_quantity") — signals G1 failure
   132	
   133	    When `expected_quantity is None` (legacy calls without a gold), falls
   134	    back to the OLD behaviour (first numeric) for backward compatibility
   135	    — but this path should not fire for any whitelist case because every
   136	    case has a gold_standard.
   137	    """
   138	    comp = report.comparison_result
   139	    kq = report.execution_result.key_quantities or {}
   140	
   141	    if expected_quantity is not None:
   142	        # DEC-V61-036 G1 round 2: profile quantities (LDC u_centerline, NACA
   143	        # pressure_coefficient, plane_channel u_mean_profile) are emitted as
   144	        # per-coordinate comparator deviations named `expected_quantity[y=X]`,
   145	        # `expected_quantity[x/c=Y]`, etc. Match both the exact-scalar case
   146	        # AND the bracketed-profile case as honest extractions.
   147	        def _quantity_matches(dev_quantity: str) -> bool:
   148	            if dev_quantity == expected_quantity:
   149	                return True
   150	            # Strip `[axis=value]` suffix for profile deviations.
   151	            return dev_quantity.split("[", 1)[0] == expected_quantity
   152	
   153	        # (1) comparator deviation matching gold's quantity (scalar OR profile)
   154	        if comp is not None and comp.deviations:
   155	            for dev in comp.deviations:
   156	                if _quantity_matches(dev.quantity):
   157	                    actual = dev.actual
   158	                    if isinstance(actual, dict) and "value" in actual:
   159	                        return dev.quantity, float(actual["value"]), "comparator_deviation"
   160	                    if isinstance(actual, (int, float)):
   161	                        return dev.quantity, float(actual), "comparator_deviation"
   162	        # (2) direct/alias lookup in key_quantities
   163	        value, resolved_key = _lookup_with_alias(kq, expected_quantity)
   164	        if value is not None:
   165	            if isinstance(value, (int, float)) and not isinstance(value, bool):
   166	                src = (
   167	                    "key_quantities_direct"
   168	                    if resolved_key == expected_quantity
   169	                    else f"key_quantities_alias:{resolved_key}"
   170	                )
   171	                return expected_quantity, float(value), src
   172	            if isinstance(value, dict) and "value" in value and isinstance(
   173	                value["value"], (int, float)
   174	            ):
   175	                return expected_quantity, float(value["value"]), "key_quantities_alias_dict"
   176	            # DEC-V61-036 G1 round 2: list-valued key_quantity IS honest
   177	            # extraction for profile gold standards. The comparator would
   178	            # normally emit per-coordinate deviations; if there ARE no
   179	            # deviations (i.e., profile is within tolerance at every point),
   180	            # record the profile as present without forcing hard-FAIL, and
   181	            # sample a scalar representative for UI display.
   182	            if isinstance(value, list) and value:
   183	                first = value[0]
   184	                if isinstance(first, (int, float)) and not isinstance(first, bool):
   185	                    # All profile points within tolerance (no deviations) and
   186	                    # comparator considered the full profile honestly. Record
   187	                    # the first-coordinate value as the scalar display sample.
   188	                    return (
   189	                        f"{expected_quantity}[0]",
   190	                        float(first),
   191	                        "key_quantities_profile_sample",
   192	                    )
   193	                # Profile of non-scalar entries — list[dict]. Look for a
   194	                # value key under several conventional names, per
   195	                # DEC-V61-036c G2 Codex round-2 nit: NACA sampleDict emits
   196	                # dict{x_over_c, Cp}, plane_channel DNS profile emits
   197	                # dict{y_plus, u_plus}, etc.
   198	                _PROFILE_SCALAR_KEYS = ("value", "Cp", "Cf", "u", "u_plus", "Nu", "f")
   199	                if isinstance(first, dict):
   200	                    for scalar_key in _PROFILE_SCALAR_KEYS:
   201	                        val = first.get(scalar_key)
   202	                        if isinstance(val, (int, float)) and not isinstance(val, bool):
   203	                            return (
   204	                                f"{expected_quantity}[0]",
   205	                                float(val),
   206	                                f"key_quantities_profile_sample_dict:{scalar_key}",
   207	                            )
   208	                # Fallback for legacy shape (kept for backward compat).
   209	                if isinstance(first, dict) and "value" in first and isinstance(
   210	                    first["value"], (int, float)
   211	                ):
   212	                    return (
   213	                        f"{expected_quantity}[0]",
   214	                        float(first["value"]),
   215	                        "key_quantities_profile_sample_dict",
   216	                    )
   217	        # (3) G1 miss — NO fallback. Signal the verdict engine to hard-FAIL.
   218	        return expected_quantity, None, "no_numeric_quantity"
   219	
   220	    # Legacy path (no expected_quantity): preserve old behaviour for any
   221	    # non-whitelist caller that hasn't been updated yet. Whitelist cases
   222	    # always pass expected_quantity per DEC-V61-036.
   223	    if comp is not None and comp.deviations:
   224	        first = comp.deviations[0]
   225	        actual = first.actual
   226	        if isinstance(actual, dict) and "value" in actual:
   227	            return first.quantity, float(actual["value"]), "comparator_deviation"
   228	        if isinstance(actual, (int, float)):
   229	            return first.quantity, float(actual), "comparator_deviation"
   230	    for k, v in kq.items():
   231	        if isinstance(v, (int, float)) and not isinstance(v, bool):
   232	            return k, float(v), "key_quantities_fallback_legacy"
   233	        if isinstance(v, dict) and "value" in v and isinstance(v["value"], (int, float)):
   234	            return k, float(v["value"]), "key_quantities_fallback_legacy"
   235	    return None, None, "no_numeric_quantity"
   236	
   237	
   238	def _phase7a_timestamp() -> str:
   239	    """Shared timestamp format — matches _write_raw_capture."""
   240	    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
   241	
   242	
   243	def _write_field_artifacts_run_manifest(
   244	    case_id: str, run_label: str, timestamp: str
   245	) -> "Path | None":
   246	    """Write reports/phase5_fields/{case_id}/runs/{run_label}.json so the
   247	    backend route can resolve run_label -> timestamp directory in O(1).
   248	
   249	    Returns the manifest Path on success, None if the artifact dir is absent
   250	    OR empty. Codex round 1 MED #3 (2026-04-21): require a NON-empty artifact
   251	    set — an empty directory from a failed foamToVTK must not produce a
   252	    bogus manifest that the route will then 404-through.
   253	    """
   254	    artifact_dir = FIELDS_DIR / case_id / timestamp
   255	    if not artifact_dir.is_dir():
   256	        print(
   257	            f"[audit] [WARN] field artifact dir missing, skipping manifest: {artifact_dir}",
   258	            flush=True,
   259	        )
   260	        return None

exec
/bin/zsh -lc "nl -ba ui/backend/services/validation_report.py | sed -n '1,260p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba ui/backend/services/validation_report.py | sed -n '261,520p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
     1	"""Validation-report assembly — reads YAML, builds the Screen 4 payload.
     2	
     3	Phase 0 scope:
     4	    - list_cases()              → GET /api/cases
     5	    - load_case_detail(id)      → GET /api/cases/{id}
     6	    - build_validation_report() → GET /api/validation-report/{id}
     7	
     8	Phase 0 measurement sourcing strategy (in order):
     9	    1. ui/backend/tests/fixtures/{case_id}_measurement.yaml
    10	       (committed alongside the backend for deterministic demo data)
    11	    2. None (returns MeasuredValue=None; UI renders "no run yet")
    12	
    13	Phase 3 will extend this to pull from reports/**/slice_metrics.yaml
    14	once live-run streaming is integrated.
    15	"""
    16	
    17	from __future__ import annotations
    18	
    19	from functools import lru_cache
    20	from pathlib import Path
    21	from typing import Any
    22	
    23	import yaml
    24	
    25	from ui.backend.schemas.validation import (
    26	    AttestorCheck,
    27	    AttestorVerdict,
    28	    AuditConcern,
    29	    CaseDetail,
    30	    CaseIndexEntry,
    31	    ContractStatus,
    32	    DecisionLink,
    33	    GoldStandardReference,
    34	    MeasuredValue,
    35	    Precondition,
    36	    RunDescriptor,
    37	    RunSummary,
    38	    ValidationReport,
    39	)
    40	
    41	
    42	# ---------------------------------------------------------------------------
    43	# Path resolution (repo-root relative)
    44	# ---------------------------------------------------------------------------
    45	# Layout:
    46	#   <repo>/
    47	#     knowledge/whitelist.yaml
    48	#     knowledge/gold_standards/{case_id}.yaml
    49	#     ui/backend/services/validation_report.py  ← this file
    50	#     ui/backend/tests/fixtures/{case_id}_measurement.yaml
    51	_HERE = Path(__file__).resolve()
    52	REPO_ROOT = _HERE.parents[3]
    53	WHITELIST_PATH = REPO_ROOT / "knowledge" / "whitelist.yaml"
    54	GOLD_STANDARDS_DIR = REPO_ROOT / "knowledge" / "gold_standards"
    55	FIXTURE_DIR = _HERE.parents[1] / "tests" / "fixtures"
    56	
    57	
    58	# ---------------------------------------------------------------------------
    59	# YAML loaders (cached — Phase 0 content is stable during a server lifetime)
    60	# ---------------------------------------------------------------------------
    61	@lru_cache(maxsize=1)
    62	def _load_whitelist() -> dict[str, dict[str, Any]]:
    63	    """Return {case_id: case_def} from knowledge/whitelist.yaml."""
    64	    if not WHITELIST_PATH.exists():
    65	        return {}
    66	    with WHITELIST_PATH.open("r", encoding="utf-8") as fh:
    67	        doc = yaml.safe_load(fh) or {}
    68	    cases = doc.get("cases", [])
    69	    out: dict[str, dict[str, Any]] = {}
    70	    for entry in cases:
    71	        cid = entry.get("id")
    72	        if cid:
    73	            out[cid] = entry
    74	    return out
    75	
    76	
    77	def _load_gold_standard(case_id: str) -> dict[str, Any] | None:
    78	    """Read knowledge/gold_standards/{case_id}.yaml if present.
    79	
    80	    Two on-disk shapes are supported:
    81	        (A) Single document with top-level `observables: [{name, ref_value,
    82	            tolerance, ...}]` + `physics_contract: {...}`
    83	            (e.g. differential_heated_cavity, turbulent_flat_plate).
    84	        (B) Multi-document — each YAML doc pins one quantity with
    85	            top-level `quantity / reference_values / tolerance`; the
    86	            first doc typically carries `physics_contract`
    87	            (e.g. circular_cylinder_wake, lid_driven_cavity).
    88	
    89	    Both shapes are normalised to (A)'s schema before returning, so
    90	    downstream code only ever sees a single `observables: [...]`.
    91	    """
    92	    candidate = GOLD_STANDARDS_DIR / f"{case_id}.yaml"
    93	    if not candidate.exists():
    94	        return None
    95	    with candidate.open("r", encoding="utf-8") as fh:
    96	        docs = [d for d in yaml.safe_load_all(fh) if d]
    97	    if not docs:
    98	        return None
    99	
   100	    # Shape A — already has observables[] ⇒ return as-is.
   101	    if len(docs) == 1 and isinstance(docs[0].get("observables"), list):
   102	        return docs[0]
   103	
   104	    # Shape B — synthesise an observables[] by flattening each doc.
   105	    primary = docs[0]
   106	    observables: list[dict[str, Any]] = []
   107	    for doc in docs:
   108	        quantity = doc.get("quantity")
   109	        if not quantity:
   110	            continue
   111	        refs = doc.get("reference_values") or []
   112	        ref_value: float | None = None
   113	        unit = ""
   114	        # Scan each reference_values entry for the first non-zero scalar
   115	        # anchor under any known key. (First entry of a profile is often
   116	        # a trivial u_plus=0 at y_plus=0 — picking the next non-zero
   117	        # entry makes the contract engine produce meaningful PASS/FAIL
   118	        # instead of collapsing deviation to 0.)
   119	        scalar_keys = (
   120	            "value", "Cf", "f", "Nu", "u", "u_Uinf", "Cp", "Re_D", "St",
   121	            "u_plus",
   122	        )
   123	        if refs and isinstance(refs[0], dict):
   124	            unit = refs[0].get("unit", "") or ""
   125	        for entry in refs:
   126	            if not isinstance(entry, dict):
   127	                continue
   128	            for scalar_key in scalar_keys:
   129	                val = entry.get(scalar_key)
   130	                if isinstance(val, (int, float)) and float(val) != 0.0:
   131	                    ref_value = float(val)
   132	                    break
   133	            if ref_value is not None:
   134	                break
   135	        # Fallback: if every entry was zero, accept the first scalar we
   136	        # can find (even zero) to preserve prior behaviour.
   137	        if ref_value is None and refs and isinstance(refs[0], dict):
   138	            for scalar_key in scalar_keys:
   139	                val = refs[0].get(scalar_key)
   140	                if isinstance(val, (int, float)):
   141	                    ref_value = float(val)
   142	                    break
   143	        observables.append(
   144	            {
   145	                "name": quantity,
   146	                "ref_value": ref_value if ref_value is not None else 0.0,
   147	                "unit": unit,
   148	                "tolerance": doc.get("tolerance"),
   149	                "description": (refs[0].get("description") if refs and isinstance(refs[0], dict) else None),
   150	            }
   151	        )
   152	    return {
   153	        "observables": observables,
   154	        "physics_contract": primary.get("physics_contract") or {},
   155	        "source": primary.get("source"),
   156	        "literature_doi": primary.get("literature_doi"),
   157	        "schema_version": primary.get("schema_version"),
   158	        "case_id": primary.get("case_info", {}).get("id") or case_id,
   159	    }
   160	
   161	
   162	def _load_fixture_measurement(case_id: str) -> dict[str, Any] | None:
   163	    """Read the legacy single-run fixture if present.
   164	
   165	    Legacy path: ui/backend/tests/fixtures/{case_id}_measurement.yaml
   166	    This is the pre-multi-run layout and is still honored for back-compat.
   167	    If a multi-run directory exists at fixtures/runs/{case_id}/, those runs
   168	    are preferred (see _list_runs + _load_run_measurement).
   169	    """
   170	    candidate = FIXTURE_DIR / f"{case_id}_measurement.yaml"
   171	    if not candidate.exists():
   172	        return None
   173	    with candidate.open("r", encoding="utf-8") as fh:
   174	        return yaml.safe_load(fh)
   175	
   176	
   177	RUNS_DIR = FIXTURE_DIR / "runs"
   178	
   179	
   180	def _list_run_files(case_id: str) -> list[Path]:
   181	    """Return run fixture paths under fixtures/runs/{case_id}/ sorted by
   182	    run_id ascending. Empty list if the directory doesn't exist.
   183	    """
   184	    case_dir = RUNS_DIR / case_id
   185	    if not case_dir.is_dir():
   186	        return []
   187	    return sorted(case_dir.glob("*_measurement.yaml"))
   188	
   189	
   190	def _run_id_from_path(p: Path) -> str:
   191	    # lid_driven_cavity/reference_pass_measurement.yaml → reference_pass
   192	    return p.stem.removesuffix("_measurement")
   193	
   194	
   195	_CATEGORY_ORDER: dict[str, int] = {
   196	    "reference": 0,
   197	    "audit_real_run": 1,
   198	    "real_incident": 2,
   199	    "under_resolved": 3,
   200	    "wrong_model": 4,
   201	    "grid_convergence": 5,
   202	}
   203	
   204	
   205	def list_runs(case_id: str) -> list[RunDescriptor]:
   206	    """Enumerate curated + legacy runs for a case.
   207	
   208	    Ordering (pedagogical, stable across filesystem locales):
   209	    1. `reference` first — students see "what done right looks like"
   210	       at the top.
   211	    2. `real_incident` next — actual production measurement, auditable
   212	       reality.
   213	    3. `under_resolved` / `wrong_model` — teaching variants.
   214	    4. `grid_convergence` last — mesh-sweep runs live behind the Mesh
   215	       tab and don't belong in the Compare run-picker's first page of
   216	       attention.
   217	    Within a category, sort by run_id ascending (mesh_20 before
   218	    mesh_160 via zero-padded numeric comparison for `mesh_N` ids).
   219	    Legacy `{case_id}_measurement.yaml` is exposed as run_id='legacy'
   220	    only when the multi-run dir is empty.
   221	    """
   222	    runs: list[RunDescriptor] = []
   223	    for path in _list_run_files(case_id):
   224	        try:
   225	            with path.open("r", encoding="utf-8") as fh:
   226	                doc = yaml.safe_load(fh) or {}
   227	        except Exception:
   228	            continue
   229	        md = doc.get("run_metadata") or {}
   230	        run_id = md.get("run_id") or _run_id_from_path(path)
   231	        runs.append(
   232	            RunDescriptor(
   233	                run_id=run_id,
   234	                label_zh=md.get("label_zh") or run_id.replace("_", " "),
   235	                label_en=md.get("label_en", "") or "",
   236	                description_zh=md.get("description_zh", "") or "",
   237	                category=md.get("category", "reference"),
   238	                expected_verdict=md.get("expected_verdict", "UNKNOWN"),
   239	            )
   240	        )
   241	    if runs:
   242	        def _sort_key(r: RunDescriptor) -> tuple[int, int, str]:
   243	            cat_rank = _CATEGORY_ORDER.get(r.category, 99)
   244	            # Numeric-aware secondary sort for mesh_N ids so mesh_20 sits
   245	            # before mesh_160 instead of lexicographic (`mesh_160` < `mesh_20`).
   246	            if r.run_id.startswith("mesh_"):
   247	                try:
   248	                    n = int(r.run_id.split("_", 1)[1])
   249	                except ValueError:
   250	                    n = 0
   251	                return (cat_rank, n, r.run_id)
   252	            return (cat_rank, 0, r.run_id)
   253	
   254	        runs.sort(key=_sort_key)
   255	        return runs
   256	
   257	    legacy = _load_fixture_measurement(case_id)
   258	    if legacy is not None:
   259	        runs.append(
   260	            RunDescriptor(

 succeeded in 0ms:
   261	                run_id="legacy",
   262	                label_zh=legacy.get("run_label_zh") or "历史测量",
   263	                label_en="Legacy fixture",
   264	                description_zh=(
   265	                    legacy.get("run_description_zh")
   266	                    or "来自 §5d 验收批次的原始测量值，保留作审计追溯用。"
   267	                ),
   268	                category="real_incident",
   269	                expected_verdict="UNKNOWN",
   270	            )
   271	        )
   272	    return runs
   273	
   274	
   275	def _load_run_measurement(case_id: str, run_id: str) -> dict[str, Any] | None:
   276	    """Load a specific run's measurement doc. Falls back to legacy fixture
   277	    when run_id=='legacy'."""
   278	    if run_id == "legacy":
   279	        return _load_fixture_measurement(case_id)
   280	    candidate = RUNS_DIR / case_id / f"{run_id}_measurement.yaml"
   281	    if not candidate.exists():
   282	        return None
   283	    with candidate.open("r", encoding="utf-8") as fh:
   284	        return yaml.safe_load(fh)
   285	
   286	
   287	def _pick_default_run_id(case_id: str) -> str | None:
   288	    """Default run resolution rule (DEC-V61-035 correction): prefer the
   289	    ``audit_real_run`` category — i.e. the actual solver-in-the-loop
   290	    verdict. Falls back to 'reference' (literature-data curated PASS
   291	    narrative) only when no audit_real_run exists, and finally to any
   292	    curated run, then 'legacy' on-disk fixture.
   293	
   294	    The previous rule preferred `reference` unconditionally, which
   295	    surfaced curated PASS narratives as the case verdict even when the
   296	    real-solver audit run FAILED — a PASS-washing bug flagged in the
   297	    2026-04-22 deep-review.
   298	    """
   299	    runs = list_runs(case_id)
   300	    # 1. Prefer audit_real_run (honest: solver-in-the-loop evidence).
   301	    for r in runs:
   302	        if r.category == "audit_real_run":
   303	            return r.run_id
   304	    # 2. Fall back to reference (curated literature-anchored run).
   305	    for r in runs:
   306	        if r.category == "reference":
   307	            return r.run_id
   308	    # 3. Any curated run.
   309	    if runs:
   310	        return runs[0].run_id
   311	    return None
   312	
   313	
   314	# ---------------------------------------------------------------------------
   315	# Mappers — YAML dict → Pydantic schema
   316	# ---------------------------------------------------------------------------
   317	def _tolerance_scalar(value: Any) -> float | None:
   318	    """Normalise tolerance-shaped YAML (scalar OR {mode, value} dict)."""
   319	    if value is None:
   320	        return None
   321	    if isinstance(value, (int, float)):
   322	        return float(value)
   323	    if isinstance(value, dict):
   324	        inner = value.get("value")
   325	        if isinstance(inner, (int, float)):
   326	            return float(inner)
   327	    return None
   328	
   329	
   330	def _make_gold_reference(
   331	    case: dict[str, Any],
   332	    gs_doc: dict[str, Any] | None,
   333	) -> GoldStandardReference | None:
   334	    """Extract the anchor ref_value + tolerance from either the
   335	    whitelist `gold_standard` block or the gold_standards/*.yaml
   336	    `observables[*]` (preferring the one matching the whitelist
   337	    `gold_standard.quantity` to stay quantity-faithful)."""
   338	    citation = case.get("reference") or (gs_doc or {}).get("source", "")
   339	    doi = case.get("doi") or (gs_doc or {}).get("literature_doi")
   340	    wl_gs = case.get("gold_standard") or {}
   341	    target_quantity = wl_gs.get("quantity")
   342	
   343	    # Prefer matching observable from gold_standards/*.yaml.
   344	    if gs_doc:
   345	        observables = gs_doc.get("observables") or []
   346	        ob: dict[str, Any] | None = None
   347	        if target_quantity:
   348	            for candidate in observables:
   349	                if candidate.get("name") == target_quantity:
   350	                    ob = candidate
   351	                    break
   352	        if ob is None and observables:
   353	            ob = observables[0]
   354	        if ob is not None:
   355	            tolerance = _tolerance_scalar(ob.get("tolerance"))
   356	            if tolerance is None:
   357	                tolerance = _tolerance_scalar(wl_gs.get("tolerance"))
   358	            if tolerance is None:
   359	                tolerance = 0.1  # conservative default
   360	            ref_value = ob.get("ref_value")
   361	            if isinstance(ref_value, (int, float)):
   362	                return GoldStandardReference(
   363	                    quantity=ob.get("name") or target_quantity or "unknown",
   364	                    ref_value=float(ref_value),
   365	                    unit=ob.get("unit", "") or "",
   366	                    tolerance_pct=float(tolerance),
   367	                    citation=citation or "",
   368	                    doi=doi,
   369	                )
   370	            # Profile-shaped ref_value (list of {x, y/value} dicts) — fall
   371	            # through to wl_gs.reference_values scanning below, which picks
   372	            # the first non-zero scalar anchor (Cp at stagnation, etc.) so
   373	            # the contract engine can produce meaningful PASS/FAIL on
   374	            # cases like naca0012_airfoil whose gold is a Cp profile.
   375	
   376	    # Fallback: synthesize from whitelist.yaml `gold_standard` inline.
   377	    refs = wl_gs.get("reference_values") or []
   378	    if not refs:
   379	        return None
   380	    value: float | None = None
   381	    # Scan entries for the first non-zero scalar under any known key.
   382	    # (First entry of a profile is often a trivial anchor like u_plus=0
   383	    # at y_plus=0; skipping-to-first-nonzero gives the engine a
   384	    # pedagogically meaningful ref.)
   385	    value_keys = ("value", "Cf", "f", "Nu", "u", "u_Uinf", "Cp", "u_plus")
   386	    first = refs[0]
   387	    for entry in refs:
   388	        if not isinstance(entry, dict):
   389	            continue
   390	        for key in value_keys:
   391	            if key in entry and isinstance(entry[key], (int, float)):
   392	                if float(entry[key]) != 0.0:
   393	                    value = float(entry[key])
   394	                    first = entry
   395	                    break
   396	        if value is not None:
   397	            break
   398	    # If every entry is zero (or none match), fall back to the very first
   399	    # dict's first matching key (even if zero) to preserve prior behavior.
   400	    if value is None:
   401	        if not isinstance(first, dict):
   402	            return None
   403	        for key in value_keys:
   404	            if key in first and isinstance(first[key], (int, float)):
   405	                value = float(first[key])
   406	                break
   407	    if value is None:
   408	        return None
   409	    tol = _tolerance_scalar(wl_gs.get("tolerance")) or 0.1
   410	    return GoldStandardReference(
   411	        quantity=wl_gs.get("quantity", "unknown"),
   412	        ref_value=value,
   413	        unit=first.get("unit", "") or "",
   414	        tolerance_pct=tol,
   415	        citation=citation or "",
   416	        doi=doi,
   417	    )
   418	
   419	
   420	def _make_preconditions(gs_doc: dict[str, Any] | None) -> list[Precondition]:
   421	    if not gs_doc:
   422	        return []
   423	    physics_contract = gs_doc.get("physics_contract") or {}
   424	    rows = physics_contract.get("physics_precondition") or []
   425	    out: list[Precondition] = []
   426	    for row in rows:
   427	        out.append(
   428	            Precondition(
   429	                condition=row.get("condition", ""),
   430	                satisfied=bool(row.get("satisfied_by_current_adapter", False)),
   431	                evidence_ref=row.get("evidence_ref"),
   432	                consequence_if_unsatisfied=row.get("consequence_if_unsatisfied"),
   433	            )
   434	        )
   435	    return out
   436	
   437	
   438	def _make_audit_concerns(
   439	    gs_doc: dict[str, Any] | None,
   440	    measurement_doc: dict[str, Any] | None,
   441	) -> list[AuditConcern]:
   442	    out: list[AuditConcern] = []
   443	    # (1) Contract-status narrative from gold_standards → top-level concern.
   444	    if gs_doc:
   445	        status_narrative = (
   446	            (gs_doc.get("physics_contract") or {}).get("contract_status") or ""
   447	        ).strip()
   448	        if status_narrative:
   449	            out.append(
   450	                AuditConcern(
   451	                    concern_type="CONTRACT_STATUS",
   452	                    summary=(
   453	                        status_narrative.splitlines()[0][:240]
   454	                        if status_narrative
   455	                        else ""
   456	                    ),
   457	                    detail=status_narrative,
   458	                    decision_refs=_extract_decision_refs(status_narrative),
   459	                )
   460	            )
   461	    # (2) Measurement-level audit concerns (fixture or slice_metrics).
   462	    if measurement_doc:
   463	        for concern in measurement_doc.get("audit_concerns", []) or []:
   464	            out.append(
   465	                AuditConcern(
   466	                    concern_type=concern.get("concern_type", "UNKNOWN"),
   467	                    summary=concern.get("summary", ""),
   468	                    detail=concern.get("detail"),
   469	                    decision_refs=concern.get("decision_refs", []) or [],
   470	                )
   471	            )
   472	        # (3) DEC-V61-036 G1: synthesize MISSING_TARGET_QUANTITY concern when
   473	        # the extractor signalled it could not resolve the gold's quantity.
   474	        # Triggers:
   475	        #   - measurement.extraction_source == "no_numeric_quantity" (new post-DEC)
   476	        #   - measurement.extraction_source == "key_quantities_fallback" (legacy
   477	        #     fixtures — this was the silent-substitution bug marker itself)
   478	        #   - measurement.value is None (explicit missing)
   479	        # Surfacing as a first-class concern lets _derive_contract_status
   480	        # hard-FAIL and the UI display the schema failure separately from
   481	        # numeric deviations.
   482	        m = measurement_doc.get("measurement") or {}
   483	        src = m.get("extraction_source")
   484	        g1_miss = (
   485	            src == "no_numeric_quantity"
   486	            or src == "key_quantities_fallback"
   487	            or m.get("value") is None
   488	        )
   489	        if g1_miss:
   490	            gold_quantity = m.get("quantity") or "<unknown>"
   491	            out.append(
   492	                AuditConcern(
   493	                    concern_type="MISSING_TARGET_QUANTITY",
   494	                    summary=(
   495	                        f"Extractor could not locate gold quantity "
   496	                        f"'{gold_quantity}' in run key_quantities."
   497	                    ),
   498	                    detail=(
   499	                        "DEC-V61-036 G1: the case-specific extractor did not "
   500	                        "emit the gold standard's target quantity and the "
   501	                        "result_comparator alias lookup also missed. Prior "
   502	                        "behavior silently substituted the first numeric "
   503	                        "key_quantities entry — that PASS-washing path is now "
   504	                        "closed. Measurement.value = None, contract_status = FAIL."
   505	                    ),
   506	                    decision_refs=["DEC-V61-036"],
   507	                )
   508	            )
   509	    return out
   510	
   511	
   512	def _extract_decision_refs(text: str) -> list[str]:
   513	    """Pull DEC-ADWM-00N / DEC-V61-00N tokens out of narrative text."""
   514	    import re
   515	
   516	    return sorted(set(re.findall(r"DEC-(?:ADWM|V61)-\d{3}", text)))
   517	
   518	
   519	def _make_decisions_trail(
   520	    measurement_doc: dict[str, Any] | None,

exec
/bin/zsh -lc 'nl -ba knowledge/attestor_thresholds.yaml' in /Users/Zhuanz/Desktop/cfd-harness-unified
 exited 1 in 0ms:
nl: knowledge/attestor_thresholds.yaml: No such file or directory

exec
/bin/zsh -lc "nl -ba ui/backend/tests/test_convergence_attestor.py | sed -n '1,260p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
     1	"""DEC-V61-038 tests: convergence attestor A1..A6.
     2	
     3	Coverage: each check's PASS/HAZARD/FAIL branch + LDC/BFS integration
     4	(real audit logs at reports/phase5_fields/*).
     5	
     6	Ground truth from Codex round-1 physics audit (DEC-036):
     7	  LDC    → ATTEST_PASS (all 6 checks PASS or N/A)
     8	  BFS    → ATTEST_FAIL via A2 (sum_local=5.25e+18) + A3 HAZARD + A5 HAZARD
     9	  DHC    → ATTEST_PASS (converged, Nu off gold but physics OK)
    10	"""
    11	
    12	from __future__ import annotations
    13	
    14	from pathlib import Path
    15	
    16	import pytest
    17	
    18	from src import convergence_attestor as ca
    19	
    20	
    21	def _write_log(tmp_path: Path, content: str) -> Path:
    22	    p = tmp_path / "log.simpleFoam"
    23	    p.write_text(content, encoding="utf-8")
    24	    return p
    25	
    26	
    27	# ---------------------------------------------------------------------------
    28	# A1 solver_exit_clean
    29	# ---------------------------------------------------------------------------
    30	
    31	def test_a1_passes_on_clean_log(tmp_path: Path) -> None:
    32	    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
    33	    result = ca.attest(log)
    34	    a1 = next(c for c in result.checks if c.check_id == "A1")
    35	    assert a1.verdict == "PASS"
    36	
    37	
    38	def test_a1_fails_on_foam_fatal(tmp_path: Path) -> None:
    39	    content = "Time = 1\nFOAM FATAL IO ERROR: missing dict\nExiting\n"
    40	    log = _write_log(tmp_path, content)
    41	    result = ca.attest(log)
    42	    a1 = next(c for c in result.checks if c.check_id == "A1")
    43	    assert a1.verdict == "FAIL"
    44	    assert result.overall == "ATTEST_FAIL"
    45	
    46	
    47	def test_a1_ignores_sigfpe_startup_banner(tmp_path: Path) -> None:
    48	    """DEC-036b Codex nit: 'floating point exception trapping' is a
    49	    startup banner, not an actual exception. Must NOT fire A1."""
    50	    content = (
    51	        "sigFpe : Enabling floating point exception trapping (FOAM_SIGFPE).\n"
    52	        "Time = 1\nEnd\n"
    53	    )
    54	    log = _write_log(tmp_path, content)
    55	    result = ca.attest(log)
    56	    a1 = next(c for c in result.checks if c.check_id == "A1")
    57	    assert a1.verdict == "PASS"
    58	
    59	
    60	# ---------------------------------------------------------------------------
    61	# A2 continuity_floor
    62	# ---------------------------------------------------------------------------
    63	
    64	def test_a2_passes_on_clean_continuity(tmp_path: Path) -> None:
    65	    content = (
    66	        "time step continuity errors : "
    67	        "sum local = 1e-07, global = 1e-09, cumulative = 1e-12\n"
    68	    )
    69	    log = _write_log(tmp_path, content)
    70	    result = ca.attest(log)
    71	    a2 = next(c for c in result.checks if c.check_id == "A2")
    72	    assert a2.verdict == "PASS"
    73	
    74	
    75	def test_a2_hazard_between_floors(tmp_path: Path) -> None:
    76	    """sum_local between A2 floor (1e-4) and G5 floor (1e-2) → HAZARD."""
    77	    content = (
    78	        "time step continuity errors : "
    79	        "sum local = 1e-03, global = 1e-05, cumulative = 0.001\n"
    80	    )
    81	    log = _write_log(tmp_path, content)
    82	    result = ca.attest(log)
    83	    a2 = next(c for c in result.checks if c.check_id == "A2")
    84	    assert a2.verdict == "HAZARD"
    85	
    86	
    87	def test_a2_hazard_above_g5_floor_after_split_brain_fix(tmp_path: Path) -> None:
    88	    """Codex DEC-038 round-1 A2/G5 split-brain fix: A2 no longer returns
    89	    FAIL even for sum_local > 1e-2. That FAIL call belongs to G5 at the
    90	    gate layer. A2 stays strictly HAZARD-tier."""
    91	    content = (
    92	        "time step continuity errors : "
    93	        "sum local = 0.5, global = 0.01, cumulative = 0.1\n"
    94	    )
    95	    log = _write_log(tmp_path, content)
    96	    result = ca.attest(log)
    97	    a2 = next(c for c in result.checks if c.check_id == "A2")
    98	    assert a2.verdict == "HAZARD"  # was FAIL pre-fix
    99	
   100	
   101	# ---------------------------------------------------------------------------
   102	# A3 residual_floor
   103	# ---------------------------------------------------------------------------
   104	
   105	def test_a3_passes_when_all_residuals_below_floor(tmp_path: Path) -> None:
   106	    content = (
   107	        "smoothSolver:  Solving for Ux, Initial residual = 1e-06, "
   108	        "Final residual = 1e-07, No Iterations 2\n"
   109	    )
   110	    log = _write_log(tmp_path, content)
   111	    result = ca.attest(log)
   112	    a3 = next(c for c in result.checks if c.check_id == "A3")
   113	    assert a3.verdict == "PASS"
   114	
   115	
   116	def test_a3_hazard_when_final_residual_above_floor(tmp_path: Path) -> None:
   117	    content = (
   118	        "smoothSolver:  Solving for Ux, Initial residual = 0.05, "
   119	        "Final residual = 0.001, No Iterations 20\n"
   120	    )
   121	    log = _write_log(tmp_path, content)
   122	    result = ca.attest(log)
   123	    a3 = next(c for c in result.checks if c.check_id == "A3")
   124	    assert a3.verdict == "HAZARD"
   125	    assert "Ux" in a3.evidence["offenders"]
   126	
   127	
   128	# ---------------------------------------------------------------------------
   129	# A4 solver_iteration_cap
   130	# ---------------------------------------------------------------------------
   131	
   132	def test_a4_fails_on_consecutive_cap_hits(tmp_path: Path) -> None:
   133	    """5 consecutive Time= blocks each with a capped GAMG p solve → FAIL.
   134	
   135	    Codex round-1 BLOCKER 2: measurement unit changed from consecutive
   136	    lines to consecutive TIME STEPS. Each `Time =` divider opens a new
   137	    block, so this test now needs Time= dividers.
   138	    """
   139	    content = "".join(
   140	        f"Time = {i}\nGAMG:  Solving for p, Initial residual = 0.9, "
   141	        "Final residual = 0.5, No Iterations 1000\n"
   142	        for i in range(5)
   143	    )
   144	    log = _write_log(tmp_path, content)
   145	    result = ca.attest(log)
   146	    a4 = next(c for c in result.checks if c.check_id == "A4")
   147	    assert a4.verdict == "FAIL"
   148	    assert a4.evidence["consecutive_cap_blocks"] >= 3
   149	
   150	
   151	def test_a4_fails_on_p_rgh_buoyant_log(tmp_path: Path) -> None:
   152	    """Codex DEC-038 round-1 BLOCKER 1: impinging_jet stuck solver is
   153	    `GAMG: Solving for p_rgh` in log.buoyantFoam — A4 regex must match
   154	    p_rgh (not just `p,`) to catch the real impinging_jet case.
   155	    """
   156	    content = "\n".join(
   157	        [f"Time = {i}s\nGAMG:  Solving for p_rgh, Initial residual = 0.7, "
   158	         "Final residual = 0.5, No Iterations 1000"
   159	         for i in range(5)]
   160	    )
   161	    log = _write_log(tmp_path, content)
   162	    result = ca.attest(log)
   163	    a4 = next(c for c in result.checks if c.check_id == "A4")
   164	    assert a4.verdict == "FAIL", f"got {a4.verdict}: {a4.summary}"
   165	
   166	
   167	def test_a4_fails_on_dicpcg_p_rgh(tmp_path: Path) -> None:
   168	    """DHC uses DICPCG: Solving for p_rgh. Same regex coverage requirement."""
   169	    content = "\n".join(
   170	        [f"Time = {i*0.5}s\nDICPCG:  Solving for p_rgh, Initial residual = 0.8, "
   171	         "Final residual = 0.6, No Iterations 1000"
   172	         for i in range(1, 6)]
   173	    )
   174	    log = _write_log(tmp_path, content)
   175	    result = ca.attest(log)
   176	    a4 = next(c for c in result.checks if c.check_id == "A4")
   177	    assert a4.verdict == "FAIL"
   178	
   179	
   180	def test_a4_multi_corrector_pimple_counts_blocks_not_lines(tmp_path: Path) -> None:
   181	    """Codex DEC-038 round-1 BLOCKER 2: PIMPLE emits multiple pressure
   182	    solves per Time= block. A4 must count BLOCKS, not LINES — 2 cap-hits
   183	    within the same block should count as 1 toward consecutive threshold,
   184	    not 2. Here 2 blocks × 2 cap-hits = 4 lines but only 2 blocks, so
   185	    consecutive=2 < 3 → PASS. A 3rd capped block is needed to FAIL.
   186	    """
   187	    # 2 capped blocks — should NOT fire (need 3 consecutive blocks).
   188	    content = (
   189	        "Time = 1s\n"
   190	        "GAMG:  Solving for p_rgh, Initial residual = 0.7, Final residual = 0.5, No Iterations 1000\n"
   191	        "GAMG:  Solving for p_rgh, Initial residual = 0.7, Final residual = 0.5, No Iterations 1000\n"
   192	        "Time = 2s\n"
   193	        "GAMG:  Solving for p_rgh, Initial residual = 0.7, Final residual = 0.5, No Iterations 1000\n"
   194	        "GAMG:  Solving for p_rgh, Initial residual = 0.7, Final residual = 0.5, No Iterations 1000\n"
   195	    )
   196	    log = _write_log(tmp_path, content)
   197	    result = ca.attest(log)
   198	    a4 = next(c for c in result.checks if c.check_id == "A4")
   199	    assert a4.verdict == "PASS", f"2 blocks should not fire A4 (threshold=3); got {a4.verdict}"
   200	
   201	
   202	def test_a4_fires_after_three_consecutive_blocks(tmp_path: Path) -> None:
   203	    """3 consecutive capped blocks → FAIL, regardless of per-block count."""
   204	    content = "".join(
   205	        f"Time = {i}s\n"
   206	        "GAMG:  Solving for p_rgh, Initial residual = 0.7, Final residual = 0.5, No Iterations 1000\n"
   207	        "GAMG:  Solving for p_rgh, Initial residual = 0.7, Final residual = 0.5, No Iterations 1000\n"
   208	        for i in range(1, 4)
   209	    )
   210	    log = _write_log(tmp_path, content)
   211	    result = ca.attest(log)
   212	    a4 = next(c for c in result.checks if c.check_id == "A4")
   213	    assert a4.verdict == "FAIL"
   214	    assert a4.evidence["consecutive_cap_blocks"] == 3
   215	
   216	
   217	def test_attestor_not_applicable_when_log_missing(tmp_path: Path) -> None:
   218	    """Codex DEC-038 round-1 comment C: missing log → ATTEST_NOT_APPLICABLE,
   219	    distinct from ATTEST_PASS. DEC-V61-040 UI tiers will surface this
   220	    explicitly for reference/visual_only runs that have no solver log.
   221	    """
   222	    result = ca.attest(None)
   223	    assert result.overall == "ATTEST_NOT_APPLICABLE"
   224	    result = ca.attest(tmp_path / "missing.log")
   225	    assert result.overall == "ATTEST_NOT_APPLICABLE"
   226	
   227	
   228	def test_a2_never_returns_fail_only_hazard(tmp_path: Path) -> None:
   229	    """Codex DEC-038 round-1 comment A7: A2 stays HAZARD-tier to avoid
   230	    split-brain with G5. Even sum_local=0.5 returns HAZARD from A2 (G5
   231	    is responsible for the FAIL call at the gate layer)."""
   232	    content = (
   233	        "time step continuity errors : "
   234	        "sum local = 0.5, global = 0.01, cumulative = 0.1\n"
   235	    )
   236	    log = _write_log(tmp_path, content)
   237	    result = ca.attest(log)
   238	    a2 = next(c for c in result.checks if c.check_id == "A2")
   239	    assert a2.verdict == "HAZARD"  # was FAIL pre-fix
   240	
   241	
   242	def test_a4_passes_on_sparse_cap_hits(tmp_path: Path) -> None:
   243	    """Single-iteration cap is not pathological — solver typically hits
   244	    high counts in transient but recovers."""
   245	    content = (
   246	        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, "
   247	        "No Iterations 1000\n"
   248	        "GAMG:  Solving for p, Initial residual = 0.5, Final residual = 0.01, "
   249	        "No Iterations 50\n"
   250	    )
   251	    log = _write_log(tmp_path, content)
   252	    result = ca.attest(log)
   253	    a4 = next(c for c in result.checks if c.check_id == "A4")
   254	    assert a4.verdict == "PASS"
   255	
   256	
   257	# ---------------------------------------------------------------------------
   258	# A5 bounding_recurrence
   259	# ---------------------------------------------------------------------------
   260	

exec
/bin/zsh -lc "nl -ba ui/backend/tests/test_convergence_attestor.py | sed -n '261,520p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   261	def test_a5_hazard_on_recurrent_bounding(tmp_path: Path) -> None:
   262	    """≥30% of last 50 iterations with `bounding k` → HAZARD."""
   263	    blocks = []
   264	    for i in range(60):
   265	        blocks.append(f"Time = {i}")
   266	        if i >= 20:  # last 40 iterations all bound k
   267	            blocks.append("bounding k, min: -1e-3 max: 1.0 average: 0.5")
   268	    log = _write_log(tmp_path, "\n".join(blocks) + "\n")
   269	    result = ca.attest(log)
   270	    a5 = next(c for c in result.checks if c.check_id == "A5")
   271	    assert a5.verdict == "HAZARD"
   272	    assert a5.evidence["per_field_fraction"]["k"] >= 0.30
   273	
   274	
   275	def test_a5_passes_on_early_bounding_only(tmp_path: Path) -> None:
   276	    """Bounding in early transient but not in final window → PASS."""
   277	    blocks = []
   278	    for i in range(60):
   279	        blocks.append(f"Time = {i}")
   280	        if i < 5:  # only first 5 iterations bound
   281	            blocks.append("bounding k, min: -1e-3 max: 1.0 average: 0.5")
   282	    log = _write_log(tmp_path, "\n".join(blocks) + "\n")
   283	    result = ca.attest(log)
   284	    a5 = next(c for c in result.checks if c.check_id == "A5")
   285	    assert a5.verdict == "PASS"
   286	
   287	
   288	# ---------------------------------------------------------------------------
   289	# A6 no_residual_progress
   290	# ---------------------------------------------------------------------------
   291	
   292	def test_a6_hazard_on_high_plateau(tmp_path: Path) -> None:
   293	    """Ux stuck at 0.4 ± 0.02 for 60 iterations → HAZARD (high and flat)."""
   294	    lines = []
   295	    for _ in range(60):
   296	        lines.append(
   297	            "smoothSolver:  Solving for Ux, Initial residual = 0.4, "
   298	            "Final residual = 0.3, No Iterations 20"
   299	        )
   300	    log = _write_log(tmp_path, "\n".join(lines) + "\n")
   301	    result = ca.attest(log)
   302	    a6 = next(c for c in result.checks if c.check_id == "A6")
   303	    assert a6.verdict == "HAZARD"
   304	
   305	
   306	def test_a6_ignores_converged_plateau(tmp_path: Path) -> None:
   307	    """Ux stuck at 1e-5 (below A3 floor) is converged, not stuck → PASS.
   308	
   309	    Codex nit: A6 should not false-positive on fully converged cases
   310	    where residuals hit machine-noise and oscillate in the floor."""
   311	    lines = []
   312	    for _ in range(60):
   313	        lines.append(
   314	            "smoothSolver:  Solving for Ux, Initial residual = 1e-05, "
   315	            "Final residual = 1e-06, No Iterations 2"
   316	        )
   317	    log = _write_log(tmp_path, "\n".join(lines) + "\n")
   318	    result = ca.attest(log)
   319	    a6 = next(c for c in result.checks if c.check_id == "A6")
   320	    assert a6.verdict == "PASS"
   321	
   322	
   323	# ---------------------------------------------------------------------------
   324	# Real-log integration tests (guarded by file presence)
   325	# ---------------------------------------------------------------------------
   326	
   327	_FIELDS = Path("/Users/Zhuanz/Desktop/cfd-harness-unified/reports/phase5_fields")
   328	
   329	
   330	def _resolve_latest_log(case: str) -> Path | None:
   331	    case_dir = _FIELDS / case
   332	    if not case_dir.is_dir():
   333	        return None
   334	    ts_candidates = [d for d in case_dir.iterdir() if d.is_dir() and d.name != "runs"]
   335	    if not ts_candidates:
   336	        return None
   337	    ts_dir = sorted(ts_candidates)[-1]
   338	    logs = list(ts_dir.glob("log.*"))
   339	    return logs[0] if logs else None
   340	
   341	
   342	def test_attestor_ldc_real_log_is_pass() -> None:
   343	    """LDC is the gold-overlay PASS reference. Attestor MUST stay clean."""
   344	    log = _resolve_latest_log("lid_driven_cavity")
   345	    if log is None:
   346	        pytest.skip("LDC phase7a log absent")
   347	    result = ca.attest(log)
   348	    assert result.overall == "ATTEST_PASS", (
   349	        f"LDC attestor tripped unexpectedly: {[(c.check_id, c.verdict, c.summary) for c in result.checks if c.verdict != 'PASS']}"
   350	    )
   351	
   352	
   353	def test_attestor_bfs_real_log_is_hazard_plus_gate_fail() -> None:
   354	    """BFS solver exploded (Codex audit: k≈1e30, ε≈1e30, sum_local≈1e18).
   355	
   356	    Post DEC-038 round-1 A2/G5 split-brain fix: attestor alone returns
   357	    ATTEST_HAZARD (A2 HAZARD + A3 HAZARD + A5 HAZARD — no FAIL-tier check
   358	    fires because A4 is clean, A1 is clean). The FAIL contract status
   359	    comes from the G5 gate at the gate layer catching sum_local > 1e-2.
   360	
   361	    This test asserts the attestor HAZARD verdict; contract-FAIL coverage
   362	    lives in test_comparator_gates_g3_g4_g5.py::test_gates_fire_on_real_bfs_audit_log.
   363	    """
   364	    log = _resolve_latest_log("backward_facing_step")
   365	    if log is None:
   366	        pytest.skip("BFS phase7a log absent")
   367	    result = ca.attest(log)
   368	    assert result.overall == "ATTEST_HAZARD", f"got {result.overall}"
   369	    # Multiple HAZARD-tier concerns should be present.
   370	    hazard_checks = [c for c in result.checks if c.verdict == "HAZARD"]
   371	    assert len(hazard_checks) >= 2
   372	    # A2 in particular must fire (sum_local=5.25e+18).
   373	    a2 = next(c for c in result.checks if c.check_id == "A2")
   374	    assert a2.verdict == "HAZARD"

web search: 
web search: 
codex
实现里已经暴露出一个偏差：模块头注释直接写“per-case override not wired”，而 DEC 明确要求 YAML 覆盖。我继续追两条线：`parse_solver_log` 是否给 A1/A2/A4 喂对数据，以及仓库里阈值文件到底有没有落地。
exec
/bin/zsh -lc "nl -ba ui/backend/services/validation_report.py | sed -n '520,760p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba src/comparator_gates.py | sed -n '281,520p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba src/comparator_gates.py | sed -n '1,280p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   520	    measurement_doc: dict[str, Any] | None,
   521	) -> list[DecisionLink]:
   522	    if not measurement_doc:
   523	        return []
   524	    out: list[DecisionLink] = []
   525	    for row in measurement_doc.get("decisions_trail", []) or []:
   526	        out.append(
   527	            DecisionLink(
   528	                decision_id=row.get("decision_id", ""),
   529	                date=row.get("date", ""),
   530	                title=row.get("title", ""),
   531	                autonomous=bool(row.get("autonomous", False)),
   532	            )
   533	        )
   534	    return out
   535	
   536	
   537	def _derive_contract_status(
   538	    gs_ref: GoldStandardReference,
   539	    measurement: MeasuredValue | None,
   540	    preconditions: list[Precondition],
   541	    audit_concerns: list[AuditConcern],
   542	) -> tuple[ContractStatus, float | None, bool | None, float, float]:
   543	    """Compute the three-state contract status + tolerance bounds.
   544	
   545	    Returns (status, deviation_pct, within_tolerance, lower, upper)."""
   546	    # For negative ref_values the naive (1-tol)*ref > (1+tol)*ref, so
   547	    # take min/max to keep `lower` as the numerically smaller bound.
   548	    # This matters for LDC where u_centerline can be negative near the
   549	    # bottom-left corner (Ghia Re=100 at y=0.0625 gives u/U = -0.03717).
   550	    bound_a = gs_ref.ref_value * (1.0 - gs_ref.tolerance_pct)
   551	    bound_b = gs_ref.ref_value * (1.0 + gs_ref.tolerance_pct)
   552	    lower = min(bound_a, bound_b)
   553	    upper = max(bound_a, bound_b)
   554	
   555	    if measurement is None:
   556	        return ("UNKNOWN", None, None, lower, upper)
   557	
   558	    # DEC-V61-036 G1 + DEC-V61-036b G3/G4/G5 + DEC-V61-038 A1/A4:
   559	    # hard-FAIL concern codes. When any of these concerns are present,
   560	    # the measurement cannot be trusted regardless of whether it lies
   561	    # inside the gold tolerance band.
   562	    #   G1  MISSING_TARGET_QUANTITY    — schema mismatch (extractor missed gold quantity)
   563	    #   G3  VELOCITY_OVERFLOW           — |U|_max > 100·U_ref
   564	    #   G4  TURBULENCE_NEGATIVE         — k/eps/omega < 0 at last iter or overflow
   565	    #   G5  CONTINUITY_DIVERGED         — sum_local > 1e-2 or |cum| > 1
   566	    #   A1  SOLVER_CRASH_LOG            — FOAM FATAL / stack-trace in log
   567	    #   A4  SOLVER_ITERATION_CAP        — pressure loop hit cap ≥3 consecutive iters
   568	    # A2/A3/A5/A6 are HAZARD tier — they record concerns but don't hard-FAIL
   569	    # (some cases physically operate at high residuals; promotion to FAIL
   570	    # via per-case override lands in a future DEC).
   571	    _HARD_FAIL_CONCERNS = {
   572	        "MISSING_TARGET_QUANTITY",
   573	        "VELOCITY_OVERFLOW",
   574	        "TURBULENCE_NEGATIVE",
   575	        "CONTINUITY_DIVERGED",
   576	        "SOLVER_CRASH_LOG",
   577	        "SOLVER_ITERATION_CAP",
   578	    }
   579	    has_hard_fail = any(
   580	        c.concern_type in _HARD_FAIL_CONCERNS for c in audit_concerns
   581	    )
   582	    if measurement.value is None or has_hard_fail:
   583	        # Codex DEC-036b round-1 feedback: when a hard-fail concern fires,
   584	        # the scalar measurement cannot be trusted even if it happens to lie
   585	        # in the tolerance band. Returning `within_tolerance=True` under a
   586	        # FAIL verdict rendered as "Within band: yes" while status was FAIL,
   587	        # which is materially confusing. Null the `within` flag whenever
   588	        # the verdict is hard-failed — the UI now renders "—" in that column.
   589	        if measurement.value is None:
   590	            return ("FAIL", None, None, lower, upper)
   591	        dev_pct = 0.0
   592	        if gs_ref.ref_value != 0.0:
   593	            dev_pct = (measurement.value - gs_ref.ref_value) / gs_ref.ref_value * 100.0
   594	        return ("FAIL", dev_pct, None, lower, upper)
   595	
   596	    deviation_pct = 0.0
   597	    if gs_ref.ref_value != 0.0:
   598	        deviation_pct = (measurement.value - gs_ref.ref_value) / gs_ref.ref_value * 100.0
   599	
   600	    # Tolerance test in deviation space (sign-invariant + consistent with
   601	    # the percentage shown in the UI). `within_tolerance` matches when
   602	    # |deviation| <= tolerance_pct expressed as a percentage.
   603	    within = abs(deviation_pct) <= gs_ref.tolerance_pct * 100.0
   604	    precondition_fails = any(not p.satisfied for p in preconditions)
   605	    has_silent_pass_hazard = any(
   606	        "SILENT_PASS_HAZARD" in c.concern_type or "SILENT_PASS_HAZARD" in (c.summary or "")
   607	        or "SILENT_PASS_HAZARD" in (c.detail or "")
   608	        for c in audit_concerns
   609	    )
   610	
   611	    if not within:
   612	        return ("FAIL", deviation_pct, within, lower, upper)
   613	    if precondition_fails or has_silent_pass_hazard:
   614	        return ("HAZARD", deviation_pct, within, lower, upper)
   615	    return ("PASS", deviation_pct, within, lower, upper)
   616	
   617	
   618	def _make_attestation(
   619	    doc: dict[str, Any] | None,
   620	) -> AttestorVerdict | None:
   621	    """DEC-V61-040: lift `attestation` block from the fixture into the API.
   622	
   623	    The attestor runs at audit-fixture time (see scripts/phase5_audit_run.py)
   624	    and writes `{overall, checks[]}` onto the measurement doc. Two states:
   625	
   626	    - Block absent (legacy fixtures, reference / visual_only tiers with no
   627	      solver log): returns None. The UI renders "no solver log available".
   628	    - Block present with `overall: ATTEST_NOT_APPLICABLE`: returns a verdict
   629	      object with that overall — a first-class "we looked and nothing to
   630	      assert" state, per Codex DEC-040 round-1 CFD opinion (Q4b).
   631	
   632	    Malformed blocks fail loudly (ValueError) rather than silently returning
   633	    None — an audit-evidence path should never hide fixture corruption.
   634	    This closes Codex round-1 FLAG on lenient parsing.
   635	    """
   636	    if not doc:
   637	        return None
   638	    block = doc.get("attestation")
   639	    if block is None:
   640	        return None
   641	    if not isinstance(block, dict):
   642	        raise ValueError(
   643	            f"attestation must be a mapping, got {type(block).__name__}"
   644	        )
   645	    overall = block.get("overall")
   646	    valid_overalls = (
   647	        "ATTEST_PASS", "ATTEST_HAZARD", "ATTEST_FAIL", "ATTEST_NOT_APPLICABLE"
   648	    )
   649	    if overall not in valid_overalls:
   650	        raise ValueError(
   651	            f"attestation.overall must be one of {valid_overalls}, "
   652	            f"got {overall!r}"
   653	        )
   654	    checks_raw = block.get("checks") or []
   655	    if not isinstance(checks_raw, list):
   656	        raise ValueError(
   657	            f"attestation.checks must be a list, got {type(checks_raw).__name__}"
   658	        )
   659	    checks: list[AttestorCheck] = []
   660	    for entry in checks_raw:
   661	        if not isinstance(entry, dict):
   662	            raise ValueError(
   663	                f"attestation.checks[] entry must be a mapping, "
   664	                f"got {type(entry).__name__}"
   665	            )
   666	        verdict = entry.get("verdict")
   667	        if verdict not in ("PASS", "HAZARD", "FAIL"):
   668	            raise ValueError(
   669	                f"attestation.checks[{entry.get('check_id', '?')}].verdict "
   670	                f"must be PASS/HAZARD/FAIL, got {verdict!r}"
   671	            )
   672	        checks.append(
   673	            AttestorCheck(
   674	                check_id=entry.get("check_id", ""),
   675	                verdict=verdict,
   676	                concern_type=entry.get("concern_type"),
   677	                summary=entry.get("summary", "") or "",
   678	            )
   679	        )
   680	    # Codex DEC-040 round-2 FLAG: checks:[] is only physically valid for
   681	    # ATTEST_NOT_APPLICABLE (the attestor bails early with no checks when
   682	    # there's no log). Any other overall with empty checks is a corrupt
   683	    # fixture — fail closed at the parsing boundary rather than letting
   684	    # the UI render a contradictory "ATTEST PASS + no solver log" badge.
   685	    if overall == "ATTEST_NOT_APPLICABLE":
   686	        if checks:
   687	            raise ValueError(
   688	                f"attestation.overall=ATTEST_NOT_APPLICABLE must have empty "
   689	                f"checks[], got {len(checks)} entries"
   690	            )
   691	    else:
   692	        if not checks:
   693	            raise ValueError(
   694	                f"attestation.overall={overall} requires non-empty checks[]; "
   695	                f"only ATTEST_NOT_APPLICABLE may have an empty checks array"
   696	            )
   697	    return AttestorVerdict(overall=overall, checks=checks)
   698	
   699	
   700	def _make_measurement(doc: dict[str, Any] | None) -> MeasuredValue | None:
   701	    if not doc:
   702	        return None
   703	    m = doc.get("measurement") or {}
   704	    if "value" not in m:
   705	        return None
   706	    # DEC-V61-036 G1: value may be explicit None when extractor could not
   707	    # locate the gold's target quantity. Preserve None instead of coercing
   708	    # to 0.0 — the verdict engine hard-FAILs on None per the G1 contract.
   709	    raw_value = m["value"]
   710	    value: float | None
   711	    if raw_value is None:
   712	        value = None
   713	    else:
   714	        value = float(raw_value)
   715	    return MeasuredValue(
   716	        value=value,
   717	        unit=m.get("unit", "") or "",
   718	        source=doc.get("source", "fixture"),
   719	        run_id=m.get("run_id"),
   720	        commit_sha=m.get("commit_sha"),
   721	        measured_at=m.get("measured_at"),
   722	        quantity=m.get("quantity"),
   723	        extraction_source=m.get("extraction_source"),
   724	    )
   725	
   726	
   727	# ---------------------------------------------------------------------------
   728	# Public service functions
   729	# ---------------------------------------------------------------------------
   730	def list_cases() -> list[CaseIndexEntry]:
   731	    whitelist = _load_whitelist()
   732	    out: list[CaseIndexEntry] = []
   733	    for cid, case in whitelist.items():
   734	        gs = _load_gold_standard(cid)
   735	        # Use the same default-run resolution as build_validation_report so
   736	        # the catalog contract_status matches what the Compare tab shows on
   737	        # first click (reference_pass preferred → student's first impression
   738	        # is PASS when curated).
   739	        default_run_id = _pick_default_run_id(cid)
   740	        measurement_doc = (
   741	            _load_run_measurement(cid, default_run_id) if default_run_id else None
   742	        )
   743	        gs_ref = _make_gold_reference(case, gs)
   744	        preconditions = _make_preconditions(gs)
   745	        audit_concerns = _make_audit_concerns(gs, measurement_doc)
   746	        measurement = _make_measurement(measurement_doc)
   747	        if gs_ref is not None:
   748	            status, *_ = _derive_contract_status(
   749	                gs_ref, measurement, preconditions, audit_concerns
   750	            )
   751	        else:
   752	            status = "UNKNOWN"
   753	        # Run distribution for the catalog-card badge. Evaluate every run
   754	        # through the actual contract engine — never report `expected_verdict`,
   755	        # which is only a curator hint and can drift from the live contract
   756	        # (e.g. a `PASS`-hinted run whose gold arms a silent-pass hazard).
   757	        runs = list_runs(cid)
   758	        verdict_counts: dict[str, int] = {}
   759	        for r in runs:
   760	            run_doc = _load_run_measurement(cid, r.run_id)

 succeeded in 0ms:
   281	                    "the gold tolerance band."
   282	                )[:2000],
   283	                evidence={"u_max": u_max, "U_ref": U_ref, "threshold": threshold},
   284	            )
   285	        )
   286	        return violations
   287	
   288	    # Log-epsilon proxy fallback when VTK unavailable.
   289	    if log_stats is not None:
   290	        eps_bound = log_stats.bounding_last.get("epsilon")
   291	        if eps_bound is not None:
   292	            eps_max = eps_bound.get("max")
   293	            if _exceeds_threshold(eps_max, G3_EPSILON_PROXY_MAX):
   294	                violations.append(
   295	                    GateViolation(
   296	                        gate_id="G3",
   297	                        concern_type="VELOCITY_OVERFLOW",
   298	                        summary=(
   299	                            f"epsilon max={eps_max:.3g} implies "
   300	                            f"|U|~{eps_max**(1/3):.2g} (VTK-proxy)"
   301	                        )[:240],
   302	                        detail=(
   303	                            f"DEC-V61-036b G3 (VTK-unavailable fallback): "
   304	                            f"log shows final epsilon max={eps_max:.6g}, "
   305	                            f"above proxy threshold {G3_EPSILON_PROXY_MAX:.0g}. "
   306	                            "Since ε~u³/L, this implies |U| is catastrophically "
   307	                            "large. Velocity overflow flagged from log."
   308	                        )[:2000],
   309	                        evidence={
   310	                            "epsilon_max": eps_max,
   311	                            "proxy_threshold": G3_EPSILON_PROXY_MAX,
   312	                            "inferred_u": eps_max ** (1.0 / 3.0),
   313	                        },
   314	                    )
   315	                )
   316	    return violations
   317	
   318	
   319	def _check_g4_turbulence_negativity(
   320	    log_stats: Optional[LogStats],
   321	) -> list[GateViolation]:
   322	    """G4: k/epsilon/omega min < 0 at last bounding line OR max > overflow."""
   323	    violations: list[GateViolation] = []
   324	    if log_stats is None:
   325	        return violations
   326	
   327	    for field_name, bounds in log_stats.bounding_last.items():
   328	        f_min = bounds.get("min")
   329	        f_max = bounds.get("max")
   330	        # NaN → treat as "catastrophically wrong" → fire gate.
   331	        if f_min is not None and (
   332	            math.isnan(f_min) or math.isinf(f_min) or f_min < 0.0
   333	        ):
   334	            violations.append(
   335	                GateViolation(
   336	                    gate_id="G4",
   337	                    concern_type="TURBULENCE_NEGATIVE",
   338	                    summary=(
   339	                        f"{field_name} min={f_min:.3g} is negative at last iter"
   340	                    )[:240],
   341	                    detail=(
   342	                        f"DEC-V61-036b G4: final `bounding {field_name}` "
   343	                        f"line shows min={f_min:.6g} (< 0), max={f_max}. "
   344	                        "Turbulence fields cannot be physically negative; "
   345	                        "this indicates solver inconsistency even if "
   346	                        "OpenFOAM's internal bounding clipped the value "
   347	                        "to a small positive before the next step."
   348	                    )[:2000],
   349	                    evidence={
   350	                        "field": field_name,
   351	                        "min": f_min,
   352	                        "max": f_max,
   353	                    },
   354	                )
   355	            )
   356	            continue
   357	        if _exceeds_threshold(f_max, G4_TURBULENCE_MAX_OVERFLOW):
   358	            violations.append(
   359	                GateViolation(
   360	                    gate_id="G4",
   361	                    concern_type="TURBULENCE_NEGATIVE",
   362	                    summary=(
   363	                        f"{field_name} max={f_max:.3g} overflow "
   364	                        f"(> {G4_TURBULENCE_MAX_OVERFLOW:.0g})"
   365	                    )[:240],
   366	                    detail=(
   367	                        f"DEC-V61-036b G4 (overflow branch): final `bounding "
   368	                        f"{field_name}` shows max={f_max:.6g}, above "
   369	                        f"{G4_TURBULENCE_MAX_OVERFLOW:.0g}. For realistic "
   370	                        "industrial RANS cases this magnitude is non-physical; "
   371	                        "likely a divergence signature bounded from below."
   372	                    )[:2000],
   373	                    evidence={
   374	                        "field": field_name,
   375	                        "min": f_min,
   376	                        "max": f_max,
   377	                        "threshold": G4_TURBULENCE_MAX_OVERFLOW,
   378	                    },
   379	                )
   380	            )
   381	    return violations
   382	
   383	
   384	def _check_g5_continuity_divergence(
   385	    log_stats: Optional[LogStats],
   386	) -> list[GateViolation]:
   387	    """G5: last-iter sum_local > 1e-2 OR |cumulative| > 1.0."""
   388	    violations: list[GateViolation] = []
   389	    if log_stats is None:
   390	        return violations
   391	
   392	    sum_local = log_stats.final_continuity_sum_local
   393	    cumulative = log_stats.final_continuity_cumulative
   394	
   395	    if _exceeds_threshold(sum_local, G5_SUM_LOCAL_MAX):
   396	        violations.append(
   397	            GateViolation(
   398	                gate_id="G5",
   399	                concern_type="CONTINUITY_DIVERGED",
   400	                summary=(
   401	                    f"continuity sum_local={sum_local:.3g} > "
   402	                    f"{G5_SUM_LOCAL_MAX:.0e}"
   403	                )[:240],
   404	                detail=(
   405	                    f"DEC-V61-036b G5: final-iteration continuity error "
   406	                    f"sum_local={sum_local:.6g} exceeds the incompressible "
   407	                    f"steady floor {G5_SUM_LOCAL_MAX:.0e}. SIMPLE/PISO "
   408	                    "pressure-velocity coupling has not converged; any "
   409	                    "extracted scalar is unreliable."
   410	                )[:2000],
   411	                evidence={
   412	                    "sum_local": sum_local,
   413	                    "cumulative": cumulative,
   414	                    "threshold": G5_SUM_LOCAL_MAX,
   415	                },
   416	            )
   417	        )
   418	        return violations  # sum_local already FAILs; don't double-flag
   419	
   420	    if _abs_exceeds_threshold(cumulative, G5_CUMULATIVE_ABS_MAX):
   421	        violations.append(
   422	            GateViolation(
   423	                gate_id="G5",
   424	                concern_type="CONTINUITY_DIVERGED",
   425	                summary=(
   426	                    f"continuity cumulative={cumulative:.3g}, "
   427	                    f"|cum| > {G5_CUMULATIVE_ABS_MAX}"
   428	                )[:240],
   429	                detail=(
   430	                    f"DEC-V61-036b G5: final-iteration cumulative continuity "
   431	                    f"error {cumulative:.6g} exceeds sanity threshold "
   432	                    f"{G5_CUMULATIVE_ABS_MAX}. This is hard divergence — "
   433	                    "the solver state does not satisfy mass conservation."
   434	                )[:2000],
   435	                evidence={
   436	                    "sum_local": sum_local,
   437	                    "cumulative": cumulative,
   438	                    "threshold": G5_CUMULATIVE_ABS_MAX,
   439	                },
   440	            )
   441	        )
   442	    return violations
   443	
   444	
   445	# ---------------------------------------------------------------------------
   446	# Public entry point
   447	# ---------------------------------------------------------------------------
   448	
   449	def check_all_gates(
   450	    log_path: Optional[Path] = None,
   451	    vtk_dir: Optional[Path] = None,
   452	    U_ref: float = 1.0,
   453	) -> list[GateViolation]:
   454	    """Run G3 + G4 + G5 and return the aggregated list of violations.
   455	
   456	    Called from `scripts/phase5_audit_run.py::_audit_fixture_doc` after
   457	    G1 extraction. Each violation becomes an `audit_concerns[]` entry;
   458	    `ui/backend/services/validation_report._derive_contract_status`
   459	    hard-FAILs when any of the concern codes is present.
   460	    """
   461	    log_stats: Optional[LogStats] = None
   462	    if log_path is not None and log_path.is_file():
   463	        log_stats = parse_solver_log(log_path)
   464	
   465	    violations: list[GateViolation] = []
   466	    violations.extend(_check_g3_velocity_overflow(log_stats, vtk_dir, U_ref))
   467	    violations.extend(_check_g4_turbulence_negativity(log_stats))
   468	    violations.extend(_check_g5_continuity_divergence(log_stats))
   469	    return violations
   470	
   471	
   472	def violation_to_audit_concern_dict(v: GateViolation) -> dict[str, Any]:
   473	    """Serialize a GateViolation as an audit_concerns[] fixture entry."""
   474	    return {
   475	        "concern_type": v.concern_type,
   476	        "summary": v.summary,
   477	        "detail": v.detail,
   478	        "decision_refs": ["DEC-V61-036b"],
   479	        "evidence": v.evidence,
   480	    }

 succeeded in 0ms:
     1	"""DEC-V61-036b: Hard comparator gates G3/G4/G5 — post-extraction physics gates.
     2	
     3	Trigger FAIL on:
     4	  * G3 VELOCITY_OVERFLOW  — |U|_max > K * U_ref (K=100 default). VTK-based,
     5	    with log-based epsilon proxy fallback (epsilon ~ u^3/L).
     6	  * G4 TURBULENCE_NEGATIVE — k/epsilon/omega min < 0 at last bounding line
     7	    OR max > 1e+10 (sanity overflow).
     8	  * G5 CONTINUITY_DIVERGED — last-iter sum_local > 1e-2 OR |cumulative| > 1.
     9	
    10	Operates on artifacts already written by the audit pipeline:
    11	  * `reports/phase5_fields/{case_id}/{ts}/log.simpleFoam` (or .pimpleFoam,
    12	    .icoFoam, .buoyantSimpleFoam)
    13	  * `reports/phase5_fields/{case_id}/{ts}/VTK/*.vtk` (latest time step)
    14	
    15	See the accompanying DEC file for ground-truth evidence from the BFS run
    16	(cumulative=-1434.64, k min=-6.41e+30) and expected gate outcomes.
    17	"""
    18	
    19	from __future__ import annotations
    20	
    21	import math
    22	import re
    23	from dataclasses import dataclass, field
    24	from pathlib import Path
    25	from typing import Any, Optional
    26	
    27	
    28	def _exceeds_threshold(value: Optional[float], threshold: float) -> bool:
    29	    """True when value is NaN, ±inf, OR finite-and-above threshold.
    30	
    31	    Codex DEC-036b round-1 feedback: plain `value > threshold` returns False
    32	    for NaN, which would silently pass the worst blowup mode. NaN and +inf
    33	    must fire the gate unconditionally.
    34	    """
    35	    if value is None:
    36	        return False
    37	    if math.isnan(value) or math.isinf(value):
    38	        return True
    39	    return value > threshold
    40	
    41	
    42	def _abs_exceeds_threshold(value: Optional[float], threshold: float) -> bool:
    43	    """|value| > threshold with NaN/Inf guard (same semantics as above)."""
    44	    if value is None:
    45	        return False
    46	    if math.isnan(value) or math.isinf(value):
    47	        return True
    48	    return abs(value) > threshold
    49	
    50	# ---------------------------------------------------------------------------
    51	# Thresholds (tunable via per-case override in future; seeded from Codex
    52	# round-1 physics audit on DEC-V61-036).
    53	# ---------------------------------------------------------------------------
    54	
    55	G3_VELOCITY_RATIO_MAX = 100.0     # |U|_max / U_ref
    56	G3_EPSILON_PROXY_MAX = 1.0e10     # fallback when VTK unavailable
    57	G4_TURBULENCE_MAX_OVERFLOW = 1.0e10  # any k/eps/omega max above this = overflow
    58	G5_SUM_LOCAL_MAX = 1.0e-2         # incompressible steady floor
    59	G5_CUMULATIVE_ABS_MAX = 1.0       # hard divergence floor
    60	
    61	
    62	# ---------------------------------------------------------------------------
    63	# Data model
    64	# ---------------------------------------------------------------------------
    65	
    66	@dataclass
    67	class GateViolation:
    68	    """A single post-extraction gate FAIL.
    69	
    70	    The fixture writer forwards these to audit_concerns[] and the
    71	    validation_report verdict engine hard-FAILs on any violation.
    72	    """
    73	
    74	    gate_id: str          # "G3" | "G4" | "G5"
    75	    concern_type: str     # "VELOCITY_OVERFLOW" | "TURBULENCE_NEGATIVE" | "CONTINUITY_DIVERGED"
    76	    summary: str
    77	    detail: str
    78	    evidence: dict = field(default_factory=dict)
    79	
    80	
    81	@dataclass
    82	class LogStats:
    83	    """Parsed telemetry from an OpenFOAM solver log."""
    84	
    85	    final_continuity_sum_local: Optional[float] = None
    86	    final_continuity_cumulative: Optional[float] = None
    87	    # Per-field (k/epsilon/omega) last-iter bounding stats.
    88	    bounding_last: dict[str, dict[str, float]] = field(default_factory=dict)
    89	    # Fatal errors (FOAM FATAL, floating exception).
    90	    fatal_detected: bool = False
    91	    fatal_lines: list[str] = field(default_factory=list)
    92	
    93	
    94	# ---------------------------------------------------------------------------
    95	# Log parsing
    96	# ---------------------------------------------------------------------------
    97	
    98	# Codex DEC-036b round-1 feedback: token classes below must also accept
    99	# `nan` / `inf` (case-insensitive). When OpenFOAM's floating-point output
   100	# overflows past double range it prints `nan` or `-inf`, and if the regex
   101	# rejected those tokens, the worst blowup mode would silently bypass the
   102	# gates. Each token class is `[\deE+.\-]+|nan|[+\-]?inf` (case-folded).
   103	_NUM_TOKEN = r"(?:[\deE+.\-]+|[nN][aA][nN]|[+\-]?[iI][nN][fF])"
   104	
   105	_CONTINUITY_RE = re.compile(
   106	    r"time step continuity errors\s*:\s*sum local\s*=\s*(" + _NUM_TOKEN + r")\s*,"
   107	    r"\s*global\s*=\s*" + _NUM_TOKEN + r"\s*,"
   108	    r"\s*cumulative\s*=\s*(" + _NUM_TOKEN + r")"
   109	)
   110	
   111	# Matches "bounding k, min: -1.23 max: 4.56 average: 0.1" — the comma+space
   112	# between min and max varies across OF versions; regex tolerates both.
   113	_BOUNDING_RE = re.compile(
   114	    r"bounding\s+(k|epsilon|omega|nuTilda|nut|nuSgs)\s*,\s*"
   115	    r"min\s*:\s*(" + _NUM_TOKEN + r")\s*,?\s*"
   116	    r"max\s*:\s*(" + _NUM_TOKEN + r")"
   117	)
   118	
   119	
   120	def _parse_foam_number(tok: str) -> Optional[float]:
   121	    """Parse a numeric token that may be `nan`, `inf`, `-inf`, or a
   122	    regular finite float. Returns float (nan/inf allowed — callers compare
   123	    against thresholds and NaN/Inf naturally fail any comparison, which
   124	    is the intended "this value is catastrophically bad" signal)."""
   125	    try:
   126	        return float(tok)
   127	    except (ValueError, TypeError):
   128	        return None
   129	
   130	# Tightened to avoid false-positive on the benign startup line
   131	# `sigFpe : Enabling floating point exception trapping (FOAM_SIGFPE)` which
   132	# announces FPE trapping capability, not an actual exception. The real
   133	# fatal markers are FOAM FATAL (IO )?ERROR + stack-trace frames.
   134	_FATAL_RE = re.compile(
   135	    r"FOAM FATAL (IO )?ERROR|"
   136	    r"#\d+\s+Foam::error::printStack|"
   137	    r"^Floating point exception",
   138	    re.MULTILINE,
   139	)
   140	
   141	
   142	def parse_solver_log(log_path: Path) -> LogStats:
   143	    """Parse continuity + bounding lines + fatal markers from a solver log.
   144	
   145	    Extracts the LAST matching occurrence of each pattern (the end-of-run
   146	    state is what matters for gate decisions). For bounding, keeps
   147	    per-field last-iter min/max.
   148	    """
   149	    stats = LogStats()
   150	    if not log_path.is_file():
   151	        return stats
   152	
   153	    last_continuity: Optional[tuple[float, float]] = None
   154	    last_bounding: dict[str, dict[str, float]] = {}
   155	    fatal_lines: list[str] = []
   156	
   157	    with log_path.open("r", encoding="utf-8", errors="replace") as fh:
   158	        for line in fh:
   159	            m = _CONTINUITY_RE.search(line)
   160	            if m:
   161	                sl = _parse_foam_number(m.group(1))
   162	                cum = _parse_foam_number(m.group(2))
   163	                if sl is not None and cum is not None:
   164	                    last_continuity = (sl, cum)
   165	                continue
   166	            m = _BOUNDING_RE.search(line)
   167	            if m:
   168	                field_name = m.group(1)
   169	                field_min = _parse_foam_number(m.group(2))
   170	                field_max = _parse_foam_number(m.group(3))
   171	                if field_min is not None and field_max is not None:
   172	                    last_bounding[field_name] = {
   173	                        "min": field_min,
   174	                        "max": field_max,
   175	                    }
   176	                continue
   177	            if _FATAL_RE.search(line):
   178	                stats.fatal_detected = True
   179	                if len(fatal_lines) < 5:
   180	                    fatal_lines.append(line.strip()[:240])
   181	
   182	    if last_continuity is not None:
   183	        stats.final_continuity_sum_local = last_continuity[0]
   184	        stats.final_continuity_cumulative = last_continuity[1]
   185	    stats.bounding_last = last_bounding
   186	    stats.fatal_lines = fatal_lines
   187	    return stats
   188	
   189	
   190	# ---------------------------------------------------------------------------
   191	# VTK velocity magnitude
   192	# ---------------------------------------------------------------------------
   193	
   194	def read_final_velocity_max(vtk_dir: Path) -> Optional[float]:
   195	    """Return the max |U| across all cells in the latest-time VTK.
   196	
   197	    Uses pyvista when available. Returns None when VTK unavailable,
   198	    unreadable, or pyvista is not installed — caller treats None as
   199	    "skip G3 VTK branch, use log-epsilon proxy instead".
   200	    """
   201	    if not vtk_dir.is_dir():
   202	        return None
   203	    try:
   204	        import numpy as np
   205	        import pyvista as pv
   206	    except ImportError:
   207	        return None
   208	
   209	    # Find the latest-time VTK file. OpenFOAM foamToVTK lays files as
   210	    # {case}_{timestep}.vtk or allPatches/{case}_{timestep}.vtk. We scan
   211	    # the whole tree under vtk_dir.
   212	    candidates = sorted(vtk_dir.rglob("*.vtk"))
   213	    if not candidates:
   214	        return None
   215	
   216	    u_max_overall: Optional[float] = None
   217	    for vtk_path in candidates:
   218	        try:
   219	            mesh = pv.read(str(vtk_path))
   220	        except Exception:
   221	            continue
   222	        # Look for a vector field named U or velocity.
   223	        point_fields = set(mesh.point_data.keys()) if hasattr(mesh, "point_data") else set()
   224	        cell_fields = set(mesh.cell_data.keys()) if hasattr(mesh, "cell_data") else set()
   225	        U_array = None
   226	        for field_name in ("U", "velocity", "u"):
   227	            if field_name in point_fields:
   228	                U_array = np.asarray(mesh.point_data[field_name])
   229	                break
   230	            if field_name in cell_fields:
   231	                U_array = np.asarray(mesh.cell_data[field_name])
   232	                break
   233	        if U_array is None or U_array.size == 0:
   234	            continue
   235	        # U is typically (N, 3); compute per-cell magnitude.
   236	        if U_array.ndim == 2 and U_array.shape[1] >= 3:
   237	            mags = np.linalg.norm(U_array[:, :3], axis=1)
   238	        else:
   239	            mags = np.abs(U_array.ravel())
   240	        if mags.size == 0:
   241	            continue
   242	        candidate_max = float(np.nanmax(mags))
   243	        if u_max_overall is None or candidate_max > u_max_overall:
   244	            u_max_overall = candidate_max
   245	    return u_max_overall
   246	
   247	
   248	# ---------------------------------------------------------------------------
   249	# Individual gate checks
   250	# ---------------------------------------------------------------------------
   251	
   252	def _check_g3_velocity_overflow(
   253	    log_stats: Optional[LogStats],
   254	    vtk_dir: Optional[Path],
   255	    U_ref: float,
   256	) -> list[GateViolation]:
   257	    """G3: |U|_max > K * U_ref OR epsilon max > G3_EPSILON_PROXY_MAX."""
   258	    violations: list[GateViolation] = []
   259	    threshold = G3_VELOCITY_RATIO_MAX * max(U_ref, 1e-6)
   260	
   261	    u_max: Optional[float] = None
   262	    if vtk_dir is not None:
   263	        u_max = read_final_velocity_max(vtk_dir)
   264	
   265	    if u_max is not None and _exceeds_threshold(u_max, threshold):
   266	        violations.append(
   267	            GateViolation(
   268	                gate_id="G3",
   269	                concern_type="VELOCITY_OVERFLOW",
   270	                summary=(
   271	                    f"|U|_max={u_max:.3g} exceeds {G3_VELOCITY_RATIO_MAX:.0f}·U_ref "
   272	                    f"({threshold:.3g})"
   273	                )[:240],
   274	                detail=(
   275	                    f"DEC-V61-036b G3: reading latest-time VTK cell velocity "
   276	                    f"found |U|_max={u_max:.6g}, which is above the "
   277	                    f"{G3_VELOCITY_RATIO_MAX:.0f}·U_ref sanity ceiling "
   278	                    f"({threshold:.6g}, U_ref={U_ref}). This indicates "
   279	                    "solver divergence or runaway acceleration — the measurement "
   280	                    "cannot be trusted regardless of whether it lies within "

exec
/bin/zsh -lc "rg --files knowledge | rg 'attestor|threshold'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 exited 1 in 0ms:
exec
/bin/zsh -lc 'rg -n "def parse_solver_log|fatal_detected|FOAM FATAL|floating exception|continuity|bounding|_derive_contract_status|ATTTEST|ATTEST|SOLVER_CRASH_LOG|CONTINUITY_NOT_CONVERGED|RESIDUALS_ABOVE_TARGET|SOLVER_ITERATION_CAP|BOUNDING_RECURRENT|NO_RESIDUAL_PROGRESS" src/comparator_gates.py ui/backend/services/validation_report.py knowledge .planning scripts -S' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
ui/backend/services/validation_report.py:479:        # Surfacing as a first-class concern lets _derive_contract_status
ui/backend/services/validation_report.py:537:def _derive_contract_status(
ui/backend/services/validation_report.py:566:    #   A1  SOLVER_CRASH_LOG            — FOAM FATAL / stack-trace in log
ui/backend/services/validation_report.py:567:    #   A4  SOLVER_ITERATION_CAP        — pressure loop hit cap ≥3 consecutive iters
ui/backend/services/validation_report.py:576:        "SOLVER_CRASH_LOG",
ui/backend/services/validation_report.py:577:        "SOLVER_ITERATION_CAP",
ui/backend/services/validation_report.py:628:    - Block present with `overall: ATTEST_NOT_APPLICABLE`: returns a verdict
ui/backend/services/validation_report.py:647:        "ATTEST_PASS", "ATTEST_HAZARD", "ATTEST_FAIL", "ATTEST_NOT_APPLICABLE"
ui/backend/services/validation_report.py:681:    # ATTEST_NOT_APPLICABLE (the attestor bails early with no checks when
ui/backend/services/validation_report.py:684:    # the UI render a contradictory "ATTEST PASS + no solver log" badge.
ui/backend/services/validation_report.py:685:    if overall == "ATTEST_NOT_APPLICABLE":
ui/backend/services/validation_report.py:688:                f"attestation.overall=ATTEST_NOT_APPLICABLE must have empty "
ui/backend/services/validation_report.py:695:                f"only ATTEST_NOT_APPLICABLE may have an empty checks array"
ui/backend/services/validation_report.py:748:            status, *_ = _derive_contract_status(
ui/backend/services/validation_report.py:764:                run_status, *_ = _derive_contract_status(
ui/backend/services/validation_report.py:855:    status, deviation, within, lower, upper = _derive_contract_status(
src/comparator_gates.py:6:  * G4 TURBULENCE_NEGATIVE — k/epsilon/omega min < 0 at last bounding line
src/comparator_gates.py:85:    final_continuity_sum_local: Optional[float] = None
src/comparator_gates.py:86:    final_continuity_cumulative: Optional[float] = None
src/comparator_gates.py:87:    # Per-field (k/epsilon/omega) last-iter bounding stats.
src/comparator_gates.py:88:    bounding_last: dict[str, dict[str, float]] = field(default_factory=dict)
src/comparator_gates.py:89:    # Fatal errors (FOAM FATAL, floating exception).
src/comparator_gates.py:90:    fatal_detected: bool = False
src/comparator_gates.py:106:    r"time step continuity errors\s*:\s*sum local\s*=\s*(" + _NUM_TOKEN + r")\s*,"
src/comparator_gates.py:111:# Matches "bounding k, min: -1.23 max: 4.56 average: 0.1" — the comma+space
src/comparator_gates.py:114:    r"bounding\s+(k|epsilon|omega|nuTilda|nut|nuSgs)\s*,\s*"
src/comparator_gates.py:133:# fatal markers are FOAM FATAL (IO )?ERROR + stack-trace frames.
src/comparator_gates.py:135:    r"FOAM FATAL (IO )?ERROR|"
src/comparator_gates.py:142:def parse_solver_log(log_path: Path) -> LogStats:
src/comparator_gates.py:143:    """Parse continuity + bounding lines + fatal markers from a solver log.
src/comparator_gates.py:146:    state is what matters for gate decisions). For bounding, keeps
src/comparator_gates.py:153:    last_continuity: Optional[tuple[float, float]] = None
src/comparator_gates.py:154:    last_bounding: dict[str, dict[str, float]] = {}
src/comparator_gates.py:164:                    last_continuity = (sl, cum)
src/comparator_gates.py:172:                    last_bounding[field_name] = {
src/comparator_gates.py:178:                stats.fatal_detected = True
src/comparator_gates.py:182:    if last_continuity is not None:
src/comparator_gates.py:183:        stats.final_continuity_sum_local = last_continuity[0]
src/comparator_gates.py:184:        stats.final_continuity_cumulative = last_continuity[1]
src/comparator_gates.py:185:    stats.bounding_last = last_bounding
src/comparator_gates.py:290:        eps_bound = log_stats.bounding_last.get("epsilon")
src/comparator_gates.py:322:    """G4: k/epsilon/omega min < 0 at last bounding line OR max > overflow."""
src/comparator_gates.py:327:    for field_name, bounds in log_stats.bounding_last.items():
src/comparator_gates.py:342:                        f"DEC-V61-036b G4: final `bounding {field_name}` "
src/comparator_gates.py:346:                        "OpenFOAM's internal bounding clipped the value "
src/comparator_gates.py:367:                        f"DEC-V61-036b G4 (overflow branch): final `bounding "
src/comparator_gates.py:384:def _check_g5_continuity_divergence(
src/comparator_gates.py:392:    sum_local = log_stats.final_continuity_sum_local
src/comparator_gates.py:393:    cumulative = log_stats.final_continuity_cumulative
src/comparator_gates.py:401:                    f"continuity sum_local={sum_local:.3g} > "
src/comparator_gates.py:405:                    f"DEC-V61-036b G5: final-iteration continuity error "
src/comparator_gates.py:426:                    f"continuity cumulative={cumulative:.3g}, "
src/comparator_gates.py:430:                    f"DEC-V61-036b G5: final-iteration cumulative continuity "
src/comparator_gates.py:458:    `ui/backend/services/validation_report._derive_contract_status`
src/comparator_gates.py:468:    violations.extend(_check_g5_continuity_divergence(log_stats))
scripts/p2_acceptance_run.py:190:    which forces hard-FAIL in validation_report._derive_contract_status.
.planning/retrospectives/2026-04-22_v61_counter32_retrospective.md:37:| V61-036b | G3/G4/G5 gates | 23→24 | unit/velocity/turb/continuity/residuals | 0 | self-approved | 0.60 |
.planning/retrospectives/2026-04-22_v61_counter32_retrospective.md:108:- **Convergence attestor A1..A6** (DEC-038): pre-extraction 6-check gate that produces ATTESTED / FLAGGED / UNATTESTED verdict independent of numeric gold match.
.planning/STATE.md:277:    - Bug: simpleFoam diverged @ t=102s with continuity error 10^62 → NaN
.planning/STATE.md:353:| naca0012_airfoil | PASS_WITH_DEVIATIONS (permanent, DEC-EX-A) | CONVERGED | DEVIATION (Cp 52.9%/32.4%/45.5%) | Wave 3 CLOSED 2026-04-18: Path W REJECT (geometry-locked y+_min), Path H REJECT (block-face grading discontinuity → NaN). Fuse triggered. DEC-EX-A: accept permanent deviation under blockMesh 6-block scope; snappyHexMesh rewrite deferred to Tier-1 future work. |
.planning/STATE.md:354:| axisymmetric_impinging_jet | PASS_WITH_DEVIATIONS | UNKNOWN (FOAM FATAL) | PASS | adapter_version_mismatch (HIGH) |
.planning/STATE.md:882:   silent-pass hazard armed by gold). Fix: per-run `_derive_contract_status` evaluation.
.planning/STATE.md:1253:    continuity divergence, stuck residuals.
.planning/STATE.md:1272:- DEC-038 attestor round 2: APPROVED_WITH_COMMENTS on `eb51dcf` (fixes + A2/G5 split-brain + ATTEST_NOT_APPLICABLE)
.planning/STATE.md:1279:lid_driven_cavity            ATTEST_PASS       []
.planning/STATE.md:1280:backward_facing_step         ATTEST_HAZARD     [G3,G4,G5]  ← G5 hard-FAILs contract
.planning/STATE.md:1281:circular_cylinder_wake       ATTEST_HAZARD     [G4,G5]     ← G5 hard-FAILs contract
.planning/STATE.md:1282:turbulent_flat_plate         ATTEST_HAZARD     [G3,G4,G5]
.planning/STATE.md:1283:duct_flow                    ATTEST_HAZARD     [G3,G4,G5]
.planning/STATE.md:1284:differential_heated_cavity   ATTEST_PASS       []
.planning/STATE.md:1285:plane_channel_flow           ATTEST_PASS       []  ← DEC-036c G2 territory (u+/y+)
.planning/STATE.md:1286:impinging_jet                ATTEST_FAIL       []  ← A4 p_rgh cap (post-round-2 fix)
.planning/STATE.md:1287:naca0012_airfoil             ATTEST_PASS       []  ← tolerance band too loose
.planning/STATE.md:1288:rayleigh_benard_convection   ATTEST_PASS       []  ← Nu extractor bug
.planning/STATE.md:1293:ATTEST_PASS but Codex physics audit says they physically FAIL — those
.planning/phases/07a-field-capture/07a-03-SUMMARY.md:90:  --> FOAM FATAL IO ERROR: Attempt to return dictionary entry as a primitive
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:10:  ATTEST_FAIL forces contract FAIL before comparator extraction even looks
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:15:    A1 solver_exit_clean   — exit code 0 AND no FOAM FATAL / floating exception in log
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:16:    A2 continuity_floor    — final sum_local ≤ case-specific floor (default 1e-4 incompressible)
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:19:    A5 bounding_recurrence — turbulence bounding fired in ≥30% of last N iterations → fake convergence
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:23:  case can have both ATTEST_FAIL (convergence broken) and G3/G4/G5 FAIL
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:37:  into phase5_audit_run.py + concern types in _derive_contract_status.
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:67:- A1 catches `FOAM FATAL IO ERROR` in the log tail (solver crashed mid-run
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:79:- A5 detects turbulence bounding recurrence — healthy cases bound maybe
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:91:   lets ATTEST_FAIL propagate into fixture metadata early so downstream
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:95:   - A1: `SOLVER_CRASH_LOG` (summary includes first fatal line)
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:96:   - A2: `CONTINUITY_NOT_CONVERGED` (vs G5 `CONTINUITY_DIVERGED`)
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:97:   - A3: `RESIDUALS_ABOVE_TARGET` (includes which fields missed)
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:98:   - A4: `SOLVER_ITERATION_CAP` (includes which solver loop)
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:99:   - A5: `BOUNDING_RECURRENT` (includes field + % of iterations bounded)
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:100:   - A6: `NO_RESIDUAL_PROGRESS` (includes field + decade range)
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:102:3. **Verdict engine integration**: `_derive_contract_status` extends
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:113:     continuity_floor: 1.0e-4
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:116:     bounding_recurrence_frac_threshold: 0.30
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:117:     bounding_recurrence_window: 50
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:129:       # unsteady pimpleFoam — continuity oscillates per-step
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:130:       continuity_floor: 1.0e-3
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:137:| lid_driven_cavity | pass | pass | pass | pass | N/A (laminar) | pass | ATTEST_PASS |
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:138:| backward_facing_step | pass | FAIL | FAIL | pass | FAIL | FAIL | ATTEST_FAIL (redundant with G3/G4/G5) |
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:139:| circular_cylinder_wake | pass | HAZARD | HAZARD | pass | check | check | ATTEST_HAZARD |
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:141:| duct_flow | pass | FAIL | FAIL | pass | FAIL | FAIL | ATTEST_FAIL (redundant with G3/G4/G5) |
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:143:| plane_channel_flow | pass | pass | pass | pass | check | pass | ATTEST_PASS (convergence OK; comparator is the problem) |
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:144:| impinging_jet | pass | pass | HAZARD | **FAIL** | pass | pass | ATTEST_FAIL via A4 |
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:145:| naca0012_airfoil | pass | pass | HAZARD? | pass | pass | pass | ATTEST_PASS or HAZARD |
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:146:| rayleigh_benard_convection | pass | HAZARD | HAZARD | pass | pass | check | ATTEST_HAZARD |
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:155:  - A1 log with `FOAM FATAL IO ERROR` → FAIL
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:159:  - A5 log with 20/50 `bounding k` lines → FAIL
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:165:  ATTEST_PASS (guard against threshold creep).
.planning/phases/07a-field-capture/07a-RESEARCH.md:177:- `sets` function object subsumes the legacy `system/sampleDict` — we can keep emitting `sampleDict` (for comparator continuity per DEC-V61-029) **OR** switch to in-controlDict form. **Recommendation: keep both.** The existing comparator path reads `postProcessing/sets/<time>/uCenterline_U.xy` from either source, and keeping `sampleDict` avoids touching `result_comparator.py`. The in-controlDict `sample` function object writes to `postProcessing/sample/<time>/uCenterline_U_p.xy` (different subdir name = the function-object name) — that's the Phase 7a artifact.
.planning/decisions/2026-04-22_phase8_dec036_hard_comparator_gates_g1.md:17:  "no_numeric_quantity", and `_derive_contract_status` forces FAIL
.planning/decisions/2026-04-22_phase8_dec036_hard_comparator_gates_g1.md:52:  handling for quantity-name comparison in _derive_contract_status;
.planning/decisions/2026-04-22_phase8_dec036_hard_comparator_gates_g1.md:110:- `ui/backend/services/validation_report.py::_derive_contract_status`
.planning/decisions/2026-04-22_phase8_dec040_ui_attestor_surface.md:59:profile=PARTIAL (11/17), attestation=ATTEST_PASS. All three now
.planning/decisions/2026-04-22_phase8_dec040_ui_attestor_surface.md:65:   - `AttestVerdict` Literal (ATTEST_PASS/HAZARD/FAIL/NOT_APPLICABLE)
.planning/decisions/2026-04-22_phase8_dec040_ui_attestor_surface.md:101:   - LDC audit_real_run returns ATTEST_PASS with 6 PASS checks
.planning/decisions/2026-04-22_phase8_dec040_ui_attestor_surface.md:110:attestation.overall: ATTEST_PASS
.planning/decisions/2026-04-22_phase8_dec040_ui_attestor_surface.md:154:  payload `{overall: ATTEST_PASS, checks: []}`. The real attestor only
.planning/decisions/2026-04-22_phase8_dec040_ui_attestor_surface.md:155:  emits empty `checks` for `ATTEST_NOT_APPLICABLE`. The parser accepted
.planning/decisions/2026-04-22_phase8_dec040_ui_attestor_surface.md:158:  ATTEST PASS badge with "No solver log available" copy side-by-side.
.planning/decisions/2026-04-22_phase8_dec040_ui_attestor_surface.md:162:  `ATTEST_NOT_APPLICABLE` has non-empty checks, or any other overall
.planning/decisions/2026-04-22_phase8_dec040_ui_attestor_surface.md:165:  `overall === "ATTEST_NOT_APPLICABLE"` only, never on `checks.length`.
.planning/decisions/2026-04-21_phase7bde_polish_gci_l4.md:116:  so we rebuild `x1d = np.linspace(x_min, x_max, side)` from bounding
.planning/decisions/2026-04-22_phase7_deep_review_pass_washing_fix.md:106:   negative/overflow k-epsilon, continuity-error blowup, stuck residuals.
.planning/decisions/2026-04-22_phase7_deep_review_pass_washing_fix.md:115:   Need post-run attestation: continuity drift, field-magnitude sanity,
.planning/decisions/2026-04-21_phase5_5c1_codex_fixes.md:131:1. Mirror this DEC to Notion (will include M3 for audit continuity).
.planning/decisions/2026-04-22_phase8_dec036b_gates_g3_g4_g5.md:13:    - G5 continuity_divergence: |sum_local| > 1e-2 OR |cumulative| > 1.0
.planning/decisions/2026-04-22_phase8_dec036b_gates_g3_g4_g5.md:29:  calls in phase5_audit_run.py + concern types in _derive_contract_status.
.planning/decisions/2026-04-22_phase8_dec036b_gates_g3_g4_g5.md:58:time step continuity errors : sum local = 5.24523e+18, global = -1328.63, cumulative = -1434.64
.planning/decisions/2026-04-22_phase8_dec036b_gates_g3_g4_g5.md:59:bounding epsilon, min: 7.38706e-17 max: 1.03929e+30 average: 1.37234e+27
.planning/decisions/2026-04-22_phase8_dec036b_gates_g3_g4_g5.md:60:bounding k, min: -6.41351e+30 max: 2.32895e+31 average: 1.39855e+29
.planning/decisions/2026-04-22_phase8_dec036b_gates_g3_g4_g5.md:63:BFS simpleFoam kEpsilon ran to `simpleFoam` exit=0 with continuity blown
.planning/decisions/2026-04-22_phase8_dec036b_gates_g3_g4_g5.md:81:  `bounding epsilon, min: X max: Y` log line at last iter. If Y > 1e+10,
.planning/decisions/2026-04-22_phase8_dec036b_gates_g3_g4_g5.md:90:  **last reported** `bounding X, min: ..., max: ...` line in the log.
.planning/decisions/2026-04-22_phase8_dec036b_gates_g3_g4_g5.md:91:  Silent-clipping during early iters is OK (solver-internal bounding),
.planning/decisions/2026-04-22_phase8_dec036b_gates_g3_g4_g5.md:99:### G5 continuity_divergence
.planning/decisions/2026-04-22_phase8_dec036b_gates_g3_g4_g5.md:120:def parse_solver_log(log_path: Path) -> LogStats:
.planning/decisions/2026-04-22_phase8_dec036b_gates_g3_g4_g5.md:121:    """Regex-extract final bounding lines, continuity line, FOAM FATAL
.planning/decisions/2026-04-22_phase8_dec036b_gates_g3_g4_g5.md:137:    violations.extend(_check_g5_continuity_divergence(log))
.planning/decisions/2026-04-22_phase8_dec036b_gates_g3_g4_g5.md:147:`ui/backend/services/validation_report.py::_derive_contract_status`
.planning/decisions/2026-04-22_phase8_dec036b_gates_g3_g4_g5.md:172:- `test_g4_turbulence_negative_at_last_iter_fail` — log with final `bounding k, min: -5.0` → FAIL
.planning/decisions/2026-04-22_phase8_dec036b_gates_g3_g4_g5.md:173:- `test_g4_turbulence_max_overflow_fail` — log with `bounding epsilon, min: 1e-5, max: 1e+30` → FAIL
.planning/phases/05b-ldc-simplefoam/05b-02-SUMMARY.md:86:`FOAM FATAL ERROR: cannot find file "constant/momentumTransport"`. +28 LOC,
.planning/phases/05b-ldc-simplefoam/05b-02-SUMMARY.md:142:  exited in 4.5s with `solver_success: false`; probe captured `FOAM FATAL ERROR:
.planning/phases/05b-ldc-simplefoam/05b-RESEARCH.md:46:2. Compute p' correction from continuity deficit.
.planning/phases/05b-ldc-simplefoam/05b-RESEARCH.md:63:- `bounded` prefix: ensures steady-state convergence (subtracts a continuity-enforced term). Essential for simpleFoam; unbounded central differencing on steady problems oscillates.
.planning/decisions/2026-04-21_phase6_td024_learn_teaching_runs.md:11:        1 PASS · 2 FAIL"），值由 `_derive_contract_status` 实际评估
.planning/decisions/2026-04-21_phase6_td024_learn_teaching_runs.md:34:  `_derive_contract_status` per run; PNG regenerated with Cooper 1984
.planning/decisions/2026-04-21_phase6_td024_learn_teaching_runs.md:133:        run_status, *_ = _derive_contract_status(

codex
我在看真实工况日志，不只看单元测试。尤其是 LDC 的真实尾部残差、impinging_jet 的 `p_rgh` cap、以及 BFS 的 continuity/bounding 尾窗，这三处最能判断有没有“测到错误对象”或“阈值一碰就翻车”。
exec
/bin/zsh -lc 'latest=$(ls -1 reports/phase5_fields/backward_facing_step | rg -v '"'"'^runs$'"' | sort | tail -n1); echo "'$latest; log=reports/phase5_fields/backward_facing_step/$latest/$(ls reports/phase5_fields/backward_facing_step/$latest | rg '"'"'^log'"\\.'); rg -n \"Time = |time step continuity errors|Solving for Ux|Solving for Uy|Solving for p\\b|bounding k|bounding epsilon|bounding omega\" \""'$log" | tail -n 120' in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc 'latest=$(ls -1 reports/phase5_fields/impinging_jet | rg -v '"'"'^runs$'"' | sort | tail -n1); echo "'$latest; log=reports/phase5_fields/impinging_jet/$latest/$(ls reports/phase5_fields/impinging_jet/$latest | rg '"'"'^log'"\\.'); rg -n \"Time = |Solving for p_rgh|Solving for p\\b|No Iterations 1000|time step continuity errors|bounding \" \""'$log" | tail -n 80' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
20260421T125637Z
315:Time = 22s
317:smoothSolver:  Solving for Ux, Initial residual = 0.266291, Final residual = 0.00242662, No Iterations 12
318:smoothSolver:  Solving for Uy, Initial residual = 0.757177, Final residual = 0.00711499, No Iterations 13
319:GAMG:  Solving for p, Initial residual = 0.915143, Final residual = 0.0047087, No Iterations 6
320:time step continuity errors : sum local = 0.0742275, global = 0.0347611, cumulative = 0.0777378
322:bounding epsilon, min: -0.585969 max: 320.692 average: 3.55064
324:bounding k, min: -0.507422 max: 13.5914 average: 0.411438
325:ExecutionTime = 0.142629 s  ClockTime = 0 s
327:Time = 23s
329:smoothSolver:  Solving for Ux, Initial residual = 0.287214, Final residual = 0.00223607, No Iterations 13
330:smoothSolver:  Solving for Uy, Initial residual = 0.717572, Final residual = 0.00660651, No Iterations 11
331:GAMG:  Solving for p, Initial residual = 0.932284, Final residual = 0.00501801, No Iterations 6
332:time step continuity errors : sum local = 0.15873, global = 0.00832631, cumulative = 0.0860641
334:bounding epsilon, min: -518.762 max: 6664.06 average: 32.6021
336:bounding k, min: -2.569 max: 46.417 average: 0.796533
337:ExecutionTime = 0.144539 s  ClockTime = 0 s
339:Time = 24s
341:smoothSolver:  Solving for Ux, Initial residual = 0.290227, Final residual = 0.00211423, No Iterations 14
342:smoothSolver:  Solving for Uy, Initial residual = 0.701734, Final residual = 0.0053395, No Iterations 11
343:GAMG:  Solving for p, Initial residual = 0.76225, Final residual = 0.00324043, No Iterations 7
344:time step continuity errors : sum local = 0.142639, global = -0.0227242, cumulative = 0.0633399
346:bounding epsilon, min: -324.835 max: 5036.09 average: 47.6972
348:bounding k, min: -1.10123 max: 139.331 average: 2.05464
349:ExecutionTime = 0.146462 s  ClockTime = 0 s
351:Time = 25s
353:smoothSolver:  Solving for Ux, Initial residual = 0.374092, Final residual = 0.00255931, No Iterations 9
354:smoothSolver:  Solving for Uy, Initial residual = 0.68363, Final residual = 0.00655352, No Iterations 10
355:GAMG:  Solving for p, Initial residual = 0.778502, Final residual = 0.00438303, No Iterations 7
356:time step continuity errors : sum local = 0.236125, global = 0.0040659, cumulative = 0.0674058
358:bounding epsilon, min: -7055.28 max: 30416.2 average: 310.477
360:bounding k, min: -28.0286 max: 312.673 average: 4.46247
361:ExecutionTime = 0.148395 s  ClockTime = 0 s
363:Time = 26s
365:smoothSolver:  Solving for Ux, Initial residual = 0.434849, Final residual = 0.00374216, No Iterations 11
366:smoothSolver:  Solving for Uy, Initial residual = 0.765463, Final residual = 0.00693629, No Iterations 11
367:GAMG:  Solving for p, Initial residual = 0.742092, Final residual = 0.00506235, No Iterations 6
368:time step continuity errors : sum local = 0.73206, global = -0.0133951, cumulative = 0.0540106
370:bounding epsilon, min: -8005.51 max: 90243.1 average: 608.897
372:bounding k, min: -90.7673 max: 890.602 average: 9.50073
373:ExecutionTime = 0.150159 s  ClockTime = 0 s
375:Time = 27s
377:smoothSolver:  Solving for Ux, Initial residual = 0.210528, Final residual = 0.00195866, No Iterations 13
378:smoothSolver:  Solving for Uy, Initial residual = 0.377826, Final residual = 0.00301034, No Iterations 15
379:GAMG:  Solving for p, Initial residual = 0.605701, Final residual = 0.00284039, No Iterations 6
380:time step continuity errors : sum local = 0.340363, global = -0.00223133, cumulative = 0.0517793
382:bounding epsilon, min: -308822 max: 876119 average: 2731.81
384:bounding k, min: -165.675 max: 1179.7 average: 15.2121
385:ExecutionTime = 0.152235 s  ClockTime = 0 s
387:Time = 28s
389:smoothSolver:  Solving for Ux, Initial residual = 0.240918, Final residual = 0.00204323, No Iterations 18
390:smoothSolver:  Solving for Uy, Initial residual = 0.4352, Final residual = 0.0041408, No Iterations 14
391:GAMG:  Solving for p, Initial residual = 0.529449, Final residual = 0.00508744, No Iterations 5
392:time step continuity errors : sum local = 0.477007, global = -0.000336432, cumulative = 0.0514429
394:bounding epsilon, min: -1255.94 max: 1.29774e+06 average: 6288.52
396:bounding k, min: -145.407 max: 1812.98 average: 21.0654
397:ExecutionTime = 0.154275 s  ClockTime = 0 s
399:Time = 29s
401:smoothSolver:  Solving for Ux, Initial residual = 0.272343, Final residual = 0.00268049, No Iterations 12
402:smoothSolver:  Solving for Uy, Initial residual = 0.688649, Final residual = 0.0060177, No Iterations 13
403:GAMG:  Solving for p, Initial residual = 0.629693, Final residual = 0.00292344, No Iterations 5
404:time step continuity errors : sum local = 0.443631, global = -0.0034408, cumulative = 0.0480021
406:bounding epsilon, min: -57803.5 max: 1.39718e+06 average: 5948.28
408:bounding k, min: -103.923 max: 2186.9 average: 24.3186
409:ExecutionTime = 0.156121 s  ClockTime = 0 s
411:Time = 30s
413:smoothSolver:  Solving for Ux, Initial residual = 0.321414, Final residual = 0.00264472, No Iterations 8
414:smoothSolver:  Solving for Uy, Initial residual = 0.657154, Final residual = 0.00540342, No Iterations 8
415:GAMG:  Solving for p, Initial residual = 0.601182, Final residual = 0.00337282, No Iterations 6
416:time step continuity errors : sum local = 0.510166, global = -0.00178239, cumulative = 0.0462197
418:bounding epsilon, min: -38161.7 max: 924888 average: 6707.49
420:bounding k, min: -313.484 max: 1714.04 average: 29.5205
421:ExecutionTime = 0.157868 s  ClockTime = 0 s
423:Time = 31s
425:smoothSolver:  Solving for Ux, Initial residual = 0.247931, Final residual = 0.00181956, No Iterations 13
426:smoothSolver:  Solving for Uy, Initial residual = 0.675277, Final residual = 0.00414231, No Iterations 11
427:GAMG:  Solving for p, Initial residual = 0.720576, Final residual = 0.00388767, No Iterations 6
428:time step continuity errors : sum local = 0.68921, global = -0.0233435, cumulative = 0.0228762
430:bounding epsilon, min: -106280 max: 716768 average: 6356.65
432:bounding k, min: -342.527 max: 1545.98 average: 28.7965
433:ExecutionTime = 0.159613 s  ClockTime = 0 s
435:Time = 32s
437:smoothSolver:  Solving for Ux, Initial residual = 0.201125, Final residual = 0.00155932, No Iterations 11
438:smoothSolver:  Solving for Uy, Initial residual = 0.564373, Final residual = 0.00491834, No Iterations 11
439:GAMG:  Solving for p, Initial residual = 0.71026, Final residual = 0.00456214, No Iterations 6
440:time step continuity errors : sum local = 1.01602, global = -0.00111461, cumulative = 0.0217615
442:bounding epsilon, min: -15930.4 max: 963799 average: 5494.93
444:bounding k, min: -52.5853 max: 1966.69 average: 32.4113
445:ExecutionTime = 0.161593 s  ClockTime = 0 s
447:Time = 33s
449:smoothSolver:  Solving for Ux, Initial residual = 0.672095, Final residual = 0.00560551, No Iterations 9
450:smoothSolver:  Solving for Uy, Initial residual = 0.889972, Final residual = 0.00845567, No Iterations 9
451:GAMG:  Solving for p, Initial residual = 0.813762, Final residual = 0.00427376, No Iterations 6
452:time step continuity errors : sum local = 1.21906, global = 0.00132386, cumulative = 0.0230854
454:bounding epsilon, min: -2101.79 max: 9.69776e+06 average: 26433.6
456:bounding k, min: -17.7066 max: 2177.5 average: 41.2723
457:ExecutionTime = 0.163304 s  ClockTime = 0 s
459:Time = 34s
461:smoothSolver:  Solving for Ux, Initial residual = 1, Final residual = 0.00837022, No Iterations 11
462:smoothSolver:  Solving for Uy, Initial residual = 1, Final residual = 0.00757541, No Iterations 15
463:GAMG:  Solving for p, Initial residual = 0.881468, Final residual = 0.00822948, No Iterations 2
464:time step continuity errors : sum local = 1.74393e+10, global = 0.00108283, cumulative = 0.0241682
466:bounding epsilon, min: -1.3272e+14 max: 3.79409e+16 average: 7.99605e+13
468:bounding k, min: -2.92944e+11 max: 9.43286e+11 average: 5.93319e+09
469:ExecutionTime = 0.164957 s  ClockTime = 0 s
471:Time = 35s
473:smoothSolver:  Solving for Ux, Initial residual = 0.78503, Final residual = 0.00674337, No Iterations 17
474:smoothSolver:  Solving for Uy, Initial residual = 0.641696, Final residual = 0.00538723, No Iterations 9
475:GAMG:  Solving for p, Initial residual = 0.835175, Final residual = 0.00496555, No Iterations 8
476:time step continuity errors : sum local = 2.89254e+09, global = -106.032, cumulative = -106.008
478:bounding epsilon, min: -1.29708e+24 max: 1.68914e+25 average: 6.93631e+22
480:bounding k, min: -9.0735e+21 max: 7.57553e+22 average: 1.91511e+20
481:ExecutionTime = 0.166937 s  ClockTime = 0 s
483:Time = 36s
485:smoothSolver:  Solving for Ux, Initial residual = 0.0374628, Final residual = 0.000327544, No Iterations 4
486:smoothSolver:  Solving for Uy, Initial residual = 0.0233626, Final residual = 0.000198486, No Iterations 12
487:GAMG:  Solving for p, Initial residual = 8.83567e-07, Final residual = 8.83567e-07, No Iterations 0
488:time step continuity errors : sum local = 5.24523e+18, global = -1328.63, cumulative = -1434.64
490:bounding epsilon, min: 7.38706e-17 max: 1.03929e+30 average: 1.37234e+27
492:bounding k, min: -6.41351e+30 max: 2.32895e+31 average: 1.39855e+29
493:ExecutionTime = 0.168564 s  ClockTime = 0 s

 succeeded in 0ms:
20260421T142307Z
2522:time step continuity errors : sum local = 1.0109e-07, global = -4.40063e-09, cumulative = 1.68079e-08
2525:ExecutionTime = 131.783 s  ClockTime = 133 s
2528:Time = 940s
2532:GAMG:  Solving for p_rgh, Initial residual = 0.673448, Final residual = 0.39827, No Iterations 1000
2533:time step continuity errors : sum local = 1.05038e-07, global = 3.76588e-09, cumulative = 2.05738e-08
2534:GAMG:  Solving for p_rgh, Initial residual = 0.637939, Final residual = 0.402707, No Iterations 1000
2535:time step continuity errors : sum local = 1.04187e-07, global = 5.00222e-09, cumulative = 2.5576e-08
2538:ExecutionTime = 132.483 s  ClockTime = 133 s
2541:Time = 945s
2545:GAMG:  Solving for p_rgh, Initial residual = 0.67743, Final residual = 0.413041, No Iterations 1000
2546:time step continuity errors : sum local = 1.03625e-07, global = 6.15804e-10, cumulative = 2.61918e-08
2547:GAMG:  Solving for p_rgh, Initial residual = 0.631031, Final residual = 0.395467, No Iterations 1000
2548:time step continuity errors : sum local = 9.92042e-08, global = -3.04586e-09, cumulative = 2.31459e-08
2551:ExecutionTime = 133.18 s  ClockTime = 134 s
2554:Time = 950s
2558:GAMG:  Solving for p_rgh, Initial residual = 0.679164, Final residual = 0.405846, No Iterations 1000
2559:time step continuity errors : sum local = 1.05337e-07, global = 2.52953e-09, cumulative = 2.56755e-08
2560:GAMG:  Solving for p_rgh, Initial residual = 0.641321, Final residual = 0.411755, No Iterations 1000
2561:time step continuity errors : sum local = 1.00958e-07, global = 2.40637e-09, cumulative = 2.80818e-08
2564:ExecutionTime = 133.879 s  ClockTime = 135 s
2567:Time = 955s
2571:GAMG:  Solving for p_rgh, Initial residual = 0.689558, Final residual = 0.406748, No Iterations 1000
2572:time step continuity errors : sum local = 1.01955e-07, global = -3.0506e-09, cumulative = 2.50312e-08
2573:GAMG:  Solving for p_rgh, Initial residual = 0.646375, Final residual = 0.404612, No Iterations 1000
2574:time step continuity errors : sum local = 1.02988e-07, global = -7.81597e-10, cumulative = 2.42496e-08
2577:ExecutionTime = 134.577 s  ClockTime = 135 s
2580:Time = 960s
2584:GAMG:  Solving for p_rgh, Initial residual = 0.688593, Final residual = 0.402598, No Iterations 1000
2585:time step continuity errors : sum local = 1.00232e-07, global = 6.72647e-10, cumulative = 2.49223e-08
2586:GAMG:  Solving for p_rgh, Initial residual = 0.635277, Final residual = 0.398652, No Iterations 1000
2587:time step continuity errors : sum local = 1.05702e-07, global = 2.22163e-09, cumulative = 2.71439e-08
2590:ExecutionTime = 135.275 s  ClockTime = 136 s
2593:Time = 965s
2597:GAMG:  Solving for p_rgh, Initial residual = 0.68918, Final residual = 0.391067, No Iterations 1000
2598:time step continuity errors : sum local = 1.02388e-07, global = -2.8848e-09, cumulative = 2.42591e-08
2599:GAMG:  Solving for p_rgh, Initial residual = 0.636691, Final residual = 0.391876, No Iterations 1000
2600:time step continuity errors : sum local = 1.02998e-07, global = 9.61601e-10, cumulative = 2.52207e-08
2603:ExecutionTime = 135.977 s  ClockTime = 137 s
2606:Time = 970s
2610:GAMG:  Solving for p_rgh, Initial residual = 0.682505, Final residual = 0.419573, No Iterations 1000
2611:time step continuity errors : sum local = 9.98839e-08, global = -3.34902e-09, cumulative = 2.18717e-08
2612:GAMG:  Solving for p_rgh, Initial residual = 0.62494, Final residual = 0.400635, No Iterations 1000
2613:time step continuity errors : sum local = 1.03121e-07, global = -1.20792e-09, cumulative = 2.06638e-08
2616:ExecutionTime = 136.674 s  ClockTime = 137 s
2619:Time = 975s
2623:GAMG:  Solving for p_rgh, Initial residual = 0.668501, Final residual = 0.385151, No Iterations 1000
2624:time step continuity errors : sum local = 1.06747e-07, global = 3.46271e-09, cumulative = 2.41265e-08
2625:GAMG:  Solving for p_rgh, Initial residual = 0.616779, Final residual = 0.38122, No Iterations 1000
2626:time step continuity errors : sum local = 1.06146e-07, global = 2.88007e-09, cumulative = 2.70065e-08
2629:ExecutionTime = 137.374 s  ClockTime = 138 s
2632:Time = 980s
2636:GAMG:  Solving for p_rgh, Initial residual = 0.688022, Final residual = 0.394222, No Iterations 1000
2637:time step continuity errors : sum local = 1.0364e-07, global = 4.2822e-09, cumulative = 3.12887e-08
2638:GAMG:  Solving for p_rgh, Initial residual = 0.634429, Final residual = 0.424925, No Iterations 1000
2639:time step continuity errors : sum local = 1.06298e-07, global = 4.93117e-09, cumulative = 3.62199e-08
2642:ExecutionTime = 138.07 s  ClockTime = 139 s
2645:Time = 985s
2649:GAMG:  Solving for p_rgh, Initial residual = 0.680301, Final residual = 0.41528, No Iterations 1000
2650:time step continuity errors : sum local = 1.05114e-07, global = 1.60583e-09, cumulative = 3.78257e-08
2651:GAMG:  Solving for p_rgh, Initial residual = 0.603709, Final residual = 0.390799, No Iterations 1000
2652:time step continuity errors : sum local = 1.05045e-07, global = 1.97057e-09, cumulative = 3.97963e-08
2655:ExecutionTime = 138.767 s  ClockTime = 140 s
2658:Time = 990s
2662:GAMG:  Solving for p_rgh, Initial residual = 0.63835, Final residual = 0.370794, No Iterations 1000
2663:time step continuity errors : sum local = 1.05667e-07, global = 4.4101e-09, cumulative = 4.42064e-08
2664:GAMG:  Solving for p_rgh, Initial residual = 0.595911, Final residual = 0.378764, No Iterations 1000
2665:time step continuity errors : sum local = 1.06455e-07, global = 5.26275e-09, cumulative = 4.94692e-08
2668:ExecutionTime = 139.471 s  ClockTime = 140 s
2671:Time = 995s
2675:GAMG:  Solving for p_rgh, Initial residual = 0.647868, Final residual = 0.386576, No Iterations 1000
2676:time step continuity errors : sum local = 1.04242e-07, global = 9.14232e-10, cumulative = 5.03834e-08
2677:GAMG:  Solving for p_rgh, Initial residual = 0.631239, Final residual = 0.421711, No Iterations 1000
2678:time step continuity errors : sum local = 1.04965e-07, global = 2.62427e-09, cumulative = 5.30077e-08
2681:ExecutionTime = 140.173 s  ClockTime = 141 s
2684:Time = 1000s
2688:GAMG:  Solving for p_rgh, Initial residual = 0.675998, Final residual = 0.397685, No Iterations 1000
2689:time step continuity errors : sum local = 1.02979e-07, global = 2.85164e-09, cumulative = 5.58593e-08
2690:GAMG:  Solving for p_rgh, Initial residual = 0.618798, Final residual = 0.411033, No Iterations 1000
2691:time step continuity errors : sum local = 1.06755e-07, global = -5.40012e-10, cumulative = 5.53193e-08
2694:ExecutionTime = 140.904 s  ClockTime = 142 s

exec
/bin/zsh -lc 'for c in lid_driven_cavity backward_facing_step impinging_jet circular_cylinder_wake rayleigh_benard_convection differential_heated_cavity plane_channel_flow naca0012_airfoil turbulent_flat_plate duct_flow; do echo "CASE $c"; ls -1 reports/phase5_fields/$c 2>/dev/null | tail -n 3; done' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
CASE lid_driven_cavity
20260421T082340Z
runs
CASE backward_facing_step
20260421T125637Z
runs
CASE impinging_jet
20260421T142307Z
runs
CASE circular_cylinder_wake
20260421T130945Z
20260421T150630Z
runs
CASE rayleigh_benard_convection
20260421T142559Z
runs
CASE differential_heated_cavity
20260421T131052Z
runs
CASE plane_channel_flow
20260421T130203Z
runs
CASE naca0012_airfoil
20260421T142539Z
runs
CASE turbulent_flat_plate
20260421T130909Z
runs
CASE duct_flow
20260421T131015Z
runs

exec
/bin/zsh -lc 'latest=$(ls -1 reports/phase5_fields/lid_driven_cavity | rg -v '"'"'^runs$'"' | sort | tail -n1); echo "'$latest; log=reports/phase5_fields/lid_driven_cavity/$latest/$(ls reports/phase5_fields/lid_driven_cavity/$latest | rg '"'"'^log'"\\.'); rg -n \"time step continuity errors|Solving for Ux|Solving for Uy|Solving for p\\b|bounding \" \""'$log" | tail -n 40' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
20260421T082340Z
8168:smoothSolver:  Solving for Ux, Initial residual = 1.00004e-05, Final residual = 8.1729e-06, No Iterations 1
8169:smoothSolver:  Solving for Uy, Initial residual = 1.00184e-05, Final residual = 8.20635e-06, No Iterations 1
8170:GAMG:  Solving for p, Initial residual = 1.23336e-05, Final residual = 1.06739e-06, No Iterations 5
8171:time step continuity errors : sum local = 1.54392e-06, global = 1.60413e-16, cumulative = 1.75317e-15
8176:smoothSolver:  Solving for Ux, Initial residual = 9.83997e-06, Final residual = 9.83997e-06, No Iterations 0
8177:smoothSolver:  Solving for Uy, Initial residual = 1.0209e-05, Final residual = 8.35993e-06, No Iterations 1
8178:GAMG:  Solving for p, Initial residual = 3.56415e-06, Final residual = 7.7533e-07, No Iterations 2
8179:time step continuity errors : sum local = 1.12465e-06, global = -1.06986e-16, cumulative = 1.64618e-15
8184:smoothSolver:  Solving for Ux, Initial residual = 9.83811e-06, Final residual = 9.83811e-06, No Iterations 0
8185:smoothSolver:  Solving for Uy, Initial residual = 1.01774e-05, Final residual = 8.3374e-06, No Iterations 1
8186:GAMG:  Solving for p, Initial residual = 9.44845e-06, Final residual = 8.98965e-07, No Iterations 4
8187:time step continuity errors : sum local = 1.32235e-06, global = 7.39366e-17, cumulative = 1.72012e-15
8192:smoothSolver:  Solving for Ux, Initial residual = 9.93881e-06, Final residual = 9.93881e-06, No Iterations 0
8193:smoothSolver:  Solving for Uy, Initial residual = 1.00038e-05, Final residual = 8.19558e-06, No Iterations 1
8194:GAMG:  Solving for p, Initial residual = 1.45642e-05, Final residual = 1.13295e-06, No Iterations 5
8195:time step continuity errors : sum local = 1.63239e-06, global = 7.69368e-17, cumulative = 1.79706e-15
8200:smoothSolver:  Solving for Ux, Initial residual = 1.01104e-05, Final residual = 8.25828e-06, No Iterations 1
8201:smoothSolver:  Solving for Uy, Initial residual = 9.73257e-06, Final residual = 9.73257e-06, No Iterations 0
8202:GAMG:  Solving for p, Initial residual = 7.68409e-06, Final residual = 8.68504e-07, No Iterations 4
8203:time step continuity errors : sum local = 1.29336e-06, global = -3.47462e-16, cumulative = 1.44959e-15
8208:smoothSolver:  Solving for Ux, Initial residual = 1.00046e-05, Final residual = 8.17578e-06, No Iterations 1
8209:smoothSolver:  Solving for Uy, Initial residual = 9.8433e-06, Final residual = 9.8433e-06, No Iterations 0
8210:GAMG:  Solving for p, Initial residual = 2.177e-05, Final residual = 1.90298e-06, No Iterations 5
8211:time step continuity errors : sum local = 2.75245e-06, global = -9.32498e-17, cumulative = 1.35634e-15
8216:smoothSolver:  Solving for Ux, Initial residual = 9.72772e-06, Final residual = 9.72772e-06, No Iterations 0
8217:smoothSolver:  Solving for Uy, Initial residual = 1.02289e-05, Final residual = 8.37262e-06, No Iterations 1
8218:GAMG:  Solving for p, Initial residual = 7.61531e-06, Final residual = 7.5963e-07, No Iterations 5
8219:time step continuity errors : sum local = 1.10597e-06, global = -1.95904e-16, cumulative = 1.16044e-15
8224:smoothSolver:  Solving for Ux, Initial residual = 9.63036e-06, Final residual = 9.63036e-06, No Iterations 0
8225:smoothSolver:  Solving for Uy, Initial residual = 1.03241e-05, Final residual = 8.45485e-06, No Iterations 1
8226:GAMG:  Solving for p, Initial residual = 5.59969e-06, Final residual = 6.87747e-07, No Iterations 3
8227:time step continuity errors : sum local = 9.93559e-07, global = 1.56562e-16, cumulative = 1.317e-15
8232:smoothSolver:  Solving for Ux, Initial residual = 9.67096e-06, Final residual = 9.67096e-06, No Iterations 0
8233:smoothSolver:  Solving for Uy, Initial residual = 1.02272e-05, Final residual = 8.37878e-06, No Iterations 1
8234:GAMG:  Solving for p, Initial residual = 1.23026e-05, Final residual = 9.74333e-07, No Iterations 5
8235:time step continuity errors : sum local = 1.44344e-06, global = -1.89661e-16, cumulative = 1.12734e-15
8240:smoothSolver:  Solving for Ux, Initial residual = 9.81642e-06, Final residual = 9.81642e-06, No Iterations 0
8241:smoothSolver:  Solving for Uy, Initial residual = 9.99311e-06, Final residual = 9.99311e-06, No Iterations 0
8242:GAMG:  Solving for p, Initial residual = 7.0337e-06, Final residual = 6.35692e-07, No Iterations 4
8243:time step continuity errors : sum local = 9.4486e-07, global = 1.85296e-16, cumulative = 1.31264e-15

exec
/bin/zsh -lc 'latest=$(ls -1 reports/phase5_fields/circular_cylinder_wake | rg -v '"'"'^runs$'"' | sort | tail -n1); echo "'$latest; log=reports/phase5_fields/circular_cylinder_wake/$latest/$(ls reports/phase5_fields/circular_cylinder_wake/$latest | rg '"'"'^log'"\\.'); rg -n \"time step continuity errors|Solving for Ux|Solving for Uy|Solving for p\\b|Solving for p_rgh|bounding |Courant|Time = \" \""'$log" | tail -n 120' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
20260421T150630Z
7892:Courant Number mean: 4.39011 max: 5.87528
7893:Time = 0.982s
7895:DILUPBiCGStab:  Solving for Ux, Initial residual = 4.97174e-06, Final residual = 2.03837e-07, No Iterations 1
7896:DILUPBiCGStab:  Solving for Uy, Initial residual = 4.35471e-06, Final residual = 1.77581e-07, No Iterations 1
7897:GAMG:  Solving for p, Initial residual = 6.27544e-07, Final residual = 6.27544e-07, No Iterations 0
7898:GAMG:  Solving for p, Initial residual = 6.27544e-07, Final residual = 6.27544e-07, No Iterations 0
7899:time step continuity errors : sum local = 0.152284, global = 0.0190558, cumulative = 15.12
7900:GAMG:  Solving for p, Initial residual = 6.27544e-07, Final residual = 6.27544e-07, No Iterations 0
7901:GAMG:  Solving for p, Initial residual = 6.27544e-07, Final residual = 6.27544e-07, No Iterations 0
7902:time step continuity errors : sum local = 0.152284, global = 0.0190558, cumulative = 15.139
7905:bounding k, min: -0.00408295 max: 40.1248 average: 0.207078
7906:ExecutionTime = 13.9143 s  ClockTime = 17 s
7908:Courant Number mean: 4.39011 max: 5.87528
7909:Time = 0.984s
7911:DILUPBiCGStab:  Solving for Ux, Initial residual = 5.07803e-06, Final residual = 2.16319e-07, No Iterations 1
7912:DILUPBiCGStab:  Solving for Uy, Initial residual = 4.36493e-06, Final residual = 1.81237e-07, No Iterations 1
7913:GAMG:  Solving for p, Initial residual = 6.27532e-07, Final residual = 6.27532e-07, No Iterations 0
7914:GAMG:  Solving for p, Initial residual = 6.27532e-07, Final residual = 6.27532e-07, No Iterations 0
7915:time step continuity errors : sum local = 0.152281, global = 0.0190558, cumulative = 15.1581
7916:GAMG:  Solving for p, Initial residual = 6.27532e-07, Final residual = 6.27532e-07, No Iterations 0
7917:GAMG:  Solving for p, Initial residual = 6.27532e-07, Final residual = 6.27532e-07, No Iterations 0
7918:time step continuity errors : sum local = 0.152281, global = 0.0190558, cumulative = 15.1771
7921:bounding k, min: -0.00902589 max: 40.0085 average: 0.207073
7922:ExecutionTime = 13.9394 s  ClockTime = 17 s
7924:Courant Number mean: 4.39011 max: 5.87528
7925:Time = 0.986s
7927:DILUPBiCGStab:  Solving for Ux, Initial residual = 5.02947e-06, Final residual = 2.08218e-07, No Iterations 1
7928:DILUPBiCGStab:  Solving for Uy, Initial residual = 4.34877e-06, Final residual = 1.77149e-07, No Iterations 1
7929:GAMG:  Solving for p, Initial residual = 6.27544e-07, Final residual = 6.27544e-07, No Iterations 0
7930:GAMG:  Solving for p, Initial residual = 6.27544e-07, Final residual = 6.27544e-07, No Iterations 0
7931:time step continuity errors : sum local = 0.152284, global = 0.0190558, cumulative = 15.1962
7932:GAMG:  Solving for p, Initial residual = 6.27544e-07, Final residual = 6.27544e-07, No Iterations 0
7933:GAMG:  Solving for p, Initial residual = 6.27544e-07, Final residual = 6.27544e-07, No Iterations 0
7934:time step continuity errors : sum local = 0.152284, global = 0.0190558, cumulative = 15.2152
7937:bounding k, min: -0.00420261 max: 40.1253 average: 0.207076
7938:ExecutionTime = 13.9643 s  ClockTime = 17 s
7940:Courant Number mean: 4.39011 max: 5.87528
7941:Time = 0.988s
7943:DILUPBiCGStab:  Solving for Ux, Initial residual = 5.04259e-06, Final residual = 2.13677e-07, No Iterations 1
7944:DILUPBiCGStab:  Solving for Uy, Initial residual = 4.27221e-06, Final residual = 1.74749e-07, No Iterations 1
7945:GAMG:  Solving for p, Initial residual = 6.27532e-07, Final residual = 6.27532e-07, No Iterations 0
7946:GAMG:  Solving for p, Initial residual = 6.27532e-07, Final residual = 6.27532e-07, No Iterations 0
7947:time step continuity errors : sum local = 0.152281, global = 0.0190558, cumulative = 15.2343
7948:GAMG:  Solving for p, Initial residual = 6.27532e-07, Final residual = 6.27532e-07, No Iterations 0
7949:GAMG:  Solving for p, Initial residual = 6.27532e-07, Final residual = 6.27532e-07, No Iterations 0
7950:time step continuity errors : sum local = 0.152281, global = 0.0190558, cumulative = 15.2534
7953:bounding k, min: -0.00897249 max: 40.0113 average: 0.207064
7954:ExecutionTime = 13.9889 s  ClockTime = 17 s
7956:Courant Number mean: 4.39011 max: 5.87528
7957:Time = 0.99s
7959:DILUPBiCGStab:  Solving for Ux, Initial residual = 4.94067e-06, Final residual = 2.03363e-07, No Iterations 1
7960:DILUPBiCGStab:  Solving for Uy, Initial residual = 4.31478e-06, Final residual = 1.76116e-07, No Iterations 1
7961:GAMG:  Solving for p, Initial residual = 6.27544e-07, Final residual = 6.27544e-07, No Iterations 0
7962:GAMG:  Solving for p, Initial residual = 6.27544e-07, Final residual = 6.27544e-07, No Iterations 0
7963:time step continuity errors : sum local = 0.152284, global = 0.0190558, cumulative = 15.2724
7964:GAMG:  Solving for p, Initial residual = 6.27545e-07, Final residual = 6.27545e-07, No Iterations 0
7965:GAMG:  Solving for p, Initial residual = 6.27545e-07, Final residual = 6.27545e-07, No Iterations 0
7966:time step continuity errors : sum local = 0.152284, global = 0.0190558, cumulative = 15.2915
7969:bounding k, min: -0.00408622 max: 40.1139 average: 0.207064
7970:ExecutionTime = 14.0138 s  ClockTime = 17 s
7972:Courant Number mean: 4.39011 max: 5.87528
7973:Time = 0.992s
7975:DILUPBiCGStab:  Solving for Ux, Initial residual = 5.00631e-06, Final residual = 2.13654e-07, No Iterations 1
7976:DILUPBiCGStab:  Solving for Uy, Initial residual = 4.26562e-06, Final residual = 1.73739e-07, No Iterations 1
7977:GAMG:  Solving for p, Initial residual = 6.27533e-07, Final residual = 6.27533e-07, No Iterations 0
7978:GAMG:  Solving for p, Initial residual = 6.27533e-07, Final residual = 6.27533e-07, No Iterations 0
7979:time step continuity errors : sum local = 0.152282, global = 0.0190558, cumulative = 15.3105
7980:GAMG:  Solving for p, Initial residual = 6.27532e-07, Final residual = 6.27532e-07, No Iterations 0
7981:GAMG:  Solving for p, Initial residual = 6.27532e-07, Final residual = 6.27532e-07, No Iterations 0
7982:time step continuity errors : sum local = 0.152282, global = 0.0190558, cumulative = 15.3296
7985:bounding k, min: -0.00888366 max: 40.011 average: 0.207051
7986:ExecutionTime = 14.0393 s  ClockTime = 17 s
7988:Courant Number mean: 4.39011 max: 5.87528
7989:Time = 0.994s
7991:DILUPBiCGStab:  Solving for Ux, Initial residual = 4.93284e-06, Final residual = 2.02363e-07, No Iterations 1
7992:DILUPBiCGStab:  Solving for Uy, Initial residual = 4.26877e-06, Final residual = 1.73966e-07, No Iterations 1
7993:GAMG:  Solving for p, Initial residual = 6.27545e-07, Final residual = 6.27545e-07, No Iterations 0
7994:GAMG:  Solving for p, Initial residual = 6.27545e-07, Final residual = 6.27545e-07, No Iterations 0
7995:time step continuity errors : sum local = 0.152284, global = 0.0190558, cumulative = 15.3486
7996:GAMG:  Solving for p, Initial residual = 6.27545e-07, Final residual = 6.27545e-07, No Iterations 0
7997:GAMG:  Solving for p, Initial residual = 6.27545e-07, Final residual = 6.27545e-07, No Iterations 0
7998:time step continuity errors : sum local = 0.152285, global = 0.0190558, cumulative = 15.3677
8001:bounding k, min: -0.00416879 max: 40.1026 average: 0.207055
8002:ExecutionTime = 14.0645 s  ClockTime = 17 s
8004:Courant Number mean: 4.39011 max: 5.87528
8005:Time = 0.996s
8007:DILUPBiCGStab:  Solving for Ux, Initial residual = 5.01652e-06, Final residual = 2.11013e-07, No Iterations 1
8008:DILUPBiCGStab:  Solving for Uy, Initial residual = 4.33294e-06, Final residual = 1.75324e-07, No Iterations 1
8009:GAMG:  Solving for p, Initial residual = 6.27532e-07, Final residual = 6.27532e-07, No Iterations 0
8010:GAMG:  Solving for p, Initial residual = 6.27532e-07, Final residual = 6.27532e-07, No Iterations 0
8011:time step continuity errors : sum local = 0.152282, global = 0.0190558, cumulative = 15.3867
8012:GAMG:  Solving for p, Initial residual = 6.27532e-07, Final residual = 6.27532e-07, No Iterations 0
8013:GAMG:  Solving for p, Initial residual = 6.27532e-07, Final residual = 6.27532e-07, No Iterations 0
8014:time step continuity errors : sum local = 0.152281, global = 0.0190558, cumulative = 15.4058
8017:bounding k, min: -0.00886771 max: 40.0079 average: 0.207048
8018:ExecutionTime = 14.092 s  ClockTime = 17 s
8020:Courant Number mean: 4.39011 max: 5.87528
8021:Time = 0.998s
8023:DILUPBiCGStab:  Solving for Ux, Initial residual = 5.01672e-06, Final residual = 2.06643e-07, No Iterations 1
8024:DILUPBiCGStab:  Solving for Uy, Initial residual = 4.29839e-06, Final residual = 1.75837e-07, No Iterations 1
8025:GAMG:  Solving for p, Initial residual = 6.27545e-07, Final residual = 6.27545e-07, No Iterations 0
8026:GAMG:  Solving for p, Initial residual = 6.27545e-07, Final residual = 6.27545e-07, No Iterations 0
8027:time step continuity errors : sum local = 0.152284, global = 0.0190558, cumulative = 15.4249
8028:GAMG:  Solving for p, Initial residual = 6.27545e-07, Final residual = 6.27545e-07, No Iterations 0
8029:GAMG:  Solving for p, Initial residual = 6.27545e-07, Final residual = 6.27545e-07, No Iterations 0
8030:time step continuity errors : sum local = 0.152285, global = 0.0190558, cumulative = 15.4439
8033:bounding k, min: -0.00424706 max: 40.1119 average: 0.207056
8034:ExecutionTime = 14.1202 s  ClockTime = 17 s
8036:Courant Number mean: 4.39011 max: 5.87528
8037:Time = 1s
8039:DILUPBiCGStab:  Solving for Ux, Initial residual = 4.93502e-06, Final residual = 2.08646e-07, No Iterations 1
8040:DILUPBiCGStab:  Solving for Uy, Initial residual = 4.42518e-06, Final residual = 1.80359e-07, No Iterations 1
8041:GAMG:  Solving for p, Initial residual = 6.27532e-07, Final residual = 6.27532e-07, No Iterations 0
8042:GAMG:  Solving for p, Initial residual = 6.27532e-07, Final residual = 6.27532e-07, No Iterations 0
8043:time step continuity errors : sum local = 0.152281, global = 0.0190558, cumulative = 15.463
8044:GAMG:  Solving for p, Initial residual = 6.27532e-07, Final residual = 6.27532e-07, No Iterations 0
8045:GAMG:  Solving for p, Initial residual = 6.27532e-07, Final residual = 6.27532e-07, No Iterations 0
8046:time step continuity errors : sum local = 0.152281, global = 0.0190558, cumulative = 15.482
8049:bounding k, min: -0.00891886 max: 40.021 average: 0.207056
8050:ExecutionTime = 14.2412 s  ClockTime = 17 s

exec
/bin/zsh -lc 'latest=$(ls -1 reports/phase5_fields/rayleigh_benard_convection | rg -v '"'"'^runs$'"' | sort | tail -n1); echo "'$latest; log=reports/phase5_fields/rayleigh_benard_convection/$latest/$(ls reports/phase5_fields/rayleigh_benard_convection/$latest | rg '"'"'^log'"\\.'); rg -n \"time step continuity errors|Solving for Ux|Solving for Uy|Solving for T\\b|Solving for p\\b|Solving for p_rgh|bounding |Time = \" \""'$log" | tail -n 120' in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc 'latest=$(ls -1 reports/phase5_fields/differential_heated_cavity | rg -v '"'"'^runs$'"' | sort | tail -n1); echo "'$latest; log=reports/phase5_fields/differential_heated_cavity/$latest/$(ls reports/phase5_fields/differential_heated_cavity/$latest | rg '"'"'^log'"\\.'); rg -n \"time step continuity errors|Solving for Ux|Solving for Uy|Solving for T\\b|Solving for p\\b|Solving for p_rgh|bounding |Time = \" \""'$log" | tail -n 120' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 957ms:
646949:smoothSolver:  Solving for Uy, Initial residual = 1.21259e-05, Final residual = 6.65845e-08, No Iterations 3
646951:DICPCG:  Solving for p_rgh, Initial residual = 1.01305e-05, Final residual = 9.62567e-08, No Iterations 39
646952:DICPCG:  Solving for p_rgh, Initial residual = 9.62577e-08, Final residual = 9.62577e-08, No Iterations 0
646953:DICPCG:  Solving for p_rgh, Initial residual = 9.62577e-08, Final residual = 9.62577e-08, No Iterations 0
646954:time step continuity errors : sum local = 3.83123e-11, global = 5.27576e-22, cumulative = -1.52229e-19
646956:smoothSolver:  Solving for Ux, Initial residual = 7.95751e-06, Final residual = 4.36951e-08, No Iterations 3
646957:smoothSolver:  Solving for Uy, Initial residual = 1.21286e-05, Final residual = 6.65988e-08, No Iterations 3
646959:DICPCG:  Solving for p_rgh, Initial residual = 1.00685e-05, Final residual = 9.88911e-08, No Iterations 9
646960:DICPCG:  Solving for p_rgh, Initial residual = 9.8892e-08, Final residual = 9.8892e-08, No Iterations 0
646961:DICPCG:  Solving for p_rgh, Initial residual = 9.8892e-08, Final residual = 9.8892e-08, No Iterations 0
646962:time step continuity errors : sum local = 3.98033e-11, global = -1.81387e-22, cumulative = -1.5241e-19
646964:smoothSolver:  Solving for Ux, Initial residual = 7.95805e-06, Final residual = 4.36984e-08, No Iterations 3
646965:smoothSolver:  Solving for Uy, Initial residual = 1.21281e-05, Final residual = 6.65966e-08, No Iterations 3
646967:DICPCG:  Solving for p_rgh, Initial residual = 1.00035e-05, Final residual = 9.65275e-08, No Iterations 19
646968:DICPCG:  Solving for p_rgh, Initial residual = 9.65284e-08, Final residual = 9.65284e-08, No Iterations 0
646969:DICPCG:  Solving for p_rgh, Initial residual = 9.65284e-08, Final residual = 9.65284e-08, No Iterations 0
646970:time step continuity errors : sum local = 3.86553e-11, global = -5.75657e-22, cumulative = -1.52986e-19
646972:smoothSolver:  Solving for Ux, Initial residual = 7.95807e-06, Final residual = 4.36986e-08, No Iterations 3
646973:smoothSolver:  Solving for Uy, Initial residual = 1.21276e-05, Final residual = 6.65936e-08, No Iterations 3
646975:DICPCG:  Solving for p_rgh, Initial residual = 9.94151e-06, Final residual = 9.93633e-08, No Iterations 39
646976:DICPCG:  Solving for p_rgh, Initial residual = 9.93642e-08, Final residual = 9.93642e-08, No Iterations 0
646977:DICPCG:  Solving for p_rgh, Initial residual = 9.93642e-08, Final residual = 9.93642e-08, No Iterations 0
646978:time step continuity errors : sum local = 3.96599e-11, global = -8.5055e-22, cumulative = -1.53836e-19
646980:smoothSolver:  Solving for Ux, Initial residual = 7.95586e-06, Final residual = 4.3686e-08, No Iterations 3
646981:smoothSolver:  Solving for Uy, Initial residual = 1.213e-05, Final residual = 6.66066e-08, No Iterations 3
646983:DICPCG:  Solving for p_rgh, Initial residual = 9.88338e-06, Final residual = 9.76433e-08, No Iterations 17
646984:DICPCG:  Solving for p_rgh, Initial residual = 9.76442e-08, Final residual = 9.76442e-08, No Iterations 0
646985:DICPCG:  Solving for p_rgh, Initial residual = 9.76442e-08, Final residual = 9.76442e-08, No Iterations 0
646986:time step continuity errors : sum local = 3.89188e-11, global = -7.47482e-23, cumulative = -1.53911e-19
646988:smoothSolver:  Solving for Ux, Initial residual = 7.95614e-06, Final residual = 4.36877e-08, No Iterations 3
646989:smoothSolver:  Solving for Uy, Initial residual = 1.21294e-05, Final residual = 6.66038e-08, No Iterations 3
646991:DICPCG:  Solving for p_rgh, Initial residual = 9.82329e-06, Final residual = 9.62875e-08, No Iterations 17
646992:DICPCG:  Solving for p_rgh, Initial residual = 9.62884e-08, Final residual = 9.62884e-08, No Iterations 0
646993:DICPCG:  Solving for p_rgh, Initial residual = 9.62884e-08, Final residual = 9.62884e-08, No Iterations 0
646994:time step continuity errors : sum local = 3.82921e-11, global = -3.86009e-23, cumulative = -1.5395e-19
646996:smoothSolver:  Solving for Ux, Initial residual = 7.95644e-06, Final residual = 4.36895e-08, No Iterations 3
646997:smoothSolver:  Solving for Uy, Initial residual = 1.21289e-05, Final residual = 6.6601e-08, No Iterations 3
646999:DICPCG:  Solving for p_rgh, Initial residual = 9.7653e-06, Final residual = 9.89357e-08, No Iterations 17
647000:DICPCG:  Solving for p_rgh, Initial residual = 9.89366e-08, Final residual = 9.89366e-08, No Iterations 0
647001:DICPCG:  Solving for p_rgh, Initial residual = 9.89366e-08, Final residual = 9.89366e-08, No Iterations 0
647002:time step continuity errors : sum local = 3.92615e-11, global = 1.73137e-22, cumulative = -1.53777e-19
647004:smoothSolver:  Solving for Ux, Initial residual = 7.9567e-06, Final residual = 4.36912e-08, No Iterations 3
647005:smoothSolver:  Solving for Uy, Initial residual = 1.21284e-05, Final residual = 6.65983e-08, No Iterations 3
647007:DICPCG:  Solving for p_rgh, Initial residual = 9.7115e-06, Final residual = 9.83208e-08, No Iterations 39
647008:DICPCG:  Solving for p_rgh, Initial residual = 9.83217e-08, Final residual = 9.83217e-08, No Iterations 0
647009:DICPCG:  Solving for p_rgh, Initial residual = 9.83217e-08, Final residual = 9.83217e-08, No Iterations 0
647010:time step continuity errors : sum local = 3.96376e-11, global = -7.19584e-23, cumulative = -1.53849e-19
647012:smoothSolver:  Solving for Ux, Initial residual = 7.95473e-06, Final residual = 4.36797e-08, No Iterations 3
647013:smoothSolver:  Solving for Uy, Initial residual = 1.21306e-05, Final residual = 6.66102e-08, No Iterations 3
647015:DICPCG:  Solving for p_rgh, Initial residual = 9.66061e-06, Final residual = 9.9088e-08, No Iterations 16
647016:DICPCG:  Solving for p_rgh, Initial residual = 9.90889e-08, Final residual = 9.90889e-08, No Iterations 0
647017:DICPCG:  Solving for p_rgh, Initial residual = 9.90889e-08, Final residual = 9.90889e-08, No Iterations 0
647018:time step continuity errors : sum local = 3.94309e-11, global = 5.49266e-22, cumulative = -1.53299e-19
647020:smoothSolver:  Solving for Ux, Initial residual = 7.95508e-06, Final residual = 4.36819e-08, No Iterations 3
647021:smoothSolver:  Solving for Uy, Initial residual = 1.21301e-05, Final residual = 6.66074e-08, No Iterations 3
647023:DICPCG:  Solving for p_rgh, Initial residual = 9.61006e-06, Final residual = 9.35913e-08, No Iterations 17
647024:DICPCG:  Solving for p_rgh, Initial residual = 9.35922e-08, Final residual = 9.35922e-08, No Iterations 0
647025:DICPCG:  Solving for p_rgh, Initial residual = 9.35922e-08, Final residual = 9.35922e-08, No Iterations 0
647026:time step continuity errors : sum local = 3.73599e-11, global = 9.34696e-23, cumulative = -1.53206e-19
647028:smoothSolver:  Solving for Ux, Initial residual = 7.95538e-06, Final residual = 4.36838e-08, No Iterations 3
647029:smoothSolver:  Solving for Uy, Initial residual = 1.21296e-05, Final residual = 6.66046e-08, No Iterations 3
647031:DICPCG:  Solving for p_rgh, Initial residual = 9.5608e-06, Final residual = 9.75549e-08, No Iterations 17
647032:DICPCG:  Solving for p_rgh, Initial residual = 9.75558e-08, Final residual = 9.75558e-08, No Iterations 0
647033:DICPCG:  Solving for p_rgh, Initial residual = 9.75558e-08, Final residual = 9.75558e-08, No Iterations 0
647034:time step continuity errors : sum local = 3.90182e-11, global = -6.30815e-22, cumulative = -1.53837e-19
647036:smoothSolver:  Solving for Ux, Initial residual = 7.95561e-06, Final residual = 4.36852e-08, No Iterations 3
647037:smoothSolver:  Solving for Uy, Initial residual = 1.2129e-05, Final residual = 6.66017e-08, No Iterations 3
647039:DICPCG:  Solving for p_rgh, Initial residual = 9.51207e-06, Final residual = 9.96338e-08, No Iterations 18
647040:DICPCG:  Solving for p_rgh, Initial residual = 9.96346e-08, Final residual = 9.96346e-08, No Iterations 0
647041:DICPCG:  Solving for p_rgh, Initial residual = 9.96346e-08, Final residual = 9.96346e-08, No Iterations 0
647042:time step continuity errors : sum local = 3.9922e-11, global = -6.32943e-22, cumulative = -1.5447e-19
647044:smoothSolver:  Solving for Ux, Initial residual = 7.95569e-06, Final residual = 4.36858e-08, No Iterations 3
647045:smoothSolver:  Solving for Uy, Initial residual = 1.21285e-05, Final residual = 6.65987e-08, No Iterations 3
647047:DICPCG:  Solving for p_rgh, Initial residual = 9.46013e-06, Final residual = 9.84824e-08, No Iterations 39
647048:DICPCG:  Solving for p_rgh, Initial residual = 9.84833e-08, Final residual = 9.84833e-08, No Iterations 0
647049:DICPCG:  Solving for p_rgh, Initial residual = 9.84833e-08, Final residual = 9.84833e-08, No Iterations 0
647050:time step continuity errors : sum local = 3.96885e-11, global = 1.79509e-22, cumulative = -1.5429e-19
647052:smoothSolver:  Solving for Ux, Initial residual = 7.95359e-06, Final residual = 4.36736e-08, No Iterations 3
647053:smoothSolver:  Solving for Uy, Initial residual = 1.21307e-05, Final residual = 6.66108e-08, No Iterations 3
647055:DICPCG:  Solving for p_rgh, Initial residual = 9.40866e-06, Final residual = 9.88821e-08, No Iterations 9
647056:DICPCG:  Solving for p_rgh, Initial residual = 9.8883e-08, Final residual = 9.8883e-08, No Iterations 0
647057:DICPCG:  Solving for p_rgh, Initial residual = 9.8883e-08, Final residual = 9.8883e-08, No Iterations 0
647058:time step continuity errors : sum local = 3.95999e-11, global = -2.35514e-22, cumulative = -1.54526e-19
647060:smoothSolver:  Solving for Ux, Initial residual = 7.95413e-06, Final residual = 4.36769e-08, No Iterations 3
647061:smoothSolver:  Solving for Uy, Initial residual = 1.21303e-05, Final residual = 6.66086e-08, No Iterations 3
647063:DICPCG:  Solving for p_rgh, Initial residual = 9.35394e-06, Final residual = 9.91985e-08, No Iterations 18
647064:DICPCG:  Solving for p_rgh, Initial residual = 9.91994e-08, Final residual = 9.91994e-08, No Iterations 0
647065:DICPCG:  Solving for p_rgh, Initial residual = 9.91994e-08, Final residual = 9.91994e-08, No Iterations 0
647066:time step continuity errors : sum local = 3.9912e-11, global = -9.22677e-24, cumulative = -1.54535e-19
647068:smoothSolver:  Solving for Ux, Initial residual = 7.95423e-06, Final residual = 4.36776e-08, No Iterations 3
647069:smoothSolver:  Solving for Uy, Initial residual = 1.21296e-05, Final residual = 6.66051e-08, No Iterations 3
647071:DICPCG:  Solving for p_rgh, Initial residual = 9.30451e-06, Final residual = 8.89463e-08, No Iterations 46
647072:DICPCG:  Solving for p_rgh, Initial residual = 8.89471e-08, Final residual = 8.89471e-08, No Iterations 0
647073:DICPCG:  Solving for p_rgh, Initial residual = 8.89471e-08, Final residual = 8.89471e-08, No Iterations 0
647074:time step continuity errors : sum local = 3.61868e-11, global = -9.10691e-22, cumulative = -1.55445e-19
647076:smoothSolver:  Solving for Ux, Initial residual = 7.95214e-06, Final residual = 4.36653e-08, No Iterations 3
647077:smoothSolver:  Solving for Uy, Initial residual = 1.21322e-05, Final residual = 6.66185e-08, No Iterations 3
647079:DICPCG:  Solving for p_rgh, Initial residual = 9.25716e-06, Final residual = 9.65165e-08, No Iterations 17
647080:DICPCG:  Solving for p_rgh, Initial residual = 9.65174e-08, Final residual = 9.65174e-08, No Iterations 0
647081:DICPCG:  Solving for p_rgh, Initial residual = 9.65174e-08, Final residual = 9.65174e-08, No Iterations 0
647082:time step continuity errors : sum local = 3.89224e-11, global = -3.85129e-22, cumulative = -1.55831e-19
647084:smoothSolver:  Solving for Ux, Initial residual = 7.95237e-06, Final residual = 4.36668e-08, No Iterations 3
647085:smoothSolver:  Solving for Uy, Initial residual = 1.21315e-05, Final residual = 6.66148e-08, No Iterations 3
647087:DICPCG:  Solving for p_rgh, Initial residual = 9.21138e-06, Final residual = 9.99332e-08, No Iterations 16
647088:DICPCG:  Solving for p_rgh, Initial residual = 9.99341e-08, Final residual = 9.99341e-08, No Iterations 0
647089:DICPCG:  Solving for p_rgh, Initial residual = 9.99341e-08, Final residual = 9.99341e-08, No Iterations 0
647090:time step continuity errors : sum local = 4.03001e-11, global = -7.06156e-22, cumulative = -1.56537e-19
647092:smoothSolver:  Solving for Ux, Initial residual = 7.95263e-06, Final residual = 4.36684e-08, No Iterations 3
647093:smoothSolver:  Solving for Uy, Initial residual = 1.21308e-05, Final residual = 6.66111e-08, No Iterations 3
647095:DICPCG:  Solving for p_rgh, Initial residual = 9.1653e-06, Final residual = 9.62386e-08, No Iterations 17
647096:DICPCG:  Solving for p_rgh, Initial residual = 9.62394e-08, Final residual = 9.62394e-08, No Iterations 0
647097:DICPCG:  Solving for p_rgh, Initial residual = 9.62394e-08, Final residual = 9.62394e-08, No Iterations 0
647098:time step continuity errors : sum local = 3.88932e-11, global = -7.72547e-22, cumulative = -1.57309e-19
647100:smoothSolver:  Solving for Ux, Initial residual = 7.95282e-06, Final residual = 4.36696e-08, No Iterations 3
647101:smoothSolver:  Solving for Uy, Initial residual = 1.213e-05, Final residual = 6.66072e-08, No Iterations 3
647103:DICPCG:  Solving for p_rgh, Initial residual = 9.12019e-06, Final residual = 9.93959e-08, No Iterations 17
647104:DICPCG:  Solving for p_rgh, Initial residual = 9.93967e-08, Final residual = 9.93967e-08, No Iterations 0
647105:DICPCG:  Solving for p_rgh, Initial residual = 9.93967e-08, Final residual = 9.93967e-08, No Iterations 0
647106:time step continuity errors : sum local = 4.018e-11, global = 2.7718e-22, cumulative = -1.57032e-19
647109:ExecutionTime = 3761.83 s  ClockTime = 3810 s

 succeeded in 955ms:
646949:smoothSolver:  Solving for Uy, Initial residual = 6.59462e-06, Final residual = 3.61188e-08, No Iterations 3
646951:DICPCG:  Solving for p_rgh, Initial residual = 1.40652e-05, Final residual = 1.38195e-07, No Iterations 29
646952:DICPCG:  Solving for p_rgh, Initial residual = 1.38197e-07, Final residual = 9.72751e-08, No Iterations 2
646953:DICPCG:  Solving for p_rgh, Initial residual = 9.72751e-08, Final residual = 9.72751e-08, No Iterations 0
646954:time step continuity errors : sum local = 2.73158e-10, global = -2.07602e-20, cumulative = 2.4826e-18
646956:smoothSolver:  Solving for Ux, Initial residual = 6.10626e-06, Final residual = 3.34448e-08, No Iterations 3
646957:smoothSolver:  Solving for Uy, Initial residual = 6.59516e-06, Final residual = 3.61216e-08, No Iterations 3
646959:DICPCG:  Solving for p_rgh, Initial residual = 1.3989e-05, Final residual = 1.36138e-07, No Iterations 29
646960:DICPCG:  Solving for p_rgh, Initial residual = 1.3614e-07, Final residual = 9.49658e-08, No Iterations 2
646961:DICPCG:  Solving for p_rgh, Initial residual = 9.49658e-08, Final residual = 9.49658e-08, No Iterations 0
646962:time step continuity errors : sum local = 2.6442e-10, global = -1.08288e-20, cumulative = 2.47177e-18
646964:smoothSolver:  Solving for Ux, Initial residual = 6.10531e-06, Final residual = 3.34394e-08, No Iterations 3
646965:smoothSolver:  Solving for Uy, Initial residual = 6.59566e-06, Final residual = 3.61243e-08, No Iterations 3
646967:DICPCG:  Solving for p_rgh, Initial residual = 1.39112e-05, Final residual = 1.34501e-07, No Iterations 29
646968:DICPCG:  Solving for p_rgh, Initial residual = 1.34503e-07, Final residual = 9.27199e-08, No Iterations 2
646969:DICPCG:  Solving for p_rgh, Initial residual = 9.27199e-08, Final residual = 9.27199e-08, No Iterations 0
646970:time step continuity errors : sum local = 2.55682e-10, global = 6.7622e-21, cumulative = 2.47853e-18
646972:smoothSolver:  Solving for Ux, Initial residual = 6.10444e-06, Final residual = 3.34344e-08, No Iterations 3
646973:smoothSolver:  Solving for Uy, Initial residual = 6.59608e-06, Final residual = 3.61265e-08, No Iterations 3
646975:DICPCG:  Solving for p_rgh, Initial residual = 1.38317e-05, Final residual = 1.33722e-07, No Iterations 29
646976:DICPCG:  Solving for p_rgh, Initial residual = 1.33723e-07, Final residual = 9.15127e-08, No Iterations 2
646977:DICPCG:  Solving for p_rgh, Initial residual = 9.15127e-08, Final residual = 9.15127e-08, No Iterations 0
646978:time step continuity errors : sum local = 2.50231e-10, global = 4.77076e-21, cumulative = 2.4833e-18
646980:smoothSolver:  Solving for Ux, Initial residual = 6.10369e-06, Final residual = 3.34301e-08, No Iterations 3
646981:smoothSolver:  Solving for Uy, Initial residual = 6.59638e-06, Final residual = 3.6128e-08, No Iterations 3
646983:DICPCG:  Solving for p_rgh, Initial residual = 1.37502e-05, Final residual = 1.36378e-07, No Iterations 14
646984:DICPCG:  Solving for p_rgh, Initial residual = 1.3638e-07, Final residual = 8.59096e-08, No Iterations 20
646985:DICPCG:  Solving for p_rgh, Initial residual = 8.59096e-08, Final residual = 8.59096e-08, No Iterations 0
646986:time step continuity errors : sum local = 2.34357e-10, global = 1.11119e-20, cumulative = 2.49442e-18
646988:smoothSolver:  Solving for Ux, Initial residual = 6.10305e-06, Final residual = 3.34263e-08, No Iterations 3
646989:smoothSolver:  Solving for Uy, Initial residual = 6.59665e-06, Final residual = 3.61291e-08, No Iterations 3
646991:DICPCG:  Solving for p_rgh, Initial residual = 1.36637e-05, Final residual = 1.29237e-07, No Iterations 13
646992:DICPCG:  Solving for p_rgh, Initial residual = 1.29238e-07, Final residual = 9.16842e-08, No Iterations 21
646993:DICPCG:  Solving for p_rgh, Initial residual = 9.16842e-08, Final residual = 9.16842e-08, No Iterations 0
646994:time step continuity errors : sum local = 2.49048e-10, global = -2.06482e-20, cumulative = 2.47377e-18
646996:smoothSolver:  Solving for Ux, Initial residual = 6.10253e-06, Final residual = 3.34233e-08, No Iterations 3
646997:smoothSolver:  Solving for Uy, Initial residual = 6.59679e-06, Final residual = 3.61296e-08, No Iterations 3
646999:DICPCG:  Solving for p_rgh, Initial residual = 1.35794e-05, Final residual = 1.23436e-07, No Iterations 13
647000:DICPCG:  Solving for p_rgh, Initial residual = 1.23437e-07, Final residual = 9.87988e-08, No Iterations 1
647001:DICPCG:  Solving for p_rgh, Initial residual = 9.87988e-08, Final residual = 9.87988e-08, No Iterations 0
647002:time step continuity errors : sum local = 2.74595e-10, global = -9.71653e-21, cumulative = 2.46405e-18
647004:smoothSolver:  Solving for Ux, Initial residual = 6.10286e-06, Final residual = 3.34257e-08, No Iterations 3
647005:smoothSolver:  Solving for Uy, Initial residual = 6.59607e-06, Final residual = 3.61264e-08, No Iterations 3
647007:DICPCG:  Solving for p_rgh, Initial residual = 1.34979e-05, Final residual = 1.33907e-07, No Iterations 29
647008:DICPCG:  Solving for p_rgh, Initial residual = 1.33909e-07, Final residual = 9.4966e-08, No Iterations 2
647009:DICPCG:  Solving for p_rgh, Initial residual = 9.4966e-08, Final residual = 9.4966e-08, No Iterations 0
647010:time step continuity errors : sum local = 2.62181e-10, global = 6.71128e-21, cumulative = 2.47076e-18
647012:smoothSolver:  Solving for Ux, Initial residual = 6.10241e-06, Final residual = 3.34234e-08, No Iterations 3
647013:smoothSolver:  Solving for Uy, Initial residual = 6.5962e-06, Final residual = 3.61271e-08, No Iterations 3
647015:DICPCG:  Solving for p_rgh, Initial residual = 1.34207e-05, Final residual = 1.27168e-07, No Iterations 30
647016:DICPCG:  Solving for p_rgh, Initial residual = 1.27169e-07, Final residual = 9.17045e-08, No Iterations 2
647017:DICPCG:  Solving for p_rgh, Initial residual = 9.17045e-08, Final residual = 9.17045e-08, No Iterations 0
647018:time step continuity errors : sum local = 2.55364e-10, global = -8.6947e-21, cumulative = 2.46207e-18
647020:smoothSolver:  Solving for Ux, Initial residual = 6.10191e-06, Final residual = 3.34207e-08, No Iterations 3
647021:smoothSolver:  Solving for Uy, Initial residual = 6.59643e-06, Final residual = 3.61283e-08, No Iterations 3
647023:DICPCG:  Solving for p_rgh, Initial residual = 1.33442e-05, Final residual = 1.28956e-07, No Iterations 30
647024:DICPCG:  Solving for p_rgh, Initial residual = 1.28958e-07, Final residual = 9.25199e-08, No Iterations 2
647025:DICPCG:  Solving for p_rgh, Initial residual = 9.25199e-08, Final residual = 9.25199e-08, No Iterations 0
647026:time step continuity errors : sum local = 2.57842e-10, global = -2.02931e-20, cumulative = 2.44177e-18
647028:smoothSolver:  Solving for Ux, Initial residual = 6.10133e-06, Final residual = 3.34176e-08, No Iterations 3
647029:smoothSolver:  Solving for Uy, Initial residual = 6.59672e-06, Final residual = 3.61299e-08, No Iterations 3
647031:DICPCG:  Solving for p_rgh, Initial residual = 1.32714e-05, Final residual = 1.28981e-07, No Iterations 30
647032:DICPCG:  Solving for p_rgh, Initial residual = 1.28983e-07, Final residual = 9.26439e-08, No Iterations 2
647033:DICPCG:  Solving for p_rgh, Initial residual = 9.26439e-08, Final residual = 9.26439e-08, No Iterations 0
647034:time step continuity errors : sum local = 2.58011e-10, global = -1.81882e-20, cumulative = 2.42359e-18
647036:smoothSolver:  Solving for Ux, Initial residual = 6.10069e-06, Final residual = 3.34141e-08, No Iterations 3
647037:smoothSolver:  Solving for Uy, Initial residual = 6.59706e-06, Final residual = 3.61317e-08, No Iterations 3
647039:DICPCG:  Solving for p_rgh, Initial residual = 1.32029e-05, Final residual = 1.27007e-07, No Iterations 30
647040:DICPCG:  Solving for p_rgh, Initial residual = 1.27008e-07, Final residual = 9.17645e-08, No Iterations 2
647041:DICPCG:  Solving for p_rgh, Initial residual = 9.17645e-08, Final residual = 9.17645e-08, No Iterations 0
647042:time step continuity errors : sum local = 2.5503e-10, global = -1.37245e-20, cumulative = 2.40986e-18
647044:smoothSolver:  Solving for Ux, Initial residual = 6.09997e-06, Final residual = 3.34101e-08, No Iterations 3
647045:smoothSolver:  Solving for Uy, Initial residual = 6.59744e-06, Final residual = 3.61337e-08, No Iterations 3
647047:DICPCG:  Solving for p_rgh, Initial residual = 1.31379e-05, Final residual = 1.2316e-07, No Iterations 30
647048:DICPCG:  Solving for p_rgh, Initial residual = 1.23162e-07, Final residual = 8.97307e-08, No Iterations 2
647049:DICPCG:  Solving for p_rgh, Initial residual = 8.97307e-08, Final residual = 8.97307e-08, No Iterations 0
647050:time step continuity errors : sum local = 2.48468e-10, global = 1.02485e-20, cumulative = 2.42011e-18
647052:smoothSolver:  Solving for Ux, Initial residual = 6.09921e-06, Final residual = 3.34058e-08, No Iterations 3
647053:smoothSolver:  Solving for Uy, Initial residual = 6.59782e-06, Final residual = 3.61357e-08, No Iterations 3
647055:DICPCG:  Solving for p_rgh, Initial residual = 1.30758e-05, Final residual = 1.18391e-07, No Iterations 30
647056:DICPCG:  Solving for p_rgh, Initial residual = 1.18393e-07, Final residual = 9.72345e-08, No Iterations 1
647057:DICPCG:  Solving for p_rgh, Initial residual = 9.72345e-08, Final residual = 9.72345e-08, No Iterations 0
647058:time step continuity errors : sum local = 2.64808e-10, global = -1.97285e-20, cumulative = 2.40038e-18
647060:smoothSolver:  Solving for Ux, Initial residual = 6.09843e-06, Final residual = 3.34014e-08, No Iterations 3
647061:smoothSolver:  Solving for Uy, Initial residual = 6.59817e-06, Final residual = 3.61376e-08, No Iterations 3
647063:DICPCG:  Solving for p_rgh, Initial residual = 1.30159e-05, Final residual = 1.13787e-07, No Iterations 30
647064:DICPCG:  Solving for p_rgh, Initial residual = 1.13788e-07, Final residual = 9.36453e-08, No Iterations 1
647065:DICPCG:  Solving for p_rgh, Initial residual = 9.36453e-08, Final residual = 9.36453e-08, No Iterations 0
647066:time step continuity errors : sum local = 2.5349e-10, global = 1.43606e-20, cumulative = 2.41474e-18
647068:smoothSolver:  Solving for Ux, Initial residual = 6.09767e-06, Final residual = 3.33971e-08, No Iterations 3
647069:smoothSolver:  Solving for Uy, Initial residual = 6.59847e-06, Final residual = 3.61391e-08, No Iterations 3
647071:DICPCG:  Solving for p_rgh, Initial residual = 1.29566e-05, Final residual = 1.10469e-07, No Iterations 30
647072:DICPCG:  Solving for p_rgh, Initial residual = 1.1047e-07, Final residual = 9.10462e-08, No Iterations 1
647073:DICPCG:  Solving for p_rgh, Initial residual = 9.10462e-08, Final residual = 9.10462e-08, No Iterations 0
647074:time step continuity errors : sum local = 2.44956e-10, global = 2.18169e-21, cumulative = 2.41692e-18
647076:smoothSolver:  Solving for Ux, Initial residual = 6.09696e-06, Final residual = 3.33931e-08, No Iterations 3
647077:smoothSolver:  Solving for Uy, Initial residual = 6.59869e-06, Final residual = 3.61402e-08, No Iterations 3
647079:DICPCG:  Solving for p_rgh, Initial residual = 1.28979e-05, Final residual = 1.28837e-07, No Iterations 29
647080:DICPCG:  Solving for p_rgh, Initial residual = 1.28838e-07, Final residual = 9.63732e-08, No Iterations 1
647081:DICPCG:  Solving for p_rgh, Initial residual = 9.63732e-08, Final residual = 9.63732e-08, No Iterations 0
647082:time step continuity errors : sum local = 2.56963e-10, global = -1.35826e-20, cumulative = 2.40334e-18
647084:smoothSolver:  Solving for Ux, Initial residual = 6.09634e-06, Final residual = 3.33896e-08, No Iterations 3
647085:smoothSolver:  Solving for Uy, Initial residual = 6.59881e-06, Final residual = 3.61408e-08, No Iterations 3
647087:DICPCG:  Solving for p_rgh, Initial residual = 1.28371e-05, Final residual = 1.26774e-07, No Iterations 14
647088:DICPCG:  Solving for p_rgh, Initial residual = 1.26775e-07, Final residual = 9.89941e-08, No Iterations 19
647089:DICPCG:  Solving for p_rgh, Initial residual = 9.89941e-08, Final residual = 9.89941e-08, No Iterations 0
647090:time step continuity errors : sum local = 2.63285e-10, global = 1.74535e-21, cumulative = 2.40509e-18
647092:smoothSolver:  Solving for Ux, Initial residual = 6.09574e-06, Final residual = 3.33862e-08, No Iterations 3
647093:smoothSolver:  Solving for Uy, Initial residual = 6.59894e-06, Final residual = 3.61414e-08, No Iterations 3
647095:DICPCG:  Solving for p_rgh, Initial residual = 1.27789e-05, Final residual = 1.27606e-07, No Iterations 13
647096:DICPCG:  Solving for p_rgh, Initial residual = 1.27607e-07, Final residual = 9.49547e-08, No Iterations 2
647097:DICPCG:  Solving for p_rgh, Initial residual = 9.49547e-08, Final residual = 9.49547e-08, No Iterations 0
647098:time step continuity errors : sum local = 2.6198e-10, global = 1.47921e-20, cumulative = 2.41988e-18
647100:smoothSolver:  Solving for Ux, Initial residual = 6.09598e-06, Final residual = 3.33881e-08, No Iterations 3
647101:smoothSolver:  Solving for Uy, Initial residual = 6.59819e-06, Final residual = 3.61381e-08, No Iterations 3
647103:DICPCG:  Solving for p_rgh, Initial residual = 1.27172e-05, Final residual = 1.17174e-07, No Iterations 30
647104:DICPCG:  Solving for p_rgh, Initial residual = 1.17175e-07, Final residual = 9.61771e-08, No Iterations 1
647105:DICPCG:  Solving for p_rgh, Initial residual = 9.61771e-08, Final residual = 9.61771e-08, No Iterations 0
647106:time step continuity errors : sum local = 2.60518e-10, global = 2.04469e-22, cumulative = 2.42008e-18
647109:ExecutionTime = 1018.01 s  ClockTime = 4324 s

codex
我已经确认了几条真实日志基线：LDC 尾部 `p≈7e-06`、continuity `~9e-07`，margin 很大；impinging_jet 的 `p_rgh` 在多个连续 `Time=` block 内双次打满 1000，A4 这部分是有真实依据的；而 cylinder 的 continuity 真实是 `1.5e-1` 量级，不是 YAML override 能解释的轻微 unsteady 抖动。
exec
/bin/zsh -lc 'rg -n "SOLVER_CRASH_LOG|SOLVER_ITERATION_CAP|CONTINUITY_NOT_CONVERGED|RESIDUALS_ABOVE_TARGET|BOUNDING_RECURRENT|NO_RESIDUAL_PROGRESS|ATTEST_HAZARD|ATTEST_FAIL|attestation" ui/backend/tests/test_validation_report.py ui/backend/tests -S' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
ui/backend/tests/test_dec040_attestation_surface.py:22:def test_dec040_ldc_audit_real_run_exposes_attestation(client: TestClient) -> None:
ui/backend/tests/test_dec040_attestation_surface.py:30:    attestation = body["attestation"]
ui/backend/tests/test_dec040_attestation_surface.py:31:    assert attestation is not None, "LDC audit fixture was backfilled with attestation"
ui/backend/tests/test_dec040_attestation_surface.py:32:    assert attestation["overall"] == "ATTEST_PASS"
ui/backend/tests/test_dec040_attestation_surface.py:34:    check_ids = [c["check_id"] for c in attestation["checks"]]
ui/backend/tests/test_dec040_attestation_surface.py:37:    assert all(c["verdict"] == "PASS" for c in attestation["checks"])
ui/backend/tests/test_dec040_attestation_surface.py:40:def test_dec040_reference_run_has_null_attestation(client: TestClient) -> None:
ui/backend/tests/test_dec040_attestation_surface.py:42:    solver log, so it should carry no attestation block → API returns null."""
ui/backend/tests/test_dec040_attestation_surface.py:46:    assert body["attestation"] is None, (
ui/backend/tests/test_dec040_attestation_surface.py:47:        "reference runs have no solver log; attestation must be null"
ui/backend/tests/test_dec040_attestation_surface.py:57:    from ui.backend.services.validation_report import _make_attestation
ui/backend/tests/test_dec040_attestation_surface.py:61:        _make_attestation(
ui/backend/tests/test_dec040_attestation_surface.py:62:            {"attestation": {"overall": "ATTEST_PASS", "checks": []}}
ui/backend/tests/test_dec040_attestation_surface.py:66:        _make_attestation(
ui/backend/tests/test_dec040_attestation_surface.py:68:                "attestation": {
ui/backend/tests/test_dec040_attestation_surface.py:77:    with pytest.raises(ValueError, match="attestation.overall must be one of"):
ui/backend/tests/test_dec040_attestation_surface.py:78:        _make_attestation(
ui/backend/tests/test_dec040_attestation_surface.py:79:            {"attestation": {"overall": "TOTALLY_BOGUS", "checks": []}}
ui/backend/tests/test_dec040_attestation_surface.py:82:    obj = _make_attestation(
ui/backend/tests/test_dec040_attestation_surface.py:83:        {"attestation": {"overall": "ATTEST_NOT_APPLICABLE", "checks": []}}
ui/backend/tests/test_dec040_attestation_surface.py:91:    """attestation + AttestorVerdict + AttestorCheck must be documented in
ui/backend/tests/test_dec040_attestation_surface.py:100:    assert "attestation" in vr["properties"]
ui/backend/tests/test_convergence_attestor.py:8:  BFS    → ATTEST_FAIL via A2 (sum_local=5.25e+18) + A3 HAZARD + A5 HAZARD
ui/backend/tests/test_convergence_attestor.py:44:    assert result.overall == "ATTEST_FAIL"
ui/backend/tests/test_convergence_attestor.py:357:    ATTEST_HAZARD (A2 HAZARD + A3 HAZARD + A5 HAZARD — no FAIL-tier check
ui/backend/tests/test_convergence_attestor.py:368:    assert result.overall == "ATTEST_HAZARD", f"got {result.overall}"
ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml:52:# ValidationReport.attestation. Generated by running src.convergence_attestor.attest
ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml:58:attestation:
ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml:63:    concern_type: SOLVER_CRASH_LOG
ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml:67:    concern_type: CONTINUITY_NOT_CONVERGED
ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml:71:    concern_type: RESIDUALS_ABOVE_TARGET
ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml:75:    concern_type: SOLVER_ITERATION_CAP
ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml:79:    concern_type: BOUNDING_RECURRENT
ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml:83:    concern_type: NO_RESIDUAL_PROGRESS

exec
/bin/zsh -lc "git show 7f29a64:knowledge/attestor_thresholds.yaml 2>/dev/null || echo 'MISSING_IN_7f29a64'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "git show 9716dd4:knowledge/attestor_thresholds.yaml 2>/dev/null || echo 'MISSING_IN_9716dd4'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "git show eb51dcf:knowledge/attestor_thresholds.yaml 2>/dev/null || echo 'MISSING_IN_eb51dcf'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
MISSING_IN_9716dd4

 succeeded in 0ms:
MISSING_IN_eb51dcf

 succeeded in 0ms:
MISSING_IN_7f29a64

exec
/bin/zsh -lc 'git show --stat --oneline 7f29a64 eb51dcf 9716dd4' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-k9zWZu9V' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-9wrSE2Gf' (errno=Operation not permitted)
7f29a64 feat(phase8): DEC-V61-038 convergence attestor A1..A6 (pre-extraction)
 ...026-04-22_phase8_dec038_convergence_attestor.md | 175 ++++++++
 scripts/phase5_audit_run.py                        |  42 +-
 src/convergence_attestor.py                        | 483 +++++++++++++++++++++
 ui/backend/services/validation_report.py           |  14 +-
 ui/backend/tests/test_convergence_attestor.py      | 262 +++++++++++
 5 files changed, 967 insertions(+), 9 deletions(-)
eb51dcf fix(phase8): DEC-V61-038 round 2 — Codex BLOCKERs: A4 p_rgh + block-counting
 src/convergence_attestor.py                   | 120 +++++++++++++++--------
 ui/backend/tests/test_convergence_attestor.py | 132 ++++++++++++++++++++++++--
 2 files changed, 200 insertions(+), 52 deletions(-)
9716dd4 fix(phase8): DEC-V61-038 round 2 nit — PBiCGStab regex ordering
 src/convergence_attestor.py | 6 +++++-
 1 file changed, 5 insertions(+), 1 deletion(-)

codex
我发现一个更大的顺序问题在冒头：`_audit_fixture_doc()` 里 attestor 确实在 gates 前，但它已经晚于 `_primary_scalar(report, …)` 和 `comparison_result` 的读取；如果 `report` 是执行完 comparator 之后才进来的，那它不是“pre-extraction”，只是“pre-gate”。我去把调用链钉死。
exec
/bin/zsh -lc "nl -ba scripts/phase5_audit_run.py | sed -n '520,860p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba src/task_runner.py | sed -n '1,280p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   520	    return out
   521	
   522	
   523	def run_one(runner: TaskRunner, case_id: str, commit_sha: str) -> dict:
   524	    t0 = time.monotonic()
   525	    print(f"[audit] {case_id} → start", flush=True)
   526	
   527	    # Phase 7a — author the single shared timestamp up front; the executor-side
   528	    # _capture_field_artifacts writes to reports/phase5_fields/{case_id}/{ts}/.
   529	    # Codex round 1 MED #3: only inject metadata for opted-in cases — other 9
   530	    # case generators do not emit Phase 7a function objects yet.
   531	    ts = _phase7a_timestamp()
   532	    try:
   533	        spec = runner._task_spec_from_case_id(case_id)
   534	        if case_id in _PHASE7A_OPTED_IN:
   535	            if spec.metadata is None:
   536	                spec.metadata = {}
   537	            spec.metadata["phase7a_timestamp"] = ts
   538	            spec.metadata["phase7a_case_id"] = case_id
   539	        report = runner.run_task(spec)
   540	    except Exception as e:  # noqa: BLE001
   541	        print(f"[audit] {case_id} EXCEPTION: {e!r}")
   542	        return {"case_id": case_id, "ok": False, "error": repr(e)}
   543	
   544	    dt = time.monotonic() - t0
   545	
   546	    # Phase 7a — write per-run manifest + build field_artifacts_ref dict iff
   547	    # the case is opted-in AND the artifact dir materialized with non-empty
   548	    # contents (best-effort, must not block audit doc). MED #3 gating above.
   549	    run_label = "audit_real_run"
   550	    manifest_path = (
   551	        _write_field_artifacts_run_manifest(case_id, run_label, ts)
   552	        if case_id in _PHASE7A_OPTED_IN
   553	        else None
   554	    )
   555	    field_artifacts_ref: "dict | None" = None
   556	    if manifest_path is not None:
   557	        field_artifacts_ref = {
   558	            "manifest_path_rel": str(manifest_path.relative_to(REPO_ROOT)),
   559	            "run_label": run_label,
   560	            # Deliberately NO timestamp string here (byte-repro): resolve via manifest.
   561	        }
   562	
   563	    doc = _audit_fixture_doc(
   564	        case_id,
   565	        report,
   566	        commit_sha,
   567	        field_artifacts_ref=field_artifacts_ref,
   568	        phase7a_timestamp=ts,
   569	    )
   570	    fixture_path = _write_audit_fixture(case_id, doc)
   571	    raw_path = _write_raw_capture(case_id, report, dt)
   572	    verdict = doc["run_metadata"]["expected_verdict"]
   573	    print(f"[audit] {case_id} → {verdict} · {dt:.1f}s · {fixture_path.name}", flush=True)
   574	    return {
   575	        "case_id": case_id,
   576	        "ok": True,
   577	        "duration_s": round(dt, 3),
   578	        "verdict": verdict,
   579	        "fixture": str(fixture_path.relative_to(REPO_ROOT)),
   580	        "raw": str(raw_path.relative_to(REPO_ROOT)),
   581	        "field_artifacts_manifest": (
   582	            str(manifest_path.relative_to(REPO_ROOT)) if manifest_path else None
   583	        ),
   584	    }
   585	
   586	
   587	def main() -> int:
   588	    parser = argparse.ArgumentParser()
   589	    parser.add_argument("cases", nargs="*", help="case ids; use --all for all 10")
   590	    parser.add_argument("--all", action="store_true", help="run all 10 whitelist cases")
   591	    args = parser.parse_args()
   592	
   593	    if os.environ.get("EXECUTOR_MODE", "").lower() != "foam_agent":
   594	        print("ERROR: set EXECUTOR_MODE=foam_agent", file=sys.stderr)
   595	        return 2
   596	
   597	    targets = ALL_CASES if args.all else args.cases
   598	    if not targets:
   599	        parser.print_help()
   600	        return 2
   601	
   602	    commit_sha = _git_head_sha()
   603	    print(f"[audit] commit: {commit_sha} · cases: {targets}")
   604	
   605	    runner = TaskRunner(executor=FoamAgentExecutor())
   606	    summary = []
   607	    for case_id in targets:
   608	        summary.append(run_one(runner, case_id, commit_sha))
   609	
   610	    print("\n=== SUMMARY ===")
   611	    for r in summary:
   612	        if r["ok"]:
   613	            print(f"{r['case_id']:38s} {r['verdict']:5s} {r['duration_s']:.1f}s")
   614	        else:
   615	            print(f"{r['case_id']:38s} ERROR {r['error'][:80]}")
   616	
   617	    ok_count = sum(1 for r in summary if r["ok"])
   618	    return 0 if ok_count == len(summary) else 1
   619	
   620	
   621	if __name__ == "__main__":
   622	    sys.exit(main())

 succeeded in 0ms:
     1	"""核心编排器：从 Notion 读取任务 → 执行 → 对比 → 记录 → 回写"""
     2	
     3	from __future__ import annotations
     4	
     5	import logging
     6	import os
     7	from dataclasses import dataclass
     8	from typing import Any, Callable, Dict, List, Optional
     9	
    10	from .foam_agent_adapter import FoamAgentExecutor, MockExecutor
    11	from .knowledge_db import KnowledgeDB
    12	from .models import (
    13	    AttributionReport,
    14	    BatchResult,
    15	    CFDExecutor,
    16	    ComparisonResult,
    17	    Compressibility,
    18	    CorrectionSpec,
    19	    ExecutionResult,
    20	    FlowType,
    21	    GeometryType,
    22	    SteadyState,
    23	    SystematicPattern,
    24	    TaskSpec,
    25	)
    26	from .notion_client import NotionClient
    27	from .result_comparator import ResultComparator
    28	from .correction_recorder import CorrectionRecorder
    29	from .error_attributor import ErrorAttributor
    30	
    31	PostExecuteHook = Callable[
    32	    [TaskSpec, ExecutionResult, Optional[ComparisonResult], Optional[CorrectionSpec]],
    33	    Any,
    34	]
    35	
    36	CORRECTION_POLICIES = ("legacy_auto_save", "suggest_only")
    37	
    38	logger = logging.getLogger(__name__)
    39	
    40	
    41	@dataclass
    42	class RunReport:
    43	    """单次任务运行的完整报告"""
    44	    task_spec: TaskSpec
    45	    execution_result: ExecutionResult
    46	    comparison_result: Optional[ComparisonResult]
    47	    correction_spec: Optional[CorrectionSpec]
    48	    summary: str
    49	    auto_verify_report: Any = None  # AutoVerifyReport or hook-returned status dict, when hook configured
    50	
    51	
    52	class TaskRunner:
    53	    """核心编排器
    54	
    55	    使用方式：
    56	        runner = TaskRunner(executor=MockExecutor())
    57	        reports = runner.run_all()
    58	    """
    59	
    60	    def __init__(
    61	        self,
    62	        executor: Optional[CFDExecutor] = None,
    63	        notion_client: Optional[NotionClient] = None,
    64	        knowledge_db: Optional[KnowledgeDB] = None,
    65	        deviation_threshold: float = 0.10,
    66	        post_execute_hook: Optional[PostExecuteHook] = None,
    67	        correction_policy: str = "legacy_auto_save",
    68	    ) -> None:
    69	        if correction_policy not in CORRECTION_POLICIES:
    70	            raise ValueError(
    71	                f"correction_policy must be one of {CORRECTION_POLICIES}, got {correction_policy!r}"
    72	            )
    73	        # Precedence: explicit executor kwarg > EXECUTOR_MODE env var > MockExecutor
    74	        if executor is not None:
    75	            self._executor: CFDExecutor = executor
    76	        else:
    77	            mode = os.environ.get("EXECUTOR_MODE", "mock").lower()
    78	            if mode == "mock":
    79	                self._executor = MockExecutor()
    80	            elif mode == "foam_agent":
    81	                self._executor = FoamAgentExecutor()
    82	            else:
    83	                raise ValueError(
    84	                    f'EXECUTOR_MODE must be "mock" or "foam_agent", got "{mode}"'
    85	                )
    86	        self._notion = notion_client or NotionClient()
    87	        self._db = knowledge_db or KnowledgeDB()
    88	        self._comparator = ResultComparator(threshold=deviation_threshold)
    89	        self._recorder = CorrectionRecorder()
    90	        self._attributor = ErrorAttributor(knowledge_db=self._db)
    91	        self._post_execute_hook = post_execute_hook
    92	        self._correction_policy = correction_policy
    93	
    94	    # ------------------------------------------------------------------
    95	    # 公开接口
    96	    # ------------------------------------------------------------------
    97	
    98	    def run_task(self, task_spec: TaskSpec) -> RunReport:
    99	        """执行单个任务，返回完整报告"""
   100	        logger.info("Running task: %s", task_spec.name)
   101	
   102	        # 1. 执行 CFD
   103	        exec_result = self._executor.execute(task_spec)
   104	        logger.info("Execution success=%s is_mock=%s", exec_result.success, exec_result.is_mock)
   105	
   106	        # 2. 加载 Gold Standard
   107	        gold = self._db.load_gold_standard(task_spec.name)
   108	        comparison: Optional[ComparisonResult] = None
   109	        correction: Optional[CorrectionSpec] = None
   110	
   111	        # 3. 对比结果
   112	        if gold is not None and exec_result.success:
   113	            comparison = self._comparator.compare(exec_result, gold)
   114	            logger.info("Comparison passed=%s", comparison.passed)
   115	
   116	            # 4. 如有偏差 → 生成 CorrectionSpec (saved only under legacy_auto_save policy)
   117	            if not comparison.passed:
   118	                correction = self._recorder.record(task_spec, exec_result, comparison)
   119	                if self._correction_policy == "legacy_auto_save":
   120	                    self._db.save_correction(correction)
   121	                else:
   122	                    logger.info(
   123	                        "correction_policy=%s: CorrectionSpec built but not persisted",
   124	                        self._correction_policy,
   125	                    )
   126	
   127	        # 5. AutoVerifier post-execute hook (SPEC §INT-1, additive)
   128	        auto_verify_report: Any = None
   129	        if self._post_execute_hook is not None:
   130	            try:
   131	                auto_verify_report = self._post_execute_hook(
   132	                    task_spec, exec_result, comparison, correction
   133	                )
   134	            except Exception:  # noqa: BLE001 - hook is optional, must not kill run
   135	                logger.exception("post_execute_hook raised; continuing without verify report")
   136	
   137	        # 6. 生成摘要
   138	        summary = self._build_summary(exec_result, comparison, correction)
   139	
   140	        # 7. 回写 Notion（Notion 未配置时静默跳过）
   141	        try:
   142	            self._notion.write_execution_result(task_spec, exec_result, summary)
   143	        except NotImplementedError:
   144	            logger.debug("Notion not configured, skipping write-back")
   145	
   146	        return RunReport(
   147	            task_spec=task_spec,
   148	            execution_result=exec_result,
   149	            comparison_result=comparison,
   150	            correction_spec=correction,
   151	            summary=summary,
   152	            auto_verify_report=auto_verify_report,
   153	        )
   154	
   155	    def run_all(self) -> List[RunReport]:
   156	        """从 Notion 读取所有 Ready 任务并逐一运行"""
   157	        try:
   158	            tasks = self._notion.list_pending_tasks()
   159	        except NotImplementedError:
   160	            logger.warning("Notion not configured; run_all() returns empty list")
   161	            return []
   162	
   163	        reports = []
   164	        for task in tasks:
   165	            report = self.run_task(task)
   166	            reports.append(report)
   167	        return reports
   168	
   169	    def run_batch(self, case_ids: List[str]) -> BatchResult:
   170	        """批量执行指定 case_id 列表（串行，一个失败不阻塞其他）。
   171	
   172	        每个 case 执行 run_task -> compare -> attribute 完整链路。
   173	        """
   174	        results: List[ComparisonResult] = []
   175	        attribution_reports: List[Optional[AttributionReport]] = []
   176	        errors: List[str] = []
   177	        passed = 0
   178	        failed = 0
   179	        total = len(case_ids)
   180	
   181	        for idx, case_id in enumerate(case_ids, 1):
   182	            try:
   183	                task_spec = self._task_spec_from_case_id(case_id)
   184	                report = self.run_task(task_spec)
   185	
   186	                comparison = report.comparison_result
   187	                if comparison is None:
   188	                    comparison = self._ensure_batch_comparison(case_id, report)
   189	
   190	                results.append(comparison)
   191	
   192	                # 归因（即使 passed=True 也做归因）
   193	                if comparison is not None:
   194	                    attribution = self._attributor.attribute(task_spec, report.execution_result, comparison)
   195	                else:
   196	                    attribution = None
   197	                attribution_reports.append(attribution)
   198	
   199	                if report.comparison_result is not None and report.comparison_result.passed:
   200	                    passed += 1
   201	                    print(f"Case {idx}/{total}: {case_id} [PASSED]")
   202	                else:
   203	                    failed += 1
   204	                    print(f"Case {idx}/{total}: {case_id} [FAILED]")
   205	
   206	            except Exception:
   207	                failed += 1
   208	                errors.append(case_id)
   209	                results.append(ComparisonResult(passed=False, summary=f"Exception during {case_id}"))
   210	                attribution_reports.append(None)
   211	                logger.exception("Batch case failed: %s", case_id)
   212	                print(f"Case {idx}/{total}: {case_id} [ERROR]")
   213	
   214	        # Batch-level systematic pattern analysis
   215	        systematic_patterns = self._analyze_systematic_patterns(case_ids, results, attribution_reports)
   216	
   217	        return BatchResult(
   218	            total=total,
   219	            passed=passed,
   220	            failed=failed,
   221	            errors=errors,
   222	            results=results,
   223	            attribution_reports=attribution_reports,
   224	            systematic_patterns=systematic_patterns,
   225	        )
   226	
   227	    def _task_spec_from_case_id(self, case_id: str) -> TaskSpec:
   228	        """从 knowledge_db 通过 case_id 还原 TaskSpec。"""
   229	        chain = self._db.get_execution_chain(case_id)
   230	        if chain is None:
   231	            raise ValueError(f"Unknown case_id: {case_id}")
   232	        parameters = chain.get("parameters", {})
   233	        return TaskSpec(
   234	            name=chain.get("case_name", case_id),
   235	            geometry_type=GeometryType(chain.get("geometry_type", "SIMPLE_GRID")),
   236	            flow_type=FlowType(chain.get("flow_type", "INTERNAL")),
   237	            steady_state=SteadyState(chain.get("steady_state", "STEADY")),
   238	            compressibility=Compressibility(chain.get("compressibility", "INCOMPRESSIBLE")),
   239	            Re=parameters.get("Re"),
   240	            Ra=parameters.get("Ra"),
   241	            Re_tau=parameters.get("Re_tau"),
   242	            Ma=parameters.get("Ma"),
   243	            boundary_conditions={**chain.get("boundary_conditions", {}), **parameters},  # includes aspect_ratio, plate_length, etc.
   244	            description=chain.get("reference", ""),
   245	        )
   246	
   247	    def _ensure_batch_comparison(self, case_id: str, report: RunReport) -> ComparisonResult:
   248	        """确保 report 有 comparison_result（如果没有则尝试生成）。"""
   249	        if report.comparison_result is not None:
   250	            return report.comparison_result
   251	        if not report.execution_result.success:
   252	            return ComparisonResult(
   253	                passed=False,
   254	                summary=report.execution_result.error_message or "Execution failed before comparison",
   255	            )
   256	        gold = self._db.load_gold_standard(case_id) or self._db.load_gold_standard(report.task_spec.name)
   257	        if gold is None:
   258	            return ComparisonResult(
   259	                passed=False,
   260	                summary=f"No gold standard found for case '{case_id}'",
   261	            )
   262	        return self._comparator.compare(report.execution_result, gold)
   263	
   264	    def _analyze_systematic_patterns(
   265	        self,
   266	        case_ids: List[str],
   267	        results: List[ComparisonResult],
   268	        attribution_reports: List[Optional[AttributionReport]],
   269	    ) -> List[SystematicPattern]:
   270	        """检测批量执行中的系统性误差模式（frequency > 0.5）。"""
   271	        cause_counts: Dict[str, List[str]] = {}
   272	        for case_id, attr in zip(case_ids, attribution_reports):
   273	            if attr is None:
   274	                continue
   275	            cause = attr.primary_cause
   276	            if cause not in ("unknown", "none", ""):
   277	                cause_counts.setdefault(cause, []).append(case_id)
   278	
   279	        patterns = []
   280	        total = len(case_ids)

exec
/bin/zsh -lc "nl -ba src/task_runner.py | sed -n '281,520p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   281	        for cause, affected in cause_counts.items():
   282	            freq = len(affected) / total
   283	            if freq > 0.5:
   284	                if freq > 0.75:
   285	                    confidence = "high"
   286	                elif freq > 0.5:
   287	                    confidence = "medium"
   288	                else:
   289	                    confidence = "low"
   290	
   291	                recommendations = {
   292	                    "mock_executor": "Consider Docker real execution for these cases to get physical results",
   293	                    "sample_config_mismatch": "Review sampleDict configuration — field names may not match generated output",
   294	                    "mesh": "Consider increasing mesh resolution across affected cases",
   295	                    "turbulence": "Review turbulence model selection — kEpsilon may be more stable than kOmegaSST for these geometries",
   296	                    "boundary_condition": "Verify BC setup against reference literature",
   297	                    "solver": "Check solver convergence settings — may need adjusted relaxation or time step",
   298	                }
   299	                patterns.append(SystematicPattern(
   300	                    cause=cause,
   301	                    affected_cases=affected,
   302	                    frequency=freq,
   303	                    confidence=confidence,
   304	                    recommendation=recommendations.get(cause, f"Review cases with {cause} root cause"),
   305	                ))
   306	        return patterns
   307	
   308	    # ------------------------------------------------------------------
   309	    # 内部辅助
   310	    # ------------------------------------------------------------------
   311	
   312	    @staticmethod
   313	    def _build_summary(
   314	        exec_result: ExecutionResult,
   315	        comparison: Optional[ComparisonResult],
   316	        correction: Optional[CorrectionSpec],
   317	    ) -> str:
   318	        parts = []
   319	        status = "✅ Success" if exec_result.success else "❌ Failed"
   320	        parts.append(f"{status} (mock={exec_result.is_mock}, t={exec_result.execution_time_s:.2f}s)")
   321	        if comparison is not None:
   322	            parts.append(f"Comparison: {'PASS' if comparison.passed else 'FAIL'}")
   323	            if comparison.deviations:
   324	                parts.append(f"Deviations: {len(comparison.deviations)}")
   325	        if correction is not None:
   326	            parts.append(f"CorrectionSpec generated: {correction.error_type.value}")
   327	        return " | ".join(parts)

exec
/bin/zsh -lc "rg -n \"_audit_fixture_doc\\(|TaskRunner\\(|run_task\\(|comparison_result|execute_task|audit_real_run\" scripts/phase5_audit_run.py src/task_runner.py src/result_comparator.py -S" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
scripts/phase5_audit_run.py:2:a deterministic audit fixture into fixtures/runs/{case_id}/audit_real_run_measurement.yaml.
scripts/phase5_audit_run.py:13:    ui/backend/tests/fixtures/runs/{case_id}/audit_real_run_measurement.yaml
scripts/phase5_audit_run.py:138:    comp = report.comparison_result
scripts/phase5_audit_run.py:292:def _audit_fixture_doc(
scripts/phase5_audit_run.py:305:    comp = report.comparison_result
scripts/phase5_audit_run.py:323:            "run_id": "audit_real_run",
scripts/phase5_audit_run.py:332:            "category": "audit_real_run",
scripts/phase5_audit_run.py:481:    out_path = case_dir / "audit_real_run_measurement.yaml"
scripts/phase5_audit_run.py:501:    comp = report.comparison_result
scripts/phase5_audit_run.py:539:        report = runner.run_task(spec)
scripts/phase5_audit_run.py:549:    run_label = "audit_real_run"
scripts/phase5_audit_run.py:563:    doc = _audit_fixture_doc(
scripts/phase5_audit_run.py:605:    runner = TaskRunner(executor=FoamAgentExecutor())
src/task_runner.py:46:    comparison_result: Optional[ComparisonResult]
src/task_runner.py:56:        runner = TaskRunner(executor=MockExecutor())
src/task_runner.py:98:    def run_task(self, task_spec: TaskSpec) -> RunReport:
src/task_runner.py:149:            comparison_result=comparison,
src/task_runner.py:165:            report = self.run_task(task)
src/task_runner.py:184:                report = self.run_task(task_spec)
src/task_runner.py:186:                comparison = report.comparison_result
src/task_runner.py:199:                if report.comparison_result is not None and report.comparison_result.passed:
src/task_runner.py:248:        """确保 report 有 comparison_result（如果没有则尝试生成）。"""
src/task_runner.py:249:        if report.comparison_result is not None:
src/task_runner.py:250:            return report.comparison_result

exec
/bin/zsh -lc "nl -ba ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml | sed -n '1,120p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba ui/backend/tests/test_dec040_attestation_surface.py | sed -n '1,140p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
     1	# Phase 5a audit-real-run fixture — AUTO-GENERATED, DO NOT HAND-EDIT.
     2	# Regenerate via:
     3	#   EXECUTOR_MODE=foam_agent .venv/bin/python scripts/phase5_audit_run.py lid_driven_cavity
     4	# This fixture backs the signed audit package. Byte-identity across
     5	# re-runs (modulo timestamp + commit_sha) is enforced by
     6	# test_phase5_byte_repro.py.
     7	
     8	run_metadata:
     9	  run_id: audit_real_run
    10	  label_zh: 真实 solver 审计运行
    11	  label_en: Real solver audit run
    12	  description_zh: FoamAgentExecutor 驱动 OpenFOAM 实际跑出的结果（commit 1cc18b2）。这是 audit package
    13	    背书的权威测量——不是合成 fixture。失败的话说明 case 本身的 physics_contract 在当前 mesh 预算下无法满足，不是 harness
    14	    bug；会进入 audit_concerns 随包交付给审查方。
    15	  category: audit_real_run
    16	  expected_verdict: FAIL
    17	case_id: lid_driven_cavity
    18	source: phase5_audit_run_foam_agent
    19	measurement:
    20	  value: -0.197225625
    21	  unit: dimensionless
    22	  run_id: audit_lid_driven_cavity_1cc18b2
    23	  commit_sha: 1cc18b2
    24	  measured_at: '2026-04-21T08:24:08Z'
    25	  quantity: u_centerline[y=0.3750]
    26	  extraction_source: comparator_deviation
    27	  solver_success: true
    28	  comparator_passed: false
    29	audit_concerns:
    30	- concern_type: CONTRACT_STATUS
    31	  summary: 'Quantity: u_centerline | Tolerance: 5.0% | Failed: 6 deviation(s)'
    32	  detail: 'Quantity: u_centerline | Tolerance: 5.0% | Failed: 6 deviation(s)'
    33	  decision_refs:
    34	  - DEC-V61-028
    35	- concern_type: DEVIATIONS
    36	  summary: 6 deviation(s) over tolerance
    37	  detail: 'u_centerline[y=0.3750]: actual=-0.197225625 expected=-0.18622; u_centerline[y=0.5625]:
    38	    actual=-0.18213393749999995 expected=-0.1688; u_centerline[y=0.6875]: actual=-0.06125237499999994
    39	    expected=-0.0526; u_centerline[y=0.7500]: actual=0.026644375000000005 expected=0.03369;
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
    51	# DEC-V61-040: solver-iteration attestor verdict, lifted into the API via
    52	# ValidationReport.attestation. Generated by running src.convergence_attestor.attest
    53	# against reports/phase5_fields/lid_driven_cavity/20260421T082340Z/log.simpleFoam —
    54	# NOT hand-authored. Regenerate on next phase5_audit_run.py refresh.
    55	# LDC converges cleanly so every A-check is PASS and overall is ATTEST_PASS;
    56	# the scalar contract still FAILs because the comparator picked the wrong
    57	# profile point for the scalar (DEC-V61-036/039 split-brain).
    58	attestation:
    59	  overall: ATTEST_PASS
    60	  checks:
    61	  - check_id: A1
    62	    verdict: PASS
    63	    concern_type: SOLVER_CRASH_LOG
    64	    summary: no FOAM FATAL / floating exception in log
    65	  - check_id: A2
    66	    verdict: PASS
    67	    concern_type: CONTINUITY_NOT_CONVERGED
    68	    summary: final sum_local=9.45e-07 ≤ 1e-04
    69	  - check_id: A3
    70	    verdict: PASS
    71	    concern_type: RESIDUALS_ABOVE_TARGET
    72	    summary: all residuals ≤ 1e-03
    73	  - check_id: A4
    74	    verdict: PASS
    75	    concern_type: SOLVER_ITERATION_CAP
    76	    summary: pressure solver peaked at 7 iterations
    77	  - check_id: A5
    78	    verdict: PASS
    79	    concern_type: BOUNDING_RECURRENT
    80	    summary: no bounding in last 50 iters
    81	  - check_id: A6
    82	    verdict: PASS
    83	    concern_type: NO_RESIDUAL_PROGRESS
    84	    summary: all residual histories show > 1 decade decay in tail window
    85	

 succeeded in 0ms:
     1	"""DEC-V61-040: tests for attestor verdict surfacing via ValidationReport.
     2	
     3	DEC-V61-038 writes the A1..A6 attestor verdict onto the fixture at audit
     4	time; DEC-V61-040 threads that verdict through the API so the UI can
     5	render a DualVerdictBadge (scalar contract + attestor) and an AttestorPanel
     6	with the per-check breakdown.
     7	"""
     8	
     9	from __future__ import annotations
    10	
    11	import pytest
    12	from fastapi.testclient import TestClient
    13	
    14	from ui.backend.main import app
    15	
    16	
    17	@pytest.fixture(scope="module")
    18	def client() -> TestClient:
    19	    return TestClient(app)
    20	
    21	
    22	def test_dec040_ldc_audit_real_run_exposes_attestation(client: TestClient) -> None:
    23	    """LDC audit_real_run: scalar FAIL but attestor ATTEST_PASS (clean
    24	    convergence, just wrong scalar point picked). Both must be in the API
    25	    response as independent verdicts."""
    26	    r = client.get("/api/validation-report/lid_driven_cavity?run_id=audit_real_run")
    27	    assert r.status_code == 200
    28	    body = r.json()
    29	    assert body["contract_status"] == "FAIL"
    30	    attestation = body["attestation"]
    31	    assert attestation is not None, "LDC audit fixture was backfilled with attestation"
    32	    assert attestation["overall"] == "ATTEST_PASS"
    33	    # All 6 checks present.
    34	    check_ids = [c["check_id"] for c in attestation["checks"]]
    35	    assert check_ids == ["A1", "A2", "A3", "A4", "A5", "A6"]
    36	    # Every check PASS for the clean LDC run.
    37	    assert all(c["verdict"] == "PASS" for c in attestation["checks"])
    38	
    39	
    40	def test_dec040_reference_run_has_null_attestation(client: TestClient) -> None:
    41	    """reference_pass is a curated literature-anchored fixture with no
    42	    solver log, so it should carry no attestation block → API returns null."""
    43	    r = client.get("/api/validation-report/lid_driven_cavity?run_id=reference_pass")
    44	    assert r.status_code == 200
    45	    body = r.json()
    46	    assert body["attestation"] is None, (
    47	        "reference runs have no solver log; attestation must be null"
    48	    )
    49	
    50	
    51	def test_dec040_parser_fails_closed_on_contradictory_payload() -> None:
    52	    """Codex round-2 FLAG: the attestor only emits checks:[] for
    53	    ATTEST_NOT_APPLICABLE. Any other overall with empty checks — or
    54	    ATTEST_NOT_APPLICABLE with non-empty checks — is a corrupt fixture
    55	    and must fail closed at the parsing boundary so the UI can't render
    56	    a contradictory ATTEST_PASS badge + 'no solver log' message."""
    57	    from ui.backend.services.validation_report import _make_attestation
    58	
    59	    # ATTEST_PASS with empty checks: physically impossible → ValueError.
    60	    with pytest.raises(ValueError, match="requires non-empty checks"):
    61	        _make_attestation(
    62	            {"attestation": {"overall": "ATTEST_PASS", "checks": []}}
    63	        )
    64	    # ATTEST_NOT_APPLICABLE with checks: also impossible → ValueError.
    65	    with pytest.raises(ValueError, match="must have empty checks"):
    66	        _make_attestation(
    67	            {
    68	                "attestation": {
    69	                    "overall": "ATTEST_NOT_APPLICABLE",
    70	                    "checks": [
    71	                        {"check_id": "A1", "verdict": "PASS"},
    72	                    ],
    73	                }
    74	            }
    75	        )
    76	    # Malformed overall → ValueError.
    77	    with pytest.raises(ValueError, match="attestation.overall must be one of"):
    78	        _make_attestation(
    79	            {"attestation": {"overall": "TOTALLY_BOGUS", "checks": []}}
    80	        )
    81	    # Valid ATTEST_NOT_APPLICABLE with empty checks is accepted.
    82	    obj = _make_attestation(
    83	        {"attestation": {"overall": "ATTEST_NOT_APPLICABLE", "checks": []}}
    84	    )
    85	    assert obj is not None
    86	    assert obj.overall == "ATTEST_NOT_APPLICABLE"
    87	    assert obj.checks == []
    88	
    89	
    90	def test_dec040_schema_fields_present_in_openapi(client: TestClient) -> None:
    91	    """attestation + AttestorVerdict + AttestorCheck must be documented in
    92	    the OpenAPI schema so TypeScript clients can rely on them."""
    93	    r = client.get("/api/openapi.json")
    94	    assert r.status_code == 200
    95	    spec = r.json()
    96	    schemas = spec["components"]["schemas"]
    97	    assert "AttestorVerdict" in schemas
    98	    assert "AttestorCheck" in schemas
    99	    vr = schemas["ValidationReport"]
   100	    assert "attestation" in vr["properties"]
   101	    av = schemas["AttestorVerdict"]
   102	    props = av["properties"]
   103	    assert "overall" in props
   104	    assert "checks" in props

exec
/bin/zsh -lc 'rg -n "attestor_thresholds|continuity_floor|residual_floor|no_progress_decade_frac|bounding_recurrence_window|iteration_cap_detector_count" -S src ui scripts knowledge .planning' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:16:    A2 continuity_floor    — final sum_local ≤ case-specific floor (default 1e-4 incompressible)
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:17:    A3 residual_floor      — final Ux/Uy/Uz/p/k/epsilon/omega initial residuals ≤ case target (default 1e-3)
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:46:  risk is threshold calibration — specifically A3 residual_floor on
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:110:4. **Per-case thresholds** in new `knowledge/attestor_thresholds.yaml`:
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:113:     continuity_floor: 1.0e-4
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:114:     residual_floor: 1.0e-3
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:115:     iteration_cap_detector_count: 3
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:117:     bounding_recurrence_window: 50
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:118:     no_progress_decade_frac: 1.0
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:123:       residual_floor: 5.0e-3
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:126:       residual_floor: 2.0e-3
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:127:       no_progress_decade_frac: 0.3
.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md:130:       continuity_floor: 1.0e-3
ui/backend/tests/test_convergence_attestor.py:61:# A2 continuity_floor
ui/backend/tests/test_convergence_attestor.py:102:# A3 residual_floor
src/convergence_attestor.py:18:    A2 continuity_floor        — final sum_local ≤ case floor        → HAZARD
src/convergence_attestor.py:19:    A3 residual_floor          — final initial residuals ≤ target    → HAZARD
src/convergence_attestor.py:26:via knowledge/attestor_thresholds.yaml (not shipped in this DEC —
src/convergence_attestor.py:47:A2_CONTINUITY_FLOOR = 1.0e-4           # incompressible steady; G5 fires at 1e-2
src/convergence_attestor.py:48:A3_RESIDUAL_FLOOR = 1.0e-3             # initial residual of any field
src/convergence_attestor.py:233:def _check_a2_continuity_floor(log_path: Path) -> AttestorCheck:
src/convergence_attestor.py:242:    if sl > A2_CONTINUITY_FLOOR:
src/convergence_attestor.py:255:            summary=(f"final sum_local={sl:.3g} > floor {A2_CONTINUITY_FLOOR:.0e}")[:240],
src/convergence_attestor.py:258:                f"convergence should be ≤ {A2_CONTINUITY_FLOOR:.0e}. Observed "
src/convergence_attestor.py:259:                f"final sum_local={sl:.6g}. Values between {A2_CONTINUITY_FLOOR:.0e} "
src/convergence_attestor.py:263:            evidence={"sum_local": sl, "threshold": A2_CONTINUITY_FLOOR},
src/convergence_attestor.py:267:        summary=f"final sum_local={sl:.3g} ≤ {A2_CONTINUITY_FLOOR:.0e}",
src/convergence_attestor.py:272:def _check_a3_residual_floor(log_path: Path) -> AttestorCheck:
src/convergence_attestor.py:283:        if last > A3_RESIDUAL_FLOOR:
src/convergence_attestor.py:288:            f"final residuals above {A3_RESIDUAL_FLOOR:.0e}: "
src/convergence_attestor.py:297:                f"should be ≤ {A3_RESIDUAL_FLOOR:.0e}. Fields listed above have "
src/convergence_attestor.py:303:            evidence={"offenders": offenders, "threshold": A3_RESIDUAL_FLOOR},
src/convergence_attestor.py:307:        summary=f"all residuals ≤ {A3_RESIDUAL_FLOOR:.0e}",
src/convergence_attestor.py:436:        if hi < A3_RESIDUAL_FLOOR:
src/convergence_attestor.py:494:        _check_a2_continuity_floor(log_path),
src/convergence_attestor.py:495:        _check_a3_residual_floor(log_path),

exec
/bin/zsh -lc 'latest=$(ls -1 reports/phase5_fields/impinging_jet | rg -v '"'"'^runs$'"' | sort | tail -n1); log=reports/phase5_fields/impinging_jet/"'$latest/$(ls reports/phase5_fields/impinging_jet/$latest | rg '"'"'^log'"\\.'); rg -o \"Solving for [A-Za-z_]+\" \""'$log" | sort -u' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
Solving for Uy
Solving for epsilon
Solving for h
Solving for k
Solving for p_rgh

exec
/bin/zsh -lc 'latest=$(ls -1 reports/phase5_fields/naca0012_airfoil | rg -v '"'"'^runs$'"' | sort | tail -n1); log=reports/phase5_fields/naca0012_airfoil/"'$latest/$(ls reports/phase5_fields/naca0012_airfoil/$latest | rg '"'"'^log'"\\.'); rg -o \"Solving for [A-Za-z_]+\" \""'$log" | sort -u' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
Solving for Ux
Solving for Uz
Solving for k
Solving for omega
Solving for p

exec
/bin/zsh -lc 'latest=$(ls -1 reports/phase5_fields/differential_heated_cavity | rg -v '"'"'^runs$'"' | sort | tail -n1); log=reports/phase5_fields/differential_heated_cavity/"'$latest/$(ls reports/phase5_fields/differential_heated_cavity/$latest | rg '"'"'^log'"\\.'); rg -o \"Solving for [A-Za-z_]+\" \""'$log" | sort -u' in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc 'latest=$(ls -1 reports/phase5_fields/rayleigh_benard_convection | rg -v '"'"'^runs$'"' | sort | tail -n1); log=reports/phase5_fields/rayleigh_benard_convection/"'$latest/$(ls reports/phase5_fields/rayleigh_benard_convection/$latest | rg '"'"'^log'"\\.'); rg -o \"Solving for [A-Za-z_]+\" \""'$log" | sort -u' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 383ms:
Solving for Ux
Solving for Uy
Solving for h
Solving for k
Solving for omega
Solving for p_rgh

 succeeded in 387ms:
Solving for Ux
Solving for Uy
Solving for h
Solving for k
Solving for omega
Solving for p_rgh

codex
我又看到一个潜在 physics 误判点：A6 现在是把所有 `Initial residual` 一股脑按字段串起来看尾窗，没有区分 buoyant/PIMPLE 同一 outer step 里的多次 `p_rgh` solve。像 impinging_jet 这种每步两次 `p_rgh` 都在 0.6 左右，它很可能把“正常的 inner-cycle 结构”当成“长期无进展”。我先把现有 fixture 里的实际 A6 结果翻出来。
exec
/bin/zsh -lc 'for c in impinging_jet rayleigh_benard_convection differential_heated_cavity circular_cylinder_wake backward_facing_step; do f=ui/backend/tests/fixtures/runs/$c/audit_real_run_measurement.yaml; echo "CASE $c"; if [ -f "$f" ]; then rg -n "attestation|check_id: A6|check_id: A4|overall:|summary:" "$f"; else echo MISSING_FIXTURE; fi; done' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
CASE impinging_jet
31:  summary: 'Quantity: nusselt_number | Tolerance: 15.0% | Failed: 1 deviation(s)'
36:  summary: 1 deviation(s) over tolerance
CASE rayleigh_benard_convection
31:  summary: 'Quantity: nusselt_number | Tolerance: 15.0% | Failed: 1 deviation(s)'
36:  summary: 1 deviation(s) over tolerance
CASE differential_heated_cavity
31:  summary: 'Quantity: nusselt_number | Tolerance: 10.0% | Failed: 1 deviation(s)'
36:  summary: 1 deviation(s) over tolerance
CASE circular_cylinder_wake
31:  summary: 'Quantity: strouhal_number | Tolerance: 5.0% | PASS'
CASE backward_facing_step
31:  summary: 'Quantity ''reattachment_length'' not found in execution result (tried
40:  summary: 1 deviation(s) over tolerance

exec
/bin/zsh -lc 'latest=$(ls -1 reports/phase5_fields/impinging_jet | rg -v '"'"'^runs$'"' | sort | tail -n1); log=reports/phase5_fields/impinging_jet/"'$latest/$(ls reports/phase5_fields/impinging_jet/$latest | rg '"'"'^log'"\\.'); rg -n \"Solving for p_rgh, Initial residual\" \""'$log" | tail -n 60' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
2311:GAMG:  Solving for p_rgh, Initial residual = 0.663229, Final residual = 0.376295, No Iterations 1000
2313:GAMG:  Solving for p_rgh, Initial residual = 0.613729, Final residual = 0.38274, No Iterations 1000
2324:GAMG:  Solving for p_rgh, Initial residual = 0.681004, Final residual = 0.399393, No Iterations 1000
2326:GAMG:  Solving for p_rgh, Initial residual = 0.636548, Final residual = 0.40783, No Iterations 1000
2337:GAMG:  Solving for p_rgh, Initial residual = 0.692875, Final residual = 0.414044, No Iterations 1000
2339:GAMG:  Solving for p_rgh, Initial residual = 0.627641, Final residual = 0.428355, No Iterations 1000
2350:GAMG:  Solving for p_rgh, Initial residual = 0.683862, Final residual = 0.423314, No Iterations 1000
2352:GAMG:  Solving for p_rgh, Initial residual = 0.642333, Final residual = 0.393178, No Iterations 1000
2363:GAMG:  Solving for p_rgh, Initial residual = 0.659962, Final residual = 0.391799, No Iterations 1000
2365:GAMG:  Solving for p_rgh, Initial residual = 0.637209, Final residual = 0.410821, No Iterations 1000
2376:GAMG:  Solving for p_rgh, Initial residual = 0.662477, Final residual = 0.401895, No Iterations 1000
2378:GAMG:  Solving for p_rgh, Initial residual = 0.627902, Final residual = 0.401377, No Iterations 1000
2389:GAMG:  Solving for p_rgh, Initial residual = 0.656649, Final residual = 0.423047, No Iterations 1000
2391:GAMG:  Solving for p_rgh, Initial residual = 0.621321, Final residual = 0.422042, No Iterations 1000
2402:GAMG:  Solving for p_rgh, Initial residual = 0.65181, Final residual = 0.405576, No Iterations 1000
2404:GAMG:  Solving for p_rgh, Initial residual = 0.616041, Final residual = 0.391483, No Iterations 1000
2415:GAMG:  Solving for p_rgh, Initial residual = 0.643117, Final residual = 0.390224, No Iterations 1000
2417:GAMG:  Solving for p_rgh, Initial residual = 0.599291, Final residual = 0.368826, No Iterations 1000
2428:GAMG:  Solving for p_rgh, Initial residual = 0.591409, Final residual = 0.351836, No Iterations 1000
2430:GAMG:  Solving for p_rgh, Initial residual = 0.610738, Final residual = 0.383977, No Iterations 1000
2441:GAMG:  Solving for p_rgh, Initial residual = 0.69178, Final residual = 0.399009, No Iterations 1000
2443:GAMG:  Solving for p_rgh, Initial residual = 0.628697, Final residual = 0.40091, No Iterations 1000
2454:GAMG:  Solving for p_rgh, Initial residual = 0.693759, Final residual = 0.406498, No Iterations 1000
2456:GAMG:  Solving for p_rgh, Initial residual = 0.608811, Final residual = 0.409043, No Iterations 1000
2467:GAMG:  Solving for p_rgh, Initial residual = 0.647042, Final residual = 0.412379, No Iterations 1000
2469:GAMG:  Solving for p_rgh, Initial residual = 0.643712, Final residual = 0.399435, No Iterations 1000
2480:GAMG:  Solving for p_rgh, Initial residual = 0.698051, Final residual = 0.419535, No Iterations 1000
2482:GAMG:  Solving for p_rgh, Initial residual = 0.642988, Final residual = 0.395266, No Iterations 1000
2493:GAMG:  Solving for p_rgh, Initial residual = 0.672728, Final residual = 0.427543, No Iterations 1000
2495:GAMG:  Solving for p_rgh, Initial residual = 0.6276, Final residual = 0.401421, No Iterations 1000
2506:GAMG:  Solving for p_rgh, Initial residual = 0.670699, Final residual = 0.400156, No Iterations 1000
2508:GAMG:  Solving for p_rgh, Initial residual = 0.635268, Final residual = 0.39949, No Iterations 1000
2519:GAMG:  Solving for p_rgh, Initial residual = 0.694662, Final residual = 0.418027, No Iterations 1000
2521:GAMG:  Solving for p_rgh, Initial residual = 0.638852, Final residual = 0.403196, No Iterations 1000
2532:GAMG:  Solving for p_rgh, Initial residual = 0.673448, Final residual = 0.39827, No Iterations 1000
2534:GAMG:  Solving for p_rgh, Initial residual = 0.637939, Final residual = 0.402707, No Iterations 1000
2545:GAMG:  Solving for p_rgh, Initial residual = 0.67743, Final residual = 0.413041, No Iterations 1000
2547:GAMG:  Solving for p_rgh, Initial residual = 0.631031, Final residual = 0.395467, No Iterations 1000
2558:GAMG:  Solving for p_rgh, Initial residual = 0.679164, Final residual = 0.405846, No Iterations 1000
2560:GAMG:  Solving for p_rgh, Initial residual = 0.641321, Final residual = 0.411755, No Iterations 1000
2571:GAMG:  Solving for p_rgh, Initial residual = 0.689558, Final residual = 0.406748, No Iterations 1000
2573:GAMG:  Solving for p_rgh, Initial residual = 0.646375, Final residual = 0.404612, No Iterations 1000
2584:GAMG:  Solving for p_rgh, Initial residual = 0.688593, Final residual = 0.402598, No Iterations 1000
2586:GAMG:  Solving for p_rgh, Initial residual = 0.635277, Final residual = 0.398652, No Iterations 1000
2597:GAMG:  Solving for p_rgh, Initial residual = 0.68918, Final residual = 0.391067, No Iterations 1000
2599:GAMG:  Solving for p_rgh, Initial residual = 0.636691, Final residual = 0.391876, No Iterations 1000
2610:GAMG:  Solving for p_rgh, Initial residual = 0.682505, Final residual = 0.419573, No Iterations 1000
2612:GAMG:  Solving for p_rgh, Initial residual = 0.62494, Final residual = 0.400635, No Iterations 1000
2623:GAMG:  Solving for p_rgh, Initial residual = 0.668501, Final residual = 0.385151, No Iterations 1000
2625:GAMG:  Solving for p_rgh, Initial residual = 0.616779, Final residual = 0.38122, No Iterations 1000
2636:GAMG:  Solving for p_rgh, Initial residual = 0.688022, Final residual = 0.394222, No Iterations 1000
2638:GAMG:  Solving for p_rgh, Initial residual = 0.634429, Final residual = 0.424925, No Iterations 1000
2649:GAMG:  Solving for p_rgh, Initial residual = 0.680301, Final residual = 0.41528, No Iterations 1000
2651:GAMG:  Solving for p_rgh, Initial residual = 0.603709, Final residual = 0.390799, No Iterations 1000
2662:GAMG:  Solving for p_rgh, Initial residual = 0.63835, Final residual = 0.370794, No Iterations 1000
2664:GAMG:  Solving for p_rgh, Initial residual = 0.595911, Final residual = 0.378764, No Iterations 1000
2675:GAMG:  Solving for p_rgh, Initial residual = 0.647868, Final residual = 0.386576, No Iterations 1000
2677:GAMG:  Solving for p_rgh, Initial residual = 0.631239, Final residual = 0.421711, No Iterations 1000
2688:GAMG:  Solving for p_rgh, Initial residual = 0.675998, Final residual = 0.397685, No Iterations 1000
2690:GAMG:  Solving for p_rgh, Initial residual = 0.618798, Final residual = 0.411033, No Iterations 1000

exec
/bin/zsh -lc 'latest=$(ls -1 reports/phase5_fields/impinging_jet | rg -v '"'"'^runs$'"' | sort | tail -n1); log=reports/phase5_fields/impinging_jet/"'$latest/$(ls reports/phase5_fields/impinging_jet/$latest | rg '"'"'^log'"\\.'); rg -n \"Solving for (Uy|h|k|epsilon), Initial residual\" \""'$log" | tail -n 80' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
2439:DILUPBiCGStab:  Solving for Uy, Initial residual = 0.309737, Final residual = 5.90355e-05, No Iterations 1
2440:DILUPBiCGStab:  Solving for h, Initial residual = 0.000951945, Final residual = 5.7075e-06, No Iterations 1
2445:DILUPBiCGStab:  Solving for epsilon, Initial residual = 0.000133803, Final residual = 5.16494e-08, No Iterations 1
2446:DILUPBiCGStab:  Solving for k, Initial residual = 0.00494117, Final residual = 2.82628e-06, No Iterations 1
2452:DILUPBiCGStab:  Solving for Uy, Initial residual = 0.256552, Final residual = 5.4253e-05, No Iterations 1
2453:DILUPBiCGStab:  Solving for h, Initial residual = 0.000925217, Final residual = 4.60069e-06, No Iterations 1
2458:DILUPBiCGStab:  Solving for epsilon, Initial residual = 0.000103336, Final residual = 4.98389e-08, No Iterations 1
2459:DILUPBiCGStab:  Solving for k, Initial residual = 0.00468073, Final residual = 2.53436e-06, No Iterations 1
2465:DILUPBiCGStab:  Solving for Uy, Initial residual = 0.167954, Final residual = 5.52983e-05, No Iterations 1
2466:DILUPBiCGStab:  Solving for h, Initial residual = 0.000900429, Final residual = 3.19947e-06, No Iterations 1
2471:DILUPBiCGStab:  Solving for epsilon, Initial residual = 0.000128837, Final residual = 5.71039e-08, No Iterations 1
2472:DILUPBiCGStab:  Solving for k, Initial residual = 0.00493141, Final residual = 2.95197e-06, No Iterations 1
2478:DILUPBiCGStab:  Solving for Uy, Initial residual = 0.209224, Final residual = 5.45477e-05, No Iterations 1
2479:DILUPBiCGStab:  Solving for h, Initial residual = 0.000920072, Final residual = 4.49476e-06, No Iterations 1
2484:DILUPBiCGStab:  Solving for epsilon, Initial residual = 0.000129942, Final residual = 7.43771e-08, No Iterations 1
2485:DILUPBiCGStab:  Solving for k, Initial residual = 0.00530968, Final residual = 3.43936e-06, No Iterations 1
2491:DILUPBiCGStab:  Solving for Uy, Initial residual = 0.241863, Final residual = 5.15175e-05, No Iterations 1
2492:DILUPBiCGStab:  Solving for h, Initial residual = 0.000914665, Final residual = 4.4892e-06, No Iterations 1
2497:DILUPBiCGStab:  Solving for epsilon, Initial residual = 0.000124878, Final residual = 5.88643e-08, No Iterations 1
2498:DILUPBiCGStab:  Solving for k, Initial residual = 0.00488166, Final residual = 3.03461e-06, No Iterations 1
2504:DILUPBiCGStab:  Solving for Uy, Initial residual = 0.130338, Final residual = 5.34761e-05, No Iterations 1
2505:DILUPBiCGStab:  Solving for h, Initial residual = 0.000915294, Final residual = 4.60766e-06, No Iterations 1
2510:DILUPBiCGStab:  Solving for epsilon, Initial residual = 0.000106532, Final residual = 5.67597e-08, No Iterations 1
2511:DILUPBiCGStab:  Solving for k, Initial residual = 0.00464914, Final residual = 2.89635e-06, No Iterations 1
2517:DILUPBiCGStab:  Solving for Uy, Initial residual = 0.195074, Final residual = 5.03854e-05, No Iterations 1
2518:DILUPBiCGStab:  Solving for h, Initial residual = 0.00088957, Final residual = 3.42213e-06, No Iterations 1
2523:DILUPBiCGStab:  Solving for epsilon, Initial residual = 0.000135382, Final residual = 7.22428e-08, No Iterations 1
2524:DILUPBiCGStab:  Solving for k, Initial residual = 0.00524764, Final residual = 3.46169e-06, No Iterations 1
2530:DILUPBiCGStab:  Solving for Uy, Initial residual = 0.278824, Final residual = 0.00273716, No Iterations 1
2531:DILUPBiCGStab:  Solving for h, Initial residual = 0.000919447, Final residual = 5.04823e-06, No Iterations 1
2536:DILUPBiCGStab:  Solving for epsilon, Initial residual = 0.000106982, Final residual = 5.89298e-08, No Iterations 1
2537:DILUPBiCGStab:  Solving for k, Initial residual = 0.00461134, Final residual = 3.01282e-06, No Iterations 1
2543:DILUPBiCGStab:  Solving for Uy, Initial residual = 0.128993, Final residual = 4.5459e-05, No Iterations 1
2544:DILUPBiCGStab:  Solving for h, Initial residual = 0.000884163, Final residual = 3.49421e-06, No Iterations 1
2549:DILUPBiCGStab:  Solving for epsilon, Initial residual = 0.000125074, Final residual = 6.36337e-08, No Iterations 1
2550:DILUPBiCGStab:  Solving for k, Initial residual = 0.00503351, Final residual = 3.17775e-06, No Iterations 1
2556:DILUPBiCGStab:  Solving for Uy, Initial residual = 0.130856, Final residual = 4.96218e-05, No Iterations 1
2557:DILUPBiCGStab:  Solving for h, Initial residual = 0.000911689, Final residual = 4.95619e-06, No Iterations 1
2562:DILUPBiCGStab:  Solving for epsilon, Initial residual = 0.000109073, Final residual = 5.61763e-08, No Iterations 1
2563:DILUPBiCGStab:  Solving for k, Initial residual = 0.0046538, Final residual = 2.9816e-06, No Iterations 1
2569:DILUPBiCGStab:  Solving for Uy, Initial residual = 0.298648, Final residual = 5.20952e-05, No Iterations 1
2570:DILUPBiCGStab:  Solving for h, Initial residual = 0.000881103, Final residual = 3.74127e-06, No Iterations 1
2575:DILUPBiCGStab:  Solving for epsilon, Initial residual = 0.000111287, Final residual = 5.42602e-08, No Iterations 1
2576:DILUPBiCGStab:  Solving for k, Initial residual = 0.00474688, Final residual = 2.92958e-06, No Iterations 1
2582:DILUPBiCGStab:  Solving for Uy, Initial residual = 0.362038, Final residual = 0.00331582, No Iterations 1
2583:DILUPBiCGStab:  Solving for h, Initial residual = 0.000888962, Final residual = 4.18848e-06, No Iterations 1
2588:DILUPBiCGStab:  Solving for epsilon, Initial residual = 0.000107201, Final residual = 5.77036e-08, No Iterations 1
2589:DILUPBiCGStab:  Solving for k, Initial residual = 0.00464747, Final residual = 3.05546e-06, No Iterations 1
2595:DILUPBiCGStab:  Solving for Uy, Initial residual = 0.166283, Final residual = 6.03397e-05, No Iterations 1
2596:DILUPBiCGStab:  Solving for h, Initial residual = 0.000867963, Final residual = 2.83482e-06, No Iterations 1
2601:DILUPBiCGStab:  Solving for epsilon, Initial residual = 0.000105803, Final residual = 4.90886e-08, No Iterations 1
2602:DILUPBiCGStab:  Solving for k, Initial residual = 0.00450265, Final residual = 2.80406e-06, No Iterations 1
2608:DILUPBiCGStab:  Solving for Uy, Initial residual = 0.269981, Final residual = 4.76758e-05, No Iterations 1
2609:DILUPBiCGStab:  Solving for h, Initial residual = 0.000884739, Final residual = 4.61438e-06, No Iterations 1
2614:DILUPBiCGStab:  Solving for epsilon, Initial residual = 0.000121953, Final residual = 6.24371e-08, No Iterations 1
2615:DILUPBiCGStab:  Solving for k, Initial residual = 0.00490779, Final residual = 3.07256e-06, No Iterations 1
2621:DILUPBiCGStab:  Solving for Uy, Initial residual = 0.150621, Final residual = 5.35032e-05, No Iterations 1
2622:DILUPBiCGStab:  Solving for h, Initial residual = 0.000887964, Final residual = 4.43215e-06, No Iterations 1
2627:DILUPBiCGStab:  Solving for epsilon, Initial residual = 9.67706e-05, Final residual = 4.72006e-08, No Iterations 1
2628:DILUPBiCGStab:  Solving for k, Initial residual = 0.00442936, Final residual = 2.70549e-06, No Iterations 1
2634:DILUPBiCGStab:  Solving for Uy, Initial residual = 0.339311, Final residual = 0.00318735, No Iterations 1
2635:DILUPBiCGStab:  Solving for h, Initial residual = 0.000866353, Final residual = 3.55726e-06, No Iterations 1
2640:DILUPBiCGStab:  Solving for epsilon, Initial residual = 9.37398e-05, Final residual = 3.98377e-08, No Iterations 1
2641:DILUPBiCGStab:  Solving for k, Initial residual = 0.00437663, Final residual = 2.35161e-06, No Iterations 1
2647:DILUPBiCGStab:  Solving for Uy, Initial residual = 0.176444, Final residual = 5.45188e-05, No Iterations 1
2648:DILUPBiCGStab:  Solving for h, Initial residual = 0.000859613, Final residual = 2.93847e-06, No Iterations 1
2653:DILUPBiCGStab:  Solving for epsilon, Initial residual = 9.15795e-05, Final residual = 3.30944e-08, No Iterations 1
2654:DILUPBiCGStab:  Solving for k, Initial residual = 0.00434463, Final residual = 2.00103e-06, No Iterations 1
2660:DILUPBiCGStab:  Solving for Uy, Initial residual = 0.283097, Final residual = 0.00236322, No Iterations 1
2661:DILUPBiCGStab:  Solving for h, Initial residual = 0.000854427, Final residual = 2.49358e-06, No Iterations 1
2666:DILUPBiCGStab:  Solving for epsilon, Initial residual = 8.86205e-05, Final residual = 2.79437e-08, No Iterations 1
2667:DILUPBiCGStab:  Solving for k, Initial residual = 0.00431282, Final residual = 1.71443e-06, No Iterations 1
2673:DILUPBiCGStab:  Solving for Uy, Initial residual = 0.134741, Final residual = 3.73504e-05, No Iterations 1
2674:DILUPBiCGStab:  Solving for h, Initial residual = 0.000849805, Final residual = 2.17062e-06, No Iterations 1
2679:DILUPBiCGStab:  Solving for epsilon, Initial residual = 8.60601e-05, Final residual = 2.49571e-08, No Iterations 1
2680:DILUPBiCGStab:  Solving for k, Initial residual = 0.00430013, Final residual = 1.66888e-06, No Iterations 1
2686:DILUPBiCGStab:  Solving for Uy, Initial residual = 0.134968, Final residual = 3.86042e-05, No Iterations 1
2687:DILUPBiCGStab:  Solving for h, Initial residual = 0.000845766, Final residual = 1.93476e-06, No Iterations 1
2692:DILUPBiCGStab:  Solving for epsilon, Initial residual = 0.000109324, Final residual = 4.78776e-08, No Iterations 1
2693:DILUPBiCGStab:  Solving for k, Initial residual = 0.00458987, Final residual = 2.67404e-06, No Iterations 1

codex
我要确认一个具体误报而不是停在推断：直接用当前实现对 impinging_jet 日志做一次只读 attestation，看看 A6 是否真的被打出来。
2026-04-22T10:48:31.797211Z ERROR codex_core::tools::router: error=exec_command failed for `/bin/zsh -lc "PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
from pathlib import Path
from src.convergence_attestor import attest
log = Path('reports/phase5_fields/impinging_jet/20260421T142307Z/log.buoyantSimpleFoam')
res = attest(log)
print(res.overall)
for c in res.checks:
    print(c.check_id, c.verdict, c.summary)
PY"`: CreateProcess { message: "Codex(Sandbox(Denied { output: ExecToolCallOutput { exit_code: 1, stdout: StreamOutput { text: \"\", truncated_after_lines: None }, stderr: StreamOutput { text: \"zsh:1: can't create temp file for here document: operation not permitted\\n\", truncated_after_lines: None }, aggregated_output: StreamOutput { text: \"zsh:1: can't create temp file for here document: operation not permitted\\n\", truncated_after_lines: None }, duration: 0ns, timed_out: false }, network_policy_decision: None }))" }
exec
/bin/zsh -lc "PYTHONDONTWRITEBYTECODE=1 python3 -c \"from pathlib import Path; from src.convergence_attestor import attest; log=Path('reports/phase5_fields/impinging_jet/20260421T142307Z/log.buoyantSimpleFoam'); res=attest(log); print(res.overall); [print(c.check_id, c.verdict, c.summary) for c in res.checks]\"" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
python3: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
python3: error: couldn't create cache file '/tmp/xcrun_db-wm2DtxSm' (errno=Operation not permitted)
python3: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
python3: error: couldn't create cache file '/tmp/xcrun_db-wgzTWKZb' (errno=Operation not permitted)
ATTEST_NOT_APPLICABLE

exec
/bin/zsh -lc 'ls -1 reports/phase5_fields/impinging_jet/20260421T142307Z' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
VTK
log.buoyantFoam

exec
/bin/zsh -lc "PYTHONDONTWRITEBYTECODE=1 python3 -c \"from pathlib import Path; from src.convergence_attestor import attest; log=Path('reports/phase5_fields/impinging_jet/20260421T142307Z/log.buoyantFoam'); res=attest(log); print(res.overall); [print(c.check_id, c.verdict, c.summary) for c in res.checks]\"" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
python3: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
python3: error: couldn't create cache file '/tmp/xcrun_db-lmznpq6C' (errno=Operation not permitted)
python3: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
python3: error: couldn't create cache file '/tmp/xcrun_db-lTny8kqs' (errno=Operation not permitted)
ATTEST_FAIL
A1 PASS no FOAM FATAL / floating exception in log
A2 PASS final sum_local=1.07e-07 ≤ 1e-04
A3 HAZARD final residuals above 1e-03: p_rgh=0.619, Uy=0.135, k=0.00459
A4 FAIL pressure solver hit 1000 iterations in ≥ 3 consecutive time-step blocks
A5 PASS no bounding in last 50 iters
A6 HAZARD p_rgh residual range over last 50 iters: 5.91e-01 – 6.98e-01 (0.07 decades)

exec
/bin/zsh -lc "PYTHONDONTWRITEBYTECODE=1 python3 -c \"from pathlib import Path; from src.convergence_attestor import attest; log=Path('reports/phase5_fields/circular_cylinder_wake/20260421T150630Z/log.pimpleFoam'); res=attest(log); print(res.overall); [print(c.check_id, c.verdict, c.summary) for c in res.checks]\"" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "PYTHONDONTWRITEBYTECODE=1 python3 -c \"from pathlib import Path; from src.convergence_attestor import attest; log=Path('reports/phase5_fields/lid_driven_cavity/20260421T082340Z/log.simpleFoam'); res=attest(log); print(res.overall); [print(c.check_id, c.verdict, c.summary) for c in res.checks]\"" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
python3: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
python3: error: couldn't create cache file '/tmp/xcrun_db-PDXn12Qt' (errno=Operation not permitted)
python3: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
python3: error: couldn't create cache file '/tmp/xcrun_db-sLDTOXpn' (errno=Operation not permitted)
ATTEST_PASS
A1 PASS no FOAM FATAL / floating exception in log
A2 PASS final sum_local=9.45e-07 ≤ 1e-04
A3 PASS all residuals ≤ 1e-03
A4 PASS pressure solver peaked at 7 iterations
A5 PASS no bounding in last 50 iters
A6 PASS all residual histories show > 1 decade decay in tail window

 succeeded in 103ms:
exec
/bin/zsh -lc "PYTHONDONTWRITEBYTECODE=1 python3 -c \"from pathlib import Path; from src.convergence_attestor import attest; log=Path('reports/phase5_fields/backward_facing_step/20260421T125637Z/log.simpleFoam'); res=attest(log); print(res.overall); [print(c.check_id, c.verdict, c.summary) for c in res.checks]\"" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
python3: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
python3: error: couldn't create cache file '/tmp/xcrun_db-63i9vhQV' (errno=Operation not permitted)
python3: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
python3: error: couldn't create cache file '/tmp/xcrun_db-rzRSZgQ7' (errno=Operation not permitted)
ATTEST_HAZARD
A1 PASS no FOAM FATAL / floating exception in log
A2 HAZARD final sum_local=5.25e+18 > floor 1e-04
A3 HAZARD final residuals above 1e-03: Ux=0.0375, Uy=0.0234
A4 PASS pressure solver peaked at 40 iterations
A5 HAZARD k bounded in 100% of last 36 iterations (threshold 30%)
A6 PASS all residual histories show > 1 decade decay in tail window

exec
/bin/zsh -lc 'rg -n "class ExecutionResult|success: bool|error_message|exit_code" src -S' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
src/correction_recorder.py:132:            exec_result.error_message or "",
src/task_runner.py:254:                summary=report.execution_result.error_message or "Execution failed before comparison",
src/models.py:90:class ExecutionResult:
src/models.py:92:    success: bool
src/models.py:98:    error_message: Optional[str] = None
src/error_attributor.py:382:        # Stage 0: 无偏差时 — 尝试从 error_message 做 solver-level 归因
src/error_attributor.py:736:        err = exec_result.error_message or ""
src/foam_agent_adapter.py:6940:            return result.exit_code == 0, log_path.read_text(encoding="utf-8", errors="replace")
src/foam_agent_adapter.py:6941:        return result.exit_code == 0, str(result.output)
src/foam_agent_adapter.py:8695:            error_message=message,

exec
/bin/zsh -lc "nl -ba src/models.py | sed -n '80,120p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
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
    91	    """CFD 执行结果"""
    92	    success: bool
    93	    is_mock: bool
    94	    residuals: Dict[str, float] = field(default_factory=dict)
    95	    key_quantities: Dict[str, Any] = field(default_factory=dict)
    96	    execution_time_s: float = 0.0
    97	    raw_output_path: Optional[str] = None
    98	    error_message: Optional[str] = None
    99	
   100	
   101	@dataclass
   102	class DeviationDetail:
   103	    """单个物理量的偏差记录"""
   104	    quantity: str
   105	    expected: Any
   106	    actual: Any
   107	    relative_error: Optional[float] = None
   108	    tolerance: Optional[float] = None
   109	
   110	
   111	@dataclass
   112	class ComparisonResult:
   113	    """结果 vs Gold Standard 对比"""
   114	    passed: bool
   115	    deviations: List[DeviationDetail] = field(default_factory=list)
   116	    summary: str = ""
   117	    gold_standard_id: Optional[str] = None
   118	
   119	
   120	@dataclass

exec
/bin/zsh -lc "nl -ba src/foam_agent_adapter.py | sed -n '8678,8705p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba src/foam_agent_adapter.py | sed -n '6928,6950p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
  8678	    # ------------------------------------------------------------------
  8679	    # Error helper
  8680	    # ------------------------------------------------------------------
  8681	
  8682	    @staticmethod
  8683	    def _fail(
  8684	        message: str,
  8685	        elapsed: float,
  8686	        raw_output_path: Optional[str] = None,
  8687	    ) -> ExecutionResult:
  8688	        return ExecutionResult(
  8689	            success=False,
  8690	            is_mock=False,
  8691	            residuals={},
  8692	            key_quantities={},
  8693	            execution_time_s=elapsed,
  8694	            raw_output_path=raw_output_path,
  8695	            error_message=message,
  8696	        )

 succeeded in 0ms:
  6928	            f"{command} > log.{safe_log_name} 2>&1"
  6929	        )
  6930	        result = container.exec_run(
  6931	            cmd=["bash", "-c", bash_cmd],
  6932	            workdir=working_dir,
  6933	        )
  6934	
  6935	        # Step 5: 读取容器内的 log 文件
  6936	        log_path = host_case_dir / f"log.{safe_log_name}"
  6937	        self._copy_file_from_container(container, f"{working_dir}/log.{safe_log_name}", log_path)
  6938	
  6939	        if log_path.exists() and log_path.stat().st_size > 0:
  6940	            return result.exit_code == 0, log_path.read_text(encoding="utf-8", errors="replace")
  6941	        return result.exit_code == 0, str(result.output)
  6942	
  6943	    @staticmethod
  6944	    def _make_tarball(src_dir: Path) -> bytes:
  6945	        """把目录内容打包成 tarball bytes（用于 put_archive）。
  6946	
  6947	        Recursive walk of all subdirectories.
  6948	        Strips host permissions to avoid container write issues.
  6949	        All files set to 0644, all dirs set to 0755.
  6950	        """

exec
/bin/zsh -lc 'rg -n "_derive_contract_status|HAZARD|CONTINUITY_NOT_CONVERGED|RESIDUALS_ABOVE_TARGET|BOUNDING_RECURRENT|NO_RESIDUAL_PROGRESS" ui/backend/tests -S' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
ui/backend/tests/fixtures/differential_heated_cavity_measurement.yaml:20:  - concern_type: COMPATIBLE_WITH_SILENT_PASS_HAZARD
ui/backend/tests/test_comparator_gates_g3_g4_g5.py:230:    from ui.backend.services.validation_report import _derive_contract_status
ui/backend/tests/test_comparator_gates_g3_g4_g5.py:252:    status, deviation, within, _, _ = _derive_contract_status(
ui/backend/tests/test_comparator_gates_g3_g4_g5.py:269:    from ui.backend.services.validation_report import _derive_contract_status
ui/backend/tests/test_comparator_gates_g3_g4_g5.py:280:    status, _, _, _, _ = _derive_contract_status(gs, m, [], concerns)
ui/backend/tests/test_comparator_gates_g3_g4_g5.py:290:    from ui.backend.services.validation_report import _derive_contract_status
ui/backend/tests/test_comparator_gates_g3_g4_g5.py:300:    status, _, within, _, _ = _derive_contract_status(gs, m, [], [])
ui/backend/tests/test_decisions_and_dashboard.py:91:    # 2026-04-22 review. HAZARD cases may or may not survive (cylinder/
ui/backend/tests/test_convergence_attestor.py:3:Coverage: each check's PASS/HAZARD/FAIL branch + LDC/BFS integration
ui/backend/tests/test_convergence_attestor.py:8:  BFS    → ATTEST_FAIL via A2 (sum_local=5.25e+18) + A3 HAZARD + A5 HAZARD
ui/backend/tests/test_convergence_attestor.py:76:    """sum_local between A2 floor (1e-4) and G5 floor (1e-2) → HAZARD."""
ui/backend/tests/test_convergence_attestor.py:84:    assert a2.verdict == "HAZARD"
ui/backend/tests/test_convergence_attestor.py:90:    gate layer. A2 stays strictly HAZARD-tier."""
ui/backend/tests/test_convergence_attestor.py:98:    assert a2.verdict == "HAZARD"  # was FAIL pre-fix
ui/backend/tests/test_convergence_attestor.py:124:    assert a3.verdict == "HAZARD"
ui/backend/tests/test_convergence_attestor.py:229:    """Codex DEC-038 round-1 comment A7: A2 stays HAZARD-tier to avoid
ui/backend/tests/test_convergence_attestor.py:230:    split-brain with G5. Even sum_local=0.5 returns HAZARD from A2 (G5
ui/backend/tests/test_convergence_attestor.py:239:    assert a2.verdict == "HAZARD"  # was FAIL pre-fix
ui/backend/tests/test_convergence_attestor.py:262:    """≥30% of last 50 iterations with `bounding k` → HAZARD."""
ui/backend/tests/test_convergence_attestor.py:271:    assert a5.verdict == "HAZARD"
ui/backend/tests/test_convergence_attestor.py:293:    """Ux stuck at 0.4 ± 0.02 for 60 iterations → HAZARD (high and flat)."""
ui/backend/tests/test_convergence_attestor.py:303:    assert a6.verdict == "HAZARD"
ui/backend/tests/test_convergence_attestor.py:357:    ATTEST_HAZARD (A2 HAZARD + A3 HAZARD + A5 HAZARD — no FAIL-tier check
ui/backend/tests/test_convergence_attestor.py:361:    This test asserts the attestor HAZARD verdict; contract-FAIL coverage
ui/backend/tests/test_convergence_attestor.py:368:    assert result.overall == "ATTEST_HAZARD", f"got {result.overall}"
ui/backend/tests/test_convergence_attestor.py:369:    # Multiple HAZARD-tier concerns should be present.
ui/backend/tests/test_convergence_attestor.py:370:    hazard_checks = [c for c in result.checks if c.verdict == "HAZARD"]
ui/backend/tests/test_convergence_attestor.py:374:    assert a2.verdict == "HAZARD"
ui/backend/tests/test_validation_report.py:71:    assert "COMPATIBLE_WITH_SILENT_PASS_HAZARD" in types
ui/backend/tests/test_validation_report.py:88:    # Measurement equals ref_value → inside tolerance → HAZARD (not PASS)
ui/backend/tests/test_validation_report.py:90:    assert body["contract_status"] == "HAZARD"
ui/backend/tests/test_validation_report.py:93:    assert "COMPATIBLE_WITH_SILENT_PASS_HAZARD" in types
ui/backend/tests/test_validation_report.py:111:    assert body["contract_status"] in ("HAZARD", "PASS", "FAIL")
ui/backend/tests/test_g1_missing_target_quantity.py:88:    """Synthetic contract: when measurement.value is None, _derive_contract_status
ui/backend/tests/test_g1_missing_target_quantity.py:96:    from ui.backend.services.validation_report import _derive_contract_status
ui/backend/tests/test_g1_missing_target_quantity.py:117:    status, deviation, within, lower, upper = _derive_contract_status(
ui/backend/tests/test_phase5_byte_repro.py:95:    assert md["expected_verdict"] in {"PASS", "FAIL", "HAZARD", "UNKNOWN"}, (
ui/backend/tests/fixtures/circular_cylinder_wake_measurement.yaml:18:  - concern_type: COMPATIBLE_WITH_SILENT_PASS_HAZARD
ui/backend/tests/fixtures/turbulent_flat_plate_measurement.yaml:13:# extraction. The curated COMPATIBLE_WITH_SILENT_PASS_HAZARD concern is
ui/backend/tests/fixtures/turbulent_flat_plate_measurement.yaml:31:  - concern_type: COMPATIBLE_WITH_SILENT_PASS_HAZARD
ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml:67:    concern_type: CONTINUITY_NOT_CONVERGED
ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml:71:    concern_type: RESIDUALS_ABOVE_TARGET
ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml:79:    concern_type: BOUNDING_RECURRENT
ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml:83:    concern_type: NO_RESIDUAL_PROGRESS
ui/backend/tests/fixtures/runs/impinging_jet/real_incident_measurement.yaml:25:  - concern_type: COMPATIBLE_WITH_SILENT_PASS_HAZARD
ui/backend/tests/fixtures/runs/turbulent_flat_plate/real_incident_measurement.yaml:39:  - concern_type: COMPATIBLE_WITH_SILENT_PASS_HAZARD
ui/backend/tests/fixtures/runs/circular_cylinder_wake/real_incident_measurement.yaml:6:# tolerance but is armed as HAZARD because no actual vortex-shedding
ui/backend/tests/fixtures/runs/circular_cylinder_wake/real_incident_measurement.yaml:17:  expected_verdict: HAZARD
ui/backend/tests/fixtures/runs/circular_cylinder_wake/real_incident_measurement.yaml:28:  - concern_type: COMPATIBLE_WITH_SILENT_PASS_HAZARD
ui/backend/tests/fixtures/runs/circular_cylinder_wake/reference_pass_measurement.yaml:8:# HAZARD framing on the real case comes from the canonical-band shortcut
ui/backend/tests/fixtures/runs/circular_cylinder_wake/reference_pass_measurement.yaml:18:    "落在标准窄带里就通过"取巧，再回去看 real_incident run 会看到 HAZARD。
ui/backend/tests/fixtures/runs/lid_driven_cavity/under_resolved_measurement.yaml:18:    结果落在 5% 容差带外——HAZARD/FAIL 都取决于你是否把它当 silent-pass。
ui/backend/tests/fixtures/runs/circular_cylinder_wake/under_resolved_measurement.yaml:14:    但仍在 HAZARD 附近徘徊，教学上演示"临界案例"。
ui/backend/tests/fixtures/runs/differential_heated_cavity/real_incident_measurement.yaml:45:  - concern_type: COMPATIBLE_WITH_SILENT_PASS_HAZARD

exec
/bin/zsh -lc "PYTHONDONTWRITEBYTECODE=1 python3 -c \"from pathlib import Path; from src.convergence_attestor import attest; log=Path('reports/phase5_fields/differential_heated_cavity/20260421T131052Z/log.buoyantSimpleFoam'); res=attest(log); print(res.overall); [print(c.check_id, c.verdict, c.summary) for c in res.checks]\"" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "PYTHONDONTWRITEBYTECODE=1 python3 -c \"from pathlib import Path; from src.convergence_attestor import attest; log=Path('reports/phase5_fields/rayleigh_benard_convection/20260421T142559Z/log.buoyantSimpleFoam'); res=attest(log); print(res.overall); [print(c.check_id, c.verdict, c.summary) for c in res.checks]\"" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
python3: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
python3: error: couldn't create cache file '/tmp/xcrun_db-cpfZ59Ci' (errno=Operation not permitted)
python3: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
python3: error: couldn't create cache file '/tmp/xcrun_db-VDlPoatP' (errno=Operation not permitted)
ATTEST_NOT_APPLICABLE

 succeeded in 0ms:
python3: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
python3: error: couldn't create cache file '/tmp/xcrun_db-86QqIBWP' (errno=Operation not permitted)
python3: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
python3: error: couldn't create cache file '/tmp/xcrun_db-NgVSnCna' (errno=Operation not permitted)
ATTEST_NOT_APPLICABLE

codex
我这边已经形成结论轮廓了，最后补一件元信息：把刚才用到的 memory 片段取精确行号，避免最终报告的 citation 漂移。
exec
/bin/zsh -lc "nl -ba /Users/Zhuanz/.codex/memories/MEMORY.md | sed -n '808,816p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   808	
   809	- the user asked: "用Notion作为我的开发中枢，避免我一直复制每个会话的提示词" -> default toward a reusable Notion-first operating model instead of prompt-copy-heavy sessions [Task 1][Task 2]
   810	- the user repeatedly required isolation: "在不干涉这两个notion项目的前提下" -> keep sibling Notion projects separate unless they explicitly ask for shared databases/relations [Task 1]
   811	- the user asked to integrate GSD and make it "完全自动化的开发，除了需要暂停下来让我定期手动触发Opus 4.6审查" -> automate by default but preserve hard manual review pauses [Task 2]
   812	- for freeze-signoff governance review, the user required a strict independent review with no writes to freeze artifacts -> treat this as review-only until the user explicitly changes scope [Task 3]
   813	- when the user said "你是 independent approval authority… 你不是 corrected request packet 作者… 你不是 Phase 8 executor" -> preserve strict role separation between approval, review, execution, and freeze authority in this repo [Task 4]
   814	- when the user said "如果 approval granted，只能创建一个 executable approval YAML 和一个 approval action report" and "不得运行 populate-formal" -> approval sessions should only produce the allowed artifacts and must not spill into execution [Task 4]
   815	- when the request-package input said the executor "must not write manual intake state" and "must not be valid input to any CLI command" -> default manual-review-intake packaging work to markdown-only, non-mutating deliverables [Task 5]
   816	- when the user said acceptance "must not equal freeze approval" and "cannot directly enter final freeze signoff" -> always restate that `accepted_for_review` is not `freeze-complete`, even when readiness evidence looks strong [Task 3][Task 4]

exec
/bin/zsh -lc "nl -ba /Users/Zhuanz/.codex/memories/MEMORY.md | sed -n '465,478p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   465	# Task Group: cfd-harness-unified governance closeout and planning gates
   466	
   467	scope: Close out accepted phases in `cfd-harness-unified`, normalize Notion-vs-repo naming drift, and keep future phases planning-only until the explicit solver/routing gate is reviewed.
   468	applies_to: cwd=/Users/Zhuanz/Desktop/cfd-harness-unified; reuse_rule=safe for this repo’s Notion-governed phase/gate work, but phase/task IDs and review packets are rollout-specific.
   469	
   470	## Task 1: Close Phase 8 and reconcile stale governance evidence
   471	
   472	### rollout_summary_files
   473	
   474	- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, Phase 8 closeout and evidence normalization)
   475	
   476	### keywords
   477	
   478	- Phase 8, AutoVerifier, 13/13, knowledge/whitelist.yaml, ai_cfd_cold_start_whitelist.yaml, Canonical Docs Type=Report, Phase 8 Done, naming drift

codex
# Codex Review Verdict — DEC-V61-038

**Verdict**: BLOCK  
**Self-pass-rate delta**: claude-estimated=0.65 → codex-independent=0.33

## Findings

### Must-fix (blocker)
- [CA-001] [validation_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/validation_report.py:558) `_derive_contract_status()` only hard-fails on `A1/A4` and ignores `A2/A3/A5/A6` entirely. That means an in-band scalar with `CONTINUITY_NOT_CONVERGED` or `NO_RESIDUAL_PROGRESS` still returns `PASS`, which is not the DEC’s two-tier model. Recommended fix: introduce an explicit HAZARD set for `A2/A3/A5/A6`, then allow per-case promotion to FAIL.
- [CA-002] [phase5_audit_run.py](/Users/Zhuanz/Desktop/cfd-harness-unified/scripts/phase5_audit_run.py:539) and [task_runner.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/task_runner.py:103) do not run the attestor pre-extraction. `TaskRunner.run_task()` already executes solver → comparator → correction before `_audit_fixture_doc()` adds attestation. That violates the “attestor first, then extraction/gates” contract and still allows non-converged runs to flow through scalar extraction/correction generation. Recommended fix: gate the compare/extract path before `comparison_result` is built.
- [CA-003] [convergence_attestor.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/convergence_attestor.py:206) and [comparator_gates.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/comparator_gates.py:134) make A1 log-only. The DEC requires `exit code 0 AND no fatal markers`; current code only parses fatal strings and never consumes `ExecutionResult.success`, even though solver success is derived from container `exit_code == 0` in [foam_agent_adapter.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/foam_agent_adapter.py:6940). It also only matches `^Floating point exception`, not broader `Floating exception` variants. Recommended fix: feed exit/success into A1 and treat either non-zero exit or fatal-tail markers as FAIL.
- [CA-004] [convergence_attestor.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/convergence_attestor.py:24) explicitly says per-case YAML overrides are “not shipped”, and `knowledge/attestor_thresholds.yaml` is absent from the tree and from commits `7f29a64`, `eb51dcf`, and `9716dd4`. That means the DEC’s per-case calibration and “promote HAZARD to FAIL” mechanism do not exist yet. Recommended fix: land the YAML, load it, validate it, and thread it into all A2/A3/A5/A6 decisions.
- [CA-005] [convergence_attestor.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/convergence_attestor.py:272) implements A3/A6 as field-agnostic global-threshold checks. A3 applies one `1e-3` floor to every parsed field, including buoyant `h`/`p_rgh`; A6 scans raw per-field solve lines, not outer-step progress. On the real impinging-jet log [log.buoyantFoam](/Users/Zhuanz/Desktop/cfd-harness-unified/reports/phase5_fields/impinging_jet/20260421T142307Z/log.buoyantFoam:2532), current code produces `A6 HAZARD` on `p_rgh` (`5.91e-01…6.98e-01`, `0.07 decades`), contradicting the DEC’s stated expectation that impinging_jet fails via A4 but not A6. Recommended fix: make A3 per-field/per-case, and make A6 reason over outer-iteration progress semantics rather than every repeated inner solve.

### Should-fix (nit)
- [CA-006] [convergence_attestor.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/convergence_attestor.py:439) uses `< 1.0` decades for “stuck”. Your stated criterion is `<= 1.0`.
- [CA-007] [convergence_attestor.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/convergence_attestor.py:313) filters out blocks with no pressure solve before checking consecutiveness. That means `cap, gap, cap, cap` is treated as 3 consecutive capped blocks, which is stricter than the DEC text.
- [CA-008] [test_convergence_attestor.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_convergence_attestor.py:323) does not implement the DEC’s promised 10-case real-log integration matrix. Real-log coverage is only LDC + BFS, so impinging_jet A4/A6, cylinder A2/A5, and buoyant-case override behavior are not regression-guarded.

## CFD physics audit per check
- **A1**: Partial. `FOAM FATAL IO ERROR` / `FOAM FATAL ERROR` detection is fine, and the `sigFpe` startup-banner false positive is covered. The missing piece is the exit-code half of the contract, plus broader fatal wording variants.
- **A2**: The A2-vs-G5 split is internally reasonable at the attestor layer: `A2=HAZARD`, `G5=FAIL`. Real LDC is safely below threshold (`9.45e-07`, about 106x margin). Real cylinder is `1.52e-01`, so this is not a subtle unsteady-only continuity wobble; G5 still needs to kill it.
- **A3**: The parser does read the final occurrence per field, so this is not an “early iteration” bug. The real defect is calibration: there is no per-field target map, no case override loading, and unknown fields like `h` are treated as if they had the same target as `p/k/omega`.
- **A4**: Good overall. The regex now handles `p` and `p_rgh`, and the `PBiCGStab` ordering fix is correct. Real impinging_jet logs hit A4 exactly as intended. Only the “gap block still counts as consecutive” nit remains.
- **A5**: Acceptable. Windowing is by final `Time =` blocks, not crude EOF line-counting. That matches “last 50 iterations” well enough for these logs. Laminar LDC stays clean; cylinder/BFS recurrent bounding is detected.
- **A6**: Not acceptable yet. The decade math boundary is off, and the measurement unit is wrong for multi-solve outer iterations. Current logic flags impinging_jet as stuck because it sees repeated `p_rgh` inner solves, not true outer-step no-progress.

## Regression guards
- **LDC ATTEST_PASS**: PASS. There is an explicit real-log integration test in [test_convergence_attestor.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_convergence_attestor.py:342). Real margins are comfortably above 2x: final `p` residual is `7.03e-06` vs `1e-3` floor, and final `sum_local` is `9.45e-07` vs `1e-4` floor.
- **Tier-split implementation**: Incorrect. A1/A4 are wired as FAIL, but A2/A3/A5/A6 are not wired as HAZARD at all, and there is no per-case promotion path.
- **Attestor-before-gates ordering**: Partially correct. In [phase5_audit_run.py](/Users/Zhuanz/Desktop/cfd-harness-unified/scripts/phase5_audit_run.py:380), attestor does run before gates and gates still run afterward for diagnostics. But it is not actually before extraction/comparison.

## Backward-compat concerns
- Existing `audit_real_run` fixtures outside LDC do not appear to be backfilled with `attestation`, so current UI/API behavior is only lightly exercised on real hazard/fail cases.
- Once the HAZARD tier is wired into `contract_status`, API/UI snapshots will change for any in-band-but-not-converged case. That is the correct behavior, but it is a compatibility-visible change.
- The current impinging_jet behavior already diverges from the DEC table (`A6` fires today). Fixing tier plumbing without fixing A6 semantics will propagate that misclassification into user-facing status.

## Recommendation
- **Ready for codex_verdict=APPROVED**: NO
- **If NO, required changes**:
1. Move attestation to the execution path before comparator extraction/correction generation.
2. Extend A1 to use both solver exit/success and fatal-log detection.
3. Land and validate `knowledge/attestor_thresholds.yaml`, including per-case overrides and HAZARD→FAIL promotion.
4. Rework A3 as per-field/per-case thresholding instead of one global floor.
5. Rework A6 to measure outer-iteration progress correctly and add an impinging_jet regression so A4 fires without spurious A6.
6. Add validation-report tests proving `A2/A3/A5/A6` yield `HAZARD` contract status, not `PASS`.
7. Add real-log integration tests for the remaining cases, especially impinging_jet, cylinder, DHC, and RBC.

Verification basis: source review, real-log inspection, and read-only `attest()` evaluation on LDC/BFS/cylinder/impinging_jet. I did not run the full pytest suite in this sandbox because temp/cache creation is blocked.


tokens used
214,531
# Codex Review Verdict — DEC-V61-038

**Verdict**: BLOCK  
**Self-pass-rate delta**: claude-estimated=0.65 → codex-independent=0.33

## Findings

### Must-fix (blocker)
- [CA-001] [validation_report.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/validation_report.py:558) `_derive_contract_status()` only hard-fails on `A1/A4` and ignores `A2/A3/A5/A6` entirely. That means an in-band scalar with `CONTINUITY_NOT_CONVERGED` or `NO_RESIDUAL_PROGRESS` still returns `PASS`, which is not the DEC’s two-tier model. Recommended fix: introduce an explicit HAZARD set for `A2/A3/A5/A6`, then allow per-case promotion to FAIL.
- [CA-002] [phase5_audit_run.py](/Users/Zhuanz/Desktop/cfd-harness-unified/scripts/phase5_audit_run.py:539) and [task_runner.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/task_runner.py:103) do not run the attestor pre-extraction. `TaskRunner.run_task()` already executes solver → comparator → correction before `_audit_fixture_doc()` adds attestation. That violates the “attestor first, then extraction/gates” contract and still allows non-converged runs to flow through scalar extraction/correction generation. Recommended fix: gate the compare/extract path before `comparison_result` is built.
- [CA-003] [convergence_attestor.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/convergence_attestor.py:206) and [comparator_gates.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/comparator_gates.py:134) make A1 log-only. The DEC requires `exit code 0 AND no fatal markers`; current code only parses fatal strings and never consumes `ExecutionResult.success`, even though solver success is derived from container `exit_code == 0` in [foam_agent_adapter.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/foam_agent_adapter.py:6940). It also only matches `^Floating point exception`, not broader `Floating exception` variants. Recommended fix: feed exit/success into A1 and treat either non-zero exit or fatal-tail markers as FAIL.
- [CA-004] [convergence_attestor.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/convergence_attestor.py:24) explicitly says per-case YAML overrides are “not shipped”, and `knowledge/attestor_thresholds.yaml` is absent from the tree and from commits `7f29a64`, `eb51dcf`, and `9716dd4`. That means the DEC’s per-case calibration and “promote HAZARD to FAIL” mechanism do not exist yet. Recommended fix: land the YAML, load it, validate it, and thread it into all A2/A3/A5/A6 decisions.
- [CA-005] [convergence_attestor.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/convergence_attestor.py:272) implements A3/A6 as field-agnostic global-threshold checks. A3 applies one `1e-3` floor to every parsed field, including buoyant `h`/`p_rgh`; A6 scans raw per-field solve lines, not outer-step progress. On the real impinging-jet log [log.buoyantFoam](/Users/Zhuanz/Desktop/cfd-harness-unified/reports/phase5_fields/impinging_jet/20260421T142307Z/log.buoyantFoam:2532), current code produces `A6 HAZARD` on `p_rgh` (`5.91e-01…6.98e-01`, `0.07 decades`), contradicting the DEC’s stated expectation that impinging_jet fails via A4 but not A6. Recommended fix: make A3 per-field/per-case, and make A6 reason over outer-iteration progress semantics rather than every repeated inner solve.

### Should-fix (nit)
- [CA-006] [convergence_attestor.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/convergence_attestor.py:439) uses `< 1.0` decades for “stuck”. Your stated criterion is `<= 1.0`.
- [CA-007] [convergence_attestor.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/convergence_attestor.py:313) filters out blocks with no pressure solve before checking consecutiveness. That means `cap, gap, cap, cap` is treated as 3 consecutive capped blocks, which is stricter than the DEC text.
- [CA-008] [test_convergence_attestor.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_convergence_attestor.py:323) does not implement the DEC’s promised 10-case real-log integration matrix. Real-log coverage is only LDC + BFS, so impinging_jet A4/A6, cylinder A2/A5, and buoyant-case override behavior are not regression-guarded.

## CFD physics audit per check
- **A1**: Partial. `FOAM FATAL IO ERROR` / `FOAM FATAL ERROR` detection is fine, and the `sigFpe` startup-banner false positive is covered. The missing piece is the exit-code half of the contract, plus broader fatal wording variants.
- **A2**: The A2-vs-G5 split is internally reasonable at the attestor layer: `A2=HAZARD`, `G5=FAIL`. Real LDC is safely below threshold (`9.45e-07`, about 106x margin). Real cylinder is `1.52e-01`, so this is not a subtle unsteady-only continuity wobble; G5 still needs to kill it.
- **A3**: The parser does read the final occurrence per field, so this is not an “early iteration” bug. The real defect is calibration: there is no per-field target map, no case override loading, and unknown fields like `h` are treated as if they had the same target as `p/k/omega`.
- **A4**: Good overall. The regex now handles `p` and `p_rgh`, and the `PBiCGStab` ordering fix is correct. Real impinging_jet logs hit A4 exactly as intended. Only the “gap block still counts as consecutive” nit remains.
- **A5**: Acceptable. Windowing is by final `Time =` blocks, not crude EOF line-counting. That matches “last 50 iterations” well enough for these logs. Laminar LDC stays clean; cylinder/BFS recurrent bounding is detected.
- **A6**: Not acceptable yet. The decade math boundary is off, and the measurement unit is wrong for multi-solve outer iterations. Current logic flags impinging_jet as stuck because it sees repeated `p_rgh` inner solves, not true outer-step no-progress.

## Regression guards
- **LDC ATTEST_PASS**: PASS. There is an explicit real-log integration test in [test_convergence_attestor.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_convergence_attestor.py:342). Real margins are comfortably above 2x: final `p` residual is `7.03e-06` vs `1e-3` floor, and final `sum_local` is `9.45e-07` vs `1e-4` floor.
- **Tier-split implementation**: Incorrect. A1/A4 are wired as FAIL, but A2/A3/A5/A6 are not wired as HAZARD at all, and there is no per-case promotion path.
- **Attestor-before-gates ordering**: Partially correct. In [phase5_audit_run.py](/Users/Zhuanz/Desktop/cfd-harness-unified/scripts/phase5_audit_run.py:380), attestor does run before gates and gates still run afterward for diagnostics. But it is not actually before extraction/comparison.

## Backward-compat concerns
- Existing `audit_real_run` fixtures outside LDC do not appear to be backfilled with `attestation`, so current UI/API behavior is only lightly exercised on real hazard/fail cases.
- Once the HAZARD tier is wired into `contract_status`, API/UI snapshots will change for any in-band-but-not-converged case. That is the correct behavior, but it is a compatibility-visible change.
- The current impinging_jet behavior already diverges from the DEC table (`A6` fires today). Fixing tier plumbing without fixing A6 semantics will propagate that misclassification into user-facing status.

## Recommendation
- **Ready for codex_verdict=APPROVED**: NO
- **If NO, required changes**:
1. Move attestation to the execution path before comparator extraction/correction generation.
2. Extend A1 to use both solver exit/success and fatal-log detection.
3. Land and validate `knowledge/attestor_thresholds.yaml`, including per-case overrides and HAZARD→FAIL promotion.
4. Rework A3 as per-field/per-case thresholding instead of one global floor.
5. Rework A6 to measure outer-iteration progress correctly and add an impinging_jet regression so A4 fires without spurious A6.
6. Add validation-report tests proving `A2/A3/A5/A6` yield `HAZARD` contract status, not `PASS`.
7. Add real-log integration tests for the remaining cases, especially impinging_jet, cylinder, DHC, and RBC.

Verification basis: source review, real-log inspection, and read-only `attest()` evaluation on LDC/BFS/cylinder/impinging_jet. I did not run the full pytest suite in this sandbox because temp/cache creation is blocked.


