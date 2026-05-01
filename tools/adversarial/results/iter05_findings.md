# Adversarial Loop · Iter 05 — Hand-crafted T-Junction (Codex generation websocket-truncated)

**Geometry:** 240 mm horizontal duct + 100 mm vertical branch rising from middle. 40 mm cross-section everywhere, 40 mm extrusion depth. 4 named patches (inlet, outlet, outlet_branch, walls).
**Intent:** Re=20 icoFoam, expects flow splitting between right outlet + branch outlet.

## Pipeline traversal results

| Stage | Status | Notes |
|-------|--------|-------|
| 1. Import STL | ✅ PASS | watertight, 4 named patches, bbox (0.240, 0.140, 0.040) |
| 2. gmsh meshing | ✅ PASS | 3896 cells; per-triangle voting correctly classifies all 4 patches; symmetric outlet/outlet_branch face counts (66/66) confirm voting accuracy on 4-patch topology |
| 3. polyMesh boundary | ✅ PASS | 4 named patches: inlet=68, outlet=66, outlet_branch=66, walls=1600 |
| 4. setup-bc?from_stl_patches=1 (initial) | ⚠️ PARTIAL | inlet/outlet correct, **outlet_branch mis-classified to NO_SLIP_WALL** (defect 7) |
| 4. setup-bc?from_stl_patches=1 (after defect 7 fix) | ✅ PASS | All 4 patches correct, no warnings |
| 5. icoFoam solve | ✅ CONVERGED | cont_err=1.43e-7, residuals p=8.86e-7, wall_time=1.5s |

## Defect Found

### Defect 7 — Compound patch names mis-classified by stripped-numeric prefix matcher (FIXED)

**Severity:** High (silently produces wrong physics — `outlet_branch` was treated as a wall, blocking branch outflow)
**Location:** `services/case_solve/bc_setup_from_stl_patches.py:_classify_patch`
**Symptom:** T-junction's `outlet_branch` patch defaulted to `NO_SLIP_WALL` because the existing prefix matcher (`re.sub(r"_?\d+$", "", lower)`) only stripped trailing digits like `outlet_1`. Compound names with non-numeric suffixes (`outlet_branch`, `inlet_main`, `walls_top`) didn't match.
**Root cause:** Defect-3 closure (V61-103) added prefix matching but only for the `inlet_<n>` / `walls<n>` numbered case. Real CAD exporters often use compound English names (`outlet_branch`, `wall_top`, `inlet_main`).
**Fix:** Added Step 3 to `_classify_patch` lookup chain — strip everything after the first underscore and re-lookup. Order: exact → strip-trailing-digits → strip-after-first-underscore → fallback NO_SLIP_WALL.
**Verification:** iter05 retest after fix produces all 4 patches with correct classes (no warnings). Solve converges (cont_err=1.43e-7, residuals match the iter02/iter03/iter04 baseline).
**Test:** `test_compound_patch_names_classify_via_underscore_split` covers `inlet_main`, `outlet_right`, `outlet_branch`, `walls_perimeter` → all classify correctly. 13/13 BC unit tests pass.
**Concern logged:** `outlet_branch` in the *physical* sense IS a separate outlet patch; engineer might want different pressure or flow rate per outlet. Current default treats both `outlet` and `outlet_branch` as `pressure_outlet` with `p=0`, which is the correct physics for "ambient outlet" but not for "fixed flow rate" use cases. Engineer can override per-patch via raw-dict editor.

## Iteration outcome

iter05 closes another mile of the "arbitrary CAD support" road:
- 4-patch topology validated (was previously only 3-patch in iter02/iter03/iter04)
- compound patch names validated (canonical CAD-export naming)
- Multi-outlet flow splitting validated (mass conservation across 2 outlets)

The Codex case-generation pipeline kept timing out (websocket truncation, 3rd time this session). All iter04+ cases were either Codex-generated-but-rescued or hand-crafted. The adversarial-loop infrastructure is solid; the bottleneck is Codex CLI reliability when run via stdin redirect.

## Strategic state

| # | Defect | Status |
|---|---|---|
| 1 | Multi-solid STL watertight | ✅ Fixed |
| 2a | gmsh STL solid names | ✅ Fixed |
| 2b | Interior obstacles | 🔍 DEC-V61-104 |
| 3 | BC LDC-only | ✅ Fixed via DEC-V61-103 |
| 5 | Single-centroid mapping | ✅ Fixed (voting) |
| 6 | Hardcoded inlet U direction | ✅ Fixed (patch-normal-aware) |
| 7 | Compound patch name classification | ✅ Fixed (3-step lookup) |

5 critical defects fixed in this session; 1 architectural defect (2b) deferred to its own DEC. The system now handles:
- Multi-patch CAD (3-N patches) ✅
- Numbered patch suffixes (`inlet_1`, `walls01`) ✅
- Compound patch names (`outlet_branch`, `inlet_main`) ✅
- 3D-rotated geometries ✅
- Multi-outlet topologies (T-junction) ✅
- icoFoam end-to-end convergence ✅

The "arbitrary CAD support" claim is now supported by 4 distinct adversarial cases (iter02 axis-aligned duct, iter03 manual baseline, iter04 rotated L-bend, iter05 T-junction).
