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

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ui.backend.services.case_solve.bc_setup_from_stl_patches import BCClass
from ui.backend.services.case_solve.patch_classification_store import (
    PatchClassificationIOError,
    upsert_override,
)


# ────────── Errors ──────────


class ToolDispatchError(RuntimeError):
    """Base class for any failure during tool dispatch.

    ``failing_check`` is one of:
      * ``unknown_tool``
      * ``arg_validation_failed``
      * ``underlying_service_error`` (V108-style typed underlying error)
      * ``unexpected``
    """

    def __init__(self, message: str, *, failing_check: str) -> None:
        super().__init__(message)
        self.failing_check = failing_check


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
    except PatchClassificationIOError as exc:
        raise ToolDispatchError(
            f"underlying V108 service failed: {exc.failing_check}",
            failing_check="underlying_service_error",
        ) from exc
    except Exception as exc:  # noqa: BLE001 — we want to surface as typed
        raise ToolDispatchError(
            f"unexpected dispatch failure for {tool!r}: {type(exc).__name__}",
            failing_check="unexpected",
        ) from exc
