2026-04-25T18:02:24.677990Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-research-deerflow/SKILL.md: missing YAML frontmatter delimited by ---
2026-04-25T18:02:24.678007Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-report-pretext/SKILL.md: missing YAML frontmatter delimited by ---
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
session id: 019dc5ce-9a26-7bd2-9037-74ec6e58e851
--------
user
You are reviewing **DEC-V61-060 Stage D** — UI surface for rayleigh_benard_convection
(Type II RBC case, 4th application of methodology v2.0). Branch `dec-v61-060-rbc`,
commit b36c7a7.

CONTEXT:
- Type II observable taxonomy: 1 HARD_GATED + 1 NON_TYPE_HARD_INVARIANT + 2 PROVISIONAL_ADVISORY
- Gold YAML: knowledge/gold_standards/rayleigh_benard_convection.yaml (4 observables)
- DHC pattern (DEC-V61-057 Stage D) is the proven mirror; this commit reuses it
  with one new wrinkle: NON_TYPE_HARD_INVARIANT (ref_value=0, absolute tolerance)
- Stage A/B/C already shipped + Codex-approved (R3..R5)

CHANGES IN COMMIT b36c7a7:
1. ui/backend/services/comparison_report.py
   - Generalize _load_dhc_observable_gold → _load_case_observable_gold(case_id, name)
   - Surface tolerance.mode (relative | absolute) on the loaded dict
   - Keep DHC backwards-compat shim that fills de Vahl Davis 1983 source/doi defaults
   - Add metrics_rbc block (mirrors metrics_dhc) with 3 buckets:
     hard_gated_count + invariant_count + advisory_count
   - For absolute tolerance: emit deviation_abs/tolerance_abs, leave _pct as None
   - For relative tolerance: emit deviation_pct/tolerance_pct, leave _abs as None
   - Pending placeholder when measurement.secondary_scalars missing
   - Wire metrics_rbc into return dict
2. ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx
   - Add metrics_rbc TS type with tolerance_mode, deviation_abs, tolerance_abs,
     invariant_count
   - Add case_id === "rayleigh_benard_convection" rendering branch
   - INVARIANT badge ("守恒不变量") rose-tinted on violation, emerald within
   - ADVISORY badge ("不计入裁决") amber-tinted (mirrors DHC)
   - tolerance/deviation rendering branches on tolerance_mode
3. scripts/phase5_audit_run.py
   - Add nusselt_top_asymmetry, w_max_nondim, roll_count_x to
     _audit_fixture_doc secondary_scalars allowlist (both dict-comp keys
     AND truthiness guard) so Stage E live runs emit a renderable measurement YAML

VERIFICATION DONE:
- ui/backend tests: 23/23 PASS (DHC behaviour preserved via shim)
- tests/test_rbc_extractors.py + test_gold_standard.py: 48/48 PASS
- Loader smoke OK; w_max_nondim correctly returns None
  (ref_value="ADVISORY_NO_LITERATURE_LOCATOR" string, BRANCH-B per intake §3)

REVIEW SCOPE:
Code-level review of commit b36c7a7. Focus areas:
- Schema correctness of metrics_rbc (any field type/null mismatch
  between Python dict and TS type that would break the JSON boundary?)
- Gate-status semantics: does the invariant rendering correctly distinguish
  "blocking on violation" (Stage C.2 comparator) from "in pass-fraction
  denominator" (which it isn't)?
- Backwards-compat: does _load_dhc_observable_gold shim preserve the
  legacy default-fallback for de Vahl Davis 1983 source/literature_doi?
- Pending-card semantics: when secondary_scalars is missing, is the
  resulting card visually distinguishable AND not contributing to
  any false PASS in the bucket counts?
- Frontend: any conditional path that could throw on null/undefined
  for the absolute-tolerance branch?

OUTPUT: structured findings (F1=critical, F2=med, F3=low) with file:line refs
and concrete diff suggestions. APPROVE / APPROVE_WITH_COMMENTS / CHANGES_REQUIRED.

Files to read:
- ui/backend/services/comparison_report.py
- ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx
- scripts/phase5_audit_run.py
- knowledge/gold_standards/rayleigh_benard_convection.yaml
- ui/backend/services/comparison_report.py (DHC block at lines ~870-985 for parity
  comparison)
codex
Reviewing commit `b36c7a7` against the three touched surfaces and the gold YAML, with focus on JSON schema alignment, gate semantics, pending-state behavior, and DHC parity. I’ll inspect the exact diff plus the relevant surrounding code paths before writing findings.
exec
/bin/zsh -lc "sed -n '1,220p' /Users/Zhuanz/.codex/plugins/cache/openai-curated/superpowers/421657af0e7e94573f3a5f2c51091df43668da94/skills/using-superpowers/SKILL.md" in /Users/Zhuanz/Desktop/cfd-s4-rbc
exec
/bin/zsh -lc "sed -n '1,220p' /Users/Zhuanz/.agents/skills/gsd-code-review/SKILL.md" in /Users/Zhuanz/Desktop/cfd-s4-rbc
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
Using the review workflow here rather than implementing anything. I’m pulling the exact commit diff plus current line-numbered file views so findings are tied to the reviewed snapshot, not assumptions from the summary.
exec
/bin/zsh -lc 'git show --stat --oneline --decorate=short b36c7a7' in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
b36c7a7 (HEAD -> dec-v61-060-rbc) [line-b] feat(rbc): DEC-V61-060 Stage D · Compare-tab 4-card surface + audit_run secondary_scalars allowlist
 scripts/phase5_audit_run.py                        |  11 ++
 ui/backend/services/comparison_report.py           | 196 +++++++++++++++++++--
 .../src/pages/learn/LearnCaseDetailPage.tsx        | 180 +++++++++++++++++++
 3 files changed, 374 insertions(+), 13 deletions(-)

exec
/bin/zsh -lc 'git rev-parse --abbrev-ref HEAD && git rev-parse HEAD && git status --short' in /Users/Zhuanz/Desktop/cfd-s4-rbc
exec
/bin/zsh -lc 'git diff b36c7a7''^ b36c7a7 -- ui/backend/services/comparison_report.py ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx scripts/phase5_audit_run.py knowledge/gold_standards/rayleigh_benard_convection.yaml' in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
dec-v61-060-rbc
b36c7a7cecd238826dca4d35e677714f7e98e571
?? reports/codex_tool_reports/dec_v61_060_round6_stage_d.md

 succeeded in 0ms:
diff --git a/scripts/phase5_audit_run.py b/scripts/phase5_audit_run.py
index 3c75b8d..7855b71 100644
--- a/scripts/phase5_audit_run.py
+++ b/scripts/phase5_audit_run.py
@@ -543,6 +543,16 @@ def _audit_fixture_doc(
                         "u_max_centerline_v",
                         "v_max_centerline_h",
                         "psi_max_center",
+                        # DEC-V61-060 Stage D.3: rayleigh_benard_convection
+                        # 3 secondary observables (Stage E populates via
+                        # src.rbc_extractors.extract_*). nusselt_top_asymmetry
+                        # is the NON_TYPE_HARD_INVARIANT (blocking on
+                        # violation, excluded from primary_gate_count);
+                        # w_max_nondim + roll_count_x are
+                        # PROVISIONAL_ADVISORY (rendered, not enforced).
+                        "nusselt_top_asymmetry",
+                        "w_max_nondim",
+                        "roll_count_x",
                     ) if k in kq and kq[k] is not None
                 }
             } if any(
@@ -552,6 +562,7 @@ def _audit_fixture_doc(
                     "deficit_x_over_D_3.0", "deficit_x_over_D_5.0",
                     "nusselt_max", "u_max_centerline_v",
                     "v_max_centerline_h", "psi_max_center",
+                    "nusselt_top_asymmetry", "w_max_nondim", "roll_count_x",
                 )
             ) else {}),
         },
diff --git a/ui/backend/services/comparison_report.py b/ui/backend/services/comparison_report.py
index dcf27e4..02591ef 100644
--- a/ui/backend/services/comparison_report.py
+++ b/ui/backend/services/comparison_report.py
@@ -391,14 +391,20 @@ def _load_bfs_reattachment_gold() -> dict | None:
 
 
 # DEC-V61-057 Stage D: DHC structured-schema gold loader.
-def _load_dhc_observable_gold(name: str) -> dict | None:
-    """Load a DHC named observable from the schema_v2 differential_heated_cavity
-    gold YAML. Returns None when the YAML, observables block, or named entry
-    is missing. Surfaces gate_status (HARD_GATED | PROVISIONAL_ADVISORY) so the
-    Compare tab can render advisory observables with a distinct badge per
-    DEC-V61-057 §C/§D.
+# DEC-V61-060 Stage D.2: generalized to (case_id, name) for RBC reuse.
+# Now also surfaces tolerance.mode so callers can branch on absolute vs
+# relative tolerance — required for NON_TYPE_HARD_INVARIANT observables
+# whose ref_value is 0 (relative-percent deviation is undefined).
+def _load_case_observable_gold(case_id: str, name: str) -> dict | None:
+    """Load a named observable from the schema_v2 gold YAML for `case_id`.
+
+    Returns None when YAML, observables block, or named entry is missing.
+    Surfaces gate_status (HARD_GATED | NON_TYPE_HARD_INVARIANT |
+    PROVISIONAL_ADVISORY) and tolerance.mode (absolute | relative) so the
+    Compare tab can render conservation invariants and advisory observables
+    distinctly per DEC-V61-057/060 §C/§D.
     """
-    gold_path = _GOLD_ROOT / "differential_heated_cavity.yaml"
+    gold_path = _GOLD_ROOT / f"{case_id}.yaml"
     if not gold_path.is_file():
         return None
     try:
@@ -413,25 +419,43 @@ def _load_dhc_observable_gold(name: str) -> dict | None:
         if not isinstance(ref_value, (int, float)):
             return None
         tol_block = obs.get("tolerance") or {}
-        tol_value = (
-            float(tol_block.get("value", 0.10))
-            if isinstance(tol_block, dict) else float(tol_block)
-        )
+        if isinstance(tol_block, dict):
+            tol_value = float(tol_block.get("value", 0.10))
+            tol_mode = str(tol_block.get("mode", "relative"))
+        else:
+            tol_value = float(tol_block)
+            tol_mode = "relative"
         return {
             "value": float(ref_value),
             "unit": obs.get("unit", "dimensionless"),
             "tolerance": tol_value,
+            "tolerance_mode": tol_mode,
             "gate_status": obs.get("gate_status", "HARD_GATED"),
             "family": obs.get("family", "unspecified"),
             "role": obs.get("role", "observation"),
-            "source": gold.get("source", "de Vahl Davis 1983"),
-            "literature_doi": gold.get("literature_doi", "10.1002/fld.1650030305"),
+            "source": gold.get("source", ""),
+            "literature_doi": gold.get("literature_doi", ""),
             "source_table": obs.get("source_table", ""),
             "description": obs.get("description", ""),
         }
     return None
 
 
+def _load_dhc_observable_gold(name: str) -> dict | None:
+    """Backwards-compat shim — DHC-specific wrapper over the generalized
+    loader. Default source/doi fall back to de Vahl Davis 1983 when the YAML
+    omits them (legacy behaviour the DHC block depends on).
+    """
+    out = _load_case_observable_gold("differential_heated_cavity", name)
+    if out is None:
+        return None
+    if not out["source"]:
+        out["source"] = "de Vahl Davis 1983"
+    if not out["literature_doi"]:
+        out["literature_doi"] = "10.1002/fld.1650030305"
+    return out
+
+
 def _load_sample_xy(path: Path, value_col: int = 1) -> tuple[np.ndarray, np.ndarray]:
     """Load an OpenFOAM raw-xy sample file. Returns (coord, value) arrays.
 
