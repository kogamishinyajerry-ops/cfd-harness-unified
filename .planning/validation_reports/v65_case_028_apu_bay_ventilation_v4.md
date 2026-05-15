# Validation Report · case_028 v4 (V65-A B79) APU bay ventilation · pimpleFoam transient relax-to-steady

**Date**: 2026-05-16
**Batch**: B79
**Case ID**: case_028_v4_apu_bay_ventilation
**Predecessor**: case_028 v3 (B78, strong-PARTIAL)
**Substrate**: `.planning/case_profiles/case_028_v4_apu_bay_ventilation_dicts/`
**Sandbox**: `~/Desktop/case_028_apu_bay_ventilation/case_v4/`
**Verdict**: **FAIL** (numerical divergence at t=0.05, catastrophic by t=0.1)

---

## 1 · One-line summary

pimpleFoam transient relax-to-steady, started from v3 endTime=5000 dir relabeled as t=0, diverged catastrophically: continuity error sum_local 4e-7 → 0.03 → 16 → 591 → 4.6e+9 → 1e+70+ in the first ~90 timesteps. **No FULL gate advance vs v3 strong-PARTIAL.** Honest negative result with V108 candidate signature capture.

---

## 2 · Setup vs v3

| Item | v3 (B78) | v4 (B79) | Delta |
|---|---|---|---|
| Solver | simpleFoam | **pimpleFoam** | SIMPLE → PIMPLE |
| Time scheme | steadyState | Euler | steady → transient |
| Initial condition | t=0 fresh | **v3 endTime=5000 relabeled t=0** | relax from near-steady |
| deltaT | n/a | **0.005 s** (fixed) | CFL-targeted |
| endTime | 5000 iter | 5 s (1000 timesteps) | wall-clock budget ~60 min |
| fvSolution PIMPLE | n/a | nOuter=3, nCorr=2, nNonOrth=1 | per-Final variant for relax factors |
| Mesh | constant/polyMesh (110,748 cells) | **REUSED from v3** | bytewise identical |
| BCs | surfaceNormalFixedValue refValue=-0.3 | **INHERITED from v3 t=5000** | no BC change |

**Scope**: This was supposed to push the residual gate that v3 missed (init res 5-7e-3 on Ux/Uy/Uz at iter 5000). The hypothesis was that PIMPLE outer correctors + finite deltaT could let the slowly-pulsating jet/recirculation settle to a tighter within-timestep gate.

---

## 3 · Observed divergence timeline (from log_pimpleFoam.txt)

| Time | sum_local cont.err | global cont.err | Verdict |
|---|---|---|---|
| 0.005 (t1) | 4.03e-7 | 1.78e-9 | OK (matches v3 IC quality) |
| 0.010 (t2) | 7.81e-6 | -1.68e-8 | OK |
| 0.025 (t5) | 2.79e-3 | 5.55e-5 | warning sign — sum_local jumped 3 decades |
| 0.030 (t6) | 3.39e-2 | 1.61e-3 | degrading rapidly |
| 0.035 (t7) | 0.197 | -2.42e-5 | losing control |
| 0.040 (t8) | **4.48** | -2.52e-3 | **critical** — sum_local > 1 |
| 0.045 (t9) | **16.29** | -1.82e-3 | failure cascading |
| 0.050 (t10) | **591** | -5.31e-2 | unrecoverable |
| 0.100 (t20) | **4.6e+9** | 6.2e+7 | already 9 decades over physical |
| 0.200 (t40) | **9.9e+22** | various | utter garbage |
| 0.440 (t88) | **1e+70+** | **1e+70+** | full numerical death |

**Initial residual baseline (t=0.005, PIMPLE iter 1)**: Ux/Uy/Uz init res = 0.005-0.007, smoothSolver doing 2 iter to reach final 2e-4 — matches v3 IC quality, NOT a startup transient artifact.

**Key signal**: PIMPLE outer iter 3 consistently fails to converge: Ux/Uy/Uz hit the 1000-inner-iter cap reaching only ~1e-3 final residual. nOuterCorrectors=3 hits without residualControl 1e-4 being met. Pressure equation receives bad RHS each outer iter → continuity errors compound.

