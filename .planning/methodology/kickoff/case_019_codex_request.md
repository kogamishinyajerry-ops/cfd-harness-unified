# Codex Case-Design Request · case_019

> **Status**: PENDING — Codex round 1 not yet sent.
> **Phase**: Industrial Extension Phase 4 #3 per
> `.planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md`.
> **Strategic role**: Forced mixing + scalar transport — process-
> industry classic. Extends case_003 incompressible-RANS to scalar
> tracer. D2 stress-test (over-dense triangulation) on mixer
> elements.
> **Backend**: CRS gpt-5.4 high primary; 86gs fallback.
> **Soft blockers**: case_009 D2 evidence informs A3-v2 priority
> (B3 from dispatch plan); if A3 cross-case unstable, case_019
> may need A3-v2 first OR alternative defect.

## Target

| field | value |
|---|---|
| case_id | `case_019_<short_name>` (Codex picks; suggested: `kenics_static_mixer`) |
| solver_class_target | Forced mixing: `simpleFoam` + scalar transport equation (extends 003) |
| numerics_class | incompressible-RANS + scalar (extends 003) |
| coverage map row to fill | "Static mixer / RTD / chemical mixing (process industry)" — currently uncovered |
| CAD source priority | Tier 2 Sulzer Chemtech / Kenics public material → Tier 3 parametric helical-element fallback (Kenics geometry well-documented in literature) |
| defect injection count | 1 |
| defect injection hint | **D2** (over-dense mixer-element triangulation, 50k-100k tris per element) — A3 advisor stress-test, depends on case_009 outcome |

## Why Kenics static mixer as case_019 (Phase 4 #3 strategic role)

Static mixers are ubiquitous in chemical / polymer / food / pharma
process industries — RTD (residence time distribution) and COV
(coefficient of variation) are clean engineering KPIs:

1. **Direct case_003 inheritance**: simpleFoam machinery already
   validated. Scalar transport (passive tracer) is the NEW element.
2. **Process industry standard**: Kenics helical-element mixer is
   the recognized industry geometry. RTD F(t) curve is the
   universal mixer-quality KPI.
3. **D2 stress-test**: A3 advisor (geometry surgery) was
   validated by case_005 v1 with PARTIAL outcome (V17 redundancy
   gap). case_019 D2 = 50k-100k tris on mixer element = clean
   stress-test of A3 cross-case behavior. Outcome informs A3-v2
   sub-DEC priority.
4. **Phase 4 shortest case**: 8h effort. Direct inheritance keeps
   it tight; scalar transport adds modest infrastructure.

## Hard constraints (Codex must honor)

1. **Solver class**: `simpleFoam` steady + scalar transport
   equation (passive tracer T or species fraction Y). Document
   transport equation: `∇·(U φ) = ∇·(D_eff ∇φ)` with D_eff =
   ν_t / Sc_t + D_molecular. Sc_t = 0.7 (industry default).
2. **CAD source**: Tier 2 Sulzer / Kenics geometry from public
   material → Tier 3 parametric fallback (Kenics is well-
   documented: helical elements at 90° rotation between
   adjacent elements, aspect ratio L/D = 1.5).
3. **Geometry must be physically realistic** — Kenics spec:
   - Pipe inner diameter D = 50-100 mm
   - Number of elements N = 6-10 (typical industrial spec for
     RTD plug-flow approach)
   - Element length L = 1.5 D each
   - Element rotation: 90° between adjacent elements
   - Helical twist 180° within each element
   - Element thickness 1-2 mm
   - Upstream development length ≥ 3 D
   - Downstream development length ≥ 5 D (RTD measurement zone)
4. **Defect injection**: exactly 1 defect:
   - **D2**: over-dense triangulation on ONE mixer element (3rd
     element from inlet, e.g.). Baseline tessellation ~5k tris
     per element; D2 forces 50k-100k tris on the chosen element.
     Expected advisor: `geometry_surgery.decimate_to_tier`
     (LANDED, A3). Status depends on case_005 V17 outcome and
     case_009 D2 outcome (per dispatch plan B3 blocker).
5. **Patch naming**: `^[A-Za-z][A-Za-z0-9_]*$`.
6. **Single fluid region** + named patches:
   - patches: `pipe_inlet`, `pipe_outlet`, `pipe_wall`,
     `mixer_element_<i>` (i = 1..N), `inlet_tracer` (separate
     inlet for tracer pulse if Codex picks Dirac-pulse RTD)
