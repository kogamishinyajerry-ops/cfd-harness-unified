# Cross-repo ticket — `build_cad.py` farfield body overlap (class-wide)

**Status**: Open
**Filed**: 2026-05-12 (session 10 F-NEW-15 substrate dig)
**Updated**: 2026-05-12 session 12 — full survey across 11 case_* repos:
  6 of 11 cases confirmed affected (case_003/006/007/008/010/016).
**Affects repo**: `~/Desktop/case_*` (Codex-maintained case generators,
not this workbench).
**Affects file**: `scripts/build_cad.py` lines 191–219 in case_003;
analogous `build_domain_patches` / `build_farfield` / `build_patch_tags`
regions in case_006/007/008/010/016. See "Class-wide affected cases"
section below for per-case evidence.
**Blocks**: case_003 e2e mesh in `cfd-harness-unified` (F-NEW-26 in case_003
ramp log; see also DEC-V61-105 multi-named-solid intake path).
**Discovered by**: `cfd-harness-unified` sessions 6–9 substrate-first ramp.

## Symptom

`cfd-harness-unified` workbench's M6 mesh route rejects
`case_003 crm_hls_boundary_layer` source CAD with HXT PLC self-intersection
errors. The error coordinate magnitude matches the CFD domain corner
(e.g. `(1.60012e+06, 838200, -702488)` from HXT post-`Tolerance=1e-12`
load). gmsh diagnoses 28% of input boundary facets (~111k/393k) fail
constrained recovery during 3D meshing.

Multiple in-workbench mitigation paths (gmsh `Geometry.Tolerance`
tuning, `Part.makeCompound`, `Part.fuse + removeSplitter`, post-
tessellation vertex snap at 5 tolerances 1μm – 1cm) were all probed
and ruled out (session 8 ramp log). The bridge layer is
architecturally incapable of fixing this — the inputs themselves
overlap.

## Bisection evidence pointing at source CAD

`cfd-harness-unified` session 8 probe5
(`scripts/case_003/session8_probes/case003_session8_probe5_drop_medium.py`):
dropped subsets of bodies one at a time and re-fed to gmsh HXT.

| Bodies included | Total facets | HXT verdict |
|---|---|---|
| All 10 | 393,498 | PLC at (1.60012e+06, 838200, -702488) |
| Drop 3 mounts | ~393k | PLC at (-838200, 838124, 838124) |
| Drop 3 farfield_* | ~393k | PLC at (-838200, -762000, 838200) |
| Drop airframe | ~108 | PLC at (-838200, 838200, -702564) |
| **Just 3 farfield boxes** | **36 facets (9 KB STL)** | **PLC at (1.6002e+06, 838124, -702488)** |

The smallest reproducer is **3 farfield boxes alone — 36 triangles of
pure axis-aligned box geometry**. A self-intersection in 3 axis-aligned
boxes can only arise if the source geometry already overlaps.

## Root cause (this ticket)

`build_cad.py:191-219` constructs each named boundary as a **3D box of
thickness `t`**, placed AT the corresponding face of the CFD domain
cuboid:

```python
def build_domain_patches(wall_shapes, airframe):
    ...
    t = max(DOMAIN_PLATE_THICKNESS_MIN_MM, DOMAIN_PLATE_THICKNESS_FRAC * chord)
    return {
        "inlet":          make_box(t,  ly, lz, (domain_xmin, cy, cz)),
        "outlet":         make_box(t,  ly, lz, (domain_xmax, cy, cz)),
        "symmetry_plane": make_box(lx, t,  lz, (cx, domain_ymin, cz)),
        "farfield_top":   make_box(lx, ly, t,  (cx, cy, domain_zmax)),
        "farfield_bottom":make_box(lx, ly, t,  (cx, cy, domain_zmin)),
        "farfield_outer": make_box(lx, t,  lz, (cx, domain_ymax, cz)),
    }
```

Each plate extends across **two full domain dimensions** (e.g.
`farfield_top` is `lx × ly × t`, spanning the full x- and y-extent of
the domain at z = `domain_zmax`). Adjacent plates therefore overlap at
the CFD domain's edges and corners.

