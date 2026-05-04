"""DEC-V61-122 · polyMesh analyzer (pure-Python · ASCII format only).

Parses ``<case_dir>/constant/polyMesh/{points, owner, neighbour,
boundary}`` into a :class:`MeshQualityReport`. The parser is
deliberately narrow — V1 ships ASCII format, no Docker, no
skewness/orthogonality. Binary support and richer metrics land in
V61-123.

Parse strategy:
  * ``points``: parens-list-with-count format. count = point_count;
    each entry is ``(x y z)``.
  * ``owner``: parens-list. count = total face count (internal +
    boundary). max(entries) + 1 = cell_count.
  * ``neighbour``: parens-list. count = internal face count.
  * ``boundary``: dict-shaped. Each non-FoamFile patch entry has
    ``nFaces N; startFace M;`` — same regex pattern V61-108 uses.

Edge cases handled:
  * Missing polyMesh dir → :class:`MeshQualityNotAvailableError`
    (route 404).
  * Missing or corrupt individual file →
    :class:`MeshQualityParseError(failing_check=...)` (route 500
    with structured detail).
  * 2D mesh with one collapsed BB axis → BB volume 0,
    cells_per_unit_volume None, warning emitted.

Performance: synthetic case with 100k cells parses in ~50-200ms on
dev hardware. Caching deferred to V61-123 if dogfood shows latency.
"""
from __future__ import annotations

import re
from pathlib import Path

from ui.backend.services.mesh_quality.schemas import (
    MeshQualityReport,
    MeshWarning,
)

# ────────── Errors ──────────


class MeshQualityNotAvailableError(RuntimeError):
    """polyMesh directory or any of {points, owner, boundary} is missing.
    Route layer maps to HTTP 404 — the case has not yet been meshed
    (or the mesh files were cleaned up)."""


class MeshQualityParseError(RuntimeError):
    """polyMesh files exist but parsing failed. ``failing_check``
    enumerates the structural problem so the route surfaces a stable
    detail without leaking traceback contents.
    """

    def __init__(self, message: str, *, failing_check: str) -> None:
        super().__init__(message)
        self.failing_check = failing_check


# ────────── Constants ──────────


# V1 thresholds for warning emission. Tuned conservatively — better
# to surface a borderline case than miss a real defect. Engineers
# evaluate severity using their own judgment when the AI coach
# echoes them.
_CELL_COUNT_LOW_THRESHOLD = 100
_CELL_COUNT_DENSE_THRESHOLD = 5_000_000
_BB_AXIS_COLLAPSE_EPS = 1e-9
# AR estimate: longest BB edge / shortest non-collapsed BB edge.
# Above this, surface an info warning; engineers may want to refine.
_AR_INFO_THRESHOLD = 50.0


# Regex matching V108's pattern for the boundary file. Same source
# of truth so V108 and V122 cannot drift.
_BOUNDARY_PATCH_RE = re.compile(
    r"(\w+)\s*\{[^}]*nFaces\s+(\d+)[^}]*startFace\s+(\d+)[^}]*\}",
    re.DOTALL,
)

_FOAM_BLOCK_HEADER_RE = re.compile(r"^\s*(\d+)\s*\n\(\s*\n", flags=re.MULTILINE)
_POINT_LINE_RE = re.compile(
    r"\(([-0-9.eE+]+)\s+([-0-9.eE+]+)\s+([-0-9.eE+]+)\)"
)


# ────────── Helpers ──────────


