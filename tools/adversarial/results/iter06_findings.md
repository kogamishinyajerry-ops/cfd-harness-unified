# Adversarial Loop · Iter 06 — Hand-crafted half-pipe with symmetry plane

**Geometry:** half-cylinder (radius 50 mm, length 300 mm) lying along +z, half-disk cross-section above the y=0 symmetry plane. 4 named patches (inlet, outlet, walls, symmetry).
**Intent:** Re=50 icoFoam, expects steady pipe flow with symmetric profile + zero normal velocity on the symmetry plane.

## Pipeline traversal results

| Stage | Status | Notes |
|-------|--------|-------|
| 1. Import STL | ✅ PASS | watertight, 4 named patches, bbox (0.10, 0.05, 0.30) |
| 2. gmsh meshing | ✅ PASS | 5295 cells; per-triangle area-weighted voting correctly classifies all 4 patches across the curved wall (the cylindrical surface gets split into multiple gmsh parametric surfaces, each individually mapped) |
| 3. polyMesh boundary | ✅ PASS | inlet=95, outlet=95, walls=1120, symmetry=668 (all 4 named, watertight count matches) |
| 4. setup-bc?from_stl_patches=1 (initial) | ⚠️ FAIL → FIXED | Patches classified correctly (`symmetry → SYMMETRY` via canonical-token scan), but `constant/polyMesh/boundary` kept gmshToFoam's default `type patch` for the symmetry patch — see defect 8 |
| 5. icoFoam solve (initial) | ❌ FATAL IO ERROR | "patch type 'patch' not constraint type 'symmetry'" — defect 8 surfaced here |
| 4. setup-bc (after defect 8 fix) | ✅ PASS | All 4 patches correct + `constant/polyMesh/boundary` rewritten to `type symmetry` for the symmetry patch (atomically committed alongside the 7 dict files) |
| 5. icoFoam solve (after defect 8 fix) | ✅ CONVERGED | cont_err=7.73e-8, residuals p=8.29e-7 / U~3e-7, wall_time=2.2s |

## Defect Found

### Defect 8 — gmshToFoam emits `type patch` for symmetry patches → icoFoam constraint mismatch (FIXED)

**Severity:** Critical (silently produces a case that imports + meshes + sets up BC successfully but fails at solver-startup with FATAL IO ERROR)
**Location:** `services/case_solve/bc_setup_from_stl_patches.py:setup_bc_from_stl_patches`
**Symptom:** iter06 half-pipe with symmetry plane: `0/p` BC dict declared `type symmetry;` (correct), but `constant/polyMesh/boundary` kept gmshToFoam's default:

```
symmetry
{
    type            patch;          // ← gmshToFoam default
    physicalType    patch;
    nFaces          668;
    startFace       10911;
}
```

icoFoam's first read of `0/p` triggered:

```
--> FOAM FATAL IO ERROR:
    patch type 'patch' not constraint type 'symmetry'
    for patch symmetry of field p in file ".../0/p"
```

**Root cause:** OpenFOAM constraint-type patches (`symmetry`, `wedge`, `cyclic`, `empty`, `processor`) require the polyMesh `boundary` file's `type` field to MATCH the field BC dict's constraint type. Regular patches (`patch`, `wall`) don't have this requirement — `noSlip` works fine with `type patch`. But constraint types use compile-time-typed `fvPatchField` subclasses that validate their `fvPatch` parent's type at construction.

**Fix:** When the BC mapper writes a SYMMETRY-class patch's BC, atomically rewrite that patch entry in `constant/polyMesh/boundary` to `type symmetry; physicalType symmetry;`. Implementation:
- New `_CONSTRAINT_PATCH_TYPES: dict[BCClass, str]` maps `BCClass.SYMMETRY → "symmetry"`. Easily extensible to wedge / cyclic / empty when those BCClasses are added.
- New `_rewrite_polymesh_boundary_constraint_types(boundary_path, patches_with_class)` returns the rewritten content (or `None` if no constraint patches in the case). Two regex passes per affected patch: first the `type` line, then optionally `physicalType`.
- `setup_bc_from_stl_patches` calls the rewrite and appends `("constant/polyMesh/boundary", rewritten_content)` to the existing 7-entry dict plan, so the boundary rewrite participates in the V61-102 atomic two-phase commit (a partial write rolls back along with the dicts).

