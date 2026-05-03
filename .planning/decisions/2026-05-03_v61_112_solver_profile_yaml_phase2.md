---
decision_id: DEC-V61-112-Phase2
title: Solver-profile YAML migration · Phase 2 — pimpleFoam profile (V61-107.5 transient template extraction)
status: Proposed (2026-05-03 · authored under user 2026-05-03 autonomous-mode mandate "全权授予你开发，全都按你的建议继续，执行开发"; user explicit follow-up "start V61-112 Phase 2 (pimpleFoam profile extraction) now")
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-03
authored_under: V61-112 Phase 1 acceptance closure (commit d0402e8) explicitly identifies Phase 2 (pimpleFoam profile) as the immediate follow-up; user direct authorization to proceed
parent_decisions:
  - DEC-V61-112 (Phase 1 · simpleFoam profile + schema + registry · Accepted 2026-05-03 commit d0402e8 · this DEC reuses the Phase 1 schema + registry, adding pimpleFoam-shaped extensions)
  - DEC-V61-107.5 (pimpleFoam transient template · 9-round Codex chain to APPROVE on commit c924360 · template authored INLINE in bc_setup_from_stl_patches.py:755-845 — extraction target for this Phase)
  - RETRO-V61-001 (risk-tier · multi-file backend (case_solve service surface) + new config schema profile = mandatory Codex pre-merge)
parent_artifacts:
  - reports/codex_tool_reports/v61_112_phase1_r1_r2_r3_chain.md (Phase 1 3-round APPROVE chain · methodology lesson "byte-identity gates need golden constants, not rewired-old-func equality")
  - ui/backend/services/case_solve/bc_setup_from_stl_patches.py:755-845 (V61-107.5 inline pimpleFoam template helpers — extraction target for this Phase)
  - ui/backend/services/case_solve/solver_profiles/schema.py (Phase 1 schema · extended in this Phase to support per-solver `name_pad` for byte-identity preservation)
