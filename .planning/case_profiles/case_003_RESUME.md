# case_003 · RESUME

**Last session**: 2026-05-11 (session 5 — F-NEW-19 fix + classifySurfaces
upstream wall surfaced)
**Status**: Phase 4a STEP→STL bridge shipped; workbench import endpoint
exercised (sessions 2-3); `detect_unit` body-class filter wired through
route (session 4); M6 mesh route observed to not converge on default
beginner sizing (session 4 follow-up); F-NEW-19 fix landed with 8 unit
tests (session 5); e2e validation surfaced **F-NEW-22 upstream wall**
(classifySurfaces super-linear on 393k facets). Not yet meshed; not yet
solved.

**Architectural correction**: this workbench uses **gmsh** for volumetric
meshing (M6) and **snappyHexMesh addLayers-only** for prism layers (M7).
The "STL → cells" wall is **M6 gmsh**, not M7 sHM.

**Stack of walls between case_003 and a meshed case**:
1. F-NEW-22 (upstream of M6 sizing) — `classifySurfaces` doesn't return
   in interactive time on 393k facets
2. F-NEW-19 (M6 sizing stage) — body-class-aware default lc — **FIXED
   in session 5** but doesn't fire until F-NEW-22 is dealt with
3. Topology partition for disconnected exterior shells (TopologyPartition
   Error path) — case_003 has 4 farfield walls + airframe + inlet/outlet/
   symmetry; unclear if partition succeeds or rejects
4. Cell budget cap (5M soft / 50M hard) — likely fine once lc is right
5. gmshToFoam container name mismatch (`cranky_black` running vs
   `cfd-openfoam` expected) — handles downstream of mesh generation

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
| **5c** | **F-NEW-22 mitigation** · classifySurfaces upstream wall — bypass via either (b) STL-solid-passthrough gmsh path (use named solid groups directly, skip parametric reclassification), or (a) coarser Q1/Q2 tessellation in bridge for industrial CAD payloads | spike OR sub-DEC | ~50-100 LOC depending on path | **NEXT** — blocks case_003 from reaching F-NEW-19's site |
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
required for reliable timeout). V27 already LANDED-by-V199-bridge.

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

## Next immediate action (session 6 candidate)

**Option A (recommended)**: Investigate F-NEW-22 — try (b) STL-solid-
passthrough gmsh path (skip `classifySurfaces` parametric
reclassification, use named solid groups from `gmsh.merge` directly).
This is the architecturally cleanest move: the bridge already emits
named solids and the workbench import path detects them; the gmsh
stage should be able to consume them without forcing a 393k-facet
reclassification. Spike-class if ≤50 LOC change at gmsh_runner.py;
sub-DEC if it touches contract.

**Option B**: Alt-path validate F-NEW-19 on a non-case_003 multi-
class STL (synthesize a small airframe + small CFD domain box, ~20k
total facets) — confirms session 5's fix fires end-to-end on a case
that doesn't trip F-NEW-22.

**Option C**: Quick F-NEW-15 substrate dig (≤5 min) — still cheap and
substrate-independent.
