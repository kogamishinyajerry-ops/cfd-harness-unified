# case_003 · RESUME

**Last session**: 2026-05-12 (session 7 — F-NEW-24 reclassified as
gmsh-tolerance artifact + F-NEW-25 confirmed real multi-instance)
**Status**: Phase 4a STEP→STL bridge shipped; workbench import endpoint
exercised (sessions 2-3); `detect_unit` body-class filter wired through
route (session 4); M6 mesh route observed to not converge on default
beginner sizing (session 4 follow-up); F-NEW-19 fix landed with 8 unit
tests (session 5); F-NEW-22 classifySurfaces super-linearity diagnosed
to `boundary=True / forReparametrization=True` flags, F2 fast-mode path
proven ~80× faster (session 6); F-NEW-24 (9356 degenerate triangles)
reclassified as gmsh `Geometry.Tolerance=1e-8` artifact on km-scale CAD
(session 7); F-NEW-25 confirmed real multi-instance with HXT diagnostic
evidence (session 7). case_003 e2e still blocked, now exclusively by
F-NEW-25 (bridge per-body tessellation produces mis-stitched shared
edges).

**Architectural correction**: this workbench uses **gmsh** for volumetric
meshing (M6) and **snappyHexMesh addLayers-only** for prism layers (M7).
The "STL → cells" wall is **M6 gmsh**, not M7 sHM.

