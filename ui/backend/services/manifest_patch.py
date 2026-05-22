"""DEC-V61-202-SUB-M30-CYCLE2 · apply a field-path PATCH to a manifest.

The route handler is thin; this service does the load → resolve →
parse-path → apply → validate → write → recompute-sha pipeline. Pure
of FastAPI concerns to keep it unit-testable.

Whitelist forking: catalog cases (in knowledge/whitelist.yaml) get an
auto-created `user_drafts/{case_id}.yaml` on first PATCH. Subsequent
PATCHes hit that draft, not the immutable catalog.
"""
from __future__ import annotations

import fcntl
import json
import re
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft7Validator

from ui.backend.schemas.manifest_patch import (
    ManifestPatchRequest,
    ManifestPatchResponse,
)
from ui.backend.services.case_completeness import CaseNotFoundError
from ui.backend.services.case_drafts import DRAFTS_DIR
from ui.backend.services.case_scaffold.template_clone import IMPORTED_DIR
from ui.backend.services.validation_report import _load_whitelist
from ui.backend.services.workbench_decide import _manifest_state_sha


class PatchPathError(ValueError):
    """Raised when a field_path is malformed or unsafe."""


class PatchConflict(Exception):
    """Raised when expected_state_sha doesn't match current state_sha.

    The route translates this to HTTP 409.
    """

    def __init__(self, current_state_sha: str):
        super().__init__("state_sha mismatch — case has changed since frame was issued")
        self.current_state_sha = current_state_sha


_PATH_SEGMENT_RE = re.compile(r"^[a-zA-Z0-9_]+$")
_FORBIDDEN = ("__", "..", "//")


def apply_field_path_patch(
    case_id: str, request: ManifestPatchRequest
) -> ManifestPatchResponse:
    """End-to-end manifest mutation. Returns response or raises.

    Order matters: validate field_path FIRST (cheap, catches probes
    before any I/O). Then take a per-case lock. Then resolve the case.
    Then check state_sha. Then write — all inside the lock so the
    check + write pair is atomic (Codex R0 P1-1 fix).
    """

    # Path validation (cheap; rejects __class__ probes etc. before disk I/O)
    segments = _parse_field_path(request.field_path)

    # Codex R0 P1-1 (race condition fix): everything below — load,
    # SHA-check, write — happens under a per-case fcntl lock. Two
    # concurrent PATCHes for the same case_id serialize; the second
    # observes the first's write and gets a 409 on its state_sha check.
    with _case_lock(case_id):
        manifest, case_kind, storage_path = _load_for_write(case_id)
        if manifest is None:
            raise CaseNotFoundError(f"case_id not found: {case_id}")

        # Optimistic concurrency: compute current state_sha BEFORE
        # applying the patch, compare to engineer's expected_state_sha.
        current_sha = _manifest_state_sha(case_id, manifest)
        if current_sha != request.expected_state_sha:
            raise PatchConflict(current_state_sha=current_sha)

        # Whitelist-fork: write goes to user_drafts/{case_id}.yaml even
        # though we loaded from the catalog.
        if case_kind == "whitelist":
            storage_path = DRAFTS_DIR / f"{case_id}.yaml"
            DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
            case_kind_after = "whitelist_forked"
        else:
            case_kind_after = case_kind

        # Apply the patch (operates on a copy so we don't half-mutate on
        # validation failure).
        patched = _deepcopy_dict(manifest)
        if request.op == "set":
            _write_at_path(patched, segments, request.value)
        elif request.op == "unset":
            _unset_at_path(patched, segments)

        # Codex R0 P1-2 (schema applicability fix): the case_manifest
        # schema describes the imported_user v2 manifest shape. Whitelist
        # and flat-draft shapes are different (e.g. `parameters: {Re: ...}`
        # vs imported's nested `physics:`). Validating non-imported cases
        # against the wrong schema would (a) accept structural breakage
        # like `parameters: "oops"` and (b) reject many fields that are
        # legitimately absent. Skip schema validation for non-imported
        # cases — frame's completeness path is the right authority.
        errors: list[str] = []
        if request.op == "set" and case_kind == "imported_user":
            errors = _validate_at_or_below_path(patched, segments)
        if errors:
            return ManifestPatchResponse(
                success=False,
                applied_path="",
                new_state_sha=current_sha,
                case_kind=case_kind_after if case_kind != "whitelist" else "whitelist",
                validation_errors=errors,
            )

        # Persist
        _write_yaml(storage_path, patched)

        # Recompute SHA. We re-derive against the new manifest dict so
        # frontend's next PATCH sends the right expected_state_sha.
        new_sha = _manifest_state_sha(case_id, patched)

        return ManifestPatchResponse(
            success=True,
            applied_path=".".join(segments),
            new_state_sha=new_sha,
            case_kind=case_kind_after,
            validation_errors=[],
        )


