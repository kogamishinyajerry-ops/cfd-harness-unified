# Codex Round 1 Review · DEC-V61-058 Stage A + B1 + B2

**Run:** 2026-04-25 · gpt-5.4 · cx-auto ramaiamandhabdbs@gmail.com (94% quota)
**Reviewing:** Cumulative branch state at commit 49395cf (Stage 0 v1+v2 + Batch A1+A2 + Batch B1.1/B1.2/B1.3 + Batch B2)
**Verdict:** `CHANGES_REQUIRED`
**Tokens used:** 235,593

## Summary

Codex independently ran:
- TestNACA0012MultiDim 25/25 passed (Python 3.12 via uv run)
- test_contract_dashboard_report 7/7 passed
- import-linter 5/5 contracts KEPT
- py_compile clean (Python 3.12)
- Reproduced F1 statefulness bug via in-process repro of `_generate_airfoil_flow`
  with a TaskSpec reused across two calls + alias change

## Findings

| ID | Severity | File:Line | Required edit | Status |
|---|---|---|---|---|
| F1 | High BLOCKING | src/foam_agent_adapter.py:6440-6462 | Stop persisting bc["alpha_deg"]; reverse precedence (angle_of_attack first); add reuse regression | LANDED commit a00ff88 |
| F2 | Medium | src/airfoil_extractors.py:228, :409 | Add math.isfinite() guards in compute_cl_cd + compute_y_plus_max; add NaN/inf tests | LANDED commit 641cf9f |
| C1 | Comment-only | knowledge/gold_standards/naca0012_airfoil.yaml:61 | Refresh stale physics_contract wording (says α-routing not implemented; B1 implemented it) | LANDED commit a2b1d63 |
| C2 | Comment-only | src/airfoil_extractors.py:287 | Add linearity_check_applicable flag for 2-point case (deferred to before Stage C) | DEFERRED |
| C3 | Comment-only | src/foam_agent_adapter.py:6839 | yPlus comment should mention `patch` column explicitly | LANDED commit a00ff88 |

## Per-question highlights (full responses below)

- Q1: precedence acceptable shape, but mutation interaction was the blocking bug. Reuse coverage was the missing test. (BLOCKING)
- Q2: forceCoeffs sign convention, pitchAxis, CofR, write cadence all CORRECT.
- Q3: yPlus FO config sufficient (no `patches` field exists in surface).
- Q4: parser reuse the right tradeoff; endpoint-delta drift is weak proxy (acceptable placeholder, replace before Stage C); 2-pt linearity_ok semantics misleading.
- Q5: gaps were F1 reuse + F2 NaN/inf tests (now closed).
- Q6: theoretical SNR table sufficient for round 1 (live measurement is Stage E).
- Q7: schema OK; PARTIALLY_COMPATIBLE bucket choice correct; stale narrative needed refresh.
- Q8: F1 + F2 + stale wording = required before Batch C/D/E. ALL LANDED.

**Recommended round-2 pass rate**: 0.70 (Codex post-edits estimate).

---

## Codex output (curated, verbatim from log)

1. **Verdict**: APPROVE / APPROVE_WITH_COMMENTS / CHANGES_REQUIRED
2. **Findings table**: ID | Severity | File:Line | Required edit | Rationale
3. **Per-question response** Q1-Q8
4. **Recommended pass-rate adjustment** for round 2 (if any)
5. **Blocking vs non-blocking findings** (CHANGES_REQUIRED needs ≥1 blocking)

Cite specific file:line. No speculation — if you don't know, say "needs
Stage E live-run" or similar.

codex
Reviewing the branch diff against `origin/main` with a code-review pass first. I’m loading the review workflow guidance, then I’ll inspect the touched files and tests before answering Q1-Q8 with line-cited verdicts.
exec
/bin/zsh -lc "sed -n '1,260p' /Users/Zhuanz/.agents/skills/gsd-code-review/SKILL.md" in /Users/Zhuanz/Desktop/cfd-s2-naca
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
/bin/zsh -lc "sed -n '1,220p' /Users/Zhuanz/.codex/plugins/cache/openai-curated/superpowers/421657af0e7e94573f3a5f2c51091df43668da94/skills/using-superpowers/SKILL.md" in /Users/Zhuanz/Desktop/cfd-s2-naca
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
/bin/zsh -lc 'git log --oneline --decorate -7' in /Users/Zhuanz/Desktop/cfd-s2-naca
 succeeded in 0ms:
49395cf (HEAD -> dec-v61-058-naca, origin/dec-v61-058-naca) B2(naca0012): src/airfoil_extractors.py + TestNACA0012MultiDim [line-b]
032623b B1.2+B1.3(naca0012): forceCoeffs + yPlus FOs on aerofoil patch [line-b]
5bbda96 B1.1(naca0012): α-routing in 0/U via task_spec.boundary_conditions [line-b]
5a80e4d A2(naca0012): expand CaseProfile to 5 registered risk_flags [line-b]
a889657 A1(naca0012): rewrite gold YAML — Ladson 1988 + Abbott + Gregory provenance [line-b]
