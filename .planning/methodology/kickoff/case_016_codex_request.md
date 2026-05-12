# Codex Case-Design Request · case_016

> **Status**: PENDING — Codex round 1 not yet sent.
> **Phase**: Industrial Extension Phase 3 #2 per
> `.planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md`.
> **Strategic role**: First aeroacoustic capability for project —
> M219 cavity DES + FW-H acoustic post-processing. Combines
> case_006 compressible-shock + case_010 LES into compressible-DES
> compound root.
> **Backend**: 86gs gpt-5.5 xhigh primary (DES + acoustic complexity);
> CRS gpt-5.4 high fallback.
> **Soft blockers**: case_006 v1 sediment available (rhoCentralFoam
> infrastructure indexed) · case_010 LES sediment helpful · D6 + D9
> are first injections; advisor-gap V-findings expected.

## Target

| field | value |
|---|---|
| case_id | `case_016_<short_name>` (Codex picks; suggested: `m219_cavity_des_acoustic`) |
| solver_class_target | Transient compressible DES + acoustic: `rhoPimpleFoam` + DDES (k-ω-SST IDDES variant). FW-H far-field at single observer point |
| numerics_class | compressible-DES (NEW root — compound from 006 + 010) |
| coverage map row to fill | "Aeroacoustics (cavity / weapons bay / landing gear bay / pantograph / sunroof)" — currently uncovered |
| CAD source priority | Tier 1 M219 cavity (UK MOD public data complete; QinetiQ archive; check URL accessibility) OR NASA cavity database |
| defect injection count | 2 |
| defect injection hint | **D6 (debris in cavity)** — UNCOVERED in 003-012 roster + **D9 (faceted curved walls)** — UNCOVERED in 003-012 roster |
| sandbox path suggestion | `~/Desktop/case_016_m219_cavity_des_acoustic/` |

## Why M219 cavity as case_016 (Phase 3 #2 strategic role)

Project currently has **zero aeroacoustic capability**. Aircraft
weapons-bay / landing-gear-bay / automotive sunroof / high-speed
train pantograph all share the cavity-flow + tonal-noise pattern.
M219 is the cleanest entry point:

1. **Compound root verification (compressible + DES)**: case_006
   established compressible-shock; case_010 will establish LES.
   case_016 confirms compressible+turbulence-resolved compose
   into DES. Compound-root validation is critical for
   industrial DES adoption.
2. **Industrial relevance**: aeroacoustic CFD is one of the
   fastest-growing CFD service areas (auto NVH, aero-acoustic
   certification, EV motor noise prediction adjacent). M219 is
   the recognized validation benchmark.
3. **Defect catalog rebalance**: D6 (debris) and D9 (faceted
   curved) are 0/12 injected. case_016 fills both gaps. Both
   first injections will surface advisor-gap V-findings.
4. **FW-H infrastructure**: new post-processor
   `FW_H_acoustic_writer.py` + `rossiter_mode_post_processor.py`
   + `frequency_spectrum_extractor.py`. Reusable for case_018
   cyclone (low-frequency rumble) and any future
   aeroacoustic case.
5. **Highest-value Phase 3 case**: pairs with case_015
   (LES+CHT) as the two compound-root verification cases. After
   both land, the harness is credible for compound-physics
   industrial work.

## Hard constraints (Codex must honor)

1. **Solver class**: `rhoPimpleFoam` transient + DDES (k-ω-SST
   IDDES variant or Spalart-Allmaras DDES — Codex picks; document
   choice). FW-H acoustic surface integration at far-field
   observer (single observer at standard location for benchmark
   comparison).
2. **CAD source**: Tier 1 M219 cavity (L=20 inch, W=4 inch, D=4
   inch — typical M219 spec; document exact source URL and
   caching strategy per case_006 lessons; license: UK MOD public,
   bake-into-script for reproducibility). Alternative: NASA
   cavity database if M219 URL blocks.
