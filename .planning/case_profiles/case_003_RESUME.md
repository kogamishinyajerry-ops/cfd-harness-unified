# case_003 · RESUME

**Last session**: 2026-05-11 (session 1)
**Status**: preprocessing probe complete; not yet meshed; not yet solved.

## Where to pick up

1. Open `.planning/case_profiles/case_003_ramp_log_2026-05-11.md` — full session 1 findings + predicted blockers.
2. Probe evidence: `ui/backend/user_drafts/imported/case_003_crm_hls/probe_session_1.json` (gitignored, regenerable via `scripts/case_003/ramp_session_1.py`).
3. Source STEP: `ui/backend/user_drafts/imported/case_003_crm_hls/raw/cad.step` (gitignored; copy from `~/Desktop/case_003_crm_hls_boundary_layer/inputs/cad_codex_v1.step` if missing).

## Decision points still open

- Reclassify V-series V20 from "unit chain bug" to "intentional 3× scale" (see ramp log F-NEW-4).
- Choose Phase 4 next move:
  - **4a** STEP→STL bridge (`freecad_step_to_stl` helper) — unblocks workbench import path
  - **4b** P0 body-class filter — fixes false UNKNOWN on multi-class STEP
  - **4c** wait until 4a runs, see what new blocker surfaces

## Next immediate action

Run: `.venv/bin/python scripts/case_003/ramp_session_1.py` to confirm environment still works, then start Phase 4a or 4b per user preference.

## Open V-series rows (not yet committed)

V20 amendment + V25 + V26 + V27. See ramp log §"V-series rows to update / add".
