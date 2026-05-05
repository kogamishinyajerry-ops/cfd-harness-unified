---
decision_id: DEC-V61-125
title: Mesh-regenerate · `lc_override` arg · engineer escape hatch for direct characteristic-length sizing
status: Proposed (2026-05-05 · pre-implementation surface scan complete; Codex pre-merge MANDATORY per RETRO-V61-001 multi-file backend + AI-driven case-mutation triggers + new tool argument that mutates polyMesh files)
codex_tool_report_path: reports/codex_tool_reports/v61_125_r1_chain.md (to be created)
codex_review_relay: CRS gpt-5.4 high (default per V61-119 §L2 protocol)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-05
authored_under: User 2026-05-05 mandate "按你的顺序和建议，继续推进" — V124 closed cleanly at 3 rounds, validating the §L1 calibration distinction. V125 picks the next item from V124's exclude-list in priority order: **direct `lc` (characteristic length) override**. This is the engineer-escape-hatch axis — when target_cell_count's cube approximation diverges too much for a non-cube geometry, the engineer can set `lc_override=0.001` directly and bypass the formula entirely. Per V124's §L1 calibration baseline (no-contract-crossing tool registry append ≈ 70%/1-2 rounds), V125 mirrors V124's surface exactly and is expected to converge similarly.
parent_decisions:
  - DEC-V61-124 (target_cell_count arg · this DEC's structural sibling — adds a third density axis to RegenerateMeshArgs alongside mesh_mode + target_cell_count, with 3-way mutual exclusion. Cube-formula sizing (V124) and direct lc (V125) are both "engineer-supplied sizing"; both share the "target" MeshMode label so the schema literal stays at 3 values)
  - DEC-V61-123 (mesh-regenerate tool · V125's registry append host — same trust-boundary discipline (extra="forbid", typed-error translation, lock contract))
  - DEC-V61-088 (pre-implementation surface scan · this DEC carries Surface-scan trailer)
  - RETRO-V61-001 (risk-tier · multi-file backend + AI-driven case-mutation triggers Codex pre-merge)
parent_artifacts:
  - ui/backend/services/meshing_gmsh/gmsh_runner.py:438-481 (existing `characteristic_length_override` hook · V125 adds NO new gmsh_runner code — pure plumbing through pipeline + tool registry)
  - ui/backend/services/meshing_gmsh/pipeline.py:102 (`mesh_imported_case` · V124 added target_cell_count kwarg; V125 adds characteristic_length_override kwarg using identical pattern)
  - ui/backend/services/llm_coach/tool_registry.py (V123/V124 RegenerateMeshArgs · V125 extends with optional lc_override field + extends mutual-exclusion validator from 2-way to 3-way)
counter_impact: +1 (autonomous_governance: true · backend-only argument extension that mutates polyMesh files via the existing V123/V124 tool path. Kogami-trigger check: not phase-close, not RETRO draft, not arc-size retro at counter 83→84 (counter ≥ 20 trigger continues to be deferred per ongoing user mandate "按你的顺序和建议，继续推进"), not governance-rule change. Codex pre-merge MANDATORY per RETRO-V61-001 (multi-file backend + AI-driven case-mutation) — same trigger pattern as V121/V123/V124.)
notion_sync_status: pending — Notion MCP server still disconnected; sync when reconnected
self_estimated_pass_rate: 75% (predicted 1-2 rounds · pure additive plumbing on existing characteristic_length_override hook · no route-layer changes · no new safety contract crossing · §L1 calibration baseline applies. Slight uptick from V124's 70% because V125 reuses V124's mutual-exclusion validator pattern + V124's MeshMode literal — incremental change to a structure that just shipped clean.)

---

# DEC-V61-125 · lc_override arg

## Why now

V124 added `target_cell_count` for the AI to propose specific cell counts. The cube-formula sizing matches presets within ~1% on cubes but diverges up to ±50% on non-cube geometries (long thin channels, complex bodies). When the engineer is fine-tuning past that imprecision (or wants to preserve a sizing they manually validated), they currently have no direct knob — they must keep re-proposing target_cell_count and watching the result converge. V125 closes the gap: `lc_override=0.005` sets the characteristic length directly. Cube formula is bypassed; cell-budget hard cap still applies; engineer is responsible for picking a reasonable lc value.

This is **item #2** from V124's "V1 deliberately excluded" table — picked in the documented priority order. Items #3 (Docker checkMesh), #4 (SSE progress), and #5+ remain queued.

## Surface scan (per DEC-V61-088)

**ROADMAP scan**: `lc_override` returns zero hits across `ui/backend/services/`, `ui/backend/routes/`, `scripts/` (excluding tests + __pycache__). The existing `characteristic_length_override` hook in `gmsh_runner.py` is end-to-end through `_subprocess_target` and `_gmsh_inline` — V125 adds NO new gmsh_runner code, just pipeline-level pass-through and registry-level argument exposure. Disposition: **extend existing**.

**Existing-implementation grep**: `characteristic_length_override` is referenced 9 times in `gmsh_runner.py` and is already plumbed; `mesh_imported_case` does NOT currently accept it. V125 wires that kwarg through.

## V1 scope (deliberately narrow)

The V125 PR ships exactly:

1. **`mesh_imported_case` extension** — add `characteristic_length_override: float | None = None` kwarg, plumbed through to `run_gmsh_on_imported_case` (1 line change at the call site).
2. **`RegenerateMeshArgs` extension** — add `lc_override: float | None` field with `gt=0` Pydantic constraint (must be positive; no upper bound — engineer is responsible, cell-budget hard cap will catch unreasonable values).
3. **3-way mutual exclusion validator** — extend the existing `@model_validator(mode='after')` from 2-way to 3-way: exactly one of `{mesh_mode, target_cell_count, lc_override}` must be set.
4. **Handler dispatch** — when `lc_override` is set, pass to `mesh_imported_case(case_id, characteristic_length_override=lc)`. Pipeline labels the run as `mesh_mode="target"` (same label as target_cell_count — both are "engineer-supplied sizing" semantically; reusing the existing literal avoids a 4-way enum split).
5. **Tool description update** — add `lc_override` to the `regenerate_mesh` description string so the LLM knows the schema.
6. **Tests** — args validation (lc_override alone passes · lc_override=0 rejects · lc_override=-0.001 rejects · 2-of-3 set rejects · all-3 set rejects · neither set still rejects per V124) · dispatch happy path (lc_override forwards through pipeline as characteristic_length_override) · summary surfaces "lc=X" when set · V123/V124 paths still work unchanged.

The system prompt's `format_tool_registry_for_prompt()` already enumerates registered tools; updating the `regenerate_mesh` description surfaces lc_override automatically.

## V1 deliberately excluded (push to V126+)

| Excluded axis | Why excluded | Successor |
|---|---|---|
| Docker `checkMesh` integration for skewness / orthogonality / aspect ratio | Heavier surface — async Docker call, additional MeshQualityReport fields, separate timeout/cancel logic. Originally part of the 三明治 vision; user-visible value is highest of the remaining queued items but scope is biggest | V126 |
| SSE progress streaming during gmsh+gmshToFoam (5-300s blocking) | V1 ships synchronous; UI shows spinner. Progress streaming requires a state-machine layer the route doesn't have today | V127+ |
| Quick-action "Regenerate mesh at lc=X" UI button outside the AI proposal flow | Would duplicate the AI-coach surface; engineers can ask the coach instead | V127+ |
| Cancel-in-flight regenerate | Adds task-management surface | V127+ |
| Iterative cell-count fitting (mesh → measure cells → adjust lc → re-mesh until within tolerance) | Considered as the V125 candidate but rejected — low user value (formula already matches presets within 5%) compared to either lc_override (engineer escape) or Docker checkMesh (real quality metrics) | V128+ if telemetry shows demand |
| New 4th MeshMode literal (e.g. "lc_override") for label honesty | Considered but rejected — both target_cell_count and lc_override are "engineer-supplied sizing" semantically. Reusing "target" mode keeps the schema enum at 3 values, avoiding a 4-way ripple across cell_budget.py + pipeline.py + schemas/mesh_imported.py + frontend types | (not needed) |
| Upper bound on lc_override | The cell-budget hard cap (50M) catches unreasonably-fine lc; an upper-bound on lc itself would need geometry-specific calibration. Engineer is responsible for picking a reasonable value | (not needed in V1) |

## Why "target" MeshMode is reused (not a new "lc_override" literal)

V124 R1 introduced "target" MeshMode for honest labeling of `target_cell_count` runs. V125's `lc_override` runs are also "engineer-supplied sizing" — distinct from "beginner" or "power" presets. Two options were considered:

A. Add a 4th literal `"lc_override"` so the response distinguishes target_cell_count vs lc_override runs.
B. Reuse `"target"` for both, with the rationale that both are "engineer override of preset sizing".

**Decision: B (reuse)** for these reasons:
- The schema enum stays at 3 values; no ripple across `cell_budget.py`, `pipeline.py`, `schemas/mesh_imported.py`, `MeshSummary`, frontend types.
- The `RegenerateMeshArgs` response (via `state_after`) carries the actual fields the engineer set — the route consumer can already distinguish target_cell_count vs lc_override by looking at the request that triggered the run.
- "target" mode's classification semantics (skip beginner soft warning, keep hard cap) apply identically to lc_override — both mean "engineer asked for this sizing explicitly".

If telemetry later reveals that the response consumer needs to distinguish the two paths from the response alone (without back-referencing the request), V126+ can split the literal at that point.

## Risk surface

- **No new safety contract crossing**: V125 explicitly does NOT touch the route's path-state classification (V123-hardened), case_lock semantics, container management, or the schema's MeshMode literal beyond what V124 already established. Per V123 §L1 + V124 §L1 calibration baselines, predicted round count is 1-2.
- **3-way mutual exclusion validator complexity**: the validator goes from "exactly one of A xor B" to "exactly one of A, B, C". Pydantic allows this naturally; tests cover all 7 combinations of the 3 booleans (000, 001, 010, 011, 100, 101, 110, 111 — only 001/010/100 should accept).
- **Bounds at the args layer**: `lc_override` must be >0 (Pydantic `gt=0`). No upper bound — cell-budget hard cap (50M cells) catches unreasonably-fine lc values at meshing time.
- **Latent landmine awareness (V124 §L2 lesson)**: V125 doesn't add new schema enum values, so no new schema-side serialization paths to audit. The `MeshSummary` schema already accepts "target" mode (V124 R2 fix); V125's lc_override runs flow through the same path. No new latent landmines expected.

## Implementation plan

```python
# tool_registry.py (additions to existing V124 RegenerateMeshArgs)

class RegenerateMeshArgs(BaseModel):
    """Args for ``regenerate_mesh`` (DEC-V61-123 + V61-124 + V61-125).

    Exactly one of mesh_mode, target_cell_count, lc_override must be set:
      * mesh_mode → preset density (beginner ~30k cells, power ~250k)
      * target_cell_count → V124 AI-proposed cell count via cube formula
      * lc_override → V125 engineer-supplied characteristic length directly
    """

    model_config = ConfigDict(extra="forbid")
    mesh_mode: Literal["beginner", "power"] | None = None
    target_cell_count: int | None = Field(default=None, ge=1_000, le=50_000_000)
    lc_override: float | None = Field(
        default=None,
        gt=0,
        description=(
            "DEC-V61-125: engineer-supplied characteristic length (lc) "
            "in case-geometry units. Bypasses both mesh_mode and "
            "target_cell_count's cube formula. Cell-budget hard cap "
            "(50M cells) still applies; engineer is responsible for "
            "picking a reasonable value. Mutually exclusive with "
            "mesh_mode and target_cell_count."
        ),
    )

    @model_validator(mode="after")
    def _exactly_one_density_axis(self) -> "RegenerateMeshArgs":
        set_count = sum([
            self.mesh_mode is not None,
            self.target_cell_count is not None,
            self.lc_override is not None,
        ])
        if set_count != 1:
            raise ValueError(
                "exactly one of mesh_mode / target_cell_count / "
                f"lc_override must be set (got {set_count})"
            )
        return self


def _handle_regenerate_mesh(case_dir: Path, args: BaseModel) -> ApplyResult:
    typed = args
    assert isinstance(typed, RegenerateMeshArgs)
    case_id = case_dir.name
    if not os.path.lexists(case_dir):
        raise ToolDispatchError(...)
    with case_lock(case_dir):
        if typed.target_cell_count is not None:
            result = mesh_imported_case(
                case_id, target_cell_count=typed.target_cell_count
            )
        elif typed.lc_override is not None:
            result = mesh_imported_case(
                case_id, characteristic_length_override=typed.lc_override
            )
        else:
            result = mesh_imported_case(case_id, mesh_mode=typed.mesh_mode)
    if typed.target_cell_count is not None:
        density_label = f"target ~{typed.target_cell_count:,} cells"
    elif typed.lc_override is not None:
        density_label = f"lc={typed.lc_override:.4g}"
    else:
        density_label = f"'{typed.mesh_mode}' mode"
    summary = (
        f"Regenerated mesh ({density_label}): "
        f"{result.cell_count} cells, {result.face_count} faces."
    )
    if result.warning:
        summary += f" Warning: {result.warning}"
    return ApplyResult(
        tool="regenerate_mesh",
        summary=summary,
        state_after={
            "cell_count": result.cell_count,
            "face_count": result.face_count,
            "point_count": result.point_count,
            "mesh_mode": result.mesh_mode,
        },
    )


# pipeline.py additions

def mesh_imported_case(
    case_id: str,
    *,
    mesh_mode: MeshMode = "beginner",
    target_cell_count: int | None = None,
    characteristic_length_override: float | None = None,
    container_name: str | None = None,
) -> MeshResult:
    ...
    gmsh_result = run_gmsh_on_imported_case(
        stl_path=stl_path,
        output_msh_path=msh_path,
        mesh_mode=mesh_mode,
        target_cell_count=target_cell_count,
        characteristic_length_override=characteristic_length_override,
    )
    ...
    # V125: characteristic_length_override is also "engineer-supplied
    # sizing" — share V124's "target" MeshMode label.
    if target_cell_count is not None or characteristic_length_override is not None:
        effective_mode = "target"
    else:
        effective_mode = mesh_mode
```

## Acceptance criteria

- AC-1: `RegenerateMeshArgs(lc_override=0.005)` passes validation; `RegenerateMeshArgs(lc_override=0)` rejects (gt=0); `RegenerateMeshArgs(lc_override=-0.001)` rejects.
- AC-2: All 4 invalid combinations of the 3 fields reject (none-set, 2-set, 3-set across all permutations).
- AC-3: All 3 valid single-field combinations pass.
- AC-4: `dispatch(case_dir, "regenerate_mesh", {"lc_override": 0.005})` invokes `mesh_imported_case` with `characteristic_length_override=0.005` (test mocks the pipeline).
- AC-5: Summary surfaces `lc=0.005` (or similar) when lc_override is set; summary does NOT say "mode" or "target ~N cells".
- AC-6: V123 mesh_mode paths and V124 target_cell_count paths continue unchanged.
- AC-7: `effective_mode` in pipeline is "target" when lc_override is set (same label V124 uses for target_cell_count).
- AC-8: Tool description string mentions lc_override and the gt=0 constraint.

## Test plan

- `test_regenerate_args_accepts_lc_override` · `test_regenerate_args_rejects_lc_override_zero` · `test_regenerate_args_rejects_lc_override_negative`
- `test_regenerate_args_rejects_lc_override_with_mesh_mode` · `test_regenerate_args_rejects_lc_override_with_target_cell_count` · `test_regenerate_args_rejects_all_three_set`
- `test_dispatch_regenerate_mesh_with_lc_override_invokes_pipeline` (assert characteristic_length_override forwarding)
- `test_dispatch_regenerate_mesh_summary_says_lc_when_set`
- `test_pipeline_lc_override_run_classified_as_target_mode` (assert pipeline labels it "target" not "beginner")
- `test_v124_target_cell_count_paths_unchanged` (regression)
- `test_v123_mesh_mode_paths_unchanged` (regression)
- `test_regenerate_mesh_tool_description_mentions_lc_override`

## Process note

V125 is the second consecutive "no-contract-crossing" DEC after V124, deliberately mirroring V124's surface to test the §L1 calibration baseline more thoroughly. If V125 lands at 1-2 rounds (matching V124), the calibration baseline is doubly validated. If V125 surprises with 4+ rounds, the §L1 distinction needs further refinement.

The 3-way mutual exclusion is the only meaningfully-new logic; it's a pure args-layer addition with no contract surface. Latent landmine prevention per V124 §L2 lesson: explicitly check that schemas/mesh_imported.py and frontend types do NOT need updates (no new MeshMode literal added; "target" already covers lc_override semantically).
