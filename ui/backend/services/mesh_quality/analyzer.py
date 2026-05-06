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

import errno
import os
import re
import stat
from pathlib import Path

from ui.backend.services.mesh_quality.schemas import (
    MeshQualityReport,
    MeshQualityReportV126,
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


def _read_text_no_symlink(
    path: Path,
    *,
    failing_check: str,
    dir_fd: int | None = None,
) -> str:
    """Read ``path`` as UTF-8 text without following symlinks.

    Codex R1 P1: a planted symlink at any of the polyMesh files
    would otherwise let the analyzer (and via the AI-coach prefetch,
    the LLM) exfiltrate arbitrary host files. Open the file with
    ``O_NOFOLLOW`` so the kernel raises ``ELOOP`` on a symlinked
    final component; raise :class:`MeshQualityParseError` with
    a stable ``failing_check`` so the route surfaces a structured
    detail rather than an opaque traceback.

    Codex base-review-4 P1: when ``dir_fd`` is supplied, the open is
    dir_fd-relative and ``path.name`` is interpreted as a leaf under
    the pinned parent inode — closes the parent-symlink-swap TOCTTOU
    where ``constant/`` or ``polyMesh/`` could be retargeted between
    a path-only lstat preflight and a leaf open. Same containment
    discipline as ``services.case_solve.patch_classification_store``.
    """
    try:
        if dir_fd is not None:
            fd = os.open(
                path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=dir_fd
            )
        else:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            # A symlink was planted at the final path component.
            # Refuse to follow.
            raise MeshQualityParseError(
                f"refused to follow symlink at {path.name}",
                failing_check="symlink_escape",
            ) from exc
        raise MeshQualityParseError(
            f"could not open {path.name}: {type(exc).__name__}",
            failing_check=failing_check,
        ) from exc
    try:
        size = os.fstat(fd).st_size
        raw = os.read(fd, size) if size > 0 else b""
    except OSError as exc:
        raise MeshQualityParseError(
            f"could not read {path.name}: {type(exc).__name__}",
            failing_check=failing_check,
        ) from exc
    finally:
        try:
            os.close(fd)
        except OSError:
            pass
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise MeshQualityParseError(
            f"{path.name} is not valid UTF-8",
            failing_check=failing_check,
        ) from exc


def _split_foam_block(
    path: Path,
    *,
    failing_check: str,
    dir_fd: int | None = None,
) -> tuple[int, str]:
    """Parse a parens-list FOAM file into (declared_count, body).

    Returns the declared count from the header line and the body
    (raw text between the opening ``(`` and the closing ``)``).

    Raises :class:`MeshQualityParseError` when the file format
    doesn't match. ``failing_check`` is the structural problem
    surfaced to the route layer. When ``dir_fd`` is supplied, the
    underlying read is dir_fd-relative — see ``_read_text_no_symlink``.
    """
    text = _read_text_no_symlink(path, failing_check=failing_check, dir_fd=dir_fd)
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


def _parse_int_body(body: str) -> list[int]:
    """Parse all bare-integer entries from a parens-list body.

    Returns the list in original order. Used to derive cell_count
    (max(owner) + 1) AND to verify the declared count against the
    actual entries (Codex R1 P2: truncated owner/neighbour blocks
    must be rejected, not silently accepted)."""
    out: list[int] = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            value = int(line.split()[0])
        except (ValueError, IndexError):
            continue
        out.append(value)
    return out


def _parse_points_body(body: str) -> list[tuple[float, float, float]]:
    pts: list[tuple[float, float, float]] = []
    for m in _POINT_LINE_RE.finditer(body):
        pts.append((float(m.group(1)), float(m.group(2)), float(m.group(3))))
    return pts


def _read_patch_ranges(
    boundary_path: Path, *, dir_fd: int | None = None
) -> dict[str, tuple[int, int]]:
    """Return ``{patch_name: (startFace, nFaces)}`` from polyMesh/boundary.
    Skips the FoamFile header dict.

    V129a: the (startFace, nFaces) tuple form is what the per-patch
    severe-non-ortho aggregator needs; ``_read_patch_face_counts``
    is now a thin wrapper that drops startFace.
    """
    text = _read_text_no_symlink(
        boundary_path, failing_check="boundary_unreadable", dir_fd=dir_fd
    )
    out: dict[str, tuple[int, int]] = {}
    for m in _BOUNDARY_PATCH_RE.finditer(text):
        name = m.group(1)
        if name == "FoamFile":
            continue
        out[name] = (int(m.group(3)), int(m.group(2)))
    # Validate against the declared count header. Some boundary
    # files have no header (just the FoamFile dict + patch list);
    # only enforce the check when the header is present.
    header_match = _FOAM_BLOCK_HEADER_RE.search(text)
    if header_match is not None:
        declared = int(header_match.group(1))
        if declared != len(out):
            raise MeshQualityParseError(
                f"boundary header declares {declared} patches but parsed {len(out)}",
                failing_check="boundary_count_mismatch",
            )
    return out


def _read_patch_face_counts(
    boundary_path: Path, *, dir_fd: int | None = None
) -> dict[str, int]:
    """Return {patch_name: nFaces} from polyMesh/boundary. Thin wrapper
    over :func:`_read_patch_ranges` that drops the startFace component.

    Kept for byte-identical V122 callers; downstream V126/V129a code
    that needs face-id mapping should call ``_read_patch_ranges``
    directly.
    """
    return {
        name: n_faces for name, (_start, n_faces) in _read_patch_ranges(
            boundary_path, dir_fd=dir_fd
        ).items()
    }


def aggregate_severe_faces_per_patch(
    severe_face_ids: tuple[int, ...] | list[int],
    patch_ranges: dict[str, tuple[int, int]],
) -> dict[str, int]:
    """Map severe-non-ortho face IDs to their patches via the
    ``(startFace, nFaces)`` ranges from polyMesh/boundary, returning
    ``{patch_name: count}`` for every named patch.

    Internal faces (id < min(startFace) for all patches) are silently
    dropped — they don't belong to any boundary patch. The returned
    dict ALWAYS includes every patch from ``patch_ranges`` (count=0
    for clean ones) so the frontend can render zero-count chips
    without a separate name list.
    """
    out: dict[str, int] = {name: 0 for name in patch_ranges}
    if not severe_face_ids:
        return out
    # Build a list of (start, end_exclusive, name) sorted by start so
    # we can binary-search per face id. For the typical case (≤30
    # patches), linear scan per id is also fine — but sort + bisect
    # keeps it O(n log p) which matters when checkMesh writes 10k+ ids.
    ranges = sorted(
        ((start, start + n, name) for name, (start, n) in patch_ranges.items()),
        key=lambda triple: triple[0],
    )
    for fid in severe_face_ids:
        # Linear scan is correct and predictable; the patch count is
        # bounded so the asymptotic win from bisect doesn't justify
        # the readability cost.
        for start, end, name in ranges:
            if start <= fid < end:
                out[name] += 1
                break
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


def analyze_mesh_quality(
    case_dir: Path,
    *,
    run_checkmesh: bool = False,
) -> MeshQualityReport | MeshQualityReportV126:
    """Read polyMesh and produce a :class:`MeshQualityReport`.

    Raises :class:`MeshQualityNotAvailableError` if the case has not
    been meshed yet (polyMesh dir missing or core files absent).

    Raises :class:`MeshQualityParseError` if the polyMesh files exist
    but cannot be parsed in the V1 ASCII format. ``failing_check``
    enumerates the structural problem so the route surfaces a stable
    HTTP 500 detail.

    DEC-V61-126: when ``run_checkmesh=True``, additionally invoke
    OpenFOAM's ``checkMesh`` inside the cfd-openfoam container to
    augment the report with skewness, non-orthogonality, and aspect-
    ratio metrics. **Graceful degradation**: when the container is
    unavailable or not running, the V122 fields populate as normal
    and the checkmesh_* fields stay None (with a logged warning) —
    the caller does NOT see an error. Other failure modes (parse
    errors, exit-nonzero) DO raise so real bugs surface; the only
    swallowed errors are the explicit "container not present"
    operational states an engineer might reasonably hit on a fresh
    install.
    """
    case_id = case_dir.name
    # Codex base-review-4 P1: pin case_dir → constant → polyMesh as
    # fds with O_NOFOLLOW|O_DIRECTORY in sequence, then do all leaf
    # opens dir_fd-relative. The R1 / base-review-2 lstat preflight
    # was correct at the moment-of-check but had a TOCTTOU window:
    # `constant/` or `polyMesh/` could be swapped to a symlink AFTER
    # the lstat returned and BEFORE the leaf O_NOFOLLOW open. Pinning
    # the inode chain via fds closes that window — every subsequent
    # op references the inode, not the path, and a mid-read symlink
    # swap on a parent has no effect.
    fds_to_close: list[int] = []
    try:
        try:
            fd_case = os.open(
                case_dir, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
            )
        except FileNotFoundError as exc:
            raise MeshQualityNotAvailableError(
                f"polyMesh directory missing for case_id={case_id!r}"
            ) from exc
        except OSError as exc:
            if exc.errno == errno.ELOOP:
                raise MeshQualityParseError(
                    "refused to follow symlink at case_dir",
                    failing_check="symlink_escape",
                ) from exc
            raise MeshQualityParseError(
                f"could not open case_dir: errno={exc.errno}",
                failing_check="symlink_escape",
            ) from exc
        fds_to_close.append(fd_case)

        for child_name, label in (("constant", "constant"), ("polyMesh", "polyMesh")):
            try:
                fd_child = os.open(
                    child_name,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                    dir_fd=fds_to_close[-1],
                )
            except FileNotFoundError as exc:
                raise MeshQualityNotAvailableError(
                    f"polyMesh directory missing for case_id={case_id!r}"
                ) from exc
            except OSError as exc:
                if exc.errno == errno.ELOOP:
                    raise MeshQualityParseError(
                        f"refused to follow symlink at {label}",
                        failing_check="symlink_escape",
                    ) from exc
                if exc.errno == errno.ENOTDIR:
                    raise MeshQualityNotAvailableError(
                        f"polyMesh directory missing for case_id={case_id!r}"
                    ) from exc
                raise MeshQualityParseError(
                    f"could not open {label}: errno={exc.errno}",
                    failing_check="symlink_escape",
                ) from exc
            fds_to_close.append(fd_child)
        fd_polymesh = fds_to_close[-1]

        polymesh = case_dir / "constant" / "polyMesh"
        points_path = polymesh / "points"
        owner_path = polymesh / "owner"
        neighbour_path = polymesh / "neighbour"
        boundary_path = polymesh / "boundary"

        # Required-leaf existence check via dir_fd-relative stat.
        for leaf_name in ("points", "owner", "boundary"):
            try:
                os.stat(leaf_name, dir_fd=fd_polymesh, follow_symlinks=False)
            except FileNotFoundError as exc:
                raise MeshQualityNotAvailableError(
                    f"polyMesh/{leaf_name} missing for case_id={case_id!r}"
                ) from exc
        # neighbour is optional — strictly internal-face count; absent
        # for some degenerate meshes (single-cell etc).

        declared_pt_count, points_body = _split_foam_block(
            points_path, failing_check="points_unreadable", dir_fd=fd_polymesh
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
            owner_path, failing_check="owner_unreadable", dir_fd=fd_polymesh
        )
        owner_entries = _parse_int_body(owner_body)
        # Codex R1 P2: the declared count header must match the actual
        # number of entries. A truncated owner file would otherwise
        # produce a 200 with bogus cell_count.
        if owner_face_count != len(owner_entries):
            raise MeshQualityParseError(
                f"owner header declares {owner_face_count} entries but "
                f"parsed {len(owner_entries)}",
                failing_check="owner_count_mismatch",
            )
        max_owner = max(owner_entries) if owner_entries else -1
        cell_count = max_owner + 1 if max_owner >= 0 else 0

        try:
            os.stat("neighbour", dir_fd=fd_polymesh, follow_symlinks=False)
            neighbour_present = True
        except FileNotFoundError:
            neighbour_present = False
        if neighbour_present:
            internal_face_count, neighbour_body = _split_foam_block(
                neighbour_path, failing_check="neighbour_unreadable", dir_fd=fd_polymesh
            )
            neighbour_entries = _parse_int_body(neighbour_body)
            if internal_face_count != len(neighbour_entries):
                raise MeshQualityParseError(
                    f"neighbour header declares {internal_face_count} entries "
                    f"but parsed {len(neighbour_entries)}",
                    failing_check="neighbour_count_mismatch",
                )
        else:
            internal_face_count = 0
        boundary_face_count = max(0, owner_face_count - internal_face_count)

        patch_ranges = _read_patch_ranges(boundary_path, dir_fd=fd_polymesh)
        patch_face_counts = {
            name: n for name, (_start, n) in patch_ranges.items()
        }
    finally:
        for fd in reversed(fds_to_close):
            try:
                os.close(fd)
            except OSError:
                pass

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

    # V126 augment: only when caller explicitly opts in. Default-False
    # path is byte-identical to V122 / V123 behavior — no Docker call
    # made, no container probe, no log warning. V126 R1 P2 backward-
    # compat fix: return MeshQualityReport (V122 shape, no checkmesh_*
    # keys) when not opted-in; return MeshQualityReportV126 (extended)
    # only when run_checkmesh=True.
    base_kwargs = dict(
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
    if not run_checkmesh:
        return MeshQualityReport(report_kind="v122", **base_kwargs)
    return MeshQualityReportV126(
        report_kind="v126",
        **base_kwargs,
        **_try_run_checkmesh(case_dir, patch_ranges=patch_ranges),
    )


def _try_run_checkmesh(
    case_dir: Path,
    *,
    patch_ranges: dict[str, tuple[int, int]] | None = None,
) -> dict[str, object]:
    """V126 graceful-degradation wrapper around run_checkmesh.

    Returns a dict suitable for kwargs unpacking into MeshQualityReport.
    On container-down operational states (container_unavailable /
    container_not_running / docker_sdk_missing) returns an empty dict
    with a logged warning so the caller still gets the V122 fields.
    On parse errors and other genuine failures, RE-raises so real
    bugs surface.

    V129a: when ``patch_ranges`` is provided AND checkMesh wrote a
    nonOrthoFaces faceSet, compute the per-patch severe-non-ortho
    count and surface it as ``checkmesh_n_severe_non_ortho_faces_per_patch``.
    Internal faces (face id below all patch startFaces) are dropped —
    they don't belong to any named patch.
    """
    import logging

    from ui.backend.services.mesh_quality.checkmesh_runner import (
        CheckMeshError,
        run_checkmesh,
    )

    logger = logging.getLogger(__name__)
    # Operational states an engineer could reasonably hit on a fresh
    # install — container hasn't been brought up yet, Docker missing,
    # etc. Surface as warning, NOT error; the V122 fields are still
    # informative on their own.
    _GRACEFUL_FAILING_CHECKS = frozenset(
        {
            "container_unavailable",
            "container_not_running",
            "docker_sdk_missing",
        }
    )
    try:
        result = run_checkmesh(case_dir)
    except CheckMeshError as exc:
        if exc.failing_check in _GRACEFUL_FAILING_CHECKS:
            logger.warning(
                "checkMesh skipped for case_id=%r failing_check=%s; "
                "report will carry V122 fields only.",
                case_dir.name,
                exc.failing_check,
            )
            return {}
        # Genuine bug surfaces (parse_error, checkmesh_exit_nonzero,
        # docker_sdk_error, polymesh_missing — though polymesh_missing
        # would have been caught by analyze_mesh_quality's earlier
        # check).
        raise
    per_patch: dict[str, int] | None = None
    if patch_ranges is not None and result.severe_non_ortho_face_ids:
        per_patch = aggregate_severe_faces_per_patch(
            result.severe_non_ortho_face_ids, patch_ranges
        )
    return {
        "checkmesh_max_non_orthogonality_deg": result.max_non_orthogonality_deg,
        "checkmesh_max_skewness": result.max_skewness,
        "checkmesh_max_aspect_ratio": result.max_aspect_ratio,
        "checkmesh_mesh_ok": result.mesh_ok,
        "checkmesh_n_severe_non_ortho_faces": result.n_severe_non_ortho_faces,
        "checkmesh_failed_checks": (
            result.failed_checks if result.failed_checks else None
        ),
        "checkmesh_n_severe_non_ortho_faces_per_patch": per_patch,
    }
