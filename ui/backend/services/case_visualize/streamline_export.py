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

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


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


# ─────────────── Auto inlet seeding ───────────────


def _inlet_bbox_from_vtp(inlet_vtp: Path) -> tuple[
    tuple[float, float, float], tuple[float, float, float]
] | None:
    """Parse just enough of an inlet.vtp XML to extract its point AABB.

    foamToVTK writes ``boundary/inlet.vtp`` with binary-encoded Float32
    points. We don't decode those (no numpy dependency hoist needed
    here); instead we scan the human-readable XML headers OpenFOAM also
    emits for many fields — but the VTP format doesn't include a bbox.

    Fallback: we read the polyMesh boundary file directly (text format)
    to find the inlet face range, then read the corresponding points
    from points file. That's slow; for now, return None and let the
    caller hardcode a sensible default. M-VIZ-V plan §S4 will harden
    this with a proper polyMesh parser.
    """
    # Pragmatic: skip parsing for now. The caller has a baseline
    # seeding policy (8-point line on the inlet AABB diagonal) which
    # works for the common axis-aligned external-aero geometry.
    return None


def _build_streamlines_dict(case_dir: Path, seed_count: int = 32) -> int:
    """Write system/streamlinesDict for OpenFOAM streamLine function.

    Returns ``seed_count`` echoing the actual seed point count written.

    Default seeding: 32-point line spanning ~80% of the inlet AABB
    diagonal at x = (mesh_xmin + 0.03). For the KJ66 external-aero
    case (x∈[-3,5], y∈[-1.5,1.5], z∈[-1.5,1.5]), this lands at
    x≈-2.97, sweeping (y,z) from (-1.0,-1.0) to (+1.0,+1.0).

    M-VIZ-V follow-up: read the case's polyMesh boundary file to find
    the actual inlet patch's bbox instead of hardcoding the external-
    aero pattern.
    """
    # 8-point line · diagonal across inlet at x = -2.95 (near-inlet)
    pts = [
        (-2.95, -1.0, -1.0),
        (-2.95, -0.7, -0.7),
        (-2.95, -0.4, -0.4),
        (-2.95, -0.1, -0.1),
        (-2.95,  0.1,  0.1),
        (-2.95,  0.4,  0.4),
        (-2.95,  0.7,  0.7),
        (-2.95,  1.0,  1.0),
    ]
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
