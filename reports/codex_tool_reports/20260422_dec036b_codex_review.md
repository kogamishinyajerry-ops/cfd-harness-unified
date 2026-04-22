2026-04-22T10:43:36.182693Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-research-deerflow/SKILL.md: missing YAML frontmatter delimited by ---
2026-04-22T10:43:36.182715Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-report-pretext/SKILL.md: missing YAML frontmatter delimited by ---
OpenAI Codex v0.118.0 (research preview)
--------
workdir: /Users/Zhuanz/Desktop/cfd-harness-unified
model: gpt-5.4
provider: openai
approval: never
sandbox: read-only
reasoning effort: xhigh
reasoning summaries: none
session id: 019db4c9-d0ad-7ad2-93fd-219e7c9903d9
--------
user
# Codex Pre-merge Review — DEC-V61-036b (Gates G3/G4/G5)

**Caller**: Claude Code Opus 4.7 (v6.2 Main Driver)
**Target DEC**: DEC-V61-036b — Hard comparator gates G3 (velocity overflow), G4 (turbulence negativity), G5 (continuity divergence)
**Self-pass-rate**: 0.60 (≤0.70 triggers pre-merge Codex per RETRO-V61-001)
**Context**: Commits 1fedfd6 + c3afe93 already landed to main; DEC-V61-036b codex_verdict=pending; backfill pre-merge audit.

## Files to review

Primary (please read in full):
- `src/comparator_gates.py` (~524 LOC new CFD module)
- `scripts/phase5_audit_run.py` (integration: `_audit_fixture_doc` path, check_all_gates call)
- `ui/backend/services/validation_report.py` (`_derive_contract_status` extension for VELOCITY_OVERFLOW/TURBULENCE_NEGATIVE/CONTINUITY_DIVERGED)
- `ui/backend/tests/test_comparator_gates_g3_g4_g5.py` (~294 LOC tests)

Context (reference as needed):
- `.planning/decisions/2026-04-22_phase8_dec036b_gates_g3_g4_g5.md` (full DEC spec incl. BFS log snapshot & expected verdict table)
- `.planning/decisions/2026-04-22_phase8_dec036_hard_comparator_gates_g1.md` (G1 sibling; G3/G4/G5 are defense-in-depth layer)

## Review criteria (CFD physics + code quality)

### 1. G3 velocity_overflow correctness
- `max(|U|) > K * U_ref` with K=100 default — does this thresholding reliably catch BFS |U|≈1e4 and turbulent_flat_plate |U|≈1.1e4 without false-firing on physical high-Re cases (e.g. NACA0012 at Re=6e6 where local U can legitimately exceed 100·U∞ near leading-edge stagnation)?
- VTK-unavailable fallback uses `ε^(1/3) * L^(1/3)` to infer velocity scale from epsilon max. Verify the inference math. Is L assumed unity safe?
- Is U_ref extraction from `task_spec.boundary_conditions` robust across all 10 whitelist cases (internal flow inlet, LDC lid velocity, external free-stream, thermal buoyancy)?

### 2. G4 turbulence_negativity correctness
- Two triggers: (a) final-iter `bounding X, min: <0`; (b) field max > 1e+10 for k/epsilon.
- Early-iter bounding is healthy (solver internal); final-iter negative is not. Verify the code correctly identifies "last reported bounding" — specifically, does it parse until EOF and use the LAST `bounding X,` line for each field, not an early one?
- For laminar cases (LDC, differential_heated_cavity): no turbulence model → no bounding lines expected. Code must skip gracefully (no FAIL on absence).

### 3. G5 continuity_divergence correctness
- Thresholds: `sum_local > 1e-2` OR `|cumulative| > 1.0`. For unsteady pimpleFoam (cylinder_wake), per-step sum_local oscillates — is the gate reading the LAST step or averaging?
- Cylinder gold wake Co≈5.9 implies oscillating continuity. Does the threshold avoid false-firing on healthy unsteady runs while still catching BFS cum=-1434?

### 4. Integration in `phase5_audit_run.py`
- Is `check_all_gates` called AFTER G1 extraction but BEFORE final verdict assembly?
- Are violations stamped into `audit_concerns[]` with correct `concern_type` strings matching `_derive_contract_status` hard-FAIL set?
- Error handling: if `parse_solver_log` fails (corrupt log), does the function return empty violations (no FAIL) or raise? Spec says WARN marker — verify.

### 5. Regression guard: LDC must stay clean
- Explicit unit test `test_gates_ldc_no_fire` — does the test use real LDC log+VTK fixtures or synthetic clean data? Real data is stronger.

### 6. Threshold calibration
- Per DEC spec: K=100 default, sum_local=1e-2, cumulative=1.0, field_max=1e+10.
- Are these hardcoded magic numbers or config-driven? If hardcoded, flag as tech debt but not blocker.
- Does the test suite probe boundary conditions (e.g., U=99·U_ref should pass, U=101·U_ref should fail)?

### 7. Round-1 nit follow-up (commit c3afe93 "NaN/inf safety + within=None")
- Verify NaN/inf guards exist on all numeric comparisons (catching `bounding epsilon max: nan` gracefully)
- Verify `within=None` edge case (no u_ref available) degrades to WARN not FAIL

## Expected output format

Respond with a structured review:

```
# Codex Review Verdict — DEC-V61-036b

**Verdict**: APPROVE / APPROVE_WITH_NOTES / CHANGES_REQUIRED / BLOCK
**Self-pass-rate delta**: claude-estimated=0.60 → codex-independent=0.XX

## Findings

### Must-fix (blocker)
- [finding id] [file:line] [description] [recommended fix]

### Should-fix (nit)
- [finding id] [file:line] [description]

### Praise / good patterns
- [what's done well]

## CFD physics audit
- G3 correctness: [analysis]
- G4 correctness: [analysis]
- G5 correctness: [analysis]
- LDC regression guard: [pass/fail + evidence]
- Threshold calibration: [analysis]

## Backward-compat concerns
- [any risk that gates could flip a previously-PASS fixture to FAIL incorrectly]

## Recommendation
- Ready for codex_verdict=APPROVED: YES / NO
- If NO, what needs to change before approval: [...]
```

Be strict. This module is defense against PASS-washing across 7 of 10 whitelist cases. A false negative (gate fails to catch a blowup) reintroduces PASS-washing. A false positive (gate fires on healthy LDC) destroys the gold-overlay reference. Both outcomes are blockers.

Be thorough but concise. Target 60-150 lines output.

codex
Reviewing the four target files plus the DEC specs first, then I’ll trace each gate end-to-end against the stated CFD expectations and look for false-negative and false-positive paths.
exec
/bin/zsh -lc 'pwd && rg -n "cfd-harness-unified|Phase 8 Done|Phase 9|DEC-V61-036b|G3|G4|G5" /Users/Zhuanz/.codex/memories/MEMORY.md' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
/Users/Zhuanz/Desktop/cfd-harness-unified
224:- OpenClaw, AI-CFD, Notion作为指挥中枢，Github作为唯一代码真相库, ~/.openclaw/openclaw.json, plugins.allow, openclaw config validate --json, MAIN_OK, CODEX_BUILDER_OK, CLAUDE_REVIEW_OK, NOTION_SYNC_OK, cfd-harness-unified
244:- The real live config surface was `~/.openclaw/openclaw.json`; the actual repo truth for this rollout was `/Users/Zhuanz/Desktop/cfd-harness-unified`, not the chat thread cwd [Task 1]
465:# Task Group: cfd-harness-unified governance closeout and planning gates
467:scope: Close out accepted phases in `cfd-harness-unified`, normalize Notion-vs-repo naming drift, and keep future phases planning-only until the explicit solver/routing gate is reviewed.
468:applies_to: cwd=/Users/Zhuanz/Desktop/cfd-harness-unified; reuse_rule=safe for this repo’s Notion-governed phase/gate work, but phase/task IDs and review packets are rollout-specific.
474:- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, Phase 8 closeout and evidence normalization)
478:- Phase 8, AutoVerifier, 13/13, knowledge/whitelist.yaml, ai_cfd_cold_start_whitelist.yaml, Canonical Docs Type=Report, Phase 8 Done, naming drift
480:## Task 2: Open Phase 9 as planning-only and keep solver expansion bounded
484:- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, Phase 9 kept as planning-only with decision-tree packet))
488:- Phase 9 planning-only, PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md, PHASE9_MODEL_ROUTING_BASELINE_PLAN.md, PHASE9_ACTIVATION_REVIEW_PACKET.md, replay_manifest, SU2 CLI Harness Skill, foam_agent_adapter.py
494:- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, handoff prompt prepared instead of silent activation))
509:- Phase 9 must start from a bounded decision tree: keep single-engine OpenFOAM, allow reference-only external solver surfaces, or open one bounded proof slice; anything broader still needs review [Task 2]
515:- Symptom: planning work accidentally looks like activation -> cause: Phase 9 docs/task text are not explicit enough about `Planned` vs `Active` -> fix: state planning-only mode in phase page, tasks, dashboard summary, and review packet [Task 2]
548:- rollout_summaries/2026-04-12T15-33-54-ByPi-jerry_ai_cfd_notion_sync_and_cfd_harness_unified_context_mis.md (cwd=/Users/Zhuanz/Documents/20260330 Jerry AI CFD Project, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/12/rollout-2026-04-12T23-33-54-019d8253-fa8b-7f40-9775-46e6e03db8ac.jsonl, updated_at=2026-04-16T17:03:18+00:00, thread_id=019d8253-fa8b-7f40-9775-46e6e03db8ac, later cfd-harness-unified instruction block correctly treated as mismatch)
923:- `state_machine.py` is the canonical state-chain source (`Draft -> IntakeValidated(G0) -> KnowledgeBound(G1) -> Planned(G2) -> Running(G3) -> Verifying(G4) -> ReviewPending(G5) -> Approved -> Closed(G6)`) and should be cited before higher-level milestone claims [Task 1]
1063:## Task 5: Build gate automation from G3 through G6 and separate logic regressions from environment blockers
1067:- rollout_summaries/2026-04-07T14-35-20-Fhet-p4_07_g3_gate_automation.md (cwd=/Users/Zhuanz/Desktop/notion-cfd-harness, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/07/rollout-2026-04-07T22-35-20-019d685e-8e38-7211-b85f-48d2356e403d.jsonl, updated_at=2026-04-07T14:44:08+00:00, thread_id=019d685e-8e38-7211-b85f-48d2356e403d, G3 gate and initial environment blocker mapping)
1068:- rollout_summaries/2026-04-07T15-18-47-3FVb-p4_08_g4_g6_gate_acceptance_workflow.md (cwd=/Users/Zhuanz/Desktop/notion-cfd-harness, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/07/rollout-2026-04-07T23-18-47-019d6886-54a7-72f2-9acb-b14b8a540035.jsonl, updated_at=2026-04-07T15:38:30+00:00, thread_id=019d6886-54a7-72f2-9acb-b14b8a540035, shared gate runner plus G4/G5/G6 wrappers)
1093:- scripts/memory-network, gate trigger G3 G4 G5 G6, status, events, sync-code-mappings, version list, JSON output, SourceFileLoader, chmod +x, events_db_id is required for Memory Events Notion sync
1418:- rollout_summaries/2026-03-28T12-30-44-G47B-claude_minimax_prompt_handoff_and_official_quota_questions.md (cwd=/Users/Zhuanz/Documents/New project, rollout_path=/Users/Zhuanz/.codex/sessions/2026/03/28/rollout-2026-03-28T20-30-44-019d346c-e22b-71b2-b229-541f7f6c8397.jsonl, updated_at=2026-03-28T13:27:17+00:00, thread_id=019d346c-e22b-71b2-b229-541f7f6c8397, prompt-handoff workflow and quota-rule explanation)

exec
/bin/zsh -lc "sed -n '1,220p' /Users/Zhuanz/.codex/skills/superpowers/27651a43bf55185d924f7a1fc49043a0a8be65a0/skills/using-superpowers/SKILL.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '1,220p' /Users/Zhuanz/.agents/skills/gsd-code-review/SKILL.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
 exited 1 in 0ms:
sed: /Users/Zhuanz/.codex/skills/superpowers/27651a43bf55185d924f7a1fc49043a0a8be65a0/skills/using-superpowers/SKILL.md: No such file or directory

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
I pulled the repo-memory handle to confirm this is the Phase 8 / gate-governed `cfd-harness-unified` line of work. Now I’m reading the gate module, integration points, tests, and DEC text in full so the review stays anchored to the written acceptance contract.
Reviewing DEC-V61-036b as a strict pre-merge audit: first gather code/spec context, then trace G3/G4/G5 logic and integration, then produce severity-ranked findings with CFD-specific reasoning.
  → Load DEC specs, target files, and relevant repo memory context
  • Trace G3, G4, and G5 implementations against stated CFD expectations and edge cases
  • Check phase5 integration, concern typing, fallback/error paths, and tests
  • Summarize verdict with blocker/nit classification and evidence
exec
/bin/zsh -lc 'wc -l src/comparator_gates.py scripts/phase5_audit_run.py ui/backend/services/validation_report.py ui/backend/tests/test_comparator_gates_g3_g4_g5.py .planning/decisions/2026-04-22_phase8_dec036b_gates_g3_g4_g5.md .planning/decisions/2026-04-22_phase8_dec036_hard_comparator_gates_g1.md' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
     480 src/comparator_gates.py
     622 scripts/phase5_audit_run.py
     926 ui/backend/services/validation_report.py
     302 ui/backend/tests/test_comparator_gates_g3_g4_g5.py
     187 .planning/decisions/2026-04-22_phase8_dec036b_gates_g3_g4_g5.md
     143 .planning/decisions/2026-04-22_phase8_dec036_hard_comparator_gates_g1.md
    2660 total

exec
/bin/zsh -lc "sed -n '1,220p' .planning/decisions/2026-04-22_phase8_dec036_hard_comparator_gates_g1.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '1,220p' .planning/decisions/2026-04-22_phase8_dec036b_gates_g3_g4_g5.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
---
decision_id: DEC-V61-036
timestamp: 2026-04-22T12:00 local
scope: |
  Phase 8 Sprint 1 — Hard comparator gates. THIS DEC lands G1 only
  (missing-target-quantity). G2–G6 land as DEC-V61-036b after Codex
  round 1. G1 is the foundational PASS-washing fix surfaced by user's
  2026-04-22 deep review: both acceptance drivers silently substitute
  the first numeric `key_quantities` entry as `measurement.value` when
  the case-specific extractor did not emit the gold's target quantity.
  Duct flow measured at `hydraulic_diameter=0.1`, BFS at
  `U_residual_magnitude=0.044` — passed as "measurement" and compared
  to gold's friction_factor / Xr_over_H, accidentally landing within
  tolerance bands and washing to PASS/HAZARD. G1 kills the fallback:
  if the gold's quantity (with aliases) cannot be found in the run's
  key_quantities, `measurement.value = None`, extraction_source =
  "no_numeric_quantity", and `_derive_contract_status` forces FAIL
  with a MISSING_TARGET_QUANTITY audit concern.
autonomous_governance: true
claude_signoff: yes
codex_tool_invoked: pending (pre-merge required per self-pass-rate ≤ 0.70)
codex_rounds: 0
codex_verdict: pending
codex_tool_report_path: []
counter_status: |
  v6.1 autonomous_governance counter 21 → 22. RETRO-V61-002 covered 20;
  next retro at counter=30 per cadence rule #2.
reversibility: |
  Partially reversible — schema change `MeasuredValue.value: float → float|None`
  is backward-compatible for reads (old fixtures with 0.0 still load),
  but regenerated audit_real_run fixtures will carry `value: null` for
  the 7 silently-substituting cases, which is a change the frontend must
  handle. Revert = 5 files restored + fixtures regenerated.
notion_sync_status: pending
github_pr_url: null (direct-to-main after Codex)
github_merge_sha: pending
github_merge_method: pre-merge Codex verdict required
external_gate_self_estimated_pass_rate: 0.65
  (Cross-file schema touch + verdict engine edit + fixture regeneration —
  Codex pre-merge required per RETRO-V61-001 rule: ≤0.70 → pre-merge.
  Expected surface: (a) measurement.value None vs 0.0 boundary handling
  in frontend renders; (b) backward compat for fixtures that had
  extraction_source="comparator_deviation" already correct; (c) alias
  handling for quantity-name comparison in _derive_contract_status;
  (d) test updates where 7 cases flip from PASS/HAZARD to FAIL.)
supersedes: null
superseded_by: null
upstream: |
  - User deep-review 2026-04-22: "BFS reattachment_length 列 'U_residual_magnitude'
    / duct_flow friction_factor 列 'hydraulic_diameter' — 不是同一个量。"
  - Deep-plan subagent 036 root-cause trace:
    * scripts/phase5_audit_run.py::_primary_scalar (L76-91) first-numeric fallback
    * scripts/p2_acceptance_run.py::_extract_primary_measurement (L64-86) same bug
    * src/result_comparator.py already correctly gates G1 via
      _lookup_with_alias; the drivers BYPASS that gate.
  - DEC-V61-035 (default → audit_real_run): surfaced honest 7 FAILs but
    6 of those FAILs are still MIS-QUANTITIES, not real measurements.
    This DEC makes the FAILs semantically correct.
---

# DEC-V61-036: Hard comparator gate G1 — missing target quantity

## Why now

User's 2026-04-22 CFD deep-review caught that `measurement.value`
displayed in the UI was from the **wrong quantity** for 7 of the 10
whitelist cases:

