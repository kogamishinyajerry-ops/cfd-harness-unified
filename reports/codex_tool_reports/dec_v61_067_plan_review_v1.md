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
/bin/zsh -lc 'git rev-parse 9a85b18 && git show --stat --oneline --no-patch 9a85b18' in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
9a85b18c8be6b98c6c2ba679e99ae2dd8afbd40c
9a85b18 [line-b] intake(impinging_jet): DEC-V61-067 Stage 0 · v1 draft (Type II, methodology v2.0 sixth-apply)

exec
/bin/zsh -lc "git show 9a85b18:knowledge/gold_standards/axisymmetric_impinging_jet.yaml | nl -ba | sed -n '1,260p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
exec
/bin/zsh -lc "git show 9a85b18:.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml | nl -ba | sed -n '1,260p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
     1	schema_version: 2
     2	case_id: axisymmetric_impinging_jet
     3	legacy_case_id: impinging_jet
     4	legacy_source_file: knowledge/gold_standards/impinging_jet.yaml
     5	source: "Computed: simpleFoam flat-plate extraction (cf_skin_friction); Literature: Cooper 1984 for impinging jet Nu correlation"
     6	literature_doi: "10.1016/j.ijheatfluidflow.2013.03.003"
     7	note: >
     8	  This case ran with simpleFoam (isothermal, no heat transfer). The extracted
     9	  nusselt_number=0.0042 is actually a local skin-friction coefficient (Cf) from
    10	  the flat-plate post-processing, not a true impinging-jet Nusselt number.
    11	  The Gold Standard ref_value=25.0 (Cooper 1984) requires buoyantFoam with
    12	  thermal boundary conditions — a different solver configuration.
    13	  This observable is INCOMPATIBLE with simpleFoam execution.
    14	physics_contract:
    15	  geometry_assumption: "Axisymmetric jet of diameter D impinging normal to a heated flat plate at stand-off distance H/D ~ 2-6; Cooper 1984 correlation requires thermal BCs on the plate"
    16	  reference_correlation_context: "Cooper 1984 Nu(r/D) correlation for impinging-jet heat transfer gives peak Nu ~ 25 in the stagnation zone at Re ~ 2.3e4. The ref_value in this YAML is **not** the true Cooper Nu (which is ~25); it is the adapter-observed Cf=0.0042 from a flat-plate extraction. The YAML's note: field is the existing disclosure of this mismatch."
    17	  physics_precondition:
    18	    - condition: "Solver has a thermal solve with plate at T_hot, jet inflow at T_cold (or equivalent) so a temperature gradient can be extracted at the plate"
    19	      satisfied_by_current_adapter: false
    20	      evidence_ref: "whitelist declares simpleFoam which is isothermal; no energy equation solved. Adapter has _generate_impinging_jet (src/foam_agent_adapter.py:4257+) that sets up a buoyantFoam-path case, but the whitelist configuration takes a simpleFoam path that never invokes this generator for the thermal observable."
    21	      consequence_if_unsatisfied: "No Nu can be computed from the solver output; the value stored as 'nusselt_number' is a flat-plate Cf borrowed from the skin-friction extractor path. PASS against ref_value=0.0042 only proves the adapter is self-consistent, not that the physics is correct."
    22	    - condition: "The ref_value in this YAML encodes the adapter's actual extraction (Cf=0.0042), NOT the literature Nu (~25)"
    23	      satisfied_by_current_adapter: true
    24	      evidence_ref: "YAML top-level `source` field explicitly calls out 'Computed: simpleFoam flat-plate extraction (cf_skin_friction)'. The Phase 7 gold revision (bf6cb5a and surrounding) replaced the Cooper Nu=25 with the Cf=0.0042 to make the comparison self-consistent under the isothermal solver. This is an honest remediation, but it means PASS on this case demonstrates extraction self-consistency only."
    25	  contract_status: "INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE — the observable is called nusselt_number but stores a cf_skin_friction value. No solver change is required to PASS, and no solver change will make it agree with the literature Nu=25 either without a different thermal setup. Future R-A-relabel slice could rename the observable to 'cf_skin_friction_at_plate' and update ref_value to match a Cf correlation; that would be a physics-valid remediation but is out of the current bounded-metadata scope."
    26	  precondition_last_reviewed: "2026-04-18 (EX-1-005 annotation slice)"
    27	relationships:
    28	  solver_reuse: impinging_jet
    29	  geometry_similarity:
    30	    reference_case: impinging_jet
    31	    similarity_type: TOPOLOGICAL
    32	  physics_analogy:
    33	    reference_case: impinging_jet
    34	    analogy_basis: legacy_alias
    35	    matched_dimensionless_group: Re
    36	observables:
    37	  - name: nusselt_number
    38	    description: "INCOMPATIBLE — simpleFoam isothermal run; cf_skin_friction extracted (Nu=0.0042 is Cf, not Nu)"
    39	    ref_value: 0.0042
    40	    unit: dimensionless
    41	    tolerance:
    42	      mode: relative
    43	      value: 0.15
    44	    notes: "This is cf_skin_friction from flat-plate post-processing. True impinging jet Nu requires buoyantFoam."

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
    10	#       Pre-Stage-A Codex review pending.
    11	
    12	case_id: axisymmetric_impinging_jet
    13	dec_id: DEC-V61-067
    14	case_number: 8  # canonical 8th case in the 10-case whitelist (impinging_jet)
    15	intake_authored_at: "2026-04-26"
    16	intake_author: "Claude Code (Opus 4.7, 1M context · Track B sixth-apply)"
    17	methodology_version: "v2.0"
    18	intake_version: 1
    19	codex_plan_review_verdict: PENDING
    20	
    21	# ============================================================================
    22	# §0 Why this case is being re-iterated (pre-existing state honesty)
    23	# ============================================================================
    24	preexisting_state_honesty: |
    25	  The current `knowledge/gold_standards/axisymmetric_impinging_jet.yaml` carries
    26	  a self-confessed broken contract:
    27	
    28	    contract_status: "INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE
    29	       — the observable is called nusselt_number but stores a cf_skin_friction
    30	       value (0.0042). No solver change is required to PASS, and no solver
    31	       change will make it agree with the literature Nu=25 either without a
    32	       different thermal setup."
    33	
    34	  The note: field still claims "simpleFoam isothermal run; cf_skin_friction
    35	  extracted (Nu=0.0042 is Cf, not Nu)", but the adapter dispatch path was
    36	  upgraded post-EX-1-005 (2026-04-18): `_generate_impinging_jet` now writes
    37	  a buoyantFoam-path case (src/foam_agent_adapter.py:674-676), AND
    38	  `_extract_jet_nusselt` (src/foam_agent_adapter.py:9613-9721) computes a
    39	  TRUE wall-normal temperature gradient via the 3-point one-sided stencil
    40	  (DEC-V61-042 fix), returning Nu_stagnation + Nu(r/D) profile + r-coords.
    41	
    42	  In other words: the EXTRACTOR is correct, but the GOLD YAML still encodes
    43	  the stale Cf=0.0042 sentinel from before DEC-V61-042 landed. The current
    44	  "PASS" verdict is therefore meaningless self-comparison — the comparator
    45	  matches a number against itself, not against literature physics.
    46	
    47	  V61-067 will:
    48	    1. Citation re-anchor the gold YAML to the actual Cooper et al. 1993
    49	       impinging-jet measurement (NOT Cooper 1984 — see §3 Cooper-citation
    50	       audit; the whitelist's "Cooper et al. 1984" label is itself suspect)
    51	       OR a publicly-archived equivalent (Behnad et al. 2013 OR Baughn &
    52	       Shimizu 1989, both publicly accessible per JFE-style archives).
    53	    2. Promote the existing Nu(r/D) profile output to a Type II observable
    54	       family (one HARD_GATED stagnation Nu + one HARD_GATED profile shape
    55	       gate + ≥1 conservation invariant + ≥1 advisory).
    56	    3. Verify that the buoyantFoam dispatch + wall-gradient stencil actually
    57	       deliver Nu_stagnation in the Cooper-correlation band (likely needs
    58	       a Re mismatch audit: whitelist sets Re=10000, but most published
    59	       impinging-jet correlations use Re=23000 or higher).
    60	    4. Document the Re/h-over-d/Pr mismatches honestly in the gold YAML
    61	       §physics_contract.note like V61-060 did for the Pandey & Schumacher
    62	       benchmark.
    63	
    64	# ============================================================================
    65	# §1 Classification (F5-M1 hard gate, §3b — NO mid-arc Type change allowed)
    66	# ============================================================================
    67	case_type: II  # 1 HARD_GATED stagnation scalar + 1 HARD_GATED profile family
    68	               # + 1 NON_TYPE_HARD_INVARIANT (monotonic decay) + 1 PROVISIONAL
    69	case_type_rationale: |
    70	  PRIMARY SCALAR GATE (1):
    71	    1. nusselt_stagnation_at_r_d_zero — HEADLINE — Nu at the radial bin
    72	       closest to r=0 (axisymmetric stagnation point), extracted by the
    73	       existing `_extract_jet_nusselt` 3-point wall-normal stencil. Cooper
    74	       correlation: Nu_stag ~ 25-40 at Re=23000 h/d=2 (citation pending §3
    75	       audit). For Re=10000 h/d=2 the expected value is lower; gold YAML
    76	       must be re-anchored to a Re=10000 source OR the whitelist Re must
    77	       be bumped to match the correlation.
    78	
    79	  PROFILE/QUALITATIVE GATES:
    80	    2. nusselt_profile_r_over_d — HARD_GATED — Nu(r/D) shape match at 5+
    81	       radial stations (r/D ∈ {0, 0.5, 1.0, 1.5, 2.0}). Reuses the existing
    82	       `nusselt_number_profile` + `nusselt_number_profile_r` adapter outputs.
    83	       Profile-mode comparator: per-station tolerance 25-30% (loose because
    84	       Cooper-style correlations are not point-precise; the SHAPE is the
    85	       gate, not point values). The DEC-V61-044 NACA Cp pattern is the
    86	       reference implementation.
    87	
    88	  CONSERVATION INVARIANT (NON_TYPE_HARD_INVARIANT, blocks on violation but
    89	  excluded from primary_gate_count denominator per Stage C.2 comparator):
    90	    3. nu_monotonic_decay_from_stagnation — Nu(r/D) must be monotonically
    91	       non-increasing from the stagnation peak outward through r/D ≤ 1.5.
    92	       This is a known physical invariant (jet impingement decays radially
    93	       in the wall-jet zone; the secondary peak at r/D ≈ 2 from vortex
    94	       breakdown only matters at high Re). Failure ⇒ solver chose an
    95	       unphysical secondary maximum near the axis or the extractor binned
    96	       cells incorrectly. tolerance: absolute, value=0 (any non-monotone
    97	       step violates).
    98	
    99	  PROVISIONAL_ADVISORY (NOT a physics gate):
   100	    4. y_plus_first_cell_at_plate — PROVISIONAL — wall-resolution diagnostic
   101	       at the impingement plate. Threshold band: y+ < 5 desired (low-Re
   102	       wall-resolved); y+ < 30 acceptable (wall-function regime). Pure
   103	       diagnostic, not enforced.
   104	
   105	primary_gate_count: 2  # nusselt_stagnation_at_r_d_zero + nusselt_profile_r_over_d
   106	                       # The conservation invariant + advisory are excluded.
   107	
   108	# ============================================================================
   109	# §2 Headline observable — citation provenance (F1-M2 hard gate)
   110	# ============================================================================
   111	headline_observable: nusselt_stagnation_at_r_d_zero
   112	headline_reference: PENDING_CITATION_AUDIT  # see §3
   113	headline_reference_value: PENDING_CITATION_AUDIT
   114	headline_reference_tolerance: 0.30  # widened from typical 0.15 to absorb
   115	                                    # Re/h-over-d mismatch + steady-vs-RANS
   116	                                    # vs unsteady RKE, like V61-060 did for RBC
   117	
   118	# ============================================================================
   119	# §3 Citation provenance audit (BLOCKING — must close before Stage A)
   120	# ============================================================================
   121	citation_audit:
   122	  whitelist_claim:
   123	    label: "Cooper et al. 1984 / Behnad et al. 2013"
   124	    doi: "10.1016/j.ijheatfluidflow.2013.03.003"
   125	    audit_status: SUSPECT
   126	    audit_reason: |
   127	      "Cooper 1984" does not match any well-known impinging-jet author/date.
   128	      The canonical impinging-jet experimental dataset commonly cited in
   129	      OpenFOAM tutorials and benchmark suites is:
   130	        - Cooper, D., Jackson, D.C., Launder, B.E., Liao, G.X. (1993)
   131	          "Impinging jet studies for turbulence model assessment — I.
   132	          Flow-field experiments", Int. J. Heat Mass Transfer 36(10),
   133	          2675-2684. DOI: 10.1016/S0017-9310(05)80204-2
   134	        - Baughn, J.W., Shimizu, S. (1989) "Heat transfer measurements
   135	          from a surface with uniform heat flux and an impinging jet",
   136	          ASME J. Heat Transfer 111(4), 1096-1098. DOI: 10.1115/1.3250776
   137	      Whitelist may have transposed digits or compressed citations. Per
   138	      V61-060 lesson: a wrong citation that "happened to PASS" is the
   139	      worst kind of stale provenance.
   140	    closure_action_required: |
   141	      Stage A.0 MUST resolve the actual paper(s) hosting the Re=10000,
   142	      h/d=2 Nu_stag value used by the gold YAML. Acceptance criterion:
   143	      a publicly accessible document with a Table or Figure number
   144	      locator (V61-060 set this precedent). If the original Cooper 1984
   145	      DOI resolves to the wrong paper (V61-060 pattern), pivot to one
   146	      of the publicly-archived alternatives above.
   147	  doi_resolves_to: NOT_VERIFIED  # Stage A.0 must run a curl/fetch on the DOI
   148	
   149	# ============================================================================
   150	# §4 Risk register (pre-Stage-A, surfaced for Codex review)
   151	# ============================================================================
   152	risk_register:
   153	  R1_re_mismatch:
   154	    severity: HIGH
   155	    description: |
   156	      Whitelist Re=10000 is unusual for impinging-jet benchmarks. Cooper
   157	      1993 ran Re=23000. Behnad 2013 may have multiple Re values. If the
   158	      gold YAML's ref_value was correlated from Re=23000 data and applied
   159	      blindly to Re=10000 simulation, deviation will be unbounded. Stage
   160	      A.0 must confirm Re consistency between gold ref + whitelist task_spec.
   161	    mitigation: |
   162	      (a) Verify Cooper 1993 has a Re=10000 row, OR
   163	      (b) Bump whitelist Re=10000 → 23000 to match the correlation, OR
   164	      (c) Use a Re-agnostic Nu correlation (Schlichting Nu/Re^0.5 = const
   165	          near stagnation) and document the assumption.
   166	  R2_h_over_d_mismatch:
   167	    severity: MED
   168	    description: |
   169	      Whitelist h/d=2 is a common stand-off. Cooper 1993 and Baughn/Shimizu
   170	      1989 both used h/d=2 OR h/d=6; verify alignment. h/d=2 puts the
   171	      stagnation in the potential core (Nu peaks); h/d=6 is post-core
   172	      (different Nu(r) shape). Stage A.0 must confirm.
   173	    mitigation: |
   174	      Lock h/d to whatever the chosen citation uses; if no overlap, hold
   175	      Stage A on a follow-up.
   176	  R3_turbulence_model_choice:
   177	    severity: MED
   178	    description: |
   179	      Whitelist sets `turbulence_model: k-omega SST`. For impinging jets
   180	      this is reasonable (k-ε notoriously over-predicts Nu near stagnation
   181	      due to round-jet stagnation anomaly). Adapter must actually emit
   182	      k-omega SST, not silently fall back to k-ε. Verify at Stage A.
   183	    mitigation: |
   184	      Stage A.5 alias-parity test (V61-060 lesson) must include a
   185	      turbulence-model-emitted-vs-declared check.
   186	  R4_buoyantFoam_dispatch_overlap:
   187	    severity: LOW
   188	    description: |
   189	      Adapter at src/foam_agent_adapter.py:676 hardcodes `solver_name =
   190	      "buoyantFoam"` for IMPINGING_JET, overriding the whitelist's
   191	      `simpleFoam` declaration. This is intentional (impinging jet needs
   192	      thermal) but contradicts whitelist; CASE_ID_TO_SOLVER in
   193	      src/auto_verifier/config.py:69 also hardcodes simpleFoam, creating
   194	      a 2-source-of-truth ambiguity.
   195	    mitigation: |
   196	      Stage A clean-up: align both the whitelist and CASE_ID_TO_SOLVER to
   197	      buoyantFoam, OR document the override path explicitly in the gold
   198	      YAML §physics_contract.note.
   199	  R5_alias_map_staleness_post_v61_060:
   200	    severity: HIGH
   201	    description: |
   202	      RETRO-V61-060 addendum: alias-map staleness was the #1 post-R3
   203	      defect. Any case_name change at Stage A.0 (e.g. citation suffix
   204	      added) MUST atomically update both `_TASK_NAME_TO_CASE_ID_ALIASES`
   205	      maps (src/foam_agent_adapter.py:247 + src/auto_verifier/config.py:30).
   206	      A.0 + A.3 should be ONE commit.
   207	    mitigation: |
   208	      Pre-commit check: if intake §3 demands a case_name rename, the same
   209	      commit MUST touch both alias maps. Codex pre-Stage-A review must
   210	      enforce this.
   211	
   212	# ============================================================================
   213	# §5 Estimated Codex round budget + pass-rate (for self-pass-rate calibration)
   214	# ============================================================================
   215	codex_budget_rounds: 5  # R5 normal checkpoint, R6 halt-risk, R7 force abandon
   216	estimated_pass_rate_round1: 0.40  # Lower than V61-060 (0.55) because the
   217	                                  # citation audit (§3) is genuinely unresolved
   218	                                  # — there's a non-trivial probability that
   219	                                  # Stage A.0 surfaces "no clean publicly-archived
   220	                                  # benchmark for Re=10000 h/d=2", forcing a
   221	                                  # whitelist Re bump (architectural change) or
   222	                                  # re-classification as PHYSICS_FIDELITY_GAP.
   223	
   224	# ============================================================================
   225	# §6 Stage A → E preview (subject to Codex pre-Stage-A review)
   226	# ============================================================================
   227	stage_preview:
   228	  A_0_citation_pivot:
   229	    purpose: Resolve §3 citation audit. Replace stale Cf=0.0042 sentinel.
   230	    deliverables:
   231	      - Verified DOI + page/table/figure locator OR pivot to alternate paper
   232	      - knowledge/gold_standards/axisymmetric_impinging_jet.yaml rewrite
   233	        (4 observables, schema_v2, Type II gate_status taxonomy)
   234	      - knowledge/whitelist.yaml `name` rename (if needed) → atomic with
   235	        BOTH alias map updates (R5 mitigation)
   236	  A_1_to_A_n_canonical_contract_repair:
   237	    purpose: Confirm adapter dispatch + extractor outputs match the new gold
   238	    deliverables:
   239	      - Whitelist+CASE_ID_TO_SOLVER alignment (R4 mitigation)
   240	      - Turbulence model emit-vs-declared parity test (R3 mitigation)
   241	      - Verify _extract_jet_nusselt's profile output matches the new
   242	        observable schema (Stage A is not expected to need extractor changes;
   243	        the extractor is already DEC-V61-042-correct)
   244	  B_extractors:
   245	    purpose: Add monotonic-decay invariant extractor; extend profile gate
   246	    deliverables:
   247	      - src/impinging_jet_extractors.py (NEW) with extract_nu_monotonicity
   248	      - tests/test_impinging_jet_extractors.py (≥20 unit tests)
   249	      - register in src/_plane_assignment.py SSOT
   250	  C_preflight_comparator_riskflags:
   251	    purpose: Atomic preflight + comparator + risk_flag registry
   252	    deliverables:
   253	      - knowledge/schemas/risk_flag_registry.yaml: 4-5 new IJ-specific flags
   254	        from §4 risk_register (R1, R2, R3, R5)
   255	      - .planning/case_profiles/axisymmetric_impinging_jet.yaml backfill
   256	      - Comparator branch reuse (V61-060 NON_TYPE_HARD_INVARIANT path)
   257	  D_ui_surface:
   258	    purpose: 4-card metrics_impinging_jet block in CompareTab + audit allowlist
   259	    deliverables:
   260	      - ui/backend/services/comparison_report.py: metrics_impinging_jet

exec
/bin/zsh -lc "git show 9a85b18:src/foam_agent_adapter.py | nl -ba | sed -n '660,705p;9610,9735p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
exec
/bin/zsh -lc "git show 9a85b18:knowledge/whitelist.yaml | nl -ba | sed -n '1,260p' | rg -n -C 6 \"impinging_jet|Cooper|Behnad\"" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
   660	                    whitelist_turb = _load_whitelist_turbulence_model(task_spec.name)
   661	                    if whitelist_turb in ("laminar", "kOmegaSST", "kEpsilon"):
   662	                        turbulence_model = whitelist_turb
   663	                    else:
   664	                        turbulence_model = self._turbulence_model_for_solver(
   665	                            solver_name, task_spec.geometry_type, task_spec.Re
   666	                        )
   667	                    self._generate_circular_cylinder_wake(case_host_dir, task_spec, turbulence_model)
   668	            elif task_spec.geometry_type == GeometryType.AIRFOIL:
   669	                solver_name = "simpleFoam"
   670	                turbulence_model = self._turbulence_model_for_solver(
   671	                    solver_name, task_spec.geometry_type, task_spec.Re
   672	                )
   673	                self._generate_airfoil_flow(case_host_dir, task_spec, turbulence_model)
   674	            elif task_spec.geometry_type == GeometryType.IMPINGING_JET:
   675	                self._generate_impinging_jet(case_host_dir, task_spec)
   676	                solver_name = "buoyantFoam"
   677	            elif task_spec.geometry_type == GeometryType.SIMPLE_GRID:
   678	                # LDC: canonical name match, no Re-heuristic (Codex MEDIUM: the
   679	                # `Re < 2300` fallback was too broad — any SIMPLE_GRID laminar
   680	                # case would get routed through the cavity generator, silent
   681	                # wrong-physics risk).
   682	                if self._is_lid_driven_cavity_case(task_spec, "simpleFoam"):
   683	                    self._generate_lid_driven_cavity(case_host_dir, task_spec)
   684	                    solver_name = "simpleFoam"
   685	                else:
   686	                    solver_name = "simpleFoam"
   687	                    turbulence_model = self._turbulence_model_for_solver(
   688	                        solver_name, task_spec.geometry_type, task_spec.Re
   689	                    )
   690	                    self._generate_steady_internal_flow(case_host_dir, task_spec, turbulence_model)
   691	            else:
   692	                self._generate_lid_driven_cavity(case_host_dir, task_spec)
   693	                solver_name = "simpleFoam"
   694	
   695	            # 5. 执行 blockMesh
   696	            blockmesh_ok, blockmesh_log = self._docker_exec(
   697	                "blockMesh", case_cont_dir, self.BLOCK_MESH_TIMEOUT,
   698	            )
   699	            if not blockmesh_ok:
   700	                return self._fail(
   701	                    f"blockMesh failed:\n{blockmesh_log}",
   702	                    time.monotonic() - t0,
   703	                    raw_output_path=raw_output_path,
   704	                )
   705	
  9610	    # ------------------------------------------------------------------
  9611	
  9612	    @staticmethod
  9613	    def _extract_jet_nusselt(
  9614	        cxs: List[float],
  9615	        cys: List[float],
  9616	        t_vals: List[float],
  9617	        task_spec: TaskSpec,
  9618	        key_quantities: Dict[str, Any],
  9619	    ) -> Dict[str, Any]:
  9620	        """Impinging Jet: 从壁面温度梯度计算局部 Nusselt number。
  9621	
  9622	        Gold Standard: Nu ≈ 25 at stagnation (r/D=0), decays to ~12 at r/D=1.
  9623	
  9624	        DEC-V61-042: previously this extractor differenced plate-face
  9625	        temperatures RADIALLY (dT/dr) — which is ≈0 by symmetry on a
  9626	        fixedValue-T plate, giving the catastrophic 0.00417 underread
  9627	        (−6000× vs gold 25.0). The fix bins cells by radial position r,
  9628	        then at each bin applies a wall-normal 3-point one-sided stencil
  9629	        against the plate BC (wall_coord_plate, T_plate plumbed through
  9630	        task_spec.boundary_conditions by _generate_impinging_jet).
  9631	
  9632	        Fails closed when BC metadata is missing — MISSING_TARGET_QUANTITY
  9633	        will fire at the comparator rather than a silent garbage read.
  9634	        """
  9635	        if not cxs or not cys or not t_vals:
  9636	            return key_quantities
  9637	
  9638	        bc = task_spec.boundary_conditions or {}
  9639	        wall_coord_plate = bc.get("wall_coord_plate")
  9640	        T_plate = bc.get("T_plate")
  9641	        T_inlet = bc.get("T_inlet")
  9642	        bc_type = bc.get("wall_bc_type")
  9643	        D_nozzle = bc.get("D_nozzle")
  9644	        if (
  9645	            wall_coord_plate is None or T_plate is None or T_inlet is None
  9646	            or bc_type is None or D_nozzle is None
  9647	        ):
  9648	            # Fail closed — absence of nusselt_number is the signal.
  9649	            # (Codex DEC-042 round-1 FLAG: don't leak extractor-internal
  9650	            # state into measurement key_quantities.)
  9651	            return key_quantities
  9652	
  9653	        Delta_T = float(T_inlet) - float(T_plate)
  9654	        if abs(Delta_T) < 1e-10:
  9655	            return key_quantities
  9656	
  9657	        from collections import defaultdict
  9658	        from src.wall_gradient import extract_wall_gradient, BCContractViolation
  9659	
  9660	        # Bin cells by radial position r = |cx| (axisymmetric, axis at cx=0).
  9661	        # Within each bin, we have cells at different cy (jet-axial) positions;
  9662	        # the 3-point stencil operates on that cy-column against the plate
  9663	        # BC at cy = wall_coord_plate.
  9664	        unique_r = sorted({round(abs(cx), 4) for cx in cxs})
  9665	        r_cols: Dict[float, List[Tuple[float, float]]] = defaultdict(list)
  9666	        for i in range(min(len(cxs), len(cys), len(t_vals))):
  9667	            r_key = round(abs(cxs[i]), 4)
  9668	            r_cols[r_key].append((cys[i], t_vals[i]))
  9669	
  9670	        sorted_r: List[float] = []
  9671	        Nu_profile: List[float] = []
  9672	        wall_cy = float(wall_coord_plate)
  9673	        for r_key in unique_r:
  9674	            column = r_cols.get(r_key, [])
  9675	            if len(column) < 2:
  9676	                continue
  9677	            # Plate sits at the MAX cy in the domain (jet hits top). The
  9678	            # wall_gradient stencil validates wall_coord < cell_coord, so
  9679	            # we flip into a wall-normal coordinate n = wall_cy - cy where
  9680	            # the wall is at n=0 and interior cells at n>0. We take |grad|
  9681	            # afterwards so the sign flip from dn/dcy = −1 washes out.
  9682	            interior = [
  9683	                (wall_cy - cy, t) for (cy, t) in column if cy < wall_cy
  9684	            ]
  9685	            if len(interior) < 2:
  9686	                continue
  9687	            try:
  9688	                grad = extract_wall_gradient(
  9689	                    wall_coord=0.0,
  9690	                    wall_value=float(T_plate),
  9691	                    coords=[n for n, _ in interior],
  9692	                    values=[t for _, t in interior],
  9693	                    bc_type=bc_type,
  9694	                    bc_gradient=bc.get("wall_bc_gradient"),
  9695	                )
  9696	            except BCContractViolation:
  9697	                continue
  9698	            # Stagnation Nu definition: h·D/k = D·|dT/dn|/ΔT (dimensionless).
  9699	            # sign of grad depends on cold-plate hot-jet orientation; take |·|.
  9700	            Nu = float(D_nozzle) * abs(grad) / Delta_T
  9701	            sorted_r.append(r_key)
  9702	            Nu_profile.append(Nu)
  9703	
  9704	        if Nu_profile:
  9705	            # Stagnation Nu at r ≈ 0 is the first (smallest r) bin.
  9706	            key_quantities["nusselt_number"] = Nu_profile[0]
  9707	            key_quantities["nusselt_number_source"] = "wall_gradient_stencil_3pt"
  9708	            key_quantities["nusselt_number_profile"] = Nu_profile
  9709	            key_quantities["nusselt_number_profile_r"] = sorted_r
  9710	            # DEC-V61-042 round-1 FLAG: previous code silently clamped
  9711	            # Nu to [0, 500]. Clamping hides runaway — e.g. a diverged
  9712	            # solver producing spurious 1e6 gradients would masquerade
  9713	            # as a benign 500. Instead, surface a HAZARD flag when a
  9714	            # physically implausible value appears so the UI and
  9715	            # comparator can treat it honestly. The threshold is
  9716	            # generous (500× gold stag Nu≈25) — any hit is a red flag.
  9717	            Nu_stag = Nu_profile[0]
  9718	            if not (0.0 <= Nu_stag <= 500.0):
  9719	                key_quantities["nusselt_number_unphysical_magnitude"] = True
  9720	
  9721	        return key_quantities
  9722	
  9723	    # ------------------------------------------------------------------
  9724	    # NACA Airfoil — 提取压力系数分布 Cp
  9725	    # ------------------------------------------------------------------
  9726	
  9727	    @staticmethod
  9728	    def _extract_airfoil_cp(
  9729	        cxs: List[float],
  9730	        czs: List[float],
  9731	        p_vals: List[float],
  9732	        task_spec: TaskSpec,
  9733	        key_quantities: Dict[str, Any],
  9734	    ) -> Dict[str, Any]:
  9735	        """NACA Airfoil: 提取翼型表面压力系数分布 Cp。

 succeeded in 0ms:
200-   200	        # NOTE: y_plus=100 value 22.8 also looks anomalous (log-law gives ~16.4,
201-   201	        # Moser Re_τ=180 centerline u+≈18.3). Out of audit §5.2 scope; noted for
202-   202	        # follow-up audit pass.
203-   203	        - {y_plus: 100.0, u_plus: 22.8}
204-   204	      tolerance: 0.05  # 5% 相对误差 (Moser DNS numerical uncertainty)
205-   205	
206:   206	  - id: impinging_jet
207-   207	    name: "Axisymmetric Impinging Jet (Re=10000)"
208:   208	    reference: "Cooper et al. 1984 / Behnad et al. 2013"
209-   209	    doi: "10.1016/j.ijheatfluidflow.2013.03.003"
210-   210	    flow_type: EXTERNAL
211-   211	    geometry_type: IMPINGING_JET
212-   212	    compressibility: INCOMPRESSIBLE
213-   213	    steady_state: STEADY
214-   214	    solver: simpleFoam
215-   215	    turbulence_model: k-omega SST
216-   216	    parameters:
217-   217	      Re: 10000
218-   218	      nozzle_diameter: 0.05
219-   219	      h_over_d: 2.0  # 喷口到板面距离 / 直径
220-   220	    # Gate Q-new Case 9 · HOLD per Kogami 2026-04-20: audit flagged Nu@r/d=0 = 25 vs
221:   221	    # Behnad 2013 ~110-130, but 4-5× discrepancy is too large to edit without reading
222:   222	    # Behnad et al. 2013 (DOI 10.1016/j.ijheatfluidflow.2013.03.003) directly and
223-   223	    # confirming (Re=10000, h/d=2) was the configuration cited. Possible mis-match:
224-   224	    # confined-jet vs free-jet, different h/d, different Re. Literature re-source
225-   225	    # pending. Values below are provisional; may change in future DEC.
226-   226	    gold_standard:
227-   227	      quantity: nusselt_number
228-   228	      description: "冲击面局部努塞尔数分布 (PROVISIONAL — Gate Q-new Case 9 hold)"

exec
/bin/zsh -lc "git show 9a85b18:.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml | nl -ba | sed -n '260,360p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
   260	      - ui/backend/services/comparison_report.py: metrics_impinging_jet
   261	        (mirrors metrics_rbc / metrics_dhc pattern)
   262	      - ui/frontend/src/pages/learn/case_detail/CompareTab.tsx: rendering
   263	        branch (NEW architecture per main refactor — sub-component, not
   264	        the monolithic LearnCaseDetailPage.tsx that V61-060 wrote against)
   265	      - scripts/phase5_audit_run.py: secondary_scalars allowlist
   266	  E_live_run_dec_closeout:
   267	    purpose: Live OpenFOAM run + DEC frontmatter + Notion sync + PR
   268	    deliverables:
   269	      - live buoyantFoam run via phase5_audit_run.py axisymmetric_impinging_jet
   270	      - audit_real_run_measurement.yaml regen
   271	      - .planning/decisions/2026-04-2X_v61_067_impinging_jet_multidim.md
   272	      - PR to main
   273	
   274	# ============================================================================
   275	# §7 Acceptance criteria (definition of done — F1-M2 two-tier close gate)
   276	# ============================================================================
   277	acceptance_criteria:
   278	  i_codex_arc_complete: |
   279	    Final Codex round returns APPROVE OR APPROVE_WITH_COMMENTS, OR
   280	    CHANGES_REQUIRED with all findings closed verbatim per the 5-condition
   281	    exception envelope (CLAUDE.md).
   282	  ii_headline_validated_or_honestly_failed: |
   283	    EITHER: live-run Nu_stagnation falls within ±30% of the chosen literature
   284	    band — primary gate PASS; OR: Nu_stagnation falls outside the band and
   285	    the DEC documents the physics-fidelity gap explicitly (V61-063 / V61-066
   286	    / V61-060 closeout pattern: METHODOLOGY_COMPLETE_PHYSICS_FIDELITY_GAP_DOCUMENTED).
   287	  iii_profile_shape_validated: |
   288	    Nu(r/D) profile across r/D ∈ {0, 0.5, 1.0, 1.5, 2.0} matches Cooper-style
   289	    monotonic decay; the conservation invariant gate must pass UNLESS the
   290	    physics-fidelity gap explanation explicitly accounts for non-monotonic
   291	    behaviour (e.g. high-Re secondary peak from vortex breakdown).
   292	  iv_invariant_count_excluded_from_pass_fraction: |
   293	    Per V61-060 Stage C.2 comparator semantics: NON_TYPE_HARD_INVARIANT
   294	    blocks verdict on violation but is excluded from primary_gate_count
   295	    denominator. UI must surface the invariant card with the appropriate
   296	    "守恒不变量" badge (rose/emerald state-aware per V61-060 R6 fix).
   297	  v_alias_map_atomic_with_case_name_rename: |
   298	    Per RETRO-V61-060 addendum: any A.0 case_name rename MUST be in the
   299	    same commit as both `_TASK_NAME_TO_CASE_ID_ALIASES` map updates.
   300	
   301	# ============================================================================
   302	# §8 Out of scope (will not be addressed in this DEC)
   303	# ============================================================================
   304	out_of_scope:
   305	  - Cross-jet-array configurations (single-jet-only)
   306	  - Compressible jet effects (Ma < 0.3 assumed)
   307	  - Confined-jet vs free-jet variants (free-jet only per existing whitelist
   308	    geometry h_over_d=2)
   309	  - Heat-transfer-coefficient measurement at the nozzle exit (only plate
   310	    Nu is in scope)
   311	  - Multi-Re sweep (single Re=10000 OR Re=23000 after §3 audit; no profile
   312	    over Re — that would be a follow-up DEC)

codex
I have the intake and gold-state context. Next I’m checking the actual generator/config paths behind the intake’s assumptions, because a few review points depend on whether the code already emits a wedge/axisymmetric thermal case or just a generic 3D block.
exec
/bin/zsh -lc 'git show 9a85b18:src/foam_agent_adapter.py | nl -ba | rg -n -C 6 "def _generate_impinging_jet|cyclicAMI|wedge|axisymmetric|IMPINGING_JET|wall_coord_plate|D_nozzle|T_plate|T_inlet"' in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
253-   253	    "Fully Developed Turbulent Pipe Flow": "duct_flow",
254-   254	    "Rayleigh-Benard Convection (Ra=10^6)": "rayleigh_benard_convection",
255-   255	    "Rayleigh-Bénard Convection (Ra=10^6)": "rayleigh_benard_convection",
256-   256	    "Differential Heated Cavity (Natural Convection)": "differential_heated_cavity",
257-   257	    "Differential Heated Cavity (Natural Convection, Ra=10^6 benchmark)": "differential_heated_cavity",
258-   258	    "NACA 0012 Airfoil External Flow": "naca0012_airfoil",
259:   259	    "Axisymmetric Impinging Jet (Re=10000)": "axisymmetric_impinging_jet",
260-   260	    "Fully Developed Plane Channel Flow (DNS)": "fully_developed_plane_channel_flow",
261-   261	}
262-   262	
263-   263	
264-   264	def _normalize_task_name_to_case_id(task_name: str) -> str:
265-   265	    """Resolve a TaskSpec.name (which may be a human-readable display title
--
668-   668	            elif task_spec.geometry_type == GeometryType.AIRFOIL:
669-   669	                solver_name = "simpleFoam"
670-   670	                turbulence_model = self._turbulence_model_for_solver(
671-   671	                    solver_name, task_spec.geometry_type, task_spec.Re
672-   672	                )
673-   673	                self._generate_airfoil_flow(case_host_dir, task_spec, turbulence_model)
674:   674	            elif task_spec.geometry_type == GeometryType.IMPINGING_JET:
675-   675	                self._generate_impinging_jet(case_host_dir, task_spec)
676-   676	                solver_name = "buoyantFoam"
677-   677	            elif task_spec.geometry_type == GeometryType.SIMPLE_GRID:
678-   678	                # LDC: canonical name match, no Re-heuristic (Codex MEDIUM: the
679-   679	                # `Re < 2300` fallback was too broad — any SIMPLE_GRID laminar
680-   680	                # case would get routed through the cavity generator, silent
--
5546-  5546	
5547-  5547	// ************************************************************************* //
5548-  5548	""",
5549-  5549	                encoding="utf-8",
5550-  5550	            )
5551-  5551	
5552:  5552	    def _generate_impinging_jet(self, case_dir: Path, task_spec: TaskSpec) -> None:
5553-  5553	        """Generate impinging jet case files (buoyantFoam steady, Boussinesq).
5554-  5554	
5555-  5555	        Uses buoyantFoam with Boussinesq approximation for thermal fields.
5556-  5556	        Hot jet inlet (310K) impinges on cold plate (290K).
5557-  5557	        """
5558-  5558	        (case_dir / "system").mkdir(parents=True, exist_ok=True)
--
5564-  5564	        h_over_d = 2.0
5565-  5565	        H = h_over_d * D
5566-  5566	        U_bulk = 1.0
5567-  5567	        nu_val = U_bulk * D / Re
5568-  5568	
5569-  5569	        # Thermal parameters (Boussinesq)
5570:  5570	        T_inlet = 310.0   # hot jet
5571:  5571	        T_plate = 290.0   # cold impingement plate
5572-  5572	        T_mean = 300.0    # reference
5573-  5573	        Cp = 1005.0
5574-  5574	        beta = 1.0 / T_mean
5575-  5575	        Pr = 0.71
5576-  5576	        mu_val = nu_val  # dynamic viscosity for Boussinesq
5577-  5577	
5578-  5578	        # Enthalpy: h = Cp*(T - T_mean)
5579:  5579	        h_inlet = Cp * (T_inlet - T_mean)   # 10050
5580:  5580	        h_plate = Cp * (T_plate - T_mean)   # -10050
5581-  5581	        h_internal = 0.0                     # mean field starts at T_mean
5582-  5582	
5583-  5583	        # Domain: r=[0, 5D], z=[z_min, z_max]; split at z=0 for planar faces
5584-  5584	        r_max = 5.0 * D
5585-  5585	        z_min = -D / 2
5586-  5586	        z_split = 0.0
--
5600-  5600	        # Plate is at the upper face of the upper block (patch `plate`,
5601-  5601	        # faces (8 9 10 11) at jet-axial coord = z_max). The extractor
5602-  5602	        # reads cells by cy (jet-axial coord in OpenFOAM's y-slot) and
5603-  5603	        # treats the wall as cy = max(cys), matching z_max here.
5604-  5604	        if task_spec.boundary_conditions is None:
5605-  5605	            task_spec.boundary_conditions = {}
5606:  5606	        task_spec.boundary_conditions["D_nozzle"] = D
5607:  5607	        task_spec.boundary_conditions["T_plate"] = T_plate
5608:  5608	        task_spec.boundary_conditions["T_inlet"] = T_inlet
5609:  5609	        task_spec.boundary_conditions["wall_coord_plate"] = z_max
5610-  5610	        task_spec.boundary_conditions["wall_bc_type"] = "fixedValue"
5611-  5611	
5612-  5612	        (case_dir / "system" / "blockMeshDict").write_text(
5613-  5613	            f"""/*--------------------------------*- C++ -*---------------------------------*\\
5614-  5614	| =========                 |                                                 |
5615-  5615	| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
--
6198-  6198	dimensions      [0 0 0 1 0 0 0];
6199-  6199	
6200-  6200	internalField   uniform {T_mean:.6g};
6201-  6201	
6202-  6202	boundaryField
6203-  6203	{{
6204:  6204	    inlet           {{ type fixedValue; value uniform {T_inlet:.6g}; }}
6205:  6205	    plate           {{ type fixedValue; value uniform {T_plate:.6g}; }}
6206-  6206	    outer           {{ type inletOutlet; inletValue uniform {T_mean:.6g}; value uniform {T_mean:.6g}; }}
6207-  6207	    axis            {{ type empty; }}
6208-  6208	    front           {{ type empty; }}
6209-  6209	    back            {{ type empty; }}
6210-  6210	}}
6211-  6211	
--
6396-  6396	                physical_points=physical_points,
6397-  6397	                fields=["T", "U"],
6398-  6398	                axis="x",
6399-  6399	                header_comment=(
6400-  6400	                    f"Impinging jet plate probes at z={probe_z}m above plate "
6401-  6401	                    f"(plate z=0), {len(rod_values)} gold r/d coords (D={D:g}m, "
6402:  6402	                    f"T_inlet={T_inlet:g}K, T_plate={T_plate:g}K; "
6403-  6403	                    f"Nu derivation via wall-gradient post-processing TBD)"
6404-  6404	                ),
6405-  6405	            )
6406-  6406	
6407-  6407	    def _generate_airfoil_flow(
6408-  6408	        self, case_dir: Path, task_spec: TaskSpec, turbulence_model: str = "kOmegaSST"
--
8481-  8481	            and task_spec.Re >= 2300
8482-  8482	        ):
8483-  8483	            key_quantities = self._extract_flat_plate_cf(
8484-  8484	                cxs, cys, u_vecs, task_spec, key_quantities
8485-  8485	            )
8486-  8486	
8487:  8487	        # Impinging Jet: IMPINGING_JET -> nusselt_number
8488:  8488	        elif geom == GeometryType.IMPINGING_JET:
8489-  8489	            t_path = latest_dir / "T"
8490-  8490	            if t_path.exists():
8491-  8491	                t_vals = self._read_openfoam_scalar_field(t_path)
8492-  8492	                key_quantities = self._extract_jet_nusselt(
8493-  8493	                    cxs, cys, t_vals, task_spec, key_quantities
8494-  8494	                )
--
8892-  8892	        task_spec: TaskSpec,
8893-  8893	        key_quantities: Dict[str, Any],
8894-  8894	    ) -> Dict[str, Any]:
8895-  8895	        """If postProcessing/sets/.../plateProbes_T.xy is present, derive
8896-  8896	        Nu from T at the probe points 1mm above the impingement plate.
8897-  8897	
8898:  8898	        Nu = |T_probe - T_plate| · D / (Δz · ΔT_ref)
8899-  8899	
8900:  8900	        where ΔT_ref = T_inlet - T_plate = 20K and Δz = 0.001m match the
8901-  8901	        generator constants (see _generate_impinging_jet). The stagnation
8902-  8902	        probe (smallest r) populates `nusselt_number`; the full profile
8903-  8903	        populates `nusselt_number_profile`.
8904-  8904	
8905-  8905	        Sign convention: absolute value — Nu is a magnitude in all common
8906-  8906	        impinging-jet conventions, regardless of heat-flux direction.
8907-  8907	        """
8908-  8908	        points = _try_load_sampledict_output(case_dir, "plateProbes", "T")
8909-  8909	        if not points:
8910-  8910	            return key_quantities
8911-  8911	        # DEC-V61-042 round-1 FLAG: read BC metadata from task_spec
8912:  8912	        # instead of hard-coding T_plate=290/T_inlet=310/D=0.05 — keeps
8913-  8913	        # this dormant second measurement path consistent with the
8914-  8914	        # primary _extract_jet_nusselt, so if the sampleDict path is
8915-  8915	        # ever reactivated (DEC-V61-044 plans to wire it into
8916-  8916	        # controlDict functions{}) it uses the same ground truth.
8917-  8917	        bc = task_spec.boundary_conditions or {}
8918:  8918	        D_nozzle = bc.get("D_nozzle", 0.05)
8919:  8919	        T_plate = bc.get("T_plate", 290.0)
8920:  8920	        T_inlet = bc.get("T_inlet", 310.0)
8921:  8921	        delta_T_ref = float(T_inlet) - float(T_plate)
8922-  8922	        delta_z = 0.001  # probe offset above the plate; matches sampleDict generator
8923-  8923	        if delta_T_ref <= 0.0 or delta_z <= 0.0:
8924-  8924	            return key_quantities
8925-  8925	        try:
8926-  8926	            sorted_pts = sorted(points, key=lambda p: p[0][0])
8927-  8927	        except (IndexError, TypeError):
--
8931-  8931	            if not values:
8932-  8932	                continue
8933-  8933	            try:
8934-  8934	                T_probe = float(values[0])
8935-  8935	            except (ValueError, TypeError):
8936-  8936	                continue
8937:  8937	            d_T = abs(T_probe - float(T_plate))
8938:  8938	            nu_local = (d_T * float(D_nozzle)) / (delta_z * delta_T_ref)
8939-  8939	            nu_profile.append(nu_local)
8940-  8940	        if not nu_profile:
8941-  8941	            return key_quantities
8942-  8942	        key_quantities["nusselt_number"] = nu_profile[0]  # stagnation (smallest r)
8943-  8943	        key_quantities["nusselt_number_profile"] = nu_profile
8944-  8944	        key_quantities["nusselt_number_source"] = "sampleDict_direct"
--
8978-  8978	            # key_quantities; on extractor failure, an *_emitter_error key is
8979-  8979	            # written and stale scalars are dropped so DEC-V61-036 G1 fires
8980-  8980	            # (Codex round 2 round-3-readiness C-priority-1 wiring).
8981-  8981	            key_quantities = self._populate_naca_force_coeffs_from_forceCoeffs(
8982-  8982	                case_dir, task_spec, key_quantities
8983-  8983	            )
8984:  8984	        if task_spec.geometry_type == GeometryType.IMPINGING_JET or "impinging" in name_lower:
8985-  8985	            key_quantities = self._populate_ij_nusselt_from_sampledict(
8986-  8986	                case_dir, task_spec, key_quantities
8987-  8987	            )
8988-  8988	        return key_quantities
8989-  8989	
8990-  8990	    @staticmethod
--
9623-  9623	
9624-  9624	        DEC-V61-042: previously this extractor differenced plate-face
9625-  9625	        temperatures RADIALLY (dT/dr) — which is ≈0 by symmetry on a
9626-  9626	        fixedValue-T plate, giving the catastrophic 0.00417 underread
9627-  9627	        (−6000× vs gold 25.0). The fix bins cells by radial position r,
9628-  9628	        then at each bin applies a wall-normal 3-point one-sided stencil
9629:  9629	        against the plate BC (wall_coord_plate, T_plate plumbed through
9630-  9630	        task_spec.boundary_conditions by _generate_impinging_jet).
9631-  9631	
9632-  9632	        Fails closed when BC metadata is missing — MISSING_TARGET_QUANTITY
9633-  9633	        will fire at the comparator rather than a silent garbage read.
9634-  9634	        """
9635-  9635	        if not cxs or not cys or not t_vals:
9636-  9636	            return key_quantities
9637-  9637	
9638-  9638	        bc = task_spec.boundary_conditions or {}
9639:  9639	        wall_coord_plate = bc.get("wall_coord_plate")
9640:  9640	        T_plate = bc.get("T_plate")
9641:  9641	        T_inlet = bc.get("T_inlet")
9642-  9642	        bc_type = bc.get("wall_bc_type")
9643:  9643	        D_nozzle = bc.get("D_nozzle")
9644-  9644	        if (
9645:  9645	            wall_coord_plate is None or T_plate is None or T_inlet is None
9646:  9646	            or bc_type is None or D_nozzle is None
9647-  9647	        ):
9648-  9648	            # Fail closed — absence of nusselt_number is the signal.
9649-  9649	            # (Codex DEC-042 round-1 FLAG: don't leak extractor-internal
9650-  9650	            # state into measurement key_quantities.)
9651-  9651	            return key_quantities
9652-  9652	
9653:  9653	        Delta_T = float(T_inlet) - float(T_plate)
9654-  9654	        if abs(Delta_T) < 1e-10:
9655-  9655	            return key_quantities
9656-  9656	
9657-  9657	        from collections import defaultdict
9658-  9658	        from src.wall_gradient import extract_wall_gradient, BCContractViolation
9659-  9659	
9660:  9660	        # Bin cells by radial position r = |cx| (axisymmetric, axis at cx=0).
9661-  9661	        # Within each bin, we have cells at different cy (jet-axial) positions;
9662-  9662	        # the 3-point stencil operates on that cy-column against the plate
9663:  9663	        # BC at cy = wall_coord_plate.
9664-  9664	        unique_r = sorted({round(abs(cx), 4) for cx in cxs})
9665-  9665	        r_cols: Dict[float, List[Tuple[float, float]]] = defaultdict(list)
9666-  9666	        for i in range(min(len(cxs), len(cys), len(t_vals))):
9667-  9667	            r_key = round(abs(cxs[i]), 4)
9668-  9668	            r_cols[r_key].append((cys[i], t_vals[i]))
9669-  9669	
9670-  9670	        sorted_r: List[float] = []
9671-  9671	        Nu_profile: List[float] = []
9672:  9672	        wall_cy = float(wall_coord_plate)
9673-  9673	        for r_key in unique_r:
9674-  9674	            column = r_cols.get(r_key, [])
9675-  9675	            if len(column) < 2:
9676-  9676	                continue
9677-  9677	            # Plate sits at the MAX cy in the domain (jet hits top). The
9678-  9678	            # wall_gradient stencil validates wall_coord < cell_coord, so
--
9684-  9684	            ]
9685-  9685	            if len(interior) < 2:
9686-  9686	                continue
9687-  9687	            try:
9688-  9688	                grad = extract_wall_gradient(
9689-  9689	                    wall_coord=0.0,
9690:  9690	                    wall_value=float(T_plate),
9691-  9691	                    coords=[n for n, _ in interior],
9692-  9692	                    values=[t for _, t in interior],
9693-  9693	                    bc_type=bc_type,
9694-  9694	                    bc_gradient=bc.get("wall_bc_gradient"),
9695-  9695	                )
9696-  9696	            except BCContractViolation:
9697-  9697	                continue
9698-  9698	            # Stagnation Nu definition: h·D/k = D·|dT/dn|/ΔT (dimensionless).
9699-  9699	            # sign of grad depends on cold-plate hot-jet orientation; take |·|.
9700:  9700	            Nu = float(D_nozzle) * abs(grad) / Delta_T
9701-  9701	            sorted_r.append(r_key)
9702-  9702	            Nu_profile.append(Nu)
9703-  9703	
9704-  9704	        if Nu_profile:
9705-  9705	            # Stagnation Nu at r ≈ 0 is the first (smallest r) bin.
9706-  9706	            key_quantities["nusselt_number"] = Nu_profile[0]

exec
/bin/zsh -lc "git show 9a85b18:src/auto_verifier/config.py | nl -ba | sed -n '1,140p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
exec
/bin/zsh -lc "git show 9a85b18:.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml | nl -ba | sed -n '118,210p;275,320p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
   118	# ============================================================================
   119	# §3 Citation provenance audit (BLOCKING — must close before Stage A)
   120	# ============================================================================
   121	citation_audit:
   122	  whitelist_claim:
   123	    label: "Cooper et al. 1984 / Behnad et al. 2013"
   124	    doi: "10.1016/j.ijheatfluidflow.2013.03.003"
   125	    audit_status: SUSPECT
   126	    audit_reason: |
   127	      "Cooper 1984" does not match any well-known impinging-jet author/date.
   128	      The canonical impinging-jet experimental dataset commonly cited in
   129	      OpenFOAM tutorials and benchmark suites is:
   130	        - Cooper, D., Jackson, D.C., Launder, B.E., Liao, G.X. (1993)
   131	          "Impinging jet studies for turbulence model assessment — I.
   132	          Flow-field experiments", Int. J. Heat Mass Transfer 36(10),
   133	          2675-2684. DOI: 10.1016/S0017-9310(05)80204-2
   134	        - Baughn, J.W., Shimizu, S. (1989) "Heat transfer measurements
   135	          from a surface with uniform heat flux and an impinging jet",
   136	          ASME J. Heat Transfer 111(4), 1096-1098. DOI: 10.1115/1.3250776
   137	      Whitelist may have transposed digits or compressed citations. Per
   138	      V61-060 lesson: a wrong citation that "happened to PASS" is the
   139	      worst kind of stale provenance.
   140	    closure_action_required: |
   141	      Stage A.0 MUST resolve the actual paper(s) hosting the Re=10000,
   142	      h/d=2 Nu_stag value used by the gold YAML. Acceptance criterion:
   143	      a publicly accessible document with a Table or Figure number
   144	      locator (V61-060 set this precedent). If the original Cooper 1984
   145	      DOI resolves to the wrong paper (V61-060 pattern), pivot to one
   146	      of the publicly-archived alternatives above.
   147	  doi_resolves_to: NOT_VERIFIED  # Stage A.0 must run a curl/fetch on the DOI
   148	
   149	# ============================================================================
   150	# §4 Risk register (pre-Stage-A, surfaced for Codex review)
   151	# ============================================================================
   152	risk_register:
   153	  R1_re_mismatch:
   154	    severity: HIGH
   155	    description: |
   156	      Whitelist Re=10000 is unusual for impinging-jet benchmarks. Cooper
   157	      1993 ran Re=23000. Behnad 2013 may have multiple Re values. If the
   158	      gold YAML's ref_value was correlated from Re=23000 data and applied
   159	      blindly to Re=10000 simulation, deviation will be unbounded. Stage
   160	      A.0 must confirm Re consistency between gold ref + whitelist task_spec.
   161	    mitigation: |
   162	      (a) Verify Cooper 1993 has a Re=10000 row, OR
   163	      (b) Bump whitelist Re=10000 → 23000 to match the correlation, OR
   164	      (c) Use a Re-agnostic Nu correlation (Schlichting Nu/Re^0.5 = const
   165	          near stagnation) and document the assumption.
   166	  R2_h_over_d_mismatch:
   167	    severity: MED
   168	    description: |
   169	      Whitelist h/d=2 is a common stand-off. Cooper 1993 and Baughn/Shimizu
   170	      1989 both used h/d=2 OR h/d=6; verify alignment. h/d=2 puts the
   171	      stagnation in the potential core (Nu peaks); h/d=6 is post-core
   172	      (different Nu(r) shape). Stage A.0 must confirm.
   173	    mitigation: |
   174	      Lock h/d to whatever the chosen citation uses; if no overlap, hold
   175	      Stage A on a follow-up.
   176	  R3_turbulence_model_choice:
   177	    severity: MED
   178	    description: |
   179	      Whitelist sets `turbulence_model: k-omega SST`. For impinging jets
   180	      this is reasonable (k-ε notoriously over-predicts Nu near stagnation
   181	      due to round-jet stagnation anomaly). Adapter must actually emit
   182	      k-omega SST, not silently fall back to k-ε. Verify at Stage A.
   183	    mitigation: |
   184	      Stage A.5 alias-parity test (V61-060 lesson) must include a
   185	      turbulence-model-emitted-vs-declared check.
   186	  R4_buoyantFoam_dispatch_overlap:
   187	    severity: LOW
   188	    description: |
   189	      Adapter at src/foam_agent_adapter.py:676 hardcodes `solver_name =
   190	      "buoyantFoam"` for IMPINGING_JET, overriding the whitelist's
   191	      `simpleFoam` declaration. This is intentional (impinging jet needs
   192	      thermal) but contradicts whitelist; CASE_ID_TO_SOLVER in
   193	      src/auto_verifier/config.py:69 also hardcodes simpleFoam, creating
   194	      a 2-source-of-truth ambiguity.
   195	    mitigation: |
   196	      Stage A clean-up: align both the whitelist and CASE_ID_TO_SOLVER to
   197	      buoyantFoam, OR document the override path explicitly in the gold
   198	      YAML §physics_contract.note.
   199	  R5_alias_map_staleness_post_v61_060:
   200	    severity: HIGH
   201	    description: |
   202	      RETRO-V61-060 addendum: alias-map staleness was the #1 post-R3
   203	      defect. Any case_name change at Stage A.0 (e.g. citation suffix
   204	      added) MUST atomically update both `_TASK_NAME_TO_CASE_ID_ALIASES`
   205	      maps (src/foam_agent_adapter.py:247 + src/auto_verifier/config.py:30).
   206	      A.0 + A.3 should be ONE commit.
   207	    mitigation: |
   208	      Pre-commit check: if intake §3 demands a case_name rename, the same
   209	      commit MUST touch both alias maps. Codex pre-Stage-A review must
   210	      enforce this.
   275	# §7 Acceptance criteria (definition of done — F1-M2 two-tier close gate)
   276	# ============================================================================
   277	acceptance_criteria:
   278	  i_codex_arc_complete: |
   279	    Final Codex round returns APPROVE OR APPROVE_WITH_COMMENTS, OR
   280	    CHANGES_REQUIRED with all findings closed verbatim per the 5-condition
   281	    exception envelope (CLAUDE.md).
   282	  ii_headline_validated_or_honestly_failed: |
   283	    EITHER: live-run Nu_stagnation falls within ±30% of the chosen literature
   284	    band — primary gate PASS; OR: Nu_stagnation falls outside the band and
   285	    the DEC documents the physics-fidelity gap explicitly (V61-063 / V61-066
   286	    / V61-060 closeout pattern: METHODOLOGY_COMPLETE_PHYSICS_FIDELITY_GAP_DOCUMENTED).
   287	  iii_profile_shape_validated: |
   288	    Nu(r/D) profile across r/D ∈ {0, 0.5, 1.0, 1.5, 2.0} matches Cooper-style
   289	    monotonic decay; the conservation invariant gate must pass UNLESS the
   290	    physics-fidelity gap explanation explicitly accounts for non-monotonic
   291	    behaviour (e.g. high-Re secondary peak from vortex breakdown).
   292	  iv_invariant_count_excluded_from_pass_fraction: |
   293	    Per V61-060 Stage C.2 comparator semantics: NON_TYPE_HARD_INVARIANT
   294	    blocks verdict on violation but is excluded from primary_gate_count
   295	    denominator. UI must surface the invariant card with the appropriate
   296	    "守恒不变量" badge (rose/emerald state-aware per V61-060 R6 fix).
   297	  v_alias_map_atomic_with_case_name_rename: |
   298	    Per RETRO-V61-060 addendum: any A.0 case_name rename MUST be in the
   299	    same commit as both `_TASK_NAME_TO_CASE_ID_ALIASES` map updates.
   300	
   301	# ============================================================================
   302	# §8 Out of scope (will not be addressed in this DEC)
   303	# ============================================================================
   304	out_of_scope:
   305	  - Cross-jet-array configurations (single-jet-only)
   306	  - Compressible jet effects (Ma < 0.3 assumed)
   307	  - Confined-jet vs free-jet variants (free-jet only per existing whitelist
   308	    geometry h_over_d=2)
   309	  - Heat-transfer-coefficient measurement at the nozzle exit (only plate
   310	    Nu is in scope)
   311	  - Multi-Re sweep (single Re=10000 OR Re=23000 after §3 audit; no profile
   312	    over Re — that would be a follow-up DEC)

 succeeded in 0ms:
     1	"""Configuration and frozen thresholds for AutoVerifier."""
     2	
     3	from __future__ import annotations
     4	
     5	from pathlib import Path
     6	
     7	REPO_ROOT = Path(__file__).resolve().parents[2]
     8	KNOWLEDGE_ROOT = REPO_ROOT / "knowledge"
     9	REPORTS_ROOT = REPO_ROOT / "reports"
    10	
    11	# Q-2 Path A (DEC-V61-011): `fully_developed_turbulent_pipe_flow` renamed to
    12	# `duct_flow` to match the actual rectangular-duct geometry the adapter emits.
    13	# Old task name mappings retained (to `duct_flow` canonical) for backwards
    14	# compat with any cached TaskSpec / test fixture still using pre-rename strings.
    15	ANCHOR_CASE_IDS = frozenset(
    16	    {
    17	        "lid_driven_cavity_benchmark",
    18	        "backward_facing_step_steady",
    19	        "cylinder_crossflow",
    20	        "turbulent_flat_plate",
    21	        "duct_flow",
    22	        "rayleigh_benard_convection",
    23	        "differential_heated_cavity",
    24	        "naca0012_airfoil",
    25	        "axisymmetric_impinging_jet",
    26	        "fully_developed_plane_channel_flow",
    27	    }
    28	)
    29	
    30	TASK_NAME_TO_CASE_ID = {
    31	    "Lid-Driven Cavity": "lid_driven_cavity_benchmark",
    32	    "Backward-Facing Step": "backward_facing_step_steady",
    33	    "Circular Cylinder Wake": "cylinder_crossflow",
    34	    "Turbulent Flat Plate (Zero Pressure Gradient)": "turbulent_flat_plate",
    35	    # Q-2 Path A rename: new canonical name + legacy aliases
    36	    "Fully Developed Turbulent Square-Duct Flow": "duct_flow",
    37	    "Fully Developed Turbulent Pipe Flow": "duct_flow",          # pre-rename legacy
    38	    "Rayleigh-Benard Convection (Ra=10^6)": "rayleigh_benard_convection",
    39	    "Rayleigh-Bénard Convection (Ra=10^6)": "rayleigh_benard_convection",
    40	    "Differential Heated Cavity (Natural Convection)": "differential_heated_cavity",
    41	    "Differential Heated Cavity (Natural Convection, Ra=10^6 benchmark)": "differential_heated_cavity",
    42	    "NACA 0012 Airfoil External Flow": "naca0012_airfoil",
    43	    "Axisymmetric Impinging Jet (Re=10000)": "axisymmetric_impinging_jet",
    44	    "Fully Developed Plane Channel Flow (DNS)": "fully_developed_plane_channel_flow",
    45	}
    46	
    47	CASE_ID_TO_GOLD_FILE = {
    48	    "lid_driven_cavity_benchmark": KNOWLEDGE_ROOT / "gold_standards" / "lid_driven_cavity_benchmark.yaml",
    49	    "backward_facing_step_steady": KNOWLEDGE_ROOT / "gold_standards" / "backward_facing_step_steady.yaml",
    50	    "cylinder_crossflow": KNOWLEDGE_ROOT / "gold_standards" / "cylinder_crossflow.yaml",
    51	    "turbulent_flat_plate": KNOWLEDGE_ROOT / "gold_standards" / "turbulent_flat_plate.yaml",
    52	    "duct_flow": KNOWLEDGE_ROOT / "gold_standards" / "duct_flow.yaml",
    53	    "rayleigh_benard_convection": KNOWLEDGE_ROOT / "gold_standards" / "rayleigh_benard_convection.yaml",
    54	    "differential_heated_cavity": KNOWLEDGE_ROOT / "gold_standards" / "differential_heated_cavity.yaml",
    55	    "naca0012_airfoil": KNOWLEDGE_ROOT / "gold_standards" / "naca0012_airfoil.yaml",
    56	    "axisymmetric_impinging_jet": KNOWLEDGE_ROOT / "gold_standards" / "axisymmetric_impinging_jet.yaml",
    57	    "fully_developed_plane_channel_flow": KNOWLEDGE_ROOT / "gold_standards" / "fully_developed_plane_channel_flow.yaml",
    58	}
    59	
    60	CASE_ID_TO_SOLVER = {
    61	    "lid_driven_cavity_benchmark": "icoFoam",
    62	    "backward_facing_step_steady": "simpleFoam",
    63	    "cylinder_crossflow": "pimpleFoam",
    64	    "turbulent_flat_plate": "simpleFoam",
    65	    "duct_flow": "simpleFoam",
    66	    "rayleigh_benard_convection": "buoyantFoam",
    67	    "differential_heated_cavity": "buoyantFoam",
    68	    "naca0012_airfoil": "simpleFoam",
    69	    "axisymmetric_impinging_jet": "simpleFoam",
    70	    "fully_developed_plane_channel_flow": "icoFoam",
    71	}
    72	
    73	DEFAULT_TIMESTAMP = "1970-01-01T00:00:00Z"
    74	ZERO_REFERENCE_EPSILON = 1e-12
    75	
    76	# Threshold registry is frozen for Phase 8a per Opus condition C5.
    77	THRESHOLDS = {
    78	    "TH-1": 1.0,      # residual ratio <= 1.0 => converged
    79	    "TH-2": 1e-5,     # default target residual
    80	    "TH-3": 0.4,      # oscillation ratio > 0.4
    81	    "TH-4": 20,       # residual window size
    82	    "TH-5": 0.05,     # default relative tolerance
    83	    "TH-6": 1e-6,     # zero-reference absolute tolerance
    84	    "TH-7-pass": 0.01,
    85	    "TH-7-warn": 0.05,
    86	    "TH-8": 0.70,     # pass-with-deviations cutoff
    87	    "TH-9": 10.0,     # divergence if final > 10 x initial
    88	}
    89	
    90	PROFILE_VALUE_KEYS = (
    91	    "value",
    92	    "u",
    93	    "v",
    94	    "w",
    95	    "Nu",
    96	    "Cp",
    97	    "Cf",
    98	    "u_Ubulk",
    99	    "u_Uinf",
   100	    "u_plus",
   101	)

exec
/bin/zsh -lc "git show 9a85b18:src/foam_agent_adapter.py | nl -ba | sed -n '5552,5750p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
  5552	    def _generate_impinging_jet(self, case_dir: Path, task_spec: TaskSpec) -> None:
  5553	        """Generate impinging jet case files (buoyantFoam steady, Boussinesq).
  5554	
  5555	        Uses buoyantFoam with Boussinesq approximation for thermal fields.
  5556	        Hot jet inlet (310K) impinges on cold plate (290K).
  5557	        """
  5558	        (case_dir / "system").mkdir(parents=True, exist_ok=True)
  5559	        (case_dir / "constant").mkdir(parents=True, exist_ok=True)
  5560	        (case_dir / "0").mkdir(parents=True, exist_ok=True)
  5561	
  5562	        Re = float(task_spec.Re or 10000)
  5563	        D = 0.05
  5564	        h_over_d = 2.0
  5565	        H = h_over_d * D
  5566	        U_bulk = 1.0
  5567	        nu_val = U_bulk * D / Re
  5568	
  5569	        # Thermal parameters (Boussinesq)
  5570	        T_inlet = 310.0   # hot jet
  5571	        T_plate = 290.0   # cold impingement plate
  5572	        T_mean = 300.0    # reference
  5573	        Cp = 1005.0
  5574	        beta = 1.0 / T_mean
  5575	        Pr = 0.71
  5576	        mu_val = nu_val  # dynamic viscosity for Boussinesq
  5577	
  5578	        # Enthalpy: h = Cp*(T - T_mean)
  5579	        h_inlet = Cp * (T_inlet - T_mean)   # 10050
  5580	        h_plate = Cp * (T_plate - T_mean)   # -10050
  5581	        h_internal = 0.0                     # mean field starts at T_mean
  5582	
  5583	        # Domain: r=[0, 5D], z=[z_min, z_max]; split at z=0 for planar faces
  5584	        r_max = 5.0 * D
  5585	        z_min = -D / 2
  5586	        z_split = 0.0
  5587	        z_max = H + D / 2
  5588	        n_r = 60
  5589	        total_nz = 80
  5590	        n_z_lower = max(1, int(round(total_nz * (z_split - z_min) / (z_max - z_min))))
  5591	        n_z_upper = total_nz - n_z_lower
  5592	
  5593	        # Gravity = 0 (forced convection impinging jet, buoyancy negligible)
  5594	        g_val = 0.0
  5595	
  5596	        # DEC-V61-042: plumb wall-coord + wall-value + BC type so the
  5597	        # wall-normal stencil can difference against the actual plate
  5598	        # temperature instead of differencing radially across the plate
  5599	        # (which is ~0 by symmetry and gave the -6000× under-read).
  5600	        # Plate is at the upper face of the upper block (patch `plate`,
  5601	        # faces (8 9 10 11) at jet-axial coord = z_max). The extractor
  5602	        # reads cells by cy (jet-axial coord in OpenFOAM's y-slot) and
  5603	        # treats the wall as cy = max(cys), matching z_max here.
  5604	        if task_spec.boundary_conditions is None:
  5605	            task_spec.boundary_conditions = {}
  5606	        task_spec.boundary_conditions["D_nozzle"] = D
  5607	        task_spec.boundary_conditions["T_plate"] = T_plate
  5608	        task_spec.boundary_conditions["T_inlet"] = T_inlet
  5609	        task_spec.boundary_conditions["wall_coord_plate"] = z_max
  5610	        task_spec.boundary_conditions["wall_bc_type"] = "fixedValue"
  5611	
  5612	        (case_dir / "system" / "blockMeshDict").write_text(
  5613	            f"""/*--------------------------------*- C++ -*---------------------------------*\\
  5614	| =========                 |                                                 |
  5615	| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
  5616	|  \\    /   O peration     | Version:  10                                    |
  5617	|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
  5618	|    \\/     M anipulation  |                                                 |
  5619	*---------------------------------------------------------------------------*/
  5620	FoamFile
  5621	{{
  5622	    version     2.0;
  5623	    format      ascii;
  5624	    class       dictionary;
  5625	    location    "system";
  5626	    object      blockMeshDict;
  5627	}}
  5628	// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
  5629	
  5630	convertToMeters 1;
  5631	
  5632	vertices
  5633	(
  5634	    (0 {z_min:.6f} 0)
  5635	    ({r_max:.6f} {z_min:.6f} 0)
  5636	    ({r_max:.6f} {z_split:.6f} 0)
  5637	    (0 {z_split:.6f} 0)
  5638	    (0 {z_min:.6f} 0.1)
  5639	    ({r_max:.6f} {z_min:.6f} 0.1)
  5640	    ({r_max:.6f} {z_split:.6f} 0.1)
  5641	    (0 {z_split:.6f} 0.1)
  5642	    (0 {z_max:.6f} 0)
  5643	    ({r_max:.6f} {z_max:.6f} 0)
  5644	    ({r_max:.6f} {z_max:.6f} 0.1)
  5645	    (0 {z_max:.6f} 0.1)
  5646	);
  5647	
  5648	blocks
  5649	(
  5650	    hex (0 1 2 3 4 5 6 7) ({n_r} {n_z_lower} 1) simpleGrading (1 1 1)
  5651	    hex (3 2 9 8 7 6 10 11) ({n_r} {n_z_upper} 1) simpleGrading (1 1 1)
  5652	);
  5653	
  5654	edges
  5655	(
  5656	);
  5657	
  5658	boundary
  5659	(
  5660	    inlet
  5661	    {{
  5662	        type            patch;
  5663	        faces           ((0 4 5 1));
  5664	    }}
  5665	    plate
  5666	    {{
  5667	        type            wall;
  5668	        faces           ((8 9 10 11));
  5669	    }}
  5670	    outer
  5671	    {{
  5672	        type            patch;
  5673	        faces           ((1 5 6 2) (2 6 10 9));
  5674	    }}
  5675	    axis
  5676	    {{
  5677	        type            empty;
  5678	        faces           ((0 3 7 4) (3 8 11 7));
  5679	    }}
  5680	    front
  5681	    {{
  5682	        type            empty;
  5683	        faces           ((0 1 2 3) (3 2 9 8));
  5684	    }}
  5685	    back
  5686	    {{
  5687	        type            empty;
  5688	        faces           ((4 5 6 7) (7 6 10 11));
  5689	    }}
  5690	);
  5691	
  5692	mergePatchPairs
  5693	(
  5694	);
  5695	
  5696	// ************************************************************************* //
  5697	""",
  5698	            encoding="utf-8",
  5699	        )
  5700	
  5701	        # Boussinesq thermophysical properties for buoyantFoam
  5702	        (case_dir / "constant" / "thermophysicalProperties").write_text(
  5703	            f"""/*--------------------------------*- C++ -*---------------------------------*\\
  5704	| =========                 |                                                 |
  5705	| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
  5706	|  \\    /   O peration     | Version:  10                                    |
  5707	|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
  5708	|    \\/     M anipulation  |                                                 |
  5709	*---------------------------------------------------------------------------*/
  5710	FoamFile
  5711	{{
  5712	    version     2.0;
  5713	    format      ascii;
  5714	    class       dictionary;
  5715	    location    "constant";
  5716	    object      thermophysicalProperties;
  5717	}}
  5718	// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
  5719	
  5720	thermoType
  5721	{{
  5722	    type            heRhoThermo;
  5723	    mixture         pureMixture;
  5724	    transport       const;
  5725	    thermo          hConst;
  5726	    equationOfState Boussinesq;
  5727	    specie          specie;
  5728	    energy          sensibleEnthalpy;
  5729	}}
  5730	
  5731	mixture
  5732	{{
  5733	    specie
  5734	    {{
  5735	        molWeight       28.9;
  5736	    }}
  5737	    equationOfState
  5738	    {{
  5739	        rho0            1.0;
  5740	        T0              {T_mean:g};
  5741	        beta            {beta:.16e};
  5742	    }}
  5743	    thermodynamics
  5744	    {{
  5745	        Cp              {Cp:.16e};
  5746	        Hf              0;
  5747	    }}
  5748	    transport
  5749	    {{
  5750	        mu              {mu_val:.16e};

exec
/bin/zsh -lc "rg -n \"NON_TYPE_HARD_INVARIANT|primary_gate_count|HARD_GATED profile|Type II|nusselt_profile|cp_profile|profile shape\" .planning knowledge src | sed -n '1,240p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
src/foam_agent_adapter.py:8695:                emit_cp_profile,
src/foam_agent_adapter.py:8698:            emitted = emit_cp_profile(
src/foam_agent_adapter.py:9801:        cp_profile: List[Tuple[float, float]] = []
src/foam_agent_adapter.py:9815:                cp_profile.append((x_key, (p_surface - p_ref) / q_ref))
src/foam_agent_adapter.py:9817:        if cp_profile:
src/foam_agent_adapter.py:9818:            key_quantities["pressure_coefficient_x"] = [x for x, _ in cp_profile]
src/foam_agent_adapter.py:9819:            key_quantities["pressure_coefficient"] = [cp for _, cp in cp_profile]
src/airfoil_extractors.py:13:Pipeline contract (matches Type II gate set per intake §3):
src/airfoil_surface_sampler.py:194:def emit_cp_profile(
knowledge/gold_standards/naca0012_airfoil.yaml:11:#   SECONDARY · Cp(x/c) profile shape at α=0° (PROFILE_GATE, qualitative):
knowledge/gold_standards/naca0012_airfoil.yaml:23:  DEC-V61-058 Type II multi-dim arc (downgraded from Type I per Codex F1):
knowledge/gold_standards/naca0012_airfoil.yaml:43:  reference_correlation_context: "Ladson 1988 TM-4074 Table 1 reports Cl/Cd at Re=3.0e6 with grit-roughness fixed-transition (matches kOmegaSST + wall-function adapter). Tunnel uncertainty ±1.2% at α=8° per §3.4. Cp profile anchors (Abbott Fig. 4-7 + Gregory Fig. 7) used QUALITATIVELY — adapter samples a near-surface band of cell centres and averages, while reference is exact-surface; 20% tolerance preserves PASS_WITH_DEVIATIONS shape-match acceptance (V61-058 Type II: profile is QUALITATIVE_GATE, not absolute scalar)."
knowledge/gold_standards/naca0012_airfoil.yaml:74:  # ── PRIMARY SCALAR (HEADLINE GATE per V61-058 Type II §1) ──
.planning/reviews/dec_v61_052_bfs_round1_codex.log:3125:src/foam_agent_adapter.py:8811:            key_quantities["pressure_coefficient_x"] = [x for x, _ in cp_profile]
.planning/reviews/dec_v61_052_bfs_round1_codex.log:3126:src/foam_agent_adapter.py:8812:            key_quantities["pressure_coefficient"] = [cp for _, cp in cp_profile]
.planning/reviews/dec_v61_052_bfs_round1_codex.log:3510:src/foam_agent_adapter.py:8811:            key_quantities["pressure_coefficient_x"] = [x for x, _ in cp_profile]
.planning/reviews/dec_v61_052_bfs_round1_codex.log:3511:src/foam_agent_adapter.py:8812:            key_quantities["pressure_coefficient"] = [cp for _, cp in cp_profile]
.planning/reviews/dec_v61_052_bfs_round1_codex.log: WARNING: stopped searching binary file after match (found "\0" byte around offset 409811)
.planning/intake/DEC-V61-053_circular_cylinder_wake.yaml:41:primary_gate_count: 4
.planning/intake/DEC-V61-053_circular_cylinder_wake.yaml:308:  - "BFS was Type II (1 scalar gate); cylinder is Type I (4 gates) — more surface area"
.planning/reviews/pedagogy_round_2_codex.log:3151:  averages; reference values are exact surface points. Cp profile shape correct.
.planning/reviews/pedagogy_round_2_codex.log:4302:    13	  averages; reference values are exact surface points. Cp profile shape correct.
.planning/reviews/dec_v61_052_bfs_round3_codex.log:3148:src/foam_agent_adapter.py:9144:            key_quantities["pressure_coefficient_x"] = [x for x, _ in cp_profile]
.planning/reviews/dec_v61_052_bfs_round3_codex.log:3149:src/foam_agent_adapter.py:9145:            key_quantities["pressure_coefficient"] = [cp for _, cp in cp_profile]
.planning/intake/DEC-V61-057_differential_heated_cavity.yaml:81:primary_gate_count: 5
.planning/reviews/case_pilot_ldc_codex_run1_readonly_blocked.log:4280:  7755	                emit_cp_profile,
.planning/reviews/case_pilot_ldc_codex_run1_readonly_blocked.log:4283:  7758	            emitted = emit_cp_profile(
.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:15:#         F1-HIGH (Type I family-count failure): downgraded case_type Type I → Type II.
.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:18:#                  Type II = 1 primary scalar (Cl@α=8°) + ≥2 profile/qualitative
.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:19:#                  gates: full Cp profile shape + Cl(α) linear-regime curve match.
.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:69:               # probes do not satisfy this. Type II = 1 primary scalar gate +
.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:82:    2. Cp_distribution_alpha_zero — Cp(x/c) profile shape match at α=0°
.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:131:  CROSS_CHECK + 1 PROVISIONAL_ADVISORY = Type II requirement (1 + ≥2)
.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:137:primary_gate_count: 1  # primary scalar; profile/qualitative gates count in case_type but not primary_gate_count
.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:468:      action: "Downgrade case_type Type I → Type II; rebuild §1 family/gate structure with 1 PRIMARY scalar + ≥2 PROFILE/QUALITATIVE; relabel Cd@α=0 + Cp@0.5 as SAME_RUN_CROSS_CHECK; relabel y+ as PROVISIONAL_ADVISORY (not Family 3)."
.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:538:            transition Re=3e6 row + 1-PRIMARY-scalar Type II scope decision
.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:589:            report.yaml updated with Type II 5-row schema."
.planning/intake/TEMPLATE.yaml:29:  requirements. Type I = ≥3 independent scalar gates. Type II = 1 primary
.planning/intake/TEMPLATE.yaml:30:  scalar gate + ≥2 qualitative/profile gates. Type III = exploratory or
.planning/intake/TEMPLATE.yaml:32:primary_gate_count: <int>
.planning/intake/TEMPLATE.yaml:65:# Rubric: high = directly threatens primary_gate_count accuracy; med = likely
.planning/reviews/case_deep_dive_round_1_codex.log:3097:    13	  averages; reference values are exact surface points. Cp profile shape correct.
.planning/reviews/case_deep_dive_round_1_codex.log:4493:    13	  averages; reference values are exact surface points. Cp profile shape correct.
.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:53:    2. Promote the existing Nu(r/D) profile output to a Type II observable
.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:54:       family (one HARD_GATED stagnation Nu + one HARD_GATED profile shape
.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:67:case_type: II  # 1 HARD_GATED stagnation scalar + 1 HARD_GATED profile family
.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:68:               # + 1 NON_TYPE_HARD_INVARIANT (monotonic decay) + 1 PROVISIONAL
.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:80:    2. nusselt_profile_r_over_d — HARD_GATED — Nu(r/D) shape match at 5+
.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:88:  CONSERVATION INVARIANT (NON_TYPE_HARD_INVARIANT, blocks on violation but
.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:89:  excluded from primary_gate_count denominator per Stage C.2 comparator):
.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:105:primary_gate_count: 2  # nusselt_stagnation_at_r_d_zero + nusselt_profile_r_over_d
.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:233:        (4 observables, schema_v2, Type II gate_status taxonomy)
.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:256:      - Comparator branch reuse (V61-060 NON_TYPE_HARD_INVARIANT path)
.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:293:    Per V61-060 Stage C.2 comparator semantics: NON_TYPE_HARD_INVARIANT
.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:294:    blocks verdict on violation but is excluded from primary_gate_count
.planning/reviews/round_1_codex.log:12178:  7755	                emit_cp_profile,
.planning/reviews/round_1_codex.log:12181:  7758	            emitted = emit_cp_profile(
.planning/reviews/pedagogy_round_3_codex.log:752:    13	  averages; reference values are exact surface points. Cp profile shape correct.
.planning/reviews/pedagogy_round_3_codex.log:993:  8647	        cp_profile: List[Tuple[float, float]] = []
.planning/reviews/pedagogy_round_3_codex.log:1007:  8661	                cp_profile.append((x_key, (p_surface - p_ref) / q_ref))
.planning/decisions/2026-04-23_cfd_cylinder_multidim_dec053.md:43:  - DEC-V61-052 (BFS · Type II precedent · 5 rounds incl. F1-M2 back-fill)
.planning/decisions/2026-04-23_cfd_cylinder_multidim_dec053.md:54:- **primary_gate_count = 4**
.planning/retrospectives/2026-04-24_retro_v61_053_python_parity.md:121:Compare DEC-V61-053 to prior Type I / Type II arcs:
.planning/retrospectives/2026-04-24_retro_v61_053_python_parity.md:163:**Methodology implication** — new Type III intake risk flag:
.planning/retrospectives/2026-04-24_retro_v61_053_python_parity.md:190:**Methodology implication** — new Type II intake risk flag:
.planning/decisions/2026-04-22_phase8_dec036c_g2_comparator_uplus_yplus.md:107:Dict-profile shapes other than `{value: X}` are now sampled — tuple
.planning/reviews/pedagogy_round_1_codex.log:3639:    13	  averages; reference values are exact surface points. Cp profile shape correct.
.planning/decisions/2026-04-25_v61_058_naca0012_multidim.md:3:title: NACA0012 airfoil multi-dim validation · Type II 5-row schema · Ladson 1988 anchors · case 5 · v2.0 third-apply
.planning/decisions/2026-04-25_v61_058_naca0012_multidim.md:64:  Recommended follow-up: separate DEC (proposed V61-061) for high-resolution NACA0012 mesh profile, reusing Stage A gold YAML + Stage B extractors + Stage E driver verbatim. The V61-058 methodology layer (Type II 4-observable schema + α-routing + multi-α extractors + sign-convention smoke + sanity-check helper) is correct and ready for that follow-up to consume.
.planning/decisions/2026-04-25_v61_058_naca0012_multidim.md:65:external_gate_caveat: "Type II DEC (1 PRIMARY scalar Cl@α=8° + 1 SAME_RUN_CROSS_CHECK Cd@α=0° + 1 PROFILE Cp_distribution + 1 QUALITATIVE dCl/dα + 1 PROVISIONAL_ADVISORY y+_max). HEADLINE FAIL on as-implemented mesh — under-resolved 16k-cell structured grid. SANITY_CHECK + sign-convention smoke PASS — methodology layer delivers correctly. Codex log archive: reports/codex_tool_reports/dec_v61_058_{plan_review,round1,round2}_review.md. Live-run sweep archive: reports/phase5_audit/dec_v61_058_live_summary.yaml + dec_v61_058_live_run_20260425T104455Z_alpha{0,4,8}.json."
.planning/decisions/2026-04-25_v61_058_naca0012_multidim.md:86:- **case_type = II** (Codex F1 forced downgrade — original I plan had 5 gates but Codex ruled the dependency graph collapsed: Cl@α=4 + Cl@α=8 + dCl/dα are not independent, all sit on the same lift-curve fit. Type II re-cast: 1 PRIMARY scalar + 1 SAME_RUN_CROSS_CHECK + 1 PROFILE + 1 QUALITATIVE + 1 PROVISIONAL_ADVISORY = 5-row Type II schema).
.planning/decisions/2026-04-25_v61_058_naca0012_multidim.md:87:- **primary_gate_count = 1** (Cl@α=8° HEADLINE_PRIMARY_SCALAR; Cd@α=0° SAME_RUN_CROSS_CHECK; Cp_dist PROFILE; dCl/dα QUALITATIVE_GATE; y+_max PROVISIONAL_ADVISORY)
.planning/decisions/2026-04-25_v61_058_naca0012_multidim.md:195:V61-058 demonstrates the v2.0 methodology working end-to-end on a Type II case where the hard gates fail honestly. The methodology layer (4 observables × Type II schema, α-routing, multi-α extractors, sign-convention smoke, sanity-check helper, audit-fixture regen) delivered correctly through 3 Codex rounds and exposed an under-resolved-mesh signal that no synthetic test fixture would have surfaced. Per RETRO-V61-053 post-R3 defect protocol, the FAIL gates are recorded as a documented limitation with a follow-up DEC recommendation, NOT an arc retry.
.planning/decisions/2026-04-22_phase8_dec044_naca_surface_sampler.md:80:   - `emit_cp_profile`: end-to-end. Returns a dict with:
.planning/decisions/2026-04-22_phase8_dec044_naca_surface_sampler.md:95:   - Primary path: call `emit_cp_profile(case_dir, chord, U_inf, rho, p_inf)`.
.planning/decisions/2026-04-25_v61_057_dhc_multidim.md:68:- **primary_gate_count = 5** (1 HARD_GATED headline + 3 HARD_GATED cross-checks + 1 PROVISIONAL_ADVISORY ψ_max)

exec
/bin/zsh -lc "git show 9a85b18:.planning/intake/DEC-V61-058_naca0012_airfoil.yaml | nl -ba | sed -n '60,180p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
    60	methodology_version: "v2.0"
    61	intake_version: 2
    62	codex_plan_review_verdict: REQUEST_CHANGES_v1_then_REWRITTEN_v2  # final verdict pending Codex re-review of v2
    63	
    64	# ============================================================================
    65	# §1 Classification (F5-M1 hard gate, §3b — NO mid-arc Type change allowed)
    66	# ============================================================================
    67	case_type: II  # DOWNGRADED v1→v2 per Codex F1: Type I requires ≥3 PHYSICALLY-
    68	               # independent families; same-run cross-check pairs and mesh-quality
    69	               # probes do not satisfy this. Type II = 1 primary scalar gate +
    70	               # ≥2 qualitative/profile gates.
    71	case_type_rationale: |
    72	  PRIMARY SCALAR GATE (1) + PROFILE/QUALITATIVE GATES (≥2):
    73	
    74	  PRIMARY SCALAR · FORCE-COEFFICIENT (forceCoeffs FO; surface-integral
    75	  pressure + viscous on aerofoil patch; α=8° run):
    76	    1. Cl_at_alpha_eight  — HEADLINE GATE — lift coefficient at α=8°,
    77	                            Ladson 1988 NASA TM-4074 §3.2 Table 1
    78	                            Re=3.0e6 grit-roughness fixed-transition row,
    79	                            α=8° column, Cl ≈ 0.815 ± 0.010.
    80	
    81	  PROFILE/QUALITATIVE GATES:
    82	    2. Cp_distribution_alpha_zero — Cp(x/c) profile shape match at α=0°
    83	                                    upper surface, gold-anchored 5+ stations
    84	                                    (existing sampleDict path, DEC-V61-044).
    85	                                    Reference: Abbott & von Doenhoff 1959
    86	                                    Fig. 4-7 (NACA0012 α=0°) cross-checked
    87	                                    against Gregory & O'Reilly 1970 ARC R&M
    88	                                    3726 Fig. 7 α=0° column. Profile-mode
    89	                                    comparator: per-station tolerance 20%
    90	                                    (inherits whitelist gold band).
    91	    3. Cl_alpha_linear_regime_slope — Cl(α) curve shape across α∈{0°,4°,8°}.
    92	                                      Three-point extraction from forceCoeffs
    93	                                      across 3 separate runs gives slope
    94	                                      dCl/dα. Ladson 1988 Re=3.0e6 linear-
    95	                                      regime slope ≈ 0.105/deg ± 0.005.
    96	                                      QUALITATIVE_GATE: linearity check
    97	                                      (|Cl(8°)-Cl(0°)|/8 ≈ |Cl(4°)-Cl(0°)|/4
    98	                                      within 5%). PASS = linear regime
    99	                                      preserved; FAIL = unphysical curvature
   100	                                      indicates solver instability or stall
   101	                                      onset before α=8°.
   102	
   103	  SUPPLEMENTARY SCALAR (advisory, supports primary):
   104	    4. Cd_at_alpha_zero  — drag coefficient at α=0°, Ladson 1988 Table 1
   105	                           grit-roughness fixed-transition Re=3.0e6 ≈ 0.0080
   106	                           ± 0.0010. Same physical run as the Cp profile;
   107	                           SAME-RUN cross-check probe, not an independent
   108	                           family — labeled CROSS_CHECK to honor Codex F1.
   109	
   110	  PROVISIONAL_ADVISORY (mesh quality, NOT a physics gate):
   111	    5. y_plus_max_on_aerofoil — wall-resolution diagnostic from yPlus FO at
   112	                                α=0° run. Threshold band: PROVISIONAL pending
   113	                                live-run measurement. y+_min derivation
   114	                                (corrected per Codex F3): u_τ = U·sqrt(Cf/2),
   115	                                Cf ≈ 0.0040 → u_τ ≈ 0.0447 → y+_min ≈
   116	                                0.0447·6.25e-4/3.33e-7 ≈ 84. y+_max in
   117	                                adverse-pressure-gradient region α=8° upper
   118	                                may exceed 300; that's why Batch B3 keeps
   119	                                this PROVISIONAL_ADVISORY (mesh-validity
   120	                                annotator on the run, not a HARD gate).
   121	
   122	  Cl_at_alpha_zero EXPLICITLY EXCLUDED from gate set (gold = 0 by symmetry,
   123	  numerical_noise_snr trap). Surfaced as SANITY_CHECK sub-status only:
   124	  "|Cl| < 0.005 confirms symmetric solve" — PASS expected, but not a HARD gate.
   125	
   126	  Cl_at_alpha_four — RUN PERFORMED to enable Cl_alpha_linear_regime_slope
   127	  gate (3-point extraction); Cl@4° value itself is reported but NOT a
   128	  separate HARD gate (avoids Codex F1 same-extraction-path objection).
   129	
   130	  Independence count: 1 PRIMARY scalar + 2 PROFILE/QUALITATIVE gates + 1
   131	  CROSS_CHECK + 1 PROVISIONAL_ADVISORY = Type II requirement (1 + ≥2)
   132	  satisfied with healthy margin.
   133	
   134	  HEADLINE = Cl_at_alpha_eight (load-bearing canonical lift benchmark; Ladson
   135	  1988 cited in >50 RANS validation studies within ±1%).
   136	
   137	primary_gate_count: 1  # primary scalar; profile/qualitative gates count in case_type but not primary_gate_count
   138	profile_qualitative_gate_count: 2  # Cp_distribution + Cl_linear_regime_slope
   139	supplementary_scalar_gate_count: 1  # Cd@α=0 (CROSS_CHECK with profile)
   140	provisional_advisory_count: 1  # y+_max (mesh diagnostic)
   141	case_type_hard_gate_signed: true
   142	headline_gate: lift_coefficient_alpha_eight  # quantity_id matches new gold YAML observables[].name
   143	
   144	# ============================================================================
   145	# §2 Reference papers (F4 specificity: paper + table/figure + Mach + transition + α row)
   146	# ============================================================================
   147	reference_paper:
   148	  primary:
   149	    citation: "Ladson, C.L. (1988). Effects of Independent Variation of Mach and Reynolds Numbers on the Low-Speed Aerodynamic Characteristics of the NACA 0012 Airfoil Section. NASA Technical Memorandum 4074."
   150	    archive_id: "NASA-TM-4074 / NTRS 19880019495"
   151	    url: "https://ntrs.nasa.gov/api/citations/19880019495/downloads/19880019495.pdf"
   152	    pinned_anchors:
   153	      - quantity: Cl_at_alpha_eight
   154	        location: "§3.2 Table 1, Re=3.0e6 grit-roughness FIXED-TRANSITION row, M=0.15, α=8.00° column"
   155	        gold_value: 0.815
   156	        gold_uncertainty: 0.010  # ±0.010 from tunnel repeatability stated in §3.4
   157	      - quantity: Cl_at_alpha_four
   158	        location: "§3.2 Table 1, Re=3.0e6 grit-roughness fixed-transition row, M=0.15, α=4.00° column"
   159	        gold_value: 0.434  # used to compute slope; not a HARD gate itself
   160	        gold_uncertainty: 0.008
   161	      - quantity: Cd_at_alpha_zero
   162	        location: "§3.2 Table 1, Re=3.0e6 grit-roughness fixed-transition row, M=0.15, α=0.00° column"
   163	        gold_value: 0.0080
   164	        gold_uncertainty: 0.0010
   165	      - quantity: dCl_dalpha_linear_regime
   166	        location: "§3.2 Table 1, Re=3.0e6 grit-roughness fixed-transition row, M=0.15, α∈[0°,8°] linear-fit slope"
   167	        gold_value: 0.105  # /deg; from 3-point fit through tabulated α=0,4,8
   168	        gold_uncertainty: 0.005
   169	  secondary:
   170	    - citation: "Abbott, I.H., & von Doenhoff, A.E. (1959). Theory of Wing Sections, Including a Summary of Airfoil Data. Dover Publications."
   171	      pinned_anchors:
   172	        - quantity: Cp_distribution_alpha_zero
   173	          location: "Fig. 4-7 (NACA0012 chordwise pressure distribution at α=0°, Re≈6e6 free-transition); USED ONLY FOR PROFILE-SHAPE qualitative match (not absolute magnitudes — Re differs)"
   174	          providing: profile_shape_kutta_te_constraint
   175	    - citation: "Gregory, N., & O'Reilly, C.L. (1970). Low-Speed Aerodynamic Characteristics of NACA 0012 Aerofoil Section, Including the Effects of Upper-Surface Roughness Simulating Hoar Frost. ARC R&M 3726."
   176	      url: "https://naca.central.cranfield.ac.uk/bitstream/handle/1826.2/3003/arc-rm-3726.pdf?sequence=1"
   177	      pinned_anchors:
   178	        - quantity: Cp_distribution_alpha_zero
   179	          location: "Fig. 7 (Cp vs x/c at α=0°, Re=2.88e6 ≈ 3e6, M=0.16, transition free per §2.3); CROSS-CHECK against Abbott Fig. 4-7"
   180	          providing: cp_distribution_alpha_zero_cross_check_re_3e6

exec
/bin/zsh -lc "git show 9a85b18:.planning/intake/DEC-V61-060_rayleigh_benard_convection.yaml | nl -ba | sed -n '60,220p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
fatal: path '.planning/intake/DEC-V61-060_rayleigh_benard_convection.yaml' does not exist in '9a85b18'

exec
/bin/zsh -lc "git ls-tree -r --name-only 9a85b18 .planning/intake | rg 'V61-060|rbc|rayleigh'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 exited 1 in 0ms:
exec
/bin/zsh -lc "rg --files .planning/intake | rg 'V61-060|rbc|rayleigh'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 exited 1 in 0ms:
exec
/bin/zsh -lc "nl -ba .planning/intake/TEMPLATE.yaml | sed -n '20,45p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
    20	codex_plan_review_verdict: PENDING  # update to APPROVE_PLAN / APPROVE_PLAN_WITH_CHANGES / REQUEST_CHANGES after pre-Stage-A Codex review
    21	
    22	# ============================================================================
    23	# §1 Classification (F5-M1 hard gate, §3b — NO mid-arc Type change allowed)
    24	# ============================================================================
    25	case_type: I|II|III
    26	case_type_rationale: |
    27	  Explain which gates exist, how many are physically independent (NOT just
    28	  implementation-independent), and why this satisfies Type I / II / III
    29	  requirements. Type I = ≥3 independent scalar gates. Type II = 1 primary
    30	  scalar gate + ≥2 qualitative/profile gates. Type III = exploratory or
    31	  canonical-only case (St/Cd baseline, no multi-dim).
    32	primary_gate_count: <int>
    33	case_type_hard_gate_signed: true
    34	headline_gate: <quantity_name>
    35	
    36	# ============================================================================
    37	# §2 Reference papers
    38	# ============================================================================
    39	reference_paper:
    40	  primary:
    41	    citation: "Author (YYYY). Title. Journal V, pp"
    42	    doi: "10.xxxx/xxxx"
    43	    providing: [list, of, gates]
    44	  secondary:  # optional cross-check sources
    45	    - citation: "..."

web search: 
web search: "10.1016/j.ijheatfluidflow.2013.03.003" impinging jet Behnad 2013
web search: 
web search: site:doi.org 10.1016/j.ijheatfluidflow.2013.03.003
web search: 
web search: "10.1115/1.3250776" impinging jet h/d 2 Re 23000
web search: 
web search: "Behnad" "impinging jet" heat transfer
web search: 
web search: 
web search: 
web search: 
web search: 
web search: "S0142727X1300060X"
web search: 
web search: Behnad jet impingement 2013 heat transfer flat plate
codex
The literature audit is sharper than the YAML currently states: the existing DOI is definitely not an impinging-jet paper, and Cooper 1993 is a flow-field paper that was designed to pair with Baughn–Shimizu heat-transfer data. I’m pulling exact bibliographic records now so the review can say which citations are safe to hard-require at Stage A.0.
exec
/bin/zsh -lc "curl -sL 'https://api.crossref.org/works?query.bibliographic=Impinging%20jet%20studies%20for%20turbulence%20model%20assessment%20flow-field%20experiments%20Cooper%20Jackson%20Launder%20Liao&rows=5' | jq '.message.items[] | {title: .title[0], DOI, issued: .issued[\"date-parts\"][0], container: .[\"container-title\"][0]}'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
exec
/bin/zsh -lc "curl -sL 'https://api.crossref.org/works?query.bibliographic=Heat%20transfer%20measurements%20from%20a%20surface%20with%20uniform%20heat%20flux%20and%20an%20impinging%20jet%20Baughn%20Shimizu&rows=5' | jq '.message.items[] | {title: .title[0], DOI, issued: .issued[\"date-parts\"][0], container: .[\"container-title\"][0]}'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
exec
/bin/zsh -lc "curl -sL 'https://api.crossref.org/works?query.bibliographic=Behnad%20impinging%20jet%202013&rows=10' | jq '.message.items[] | {title: (.title[0]//\"\"), DOI, issued: .issued[\"date-parts\"][0], container: (.[\"container-title\"][0]//\"\")}'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
exec
/bin/zsh -lc "curl -sI 'https://doi.org/10.1016/j.ijheatfluidflow.2013.03.003' | sed -n '1,20p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 613ms:
HTTP/2 302 
date: Sun, 26 Apr 2026 01:52:05 GMT
content-type: text/html;charset=utf-8
location: https://linkinghub.elsevier.com/retrieve/pii/S0142727X1300060X
server: cloudflare
vary: Origin
vary: Accept
expires: Sun, 26 Apr 2026 02:49:26 GMT
link: <https://dul.usage.elsevier.com/doi/>; rel=dul
permissions-policy: interest-cohort=(),browsing-topics=()
cf-cache-status: DYNAMIC
strict-transport-security: max-age=31536000; includeSubDomains; preload
report-to: {"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=NIwmhAV9kc5M%2F53XPxbjJ0O9IvSzLCyJc4AsL7oMp375TzvRB6XeiS%2F9PiFXZaS6O8NEDi9%2BqSrc%2FxGGnKrkv6pHaugy7h9m2tFq4Xd8ZMSbBagz4ibVgDQ%3D"}]}
nel: {"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}
cf-ray: 9f21f2330943eb28-SJC
alt-svc: h3=":443"; ma=86400


 succeeded in 1437ms:
{
  "title": "Heat Transfer Measurements From a Surface With Uniform Heat Flux and an Impinging Jet",
  "DOI": "10.1115/1.3250776",
  "issued": [
    1989,
    11,
    1
  ],
  "container": "Journal of Heat Transfer"
}
{
  "title": "An Experimental Study of Entrainment Effects on the Heat Transfer From a Flat Surface to a Heated Circular Impinging Jet",
  "DOI": "10.1115/1.2911197",
  "issued": [
    1991,
    11,
    1
  ],
  "container": "Journal of Heat Transfer"
}
{
  "title": "Heat transfer between a circular free impinging jet and a solid surface with non-uniform wall temperature or wall heat flux—1. Solution for the stagnation region",
  "DOI": "10.1016/0017-9310(89)90034-3",
  "issued": [
    1989,
    7
  ],
  "container": "International Journal of Heat and Mass Transfer"
}
{
  "title": "Heat Transfer Measurements from a Flat Plate to a Swirling Impinging Jet",
  "DOI": "10.1615/ihtc11.2320",
  "issued": [
    1998
  ],
  "container": "Proceeding of International Heat Transfer Conference 11"
}
{
  "title": "An Instrument for the Measurement of Heat Flux from a Surface with Uniform Temperature",
  "DOI": "10.1115/1.3244346",
  "issued": [
    1980,
    8,
    1
  ],
  "container": "Journal of Heat Transfer"
}

 succeeded in 1701ms:
{
  "title": "Impinging jet studies for turbulence model assessment—I. Flow-field experiments",
  "DOI": "10.1016/s0017-9310(05)80204-2",
  "issued": [
    1993,
    7
  ],
  "container": "International Journal of Heat and Mass Transfer"
}
{
  "title": "IMPINGING JET: EXPERIMENTAL ANALYSIS OF FLOW FIELD AND HEAT TRANSFER FOR ASSESSMENT OF TURBULENCE MODELS",
  "DOI": "10.1615/ihtc13.trb.15",
  "issued": [
    2006
  ],
  "container": "Turbulence"
}
{
  "title": "IMPINGING JET: EXPERIMENTAL ANALYSIS OF FLOW FIELD AND HEAT TRANSFER FOR ASSESSMENT OF TURBULENCE MODELS",
  "DOI": "10.1615/ihtc13.trb.150",
  "issued": [
    2006
  ],
  "container": "Turbulence"
}
{
  "title": "Impinging jet studies for turbulence model assessment—II. An examination of the performance of four turbulence models",
  "DOI": "10.1016/s0017-9310(05)80205-4",
  "issued": [
    1993,
    7
  ],
  "container": "International Journal of Heat and Mass Transfer"
}
{
  "title": "EFFECTS OF ROTATION ON COOLING PERFORMANCE OF AN IMPINGING JET ROW",
  "DOI": "10.1615/tsfp3.1730",
  "issued": [
    2003
  ],
  "container": "Proceeding of Third Symposium on Turbulence and Shear Flow Phenomena"
}

 succeeded in 1893ms:
{
  "title": "HEAT TRANSFER FROM AN INFLOW-TYPE SWIRLING TURBULENT IMPINGING JET(Impinging Jet)",
  "DOI": "10.1299/jsmeicjwsf.2005.111",
  "issued": [
    2005
  ],
  "container": "The Proceedings of the International Conference on Jets, Wakes and Separated Flows (ICJWSF)"
}
{
  "title": "TURBULENCE MODEL FOR PREDICTING HEAT TRANSFER IN IMPINGING JET(Impinging Jet)",
  "DOI": "10.1299/jsmeicjwsf.2005.117",
  "issued": [
    2005
  ],
  "container": "The Proceedings of the International Conference on Jets, Wakes and Separated Flows (ICJWSF)"
}
{
  "title": "CHARACTERISTICS OF OSCILLATION FREQUENCY CAUSED BY SUPERSONIC IMPINGING JET(Impinging Jet)",
  "DOI": "10.1299/jsmeicjwsf.2005.123",
  "issued": [
    2005
  ],
  "container": "The Proceedings of the International Conference on Jets, Wakes and Separated Flows (ICJWSF)"
}
{
  "title": "EVALUATION OF LOCAL HEAT TRANSFER AND VISUALIZATION OF AN IMPINGING JET ACOUSTICALLY PERTURBED(Impinging Jet)",
  "DOI": "10.1299/jsmeicjwsf.2005.105",
  "issued": [
    2005
  ],
  "container": "The Proceedings of the International Conference on Jets, Wakes and Separated Flows (ICJWSF)"
}
{
  "title": "Flow and Heat Transfer of a Micro Jet Impinging on a Heated Chip: Part I—Micro Free and Impinging Jet Flow",
  "DOI": "10.1080/15567265.2012.748110",
  "issued": [
    2013,
    1
  ],
  "container": "Nanoscale and Microscale Thermophysical Engineering"
}
{
  "title": "Direct Numerical Simulation of a Rectangular Supersonic Jet Impinging on a Solid Wall",
  "DOI": "10.2514/6.2013-3098",
  "issued": [
    2013,
    6,
    22
  ],
  "container": "43rd Fluid Dynamics Conference"
}
{
  "title": "Noise predictions of a hot twin-jet impinging on a jet blast deflector",
  "DOI": "10.2514/6.2013-324",
  "issued": [
    2013,
    1,
    5
  ],
  "container": "51st AIAA Aerospace Sciences Meeting including the New Horizons Forum and Aerospace Exposition"
}
{
  "title": "The Effect of Fluid-Resonant Coupling in High-Speed Impinging Planar Jet Flows",
  "DOI": "10.1115/pvp2013-97141",
  "issued": [
    2013,
    7,
    14
  ],
  "container": "Volume 4: Fluid-Structure Interaction"
}
{
  "title": "Hysteresis effects in the impinging jet noise",
  "DOI": "10.1121/1.4800557",
  "issued": [
    2013
  ],
  "container": "Proceedings of Meetings on Acoustics"
}
{
  "title": "Cold Flow Comparison of Impinging-Sheet Injectors With Impinging-Jet Injectors",
  "DOI": "10.2514/6.2025-2285",
  "issued": [
    2025,
    1,
    3
  ],
  "container": "AIAA SCITECH 2025 Forum"
}

web search: 
web search: "Behnia" impinging jet 2013 heat transfer
web search: 
web search: "Cooper" impinging jet heat transfer 1973 report
exec
/bin/zsh -lc "git show 9a85b18:src/foam_agent_adapter.py | nl -ba | sed -n '6198,6208p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
  6198	dimensions      [0 0 0 1 0 0 0];
  6199	
  6200	internalField   uniform {T_mean:.6g};
  6201	
  6202	boundaryField
  6203	{{
  6204	    inlet           {{ type fixedValue; value uniform {T_inlet:.6g}; }}
  6205	    plate           {{ type fixedValue; value uniform {T_plate:.6g}; }}
  6206	    outer           {{ type inletOutlet; inletValue uniform {T_mean:.6g}; value uniform {T_mean:.6g}; }}
  6207	    axis            {{ type empty; }}
  6208	    front           {{ type empty; }}

exec
/bin/zsh -lc "git show 9a85b18:knowledge/whitelist.yaml | nl -ba | sed -n '226,245p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
   226	    gold_standard:
   227	      quantity: nusselt_number
   228	      description: "冲击面局部努塞尔数分布 (PROVISIONAL — Gate Q-new Case 9 hold)"
   229	      reference_values:
   230	        - {r_over_d: 0.0, Nu: 25.0}
   231	        - {r_over_d: 1.0, Nu: 12.0}
   232	      tolerance: 0.15  # 15% 相对误差
   233	
   234	  - id: naca0012_airfoil
   235	    name: "NACA 0012 Airfoil External Flow"
   236	    reference: "Thomas 1979 / Lada & Gostling 2007"
   237	    doi: "10.1017/S0001924000001169"
   238	    flow_type: EXTERNAL
   239	    geometry_type: AIRFOIL
   240	    compressibility: INCOMPRESSIBLE
   241	    steady_state: STEADY
   242	    solver: simpleFoam
   243	    turbulence_model: k-omega SST
   244	    parameters:
   245	      Re: 3000000

exec
/bin/zsh -lc "rg -n \"case_type: II|primary_gate_count:\" .planning/intake/DEC-V61-0*.yaml | sed -n '1,120p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:67:case_type: II  # 1 HARD_GATED stagnation scalar + 1 HARD_GATED profile family
.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:105:primary_gate_count: 2  # nusselt_stagnation_at_r_d_zero + nusselt_profile_r_over_d
.planning/intake/DEC-V61-061_naca0012_mesh_refinement.yaml:12:case_type: II  # inherited from V61-058
.planning/intake/DEC-V61-057_differential_heated_cavity.yaml:81:primary_gate_count: 5
.planning/intake/DEC-V61-053_circular_cylinder_wake.yaml:41:primary_gate_count: 4
.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:67:case_type: II  # DOWNGRADED v1→v2 per Codex F1: Type I requires ≥3 PHYSICALLY-
.planning/intake/DEC-V61-058_naca0012_airfoil.yaml:137:primary_gate_count: 1  # primary scalar; profile/qualitative gates count in case_type but not primary_gate_count

exec
/bin/zsh -lc "git show 9a85b18:.planning/intake/DEC-V61-061_naca0012_mesh_refinement.yaml | nl -ba | sed -n '1,80p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
     1	# DEC-V61-061 · NACA0012 mesh refinement (followup to V61-058)
     2	# Intake v1 · Stage 0 · 2026-04-25
     3	# Target: close the V61-058 physics-fidelity gap by refining
     4	# `_generate_airfoil_flow` mesh template only. Reuses V61-058
     5	# methodology stack verbatim (gold YAML, extractors, Stage E driver).
     6	
     7	dec_id: DEC-V61-061
     8	title: NACA0012 mesh refinement · close V61-058 physics-fidelity gap
     9	case_id: naca0012_airfoil  # SAME canonical case_id as V61-058
    10	predecessor: DEC-V61-058
    11	methodology_version: "v2.0 (fourth-apply, post-V61-053+057+058)"
    12	case_type: II  # inherited from V61-058
    13	autonomous_governance: true
    14	
    15	# §1 Scope (in/out)
    16	scope:
    17	  in:
    18	    - "Mesh refinement in `src/foam_agent_adapter.py::_generate_airfoil_flow`"
    19	    - "Targets: airfoil surface 120→240+ pts; y+_max 139→~50; domain ±5→±10 chord"
    20	    - "Re-run Stage E sweep at α∈{0,4,8}° using existing scripts/dec_v61_058_live_runs.py (single-line dec_id rebrand only)"
    21	    - "Verify V61-058 hard gates: Cl@α=8°≈0.815 (5%), Cd@α=0°≈0.008 (15%), dCl/dα≈0.105/deg (10%)"
    22	    - "Re-verify smoke + sanity: |Cl@α=0°|<0.005, sign convention Cl@α=8°>0"
    23	  out:
    24	    - "Gold YAML changes (locked by V61-058 A1)"
    25	    - "Extractor logic changes (locked by V61-058 B2)"
    26	    - "Stage D audit fixture format (V61-058 D regenerates automatically)"
    27	    - "New gates / new observables"
    28	    - "Stall regime / finite-AR / compressibility / transition modeling"
    29	    - "Other case meshes (cylinder, BFS, channel, etc.) — V61-061 touches only `_generate_airfoil_flow`"
    30	
    31	# §2 Hard gates (inherited verbatim from V61-058 §3)
    32	hard_gates:
    33	  - id: lift_coefficient_alpha_eight
    34	    role: HEADLINE_PRIMARY_SCALAR
    35	    target: 0.815
    36	    tolerance: 0.05
    37	    source: "Ladson 1988 NASA TM-4074 §3.2 Tab.1 Re=3e6"
    38	    v61_058_actual: 0.491  # 40% under
    39	  - id: drag_coefficient_alpha_zero
    40	    role: SAME_RUN_CROSS_CHECK
    41	    target: 0.0080
    42	    tolerance: 0.15
    43	    source: "Ladson 1988 same"
    44	    v61_058_actual: 0.0201  # 151% over
    45	  - id: lift_slope_dCl_dalpha_linear_regime
    46	    role: QUALITATIVE_GATE
    47	    target: 0.105
    48	    tolerance: 0.10
    49	    source: "Ladson 1988 + Abbott 1959 cross-check"
    50	    v61_058_actual: 0.061  # 42% under
    51	
    52	smoke_assertions:  # SANITY_CHECK + sign convention (intake §9 inherited)
    53	  - "α=+8° → Cl > 0 strictly"
    54	  - "α=0° → |Cl| < 0.005 (numerical noise floor)"
    55	
    56	advisory:
    57	  y_plus_max:
    58	    band: [11, 500]
    59	    target: ~30  # log-layer wall-function sweet spot
    60	
    61	# §3 Technical hypothesis (root cause from V61-058 defect_addendum)
    62	hypothesis: |
    63	  V61-058 Stage E ran at 16k cells, 120 airfoil surface faces, y+_max=139,
    64	  domain ±5 chord. All three failing gates trace to the same root cause:
    65	  under-resolved boundary layer + wake. With 120 surface faces and y+ in
    66	  the upper log-layer, kOmegaSST + wall functions systematically
    67	  under-predicts pressure-side suction peak (→ Cl@α=8° low) and
    68	  over-predicts skin friction (→ Cd@α=0° high). dCl/dα is the linear
    69	  combination of the first two effects.
    70	
    71	  Refinement plan (single-axis change, monotone improvement expected):
    72	  - Surface points 120→240 (double in nx on each of 4 aerofoil blocks: 30→60)
    73	  - z-direction nz: 80→120 cells, simpleGrading 40→200 → first cell ~5e-4 → y+~30-50
    74	  - Domain x: ±5→±10 chord; z: ±2→±4 chord
    75	  - Wake blocks nx: 40→60 (better wake resolution)
    76	
    77	  Estimated cell count: 4×60×120 + 2×60×120 = 43,200 (~2.7x V61-058)
    78	  Estimated runtime: 31s × 2.7 × 1.3 (matrix cond) ≈ 2 min per α
    79	  Domain doubling factor: x range from 10c→20c, z from 4c→8c.
    80	  But cell count is set by nx, nz directly, so domain change adjusts

exec
/bin/zsh -lc 'rg -n "case_type_hard_gate_signed|headline_gate|profile_qualitative_gate_count|supplementary_scalar_gate_count" .planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml' in /Users/Zhuanz/Desktop/cfd-s4-rbc
 exited 1 in 0ms:
exec
/bin/zsh -lc "curl -sL 'https://api.crossref.org/works?query.bibliographic=Prediction%20of%20heat%20transfer%20in%20an%20axisymmetric%20turbulent%20jet%20impinging%20on%20a%20flat%20plate%20Behnia%20Parneix%20Durbin&rows=5' | jq '.message.items[] | {title: .title[0], DOI, issued: .issued[\"date-parts\"][0], container: .[\"container-title\"][0]}'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
exec
/bin/zsh -lc "curl -sL 'https://api.crossref.org/works?query.bibliographic=Numerical%20study%20of%20turbulent%20heat%20transfer%20in%20confined%20and%20unconfined%20impinging%20jets%20Behnia&rows=5' | jq '.message.items[] | {title: .title[0], DOI, issued: .issued[\"date-parts\"][0], container: .[\"container-title\"][0]}'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 2780ms:
{
  "title": "Numerical study of turbulent heat transfer in confined and unconfined impinging jets",
  "DOI": "10.1016/s0142-727x(98)10040-1",
  "issued": [
    1999,
    2
  ],
  "container": "International Journal of Heat and Fluid Flow"
}
{
  "title": "A Numerical Study of Turbulent Heat Transfer in Unconfined Impinging Slot Jets",
  "DOI": "10.1115/imece2003-43347",
  "issued": [
    2003
  ],
  "container": "Heat Transfer, Volume 4"
}
{
  "title": "NUMERICAL INVESTIGATION OF HEAT TRANSFER UNDER CONFINED IMPINGING TURBULENT SLOT JETS",
  "DOI": "10.1080/104077899274976",
  "issued": [
    1999,
    6
  ],
  "container": "Numerical Heat Transfer, Part A: Applications"
}
{
  "title": "3-D Numerical Heat Transfer for Confined Turbulent Twin Circular Jets Impinging on an Inclined Moving Plate",
  "DOI": "10.1115/imece2014-36054",
  "issued": [
    2014,
    11,
    14
  ],
  "container": "Volume 8B: Heat Transfer and Thermal Engineering"
}
{
  "title": "TURBULENT FLOW AND HEAT TRANSFER FROM CONFINED MULTIPLE IMPINGING SLOT JETS",
  "DOI": "10.1080/10407789508913687",
  "issued": [
    1995,
    1
  ],
  "container": "Numerical Heat Transfer, Part A: Applications"
}

 succeeded in 3219ms:
{
  "title": "Prediction of heat transfer in an axisymmetric turbulent jet impinging on a flat plate",
  "DOI": "10.1016/s0017-9310(97)00254-8",
  "issued": [
    1998,
    6
  ],
  "container": "International Journal of Heat and Mass Transfer"
}
{
  "title": "Predictions of Turbulent Heat Transfer in an Axisymmetric Jet Impinging on a Heated Pedestal",
  "DOI": "10.1115/1.2825964",
  "issued": [
    1999,
    2,
    1
  ],
  "container": "Journal of Heat Transfer"
}
{
  "title": "Numerical study of turbulent heat transfer in confined and unconfined impinging jets",
  "DOI": "10.1016/s0142-727x(98)10040-1",
  "issued": [
    1999,
    2
  ],
  "container": "International Journal of Heat and Fluid Flow"
}
{
  "title": "Turbulent Heat Transfer From a Slot Jet Impinging on a Flat Plate",
  "DOI": "10.1115/1.4024554",
  "issued": [
    2013,
    8,
    19
  ],
  "container": "Journal of Heat Transfer"
}
{
  "title": "An Investigation on Turbulent Heat Transfer of an Axisymmetric Jet Impinging on a Flat Plate",
  "DOI": "10.1299/jsme1958.28.74",
  "issued": [
    1985
  ],
  "container": "Bulletin of JSME"
}

codex
Reviewed against commit `9a85b18`.

- **F1 = HIGH** — [§3 citation_audit](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:121) is correctly suspicious, but the closure framing is still too loose for Stage A.0. The whitelist DOI in [knowledge/whitelist.yaml](/Users/Zhuanz/Desktop/cfd-s4-rbc/knowledge/whitelist.yaml:206) resolves to an unrelated turbine LES paper, not an impinging-jet source: <https://doi.org/10.1016/j.ijheatfluidflow.2013.03.003>. Also, `Cooper et al. 1993` is the hydrodynamic companion dataset, not the heat-transfer anchor: <https://doi.org/10.1016/S0017-9310(05)80204-2>. The heat-transfer anchor is much more plausibly `Baughn & Shimizu 1989`: <https://doi.org/10.1115/1.3250776>. I would also treat `Behnad et al. 2013` as likely corruption of `Behnia et al. 1998/1999`, not a trusted fallback (`10.1016/S0017-9310(97)00254-8`, `10.1016/S0142-727X(98)10040-1`). Concrete edit: rewrite §3 so Stage A.0 must try these DOIs in order, and distinguish `thermal gold anchor` from `hydrodynamic support` instead of listing Cooper/Baughn as interchangeable alternatives.

- **F2 = MED** — [§1 classification](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:67) should stay **Type II**, not be split into per-station Type I gates; the stations are one profile family, not independent physics families. But the current taxonomy is internally inconsistent with the template and V61-058 precedent: it declares only one profile/qualitative gate, sets `primary_gate_count: 2`, and omits `headline_gate` / `case_type_hard_gate_signed`. Concrete edit: keep Type II, change `primary_gate_count` to `1`, add `profile_qualitative_gate_count: 2`, and either relabel monotonicity as a second `QUALITATIVE_GATE` or add a distinct second shape gate such as `secondary_peak_presence_or_absence` / `half-width radius`. This also means [§6 stage_preview](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:227) needs an extra early batch before extractor/comparator work: resolve citation + free/confined + Re/H/D + wall-BC family first. With those gaps still open, `estimated_pass_rate_round1 = 0.40` looks optimistic; I’d set `0.25–0.30`.

- **F3 = LOW** — [§4 risk_register](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:152) is missing three explicit surfaced risks already visible in code: `nusselt_number_unphysical_magnitude` exists in [_extract_jet_nusselt](/Users/Zhuanz/Desktop/cfd-s4-rbc/src/foam_agent_adapter.py:9717); the generator uses a constant-temperature plate, not uniform heat flux, at [foam_agent_adapter.py:6204](/Users/Zhuanz/Desktop/cfd-s4-rbc/src/foam_agent_adapter.py:6204); and the mesh is neither cyclic AMI nor 3D wedge, but a pseudo-2D slab with `empty` patches at [foam_agent_adapter.py:5632](/Users/Zhuanz/Desktop/cfd-s4-rbc/src/foam_agent_adapter.py:5632). [§7 acceptance_criteria](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:277) should therefore name exact DOI + figure/table locator, exact station set, exact tolerance mode, and “hazard flag absent” as a verifiable criterion.

**Verdict:** `REQUEST_CHANGES`
tokens used
162,254
Reviewed against commit `9a85b18`.

- **F1 = HIGH** — [§3 citation_audit](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:121) is correctly suspicious, but the closure framing is still too loose for Stage A.0. The whitelist DOI in [knowledge/whitelist.yaml](/Users/Zhuanz/Desktop/cfd-s4-rbc/knowledge/whitelist.yaml:206) resolves to an unrelated turbine LES paper, not an impinging-jet source: <https://doi.org/10.1016/j.ijheatfluidflow.2013.03.003>. Also, `Cooper et al. 1993` is the hydrodynamic companion dataset, not the heat-transfer anchor: <https://doi.org/10.1016/S0017-9310(05)80204-2>. The heat-transfer anchor is much more plausibly `Baughn & Shimizu 1989`: <https://doi.org/10.1115/1.3250776>. I would also treat `Behnad et al. 2013` as likely corruption of `Behnia et al. 1998/1999`, not a trusted fallback (`10.1016/S0017-9310(97)00254-8`, `10.1016/S0142-727X(98)10040-1`). Concrete edit: rewrite §3 so Stage A.0 must try these DOIs in order, and distinguish `thermal gold anchor` from `hydrodynamic support` instead of listing Cooper/Baughn as interchangeable alternatives.

- **F2 = MED** — [§1 classification](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:67) should stay **Type II**, not be split into per-station Type I gates; the stations are one profile family, not independent physics families. But the current taxonomy is internally inconsistent with the template and V61-058 precedent: it declares only one profile/qualitative gate, sets `primary_gate_count: 2`, and omits `headline_gate` / `case_type_hard_gate_signed`. Concrete edit: keep Type II, change `primary_gate_count` to `1`, add `profile_qualitative_gate_count: 2`, and either relabel monotonicity as a second `QUALITATIVE_GATE` or add a distinct second shape gate such as `secondary_peak_presence_or_absence` / `half-width radius`. This also means [§6 stage_preview](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:227) needs an extra early batch before extractor/comparator work: resolve citation + free/confined + Re/H/D + wall-BC family first. With those gaps still open, `estimated_pass_rate_round1 = 0.40` looks optimistic; I’d set `0.25–0.30`.

- **F3 = LOW** — [§4 risk_register](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:152) is missing three explicit surfaced risks already visible in code: `nusselt_number_unphysical_magnitude` exists in [_extract_jet_nusselt](/Users/Zhuanz/Desktop/cfd-s4-rbc/src/foam_agent_adapter.py:9717); the generator uses a constant-temperature plate, not uniform heat flux, at [foam_agent_adapter.py:6204](/Users/Zhuanz/Desktop/cfd-s4-rbc/src/foam_agent_adapter.py:6204); and the mesh is neither cyclic AMI nor 3D wedge, but a pseudo-2D slab with `empty` patches at [foam_agent_adapter.py:5632](/Users/Zhuanz/Desktop/cfd-s4-rbc/src/foam_agent_adapter.py:5632). [§7 acceptance_criteria](/Users/Zhuanz/Desktop/cfd-s4-rbc/.planning/intake/DEC-V61-067_axisymmetric_impinging_jet.yaml:277) should therefore name exact DOI + figure/table locator, exact station set, exact tolerance mode, and “hazard flag absent” as a verifiable criterion.

**Verdict:** `REQUEST_CHANGES`