**Stack of walls between case_003 and a meshed case** (revised session 6):
1. ~~F-NEW-22 (upstream of M6 sizing) — `classifySurfaces` doesn't return
   in interactive time on 393k facets~~ — **FIX FOUND session 6**: F2 path
   (`classifySurfaces(angle=180°, boundary=False, forReparametrization=False)`
   + skip `createGeometry()` + `addSurfaceLoop + addVolume`). NOT YET
   IMPLEMENTED in `gmsh_runner.py` — implementation deferred until
   substrate walls (#1a, #1b below) cleared, otherwise no e2e validation
   path on case_003.
~~1a. **F-NEW-24**~~ — RECLASSIFIED session 7 as gmsh `Geometry.Tolerance=1e-8`
    artifact on km-scale CAD. Fix is a single gmsh option set
    (`Tolerance=1e-12`), bundled into F2 path implementation (V45).
    NOT a real substrate wall.
1b. **F-NEW-25 (CONFIRMED REAL)** — multi-instance bridge stitching
    issue: at least 2 distinct self-intersection points along y=838200 mm
    farfield boundary (HXT PLC errors at (-838124, 838200, 838124) under
    Tolerance=1e-8 and (1.6e6, 838200, -702488) under Tolerance=1e-12).
    ~28% of input facets (111k/393k) fail HXT constrained recovery.
    Root cause: `step_to_per_body_stl` runs FreeCAD `MeshPart.meshFromShape`
    per body independently; adjacent farfield boxes share edges but
    independent tessellations don't enforce vertex identity. Bridge needs
    pre-tessellation farfield-merge (sub-DEC, ~100 LOC sidecar change).
1c. **F-NEW-17 firing (session 6 obs)** — 152m CRM-HLS airframe exceeds
    F-NEW-19's 100m airframe-class ceiling. Filter retains only 18-27m
    sub-structures, rejects actual airframe. Filter band needs adjustment
    for industrial-scale airframes >100m.
2. F-NEW-19 (M6 sizing stage) — body-class-aware default lc — **FIXED
   session 5** but doesn't fire correctly on case_003 (F-NEW-17 issue);
   even with correct sizing, blocked by F-NEW-24/25.
3. Topology partition for disconnected exterior shells (TopologyPartition
   Error path) — case_003 has 4 farfield walls + airframe + inlet/outlet/
   symmetry; unclear if partition succeeds or rejects.
4. Cell budget cap (5M soft / 50M hard) — likely fine once lc is right.
5. gmshToFoam container name mismatch (`cranky_black` running vs
   `cfd-openfoam` expected) — handles downstream of mesh generation.

## Where to pick up

1. `.planning/case_profiles/case_003_ramp_log_2026-05-11.md` for the
   full F-NEW-1..18 list, session-1 through session-4 narrative, and
   V-series queue (V25..V31).
2. Session 3 driver: `scripts/case_003/ramp_session_3_workbench.py`.
3. Session 4 inline probe (no driver script — single python -c block in
   ramp_log session 4): re-uploads spike #2 combined.stl, verifies
   `unit_guess=mm` on `POST /api/import/stl`.
4. STL evidence: `ui/backend/user_drafts/imported/case_003_crm_hls/stl_session_2/` (gitignored, regenerable in ~7 s).
5. Session 4 evidence: `combined_session_4.stl` in same dir.

## Outstanding blockers — prioritized by substrate evidence

| # | Finding | Class | Estimate | Status |
|---|---|---|---|---|
| ~~1~~ | ~~F-NEW-9 · 50 MB cap~~ | ~~spike~~ | ~~3 LOC~~ | **DONE** session 3 · cap raised to 200 MB |
| ~~2~~ | ~~F-NEW-10 · combined multi-solid ASCII emit~~ | ~~spike~~ | ~~21+25 LOC~~ | **DONE** session 3 · `combine_per_body_stls` |
| ~~3~~ | ~~F-NEW-12 · body-class filter for unit_guess~~ | ~~spike~~ | ~~25+test LOC~~ | **DONE** session 3 · `detect_unit(body_extents_raw=...)` |
| ~~4~~ | ~~F-NEW-12 wiring · route call detect_unit~~ | ~~spike~~ | ~~~70 LOC + 2 tests~~ | **DONE** session 4 · `unit_guess` now `mm` on case_003 combined STL |
| ~~5~~ | ~~M7 sHM real run~~ — **superseded by session 4 follow-up M6 observation**; the relevant stage in this codebase is M6 gmsh, not M7 sHM | obs | n/a | **DONE-as-observation** session 4 |
| ~~5a~~ | ~~F-NEW-19 mitigation spike · body-class-aware default lc~~ | ~~spike~~ | ~~~80 LOC + 8 tests~~ | **DONE** session 5 — but not yet exercised end-to-end (blocked by F-NEW-22) |
| **5c** | **F-NEW-22 + F-NEW-24 joint spike** · F2 path implementation in `gmsh_runner.py`: fast-classify (`boundary=False`, `forReparametrization=False`) + skip `createGeometry()` + `addSurfaceLoop` + `addVolume` + `Geometry.Tolerance=1e-12` for multi-named-solid industrial CAD payloads. Conditionally activated by detected solid count + facet count threshold | spike | ~80-150 LOC + 4-6 tests | **NEXT** — unit-test on synthetic 2-body STL; case_003 e2e validation gated on 5d |
| ~~5d~~ | ~~F-NEW-24 bridge filter~~ — **REMOVED session 7**: F-NEW-24 is artifact, not substrate. No bridge change needed. |
| **5e** | **F-NEW-25 mitigation** · bridge pre-tessellation farfield-merge in `_freecad_step_to_stl_sidecar.py`: detect bodies whose faces share edges (or `farfield`-prefixed) and join via `Part.Fuse` before `MeshPart.meshFromShape` | sub-DEC | ~100 LOC sidecar + 2-3 tests | clears the **only** remaining substrate wall before case_003 e2e |
| **5f** | **F-NEW-17 mitigation** · adjust `_is_industrial_plausible_extent` upper bound for industrial airframes >100m (CRM-HLS at 152m fails); needs configurable band per body-class | spike | ~30-50 LOC + tests | independent of 5c/5e; can ship anytime; not blocking F2 implementation if F2 ignores the filter |
| **5b** | **F-NEW-20 mitigation spike** · M6 route soft wall-clock timeout + `gmsh_timeout` failing_check; protects workbench from degenerate sizing burning CPU indefinitely. **F-NEW-23 add**: in-process Python signals don't interrupt gmsh C++ stages — must use subprocess-wrapper + external kill | spike | ~40 LOC + 1 test | optional after 5c |
| **6** | **F-NEW-15 substrate dig** · was Codex's `build_cad.py` for case_003 v1 intentionally emitting a 2-component airframe? ≤5 min grep at `~/Desktop/case_003_crm_hls_boundary_layer/` | substrate / data | ≤5 min | open |
| **6a** | **F-NEW-19 alt-path probe** · trigger M6 route with explicit `sizing_field` (N2.1 custom mode) on a non-case_003 multi-class STL to validate F-NEW-19 fires end-to-end — confirms session 5's fix on a path that actually reaches the lc-decision site | observation | ~10 min | optional, validates session 5 fix on real e2e flow |
| 7 | **F-NEW-17** · Body-class filter cross-talks with F-NEW-4 (Codex 3× scaling); ship/large geometries may need configurable industrial range | enhancement / not blocking | n/a | revisit when ≥1 case has all-bodies-above-100 m |
| 8 | **F-NEW-13 truth-chain copy** · "watertight" passes on boundary-only payload; UX/copy issue at M-CONTROL-RAIL | UX / docs | deferred | deferred to M-CONTROL-RAIL UI work |
| 9 | **V-series authoring** · V25/V26/V28/V29/V30/V31 still queued for `industrial_case_solver_findings.md` | docs | n/a | low priority, batch when next touching V-series |

Recommended next-session order: **5 first (M7 sHM observation, the big
unknown), 6 if time permits (cheap, related to 5)**. 7-9 are not
blockers.

## V-series queue (10 not-yet-committed rows)

V25 + V26 + V28 + V29 + V30 + **V31** (session 4 wiring landed —
route now calls `detect_unit` with body-class filter) + **V32**
(session 4 follow-up — M6 default beginner lc unworkable on
industrial multi-class STEP) + **V33** (session 4 follow-up — M6
route lacks soft wall-clock timeout) + **V34** (session 5 —
classifySurfaces super-linear on 393k facets) + **V35** (session 5
— gmsh C++ stages don't yield to Python SIGALRM, subprocess
required for reliable timeout) + **V36** (session 6 — F2 path:
`classifySurfaces(boundary=False, forReparametrization=False)` +
skip `createGeometry` + `addSurfaceLoop + addVolume` is the
F-NEW-22 architectural fix, ~80× speedup on classify) + **V37**
(session 6 — `boundary` and `forReparametrization` flags drive
classifySurfaces super-linearity, not the `angle` parameter) +
**V38** (session 6 — F-NEW-24: combined STL has 9356 degenerate
triangles; bridge filter needed) + **V39** (session 6 — F-NEW-25:
case_003 STL has surface self-intersections at farfield shared
corners; bridge vertex-snap or pre-tessellation merge needed) +
**V40** (session 6 — F-NEW-17 fires in the wild: 152m CRM-HLS
airframe exceeds 100m airframe-class ceiling) + **V41** (session 7
— gmsh default `Geometry.Tolerance=1e-8` mismatched to km-scale
industrial CAD; set Tolerance=1e-12 on multi-named-solid loads) +
**V42** (session 7 — F-NEW-24 is V41 artifact, NOT a real
substrate issue; SUPERSEDES V38) + **V43** (session 7 — F-NEW-25
is multi-instance real: ≥2 self-intersections along y=838200 mm
farfield boundary; 28% of facets fail HXT constrained recovery;
SUPERSEDES V39 single-instance framing) + **V44** (session 7 —
HXT diagnostically superior to Delaunay 3D for substrate-error
cases; fast-fails with named coord + entity pair) + **V45**
(session 7 — F-NEW-22 + F-NEW-24 fixable as one F2-path spike,
F-NEW-25 separate bridge sub-DEC). V27 already LANDED-by-V199-bridge.

V32 needs status update next batch: **F-NEW-19 fix LANDED session 5**;
the unworkable-default-lc issue is solved for cases that reach the
lc-decision site, but case_003 needs F-NEW-22 first.

## Reproduce session 2 STL output

```bash
.venv/bin/python -c "
from pathlib import Path
from ui.backend.services.geometry_ingest.freecad_step_to_stl import step_to_per_body_stl
step_to_per_body_stl(
    step_path=Path('ui/backend/user_drafts/imported/case_003_crm_hls/raw/cad.step'),
    out_dir=Path('ui/backend/user_drafts/imported/case_003_crm_hls/stl_session_2'),
)
"
```

## Reproduce session 3 workbench probes

```bash
.venv/bin/python scripts/case_003/ramp_session_3_workbench.py
```

## Reproduce session 4 end-to-end probe

```bash
.venv/bin/python -c "
import sys; sys.path.insert(0, '.')
from pathlib import Path
from fastapi.testclient import TestClient
from ui.backend.main import app
from ui.backend.services.geometry_ingest.freecad_step_to_stl import combine_per_body_stls
stl_dir = Path('ui/backend/user_drafts/imported/case_003_crm_hls/stl_session_2')
combined = combine_per_body_stls(stl_dir, out_path=stl_dir / 'combined_session_4.stl')
client = TestClient(app)
r = client.post('/api/import/stl', files={'file': ('combined.stl', combined.read_bytes(), 'application/octet-stream')})
print(r.status_code, r.json()['ingest_report']['unit_guess'])
"
# Expect: 200 mm
```

## Next immediate action (session 7-8 candidate)

Session 7 collapsed F-NEW-24 into an artifact (gmsh tolerance) and
confirmed F-NEW-25 is the only remaining substrate wall. The plan
forward is now:

**Option A (recommended, session 7 continuation)**: F2 path joint spike
in `gmsh_runner.py` — bundles F-NEW-22 + F-NEW-24 fix into one change:
fast-classify + skip createGeometry + addSurfaceLoop + addVolume +
`Geometry.Tolerance=1e-12`. Unit-tested on synthetic 2-body multi-named-
solid STL. ~80-150 LOC service code + 4-6 tests. Same shape as F-NEW-19's
session-5 landing (unit-validated; e2e on case_003 gated on 5e).

**Option B (session 8)**: F-NEW-25 sub-DEC — bridge sidecar pre-
tessellation farfield-merge via `Part.Fuse` on coplanar / edge-sharing
bodies before `MeshPart.meshFromShape`. ~100 LOC sidecar + 2-3 tests.
Sub-DEC because it touches the bridge's emit contract (number of output
bodies may shrink).

**Option C**: F-NEW-17 fix — adjust the airframe-class extent band.
Independent of 5c/5e/F2, can ship anytime. ~30-50 LOC.

Recommended order: A (this session, if energy permits) → B (next
session) → C (any time). After A+B, case_003 e2e mesh should clear
on the F2 + clean-stitched-substrate combination.
