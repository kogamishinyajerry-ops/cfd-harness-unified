# case_003 · RESUME

**Last session**: 2026-05-12 (session 13 — Option H closed: route
wiring gap for F-NEW-26 defensive layer fixed + 2 integration tests
pin the wiring; session 11 V61 claim "no route-code change needed"
corrected to V66 "route did NOT transparently carry; wiring closed
session 13")
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
~~1b. F-NEW-25 bridge per-body tessellation~~ — **RECLASSIFIED session 8
    as F-NEW-26**: source CAD overlap, not bridge artifact. Body-bisection
    probe (session 8 probe5) showed 3 farfield bodies alone (9 KB STL,
    36 facets) produce PLC self-intersection at same coordinate magnitude
    as the full 10-body case. Bridge transformations (compound / fuse /
    vertex snap) cannot construct self-intersection from non-overlapping
    inputs → inputs themselves overlap. **Blocker is now in Codex's
    `build_cad.py` farfield construction (cross-repo), not in this
    workbench.**
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
| ~~5c~~ | ~~F-NEW-22 + F-NEW-24 joint spike~~ F2 path: **session 7 commit `3d4a778`** used fast-classify (bug B in session 9); **session 9 redesign** skips `classifySurfaces` entirely + uses gmsh.merge-time discrete entities directly. Activation gate `_should_use_f2_path` (≥2 named solids + ≥10k facets) — default-arg pitfall fixed (bug A). Bypasses `partition_surfaces_by_body` (DEC-V61-104) because discrete entities lack edges; F2 target use cases (external aerodynamics) don't need interior-obstacle subtraction. | spike | service + tests | **REDESIGNED** session 9 — 54/54 tests pass on both seamed + disjoint topologies. case_003 e2e still gated on F-NEW-26 cross-repo. |
| ~~5d~~ | ~~F-NEW-24 bridge filter~~ — **REMOVED session 7**: F-NEW-24 is artifact, not substrate. No bridge change needed. |
| ~~5e~~ | ~~F-NEW-25 bridge sub-DEC~~ — **REDIRECTED session 8**: cannot fix at bridge layer; root cause is source CAD overlap |
| **5g** | **F-NEW-26 source-CAD fix** (cross-repo) | sub-DEC (other repo) | ~100 LOC in `build_cad.py` (Option A) | **DIAGNOSED + TICKETED** session 10. Root cause = `build_domain_patches` thick-plate-at-face construction; 13 pairwise edge-overlaps + 8 corner overlaps. Class-wide issue (≥case_003 + case_008 confirmed identical). Ticket: `.planning/cross_repo_tickets/2026-05-12_case_003_build_cad_farfield_overlap.md`. **PENDING cross-repo (Codex) action**. |
| ~~5h~~ | ~~F2 path validation alternative~~ synthetic industrial-scale fixture | spike | 50 LOC fixture + 3 tests | **DONE** session 9 — `large_seamed_multi_solid_box_stl` (12,288 facets) added to conftest. Surfaced 2 bugs in session 7 F2 path (default-arg pitfall + classify collapse on connected topology). Both fixed in session 9 redesign. |
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
F-NEW-25 separate bridge sub-DEC) + **V46** (session 8 — F-NEW-25
is symptom of F-NEW-26 source-CAD overlap; SUPERSEDES V43) + **V47**
(session 8 — `Part.makeCompound` purely topological, no vertex
stitching) + **V48** (session 8 — `fuse + removeSplitter` cleans
BRep but not tessellation; OCC tessellates per-face) + **V49**
(session 8 — post-tessellation vertex snap cannot fix F-NEW-26 at
any tolerance) + **V50** (session 8 — body-bisection: 3 farfield
bodies alone, 9 KB STL, reproduce PLC error → source CAD overlap
proven) + **V51** (session 8 — case_003 e2e blocker is cross-repo:
Codex `build_cad.py`, not workbench-side) + **V52** (session 9 —
F2 path skip `classifySurfaces` entirely; use gmsh.merge discrete
entities) + **V53** (session 9 — Python default-arg pitfall masked
session 7 F2 test setup bug) + **V54** (session 9 —
`classifySurfaces(angle=180°, ...)` topology-dependent: preserves
disjoint entities, collapses seamed) + **V55** (session 9 — F2
bypasses `partition_surfaces_by_body`; OK for external aerodynamics) +
**V56** (session 10 — F-NEW-26 root cause precisely localized:
`build_domain_patches` thick-plate-at-face; 12 edge + 8 corner
overlaps) + **V57** (session 10 — class-wide issue: case_003 + case_008
share identical pattern, ≥3 more cases likely affected) + **V58**
(session 10 — cross-repo ticket filed with 3 fix options ranked) +
**V59** (session 11 — M5.0 import-time AABB overlap detection lands
with 3-tier classification: containment / edge_overlap / significant)
+ **V60** (session 11 — cavity pattern preserved by classification:
no UX regression on LDC / cylinder-in-channel) + **V61** (session 11
— route layer transparently carries diagnostic; explicit route-test
deferred to Option H) + **V62** (session 12 — full survey: 6/11 cases
affected; 5 not) + **V63** (session 12 — case_006 DOUBLE overlap
worst-case identified) + **V64** (session 12 — case_016 has 14 patch
tags; worst extent of bug) + **V65** (session 12 — recommended fix
path = shared-helper extraction across 6 affected cases).
V27 already LANDED-by-V199-bridge.

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

