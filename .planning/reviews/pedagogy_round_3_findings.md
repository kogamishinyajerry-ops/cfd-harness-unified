# DEC-V61-047 Round 3 — Codex Consolidated Verdict

**Overall**: APPROVE_WITH_COMMENTS
**Blockers**: 0
**Expert verdict**: APPROVE_WITH_COMMENTS — the round-2 blocker is closed. `naca0012_airfoil` now teaches the canonical repo-truth regime (`simpleFoam` + `kOmegaSST`, `Re=3e6`, `α=0°`, `p=0.3`, `U/k/ω=0.5`, near-surface Cp attenuation => `20%` tolerance + `PASS_WITH_DEVIATIONS`), and the re-review window contains no other case edits. Frontend verification stayed green (`ui/frontend`: `npm run typecheck`, `npm run build`).
**Novice verdict**: APPROVE_WITH_COMMENTS — a novice will no longer leave with the wrong NACA 0012 benchmark setup. The core story is now honest: symmetric airfoil, zero incidence, attached flow, and a Cp curve whose amplitude is muted because the adapter samples a near-surface cell band rather than the exact wall surface.

## N1 verification
- status: CLOSED
- evidence: `ui/frontend/src/data/learnCases.ts:203-213` now teaches `α=0°` attached symmetric flow, `Re=3e6`, `simpleFoam + kOmegaSST`, `p=0.3`, `U/k/ω=0.5`, thin-span x-z mesh with empty side patches, and near-surface-band Cp attenuation with `20%` / `PASS_WITH_DEVIATIONS`. That matches `knowledge/whitelist.yaml:242-246`, `knowledge/gold_standards/naca0012_airfoil.yaml:5-28`, `src/foam_agent_adapter.py:5917-5950`, `src/foam_agent_adapter.py:6080-6143`, `src/foam_agent_adapter.py:6337-6363`, `src/foam_agent_adapter.py:6370-6526`, `src/foam_agent_adapter.py:8612-8661`, and `ui/backend/tests/fixtures/runs/naca0012_airfoil/reference_pass_measurement.yaml:1-19`.
- evidence: the re-review scope is surgical. `git diff --name-only 51c7198..196fb94` returns only `ui/frontend/src/data/learnCases.ts`, and `git diff --unified=0 51c7198..196fb94 -- ui/frontend/src/data/learnCases.ts | rg 'lid_driven_cavity|backward_facing_step|circular_cylinder_wake|turbulent_flat_plate|plane_channel_flow|impinging_jet|rayleigh_benard_convection|differential_heated_cavity|duct_flow'` returns no matches, so the other 9 cases are untouched.

## Carry-forward
- F3 deferral: still accept. Round 3 changes only `ui/frontend/src/data/learnCases.ts`; nothing in the Tier-C backend/reporting path changed, so the round-2 backlog judgment stands.
- F1 / F2 / F4 / F5 / F6: stay closed. This window edits one `naca0012_airfoil` block only, and the frontend still verifies cleanly after the change.

## New findings (if any)
- None blocking in `51c7198..196fb94`.

## If APPROVE / APPROVE_WITH_COMMENTS
End iteration.
- Optional backlog only: if you want the Story tab to become literal patch-by-patch adapter documentation rather than pedagogy-first shorthand, tighten `ui/frontend/src/data/learnCases.ts:211-212` to the current adapter's exact far-field extents and `freestreamVelocity` / `freestreamPressure` wording. That is not a reason to reopen DEC-V61-047.
