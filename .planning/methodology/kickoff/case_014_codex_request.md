# Codex Case-Design Request · case_014

> **Status**: PENDING — Codex round 1 not yet sent.
> **Phase**: Industrial Extension Phase 2 #2 per
> `.planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md`.
> **Strategic role**: True industrial turbomachinery — combines
> case_004 MRF + case_005 compressible-RANS into NASA CC3 centrifugal
> compressor stage. Establishes turbomachinery business credibility.
> **Backend**: 86gs gpt-5.5 xhigh primary (most complex turbomachinery
> case; longest in roster); CRS gpt-5.4 high fallback.
> **Soft blockers**: case_004 v2 sediment recommended (MRF clean) ·
> case_005 v2 sediment recommended (compressible BC patterns) ·
> A2-v2 ideally landed for D1 tip-clearance verification.

## Target

| field | value |
|---|---|
| case_id | `case_014_<short_name>` (Codex picks; suggested: `nasa_cc3_compressor_stage`) |
| solver_class_target | High-speed compressible rotating: `rhoSimpleFoam` + MRF (combines case_004 MRF + case_005 compressible-RANS) |
| numerics_class | compressible-RANS-MRF (NEW root — first true turbomachinery for project) |
| coverage map row to fill | "Industrial turbomachinery (compressor / turbine row)" — currently uncovered |
| CAD source priority | Tier 1 NASA CC3 (publicly fully-documented; expect HTTP 500 transient per case_005/006 pattern → plan caching) |
| defect injection count | 2 |
| defect injection hint | D1 (tip clearance critical, 0.2-0.5 mm — performance-determining for compressor) + D8 (thin blade leading edge, 0.6-0.8 mm — extends thin_wall_advisor cross-topology arc to turbomachinery) |
| sandbox path suggestion | `~/Desktop/case_014_nasa_cc3_compressor_stage/` |

## Why NASA CC3 as case_014 (Phase 2 #2 strategic role)

NASA CC3 centrifugal compressor stage is **turbomachinery CFD's
gold standard** — landing this gives the project credibility for
turbomachinery business (gas turbine / turbocharger / refrigeration /
aero engine boost stage):

1. **Combines 004 + 005 + 013**: MRF (case_004) + compressible-RANS
   (case_005) + confined volute (case_013). Maximum 3-case
   inheritance demonstration of Pattern 6.
2. **Tier-1 gold standard**: NASA CC3 is publicly fully-documented
   (geometry, total pressure ratio, isentropic efficiency,
   characteristic curve). Industry uses it as the validation
   benchmark.
3. **NEW physics**: tip-leakage flow, surge prediction, choke
   boundary, periodic blade-row boundaries (vs case_004's full
   360° model), total-total vs total-static reference state.
4. **Defect catalog**: D1 10th-or-11th injection extending to
   tip-leakage critical regime (industry-realistic 0.2-0.5 mm
   spec; 1% of impeller diameter); D8 7th-or-8th injection
   extending thin_wall_advisor arc to compressor blade LE.
5. **Longest case in batch**: 14-18h sub-session effort. Worth
   the investment because turbomachinery is high-value
   industrial-service work.

## Hard constraints (Codex must honor)

1. **Solver class**: `rhoSimpleFoam` + MRF steady. v1 = single
   operating point at design speed/pressure ratio (PR_design).
   v2 = characteristic curve (5-7 operating points spanning
   choke / design / surge boundaries). Document v1 → v2
   transition criteria.
2. **CAD source**: Tier 1 NASA CC3 reference geometry. Document
   source URL + caching strategy (expect HTTP 500 per case_005/006
   pattern; provide bake-into-script fallback). License: NASA
   public domain — no redistribution issue.
3. **Geometry must be physically realistic** — based on NASA CC3:
   - **Impeller**: 15 main blades + 15 splitter blades (NASA CC3
     spec) OR documented variant; D2 ≈ 215 mm
   - **Diffuser**: vaneless or vaned; document choice (NASA CC3
     uses vaned diffuser)
   - **Periodic blade-row boundary**: model ONE main+splitter
     passage with rotational periodicity (24°/30 = 12° wedge for
     30-blade-equivalent count; document choice)
   - **Tip clearance**: realistic 0.2-0.5 mm baseline (typical
     1% of D2)
   - **Inlet plenum**: axial inlet with realistic upstream length
     (≥ 2× D2)
   - **Outlet collector**: vaneless space + diffuser → exit plenum
