---
batch: B104
title: V66-B canonical eval cases E03-E15 batched documentation
date: 2026-05-16
purpose: V66-B Done #2 advance (5/20 → 15/20 documented)
batching_rationale: Anthropic agent canon "context as scarce resource" — 10 lighter-content cases batched per file rather than 10 separate files
---

# Canonical eval cases E03-E15 (10 cases · batched)

> Each case carries minimum-required fields per V66-B Done #2:
> 1. V-row attribution
> 2. Expected advisor firings (table)
> 3. Expected verdict signature
> 4. Sandbox path
> 5. Why this case anchors its V-row

---

## E03 · case_022_v64 Driver-Seegmiller BFS (V104)

- **v_row_attribution**: [V104]
- **physics_regime**: incompressible separation · backward-facing step
- **substrate**: Driver & Seegmiller 1985 NASA TM-86844
- **sandbox**: workspace/projects/case_022/foamcase_v64/
- **expected_verdict_signature**: "kOmegaSST under-predicts reattachment length by ~10% on BFS · F-NEW captured"

| Rule | Expected fire | Why |
|---|---|---|
| `inlet_outlet_validator` | ✓ info | inlet velocity profile |
| `urf_advisor` | ✓ info | separation needs lowered URF |
| `mesh_quality_advisor` | ✓ info | step-corner mesh refinement |
| `solver_block_advisor` | ✓ info | simpleFoam + kOmegaSST |
| `cf_canonical_choice_advisor` | ✗ | not flat BL |
| `yplus_regime_match_advisor` | ✓ info | if y+ documented |

**Anchor**: V104 (kOmegaSST separation under-prediction) — 1st witness LANDED B82.

---

## E04 · case_027_v65 Hagen-Poiseuille wedge (V105)

- **v_row_attribution**: [V105]
- **physics_regime**: pipe laminar · wedge axisymmetric
- **substrate**: Hagen-Poiseuille analytical (μ=fluid viscosity, parabolic profile)
- **sandbox**: workspace/projects/case_027/foamcase_v65/
- **expected_verdict_signature**: "wedge-axis Uz plateau matches analytical to <0.5% · validates wedge BC interpretation"

| Rule | Expected fire | Why |
|---|---|---|
| `virtual_interface_detector` | ✓ info | wedge symmetry patches |
| `solver_block_advisor` | ✓ info | icoFoam laminar |
| `unit_detector` | ✓ info |
| `face_orientation_advisor` | ✓ info | wedge axis face normal critical |
| `urf_advisor` | ✗ | laminar steady not needed |
| `cf_canonical_choice_advisor` | ✗ | analytical not Cf |

**Anchor**: V105 (wedge-axis Uz plateau) — LANDED B83.

---

## E05 · case_031_v65 NACA0012 transonic (V106)

- **v_row_attribution**: [V106]
- **physics_regime**: compressible transonic · M~0.7
- **substrate**: NACA0012 transonic standard
- **sandbox**: workspace/projects/case_031/foamcase_v65/
- **expected_verdict_signature**: "limitTemperature fvOptions required for thermo polynomial range · without → divergence"

| Rule | Expected fire | Why |
|---|---|---|
| `thermo_polynomial_range_advisor` | ✓ **error** | T might exceed polynomial range |
| `solver_block_advisor` | ✓ info | rhoSimpleFoam |
| `urf_advisor` | ✓ info | transonic needs lowered URF |
| `inlet_outlet_validator` | ✓ info | far-field BC |
| `unit_detector` | ✓ info | compressible needs T, p separate |
| `cf_canonical_choice_advisor` | ✗ | not flat BL |
| `face_orientation_advisor` | ✗ | 2D |

**Anchor**: V106 (limitTemperature template) — LANDED B84.

---

## E06 · case_032_v65 independent flat plate low-Re (V107)

- **v_row_attribution**: [V107]
- **physics_regime**: incompressible BL · low-Re kOmegaSST trigger zone
- **substrate**: independent flat plate L=1.0m, 30k cells, 5×200 grading
- **sandbox**: workspace/projects/case_032/foamcase_v65/
- **expected_verdict_signature**: "kOmegaSST + I=0.5% at Re_x ∈ [1e6, 3e6] under-predicts Cf by ~10% · matches V107 prediction"

| Rule | Expected fire | Why |
|---|---|---|
| `inlet_outlet_validator` | ✓ info |
| `solver_block_advisor` | ✓ info |
| `unit_detector` | ✓ info |
| **`low_re_kOmegaSST_trigger_advisor`** | ✓ **warn** (HIGH) | exact V107 trigger condition |
| **`cf_canonical_choice_advisor`** | ✓ warn | cross-canonical at Re_x boundary |
| **`yplus_regime_match_advisor`** | ✓ info | y+~1 kOmegaSST in_band |
| `urf_advisor` | ✓ info |

**Anchor**: V107 (F-NEW-low-Re-trigger) — 2nd witness LANDED B86. case_021 v64 + v65 are 1st + 2nd witnesses; case_032 is 3rd (independent substrate).

