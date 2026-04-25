---
retro_id: RETRO-V61-059
title: DEC-V61-059 plane_channel_flow Type II multi-dim · 4-round Codex Stage A + Stage B sub-arc + 3 post-R3 defects
date: 2026-04-25
trigger: post-R3 live-run defect (per RETRO-V61-053 addendum protocol)
related_dec: DEC-V61-059
counter_at_retro: 41 (after V61-059 lands)
related_retros:
  - RETRO-V61-053 (cylinder · same OpenFOAM-version-emitter API drift class · counter 40)
  - RETRO-V61-001 (Codex-per-risky-PR baseline · counter 16)
---

## Incident summary

DEC-V61-059 is the third Type II case to land under methodology v2.0
(after V61-052 BFS and V61-057 DHC pre-stage close). The arc took
**4 Codex rounds** to clean-close Stage A, then surfaced 3 post-R3
runtime-emergent defects at Stage B execution and required a
**2-round Stage B sub-arc** to clean-close those plus their fall-out.

Codex round outcomes:

| Round | Stage | Verdict | Findings |
|-------|-------|---------|----------|
| Plan (Stage 0) | intake | reviewed inline | self-estimated 0.40 round-1 pass rate |
| R1 (post-A.1-A.6) | Stage A | CHANGES_REQUIRED | F1 (P2 bc-stamp trust), F2 (P2 hyphen normalize) |
| R2 (post-R1) | Stage A | CHANGES_REQUIRED | F3 (**P1** verdict-engine wiring TOOTHLESS), F4 (P2 SNR floor) |
| R3 (post-R2) | Stage A | CHANGES_REQUIRED | F5 (P2 log-law band over-tight), F6 (P3 driver guard) |
| R4 (post-R3) | Stage A | **CLEAN APPROVE** | 0 |
| **R5 (Stage B sub-arc r1)** | **post-Stage-B** | **CHANGES_REQUIRED** | **F7 (P2 reader field-aware), F8 (P2 stale downstream consumers)** |
| **R6 (Stage B sub-arc r2)** | **post-sub-arc-r1** | **APPROVE_WITH_COMMENTS** | F9 (P3 coexistence test), F10 (P3 log-name order alignment) |

Final: **19 commits** in the DEC arc, F1-M2-clean on Stage A,
APPROVE_WITH_COMMENTS on Stage B sub-arc.

## Hidden defects caught post-R3 (RETRO-V61-053 addendum class)

After Codex round 4 returned CLEAN APPROVE on Stage A, Stage B's
live OpenFOAM run on commit `fb2ea78` crashed at simulated 4.6s
with `FOAM FATAL ERROR: Unable to find turbulence model in the
database` from inside the wallShearStress function-object. Three
distinct defects, all variants of the same class —
**OpenFOAM-version-emitter API drift**:

| # | Commit | Defect | Why static review missed it |
|---|--------|--------|-----------------------------|
| 1 | `a71e8ec` | `constant/turbulenceProperties` → `constant/momentumTransport` (OF10 incompressible rename) | The file was emitted; only running the FO surfaces the registry-lookup mismatch |
| 2 | `4af21a2` | `icoFoam` → `pisoFoam` swap (icoFoam is hard-coded laminar PISO that does NOT register a momentumTransportModel; pisoFoam does) | Code paths exercise file generation, not the OF runtime registry |
| 3 | `42158e2` | `<set_name>_<field>.xy` → `<set_name>.xy` (OF10 sets-FO writes one packed file with all components) | Reader looked at the legacy filename; OF10 file was right there but undetected |

A 4th commit (`59198cf`) was a runtime-budget tuning regression —
the original `endTime=50, deltaT=0.002` burned 3-hour wall-clock on
flow that had converged at simulated t≈1.5s. Reduced to
`endTime=5, deltaT=0.05`, p-solver PCG/DIC → GAMG/GaussSeidel; per-
run wall now ~9 minutes. Not a correctness defect but would have
made batch Stage B unworkable.

## Stage B sub-arc (Codex rounds 5-6) findings

The post-R3 fix stack itself introduced 2 P2 static-review defects
that Codex caught in round 5:

- **F7** (`src/plane_channel_uplus_emitter.py:177-180`): the
  OF10-first reader silently returned packed-`U` data when the
  caller asked for `field="p"`. The OF10 `<set_name>.xy` file
  holds U specifically; reading column 2 as "the requested field"
  is a wrong-field/wrong-column read.
- **F8** (3 downstream consumers): `scripts/render_case_report.py`,
  `src/metrics/residual.py`, `src/audit_package/manifest.py` all
  hard-coded the old solver/file names. Codex empirically verified
  by running probes against the live Stage B artifact dir that
  these consumers returned None / {} on the new pisoFoam-only +
  momentumTransport-only artifact tree.

Codex empirically validating findings against the live artifact
tree is the **dynamic-vs-static frontier RETRO-V61-053 §10
introduced** as the load-bearing methodology lesson. F8 would have
been very hard to catch by static review alone.

Round 6 added two P3 nits explicitly classified as "post-smoke
hardening rather than closure blockers":

- **F9**: round-5's exact bug class was a coexistence (both files
  in the same dir) precedence issue. Round 5's regressions tested
  the failure modes separately but not the coexistence case. Added
  one coexistence test.