7. **Operating point**: process-industry typical
   - Re = 1000-5000 (laminar to transitional; document choice)
   - Working fluid: water (industrial mixer typical) OR Newtonian
     viscous fluid for laminar regime
   - Tracer: passive scalar with same diffusion as water
   - Inlet velocity profile: developed (or document if uniform)
8. **Determinism**: CadQuery script byte-identical regeneration.
9. **Industrial flavor**: Kenics helical-element mixer.
10. **Reference data**:
    - RTD F(t) curve at outlet — F(t) = c(t)/c_∞ for step
      injection; expect plug-flow approach for N ≥ 6
    - COV at outlet — COV = σ_c / c_mean ≤ 0.05 typical mixer
      spec
    - Pressure drop Δp_per_element from Kenics correlation
    - CFD vs Kenics published correlation within ±15%

## Codex prompt (paste-ready)

```
You are Codex, acting as case 出题者 for the cfd-harness-unified
project. You design ONE industrial CFD case end-to-end.

## Project context

cfd-harness-unified at /Users/Zhuanz/Desktop/cfd-harness-unified/.
18 prior cases (002a/b + 003-018). You designed 004-018.
**case_019 is Phase 4 #3** — Kenics static mixer with scalar
transport. Process-industry classic. Extends case_003 to scalar
species/tracer.

## Required reading

1. .planning/methodology/codex_case_design_protocol.md
2. .planning/methodology/component_bank.md (E-class mixer)
3. .planning/methodology/public_cad_sources.md
4. .planning/methodology/kickoff/case_003_codex_response.md
   (incompressible-RANS pattern)
5. .planning/methodology/kickoff/case_009_codex_response.md
   (chemkinToFoam scalar species patterns; reference for
   scalar transport BC)
6. .planning/case_profiles/case_003_crm_hls_boundary_layer.md
7. .planning/methodology/industrial_case_solver_findings.md
   (V17 from case_005 — A3 redundancy gap; if case_009 D2
   sediment landed, additional A3 evidence)
8. .planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md
9. .planning/strategic/case_013_020_dispatch_plan_2026-05-08.md
   (B3 blocker: case_009 D2 outcome informs A3-v2 priority)
10. .planning/methodology/knowledge_status_convention.md

## Hard constraints

1. **Solver class**: simpleFoam steady + scalar transport
   equation. Sc_t = 0.7 industry default.
2. **CAD source**: Tier 2 Sulzer / Kenics public → Tier 3
   parametric fallback. Kenics dimensions well-documented.
3. **Geometry physical realism** — Kenics spec:
   - D = 50-100 mm
   - N = 6-10 elements
   - L_per_element = 1.5 D
   - 90° rotation between adjacent elements
   - 180° helical twist within element
   - Element thickness 1-2 mm
   - Upstream ≥ 3 D, downstream ≥ 5 D (RTD zone)
4. **Defect injection (REQUIRED 1 defect)**:
   - D2: over-dense triangulation on one element, 50k-100k tris
     vs baseline ~5k. Advisor=geometry_surgery.decimate_to_tier
     (A3 LANDED, V17 partial; cross-case behavior under test).
5. **Patch naming**: ^[A-Za-z][A-Za-z0-9_]*$.
6. **Operating point**: Re=1000-5000 (laminar/transitional;
   document choice). Water or Newtonian viscous fluid.
7. **Tracer/scalar**: passive scalar; document injection method
   (step / pulse / continuous).
8. **Industrial flavor**: Kenics helical mixer (process
   industry).
9. **Reference data**: RTD F(t), COV ± 15%, Δp ± 15% per
   Kenics correlation.
10. **NO Ahmed/NACA/Sajben** (Lane B).
11. **NO new defect categories** outside D1-D10.

## Your 5 deliverables

(same format as prior)

### 1. Engineering brief
- Component picked + bank ID + reasoning
- Engineering question (typical: "what is RTD F(t) + COV at
  outlet of N-element Kenics mixer at Re=Y, with as-installed
  D2 over-dense element defect?")
- Physics signature (simpleFoam + scalar, Re=1000-5000,
  Sc_t=0.7, laminar/transitional)
- Parts inventory (single fluid + N mixer elements + named
  patches)
- BC plan (inlet: flowRateInletVelocity OR fixedValue U with
  developed profile; outlet: pressureOutlet; walls: noSlip;
  scalar: T=1 at inlet for step injection or T=δ(t) for pulse;
  T=0 elsewhere; outlet: zeroGradient T)
- Expected metrics:
  - RTD F(t) curve at outlet (with step injection)
  - COV at outlet (= σ_c / c_mean)
  - Pressure drop per element + total Δp
  - Mixing visualization (scalar field + Q-criterion)
- Hypothesized failure modes:
  - case_003 inheritance (incompressible-RANS patterns)
  - V17 reproduction (A3 redundancy gap on D2 element)
  - NEW: scalar transport convergence vs flow convergence
    (T equation may converge slower than U)
  - NEW: laminar/transitional regime stability (Re=2300 boundary
    sensitivity)
  - NEW: helical-element meshing (curved surfaces require
    refined boundary layer)
  - NEW: COV time-averaging convergence
- Defect injection summary (D2 with verification)
- Sub-session estimated effort: 8h

### 2. CAD generation script (Python, executable)

CadQuery preferred (helical sweep + rotation between elements):
- Deterministic
- --out CLI with default
- Parametric constants (D_pipe, N_elements, L_element_factor,
  twist_angle_deg, rotation_between_elements_deg, element_thickness_mm,
  L_upstream_factor, L_downstream_factor, d2_target_element_index,
  d2_tessellation_target_tris, ...)
- Single fluid region body + named element patches
- Defect: D2 increase tessellation density on chosen element
- STEP export with named patches preserved

### 3. STEP file path

/Users/Zhuanz/Desktop/case_019_kenics_static_mixer/inputs/cad_codex_v1.step

### 4. Parts manifest YAML

- region: region_fluid (single)
- patches: full list with bc_type plan + scalar BC
- thermophysics: water Newtonian (or document alternate fluid)
- scalar_transport: passive scalar T, Sc_t=0.7,
  D_molecular_m2_s
- mixer operating point: Re, Q (flow), inlet U profile,
  injection method (step/pulse/continuous)
- Kenics correlation reference for predicted COV + Δp

### 5. Defect manifest YAML

- D2 over-dense tessellation:
  - target element index
  - baseline tessellation tri count
  - D2 target tri count (50k-100k)
  - expected advisor: geometry_surgery.decimate_to_tier (A3 LANDED)
  - status: depends on case_005 V17 + case_009 D2 outcomes
  - if A3 reliably surfaces D2 (case_009 confirmed): expected
    advisor PASS
  - if A3 still partial (V17 unresolved): expected PARTIAL +
    flag for A3-v2 sub-DEC priority

## Format your response

(same as prior)

## Round budget

Round 1 of 3.

## What you should NOT do

- Do NOT use turbulent k-ε for Re < 2300 laminar
- Do NOT skip scalar transport (defines the case)
- Do NOT use D1/D5/D6/D7/D8/D9 (D2 is the under-utilized choice
  for case_019)
- Do NOT skip RTD F(t) computation
- Do NOT exceed 8h sub-session effort

## Begin
```

