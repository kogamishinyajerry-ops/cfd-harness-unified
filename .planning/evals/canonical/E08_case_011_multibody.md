---
eval_case_id: E08
case_id: case_011
title: Multi-body industrial CHT 13-body (V10 + V55 carry-forward · broadest advisor sweep)
v_row_attribution: [V10, V55, V25, V27, V32, V41, V49]
v_row_class: LANDED (V51-A frozen carry-forward)
physics_regime: industrial CHT · multi-body · 13 STL solids
status: ACTIVE_EVAL
sandbox_path: workspace/projects/case_011/foamcase_v3/
substrate_lineage: industrial multi-component thermal management box
expected_verdict_signature: "13-body STL ingest with thin-wall + extra_body + virtual_interface advisors all firing simultaneously · broadest advisor coverage in eval set"
---

# E08 · case_011 multi-body industrial CHT

## Case summary

- **Geometry**: 13 STL bodies in industrial enclosure · CHT (conjugate heat transfer)
- **Mesh**: snappyHexMesh with explicit feature edges · ~1.2M cells post-snap
- **Solver**: chtMultiRegionFoam · multi-region · steady
- **Physics**: solid + fluid coupling at 26+ patch interfaces

## V-row attribution

This case is the **broadest advisor sweep** in the eval set — it triggers 8/11 baseline advisors simultaneously, making it the gold-standard regression case for advisor stack maturity.

- **V10**: snappyHexMesh ate thin walls (1st observation here · LANDED via V51-A)
- **V55**: extra_body in STL set required explicit ingest path (advisor warns when STL count > region count)
- **V25/V27/V32/V41/V49**: face-orientation, stl-face-label-validity, bc-type-name, inlet-outlet, urf carry-forwards

## Expected advisor rule firings

| Rule | Expected fire | Severity | Why |
|---|---|---|---|
| `thin_wall_advisor` | ✓ | **error** | 5 critical thin-wall regions detected (V10 anchor) |
| `extra_body_advisor` | ✓ | warn | 13 STL vs 11 regions → 2 extra bodies need disposition |
| `shm_dict_validator` | ✓ | warn | snappyHexMeshDict feature-edge level mismatch typical |
| `virtual_interface_detector` | ✓ | info | 26+ patch interfaces detected |
| `face_orientation_advisor` | ✓ | info | multi-body face normal validation |
| `stl_face_label_validator` | ✓ | info | 13 STL → 13 distinct patch names required |
| `bc_type_name_validity_advisor` | ✓ | info | chtMultiRegionFoam needs region-specific BC types |
| `inlet_outlet_validator` | ✓ | info | inlet/outlet flow boundary present |
| `urf_advisor` | ✓ | info | CHT typical URF lowered |
| `solver_block_advisor` | ✓ | info | chtMultiRegionFoam dispatched |
| `mesh_quality_advisor` | maybe | info | typical aspect-ratio warnings on industrial meshes |
| `thermo_polynomial_range_advisor` | maybe | info | if temperature range exceeds polynomial limits |
| **`yplus_regime_match_advisor` (NEW)** | ✓ | info | if wall-function regime documented |
| `cf_canonical_choice_advisor` | ✗ | — | industrial CHT, not 2D BL |
| `low_re_kOmegaSST_trigger_advisor` | ✗ | — | not low-Re BL |

**Expected fire count**: **9-10 / 14 advisors** (highest in eval set). Coverage breadth = regression-protection value.

## Expected verdict pattern

```yaml
verdict: PARTIAL (V51-A frozen carry-forward) · industrial CHT no canonical reference
v_rows_validated: [V10, V55, V25, V27, V32, V41, V49]
advisor_signals:
  - thin_wall_error (5 critical regions · V10 anchor)
  - extra_body_warn (2 STL without region disposition · V55 anchor)
  - shm_dict_warn (feature edge level mismatch typical)
  - virtual_interface_info (26+ patch interfaces · V25 anchor)
  - face_orientation_info
  - stl_face_label_info
  - bc_type_name_info
  - inlet_outlet_info
  - urf_info
```

## Why this case anchors broad advisor coverage

Industrial multi-body CHT cases are the **only** case class that exercises thin-wall + extra-body + virtual-interface advisors simultaneously. Removing this case from eval set → loss of regression protection for 5+ V-rows at once.

## Anti-regression check

If fewer than 8 advisors fire on E08 → advisor stack regression on industrial CHT class → REGRESSION.

If `thin_wall_advisor` reports < 5 critical regions → V10 advisor coverage broken → REGRESSION.

— B102 · V66-B Done #2 eval-case detail · 2026-05-16
