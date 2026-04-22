2026-04-22T11:40:41.838554Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-research-deerflow/SKILL.md: missing YAML frontmatter delimited by ---
2026-04-22T11:40:41.838575Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-report-pretext/SKILL.md: missing YAML frontmatter delimited by ---
OpenAI Codex v0.118.0 (research preview)
--------
workdir: /Users/Zhuanz/Desktop/cfd-harness-unified
model: gpt-5.4
provider: openai
approval: never
sandbox: workspace-write [workdir, /tmp, $TMPDIR, /Users/Zhuanz/.codex/memories]
reasoning effort: xhigh
reasoning summaries: none
session id: 019db4fe-1672-7021-a58e-bed2e86d0506
--------
user
# [CLAUDE → CODEX TOOL INVOCATION]

    from: claude-code-opus47 (Main Driver v6.2)
    to: codex-gpt54-xhigh (Joint Dev Peer · §A Diff Generator)
    task: "DEC-V61-045 Wave 1 Invocation C — test coverage for Wave 1 fixes"
    contract: Notion DEC-V61-045 PROPOSAL
    spec: .planning/decisions/2026-04-22_phase8_dec045_attestor_gates_blocker_fixes_PROPOSAL.md
    upstream_findings:
      - reports/codex_tool_reports/20260422_dec036b_codex_review.md (S2 nit — test coverage weaker than DEC claimed)
      - reports/codex_tool_reports/20260422_dec038_codex_review.md (CA-008 — missing 10-case integration)

    scope:
      Add test cases covering Wave 1 A/B changes. Do NOT modify existing tests
      unless they break from API shift. If an existing test needs signature
      update (e.g., attest(log) → attest(log, ...)), only update the minimum
      necessary; do NOT refactor or improve unrelated tests.

    allowed_files:
      - ui/backend/tests/test_convergence_attestor.py
      - ui/backend/tests/test_comparator_gates_g3_g4_g5.py

    read_only_context:
      - src/convergence_attestor.py   (post-Wave-1-A state; new APIs)
      - src/comparator_gates.py       (post-Wave-1-B state; new VTK reader)
      - knowledge/attestor_thresholds.yaml
      - reports/codex_tool_reports/20260422_dec045_wave1_A_convergence_attestor_result.md
      - reports/codex_tool_reports/20260422_dec045_wave1_B_comparator_gates_result.md

    forbidden_files:
      - any file not in allowed_files

    autonomy: TOOL-SCOPE

---

## Test cases to add

### In `ui/backend/tests/test_convergence_attestor.py`

Add these tests (new top-level `def test_*` functions). Import signatures:
```python
from src import convergence_attestor as ca
from src.convergence_attestor import Thresholds, load_thresholds
```

1. **test_load_thresholds_defaults**: `load_thresholds()` returns Thresholds with values matching YAML `defaults` section. Verify `continuity_floor==1e-4`, `residual_floor==1e-3`, `residual_floor_per_field["p_rgh"]==1e-2`.

2. **test_load_thresholds_per_case_impinging_jet**: `load_thresholds("impinging_jet")` returns Thresholds where `residual_floor_per_field["p_rgh"]==5e-3`. Other fields inherit defaults.

3. **test_load_thresholds_per_case_rayleigh_benard**: `load_thresholds("rayleigh_benard_convection")` returns Thresholds where `residual_floor_per_field["h"]==2e-3` AND `no_progress_decade_frac==0.3`.

4. **test_load_thresholds_unknown_case_falls_back**: `load_thresholds("nonexistent_xyz_12345")` returns Thresholds identical to `load_thresholds()` (defaults). No exception, no log ERROR (WARN or silent is OK).

5. **test_load_thresholds_missing_yaml_uses_hardcoded** (tmp_path fixture):
   ```python
   bad_path = tmp_path / "nonexistent.yaml"
   t = load_thresholds(yaml_path=bad_path)
   # Must return Thresholds instance, not raise. Values should match
   # hardcoded defaults (pre-YAML constants).
   assert t.continuity_floor == ca.A2_CONTINUITY_FLOOR
   assert t.residual_floor == ca.A3_RESIDUAL_FLOOR
   ```

6. **test_a1_exit_code_false_forces_fail**: construct a mock `execution_result` object (use `types.SimpleNamespace(success=False, exit_code=139)`). Pass a log with NO fatal markers. Call `_check_a1_solver_crash(log, execution_result=er)`. Assert verdict==FAIL, evidence contains exit_code.

7. **test_a1_log_fatal_fires_even_with_success_exit**: construct `execution_result=SimpleNamespace(success=True, exit_code=0)`. Pass a log containing `Floating exception` in the middle. Assert verdict==FAIL (log signal alone is sufficient).

8. **test_a1_sigFpe_banner_not_false_positive**: regression guard — a log with the startup banner `sigFpe : Enabling floating point exception trapping (FOAM_SIGFPE).` but NO actual FATAL/exception markers should NOT fire A1.

9. **test_a3_per_field_threshold_impinging_jet_p_rgh**: write a synthetic log with final `DILUPBiCGStab:  Solving for p_rgh, Initial residual = 6e-3, Final residual = 1e-5, No Iterations 2`. Call `_check_a3_residual_floor(log, thresholds=load_thresholds("impinging_jet"))`. Assert verdict==HAZARD (6e-3 > 5e-3 per-case threshold). Verify the default (not impinging_jet) would be FAIL/HAZARD at 6e-3 > 1e-3 — but for this test we want to prove the per-case override is applied.

10. **test_a6_decade_range_exactly_1_fires_fail** (CA-006 guard): synthetic residual timeline with initial residual oscillating between 1.0 and 10.0 for 50 iters (exactly 1 decade). With default `no_progress_decade_frac==1.0`, verdict should be FAIL (`<=` not `<`). Previously `< 1.0` would have been PASS at exactly 1.0.

11. **test_a4_gap_blocks_reset_consecutive** (CA-007 guard): synthetic log with 4 time-step blocks: block 1 pressure cap (No Iterations 1000), block 2 no pressure solve (gap), block 3 pressure cap, block 4 pressure cap. Max consecutive capped = 2 (blocks 3-4). Assert A4 verdict==PASS.

12. **test_a4_three_consecutive_caps_fail**: 3 back-to-back capped blocks with no gaps. Assert A4 verdict==FAIL.

13. **test_attest_with_execution_result_failure**: `attest(log, execution_result=SimpleNamespace(success=False))` on an otherwise clean log. Assert `overall == "ATTEST_FAIL"` and A1 check in result.checks has verdict==FAIL.

### In `ui/backend/tests/test_comparator_gates_g3_g4_g5.py`

Add these tests. Import:
```python
from src.comparator_gates import read_final_velocity_max, check_all_gates
```

1. **test_read_final_velocity_max_skips_allPatches** (tmp_path): create fake VTK dir with `case_100.vtk` AND `allPatches/allPatches_100.vtk`. Both have pyvista-readable content with U data. Assert `read_final_velocity_max(dir)` returns max from case_100.vtk only.

   **NOTE**: creating synthetic pyvista-readable VTK files is non-trivial. Alternative: monkeypatch `pyvista.read` to return crafted meshes for specific paths. Use monkeypatch approach — it's more robust + faster.

2. **test_read_final_velocity_max_uses_latest_timestep** (tmp_path + monkeypatch): create 3 pseudo-files `case_100.vtk` (max |U|=999), `case_200.vtk` (max |U|=1.0), `case_500.vtk` (max |U|=2.0). Assert returns 2.0 (latest by timestep, NOT alphabetic).

3. **test_read_final_velocity_max_allPatches_only_returns_none** (tmp_path): VTK dir contains only `allPatches/*.vtk`, no internal. Assert returns None.

4. **test_read_final_velocity_max_numeric_vs_alphabetic_sort** (tmp_path + monkeypatch): create `case_10.vtk`, `case_100.vtk`, `case_2.vtk`. Alphabetic sort would pick `case_2.vtk` last (highest). Numeric should pick `case_100.vtk`. Assert returns the |U| value from case_100.vtk.

5. **test_read_final_velocity_max_no_timestep_suffix_skipped** (tmp_path): file `bare_case.vtk` (no trailing `_<int>.vtk`). Should be skipped. If no other files match → returns None.

6. **test_g3_boundary_99_U_ref_passes** (monkeypatch VTK reader): `check_all_gates(log, vtk_dir, U_ref=1.0)` where read_final_velocity_max returns 99.0 (just under K*U_ref=100). Assert no G3 violation.

7. **test_g3_boundary_101_U_ref_fails** (monkeypatch VTK reader): same setup with read returning 101.0. Assert G3 violation fires.

8. **test_g3_U_ref_none_behavior**: current code uses `U_ref=1.0` default when caller doesn't pass one. Document this in a test: call with `U_ref=1.0` (explicit) vs the default case. This is less a test of new behavior, more a pin-the-spec regression guard per DEC-036b S1 concern. If U_ref plumbing is Wave 2, skip this test with reason "Wave 2 scope".

## Implementation notes

- `monkeypatch.setattr("pyvista.read", fake_read)` where `fake_read(path_str)` returns a dict-like object with `.point_data` / `.cell_data` attributes containing numpy arrays. Use simple mock class.
- For synthetic logs: use the existing `_write_log` helper in test file (there's likely one; if not, create local helper).
- Tests should be fast: no real VTK I/O, no pyvista actual reads.
- Keep each test < 40 lines.

## Acceptance Checks

CHK-1: All 13 convergence_attestor tests + 8 comparator_gates tests PASS when run with `pytest ui/backend/tests/test_convergence_attestor.py ui/backend/tests/test_comparator_gates_g3_g4_g5.py -q`.

CHK-2: No existing tests fail. If an existing test breaks due to API change (attest() signature, threshold constants), minimal fix only — document each touched line in the output report.

CHK-3: No new pytest fixtures introduced at conftest.py level (keep fixtures local to test file).

## Reject Conditions

REJ-1: Edits outside `allowed_files`.
REJ-2: Refactoring or reformatting existing tests beyond minimum-necessary API updates.
REJ-3: Adding dependencies not currently in pyproject.toml.
REJ-4: Running actual pytest (that's Claude's verification step, not Codex's).
REJ-5: Deleting any existing test.

## Output format

```
# Codex Diff Report — DEC-V61-045 Wave 1 C

## Files modified
- ui/backend/tests/test_convergence_attestor.py [+N/-M]
- ui/backend/tests/test_comparator_gates_g3_g4_g5.py [+N/-M]

## Tests added (per file)
- Per-test one-line description + the CHK it covers

## Existing tests touched (if any)
- file:line — what changed + why (API shift requiring signature update)

## Self-verified checks
- CHK-1..3 PASS/FAIL evidence

## Tokens used
```

---

[/CLAUDE → CODEX TOOL INVOCATION]

codex
正在处理 DEC-V61-045 Wave 1 C。我先做一次轻量上下文恢复：查 memory 里这类 `cfd-harness-unified` 约束，再读目标测试文件和对应实现，确认只在允许文件内补测试。
exec
/bin/zsh -lc 'rg -n "cfd-harness-unified|Phase 8|DEC-V61-045|attestor|comparator_gates" /Users/Zhuanz/.codex/memories/MEMORY.md' in /Users/Zhuanz/Desktop/cfd-harness-unified
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

exec
/bin/zsh -lc "pwd && rg --files . | rg \"ui/backend/tests/test_convergence_attestor.py|ui/backend/tests/test_comparator_gates_g3_g4_g5.py|src/convergence_attestor.py|src/comparator_gates.py|knowledge/attestor_thresholds.yaml|reports/codex_tool_reports/20260422_dec045_wave1_(A|B)_.*\\.md|\\.planning/decisions/2026-04-22_phase8_dec045_attestor_gates_blocker_fixes_PROPOSAL.md\"" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
/Users/Zhuanz/Desktop/cfd-harness-unified
./src/comparator_gates.py
./src/convergence_attestor.py
./reports/codex_tool_reports/20260422_dec045_wave1_A_convergence_attestor_result.md
./reports/codex_tool_reports/20260422_dec045_wave1_A_convergence_attestor_prompt.md
./reports/codex_tool_reports/20260422_dec045_wave1_B_comparator_gates_prompt.md
./reports/codex_tool_reports/20260422_dec045_wave1_B_comparator_gates_result.md
./ui/backend/tests/test_convergence_attestor.py
./knowledge/attestor_thresholds.yaml
./ui/backend/tests/test_comparator_gates_g3_g4_g5.py

codex
先补技能上下文，再读实现与测试骨架。这个切片只做测试补强，我会按最小改动处理，不碰允许范围外文件，也不跑 `pytest`。
exec
/bin/zsh -lc "sed -n '1,220p' /Users/Zhuanz/.codex/skills/auto-compression-agent/SKILL.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '1,220p' /Users/Zhuanz/.codex/plugins/cache/openai-curated/superpowers/27651a43bf55185d924f7a1fc49043a0a8be65a0/skills/using-superpowers/SKILL.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
---
name: auto-compression-agent
description: >
  An always-active intelligent context compression skill for all coding and research sessions.
  Activates automatically on any development task — multi-file coding, bug fixing, repo exploration,
  research synthesis, or long-running agent sessions. Monitors 6 real-time signals and triggers
  layered compression before drift occurs. Never miss a compression opportunity.
---

# Auto-Compression Agent

An intelligent, always-on context compression system that monitors 6 signals in real-time and
triggers layered compression BEFORE drift becomes severe. This is not a reactive checkpoint tool —
it is a proactive monitoring and compression framework.

## Core Principle

**Compress before you drift, not after you already drifted.**

Your baseline data proves the old model (50% threshold, compress when things feel noisy) is too slow.
Evidence drift appears in the **first minute** of failing sessions. By the time you hit 50% context,
you've already lost.

---

## The 6 Real-Time Signals

After EVERY significant interaction, silently evaluate these signals:

### Signal 1: Evidence Drift Count (EARLIEST WARNING)
**Trigger: ≥2 uncertain expressions in a single response**

Uncertain expressions: "可能是", "大概是", "应该是", "估计", "也许", "可能", "不确定", "凭感觉"

**This is your free early warning system.** Evidence drift often appears 5-10 minutes before
any other drift type. When you catch 2 in one response, compress immediately.

### Signal 2: Context Pressure
**Trigger: ≥20% context usage**

Monitor token_count events. The thresholds:
- **20%**: Mini compression (one-line state reset)
- **35%**: Standard compression (structured checkpoint)
- **50%**: Deep compression (full phase summary) + forced rebuild
- **65%**: Emergency — stop, compress everything, rebuild from scratch

### Signal 3: Phase Transition
**Trigger: Moving between exploration → implementation → validation**

Every time you shift phases:
- Exploration ended, implementation starting → compress exploration findings
- Implementation ended, testing/validation starting → compress implementation state
- Validation ended, cleanup/refinement → compress validation results

### Signal 4: Tool Failure Cascade
**Trigger: ≥2 consecutive tool failures without a strategy change**

If you try the same approach 2+ times and it keeps failing, compress the failed-attempt log
and the current state before trying a third time.

### Signal 5: Constraint Forget
**Trigger: Re-reading a file you've already read, or reasking for information already provided**

If the user says "as I mentioned before" or you catch yourself re-reading the same file,
compress immediately — your context has a gap.

### Signal 6: Plan Oscillation
**Trigger: ≥3 "改成" / "推翻" / "重新" signals within 10 minutes**

This means the plan is unstable. Compress the decision ledger and force a firm next action.

---

## The Three Compression Tiers

### Tier 1: Mini Compression (20% context OR 2 evidence drift signals)

One-line state reset. Output this format:

```
[COMPRESS-1] <objective> | <3 stable facts> | <next action> | <1 open risk>
```

Example:
```
[COMPRESS-1] Fix pricing.py discount order | tier before promo | confirmed current-rules.md authoritative | Test: test_pricing.py::test_multiplicative | risk: historical-notes.md still in context
```

### Tier 2: Standard Compression (35% context OR phase transition OR tool failure cascade)

Full structured checkpoint. Use the template in `references/checkpoint-templates.md`.
This is the most common compression type.

Output a checkpoint AND immediately continue from it — do not wait.

### Tier 3: Deep Compression (50%+ context OR emergency signal)

Full phase summary + context rebuild. This compresses everything accumulated so far
and produces a clean-slate restart recipe.

Steps:
1. Write the deep checkpoint using the full template
2. Acknowledge the compression to the user
3. Rebuild the minimum working context from the checkpoint
4. Continue with only the checkpoint + immediate needs

---

## The Five-Layer Working Model

At all times, maintain these five layers. Compressions preserve layers 1-3
and replace large layer-4 artifacts with references.

```
Layer 1: Working Context — only what the NEXT step needs
Layer 2: Task State — goal, constraints, completion criteria
Layer 3: Decision Ledger — what you decided, why, what you rejected
Layer 4: Artifact Index — files, URLs, commands, docs (with paths/references)
Layer 5: Open Loops — unresolved questions, risks, failed attempts
```

Compression is successful when Layer 1 is executable without reading Layer 4 artifacts.

---

## Checkpoint Quality Standards

Every checkpoint MUST pass the **Stranger Test**:

> "A colleague who has never seen this conversation could read this checkpoint,
> reopen 1-2 artifacts, and continue the task in under 5 minutes with no additional questions."

Checklist before finalizing any checkpoint:
- [ ] Contains exactly one concrete **next action** (not "keep going")
- [ ] Stable facts are separated from hypotheses
- [ ] Rejected paths include WHY they were rejected
- [ ] File references are absolute paths, not descriptions
- [ ] Open risks are explicitly named, not just implied
- [ ] No raw tool output or terminal logs
- [ ] Shorter than the material it replaces

---

## Anti-Patterns (Never Do These)

1. **Hour-by-hour narrative** — compress events, not timelines
2. **Raw tool output** — rerun commands, don't paste their output
3. **Confirmed + guessed mixed** — mark uncertainty explicitly
4. **"Just in case" files** — only keep files that change the next action
5. **Vague next actions** — "keep working on X" is not a next action
6. **Dropping failed attempts** — the rejected path IS the value

---

## Context Pressure Dashboard

After every compression, briefly note the current state using this compact format:

```
[CP: XX%] [PHASE: explore/impl/valid] [DRIFT: evidence:N goal:N plan:N] [NEXT: <1 sentence>]
```

This goes in your working context and is updated after every compression.
You can output this silently in commentary.

---

## When to Output Compression Status

You do NOT need to announce every compression to the user.
Only announce when:
- You are triggering a Tier 2 or Tier 3 compression
- The compression reveals something important about the task state
- The user asks about progress or context

Otherwise, compress silently and continue.

---

## Running Summary Requirement

When you finish a session, output:

```
## Session Summary
- Checkpoints created: N
- Compression triggers: <list the signal types that fired>
- Final context pressure: XX%
- Unresolved risks: <1-3 bullets>
- Next session starting point: <checkpoint location or recreation recipe>
```

This is required for any task that took more than 15 minutes or 3 tool calls.

---

## Relationship to context-compression-agent

The `context-compression-agent` skill provides the foundational framework.
This skill (`auto-compression-agent`) overrides it when both are available,
because it provides earlier triggers, multi-tier compression, and proactive monitoring.

If you need the full checkpoint templates or eval protocol,
those are in `references/` alongside this skill.

## References

- `references/checkpoint-templates.md` — Full templates for all three tiers
- `references/eval-protocol.md` — How to measure if compression is working
- `references/trigger-logic.md` — Decision tree for which compression tier to use

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
/bin/zsh -lc "sed -n '1,220p' /Users/Zhuanz/.codex/plugins/cache/openai-curated/superpowers/27651a43bf55185d924f7a1fc49043a0a8be65a0/skills/verification-before-completion/SKILL.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
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
使用 `using-superpowers` 做技能约束校准，`auto-compression-agent` 监控上下文漂移，收尾前按 `verification-before-completion` 只陈述有证据的状态。现在读取实现、现有测试和 DEC 文档，锁定需要补的断言形态。
exec
/bin/zsh -lc "sed -n '1,240p' ui/backend/tests/test_convergence_attestor.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
"""DEC-V61-038 tests: convergence attestor A1..A6.

Coverage: each check's PASS/HAZARD/FAIL branch + LDC/BFS integration
(real audit logs at reports/phase5_fields/*).

Ground truth from Codex round-1 physics audit (DEC-036):
  LDC    → ATTEST_PASS (all 6 checks PASS or N/A)
  BFS    → ATTEST_FAIL via A2 (sum_local=5.25e+18) + A3 HAZARD + A5 HAZARD
  DHC    → ATTEST_PASS (converged, Nu off gold but physics OK)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src import convergence_attestor as ca


def _write_log(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "log.simpleFoam"
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# A1 solver_exit_clean
# ---------------------------------------------------------------------------

def test_a1_passes_on_clean_log(tmp_path: Path) -> None:
    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
    result = ca.attest(log)
    a1 = next(c for c in result.checks if c.check_id == "A1")
    assert a1.verdict == "PASS"


def test_a1_fails_on_foam_fatal(tmp_path: Path) -> None:
    content = "Time = 1\nFOAM FATAL IO ERROR: missing dict\nExiting\n"
    log = _write_log(tmp_path, content)
    result = ca.attest(log)
    a1 = next(c for c in result.checks if c.check_id == "A1")
    assert a1.verdict == "FAIL"
    assert result.overall == "ATTEST_FAIL"


def test_a1_ignores_sigfpe_startup_banner(tmp_path: Path) -> None:
    """DEC-036b Codex nit: 'floating point exception trapping' is a
    startup banner, not an actual exception. Must NOT fire A1."""
    content = (
        "sigFpe : Enabling floating point exception trapping (FOAM_SIGFPE).\n"
        "Time = 1\nEnd\n"
    )
    log = _write_log(tmp_path, content)
    result = ca.attest(log)
    a1 = next(c for c in result.checks if c.check_id == "A1")
    assert a1.verdict == "PASS"


# ---------------------------------------------------------------------------
# A2 continuity_floor
# ---------------------------------------------------------------------------

def test_a2_passes_on_clean_continuity(tmp_path: Path) -> None:
    content = (
        "time step continuity errors : "
        "sum local = 1e-07, global = 1e-09, cumulative = 1e-12\n"
    )
    log = _write_log(tmp_path, content)
    result = ca.attest(log)
    a2 = next(c for c in result.checks if c.check_id == "A2")
    assert a2.verdict == "PASS"


def test_a2_hazard_between_floors(tmp_path: Path) -> None:
    """sum_local between A2 floor (1e-4) and G5 floor (1e-2) → HAZARD."""
    content = (
        "time step continuity errors : "
        "sum local = 1e-03, global = 1e-05, cumulative = 0.001\n"
    )
    log = _write_log(tmp_path, content)
    result = ca.attest(log)
    a2 = next(c for c in result.checks if c.check_id == "A2")
    assert a2.verdict == "HAZARD"


def test_a2_hazard_above_g5_floor_after_split_brain_fix(tmp_path: Path) -> None:
    """Codex DEC-038 round-1 A2/G5 split-brain fix: A2 no longer returns
    FAIL even for sum_local > 1e-2. That FAIL call belongs to G5 at the
    gate layer. A2 stays strictly HAZARD-tier."""
    content = (
        "time step continuity errors : "
        "sum local = 0.5, global = 0.01, cumulative = 0.1\n"
    )
    log = _write_log(tmp_path, content)
    result = ca.attest(log)
    a2 = next(c for c in result.checks if c.check_id == "A2")
    assert a2.verdict == "HAZARD"  # was FAIL pre-fix


# ---------------------------------------------------------------------------
# A3 residual_floor
# ---------------------------------------------------------------------------

def test_a3_passes_when_all_residuals_below_floor(tmp_path: Path) -> None:
    content = (
        "smoothSolver:  Solving for Ux, Initial residual = 1e-06, "
        "Final residual = 1e-07, No Iterations 2\n"
    )
    log = _write_log(tmp_path, content)
    result = ca.attest(log)
    a3 = next(c for c in result.checks if c.check_id == "A3")
    assert a3.verdict == "PASS"


def test_a3_hazard_when_final_residual_above_floor(tmp_path: Path) -> None:
    content = (
        "smoothSolver:  Solving for Ux, Initial residual = 0.05, "
        "Final residual = 0.001, No Iterations 20\n"
    )
    log = _write_log(tmp_path, content)
    result = ca.attest(log)
    a3 = next(c for c in result.checks if c.check_id == "A3")
    assert a3.verdict == "HAZARD"
    assert "Ux" in a3.evidence["offenders"]


# ---------------------------------------------------------------------------
# A4 solver_iteration_cap
# ---------------------------------------------------------------------------

def test_a4_fails_on_consecutive_cap_hits(tmp_path: Path) -> None:
    """5 consecutive Time= blocks each with a capped GAMG p solve → FAIL.

    Codex round-1 BLOCKER 2: measurement unit changed from consecutive
    lines to consecutive TIME STEPS. Each `Time =` divider opens a new
    block, so this test now needs Time= dividers.
    """
    content = "".join(
        f"Time = {i}\nGAMG:  Solving for p, Initial residual = 0.9, "
        "Final residual = 0.5, No Iterations 1000\n"
        for i in range(5)
    )
    log = _write_log(tmp_path, content)
    result = ca.attest(log)
    a4 = next(c for c in result.checks if c.check_id == "A4")
    assert a4.verdict == "FAIL"
    assert a4.evidence["consecutive_cap_blocks"] >= 3


def test_a4_fails_on_p_rgh_buoyant_log(tmp_path: Path) -> None:
    """Codex DEC-038 round-1 BLOCKER 1: impinging_jet stuck solver is
    `GAMG: Solving for p_rgh` in log.buoyantFoam — A4 regex must match
    p_rgh (not just `p,`) to catch the real impinging_jet case.
    """
    content = "\n".join(
        [f"Time = {i}s\nGAMG:  Solving for p_rgh, Initial residual = 0.7, "
         "Final residual = 0.5, No Iterations 1000"
         for i in range(5)]
    )
    log = _write_log(tmp_path, content)
    result = ca.attest(log)
    a4 = next(c for c in result.checks if c.check_id == "A4")
    assert a4.verdict == "FAIL", f"got {a4.verdict}: {a4.summary}"


def test_a4_fails_on_dicpcg_p_rgh(tmp_path: Path) -> None:
    """DHC uses DICPCG: Solving for p_rgh. Same regex coverage requirement."""
    content = "\n".join(
        [f"Time = {i*0.5}s\nDICPCG:  Solving for p_rgh, Initial residual = 0.8, "
         "Final residual = 0.6, No Iterations 1000"
         for i in range(1, 6)]
    )
    log = _write_log(tmp_path, content)
    result = ca.attest(log)
    a4 = next(c for c in result.checks if c.check_id == "A4")
    assert a4.verdict == "FAIL"


def test_a4_multi_corrector_pimple_counts_blocks_not_lines(tmp_path: Path) -> None:
    """Codex DEC-038 round-1 BLOCKER 2: PIMPLE emits multiple pressure
    solves per Time= block. A4 must count BLOCKS, not LINES — 2 cap-hits
    within the same block should count as 1 toward consecutive threshold,
    not 2. Here 2 blocks × 2 cap-hits = 4 lines but only 2 blocks, so
    consecutive=2 < 3 → PASS. A 3rd capped block is needed to FAIL.
    """
    # 2 capped blocks — should NOT fire (need 3 consecutive blocks).
    content = (
        "Time = 1s\n"
        "GAMG:  Solving for p_rgh, Initial residual = 0.7, Final residual = 0.5, No Iterations 1000\n"
        "GAMG:  Solving for p_rgh, Initial residual = 0.7, Final residual = 0.5, No Iterations 1000\n"
        "Time = 2s\n"
        "GAMG:  Solving for p_rgh, Initial residual = 0.7, Final residual = 0.5, No Iterations 1000\n"
        "GAMG:  Solving for p_rgh, Initial residual = 0.7, Final residual = 0.5, No Iterations 1000\n"
    )
    log = _write_log(tmp_path, content)
    result = ca.attest(log)
    a4 = next(c for c in result.checks if c.check_id == "A4")
    assert a4.verdict == "PASS", f"2 blocks should not fire A4 (threshold=3); got {a4.verdict}"


def test_a4_fires_after_three_consecutive_blocks(tmp_path: Path) -> None:
    """3 consecutive capped blocks → FAIL, regardless of per-block count."""
    content = "".join(
        f"Time = {i}s\n"
        "GAMG:  Solving for p_rgh, Initial residual = 0.7, Final residual = 0.5, No Iterations 1000\n"
        "GAMG:  Solving for p_rgh, Initial residual = 0.7, Final residual = 0.5, No Iterations 1000\n"
        for i in range(1, 4)
    )
    log = _write_log(tmp_path, content)
    result = ca.attest(log)
    a4 = next(c for c in result.checks if c.check_id == "A4")
    assert a4.verdict == "FAIL"
    assert a4.evidence["consecutive_cap_blocks"] == 3


def test_attestor_not_applicable_when_log_missing(tmp_path: Path) -> None:
    """Codex DEC-038 round-1 comment C: missing log → ATTEST_NOT_APPLICABLE,
    distinct from ATTEST_PASS. DEC-V61-040 UI tiers will surface this
    explicitly for reference/visual_only runs that have no solver log.
    """
    result = ca.attest(None)
    assert result.overall == "ATTEST_NOT_APPLICABLE"
    result = ca.attest(tmp_path / "missing.log")
    assert result.overall == "ATTEST_NOT_APPLICABLE"


def test_a2_never_returns_fail_only_hazard(tmp_path: Path) -> None:
    """Codex DEC-038 round-1 comment A7: A2 stays HAZARD-tier to avoid
    split-brain with G5. Even sum_local=0.5 returns HAZARD from A2 (G5
    is responsible for the FAIL call at the gate layer)."""
    content = (
        "time step continuity errors : "
        "sum local = 0.5, global = 0.01, cumulative = 0.1\n"
    )
    log = _write_log(tmp_path, content)
    result = ca.attest(log)
    a2 = next(c for c in result.checks if c.check_id == "A2")
    assert a2.verdict == "HAZARD"  # was FAIL pre-fix


exec
/bin/zsh -lc "sed -n '1,240p' .planning/decisions/2026-04-22_phase8_dec045_attestor_gates_blocker_fixes_PROPOSAL.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '1,260p' ui/backend/tests/test_comparator_gates_g3_g4_g5.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '1,220p' knowledge/attestor_thresholds.yaml" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
---
decision_id: DEC-V61-045
status: PROPOSAL (awaiting Kogami scope approval before execution)
timestamp: 2026-04-22T19:20 local
scope: |
  Phase 8 Sprint 1 follow-up — fix 8 Codex blockers across DEC-036b
  (CHANGES_REQUIRED, 3 blockers + 2 nits) and DEC-038 (BLOCK, 5 blockers
  + 3 nits). v6.2 independent-verification protocol surfaced substantial
  gaps between DEC-stated contracts and landed implementation. Combined
  fix DEC because both sides share orchestration touchpoints
  (_audit_fixture_doc + _derive_contract_status + TaskRunner flow).

  This DEC is a PROPOSAL — awaiting Kogami approval of scope + approach
  before any code change. Once approved, this becomes DEC-V61-045 with
  autonomous_governance path and pre-merge Codex review (self-pass well
  below 0.70 given complexity).

autonomous_governance: pending_kogami_approval
claude_signoff: proposal_only
codex_tool_invoked: false (no diff yet; pre-merge required before landing)
codex_rounds: 0
codex_verdict: not_yet_requested
external_gate_self_estimated_pass_rate: 0.50
  (Complex multi-module change touching orchestration + verdict engine +
  new YAML schema + attestor-pre-extraction reordering + 4-5 physics
  semantics fixes. self-pass notably low because the blast radius
  includes: (a) task_runner execution order change risks comparison_result
  not being populated for in-tolerance healthy runs, (b) HAZARD tier
  propagating to UI/API snapshot tests that may require fixture rebase,
  (c) A6 outer-iteration semantics redesign is genuinely non-trivial
  physics reasoning.)
reversibility: |
  Partially reversible. New YAML file is additive; tier wiring in
  _derive_contract_status is additive HAZARD set; attestor-pre-extraction
  move is a reordering (reversible by swap-back). A6 semantics rewrite is
  a behavior change that breaks impinging_jet expectations — irreversible
  without spec decision on correct A6 model.
---

# DEC-V61-045 (PROPOSAL): Attestor + Gates Blocker Fix Bundle

## Upstream findings

Both source DECs have codex_verdict on main but landed code contradicts DEC spec:

### DEC-V61-036b (CHANGES_REQUIRED)
Codex report: `reports/codex_tool_reports/20260422_dec036b_codex_review.md`
Codex independent pass-rate: 0.42 (claude-estimated 0.60)

- **B1** `expected_verdict` decided before attestor/gates run, never recomputed → stale PASS in fixture metadata + CLI summary
- **B2** G3 `U_ref` never resolved from `task_spec.boundary_conditions`; all cases audited at default 1.0
- **B3** `read_final_velocity_max()` scans every VTK incl. allPatches + earlier timesteps → false-positives
- S1 WARN paths print to stdout but don't stamp WARN concern
- S2 test coverage weaker than DEC claims

### DEC-V61-038 (BLOCK)
Codex report: `reports/codex_tool_reports/20260422_dec038_codex_review.md`
Codex independent pass-rate: 0.33 (claude-estimated 0.65)

- **CA-001** `_derive_contract_status()` hard-fails ONLY on A1/A4; A2/A3/A5/A6 ignored → in-band scalar w/ CONTINUITY_NOT_CONVERGED still returns PASS (defeats two-tier model)
- **CA-002** `TaskRunner.run_task()` executes comparator BEFORE attestor → non-converged runs flow through extraction+correction (violates "attestor first" contract)
- **CA-003** A1 log-only; never consumes `ExecutionResult.success` exit code; only matches `^Floating point exception`
- **CA-004** `knowledge/attestor_thresholds.yaml` DOES NOT EXIST despite being referenced → per-case override + HAZARD→FAIL promotion non-functional
- **CA-005** A3/A6 field-agnostic; produces incorrect A6 HAZARD on impinging_jet p_rgh (DEC expects A4-only)
- CA-006 "stuck" uses `< 1.0` decade, DEC says `<= 1.0`
- CA-007 A4 gap-block consecutiveness stricter than DEC
- CA-008 missing 10-case real-log integration matrix (only LDC+BFS)

## Proposed fix bundle (7 tracks, ordered by dependency)

### Track 1: Land `knowledge/attestor_thresholds.yaml` [DEC-038 CA-004]
- New file per DEC-038 spec section 4
- Schema validation (strict YAML → dataclass)
- Loader in `convergence_attestor.py` with per-case key lookup + default fallback
- Tests: unknown case → defaults; known case → override; malformed YAML → raise

### Track 2: Wire HAZARD tier in `_derive_contract_status` [DEC-038 CA-001]
- Add HAZARD concern set: `{A2: CONTINUITY_NOT_CONVERGED, A3: RESIDUALS_ABOVE_TARGET, A5: BOUNDING_RECURRENT, A6: NO_RESIDUAL_PROGRESS}`
- Promotion rule: per-case override can promote HAZARD→FAIL (from Track 1 YAML)
- Preserve A1/A4 hard-FAIL behavior (unchanged)
- Contract: in-band scalar + any HAZARD concern → `contract_status=HAZARD`
- Tests: 4 new test cases per concern code; 1 promotion override test

### Track 3: Move attestor pre-extraction in TaskRunner [DEC-038 CA-002]
- `TaskRunner.run_task()` reorder: solver → **attestor check** → (if FAIL/HAZARD with promotion) short-circuit correction generation, populate attestor-only ComparisonResult → UI still renders
- If PASS or unpromoted HAZARD → continue with comparator → correction
- Blast radius: `comparison_result` may be None for ATTEST_FAIL; UI/API must handle
- Tests: full E2E per path (PASS / HAZARD / ATTEST_FAIL)

### Track 4: Fix A1 to consume exit_code [DEC-038 CA-003]
- `attest()` takes `execution_result: ExecutionResult | None = None` param
- If `execution_result.success is False` → A1 FAIL regardless of log content
- Regex widen: `(Floating point exception|Floating exception|FOAM FATAL)` with consistent anchoring

### Track 5: Recompute `expected_verdict` post-gates [DEC-036b B1]
- `_audit_fixture_doc()` assembles concerns list → call `_derive_contract_status` helper → write back final verdict to fixture metadata
- Preserve "expected_verdict" as goldens-derived baseline; add "actual_verdict" for post-gate result
- CLI summary prints actual_verdict not expected_verdict

### Track 6: Plumb U_ref from task_spec [DEC-036b B2]
- `_audit_fixture_doc(task_spec, ...)` extract `u_ref = task_spec.boundary_conditions.get_ref_velocity()` helper
- Per flow_type: internal→inlet U, LDC→lid U, external→free-stream, buoyancy→reference
- Unresolved → `WARN` concern stamped in fixture (not just stdout)
- Pass through to `check_all_gates(U_ref=u_ref)`; `None` behaves per Track 4 semantics

### Track 7: Fix `read_final_velocity_max()` [DEC-036b B3]
- Identify latest-time VTK directory by numeric time suffix (not alphabetic sort)
- Exclude `allPatches/*.vtk` and boundary-patch VTK files; internal-field only
- Tests: multi-timestep tree with earlier spike + clean final → no false-fire

### Track 8 (A6 redesign) [DEC-038 CA-005]
- **Non-trivial physics call** — needs Kogami/Codex consultation:
  - Current A6 scans per-field Initial residual lines across every inner PBiCGStab/GAMG solve
  - Multi-solve outer iterations (buoyantFoam, pimpleFoam) have many inner solves per Time= block
  - Correct A6 should compare outer-step residuals (first solve of each Time=) rather than every inner solve
  - impinging_jet regression: A6 must NOT fire (A4 carries it); DHC A6 should still fire if stuck
- Risk: this behavioral change may flip other cases' attestor output

### Track 9 (Test matrix expansion) [DEC-036b S2, DEC-038 CA-008]
- Threshold-boundary tests for G3 (99·U_ref pass / 101·U_ref fail / U_ref=None WARN)
- 10-case real-log integration matrix for attestor (currently only LDC+BFS)
- VTK-branch test with crafted real-timestep-layout fixture
- WARN concern assertions (not just stdout)

## Execution plan

Sequential waves (due to dependency ordering):

**Wave 1**: Track 1 (YAML) + Track 4 (A1 exit-code) + Track 7 (VTK reader) + Track 9a (nit-level tests)
  — Independent, can parallelize via subagents

**Wave 2**: Track 2 (HAZARD tier) + Track 6 (U_ref plumb)
  — Depends on Wave 1 Track 1 (YAML loader for promotion)

**Wave 3**: Track 3 (TaskRunner reorder) + Track 5 (verdict recompute)
  — Depends on Wave 2 (HAZARD tier must be wired before reorder can short-circuit)

**Wave 4**: Track 8 (A6 redesign) + Track 9b (full integration matrix)
  — Highest risk; isolate to final wave for easier rollback

**Codex rounds**: ≥2 required per wave (pre-merge given self-pass 0.50). Total 8 rounds minimum.

## Risks

1. **Fixture rebase cascade**: Wave 2+3 flip many test fixtures from PASS to HAZARD (correct behavior) — this is UI/API snapshot churn.
2. **impinging_jet behavior change**: Wave 4 A6 redesign flips impinging_jet from A4+A6 to A4-only; any downstream consumer expecting A6 concern breaks.
3. **TaskRunner reorder blast radius**: Wave 3 changes task_runner execution order; any caller expecting comparison_result always populated breaks.
4. **YAML schema drift**: Wave 1 introduces YAML schema that must stay forward-compatible.
5. **Self-pass 0.50 realistic**: with 8 tracks and 4 waves, expect ≥1 Codex CHANGES_REQUIRED round before final APPROVE.

## Scope decision points for Kogami

Kogami should explicitly approve/reject:

(a) **Execute all 9 tracks autonomously** (Claude drives, Codex audits per wave) — est. 3-5 sessions
(b) **Execute Waves 1-2 only** (low-risk additive fixes); defer Waves 3-4 to Phase 8 Sprint 2
(c) **Pivot** — accept DEC-036b/038 current state as "known gap" and plan v2 in Sprint 2 rather than patch
(d) **Delete + rewrite** — landed code has substantial contract gap; full rewrite may be cleaner than patch
(e) **Other** — Kogami-defined

Recommendation: **(b) Waves 1-2**. Rationale:
- Wave 1 is low-risk additive (YAML + A1 exit-code + VTK reader + unit tests)
- Wave 2 wires the HAZARD tier which is the single most important gap (CA-001)
- Wave 3 (TaskRunner reorder) has high blast radius; deferring allows Sprint 2 dedicated session
- Wave 4 (A6 redesign) needs physics discussion, not just code change
- Delivering Waves 1-2 captures ~60% of blocker remediation with ~30% of total risk

---

**Status**: PROPOSAL ONLY. No code changed. Awaiting Kogami scope decision.
**Author**: Claude Code Opus 4.7 (v6.2 Main Driver)
**Related**: DEC-V61-036b (CHANGES_REQUIRED), DEC-V61-038 (BLOCK)

 succeeded in 0ms:
# Convergence Attestor Thresholds — per-case override registry
#
# Referenced by: src/convergence_attestor.py (loader added per DEC-V61-045 Track 1)
# Specified by: DEC-V61-038 §3 Per-case thresholds
# Remediation: Codex DEC-038 CA-004 (YAML absent) + CA-005 (A3 field-agnostic)
#
# Tier semantics:
# - A1 (solver_exit_clean):   always FAIL
# - A2 (continuity_floor):    HAZARD default; per-case promote_to_fail list can raise
# - A3 (residual_floor):      HAZARD default; per-field + per-case thresholds
# - A4 (iteration_cap):       always FAIL
# - A5 (bounding_recurrence): HAZARD default
# - A6 (no_progress):         HAZARD default; per-case decade-window override
#
# Schema version: 1 (additive-only changes; bump on breaking change)

schema_version: 1

defaults:
  # A2: global sum_local floor (incompressible steady target)
  continuity_floor: 1.0e-4

  # A3: fallback residual floor if field not in residual_floor_per_field
  residual_floor: 1.0e-3

  # A3: per-field targets (CA-005 fix — field-aware thresholding)
  # Unknown fields fall back to residual_floor above.
  residual_floor_per_field:
    Ux: 1.0e-3
    Uy: 1.0e-3
    Uz: 1.0e-3
    p: 1.0e-3
    p_rgh: 1.0e-2     # buoyant/multiphase pressure plateaus one decade higher
    k: 1.0e-3
    epsilon: 1.0e-3
    omega: 1.0e-3
    nuTilda: 1.0e-3
    h: 1.0e-3         # buoyant enthalpy
    T: 1.0e-3

  # A4: consecutive-capped-block count before FAIL
  iteration_cap_detector_count: 3

  # A5: bounding-recurrence window + trigger fraction
  bounding_recurrence_frac_threshold: 0.30
  bounding_recurrence_window: 50

  # A6: no-progress window (outer-step residuals) + min decade-of-decay required
  # CA-006 fix: criterion is <= 1.0 decade (not < 1.0) for "stuck"
  no_progress_decade_frac: 1.0
  no_progress_window: 50

# Per-case overrides. Missing keys inherit from defaults.
# Case IDs must match task_spec.task_id (snake_case whitelist IDs).
per_case:

  impinging_jet:
    # Stagnation region p_rgh plateaus higher; DEC-038 expected behavior:
    # A4 FAIL (1000-iter cap) carries the verdict; A6 should NOT fire.
    residual_floor_per_field:
      p_rgh: 5.0e-3
    # A6 disabled (legitimate inner-solve repeats look like stuck outer-step
    # residuals under old per-solve semantics; see CA-005 fix in Track 8)
    promote_to_fail: []

  rayleigh_benard_convection:
    # Oscillatory instability — residuals don't decay monotonically.
    residual_floor_per_field:
      h: 2.0e-3
      p_rgh: 2.0e-3
    no_progress_decade_frac: 0.3  # legitimate oscillation tolerance
    promote_to_fail: []

  circular_cylinder_wake:
    # Unsteady pimpleFoam — per-step continuity wobble normal.
    continuity_floor: 1.0e-3
    promote_to_fail: []

  differential_heated_cavity:
    # Buoyant-simple at Ra=1e10; BL-coupled residuals plateau higher.
    residual_floor_per_field:
      h: 1.0e-2
      p_rgh: 1.0e-2
    promote_to_fail: []

  # Steady canonical cases inherit all defaults (no override needed):
  # - lid_driven_cavity (laminar; A5 N/A by construction)
  # - backward_facing_step (kEpsilon; DEC expectation: broken fixture → FAIL)
  # - turbulent_flat_plate (SST; DEC expectation: broken fixture → FAIL)
  # - plane_channel_flow (DNS log-style; standard floors apply)
  # - naca0012_airfoil (steady SA; standard floors)
  # - duct_flow (steady kEpsilon; DEC expectation: broken fixture → FAIL)

# Forward-compat: additional keys under defaults or per_case are non-breaking.
# Loader should warn on unknown top-level keys, accept unknown nested keys.

 succeeded in 0ms:
"""DEC-V61-036b tests: hard comparator gates G3 (velocity overflow),
G4 (turbulence negativity), G5 (continuity divergence).

Evidence sources:
  * BFS audit log shows catastrophic blowup (sum_local=5.24e+18,
    cumulative=-1434.64, k min=-6.41e+30). Synthetic logs in this file
    reproduce those markers for deterministic unit testing.
  * LDC audit log shows clean convergence (sum_local ≈ 1e-6, k laminar
    skipped). Synthetic clean logs assert G3/G4/G5 all pass.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src import comparator_gates as cg
from ui.backend.main import app


# ---------------------------------------------------------------------------
# Shared synthetic log fixtures
# ---------------------------------------------------------------------------

_CLEAN_LDC_LOG = """\
Time = 500

DICPCG:  Solving for p, Initial residual = 1e-08, Final residual = 1e-09, No Iterations 2
time step continuity errors : sum local = 4.5e-08, global = -1.2e-09, cumulative = 3.1e-08
ExecutionTime = 12.3 s  ClockTime = 14 s

End
"""

_BFS_BLOWUP_TAIL = """\
Time = 50

smoothSolver:  Solving for Ux, Initial residual = 0.9, Final residual = 0.6, No Iterations 12
smoothSolver:  Solving for Uy, Initial residual = 0.8, Final residual = 0.5, No Iterations 12
GAMG:  Solving for p, Initial residual = 0.99, Final residual = 0.9, No Iterations 25
time step continuity errors : sum local = 5.24523e+18, global = -1328.63, cumulative = -1434.64
smoothSolver:  Solving for epsilon, Initial residual = 0.8, Final residual = 0.4, No Iterations 3
bounding epsilon, min: 7.38706e-17 max: 1.03929e+30 average: 1.37234e+27
smoothSolver:  Solving for k, Initial residual = 0.7, Final residual = 0.4, No Iterations 4
bounding k, min: -6.41351e+30 max: 2.32895e+31 average: 1.39855e+29
ExecutionTime = 0.6 s  ClockTime = 0 s
"""


def _write_log(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "log.simpleFoam"
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Log parsing
# ---------------------------------------------------------------------------

def test_parse_solver_log_extracts_continuity_and_bounding(tmp_path: Path) -> None:
    log = _write_log(tmp_path, _BFS_BLOWUP_TAIL)
    stats = cg.parse_solver_log(log)
    assert stats.final_continuity_sum_local == pytest.approx(5.24523e18)
    assert stats.final_continuity_cumulative == pytest.approx(-1434.64)
    assert "k" in stats.bounding_last
    assert stats.bounding_last["k"]["min"] == pytest.approx(-6.41351e30)
    assert stats.bounding_last["epsilon"]["max"] == pytest.approx(1.03929e30)
    assert stats.fatal_detected is False


def test_parse_solver_log_detects_foam_fatal(tmp_path: Path) -> None:
    content = _CLEAN_LDC_LOG + "\nFOAM FATAL IO ERROR: missing dictionary key\n"
    log = _write_log(tmp_path, content)
    stats = cg.parse_solver_log(log)
    assert stats.fatal_detected is True


# ---------------------------------------------------------------------------
# G5 — continuity divergence
# ---------------------------------------------------------------------------

def test_g5_fails_on_sum_local_overflow(tmp_path: Path) -> None:
    log = _write_log(tmp_path, _BFS_BLOWUP_TAIL)
    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
    g5 = [v for v in violations if v.gate_id == "G5"]
    assert len(g5) == 1
    assert g5[0].concern_type == "CONTINUITY_DIVERGED"
    assert g5[0].evidence["sum_local"] == pytest.approx(5.24523e18)


def test_g5_fails_on_cumulative_only(tmp_path: Path) -> None:
    # sum_local within threshold, cumulative huge — second branch.
    content = (
        "time step continuity errors : "
        "sum local = 1e-04, global = 0.001, cumulative = 2.5\n"
    )
    log = _write_log(tmp_path, content)
    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
    g5 = [v for v in violations if v.gate_id == "G5"]
    assert len(g5) == 1
    assert g5[0].evidence["cumulative"] == pytest.approx(2.5)


def test_g5_passes_on_clean_ldc_log(tmp_path: Path) -> None:
    log = _write_log(tmp_path, _CLEAN_LDC_LOG)
    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
    g5 = [v for v in violations if v.gate_id == "G5"]
    assert g5 == []


# ---------------------------------------------------------------------------
# G4 — turbulence negativity
# ---------------------------------------------------------------------------

def test_g4_fails_on_negative_k_at_last_iter(tmp_path: Path) -> None:
    log = _write_log(tmp_path, _BFS_BLOWUP_TAIL)
    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
    g4 = [v for v in violations if v.gate_id == "G4"]
    # BFS log shows k min=-6.4e30 AND epsilon max=1.03e30 — both fire G4
    # (negative branch for k, overflow branch for epsilon).
    concern_fields = {v.evidence["field"] for v in g4}
    assert "k" in concern_fields
    assert any(v.evidence.get("min", 1.0) < 0 for v in g4)


def test_g4_fails_on_epsilon_overflow_without_negative(tmp_path: Path) -> None:
    content = (
        "bounding epsilon, min: 1e-5 max: 1e+30 average: 1e+26\n"
        "bounding k, min: 1e-6 max: 0.5 average: 0.01\n"
    )
    log = _write_log(tmp_path, content)
    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
    g4 = [v for v in violations if v.gate_id == "G4"]
    assert len(g4) == 1
    assert g4[0].evidence["field"] == "epsilon"
    assert g4[0].evidence["max"] == pytest.approx(1e30)


def test_g4_passes_on_clean_ldc_log(tmp_path: Path) -> None:
    # LDC is laminar — no bounding lines emitted. G4 should return no violations.
    log = _write_log(tmp_path, _CLEAN_LDC_LOG)
    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
    g4 = [v for v in violations if v.gate_id == "G4"]
    assert g4 == []


# ---------------------------------------------------------------------------
# G3 — velocity overflow (log-proxy branch; VTK branch gated by pyvista)
# ---------------------------------------------------------------------------

def test_g3_proxy_fails_on_epsilon_overflow(tmp_path: Path) -> None:
    log = _write_log(tmp_path, _BFS_BLOWUP_TAIL)
    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
    g3 = [v for v in violations if v.gate_id == "G3"]
    assert len(g3) == 1
    assert g3[0].concern_type == "VELOCITY_OVERFLOW"
    # BFS epsilon max=1.03e30 → inferred u ~ (1e30)^(1/3) = 1e10
    assert g3[0].evidence["epsilon_max"] == pytest.approx(1.03929e30)


def test_g3_passes_on_clean_ldc_log(tmp_path: Path) -> None:
    log = _write_log(tmp_path, _CLEAN_LDC_LOG)
    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
    g3 = [v for v in violations if v.gate_id == "G3"]
    assert g3 == []


# ---------------------------------------------------------------------------
# NaN/Inf safety (Codex DEC-036b round-1 nit)
# ---------------------------------------------------------------------------

def test_g5_fires_on_nan_sum_local(tmp_path: Path) -> None:
    """OpenFOAM overflowed → prints `nan` for continuity; gate must fire."""
    content = (
        "time step continuity errors : "
        "sum local = nan, global = 0.01, cumulative = -0.5\n"
    )
    log = _write_log(tmp_path, content)
    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
    g5 = [v for v in violations if v.gate_id == "G5"]
    assert len(g5) == 1, f"expected G5 on nan sum_local, got {violations}"


def test_g4_fires_on_inf_k_max(tmp_path: Path) -> None:
    """+inf in bounding line must fire G4 (not silently skip)."""
    content = "bounding k, min: 1e-5 max: inf average: 1e+20\n"
    log = _write_log(tmp_path, content)
    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
    g4 = [v for v in violations if v.gate_id == "G4"]
    assert len(g4) == 1
    assert g4[0].evidence["field"] == "k"


# ---------------------------------------------------------------------------
# BFS integration — all three gates fire on the real BFS audit log
# ---------------------------------------------------------------------------

_REAL_BFS_LOG = Path(
    "/Users/Zhuanz/Desktop/cfd-harness-unified/reports/phase5_fields/"
    "backward_facing_step/20260421T125637Z/log.simpleFoam"
)


@pytest.mark.skipif(not _REAL_BFS_LOG.is_file(), reason="BFS phase7a log absent")
def test_gates_fire_on_real_bfs_audit_log() -> None:
    violations = cg.check_all_gates(log_path=_REAL_BFS_LOG, vtk_dir=None, U_ref=1.0)
    gate_ids = {v.gate_id for v in violations}
    # BFS must trigger G5 (continuity) + G4 (turbulence) + G3 (velocity proxy).
    assert {"G3", "G4", "G5"}.issubset(gate_ids)


# ---------------------------------------------------------------------------
# Integration with validation_report verdict engine
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


def test_validation_report_hard_fails_on_velocity_overflow_concern() -> None:
    """Fixture with VELOCITY_OVERFLOW concern must hard-FAIL the verdict."""
    from ui.backend.schemas.validation import (
        AuditConcern,
        GoldStandardReference,
        MeasuredValue,
    )
    from ui.backend.services.validation_report import _derive_contract_status

    gs = GoldStandardReference(
        quantity="friction_factor",
        ref_value=0.0185,
        unit="dimensionless",
        tolerance_pct=0.10,
        citation="Colebrook 1939",
    )
    # Value IS inside the tolerance band — would normally PASS.
    m = MeasuredValue(
        value=0.0185,
        source="fixture",
        quantity="friction_factor",
        extraction_source="comparator_deviation",
    )
    concerns = [
        AuditConcern(
            concern_type="VELOCITY_OVERFLOW",
            summary="|U|_max=1e10",
        )
    ]
    status, deviation, within, _, _ = _derive_contract_status(
        gs, m, preconditions=[], audit_concerns=concerns
    )
    # DEC-V61-036b: VELOCITY_OVERFLOW overrides a "within band" comparator PASS.
    # Codex round-1 nit applied: within_tolerance is nulled when hard-fail
    # concern fires, so the UI doesn't render "Within band: yes" under FAIL.
    assert status == "FAIL"
    assert deviation == pytest.approx(0.0, abs=1e-9)
    assert within is None  # nulled per Codex nit (value IS inside band, but trust is null)

exec
/bin/zsh -lc "sed -n '1,220p' reports/codex_tool_reports/20260422_dec045_wave1_B_comparator_gates_result.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
2026-04-22T11:25:14.125500Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-research-deerflow/SKILL.md: missing YAML frontmatter delimited by ---
2026-04-22T11:25:14.125521Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-report-pretext/SKILL.md: missing YAML frontmatter delimited by ---
OpenAI Codex v0.118.0 (research preview)
--------
workdir: /Users/Zhuanz/Desktop/cfd-harness-unified
model: gpt-5.4
provider: openai
approval: never
sandbox: workspace-write [workdir, /tmp, $TMPDIR, /Users/Zhuanz/.codex/memories]
reasoning effort: xhigh
reasoning summaries: none
session id: 019db4ef-e60e-7651-9e1f-66213e5c9722
--------
user
# [CLAUDE → CODEX TOOL INVOCATION]

    from: claude-code-opus47 (Main Driver v6.2)
    to: codex-gpt54-xhigh (Joint Dev Peer · §A Diff Generator)
    task: "DEC-V61-045 Wave 1 Invocation B — comparator_gates.py VTK reader fix"
    contract: Notion DEC-V61-045 PROPOSAL
    spec: .planning/decisions/2026-04-22_phase8_dec045_attestor_gates_blocker_fixes_PROPOSAL.md
    upstream_findings:
      - reports/codex_tool_reports/20260422_dec036b_codex_review.md (CHANGES_REQUIRED, B3 finding)

    scope_tracks:
      - Track 7: Fix read_final_velocity_max() to use latest-time internal-field VTK only

    allowed_files:
      - src/comparator_gates.py

    read_only_context:
      - reports/phase5_fields/lid_driven_cavity/<ts>/VTK/   (real VTK layout reference)
      - reports/phase5_fields/circular_cylinder_wake/<ts>/VTK/  (multi-timestep layout)
      - reports/codex_tool_reports/20260422_dec036b_codex_review.md  (finding B3)

    forbidden_files:
      - any file not in allowed_files
      - especially tests/, scripts/, ui/backend/

    autonomy: TOOL-SCOPE

---

## Problem statement (from Codex DEC-036b B3)

Current `read_final_velocity_max()` at `src/comparator_gates.py:194-245` scans every `*.vtk` under the VTK tree via `vtk_dir.rglob("*.vtk")`. This:

1. **Includes `allPatches/*.vtk`** — these are boundary-patch exports, NOT internal-field. A boundary velocity spike (e.g., LDC lid moving at U=1) propagates into `u_max` even when internal field is clean.
2. **Includes earlier timesteps** — foamToVTK emits `{case}_{timestep}.vtk` for each time. An early-iter velocity transient can false-fire G3 even if the final solution converged to clean field.
3. **Sorts alphabetically** — `sorted(vtk_dir.rglob(...))` gives alphabetical order, which does NOT guarantee latest-time last. `case_100.vtk` sorts after `case_1000.vtk` alphabetically? Actually no, Python string sort: `case_100.vtk` < `case_1000.vtk` (shorter comes first with prefix match). But `case_2.vtk` > `case_1000.vtk` (2 > 1 at position 5). So alphabetical is unreliable for numeric suffixes.

## Required fix

Rewrite `read_final_velocity_max(vtk_dir: Path) -> Optional[float]` to:

1. **Identify latest timestep only**. Parse timestep from filename pattern `{anything}_{integer}.vtk`. If multiple files share the max timestep (e.g., one internal + one allPatches), prefer internal.

2. **Exclude boundary-patch files**. Skip any `*.vtk` whose path contains a directory component named `allPatches` OR whose filename starts with a boundary name (harder to enumerate — prefer the allPatches/ subdir exclusion).

3. **Read exactly one VTK file** (the latest internal). Apply current pyvista reading + max-|U| computation to that single file.

4. **Graceful degradation**: if pattern not parseable OR no internal VTK found OR pyvista unavailable → return None (same as current behavior).

## Reference: real VTK layouts

From repo artifacts:

```
reports/phase5_fields/lid_driven_cavity/20260421T131010Z/VTK/
├── allPatches/
│   └── allPatches_1000.vtk
└── case_1000.vtk                      ← INTERNAL FIELD (use this)
```

```
reports/phase5_fields/circular_cylinder_wake/20260421T150630Z/VTK/
├── allPatches/
│   ├── allPatches_100.vtk
│   ├── allPatches_200.vtk
│   ...
│   └── allPatches_500.vtk
├── ldc_xxx_100.vtk
├── ldc_xxx_200.vtk
...
└── ldc_xxx_500.vtk                    ← LATEST INTERNAL (use this)
```

Note: the `ldc_` prefix in cylinder_wake files is historical naming drift; don't hard-code prefixes. Parse timestep numerically from suffix.

## Recommended algorithm

```python
def read_final_velocity_max(vtk_dir: Path) -> Optional[float]:
    if not vtk_dir.is_dir():
        return None
    try:
        import numpy as np
        import pyvista as pv
    except ImportError:
        return None

    # Collect internal-field VTK files (exclude allPatches subdirectory).
    internal = []
    for p in vtk_dir.rglob("*.vtk"):
        # Skip anything inside an allPatches/ directory.
        if "allPatches" in p.parts:
            continue
        # Parse trailing _<int>.vtk
        m = re.search(r"_(\d+)\.vtk$", p.name)
        if not m:
            continue
        timestep = int(m.group(1))
        internal.append((timestep, p))

    if not internal:
        return None

    # Pick highest timestep. If tie, first encountered wins (deterministic
    # via sort on (timestep, str(path))).
    internal.sort(key=lambda tp: (tp[0], str(tp[1])))
    _, latest_path = internal[-1]

    try:
        mesh = pv.read(str(latest_path))
    except Exception:
        return None

    # Existing U extraction logic (preserve):
    point_fields = set(mesh.point_data.keys()) if hasattr(mesh, "point_data") else set()
    cell_fields = set(mesh.cell_data.keys()) if hasattr(mesh, "cell_data") else set()
    U_array = None
    for field_name in ("U", "velocity", "u"):
        if field_name in point_fields:
            U_array = np.asarray(mesh.point_data[field_name])
            break
        if field_name in cell_fields:
            U_array = np.asarray(mesh.cell_data[field_name])
            break
    if U_array is None or U_array.size == 0:
        return None
    if U_array.ndim == 2 and U_array.shape[1] >= 3:
        mags = np.linalg.norm(U_array[:, :3], axis=1)
    else:
        mags = np.abs(U_array.ravel())
    if mags.size == 0:
        return None
    return float(np.nanmax(mags))
```

## Acceptance Checks

CHK-1: On a VTK dir with `case_100.vtk` (internal, max |U|=1.0) + `allPatches/allPatches_100.vtk` (boundary, max |U|=1.0), returns 1.0 from the internal file.

CHK-2: On a VTK dir with `case_100.vtk` (max |U|=999) + `case_500.vtk` (max |U|=1.0), returns 1.0 (latest timestep).

CHK-3: On a VTK dir with only `allPatches/allPatches_500.vtk` (no internal), returns None.

CHK-4: On a VTK dir with a mix `case_10.vtk`, `case_100.vtk`, `case_2.vtk`, picks `case_100.vtk` (largest numeric timestep, NOT alphabetically sorted where `case_2.vtk` > `case_100.vtk`).

CHK-5: On a VTK dir with filename `case.vtk` (no timestep suffix), skips that file (no match against `_<int>.vtk`); if no other files match returns None.

CHK-6: Existing callers of `read_final_velocity_max(vtk_dir)` (in `_check_g3_velocity_overflow`) work unchanged — signature and return type preserved.

## Reject Conditions

REJ-1: Any edit outside `src/comparator_gates.py`.
REJ-2: Changing the function signature `read_final_velocity_max(vtk_dir: Path) -> Optional[float]`.
REJ-3: Introducing new imports beyond `re` + existing `numpy`/`pyvista` dynamic imports.
REJ-4: Breaking backward compat for `_check_g3_velocity_overflow` caller.

## Output format

```
# Codex Diff Report — DEC-V61-045 Wave 1 B

## Files modified
- src/comparator_gates.py [+N/-M]

## Changes summary
- Rewrite read_final_velocity_max to use latest internal VTK only

## Acceptance checks self-verified
- CHK-1..CHK-6: PASS/FAIL + evidence

## Tokens used
```

---

[/CLAUDE → CODEX TOOL INVOCATION]

codex
我会先做一个轻量上下文核对：读取这次决策说明、B3 finding，以及 `src/comparator_gates.py` 现状，确认只在允许文件内修改。
exec
/bin/zsh -lc "sed -n '1,220p' .planning/decisions/2026-04-22_phase8_dec045_attestor_gates_blocker_fixes_PROPOSAL.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
---
decision_id: DEC-V61-045
status: PROPOSAL (awaiting Kogami scope approval before execution)
timestamp: 2026-04-22T19:20 local
scope: |
  Phase 8 Sprint 1 follow-up — fix 8 Codex blockers across DEC-036b
  (CHANGES_REQUIRED, 3 blockers + 2 nits) and DEC-038 (BLOCK, 5 blockers
  + 3 nits). v6.2 independent-verification protocol surfaced substantial
  gaps between DEC-stated contracts and landed implementation. Combined
  fix DEC because both sides share orchestration touchpoints
  (_audit_fixture_doc + _derive_contract_status + TaskRunner flow).

  This DEC is a PROPOSAL — awaiting Kogami approval of scope + approach
  before any code change. Once approved, this becomes DEC-V61-045 with
  autonomous_governance path and pre-merge Codex review (self-pass well
  below 0.70 given complexity).

autonomous_governance: pending_kogami_approval
claude_signoff: proposal_only
codex_tool_invoked: false (no diff yet; pre-merge required before landing)
codex_rounds: 0
codex_verdict: not_yet_requested
external_gate_self_estimated_pass_rate: 0.50
  (Complex multi-module change touching orchestration + verdict engine +

exec
/bin/zsh -lc "sed -n '1,220p' reports/codex_tool_reports/20260422_dec045_wave1_A_convergence_attestor_result.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
2026-04-22T11:24:05.559301Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-research-deerflow/SKILL.md: missing YAML frontmatter delimited by ---
2026-04-22T11:24:05.559325Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-report-pretext/SKILL.md: missing YAML frontmatter delimited by ---
OpenAI Codex v0.118.0 (research preview)
--------
workdir: /Users/Zhuanz/Desktop/cfd-harness-unified
model: gpt-5.4
provider: openai
approval: never
sandbox: workspace-write [workdir, /tmp, $TMPDIR, /Users/Zhuanz/.codex/memories]
reasoning effort: xhigh
reasoning summaries: none
session id: 019db4ee-e164-79a2-adf4-3daf953e8fbd
--------
user
# [CLAUDE → CODEX TOOL INVOCATION]

    from: claude-code-opus47 (Main Driver v6.2)
    to: codex-gpt54-xhigh (Joint Dev Peer · §A Diff Generator)
    task: "DEC-V61-045 Wave 1 Invocation A — convergence_attestor.py fixes"
    contract: Notion DEC-V61-045 PROPOSAL
    spec: .planning/decisions/2026-04-22_phase8_dec045_attestor_gates_blocker_fixes_PROPOSAL.md
    upstream_findings:
      - reports/codex_tool_reports/20260422_dec038_codex_review.md (BLOCK, 5 blockers)
    scope_tracks:
      - Track 1: Land YAML loader (CA-004 remediation)
      - Track 4: A1 consumes exit_code (CA-003 remediation)
      - CA-005 partial: A3 per-field residual targets
      - CA-006 nit: A6 "stuck" uses <= 1.0 not < 1.0
      - CA-007 nit: A4 gap-block consecutiveness fix

    allowed_files:
      - src/convergence_attestor.py           (primary edit surface)

    read_only_context:
      - knowledge/attestor_thresholds.yaml    (YAML schema Claude pre-wrote; loader must parse this)
      - src/comparator_gates.py               (parse_solver_log consumer; don't modify)
      - src/foam_agent_adapter.py             (ExecutionResult shape reference; don't modify)
      - reports/codex_tool_reports/20260422_dec038_codex_review.md  (findings source)
      - scripts/phase5_audit_run.py           (caller; backward-compat target but DON'T EDIT)
      - ui/backend/tests/test_convergence_attestor.py (existing test shape; DON'T EDIT — separate invocation)

    forbidden_files:
      - any file not in allowed_files list (read-only context is OK to read, NOT edit)
      - especially: knowledge/gold_standards/** (hard-floor 1)
      - especially: tests/** and ui/backend/tests/** (separate Codex invocation)
      - especially: scripts/phase5_audit_run.py (Wave 2/3 scope)

    autonomy: TOOL-SCOPE (within src/convergence_attestor.py, full architectural freedom)

---

## Detailed work spec

### 1. Thresholds dataclass + loader (Track 1)

Add a dataclass `Thresholds` matching the YAML schema. Add a loader function that reads `knowledge/attestor_thresholds.yaml`, applies per-case overrides, and returns a resolved `Thresholds` instance. Loader is idempotent and cacheable (module-level cache acceptable; invalidation on case_id change).

```python
@dataclass(frozen=True)
class Thresholds:
    continuity_floor: float
    residual_floor: float
    residual_floor_per_field: dict[str, float]  # field → target; defaultdict-like
    iteration_cap_detector_count: int
    bounding_recurrence_frac_threshold: float
    bounding_recurrence_window: int
    no_progress_decade_frac: float
    no_progress_window: int
    promote_to_fail: frozenset[str] = field(default_factory=frozenset)
    case_id: Optional[str] = None   # for logging/debug only

def load_thresholds(
    case_id: Optional[str] = None,
    yaml_path: Optional[Path] = None,
) -> Thresholds:
    """Load YAML and resolve per-case overrides. Returns defaults-only
    instance if case_id is None or case not present in YAML."""
```

Design constraints:
- Use `yaml.safe_load` (import `yaml`; it's available — project dep).
- Default YAML path: `Path(__file__).resolve().parent.parent / "knowledge" / "attestor_thresholds.yaml"` (repo-relative).
- If YAML missing → return hardcoded-constant defaults + log WARN. Do NOT raise.
- If YAML schema_version != 1 → log WARN but continue with best-effort parse.
- Unknown top-level keys in YAML → log WARN, continue.
- Unknown per-field keys in residual_floor_per_field → accept (forward-compat).
- `promote_to_fail` is a list in YAML; convert to frozenset.
- Merge logic for per_case override:
  - Start with defaults
  - For each key in per_case[case_id], override defaults
  - For residual_floor_per_field: per-case dict REPLACES defaults (not merge) — document this choice explicitly in code comment. If you think merge is safer, implement merge and justify in your response.
  - Actually: recommended implementation is MERGE (per_case values override, unmentioned defaults preserved). Please use merge semantics.

### 2. `_check_a1_solver_crash` — consume exit code (Track 4)

Current signature: `_check_a1_solver_crash(log_path: Path) -> AttestorCheck`

New signature: `_check_a1_solver_crash(log_path: Path, execution_result: Any = None) -> AttestorCheck`

Semantics:
- If `execution_result is not None`:
  - Check `getattr(execution_result, "success", None)`. If `False` → FAIL with concern_type `SOLVER_CRASH_LOG` and evidence includes exit_code if available (`getattr(execution_result, "exit_code", None)`).
- Then ALSO check log for FATAL markers (independent signal).
- FAIL verdict if EITHER exit indicates failure OR log has FATAL marker.
- Regex widen: currently only `^Floating point exception`. Expand to match:
  - `FOAM FATAL IO ERROR`
  - `FOAM FATAL ERROR`
  - `^Floating point exception`
  - `Floating exception` (anywhere)
- Avoid matching the startup banner `sigFpe : Enabling floating point exception trapping` (current code handles this; preserve).

Use duck-typing (`getattr`) — do NOT `from src.foam_agent_adapter import ExecutionResult` to avoid circular import risk. `execution_result` param typed as `Any = None`.

### 3. `_check_a3_residual_floor` — per-field targets (CA-005 partial)

Current: one `A3_RESIDUAL_FLOOR` for all fields.

New: pull per-field target from `thresholds.residual_floor_per_field.get(field_name, thresholds.residual_floor)`.

Field names seen in real logs: Ux, Uy, Uz, p, p_rgh, k, epsilon, omega, h, nuTilda, T.

Updated summary/detail strings should include the per-field target when reporting offenders (not just one global threshold).

### 4. CA-006: A6 decade check boundary

Current: `if decade_range < A6_PROGRESS_DECADE_FRAC` → FAIL (stuck).

New: `if decade_range <= thresholds.no_progress_decade_frac` → FAIL. Also use `thresholds.no_progress_decade_frac` not module constant.

### 5. CA-007: A4 gap-block consecutiveness

Current behavior per Codex finding: blocks with no pressure solve are filtered out before consecutive-check. So `[cap, gap, cap, cap]` looks like `[cap, cap, cap]` = 3 consecutive → A4 FAIL.

New behavior: preserve gap blocks in the sequence; streak resets to 0 on a gap. `[cap, gap, cap, cap]` = max streak 2 → A4 PASS.

Implement: walk the full per-block cap-count sequence (including `0` for gaps), count consecutive caps, track max streak, FAIL if `max_streak >= thresholds.iteration_cap_detector_count`.

### 6. Thread thresholds through all checks

All `_check_a[2-6]_*` take `thresholds: Thresholds` param. `_check_a1_*` takes `execution_result`. All module-constant uses (A2_CONTINUITY_FLOOR, A3_RESIDUAL_FLOOR, A5_*, A6_*) replaced by `thresholds.<field>`.

KEEP module constants for backward compat as defaults in `load_thresholds` fallback path (when YAML missing). Rename if naming clashes, but they should still exist.

### 7. `attest()` main function signature update

```python
def attest(
    log_path: Optional[Path],
    execution_result: Any = None,
    case_id: Optional[str] = None,
    thresholds: Optional[Thresholds] = None,
) -> AttestationResult:
    """Run all 6 checks and aggregate verdict.

    Parameters
    ----------
    log_path : Path or None
        Solver log. None → ATTEST_NOT_APPLICABLE.
    execution_result : Any, optional
        Duck-typed object with .success and .exit_code attrs. Used by A1.
    case_id : str, optional
        Whitelist case ID for per-case YAML override lookup.
    thresholds : Thresholds, optional
        Pre-resolved thresholds. If None, calls load_thresholds(case_id).
    """
```

Backward compat: `attest(log_path)` still works (execution_result=None, case_id=None, thresholds defaults).

---

## Acceptance Checks (CHK-N)

CHK-1: Existing `scripts/phase5_audit_run.py:383` caller `attestation = attest(solver_log)` must still work unchanged (no required new args).

CHK-2: Existing `ui/backend/tests/test_convergence_attestor.py` tests that call `attest(log)` should still pass without test modifications. If the tests had hardcoded old threshold constants (e.g., `A2_CONTINUITY_FLOOR`), those constants must still be importable at module level (even if internally the value comes from YAML).

CHK-3: `load_thresholds()` without args returns `Thresholds` instance with YAML-defaults values (not missing keys, not None values).

CHK-4: `load_thresholds("impinging_jet")` returns Thresholds with `residual_floor_per_field["p_rgh"] == 5.0e-3` (per-case override applied).

CHK-5: `load_thresholds("nonexistent_case_xyz")` returns Thresholds with defaults (no raise, no per-case lookup error).

CHK-6: If `knowledge/attestor_thresholds.yaml` is renamed/moved, `load_thresholds()` returns hardcoded-constant defaults and logs WARN (graceful degradation).

CHK-7: `_check_a1_solver_crash(log_path, execution_result=mock(success=False, exit_code=139))` returns `verdict=FAIL` regardless of log content.

CHK-8: `_check_a1_solver_crash(log_path, execution_result=mock(success=True))` with log containing `Floating exception` returns `verdict=FAIL` (log signal alone).

CHK-9: `_check_a3_residual_floor` on a log with `p_rgh Initial residual = 6e-3` + thresholds from `impinging_jet` → PASS (6e-3 <= 5e-3? No wait, 6e-3 > 5e-3. Let me redo: threshold for p_rgh=5e-3 case-override; final p_rgh residual=6e-3 > 5e-3 → HAZARD). Verify the per-field path is taken. Synthetic test data is fine.

CHK-10: CA-006: `_check_a6_no_progress` on a log where max decade_range across fields is exactly 1.0 → FAIL (not PASS). Previously `< 1.0` would have been PASS at 1.0.

CHK-11: CA-007: `_check_a4_iteration_cap` on a block sequence `[cap, gap, cap, cap]` (where gap has 0 pressure solves) returns PASS. Max consecutive = 2, below threshold 3.

CHK-12: `_check_a4_iteration_cap` on `[cap, cap, cap]` consecutive → FAIL as before.

CHK-13: `attest(None)` returns `overall=ATTEST_NOT_APPLICABLE` (unchanged behavior).

CHK-14: `attest(log, execution_result=mock(success=False))` returns `overall=ATTEST_FAIL` with A1 in checks even if log is otherwise clean.

## Reject Conditions (REJ-N)

REJ-1: Any edit to files outside `allowed_files`. In particular: do NOT edit scripts/, tests/, or ui/backend/.
REJ-2: Removing module-level A2/A3/A5/A6 constants (existing code imports them).
REJ-3: Changing `_check_a*` function NAMES (existing tests may import them directly).
REJ-4: Breaking backward compat for `attest(log_path)` one-arg call.
REJ-5: Importing ExecutionResult from foam_agent_adapter (circular import risk).
REJ-6: Making loader raise on missing YAML (must gracefully fall back).

## Output format

After applying changes, emit a structured report:

```
# Codex Diff Report — DEC-V61-045 Wave 1 A

## Files modified
- path/to/file [+N/-M lines]


exec
/bin/zsh -lc "sed -n '1,260p' src/comparator_gates.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '1,260p' src/convergence_attestor.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
"""DEC-V61-036b: Hard comparator gates G3/G4/G5 — post-extraction physics gates.

Trigger FAIL on:
  * G3 VELOCITY_OVERFLOW  — |U|_max > K * U_ref (K=100 default). VTK-based,
    with log-based epsilon proxy fallback (epsilon ~ u^3/L).
  * G4 TURBULENCE_NEGATIVE — k/epsilon/omega min < 0 at last bounding line
    OR max > 1e+10 (sanity overflow).
  * G5 CONTINUITY_DIVERGED — last-iter sum_local > 1e-2 OR |cumulative| > 1.

Operates on artifacts already written by the audit pipeline:
  * `reports/phase5_fields/{case_id}/{ts}/log.simpleFoam` (or .pimpleFoam,
    .icoFoam, .buoyantSimpleFoam)
  * `reports/phase5_fields/{case_id}/{ts}/VTK/*.vtk` (latest time step)

See the accompanying DEC file for ground-truth evidence from the BFS run
(cumulative=-1434.64, k min=-6.41e+30) and expected gate outcomes.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


def _exceeds_threshold(value: Optional[float], threshold: float) -> bool:
    """True when value is NaN, ±inf, OR finite-and-above threshold.

    Codex DEC-036b round-1 feedback: plain `value > threshold` returns False
    for NaN, which would silently pass the worst blowup mode. NaN and +inf
    must fire the gate unconditionally.
    """
    if value is None:
        return False
    if math.isnan(value) or math.isinf(value):
        return True
    return value > threshold


def _abs_exceeds_threshold(value: Optional[float], threshold: float) -> bool:
    """|value| > threshold with NaN/Inf guard (same semantics as above)."""
    if value is None:
        return False
    if math.isnan(value) or math.isinf(value):
        return True
    return abs(value) > threshold

# ---------------------------------------------------------------------------
# Thresholds (tunable via per-case override in future; seeded from Codex
# round-1 physics audit on DEC-V61-036).
# ---------------------------------------------------------------------------

G3_VELOCITY_RATIO_MAX = 100.0     # |U|_max / U_ref
G3_EPSILON_PROXY_MAX = 1.0e10     # fallback when VTK unavailable
G4_TURBULENCE_MAX_OVERFLOW = 1.0e10  # any k/eps/omega max above this = overflow
G5_SUM_LOCAL_MAX = 1.0e-2         # incompressible steady floor
G5_CUMULATIVE_ABS_MAX = 1.0       # hard divergence floor


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class GateViolation:
    """A single post-extraction gate FAIL.

    The fixture writer forwards these to audit_concerns[] and the
    validation_report verdict engine hard-FAILs on any violation.
    """

    gate_id: str          # "G3" | "G4" | "G5"
    concern_type: str     # "VELOCITY_OVERFLOW" | "TURBULENCE_NEGATIVE" | "CONTINUITY_DIVERGED"
    summary: str
    detail: str
    evidence: dict = field(default_factory=dict)


@dataclass
class LogStats:
    """Parsed telemetry from an OpenFOAM solver log."""

    final_continuity_sum_local: Optional[float] = None
    final_continuity_cumulative: Optional[float] = None
    # Per-field (k/epsilon/omega) last-iter bounding stats.
    bounding_last: dict[str, dict[str, float]] = field(default_factory=dict)
    # Fatal errors (FOAM FATAL, floating exception).
    fatal_detected: bool = False
    fatal_lines: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Log parsing
# ---------------------------------------------------------------------------

# Codex DEC-036b round-1 feedback: token classes below must also accept
# `nan` / `inf` (case-insensitive). When OpenFOAM's floating-point output
# overflows past double range it prints `nan` or `-inf`, and if the regex
# rejected those tokens, the worst blowup mode would silently bypass the
# gates. Each token class is `[\deE+.\-]+|nan|[+\-]?inf` (case-folded).
_NUM_TOKEN = r"(?:[\deE+.\-]+|[nN][aA][nN]|[+\-]?[iI][nN][fF])"

_CONTINUITY_RE = re.compile(
    r"time step continuity errors\s*:\s*sum local\s*=\s*(" + _NUM_TOKEN + r")\s*,"
    r"\s*global\s*=\s*" + _NUM_TOKEN + r"\s*,"
    r"\s*cumulative\s*=\s*(" + _NUM_TOKEN + r")"
)

# Matches "bounding k, min: -1.23 max: 4.56 average: 0.1" — the comma+space
# between min and max varies across OF versions; regex tolerates both.
_BOUNDING_RE = re.compile(
    r"bounding\s+(k|epsilon|omega|nuTilda|nut|nuSgs)\s*,\s*"
    r"min\s*:\s*(" + _NUM_TOKEN + r")\s*,?\s*"
    r"max\s*:\s*(" + _NUM_TOKEN + r")"
)


def _parse_foam_number(tok: str) -> Optional[float]:
    """Parse a numeric token that may be `nan`, `inf`, `-inf`, or a
    regular finite float. Returns float (nan/inf allowed — callers compare
    against thresholds and NaN/Inf naturally fail any comparison, which
    is the intended "this value is catastrophically bad" signal)."""
    try:
        return float(tok)
    except (ValueError, TypeError):
        return None

# Tightened to avoid false-positive on the benign startup line
# `sigFpe : Enabling floating point exception trapping (FOAM_SIGFPE)` which
# announces FPE trapping capability, not an actual exception. The real
# fatal markers are FOAM FATAL (IO )?ERROR + stack-trace frames.
_FATAL_RE = re.compile(
    r"FOAM FATAL (IO )?ERROR|"
    r"#\d+\s+Foam::error::printStack|"
    r"^Floating point exception",
    re.MULTILINE,
)


def parse_solver_log(log_path: Path) -> LogStats:
    """Parse continuity + bounding lines + fatal markers from a solver log.

    Extracts the LAST matching occurrence of each pattern (the end-of-run
    state is what matters for gate decisions). For bounding, keeps
    per-field last-iter min/max.
    """
    stats = LogStats()
    if not log_path.is_file():
        return stats

    last_continuity: Optional[tuple[float, float]] = None
    last_bounding: dict[str, dict[str, float]] = {}
    fatal_lines: list[str] = []

    with log_path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = _CONTINUITY_RE.search(line)
            if m:
                sl = _parse_foam_number(m.group(1))
                cum = _parse_foam_number(m.group(2))
                if sl is not None and cum is not None:
                    last_continuity = (sl, cum)
                continue
            m = _BOUNDING_RE.search(line)
            if m:
                field_name = m.group(1)
                field_min = _parse_foam_number(m.group(2))
                field_max = _parse_foam_number(m.group(3))
                if field_min is not None and field_max is not None:
                    last_bounding[field_name] = {
                        "min": field_min,
                        "max": field_max,
                    }
                continue
            if _FATAL_RE.search(line):
                stats.fatal_detected = True
                if len(fatal_lines) < 5:
                    fatal_lines.append(line.strip()[:240])

    if last_continuity is not None:
        stats.final_continuity_sum_local = last_continuity[0]
        stats.final_continuity_cumulative = last_continuity[1]
    stats.bounding_last = last_bounding
    stats.fatal_lines = fatal_lines
    return stats


# ---------------------------------------------------------------------------
# VTK velocity magnitude
# ---------------------------------------------------------------------------

def read_final_velocity_max(vtk_dir: Path) -> Optional[float]:
    """Return the max |U| across all cells in the latest internal-field VTK.

    Uses pyvista when available. Returns None when VTK unavailable,
    unreadable, or pyvista is not installed — caller treats None as
    "skip G3 VTK branch, use log-epsilon proxy instead".
    """
    if not vtk_dir.is_dir():
        return None
    try:
        import numpy as np
        import pyvista as pv
    except ImportError:
        return None

    latest_internal: list[tuple[int, str, Path]] = []
    for vtk_path in vtk_dir.rglob("*.vtk"):
        if "allPatches" in vtk_path.parts:
            continue
        match = re.search(r"_(\d+)\.vtk$", vtk_path.name)
        if match is None:
            continue
        latest_internal.append((int(match.group(1)), str(vtk_path), vtk_path))

    if not latest_internal:
        return None

    latest_internal.sort(key=lambda item: (item[0], item[1]))
    vtk_path = latest_internal[-1][2]

    try:
        mesh = pv.read(str(vtk_path))
    except Exception:
        return None

    # Look for a vector field named U or velocity.
    point_fields = set(mesh.point_data.keys()) if hasattr(mesh, "point_data") else set()
    cell_fields = set(mesh.cell_data.keys()) if hasattr(mesh, "cell_data") else set()
    U_array = None
    for field_name in ("U", "velocity", "u"):
        if field_name in point_fields:
            U_array = np.asarray(mesh.point_data[field_name])
            break
        if field_name in cell_fields:
            U_array = np.asarray(mesh.cell_data[field_name])
            break
    if U_array is None or U_array.size == 0:
        return None
    # U is typically (N, 3); compute per-cell magnitude.
    if U_array.ndim == 2 and U_array.shape[1] >= 3:
        mags = np.linalg.norm(U_array[:, :3], axis=1)
    else:
        mags = np.abs(U_array.ravel())
    if mags.size == 0:
        return None
    return float(np.nanmax(mags))


# ---------------------------------------------------------------------------
# Individual gate checks
# ---------------------------------------------------------------------------

def _check_g3_velocity_overflow(
    log_stats: Optional[LogStats],
    vtk_dir: Optional[Path],
    U_ref: float,
) -> list[GateViolation]:

 succeeded in 0ms:
"""DEC-V61-038: Pre-extraction convergence attestor A1..A6.

Complements DEC-V61-036b (post-extraction gates G3/G4/G5). Where G3/G4/G5
say "the extracted measurement cannot be trusted because the final-state
fields are broken", A1..A6 say "the run itself never physically converged
even if the solver exited 0".

Composition with gates:
    solver exit 0
    → attestor.attest(log)    → ATTEST_PASS / HAZARD / FAIL
    → if ATTEST_FAIL: contract FAIL (before extraction)
    → else: comparator_gates.check_all_gates(log, vtk)
    → if any gate: contract FAIL
    → else: comparator verdict

Checks:
    A1 solver_exit_clean       — no FOAM FATAL / floating exception  → FAIL
    A2 continuity_floor        — final sum_local ≤ case floor        → HAZARD
    A3 residual_floor          — final initial residuals ≤ target    → HAZARD
    A4 solver_iteration_cap    — pressure loop hit cap repeatedly    → FAIL
    A5 bounding_recurrence     — turbulence bounding in last N iters → HAZARD
    A6 no_residual_progress    — residuals stuck at plateau          → HAZARD

A1/A4 are hard FAIL (solver crashes / caps never acceptable).
A2/A3/A5/A6 default HAZARD; per-case thresholds can promote to FAIL
via knowledge/attestor_thresholds.yaml.

The attestor returns ATTEST_FAIL if ANY check FAILs; ATTEST_HAZARD if
only HAZARD-tier checks fire; else ATTEST_PASS.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, Optional

import yaml

from src.comparator_gates import parse_solver_log

# ---------------------------------------------------------------------------
# Thresholds (kept as module constants for backward compatibility; YAML-backed
# Thresholds resolution overlays these defaults when the registry is present)
# ---------------------------------------------------------------------------

A2_CONTINUITY_FLOOR = 1.0e-4           # incompressible steady; G5 fires at 1e-2
A3_RESIDUAL_FLOOR = 1.0e-3             # initial residual of any field
# Codex DEC-038 round-1 BLOCKER 1: A4 regex must cover every pressure
# solver + every pressure field name seen in the real audit logs.
# - Solver types: GAMG, PCG, DICPCG, PBiCG, DILUPBiCGStab
# - Pressure field names: p (incompressible), p_rgh (buoyant), pd
# - Multi-corrector PIMPLE loops emit multiple pressure solves per Time=
#   block; A4 must track BLOCKS not LINES (BLOCKER 2) so consecutive-hit
#   semantics match the DEC's "3 consecutive time steps" intent.
A4_PRESSURE_FIELD_RE = re.compile(
    # Codex DEC-038 round-2 nit: PBiCGStab:... would not match PBiCG
    # alternative because the next char after the 5-letter prefix is 'S'
    # not ':'. List PBiCGStab before PBiCG so regex alternation picks the
    # longer literal first.
    r"(?:GAMG|DICPCG|PCG|PBiCGStab|PBiCG|DILUPBiCGStab|smoothSolver)\s*:\s*"
    r"Solving for\s+(p(?:_rgh|d)?)\s*,"
    r".+?No Iterations\s+(\d+)"
)
A4_ITERATION_CAP_VALUES = (1000, 999, 998)  # solver-reported caps
A4_CONSECUTIVE = 3                     # how many consecutive time-step blocks = FAIL

A5_BOUNDING_WINDOW = 50                # last N iterations to inspect
A5_BOUNDING_RECURRENCE_FRAC = 0.30     # ≥ 30% of window bounded = HAZARD

A6_PROGRESS_WINDOW = 50
A6_PROGRESS_DECADE_FRAC = 1.0          # need > 1 decade decay over window

LOGGER = logging.getLogger(__name__)

_DEFAULT_THRESHOLDS_PATH = (
    Path(__file__).resolve().parent.parent / "knowledge" / "attestor_thresholds.yaml"
)
_KNOWN_A3_FIELDS = (
    "Ux",
    "Uy",
    "Uz",
    "p",
    "p_rgh",
    "k",
    "epsilon",
    "omega",
    "h",
    "nuTilda",
    "T",
)
_THRESHOLD_TOP_LEVEL_KEYS = frozenset({"schema_version", "defaults", "per_case"})


AttestVerdict = Literal[
    "ATTEST_PASS",
    "ATTEST_HAZARD",
    "ATTEST_FAIL",
    "ATTEST_NOT_APPLICABLE",  # no log available (reference/visual_only tiers)
]
CheckVerdict = Literal["PASS", "HAZARD", "FAIL"]


@dataclass(frozen=True)
class Thresholds:
    continuity_floor: float
    residual_floor: float
    residual_floor_per_field: dict[str, float]
    iteration_cap_detector_count: int
    bounding_recurrence_frac_threshold: float
    bounding_recurrence_window: int
    no_progress_decade_frac: float
    no_progress_window: int
    promote_to_fail: frozenset[str] = field(default_factory=frozenset)
    case_id: Optional[str] = None


@dataclass
class AttestorCheck:
    """Single check outcome (A1..A6)."""

    check_id: str              # "A1" .. "A6"
    concern_type: str          # "SOLVER_CRASH_LOG" / "CONTINUITY_NOT_CONVERGED" / ...
    verdict: CheckVerdict
    summary: str
    detail: str
    evidence: dict = field(default_factory=dict)


@dataclass
class AttestationResult:
    """Aggregate attestation: overall verdict + per-check breakdown.

    `concerns` is the subset of checks whose verdict is HAZARD or FAIL
    (PASS checks are not surfaced in the fixture to avoid clutter).
    """

    overall: AttestVerdict
    checks: list[AttestorCheck] = field(default_factory=list)

    @property
    def concerns(self) -> list[AttestorCheck]:
        return [c for c in self.checks if c.verdict != "PASS"]


_DEFAULT_THRESHOLDS = Thresholds(
    continuity_floor=A2_CONTINUITY_FLOOR,
    residual_floor=A3_RESIDUAL_FLOOR,
    residual_floor_per_field={field_name: A3_RESIDUAL_FLOOR for field_name in _KNOWN_A3_FIELDS},
    iteration_cap_detector_count=A4_CONSECUTIVE,
    bounding_recurrence_frac_threshold=A5_BOUNDING_RECURRENCE_FRAC,
    bounding_recurrence_window=A5_BOUNDING_WINDOW,
    no_progress_decade_frac=A6_PROGRESS_DECADE_FRAC,
    no_progress_window=A6_PROGRESS_WINDOW,
)


def _thresholds_to_mutable_dict(base: Thresholds) -> dict[str, Any]:
    return {
        "continuity_floor": base.continuity_floor,
        "residual_floor": base.residual_floor,
        "residual_floor_per_field": dict(base.residual_floor_per_field),
        "iteration_cap_detector_count": base.iteration_cap_detector_count,
        "bounding_recurrence_frac_threshold": base.bounding_recurrence_frac_threshold,
        "bounding_recurrence_window": base.bounding_recurrence_window,
        "no_progress_decade_frac": base.no_progress_decade_frac,
        "no_progress_window": base.no_progress_window,
        "promote_to_fail": frozenset(base.promote_to_fail),
    }


def _build_thresholds(payload: dict[str, Any], case_id: Optional[str]) -> Thresholds:
    return Thresholds(
        continuity_floor=float(payload["continuity_floor"]),
        residual_floor=float(payload["residual_floor"]),
        residual_floor_per_field=dict(payload["residual_floor_per_field"]),
        iteration_cap_detector_count=int(payload["iteration_cap_detector_count"]),
        bounding_recurrence_frac_threshold=float(
            payload["bounding_recurrence_frac_threshold"]
        ),
        bounding_recurrence_window=int(payload["bounding_recurrence_window"]),
        no_progress_decade_frac=float(payload["no_progress_decade_frac"]),
        no_progress_window=int(payload["no_progress_window"]),
        promote_to_fail=frozenset(payload["promote_to_fail"]),
        case_id=case_id,
    )


def _fallback_thresholds(case_id: Optional[str]) -> Thresholds:
    return _build_thresholds(_thresholds_to_mutable_dict(_DEFAULT_THRESHOLDS), case_id)


def _coerce_float(
    value: Any,
    *,
    fallback: float,
    path: Path,
    key_path: str,
) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        LOGGER.warning(
            "attestor thresholds: invalid numeric value for %s in %s: %r; using %.6g",
            key_path,
            path,
            value,
            fallback,
        )
        return fallback


def _coerce_int(
    value: Any,
    *,
    fallback: int,
    path: Path,
    key_path: str,
) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        LOGGER.warning(
            "attestor thresholds: invalid integer value for %s in %s: %r; using %d",
            key_path,
            path,
            value,
            fallback,
        )
        return fallback


def _apply_threshold_overrides(
    resolved: dict[str, Any],
    overrides: Any,
    *,
    path: Path,
    label: str,
) -> None:
    if overrides is None:
        return
    if not isinstance(overrides, dict):
        LOGGER.warning(
            "attestor thresholds: %s in %s is not a mapping; ignoring override",
            label,
            path,
        )
        return

    if "continuity_floor" in overrides:
        resolved["continuity_floor"] = _coerce_float(
            overrides["continuity_floor"],
            fallback=float(resolved["continuity_floor"]),
            path=path,
            key_path=f"{label}.continuity_floor",
        )
    if "residual_floor" in overrides:

codex
已经确认 Wave 1 A/B 实现都已落在源码里；这次只需要把测试覆盖补齐到 DEC 要求。下一步我会读出 A1/A3/A4/A6 与 `read_final_velocity_max()` 的当前行为，避免写出和现实现状不匹配的断言。
exec
/bin/zsh -lc "rg -n \"def read_final_velocity_max|def check_all_gates\\(\" src/comparator_gates.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '260,420p' src/comparator_gates.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '260,520p' src/convergence_attestor.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
) -> list[GateViolation]:
    """G3: |U|_max > K * U_ref OR epsilon max > G3_EPSILON_PROXY_MAX."""
    violations: list[GateViolation] = []
    threshold = G3_VELOCITY_RATIO_MAX * max(U_ref, 1e-6)

    u_max: Optional[float] = None
    if vtk_dir is not None:
        u_max = read_final_velocity_max(vtk_dir)

    if u_max is not None and _exceeds_threshold(u_max, threshold):
        violations.append(
            GateViolation(
                gate_id="G3",
                concern_type="VELOCITY_OVERFLOW",
                summary=(
                    f"|U|_max={u_max:.3g} exceeds {G3_VELOCITY_RATIO_MAX:.0f}·U_ref "
                    f"({threshold:.3g})"
                )[:240],
                detail=(
                    f"DEC-V61-036b G3: reading latest-time VTK cell velocity "
                    f"found |U|_max={u_max:.6g}, which is above the "
                    f"{G3_VELOCITY_RATIO_MAX:.0f}·U_ref sanity ceiling "
                    f"({threshold:.6g}, U_ref={U_ref}). This indicates "
                    "solver divergence or runaway acceleration — the measurement "
                    "cannot be trusted regardless of whether it lies within "
                    "the gold tolerance band."
                )[:2000],
                evidence={"u_max": u_max, "U_ref": U_ref, "threshold": threshold},
            )
        )
        return violations

    # Log-epsilon proxy fallback when VTK unavailable.
    if log_stats is not None:
        eps_bound = log_stats.bounding_last.get("epsilon")
        if eps_bound is not None:
            eps_max = eps_bound.get("max")
            if _exceeds_threshold(eps_max, G3_EPSILON_PROXY_MAX):
                violations.append(
                    GateViolation(
                        gate_id="G3",
                        concern_type="VELOCITY_OVERFLOW",
                        summary=(
                            f"epsilon max={eps_max:.3g} implies "
                            f"|U|~{eps_max**(1/3):.2g} (VTK-proxy)"
                        )[:240],
                        detail=(
                            f"DEC-V61-036b G3 (VTK-unavailable fallback): "
                            f"log shows final epsilon max={eps_max:.6g}, "
                            f"above proxy threshold {G3_EPSILON_PROXY_MAX:.0g}. "
                            "Since ε~u³/L, this implies |U| is catastrophically "
                            "large. Velocity overflow flagged from log."
                        )[:2000],
                        evidence={
                            "epsilon_max": eps_max,
                            "proxy_threshold": G3_EPSILON_PROXY_MAX,
                            "inferred_u": eps_max ** (1.0 / 3.0),
                        },
                    )
                )
    return violations


def _check_g4_turbulence_negativity(
    log_stats: Optional[LogStats],
) -> list[GateViolation]:
    """G4: k/epsilon/omega min < 0 at last bounding line OR max > overflow."""
    violations: list[GateViolation] = []
    if log_stats is None:
        return violations

    for field_name, bounds in log_stats.bounding_last.items():
        f_min = bounds.get("min")
        f_max = bounds.get("max")
        # NaN → treat as "catastrophically wrong" → fire gate.
        if f_min is not None and (
            math.isnan(f_min) or math.isinf(f_min) or f_min < 0.0
        ):
            violations.append(
                GateViolation(
                    gate_id="G4",
                    concern_type="TURBULENCE_NEGATIVE",
                    summary=(
                        f"{field_name} min={f_min:.3g} is negative at last iter"
                    )[:240],
                    detail=(
                        f"DEC-V61-036b G4: final `bounding {field_name}` "
                        f"line shows min={f_min:.6g} (< 0), max={f_max}. "
                        "Turbulence fields cannot be physically negative; "
                        "this indicates solver inconsistency even if "
                        "OpenFOAM's internal bounding clipped the value "
                        "to a small positive before the next step."
                    )[:2000],
                    evidence={
                        "field": field_name,
                        "min": f_min,
                        "max": f_max,
                    },
                )
            )
            continue
        if _exceeds_threshold(f_max, G4_TURBULENCE_MAX_OVERFLOW):
            violations.append(
                GateViolation(
                    gate_id="G4",
                    concern_type="TURBULENCE_NEGATIVE",
                    summary=(
                        f"{field_name} max={f_max:.3g} overflow "
                        f"(> {G4_TURBULENCE_MAX_OVERFLOW:.0g})"
                    )[:240],
                    detail=(
                        f"DEC-V61-036b G4 (overflow branch): final `bounding "
                        f"{field_name}` shows max={f_max:.6g}, above "
                        f"{G4_TURBULENCE_MAX_OVERFLOW:.0g}. For realistic "
                        "industrial RANS cases this magnitude is non-physical; "
                        "likely a divergence signature bounded from below."
                    )[:2000],
                    evidence={
                        "field": field_name,
                        "min": f_min,
                        "max": f_max,
                        "threshold": G4_TURBULENCE_MAX_OVERFLOW,
                    },
                )
            )
    return violations


def _check_g5_continuity_divergence(
    log_stats: Optional[LogStats],
) -> list[GateViolation]:
    """G5: last-iter sum_local > 1e-2 OR |cumulative| > 1.0."""
    violations: list[GateViolation] = []
    if log_stats is None:
        return violations

    sum_local = log_stats.final_continuity_sum_local
    cumulative = log_stats.final_continuity_cumulative

    if _exceeds_threshold(sum_local, G5_SUM_LOCAL_MAX):
        violations.append(
            GateViolation(
                gate_id="G5",
                concern_type="CONTINUITY_DIVERGED",
                summary=(
                    f"continuity sum_local={sum_local:.3g} > "
                    f"{G5_SUM_LOCAL_MAX:.0e}"
                )[:240],
                detail=(
                    f"DEC-V61-036b G5: final-iteration continuity error "
                    f"sum_local={sum_local:.6g} exceeds the incompressible "
                    f"steady floor {G5_SUM_LOCAL_MAX:.0e}. SIMPLE/PISO "
                    "pressure-velocity coupling has not converged; any "
                    "extracted scalar is unreliable."
                )[:2000],
                evidence={
                    "sum_local": sum_local,
                    "cumulative": cumulative,
                    "threshold": G5_SUM_LOCAL_MAX,
                },
            )

 succeeded in 0ms:
194:def read_final_velocity_max(vtk_dir: Path) -> Optional[float]:
453:def check_all_gates(

 succeeded in 0ms:
    if "residual_floor" in overrides:
        resolved["residual_floor"] = _coerce_float(
            overrides["residual_floor"],
            fallback=float(resolved["residual_floor"]),
            path=path,
            key_path=f"{label}.residual_floor",
        )
    if "residual_floor_per_field" in overrides:
        field_overrides = overrides["residual_floor_per_field"]
        if isinstance(field_overrides, dict):
            merged = dict(resolved["residual_floor_per_field"])
            # Merge semantics are intentional: case-specific overrides should
            # only replace the mentioned fields and preserve YAML defaults for
            # everything else.
            for field_name, raw_value in field_overrides.items():
                merged[str(field_name)] = _coerce_float(
                    raw_value,
                    fallback=float(merged.get(str(field_name), resolved["residual_floor"])),
                    path=path,
                    key_path=f"{label}.residual_floor_per_field.{field_name}",
                )
            resolved["residual_floor_per_field"] = merged
        else:
            LOGGER.warning(
                "attestor thresholds: %s.residual_floor_per_field in %s is not a mapping; ignoring override",
                label,
                path,
            )
    if "iteration_cap_detector_count" in overrides:
        resolved["iteration_cap_detector_count"] = _coerce_int(
            overrides["iteration_cap_detector_count"],
            fallback=int(resolved["iteration_cap_detector_count"]),
            path=path,
            key_path=f"{label}.iteration_cap_detector_count",
        )
    if "bounding_recurrence_frac_threshold" in overrides:
        resolved["bounding_recurrence_frac_threshold"] = _coerce_float(
            overrides["bounding_recurrence_frac_threshold"],
            fallback=float(resolved["bounding_recurrence_frac_threshold"]),
            path=path,
            key_path=f"{label}.bounding_recurrence_frac_threshold",
        )
    if "bounding_recurrence_window" in overrides:
        resolved["bounding_recurrence_window"] = _coerce_int(
            overrides["bounding_recurrence_window"],
            fallback=int(resolved["bounding_recurrence_window"]),
            path=path,
            key_path=f"{label}.bounding_recurrence_window",
        )
    if "no_progress_decade_frac" in overrides:
        resolved["no_progress_decade_frac"] = _coerce_float(
            overrides["no_progress_decade_frac"],
            fallback=float(resolved["no_progress_decade_frac"]),
            path=path,
            key_path=f"{label}.no_progress_decade_frac",
        )
    if "no_progress_window" in overrides:
        resolved["no_progress_window"] = _coerce_int(
            overrides["no_progress_window"],
            fallback=int(resolved["no_progress_window"]),
            path=path,
            key_path=f"{label}.no_progress_window",
        )
    if "promote_to_fail" in overrides:
        raw_promote = overrides["promote_to_fail"]
        if isinstance(raw_promote, (list, tuple, set, frozenset)):
            resolved["promote_to_fail"] = frozenset(str(item) for item in raw_promote)
        else:
            LOGGER.warning(
                "attestor thresholds: %s.promote_to_fail in %s is not a list-like value; ignoring override",
                label,
                path,
            )


@lru_cache(maxsize=32)
def _load_thresholds_cached(
    case_id: Optional[str],
    yaml_path_str: Optional[str],
) -> Thresholds:
    yaml_path = Path(yaml_path_str) if yaml_path_str is not None else _DEFAULT_THRESHOLDS_PATH
    if not yaml_path.is_file():
        LOGGER.warning(
            "attestor thresholds: YAML not found at %s; using hardcoded defaults",
            yaml_path,
        )
        return _fallback_thresholds(case_id)

    try:
        raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    except OSError as exc:
        LOGGER.warning(
            "attestor thresholds: failed to read %s (%s); using hardcoded defaults",
            yaml_path,
            exc,
        )
        return _fallback_thresholds(case_id)
    except yaml.YAMLError as exc:
        LOGGER.warning(
            "attestor thresholds: failed to parse %s (%s); using hardcoded defaults",
            yaml_path,
            exc,
        )
        return _fallback_thresholds(case_id)

    if not isinstance(raw, dict):
        LOGGER.warning(
            "attestor thresholds: root of %s is not a mapping; using hardcoded defaults",
            yaml_path,
        )
        return _fallback_thresholds(case_id)

    unknown_top_level = sorted(set(raw) - _THRESHOLD_TOP_LEVEL_KEYS)
    if unknown_top_level:
        LOGGER.warning(
            "attestor thresholds: unknown top-level keys in %s: %s",
            yaml_path,
            ", ".join(unknown_top_level),
        )

    if raw.get("schema_version") != 1:
        LOGGER.warning(
            "attestor thresholds: expected schema_version=1 in %s, got %r; continuing best-effort",
            yaml_path,
            raw.get("schema_version"),
        )

    resolved = _thresholds_to_mutable_dict(_DEFAULT_THRESHOLDS)
    _apply_threshold_overrides(
        resolved,
        raw.get("defaults"),
        path=yaml_path,
        label="defaults",
    )

    if case_id:
        per_case = raw.get("per_case")
        if isinstance(per_case, dict):
            _apply_threshold_overrides(
                resolved,
                per_case.get(case_id),
                path=yaml_path,
                label=f"per_case.{case_id}",
            )
        elif per_case is not None:
            LOGGER.warning(
                "attestor thresholds: per_case in %s is not a mapping; ignoring case overrides",
                yaml_path,
            )

    return _build_thresholds(resolved, case_id)


def load_thresholds(
    case_id: Optional[str] = None,
    yaml_path: Optional[Path] = None,
) -> Thresholds:
    """Load YAML-backed convergence thresholds with graceful fallback."""
    normalized_path = (
        str(Path(yaml_path).expanduser().resolve()) if yaml_path is not None else None
    )
    return _load_thresholds_cached(case_id, normalized_path)


# ---------------------------------------------------------------------------
# Per-check regexes (reuse parse_solver_log output where possible)
# ---------------------------------------------------------------------------

_INITIAL_RESIDUAL_RE = re.compile(
    r"Solving for\s+(\w+),\s*Initial residual\s*=\s*([\deE+.\-]+),"
    r"\s*Final residual\s*=\s*([\deE+.\-]+),\s*No Iterations\s+(\d+)"
)

_BOUNDING_LINE_RE = re.compile(r"^\s*bounding\s+(k|epsilon|omega|nuTilda|nut)\b")
# OpenFOAM writes `Time = 123` on its own line AND as `Time = 123s` with
# trailing `s`. Accept either form; trailing whitespace tolerated.
_TIME_STEP_RE = re.compile(r"^Time\s*=\s*[\deE+.\-]+s?\s*$")
_A1_FATAL_MARKER_RE = re.compile(
    r"FOAM FATAL IO ERROR|FOAM FATAL ERROR|^Floating point exception\b|Floating exception\b"
)


def _parse_residual_timeline(log_path: Path) -> dict[str, list[float]]:
    """Extract per-field Initial residual history across all iterations.

    Returns {"Ux": [...], "Uy": [...], "p": [...], "k": [...], "epsilon": [...]}.
    Order preserves the log's iteration order. Used by A3 + A6.
    """
    timeline: dict[str, list[float]] = {}
    with log_path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = _INITIAL_RESIDUAL_RE.search(line)
            if not m:
                continue
            field_name = m.group(1)
            try:
                r0 = float(m.group(2))
            except ValueError:
                continue
            timeline.setdefault(field_name, []).append(r0)
    return timeline


def _parse_iteration_caps_per_block(log_path: Path) -> list[int]:
    """Return per-`Time = ...` block the MAX pressure-solver iteration count
    seen inside that block.

    Codex DEC-038 round-1 BLOCKER 2: A4 must count consecutive TIME STEPS
    (outer iterations), not consecutive solve lines — PIMPLE multi-corrector
    loops emit ≥2 pressure solves per block and the prior line-based count
    would false-fire after 1.5 blocks. Returns one entry per block; a
    block's count is the worst (max) pressure iteration count seen in it.
    Blocks with no pressure solve get 0 so A4 can explicitly reset the
    consecutiveness streak on gaps.
    """
    per_block_max: list[int] = []
    current_max = 0
    seen_any = False
    with log_path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if _TIME_STEP_RE.match(line):
                if seen_any:
                    per_block_max.append(current_max)
                current_max = 0
                seen_any = True
                continue
            m = A4_PRESSURE_FIELD_RE.search(line)
            if m:
                try:
                    count = int(m.group(2))
                except ValueError:
                    continue
                if count > current_max:
                    current_max = count
        if seen_any:
            per_block_max.append(current_max)
    return per_block_max


def _parse_bounding_lines_per_step(log_path: Path) -> list[set[str]]:
    """Return list of sets, one per `Time =` block, containing fields that
    bounded in that block. Used by A5.
    """
    blocks: list[set[str]] = [set()]
    with log_path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if _TIME_STEP_RE.match(line):
                blocks.append(set())
                continue
            m = _BOUNDING_LINE_RE.match(line)
            if m:
                blocks[-1].add(m.group(1))
    # Drop leading empty block before first `Time =`.
    if blocks and not blocks[0]:
        blocks.pop(0)
    return blocks


def _scan_a1_fatal_lines(log_path: Path) -> list[str]:
    if not log_path.is_file():
        return []

exec
/bin/zsh -lc "rg -n \"def load_thresholds|def _check_a1_solver_crash|def _check_a3_residual_floor|def _check_a4_iteration_cap|def _check_a6_no_progress|def attest\\(\" src/convergence_attestor.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
413:def load_thresholds(
542:def _check_a1_solver_crash(log_path: Path, execution_result: Any = None) -> AttestorCheck:
637:def _check_a3_residual_floor(log_path: Path, thresholds: Thresholds) -> AttestorCheck:
691:def _check_a4_iteration_cap(log_path: Path, thresholds: Thresholds) -> AttestorCheck:
804:def _check_a6_no_progress(log_path: Path, thresholds: Thresholds) -> AttestorCheck:
883:def attest(

exec
/bin/zsh -lc "sed -n '520,980p' src/convergence_attestor.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
        return []

    fatal_lines: list[str] = []
    with log_path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            normalized = line.strip()
            if not normalized:
                continue
            lower = normalized.lower()
            if "floating point exception trapping" in lower:
                continue
            if _A1_FATAL_MARKER_RE.search(normalized):
                fatal_lines.append(normalized[:240])
                if len(fatal_lines) >= 5:
                    break
    return fatal_lines


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def _check_a1_solver_crash(log_path: Path, execution_result: Any = None) -> AttestorCheck:
    stats = parse_solver_log(log_path)
    fatal_lines: list[str] = []
    for line in stats.fatal_lines + _scan_a1_fatal_lines(log_path):
        if line and line not in fatal_lines:
            fatal_lines.append(line)
    exec_failed = getattr(execution_result, "success", None) is False
    exit_code = getattr(execution_result, "exit_code", None) if execution_result is not None else None

    if exec_failed or fatal_lines or stats.fatal_detected:
        evidence: dict[str, Any] = {"fatal_lines": fatal_lines[:3]}
        summary_parts: list[str] = []
        detail_parts: list[str] = []
        if exec_failed:
            evidence["execution_success"] = False
            evidence["exit_code"] = exit_code
            summary_parts.append(
                "execution_result.success=False"
                if exit_code is None
                else f"execution_result.success=False (exit_code={exit_code})"
            )
            detail_parts.append(
                "execution_result reported solver failure"
                if exit_code is None
                else f"execution_result reported solver failure with exit_code={exit_code}"
            )
        if fatal_lines or stats.fatal_detected:
            summary_parts.append(
                fatal_lines[0][:120] if fatal_lines else "fatal marker found in solver log"
            )
            detail_parts.append(
                "solver log contains a FOAM FATAL / floating exception marker"
            )
        return AttestorCheck(
            check_id="A1",
            concern_type="SOLVER_CRASH_LOG",
            verdict="FAIL",
            summary="; ".join(summary_parts)[:240],
            detail=(
                "DEC-V61-038 A1: "
                + "; ".join(detail_parts)
                + ". A1 fails if either the execution_result reports a non-zero-style "
                "failure or the log itself contains fatal markers, because either signal "
                "means the run cannot be trusted."
            )[:2000],
            evidence=evidence,
        )
    return AttestorCheck(
        check_id="A1",
        concern_type="SOLVER_CRASH_LOG",
        verdict="PASS",
        summary="no execution-result failure or fatal marker in log",
        detail="",
    )


def _check_a2_continuity_floor(log_path: Path, thresholds: Thresholds) -> AttestorCheck:
    stats = parse_solver_log(log_path)
    sl = stats.final_continuity_sum_local
    if sl is None:
        return AttestorCheck(
            check_id="A2", concern_type="CONTINUITY_NOT_CONVERGED", verdict="PASS",
            summary="no continuity line in log (case may not report it)",
            detail="",
        )
    if sl > thresholds.continuity_floor:
        # Codex DEC-038 round-1 A2/G5 split-brain comment: A2 stays strictly
        # HAZARD here to avoid conflict with G5, which hard-FAILs
        # `sum_local > 1e-2` on the gate side. Keeping A2 as HAZARD means
        # the attestor tier is purely diagnostic; the FAIL call belongs to
        # the gate layer. Previously A2 returned FAIL for >1e-2, but the
        # verdict engine did not hard-FAIL on CONTINUITY_NOT_CONVERGED, so
        # the semantics split across layers. Now A2 is always HAZARD-tier.
        verdict: CheckVerdict = "HAZARD"
        return AttestorCheck(
            check_id="A2",
            concern_type="CONTINUITY_NOT_CONVERGED",
            verdict=verdict,
            summary=(f"final sum_local={sl:.3g} > floor {thresholds.continuity_floor:.0e}")[:240],
            detail=(
                f"DEC-V61-038 A2: incompressible steady continuity error at "
                f"convergence should be ≤ {thresholds.continuity_floor:.0e}. Observed "
                f"final sum_local={sl:.6g}. Values between {thresholds.continuity_floor:.0e} "
                f"and 1e-2 are HAZARD (marginal convergence); >1e-2 is FAIL "
                "(DEC-036b G5 also fires)."
            )[:2000],
            evidence={"sum_local": sl, "threshold": thresholds.continuity_floor},
        )
    return AttestorCheck(
        check_id="A2", concern_type="CONTINUITY_NOT_CONVERGED", verdict="PASS",
        summary=f"final sum_local={sl:.3g} ≤ {thresholds.continuity_floor:.0e}",
        detail="",
    )


def _check_a3_residual_floor(log_path: Path, thresholds: Thresholds) -> AttestorCheck:
    timeline = _parse_residual_timeline(log_path)
    if not timeline:
        return AttestorCheck(
            check_id="A3", concern_type="RESIDUALS_ABOVE_TARGET", verdict="PASS",
            summary="no residual lines parsed from log",
            detail="",
        )
    offenders: dict[str, float] = {}
    offender_thresholds: dict[str, float] = {}
    for field_name, history in timeline.items():
        last = history[-1]
        threshold = thresholds.residual_floor_per_field.get(
            field_name,
            thresholds.residual_floor,
        )
        if last > threshold:
            offenders[field_name] = last
            offender_thresholds[field_name] = threshold
    if offenders:
        sorted_off = sorted(offenders.items(), key=lambda kv: -kv[1])
        summary = (
            "final residuals above field targets: "
            + ", ".join(
                f"{field_name}={value:.3g}>{offender_thresholds[field_name]:.3g}"
                for field_name, value in sorted_off[:3]
            )
        )[:240]
        return AttestorCheck(
            check_id="A3", concern_type="RESIDUALS_ABOVE_TARGET",
            verdict="HAZARD",
            summary=summary,
            detail=(
                "DEC-V61-038 A3: at convergence, SIMPLE/PISO initial residuals "
                "should be ≤ each field's configured threshold. Fields listed "
                "above have final-iteration Initial residuals exceeding their "
                "per-field targets. This "
                "may be physically expected for some cases (impinging_jet "
                "p_rgh, RBC oscillatory modes) — HAZARD not FAIL until a "
                "per-case override promotes it."
            )[:2000],
            evidence={
                "offenders": offenders,
                "thresholds_by_field": offender_thresholds,
                "default_threshold": thresholds.residual_floor,
            },
        )
    return AttestorCheck(
        check_id="A3", concern_type="RESIDUALS_ABOVE_TARGET", verdict="PASS",
        summary="all residuals ≤ their configured field thresholds",
        detail="",
    )


def _check_a4_iteration_cap(log_path: Path, thresholds: Thresholds) -> AttestorCheck:
    per_block = _parse_iteration_caps_per_block(log_path)
    if not per_block:
        return AttestorCheck(
            check_id="A4", concern_type="SOLVER_ITERATION_CAP", verdict="PASS",
            summary="no pressure solver iteration counts in log",
            detail="",
        )
    consecutive = 0
    max_consecutive = 0
    cap_hits = 0
    max_iterations = 0
    for b_max in per_block:
        if b_max > max_iterations:
            max_iterations = b_max
        if b_max in A4_ITERATION_CAP_VALUES or b_max >= 1000:
            consecutive += 1
            cap_hits += 1
            if consecutive > max_consecutive:
                max_consecutive = consecutive
            if consecutive >= thresholds.iteration_cap_detector_count:
                return AttestorCheck(
                    check_id="A4", concern_type="SOLVER_ITERATION_CAP",
                    verdict="FAIL",
                    summary=(
                        f"pressure solver hit {b_max} iterations in "
                        f"≥ {thresholds.iteration_cap_detector_count} consecutive time-step blocks"
                    )[:240],
                    detail=(
                        "DEC-V61-038 A4: pressure-velocity solver loop is "
                        f"hitting its iteration cap (~{b_max}) in at least "
                        f"{thresholds.iteration_cap_detector_count} consecutive time-step blocks "
                        "(Time = ... dividers). SIMPLE/PISO/PIMPLE coupling "
                        "has effectively failed — the solver is burning CPU "
                        "without reducing the residual. Hard FAIL."
                    )[:2000],
                    evidence={
                        "consecutive_cap_blocks": consecutive,
                        "max_consecutive_cap_blocks": max_consecutive,
                        "final_cap_value": b_max,
                        "total_blocks": len(per_block),
                    },
                )
        else:
            consecutive = 0
    return AttestorCheck(
        check_id="A4", concern_type="SOLVER_ITERATION_CAP", verdict="PASS",
        summary=(
            f"pressure solver peaked at {max_iterations} iterations; "
            f"max consecutive cap streak={max_consecutive}"
            if cap_hits
            else f"no capped pressure-solver blocks across {len(per_block)} time steps"
        )[:240],
        detail="",
    )


def _check_a5_bounding_recurrence(log_path: Path, thresholds: Thresholds) -> AttestorCheck:
    blocks = _parse_bounding_lines_per_step(log_path)
    if len(blocks) < 5:
        # Too few time steps to judge recurrence.
        return AttestorCheck(
            check_id="A5", concern_type="BOUNDING_RECURRENT", verdict="PASS",
            summary=f"only {len(blocks)} time-step blocks parsed",
            detail="",
        )
    window = blocks[-thresholds.bounding_recurrence_window:]
    if not window:
        return AttestorCheck(
            check_id="A5", concern_type="BOUNDING_RECURRENT", verdict="PASS",
            summary="no final-window blocks",
            detail="",
        )
    per_field_frac: dict[str, float] = {}
    for field_name in ("k", "epsilon", "omega", "nuTilda", "nut"):
        bounded_count = sum(1 for b in window if field_name in b)
        if bounded_count == 0:
            continue
        frac = bounded_count / len(window)
        per_field_frac[field_name] = frac
    offenders = {k: v for k, v in per_field_frac.items()
                 if v >= thresholds.bounding_recurrence_frac_threshold}
    if offenders:
        top = max(offenders.items(), key=lambda kv: kv[1])
        return AttestorCheck(
            check_id="A5", concern_type="BOUNDING_RECURRENT",
            verdict="HAZARD",
            summary=(
                f"{top[0]} bounded in {top[1]*100:.0f}% of last "
                f"{len(window)} iterations (threshold "
                f"{thresholds.bounding_recurrence_frac_threshold*100:.0f}%)"
            )[:240],
            detail=(
                "DEC-V61-038 A5: turbulence field is being clipped in a large "
                f"fraction of the FINAL {len(window)} iterations. Healthy "
                "convergence shows bounding events in early transients then "
                "stabilises. Recurrent bounding in the tail indicates the "
                "solution never settles — 'converged' residuals are an artefact "
                "of clipping, not physical equilibrium."
            )[:2000],
            evidence={"per_field_fraction": per_field_frac, "window": len(window)},
        )
    return AttestorCheck(
        check_id="A5", concern_type="BOUNDING_RECURRENT", verdict="PASS",
        summary=(
            f"bounding fractions in last {len(window)} iters: "
            + ", ".join(f"{k}={v:.0%}" for k, v in per_field_frac.items())
            if per_field_frac else f"no bounding in last {len(window)} iters"
        )[:240],
        detail="",
    )


def _check_a6_no_progress(log_path: Path, thresholds: Thresholds) -> AttestorCheck:
    timeline = _parse_residual_timeline(log_path)
    if not timeline:
        return AttestorCheck(
            check_id="A6", concern_type="NO_RESIDUAL_PROGRESS", verdict="PASS",
            summary="no residuals parsed",
            detail="",
        )
    offenders: dict[str, dict[str, float]] = {}
    for field_name, history in timeline.items():
        if len(history) < thresholds.no_progress_window:
            continue
        window = history[-thresholds.no_progress_window:]
        lo = min(window)
        hi = max(window)
        if lo <= 0 or hi <= 0:
            continue
        # A6 only fires when residuals are STUCK AT A HIGH PLATEAU — i.e.,
        # still above the A3 floor. If residuals have already decayed to
        # convergence (< 1e-3), a small decade-range in the tail is just
        # machine-noise fluctuation, not "stuck". Guard against this
        # false positive (caught on LDC: Ux plateaued at 1e-5 with 0.02
        # decades range — that's converged, not stuck).
        threshold = thresholds.residual_floor_per_field.get(
            field_name,
            thresholds.residual_floor,
        )
        if hi < threshold:
            continue
        decades = math_log10(hi / lo) if hi > lo else 0.0
        if decades <= thresholds.no_progress_decade_frac:
            offenders[field_name] = {
                "decades": decades,
                "lo": lo,
                "hi": hi,
                "threshold": threshold,
            }
    if offenders:
        worst = min(offenders.items(), key=lambda kv: kv[1]["decades"])
        return AttestorCheck(
            check_id="A6", concern_type="NO_RESIDUAL_PROGRESS",
            verdict="HAZARD",
            summary=(
                f"{worst[0]} residual range over last "
                f"{thresholds.no_progress_window} iters: "
                f"{worst[1]['lo']:.2e} – {worst[1]['hi']:.2e} "
                f"({worst[1]['decades']:.2f} decades)"
            )[:240],
            detail=(
                "DEC-V61-038 A6: initial residuals for the fields listed "
                f"above did not decay > {thresholds.no_progress_decade_frac:.1f} decade(s) "
                f"over the last {thresholds.no_progress_window} iterations. Solver is "
                "stuck at a plateau; any scalar extracted from this 'converged' "
                "state is physically ambiguous."
            )[:2000],
            evidence={"offenders": offenders, "window": thresholds.no_progress_window},
        )
    return AttestorCheck(
        check_id="A6", concern_type="NO_RESIDUAL_PROGRESS", verdict="PASS",
        summary=(
            f"all residual histories show > {thresholds.no_progress_decade_frac:.1f} "
            "decade decay in tail window"
        ),
        detail="",
    )


def math_log10(x: float) -> float:
    """log10 with a zero-guard. Inlined to avoid a dependency in this module."""
    import math
    if x <= 0:
        return 0.0
    return math.log10(x)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def attest(
    log_path: Optional[Path],
    execution_result: Any = None,
    case_id: Optional[str] = None,
    thresholds: Optional[Thresholds] = None,
) -> AttestationResult:
    """Run all 6 checks and aggregate verdict.

    Parameters
    ----------
    log_path : Path or None
        Solver log. None → ATTEST_NOT_APPLICABLE.
    execution_result : Any, optional
        Duck-typed object with .success and .exit_code attrs. Used by A1.
    case_id : str, optional
        Whitelist case ID for per-case YAML override lookup.
    thresholds : Thresholds, optional
        Pre-resolved thresholds. If None, calls load_thresholds(case_id).
    """
    if log_path is None or not log_path.is_file():
        return AttestationResult(overall="ATTEST_NOT_APPLICABLE", checks=[])

    resolved_thresholds = thresholds or load_thresholds(case_id)
    checks = [
        _check_a1_solver_crash(log_path, execution_result=execution_result),
        _check_a2_continuity_floor(log_path, resolved_thresholds),
        _check_a3_residual_floor(log_path, resolved_thresholds),
        _check_a4_iteration_cap(log_path, resolved_thresholds),
        _check_a5_bounding_recurrence(log_path, resolved_thresholds),
        _check_a6_no_progress(log_path, resolved_thresholds),
    ]

    has_fail = any(c.verdict == "FAIL" for c in checks)
    has_hazard = any(c.verdict == "HAZARD" for c in checks)
    if has_fail:
        overall: AttestVerdict = "ATTEST_FAIL"
    elif has_hazard:
        overall = "ATTEST_HAZARD"
    else:
        overall = "ATTEST_PASS"

    return AttestationResult(overall=overall, checks=checks)


def check_to_audit_concern_dict(c: AttestorCheck) -> dict[str, Any]:
    """Serialize a non-PASS AttestorCheck as an audit_concerns[] entry."""
    return {
        "concern_type": c.concern_type,
        "summary": c.summary,
        "detail": c.detail,
        "decision_refs": ["DEC-V61-038"],
        "evidence": c.evidence,
        "attestor_check_id": c.check_id,
        "attestor_verdict": c.verdict,
    }

exec
/bin/zsh -lc "sed -n '420,560p' src/comparator_gates.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
            )
        )
        return violations  # sum_local already FAILs; don't double-flag

    if _abs_exceeds_threshold(cumulative, G5_CUMULATIVE_ABS_MAX):
        violations.append(
            GateViolation(
                gate_id="G5",
                concern_type="CONTINUITY_DIVERGED",
                summary=(
                    f"continuity cumulative={cumulative:.3g}, "
                    f"|cum| > {G5_CUMULATIVE_ABS_MAX}"
                )[:240],
                detail=(
                    f"DEC-V61-036b G5: final-iteration cumulative continuity "
                    f"error {cumulative:.6g} exceeds sanity threshold "
                    f"{G5_CUMULATIVE_ABS_MAX}. This is hard divergence — "
                    "the solver state does not satisfy mass conservation."
                )[:2000],
                evidence={
                    "sum_local": sum_local,
                    "cumulative": cumulative,
                    "threshold": G5_CUMULATIVE_ABS_MAX,
                },
            )
        )
    return violations


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def check_all_gates(
    log_path: Optional[Path] = None,
    vtk_dir: Optional[Path] = None,
    U_ref: float = 1.0,
) -> list[GateViolation]:
    """Run G3 + G4 + G5 and return the aggregated list of violations.

    Called from `scripts/phase5_audit_run.py::_audit_fixture_doc` after
    G1 extraction. Each violation becomes an `audit_concerns[]` entry;
    `ui/backend/services/validation_report._derive_contract_status`
    hard-FAILs when any of the concern codes is present.
    """
    log_stats: Optional[LogStats] = None
    if log_path is not None and log_path.is_file():
        log_stats = parse_solver_log(log_path)

    violations: list[GateViolation] = []
    violations.extend(_check_g3_velocity_overflow(log_stats, vtk_dir, U_ref))
    violations.extend(_check_g4_turbulence_negativity(log_stats))
    violations.extend(_check_g5_continuity_divergence(log_stats))
    return violations


def violation_to_audit_concern_dict(v: GateViolation) -> dict[str, Any]:
    """Serialize a GateViolation as an audit_concerns[] fixture entry."""
    return {
        "concern_type": v.concern_type,
        "summary": v.summary,
        "detail": v.detail,
        "decision_refs": ["DEC-V61-036b"],
        "evidence": v.evidence,
    }

Context is loaded. I have the current attestor and gate semantics, the target tests, and the allowed edit surface. Next is to map each requested case to the existing helpers, then patch the two test files only.
  → Map requested Wave 1 A/B coverage onto current helper APIs and existing test structure
  • Patch ui/backend/tests/test_convergence_attestor.py with the 13 requested attestor/YAML/A1/A3/A4/A6 tests
  • Patch ui/backend/tests/test_comparator_gates_g3_g4_g5.py with the requested VTK-reader and G3 boundary tests
  • Self-check diffs against scope and prepare the required Codex Diff Report without claiming pytest passed
codex
映射已经够用了。现在补丁前再看一下两个测试文件尾部，确认追加位置和现有 import 不会冲突，然后直接改。
exec
/bin/zsh -lc "sed -n '240,420p' ui/backend/tests/test_convergence_attestor.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:


def test_a4_passes_on_sparse_cap_hits(tmp_path: Path) -> None:
    """Single-iteration cap is not pathological — solver typically hits
    high counts in transient but recovers."""
    content = (
        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, "
        "No Iterations 1000\n"
        "GAMG:  Solving for p, Initial residual = 0.5, Final residual = 0.01, "
        "No Iterations 50\n"
    )
    log = _write_log(tmp_path, content)
    result = ca.attest(log)
    a4 = next(c for c in result.checks if c.check_id == "A4")
    assert a4.verdict == "PASS"


# ---------------------------------------------------------------------------
# A5 bounding_recurrence
# ---------------------------------------------------------------------------

def test_a5_hazard_on_recurrent_bounding(tmp_path: Path) -> None:
    """≥30% of last 50 iterations with `bounding k` → HAZARD."""
    blocks = []
    for i in range(60):
        blocks.append(f"Time = {i}")
        if i >= 20:  # last 40 iterations all bound k
            blocks.append("bounding k, min: -1e-3 max: 1.0 average: 0.5")
    log = _write_log(tmp_path, "\n".join(blocks) + "\n")
    result = ca.attest(log)
    a5 = next(c for c in result.checks if c.check_id == "A5")
    assert a5.verdict == "HAZARD"
    assert a5.evidence["per_field_fraction"]["k"] >= 0.30


def test_a5_passes_on_early_bounding_only(tmp_path: Path) -> None:
    """Bounding in early transient but not in final window → PASS."""
    blocks = []
    for i in range(60):
        blocks.append(f"Time = {i}")
        if i < 5:  # only first 5 iterations bound
            blocks.append("bounding k, min: -1e-3 max: 1.0 average: 0.5")
    log = _write_log(tmp_path, "\n".join(blocks) + "\n")
    result = ca.attest(log)
    a5 = next(c for c in result.checks if c.check_id == "A5")
    assert a5.verdict == "PASS"


# ---------------------------------------------------------------------------
# A6 no_residual_progress
# ---------------------------------------------------------------------------

def test_a6_hazard_on_high_plateau(tmp_path: Path) -> None:
    """Ux stuck at 0.4 ± 0.02 for 60 iterations → HAZARD (high and flat)."""
    lines = []
    for _ in range(60):
        lines.append(
            "smoothSolver:  Solving for Ux, Initial residual = 0.4, "
            "Final residual = 0.3, No Iterations 20"
        )
    log = _write_log(tmp_path, "\n".join(lines) + "\n")
    result = ca.attest(log)
    a6 = next(c for c in result.checks if c.check_id == "A6")
    assert a6.verdict == "HAZARD"


def test_a6_ignores_converged_plateau(tmp_path: Path) -> None:
    """Ux stuck at 1e-5 (below A3 floor) is converged, not stuck → PASS.

    Codex nit: A6 should not false-positive on fully converged cases
    where residuals hit machine-noise and oscillate in the floor."""
    lines = []
    for _ in range(60):
        lines.append(
            "smoothSolver:  Solving for Ux, Initial residual = 1e-05, "
            "Final residual = 1e-06, No Iterations 2"
        )
    log = _write_log(tmp_path, "\n".join(lines) + "\n")
    result = ca.attest(log)
    a6 = next(c for c in result.checks if c.check_id == "A6")
    assert a6.verdict == "PASS"


# ---------------------------------------------------------------------------
# Real-log integration tests (guarded by file presence)
# ---------------------------------------------------------------------------

_FIELDS = Path("/Users/Zhuanz/Desktop/cfd-harness-unified/reports/phase5_fields")


def _resolve_latest_log(case: str) -> Path | None:
    case_dir = _FIELDS / case
    if not case_dir.is_dir():
        return None
    ts_candidates = [d for d in case_dir.iterdir() if d.is_dir() and d.name != "runs"]
    if not ts_candidates:
        return None
    ts_dir = sorted(ts_candidates)[-1]
    logs = list(ts_dir.glob("log.*"))
    return logs[0] if logs else None


def test_attestor_ldc_real_log_is_pass() -> None:
    """LDC is the gold-overlay PASS reference. Attestor MUST stay clean."""
    log = _resolve_latest_log("lid_driven_cavity")
    if log is None:
        pytest.skip("LDC phase7a log absent")
    result = ca.attest(log)
    assert result.overall == "ATTEST_PASS", (
        f"LDC attestor tripped unexpectedly: {[(c.check_id, c.verdict, c.summary) for c in result.checks if c.verdict != 'PASS']}"
    )


def test_attestor_bfs_real_log_is_hazard_plus_gate_fail() -> None:
    """BFS solver exploded (Codex audit: k≈1e30, ε≈1e30, sum_local≈1e18).

    Post DEC-038 round-1 A2/G5 split-brain fix: attestor alone returns
    ATTEST_HAZARD (A2 HAZARD + A3 HAZARD + A5 HAZARD — no FAIL-tier check
    fires because A4 is clean, A1 is clean). The FAIL contract status
    comes from the G5 gate at the gate layer catching sum_local > 1e-2.

    This test asserts the attestor HAZARD verdict; contract-FAIL coverage
    lives in test_comparator_gates_g3_g4_g5.py::test_gates_fire_on_real_bfs_audit_log.
    """
    log = _resolve_latest_log("backward_facing_step")
    if log is None:
        pytest.skip("BFS phase7a log absent")
    result = ca.attest(log)
    assert result.overall == "ATTEST_HAZARD", f"got {result.overall}"
    # Multiple HAZARD-tier concerns should be present.
    hazard_checks = [c for c in result.checks if c.verdict == "HAZARD"]
    assert len(hazard_checks) >= 2
    # A2 in particular must fire (sum_local=5.25e+18).
    a2 = next(c for c in result.checks if c.check_id == "A2")
    assert a2.verdict == "HAZARD"

exec
/bin/zsh -lc "sed -n '260,460p' ui/backend/tests/test_comparator_gates_g3_g4_g5.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
    assert within is None  # nulled per Codex nit (value IS inside band, but trust is null)


def test_validation_report_hard_fails_on_continuity_diverged() -> None:
    from ui.backend.schemas.validation import (
        AuditConcern,
        GoldStandardReference,
        MeasuredValue,
    )
    from ui.backend.services.validation_report import _derive_contract_status

    gs = GoldStandardReference(
        quantity="reattachment_length",
        ref_value=6.26,
        unit="Xr/H",
        tolerance_pct=0.10,
        citation="Driver 1985",
    )
    m = MeasuredValue(value=6.28, source="fixture", quantity="reattachment_length")
    concerns = [AuditConcern(concern_type="CONTINUITY_DIVERGED", summary="cum=-1434")]
    status, _, _, _, _ = _derive_contract_status(gs, m, [], concerns)
    assert status == "FAIL"


def test_validation_report_preserves_pass_without_gate_concerns() -> None:
    """No gate concerns + value within band → PASS still works."""
    from ui.backend.schemas.validation import (
        GoldStandardReference,
        MeasuredValue,
    )
    from ui.backend.services.validation_report import _derive_contract_status

    gs = GoldStandardReference(
        quantity="u_centerline",
        ref_value=-0.2058,
        unit="dimensionless",
        tolerance_pct=0.05,
        citation="Ghia 1982",
    )
    m = MeasuredValue(value=-0.2050, source="fixture", quantity="u_centerline")
    status, _, within, _, _ = _derive_contract_status(gs, m, [], [])
    assert status == "PASS"
    assert within is True

codex
准备开始改测试文件。我会只追加 import / helper / 新测试，除非现有测试因为 API 形态必须做最小签名兼容，否则不触碰已有断言。
apply patch
patch: completed
/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_convergence_attestor.py
diff --git a/ui/backend/tests/test_convergence_attestor.py b/ui/backend/tests/test_convergence_attestor.py
index a02d5d774bfce941d32895e48f7f3ccc6946faad..59f031641ee8961adbf16dde3136e33ccf20cad5
--- a/ui/backend/tests/test_convergence_attestor.py
+++ b/ui/backend/tests/test_convergence_attestor.py
@@ -12,10 +12,12 @@
 from __future__ import annotations
 
 from pathlib import Path
+from types import SimpleNamespace
 
 import pytest
 
 from src import convergence_attestor as ca
+from src.convergence_attestor import Thresholds, load_thresholds
 
 
 def _write_log(tmp_path: Path, content: str) -> Path:
@@ -239,6 +241,44 @@
     assert a2.verdict == "HAZARD"  # was FAIL pre-fix
 
 
+def test_load_thresholds_defaults() -> None:
+    thresholds = load_thresholds()
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.continuity_floor == pytest.approx(1e-4)
+    assert thresholds.residual_floor == pytest.approx(1e-3)
+    assert thresholds.residual_floor_per_field["p_rgh"] == pytest.approx(1e-2)
+
+
+def test_load_thresholds_per_case_impinging_jet() -> None:
+    thresholds = load_thresholds("impinging_jet")
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.residual_floor_per_field["p_rgh"] == pytest.approx(5e-3)
+    assert thresholds.residual_floor_per_field["Ux"] == pytest.approx(1e-3)
+
+
+def test_load_thresholds_per_case_rayleigh_benard() -> None:
+    thresholds = load_thresholds("rayleigh_benard_convection")
+    assert thresholds.residual_floor_per_field["h"] == pytest.approx(2e-3)
+    assert thresholds.no_progress_decade_frac == pytest.approx(0.3)
+
+
+def test_load_thresholds_unknown_case_falls_back() -> None:
+    defaults = load_thresholds()
+    unknown = load_thresholds("nonexistent_xyz_12345")
+    assert unknown.continuity_floor == defaults.continuity_floor
+    assert unknown.residual_floor == defaults.residual_floor
+    assert unknown.residual_floor_per_field == defaults.residual_floor_per_field
+    assert unknown.no_progress_decade_frac == defaults.no_progress_decade_frac
+
+
+def test_load_thresholds_missing_yaml_uses_hardcoded(tmp_path: Path) -> None:
+    bad_path = tmp_path / "nonexistent.yaml"
+    thresholds = load_thresholds(yaml_path=bad_path)
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.continuity_floor == ca.A2_CONTINUITY_FLOOR
+    assert thresholds.residual_floor == ca.A3_RESIDUAL_FLOOR
+
+
 def test_a4_passes_on_sparse_cap_hits(tmp_path: Path) -> None:
     """Single-iteration cap is not pathological — solver typically hits
     high counts in transient but recovers."""
@@ -254,6 +294,51 @@
     assert a4.verdict == "PASS"
 
 
+def test_a1_exit_code_false_forces_fail(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=False, exit_code=139),
+    )
+    assert result.verdict == "FAIL"
+    assert result.evidence["exit_code"] == 139
+
+
+def test_a1_log_fatal_fires_even_with_success_exit(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nmiddle\nFloating exception\nEnd\n")
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=True, exit_code=0),
+    )
+    assert result.verdict == "FAIL"
+
+
+def test_a1_sigFpe_banner_not_false_positive(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "sigFpe : Enabling floating point exception trapping (FOAM_SIGFPE).\n"
+        "Time = 1\nEnd\n",
+    )
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=True, exit_code=0),
+    )
+    assert result.verdict == "PASS"
+
+
+def test_a3_per_field_threshold_impinging_jet_p_rgh(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "DILUPBiCGStab:  Solving for p_rgh, Initial residual = 6e-3, "
+        "Final residual = 1e-5, No Iterations 2\n",
+    )
+    impinging = ca._check_a3_residual_floor(log, thresholds=load_thresholds("impinging_jet"))
+    default = ca._check_a3_residual_floor(log, thresholds=load_thresholds())
+    assert impinging.verdict == "HAZARD"
+    assert impinging.evidence["thresholds_by_field"]["p_rgh"] == pytest.approx(5e-3)
+    assert default.verdict == "PASS"
+
+
 # ---------------------------------------------------------------------------
 # A5 bounding_recurrence
 # ---------------------------------------------------------------------------
@@ -320,6 +405,59 @@
     assert a6.verdict == "PASS"
 
 
+def test_a6_decade_range_exactly_1_fires_fail(tmp_path: Path) -> None:
+    lines = []
+    for i in range(50):
+        initial = "1.0" if i % 2 == 0 else "10.0"
+        lines.append(
+            f"smoothSolver:  Solving for Ux, Initial residual = {initial}, "
+            "Final residual = 0.5, No Iterations 2"
+        )
+    log = _write_log(tmp_path, "\n".join(lines) + "\n")
+    result = ca._check_a6_no_progress(log, thresholds=load_thresholds())
+    assert result.verdict == "HAZARD"
+    assert result.evidence["offenders"]["Ux"]["decades"] == pytest.approx(1.0)
+
+
+def test_a4_gap_blocks_reset_consecutive(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "Time = 1\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 2\n"
+        "smoothSolver:  Solving for Ux, Initial residual = 0.1, Final residual = 0.01, No Iterations 2\n"
+        "Time = 3\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 4\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n",
+    )
+    result = ca._check_a4_iteration_cap(log, thresholds=load_thresholds())
+    assert result.verdict == "PASS"
+
+
+def test_a4_three_consecutive_caps_fail(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "Time = 1\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 2\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 3\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n",
+    )
+    result = ca._check_a4_iteration_cap(log, thresholds=load_thresholds())
+    assert result.verdict == "FAIL"
+    assert result.evidence["consecutive_cap_blocks"] == 3
+
+
+def test_attest_with_execution_result_failure(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
+    result = ca.attest(log, execution_result=SimpleNamespace(success=False))
+    a1 = next(c for c in result.checks if c.check_id == "A1")
+    assert result.overall == "ATTEST_FAIL"
+    assert a1.verdict == "FAIL"
+
+
 # ---------------------------------------------------------------------------
 # Real-log integration tests (guarded by file presence)
 # ---------------------------------------------------------------------------

diff --git a/ui/backend/tests/test_convergence_attestor.py b/ui/backend/tests/test_convergence_attestor.py
index a02d5d774bfce941d32895e48f7f3ccc6946faad..59f031641ee8961adbf16dde3136e33ccf20cad5
--- a/ui/backend/tests/test_convergence_attestor.py
+++ b/ui/backend/tests/test_convergence_attestor.py
@@ -12,10 +12,12 @@
 from __future__ import annotations
 
 from pathlib import Path
+from types import SimpleNamespace
 
 import pytest
 
 from src import convergence_attestor as ca
+from src.convergence_attestor import Thresholds, load_thresholds
 
 
 def _write_log(tmp_path: Path, content: str) -> Path:
@@ -239,6 +241,44 @@
     assert a2.verdict == "HAZARD"  # was FAIL pre-fix
 
 
+def test_load_thresholds_defaults() -> None:
+    thresholds = load_thresholds()
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.continuity_floor == pytest.approx(1e-4)
+    assert thresholds.residual_floor == pytest.approx(1e-3)
+    assert thresholds.residual_floor_per_field["p_rgh"] == pytest.approx(1e-2)
+
+
+def test_load_thresholds_per_case_impinging_jet() -> None:
+    thresholds = load_thresholds("impinging_jet")
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.residual_floor_per_field["p_rgh"] == pytest.approx(5e-3)
+    assert thresholds.residual_floor_per_field["Ux"] == pytest.approx(1e-3)
+
+
+def test_load_thresholds_per_case_rayleigh_benard() -> None:
+    thresholds = load_thresholds("rayleigh_benard_convection")
+    assert thresholds.residual_floor_per_field["h"] == pytest.approx(2e-3)
+    assert thresholds.no_progress_decade_frac == pytest.approx(0.3)
+
+
+def test_load_thresholds_unknown_case_falls_back() -> None:
+    defaults = load_thresholds()
+    unknown = load_thresholds("nonexistent_xyz_12345")
+    assert unknown.continuity_floor == defaults.continuity_floor
+    assert unknown.residual_floor == defaults.residual_floor
+    assert unknown.residual_floor_per_field == defaults.residual_floor_per_field
+    assert unknown.no_progress_decade_frac == defaults.no_progress_decade_frac
+
+
+def test_load_thresholds_missing_yaml_uses_hardcoded(tmp_path: Path) -> None:
+    bad_path = tmp_path / "nonexistent.yaml"
+    thresholds = load_thresholds(yaml_path=bad_path)
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.continuity_floor == ca.A2_CONTINUITY_FLOOR
+    assert thresholds.residual_floor == ca.A3_RESIDUAL_FLOOR
+
+
 def test_a4_passes_on_sparse_cap_hits(tmp_path: Path) -> None:
     """Single-iteration cap is not pathological — solver typically hits
     high counts in transient but recovers."""
@@ -254,6 +294,51 @@
     assert a4.verdict == "PASS"
 
 
+def test_a1_exit_code_false_forces_fail(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=False, exit_code=139),
+    )
+    assert result.verdict == "FAIL"
+    assert result.evidence["exit_code"] == 139
+
+
+def test_a1_log_fatal_fires_even_with_success_exit(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nmiddle\nFloating exception\nEnd\n")
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=True, exit_code=0),
+    )
+    assert result.verdict == "FAIL"
+
+
+def test_a1_sigFpe_banner_not_false_positive(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "sigFpe : Enabling floating point exception trapping (FOAM_SIGFPE).\n"
+        "Time = 1\nEnd\n",
+    )
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=True, exit_code=0),
+    )
+    assert result.verdict == "PASS"
+
+
+def test_a3_per_field_threshold_impinging_jet_p_rgh(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "DILUPBiCGStab:  Solving for p_rgh, Initial residual = 6e-3, "
+        "Final residual = 1e-5, No Iterations 2\n",
+    )
+    impinging = ca._check_a3_residual_floor(log, thresholds=load_thresholds("impinging_jet"))
+    default = ca._check_a3_residual_floor(log, thresholds=load_thresholds())
+    assert impinging.verdict == "HAZARD"
+    assert impinging.evidence["thresholds_by_field"]["p_rgh"] == pytest.approx(5e-3)
+    assert default.verdict == "PASS"
+
+
 # ---------------------------------------------------------------------------
 # A5 bounding_recurrence
 # ---------------------------------------------------------------------------
@@ -320,6 +405,59 @@
     assert a6.verdict == "PASS"
 
 
+def test_a6_decade_range_exactly_1_fires_fail(tmp_path: Path) -> None:
+    lines = []
+    for i in range(50):
+        initial = "1.0" if i % 2 == 0 else "10.0"
+        lines.append(
+            f"smoothSolver:  Solving for Ux, Initial residual = {initial}, "
+            "Final residual = 0.5, No Iterations 2"
+        )
+    log = _write_log(tmp_path, "\n".join(lines) + "\n")
+    result = ca._check_a6_no_progress(log, thresholds=load_thresholds())
+    assert result.verdict == "HAZARD"
+    assert result.evidence["offenders"]["Ux"]["decades"] == pytest.approx(1.0)
+
+
+def test_a4_gap_blocks_reset_consecutive(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "Time = 1\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 2\n"
+        "smoothSolver:  Solving for Ux, Initial residual = 0.1, Final residual = 0.01, No Iterations 2\n"
+        "Time = 3\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 4\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n",
+    )
+    result = ca._check_a4_iteration_cap(log, thresholds=load_thresholds())
+    assert result.verdict == "PASS"
+
+
+def test_a4_three_consecutive_caps_fail(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "Time = 1\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 2\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 3\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n",
+    )
+    result = ca._check_a4_iteration_cap(log, thresholds=load_thresholds())
+    assert result.verdict == "FAIL"
+    assert result.evidence["consecutive_cap_blocks"] == 3
+
+
+def test_attest_with_execution_result_failure(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
+    result = ca.attest(log, execution_result=SimpleNamespace(success=False))
+    a1 = next(c for c in result.checks if c.check_id == "A1")
+    assert result.overall == "ATTEST_FAIL"
+    assert a1.verdict == "FAIL"
+
+
 # ---------------------------------------------------------------------------
 # Real-log integration tests (guarded by file presence)
 # ---------------------------------------------------------------------------

apply patch
patch: completed
/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
diff --git a/ui/backend/tests/test_comparator_gates_g3_g4_g5.py b/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
index 09b3735d6c46c89142e04c3196200f1ffd8001e2..f842f208509e372ebc3dbb92b3f59a87aa635c7e
--- a/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
+++ b/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
@@ -12,11 +12,14 @@
 from __future__ import annotations
 
 from pathlib import Path
+import sys
+from types import SimpleNamespace
 
 import pytest
 from fastapi.testclient import TestClient
 
 from src import comparator_gates as cg
+from src.comparator_gates import check_all_gates, read_final_velocity_max
 from ui.backend.main import app
 
 
@@ -55,6 +58,30 @@
     return p
 
 
+class _FakeMesh:
+    def __init__(self, *, point_data: dict | None = None, cell_data: dict | None = None) -> None:
+        self.point_data = point_data or {}
+        self.cell_data = cell_data or {}
+
+
+def _write_vtk_stub(path: Path) -> Path:
+    path.parent.mkdir(parents=True, exist_ok=True)
+    path.write_text("stub", encoding="utf-8")
+    return path
+
+
+def _install_fake_pyvista(monkeypatch: pytest.MonkeyPatch, meshes_by_name: dict[str, _FakeMesh]) -> list[str]:
+    reads: list[str] = []
+
+    def fake_read(path_str: str) -> _FakeMesh:
+        name = Path(path_str).name
+        reads.append(name)
+        return meshes_by_name[name]
+
+    monkeypatch.setitem(sys.modules, "pyvista", SimpleNamespace(read=fake_read))
+    return reads
+
+
 # ---------------------------------------------------------------------------
 # Log parsing
 # ---------------------------------------------------------------------------
@@ -167,6 +194,82 @@
     assert g3 == []
 
 
+def test_read_final_velocity_max_skips_allPatches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    _write_vtk_stub(tmp_path / "case_100.vtk")
+    _write_vtk_stub(tmp_path / "allPatches" / "allPatches_100.vtk")
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_100.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+            "allPatches_100.vtk": _FakeMesh(point_data={"U": [[999.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(2.0)
+    assert reads == ["case_100.vtk"]
+
+
+def test_read_final_velocity_max_uses_latest_timestep(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    for name in ("case_100.vtk", "case_200.vtk", "case_500.vtk"):
+        _write_vtk_stub(tmp_path / name)
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_100.vtk": _FakeMesh(point_data={"U": [[999.0, 0.0, 0.0]]}),
+            "case_200.vtk": _FakeMesh(point_data={"U": [[1.0, 0.0, 0.0]]}),
+            "case_500.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(2.0)
+    assert reads == ["case_500.vtk"]
+
+
+def test_read_final_velocity_max_allPatches_only_returns_none(tmp_path: Path) -> None:
+    _write_vtk_stub(tmp_path / "allPatches" / "allPatches_500.vtk")
+    assert read_final_velocity_max(tmp_path) is None
+
+
+def test_read_final_velocity_max_numeric_vs_alphabetic_sort(
+    tmp_path: Path,
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    for name in ("case_10.vtk", "case_100.vtk", "case_2.vtk"):
+        _write_vtk_stub(tmp_path / name)
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_10.vtk": _FakeMesh(point_data={"U": [[10.0, 0.0, 0.0]]}),
+            "case_100.vtk": _FakeMesh(point_data={"U": [[100.0, 0.0, 0.0]]}),
+            "case_2.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(100.0)
+    assert reads == ["case_100.vtk"]
+
+
+def test_read_final_velocity_max_no_timestep_suffix_skipped(tmp_path: Path) -> None:
+    _write_vtk_stub(tmp_path / "bare_case.vtk")
+    assert read_final_velocity_max(tmp_path) is None
+
+
+def test_g3_boundary_99_U_ref_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    monkeypatch.setattr(cg, "read_final_velocity_max", lambda _: 99.0)
+    violations = check_all_gates(log_path=None, vtk_dir=tmp_path, U_ref=1.0)
+    assert [v for v in violations if v.gate_id == "G3"] == []
+
+
+def test_g3_boundary_101_U_ref_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    monkeypatch.setattr(cg, "read_final_velocity_max", lambda _: 101.0)
+    violations = check_all_gates(log_path=None, vtk_dir=tmp_path, U_ref=1.0)
+    g3 = [v for v in violations if v.gate_id == "G3"]
+    assert len(g3) == 1
+    assert g3[0].evidence["u_max"] == pytest.approx(101.0)
+
+
+@pytest.mark.skip(reason="Wave 2 scope")
+def test_g3_u_ref_none_behavior() -> None:
+    pass
+
+
 # ---------------------------------------------------------------------------
 # NaN/Inf safety (Codex DEC-036b round-1 nit)
 # ---------------------------------------------------------------------------
diff --git a/ui/backend/tests/test_convergence_attestor.py b/ui/backend/tests/test_convergence_attestor.py
index a02d5d774bfce941d32895e48f7f3ccc6946faad..59f031641ee8961adbf16dde3136e33ccf20cad5
--- a/ui/backend/tests/test_convergence_attestor.py
+++ b/ui/backend/tests/test_convergence_attestor.py
@@ -12,10 +12,12 @@
 from __future__ import annotations
 
 from pathlib import Path
+from types import SimpleNamespace
 
 import pytest
 
 from src import convergence_attestor as ca
+from src.convergence_attestor import Thresholds, load_thresholds
 
 
 def _write_log(tmp_path: Path, content: str) -> Path:
@@ -239,6 +241,44 @@
     assert a2.verdict == "HAZARD"  # was FAIL pre-fix
 
 
+def test_load_thresholds_defaults() -> None:
+    thresholds = load_thresholds()
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.continuity_floor == pytest.approx(1e-4)
+    assert thresholds.residual_floor == pytest.approx(1e-3)
+    assert thresholds.residual_floor_per_field["p_rgh"] == pytest.approx(1e-2)
+
+
+def test_load_thresholds_per_case_impinging_jet() -> None:
+    thresholds = load_thresholds("impinging_jet")
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.residual_floor_per_field["p_rgh"] == pytest.approx(5e-3)
+    assert thresholds.residual_floor_per_field["Ux"] == pytest.approx(1e-3)
+
+
+def test_load_thresholds_per_case_rayleigh_benard() -> None:
+    thresholds = load_thresholds("rayleigh_benard_convection")
+    assert thresholds.residual_floor_per_field["h"] == pytest.approx(2e-3)
+    assert thresholds.no_progress_decade_frac == pytest.approx(0.3)
+
+
+def test_load_thresholds_unknown_case_falls_back() -> None:
+    defaults = load_thresholds()
+    unknown = load_thresholds("nonexistent_xyz_12345")
+    assert unknown.continuity_floor == defaults.continuity_floor
+    assert unknown.residual_floor == defaults.residual_floor
+    assert unknown.residual_floor_per_field == defaults.residual_floor_per_field
+    assert unknown.no_progress_decade_frac == defaults.no_progress_decade_frac
+
+
+def test_load_thresholds_missing_yaml_uses_hardcoded(tmp_path: Path) -> None:
+    bad_path = tmp_path / "nonexistent.yaml"
+    thresholds = load_thresholds(yaml_path=bad_path)
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.continuity_floor == ca.A2_CONTINUITY_FLOOR
+    assert thresholds.residual_floor == ca.A3_RESIDUAL_FLOOR
+
+
 def test_a4_passes_on_sparse_cap_hits(tmp_path: Path) -> None:
     """Single-iteration cap is not pathological — solver typically hits
     high counts in transient but recovers."""
@@ -254,6 +294,51 @@
     assert a4.verdict == "PASS"
 
 
+def test_a1_exit_code_false_forces_fail(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=False, exit_code=139),
+    )
+    assert result.verdict == "FAIL"
+    assert result.evidence["exit_code"] == 139
+
+
+def test_a1_log_fatal_fires_even_with_success_exit(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nmiddle\nFloating exception\nEnd\n")
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=True, exit_code=0),
+    )
+    assert result.verdict == "FAIL"
+
+
+def test_a1_sigFpe_banner_not_false_positive(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "sigFpe : Enabling floating point exception trapping (FOAM_SIGFPE).\n"
+        "Time = 1\nEnd\n",
+    )
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=True, exit_code=0),
+    )
+    assert result.verdict == "PASS"
+
+
+def test_a3_per_field_threshold_impinging_jet_p_rgh(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "DILUPBiCGStab:  Solving for p_rgh, Initial residual = 6e-3, "
+        "Final residual = 1e-5, No Iterations 2\n",
+    )
+    impinging = ca._check_a3_residual_floor(log, thresholds=load_thresholds("impinging_jet"))
+    default = ca._check_a3_residual_floor(log, thresholds=load_thresholds())
+    assert impinging.verdict == "HAZARD"
+    assert impinging.evidence["thresholds_by_field"]["p_rgh"] == pytest.approx(5e-3)
+    assert default.verdict == "PASS"
+
+
 # ---------------------------------------------------------------------------
 # A5 bounding_recurrence
 # ---------------------------------------------------------------------------
@@ -320,6 +405,59 @@
     assert a6.verdict == "PASS"
 
 
+def test_a6_decade_range_exactly_1_fires_fail(tmp_path: Path) -> None:
+    lines = []
+    for i in range(50):
+        initial = "1.0" if i % 2 == 0 else "10.0"
+        lines.append(
+            f"smoothSolver:  Solving for Ux, Initial residual = {initial}, "
+            "Final residual = 0.5, No Iterations 2"
+        )
+    log = _write_log(tmp_path, "\n".join(lines) + "\n")
+    result = ca._check_a6_no_progress(log, thresholds=load_thresholds())
+    assert result.verdict == "HAZARD"
+    assert result.evidence["offenders"]["Ux"]["decades"] == pytest.approx(1.0)
+
+
+def test_a4_gap_blocks_reset_consecutive(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "Time = 1\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 2\n"
+        "smoothSolver:  Solving for Ux, Initial residual = 0.1, Final residual = 0.01, No Iterations 2\n"
+        "Time = 3\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 4\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n",
+    )
+    result = ca._check_a4_iteration_cap(log, thresholds=load_thresholds())
+    assert result.verdict == "PASS"
+
+
+def test_a4_three_consecutive_caps_fail(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "Time = 1\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 2\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 3\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n",
+    )
+    result = ca._check_a4_iteration_cap(log, thresholds=load_thresholds())
+    assert result.verdict == "FAIL"
+    assert result.evidence["consecutive_cap_blocks"] == 3
+
+
+def test_attest_with_execution_result_failure(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
+    result = ca.attest(log, execution_result=SimpleNamespace(success=False))
+    a1 = next(c for c in result.checks if c.check_id == "A1")
+    assert result.overall == "ATTEST_FAIL"
+    assert a1.verdict == "FAIL"
+
+
 # ---------------------------------------------------------------------------
 # Real-log integration tests (guarded by file presence)
 # ---------------------------------------------------------------------------

diff --git a/ui/backend/tests/test_comparator_gates_g3_g4_g5.py b/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
index 09b3735d6c46c89142e04c3196200f1ffd8001e2..f842f208509e372ebc3dbb92b3f59a87aa635c7e
--- a/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
+++ b/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
@@ -12,11 +12,14 @@
 from __future__ import annotations
 
 from pathlib import Path
+import sys
+from types import SimpleNamespace
 
 import pytest
 from fastapi.testclient import TestClient
 
 from src import comparator_gates as cg
+from src.comparator_gates import check_all_gates, read_final_velocity_max
 from ui.backend.main import app
 
 
@@ -55,6 +58,30 @@
     return p
 
 
+class _FakeMesh:
+    def __init__(self, *, point_data: dict | None = None, cell_data: dict | None = None) -> None:
+        self.point_data = point_data or {}
+        self.cell_data = cell_data or {}
+
+
+def _write_vtk_stub(path: Path) -> Path:
+    path.parent.mkdir(parents=True, exist_ok=True)
+    path.write_text("stub", encoding="utf-8")
+    return path
+
+
+def _install_fake_pyvista(monkeypatch: pytest.MonkeyPatch, meshes_by_name: dict[str, _FakeMesh]) -> list[str]:
+    reads: list[str] = []
+
+    def fake_read(path_str: str) -> _FakeMesh:
+        name = Path(path_str).name
+        reads.append(name)
+        return meshes_by_name[name]
+
+    monkeypatch.setitem(sys.modules, "pyvista", SimpleNamespace(read=fake_read))
+    return reads
+
+
 # ---------------------------------------------------------------------------
 # Log parsing
 # ---------------------------------------------------------------------------
@@ -167,6 +194,82 @@
     assert g3 == []
 
 
+def test_read_final_velocity_max_skips_allPatches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    _write_vtk_stub(tmp_path / "case_100.vtk")
+    _write_vtk_stub(tmp_path / "allPatches" / "allPatches_100.vtk")
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_100.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+            "allPatches_100.vtk": _FakeMesh(point_data={"U": [[999.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(2.0)
+    assert reads == ["case_100.vtk"]
+
+
+def test_read_final_velocity_max_uses_latest_timestep(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    for name in ("case_100.vtk", "case_200.vtk", "case_500.vtk"):
+        _write_vtk_stub(tmp_path / name)
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_100.vtk": _FakeMesh(point_data={"U": [[999.0, 0.0, 0.0]]}),
+            "case_200.vtk": _FakeMesh(point_data={"U": [[1.0, 0.0, 0.0]]}),
+            "case_500.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(2.0)
+    assert reads == ["case_500.vtk"]
+
+
+def test_read_final_velocity_max_allPatches_only_returns_none(tmp_path: Path) -> None:
+    _write_vtk_stub(tmp_path / "allPatches" / "allPatches_500.vtk")
+    assert read_final_velocity_max(tmp_path) is None
+
+
+def test_read_final_velocity_max_numeric_vs_alphabetic_sort(
+    tmp_path: Path,
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    for name in ("case_10.vtk", "case_100.vtk", "case_2.vtk"):
+        _write_vtk_stub(tmp_path / name)
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_10.vtk": _FakeMesh(point_data={"U": [[10.0, 0.0, 0.0]]}),
+            "case_100.vtk": _FakeMesh(point_data={"U": [[100.0, 0.0, 0.0]]}),
+            "case_2.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(100.0)
+    assert reads == ["case_100.vtk"]
+
+
+def test_read_final_velocity_max_no_timestep_suffix_skipped(tmp_path: Path) -> None:
+    _write_vtk_stub(tmp_path / "bare_case.vtk")
+    assert read_final_velocity_max(tmp_path) is None
+
+
+def test_g3_boundary_99_U_ref_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    monkeypatch.setattr(cg, "read_final_velocity_max", lambda _: 99.0)
+    violations = check_all_gates(log_path=None, vtk_dir=tmp_path, U_ref=1.0)
+    assert [v for v in violations if v.gate_id == "G3"] == []
+
+
+def test_g3_boundary_101_U_ref_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    monkeypatch.setattr(cg, "read_final_velocity_max", lambda _: 101.0)
+    violations = check_all_gates(log_path=None, vtk_dir=tmp_path, U_ref=1.0)
+    g3 = [v for v in violations if v.gate_id == "G3"]
+    assert len(g3) == 1
+    assert g3[0].evidence["u_max"] == pytest.approx(101.0)
+
+
+@pytest.mark.skip(reason="Wave 2 scope")
+def test_g3_u_ref_none_behavior() -> None:
+    pass
+
+
 # ---------------------------------------------------------------------------
 # NaN/Inf safety (Codex DEC-036b round-1 nit)
 # ---------------------------------------------------------------------------
diff --git a/ui/backend/tests/test_convergence_attestor.py b/ui/backend/tests/test_convergence_attestor.py
index a02d5d774bfce941d32895e48f7f3ccc6946faad..59f031641ee8961adbf16dde3136e33ccf20cad5
--- a/ui/backend/tests/test_convergence_attestor.py
+++ b/ui/backend/tests/test_convergence_attestor.py
@@ -12,10 +12,12 @@
 from __future__ import annotations
 
 from pathlib import Path
+from types import SimpleNamespace
 
 import pytest
 
 from src import convergence_attestor as ca
+from src.convergence_attestor import Thresholds, load_thresholds
 
 
 def _write_log(tmp_path: Path, content: str) -> Path:
@@ -239,6 +241,44 @@
     assert a2.verdict == "HAZARD"  # was FAIL pre-fix
 
 
+def test_load_thresholds_defaults() -> None:
+    thresholds = load_thresholds()
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.continuity_floor == pytest.approx(1e-4)
+    assert thresholds.residual_floor == pytest.approx(1e-3)
+    assert thresholds.residual_floor_per_field["p_rgh"] == pytest.approx(1e-2)
+
+
+def test_load_thresholds_per_case_impinging_jet() -> None:
+    thresholds = load_thresholds("impinging_jet")
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.residual_floor_per_field["p_rgh"] == pytest.approx(5e-3)
+    assert thresholds.residual_floor_per_field["Ux"] == pytest.approx(1e-3)
+
+
+def test_load_thresholds_per_case_rayleigh_benard() -> None:
+    thresholds = load_thresholds("rayleigh_benard_convection")
+    assert thresholds.residual_floor_per_field["h"] == pytest.approx(2e-3)
+    assert thresholds.no_progress_decade_frac == pytest.approx(0.3)
+
+
+def test_load_thresholds_unknown_case_falls_back() -> None:
+    defaults = load_thresholds()
+    unknown = load_thresholds("nonexistent_xyz_12345")
+    assert unknown.continuity_floor == defaults.continuity_floor
+    assert unknown.residual_floor == defaults.residual_floor
+    assert unknown.residual_floor_per_field == defaults.residual_floor_per_field
+    assert unknown.no_progress_decade_frac == defaults.no_progress_decade_frac
+
+
+def test_load_thresholds_missing_yaml_uses_hardcoded(tmp_path: Path) -> None:
+    bad_path = tmp_path / "nonexistent.yaml"
+    thresholds = load_thresholds(yaml_path=bad_path)
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.continuity_floor == ca.A2_CONTINUITY_FLOOR
+    assert thresholds.residual_floor == ca.A3_RESIDUAL_FLOOR
+
+
 def test_a4_passes_on_sparse_cap_hits(tmp_path: Path) -> None:
     """Single-iteration cap is not pathological — solver typically hits
     high counts in transient but recovers."""
@@ -254,6 +294,51 @@
     assert a4.verdict == "PASS"
 
 
+def test_a1_exit_code_false_forces_fail(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=False, exit_code=139),
+    )
+    assert result.verdict == "FAIL"
+    assert result.evidence["exit_code"] == 139
+
+
+def test_a1_log_fatal_fires_even_with_success_exit(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nmiddle\nFloating exception\nEnd\n")
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=True, exit_code=0),
+    )
+    assert result.verdict == "FAIL"
+
+
+def test_a1_sigFpe_banner_not_false_positive(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "sigFpe : Enabling floating point exception trapping (FOAM_SIGFPE).\n"
+        "Time = 1\nEnd\n",
+    )
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=True, exit_code=0),
+    )
+    assert result.verdict == "PASS"
+
+
+def test_a3_per_field_threshold_impinging_jet_p_rgh(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "DILUPBiCGStab:  Solving for p_rgh, Initial residual = 6e-3, "
+        "Final residual = 1e-5, No Iterations 2\n",
+    )
+    impinging = ca._check_a3_residual_floor(log, thresholds=load_thresholds("impinging_jet"))
+    default = ca._check_a3_residual_floor(log, thresholds=load_thresholds())
+    assert impinging.verdict == "HAZARD"
+    assert impinging.evidence["thresholds_by_field"]["p_rgh"] == pytest.approx(5e-3)
+    assert default.verdict == "PASS"
+
+
 # ---------------------------------------------------------------------------
 # A5 bounding_recurrence
 # ---------------------------------------------------------------------------
@@ -320,6 +405,59 @@
     assert a6.verdict == "PASS"
 
 
+def test_a6_decade_range_exactly_1_fires_fail(tmp_path: Path) -> None:
+    lines = []
+    for i in range(50):
+        initial = "1.0" if i % 2 == 0 else "10.0"
+        lines.append(
+            f"smoothSolver:  Solving for Ux, Initial residual = {initial}, "
+            "Final residual = 0.5, No Iterations 2"
+        )
+    log = _write_log(tmp_path, "\n".join(lines) + "\n")
+    result = ca._check_a6_no_progress(log, thresholds=load_thresholds())
+    assert result.verdict == "HAZARD"
+    assert result.evidence["offenders"]["Ux"]["decades"] == pytest.approx(1.0)
+
+
+def test_a4_gap_blocks_reset_consecutive(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "Time = 1\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 2\n"
+        "smoothSolver:  Solving for Ux, Initial residual = 0.1, Final residual = 0.01, No Iterations 2\n"
+        "Time = 3\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 4\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n",
+    )
+    result = ca._check_a4_iteration_cap(log, thresholds=load_thresholds())
+    assert result.verdict == "PASS"
+
+
+def test_a4_three_consecutive_caps_fail(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "Time = 1\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 2\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 3\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n",
+    )
+    result = ca._check_a4_iteration_cap(log, thresholds=load_thresholds())
+    assert result.verdict == "FAIL"
+    assert result.evidence["consecutive_cap_blocks"] == 3
+
+
+def test_attest_with_execution_result_failure(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
+    result = ca.attest(log, execution_result=SimpleNamespace(success=False))
+    a1 = next(c for c in result.checks if c.check_id == "A1")
+    assert result.overall == "ATTEST_FAIL"
+    assert a1.verdict == "FAIL"
+
+
 # ---------------------------------------------------------------------------
 # Real-log integration tests (guarded by file presence)
 # ---------------------------------------------------------------------------

codex
测试补丁已经落下。现在做本地静态核对：看 diff、检查新 helper / import 是否干净，并用 `py_compile` 做语法验证，不跑 `pytest`。
exec
/bin/zsh -lc 'git diff --numstat -- ui/backend/tests/test_convergence_attestor.py ui/backend/tests/test_comparator_gates_g3_g4_g5.py' in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc 'git diff -- ui/backend/tests/test_convergence_attestor.py ui/backend/tests/test_comparator_gates_g3_g4_g5.py' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
103	0	ui/backend/tests/test_comparator_gates_g3_g4_g5.py
138	0	ui/backend/tests/test_convergence_attestor.py

 succeeded in 0ms:
diff --git a/ui/backend/tests/test_comparator_gates_g3_g4_g5.py b/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
index 09b3735..f842f20 100644
--- a/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
+++ b/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
@@ -12,11 +12,14 @@ Evidence sources:
 from __future__ import annotations
 
 from pathlib import Path
+import sys
+from types import SimpleNamespace
 
 import pytest
 from fastapi.testclient import TestClient
 
 from src import comparator_gates as cg
+from src.comparator_gates import check_all_gates, read_final_velocity_max
 from ui.backend.main import app
 
 
@@ -55,6 +58,30 @@ def _write_log(tmp_path: Path, content: str) -> Path:
     return p
 
 
+class _FakeMesh:
+    def __init__(self, *, point_data: dict | None = None, cell_data: dict | None = None) -> None:
+        self.point_data = point_data or {}
+        self.cell_data = cell_data or {}
+
+
+def _write_vtk_stub(path: Path) -> Path:
+    path.parent.mkdir(parents=True, exist_ok=True)
+    path.write_text("stub", encoding="utf-8")
+    return path
+
+
+def _install_fake_pyvista(monkeypatch: pytest.MonkeyPatch, meshes_by_name: dict[str, _FakeMesh]) -> list[str]:
+    reads: list[str] = []
+
+    def fake_read(path_str: str) -> _FakeMesh:
+        name = Path(path_str).name
+        reads.append(name)
+        return meshes_by_name[name]
+
+    monkeypatch.setitem(sys.modules, "pyvista", SimpleNamespace(read=fake_read))
+    return reads
+
+
 # ---------------------------------------------------------------------------
 # Log parsing
 # ---------------------------------------------------------------------------
@@ -167,6 +194,82 @@ def test_g3_passes_on_clean_ldc_log(tmp_path: Path) -> None:
     assert g3 == []
 
 
+def test_read_final_velocity_max_skips_allPatches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    _write_vtk_stub(tmp_path / "case_100.vtk")
+    _write_vtk_stub(tmp_path / "allPatches" / "allPatches_100.vtk")
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_100.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+            "allPatches_100.vtk": _FakeMesh(point_data={"U": [[999.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(2.0)
+    assert reads == ["case_100.vtk"]
+
+
+def test_read_final_velocity_max_uses_latest_timestep(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    for name in ("case_100.vtk", "case_200.vtk", "case_500.vtk"):
+        _write_vtk_stub(tmp_path / name)
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_100.vtk": _FakeMesh(point_data={"U": [[999.0, 0.0, 0.0]]}),
+            "case_200.vtk": _FakeMesh(point_data={"U": [[1.0, 0.0, 0.0]]}),
+            "case_500.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(2.0)
+    assert reads == ["case_500.vtk"]
+
+
+def test_read_final_velocity_max_allPatches_only_returns_none(tmp_path: Path) -> None:
+    _write_vtk_stub(tmp_path / "allPatches" / "allPatches_500.vtk")
+    assert read_final_velocity_max(tmp_path) is None
+
+
+def test_read_final_velocity_max_numeric_vs_alphabetic_sort(
+    tmp_path: Path,
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    for name in ("case_10.vtk", "case_100.vtk", "case_2.vtk"):
+        _write_vtk_stub(tmp_path / name)
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_10.vtk": _FakeMesh(point_data={"U": [[10.0, 0.0, 0.0]]}),
+            "case_100.vtk": _FakeMesh(point_data={"U": [[100.0, 0.0, 0.0]]}),
+            "case_2.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(100.0)
+    assert reads == ["case_100.vtk"]
+
+
+def test_read_final_velocity_max_no_timestep_suffix_skipped(tmp_path: Path) -> None:
+    _write_vtk_stub(tmp_path / "bare_case.vtk")
+    assert read_final_velocity_max(tmp_path) is None
+
+
+def test_g3_boundary_99_U_ref_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    monkeypatch.setattr(cg, "read_final_velocity_max", lambda _: 99.0)
+    violations = check_all_gates(log_path=None, vtk_dir=tmp_path, U_ref=1.0)
+    assert [v for v in violations if v.gate_id == "G3"] == []
+
+
+def test_g3_boundary_101_U_ref_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    monkeypatch.setattr(cg, "read_final_velocity_max", lambda _: 101.0)
+    violations = check_all_gates(log_path=None, vtk_dir=tmp_path, U_ref=1.0)
+    g3 = [v for v in violations if v.gate_id == "G3"]
+    assert len(g3) == 1
+    assert g3[0].evidence["u_max"] == pytest.approx(101.0)
+
+
+@pytest.mark.skip(reason="Wave 2 scope")
+def test_g3_u_ref_none_behavior() -> None:
+    pass
+
+
 # ---------------------------------------------------------------------------
 # NaN/Inf safety (Codex DEC-036b round-1 nit)
 # ---------------------------------------------------------------------------
diff --git a/ui/backend/tests/test_convergence_attestor.py b/ui/backend/tests/test_convergence_attestor.py
index a02d5d7..59f0316 100644
--- a/ui/backend/tests/test_convergence_attestor.py
+++ b/ui/backend/tests/test_convergence_attestor.py
@@ -12,10 +12,12 @@ Ground truth from Codex round-1 physics audit (DEC-036):
 from __future__ import annotations
 
 from pathlib import Path
+from types import SimpleNamespace
 
 import pytest
 
 from src import convergence_attestor as ca
+from src.convergence_attestor import Thresholds, load_thresholds
 
 
 def _write_log(tmp_path: Path, content: str) -> Path:
@@ -239,6 +241,44 @@ def test_a2_never_returns_fail_only_hazard(tmp_path: Path) -> None:
     assert a2.verdict == "HAZARD"  # was FAIL pre-fix
 
 
+def test_load_thresholds_defaults() -> None:
+    thresholds = load_thresholds()
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.continuity_floor == pytest.approx(1e-4)
+    assert thresholds.residual_floor == pytest.approx(1e-3)
+    assert thresholds.residual_floor_per_field["p_rgh"] == pytest.approx(1e-2)
+
+
+def test_load_thresholds_per_case_impinging_jet() -> None:
+    thresholds = load_thresholds("impinging_jet")
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.residual_floor_per_field["p_rgh"] == pytest.approx(5e-3)
+    assert thresholds.residual_floor_per_field["Ux"] == pytest.approx(1e-3)
+
+
+def test_load_thresholds_per_case_rayleigh_benard() -> None:
+    thresholds = load_thresholds("rayleigh_benard_convection")
+    assert thresholds.residual_floor_per_field["h"] == pytest.approx(2e-3)
+    assert thresholds.no_progress_decade_frac == pytest.approx(0.3)
+
+
+def test_load_thresholds_unknown_case_falls_back() -> None:
+    defaults = load_thresholds()
+    unknown = load_thresholds("nonexistent_xyz_12345")
+    assert unknown.continuity_floor == defaults.continuity_floor
+    assert unknown.residual_floor == defaults.residual_floor
+    assert unknown.residual_floor_per_field == defaults.residual_floor_per_field
+    assert unknown.no_progress_decade_frac == defaults.no_progress_decade_frac
+
+
+def test_load_thresholds_missing_yaml_uses_hardcoded(tmp_path: Path) -> None:
+    bad_path = tmp_path / "nonexistent.yaml"
+    thresholds = load_thresholds(yaml_path=bad_path)
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.continuity_floor == ca.A2_CONTINUITY_FLOOR
+    assert thresholds.residual_floor == ca.A3_RESIDUAL_FLOOR
+
+
 def test_a4_passes_on_sparse_cap_hits(tmp_path: Path) -> None:
     """Single-iteration cap is not pathological — solver typically hits
     high counts in transient but recovers."""
@@ -254,6 +294,51 @@ def test_a4_passes_on_sparse_cap_hits(tmp_path: Path) -> None:
     assert a4.verdict == "PASS"
 
 
+def test_a1_exit_code_false_forces_fail(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=False, exit_code=139),
+    )
+    assert result.verdict == "FAIL"
+    assert result.evidence["exit_code"] == 139
+
+
+def test_a1_log_fatal_fires_even_with_success_exit(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nmiddle\nFloating exception\nEnd\n")
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=True, exit_code=0),
+    )
+    assert result.verdict == "FAIL"
+
+
+def test_a1_sigFpe_banner_not_false_positive(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "sigFpe : Enabling floating point exception trapping (FOAM_SIGFPE).\n"
+        "Time = 1\nEnd\n",
+    )
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=True, exit_code=0),
+    )
+    assert result.verdict == "PASS"
+
+
+def test_a3_per_field_threshold_impinging_jet_p_rgh(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "DILUPBiCGStab:  Solving for p_rgh, Initial residual = 6e-3, "
+        "Final residual = 1e-5, No Iterations 2\n",
+    )
+    impinging = ca._check_a3_residual_floor(log, thresholds=load_thresholds("impinging_jet"))
+    default = ca._check_a3_residual_floor(log, thresholds=load_thresholds())
+    assert impinging.verdict == "HAZARD"
+    assert impinging.evidence["thresholds_by_field"]["p_rgh"] == pytest.approx(5e-3)
+    assert default.verdict == "PASS"
+
+
 # ---------------------------------------------------------------------------
 # A5 bounding_recurrence
 # ---------------------------------------------------------------------------
@@ -320,6 +405,59 @@ def test_a6_ignores_converged_plateau(tmp_path: Path) -> None:
     assert a6.verdict == "PASS"
 
 
+def test_a6_decade_range_exactly_1_fires_fail(tmp_path: Path) -> None:
+    lines = []
+    for i in range(50):
+        initial = "1.0" if i % 2 == 0 else "10.0"
+        lines.append(
+            f"smoothSolver:  Solving for Ux, Initial residual = {initial}, "
+            "Final residual = 0.5, No Iterations 2"
+        )
+    log = _write_log(tmp_path, "\n".join(lines) + "\n")
+    result = ca._check_a6_no_progress(log, thresholds=load_thresholds())
+    assert result.verdict == "HAZARD"
+    assert result.evidence["offenders"]["Ux"]["decades"] == pytest.approx(1.0)
+
+
+def test_a4_gap_blocks_reset_consecutive(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "Time = 1\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 2\n"
+        "smoothSolver:  Solving for Ux, Initial residual = 0.1, Final residual = 0.01, No Iterations 2\n"
+        "Time = 3\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 4\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n",
+    )
+    result = ca._check_a4_iteration_cap(log, thresholds=load_thresholds())
+    assert result.verdict == "PASS"
+
+
+def test_a4_three_consecutive_caps_fail(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "Time = 1\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 2\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 3\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n",
+    )
+    result = ca._check_a4_iteration_cap(log, thresholds=load_thresholds())
+    assert result.verdict == "FAIL"
+    assert result.evidence["consecutive_cap_blocks"] == 3
+
+
+def test_attest_with_execution_result_failure(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
+    result = ca.attest(log, execution_result=SimpleNamespace(success=False))
+    a1 = next(c for c in result.checks if c.check_id == "A1")
+    assert result.overall == "ATTEST_FAIL"
+    assert a1.verdict == "FAIL"
+
+
 # ---------------------------------------------------------------------------
 # Real-log integration tests (guarded by file presence)
 # ---------------------------------------------------------------------------

2026-04-22T11:44:48.037022Z ERROR codex_core::tools::router: error=exec_command failed for `/bin/zsh -lc 'python3 -m py_compile ui/backend/tests/test_convergence_attestor.py ui/backend/tests/test_comparator_gates_g3_g4_g5.py'`: CreateProcess { message: "Codex(Sandbox(Denied { output: ExecToolCallOutput { exit_code: 1, stdout: StreamOutput { text: \"\", truncated_after_lines: None }, stderr: StreamOutput { text: \"Traceback (most recent call last):\\n  File \\\"/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/runpy.py\\\", line 197, in _run_module_as_main\\n    return _run_code(code, main_globals, None,\\n  File \\\"/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/runpy.py\\\", line 87, in _run_code\\n    exec(code, run_globals)\\n  File \\\"/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/py_compile.py\\\", line 215, in <module>\\n    sys.exit(main())\\n  File \\\"/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/py_compile.py\\\", line 207, in main\\n    compile(filename, doraise=True)\\n  File \\\"/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/py_compile.py\\\", line 172, in compile\\n    importlib._bootstrap_external._write_atomic(cfile, bytecode, mode)\\n  File \\\"<frozen importlib._bootstrap_external>\\\", line 186, in _write_atomic\\nPermissionError: [Errno 1] Operation not permitted: '/Users/Zhuanz/Library/Caches/com.apple.python/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_convergence_attestor.cpython-39.pyc.4455865648'\\n\", truncated_after_lines: None }, aggregated_output: StreamOutput { text: \"Traceback (most recent call last):\\n  File \\\"/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/runpy.py\\\", line 197, in _run_module_as_main\\n    return _run_code(code, main_globals, None,\\n  File \\\"/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/runpy.py\\\", line 87, in _run_code\\n    exec(code, run_globals)\\n  File \\\"/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/py_compile.py\\\", line 215, in <module>\\n    sys.exit(main())\\n  File \\\"/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/py_compile.py\\\", line 207, in main\\n    compile(filename, doraise=True)\\n  File \\\"/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/py_compile.py\\\", line 172, in compile\\n    importlib._bootstrap_external._write_atomic(cfile, bytecode, mode)\\n  File \\\"<frozen importlib._bootstrap_external>\\\", line 186, in _write_atomic\\nPermissionError: [Errno 1] Operation not permitted: '/Users/Zhuanz/Library/Caches/com.apple.python/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_convergence_attestor.cpython-39.pyc.4455865648'\\n\", truncated_after_lines: None }, duration: 0ns, timed_out: false }, network_policy_decision: None }))" }
diff --git a/ui/backend/tests/test_comparator_gates_g3_g4_g5.py b/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
index 09b3735d6c46c89142e04c3196200f1ffd8001e2..f842f208509e372ebc3dbb92b3f59a87aa635c7e
--- a/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
+++ b/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
@@ -12,11 +12,14 @@
 from __future__ import annotations
 
 from pathlib import Path
+import sys
+from types import SimpleNamespace
 
 import pytest
 from fastapi.testclient import TestClient
 
 from src import comparator_gates as cg
+from src.comparator_gates import check_all_gates, read_final_velocity_max
 from ui.backend.main import app
 
 
@@ -55,6 +58,30 @@
     return p
 
 
+class _FakeMesh:
+    def __init__(self, *, point_data: dict | None = None, cell_data: dict | None = None) -> None:
+        self.point_data = point_data or {}
+        self.cell_data = cell_data or {}
+
+
+def _write_vtk_stub(path: Path) -> Path:
+    path.parent.mkdir(parents=True, exist_ok=True)
+    path.write_text("stub", encoding="utf-8")
+    return path
+
+
+def _install_fake_pyvista(monkeypatch: pytest.MonkeyPatch, meshes_by_name: dict[str, _FakeMesh]) -> list[str]:
+    reads: list[str] = []
+
+    def fake_read(path_str: str) -> _FakeMesh:
+        name = Path(path_str).name
+        reads.append(name)
+        return meshes_by_name[name]
+
+    monkeypatch.setitem(sys.modules, "pyvista", SimpleNamespace(read=fake_read))
+    return reads
+
+
 # ---------------------------------------------------------------------------
 # Log parsing
 # ---------------------------------------------------------------------------
@@ -167,6 +194,82 @@
     assert g3 == []
 
 
+def test_read_final_velocity_max_skips_allPatches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    _write_vtk_stub(tmp_path / "case_100.vtk")
+    _write_vtk_stub(tmp_path / "allPatches" / "allPatches_100.vtk")
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_100.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+            "allPatches_100.vtk": _FakeMesh(point_data={"U": [[999.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(2.0)
+    assert reads == ["case_100.vtk"]
+
+
+def test_read_final_velocity_max_uses_latest_timestep(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    for name in ("case_100.vtk", "case_200.vtk", "case_500.vtk"):
+        _write_vtk_stub(tmp_path / name)
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_100.vtk": _FakeMesh(point_data={"U": [[999.0, 0.0, 0.0]]}),
+            "case_200.vtk": _FakeMesh(point_data={"U": [[1.0, 0.0, 0.0]]}),
+            "case_500.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(2.0)
+    assert reads == ["case_500.vtk"]
+
+
+def test_read_final_velocity_max_allPatches_only_returns_none(tmp_path: Path) -> None:
+    _write_vtk_stub(tmp_path / "allPatches" / "allPatches_500.vtk")
+    assert read_final_velocity_max(tmp_path) is None
+
+
+def test_read_final_velocity_max_numeric_vs_alphabetic_sort(
+    tmp_path: Path,
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    for name in ("case_10.vtk", "case_100.vtk", "case_2.vtk"):
+        _write_vtk_stub(tmp_path / name)
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_10.vtk": _FakeMesh(point_data={"U": [[10.0, 0.0, 0.0]]}),
+            "case_100.vtk": _FakeMesh(point_data={"U": [[100.0, 0.0, 0.0]]}),
+            "case_2.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(100.0)
+    assert reads == ["case_100.vtk"]
+
+
+def test_read_final_velocity_max_no_timestep_suffix_skipped(tmp_path: Path) -> None:
+    _write_vtk_stub(tmp_path / "bare_case.vtk")
+    assert read_final_velocity_max(tmp_path) is None
+
+
+def test_g3_boundary_99_U_ref_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    monkeypatch.setattr(cg, "read_final_velocity_max", lambda _: 99.0)
+    violations = check_all_gates(log_path=None, vtk_dir=tmp_path, U_ref=1.0)
+    assert [v for v in violations if v.gate_id == "G3"] == []
+
+
+def test_g3_boundary_101_U_ref_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    monkeypatch.setattr(cg, "read_final_velocity_max", lambda _: 101.0)
+    violations = check_all_gates(log_path=None, vtk_dir=tmp_path, U_ref=1.0)
+    g3 = [v for v in violations if v.gate_id == "G3"]
+    assert len(g3) == 1
+    assert g3[0].evidence["u_max"] == pytest.approx(101.0)
+
+
+@pytest.mark.skip(reason="Wave 2 scope")
+def test_g3_u_ref_none_behavior() -> None:
+    pass
+
+
 # ---------------------------------------------------------------------------
 # NaN/Inf safety (Codex DEC-036b round-1 nit)
 # ---------------------------------------------------------------------------
diff --git a/ui/backend/tests/test_convergence_attestor.py b/ui/backend/tests/test_convergence_attestor.py
index a02d5d774bfce941d32895e48f7f3ccc6946faad..59f031641ee8961adbf16dde3136e33ccf20cad5
--- a/ui/backend/tests/test_convergence_attestor.py
+++ b/ui/backend/tests/test_convergence_attestor.py
@@ -12,10 +12,12 @@
 from __future__ import annotations
 
 from pathlib import Path
+from types import SimpleNamespace
 
 import pytest
 
 from src import convergence_attestor as ca
+from src.convergence_attestor import Thresholds, load_thresholds
 
 
 def _write_log(tmp_path: Path, content: str) -> Path:
@@ -239,6 +241,44 @@
     assert a2.verdict == "HAZARD"  # was FAIL pre-fix
 
 
+def test_load_thresholds_defaults() -> None:
+    thresholds = load_thresholds()
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.continuity_floor == pytest.approx(1e-4)
+    assert thresholds.residual_floor == pytest.approx(1e-3)
+    assert thresholds.residual_floor_per_field["p_rgh"] == pytest.approx(1e-2)
+
+
+def test_load_thresholds_per_case_impinging_jet() -> None:
+    thresholds = load_thresholds("impinging_jet")
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.residual_floor_per_field["p_rgh"] == pytest.approx(5e-3)
+    assert thresholds.residual_floor_per_field["Ux"] == pytest.approx(1e-3)
+
+
+def test_load_thresholds_per_case_rayleigh_benard() -> None:
+    thresholds = load_thresholds("rayleigh_benard_convection")
+    assert thresholds.residual_floor_per_field["h"] == pytest.approx(2e-3)
+    assert thresholds.no_progress_decade_frac == pytest.approx(0.3)
+
+
+def test_load_thresholds_unknown_case_falls_back() -> None:
+    defaults = load_thresholds()
+    unknown = load_thresholds("nonexistent_xyz_12345")
+    assert unknown.continuity_floor == defaults.continuity_floor
+    assert unknown.residual_floor == defaults.residual_floor
+    assert unknown.residual_floor_per_field == defaults.residual_floor_per_field
+    assert unknown.no_progress_decade_frac == defaults.no_progress_decade_frac
+
+
+def test_load_thresholds_missing_yaml_uses_hardcoded(tmp_path: Path) -> None:
+    bad_path = tmp_path / "nonexistent.yaml"
+    thresholds = load_thresholds(yaml_path=bad_path)
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.continuity_floor == ca.A2_CONTINUITY_FLOOR
+    assert thresholds.residual_floor == ca.A3_RESIDUAL_FLOOR
+
+
 def test_a4_passes_on_sparse_cap_hits(tmp_path: Path) -> None:
     """Single-iteration cap is not pathological — solver typically hits
     high counts in transient but recovers."""
@@ -254,6 +294,51 @@
     assert a4.verdict == "PASS"
 
 
+def test_a1_exit_code_false_forces_fail(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=False, exit_code=139),
+    )
+    assert result.verdict == "FAIL"
+    assert result.evidence["exit_code"] == 139
+
+
+def test_a1_log_fatal_fires_even_with_success_exit(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nmiddle\nFloating exception\nEnd\n")
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=True, exit_code=0),
+    )
+    assert result.verdict == "FAIL"
+
+
+def test_a1_sigFpe_banner_not_false_positive(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "sigFpe : Enabling floating point exception trapping (FOAM_SIGFPE).\n"
+        "Time = 1\nEnd\n",
+    )
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=True, exit_code=0),
+    )
+    assert result.verdict == "PASS"
+
+
+def test_a3_per_field_threshold_impinging_jet_p_rgh(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "DILUPBiCGStab:  Solving for p_rgh, Initial residual = 6e-3, "
+        "Final residual = 1e-5, No Iterations 2\n",
+    )
+    impinging = ca._check_a3_residual_floor(log, thresholds=load_thresholds("impinging_jet"))
+    default = ca._check_a3_residual_floor(log, thresholds=load_thresholds())
+    assert impinging.verdict == "HAZARD"
+    assert impinging.evidence["thresholds_by_field"]["p_rgh"] == pytest.approx(5e-3)
+    assert default.verdict == "PASS"
+
+
 # ---------------------------------------------------------------------------
 # A5 bounding_recurrence
 # ---------------------------------------------------------------------------
@@ -320,6 +405,59 @@
     assert a6.verdict == "PASS"
 
 
+def test_a6_decade_range_exactly_1_fires_fail(tmp_path: Path) -> None:
+    lines = []
+    for i in range(50):
+        initial = "1.0" if i % 2 == 0 else "10.0"
+        lines.append(
+            f"smoothSolver:  Solving for Ux, Initial residual = {initial}, "
+            "Final residual = 0.5, No Iterations 2"
+        )
+    log = _write_log(tmp_path, "\n".join(lines) + "\n")
+    result = ca._check_a6_no_progress(log, thresholds=load_thresholds())
+    assert result.verdict == "HAZARD"
+    assert result.evidence["offenders"]["Ux"]["decades"] == pytest.approx(1.0)
+
+
+def test_a4_gap_blocks_reset_consecutive(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "Time = 1\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 2\n"
+        "smoothSolver:  Solving for Ux, Initial residual = 0.1, Final residual = 0.01, No Iterations 2\n"
+        "Time = 3\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 4\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n",
+    )
+    result = ca._check_a4_iteration_cap(log, thresholds=load_thresholds())
+    assert result.verdict == "PASS"
+
+
+def test_a4_three_consecutive_caps_fail(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "Time = 1\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 2\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 3\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n",
+    )
+    result = ca._check_a4_iteration_cap(log, thresholds=load_thresholds())
+    assert result.verdict == "FAIL"
+    assert result.evidence["consecutive_cap_blocks"] == 3
+
+
+def test_attest_with_execution_result_failure(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
+    result = ca.attest(log, execution_result=SimpleNamespace(success=False))
+    a1 = next(c for c in result.checks if c.check_id == "A1")
+    assert result.overall == "ATTEST_FAIL"
+    assert a1.verdict == "FAIL"
+
+
 # ---------------------------------------------------------------------------
 # Real-log integration tests (guarded by file presence)
 # ---------------------------------------------------------------------------

codex
`py_compile` 第一次被 macOS cache 目录权限拦住了，不是代码错误。我改用临时 `PYTHONPYCACHEPREFIX` 复跑，这样能做同等语法检查而不触碰受限缓存路径。
exec
/bin/zsh -lc "nl -ba ui/backend/tests/test_convergence_attestor.py | sed -n '1,220p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba ui/backend/tests/test_comparator_gates_g3_g4_g5.py | sed -n '1,280p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
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
    15	from types import SimpleNamespace
    16	
    17	import pytest
    18	
    19	from src import convergence_attestor as ca
    20	from src.convergence_attestor import Thresholds, load_thresholds
    21	
    22	
    23	def _write_log(tmp_path: Path, content: str) -> Path:
    24	    p = tmp_path / "log.simpleFoam"
    25	    p.write_text(content, encoding="utf-8")
    26	    return p
    27	
    28	
    29	# ---------------------------------------------------------------------------
    30	# A1 solver_exit_clean
    31	# ---------------------------------------------------------------------------
    32	
    33	def test_a1_passes_on_clean_log(tmp_path: Path) -> None:
    34	    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
    35	    result = ca.attest(log)
    36	    a1 = next(c for c in result.checks if c.check_id == "A1")
    37	    assert a1.verdict == "PASS"
    38	
    39	
    40	def test_a1_fails_on_foam_fatal(tmp_path: Path) -> None:
    41	    content = "Time = 1\nFOAM FATAL IO ERROR: missing dict\nExiting\n"
    42	    log = _write_log(tmp_path, content)
    43	    result = ca.attest(log)
    44	    a1 = next(c for c in result.checks if c.check_id == "A1")
    45	    assert a1.verdict == "FAIL"
    46	    assert result.overall == "ATTEST_FAIL"
    47	
    48	
    49	def test_a1_ignores_sigfpe_startup_banner(tmp_path: Path) -> None:
    50	    """DEC-036b Codex nit: 'floating point exception trapping' is a
    51	    startup banner, not an actual exception. Must NOT fire A1."""
    52	    content = (
    53	        "sigFpe : Enabling floating point exception trapping (FOAM_SIGFPE).\n"
    54	        "Time = 1\nEnd\n"
    55	    )
    56	    log = _write_log(tmp_path, content)
    57	    result = ca.attest(log)
    58	    a1 = next(c for c in result.checks if c.check_id == "A1")
    59	    assert a1.verdict == "PASS"
    60	
    61	
    62	# ---------------------------------------------------------------------------
    63	# A2 continuity_floor
    64	# ---------------------------------------------------------------------------
    65	
    66	def test_a2_passes_on_clean_continuity(tmp_path: Path) -> None:
    67	    content = (
    68	        "time step continuity errors : "
    69	        "sum local = 1e-07, global = 1e-09, cumulative = 1e-12\n"
    70	    )
    71	    log = _write_log(tmp_path, content)
    72	    result = ca.attest(log)
    73	    a2 = next(c for c in result.checks if c.check_id == "A2")
    74	    assert a2.verdict == "PASS"
    75	
    76	
    77	def test_a2_hazard_between_floors(tmp_path: Path) -> None:
    78	    """sum_local between A2 floor (1e-4) and G5 floor (1e-2) → HAZARD."""
    79	    content = (
    80	        "time step continuity errors : "
    81	        "sum local = 1e-03, global = 1e-05, cumulative = 0.001\n"
    82	    )
    83	    log = _write_log(tmp_path, content)
    84	    result = ca.attest(log)
    85	    a2 = next(c for c in result.checks if c.check_id == "A2")
    86	    assert a2.verdict == "HAZARD"
    87	
    88	
    89	def test_a2_hazard_above_g5_floor_after_split_brain_fix(tmp_path: Path) -> None:
    90	    """Codex DEC-038 round-1 A2/G5 split-brain fix: A2 no longer returns
    91	    FAIL even for sum_local > 1e-2. That FAIL call belongs to G5 at the
    92	    gate layer. A2 stays strictly HAZARD-tier."""
    93	    content = (
    94	        "time step continuity errors : "
    95	        "sum local = 0.5, global = 0.01, cumulative = 0.1\n"
    96	    )
    97	    log = _write_log(tmp_path, content)
    98	    result = ca.attest(log)
    99	    a2 = next(c for c in result.checks if c.check_id == "A2")
   100	    assert a2.verdict == "HAZARD"  # was FAIL pre-fix
   101	
   102	
   103	# ---------------------------------------------------------------------------
   104	# A3 residual_floor
   105	# ---------------------------------------------------------------------------
   106	
   107	def test_a3_passes_when_all_residuals_below_floor(tmp_path: Path) -> None:
   108	    content = (
   109	        "smoothSolver:  Solving for Ux, Initial residual = 1e-06, "
   110	        "Final residual = 1e-07, No Iterations 2\n"
   111	    )
   112	    log = _write_log(tmp_path, content)
   113	    result = ca.attest(log)
   114	    a3 = next(c for c in result.checks if c.check_id == "A3")
   115	    assert a3.verdict == "PASS"
   116	
   117	
   118	def test_a3_hazard_when_final_residual_above_floor(tmp_path: Path) -> None:
   119	    content = (
   120	        "smoothSolver:  Solving for Ux, Initial residual = 0.05, "
   121	        "Final residual = 0.001, No Iterations 20\n"
   122	    )
   123	    log = _write_log(tmp_path, content)
   124	    result = ca.attest(log)
   125	    a3 = next(c for c in result.checks if c.check_id == "A3")
   126	    assert a3.verdict == "HAZARD"
   127	    assert "Ux" in a3.evidence["offenders"]
   128	
   129	
   130	# ---------------------------------------------------------------------------
   131	# A4 solver_iteration_cap
   132	# ---------------------------------------------------------------------------
   133	
   134	def test_a4_fails_on_consecutive_cap_hits(tmp_path: Path) -> None:
   135	    """5 consecutive Time= blocks each with a capped GAMG p solve → FAIL.
   136	
   137	    Codex round-1 BLOCKER 2: measurement unit changed from consecutive
   138	    lines to consecutive TIME STEPS. Each `Time =` divider opens a new
   139	    block, so this test now needs Time= dividers.
   140	    """
   141	    content = "".join(
   142	        f"Time = {i}\nGAMG:  Solving for p, Initial residual = 0.9, "
   143	        "Final residual = 0.5, No Iterations 1000\n"
   144	        for i in range(5)
   145	    )
   146	    log = _write_log(tmp_path, content)
   147	    result = ca.attest(log)
   148	    a4 = next(c for c in result.checks if c.check_id == "A4")
   149	    assert a4.verdict == "FAIL"
   150	    assert a4.evidence["consecutive_cap_blocks"] >= 3
   151	
   152	
   153	def test_a4_fails_on_p_rgh_buoyant_log(tmp_path: Path) -> None:
   154	    """Codex DEC-038 round-1 BLOCKER 1: impinging_jet stuck solver is
   155	    `GAMG: Solving for p_rgh` in log.buoyantFoam — A4 regex must match
   156	    p_rgh (not just `p,`) to catch the real impinging_jet case.
   157	    """
   158	    content = "\n".join(
   159	        [f"Time = {i}s\nGAMG:  Solving for p_rgh, Initial residual = 0.7, "
   160	         "Final residual = 0.5, No Iterations 1000"
   161	         for i in range(5)]
   162	    )
   163	    log = _write_log(tmp_path, content)
   164	    result = ca.attest(log)
   165	    a4 = next(c for c in result.checks if c.check_id == "A4")
   166	    assert a4.verdict == "FAIL", f"got {a4.verdict}: {a4.summary}"
   167	
   168	
   169	def test_a4_fails_on_dicpcg_p_rgh(tmp_path: Path) -> None:
   170	    """DHC uses DICPCG: Solving for p_rgh. Same regex coverage requirement."""
   171	    content = "\n".join(
   172	        [f"Time = {i*0.5}s\nDICPCG:  Solving for p_rgh, Initial residual = 0.8, "
   173	         "Final residual = 0.6, No Iterations 1000"
   174	         for i in range(1, 6)]
   175	    )
   176	    log = _write_log(tmp_path, content)
   177	    result = ca.attest(log)
   178	    a4 = next(c for c in result.checks if c.check_id == "A4")
   179	    assert a4.verdict == "FAIL"
   180	
   181	
   182	def test_a4_multi_corrector_pimple_counts_blocks_not_lines(tmp_path: Path) -> None:
   183	    """Codex DEC-038 round-1 BLOCKER 2: PIMPLE emits multiple pressure
   184	    solves per Time= block. A4 must count BLOCKS, not LINES — 2 cap-hits
   185	    within the same block should count as 1 toward consecutive threshold,
   186	    not 2. Here 2 blocks × 2 cap-hits = 4 lines but only 2 blocks, so
   187	    consecutive=2 < 3 → PASS. A 3rd capped block is needed to FAIL.
   188	    """
   189	    # 2 capped blocks — should NOT fire (need 3 consecutive blocks).
   190	    content = (
   191	        "Time = 1s\n"
   192	        "GAMG:  Solving for p_rgh, Initial residual = 0.7, Final residual = 0.5, No Iterations 1000\n"
   193	        "GAMG:  Solving for p_rgh, Initial residual = 0.7, Final residual = 0.5, No Iterations 1000\n"
   194	        "Time = 2s\n"
   195	        "GAMG:  Solving for p_rgh, Initial residual = 0.7, Final residual = 0.5, No Iterations 1000\n"
   196	        "GAMG:  Solving for p_rgh, Initial residual = 0.7, Final residual = 0.5, No Iterations 1000\n"
   197	    )
   198	    log = _write_log(tmp_path, content)
   199	    result = ca.attest(log)
   200	    a4 = next(c for c in result.checks if c.check_id == "A4")
   201	    assert a4.verdict == "PASS", f"2 blocks should not fire A4 (threshold=3); got {a4.verdict}"
   202	
   203	
   204	def test_a4_fires_after_three_consecutive_blocks(tmp_path: Path) -> None:
   205	    """3 consecutive capped blocks → FAIL, regardless of per-block count."""
   206	    content = "".join(
   207	        f"Time = {i}s\n"
   208	        "GAMG:  Solving for p_rgh, Initial residual = 0.7, Final residual = 0.5, No Iterations 1000\n"
   209	        "GAMG:  Solving for p_rgh, Initial residual = 0.7, Final residual = 0.5, No Iterations 1000\n"
   210	        for i in range(1, 4)
   211	    )
   212	    log = _write_log(tmp_path, content)
   213	    result = ca.attest(log)
   214	    a4 = next(c for c in result.checks if c.check_id == "A4")
   215	    assert a4.verdict == "FAIL"
   216	    assert a4.evidence["consecutive_cap_blocks"] == 3
   217	
   218	
   219	def test_attestor_not_applicable_when_log_missing(tmp_path: Path) -> None:
   220	    """Codex DEC-038 round-1 comment C: missing log → ATTEST_NOT_APPLICABLE,

 succeeded in 0ms:
     1	"""DEC-V61-036b tests: hard comparator gates G3 (velocity overflow),
     2	G4 (turbulence negativity), G5 (continuity divergence).
     3	
     4	Evidence sources:
     5	  * BFS audit log shows catastrophic blowup (sum_local=5.24e+18,
     6	    cumulative=-1434.64, k min=-6.41e+30). Synthetic logs in this file
     7	    reproduce those markers for deterministic unit testing.
     8	  * LDC audit log shows clean convergence (sum_local ≈ 1e-6, k laminar
     9	    skipped). Synthetic clean logs assert G3/G4/G5 all pass.
    10	"""
    11	
    12	from __future__ import annotations
    13	
    14	from pathlib import Path
    15	import sys
    16	from types import SimpleNamespace
    17	
    18	import pytest
    19	from fastapi.testclient import TestClient
    20	
    21	from src import comparator_gates as cg
    22	from src.comparator_gates import check_all_gates, read_final_velocity_max
    23	from ui.backend.main import app
    24	
    25	
    26	# ---------------------------------------------------------------------------
    27	# Shared synthetic log fixtures
    28	# ---------------------------------------------------------------------------
    29	
    30	_CLEAN_LDC_LOG = """\
    31	Time = 500
    32	
    33	DICPCG:  Solving for p, Initial residual = 1e-08, Final residual = 1e-09, No Iterations 2
    34	time step continuity errors : sum local = 4.5e-08, global = -1.2e-09, cumulative = 3.1e-08
    35	ExecutionTime = 12.3 s  ClockTime = 14 s
    36	
    37	End
    38	"""
    39	
    40	_BFS_BLOWUP_TAIL = """\
    41	Time = 50
    42	
    43	smoothSolver:  Solving for Ux, Initial residual = 0.9, Final residual = 0.6, No Iterations 12
    44	smoothSolver:  Solving for Uy, Initial residual = 0.8, Final residual = 0.5, No Iterations 12
    45	GAMG:  Solving for p, Initial residual = 0.99, Final residual = 0.9, No Iterations 25
    46	time step continuity errors : sum local = 5.24523e+18, global = -1328.63, cumulative = -1434.64
    47	smoothSolver:  Solving for epsilon, Initial residual = 0.8, Final residual = 0.4, No Iterations 3
    48	bounding epsilon, min: 7.38706e-17 max: 1.03929e+30 average: 1.37234e+27
    49	smoothSolver:  Solving for k, Initial residual = 0.7, Final residual = 0.4, No Iterations 4
    50	bounding k, min: -6.41351e+30 max: 2.32895e+31 average: 1.39855e+29
    51	ExecutionTime = 0.6 s  ClockTime = 0 s
    52	"""
    53	
    54	
    55	def _write_log(tmp_path: Path, content: str) -> Path:
    56	    p = tmp_path / "log.simpleFoam"
    57	    p.write_text(content, encoding="utf-8")
    58	    return p
    59	
    60	
    61	class _FakeMesh:
    62	    def __init__(self, *, point_data: dict | None = None, cell_data: dict | None = None) -> None:
    63	        self.point_data = point_data or {}
    64	        self.cell_data = cell_data or {}
    65	
    66	
    67	def _write_vtk_stub(path: Path) -> Path:
    68	    path.parent.mkdir(parents=True, exist_ok=True)
    69	    path.write_text("stub", encoding="utf-8")
    70	    return path
    71	
    72	
    73	def _install_fake_pyvista(monkeypatch: pytest.MonkeyPatch, meshes_by_name: dict[str, _FakeMesh]) -> list[str]:
    74	    reads: list[str] = []
    75	
    76	    def fake_read(path_str: str) -> _FakeMesh:
    77	        name = Path(path_str).name
    78	        reads.append(name)
    79	        return meshes_by_name[name]
    80	
    81	    monkeypatch.setitem(sys.modules, "pyvista", SimpleNamespace(read=fake_read))
    82	    return reads
    83	
    84	
    85	# ---------------------------------------------------------------------------
    86	# Log parsing
    87	# ---------------------------------------------------------------------------
    88	
    89	def test_parse_solver_log_extracts_continuity_and_bounding(tmp_path: Path) -> None:
    90	    log = _write_log(tmp_path, _BFS_BLOWUP_TAIL)
    91	    stats = cg.parse_solver_log(log)
    92	    assert stats.final_continuity_sum_local == pytest.approx(5.24523e18)
    93	    assert stats.final_continuity_cumulative == pytest.approx(-1434.64)
    94	    assert "k" in stats.bounding_last
    95	    assert stats.bounding_last["k"]["min"] == pytest.approx(-6.41351e30)
    96	    assert stats.bounding_last["epsilon"]["max"] == pytest.approx(1.03929e30)
    97	    assert stats.fatal_detected is False
    98	
    99	
   100	def test_parse_solver_log_detects_foam_fatal(tmp_path: Path) -> None:
   101	    content = _CLEAN_LDC_LOG + "\nFOAM FATAL IO ERROR: missing dictionary key\n"
   102	    log = _write_log(tmp_path, content)
   103	    stats = cg.parse_solver_log(log)
   104	    assert stats.fatal_detected is True
   105	
   106	
   107	# ---------------------------------------------------------------------------
   108	# G5 — continuity divergence
   109	# ---------------------------------------------------------------------------
   110	
   111	def test_g5_fails_on_sum_local_overflow(tmp_path: Path) -> None:
   112	    log = _write_log(tmp_path, _BFS_BLOWUP_TAIL)
   113	    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
   114	    g5 = [v for v in violations if v.gate_id == "G5"]
   115	    assert len(g5) == 1
   116	    assert g5[0].concern_type == "CONTINUITY_DIVERGED"
   117	    assert g5[0].evidence["sum_local"] == pytest.approx(5.24523e18)
   118	
   119	
   120	def test_g5_fails_on_cumulative_only(tmp_path: Path) -> None:
   121	    # sum_local within threshold, cumulative huge — second branch.
   122	    content = (
   123	        "time step continuity errors : "
   124	        "sum local = 1e-04, global = 0.001, cumulative = 2.5\n"
   125	    )
   126	    log = _write_log(tmp_path, content)
   127	    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
   128	    g5 = [v for v in violations if v.gate_id == "G5"]
   129	    assert len(g5) == 1
   130	    assert g5[0].evidence["cumulative"] == pytest.approx(2.5)
   131	
   132	
   133	def test_g5_passes_on_clean_ldc_log(tmp_path: Path) -> None:
   134	    log = _write_log(tmp_path, _CLEAN_LDC_LOG)
   135	    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
   136	    g5 = [v for v in violations if v.gate_id == "G5"]
   137	    assert g5 == []
   138	
   139	
   140	# ---------------------------------------------------------------------------
   141	# G4 — turbulence negativity
   142	# ---------------------------------------------------------------------------
   143	
   144	def test_g4_fails_on_negative_k_at_last_iter(tmp_path: Path) -> None:
   145	    log = _write_log(tmp_path, _BFS_BLOWUP_TAIL)
   146	    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
   147	    g4 = [v for v in violations if v.gate_id == "G4"]
   148	    # BFS log shows k min=-6.4e30 AND epsilon max=1.03e30 — both fire G4
   149	    # (negative branch for k, overflow branch for epsilon).
   150	    concern_fields = {v.evidence["field"] for v in g4}
   151	    assert "k" in concern_fields
   152	    assert any(v.evidence.get("min", 1.0) < 0 for v in g4)
   153	
   154	
   155	def test_g4_fails_on_epsilon_overflow_without_negative(tmp_path: Path) -> None:
   156	    content = (
   157	        "bounding epsilon, min: 1e-5 max: 1e+30 average: 1e+26\n"
   158	        "bounding k, min: 1e-6 max: 0.5 average: 0.01\n"
   159	    )
   160	    log = _write_log(tmp_path, content)
   161	    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
   162	    g4 = [v for v in violations if v.gate_id == "G4"]
   163	    assert len(g4) == 1
   164	    assert g4[0].evidence["field"] == "epsilon"
   165	    assert g4[0].evidence["max"] == pytest.approx(1e30)
   166	
   167	
   168	def test_g4_passes_on_clean_ldc_log(tmp_path: Path) -> None:
   169	    # LDC is laminar — no bounding lines emitted. G4 should return no violations.
   170	    log = _write_log(tmp_path, _CLEAN_LDC_LOG)
   171	    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
   172	    g4 = [v for v in violations if v.gate_id == "G4"]
   173	    assert g4 == []
   174	
   175	
   176	# ---------------------------------------------------------------------------
   177	# G3 — velocity overflow (log-proxy branch; VTK branch gated by pyvista)
   178	# ---------------------------------------------------------------------------
   179	
   180	def test_g3_proxy_fails_on_epsilon_overflow(tmp_path: Path) -> None:
   181	    log = _write_log(tmp_path, _BFS_BLOWUP_TAIL)
   182	    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
   183	    g3 = [v for v in violations if v.gate_id == "G3"]
   184	    assert len(g3) == 1
   185	    assert g3[0].concern_type == "VELOCITY_OVERFLOW"
   186	    # BFS epsilon max=1.03e30 → inferred u ~ (1e30)^(1/3) = 1e10
   187	    assert g3[0].evidence["epsilon_max"] == pytest.approx(1.03929e30)
   188	
   189	
   190	def test_g3_passes_on_clean_ldc_log(tmp_path: Path) -> None:
   191	    log = _write_log(tmp_path, _CLEAN_LDC_LOG)
   192	    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
   193	    g3 = [v for v in violations if v.gate_id == "G3"]
   194	    assert g3 == []
   195	
   196	
   197	def test_read_final_velocity_max_skips_allPatches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
   198	    _write_vtk_stub(tmp_path / "case_100.vtk")
   199	    _write_vtk_stub(tmp_path / "allPatches" / "allPatches_100.vtk")
   200	    reads = _install_fake_pyvista(
   201	        monkeypatch,
   202	        {
   203	            "case_100.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
   204	            "allPatches_100.vtk": _FakeMesh(point_data={"U": [[999.0, 0.0, 0.0]]}),
   205	        },
   206	    )
   207	    assert read_final_velocity_max(tmp_path) == pytest.approx(2.0)
   208	    assert reads == ["case_100.vtk"]
   209	
   210	
   211	def test_read_final_velocity_max_uses_latest_timestep(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
   212	    for name in ("case_100.vtk", "case_200.vtk", "case_500.vtk"):
   213	        _write_vtk_stub(tmp_path / name)
   214	    reads = _install_fake_pyvista(
   215	        monkeypatch,
   216	        {
   217	            "case_100.vtk": _FakeMesh(point_data={"U": [[999.0, 0.0, 0.0]]}),
   218	            "case_200.vtk": _FakeMesh(point_data={"U": [[1.0, 0.0, 0.0]]}),
   219	            "case_500.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
   220	        },
   221	    )
   222	    assert read_final_velocity_max(tmp_path) == pytest.approx(2.0)
   223	    assert reads == ["case_500.vtk"]
   224	
   225	
   226	def test_read_final_velocity_max_allPatches_only_returns_none(tmp_path: Path) -> None:
   227	    _write_vtk_stub(tmp_path / "allPatches" / "allPatches_500.vtk")
   228	    assert read_final_velocity_max(tmp_path) is None
   229	
   230	
   231	def test_read_final_velocity_max_numeric_vs_alphabetic_sort(
   232	    tmp_path: Path,
   233	    monkeypatch: pytest.MonkeyPatch,
   234	) -> None:
   235	    for name in ("case_10.vtk", "case_100.vtk", "case_2.vtk"):
   236	        _write_vtk_stub(tmp_path / name)
   237	    reads = _install_fake_pyvista(
   238	        monkeypatch,
   239	        {
   240	            "case_10.vtk": _FakeMesh(point_data={"U": [[10.0, 0.0, 0.0]]}),
   241	            "case_100.vtk": _FakeMesh(point_data={"U": [[100.0, 0.0, 0.0]]}),
   242	            "case_2.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
   243	        },
   244	    )
   245	    assert read_final_velocity_max(tmp_path) == pytest.approx(100.0)
   246	    assert reads == ["case_100.vtk"]
   247	
   248	
   249	def test_read_final_velocity_max_no_timestep_suffix_skipped(tmp_path: Path) -> None:
   250	    _write_vtk_stub(tmp_path / "bare_case.vtk")
   251	    assert read_final_velocity_max(tmp_path) is None
   252	
   253	
   254	def test_g3_boundary_99_U_ref_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
   255	    monkeypatch.setattr(cg, "read_final_velocity_max", lambda _: 99.0)
   256	    violations = check_all_gates(log_path=None, vtk_dir=tmp_path, U_ref=1.0)
   257	    assert [v for v in violations if v.gate_id == "G3"] == []
   258	
   259	
   260	def test_g3_boundary_101_U_ref_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
   261	    monkeypatch.setattr(cg, "read_final_velocity_max", lambda _: 101.0)
   262	    violations = check_all_gates(log_path=None, vtk_dir=tmp_path, U_ref=1.0)
   263	    g3 = [v for v in violations if v.gate_id == "G3"]
   264	    assert len(g3) == 1
   265	    assert g3[0].evidence["u_max"] == pytest.approx(101.0)
   266	
   267	
   268	@pytest.mark.skip(reason="Wave 2 scope")
   269	def test_g3_u_ref_none_behavior() -> None:
   270	    pass
   271	
   272	
   273	# ---------------------------------------------------------------------------
   274	# NaN/Inf safety (Codex DEC-036b round-1 nit)
   275	# ---------------------------------------------------------------------------
   276	
   277	def test_g5_fires_on_nan_sum_local(tmp_path: Path) -> None:
   278	    """OpenFOAM overflowed → prints `nan` for continuity; gate must fire."""
   279	    content = (
   280	        "time step continuity errors : "

exec
/bin/zsh -lc 'env PYTHONPYCACHEPREFIX=/tmp/codex_pycache python3 -m py_compile ui/backend/tests/test_convergence_attestor.py ui/backend/tests/test_comparator_gates_g3_g4_g5.py' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
diff --git a/ui/backend/tests/test_comparator_gates_g3_g4_g5.py b/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
index 09b3735d6c46c89142e04c3196200f1ffd8001e2..f842f208509e372ebc3dbb92b3f59a87aa635c7e
--- a/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
+++ b/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
@@ -12,11 +12,14 @@
 from __future__ import annotations
 
 from pathlib import Path
+import sys
+from types import SimpleNamespace
 
 import pytest
 from fastapi.testclient import TestClient
 
 from src import comparator_gates as cg
+from src.comparator_gates import check_all_gates, read_final_velocity_max
 from ui.backend.main import app
 
 
@@ -55,6 +58,30 @@
     return p
 
 
+class _FakeMesh:
+    def __init__(self, *, point_data: dict | None = None, cell_data: dict | None = None) -> None:
+        self.point_data = point_data or {}
+        self.cell_data = cell_data or {}
+
+
+def _write_vtk_stub(path: Path) -> Path:
+    path.parent.mkdir(parents=True, exist_ok=True)
+    path.write_text("stub", encoding="utf-8")
+    return path
+
+
+def _install_fake_pyvista(monkeypatch: pytest.MonkeyPatch, meshes_by_name: dict[str, _FakeMesh]) -> list[str]:
+    reads: list[str] = []
+
+    def fake_read(path_str: str) -> _FakeMesh:
+        name = Path(path_str).name
+        reads.append(name)
+        return meshes_by_name[name]
+
+    monkeypatch.setitem(sys.modules, "pyvista", SimpleNamespace(read=fake_read))
+    return reads
+
+
 # ---------------------------------------------------------------------------
 # Log parsing
 # ---------------------------------------------------------------------------
@@ -167,6 +194,82 @@
     assert g3 == []
 
 
+def test_read_final_velocity_max_skips_allPatches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    _write_vtk_stub(tmp_path / "case_100.vtk")
+    _write_vtk_stub(tmp_path / "allPatches" / "allPatches_100.vtk")
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_100.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+            "allPatches_100.vtk": _FakeMesh(point_data={"U": [[999.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(2.0)
+    assert reads == ["case_100.vtk"]
+
+
+def test_read_final_velocity_max_uses_latest_timestep(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    for name in ("case_100.vtk", "case_200.vtk", "case_500.vtk"):
+        _write_vtk_stub(tmp_path / name)
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_100.vtk": _FakeMesh(point_data={"U": [[999.0, 0.0, 0.0]]}),
+            "case_200.vtk": _FakeMesh(point_data={"U": [[1.0, 0.0, 0.0]]}),
+            "case_500.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(2.0)
+    assert reads == ["case_500.vtk"]
+
+
+def test_read_final_velocity_max_allPatches_only_returns_none(tmp_path: Path) -> None:
+    _write_vtk_stub(tmp_path / "allPatches" / "allPatches_500.vtk")
+    assert read_final_velocity_max(tmp_path) is None
+
+
+def test_read_final_velocity_max_numeric_vs_alphabetic_sort(
+    tmp_path: Path,
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    for name in ("case_10.vtk", "case_100.vtk", "case_2.vtk"):
+        _write_vtk_stub(tmp_path / name)
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_10.vtk": _FakeMesh(point_data={"U": [[10.0, 0.0, 0.0]]}),
+            "case_100.vtk": _FakeMesh(point_data={"U": [[100.0, 0.0, 0.0]]}),
+            "case_2.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(100.0)
+    assert reads == ["case_100.vtk"]
+
+
+def test_read_final_velocity_max_no_timestep_suffix_skipped(tmp_path: Path) -> None:
+    _write_vtk_stub(tmp_path / "bare_case.vtk")
+    assert read_final_velocity_max(tmp_path) is None
+
+
+def test_g3_boundary_99_U_ref_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    monkeypatch.setattr(cg, "read_final_velocity_max", lambda _: 99.0)
+    violations = check_all_gates(log_path=None, vtk_dir=tmp_path, U_ref=1.0)
+    assert [v for v in violations if v.gate_id == "G3"] == []
+
+
+def test_g3_boundary_101_U_ref_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    monkeypatch.setattr(cg, "read_final_velocity_max", lambda _: 101.0)
+    violations = check_all_gates(log_path=None, vtk_dir=tmp_path, U_ref=1.0)
+    g3 = [v for v in violations if v.gate_id == "G3"]
+    assert len(g3) == 1
+    assert g3[0].evidence["u_max"] == pytest.approx(101.0)
+
+
+@pytest.mark.skip(reason="Wave 2 scope")
+def test_g3_u_ref_none_behavior() -> None:
+    pass
+
+
 # ---------------------------------------------------------------------------
 # NaN/Inf safety (Codex DEC-036b round-1 nit)
 # ---------------------------------------------------------------------------
diff --git a/ui/backend/tests/test_convergence_attestor.py b/ui/backend/tests/test_convergence_attestor.py
index a02d5d774bfce941d32895e48f7f3ccc6946faad..59f031641ee8961adbf16dde3136e33ccf20cad5
--- a/ui/backend/tests/test_convergence_attestor.py
+++ b/ui/backend/tests/test_convergence_attestor.py
@@ -12,10 +12,12 @@
 from __future__ import annotations
 
 from pathlib import Path
+from types import SimpleNamespace
 
 import pytest
 
 from src import convergence_attestor as ca
+from src.convergence_attestor import Thresholds, load_thresholds
 
 
 def _write_log(tmp_path: Path, content: str) -> Path:
@@ -239,6 +241,44 @@
     assert a2.verdict == "HAZARD"  # was FAIL pre-fix
 
 
+def test_load_thresholds_defaults() -> None:
+    thresholds = load_thresholds()
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.continuity_floor == pytest.approx(1e-4)
+    assert thresholds.residual_floor == pytest.approx(1e-3)
+    assert thresholds.residual_floor_per_field["p_rgh"] == pytest.approx(1e-2)
+
+
+def test_load_thresholds_per_case_impinging_jet() -> None:
+    thresholds = load_thresholds("impinging_jet")
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.residual_floor_per_field["p_rgh"] == pytest.approx(5e-3)
+    assert thresholds.residual_floor_per_field["Ux"] == pytest.approx(1e-3)
+
+
+def test_load_thresholds_per_case_rayleigh_benard() -> None:
+    thresholds = load_thresholds("rayleigh_benard_convection")
+    assert thresholds.residual_floor_per_field["h"] == pytest.approx(2e-3)
+    assert thresholds.no_progress_decade_frac == pytest.approx(0.3)
+
+
+def test_load_thresholds_unknown_case_falls_back() -> None:
+    defaults = load_thresholds()
+    unknown = load_thresholds("nonexistent_xyz_12345")
+    assert unknown.continuity_floor == defaults.continuity_floor
+    assert unknown.residual_floor == defaults.residual_floor
+    assert unknown.residual_floor_per_field == defaults.residual_floor_per_field
+    assert unknown.no_progress_decade_frac == defaults.no_progress_decade_frac
+
+
+def test_load_thresholds_missing_yaml_uses_hardcoded(tmp_path: Path) -> None:
+    bad_path = tmp_path / "nonexistent.yaml"
+    thresholds = load_thresholds(yaml_path=bad_path)
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.continuity_floor == ca.A2_CONTINUITY_FLOOR
+    assert thresholds.residual_floor == ca.A3_RESIDUAL_FLOOR
+
+
 def test_a4_passes_on_sparse_cap_hits(tmp_path: Path) -> None:
     """Single-iteration cap is not pathological — solver typically hits
     high counts in transient but recovers."""
@@ -254,6 +294,51 @@
     assert a4.verdict == "PASS"
 
 
+def test_a1_exit_code_false_forces_fail(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=False, exit_code=139),
+    )
+    assert result.verdict == "FAIL"
+    assert result.evidence["exit_code"] == 139
+
+
+def test_a1_log_fatal_fires_even_with_success_exit(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nmiddle\nFloating exception\nEnd\n")
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=True, exit_code=0),
+    )
+    assert result.verdict == "FAIL"
+
+
+def test_a1_sigFpe_banner_not_false_positive(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "sigFpe : Enabling floating point exception trapping (FOAM_SIGFPE).\n"
+        "Time = 1\nEnd\n",
+    )
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=True, exit_code=0),
+    )
+    assert result.verdict == "PASS"
+
+
+def test_a3_per_field_threshold_impinging_jet_p_rgh(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "DILUPBiCGStab:  Solving for p_rgh, Initial residual = 6e-3, "
+        "Final residual = 1e-5, No Iterations 2\n",
+    )
+    impinging = ca._check_a3_residual_floor(log, thresholds=load_thresholds("impinging_jet"))
+    default = ca._check_a3_residual_floor(log, thresholds=load_thresholds())
+    assert impinging.verdict == "HAZARD"
+    assert impinging.evidence["thresholds_by_field"]["p_rgh"] == pytest.approx(5e-3)
+    assert default.verdict == "PASS"
+
+
 # ---------------------------------------------------------------------------
 # A5 bounding_recurrence
 # ---------------------------------------------------------------------------
@@ -320,6 +405,59 @@
     assert a6.verdict == "PASS"
 
 
+def test_a6_decade_range_exactly_1_fires_fail(tmp_path: Path) -> None:
+    lines = []
+    for i in range(50):
+        initial = "1.0" if i % 2 == 0 else "10.0"
+        lines.append(
+            f"smoothSolver:  Solving for Ux, Initial residual = {initial}, "
+            "Final residual = 0.5, No Iterations 2"
+        )
+    log = _write_log(tmp_path, "\n".join(lines) + "\n")
+    result = ca._check_a6_no_progress(log, thresholds=load_thresholds())
+    assert result.verdict == "HAZARD"
+    assert result.evidence["offenders"]["Ux"]["decades"] == pytest.approx(1.0)
+
+
+def test_a4_gap_blocks_reset_consecutive(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "Time = 1\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 2\n"
+        "smoothSolver:  Solving for Ux, Initial residual = 0.1, Final residual = 0.01, No Iterations 2\n"
+        "Time = 3\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 4\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n",
+    )
+    result = ca._check_a4_iteration_cap(log, thresholds=load_thresholds())
+    assert result.verdict == "PASS"
+
+
+def test_a4_three_consecutive_caps_fail(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "Time = 1\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 2\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 3\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n",
+    )
+    result = ca._check_a4_iteration_cap(log, thresholds=load_thresholds())
+    assert result.verdict == "FAIL"
+    assert result.evidence["consecutive_cap_blocks"] == 3
+
+
+def test_attest_with_execution_result_failure(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
+    result = ca.attest(log, execution_result=SimpleNamespace(success=False))
+    a1 = next(c for c in result.checks if c.check_id == "A1")
+    assert result.overall == "ATTEST_FAIL"
+    assert a1.verdict == "FAIL"
+
+
 # ---------------------------------------------------------------------------
 # Real-log integration tests (guarded by file presence)
 # ---------------------------------------------------------------------------

codex
我发现一个小偏差：`U_ref` 那个 skipped test 名字没完全按 invocation 里写的大小写。我修正成原名，同时给两个边界测试补一句说明，避免后续读到测试名和 verdict tier 对不上。
apply patch
patch: completed
/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_convergence_attestor.py
diff --git a/ui/backend/tests/test_comparator_gates_g3_g4_g5.py b/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
index 09b3735d6c46c89142e04c3196200f1ffd8001e2..f842f208509e372ebc3dbb92b3f59a87aa635c7e
--- a/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
+++ b/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
@@ -12,11 +12,14 @@
 from __future__ import annotations
 
 from pathlib import Path
+import sys
+from types import SimpleNamespace
 
 import pytest
 from fastapi.testclient import TestClient
 
 from src import comparator_gates as cg
+from src.comparator_gates import check_all_gates, read_final_velocity_max
 from ui.backend.main import app
 
 
@@ -55,6 +58,30 @@
     return p
 
 
+class _FakeMesh:
+    def __init__(self, *, point_data: dict | None = None, cell_data: dict | None = None) -> None:
+        self.point_data = point_data or {}
+        self.cell_data = cell_data or {}
+
+
+def _write_vtk_stub(path: Path) -> Path:
+    path.parent.mkdir(parents=True, exist_ok=True)
+    path.write_text("stub", encoding="utf-8")
+    return path
+
+
+def _install_fake_pyvista(monkeypatch: pytest.MonkeyPatch, meshes_by_name: dict[str, _FakeMesh]) -> list[str]:
+    reads: list[str] = []
+
+    def fake_read(path_str: str) -> _FakeMesh:
+        name = Path(path_str).name
+        reads.append(name)
+        return meshes_by_name[name]
+
+    monkeypatch.setitem(sys.modules, "pyvista", SimpleNamespace(read=fake_read))
+    return reads
+
+
 # ---------------------------------------------------------------------------
 # Log parsing
 # ---------------------------------------------------------------------------
@@ -167,6 +194,82 @@
     assert g3 == []
 
 
+def test_read_final_velocity_max_skips_allPatches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    _write_vtk_stub(tmp_path / "case_100.vtk")
+    _write_vtk_stub(tmp_path / "allPatches" / "allPatches_100.vtk")
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_100.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+            "allPatches_100.vtk": _FakeMesh(point_data={"U": [[999.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(2.0)
+    assert reads == ["case_100.vtk"]
+
+
+def test_read_final_velocity_max_uses_latest_timestep(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    for name in ("case_100.vtk", "case_200.vtk", "case_500.vtk"):
+        _write_vtk_stub(tmp_path / name)
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_100.vtk": _FakeMesh(point_data={"U": [[999.0, 0.0, 0.0]]}),
+            "case_200.vtk": _FakeMesh(point_data={"U": [[1.0, 0.0, 0.0]]}),
+            "case_500.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(2.0)
+    assert reads == ["case_500.vtk"]
+
+
+def test_read_final_velocity_max_allPatches_only_returns_none(tmp_path: Path) -> None:
+    _write_vtk_stub(tmp_path / "allPatches" / "allPatches_500.vtk")
+    assert read_final_velocity_max(tmp_path) is None
+
+
+def test_read_final_velocity_max_numeric_vs_alphabetic_sort(
+    tmp_path: Path,
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    for name in ("case_10.vtk", "case_100.vtk", "case_2.vtk"):
+        _write_vtk_stub(tmp_path / name)
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_10.vtk": _FakeMesh(point_data={"U": [[10.0, 0.0, 0.0]]}),
+            "case_100.vtk": _FakeMesh(point_data={"U": [[100.0, 0.0, 0.0]]}),
+            "case_2.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(100.0)
+    assert reads == ["case_100.vtk"]
+
+
+def test_read_final_velocity_max_no_timestep_suffix_skipped(tmp_path: Path) -> None:
+    _write_vtk_stub(tmp_path / "bare_case.vtk")
+    assert read_final_velocity_max(tmp_path) is None
+
+
+def test_g3_boundary_99_U_ref_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    monkeypatch.setattr(cg, "read_final_velocity_max", lambda _: 99.0)
+    violations = check_all_gates(log_path=None, vtk_dir=tmp_path, U_ref=1.0)
+    assert [v for v in violations if v.gate_id == "G3"] == []
+
+
+def test_g3_boundary_101_U_ref_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    monkeypatch.setattr(cg, "read_final_velocity_max", lambda _: 101.0)
+    violations = check_all_gates(log_path=None, vtk_dir=tmp_path, U_ref=1.0)
+    g3 = [v for v in violations if v.gate_id == "G3"]
+    assert len(g3) == 1
+    assert g3[0].evidence["u_max"] == pytest.approx(101.0)
+
+
+@pytest.mark.skip(reason="Wave 2 scope")
+def test_g3_u_ref_none_behavior() -> None:
+    pass
+
+
 # ---------------------------------------------------------------------------
 # NaN/Inf safety (Codex DEC-036b round-1 nit)
 # ---------------------------------------------------------------------------
diff --git a/ui/backend/tests/test_convergence_attestor.py b/ui/backend/tests/test_convergence_attestor.py
index a02d5d774bfce941d32895e48f7f3ccc6946faad..143fe368a994406fc6f8e64f880b0c9e8ad3afc8
--- a/ui/backend/tests/test_convergence_attestor.py
+++ b/ui/backend/tests/test_convergence_attestor.py
@@ -12,10 +12,12 @@
 from __future__ import annotations
 
 from pathlib import Path
+from types import SimpleNamespace
 
 import pytest
 
 from src import convergence_attestor as ca
+from src.convergence_attestor import Thresholds, load_thresholds
 
 
 def _write_log(tmp_path: Path, content: str) -> Path:
@@ -239,6 +241,44 @@
     assert a2.verdict == "HAZARD"  # was FAIL pre-fix
 
 
+def test_load_thresholds_defaults() -> None:
+    thresholds = load_thresholds()
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.continuity_floor == pytest.approx(1e-4)
+    assert thresholds.residual_floor == pytest.approx(1e-3)
+    assert thresholds.residual_floor_per_field["p_rgh"] == pytest.approx(1e-2)
+
+
+def test_load_thresholds_per_case_impinging_jet() -> None:
+    thresholds = load_thresholds("impinging_jet")
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.residual_floor_per_field["p_rgh"] == pytest.approx(5e-3)
+    assert thresholds.residual_floor_per_field["Ux"] == pytest.approx(1e-3)
+
+
+def test_load_thresholds_per_case_rayleigh_benard() -> None:
+    thresholds = load_thresholds("rayleigh_benard_convection")
+    assert thresholds.residual_floor_per_field["h"] == pytest.approx(2e-3)
+    assert thresholds.no_progress_decade_frac == pytest.approx(0.3)
+
+
+def test_load_thresholds_unknown_case_falls_back() -> None:
+    defaults = load_thresholds()
+    unknown = load_thresholds("nonexistent_xyz_12345")
+    assert unknown.continuity_floor == defaults.continuity_floor
+    assert unknown.residual_floor == defaults.residual_floor
+    assert unknown.residual_floor_per_field == defaults.residual_floor_per_field
+    assert unknown.no_progress_decade_frac == defaults.no_progress_decade_frac
+
+
+def test_load_thresholds_missing_yaml_uses_hardcoded(tmp_path: Path) -> None:
+    bad_path = tmp_path / "nonexistent.yaml"
+    thresholds = load_thresholds(yaml_path=bad_path)
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.continuity_floor == ca.A2_CONTINUITY_FLOOR
+    assert thresholds.residual_floor == ca.A3_RESIDUAL_FLOOR
+
+
 def test_a4_passes_on_sparse_cap_hits(tmp_path: Path) -> None:
     """Single-iteration cap is not pathological — solver typically hits
     high counts in transient but recovers."""
@@ -254,6 +294,52 @@
     assert a4.verdict == "PASS"
 
 
+def test_a1_exit_code_false_forces_fail(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=False, exit_code=139),
+    )
+    assert result.verdict == "FAIL"
+    assert result.evidence["exit_code"] == 139
+
+
+def test_a1_log_fatal_fires_even_with_success_exit(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nmiddle\nFloating exception\nEnd\n")
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=True, exit_code=0),
+    )
+    assert result.verdict == "FAIL"
+
+
+def test_a1_sigFpe_banner_not_false_positive(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "sigFpe : Enabling floating point exception trapping (FOAM_SIGFPE).\n"
+        "Time = 1\nEnd\n",
+    )
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=True, exit_code=0),
+    )
+    assert result.verdict == "PASS"
+
+
+def test_a3_per_field_threshold_impinging_jet_p_rgh(tmp_path: Path) -> None:
+    """Override guard: 6e-3 trips impinging_jet p_rgh (5e-3) but not YAML default (1e-2)."""
+    log = _write_log(
+        tmp_path,
+        "DILUPBiCGStab:  Solving for p_rgh, Initial residual = 6e-3, "
+        "Final residual = 1e-5, No Iterations 2\n",
+    )
+    impinging = ca._check_a3_residual_floor(log, thresholds=load_thresholds("impinging_jet"))
+    default = ca._check_a3_residual_floor(log, thresholds=load_thresholds())
+    assert impinging.verdict == "HAZARD"
+    assert impinging.evidence["thresholds_by_field"]["p_rgh"] == pytest.approx(5e-3)
+    assert default.verdict == "PASS"
+
+
 # ---------------------------------------------------------------------------
 # A5 bounding_recurrence
 # ---------------------------------------------------------------------------
@@ -320,6 +406,60 @@
     assert a6.verdict == "PASS"
 
 
+def test_a6_decade_range_exactly_1_fires_fail(tmp_path: Path) -> None:
+    """Boundary guard: exactly 1.0 decade must fire A6, which stays HAZARD-tier."""
+    lines = []
+    for i in range(50):
+        initial = "1.0" if i % 2 == 0 else "10.0"
+        lines.append(
+            f"smoothSolver:  Solving for Ux, Initial residual = {initial}, "
+            "Final residual = 0.5, No Iterations 2"
+        )
+    log = _write_log(tmp_path, "\n".join(lines) + "\n")
+    result = ca._check_a6_no_progress(log, thresholds=load_thresholds())
+    assert result.verdict == "HAZARD"
+    assert result.evidence["offenders"]["Ux"]["decades"] == pytest.approx(1.0)
+
+
+def test_a4_gap_blocks_reset_consecutive(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "Time = 1\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 2\n"
+        "smoothSolver:  Solving for Ux, Initial residual = 0.1, Final residual = 0.01, No Iterations 2\n"
+        "Time = 3\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 4\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n",
+    )
+    result = ca._check_a4_iteration_cap(log, thresholds=load_thresholds())
+    assert result.verdict == "PASS"
+
+
+def test_a4_three_consecutive_caps_fail(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "Time = 1\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 2\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 3\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n",
+    )
+    result = ca._check_a4_iteration_cap(log, thresholds=load_thresholds())
+    assert result.verdict == "FAIL"
+    assert result.evidence["consecutive_cap_blocks"] == 3
+
+
+def test_attest_with_execution_result_failure(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
+    result = ca.attest(log, execution_result=SimpleNamespace(success=False))
+    a1 = next(c for c in result.checks if c.check_id == "A1")
+    assert result.overall == "ATTEST_FAIL"
+    assert a1.verdict == "FAIL"
+
+
 # ---------------------------------------------------------------------------
 # Real-log integration tests (guarded by file presence)
 # ---------------------------------------------------------------------------

diff --git a/ui/backend/tests/test_comparator_gates_g3_g4_g5.py b/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
index 09b3735d6c46c89142e04c3196200f1ffd8001e2..f842f208509e372ebc3dbb92b3f59a87aa635c7e
--- a/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
+++ b/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
@@ -12,11 +12,14 @@
 from __future__ import annotations
 
 from pathlib import Path
+import sys
+from types import SimpleNamespace
 
 import pytest
 from fastapi.testclient import TestClient
 
 from src import comparator_gates as cg
+from src.comparator_gates import check_all_gates, read_final_velocity_max
 from ui.backend.main import app
 
 
@@ -55,6 +58,30 @@
     return p
 
 
+class _FakeMesh:
+    def __init__(self, *, point_data: dict | None = None, cell_data: dict | None = None) -> None:
+        self.point_data = point_data or {}
+        self.cell_data = cell_data or {}
+
+
+def _write_vtk_stub(path: Path) -> Path:
+    path.parent.mkdir(parents=True, exist_ok=True)
+    path.write_text("stub", encoding="utf-8")
+    return path
+
+
+def _install_fake_pyvista(monkeypatch: pytest.MonkeyPatch, meshes_by_name: dict[str, _FakeMesh]) -> list[str]:
+    reads: list[str] = []
+
+    def fake_read(path_str: str) -> _FakeMesh:
+        name = Path(path_str).name
+        reads.append(name)
+        return meshes_by_name[name]
+
+    monkeypatch.setitem(sys.modules, "pyvista", SimpleNamespace(read=fake_read))
+    return reads
+
+
 # ---------------------------------------------------------------------------
 # Log parsing
 # ---------------------------------------------------------------------------
@@ -167,6 +194,82 @@
     assert g3 == []
 
 
+def test_read_final_velocity_max_skips_allPatches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    _write_vtk_stub(tmp_path / "case_100.vtk")
+    _write_vtk_stub(tmp_path / "allPatches" / "allPatches_100.vtk")
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_100.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+            "allPatches_100.vtk": _FakeMesh(point_data={"U": [[999.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(2.0)
+    assert reads == ["case_100.vtk"]
+
+
+def test_read_final_velocity_max_uses_latest_timestep(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    for name in ("case_100.vtk", "case_200.vtk", "case_500.vtk"):
+        _write_vtk_stub(tmp_path / name)
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_100.vtk": _FakeMesh(point_data={"U": [[999.0, 0.0, 0.0]]}),
+            "case_200.vtk": _FakeMesh(point_data={"U": [[1.0, 0.0, 0.0]]}),
+            "case_500.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(2.0)
+    assert reads == ["case_500.vtk"]
+
+
+def test_read_final_velocity_max_allPatches_only_returns_none(tmp_path: Path) -> None:
+    _write_vtk_stub(tmp_path / "allPatches" / "allPatches_500.vtk")
+    assert read_final_velocity_max(tmp_path) is None
+
+
+def test_read_final_velocity_max_numeric_vs_alphabetic_sort(
+    tmp_path: Path,
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    for name in ("case_10.vtk", "case_100.vtk", "case_2.vtk"):
+        _write_vtk_stub(tmp_path / name)
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_10.vtk": _FakeMesh(point_data={"U": [[10.0, 0.0, 0.0]]}),
+            "case_100.vtk": _FakeMesh(point_data={"U": [[100.0, 0.0, 0.0]]}),
+            "case_2.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(100.0)
+    assert reads == ["case_100.vtk"]
+
+
+def test_read_final_velocity_max_no_timestep_suffix_skipped(tmp_path: Path) -> None:
+    _write_vtk_stub(tmp_path / "bare_case.vtk")
+    assert read_final_velocity_max(tmp_path) is None
+
+
+def test_g3_boundary_99_U_ref_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    monkeypatch.setattr(cg, "read_final_velocity_max", lambda _: 99.0)
+    violations = check_all_gates(log_path=None, vtk_dir=tmp_path, U_ref=1.0)
+    assert [v for v in violations if v.gate_id == "G3"] == []
+
+
+def test_g3_boundary_101_U_ref_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    monkeypatch.setattr(cg, "read_final_velocity_max", lambda _: 101.0)
+    violations = check_all_gates(log_path=None, vtk_dir=tmp_path, U_ref=1.0)
+    g3 = [v for v in violations if v.gate_id == "G3"]
+    assert len(g3) == 1
+    assert g3[0].evidence["u_max"] == pytest.approx(101.0)
+
+
+@pytest.mark.skip(reason="Wave 2 scope")
+def test_g3_u_ref_none_behavior() -> None:
+    pass
+
+
 # ---------------------------------------------------------------------------
 # NaN/Inf safety (Codex DEC-036b round-1 nit)
 # ---------------------------------------------------------------------------
diff --git a/ui/backend/tests/test_convergence_attestor.py b/ui/backend/tests/test_convergence_attestor.py
index a02d5d774bfce941d32895e48f7f3ccc6946faad..143fe368a994406fc6f8e64f880b0c9e8ad3afc8
--- a/ui/backend/tests/test_convergence_attestor.py
+++ b/ui/backend/tests/test_convergence_attestor.py
@@ -12,10 +12,12 @@
 from __future__ import annotations
 
 from pathlib import Path
+from types import SimpleNamespace
 
 import pytest
 
 from src import convergence_attestor as ca
+from src.convergence_attestor import Thresholds, load_thresholds
 
 
 def _write_log(tmp_path: Path, content: str) -> Path:
@@ -239,6 +241,44 @@
     assert a2.verdict == "HAZARD"  # was FAIL pre-fix
 
 
+def test_load_thresholds_defaults() -> None:
+    thresholds = load_thresholds()
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.continuity_floor == pytest.approx(1e-4)
+    assert thresholds.residual_floor == pytest.approx(1e-3)
+    assert thresholds.residual_floor_per_field["p_rgh"] == pytest.approx(1e-2)
+
+
+def test_load_thresholds_per_case_impinging_jet() -> None:
+    thresholds = load_thresholds("impinging_jet")
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.residual_floor_per_field["p_rgh"] == pytest.approx(5e-3)
+    assert thresholds.residual_floor_per_field["Ux"] == pytest.approx(1e-3)
+
+
+def test_load_thresholds_per_case_rayleigh_benard() -> None:
+    thresholds = load_thresholds("rayleigh_benard_convection")
+    assert thresholds.residual_floor_per_field["h"] == pytest.approx(2e-3)
+    assert thresholds.no_progress_decade_frac == pytest.approx(0.3)
+
+
+def test_load_thresholds_unknown_case_falls_back() -> None:
+    defaults = load_thresholds()
+    unknown = load_thresholds("nonexistent_xyz_12345")
+    assert unknown.continuity_floor == defaults.continuity_floor
+    assert unknown.residual_floor == defaults.residual_floor
+    assert unknown.residual_floor_per_field == defaults.residual_floor_per_field
+    assert unknown.no_progress_decade_frac == defaults.no_progress_decade_frac
+
+
+def test_load_thresholds_missing_yaml_uses_hardcoded(tmp_path: Path) -> None:
+    bad_path = tmp_path / "nonexistent.yaml"
+    thresholds = load_thresholds(yaml_path=bad_path)
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.continuity_floor == ca.A2_CONTINUITY_FLOOR
+    assert thresholds.residual_floor == ca.A3_RESIDUAL_FLOOR
+
+
 def test_a4_passes_on_sparse_cap_hits(tmp_path: Path) -> None:
     """Single-iteration cap is not pathological — solver typically hits
     high counts in transient but recovers."""
@@ -254,6 +294,52 @@
     assert a4.verdict == "PASS"
 
 
+def test_a1_exit_code_false_forces_fail(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=False, exit_code=139),
+    )
+    assert result.verdict == "FAIL"
+    assert result.evidence["exit_code"] == 139
+
+
+def test_a1_log_fatal_fires_even_with_success_exit(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nmiddle\nFloating exception\nEnd\n")
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=True, exit_code=0),
+    )
+    assert result.verdict == "FAIL"
+
+
+def test_a1_sigFpe_banner_not_false_positive(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "sigFpe : Enabling floating point exception trapping (FOAM_SIGFPE).\n"
+        "Time = 1\nEnd\n",
+    )
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=True, exit_code=0),
+    )
+    assert result.verdict == "PASS"
+
+
+def test_a3_per_field_threshold_impinging_jet_p_rgh(tmp_path: Path) -> None:
+    """Override guard: 6e-3 trips impinging_jet p_rgh (5e-3) but not YAML default (1e-2)."""
+    log = _write_log(
+        tmp_path,
+        "DILUPBiCGStab:  Solving for p_rgh, Initial residual = 6e-3, "
+        "Final residual = 1e-5, No Iterations 2\n",
+    )
+    impinging = ca._check_a3_residual_floor(log, thresholds=load_thresholds("impinging_jet"))
+    default = ca._check_a3_residual_floor(log, thresholds=load_thresholds())
+    assert impinging.verdict == "HAZARD"
+    assert impinging.evidence["thresholds_by_field"]["p_rgh"] == pytest.approx(5e-3)
+    assert default.verdict == "PASS"
+
+
 # ---------------------------------------------------------------------------
 # A5 bounding_recurrence
 # ---------------------------------------------------------------------------
@@ -320,6 +406,60 @@
     assert a6.verdict == "PASS"
 
 
+def test_a6_decade_range_exactly_1_fires_fail(tmp_path: Path) -> None:
+    """Boundary guard: exactly 1.0 decade must fire A6, which stays HAZARD-tier."""
+    lines = []
+    for i in range(50):
+        initial = "1.0" if i % 2 == 0 else "10.0"
+        lines.append(
+            f"smoothSolver:  Solving for Ux, Initial residual = {initial}, "
+            "Final residual = 0.5, No Iterations 2"
+        )
+    log = _write_log(tmp_path, "\n".join(lines) + "\n")
+    result = ca._check_a6_no_progress(log, thresholds=load_thresholds())
+    assert result.verdict == "HAZARD"
+    assert result.evidence["offenders"]["Ux"]["decades"] == pytest.approx(1.0)
+
+
+def test_a4_gap_blocks_reset_consecutive(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "Time = 1\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 2\n"
+        "smoothSolver:  Solving for Ux, Initial residual = 0.1, Final residual = 0.01, No Iterations 2\n"
+        "Time = 3\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 4\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n",
+    )
+    result = ca._check_a4_iteration_cap(log, thresholds=load_thresholds())
+    assert result.verdict == "PASS"
+
+
+def test_a4_three_consecutive_caps_fail(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "Time = 1\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 2\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 3\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n",
+    )
+    result = ca._check_a4_iteration_cap(log, thresholds=load_thresholds())
+    assert result.verdict == "FAIL"
+    assert result.evidence["consecutive_cap_blocks"] == 3
+
+
+def test_attest_with_execution_result_failure(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
+    result = ca.attest(log, execution_result=SimpleNamespace(success=False))
+    a1 = next(c for c in result.checks if c.check_id == "A1")
+    assert result.overall == "ATTEST_FAIL"
+    assert a1.verdict == "FAIL"
+
+
 # ---------------------------------------------------------------------------
 # Real-log integration tests (guarded by file presence)
 # ---------------------------------------------------------------------------

apply patch
patch: completed
/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
diff --git a/ui/backend/tests/test_comparator_gates_g3_g4_g5.py b/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
index 09b3735d6c46c89142e04c3196200f1ffd8001e2..51deab94d30d3bda4a7fb2df85320f8c02c6d0e8
--- a/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
+++ b/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
@@ -12,11 +12,14 @@
 from __future__ import annotations
 
 from pathlib import Path
+import sys
+from types import SimpleNamespace
 
 import pytest
 from fastapi.testclient import TestClient
 
 from src import comparator_gates as cg
+from src.comparator_gates import check_all_gates, read_final_velocity_max
 from ui.backend.main import app
 
 
@@ -55,6 +58,30 @@
     return p
 
 
+class _FakeMesh:
+    def __init__(self, *, point_data: dict | None = None, cell_data: dict | None = None) -> None:
+        self.point_data = point_data or {}
+        self.cell_data = cell_data or {}
+
+
+def _write_vtk_stub(path: Path) -> Path:
+    path.parent.mkdir(parents=True, exist_ok=True)
+    path.write_text("stub", encoding="utf-8")
+    return path
+
+
+def _install_fake_pyvista(monkeypatch: pytest.MonkeyPatch, meshes_by_name: dict[str, _FakeMesh]) -> list[str]:
+    reads: list[str] = []
+
+    def fake_read(path_str: str) -> _FakeMesh:
+        name = Path(path_str).name
+        reads.append(name)
+        return meshes_by_name[name]
+
+    monkeypatch.setitem(sys.modules, "pyvista", SimpleNamespace(read=fake_read))
+    return reads
+
+
 # ---------------------------------------------------------------------------
 # Log parsing
 # ---------------------------------------------------------------------------
@@ -167,6 +194,82 @@
     assert g3 == []
 
 
+def test_read_final_velocity_max_skips_allPatches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    _write_vtk_stub(tmp_path / "case_100.vtk")
+    _write_vtk_stub(tmp_path / "allPatches" / "allPatches_100.vtk")
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_100.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+            "allPatches_100.vtk": _FakeMesh(point_data={"U": [[999.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(2.0)
+    assert reads == ["case_100.vtk"]
+
+
+def test_read_final_velocity_max_uses_latest_timestep(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    for name in ("case_100.vtk", "case_200.vtk", "case_500.vtk"):
+        _write_vtk_stub(tmp_path / name)
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_100.vtk": _FakeMesh(point_data={"U": [[999.0, 0.0, 0.0]]}),
+            "case_200.vtk": _FakeMesh(point_data={"U": [[1.0, 0.0, 0.0]]}),
+            "case_500.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(2.0)
+    assert reads == ["case_500.vtk"]
+
+
+def test_read_final_velocity_max_allPatches_only_returns_none(tmp_path: Path) -> None:
+    _write_vtk_stub(tmp_path / "allPatches" / "allPatches_500.vtk")
+    assert read_final_velocity_max(tmp_path) is None
+
+
+def test_read_final_velocity_max_numeric_vs_alphabetic_sort(
+    tmp_path: Path,
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    for name in ("case_10.vtk", "case_100.vtk", "case_2.vtk"):
+        _write_vtk_stub(tmp_path / name)
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_10.vtk": _FakeMesh(point_data={"U": [[10.0, 0.0, 0.0]]}),
+            "case_100.vtk": _FakeMesh(point_data={"U": [[100.0, 0.0, 0.0]]}),
+            "case_2.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(100.0)
+    assert reads == ["case_100.vtk"]
+
+
+def test_read_final_velocity_max_no_timestep_suffix_skipped(tmp_path: Path) -> None:
+    _write_vtk_stub(tmp_path / "bare_case.vtk")
+    assert read_final_velocity_max(tmp_path) is None
+
+
+def test_g3_boundary_99_U_ref_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    monkeypatch.setattr(cg, "read_final_velocity_max", lambda _: 99.0)
+    violations = check_all_gates(log_path=None, vtk_dir=tmp_path, U_ref=1.0)
+    assert [v for v in violations if v.gate_id == "G3"] == []
+
+
+def test_g3_boundary_101_U_ref_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    monkeypatch.setattr(cg, "read_final_velocity_max", lambda _: 101.0)
+    violations = check_all_gates(log_path=None, vtk_dir=tmp_path, U_ref=1.0)
+    g3 = [v for v in violations if v.gate_id == "G3"]
+    assert len(g3) == 1
+    assert g3[0].evidence["u_max"] == pytest.approx(101.0)
+
+
+@pytest.mark.skip(reason="Wave 2 scope")
+def test_g3_U_ref_none_behavior() -> None:
+    pass
+
+
 # ---------------------------------------------------------------------------
 # NaN/Inf safety (Codex DEC-036b round-1 nit)
 # ---------------------------------------------------------------------------
diff --git a/ui/backend/tests/test_convergence_attestor.py b/ui/backend/tests/test_convergence_attestor.py
index a02d5d774bfce941d32895e48f7f3ccc6946faad..143fe368a994406fc6f8e64f880b0c9e8ad3afc8
--- a/ui/backend/tests/test_convergence_attestor.py
+++ b/ui/backend/tests/test_convergence_attestor.py
@@ -12,10 +12,12 @@
 from __future__ import annotations
 
 from pathlib import Path
+from types import SimpleNamespace
 
 import pytest
 
 from src import convergence_attestor as ca
+from src.convergence_attestor import Thresholds, load_thresholds
 
 
 def _write_log(tmp_path: Path, content: str) -> Path:
@@ -239,6 +241,44 @@
     assert a2.verdict == "HAZARD"  # was FAIL pre-fix
 
 
+def test_load_thresholds_defaults() -> None:
+    thresholds = load_thresholds()
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.continuity_floor == pytest.approx(1e-4)
+    assert thresholds.residual_floor == pytest.approx(1e-3)
+    assert thresholds.residual_floor_per_field["p_rgh"] == pytest.approx(1e-2)
+
+
+def test_load_thresholds_per_case_impinging_jet() -> None:
+    thresholds = load_thresholds("impinging_jet")
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.residual_floor_per_field["p_rgh"] == pytest.approx(5e-3)
+    assert thresholds.residual_floor_per_field["Ux"] == pytest.approx(1e-3)
+
+
+def test_load_thresholds_per_case_rayleigh_benard() -> None:
+    thresholds = load_thresholds("rayleigh_benard_convection")
+    assert thresholds.residual_floor_per_field["h"] == pytest.approx(2e-3)
+    assert thresholds.no_progress_decade_frac == pytest.approx(0.3)
+
+
+def test_load_thresholds_unknown_case_falls_back() -> None:
+    defaults = load_thresholds()
+    unknown = load_thresholds("nonexistent_xyz_12345")
+    assert unknown.continuity_floor == defaults.continuity_floor
+    assert unknown.residual_floor == defaults.residual_floor
+    assert unknown.residual_floor_per_field == defaults.residual_floor_per_field
+    assert unknown.no_progress_decade_frac == defaults.no_progress_decade_frac
+
+
+def test_load_thresholds_missing_yaml_uses_hardcoded(tmp_path: Path) -> None:
+    bad_path = tmp_path / "nonexistent.yaml"
+    thresholds = load_thresholds(yaml_path=bad_path)
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.continuity_floor == ca.A2_CONTINUITY_FLOOR
+    assert thresholds.residual_floor == ca.A3_RESIDUAL_FLOOR
+
+
 def test_a4_passes_on_sparse_cap_hits(tmp_path: Path) -> None:
     """Single-iteration cap is not pathological — solver typically hits
     high counts in transient but recovers."""
@@ -254,6 +294,52 @@
     assert a4.verdict == "PASS"
 
 
+def test_a1_exit_code_false_forces_fail(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=False, exit_code=139),
+    )
+    assert result.verdict == "FAIL"
+    assert result.evidence["exit_code"] == 139
+
+
+def test_a1_log_fatal_fires_even_with_success_exit(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nmiddle\nFloating exception\nEnd\n")
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=True, exit_code=0),
+    )
+    assert result.verdict == "FAIL"
+
+
+def test_a1_sigFpe_banner_not_false_positive(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "sigFpe : Enabling floating point exception trapping (FOAM_SIGFPE).\n"
+        "Time = 1\nEnd\n",
+    )
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=True, exit_code=0),
+    )
+    assert result.verdict == "PASS"
+
+
+def test_a3_per_field_threshold_impinging_jet_p_rgh(tmp_path: Path) -> None:
+    """Override guard: 6e-3 trips impinging_jet p_rgh (5e-3) but not YAML default (1e-2)."""
+    log = _write_log(
+        tmp_path,
+        "DILUPBiCGStab:  Solving for p_rgh, Initial residual = 6e-3, "
+        "Final residual = 1e-5, No Iterations 2\n",
+    )
+    impinging = ca._check_a3_residual_floor(log, thresholds=load_thresholds("impinging_jet"))
+    default = ca._check_a3_residual_floor(log, thresholds=load_thresholds())
+    assert impinging.verdict == "HAZARD"
+    assert impinging.evidence["thresholds_by_field"]["p_rgh"] == pytest.approx(5e-3)
+    assert default.verdict == "PASS"
+
+
 # ---------------------------------------------------------------------------
 # A5 bounding_recurrence
 # ---------------------------------------------------------------------------
@@ -320,6 +406,60 @@
     assert a6.verdict == "PASS"
 
 
+def test_a6_decade_range_exactly_1_fires_fail(tmp_path: Path) -> None:
+    """Boundary guard: exactly 1.0 decade must fire A6, which stays HAZARD-tier."""
+    lines = []
+    for i in range(50):
+        initial = "1.0" if i % 2 == 0 else "10.0"
+        lines.append(
+            f"smoothSolver:  Solving for Ux, Initial residual = {initial}, "
+            "Final residual = 0.5, No Iterations 2"
+        )
+    log = _write_log(tmp_path, "\n".join(lines) + "\n")
+    result = ca._check_a6_no_progress(log, thresholds=load_thresholds())
+    assert result.verdict == "HAZARD"
+    assert result.evidence["offenders"]["Ux"]["decades"] == pytest.approx(1.0)
+
+
+def test_a4_gap_blocks_reset_consecutive(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "Time = 1\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 2\n"
+        "smoothSolver:  Solving for Ux, Initial residual = 0.1, Final residual = 0.01, No Iterations 2\n"
+        "Time = 3\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 4\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n",
+    )
+    result = ca._check_a4_iteration_cap(log, thresholds=load_thresholds())
+    assert result.verdict == "PASS"
+
+
+def test_a4_three_consecutive_caps_fail(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "Time = 1\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 2\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 3\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n",
+    )
+    result = ca._check_a4_iteration_cap(log, thresholds=load_thresholds())
+    assert result.verdict == "FAIL"
+    assert result.evidence["consecutive_cap_blocks"] == 3
+
+
+def test_attest_with_execution_result_failure(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
+    result = ca.attest(log, execution_result=SimpleNamespace(success=False))
+    a1 = next(c for c in result.checks if c.check_id == "A1")
+    assert result.overall == "ATTEST_FAIL"
+    assert a1.verdict == "FAIL"
+
+
 # ---------------------------------------------------------------------------
 # Real-log integration tests (guarded by file presence)
 # ---------------------------------------------------------------------------

diff --git a/ui/backend/tests/test_comparator_gates_g3_g4_g5.py b/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
index 09b3735d6c46c89142e04c3196200f1ffd8001e2..51deab94d30d3bda4a7fb2df85320f8c02c6d0e8
--- a/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
+++ b/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
@@ -12,11 +12,14 @@
 from __future__ import annotations
 
 from pathlib import Path
+import sys
+from types import SimpleNamespace
 
 import pytest
 from fastapi.testclient import TestClient
 
 from src import comparator_gates as cg
+from src.comparator_gates import check_all_gates, read_final_velocity_max
 from ui.backend.main import app
 
 
@@ -55,6 +58,30 @@
     return p
 
 
+class _FakeMesh:
+    def __init__(self, *, point_data: dict | None = None, cell_data: dict | None = None) -> None:
+        self.point_data = point_data or {}
+        self.cell_data = cell_data or {}
+
+
+def _write_vtk_stub(path: Path) -> Path:
+    path.parent.mkdir(parents=True, exist_ok=True)
+    path.write_text("stub", encoding="utf-8")
+    return path
+
+
+def _install_fake_pyvista(monkeypatch: pytest.MonkeyPatch, meshes_by_name: dict[str, _FakeMesh]) -> list[str]:
+    reads: list[str] = []
+
+    def fake_read(path_str: str) -> _FakeMesh:
+        name = Path(path_str).name
+        reads.append(name)
+        return meshes_by_name[name]
+
+    monkeypatch.setitem(sys.modules, "pyvista", SimpleNamespace(read=fake_read))
+    return reads
+
+
 # ---------------------------------------------------------------------------
 # Log parsing
 # ---------------------------------------------------------------------------
@@ -167,6 +194,82 @@
     assert g3 == []
 
 
+def test_read_final_velocity_max_skips_allPatches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    _write_vtk_stub(tmp_path / "case_100.vtk")
+    _write_vtk_stub(tmp_path / "allPatches" / "allPatches_100.vtk")
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_100.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+            "allPatches_100.vtk": _FakeMesh(point_data={"U": [[999.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(2.0)
+    assert reads == ["case_100.vtk"]
+
+
+def test_read_final_velocity_max_uses_latest_timestep(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    for name in ("case_100.vtk", "case_200.vtk", "case_500.vtk"):
+        _write_vtk_stub(tmp_path / name)
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_100.vtk": _FakeMesh(point_data={"U": [[999.0, 0.0, 0.0]]}),
+            "case_200.vtk": _FakeMesh(point_data={"U": [[1.0, 0.0, 0.0]]}),
+            "case_500.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(2.0)
+    assert reads == ["case_500.vtk"]
+
+
+def test_read_final_velocity_max_allPatches_only_returns_none(tmp_path: Path) -> None:
+    _write_vtk_stub(tmp_path / "allPatches" / "allPatches_500.vtk")
+    assert read_final_velocity_max(tmp_path) is None
+
+
+def test_read_final_velocity_max_numeric_vs_alphabetic_sort(
+    tmp_path: Path,
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    for name in ("case_10.vtk", "case_100.vtk", "case_2.vtk"):
+        _write_vtk_stub(tmp_path / name)
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_10.vtk": _FakeMesh(point_data={"U": [[10.0, 0.0, 0.0]]}),
+            "case_100.vtk": _FakeMesh(point_data={"U": [[100.0, 0.0, 0.0]]}),
+            "case_2.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(100.0)
+    assert reads == ["case_100.vtk"]
+
+
+def test_read_final_velocity_max_no_timestep_suffix_skipped(tmp_path: Path) -> None:
+    _write_vtk_stub(tmp_path / "bare_case.vtk")
+    assert read_final_velocity_max(tmp_path) is None
+
+
+def test_g3_boundary_99_U_ref_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    monkeypatch.setattr(cg, "read_final_velocity_max", lambda _: 99.0)
+    violations = check_all_gates(log_path=None, vtk_dir=tmp_path, U_ref=1.0)
+    assert [v for v in violations if v.gate_id == "G3"] == []
+
+
+def test_g3_boundary_101_U_ref_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    monkeypatch.setattr(cg, "read_final_velocity_max", lambda _: 101.0)
+    violations = check_all_gates(log_path=None, vtk_dir=tmp_path, U_ref=1.0)
+    g3 = [v for v in violations if v.gate_id == "G3"]
+    assert len(g3) == 1
+    assert g3[0].evidence["u_max"] == pytest.approx(101.0)
+
+
+@pytest.mark.skip(reason="Wave 2 scope")
+def test_g3_U_ref_none_behavior() -> None:
+    pass
+
+
 # ---------------------------------------------------------------------------
 # NaN/Inf safety (Codex DEC-036b round-1 nit)
 # ---------------------------------------------------------------------------
diff --git a/ui/backend/tests/test_convergence_attestor.py b/ui/backend/tests/test_convergence_attestor.py
index a02d5d774bfce941d32895e48f7f3ccc6946faad..143fe368a994406fc6f8e64f880b0c9e8ad3afc8
--- a/ui/backend/tests/test_convergence_attestor.py
+++ b/ui/backend/tests/test_convergence_attestor.py
@@ -12,10 +12,12 @@
 from __future__ import annotations
 
 from pathlib import Path
+from types import SimpleNamespace
 
 import pytest
 
 from src import convergence_attestor as ca
+from src.convergence_attestor import Thresholds, load_thresholds
 
 
 def _write_log(tmp_path: Path, content: str) -> Path:
@@ -239,6 +241,44 @@
     assert a2.verdict == "HAZARD"  # was FAIL pre-fix
 
 
+def test_load_thresholds_defaults() -> None:
+    thresholds = load_thresholds()
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.continuity_floor == pytest.approx(1e-4)
+    assert thresholds.residual_floor == pytest.approx(1e-3)
+    assert thresholds.residual_floor_per_field["p_rgh"] == pytest.approx(1e-2)
+
+
+def test_load_thresholds_per_case_impinging_jet() -> None:
+    thresholds = load_thresholds("impinging_jet")
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.residual_floor_per_field["p_rgh"] == pytest.approx(5e-3)
+    assert thresholds.residual_floor_per_field["Ux"] == pytest.approx(1e-3)
+
+
+def test_load_thresholds_per_case_rayleigh_benard() -> None:
+    thresholds = load_thresholds("rayleigh_benard_convection")
+    assert thresholds.residual_floor_per_field["h"] == pytest.approx(2e-3)
+    assert thresholds.no_progress_decade_frac == pytest.approx(0.3)
+
+
+def test_load_thresholds_unknown_case_falls_back() -> None:
+    defaults = load_thresholds()
+    unknown = load_thresholds("nonexistent_xyz_12345")
+    assert unknown.continuity_floor == defaults.continuity_floor
+    assert unknown.residual_floor == defaults.residual_floor
+    assert unknown.residual_floor_per_field == defaults.residual_floor_per_field
+    assert unknown.no_progress_decade_frac == defaults.no_progress_decade_frac
+
+
+def test_load_thresholds_missing_yaml_uses_hardcoded(tmp_path: Path) -> None:
+    bad_path = tmp_path / "nonexistent.yaml"
+    thresholds = load_thresholds(yaml_path=bad_path)
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.continuity_floor == ca.A2_CONTINUITY_FLOOR
+    assert thresholds.residual_floor == ca.A3_RESIDUAL_FLOOR
+
+
 def test_a4_passes_on_sparse_cap_hits(tmp_path: Path) -> None:
     """Single-iteration cap is not pathological — solver typically hits
     high counts in transient but recovers."""
@@ -254,6 +294,52 @@
     assert a4.verdict == "PASS"
 
 
+def test_a1_exit_code_false_forces_fail(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=False, exit_code=139),
+    )
+    assert result.verdict == "FAIL"
+    assert result.evidence["exit_code"] == 139
+
+
+def test_a1_log_fatal_fires_even_with_success_exit(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nmiddle\nFloating exception\nEnd\n")
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=True, exit_code=0),
+    )
+    assert result.verdict == "FAIL"
+
+
+def test_a1_sigFpe_banner_not_false_positive(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "sigFpe : Enabling floating point exception trapping (FOAM_SIGFPE).\n"
+        "Time = 1\nEnd\n",
+    )
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=True, exit_code=0),
+    )
+    assert result.verdict == "PASS"
+
+
+def test_a3_per_field_threshold_impinging_jet_p_rgh(tmp_path: Path) -> None:
+    """Override guard: 6e-3 trips impinging_jet p_rgh (5e-3) but not YAML default (1e-2)."""
+    log = _write_log(
+        tmp_path,
+        "DILUPBiCGStab:  Solving for p_rgh, Initial residual = 6e-3, "
+        "Final residual = 1e-5, No Iterations 2\n",
+    )
+    impinging = ca._check_a3_residual_floor(log, thresholds=load_thresholds("impinging_jet"))
+    default = ca._check_a3_residual_floor(log, thresholds=load_thresholds())
+    assert impinging.verdict == "HAZARD"
+    assert impinging.evidence["thresholds_by_field"]["p_rgh"] == pytest.approx(5e-3)
+    assert default.verdict == "PASS"
+
+
 # ---------------------------------------------------------------------------
 # A5 bounding_recurrence
 # ---------------------------------------------------------------------------
@@ -320,6 +406,60 @@
     assert a6.verdict == "PASS"
 
 
+def test_a6_decade_range_exactly_1_fires_fail(tmp_path: Path) -> None:
+    """Boundary guard: exactly 1.0 decade must fire A6, which stays HAZARD-tier."""
+    lines = []
+    for i in range(50):
+        initial = "1.0" if i % 2 == 0 else "10.0"
+        lines.append(
+            f"smoothSolver:  Solving for Ux, Initial residual = {initial}, "
+            "Final residual = 0.5, No Iterations 2"
+        )
+    log = _write_log(tmp_path, "\n".join(lines) + "\n")
+    result = ca._check_a6_no_progress(log, thresholds=load_thresholds())
+    assert result.verdict == "HAZARD"
+    assert result.evidence["offenders"]["Ux"]["decades"] == pytest.approx(1.0)
+
+
+def test_a4_gap_blocks_reset_consecutive(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "Time = 1\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 2\n"
+        "smoothSolver:  Solving for Ux, Initial residual = 0.1, Final residual = 0.01, No Iterations 2\n"
+        "Time = 3\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 4\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n",
+    )
+    result = ca._check_a4_iteration_cap(log, thresholds=load_thresholds())
+    assert result.verdict == "PASS"
+
+
+def test_a4_three_consecutive_caps_fail(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "Time = 1\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 2\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 3\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n",
+    )
+    result = ca._check_a4_iteration_cap(log, thresholds=load_thresholds())
+    assert result.verdict == "FAIL"
+    assert result.evidence["consecutive_cap_blocks"] == 3
+
+
+def test_attest_with_execution_result_failure(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
+    result = ca.attest(log, execution_result=SimpleNamespace(success=False))
+    a1 = next(c for c in result.checks if c.check_id == "A1")
+    assert result.overall == "ATTEST_FAIL"
+    assert a1.verdict == "FAIL"
+
+
 # ---------------------------------------------------------------------------
 # Real-log integration tests (guarded by file presence)
 # ---------------------------------------------------------------------------

exec
/bin/zsh -lc 'rg -n "test_a3_per_field_threshold_impinging_jet_p_rgh|test_a6_decade_range_exactly_1_fires_fail|test_g3_U_ref_none_behavior" ui/backend/tests/test_convergence_attestor.py ui/backend/tests/test_comparator_gates_g3_g4_g5.py' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
ui/backend/tests/test_convergence_attestor.py:329:def test_a3_per_field_threshold_impinging_jet_p_rgh(tmp_path: Path) -> None:
ui/backend/tests/test_convergence_attestor.py:409:def test_a6_decade_range_exactly_1_fires_fail(tmp_path: Path) -> None:
ui/backend/tests/test_comparator_gates_g3_g4_g5.py:269:def test_g3_U_ref_none_behavior() -> None:

exec
/bin/zsh -lc 'env PYTHONPYCACHEPREFIX=/tmp/codex_pycache python3 -m py_compile ui/backend/tests/test_convergence_attestor.py ui/backend/tests/test_comparator_gates_g3_g4_g5.py' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
exec
/bin/zsh -lc 'git diff --numstat -- ui/backend/tests/test_convergence_attestor.py ui/backend/tests/test_comparator_gates_g3_g4_g5.py' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
103	0	ui/backend/tests/test_comparator_gates_g3_g4_g5.py
140	0	ui/backend/tests/test_convergence_attestor.py

diff --git a/ui/backend/tests/test_comparator_gates_g3_g4_g5.py b/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
index 09b3735d6c46c89142e04c3196200f1ffd8001e2..51deab94d30d3bda4a7fb2df85320f8c02c6d0e8
--- a/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
+++ b/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
@@ -12,11 +12,14 @@
 from __future__ import annotations
 
 from pathlib import Path
+import sys
+from types import SimpleNamespace
 
 import pytest
 from fastapi.testclient import TestClient
 
 from src import comparator_gates as cg
+from src.comparator_gates import check_all_gates, read_final_velocity_max
 from ui.backend.main import app
 
 
@@ -55,6 +58,30 @@
     return p
 
 
+class _FakeMesh:
+    def __init__(self, *, point_data: dict | None = None, cell_data: dict | None = None) -> None:
+        self.point_data = point_data or {}
+        self.cell_data = cell_data or {}
+
+
+def _write_vtk_stub(path: Path) -> Path:
+    path.parent.mkdir(parents=True, exist_ok=True)
+    path.write_text("stub", encoding="utf-8")
+    return path
+
+
+def _install_fake_pyvista(monkeypatch: pytest.MonkeyPatch, meshes_by_name: dict[str, _FakeMesh]) -> list[str]:
+    reads: list[str] = []
+
+    def fake_read(path_str: str) -> _FakeMesh:
+        name = Path(path_str).name
+        reads.append(name)
+        return meshes_by_name[name]
+
+    monkeypatch.setitem(sys.modules, "pyvista", SimpleNamespace(read=fake_read))
+    return reads
+
+
 # ---------------------------------------------------------------------------
 # Log parsing
 # ---------------------------------------------------------------------------
@@ -167,6 +194,82 @@
     assert g3 == []
 
 
+def test_read_final_velocity_max_skips_allPatches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    _write_vtk_stub(tmp_path / "case_100.vtk")
+    _write_vtk_stub(tmp_path / "allPatches" / "allPatches_100.vtk")
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_100.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+            "allPatches_100.vtk": _FakeMesh(point_data={"U": [[999.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(2.0)
+    assert reads == ["case_100.vtk"]
+
+
+def test_read_final_velocity_max_uses_latest_timestep(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    for name in ("case_100.vtk", "case_200.vtk", "case_500.vtk"):
+        _write_vtk_stub(tmp_path / name)
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_100.vtk": _FakeMesh(point_data={"U": [[999.0, 0.0, 0.0]]}),
+            "case_200.vtk": _FakeMesh(point_data={"U": [[1.0, 0.0, 0.0]]}),
+            "case_500.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(2.0)
+    assert reads == ["case_500.vtk"]
+
+
+def test_read_final_velocity_max_allPatches_only_returns_none(tmp_path: Path) -> None:
+    _write_vtk_stub(tmp_path / "allPatches" / "allPatches_500.vtk")
+    assert read_final_velocity_max(tmp_path) is None
+
+
+def test_read_final_velocity_max_numeric_vs_alphabetic_sort(
+    tmp_path: Path,
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    for name in ("case_10.vtk", "case_100.vtk", "case_2.vtk"):
+        _write_vtk_stub(tmp_path / name)
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_10.vtk": _FakeMesh(point_data={"U": [[10.0, 0.0, 0.0]]}),
+            "case_100.vtk": _FakeMesh(point_data={"U": [[100.0, 0.0, 0.0]]}),
+            "case_2.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(100.0)
+    assert reads == ["case_100.vtk"]
+
+
+def test_read_final_velocity_max_no_timestep_suffix_skipped(tmp_path: Path) -> None:
+    _write_vtk_stub(tmp_path / "bare_case.vtk")
+    assert read_final_velocity_max(tmp_path) is None
+
+
+def test_g3_boundary_99_U_ref_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    monkeypatch.setattr(cg, "read_final_velocity_max", lambda _: 99.0)
+    violations = check_all_gates(log_path=None, vtk_dir=tmp_path, U_ref=1.0)
+    assert [v for v in violations if v.gate_id == "G3"] == []
+
+
+def test_g3_boundary_101_U_ref_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    monkeypatch.setattr(cg, "read_final_velocity_max", lambda _: 101.0)
+    violations = check_all_gates(log_path=None, vtk_dir=tmp_path, U_ref=1.0)
+    g3 = [v for v in violations if v.gate_id == "G3"]
+    assert len(g3) == 1
+    assert g3[0].evidence["u_max"] == pytest.approx(101.0)
+
+
+@pytest.mark.skip(reason="Wave 2 scope")
+def test_g3_U_ref_none_behavior() -> None:
+    pass
+
+
 # ---------------------------------------------------------------------------
 # NaN/Inf safety (Codex DEC-036b round-1 nit)
 # ---------------------------------------------------------------------------
diff --git a/ui/backend/tests/test_convergence_attestor.py b/ui/backend/tests/test_convergence_attestor.py
index a02d5d774bfce941d32895e48f7f3ccc6946faad..143fe368a994406fc6f8e64f880b0c9e8ad3afc8
--- a/ui/backend/tests/test_convergence_attestor.py
+++ b/ui/backend/tests/test_convergence_attestor.py
@@ -12,10 +12,12 @@
 from __future__ import annotations
 
 from pathlib import Path
+from types import SimpleNamespace
 
 import pytest
 
 from src import convergence_attestor as ca
+from src.convergence_attestor import Thresholds, load_thresholds
 
 
 def _write_log(tmp_path: Path, content: str) -> Path:
@@ -239,6 +241,44 @@
     assert a2.verdict == "HAZARD"  # was FAIL pre-fix
 
 
+def test_load_thresholds_defaults() -> None:
+    thresholds = load_thresholds()
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.continuity_floor == pytest.approx(1e-4)
+    assert thresholds.residual_floor == pytest.approx(1e-3)
+    assert thresholds.residual_floor_per_field["p_rgh"] == pytest.approx(1e-2)
+
+
+def test_load_thresholds_per_case_impinging_jet() -> None:
+    thresholds = load_thresholds("impinging_jet")
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.residual_floor_per_field["p_rgh"] == pytest.approx(5e-3)
+    assert thresholds.residual_floor_per_field["Ux"] == pytest.approx(1e-3)
+
+
+def test_load_thresholds_per_case_rayleigh_benard() -> None:
+    thresholds = load_thresholds("rayleigh_benard_convection")
+    assert thresholds.residual_floor_per_field["h"] == pytest.approx(2e-3)
+    assert thresholds.no_progress_decade_frac == pytest.approx(0.3)
+
+
+def test_load_thresholds_unknown_case_falls_back() -> None:
+    defaults = load_thresholds()
+    unknown = load_thresholds("nonexistent_xyz_12345")
+    assert unknown.continuity_floor == defaults.continuity_floor
+    assert unknown.residual_floor == defaults.residual_floor
+    assert unknown.residual_floor_per_field == defaults.residual_floor_per_field
+    assert unknown.no_progress_decade_frac == defaults.no_progress_decade_frac
+
+
+def test_load_thresholds_missing_yaml_uses_hardcoded(tmp_path: Path) -> None:
+    bad_path = tmp_path / "nonexistent.yaml"
+    thresholds = load_thresholds(yaml_path=bad_path)
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.continuity_floor == ca.A2_CONTINUITY_FLOOR
+    assert thresholds.residual_floor == ca.A3_RESIDUAL_FLOOR
+
+
 def test_a4_passes_on_sparse_cap_hits(tmp_path: Path) -> None:
     """Single-iteration cap is not pathological — solver typically hits
     high counts in transient but recovers."""
@@ -254,6 +294,52 @@
     assert a4.verdict == "PASS"
 
 
+def test_a1_exit_code_false_forces_fail(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=False, exit_code=139),
+    )
+    assert result.verdict == "FAIL"
+    assert result.evidence["exit_code"] == 139
+
+
+def test_a1_log_fatal_fires_even_with_success_exit(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nmiddle\nFloating exception\nEnd\n")
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=True, exit_code=0),
+    )
+    assert result.verdict == "FAIL"
+
+
+def test_a1_sigFpe_banner_not_false_positive(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "sigFpe : Enabling floating point exception trapping (FOAM_SIGFPE).\n"
+        "Time = 1\nEnd\n",
+    )
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=True, exit_code=0),
+    )
+    assert result.verdict == "PASS"
+
+
+def test_a3_per_field_threshold_impinging_jet_p_rgh(tmp_path: Path) -> None:
+    """Override guard: 6e-3 trips impinging_jet p_rgh (5e-3) but not YAML default (1e-2)."""
+    log = _write_log(
+        tmp_path,
+        "DILUPBiCGStab:  Solving for p_rgh, Initial residual = 6e-3, "
+        "Final residual = 1e-5, No Iterations 2\n",
+    )
+    impinging = ca._check_a3_residual_floor(log, thresholds=load_thresholds("impinging_jet"))
+    default = ca._check_a3_residual_floor(log, thresholds=load_thresholds())
+    assert impinging.verdict == "HAZARD"
+    assert impinging.evidence["thresholds_by_field"]["p_rgh"] == pytest.approx(5e-3)
+    assert default.verdict == "PASS"
+
+
 # ---------------------------------------------------------------------------
 # A5 bounding_recurrence
 # ---------------------------------------------------------------------------
@@ -320,6 +406,60 @@
     assert a6.verdict == "PASS"
 
 
+def test_a6_decade_range_exactly_1_fires_fail(tmp_path: Path) -> None:
+    """Boundary guard: exactly 1.0 decade must fire A6, which stays HAZARD-tier."""
+    lines = []
+    for i in range(50):
+        initial = "1.0" if i % 2 == 0 else "10.0"
+        lines.append(
+            f"smoothSolver:  Solving for Ux, Initial residual = {initial}, "
+            "Final residual = 0.5, No Iterations 2"
+        )
+    log = _write_log(tmp_path, "\n".join(lines) + "\n")
+    result = ca._check_a6_no_progress(log, thresholds=load_thresholds())
+    assert result.verdict == "HAZARD"
+    assert result.evidence["offenders"]["Ux"]["decades"] == pytest.approx(1.0)
+
+
+def test_a4_gap_blocks_reset_consecutive(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "Time = 1\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 2\n"
+        "smoothSolver:  Solving for Ux, Initial residual = 0.1, Final residual = 0.01, No Iterations 2\n"
+        "Time = 3\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 4\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n",
+    )
+    result = ca._check_a4_iteration_cap(log, thresholds=load_thresholds())
+    assert result.verdict == "PASS"
+
+
+def test_a4_three_consecutive_caps_fail(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "Time = 1\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 2\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 3\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n",
+    )
+    result = ca._check_a4_iteration_cap(log, thresholds=load_thresholds())
+    assert result.verdict == "FAIL"
+    assert result.evidence["consecutive_cap_blocks"] == 3
+
+
+def test_attest_with_execution_result_failure(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
+    result = ca.attest(log, execution_result=SimpleNamespace(success=False))
+    a1 = next(c for c in result.checks if c.check_id == "A1")
+    assert result.overall == "ATTEST_FAIL"
+    assert a1.verdict == "FAIL"
+
+
 # ---------------------------------------------------------------------------
 # Real-log integration tests (guarded by file presence)
 # ---------------------------------------------------------------------------

The two allowed test files are patched, syntax-checked with py_compile using a writable temp pycache prefix, and scoped review confirms no edits outside the allowed surface.
  ✓ Map requested Wave 1 A/B coverage onto current helper APIs and existing test structure
  ✓ Patch ui/backend/tests/test_convergence_attestor.py with the 13 requested attestor/YAML/A1/A3/A4/A6 tests
  ✓ Patch ui/backend/tests/test_comparator_gates_g3_g4_g5.py with the requested VTK-reader and G3 boundary tests
  → Self-check diffs against scope and prepare the required Codex Diff Report without claiming pytest passed
diff --git a/ui/backend/tests/test_comparator_gates_g3_g4_g5.py b/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
index 09b3735d6c46c89142e04c3196200f1ffd8001e2..51deab94d30d3bda4a7fb2df85320f8c02c6d0e8
--- a/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
+++ b/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
@@ -12,11 +12,14 @@
 from __future__ import annotations
 
 from pathlib import Path
+import sys
+from types import SimpleNamespace
 
 import pytest
 from fastapi.testclient import TestClient
 
 from src import comparator_gates as cg
+from src.comparator_gates import check_all_gates, read_final_velocity_max
 from ui.backend.main import app
 
 
@@ -55,6 +58,30 @@
     return p
 
 
+class _FakeMesh:
+    def __init__(self, *, point_data: dict | None = None, cell_data: dict | None = None) -> None:
+        self.point_data = point_data or {}
+        self.cell_data = cell_data or {}
+
+
+def _write_vtk_stub(path: Path) -> Path:
+    path.parent.mkdir(parents=True, exist_ok=True)
+    path.write_text("stub", encoding="utf-8")
+    return path
+
+
+def _install_fake_pyvista(monkeypatch: pytest.MonkeyPatch, meshes_by_name: dict[str, _FakeMesh]) -> list[str]:
+    reads: list[str] = []
+
+    def fake_read(path_str: str) -> _FakeMesh:
+        name = Path(path_str).name
+        reads.append(name)
+        return meshes_by_name[name]
+
+    monkeypatch.setitem(sys.modules, "pyvista", SimpleNamespace(read=fake_read))
+    return reads
+
+
 # ---------------------------------------------------------------------------
 # Log parsing
 # ---------------------------------------------------------------------------
@@ -167,6 +194,82 @@
     assert g3 == []
 
 
+def test_read_final_velocity_max_skips_allPatches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    _write_vtk_stub(tmp_path / "case_100.vtk")
+    _write_vtk_stub(tmp_path / "allPatches" / "allPatches_100.vtk")
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_100.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+            "allPatches_100.vtk": _FakeMesh(point_data={"U": [[999.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(2.0)
+    assert reads == ["case_100.vtk"]
+
+
+def test_read_final_velocity_max_uses_latest_timestep(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    for name in ("case_100.vtk", "case_200.vtk", "case_500.vtk"):
+        _write_vtk_stub(tmp_path / name)
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_100.vtk": _FakeMesh(point_data={"U": [[999.0, 0.0, 0.0]]}),
+            "case_200.vtk": _FakeMesh(point_data={"U": [[1.0, 0.0, 0.0]]}),
+            "case_500.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(2.0)
+    assert reads == ["case_500.vtk"]
+
+
+def test_read_final_velocity_max_allPatches_only_returns_none(tmp_path: Path) -> None:
+    _write_vtk_stub(tmp_path / "allPatches" / "allPatches_500.vtk")
+    assert read_final_velocity_max(tmp_path) is None
+
+
+def test_read_final_velocity_max_numeric_vs_alphabetic_sort(
+    tmp_path: Path,
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    for name in ("case_10.vtk", "case_100.vtk", "case_2.vtk"):
+        _write_vtk_stub(tmp_path / name)
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_10.vtk": _FakeMesh(point_data={"U": [[10.0, 0.0, 0.0]]}),
+            "case_100.vtk": _FakeMesh(point_data={"U": [[100.0, 0.0, 0.0]]}),
+            "case_2.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(100.0)
+    assert reads == ["case_100.vtk"]
+
+
+def test_read_final_velocity_max_no_timestep_suffix_skipped(tmp_path: Path) -> None:
+    _write_vtk_stub(tmp_path / "bare_case.vtk")
+    assert read_final_velocity_max(tmp_path) is None
+
+
+def test_g3_boundary_99_U_ref_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    monkeypatch.setattr(cg, "read_final_velocity_max", lambda _: 99.0)
+    violations = check_all_gates(log_path=None, vtk_dir=tmp_path, U_ref=1.0)
+    assert [v for v in violations if v.gate_id == "G3"] == []
+
+
+def test_g3_boundary_101_U_ref_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    monkeypatch.setattr(cg, "read_final_velocity_max", lambda _: 101.0)
+    violations = check_all_gates(log_path=None, vtk_dir=tmp_path, U_ref=1.0)
+    g3 = [v for v in violations if v.gate_id == "G3"]
+    assert len(g3) == 1
+    assert g3[0].evidence["u_max"] == pytest.approx(101.0)
+
+
+@pytest.mark.skip(reason="Wave 2 scope")
+def test_g3_U_ref_none_behavior() -> None:
+    pass
+
+
 # ---------------------------------------------------------------------------
 # NaN/Inf safety (Codex DEC-036b round-1 nit)
 # ---------------------------------------------------------------------------
diff --git a/ui/backend/tests/test_convergence_attestor.py b/ui/backend/tests/test_convergence_attestor.py
index a02d5d774bfce941d32895e48f7f3ccc6946faad..143fe368a994406fc6f8e64f880b0c9e8ad3afc8
--- a/ui/backend/tests/test_convergence_attestor.py
+++ b/ui/backend/tests/test_convergence_attestor.py
@@ -12,10 +12,12 @@
 from __future__ import annotations
 
 from pathlib import Path
+from types import SimpleNamespace
 
 import pytest
 
 from src import convergence_attestor as ca
+from src.convergence_attestor import Thresholds, load_thresholds
 
 
 def _write_log(tmp_path: Path, content: str) -> Path:
@@ -239,6 +241,44 @@
     assert a2.verdict == "HAZARD"  # was FAIL pre-fix
 
 
+def test_load_thresholds_defaults() -> None:
+    thresholds = load_thresholds()
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.continuity_floor == pytest.approx(1e-4)
+    assert thresholds.residual_floor == pytest.approx(1e-3)
+    assert thresholds.residual_floor_per_field["p_rgh"] == pytest.approx(1e-2)
+
+
+def test_load_thresholds_per_case_impinging_jet() -> None:
+    thresholds = load_thresholds("impinging_jet")
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.residual_floor_per_field["p_rgh"] == pytest.approx(5e-3)
+    assert thresholds.residual_floor_per_field["Ux"] == pytest.approx(1e-3)
+
+
+def test_load_thresholds_per_case_rayleigh_benard() -> None:
+    thresholds = load_thresholds("rayleigh_benard_convection")
+    assert thresholds.residual_floor_per_field["h"] == pytest.approx(2e-3)
+    assert thresholds.no_progress_decade_frac == pytest.approx(0.3)
+
+
+def test_load_thresholds_unknown_case_falls_back() -> None:
+    defaults = load_thresholds()
+    unknown = load_thresholds("nonexistent_xyz_12345")
+    assert unknown.continuity_floor == defaults.continuity_floor
+    assert unknown.residual_floor == defaults.residual_floor
+    assert unknown.residual_floor_per_field == defaults.residual_floor_per_field
+    assert unknown.no_progress_decade_frac == defaults.no_progress_decade_frac
+
+
+def test_load_thresholds_missing_yaml_uses_hardcoded(tmp_path: Path) -> None:
+    bad_path = tmp_path / "nonexistent.yaml"
+    thresholds = load_thresholds(yaml_path=bad_path)
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.continuity_floor == ca.A2_CONTINUITY_FLOOR
+    assert thresholds.residual_floor == ca.A3_RESIDUAL_FLOOR
+
+
 def test_a4_passes_on_sparse_cap_hits(tmp_path: Path) -> None:
     """Single-iteration cap is not pathological — solver typically hits
     high counts in transient but recovers."""
@@ -254,6 +294,52 @@
     assert a4.verdict == "PASS"
 
 
+def test_a1_exit_code_false_forces_fail(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=False, exit_code=139),
+    )
+    assert result.verdict == "FAIL"
+    assert result.evidence["exit_code"] == 139
+
+
+def test_a1_log_fatal_fires_even_with_success_exit(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nmiddle\nFloating exception\nEnd\n")
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=True, exit_code=0),
+    )
+    assert result.verdict == "FAIL"
+
+
+def test_a1_sigFpe_banner_not_false_positive(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "sigFpe : Enabling floating point exception trapping (FOAM_SIGFPE).\n"
+        "Time = 1\nEnd\n",
+    )
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=True, exit_code=0),
+    )
+    assert result.verdict == "PASS"
+
+
+def test_a3_per_field_threshold_impinging_jet_p_rgh(tmp_path: Path) -> None:
+    """Override guard: 6e-3 trips impinging_jet p_rgh (5e-3) but not YAML default (1e-2)."""
+    log = _write_log(
+        tmp_path,
+        "DILUPBiCGStab:  Solving for p_rgh, Initial residual = 6e-3, "
+        "Final residual = 1e-5, No Iterations 2\n",
+    )
+    impinging = ca._check_a3_residual_floor(log, thresholds=load_thresholds("impinging_jet"))
+    default = ca._check_a3_residual_floor(log, thresholds=load_thresholds())
+    assert impinging.verdict == "HAZARD"
+    assert impinging.evidence["thresholds_by_field"]["p_rgh"] == pytest.approx(5e-3)
+    assert default.verdict == "PASS"
+
+
 # ---------------------------------------------------------------------------
 # A5 bounding_recurrence
 # ---------------------------------------------------------------------------
@@ -320,6 +406,60 @@
     assert a6.verdict == "PASS"
 
 
+def test_a6_decade_range_exactly_1_fires_fail(tmp_path: Path) -> None:
+    """Boundary guard: exactly 1.0 decade must fire A6, which stays HAZARD-tier."""
+    lines = []
+    for i in range(50):
+        initial = "1.0" if i % 2 == 0 else "10.0"
+        lines.append(
+            f"smoothSolver:  Solving for Ux, Initial residual = {initial}, "
+            "Final residual = 0.5, No Iterations 2"
+        )
+    log = _write_log(tmp_path, "\n".join(lines) + "\n")
+    result = ca._check_a6_no_progress(log, thresholds=load_thresholds())
+    assert result.verdict == "HAZARD"
+    assert result.evidence["offenders"]["Ux"]["decades"] == pytest.approx(1.0)
+
+
+def test_a4_gap_blocks_reset_consecutive(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "Time = 1\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 2\n"
+        "smoothSolver:  Solving for Ux, Initial residual = 0.1, Final residual = 0.01, No Iterations 2\n"
+        "Time = 3\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 4\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n",
+    )
+    result = ca._check_a4_iteration_cap(log, thresholds=load_thresholds())
+    assert result.verdict == "PASS"
+
+
+def test_a4_three_consecutive_caps_fail(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "Time = 1\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 2\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 3\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n",
+    )
+    result = ca._check_a4_iteration_cap(log, thresholds=load_thresholds())
+    assert result.verdict == "FAIL"
+    assert result.evidence["consecutive_cap_blocks"] == 3
+
+
+def test_attest_with_execution_result_failure(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
+    result = ca.attest(log, execution_result=SimpleNamespace(success=False))
+    a1 = next(c for c in result.checks if c.check_id == "A1")
+    assert result.overall == "ATTEST_FAIL"
+    assert a1.verdict == "FAIL"
+
+
 # ---------------------------------------------------------------------------
 # Real-log integration tests (guarded by file presence)
 # ---------------------------------------------------------------------------

codex
# Codex Diff Report — DEC-V61-045 Wave 1 C

## Files modified
- `ui/backend/tests/test_convergence_attestor.py` [+140/-0]
- `ui/backend/tests/test_comparator_gates_g3_g4_g5.py` [+103/-0]

## Tests added (per file)
- `test_load_thresholds_defaults` — verifies YAML defaults load into `Thresholds`; covers CHK-1.
- `test_load_thresholds_per_case_impinging_jet` — verifies `impinging_jet` override for `p_rgh`; covers CHK-1.
- `test_load_thresholds_per_case_rayleigh_benard` — verifies `rayleigh_benard_convection` overrides `h` and `no_progress_decade_frac`; covers CHK-1.
- `test_load_thresholds_unknown_case_falls_back` — verifies unknown case uses default threshold values without error; covers CHK-1.
- `test_load_thresholds_missing_yaml_uses_hardcoded` — verifies missing YAML falls back to module constants; covers CHK-1.
- `test_a1_exit_code_false_forces_fail` — verifies `execution_result.success=False` forces A1 FAIL and preserves `exit_code`; covers CHK-1.
- `test_a1_log_fatal_fires_even_with_success_exit` — verifies log fatal markers still fail A1 with successful exit status; covers CHK-1.
- `test_a1_sigFpe_banner_not_false_positive` — regression guard for benign `sigFpe` startup banner; covers CHK-1.
- `test_a3_per_field_threshold_impinging_jet_p_rgh` — proves the `impinging_jet` `p_rgh=5e-3` override is applied against YAML default behavior; covers CHK-1.
- `test_a6_decade_range_exactly_1_fires_fail` — guards the `<= 1.0` A6 boundary; confirms the check fires at exactly one decade; covers CHK-1.
- `test_a4_gap_blocks_reset_consecutive` — guards `[cap, gap, cap, cap]` resetting the streak; covers CHK-1.
- `test_a4_three_consecutive_caps_fail` — guards three back-to-back capped blocks failing A4; covers CHK-1.
- `test_attest_with_execution_result_failure` — verifies `attest(..., execution_result=SimpleNamespace(success=False))` produces `ATTEST_FAIL`; covers CHK-1.
- `test_read_final_velocity_max_skips_allPatches` — verifies `allPatches` VTKs are ignored and only the internal file is read; covers CHK-1.
- `test_read_final_velocity_max_uses_latest_timestep` — verifies latest numeric timestep wins over earlier spikes; covers CHK-1.
- `test_read_final_velocity_max_allPatches_only_returns_none` — verifies boundary-only VTK trees return `None`; covers CHK-1.
- `test_read_final_velocity_max_numeric_vs_alphabetic_sort` — verifies numeric suffix ordering beats alphabetic ordering; covers CHK-1.
- `test_read_final_velocity_max_no_timestep_suffix_skipped` — verifies non-matching filenames are ignored; covers CHK-1.
- `test_g3_boundary_99_U_ref_passes` — verifies G3 stays quiet just below `100 * U_ref`; covers CHK-1.
- `test_g3_boundary_101_U_ref_fails` — verifies G3 fires just above `100 * U_ref`; covers CHK-1.
- `test_g3_U_ref_none_behavior` — explicit `Wave 2 scope` skip pin per invocation note; no CHK counted.

## Existing tests touched (if any)
- None.

## Self-verified checks
- CHK-1: NOT RUN. Per REJ-4, I did not execute `pytest ui/backend/tests/test_convergence_attestor.py ui/backend/tests/test_comparator_gates_g3_g4_g5.py -q`.
- CHK-2: PASS by diff inspection. No existing test bodies were edited; only imports, local helpers, and new `test_*` functions were added.
- CHK-3: PASS by diff inspection. No `conftest.py` changes and no shared fixture additions outside the two allowed files.
- Syntax check: PASS via `env PYTHONPYCACHEPREFIX=/tmp/codex_pycache python3 -m py_compile ui/backend/tests/test_convergence_attestor.py ui/backend/tests/test_comparator_gates_g3_g4_g5.py`.

## Tokens used
- Not exposed by this Codex runtime.


diff --git a/ui/backend/tests/test_comparator_gates_g3_g4_g5.py b/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
index 09b3735d6c46c89142e04c3196200f1ffd8001e2..51deab94d30d3bda4a7fb2df85320f8c02c6d0e8
--- a/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
+++ b/ui/backend/tests/test_comparator_gates_g3_g4_g5.py
@@ -12,11 +12,14 @@
 from __future__ import annotations
 
 from pathlib import Path
+import sys
+from types import SimpleNamespace
 
 import pytest
 from fastapi.testclient import TestClient
 
 from src import comparator_gates as cg
+from src.comparator_gates import check_all_gates, read_final_velocity_max
 from ui.backend.main import app
 
 
@@ -55,6 +58,30 @@
     return p
 
 
+class _FakeMesh:
+    def __init__(self, *, point_data: dict | None = None, cell_data: dict | None = None) -> None:
+        self.point_data = point_data or {}
+        self.cell_data = cell_data or {}
+
+
+def _write_vtk_stub(path: Path) -> Path:
+    path.parent.mkdir(parents=True, exist_ok=True)
+    path.write_text("stub", encoding="utf-8")
+    return path
+
+
+def _install_fake_pyvista(monkeypatch: pytest.MonkeyPatch, meshes_by_name: dict[str, _FakeMesh]) -> list[str]:
+    reads: list[str] = []
+
+    def fake_read(path_str: str) -> _FakeMesh:
+        name = Path(path_str).name
+        reads.append(name)
+        return meshes_by_name[name]
+
+    monkeypatch.setitem(sys.modules, "pyvista", SimpleNamespace(read=fake_read))
+    return reads
+
+
 # ---------------------------------------------------------------------------
 # Log parsing
 # ---------------------------------------------------------------------------
@@ -167,6 +194,82 @@
     assert g3 == []
 
 
+def test_read_final_velocity_max_skips_allPatches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    _write_vtk_stub(tmp_path / "case_100.vtk")
+    _write_vtk_stub(tmp_path / "allPatches" / "allPatches_100.vtk")
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_100.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+            "allPatches_100.vtk": _FakeMesh(point_data={"U": [[999.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(2.0)
+    assert reads == ["case_100.vtk"]
+
+
+def test_read_final_velocity_max_uses_latest_timestep(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    for name in ("case_100.vtk", "case_200.vtk", "case_500.vtk"):
+        _write_vtk_stub(tmp_path / name)
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_100.vtk": _FakeMesh(point_data={"U": [[999.0, 0.0, 0.0]]}),
+            "case_200.vtk": _FakeMesh(point_data={"U": [[1.0, 0.0, 0.0]]}),
+            "case_500.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(2.0)
+    assert reads == ["case_500.vtk"]
+
+
+def test_read_final_velocity_max_allPatches_only_returns_none(tmp_path: Path) -> None:
+    _write_vtk_stub(tmp_path / "allPatches" / "allPatches_500.vtk")
+    assert read_final_velocity_max(tmp_path) is None
+
+
+def test_read_final_velocity_max_numeric_vs_alphabetic_sort(
+    tmp_path: Path,
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    for name in ("case_10.vtk", "case_100.vtk", "case_2.vtk"):
+        _write_vtk_stub(tmp_path / name)
+    reads = _install_fake_pyvista(
+        monkeypatch,
+        {
+            "case_10.vtk": _FakeMesh(point_data={"U": [[10.0, 0.0, 0.0]]}),
+            "case_100.vtk": _FakeMesh(point_data={"U": [[100.0, 0.0, 0.0]]}),
+            "case_2.vtk": _FakeMesh(point_data={"U": [[2.0, 0.0, 0.0]]}),
+        },
+    )
+    assert read_final_velocity_max(tmp_path) == pytest.approx(100.0)
+    assert reads == ["case_100.vtk"]
+
+
+def test_read_final_velocity_max_no_timestep_suffix_skipped(tmp_path: Path) -> None:
+    _write_vtk_stub(tmp_path / "bare_case.vtk")
+    assert read_final_velocity_max(tmp_path) is None
+
+
+def test_g3_boundary_99_U_ref_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    monkeypatch.setattr(cg, "read_final_velocity_max", lambda _: 99.0)
+    violations = check_all_gates(log_path=None, vtk_dir=tmp_path, U_ref=1.0)
+    assert [v for v in violations if v.gate_id == "G3"] == []
+
+
+def test_g3_boundary_101_U_ref_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    monkeypatch.setattr(cg, "read_final_velocity_max", lambda _: 101.0)
+    violations = check_all_gates(log_path=None, vtk_dir=tmp_path, U_ref=1.0)
+    g3 = [v for v in violations if v.gate_id == "G3"]
+    assert len(g3) == 1
+    assert g3[0].evidence["u_max"] == pytest.approx(101.0)
+
+
+@pytest.mark.skip(reason="Wave 2 scope")
+def test_g3_U_ref_none_behavior() -> None:
+    pass
+
+
 # ---------------------------------------------------------------------------
 # NaN/Inf safety (Codex DEC-036b round-1 nit)
 # ---------------------------------------------------------------------------
diff --git a/ui/backend/tests/test_convergence_attestor.py b/ui/backend/tests/test_convergence_attestor.py
index a02d5d774bfce941d32895e48f7f3ccc6946faad..143fe368a994406fc6f8e64f880b0c9e8ad3afc8
--- a/ui/backend/tests/test_convergence_attestor.py
+++ b/ui/backend/tests/test_convergence_attestor.py
@@ -12,10 +12,12 @@
 from __future__ import annotations
 
 from pathlib import Path
+from types import SimpleNamespace
 
 import pytest
 
 from src import convergence_attestor as ca
+from src.convergence_attestor import Thresholds, load_thresholds
 
 
 def _write_log(tmp_path: Path, content: str) -> Path:
@@ -239,6 +241,44 @@
     assert a2.verdict == "HAZARD"  # was FAIL pre-fix
 
 
+def test_load_thresholds_defaults() -> None:
+    thresholds = load_thresholds()
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.continuity_floor == pytest.approx(1e-4)
+    assert thresholds.residual_floor == pytest.approx(1e-3)
+    assert thresholds.residual_floor_per_field["p_rgh"] == pytest.approx(1e-2)
+
+
+def test_load_thresholds_per_case_impinging_jet() -> None:
+    thresholds = load_thresholds("impinging_jet")
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.residual_floor_per_field["p_rgh"] == pytest.approx(5e-3)
+    assert thresholds.residual_floor_per_field["Ux"] == pytest.approx(1e-3)
+
+
+def test_load_thresholds_per_case_rayleigh_benard() -> None:
+    thresholds = load_thresholds("rayleigh_benard_convection")
+    assert thresholds.residual_floor_per_field["h"] == pytest.approx(2e-3)
+    assert thresholds.no_progress_decade_frac == pytest.approx(0.3)
+
+
+def test_load_thresholds_unknown_case_falls_back() -> None:
+    defaults = load_thresholds()
+    unknown = load_thresholds("nonexistent_xyz_12345")
+    assert unknown.continuity_floor == defaults.continuity_floor
+    assert unknown.residual_floor == defaults.residual_floor
+    assert unknown.residual_floor_per_field == defaults.residual_floor_per_field
+    assert unknown.no_progress_decade_frac == defaults.no_progress_decade_frac
+
+
+def test_load_thresholds_missing_yaml_uses_hardcoded(tmp_path: Path) -> None:
+    bad_path = tmp_path / "nonexistent.yaml"
+    thresholds = load_thresholds(yaml_path=bad_path)
+    assert isinstance(thresholds, Thresholds)
+    assert thresholds.continuity_floor == ca.A2_CONTINUITY_FLOOR
+    assert thresholds.residual_floor == ca.A3_RESIDUAL_FLOOR
+
+
 def test_a4_passes_on_sparse_cap_hits(tmp_path: Path) -> None:
     """Single-iteration cap is not pathological — solver typically hits
     high counts in transient but recovers."""
@@ -254,6 +294,52 @@
     assert a4.verdict == "PASS"
 
 
+def test_a1_exit_code_false_forces_fail(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=False, exit_code=139),
+    )
+    assert result.verdict == "FAIL"
+    assert result.evidence["exit_code"] == 139
+
+
+def test_a1_log_fatal_fires_even_with_success_exit(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nmiddle\nFloating exception\nEnd\n")
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=True, exit_code=0),
+    )
+    assert result.verdict == "FAIL"
+
+
+def test_a1_sigFpe_banner_not_false_positive(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "sigFpe : Enabling floating point exception trapping (FOAM_SIGFPE).\n"
+        "Time = 1\nEnd\n",
+    )
+    result = ca._check_a1_solver_crash(
+        log,
+        execution_result=SimpleNamespace(success=True, exit_code=0),
+    )
+    assert result.verdict == "PASS"
+
+
+def test_a3_per_field_threshold_impinging_jet_p_rgh(tmp_path: Path) -> None:
+    """Override guard: 6e-3 trips impinging_jet p_rgh (5e-3) but not YAML default (1e-2)."""
+    log = _write_log(
+        tmp_path,
+        "DILUPBiCGStab:  Solving for p_rgh, Initial residual = 6e-3, "
+        "Final residual = 1e-5, No Iterations 2\n",
+    )
+    impinging = ca._check_a3_residual_floor(log, thresholds=load_thresholds("impinging_jet"))
+    default = ca._check_a3_residual_floor(log, thresholds=load_thresholds())
+    assert impinging.verdict == "HAZARD"
+    assert impinging.evidence["thresholds_by_field"]["p_rgh"] == pytest.approx(5e-3)
+    assert default.verdict == "PASS"
+
+
 # ---------------------------------------------------------------------------
 # A5 bounding_recurrence
 # ---------------------------------------------------------------------------
@@ -320,6 +406,60 @@
     assert a6.verdict == "PASS"
 
 
+def test_a6_decade_range_exactly_1_fires_fail(tmp_path: Path) -> None:
+    """Boundary guard: exactly 1.0 decade must fire A6, which stays HAZARD-tier."""
+    lines = []
+    for i in range(50):
+        initial = "1.0" if i % 2 == 0 else "10.0"
+        lines.append(
+            f"smoothSolver:  Solving for Ux, Initial residual = {initial}, "
+            "Final residual = 0.5, No Iterations 2"
+        )
+    log = _write_log(tmp_path, "\n".join(lines) + "\n")
+    result = ca._check_a6_no_progress(log, thresholds=load_thresholds())
+    assert result.verdict == "HAZARD"
+    assert result.evidence["offenders"]["Ux"]["decades"] == pytest.approx(1.0)
+
+
+def test_a4_gap_blocks_reset_consecutive(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "Time = 1\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 2\n"
+        "smoothSolver:  Solving for Ux, Initial residual = 0.1, Final residual = 0.01, No Iterations 2\n"
+        "Time = 3\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 4\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n",
+    )
+    result = ca._check_a4_iteration_cap(log, thresholds=load_thresholds())
+    assert result.verdict == "PASS"
+
+
+def test_a4_three_consecutive_caps_fail(tmp_path: Path) -> None:
+    log = _write_log(
+        tmp_path,
+        "Time = 1\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 2\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n"
+        "Time = 3\n"
+        "GAMG:  Solving for p, Initial residual = 0.9, Final residual = 0.5, No Iterations 1000\n",
+    )
+    result = ca._check_a4_iteration_cap(log, thresholds=load_thresholds())
+    assert result.verdict == "FAIL"
+    assert result.evidence["consecutive_cap_blocks"] == 3
+
+
+def test_attest_with_execution_result_failure(tmp_path: Path) -> None:
+    log = _write_log(tmp_path, "Time = 1\nExecutionTime = 1 s\nEnd\n")
+    result = ca.attest(log, execution_result=SimpleNamespace(success=False))
+    a1 = next(c for c in result.checks if c.check_id == "A1")
+    assert result.overall == "ATTEST_FAIL"
+    assert a1.verdict == "FAIL"
+
+
 # ---------------------------------------------------------------------------
 # Real-log integration tests (guarded by file presence)
 # ---------------------------------------------------------------------------

tokens used
99,324
# Codex Diff Report — DEC-V61-045 Wave 1 C

## Files modified
- `ui/backend/tests/test_convergence_attestor.py` [+140/-0]
- `ui/backend/tests/test_comparator_gates_g3_g4_g5.py` [+103/-0]

## Tests added (per file)
- `test_load_thresholds_defaults` — verifies YAML defaults load into `Thresholds`; covers CHK-1.
- `test_load_thresholds_per_case_impinging_jet` — verifies `impinging_jet` override for `p_rgh`; covers CHK-1.
- `test_load_thresholds_per_case_rayleigh_benard` — verifies `rayleigh_benard_convection` overrides `h` and `no_progress_decade_frac`; covers CHK-1.
- `test_load_thresholds_unknown_case_falls_back` — verifies unknown case uses default threshold values without error; covers CHK-1.
- `test_load_thresholds_missing_yaml_uses_hardcoded` — verifies missing YAML falls back to module constants; covers CHK-1.
- `test_a1_exit_code_false_forces_fail` — verifies `execution_result.success=False` forces A1 FAIL and preserves `exit_code`; covers CHK-1.
- `test_a1_log_fatal_fires_even_with_success_exit` — verifies log fatal markers still fail A1 with successful exit status; covers CHK-1.
- `test_a1_sigFpe_banner_not_false_positive` — regression guard for benign `sigFpe` startup banner; covers CHK-1.
- `test_a3_per_field_threshold_impinging_jet_p_rgh` — proves the `impinging_jet` `p_rgh=5e-3` override is applied against YAML default behavior; covers CHK-1.
- `test_a6_decade_range_exactly_1_fires_fail` — guards the `<= 1.0` A6 boundary; confirms the check fires at exactly one decade; covers CHK-1.
- `test_a4_gap_blocks_reset_consecutive` — guards `[cap, gap, cap, cap]` resetting the streak; covers CHK-1.
- `test_a4_three_consecutive_caps_fail` — guards three back-to-back capped blocks failing A4; covers CHK-1.
- `test_attest_with_execution_result_failure` — verifies `attest(..., execution_result=SimpleNamespace(success=False))` produces `ATTEST_FAIL`; covers CHK-1.
- `test_read_final_velocity_max_skips_allPatches` — verifies `allPatches` VTKs are ignored and only the internal file is read; covers CHK-1.
- `test_read_final_velocity_max_uses_latest_timestep` — verifies latest numeric timestep wins over earlier spikes; covers CHK-1.
- `test_read_final_velocity_max_allPatches_only_returns_none` — verifies boundary-only VTK trees return `None`; covers CHK-1.
- `test_read_final_velocity_max_numeric_vs_alphabetic_sort` — verifies numeric suffix ordering beats alphabetic ordering; covers CHK-1.
- `test_read_final_velocity_max_no_timestep_suffix_skipped` — verifies non-matching filenames are ignored; covers CHK-1.
- `test_g3_boundary_99_U_ref_passes` — verifies G3 stays quiet just below `100 * U_ref`; covers CHK-1.
- `test_g3_boundary_101_U_ref_fails` — verifies G3 fires just above `100 * U_ref`; covers CHK-1.
- `test_g3_U_ref_none_behavior` — explicit `Wave 2 scope` skip pin per invocation note; no CHK counted.

## Existing tests touched (if any)
- None.

## Self-verified checks
- CHK-1: NOT RUN. Per REJ-4, I did not execute `pytest ui/backend/tests/test_convergence_attestor.py ui/backend/tests/test_comparator_gates_g3_g4_g5.py -q`.
- CHK-2: PASS by diff inspection. No existing test bodies were edited; only imports, local helpers, and new `test_*` functions were added.
- CHK-3: PASS by diff inspection. No `conftest.py` changes and no shared fixture additions outside the two allowed files.
- Syntax check: PASS via `env PYTHONPYCACHEPREFIX=/tmp/codex_pycache python3 -m py_compile ui/backend/tests/test_convergence_attestor.py ui/backend/tests/test_comparator_gates_g3_g4_g5.py`.

## Tokens used
- Not exposed by this Codex runtime.


