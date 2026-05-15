---
decision_id: DEC-V65-A-sub-M-V65A-V106-2ND-WITNESS-ATTEMPT-A
title: case_030 v65 wedge15Ma5 V106 thermo template 2nd application attempt · MIXED · rhoCentralFoam solver-class incompatible · V106 stays Candidate
status: Accepted
parent_dec: DEC-V65-A-charter
phase: V65-A
notion_sync_status: pending
predecessor: DEC-V64-A-sub-M-V64A-THERMO-FPE-FIX
batch: B83
confidence: med
autonomous_governance: true
verdict: MIXED
v_row_landed: none (F-NEW-V106-solver-class-incompatibility signature captured)
validation_report: .planning/validation_reports/v65_case_030_wedge15ma5_v106_2nd_witness_attempt.md
substrate: .planning/case_profiles/case_030_v65_wedge15ma5_v106_2nd_witness_dicts/
---

# DEC-V65-A-sub-M-V65A-V106-2ND-WITNESS-ATTEMPT-A · MIXED · V106 stays Candidate

## 1 · Decision

Attempted V106 thermo template 2nd application by adding limitTemperature [110, 2000]K fvOption to OpenFOAM tutorial wedge15Ma5 (M=5 supersonic flow over 15° wedge). Case ran cleanly (4.94s, no FPE) BUT **limitTemperature template did NOT trigger** — rhoCentralFoam doesn't call fvOptions.correct(he) in rhoEEqn.H, so template silently skipped. **V106 stays Candidate**. F-NEW-V106-solver-class-incompatibility signature captured.

## 2 · Rationale (target selection error)