## Validation checklist

- [ ] CAD source: Tier 2 / Tier 3 with rationale
- [ ] CadQuery script `python3 -m py_compile` passes
- [ ] All names ^[A-Za-z][A-Za-z0-9_]*$
- [ ] **Single fluid region** declared
- [ ] **N=6-10 helical elements** with documented rotation +
      twist
- [ ] **D=50-100 mm** pipe diameter
- [ ] D2 target element + tessellation count documented
- [ ] Operating point: Re=1000-5000, fluid documented
- [ ] **Scalar transport BC** documented (injection method)
- [ ] **Sc_t=0.7** documented
- [ ] RTD F(t) computation method specified
- [ ] COV computation method specified
- [ ] Reference (Kenics correlation) cited
- [ ] A3 advisor expected outcome documented (depends on V17 +
      case_009)

## After validation passes

(same as prior)

## Risk mitigations

- If Codex picks turbulent at low Re → revision request
- If Codex skips scalar transport → revision request
- If Codex picks D8 thin element → revision request (D2 is the
  case identity for A3 stress-test)
- If A3 outcome from case_009 has not landed when case_019
  dispatches: case_019 sediment may produce A3 cross-case
  V-finding (3rd data point); manage as discovery not failure
- If 86gs / CRS overload → fall back to other
