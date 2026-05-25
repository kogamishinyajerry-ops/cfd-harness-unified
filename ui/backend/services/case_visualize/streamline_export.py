"""Streamline VTP exporter — wraps OpenFOAM's native ``streamLine``
function-object. Seeds streamlines from the inlet patch's bounding-box
diagonal (auto seeding, per B2.5 architecture decision 2026-05-19).

Output (per OpenFOAM v2312):

    <case>/postProcessing/sets/streamlines/<time>/track0.vtp

Single VTP polyData file · LittleEndian binary · contains
``<Lines>`` (one polyline per particle track) + ``<PointData>`` arrays
``U``, ``p``. vtk.js's vtkXMLPolyDataReader consumes this natively.

Why container-side streamLine and not Python vtkStreamTracer:
  • cfd-harness Python env doesn't have vtk installed
  • OpenFOAM's streamLine reproduces field interpolation exactly the
    same way as the solver (no client-server interpolation drift)
  • One-shot subprocess avoids the heavy vtk SDK dependency
"""
from __future__ import annotations

import math
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

Vec3 = tuple[float, float, float]


class StreamlineExportError(RuntimeError):
    """Raised when seed extraction or streamLine execution fails."""


IMAGE = os.environ.get("CFD_OPENFOAM_IMAGE", "opencfd/openfoam-default:2312")
BASHRC = "/usr/lib/openfoam/openfoam2312/etc/bashrc"


@dataclass(frozen=True)
class StreamlineExportResult:
    """On-disk path for the VTP cloud + the time it corresponds to."""

    track_vtp: Path
    latest_time: str
    seed_count: int  # number of input seeds (not output track count)


# ─────────────── Mesh-derived seeding (DEC-V61-205 M5 C2) ───────────────
#
# The seed points MUST land inside the fluid domain or streamLine returns
# a single degenerate track (NumberOfPoints=1, U=0). The legacy code
# hardcoded an x=-2.95 line for the KJ66 external-aero box, so EVERY other
# geometry (LDC, backward_step, …) seeded outside its mesh → no streamline
# overlay ever rendered. We now derive the seed line from the case's real
# bounding box: prefer the actual mesh extent (polyMesh/points), fall back
# to the ingest manifest's geometry bbox, and only then to the legacy box.

# Legacy KJ66 external-aero seed line · last resort when no bbox is found.
_LEGACY_KJ66_SEEDS: list[Vec3] = [
    (-2.95, -1.0, -1.0),
    (-2.95, -0.7, -0.7),
    (-2.95, -0.4, -0.4),
    (-2.95, -0.1, -0.1),
    (-2.95, 0.1, 0.1),
    (-2.95, 0.4, 0.4),
    (-2.95, 0.7, 0.7),
    (-2.95, 1.0, 1.0),
]

_POINT_RE = re.compile(
    r"\(\s*([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s*\)"
)


def _bbox_from_points_file(points_path: Path) -> tuple[Vec3, Vec3] | None:
    """AABB from an ASCII ``constant/polyMesh/points`` file. Returns None
    for a missing/binary/empty file (caller falls back)."""
    if not points_path.is_file():
        return None
    try:
        text = points_path.read_text(errors="ignore")
    except OSError:
        return None
    mins = [math.inf, math.inf, math.inf]
    maxs = [-math.inf, -math.inf, -math.inf]
    found = False
    for m in _POINT_RE.finditer(text):
        try:
            xyz = (float(m.group(1)), float(m.group(2)), float(m.group(3)))
        except ValueError:
            continue
        found = True
        for i in range(3):
            mins[i] = min(mins[i], xyz[i])
            maxs[i] = max(maxs[i], xyz[i])
    if not found or not all(math.isfinite(v) for v in (*mins, *maxs)):
        return None
    return ((mins[0], mins[1], mins[2]), (maxs[0], maxs[1], maxs[2]))


def _bbox_from_manifest(case_dir: Path) -> tuple[Vec3, Vec3] | None:
    """AABB from the ingest manifest's ``ingest_report_summary.bbox_*``.
    The geometry bbox is in the same coordinate frame as the gmshToFoam
    mesh, so it's a safe fallback when polyMesh/points is binary."""
    manifest = case_dir / "case_manifest.yaml"
    if not manifest.is_file():
        return None
    try:
        import yaml

        data = yaml.safe_load(manifest.read_text()) or {}
    except Exception:
        return None
    summ = data.get("ingest_report_summary") or {}
    bmin, bmax = summ.get("bbox_min"), summ.get("bbox_max")
    if not (isinstance(bmin, list) and isinstance(bmax, list)):
        return None
    if len(bmin) != 3 or len(bmax) != 3:
        return None
    try:
        return (
            (float(bmin[0]), float(bmin[1]), float(bmin[2])),
            (float(bmax[0]), float(bmax[1]), float(bmax[2])),
        )
    except (TypeError, ValueError):
        return None


def _mesh_bbox(case_dir: Path) -> tuple[Vec3, Vec3] | None:
    """Domain AABB for seeding: real mesh extent first, manifest second."""
    box = _bbox_from_points_file(case_dir / "constant" / "polyMesh" / "points")
    if box is not None:
        return box
    return _bbox_from_manifest(case_dir)


