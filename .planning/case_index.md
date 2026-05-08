# Case Index

> **Multi-case tracker.** Established by DEC-V61-198 strategic pivot
> (2026-05-07). The project state is described by **which solver
> classes have a covered case running through it**, not by case
> count.
>
> Each row points at a `case_NNN_<name>.md` reference profile (or
> `.yaml` for gold-standard academic cases). Industrial cases live
> in dedicated desktop sandboxes; their reference profile in this
> repo is a pointer + summary, not a copy.

## Active threads

| case_id | Solver class | Case-thread location | Status | V-series source | Last touch |
|---|---|---|---|---|---|
| `case_002a_apu_bay_buoyant_simple` | Internal flow + buoyancy + forced convection | `~/Desktop/apu-bay-ventilation/` | active · v14 @ iter 813+ | V3-V13 | 2026-05-07 |
| `case_002b_apu_bay_cht` | CHT (multi-region + radiation) | `~/Desktop/apu-bay-ventilation-cht/` | active · v2 norad @ iter 67+ | V14-V15 | 2026-05-07 |
| `case_003_crm_hls_boundary_layer` | External high-Re + boundary layer (incompressible-RANS) | `~/Desktop/case_003_crm_hls_boundary_layer/` | **active · v1 paused at advisor-validation** (first 003-series sub-session executed 2026-05-08; CAD generation + D1+D8 ground-truth + A2 advisor first industrial cross-topology field-validation = PASS + thin_wall_advisor first cross-topology consistency = PASS; CFD pipeline deferred pending V20 unit-scale resolution) | V2 status upgrade + V10 status upgrade + V20 (HLPW6 unit-scale) + V21 (A2 cross-case divergence vs case_005 V19) | 2026-05-08 |
| `case_004_nrel_phase_vi_mrf` | Rotating machinery (MRF / sliding mesh) (incompressible-RANS-MRF) | `~/Desktop/case_004_nrel_phase_vi_mrf/` | **active · v1 paused at advisor-validation + MRF-infrastructure-design** (sub-session executed 2026-05-08; CAD generation 1.96 MB STEP + Tier-1 NREL/TP-500-29955 PDF cached 7.89 MB; D1+D8 ground-truth FreeCAD distToShape=0.30000 mm exact + bbox-min=0.75000 mm exact; A2 advisor 3rd cross-topology PASS via `_run_shared`; thin_wall_advisor 3rd cross-topology PASS @ severity=critical; V16 fragmentation pattern reproduced + new datum-frame fragmentation observed; MRFProperties Jinja2 template + 08b_write_mrf.py + 07b_audit_mrf.py NEW infrastructure ready; mesh + solver run pending for v2 sub-session) | V2 status upgrade (3rd PASS) + V10 status upgrade (3-case consistency) + **V22** (A2 rotating-machinery PASS) + **V23** (thin_wall rotating-machinery PASS) + **V24** (V16 reproduction + datum-frame additional finding) | 2026-05-08 |
| `case_005_rae_m2129_sduct` | Internal compressible subsonic-transonic diffuser (compressible-RANS) | `~/Desktop/case_005_rae_m2129_sduct/` | **active · v1 baseline + v2 V21 disambiguation + v2 CFD push** (v1: 52,078 cells, 144 s solver wall time, pseudo-steady oscillating per V18, AIP Mach 0.18 vs target 0.40-0.60, A2 + A3 v1 falsifications both = PARTIAL; v2 disambiguation 2026-05-08: **V21 closed**, **V19 superseded by V25**, **V25 NEW**; v2 CFD 2026-05-08 afternoon: rhoSimpleFoam 2000 iter, URF.p 0.20→0.10, URF.U 0.50→0.30, Sutherland — Ux residual dropped 30-70× (0.2-0.5 → 0.007-0.008), DC60 improved 0.351→0.264, AIP Mach 0.18→0.15, **but mass-flow asymmetry preserved at 2.8× → V18 reinforced + S13 sharpened: URF-only insufficient when totalPressure-inlet+fixedValue-outlet is the BC chain; v3 needs S13 path 1 OR path 3 OR mesh refinement**) | V16, V17, V18 (sharpened), V19 (superseded), V21 (closed), **V25 (NEW)** sourced; S13 (sharpened with v2 falsification), S14 playbook entries | 2026-05-08 |
| `case_006_onera_m6_transonic` | External transonic 3D wing (compressible-shock-density-based) | `~/Desktop/case_006_onera_m6_transonic/` | **active · v1 baseline complete** (sub-session executed 2026-05-08; CAD generation **with V26 fix-in-place** (Codex centered=True off-by-half-width formula bug) + D1+D4 ground truth (post-fix D1=0.35 mm exact; D4=0.180 mm exact) + A2 4th-of-5 V25 placeholder confirmation + thin_wall_advisor extreme-thinness PASS at 0.18 mm sliver (V30; extends V10/V23 to 5-case cross-topology spanning 3 orders of magnitude in thickness) + Codex defect→advisor mapping correction (V31; D4 thin_wall not geometry_surgery) + Tier-1 NASA Glenn HTTP 500 + SSL double-blocker workaround (V32; ONERA-D proxy = NACA 0010) + first density-based solver pipeline complete (rhoCentralFoam 5 ms physical, 663 s wall, Cl=0.250 / Cd=0.054, lambda-shock SMEARED-INDICATIVE: supersonic pocket M=1.18 captured at η=0.64 but pattern not resolved at 48k cells)) | **V26-V32 NEW** (Codex CAD off-by-half-width + rhoCentralFoam adjustTimeStep + symGaussSeidel + freestream BC + thin_wall extreme-thinness + Codex defect-mapping + Tier-1 source double-blocker), playbook S15 (NEW: rhoCentralFoam infrastructure root) | 2026-05-08 |
| `case_007_kcs_ship_vof` | Free-surface ship hydrodynamics (multiphase-VOF / interFoam) | `~/Desktop/case_007_kcs_ship_vof/` (sandbox not yet created) | **dispatched · DEFERRED** (round 2 of 2; first multiphase case; D8 thin_wall_advisor consistency check vs case_004) | (pending — first multiphase case; root-of-numerics-class) | 2026-05-08 |
| `case_008_glc305_irt_lagrangian` | External + Lagrangian icing (incompressible-RANS-Lagrangian) | `~/Desktop/case_008_glc305_irt_lagrangian/` | **active · v1 advisor-validation + Lagrangian-infrastructure design** (sub-session executed 2026-05-08; sandbox built with 10-body Codex CAD generator + parts/defect manifests + kinematicCloud writer hand-crafted case-locally + β(s/c) post-processor stub + 4-stage staged solver shell + advisor exercises: D8 thin_wall_advisor critical at 0.16 cells/thickness — 6th distinct industrial topology PASS → V10/V23/V30 status upgrade to **`[VALIDATED]`** + D1 A2 `_run_shared` matched=True with placeholder fields per V25 — 5th algorithm-path PASS for cross-topology consistency, gap-detection still pending V25 fix; CFD pipeline (cadquery STEP regen + simpleFoam + freeze + kinematicCloud + β extraction) deferred to v2 sub-session) | **V36** (NEW: A2 5th cross-topology algorithm-path PASS on incompressible-RANS-Lagrangian airfoil-mount), **V37** (NEW: thin_wall_advisor 6-topology arc closed at `[VALIDATED]`), V10/V23/V30 status upgrade, V33 reinforced; **S16** (NEW: Lagrangian-on-frozen-Eulerian decoupling pattern) | 2026-05-08 |
| `case_009_sandia_flame_d` | Reacting low-Mach piloted jet flame (reacting-low-Mach / reactingFoam + DRM-19) | `~/Desktop/case_009_sandia_flame_d/` | **active · v1 baseline complete** (sub-session executed 2026-05-08; sandbox built with 13-body Codex CAD generator + parts/defect manifests; D1=0.350mm distToShape PASS, D8=0.800mm bbox PASS; A2 6th-of-6 V25 placeholder confirmation on combustion-burner topology + thin_wall_advisor 6th cross-topology consistency; reacting infrastructure LANDED: blockMesh wedge (11.6k cells, 6 radial blocks), DRM-19 chemkinToFoam (after V38+V39+V41 patches), 21 species 0/Yi BCs, hePsiThermo+reactingMixture+sutherland+janaf+sensibleEnthalpy, PaSR+Cmix=1.0+EulerImplicit. Stage A cold-flow ran clean to t=0.005s (min/max(T)=[294,1880]K); Stage B ignite ran chemistry-on to t=0.0055s (T_max climbed 1880→1982K, heat-release in mixing layer). Full ramp deferred to v2 multi-hour budget. **5+ artifact extraction candidates** identified) | **V38-V42 NEW** (chemkinToFoam THERMO ALL + tran.dat END + transport-input dual-mode + GRI Tlow=300 clamp + A2 6th algorithm-path PASS), **S17 + S18 NEW** (reactingFoam infrastructure + staged startup playbook) | 2026-05-08 |
| `case_010_drivaer_fastback_les` | External transient LES vehicle aero (incompressible-LES / pimpleFoam + WALE) | `~/Desktop/case_010_drivaer_fastback_les/` (sandbox not yet created) | **dispatched · DEFERRED** (final case in original 10-case roster; 4-case D8 advisor consistency context) | (pending — first transient LES case; root-of-numerics-class) | 2026-05-08 |
| `case_011_plate_fin_compact_hx` | Multi-stream CHT (chtMultiRegionFoam steady; gas-turbine/APU air-air recuperator; steady-laminar-CHT-multi-stream NEW root) | `~/Desktop/case_011_plate_fin_compact_hx/` | **active · v1 advisor-validation + multi-region scaffolding** (sub-session 2026-05-09; CAD 5.5 MB STEP byte-deterministic + 3-region surface extraction + D8 thin_wall_advisor 7th cross-topology PASS severity=critical recommended_level=4 + D5 A2 `_run_shared` ALGORITHM_RUNS_CLEANLY [QUESTIONABLE 2026-05-08] reproducing V25 placeholders on HX plate-plate = 4th-data-point V25 confirmation; OF case scaffolded + sHM 980,618 cells with 86 illegal faces + splitMeshRegions **PARTIAL_FRAGMENTED** (region_hot_fluid in 312 connected components per V48/V50 prediction); chtMultiRegionFoam SKIPPED on broken mesh; v2 will bump fin refinement to (3,4) and re-run) | **V47-V50 NEW** (chtMultiRegionFoam multi-stream BC bookkeeping + sHM compact-fin snap cliff + A2 plate-plate algorithm-clean + thin_wall 7th cross-topology), **S22 + S23 candidates** (sHM compact-HX fin meshing + chtMultiRegionFoam multi-stream BC checklist), V25 4th confirmation, V10/V23/V30 status reinforced | 2026-05-09 |
| `case_012_hvac_supply_diffuser` | Industrial HVAC delivery (buoyantSimpleFoam single-region, 4-way ceiling diffuser commercial office; compressible-buoyant-RANS already-covered industrial-deployment form) | `~/Desktop/case_012_hvac_supply_diffuser/` | **active · v1 sediment 2026-05-09** (Phase 1 #2 closes Phase 1; sub-session executed: Codex 248-LOC CadQuery byte-deterministic STEP + V51 STEP timestamp canonicalization + 19 named bodies extracted + D1 0.350 mm distToShape PASS + D7 38.000° face-normal-dot PASS [first project D7] + A2 9th cross-topology PASS [V25 placeholder caveat applied]; sHM 1.16M cells + V52 minMedialAxisAngle key fix; **V53 NEW: Codex 3D-solid supply/return → sHM walls → sealed-room natural-convection v1 only**; v1.5/v2 fix path documented [createPatch carve OR thin-face CAD emission]) | **V49-V53 NEW** (A2 9th cross-topology PASS + D7 advisor-gap surfacer + STEP timestamp determinism + sHM minMedialAxisAngle key + Codex CAD inlet/outlet emission protocol gap), A6/A7/A8 artifact extraction drafts | 2026-05-09 |
| `case_013_centrifugal_pump_cavitating` | Confined rotating + phase-change (simpleFoam+MRF v1 / cavitatingFoam+Schnerr-Sauer v2; industrial water-treatment pump; incompressible-MRF-cavitating NEW root) | `~/Desktop/case_013_centrifugal_pump_cavitating/` (sandbox not yet created) | **dispatched · DEFERRED** (Phase 2 #1; first confined rotating + first phase-change for project; inherits case_004 MRF V22-V24; N=2900 rpm D2=250mm Q_BEP=0.080 m³/s H_BEP=35m; D1 10th cross-topology + **D7 2nd injection · accumulating advisor-gap evidence**) | (pending — first cavitation pipeline; **2nd backend fallback recovery** [VALIDATED 2-of-2 after case_011]; Codex round 2 of 3 · 86gs xhigh R0 + CRS high R1 fallback emit) | 2026-05-08 |
| `case_014_nasa_cc3_compressor_stage` | High-speed rotating + compressible (rhoSimpleFoam+MRF+cyclicAMI; NASA CC3 gold-standard centrifugal compressor; compressible-RANS-MRF NEW root) | `~/Desktop/case_014_nasa_cc3_compressor_stage/` (sandbox not yet created) | **dispatched · DEFERRED** (Phase 2 #2 closes Phase 2; gold-standard turbomachinery; combines case_004 MRF + case_005 compressible-RANS + case_013 confined-volute; 15 main + 15 splitter blades, R_TE=215.5 mm, U_tip=492 m/s, 21,789 rpm, PR=4.0; D1 11th cross-topology + **D8 8th [VALIDATED] cross-topology arc data point**) | (pending — first periodic-blade-row + cyclicAMI for project; longest sub-session in batch 14-18h; Codex round 1 · CRS gpt-5.4 high single-round emit 148k tok) | 2026-05-08 |
| `case_015_vattenfall_t_junction_thermal_striping` | LES + CHT compound (chtMultiRegionFoam WALE wall-modeled; Vattenfall OECD/NEA T-junction; nuclear primary loop fatigue topology; incompressible-LES-CHT NEW compound root) | `~/Desktop/case_015_vattenfall_t_junction/` (sandbox not yet created) | **dispatched · DEFERRED** (Phase 3 #1; first compound numerics root for project; combines case_002b CHT V14/V15 + case_010 LES; main ID=140 / branch ID=100 / 90° T / wall 6mm SS304; cold ṁ=9 @ 19°C / hot ṁ=6 @ 36°C; **D5 60μm weld misalignment 2nd D5 injection [QUESTIONABLE]**; ±2K mean / ±0.5K RMS) | (pending — first compound numerics root; LES+CHT joint statistics 5+10 flow-throughs; **12th D1/D5 cross-topology PASS pending A2-v2**; Codex round 1 · CRS gpt-5.4 high 160k tok with section-marker normalization) | 2026-05-08 |
| `case_016_m219_cavity_des_acoustic` | Transient compressible DES + acoustic (rhoPimpleFoam + k-ω-SST IDDES + FW-H far-field; M219 weapons-bay cavity; compressible-DES NEW compound root) | `~/Desktop/case_016_m219_cavity_des_acoustic/` (sandbox not yet created) | **dispatched · DEFERRED** (Phase 3 #2 closes Phase 3; first aeroacoustic capability; second compound numerics root combining case_006 V26-V32 + case_010 V45-V46; M=0.85 U=290 m/s; cavity 508×102×102 mm; **D6 first injection + D9 first injection — both advisor-gap markers**; published Rossiter modes 142/353/592/813 Hz; Codex flagged + corrected request math error on time-window — 0.75s for 100-cycle FFT) | (pending — first aeroacoustic for project; FW-H + IDDES + Rossiter mode infrastructure all-new; **D6+D9 advisor-gap V-findings will trigger harvest 003 A4-A8 evaluation**; Codex round 1 · CRS gpt-5.4 high single-round emit 228k tok) | 2026-05-08 |
| `case_017_pin_fin_electronic_heatsink` | Microscale CHT (chtMultiRegionFoam steady · 4 regions: air+chip+TIM+heatsink; CPU/GPU/IGBT/EV-battery cooling; chtMultiRegion at chip scale extends 002b) | `~/Desktop/case_017_pin_fin_electronic_heatsink/` (sandbox not yet created) | **dispatched · DEFERRED** (Phase 4 #1; bank ID `A1` re-anchored to original pin-fin meaning; 4-region 3-pair conjugate stack with TIM layer; heatsink 50×50×5mm, chip 10×10×0.7mm; Re_pin≈300-400 laminar/transitional; **D8 9th [VALIDATED] cross-topology arc + D9 2nd-3rd advisor-gap evidence**) | (pending — first solid-solid conjugate 3-pair stack; first chip-scale meshing for project; component_bank A1a/A1b split candidate; Codex round 1 · CRS gpt-5.4 high 157k tok with section-marker normalization) | 2026-05-08 |
| `case_018_stairmand_cyclone_separator` | 3D swirl + Lagrangian (pimpleFoam transient + LaunderGibsonRSTM + kinematicCloud one-way; Stairmand cyclone separator; incompressible-RANS-Lagrangian-swirl extends case_008) | `~/Desktop/case_018_stairmand_cyclone_separator/` (sandbox not yet created) | **dispatched · DEFERRED** (Phase 4 #2; first 3D swirl + first RSM for project; D=250mm Stairmand ratios; U_inlet=20 m/s Re=3.3e5 swirl S~1-3; particle 1-50μm silica; **D6 2nd injection · accumulating advisor-gap evidence after case_016 first**) | (pending — first RSM turbulence; PVC capture sensitivity; long-time d50 statistics ≥10 flow-throughs; Codex round 1 · CRS gpt-5.4 high 139k tok with section-marker normalization) | 2026-05-08 |
| `case_019_kenics_static_mixer` | Forced mixing + scalar transport (simpleFoam steady + passive scalar; 8-element Kenics helical static mixer; incompressible-RANS+scalar extends case_003) | `~/Desktop/case_019_kenics_static_mixer/` (sandbox not yet created) | **dispatched · DEFERRED** (Phase 4 #3; process-industry classic; D=80mm 8-element Kenics; Re=3200 transitional; **D2 A3 advisor cross-case stress-test [QUESTIONABLE V17]**; RTD F(t) + COV ≤ 0.05 + Δp Kenics correlation) | (pending — first scalar transport for project; A3 cross-case stability data point; Codex round 1 · CRS gpt-5.4 high 183k tok with section-marker normalization) | 2026-05-08 |
| `case_020_porous_media_filter_darcy_forchheimer` | Anisotropic porous resistance (simpleFoam + DarcyForchheimer fvOption; HEPA terminal filter cassette; incompressible-RANS+Darcy-Forchheimer extends case_003) | `~/Desktop/case_020_porous_media_filter/` (sandbox not yet created) | **dispatched · DEFERRED · FINAL CASE in 11-case industrial-extension batch** (Phase 4 #4; HEPA filter HVAC housing; U_face=2.5 m/s Re=3.3e4; anisotropic Darcy-Forchheimer; D9 2nd-3rd evidence + **D10 FIRST INJECTION closes defect-catalog gap analysis (D3+D4 carry to next batch)**) | (pending — first porous source for project; first D10; **triggers harvest cycle 003 full-mode** after sediment; Codex round 1 · CRS gpt-5.4 high 117k tok with section-marker normalization) | 2026-05-08 |

## Closed threads

(none yet)

## Pending solver-classes

Per DEC-V61-198 coverage map. Pull when concrete brief arrives — do
not pre-stage.

| Solver class | Status | Likely candidate when triggered |
|---|---|---|
| External flow + high-Re + boundary layer | 🟦 partial (case_003, v1 advisor-validation 2026-05-08; CFD deferred pending V20) | NASA/AIAA HLPW6 CRM-HLS |
| Rotating machinery (MRF / sliding mesh) | 🟦 partial (case_004, v1 advisor-validation + MRF-infrastructure 2026-05-08; CFD pipeline pending v2) | NREL Phase VI rotor (UAE) |
| Internal compressible diffuser | ✅ covered (case_005, v1 baseline 2026-05-08) | RAE M2129 S-duct |
| Compressible high-speed (shock-density-based) | ✅ covered (case_006, v1 baseline 2026-05-08; first density-based case for project) | ONERA M6 transonic wing |
| Multiphase / VOF | dispatched (case_007, deferred) | KCS ship hull (ITTC G2010) |
| Particle-laden / Lagrangian (icing) | dispatched (case_008, deferred) | NASA IRT GLC305 |
| Combustion / reacting flow | ✅ active (case_009 v1 baseline 2026-05-08) | Sandia Flame D (TNF) |
| Transient LES / DES | dispatched (case_010, deferred) | DrivAer fastback (TUM) |
| Multi-stream CHT (industrial heat exchanger) | dispatched (case_011, deferred · NEW root extending 002b CHT) | Plate-fin compact HX (gas-turbine/APU recuperator) |

## Gold-standard academic cases (reference fleet, not industrial)

See `case_profiles/*.yaml` — 10 frozen cases from the
project's earlier methodology phase. **Not the dogfood substrate
post-DEC-V61-198**; retained as verdict-tolerance fixtures only.

## Conventions

- **Naming**: `case_NNN_<short_name>.md` for industrial reference
  profiles. NNN is monotonically allocated; sub-letters (a/b/c)
  indicate parallel threads on the same physical case (different
  solver, different physics simplification, etc.).
- **Industrial references are pointers, not copies**: the
  reference profile in `.planning/case_profiles/` documents
  per-step wall times, V-series source, what's hand-coded vs reused
  — but the case files themselves stay in the desktop sandbox.
- **Gold-standard cases stay in YAML** (legacy schema with
  `risk_flags`, `tolerance_policy`); industrial cases stay in
  Markdown (no benchmark, narrative documentation).
- **Updating this index**: any time a case-thread starts, closes,
  or sediments a new V-series finding, append/update the row +
  bump "Last touch". Append-only for the "Closed threads" section.

## How a case gets a row

A case earns a row when it satisfies all three:
1. Has at least one full pipeline run (CAD → mesh → solve at least
   to first time-step)
2. Has produced at least one V-series finding (or validated an
   existing one)
3. Has a reference profile written under `.planning/case_profiles/`

A case is **closed** (move to "Closed threads") when:
- Final report exists in the case-thread sandbox
- All V-series findings backfilled into the index
- Any reusable engineering pattern is either extracted as a
  main-project artifact or filed as a deferred-extraction note
  in the reference profile

## Cross-references

- `solver_class` taxonomy: DEC-V61-198 §"Three pillars · P1"
- V-series finding format: `industrial_case_solver_findings.md`
- Solver convergence playbook: `solver_convergence_playbook.md`
- RAG corpus format (M6 prerequisite): `rag_corpus_format.md`
- Per-case ingestion checklist: DEC-V61-198 §"Six per-case standard moves"
