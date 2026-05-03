---
decision_id: DEC-V61-112-Phase3
title: Solver-profile YAML migration · Phase 3 — icoFoam LDC profile (V61-097 setup_ldc_bc inline template extraction)
status: Proposed (2026-05-03 · authored under user 2026-05-03 autonomous-mode mandate "全权授予你开发，全都按你的建议继续，执行开发"; user explicit follow-up "start V61-112 Phase 3 (LDC icoFoam migration)")
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-03
authored_under: V61-112 Phase 2 acceptance closure (commit 528bc6b · counter 68→69) explicitly identifies Phase 3 (LDC icoFoam migration) as the immediate follow-up
parent_decisions:
  - DEC-V61-112 (Phase 1 · simpleFoam profile + schema + registry · Accepted commit d0402e8)
  - DEC-V61-112-Phase2 (pimpleFoam profile + per-solver name_pad schema extension · Accepted commit 528bc6b · this DEC reuses the Phase 2-extended schema)
  - DEC-V61-097 (LDC setup_ldc_bc Phase-1A · supplied the icoFoam template authored INLINE in `bc_setup.py:452-503` — extraction target for this Phase)
  - RETRO-V61-001 (risk-tier · multi-file backend (case_solve service surface) + new config schema profile = mandatory Codex pre-merge)
parent_artifacts:
  - reports/codex_tool_reports/v61_112_phase2_r1_r2_r3_chain.md (Phase 2 3-round APPROVE chain · 2 NEW methodology lessons applicable to Phase 3: caller-input-type-aware golden snapshots + dataclass-default-literal-type discipline)
  - ui/backend/services/case_solve/bc_setup.py:452-503 (V61-097 inline icoFoam controlDict + fvSchemes + fvSolution — extraction targets for this Phase)
  - ui/backend/services/case_solve/solver_profiles/schema.py (Phase 1+2 schema · reused unchanged for Phase 3; icoFoam fits within existing dataclass without further schema extensions)
