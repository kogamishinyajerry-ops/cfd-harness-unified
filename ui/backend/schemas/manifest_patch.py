"""DEC-V61-202-SUB-M30-CYCLE2 · field-path manifest PATCH request/response.

A workbench rail CTA produces one of these; the route applies the
write atomically with optimistic state_sha concurrency.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# JSON-Pointer-ish path: dot-separated, no leading slash. Validated by
# the service to reject unsafe traversals (`__` / blank segments).
FieldPath = str

# What kinds of writes the engineer is making. Just metadata for now;
# the service treats them uniformly. Future cycles can specialize
# (e.g. "patch_rename" needs to update polyMesh too).
PatchOp = Literal["set", "unset"]


class ManifestPatchRequest(BaseModel):
    """One field-path write against the case's manifest."""

    field_path: FieldPath = Field(
        ...,
        min_length=1,
        max_length=200,
        description=(
            "Dot-separated path rooted at the manifest dict. Examples: "
            "'vof_contract.phases', 'bc_contract.inlet.velocity.type', "
            "'mesh_contract.y_plus_target.max'."
        ),
    )
    value: Any = Field(
        default=None,
        description=(
            "New value to write at field_path. May be a scalar (str / "
            "int / float / bool) or a structured value (list / dict). "
            "Ignored when op='unset'."
        ),
    )
    op: PatchOp = Field(
        default="set",
        description=(
            "set = write value at path (creating intermediate dicts as "
            "needed). unset = delete the key at path (leaves parent "
            "intact)."
        ),
    )
    expected_state_sha: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description=(
            "SHA-256 hex digest the frontend captured from the most "
            "recent WorkbenchFrame. The route rejects with 409 if the "
            "current state_sha differs — optimistic concurrency control."
        ),
    )


class ManifestPatchResponse(BaseModel):
    """Result of applying a field-path PATCH."""

    success: bool
    applied_path: str = Field(
        ...,
        description=(
            "The normalized field_path actually written. Empty string "
            "when success=False."
        ),
    )
    new_state_sha: str = Field(
        ...,
        description=(
            "Frame state_sha after the write. Frontend should use this "
            "as the next expected_state_sha. Equals previous state_sha "
            "when success=False (no write happened)."
        ),
    )
    case_kind: Literal["imported_user", "draft", "whitelist", "whitelist_forked"] = Field(
        ...,
        description=(
            "Where the manifest now lives. `whitelist_forked` means the "
            "engineer's PATCH on a catalog case auto-created a draft "
            "(user_drafts/{case_id}.yaml); subsequent PATCHes hit that."
        ),
    )
    validation_errors: list[str] = Field(
        default_factory=list,
        description=(
            "Non-empty when the patched manifest fails case_manifest.schema.json. "
            "Engineer-readable strings (e.g. 'vof_contract.phases: must be "
            "an array of at least 2 strings')."
        ),
    )