def _split_foam_block(path: Path, *, failing_check: str) -> tuple[int, str]:
    """Parse a parens-list FOAM file into (declared_count, body).

    Returns the declared count from the header line and the body
    (raw text between the opening ``(`` and the closing ``)``).

    Raises :class:`MeshQualityParseError` when the file format
    doesn't match. ``failing_check`` is the structural problem
    surfaced to the route layer.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise MeshQualityParseError(
            f"could not read {path.name}: {type(exc).__name__}",
            failing_check=failing_check,
        ) from exc
    m = _FOAM_BLOCK_HEADER_RE.search(text)
    if not m:
        raise MeshQualityParseError(
            f"{path.name} is not a parens-list FOAM file (missing count header)",
            failing_check=failing_check,
        )
    count = int(m.group(1))
    body_start = m.end()
    body_end = text.find("\n)", body_start)
    if body_end == -1:
        raise MeshQualityParseError(
            f"{path.name} parens list is unterminated",
            failing_check=failing_check,
        )
    return count, text[body_start:body_end]


def _max_int_in_body(body: str) -> int:
    """Return the largest non-negative integer appearing on any line
    of the body. Used for owner.max() to derive cell_count.

    Returns -1 when body is empty (caller treats as 'no cells').
    """
    largest = -1
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        # Owner/neighbour entries are bare integers, one per line.
        # Defensive: if a line has multiple tokens (shouldn't happen
        # in ASCII format), we still grab the first parseable int.
        try:
            value = int(line.split()[0])
        except (ValueError, IndexError):
            continue
        if value > largest:
            largest = value
    return largest


def _parse_points_body(body: str) -> list[tuple[float, float, float]]:
    pts: list[tuple[float, float, float]] = []
    for m in _POINT_LINE_RE.finditer(body):
        pts.append((float(m.group(1)), float(m.group(2)), float(m.group(3))))
    return pts


def _read_patch_face_counts(boundary_path: Path) -> dict[str, int]:
    """Return {patch_name: nFaces} from polyMesh/boundary. Skips the
    FoamFile dict that always sits at the head."""
    try:
        text = boundary_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise MeshQualityParseError(
            f"could not read boundary: {type(exc).__name__}",
            failing_check="boundary_unreadable",
        ) from exc
    out: dict[str, int] = {}
    for m in _BOUNDARY_PATCH_RE.finditer(text):
        name = m.group(1)
        if name == "FoamFile":
            continue
        out[name] = int(m.group(2))
    return out


def _bounding_box(
    pts: list[tuple[float, float, float]],
) -> tuple[
    tuple[float, float, float],
    tuple[float, float, float],
    float,
    list[bool],
]:
    """Return (min_corner, max_corner, volume, axis_collapsed_flags).

    The flags list has 3 entries (x, y, z); each True iff that axis
    spans less than ``_BB_AXIS_COLLAPSE_EPS`` (a 2D-mesh signal).
    Volume is 0.0 when any axis is collapsed.
    """
    if not pts:
        return ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 0.0, [True, True, True])
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    zs = [p[2] for p in pts]
    mn = (min(xs), min(ys), min(zs))
    mx = (max(xs), max(ys), max(zs))
    spans = [mx[i] - mn[i] for i in range(3)]
    collapsed = [s < _BB_AXIS_COLLAPSE_EPS for s in spans]
    if any(collapsed):
        volume = 0.0
    else:
        volume = spans[0] * spans[1] * spans[2]
    return (mn, mx, volume, collapsed)


def _emit_warnings(
    *,
    cell_count: int,
    bb_collapsed: list[bool],
    bb_max: tuple[float, float, float],
    bb_min: tuple[float, float, float],
    patch_face_counts: dict[str, int],
) -> list[MeshWarning]:
    out: list[MeshWarning] = []
    if cell_count < _CELL_COUNT_LOW_THRESHOLD:
        out.append(
            MeshWarning(
                severity="warning",
                code="cell_count_low",
                message=(
                    f"only {cell_count} cells in this mesh — "
                    "under-refined for production-quality results."
                ),
            )
        )
    if cell_count > _CELL_COUNT_DENSE_THRESHOLD:
        out.append(
            MeshWarning(
                severity="info",
                code="dense_mesh",
                message=(
                    f"{cell_count} cells; large simulation cost expected "
                    "(>5M cells)."
                ),
            )
        )
    if any(bb_collapsed):
        axes = "xyz"
        collapsed_axes = ",".join(axes[i] for i, c in enumerate(bb_collapsed) if c)
        out.append(
            MeshWarning(
                severity="info",
                code="bb_collapsed_dim",
                message=(
                    f"bounding box has collapsed axis ({collapsed_axes}) — "
                    "2D mesh detected; cells_per_unit_volume not computed."
                ),
            )
        )
    # Estimate aspect ratio from the BB extents (the longest BB edge
    # over the shortest non-collapsed BB edge). This is a coarse
    # signal — the AR of individual cells can be very different —
    # but a >50× span suggests the mesh designer should review the
    # refinement strategy.
    spans = [bb_max[i] - bb_min[i] for i in range(3)]
    non_collapsed_spans = [s for s, c in zip(spans, bb_collapsed) if not c]
    if len(non_collapsed_spans) >= 2:
        max_span = max(non_collapsed_spans)
        min_span = min(non_collapsed_spans)
        if min_span > 0:
            ar_estimate = max_span / min_span
            if ar_estimate > _AR_INFO_THRESHOLD:
                out.append(
                    MeshWarning(
                        severity="info",
                        code="very_high_aspect_ratio_estimate",
                        message=(
                            f"bounding-box edge AR ≈ {ar_estimate:.1f} — "
                            "individual cell AR may exceed solver "
                            "tolerance; review refinement strategy."
                        ),
                    )
                )
    for patch_name, n in patch_face_counts.items():
        if n == 0:
            out.append(
                MeshWarning(
                    severity="warning",
                    code="patch_zero_faces",
                    message=(
                        f"patch '{patch_name}' has 0 faces — "
                        "BC will not be applied to any geometry."
                    ),
                )
            )
    return out


# ────────── Public entry point ──────────


def analyze_mesh_quality(case_dir: Path) -> MeshQualityReport:
    """Read polyMesh and produce a :class:`MeshQualityReport`.

    Raises :class:`MeshQualityNotAvailableError` if the case has not
    been meshed yet (polyMesh dir missing or core files absent).

    Raises :class:`MeshQualityParseError` if the polyMesh files exist
    but cannot be parsed in the V1 ASCII format. ``failing_check``
    enumerates the structural problem so the route surfaces a stable
    HTTP 500 detail.
    """
    case_id = case_dir.name
    polymesh = case_dir / "constant" / "polyMesh"
    if not polymesh.is_dir():
        raise MeshQualityNotAvailableError(
            f"polyMesh directory missing for case_id={case_id!r}"
        )

    points_path = polymesh / "points"
    owner_path = polymesh / "owner"
    neighbour_path = polymesh / "neighbour"
    boundary_path = polymesh / "boundary"

    for required, name in (
        (points_path, "points"),
        (owner_path, "owner"),
        (boundary_path, "boundary"),
    ):
        if not required.is_file():
            raise MeshQualityNotAvailableError(
                f"polyMesh/{name} missing for case_id={case_id!r}"
            )
    # neighbour is optional — strictly internal-face count; absent
    # for some degenerate meshes (single-cell etc).

    declared_pt_count, points_body = _split_foam_block(
        points_path, failing_check="points_unreadable"
    )
    pts = _parse_points_body(points_body)
    if declared_pt_count != len(pts):
        # Defensive: declared header count should match parsed entries;
        # mismatch means corrupt file.
        raise MeshQualityParseError(
            f"points header declares {declared_pt_count} entries but "
            f"parsed {len(pts)}",
            failing_check="points_count_mismatch",
        )

    owner_face_count, owner_body = _split_foam_block(
        owner_path, failing_check="owner_unreadable"
    )
    max_owner = _max_int_in_body(owner_body)
    cell_count = max_owner + 1 if max_owner >= 0 else 0

    if neighbour_path.is_file():
        internal_face_count, _neighbour_body = _split_foam_block(
            neighbour_path, failing_check="neighbour_unreadable"
        )
    else:
        internal_face_count = 0
    boundary_face_count = max(0, owner_face_count - internal_face_count)

    patch_face_counts = _read_patch_face_counts(boundary_path)

    bb_min, bb_max, bb_volume, bb_collapsed = _bounding_box(pts)
    cells_per_unit_volume: float | None = None
    if bb_volume > 0:
        cells_per_unit_volume = round(cell_count / bb_volume, 4)

    warnings = _emit_warnings(
        cell_count=cell_count,
        bb_collapsed=bb_collapsed,
        bb_max=bb_max,
        bb_min=bb_min,
        patch_face_counts=patch_face_counts,
    )

    return MeshQualityReport(
        case_id=case_id,
        polymesh_present=True,
        cell_count=cell_count,
        point_count=len(pts),
        internal_face_count=internal_face_count,
        boundary_face_count=boundary_face_count,
        bounding_box_min=bb_min,
        bounding_box_max=bb_max,
        bounding_box_volume=round(bb_volume, 6),
        cells_per_unit_volume=cells_per_unit_volume,
        patch_face_counts=patch_face_counts,
        warnings=warnings,
    )