@@ -965,6 +989,149 @@ def _build_visual_only_context(
         except (OSError, yaml.YAMLError, ValueError, TypeError):
             metrics_dhc = None
 
+    # DEC-V61-060 Stage D.2: rayleigh_benard_convection 4-observable anchor
+    # cards (1 HARD_GATED + 1 NON_TYPE_HARD_INVARIANT + 2 PROVISIONAL_ADVISORY).
+    # Headline value is `nusselt_number` carried in measurement.value; the other
+    # 3 come from measurement.secondary_scalars populated by Stage E live run.
+    # NON_TYPE_HARD_INVARIANT (nusselt_top_asymmetry) has ref_value=0 with an
+    # absolute tolerance — relative-percent deviation is undefined, so we
+    # surface deviation as the absolute |actual| and tolerance band as the
+    # absolute value (not converted to %).
+    metrics_rbc: Optional[dict] = None
+    if case_id == "rayleigh_benard_convection":
+        try:
+            meas_path = (_REPO_ROOT / "ui/backend/tests/fixtures/runs"
+                         / case_id / f"{run_label}_measurement.yaml")
+            if meas_path.is_file():
+                meas = yaml.safe_load(meas_path.read_text(encoding="utf-8")) or {}
+                m = meas.get("measurement", {}) or {}
+                primary_value = m.get("value")
+                secondary = m.get("secondary_scalars") or {}
+                rbc_observables: list[dict] = []
+                obs_to_value: dict[str, Any] = {
+                    "nusselt_number": primary_value,
+                    "nusselt_top_asymmetry": secondary.get("nusselt_top_asymmetry"),
+                    "w_max_nondim": secondary.get("w_max_nondim"),
+                    "roll_count_x": secondary.get("roll_count_x"),
+                }
+                label_map = {
+                    "nusselt_number":         ("R-Nu_avg",  "Nu",        "底部热壁平均 Nusselt"),
+                    "nusselt_top_asymmetry":  ("R-ΔNu/Nu",  "|ΔNu|/Nu",  "顶/底 Nu 守恒不对称"),
+                    "w_max_nondim":           ("R-w_max",   "w/U_ff",    "对流胞峰值垂向速度"),
+                    "roll_count_x":           ("R-N_roll",  "N_rolls",   "底壁两胞结构计数"),
+                }
+                for obs_name, actual in obs_to_value.items():
+                    gold = _load_case_observable_gold(case_id, obs_name)
+                    if gold is None:
+                        continue
+                    label, symbol, label_zh = label_map.get(
+                        obs_name, (obs_name, obs_name, obs_name)
+                    )
+                    expected = gold["value"]
+                    tol_value = gold["tolerance"]
+                    tol_mode = gold["tolerance_mode"]
+                    if isinstance(actual, (int, float)):
+                        actual_f = float(actual)
+                        if tol_mode == "absolute":
+                            # Conservation-invariant style: ref typically 0;
+                            # surface absolute deviation in same units.
+                            dev_abs = abs(actual_f - expected)
+                            within = dev_abs <= tol_value
+                            # tolerance_pct still reported as the absolute
+                            # band (units carried by the observable, not %).
+                            rbc_observables.append({
+                                "label": label,
+                                "label_zh": label_zh,
+                                "symbol": symbol,
+                                "name": obs_name,
+                                "actual": actual_f,
+                                "expected": expected,
+                                "deviation_pct": None,
+                                "deviation_abs": dev_abs,
+                                "tolerance_pct": None,
+                                "tolerance_abs": tol_value,
+                                "tolerance_mode": tol_mode,
+                                "within_tolerance": within,
+                                "gate_status": gold["gate_status"],
+                                "family": gold["family"],
+                                "role": gold["role"],
+                                "source_table": gold["source_table"],
+                            })
+                        else:
+                            dev_pct = (
+                                (actual_f - expected) / expected * 100
+                                if expected else 0.0
+                            )
+                            tol_pct = tol_value * 100.0
+                            within = abs(dev_pct) <= tol_pct
+                            rbc_observables.append({
+                                "label": label,
+                                "label_zh": label_zh,
+                                "symbol": symbol,
+                                "name": obs_name,
+                                "actual": actual_f,
+                                "expected": expected,
+                                "deviation_pct": dev_pct,
+                                "deviation_abs": None,
+                                "tolerance_pct": tol_pct,
+                                "tolerance_abs": None,
+                                "tolerance_mode": tol_mode,
+                                "within_tolerance": within,
+                                "gate_status": gold["gate_status"],
+                                "family": gold["family"],
+                                "role": gold["role"],
+                                "source_table": gold["source_table"],
+                            })
+                    else:
+                        # Pending placeholder — Stage E hasn't populated yet.
+                        rbc_observables.append({
+                            "label": label,
+                            "label_zh": label_zh,
+                            "symbol": symbol,
+                            "name": obs_name,
+                            "actual": None,
+                            "expected": expected,
+                            "deviation_pct": None,
+                            "deviation_abs": None,
+                            "tolerance_pct": (
+                                tol_value * 100.0 if tol_mode == "relative" else None
+                            ),
+                            "tolerance_abs": (
+                                tol_value if tol_mode == "absolute" else None
+                            ),
+                            "tolerance_mode": tol_mode,
+                            "within_tolerance": None,
+                            "gate_status": gold["gate_status"],
+                            "family": gold["family"],
+                            "role": gold["role"],
+                            "source_table": gold["source_table"],
+                            "pending": True,
+                        })
+                if rbc_observables:
+                    hard_gated = [
+                        o for o in rbc_observables
+                        if o["gate_status"] == "HARD_GATED"
+                    ]
+                    invariants = [
+                        o for o in rbc_observables
+                        if o["gate_status"] == "NON_TYPE_HARD_INVARIANT"
+                    ]
+                    advisory = [
+                        o for o in rbc_observables
+                        if o["gate_status"] == "PROVISIONAL_ADVISORY"
+                    ]
+                    metrics_rbc = {
+                        "observables": rbc_observables,
+                        "hard_gated_count": len(hard_gated),
+                        "invariant_count": len(invariants),
+                        "advisory_count": len(advisory),
+                        "source": "Pandey & Schumacher 2018 — TU Ilmenau DFG SPP 1881 Benchmark Case 1",
+                        "literature_doi": "",
+                        "short": "Pandey & Schumacher 2018 TU Ilmenau Table 1",
+                    }
+        except (OSError, yaml.YAMLError, ValueError, TypeError):
+            metrics_rbc = None
+
     return {
         "visual_only": True,
         "case_id": case_id,
@@ -1002,6 +1169,9 @@ def _build_visual_only_context(
         # DEC-V61-057 Stage D: DHC 5-observable Compare-tab block
         # (4 HARD_GATED + 1 PROVISIONAL_ADVISORY).
         "metrics_dhc": metrics_dhc,
+        # DEC-V61-060 Stage D.2: RBC 4-observable Compare-tab block
+        # (1 HARD_GATED + 1 NON_TYPE_HARD_INVARIANT + 2 PROVISIONAL_ADVISORY).
+        "metrics_rbc": metrics_rbc,
     }
 
 
diff --git a/ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx b/ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx
index c0dfbc5..6ad3b67 100644
--- a/ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx
+++ b/ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx
@@ -1498,6 +1498,155 @@ function MultiDimensionComparePanel({
       );
     }
 
+    // RBC 4-observable anchor cards (DEC-V61-060 Stage D · Pandey & Schumacher 2018)
+    // 1 HARD_GATED + 1 NON_TYPE_HARD_INVARIANT + 2 PROVISIONAL_ADVISORY. Mirrors DHC
+    // pattern but adds an "Invariant" badge for nusselt_top_asymmetry which uses
+    // absolute tolerance (ref_value=0) instead of relative %.
+    if (data.case_id === "rayleigh_benard_convection") {
+      const rbc = data.metrics_rbc;
+      if (!rbc || !rbc.observables || rbc.observables.length === 0) return null;
+
+      const renderRbcCard = (o: typeof rbc.observables[number]) => {
+        const isAdvisory = o.gate_status === "PROVISIONAL_ADVISORY";
+        const isInvariant = o.gate_status === "NON_TYPE_HARD_INVARIANT";
+        const isPending = !!o.pending;
+        const passing = o.within_tolerance === true;
+        const failing = o.within_tolerance === false;
+
+        let borderBg: string;
+        if (isPending) {
+          borderBg = "border-surface-800 bg-surface-900/40";
+        } else if (isAdvisory) {
+          borderBg = passing
+            ? "border-emerald-800/60 bg-emerald-900/15"
+            : "border-amber-800/60 bg-amber-900/15";
+        } else if (isInvariant) {
+          // Invariant violation BLOCKS the verdict — render rose like HARD_GATED.
+          borderBg = passing
+            ? "border-emerald-800/60 bg-emerald-900/15"
+            : "border-rose-800/60 bg-rose-900/15";
+        } else {
+          borderBg = passing
+            ? "border-emerald-800/60 bg-emerald-900/15"
+            : "border-rose-800/60 bg-rose-900/15";
+        }
+
+        let statusLabel: string;
+        let statusColor: string;
+        if (isPending) {
+          statusLabel = "PENDING";
+          statusColor = "text-surface-400";
+        } else if (passing) {
+          if (isAdvisory) { statusLabel = "ADVISORY · WITHIN"; statusColor = "text-emerald-300"; }
+          else if (isInvariant) { statusLabel = "INVARIANT · OK"; statusColor = "text-emerald-300"; }
+          else { statusLabel = "PASS"; statusColor = "text-emerald-300"; }
+        } else if (failing) {
+          if (isAdvisory) { statusLabel = "ADVISORY · OUTSIDE"; statusColor = "text-amber-300"; }
+          else if (isInvariant) { statusLabel = "INVARIANT · VIOLATED"; statusColor = "text-rose-300"; }
+          else { statusLabel = "FAIL"; statusColor = "text-rose-300"; }
+        } else {
+          statusLabel = "—";
+          statusColor = "text-surface-400";
+        }
+
+        const isAbsolute = o.tolerance_mode === "absolute";
+        const deviationDisplay: string =
+          isPending
+            ? "—"
+            : isAbsolute
+              ? (o.deviation_abs !== null && o.deviation_abs !== undefined
+                  ? o.deviation_abs.toFixed(4)
+                  : "—")
+              : (o.deviation_pct !== null && o.deviation_pct !== undefined
+                  ? `${o.deviation_pct.toFixed(1)}%`
+                  : "—");
+        const toleranceDisplay: string =
+          isAbsolute
+            ? (o.tolerance_abs !== null && o.tolerance_abs !== undefined
+                ? `±${o.tolerance_abs.toFixed(4)}`
+                : "—")
+            : (o.tolerance_pct !== null && o.tolerance_pct !== undefined
+                ? `±${o.tolerance_pct.toFixed(0)}%`
+                : "—");
+
+        return (
+          <div key={o.name} className={`rounded-md border p-3 ${borderBg}`}>
+            <div className="mb-2 flex items-baseline gap-2">
+              <span className="mono text-[10.5px] font-semibold uppercase tracking-wider text-surface-500">
+                {o.label} · {o.symbol}
+              </span>
+              <span className={`mono text-[10.5px] font-semibold ${statusColor}`}>
+                {statusLabel}
+              </span>
+              {isAdvisory && (
+                <span className="mono text-[10px] text-amber-300/80" title="Excluded from overall verdict — gate_status=PROVISIONAL_ADVISORY">
+                  · 不计入裁决
+                </span>
+              )}
+              {isInvariant && (
+                <span className="mono text-[10px] text-rose-300/80" title="Conservation invariant — violation forces verdict=FAIL but excluded from primary_gate_count denominator (DEC-V61-060 Stage C.2)">
+                  · 守恒不变量
+                </span>
+              )}
+            </div>
+            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
+              <div>
+                <div className="text-[10.5px] text-surface-500">测量</div>
+                <div className="mono text-surface-100">
+                  {o.actual !== null && o.actual !== undefined ? o.actual.toFixed(3) : "—"}
+                </div>
+              </div>
+              <div>
+                <div className="text-[10.5px] text-surface-500">金标准</div>
+                <div className="mono text-surface-100">
+                  {o.expected !== null && o.expected !== undefined ? o.expected.toFixed(3) : "—"}
+                </div>
+              </div>
+              <div>
+                <div className="text-[10.5px] text-surface-500">偏差</div>
+                <div className={`mono ${
+                  isPending
+                    ? "text-surface-500"
+                    : (passing
+                        ? "text-emerald-300"
+                        : (isAdvisory ? "text-amber-300" : "text-rose-300"))
+                }`}>
+                  {deviationDisplay}
+                </div>
+              </div>
+              <div>
+                <div className="text-[10.5px] text-surface-500">容差带</div>
+                <div className="mono text-surface-100">{toleranceDisplay}</div>
+              </div>
+            </div>
+            <div className="mt-2 text-[10.5px] text-surface-500">
+              {o.label_zh}
+              {o.source_table ? <> · 来源：<span className="mono">{o.source_table}</span></> : null}
+              {isPending && (
+                <span className="ml-1 text-amber-300/80">
+                  · Stage E live run 待跑（secondary_scalars 未填）
+                </span>
+              )}
+            </div>
+          </div>
+        );
+      };
+
+      return (
+        <section className="space-y-4">
+          <div className="flex items-baseline justify-between">
+            <h3 className="card-title">多维验证证据 · Multi-dimension evidence</h3>
+            <p className="text-[11px] text-surface-500">
+              {rbc.short} · {rbc.hard_gated_count} HARD_GATED + {rbc.invariant_count} INVARIANT + {rbc.advisory_count} ADVISORY (Type II 底加热 RBC)
+            </p>
+          </div>
+          <div className="grid gap-3 md:grid-cols-2">
+            {rbc.observables.map(renderRbcCard)}
+          </div>
+        </section>
+      );
+    }
+
     // Other visual_only cases: no scalar-anchor cards yet.
     return null;
   }
@@ -3080,6 +3229,37 @@ type ComparisonReportContext = {
     literature_doi: string;
     short: string;
   } | null;
+  // DEC-V61-060 Stage D.2: rayleigh_benard_convection 4-observable Compare-tab
+  // block (1 HARD_GATED + 1 NON_TYPE_HARD_INVARIANT + 2 PROVISIONAL_ADVISORY).
+  // NON_TYPE_HARD_INVARIANT carries absolute tolerance (ref_value=0); UI renders
+  // deviation/tolerance in the observable's native units instead of %.
+  metrics_rbc?: {
+    observables: {
+      label: string;
+      label_zh: string;
+      symbol: string;
+      name: string;
+      actual: number | null;
+      expected: number | null;
+      deviation_pct: number | null;
+      deviation_abs: number | null;
+      tolerance_pct: number | null;
+      tolerance_abs: number | null;
+      tolerance_mode: string;  // "relative" | "absolute"
+      within_tolerance: boolean | null;
+      gate_status: string;
+      family: string;
+      role: string;
+      source_table: string;
+      pending?: boolean;
+    }[];
+    hard_gated_count: number;
+    invariant_count: number;
+    advisory_count: number;
+    source: string;
+    literature_doi: string;
+    short: string;
+  } | null;
 };
 
 function ScientificComparisonReportSection({ caseId }: { caseId: string }) {

exec
/bin/zsh -lc "nl -ba ui/backend/services/comparison_report.py | sed -n '390,470p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
   390	    }
   391	
   392	
   393	# DEC-V61-057 Stage D: DHC structured-schema gold loader.
   394	# DEC-V61-060 Stage D.2: generalized to (case_id, name) for RBC reuse.
   395	# Now also surfaces tolerance.mode so callers can branch on absolute vs
   396	# relative tolerance — required for NON_TYPE_HARD_INVARIANT observables
   397	# whose ref_value is 0 (relative-percent deviation is undefined).
   398	def _load_case_observable_gold(case_id: str, name: str) -> dict | None:
   399	    """Load a named observable from the schema_v2 gold YAML for `case_id`.
   400	
   401	    Returns None when YAML, observables block, or named entry is missing.
   402	    Surfaces gate_status (HARD_GATED | NON_TYPE_HARD_INVARIANT |
   403	    PROVISIONAL_ADVISORY) and tolerance.mode (absolute | relative) so the
   404	    Compare tab can render conservation invariants and advisory observables
   405	    distinctly per DEC-V61-057/060 §C/§D.
   406	    """
   407	    gold_path = _GOLD_ROOT / f"{case_id}.yaml"
   408	    if not gold_path.is_file():
   409	        return None
   410	    try:
   411	        gold = yaml.safe_load(gold_path.read_text(encoding="utf-8")) or {}
   412	    except yaml.YAMLError:
   413	        return None
   414	    observables = gold.get("observables") or []
   415	    for obs in observables:
   416	        if not isinstance(obs, dict) or obs.get("name") != name:
   417	            continue
   418	        ref_value = obs.get("ref_value")
   419	        if not isinstance(ref_value, (int, float)):
   420	            return None
   421	        tol_block = obs.get("tolerance") or {}
   422	        if isinstance(tol_block, dict):
   423	            tol_value = float(tol_block.get("value", 0.10))
   424	            tol_mode = str(tol_block.get("mode", "relative"))
   425	        else:
   426	            tol_value = float(tol_block)
   427	            tol_mode = "relative"
   428	        return {
   429	            "value": float(ref_value),
   430	            "unit": obs.get("unit", "dimensionless"),
   431	            "tolerance": tol_value,
   432	            "tolerance_mode": tol_mode,
   433	            "gate_status": obs.get("gate_status", "HARD_GATED"),
   434	            "family": obs.get("family", "unspecified"),
   435	            "role": obs.get("role", "observation"),
   436	            "source": gold.get("source", ""),
   437	            "literature_doi": gold.get("literature_doi", ""),
   438	            "source_table": obs.get("source_table", ""),
   439	            "description": obs.get("description", ""),
   440	        }
   441	    return None
   442	
   443	
   444	def _load_dhc_observable_gold(name: str) -> dict | None:
   445	    """Backwards-compat shim — DHC-specific wrapper over the generalized
   446	    loader. Default source/doi fall back to de Vahl Davis 1983 when the YAML
   447	    omits them (legacy behaviour the DHC block depends on).
   448	    """
   449	    out = _load_case_observable_gold("differential_heated_cavity", name)
   450	    if out is None:
   451	        return None
   452	    if not out["source"]:
   453	        out["source"] = "de Vahl Davis 1983"
   454	    if not out["literature_doi"]:
   455	        out["literature_doi"] = "10.1002/fld.1650030305"
   456	    return out
   457	
   458	
   459	def _load_sample_xy(path: Path, value_col: int = 1) -> tuple[np.ndarray, np.ndarray]:
   460	    """Load an OpenFOAM raw-xy sample file. Returns (coord, value) arrays.
   461	
   462	    OpenFOAM's lineUniform function object writes either 2-col files
   463	    (coord + single-field-scalar) or 5-col files (coord + U_x + U_y + U_z
   464	    + p) depending on fields requested. Col 0 is always the sampling axis
   465	    coordinate. For u_centerline (sampled along y, U_x is the observable)
   466	    value_col=1 is correct. For v_centerline (sampled along x, U_y is the
   467	    observable) value_col=2.
   468	
   469	    DEC-V61-050 batch 1: value_col parameter added so a single helper
   470	    services both LDC observables without duplicating parser code.

exec
/bin/zsh -lc "nl -ba ui/backend/services/comparison_report.py | sed -n '870,1175p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
   870	                            "tolerance_pct": tol_pct,
   871	                            "all_within_tolerance": all_pass,
   872	                            "method": "sampleDict_cylinderCenterline_time_average",
   873	                        }
   874	                        paper_u_centerline = {
   875	                            "source": gold_centerline["source"],
   876	                            "doi": gold_centerline.get("literature_doi", ""),
   877	                            "short": "Williamson 1996 Fig.19",
   878	                            "tolerance_pct": tol_pct,
   879	                        }
   880	        except (OSError, yaml.YAMLError, ValueError, TypeError):
   881	            # Fail-soft: any parse/type issue → all 4 stay None; UI hides cards silently.
   882	            metrics_strouhal = None; paper_strouhal = None
   883	            metrics_cd_mean = None; paper_cd_mean = None
   884	            metrics_cl_rms = None; paper_cl_rms = None
   885	            metrics_u_centerline = None; paper_u_centerline = None
   886	
   887	    # DEC-V61-057 Stage D: differential_heated_cavity 5-observable anchor
   888	    # cards (4 HARD_GATED + 1 PROVISIONAL_ADVISORY). Mirrors cylinder pattern
   889	    # but reads from the structured schema_v2 observables[] block (not
   890	    # multi-doc YAML). Headline value is `nusselt_number` carried in
   891	    # measurement.value; the other 4 come from measurement.secondary_scalars
   892	    # populated by Stage E live run via scripts/phase5_audit_run.py.
   893	    metrics_dhc: Optional[dict] = None
   894	    if case_id == "differential_heated_cavity":
   895	        try:
   896	            meas_path = (_REPO_ROOT / "ui/backend/tests/fixtures/runs"
   897	                         / case_id / f"{run_label}_measurement.yaml")
   898	            if meas_path.is_file():
   899	                meas = yaml.safe_load(meas_path.read_text(encoding="utf-8")) or {}
   900	                m = meas.get("measurement", {}) or {}
   901	                primary_value = m.get("value")
   902	                secondary = m.get("secondary_scalars") or {}
   903	                dhc_observables: list[dict] = []
   904	                # Headline (nusselt_number) → primary measurement.value
   905	                # The other 4 → secondary_scalars (populated by Stage E).
   906	                obs_to_value: dict[str, Any] = {
   907	                    "nusselt_number": primary_value,
   908	                    "nusselt_max": secondary.get("nusselt_max"),
   909	                    "u_max_centerline_v": secondary.get("u_max_centerline_v"),
   910	                    "v_max_centerline_h": secondary.get("v_max_centerline_h"),
   911	                    "psi_max_center": secondary.get("psi_max_center"),
   912	                }
   913	                # Renderer-friendly Chinese labels keyed by observable name.
   914	                label_map = {
   915	                    "nusselt_number":      ("D-Nu_avg", "Nu", "壁面平均 Nusselt"),
   916	                    "nusselt_max":         ("D-Nu_max", "Nu_max", "壁面峰值 Nusselt"),
   917	                    "u_max_centerline_v":  ("D-u_max",  "u·L/α", "x=L/2 中线 u 峰值"),
   918	                    "v_max_centerline_h":  ("D-v_max",  "v·L/α", "y=L/2 中线 v 峰值"),
   919	                    "psi_max_center":      ("D-ψ_max",  "ψ·1/α",  "腔心流函数峰值"),
   920	                }
   921	                for obs_name, actual in obs_to_value.items():
   922	                    gold = _load_dhc_observable_gold(obs_name)
   923	                    if gold is None:
   924	                        continue
   925	                    label, symbol, label_zh = label_map.get(
   926	                        obs_name, (obs_name, obs_name, obs_name)
   927	                    )
   928	                    if isinstance(actual, (int, float)):
   929	                        actual_f = float(actual)
   930	                        expected = gold["value"]
   931	                        dev_pct = (
   932	                            (actual_f - expected) / expected * 100
   933	                            if expected else 0.0
   934	                        )
   935	                        tol_pct = gold["tolerance"] * 100.0
   936	                        within = abs(dev_pct) <= tol_pct
   937	                        dhc_observables.append({
   938	                            "label": label,
   939	                            "label_zh": label_zh,
   940	                            "symbol": symbol,
   941	                            "name": obs_name,
   942	                            "actual": actual_f,
   943	                            "expected": expected,
   944	                            "deviation_pct": dev_pct,
   945	                            "tolerance_pct": tol_pct,
   946	                            "within_tolerance": within,
   947	                            "gate_status": gold["gate_status"],
   948	                            "family": gold["family"],
   949	                            "role": gold["role"],
   950	                            "source_table": gold["source_table"],
   951	                        })
   952	                    else:
   953	                        # Stage E hasn't populated this observable yet —
   954	                        # surface a "pending" card so the user can see the
   955	                        # 5-observable promise even on Stage D fixtures.
   956	                        dhc_observables.append({
   957	                            "label": label,
   958	                            "label_zh": label_zh,
   959	                            "symbol": symbol,
   960	                            "name": obs_name,
   961	                            "actual": None,
   962	                            "expected": gold["value"],
   963	                            "deviation_pct": None,
   964	                            "tolerance_pct": gold["tolerance"] * 100.0,
   965	                            "within_tolerance": None,
   966	                            "gate_status": gold["gate_status"],
   967	                            "family": gold["family"],
   968	                            "role": gold["role"],
   969	                            "source_table": gold["source_table"],
   970	                            "pending": True,
   971	                        })
   972	                if dhc_observables:
   973	                    hard_gated = [
   974	                        o for o in dhc_observables
   975	                        if o["gate_status"] != "PROVISIONAL_ADVISORY"
   976	                    ]
   977	                    advisory = [
   978	                        o for o in dhc_observables
   979	                        if o["gate_status"] == "PROVISIONAL_ADVISORY"
   980	                    ]
   981	                    metrics_dhc = {
   982	                        "observables": dhc_observables,
   983	                        "hard_gated_count": len(hard_gated),
   984	                        "advisory_count": len(advisory),
   985	                        "source": "de Vahl Davis 1983",
   986	                        "literature_doi": "10.1002/fld.1650030305",
   987	                        "short": "de Vahl Davis 1983 Tables I/II/III",
   988	                    }
   989	        except (OSError, yaml.YAMLError, ValueError, TypeError):
   990	            metrics_dhc = None
   991	
   992	    # DEC-V61-060 Stage D.2: rayleigh_benard_convection 4-observable anchor
   993	    # cards (1 HARD_GATED + 1 NON_TYPE_HARD_INVARIANT + 2 PROVISIONAL_ADVISORY).
   994	    # Headline value is `nusselt_number` carried in measurement.value; the other
   995	    # 3 come from measurement.secondary_scalars populated by Stage E live run.
   996	    # NON_TYPE_HARD_INVARIANT (nusselt_top_asymmetry) has ref_value=0 with an
   997	    # absolute tolerance — relative-percent deviation is undefined, so we
   998	    # surface deviation as the absolute |actual| and tolerance band as the
   999	    # absolute value (not converted to %).
  1000	    metrics_rbc: Optional[dict] = None
  1001	    if case_id == "rayleigh_benard_convection":
  1002	        try:
  1003	            meas_path = (_REPO_ROOT / "ui/backend/tests/fixtures/runs"
  1004	                         / case_id / f"{run_label}_measurement.yaml")
  1005	            if meas_path.is_file():
  1006	                meas = yaml.safe_load(meas_path.read_text(encoding="utf-8")) or {}
  1007	                m = meas.get("measurement", {}) or {}
  1008	                primary_value = m.get("value")
  1009	                secondary = m.get("secondary_scalars") or {}
  1010	                rbc_observables: list[dict] = []
  1011	                obs_to_value: dict[str, Any] = {
  1012	                    "nusselt_number": primary_value,
  1013	                    "nusselt_top_asymmetry": secondary.get("nusselt_top_asymmetry"),
  1014	                    "w_max_nondim": secondary.get("w_max_nondim"),
  1015	                    "roll_count_x": secondary.get("roll_count_x"),
  1016	                }
  1017	                label_map = {
  1018	                    "nusselt_number":         ("R-Nu_avg",  "Nu",        "底部热壁平均 Nusselt"),
  1019	                    "nusselt_top_asymmetry":  ("R-ΔNu/Nu",  "|ΔNu|/Nu",  "顶/底 Nu 守恒不对称"),
  1020	                    "w_max_nondim":           ("R-w_max",   "w/U_ff",    "对流胞峰值垂向速度"),
  1021	                    "roll_count_x":           ("R-N_roll",  "N_rolls",   "底壁两胞结构计数"),
  1022	                }
  1023	                for obs_name, actual in obs_to_value.items():
  1024	                    gold = _load_case_observable_gold(case_id, obs_name)
  1025	                    if gold is None:
  1026	                        continue
  1027	                    label, symbol, label_zh = label_map.get(
  1028	                        obs_name, (obs_name, obs_name, obs_name)
  1029	                    )
  1030	                    expected = gold["value"]
  1031	                    tol_value = gold["tolerance"]
  1032	                    tol_mode = gold["tolerance_mode"]
  1033	                    if isinstance(actual, (int, float)):
  1034	                        actual_f = float(actual)
  1035	                        if tol_mode == "absolute":
  1036	                            # Conservation-invariant style: ref typically 0;
  1037	                            # surface absolute deviation in same units.
  1038	                            dev_abs = abs(actual_f - expected)
  1039	                            within = dev_abs <= tol_value
  1040	                            # tolerance_pct still reported as the absolute
  1041	                            # band (units carried by the observable, not %).
  1042	                            rbc_observables.append({
  1043	                                "label": label,
  1044	                                "label_zh": label_zh,
  1045	                                "symbol": symbol,
  1046	                                "name": obs_name,
  1047	                                "actual": actual_f,
  1048	                                "expected": expected,
  1049	                                "deviation_pct": None,
  1050	                                "deviation_abs": dev_abs,
  1051	                                "tolerance_pct": None,
  1052	                                "tolerance_abs": tol_value,
  1053	                                "tolerance_mode": tol_mode,
  1054	                                "within_tolerance": within,
  1055	                                "gate_status": gold["gate_status"],
  1056	                                "family": gold["family"],
  1057	                                "role": gold["role"],
  1058	                                "source_table": gold["source_table"],
  1059	                            })
  1060	                        else:
  1061	                            dev_pct = (
  1062	                                (actual_f - expected) / expected * 100
  1063	                                if expected else 0.0
  1064	                            )
  1065	                            tol_pct = tol_value * 100.0
  1066	                            within = abs(dev_pct) <= tol_pct
  1067	                            rbc_observables.append({
  1068	                                "label": label,
  1069	                                "label_zh": label_zh,
  1070	                                "symbol": symbol,
  1071	                                "name": obs_name,
  1072	                                "actual": actual_f,
  1073	                                "expected": expected,
  1074	                                "deviation_pct": dev_pct,
  1075	                                "deviation_abs": None,
  1076	                                "tolerance_pct": tol_pct,
  1077	                                "tolerance_abs": None,
  1078	                                "tolerance_mode": tol_mode,
  1079	                                "within_tolerance": within,
  1080	                                "gate_status": gold["gate_status"],
  1081	                                "family": gold["family"],
  1082	                                "role": gold["role"],
  1083	                                "source_table": gold["source_table"],
  1084	                            })
  1085	                    else:
  1086	                        # Pending placeholder — Stage E hasn't populated yet.
  1087	                        rbc_observables.append({
  1088	                            "label": label,
  1089	                            "label_zh": label_zh,
  1090	                            "symbol": symbol,
  1091	                            "name": obs_name,
  1092	                            "actual": None,
  1093	                            "expected": expected,
  1094	                            "deviation_pct": None,
  1095	                            "deviation_abs": None,
  1096	                            "tolerance_pct": (
  1097	                                tol_value * 100.0 if tol_mode == "relative" else None
  1098	                            ),
  1099	                            "tolerance_abs": (
  1100	                                tol_value if tol_mode == "absolute" else None
  1101	                            ),
  1102	                            "tolerance_mode": tol_mode,
  1103	                            "within_tolerance": None,
  1104	                            "gate_status": gold["gate_status"],
  1105	                            "family": gold["family"],
  1106	                            "role": gold["role"],
  1107	                            "source_table": gold["source_table"],
  1108	                            "pending": True,
  1109	                        })
  1110	                if rbc_observables:
  1111	                    hard_gated = [
  1112	                        o for o in rbc_observables
  1113	                        if o["gate_status"] == "HARD_GATED"
  1114	                    ]
  1115	                    invariants = [
  1116	                        o for o in rbc_observables
  1117	                        if o["gate_status"] == "NON_TYPE_HARD_INVARIANT"
  1118	                    ]
  1119	                    advisory = [
  1120	                        o for o in rbc_observables
  1121	                        if o["gate_status"] == "PROVISIONAL_ADVISORY"
  1122	                    ]
  1123	                    metrics_rbc = {
  1124	                        "observables": rbc_observables,
  1125	                        "hard_gated_count": len(hard_gated),
  1126	                        "invariant_count": len(invariants),
  1127	                        "advisory_count": len(advisory),
  1128	                        "source": "Pandey & Schumacher 2018 — TU Ilmenau DFG SPP 1881 Benchmark Case 1",
  1129	                        "literature_doi": "",
  1130	                        "short": "Pandey & Schumacher 2018 TU Ilmenau Table 1",
  1131	                    }
  1132	        except (OSError, yaml.YAMLError, ValueError, TypeError):
  1133	            metrics_rbc = None
  1134	
  1135	    return {
  1136	        "visual_only": True,
  1137	        "case_id": case_id,
  1138	        "run_label": run_label,
  1139	        "timestamp": timestamp,
  1140	        "renders": renders,
  1141	        "solver": solver,
  1142	        "commit_sha": commit_sha,
  1143	        "verdict": None,
  1144	        "verdict_gradient": "#64748b 0%, #94a3b8 100%",
  1145	        "subtitle": (
  1146	            "Visual-only mode (DEC-V61-034 Tier C): real OpenFOAM field + "
  1147	            "residual evidence captured; per-case gold-overlay plumbing pending "
  1148	            "Phase 7c Sprint 2 (Tier B)."
  1149	        ),
  1150	        "paper": None,
  1151	        "metrics": None,
  1152	        "gci": None,
  1153	        "grid_convergence": None,
  1154	        "deviations": None,
  1155	        "residual_info": None,
  1156	        "tolerance_percent": None,
  1157	        # DEC-V61-052 Batch D: BFS scalar-anchor block.
  1158	        "metrics_reattachment": metrics_reattachment,
  1159	        "paper_reattachment": paper_reattachment,
  1160	        # DEC-V61-053 Batch D: cylinder 4-scalar + profile anchor blocks.
  1161	        "metrics_strouhal": metrics_strouhal,
  1162	        "paper_strouhal": paper_strouhal,
  1163	        "metrics_cd_mean": metrics_cd_mean,
  1164	        "paper_cd_mean": paper_cd_mean,
  1165	        "metrics_cl_rms": metrics_cl_rms,
  1166	        "paper_cl_rms": paper_cl_rms,
  1167	        "metrics_u_centerline": metrics_u_centerline,
  1168	        "paper_u_centerline": paper_u_centerline,
  1169	        # DEC-V61-057 Stage D: DHC 5-observable Compare-tab block
  1170	        # (4 HARD_GATED + 1 PROVISIONAL_ADVISORY).
  1171	        "metrics_dhc": metrics_dhc,
  1172	        # DEC-V61-060 Stage D.2: RBC 4-observable Compare-tab block
  1173	        # (1 HARD_GATED + 1 NON_TYPE_HARD_INVARIANT + 2 PROVISIONAL_ADVISORY).
  1174	        "metrics_rbc": metrics_rbc,
  1175	    }

exec
/bin/zsh -lc "nl -ba ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx | sed -n '1490,1660p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
exec
/bin/zsh -lc "nl -ba scripts/phase5_audit_run.py | sed -n '532,570p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
exec
/bin/zsh -lc "nl -ba knowledge/gold_standards/rayleigh_benard_convection.yaml | sed -n '1,220p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
exec
/bin/zsh -lc "nl -ba ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx | sed -n '3210,3275p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
   532	            **({
   533	                "secondary_scalars": {
   534	                    k: kq[k] for k in (
   535	                        # DEC-V61-053 cylinder cross-checks
   536	                        "cd_mean", "cl_rms",
   537	                        "deficit_x_over_D_1.0", "deficit_x_over_D_2.0",
   538	                        "deficit_x_over_D_3.0", "deficit_x_over_D_5.0",
   539	                        # DEC-V61-057 Stage D.3: differential_heated_cavity
   540	                        # 4-observable cross-checks (Stage E populates these
   541	                        # via src.dhc_extractors.extract_*).
   542	                        "nusselt_max",
   543	                        "u_max_centerline_v",
   544	                        "v_max_centerline_h",
   545	                        "psi_max_center",
   546	                        # DEC-V61-060 Stage D.3: rayleigh_benard_convection
   547	                        # 3 secondary observables (Stage E populates via
   548	                        # src.rbc_extractors.extract_*). nusselt_top_asymmetry
   549	                        # is the NON_TYPE_HARD_INVARIANT (blocking on
   550	                        # violation, excluded from primary_gate_count);
   551	                        # w_max_nondim + roll_count_x are
   552	                        # PROVISIONAL_ADVISORY (rendered, not enforced).
   553	                        "nusselt_top_asymmetry",
   554	                        "w_max_nondim",
   555	                        "roll_count_x",
   556	                    ) if k in kq and kq[k] is not None
   557	                }
   558	            } if any(
   559	                k in kq for k in (
   560	                    "cd_mean", "cl_rms",
   561	                    "deficit_x_over_D_1.0", "deficit_x_over_D_2.0",
   562	                    "deficit_x_over_D_3.0", "deficit_x_over_D_5.0",
   563	                    "nusselt_max", "u_max_centerline_v",
   564	                    "v_max_centerline_h", "psi_max_center",
   565	                    "nusselt_top_asymmetry", "w_max_nondim", "roll_count_x",
   566	                )
   567	            ) else {}),
   568	        },
   569	        "audit_concerns": [],
   570	        "decisions_trail": [

 succeeded in 0ms:
  1490	            <p className="text-[11px] text-surface-500">
  1491	              {dhc.short} · {dhc.hard_gated_count} 个 HARD_GATED + {dhc.advisory_count} 个 PROVISIONAL_ADVISORY (Type I 自然对流方腔)
  1492	            </p>
  1493	          </div>
  1494	          <div className="grid gap-3 md:grid-cols-2">
  1495	            {dhc.observables.map(renderDhcCard)}
  1496	          </div>
  1497	        </section>
  1498	      );
  1499	    }
  1500	
  1501	    // RBC 4-observable anchor cards (DEC-V61-060 Stage D · Pandey & Schumacher 2018)
  1502	    // 1 HARD_GATED + 1 NON_TYPE_HARD_INVARIANT + 2 PROVISIONAL_ADVISORY. Mirrors DHC
  1503	    // pattern but adds an "Invariant" badge for nusselt_top_asymmetry which uses
  1504	    // absolute tolerance (ref_value=0) instead of relative %.
  1505	    if (data.case_id === "rayleigh_benard_convection") {
  1506	      const rbc = data.metrics_rbc;
  1507	      if (!rbc || !rbc.observables || rbc.observables.length === 0) return null;
  1508	
  1509	      const renderRbcCard = (o: typeof rbc.observables[number]) => {
  1510	        const isAdvisory = o.gate_status === "PROVISIONAL_ADVISORY";
  1511	        const isInvariant = o.gate_status === "NON_TYPE_HARD_INVARIANT";
  1512	        const isPending = !!o.pending;
  1513	        const passing = o.within_tolerance === true;
  1514	        const failing = o.within_tolerance === false;
  1515	
  1516	        let borderBg: string;
  1517	        if (isPending) {
  1518	          borderBg = "border-surface-800 bg-surface-900/40";
  1519	        } else if (isAdvisory) {
  1520	          borderBg = passing
  1521	            ? "border-emerald-800/60 bg-emerald-900/15"
  1522	            : "border-amber-800/60 bg-amber-900/15";
  1523	        } else if (isInvariant) {
  1524	          // Invariant violation BLOCKS the verdict — render rose like HARD_GATED.
  1525	          borderBg = passing
  1526	            ? "border-emerald-800/60 bg-emerald-900/15"
  1527	            : "border-rose-800/60 bg-rose-900/15";
  1528	        } else {
  1529	          borderBg = passing
  1530	            ? "border-emerald-800/60 bg-emerald-900/15"
  1531	            : "border-rose-800/60 bg-rose-900/15";
  1532	        }
  1533	
  1534	        let statusLabel: string;
  1535	        let statusColor: string;
  1536	        if (isPending) {
  1537	          statusLabel = "PENDING";
  1538	          statusColor = "text-surface-400";
  1539	        } else if (passing) {
  1540	          if (isAdvisory) { statusLabel = "ADVISORY · WITHIN"; statusColor = "text-emerald-300"; }
  1541	          else if (isInvariant) { statusLabel = "INVARIANT · OK"; statusColor = "text-emerald-300"; }
  1542	          else { statusLabel = "PASS"; statusColor = "text-emerald-300"; }
  1543	        } else if (failing) {
  1544	          if (isAdvisory) { statusLabel = "ADVISORY · OUTSIDE"; statusColor = "text-amber-300"; }
  1545	          else if (isInvariant) { statusLabel = "INVARIANT · VIOLATED"; statusColor = "text-rose-300"; }
  1546	          else { statusLabel = "FAIL"; statusColor = "text-rose-300"; }
  1547	        } else {
  1548	          statusLabel = "—";
  1549	          statusColor = "text-surface-400";
  1550	        }
  1551	
  1552	        const isAbsolute = o.tolerance_mode === "absolute";
  1553	        const deviationDisplay: string =
  1554	          isPending
  1555	            ? "—"
  1556	            : isAbsolute
  1557	              ? (o.deviation_abs !== null && o.deviation_abs !== undefined
  1558	                  ? o.deviation_abs.toFixed(4)
  1559	                  : "—")
  1560	              : (o.deviation_pct !== null && o.deviation_pct !== undefined
  1561	                  ? `${o.deviation_pct.toFixed(1)}%`
  1562	                  : "—");
  1563	        const toleranceDisplay: string =
  1564	          isAbsolute
  1565	            ? (o.tolerance_abs !== null && o.tolerance_abs !== undefined
  1566	                ? `±${o.tolerance_abs.toFixed(4)}`
  1567	                : "—")
  1568	            : (o.tolerance_pct !== null && o.tolerance_pct !== undefined
  1569	                ? `±${o.tolerance_pct.toFixed(0)}%`
  1570	                : "—");
  1571	
  1572	        return (
  1573	          <div key={o.name} className={`rounded-md border p-3 ${borderBg}`}>
  1574	            <div className="mb-2 flex items-baseline gap-2">
  1575	              <span className="mono text-[10.5px] font-semibold uppercase tracking-wider text-surface-500">
  1576	                {o.label} · {o.symbol}
  1577	              </span>
  1578	              <span className={`mono text-[10.5px] font-semibold ${statusColor}`}>
  1579	                {statusLabel}
  1580	              </span>
  1581	              {isAdvisory && (
  1582	                <span className="mono text-[10px] text-amber-300/80" title="Excluded from overall verdict — gate_status=PROVISIONAL_ADVISORY">
  1583	                  · 不计入裁决
  1584	                </span>
  1585	              )}
  1586	              {isInvariant && (
  1587	                <span className="mono text-[10px] text-rose-300/80" title="Conservation invariant — violation forces verdict=FAIL but excluded from primary_gate_count denominator (DEC-V61-060 Stage C.2)">
  1588	                  · 守恒不变量
  1589	                </span>
  1590	              )}
  1591	            </div>
  1592	            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
  1593	              <div>
  1594	                <div className="text-[10.5px] text-surface-500">测量</div>
  1595	                <div className="mono text-surface-100">
  1596	                  {o.actual !== null && o.actual !== undefined ? o.actual.toFixed(3) : "—"}
  1597	                </div>
  1598	              </div>
  1599	              <div>
  1600	                <div className="text-[10.5px] text-surface-500">金标准</div>
  1601	                <div className="mono text-surface-100">
  1602	                  {o.expected !== null && o.expected !== undefined ? o.expected.toFixed(3) : "—"}
  1603	                </div>
  1604	              </div>
  1605	              <div>
  1606	                <div className="text-[10.5px] text-surface-500">偏差</div>
  1607	                <div className={`mono ${
  1608	                  isPending
  1609	                    ? "text-surface-500"
  1610	                    : (passing
  1611	                        ? "text-emerald-300"
  1612	                        : (isAdvisory ? "text-amber-300" : "text-rose-300"))
  1613	                }`}>
  1614	                  {deviationDisplay}
  1615	                </div>
  1616	              </div>
  1617	              <div>
  1618	                <div className="text-[10.5px] text-surface-500">容差带</div>
  1619	                <div className="mono text-surface-100">{toleranceDisplay}</div>
  1620	              </div>
  1621	            </div>
  1622	            <div className="mt-2 text-[10.5px] text-surface-500">
  1623	              {o.label_zh}
  1624	              {o.source_table ? <> · 来源：<span className="mono">{o.source_table}</span></> : null}
  1625	              {isPending && (
  1626	                <span className="ml-1 text-amber-300/80">
  1627	                  · Stage E live run 待跑（secondary_scalars 未填）
  1628	                </span>
  1629	              )}
  1630	            </div>
  1631	          </div>
  1632	        );
  1633	      };
  1634	
  1635	      return (
  1636	        <section className="space-y-4">
  1637	          <div className="flex items-baseline justify-between">
  1638	            <h3 className="card-title">多维验证证据 · Multi-dimension evidence</h3>
  1639	            <p className="text-[11px] text-surface-500">
  1640	              {rbc.short} · {rbc.hard_gated_count} HARD_GATED + {rbc.invariant_count} INVARIANT + {rbc.advisory_count} ADVISORY (Type II 底加热 RBC)
  1641	            </p>
  1642	          </div>
  1643	          <div className="grid gap-3 md:grid-cols-2">
  1644	            {rbc.observables.map(renderRbcCard)}
  1645	          </div>
  1646	        </section>
  1647	      );
  1648	    }
  1649	
  1650	    // Other visual_only cases: no scalar-anchor cards yet.
  1651	    return null;
  1652	  }
  1653	  if (!data.metrics || !data.paper) return null;
  1654	
  1655	  const m = data.metrics;
  1656	  const renderUrl = (basename: string) =>
  1657	    `/api/cases/${encodeURIComponent(caseId)}/runs/${encodeURIComponent(
  1658	      runLabel,
  1659	    )}/renders/${basename}`;
  1660	  const profileUrl = data.renders.profile_png_rel ? renderUrl("profile_u_centerline.png") : null;

 succeeded in 0ms:
  3210	    observables: {
  3211	      label: string;
  3212	      label_zh: string;
  3213	      symbol: string;
  3214	      name: string;
  3215	      actual: number | null;
  3216	      expected: number | null;
  3217	      deviation_pct: number | null;
  3218	      tolerance_pct: number;
  3219	      within_tolerance: boolean | null;
  3220	      gate_status: string;
  3221	      family: string;
  3222	      role: string;
  3223	      source_table: string;
  3224	      pending?: boolean;
  3225	    }[];
  3226	    hard_gated_count: number;
  3227	    advisory_count: number;
  3228	    source: string;
  3229	    literature_doi: string;
  3230	    short: string;
  3231	  } | null;
  3232	  // DEC-V61-060 Stage D.2: rayleigh_benard_convection 4-observable Compare-tab
  3233	  // block (1 HARD_GATED + 1 NON_TYPE_HARD_INVARIANT + 2 PROVISIONAL_ADVISORY).
  3234	  // NON_TYPE_HARD_INVARIANT carries absolute tolerance (ref_value=0); UI renders
  3235	  // deviation/tolerance in the observable's native units instead of %.
  3236	  metrics_rbc?: {
  3237	    observables: {
  3238	      label: string;
  3239	      label_zh: string;
  3240	      symbol: string;
  3241	      name: string;
  3242	      actual: number | null;
  3243	      expected: number | null;
  3244	      deviation_pct: number | null;
  3245	      deviation_abs: number | null;
  3246	      tolerance_pct: number | null;
  3247	      tolerance_abs: number | null;
  3248	      tolerance_mode: string;  // "relative" | "absolute"
  3249	      within_tolerance: boolean | null;
  3250	      gate_status: string;
  3251	      family: string;
  3252	      role: string;
  3253	      source_table: string;
  3254	      pending?: boolean;
  3255	    }[];
  3256	    hard_gated_count: number;
  3257	    invariant_count: number;
  3258	    advisory_count: number;
  3259	    source: string;
  3260	    literature_doi: string;
  3261	    short: string;
  3262	  } | null;
  3263	};
  3264	
  3265	function ScientificComparisonReportSection({ caseId }: { caseId: string }) {
  3266	  const runLabel = "audit_real_run";
  3267	  const { data, isLoading, error } = useQuery<ComparisonReportContext, ApiError>({
  3268	    queryKey: ["comparison-report-ctx", caseId, runLabel],
  3269	    queryFn: async () => {
  3270	      const resp = await fetch(
  3271	        `/api/cases/${encodeURIComponent(caseId)}/runs/${encodeURIComponent(
  3272	          runLabel,
  3273	        )}/comparison-report/context`,
  3274	        { credentials: "same-origin" },
  3275	      );

 succeeded in 0ms:
     1	schema_version: 2
     2	case_id: rayleigh_benard_convection
     3	source: "Pandey & Schumacher 2018 — TU Ilmenau DFG SPP 1881 Benchmark Case 1"
     4	literature_doi: ""  # benchmark tutorial; primary citation is the publicly-archived PDF
     5	literature_url: "https://www.tu-ilmenau.de/fileadmin/Bereiche/MB/sm/DFG-Priority_Programme_1881__Turbulent_Superstructures/Benchmark_cases/Benchmark_case_1/Tutorial_RBC.pdf"
     6	note: >
     7	  DEC-V61-060 Stage A.0 (2026-04-25): pivoted from broken Chaivat 2006
     8	  / DOI 10.1016/j.ijheatmasstransfer.2005.07.039 (which actually resolves
     9	  to a rectangular-jets impingement-cooling paper, NOT RBC) to the
    10	  publicly-archived Pandey & Schumacher TU Ilmenau benchmark.
    11	  Benchmark parameters: Lx=4, H=1 (AR=4), Pr=10, Ra=10^6, free-slip
    12	  walls all-around, fixed-T top/bottom, zeroGradient T sidewalls. The
    13	  reported Nu=17.7 is the time-averaged Nusselt number over the
    14	  statistically-stationary window t/t_f ∈ [2000, 2500] (Table 1, p.6).
    15	  Adapter implementation deviations: (a) steady SIMPLE solver instead of
    16	  time-resolved RK4 — captures a metastable steady-ish solution, not a
    17	  true time-average; (b) no-slip walls (OF10 hotRoom convention) instead
    18	  of free-slip; (c) Pr=10 retained (matches benchmark, NOT the prior
    19	  air-Pr=0.71 setup). Tolerance widened to ±25% to absorb (a)+(b).
    20	physics_contract:
    21	  geometry_assumption: "2D rectangular cavity, Lx=4 H=1 (AR=4), heated from below, cooled from above, insulated zeroGradient T sidewalls; Boussinesq approximation; Pr=10 (water-like)"
    22	  reference_correlation_context: "Pandey & Schumacher 2018 TU Ilmenau benchmark Table 1: Nu_avg=17.7 ± large fluctuations 10-30 (Fig 2). At Ra=10^6 Pr=10 the 2D RBC flow is mildly turbulent with two dominant counter-rotating rolls (Fig 4b). Adapter steady SIMPLE captures the mean roll structure; instantaneous Nu cannot match because a time-average is unavailable from a steady solve."
    23	  physics_precondition:
    24	    - condition: "Mesh resolves both the 2-roll structure (Lx/2 wavelength) and the boundary layer (~10 cells across thermal BL at Ra=1e6)"
    25	      satisfied_by_current_adapter: pending_stage_a_4
    26	      evidence_ref: "Stage A.4 will add horizontal-wall BL grading; pre-A.4 mesh is uniform 80x40 — borderline for AR=4."
    27	    - condition: "Bottom-heated topology (hot wall y=0, cold wall y=Ly) with gravity (0,-g,0)"
    28	      satisfied_by_current_adapter: pending_stage_a_3
    29	      evidence_ref: "Pre-Stage-A.3 adapter emits side-heated topology (DEC-V61-060 risk_flag rbc_topology_side_heated_vs_bottom_heated)."
    30	    - condition: "Nu extracted from bottom hot-wall temperature gradient via wall_orientation='y' branch in _extract_nc_nusselt"
    31	      satisfied_by_current_adapter: pending_stage_a_2
    32	      evidence_ref: "Pre-Stage-A.2 _extract_nc_nusselt has only x-orientation branch (DEC-V61-060 risk_flag nu_extractor_wall_orientation_mismatch)."
    33	  contract_status: "INCOMPLETE_PRE_STAGE_A — preconditions point to Stage A.1-A.4 deliverables. Will become COMPATIBLE after Stage A.5 integration smoke."
    34	  precondition_last_reviewed: "2026-04-25 (DEC-V61-060 Stage A.0 citation commit)"
    35	observables:
    36	  - name: nusselt_number
    37	    description: "RBC time-averaged Nu_avg at Ra=1e6, Pr=10, AR=4 (Pandey & Schumacher 2018 TU Ilmenau benchmark Table 1 p.6)"
    38	    ref_value: 17.7
    39	    unit: dimensionless
    40	    family: wall_gradient_derived
    41	    role: HEADLINE
    42	    gate_status: HARD_GATED
    43	    counts_toward_primary_gate_count: true
    44	    source_table: "Pandey & Schumacher 2018 TU Ilmenau DFG SPP 1881 Benchmark Case 1, Table 1, p.6 (https://www.tu-ilmenau.de/fileadmin/Bereiche/MB/sm/DFG-Priority_Programme_1881__Turbulent_Superstructures/Benchmark_cases/Benchmark_case_1/Tutorial_RBC.pdf)"
    45	    tolerance:
    46	      mode: relative
    47	      value: 0.25  # widened from 0.15 — see physics_contract.note for rationale
    48	  - name: nusselt_top_asymmetry
    49	    description: "Conservation invariant: |Nu_top - Nu_bottom| / |Nu_bottom|; should be ~0 by mass + energy conservation"
    50	    ref_value: 0.0
    51	    unit: dimensionless
    52	    family: wall_gradient_derived
    53	    role: CONSERVATION_INVARIANT
    54	    gate_status: NON_TYPE_HARD_INVARIANT  # Stage C.2 will add comparator branch (DEC-V61-060 §7)
    55	    counts_toward_primary_gate_count: false
    56	    source_table: "Conservation invariant (NOT a literature value); blocking on violation but excluded from primary_gate_count denominator"
    57	    tolerance:
    58	      mode: absolute
    59	      value: 0.05  # 5% relative imbalance band
    60	  - name: w_max_nondim
    61	    description: "Peak |u_y| nondimensionalized by free-fall velocity U_ff=sqrt(g·β·ΔT·H); advisory only"
    62	    ref_value: ADVISORY_NO_LITERATURE_LOCATOR  # BRANCH-B per intake §3 advisory_rationale
    63	    unit: dimensionless
    64	    family: interior_velocity_field
    65	    role: ADVISORY_INTERIOR_VELOCITY
    66	    gate_status: PROVISIONAL_ADVISORY
    67	    counts_toward_primary_gate_count: false
    68	    source_table: "Pandey & Schumacher 2018 reports Re_rms=95.5 (Table 1) but no point-value w_max with locator. Werne 1993 / Goldhirsch 1989 paywalled — see DEC-V61-060 commit body §A.0-search-trail."
    69	    tolerance:
    70	      mode: relative
    71	      value: 0.20  # not enforced (advisory)
    72	  - name: roll_count_x
    73	    description: "Counter-rotating roll count along bottom hot wall; canonical 2-roll structure for AR=4 at Ra=1e6"
    74	    ref_value: 2  # Pandey & Schumacher Fig 4b shows dominant 2-roll structure for AR=4 Pr=10 Ra=1e6
    75	    unit: count
    76	    family: structural
    77	    role: ADVISORY_STRUCTURAL
    78	    gate_status: PROVISIONAL_ADVISORY
    79	    counts_toward_primary_gate_count: false
    80	    source_table: "Pandey & Schumacher 2018 Fig 4b (instantaneous t=2250 t_f) and Fig 5 (time-averaged): two-roll structure with hot fluid rising at center and cold fluid descending at sidewalls"
    81	    tolerance:
    82	      mode: absolute
    83	      value: 0  # exact match (advisory only)

exec
/bin/zsh -lc "rg -n \"metrics_rbc|NON_TYPE_HARD_INVARIANT|tolerance_mode|deviation_abs|tolerance_abs\" ui/backend ui/frontend src tests -g '"'!node_modules'"'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
exec
/bin/zsh -lc "rg -n \"comparison-report/context|ComparisonReportContext|metrics_dhc\" ui/backend ui/frontend -g '"'!node_modules'"'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
ui/backend/services/comparison_report.py:893:    metrics_dhc: Optional[dict] = None
ui/backend/services/comparison_report.py:981:                    metrics_dhc = {
ui/backend/services/comparison_report.py:990:            metrics_dhc = None
ui/backend/services/comparison_report.py:1171:        "metrics_dhc": metrics_dhc,
ui/backend/services/comparison_report.py:1606:            f"/api/cases/{case_id}/runs/{run_label}/comparison-report/context "
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1128:// Reuses the existing comparison-report/context endpoint (same data
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1169:  const { data, error, isLoading } = useQuery<ComparisonReportContext, ApiError>({
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1175:        )}/comparison-report/context`,
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1179:      return (await resp.json()) as ComparisonReportContext;
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1389:      const dhc = data.metrics_dhc;
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:2927:type ComparisonReportContext = {
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:3209:  metrics_dhc?: {
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:3267:  const { data, isLoading, error } = useQuery<ComparisonReportContext, ApiError>({
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:3273:        )}/comparison-report/context`,
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:3277:      return (await resp.json()) as ComparisonReportContext;
ui/backend/routes/comparison_report.py:49:    "/cases/{case_id}/runs/{run_label}/comparison-report/context",
ui/backend/tests/test_comparison_report_visual_only.py:117:        "/api/cases/totally_unknown_case/runs/audit_real_run/comparison-report/context",
ui/backend/tests/test_comparison_report_visual_only.py:406:    scalars → metrics_dhc emits 5 cards (4 HARD_GATED + 1 PROVISIONAL_ADVISORY)."""
ui/backend/tests/test_comparison_report_visual_only.py:434:    assert ctx["metrics_dhc"] is not None
ui/backend/tests/test_comparison_report_visual_only.py:435:    obs = ctx["metrics_dhc"]["observables"]
ui/backend/tests/test_comparison_report_visual_only.py:441:    assert ctx["metrics_dhc"]["hard_gated_count"] == 4
ui/backend/tests/test_comparison_report_visual_only.py:442:    assert ctx["metrics_dhc"]["advisory_count"] == 1
ui/backend/tests/test_comparison_report_visual_only.py:480:    obs = ctx["metrics_dhc"]["observables"]
ui/backend/tests/test_comparison_report_visual_only.py:524:    by_name = {o["name"]: o for o in ctx["metrics_dhc"]["observables"]}
ui/backend/tests/test_comparison_report_route.py:51:        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report/context",
ui/backend/tests/test_comparison_report_route.py:79:        "/api/cases/%2e%2e__pwn/runs/audit_real_run/comparison-report/context",
ui/backend/tests/test_comparison_report_route.py:175:        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report/context",

 succeeded in 0ms:
tests/test_auto_verifier/test_gold_standard.py:193:# DEC-V61-060 Stage C.2 · NON_TYPE_HARD_INVARIANT branch tests
tests/test_auto_verifier/test_gold_standard.py:206:             "gate_status": "NON_TYPE_HARD_INVARIANT"},
tests/test_auto_verifier/test_gold_standard.py:229:             "gate_status": "NON_TYPE_HARD_INVARIANT"},
tests/test_auto_verifier/test_gold_standard.py:258:             "gate_status": "NON_TYPE_HARD_INVARIANT"},
tests/test_auto_verifier/test_gold_standard.py:269:    """Mixed scenario: HARD_GATED + NON_TYPE_HARD_INVARIANT + 2× PROVISIONAL_ADVISORY
tests/test_auto_verifier/test_gold_standard.py:279:             "gate_status": "NON_TYPE_HARD_INVARIANT"},
ui/backend/services/comparison_report.py:396:# relative tolerance — required for NON_TYPE_HARD_INVARIANT observables
ui/backend/services/comparison_report.py:402:    Surfaces gate_status (HARD_GATED | NON_TYPE_HARD_INVARIANT |
ui/backend/services/comparison_report.py:432:            "tolerance_mode": tol_mode,
ui/backend/services/comparison_report.py:993:    # cards (1 HARD_GATED + 1 NON_TYPE_HARD_INVARIANT + 2 PROVISIONAL_ADVISORY).
ui/backend/services/comparison_report.py:996:    # NON_TYPE_HARD_INVARIANT (nusselt_top_asymmetry) has ref_value=0 with an
ui/backend/services/comparison_report.py:1000:    metrics_rbc: Optional[dict] = None
ui/backend/services/comparison_report.py:1032:                    tol_mode = gold["tolerance_mode"]
ui/backend/services/comparison_report.py:1050:                                "deviation_abs": dev_abs,
ui/backend/services/comparison_report.py:1052:                                "tolerance_abs": tol_value,
ui/backend/services/comparison_report.py:1053:                                "tolerance_mode": tol_mode,
ui/backend/services/comparison_report.py:1075:                                "deviation_abs": None,
ui/backend/services/comparison_report.py:1077:                                "tolerance_abs": None,
ui/backend/services/comparison_report.py:1078:                                "tolerance_mode": tol_mode,
ui/backend/services/comparison_report.py:1095:                            "deviation_abs": None,
ui/backend/services/comparison_report.py:1099:                            "tolerance_abs": (
ui/backend/services/comparison_report.py:1102:                            "tolerance_mode": tol_mode,
ui/backend/services/comparison_report.py:1117:                        if o["gate_status"] == "NON_TYPE_HARD_INVARIANT"
ui/backend/services/comparison_report.py:1123:                    metrics_rbc = {
ui/backend/services/comparison_report.py:1133:            metrics_rbc = None
ui/backend/services/comparison_report.py:1173:        # (1 HARD_GATED + 1 NON_TYPE_HARD_INVARIANT + 2 PROVISIONAL_ADVISORY).
ui/backend/services/comparison_report.py:1174:        "metrics_rbc": metrics_rbc,
src/rbc_extractors.py:13:    (HARD_GATED / NON_TYPE_HARD_INVARIANT / PROVISIONAL_ADVISORY),
src/rbc_extractors.py:29:  - ``extract_nu_asymmetry`` (B.1, NON_TYPE_HARD_INVARIANT): conservation
src/report_engine/generator.py:98:        # DEC-V61-060 Stage C.2: also exclude NON_TYPE_HARD_INVARIANT
src/report_engine/generator.py:107:                not in ("PROVISIONAL_ADVISORY", "NON_TYPE_HARD_INVARIANT")
tests/test_rbc_extractors.py:388:        Demonstrates that the NON_TYPE_HARD_INVARIANT fires correctly
src/auto_verifier/gold_standard_comparator.py:26:        # DEC-V61-060 Stage C.2: NON_TYPE_HARD_INVARIANT observables (e.g.
src/auto_verifier/gold_standard_comparator.py:34:            if c.gate_status not in ("PROVISIONAL_ADVISORY", "NON_TYPE_HARD_INVARIANT")
src/auto_verifier/gold_standard_comparator.py:36:        invariant_checks = [c for c in checks if c.gate_status == "NON_TYPE_HARD_INVARIANT"]
src/auto_verifier/gold_standard_comparator.py:54:        # DEC-V61-060 Stage C.2 acceptance criterion (i): NON_TYPE_HARD_INVARIANT
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1502:    // 1 HARD_GATED + 1 NON_TYPE_HARD_INVARIANT + 2 PROVISIONAL_ADVISORY. Mirrors DHC
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1506:      const rbc = data.metrics_rbc;
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1511:        const isInvariant = o.gate_status === "NON_TYPE_HARD_INVARIANT";
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1552:        const isAbsolute = o.tolerance_mode === "absolute";
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1557:              ? (o.deviation_abs !== null && o.deviation_abs !== undefined
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1558:                  ? o.deviation_abs.toFixed(4)
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1565:            ? (o.tolerance_abs !== null && o.tolerance_abs !== undefined
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1566:                ? `±${o.tolerance_abs.toFixed(4)}`
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:3233:  // block (1 HARD_GATED + 1 NON_TYPE_HARD_INVARIANT + 2 PROVISIONAL_ADVISORY).
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:3234:  // NON_TYPE_HARD_INVARIANT carries absolute tolerance (ref_value=0); UI renders
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:3236:  metrics_rbc?: {
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:3245:      deviation_abs: number | null;
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:3247:      tolerance_abs: number | null;
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:3248:      tolerance_mode: string;  // "relative" | "absolute"

codex
I’ve got the exact reviewed snapshot. Next pass is checking whether the commit’s semantics match the existing Stage C comparator behavior and whether the UI/backend boundary is actually safe under the current route/tests, not just under ideal fixture values.
exec
/bin/zsh -lc "nl -ba src/auto_verifier/gold_standard_comparator.py | sed -n '1,140p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
exec
/bin/zsh -lc "nl -ba src/report_engine/generator.py | sed -n '80,130p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
exec
/bin/zsh -lc "nl -ba ui/backend/routes/comparison_report.py | sed -n '1,180p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
    80	        output.write_text(result.markdown, encoding="utf-8")
    81	        result.output_path = str(output)
    82	        return result
    83	
    84	    def generate_many(self, case_ids: Iterable[str]) -> List[RenderResult]:
    85	        return [self.generate(case_id) for case_id in case_ids]
    86	
    87	    @staticmethod
    88	    def _build_template_context(context: ReportContext) -> dict:
    89	        verify = context.auto_verify_report
    90	        comparison = verify["gold_standard_comparison"]
    91	        observables = comparison.get("observables", [])
    92	        # DEC-V61-057 Codex round-4 F2-LOW: match_rate must exclude
    93	        # PROVISIONAL_ADVISORY observables so the markdown report agrees
    94	        # with the comparator's overall verdict (Stage C: advisory checks
    95	        # don't degrade the pass-fraction). Backward compat: legacy
    96	        # ObservableCheck.to_dict() omitting gate_status defaults to
    97	        # HARD_GATED.
    98	        # DEC-V61-060 Stage C.2: also exclude NON_TYPE_HARD_INVARIANT
    99	        # observables from match_rate. These are conservation invariants
   100	        # (no literature ref_value); they BLOCK the verdict on violation
   101	        # but DO NOT count toward the pass-fraction denominator. This
   102	        # matches the comparator's own hard_checks definition (RBC
   103	        # denominator = 1, not 2 — see intake §7C acceptance criterion iv).
   104	        hard_observables = [
   105	            o for o in observables
   106	            if o.get("gate_status", "HARD_GATED")
   107	                not in ("PROVISIONAL_ADVISORY", "NON_TYPE_HARD_INVARIANT")
   108	        ]
   109	        pass_count = sum(1 for observable in hard_observables if observable.get("within_tolerance"))
   110	        total_count = len(hard_observables)
   111	        match_rate = (pass_count / total_count) if total_count else 0.0
   112	        return {
   113	            "case_id": context.case_id,
   114	            "case_meta": context.case_meta,
   115	            "gold_standard": context.gold_standard,
   116	            "auto_verify_report": verify,
   117	            "attribution_report": context.attribution_report,
   118	            "correction_spec": context.correction_spec,
   119	            "project_progress": context.project_progress,
   120	            "match_rate": match_rate,
   121	            "deviation_direction": _deviation_direction,
   122	            "format_value": _format_value,
   123	        }
   124	
   125	    @staticmethod
   126	    def _warnings(context: ReportContext) -> List[str]:
   127	        warnings = []
   128	        if context.case_meta.get("meta_source") == "[DATA MISSING]":
   129	            warnings.append("case_meta_missing")
   130	        if context.attribution_report is None and context.auto_verify_report.get("verdict") == "FAIL":

 succeeded in 0ms:
     1	"""Contract-aware Gold Standard comparison for anchor cases."""
     2	
     3	from __future__ import annotations
     4	
     5	import math
     6	from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, cast
     7	
     8	from .config import PROFILE_VALUE_KEYS, THRESHOLDS, ZERO_REFERENCE_EPSILON
     9	from .schemas import GoldStandardComparison, ObservableCheck
    10	
    11	
    12	class GoldStandardComparator:
    13	    """Compare contract observables against simulated results."""
    14	
    15	    def compare(self, gold_standard: Dict[str, Any], sim_results: Dict[str, Any]) -> GoldStandardComparison:
    16	        observables = gold_standard.get("observables", [])
    17	        if not observables:
    18	            return GoldStandardComparison(overall="SKIPPED", warnings=["missing_gold_standard_observables"])
    19	
    20	        checks: List[ObservableCheck] = []
    21	        for observable in observables:
    22	            checks.append(self._compare_observable(observable, sim_results))
    23	
    24	        # DEC-V61-057 Stage C: PROVISIONAL_ADVISORY observables are rendered
    25	        # for the user but excluded from the pass-fraction verdict.
    26	        # DEC-V61-060 Stage C.2: NON_TYPE_HARD_INVARIANT observables (e.g.
    27	        # RBC nusselt_top_asymmetry) are conservation invariants — also
    28	        # excluded from the pass-fraction denominator (they carry no
    29	        # literature ref_value), but BLOCKING on violation: if any
    30	        # invariant fails, run.overall = FAIL regardless of HARD_GATED
    31	        # pass-fraction. See intake §7C acceptance criteria i-iv.
    32	        hard_checks = [
    33	            c for c in checks
    34	            if c.gate_status not in ("PROVISIONAL_ADVISORY", "NON_TYPE_HARD_INVARIANT")
    35	        ]
    36	        invariant_checks = [c for c in checks if c.gate_status == "NON_TYPE_HARD_INVARIANT"]
    37	        warnings: List[str] = []
    38	        if not hard_checks:
    39	            return GoldStandardComparison(
    40	                overall="SKIPPED",
    41	                observables=checks,
    42	                warnings=["no_hard_gated_observables"],
    43	            )
    44	
    45	        pass_count = sum(1 for check in hard_checks if check.within_tolerance)
    46	        ratio = pass_count / len(hard_checks)
    47	        if pass_count == len(hard_checks):
    48	            overall = "PASS"
    49	        elif ratio >= THRESHOLDS["TH-8"]:
    50	            overall = "PASS_WITH_DEVIATIONS"
    51	        else:
    52	            overall = "FAIL"
    53	
    54	        # DEC-V61-060 Stage C.2 acceptance criterion (i): NON_TYPE_HARD_INVARIANT
    55	        # violation FAILs the run even when HARD_GATED observables pass. The
    56	        # invariant represents a physics-conservation requirement (e.g.
    57	        # |Nu_top - Nu_bottom| / |Nu_bottom| ≤ 0.05); a violation indicates
    58	        # BL under-resolution or solver imbalance, both of which would also
    59	        # invalidate the headline Nu even if it numerically lands inside
    60	        # the wide ±25% tolerance band by coincidence.
    61	        invariant_failures = [c for c in invariant_checks if not c.within_tolerance]
    62	        if invariant_failures:
    63	            overall = "FAIL"
    64	            for c in invariant_failures:
    65	                warnings.append(f"non_type_hard_invariant_violated:{c.name}")
    66	
    67	        # If any PROVISIONAL_ADVISORY observable failed its tolerance check,
    68	        # surface that as a non-blocking warning so the UI can render the
    69	        # advisory caveat without changing the verdict.
    70	        for c in checks:
    71	            if c.gate_status == "PROVISIONAL_ADVISORY" and not c.within_tolerance:
    72	                warnings.append(f"advisory_observable_outside_tolerance:{c.name}")
    73	
    74	        return GoldStandardComparison(overall=overall, observables=checks, warnings=warnings)
    75	
    76	    def _compare_observable(self, observable: Dict[str, Any], sim_results: Dict[str, Any]) -> ObservableCheck:
    77	        name = observable["name"]
    78	        ref_value = observable["ref_value"]
    79	        tolerance = observable.get("tolerance", {"mode": "relative", "value": THRESHOLDS["TH-5"]})
    80	        gate_status = observable.get("gate_status", "HARD_GATED")
    81	        sim_value = sim_results.get(name)
    82	
    83	        if sim_value is None:
    84	            return ObservableCheck(
    85	                name=name,
    86	                ref_value=ref_value,
    87	                sim_value=None,
    88	                rel_error=None,
    89	                abs_error=None,
    90	                tolerance=tolerance,
    91	                within_tolerance=False,
    92	                gate_status=gate_status,
    93	            )
    94	
    95	        if isinstance(ref_value, list):
    96	            check = self._compare_profile(name, ref_value, sim_value, sim_results, tolerance)
    97	        elif isinstance(ref_value, dict):
    98	            check = self._compare_mapping(name, ref_value, sim_value, tolerance)
    99	        else:
   100	            check = self._compare_scalar(name, ref_value, sim_value, tolerance)
   101	        check.gate_status = gate_status
   102	        return check
   103	
   104	    def _compare_scalar(
   105	        self,
   106	        name: str,
   107	        ref_value: Any,
   108	        sim_value: Any,
   109	        tolerance: Dict[str, Any],
   110	    ) -> ObservableCheck:
   111	        if not self._is_finite_number(sim_value):
   112	            return ObservableCheck(name, ref_value, sim_value, None, None, tolerance, False)
   113	
   114	        rel_error, abs_error, within = self._compare_number(float(ref_value), float(sim_value), tolerance)
   115	        return ObservableCheck(name, ref_value, sim_value, rel_error, abs_error, tolerance, within)
   116	
   117	    def _compare_mapping(
   118	        self,
   119	        name: str,
   120	        ref_value: Dict[str, Any],
   121	        sim_value: Any,
   122	        tolerance: Dict[str, Any],
   123	    ) -> ObservableCheck:
   124	        if not isinstance(sim_value, dict):
   125	            return ObservableCheck(name, ref_value, sim_value, None, None, tolerance, False)
   126	
   127	        rel_errors, abs_errors, within_all = self._compare_mapping_entries(ref_value, sim_value, tolerance)
   128	
   129	        return ObservableCheck(
   130	            name=name,
   131	            ref_value=ref_value,
   132	            sim_value=sim_value,
   133	            rel_error=max(rel_errors) if rel_errors else None,
   134	            abs_error=max(abs_errors) if abs_errors else None,
   135	            tolerance=tolerance,
   136	            within_tolerance=within_all,
   137	        )
   138	
   139	    def _compare_mapping_entries(
   140	        self,

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
/bin/zsh -lc "rg -n \"rayleigh_benard_convection|metrics_rbc|nusselt_top_asymmetry|roll_count_x|w_max_nondim\" ui/backend/tests tests ui/frontend/src/pages/learn -g '"'!node_modules'"'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
tests/test_auto_verifier/test_gold_standard.py:204:            {"name": "nusselt_top_asymmetry", "ref_value": 0.0,
tests/test_auto_verifier/test_gold_standard.py:209:    sim = {"nusselt_number": 17.0, "nusselt_top_asymmetry": 0.02}
tests/test_auto_verifier/test_gold_standard.py:227:            {"name": "nusselt_top_asymmetry", "ref_value": 0.0,
tests/test_auto_verifier/test_gold_standard.py:233:           "nusselt_top_asymmetry": 0.10}    # FAIL (> 0.05)
tests/test_auto_verifier/test_gold_standard.py:238:    assert any("non_type_hard_invariant_violated:nusselt_top_asymmetry" in w
tests/test_auto_verifier/test_gold_standard.py:256:            {"name": "nusselt_top_asymmetry", "ref_value": 0.0,
tests/test_auto_verifier/test_gold_standard.py:261:    sim = {"nusselt_number": 17.0, "nusselt_top_asymmetry": 0.0}
tests/test_auto_verifier/test_gold_standard.py:277:            {"name": "nusselt_top_asymmetry", "ref_value": 0.0,
tests/test_auto_verifier/test_gold_standard.py:280:            {"name": "w_max_nondim", "ref_value": 1.5,
tests/test_auto_verifier/test_gold_standard.py:283:            {"name": "roll_count_x", "ref_value": 2,
tests/test_auto_verifier/test_gold_standard.py:289:    sim = {"nusselt_number": 17.0, "nusselt_top_asymmetry": 0.02,
tests/test_auto_verifier/test_gold_standard.py:290:           "w_max_nondim": 1.6, "roll_count_x": 2}
tests/test_auto_verifier/test_gold_standard.py:294:    sim_with_advisory_miss = dict(sim, w_max_nondim=2.5)  # 67% off
tests/test_auto_verifier/test_gold_standard.py:299:    assert any("advisory_observable_outside_tolerance:w_max_nondim" in w
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:132:  rayleigh_benard_convection: {
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1503:    // pattern but adds an "Invariant" badge for nusselt_top_asymmetry which uses
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1505:    if (data.case_id === "rayleigh_benard_convection") {
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1506:      const rbc = data.metrics_rbc;
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:3232:  // DEC-V61-060 Stage D.2: rayleigh_benard_convection 4-observable Compare-tab
ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:3236:  metrics_rbc?: {
ui/backend/tests/test_convergence_attestor.py:373:    thresholds = load_thresholds("rayleigh_benard_convection")
tests/test_foam_agent_adapter.py:1460:        spec = _make_nc_spec(Ra=1e6, aspect_ratio=4.0, name="rayleigh_benard_convection")
tests/test_foam_agent_adapter.py:1674:        spec = _make_nc_spec(Ra=1e6, aspect_ratio=4.0, name="rayleigh_benard_convection")
tests/test_foam_agent_adapter.py:1690:        """DEC-V61-057 Batch A.2: rayleigh_benard_convection's whitelist also
tests/test_foam_agent_adapter.py:2446:            Ra=1e6, aspect_ratio=4.0, name="rayleigh_benard_convection"
tests/test_foam_agent_adapter.py:2489:            Ra=1e6, aspect_ratio=4.0, name="rayleigh_benard_convection"
tests/test_foam_agent_adapter.py:2527:            name="rayleigh_benard_convection",
tests/test_foam_agent_adapter.py:2607:            Ra=1e6, aspect_ratio=4.0, name="rayleigh_benard_convection"
tests/test_foam_agent_adapter.py:2658:            Ra=1e6, aspect_ratio=4.0, name="rayleigh_benard_convection"
tests/test_foam_agent_adapter.py:2689:            Ra=1e6, aspect_ratio=4.0, name="rayleigh_benard_convection"
tests/test_foam_agent_adapter.py:2724:            Ra=1e6, aspect_ratio=4.0, name="rayleigh_benard_convection"
tests/test_foam_agent_adapter.py:2784:            Ra=1e6, aspect_ratio=4.0, name="rayleigh_benard_convection"
tests/test_foam_agent_adapter.py:2823:            Ra=1e6, aspect_ratio=4.0, name="rayleigh_benard_convection"
tests/test_rbc_extractors.py:221:        # → w_max_nondim ≈ 0.005 / 0.00316 ≈ 1.58
tests/test_rbc_extractors.py:271:from src.rbc_extractors import extract_roll_count_x
tests/test_rbc_extractors.py:275:    """DEC-V61-060 Stage B.3 unit tests for extract_roll_count_x."""
tests/test_rbc_extractors.py:283:        out = extract_roll_count_x(slice_, bc)
tests/test_rbc_extractors.py:296:        out = extract_roll_count_x(slice_, bc)
tests/test_rbc_extractors.py:315:        out = extract_roll_count_x(slice_, bc)
tests/test_rbc_extractors.py:337:        out = extract_roll_count_x(slice_, bc)
tests/test_rbc_extractors.py:361:          - w_max_nondim positive O(1)
tests/test_rbc_extractors.py:368:        rc_out = extract_roll_count_x(slice_, bc)
tests/test_rbc_extractors.py:410:        rc_out = extract_roll_count_x(slice_, bc)
tests/test_rbc_extractors.py:422:        for fn in (extract_nu_asymmetry, extract_w_max, extract_roll_count_x):
tests/test_rbc_extractors.py:466:        out = extract_roll_count_x(slice_, bc)
tests/test_metrics/test_case_profile_loader.py:216:        "rayleigh_benard_convection",
ui/backend/tests/test_comparison_report_visual_only.py:80:        "rayleigh_benard_convection", "differential_heated_cavity", "duct_flow",
ui/backend/tests/test_case_export.py:101:        "rayleigh_benard_convection",
ui/backend/tests/fixtures/runs/rayleigh_benard_convection/wrong_model_measurement.yaml:1:# Wrong-model run for rayleigh_benard_convection at Ra=1e7.
ui/backend/tests/fixtures/runs/rayleigh_benard_convection/wrong_model_measurement.yaml:18:case_id: rayleigh_benard_convection
ui/backend/tests/test_dec039_profile_verdict_reconciliation.py:47:                 "rayleigh_benard_convection"):
ui/backend/tests/fixtures/runs/rayleigh_benard_convection/mesh_160_measurement.yaml:12:case_id: rayleigh_benard_convection
ui/backend/tests/fixtures/runs/rayleigh_benard_convection/real_incident_measurement.yaml:1:# Real-incident run for rayleigh_benard_convection.
ui/backend/tests/fixtures/runs/rayleigh_benard_convection/real_incident_measurement.yaml:18:case_id: rayleigh_benard_convection
ui/backend/tests/test_grid_convergence_monotonicity.py:48:    "rayleigh_benard_convection",
ui/backend/tests/fixtures/runs/rayleigh_benard_convection/mesh_80_measurement.yaml:11:case_id: rayleigh_benard_convection
ui/backend/tests/fixtures/runs/rayleigh_benard_convection/mesh_40_measurement.yaml:11:case_id: rayleigh_benard_convection
ui/backend/tests/fixtures/runs/rayleigh_benard_convection/audit_real_run_measurement.yaml:3:#   EXECUTOR_MODE=foam_agent .venv/bin/python scripts/phase5_audit_run.py rayleigh_benard_convection
ui/backend/tests/fixtures/runs/rayleigh_benard_convection/audit_real_run_measurement.yaml:17:case_id: rayleigh_benard_convection
ui/backend/tests/fixtures/runs/rayleigh_benard_convection/audit_real_run_measurement.yaml:22:  run_id: audit_rayleigh_benard_convection_547002a
ui/backend/tests/fixtures/runs/rayleigh_benard_convection/audit_real_run_measurement.yaml:46:  manifest_path_rel: reports/phase5_fields/rayleigh_benard_convection/runs/audit_real_run.json
ui/backend/tests/fixtures/runs/rayleigh_benard_convection/reference_pass_measurement.yaml:1:# Reference-pass run for rayleigh_benard_convection at Ra=1e7.
ui/backend/tests/fixtures/runs/rayleigh_benard_convection/reference_pass_measurement.yaml:18:case_id: rayleigh_benard_convection
ui/backend/tests/fixtures/runs/rayleigh_benard_convection/mesh_20_measurement.yaml:11:case_id: rayleigh_benard_convection

