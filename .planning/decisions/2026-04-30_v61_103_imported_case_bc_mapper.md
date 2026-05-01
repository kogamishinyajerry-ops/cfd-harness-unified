---
decision_id: DEC-V61-103
title: Imported-case BC mapper — `/setup-bc?from_stl_patches=1` mode driven by named polyMesh patches
status: Proposed (2026-04-30 · authored under user direction "全权授予你开发，全都按你的建议来" after adversarial-loop iter01-03 surfaced defect 3 as the only remaining workflow blocker for arbitrary-CAD support)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-04-30
authored_under: tools/adversarial/results/iter02_findings.md (defect 3 root cause + scope) + iter03_findings.md (workaround validated end-to-end with author_dicts.py)
parent_decisions:
  - DEC-V61-097 (Phase-1A LDC dogfood · setup_ldc_bc — the LDC-only path this DEC generalizes)
  - DEC-V61-101 (Minimal channel executor · setup_channel_bc — same pattern, second hardcoded family)
  - DEC-V61-102 (M-RESCUE Manual Override Foundation · raw-dict editor is today's defect-3 workaround, this DEC promotes the workaround to a first-class workflow)
  - RETRO-V61-001 (risk-tier triggers · multi-file backend route + new public route surface = mandatory Codex review)
parent_artifacts:
  - tools/adversarial/results/iter02_findings.md (defect 3 diagnosis · `case_solve.py:206` hardcodes setup_ldc_bc)
  - tools/adversarial/results/iter03_findings.md (workaround validation · iter03 `author_dicts.py` proves the dict shape works end-to-end → icoFoam converged)
  - ui/backend/routes/case_solve.py:123-218 (current /setup-bc handler — LDC-only legacy path)
  - ui/backend/services/case_solve/bc_setup.py:382-505 (`_author_dicts` template — dict shape this DEC reuses with patch-name parameterization)
counter_impact: +1 (autonomous_governance: true · architectural extension DEC, builds on V61-102's manifest invariant)
self_estimated_pass_rate: 65% (new public route + cross-cutting BC-author refactor + frontend Step 3 mode toggle + defaults-table extensibility hooks · structurally similar to V61-102 Phase 1 scope but adds frontend touchpoint)
codex_tool_report_path: (TBD — will land alongside Phase-1 Codex review of this DEC)
notion_sync_status: synced 2026-04-30 (https://app.notion.com/p/353c68942bed81179b4ddf765f6d5a53)

# Why now

Adversarial-loop iter01-03 (2026-04-30) verified that the system's mesh + solver layers are fully CAD-agnostic when fed properly-named-patch dicts. The only remaining LDC coupling is in `routes/case_solve.py:206`:

```python
result = setup_ldc_bc(case_dir, case_id=case_id)
```

Every imported case — regardless of named polyMesh patches — gets fed through `setup_ldc_bc` which splits the boundary into `lid` + `fixedWalls` and writes icoFoam Re=100 dicts. The named patches that defect-2a-fix preserves through gmsh (inlet, outlet, walls, etc.) are silently ignored.

The DEC-V61-102 raw-dict editor IS the workaround today. iter03 proved it works (a 100-LOC author script bypasses /setup-bc, drops 7 dicts to disk, /solve runs cleanly, icoFoam converges). But that's an "engineer rescue" path, not a workflow.

Without DEC-V61-103, "arbitrary CAD support" stays a marketing claim — every imported case forces the engineer through manual dict-authoring. With it, the canonical CAD-export form (named patches) drives the workbench end-to-end.

# Scope

## Phase 1 · Backend new route + service (1 week)

### 1.1 New service: `bc_setup_from_stl_patches`

`ui/backend/services/case_solve/bc_setup_from_stl_patches.py` (NEW)

Reads `constant/polyMesh/boundary` to discover named patches. For each patch, looks up a default BC class from a project-level table:

```python
DEFAULT_PATCH_CLASS = {
    "inlet": BCClass.VELOCITY_INLET,
    "outlet": BCClass.PRESSURE_OUTLET,
    "walls": BCClass.NO_SLIP_WALL,
    "wall": BCClass.NO_SLIP_WALL,
    "symmetry": BCClass.SYMMETRY,
    "top": BCClass.NO_SLIP_WALL,        # heuristic: ambiguous
    "bottom": BCClass.NO_SLIP_WALL,
    "front": BCClass.NO_SLIP_WALL,
    "back": BCClass.NO_SLIP_WALL,
    # Default fallback (any unrecognized name): NO_SLIP_WALL with warning
}
```

Each `BCClass` carries a `(0/U_template, 0/p_template)` pair. The service:

1. Reads `polyMesh/boundary` patch list (re-uses `services/case_dicts/boundary_parser.py` if it exists, else inlines a minimal parser).
2. For each patch, picks a `BCClass` from `DEFAULT_PATCH_CLASS` (case-insensitive lookup with fallback).
3. Authors `0/U`, `0/p` from concatenated templates with default scalar values (`U_inlet=0.5 m/s`, `p_outlet=0`, `nu=1e-3` — same defaults as V61-102 raw-dict).
4. Authors `constant/physicalProperties`, `constant/momentumTransport`, `system/{controlDict,fvSchemes,fvSolution}` using V61-102's `_author_dicts` template, parameterized with solver choice (default `icoFoam`, `endTime=5s`, `deltaT=0.01s`).
5. Wraps the multi-file write in V61-102's `_atomic_commit_dicts` so the user-override invariant + 2-phase commit semantics apply (engineer-edited dicts via raw-dict editor are NOT clobbered).
6. Returns `BCSetupResult` shape compatible with `setup_ldc_bc` (n_inlet_faces, n_outlet_faces, n_wall_faces, defaults_used, written_files).

### 1.2 Route surface extension

`ui/backend/routes/case_solve.py`

Add a new query param to `POST /import/{case_id}/setup-bc`:

```python
@router.post("/import/{case_id}/setup-bc")
def setup_bc(
    case_id: str,
    envelope: int = Query(0, ge=0, le=1),
    force_uncertain: int = Query(0, ge=0, le=1),
    force_blocked: int = Query(0, ge=0, le=1),
    from_stl_patches: int = Query(0, ge=0, le=1, description="Drive BC from named polyMesh patches"),
):
    if from_stl_patches:
        return setup_bc_from_stl_patches(case_dir, case_id=case_id)
    if envelope:
        ...
    return setup_ldc_bc(case_dir, case_id=case_id)
```

When the imported case has named patches, the frontend SHOULD pass `from_stl_patches=1`. When it has only `defaultFaces` (legacy single-solid STL), it falls through to `envelope=1` or LDC.

### 1.3 Failure modes & error contract

- Patch name not in DEFAULT_PATCH_CLASS → emit warning in result, fall through to NO_SLIP_WALL default (not an error). Engineer can override via raw-dict editor (V61-102 path).
- `polyMesh/boundary` missing → return 409 `failing_check=mesh_not_setup`.
- Atomic commit fails → return 409 (V61-102 `_atomic_commit_dicts` semantics).

## Phase 2 · Frontend Step 3 mode toggle (3 days)

`ui/frontend/src/pages/workbench/step_panel_shell/steps/Step3SetupBC.tsx`

When the case is `source_origin: imported_user` AND `polyMesh/boundary` patch list contains named patches (not just `defaultFaces`), the Step 3 panel:

1. Detects named-patch mode via a new `GET /import/{case_id}/bc-strategy` (returns `{strategy: "from_stl_patches" | "ldc" | "envelope_annotations"}`).
2. Renders the patch list with default BC class per patch.
3. Engineer can confirm defaults + click `[AI 处理]` → `POST /setup-bc?from_stl_patches=1`.
4. After setup, the DEC-V61-102 raw-dict editor remains available for fine-tuning.

For non-named-patch cases (defaultFaces or LDC), Step 3 falls back to existing behavior (envelope=1 / LDC defaults).

## Phase 3 · Tests + adversarial loop continuation (3 days)

- 8 backend unit tests covering `bc_setup_from_stl_patches`:
  - 3-patch duct (inlet/outlet/walls) → expected dicts produced
  - 4-patch case (inlet/outlet/walls/symmetry) → symmetry handled
  - Unknown patch name → falls through to NO_SLIP_WALL with warning
  - Patch name case-insensitivity (`Inlet` matches `inlet`)
  - `polyMesh/boundary` missing → 409
  - Atomic commit failure → rollback verified
  - Idempotent (calling twice yields same result)
  - User-override invariant: dicts edited via raw-dict editor are NOT clobbered
- 4 frontend unit tests covering Step 3 mode detection + dispatch.
- Adversarial loop iter04+: Codex generates new geometry classes (L-bend, T-junction, high-aspect-ratio thin channel), drives through full pipeline using new mode → finds next-tier defects.

# Out of scope (deferred)

- Multi-solver support (simpleFoam, pimpleFoam, buoyantFoam) — covered separately by M12 (workbench_long_horizon_roadmap_2026-04-29.md).
- Turbulence model selection — same.
- BC class extensibility (custom BC types via plugin/hook) — needs DEC of its own, not blocking iter04+.
- Defect 2b (interior obstacle topology in mesher) — covered by DEC-V61-104.

# Success criteria

1. `POST /setup-bc?from_stl_patches=1` returns 200 + 7-dict success on iter02 duct case.
2. `POST /solve` after the above returns `converged=true` (matches iter03 manual-author result).
3. End-to-end pipeline test: import multi-solid STL → mesh → setup-bc?from_stl_patches=1 → solve → converged.
4. All 11 geometry_ingest + 101 mesh+gmsh+import tests still pass.
5. Codex review APPROVE or APPROVE_WITH_COMMENTS, all comments closed.
6. iter04 case (Codex-generated L-bend) drives end-to-end without manual dict authoring.

# Effort estimate

- Phase 1 (backend): 1 week (200 LOC service + route extension + 8 tests)
- Phase 2 (frontend): 3 days (Step 3 mode toggle + bc-strategy probe + 4 tests)
- Phase 3 (validation): 3 days (adversarial iter04+, document findings)

Total ≈ 2 weeks if seriated, ~1 week if parallel.
