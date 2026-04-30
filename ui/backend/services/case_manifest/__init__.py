"""DEC-V61-102 · case_manifest module.

Single source of truth for case state across the workbench. See
``schema.py`` for the v2 model, ``io.py`` for read/write/migrate, and
``overrides.py`` for the AI/user override marking helpers.
"""
from .io import (
    MANIFEST_FILENAME,
    ManifestNotFoundError,
    ManifestParseError,
    compute_etag,
    read_case_manifest,
    write_case_manifest,
)
from .locking import case_lock
from .overrides import (
    is_user_override,
    mark_ai_authored,
    mark_user_override,
    reset_to_ai_default,
)
from .schema import (
    BCPatch,
    BCSection,
    CaseManifest,
    HistoryEntry,
    NumericsSection,
    OverridesSection,
    PhysicsSection,
    RawDictOverride,
)

__all__ = [
    "MANIFEST_FILENAME",
    "ManifestNotFoundError",
    "ManifestParseError",
    "compute_etag",
    "read_case_manifest",
    "write_case_manifest",
    "case_lock",
    "is_user_override",
    "mark_ai_authored",
    "mark_user_override",
    "reset_to_ai_default",
    "BCPatch",
    "BCSection",
    "CaseManifest",
    "HistoryEntry",
    "NumericsSection",
    "OverridesSection",
    "PhysicsSection",
    "RawDictOverride",
]
