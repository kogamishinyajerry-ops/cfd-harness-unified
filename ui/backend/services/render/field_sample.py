"""OpenFOAM scalar field → binary float32 stream (Tier-A fallback).

M-RENDER-API Tier-A B.3 (DEC-V61-095 spec_v2 §B.3). Reads a scalar
volScalarField from an OpenFOAM time-directory and returns the
``internalField`` values as a packed float32 binary blob.

Per spec_v2 §B.3, Tier-A ships the **binary stream fallback** rather
than the full glTF-accessor-with-COLOR_0 path — the latter is harder
to assemble in our hand-built glTF builder and the frontend can do
colormap mapping on a raw float32 array just as well. M-VIZ.results
upgrades to baked glTF colors.

Source resolution:
    <imported_case_dir>/{run_id}/{name}        (M5.1 OpenFOAM time-dir)

(The Round-1 review flagged a `reports/phase5_fields/` fallback as
dead code — that artifact tree stores `{case_id}/{timestamp}/VTK/...`,
not raw `{run_id}/{name}` text fields, so it could never resolve a
real archived run. Removed in Round-2.)

Tier-A scope:
    - Scalar fields only (volScalarField · internalField)
    - nonuniform List<scalar> only (uniform-field handling deferred)
    - No boundary fields (Tier-A internalField only)

Cache layout:
    <imported_case_dir>/.render_cache/field-{run_id}-{name}.bin
"""
from __future__ import annotations

import os
import re
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np

from ui.backend.services.case_drafts import is_safe_case_id
from ui.backend.services.case_scaffold import template_clone


CacheStatus = Literal["hit", "miss", "rebuild"]

# Match: ``internalField nonuniform List<scalar> <count>(<numbers>)``
# with arbitrary whitespace + an optional newline before the count.
# We tolerate ``List<scalar>`` and ``List<float>`` (some emitters use float).
_INTERNAL_NONUNIFORM_RE = re.compile(
    r"internalField\s+nonuniform\s+List<\s*(?:scalar|float|double)\s*>\s*"
    r"(\d+)\s*\(\s*([^)]*?)\s*\)\s*;",
    re.DOTALL,
)


@dataclass(frozen=True, slots=True)
class FieldSampleResult:
    cache_path: Path
    point_count: int
    status: CacheStatus


@dataclass(frozen=True, slots=True)
class FieldSampleError(Exception):
    failing_check: Literal[
        "case_not_found",
        "run_not_found",
        "field_not_found",
        "field_unsupported",
        "field_parse_error",
    ]
    message: str

    def __str__(self) -> str:
        return f"{self.failing_check}: {self.message}"


def _imported_case_dir(case_id: str) -> Path:
    return template_clone.IMPORTED_DIR / case_id


def _safe_field_segment(name: str, kind: str) -> None:
    """Path-traversal guard for run_id and field name segments.

    is_safe_case_id is too narrow (no dot allowed) for OpenFOAM run_ids
    that often carry timestamps with dots (e.g. ``run_2026-04-28T10.30``).
    Mirror run_ids._SEGMENT_RE which allows `[A-Za-z0-9_-]` after a
    leading alphanumeric.
    """
    if not name or name in (".", ".."):
        raise FieldSampleError(
            failing_check="run_not_found" if kind == "run_id" else "field_not_found",
            message=f"invalid {kind}: empty or '.'/'..'",
        )
    if "/" in name or "\\" in name or ".." in name:
        raise FieldSampleError(
            failing_check="run_not_found" if kind == "run_id" else "field_not_found",
            message=f"invalid {kind}: contains separator or '..'",
        )
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9_\-]*$", name):
        raise FieldSampleError(
            failing_check="run_not_found" if kind == "run_id" else "field_not_found",
            message=f"invalid {kind}: must match [A-Za-z0-9][A-Za-z0-9_-]*",
        )


def _resolve_field_path(case_id: str, run_id: str, name: str) -> Path:
    """Return the on-disk OpenFOAM scalar-field file for the case+run+name.

    Raises FieldSampleError with case_not_found / run_not_found /
    field_not_found per which level the resolution failed at.
    """
    if not is_safe_case_id(case_id):
        raise FieldSampleError(
            failing_check="case_not_found",
            message=f"unsafe case_id: {case_id!r}",
        )
    case_dir = _imported_case_dir(case_id)
    if not case_dir.is_dir():
        raise FieldSampleError(
            failing_check="case_not_found",
            message=f"imported case dir missing: {case_dir}",
        )

    _safe_field_segment(run_id, "run_id")
    _safe_field_segment(name, "field_name")

    run_dir = case_dir / run_id
    if not run_dir.is_dir():
        raise FieldSampleError(
            failing_check="run_not_found",
            message=f"no run dir for {run_id!r} under {case_id!r}",
        )
    candidate = run_dir / name
    if not candidate.is_file():
        raise FieldSampleError(
            failing_check="field_not_found",
            message=f"field {name!r} not found in run {run_id!r} of case {case_id!r}",
        )

    # Round-2 Finding 1: containment guard against symlink escape.
    # is_safe_case_id + segment validators stop literal traversal in URL
    # path segments, but a symlink under <case_dir>/<run_id>/<name>
    # pointing outside IMPORTED_DIR would still let us read+transcode an
    # arbitrary file. Resolve strictly and assert the resolved path stays
    # under the case dir's resolved root.
    try:
        resolved = candidate.resolve(strict=True)
        case_root = case_dir.resolve(strict=True)
        resolved.relative_to(case_root)
    except (FileNotFoundError, OSError, ValueError):
        raise FieldSampleError(
            failing_check="field_not_found",
            message=(
                f"field {name!r} resolution escaped case dir for "
                f"run {run_id!r} of case {case_id!r}"
            ),
        )
    return resolved