---

## E07 · case_029_v65 NACA0012 stall (V104 2nd witness)

- **v_row_attribution**: [V104]
- **physics_regime**: incompressible high-AoA stall
- **substrate**: NACA0012 at high AoA (≥15°)
- **sandbox**: workspace/projects/case_029/foamcase_v65/
- **expected_verdict_signature**: "kOmegaSST under-predicts post-stall Cl by ~12% · 2nd witness for V104 (separation under-pred)"

| Rule | Expected fire | Why |
|---|---|---|
| `face_orientation_advisor` | ✓ info | airfoil camber normals |
| `mesh_quality_advisor` | ✓ info | LE/TE refinement |
| `urf_advisor` | ✓ info | stall needs URF≤0.5 |
| `solver_block_advisor` | ✓ info |
| `inlet_outlet_validator` | ✓ info |
| `yplus_regime_match_advisor` | ✓ info |
| `cf_canonical_choice_advisor` | ✗ | not flat BL |

**Anchor**: V104 (kOmegaSST separation under-prediction) 2nd witness LANDED B85. case_022 BFS is 1st witness.

---

## E09 · case_003_v2 CRM-HLS CHT (V100)

- **v_row_attribution**: [V100]
- **physics_regime**: industrial CHT · high-lift configuration
- **substrate**: NASA CRM high-lift CHT validation
- **sandbox**: workspace/projects/case_003/foamcase_v2/
- **expected_verdict_signature**: "A8 API contract bug (V100) · validated via session-level review · industrial CHT 4-region"

| Rule | Expected fire | Why |
|---|---|---|
| `shm_dict_validator` | ✓ warn |
| `thin_wall_advisor` | ✓ warn |
| `extra_body_advisor` | ✓ warn |
| `face_orientation_advisor` | ✓ info |
| `bc_type_name_validity_advisor` | ✓ info |
| `solver_block_advisor` | ✓ info | chtMultiRegionFoam |
| `cf_canonical_choice_advisor` | ✗ | industrial |

**Anchor**: V100 (A8 API contract bug) — LANDED V64-A.

---

## E10 · case_006_v3 ONERA M6 thermo (V46 + V64)

- **v_row_attribution**: [V46, V64]
- **physics_regime**: compressible transonic · 3D wing
- **substrate**: ONERA M6 (Schmitt-Charpin 1979)
- **sandbox**: workspace/projects/case_006/foamcase_v3/
- **expected_verdict_signature**: "sutherland viscosity + thermo-FPE polynomial range · validated against Schmitt-Charpin pressure data"

| Rule | Expected fire | Why |
|---|---|---|
| `thermo_polynomial_range_advisor` | ✓ warn |
| `solver_block_advisor` | ✓ info | rhoSimpleFoam |
| `urf_advisor` | ✓ info |
| `unit_detector` | ✓ info |
| `face_orientation_advisor` | ✓ info | 3D wing |
| `cf_canonical_choice_advisor` | ✗ | 3D wing |

**Anchor**: V46 (sutherland) + V64 (thermo-FPE) — LANDED V63-A.

---

## E12 · case_030 wedge15Ma5 (F-NEW-V106-solver-class)

- **v_row_attribution**: [F-NEW-V106-solver-class]
- **physics_regime**: compressible hypersonic wedge · density-based candidate
- **substrate**: 15° wedge at Mach 5 (Anderson 2003 Fundamentals analytical)
- **sandbox**: workspace/projects/case_030/foamcase_v3/
- **expected_verdict_signature**: "rhoCentralFoam compatibility advisor MISSING (rule gap) · B83 MIXED outcome captured as F-NEW"

| Rule | Expected fire | Why |
|---|---|---|
| `solver_block_advisor` | ✓ warn | rhoCentralFoam requires specific schemes |
| `thermo_polynomial_range_advisor` | ✓ error | T at Mach 5 likely outside polynomial range |
| `unit_detector` | ✓ info |
| `inlet_outlet_validator` | ✓ info |
| `cf_canonical_choice_advisor` | ✗ | hypersonic, not subsonic BL |

**Anchor gap**: F-NEW-V106-solver-class · rhoCentralFoam compatibility advisor not in current 14-rule stack. V13x-4 candidate for V67-B.

---

## E13 · case_033 airFoil2D (F-NEW-tutorial-substrate-inspection)

- **v_row_attribution**: [F-NEW-tutorial-substrate-inspection]
- **physics_regime**: incompressible 2D airfoil · tutorial substrate FAIL
- **substrate**: airFoil2D OpenFOAM tutorial (cambered airfoil at 35m chord)
- **sandbox**: workspace/projects/case_033/foamcase_v3/
- **expected_verdict_signature**: "B88 substrate-mismatch FAIL · Cl=19.78 bogus due to cambered airfoil at 35m chord (not NACA0012 at 1m as assumed)"

