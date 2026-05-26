# Dogfood retro · Real turbine cascade through the full pipeline · 2026-05-26

> Trigger: user asked to "先跑通真正意义上的全流程算例" (first run a genuinely
> end-to-end full-pipeline case) using a high-pressure high-temperature turbine
> rotor blade with internal + film cooling. After surfacing that the executor
> is incompressible-only, the user chose **"Real blade profile, RANS now"** —
> drive a real cambered turbine blade through the full pipeline as incompressible
> flow, surface every breakpoint, then scope the compressible/CHT engine work
> from evidence.
>
> Not a milestone cycle (M5 closed at `455f34d`); this is an engine-capability
> dogfood. Artifacts: `scripts/dogfood/cases/geometry/{make_turbine_cascade.py,
> turbine_cascade.stl, TURBINE_CASCADE_README.md}`.

## 做了什么 (what)

Built a parametric 2.5D turbine-blade cascade fluid domain (cambered blade, ~40°
turning, NACA-00 thickness, 6 named solids → patches) and drove it through
**import → mesh → setup-bc → solve → post**, all LLM-offline on the real
`cfd-openfoam` executor. Every stage passed on real geometry that is nothing
like the canonical LDC/BFS/channel cases:

| Stage | Outcome |
|---|---|
| Import (STL) | case `imported_2026-05-26T01-50-08Z_ed564909` |
| Mesh (gmsh→gmshToFoam) | 8,614 pts · **28,305 cells** · 6 patches, named-solid→patch 1:1 (F2 path) |
| setup-bc | icoFoam transient laminar, `from_stl_patches=1`, U_in=1.0 |
| **Solve** | **icoFoam CONVERGED** · end_time 4.999925 · continuity **1.97e-10** · p resid 1.4e-6 · **543.6 s** wall |
| Results | real `U`/`p`/`phi`, 6 time dirs, **U_max 1.84 m/s** |
| Post | `foamToVTK` surface(blade) + `streamLine`; **rendered in V4 Post** with real scalar range 0→1.60 m/s |

**Visual capstone confirmed** (the mandatory spot-check): the V4 Post viewport
shows the real cascade flow field — the blue cambered blade body (转子域 patch,
|U|≈0 at the no-slip wall) surrounded by the yellow/green cascade passages
colored by velocity magnitude, real legend `|U| 0→1.60 m/s`, honest "无基准对比
· 仅可视化结果 · 无 gold" (the M5 C3 de-fake correctly showing no fabricated
verdict). KPI strip reads real solver truth: 成功 / 543.6s / 退出码 0 /
残差 1.4e-6 / 无基准.

## 关键发现 (key findings)

1. **gmsh F2 path should trigger on surface CURVATURE, not only facet count.**
   The native ~3.7k-facet curved blade takes the baseline
   `classifySurfaces(40°) + createGeometry` path, which reparametrizes the
   surface and **fails**: "Invalid boundary mesh overlapping facets on surface
   11/14" / PLC segment-facet intersect — at BOTH a thin and a thick z-slab, so
   it's the blade curvature, not slab aspect ratio. The only reason the case
   meshed is that subdividing to 14,752 facets crosses
   `gmsh_runner._F2_PATH_FACET_THRESHOLD = 10_000`, which routes it to the F2
   (discrete-entity) path that skips classifySurfaces. **Real fix**: F2 routing
   should consider a curvature / dihedral-angle heuristic, not just facet count —
   a smooth high-facet box shouldn't need F2 while a coarse curved blade does.
   (Captured in the generator's `subdivide_4` docstring + README so the
   workaround is self-documenting, not a silent hack.)

2. **BC classifier has no cyclic / empty patch types.** `periodic_lower`,
   `periodic_upper`, and `frontAndBack` all default to no-slip walls (with an
   honest warning — no silent fakery). So this 2.5D cascade actually solves as a
   **3D duct with a blade inside**, not a true periodic 2D cascade. For a
   genuine cascade you'd want `periodic_*` → `cyclic` (or `cyclicAMI`) and
   `frontAndBack` → `empty`. The classifier maps unknown patches to walls
   conservatively, which is the *honest* default, but auto-configuring real
   cyclic+empty BCs is a true capability gap for periodic/cascade geometries.

3. **Executor is incompressible-only — the cooled HPT blade is out of reach.**
   Definitive (not inferred): the solve_runner convergence logic +
   `case_family_registry.SOLVER_TO_CASE_FAMILY_CANDIDATES` + every real case
   (backward_step / channel_flow_rans_sst / flat_plate_rans_sst) cover only
   icoFoam / simpleFoam / pisoFoam / pimpleFoam / interFoam. There is **no**
   rhoSimpleFoam/rhoPimpleFoam (compressible) or chtMultiRegionFoam (conjugate
   heat transfer) in the executor — those exist only in the AI-advisor V-series
   corpus. The user's target (internal cooling + film cooling + hot-gas CHT,
   transonic) needs compressible + multi-region CHT + cooling-hole geometry —
   none of which the engine can run today. This is the evidence the user asked
   for to scope the next milestone.

4. **The honest-telemetry work (M5) held up under a brand-new geometry.** The
   Post view rendered real run-derived data for a case it had never seen: real
   convergence gauge (98), real KPIs (543.6s / 1.4e-6), honest no-baseline
   verdict, real foamToVTK scalar range. No fabricated numbers leaked. The M5
   de-fake is geometry-agnostic, as intended.

## 治理 (governance)

| Gate | Status |
|---|---|
| Four-question gate | ✅ LLM offline (whole pipeline is Docker OpenFOAM, no AI call) · artifacts canonical (polyMesh, time dirs, VTK, residual log — all file-backed) · TrustGate (real residual source + honest no-baseline) · AI advisory-only (no AI ran the solve; engineer-initiated) |
| Codex review | N/A for this dogfood — the only code is a self-contained geometry generator (no routes/services/security surface touched); commit carries `confidence: high`. The engine findings are scoping inputs, not code changes. |
| Visual spot-check | ✅ real turbine flow field confirmed in V4 Post (this retro) |
| No date/schedule gating | ✅ |
| Notion sync | no new Accepted DEC this session; findings feed the (deferred) compressible/CHT milestone charter |

## 下一步 / 风险 (next / risks)

- **Compressible + CHT engine scoping** (the user's actual target). From the
  evidence, the cooled HPT blade needs, in rough order: (a) compressible solver
  family in the executor (rhoSimpleFoam/rhoPimpleFoam) + case-family registry
  entries; (b) thermal/energy BCs in the classifier; (c) conjugate heat transfer
  (chtMultiRegionFoam multi-region split) for solid-blade↔hot-gas; (d) cooling-
  hole geometry handling (film holes are sub-mm — meshing + the F2 curvature gap
  compound here). Each is a milestone-sized arc; (a)+(b) are the smallest first
  step that unlocks "hot gas over an uncooled blade".
- **F2 curvature heuristic** (finding #1) — small, high-leverage engine fix;
  candidate spike-class change to `_should_use_f2_path` (curvature/dihedral
  signal alongside the facet threshold). Would remove the subdivision workaround.
- **Cyclic/empty BC auto-config** (finding #2) — needed before any *true*
  periodic cascade; medium arc (classifier + template + AMI/coupled-patch
  validation).
- **Risk**: the subdivision workaround is documented but is still a workaround;
  if someone regenerates with `--subdivide 0` the case won't mesh. The README +
  docstring make the why explicit so it isn't mistaken for a bug.
