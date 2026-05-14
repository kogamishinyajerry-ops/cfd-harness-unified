# Track C · Advisor e2e — Session 5 · case_009 Sandia Flame D v1.5 cleanup (reacting low-Mach numerics class promotion)

> **Date**: 2026-05-14
> **Track**: C (Claude Code session as M6 advisor, per `feedback_claude_code_is_the_advisor.md`)
> **Mandate**: M6 charter empirical close — close the V41 channel-(b) gap surfaced by Track C session 4 (V91) and formally promote **reacting low-Mach** to the third e2e numerics class. Session 1 = incompressible-LES (case_010); session 2 = steady-laminar-CHT-multi-stream (case_011); session 3 = incompressible-RANS-MRF (case_004); session 4 = reacting low-Mach **blind audit + V41 falsification**; session 5 = reacting low-Mach **fix-verification + class-3 promotion** on the same root case.
> **Subject case**: `~/Desktop/case_009_sandia_flame_d/v1_5/` (case_009 in 16-case roster · reacting-low-Mach root · Sandia/TUD piloted-jet methane-air flame · DRM-19 19+2 species · PaSR + Cmix=1.0 + kEpsilon)
> **Authored by**: Claude Code Opus 4.7 (1M context)
> **Counter impact**: nil retro-side (B10 sub-DEC `V61-198-sub-case-009-v1-5-cleanup` counter +1 was booked at its commit `2c93e69`; this retro is methodology consolidation, not a new autonomous_governance DEC)

---

## 1. Session goal

Formalize the **case_009 v1.5 cleanup** (commit `2c93e69`) as Track C session 5, with three deliverables:

1. **Promotion act** — register reacting-low-Mach as the third e2e numerics class on the ARC-GOAL #4 ledger. Sessions 1-4 left this slot at `[QUESTIONABLE]` per V91 because v1 production state failed to clear the warning flood. v1.5 production state clears it (0 limit warnings across 2000 timesteps of ignite; Tmax envelope climbs through 1985 K with monotone CO2/H2O/Qdot signal). Class-3 promotion is now substrate-justified.
2. **A10 promotion-gate status evaluation** — session 4 set the gate as "2nd reacting-low-Mach case". v1.5 does not add a 2nd case to the 16-case roster, but it does supply **paired negative-→-positive evidence inside a single case**. Evaluate whether this evidence form is admissible toward A10 extraction.
3. **Sediment-state hygiene** — V91 surfaced V41 sediment as `[VALIDATED]`-but-empirically-false. The B10 sub-DEC amended V41 → `[QUESTIONABLE 2026-05-14]` and added V93 as the actionable rule. Session 5 closes the audit→correction loop and records the methodology lesson (intent-check at sediment time, not surface-check).

Hard constraints from brief (all observed): no edits to `ARC-GOAL.md` (main-session reconcile · B12-race avoidance), no edits to `ui/backend/services/geometry_ingest/` (A10 land deferred), no edits to `case_011/004/010`, no edits to `case_009/v1_5/` external substrate (B10 froze it), no new V-rows (V93 already in B10), corpus-sync hook does not trigger (no methodology file mutation this commit).

## 2. Substrate state delta — v1 → v1.5

Source of truth: `~/Desktop/case_009_sandia_flame_d/v1_5/PATCH_LOG.md` + commit `2c93e69` diff. v1.5 lives in a sibling `v1_5/` directory; the v1 production state remains untouched on disk (V91 evidence preservation).

**Net additions** (v1.5 only):

- `v1_5/scripts/patch_janaf_tlow.py` — argparse CLI, brace-depth-aware top-level species-block parser, writes `.pre_tlow_patch` backup before mutating; lowers `Tlow N;` → `Tlow target;` (default `target=200`) when `N>target`; idempotent. Audit table `(species, old, new)` prints to stdout.
- `v1_5/scripts/parse_log_and_plot.py` — evidence generator (convergence + Tmax-vs-time + species_max).
- `v1_5/case/constant/thermo.compressibleGas` (patched) + `.pre_tlow_patch` (verbatim v1 backup; one-command revert).
- `v1_5/case/system/controlDict` — `startFrom=latestTime` (`t=0.005` cold-flow endpoint), `endTime=0.007` (2 ms ignite window), `writeInterval=0.0001`, `fieldMinMax` functionObject added for T / CH4 / OH / H2O / CO2 / Qdot.
- `v1_5/case/log_ignite_v1_5.txt` (80,439 lines, ~10 MB). **0 limit warnings** (`grep -c "limit:" log_ignite_v1_5.txt` = 0).
- `v1_5/case/0.0051 .. 0.007` write-time snapshots at dt=1e-4 (21 dirs).
- `v1_5/evidence/{convergence.png, Tmax_vs_time.png, species_max.json}`.
- `v1_5/PATCH_LOG.md` — root-cause narrative + change manifest + physical defense for 100 K extrapolation (AR exact / N2 <1% cp error / 11 trace species Y_k≈0).

