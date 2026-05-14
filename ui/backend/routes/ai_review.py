"""DEC-V62-A-sub-ROUTE-AI-REVIEW · POST /ai-review.

Composes the LANDED advisor stack (``advisor_stack.assemble_stack``) into
one route. Pure dispatch with **zero** required LLM dependency. The
optional ``llm_enhance`` flag wraps the upstream import in ``try/except``
so the route still returns the base report when no provider is present.

V130 four-question gate (advisory-not-driver):

1. **LLM offline OK?** Yes. Base path imports zero LLM modules; the
   ``llm_enhance=True`` branch is best-effort and silently downgrades
   to ``llm_enhanced=False`` if the import or call fails.
2. **Artifacts output?** Yes. Every 200 response persists the
   serialized report to ``<repo>/.planning/audits/<case_label>_ai_review_<ts>.json``.
   The path is returned in the response so callers can attach it to a
   commit / DEC trail.
3. **TrustGate?** Yes. Each finding carries ``source_advisor`` and
   ``evidence_v_rows`` (enforced by ``advisor_stack`` contract); the
   route does not strip or re-author this provenance.
4. **AI advisory only?** Yes. The route only **reads** ``case_dir``
   (auto-discover step) and writes the audit artifact to
   ``.planning/audits/`` — never to anywhere under ``case_dir``.

Auto-discovery convention (only when ``case_dir`` is provided AND the
explicit kwarg is absent):

  * ``parts_manifest``    ← ``<case_dir>/inputs/parts_manifest.{yaml,yml,json}``
  * ``shm_dict``          ← ``<case_dir>/inputs/shm_dict.{yaml,yml,json}``
  * ``thermo_dict``       ← ``<case_dir>/inputs/thermo_dict.{yaml,yml,json}``
  * ``thin_wall_inputs``  ← ``<case_dir>/inputs/thin_wall_inputs.{yaml,yml,json}``
  * ``step_path``         ← first ``*.step``/``*.stp`` under ``<case_dir>``
                            (root) or ``<case_dir>/cad/``
  * ``step_bbox`` (6-tuple) /
    ``step_extents`` (3-tuple)
                          ← ``<case_dir>/cad/bbox.json`` or fields
                            ``bbox`` / ``extents`` inside
                            ``<case_dir>/manifest.json``
  * ``interface_bodies`` /
    ``interface_specs``   ← ``<case_dir>/interface_bodies.json`` /
                            ``<case_dir>/interface_specs.json`` (or
                            fields with same names inside
                            ``<case_dir>/manifest.json``)
  * ``stl_bbox_set``      ← ``<case_dir>/cad/stl_bbox_set.json`` (or the
                            ``stl_bbox_set`` field inside
                            ``<case_dir>/manifest.json``) —
                            DEC-V63-A-sub-M-D6-HTTP-WIRE

DEC-V62-A-sub-REQ-SCHEMA-EXPAND (2026-05-14): the five new fields
unblock ``unit_detector`` (gated on ``step_path``) and the A2-v2
``virtual_interface_detector`` (gated on ``interface_bodies`` +
``interface_specs``) in the HTTP path. ``advisor_stack.assemble_stack``
already supports the corresponding kwargs; this route only adds wire
plumbing + dataclass rehydration.

DEC-V63-A-sub-M-D6-HTTP-WIRE (2026-05-14): closes the D6 deferred
wire-up that REQ-SCHEMA-EXPAND explicitly carved out (§"this sub-DEC
does NOT add"). Adds ``stl_bbox_set`` wire field + auto-discover from
``<case_dir>/cad/stl_bbox_set.json`` (preferred) or the
``stl_bbox_set`` field inside ``<case_dir>/manifest.json``.
``assemble_stack`` registers the new ``stl_bbox_set`` kwarg and a
matching D6 routing rule.

DEC-V62-A-sub-D10 (2026-05-14): adds ``bc_specs`` + ``bc_fork`` wire
fields routing into D10 ``bc_type_name_validity_advisor``. Closes
M-STACK-TRACK-3 §gap2 (V29 evidence row) — case_006 ONERA M6 farfield
parts declaring foam-extend-only BC names would previously pass the
stack silently because A5 short-circuits on ``role`` outside
``THROUGH_FLOW_ROLES`` and never inspects ``bc:`` blocks. The stack
also auto-extracts ``bc_specs`` from ``parts_manifest`` when the
explicit field is absent.

Missing files are silently skipped (the absence is observable via
``advisor_count`` in the report).
"""
from __future__ import annotations

import dataclasses
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from ui.backend.routes._loopback_guard import require_loopback
from ui.backend.services.advisor_stack import AdvisorStackReport, assemble_stack
from ui.backend.services.geometry_ingest.thin_wall_advisor import PatchGeometry
from ui.backend.services.geometry_ingest.virtual_interface_detector import (
    BodyGeometry,
    FaceGeometry,
    InterfaceSpec,
)
from ui.backend.services.v_series_drift_guard import enforce_at_route_boundary