def _parse_internal_scalar_field(field_path: Path) -> np.ndarray:
    """Return the internalField scalar values as a float32 numpy array.

    Tier-A: nonuniform List<scalar> only. Uniform-field (one value
    replicated across all cells) handling is deferred to M-VIZ.results.
    """
    try:
        text = field_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise FieldSampleError(
            failing_check="field_parse_error",
            message=f"could not read {field_path.name}: {exc!r}",
        )

    m = _INTERNAL_NONUNIFORM_RE.search(text)
    if not m:
        # Detect uniform fields explicitly so we can return a clearer
        # 422 (unsupported) instead of a generic parse error.
        if re.search(r"internalField\s+uniform\s+", text):
            raise FieldSampleError(
                failing_check="field_unsupported",
                message="uniform internalField not supported in Tier-A",
            )
        raise FieldSampleError(
            failing_check="field_parse_error",
            message=f"no nonuniform List<scalar> internalField in {field_path.name}",
        )

    declared_count = int(m.group(1))
    body = m.group(2)
    try:
        values = np.fromstring(body, sep=" ", dtype=np.float32)
    except Exception as exc:
        raise FieldSampleError(
            failing_check="field_parse_error",
            message=f"could not parse field values: {exc!r}",
        )
    if values.size != declared_count:
        raise FieldSampleError(
            failing_check="field_parse_error",
            message=(
                f"declared count {declared_count} != parsed length {values.size} "
                f"in {field_path.name}"
            ),
        )
    return values


def _cache_target(case_dir: Path, run_id: str, name: str) -> Path:
    return case_dir / ".render_cache" / f"field-{run_id}-{name}.bin"


def _is_cache_fresh(cache: Path, source: Path) -> bool:
    if not cache.exists():
        return False
    try:
        return cache.stat().st_mtime >= source.stat().st_mtime
    except FileNotFoundError:
        return False


def _atomic_write(target: Path, payload: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(
        f".tmp.{secrets.token_hex(4)}{target.suffix}"
    )
    tmp.write_bytes(payload)
    os.replace(tmp, target)


def build_field_payload(case_id: str, run_id: str, name: str) -> FieldSampleResult:
    """Public entrypoint — return the cached float32 binary for the field.

    Raises FieldSampleError on any failure path the route maps to 4xx.
    """
    field_path = _resolve_field_path(case_id, run_id, name)
    case_dir = _imported_case_dir(case_id)
    cache = _cache_target(case_dir, run_id, name)

    if _is_cache_fresh(cache, field_path):
        # Cache hit — read the cached array's length to populate the result.
        # The frontend uses Content-Length header for the same info, but the
        # service returns it for tests / logging.
        n = cache.stat().st_size // 4
        return FieldSampleResult(cache_path=cache, point_count=n, status="hit")

    # Round-2 Finding 3 (closed in Round-3): snapshot source mtime
    # before parsing, after parsing, AND after os.replace. The post-
    # parse check stops a stale-body / fresh-cache race; the post-
    # replace check stops the residual window where the source mutates
    # between our post-parse stat and the atomic rename — without this
    # the cache mtime can outrace the source mtime forever, freezing
    # stale bytes (Codex Round-2 PARTIAL note). On detected mutation
    # we delete the just-written cache so the next request rebuilds.
    src_mtime_before = field_path.stat().st_mtime_ns
    values = _parse_internal_scalar_field(field_path)
    src_mtime_after_parse = field_path.stat().st_mtime_ns
    if src_mtime_after_parse != src_mtime_before:
        raise FieldSampleError(
            failing_check="field_parse_error",
            message=(
                f"source {field_path.name} mutated during rebuild "
                "(retry the request)"
            ),
        )
    payload = values.astype(np.float32, copy=False).tobytes()
    status: CacheStatus = "rebuild" if cache.exists() else "miss"
    _atomic_write(cache, payload)
    src_mtime_after_replace = field_path.stat().st_mtime_ns
    if src_mtime_after_replace != src_mtime_before:
        try:
            cache.unlink()
        except OSError:
            pass
        raise FieldSampleError(
            failing_check="field_parse_error",
            message=(
                f"source {field_path.name} mutated during atomic write "
                "(retry the request)"
            ),
        )
    return FieldSampleResult(
        cache_path=cache,
        point_count=int(values.size),
        status=status,
    )
