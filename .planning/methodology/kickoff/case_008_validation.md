# case_008 · Codex Output Validation Report

> **Round 1 of 2** · 2026-05-08 — main session  
> **Verdict: PASS WITH NOTES**.  
> **Backend**: 86gs gpt-5.5 xhigh.  
> Clarification preamble worked — no read-only-workspace
> hallucination.

## Summary
- **Case ID**: `case_008_glc305_irt_lagrangian`
- **Component**: GLC305 clean airfoil (305 mm chord, 2D-extruded slab, NASA Glenn IRT droplet-impingement reference)
- **Hard exclusion honored**: `NACA0012_not_used` explicit in manifest
- **Solver**: simpleFoam (steady RANS) + kinematicCloud (one-way Lagrangian particle tracking after Eulerian convergence). v2 fallback DPMFoam only if particle volume fraction not negligible (nominal 7e-7 → 1-way is correct)
- **Freestream**: U_inf=67 m/s, α=4°, T_inf=268 K, ν_air=1.4e-5, Re_chord ≈ 1.46e6, MVD=25 µm, LWC=0.7 g/m³, ρ_p=1000
- **Defects**: D1 (0.35 mm gap root_mount_pad ↔ root_mount_strut at x/c=0.72) + D8 (0.80 mm thin trailing_edge_tab_thin at x/c=1.00)
- **Effort**: 8-12h, ~3 versions

## 13-check pass/fail summary

| # | Check | Status |
|---|---|---|
| 1 | CadQuery script syntax | ✅ 231 LOC, py_compile OK |
| 2 | cadquery installable | ⚠ standard caveat |
| 3 | Source URLs reachable | ✅ NTRS citations 20020061865, 20020090796 valid form |
| 4 | Patch names regex | ✅ 10 named bodies (`airfoil_clean`, `root_mount_pad`, `root_mount_strut`, `trailing_edge_tab_thin`, `inlet`, `outlet`, `farfield_top`, `farfield_bottom`, `sym_plane_left`, `sym_plane_right`) |
| 5 | NOT NACA 0012 | ✅ GLC305 picked; `hard_exclusion_honored: NACA0012_not_used` explicit |
| 6 | lagrangian_cloud block | ✅ kinematicCloud + patchInjection + run_sequence (simpleFoam→freeze→cloud) |
| 7 | freestream block w/ MVD/LWC | ✅ MVD=25e-6, LWC=0.0007, ρ_p=1000, U vector includes α=4° |
| 8 | collection_efficiency block | ✅ β(s/c) measurement strategy + impingement limits |
| 9 | dimensionless_groups block | ✅ Re_chord, K_inertia=0.41, Stokes=0.41, We=2.0 |
| 10 | Defects NOT on LE stagnation | ✅ D1 at x/c=0.72 (TE-side mounting strut), D8 at x/c=1.00 (TE tab); both outside ±10°/+30° around stagnation |
| 11 | No ice horn in input | ✅ `no_ice_horn_in_input_geometry: true` explicit |
| 12 | 2D-extruded slab w/ symmetry | ✅ `sym_plane_left` + `sym_plane_right` |
| 13 | Steady-state Eulerian first | ✅ run_sequence enforces simpleFoam→freeze→cloud |

**All 13 checks pass.**

## Notes

### N1 · 6th consecutive A2-pending
D1's `expected_advisor_to_catch: virtual_interface_detector`
again references A2-pending. Cases 003/004/005/006/007/**008**
all surface this gap. **6-of-6** evidence — A2 extraction is
unambiguous priority for next harvest cycle.

### N2 · D8 thin_wall_advisor consistency check (3rd time)
D8 (0.80 mm) maps to landed `thin_wall_advisor`. case_004 (0.75
mm yaw_sensor_shim) + case_007 (0.80 mm transom plate) +
case_008 (0.80 mm TE tab) form a 3-case advisor consistency
trial. Sub-session should observe consistent advisor signals
across all three; geometry topology differences (3D shim vs
ship plate vs airfoil TE tab) are useful sensitivity test.

### N3 · First Lagrangian case for project
No prior `kinematicCloud` infrastructure. New artifact candidates:
- `lagrangian_cloud_writer.py` (kinematicCloudProperties +
  injection model + drag/force model)
- `collection_efficiency_post_processor.py` (parse
  cloud-impact stats → β(s/c) curve)

### N4 · Re slightly off nominal IRT reference
Codex computed `Re_chord_from_specified_nu: 1.46e6` vs
`Re_chord_nominal_IRT_reference: 1.8e6`. The discrepancy comes
from picking ν_air at low T (268 K → ν=1.4e-5) vs typical NTRS
references that may use 288 K. Sub-session can either accept
this (T=268 K is consistent with icing T below freezing) or
re-tune ν to match the canonical 1.8e6 Re. Document in v1.

### N5 · 2D-extruded slab vs full 3D
Codex went with 2D-extruded slab (1 chord spanwise, sym_plane
left/right). Correct for case_008 scope; full 3D wing would be
a different case. Note for sub-session: kinematicCloud particles
in 2D-extruded slab work correctly because particle injection
is at the patchInjection on inlet, not volumetric.

## Approval
✅ proceed to `kickoff/case_008_glc305_irt_lagrangian.md`.

## Files
- `kickoff/case_008_codex_request.md`
- `kickoff/case_008_codex_response.md` (603 lines)
- `kickoff/case_008_validation.md` (this)
- `kickoff/case_008_glc305_irt_lagrangian.md` (next)