def _seed_points_from_bbox(bmin: Vec3, bmax: Vec3, n: int = 12) -> list[Vec3]:
    """``n`` points along the interior body diagonal (5%–95% of the AABB)
    so seeds land inside the fluid domain for any geometry. A degenerate
    (zero-width) axis collapses to its midpoint rather than producing NaNs."""
    n = max(2, n)
    lo, hi = 0.05, 0.95
    pts: list[Vec3] = []
    for i in range(n):
        t = lo + (hi - lo) * (i / (n - 1))
        pts.append(
            tuple(  # type: ignore[arg-type]
                bmin[k] + t * (bmax[k] - bmin[k]) for k in range(3)
            )
        )
    return pts


def _build_streamlines_dict(case_dir: Path, seed_count: int = 12) -> int:
    """Write system/streamlinesDict for OpenFOAM streamLine function.

    Returns the actual seed point count written. Seeds are derived from
    the case's real bounding box (DEC-V61-205 M5 C2) so streamlines
    integrate inside the domain for any geometry — not the legacy
    hardcoded KJ66 external-aero box.
    """
    bbox = _mesh_bbox(case_dir)
    if bbox is not None:
        pts = _seed_points_from_bbox(bbox[0], bbox[1], seed_count)
    else:
        # No mesh points + no manifest bbox → legacy KJ66 box as last resort.
        pts = _LEGACY_KJ66_SEEDS
    pts_block = "\n        ".join(f"({x} {y} {z})" for x, y, z in pts)
    dict_text = f"""\
type            streamLine;
libs            ("libfieldFunctionObjects.so");

executeControl  writeTime;
writeControl    writeTime;

setFormat       vtk;
direction       forward;
lifeTime        10000;
nSubCycle       5;
cloud           particleTracks;
fields          (U p);

seedSampleSet
{{
    type        cloud;
    axis        xyz;
    points
    (
        {pts_block}
    );
}}
"""
    (case_dir / "system" / "streamlinesDict").write_text(
        dict_text, encoding="utf-8"
    )
    return len(pts)


# ─────────────── Container exec ───────────────


def _run_streamlines(case_dir: Path) -> subprocess.CompletedProcess[str]:
    cmd = [
        "docker", "run", "--rm",
        "--entrypoint", "/bin/bash",
        "-v", f"{case_dir}:/case", "-w", "/case",
        IMAGE,
        "-c", f"source {BASHRC} && postProcess -func streamlines -latestTime",
    ]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=600)


def _latest_streamlines_vtp(case_dir: Path) -> Path | None:
    """Return the newest track0.vtp under postProcessing/sets/streamlines."""
    root = case_dir / "postProcessing" / "sets" / "streamlines"
    if not root.is_dir():
        return None
    time_dirs = [p for p in root.iterdir() if p.is_dir()]
    if not time_dirs:
        return None
    # Newest by mtime — OpenFOAM keeps the latest under <time>/.
    time_dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    candidate = time_dirs[0] / "track0.vtp"
    return candidate if candidate.is_file() else None


# ─────────────── Public entry ───────────────


def ensure_streamlines(
    case_dir: Path, *, force: bool = False
) -> StreamlineExportResult:
    """Make sure ``postProcessing/sets/streamlines/<time>/track0.vtp``
    exists and is fresh w.r.t. the latest time directory.

    Raises
    ------
    StreamlineExportError
        No time directories (solver hasn't run), or streamLine failed.
    """
    # Find latest time directory.
    from .vtk_export import _latest_time  # share the helper

    latest = _latest_time(case_dir)
    if latest is None:
        raise StreamlineExportError(
            f"no time directories under {case_dir} — solver hasn't run."
        )
    time_name, time_dir = latest
    if float(time_name) == 0.0:
        raise StreamlineExportError(
            "only initial condition (0/) exists — solver hasn't run."
        )

    # Cache check.
    existing = _latest_streamlines_vtp(case_dir)
    u_field = time_dir / "U"
    if (
        not force
        and existing is not None
        and u_field.is_file()
        and existing.stat().st_mtime >= u_field.stat().st_mtime
    ):
        return StreamlineExportResult(
            track_vtp=existing,
            latest_time=time_name,
            seed_count=0,  # cached · unknown without re-parsing
        )

    seed_count = _build_streamlines_dict(case_dir)
    result = _run_streamlines(case_dir)
    if result.returncode != 0:
        raise StreamlineExportError(
            f"streamLine postProcess failed (exit={result.returncode}):\n"
            f"stderr tail: {result.stderr[-500:]}"
        )

    fresh = _latest_streamlines_vtp(case_dir)
    if fresh is None:
        raise StreamlineExportError(
            "postProcess returned 0 but no track0.vtp on disk.\n"
            f"stdout tail: {result.stdout[-500:]}"
        )
    return StreamlineExportResult(
        track_vtp=fresh, latest_time=time_name, seed_count=seed_count
    )
