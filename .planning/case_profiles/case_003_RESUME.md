# case_003 · RESUME

**Last session**: 2026-05-11 (session 6 — F-NEW-22 architectural fix
identified + F-NEW-24/25 substrate walls surfaced)
**Status**: Phase 4a STEP→STL bridge shipped; workbench import endpoint
exercised (sessions 2-3); `detect_unit` body-class filter wired through
route (session 4); M6 mesh route observed to not converge on default
beginner sizing (session 4 follow-up); F-NEW-19 fix landed with 8 unit
tests (session 5); F-NEW-22 classifySurfaces super-linearity diagnosed
to `boundary=True / forReparametrization=True` flags, F2 fast-mode path
proven ~80× faster (session 6); case_003 e2e still blocked, now by
substrate-level walls **F-NEW-24** (9356 degenerate triangles) and
**F-NEW-25** (surface self-intersection at farfield corners). Not yet
meshed; not yet solved.

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
1a. **F-NEW-24 (NEW)** — `combine_per_body_stls` emits combined STL with
    9,356 degenerate triangles on 384k total. Delaunay 3D spirals on
    these; HXT fast-fails. Bridge needs degenerate-triangle filter.
1b. **F-NEW-25 (NEW)** — case_003 combined STL has surface
    self-intersections at farfield-body shared corners (HXT PLC error
    at coord ~(838m, 838m, 838m)). Per-body emit + concatenate doesn't
    snap vertices at shared edges. Bridge needs vertex-snap or
    pre-tessellation farfield-merge.
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
| ~~5c~~ | ~~F-NEW-22 mitigation (architectural)~~ | spike | ~50-100 LOC | **PATH FOUND session 6** — F2 path (fast-classify + skip createGeometry + addSurfaceLoop + addVolume). Implementation deferred until F-NEW-24/25 cleared so e2e validation is feasible. |
| **5d** | **F-NEW-24 mitigation** · bridge degenerate-triangle filter in `combine_per_body_stls` or `freecad_step_to_stl.step_to_per_body_stl` | spike | ~50-100 LOC + 2-3 tests | **NEXT** — upstream wall that blocks F2 path validation on case_003 |
| **5e** | **F-NEW-25 mitigation** · bridge vertex-snap or pre-tessellation farfield-merge to eliminate shared-edge micro-gaps | sub-DEC | ~100-200 LOC | follows 5d — clears the last substrate wall before F2 implementation |
| **5f** | **F-NEW-17 mitigation** · adjust `_is_industrial_plausible_extent` upper bound for industrial airframes >100m (CRM-HLS at 152m fails); needs configurable band per body-class | spike | ~30-50 LOC + tests | independent of 5d/5e; can ship anytime; not blocking F2 implementation if F2 ignores the filter |
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
airframe exceeds 100m airframe-class ceiling). V27 already
LANDED-by-V199-bridge.

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

## Next immediate action (session 7 candidate)

Session 6 closed the F-NEW-22 architectural unknown (F2 path is the fix)
but surfaced two substrate-level walls that block end-to-end validation
on case_003. The remaining work is now substrate-bridge, not gmsh-runner.

**Option A (recommended)**: F-NEW-24 spike — bridge degenerate-triangle
filter in `combine_per_body_stls` or upstream `step_to_per_body_stl`.
Reproduce on `combined_session_4.stl`: count degenerates, filter, re-emit,
verify gmsh reports 0 degenerates. ~50-100 LOC + 2-3 tests. Cheapest
unblock on case_003.

**Option B**: F2 path spike implementation in `gmsh_runner.py` with
synthetic 2-body STL unit test. Decouples from case_003 by validating
F2 on a clean synthetic substrate. ~80-150 LOC + 4-6 tests. Same shape
as F-NEW-19's session-5 landing (unit-tested fix; e2e on case_003 follows
when substrate clears).

**Option C**: F-NEW-25 sub-DEC — bridge vertex-snap or pre-tessellation
farfield-merge. More invasive than 5d but addresses the deeper substrate
issue. ~100-200 LOC. Sub-DEC because it touches the bridge's emit
contract.

**Option D**: F-NEW-17 fix — adjust the airframe-class extent band.
Independent of 5d/5e/F2, can ship anytime. ~30-50 LOC.

Recommended order: A (5d) → B (F2 implementation) → C (5e) → D (5f).
Skipping straight to B without 5d means F2 lands without e2e validation
on case_003.