| Rule | Expected fire | Why |
|---|---|---|
| `solver_block_advisor` | ✓ info |
| `inlet_outlet_validator` | ✓ info |
| `face_orientation_advisor` | ✓ info |
| `urf_advisor` | ✓ info |
| `substrate_inspection_advisor` | ✗ MISSING | F-NEW rule gap |
| `cf_canonical_choice_advisor` | ✗ | 2D airfoil |

**Anchor gap**: F-NEW-tutorial-substrate-inspection · substrate-inspection advisor not in current stack. V13x-5 candidate.

---

## E14 · case_034 NACA0012 sHM-layers (F-NEW-shm-layer-addition-instability)

- **v_row_attribution**: [F-NEW-shm-layer-addition-instability]
- **physics_regime**: incompressible 2D airfoil mesh generation
- **substrate**: NACA0012 with sHM addLayers attempt
- **sandbox**: workspace/projects/case_034/foamcase_v3/
- **expected_verdict_signature**: "B90 FAIL · 0/1696 faces extruded · writeLayerSets crash · y+ avg 763 unsuitable"

| Rule | Expected fire | Why |
|---|---|---|
| `shm_dict_validator` | ✓ warn | layer addition param check |
| `mesh_quality_advisor` | ✓ error | y+ 763 unacceptable |
| `solver_block_advisor` | ✓ info |
| **`yplus_regime_match_advisor`** | ✓ **error** | y+ 763 out of any regime band |
| `yplus_target_validation_advisor` | ✗ MISSING | F-NEW rule gap |

**Anchor gap**: F-NEW-shm-layer-addition-instability · partially covered by `yplus_regime_match_advisor` (V66-B new) · V13x-6 candidate.

---

## E15 · case_035 kEpsilon y+~1 (F-NEW-kEpsilon-wallfn-mismatch · B92 anti-pattern)

- **v_row_attribution**: [F-NEW-kEpsilon-wallfn-mismatch]
- **physics_regime**: incompressible BL · WRONG model-mesh combination (kEpsilon at y+~1)
- **substrate**: case_035 NASA TMR substrate + kEpsilon model + y+~1 mesh
- **sandbox**: workspace/projects/case_035/foamcase_v3/kEps_variant/
- **expected_verdict_signature**: "kEpsilon at y+~1 over-predicts Cf by 60-67% (wall function regime mismatch · B92 FAIL anti-pattern)"

| Rule | Expected fire | Why |
|---|---|---|
| `solver_block_advisor` | ✓ info | simpleFoam + kEpsilon |
| `inlet_outlet_validator` | ✓ info |
| **`yplus_regime_match_advisor`** | ✓ **ERROR** | y+~1.2 in kEpsilon dead zone [5, 30] · B92 anti-pattern direct hit |
| **`cf_canonical_choice_advisor`** | ✓ warn |
| `unit_detector` | ✓ info |

**Anchor**: F-NEW-kEpsilon-wallfn-mismatch · directly covered by `yplus_regime_match_advisor` (V66-B new advisor) → B92 anti-pattern now caught by advisor stack. **V13x-3 promotion candidate** (yplus_regime_match LANDING witnessed).

---

## Aggregate advisor firings across E03-E15 (10 cases)

| Rule | E03 | E04 | E05 | E06 | E07 | E09 | E10 | E12 | E13 | E14 | E15 | Total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| inlet_outlet_validator | ✓ | | | ✓ | ✓ | | | ✓ | ✓ | | ✓ | 6 |
| solver_block_advisor | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 11 |
| urf_advisor | ✓ | | ✓ | ✓ | ✓ | | ✓ | | ✓ | | | 6 |
| unit_detector | | ✓ | ✓ | ✓ | | | ✓ | ✓ | | | ✓ | 6 |
| mesh_quality_advisor | ✓ | | | | ✓ | | | | | ✓ | | 3 |
| face_orientation_advisor | | ✓ | | | ✓ | ✓ | ✓ | | ✓ | | | 5 |
| thermo_polynomial_range | | | ✓ | | | | ✓ | ✓ | | | | 3 |
| shm_dict_validator | | | | | | ✓ | | | | ✓ | | 2 |
| thin_wall_advisor | | | | | | ✓ | | | | | | 1 |
| extra_body_advisor | | | | | | ✓ | | | | | | 1 |
| bc_type_name_validity | | | | | | ✓ | | | | | | 1 |
| virtual_interface_detector | | ✓ | | | | | | | | | | 1 |
| stl_face_label_validator | | | | | | | | | | | | 0 |
| **cf_canonical_choice (NEW)** | | | | ✓ | | | | | | | ✓ | 2 |
| **low_re_kOmegaSST (NEW)** | | | | ✓ | | | | | | | | 1 |
| **yplus_regime_match (NEW)** | ✓ | | | ✓ | ✓ | | | | | ✓ | ✓ | 5 |

**Total fires across E03-E15**: 54 firings.
**Combined E01-E16 (15 cases run)**: 54 + 38 = **92 firings** (cumulative · target ≥100 across 20 cases).

— Claude Code (Opus 4.7 1M) · B104 · V66-B canonical eval cases E03-E15 batched · 2026-05-16
