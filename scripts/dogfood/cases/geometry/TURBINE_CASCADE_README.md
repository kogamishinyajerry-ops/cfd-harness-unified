# Turbine cascade — full-pipeline dogfood case

A 2.5D **turbine-blade cascade** fluid domain, used to prove the workbench can
drive a *real* (non-canonical, curved-wall, multi-patch) industrial-style
geometry through the entire pipeline — **import → mesh → setup-bc → solve →
post** — end to end, LLM-offline, on the real OpenFOAM executor.

> This case was built (2026-05-26) after the user asked to "先跑通真正意义上的
> 全流程算例" (first run a genuinely end-to-end full-pipeline case) using a
> turbine rotor blade. The cooled-blade target (internal + film cooling,
> compressible CHT) is **out of reach of the current executor** — see the
> "Engine findings" section; this case is the incompressible-RANS-now path the
> user chose, which surfaces every real breakpoint.

## Geometry

`make_turbine_cascade.py` generates a single-passage cascade fluid domain:

- **Blade**: parametric cambered profile — camber-line turning from φ_LE = +15°
  to φ_TE = −25° (~40° turning), NACA-00 thickness distribution (t_max = 0.10),
  chord 1.0, centred in a 3.5 × 1.0 domain (x ∈ [−1, 2.5], y ∈ [0, 1]).
- **2.5D extrusion**: one cell-thick in z (z ∈ [0, 0.1]).
- **6 named solids** (→ OpenFOAM patches 1:1 via the gmsh F2 path):
  `inlet`, `outlet`, `periodic_lower`, `periodic_upper`, `blade`, `frontAndBack`.
- Domain Delaunay-triangulated around the blade polygon; watertight
  (every edge shared by exactly 2 facets — asserted in the generator).

### Regenerate the STL

```bash
.venv/bin/python scripts/dogfood/cases/geometry/make_turbine_cascade.py
# -> turbine_cascade.stl : 14,752 facets, WATERTIGHT: True
```

`--subdivide 0` emits the native ~3.7k-facet mesh (takes the classifySurfaces
gmsh path, which **fails** on the curved blade — see finding #1). Default
(`--subdivide 1`, ×4 → 14,752 facets) crosses the backend's F2-path facet gate
so gmsh skips reparametrization.

## Full-pipeline reproduction (real OpenFOAM)

Prereqs: `cfd-openfoam` Docker container up (OF10 amd64 emulated) + backend on
:8001 (see `~/.claude/.../reference_cfd_main_worktree_location.md`).

```bash
BASE=http://127.0.0.1:8001
# 1. import (STL-only)
curl -sS -F file=@scripts/dogfood/cases/geometry/turbine_cascade.stl \
     "$BASE/api/import/stl"            # -> {case_id: imported_...}
# 2. mesh (gmsh -> gmshToFoam -> polyMesh) — F2 path preserves the 6 patches
curl -sS -X POST "$BASE/api/import/$CID/mesh"
# 3. setup-bc — from the STL patches (incompressible, U_in along -x)
curl -sS -X POST "$BASE/api/import/$CID/setup-bc?from_stl_patches=1&inlet_speed=1.0&delta_t=0.001"
# 4. solve (icoFoam, transient laminar)
curl -sS -X POST "$BASE/api/import/$CID/solve"
# 5. post overlays
curl -sS "$BASE/api/import/$CID/post/surface.vtp?patch=blade" -o /tmp/blade.vtp
curl -sS "$BASE/api/import/$CID/post/streamlines.vtp"          -o /tmp/streams.vtp
```

## Proven result (run 2026-05-26T02-01-12Z)

| Stage | Outcome |
|---|---|
| Mesh | 8,614 points · 28,305 cells · 6 patches (1:1 to named solids) |
| Solver | `icoFoam` (incompressible transient laminar) |
| Convergence | **end_time 4.999925** · continuity sum-local **1.97e-10** · p resid **1.4e-6** |
| Wall time | **543.6 s** (OF10 amd64 emulated on arm64) |
| Fields | real `U`/`p`/`phi` across 6 time dirs; **U_max 1.84 m/s** |
| Post | `foamToVTK` surface (blade) + integrated `streamLine`; render in V4 Post with real scalar range 0 → 1.60 m/s |

## Engine findings (the point of the dogfood — see the retro)

1. **gmsh F2 path should trigger on surface CURVATURE, not only facet count.**
   The native ~3.7k-facet curved blade takes the `classifySurfaces(40°) +
   createGeometry` path, which reparametrizes and fails with "Invalid boundary
   mesh / overlapping facets". The subdivision-to-14.7k workaround only works
   because it crosses `_F2_PATH_FACET_THRESHOLD`. A curvature/aspect heuristic
   would route curved-wall geometries to the F2 (discrete) path directly.
2. **BC classifier has no cyclic / empty patch types.** `periodic_lower/upper`
   and `frontAndBack` default to no-slip walls (honest warning, no silent
   fakery), so this 2.5D cascade solves as a **3D duct with a blade**, not a
   true periodic 2D cascade. Auto-configuring genuine cyclic + empty BCs is a
   real gap for cascade/periodic cases.
3. **Executor is incompressible-only** (icoFoam/simpleFoam/pisoFoam/pimpleFoam/
   interFoam). The user's cooled HPT blade needs compressible (rhoSimpleFoam/
   rhoPimpleFoam) + conjugate heat transfer (chtMultiRegionFoam) — those live
   only in the AI-advisor V-series corpus, not the executor. Scoped as the
   evidence-based next milestone.
