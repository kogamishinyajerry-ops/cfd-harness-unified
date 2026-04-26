2026-04-26T02:05:33.502948Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-research-deerflow/SKILL.md: missing YAML frontmatter delimited by ---
2026-04-26T02:05:33.502966Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-report-pretext/SKILL.md: missing YAML frontmatter delimited by ---
Reading additional input from stdin...
OpenAI Codex v0.118.0 (research preview)
--------
workdir: /Users/Zhuanz/Desktop/cfd-s4-rbc
model: gpt-5.4
provider: openai
approval: never
sandbox: danger-full-access
reasoning effort: xhigh
reasoning summaries: none
session id: 019dc788-efbf-7e70-897c-27273ad08f04
--------
user
You are reviewing **DEC-V61-067 Stage 0 intake v2** for axisymmetric_impinging_jet.
Branch `dec-v61-067-impinging-jet`, commit 46f0075.

CONTEXT: this is R2 verify of v2 intake after R1 returned REQUEST_CHANGES with
3 findings (1 HIGH + 1 MED + 1 LOW). All findings claimed to be closed verbatim.

R1 findings (now must verify closure):
- F1-HIGH (citation_audit closure too loose):
  - Whitelist DOI 10.1016/j.ijheatfluidflow.2013.03.003 verified to resolve to
    a turbine-LES paper (NOT impinging jet)
  - Cooper et al. 1993 = HYDRODYNAMIC dataset (Part I), should NOT be primary
    thermal anchor
  - Heat transfer anchor: Baughn & Shimizu 1989 (10.1115/1.3250776)
  - "Behnad 2013" likely corruption of Behnia et al. 1998/1999
    (10.1016/S0017-9310(97)00254-8 + 10.1016/S0142-727X(98)10040-1)
  - Edit: rewrite §3 with priority-ordered DOI chain, distinguish thermal
    anchor from hydrodynamic support
- F2-MED (taxonomy internal inconsistency):
  - Keep Type II
  - Change primary_gate_count: 2 → 1
  - Add profile_qualitative_gate_count: 2
  - Add headline_gate / case_type_hard_gate_signed fields
  - Add second distinct shape gate (secondary_peak_presence_or_absence)
  - Add early Stage A.0a batch in §6
  - Lower estimated_pass_rate_round1 to 0.25-0.30
- F3-LOW (risk register completeness):
  - Add nusselt_number_unphysical_magnitude HAZARD risk (line 9717)
  - Add constant-T plate vs uniform-q BC mismatch (line 6204)
  - Add pseudo-2D slab vs cyclic AMI/wedge (line 5632)
  - §7 acceptance criteria: exact DOI+locator + station set + tolerance mode +
    hazard-flag-absent verifiable

REVIEW SCOPE:
1. Verify all 3 R1 findings are closed verbatim (not just acknowledged).
2. Spot-check no new issues introduced by the v2 edits:
   - Internal consistency (gate counts add up)
   - §6 stage_preview matches §1 + §3 + §7
   - §4 risk register R6/R7/R8 each have a mitigation pointing to a §7 criterion
3. Final verdict for proceeding to Stage A.0a:
   APPROVE_PLAN / APPROVE_PLAN_WITH_CHANGES / REQUEST_CHANGES

Files to read:
- .planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml (commit 46f0075)
- reports/codex_tool_reports/dec_v61_067_plan_review_v1.md (the R1 review)

OUTPUT: Under 500 words. Just verify closure. Don't re-do the whole audit.
codex
Reviewing the Stage 0 intake against the exact `46f0075` artifact and the R1 report first. I’ll verify each claimed closure in the YAML, then do the requested consistency spot-checks before issuing a verdict.
exec
/bin/zsh -lc "sed -n '1,220p' /Users/Zhuanz/.codex/plugins/cache/openai-curated/superpowers/421657af0e7e94573f3a5f2c51091df43668da94/skills/using-superpowers/SKILL.md" in /Users/Zhuanz/Desktop/cfd-s4-rbc
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
/bin/zsh -lc "sed -n '1,260p' reports/codex_tool_reports/dec_v61_067_plan_review_v1.md" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
2026-04-26T01:49:15.363827Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-research-deerflow/SKILL.md: missing YAML frontmatter delimited by ---
2026-04-26T01:49:15.363849Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-report-pretext/SKILL.md: missing YAML frontmatter delimited by ---
Reading additional input from stdin...
OpenAI Codex v0.118.0 (research preview)
--------
workdir: /Users/Zhuanz/Desktop/cfd-s4-rbc
model: gpt-5.4
provider: openai
approval: never
sandbox: danger-full-access
reasoning effort: xhigh
reasoning summaries: none
session id: 019dc77a-02e4-75e3-bb45-c7b5f7bbc77b
--------
user
You are reviewing **DEC-V61-067 Stage 0 intake** for axisymmetric_impinging_jet
(8th case in 10-case whitelist, methodology v2.0 sixth-apply). Branch
`dec-v61-067-impinging-jet`, commit 9a85b18.

CONTEXT — methodology v2.0 precedents:
- V61-053 cylinder (Type I PASS), V61-057 DHC (Type I PASS),
  V61-058 NACA (Type II PASS), V61-060 RBC (Type II FAIL physics-bound),
  V61-063 flat_plate (Type II FAIL physics-fidelity-gap),
  V61-066 duct_flow (Type II FAIL physics-fidelity-gap)
- Pattern: pre-Stage-A intake review catches citation/scope errors BEFORE
  any code is written. V61-060 needed 4 intake rounds; V61-058 needed 2.

KEY PRE-EXISTING STATE (read these first):
1. .planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml — the intake
   to review. Read §0 preexisting_state_honesty + §3 citation_audit FIRST.
2. knowledge/gold_standards/axisymmetric_impinging_jet.yaml — the broken
   gold YAML this intake aims to fix (contract_status =
   INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE)
3. knowledge/whitelist.yaml — search "impinging_jet" entry; note the
   "Cooper et al. 1984 / Behnad et al. 2013" citation that the intake §3
   flags as suspect
4. src/foam_agent_adapter.py lines 670-695 (dispatch) and 9613-9721
   (_extract_jet_nusselt — DEC-V61-042 3-pt stencil already in place)

REVIEW SCOPE:
1. **§3 citation_audit (BLOCKING)** — is the audit framing correct? Is
   "Cooper et al. 1984" likely a corruption of Cooper/Jackson/Launder/Liao
   1993 OR Cooper 1973 (orig CHAM TR/76 report)? Should the intake list
   specific resolveable DOIs the executor MUST try at Stage A.0?
2. **§1 case_type = II classification** — is 1 HARD_GATED stagnation +
   1 HARD_GATED profile + 1 NON_TYPE_HARD_INVARIANT + 1 PROVISIONAL the
   right taxonomy? Should the profile gate be split into multiple per-station
   gates (Type I)?