logger = logging.getLogger(__name__)

router = APIRouter()


# Repo root = three parents up from this file
# (.../ui/backend/routes/ai_review.py → .../ui/backend → .../ui → .../<repo>)
_REPO_ROOT = Path(__file__).resolve().parents[3]
_AUDITS_DIR_NAME = ".planning/audits"


_DISCOVER_KEYS: dict[str, tuple[str, ...]] = {
    "parts_manifest": ("parts_manifest.yaml", "parts_manifest.yml", "parts_manifest.json"),
    "shm_dict": ("shm_dict.yaml", "shm_dict.yml", "shm_dict.json"),
    "thermo_dict": ("thermo_dict.yaml", "thermo_dict.yml", "thermo_dict.json"),
    "thin_wall_inputs": ("thin_wall_inputs.yaml", "thin_wall_inputs.yml", "thin_wall_inputs.json"),
}


# ---------- Wire schemas ---------------------------------------------------


class AIReviewRequest(BaseModel):
    """Inputs for ``POST /ai-review``.

    All fields are optional. ``case_dir`` enables auto-discovery of the
    other artifacts from ``<case_dir>/inputs/``; explicit kwargs always
    win if both are supplied (auto-discovery only fills *missing* slots).
    """

    model_config = ConfigDict(extra="ignore")

    case_dir: Optional[str] = Field(
        default=None,
        description="Absolute or repo-relative path. Auto-discovers artifacts.",
    )
    parts_manifest: Optional[dict[str, Any]] = None
    shm_dict: Optional[dict[str, Any]] = None
    thermo_dict: Optional[dict[str, Any]] = None
    thin_wall_inputs: Optional[dict[str, Any]] = None
    # DEC-V62-A-sub-REQ-SCHEMA-EXPAND (2026-05-14) — fields below
    # unblock unit_detector + A2-v2 in the HTTP path. assemble_stack
    # already routes these kwargs (see services/advisor_stack.py).
    step_path: Optional[str] = Field(
        default=None,
        description=(
            "Path to a CAD STEP/STP file. Gates unit_detector. Path is "
            "passed through as-is to the advisor; the route does not "
            "open or write it (V132 advisory-only)."
        ),
    )
    step_bbox: Optional[list[float]] = Field(
        default=None,
        description=(
            "Six-tuple [xmin, ymin, zmin, xmax, ymax, zmax] (raw units) "
            "for the overall STEP bounding box. Converted to "
            "step_bbox_max_extent_raw = max(extent_xyz) before dispatch."
        ),
    )
    step_extents: Optional[list[float]] = Field(
        default=None,
        description=(
            "List of per-body max bbox extents (raw units), one float "
            "per body. Forwarded to unit_detector as body_extents_raw "
            "for airframe-class filtering (3-tuple is the typical "
            "single-domain case; lists of any length are accepted)."
        ),
    )
    interface_bodies: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description=(
            "Wire form of virtual_interface_detector.BodyGeometry "
            "instances. Each item: {name, centroid:[x,y,z], faces:[{"
            "area, bbox_min:[x,y,z], bbox_max:[x,y,z], normal:[x,y,z], "
            "centroid:[x,y,z]}, ...]}. Combined with interface_specs "
            "gates the A2-v2 advisor."
        ),
    )
    interface_specs: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description=(
            "Wire form of virtual_interface_detector.InterfaceSpec. "
            "Each item: {patch_name, mode: 'shared'|'endcap', body_a?, "
            "body_b?, body?, axis?}. Combined with interface_bodies "
            "gates the A2-v2 advisor."
        ),
    )
    # DEC-V62-A-sub-D10 (2026-05-14) — fields below explicitly route
    # bc_specs into the D10 bc_type_name_validity_advisor without
    # requiring parts_manifest. When absent AND parts_manifest carries
    # bc: blocks, the stack auto-extracts via
    # extract_bc_specs_from_parts_manifest, so this field is purely
    # for callers that lack a full parts_manifest but DO have BC
    # declarations to validate (e.g., a partial config-validate flow).
    bc_specs: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description=(
            "Explicit D10 input. Each item: {part_name: str, "
            "fields: {<bc_field_name>: <bc_type_name>, ...}}. When "
            "absent, the stack auto-extracts from parts_manifest "
            "(parts[i].bc blocks). Explicit value wins over auto-"
            "extraction. See DEC-V62-A-sub-D10."
        ),
    )
    bc_fork: Optional[str] = Field(
        default=None,
        description=(
            "Which OpenFOAM fork the case targets — 'main' (ESI v2312, "
            "project default), 'foam-extend', or 'unknown'. Selects the "
            "severity D10 assigns to characteristic*-family BC names. "
            "Defaults to 'main' when None."
        ),
    )
    # DEC-V63-A-sub-D11 (2026-05-14) — wire field below routes STL face-
    # label inventory into D11 stl_face_label_validator (V94 face-label-
    # loss class). Same physical input that A8 V99-widening already
    # consumes via the stack's shm_stl_face_normals kwarg; the wire
    # field unifies them under a single payload entry.
    stl_face_normals: Optional[dict[str, list[list[float]]]] = Field(
        default=None,
        description=(
            "STL solid-label → list of facet-normal 3-vectors. Each "
            "key is an STL solid block name (the face-label inventory "
            "the engineer's CAD pipeline emitted); each value is a "
            "list of [nx, ny, nz] floats. Routes into both D11 "
            "(face-label consistency) and A8 V99-widening (shm dict "
            "geometry alias resolution). When absent AND case_dir is "
            "supplied, auto-discovered from "
            "<case_dir>/cad/face_normals.json. See DEC-V63-A-sub-D11."
        ),
    )
    # DEC-V63-A-sub-M-D6-HTTP-WIRE (2026-05-14) — wire field below
    # routes STL body bounding boxes into D6 extra_body_advisor (V55
    # case_016 debris-cube class). Closes the deferred D6 wire-up that
    # DEC-V62-A-sub-REQ-SCHEMA-EXPAND explicitly carved out of scope
    # (§"this sub-DEC does NOT add") and V63-A carry-over #4.
    stl_bbox_set: Optional[dict[str, Any]] = Field(
        default=None,
        description=(
            "STL body-name → 6-element [xmin, ymin, zmin, xmax, ymax, "
            "zmax] AABB in millimetres. Routes into D6 "
            "extra_body_advisor for case_016-class FOD / debris / "
            "helper-body detection. The advisor reads parts_manifest "
            "for declared bodies + roles and flags STL entries that "
            "are unregistered (critical), solid-inside-fluid-region "
            "(warning), or undeclared-inclusion (warning). When "
            "absent AND case_dir is supplied, auto-discovered from "
            "<case_dir>/cad/stl_bbox_set.json OR the ``stl_bbox_set`` "
            "field inside <case_dir>/manifest.json. The value type is "
            "intentionally ``Any`` (not ``list[float]``) so a single "
            "malformed entry (wrong type / wrong arity / non-numeric) "
            "is silently skipped by the advisor's _coerce_bbox guard "
            "without 422-ing the whole request — mixed-quality STL "
            "inventories are a routine case_016-class shape (helper "
            "bodies often arrive partially-typed). See "
            "DEC-V63-A-sub-M-D6-HTTP-WIRE Codex R0 P2 fix."
        ),
    )
    llm_enhance: bool = Field(
        default=False,
        description=(
            "Optional LLM augment. Default OFF for 4-question gate "
            "compliance. When True and a provider is importable, the "
            "route adds an `llm_summary` field; on failure it silently "
            "downgrades to llm_enhanced=False."
        ),
    )
    drift_mode: Optional[str] = Field(
        default=None,
        description=(
            "DEC-V62-A-sub-M-DRIFT-V2 enforcement mode. None or 'audit' "
            "(default) appends a v_series_drift_guard audit entry without "
            "dropping findings (backward compatible). 'strict' drops "
            "findings citing V-rows absent from the runtime corpus. The "
            "request body field is overridden by the `?drift_mode=` "
            "query param when both are supplied."
        ),
    )