4. **Defect injection**: exactly 2 defects from catalog. Required
   set:
   - **D1**: tip clearance gap defect on ONE blade, +0.2-0.4 mm
     additional gap beyond nominal (real wear-induced or
     manufacturing out-of-tolerance defect). Apply
     [QUESTIONABLE 2026-05-08] marker per V25.
   - **D8**: thin LE on ONE blade, 0.6-0.8 mm leading-edge
     thickness vs nominal. Expected advisor: thin_wall_advisor
     (LANDED, 6-of-6 [VALIDATED]; case_014 is 7th-or-8th
     cross-topology arc data point).
5. **Patch naming**: all body names `^[A-Za-z][A-Za-z0-9_]*$`.
6. **Periodic boundary handling**: parts manifest MUST declare
   - rotational `periodic_lower` and `periodic_upper` patches
   - matching face transformation angle
   - sub-session writes `cyclicAMI` or `cyclic` BC
7. **Operating point**: NASA CC3 design point
   - N (rotation): 21,789 rpm (design speed)
   - PR_design: 4.0 (total pressure ratio)
   - mass flow: 4.54 kg/s (design)
   - inlet conditions: T0 = 293.15 K, P0 = 101.325 kPa
   - turbulence model: k-ω-SST (industry standard for
     turbomachinery; document over k-ε)
8. **Determinism**: CadQuery script byte-identical regeneration.
9. **Industrial flavor**: NASA CC3 is recognizable industrial
   turbomachinery; do NOT genericize.
10. **Reference data**: PR(ṁ) characteristic curve at 5-7 points,
    η_isentropic at design point, surge margin %, choke ṁ.
    CFD vs NASA published within ±5% PR at design, ±3% η.

## Codex prompt (paste-ready)

