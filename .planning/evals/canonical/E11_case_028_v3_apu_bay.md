---
eval_case_id: E11
case_id: case_028_v3
title: APU bay strong-PARTIAL · F-NEW-V107-candidate (intake_duct STL-driven)
v_row_attribution: [F-NEW-V107-candidate, V55, V25, V41]
v_row_class: F-NEW-candidate (strong-PARTIAL, awaiting 2nd witness for LANDING)
physics_regime: industrial ventilation · multi-body · APU bay
status: ACTIVE_EVAL
sandbox_path: workspace/projects/case_028/foamcase_v3/
substrate_lineage: APU bay ventilation industrial case (2026-05-11 reimport)
expected_verdict_signature: "STL-driven intake duct geometry + thin-wall + extra-body advisors fire · strong-PARTIAL verdict from industrial cooling validation (no canonical Cf reference)"
---

# E11 · case_028_v3 APU bay strong-PARTIAL (F-NEW-V107 candidate)

## Case summary

- **Geometry**: APU bay ventilation enclosure · STL-driven intake duct · 11 region multi-body
- **Mesh**: snappyHexMesh on STEP-reimport STL · ~89k cells (sHM validated)
- **Solver**: simpleFoam (incompressible) · kOmegaSST · industrial cooling regime
- **Physics**: forced ventilation through APU compartment

## V-row attribution

**F-NEW-V107-candidate (1st observation here)**: STL-driven intake duct geometry creates a flow-defining boundary that needs explicit advisor recognition. Currently captured as candidate; awaits 2nd witness to LAND.

- **V55 carry-forward**: extra-body STL disposition
- **V25**: virtual-interface patches at duct/bay junctions
- **V41**: inlet-outlet flow boundary validation

## Expected advisor rule firings

| Rule | Expected fire | Severity | Why |
|---|---|---|---|
| `thin_wall_advisor` | ✓ | **error** | 5 critical (industrial sheet metal) |
| `mesh_quality_advisor` | ✓ | warn | typical aspect-ratio warnings on snappy-on-curved |
| `solver_block_advisor` | ✓ | info | simpleFoam + RAS |
| `urf_advisor` | ✓ | info | industrial-typical lowered URF |
| `face_orientation_advisor` | ✓ | info | multi-body face normal validation |
| `extra_body_advisor` | ✓ | warn | STL count vs region count check |
| `bc_type_name_validity_advisor` | ✓ | info | inlet/outlet/wall variety |
| `inlet_outlet_validator` | ✓ | info | forced inlet present |
| **`yplus_regime_match_advisor` (NEW)** | maybe | warn | if y+ > 30 with kOmegaSST, fires warn (in_band for wall fn) |
| **`low_re_kOmegaSST_trigger_advisor` (NEW)** | ✗ | — | I likely > 1% for industrial inlet |
| `cf_canonical_choice_advisor` | ✗ | — | no flat-plate BL |
| `virtual_interface_detector` | ✓ | info | duct/bay junction patches |

**Expected fire count**: 8 / 14 advisors. Same breadth class as E08 but different physics.

## Expected verdict pattern

```yaml
verdict: strong-PARTIAL (no canonical Cf for industrial ventilation · validated against engineering targets)
v_rows_validated: [V55, V25, V41]
v_rows_candidate: [F-NEW-V107-candidate awaiting 2nd witness]
advisor_signals:
  - thin_wall_error (5 critical)
  - mesh_quality_warn
  - extra_body_warn
  - face_orientation_info
  - virtual_interface_info
  - bc_type_name_info
  - inlet_outlet_info
  - urf_info
```

## Why this case anchors F-NEW-V107-candidate

APU bay is the only industrial-ventilation witness in the eval set. If a 2nd similar case lands (e.g., a different ventilation enclosure), the F-NEW-V107-candidate promotes to LANDED V108 with this case as 1st witness.

## Anti-regression check

If `thin_wall_advisor` fires < 5 critical regions → industrial sheet-metal coverage regression → REGRESSION.

If `extra_body_advisor` fails to fire → STL ingest advisor regression → REGRESSION.

— B102 · V66-B Done #2 eval-case detail · 2026-05-16