**Net removals from v1.5 case dir** (vs v1 starting state, after rsync-clone): time dirs `0.001..0.004` (intermediate cold-flow snapshots; storage hygiene) and `0.0055` (corrupted by the v1 limit storm; v1.5 restarts from `0.005` which was the last clean cold-flow endpoint). v1 directory itself untouched on disk.

**Key empirical deltas** (cross-checked vs B10 §5 verification table):

| Check | v1 | v1.5 |
|---|---|---|
| `grep -c "Tlow[[:space:]]\+300" constant/thermo.compressibleGas` | 13 | 0 |
| `grep -c "Tlow[[:space:]]\+200" constant/thermo.compressibleGas` | 40 | 53 |
| limit-warning lines in ignite log | 8,860,176 | 0 |
| ignite physical-time advanced | 593 μs (stalled) | 2000 μs (clean) |
| Tmax envelope at ignite endTime | stuck at pilot floor 1880 K | 1985 K (post-ignition climb) |
| ignite log size | 35 MB (warning flood) | ~10 MB (residuals only) |

Solver still uses the v1 controlDict deltaT=1e-6 (no scheme change). The transition from `[QUESTIONABLE]` to e2e-PASS is **entirely attributable to the per-species Tlow patch** — no fvSchemes, fvSolution, mesh, BC, or turbulenceProperties changes were made. This is the cleanest possible isolation of V93's intervention.

## 3. Death mode — V41 channel-(b) gap

The V41 sediment row (authored 2026-05-08) claimed two outcomes: (a) global header `200.000 1000.000 5000.000` written to therm.dat pre-conversion, (b) "all species now show Tlow 200" in the converted `thermo.compressibleGas`. Session 4 (V91) blind-verified that (b) was empirically false — 13 of 53 species still carried per-species `Tlow 300;` records. The session-4 retro flagged this as **channel-(b) gap**: V41 was authored as if patching channel-(a) implied channel-(b), but **chemkinToFoam carries the two channels independently**.

The mechanism (now load-bearing across the audit chain · re-articulated here from PATCH_LOG.md root-cause + B10 §1 Context):

1. chemkin-II `therm.dat` carries a **global temperature-range header** on line 2 (`G 300.000 1000.000 5000.000`) — the V41 patch target.
2. **Each species record also declares its own range** in the leading line of its 4-line NASA-7 block (e.g., `N2  ... G 300.000 5000.000 1000.000`).
3. chemkinToFoam writes per-species records into `constant/thermo.compressibleGas` **using each species' own record** — the global header is a fallback/default, not an override.
4. janafThermo's runtime limiter checks **per-species** Tlow/Thigh against cell T.
5. Result: a global-header-only patch is **necessary but not sufficient**. Per-species records must also be rewritten — either via pre-conversion sweep of `therm.dat` or post-conversion sweep of `thermo.compressibleGas`. v1.5 takes the post-conversion path (`patch_janaf_tlow.py` operates on the OpenFOAM dict, not chemkin input).

**Death-mode signature for retro catalog**: the sediment author saw `chemkinToFoam exit 0 + cold-flow runs without crashing` and conflated the **non-crash outcome** with the **patch-complete outcome**. Cold-flow ran clean because **cells at T<300 with non-trivial species mass-fractions are confined to the fuel-jet region**, and during cold-flow Y_k chemistry source terms are zero → the limiter still fires but the resulting wall-clock penalty is amortized over the cold mixing transient. Ignite stage is where it bit: chemistry source terms turn on, every PIMPLE inner iter hits the limiter at every fuel-jet cell, and 8.86M warnings in 593 μs is the floor of the cost.

**V41 was authored at the surface check; the intent check was never run.** This is the same family as V83 (mesh_ok permissive verdict), V86 (orphaned .eMesh silent), V90 (sHM cellZones broken-but-accepted), V91 (V-series sediment-status itself).

## 4. Advisor coverage gap analysis — A10 thermo_polynomial_range_advisor

The advisor that would have prevented this is **A10 `thermo_polynomial_range_advisor`** (candidate registered in session 4 retro §6/§8): for each species in the active mechanism, read `Tlow` / `Thigh` from `constant/thermo.compressibleGas`; for each boundary `fixedValue T` in `0/T`, assert `Tlow + safety_margin ≤ T_BC ≤ Thigh - safety_margin`. The check is cheap (O(species × BCs), a few hundred comparisons per case) and the rule it encodes is V93.