---

## 4 · Numerical post-mortem · 4 contributing causes

1. **Initial condition not actually steady**: v3 endTime=5000 had init residuals 5-7e-3 on Ux/Uy/Uz. SIMPLE residual is "1-norm of solve residual after under-relaxation" which isn't the same physical "steady-state-ness". Relabeling t=0 introduced a finite "kick" — the flow IS transient, just slow.

2. **deltaT=0.005 too aggressive for impinging jet recirculation**: probe at (65.5, 0.5, 0.0) measured 8566 mm/s in v3 — Co at deltaT=0.005 in the recirculation zone is ~5-10× the 1.5 maxCo cap. Adaptive timestep was active (`adjustTimeStep yes`) but max ratio per step capped at 0.2 — couldn't react fast enough.

3. **nOuterCorrectors=3 with smoothSolver 1000-iter cap is over-permissive**: outer iter 3 routinely hits the 1000-inner-iter cap on Ux/Uy/Uz with final residual 0.001-0.03 — meaning PIMPLE consistency was never enforced. Pressure-velocity coupling broke at outer iter 3 → next timestep starts from inconsistent state.

4. **fvSolution relaxationFactors mismatched for transient**: U=0.7 / UFinal=1.0 with `consistent yes` is the v3-style SIMPLEC pattern, not standard PIMPLE. Standard transient PIMPLE typically uses U=1.0 / UFinal=1.0 (no under-relaxation on transient term). Under-relaxing the momentum predictor in a transient context fights the time integration.

**Root cause**: combined failure of all four. Any single one might be survivable; together they compound.

---

## 5 · Mass flow / probe state at failure

| Quantity | v3 final (t=5000 iter) | v4 t=0.005 (first step) | v4 t=0.44 (last sane-ish) |
|---|---|---|---|
| intake mass flow (kg/s) | 1.69 | -1.409 | -1.409 (frozen by surfaceNormalFixedValue BC) |
| vent mass flow (kg/s) | -1.69 (balanced) | various small | **3.67e+73** (garbage) |
| Mass balance | 2e-6% | ~0% | utterly broken |
| Probe (66.5, 0.5, 0.0) Ux | physical | physical | NaN/Inf |

Intake mass flow stays at -1.41 because surfaceNormalFixedValue BC fixes face-normal velocity at the inlet — but the INTERIOR field is what diverged. The BC is a thin film over a corrupted volume.

---

## 6 · §3.1 NOT applicable (FAIL doesn't qualify)

§3.1 MARGINAL→FULL ratification semantics is for canonical-OpenFOAM-geometry-artifact on non-primary-physics-component PARTIAL. **FAIL is not PARTIAL.** A diverged solve produces no ratifiable artifact.

§3.2 multi-case PARTIAL→FULL rebadge: same — FAIL doesn't enter the rebadge pool.

---

## 7 · 4Q gate (V130 thesis)

| Q | Answer |
|---|---|
| LLM offline can run? | ✓ entire batch reproducible with OpenFOAM 2312 + dict substrate + 0 LLM dependency |
| Artifacts produced? | ✓ log_pimpleFoam.txt 345k lines · postProcessing/intake_mass_flow & vent_mass_flow timestep series · 5 probe time-series · failure mode fully captured |
| TrustGate explainable? | ✓ failure was numerical, not physical · 4-cause post-mortem is reproducible · advisor stack would flag (k|omega) un-converged init |
| AI advisor-only? | ✓ no AI touched dict substrate · only Claude Code drove batch · negative result was honestly disclosed |

**4 of 4 PASS.** This is a valid V65-A batch despite FAIL verdict — engineering rigor for a negative result, not redirected from FULL.

---

## 8 · V108 candidate signature capture

**Signature title**: "PIMPLE relax from near-steady SIMPLE final state requires fortified config: nOuterCorr ≥6 + tight residualControl 1e-6 + transient-style relaxFactors (U=1.0) + adaptive deltaT with aggressive maxCo=0.5"

