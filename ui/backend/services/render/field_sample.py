"""OpenFOAM scalar field → binary float32 stream (Tier-A fallback).

M-RENDER-API Tier-A B.3 (DEC-V61-095 spec_v2 §B.3). Reads a scalar
volScalarField from an OpenFOAM time-directory and returns the
``internalField`` values as a packed float32 binary blob.

Per spec_v2 §B.3, Tier-A ships the **binary stream fallback** rather
than the full glTF-accessor-with-COLOR_0 path — the latter is harder
to assemble in our hand-built glTF builder and the frontend can do
colormap mapping on a raw float32 array just as well. M-VIZ.results
upgrades to baked glTF colors.

Source resolution order:
    1. <imported_case_dir>/{run_id}/{name}        (M5.1 OpenFOAM time-dir)
    2. reports/phase5_fields/{case_id}/{run_id}/{name}   (Phase-7a fallback)

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
from ui.backend.services.validation_report import REPO_ROOT


CacheStatus = Literal["hit", "miss", "rebuild"]

_PHASE5_FIELDS_ROOT = REPO_ROOT / "reports" / "phase5_fields"

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

    candidates = [
        case_dir / run_id / name,
        _PHASE5_FIELDS_ROOT / case_id / run_id / name,
    ]
    for c in candidates:
        if c.is_file():
            return c

    # Differentiate run_not_found vs field_not_found for nicer 4xx mapping.
    primary_run_dir = case_dir / run_id
    fallback_run_dir = _PHASE5_FIELDS_ROOT / case_id / run_id
    if not primary_run_dir.is_dir() and not fallback_run_dir.is_dir():
        raise FieldSampleError(
            failing_check="run_not_found",
            message=f"no run dir for {run_id!r} under {case_id!r}",
        )
    raise FieldSampleError(
        failing_check="field_not_found",
        message=f"field {name!r} not found in run {run_id!r} of case {case_id!r}",
    )


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

    values = _parse_internal_scalar_field(field_path)
    payload = values.astype(np.float32, copy=False).tobytes()
    status: CacheStatus = "rebuild" if cache.exists() else "miss"
    _atomic_write(cache, payload)
    return FieldSampleResult(
        cache_path=cache,
        point_count=int(values.size),
        status=status,
    )