| case | gold expects | actual measured | current verdict |
|---|---|---|---|
| BFS | `reattachment_length` (Xr/H ≈ 6.26) | `U_residual_magnitude` ≈ 0.044 | FAIL +0.48% (accidentally close to gold's range) |
| duct_flow | `friction_factor` (f ≈ 0.0185) | `hydraulic_diameter` = 0.1 | FAIL +440% |
| plane_channel | `u_mean_profile` | `U_max_approx` | FAIL |
| DHC | `nusselt_number` | `temperature_diff` | FAIL |
| RBC | `nusselt_number` | `temperature_diff` | FAIL |
| turbulent pipe | `friction_factor` | `U_max_approx` | FAIL |
| impinging jet | `nusselt_number` | `wall_heat_flux` | FAIL |

The deviations happen to surface as large FAILs today (thanks to
DEC-V61-035 flipping default → audit_real_run), but that's
**arithmetic accident**. The fundamental error is that a different
scalar is being compared to gold — the FAIL status isn't an honest
physics FAIL, it's a schema FAIL masquerading as physics.

## What lands (this DEC)

### 1. Schema: `MeasuredValue` allows absent value + carries quantity name
- `ui/backend/schemas/validation.py::MeasuredValue`
- `value: float` → `value: float | None`
- New field: `quantity: str | None = None`

### 2. Driver refactor — strict-lookup, no first-numeric fallback
- `scripts/phase5_audit_run.py::_primary_scalar` → becomes
  `_primary_scalar(report, expected_quantity)`; uses
  `result_comparator._lookup_with_alias(key_quantities, expected_quantity)`;
  on miss returns `(expected_quantity, None, "no_numeric_quantity")`.
- `scripts/p2_acceptance_run.py::_extract_primary_measurement` → same refactor.
- Both callers (`_audit_fixture_doc`, `_write_fixture`) load the gold
  YAML and pass gold's canonical `quantity` into the extractor.

### 3. Verdict engine: hard-FAIL on missing value
- `ui/backend/services/validation_report.py::_derive_contract_status`
- New branch at top: if `measurement is None` or `measurement.value is None`
  → return `("FAIL", None, None, lower, upper)`.
- `_make_measurement`: accept `value: None` (was `if "value" not in m: return None`).
- `_make_audit_concerns`: when `measurement_doc["measurement"]["extraction_source"] == "no_numeric_quantity"`,
  inject `AuditConcern(concern_type="MISSING_TARGET_QUANTITY", ...)`.

### 4. Fixture regeneration
- 7 audit_real_run fixtures regenerated; `value: null, quantity: "<gold_name>",
  extraction_source: "no_numeric_quantity"`.
- LDC + 3 correctly-extracting cases unaffected.

### 5. Tests updated
- `test_dashboard_has_cases_and_summary`: `fail_cases >= 7` (was `>= 1`).
- `test_validation_report_default_prefers_audit_real_run`: measurement.value is None, contract_status FAIL, MISSING_TARGET_QUANTITY in concern types.
- New `test_g1_missing_target_quantity_fails`: synthetic no-match → FAIL.
- New `test_g1_ldc_passes`: LDC u_centerline present → PASS unchanged.

## What is NOT in this DEC

- **G2 unit mismatch** (follow-up DEC-036b) — needs canonical-unit table design.
- **G3/G4 VTK gates** (follow-up DEC-036c) — new `src/comparator_gates.py`.
- **G5/G6 log gates** (follow-up DEC-036d) — extends `_parse_log_residuals`.
- **DEC-038 attestor** — lands separately, pre-extraction.

Splitting into 4 sub-DECs keeps each Codex round tight (≤200 LOC).

## Regression + Codex

Pre-merge Codex review mandatory (self-pass 0.65 ≤ 0.70 threshold).
Post-Codex: `PYTHONPATH=. .venv/bin/pytest ui/backend/tests/ -q` → 142+ pass.

## Counter

21 → 22.

## Related

- DEC-V61-035 (default → audit_real_run) — surfaced the bug by making
  honest verdicts visible; this DEC makes those verdicts semantically correct.
- DEC-V61-038 (convergence attestor) — pairs pre-extraction; composes AND-gated with 036.
- Phase 8 Sprint 1 = {036a G1, 036b G2, 038 A1-A6} landing together.

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

codex
The DEC is clear on intent: last-iteration semantics matter, laminar cases must skip cleanly, and `within=None` should degrade rather than hard-fail. I’m now matching the implementation to that contract line by line.
exec
/bin/zsh -lc "sed -n '1,200p' src/comparator_gates.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '401,520p' src/comparator_gates.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '201,400p' src/comparator_gates.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
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
    """Return the max |U| across all cells in the latest-time VTK.

    Uses pyvista when available. Returns None when VTK unavailable,
    unreadable, or pyvista is not installed — caller treats None as
    "skip G3 VTK branch, use log-epsilon proxy instead".
    """

 succeeded in 0ms:
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

 succeeded in 0ms:
    if not vtk_dir.is_dir():
        return None
    try:
        import numpy as np
        import pyvista as pv
    except ImportError:
        return None

    # Find the latest-time VTK file. OpenFOAM foamToVTK lays files as
    # {case}_{timestep}.vtk or allPatches/{case}_{timestep}.vtk. We scan
    # the whole tree under vtk_dir.
    candidates = sorted(vtk_dir.rglob("*.vtk"))
    if not candidates:
        return None

    u_max_overall: Optional[float] = None
    for vtk_path in candidates:
        try:
            mesh = pv.read(str(vtk_path))
        except Exception:
            continue
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
            continue
        # U is typically (N, 3); compute per-cell magnitude.
        if U_array.ndim == 2 and U_array.shape[1] >= 3:
            mags = np.linalg.norm(U_array[:, :3], axis=1)
        else:
            mags = np.abs(U_array.ravel())
        if mags.size == 0:
            continue
        candidate_max = float(np.nanmax(mags))
        if u_max_overall is None or candidate_max > u_max_overall:
            u_max_overall = candidate_max
    return u_max_overall


# ---------------------------------------------------------------------------
# Individual gate checks
# ---------------------------------------------------------------------------

def _check_g3_velocity_overflow(
    log_stats: Optional[LogStats],
    vtk_dir: Optional[Path],
    U_ref: float,
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

exec
/bin/zsh -lc "sed -n '221,440p' scripts/phase5_audit_run.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '1,220p' scripts/phase5_audit_run.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
    # non-whitelist caller that hasn't been updated yet. Whitelist cases
    # always pass expected_quantity per DEC-V61-036.
    if comp is not None and comp.deviations:
        first = comp.deviations[0]
        actual = first.actual
        if isinstance(actual, dict) and "value" in actual:
            return first.quantity, float(actual["value"]), "comparator_deviation"
        if isinstance(actual, (int, float)):
            return first.quantity, float(actual), "comparator_deviation"
    for k, v in kq.items():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return k, float(v), "key_quantities_fallback_legacy"
        if isinstance(v, dict) and "value" in v and isinstance(v["value"], (int, float)):
            return k, float(v["value"]), "key_quantities_fallback_legacy"
    return None, None, "no_numeric_quantity"


def _phase7a_timestamp() -> str:
    """Shared timestamp format — matches _write_raw_capture."""
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _write_field_artifacts_run_manifest(
    case_id: str, run_label: str, timestamp: str
) -> "Path | None":
    """Write reports/phase5_fields/{case_id}/runs/{run_label}.json so the
    backend route can resolve run_label -> timestamp directory in O(1).

    Returns the manifest Path on success, None if the artifact dir is absent
    OR empty. Codex round 1 MED #3 (2026-04-21): require a NON-empty artifact
    set — an empty directory from a failed foamToVTK must not produce a
    bogus manifest that the route will then 404-through.
    """
    artifact_dir = FIELDS_DIR / case_id / timestamp
    if not artifact_dir.is_dir():
        print(
            f"[audit] [WARN] field artifact dir missing, skipping manifest: {artifact_dir}",
            flush=True,
        )
        return None
    # Count usable leaf files (foamToVTK output, samples, residuals).
    usable = [p for p in artifact_dir.rglob("*") if p.is_file()]
    if not usable:
        print(
            f"[audit] [WARN] field artifact dir empty, skipping manifest: {artifact_dir}",
            flush=True,
        )
        return None
    runs_dir = FIELDS_DIR / case_id / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    manifest = runs_dir / f"{run_label}.json"
    payload = {
        "run_label": run_label,
        "timestamp": timestamp,
        "case_id": case_id,
        "artifact_dir_rel": str(artifact_dir.relative_to(REPO_ROOT)),
    }
    manifest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return manifest


# DEC-V61-034 Tier C: opt in all 10 whitelist cases for Phase 7a field
# capture. The executor's _capture_field_artifacts runs foamToVTK + stages
# VTK / residuals / solver log for ANY case regardless of whether its
# generator emits the controlDict functions{} block (residuals are
# log-parsed in the renderer when the functionObject wasn't emitted).
# LDC still gets the full gold-overlay report via its sample block; the
# other 9 cases flow through Tier C visual-only rendering (contour + residuals).
_PHASE7A_OPTED_IN: frozenset[str] = frozenset(ALL_CASES)


def _audit_fixture_doc(
    case_id: str,
    report,
    commit_sha: str,
    field_artifacts_ref: "dict | None" = None,
    phase7a_timestamp: "str | None" = None,
    u_ref: float = 1.0,
) -> dict:
    # DEC-V61-036 G1: load the gold's canonical quantity BEFORE extraction
    # so the driver can strict-match (and hard-fail on miss) instead of
    # silently substituting "first numeric".
    expected_quantity = _gold_expected_quantity(case_id)
    quantity, value, source_note = _primary_scalar(report, expected_quantity)
    comp = report.comparison_result
    passed = comp.passed if comp else False

    # DEC-V61-036 G1: verdict hint must reflect the missing-quantity outcome.
    # Prior behaviour tied verdict_hint to comp.passed alone, which showed
    # "PASS" for runs that simply didn't measure the gold quantity.
    if source_note == "no_numeric_quantity" or value is None:
        verdict_hint = "FAIL"
    else:
        verdict_hint = "PASS" if passed else "FAIL"

    # DEC-V61-036 G1: write measurement.value as literal null (None) when
    # extractor missed; the verdict engine hard-FAILs on None. Do NOT coerce
    # to 0.0 — that was the prior PASS-washing path.
    measurement_value: float | None = value

    doc = {
        "run_metadata": {
            "run_id": "audit_real_run",
            "label_zh": "真实 solver 审计运行",
            "label_en": "Real solver audit run",
            "description_zh": (
                f"FoamAgentExecutor 驱动 OpenFOAM 实际跑出的结果（commit {commit_sha}）。"
                "这是 audit package 背书的权威测量——不是合成 fixture。"
                "失败的话说明 case 本身的 physics_contract 在当前 mesh 预算下无法满足，"
                "不是 harness bug；会进入 audit_concerns 随包交付给审查方。"
            ),
            "category": "audit_real_run",
            "expected_verdict": verdict_hint,
        },
        "case_id": case_id,
        "source": "phase5_audit_run_foam_agent",
        "measurement": {
            "value": measurement_value,
            "unit": "dimensionless",
            "run_id": f"audit_{case_id}_{commit_sha}",
            "commit_sha": commit_sha,
            "measured_at": _iso_now(),
            "quantity": quantity,
            "extraction_source": source_note,
            "solver_success": report.execution_result.success,
            "comparator_passed": passed,
        },
        "audit_concerns": [],
        "decisions_trail": [
            {
                "decision_id": "DEC-V61-028",
                "date": "2026-04-21",
                "title": "Phase 5a audit pipeline — real-solver fixtures",
                "autonomous": True,
            },
            {
                "decision_id": "DEC-V61-036",
                "date": "2026-04-22",
                "title": "Hard comparator gate G1 (missing-target-quantity)",
                "autonomous": True,
            },
        ],
    }

    # DEC-V61-036b G3/G4/G5 + DEC-V61-038 A1..A6: run pre-extraction
    # attestor THEN post-extraction physics gates against the captured
    # field artifacts + solver log. Attestor checks convergence process;
    # gates check final-state sanity. Both emit audit_concerns[] entries
    # that the verdict engine hard-FAILs on. Non-blocking on missing
    # artifacts — both skip gracefully when log/VTK is unavailable.
    if phase7a_timestamp is not None:
        artifact_dir = FIELDS_DIR / case_id / phase7a_timestamp
        solver_log: "Path | None" = None
        if artifact_dir.is_dir():
            log_candidates = sorted(artifact_dir.glob("log.*"))
            if log_candidates:
                solver_log = log_candidates[0]
        vtk_dir = artifact_dir / "VTK" if artifact_dir.is_dir() else None

        # DEC-V61-038 attestor — runs first, records overall verdict on the
        # fixture for UI display + injects HAZARD/FAIL checks as concerns.
        try:
            attestation = attest(solver_log)
            doc["attestation"] = {
                "overall": attestation.overall,
                "checks": [
                    {
                        "check_id": c.check_id,
                        "verdict": c.verdict,
                        "concern_type": c.concern_type,
                        "summary": c.summary,
                    }
                    for c in attestation.checks
                ],
            }
            for c in attestation.concerns:
                doc["audit_concerns"].append(check_to_audit_concern_dict(c))
        except Exception as exc:  # noqa: BLE001 — never crash the audit
            print(
                f"[audit] [WARN] attestor failed on {case_id}: {exc!r}",
                flush=True,
            )

        # DEC-V61-036b gates — post-extraction physics checks.
        try:
            gate_violations = check_all_gates(
                log_path=solver_log,
                vtk_dir=vtk_dir if vtk_dir and vtk_dir.is_dir() else None,
                U_ref=u_ref,
            )
            for v in gate_violations:
                doc["audit_concerns"].append(violation_to_audit_concern_dict(v))
        except Exception as exc:  # noqa: BLE001 — gates must not crash the audit
            print(
                f"[audit] [WARN] gates failed on {case_id}: {exc!r}", flush=True
            )

    # DEC-V61-036 G1: stamp a first-class concern when the extractor could
    # not resolve the gold's quantity. The verdict engine hard-FAILs
    # independently based on measurement.value is None, but embedding the
    # concern in the fixture makes the audit package self-explaining.
    if source_note == "no_numeric_quantity":
        doc["audit_concerns"].append(
            {
                "concern_type": "MISSING_TARGET_QUANTITY",
                "summary": (
                    f"Extractor could not locate gold quantity "
                    f"{quantity!r} in run key_quantities."
                )[:240],
                "detail": (
                    "Gold standard expected a measurement of "
                    f"{quantity!r} (with result_comparator alias resolution), "
                    "but the case-specific extractor did not emit that key. "
                    "Prior harness behaviour (pre-DEC-V61-036) silently "
                    "substituted the first numeric key_quantities entry and "
                    "compared it against the gold's tolerance band — that "
                    "PASS-washing path is now closed. The adapter needs a "
                    "case-specific extractor for this quantity; the verdict "
                    "is hard-FAIL until that lands."
                )[:2000],

 succeeded in 0ms:
"""Phase 5a audit-run driver — runs a case via FoamAgentExecutor and writes
a deterministic audit fixture into fixtures/runs/{case_id}/audit_real_run_measurement.yaml.

Usage (from repo root):
    EXECUTOR_MODE=foam_agent \\
    .venv/bin/python scripts/phase5_audit_run.py <case_id> [<case_id>...]

    # all cases:
    EXECUTOR_MODE=foam_agent \\
    .venv/bin/python scripts/phase5_audit_run.py --all

Output:
    ui/backend/tests/fixtures/runs/{case_id}/audit_real_run_measurement.yaml
    reports/phase5_audit/{timestamp}_{case_id}_raw_run.json  (stdout/stderr)

Determinism:
    Timestamp + commit_sha are the only non-deterministic fields; tests use
    an `allowed_nondeterminism` set to strip them before byte-comparison.
    Numeric values from simpleFoam are deterministic given identical
    mesh + schemes + fvSolution + initial conditions (we use steady-state
    solvers for Phase 5a, no RNG). This property is enforced by
    test_phase5_byte_repro.py.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.foam_agent_adapter import FoamAgentExecutor  # noqa: E402
from src.task_runner import TaskRunner  # noqa: E402
from src.result_comparator import _lookup_with_alias  # noqa: E402
from src.comparator_gates import (  # noqa: E402
    check_all_gates,
    violation_to_audit_concern_dict,
)
from src.convergence_attestor import (  # noqa: E402
    attest,
    check_to_audit_concern_dict,
)

RUNS_DIR = REPO_ROOT / "ui" / "backend" / "tests" / "fixtures" / "runs"
RAW_DIR = REPO_ROOT / "reports" / "phase5_audit"
FIELDS_DIR = REPO_ROOT / "reports" / "phase5_fields"

ALL_CASES = [
    "lid_driven_cavity",
    "backward_facing_step",
    "circular_cylinder_wake",
    "turbulent_flat_plate",
    "duct_flow",
    "differential_heated_cavity",
    "plane_channel_flow",
    "impinging_jet",
    "naca0012_airfoil",
    "rayleigh_benard_convection",
]


def _git_head_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"], timeout=5
        )
        return out.decode().strip()[:7]
    except Exception:
        return "unknown"


def _iso_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _gold_expected_quantity(case_id: str) -> str | None:
    """Load `quantity` from knowledge/gold_standards/{case_id}.yaml.

    Returns the canonical gold quantity name (e.g. "reattachment_length",
    "friction_factor"). Used by DEC-V61-036 G1 to gate extraction — the
    driver must compare measured value against this exact key (with
    result_comparator alias resolution), not against "first numeric".
    """
    gold_path = REPO_ROOT / "knowledge" / "gold_standards" / f"{case_id}.yaml"
    if not gold_path.is_file():
        return None
    try:
        with gold_path.open("r", encoding="utf-8") as fh:
            docs = list(yaml.safe_load_all(fh))
    except Exception:
        return None
    # Flat schema: top-level `quantity:` key in the first non-empty doc.
    # observables[] schema: first observable's `name`.
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        q = doc.get("quantity")
        if isinstance(q, str) and q.strip():
            return q.strip()
        obs = doc.get("observables")
        if isinstance(obs, list) and obs:
            first = obs[0]
            if isinstance(first, dict):
                name = first.get("name")
                if isinstance(name, str) and name.strip():
                    return name.strip()
    return None


def _primary_scalar(
    report, expected_quantity: str | None = None
) -> tuple[str | None, float | None, str]:
    """Extract the primary scalar for the audit fixture.

    DEC-V61-036 G1: when `expected_quantity` is provided, this function
    requires the run to emit exactly that quantity (with alias resolution)
    — it no longer falls back to "first numeric key_quantities entry".

    Priority:
      1. comparator.deviations entry whose `quantity` matches expected_quantity
      2. key_quantities lookup via `_lookup_with_alias(kq, expected_quantity)`
      3. (expected_quantity, None, "no_numeric_quantity") — signals G1 failure

    When `expected_quantity is None` (legacy calls without a gold), falls
    back to the OLD behaviour (first numeric) for backward compatibility
    — but this path should not fire for any whitelist case because every
    case has a gold_standard.
    """
    comp = report.comparison_result
    kq = report.execution_result.key_quantities or {}

    if expected_quantity is not None:
        # DEC-V61-036 G1 round 2: profile quantities (LDC u_centerline, NACA
        # pressure_coefficient, plane_channel u_mean_profile) are emitted as
        # per-coordinate comparator deviations named `expected_quantity[y=X]`,
        # `expected_quantity[x/c=Y]`, etc. Match both the exact-scalar case
        # AND the bracketed-profile case as honest extractions.
        def _quantity_matches(dev_quantity: str) -> bool:
            if dev_quantity == expected_quantity:
                return True
            # Strip `[axis=value]` suffix for profile deviations.
            return dev_quantity.split("[", 1)[0] == expected_quantity

        # (1) comparator deviation matching gold's quantity (scalar OR profile)
        if comp is not None and comp.deviations:
            for dev in comp.deviations:
                if _quantity_matches(dev.quantity):
                    actual = dev.actual
                    if isinstance(actual, dict) and "value" in actual:
                        return dev.quantity, float(actual["value"]), "comparator_deviation"
                    if isinstance(actual, (int, float)):
                        return dev.quantity, float(actual), "comparator_deviation"
        # (2) direct/alias lookup in key_quantities
        value, resolved_key = _lookup_with_alias(kq, expected_quantity)
        if value is not None:
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                src = (
                    "key_quantities_direct"
                    if resolved_key == expected_quantity
                    else f"key_quantities_alias:{resolved_key}"
                )
                return expected_quantity, float(value), src
            if isinstance(value, dict) and "value" in value and isinstance(
                value["value"], (int, float)
            ):
                return expected_quantity, float(value["value"]), "key_quantities_alias_dict"
            # DEC-V61-036 G1 round 2: list-valued key_quantity IS honest
            # extraction for profile gold standards. The comparator would
            # normally emit per-coordinate deviations; if there ARE no
            # deviations (i.e., profile is within tolerance at every point),
            # record the profile as present without forcing hard-FAIL, and
            # sample a scalar representative for UI display.
            if isinstance(value, list) and value:
                first = value[0]
                if isinstance(first, (int, float)) and not isinstance(first, bool):
                    # All profile points within tolerance (no deviations) and
                    # comparator considered the full profile honestly. Record
                    # the first-coordinate value as the scalar display sample.
                    return (
                        f"{expected_quantity}[0]",
                        float(first),
                        "key_quantities_profile_sample",
                    )
                # Profile of non-scalar entries — list[dict]. Look for a
                # value key under several conventional names, per
                # DEC-V61-036c G2 Codex round-2 nit: NACA sampleDict emits
                # dict{x_over_c, Cp}, plane_channel DNS profile emits
                # dict{y_plus, u_plus}, etc.
                _PROFILE_SCALAR_KEYS = ("value", "Cp", "Cf", "u", "u_plus", "Nu", "f")
                if isinstance(first, dict):
                    for scalar_key in _PROFILE_SCALAR_KEYS:
                        val = first.get(scalar_key)
                        if isinstance(val, (int, float)) and not isinstance(val, bool):
                            return (
                                f"{expected_quantity}[0]",
                                float(val),
                                f"key_quantities_profile_sample_dict:{scalar_key}",
                            )
                # Fallback for legacy shape (kept for backward compat).
                if isinstance(first, dict) and "value" in first and isinstance(
                    first["value"], (int, float)
                ):
                    return (
                        f"{expected_quantity}[0]",
                        float(first["value"]),
                        "key_quantities_profile_sample_dict",
                    )
        # (3) G1 miss — NO fallback. Signal the verdict engine to hard-FAIL.
        return expected_quantity, None, "no_numeric_quantity"

    # Legacy path (no expected_quantity): preserve old behaviour for any

exec
/bin/zsh -lc "sed -n '441,700p' scripts/phase5_audit_run.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
                "decision_refs": ["DEC-V61-036"],
            }
        )

    if comp is not None:
        doc["audit_concerns"].append(
            {
                "concern_type": "CONTRACT_STATUS",
                "summary": (comp.summary or "No summary")[:240],
                "detail": (comp.summary or "")[:2000],
                "decision_refs": ["DEC-V61-028"],
            }
        )
        if comp.deviations:
            # Summarize first 5 deviations for the audit record
            dev_summary = "; ".join(
                f"{d.quantity}: actual={d.actual} expected={d.expected}"
                for d in comp.deviations[:5]
            )
            doc["audit_concerns"].append(
                {
                    "concern_type": "DEVIATIONS",
                    "summary": f"{len(comp.deviations)} deviation(s) over tolerance"[:240],
                    "detail": dev_summary[:2000],
                    "decision_refs": ["DEC-V61-028"],
                }
            )

    # Phase 7a — field artifacts reference (manifest path only; NO timestamps
    # in the YAML itself so byte-repro stays green per 07a-RESEARCH.md §3.1).
    # The manifest at the referenced path contains the timestamp.
    if field_artifacts_ref is not None:
        doc["field_artifacts"] = field_artifacts_ref

    return doc


def _write_audit_fixture(case_id: str, doc: dict) -> Path:
    case_dir = RUNS_DIR / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    out_path = case_dir / "audit_real_run_measurement.yaml"
    header = (
        "# Phase 5a audit-real-run fixture — AUTO-GENERATED, DO NOT HAND-EDIT.\n"
        "# Regenerate via:\n"
        f"#   EXECUTOR_MODE=foam_agent .venv/bin/python scripts/phase5_audit_run.py {case_id}\n"
        "# This fixture backs the signed audit package. Byte-identity across\n"
        "# re-runs (modulo timestamp + commit_sha) is enforced by\n"
        "# test_phase5_byte_repro.py.\n\n"
    )
    with out_path.open("w", encoding="utf-8") as fh:
        fh.write(header)
        yaml.safe_dump(doc, fh, allow_unicode=True, sort_keys=False, default_flow_style=False)
    return out_path


def _write_raw_capture(case_id: str, report, duration_s: float) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = RAW_DIR / f"{ts}_{case_id}_raw.json"
    er = report.execution_result
    comp = report.comparison_result
    data = {
        "case_id": case_id,
        "measured_at": _iso_now(),
        "duration_s": round(duration_s, 3),
        "solver_success": er.success,
        "key_quantities": er.key_quantities,
        "comparator_passed": comp.passed if comp else None,
        "comparator_summary": (comp.summary if comp else None),
        "deviations": (
            [
                {"quantity": d.quantity, "actual": d.actual, "expected": d.expected}
                for d in (comp.deviations or [])
            ]
            if comp
            else []
        ),
    }
    out.write_text(json.dumps(data, indent=2, default=str))
    return out


def run_one(runner: TaskRunner, case_id: str, commit_sha: str) -> dict:
    t0 = time.monotonic()
    print(f"[audit] {case_id} → start", flush=True)

    # Phase 7a — author the single shared timestamp up front; the executor-side
    # _capture_field_artifacts writes to reports/phase5_fields/{case_id}/{ts}/.
    # Codex round 1 MED #3: only inject metadata for opted-in cases — other 9
    # case generators do not emit Phase 7a function objects yet.
    ts = _phase7a_timestamp()
    try:
        spec = runner._task_spec_from_case_id(case_id)
        if case_id in _PHASE7A_OPTED_IN:
            if spec.metadata is None:
                spec.metadata = {}
            spec.metadata["phase7a_timestamp"] = ts
            spec.metadata["phase7a_case_id"] = case_id
        report = runner.run_task(spec)
    except Exception as e:  # noqa: BLE001
        print(f"[audit] {case_id} EXCEPTION: {e!r}")
        return {"case_id": case_id, "ok": False, "error": repr(e)}

    dt = time.monotonic() - t0

    # Phase 7a — write per-run manifest + build field_artifacts_ref dict iff
    # the case is opted-in AND the artifact dir materialized with non-empty
    # contents (best-effort, must not block audit doc). MED #3 gating above.
    run_label = "audit_real_run"
    manifest_path = (
        _write_field_artifacts_run_manifest(case_id, run_label, ts)
        if case_id in _PHASE7A_OPTED_IN
        else None
    )
    field_artifacts_ref: "dict | None" = None
    if manifest_path is not None:
        field_artifacts_ref = {
            "manifest_path_rel": str(manifest_path.relative_to(REPO_ROOT)),
            "run_label": run_label,
            # Deliberately NO timestamp string here (byte-repro): resolve via manifest.
        }

    doc = _audit_fixture_doc(
        case_id,
        report,
        commit_sha,
        field_artifacts_ref=field_artifacts_ref,
        phase7a_timestamp=ts,
    )
    fixture_path = _write_audit_fixture(case_id, doc)
    raw_path = _write_raw_capture(case_id, report, dt)
    verdict = doc["run_metadata"]["expected_verdict"]
    print(f"[audit] {case_id} → {verdict} · {dt:.1f}s · {fixture_path.name}", flush=True)
    return {
        "case_id": case_id,
        "ok": True,
        "duration_s": round(dt, 3),
        "verdict": verdict,
        "fixture": str(fixture_path.relative_to(REPO_ROOT)),
        "raw": str(raw_path.relative_to(REPO_ROOT)),
        "field_artifacts_manifest": (
            str(manifest_path.relative_to(REPO_ROOT)) if manifest_path else None
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("cases", nargs="*", help="case ids; use --all for all 10")
    parser.add_argument("--all", action="store_true", help="run all 10 whitelist cases")
    args = parser.parse_args()

    if os.environ.get("EXECUTOR_MODE", "").lower() != "foam_agent":
        print("ERROR: set EXECUTOR_MODE=foam_agent", file=sys.stderr)
        return 2

    targets = ALL_CASES if args.all else args.cases
    if not targets:
        parser.print_help()
        return 2

    commit_sha = _git_head_sha()
    print(f"[audit] commit: {commit_sha} · cases: {targets}")

    runner = TaskRunner(executor=FoamAgentExecutor())
    summary = []
    for case_id in targets:
        summary.append(run_one(runner, case_id, commit_sha))

    print("\n=== SUMMARY ===")
    for r in summary:
        if r["ok"]:
            print(f"{r['case_id']:38s} {r['verdict']:5s} {r['duration_s']:.1f}s")
        else:
            print(f"{r['case_id']:38s} ERROR {r['error'][:80]}")

    ok_count = sum(1 for r in summary if r["ok"])
    return 0 if ok_count == len(summary) else 1


if __name__ == "__main__":
    sys.exit(main())

exec
/bin/zsh -lc "sed -n '501,750p' ui/backend/services/validation_report.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '251,500p' ui/backend/services/validation_report.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '1,250p' ui/backend/services/validation_report.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
                        "result_comparator alias lookup also missed. Prior "
                        "behavior silently substituted the first numeric "
                        "key_quantities entry — that PASS-washing path is now "
                        "closed. Measurement.value = None, contract_status = FAIL."
                    ),
                    decision_refs=["DEC-V61-036"],
                )
            )
    return out


def _extract_decision_refs(text: str) -> list[str]:
    """Pull DEC-ADWM-00N / DEC-V61-00N tokens out of narrative text."""
    import re

    return sorted(set(re.findall(r"DEC-(?:ADWM|V61)-\d{3}", text)))


def _make_decisions_trail(
    measurement_doc: dict[str, Any] | None,
) -> list[DecisionLink]:
    if not measurement_doc:
        return []
    out: list[DecisionLink] = []
    for row in measurement_doc.get("decisions_trail", []) or []:
        out.append(
            DecisionLink(
                decision_id=row.get("decision_id", ""),
                date=row.get("date", ""),
                title=row.get("title", ""),
                autonomous=bool(row.get("autonomous", False)),
            )
        )
    return out


def _derive_contract_status(
    gs_ref: GoldStandardReference,
    measurement: MeasuredValue | None,
    preconditions: list[Precondition],
    audit_concerns: list[AuditConcern],
) -> tuple[ContractStatus, float | None, bool | None, float, float]:
    """Compute the three-state contract status + tolerance bounds.

    Returns (status, deviation_pct, within_tolerance, lower, upper)."""
    # For negative ref_values the naive (1-tol)*ref > (1+tol)*ref, so
    # take min/max to keep `lower` as the numerically smaller bound.
    # This matters for LDC where u_centerline can be negative near the
    # bottom-left corner (Ghia Re=100 at y=0.0625 gives u/U = -0.03717).
    bound_a = gs_ref.ref_value * (1.0 - gs_ref.tolerance_pct)
    bound_b = gs_ref.ref_value * (1.0 + gs_ref.tolerance_pct)
    lower = min(bound_a, bound_b)
    upper = max(bound_a, bound_b)

    if measurement is None:
        return ("UNKNOWN", None, None, lower, upper)

    # DEC-V61-036 G1 + DEC-V61-036b G3/G4/G5 + DEC-V61-038 A1/A4:
    # hard-FAIL concern codes. When any of these concerns are present,
    # the measurement cannot be trusted regardless of whether it lies
    # inside the gold tolerance band.
    #   G1  MISSING_TARGET_QUANTITY    — schema mismatch (extractor missed gold quantity)
    #   G3  VELOCITY_OVERFLOW           — |U|_max > 100·U_ref
    #   G4  TURBULENCE_NEGATIVE         — k/eps/omega < 0 at last iter or overflow
    #   G5  CONTINUITY_DIVERGED         — sum_local > 1e-2 or |cum| > 1
    #   A1  SOLVER_CRASH_LOG            — FOAM FATAL / stack-trace in log
    #   A4  SOLVER_ITERATION_CAP        — pressure loop hit cap ≥3 consecutive iters
    # A2/A3/A5/A6 are HAZARD tier — they record concerns but don't hard-FAIL
    # (some cases physically operate at high residuals; promotion to FAIL
    # via per-case override lands in a future DEC).
    _HARD_FAIL_CONCERNS = {
        "MISSING_TARGET_QUANTITY",
        "VELOCITY_OVERFLOW",
        "TURBULENCE_NEGATIVE",
        "CONTINUITY_DIVERGED",
        "SOLVER_CRASH_LOG",
        "SOLVER_ITERATION_CAP",
    }
    has_hard_fail = any(
        c.concern_type in _HARD_FAIL_CONCERNS for c in audit_concerns
    )
    if measurement.value is None or has_hard_fail:
        # Codex DEC-036b round-1 feedback: when a hard-fail concern fires,
        # the scalar measurement cannot be trusted even if it happens to lie
        # in the tolerance band. Returning `within_tolerance=True` under a
        # FAIL verdict rendered as "Within band: yes" while status was FAIL,
        # which is materially confusing. Null the `within` flag whenever
        # the verdict is hard-failed — the UI now renders "—" in that column.
        if measurement.value is None:
            return ("FAIL", None, None, lower, upper)
        dev_pct = 0.0
        if gs_ref.ref_value != 0.0:
            dev_pct = (measurement.value - gs_ref.ref_value) / gs_ref.ref_value * 100.0
        return ("FAIL", dev_pct, None, lower, upper)

    deviation_pct = 0.0
    if gs_ref.ref_value != 0.0:
        deviation_pct = (measurement.value - gs_ref.ref_value) / gs_ref.ref_value * 100.0

    # Tolerance test in deviation space (sign-invariant + consistent with
    # the percentage shown in the UI). `within_tolerance` matches when
    # |deviation| <= tolerance_pct expressed as a percentage.
    within = abs(deviation_pct) <= gs_ref.tolerance_pct * 100.0
    precondition_fails = any(not p.satisfied for p in preconditions)
    has_silent_pass_hazard = any(
        "SILENT_PASS_HAZARD" in c.concern_type or "SILENT_PASS_HAZARD" in (c.summary or "")
        or "SILENT_PASS_HAZARD" in (c.detail or "")
        for c in audit_concerns
    )

    if not within:
        return ("FAIL", deviation_pct, within, lower, upper)
    if precondition_fails or has_silent_pass_hazard:
        return ("HAZARD", deviation_pct, within, lower, upper)
    return ("PASS", deviation_pct, within, lower, upper)


def _make_attestation(
    doc: dict[str, Any] | None,
) -> AttestorVerdict | None:
    """DEC-V61-040: lift `attestation` block from the fixture into the API.

    The attestor runs at audit-fixture time (see scripts/phase5_audit_run.py)
    and writes `{overall, checks[]}` onto the measurement doc. Two states:

    - Block absent (legacy fixtures, reference / visual_only tiers with no
      solver log): returns None. The UI renders "no solver log available".
    - Block present with `overall: ATTEST_NOT_APPLICABLE`: returns a verdict
      object with that overall — a first-class "we looked and nothing to
      assert" state, per Codex DEC-040 round-1 CFD opinion (Q4b).

    Malformed blocks fail loudly (ValueError) rather than silently returning
    None — an audit-evidence path should never hide fixture corruption.
    This closes Codex round-1 FLAG on lenient parsing.
    """
    if not doc:
        return None
    block = doc.get("attestation")
    if block is None:
        return None
    if not isinstance(block, dict):
        raise ValueError(
            f"attestation must be a mapping, got {type(block).__name__}"
        )
    overall = block.get("overall")
    valid_overalls = (
        "ATTEST_PASS", "ATTEST_HAZARD", "ATTEST_FAIL", "ATTEST_NOT_APPLICABLE"
    )
    if overall not in valid_overalls:
        raise ValueError(
            f"attestation.overall must be one of {valid_overalls}, "
            f"got {overall!r}"
        )
    checks_raw = block.get("checks") or []
    if not isinstance(checks_raw, list):
        raise ValueError(
            f"attestation.checks must be a list, got {type(checks_raw).__name__}"
        )
    checks: list[AttestorCheck] = []
    for entry in checks_raw:
        if not isinstance(entry, dict):
            raise ValueError(
                f"attestation.checks[] entry must be a mapping, "
                f"got {type(entry).__name__}"
            )
        verdict = entry.get("verdict")
        if verdict not in ("PASS", "HAZARD", "FAIL"):
            raise ValueError(
                f"attestation.checks[{entry.get('check_id', '?')}].verdict "
                f"must be PASS/HAZARD/FAIL, got {verdict!r}"
            )
        checks.append(
            AttestorCheck(
                check_id=entry.get("check_id", ""),
                verdict=verdict,
                concern_type=entry.get("concern_type"),
                summary=entry.get("summary", "") or "",
            )
        )
    # Codex DEC-040 round-2 FLAG: checks:[] is only physically valid for
    # ATTEST_NOT_APPLICABLE (the attestor bails early with no checks when
    # there's no log). Any other overall with empty checks is a corrupt
    # fixture — fail closed at the parsing boundary rather than letting
    # the UI render a contradictory "ATTEST PASS + no solver log" badge.
    if overall == "ATTEST_NOT_APPLICABLE":
        if checks:
            raise ValueError(
                f"attestation.overall=ATTEST_NOT_APPLICABLE must have empty "
                f"checks[], got {len(checks)} entries"
            )
    else:
        if not checks:
            raise ValueError(
                f"attestation.overall={overall} requires non-empty checks[]; "
                f"only ATTEST_NOT_APPLICABLE may have an empty checks array"
            )
    return AttestorVerdict(overall=overall, checks=checks)


def _make_measurement(doc: dict[str, Any] | None) -> MeasuredValue | None:
    if not doc:
        return None
    m = doc.get("measurement") or {}
    if "value" not in m:
        return None
    # DEC-V61-036 G1: value may be explicit None when extractor could not
    # locate the gold's target quantity. Preserve None instead of coercing
    # to 0.0 — the verdict engine hard-FAILs on None per the G1 contract.
    raw_value = m["value"]
    value: float | None
    if raw_value is None:
        value = None
    else:
        value = float(raw_value)
    return MeasuredValue(
        value=value,
        unit=m.get("unit", "") or "",
        source=doc.get("source", "fixture"),
        run_id=m.get("run_id"),
        commit_sha=m.get("commit_sha"),
        measured_at=m.get("measured_at"),
        quantity=m.get("quantity"),
        extraction_source=m.get("extraction_source"),
    )


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------
def list_cases() -> list[CaseIndexEntry]:
    whitelist = _load_whitelist()
    out: list[CaseIndexEntry] = []
    for cid, case in whitelist.items():
        gs = _load_gold_standard(cid)
        # Use the same default-run resolution as build_validation_report so
        # the catalog contract_status matches what the Compare tab shows on
        # first click (reference_pass preferred → student's first impression
        # is PASS when curated).
        default_run_id = _pick_default_run_id(cid)
        measurement_doc = (
            _load_run_measurement(cid, default_run_id) if default_run_id else None
        )
        gs_ref = _make_gold_reference(case, gs)
        preconditions = _make_preconditions(gs)
        audit_concerns = _make_audit_concerns(gs, measurement_doc)
        measurement = _make_measurement(measurement_doc)
        if gs_ref is not None:
            status, *_ = _derive_contract_status(
                gs_ref, measurement, preconditions, audit_concerns
            )

 succeeded in 0ms:
                return (cat_rank, n, r.run_id)
            return (cat_rank, 0, r.run_id)

        runs.sort(key=_sort_key)
        return runs

    legacy = _load_fixture_measurement(case_id)
    if legacy is not None:
        runs.append(
            RunDescriptor(
                run_id="legacy",
                label_zh=legacy.get("run_label_zh") or "历史测量",
                label_en="Legacy fixture",
                description_zh=(
                    legacy.get("run_description_zh")
                    or "来自 §5d 验收批次的原始测量值，保留作审计追溯用。"
                ),
                category="real_incident",
                expected_verdict="UNKNOWN",
            )
        )
    return runs


def _load_run_measurement(case_id: str, run_id: str) -> dict[str, Any] | None:
    """Load a specific run's measurement doc. Falls back to legacy fixture
    when run_id=='legacy'."""
    if run_id == "legacy":
        return _load_fixture_measurement(case_id)
    candidate = RUNS_DIR / case_id / f"{run_id}_measurement.yaml"
    if not candidate.exists():
        return None
    with candidate.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _pick_default_run_id(case_id: str) -> str | None:
    """Default run resolution rule (DEC-V61-035 correction): prefer the
    ``audit_real_run`` category — i.e. the actual solver-in-the-loop
    verdict. Falls back to 'reference' (literature-data curated PASS
    narrative) only when no audit_real_run exists, and finally to any
    curated run, then 'legacy' on-disk fixture.

    The previous rule preferred `reference` unconditionally, which
    surfaced curated PASS narratives as the case verdict even when the
    real-solver audit run FAILED — a PASS-washing bug flagged in the
    2026-04-22 deep-review.
    """
    runs = list_runs(case_id)
    # 1. Prefer audit_real_run (honest: solver-in-the-loop evidence).
    for r in runs:
        if r.category == "audit_real_run":
            return r.run_id
    # 2. Fall back to reference (curated literature-anchored run).
    for r in runs:
        if r.category == "reference":
            return r.run_id
    # 3. Any curated run.
    if runs:
        return runs[0].run_id
    return None


# ---------------------------------------------------------------------------
# Mappers — YAML dict → Pydantic schema
# ---------------------------------------------------------------------------
def _tolerance_scalar(value: Any) -> float | None:
    """Normalise tolerance-shaped YAML (scalar OR {mode, value} dict)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        inner = value.get("value")
        if isinstance(inner, (int, float)):
            return float(inner)
    return None


def _make_gold_reference(
    case: dict[str, Any],
    gs_doc: dict[str, Any] | None,
) -> GoldStandardReference | None:
    """Extract the anchor ref_value + tolerance from either the
    whitelist `gold_standard` block or the gold_standards/*.yaml
    `observables[*]` (preferring the one matching the whitelist
    `gold_standard.quantity` to stay quantity-faithful)."""
    citation = case.get("reference") or (gs_doc or {}).get("source", "")
    doi = case.get("doi") or (gs_doc or {}).get("literature_doi")
    wl_gs = case.get("gold_standard") or {}
    target_quantity = wl_gs.get("quantity")

    # Prefer matching observable from gold_standards/*.yaml.
    if gs_doc:
        observables = gs_doc.get("observables") or []
        ob: dict[str, Any] | None = None
        if target_quantity:
            for candidate in observables:
                if candidate.get("name") == target_quantity:
                    ob = candidate
                    break
        if ob is None and observables:
            ob = observables[0]
        if ob is not None:
            tolerance = _tolerance_scalar(ob.get("tolerance"))
            if tolerance is None:
                tolerance = _tolerance_scalar(wl_gs.get("tolerance"))
            if tolerance is None:
                tolerance = 0.1  # conservative default
            ref_value = ob.get("ref_value")
            if isinstance(ref_value, (int, float)):
                return GoldStandardReference(
                    quantity=ob.get("name") or target_quantity or "unknown",
                    ref_value=float(ref_value),
                    unit=ob.get("unit", "") or "",
                    tolerance_pct=float(tolerance),
                    citation=citation or "",
                    doi=doi,
                )
            # Profile-shaped ref_value (list of {x, y/value} dicts) — fall
            # through to wl_gs.reference_values scanning below, which picks
            # the first non-zero scalar anchor (Cp at stagnation, etc.) so
            # the contract engine can produce meaningful PASS/FAIL on
            # cases like naca0012_airfoil whose gold is a Cp profile.

    # Fallback: synthesize from whitelist.yaml `gold_standard` inline.
    refs = wl_gs.get("reference_values") or []
    if not refs:
        return None
    value: float | None = None
    # Scan entries for the first non-zero scalar under any known key.
    # (First entry of a profile is often a trivial anchor like u_plus=0
    # at y_plus=0; skipping-to-first-nonzero gives the engine a
    # pedagogically meaningful ref.)
    value_keys = ("value", "Cf", "f", "Nu", "u", "u_Uinf", "Cp", "u_plus")
    first = refs[0]
    for entry in refs:
        if not isinstance(entry, dict):
            continue
        for key in value_keys:
            if key in entry and isinstance(entry[key], (int, float)):
                if float(entry[key]) != 0.0:
                    value = float(entry[key])
                    first = entry
                    break
        if value is not None:
            break
    # If every entry is zero (or none match), fall back to the very first
    # dict's first matching key (even if zero) to preserve prior behavior.
    if value is None:
        if not isinstance(first, dict):
            return None
        for key in value_keys:
            if key in first and isinstance(first[key], (int, float)):
                value = float(first[key])
                break
    if value is None:
        return None
    tol = _tolerance_scalar(wl_gs.get("tolerance")) or 0.1
    return GoldStandardReference(
        quantity=wl_gs.get("quantity", "unknown"),
        ref_value=value,
        unit=first.get("unit", "") or "",
        tolerance_pct=tol,
        citation=citation or "",
        doi=doi,
    )


def _make_preconditions(gs_doc: dict[str, Any] | None) -> list[Precondition]:
    if not gs_doc:
        return []
    physics_contract = gs_doc.get("physics_contract") or {}
    rows = physics_contract.get("physics_precondition") or []
    out: list[Precondition] = []
    for row in rows:
        out.append(
            Precondition(
                condition=row.get("condition", ""),
                satisfied=bool(row.get("satisfied_by_current_adapter", False)),
                evidence_ref=row.get("evidence_ref"),
                consequence_if_unsatisfied=row.get("consequence_if_unsatisfied"),
            )
        )
    return out


def _make_audit_concerns(
    gs_doc: dict[str, Any] | None,
    measurement_doc: dict[str, Any] | None,
) -> list[AuditConcern]:
    out: list[AuditConcern] = []
    # (1) Contract-status narrative from gold_standards → top-level concern.
    if gs_doc:
        status_narrative = (
            (gs_doc.get("physics_contract") or {}).get("contract_status") or ""
        ).strip()
        if status_narrative:
            out.append(
                AuditConcern(
                    concern_type="CONTRACT_STATUS",
                    summary=(
                        status_narrative.splitlines()[0][:240]
                        if status_narrative
                        else ""
                    ),
                    detail=status_narrative,
                    decision_refs=_extract_decision_refs(status_narrative),
                )
            )
    # (2) Measurement-level audit concerns (fixture or slice_metrics).
    if measurement_doc:
        for concern in measurement_doc.get("audit_concerns", []) or []:
            out.append(
                AuditConcern(
                    concern_type=concern.get("concern_type", "UNKNOWN"),
                    summary=concern.get("summary", ""),
                    detail=concern.get("detail"),
                    decision_refs=concern.get("decision_refs", []) or [],
                )
            )
        # (3) DEC-V61-036 G1: synthesize MISSING_TARGET_QUANTITY concern when
        # the extractor signalled it could not resolve the gold's quantity.
        # Triggers:
        #   - measurement.extraction_source == "no_numeric_quantity" (new post-DEC)
        #   - measurement.extraction_source == "key_quantities_fallback" (legacy
        #     fixtures — this was the silent-substitution bug marker itself)
        #   - measurement.value is None (explicit missing)
        # Surfacing as a first-class concern lets _derive_contract_status
        # hard-FAIL and the UI display the schema failure separately from
        # numeric deviations.
        m = measurement_doc.get("measurement") or {}
        src = m.get("extraction_source")
        g1_miss = (
            src == "no_numeric_quantity"
            or src == "key_quantities_fallback"
            or m.get("value") is None
        )
        if g1_miss:
            gold_quantity = m.get("quantity") or "<unknown>"
            out.append(
                AuditConcern(
                    concern_type="MISSING_TARGET_QUANTITY",
                    summary=(
                        f"Extractor could not locate gold quantity "
                        f"'{gold_quantity}' in run key_quantities."
                    ),
                    detail=(
                        "DEC-V61-036 G1: the case-specific extractor did not "
                        "emit the gold standard's target quantity and the "

 succeeded in 0ms:
"""Validation-report assembly — reads YAML, builds the Screen 4 payload.

Phase 0 scope:
    - list_cases()              → GET /api/cases
    - load_case_detail(id)      → GET /api/cases/{id}
    - build_validation_report() → GET /api/validation-report/{id}

Phase 0 measurement sourcing strategy (in order):
    1. ui/backend/tests/fixtures/{case_id}_measurement.yaml
       (committed alongside the backend for deterministic demo data)
    2. None (returns MeasuredValue=None; UI renders "no run yet")

Phase 3 will extend this to pull from reports/**/slice_metrics.yaml
once live-run streaming is integrated.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from ui.backend.schemas.validation import (
    AttestorCheck,
    AttestorVerdict,
    AuditConcern,
    CaseDetail,
    CaseIndexEntry,
    ContractStatus,
    DecisionLink,
    GoldStandardReference,
    MeasuredValue,
    Precondition,
    RunDescriptor,
    RunSummary,
    ValidationReport,
)


# ---------------------------------------------------------------------------
# Path resolution (repo-root relative)
# ---------------------------------------------------------------------------
# Layout:
#   <repo>/
#     knowledge/whitelist.yaml
#     knowledge/gold_standards/{case_id}.yaml
#     ui/backend/services/validation_report.py  ← this file
#     ui/backend/tests/fixtures/{case_id}_measurement.yaml
_HERE = Path(__file__).resolve()
REPO_ROOT = _HERE.parents[3]
WHITELIST_PATH = REPO_ROOT / "knowledge" / "whitelist.yaml"
GOLD_STANDARDS_DIR = REPO_ROOT / "knowledge" / "gold_standards"
FIXTURE_DIR = _HERE.parents[1] / "tests" / "fixtures"


# ---------------------------------------------------------------------------
# YAML loaders (cached — Phase 0 content is stable during a server lifetime)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _load_whitelist() -> dict[str, dict[str, Any]]:
    """Return {case_id: case_def} from knowledge/whitelist.yaml."""
    if not WHITELIST_PATH.exists():
        return {}
    with WHITELIST_PATH.open("r", encoding="utf-8") as fh:
        doc = yaml.safe_load(fh) or {}
    cases = doc.get("cases", [])
    out: dict[str, dict[str, Any]] = {}
    for entry in cases:
        cid = entry.get("id")
        if cid:
            out[cid] = entry
    return out


def _load_gold_standard(case_id: str) -> dict[str, Any] | None:
    """Read knowledge/gold_standards/{case_id}.yaml if present.

    Two on-disk shapes are supported:
        (A) Single document with top-level `observables: [{name, ref_value,
            tolerance, ...}]` + `physics_contract: {...}`
            (e.g. differential_heated_cavity, turbulent_flat_plate).
        (B) Multi-document — each YAML doc pins one quantity with
            top-level `quantity / reference_values / tolerance`; the
            first doc typically carries `physics_contract`
            (e.g. circular_cylinder_wake, lid_driven_cavity).

    Both shapes are normalised to (A)'s schema before returning, so
    downstream code only ever sees a single `observables: [...]`.
    """
    candidate = GOLD_STANDARDS_DIR / f"{case_id}.yaml"
    if not candidate.exists():
        return None
    with candidate.open("r", encoding="utf-8") as fh:
        docs = [d for d in yaml.safe_load_all(fh) if d]
    if not docs:
        return None

    # Shape A — already has observables[] ⇒ return as-is.
    if len(docs) == 1 and isinstance(docs[0].get("observables"), list):
        return docs[0]

    # Shape B — synthesise an observables[] by flattening each doc.
    primary = docs[0]
    observables: list[dict[str, Any]] = []
    for doc in docs:
        quantity = doc.get("quantity")
        if not quantity:
            continue
        refs = doc.get("reference_values") or []
        ref_value: float | None = None
        unit = ""
        # Scan each reference_values entry for the first non-zero scalar
        # anchor under any known key. (First entry of a profile is often
        # a trivial u_plus=0 at y_plus=0 — picking the next non-zero
        # entry makes the contract engine produce meaningful PASS/FAIL
        # instead of collapsing deviation to 0.)
        scalar_keys = (
            "value", "Cf", "f", "Nu", "u", "u_Uinf", "Cp", "Re_D", "St",
            "u_plus",
        )
        if refs and isinstance(refs[0], dict):
            unit = refs[0].get("unit", "") or ""
        for entry in refs:
            if not isinstance(entry, dict):
                continue
            for scalar_key in scalar_keys:
                val = entry.get(scalar_key)
                if isinstance(val, (int, float)) and float(val) != 0.0:
                    ref_value = float(val)
                    break
            if ref_value is not None:
                break
        # Fallback: if every entry was zero, accept the first scalar we
        # can find (even zero) to preserve prior behaviour.
        if ref_value is None and refs and isinstance(refs[0], dict):
            for scalar_key in scalar_keys:
                val = refs[0].get(scalar_key)
                if isinstance(val, (int, float)):
                    ref_value = float(val)
                    break
        observables.append(
            {
                "name": quantity,
                "ref_value": ref_value if ref_value is not None else 0.0,
                "unit": unit,
                "tolerance": doc.get("tolerance"),
                "description": (refs[0].get("description") if refs and isinstance(refs[0], dict) else None),
            }
        )
    return {
        "observables": observables,
        "physics_contract": primary.get("physics_contract") or {},
        "source": primary.get("source"),
        "literature_doi": primary.get("literature_doi"),
        "schema_version": primary.get("schema_version"),
        "case_id": primary.get("case_info", {}).get("id") or case_id,
    }


def _load_fixture_measurement(case_id: str) -> dict[str, Any] | None:
    """Read the legacy single-run fixture if present.

    Legacy path: ui/backend/tests/fixtures/{case_id}_measurement.yaml
    This is the pre-multi-run layout and is still honored for back-compat.
    If a multi-run directory exists at fixtures/runs/{case_id}/, those runs
    are preferred (see _list_runs + _load_run_measurement).
    """
    candidate = FIXTURE_DIR / f"{case_id}_measurement.yaml"
    if not candidate.exists():
        return None
    with candidate.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


RUNS_DIR = FIXTURE_DIR / "runs"


def _list_run_files(case_id: str) -> list[Path]:
    """Return run fixture paths under fixtures/runs/{case_id}/ sorted by
    run_id ascending. Empty list if the directory doesn't exist.
    """
    case_dir = RUNS_DIR / case_id
    if not case_dir.is_dir():
        return []
    return sorted(case_dir.glob("*_measurement.yaml"))


def _run_id_from_path(p: Path) -> str:
    # lid_driven_cavity/reference_pass_measurement.yaml → reference_pass
    return p.stem.removesuffix("_measurement")


_CATEGORY_ORDER: dict[str, int] = {
    "reference": 0,
    "audit_real_run": 1,
    "real_incident": 2,
    "under_resolved": 3,
    "wrong_model": 4,
    "grid_convergence": 5,
}


def list_runs(case_id: str) -> list[RunDescriptor]:
    """Enumerate curated + legacy runs for a case.

    Ordering (pedagogical, stable across filesystem locales):
    1. `reference` first — students see "what done right looks like"
       at the top.
    2. `real_incident` next — actual production measurement, auditable
       reality.
    3. `under_resolved` / `wrong_model` — teaching variants.
    4. `grid_convergence` last — mesh-sweep runs live behind the Mesh
       tab and don't belong in the Compare run-picker's first page of
       attention.
    Within a category, sort by run_id ascending (mesh_20 before
    mesh_160 via zero-padded numeric comparison for `mesh_N` ids).
    Legacy `{case_id}_measurement.yaml` is exposed as run_id='legacy'
    only when the multi-run dir is empty.
    """
    runs: list[RunDescriptor] = []
    for path in _list_run_files(case_id):
        try:
            with path.open("r", encoding="utf-8") as fh:
                doc = yaml.safe_load(fh) or {}
        except Exception:
            continue
        md = doc.get("run_metadata") or {}
        run_id = md.get("run_id") or _run_id_from_path(path)
        runs.append(
            RunDescriptor(
                run_id=run_id,
                label_zh=md.get("label_zh") or run_id.replace("_", " "),
                label_en=md.get("label_en", "") or "",
                description_zh=md.get("description_zh", "") or "",
                category=md.get("category", "reference"),
                expected_verdict=md.get("expected_verdict", "UNKNOWN"),
            )
        )
    if runs:
        def _sort_key(r: RunDescriptor) -> tuple[int, int, str]:
            cat_rank = _CATEGORY_ORDER.get(r.category, 99)
            # Numeric-aware secondary sort for mesh_N ids so mesh_20 sits
            # before mesh_160 instead of lexicographic (`mesh_160` < `mesh_20`).
            if r.run_id.startswith("mesh_"):
                try:
                    n = int(r.run_id.split("_", 1)[1])
                except ValueError:
                    n = 0

exec
/bin/zsh -lc "sed -n '751,980p' ui/backend/services/validation_report.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
        else:
            status = "UNKNOWN"
        # Run distribution for the catalog-card badge. Evaluate every run
        # through the actual contract engine — never report `expected_verdict`,
        # which is only a curator hint and can drift from the live contract
        # (e.g. a `PASS`-hinted run whose gold arms a silent-pass hazard).
        runs = list_runs(cid)
        verdict_counts: dict[str, int] = {}
        for r in runs:
            run_doc = _load_run_measurement(cid, r.run_id)
            run_audits = _make_audit_concerns(gs, run_doc)
            run_measurement = _make_measurement(run_doc)
            if gs_ref is not None:
                run_status, *_ = _derive_contract_status(
                    gs_ref, run_measurement, preconditions, run_audits
                )
            else:
                run_status = "UNKNOWN"
            verdict_counts[run_status] = verdict_counts.get(run_status, 0) + 1
        run_summary = RunSummary(total=len(runs), verdict_counts=verdict_counts)
        out.append(
            CaseIndexEntry(
                case_id=cid,
                name=case.get("name", cid),
                flow_type=case.get("flow_type", "UNKNOWN"),
                geometry_type=case.get("geometry_type", "UNKNOWN"),
                turbulence_model=case.get("turbulence_model", "UNKNOWN"),
                has_gold_standard=gs is not None,
                has_measurement=measurement is not None,
                run_summary=run_summary,
                contract_status=status,
            )
        )
    return out


def load_case_detail(case_id: str) -> CaseDetail | None:
    whitelist = _load_whitelist()
    case = whitelist.get(case_id)
    if case is None:
        return None
    gs = _load_gold_standard(case_id)
    gs_ref = _make_gold_reference(case, gs)
    preconditions = _make_preconditions(gs)
    narrative = None
    if gs:
        narrative = (gs.get("physics_contract") or {}).get("contract_status")
        if isinstance(narrative, str):
            narrative = narrative.strip() or None
    return CaseDetail(
        case_id=case_id,
        name=case.get("name", case_id),
        reference=case.get("reference"),
        doi=case.get("doi"),
        flow_type=case.get("flow_type", "UNKNOWN"),
        geometry_type=case.get("geometry_type", "UNKNOWN"),
        compressibility=case.get("compressibility"),
        steady_state=case.get("steady_state"),
        solver=case.get("solver"),
        turbulence_model=case.get("turbulence_model", "UNKNOWN"),
        parameters=case.get("parameters") or {},
        gold_standard=gs_ref,
        preconditions=preconditions,
        contract_status_narrative=narrative,
    )


def build_validation_report(
    case_id: str,
    run_id: str | None = None,
) -> ValidationReport | None:
    """Build the Screen-4 validation report for a case.

    Run resolution:
    - If `run_id` is None, resolves to the first 'reference' run (so
      default view shows PASS narrative where curated), falling back to
      any curated run, then to the legacy {case_id}_measurement.yaml
      fixture.
    - If `run_id` is provided but doesn't exist, returns None (treat
      as 404 at the route layer).
    """
    case_detail = load_case_detail(case_id)
    if case_detail is None or case_detail.gold_standard is None:
        return None
    gs = _load_gold_standard(case_id)

    # Resolve which run's measurement to load.
    if run_id is None:
        resolved_run_id = _pick_default_run_id(case_id)
    else:
        resolved_run_id = run_id

    if resolved_run_id is None:
        # No fixture at all for this case — report renders with measurement=None.
        measurement_doc = None
    else:
        measurement_doc = _load_run_measurement(case_id, resolved_run_id)
        if measurement_doc is None and run_id is not None:
            # User explicitly asked for an unknown run_id.
            return None
    measurement = _make_measurement(measurement_doc)
    preconditions = case_detail.preconditions
    audit_concerns = _make_audit_concerns(gs, measurement_doc)
    decisions_trail = _make_decisions_trail(measurement_doc)
    status, deviation, within, lower, upper = _derive_contract_status(
        case_detail.gold_standard, measurement, preconditions, audit_concerns
    )
    # DEC-V61-039: reconcile with comparison_report's pointwise profile
    # verdict. For LDC (the only current gold-overlay case) 11/17 profile
    # points pass → PARTIAL, while scalar contract_status is PASS. Surfacing
    # both honestly lets the UI explain the split-brain rather than hiding
    # the profile-level truth behind a scalar PASS. Non-blocking: if the
    # comparison_report service is absent or the case is not gold-overlay,
    # profile_verdict stays None.
    profile_verdict, profile_pass, profile_total = _compute_profile_verdict(
        case_id, resolved_run_id
    )
    attestation = _make_attestation(measurement_doc)
    return ValidationReport(
        case=case_detail,
        gold_standard=case_detail.gold_standard,
        measurement=measurement,
        contract_status=status,
        deviation_pct=deviation,
        within_tolerance=within,
        tolerance_lower=lower,
        tolerance_upper=upper,
        audit_concerns=audit_concerns,
        preconditions=preconditions,
        decisions_trail=decisions_trail,
        profile_verdict=profile_verdict,
        profile_pass_count=profile_pass,
        profile_total_count=profile_total,
        attestation=attestation,
    )


def _compute_profile_verdict(
    case_id: str, run_label: str | None
) -> tuple[str | None, int | None, int | None]:
    """DEC-V61-039: compute pointwise profile verdict from comparison_report.

    Returns (verdict, pass_count, total_count). All three None when:
      - case is not gold-overlay (not LDC),
      - no sample data available for the run,
      - comparison_report service raises (guarded).

    Currently only LDC has the uCenterline sample pipeline wired. When
    DEC-V61-037 per-case plots land, other cases will emit their own
    profile samples and become gold-overlay too.
    """
    if run_label is None:
        return (None, None, None)
    try:
        from ui.backend.services import comparison_report as cr

        # Only LDC is currently in the gold-overlay set (DEC-V61-034). Other
        # cases are visual-only or scalar; profile_verdict stays None for
        # them. Reaching into the module-private set keeps this DEC tight —
        # if the set expands later, the verdict surfaces automatically.
        if case_id not in getattr(cr, "_GOLD_OVERLAY_CASES", set()):
            return (None, None, None)
        ctx = cr.build_report_context(case_id, run_label)
    except Exception:  # noqa: BLE001
        return (None, None, None)
    if not ctx or ctx.get("visual_only"):
        return (None, None, None)
    verdict = ctx.get("verdict")
    metrics = ctx.get("metrics") or {}
    if verdict not in ("PASS", "PARTIAL", "FAIL"):
        return (None, None, None)
    return (
        verdict,
        metrics.get("n_pass"),
        metrics.get("n_total"),
    )

exec
/bin/zsh -lc "sed -n '1,180p' ui/backend/tests/test_comparator_gates_g3_g4_g5.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '181,360p' ui/backend/tests/test_comparator_gates_g3_g4_g5.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
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

 succeeded in 0ms:
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
I’ve finished the target-file read. The main risk surface is now narrowing to three things: whether `U_ref` is ever real rather than defaulted, whether “last step” semantics match unsteady logs, and whether the current tests actually cover the claimed boundary conditions.
exec
/bin/zsh -lc 'rg -n "u_ref|U_ref|boundary_conditions|check_all_gates|_derive_contract_status|VELOCITY_OVERFLOW|TURBULENCE_NEGATIVE|CONTINUITY_DIVERGED" -S scripts/phase5_audit_run.py src/comparator_gates.py ui/backend/services/validation_report.py ui/backend/tests/test_comparator_gates_g3_g4_g5.py' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
ui/backend/tests/test_comparator_gates_g3_g4_g5.py:86:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
ui/backend/tests/test_comparator_gates_g3_g4_g5.py:89:    assert g5[0].concern_type == "CONTINUITY_DIVERGED"
ui/backend/tests/test_comparator_gates_g3_g4_g5.py:100:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
ui/backend/tests/test_comparator_gates_g3_g4_g5.py:108:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
ui/backend/tests/test_comparator_gates_g3_g4_g5.py:119:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
ui/backend/tests/test_comparator_gates_g3_g4_g5.py:134:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
ui/backend/tests/test_comparator_gates_g3_g4_g5.py:144:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
ui/backend/tests/test_comparator_gates_g3_g4_g5.py:155:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
ui/backend/tests/test_comparator_gates_g3_g4_g5.py:158:    assert g3[0].concern_type == "VELOCITY_OVERFLOW"
ui/backend/tests/test_comparator_gates_g3_g4_g5.py:165:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
ui/backend/tests/test_comparator_gates_g3_g4_g5.py:181:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
ui/backend/tests/test_comparator_gates_g3_g4_g5.py:190:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
ui/backend/tests/test_comparator_gates_g3_g4_g5.py:208:    violations = cg.check_all_gates(log_path=_REAL_BFS_LOG, vtk_dir=None, U_ref=1.0)
ui/backend/tests/test_comparator_gates_g3_g4_g5.py:224:    """Fixture with VELOCITY_OVERFLOW concern must hard-FAIL the verdict."""
ui/backend/tests/test_comparator_gates_g3_g4_g5.py:230:    from ui.backend.services.validation_report import _derive_contract_status
ui/backend/tests/test_comparator_gates_g3_g4_g5.py:248:            concern_type="VELOCITY_OVERFLOW",
ui/backend/tests/test_comparator_gates_g3_g4_g5.py:252:    status, deviation, within, _, _ = _derive_contract_status(
ui/backend/tests/test_comparator_gates_g3_g4_g5.py:255:    # DEC-V61-036b: VELOCITY_OVERFLOW overrides a "within band" comparator PASS.
ui/backend/tests/test_comparator_gates_g3_g4_g5.py:269:    from ui.backend.services.validation_report import _derive_contract_status
ui/backend/tests/test_comparator_gates_g3_g4_g5.py:279:    concerns = [AuditConcern(concern_type="CONTINUITY_DIVERGED", summary="cum=-1434")]
ui/backend/tests/test_comparator_gates_g3_g4_g5.py:280:    status, _, _, _, _ = _derive_contract_status(gs, m, [], concerns)
ui/backend/tests/test_comparator_gates_g3_g4_g5.py:290:    from ui.backend.services.validation_report import _derive_contract_status
ui/backend/tests/test_comparator_gates_g3_g4_g5.py:300:    status, _, within, _, _ = _derive_contract_status(gs, m, [], [])
ui/backend/services/validation_report.py:479:        # Surfacing as a first-class concern lets _derive_contract_status
ui/backend/services/validation_report.py:537:def _derive_contract_status(
ui/backend/services/validation_report.py:563:    #   G3  VELOCITY_OVERFLOW           — |U|_max > 100·U_ref
ui/backend/services/validation_report.py:564:    #   G4  TURBULENCE_NEGATIVE         — k/eps/omega < 0 at last iter or overflow
ui/backend/services/validation_report.py:565:    #   G5  CONTINUITY_DIVERGED         — sum_local > 1e-2 or |cum| > 1
ui/backend/services/validation_report.py:573:        "VELOCITY_OVERFLOW",
ui/backend/services/validation_report.py:574:        "TURBULENCE_NEGATIVE",
ui/backend/services/validation_report.py:575:        "CONTINUITY_DIVERGED",
ui/backend/services/validation_report.py:748:            status, *_ = _derive_contract_status(
ui/backend/services/validation_report.py:764:                run_status, *_ = _derive_contract_status(
ui/backend/services/validation_report.py:855:    status, deviation, within, lower, upper = _derive_contract_status(
scripts/phase5_audit_run.py:45:    check_all_gates,
scripts/phase5_audit_run.py:298:    u_ref: float = 1.0,
scripts/phase5_audit_run.py:406:            gate_violations = check_all_gates(
scripts/phase5_audit_run.py:409:                U_ref=u_ref,
src/comparator_gates.py:4:  * G3 VELOCITY_OVERFLOW  — |U|_max > K * U_ref (K=100 default). VTK-based,
src/comparator_gates.py:6:  * G4 TURBULENCE_NEGATIVE — k/epsilon/omega min < 0 at last bounding line
src/comparator_gates.py:8:  * G5 CONTINUITY_DIVERGED — last-iter sum_local > 1e-2 OR |cumulative| > 1.
src/comparator_gates.py:55:G3_VELOCITY_RATIO_MAX = 100.0     # |U|_max / U_ref
src/comparator_gates.py:75:    concern_type: str     # "VELOCITY_OVERFLOW" | "TURBULENCE_NEGATIVE" | "CONTINUITY_DIVERGED"
src/comparator_gates.py:255:    U_ref: float,
src/comparator_gates.py:257:    """G3: |U|_max > K * U_ref OR epsilon max > G3_EPSILON_PROXY_MAX."""
src/comparator_gates.py:259:    threshold = G3_VELOCITY_RATIO_MAX * max(U_ref, 1e-6)
src/comparator_gates.py:269:                concern_type="VELOCITY_OVERFLOW",
src/comparator_gates.py:271:                    f"|U|_max={u_max:.3g} exceeds {G3_VELOCITY_RATIO_MAX:.0f}·U_ref "
src/comparator_gates.py:277:                    f"{G3_VELOCITY_RATIO_MAX:.0f}·U_ref sanity ceiling "
src/comparator_gates.py:278:                    f"({threshold:.6g}, U_ref={U_ref}). This indicates "
src/comparator_gates.py:283:                evidence={"u_max": u_max, "U_ref": U_ref, "threshold": threshold},
src/comparator_gates.py:297:                        concern_type="VELOCITY_OVERFLOW",
src/comparator_gates.py:337:                    concern_type="TURBULENCE_NEGATIVE",
src/comparator_gates.py:361:                    concern_type="TURBULENCE_NEGATIVE",
src/comparator_gates.py:399:                concern_type="CONTINUITY_DIVERGED",
src/comparator_gates.py:424:                concern_type="CONTINUITY_DIVERGED",
src/comparator_gates.py:449:def check_all_gates(
src/comparator_gates.py:452:    U_ref: float = 1.0,
src/comparator_gates.py:458:    `ui/backend/services/validation_report._derive_contract_status`
src/comparator_gates.py:466:    violations.extend(_check_g3_velocity_overflow(log_stats, vtk_dir, U_ref))

exec
/bin/zsh -lc 'rg -n "circular_cylinder_wake|naca0012_airfoil|lid_driven_cavity|backward_facing_step|turbulent_flat_plate|plane_channel_flow|differential_heated_cavity|rayleigh_benard_convection|duct_flow|impinging_jet" knowledge/whitelist.yaml knowledge/gold_standards -S' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
knowledge/whitelist.yaml:6:  - id: lid_driven_cavity
knowledge/whitelist.yaml:28:      # lid_driven_cavity.yaml header comment for full-table traceability.
knowledge/whitelist.yaml:51:  - id: backward_facing_step
knowledge/whitelist.yaml:56:    geometry_type: BACKWARD_FACING_STEP
knowledge/whitelist.yaml:71:  - id: circular_cylinder_wake
knowledge/whitelist.yaml:94:  - id: turbulent_flat_plate
knowledge/whitelist.yaml:128:  - id: duct_flow
knowledge/whitelist.yaml:149:  - id: differential_heated_cavity
knowledge/whitelist.yaml:177:  - id: plane_channel_flow
knowledge/whitelist.yaml:206:  - id: impinging_jet
knowledge/whitelist.yaml:211:    geometry_type: IMPINGING_JET
knowledge/whitelist.yaml:234:  - id: naca0012_airfoil
knowledge/whitelist.yaml:257:  - id: rayleigh_benard_convection
knowledge/gold_standards/lid_driven_cavity.yaml:80:  id: lid_driven_cavity
knowledge/gold_standards/lid_driven_cavity.yaml:128:  id: lid_driven_cavity
knowledge/gold_standards/lid_driven_cavity.yaml:160:  id: lid_driven_cavity
knowledge/gold_standards/circular_cylinder_wake.yaml:41:  id: circular_cylinder_wake
knowledge/gold_standards/circular_cylinder_wake.yaml:64:  id: circular_cylinder_wake
knowledge/gold_standards/circular_cylinder_wake.yaml:87:  id: circular_cylinder_wake
knowledge/gold_standards/circular_cylinder_wake.yaml:119:  id: circular_cylinder_wake
knowledge/gold_standards/differential_heated_cavity.yaml:2:case_id: differential_heated_cavity
knowledge/gold_standards/turbulent_flat_plate.yaml:2:case_id: turbulent_flat_plate
knowledge/gold_standards/turbulent_flat_plate.yaml:26:      evidence_ref: ".planning/STATE.md records turbulent_flat_plate mesh at 80 y-cells with 4:1 wall grading. Blasius δ_99=5·√(ν·x/U); at U=1, ν=1/50000, x=0.5: δ_99=0.0224m. 80 cells over H=1.0 with 4:1 grading → ~50 cells within y<0.0224, well-resolved."
knowledge/gold_standards/naca0012_airfoil.yaml:2:case_id: naca0012_airfoil
knowledge/gold_standards/impinging_jet.yaml:26:  id: impinging_jet
knowledge/gold_standards/impinging_jet.yaml:29:  geometry_type: IMPINGING_JET
knowledge/gold_standards/axisymmetric_impinging_jet.yaml:2:case_id: axisymmetric_impinging_jet
knowledge/gold_standards/axisymmetric_impinging_jet.yaml:3:legacy_case_id: impinging_jet
knowledge/gold_standards/axisymmetric_impinging_jet.yaml:4:legacy_source_file: knowledge/gold_standards/impinging_jet.yaml
knowledge/gold_standards/axisymmetric_impinging_jet.yaml:20:      evidence_ref: "whitelist declares simpleFoam which is isothermal; no energy equation solved. Adapter has _generate_impinging_jet (src/foam_agent_adapter.py:4257+) that sets up a buoyantFoam-path case, but the whitelist configuration takes a simpleFoam path that never invokes this generator for the thermal observable."
knowledge/gold_standards/axisymmetric_impinging_jet.yaml:28:  solver_reuse: impinging_jet
knowledge/gold_standards/axisymmetric_impinging_jet.yaml:30:    reference_case: impinging_jet
knowledge/gold_standards/axisymmetric_impinging_jet.yaml:33:    reference_case: impinging_jet
knowledge/gold_standards/plane_channel_flow.yaml:31:  id: plane_channel_flow
knowledge/gold_standards/backward_facing_step_steady.yaml:2:case_id: backward_facing_step_steady
knowledge/gold_standards/backward_facing_step_steady.yaml:3:legacy_case_id: backward_facing_step
knowledge/gold_standards/backward_facing_step_steady.yaml:4:legacy_source_file: knowledge/gold_standards/backward_facing_step.yaml
knowledge/gold_standards/backward_facing_step_steady.yaml:23:  solver_reuse: backward_facing_step
knowledge/gold_standards/backward_facing_step_steady.yaml:25:    reference_case: backward_facing_step
knowledge/gold_standards/backward_facing_step_steady.yaml:28:    reference_case: backward_facing_step
knowledge/gold_standards/lid_driven_cavity_benchmark.yaml:2:case_id: lid_driven_cavity_benchmark
knowledge/gold_standards/lid_driven_cavity_benchmark.yaml:3:legacy_case_id: lid_driven_cavity
knowledge/gold_standards/lid_driven_cavity_benchmark.yaml:4:legacy_source_file: knowledge/gold_standards/lid_driven_cavity.yaml
knowledge/gold_standards/lid_driven_cavity_benchmark.yaml:23:  solver_reuse: lid_driven_cavity
knowledge/gold_standards/lid_driven_cavity_benchmark.yaml:25:    reference_case: lid_driven_cavity
knowledge/gold_standards/lid_driven_cavity_benchmark.yaml:28:    reference_case: lid_driven_cavity
knowledge/gold_standards/duct_flow.yaml:2:case_id: duct_flow
knowledge/gold_standards/duct_flow.yaml:17:  `duct_flow` with Jones 1976 rectangular-duct correlation — honest physics
knowledge/gold_standards/duct_flow.yaml:62:    reference_case: duct_flow
knowledge/gold_standards/rayleigh_benard_convection.yaml:2:case_id: rayleigh_benard_convection
knowledge/gold_standards/rayleigh_benard_convection.yaml:22:  contract_status: "COMPATIBLE — all preconditions satisfied at Ra=1e6. NOT transferable to Ra≥1e9 without mesh refinement (see differential_heated_cavity physics_contract for the high-Ra regime)."
knowledge/gold_standards/fully_developed_plane_channel_flow.yaml:2:case_id: fully_developed_plane_channel_flow
knowledge/gold_standards/fully_developed_plane_channel_flow.yaml:3:legacy_case_id: plane_channel_flow
knowledge/gold_standards/fully_developed_plane_channel_flow.yaml:4:legacy_source_file: knowledge/gold_standards/plane_channel_flow.yaml
knowledge/gold_standards/fully_developed_plane_channel_flow.yaml:29:  solver_reuse: plane_channel_flow
knowledge/gold_standards/fully_developed_plane_channel_flow.yaml:31:    reference_case: plane_channel_flow
knowledge/gold_standards/fully_developed_plane_channel_flow.yaml:34:    reference_case: plane_channel_flow
knowledge/gold_standards/cylinder_crossflow.yaml:3:legacy_case_id: circular_cylinder_wake
knowledge/gold_standards/cylinder_crossflow.yaml:4:legacy_source_file: knowledge/gold_standards/circular_cylinder_wake.yaml
knowledge/gold_standards/cylinder_crossflow.yaml:26:  solver_reuse: circular_cylinder_wake
knowledge/gold_standards/cylinder_crossflow.yaml:28:    reference_case: circular_cylinder_wake
knowledge/gold_standards/cylinder_crossflow.yaml:31:    reference_case: circular_cylinder_wake
knowledge/gold_standards/backward_facing_step.yaml:31:  id: backward_facing_step
knowledge/gold_standards/backward_facing_step.yaml:34:  geometry_type: BACKWARD_FACING_STEP
knowledge/gold_standards/backward_facing_step.yaml:54:  id: backward_facing_step
knowledge/gold_standards/backward_facing_step.yaml:57:  geometry_type: BACKWARD_FACING_STEP
knowledge/gold_standards/backward_facing_step.yaml:85:  id: backward_facing_step
knowledge/gold_standards/backward_facing_step.yaml:88:  geometry_type: BACKWARD_FACING_STEP
knowledge/gold_standards/backward_facing_step.yaml:117:  id: backward_facing_step
knowledge/gold_standards/backward_facing_step.yaml:120:  geometry_type: BACKWARD_FACING_STEP

exec
/bin/zsh -lc 'rg -n "boundary_conditions" knowledge src scripts ui/backend/tests | head -n 200' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
src/task_runner.py:243:            boundary_conditions={**chain.get("boundary_conditions", {}), **parameters},  # includes aspect_ratio, plate_length, etc.
src/knowledge_db.py:74:                    boundary_conditions=case.get("boundary_conditions", {}),
src/knowledge_db.py:117:            boundary_conditions, mesh_strategy, gold_standard. Returns None if not found.
src/knowledge_db.py:187:            "boundary_conditions": case.get("boundary_conditions", {}),
src/models.py:77:    boundary_conditions: Dict[str, Any] = field(default_factory=dict)
src/notion_client.py:138:            boundary_conditions={},
src/foam_agent_adapter.py:1824:        aspect_ratio = float(task_spec.boundary_conditions.get("aspect_ratio", 1.0)) if task_spec.boundary_conditions else 1.0
src/foam_agent_adapter.py:1825:        # Infer from Ra when boundary_conditions.aspect_ratio not set:
src/foam_agent_adapter.py:1828:        if aspect_ratio == 1.0 and not (task_spec.boundary_conditions and task_spec.boundary_conditions.get("aspect_ratio")):
src/foam_agent_adapter.py:1854:        # Store dT/L in boundary_conditions for the extractor (TaskSpec is local to this call)
src/foam_agent_adapter.py:1855:        if task_spec.boundary_conditions is None:
src/foam_agent_adapter.py:1856:            task_spec.boundary_conditions = {}
src/foam_agent_adapter.py:1857:        task_spec.boundary_conditions["dT"] = dT
src/foam_agent_adapter.py:1858:        task_spec.boundary_conditions["L"] = L
src/foam_agent_adapter.py:1864:        task_spec.boundary_conditions["wall_coord_hot"] = 0.0
src/foam_agent_adapter.py:1865:        task_spec.boundary_conditions["wall_coord_cold"] = L
src/foam_agent_adapter.py:1866:        task_spec.boundary_conditions["T_hot_wall"] = T_hot
src/foam_agent_adapter.py:1867:        task_spec.boundary_conditions["T_cold_wall"] = T_cold
src/foam_agent_adapter.py:1868:        task_spec.boundary_conditions["wall_bc_type"] = "fixedValue"
src/foam_agent_adapter.py:3122:        if task_spec.boundary_conditions is None:
src/foam_agent_adapter.py:3123:            task_spec.boundary_conditions = {}
src/foam_agent_adapter.py:3124:        task_spec.boundary_conditions["channel_D"] = D
src/foam_agent_adapter.py:3125:        task_spec.boundary_conditions["channel_half_height"] = half_D
src/foam_agent_adapter.py:3126:        task_spec.boundary_conditions["nu"] = nu_val
src/foam_agent_adapter.py:3127:        task_spec.boundary_conditions["U_bulk"] = U_bulk
src/foam_agent_adapter.py:3537:        L = float(task_spec.boundary_conditions.get("plate_length", 1.0)) if task_spec.boundary_conditions else 1.0
src/foam_agent_adapter.py:4274:        if task_spec.boundary_conditions is None:
src/foam_agent_adapter.py:4275:            task_spec.boundary_conditions = {}
src/foam_agent_adapter.py:4276:        task_spec.boundary_conditions["cylinder_D"] = D
src/foam_agent_adapter.py:4277:        task_spec.boundary_conditions["U_ref"] = U_bulk
src/foam_agent_adapter.py:5111:        if task_spec.boundary_conditions is None:
src/foam_agent_adapter.py:5112:            task_spec.boundary_conditions = {}
src/foam_agent_adapter.py:5113:        task_spec.boundary_conditions["D_nozzle"] = D
src/foam_agent_adapter.py:5114:        task_spec.boundary_conditions["T_plate"] = T_plate
src/foam_agent_adapter.py:5115:        task_spec.boundary_conditions["T_inlet"] = T_inlet
src/foam_agent_adapter.py:5116:        task_spec.boundary_conditions["wall_coord_plate"] = z_max
src/foam_agent_adapter.py:5117:        task_spec.boundary_conditions["wall_bc_type"] = "fixedValue"
src/foam_agent_adapter.py:5929:        bc = task_spec.boundary_conditions or {}
src/foam_agent_adapter.py:5933:        # DEC-V61-044: plumb chord + U_inf + rho into boundary_conditions
src/foam_agent_adapter.py:5937:        task_spec.boundary_conditions = bc
src/foam_agent_adapter.py:6790:        """渲染 blockMeshDict，支持 TaskSpec boundary_conditions 参数覆盖。"""
src/foam_agent_adapter.py:6791:        # 允许通过 boundary_conditions 覆盖顶盖速度
src/foam_agent_adapter.py:6793:            task_spec.boundary_conditions.get("lid_velocity_u", 1.0)
src/foam_agent_adapter.py:7519:        # migrates into boundary_conditions.
src/foam_agent_adapter.py:7529:            hd = (task_spec.boundary_conditions or {}).get("hydraulic_diameter")
src/foam_agent_adapter.py:7644:        `parameters` into `boundary_conditions` (src/task_runner.py:232-243);
src/foam_agent_adapter.py:7655:        return "hydraulic_diameter" in (task_spec.boundary_conditions or {})
src/foam_agent_adapter.py:7746:        bc = task_spec.boundary_conditions or {}
src/foam_agent_adapter.py:7842:        bc = task_spec.boundary_conditions or {}
src/foam_agent_adapter.py:8062:        plumbed through task_spec.boundary_conditions by the generator
src/foam_agent_adapter.py:8071:        bc = task_spec.boundary_conditions or {}
src/foam_agent_adapter.py:8166:        bc = task_spec.boundary_conditions or {}
src/foam_agent_adapter.py:8272:        bc = task_spec.boundary_conditions or {}
src/foam_agent_adapter.py:8476:        task_spec.boundary_conditions by _generate_impinging_jet).
src/foam_agent_adapter.py:8484:        bc = task_spec.boundary_conditions or {}
src/foam_agent_adapter.py:8594:        bc = task_spec.boundary_conditions or {}
src/error_attributor.py:692:        bcs = task_spec.boundary_conditions
knowledge/whitelist.yaml:18:    boundary_conditions:
knowledge/gold_standards/lid_driven_cavity.yaml:85:  boundary_conditions:
knowledge/gold_standards/lid_driven_cavity.yaml:133:  boundary_conditions:
knowledge/gold_standards/naca0012_airfoil.yaml:15:  geometry_assumption: "2D NACA0012 airfoil in external incompressible flow at 0° angle of attack; thin-span x-z plane mesh with empty side patches; chord length 1.0 by default (task_spec.boundary_conditions.chord_length override supported)"

exec
/bin/zsh -lc "sed -n '1,320p' knowledge/whitelist.yaml" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '220,280p' src/task_runner.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
            failed=failed,
            errors=errors,
            results=results,
            attribution_reports=attribution_reports,
            systematic_patterns=systematic_patterns,
        )

    def _task_spec_from_case_id(self, case_id: str) -> TaskSpec:
        """从 knowledge_db 通过 case_id 还原 TaskSpec。"""
        chain = self._db.get_execution_chain(case_id)
        if chain is None:
            raise ValueError(f"Unknown case_id: {case_id}")
        parameters = chain.get("parameters", {})
        return TaskSpec(
            name=chain.get("case_name", case_id),
            geometry_type=GeometryType(chain.get("geometry_type", "SIMPLE_GRID")),
            flow_type=FlowType(chain.get("flow_type", "INTERNAL")),
            steady_state=SteadyState(chain.get("steady_state", "STEADY")),
            compressibility=Compressibility(chain.get("compressibility", "INCOMPRESSIBLE")),
            Re=parameters.get("Re"),
            Ra=parameters.get("Ra"),
            Re_tau=parameters.get("Re_tau"),
            Ma=parameters.get("Ma"),
            boundary_conditions={**chain.get("boundary_conditions", {}), **parameters},  # includes aspect_ratio, plate_length, etc.
            description=chain.get("reference", ""),
        )

    def _ensure_batch_comparison(self, case_id: str, report: RunReport) -> ComparisonResult:
        """确保 report 有 comparison_result（如果没有则尝试生成）。"""
        if report.comparison_result is not None:
            return report.comparison_result
        if not report.execution_result.success:
            return ComparisonResult(
                passed=False,
                summary=report.execution_result.error_message or "Execution failed before comparison",
            )
        gold = self._db.load_gold_standard(case_id) or self._db.load_gold_standard(report.task_spec.name)
        if gold is None:
            return ComparisonResult(
                passed=False,
                summary=f"No gold standard found for case '{case_id}'",
            )
        return self._comparator.compare(report.execution_result, gold)

    def _analyze_systematic_patterns(
        self,
        case_ids: List[str],
        results: List[ComparisonResult],
        attribution_reports: List[Optional[AttributionReport]],
    ) -> List[SystematicPattern]:
        """检测批量执行中的系统性误差模式（frequency > 0.5）。"""
        cause_counts: Dict[str, List[str]] = {}
        for case_id, attr in zip(case_ids, attribution_reports):
            if attr is None:
                continue
            cause = attr.primary_cause
            if cause not in ("unknown", "none", ""):
                cause_counts.setdefault(cause, []).append(case_id)

        patterns = []
        total = len(case_ids)

 succeeded in 0ms:
# 冷启动白名单：10 条经典验证案例
# 来源均为公开发表论文，可作为 Gold Standard
# 覆盖: 内部/外部/自然对流, 稳态/瞬态, 湍流/层流

cases:
  - id: lid_driven_cavity
    name: "Lid-Driven Cavity"
    reference: "Ghia et al. 1982"
    doi: "10.1016/0021-9991(82)90058-4"
    flow_type: INTERNAL
    geometry_type: SIMPLE_GRID
    compressibility: INCOMPRESSIBLE
    steady_state: STEADY
    solver: icoFoam
    turbulence_model: laminar
    parameters:
      Re: 100
    boundary_conditions:
      top_wall_u: 1.0
      other_walls_u: 0.0
    gold_standard:
      # Q-5 Path A closure (2026-04-21, DEC-V61-030): re-transcribed from Ghia
      # 1982 Table I Re=100 after the Phase 0 synthesized values failed external
      # cross-check (prior gold said u=+0.025 at y=0.5; Ghia actual is -0.20581).
      # Source: Ghia, Ghia & Shin 1982, J. Comput. Phys. 47, 387-411 Table I col 2.
      # Values on the uniform 17-point y grid are interpolated linearly from
      # Ghia's 17 native non-uniform y points. Matches knowledge/gold_standards/
      # lid_driven_cavity.yaml header comment for full-table traceability.
      quantity: u_centerline
      description: "Ghia 1982 Re=100 u velocity along vertical centerline (x=0.5), uniform 17-point y grid"
      reference_values:
        - {y: 0.0000, u:  0.00000}
        - {y: 0.0625, u: -0.04192}
        - {y: 0.1250, u: -0.07671}
        - {y: 0.1875, u: -0.10936}
        - {y: 0.2500, u: -0.14085}
        - {y: 0.3125, u: -0.16648}
        - {y: 0.3750, u: -0.18622}
        - {y: 0.4375, u: -0.20597}
        - {y: 0.5000, u: -0.20581}
        - {y: 0.5625, u: -0.16880}
        - {y: 0.6250, u: -0.12711}
        - {y: 0.6875, u: -0.05260}
        - {y: 0.7500, u:  0.03369}
        - {y: 0.8125, u:  0.15538}
        - {y: 0.8750, u:  0.33656}
        - {y: 0.9375, u:  0.61714}
        - {y: 1.0000, u:  1.00000}
      tolerance: 0.05  # 5% 相对误差

  - id: backward_facing_step
    name: "Backward-Facing Step"
    reference: "Driver & Seegmiller 1985"
    doi: "10.2514/3.9086"
    flow_type: INTERNAL
    geometry_type: BACKWARD_FACING_STEP
    compressibility: INCOMPRESSIBLE
    steady_state: STEADY
    solver: simpleFoam
    turbulence_model: k-epsilon
    parameters:
      Re: 7600
      expansion_ratio: 1.125
    gold_standard:
      quantity: reattachment_length
      description: "再附长度 Xr/H（H 为台阶高度）"
      reference_values:
        - {value: 6.26, unit: "Xr/H"}
      tolerance: 0.10  # 10% 相对误差

  - id: circular_cylinder_wake
    name: "Circular Cylinder Wake"
    reference: "Williamson 1996"
    doi: "10.1146/annurev.fl.28.010196.002421"
    flow_type: EXTERNAL
    geometry_type: BODY_IN_CHANNEL
    compressibility: INCOMPRESSIBLE
    steady_state: TRANSIENT
    solver: pimpleFoam
    # Re=100 is in the laminar 2D Karman vortex shedding regime (Williamson 1996:
    # 3D transition ~Re=190). k-omega SST over-dissipates the wake → under-predicts
    # St; laminar is physically correct. A-class metadata correction per
    # docs/whitelist_audit.md §3. reference_values untouched. (DEC-V61-005)
    turbulence_model: laminar
    parameters:
      Re: 100
    gold_standard:
      quantity: strouhal_number
      description: "斯特劳哈尔数 St = fD/U"
      reference_values:
        - {value: 0.165, unit: "dimensionless"}
      tolerance: 0.05  # 5% 相对误差

  - id: turbulent_flat_plate
    name: "Laminar Flat Plate (Zero Pressure Gradient, Re_x ≤ 5e4)"  # Name retained for case_id stability; physics is laminar Blasius
    reference: "Blasius 1908 / Schlichting Boundary Layer Theory (7th ed.) Ch.7"
    doi: "10.1007/978-3-662-52919-5"
    flow_type: INTERNAL
    geometry_type: SIMPLE_GRID
    compressibility: INCOMPRESSIBLE
    steady_state: STEADY
    solver: simpleFoam
    # Re=50000, plate_length=1.0 → Re_x=25000 at x=0.5, Re_x=50000 at x=1.0. Both are
    # deep in the laminar regime (transition on smooth plate ~Re_x=3e5–5e5). k-ω SST
    # with Spalding-fit gold 0.0076/0.0061 was physically incorrect. Flipped to
    # Blasius Cf=0.664/√Re_x which is the canonical laminar similarity solution.
    # Gate Q-new Case 4 · Path A approved by Kogami 2026-04-20. (DEC-V61-006)
    turbulence_model: laminar
    parameters:
      Re: 50000
      plate_length: 1.0
    gold_standard:
      quantity: cf_skin_friction
      description: "平板摩擦系数 Cf = 0.664/√Re_x (Blasius laminar similarity); x=0.5→Re_x=25000, x=1.0→Re_x=50000"
      reference_values:
        - {x: 0.5, Cf: 0.00420}   # Blasius: 0.664 / √25000 = 0.00420
        - {x: 1.0, Cf: 0.00297}   # Blasius: 0.664 / √50000 = 0.00297
      tolerance: 0.10  # 10% relative — Blasius is exact analytically; 10% covers mesh + numerical dissipation

  # RENAMED from `fully_developed_pipe` per Gate Q-2 Path A (DEC-V61-011, 2026-04-20).
  # Original case was labeled "pipe" but adapter's SIMPLE_GRID generator emits a
  # rectangular duct, not a circular pipe. Reference correlation updated from
  # Blasius/Moody pipe to Jones 1976 smooth square-duct. Numerical value at Re=50000
  # happens to be within 2% of the old Colebrook pipe value, so the comparator
  # verdict is unchanged — but the physics label is now honest.
  # Legacy aliases `fully_developed_pipe` / `fully_developed_turbulent_pipe_flow`
  # preserved for historical correction-log references via CANONICAL_ALIASES.
  - id: duct_flow
    name: "Fully Developed Turbulent Square-Duct Flow"
    reference: "Jones 1976 / Jones & Launder 1973"
    doi: "10.1016/0017-9310(76)90033-4"
    flow_type: INTERNAL
    geometry_type: SIMPLE_GRID
    compressibility: INCOMPRESSIBLE
    steady_state: STEADY
    solver: simpleFoam
    turbulence_model: k-epsilon
    parameters:
      Re: 50000
      hydraulic_diameter: 0.1  # D_h for square duct = side length
      aspect_ratio: 1.0         # square cross-section
    gold_standard:
      quantity: friction_factor
      description: "Darcy friction factor f for smooth square duct (AR=1); Jones 1976 correlation f_duct ≈ 0.88·f_pipe(Re); cross-validated vs. Colebrook pipe + Nikuradse duct data"
      reference_values:
        - {Re: 50000, f: 0.0185}   # Jones 1976 smooth square duct at Re=50000 (within 2% of Colebrook pipe 0.0181)
      tolerance: 0.10  # 10% relative — Jones correlation uncertainty wider than Moody pipe

  - id: differential_heated_cavity
    name: "Differential Heated Cavity (Natural Convection, Ra=10^6 benchmark)"
    reference: "de Vahl Davis 1983 / Dhir 2001"
    doi: "10.1002/fld.1650030305"
    flow_type: NATURAL_CONVECTION
    geometry_type: NATURAL_CONVECTION_CAVITY
    compressibility: INCOMPRESSIBLE
    steady_state: STEADY
    solver: buoyantFoam
    # Previous state: Ra=1e10 with Nu=30 gold (turbulent SST). Audit + Q-1 established
    # Ra=1e10 requires ~1000 wall-normal cells for BL resolution (infeasible at current
    # adapter 80-cell wall-normal), AND Nu=30 was inconsistent with literature (100-325).
    # Gate Q-new Case 6 · Path P-2 approved by Kogami 2026-04-20: downgrade Ra to 1e6,
    # the canonical de Vahl Davis 1983 benchmark where Nu_avg=8.800 is both well-
    # documented (within 0.2% across multiple DNS studies) AND resolvable on 40-80
    # wall-normal cells. This closes Q-1 with P-2. (DEC-V61-006)
    turbulence_model: laminar  # Ra=1e6 is fully-laminar steady-convective regime
    parameters:
      Ra: 1000000  # Ra = 1e6 (de Vahl Davis 1983 canonical benchmark)
      aspect_ratio: 1.0
      Pr: 0.71
    gold_standard:
      quantity: nusselt_number
      description: "方腔热壁平均努塞尔数 Nu_avg (de Vahl Davis 1983 benchmark, Ra=1e6, Pr=0.71, AR=1.0)"
      reference_values:
        - {Ra: 1e6, Nu: 8.8}   # de Vahl Davis 1983: Nu_avg = 8.800
      tolerance: 0.10  # 10% — benchmark is highly resolved; adapter mesh resolution is the dominant uncertainty

  - id: plane_channel_flow
    name: "Fully Developed Plane Channel Flow (DNS)"
    reference: "Kim et al. 1987 / Moser et al. 1999"
    doi: "10.1017/S0022112087000892"
    flow_type: INTERNAL
    geometry_type: BODY_IN_CHANNEL
    compressibility: INCOMPRESSIBLE
    steady_state: STEADY
    solver: icoFoam  # DNS — laminar (no turbulence model, resolved scales)
    turbulence_model: laminar
    parameters:
      Re_tau: 180  # 基于摩擦速度的雷诺数
      half_channel_height: 1.0
    gold_standard:
      quantity: u_mean_profile
      description: "无量纲速度分布 u+ vs y+ (Moser 1999 Re_τ=180 DNS; log-law κ=0.41 B=5.2)"
      reference_values:
        - {y_plus: 0.0, u_plus: 0.0}
        - {y_plus: 5.0, u_plus: 5.4}
        # Gate Q-new Case 8 · Path A approved by Kogami 2026-04-20:
        # log-law (1/0.41)·ln(30)+5.2 = 13.49 ≈ 13.5. Previous 14.5 off by ~7%.
        # (DEC-V61-006)
        - {y_plus: 30.0, u_plus: 13.5}
        # NOTE: y_plus=100 value 22.8 also looks anomalous (log-law gives ~16.4,
        # Moser Re_τ=180 centerline u+≈18.3). Out of audit §5.2 scope; noted for
        # follow-up audit pass.
        - {y_plus: 100.0, u_plus: 22.8}
      tolerance: 0.05  # 5% 相对误差 (Moser DNS numerical uncertainty)

  - id: impinging_jet
    name: "Axisymmetric Impinging Jet (Re=10000)"
    reference: "Cooper et al. 1984 / Behnad et al. 2013"
    doi: "10.1016/j.ijheatfluidflow.2013.03.003"
    flow_type: EXTERNAL
    geometry_type: IMPINGING_JET
    compressibility: INCOMPRESSIBLE
    steady_state: STEADY
    solver: simpleFoam
    turbulence_model: k-omega SST
    parameters:
      Re: 10000
      nozzle_diameter: 0.05
      h_over_d: 2.0  # 喷口到板面距离 / 直径
    # Gate Q-new Case 9 · HOLD per Kogami 2026-04-20: audit flagged Nu@r/d=0 = 25 vs
    # Behnad 2013 ~110-130, but 4-5× discrepancy is too large to edit without reading
    # Behnad et al. 2013 (DOI 10.1016/j.ijheatfluidflow.2013.03.003) directly and
    # confirming (Re=10000, h/d=2) was the configuration cited. Possible mis-match:
    # confined-jet vs free-jet, different h/d, different Re. Literature re-source
    # pending. Values below are provisional; may change in future DEC.
    gold_standard:
      quantity: nusselt_number
      description: "冲击面局部努塞尔数分布 (PROVISIONAL — Gate Q-new Case 9 hold)"
      reference_values:
        - {r_over_d: 0.0, Nu: 25.0}
        - {r_over_d: 1.0, Nu: 12.0}
      tolerance: 0.15  # 15% 相对误差

  - id: naca0012_airfoil
    name: "NACA 0012 Airfoil External Flow"
    reference: "Thomas 1979 / Lada & Gostling 2007"
    doi: "10.1017/S0001924000001169"
    flow_type: EXTERNAL
    geometry_type: AIRFOIL
    compressibility: INCOMPRESSIBLE
    steady_state: STEADY
    solver: simpleFoam
    turbulence_model: k-omega SST
    parameters:
      Re: 3000000
      angle_of_attack: 0.0
      chord_length: 1.0
    gold_standard:
      quantity: pressure_coefficient
      description: "翼型表面压力系数分布 Cp"
      reference_values:
        - {x_over_c: 0.0, Cp: 1.0}
        - {x_over_c: 0.3, Cp: -0.5}
        - {x_over_c: 1.0, Cp: 0.2}
      tolerance: 0.20  # 20% 相对误差

  - id: rayleigh_benard_convection
    name: "Rayleigh-Bénard Convection (Ra=10^6)"
    reference: "Chaivat et al. 2006"
    doi: "10.1016/j.ijheatmasstransfer.2005.07.039"
    flow_type: NATURAL_CONVECTION
    geometry_type: NATURAL_CONVECTION_CAVITY
    compressibility: INCOMPRESSIBLE
    steady_state: STEADY
    solver: buoyantFoam
    # Ra=1e6 is steady-convective (fully turbulent onset ~Ra=1.5e8 for moderate Pr).
    # k-omega SST over-dissipates at this Ra → under-predicts Nu. Chaivat correlation
    # Nu=0.229*Ra^0.269 assumes laminar steady regime. A-class metadata correction per
    # docs/whitelist_audit.md §3. reference_values untouched. (DEC-V61-005)
    turbulence_model: laminar
    parameters:
      Ra: 1000000
      Pr: 0.71
      aspect_ratio: 2.0
    # Gate Q-new Case 10 · HOLD per Kogami 2026-04-20: initial audit claimed Chaivat
    # correlation gives 7.2 at Ra=1e6, but recompute shows 0.229·(1e6)^0.269 = 9.4,
    # putting current 10.5 only 11.5% off (within 15% tolerance). Small discrepancy,
    # possibly using a different Chaivat correlation variant than the description
    # states. Chaivat 2006 (DOI 10.1016/j.ijheatmasstransfer.2005.07.039) paper
    # re-read pending before any edit. Values below retained.
    gold_standard:
      quantity: nusselt_number
      description: "水平层自然对流 Nu (PROVISIONAL — Gate Q-new Case 10 hold; see comment)"
      reference_values:
        - {Ra: 1e6, Nu: 10.5}
      tolerance: 0.15  # 15% 相对误差

exec
/bin/zsh -lc "sed -n '60,120p' src/models.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:

# ---------------------------------------------------------------------------
# Core dataclasses
# ---------------------------------------------------------------------------

@dataclass
class TaskSpec:
    """从 Notion 读取的任务规格"""
    name: str
    geometry_type: GeometryType
    flow_type: FlowType
    steady_state: SteadyState
    compressibility: Compressibility
    Re: Optional[float] = None
    Ra: Optional[float] = None
    Re_tau: Optional[float] = None
    Ma: Optional[float] = None
    boundary_conditions: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    notion_task_id: Optional[str] = None
    # Phase 7a — optional per-run metadata bag. Currently carries the
    # driver-authored `phase7a_timestamp` (and `phase7a_case_id`) so
    # FoamAgentExecutor._capture_field_artifacts can stage OpenFOAM field
    # artifacts into reports/phase5_fields/{case_id}/{timestamp}/ before the
    # finally-block tears down the case dir. Default-None keeps the
    # dataclass backward-compatible for all 79/79 existing tests.
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ExecutionResult:
    """CFD 执行结果"""
    success: bool
    is_mock: bool
    residuals: Dict[str, float] = field(default_factory=dict)
    key_quantities: Dict[str, Any] = field(default_factory=dict)
    execution_time_s: float = 0.0
    raw_output_path: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class DeviationDetail:
    """单个物理量的偏差记录"""
    quantity: str
    expected: Any
    actual: Any
    relative_error: Optional[float] = None
    tolerance: Optional[float] = None


@dataclass
class ComparisonResult:
    """结果 vs Gold Standard 对比"""
    passed: bool
    deviations: List[DeviationDetail] = field(default_factory=list)
    summary: str = ""
    gold_standard_id: Optional[str] = None


@dataclass

codex
I’ve got enough context to switch from code reading to claim checking. Next step is lightweight verification: targeted search around the line numbers I expect to cite, and one attempt to run the dedicated gate test file without writing into the repo.
exec
/bin/zsh -lc "nl -ba src/comparator_gates.py | sed -n '245,330p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
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

exec
/bin/zsh -lc "nl -ba scripts/phase5_audit_run.py | sed -n '290,430p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
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

exec
/bin/zsh -lc "nl -ba ui/backend/tests/test_comparator_gates_g3_g4_g5.py | sed -n '1,320p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
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
    15	
    16	import pytest
    17	from fastapi.testclient import TestClient
    18	
    19	from src import comparator_gates as cg
    20	from ui.backend.main import app
    21	
    22	
    23	# ---------------------------------------------------------------------------
    24	# Shared synthetic log fixtures
    25	# ---------------------------------------------------------------------------
    26	
    27	_CLEAN_LDC_LOG = """\
    28	Time = 500
    29	
    30	DICPCG:  Solving for p, Initial residual = 1e-08, Final residual = 1e-09, No Iterations 2
    31	time step continuity errors : sum local = 4.5e-08, global = -1.2e-09, cumulative = 3.1e-08
    32	ExecutionTime = 12.3 s  ClockTime = 14 s
    33	
    34	End
    35	"""
    36	
    37	_BFS_BLOWUP_TAIL = """\
    38	Time = 50
    39	
    40	smoothSolver:  Solving for Ux, Initial residual = 0.9, Final residual = 0.6, No Iterations 12
    41	smoothSolver:  Solving for Uy, Initial residual = 0.8, Final residual = 0.5, No Iterations 12
    42	GAMG:  Solving for p, Initial residual = 0.99, Final residual = 0.9, No Iterations 25
    43	time step continuity errors : sum local = 5.24523e+18, global = -1328.63, cumulative = -1434.64
    44	smoothSolver:  Solving for epsilon, Initial residual = 0.8, Final residual = 0.4, No Iterations 3
    45	bounding epsilon, min: 7.38706e-17 max: 1.03929e+30 average: 1.37234e+27
    46	smoothSolver:  Solving for k, Initial residual = 0.7, Final residual = 0.4, No Iterations 4
    47	bounding k, min: -6.41351e+30 max: 2.32895e+31 average: 1.39855e+29
    48	ExecutionTime = 0.6 s  ClockTime = 0 s
    49	"""
    50	
    51	
    52	def _write_log(tmp_path: Path, content: str) -> Path:
    53	    p = tmp_path / "log.simpleFoam"
    54	    p.write_text(content, encoding="utf-8")
    55	    return p
    56	
    57	
    58	# ---------------------------------------------------------------------------
    59	# Log parsing
    60	# ---------------------------------------------------------------------------
    61	
    62	def test_parse_solver_log_extracts_continuity_and_bounding(tmp_path: Path) -> None:
    63	    log = _write_log(tmp_path, _BFS_BLOWUP_TAIL)
    64	    stats = cg.parse_solver_log(log)
    65	    assert stats.final_continuity_sum_local == pytest.approx(5.24523e18)
    66	    assert stats.final_continuity_cumulative == pytest.approx(-1434.64)
    67	    assert "k" in stats.bounding_last
    68	    assert stats.bounding_last["k"]["min"] == pytest.approx(-6.41351e30)
    69	    assert stats.bounding_last["epsilon"]["max"] == pytest.approx(1.03929e30)
    70	    assert stats.fatal_detected is False
    71	
    72	
    73	def test_parse_solver_log_detects_foam_fatal(tmp_path: Path) -> None:
    74	    content = _CLEAN_LDC_LOG + "\nFOAM FATAL IO ERROR: missing dictionary key\n"
    75	    log = _write_log(tmp_path, content)
    76	    stats = cg.parse_solver_log(log)
    77	    assert stats.fatal_detected is True
    78	
    79	
    80	# ---------------------------------------------------------------------------
    81	# G5 — continuity divergence
    82	# ---------------------------------------------------------------------------
    83	
    84	def test_g5_fails_on_sum_local_overflow(tmp_path: Path) -> None:
    85	    log = _write_log(tmp_path, _BFS_BLOWUP_TAIL)
    86	    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
    87	    g5 = [v for v in violations if v.gate_id == "G5"]
    88	    assert len(g5) == 1
    89	    assert g5[0].concern_type == "CONTINUITY_DIVERGED"
    90	    assert g5[0].evidence["sum_local"] == pytest.approx(5.24523e18)
    91	
    92	
    93	def test_g5_fails_on_cumulative_only(tmp_path: Path) -> None:
    94	    # sum_local within threshold, cumulative huge — second branch.
    95	    content = (
    96	        "time step continuity errors : "
    97	        "sum local = 1e-04, global = 0.001, cumulative = 2.5\n"
    98	    )
    99	    log = _write_log(tmp_path, content)
   100	    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
   101	    g5 = [v for v in violations if v.gate_id == "G5"]
   102	    assert len(g5) == 1
   103	    assert g5[0].evidence["cumulative"] == pytest.approx(2.5)
   104	
   105	
   106	def test_g5_passes_on_clean_ldc_log(tmp_path: Path) -> None:
   107	    log = _write_log(tmp_path, _CLEAN_LDC_LOG)
   108	    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
   109	    g5 = [v for v in violations if v.gate_id == "G5"]
   110	    assert g5 == []
   111	
   112	
   113	# ---------------------------------------------------------------------------
   114	# G4 — turbulence negativity
   115	# ---------------------------------------------------------------------------
   116	
   117	def test_g4_fails_on_negative_k_at_last_iter(tmp_path: Path) -> None:
   118	    log = _write_log(tmp_path, _BFS_BLOWUP_TAIL)
   119	    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
   120	    g4 = [v for v in violations if v.gate_id == "G4"]
   121	    # BFS log shows k min=-6.4e30 AND epsilon max=1.03e30 — both fire G4
   122	    # (negative branch for k, overflow branch for epsilon).
   123	    concern_fields = {v.evidence["field"] for v in g4}
   124	    assert "k" in concern_fields
   125	    assert any(v.evidence.get("min", 1.0) < 0 for v in g4)
   126	
   127	
   128	def test_g4_fails_on_epsilon_overflow_without_negative(tmp_path: Path) -> None:
   129	    content = (
   130	        "bounding epsilon, min: 1e-5 max: 1e+30 average: 1e+26\n"
   131	        "bounding k, min: 1e-6 max: 0.5 average: 0.01\n"
   132	    )
   133	    log = _write_log(tmp_path, content)
   134	    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
   135	    g4 = [v for v in violations if v.gate_id == "G4"]
   136	    assert len(g4) == 1
   137	    assert g4[0].evidence["field"] == "epsilon"
   138	    assert g4[0].evidence["max"] == pytest.approx(1e30)
   139	
   140	
   141	def test_g4_passes_on_clean_ldc_log(tmp_path: Path) -> None:
   142	    # LDC is laminar — no bounding lines emitted. G4 should return no violations.
   143	    log = _write_log(tmp_path, _CLEAN_LDC_LOG)
   144	    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
   145	    g4 = [v for v in violations if v.gate_id == "G4"]
   146	    assert g4 == []
   147	
   148	
   149	# ---------------------------------------------------------------------------
   150	# G3 — velocity overflow (log-proxy branch; VTK branch gated by pyvista)
   151	# ---------------------------------------------------------------------------
   152	
   153	def test_g3_proxy_fails_on_epsilon_overflow(tmp_path: Path) -> None:
   154	    log = _write_log(tmp_path, _BFS_BLOWUP_TAIL)
   155	    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
   156	    g3 = [v for v in violations if v.gate_id == "G3"]
   157	    assert len(g3) == 1
   158	    assert g3[0].concern_type == "VELOCITY_OVERFLOW"
   159	    # BFS epsilon max=1.03e30 → inferred u ~ (1e30)^(1/3) = 1e10
   160	    assert g3[0].evidence["epsilon_max"] == pytest.approx(1.03929e30)
   161	
   162	
   163	def test_g3_passes_on_clean_ldc_log(tmp_path: Path) -> None:
   164	    log = _write_log(tmp_path, _CLEAN_LDC_LOG)
   165	    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
   166	    g3 = [v for v in violations if v.gate_id == "G3"]
   167	    assert g3 == []
   168	
   169	
   170	# ---------------------------------------------------------------------------
   171	# NaN/Inf safety (Codex DEC-036b round-1 nit)
   172	# ---------------------------------------------------------------------------
   173	
   174	def test_g5_fires_on_nan_sum_local(tmp_path: Path) -> None:
   175	    """OpenFOAM overflowed → prints `nan` for continuity; gate must fire."""
   176	    content = (
   177	        "time step continuity errors : "
   178	        "sum local = nan, global = 0.01, cumulative = -0.5\n"
   179	    )
   180	    log = _write_log(tmp_path, content)
   181	    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
   182	    g5 = [v for v in violations if v.gate_id == "G5"]
   183	    assert len(g5) == 1, f"expected G5 on nan sum_local, got {violations}"
   184	
   185	
   186	def test_g4_fires_on_inf_k_max(tmp_path: Path) -> None:
   187	    """+inf in bounding line must fire G4 (not silently skip)."""
   188	    content = "bounding k, min: 1e-5 max: inf average: 1e+20\n"
   189	    log = _write_log(tmp_path, content)
   190	    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
   191	    g4 = [v for v in violations if v.gate_id == "G4"]
   192	    assert len(g4) == 1
   193	    assert g4[0].evidence["field"] == "k"
   194	
   195	
   196	# ---------------------------------------------------------------------------
   197	# BFS integration — all three gates fire on the real BFS audit log
   198	# ---------------------------------------------------------------------------
   199	
   200	_REAL_BFS_LOG = Path(
   201	    "/Users/Zhuanz/Desktop/cfd-harness-unified/reports/phase5_fields/"
   202	    "backward_facing_step/20260421T125637Z/log.simpleFoam"
   203	)
   204	
   205	
   206	@pytest.mark.skipif(not _REAL_BFS_LOG.is_file(), reason="BFS phase7a log absent")
   207	def test_gates_fire_on_real_bfs_audit_log() -> None:
   208	    violations = cg.check_all_gates(log_path=_REAL_BFS_LOG, vtk_dir=None, U_ref=1.0)
   209	    gate_ids = {v.gate_id for v in violations}
   210	    # BFS must trigger G5 (continuity) + G4 (turbulence) + G3 (velocity proxy).
   211	    assert {"G3", "G4", "G5"}.issubset(gate_ids)
   212	
   213	
   214	# ---------------------------------------------------------------------------
   215	# Integration with validation_report verdict engine
   216	# ---------------------------------------------------------------------------
   217	
   218	@pytest.fixture(scope="module")
   219	def client() -> TestClient:
   220	    return TestClient(app)
   221	
   222	
   223	def test_validation_report_hard_fails_on_velocity_overflow_concern() -> None:
   224	    """Fixture with VELOCITY_OVERFLOW concern must hard-FAIL the verdict."""
   225	    from ui.backend.schemas.validation import (
   226	        AuditConcern,
   227	        GoldStandardReference,
   228	        MeasuredValue,
   229	    )
   230	    from ui.backend.services.validation_report import _derive_contract_status
   231	
   232	    gs = GoldStandardReference(
   233	        quantity="friction_factor",
   234	        ref_value=0.0185,
   235	        unit="dimensionless",
   236	        tolerance_pct=0.10,
   237	        citation="Colebrook 1939",
   238	    )
   239	    # Value IS inside the tolerance band — would normally PASS.
   240	    m = MeasuredValue(
   241	        value=0.0185,
   242	        source="fixture",
   243	        quantity="friction_factor",
   244	        extraction_source="comparator_deviation",
   245	    )
   246	    concerns = [
   247	        AuditConcern(
   248	            concern_type="VELOCITY_OVERFLOW",
   249	            summary="|U|_max=1e10",
   250	        )
   251	    ]
   252	    status, deviation, within, _, _ = _derive_contract_status(
   253	        gs, m, preconditions=[], audit_concerns=concerns
   254	    )
   255	    # DEC-V61-036b: VELOCITY_OVERFLOW overrides a "within band" comparator PASS.
   256	    # Codex round-1 nit applied: within_tolerance is nulled when hard-fail
   257	    # concern fires, so the UI doesn't render "Within band: yes" under FAIL.
   258	    assert status == "FAIL"
   259	    assert deviation == pytest.approx(0.0, abs=1e-9)
   260	    assert within is None  # nulled per Codex nit (value IS inside band, but trust is null)
   261	
   262	
   263	def test_validation_report_hard_fails_on_continuity_diverged() -> None:
   264	    from ui.backend.schemas.validation import (
   265	        AuditConcern,
   266	        GoldStandardReference,
   267	        MeasuredValue,
   268	    )
   269	    from ui.backend.services.validation_report import _derive_contract_status
   270	
   271	    gs = GoldStandardReference(
   272	        quantity="reattachment_length",
   273	        ref_value=6.26,
   274	        unit="Xr/H",
   275	        tolerance_pct=0.10,
   276	        citation="Driver 1985",
   277	    )
   278	    m = MeasuredValue(value=6.28, source="fixture", quantity="reattachment_length")
   279	    concerns = [AuditConcern(concern_type="CONTINUITY_DIVERGED", summary="cum=-1434")]
   280	    status, _, _, _, _ = _derive_contract_status(gs, m, [], concerns)
   281	    assert status == "FAIL"
   282	
   283	
   284	def test_validation_report_preserves_pass_without_gate_concerns() -> None:
   285	    """No gate concerns + value within band → PASS still works."""
   286	    from ui.backend.schemas.validation import (
   287	        GoldStandardReference,
   288	        MeasuredValue,
   289	    )
   290	    from ui.backend.services.validation_report import _derive_contract_status
   291	
   292	    gs = GoldStandardReference(
   293	        quantity="u_centerline",
   294	        ref_value=-0.2058,
   295	        unit="dimensionless",
   296	        tolerance_pct=0.05,
   297	        citation="Ghia 1982",
   298	    )
   299	    m = MeasuredValue(value=-0.2050, source="fixture", quantity="u_centerline")
   300	    status, _, within, _, _ = _derive_contract_status(gs, m, [], [])
   301	    assert status == "PASS"
   302	    assert within is True

exec
/bin/zsh -lc 'PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest ui/backend/tests/test_comparator_gates_g3_g4_g5.py -q -p no:cacheprovider' in /Users/Zhuanz/Desktop/cfd-harness-unified
2026-04-22T10:45:35.418617Z ERROR codex_core::tools::router: error=exec_command failed for `/bin/zsh -lc 'PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest ui/backend/tests/test_comparator_gates_g3_g4_g5.py -q -p no:cacheprovider'`: SandboxDenied { message: "python3: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead\npython3: error: couldn't create cache file '/tmp/xcrun_db-51m7VwyM' (errno=Operation not permitted)\npython3: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead\npython3: error: couldn't create cache file '/tmp/xcrun_db-Nhv1IeyD' (errno=Operation not permitted)\n/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/config/__init__.py:331: PluggyTeardownRaisedWarning: A plugin raised an exception during an old-style hookwrapper teardown.\nPlugin: helpconfig, Hook: pytest_cmdline_parse\nFileNotFoundError: [Errno 2] No usable temporary directory found in ['/var/folders/q4/859yhpgn6x3fx6kv4mj5gmv40000gp/T/', '/tmp', '/var/tmp', '/usr/tmp', '/Users/Zhuanz/Desktop/cfd-harness-unified']\nFor more information see https://pluggy.readthedocs.io/en/stable/api_reference.html#pluggy.PluggyTeardownRaisedWarning\n  config = pluginmanager.hook.pytest_cmdline_parse(\nTraceback (most recent call last):\n  File \"/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/runpy.py\", line 197, in _run_module_as_main\n    return _run_code(code, main_globals, None,\n  File \"/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/runpy.py\", line 87, in _run_code\n    exec(code, run_globals)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pytest/__main__.py\", line 5, in <module>\n    raise SystemExit(pytest.console_main())\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/config/__init__.py\", line 192, in console_main\n    code = main()\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/config/__init__.py\", line 150, in main\n    config = _prepareconfig(args, plugins)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/config/__init__.py\", line 331, in _prepareconfig\n    config = pluginmanager.hook.pytest_cmdline_parse(\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_hooks.py\", line 512, in __call__\n    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_manager.py\", line 120, in _hookexec\n    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py\", line 167, in _multicall\n    raise exception\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py\", line 139, in _multicall\n    teardown.throw(exception)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py\", line 43, in run_old_style_hookwrapper\n    teardown.send(result)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/helpconfig.py\", line 104, in pytest_cmdline_parse\n    config: Config = outcome.get_result()\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_result.py\", line 103, in get_result\n    raise exc.with_traceback(tb)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py\", line 38, in run_old_style_hookwrapper\n    res = yield\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py\", line 121, in _multicall\n    res = hook_impl.function(*args)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/config/__init__.py\", line 1075, in pytest_cmdline_parse\n    self.parse(args)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/config/__init__.py\", line 1425, in parse\n    self._preparse(args, addopts=addopts)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/config/__init__.py\", line 1327, in _preparse\n    self.hook.pytest_load_initial_conftests(\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_hooks.py\", line 512, in __call__\n    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_manager.py\", line 120, in _hookexec\n    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py\", line 167, in _multicall\n    raise exception\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py\", line 139, in _multicall\n    teardown.throw(exception)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py\", line 53, in run_old_style_hookwrapper\n    return result.get_result()\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_result.py\", line 103, in get_result\n    raise exc.with_traceback(tb)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py\", line 38, in run_old_style_hookwrapper\n    res = yield\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py\", line 107, in _multicall\n    next(function_gen)  # first yield\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py\", line 34, in run_old_style_hookwrapper\n    next(teardown)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/capture.py\", line 149, in pytest_load_initial_conftests\n    capman.start_global_capturing()\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/capture.py\", line 750, in start_global_capturing\n    self._global_capturing = _get_multicapture(self._method)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/capture.py\", line 692, in _get_multicapture\n    return MultiCapture(in_=FDCapture(0), out=FDCapture(1), err=FDCapture(2))\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/capture.py\", line 466, in __init__\n    TemporaryFile(buffering=0),\n  File \"/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/tempfile.py\", line 581, in TemporaryFile\n    prefix, suffix, dir, output_type = _sanitize_params(prefix, suffix, dir)\n  File \"/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/tempfile.py\", line 118, in _sanitize_params\n    dir = gettempdir()\n  File \"/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/tempfile.py\", line 287, in gettempdir\n    tempdir = _get_default_tempdir()\n  File \"/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/tempfile.py\", line 219, in _get_default_tempdir\n    raise FileNotFoundError(_errno.ENOENT,\nFileNotFoundError: [Errno 2] No usable temporary directory found in ['/var/folders/q4/859yhpgn6x3fx6kv4mj5gmv40000gp/T/', '/tmp', '/var/tmp', '/usr/tmp', '/Users/Zhuanz/Desktop/cfd-harness-unified']\n", output: ExecToolCallOutput { exit_code: 1, stdout: StreamOutput { text: "", truncated_after_lines: None }, stderr: StreamOutput { text: "python3: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead\npython3: error: couldn't create cache file '/tmp/xcrun_db-51m7VwyM' (errno=Operation not permitted)\npython3: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead\npython3: error: couldn't create cache file '/tmp/xcrun_db-Nhv1IeyD' (errno=Operation not permitted)\n/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/config/__init__.py:331: PluggyTeardownRaisedWarning: A plugin raised an exception during an old-style hookwrapper teardown.\nPlugin: helpconfig, Hook: pytest_cmdline_parse\nFileNotFoundError: [Errno 2] No usable temporary directory found in ['/var/folders/q4/859yhpgn6x3fx6kv4mj5gmv40000gp/T/', '/tmp', '/var/tmp', '/usr/tmp', '/Users/Zhuanz/Desktop/cfd-harness-unified']\nFor more information see https://pluggy.readthedocs.io/en/stable/api_reference.html#pluggy.PluggyTeardownRaisedWarning\n  config = pluginmanager.hook.pytest_cmdline_parse(\nTraceback (most recent call last):\n  File \"/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/runpy.py\", line 197, in _run_module_as_main\n    return _run_code(code, main_globals, None,\n  File \"/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/runpy.py\", line 87, in _run_code\n    exec(code, run_globals)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pytest/__main__.py\", line 5, in <module>\n    raise SystemExit(pytest.console_main())\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/config/__init__.py\", line 192, in console_main\n    code = main()\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/config/__init__.py\", line 150, in main\n    config = _prepareconfig(args, plugins)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/config/__init__.py\", line 331, in _prepareconfig\n    config = pluginmanager.hook.pytest_cmdline_parse(\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_hooks.py\", line 512, in __call__\n    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_manager.py\", line 120, in _hookexec\n    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py\", line 167, in _multicall\n    raise exception\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py\", line 139, in _multicall\n    teardown.throw(exception)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py\", line 43, in run_old_style_hookwrapper\n    teardown.send(result)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/helpconfig.py\", line 104, in pytest_cmdline_parse\n    config: Config = outcome.get_result()\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_result.py\", line 103, in get_result\n    raise exc.with_traceback(tb)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py\", line 38, in run_old_style_hookwrapper\n    res = yield\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py\", line 121, in _multicall\n    res = hook_impl.function(*args)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/config/__init__.py\", line 1075, in pytest_cmdline_parse\n    self.parse(args)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/config/__init__.py\", line 1425, in parse\n    self._preparse(args, addopts=addopts)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/config/__init__.py\", line 1327, in _preparse\n    self.hook.pytest_load_initial_conftests(\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_hooks.py\", line 512, in __call__\n    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_manager.py\", line 120, in _hookexec\n    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py\", line 167, in _multicall\n    raise exception\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py\", line 139, in _multicall\n    teardown.throw(exception)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py\", line 53, in run_old_style_hookwrapper\n    return result.get_result()\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_result.py\", line 103, in get_result\n    raise exc.with_traceback(tb)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py\", line 38, in run_old_style_hookwrapper\n    res = yield\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py\", line 107, in _multicall\n    next(function_gen)  # first yield\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py\", line 34, in run_old_style_hookwrapper\n    next(teardown)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/capture.py\", line 149, in pytest_load_initial_conftests\n    capman.start_global_capturing()\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/capture.py\", line 750, in start_global_capturing\n    self._global_capturing = _get_multicapture(self._method)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/capture.py\", line 692, in _get_multicapture\n    return MultiCapture(in_=FDCapture(0), out=FDCapture(1), err=FDCapture(2))\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/capture.py\", line 466, in __init__\n    TemporaryFile(buffering=0),\n  File \"/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/tempfile.py\", line 581, in TemporaryFile\n    prefix, suffix, dir, output_type = _sanitize_params(prefix, suffix, dir)\n  File \"/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/tempfile.py\", line 118, in _sanitize_params\n    dir = gettempdir()\n  File \"/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/tempfile.py\", line 287, in gettempdir\n    tempdir = _get_default_tempdir()\n  File \"/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/tempfile.py\", line 219, in _get_default_tempdir\n    raise FileNotFoundError(_errno.ENOENT,\nFileNotFoundError: [Errno 2] No usable temporary directory found in ['/var/folders/q4/859yhpgn6x3fx6kv4mj5gmv40000gp/T/', '/tmp', '/var/tmp', '/usr/tmp', '/Users/Zhuanz/Desktop/cfd-harness-unified']\n", truncated_after_lines: None }, aggregated_output: StreamOutput { text: "python3: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead\npython3: error: couldn't create cache file '/tmp/xcrun_db-51m7VwyM' (errno=Operation not permitted)\npython3: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead\npython3: error: couldn't create cache file '/tmp/xcrun_db-Nhv1IeyD' (errno=Operation not permitted)\n/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/config/__init__.py:331: PluggyTeardownRaisedWarning: A plugin raised an exception during an old-style hookwrapper teardown.\nPlugin: helpconfig, Hook: pytest_cmdline_parse\nFileNotFoundError: [Errno 2] No usable temporary directory found in ['/var/folders/q4/859yhpgn6x3fx6kv4mj5gmv40000gp/T/', '/tmp', '/var/tmp', '/usr/tmp', '/Users/Zhuanz/Desktop/cfd-harness-unified']\nFor more information see https://pluggy.readthedocs.io/en/stable/api_reference.html#pluggy.PluggyTeardownRaisedWarning\n  config = pluginmanager.hook.pytest_cmdline_parse(\nTraceback (most recent call last):\n  File \"/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/runpy.py\", line 197, in _run_module_as_main\n    return _run_code(code, main_globals, None,\n  File \"/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/runpy.py\", line 87, in _run_code\n    exec(code, run_globals)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pytest/__main__.py\", line 5, in <module>\n    raise SystemExit(pytest.console_main())\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/config/__init__.py\", line 192, in console_main\n    code = main()\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/config/__init__.py\", line 150, in main\n    config = _prepareconfig(args, plugins)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/config/__init__.py\", line 331, in _prepareconfig\n    config = pluginmanager.hook.pytest_cmdline_parse(\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_hooks.py\", line 512, in __call__\n    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_manager.py\", line 120, in _hookexec\n    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py\", line 167, in _multicall\n    raise exception\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py\", line 139, in _multicall\n    teardown.throw(exception)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py\", line 43, in run_old_style_hookwrapper\n    teardown.send(result)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/helpconfig.py\", line 104, in pytest_cmdline_parse\n    config: Config = outcome.get_result()\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_result.py\", line 103, in get_result\n    raise exc.with_traceback(tb)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py\", line 38, in run_old_style_hookwrapper\n    res = yield\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py\", line 121, in _multicall\n    res = hook_impl.function(*args)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/config/__init__.py\", line 1075, in pytest_cmdline_parse\n    self.parse(args)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/config/__init__.py\", line 1425, in parse\n    self._preparse(args, addopts=addopts)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/config/__init__.py\", line 1327, in _preparse\n    self.hook.pytest_load_initial_conftests(\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_hooks.py\", line 512, in __call__\n    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_manager.py\", line 120, in _hookexec\n    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py\", line 167, in _multicall\n    raise exception\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py\", line 139, in _multicall\n    teardown.throw(exception)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py\", line 53, in run_old_style_hookwrapper\n    return result.get_result()\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_result.py\", line 103, in get_result\n    raise exc.with_traceback(tb)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py\", line 38, in run_old_style_hookwrapper\n    res = yield\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py\", line 107, in _multicall\n    next(function_gen)  # first yield\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py\", line 34, in run_old_style_hookwrapper\n    next(teardown)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/capture.py\", line 149, in pytest_load_initial_conftests\n    capman.start_global_capturing()\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/capture.py\", line 750, in start_global_capturing\n    self._global_capturing = _get_multicapture(self._method)\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/capture.py\", line 692, in _get_multicapture\n    return MultiCapture(in_=FDCapture(0), out=FDCapture(1), err=FDCapture(2))\n  File \"/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/capture.py\", line 466, in __init__\n    TemporaryFile(buffering=0),\n  File \"/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/tempfile.py\", line 581, in TemporaryFile\n    prefix, suffix, dir, output_type = _sanitize_params(prefix, suffix, dir)\n  File \"/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/tempfile.py\", line 118, in _sanitize_params\n    dir = gettempdir()\n  File \"/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/tempfile.py\", line 287, in gettempdir\n    tempdir = _get_default_tempdir()\n  File \"/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/tempfile.py\", line 219, in _get_default_tempdir\n    raise FileNotFoundError(_errno.ENOENT,\nFileNotFoundError: [Errno 2] No usable temporary directory found in ['/var/folders/q4/859yhpgn6x3fx6kv4mj5gmv40000gp/T/', '/tmp', '/var/tmp', '/usr/tmp', '/Users/Zhuanz/Desktop/cfd-harness-unified']\n", truncated_after_lines: None }, duration: 0ns, timed_out: false } }
 exited 1 in 198ms:
/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/config/__init__.py:331: PluggyTeardownRaisedWarning: A plugin raised an exception during an old-style hookwrapper teardown.
Plugin: helpconfig, Hook: pytest_cmdline_parse
FileNotFoundError: [Errno 2] No usable temporary directory found in ['/var/folders/q4/859yhpgn6x3fx6kv4mj5gmv40000gp/T/', '/tmp', '/var/tmp', '/usr/tmp', '/Users/Zhuanz/Desktop/cfd-harness-unified']
For more information see https://pluggy.readthedocs.io/en/stable/api_reference.html#pluggy.PluggyTeardownRaisedWarning
  config = pluginmanager.hook.pytest_cmdline_parse(
Traceback (most recent call last):
  File "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/runpy.py", line 197, in _run_module_as_main
    return _run_code(code, main_globals, None,
  File "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/runpy.py", line 87, in _run_code
    exec(code, run_globals)
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pytest/__main__.py", line 5, in <module>
    raise SystemExit(pytest.console_main())
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/config/__init__.py", line 192, in console_main
    code = main()
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/config/__init__.py", line 150, in main
    config = _prepareconfig(args, plugins)
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/config/__init__.py", line 331, in _prepareconfig
    config = pluginmanager.hook.pytest_cmdline_parse(
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_hooks.py", line 512, in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_manager.py", line 120, in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py", line 167, in _multicall
    raise exception
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py", line 139, in _multicall
    teardown.throw(exception)
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py", line 43, in run_old_style_hookwrapper
    teardown.send(result)
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/helpconfig.py", line 104, in pytest_cmdline_parse
    config: Config = outcome.get_result()
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_result.py", line 103, in get_result
    raise exc.with_traceback(tb)
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py", line 38, in run_old_style_hookwrapper
    res = yield
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py", line 121, in _multicall
    res = hook_impl.function(*args)
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/config/__init__.py", line 1075, in pytest_cmdline_parse
    self.parse(args)
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/config/__init__.py", line 1425, in parse
    self._preparse(args, addopts=addopts)
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/config/__init__.py", line 1327, in _preparse
    self.hook.pytest_load_initial_conftests(
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_hooks.py", line 512, in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_manager.py", line 120, in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py", line 167, in _multicall
    raise exception
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py", line 139, in _multicall
    teardown.throw(exception)
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py", line 53, in run_old_style_hookwrapper
    return result.get_result()
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_result.py", line 103, in get_result
    raise exc.with_traceback(tb)
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py", line 38, in run_old_style_hookwrapper
    res = yield
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py", line 107, in _multicall
    next(function_gen)  # first yield
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/pluggy/_callers.py", line 34, in run_old_style_hookwrapper
    next(teardown)
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/capture.py", line 149, in pytest_load_initial_conftests
    capman.start_global_capturing()
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/capture.py", line 750, in start_global_capturing
    self._global_capturing = _get_multicapture(self._method)
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/capture.py", line 692, in _get_multicapture
    return MultiCapture(in_=FDCapture(0), out=FDCapture(1), err=FDCapture(2))
  File "/Users/Zhuanz/Library/Python/3.9/lib/python/site-packages/_pytest/capture.py", line 466, in __init__
    TemporaryFile(buffering=0),
  File "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/tempfile.py", line 581, in TemporaryFile
    prefix, suffix, dir, output_type = _sanitize_params(prefix, suffix, dir)
  File "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/tempfile.py", line 118, in _sanitize_params
    dir = gettempdir()
  File "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/tempfile.py", line 287, in gettempdir
    tempdir = _get_default_tempdir()
  File "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/tempfile.py", line 219, in _get_default_tempdir
    raise FileNotFoundError(_errno.ENOENT,
FileNotFoundError: [Errno 2] No usable temporary directory found in ['/var/folders/q4/859yhpgn6x3fx6kv4mj5gmv40000gp/T/', '/tmp', '/var/tmp', '/usr/tmp', '/Users/Zhuanz/Desktop/cfd-harness-unified']

exec
/bin/zsh -lc "rg -n \"time step continuity errors|bounding (k|epsilon|omega)\" reports/phase5_fields/backward_facing_step -g 'log.*' | tail -n 40" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "rg -n \"time step continuity errors|bounding (k|epsilon|omega)\" reports/phase5_fields/circular_cylinder_wake -g 'log.*' | tail -n 40" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "rg -n \"time step continuity errors|bounding (k|epsilon|omega)\" reports/phase5_fields/lid_driven_cavity -g 'log.*' | tail -n 20" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
 succeeded in 0ms:
exec
/bin/zsh -lc "find reports/phase5_fields -maxdepth 3 -name 'log.*' | sort | sed -n '1,120p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
 succeeded in 0ms:
reports/phase5_fields/backward_facing_step/20260421T125637Z/log.simpleFoam
reports/phase5_fields/circular_cylinder_wake/20260421T150630Z/log.pimpleFoam
reports/phase5_fields/differential_heated_cavity/20260421T131052Z/log.buoyantFoam
reports/phase5_fields/duct_flow/20260421T131015Z/log.simpleFoam
reports/phase5_fields/impinging_jet/20260421T142307Z/log.buoyantFoam
reports/phase5_fields/lid_driven_cavity/20260421T082340Z/log.simpleFoam
reports/phase5_fields/naca0012_airfoil/20260421T142539Z/log.simpleFoam
reports/phase5_fields/plane_channel_flow/20260421T130203Z/log.icoFoam
reports/phase5_fields/rayleigh_benard_convection/20260421T142559Z/log.buoyantFoam
reports/phase5_fields/turbulent_flat_plate/20260421T130909Z/log.simpleFoam

codex
The test run is blocked by the sandbox’s tempdir restrictions, so I’m staying evidence-based from source plus real log artifacts already in the repo. I’m pulling the actual Phase 5 field logs now to sanity-check how the parser would behave on the live BFS / cylinder / LDC artifacts, not just the synthetic test strings.
exec
/bin/zsh -lc 'tail -n 120 reports/phase5_fields/turbulent_flat_plate/20260421T130909Z/log.simpleFoam' in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc 'tail -n 80 reports/phase5_fields/backward_facing_step/20260421T125637Z/log.simpleFoam' in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc 'tail -n 80 reports/phase5_fields/lid_driven_cavity/20260421T082340Z/log.simpleFoam' in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc 'tail -n 120 reports/phase5_fields/circular_cylinder_wake/20260421T150630Z/log.pimpleFoam' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
bounding k, min: -313.484 max: 1714.04 average: 29.5205
ExecutionTime = 0.157868 s  ClockTime = 0 s

Time = 31s

smoothSolver:  Solving for Ux, Initial residual = 0.247931, Final residual = 0.00181956, No Iterations 13
smoothSolver:  Solving for Uy, Initial residual = 0.675277, Final residual = 0.00414231, No Iterations 11
GAMG:  Solving for p, Initial residual = 0.720576, Final residual = 0.00388767, No Iterations 6
time step continuity errors : sum local = 0.68921, global = -0.0233435, cumulative = 0.0228762
smoothSolver:  Solving for epsilon, Initial residual = 0.221331, Final residual = 0.00154836, No Iterations 7
bounding epsilon, min: -106280 max: 716768 average: 6356.65
smoothSolver:  Solving for k, Initial residual = 0.171932, Final residual = 0.00127009, No Iterations 10
bounding k, min: -342.527 max: 1545.98 average: 28.7965
ExecutionTime = 0.159613 s  ClockTime = 0 s

Time = 32s

smoothSolver:  Solving for Ux, Initial residual = 0.201125, Final residual = 0.00155932, No Iterations 11
smoothSolver:  Solving for Uy, Initial residual = 0.564373, Final residual = 0.00491834, No Iterations 11
GAMG:  Solving for p, Initial residual = 0.71026, Final residual = 0.00456214, No Iterations 6
time step continuity errors : sum local = 1.01602, global = -0.00111461, cumulative = 0.0217615
smoothSolver:  Solving for epsilon, Initial residual = 0.168508, Final residual = 0.00156971, No Iterations 7
bounding epsilon, min: -15930.4 max: 963799 average: 5494.93
smoothSolver:  Solving for k, Initial residual = 0.154125, Final residual = 0.00133748, No Iterations 10
bounding k, min: -52.5853 max: 1966.69 average: 32.4113
ExecutionTime = 0.161593 s  ClockTime = 0 s

Time = 33s

smoothSolver:  Solving for Ux, Initial residual = 0.672095, Final residual = 0.00560551, No Iterations 9
smoothSolver:  Solving for Uy, Initial residual = 0.889972, Final residual = 0.00845567, No Iterations 9
GAMG:  Solving for p, Initial residual = 0.813762, Final residual = 0.00427376, No Iterations 6
time step continuity errors : sum local = 1.21906, global = 0.00132386, cumulative = 0.0230854
smoothSolver:  Solving for epsilon, Initial residual = 0.00760792, Final residual = 7.52599e-11, No Iterations 1
bounding epsilon, min: -2101.79 max: 9.69776e+06 average: 26433.6
smoothSolver:  Solving for k, Initial residual = 0.130358, Final residual = 0.00125517, No Iterations 8
bounding k, min: -17.7066 max: 2177.5 average: 41.2723
ExecutionTime = 0.163304 s  ClockTime = 0 s

Time = 34s

smoothSolver:  Solving for Ux, Initial residual = 1, Final residual = 0.00837022, No Iterations 11
smoothSolver:  Solving for Uy, Initial residual = 1, Final residual = 0.00757541, No Iterations 15
GAMG:  Solving for p, Initial residual = 0.881468, Final residual = 0.00822948, No Iterations 2
time step continuity errors : sum local = 1.74393e+10, global = 0.00108283, cumulative = 0.0241682
smoothSolver:  Solving for epsilon, Initial residual = 1, Final residual = 0.0083654, No Iterations 11
bounding epsilon, min: -1.3272e+14 max: 3.79409e+16 average: 7.99605e+13
smoothSolver:  Solving for k, Initial residual = 1, Final residual = 0.00346927, No Iterations 3
bounding k, min: -2.92944e+11 max: 9.43286e+11 average: 5.93319e+09
ExecutionTime = 0.164957 s  ClockTime = 0 s

Time = 35s

smoothSolver:  Solving for Ux, Initial residual = 0.78503, Final residual = 0.00674337, No Iterations 17
smoothSolver:  Solving for Uy, Initial residual = 0.641696, Final residual = 0.00538723, No Iterations 9
GAMG:  Solving for p, Initial residual = 0.835175, Final residual = 0.00496555, No Iterations 8
time step continuity errors : sum local = 2.89254e+09, global = -106.032, cumulative = -106.008
smoothSolver:  Solving for epsilon, Initial residual = 0.496766, Final residual = 0.00427618, No Iterations 7
bounding epsilon, min: -1.29708e+24 max: 1.68914e+25 average: 6.93631e+22
smoothSolver:  Solving for k, Initial residual = 0.999981, Final residual = 0.00871171, No Iterations 15
bounding k, min: -9.0735e+21 max: 7.57553e+22 average: 1.91511e+20
ExecutionTime = 0.166937 s  ClockTime = 0 s

Time = 36s

smoothSolver:  Solving for Ux, Initial residual = 0.0374628, Final residual = 0.000327544, No Iterations 4
smoothSolver:  Solving for Uy, Initial residual = 0.0233626, Final residual = 0.000198486, No Iterations 12
GAMG:  Solving for p, Initial residual = 8.83567e-07, Final residual = 8.83567e-07, No Iterations 0
time step continuity errors : sum local = 5.24523e+18, global = -1328.63, cumulative = -1434.64
smoothSolver:  Solving for epsilon, Initial residual = 6.27785e-09, Final residual = 6.27785e-09, No Iterations 0
bounding epsilon, min: 7.38706e-17 max: 1.03929e+30 average: 1.37234e+27
smoothSolver:  Solving for k, Initial residual = 3.34255e-06, Final residual = 2.90268e-08, No Iterations 16
bounding k, min: -6.41351e+30 max: 2.32895e+31 average: 1.39855e+29
ExecutionTime = 0.168564 s  ClockTime = 0 s


SIMPLE solution converged in 36 iterations

End


 succeeded in 0ms:
time step continuity errors : sum local = 1.54392e-06, global = 1.60413e-16, cumulative = 1.75317e-15
ExecutionTime = 16.4921 s  ClockTime = 17 s

Time = 1016s

smoothSolver:  Solving for Ux, Initial residual = 9.83997e-06, Final residual = 9.83997e-06, No Iterations 0
smoothSolver:  Solving for Uy, Initial residual = 1.0209e-05, Final residual = 8.35993e-06, No Iterations 1
GAMG:  Solving for p, Initial residual = 3.56415e-06, Final residual = 7.7533e-07, No Iterations 2
time step continuity errors : sum local = 1.12465e-06, global = -1.06986e-16, cumulative = 1.64618e-15
ExecutionTime = 16.5013 s  ClockTime = 17 s

Time = 1017s

smoothSolver:  Solving for Ux, Initial residual = 9.83811e-06, Final residual = 9.83811e-06, No Iterations 0
smoothSolver:  Solving for Uy, Initial residual = 1.01774e-05, Final residual = 8.3374e-06, No Iterations 1
GAMG:  Solving for p, Initial residual = 9.44845e-06, Final residual = 8.98965e-07, No Iterations 4
time step continuity errors : sum local = 1.32235e-06, global = 7.39366e-17, cumulative = 1.72012e-15
ExecutionTime = 16.5129 s  ClockTime = 17 s

Time = 1018s

smoothSolver:  Solving for Ux, Initial residual = 9.93881e-06, Final residual = 9.93881e-06, No Iterations 0
smoothSolver:  Solving for Uy, Initial residual = 1.00038e-05, Final residual = 8.19558e-06, No Iterations 1
GAMG:  Solving for p, Initial residual = 1.45642e-05, Final residual = 1.13295e-06, No Iterations 5
time step continuity errors : sum local = 1.63239e-06, global = 7.69368e-17, cumulative = 1.79706e-15
ExecutionTime = 16.5251 s  ClockTime = 17 s

Time = 1019s

smoothSolver:  Solving for Ux, Initial residual = 1.01104e-05, Final residual = 8.25828e-06, No Iterations 1
smoothSolver:  Solving for Uy, Initial residual = 9.73257e-06, Final residual = 9.73257e-06, No Iterations 0
GAMG:  Solving for p, Initial residual = 7.68409e-06, Final residual = 8.68504e-07, No Iterations 4
time step continuity errors : sum local = 1.29336e-06, global = -3.47462e-16, cumulative = 1.44959e-15
ExecutionTime = 16.5365 s  ClockTime = 17 s

Time = 1020s

smoothSolver:  Solving for Ux, Initial residual = 1.00046e-05, Final residual = 8.17578e-06, No Iterations 1
smoothSolver:  Solving for Uy, Initial residual = 9.8433e-06, Final residual = 9.8433e-06, No Iterations 0
GAMG:  Solving for p, Initial residual = 2.177e-05, Final residual = 1.90298e-06, No Iterations 5
time step continuity errors : sum local = 2.75245e-06, global = -9.32498e-17, cumulative = 1.35634e-15
ExecutionTime = 16.5492 s  ClockTime = 17 s

Time = 1021s

smoothSolver:  Solving for Ux, Initial residual = 9.72772e-06, Final residual = 9.72772e-06, No Iterations 0
smoothSolver:  Solving for Uy, Initial residual = 1.02289e-05, Final residual = 8.37262e-06, No Iterations 1
GAMG:  Solving for p, Initial residual = 7.61531e-06, Final residual = 7.5963e-07, No Iterations 5
time step continuity errors : sum local = 1.10597e-06, global = -1.95904e-16, cumulative = 1.16044e-15
ExecutionTime = 16.5619 s  ClockTime = 17 s

Time = 1022s

smoothSolver:  Solving for Ux, Initial residual = 9.63036e-06, Final residual = 9.63036e-06, No Iterations 0
smoothSolver:  Solving for Uy, Initial residual = 1.03241e-05, Final residual = 8.45485e-06, No Iterations 1
GAMG:  Solving for p, Initial residual = 5.59969e-06, Final residual = 6.87747e-07, No Iterations 3
time step continuity errors : sum local = 9.93559e-07, global = 1.56562e-16, cumulative = 1.317e-15
ExecutionTime = 16.5723 s  ClockTime = 17 s

Time = 1023s

smoothSolver:  Solving for Ux, Initial residual = 9.67096e-06, Final residual = 9.67096e-06, No Iterations 0
smoothSolver:  Solving for Uy, Initial residual = 1.02272e-05, Final residual = 8.37878e-06, No Iterations 1
GAMG:  Solving for p, Initial residual = 1.23026e-05, Final residual = 9.74333e-07, No Iterations 5
time step continuity errors : sum local = 1.44344e-06, global = -1.89661e-16, cumulative = 1.12734e-15
ExecutionTime = 16.585 s  ClockTime = 17 s

Time = 1024s

smoothSolver:  Solving for Ux, Initial residual = 9.81642e-06, Final residual = 9.81642e-06, No Iterations 0
smoothSolver:  Solving for Uy, Initial residual = 9.99311e-06, Final residual = 9.99311e-06, No Iterations 0
GAMG:  Solving for p, Initial residual = 7.0337e-06, Final residual = 6.35692e-07, No Iterations 4
time step continuity errors : sum local = 9.4486e-07, global = 1.85296e-16, cumulative = 1.31264e-15
ExecutionTime = 16.5959 s  ClockTime = 17 s


SIMPLE solution converged in 1024 iterations

End


 succeeded in 0ms:
smoothSolver:  Solving for Ux, Initial residual = 0.0035456, Final residual = 2.33436e-05, No Iterations 8
GAMG:  Solving for p, Initial residual = 0.0143495, Final residual = 0.000129533, No Iterations 11
GAMG:  Solving for p, Initial residual = 0.000131388, Final residual = 1.19844e-06, No Iterations 14
time step continuity errors : sum local = 0.000165186, global = -7.17094e-06, cumulative = 29.0062
DILUPBiCGStab:  Solving for omega, Initial residual = 0.00120808, Final residual = 7.84693e-06, No Iterations 1
DILUPBiCGStab:  Solving for k, Initial residual = 0.00250556, Final residual = 1.35853e-05, No Iterations 1
ExecutionTime = 25.0847 s  ClockTime = 25 s

Time = 990s

smoothSolver:  Solving for Ux, Initial residual = 0.00354398, Final residual = 2.33329e-05, No Iterations 8
GAMG:  Solving for p, Initial residual = 0.0143301, Final residual = 0.000129549, No Iterations 11
GAMG:  Solving for p, Initial residual = 0.000131405, Final residual = 1.19076e-06, No Iterations 14
time step continuity errors : sum local = 0.000163055, global = -7.07288e-06, cumulative = 29.0062
DILUPBiCGStab:  Solving for omega, Initial residual = 0.00120693, Final residual = 7.83919e-06, No Iterations 1
DILUPBiCGStab:  Solving for k, Initial residual = 0.00250426, Final residual = 1.3581e-05, No Iterations 1
ExecutionTime = 25.1062 s  ClockTime = 25 s

Time = 991s

smoothSolver:  Solving for Ux, Initial residual = 0.00354236, Final residual = 2.33221e-05, No Iterations 8
GAMG:  Solving for p, Initial residual = 0.0143107, Final residual = 0.000129556, No Iterations 11
GAMG:  Solving for p, Initial residual = 0.000131411, Final residual = 1.18232e-06, No Iterations 14
time step continuity errors : sum local = 0.00016084, global = -6.933e-06, cumulative = 29.0062
DILUPBiCGStab:  Solving for omega, Initial residual = 0.00120577, Final residual = 7.83164e-06, No Iterations 1
DILUPBiCGStab:  Solving for k, Initial residual = 0.00250295, Final residual = 1.35767e-05, No Iterations 1
ExecutionTime = 25.1277 s  ClockTime = 25 s

Time = 992s

smoothSolver:  Solving for Ux, Initial residual = 0.00354075, Final residual = 2.33114e-05, No Iterations 8
GAMG:  Solving for p, Initial residual = 0.0142912, Final residual = 0.000129534, No Iterations 11
GAMG:  Solving for p, Initial residual = 0.000131389, Final residual = 1.17156e-06, No Iterations 14
time step continuity errors : sum local = 0.000158337, global = -6.78848e-06, cumulative = 29.0062
DILUPBiCGStab:  Solving for omega, Initial residual = 0.00120462, Final residual = 7.82413e-06, No Iterations 1
DILUPBiCGStab:  Solving for k, Initial residual = 0.00250165, Final residual = 1.35725e-05, No Iterations 1
ExecutionTime = 25.1491 s  ClockTime = 25 s

Time = 993s

smoothSolver:  Solving for Ux, Initial residual = 0.00353913, Final residual = 2.33006e-05, No Iterations 8
GAMG:  Solving for p, Initial residual = 0.0142719, Final residual = 0.000129507, No Iterations 11
GAMG:  Solving for p, Initial residual = 0.000131362, Final residual = 1.1796e-06, No Iterations 14
time step continuity errors : sum local = 0.000158381, global = -6.79184e-06, cumulative = 29.0062
DILUPBiCGStab:  Solving for omega, Initial residual = 0.00120347, Final residual = 7.81649e-06, No Iterations 1
DILUPBiCGStab:  Solving for k, Initial residual = 0.00250036, Final residual = 1.35683e-05, No Iterations 1
ExecutionTime = 25.1707 s  ClockTime = 25 s

Time = 994s

smoothSolver:  Solving for Ux, Initial residual = 0.00353752, Final residual = 2.32898e-05, No Iterations 8
GAMG:  Solving for p, Initial residual = 0.0142526, Final residual = 0.000129469, No Iterations 11
GAMG:  Solving for p, Initial residual = 0.000131324, Final residual = 1.17081e-06, No Iterations 14
time step continuity errors : sum local = 0.000156174, global = -6.67493e-06, cumulative = 29.0062
DILUPBiCGStab:  Solving for omega, Initial residual = 0.00120232, Final residual = 7.80897e-06, No Iterations 1
DILUPBiCGStab:  Solving for k, Initial residual = 0.00249907, Final residual = 1.35641e-05, No Iterations 1
ExecutionTime = 25.1923 s  ClockTime = 26 s

Time = 995s

smoothSolver:  Solving for Ux, Initial residual = 0.00353591, Final residual = 2.3279e-05, No Iterations 8
GAMG:  Solving for p, Initial residual = 0.0142334, Final residual = 0.00012944, No Iterations 11
GAMG:  Solving for p, Initial residual = 0.000131295, Final residual = 1.16161e-06, No Iterations 14
time step continuity errors : sum local = 0.000153937, global = -6.54417e-06, cumulative = 29.0062
DILUPBiCGStab:  Solving for omega, Initial residual = 0.00120118, Final residual = 7.80131e-06, No Iterations 1
DILUPBiCGStab:  Solving for k, Initial residual = 0.00249779, Final residual = 1.35599e-05, No Iterations 1
ExecutionTime = 25.2139 s  ClockTime = 26 s

Time = 996s

smoothSolver:  Solving for Ux, Initial residual = 0.00353431, Final residual = 2.32682e-05, No Iterations 8
GAMG:  Solving for p, Initial residual = 0.0142142, Final residual = 0.000129957, No Iterations 11
GAMG:  Solving for p, Initial residual = 0.00013182, Final residual = 1.19287e-06, No Iterations 14
time step continuity errors : sum local = 0.000157048, global = -6.73456e-06, cumulative = 29.0062
DILUPBiCGStab:  Solving for omega, Initial residual = 0.00120003, Final residual = 7.79388e-06, No Iterations 1
DILUPBiCGStab:  Solving for k, Initial residual = 0.00249652, Final residual = 1.35557e-05, No Iterations 1
ExecutionTime = 25.2354 s  ClockTime = 26 s

Time = 997s

smoothSolver:  Solving for Ux, Initial residual = 0.00353274, Final residual = 2.32574e-05, No Iterations 8
GAMG:  Solving for p, Initial residual = 0.014195, Final residual = 0.000129904, No Iterations 11
GAMG:  Solving for p, Initial residual = 0.000131767, Final residual = 1.19767e-06, No Iterations 14
time step continuity errors : sum local = 0.000156653, global = -6.71821e-06, cumulative = 29.0062
DILUPBiCGStab:  Solving for omega, Initial residual = 0.00119889, Final residual = 7.78656e-06, No Iterations 1
DILUPBiCGStab:  Solving for k, Initial residual = 0.00249525, Final residual = 1.35516e-05, No Iterations 1
ExecutionTime = 25.2569 s  ClockTime = 26 s

Time = 998s

smoothSolver:  Solving for Ux, Initial residual = 0.0035312, Final residual = 2.32466e-05, No Iterations 8
GAMG:  Solving for p, Initial residual = 0.0141757, Final residual = 0.000130355, No Iterations 11
GAMG:  Solving for p, Initial residual = 0.000132225, Final residual = 1.2481e-06, No Iterations 14
time step continuity errors : sum local = 0.000162186, global = -6.99731e-06, cumulative = 29.0062
DILUPBiCGStab:  Solving for omega, Initial residual = 0.00119776, Final residual = 7.77893e-06, No Iterations 1
DILUPBiCGStab:  Solving for k, Initial residual = 0.00249398, Final residual = 1.35474e-05, No Iterations 1
ExecutionTime = 25.2785 s  ClockTime = 26 s

Time = 999s

smoothSolver:  Solving for Ux, Initial residual = 0.00352966, Final residual = 2.32357e-05, No Iterations 8
GAMG:  Solving for p, Initial residual = 0.0141562, Final residual = 0.000130281, No Iterations 11
GAMG:  Solving for p, Initial residual = 0.00013215, Final residual = 1.2246e-06, No Iterations 14
time step continuity errors : sum local = 0.000158097, global = -6.77249e-06, cumulative = 29.0062
DILUPBiCGStab:  Solving for omega, Initial residual = 0.00119662, Final residual = 7.77131e-06, No Iterations 1
DILUPBiCGStab:  Solving for k, Initial residual = 0.00249272, Final residual = 1.35433e-05, No Iterations 1
ExecutionTime = 25.3 s  ClockTime = 26 s

Time = 1000s

smoothSolver:  Solving for Ux, Initial residual = 0.00352813, Final residual = 2.32249e-05, No Iterations 8
GAMG:  Solving for p, Initial residual = 0.0141368, Final residual = 0.000130236, No Iterations 11
GAMG:  Solving for p, Initial residual = 0.000132103, Final residual = 1.22432e-06, No Iterations 14
time step continuity errors : sum local = 0.000157034, global = -6.69858e-06, cumulative = 29.0061
DILUPBiCGStab:  Solving for omega, Initial residual = 0.00119549, Final residual = 7.76359e-06, No Iterations 1
DILUPBiCGStab:  Solving for k, Initial residual = 0.00249147, Final residual = 1.35393e-05, No Iterations 1
ExecutionTime = 25.3723 s  ClockTime = 26 s

End


 succeeded in 0ms:
time step continuity errors : sum local = 0.152284, global = 0.0190558, cumulative = 15.2152
DILUPBiCGStab:  Solving for omega, Initial residual = 0.000520813, Final residual = 3.52612e-08, No Iterations 2
DILUPBiCGStab:  Solving for k, Initial residual = 0.000834317, Final residual = 9.47117e-08, No Iterations 2
bounding k, min: -0.00420261 max: 40.1253 average: 0.207076
ExecutionTime = 13.9643 s  ClockTime = 17 s

Courant Number mean: 4.39011 max: 5.87528
Time = 0.988s

DILUPBiCGStab:  Solving for Ux, Initial residual = 5.04259e-06, Final residual = 2.13677e-07, No Iterations 1
DILUPBiCGStab:  Solving for Uy, Initial residual = 4.27221e-06, Final residual = 1.74749e-07, No Iterations 1
GAMG:  Solving for p, Initial residual = 6.27532e-07, Final residual = 6.27532e-07, No Iterations 0
GAMG:  Solving for p, Initial residual = 6.27532e-07, Final residual = 6.27532e-07, No Iterations 0
time step continuity errors : sum local = 0.152281, global = 0.0190558, cumulative = 15.2343
GAMG:  Solving for p, Initial residual = 6.27532e-07, Final residual = 6.27532e-07, No Iterations 0
GAMG:  Solving for p, Initial residual = 6.27532e-07, Final residual = 6.27532e-07, No Iterations 0
time step continuity errors : sum local = 0.152281, global = 0.0190558, cumulative = 15.2534
DILUPBiCGStab:  Solving for omega, Initial residual = 0.000529031, Final residual = 2.42262e-08, No Iterations 2
DILUPBiCGStab:  Solving for k, Initial residual = 0.00086087, Final residual = 6.28684e-08, No Iterations 2
bounding k, min: -0.00897249 max: 40.0113 average: 0.207064
ExecutionTime = 13.9889 s  ClockTime = 17 s

Courant Number mean: 4.39011 max: 5.87528
Time = 0.99s

DILUPBiCGStab:  Solving for Ux, Initial residual = 4.94067e-06, Final residual = 2.03363e-07, No Iterations 1
DILUPBiCGStab:  Solving for Uy, Initial residual = 4.31478e-06, Final residual = 1.76116e-07, No Iterations 1
GAMG:  Solving for p, Initial residual = 6.27544e-07, Final residual = 6.27544e-07, No Iterations 0
GAMG:  Solving for p, Initial residual = 6.27544e-07, Final residual = 6.27544e-07, No Iterations 0
time step continuity errors : sum local = 0.152284, global = 0.0190558, cumulative = 15.2724
GAMG:  Solving for p, Initial residual = 6.27545e-07, Final residual = 6.27545e-07, No Iterations 0
GAMG:  Solving for p, Initial residual = 6.27545e-07, Final residual = 6.27545e-07, No Iterations 0
time step continuity errors : sum local = 0.152284, global = 0.0190558, cumulative = 15.2915
DILUPBiCGStab:  Solving for omega, Initial residual = 0.000518086, Final residual = 3.41953e-08, No Iterations 2
DILUPBiCGStab:  Solving for k, Initial residual = 0.000821225, Final residual = 9.5208e-08, No Iterations 2
bounding k, min: -0.00408622 max: 40.1139 average: 0.207064
ExecutionTime = 14.0138 s  ClockTime = 17 s

Courant Number mean: 4.39011 max: 5.87528
Time = 0.992s

DILUPBiCGStab:  Solving for Ux, Initial residual = 5.00631e-06, Final residual = 2.13654e-07, No Iterations 1
DILUPBiCGStab:  Solving for Uy, Initial residual = 4.26562e-06, Final residual = 1.73739e-07, No Iterations 1
GAMG:  Solving for p, Initial residual = 6.27533e-07, Final residual = 6.27533e-07, No Iterations 0
GAMG:  Solving for p, Initial residual = 6.27533e-07, Final residual = 6.27533e-07, No Iterations 0
time step continuity errors : sum local = 0.152282, global = 0.0190558, cumulative = 15.3105
GAMG:  Solving for p, Initial residual = 6.27532e-07, Final residual = 6.27532e-07, No Iterations 0
GAMG:  Solving for p, Initial residual = 6.27532e-07, Final residual = 6.27532e-07, No Iterations 0
time step continuity errors : sum local = 0.152282, global = 0.0190558, cumulative = 15.3296
DILUPBiCGStab:  Solving for omega, Initial residual = 0.00052771, Final residual = 2.50113e-08, No Iterations 2
DILUPBiCGStab:  Solving for k, Initial residual = 0.000858208, Final residual = 6.34548e-08, No Iterations 2
bounding k, min: -0.00888366 max: 40.011 average: 0.207051
ExecutionTime = 14.0393 s  ClockTime = 17 s

Courant Number mean: 4.39011 max: 5.87528
Time = 0.994s

DILUPBiCGStab:  Solving for Ux, Initial residual = 4.93284e-06, Final residual = 2.02363e-07, No Iterations 1
DILUPBiCGStab:  Solving for Uy, Initial residual = 4.26877e-06, Final residual = 1.73966e-07, No Iterations 1
GAMG:  Solving for p, Initial residual = 6.27545e-07, Final residual = 6.27545e-07, No Iterations 0
GAMG:  Solving for p, Initial residual = 6.27545e-07, Final residual = 6.27545e-07, No Iterations 0
time step continuity errors : sum local = 0.152284, global = 0.0190558, cumulative = 15.3486
GAMG:  Solving for p, Initial residual = 6.27545e-07, Final residual = 6.27545e-07, No Iterations 0
GAMG:  Solving for p, Initial residual = 6.27545e-07, Final residual = 6.27545e-07, No Iterations 0
time step continuity errors : sum local = 0.152285, global = 0.0190558, cumulative = 15.3677
DILUPBiCGStab:  Solving for omega, Initial residual = 0.000517178, Final residual = 3.533e-08, No Iterations 2
DILUPBiCGStab:  Solving for k, Initial residual = 0.000819424, Final residual = 9.9248e-08, No Iterations 2
bounding k, min: -0.00416879 max: 40.1026 average: 0.207055
ExecutionTime = 14.0645 s  ClockTime = 17 s

Courant Number mean: 4.39011 max: 5.87528
Time = 0.996s

DILUPBiCGStab:  Solving for Ux, Initial residual = 5.01652e-06, Final residual = 2.11013e-07, No Iterations 1
DILUPBiCGStab:  Solving for Uy, Initial residual = 4.33294e-06, Final residual = 1.75324e-07, No Iterations 1
GAMG:  Solving for p, Initial residual = 6.27532e-07, Final residual = 6.27532e-07, No Iterations 0
GAMG:  Solving for p, Initial residual = 6.27532e-07, Final residual = 6.27532e-07, No Iterations 0
time step continuity errors : sum local = 0.152282, global = 0.0190558, cumulative = 15.3867
GAMG:  Solving for p, Initial residual = 6.27532e-07, Final residual = 6.27532e-07, No Iterations 0
GAMG:  Solving for p, Initial residual = 6.27532e-07, Final residual = 6.27532e-07, No Iterations 0
time step continuity errors : sum local = 0.152281, global = 0.0190558, cumulative = 15.4058
DILUPBiCGStab:  Solving for omega, Initial residual = 0.000528797, Final residual = 2.34581e-08, No Iterations 2
DILUPBiCGStab:  Solving for k, Initial residual = 0.000854637, Final residual = 6.4168e-08, No Iterations 2
bounding k, min: -0.00886771 max: 40.0079 average: 0.207048
ExecutionTime = 14.092 s  ClockTime = 17 s

Courant Number mean: 4.39011 max: 5.87528
Time = 0.998s

DILUPBiCGStab:  Solving for Ux, Initial residual = 5.01672e-06, Final residual = 2.06643e-07, No Iterations 1
DILUPBiCGStab:  Solving for Uy, Initial residual = 4.29839e-06, Final residual = 1.75837e-07, No Iterations 1
GAMG:  Solving for p, Initial residual = 6.27545e-07, Final residual = 6.27545e-07, No Iterations 0
GAMG:  Solving for p, Initial residual = 6.27545e-07, Final residual = 6.27545e-07, No Iterations 0
time step continuity errors : sum local = 0.152284, global = 0.0190558, cumulative = 15.4249
GAMG:  Solving for p, Initial residual = 6.27545e-07, Final residual = 6.27545e-07, No Iterations 0
GAMG:  Solving for p, Initial residual = 6.27545e-07, Final residual = 6.27545e-07, No Iterations 0
time step continuity errors : sum local = 0.152285, global = 0.0190558, cumulative = 15.4439
DILUPBiCGStab:  Solving for omega, Initial residual = 0.000517859, Final residual = 3.57742e-08, No Iterations 2
DILUPBiCGStab:  Solving for k, Initial residual = 0.00082816, Final residual = 9.4539e-08, No Iterations 2
bounding k, min: -0.00424706 max: 40.1119 average: 0.207056
ExecutionTime = 14.1202 s  ClockTime = 17 s

Courant Number mean: 4.39011 max: 5.87528
Time = 1s

DILUPBiCGStab:  Solving for Ux, Initial residual = 4.93502e-06, Final residual = 2.08646e-07, No Iterations 1
DILUPBiCGStab:  Solving for Uy, Initial residual = 4.42518e-06, Final residual = 1.80359e-07, No Iterations 1
GAMG:  Solving for p, Initial residual = 6.27532e-07, Final residual = 6.27532e-07, No Iterations 0
GAMG:  Solving for p, Initial residual = 6.27532e-07, Final residual = 6.27532e-07, No Iterations 0
time step continuity errors : sum local = 0.152281, global = 0.0190558, cumulative = 15.463
GAMG:  Solving for p, Initial residual = 6.27532e-07, Final residual = 6.27532e-07, No Iterations 0
GAMG:  Solving for p, Initial residual = 6.27532e-07, Final residual = 6.27532e-07, No Iterations 0
time step continuity errors : sum local = 0.152281, global = 0.0190558, cumulative = 15.482
DILUPBiCGStab:  Solving for omega, Initial residual = 0.000532434, Final residual = 2.29729e-08, No Iterations 2
DILUPBiCGStab:  Solving for k, Initial residual = 0.000856248, Final residual = 6.47183e-08, No Iterations 2
bounding k, min: -0.00891886 max: 40.021 average: 0.207056
ExecutionTime = 14.2412 s  ClockTime = 17 s

End


exec
/bin/zsh -lc "nl -ba src/comparator_gates.py | sed -n '198,245p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
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

exec
/bin/zsh -lc "find reports/phase5_fields/backward_facing_step/20260421T125637Z/VTK -maxdepth 3 -type f | sort | sed -n '1,80p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "find reports/phase5_fields/circular_cylinder_wake/20260421T150630Z/VTK -maxdepth 3 -type f | sort | sed -n '1,80p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
reports/phase5_fields/backward_facing_step/20260421T125637Z/VTK/allPatches/allPatches_36.vtk
reports/phase5_fields/backward_facing_step/20260421T125637Z/VTK/ldc_88913_1776776197258_36.vtk

exec
/bin/zsh -lc "find reports/phase5_fields/naca0012_airfoil/20260421T142539Z/VTK -maxdepth 3 -type f | sort | sed -n '1,80p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
reports/phase5_fields/circular_cylinder_wake/20260421T150630Z/VTK/allPatches/allPatches_500.vtk
reports/phase5_fields/circular_cylinder_wake/20260421T150630Z/VTK/ldc_4169_1776783990890_500.vtk

 succeeded in 0ms:
reports/phase5_fields/naca0012_airfoil/20260421T142539Z/VTK/allPatches/allPatches_439.vtk
reports/phase5_fields/naca0012_airfoil/20260421T142539Z/VTK/ldc_89360_1776781539634_439.vtk

exec
/bin/zsh -lc "nl -ba ui/backend/services/validation_report.py | sed -n '537,590p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
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

exec
/bin/zsh -lc "rg -n \"U_ref|U_bulk|top_wall_u|lid_velocity_u|velocity_inlet|inlet.*U|freestream|free[-_ ]stream|chord_length|nozzle_diameter|wall_heat_flux|dT|U_inf\" src/foam_agent_adapter.py src/task_runner.py knowledge/whitelist.yaml -S | sed -n '1,220p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
knowledge/whitelist.yaml:19:      top_wall_u: 1.0
knowledge/whitelist.yaml:218:      nozzle_diameter: 0.05
knowledge/whitelist.yaml:247:      chord_length: 1.0
src/foam_agent_adapter.py:89:# (where Ra is derived from g, beta, dT, L, nu, Pr — five values that must
src/foam_agent_adapter.py:91:# in inlet-U=1 convention). Other builders take Re as a direct velocity
src/foam_agent_adapter.py:842:stopAt          endTime;
src/foam_agent_adapter.py:844:endTime         2000;
src/foam_agent_adapter.py:1178:        # Re=7600, H=1, U_bulk = nu*Re/H = nu*7600
src/foam_agent_adapter.py:1180:        # Gold Standard: nu = U_bulk * H / Re, U_bulk 由 Re 反推
src/foam_agent_adapter.py:1181:        # 这里 nu = 1/7600 m^2/s  (U_bulk=1 m/s, H=1 m)
src/foam_agent_adapter.py:1245:stopAt          endTime;
src/foam_agent_adapter.py:1247:endTime         1000;
src/foam_agent_adapter.py:1426:        # Inlet: uniform flow U = (U_bulk, 0, 0), where U_bulk = 1 m/s
src/foam_agent_adapter.py:1427:        # (Re = U_bulk*H/nu, so U_bulk = nu*Re/H = nu*7600)
src/foam_agent_adapter.py:1818:        # Boussinesq validity: beta * dT << 1
src/foam_agent_adapter.py:1819:        # At mean T=323K: beta=1/T_mean≈0.0031; set dT=10K → beta*dT≈0.031 (VALID)
src/foam_agent_adapter.py:1820:        # dT=10K works for both Ra=1e6 (NC Cavity) and Ra=1e10 (DHC) via g scaling
src/foam_agent_adapter.py:1823:        dT = T_hot - T_cold  # 10K — Boussinesq-valid for all Ra
src/foam_agent_adapter.py:1839:        # Ra = g * beta * dT * L^3 / (nu * alpha)
src/foam_agent_adapter.py:1840:        # g = Ra * nu * alpha / (beta * dT * L^3)
src/foam_agent_adapter.py:1841:        g = Ra * nu * alpha / (beta * dT * L**3)  # gravity magnitude
src/foam_agent_adapter.py:1854:        # Store dT/L in boundary_conditions for the extractor (TaskSpec is local to this call)
src/foam_agent_adapter.py:1857:        task_spec.boundary_conditions["dT"] = dT
src/foam_agent_adapter.py:2104:        # endTime=500 (1000 steps) would take ~19h. Characteristic time τ=L/v_buoy
src/foam_agent_adapter.py:2105:        # ≈ 0.84s at Ra=1e10, so endTime=10 (~12τ) is sufficient for quasi-steady
src/foam_agent_adapter.py:2106:        # Nu extraction. 80²-uniform baseline (Ra=1e6) keeps endTime=500 unchanged.
src/foam_agent_adapter.py:2132:stopAt          endTime;
src/foam_agent_adapter.py:2134:endTime         500;
src/foam_agent_adapter.py:2158:        # EX-1-007 B1: writeInterval must be <= endTime, else postProcess -latestTime
src/foam_agent_adapter.py:2160:        # (100 then 200) — collapsed to single 200, now parameterized to endTime.
src/foam_agent_adapter.py:2164:                "endTime         500;",
src/foam_agent_adapter.py:2165:                "endTime         {0};".format(_dhc_end_time),
src/foam_agent_adapter.py:2963:            declared_dT=dT,
src/foam_agent_adapter.py:2976:        declared_dT: float,
src/foam_agent_adapter.py:3023:        Ra_effective = g_mag * beta * declared_dT * (declared_L ** 3) / (nu * alpha)
src/foam_agent_adapter.py:3035:                "dT={:.4f}, L={:.4f}. Fix the generator or update the declared "
src/foam_agent_adapter.py:3038:                    beta, mu, Pr, g_mag, declared_dT, declared_L,
src/foam_agent_adapter.py:3057:        The convention U_bulk=1 m/s means Re = 1/nu — any drift here means
src/foam_agent_adapter.py:3097:        - Inlet (x=-5D): fixedValue U=(U_bulk,0,0), zeroGradient p
src/foam_agent_adapter.py:3115:        U_bulk = 1.0
src/foam_agent_adapter.py:3127:        task_spec.boundary_conditions["U_bulk"] = U_bulk
src/foam_agent_adapter.py:3273:stopAt          endTime;
src/foam_agent_adapter.py:3274:endTime         50;
src/foam_agent_adapter.py:3452:        value           uniform ({U_bulk} 0 0);
src/foam_agent_adapter.py:3528:        - inlet: uniform velocity U = (U_bulk, 0, 0)
src/foam_agent_adapter.py:3538:        nu_val = 1.0 / Re  # U_bulk=1 m/s → nu = 1/Re
src/foam_agent_adapter.py:3539:        U_bulk = 1.0  # m/s (consistent with nu=1/Re)
src/foam_agent_adapter.py:3713:stopAt          endTime;
src/foam_agent_adapter.py:3714:endTime         1000;
src/foam_agent_adapter.py:3993:        value           uniform ({U_bulk} 0 0);
src/foam_agent_adapter.py:4269:        U_bulk = 1.0  # m/s
src/foam_agent_adapter.py:4270:        nu_val = U_bulk * D / Re  # kinematic viscosity
src/foam_agent_adapter.py:4271:        # DEC-V61-041: plumb D, U_ref so the FFT emitter doesn't have to
src/foam_agent_adapter.py:4277:        task_spec.boundary_conditions["U_ref"] = U_bulk
src/foam_agent_adapter.py:4621:stopAt          endTime;
src/foam_agent_adapter.py:4622:// DEC-V61-041: endTime extended to 200 convective units (D=0.1, U=1 →
src/foam_agent_adapter.py:4627:endTime         200.0;
src/foam_agent_adapter.py:4653:// matches the inlet U_bulk. Codex DEC-041 round 1 BLOCKER fix: Aref
src/foam_agent_adapter.py:4883:internalField   uniform ({U_bulk} 0 0);
src/foam_agent_adapter.py:4887:    inlet        {{ type fixedValue; value uniform ({U_bulk} 0 0); }}
src/foam_agent_adapter.py:5073:        U_bulk = 1.0
src/foam_agent_adapter.py:5074:        nu_val = U_bulk * D / Re
src/foam_agent_adapter.py:5350:stopAt          endTime;
src/foam_agent_adapter.py:5351:endTime         1000;
src/foam_agent_adapter.py:5529:        U_nozzle = U_bulk
src/foam_agent_adapter.py:5555:    inlet           {{ type fixedValue; value uniform (0 0 {U_bulk:.6f}); }}
src/foam_agent_adapter.py:5930:        chord = float(bc.get("chord_length", 1.0))
src/foam_agent_adapter.py:5931:        U_inf = 1.0  # freestream velocity
src/foam_agent_adapter.py:5932:        nu_val = U_inf * chord / Re
src/foam_agent_adapter.py:5933:        # DEC-V61-044: plumb chord + U_inf + rho into boundary_conditions
src/foam_agent_adapter.py:5935:        # p → Cp without re-deriving the freestream from other sources.
src/foam_agent_adapter.py:5938:        bc.setdefault("chord_length", chord)
src/foam_agent_adapter.py:5939:        bc["U_inf"] = U_inf
src/foam_agent_adapter.py:6096:        inGroups        (freestream);
src/foam_agent_adapter.py:6110:        inGroups        (freestream);
src/foam_agent_adapter.py:6234:stopAt          endTime;
src/foam_agent_adapter.py:6235:endTime         2000;
src/foam_agent_adapter.py:6370:        Ux = U_inf
src/foam_agent_adapter.py:6373:        # k = 1.5*(U_inf*I)^2  --  gives physically consistent TKE
src/foam_agent_adapter.py:6381:        k_init = 1.5 * (U_inf * I_turb) ** 2   # = 3.75e-5
src/foam_agent_adapter.py:6409:    freestream
src/foam_agent_adapter.py:6411:        type            freestreamVelocity;
src/foam_agent_adapter.py:6412:        freestreamValue uniform ({Ux} 0 0);
src/foam_agent_adapter.py:6448:    freestream
src/foam_agent_adapter.py:6450:        type            freestreamPressure;
src/foam_agent_adapter.py:6451:        freestreamValue uniform 0;
src/foam_agent_adapter.py:6488:    freestream {{ type inletOutlet; inletValue uniform {k_init}; value uniform {k_init}; }}
src/foam_agent_adapter.py:6523:    freestream {{ type inletOutlet; inletValue uniform {omega_init}; value uniform {omega_init}; }}
src/foam_agent_adapter.py:6558:    freestream {{ type calculated; value uniform 0; }}
src/foam_agent_adapter.py:6600:                    f"(chord={chord:g}); Cp = (p - p_inf) / (0.5*U_inf^2), "
src/foam_agent_adapter.py:6601:                    f"U_inf={U_inf:g}, p_inf=0 gauge"
src/foam_agent_adapter.py:6793:            task_spec.boundary_conditions.get("lid_velocity_u", 1.0)
src/foam_agent_adapter.py:7747:        chord = float(bc.get("chord_length", 1.0))
src/foam_agent_adapter.py:7748:        U_inf = float(bc.get("U_inf", 1.0))
src/foam_agent_adapter.py:7761:                U_inf=U_inf,
src/foam_agent_adapter.py:7789:        q_ref = 0.5 * rho * U_inf * U_inf
src/foam_agent_adapter.py:8121:            dT_bulk = float(bc.get("dT", 10.0))
src/foam_agent_adapter.py:8125:            ) * L / dT_bulk
src/foam_agent_adapter.py:8274:        U_ref = float(bc.get("U_ref", 1.0))
src/foam_agent_adapter.py:8283:                emitted = emit_strouhal(case_dir, D=D, U_ref=U_ref)
src/foam_agent_adapter.py:8300:        q_ref = 0.5 * rho * U_ref ** 2
src/foam_agent_adapter.py:8335:        然后 Cf = tau_w / (0.5*rho*U_ref^2) = nu * (du/dy) / (0.5*U_ref^2)
src/foam_agent_adapter.py:8344:        U_ref = 1.0
src/foam_agent_adapter.py:8423:                Cf = tau_w / (0.5 * U_ref**2)
src/foam_agent_adapter.py:8432:                        x_local = x_target / U_ref  # physical x position
src/foam_agent_adapter.py:8433:                        Re_x = U_ref * x_local / nu_val
src/foam_agent_adapter.py:8471:        temperatures RADIALLY (dT/dr) — which is ≈0 by symmetry on a
src/foam_agent_adapter.py:8544:            # Stagnation Nu definition: h·D/k = D·|dT/dn|/ΔT (dimensionless).
src/foam_agent_adapter.py:8593:        U_ref = 1.0
src/foam_agent_adapter.py:8595:        chord = float(bc.get("chord_length", 1.0))
src/foam_agent_adapter.py:8597:        q_ref = 0.5 * rho * U_ref**2

exec
/bin/zsh -lc "rg -n \"_audit_fixture_doc\\(|u_ref=\" -S ." in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
./src/comparator_gates.py:278:                    f"({threshold:.6g}, U_ref={U_ref}). This indicates "
./src/cylinder_strouhal_fft.py:390:        U_ref=U_ref,
./scripts/phase5_audit_run.py:292:def _audit_fixture_doc(
./scripts/phase5_audit_run.py:409:                U_ref=u_ref,
./scripts/phase5_audit_run.py:563:    doc = _audit_fixture_doc(
./src/foam_agent_adapter.py:8283:                emitted = emit_strouhal(case_dir, D=D, U_ref=U_ref)
./tests/test_cylinder_strouhal_fft.py:167:    result = compute_strouhal(t, cl, cd, U_ref=1.0, D=0.1, transient_trim_s=50.0)
./tests/test_cylinder_strouhal_fft.py:192:        t_arr, cl_arr, cd_arr, U_ref=1.0, D=0.1, transient_trim_s=50.0
./tests/test_cylinder_strouhal_fft.py:213:        t, cl, cd, U_ref=1.0, D=0.1, transient_trim_s=50.0
./tests/test_cylinder_strouhal_fft.py:230:        compute_strouhal(t, cl, cd, U_ref=1.0, D=0.1, transient_trim_s=50.0)
./tests/test_cylinder_strouhal_fft.py:241:        compute_strouhal(t, cl, cd, U_ref=1.0, D=0.1, transient_trim_s=50.0)
./tests/test_cylinder_strouhal_fft.py:247:                         U_ref=1.0, D=0.0)
./tests/test_cylinder_strouhal_fft.py:253:                         U_ref=0.0, D=0.1)
./tests/test_cylinder_strouhal_fft.py:258:        compute_strouhal([0.0, 1.0], [0.0], [1.0, 1.0], U_ref=1.0, D=0.1)
./tests/test_cylinder_strouhal_fft.py:265:    assert emit_strouhal(tmp_path, D=0.1, U_ref=1.0) is None
./tests/test_cylinder_strouhal_fft.py:273:    result = emit_strouhal(tmp_path, D=0.1, U_ref=1.0, transient_trim_s=50.0)
./tests/test_cylinder_strouhal_fft.py:288:        emit_strouhal(tmp_path, D=0.1, U_ref=1.0)
./tests/test_cylinder_strouhal_fft.py:298:    result = emit_strouhal(tmp_path, D=0.1, U_ref=1.0, transient_trim_s=50.0)
./ui/backend/tests/test_comparator_gates_g3_g4_g5.py:86:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./ui/backend/tests/test_comparator_gates_g3_g4_g5.py:100:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./ui/backend/tests/test_comparator_gates_g3_g4_g5.py:108:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./ui/backend/tests/test_comparator_gates_g3_g4_g5.py:119:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./ui/backend/tests/test_comparator_gates_g3_g4_g5.py:134:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./ui/backend/tests/test_comparator_gates_g3_g4_g5.py:144:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./ui/backend/tests/test_comparator_gates_g3_g4_g5.py:155:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./ui/backend/tests/test_comparator_gates_g3_g4_g5.py:165:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./ui/backend/tests/test_comparator_gates_g3_g4_g5.py:181:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./ui/backend/tests/test_comparator_gates_g3_g4_g5.py:190:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./ui/backend/tests/test_comparator_gates_g3_g4_g5.py:208:    violations = cg.check_all_gates(log_path=_REAL_BFS_LOG, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec038_codex_review.md:796:- `test_g3_velocity_overflow_fail_synthetic_vtk` — crafted VTK with U=500, U_ref=1 → FAIL
./reports/codex_tool_reports/20260422_dec038_codex_review.md:1698:   292	def _audit_fixture_doc(
./reports/codex_tool_reports/20260422_dec038_codex_review.md:1815:   409	                U_ref=u_ref,
./reports/codex_tool_reports/20260422_dec038_codex_review.md:3838:   278	                    f"({threshold:.6g}, U_ref={U_ref}). This indicates "
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:1031:   128	def _audit_fixture_doc(
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md:1194:   291	    doc = _audit_fixture_doc(
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:1785: def _audit_fixture_doc(
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md:2171:   312	    doc = _audit_fixture_doc(
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:537:- `test_g3_velocity_overflow_fail_synthetic_vtk` — crafted VTK with U=500, U_ref=1 → FAIL
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:925:                    f"({threshold:.6g}, U_ref={U_ref}). This indicates "
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:1125:def _audit_fixture_doc(
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:1242:                U_ref=u_ref,
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:1622:    doc = _audit_fixture_doc(
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:2715:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:2729:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:2737:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:2748:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:2763:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:2773:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:2784:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:2794:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:2812:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:2821:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:2839:    violations = cg.check_all_gates(log_path=_REAL_BFS_LOG, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:2940:ui/backend/tests/test_comparator_gates_g3_g4_g5.py:86:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:2942:ui/backend/tests/test_comparator_gates_g3_g4_g5.py:100:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:2943:ui/backend/tests/test_comparator_gates_g3_g4_g5.py:108:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:2944:ui/backend/tests/test_comparator_gates_g3_g4_g5.py:119:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:2945:ui/backend/tests/test_comparator_gates_g3_g4_g5.py:134:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:2946:ui/backend/tests/test_comparator_gates_g3_g4_g5.py:144:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:2947:ui/backend/tests/test_comparator_gates_g3_g4_g5.py:155:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:2949:ui/backend/tests/test_comparator_gates_g3_g4_g5.py:165:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:2950:ui/backend/tests/test_comparator_gates_g3_g4_g5.py:181:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:2951:ui/backend/tests/test_comparator_gates_g3_g4_g5.py:190:    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:2952:ui/backend/tests/test_comparator_gates_g3_g4_g5.py:208:    violations = cg.check_all_gates(log_path=_REAL_BFS_LOG, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:2977:scripts/phase5_audit_run.py:409:                U_ref=u_ref,
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:2989:src/comparator_gates.py:278:                    f"({threshold:.6g}, U_ref={U_ref}). This indicates "
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:3598:   278	                    f"({threshold:.6g}, U_ref={U_ref}). This indicates "
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:3657:   292	def _audit_fixture_doc(
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:3774:   409	                U_ref=u_ref,
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:3885:    86	    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:3899:   100	    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:3907:   108	    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:3918:   119	    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:3933:   134	    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:3943:   144	    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:3954:   155	    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:3964:   165	    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:3980:   181	    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:3989:   190	    violations = cg.check_all_gates(log_path=log, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:4007:   208	    violations = cg.check_all_gates(log_path=_REAL_BFS_LOG, vtk_dir=None, U_ref=1.0)
./reports/codex_tool_reports/20260422_dec036b_codex_review.md:4856:src/foam_agent_adapter.py:8283:                emitted = emit_strouhal(case_dir, D=D, U_ref=U_ref)
./reports/codex_tool_reports/2026-04-21_phase7c_tier_c_codex_review_round1.md:4956:   148	def _audit_fixture_doc(
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:1679: def _audit_fixture_doc(
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:2311:   144	def _audit_fixture_doc(
./reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md:2479:   312	    doc = _audit_fixture_doc(

exec
/bin/zsh -lc 'rg -n "WARN marker|warn marker|WARN|default 1.0 m/s|unresolvable" .planning/decisions/2026-04-22_phase8_dec036b_gates_g3_g4_g5.md src/comparator_gates.py scripts/phase5_audit_run.py' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
scripts/phase5_audit_run.py:257:            f"[audit] [WARN] field artifact dir missing, skipping manifest: {artifact_dir}",
scripts/phase5_audit_run.py:265:            f"[audit] [WARN] field artifact dir empty, skipping manifest: {artifact_dir}",
scripts/phase5_audit_run.py:400:                f"[audit] [WARN] attestor failed on {case_id}: {exc!r}",
scripts/phase5_audit_run.py:415:                f"[audit] [WARN] gates failed on {case_id}: {exc!r}", flush=True
.planning/decisions/2026-04-22_phase8_dec036b_gates_g3_g4_g5.md:78:  internal, lid U for LDC, free-stream for external). When unresolvable,
.planning/decisions/2026-04-22_phase8_dec036b_gates_g3_g4_g5.md:79:  default 1.0 m/s and emit a WARN marker.
.planning/decisions/2026-04-22_phase8_dec036b_gates_g3_g4_g5.md:84:- **Decision**: FAIL (not WARN) — a solver that exits 0 with |U| > 100·U_ref
.planning/decisions/2026-04-22_phase8_dec036b_gates_g3_g4_g5.md:126:    unavailable (handled as WARN, not FAIL)."""

exec
/bin/zsh -lc "nl -ba scripts/phase5_audit_run.py | sed -n '548,572p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
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

exec
/bin/zsh -lc 'tail -n 60 reports/phase5_fields/naca0012_airfoil/20260421T142539Z/log.simpleFoam' in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc 'tail -n 80 reports/phase5_fields/impinging_jet/20260421T142307Z/log.buoyantFoam' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
time step continuity errors : sum local = 1.34359e-08, global = 2.90822e-09, cumulative = 0.00154031
DILUPBiCGStab:  Solving for omega, Initial residual = 2.28309e-08, Final residual = 4.04026e-10, No Iterations 1
DILUPBiCGStab:  Solving for k, Initial residual = 7.9043e-07, Final residual = 2.25207e-08, No Iterations 1
ExecutionTime = 9.39555 s  ClockTime = 9 s

Time = 435s

DILUPBiCGStab:  Solving for Ux, Initial residual = 4.5198e-07, Final residual = 9.89073e-09, No Iterations 1
DILUPBiCGStab:  Solving for Uz, Initial residual = 3.38113e-07, Final residual = 5.52609e-09, No Iterations 1
GAMG:  Solving for p, Initial residual = 1.15989e-06, Final residual = 4.81055e-07, No Iterations 1
time step continuity errors : sum local = 1.27545e-08, global = 2.8136e-09, cumulative = 0.00154031
DILUPBiCGStab:  Solving for omega, Initial residual = 2.24434e-08, Final residual = 3.98204e-10, No Iterations 1
DILUPBiCGStab:  Solving for k, Initial residual = 7.638e-07, Final residual = 2.17159e-08, No Iterations 1
ExecutionTime = 9.41173 s  ClockTime = 9 s

Time = 436s

DILUPBiCGStab:  Solving for Ux, Initial residual = 4.40675e-07, Final residual = 9.73877e-09, No Iterations 1
DILUPBiCGStab:  Solving for Uz, Initial residual = 3.27158e-07, Final residual = 5.38684e-09, No Iterations 1
GAMG:  Solving for p, Initial residual = 1.11596e-06, Final residual = 4.58544e-07, No Iterations 1
time step continuity errors : sum local = 1.21577e-08, global = 2.71679e-09, cumulative = 0.00154031
DILUPBiCGStab:  Solving for omega, Initial residual = 2.20692e-08, Final residual = 3.92772e-10, No Iterations 1
DILUPBiCGStab:  Solving for k, Initial residual = 7.38281e-07, Final residual = 2.09355e-08, No Iterations 1
ExecutionTime = 9.42785 s  ClockTime = 9 s

Time = 437s

DILUPBiCGStab:  Solving for Ux, Initial residual = 4.29637e-07, Final residual = 9.58786e-09, No Iterations 1
DILUPBiCGStab:  Solving for Uz, Initial residual = 3.16386e-07, Final residual = 5.24402e-09, No Iterations 1
GAMG:  Solving for p, Initial residual = 1.07373e-06, Final residual = 4.39679e-07, No Iterations 1
time step continuity errors : sum local = 1.16575e-08, global = 2.6209e-09, cumulative = 0.00154031
DILUPBiCGStab:  Solving for omega, Initial residual = 2.17087e-08, Final residual = 3.87324e-10, No Iterations 1
DILUPBiCGStab:  Solving for k, Initial residual = 7.13419e-07, Final residual = 2.01777e-08, No Iterations 1
ExecutionTime = 9.44369 s  ClockTime = 9 s

Time = 438s

DILUPBiCGStab:  Solving for Ux, Initial residual = 4.18839e-07, Final residual = 9.44223e-09, No Iterations 1
DILUPBiCGStab:  Solving for Uz, Initial residual = 3.05951e-07, Final residual = 5.10183e-09, No Iterations 1
GAMG:  Solving for p, Initial residual = 1.03344e-06, Final residual = 4.23826e-07, No Iterations 1
time step continuity errors : sum local = 1.12372e-08, global = 2.52794e-09, cumulative = 0.00154032
DILUPBiCGStab:  Solving for omega, Initial residual = 2.13501e-08, Final residual = 3.81905e-10, No Iterations 1
DILUPBiCGStab:  Solving for k, Initial residual = 6.89179e-07, Final residual = 1.94434e-08, No Iterations 1
ExecutionTime = 9.46003 s  ClockTime = 9 s

Time = 439s

DILUPBiCGStab:  Solving for Ux, Initial residual = 4.08398e-07, Final residual = 9.29459e-09, No Iterations 1
DILUPBiCGStab:  Solving for Uz, Initial residual = 2.95944e-07, Final residual = 4.96388e-09, No Iterations 1
GAMG:  Solving for p, Initial residual = 9.95003e-07, Final residual = 9.95003e-07, No Iterations 0
time step continuity errors : sum local = 2.63812e-08, global = -9.65747e-10, cumulative = 0.00154032
DILUPBiCGStab:  Solving for omega, Initial residual = 2.10842e-08, Final residual = 3.81231e-10, No Iterations 1
DILUPBiCGStab:  Solving for k, Initial residual = 6.65773e-07, Final residual = 1.87314e-08, No Iterations 1
ExecutionTime = 9.47541 s  ClockTime = 9 s


SIMPLE solution converged in 439 iterations

End


 succeeded in 0ms:
Courant Number mean: 2.36616e-07 max: 3.86465e-06
Time = 975s

DILUPBiCGStab:  Solving for Uy, Initial residual = 0.150621, Final residual = 5.35032e-05, No Iterations 1
DILUPBiCGStab:  Solving for h, Initial residual = 0.000887964, Final residual = 4.43215e-06, No Iterations 1
GAMG:  Solving for p_rgh, Initial residual = 0.668501, Final residual = 0.385151, No Iterations 1000
time step continuity errors : sum local = 1.06747e-07, global = 3.46271e-09, cumulative = 2.41265e-08
GAMG:  Solving for p_rgh, Initial residual = 0.616779, Final residual = 0.38122, No Iterations 1000
time step continuity errors : sum local = 1.06146e-07, global = 2.88007e-09, cumulative = 2.70065e-08
DILUPBiCGStab:  Solving for epsilon, Initial residual = 9.67706e-05, Final residual = 4.72006e-08, No Iterations 1
DILUPBiCGStab:  Solving for k, Initial residual = 0.00442936, Final residual = 2.70549e-06, No Iterations 1
ExecutionTime = 137.374 s  ClockTime = 138 s

Courant Number mean: 3.12941e-07 max: 4.20564e-06
Time = 980s

DILUPBiCGStab:  Solving for Uy, Initial residual = 0.339311, Final residual = 0.00318735, No Iterations 1
DILUPBiCGStab:  Solving for h, Initial residual = 0.000866353, Final residual = 3.55726e-06, No Iterations 1
GAMG:  Solving for p_rgh, Initial residual = 0.688022, Final residual = 0.394222, No Iterations 1000
time step continuity errors : sum local = 1.0364e-07, global = 4.2822e-09, cumulative = 3.12887e-08
GAMG:  Solving for p_rgh, Initial residual = 0.634429, Final residual = 0.424925, No Iterations 1000
time step continuity errors : sum local = 1.06298e-07, global = 4.93117e-09, cumulative = 3.62199e-08
DILUPBiCGStab:  Solving for epsilon, Initial residual = 9.37398e-05, Final residual = 3.98377e-08, No Iterations 1
DILUPBiCGStab:  Solving for k, Initial residual = 0.00437663, Final residual = 2.35161e-06, No Iterations 1
ExecutionTime = 138.07 s  ClockTime = 139 s

Courant Number mean: 2.48331e-07 max: 4.11106e-06
Time = 985s

DILUPBiCGStab:  Solving for Uy, Initial residual = 0.176444, Final residual = 5.45188e-05, No Iterations 1
DILUPBiCGStab:  Solving for h, Initial residual = 0.000859613, Final residual = 2.93847e-06, No Iterations 1
GAMG:  Solving for p_rgh, Initial residual = 0.680301, Final residual = 0.41528, No Iterations 1000
time step continuity errors : sum local = 1.05114e-07, global = 1.60583e-09, cumulative = 3.78257e-08
GAMG:  Solving for p_rgh, Initial residual = 0.603709, Final residual = 0.390799, No Iterations 1000
time step continuity errors : sum local = 1.05045e-07, global = 1.97057e-09, cumulative = 3.97963e-08
DILUPBiCGStab:  Solving for epsilon, Initial residual = 9.15795e-05, Final residual = 3.30944e-08, No Iterations 1
DILUPBiCGStab:  Solving for k, Initial residual = 0.00434463, Final residual = 2.00103e-06, No Iterations 1
ExecutionTime = 138.767 s  ClockTime = 140 s

Courant Number mean: 3.84908e-07 max: 5.23623e-06
Time = 990s

DILUPBiCGStab:  Solving for Uy, Initial residual = 0.283097, Final residual = 0.00236322, No Iterations 1
DILUPBiCGStab:  Solving for h, Initial residual = 0.000854427, Final residual = 2.49358e-06, No Iterations 1
GAMG:  Solving for p_rgh, Initial residual = 0.63835, Final residual = 0.370794, No Iterations 1000
time step continuity errors : sum local = 1.05667e-07, global = 4.4101e-09, cumulative = 4.42064e-08
GAMG:  Solving for p_rgh, Initial residual = 0.595911, Final residual = 0.378764, No Iterations 1000
time step continuity errors : sum local = 1.06455e-07, global = 5.26275e-09, cumulative = 4.94692e-08
DILUPBiCGStab:  Solving for epsilon, Initial residual = 8.86205e-05, Final residual = 2.79437e-08, No Iterations 1
DILUPBiCGStab:  Solving for k, Initial residual = 0.00431282, Final residual = 1.71443e-06, No Iterations 1
ExecutionTime = 139.471 s  ClockTime = 140 s

Courant Number mean: 2.27168e-07 max: 4.54917e-06
Time = 995s

DILUPBiCGStab:  Solving for Uy, Initial residual = 0.134741, Final residual = 3.73504e-05, No Iterations 1
DILUPBiCGStab:  Solving for h, Initial residual = 0.000849805, Final residual = 2.17062e-06, No Iterations 1
GAMG:  Solving for p_rgh, Initial residual = 0.647868, Final residual = 0.386576, No Iterations 1000
time step continuity errors : sum local = 1.04242e-07, global = 9.14232e-10, cumulative = 5.03834e-08
GAMG:  Solving for p_rgh, Initial residual = 0.631239, Final residual = 0.421711, No Iterations 1000
time step continuity errors : sum local = 1.04965e-07, global = 2.62427e-09, cumulative = 5.30077e-08
DILUPBiCGStab:  Solving for epsilon, Initial residual = 8.60601e-05, Final residual = 2.49571e-08, No Iterations 1
DILUPBiCGStab:  Solving for k, Initial residual = 0.00430013, Final residual = 1.66888e-06, No Iterations 1
ExecutionTime = 140.173 s  ClockTime = 141 s

Courant Number mean: 2.30013e-07 max: 4.26101e-06
Time = 1000s

DILUPBiCGStab:  Solving for Uy, Initial residual = 0.134968, Final residual = 3.86042e-05, No Iterations 1
DILUPBiCGStab:  Solving for h, Initial residual = 0.000845766, Final residual = 1.93476e-06, No Iterations 1
GAMG:  Solving for p_rgh, Initial residual = 0.675998, Final residual = 0.397685, No Iterations 1000
time step continuity errors : sum local = 1.02979e-07, global = 2.85164e-09, cumulative = 5.58593e-08
GAMG:  Solving for p_rgh, Initial residual = 0.618798, Final residual = 0.411033, No Iterations 1000
time step continuity errors : sum local = 1.06755e-07, global = -5.40012e-10, cumulative = 5.53193e-08
DILUPBiCGStab:  Solving for epsilon, Initial residual = 0.000109324, Final residual = 4.78776e-08, No Iterations 1
DILUPBiCGStab:  Solving for k, Initial residual = 0.00458987, Final residual = 2.67404e-06, No Iterations 1
ExecutionTime = 140.904 s  ClockTime = 142 s

End


exec
/bin/zsh -lc "rg -n \"read_final_velocity_max|synthetic_vtk|VELOCITY_OVERFLOW.*VTK|pyvista\" ui/backend/tests tests src | sed -n '1,200p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
src/comparator_gates.py:4:  * G3 VELOCITY_OVERFLOW  — |U|_max > K * U_ref (K=100 default). VTK-based,
src/comparator_gates.py:194:def read_final_velocity_max(vtk_dir: Path) -> Optional[float]:
src/comparator_gates.py:197:    Uses pyvista when available. Returns None when VTK unavailable,
src/comparator_gates.py:198:    unreadable, or pyvista is not installed — caller treats None as
src/comparator_gates.py:205:        import pyvista as pv
src/comparator_gates.py:263:        u_max = read_final_velocity_max(vtk_dir)
ui/backend/tests/test_comparator_gates_g3_g4_g5.py:150:# G3 — velocity overflow (log-proxy branch; VTK branch gated by pyvista)

exec
/bin/zsh -lc "nl -ba /Users/Zhuanz/.codex/memories/MEMORY.md | sed -n '465,515p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
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
   479	
   480	## Task 2: Open Phase 9 as planning-only and keep solver expansion bounded
   481	
   482	### rollout_summary_files
   483	
   484	- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, Phase 9 kept as planning-only with decision-tree packet))
   485	
   486	### keywords
   487	
   488	- Phase 9 planning-only, PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md, PHASE9_MODEL_ROUTING_BASELINE_PLAN.md, PHASE9_ACTIVATION_REVIEW_PACKET.md, replay_manifest, SU2 CLI Harness Skill, foam_agent_adapter.py
   489	
   490	## Task 3: Stop cleanly at the Opus 4.7 activation gate
   491	
   492	### rollout_summary_files
   493	
   494	- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, handoff prompt prepared instead of silent activation))
   495	
   496	### keywords
   497	
   498	- Opus 4.7 activation review, self-dispatch, planning-only, single-engine OpenFOAM, SU2 reference-only, CFX hold, review packet
   499	
   500	## User preferences
   501	
   502	- when working this repo, the user phrased the boundary as "继续推进开发，直至需要Opus 4.7介入" -> keep executing autonomously until a real gate is reached, then stop with a ready review packet [Task 1][Task 2][Task 3]
   503	- the rollout also showed a preference for explicit gate-aware staging rather than silent activation -> preserve the planning-only vs active distinction clearly in Notion and repo docs [Task 2][Task 3]
   504	
   505	## Reusable knowledge
   506	
   507	- Notion phase/task closure here requires updating both page properties and page body text; one surface alone leaves stale recovery state [Task 1]
   508	- `knowledge/whitelist.yaml` is the active whitelist source; older references to `knowledge/ai_cfd_cold_start_whitelist.yaml` are naming drift to normalize, not a fresh design change [Task 1]
   509	- Phase 9 must start from a bounded decision tree: keep single-engine OpenFOAM, allow reference-only external solver surfaces, or open one bounded proof slice; anything broader still needs review [Task 2]
   510	- The presence of SU2 tooling in skill inventory does not mean runtime support is already widened; `src/foam_agent_adapter.py` remained OpenFOAM-centered in this phase [Task 2]
   511	
   512	## Failures and how to do differently
   513	
   514	- Symptom: Notion and repo disagree on path names or report counts -> cause: contract naming drift and stale evidence -> fix: normalize the names and reconcile evidence instead of assuming one side is fully authoritative [Task 1]
   515	- Symptom: planning work accidentally looks like activation -> cause: Phase 9 docs/task text are not explicit enough about `Planned` vs `Active` -> fix: state planning-only mode in phase page, tasks, dashboard summary, and review packet [Task 2]

  ✓ Load DEC specs, target files, and relevant repo memory context
  ✓ Trace G3, G4, and G5 implementations against stated CFD expectations and edge cases
  ✓ Check phase5 integration, concern typing, fallback/error paths, and tests
  → Summarize verdict with blocker/nit classification and evidence
  ✓ Load DEC specs, target files, and relevant repo memory context
  ✓ Trace G3, G4, and G5 implementations against stated CFD expectations and edge cases
  ✓ Check phase5 integration, concern typing, fallback/error paths, and tests
  ✓ Summarize verdict with blocker/nit classification and evidence
codex
# Codex Review Verdict — DEC-V61-036b

**Verdict**: CHANGES_REQUIRED  
**Self-pass-rate delta**: claude-estimated=0.60 → codex-independent=0.42

## Findings

### Must-fix (blocker)
- [B1] [phase5_audit_run.py:311](/Users/Zhuanz/Desktop/cfd-harness-unified/scripts/phase5_audit_run.py:311), [phase5_audit_run.py:406](/Users/Zhuanz/Desktop/cfd-harness-unified/scripts/phase5_audit_run.py:406), [phase5_audit_run.py:563](/Users/Zhuanz/Desktop/cfd-harness-unified/scripts/phase5_audit_run.py:563) `expected_verdict` is decided before attestor/G3/G4/G5 run, then never recomputed. That means the fixture metadata and CLI summary can still say `PASS` even after hard-fail concerns are appended. Recommended fix: compute the final verdict after all concerns are stamped, ideally via the same contract-status helper the backend uses.
- [B2] [phase5_audit_run.py:298](/Users/Zhuanz/Desktop/cfd-harness-unified/scripts/phase5_audit_run.py:298), [phase5_audit_run.py:409](/Users/Zhuanz/Desktop/cfd-harness-unified/scripts/phase5_audit_run.py:409), [comparator_gates.py:252](/Users/Zhuanz/Desktop/cfd-harness-unified/src/comparator_gates.py:252) G3 never resolves `U_ref` from `task_spec.boundary_conditions`; `run_one()` calls `_audit_fixture_doc()` without passing any `u_ref`, so every case is audited at the default `1.0`. This violates the DEC contract, masks the `within=None` / WARN path entirely, and makes threshold correctness depend on today’s unit-velocity conventions rather than the case definition. Recommended fix: derive `U_ref` per case from the spec before calling `check_all_gates`, and let “unknown” travel as an explicit state instead of silently coercing to `1.0`.
- [B3] [comparator_gates.py:209](/Users/Zhuanz/Desktop/cfd-harness-unified/src/comparator_gates.py:209) `read_final_velocity_max()` does not read the final-time internal field; it scans every `*.vtk` under the tree, includes `allPatches`, and returns the maximum over the whole set. Any earlier spike or boundary-patch artifact can false-fire G3 even if the final internal solution is clean. Recommended fix: identify the latest timestep explicitly and read only the internal-field VTK for that timestep.

### Should-fix (nit)
- [S1] [phase5_audit_run.py:398](/Users/Zhuanz/Desktop/cfd-harness-unified/scripts/phase5_audit_run.py:398), [phase5_audit_run.py:413](/Users/Zhuanz/Desktop/cfd-harness-unified/scripts/phase5_audit_run.py:413), [comparator_gates.py:203](/Users/Zhuanz/Desktop/cfd-harness-unified/src/comparator_gates.py:203), [comparator_gates.py:288](/Users/Zhuanz/Desktop/cfd-harness-unified/src/comparator_gates.py:288) missing-coverage paths only print `[WARN]` to stdout or silently skip. They do not stamp the fixture with a WARN concern even though the DEC says unresolved `U_ref` / VTK-unavailable paths should be visible. This leaves silent false-negative holes, especially for k-omega or laminar cases where “no VTK” means G3 disappears completely.
- [S2] [test_comparator_gates_g3_g4_g5.py:27](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparator_gates_g3_g4_g5.py:27), [test_comparator_gates_g3_g4_g5.py:153](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparator_gates_g3_g4_g5.py:153), [test_comparator_gates_g3_g4_g5.py:200](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparator_gates_g3_g4_g5.py:200) coverage is materially weaker than the DEC claims: LDC “clean” is synthetic, the BFS real-log test is machine-specific and skip-prone, there is no VTK-branch test at all, and no threshold-boundary test like `99·U_ref` pass / `101·U_ref` fail or `U_ref=None` WARN behavior.

### Praise / good patterns
- [comparator_gates.py:145](/Users/Zhuanz/Desktop/cfd-harness-unified/src/comparator_gates.py:145) the parser keeps the last continuity line and the last bounding line per field, which is the right semantics for G4/G5.
- [validation_report.py:558](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/validation_report.py:558) the hard-fail concern set is correctly wired, and nulling `within_tolerance` on hard fail avoids the “FAIL but still within band=yes” UI contradiction.

## CFD physics audit
- G3 correctness: the `K=100` ceiling itself is not the main problem. For current incompressible whitelist cases it is a very loose sanity bound; I would not expect a legitimate NACA0012 run to reach `100·U∞`. The real correctness problems are `U_ref` not being case-derived and the VTK reader not actually using the final internal field.
- G3 epsilon fallback math: the code uses `u ~ epsilon^(1/3)` with implicit `L=1`, which is acceptable only as an order-of-magnitude catastrophe proxy. As implemented, it is not a calibrated velocity reconstruction, and there is no WARN marker when this degraded path is the only path.
- G4 correctness: good. `parse_solver_log()` overwrites per-field bounding stats until EOF, so it does use the last reported `bounding k/epsilon/omega...` line. Laminar cases with no bounding lines skip cleanly.
- G5 correctness: the code reads the last continuity line, not an average. On the real repo artifacts that means BFS clearly fails, and cylinder also clearly fails. The risk is not parser correctness; the risk is threshold aggressiveness for future healthy transient cases because the implementation is not solver-aware.
- LDC regression guard: pass by inspection, but weakly guarded. The real LDC log in `reports/phase5_fields/lid_driven_cavity/.../log.simpleFoam` ends around `sum_local≈1e-6` with no turbulence bounding lines, so G4/G5 should stay clean. The current automated regression, however, uses only the synthetic `_CLEAN_LDC_LOG`.
- Threshold calibration: hardcoded, not config-driven. That is acceptable for this DEC as long as the tests pin the boundaries, but the tests currently do not pin `99·U_ref` vs `101·U_ref`, real LDC, or transient healthy/non-healthy separation.

## Backward-compat concerns
- `expected_verdict` can now drift from the true contract verdict, which is dangerous because `run_one()` prints that stale value as the audit summary.
- G5 is intentionally harsh on the current bad fixtures, but it is not solver-type-aware. In the repo’s own real logs, `circular_cylinder_wake` ends around `sum_local≈0.152`, `cumulative≈15.48`, and `turbulent_flat_plate` ends with `cumulative≈29.0`; both will hard-fail. That matches today’s DEC intent, but it is a risk if a future transient case is expected to pass.
- If VTK is unavailable for k-omega or laminar cases, G3 can silently vanish because the fallback only looks for `epsilon`.

## Recommendation
- Ready for `codex_verdict=APPROVED`: NO
- If NO, what needs to change before approval:
1. Recompute fixture/CLI verdict after attestor + G3/G4/G5 concerns are appended.
2. Plumb real `U_ref` extraction from `TaskSpec.boundary_conditions`, and make the missing-`U_ref` state explicit with a WARN concern.
3. Fix `read_final_velocity_max()` to use only the latest internal-field VTK, then add a direct VTK-path regression test.
4. Strengthen tests with repo-relative real LDC/BFS fixtures and threshold-boundary cases.

Verification note: I attempted to run `ui/backend/tests/test_comparator_gates_g3_g4_g5.py`, but this sandbox has no usable temp directory, so the review is source-and-artifact based rather than pytest-executed.


tokens used
136,277
# Codex Review Verdict — DEC-V61-036b

**Verdict**: CHANGES_REQUIRED  
**Self-pass-rate delta**: claude-estimated=0.60 → codex-independent=0.42

## Findings

### Must-fix (blocker)
- [B1] [phase5_audit_run.py:311](/Users/Zhuanz/Desktop/cfd-harness-unified/scripts/phase5_audit_run.py:311), [phase5_audit_run.py:406](/Users/Zhuanz/Desktop/cfd-harness-unified/scripts/phase5_audit_run.py:406), [phase5_audit_run.py:563](/Users/Zhuanz/Desktop/cfd-harness-unified/scripts/phase5_audit_run.py:563) `expected_verdict` is decided before attestor/G3/G4/G5 run, then never recomputed. That means the fixture metadata and CLI summary can still say `PASS` even after hard-fail concerns are appended. Recommended fix: compute the final verdict after all concerns are stamped, ideally via the same contract-status helper the backend uses.
- [B2] [phase5_audit_run.py:298](/Users/Zhuanz/Desktop/cfd-harness-unified/scripts/phase5_audit_run.py:298), [phase5_audit_run.py:409](/Users/Zhuanz/Desktop/cfd-harness-unified/scripts/phase5_audit_run.py:409), [comparator_gates.py:252](/Users/Zhuanz/Desktop/cfd-harness-unified/src/comparator_gates.py:252) G3 never resolves `U_ref` from `task_spec.boundary_conditions`; `run_one()` calls `_audit_fixture_doc()` without passing any `u_ref`, so every case is audited at the default `1.0`. This violates the DEC contract, masks the `within=None` / WARN path entirely, and makes threshold correctness depend on today’s unit-velocity conventions rather than the case definition. Recommended fix: derive `U_ref` per case from the spec before calling `check_all_gates`, and let “unknown” travel as an explicit state instead of silently coercing to `1.0`.
- [B3] [comparator_gates.py:209](/Users/Zhuanz/Desktop/cfd-harness-unified/src/comparator_gates.py:209) `read_final_velocity_max()` does not read the final-time internal field; it scans every `*.vtk` under the tree, includes `allPatches`, and returns the maximum over the whole set. Any earlier spike or boundary-patch artifact can false-fire G3 even if the final internal solution is clean. Recommended fix: identify the latest timestep explicitly and read only the internal-field VTK for that timestep.

### Should-fix (nit)
- [S1] [phase5_audit_run.py:398](/Users/Zhuanz/Desktop/cfd-harness-unified/scripts/phase5_audit_run.py:398), [phase5_audit_run.py:413](/Users/Zhuanz/Desktop/cfd-harness-unified/scripts/phase5_audit_run.py:413), [comparator_gates.py:203](/Users/Zhuanz/Desktop/cfd-harness-unified/src/comparator_gates.py:203), [comparator_gates.py:288](/Users/Zhuanz/Desktop/cfd-harness-unified/src/comparator_gates.py:288) missing-coverage paths only print `[WARN]` to stdout or silently skip. They do not stamp the fixture with a WARN concern even though the DEC says unresolved `U_ref` / VTK-unavailable paths should be visible. This leaves silent false-negative holes, especially for k-omega or laminar cases where “no VTK” means G3 disappears completely.
- [S2] [test_comparator_gates_g3_g4_g5.py:27](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparator_gates_g3_g4_g5.py:27), [test_comparator_gates_g3_g4_g5.py:153](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparator_gates_g3_g4_g5.py:153), [test_comparator_gates_g3_g4_g5.py:200](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparator_gates_g3_g4_g5.py:200) coverage is materially weaker than the DEC claims: LDC “clean” is synthetic, the BFS real-log test is machine-specific and skip-prone, there is no VTK-branch test at all, and no threshold-boundary test like `99·U_ref` pass / `101·U_ref` fail or `U_ref=None` WARN behavior.

### Praise / good patterns
- [comparator_gates.py:145](/Users/Zhuanz/Desktop/cfd-harness-unified/src/comparator_gates.py:145) the parser keeps the last continuity line and the last bounding line per field, which is the right semantics for G4/G5.
- [validation_report.py:558](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/validation_report.py:558) the hard-fail concern set is correctly wired, and nulling `within_tolerance` on hard fail avoids the “FAIL but still within band=yes” UI contradiction.

## CFD physics audit
- G3 correctness: the `K=100` ceiling itself is not the main problem. For current incompressible whitelist cases it is a very loose sanity bound; I would not expect a legitimate NACA0012 run to reach `100·U∞`. The real correctness problems are `U_ref` not being case-derived and the VTK reader not actually using the final internal field.
- G3 epsilon fallback math: the code uses `u ~ epsilon^(1/3)` with implicit `L=1`, which is acceptable only as an order-of-magnitude catastrophe proxy. As implemented, it is not a calibrated velocity reconstruction, and there is no WARN marker when this degraded path is the only path.
- G4 correctness: good. `parse_solver_log()` overwrites per-field bounding stats until EOF, so it does use the last reported `bounding k/epsilon/omega...` line. Laminar cases with no bounding lines skip cleanly.
- G5 correctness: the code reads the last continuity line, not an average. On the real repo artifacts that means BFS clearly fails, and cylinder also clearly fails. The risk is not parser correctness; the risk is threshold aggressiveness for future healthy transient cases because the implementation is not solver-aware.
- LDC regression guard: pass by inspection, but weakly guarded. The real LDC log in `reports/phase5_fields/lid_driven_cavity/.../log.simpleFoam` ends around `sum_local≈1e-6` with no turbulence bounding lines, so G4/G5 should stay clean. The current automated regression, however, uses only the synthetic `_CLEAN_LDC_LOG`.
- Threshold calibration: hardcoded, not config-driven. That is acceptable for this DEC as long as the tests pin the boundaries, but the tests currently do not pin `99·U_ref` vs `101·U_ref`, real LDC, or transient healthy/non-healthy separation.

## Backward-compat concerns
- `expected_verdict` can now drift from the true contract verdict, which is dangerous because `run_one()` prints that stale value as the audit summary.
- G5 is intentionally harsh on the current bad fixtures, but it is not solver-type-aware. In the repo’s own real logs, `circular_cylinder_wake` ends around `sum_local≈0.152`, `cumulative≈15.48`, and `turbulent_flat_plate` ends with `cumulative≈29.0`; both will hard-fail. That matches today’s DEC intent, but it is a risk if a future transient case is expected to pass.
- If VTK is unavailable for k-omega or laminar cases, G3 can silently vanish because the fallback only looks for `epsilon`.

## Recommendation
- Ready for `codex_verdict=APPROVED`: NO
- If NO, what needs to change before approval:
1. Recompute fixture/CLI verdict after attestor + G3/G4/G5 concerns are appended.
2. Plumb real `U_ref` extraction from `TaskSpec.boundary_conditions`, and make the missing-`U_ref` state explicit with a WARN concern.
3. Fix `read_final_velocity_max()` to use only the latest internal-field VTK, then add a direct VTK-path regression test.
4. Strengthen tests with repo-relative real LDC/BFS fixtures and threshold-boundary cases.

Verification note: I attempted to run `ui/backend/tests/test_comparator_gates_g3_g4_g5.py`, but this sandbox has no usable temp directory, so the review is source-and-artifact based rather than pytest-executed.