3. **§4 risk register completeness** — is anything missing? E.g.:
   - DEC-V61-042 round-1 HAZARD: nusselt_number_unphysical_magnitude flag
     (Nu > 500). Should V61-067 surface this in risk register?
   - Free-jet vs confined-jet ambiguity (Cooper 1993 was confined; whitelist
     doesn't say which)
   - Axisymmetric mesh assumption (cyclic AMI vs full 3D wedge — adapter
     emits which?)
4. **§6 stage_preview** — is the Stage A.0 → E sequence well-scoped? Are
   there missing intermediate batches?
5. **estimated_pass_rate_round1 = 0.40** — is this realistic given the
   citation audit risk? Higher or lower?
6. **§7 acceptance_criteria** — are these unambiguous and verifiable?

OUTPUT: structured findings (F1=HIGH, F2=MED, F3=LOW) with specific section
references and concrete edit suggestions. APPROVE_PLAN / APPROVE_PLAN_WITH_CHANGES /
REQUEST_CHANGES verdict. Under 600 words.
codex
Reviewing the Stage 0 intake as a read-only acceptance pass. I’m loading the cited intake, gold standard, whitelist entry, and adapter extraction path first, then I’ll check the literature side where the intake’s citation audit is making claims.
exec
/bin/zsh -lc "rg -n \"DEC-V61-067|axisymmetric_impinging_jet|impinging_jet|Cooper et al\\. 1984|Behnad et al\\. 2013\" /Users/Zhuanz/.codex/memories/MEMORY.md" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 exited 1 in 0ms:
exec
/bin/zsh -lc "sed -n '1,220p' /Users/Zhuanz/.codex/plugins/cache/openai-curated/superpowers/421657af0e7e94573f3a5f2c51091df43668da94/skills/using-superpowers/SKILL.md" in /Users/Zhuanz/Desktop/cfd-s4-rbc
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
/bin/zsh -lc 'git rev-parse --show-toplevel && git status --short && git branch --show-current && git rev-parse HEAD' in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
/Users/Zhuanz/Desktop/cfd-s4-rbc
 M reports/codex_tool_reports/dec_v61_067_plan_review_v1.md
dec-v61-067-impinging-jet
cca8117f265d95f860fa98d07c1881879202f796

codex
I found the working tree isn’t exactly at the requested snapshot: current `dec-v61-067-impinging-jet` head is `cca8117`, with a local modification under `reports/`. I’m switching the review to commit-addressed reads from `9a85b18` so the verdict stays pinned to the intake version you named.
exec
/bin/zsh -lc "sed -n '1,220p' /Users/Zhuanz/.agents/skills/gsd-code-review/SKILL.md" in /Users/Zhuanz/Desktop/cfd-s4-rbc
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
/bin/zsh -lc 'pwd && git branch --show-current && git rev-parse --short HEAD && git status --short' in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
/Users/Zhuanz/Desktop/cfd-s4-rbc
dec-v61-067-impinging-jet
46f0075
?? reports/codex_tool_reports/dec_v61_067_plan_review_v2.md

codex
Using `using-superpowers` as the required process guard, then doing a strict read-only review against the pinned commit. I’ve confirmed the branch/commit match; next I’m locating the exact v2 edits for the three R1 findings and the stage/risk consistency checks.
exec
/bin/zsh -lc "git show 46f0075:.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml | nl -ba | sed -n '1,260p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
exec
/bin/zsh -lc "git show 46f0075:.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml | nl -ba | rg -n \"citation_audit|case_type|primary_gate_count|profile_qualitative_gate_count|headline_gate|case_type_hard_gate_signed|secondary_peak_presence_or_absence|estimated_pass_rate_round1|stage_preview|risk_register|R6|R7|R8|acceptance_criteria|A.0a|Baughn|Behnia|Cooper|10\\.1115/1\\.3250776|10\\.1016/S0017-9310\\(97\\)00254-8|10\\.1016/S0142-727X\\(98\\)10040-1|10\\.1016/j\\.ijheatfluidflow\\.2013\\.03\\.003|hazard|pseudo-2D|constant-T|uniform-q|nusselt_number_unphysical_magnitude|station set|tolerance mode\"" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
15:    15	#         F1-HIGH (citation_audit closure too loose): rewrite §3 with
19:    19	#                  Codex Crossref query. Cooper et al. 1993 demoted to
20:    20	#                  hydrodynamic-only. Baughn & Shimizu 1989
21:    21	#                  (10.1115/1.3250776) promoted to primary thermal anchor
22:    22	#                  candidate. Behnia et al. 1998/1999
23:    23	#                  (10.1016/S0017-9310(97)00254-8 +
24:    24	#                  10.1016/S0142-727X(98)10040-1) identified as the likely
27:    27	#                  primary_gate_count: 2 → 1; add profile_qualitative_gate_count: 2;
28:    28	#                  add headline_gate + case_type_hard_gate_signed fields per
31:    31	#                  (secondary_peak_presence_or_absence) so qualitative
32:    32	#                  count = 2 cleanly. Add early Stage A.0a batch in §6 to
34:    34	#                  family BEFORE extractor work. estimated_pass_rate_round1
37:    37	#                  R6 nusselt_number_unphysical_magnitude HAZARD flag exists
38:    38	#                  in extractor (foam_agent_adapter.py:9717); R7 plate BC is
41:    41	#                  per foam_agent_adapter.py:6204; R8 mesh is pseudo-2D slab
44:    44	#                  approximation that may not match Cooper's true axisymmetric
45:    45	#                  3D measurement. §7 acceptance_criteria tightened with
46:    46	#                  exact DOI+locator + station set + tolerance mode +
47:    47	#                  hazard-flag-absent verifiable criterion.
85:    85	    1. Citation re-anchor the gold YAML to the actual Cooper et al. 1993
86:    86	       impinging-jet measurement (NOT Cooper 1984 — see §3 Cooper-citation
87:    87	       audit; the whitelist's "Cooper et al. 1984" label is itself suspect)
88:    88	       OR a publicly-archived equivalent (Behnad et al. 2013 OR Baughn &
94:    94	       deliver Nu_stagnation in the Cooper-correlation band (likely needs
104:   104	case_type: II  # v2 (per Codex F2): keep Type II — stations are ONE profile
109:   109	               # profile_qualitative_gate_count = 2 cleanly (mirrors
111:   111	               # shape gate (secondary_peak_presence_or_absence) replaces
113:   113	case_type_rationale: |
118:   118	       Reference value pending §3 citation audit (will be either Baughn
119:   119	       & Shimizu 1989 thermal anchor OR Behnia et al. 1998 RANS-validation
120:   120	       value, NOT Cooper 1993 which is hydrodynamic-only).
130:   130	    3. secondary_peak_presence_or_absence — QUALITATIVE_GATE — the canonical
132:   132	       r/D ≈ 2 caused by transition-to-turbulence in the wall jet (Cooper
133:   133	       1993 + Baughn & Shimizu 1989 both report this for Re ≥ ~20000).
159:   159	primary_gate_count: 1               # v2 (per Codex F2): only the headline
163:   163	profile_qualitative_gate_count: 2   # v2: nusselt_profile_r_over_d +
164:   164	                                    # secondary_peak_presence_or_absence
165:   165	case_type_hard_gate_signed: 1       # v2 (per Codex F2 + V61-058 template):
168:   168	                                    # denominator. Equals primary_gate_count
177:   177	headline_gate: nusselt_stagnation_at_r_d_zero  # v2 per V61-058 template:
189:   189	citation_audit:
191:   191	    label: "Cooper et al. 1984 / Behnad et al. 2013"
192:   192	    doi: "10.1016/j.ijheatfluidflow.2013.03.003"
199:   199	      Whitelist label "Cooper 1984" does not match any well-known
200:   200	      impinging-jet author/date. Whitelist DOI 10.1016/j.ijheatfluidflow.2013.03.003
203:   203	      corruption of "Behnia 1998/1999".
211:   211	      authors: "Baughn, J.W., Shimizu, S."
215:   215	      doi: "10.1115/1.3250776"
227:   227	        (a) Try DOI 10.1115/1.3250776; verify resolves to the right paper.
238:   238	      authors: "Behnia, M., Parneix, S., Durbin, P.A."
242:   242	      doi: "10.1016/S0017-9310(97)00254-8"
246:   246	        model and validates against Baughn 1989 + Yan 1991. Useful as
251:   251	        Try if Baughn 1989 is paywalled or unavailable. Use Behnia 1998
252:   252	        only if (a) it includes a Re=10000 row OR (b) the Behnia/Baughn
257:   257	      authors: "Behnia, M., Parneix, S., Shabany, Y., Durbin, P.A."
261:   261	      doi: "10.1016/S0142-727X(98)10040-1"
269:   269	      authors: "Cooper, D., Jackson, D.C., Launder, B.E., Liao, G.X."
275:   275	        v2 per Codex F1: Cooper 1993 PART I is HYDRODYNAMIC ONLY (mean
276:   276	        velocity + Reynolds stresses). Heat transfer is in Part II (Cooper
277:   277	        et al. 1993 companion paper, different DOI). v1 listed Cooper 1993
278:   278	        as interchangeable with Baughn 1989 — that conflated flow-field
279:   279	        and heat-transfer datasets. Cooper 1993 Part I is reusable for
297:   297	    updated; if BC mismatch present (constant-T vs uniform-q), it MUST
303:   303	risk_register:
307:   307	      Whitelist Re=10000 is unusual for impinging-jet benchmarks. Cooper
313:   313	      (a) Verify Cooper 1993 has a Re=10000 row, OR
320:   320	      Whitelist h/d=2 is a common stand-off. Cooper 1993 and Baughn/Shimizu
365:   365	  R6_unphysical_magnitude_hazard_flag_exists:
369:   369	      `nusselt_number_unphysical_magnitude=True` when extracted Nu_stag
378:   378	      §7 acceptance criterion v explicitly requires "hazard flag absent
381:   381	  R7_plate_bc_constant_temperature_vs_uniform_heat_flux:
387:   387	      Many literature impinging-jet correlations (Baughn & Shimizu 1989
391:   391	      uniform-q yields a DIFFERENT Nu(r/D) profile than constant-T.
392:   392	      If §3 lands Baughn 1989 as primary anchor, this BC mismatch is a
403:   403	  R8_pseudo_2d_slab_geometry_vs_true_axisymmetric:
406:   406	      Adapter at foam_agent_adapter.py:5632-5687 emits a pseudo-2D slab
413:   413	      2D slab, NOT an axisymmetric solve. Cooper-style correlations
426:   426	      the plate) WILL differ. §1 gates 1+2+3 are all LOCAL, so R8
433:   433	codex_budget_rounds: 5  # R5 normal checkpoint, R6 halt-risk, R7 force abandon
434:   434	estimated_pass_rate_round1: 0.28  # v2 per Codex F2: lowered 0.40 → 0.28 (midpoint
448:   448	stage_preview:
449:   449	  # v2 (per Codex F2): Stage A.0 split into A.0a (citation+context audit)
450:   450	  # and A.0b (gold YAML rewrite). A.0a MUST close all four entangled
455:   455	  A_0a_pre_pivot_context_audit:
465:   465	        (4) Wall-BC family — confirm constant-T (Dirichlet) vs uniform-q
466:   466	            (Neumann); §4 R7 risk crystallises here.
477:   477	      Apply the A.0a decisions to the gold YAML and whitelist atomically.
482:   482	        documents any A.0a-surfaced mismatches per V61-060 honesty pattern)
505:   505	        from §4 risk_register (R1, R2, R3, R5)
528:   528	acceptance_criteria:
535:   535	    (relative tolerance) of the gold ref_value resolved at A.0a — primary
537:   537	    physics-fidelity gap explicitly with R7 BC-mismatch and/or R1 Re-mismatch
541:   541	    v2 per Codex F3: tighten "matches Cooper-style" to verifiable form:
546:   546	        A.0a from explicit Table/Figure locator (NOT a generic "Cooper-style"
549:   549	      - if A.0a anchor lacks one or more stations, explicitly mark them
552:   552	    v2 per Codex F2: gate #3 (secondary_peak_presence_or_absence) PASS:
562:   562	  vi_unphysical_magnitude_hazard_flag_absent: |
564:   564	    `nusselt_number_unphysical_magnitude=False` (or unset). If the flag
569:   569	    v2 per Codex F3 + R7: the chosen gold ref's wall BC family
570:   570	    (constant-T vs uniform-q) MUST appear in
575:   575	    v2 per Codex F3 + R8: the gold YAML §physics_contract.note MUST
576:   576	    acknowledge that the adapter emits a pseudo-2D Cartesian r-z slab

 succeeded in 0ms:
     1	# Stage 0 · Case Intake Assessment · DEC-V61-067 · axisymmetric_impinging_jet
     2	# Mandated by methodology v2.0 F1-M1 hard gate before Stage A.
     3	# Track B sixth-apply (precedents: V61-053 cylinder, V61-057 DHC, V61-058 NACA,
     4	# V61-060 RBC, V61-063 flat_plate, V61-066 duct_flow). Other in-flight sessions:
     5	# V61-059 plane_channel (PR #41 OPEN); V61-060 RBC (PR #43 OPEN).
     6	#
     7	# Revision history:
     8	#   v1 (2026-04-26): initial Stage 0 draft.
     9	#       authored by Claude Code Opus 4.7 1M.
    10	#   v2 (2026-04-26): Codex pre-Stage-A R1 returned REQUEST_CHANGES with
    11	#       1 HIGH + 1 MED + 1 LOW. All findings applied verbatim.
    12	#       Codex log: reports/codex_tool_reports/dec_v61_067_plan_review_v1.md
    13	#
    14	#       v1 → v2 edit summary:
    15	#         F1-HIGH (citation_audit closure too loose): rewrite §3 with
    16	#                  priority-ordered DOI list, distinguish THERMAL gold anchor
    17	#                  from HYDRODYNAMIC support. Whitelist DOI verified to
    18	#                  resolve to a turbine-LES paper (NOT impinging jet) per
    19	#                  Codex Crossref query. Cooper et al. 1993 demoted to
    20	#                  hydrodynamic-only. Baughn & Shimizu 1989
    21	#                  (10.1115/1.3250776) promoted to primary thermal anchor
    22	#                  candidate. Behnia et al. 1998/1999
    23	#                  (10.1016/S0017-9310(97)00254-8 +
    24	#                  10.1016/S0142-727X(98)10040-1) identified as the likely
    25	#                  "Behnad 2013" corruption.
    26	#         F2-MED (taxonomy internal inconsistency): keep Type II but fix
    27	#                  primary_gate_count: 2 → 1; add profile_qualitative_gate_count: 2;
    28	#                  add headline_gate + case_type_hard_gate_signed fields per
    29	#                  V61-058 template. Stations are ONE profile family, NOT
    30	#                  independent. Add a distinct second shape gate
    31	#                  (secondary_peak_presence_or_absence) so qualitative
    32	#                  count = 2 cleanly. Add early Stage A.0a batch in §6 to
    33	#                  resolve citation + free/confined + Re/H/D + wall-BC
    34	#                  family BEFORE extractor work. estimated_pass_rate_round1
    35	#                  lowered 0.40 → 0.28 (midpoint of Codex 0.25-0.30 band).
    36	#         F3-LOW (risk register completeness): add 3 risks visible in code:
    37	#                  R6 nusselt_number_unphysical_magnitude HAZARD flag exists
    38	#                  in extractor (foam_agent_adapter.py:9717); R7 plate BC is
    39	#                  fixedValue T_plate (constant-temperature, NOT uniform
    40	#                  heat flux — many literature correlations use the latter)
    41	#                  per foam_agent_adapter.py:6204; R8 mesh is pseudo-2D slab
    42	#                  with `empty` patches (NOT cyclic AMI / wedge / 3D)
    43	#                  per foam_agent_adapter.py:5632 — this is a wedge-like
    44	#                  approximation that may not match Cooper's true axisymmetric
    45	#                  3D measurement. §7 acceptance_criteria tightened with
    46	#                  exact DOI+locator + station set + tolerance mode +
    47	#                  hazard-flag-absent verifiable criterion.
    48	
    49	case_id: axisymmetric_impinging_jet
    50	dec_id: DEC-V61-067
    51	case_number: 8  # canonical 8th case in the 10-case whitelist (impinging_jet)
    52	intake_authored_at: "2026-04-26"
    53	intake_author: "Claude Code (Opus 4.7, 1M context · Track B sixth-apply)"
    54	methodology_version: "v2.0"
    55	intake_version: 2
    56	codex_plan_review_verdict: REQUEST_CHANGES_v1_then_REWRITTEN_v2  # final pending Codex R2
    57	
    58	# ============================================================================
    59	# §0 Why this case is being re-iterated (pre-existing state honesty)
    60	# ============================================================================
    61	preexisting_state_honesty: |
    62	  The current `knowledge/gold_standards/axisymmetric_impinging_jet.yaml` carries
    63	  a self-confessed broken contract:
    64	
    65	    contract_status: "INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE
    66	       — the observable is called nusselt_number but stores a cf_skin_friction
    67	       value (0.0042). No solver change is required to PASS, and no solver
    68	       change will make it agree with the literature Nu=25 either without a
    69	       different thermal setup."
    70	
    71	  The note: field still claims "simpleFoam isothermal run; cf_skin_friction
    72	  extracted (Nu=0.0042 is Cf, not Nu)", but the adapter dispatch path was
    73	  upgraded post-EX-1-005 (2026-04-18): `_generate_impinging_jet` now writes
    74	  a buoyantFoam-path case (src/foam_agent_adapter.py:674-676), AND
    75	  `_extract_jet_nusselt` (src/foam_agent_adapter.py:9613-9721) computes a
    76	  TRUE wall-normal temperature gradient via the 3-point one-sided stencil
    77	  (DEC-V61-042 fix), returning Nu_stagnation + Nu(r/D) profile + r-coords.
    78	
    79	  In other words: the EXTRACTOR is correct, but the GOLD YAML still encodes
    80	  the stale Cf=0.0042 sentinel from before DEC-V61-042 landed. The current
    81	  "PASS" verdict is therefore meaningless self-comparison — the comparator
    82	  matches a number against itself, not against literature physics.
    83	
    84	  V61-067 will:
    85	    1. Citation re-anchor the gold YAML to the actual Cooper et al. 1993
    86	       impinging-jet measurement (NOT Cooper 1984 — see §3 Cooper-citation
    87	       audit; the whitelist's "Cooper et al. 1984" label is itself suspect)
    88	       OR a publicly-archived equivalent (Behnad et al. 2013 OR Baughn &
    89	       Shimizu 1989, both publicly accessible per JFE-style archives).
    90	    2. Promote the existing Nu(r/D) profile output to a Type II observable
    91	       family (one HARD_GATED stagnation Nu + one HARD_GATED profile shape
    92	       gate + ≥1 conservation invariant + ≥1 advisory).
    93	    3. Verify that the buoyantFoam dispatch + wall-gradient stencil actually
    94	       deliver Nu_stagnation in the Cooper-correlation band (likely needs
    95	       a Re mismatch audit: whitelist sets Re=10000, but most published
    96	       impinging-jet correlations use Re=23000 or higher).
    97	    4. Document the Re/h-over-d/Pr mismatches honestly in the gold YAML
    98	       §physics_contract.note like V61-060 did for the Pandey & Schumacher
    99	       benchmark.
   100	
   101	# ============================================================================
   102	# §1 Classification (F5-M1 hard gate, §3b — NO mid-arc Type change allowed)
   103	# ============================================================================
   104	case_type: II  # v2 (per Codex F2): keep Type II — stations are ONE profile
   105	               # family, NOT independent physics families. 1 PRIMARY SCALAR
   106	               # + 2 PROFILE_QUALITATIVE_GATES + 1 PROVISIONAL_ADVISORY.
   107	               # The monotonicity check is RELABELED from
   108	               # NON_TYPE_HARD_INVARIANT to QUALITATIVE_GATE so the
   109	               # profile_qualitative_gate_count = 2 cleanly (mirrors
   110	               # V61-058's qualitative-gate accounting). A second distinct
   111	               # shape gate (secondary_peak_presence_or_absence) replaces
   112	               # the prior over-count of "the profile" as 2 separate gates.
   113	case_type_rationale: |
   114	  PRIMARY SCALAR GATE (1):
   115	    1. nusselt_stagnation_at_r_d_zero — HEADLINE — Nu at the radial bin
   116	       closest to r=0 (axisymmetric stagnation point), extracted by the
   117	       existing `_extract_jet_nusselt` 3-point wall-normal stencil.
   118	       Reference value pending §3 citation audit (will be either Baughn
   119	       & Shimizu 1989 thermal anchor OR Behnia et al. 1998 RANS-validation
   120	       value, NOT Cooper 1993 which is hydrodynamic-only).
   121	
   122	  PROFILE/QUALITATIVE GATES (2):
   123	    2. nusselt_profile_r_over_d — QUALITATIVE_GATE — Nu(r/D) shape match
   124	       at 5+ radial stations (r/D ∈ {0, 0.5, 1.0, 1.5, 2.0}). Reuses the
   125	       existing `nusselt_number_profile` + `nusselt_number_profile_r`
   126	       adapter outputs. Profile-mode comparator: per-station tolerance
   127	       25-30%. The SHAPE is the gate, not the per-point values. The
   128	       DEC-V61-044 NACA Cp pattern is the reference implementation.
   129	
   130	    3. secondary_peak_presence_or_absence — QUALITATIVE_GATE — the canonical
   131	       impinging-jet Nu(r/D) profile at h/D ≈ 2 has a SECONDARY PEAK around
   132	       r/D ≈ 2 caused by transition-to-turbulence in the wall jet (Cooper
   133	       1993 + Baughn & Shimizu 1989 both report this for Re ≥ ~20000).
   134	       At Re = 10000 the secondary peak may be absent or weak (transitional
   135	       flow regime). The gate's PASS condition depends on §3 citation audit:
   136	         - If gold anchor measures Re=10000 → gate = "secondary peak ABSENT"
   137	           (boolean, no tolerance)
   138	         - If gold anchor measures Re ≥ 20000 (mismatch case) → gate is
   139	           DOWNGRADED to PROVISIONAL_ADVISORY in v3 with explicit
   140	           §physics_contract.note acknowledgement
   141	       This gate is DISTINCT from the profile-shape gate above: it tests
   142	       a topological feature (number of local maxima ≥ 1.5 D outward),
   143	       not the per-station magnitudes.
   144	
   145	  PROVISIONAL_ADVISORY (NOT a physics gate):
   146	    4. y_plus_first_cell_at_plate — PROVISIONAL — wall-resolution diagnostic
   147	       at the impingement plate. Threshold band: y+ < 5 desired (low-Re
   148	       wall-resolved); y+ < 30 acceptable (wall-function regime). Pure
   149	       diagnostic, not enforced.
   150	
   151	  RETIRED FROM v1 (per Codex F2):
   152	    - nu_monotonic_decay_from_stagnation as NON_TYPE_HARD_INVARIANT was
   153	      MIS-CLASSIFIED. The "should monotonically decay" claim is itself the
   154	      content of gate #3 (secondary peak absent ⇔ no second local max),
   155	      so v1 was double-counting the same physics. Folded into gate #3.
   156	      The per-station shape-match in gate #2 already provides the only
   157	      independent physics signal.
   158	
   159	primary_gate_count: 1               # v2 (per Codex F2): only the headline
   160	                                    # scalar (Nu_stag) counts toward the
   161	                                    # primary denominator. Profile gates are
   162	                                    # qualitative.
   163	profile_qualitative_gate_count: 2   # v2: nusselt_profile_r_over_d +
   164	                                    # secondary_peak_presence_or_absence
   165	case_type_hard_gate_signed: 1       # v2 (per Codex F2 + V61-058 template):
   166	                                    # number of HARD_GATED observables that
   167	                                    # contribute to the primary verdict
   168	                                    # denominator. Equals primary_gate_count
   169	                                    # for this DEC; field exists for
   170	                                    # cross-referencing comparator's hard
   171	                                    # checks (Stage C.2 semantics).
   172	
   173	# ============================================================================
   174	# §2 Headline observable — citation provenance (F1-M2 hard gate)
   175	# ============================================================================
   176	headline_observable: nusselt_stagnation_at_r_d_zero
   177	headline_gate: nusselt_stagnation_at_r_d_zero  # v2 per V61-058 template:
   178	                                                # explicit field for the
   179	                                                # comparator's headline pick
   180	headline_reference: PENDING_CITATION_AUDIT      # resolved in §3 priority chain
   181	headline_reference_value: PENDING_CITATION_AUDIT
   182	headline_reference_tolerance: 0.30  # widened from typical 0.15 to absorb
   183	                                    # Re/h-over-d mismatch + steady-vs-RANS
   184	                                    # vs unsteady RKE, like V61-060 did for RBC
   185	
   186	# ============================================================================
   187	# §3 Citation provenance audit (BLOCKING — must close before Stage A)
   188	# ============================================================================
   189	citation_audit:
   190	  whitelist_claim:
   191	    label: "Cooper et al. 1984 / Behnad et al. 2013"
   192	    doi: "10.1016/j.ijheatfluidflow.2013.03.003"
   193	    audit_status: VERIFIED_WRONG_PAPER  # v2 per Codex F1: Crossref query
   194	                                        # confirms this DOI resolves to a
   195	                                        # turbine-LES paper, NOT impinging
   196	                                        # jet (V61-060 pattern repeated).
   197	    doi_resolves_to: "Turbine LES paper (NOT impinging jet) — VERIFIED 2026-04-26 via Codex Crossref query"
   198	    audit_reason: |
   199	      Whitelist label "Cooper 1984" does not match any well-known
   200	      impinging-jet author/date. Whitelist DOI 10.1016/j.ijheatfluidflow.2013.03.003
   201	      VERIFIED to resolve to an unrelated turbine-LES paper (Codex
   202	      Crossref query, 2026-04-26). "Behnad 2013" is most likely a
   203	      corruption of "Behnia 1998/1999".
   204	
   205	  # v2 (per Codex F1): Stage A.0 MUST try the following resolveable DOIs
   206	  # in priority order. The list distinguishes THERMAL gold anchor
   207	  # (primary; what the headline Nu_stag will be compared against) from
   208	  # HYDRODYNAMIC support (provides flow-field references but NOT Nu).
   209	  thermal_gold_anchor_priority_chain:
   210	    1_baughn_shimizu_1989:
   211	      authors: "Baughn, J.W., Shimizu, S."
   212	      year: 1989
   213	      title: "Heat transfer measurements from a surface with uniform heat flux and an impinging jet"
   214	      journal: "ASME J. Heat Transfer 111(4), 1096-1098"
   215	      doi: "10.1115/1.3250776"
   216	      reason_promoted: |
   217	        PRIMARY THERMAL ANCHOR CANDIDATE (Codex F1 recommendation).
   218	        Direct heat-transfer measurement from an axisymmetric jet
   219	        impinging on a uniform-heat-flux plate. Re ≈ 23700, h/D ∈ {2, 6, 10}.
   220	        Reports Nu(r/D) profile + stagnation Nu. Critical caveat: the
   221	        measurement uses uniform-heat-flux boundary condition (q=const),
   222	        NOT constant-temperature plate (T=const) which is what the
   223	        adapter currently emits at foam_agent_adapter.py:6204. This
   224	        BC mismatch must be reflected in the gold YAML §physics_contract.note
   225	        like V61-060 did for Pandey & Schumacher's free-slip vs no-slip mismatch.
   226	      stage_a_0_action: |
   227	        (a) Try DOI 10.1115/1.3250776; verify resolves to the right paper.
   228	        (b) If accessible, extract Nu_stag and Nu(r/D) at r/D ∈ {0, 0.5, 1, 1.5, 2}
   229	            from the published Table or Figure with explicit locator.
   230	        (c) If h/D=2 row exists, use it. Otherwise pivot to h/D=6 and
   231	            update whitelist.parameters.h_over_d to match.
   232	        (d) Re mismatch: paper reports Re ≈ 23700; whitelist sets Re=10000.
   233	            Stage A.0 MUST either (i) bump whitelist Re to 23700 OR
   234	            (ii) document this gap as a known physics-fidelity risk
   235	            in §physics_contract.note (V61-060 pattern).
   236	
   237	    2_behnia_1998_axisymmetric_jet:
   238	      authors: "Behnia, M., Parneix, S., Durbin, P.A."
   239	      year: 1998
   240	      title: "Prediction of heat transfer in an axisymmetric turbulent jet impinging on a flat plate"
   241	      journal: "Int. J. Heat Mass Transfer 41(12), 1845-1855"
   242	      doi: "10.1016/S0017-9310(97)00254-8"
   243	      reason_promoted: |
   244	        SECONDARY THERMAL ANCHOR (RANS-validation paper).
   245	        Re ∈ {15000, 23000} per the v2 paper; uses k-ε-v2-f turbulence
   246	        model and validates against Baughn 1989 + Yan 1991. Useful as
   247	        a CROSS-CHECK because it provides explicit RANS-CFD vs
   248	        experiment Nu(r/D) profiles, calibrating what "good agreement"
   249	        actually looks like for our k-omega SST stack.
   250	      stage_a_0_action: |
   251	        Try if Baughn 1989 is paywalled or unavailable. Use Behnia 1998
   252	        only if (a) it includes a Re=10000 row OR (b) the Behnia/Baughn
   253	        comparison table justifies a CFD-to-CFD anchor (less honest;
   254	        V61-060 explicitly avoided this kind of self-comparison).
   255	
   256	    3_behnia_1999_unconfined_confined:
   257	      authors: "Behnia, M., Parneix, S., Shabany, Y., Durbin, P.A."
   258	      year: 1999
   259	      title: "Numerical study of turbulent heat transfer in confined and unconfined impinging jets"
   260	      journal: "Int. J. Heat Fluid Flow 20(1), 1-9"

exec
/bin/zsh -lc 'rg -n "F1|F2|F3|HIGH|MED|LOW|citation_audit|taxonomy|risk register|APPROVE|REQUEST_CHANGES" reports/codex_tool_reports/dec_v61_067_plan_review_v1.md' in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
30:   to review. Read §0 preexisting_state_honesty + §3 citation_audit FIRST.
41:1. **§3 citation_audit (BLOCKING)** — is the audit framing correct? Is
47:   right taxonomy? Should the profile gate be split into multiple per-station
49:3. **§4 risk register completeness** — is anything missing? E.g.:
51:     (Nu > 500). Should V61-067 surface this in risk register?
62:OUTPUT: structured findings (F1=HIGH, F2=MED, F3=LOW) with specific section
63:references and concrete edit suggestions. APPROVE_PLAN / APPROVE_PLAN_WITH_CHANGES /
64:REQUEST_CHANGES verdict. Under 600 words.
319:     2	# Mandated by methodology v2.0 F1-M1 hard gate before Stage A.
426:   109	# §2 Headline observable — citation provenance (F1-M2 hard gate)
438:   121	citation_audit:
471:   154	    severity: HIGH
484:   167	    severity: MED
494:   177	    severity: MED
504:   187	    severity: LOW
517:   200	    severity: HIGH
550:   233	        (4 observables, schema_v2, Type II gate_status taxonomy)
602:   678	                # LDC: canonical name match, no Re-heuristic (Codex MEDIUM: the
806:   275	# §7 Acceptance criteria (definition of done — F1-M2 two-tier close gate)
810:   279	    Final Codex round returns APPROVE OR APPROVE_WITH_COMMENTS, OR
874:678-   678	                # LDC: canonical name match, no Re-heuristic (Codex MEDIUM: the
1132:   121	citation_audit:
1165:   154	    severity: HIGH
1178:   167	    severity: MED
1188:   177	    severity: MED
1198:   187	    severity: LOW
1211:   200	    severity: HIGH
1222:   275	# §7 Acceptance criteria (definition of done — F1-M2 two-tier close gate)
1226:   279	    Final Codex round returns APPROVE OR APPROVE_WITH_COMMENTS, OR
1580:knowledge/gold_standards/naca0012_airfoil.yaml:23:  DEC-V61-058 Type II multi-dim arc (downgraded from Type I per Codex F1):
1597:.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:15:#         F1-HIGH (Type I family-count failure): downgraded case_type Type I → Type II.
1621:.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:233:        (4 observables, schema_v2, Type II gate_status taxonomy)
1630:.planning/decisions/2026-04-23_cfd_cylinder_multidim_dec053.md:43:  - DEC-V61-052 (BFS · Type II precedent · 5 rounds incl. F1-M2 back-fill)
1640:.planning/decisions/2026-04-25_v61_058_naca0012_multidim.md:86:- **case_type = II** (Codex F1 forced downgrade — original I plan had 5 gates but Codex ruled the dependency graph collapsed: Cl@α=4 + Cl@α=8 + dCl/dα are not independent, all sit on the same lift-curve fit. Type II re-cast: 1 PRIMARY scalar + 1 SAME_RUN_CROSS_CHECK + 1 PROFILE + 1 QUALITATIVE + 1 PROVISIONAL_ADVISORY = 5-row Type II schema).
1652:    62	codex_plan_review_verdict: REQUEST_CHANGES_v1_then_REWRITTEN_v2  # final verdict pending Codex re-review of v2
1657:    67	case_type: II  # DOWNGRADED v1→v2 per Codex F1: Type I requires ≥3 PHYSICALLY-
1698:   108	                           family — labeled CROSS_CHECK to honor Codex F1.
1704:   114	                                (corrected per Codex F3): u_τ = U·sqrt(Cf/2),
1716:   126	  Cl_at_alpha_four — RUN PERFORMED to enable Cl_alpha_linear_regime_slope
1718:   128	  separate HARD gate (avoids Codex F1 same-extraction-path objection).
1786:    20	codex_plan_review_verdict: PENDING  # update to APPROVE_PLAN / APPROVE_PLAN_WITH_CHANGES / REQUEST_CHANGES after pre-Stage-A Codex review
1918:  "title": "IMPINGING JET: EXPERIMENTAL ANALYSIS OF FLOW FIELD AND HEAT TRANSFER FOR ASSESSMENT OF TURBULENCE MODELS",
1926:  "title": "IMPINGING JET: EXPERIMENTAL ANALYSIS OF FLOW FIELD AND HEAT TRANSFER FOR ASSESSMENT OF TURBULENCE MODELS",
1953:  "title": "HEAT TRANSFER FROM AN INFLOW-TYPE SWIRLING TURBULENT IMPINGING JET(Impinging Jet)",
2093:.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:67:case_type: II  # DOWNGRADED v1→v2 per Codex F1: Type I requires ≥3 PHYSICALLY-
2225:  "title": "TURBULENT FLOW AND HEAT TRANSFER FROM CONFINED MULTIPLE IMPINGING SLOT JETS",
2285:- **F1 = HIGH** — [§3 citation_audit](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:121) is correctly suspicious, but the closure framing is still too loose for Stage A.0. The whitelist DOI in [knowledge/whitelist.yaml](/Users/Zhuanz/Desktop/cfd-s4-rbc/knowledge/whitelist.yaml:206) resolves to an unrelated turbine LES paper, not an impinging-jet source: <https://doi.org/10.1016/j.ijheatfluidflow.2013.03.003>. Also, `Cooper et al. 1993` is the hydrodynamic companion dataset, not the heat-transfer anchor: <https://doi.org/10.1016/S0017-9310(05)80204-2>. The heat-transfer anchor is much more plausibly `Baughn & Shimizu 1989`: <https://doi.org/10.1115/1.3250776>. I would also treat `Behnad et al. 2013` as likely corruption of `Behnia et al. 1998/1999`, not a trusted fallback (`10.1016/S0017-9310(97)00254-8`, `10.1016/S0142-727X(98)10040-1`). Concrete edit: rewrite §3 so Stage A.0 must try these DOIs in order, and distinguish `thermal gold anchor` from `hydrodynamic support` instead of listing Cooper/Baughn as interchangeable alternatives.
2287:- **F2 = MED** — [§1 classification](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:67) should stay **Type II**, not be split into per-station Type I gates; the stations are one profile family, not independent physics families. But the current taxonomy is internally inconsistent with the template and V61-058 precedent: it declares only one profile/qualitative gate, sets `primary_gate_count: 2`, and omits `headline_gate` / `case_type_hard_gate_signed`. Concrete edit: keep Type II, change `primary_gate_count` to `1`, add `profile_qualitative_gate_count: 2`, and either relabel monotonicity as a second `QUALITATIVE_GATE` or add a distinct second shape gate such as `secondary_peak_presence_or_absence` / `half-width radius`. This also means [§6 stage_preview](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:227) needs an extra early batch before extractor/comparator work: resolve citation + free/confined + Re/H/D + wall-BC family first. With those gaps still open, `estimated_pass_rate_round1 = 0.40` looks optimistic; I’d set `0.25–0.30`.
2289:- **F3 = LOW** — [§4 risk_register](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:152) is missing three explicit surfaced risks already visible in code: `nusselt_number_unphysical_magnitude` exists in [_extract_jet_nusselt](/Users/Zhuanz/Desktop/cfd-s4-rbc/src/foam_agent_adapter.py:9717); the generator uses a constant-temperature plate, not uniform heat flux, at [foam_agent_adapter.py:6204](/Users/Zhuanz/Desktop/cfd-s4-rbc/src/foam_agent_adapter.py:6204); and the mesh is neither cyclic AMI nor 3D wedge, but a pseudo-2D slab with `empty` patches at [foam_agent_adapter.py:5632](/Users/Zhuanz/Desktop/cfd-s4-rbc/src/foam_agent_adapter.py:5632). [§7 acceptance_criteria](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:277) should therefore name exact DOI + figure/table locator, exact station set, exact tolerance mode, and “hazard flag absent” as a verifiable criterion.
2291:**Verdict:** `REQUEST_CHANGES`
2296:- **F1 = HIGH** — [§3 citation_audit](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:121) is correctly suspicious, but the closure framing is still too loose for Stage A.0. The whitelist DOI in [knowledge/whitelist.yaml](/Users/Zhuanz/Desktop/cfd-s4-rbc/knowledge/whitelist.yaml:206) resolves to an unrelated turbine LES paper, not an impinging-jet source: <https://doi.org/10.1016/j.ijheatfluidflow.2013.03.003>. Also, `Cooper et al. 1993` is the hydrodynamic companion dataset, not the heat-transfer anchor: <https://doi.org/10.1016/S0017-9310(05)80204-2>. The heat-transfer anchor is much more plausibly `Baughn & Shimizu 1989`: <https://doi.org/10.1115/1.3250776>. I would also treat `Behnad et al. 2013` as likely corruption of `Behnia et al. 1998/1999`, not a trusted fallback (`10.1016/S0017-9310(97)00254-8`, `10.1016/S0142-727X(98)10040-1`). Concrete edit: rewrite §3 so Stage A.0 must try these DOIs in order, and distinguish `thermal gold anchor` from `hydrodynamic support` instead of listing Cooper/Baughn as interchangeable alternatives.
2298:- **F2 = MED** — [§1 classification](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:67) should stay **Type II**, not be split into per-station Type I gates; the stations are one profile family, not independent physics families. But the current taxonomy is internally inconsistent with the template and V61-058 precedent: it declares only one profile/qualitative gate, sets `primary_gate_count: 2`, and omits `headline_gate` / `case_type_hard_gate_signed`. Concrete edit: keep Type II, change `primary_gate_count` to `1`, add `profile_qualitative_gate_count: 2`, and either relabel monotonicity as a second `QUALITATIVE_GATE` or add a distinct second shape gate such as `secondary_peak_presence_or_absence` / `half-width radius`. This also means [§6 stage_preview](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:227) needs an extra early batch before extractor/comparator work: resolve citation + free/confined + Re/H/D + wall-BC family first. With those gaps still open, `estimated_pass_rate_round1 = 0.40` looks optimistic; I’d set `0.25–0.30`.
2300:- **F3 = LOW** — [§4 risk_register](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:152) is missing three explicit surfaced risks already visible in code: `nusselt_number_unphysical_magnitude` exists in [_extract_jet_nusselt](/Users/Zhuanz/Desktop/cfd-s4-rbc/src/foam_agent_adapter.py:9717); the generator uses a constant-temperature plate, not uniform heat flux, at [foam_agent_adapter.py:6204](/Users/Zhuanz/Desktop/cfd-s4-rbc/src/foam_agent_adapter.py:6204); and the mesh is neither cyclic AMI nor 3D wedge, but a pseudo-2D slab with `empty` patches at [foam_agent_adapter.py:5632](/Users/Zhuanz/Desktop/cfd-s4-rbc/src/foam_agent_adapter.py:5632). [§7 acceptance_criteria](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:277) should therefore name exact DOI + figure/table locator, exact station set, exact tolerance mode, and “hazard flag absent” as a verifiable criterion.
2302:**Verdict:** `REQUEST_CHANGES`

exec
/bin/zsh -lc "git show 46f0075:.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml | nl -ba | sed -n '260,620p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
   260	      journal: "Int. J. Heat Fluid Flow 20(1), 1-9"
   261	      doi: "10.1016/S0142-727X(98)10040-1"
   262	      reason_promoted: |
   263	        TERTIARY ANCHOR — addresses §4 R-confinement (free-jet vs
   264	        confined-jet) by reporting BOTH configurations.
   265	      stage_a_0_action: Use only if R-confinement audit at §4 surfaces a confinement mismatch.
   266	
   267	  hydrodynamic_support_only:
   268	    cooper_1993:
   269	      authors: "Cooper, D., Jackson, D.C., Launder, B.E., Liao, G.X."
   270	      year: 1993
   271	      title: "Impinging jet studies for turbulence model assessment — I. Flow-field experiments"
   272	      journal: "Int. J. Heat Mass Transfer 36(10), 2675-2684"
   273	      doi: "10.1016/S0017-9310(05)80204-2"
   274	      reason_demoted: |
   275	        v2 per Codex F1: Cooper 1993 PART I is HYDRODYNAMIC ONLY (mean
   276	        velocity + Reynolds stresses). Heat transfer is in Part II (Cooper
   277	        et al. 1993 companion paper, different DOI). v1 listed Cooper 1993
   278	        as interchangeable with Baughn 1989 — that conflated flow-field
   279	        and heat-transfer datasets. Cooper 1993 Part I is reusable for
   280	        hydrodynamic SANITY_CHECK (e.g. axial velocity decay along the
   281	        centerline) but does NOT supply Nu_stag.
   282	      stage_a_0_action: |
   283	        Optional — use as cross-check for the hydrodynamic field if a
   284	        future v2 sub-batch adds a velocity-profile observable. Out of
   285	        scope for the headline Nu_stag gate.
   286	
   287	  closure_action_required: |
   288	    Stage A.0 MUST attempt the THREE thermal_gold_anchor_priority_chain
   289	    DOIs in order, RECORDING in §physics_contract.note:
   290	      (i) which DOI was tried,
   291	      (ii) whether it resolved to the expected paper,
   292	      (iii) which Re row was used (with table/figure locator),
   293	      (iv) any BC / Re / h-D mismatch that must be acknowledged in
   294	           §physics_contract.note as a known fidelity-gap.
   295	    PASS CRITERIA: at least ONE thermal anchor with explicit locator
   296	    landed; whitelist DOI replaced; gold YAML §source/literature_doi
   297	    updated; if BC mismatch present (constant-T vs uniform-q), it MUST
   298	    appear in physics_contract.note (V61-060 acknowledgement pattern).
   299	
   300	# ============================================================================
   301	# §4 Risk register (pre-Stage-A, surfaced for Codex review)
   302	# ============================================================================
   303	risk_register:
   304	  R1_re_mismatch:
   305	    severity: HIGH
   306	    description: |
   307	      Whitelist Re=10000 is unusual for impinging-jet benchmarks. Cooper
   308	      1993 ran Re=23000. Behnad 2013 may have multiple Re values. If the
   309	      gold YAML's ref_value was correlated from Re=23000 data and applied
   310	      blindly to Re=10000 simulation, deviation will be unbounded. Stage
   311	      A.0 must confirm Re consistency between gold ref + whitelist task_spec.
   312	    mitigation: |
   313	      (a) Verify Cooper 1993 has a Re=10000 row, OR
   314	      (b) Bump whitelist Re=10000 → 23000 to match the correlation, OR
   315	      (c) Use a Re-agnostic Nu correlation (Schlichting Nu/Re^0.5 = const
   316	          near stagnation) and document the assumption.
   317	  R2_h_over_d_mismatch:
   318	    severity: MED
   319	    description: |
   320	      Whitelist h/d=2 is a common stand-off. Cooper 1993 and Baughn/Shimizu
   321	      1989 both used h/d=2 OR h/d=6; verify alignment. h/d=2 puts the
   322	      stagnation in the potential core (Nu peaks); h/d=6 is post-core
   323	      (different Nu(r) shape). Stage A.0 must confirm.
   324	    mitigation: |
   325	      Lock h/d to whatever the chosen citation uses; if no overlap, hold
   326	      Stage A on a follow-up.
   327	  R3_turbulence_model_choice:
   328	    severity: MED
   329	    description: |
   330	      Whitelist sets `turbulence_model: k-omega SST`. For impinging jets
   331	      this is reasonable (k-ε notoriously over-predicts Nu near stagnation
   332	      due to round-jet stagnation anomaly). Adapter must actually emit
   333	      k-omega SST, not silently fall back to k-ε. Verify at Stage A.
   334	    mitigation: |
   335	      Stage A.5 alias-parity test (V61-060 lesson) must include a
   336	      turbulence-model-emitted-vs-declared check.
   337	  R4_buoyantFoam_dispatch_overlap:
   338	    severity: LOW
   339	    description: |
   340	      Adapter at src/foam_agent_adapter.py:676 hardcodes `solver_name =
   341	      "buoyantFoam"` for IMPINGING_JET, overriding the whitelist's
   342	      `simpleFoam` declaration. This is intentional (impinging jet needs
   343	      thermal) but contradicts whitelist; CASE_ID_TO_SOLVER in
   344	      src/auto_verifier/config.py:69 also hardcodes simpleFoam, creating
   345	      a 2-source-of-truth ambiguity.
   346	    mitigation: |
   347	      Stage A clean-up: align both the whitelist and CASE_ID_TO_SOLVER to
   348	      buoyantFoam, OR document the override path explicitly in the gold
   349	      YAML §physics_contract.note.
   350	  R5_alias_map_staleness_post_v61_060:
   351	    severity: HIGH
   352	    description: |
   353	      RETRO-V61-060 addendum: alias-map staleness was the #1 post-R3
   354	      defect. Any case_name change at Stage A.0 (e.g. citation suffix
   355	      added) MUST atomically update both `_TASK_NAME_TO_CASE_ID_ALIASES`
   356	      maps (src/foam_agent_adapter.py:247 + src/auto_verifier/config.py:30).
   357	      A.0 + A.3 should be ONE commit.
   358	    mitigation: |
   359	      Pre-commit check: if intake §3 demands a case_name rename, the same
   360	      commit MUST touch both alias maps. Codex pre-Stage-A review must
   361	      enforce this.
   362	
   363	  # v2 (per Codex F3-LOW): three risks already visible in the code that
   364	  # were missed in v1.
   365	  R6_unphysical_magnitude_hazard_flag_exists:
   366	    severity: MED
   367	    description: |
   368	      `_extract_jet_nusselt` already emits a HAZARD flag
   369	      `nusselt_number_unphysical_magnitude=True` when extracted Nu_stag
   370	      falls outside [0, 500] (foam_agent_adapter.py:9717-9719). DEC-V61-042
   371	      round 1 explicitly noted "previous code silently clamped Nu to
   372	      [0, 500]" — a diverged solver could mask runaway gradients as
   373	      benign 500 values. Stage E live run + Stage D UI MUST surface this
   374	      flag (similar to V61-060's NON_TYPE_HARD_INVARIANT card pattern).
   375	      If the flag fires post-Stage-E, that is a HARD-FAIL signal even
   376	      if the headline Nu falls within tolerance.
   377	    mitigation: |
   378	      §7 acceptance criterion v explicitly requires "hazard flag absent
   379	      OR explicitly excused in DEC closeout" before headline-PASS verdict
   380	      can land.
   381	  R7_plate_bc_constant_temperature_vs_uniform_heat_flux:
   382	    severity: HIGH
   383	    description: |
   384	      Adapter at foam_agent_adapter.py:6204 emits the plate as
   385	      `type fixedValue; value uniform {T_plate};` — that is a
   386	      CONSTANT-TEMPERATURE Dirichlet BC (T = const).
   387	      Many literature impinging-jet correlations (Baughn & Shimizu 1989
   388	      explicitly; Yan 1991; ERCOFTAC IJ benchmarks) use UNIFORM HEAT FLUX
   389	      (q = const, Neumann ∂T/∂n = const) instead. The Nu-Re-Pr correlation
   390	      coefficients differ between the two BC families: at the same Re,
   391	      uniform-q yields a DIFFERENT Nu(r/D) profile than constant-T.
   392	      If §3 lands Baughn 1989 as primary anchor, this BC mismatch is a
   393	      direct fidelity-gap risk that may produce a 30-50% deviation
   394	      independently of Re/h/D.
   395	    mitigation: |
   396	      Stage A.0 closure must EXPLICITLY note BC family in the gold YAML
   397	      §physics_contract.note. Stage E acceptance widened to include
   398	      "either headline within ±30% OR DEC closeout as
   399	      METHODOLOGY_COMPLETE_PHYSICS_FIDELITY_GAP_DOCUMENTED with BC
   400	      mismatch as primary cause" (V61-063/V61-066 honest-FAIL pattern).
   401	      Optional Stage A sub-batch: add fixedGradient T plate BC variant
   402	      to the adapter (~30 LOC, separate DEC).
   403	  R8_pseudo_2d_slab_geometry_vs_true_axisymmetric:
   404	    severity: MED
   405	    description: |
   406	      Adapter at foam_agent_adapter.py:5632-5687 emits a pseudo-2D slab
   407	      with `front`/`back` faces as `empty` patches (Cartesian r-z slab,
   408	      depth 0.1 m). This is NEITHER:
   409	        (a) a true 3D axisymmetric mesh (cyclic AMI / wedge), NOR
   410	        (b) a 2.5D wedge with `wedge` boundary type
   411	      The OpenFOAM `empty` BC tells the solver to treat the third
   412	      direction as 1 cell with no gradient — equivalent to a Cartesian
   413	      2D slab, NOT an axisymmetric solve. Cooper-style correlations
   414	      assume true axisymmetric flow (3D rotation about the axis); a
   415	      Cartesian slab forces the radial direction to be a 1D line
   416	      instead of a 2D r-θ surface, which DOUBLES the actual cross-
   417	      sectional area sampled per unit r and changes the integrated
   418	      Nu measurement by O(1).
   419	    mitigation: |
   420	      Stage A.0 closure must verify whether the slab approximation is
   421	      tolerable: (a) if Nu is computed as a LOCAL gradient (the current
   422	      extractor at line 9698 uses local |∂T/∂n| at each radial bin),
   423	      slab vs axisymmetric does NOT affect the local value, so this is
   424	      LOW IMPACT for nusselt_stagnation_at_r_d_zero; BUT
   425	      (b) any INTEGRATED quantity (e.g. total heat transfer rate over
   426	      the plate) WILL differ. §1 gates 1+2+3 are all LOCAL, so R8
   427	      stays MED severity (not HIGH) — but Stage E DEC must mention
   428	      the slab approximation as a known limitation.
   429	
   430	# ============================================================================
   431	# §5 Estimated Codex round budget + pass-rate (for self-pass-rate calibration)
   432	# ============================================================================
   433	codex_budget_rounds: 5  # R5 normal checkpoint, R6 halt-risk, R7 force abandon
   434	estimated_pass_rate_round1: 0.28  # v2 per Codex F2: lowered 0.40 → 0.28 (midpoint
   435	                                  # of Codex 0.25-0.30 band). Pre-Stage-A R1 already
   436	                                  # CHANGES_REQUIRED (matches R1=0% pass at any
   437	                                  # ≤0.30 estimate), so this is now backward-
   438	                                  # calibrated. Citation audit (§3) is genuinely
   439	                                  # — there's a non-trivial probability that
   440	                                  # Stage A.0 surfaces "no clean publicly-archived
   441	                                  # benchmark for Re=10000 h/d=2", forcing a
   442	                                  # whitelist Re bump (architectural change) or
   443	                                  # re-classification as PHYSICS_FIDELITY_GAP.
   444	
   445	# ============================================================================
   446	# §6 Stage A → E preview (subject to Codex pre-Stage-A review)
   447	# ============================================================================
   448	stage_preview:
   449	  # v2 (per Codex F2): Stage A.0 split into A.0a (citation+context audit)
   450	  # and A.0b (gold YAML rewrite). A.0a MUST close all four entangled
   451	  # questions — citation, free/confined, Re/H/D, wall-BC family — BEFORE
   452	  # any gold/extractor/comparator work touches the codebase. This prevents
   453	  # the V61-060 Stage A.0 trap where a citation pivot wasn't atomic with
   454	  # the alias map update.
   455	  A_0a_pre_pivot_context_audit:
   456	    purpose: |
   457	      Resolve the four entangled context questions atomically:
   458	        (1) Citation — try the §3 thermal_gold_anchor_priority_chain DOIs
   459	            in order; record which paper, which Re row, which Table/Figure.
   460	        (2) Confinement — confirm whether the chosen anchor reports
   461	            FREE-jet (recommended, matches whitelist geometry) or
   462	            CONFINED-jet (would require a physics_contract.note caveat).
   463	        (3) Re/H/D match — confirm the gold's Re vs whitelist Re=10000
   464	            and h/D vs whitelist h_over_d=2.0 alignment.
   465	        (4) Wall-BC family — confirm constant-T (Dirichlet) vs uniform-q
   466	            (Neumann); §4 R7 risk crystallises here.
   467	    deliverables:
   468	      - .planning/intake/DEC-V61-067_a0a_context_resolution.md (NEW)
   469	        with one bullet per question + DOI + Table/Figure locator OR
   470	        explicit "no clean match — gap documented" finding
   471	      - Decision: PROCEED (anchor + Re + h/D + BC all match) vs
   472	        MISMATCH_DOCUMENTED (proceed but expect honest-FAIL closeout) vs
   473	        BLOCK (cannot proceed; whitelist Re bump or follow-up DEC required)
   474	    no_code_changes_yet: true
   475	  A_0b_citation_pivot:
   476	    purpose: |
   477	      Apply the A.0a decisions to the gold YAML and whitelist atomically.
   478	    deliverables:
   479	      - knowledge/gold_standards/axisymmetric_impinging_jet.yaml rewrite
   480	        (4 observables matching v2 §1: 1 HARD_GATED + 2 QUALITATIVE_GATES
   481	        + 1 PROVISIONAL_ADVISORY; schema_v2; physics_contract.note
   482	        documents any A.0a-surfaced mismatches per V61-060 honesty pattern)
   483	      - knowledge/whitelist.yaml `name` rename + DOI replace + atomic
   484	        update of BOTH `_TASK_NAME_TO_CASE_ID_ALIASES` maps
   485	        (foam_agent_adapter.py:247 + auto_verifier/config.py:30) per
   486	        R5 mitigation — ALL IN ONE COMMIT
   487	  A_1_to_A_n_canonical_contract_repair:
   488	    purpose: Confirm adapter dispatch + extractor outputs match the new gold
   489	    deliverables:
   490	      - Whitelist+CASE_ID_TO_SOLVER alignment (R4 mitigation)
   491	      - Turbulence model emit-vs-declared parity test (R3 mitigation)
   492	      - Verify _extract_jet_nusselt's profile output matches the new
   493	        observable schema (Stage A is not expected to need extractor changes;
   494	        the extractor is already DEC-V61-042-correct)
   495	  B_extractors:
   496	    purpose: Add monotonic-decay invariant extractor; extend profile gate
   497	    deliverables:
   498	      - src/impinging_jet_extractors.py (NEW) with extract_nu_monotonicity
   499	      - tests/test_impinging_jet_extractors.py (≥20 unit tests)
   500	      - register in src/_plane_assignment.py SSOT
   501	  C_preflight_comparator_riskflags:
   502	    purpose: Atomic preflight + comparator + risk_flag registry
   503	    deliverables:
   504	      - knowledge/schemas/risk_flag_registry.yaml: 4-5 new IJ-specific flags
   505	        from §4 risk_register (R1, R2, R3, R5)
   506	      - .planning/case_profiles/axisymmetric_impinging_jet.yaml backfill
   507	      - Comparator branch reuse (V61-060 NON_TYPE_HARD_INVARIANT path)
   508	  D_ui_surface:
   509	    purpose: 4-card metrics_impinging_jet block in CompareTab + audit allowlist
   510	    deliverables:
   511	      - ui/backend/services/comparison_report.py: metrics_impinging_jet
   512	        (mirrors metrics_rbc / metrics_dhc pattern)
   513	      - ui/frontend/src/pages/learn/case_detail/CompareTab.tsx: rendering
   514	        branch (NEW architecture per main refactor — sub-component, not
   515	        the monolithic LearnCaseDetailPage.tsx that V61-060 wrote against)
   516	      - scripts/phase5_audit_run.py: secondary_scalars allowlist
   517	  E_live_run_dec_closeout:
   518	    purpose: Live OpenFOAM run + DEC frontmatter + Notion sync + PR
   519	    deliverables:
   520	      - live buoyantFoam run via phase5_audit_run.py axisymmetric_impinging_jet
   521	      - audit_real_run_measurement.yaml regen
   522	      - .planning/decisions/2026-04-2X_v61_067_impinging_jet_multidim.md
   523	      - PR to main
   524	
   525	# ============================================================================
   526	# §7 Acceptance criteria (definition of done — F1-M2 two-tier close gate)
   527	# ============================================================================
   528	acceptance_criteria:
   529	  i_codex_arc_complete: |
   530	    Final Codex round returns APPROVE OR APPROVE_WITH_COMMENTS, OR
   531	    CHANGES_REQUIRED with all findings closed verbatim per the 5-condition
   532	    exception envelope (CLAUDE.md).
   533	  ii_headline_validated_or_honestly_failed: |
   534	    EITHER: live-run nusselt_stagnation_at_r_d_zero falls within ±30%
   535	    (relative tolerance) of the gold ref_value resolved at A.0a — primary
   536	    gate PASS; OR: it falls outside the band and the DEC documents the
   537	    physics-fidelity gap explicitly with R7 BC-mismatch and/or R1 Re-mismatch
   538	    cited as primary cause (V61-063 / V61-066 / V61-060 honest-FAIL pattern:
   539	    METHODOLOGY_COMPLETE_PHYSICS_FIDELITY_GAP_DOCUMENTED).
   540	  iii_profile_shape_validated_with_explicit_locators: |
   541	    v2 per Codex F3: tighten "matches Cooper-style" to verifiable form:
   542	    Nu(r/D) profile MUST be measured at exactly r/D ∈ {0.0, 0.5, 1.0, 1.5, 2.0}
   543	    using the existing `_extract_jet_nusselt` `nusselt_number_profile_r`
   544	    output. PASS:
   545	      - per-station relative tolerance ≤30% vs gold values resolved at
   546	        A.0a from explicit Table/Figure locator (NOT a generic "Cooper-style"
   547	        reference)
   548	      - tolerance.mode = relative for all 5 stations
   549	      - if A.0a anchor lacks one or more stations, explicitly mark them
   550	        ADVISORY with a per-station gap reason in the gold YAML.
   551	  iv_secondary_peak_qualitative_gate: |
   552	    v2 per Codex F2: gate #3 (secondary_peak_presence_or_absence) PASS:
   553	      - if Re ≤ 15000: secondary peak ABSENT (Nu(r/D) is monotonically
   554	        non-increasing for r/D ∈ [0, 2]) — boolean gate, no tolerance
   555	      - if Re ≥ 20000: secondary peak PRESENT at r/D ∈ [1.5, 2.5] (one
   556	        local maximum after the stagnation peak) — boolean gate
   557	      - if 15000 < Re < 20000: gate is ADVISORY (transitional regime)
   558	  v_alias_map_atomic_with_case_name_rename: |
   559	    Per RETRO-V61-060 addendum: any A.0b case_name rename MUST be in the
   560	    same commit as both `_TASK_NAME_TO_CASE_ID_ALIASES` map updates
   561	    (foam_agent_adapter.py:247 + auto_verifier/config.py:30).
   562	  vi_unphysical_magnitude_hazard_flag_absent: |
   563	    v2 per Codex F3: Stage E live run must produce
   564	    `nusselt_number_unphysical_magnitude=False` (or unset). If the flag
   565	    fires, the DEC closeout MUST explicitly excuse it with a root-cause
   566	    explanation (e.g. "diverged solver despite headline within tolerance"
   567	    is NOT an acceptable PASS regardless of comparator verdict).
   568	  vii_bc_family_documented_in_gold_yaml: |
   569	    v2 per Codex F3 + R7: the chosen gold ref's wall BC family
   570	    (constant-T vs uniform-q) MUST appear in
   571	    knowledge/gold_standards/axisymmetric_impinging_jet.yaml
   572	    §physics_contract.note with explicit acknowledgement of mismatch
   573	    against the adapter's current `fixedValue T_plate` BC.
   574	  viii_pseudo_2d_slab_geometry_acknowledgement: |
   575	    v2 per Codex F3 + R8: the gold YAML §physics_contract.note MUST
   576	    acknowledge that the adapter emits a pseudo-2D Cartesian r-z slab
   577	    with `empty` patches (not a true 3D axisymmetric or wedge mesh).
   578	    The DEC closeout MUST state whether this matters for the chosen
   579	    observables (the current §1 gates are all LOCAL gradients, so the
   580	    impact is expected to be LOW; future integrated-quantity DECs would
   581	    need a different mesh topology).
   582	
   583	# ============================================================================
   584	# §8 Out of scope (will not be addressed in this DEC)
   585	# ============================================================================
   586	out_of_scope:
   587	  - Cross-jet-array configurations (single-jet-only)
   588	  - Compressible jet effects (Ma < 0.3 assumed)
   589	  - Confined-jet vs free-jet variants (free-jet only per existing whitelist
   590	    geometry h_over_d=2)
   591	  - Heat-transfer-coefficient measurement at the nozzle exit (only plate
   592	    Nu is in scope)
   593	  - Multi-Re sweep (single Re=10000 OR Re=23000 after §3 audit; no profile
   594	    over Re — that would be a follow-up DEC)

codex
- `MED` — §6 still contains a stale downstream task: [DEC-V61-067_axisymmetric_impinging_jet.yaml](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:495) plans `extract_nu_monotonicity`, but §1 explicitly retires monotonic decay as a separate gate and folds that physics into `secondary_peak_presence_or_absence` at [same file](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:151). That means `stage_preview` no longer fully matches the v2 taxonomy.

- `LOW` — §4→§7 traceability for the new risks is not fully clean. R6 says it points to “§7 acceptance criterion v” at [line 377](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:377), but the hazard-flag criterion is actually `vi` at [line 562](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:562). R7 and R8 have the right acceptance intent at [lines 395 and 419](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:395), but they do not explicitly point to the matching §7 criteria (`vii`/`viii`).

R1 closure check: all three original findings are substantively closed in the v2 intake.

- F1-HIGH closed: §3 is now rewritten as a priority-ordered DOI chain, with the whitelist DOI marked wrong, `Baughn & Shimizu 1989` promoted as the primary thermal anchor, `Behnia 1998/1999` added as the likely corruption path, and `Cooper 1993` demoted to hydrodynamic-only support at [§3](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:189).
- F2-MED closed: Type II is retained; `primary_gate_count` is now `1`, `profile_qualitative_gate_count` is `2`, `headline_gate` and `case_type_hard_gate_signed` were added, `secondary_peak_presence_or_absence` was added, `A.0a` exists, and `estimated_pass_rate_round1` is lowered to `0.28` at [§1/§5/§6](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:104).
- F3-LOW closed: R6/R7/R8 are present in §4, and §7 now names exact locator/station/tolerance/hazard requirements at [§4/§7](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:303).

Verdict: `APPROVE_PLAN_WITH_CHANGES`

Stage A.0a can proceed, but the two consistency defects above should be patched before downstream execution past A.0a/A.0b.
tokens used
58,816
- `MED` — §6 still contains a stale downstream task: [DEC-V61-067_axisymmetric_impinging_jet.yaml](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:495) plans `extract_nu_monotonicity`, but §1 explicitly retires monotonic decay as a separate gate and folds that physics into `secondary_peak_presence_or_absence` at [same file](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:151). That means `stage_preview` no longer fully matches the v2 taxonomy.

- `LOW` — §4→§7 traceability for the new risks is not fully clean. R6 says it points to “§7 acceptance criterion v” at [line 377](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:377), but the hazard-flag criterion is actually `vi` at [line 562](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:562). R7 and R8 have the right acceptance intent at [lines 395 and 419](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:395), but they do not explicitly point to the matching §7 criteria (`vii`/`viii`).

R1 closure check: all three original findings are substantively closed in the v2 intake.

- F1-HIGH closed: §3 is now rewritten as a priority-ordered DOI chain, with the whitelist DOI marked wrong, `Baughn & Shimizu 1989` promoted as the primary thermal anchor, `Behnia 1998/1999` added as the likely corruption path, and `Cooper 1993` demoted to hydrodynamic-only support at [§3](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:189).
- F2-MED closed: Type II is retained; `primary_gate_count` is now `1`, `profile_qualitative_gate_count` is `2`, `headline_gate` and `case_type_hard_gate_signed` were added, `secondary_peak_presence_or_absence` was added, `A.0a` exists, and `estimated_pass_rate_round1` is lowered to `0.28` at [§1/§5/§6](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:104).
- F3-LOW closed: R6/R7/R8 are present in §4, and §7 now names exact locator/station/tolerance/hazard requirements at [§4/§7](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:303).

Verdict: `APPROVE_PLAN_WITH_CHANGES`

Stage A.0a can proceed, but the two consistency defects above should be patched before downstream execution past A.0a/A.0b.