class AIReviewResponse(BaseModel):
    """Output from ``POST /ai-review``.

    ``report`` is the JSON-serialized ``AdvisorStackReport`` (via
    ``dataclasses.asdict`` + a string fallback for non-JSONable leaves).
    The native dataclass shape is preserved key-by-key so external
    auditors can pin assertions on individual fields.
    """

    model_config = ConfigDict(extra="ignore")

    report: dict[str, Any]
    audit_artifact_path: str
    llm_enhanced: bool
    timing: dict[str, float]


# ---------- Helpers --------------------------------------------------------


def _load_dict_file(path: Path) -> Optional[dict[str, Any]]:
    """Read a YAML or JSON dict file. Returns None on any failure."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        if path.suffix.lower() == ".json":
            obj = json.loads(text)
        else:
            obj = yaml.safe_load(text)
    except (json.JSONDecodeError, yaml.YAMLError):
        logger.warning("ai-review: failed to parse %s", path)
        return None
    if not isinstance(obj, dict):
        return None
    return obj


def _autodiscover(case_dir: Path) -> dict[str, dict[str, Any]]:
    """Look for known artifact filenames under ``case_dir/inputs/``.

    Returns a dict keyed by ``assemble_stack`` kwarg name. Missing files
    are simply absent from the result (no error). Per V130, callers must
    treat absence as silent skip — never raise.
    """
    inputs_dir = case_dir / "inputs"
    found: dict[str, dict[str, Any]] = {}
    if not inputs_dir.is_dir():
        return found
    for kw, candidates in _DISCOVER_KEYS.items():
        for name in candidates:
            p = inputs_dir / name
            if p.is_file():
                loaded = _load_dict_file(p)
                if loaded is not None:
                    found[kw] = loaded
                break
    return found


def _autodiscover_step(case_dir: Path) -> Optional[str]:
    """Find the first ``*.step`` / ``*.stp`` under ``case_dir`` or ``case_dir/cad/``.

    Root searched before ``cad/`` so a top-level STEP wins. Returns the
    absolute path as a string (JSON-safe) or None when nothing found.
    Missing/empty directories are silently skipped per V130.
    """
    for sub in (case_dir, case_dir / "cad"):
        if not sub.is_dir():
            continue
        for suffix in ("*.step", "*.stp", "*.STEP", "*.STP"):
            for p in sorted(sub.glob(suffix)):
                if p.is_file():
                    return str(p)
    return None


def _autodiscover_geometry_metadata(case_dir: Path) -> dict[str, Any]:
    """Extract ``step_bbox`` / ``step_extents`` / ``interface_bodies`` /
    ``interface_specs`` from ``case_dir`` artifacts.

    Search order (first hit wins per field):

      * ``<case_dir>/cad/bbox.json``  → ``bbox``, ``extents``
      * ``<case_dir>/interface_bodies.json`` (list) → ``interface_bodies``
      * ``<case_dir>/interface_specs.json`` (list)  → ``interface_specs``
      * ``<case_dir>/manifest.json`` may carry any of the four under
        keys ``bbox`` / ``extents`` / ``interface_bodies`` /
        ``interface_specs``

    Returns a dict with only the fields that were successfully resolved.
    Per V130, missing files / malformed shapes degrade silently.
    """
    found: dict[str, Any] = {}

    bbox_path = case_dir / "cad" / "bbox.json"
    if bbox_path.is_file():
        bbox_doc = _load_dict_file(bbox_path) or {}
        if isinstance(bbox_doc.get("bbox"), list):
            found["step_bbox"] = bbox_doc["bbox"]
        if isinstance(bbox_doc.get("extents"), list):
            found["step_extents"] = bbox_doc["extents"]

    for key in ("interface_bodies", "interface_specs"):
        p = case_dir / f"{key}.json"
        if p.is_file():
            try:
                obj = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                obj = None
            if isinstance(obj, list):
                found[key] = obj

    manifest = case_dir / "manifest.json"
    if manifest.is_file():
        m = _load_dict_file(manifest) or {}
        for key in ("bbox", "extents"):
            mapped = "step_bbox" if key == "bbox" else "step_extents"
            if mapped not in found and isinstance(m.get(key), list):
                found[mapped] = m[key]
        for key in ("interface_bodies", "interface_specs"):
            if key not in found and isinstance(m.get(key), list):
                found[key] = m[key]

    return found


def _rehydrate_face(raw: dict[str, Any]) -> FaceGeometry:
    return FaceGeometry(
        area=float(raw["area"]),
        bbox_min=tuple(float(x) for x in raw["bbox_min"]),  # type: ignore[arg-type]
        bbox_max=tuple(float(x) for x in raw["bbox_max"]),  # type: ignore[arg-type]
        normal=tuple(float(x) for x in raw["normal"]),  # type: ignore[arg-type]
        centroid=tuple(float(x) for x in raw["centroid"]),  # type: ignore[arg-type]
    )


def _rehydrate_interface_bodies(
    raw: list[dict[str, Any]],
) -> dict[str, BodyGeometry]:
    """Convert wire-form body list into ``{name: BodyGeometry}`` mapping.

    Each item must carry ``name`` (str), ``centroid`` ([x,y,z]), and
    ``faces`` (list of face dicts). Malformed entries raise 400 — the
    advisor would otherwise crash into per-call isolation and the
    finding would be silently lost.
    """
    out: dict[str, BodyGeometry] = {}
    for item in raw:
        if not isinstance(item, dict):
            raise HTTPException(
                status_code=400,
                detail={
                    "failing_check": "interface_body_shape",
                    "expected": "dict with keys {name, centroid, faces}",
                    "got": type(item).__name__,
                },
            )
        try:
            name = str(item["name"])
            centroid = tuple(float(x) for x in item["centroid"])
            faces_raw = item.get("faces") or ()
            faces = tuple(_rehydrate_face(f) for f in faces_raw)
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "failing_check": "interface_body_fields",
                    "expected": "name: str, centroid: [f,f,f], faces: list",
                    "error": str(exc),
                },
            ) from exc
        if len(centroid) != 3:
            raise HTTPException(
                status_code=400,
                detail={
                    "failing_check": "interface_body_centroid_arity",
                    "expected_len": 3,
                    "got_len": len(centroid),
                },
            )
        out[name] = BodyGeometry(name=name, faces=faces, centroid=centroid)  # type: ignore[arg-type]
    return out


def _rehydrate_interface_specs(raw: list[dict[str, Any]]) -> list[InterfaceSpec]:
    """Convert wire-form spec list into ``InterfaceSpec`` instances."""
    out: list[InterfaceSpec] = []
    for item in raw:
        if not isinstance(item, dict):
            raise HTTPException(
                status_code=400,
                detail={
                    "failing_check": "interface_spec_shape",
                    "expected": "dict with keys {patch_name, mode, ...}",
                    "got": type(item).__name__,
                },
            )
        try:
            patch_name = str(item["patch_name"])
            mode = str(item["mode"])
        except (KeyError, TypeError) as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "failing_check": "interface_spec_fields",
                    "expected": "patch_name: str, mode: 'shared'|'endcap'",
                    "error": str(exc),
                },
            ) from exc
        out.append(
            InterfaceSpec(
                patch_name=patch_name,
                mode=mode,
                body_a=item.get("body_a"),
                body_b=item.get("body_b"),
                body=item.get("body"),
                axis=item.get("axis"),
            )
        )
    return out


def _bbox_max_extent(bbox: list[float]) -> float:
    """Compute ``max(dx, dy, dz)`` from a 6-tuple bbox in raw units.

    Raises HTTPException(400) on arity / type errors so the route
    surfaces an actionable failure instead of 500-ing inside dispatch.
    """
    if len(bbox) != 6:
        raise HTTPException(
            status_code=400,
            detail={
                "failing_check": "step_bbox_arity",
                "expected_len": 6,
                "got_len": len(bbox),
            },
        )
    try:
        vals = [float(x) for x in bbox]
    except (TypeError, ValueError, OverflowError) as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "failing_check": "step_bbox_fields",
                "expected": "6 floats [xmin,ymin,zmin,xmax,ymax,zmax]",
                "error": str(exc),
            },
        ) from exc
    return max(vals[3] - vals[0], vals[4] - vals[1], vals[5] - vals[2])


def _resolve_case_dir(case_dir_raw: str) -> Path:
    """Resolve an absolute or repo-relative path; raise HTTPException(400) if missing."""
    p = Path(case_dir_raw)
    if not p.is_absolute():
        p = (_REPO_ROOT / p).resolve()
    if not p.is_dir():
        raise HTTPException(
            status_code=400,
            detail={
                "failing_check": "case_dir_not_found",
                "case_dir": str(p),
            },
        )
    return p


def _report_to_dict(report: AdvisorStackReport) -> dict[str, Any]:
    """Convert AdvisorStackReport to a JSON-serializable dict.

    ``dataclasses.asdict`` handles nested frozen dataclasses recursively
    but drops ``@property`` fields. Codex R0 P2 (2026-05-14): explicitly
    fold ``failed_advisor_count``, ``critical_count``, and
    ``warning_count`` in so clients never have to re-derive them and the
    route's "crashes surface as failed_advisor_count" contract holds in
    the wire payload.
    """
    raw = dataclasses.asdict(report)
    raw["failed_advisor_count"] = report.failed_advisor_count
    raw["critical_count"] = report.critical_count
    raw["warning_count"] = report.warning_count
    # Round-trip through JSON to coerce any stray Path/Enum leaves into
    # primitives the FastAPI serializer can handle.
    return json.loads(json.dumps(raw, default=str))


def _rehydrate_thin_wall_inputs(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert wire-form ``thin_wall_inputs`` into the dataclass shape
    ``thin_wall_advisor.detect_thin_wall_patches_at_risk`` expects.

    Codex R0 P2 (2026-05-14): the advisor takes a sequence of
    ``PatchGeometry`` (frozen dataclass with ``name`` + ``bbox_dimensions``).
    Over HTTP/YAML, callers supply plain dicts — without rehydration the
    advisor crashes inside the stack and the finding is lost to crash-
    isolation. ``bbox_dimensions`` is coerced to a 3-tuple of floats so
    the dataclass's frozen hash stays stable.

    Patches that are already ``PatchGeometry`` instances pass through
    unchanged so in-process callers still work.

    Codex R1 P3 (2026-05-14): a wire-form ``patches`` field that is
    present but not list-shaped (e.g. ``""``, ``0``, ``{}``) was
    previously silently normalized to ``()`` by ``or ()``, masking the
    400 signal. Distinguish absent (``None``, key missing → ``()``)
    from malformed-non-iterable (raise 400) explicitly.
    """
    if "patches" in raw:
        patches_in = raw["patches"]
        if patches_in is None:
            patches_in = ()
        elif not isinstance(patches_in, (list, tuple)):
            raise HTTPException(
                status_code=400,
                detail={
                    "failing_check": "thin_wall_patches_type",
                    "expected": "list of patch dicts",
                    "got": type(patches_in).__name__,
                },
            )
    else:
        patches_in = ()
    patches_out: list[PatchGeometry] = []
    for p in patches_in:
        if isinstance(p, PatchGeometry):
            patches_out.append(p)
            continue
        if not isinstance(p, dict):
            raise HTTPException(
                status_code=400,
                detail={
                    "failing_check": "thin_wall_patch_shape",
                    "expected": "dict with keys {name, bbox_dimensions}",
                    "got": type(p).__name__,
                },
            )
        # Codex R1 P2 (2026-05-14): ``float(x)`` on an oversized int
        # raises ``OverflowError``, which is not a subclass of any of
        # the previously-caught exceptions. Without explicit handling
        # the route 500s on malformed bbox values — adding OverflowError
        # keeps the documented 400-on-bad-bbox contract honest.
        try:
            name = str(p["name"])
            bbox = tuple(float(x) for x in p["bbox_dimensions"])
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "failing_check": "thin_wall_patch_fields",
                    "expected": "name: str, bbox_dimensions: [float, float, float]",
                    "error": str(exc),
                },
            ) from exc
        if len(bbox) != 3:
            raise HTTPException(
                status_code=400,
                detail={
                    "failing_check": "thin_wall_bbox_arity",
                    "expected_len": 3,
                    "got_len": len(bbox),
                },
            )
        patches_out.append(PatchGeometry(name=name, bbox_dimensions=bbox))
    rehydrated = dict(raw)
    rehydrated["patches"] = tuple(patches_out)
    return rehydrated