3. **Geometry must be physically realistic**:
   - **Cavity**: rectangular, M219 spec L:W:D = 5:1:1
     (508 × 102 × 102 mm typical)
   - **Upstream boundary layer plate**: ≥ 6× cavity length
     upstream of cavity leading edge (boundary-layer development)
   - **Downstream plate**: ≥ 4× cavity length downstream
   - **Side plates**: width ≥ 4× cavity width on each side
   - **Far-field box**: large enough to avoid acoustic boundary
     reflection (≥ 30× cavity length total domain length;
     non-reflective BC at outer boundaries)
4. **Defect injection**: exactly 2 defects from catalog. Required
   set:
   - **D6**: debris body (small block, 5-15 mm cube) inside
     cavity at random documented location. UNCOVERED in 003-012;
     no LANDED advisor for "extra body in fluid region" pattern.
   - **D9**: faceted curved walls — replace the cavity LE / TE
     curved fillet with faceted approximation (12-24 facets per
     90° instead of smooth curve). UNCOVERED in 003-012; no
     LANDED advisor for "curved-surface tessellation accuracy"
     pattern.
5. **Patch naming**: `^[A-Za-z][A-Za-z0-9_]*$`.
6. **Single fluid region** + named patches:
   - patches: `cavity_floor`, `cavity_le_wall`, `cavity_te_wall`,
     `cavity_side_wall_starboard`, `cavity_side_wall_port`,
     `flat_plate_upstream`, `flat_plate_downstream`,
     `flat_plate_side_starboard`, `flat_plate_side_port`,
     `inflow`, `outflow`, `top_far_field`,
     `debris_cube` (D6), `cavity_le_faceted` (D9 if separate
     patch needed)
7. **Operating point**: M219 standard
   - M_inf = 0.85 (subsonic compressible, typical M219 case)
   - U_inf ≈ 290 m/s at altitude
   - T_inf = 273.15 K
   - Re_L (cavity length) ≈ 6e6
   - turbulence: k-ω-SST IDDES (or SA-DDES alternate)
8. **Acoustic configuration**:
   - FW-H surface: porous control surface around cavity,
     positioned in resolved-turbulence region (typical 1-2 cavity
     L from cavity floor)
   - Observer: single far-field point (e.g., 8 m from cavity
     center at 90° elevation — document exact position)
   - Sample rate: ≥ 2× expected highest-frequency Rossiter mode
     (Rossiter mode 4 ≈ 1500 Hz at M219 condition → ≥ 3000 Hz
     sample rate → dt ≤ 3.3e-4 s; recommended dt ~ 1e-5 to 1e-4 s
     for CFL ≤ 1)
   - Time window: ≥ 0.1 s (covers ≥ 100 cycles of fundamental
     Rossiter mode at ~1000 Hz)
9. **Determinism**: CadQuery script byte-identical regeneration.
10. **Industrial flavor**: M219 weapons bay (military aerospace);
    do NOT genericize.
11. **Reference data**: Rossiter mode frequencies (modes 1-4),
    SPL spectrum at floor center (M219 published Kulite 5/9
    pressure transducer locations), drag increment vs flat
    plate. CFD vs M219 published within ±3 dB SPL, ±5% Rossiter
    frequency.

## Codex prompt (paste-ready)

