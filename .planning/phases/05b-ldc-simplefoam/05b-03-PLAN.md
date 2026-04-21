---
phase: 05b-ldc-simplefoam
plan: 03
type: execute
wave: 3
depends_on:
  - "05b-01"
  - "05b-02"
files_modified:
  - .planning/decisions/2026-04-21_phase5b_ldc_simplefoam_migration.md
  - .planning/STATE.md
  - .planning/ROADMAP.md
autonomous: false
requirements:
  - CODEX-POST-EDIT-REVIEW
  - DEC-V61-RECORD
  - GIT-ATOMIC-COMMIT

must_haves:
  truths:
    - "Codex post-edit review has been invoked on the Plan 01 + Plan 02 diff and returned a final verdict (APPROVED, or APPROVED after CHANGES_REQUIRED addressed)"
    - "A new DEC file records the Phase 5b LDC simpleFoam migration with autonomous_governance flag set appropriately"
    - "STATE.md is updated to reflect Phase 5b LDC sub-phase complete (2 PASS / 8 FAIL → 3 PASS / 7 FAIL)"
    - "ROADMAP.md Phase 5b entry remains under `## Current` with status updated to 'Sub-phase complete (commit <SHA>); 7 FAIL cases remain' and the Plan checklist marked [x]"
    - "A single atomic commit ships src/, fixtures/, reports/, and decisions/; if SHA backfill is needed, it goes in a NEW follow-up commit (no git amend — CLAUDE.md git safety)"
  artifacts:
    - path: ".planning/decisions/2026-04-21_phase5b_ldc_simplefoam_migration.md"
      provides: "DEC-V61 record for the LDC solver swap"
      contains: "autonomous_governance"
    - path: ".planning/STATE.md"
      provides: "Updated phase position marker"
      contains: "Phase 5b"
  key_links:
    - from: ".planning/decisions/2026-04-21_phase5b_ldc_simplefoam_migration.md"
      to: "git commit SHA for the rewrite"
      via: "frontmatter codex_tool_report_path + linked commit"
      pattern: "codex_tool_report_path|commit:"
    - from: "STATE.md"
      to: "roadmap phase entry"
      via: "explicit position note"
      pattern: "Phase 5b"
---

<objective>
Close **the LDC sub-phase of** Phase 5b by: (1) running Codex post-edit review on the `src/foam_agent_adapter.py` diff (mandatory per RETRO-V61-001 — diff >5 LOC in `src/`); (2) recording a DEC-V61 decision file; (3) updating STATE.md and ROADMAP.md; (4) committing atomically via git. Plan 03 contains a human-verify checkpoint because Codex output may request CHANGES_REQUIRED — Claude cannot autonomously decide whether Codex's critiques are worth addressing before merge vs post-merge.