counter_impact: +1 (autonomous_governance: true · architectural foundation continuation, no external gate required)
self_estimated_pass_rate: 60% (calibrated UP from Phase 1+2's 50%/50% baseline because Phase 3 introduces NO new schema extensions — reuses Phase 1+2 schema as-is. icoFoam template is structurally simpler than pimpleFoam: fewer solver entries (no UFinal), simpler controlDict (no adjustTimeStep / maxCo / maxDeltaT_follows), simpler fvSchemes (no divDevReff term, orthogonal laplacian/snGrad). Risk surface narrows to: (a) PISO control_block_name (new value alongside SIMPLE/PIMPLE), (b) `endTime 2;` int literal preservation, (c) wrapper rewire pattern slightly different — `_author_dicts` is the single call site, not 3 wrapper helpers like Phase 2)
notion_sync_status: pending (Notion MCP offline this session; sync queued for next online window)

# DEC-V61-112 Phase 3 · icoFoam LDC profile

## Why now

V61-112 Phase 2 closed 2026-05-03 with the pimpleFoam profile (transient PIMPLE) extracted. Phase 2 acceptance closure explicitly identifies Phase 3 (LDC icoFoam) as the next migration step. User explicit direction "start V61-112 Phase 3 (LDC icoFoam migration)" authorizes immediate execution.

V61-097 landed the LDC `setup_ldc_bc` Phase-1A pipeline with icoFoam inline templates at `bc_setup.py:452-503`. icoFoam is OpenFOAM-10's LDC default solver; the LDC pipeline is the M-PANELS Phase-C demo's hot path used by every cube/cavity dogfood case (smoke + e2e + adversarial).

## Decision

Author `ui/backend/services/case_solve/solver_profiles/profiles/icoFoam.yaml` extracting the V61-097 inline LDC templates. Rewire `_author_dicts` (in `bc_setup.py`) inline `w("system/controlDict", ...)` / `w("system/fvSchemes", ...)` / `w("system/fvSolution", ...)` calls to load the profile and pass the rendered output. Mirror the Phase 1+2 wrapper-delegation pattern with the difference that this Phase has no `_build_icofoam_*` helpers — the migration site is the inline `w(...)` call directly.

### Schema reuse (no extensions needed)

Phase 3 fits within the Phase 1+2 schema:
- `application: icoFoam`
- `control_block_name: PISO` — new value alongside SIMPLE (Phase 1) / PIMPLE (Phase 2). The control_block_name field accepts any string (validated via Phase 1 R2 P2 closure's isinstance-str check).
- `solvers`: 3 entries (p, pFinal, U) — no UFinal. `pFinal` uses 1-space pad per Phase 2's `name_pad` extension; `p` and `U` use 2-space default.
- `control_block_fields`: nCorrectors, nNonOrthogonalCorrectors, pRefCell, pRefValue (PISO-specific subset).
- No `relaxationFactors`.
- No `residualControl`.
- controlDict: `adjust_time_step: null` (omit), `max_co: null` (omit), no maxDeltaT path. icoFoam ignores all transient-stability keys.
- Caller signature: `_author_dicts` does NOT pass end_time/delta_t — the inline templates use literals (endTime=2, deltaT=0.005, writeInterval=0.5). Profile's `end_time_default: 2` (YAML int) + `delta_t_default: 0.005` (YAML float) + `write_interval: 0.5` (YAML float) covers byte-identity via Phase 2 R1 P2 fix (YAML int-vs-float type distinction round-trips).

## Acceptance criteria

§1 Phase 3 icoFoam.yaml byte-identical to V61-097 inline output for the LDC default case parameters (no caller args; literals from inline). Verified via golden-snapshot constants embedded in `test_solver_profiles.py`.

§2 Phase 1 + Phase 2 profiles + golden tests UNCHANGED — Phase 3 reuses the Phase 2-extended schema. All Phase 1 + Phase 2 tests (50 tests as of Phase 2 closure) continue to pass.

§3 `_author_dicts` rewire: replace the 3 inline `w("system/controlDict", ...)` / `w("system/fvSchemes", ...)` / `w("system/fvSolution", ...)` calls with `load_profile("icoFoam").render_*()` results. NO new helper functions introduced (different from Phase 1+2 which had `_build_simplefoam_*` / `_build_pimplefoam_*` wrappers).

§4 Codex pre-merge APPROVE / APPROVE_WITH_COMMENTS per RETRO-V61-001 risk-tier (multi-file backend route + new config schema profile).

§5 Surface scan applied per V61-088: `bc_setup.py:452-503 (V61-097 inline LDC icoFoam) + bc_setup.py:822-906 (channel pimpleFoam — Phase 4 follow-up)` · disposition `refactor existing (Phase 3 extracts LDC icoFoam only; channel deferred to Phase 4)`.

§6 Phase 2 methodology lessons applied directly:
- Caller-input-type-aware golden snapshots: although `_author_dicts` doesn't take end_time/delta_t args, the rendered output is fixed; tests verify byte-identity for the no-args render path.
- Dataclass default literal type: Phase 2 R2 P3 closure already tightened controlDict defaults to int; Phase 3 inherits.

## Out of scope

- Channel pimpleFoam migration (Phase 4 follow-up DEC) — `bc_setup.py:822-906` `setup_channel_bc` template; intentionally deferred to keep this Phase's diff bounded
- Live LDC dogfood verification — Docker container required; behavioral parity verified by existing 1131+ backend tests covering setup_ldc_bc + LDC dogfood smoke
- 0/U + 0/p + constant/physicalProperties + constant/momentumTransport templates (lines 411-450 in bc_setup.py) — these are case-physics fields (initial+boundary+material), NOT solver templates. Out of solver-profile scope; remain inline in `_author_dicts`.

## Process note

V61-112 Phase 3 explicitly applies the V61-088 pre-implementation surface scan rule:

`Surface-scan-found: ui/backend/services/case_solve/bc_setup.py:452-503 (V61-097 inline LDC icoFoam controlDict + fvSchemes + fvSolution) + ui/backend/services/case_solve/bc_setup.py:822-906 (channel pimpleFoam — Phase 4 follow-up) · disposition: refactor existing (Phase 3 extracts LDC icoFoam only; channel deferred to Phase 4; Phase 1+2 schema reused without extensions)`

V61-112 Phase 3 applies the 2 Phase 2 methodology lessons (chain report § Methodology lessons captured for next RETRO):
- Lesson 1: golden snapshots exercise real input scenarios — `_author_dicts` no-args render path
- Lesson 2: dataclass defaults tightened to int by Phase 2 R2 P3 closure — Phase 3 inherits the contract