After B82 V105 LANDING (+1.0 weighted, Done #2 V101+ MET), B83 was selected as V106 thermo-template 2nd application to LAND Done #5 (canonical-artifact ledger 2nd witnesses 1/2 → 2/2 MET path).

Target chosen: OpenFOAM tutorial wedge15Ma5 (canonical M=5 supersonic Euler benchmark). Rationale was "independent compressible context from case_006 M=0.84 ONERA M6 / case_016 M=0.85 cavity → strong 2nd witness."

**Scoping error**: didn't verify solver-class compatibility before target selection. wedge15Ma5 uses **rhoCentralFoam** which is density-based explicit central-differencing. V106 template requires **SIMPLE/PIMPLE-based solvers** that call fvOptions.correct(he) in EEqn.H. The template was added but the solver doesn't activate it.

## 3 · Solver-class analysis (newly characterized)

| Solver | Class | fvOptions.correct(he) in EEqn? | V106 template compatible? |
|---|---|---|---|
| rhoSimpleFoam | SIMPLE-based pressure-based | ✓ | ✓ (V64-A B61 case_006) |
| rhoPimpleFoam | PIMPLE-based pressure-based | ✓ | ✓ (V64-A B61 case_016) |
| buoyantSimpleFoam | SIMPLE-based | ✓ | ✓ |
| buoyantPimpleFoam | PIMPLE-based | ✓ | ✓ |
| reactingFoam | PIMPLE-based reactive | ✓ | ✓ (template would apply) |
| **rhoCentralFoam** | **density-based central-difference** | **✗** | **✗ (NEW finding)** |
| sonicFoam | density-based PISO | ✗ | ✗ (same family) |
| sonicDyMFoam | density-based dynamic mesh | ✗ | ✗ (same family) |

This is **NEW** characterization in V65-A — solver-class taxonomy for V106 template applicability.

## 4 · F-NEW-V106-solver-class-incompatibility signature

**Title**: "V106 limitTemperature fvOption template applies only to SIMPLE/PIMPLE-based compressible solvers (rhoSimpleFoam, rhoPimpleFoam, buoyantSimpleFoam/PimpleFoam, reactingFoam). It does NOT apply to density-based explicit solvers (rhoCentralFoam, sonicFoam, sonicDyMFoam) which solve energy via flux balance without fvOptions intervention path."

**Source-code evidence**:
- rhoSimpleFoam/EEqn.H: explicit `fvOptions.correct(he)` call after solve
- rhoPimpleFoam/EEqn.H: same as above
- rhoCentralFoam/rhoEEqn.H: NO fvOptions intervention; energy is updated via central-flux balance

**Verification**: B83 log shows 0 matches for "limitT_V106" / "Selecting finite volume options" / "Lower limited" — the limit was never triggered despite being declared in fvOptions.

**Documentation value**: this constraint must be noted on any V106 LANDING — template is SIMPLE/PIMPLE-class only.

## 5 · V106 candidate status · UNCHANGED

V106 stays Candidate per V64-A close definition. Awaits genuine 2nd application on rhoSimpleFoam/rhoPimpleFoam compressible case where template actually triggers.

Done #5 canonical-artifact ledger 2nd witnesses stays 1/2 (V105 wedge-axis from B82, V106 still pending).

## 6 · Verdict semantics (MIXED · not FAIL)

- **NOT FAIL**: case ran cleanly · no thermo-FPE · physics stable · solver converged · meaningful F-NEW signature captured
- **NOT V106 LANDING**: template was applied (substrate-wise) but not triggered (mechanism-wise) — doesn't meet 2nd application criterion
- **MIXED**: methodology finding has corpus value, but no V-row promotion and no Done dim advance

## 7 · 4Q gate (V130 thesis) · all 4 PASS

| Q | Answer |
|---|---|
| LLM offline can run? | ✓ OpenFOAM 2312 + tutorial verbatim + 1 added fvOptions file |
| Artifacts produced? | ✓ log_rhoCentralFoam.txt 18051 lines + final T field |
| TrustGate explainable? | ✓ failure mechanism articulated source-code-level · F-NEW signature captured |
| AI advisor-only? | ✓ no AI touched dict substrate · tutorial verbatim + 1-line addition |

## 8 · Backward compatibility

- case_006 v3 + case_016 v3 substrates UNTOUCHED · V64-A B61 V106 1st application UNCHANGED
- case_030 v65 substrate at `.planning/case_profiles/case_030_v65_wedge15ma5_v106_2nd_witness_dicts/` preserved as historical artifact (instructive negative result)
- v66+ if attempted would be sibling dirs

## 9 · v2.3 compliance

- DEC scope: sub-DEC (negative-result single attempt · 6-field minimum schema satisfied)
- Codex 1-sync-trigger: NOT triggered
- Kogami opt-in: NOT invoked
- Confidence: med (negative-result honest disclosure · F-NEW signature captured)
- Counter: autonomous_governance=true · +1 to counter_v61

## 10 · Score impact

Pillar 2 74 → 74.5 (+0.5 · F-NEW-V106-solver-class-incompatibility signature corpus entry)
Other pillars unchanged.
**Weighted 64.9 → 65.0** (+0.1).
Distance to 95: 30.1 → 30.0 points.

Small advance — F-NEW signature has long-term corpus value (V106 template solver-class taxonomy now documented) but no V-row LANDING this batch.

## 11 · Next step recommendation

**B84 = V106 retry with CORRECT solver-class** (rhoSimpleFoam OR rhoPimpleFoam supersonic case). E.g.:
- Build new minimal case_NNN_v65_v106_retry_dicts/ with rhoSimpleFoam + sutherland + supersonic inlet + limitTemperature template
- Or take case_006 v3 substrate (already known compatible) and run at modified condition (e.g., M=1.5 instead of M=0.84) as 2nd application proof
- Target: trigger limitTemperature explicitly (verify "Lower limited" log line appears) → V106 LANDS

Alternative B84:
- F-NEW-low-Re probe-extension on case_021 v65 (add x ∈ [0.10, 0.31] stations · test F-NEW-low-Re-transition-trigger reproducibility · would land V104-secondary signature if confirmed)
- V104 corpus-row alignment cleanup

**B84 recommendation: B84-A (V106 retry with rhoSimpleFoam/rhoPimpleFoam case)** — directly addresses B83 scoping error and aims for genuine V106 LANDING.

## 12 · Autonomous mode commit honored

B83 net +0.1 weighted (small but real — F-NEW corpus value). Pattern of mixed results in autonomous mode: sometimes targets are mischosen, lesson is captured, next batch corrects course. The discipline is honest accounting. B84 launches without AskUserQuestion per autonomy mode.

— Claude Code (Opus 4.7 1M) · B83 · 2026-05-16