**Scope clarification (WARNING #7):** Phase 5b is an *umbrella* phase containing 8 per-case sub-phases (LDC + 7 others: BFS, turbulent_flat_plate, duct_flow, impinging_jet, naca0012_airfoil, differential_heated_cavity, rayleigh_benard_convection). This plan closes *only the LDC sub-phase*. The Phase 5b umbrella remains under `## Current` in ROADMAP.md until all 8 sub-phases are done. Status goes to "Sub-phase complete (commit <SHA>); 7 FAIL cases remain", not "COMPLETE".

Purpose: Phase 5b-LDC is the FIRST of 8 per-case sub-phases and establishes the solver-swap pattern. The governance trail (DEC + Codex report + STATE update) must be clean so the remaining 7 sub-phases have an unambiguous template. Per RETRO-V61-001 §"Codex-per-risky-PR baseline", `src/` diff >5 LOC with no `verbatim exception` is a mandatory Codex trigger.

Output:
- Codex review report saved under `reports/codex_tool_reports/`
- `.planning/decisions/2026-04-21_phase5b_ldc_simplefoam_migration.md` DEC file
- Updated `.planning/STATE.md` and `.planning/ROADMAP.md` (Phase 5b stays under Current; LDC sub-phase line marked done)
- One primary git commit covering all Plan 01+02+03 deliverables; optional NEW follow-up commit for SHA backfill (never an amend)
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/05b-ldc-simplefoam/05b-CONTEXT.md
@.planning/phases/05b-ldc-simplefoam/05b-RESEARCH.md
@.planning/phases/05b-ldc-simplefoam/05b-01-PLAN.md
@.planning/phases/05b-ldc-simplefoam/05b-02-PLAN.md
@CLAUDE.md

<interfaces>
Codex invocation pattern (per CLAUDE.md "Codex 账号自动切换"):
```bash
# ALL Codex commands must be prefixed with cx-auto 20 &&
cx-auto 20 && codex exec "Review the Phase 5b src/foam_agent_adapter.py diff for OpenFOAM correctness and physics accuracy. Context: ..." 2>&1
# OR
cx-auto 20 && codex review 2>&1
```

DEC file naming convention (per existing decisions/ directory):
```
.planning/decisions/YYYY-MM-DD_<descriptor>.md
# Example from CONTEXT.md canonical_refs:
# .planning/decisions/2026-04-21_phase6_td028_q4_bfs_closure.md (DEC-V61-028)
```

DEC frontmatter fields the retrospective counter reads:
```yaml
---
decision_id: DEC-V61-NNN   # NEXT available number — check .planning/decisions/ for max
date: 2026-04-21
title: <one-line>
autonomous_governance: true | false
codex_tool_report_path: reports/codex_tool_reports/<filename>   # pointer to the Codex output
self_estimated_pass_rate: <0..100>
notion_sync_status: pending
---
```

Per RETRO-V61-001:
- `autonomous_governance: true` means THIS DEC is a +1 on the counter (arc-size telemetry only, no stop-signal).
- `self_estimated_pass_rate ≤ 70` triggers PRE-merge Codex. Plan 01+02 work is a direct execution of CONTEXT.md's explicit value-level decisions → high confidence (~85-90%). Self-estimate likely >70 → POST-merge Codex acceptable, but since the diff touches 三禁区 #1 (`src/`), we do Codex before the commit ships if self_estimated_pass_rate is uncertain.

Existing DEC numbering (from CONTEXT.md + STATE.md citations):
- DEC-V61-017 verbatim exception example
- DEC-V61-018 honest 60% example
- DEC-V61-028 Phase 5a closure (latest cited)
- Therefore the NEXT DEC should be DEC-V61-029 or higher — verify by listing `.planning/decisions/` and picking max+1.

**Git safety (CLAUDE.md verbatim):**
> "CRITICAL: Always create NEW commits rather than amending, unless the user explicitly requests a git amend. When a pre-commit hook fails, the commit did NOT happen — so --amend would modify the PREVIOUS commit, which may result in destroying work or losing previous changes."

This plan therefore uses a **single-path commit strategy: one primary commit, and (if SHA backfill is needed) a second NEW follow-up commit**. No amend branch is authorized.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Prepare pre-commit state + invoke Codex post-edit review</name>
  <files>reports/codex_tool_reports/2026-04-21_phase5b_ldc_simplefoam.md</files>
  <read_first>
    - CLAUDE.md sections "Codex 账号自动切换" and "v6.1 自主治理规则 · Codex-per-risky-PR baseline"
    - The actual diff to review: run `git diff src/foam_agent_adapter.py` to see exactly what Codex is reviewing
    - Recent Codex reports in `reports/codex_tool_reports/` if that directory exists, to match report format
  </read_first>
  <action>
    Step 1 — Verify Plan 01 + Plan 02 artifacts are in the worktree but NOT yet committed:
    ```
    cd /Users/Zhuanz/Desktop/cfd-harness-unified
    git status --short
    # Expected dirty files:
    #   M src/foam_agent_adapter.py
    #   M ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml
    #   ?? reports/phase5_audit/<new_timestamp>_lid_driven_cavity_raw.json
    git diff --stat src/foam_agent_adapter.py
    ```

    Step 2 — Determine self_estimated_pass_rate. Use this decision tree:
    - Plan 01 values were all from CONTEXT.md `<specifics>` (verbatim-from-context) → high confidence
    - Plan 02 fixture PASSED with comparator → physics validated end-to-end → high confidence
    - BUT: this is the FIRST simpleFoam migration in this repo, and the author is M-2.7 not an OpenFOAM expert → moderate caution
    - Reasonable self-estimate: **80%** (between DEC-V61-017 "obvious verbatim" ~95% and DEC-V61-018 "honest uncertain" 60%)
    - Since 80% > 70%, POST-merge Codex is permitted per RETRO-V61-001 — BUT the prior attempt at Phase 5b was reverted, so this is a second attempt on a known-tricky area; err toward PRE-merge.

    **Decision: PRE-merge Codex review (run before commit).** Record self_estimated_pass_rate=80 in the DEC with rationale "second attempt on reverted area, prudence over speed".

    Step 3 — Ensure Codex output directory exists:
    ```
    mkdir -p reports/codex_tool_reports
    ```

    Step 4 — Invoke Codex with a focused review prompt. The exact command:
    ```
    cx-auto 20 && codex exec "Please review the diff in src/foam_agent_adapter.py for the Phase 5b lid-driven-cavity migration from icoFoam (transient PISO) to simpleFoam (steady-state SIMPLE) on a 129x129 2D pseudo-3D mesh.

    Context:
    - The case is Re=100 LDC matched against Ghia 1982 u_centerline at 5% tolerance.
    - Previous icoFoam at 20x20 FAILed the comparator; previous icoFoam at 129x129 with 30 characteristic times ALSO FAILed (wrong-signed u profile — transient not converged to steady state).
    - This rewrite ships: simpleFoam + SIMPLEC (consistent yes) + GAMG p + bounded limitedLinearV 1 for div(phi,U) + wallDist meshWave + steadyState ddt + 129x129 + frontAndBack empty patch replacing wall3/wall4.
    - The regenerated audit_real_run fixture NOW PASSes comparator against Ghia 1982.

    Specifically check:
    1. fvSchemes correctness for steady incompressible at Re=100 (any missing terms? bounded on the right divs?)
    2. fvSolution SIMPLE vs SIMPLEC + relaxationFactors 0.9/0.3 — appropriate for LDC?
    3. boundary conditions on 0/U and 0/p for frontAndBack empty — consistent with blockMeshDict patch type?
    4. residualControl p 1e-5 / U 1e-5 — realistic target for this mesh + scheme combo?
    5. Any OpenFOAM v10 syntax issues or deprecated dictionary entries?
    6. Any risk that the pattern won't generalize to Phase 5c..5j (BFS, TFP, channel, etc.)?
    7. Is 'endTime 2000' with 'deltaT 1' the right pseudo-transient budget?

    Please produce verdict APPROVED or CHANGES_REQUIRED with numbered Suggested Fix items if the latter." 2>&1 | tee reports/codex_tool_reports/2026-04-21_phase5b_ldc_simplefoam.md
    ```

    Step 5 — Parse Codex output:
    ```
    grep -iE '^verdict|APPROVED|CHANGES_REQUIRED' reports/codex_tool_reports/2026-04-21_phase5b_ldc_simplefoam.md | head -5
    ```

    Step 6 — Hold state for human-verify checkpoint in Task 2.
  </action>
  <verify>
    <automated>test -f /Users/Zhuanz/Desktop/cfd-harness-unified/reports/codex_tool_reports/2026-04-21_phase5b_ldc_simplefoam.md && wc -l /Users/Zhuanz/Desktop/cfd-harness-unified/reports/codex_tool_reports/2026-04-21_phase5b_ldc_simplefoam.md</automated>
  </verify>
  <acceptance_criteria>
    - File `reports/codex_tool_reports/2026-04-21_phase5b_ldc_simplefoam.md` exists
    - File size > 100 bytes (rough sanity — Codex output is always more than a one-liner)
    - The file contains one of: "APPROVED", "CHANGES_REQUIRED", "LGTM", or an explicit verdict statement
    - `git status` still shows `src/foam_agent_adapter.py` and the fixture as UNcommitted (commit comes in Task 3)
  </acceptance_criteria>
  <done>
    Codex review report saved. Verdict known. Ready for human to decide: accept-as-is + commit, or address CHANGES_REQUIRED first.
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 2: Human review of Codex verdict + approve commit or request fix-up</name>
  <what-built>
    - `src/foam_agent_adapter.py` rewrite (Plan 01) — icoFoam → simpleFoam + 129×129 + frontAndBack empty
    - `ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml` regenerated with PASS verdict (Plan 02)
    - `reports/phase5_audit/*_lid_driven_cavity_raw.json` raw capture (Plan 02)
    - `reports/codex_tool_reports/2026-04-21_phase5b_ldc_simplefoam.md` Codex review (Task 1)
  </what-built>
  <how-to-verify>
    1. **Read the Codex report:**
       ```
       cat reports/codex_tool_reports/2026-04-21_phase5b_ldc_simplefoam.md
       ```
       Look for:
       - Verdict: APPROVED / CHANGES_REQUIRED / LGTM
       - Any numbered Suggested Fix items
       - Physics critiques (convergence, scheme choice, URFs)
       - Style critiques (OpenFOAM syntax, deprecations)

    2. **If APPROVED (or LGTM):** Type `approved — commit` to proceed to Task 3 (atomic commit).

    3. **If CHANGES_REQUIRED with minor critiques (≤5 LOC, obvious):** Inspect each Suggested Fix. For each, decide:
       - "Accept + fix now" — the fix is a verbatim exception (RETRO-V61-001 §"Verbatim exception"), will be applied as a new small commit AFTER the main commit. Type `accept-with-fixup — commit`.
       - "Defer to Phase 5c-j retrospective" — note for future, proceed to commit. Type `defer-critiques — commit`.
       - "Require rework before commit" — return to Plan 01, apply fixes. Type `rework — abort`.

    4. **If CHANGES_REQUIRED with major critiques (physics wrong, URFs unsafe, divSchemes inappropriate):** Type `rework — abort`. Orchestrator will re-dispatch Plan 01 with the Codex feedback as revision context.

    5. **Sanity-check PASS fixture:**
       ```
       grep -E 'expected_verdict|comparator_passed|value|measured_at' \
         ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml
       ```
       Confirm `expected_verdict: PASS` + `comparator_passed: true`. If not, something slipped — type `rework — abort`.

    6. **Self_estimated_pass_rate honesty check (RETRO-V61-001):** if Codex returned CHANGES_REQUIRED and your self-estimate was 80%, that is a ~80/20 but not wildly off. If Codex returned APPROVED, the 80% estimate was calibrated.
  </how-to-verify>
  <resume-signal>
    Type one of:
    - `approved — commit` (Codex clean, proceed to atomic commit)
    - `accept-with-fixup — commit` (minor fix-ups to apply AFTER main commit as a NEW follow-up commit — never amend)
    - `defer-critiques — commit` (critiques noted but non-blocking, proceed)
    - `rework — abort` (return to Plan 01 with Codex feedback — Plan 03 halts, orchestrator handles revision)
  </resume-signal>
</task>

<task type="auto" tdd="false">
  <name>Task 3: Record DEC-V61, update STATE.md + ROADMAP.md, atomic git commit</name>
  <files>
    .planning/decisions/2026-04-21_phase5b_ldc_simplefoam_migration.md
    .planning/STATE.md
    .planning/ROADMAP.md
  </files>
  <read_first>
    - .planning/decisions/2026-04-21_phase6_td028_q4_bfs_closure.md (nearest DEC template — match frontmatter structure)
    - .planning/STATE.md (to know what sections need bumping)
    - .planning/ROADMAP.md — the Phase 5b entry (sub-phase status needs update, NOT umbrella status)
  </read_first>
  <action>
    Step 1 — Determine next DEC number:
    ```
    ls .planning/decisions/ | grep -oE 'V61-[0-9]+' | sort -V | tail -5
    # Take max + 1. Expected: DEC-V61-029 (since CONTEXT cites DEC-V61-028 as Phase 5a closure).
    ```
    Use that as `decision_id` below. Denote as DEC-V61-<NEXT>.

    Step 2 — Create DEC file `.planning/decisions/2026-04-21_phase5b_ldc_simplefoam_migration.md`:

    ```markdown
    ---
    decision_id: DEC-V61-<NEXT>
    date: 2026-04-21
    title: "Phase 5b LDC — icoFoam → simpleFoam migration, 129×129 mesh, Ghia 1982 match"
    autonomous_governance: true
    self_estimated_pass_rate: 80
    codex_tool_report_path: reports/codex_tool_reports/2026-04-21_phase5b_ldc_simplefoam.md
    notion_sync_status: pending
    phase: 5b-ldc-simplefoam
    supersedes: []
    superseded_by: []
    related:
      - DEC-V61-028  # Phase 5a real-solver pipeline closure
    ---

    # DEC-V61-<NEXT> — Phase 5b LDC simpleFoam migration

    ## Summary

    The `lid_driven_cavity` case generator in `src/foam_agent_adapter.py` is rewritten from icoFoam (transient PISO) to simpleFoam (steady-state SIMPLE) on a 129×129 2D pseudo-3D mesh with a `frontAndBack` `empty` patch. The regenerated `audit_real_run_measurement.yaml` now PASSes against Ghia 1982 u_centerline at 5% tolerance on all 17 y-points.

    ## Rationale

    Phase 5a shipped a real-solver audit pipeline with baseline 2 PASS / 8 FAIL. LDC was FAIL because:
    - icoFoam is transient; Ghia's reference is asymptotic steady state.
    - A prior Phase 5b attempt (reverted) confirmed that even 30 characteristic times of icoFoam at 129×129 produce a wrong-signed, monotonically-decreasing u profile — the transient has not reached the vortex attractor.
    - simpleFoam converges to steady state in <2000 SIMPLE iterations (~30-90 s wall time) on a 129×129 mesh.

    Solver swap is mandatory; this DEC records the concrete implementation choices.

    ## Concrete changes

    1. `src/foam_agent_adapter.py::_generate_lid_driven_cavity`:
       - controlDict: `application icoFoam` → `simpleFoam`; endTime 10 → 2000; deltaT 0.005 → 1.
       - fvSchemes: `ddtSchemes default Euler` → `steadyState`; div(phi,U) → `bounded Gauss limitedLinearV 1`; add div((nuEff*dev2(T(grad(U))))) Gauss linear; add wallDist meshWave, interpolationSchemes, snGradSchemes.
       - fvSolution: `PISO { nCorrectors 2 }` → `SIMPLE { consistent yes; residualControl p/U 1e-5 }`; p solver PCG+DIC → GAMG+GaussSeidel; add relaxationFactors U=0.9 p=0.3.
       - 0/U + 0/p: remove wall3/wall4 entries; add frontAndBack { type empty }.
    2. `src/foam_agent_adapter.py::_render_block_mesh_dict`:
       - Block cell count (20 20 1) → (129 129 1).
       - Remove wall3 and wall4 patch declarations; add frontAndBack patch of type empty covering both z-face quads.

    ## Validation evidence

    - `audit_real_run_measurement.yaml`: `expected_verdict: PASS`, `comparator_passed: true`, commit_sha=<FILL FROM git rev-parse --short HEAD AFTER COMMIT>.
    - Backend pytest: 79/79 green (ui/backend/tests/).
    - Frontend tsc --noEmit: clean.
    - Codex post-edit review: <FILL: APPROVED | APPROVED-with-fixup | …> — see codex_tool_report_path.
    - Raw solver capture: reports/phase5_audit/<TIMESTAMP>_lid_driven_cavity_raw.json.

    ## Autonomous governance

    - `autonomous_governance: true` — counts as +1 on v6.1 counter (telemetry only; no stop signal per RETRO-V61-001).
    - Codex pre-merge review invoked (self_estimated_pass_rate=80, which is >70 threshold but prudent given prior reverted attempt on this same area).

    ## Scope note

    This is the first of 8 Phase 5b per-case sub-phases. The remaining 7 (BFS, turbulent_flat_plate, duct_flow, impinging_jet, naca0012_airfoil, differential_heated_cavity, rayleigh_benard_convection) will reuse this simpleFoam + frontAndBack-empty pattern where applicable; NACA + TFP + BFS additionally need a turbulence model, which will be separate DECs.

    ## Non-goals (deferred)

    - Generalization of simpleFoam emission into a helper function — left inline per CONTEXT.md §"Claude's Discretion".
    - Second-order scheme upgrades (current `limitedLinearV 1` is 2nd-order-bounded; higher-order left for future).
    - Automated byte-reproducibility that actually re-runs solver (still schema-only per RESEARCH.md R4).
    ```

    Replace all `<NEXT>` tokens with the determined DEC number.

    Step 3 — Update `.planning/STATE.md`. Read current content, then add a dated bullet or update the phase-position marker. Concrete edit pattern (use Edit tool):
    - Locate any "Current phase" or "Active work" section.
    - Add line: `- Phase 5b LDC sub-phase: COMPLETE (commit SHA TBD). 3 PASS / 7 FAIL baseline. DEC-V61-<NEXT>. Phase 5b umbrella remains active (7 sub-phases to go).`
    - If STATE.md has no such section (unlikely), append at the end under a new `## 2026-04-21 Phase 5b LDC sub-phase closure` heading.

    Step 4 — Update `.planning/ROADMAP.md` Phase 5b entry (WARNING #7 fix — keep under `## Current`, do NOT move to `## Completed`):

    The Phase 5b umbrella has 8 sub-phases; only LDC is done after this plan. Therefore:
    - **Keep Phase 5b under `## Current`.** Do NOT move to `## Completed`.
    - Change the `- Status:` line from `- Status: Planning` to:
      ```
      - Status: Sub-phase complete (commit <FILL_SHA>); next LDC sub-phase done, 7 FAIL cases remain (BFS, TFP, duct_flow, impinging_jet, NACA0012, DHC, RBC)
      ```
    - Leave Goal, Upstream, Required outputs, Non-goals, Constraints unchanged — they are historically accurate.
    - Update the Plans checklist: mark `05b-01-PLAN.md`, `05b-02-PLAN.md`, `05b-03-PLAN.md` entries with `[x]` (from `[ ]`).
    - Add a note line at end of the entry:
      ```
      - LDC outcome: PASS against Ghia 1982 u_centerline on all 17 y-points (commit <FILL_SHA>). Established simpleFoam+frontAndBack-empty pattern for Phase 5c..5j. See DEC-V61-<NEXT>.
      ```

    Step 5 — Atomic git commit. Stage exactly these files (explicit list, NOT `git add -A`):
    ```
    git add \
      src/foam_agent_adapter.py \
      ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml \
      reports/phase5_audit/*_lid_driven_cavity_raw.json \
      reports/codex_tool_reports/2026-04-21_phase5b_ldc_simplefoam.md \
      .planning/decisions/2026-04-21_phase5b_ldc_simplefoam_migration.md \
      .planning/STATE.md \
      .planning/ROADMAP.md \
      .planning/phases/05b-ldc-simplefoam/
    ```

    Commit message (use HEREDOC):
    ```
    git commit -m "$(cat <<'EOF'
    feat(phase5b): LDC simpleFoam migration + Ghia 1982 PASS

    Rewrite _generate_lid_driven_cavity and _render_block_mesh_dict in
    src/foam_agent_adapter.py to emit a simpleFoam (steady-state SIMPLE)
    case on a 129x129 2D pseudo-3D mesh with frontAndBack empty patch,
    replacing the prior icoFoam (transient PISO) + 20x20 mesh. Regenerate
    audit_real_run fixture; comparator now PASSes against Ghia 1982
    u_centerline at 5% tolerance.

    Prior Phase 5b attempt (reverted) confirmed icoFoam at 129x129 does
    not converge to steady state within viable wall-time budget. simpleFoam
    reaches residuals 1e-5 in ~30-90 s on this mesh.

    First of 8 per-case Phase 5b sub-phases. Establishes the
    simpleFoam + frontAndBack-empty pattern for BFS, TFP, duct_flow,
    impinging_jet, NACA0012, DHC, RBC.

    DEC-V61-<NEXT>
    Codex review: reports/codex_tool_reports/2026-04-21_phase5b_ldc_simplefoam.md
    autonomous_governance: true (counter +1)

    Closes: Phase 5b LDC sub-phase (7 sub-phases remain in Phase 5b)

    Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
    EOF
    )"
    ```
    Replace `<NEXT>` token.

    Step 6 — SHA backfill (WARNING #8 fix — single path, **NEW follow-up commit, no amend**):

    Per CLAUDE.md git safety protocol: "Always create NEW commits rather than amending, unless the user explicitly requests a git amend." This plan does NOT authorize amending under any resume-signal. Even `accept-with-fixup — commit` from Task 2 means NEW follow-up commit(s), not amend.

    The primary commit above was created with literal `<FILL_SHA>` placeholders still in the DEC, STATE.md, and ROADMAP.md. Backfill them with the actual SHA in a second NEW commit:

    ```
    SHA=$(git rev-parse --short HEAD)
    # Edit the DEC file: replace "commit SHA TBD" and "<FILL_SHA>" with $SHA (use sed -i)
    sed -i '' "s/<FILL_SHA>/$SHA/g" .planning/decisions/2026-04-21_phase5b_ldc_simplefoam_migration.md
    sed -i '' "s/<FILL_SHA>/$SHA/g" .planning/ROADMAP.md
    sed -i '' "s/commit SHA TBD/commit $SHA/g" .planning/STATE.md

    git add .planning/decisions/2026-04-21_phase5b_ldc_simplefoam_migration.md .planning/STATE.md .planning/ROADMAP.md
    git commit -m "docs(phase5b): backfill commit SHA $SHA in DEC/STATE/ROADMAP

    Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
    ```

    **No amend branch. No `git commit --amend` anywhere in this plan.** If SHA backfill fails (sed miss, file drift), investigate manually — do not attempt to rewrite the primary commit.

    Step 7 — Final status check:
    ```
    git log --oneline -5
    git status
    # should show clean worktree
    ```
  </action>
  <verify>
    <automated>cd /Users/Zhuanz/Desktop/cfd-harness-unified && git log --oneline -3 | grep -i 'phase5b' && test -f .planning/decisions/2026-04-21_phase5b_ldc_simplefoam_migration.md && grep -E 'decision_id: DEC-V61-' .planning/decisions/2026-04-21_phase5b_ldc_simplefoam_migration.md && grep -iE 'phase 5b' .planning/ROADMAP.md | grep -iE 'sub-phase complete|LDC outcome'</automated>
  </verify>
  <acceptance_criteria>
    - File `.planning/decisions/2026-04-21_phase5b_ldc_simplefoam_migration.md` exists with `decision_id: DEC-V61-<N>` in frontmatter where N is the next sequential number
    - File contains `autonomous_governance: true` and `codex_tool_report_path:` pointing to the Task 1 Codex file
    - `.planning/STATE.md` mentions "Phase 5b LDC sub-phase" and "COMPLETE" (or equivalent marker)
    - `.planning/ROADMAP.md` Phase 5b entry is **still under `## Current`** (not moved to `## Completed`); status line updated to "Sub-phase complete" / "LDC outcome: PASS" content; plan checklist entries marked `[x]`
    - `git log --oneline -3` shows at least one commit with "phase5b" or "Phase 5b" in the subject
    - `git status` shows a clean worktree (all Plan 01/02/03 artifacts committed; optional second SHA-backfill commit also committed)
    - No use of `git commit --amend` anywhere in the executor's command history for this task (verifiable: reflog should not show amend)
    - The verify block above exits 0
  </acceptance_criteria>
  <done>
    DEC recorded. STATE.md and ROADMAP.md reflect sub-phase completion (umbrella Phase 5b still active under `## Current`). Atomic commit shipped plus optional NEW follow-up SHA-backfill commit (never amend). Worktree clean. Phase 5b LDC sub-phase officially closed; 7 more sub-phases queued.
  </done>
</task>

</tasks>

<verification>
1. Codex review report exists at `reports/codex_tool_reports/2026-04-21_phase5b_ldc_simplefoam.md`.
2. Human checkpoint in Task 2 captured and verdict resolved.
3. DEC file in `.planning/decisions/` records the migration with correct frontmatter.
4. STATE.md + ROADMAP.md updated to reflect Phase 5b LDC **sub-phase** complete; Phase 5b umbrella remains under `## Current`.
5. Git worktree clean; main commit includes all Plan 01+02+03 artifacts; optional second commit for SHA backfill — both are NEW commits, no amend.
6. Subsequent Phase 5c onward can reference this pattern and this DEC.
</verification>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| autonomous-governance telemetry → counter integrity | DEC file's `autonomous_governance: true` flag increments the v6.1 counter; mis-flagged DEC distorts arc-size retrospective. |
| Codex report → audit trail | The Codex report is the third-party-review evidence that backs the "reviewed" claim on this PR. Fabrication or selective editing would compromise the governance model. |
| git history → repudiation surface | Amending commits rewrites history and can destroy work. CLAUDE.md forbids amend without explicit user request. This plan enforces single-path: NEW commits only. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-05b-07 | Tampering | DEC frontmatter `self_estimated_pass_rate` | mitigate | Value (80) recorded with explicit rationale in the DEC body. RETRO-V61-001 penalizes overestimation at next retrospective; honest uncertainty is tracked. |
| T-05b-08 | Repudiation | Could claim Codex was invoked when it wasn't | mitigate | `codex_tool_report_path` in DEC frontmatter + actual file committed to git. Any reviewer can cat the file and verify content. `cx-auto 20` header in the Codex log proves account-switch was performed. |
| T-05b-09 | Elevation of privilege | A future sub-phase copies this pattern verbatim to a case where simpleFoam is wrong (e.g. transient von Kármán wake) | accept | This DEC explicitly states "Scope note: turbulence + transient-by-nature cases need separate DECs". Pattern-copy without understanding is a process-level risk, not a technical one; addressed by the retrospective cadence. |
| T-05b-10 | Tampering | git history via `--amend` destroying the primary commit | mitigate | Plan 03 explicitly forbids amend anywhere in Task 3 Step 6. Single-path SHA backfill via NEW commit. Verifiable via `git reflog` — no amend entries. |
</threat_model>

<success_criteria>
1. Codex review invoked + report saved.
2. Human checkpoint resolved with explicit resume-signal.
3. DEC file with next sequential V61 number + correct autonomous_governance flag + codex_tool_report_path pointer.
4. STATE.md reflects Phase 5b LDC sub-phase completion.
5. ROADMAP.md Phase 5b stays under `## Current`; sub-phase status updated; plan checklist entries `[x]`; LDC outcome line added.
6. At least one atomic commit covering src/, fixture, raw capture, Codex report, DEC, STATE, ROADMAP, and phase directory. Optional second commit for SHA backfill.
7. No `git commit --amend` used.
8. Commit message references the DEC id + autonomous_governance status.
</success_criteria>

<output>
After completion, create `.planning/phases/05b-ldc-simplefoam/05b-03-SUMMARY.md` documenting:
- Codex verdict (APPROVED / APPROVED-with-fixup / etc.)
- DEC id allocated (DEC-V61-NNN)
- Commit SHA(s) (primary + optional NEW SHA-backfill follow-up — confirm no amend used)
- Self_estimated_pass_rate with retrospective calibration note
- autonomous_governance counter impact (+1)
- Any Codex critiques deferred to future sub-phases with pointers
- Confirmation that Phase 5b **LDC sub-phase** is closed; Phase 5b umbrella still has 7 sub-phases remaining; next up is Phase 5c (another FAIL case, likely BFS)
</output>
</content>
</invoke>