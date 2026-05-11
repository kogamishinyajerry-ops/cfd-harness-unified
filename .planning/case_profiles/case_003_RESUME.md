# case_003 · RESUME

**Last session**: 2026-05-11 (session 4 — wire body_extents_raw into
workbench route + M6 mesh-generation observation)
**Status**: Phase 4a STEP→STL bridge shipped; workbench import endpoint
exercised (sessions 2-3); `detect_unit` body-class filter wired through
route (session 4); M6 mesh route observed to **not converge in 7+ min**
on case_003 default beginner sizing (session 4 follow-up). Not yet
meshed; not yet solved.

**Architectural correction**: this workbench uses **gmsh** for volumetric
meshing (M6) and **snappyHexMesh addLayers-only** for prism layers (M7).
The "STL → cells" wall is **M6 gmsh**, not M7 sHM. Sessions 5+ should
plan against gmsh walls (F-NEW-19, F-NEW-20), not full-sHM walls.

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
| **5a** | **F-NEW-19 mitigation spike** · body-class-aware default lc — reuse session 3 spike #3's filter at the gmsh-pipeline boundary to compute `_default_characteristic_length` from airframe-class bodies only, not the multi-class diagonal | spike | ~40 LOC + 1 test + 1 timed M6 probe | **NEXT** |
| **5b** | **F-NEW-20 mitigation spike** · M6 route soft wall-clock timeout + `gmsh_timeout` failing_check; protects workbench from degenerate sizing burning CPU indefinitely | spike | ~20 LOC + 1 test | optional after 5a |
| **6** | **F-NEW-15 substrate dig** · was Codex's `build_cad.py` for case_003 v1 intentionally emitting a 2-component airframe? ≤5 min grep at `~/Desktop/case_003_crm_hls_boundary_layer/` | substrate / data | ≤5 min | open |
| **6a** | **F-NEW-19 alt-path probe** · trigger M6 route with explicit `sizing_field` (N2.1 custom mode) to validate that engineer-supplied sizing *does* converge — confirms hypothesis without code change | observation | ~5 min | optional, validates 5a hypothesis pre-implementation |
| 7 | **F-NEW-17** · Body-class filter cross-talks with F-NEW-4 (Codex 3× scaling); ship/large geometries may need configurable industrial range | enhancement / not blocking | n/a | revisit when ≥1 case has all-bodies-above-100 m |
| 8 | **F-NEW-13 truth-chain copy** · "watertight" passes on boundary-only payload; UX/copy issue at M-CONTROL-RAIL | UX / docs | deferred | deferred to M-CONTROL-RAIL UI work |
| 9 | **V-series authoring** · V25/V26/V28/V29/V30/V31 still queued for `industrial_case_solver_findings.md` | docs | n/a | low priority, batch when next touching V-series |

Recommended next-session order: **5 first (M7 sHM observation, the big
unknown), 6 if time permits (cheap, related to 5)**. 7-9 are not
blockers.

## V-series queue (8 not-yet-committed rows)

V25 + V26 + V28 + V29 + V30 + **V31** (session 4 wiring landed —
route now calls `detect_unit` with body-class filter) + **V32**
(session 4 follow-up — M6 default beginner lc unworkable on
industrial multi-class STEP) + **V33** (session 4 follow-up — M6
route lacks soft wall-clock timeout). V27 already
LANDED-by-V199-bridge.

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

## Next immediate action (session 5 candidate)

**Option A (recommended)**: Run 6a first (5-min explicit `sizing_field`
probe to validate F-NEW-19 hypothesis) → if M6 converges with custom
sizing, implement 5a (body-class-aware default lc spike) → commit.
Validate-then-implement preserves substrate-first discipline.

**Option B**: Jump straight to 5a implementation if confidence in
F-NEW-19 root cause hypothesis is already sufficient (the docstring +
formula in `gmsh_runner._default_characteristic_length` is explicit
about the "typical box geometry" calibration).

**Option C**: Quick F-NEW-15 substrate dig (≤5 min) before anything
else — independent of M6 work, cheap, surfaces whether the airframe
is intentionally disconnected in `build_cad.py`.