**Evidence accumulated for A10 across sessions 4 + 5**:

| Evidence row | Case | State | What A10 would catch |
|---|---|---|---|
| #1 (session 4) | case_009 v1 | failing | 13 species at Tlow=300 in thermo.compressibleGas while `0/T fuel_jet` is fixedValue 294 K → 8.86M warnings + ignite stall |
| #2 (session 5) | case_009 v1.5 | passing | After per-species sweep, all 53 species at Tlow=200; `0/T fuel_jet` still 294 K but 294 > 200 by 94 K safety margin → 0 warnings + clean ignite |

**This is the first time Track C produces paired before/after evidence for the same advisor within a single case across two sessions.** Sessions 1-4 all surfaced single-state-snapshot findings. Sessions 4+5 together demonstrate the **falsifiable counterfactual structure**: in v1 the advisor would have rejected the case; in v1.5 the advisor would have accepted it; the only delta between v1 and v1.5 is the patch that V93 codifies as the actionable rule. The advisor's value is no longer hypothetical — it is empirically isolated to the one bit that V93 changes.

**Promotion gate evaluation** (against the session-4 gate "2nd reacting-low-Mach case"):

- **Strict reading of the gate**: NOT SATISFIED. v1.5 is the same case_009; no new case enters the roster.
- **Substantive reading**: the gate's intent was "evidence beyond a single failing snapshot". v1.5 supplies a *passing* snapshot under the patch, which is functionally a stronger discriminator than two failing snapshots (a 2nd failing case would only re-confirm the negative; v1+v1.5 confirms the rule's actionability).
- **Recommended gate softening** (for user ratification, not auto-land): rephrase A10's promotion gate from "2nd reacting case" to **"paired before/after evidence on ≥1 reacting case, OR 2 independent reacting cases"**. The "OR" clause is satisfied by sessions 4+5.
- **Constraint per session-5 brief**: A10 land is explicitly out-of-scope this session (briefing §硬约束). Recommendation only; no edit to advisor stack.

**What v1.5 does NOT validate for A10**: cross-mechanism robustness (DRM-19 only · GRI-3.0 superset still latent), cross-species coverage (the 11 trace species patched per V93 weren't load-bearing in v1.5's run-time chemistry path), cross-case generalization (only case_009 substrate exercised). These remain genuine gaps. A10's first-land sub-DEC, when dispatched, should ship with `tests/` covering at least the GRI-3.0 superset case path and a synthetic non-reacting compressible-RANS thermo-range case (per session-4 §7 alternative gate-satisfaction path).

## 5. V-row sediment landed by B10 — V93

V93 was landed in commit `2c93e69` (B10 sub-DEC) in both corpora (`industrial_case_solver_findings.md` + `docs/openfoam_corpus/industrial_solver_findings_v_series.md`). This retro adds **zero new V-rows** (per brief §硬约束). V93's content recap, for retro audit-trail completeness only:

- **Class**: reacting-low-Mach actionable rule.
- **Rule**: `min(boundary fixedValue T) - safety_margin ≥ max(per-species Tlow in constant/thermo.compressibleGas)`. If violated, expect janafThermo limit-warning flood at every chemistry source-term evaluation; symptoms = log explodes + ODE substep solver thrashes against limiter + ignition fails to propagate.
- **Canonical remediation tool**: `patch_janaf_tlow.py` (v1.5 substrate). Idempotent. Backup-on-write.
- **Cross-link**: V93 references V41 as the **necessary-but-insufficient** companion; the full mech-loader extraction (DEC-V61-198 sub-DEC candidate) must run V41 (pre-conversion header) + V93 (post-conversion per-species sweep) idempotently.

## 6. V-row amendments landed by B10 — V41 status flip

V41 was amended `[VALIDATED 2026-05-08]` → `[QUESTIONABLE 2026-05-14]` in both corpora as part of commit `2c93e69`, with the Status, Reference case, and Lesson rows updated to cite the v1.5 cleanup. The summary table row at line 103 of `industrial_case_solver_findings.md` was updated to match. **No edits this retro commit** — sediment correction is already on the record; the retro is the methodology consolidation of the act.

The amendment preserves the audit causality the session-4 retro §6 item 3 flagged: V91 (audit finding) and V41 amendment (correction) landed in **separate commits** (`101ed35` retro vs `2c93e69` correction), with B10 carrying the user-ratified semantic flip. Session 5 retro lands as a **third** commit on top, completing the audit→correction→consolidation arc as three independently-reviewable units.