exec
/bin/zsh -lc "nl -ba ui/backend/tests/fixtures/runs/rayleigh_benard_convection/audit_real_run_measurement.yaml | sed -n '1,180p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
exec
/bin/zsh -lc "nl -ba ui/backend/tests/fixtures/runs/differential_heated_cavity/audit_real_run_measurement.yaml | sed -n '1,180p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
     1	# Phase 5a audit-real-run fixture — AUTO-GENERATED, DO NOT HAND-EDIT.
     2	# Regenerate via:
     3	#   EXECUTOR_MODE=foam_agent .venv/bin/python scripts/phase5_audit_run.py rayleigh_benard_convection
     4	# This fixture backs the signed audit package. Byte-identity across
     5	# re-runs (modulo timestamp + commit_sha) is enforced by
     6	# test_phase5_byte_repro.py.
     7	
     8	run_metadata:
     9	  run_id: audit_real_run
    10	  label_zh: 真实 solver 审计运行
    11	  label_en: Real solver audit run
    12	  description_zh: FoamAgentExecutor 驱动 OpenFOAM 实际跑出的结果（commit 547002a）。这是 audit package
    13	    背书的权威测量——不是合成 fixture。失败的话说明 case 本身的 physics_contract 在当前 mesh 预算下无法满足，不是 harness
    14	    bug；会进入 audit_concerns 随包交付给审查方。
    15	  category: audit_real_run
    16	  expected_verdict: FAIL
    17	case_id: rayleigh_benard_convection
    18	source: phase5_audit_run_foam_agent
    19	measurement:
    20	  value: 26.396975806451643
    21	  unit: dimensionless
    22	  run_id: audit_rayleigh_benard_convection_547002a
    23	  commit_sha: 547002a
    24	  measured_at: '2026-04-21T15:29:41Z'
    25	  quantity: nusselt_number
    26	  extraction_source: comparator_deviation
    27	  solver_success: true
    28	  comparator_passed: false
    29	audit_concerns:
    30	- concern_type: CONTRACT_STATUS
    31	  summary: 'Quantity: nusselt_number | Tolerance: 15.0% | Failed: 1 deviation(s)'
    32	  detail: 'Quantity: nusselt_number | Tolerance: 15.0% | Failed: 1 deviation(s)'
    33	  decision_refs:
    34	  - DEC-V61-028
    35	- concern_type: DEVIATIONS
    36	  summary: 1 deviation(s) over tolerance
    37	  detail: 'nusselt_number: actual=26.396975806451643 expected=10.5'
    38	  decision_refs:
    39	  - DEC-V61-028
    40	decisions_trail:
    41	- decision_id: DEC-V61-028
    42	  date: '2026-04-21'
    43	  title: Phase 5a audit pipeline — real-solver fixtures
    44	  autonomous: true
    45	field_artifacts:
    46	  manifest_path_rel: reports/phase5_fields/rayleigh_benard_convection/runs/audit_real_run.json
    47	  run_label: audit_real_run

 succeeded in 0ms:
     1	# Phase 5a audit-real-run fixture — AUTO-GENERATED, DO NOT HAND-EDIT.
     2	# Regenerate via:
     3	#   EXECUTOR_MODE=foam_agent .venv/bin/python scripts/phase5_audit_run.py differential_heated_cavity
     4	# This fixture backs the signed audit package. Byte-identity across
     5	# re-runs (modulo timestamp + commit_sha) is enforced by
     6	# test_phase5_byte_repro.py.
     7	
     8	run_metadata:
     9	  run_id: audit_real_run
    10	  label_zh: 真实 solver 审计运行
    11	  label_en: Real solver audit run
    12	  description_zh: FoamAgentExecutor 驱动 OpenFOAM 实际跑出的结果（commit 63e915e）。这是 audit package
    13	    背书的权威测量——不是合成 fixture。失败的话说明 case 本身的 physics_contract 在当前 mesh 预算下无法满足，不是 harness
    14	    bug；会进入 audit_concerns 随包交付给审查方。
    15	  category: audit_real_run
    16	  expected_verdict: PASS
    17	  actual_verdict: PASS
    18	case_id: differential_heated_cavity
    19	source: phase5_audit_run_foam_agent
    20	measurement:
    21	  value: 8.838721264368287
    22	  unit: dimensionless
    23	  run_id: audit_differential_heated_cavity_63e915e
    24	  commit_sha: 63e915e
    25	  measured_at: '2026-04-25T09:03:03Z'
    26	  quantity: nusselt_number
    27	  extraction_source: key_quantities_direct
    28	  solver_success: true
    29	  comparator_passed: true
    30	audit_concerns:
    31	- concern_type: CONTRACT_STATUS
    32	  summary: 'Quantity: nusselt_number | Tolerance: 10.0% | PASS'
    33	  detail: 'Quantity: nusselt_number | Tolerance: 10.0% | PASS'
    34	  decision_refs:
    35	  - DEC-V61-028
    36	decisions_trail:
    37	- decision_id: DEC-V61-028
    38	  date: '2026-04-21'
    39	  title: Phase 5a audit pipeline — real-solver fixtures
    40	  autonomous: true
    41	- decision_id: DEC-V61-036
    42	  date: '2026-04-22'
    43	  title: Hard comparator gate G1 (missing-target-quantity)
    44	  autonomous: true
    45	attestation:
    46	  overall: ATTEST_NOT_APPLICABLE
    47	  checks: []
    48	field_artifacts:
    49	  manifest_path_rel: reports/phase5_fields/differential_heated_cavity/runs/audit_real_run.json
    50	  run_label: audit_real_run