# ────────────────────────── per-case lock ──────────────────────────


_LOCK_DIR = Path("/tmp/cfd-harness-manifest-patch-locks")


@contextmanager
def _case_lock(case_id: str):
    """fcntl-based exclusive lock on a sidecar lockfile.

    Why a sidecar (not the YAML itself):
        - YAML write may rename / replace the file (yaml.safe_dump +
          Path.write_text); locks on inode-replaced files release
          silently. A sidecar that never moves keeps the lock stable.
        - Avoids permission interactions with the YAML's mode bits.

    Why fcntl (not threading.Lock):
        - Works across multi-worker uvicorn deployments (when we get
          there); threading.Lock is single-process only.
        - Acquired blockingly — concurrent PATCHes for the same case_id
          serialize naturally; the second observes the first's write +
          gets a 409 on its state_sha check.

    Slug case_id to a safe filename (allow only [a-zA-Z0-9_-]+).
    """
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", case_id)
    _LOCK_DIR.mkdir(parents=True, exist_ok=True)
    lock_path = _LOCK_DIR / f"{safe}.lock"
    with open(lock_path, "w") as lock_fh:
        try:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            try:
                fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass


# ────────────────────────── load / save ──────────────────────────


def _load_for_write(
    case_id: str,
) -> tuple[dict | None, str | None, Path | None]:
    """Resolve case → (manifest_dict, case_kind, write_path).

    case_kind values:
        - "imported_user" — manifest at user_drafts/imported/{id}/case_manifest.yaml
        - "draft" — flat YAML at user_drafts/{id}.yaml
        - "whitelist" — catalog entry; writes will fork to draft
        - None — case not found
    """
    imported = IMPORTED_DIR / case_id / "case_manifest.yaml"
    if imported.is_file():
        return _read_yaml(imported), "imported_user", imported

    draft = DRAFTS_DIR / f"{case_id}.yaml"
    if draft.is_file():
        return _read_yaml(draft), "draft", draft

    whitelist = _load_whitelist()
    if case_id in whitelist:
        return whitelist[case_id], "whitelist", None

    return None, None, None


def _read_yaml(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
        loaded = yaml.safe_load(text)
        return loaded if isinstance(loaded, dict) else {}
    except (OSError, yaml.YAMLError):
        return {}


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))


# ────────────────────────── path parsing ──────────────────────────


def _parse_field_path(field_path: str) -> list[str]:
    """Validate + split a dot-separated path.

    Rejects:
        - empty / whitespace-only paths
        - paths containing `__` (dunders / sandbox-escape probes)
        - paths with `..` (path traversal)
        - paths with `//` (URL-encoded probes)
        - segments that aren't [a-zA-Z0-9_]+
    """
    if not field_path or not field_path.strip():
        raise PatchPathError("field_path is empty")
    if any(token in field_path for token in _FORBIDDEN):
        raise PatchPathError(
            f"field_path contains forbidden substring (one of {_FORBIDDEN}): {field_path}"
        )
    segments = field_path.split(".")
    for seg in segments:
        if not seg:
            raise PatchPathError(f"field_path has empty segment: {field_path}")
        if not _PATH_SEGMENT_RE.match(seg):
            raise PatchPathError(
                f"field_path segment {seg!r} contains invalid characters; "
                "only [a-zA-Z0-9_] allowed"
            )
    return segments


def _write_at_path(obj: dict, segments: list[str], value: Any) -> None:
    """Mutate `obj` in place: set value at the leaf addressed by segments.

    Intermediate dicts are auto-created. If an intermediate is a non-
    dict (e.g. a list or scalar), raises PatchPathError to avoid
    silently clobbering structured data.
    """
    if not segments:
        raise PatchPathError("cannot write at empty path")
    cur = obj
    for seg in segments[:-1]:
        if seg not in cur:
            cur[seg] = {}
        if not isinstance(cur[seg], dict):
            raise PatchPathError(
                f"intermediate segment {seg!r} is not a dict (found {type(cur[seg]).__name__})"
            )
        cur = cur[seg]
    cur[segments[-1]] = value


def _unset_at_path(obj: dict, segments: list[str]) -> None:
    """Mutate `obj` in place: delete leaf addressed by segments.

    No-op if the path doesn't exist (idempotent).
    """
    if not segments:
        return
    cur = obj
    for seg in segments[:-1]:
        if not isinstance(cur, dict) or seg not in cur:
            return
        cur = cur[seg]
    if isinstance(cur, dict):
        cur.pop(segments[-1], None)


# ────────────────────────── schema validation ──────────────────────────


_SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / "audit"
    / "cfdtrust"
    / "schemas"
    / "case_manifest.schema.json"
)


@lru_cache(maxsize=1)
def _load_manifest_schema() -> dict:
    """Read case_manifest.schema.json from the cfdtrust audit subtree.

    Direct file read (not via cfdtrust import) so ui.backend.services
    doesn't depend on the cfdtrust package being importable as a
    top-level module — it isn't outside its own test conftest.
    """
    if not _SCHEMA_PATH.is_file():
        return {}
    try:
        return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _validate_against_schema(manifest: dict) -> list[str]:
    """Return ALL engineer-readable error strings; empty = valid.

    Exists for tests + future "Step 5 final validation" flows. PATCH
    requests use `_validate_at_or_below_path` instead (lenient).
    """
    schema = _load_manifest_schema()
    if not schema:
        return []
    validator = Draft7Validator(schema)
    out: list[str] = []
    for err in validator.iter_errors(manifest):
        loc = "/".join(str(p) for p in err.absolute_path) or "<root>"
        out.append(f"{loc}: {err.message}")
    return out


def _validate_at_or_below_path(
    manifest: dict, written_segments: list[str]
) -> list[str]:
    """Return only validation errors whose absolute_path is at or below
    the path that was just written.

    Workbench-guided UX: a partial manifest must be writable field-by-
    field. Whole-manifest validation would block every PATCH on an
    in-flight case because global `required` checks fail. Instead we
    let the engineer build the case incrementally and only fail on
    errors directly tied to the field they just changed.

    Algorithm:
        - Run full validator.iter_errors
        - For each error: build the segment path (e.g. ['vof_contract',
          'phases', 0]) and check if it starts with `written_segments`
        - Keep only matching errors
        - Always keep type-mismatch errors regardless of path (these
          mean the engineer wrote bad data, not "case incomplete")
    """
    schema = _load_manifest_schema()
    if not schema:
        return []
    validator = Draft7Validator(schema)
    out: list[str] = []
    for err in validator.iter_errors(manifest):
        abs_path = [str(p) for p in err.absolute_path]
        loc = "/".join(abs_path) or "<root>"

        # Path-match filter: keep errors whose path starts with the
        # written segments. `written_segments=['vof_contract', 'phases']`
        # matches abs_path=['vof_contract', 'phases'] or
        # abs_path=['vof_contract', 'phases', 0], but NOT
        # abs_path=['bc_contract', ...].
        #
        # Codex R0 P2 fix: type errors are also scoped — a pre-existing
        # type mismatch at `bc_contract.foo` must NOT block a PATCH at
        # `vof_contract.phases`. Only type errors at-or-below the
        # written path are surfaced.
        if _path_starts_with(abs_path, written_segments):
            out.append(f"{loc}: {err.message}")
            continue

        # Special case: the engineer wrote a path that's structurally
        # required, but they cleared it (e.g. unset). The error is a
        # `required` error at the parent saying "<our last segment>
        # is required". Surface that. Reject all OTHER required errors
        # (case incomplete is the frame's job, not PATCH's job).
        if err.validator == "required" and len(written_segments) >= 1:
            parent_path = written_segments[:-1]
            missing_prop = _required_missing_property(err)
            if abs_path == parent_path and missing_prop == written_segments[-1]:
                out.append(f"{loc}: {err.message}")

    return out


def _required_missing_property(err) -> str | None:
    """Extract the missing property name from a jsonschema `required` error.

    The message is typically `'<name>' is a required property`. We pull
    the quoted name out so we can decide whether the missing field is
    the one the engineer just (un)set.
    """
    msg = str(err.message)
    if "'" in msg:
        try:
            return msg.split("'")[1]
        except IndexError:
            return None
    return None


def _path_starts_with(abs_path: list[str], prefix: list[str]) -> bool:
    """True iff abs_path[:len(prefix)] == prefix."""
    if len(abs_path) < len(prefix):
        return False
    return abs_path[: len(prefix)] == prefix


# ────────────────────────── state_sha bridge ──────────────────────────


def manifest_only_state_sha(case_id: str) -> str | None:
    """Public helper for callers that want the manifest_state_sha
    without going through apply_field_path_patch. Returns None if the
    case isn't found.
    """
    manifest, _, _ = _load_for_write(case_id)
    if manifest is None:
        return None
    return _manifest_state_sha(case_id, manifest)


def _deepcopy_dict(d: dict) -> dict:
    """Cheap deepcopy via YAML round-trip; safer than json.dumps because
    YAML handles non-JSON types (e.g. tuples in lists). Manifest dicts
    are small (~100 fields), so the perf hit is negligible.
    """
    text = yaml.safe_dump(d)
    return yaml.safe_load(text) or {}