**Verification:** iter06 retest after fix — all 4 patches still classified correctly, `constant/polyMesh/boundary` symmetry block now reads `type symmetry; physicalType symmetry;`, solver converges (cont_err=7.73e-8). Other patches' `type` unchanged. Walls deliberately NOT rewritten to `type wall` — `noSlip` + `type patch` is valid OpenFOAM and outside this defect's scope.

**Test:** `test_four_patch_with_symmetry_emits_symmetry_block` extended with assertions on the boundary file rewrite (symmetry block has `type symmetry`, inlet block stays `type patch`). 13/13 BC unit tests pass.

**Concern logged:** When future BCClasses get added (wedge for axisymmetric cases, cyclic for periodic boundaries), they need to (a) add an entry to `_CONSTRAINT_PATCH_TYPES`, (b) potentially also rewrite `constant/polyMesh/cyclicLink` or similar. The framework is in place; only the data needs to grow.

## Iteration outcome

iter06 closes another adversarial-discovery loop:

- **Curved-wall geometry validated** — gmsh splits the cylindrical wall into multiple parametric surfaces, area-weighted voting maps each correctly back to the source `walls` solid. The defect-5 + defect-5 follow-up (area weighting) work was prerequisite — iter06 is the first case where curved walls actually exercise this code path.
- **SYMMETRY BCClass validated end-to-end** — first adversarial case to drive the SYMMETRY path through import → mesh → BC → solve. Surfaced defect 8 (boundary file constraint-type rewrite) which had been latent since DEC-V61-103 cacda9f.
- **5 distinct adversarial cases now converge** end-to-end with icoFoam: iter02 (axis-aligned duct), iter03 (manual baseline), iter04 (rotated L-bend, Euler 15/30/20°), iter05 (rotated T-junction, Euler 21/-28/17°), iter06 (half-pipe with symmetry).

## Strategic state (end of iter06)

| # | Defect | Status |
|---|---|---|
| 1 | Multi-solid STL watertight | ✅ Fixed |
| 2a | gmsh STL solid names | ✅ Fixed |
| 2b | Interior obstacles | 🔍 DEC-V61-104 (deferred) |
| 3 | BC LDC-only | ✅ Fixed (Phase 1 / DEC-V61-103) |
| 4 | Numbered patch suffixes | ✅ Fixed |
| 5 | Single-centroid mapping | ✅ Fixed (voting; area-weighted post-Codex) |
| 6 | Hardcoded inlet U direction | ✅ Fixed (patch-normal-aware) |
| 7 | Compound patch name classification | ✅ Fixed (canonical-token scan post-Codex) |
| 8 | SYMMETRY patch boundary-file constraint type | ✅ Fixed |

8 critical/high defects fixed across 6 adversarial cases. The system now handles:

- Multi-patch CAD (3-N patches) ✅
- Numbered patch suffixes (`inlet_1`, `walls01`) ✅
- Compound patch names (`outlet_branch`, `left_inlet`) ✅
- 3D-rotated geometries ✅
- Multi-outlet topologies (T-junction) ✅
- **Curved (cylindrical) wall surfaces** ✅ (iter06 new)
- **SYMMETRY constraint-type patches end-to-end** ✅ (iter06 new)
- icoFoam end-to-end convergence ✅

The "arbitrary CAD support" claim is now backed by **5 distinct adversarial cases**: iter02 axis-aligned duct, iter04 rotated L-bend, iter05 rotated T-junction, iter06 half-pipe with symmetry, plus iter03 manual baseline.

## Codex review status

Defect 8 fix is a single-file backend change (~80 LOC + regression test extension on existing test). It falls within the verbatim-exception scope per RETRO-V61-001 (≤1 file substantive change, has regression test, addresses a specific bug class — constraint patch type mismatch — with surgical fix). Post-merge Codex review optional. If invoked, focus questions:

- Is the regex-based boundary file rewrite robust against unusual gmshToFoam output formats (e.g., extra whitespace, comment lines in patch blocks)?
- Are there other constraint-type BCClasses that should be added to `_CONSTRAINT_PATCH_TYPES` proactively (wedge for 2D axisymmetric, cyclic for periodic)?
- The atomic commit currently rewrites the boundary file every time setup-bc runs (even for cases without constraint patches, the function reads the file but returns None). Acceptable cost? Or guard with an early-out when `_CONSTRAINT_PATCH_TYPES & {cls for ... in patches_with_class}` is empty?
