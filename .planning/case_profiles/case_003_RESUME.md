# case_003 · RESUME

**Last session**: 2026-05-11 (session 2)
**Status**: 10× per-body ASCII STL produced via `freecad_step_to_stl` bridge;
not yet routed through workbench `import_geometry` endpoint; not yet meshed;
not yet solved.

## Where to pick up

1. Open `.planning/case_profiles/case_003_ramp_log_2026-05-11.md` for
   session 1 + 2 findings (F-NEW-1..8, V-series queue).
2. STL evidence: `ui/backend/user_drafts/imported/case_003_crm_hls/stl_session_2/` (gitignored, regenerable in ~7 s via the snippet below).
3. Source STEP: `ui/backend/user_drafts/imported/case_003_crm_hls/raw/cad.step` (gitignored).

## Reproduce session 2 output

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

## Decision points still open

- V-series rows V20 amend / V25 / V26 / V27 still queued (session 1
  ramp_log §"V-series rows to update / add"), not yet committed to
  `industrial_case_solver_findings.md`.
- Phase 4 next move (now that 4a is shipped):
  - **4b** P0 body-class filter (F-NEW-3) — fix false UNKNOWN on multi-class STEP
  - **5** route layer integration — POST STLs to `/api/import-geometry` + observe manifest write
  - **6** sHM ramp + cell budget validation on 91 m airframe + 1.5 km farfield
  - **wait** — let next case (or workbench shake-down) drive choice (substrate-first)

## Next immediate action

Per substrate-first: ride the new STLs through the workbench import
endpoint manually, see what new blocker surfaces, then choose 4b vs 5
vs 6 based on what breaks.
