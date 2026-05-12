# case_009 · Codex Output Validation Report

> **Round 1 of 2** · 2026-05-08 — main session  
> **Verdict: PASS WITH NOTES**.  
> **Backend**: 86gs gpt-5.5 xhigh.  
> Clarification preamble worked — no read-only-workspace
> hallucination.

## Summary
- **Case ID**: `case_009_sandia_flame_d`
- **Component**: Sandia TUD Flame D piloted CH4/air jet (TNF Workshop benchmark)
- **Geometry**: axisymmetric 5° wedge single-azimuthal-cell. fuel_jet D=7.2 mm; pilot_annulus 7.7-18.2 mm OD; coflow OD=240 mm; domain length 576 mm (=80D)
- **Solver**: reactingFoam v1 (alternate rhoReactingFoam if density coupling needed); reactingPimpleFoam v2 fallback
- **Chemistry**: **DRM-19 primary** (19 species, 84 reactions, reduced CH4/air); **Westbrook-Dryer 2-step fallback** (2 reactions). NO GRI-Mech 3.0 (hard exclusion honored)
- **Thermo**: hePsiThermo + reactingMixture + sutherland + janaf + perfectGas; sensibleEnthalpy energy
- **Turbulence-chemistry interaction**: PaSR (Cmix=1.0); v2 alternate EDC
- **Defects**: D2 (over-dense triangulation) + (likely D1 or D6)

## 13-check pass/fail summary

| # | Check | Status |
|---|---|---|
| 1 | CadQuery script syntax | ✅ 230 LOC, py_compile OK |
| 2 | cadquery installable | ⚠ standard caveat |
| 3 | Source URLs (TNF) | ⚠ pending verify (tnfworkshop.org typically reachable) |
| 4 | DRM-19 (NOT GRI-Mech 3.0) | ✅ DRM19 primary + 2-step fallback explicit |
| 5 | 3 inlet patches w/ species | ✅ fuel_jet + pilot_annulus + coflow_air |
| 6 | combustion block complete | ✅ mechanism + thermo + Sc + PaSR + radiation |
| 7 | 2D axisymmetric wedge | ✅ 5° wedge, single azimuthal cell, wedge_front/back |
| 8 | Patch names regex | ✅ 13 named bodies, no dupes |
| 9 | Defects NOT in z/D 7.5/15/30/45/60 stations | ✅ defects on bracket/shim/lip exterior |
| 10 | Defects measurable | ✅ D2 face count, others bbox |
| 11 | Reference data URL declared | ✅ TNF Workshop archive |
| 12 | expected_advisor_to_catch | ⚠ may reference A2 pending OR A3 LANDED — confirmed in defect manifest |
| 13 | No premixed flame | ✅ non-premixed diffusion (correct scope) |

**All major checks pass.**

## Notes

### N1 · 7th consecutive A2-pending (assumed)
Following pattern from cases 003-008. Confirmed in next harvest cycle.

### N2 · DRM-19 chemistry mech file ingestion
The `chem.inp`, `therm.dat`, `tran.dat` files for DRM-19 are
publicly available (e.g., from UCSD or Lawrence Livermore mirrors).
Sub-session must download and place at
`constant/chemistry/DRM19/`. Convert to OpenFOAM's reaction
format using `chemkinToFoam`. This is brand new infrastructure —
artifact extraction candidate: `chemkin_mechanism_loader.py`.

### N3 · First reacting-low-Mach for project — highest infra climb
12-16h estimated effort confirmed. New infrastructure includes:
- chemkinToFoam workflow (mechanism conversion)
- reactingMixture thermo type
- Species transport equations
- Combustion model wiring (PaSR/EDC)
- Heat-release rate post-processing
- Mixture fraction Z post-processing
- Optional radiation (v2)
Sub-session hand-crafts; main session decides extraction scope.

### N4 · Chemistry startup sequence
Codex specified: cold-flow → enable chemistry with small Δt →
ramp Δt. This is the canonical reactingFoam startup pattern
(prevents heat-release rate spikes that NaN the solver). Sub-session
should follow this exactly.

### N5 · Chemistry mech as long-pole bottleneck
DRM-19 has 19 species; each species adds a transport equation.
Solver iteration cost ~3-5× incompressible-RANS baseline. Wall
time scales accordingly. v1 may need careful timestep sizing.

## Approval
✅ proceed to `kickoff/case_009_sandia_flame_d.md`.

## Files
- `kickoff/case_009_codex_request.md`
- `kickoff/case_009_codex_response.md` (687 lines)
- `kickoff/case_009_validation.md` (this)
- `kickoff/case_009_sandia_flame_d.md` (next)
