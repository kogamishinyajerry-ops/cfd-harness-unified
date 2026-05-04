---
decision_id: DEC-V61-123
title: Mesh-regenerate tool · `regenerate_mesh` registry entry wrapping `mesh_imported_case` · AI proposes coarse→fine remesh, engineer approves
status: Accepted (2026-05-05 · Codex CRS gpt-5.4 high R9 APPROVE clean at 0ff51e3 · 9-round chain · major overrun vs predicted 70%/1-2 rounds — see chain report §L1 + §L4 for the under-specified-safety-contract and cross-platform-errno-parity calibration baselines)
anchor_commit: 0ff51e3
codex_tool_report_path: reports/codex_tool_reports/v61_123_r1_chain.md
codex_review_relay: CRS gpt-5.4 high (default per V61-119 §L2 sustained-86gs-instability protocol)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-04
authored_under: User 2026-05-04 mandate "按你的顺序和建议，继续推进" — V123 is item I (second half of mesh-quality 三明治) following V122's adviser foundation. V122 gave the AI mesh KNOWLEDGE; V123 gives it the HAND to act on what it sees. When the V122 prompt section reports `cell_count_low` warning, the AI now has a registered tool to propose `regenerate_mesh(mesh_mode="power")` and the engineer approves via the V121 PROPOSAL protocol.
parent_decisions:
  - DEC-V61-122 (mesh-quality adviser · upstream KNOWLEDGE source — when V122 surfaces `cell_count_low` warning, V123 is the actionable remediation; the two compose into the 三明治)
  - DEC-V61-121 (AI coach action proposals · V123 plugs into the same `_TOOL_REGISTRY` and reuses the audit / lock / extra="forbid" trust boundary; zero protocol changes)
  - DEC-V61-088 (pre-implementation surface scan · this DEC carries Surface-scan trailer)
  - RETRO-V61-001 (risk-tier · new tool that mutates polyMesh files + AI-driven case-mutation triggers Codex pre-merge)
parent_artifacts:
  - ui/backend/services/llm_coach/tool_registry.py (V121 registry · V123 appends `regenerate_mesh` descriptor + handler · existing trust-boundary discipline (extra="forbid" · per-tool args_model · ToolDispatchError translation) preserves the V121 contract)
  - ui/backend/services/meshing_gmsh/pipeline.py:102 (`mesh_imported_case(case_id, *, mesh_mode, container_name)` · V123 handler delegates to this; pipeline already has `MeshPipelineError(failing_check)` envelope so V123 only needs a thin translation)
  - ui/backend/services/llm_coach/audit.py (V121 audit serializer · V123 ApplyResult flows through the existing audit lock — no changes needed)
counter_impact: +1 (autonomous_governance: true · new backend tool entry that mutates polyMesh files. Kogami-trigger check: not phase-close, not RETRO draft, not arc-size retro at counter 81→82 (counter ≥ 20 trigger continues to be deferred per ongoing user mandate "按你的顺序和建议，继续推进"), not governance-rule change. Codex pre-merge MANDATORY per RETRO-V61-001 (multi-file backend + AI-driven case-mutation) — same trigger pattern as V121.)
notion_sync_status: pending — Notion MCP server still disconnected; sync when reconnected
self_estimated_pass_rate: 70% (predicted 1-2 rounds · single-axis surface · V121 trust boundary already validated · `mesh_imported_case` has 23+ rounds of pre-existing Codex audit · risk concentrated in long-blocking-time + idempotency)

---

# DEC-V61-123 · Mesh-regenerate tool

## Why now

V122 gave the AI coach mesh KNOWLEDGE — it can now read `cell_count_low` / `dense_mesh` / `bb_collapsed_dim` warnings. But the coach can only TALK about the mesh; it can't fix it. V123 closes the loop: a `regenerate_mesh` tool entry in the V121 registry. When the AI surfaces "your mesh is under-refined at 80 cells", it can now also propose `<<PROPOSAL ... regenerate_mesh(mesh_mode="power") ...>>` and the engineer hits Accept. The mesh re-runs and the next V122 snapshot shows the result.