Session 10 closed Option E. case_003 e2e now waits on cross-repo
Codex action (F-NEW-26 ticket). Workbench-side actionable items:

~~Option F (session 11)~~ — **DONE** session 11 commit `4f671c4`. M5.0
import-time body-pair AABB overlap detection landed with 3-tier
classification (containment / edge_overlap / significant). case_003
F-NEW-26 pattern reproduces in tests and triggers the systematic-CAD-
bug error path. Cavity / interior-obstacle cases (LDC, cylinder-in-
channel) preserved as silent (containment-only). 9 new tests, 76/76
in ingest+meshing.

~~Option G (session 12)~~ — **DONE** session 12 (no commit; doc-only
class-wide survey). 6 of 11 cases confirmed affected
(case_003/006/007/008/010/016); 5 not affected with reasons. Ticket
updated with recommended fix paths.

~~Option H (session 13 — route-layer test)~~ — **DONE** session 13.
Verification revealed a **wiring gap**: route called `run_health_
checks` without `body_aabbs`, so defensive layer was dead code at the
HTTP layer (only the `ingest_stl` wrapper exercised it). Gap closed:
`_per_body_max_extents` → `_per_body_info` (returns both extents +
AABBs); route passes both; `failing_check` taxonomy adds
`"body_overlap"`; `_select_primary_error` prefers AABB message over
co-occurring watertight error. 2 new route tests (positive: 6-plate
→ 400 with ticket reference; negative: disjoint named solids → 200
silent). V66/V67/V68/V69 logged. Session 11 V61 claim corrected.

**Option C**: F-NEW-17 fix — adjust the airframe-class extent band.
Independent; can ship anytime. ~30-50 LOC.

**Option I (proactive — session 13+)**: pick an affected case
(case_007 ship_vof or case_010 drivaer recommended as simpler
parallels of case_003) and attempt end-to-end import + diagnose
whether the F-NEW-26 defensive layer correctly catches that case's
specific overlap pattern. Validates the defensive layer against
real-world variations of the bug.

Recommended order: ~~H (close route-side test gap)~~ DONE session 13
→ ~~I~~ DEFERRED (low marginal value — see judgment below)
→ C (independent · F-NEW-17 airframe extent band).

**Option I deferral (session 13 judgment)**: case_007 + case_010 both
use the identical 6-plate `make_box`-at-6-faces pattern as case_003
(verified session 12 survey + session 13 grep on
`~/Desktop/case_007_kcs_ship_vof/scripts/build_cad.py:227-258` and
`~/Desktop/case_010_drivaer_fastback_les/scripts/build_cad.py:180-199`
— both define `build_domain_patches()` returning 6 thick-plate
solids). The session 13 synthetic fixture (`farfield_6_plate_stl`)
already proves the defensive layer catches this pattern with 12
edge-overlap pairs. Running the actual build_cad.py end-to-end on
these cases would re-prove the same conclusion with different
domain dimensions — incremental, not informative. The right next
moves are: (1) wait for cross-repo Codex fix of build_cad.py
(ticket pending); (2) Option C (independent · F-NEW-17 airframe
extent band, shippable anytime); (3) advance to next priority case
ramp. If a future affected case uses a non-6-plate pattern (e.g.,
case_016 with 14 patch tags), revisit Option I then.