exec
/bin/zsh -lc 'rg -n "secondary_scalars:" ui/backend/tests/fixtures/runs/rayleigh_benard_convection -n' in /Users/Zhuanz/Desktop/cfd-s4-rbc
 exited 1 in 0ms:
exec
/bin/zsh -lc "python - <<'PY'
from ui.backend.services.comparison_report import build_report_context
ctx = build_report_context('rayleigh_benard_convection', 'audit_real_run')
print('metrics_rbc present:', ctx.get('metrics_rbc') is not None)
if ctx.get('metrics_rbc'):
    print(ctx['metrics_rbc'])
PY" in /Users/Zhuanz/Desktop/cfd-s4-rbc
exec
/bin/zsh -lc "nl -ba knowledge/gold_standards/differential_heated_cavity.yaml | sed -n '1,120p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 exited 127 in 0ms:
zsh:1: command not found: python

 succeeded in 0ms:
     1	schema_version: 2
     2	case_id: differential_heated_cavity
     3	source: "de Vahl Davis 1983"
     4	literature_doi: "10.1002/fld.1650030305"
     5	physics_contract:
     6	  geometry_assumption: "Square 2D cavity (AR=1), opposing vertical walls at T_hot and T_cold, adiabatic top/bottom walls, Boussinesq approximation"
     7	  reference_correlation_context: "REGIME CORRECTION (Gate Q-new Case 6 · Path P-2, 2026-04-20): downgraded from Ra=1e10 to Ra=1e6, the canonical de Vahl Davis 1983 benchmark. At Ra=1e6, Pr=0.71, AR=1.0: Nu_avg(hot wall) = 8.800 (de Vahl Davis 1983 Table IV, referenced by >40 subsequent studies all within ±0.2%). The Ra=1e6 regime has BL thickness δ/L ~ Ra^(-0.25) ≈ 0.032, requiring only 5-10 cells inside the BL per wall — comfortably resolvable on adapter's 40-80-cell wall-normal mesh."
     8	  physics_precondition:
     9	    - condition: "Mesh resolves the thermal boundary layer at target Ra=1e6"
    10	      satisfied_by_current_adapter: true
    11	      evidence_ref: "At Ra=1e6, δ_T/L ≈ 0.032 → 5-10 BL cells at 40-80 wall-normal cells is sufficient. Adapter mesh per STATE.md: 80 y-cells with wall grading, comfortably within resolution requirements. Compare to the previous Ra=1e10 requirement (~1000 wall-normal cells) which was infeasible."
    12	    - condition: "Solver supports buoyancy-driven flow with Boussinesq density coupling at Ra=1e6 (laminar steady-convective regime)"
    13	      satisfied_by_current_adapter: true
    14	      evidence_ref: "buoyantBoussinesqSimpleFoam (or equivalent) with laminar turbulence model per whitelist DEC-V61-006. Ra=1e6 is well below turbulent onset (~Ra=1.5e8), so laminar+SIMPLE steady is the canonical configuration."
    15	    - condition: "Extractor methodology (mean-over-y wall-adjacent gradient) aligns with gold ref_value definition (wall-averaged hot-wall Nu)"
    16	      satisfied_by_current_adapter: true
    17	      evidence_ref: "EX-1-008 commit 60952b6 landed the mean-over-y refactor; behavior unchanged by Ra downgrade."
    18	  contract_status: >
    19	    SATISFIED — Ra=1e6 downgrade (Path P-2) simultaneously closes three prior
    20	    open issues: (1) mesh-resolution precondition (~1000 cells infeasible →
    21	    40-80 cells sufficient); (2) gold-reference accuracy (de Vahl Davis Nu=8.800
    22	    is unambiguous benchmark, vs. the contested Nu=30@Ra=1e10 value); (3) Q-1
    23	    hard-floor from DEC-ADWM-004 FUSE closes with this same edit. The
    24	    measurement gap between adapter and gold is now a simple mesh/scheme
    25	    convergence question, not a correctness question.
    26	  precondition_last_reviewed: "2026-04-20 (DEC-V61-006 B-class gold remediation · Gate Q-new Case 6 Path P-2 · closes Q-1)"
    27	note: >
    28	  Historical Ra=1e10 configuration (Nu=30 gold, never-resolved mesh) is
    29	  retired by DEC-V61-006. Recovery requires git revert -m 1 of PR #6 merge.
    30	  Phase 7 legacy Docker cache warning below still applies to adapter behaviour:
    31	
    32	  Docker E2E (Phase 7, 2026-04-16) crashed at "Starting time loop" with
    33	  "Unknown function type cellCentre" before iteration. The adapter code was
    34	  already corrected to use writeCellCentres (line 4422). The Docker run used
    35	  an older cached adapter version. Rerunning with current adapter should resolve.
    36	observables:
    37	  # ─── HEADLINE GATE ──────────────────────────────────────────────
    38	  - name: nusselt_number
    39	    description: wall-averaged Nusselt number for the hot wall at Ra = 1e6 (de Vahl Davis 1983 benchmark)
    40	    ref_value: 8.8
    41	    unit: dimensionless
    42	    tolerance:
    43	      mode: relative
    44	      value: 0.10
    45	    gate_status: HARD_GATED
    46	    family: wall_gradient_derived
    47	    extractor: src.foam_agent_adapter._extract_nc_nusselt
    48	    role: HEADLINE
    49	    source_table: "de Vahl Davis 1983 Table IV"
    50	
    51	  # ─── DEC-V61-057 Stage C · multi-dim observable expansion ───────
    52	  # Added per intake §3 + §C: 3 HARD_GATED + 1 PROVISIONAL_ADVISORY.
    53	  # Tolerances per intake §B (B.1 7%, B.2 5%, B.3 8%).
    54	
    55	  - name: nusselt_max
    56	    description: peak local Nusselt along the hot wall at y/L ≈ 0.0378 (de Vahl Davis 1983 Table III)
    57	    ref_value: 17.925
    58	    unit: dimensionless
    59	    tolerance:
    60	      mode: relative
    61	      value: 0.07
    62	    gate_status: HARD_GATED
    63	    family: wall_gradient_derived
    64	    extractor: src.dhc_extractors.extract_nu_max
    65	    role: SAME_SURFACE_CROSS_CHECK
    66	    source_table: "de Vahl Davis 1983 Table III"
    67	
    68	  - name: u_max_centerline_v
    69	    description: peak |u_x| sampled along the x=L/2 vertical mid-plane, non-dim u·L/α (de Vahl Davis 1983 Table II Run 4)
    70	    ref_value: 64.63
    71	    unit: dimensionless
    72	    tolerance:
    73	      mode: relative
    74	      value: 0.05
    75	    gate_status: HARD_GATED
    76	    family: interior_velocity_profile
    77	    extractor: src.dhc_extractors.extract_u_max_vertical
    78	    role: INDEPENDENT_CROSS_CHECK
    79	    source_table: "de Vahl Davis 1983 Table II Run 4"
    80	
    81	  - name: v_max_centerline_h
    82	    description: peak |u_y| sampled along the y=L/2 horizontal mid-plane, non-dim v·L/α (de Vahl Davis 1983 Table II Run 4)
    83	    ref_value: 219.36
    84	    unit: dimensionless
    85	    tolerance:
    86	      mode: relative
    87	      value: 0.05
    88	    gate_status: HARD_GATED
    89	    family: interior_velocity_profile
    90	    extractor: src.dhc_extractors.extract_v_max_horizontal
    91	    role: INDEPENDENT_CROSS_CHECK
    92	    source_table: "de Vahl Davis 1983 Table II Run 4"
    93	
    94	  - name: psi_max_center
    95	    description: peak |ψ| via trapezoidal ∫ u_x dy reconstruction, non-dim ψ_raw/α (de Vahl Davis 1983 Table I Run 4)
    96	    ref_value: 16.750
    97	    unit: dimensionless
    98	    tolerance:
    99	      mode: relative
   100	      value: 0.08
   101	    gate_status: PROVISIONAL_ADVISORY
   102	    family: stream_function_derived
   103	    extractor: src.dhc_extractors.extract_psi_max
   104	    role: ADVISORY_RECONSTRUCTION
   105	    source_table: "de Vahl Davis 1983 Table I Run 4"
   106	    advisory_rationale: |
   107	      ψ is reconstructed by cumulative trapezoidal ∫_0^y u_x dy with the
   108	      no-slip bottom-wall BC. Closure residual at the top wall (which
   109	      should be 0 by mass conservation) measures the integration noise
   110	      floor. The extractor demotes the value from HARD_GATED to
   111	      PROVISIONAL_ADVISORY when closure_residual_max_nondim /
   112	      |PSI_MAX_GOLD_NONDIM| ≥ 0.01 (1 %). PROVISIONAL_ADVISORY observables
   113	      are reported by the comparator but are NOT counted toward the
   114	      pass-fraction overall verdict.

