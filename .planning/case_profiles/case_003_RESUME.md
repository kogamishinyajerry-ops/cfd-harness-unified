# case_003 · RESUME

**Last session**: 2026-05-11 (session 4 — wire body_extents_raw into workbench route)
**Status**: Phase 4a STEP→STL bridge shipped; workbench import endpoint
exercised (sessions 2-3); `detect_unit` body-class filter wired through
route (session 4). Not yet meshed; not yet solved. **Next wall = M7
snappyHexMesh on the 10-body combined.stl.**

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
| **5** | **M7 sHM real run** · observe what new walls appear at the mesh-generation stage when the 10-body combined STL hits sHM (F-NEW-13 prediction: boundary-shells watertight ≠ flowable; F-NEW-15/16: airframe-as-2-components → 2 regions?) | observation / new finding stream | session of work, no code change | **NEXT** |
| **6** | **F-NEW-15 substrate dig** · was Codex's `build_cad.py` for case_003 v1 intentionally emitting a 2-component airframe? ≤5 min grep at `~/Desktop/case_003_crm_hls_boundary_layer/` | substrate / data | ≤5 min | open |
| 7 | **F-NEW-17** · Body-class filter cross-talks with F-NEW-4 (Codex 3× scaling); ship/large geometries may need configurable industrial range | enhancement / not blocking | n/a | revisit when ≥1 case has all-bodies-above-100 m |
| 8 | **F-NEW-13 truth-chain copy** · "watertight" passes on boundary-only payload; UX/copy issue at M-CONTROL-RAIL | UX / docs | deferred | deferred to M-CONTROL-RAIL UI work |
| 9 | **V-series authoring** · V25/V26/V28/V29/V30/V31 still queued for `industrial_case_solver_findings.md` | docs | n/a | low priority, batch when next touching V-series |

Recommended next-session order: **5 first (M7 sHM observation, the big
unknown), 6 if time permits (cheap, related to 5)**. 7-9 are not
blockers.

## V-series queue (6 not-yet-committed rows)

V25 + V26 + V28 + V29 + V30 + **V31** (session 4 wiring landed —
route now calls `detect_unit` with body-class filter). V27 already
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

Walk a fresh case_003 case through M7 sHM and observe what breaks.
**Not a code change**; an observation session. Expected to surface
F-NEW-19..N findings around sHM behavior on the 10-body / 2-component
airframe / 91m + 1.5km domain payload.