- **F10**: the 3 downstream consumers' log-name preference orders
  diverged. Aligned all three to the canonical order
  `simpleFoam → icoFoam → pisoFoam → pimpleFoam → buoyantFoam → ...`.

## What went right

1. **Cross-session coordination via standalone PR**. The G2
   detector was opened as PR #38 on the standalone branch
   `fix-comparator-g2-uplus-yplus` so SESSION 1 (V61-057) and
   SESSION 2 (V61-058) could rebase on a coherent G2 base without
   inheriting V61-059's adapter/extractor changes. PR #38 was
   backported with G2-only round-2/round-3 hardening (F3+F5+F6) so
   the cross-session base stays clean.

2. **F3 was the deepest finding of the entire arc** and was caught
   because Codex re-reads the verdict-engine wiring on every round.
   The original A.1 commit added the G2 detector and the gate test
   suite, but missed adding `CANONICAL_BAND_SHORTCUT_LAMINAR_DNS`
   to `_HARD_FAIL_CONCERNS` in `validation_report.py:601-608`. That
   meant the gate could fire and STILL not change the verdict —
   the entire DEC thesis was toothless. This is exactly the kind of
   cross-plane wiring gap that round-by-round review catches and
   single-round review would miss.

3. **Stage B sub-arc clean-close on round 2**. The 2-round
   sub-arc kept the methodology rule "post-R3 defects re-open the
   review surface" honest without requiring a budget-blowout
   abandon. Sub-arc round 2 = APPROVE_WITH_COMMENTS, fully closed.

4. **Honest Stage B FAIL verdict**. The plane-channel Stage B run
   completed with `solver_success: true` and 3 deviations vs Moser/
   Kim DNS gold (laminar profile far below turbulent reference).
   G2 stays silent (correct: profile far outside canonical band).
   The FAIL is physics-honest, not pipeline bug. This is the
   intended outcome of running the laminar A.4.a path against a
   turbulent reference; A.4.b/A.5.b will land the kOmegaSST RANS
   path that closes the physics gap.

## What went wrong (lessons)

1. **`openfoam_version_emitter_api_drift` should have been HIGH in
   intake §6**. The intake had `executable_smoke_test` and
   `solver_stability_on_novel_geometry` from RETRO-V61-053
   addendum, but neither named the OpenFOAM-minor-version output
   API class explicitly. All 3 hits would have been predicted by a
   `openfoam_version_emitter_api_drift` flag. The RETRO-V61-053
   action-items list now includes this as a HIGH risk_flag for
   any case that depends on OpenFOAM-generated auxiliary files,
   registry objects, or function-object outputs.

2. **Stage B runtime budget should be checked at intake time**.
   The 3-hour wall-clock on the original `endTime=50, deltaT=0.002`
   pair would have made Stage B unworkable; we caught it
   empirically only when the smoke test exposed it. Future intake
   should require a Stage-B-feasibility back-of-envelope check
   (cells × timesteps × seconds-per-iter < N-hour wall budget).

3. **Multi-consumer log-name discovery (F8/F10) is structural
   debt**. Three places hard-coded log-name whitelists that
   diverged. Long-term fix: extract a shared `FOAM_SOLVER_LOG_NAMES`
   tuple to a common module. Done in-place alignment for V61-059;
   centralization queued for a follow-up DEC.

## Counter status

`autonomous_governance_counter_v61`: **41** after DEC-V61-059
lands. Up from 40 (V61-053 close). Well under any soft-review
threshold. V61-059 is autonomous_governance: true (no external
gate) and counts.

Stage B sub-arc rounds 5-6 do not bump the counter further — the
sub-arc is treated as a continuation of the V61-059 DEC, not a
new DEC.

## Cross-refs

- DEC file: `.planning/decisions/2026-04-25_cfd_plane_channel_multidim_dec059.md`
- Intake: `.planning/intake/DEC-V61-059_plane_channel_flow.yaml`
- Codex logs:
  - Stage A: `reports/codex_tool_reports/dec_v61_059_plan_review_round{1,2,3,4}.md`
  - Stage B sub-arc: `reports/codex_tool_reports/dec_v61_059_round{5,6}.md`
- Live-run logs:
  `reports/phase5_audit/dec_v61_059_stage_b_live_run_v{4,5}.log`
  (v5 = clean Stage B run on commit `42158e2`)
- Methodology: Notion page §10 (static vs dynamic review,
  RETRO-V61-053 addendum)

## Action items

1. **Update `.planning/intake/TEMPLATE.yaml`** to include
   `openfoam_version_emitter_api_drift` as a HIGH risk_flag with
   the V61-059 evidence cited (3 distinct hits in one DEC).
2. **Centralize `FOAM_SOLVER_LOG_NAMES`** in a future doc-debt DEC
   so the F10 alignment doesn't drift again.
3. **Stage A.4.b + A.5.b deferred work** (kOmegaSST RANS path +
   gold YAML observables[] regen at Re_τ=395) remains queued.
   When it lands, it re-opens the Codex review surface as a new
   sub-arc per intake §7 batch-A.5 note.

This retro is doc-only; no counter tick.