exec
/bin/zsh -lc 'pytest -q ui/backend/tests/test_comparison_report_visual_only.py' in /Users/Zhuanz/Desktop/cfd-s4-rbc
 exited 2 in 368ms:
============================= test session starts ==============================
platform darwin -- Python 3.11.15, pytest-9.0.2, pluggy-1.6.0
rootdir: /Users/Zhuanz/Desktop/cfd-s4-rbc
configfile: pyproject.toml
plugins: anyio-4.13.0
collected 0 items / 1 error

==================================== ERRORS ====================================
___ ERROR collecting ui/backend/tests/test_comparison_report_visual_only.py ____
ImportError while importing test module '/Users/Zhuanz/Desktop/cfd-s4-rbc/ui/backend/tests/test_comparison_report_visual_only.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/homebrew/Cellar/python@3.11/3.11.15/Frameworks/Python.framework/Versions/3.11/lib/python3.11/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
ui/backend/tests/test_comparison_report_visual_only.py:18: in <module>
    from ui.backend.main import app
E   ModuleNotFoundError: No module named 'ui'
=========================== short test summary info ============================
ERROR ui/backend/tests/test_comparison_report_visual_only.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
=============================== 1 error in 0.19s ===============================

codex
The first test invocation exposed an environment detail, not a product issue: plain `pytest` here doesn’t resolve the repo package path (`ModuleNotFoundError: ui`). I’m switching to the repo interpreter / import path the project actually expects before drawing any conclusions from test coverage.
exec
/bin/zsh -lc 'which python3 && python3 --version && ls -d .venv 2>/dev/null || true' in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
/usr/bin/python3
Python 3.9.6
.venv