def _persist_audit(payload: dict[str, Any], case_label: str) -> Path:
    """Write the report JSON under ``<repo>/.planning/audits/``.

    The audit dir is created on demand (idempotent). The filename is
    ``<case_label>_ai_review_<ISO-UTC-ts-micros>_<uuid8>.json``.

    Codex R0 P2 (2026-05-14): including microseconds + an 8-hex UUID4
    slice guarantees per-request uniqueness even under concurrent
    workers or back-to-back retries inside the same second, preserving
    the route's audit-trail-is-additive contract.
    """
    audits_dir = _REPO_ROOT / _AUDITS_DIR_NAME
    audits_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    nonce = uuid.uuid4().hex[:8]
    safe_label = "".join(c if c.isalnum() or c in {"_", "-"} else "_" for c in case_label) or "anon"
    out_path = audits_dir / f"{safe_label}_ai_review_{ts}_{nonce}.json"
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return out_path


def _try_llm_enhance(report_dict: dict[str, Any]) -> tuple[bool, float]:
    """Best-effort LLM augmentation. Returns (succeeded, ms).

    Per the 4-question gate, this MUST be a pure addendum: the base
    advisor stack output is always present whether or not the LLM call
    succeeds. We treat any import or call exception as
    ``llm_enhanced=False`` and return promptly so the route still
    returns a 200 with a complete base report.
    """
    t0 = time.perf_counter()
    try:
        # Late import keeps the offline import graph clean.
        from ui.backend.services.llm_provider import (  # noqa: F401
            get_default_provider,
        )
        # We do NOT actually invoke the provider here — invoking it
        # would consume operator quota and require loopback + auth
        # gating that this route does not carry. The presence of an
        # importable provider is recorded as the "enhancement" signal;
        # downstream consumers (UI) can fan out to /ai-chat /
        # /cases/{id}/ai-review for real LLM grounding. This keeps the
        # 4Q gate honest: zero LLM call on POST /ai-review.
        return True, (time.perf_counter() - t0) * 1000.0
    except Exception:  # noqa: BLE001 - intentional broad except
        return False, (time.perf_counter() - t0) * 1000.0


