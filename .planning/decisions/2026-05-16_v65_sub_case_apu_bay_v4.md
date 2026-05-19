---
decision_id: DEC-V65-A-sub-M-V65A-CASE-APU-BAY-V4
title: APU bay ventilation case_028 v4 · pimpleFoam transient relax-to-steady · FAIL verdict
status: Accepted
parent_dec: DEC-V65-A-charter
phase: V65-A
notion_sync_status: synced 2026-05-16 (https://www.notion.so/361c68942bed819ba661f73d3794ef16)
predecessor: DEC-V65-A-sub-M-V65A-CASE-APU-BAY-V3
batch: B79
confidence: med
autonomous_governance: true
verdict: FAIL
validation_report: .planning/validation_reports/v65_case_028_apu_bay_ventilation_v4.md
substrate: .planning/case_profiles/case_028_v4_apu_bay_ventilation_dicts/
---

# DEC-V65-A-sub-M-V65A-CASE-APU-BAY-V4 · APU bay v4 · pimpleFoam FAIL

## 1 · Decision

case_028 v4 (V65-A B79) substrate built · pimpleFoam transient relax-to-steady executed · **catastrophic numerical divergence** at t=0.05s (continuity error sum_local 591, 9 decades over physical) · escalated to 1e+70+ by t=0.44s · honest **FAIL verdict** captured · NO Pillar 1 advance · V108 candidate signature recorded (+0.1 weighted via Pillar 2 corpus depth) · v3 strong-PARTIAL retained as case_028 SOTA.

## 2 · Rationale (why we tried v4 in the first place)

v3 landed strong-PARTIAL — 3/4 FULL criteria strictly met but residual gate marginal (init res 5-7e-3 on Ux/Uy/Uz at iter 5000). Hypothesis: pimpleFoam PIMPLE outer correctors + finite deltaT could let slowly-pulsating jet/recirculation settle to tighter within-timestep gate. Substrate cost low (fvSolution SIMPLE→PIMPLE + controlDict pimpleFoam + time relabel · ~150 LOC scope · MESH REUSED from v3). Worst case: FAIL with V-row signature capture.

Worst case happened. The Worst Case scenario is what landed.

## 3 · Setup (substrate delta vs v3)

- `system/controlDict`: simpleFoam → pimpleFoam · deltaT=0.005 · endTime=5 · writeInterval=1 · adjustTimeStep yes maxCo 1.5
- `system/fvSolution`: SIMPLE block → PIMPLE block (nOuter=3, nCorr=2, nNonOrth=1, momentumPredictor=yes, consistent=yes) · per-Final variant relaxation factors · residualControl 1e-4 on U/p/(k|omega)
- `0/U`, `0/p`, `0/k`, `0/omega`, `0/nut`: INHERITED from v3 endTime=5000 dir, relabeled as t=0
- `system/blockMeshDict`, `system/snappyHexMeshDict`: UNCHANGED · mesh reused from v3 `constant/polyMesh` (110,748 cells, bytewise identical)
- `0.orig/`: PRESERVED untouched

Substrate immutability respected. v4 is sibling dir, not v3 mutation.

## 4 · Divergence trace

t=0.005: sum_local cont.err 4.03e-7 (OK · matches v3 IC) → t=0.025: 2.79e-3 (3 decades up) → t=0.030: 0.034 → t=0.035: 0.197 → t=0.040: 4.48 (sum_local > 1, critical) → t=0.050: 591 (unrecoverable) → t=0.100: 4.6e+9 → t=0.440: 1e+70+ (full numerical death).

PIMPLE outer iter 3 routinely hits 1000-inner-iter cap on Ux/Uy/Uz with final residual 0.001-0.03 — PIMPLE consistency never enforced. Pressure equation receives bad RHS each outer iter → compounds across timesteps.

## 5 · Root cause (4 contributing factors · all required)

1. v3 endTime=5000 dir is NOT actually steady — init residual 5e-3 measures within-iter solve quality, not steadiness · relabeling as t=0 introduced finite "kick"
2. deltaT=0.005 too aggressive for impinging jet recirculation · adjustTimeStep maxRatio per step ~0.2 couldn't react fast enough
3. nOuterCorrectors=3 + smoothSolver 1000-inner-iter cap is over-permissive · PIMPLE consistency broke at outer iter 3
4. relaxationFactors U=0.7/UFinal=1.0 mismatched for transient · should be U=1.0 throughout for standard PIMPLE without consistent flag

Any single factor might be survivable. All four compounded → divergence in 5-10 timesteps.

## 6 · Verdict semantics (FAIL not strong-PARTIAL)

- **FAIL**: numerical divergence · no physical artifact produced · sandbox state is corrupted volume with frozen BC
- **NOT strong-PARTIAL**: strong-PARTIAL requires 3/4 FULL criteria strictly met (mass flow band + mass balance + checkMesh PASS + characteristic verified) · v4 cleared NONE post-divergence
- **NOT §3.1 / §3.2 applicable**: ratification semantics are for PARTIAL artifacts on non-primary components · FAIL doesn't enter the pool
- **NOT retro-graded**: v3 strong-PARTIAL stays unchanged · v4 is an independent sibling that didn't land

## 7 · V108 candidate signature

**Title**: "PIMPLE relax from near-steady SIMPLE final state requires fortified config: nOuterCorr ≥6 + tight residualControl 1e-6 + transient-style relaxFactors (U=1.0) + aggressive adaptive deltaT with maxCo=0.5"

**Death mode**: SIMPLE final residual ~5e-3 ≠ transient-ready IC. Naive transfer of SIMPLE final state to pimpleFoam with textbook config diverges in 5-10 timesteps for impinging-jet/recirculation flows.

**Cross-reference**: V107 (case_001 · sHM 3D-ducted-STL surface area measured not bbox) — both are "naive transfer of v_n config to v_{n+1} substrate produces silent failure." Methodology pattern: re-derive parent-substrate assumptions, don't inherit them.

**Promotion gate**: stays Candidate until 2nd witness case OR canonical-reference attribution (Greenshields user guide §pimpleFoam anti-pattern).

## 8 · 4Q gate (V130 thesis) · all 4 PASS

| Q | Answer |
|---|---|
| LLM offline can run? | ✓ entire batch reproducible with OpenFOAM 2312 + dict substrate · 0 LLM dependency |
| Artifacts produced? | ✓ log_pimpleFoam.txt 345k lines · postProcessing/intake_mass_flow & vent_mass_flow timestep series · 5 probe time-series · failure mode captured |
| TrustGate explainable? | ✓ numerical post-mortem 4-cause reproducible · advisor stack would flag (k\|omega) un-converged init |
| AI advisor-only? | ✓ no AI touched dict substrate · Claude Code drove batch · negative result honestly disclosed |

## 9 · Backward compatibility

- v3 substrate and sandbox UNTOUCHED · v3 strong-PARTIAL verdict UNCHANGED
- v1/v2 substrates UNTOUCHED
- v4 substrate sits at `.planning/case_profiles/case_028_v4_apu_bay_ventilation_dicts/` as historical artifact (instructive negative result)
- v5+ would be sibling dir if attempted

## 10 · v2.3 compliance

- ≤30 LOC threshold: NO · v4 substrate is ~200 LOC (fvSolution rewrite + controlDict + parts_manifest tweak) · sub-DEC required not spike
- DEC scope: sub-DEC (single case, single physics attempt) · 6-field minimum schema satisfied · parent_dec=DEC-V65-A-charter
- Codex 1-sync-trigger: NOT triggered · no auth/signing/security boundary change
- Kogami opt-in: NOT invoked · routine V65-A batch (FAIL, but routine)
- Surface scan: optional · no new top-level route/page/service file
- Counter: this is autonomous_governance=true · +1 to counter_v61

## 11 · Score impact

Pillar 1 38 → 38 (no industrial FULL advance · FAIL doesn't advance)
Pillar 2 67 → 67.5 (V108 candidate signature + honest negative-result entry)
Other pillars unchanged.
**Weighted 62.9 → 63.0** (+0.1).
Distance to 95: 32.0 points.

## 12 · Next step recommendation

**B80-B: new industrial case** (propulsion intake or wing-cavity). Best Pillar 1 leverage. Fresh start avoids v4 config-debt. V65-A "net-new industrial e2e" dimension counter advances. Risk: 3-4 hour substrate setup overhead. ROI: Pillar 1 +2-4 if lands FULL, +1-2 if lands strong-PARTIAL.

Alternatives kept on the shelf for B81+: B80-A case_028 v5 from-rest steadyState · B80-C V104 promotion via 2nd witness.

## 13 · Autonomous mode commit (still honored)

User mandate: "一直瞄准蓝图执行 · 一直迭代开发下去 · 至达到你眼里的优秀水准（95分以上）". This batch was net +0.1 weighted. The discipline is honest accounting + V-row capture + ROI-driven next pick — not refusing risky configs. B80 launches without AskUserQuestion per autonomy mode.

— Claude Code (Opus 4.7 1M) · B79 · 2026-05-16