```
You are Codex, acting as case 出题者 for the cfd-harness-unified
project. You design ONE industrial CFD case end-to-end.

## Project context

cfd-harness-unified at /Users/Zhuanz/Desktop/cfd-harness-unified/.
15 prior cases (002a/b + 003-015). You designed 004-015.
**case_016 is Phase 3 #2** — first aeroacoustic case for project.
M219 cavity DES + FW-H acoustic. Compound root: compressible-DES
(combines case_006 compressible-shock + case_010 LES).

## Required reading

1. .planning/methodology/codex_case_design_protocol.md
2. .planning/methodology/component_bank.md (E-class cavity)
3. .planning/methodology/public_cad_sources.md (Tier 1 M219)
4. .planning/methodology/kickoff/case_006_codex_response.md
   (rhoCentralFoam + Tier 1 NASA HTTP 500 caching)
5. .planning/methodology/kickoff/case_010_codex_response.md (LES)
6. .planning/case_profiles/case_006_onera_m6_transonic.md
7. .planning/methodology/industrial_case_solver_findings.md
   (V26-V32 from case_006; LES findings from case_010 if
   sedimented)
8. .planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md
9. .planning/strategic/case_013_020_dispatch_plan_2026-05-08.md
10. .planning/methodology/knowledge_status_convention.md

## Hard constraints

1. **Solver class**: rhoPimpleFoam + DDES (k-ω-SST IDDES preferred;
   SA-DDES alternate). FW-H surface integration; far-field
   observer at standard position.
2. **CAD source**: Tier 1 M219 cavity (L:W:D = 5:1:1, typical
   508×102×102 mm). UK MOD public; bake-into-script per case_006
   strategy. NASA cavity DB acceptable if M219 URL blocks.
3. **Geometry physical realism**:
   - M219 cavity dimensions per spec
   - Upstream boundary-layer plate ≥ 6× cavity length
   - Downstream plate ≥ 4× cavity length
   - Side plates ≥ 4× cavity width each side
   - Far-field domain ≥ 30× cavity length total
   - Non-reflective BC at outer boundaries
4. **Defect injection (REQUIRED 2 defects)**:
   - D6: debris cube (5-15 mm) inside cavity at documented
     location. UNCOVERED defect; no LANDED advisor.
   - D9: faceted curve at LE/TE (12-24 facets per 90°).
     UNCOVERED defect; no LANDED advisor.
5. **Patch naming**: ^[A-Za-z][A-Za-z0-9_]*$.
6. **Operating point**: M219 standard (M=0.85, U≈290 m/s, T=273.15 K,
   Re_L ≈ 6e6).
7. **Turbulence model**: k-ω-SST IDDES preferred; document
   alternate.
8. **Acoustic configuration**:
   - FW-H porous surface in resolved-turbulence region
   - Single far-field observer
   - dt ~ 1e-5 to 1e-4 s (CFL ≤ 1, sample ≥ 3 kHz)
   - Time window ≥ 0.1 s (≥ 100 fundamental cycles)
9. **Industrial flavor**: M219 weapons bay; military aerospace
   recognizable.
10. **Reference data**: Rossiter modes 1-4, SPL ±3 dB, Rossiter
    freq ±5%, drag increment.
11. **NO Ahmed/NACA/Sajben** (Lane B).
12. **NO new defect categories** outside D1-D10.
13. **NO 2D simplification** (cavity is 3D; spanwise turbulence
    matters).

## Your 5 deliverables

(same format as prior cases)

### 1. Engineering brief
- Component picked + bank ID + reasoning
- Engineering question (typical: "what are Rossiter mode
  frequencies + SPL at standard observer for M219 cavity at
  M=0.85, with as-installed debris + faceted-LE defects?")
- Physics signature (rhoPimpleFoam + IDDES, M=0.85,
  Re_L=6e6, k-ω-SST IDDES, FW-H acoustic post-processing)
- Parts inventory (single fluid region + named patches +
  D6 debris body + D9 faceted patches)
- BC plan (inflow: characteristicVelocityInletOutletVelocity
  M=0.85; outflow: waveTransmissive; cavity walls: noSlip;
  flat plates: noSlip; far-field top: waveTransmissive or
  zeroGradient with non-reflective treatment)
- Expected metrics:
  - Rossiter modes 1-4 frequencies (M219 published values)
  - SPL spectrum at Kulite 5/9 (cavity floor, document
    coordinates per M219 spec)
  - Drag increment vs flat plate baseline
  - FW-H far-field SPL at observer
- Hypothesized failure modes:
  - V26-V32 inheritance from case_006
  - V-findings from case_010 LES
  - NEW: tonal noise capture vs grid resolution (cavity LE
    refinement critical)
  - NEW: FW-H surface placement sensitivity (inside resolved
    turbulence region required)
  - NEW: time-window length for FFT convergence (≥ 100
    fundamental cycles)
  - NEW: boundary acoustic reflection at outflow / far-field
    (non-reflective BC infrastructure)
  - NEW: D6 advisor-gap (extra-body-in-fluid detection)
  - NEW: D9 advisor-gap (faceted-vs-smooth curved-surface
    detection)
- Defect injection summary
- Sub-session estimated effort: 12-14h

### 2. CAD generation script (Python, executable)

CadQuery preferred:
- Deterministic
- --out CLI with default
- Parametric constants (cavity_L, cavity_W, cavity_D,
  upstream_plate_L, downstream_plate_L, side_plate_W,
  far_field_box_L, debris_size_mm, debris_position_xyz_mm,
  facet_count_per_90deg, le_fillet_baseline_mm, ...)
- Single fluid region body + named patches
- Defect injection: D6 debris cube; D9 faceted LE/TE
  approximation
- STEP export with named patches preserved (cq.Solid.fuse() per
  V16/V24)

### 3. STEP file path

/Users/Zhuanz/Desktop/case_016_m219_cavity_des_acoustic/inputs/cad_codex_v1.step

### 4. Parts manifest YAML

- region: region_air
- patches: full list with bc_type plan
- thermophysics: air ideal gas Sutherland
- M219 operating point: M, U, T, Re_L, altitude reference
- IDDES config: model, dt, sample rate
- FW-H config: surface position, observer position, sample
  rate, time window
- reference: M219 publication citation; bake-into-script

### 5. Defect manifest YAML

- D6 [QUESTIONABLE 2026-05-08] (no LANDED advisor for
  extra-body-in-fluid; flag advisor-gap V-finding;
  manual FreeCAD body-count + bbox check)
- D9 [QUESTIONABLE 2026-05-08] (no LANDED advisor for
  curved-surface tessellation accuracy; flag advisor-gap
  V-finding; manual chord-length / facet-count comparison)

## Format your response

(same as prior)

## Round budget

Round 1 of 3.

## What you should NOT do

- Do NOT skip FW-H acoustic post-processing (defines the case)
- Do NOT use steady solver (DES is transient)
- Do NOT use 2D simplification (cavity 3D spanwise required)
- Do NOT use rhoCentralFoam (case_006 territory; 016 is
  rhoPimpleFoam transient)
- Do NOT use D1/D8 (D6/D9 are the under-utilized choices for
  case_016)
- Do NOT skip non-reflective BC for far-field (acoustic
  reflection contaminates spectrum)
- Do NOT exceed 14h sub-session effort

## Begin
```