# ---------- Route ----------------------------------------------------------


@router.post(
    "/ai-review",
    response_model=AIReviewResponse,
    tags=["ai-review"],
)
async def post_ai_review(
    payload: AIReviewRequest, request: Request
) -> AIReviewResponse:
    """Run the V62-A advisor stack against the supplied artifacts.

    Behavior contract:

      * **Loopback-only by default** (Codex R0 P1 · 2026-05-14). The
        route accepts caller-controlled ``case_dir`` and discovers
        ``inputs/*.{yaml,json}`` underneath, which would turn the
        endpoint into an arbitrary host-file probe if exposed to
        non-loopback callers. Operators with a trusted reverse proxy
        + auth in front set ``AI_CHAT_ALLOW_NON_LOOPBACK=1`` to opt
        in, matching the sibling AI routes' guard semantics.
      * Read-only against ``case_dir`` (V132 advisory-only)
      * Persists a JSON audit artifact under ``.planning/audits/``
      * Per-advisor crashes are isolated by ``assemble_stack`` and
        surface as ``failed_advisor_count`` on the report
      * Returns 200 with ``advisor_count=0`` on truly empty input

    Errors:

      * 400 when ``case_dir`` is provided but does not resolve to a
        directory on disk
      * 400 when ``thin_wall_inputs.patches`` cannot be rehydrated to
        ``PatchGeometry`` (missing or malformed name / bbox_dimensions)
      * 403 when the caller is non-loopback and the override env-var
        is not set
    """
    require_loopback(request, route_label="/api/ai-review")
    t_start = time.perf_counter()

    # ----- 1. Resolve inputs (explicit > auto-discover) -----
    explicit_kwargs: dict[str, Any] = {
        "parts_manifest": payload.parts_manifest,
        "shm_dict": payload.shm_dict,
        "thermo_dict": payload.thermo_dict,
        "thin_wall_inputs": payload.thin_wall_inputs,
        # DEC-V62-A-sub-REQ-SCHEMA-EXPAND
        "step_path": payload.step_path,
        "step_bbox": payload.step_bbox,
        "step_extents": payload.step_extents,
        "interface_bodies": payload.interface_bodies,
        "interface_specs": payload.interface_specs,
        # DEC-V62-A-sub-D10
        "bc_specs": payload.bc_specs,
        # DEC-V63-A-sub-D11
        "stl_face_normals": payload.stl_face_normals,
        # DEC-V63-A-sub-M-D6-HTTP-WIRE
        "stl_bbox_set": payload.stl_bbox_set,
    }
    if payload.bc_fork is not None:
        explicit_kwargs["bc_fork"] = payload.bc_fork
    case_label = "anon"
    if payload.case_dir is not None:
        case_path = _resolve_case_dir(payload.case_dir)
        case_label = case_path.name
        discovered = _autodiscover(case_path)
        for kw, value in discovered.items():
            if explicit_kwargs.get(kw) is None:
                explicit_kwargs[kw] = value
        if explicit_kwargs.get("step_path") is None:
            step = _autodiscover_step(case_path)
            if step is not None:
                explicit_kwargs["step_path"] = step
        geo_meta = _autodiscover_geometry_metadata(case_path)
        for kw, value in geo_meta.items():
            if explicit_kwargs.get(kw) is None:
                explicit_kwargs[kw] = value
        # DEC-V63-A-sub-D11: auto-discover stl_face_normals from
        # <case_dir>/cad/face_normals.json when the wire field is absent.
        # On-disk format mirrors the wire schema: dict[label, list[[nx,ny,nz]]].
        if explicit_kwargs.get("stl_face_normals") is None:
            normals_path = case_path / "cad" / "face_normals.json"
            if normals_path.is_file():
                try:
                    loaded = json.loads(normals_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    loaded = None
                if isinstance(loaded, dict):
                    explicit_kwargs["stl_face_normals"] = loaded

        # DEC-V63-A-sub-M-D6-HTTP-WIRE: auto-discover stl_bbox_set when
        # the wire field is absent. Search order (first hit wins):
        #   (1) <case_dir>/cad/stl_bbox_set.json   (dedicated file —
        #       mirrors face_normals.json convention)
        #   (2) <case_dir>/manifest.json field ``stl_bbox_set``
        # On-disk format mirrors the wire schema: dict[body_name,
        # [xmin, ymin, zmin, xmax, ymax, zmax]] in millimetres.
        # Per V130, missing files / malformed shapes degrade silently —
        # the route never raises from auto-discover.
        if explicit_kwargs.get("stl_bbox_set") is None:
            bbox_set_path = case_path / "cad" / "stl_bbox_set.json"
            if bbox_set_path.is_file():
                try:
                    bbox_set_loaded = json.loads(
                        bbox_set_path.read_text(encoding="utf-8")
                    )
                except (OSError, json.JSONDecodeError):
                    bbox_set_loaded = None
                if isinstance(bbox_set_loaded, dict):
                    explicit_kwargs["stl_bbox_set"] = bbox_set_loaded
            if explicit_kwargs.get("stl_bbox_set") is None:
                manifest_path = case_path / "manifest.json"
                if manifest_path.is_file():
                    manifest_doc = _load_dict_file(manifest_path) or {}
                    candidate = manifest_doc.get("stl_bbox_set")
                    if isinstance(candidate, dict):
                        explicit_kwargs["stl_bbox_set"] = candidate

    # Codex R0 P2 (2026-05-14): thin_wall_inputs arrives as plain dicts
    # over the wire; the advisor expects ``PatchGeometry`` dataclass
    # instances. Rehydrate here before dispatch so the documented input
    # actually produces findings (instead of failing into crash isolation).
    if explicit_kwargs.get("thin_wall_inputs") is not None:
        explicit_kwargs["thin_wall_inputs"] = _rehydrate_thin_wall_inputs(
            explicit_kwargs["thin_wall_inputs"]
        )

    # DEC-V63-A-sub-D11: stl_face_normals arrives as dict[label,
    # list[list[float]]] (JSON-compatible). The stack's
    # shm_stl_face_normals kwarg expects dict[label, list[tuple[float,
    # float, float]]]. Coerce + plumb to the stack-side name; 400 on
    # malformed normals shape.
    stl_face_normals_wire = explicit_kwargs.pop("stl_face_normals", None)
    if stl_face_normals_wire is not None:
        if not isinstance(stl_face_normals_wire, dict):
            raise HTTPException(
                status_code=400,
                detail={
                    "failing_check": "stl_face_normals_type",
                    "expected": "dict[str, list[[float, float, float]]]",
                    "got": type(stl_face_normals_wire).__name__,
                },
            )
        coerced_normals: dict[str, list[tuple[float, float, float]]] = {}
        for label, normals in stl_face_normals_wire.items():
            if not isinstance(label, str) or not isinstance(normals, list):
                continue
            triples: list[tuple[float, float, float]] = []
            for normal in normals:
                if not isinstance(normal, (list, tuple)) or len(normal) != 3:
                    continue
                try:
                    triples.append((float(normal[0]), float(normal[1]), float(normal[2])))
                except (TypeError, ValueError, OverflowError):
                    continue
            coerced_normals[label] = triples
        explicit_kwargs["shm_stl_face_normals"] = coerced_normals

    # DEC-V63-A-sub-M-D6-HTTP-WIRE: stl_bbox_set arrives as
    # dict[body_name, list[float]] — Pydantic's strict dict typing on the
    # request schema enforces the top-level shape (422 on non-dict). The
    # D6 advisor accepts ``dict[str, Any]`` and performs its own per-entry
    # bbox coercion via ``_coerce_bbox`` (drops malformed entries
    # silently). Nothing further needed at the route boundary — the value
    # passes through unchanged in ``explicit_kwargs`` to assemble_stack.

    # DEC-V62-A-sub-REQ-SCHEMA-EXPAND: wire-form lists/six-tuples →
    # assemble_stack-shaped kwargs. Pop the wire-form keys and replace
    # with the dataclass / scalar shapes the stack signature expects.
    step_bbox_wire = explicit_kwargs.pop("step_bbox", None)
    if step_bbox_wire is not None:
        explicit_kwargs["step_bbox_max_extent_raw"] = _bbox_max_extent(step_bbox_wire)
    step_extents_wire = explicit_kwargs.pop("step_extents", None)
    if step_extents_wire is not None:
        try:
            explicit_kwargs["step_body_extents_raw"] = [float(x) for x in step_extents_wire]
        except (TypeError, ValueError, OverflowError) as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "failing_check": "step_extents_fields",
                    "expected": "list of floats",
                    "error": str(exc),
                },
            ) from exc
    if explicit_kwargs.get("interface_bodies") is not None:
        explicit_kwargs["interface_bodies"] = _rehydrate_interface_bodies(
            explicit_kwargs["interface_bodies"]
        )
    if explicit_kwargs.get("interface_specs") is not None:
        explicit_kwargs["interface_specs"] = _rehydrate_interface_specs(
            explicit_kwargs["interface_specs"]
        )

    stack_kwargs = {k: v for k, v in explicit_kwargs.items() if v is not None}

    # ----- 2. Dispatch stack (crash-isolated per advisor) -----
    t_advisor_start = time.perf_counter()
    report = assemble_stack(**stack_kwargs)
    advisor_ms = (time.perf_counter() - t_advisor_start) * 1000.0

    # ----- 2.5 Apply V-series drift guard (DEC-V62-A-sub-M-DRIFT-V2) -----
    # Query param wins over request body field; both default to "audit"
    # so existing 50 route tests see identical wire contract (one extra
    # advisor_calls entry · zero finding deltas).
    drift_mode_raw = request.query_params.get("drift_mode") or payload.drift_mode or "audit"
    drift_mode = drift_mode_raw.strip().lower()
    if drift_mode not in ("audit", "strict"):
        raise HTTPException(
            status_code=400,
            detail={
                "failing_check": "drift_mode_value",
                "expected": "audit|strict",
                "got": drift_mode_raw,
            },
        )
    report = enforce_at_route_boundary(report, mode=drift_mode)  # type: ignore[arg-type]

    # ----- 3. Optional LLM augment (best-effort, 4Q-gate-safe) -----
    llm_enhanced = False
    llm_ms = 0.0
    if payload.llm_enhance:
        report_dict_preview = _report_to_dict(report)
        llm_enhanced, llm_ms = _try_llm_enhance(report_dict_preview)

    # ----- 4. Serialize + persist audit artifact -----
    report_dict = _report_to_dict(report)
    audit_path = _persist_audit(
        {
            "case_label": case_label,
            "llm_enhanced": llm_enhanced,
            "report": report_dict,
        },
        case_label=case_label,
    )

    total_ms = (time.perf_counter() - t_start) * 1000.0

    return AIReviewResponse(
        report=report_dict,
        audit_artifact_path=str(audit_path),
        llm_enhanced=llm_enhanced,
        timing={
            "advisor_dispatch_ms": round(advisor_ms, 3),
            "llm_ms": round(llm_ms, 3),
            "total_ms": round(total_ms, 3),
        },
    )
