---
decision_id: DEC-V61-124
title: Mesh-regenerate · `target_cell_count` arg · AI proposes specific cell counts not just beginner/power presets
status: Proposed (2026-05-05 · pre-implementation surface scan complete; Codex pre-merge MANDATORY per RETRO-V61-001 multi-file backend + AI-driven case-mutation triggers + new tool argument that mutates polyMesh files)
codex_tool_report_path: reports/codex_tool_reports/v61_124_r1_chain.md (to be created)
codex_review_relay: CRS gpt-5.4 high (default per V61-119 §L2 sustained-86gs-instability protocol — empirically validated at V123 R8 to recover within 25min on both-relay outages)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-05
authored_under: User 2026-05-05 mandate "按你的顺序和建议，继续推进" — V123's mesh-quality 三明治 closed cleanly at 9 rounds. Of the 5 candidate axes (target_cell_count · lc override · Docker checkMesh · SSE progress · quick-action UI button) listed in V123 §"V1 deliberately excluded", V124 picks **target_cell_count** as the smallest, most contained axis explicitly because of V123 R1-R9 chain learnings (§L1 in V123 chain report) — when a feature touches a pre-existing safety contract, the V1 scope-down on the new feature alone is insufficient. target_cell_count is the only axis from V123's exclude-list that does NOT touch the route's path-state classification, the case_lock semantics, OR introduce new container management. It is pure additive plumbing on top of `characteristic_length_override`, which gmsh_runner already supports end-to-end.
parent_decisions:
  - DEC-V61-123 (mesh-regenerate tool · this DEC's argument-extension host — V123 closed at 9 rounds; V124 demonstrates methodology learning by deliberately picking the smallest no-contract-crossing axis)
  - DEC-V61-122 (mesh-quality adviser · V124 surfaces target_cell_count alongside V122's cell_count metric so the AI can propose "you have 80 cells; regenerate at ~100,000")
  - DEC-V61-105 (cell-budget classifier · `classify_cell_count` is the ultimate guard; V124's target_cell_count is bounded by the same hard cap)
  - DEC-V61-088 (pre-implementation surface scan · this DEC carries Surface-scan trailer)
  - RETRO-V61-001 (risk-tier · multi-file backend + AI-driven case-mutation triggers Codex pre-merge)
parent_artifacts:
  - ui/backend/services/meshing_gmsh/gmsh_runner.py:71-83 (`_default_characteristic_length` and `_gmsh_inline.characteristic_length_override` plumbing — already end-to-end; V124 adds a target_cell_count → lc conversion shim)
  - ui/backend/services/meshing_gmsh/pipeline.py:102 (`mesh_imported_case` — V124 extends with `target_cell_count: int | None = None` kwarg)
  - ui/backend/services/llm_coach/tool_registry.py (V123's RegenerateMeshArgs · V124 adds optional target_cell_count field with mutual-exclusion validation against mesh_mode)
counter_impact: +1 (autonomous_governance: true · backend-only argument extension that mutates polyMesh files via the existing V123 tool path. Kogami-trigger check: not phase-close, not RETRO draft, not arc-size retro at counter 82→83 (counter ≥ 20 trigger continues to be deferred per ongoing user mandate "按你的顺序和建议，继续推进"), not governance-rule change. Codex pre-merge MANDATORY per RETRO-V61-001 (multi-file backend + AI-driven case-mutation) — same trigger pattern as V121/V123.)
notion_sync_status: pending — Notion MCP server still disconnected; sync when reconnected
self_estimated_pass_rate: 70% (predicted 1-2 rounds · single-axis surface · pure additive plumbing on existing characteristic_length_override · no route-layer changes · no new container/Docker logic · no new safety contract crossing — applying V123 R1-R9 chain §L1 lesson by deliberately picking the smallest scope. The "tool registry append" calibration baseline (~70% / 1-2 rounds) applies because V124 does NOT cross the path-state safety surface that V123 had to harden over R3-R8.)

---

# DEC-V61-124 · target_cell_count arg

## Why now

V122 surfaces `cell_count_low` warnings when the mesh has under 100 cells. V123 lets the AI propose `regenerate_mesh(mesh_mode="power")` to refine. But the only knobs the AI has are two presets: `beginner` (~30k cells on a unit-cube geometry) and `power` (~250k). Real engineering intuition is "I want around N cells" not "I want one of two preset modes". V124 closes that gap: the AI can now propose `regenerate_mesh(target_cell_count=500_000)` and the engineer accepts. The cell-budget guard (V61-105) still bounds the request, so the AI cannot blow past the 50M hard cap.

This is **item #1** from V123's "V1 deliberately excluded" table — picked deliberately as the *smallest no-contract-crossing axis*. Items #3 (Docker checkMesh) and #4 (SSE progress) cross more pre-existing surfaces and per V123 §L1 should be filed as their own DECs after V124 ships.

## Surface scan (per DEC-V61-088)

**ROADMAP scan**: `target_cell_count` and `cell_count_target` are referenced *only* in `gmsh_runner.py:72` as a hypothetical-caller docstring fragment ("Fallback sizing when the caller doesn't supply ``cell_count_target``") — no actual implementation. V124 is greenfield with the foundational `characteristic_length_override` hook already in place.

**Existing-implementation grep** (`grep -rn "target_cell_count\|cell_count_target\|TARGET_CELL\|fit.*cell" ui/backend/`): zero hits outside the docstring. Disposition: **extend existing** — V124 plugs into the already-end-to-end `characteristic_length_override` plumbing.

## V1 scope (deliberately narrow)

The V124 PR ships exactly:

1. **`mesh_imported_case` extension** — add `target_cell_count: int | None = None` kwarg.
2. **`run_gmsh_on_imported_case` extension** — add `target_cell_count: int | None = None` kwarg, plumbed through `_subprocess_target` → `_gmsh_inline`.
3. **target_cell_count → lc conversion** in `_gmsh_inline`, applied AFTER bbox diagonal extraction. Formula: `lc = diagonal × 1.05 / target_cell_count^(1/3)` (calibrated to match beginner/power presets at 30k / 250k cells respectively for a unit cube — see `Why this formula` below).
4. **`RegenerateMeshArgs` extension** with optional `target_cell_count: int | None = None` field.
5. **Mutual exclusion validation** at the Pydantic args layer — exactly one of `mesh_mode` / `target_cell_count` may be set.
6. **Cell-budget bounds** at the args layer — `target_cell_count` must be in `[1_000, 50_000_000]` (1k floor prevents nonsense; 50M ceiling matches the V61-105 hard cap so an out-of-range request fails fast with `arg_validation_failed` rather than `cell_cap_exceeded` at meshing time).
7. **Tests** — happy path (handler invokes pipeline with target_cell_count) · arg validation (mutual exclusion · floor · ceiling) · pipeline pass-through (target_cell_count flows to gmsh_runner) · lc-formula sanity check (computed lc matches beginner/power presets for cube reference geometry within 5%).

The system prompt's `format_tool_registry_for_prompt()` already enumerates registered tools; updating the `regenerate_mesh` tool description to mention target_cell_count surfaces it automatically.

## V1 deliberately excluded (push to V125+)

| Excluded axis | Why excluded | Successor |
|---|---|---|
| Direct `lc` (characteristic length) override at the AI tool level | Bypasses cell-budget guard; engineer-only escape hatch with manual review needed | V125+ |
| Docker `checkMesh` integration for skewness / orthogonality / aspect ratio | Heavier surface — async Docker call, additional MeshQualityReport fields, separate timeout/cancel logic | V125 (originally part of the 三明治 vision; broken out per V123 §L1) |
| SSE progress streaming during gmsh+gmshToFoam (5-300s blocking) | V1 ships synchronous; UI shows spinner. Progress streaming requires a state-machine layer the route doesn't have today | V126+ |
| Quick-action "Regenerate mesh at N cells" UI button outside the AI proposal flow | Would duplicate the AI-coach surface; engineers can ask the coach instead | V126+ |
| Cancel-in-flight regenerate | Adds task-management surface | V126+ |
| Iterative cell-count fitting (mesh → measure cells → adjust lc → re-mesh until within ±5% of target) | The cell_count formula is approximate (±50% in practice for non-cube geometries); iterative fitting is heavier scope and the engineer can re-propose if the result is off | V125+ |

## Why this formula

For a tetrahedral mesh of a bbox-volume V with characteristic length lc:
- Cell count ≈ 6 × V / lc³ (gmsh's Delaunay 3D produces ~6 tets per cubic-lc volume on regular geometries)
- For a cube of side s: V = s³, diagonal d = s × √3, so V = (d/√3)³ ≈ 0.192 d³
- Therefore: lc ≈ (0.192 × d³ × 6 / N)^(1/3) = d × (1.155 / N)^(1/3) ≈ d × 1.05 / N^(1/3)

Sanity-check against existing presets (unit cube, d = √3 ≈ 1.732):
- target_cell_count = 30_000 → lc = 1.732 × 1.05 / 31.07 ≈ 0.0585 → matches `beginner` (d/30 ≈ 0.0577) within 1.4%
- target_cell_count = 250_000 → lc = 1.732 × 1.05 / 62.99 ≈ 0.0289 → matches `power` (d/60 ≈ 0.0289) within 0.1%

Real-world geometries (non-cubic) will diverge from this approximation; the cell_budget guard catches gross overshoots and the AI/engineer can re-propose. Documented in the kwarg docstring.

## Risk surface

- **Formula imprecision**: real cell counts may differ from target by ±50% for non-cube geometries. Documented; acceptable because the engineer sees the actual cell count in the V122 next snapshot and can re-propose. Cell budget guard (V61-105) still bounds.
- **Mutual exclusion at the args layer**: enforce via Pydantic `model_validator(mode='after')` so a proposal carrying both fields rejects with `arg_validation_failed`. Tests cover this.
- **Bounds at the args layer**: `target_cell_count` must be ≥1000 (prevents trivial / typo `target_cell_count=10`) and ≤50_000_000 (matches V61-105 hard cap). Tests cover both rails.
- **No new safety contract crossing**: V124 explicitly does NOT touch the route's path-state classification (V123-hardened), case_lock semantics, or container management. The expected Codex round count reflects this — predicted 1-2 rounds at 70% pass rate.

## Implementation plan

```python
# tool_registry.py additions

class RegenerateMeshArgs(BaseModel):
    """Args for ``regenerate_mesh`` (DEC-V61-123 + V61-124).

    Exactly one of ``mesh_mode`` or ``target_cell_count`` must be set:
      * ``mesh_mode`` → preset density (beginner ~30k cells, power ~250k)
      * ``target_cell_count`` → AI-proposed specific cell count (1k-50M)

    extra="forbid" matches V121/V123 trust-boundary discipline.
    """

    model_config = ConfigDict(extra="forbid")

    mesh_mode: Literal["beginner", "power"] | None = None
    target_cell_count: int | None = Field(
        default=None,
        ge=1_000,
        le=50_000_000,
        description=(
            "AI-proposed specific cell count. The pipeline converts this "
            "to a characteristic length via a cube approximation; real "
            "cell count may differ by up to ±50% for non-cube geometries. "
            "Bounded by V61-105 cell-budget hard cap (50M)."
        ),
    )

    @model_validator(mode="after")
    def _exactly_one_density_axis(self) -> "RegenerateMeshArgs":
        if (self.mesh_mode is None) == (self.target_cell_count is None):
            raise ValueError(
                "exactly one of mesh_mode or target_cell_count must be set"
            )
        return self


def _handle_regenerate_mesh(case_dir: Path, args: BaseModel) -> ApplyResult:
    typed = args
    assert isinstance(typed, RegenerateMeshArgs)
    case_id = case_dir.name
    if not os.path.lexists(case_dir):
        raise ToolDispatchError(...)  # unchanged from V123
    with case_lock(case_dir):
        if typed.target_cell_count is not None:
            result = mesh_imported_case(
                case_id, target_cell_count=typed.target_cell_count
            )
        else:
            result = mesh_imported_case(case_id, mesh_mode=typed.mesh_mode)
    summary_density = (
        f"target ~{typed.target_cell_count:,} cells"
        if typed.target_cell_count is not None
        else f"'{typed.mesh_mode}' mode"
    )
    summary = (
        f"Regenerated mesh ({summary_density}): "
        f"{result.cell_count} cells, {result.face_count} faces."
    )
    if result.warning:
        summary += f" Warning: {result.warning}"
    return ApplyResult(...)


# pipeline.py additions

def mesh_imported_case(
    case_id: str,
    *,
    mesh_mode: MeshMode = "beginner",
    target_cell_count: int | None = None,
    container_name: str | None = None,
) -> MeshResult:
    ...
    gmsh_result = run_gmsh_on_imported_case(
        stl_path=stl_path,
        output_msh_path=msh_path,
        mesh_mode=mesh_mode,
        target_cell_count=target_cell_count,
    )
    ...


# gmsh_runner.py additions

def run_gmsh_on_imported_case(
    *,
    stl_path: Path,
    output_msh_path: Path,
    mesh_mode: str = "beginner",
    target_cell_count: int | None = None,
    characteristic_length_override: float | None = None,
) -> GmshRunResult:
    ...

# Inside _gmsh_inline, after bbox diagonal extraction:
if target_cell_count is not None:
    # V124: convert target_cell_count → lc using cube approximation.
    # See DEC-V61-124 §"Why this formula" for derivation; calibrated to
    # match beginner/power presets at 30k/250k cells respectively.
    lc = diagonal * 1.05 / (target_cell_count ** (1.0 / 3.0))
elif characteristic_length_override is not None:
    lc = characteristic_length_override
else:
    lc = _default_characteristic_length(diagonal, mesh_mode)
```

## Acceptance criteria

- AC-1: `RegenerateMeshArgs(target_cell_count=100_000)` passes validation; `RegenerateMeshArgs()` (neither field set) and `RegenerateMeshArgs(mesh_mode="power", target_cell_count=100_000)` (both set) raise `ValidationError`.
- AC-2: `target_cell_count=999` rejects; `target_cell_count=50_000_001` rejects; `target_cell_count=1_000` and `target_cell_count=50_000_000` accept.
- AC-3: `dispatch(case_dir, "regenerate_mesh", {"target_cell_count": 500_000})` invokes `mesh_imported_case` with `target_cell_count=500_000` (test mocks the pipeline).
- AC-4: When `target_cell_count` is passed to `_gmsh_inline`, the resulting `lc` value matches the cube-derived formula within 0.5% for a synthetic unit-cube geometry.
- AC-5: For target_cell_count=30_000 the computed lc matches beginner-preset lc within 5% (regression-protect the formula calibration).
- AC-6: For target_cell_count=250_000 the computed lc matches power-preset lc within 5%.
- AC-7: V123 happy paths (mesh_mode="beginner" / "power") continue to work unchanged.
- AC-8: Tool description string mentions target_cell_count and the 1k-50M bounds so the LLM knows the schema.

## Test plan

- `test_regenerate_args_accepts_target_cell_count` · `test_regenerate_args_accepts_mesh_mode_only` · `test_regenerate_args_rejects_both_set` · `test_regenerate_args_rejects_neither_set`
- `test_regenerate_args_target_cell_count_floor` · `test_regenerate_args_target_cell_count_ceiling`
- `test_dispatch_regenerate_mesh_with_target_cell_count_invokes_pipeline_with_target` · `test_dispatch_regenerate_mesh_summary_says_target_when_set`
- `test_lc_from_target_cell_count_matches_beginner_preset_for_30k` · `test_lc_from_target_cell_count_matches_power_preset_for_250k` (these run inside `_gmsh_inline` via a synthetic-cube fixture; mock gmsh)
- `test_pipeline_passes_target_cell_count_to_gmsh_runner` (assert keyword forwarding)
- `test_v123_mesh_mode_paths_unchanged` (regression: V123's beginner/power tests still pass)
- (Existing prompt tests in `test_llm_coach.py` will detect the updated `regenerate_mesh` description automatically — extend the assertion to check for `target_cell_count` in the description.)

## Process note

V124 is the explicit application of V123 R1-R9 §L1 lesson: when the prior arc revealed that "tool entry crossing pre-existing safety contract" is a 7-10-round calibration baseline, the next DEC should *avoid* crossing safety contracts entirely. V124's surface is genuinely additive — `characteristic_length_override` plumbing is already end-to-end through gmsh_runner; the only new code is the formula + Pydantic mutual-exclusion validator + handler dispatch branch.

If V124 lands at 1-2 rounds as predicted, that confirms §L1's calibration baseline distinction (cross-contract vs no-contract) is the right axis. If V124 surprises with a 4+ round cascade, the calibration needs further refinement — likely "any change to a tool's args schema" needs its own baseline regardless of contract crossing.
