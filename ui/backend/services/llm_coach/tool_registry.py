"""DEC-V61-121 · LLM coach tool registry + dispatcher.

V1 has exactly ONE tool — ``set_patch_bc_type`` — that wraps V61-108's
``upsert_override`` service function. The registry is designed
extensible so V61-122+ can add new tools by appending to
``_TOOL_REGISTRY``; dispatch is a single ``dispatch(...)`` call site
that the route uses uniformly.

Trust boundary: any tool the LLM proposes must appear in the registry,
or ``dispatch`` raises ``UnknownToolError``. Per-tool argument
validation runs through the tool's Pydantic model BEFORE the underlying
service is invoked, so malformed args fail at parse time without
touching disk.

Idempotency: V1's only tool, ``set_patch_bc_type``, dispatches into
``upsert_override`` which is naturally idempotent (overwriting the
same (patch, bc_class) pair is a no-op). V61-122+ tools that are NOT
naturally idempotent will need an explicit ``idempotency_key`` field
on ``ToolDescriptor`` — out of V1 scope.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from ui.backend.services.case_solve.bc_setup_from_stl_patches import (
    BCClass,
    _read_patch_ranges,
)
from ui.backend.services.case_solve.patch_classification_store import (
    PatchClassificationIOError,
    upsert_override,
)
# DEC-V61-131 N1.1: regenerate_mesh tool no longer calls
# mesh_imported_case + case_lock from the AI dispatch path. The
# handler returns an advisory ApplyResult only; MeshPipelineError /
# CaseLockError handling was specific to that path and is removed.


# ────────── Errors ──────────


class ToolDispatchError(RuntimeError):
    """Base class for any failure during tool dispatch.

    ``failing_check`` is one of:
      * ``unknown_tool``
      * ``arg_validation_failed``
      * ``underlying_service_error`` (V108-style typed underlying error)
      * ``unexpected``

    ``inner_failing_check`` is the underlying service's typed
    ``failing_check`` when one exists (V123 R1 P2-1: e.g. ``cell_cap_exceeded``,
    ``symlink_escape``, ``gmshToFoam_failed``). The route layer surfaces
    this in the response body so the frontend ProposalCard can branch
    on it for actionable remediation messages instead of a generic
    failure.
    """

    def __init__(
        self,
        message: str,
        *,
        failing_check: str,
        inner_failing_check: str | None = None,
    ) -> None:
        super().__init__(message)
        self.failing_check = failing_check
        self.inner_failing_check = inner_failing_check


class UnknownToolError(ToolDispatchError):
    """The LLM proposed a tool name not in the registry. The route
    layer maps this to HTTP 400 with the tool name in `detail`."""

    def __init__(self, tool_name: str) -> None:
        super().__init__(
            f"unknown tool: {tool_name!r}", failing_check="unknown_tool"
        )
        self.tool_name = tool_name


class ToolArgError(ToolDispatchError):
    """The LLM-emitted args failed Pydantic validation for the named
    tool. Route layer maps to HTTP 400."""

    def __init__(self, tool_name: str, validation_errors: list[dict[str, Any]]) -> None:
        super().__init__(
            f"args validation failed for {tool_name!r}: {validation_errors}",
            failing_check="arg_validation_failed",
        )
        self.tool_name = tool_name
        self.validation_errors = validation_errors


# ────────── Tool argument schemas ──────────


class SetPatchBcTypeArgs(BaseModel):
    """Args for ``set_patch_bc_type``.

    Field shape mirrors the V61-108 PUT route's body. ``bc_class`` is
    a ``Literal`` so the BCClass enum is enforced at the schema layer
    — the LLM cannot propose values outside the V108 contract.

    Codex R1 P3: ``extra="forbid"`` — a malformed proposal that ships
    extra keys (e.g. ``{patch_name, bc_class, note}``) MUST fail
    validation, not silently drop the stray field. The registry
    boundary's job is to reject anything off-contract before
    dispatch."""

    model_config = ConfigDict(extra="forbid")

    patch_name: str = Field(..., min_length=1, max_length=128)
    bc_class: Literal[
        "velocity_inlet", "pressure_outlet", "no_slip_wall", "symmetry"
    ]


class RegenerateMeshArgs(BaseModel):
    """Args for ``regenerate_mesh`` (DEC-V61-123 + V61-124 + V61-125).

    Re-runs gmsh + gmshToFoam on the case's imported STL with the
    requested density, replacing ``polyMesh/`` in place. Density may
    be specified three ways:

    * ``mesh_mode`` — preset density (beginner ~30k cells, power ~250k).
    * ``target_cell_count`` — V124 AI-proposed specific cell count via
      cube formula; real count may diverge ±50% on non-cube geometries.
    * ``lc_override`` — V125 engineer escape hatch; supplies the gmsh
      characteristic length directly. Bypasses both presets and the
      V124 cube formula. Cell-budget hard cap still applies.

    Exactly one of the three must be set. Mutual exclusion is
    enforced by a model-level validator so a proposal carrying any
    other combination fails at the registry boundary with
    ``arg_validation_failed``.

    ``extra="forbid"`` matches V121's trust-boundary discipline — a
    proposal that ships off-contract keys MUST fail at the registry
    boundary, not silently drop them.
    """

    model_config = ConfigDict(extra="forbid")

    mesh_mode: Literal["beginner", "power"] | None = Field(
        default=None,
        description=(
            "Density preset. 'beginner' targets a few hundred thousand "
            "cells (lc ~ diagonal/30); 'power' targets ~10x finer "
            "(lc ~ diagonal/60). Both are bounded by the V61-105 "
            "cell-budget guard. Mutually exclusive with target_cell_count "
            "and lc_override."
        ),
    )
    target_cell_count: int | None = Field(
        default=None,
        ge=1_000,
        le=50_000_000,
        description=(
            "DEC-V61-124: AI-proposed specific cell count (1k-50M). The "
            "pipeline converts this to a characteristic length via a "
            "cube approximation; real cell count may differ by up to "
            "+/-50% for non-cube geometries. Bounded by V61-105 "
            "cell-budget hard cap (50M). Mutually exclusive with "
            "mesh_mode and lc_override."
        ),
    )
    lc_override: float | None = Field(
        default=None,
        gt=0,
        description=(
            "DEC-V61-125: engineer-supplied characteristic length (lc) "
            "in case-geometry units. Bypasses mesh_mode preset sizing "
            "AND target_cell_count's cube formula. The cell-budget "
            "hard cap (50M cells) still applies; engineer is "
            "responsible for picking a reasonable value. Mutually "
            "exclusive with mesh_mode and target_cell_count."
        ),
    )

    @model_validator(mode="after")
    def _exactly_one_density_axis(self) -> "RegenerateMeshArgs":
        """V124 + V125: enforce mutual exclusion across the three
        density axes. Exactly one of {mesh_mode, target_cell_count,
        lc_override} must be set; any other count fails validation
        with a clear message."""
        set_count = sum(
            1
            for value in (
                self.mesh_mode,
                self.target_cell_count,
                self.lc_override,
            )
            if value is not None
        )
        if set_count != 1:
            raise ValueError(
                "exactly one of mesh_mode / target_cell_count / "
                f"lc_override must be set (got {set_count})"
            )
        return self


# ────────── ApplyResult shape ──────────


@dataclass(frozen=True)
class ApplyResult:
    """Returned by ``dispatch`` on success. The route serializes this
    as the JSON response body. ``summary`` is operator-friendly text
    the UI can echo back in the chat panel after Accept."""

    tool: str
    summary: str
    state_after: dict[str, Any]


# ────────── Tool descriptor ──────────


# Each tool is implemented as a (args_model, handler) pair. The
# handler receives validated args + the case_dir path and returns
# an ApplyResult. Handlers may raise PatchClassificationIOError-shaped
# typed errors which dispatch translates to ToolDispatchError.
_ToolHandler = Callable[[Path, BaseModel], ApplyResult]


@dataclass(frozen=True)
class ToolDescriptor:
    name: str
    args_model: type[BaseModel]
    handler: _ToolHandler
    description: str  # surfaced in the system prompt's tool list


def _handle_set_patch_bc_type(case_dir: Path, args: BaseModel) -> ApplyResult:
    typed = args  # type: SetPatchBcTypeArgs (caller already validated)
    assert isinstance(typed, SetPatchBcTypeArgs)
    bc_class_enum = BCClass(typed.bc_class)
    # Codex base-review P2: gate proposals against the live polyMesh
    # boundary the same way the manual PUT route does (see
    # routes/case_patch_classification.py:_read_available_patches).
    # Without this, a stale or hallucinated patch_name still returns
    # 200 and writes an override that can never match a real patch.
    boundary = case_dir / "constant" / "polyMesh" / "boundary"
    if boundary.is_file():
        try:
            available = [name for name, _s, _n in _read_patch_ranges(boundary)]
        except Exception:  # noqa: BLE001 — defensive over a stable surface
            available = []
        if available and typed.patch_name not in available:
            raise ToolDispatchError(
                f"patch_name {typed.patch_name!r} is not present in the "
                f"current polyMesh boundary (available: {available!r}).",
                failing_check="underlying_service_error",
                inner_failing_check="patch_not_in_mesh",
            )
    state_after = upsert_override(
        case_dir, patch_name=typed.patch_name, bc_class=bc_class_enum
    )
    return ApplyResult(
        tool="set_patch_bc_type",
        summary=(
            f"Set patch '{typed.patch_name}' BC class to "
            f"'{typed.bc_class}'."
        ),
        state_after={
            "overrides": {name: cls.value for name, cls in state_after.items()},
        },
    )


def _handle_regenerate_mesh(case_dir: Path, args: BaseModel) -> ApplyResult:
    """DEC-V61-131 N1.1: advisory-only handler.

    The pre-N1.1 implementation called ``mesh_imported_case`` under
    ``case_lock`` to rewrite ``polyMesh/`` in place. Per V130 Principle
    B, the AI dispatch path no longer mutates the case. The handler
    now returns an ApplyResult describing the suggested density —
    the engineer applies it by going to Step 2 and clicking the
    engineer-driven [AI 处理] button (a human-driven
    ``api.meshImported`` call), which remains the only mesh mutation
    surface.

    The pre-lock ``os.path.lexists`` check is preserved purely as a
    sanity guard so the surfaced summary doesn't claim suggestions
    for a case that no longer exists; no lock is acquired.
    """
    typed = args  # type: RegenerateMeshArgs (caller already validated)
    assert isinstance(typed, RegenerateMeshArgs)
    if not os.path.lexists(case_dir):
        raise ToolDispatchError(
            f"case_dir {case_dir} no longer exists",
            failing_check="underlying_service_error",
            inner_failing_check="case_disappeared",
        )
    if typed.target_cell_count is not None:
        density_label = f"target ~{typed.target_cell_count:,} cells"
        suggestion = {
            "axis": "target_cell_count",
            "target_cell_count": typed.target_cell_count,
        }
    elif typed.lc_override is not None:
        density_label = f"lc={typed.lc_override:.4g}"
        suggestion = {
            "axis": "lc_override",
            "lc_override": typed.lc_override,
        }
    else:
        density_label = f"'{typed.mesh_mode}' mode"
        suggestion = {
            "axis": "mesh_mode",
            "mesh_mode": typed.mesh_mode,
        }
    summary = (
        f"AI suggests regenerating the mesh ({density_label}). "
        f"To apply: re-run Step 2 [AI 处理] with this density. "
        f"(N1.1 / V130: AI does not auto-apply mesh changes.)"
    )
    return ApplyResult(
        tool="regenerate_mesh",
        summary=summary,
        state_after={
            "advisory": True,
            "suggestion": suggestion,
        },
    )


_TOOL_REGISTRY: dict[str, ToolDescriptor] = {
    "set_patch_bc_type": ToolDescriptor(
        name="set_patch_bc_type",
        args_model=SetPatchBcTypeArgs,
        handler=_handle_set_patch_bc_type,
        description=(
            "Set or replace the BC classification for a single named patch "
            "in the case. Maps to DEC-V61-108's per-patch override store. "
            "args: patch_name (str, required), bc_class (one of "
            "velocity_inlet | pressure_outlet | no_slip_wall | symmetry)."
        ),
    ),
    "regenerate_mesh": ToolDescriptor(
        name="regenerate_mesh",
        args_model=RegenerateMeshArgs,
        handler=_handle_regenerate_mesh,
        description=(
            "Re-run gmsh + gmshToFoam on the case's imported STL to "
            "produce a fresh polyMesh with the requested density. Use "
            "after the mesh-quality snapshot reports cell_count_low or "
            "when the engineer asks to refine. args: EXACTLY ONE of "
            "mesh_mode (one of beginner | power) OR target_cell_count "
            "(integer between 1000 and 50000000 — DEC-V61-124 lets the "
            "AI propose a specific cell count instead of a preset) OR "
            "lc_override (positive float, gmsh characteristic length in "
            "geometry units — DEC-V61-125 engineer escape hatch when "
            "the cube formula diverges too much; cell-budget cap still "
            "applies)."
        ),
    ),
}


# ────────── Public API ──────────


def list_tools() -> list[ToolDescriptor]:
    """Return all registered tools. Used by the system prompt composer
    to enumerate what the LLM may propose."""
    return list(_TOOL_REGISTRY.values())


def dispatch(case_dir: Path, tool: str, args: dict[str, Any]) -> ApplyResult:
    """Validate `args` against the named tool's schema and invoke its
    handler. Raises:
      * UnknownToolError — tool not in registry
      * ToolArgError — args fail Pydantic validation
      * ToolDispatchError(failing_check="underlying_service_error") —
        typed error from the underlying V108 service
      * ToolDispatchError(failing_check="unexpected") — anything else;
        rare path, log + raise so the route can return 500
    """
    descriptor = _TOOL_REGISTRY.get(tool)
    if descriptor is None:
        raise UnknownToolError(tool)
    try:
        validated = descriptor.args_model(**args)
    except ValidationError as exc:
        raise ToolArgError(tool, exc.errors()) from exc
    try:
        return descriptor.handler(case_dir, validated)
    except ToolDispatchError:
        # Handlers may legitimately raise ToolDispatchError themselves
        # (e.g. V123 P3 case_disappeared pre-check). Pass through so the
        # blanket Exception handler below doesn't reclassify them as
        # ``unexpected``.
        raise
    except PatchClassificationIOError as exc:
        raise ToolDispatchError(
            f"underlying V108 service failed: {exc.failing_check}",
            failing_check="underlying_service_error",
            inner_failing_check=exc.failing_check,
        ) from exc
    # DEC-V61-131 N1.1: MeshPipelineError / CaseLockError handlers
    # removed with regenerate_mesh strip; the only remaining handler
    # path is _handle_set_patch_bc_type → upsert_override (which
    # raises PatchClassificationIOError, handled above).
    except Exception as exc:  # noqa: BLE001 — we want to surface as typed
        raise ToolDispatchError(
            f"unexpected dispatch failure for {tool!r}: {type(exc).__name__}",
            failing_check="unexpected",
        ) from exc