counter_impact: +1 (autonomous_governance: true · architectural foundation continuation, no external gate required)
self_estimated_pass_rate: 50% (calibrated DOWN from Phase 1's 60% per Phase 1 closure recommendation: "for next retro: config-schema-migration anchor should drop to ~50%". Schema extension introduces a new dispatch path (per-solver name_pad — string vs dict-shaped solver entries); Phase 1 lessons on golden snapshots + nested validation applied; expect Codex 2-3 rounds with possible P2 findings on the new SolverEntry shape validation)
notion_sync_status: pending (Notion MCP offline this session; sync queued for next online window)

# DEC-V61-112 Phase 2 · pimpleFoam profile + schema extension

## Why now

V61-112 Phase 1 closed 2026-05-03 with the simpleFoam profile (steady-state SIMPLE) extracted into YAML. Phase 1 acceptance closure explicitly identifies Phase 2 (pimpleFoam · transient PIMPLE) as the next migration step. User explicit direction "start V61-112 Phase 2 (pimpleFoam profile extraction) now" authorizes immediate execution.

V61-107.5 landed pimpleFoam as the named-patch path's default solver (replacing icoFoam due to OpenFOAM-10 setDeltaT.H + adjustTimeStep contract — see V61-107.5 R12-R20 chain). The pimpleFoam template helpers `_build_pimplefoam_control_dict` / `_build_pimplefoam_fv_schemes` / `_build_pimplefoam_fv_solution` live INLINE at `bc_setup_from_stl_patches.py:755-845`. Three sites + simpleFoam (already extracted) + 2 deferred (LDC icoFoam Phase 3 + channel pimpleFoam Phase 4) means the V61-102 §Phase 3 deferral (4 inline-template extraction sites) is half-closed after this Phase.

## Decision

Author `ui/backend/services/case_solve/solver_profiles/profiles/pimpleFoam.yaml` extracting the V61-107.5 inline templates. Rewire `_build_pimplefoam_*` wrappers to delegate to `load_profile("pimpleFoam").render_*()`, mirroring the Phase 1 simpleFoam wrapper pattern. Add `test_solver_profiles.py` golden-snapshot regression tests for pimpleFoam — applying the Phase 1 R1 P2-2 methodology lesson (literal pre-rewire bytes embedded as immovable constants, NOT tautological wrapper-equality).

### Schema extension required: per-solver `name_pad`

V61-107.5 inline pimpleFoam fvSolution uses inconsistent solver-line whitespace:
```
    p  { solver PCG; ...; }       # 2-space pad after name
    pFinal { $p; relTol 0; }       # 1-space pad after name
    U  { solver smoothSolver; ...; }
    UFinal { $U; relTol 0; }
```

The Phase 1 schema renders all solver entries with hardcoded 2-space pad (`f"    {field_name}  {{ {body} }}"`). Byte-identity to V61-107.5 inline requires per-solver pad control.

**Option chosen**: extend `solvers` value type from `str` (Phase 1) to `str | dict[str, Any]`:
- `str` value → treated as `{body: <str>, name_pad: 2}` (Phase 1 backward-compat)
- `dict` value → must contain `body: str`, optionally `name_pad: int` (default 2)

Migration impact:
- Phase 1 `simpleFoam.yaml` unchanged (string-typed values continue to work, normalized at load time)
- Phase 1 schema-validation test `test_fv_solution_solvers_value_dict_raises_schema_error` continues to pass — its bad-shape `{p: {solver: "GAMG"}}` still rejected (no `body` field)
- Phase 1 byte-identity tests continue to pass — string normalization yields `name_pad=2` matching Phase 1 hardcoded behavior

Alternatives considered (rejected):
1. **Normalize V61-107.5 to consistent 2-space pad** — would change pimpleFoam fvSolution bytes. Existing iter02/iter04/iter05/iter06 E2E smoke tests would still pass (OpenFOAM tolerates whitespace), but the V61-107.5 explicit acceptance contract says "byte-identical to current inline". Rejected to preserve V61-107.5 acceptance.
2. **List-of-lines `solvers: [str, str, ...]` schema** — most flexible but invalidates Phase 1 simpleFoam.yaml format. Migration cost > benefit.
3. **Top-level `solver_name_pad: int = 2`** — uniform per-profile pad. Doesn't handle pimpleFoam's mixed pad. Rejected.

## Acceptance criteria

§1 Schema extension supports per-solver `name_pad` via str|dict value type, default 2, backward-compat for Phase 1 `simpleFoam.yaml` string-only values. Schema-validation rejects malformed dict shapes (missing `body`, non-int `name_pad`, extra unknown keys, etc.).

§2 Phase 2 pimpleFoam.yaml byte-identical to V61-107.5 inline output for the iter01-style canonical case parameters (end_time=5, delta_t=0.001 — representative iter02 smoke). Verified via golden-snapshot constants embedded in `test_solver_profiles.py`.

§3 Phase 1 simpleFoam.yaml + golden tests UNCHANGED — Phase 2 schema extension MUST be backward-compat. All Phase 1 tests (21 tests) continue to pass.

§4 `_build_pimplefoam_*` wrappers rewired to delegate to `load_profile("pimpleFoam").render_*()`, preserving V61-107.5 call signature for backward compat (callers + tests).

§5 Codex pre-merge APPROVE / APPROVE_WITH_COMMENTS per RETRO-V61-001 risk-tier (multi-file backend route + new config schema entry; ≤70% self-pass-rate gate also triggers pre-merge).

§6 Surface scan applied per V61-088: `bc_setup_from_stl_patches.py:755-845 (V61-107.5 inline pimpleFoam) + bc_setup.py:822-906 (channel pimpleFoam — DEFERRED to Phase 4)` · disposition `refactor existing (Phase 2 extracts STL-path pimpleFoam only; channel path deferred to Phase 4)`.

## Out of scope

- LDC icoFoam migration (Phase 3 follow-up DEC) — `bc_setup.py:450-503` `setup_ldc_bc` icoFoam template
- Channel pimpleFoam migration (Phase 4 follow-up DEC) — `bc_setup.py:822-906` `setup_channel_bc` pimpleFoam template; intentionally deferred so this Phase's diff stays bounded (`bc_setup_from_stl_patches.py` only)
- Live iter02/iter04/iter05/iter06 dogfood verification — Docker container required; behavioral parity verified by existing 198+ backend tests covering the named-patch path
- Solver-runner adoption of profiles for application-name parsing — `solver_runner.read_application_from_control_dict` parser remains the single source of truth per V61-111 R2 P2-1 closure

## Process note

V61-112 Phase 2 explicitly applies the V61-088 pre-implementation surface scan rule:

`Surface-scan-found: ui/backend/services/case_solve/bc_setup_from_stl_patches.py:755-845 (V61-107.5 inline pimpleFoam template helpers) + ui/backend/services/case_solve/bc_setup.py:822-906 (channel pimpleFoam — Phase 4 follow-up) + ui/backend/services/case_solve/solver_profiles/schema.py:184-185 (Phase 1 solvers field hardcoded 2-space pad — extending) · disposition: refactor existing (Phase 2 extracts STL-path pimpleFoam only; channel deferred to Phase 4; schema extended backward-compat)`

V61-112 Phase 2 applies Phase 1 R1 P2-2 methodology lesson directly: golden snapshots are captured BEFORE the wrapper rewire and embedded as literal constants in test_solver_profiles.py, ensuring the byte-identity gate detects future drift.