```
You are Codex, acting as case 出题者 (case designer) for the
cfd-harness-unified project. The project main session is asking
you to design ONE industrial CFD case end-to-end so a Claude Code
sub-session can execute it.

This is your design task, not your solver task. You design; the
sub-session runs.

## Project context (read first)

cfd-harness-unified is a CFD harness over OpenFOAM at
/Users/Zhuanz/Desktop/cfd-harness-unified/. Per DEC-V61-198
(2026-05-07 strategic charter), the project's development
philosophy is "container that accumulates industrial CFD
experience".

13 prior cases (original 10-case roster + Phase 1 + case_013):
- case_002a/b: APU bay buoyant + CHT
- case_003-010: original roster
- case_011: plate-fin compact HX (multi-stream CHT)
- case_012: HVAC supply diffuser (buoyantSimpleFoam)
- case_013: centrifugal pump + cavitation (incompressible-MRF-cavitating)

You designed case_004 through case_013. **case_014 is Phase 2 #2** —
NASA CC3 centrifugal compressor stage. This is the project's
gold-standard turbomachinery case combining MRF (004) +
compressible-RANS (005) + confined volute (013). Establishes
turbomachinery industry credibility.

## Required reading (in cfd-harness-unified repo)

1. .planning/methodology/codex_case_design_protocol.md
2. .planning/methodology/component_bank.md (D-class compressor)
3. .planning/methodology/public_cad_sources.md (NASA CC3 Tier-1)
4. .planning/methodology/kickoff/case_004_codex_response.md (MRF)
5. .planning/methodology/kickoff/case_005_codex_response.md
   (compressible-RANS BC patterns)
6. .planning/methodology/kickoff/case_006_codex_response.md (NASA
   Tier-1 HTTP 500 caching pattern)
7. .planning/methodology/kickoff/case_013_codex_response.md
   (confined-volute MRF)
8. .planning/case_profiles/case_004_nrel_phase_vi_mrf.md
9. .planning/case_profiles/case_005_rae_m2129_sduct.md
10. .planning/methodology/industrial_case_solver_findings.md
    (V22-V32 inheritance from MRF + compressible cases)
11. .planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md
12. .planning/strategic/case_013_020_dispatch_plan_2026-05-08.md
13. .planning/methodology/knowledge_status_convention.md

## Hard constraints

1. **Solver class**: rhoSimpleFoam + MRF steady. v1 design point
   only; v2 characteristic curve (5-7 points spanning choke /
   design / surge).
2. **CAD source**: Tier 1 NASA CC3 (15 main + 15 splitter blades
   per NASA spec; D2 ≈ 215 mm). Cache strategy for HTTP 500
   transient per case_005/006 lessons.
3. **Geometry physical realism**:
   - Impeller per NASA CC3 spec
   - Vaned diffuser (CC3 uses vaned)
   - Periodic blade-row boundary (one passage with rotational
     periodicity, not full 360°)
   - Tip clearance baseline 0.2-0.5 mm (industry typical 1% D2)
   - Axial inlet plenum ≥ 2× D2
   - Outlet collector + vaneless space + vaned diffuser
4. **Defect injection (REQUIRED 2 defects)**:
   - D1: +0.2-0.4 mm additional tip-clearance gap on ONE blade.
     Apply [QUESTIONABLE 2026-05-08] per V25.
   - D8: 0.6-0.8 mm leading-edge thickness on ONE blade. Advisor=
     thin_wall_advisor (LANDED, 6-of-6 [VALIDATED]).
5. **Patch naming**: ^[A-Za-z][A-Za-z0-9_]*$.
6. **Periodic boundary**: rotational periodic_lower + periodic_upper
   patches with matching transformation. Sub-session writes
   cyclicAMI or cyclic BC.
7. **Operating point**: NASA CC3 design point (21,789 rpm, PR=4.0,
   ṁ=4.54 kg/s, T0=293.15 K, P0=101.325 kPa).
8. **Turbulence model**: k-ω-SST (document over k-ε for
   turbomachinery).
9. **Industrial flavor**: NASA CC3 turbomachinery; gas turbine /
   turbocharger / aero engine boost stage applicability.
10. **Reference data**: PR ± 5% at design, η ± 3% at design,
    surge margin %, choke ṁ.
11. **NO Ahmed/NACA/Sajben** (Lane B).
12. **NO new defect categories** outside D1-D10.

## Your 5 deliverables

(same format as case_011/012/013)

### 1. Engineering brief
- Component picked + bank ID + reasoning
- Engineering question (typical: "what is the PR-η-surge-choke
  characteristic at design speed with as-installed tip-clearance
  + LE-thickness defects?")
- Physics signature (rhoSimpleFoam + MRF, k-ω-SST, Re_blade
  ~1e6, M_tip ~ 0.8-1.0)
- Parts inventory (region_fluid + MRF cellZone + periodic
  patches + tip clearance + diffuser vanes)
- BC plan (inlet plenum: totalPressure + totalTemperature;
  outlet: pressureOutlet at design back-pressure for v1, varied
  for v2 char curve; blade walls: rotating wall in MRF zone;
  shroud: rotating + tip-leakage gap; periodic: cyclicAMI)
- Expected metrics: PR(ṁ), η(ṁ), surge margin, choke ṁ, tip-
  leakage flow visualization at design, supersonic pocket map
  if present
- Hypothesized failure modes:
  - V22 inheritance (MRF rotation patterns)
  - V18 inheritance (compressible mass-flow asymmetry from
    case_005)
  - NEW: tip-leakage capture grid sensitivity
  - NEW: surge prediction sensitivity to back-pressure ramp rate
  - NEW: periodic boundary face matching tolerance
  - NEW: total-total vs total-static reference state ambiguity
  - NEW: choke-boundary mass-flow numerical limit
- Defect injection summary
- Sub-session estimated effort: 14-18h

### 2. CAD generation script (Python, executable)

CadQuery preferred:
- Deterministic
- --out CLI with default
- Parametric constants (n_main_blades, n_splitter_blades, D2,
  blade_angle_inlet_main, blade_angle_outlet, blade_angle_inlet_splitter,
  splitter_position, vaneless_radius, n_diffuser_vanes, diffuser_angle,
  tip_clearance_baseline_mm, d1_tip_gap_offset_mm, d8_blade_index,
  d8_le_thickness_mm, periodic_angle_deg, ...)
- Comments at decision points
- Single fluid region body (one passage with periodic boundaries)
  + named patches (each blade, each blade tip, hub, shroud,
  diffuser vanes, inlet plenum, outlet collector, periodic_lower,
  periodic_upper)
- Defect injection: D1 enlarges tip clearance on blade_<i>;
  D8 thins LE of blade_<j>
- STEP export with named patches preserved (cq.Solid.fuse() per
  V16/V24)

### 3. STEP file path

/Users/Zhuanz/Desktop/case_014_nasa_cc3_compressor_stage/inputs/cad_codex_v1.step

### 4. Parts manifest YAML

- region: region_fluid (single)
- mrf_zone: cellZone with axis (z) + omega (21,789 rpm)
- periodic: periodic_lower / periodic_upper with rotation angle
- patches: full list with bc_type plan
- thermophysics: air ideal gas with Sutherland viscosity
- compressor operating point: N, ṁ_design, PR_design, η_target,
  surge_margin_%, choke_ṁ
- reference: NASA CC3 publication citation (bake-into-script
  per case_006 license-clean strategy)

### 5. Defect manifest YAML

- D1 [QUESTIONABLE 2026-05-08] (A2 v1 cannot field-validate;
  A2-v2 draft pending)
- D8 thin_wall_advisor [VALIDATED 6-of-6] (case_014 = 7th-or-8th
  cross-topology arc; expected critical warning)

## Format your response

(same as prior cases)

## Round budget

Round 1 of 3.

## What you should NOT do

- Do NOT propose full 360° model (use periodic single-passage)
- Do NOT skip diffuser (CC3 has vaned diffuser, not vaneless)
- Do NOT use k-ε for turbomachinery (document k-ω-SST choice)
- Do NOT use chtMultiRegionFoam (single-region + MRF cellZone)
- Do NOT propose D7 (case_013 covers D7; 014 uses D8 to extend
  thin_wall arc)
- Do NOT skip surge / choke boundary handling rationale
- Do NOT exceed 18h estimated sub-session effort

## Begin
```

