# Canonical Eval Set · V66-B AI Advisor Stack Build-out

> 30-case canonical eval set for AI advisor regression protection. Each case has known V-row attribution + expected advisor rule firings. Per V64-A V130 thesis + V132 collapse (Claude Code session = AI advisor).
>
> **Established**: 2026-05-16 (V66-B B100 charter execution · DEC-V66-B-charter)
> **Format**: 1 file per case · YAML frontmatter for machine readability · Markdown body for human readability
> **Purpose**: Done #2 + #3 + #4 of V66-B (eval set + regression protection + SDK reproducibility)

---

## 30-case selection criteria

1. ≥1 case per LANDED V101-V107 row (7 cases minimum)
2. ≥3 cases for V51-V100 carry-forward witnesses
3. ≥5 cases for F-NEW candidate scenarios (1st-observation tracking)
4. Multi-physics coverage: incompressible BL · compressible transonic · rotor MRF · thermo-FPE · separation · transition · industrial CHT
5. Each case documents:
   - Expected V-row attribution (which V-rows the case is an instance of)
   - Expected advisor rule firings (which of 11+ rules SHOULD fire)
   - Expected advisor verdict signature
   - Sandbox path (if extant) for reproducibility

---

## Eval case roster (30 cases)

### Group A · V101-V107 LANDED V-row witnesses (7 cases)

| # | Case ID | V-row | Physics regime | Expected advisors firing |
|---|---|---|---|---|
| E01 | case_004_v4 NREL Phase VI MRF | V101 (chord-axis convention) | rotor MRF incompressible | face_orientation, urf_advisor, solver_block_advisor |
| E02 | case_021_v65 NASA TMR flat plate | V103 (Cf-canonical-choice) | incompressible TBL | inlet_outlet_validator, solver_block_advisor, unit_detector |
| E03 | case_022_v64 Driver-Seegmiller BFS | V104 (kOmegaSST separation under-pred) | incompressible separation | inlet_outlet_validator, urf_advisor, mesh_quality_advisor |
| E04 | case_027_v65 Hagen-Poiseuille pipe | V105 (wedge-axis Uz plateau) | pipe laminar wedge | virtual_interface_detector, solver_block_advisor |
| E05 | case_031_v65 NACA0012 transonic | V106 (limitTemperature template) | compressible transonic | thermo_polynomial_range, solver_block, urf_advisor |
| E06 | case_032_v65 independent flat plate | V107 (F-NEW-low-Re-trigger) | incompressible BL low-Re | inlet_outlet, solver_block, unit_detector |
| E07 | case_029_v65 NACA0012 stall | V104 2nd witness (NACA stall) | incompressible high-AoA | face_orientation, mesh_quality, urf_advisor, solver_block |

### Group B · V51-V100 carry-forward witnesses (3 cases)

| # | Case ID | V-row | Physics regime | Expected advisors |
|---|---|---|---|---|
| E08 | case_011 multi-body industrial | V10 (sHM ate thin walls) + V55 (extra_body) + carry-forward | industrial CHT 13-body | thin_wall, extra_body, shm_dict_validator, virtual_interface, face_orientation, stl_face_label, bc_type_name, inlet_outlet, urf (8/11) |
| E09 | case_003_v2 CRM-HLS CHT | V100 (A8 API contract bug) | industrial CHT high-lift | shm_dict_validator, thin_wall, extra_body, face_orientation |
| E10 | case_006_v3 ONERA M6 thermo | V46 (sutherland) + V64 (thermo-FPE) | compressible transonic | thermo_polynomial_range, solver_block, urf, unit_detector |

### Group C · F-NEW candidate scenarios (5 cases)

| # | Case ID | F-NEW candidate | Expected advisor gap |
|---|---|---|---|
| E11 | case_028_v3 APU bay strong-PARTIAL | V107 candidate (intake_duct STL-driven) | thin_wall (5 critical), mesh_quality, solver_block, urf, face_orientation, extra_body, bc_type_name, inlet_outlet (8/11) |
| E12 | case_030 wedge15Ma5 (B83 MIXED) | F-NEW-V106-solver-class-incompat | rhoCentralFoam compatibility advisor MISSING (rule gap) |
| E13 | case_033 airFoil2D (B88 substrate FAIL) | F-NEW-tutorial-substrate-inspection | substrate-inspection advisor MISSING (rule gap) |
| E14 | case_034 NACA0012 sHM-layers (B90 FAIL) | F-NEW-shm-layer-addition-instability | y+-target validation advisor MISSING (rule gap) |
| E15 | case_035 kEpsilon y+~1 (B92 FAIL) | F-NEW-kEpsilon-wallfn-mismatch | wall-function-regime-vs-yplus advisor MISSING (rule gap) |

### Group D · Industrial FULL benchmarks (3 cases)

| # | Case ID | Outcome | Expected advisors |
|---|---|---|---|
| E16 | case_035_v65 NASA TMR kOmegaSST (B91 FULL) | industrial FULL Wieghardt ±9.19% | inlet_outlet, solver_block, unit_detector, urf (4/11 — clean attached BL needs fewer) |
| E17 | case_035_SA y+=1 (B94 DOUBLE-FULL) | industrial FULL Wieghardt 2.23% + SG 6.76% | inlet_outlet, solver_block, unit_detector, urf (4/11) |
| E18 | case_035_SA y+=5 (B97 FULL within-iter) | industrial FULL · within-iter residual qualifier | inlet_outlet, solver_block, urf (3/11) + residual-gate-qualifier advisor |

### Group E · V64-A 1D analytical strict-FULL trio (2 cases)