exec
/bin/zsh -lc "PYTHONPATH=. python3 - <<'PY'
from ui.backend.services.comparison_report import build_report_context
ctx = build_report_context('rayleigh_benard_convection', 'audit_real_run')
print('metrics_rbc present:', ctx.get('metrics_rbc') is not None)
if ctx.get('metrics_rbc'):
    for o in ctx['metrics_rbc']['observables']:
        print(o)
    print('counts', ctx['metrics_rbc']['hard_gated_count'], ctx['metrics_rbc']['invariant_count'], ctx['metrics_rbc']['advisory_count'])
PY" in /Users/Zhuanz/Desktop/cfd-s4-rbc
exec
/bin/zsh -lc 'PYTHONPATH=. python3 -m pytest -q ui/backend/tests/test_comparison_report_visual_only.py' in /Users/Zhuanz/Desktop/cfd-s4-rbc
 exited 1 in 128ms:
Traceback (most recent call last):
  File "/Users/Zhuanz/Desktop/cfd-s4-rbc/ui/backend/services/comparison_report.py", line 1205, in build_report_context
    artifact_dir.resolve(strict=True).relative_to(
  File "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/pathlib.py", line 1205, in resolve
    s = self._flavour.resolve(self, strict=strict)
  File "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/pathlib.py", line 363, in resolve
    return _resolve(base, str(path)) or sep
  File "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/pathlib.py", line 347, in _resolve
    target = accessor.readlink(newpath)
  File "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/pathlib.py", line 452, in readlink
    return os.readlink(path)
FileNotFoundError: [Errno 2] No such file or directory: '/Users/Zhuanz/Desktop/cfd-s4-rbc/reports/phase5_fields/rayleigh_benard_convection/20260421T142559Z'

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "<stdin>", line 2, in <module>
  File "/Users/Zhuanz/Desktop/cfd-s4-rbc/ui/backend/services/comparison_report.py", line 1209, in build_report_context
    raise ReportError(f"artifact dir escapes fields root: {artifact_dir}")
ui.backend.services.comparison_report.ReportError: artifact dir escapes fields root: /Users/Zhuanz/Desktop/cfd-s4-rbc/reports/phase5_fields/rayleigh_benard_convection/20260421T142559Z

 exited 2 in 825ms:
============================= test session starts ==============================
platform darwin -- Python 3.9.6, pytest-7.4.4, pluggy-1.6.0
rootdir: /Users/Zhuanz/Desktop/cfd-s4-rbc
configfile: pyproject.toml
plugins: anyio-4.12.1, asyncio-0.23.5, mock-3.15.1, cov-4.1.0
asyncio: mode=strict
collected 0 items / 1 error

==================================== ERRORS ====================================
___ ERROR collecting ui/backend/tests/test_comparison_report_visual_only.py ____
ui/backend/tests/test_comparison_report_visual_only.py:18: in <module>
    from ui.backend.main import app
ui/backend/main.py:46: in <module>
    from ui.backend.routes import (
ui/backend/routes/case_editor.py:22: in <module>
    from ui.backend.services.case_drafts import (
ui/backend/services/case_drafts.py:38: in <module>
    @dataclass(slots=True)
E   TypeError: dataclass() got an unexpected keyword argument 'slots'
=========================== short test summary info ============================
ERROR ui/backend/tests/test_comparison_report_visual_only.py - TypeError: dat...
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
=============================== 1 error in 0.54s ===============================

exec
/bin/zsh -lc './.venv/bin/python --version' in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
Python 3.12.13

exec
/bin/zsh -lc "PYTHONPATH=. ./.venv/bin/python - <<'PY'
from ui.backend.services.comparison_report import build_report_context, ReportError
try:
    ctx = build_report_context('rayleigh_benard_convection', 'audit_real_run')
    print('metrics_rbc present:', ctx.get('metrics_rbc') is not None)
    if ctx.get('metrics_rbc'):
        for o in ctx['metrics_rbc']['observables']:
            print(o)
        print('counts', ctx['metrics_rbc']['hard_gated_count'], ctx['metrics_rbc']['invariant_count'], ctx['metrics_rbc']['advisory_count'])
except ReportError as e:
    print('ReportError:', e)
PY" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
ReportError: artifact dir escapes fields root: /Users/Zhuanz/Desktop/cfd-s4-rbc/reports/phase5_fields/rayleigh_benard_convection/20260421T142559Z

exec
/bin/zsh -lc 'PYTHONPATH=. ./.venv/bin/python -m pytest -q ui/backend/tests/test_comparison_report_visual_only.py' in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 689ms:
============================= test session starts ==============================
platform darwin -- Python 3.12.13, pytest-9.0.3, pluggy-1.6.0
rootdir: /Users/Zhuanz/Desktop/cfd-s4-rbc
configfile: pyproject.toml
plugins: anyio-4.13.0
collected 16 items

ui/backend/tests/test_comparison_report_visual_only.py ................  [100%]

============================== 16 passed in 0.49s ==============================

exec
/bin/zsh -lc "rg -n \"def _build_visual_only_context|def build_report_context|_build_visual_only_context\\(\" ui/backend/services/comparison_report.py" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
645:def _build_visual_only_context(
1178:def build_report_context(case_id: str, run_label: str = "audit_real_run", *, for_pdf: bool = False) -> dict:
1215:        return _build_visual_only_context(case_id, run_label, timestamp, artifact_dir, for_pdf=for_pdf)

exec
/bin/zsh -lc "nl -ba ui/backend/services/comparison_report.py | sed -n '1180,1265p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
  1180	
  1181	    for_pdf: when True, the `renders.*_png` fields carry repo-relative
  1182	    paths (e.g. reports/phase5_renders/...) that WeasyPrint resolves
  1183	    against base_url=_REPO_ROOT. When False (default), those fields
  1184	    carry absolute HTTP URLs to the /api/cases/.../renders/{file}
  1185	    route so the HTML served at /api/cases/.../comparison-report
  1186	    actually displays images in a browser — without this, img srcs
  1187	    were resolved against the report URL and 404'd (2026-04-23
  1188	    user-reported bug).
  1189	    """
  1190	    if case_id not in _REPORT_SUPPORTED_CASES:
  1191	        raise ReportError(
  1192	            f"case_id={case_id!r} not in Phase 7 report scope. "
  1193	            f"Supported: {sorted(_REPORT_SUPPORTED_CASES)}."
  1194	        )
  1195	
  1196	    run_manifest = _load_run_manifest(case_id, run_label)
  1197	    timestamp = _validated_timestamp(run_manifest.get("timestamp"))
  1198	    if timestamp is None:
  1199	        raise ReportError(
  1200	            f"invalid timestamp in run manifest for {case_id}/{run_label}"
  1201	        )
  1202	    artifact_dir = _FIELDS_ROOT / case_id / timestamp
  1203	    # Containment: must be inside _FIELDS_ROOT/case_id/ even after .resolve().
  1204	    try:
  1205	        artifact_dir.resolve(strict=True).relative_to(
  1206	            (_FIELDS_ROOT / case_id).resolve()
  1207	        )
  1208	    except (ValueError, OSError, FileNotFoundError):
  1209	        raise ReportError(f"artifact dir escapes fields root: {artifact_dir}")
  1210	    if not artifact_dir.is_dir():
  1211	        raise ReportError(f"artifact dir missing: {artifact_dir}")
  1212	
  1213	    # Tier C: visual-only cases skip gold-overlay / verdict / GCI assembly.
  1214	    if case_id in _VISUAL_ONLY_CASES:
  1215	        return _build_visual_only_context(case_id, run_label, timestamp, artifact_dir, for_pdf=for_pdf)
  1216	
  1217	    # Load + compute
  1218	    gold_y, gold_u, gold_doc = _load_ldc_gold()
  1219	    tolerance = float(gold_doc.get("tolerance", 0.05)) * 100.0  # fraction → percent
  1220	    latest_sample = _latest_sample_iter(artifact_dir)
  1221	    y_sim, u_sim = _load_sample_xy(latest_sample / "uCenterline.xy")
  1222	    metrics = _compute_metrics(y_sim, u_sim, gold_y, gold_u, tolerance)
  1223	
  1224	    # DEC-V61-050 batch 1: v_centerline second observable (Ghia Table II).
  1225	    # Best-effort: silently skip if gold block missing, xy file missing,
  1226	    # or sample file malformed (e.g., old fixtures predating the v
  1227	    # sampler). The u path above must work; v is additive evidence.
  1228	    metrics_v: dict[str, Any] | None = None
  1229	    v_tolerance: float | None = None
  1230	    v_gold_pair = _load_ldc_v_gold()
  1231	    if v_gold_pair is not None:
  1232	        gold_x, gold_v, v_doc = v_gold_pair
  1233	        v_tolerance = float(v_doc.get("tolerance", 0.05)) * 100.0
  1234	        v_xy_path = latest_sample / "vCenterline.xy"
  1235	        if v_xy_path.is_file():
  1236	            try:
  1237	                # v observable is U_y; in OF native xy format that is col 2.
  1238	                x_sim, v_sim = _load_sample_xy(v_xy_path, value_col=2)
  1239	                metrics_v = _compute_metrics(x_sim, v_sim, gold_x, gold_v, v_tolerance)
  1240	            except ReportError:
  1241	                metrics_v = None
  1242	
  1243	    # DEC-V61-050 batches 3 + 4: primary vortex + secondary vortices via
  1244	    # ψ on a resampling of the audit VTK. Share the ψ grid + VTK-read
  1245	    # between both dimensions (one integration, two argmin windows) so
  1246	    # the cache hit stays warm.
  1247	    #
  1248	    # Codex round 1 MEDs: (a) widen exception envelope — pyvista/VTK can
  1249	    # raise RuntimeError/TypeError/KeyError/etc. beyond ImportError+OSError
  1250	    # +ValueError, so catch Exception here (this is an optional viz
  1251	    # dimension, not a critical path). (b) compute ψ wall-closure
  1252	    # residuals so the UI can flag when the observable scale is
  1253	    # dwarfed by numerical noise (especially secondary eddies ψ ~1e-6
  1254	    # vs typical wall residual ~1e-3 on 129² trapezoidal).
  1255	    metrics_primary_vortex: dict[str, Any] | None = None
  1256	    metrics_secondary_vortices: dict[str, Any] | None = None
  1257	    psi_wall_residuals: dict[str, Any] | None = None
  1258	    vortex_gold = _load_ldc_vortex_gold()
  1259	    secondary_gold = _load_ldc_secondary_vortices_gold()
  1260	    if vortex_gold is not None or secondary_gold is not None:
  1261	        try:
  1262	            from ui.backend.services.psi_extraction import (
  1263	                compute_streamfunction_from_vtk,
  1264	                find_vortex_core,
  1265	                pick_latest_internal_vtk,

exec
/bin/zsh -lc "PYTHONPATH=. ./.venv/bin/python - <<'PY'
from ui.backend.services.comparison_report import _build_visual_only_context
ctx = _build_visual_only_context('rayleigh_benard_convection', 'audit_real_run', '20260421T142559Z', {}, {}, '547002a')
print(ctx['metrics_rbc'])
PY" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 exited 1 in 0ms:
Traceback (most recent call last):
  File "<stdin>", line 2, in <module>
TypeError: _build_visual_only_context() takes 4 positional arguments but 6 were given

exec
/bin/zsh -lc "nl -ba ui/backend/services/comparison_report.py | sed -n '640,700p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
   640	# ---------------------------------------------------------------------------
   641	# Public API
   642	# ---------------------------------------------------------------------------
   643	
   644	
   645	def _build_visual_only_context(
   646	    case_id: str, run_label: str, timestamp: str, artifact_dir: Path,
   647	    *, for_pdf: bool = False,
   648	) -> dict:
   649	    """Tier C reduced context (DEC-V61-034): real contour + residuals PNGs from
   650	    the captured OpenFOAM artifacts, no gold overlay / verdict / GCI. The
   651	    frontend + template detect ``visual_only: True`` and suppress the
   652	    gold-dependent sections.
   653	    """
   654	    renders_manifest = _load_renders_manifest(case_id, run_label)
   655	    renders_dir = _RENDERS_ROOT / case_id / timestamp
   656	
   657	    def _rel(key: str, default: str = "") -> str:
   658	        candidate: Optional[str] = None
   659	        if renders_manifest:
   660	            raw = renders_manifest.get("outputs", {}).get(key)
   661	            if isinstance(raw, str):
   662	                validated = _safe_rel_under(raw, _RENDERS_ROOT)
   663	                if validated:
   664	                    candidate = validated
   665	        if candidate is None and default:
   666	            guess = renders_dir / default
   667	            if guess.is_file():
   668	                try:
   669	                    rel = str(guess.resolve().relative_to(_REPO_ROOT.resolve()))
   670	                    if _safe_rel_under(rel, _RENDERS_ROOT):
   671	                        candidate = rel
   672	                except ValueError:
   673	                    pass
   674	        return candidate or ""
   675	
   676	    # _rel = repo-relative path (PDF base_url=_REPO_ROOT resolves it).
   677	    # _url = browser URL (HTML served at /api/... needs an absolute path
   678	    # that hits the working renders route — repo-relative paths would
   679	    # otherwise resolve against the /api/cases/... URL and 404).
   680	    def _url(basename: str) -> str:
   681	        return f"/api/cases/{case_id}/runs/{run_label}/renders/{basename}"
   682	
   683	    renders = {
   684	        "contour_png_rel": _rel("contour_u_magnitude_png", "contour_u_magnitude.png"),
   685	        "residuals_png_rel": _rel("residuals_png", "residuals.png"),
   686	        "contour_png_url": _url("contour_u_magnitude.png"),
   687	        "residuals_png_url": _url("residuals.png"),
   688	        # Unified field read by the template — PDF mode gets repo-rel
   689	        # paths (WeasyPrint base_url resolves them); HTML browser mode
   690	        # gets API URLs that the /renders/ route serves.
   691	        "contour_png": _rel("contour_u_magnitude_png", "contour_u_magnitude.png") if for_pdf else _url("contour_u_magnitude.png"),
   692	        "residuals_png": _rel("residuals_png", "residuals.png") if for_pdf else _url("residuals.png"),
   693	    }
   694	
   695	    # Detect solver name from which log.<solver> file exists in artifact dir.
   696	    solver = "unknown"
   697	    for cand in ("simpleFoam", "icoFoam", "pimpleFoam", "buoyantFoam"):
   698	        if (artifact_dir / f"log.{cand}").is_file():
   699	            solver = cand
   700	            break

exec
/bin/zsh -lc "PYTHONPATH=. ./.venv/bin/python - <<'PY'
from pathlib import Path
from ui.backend.services.comparison_report import _build_visual_only_context
ctx = _build_visual_only_context('rayleigh_benard_convection', 'audit_real_run', '20260421T142559Z', Path('.'))
print(ctx['metrics_rbc'])
PY" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
{'observables': [{'label': 'R-Nu_avg', 'label_zh': '底部热壁平均 Nusselt', 'symbol': 'Nu', 'name': 'nusselt_number', 'actual': 26.396975806451643, 'expected': 17.7, 'deviation_pct': 49.1354565336251, 'deviation_abs': None, 'tolerance_pct': 25.0, 'tolerance_abs': None, 'tolerance_mode': 'relative', 'within_tolerance': False, 'gate_status': 'HARD_GATED', 'family': 'wall_gradient_derived', 'role': 'HEADLINE', 'source_table': 'Pandey & Schumacher 2018 TU Ilmenau DFG SPP 1881 Benchmark Case 1, Table 1, p.6 (https://www.tu-ilmenau.de/fileadmin/Bereiche/MB/sm/DFG-Priority_Programme_1881__Turbulent_Superstructures/Benchmark_cases/Benchmark_case_1/Tutorial_RBC.pdf)'}, {'label': 'R-ΔNu/Nu', 'label_zh': '顶/底 Nu 守恒不对称', 'symbol': '|ΔNu|/Nu', 'name': 'nusselt_top_asymmetry', 'actual': None, 'expected': 0.0, 'deviation_pct': None, 'deviation_abs': None, 'tolerance_pct': None, 'tolerance_abs': 0.05, 'tolerance_mode': 'absolute', 'within_tolerance': None, 'gate_status': 'NON_TYPE_HARD_INVARIANT', 'family': 'wall_gradient_derived', 'role': 'CONSERVATION_INVARIANT', 'source_table': 'Conservation invariant (NOT a literature value); blocking on violation but excluded from primary_gate_count denominator', 'pending': True}, {'label': 'R-N_roll', 'label_zh': '底壁两胞结构计数', 'symbol': 'N_rolls', 'name': 'roll_count_x', 'actual': None, 'expected': 2.0, 'deviation_pct': None, 'deviation_abs': None, 'tolerance_pct': None, 'tolerance_abs': 0.0, 'tolerance_mode': 'absolute', 'within_tolerance': None, 'gate_status': 'PROVISIONAL_ADVISORY', 'family': 'structural', 'role': 'ADVISORY_STRUCTURAL', 'source_table': 'Pandey & Schumacher 2018 Fig 4b (instantaneous t=2250 t_f) and Fig 5 (time-averaged): two-roll structure with hot fluid rising at center and cold fluid descending at sidewalls', 'pending': True}], 'hard_gated_count': 1, 'invariant_count': 1, 'advisory_count': 1, 'source': 'Pandey & Schumacher 2018 — TU Ilmenau DFG SPP 1881 Benchmark Case 1', 'literature_doi': '', 'short': 'Pandey & Schumacher 2018 TU Ilmenau Table 1'}

exec
/bin/zsh -lc "nl -ba tests/test_auto_verifier/test_gold_standard.py | sed -n '260,310p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
   260	    }
   261	    sim = {"nusselt_number": 17.0, "nusselt_top_asymmetry": 0.0}
   262	    report = GoldStandardComparator().compare(gold, sim)
   263	    # If the invariant were counted in denom, 1/2 PASS would be
   264	    # PASS_WITH_DEVIATIONS or FAIL. With proper exclusion, 1/1 is PASS.
   265	    assert report.overall == "PASS"
   266	
   267	
   268	def test_advisory_and_invariant_coexist():
   269	    """Mixed scenario: HARD_GATED + NON_TYPE_HARD_INVARIANT + 2× PROVISIONAL_ADVISORY
   270	    (the canonical RBC Stage C contract). All four gate_statuses must be
   271	    handled correctly together."""
   272	    gold = {
   273	        "observables": [
   274	            {"name": "nusselt_number", "ref_value": 17.7,
   275	             "tolerance": {"mode": "relative", "value": 0.25},
   276	             "gate_status": "HARD_GATED"},
   277	            {"name": "nusselt_top_asymmetry", "ref_value": 0.0,
   278	             "tolerance": {"mode": "absolute", "value": 0.05},
   279	             "gate_status": "NON_TYPE_HARD_INVARIANT"},
   280	            {"name": "w_max_nondim", "ref_value": 1.5,
   281	             "tolerance": {"mode": "relative", "value": 0.20},
   282	             "gate_status": "PROVISIONAL_ADVISORY"},
   283	            {"name": "roll_count_x", "ref_value": 2,
   284	             "tolerance": {"mode": "absolute", "value": 0},
   285	             "gate_status": "PROVISIONAL_ADVISORY"},
   286	        ]
   287	    }
   288	    # All within tolerance → overall PASS, no violations
   289	    sim = {"nusselt_number": 17.0, "nusselt_top_asymmetry": 0.02,
   290	           "w_max_nondim": 1.6, "roll_count_x": 2}
   291	    report = GoldStandardComparator().compare(gold, sim)
   292	    assert report.overall == "PASS"
   293	    # Now: w_max outside advisory tolerance → still PASS but warning
   294	    sim_with_advisory_miss = dict(sim, w_max_nondim=2.5)  # 67% off
   295	    report2 = GoldStandardComparator().compare(gold, sim_with_advisory_miss)
   296	    assert report2.overall == "PASS", (
   297	        f"Advisory miss must NOT degrade verdict; got {report2.overall}"
   298	    )
   299	    assert any("advisory_observable_outside_tolerance:w_max_nondim" in w
   300	               for w in report2.warnings)

exec
/bin/zsh -lc 'rg -n "ADVISORY_NO_LITERATURE_LOCATOR|counts_toward_primary_gate_count|advisory_rationale" -S src ui tests knowledge' in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
knowledge/gold_standards/differential_heated_cavity.yaml:106:    advisory_rationale: |
knowledge/gold_standards/rayleigh_benard_convection.yaml:43:    counts_toward_primary_gate_count: true
knowledge/gold_standards/rayleigh_benard_convection.yaml:55:    counts_toward_primary_gate_count: false
knowledge/gold_standards/rayleigh_benard_convection.yaml:62:    ref_value: ADVISORY_NO_LITERATURE_LOCATOR  # BRANCH-B per intake §3 advisory_rationale
knowledge/gold_standards/rayleigh_benard_convection.yaml:67:    counts_toward_primary_gate_count: false
knowledge/gold_standards/rayleigh_benard_convection.yaml:79:    counts_toward_primary_gate_count: false
src/rbc_extractors.py:343:    "ADVISORY_NO_LITERATURE_LOCATOR" — comparator surfaces but does NOT

exec
/bin/zsh -lc "nl -ba src/rbc_extractors.py | sed -n '320,360p'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
   320	    # Reject any non-finite final result rather than emit status=ok+nan.
   321	    if not (_is_finite(nu_bottom) and _is_finite(nu_top) and _is_finite(asymmetry)):
   322	        return {}
   323	    return {
   324	        "value": asymmetry,
   325	        "nu_bottom": nu_bottom,
   326	        "nu_top": nu_top,
   327	        "column_count_bottom": len(grads_bottom),
   328	        "column_count_top": len(grads_top),
   329	        "status": "ok",
   330	    }
   331	
   332	
   333	def extract_w_max(slice_: RBCFieldSlice, bc: RBCBoundary) -> Dict[str, Any]:
   334	    """Peak vertical velocity nondim by free-fall velocity (B.2).
   335	
   336	    Definition (DEC-V61-060 §3 in_scope w_max_nondim):
   337	        U_ff = sqrt(g · β · dT · H)
   338	        raw_w_max = max |u_y| over interior cells (excluding wall layers
   339	                    to avoid the no-slip-zero contribution polluting the max)
   340	        w_max_nondim = raw_w_max / U_ff
   341	
   342	    Per intake A.0 BRANCH-B, w_max_nondim ref_value =
   343	    "ADVISORY_NO_LITERATURE_LOCATOR" — comparator surfaces but does NOT
   344	    enforce. This extractor still computes the value; the gate_status
   345	    is PROVISIONAL_ADVISORY.
   346	
   347	    "Interior" excludes cells within H/20 of either horizontal wall to
   348	    avoid biasing the max by no-slip-zero values. Pandey & Schumacher
   349	    Fig 4 shows peak |u_y| occurring well inside the cavity, not at the
   350	    wall, so this trim is benign.
   351	
   352	    Returns dict with:
   353	        - ``value``: w_max_nondim (raw / U_ff)
   354	        - ``raw_w_max``: max |u_y| in interior cells (m/s)
   355	        - ``U_ff``: free-fall velocity (m/s)
   356	        - ``interior_cell_count``: number of cells contributing to the max
   357	        - ``status``: 'ok' on success
   358	    Returns ``{}`` on missing u_vecs / shape error / U_ff = 0.
   359	    """
   360	    if slice_.u_vecs is None:

exec
/bin/zsh -lc "rg -n \"metrics_rbc|rbc_observables|rayleigh_benard_convection\" ui/backend/tests/test_comparison_report_visual_only.py ui/backend/tests -g '"'!node_modules'"'" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
ui/backend/tests/test_comparison_report_visual_only.py:80:        "rayleigh_benard_convection", "differential_heated_cavity", "duct_flow",
ui/backend/tests/test_convergence_attestor.py:373:    thresholds = load_thresholds("rayleigh_benard_convection")
ui/backend/tests/test_comparison_report_visual_only.py:80:        "rayleigh_benard_convection", "differential_heated_cavity", "duct_flow",
ui/backend/tests/test_dec039_profile_verdict_reconciliation.py:47:                 "rayleigh_benard_convection"):
ui/backend/tests/fixtures/runs/rayleigh_benard_convection/real_incident_measurement.yaml:1:# Real-incident run for rayleigh_benard_convection.
ui/backend/tests/fixtures/runs/rayleigh_benard_convection/real_incident_measurement.yaml:18:case_id: rayleigh_benard_convection
ui/backend/tests/fixtures/runs/rayleigh_benard_convection/audit_real_run_measurement.yaml:3:#   EXECUTOR_MODE=foam_agent .venv/bin/python scripts/phase5_audit_run.py rayleigh_benard_convection
ui/backend/tests/fixtures/runs/rayleigh_benard_convection/audit_real_run_measurement.yaml:17:case_id: rayleigh_benard_convection
ui/backend/tests/fixtures/runs/rayleigh_benard_convection/audit_real_run_measurement.yaml:22:  run_id: audit_rayleigh_benard_convection_547002a
ui/backend/tests/fixtures/runs/rayleigh_benard_convection/audit_real_run_measurement.yaml:46:  manifest_path_rel: reports/phase5_fields/rayleigh_benard_convection/runs/audit_real_run.json
ui/backend/tests/test_grid_convergence_monotonicity.py:48:    "rayleigh_benard_convection",
ui/backend/tests/test_case_export.py:101:        "rayleigh_benard_convection",
ui/backend/tests/fixtures/runs/rayleigh_benard_convection/reference_pass_measurement.yaml:1:# Reference-pass run for rayleigh_benard_convection at Ra=1e7.
ui/backend/tests/fixtures/runs/rayleigh_benard_convection/reference_pass_measurement.yaml:18:case_id: rayleigh_benard_convection
ui/backend/tests/fixtures/runs/rayleigh_benard_convection/mesh_20_measurement.yaml:11:case_id: rayleigh_benard_convection
ui/backend/tests/fixtures/runs/rayleigh_benard_convection/mesh_160_measurement.yaml:12:case_id: rayleigh_benard_convection
ui/backend/tests/fixtures/runs/rayleigh_benard_convection/mesh_40_measurement.yaml:11:case_id: rayleigh_benard_convection
ui/backend/tests/fixtures/runs/rayleigh_benard_convection/wrong_model_measurement.yaml:1:# Wrong-model run for rayleigh_benard_convection at Ra=1e7.
ui/backend/tests/fixtures/runs/rayleigh_benard_convection/wrong_model_measurement.yaml:18:case_id: rayleigh_benard_convection
ui/backend/tests/fixtures/runs/rayleigh_benard_convection/mesh_80_measurement.yaml:11:case_id: rayleigh_benard_convection

codex
I’ve found one concrete behavioral mismatch already by executing the backend helper against the Stage D RBC fixture: the reviewed snapshot emits only 3 RBC observables, not 4, because one advisory gold entry is filtered out before the UI ever sees it. I’m doing one last pass on the frontend and tooling surface to see if there’s any additional runtime or type-level break beyond that.
exec
/bin/zsh -lc 'cat package.json' in /Users/Zhuanz/Desktop/cfd-s4-rbc
 exited 1 in 0ms:
cat: package.json: No such file or directory

exec
/bin/zsh -lc "rg -n '\"typecheck\"|\"build\"|\"lint\"' package.json ui/frontend/package.json" in /Users/Zhuanz/Desktop/cfd-s4-rbc
 exited 2 in 0ms:
rg: package.json: No such file or directory (os error 2)
ui/frontend/package.json:9:    "build": "tsc -b && vite build",
ui/frontend/package.json:11:    "typecheck": "tsc --noEmit",
ui/frontend/package.json:12:    "lint": "eslint src --ext .ts,.tsx"

exec
/bin/zsh -lc 'rg -n "守恒不变量|INVARIANT|ADVISORY · WITHIN|ADVISORY · OUTSIDE|PENDING" ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx' in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
1417:          statusLabel = "PENDING";
1420:          statusLabel = isAdvisory ? "ADVISORY · WITHIN" : "PASS";
1423:          statusLabel = isAdvisory ? "ADVISORY · OUTSIDE" : "FAIL";
1502:    // 1 HARD_GATED + 1 NON_TYPE_HARD_INVARIANT + 2 PROVISIONAL_ADVISORY. Mirrors DHC
1511:        const isInvariant = o.gate_status === "NON_TYPE_HARD_INVARIANT";
1537:          statusLabel = "PENDING";
1540:          if (isAdvisory) { statusLabel = "ADVISORY · WITHIN"; statusColor = "text-emerald-300"; }
1541:          else if (isInvariant) { statusLabel = "INVARIANT · OK"; statusColor = "text-emerald-300"; }
1544:          if (isAdvisory) { statusLabel = "ADVISORY · OUTSIDE"; statusColor = "text-amber-300"; }
1545:          else if (isInvariant) { statusLabel = "INVARIANT · VIOLATED"; statusColor = "text-rose-300"; }
1588:                  · 守恒不变量
1640:              {rbc.short} · {rbc.hard_gated_count} HARD_GATED + {rbc.invariant_count} INVARIANT + {rbc.advisory_count} ADVISORY (Type II 底加热 RBC)
3233:  // block (1 HARD_GATED + 1 NON_TYPE_HARD_INVARIANT + 2 PROVISIONAL_ADVISORY).
3234:  // NON_TYPE_HARD_INVARIANT carries absolute tolerance (ref_value=0); UI renders

exec
/bin/zsh -lc 'ls ui/frontend' in /Users/Zhuanz/Desktop/cfd-s4-rbc
 succeeded in 0ms:
README.md
index.html
package.json
postcss.config.js
public
src
tailwind.config.ts
tsconfig.json
tsconfig.node.json
vite.config.ts

exec
/bin/zsh -lc 'cd ui/frontend && npm run typecheck' in /Users/Zhuanz/Desktop/cfd-s4-rbc
 exited 127 in 0ms:

> cfd-harness-ui-frontend@0.4.0-phase-1-to-4 typecheck
> tsc --noEmit

sh: tsc: command not found

codex
**Findings**

- `F2` [ui/backend/services/comparison_report.py](/Users/Zhuanz/Desktop/cfd-s4-rbc/ui/backend/services/comparison_report.py:419), [ui/backend/services/comparison_report.py](/Users/Zhuanz/Desktop/cfd-s4-rbc/ui/backend/services/comparison_report.py:1024), [rayleigh_benard_convection.yaml](/Users/Zhuanz/Desktop/cfd-s4-rbc/knowledge/gold_standards/rayleigh_benard_convection.yaml:62): `_load_case_observable_gold()` hard-rejects any non-numeric `ref_value`, so RBC’s `w_max_nondim` advisory sentinel (`ADVISORY_NO_LITERATURE_LOCATOR`) never reaches the UI. The RBC loop then hits `if gold is None: continue`, which drops that observable entirely. I reproduced this via `_build_visual_only_context(...)`: the commit emits only `nusselt_number`, `nusselt_top_asymmetry`, and `roll_count_x`, with `advisory_count == 1`. That breaks the stated `1 HARD_GATED + 1 INVARIANT + 2 ADVISORY` taxonomy and means the Stage D fixture does not actually show the promised 4-card surface.
  Diff suggestion: stop using `None` as “skip this observable” for non-numeric advisory refs. Return a loader payload with `expected=None` plus a flag like `has_numeric_reference=False`, and append a neutral/non-scored advisory card instead of `continue`.

- `F3` [LearnCaseDetailPage.tsx](/Users/Zhuanz/Desktop/cfd-s4-rbc/ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1586): the invariant badge color is hard-coded to rose for all states. The branch correctly sets border/status text by pass/fail, but `· 守恒不变量` stays `text-rose-300/80` even when the invariant is within tolerance or pending. That contradicts the requested semantics (“rose on violation, emerald within”) and makes a passing invariant look failed-ish.
  Diff suggestion: compute the badge class from `isPending` / `failing` / `passing`, e.g. neutral for pending, rose for violated, emerald for within tolerance.

**Checked Items**

- DHC backward-compat shim looks correct: [ui/backend/services/comparison_report.py](/Users/Zhuanz/Desktop/cfd-s4-rbc/ui/backend/services/comparison_report.py:444) still restores the legacy de Vahl Davis source/DOI defaults when the generalized loader returns empty strings.
- Invariant denominator semantics are represented correctly in the UI copy and counts: [LearnCaseDetailPage.tsx](/Users/Zhuanz/Desktop/cfd-s4-rbc/ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1587), [ui/backend/services/comparison_report.py](/Users/Zhuanz/Desktop/cfd-s4-rbc/ui/backend/services/comparison_report.py:1111).
- The absolute-tolerance branch is null-safe; I do not see a `toFixed()` throw path in [LearnCaseDetailPage.tsx](/Users/Zhuanz/Desktop/cfd-s4-rbc/ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1552).
- Pending cards do not create a false PASS signal; counts here are taxonomy counts, not pass counts. The real pending-related problem is the dropped `w_max_nondim` card.

**Verdict**

`CHANGES_REQUIRED`

Backend verification I ran: `PYTHONPATH=. ./.venv/bin/python -m pytest -q ui/backend/tests/test_comparison_report_visual_only.py` passed. Frontend typecheck was not runnable in this workspace because `ui/frontend` is missing local `tsc` (`npm run typecheck` -> `sh: tsc: command not found`).
tokens used
86,565
**Findings**

- `F2` [ui/backend/services/comparison_report.py](/Users/Zhuanz/Desktop/cfd-s4-rbc/ui/backend/services/comparison_report.py:419), [ui/backend/services/comparison_report.py](/Users/Zhuanz/Desktop/cfd-s4-rbc/ui/backend/services/comparison_report.py:1024), [rayleigh_benard_convection.yaml](/Users/Zhuanz/Desktop/cfd-s4-rbc/knowledge/gold_standards/rayleigh_benard_convection.yaml:62): `_load_case_observable_gold()` hard-rejects any non-numeric `ref_value`, so RBC’s `w_max_nondim` advisory sentinel (`ADVISORY_NO_LITERATURE_LOCATOR`) never reaches the UI. The RBC loop then hits `if gold is None: continue`, which drops that observable entirely. I reproduced this via `_build_visual_only_context(...)`: the commit emits only `nusselt_number`, `nusselt_top_asymmetry`, and `roll_count_x`, with `advisory_count == 1`. That breaks the stated `1 HARD_GATED + 1 INVARIANT + 2 ADVISORY` taxonomy and means the Stage D fixture does not actually show the promised 4-card surface.
  Diff suggestion: stop using `None` as “skip this observable” for non-numeric advisory refs. Return a loader payload with `expected=None` plus a flag like `has_numeric_reference=False`, and append a neutral/non-scored advisory card instead of `continue`.

- `F3` [LearnCaseDetailPage.tsx](/Users/Zhuanz/Desktop/cfd-s4-rbc/ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1586): the invariant badge color is hard-coded to rose for all states. The branch correctly sets border/status text by pass/fail, but `· 守恒不变量` stays `text-rose-300/80` even when the invariant is within tolerance or pending. That contradicts the requested semantics (“rose on violation, emerald within”) and makes a passing invariant look failed-ish.
  Diff suggestion: compute the badge class from `isPending` / `failing` / `passing`, e.g. neutral for pending, rose for violated, emerald for within tolerance.

**Checked Items**

- DHC backward-compat shim looks correct: [ui/backend/services/comparison_report.py](/Users/Zhuanz/Desktop/cfd-s4-rbc/ui/backend/services/comparison_report.py:444) still restores the legacy de Vahl Davis source/DOI defaults when the generalized loader returns empty strings.
- Invariant denominator semantics are represented correctly in the UI copy and counts: [LearnCaseDetailPage.tsx](/Users/Zhuanz/Desktop/cfd-s4-rbc/ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1587), [ui/backend/services/comparison_report.py](/Users/Zhuanz/Desktop/cfd-s4-rbc/ui/backend/services/comparison_report.py:1111).
- The absolute-tolerance branch is null-safe; I do not see a `toFixed()` throw path in [LearnCaseDetailPage.tsx](/Users/Zhuanz/Desktop/cfd-s4-rbc/ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1552).
- Pending cards do not create a false PASS signal; counts here are taxonomy counts, not pass counts. The real pending-related problem is the dropped `w_max_nondim` card.

**Verdict**

`CHANGES_REQUIRED`

Backend verification I ran: `PYTHONPATH=. ./.venv/bin/python -m pytest -q ui/backend/tests/test_comparison_report_visual_only.py` passed. Frontend typecheck was not runnable in this workspace because `ui/frontend` is missing local `tsc` (`npm run typecheck` -> `sh: tsc: command not found`).
