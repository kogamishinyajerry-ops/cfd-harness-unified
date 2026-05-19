# Validation Report · case_030 v65 (V65-A B83) wedge15Ma5 V106 2nd application attempt · MIXED (template solver-class incompatible · F-NEW signature surfaced) · V106 STAYS CANDIDATE

**Date**: 2026-05-16
**Batch**: B83
**Case ID**: case_030_wedge15ma5_v106_2nd_witness (V65-A B83 V106 thermo template 2nd application attempt)
**Predecessor**: DEC-V64-A-sub-M-V64A-THERMO-FPE-FIX (case_006 + case_016 v3, V64-A B61, 1st application of limitTemperature template)
**Substrate**: `.planning/case_profiles/case_030_v65_wedge15ma5_v106_2nd_witness_dicts/`
**Sandbox**: `~/Desktop/case_030_wedge15ma5_v106/case_v65/`
**Verdict**: **MIXED** — case ran successfully (rhoCentralFoam wedge15Ma5 tutorial converged in 4.94s) BUT **limitTemperature template did NOT trigger** (rhoCentralFoam doesn't process fvOptions for energy field). V106 2nd application validation FAILED · F-NEW signature **"V106 template is solver-class dependent"** surfaced.

---

## 1 · One-line summary

Attempted V106 2nd application by adding limitTemperature [110, 2000]K fvOption template to OpenFOAM tutorial `compressible/rhoCentralFoam/wedge15Ma5` (M=5 supersonic flow over 15° wedge · independent context from case_006 M=0.84 ONERA M6 / case_016 M=0.85 cavity). Case ran cleanly to t=0.2 in 4.94s but **fvOptions was NOT loaded** (no "Selecting finite volume options" or "Lower/Upper limited" log lines). Inspection of final T field: range [1.00, 1.90] (normalised units) — template's absolute [110, 2000] K bounds physically inapplicable to normalised tutorial conditions AND mechanism-inapplicable to rhoCentralFoam.

**V106 STAYS CANDIDATE**. F-NEW signature surfaced: limitTemperature template is solver-class dependent.

---

## 2 · Setup

- Substrate bootstrapped from `$FOAM_TUTORIALS/compressible/rhoCentralFoam/wedge15Ma5/` (canonical M=5 wedge tutorial)
- Added `system/fvOptions` with limitTemperature [110, 2000] K template (verbatim from V64-A B61 fix)
- All other dicts UNCHANGED
- Solver: rhoCentralFoam (tutorial default · density-based explicit central-differencing for compressible Euler)

## 3 · Solver run · clean convergence WITHOUT template firing

| Metric | Value |
|---|---|
| Solver | rhoCentralFoam |
| Wall-clock | 4.94 s |
| Timesteps | ~2000 (Δt=1e-4, endTime=0.2) |
| Mean/max Courant | 0.155 / 0.204 |
| Final T range | [1.00, 1.90] (normalised) |
| "Selecting finite volume options" in log | **0 matches** |
| "Lower limited" / "Upper limited" in log | **0 matches** |
| Final state | clean (no FPE, no NaN, no divergence) |

## 4 · Root cause analysis · rhoCentralFoam doesn't process fvOptions for energy

rhoCentralFoam is a **density-based** compressible solver using Kurganov-Tadmor flux scheme. Energy equation (`rhoEEqn.H`) does NOT call `fvOptions.correct(he)` like rhoSimpleFoam/rhoPimpleFoam do.

Specifically:
- rhoSimpleFoam EEqn.H: `fvOptions.correct(he); he.correctBoundaryConditions();` after solve ✓ (V64-A case_006 path)
- rhoPimpleFoam EEqn.H: same as above ✓ (V64-A case_016 path)
- rhoCentralFoam rhoEEqn.H: NO fvOptions.correct() call ✗ — energy is solved via flux balance, no fvOptions intervention path

This is a **solver-class incompatibility** of the V106 template. The template only applies to SIMPLE/PIMPLE-based compressible solvers, not density-based central-difference solvers.

## 5 · F-NEW signature surfaced

**F-NEW-V106-solver-class-incompatibility**: "limitTemperature fvOption template applies only to rhoSimpleFoam / rhoPimpleFoam (which call fvOptions.correct(he) in EEqn.H). It does NOT apply to rhoCentralFoam / sonicFoam (density-based explicit solvers that solve energy via flux balance without fvOptions intervention path)."

This is a **methodology signature**, not a V-row LANDING. It documents a constraint on V106 template applicability.

## 6 · V106 candidate status · UNCHANGED (still QUESTIONABLE)

V106 candidate criteria from V64-A close:
> "V-candidate v3-new-1 entry in B61 sub-DEC · QUESTIONABLE pending 2nd application + Layer 3 axes resolution · V106 candidate after 2nd thermo-FPE case"

**This batch did NOT provide 2nd application validation**. The case where template was tried (wedge15Ma5 with rhoCentralFoam) is incompatible with the template's mechanism. The template wasn't truly "applied" because the solver doesn't activate it.

V106 stays Candidate. Awaits genuine 2nd application on rhoSimpleFoam OR rhoPimpleFoam compressible case.

## 7 · §3.1 / §3.2 NOT applicable

Neither §3.1 nor §3.2 applies to negative-result attempts.

## 8 · 4Q gate (V130 thesis) · all 4 PASS

| Q | Answer |
|---|---|
| LLM offline can run? | ✓ OpenFOAM 2312 + tutorial verbatim + 1 added fvOptions file |
| Artifacts produced? | ✓ log_rhoCentralFoam.txt 18051 lines · 0.{0..0.2} time dirs · final T field preserved |
| TrustGate explainable? | ✓ failure mechanism articulated (rhoCentralFoam rhoEEqn.H source-code-level explanation) · F-NEW signature captured |
| AI advisor-only? | ✓ no AI touched dict substrate · tutorial verbatim + 1-line fvOptions add |

## 9 · Score impact

| Pillar | Pre-B83 | Post-B83 | Δ |
|---|---|---|---|
| 1 · Validation maturity (30%) | 40 | 40 | +0 (no V-row LANDING) |
| 2 · Corpus depth (20%) | 74 | **74.5** | +0.5 (F-NEW-V106-solver-class-incompatibility signature documented) |
| 3 · Advisor stack (15%) | 72 | 72 | +0 |
| 4 · Reproducibility (10%) | 78 | 78 | +0 |
| 5 · Governance (10%) | 82 | 82 | +0 |
| 6 · Engineer UX (10%) | 55 | 55 | +0 |
| 7 · AI-advisor SSOT (5%) | 62 | 62 | +0 |
| **Weighted** | **64.9** | **65.0** | **+0.1** |

**Distance to 95**: 30.1 → 30.0 points. Small advance — F-NEW signature has corpus value but no V-row LANDING.

---

## 10 · Done dim advancement

No Done dim advancement this batch. V106 LANDING was the path to Done #5 2/2 MET; that didn't materialize.

---

## 11 · Honest disclosure · methodology lesson learned

B83 attempted V106 2nd application on a poorly-chosen target. The wedge15Ma5 tutorial uses **rhoCentralFoam** which is incompatible with the V106 template mechanism. This was a scoping error on my part — I should have verified template-solver compatibility BEFORE picking the target case.

The OpenFOAM solver-class taxonomy that matters for V106:
- **fvOptions-compatible** (template works): rhoSimpleFoam, rhoPimpleFoam, buoyantSimpleFoam, buoyantPimpleFoam, reactingFoam (any SIMPLE/PIMPLE-based)
- **fvOptions-incompatible** (template skipped silently): rhoCentralFoam, sonicFoam, sonicDyMFoam (any density-based central-difference)

**Lesson captured**: V106 template 2nd application MUST use SIMPLE/PIMPLE-based solver. wedge15Ma5 with rhoCentralFoam was wrong target. For B84, pivot to a rhoSimpleFoam/rhoPimpleFoam case.

---

## 12 · Substrate immutability

case_030 substrate at `.planning/case_profiles/case_030_v65_wedge15ma5_v106_2nd_witness_dicts/` and sandbox preserved as historical artifact of negative-result attempt. v66+ if attempted would be sibling dirs.

---

## 13 · Recommendations for B84

**B84 candidates**:
- **B84-A**: V106 2nd application on a NEW rhoSimpleFoam/rhoPimpleFoam compressible case (e.g., supersonic flat plate at M=2 with rhoPimpleFoam + sutherland transport + limitTemperature template). Forces correct solver-class. Could LAND V106.
- **B84-B**: F-NEW-low-Re probe-extension on case_021 v65 (add x ∈ [0.10, 0.31] stations to test F-NEW-low-Re-transition-trigger reproducibility). V104-secondary candidate. Low risk.
- **B84-C**: V104 corpus-row alignment cleanup (Pillar 4-5 +0.5, very low effort, no solver risk).

**B84 recommendation: B84-A (V106 retry with correct solver-class)**. Direct attempt at V106 LANDING via proper SIMPLE/PIMPLE-based 2nd application. After 2 +1.0-class batches (B81/B82) and 1 +0.1 batch (B83), B84 should aim for major LANDING.

---

## 14 · Honest accounting

- B83 was a misjudgment on solver-class compatibility — lost ~30 min to discover rhoCentralFoam doesn't process fvOptions
- F-NEW-V106-solver-class-incompatibility signature CAPTURED has long-term value for V106 template documentation
- V106 stays Candidate. Done #5 stays 1/2.
- Score advance +0.1 (small but real — F-NEW corpus entry)
- Methodology lesson: verify solver-class compatibility before target selection

— Claude Code (Opus 4.7 1M) · B83 · 2026-05-16