This completes the **mesh-quality 三明治** (item #2 on the differentiation list): adviser foundation (V122) + remediation tool (V123). Two-DEC arc H→I closes here.

## Surface scan (per DEC-V61-088)

**ROADMAP scan**: post-W5 + workbench-rollout return zero hits for `regenerate_mesh`, `regen_mesh`, `set_mesh_lc`, `remesh`. The single grep hit at `report_bundle.py:711` is a stale comment about cached-result invalidation, not an actual tool. V123 is structurally distinct.

**Existing-implementation grep** (`grep -rin "gmsh.*regenerate\|set_mesh_lc\|remesh" ui/backend/`): no pre-existing implementation. `mesh_imported_case(case_id, *, mesh_mode, container_name)` exists at `pipeline.py:102` and is the canonical re-mesh path; V123's handler delegates to it. Disposition: **extend existing** (registry append + thin handler).

## V1 scope (deliberately narrow)

The V123 PR ships exactly:

1. **`RegenerateMeshArgs` Pydantic model** in `tool_registry.py` with `mesh_mode: Literal["beginner","power"]` and `model_config = ConfigDict(extra="forbid")`.
2. **`_handle_regenerate_mesh(case_dir, args)` handler** that delegates to `mesh_imported_case(case_id=case_dir.name, mesh_mode=args.mesh_mode)` and translates `MeshPipelineError` → `ToolDispatchError(failing_check="underlying_service_error")` preserving the underlying `failing_check` in the message.
3. **Registry entry** `"regenerate_mesh"` with description text the system prompt will surface.
4. **Tests** — dispatch happy path (mocked `mesh_imported_case`) · arg validation (extra key rejected) · underlying-error translation (`MeshPipelineError("cell_cap_exceeded")` → `ToolDispatchError(failing_check="underlying_service_error")`) · idempotency note (re-meshing always overwrites; the test asserts a second call with same args succeeds, no replay-key needed).

The system prompt's `format_tool_registry_for_prompt()` already enumerates registered tools, so V123 surfaces automatically — no prompts.py change.

## V1 deliberately excluded (push to V124+)

| Excluded axis | Why excluded | Successor |
|---|---|---|
| Custom `target_cell_count` arg (numeric) | Beginner/power presets cover 90% of remediation cases; numeric input needs UI surface for the engineer to type a number AND validation against the V61-105 cell budget classifier | V124 |
| Direct `lc` (characteristic length) override | Bypasses cell budget guard; would need a per-case scaling sanity check | V124+ |
| Docker `checkMesh` integration for skewness / orthogonality / aspect ratio | Heavier surface — async Docker call, additional `MeshQualityReport` fields, separate timeout/cancel logic | V124 (originally part of the 三明治 vision; broken out as its own arc) |
| SSE progress streaming during gmsh+gmshToFoam (5-300s blocking) | V1 ships synchronous; UI shows spinner. Progress streaming requires a state-machine layer the route doesn't have today | V125+ |
| Quick-action "Regenerate mesh" button in the workbench UI (outside the AI proposal flow) | Would duplicate the AI-coach surface; engineers can ask the coach instead | V125+ |
| Replay-key / dedup across concurrent regenerate proposals | gmsh is naturally idempotent (same input STL + same lc → same output mesh up to gmsh's deterministic seed); a stale proposal that re-runs after the engineer already accepted a fresher proposal harmlessly produces the same output | (not needed) |
| Cancel-in-flight regenerate | Adds task-management surface; the synchronous block returns a single 200/4xx/5xx | V125+ |

## Risk surface

- **Long-blocking call**: a real mesh on a non-trivial geometry can take 30-300s. The route returns synchronously. UI must show a spinner; the V121 chat panel's existing "applying…" state covers this. **No change needed in V123** — same blocking shape as V108's BC override route.
- **Concurrent mesh writes**: V108's `case_lock` already serializes per-case writes; V123's handler delegates to `mesh_imported_case` which writes `polyMesh/` directly without taking `case_lock`. Two concurrent regenerate proposals would race. **Mitigation**: have `_handle_regenerate_mesh` acquire `case_lock` before invoking the pipeline. Same pattern V121 audit lock uses; reentrant-safe because `mesh_imported_case` doesn't itself take `case_lock`.
- **Underlying pipeline error envelope**: `MeshPipelineError.failing_check` is a Literal of 5 values (case_not_found · source_not_imported · gmsh_diverged · cell_cap_exceeded · gmshToFoam_failed). V123 translates ALL of them to `underlying_service_error` and preserves the original `failing_check` in the message text. Route maps to HTTP 500 (unexpected backend failure during AI tool dispatch); UI's chat panel shows the error string.

## Implementation plan

```python
# tool_registry.py additions

from ui.backend.services.case_manifest.locking import case_lock  # V108
from ui.backend.services.meshing_gmsh import (
    MeshPipelineError,
    mesh_imported_case,
)


class RegenerateMeshArgs(BaseModel):
    """Args for ``regenerate_mesh``. Re-runs gmsh + gmshToFoam on the
    imported STL with the requested mesh density mode, replacing
    ``polyMesh/`` in place.

    Codex R1 P3 (V121): ``extra="forbid"`` rejects off-contract keys.
    """

    model_config = ConfigDict(extra="forbid")

    mesh_mode: Literal["beginner", "power"] = Field(
        ...,
        description=(
            "Density preset. 'beginner' targets a few hundred thousand "
            "cells (lc ≈ diagonal/30); 'power' targets ~10× finer "
            "(lc ≈ diagonal/60). Both are bounded by the V61-105 "
            "cell-budget guard."
        ),
    )


def _handle_regenerate_mesh(case_dir: Path, args: BaseModel) -> ApplyResult:
    typed = args
    assert isinstance(typed, RegenerateMeshArgs)
    case_id = case_dir.name
    # Serialize concurrent regenerate proposals via V108's case_lock —
    # mesh_imported_case writes polyMesh/ in place, so two concurrent
    # accepts would race on file content.
    with case_lock(case_dir):
        try:
            result = mesh_imported_case(case_id, mesh_mode=typed.mesh_mode)
        except MeshPipelineError as exc:
            raise ToolDispatchError(
                f"mesh pipeline failed: {exc.failing_check}: {exc}",
                failing_check="underlying_service_error",
            ) from exc
    return ApplyResult(
        tool="regenerate_mesh",
        summary=(
            f"Regenerated mesh in '{typed.mesh_mode}' mode: "
            f"{result.cell_count} cells, {result.face_count} faces."
            + (f" Warning: {result.warning}" if result.warning else "")
        ),
        state_after={
            "cell_count": result.cell_count,
            "face_count": result.face_count,
            "point_count": result.point_count,
            "mesh_mode": result.mesh_mode,
        },
    )


_TOOL_REGISTRY["regenerate_mesh"] = ToolDescriptor(
    name="regenerate_mesh",
    args_model=RegenerateMeshArgs,
    handler=_handle_regenerate_mesh,
    description=(
        "Re-run gmsh + gmshToFoam on the case's imported STL to produce "
        "a fresh polyMesh with the requested density. Use after the "
        "mesh-quality snapshot reports cell_count_low or when the "
        "engineer asks to refine. args: mesh_mode "
        "(one of beginner | power)."
    ),
)
```

## Acceptance criteria

- AC-1: `regenerate_mesh` appears in `list_tools()` output and in the system prompt's tool registry section.
- AC-2: `dispatch(case_dir, "regenerate_mesh", {"mesh_mode": "power"})` returns an `ApplyResult` with cell_count from the underlying pipeline (test mocks `mesh_imported_case`).
- AC-3: `dispatch(..., {"mesh_mode": "power", "extra_field": 1})` raises `ToolArgError` (extra="forbid" enforced).
- AC-4: `MeshPipelineError("…", "cell_cap_exceeded")` raised by the underlying pipeline becomes `ToolDispatchError(failing_check="underlying_service_error")` with the original `failing_check` preserved in the message.
- AC-5: Concurrent `dispatch` calls on the same case_dir serialize via `case_lock` (test uses two threads + a slow-path mock; assert sequential execution).
- AC-6: Idempotency note: a second `dispatch` with the same args after the first succeeds (no replay-key store; gmsh's determinism guarantees same output).

## Test plan

- `test_regenerate_mesh_dispatch_happy_path` — patches `mesh_imported_case` to return a fixed `MeshResult`; asserts `ApplyResult.tool == "regenerate_mesh"`, summary contains cell count, state_after contains the underlying result fields.
- `test_regenerate_mesh_arg_validation_extra_key` — extra key raises `ToolArgError`.
- `test_regenerate_mesh_arg_validation_bad_mode` — `mesh_mode="ultra"` raises `ToolArgError`.
- `test_regenerate_mesh_pipeline_error_translated` — `mesh_imported_case` raises `MeshPipelineError("cap exceeded", "cell_cap_exceeded")` → `ToolDispatchError(failing_check="underlying_service_error")` with `cell_cap_exceeded` in message.
- `test_regenerate_mesh_serialized_under_case_lock` — 2-thread regenerate, slow-path mock, assert sequential ordering.
- `test_regenerate_mesh_idempotent_re_dispatch` — two sequential dispatches with same args both succeed.
- (Existing prompt tests in `test_llm_coach.py` will detect the new tool in `Registered tools` listing — extend `test_prompt_includes_v121_proposal_protocol_and_tool_registry` with a `regenerate_mesh` assertion.)

## Process note

V123 is the closing half of the **2-DEC arc H→I (mesh-quality 三明治)**. V122 (foundation, 2 rounds APPROVE clean) ships the adviser; V123 ships the hand. Both DECs use V1-explicit-scope-down to keep round count bounded — the deliberately-excluded axes table above pushes target_cell_count, lc override, checkMesh, SSE progress, cancel, and quick-action UI all to V124+.

Self-pass-rate prediction 70% / 1-2 rounds reflects: (a) the V121 trust-boundary discipline is now reused without changes; (b) `mesh_imported_case` has ~23 rounds of historical Codex audit so the underlying surface is mature; (c) the only new logic is a 2-axis tool — args validation + handler delegation. Codex's most likely finding class would be a missed `case_lock` acquisition or a missed pipeline-error case; both are within the documented scope of the implementation.