### Worked example: `farfield_top ∩ farfield_outer`

- `farfield_top`:   x ∈ [domain_xmin, domain_xmax], y ∈ [domain_ymin, domain_ymax],
  z ∈ [domain_zmax − t/2, domain_zmax + t/2]
- `farfield_outer`: x ∈ [domain_xmin, domain_xmax], y ∈ [domain_ymax − t/2, domain_ymax + t/2],
  z ∈ [domain_zmin, domain_zmax]

Intersection volume = `lx × t × t` (an edge running along x at the
domain's top-outer edge). Same shape edge-overlap exists for **every
pair of adjacent plates**:

| Pair | Overlap edge |
|---|---|
| inlet ∩ farfield_top   | t × ly × t (along y, at x=xmin, z=zmax) |
| inlet ∩ farfield_bottom| t × ly × t (along y, at x=xmin, z=zmin) |
| inlet ∩ farfield_outer | t × t × lz (along z, at x=xmin, y=ymax) |
| inlet ∩ symmetry_plane | t × t × lz (along z, at x=xmin, y=ymin) |
| outlet ∩ farfield_top  | t × ly × t |
| outlet ∩ farfield_bottom | t × ly × t |
| outlet ∩ farfield_outer  | t × t × lz |
| outlet ∩ symmetry_plane  | t × t × lz |
| symmetry_plane ∩ farfield_top   | lx × t × t |
| symmetry_plane ∩ farfield_bottom| lx × t × t |
| farfield_outer ∩ farfield_top   | lx × t × t |
| farfield_outer ∩ farfield_bottom| lx × t × t |

**13 pairwise overlapping edges** along the 12 edges of the CFD
domain cuboid (some edges are shared by 2 pairs). Plus 8 corners
where 3 plates meet — those are triple-overlaps.

The y=838,200 mm coordinate appearing repeatedly in PLC errors is
exactly the `domain_ymax` value (or equivalent corner offset) for
case_003's specific domain sizing constants.

## Recommended fix (3 options, ranked by quality)

### Option A (recommended — clean, watertight, preserves naming)

Construct a **single watertight CFD domain box**, then extract its 6
faces as named boundary groups (FreeCAD: face groups; CadQuery: face
selectors). The named-solid structure is preserved at the STEP/STL
export layer via assembly face groups or per-face metadata, not via
separate solid bodies.

This eliminates overlap by construction (one solid → no
self-intersection possible) and matches industrial CFD practice
(named patches, not named bodies, for CFD domain walls).

```python
def build_domain_patches_v2(wall_shapes, airframe):
    src_bb = airframe.BoundingBox()
    chord = max(src_bb.xlen, 100.0)
    xmin, xmax, ymin, ymax, zmin, zmax = bbox_union(wall_shapes)
    domain_xmin = xmin - UPSTREAM_CHORDS * chord
    # ... compute domain extent same as before ...
    lx = domain_xmax - domain_xmin
    ly = domain_ymax - domain_ymin
    lz = domain_zmax - domain_zmin

    # Single watertight domain box
    domain = make_box(lx, ly, lz, (cx, cy, cz))

    # Extract faces by normal direction, tag each with patch name
    faces = {}
    for f in domain.Faces():
        n = f.normalAt()
        if abs(n.x + 1.0) < 1e-6: faces["inlet"] = f
        elif abs(n.x - 1.0) < 1e-6: faces["outlet"] = f
        elif abs(n.y + 1.0) < 1e-6: faces["symmetry_plane"] = f
        elif abs(n.y - 1.0) < 1e-6: faces["farfield_outer"] = f
        elif abs(n.z + 1.0) < 1e-6: faces["farfield_bottom"] = f
        elif abs(n.z - 1.0) < 1e-6: faces["farfield_top"] = f
    return faces  # dict[str, cq.Face] — caller emits face groups
```

Caller adapts: instead of `asm.add(domain[name], name=name)` per body,
attach a single domain solid and per-face metadata that downstream
tools (FreeCAD STEP import + `meshFromShape` per face) can lift back
as named patches.

This requires downstream `cfd-harness-unified` bridge to be aware of
"single solid with face groups" pattern (currently it expects one
solid per named body). That is a parallel bridge improvement — but
the bridge can detect this pattern automatically via STEP face-group
metadata.

### Option B (minimal-change — pre-emit boolean subtraction)

Keep the 6-plate structure but **subtract overlaps before emit**.
After constructing all 6 plates, run boolean cuts so each plate
excludes the volume of every later-listed plate:

```python
def build_domain_patches_v2(wall_shapes, airframe):
    plates = {...}  # same 6 boxes as before
    # Establish a canonical order; later plates cut earlier ones
    order = ["inlet", "outlet", "symmetry_plane",
             "farfield_top", "farfield_bottom", "farfield_outer"]
    for i, name in enumerate(order):
        cutters = [plates[order[j]] for j in range(i+1, len(order))]
        for c in cutters:
            plates[name] = plates[name].cut(c)
    return plates
```

This gives each plate a unique non-overlapping volume (cutting
introduces L-shaped or notched solids at edges, but they're
watertight and don't self-intersect with neighbors).

Trade-off: the cut plates are no longer simple axis-aligned boxes —
they have notched edges where cuts happened. Tessellation produces
more facets per plate (was 12, now perhaps 30-50 each). Total facet
count goes up modestly but the workbench mesh route handles this
fine.

### Option C (defensive — zero-thickness face patches)

Replace each plate with a **zero-thickness face** (CadQuery `Workplane`
+ `polyline` + `close` + `wire` + `face`, not a `box`). Faces don't
have interior volume so they can't self-intersect at corners. But:
- Each face is now a degenerate "solid" (a flat sheet)
- FreeCAD `meshFromShape` on a face produces a 2D mesh that may not
  satisfy the workbench's "watertight per-solid" assumption
- Workbench bridge expects 3D solids in the STEP, this would change
  the bridge contract

Lower-quality option; included for completeness.

## Recommended path

**Option A**. It's the architecturally correct industrial CFD pattern
(one CFD domain, named boundary patches), eliminates the bug class
entirely, and matches the named-patch metadata convention that
`cfd-harness-unified`'s detect_patches already supports.

The workbench-side bridge already handles per-solid STL well; the
adaptation needed is to recognize "1 solid with N named face groups"
STEP input and emit per-face STL blocks. This is a parallel improvement
to the bridge that's worth doing regardless.

If Option A is not feasible in the short term, **Option B** is a
drop-in single-function change that doesn't touch the bridge.

## Validation criteria (for the cross-repo fix landing)

When the build_cad.py fix lands, regenerate `cad.step` and the workbench
bridge should produce a `combined.stl` that:

1. Passes `gmsh + HXT + Algorithm3D=10 + Geometry.Tolerance=1e-12 +
   F2 path (skip classifySurfaces)` end-to-end with a non-zero cell
   count
2. Produces no "missing facet recovery" warnings from HXT
3. Bisection test (drop body subsets one at a time) — any subset
   should mesh cleanly, not just the full assembly

Validation script: `cfd-harness-unified` session 8 probe5 can be
reused to verify the fix.

## Class-wide affected cases (session 12 full survey)

Surveyed all 11 build_cad.py files under `~/Desktop/case_*`. Same
thick-plate-at-face construction confirmed in **6 of 11 cases**:

| Case | Evidence | Severity |
|---|---|---|
| **case_003** crm_hls_boundary_layer | confirmed root-cause (this ticket); `make_box(t, ly, lz, ...)` per plate; 6 plates at 6 faces of CFD domain | base |
| **case_006** onera_m6_transonic | `farfield_box` (full cuboid) + 6 thin plates (`farfield_upstream/downstream/top/bottom/outboard/symmetry_plane_root` via `make_plate_x/y/z`) at the 6 faces of that cuboid → **DOUBLE overlap**: plates overlap each other AND each plate overlaps farfield_box | **worse** (cuboid + plates) |
| **case_007** kcs_ship_vof | 6 thick boxes (`water_inlet/water_outlet/atmosphere/side_walls/domain_bottom/symmetry_plane_centerline`) constructed as `make_box(center=(DOMAIN_*_MIN/MAX, ...), size=(PATCH_THICKNESS_MM, ...))` — identical case_003 pattern | base |
| **case_008** glc305_irt_lagrangian | `make_box(center=(X_MIN_MM, y_mid, 0.0), size=(PATCH_THICKNESS_MM, y_len, z_len))` × 6 patches | base |
| **case_010** drivaer_fastback_les | 6 thick boxes (`inlet/outlet/top/side_outboard/ground/symmetry_plane_centerline`) via `make_box((X_MIN_MM, y_mid, z_mid), (PATCH_THICKNESS_MM, y_len, z_len))` | base |
| **case_016** m219_cavity_des_acoustic | **14 thick patch tags** via `make_box(X_MIN_MM, X_MIN_MM + t, ...)`: inflow/outflow/top_far_field/far_field_port/starboard + flat_plate_upstream/downstream/side_port/starboard + cavity_floor/le_wall/te_wall/side_wall_port/starboard + fwh_porous_surface. Higher patch count → more pairwise edge overlaps | **worst** (14 plates) |

**Not affected** (5 cases, different geometry patterns):

| Case | Why not affected |
|---|---|
| case_004 nrel_phase_vi_mrf | Rotor case; blade/hub/spinner construction, no flat domain patches |
| case_005 rae_m2129_sduct | Internal duct case; boundary disks via `cylinder_along_x` (not boxes; at axially-distinct x positions) |
| case_009 sandia_flame_d | Cylindrical wedge-sector domain; `sector_solid` annuli at distinct radii (don't axis-aligned-overlap) |
| case_011 plate_fin_compact_hx | Internal HX; stack-pack geometry, no external domain patches |
| case_012 hvac_supply_diffuser | Internal HVAC; centered boxes via different layout |
| case_015 vattenfall_t_junction | Internal T-junction; cylindrical pipes via `cyl_x`/`cyl_z` |

**Conclusion**: 6 of 11 cases (54%) share the thick-plate-at-face
defect. This is a Codex case-generator framework-wide issue, not a
one-case bug.

**Recommendation**: prioritize fixing the shared pattern. Three
practical paths:

1. **Per-case retrofit** (most direct): apply Option A or B from the
   "Recommended fix" section to each affected build_cad.py
   independently. ~6 PRs but each is mechanical and case-local.

2. **Shared-helper extraction** (best long-term): factor out a
   `cfd_domain_patches(domain_bbox, thickness, names)` helper that
   applies Option A or B once. Migrate the 6 affected cases to use it.

3. **Workbench-side enforcement** (interim mitigation): the workbench
   side has already shipped session 11's defensive layer
   (`cfd-harness-unified` commit `4f671c4`), which detects this
   pattern at import time and emits a structured error pointing at
   this ticket. Affected cases will get clear diagnostics until the
   source fix lands. Does NOT replace the fix; just makes the symptom
   visible and actionable.

The 14-plate case_016 has the most pairwise edge overlaps and should
be a priority for the fix (or for not-yet-attempted import to confirm
behavior — but the workbench defensive layer will reject it loudly).

## Workbench-side state (no further action pending fix)

- F2 path is implemented and correct
  (`cfd-harness-unified` commit `bc38b7d`, session 9). On a clean
  multi-named-solid input it meshes correctly.
- M5.0 health check does not currently detect F-NEW-26-style overlap.
  Option F in case_003_RESUME.md (defensive health-check upgrade) is
  open as future work.
- case_003 ramp is on hold for this ticket. Subsequent cases (case_004
  CRM-HLS NREL phase VI MRF, etc.) may have similar overlap if
  build_cad.py is the shared CAD constructor — should review their
  build scripts for the same pattern.

## Contact

`cfd-harness-unified` ramp lead at the workbench repo. Reference
materials:

- `cfd-harness-unified` session 8 ramp_log entry + probe5 archive
  (`scripts/case_003/session8_probes/case003_session8_probe5_drop_medium.py`)
- `cfd-harness-unified` session 9 ramp_log + F2 redesign commit
  `bc38b7d`
- This ticket file as the canonical diagnosis