## 7. Pacing acknowledgment — 5 sessions / 2 calendar days

Sessions 1+2+3+4: all 2026-05-13. B10 sub-DEC + session 5 retro (this file): 2026-05-14. **Track C arc has now produced 5 retro-grade sessions in 2 calendar days.**

- **Session 1 §7 weekly recommendation**: ≥1 week cadence between Track C sessions.
- **Session 2 cadence**: 1-day cadence (deviation noted).
- **Session 3 §10 cadence note**: "3 sessions / 1 day" deviation acknowledged.
- **Session 4 §10 pacing note**: "4 sessions / 1 day" + risk of inter-session priming flagged.
- **Session 5 cadence (this file)**: 5 sessions / 2 days. Drift from session-1 §7 baseline = **persistent**.

**Risk addressed by continued clustering**: closing the V41/V91 audit-correction-consolidation arc inside the same warm-context arc-window. Splitting B10 + session 5 retro across a week-long gap would have lost the substrate detail (which `grep` commands return which counts, which timesteps the log limit-storms hit, what the `.pre_tlow_patch` backup looked like) — these are all reproducible from disk but the methodology narrative density would decay.

**Risks incurred**:

- **Priming bias compounded**: session 5 leans heavily on session 4's framing (V83 cross-application pattern, sediment-state-as-verifiable-artifact, channel-(a)-vs-channel-(b) decomposition). The frame fits genuinely for V93 but reads as suspiciously rapid pattern-fitting — same caveat as session 4 §5, now one session deeper into the chain.
- **Inter-session methodology-pattern reuse**: V93 is presented as the **5th cross-application** of V83's intent-cross-reference pattern (see §8 below). The 5th application is the most overdetermined yet, but also the one where independent verification would carry the most weight. Recommend session 6 (whenever it lands) tests a methodology frame **other than** V83 to break the chain's load on a single cross-cutting pattern.
- **Cumulative token-spend** approaching ~300-330k across 5 retros + 4 V-row landings (V88, V91, V92/V93/V94 carried in adjacent commits). Auto-compaction still not triggered; budget tracked.

**Per main-session direction**: continued same-arc cadence is user-ratified for the V41/V91/V93 closure act. Session 6+ should resume weekly cadence unless an equivalently load-bearing audit arc opens.

## 8. Cross-application of V83 — fifth occurrence

V83 (originally session 1 case_010 `mesh_ok` permissive-verdict blind spot) has now cross-applied across five Track C surfaces:

| # | Surface | Session | V-row |
|---|---|---|---|
| 1 | `mesh_ok` permissive verdict semantics | 1 | V83 (origin row) |
| 2 | `check_mesh_summary` accept-without-intent-check | 1+2 | V83 widened |
| 3 | `mrf_audit` accept-rotation-zone-without-cellZone-presence | 3 | V88 sub-mechanism (a) |
| 4 | V-series sediment-status as verifiable-artifact class | 4 | V91 |
| 5 | **boundary-condition fixedValue T ↔ thermo-dict per-species Tlow cross-check** | **5** | **V93** |

Cross-application #5 (this session) widens V83's scope **outside the audit-script class entirely**: V93's intent check spans two CFD artifact files (`0/T` boundary specification + `constant/thermo.compressibleGas` species record), neither of which is an audit script. The cross-cutting pattern is now overdetermined as **"artifact passes a local surface check but violates a cross-artifact intent check"**, with V93 demonstrating that the pattern applies even when both artifacts are first-class case configuration (not audit output).

This is the strongest case yet for the **`audit_verdict_semantics_advisor`** Pillar-2 extraction the session 4 retro §10 flagged. Recommend escalation:

- **Current standing**: "deferred" per session 4 §10 / §reordering recommendation.
- **Recommended standing**: **"queue for next implementation session"** — methodology gap is overdetermined; 5 cross-applications across 5 sessions across 4 numerics classes; pattern survives both audit-script surface and CFD-artifact surface.
- **Scope refinement**: the advisor should accept (artifact_A, artifact_B, intent_rule) tuples rather than being tied to audit scripts. V93's "boundary T ≥ thermo Tlow" check would be one such tuple; V83's "mesh_ok verdict ↔ cellZone presence" would be another.

## 9. e2e numerics class promotion — reacting-low-Mach formally accepted

Per ARC-GOAL #4 "End-to-end solver 跑通 numerics class 数 ≥ 3":

