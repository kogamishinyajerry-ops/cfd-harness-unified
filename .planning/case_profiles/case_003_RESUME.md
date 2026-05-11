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

| # | Finding | Class | Estimate | Promotion |
|---|---|---|---|---|
| **1** | **F-NEW-9** · 50 MB STL cap blocks 87 MB airframe at Q3 deflection | sub-DEC (changes route) | ~3 LOC + 1 test | unblocks every industrial STEP case |
| **2** | **F-NEW-10** · Bridge lacks "combined multi-solid ASCII emit" mode | spike-class | ~30 LOC + 1 test | makes one-shot workbench upload trivial |
| **3** | **F-NEW-12 / 4b** · P0 unit_detector / workbench unit_guess conflates airframe-class bodies with CFD-domain bodies | spike-class | ~40 LOC + 1 test on `unit_detector.py` | fixes UNKNOWN unit_guess UX |
| **4** | **F-NEW-13** · `is_watertight=True` on boundary-only payload is misleading as CFD-readiness | UX / Truth Chain copy | deferred to M-CONTROL-RAIL UI work | no code action this session |

Recommended order: 1 → 2 → 3 in three small commits (≈90 min total). 1
needs sub-DEC frontmatter (changes route gate); 2 + 3 are spike-class.

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
