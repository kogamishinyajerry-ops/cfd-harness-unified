# case_003 · RESUME

**Last session**: 2026-05-11 (session 3 — workbench import probe)
**Status**: Phase 4a STEP→STL bridge shipped (session 2); workbench
import endpoint exercised against the 10 STLs (session 3); not yet
meshed; not yet solved.

## Where to pick up

1. `.planning/case_profiles/case_003_ramp_log_2026-05-11.md` for the
   full F-NEW-1..14 list and V-series queue (V25..V30).
2. Session 3 driver: `scripts/case_003/ramp_session_3_workbench.py`.
   Re-run with `.venv/bin/python scripts/case_003/ramp_session_3_workbench.py`
   if you need fresh probe output.
3. STL evidence: `ui/backend/user_drafts/imported/case_003_crm_hls/stl_session_2/` (gitignored, regenerable in ~7 s).

## Outstanding blockers — prioritized by substrate evidence

| # | Finding | Class | Estimate | Status |
|---|---|---|---|---|
| ~~1~~ | ~~F-NEW-9 · 50 MB cap~~ | ~~spike~~ | ~~3 LOC~~ | **DONE** · cap raised to 200 MB; 87 MB airframe rides route 200 OK |
| ~~2~~ | ~~F-NEW-10 · combined multi-solid ASCII emit~~ | ~~spike~~ | ~~21 LOC + 25 LOC test~~ | **DONE** · `combine_per_body_stls`; 10 patches round-trip through workbench |
| ~~3~~ | ~~F-NEW-12 · body-class filter for unit_guess~~ | ~~spike~~ | ~~25 LOC + 3 tests~~ | **DONE** · `detect_unit(body_extents_raw=...)`; UNKNOWN→MM confidence 1.0 on real case_003 |
| **4** | **F-NEW-13** · `is_watertight=True` on boundary-only payload is misleading | UX / truth-chain copy | deferred to M-CONTROL-RAIL UI work | deferred |
| **5** | **F-NEW-15 + F-NEW-16** · Codex-built airframe is 2 disconnected bodies | substrate / data | read `build_cad.py` first | substrate-data, not workbench-code |
| **6** | **F-NEW-17** (NEW from spike #3) · Body-class filter cross-talks with F-NEW-4 (Codex 3× scaling); ship/large geometries may need configurable industrial range | enhancement / not blocking | n/a | revisit when ≥1 case has all-bodies-above-100 m |
| **7** | **Wiring** · the new `body_extents_raw` path isn't wired into the workbench route yet (route still passes only overall bbox) | wiring / new spike | ~20 LOC | next session candidate |

Recommended order: 2 → 3 in two spike commits. F-NEW-15 needs CAD-generator
reading first; potentially out of substrate-listening scope (project-data
issue, not workbench issue).

## V-series queue (5 not-yet-committed rows)

V25 + V26 + V27(LANDED) + V28 + V29 + V30. See ramp_log §"V-series queue"
for one-liners. Author into `industrial_case_solver_findings.md` next
time you touch V-series (low priority).

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

## Next immediate action

Land #1 (route cap raise) as sub-DEC — smallest unblock with widest
substrate value. Then #2 + #3 as back-to-back spikes. After that,
manually walk a fresh case_003 case through M7 sHM (probe F-NEW-13
empirically: does sHM actually produce a sane mesh on the combined
9-body STL when airframe is uploaded separately?).