- **Before session 5**: 2 / 3 (compressible-buoyant-RANS · CHT-multi-stream). Reacting-low-Mach was at `[QUESTIONABLE]` per V91 — case_009 v1 ignite stalled at 593 μs and the cold-flow PASS carried janaf limit warnings.
- **After session 5**: **3 / 3**. reacting-low-Mach formally promoted on the strength of v1.5 evidence (commit `2c93e69`).

**Promotion criteria checked**:

1. **Solver runs to its target physical time** — v1.5 ignite ran 0.005 → 0.007 s (2 ms ignite window, 2000 timesteps at dt=1e-6). PASS.
2. **No warning floods that mask real solver behavior** — `grep -c "limit:" log_ignite_v1_5.txt` = 0. PASS.
3. **Physically reasonable signal** — Tmax envelope climbs from pilot floor 1880 K through 1985 K with monotone CO2 (peak 0.110), monotone H2O (peak 0.125), monotone OH (peak 4.3e-3), monotone Qdot (peak 2.2e9 W/m³). Chemistry kicks on; flame structure develops; wall-clock dominated by chemistry ODE not limiter. PASS.
4. **Reproducibility evidence** — `evidence/species_max.json` captures the n=2000 statistics; `evidence/convergence.png` + `evidence/Tmax_vs_time.png` visualize the ignite ramp. `PATCH_LOG.md` documents the patch + physical defense for the 100 K extrapolation. PASS.

**Acknowledged caveat (matches B10 §4 + §5)**: 2 ms is short of full Sandia Flame D steady-state (~50-100 ms for axisymmetric statistics to converge), but the **infrastructure-validation criterion** for "numerics class running" is met: stability, monotone ignition, no limiter-dominated wall-clock. Full-physics validation (Bilger Z profiles vs TNF measurements) is v2+ scope. The class-3 promotion is on **e2e infrastructure**, not **full-physics validation** — same standard applied to compressible-buoyant-RANS and CHT-multi-stream classes.

**ARC-GOAL #4 ledger entry (for main-session reconcile)**:
- New row: "case_009 v1.5 ignition 2000-step PASS · 0 limit warnings · Tmax 1985 K · commit `2c93e69` · sub-DEC `2026-05-14_v61_198_sub_case_009_v1_5_cleanup.md` · retro `2026-05-14_track_c_session_5_case_009_v1_5_reacting.md`"

## 10. Next session candidates

Per sessions 1+2+3+4 §7/§10 + session-5 pacing reset:

- **Session 6** (recommended, weekly cadence resumed): **case_007 KCS ship VOF** (multiphase-VOF numerics class). Still the strongest A8 2nd-evidence candidate per sessions 1+4 §7. Substrate readiness check before scheduling: `ls ~/Desktop/case_007*/case/log/ ~/Desktop/case_007*/evidence/v1*/REPORT.md ~/Desktop/case_007*/case/system/snappyHexMeshDict`.
- **Session 7** (alternative, if A10 lands as separate sub-DEC before session 6): cross-numerics-class **re-visit of case_004 v2 or case_011 v3** with the full Track C protocol post-fix-land, testing "does session N+1 catch findings session N missed". Most directly probes the inter-session priming bias risk session 4 + 5 §pacing flagged.
- **Session 8** (deferred): **case_008 airfoil-with-mount** (transonic-compressible numerics class) — sparse V-corpus coverage (V28/V53), good blind-spot probe + includes sHM dict for A8 widening.

**A10 land recommendation** (out-of-scope this retro but flagged for main-session decision):
- Gate softening recommended in §4 (paired before/after evidence on ≥1 reacting case as alternative gate).
- If accepted, A10 sub-DEC can land in parallel with session 6 — independent surface (`ui/backend/services/geometry_ingest/advisors/thermo_polynomial_range_advisor.py` + tests) from the Track C session arc.

**Substrate readiness check before scheduling session 6**: `ls ~/Desktop/case_007*/case/log/` (sHM completed log present?), `~/Desktop/case_007*/evidence/v1*/REPORT.md` (v1-level limitations documented?), `~/Desktop/case_007*/case/system/snappyHexMeshDict` (feature-list / region-syntax / locationInMesh choices A8 could exercise?).

**A6 / A8 / A10 leverage update post-session-5**:
- **A6 hvac_adpi**: UNCHANGED at 1-case sediment. case_009 v1.5 substrate has no HVAC surface.
- **A8 shm_dict_validator**: UNCHANGED at 1-case sediment. case_009 v1.5 still blockMesh-only.
- **A10 thermo_polynomial_range_advisor**: **structurally ready for land** under softened gate (paired before/after on case_009 v1+v1.5). Strict gate (2nd reacting case) unsatisfied; recommendation = soften gate, land A10 in a sub-DEC parallel to session 6.

— EOF —