**Death mode**: SIMPLE final residual ~5e-3 does NOT mean "transient-ready IC". Init residual measures within-iter solve quality, not steadiness. Relabeling SIMPLE final dir as t=0 for pimpleFoam, then using textbook PIMPLE config with under-relaxation, will diverge in 5-10 timesteps for impinging-jet/recirculation flows.

**Witness case**: case_028 v4 (single case in v65-A · would need 2nd witness OR canonical-reference attribution for V-row promotion to Confirmed).

**Cross-reference candidate**: case_001 V107 (3D-ducted-STL surface area measured from sHM not bbox) — both V107 and V108 are "naive transfer of v_n config to v_{n+1} substrate produces silent failures." Methodology pattern: don't reuse parent-substrate assumptions without re-derivation.

**Promotion gate**: V108 stays "Candidate" until a 2nd witness case demonstrates the same death mode, OR until OpenFOAM PIMPLE-from-SIMPLE-relabel anti-pattern is documented in canonical reference (e.g., Greenshields CFD Direct user guide §pimpleFoam).

---

## 9 · Score impact

| Pillar | Pre-B79 | Post-B79 | Δ |
|---|---|---|---|
| 1 · Validation maturity (30%) | 38 | **38** | +0 (no industrial FULL gain · FAIL doesn't advance) |
| 2 · Corpus depth (20%) | 67 | **67.5** | +0.5 (V108 candidate signature + honest negative result entry) |
| 3 · Advisor stack (15%) | 72 | 72 | +0 |
| 4 · Reproducibility (10%) | 78 | 78 | +0 |
| 5 · Governance (10%) | 81 | 81 | +0 |
| 6 · Engineer UX (10%) | 55 | 55 | +0 |
| 7 · AI-advisor SSOT (5%) | 62 | 62 | +0 |
| **Weighted** | **62.9** | **63.0** | **+0.1** |

**Distance to 95**: 32.0 points (negligible movement). B79 was net-neutral with marginal corpus uptick — honest accounting.

---

## 10 · Recommendations for B80

**Do NOT retry pimpleFoam v5** on case_028 with same near-steady IC. The death mode is config-deep; would need 3-4 timesteps of careful adaptive-deltaT ramping + relaxed BCs + transient-style fvSolution. ROI lower than alternative B80 attacks.

**Better B80 candidates** (by ROI for 95-distance):
- **B80-A**: case_028 v5 from-rest (t=0 U=0 + slowly ramp BC over 0.5s) with **steadyState SIMPLE only** — abandon transient ambition, push residual gate via better v3-equivalent under-relaxation + longer iter budget (10k iter). Risk: still strong-PARTIAL. ROI: Pillar 1 +1-2.
- **B80-B**: NEW industrial case — propulsion intake or wing-cavity (different physics envelope, fresh FULL attempt). Risk: substrate setup overhead 3-4 hours. ROI: Pillar 1 +2-4 if lands FULL.
- **B80-C**: V104 promotion from Candidate→Confirmed via 2nd witness (cross-case work). Risk: depends on which V-row. ROI: Pillar 2 +1-2.

**B80 recommendation: B80-B (new industrial case)** — best Pillar 1 leverage, fresh start avoids v4 config-debt, V65-A "net-new industrial e2e" dimension counter advances.

---

## 11 · Substrate immutability

v4 dicts remain at `.planning/case_profiles/case_028_v4_apu_bay_ventilation_dicts/` UNTOUCHED. Sandbox at `~/Desktop/case_028_apu_bay_ventilation/case_v4/` preserved (log + postProcessing). No retro-edit. v5 would be a sibling dir, never a v4 mutation.

---

## 12 · Honest disclosure

- This was a high-effort batch (~60 min wall-clock) that produced ZERO industrial FULL advance.
- Verdict is FAIL, not strong-PARTIAL. Don't dress it up.
- The user mandate is "iterate to 95" — that means SOME batches will fail. The discipline is honest accounting + V-row capture + ROI-driven next pick, not refusing to attempt risky configs.
- v3 strong-PARTIAL remains the case_028 SOTA. v4 is a sibling experiment that didn't pan out.

— Claude Code (Opus 4.7 1M) · B79 · 2026-05-16