| # | Case ID | V-row | Expected advisors |
|---|---|---|---|
| E19 | case_025 Poiseuille (V64-A FULL) | strict analytical | virtual_interface, solver_block, unit_detector (3/11 — minimal) |
| E20 | case_026 Couette (V64-A FULL) | strict analytical | virtual_interface, solver_block, unit_detector (3/11 — minimal) |

### Group F · V70 turbulence/compressibility breadth expansion (10 cases)

| # | Case ID | V-row / gap | Physics regime | Expected advisors |
|---|---|---|---|---|
| E21 | case_036_kOmegaSST_lowRe | F-NEW-kOmegaSST-lowRe | low-Re k-omega-SST steady | turbulence_model_advisor, mesh_resolution_advisor, separation_resolution_advisor |
| E22 | case_037_rhoCentralFoam_supersonic | GAP-rhoCentralFoam-anchor | supersonic wedge / oblique shock | rhoCentralFoam_compatibility_advisor, compressibility_regime_advisor, shock_capture_quality_advisor |
| E23 | case_038_rhoPimpleFoam_transonic_transient | GAP-rhoPimpleFoam-anchor | transonic transient buffet | compressibility_regime_advisor, shock_capture_quality_advisor, statistics_averaging_advisor |
| E24 | case_039_SpalartAllmaras_stall | GAP-SA-anchor | separated NACA0012 S-A | turbulence_model_advisor, separation_resolution_advisor, mesh_resolution_advisor |
| E25 | case_040_pimpleFoam_kEpsilon_transient | F-NEW-kEpsilon-transient | transient k-epsilon channel | turbulence_model_advisor, statistics_averaging_advisor |
| E26 | case_041_kOmegaSST_lowMach | GAP-weakly-compressible | weakly-compressible low-Mach | compressibility_regime_advisor, turbulence_model_advisor |
| E27 | case_042_DNS_channel_highRe | V70-DONE-2 | DNS channel Re_tau=590 | mesh_resolution_advisor, statistics_averaging_advisor |
| E28 | case_043_LES_backstep | F-NEW-LES-anchor | LES backward-facing step | separation_resolution_advisor, mesh_resolution_advisor, statistics_averaging_advisor |
| E29 | case_044_CHT_laminar | case_002a-CHT-laminar | laminar CHT | substrate_inspection_advisor, mesh_resolution_advisor |
| E30 | case_045_2D_symmetry_empty | BC-coverage-2D | 2D extrusion / empty BC | virtual_interface_detector, bc_type_name_validity_advisor |

---

## Expected advisor stack performance

For canonical eval set V66-B Done #3 regression protection, expanded by V70 breadth coverage:

| Advisor | Expected fire count across 30 cases | Coverage |
|---|---|---|
| face_orientation_advisor | 5+ (E01, E07, E08, E09, E11) | broad |
| inlet_outlet_validator | 8+ (most cases) | broad |
| bc_type_name_validity_advisor | 8+ (most cases) | broad |
| virtual_interface_detector | 4+ (E04, E08, E19, E20) | moderate |
| shm_dict_validator | 3+ (E08, E09, E11) | moderate |
| stl_face_label_validator | 2+ (E08, E11) | narrow |
| extra_body_advisor | 4+ (E08, E09, E11, others) | moderate |
| thermo_polynomial_range_advisor | 3+ (E05, E10, E11 thermo-class) | narrow |
| unit_detector | 10+ (most cases) | broad |
| solver_block_advisor | 12+ (most cases) | broad |
| thin_wall_advisor | 4+ (E08, E11, others industrial-CHT) | moderate |
| **NEW (V66-B)** mesh_quality_advisor | 3+ (E03, E11, NACA stall) | moderate (existing module · adds to dispatch) |
| **NEW (V66-B)** urf_advisor | 6+ (high-Re external aero cases) | broad |
| **NEW (V66-B)** advisor_v103 (Cf-canonical-choice) | 4+ (TBL cases at Re_x > 5e6) | narrow but signal |
| **NEW (V66-B)** advisor_v107 (low-Re kOmegaSST trigger) | 3+ (low-Re-band TBL with I=0.5%) | narrow |
| **NEW (V66-B)** advisor_yplus_regime_match | 5+ (any case with explicit y+ target) | broad |

**Target**: post-V66-B advisor stack ≥ 14 dispatched advisors (current 11 + 3 new) · cumulative fire rate ≥ 100 across 30 cases.

---

## V69.1 layout update (2026-05-16 · DEC-V69.1)

30 individual case files (E01-E30) replace the V66-B B104/B105 batched
documents. Batched docs preserved at `_archive_batched/` for audit.
Schema for individual files: YAML frontmatter (eval_case_id · case_id ·
title · v_row_attribution · v_row_class · physics_regime · status ·
sandbox_path · substrate_lineage · expected_verdict_signature) + body
with rules-firing table + anchor narrative.

V69.2 (next sub-DEC) adds `test_canonical_advisor_eval.py` regression
harness running each frontmatter through `assemble_stack`.

## Roadmap to V66-B Done #1-3 closure

- B101 · Author 3 new advisor rule descriptions (advisor_v103 + advisor_v107 + advisor_yplus_regime_match) per scoring framework anchors
- B102 · Document 5 most-impactful eval cases (E01, E02, E08, E11, E16) in detail · file per case
- B103 · Eval run · advisor stack over 5 cases · log firings · false neg/pos check
- B104 · 10 more cases documented · 2nd eval run
- B105 · Full 20 cases documented · 3rd eval run · SDK doc draft
- B106 · V66-B close DEC after 6/6 Done dims · V67 charter seed

— Claude Code (Opus 4.7 1M) · V66-B B100 · canonical eval set INDEX · 2026-05-16