## Validation checklist (main session runs after Codex responds)

- [ ] CAD source picked (Tier 1 NASA CC3, caching strategy
      documented)
- [ ] CadQuery script `python3 -m py_compile` passes
- [ ] All patch + region names satisfy ^[A-Za-z][A-Za-z0-9_]*$
- [ ] **Single region_fluid** with **MRF cellZone** declared
- [ ] **Periodic boundary** declared with rotation angle
- [ ] **15 main + 15 splitter blades** OR documented CC3 variant
- [ ] **Vaned diffuser** present with documented vane count
- [ ] **Tip clearance baseline** declared (0.2-0.5 mm)
- [ ] D1 tip-gap defect: +0.2-0.4 mm additional, [QUESTIONABLE]
- [ ] D8 thin LE: 0.6-0.8 mm, advisor=thin_wall_advisor
- [ ] Both defects OUTSIDE the design-PR comparison zone
- [ ] Operating point matches NASA CC3 (21,789 rpm, PR 4.0,
      ṁ 4.54 kg/s)
- [ ] **k-ω-SST** turbulence model documented (over k-ε)
- [ ] v1 → v2 transition criteria explicit (design point → char
      curve)
- [ ] Total-total vs total-static reference state documented

## After validation passes

(same as prior cases)

## Risk mitigations

- If Codex returns full 360° → revision request with periodic
  passage
- If Codex picks vaneless diffuser → challenge in revision (CC3
  has vaned)
- If Codex skips surge/choke → revision request with v2
  characteristic curve
- If Codex uses k-ε → revision request (k-ω-SST industry standard)
- If 86gs gpt-5.5 503/429 → fall back to CRS gpt-5.4 high
  (this is the most complex case; CRS may struggle with the
  detail; expect possible round 2 if fallback used)
