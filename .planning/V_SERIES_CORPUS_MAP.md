# V-Series Corpus Map

> Companion to `DEMO.md` and `CHANGELOG_MILESTONE_2026-05-22.md`.
> SSOT: `.planning/methodology/industrial_case_solver_findings.md` (85+ V-rows, V1..V84+).
> One-page map of what the engine's advisor surface "knows about."

---

## What the V-series IS

The V-series is the **engineer-facing solver / mesh internal failure-mode catalog** that accumulates whenever a real CFD case (case_002+) surfaces an OpenFOAM-internal or mesh-internal failure. Each V-row is one canonical failure pattern: symptom + case-of-origin + root cause + fix-class + cross-case witness count. The corpus is append-only; nothing is removed once it lands. As of 2026-05-22 it spans V1..V84+ across cases 002 (CHT/buoyancy/multi-region) through 091 (NACA airfoil arcs).

V-series is explicitly **distinct from the F-series**. F-series tracks workbench REST API / persona-driven surface defects (HTTP routes, OpenAPI descriptors, persona prompt misfires). V-series tracks solver-internal physics. The two are non-overlapping by construction — F-series asks "would this happen with no LLM in the loop?" If yes, it's V-series. The split lets the advisor reason about CFD failure modes without polluting the surface gripes channel.

---

## Coverage map · which solver classes the corpus has witnessed

| Solver class | V-rows | Representative cases | Status |
|---|---|---|---|
| **Compressible buoyant CHT** (rhoSimpleFoam / buoyantSimpleFoam + CHT) | V3-V16 (≈14 rows) | case_002a / case_002b APU bay | closed / playbook (V12, V13) |
| **STEP CAD ingest** | V1, V2, V16 | case_002a, case_003 CRM-HLS | closed / partial |
| **Compressible-RANS pseudo-steady mass imbalance** | V18+ | case_005 RAE M2129 | partial |
| **Turbulent RANS flat plate** | V20+ rows | case_021 NASA TMR, case_032 flat_plate | partial |
| **Backward-facing step (BFS)** | V64-class | case_022 Driver-Seegmiller | LANDED via DEC-V65 |
| **NACA airfoil separation** | V101..V104 | case_029 NACA stall + case_022 BFS (2-case witness) | LANDED |
| **Industrial multi-solid ventilation** | V60+ | case_028 APU bay v1/v2/v3 (B74/B75 substrates) | LANDED (strong-PARTIAL) |
| **Reacting low-Mach combustion** | V41 (janafThermo bounds), TBD-15..TBD-20 queued | case_009 Sandia Flame D | partial (TBD-17 fence shipped; TBD-15/16/18/19/20 spike or DEC-class queued) |
| **Multiphase VOF** | TBD-1..TBD-4 queued | case_007 KCS ship | queued (vof_contract DEC needed) |
| **Incompressible external LES** | Gap #26-#31 queued | case_010 DrivAer fastback | queued (les_contract DEC needed) |
| **Transonic compressible (density-based)** | Gap #17-#24 queued | case_006 ONERA M6 | queued (compressible_contract DEC needed) |

The "closed / playbook / partial / queued" status field tracks whether the failure mode is (a) live-verified fixed in an industrial case, (b) codified in `solver_convergence_playbook.md` (knowledge IS the fix), (c) mitigated structurally but deferred, or (d) known gap.

---

## Sample V-findings (representative patterns)

A few V-rows to make the catalog concrete — each is a real failure observed in a real case, with a specific fix-class:

- **V3 · kOmegaSST + zero IC → ω blowup → wall NaN** (case_002a, closed). Tag `N-buoy`. The fix is non-zero ω initialization (`omegaWallFunction` requires sensible bulk ω; bare zero IC blows up at wall on iter 1).
- **V5 · DIC / DILU preconditioner SIGFPE on compressible buoyant** (case_002a, closed). Tag `N-buoy`. Switching to `GAMG` for `p_rgh` + `DILUPBiCGStab` for U/h/k/ω sidesteps the SIGFPE; previously the case died at iter 3.
- **V7 · Compressible ρ goes negative → solver explodes** (case_002a, closed). Tag `N-buoy`. Caused by missing `bounded` divSchemes on `phi,U` + missing relaxation on `rho`. Documented in playbook.
- **V10 · sHM ate thin walls; BC writer drops missing patches** (case_002a, V-4x validated). Tag `A1` (advisor seed). The advisor pattern: detect post-sHM patch count delta vs pre-sHM, surface as warning before solver dispatch.
- **V15 · CHT fluid-side limitTemperature clamping** (case_002b, closed). Tag `N-cht`. The V5-class buoyant fix crosses solver families — same SIGFPE root cause manifests differently in CHT (cells at T=±1e+300) and needs `limitTemperature` fvOptions in fluid region.
- **V41 · janafThermo bounds floods log when Tlow > cell T** (case_009 Sandia Flame D). The thermophysical header declares `Tlow=300`; case cold-flow stage has cells at T~294; OpenFOAM emits one warning line per cell per PIMPLE iter, producing GiB of log noise. Mitigation: case-specific Tlow=200 thermo override; **queued** as part of the `reacting_contract` schema extension (TBD-18).
- **TBD-17 · solver_execution gate falsely PASSes when last-iteration residual block is partial** (case_009, self-discovered 2026-05-22). The newest entry. Fix: `_PARTIAL_FINAL_COVERAGE_THRESHOLD = 0.5` (commit `3b5c43f`). See `DOGFOOD_CASE_009.md` §TBD-17 for the full root-cause walk.

The full 85+ row catalog is in `.planning/methodology/industrial_case_solver_findings.md`. Status legend in the catalog header.

---

## How Claude Code session uses V-series AS the advisor

**SSOT for this design choice:** `feedback_claude_code_is_the_advisor.md` (user-level memory, `~/.claude/projects/-Users-Zhuanz/memory/feedback_claude_code_is_the_advisor.md`).

The "AI advisor" surface in cfd-harness-unified is intentionally NOT a separately-deployed RAG service or a workbench-embedded chat panel. The advisor IS a Claude Code session reading the V-series corpus on-demand:

1. **A real CFD case is in trouble.** Engineer is in OpenFOAM, residuals diverging, or a gate is BLOCKING in `cfdtrust audit`.
2. **Claude Code session is invoked** at the cfd-harness-unified working tree. It has `Read` / `Grep` / `Bash` over `.planning/methodology/` and the engine source.
3. **Session greps the V-series** for the case's failure signature (e.g., "p_rgh GAMG", "thin wall", "ω wall NaN", "negative ρ"). Matches surface canonical V-rows that have already been root-caused on a sibling case.
4. **Session reads the matched V-rows + the playbook entry** if one exists. The corpus's append-only history means a 2026-04 fix on case_002a is still in the catalog and still applicable to a 2026-05 reacting case if the failure signature matches.
5. **Session surfaces the canonical fix-class to the engineer** as a death-mode hypothesis — never as a "definitive answer." The advisor is advisory-only per the strategic pivot (see `feedback_cfd_harness_ai_advisor_pivot.md`).

This design rejects three anti-patterns the M6 advisor charter previously contemplated:
- ❌ "Embed a RAG retrieval button in the workbench UI." (Charter draft pivot rejected this — Claude Code session IS the retrieval.)
- ❌ "Train a fine-tuned CFD assistant model." (No model fine-tuning; the V-series corpus + a frontier model IS the system.)
- ❌ "AI writes the manifest / solver dict / case files." (Hard line: AI is GET-only on case state, never write.)

---

## Path to the corpus

- Primary SSOT: `.planning/methodology/industrial_case_solver_findings.md`
- Companion (decision tree, lookup): `.planning/methodology/solver_convergence_playbook.md`
- Strategic pivot SSOT: `~/.claude/projects/-Users-Zhuanz/memory/feedback_cfd_harness_ai_advisor_pivot.md` + `~/.claude/projects/-Users-Zhuanz/memory/feedback_claude_code_is_the_advisor.md`
- Per-case findings reports (dogfood-discovered new entries): `_sandboxes/case_*/case/DOGFOOD_CASE_*.md` + `.planning/dogfood/DOGFOOD_CASE_*.md`
- F-series counterpart (NOT this catalog): `.planning/methodology/workbench_persona_findings.md`