## Validation checklist

- [ ] CAD source picked (Tier 1 M219, caching documented)
- [ ] CadQuery script `python3 -m py_compile` passes
- [ ] All names ^[A-Za-z][A-Za-z0-9_]*$
- [ ] **Single fluid region** declared
- [ ] **M219 dimensions** per spec (L:W:D = 5:1:1)
- [ ] **Boundary-layer development length** ≥ 6× cavity L
- [ ] **Far-field box** ≥ 30× cavity L
- [ ] **Non-reflective BC** at outer boundaries
- [ ] D6 debris cube: 5-15 mm, position documented, advisor=NONE
- [ ] D9 faceted curve: 12-24 facets per 90°, advisor=NONE
- [ ] Operating point matches M219 (M=0.85, U≈290 m/s, T=273.15K)
- [ ] **k-ω-SST IDDES** documented
- [ ] **FW-H surface** position documented
- [ ] **Far-field observer** position documented
- [ ] dt ≤ 1e-4 s (CFL ≤ 1, ≥ 3 kHz sample)
- [ ] Time window ≥ 0.1 s
- [ ] Reference data (Rossiter modes + SPL ±3 dB) documented
- [ ] D6 and D9 first injections — advisor-gap V-findings flagged

## After validation passes

(same as prior cases)

## Risk mitigations

- If Codex picks 2D simplification → revision request (3D required)
- If Codex skips FW-H → revision request (defines the case)
- If Codex picks rhoCentralFoam → revision request (rhoPimpleFoam
  for transient DES)
- If Codex uses standard k-ω-SST RANS instead of IDDES → revision
  request
- If 86gs gpt-5.5 503/429 → fall back to CRS gpt-5.4 high
  (DES + acoustic complexity; CRS may need round 2)
