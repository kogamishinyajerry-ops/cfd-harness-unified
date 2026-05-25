"""VTK XML exporter — runs ``foamToVTK -latestTime`` inside the
OpenFOAM container and returns paths to the resulting .vtu / .vtp files.

Produced layout (per OpenFOAM v2312):

    <case>/VTK/
        case_<time>/
            internal.vtu                    # full volume mesh + fields
            boundary/
                engine.vtp                  # per-patch surface mesh + fields
                inlet.vtp
                outlet.vtp
                farfield.vtp
            boundary.vtm
        case_<time>.vtm

The function caches: if ``VTK/case_<latestTime>/`` already exists and is
newer than the latest time directory's U field, no re-export is run.

This is the B2.5 foundation for:
  • surface_export — pulls boundary/<patch>.vtp for the Post viewport
  • streamline_export — uses internal.vtu via OpenFOAM streamLine function

Mirrors velocity_slice.py's container-stage pattern (DEC-V61-097) so
behaviour is consistent across the case_visualize services.
"""
from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


class VtkExportError(RuntimeError):
    """Raised when foamToVTK fails or pre-conditions aren't met."""


IMAGE = os.environ.get("CFD_OPENFOAM_IMAGE", "opencfd/openfoam-default:2312")
BASHRC = "/usr/lib/openfoam/openfoam2312/etc/bashrc"
_TIME_DIR_RE = re.compile(r"^\d+(\.\d+)?$")


@dataclass(frozen=True)
class VtkExportResult:
    """Resolved on-disk paths after a successful foamToVTK pass."""

    case_time_dir: Path  # VTK/case_<time>/
    internal_vtu: Path  # VTK/case_<time>/internal.vtu
    boundary_dir: Path  # VTK/case_<time>/boundary/
    latest_time: str


def _list_time_dirs(case_dir: Path) -> list[tuple[float, Path]]:
    """Return [(time_float, time_dir_path), ...] sorted ascending."""
    out: list[tuple[float, Path]] = []
    for child in case_dir.iterdir():
        if not child.is_dir():
            continue
        if _TIME_DIR_RE.fullmatch(child.name):
            out.append((float(child.name), child))
    out.sort()
    return out


def _latest_time(case_dir: Path) -> tuple[str, Path] | None:
    times = _list_time_dirs(case_dir)
    if not times:
        return None
    _, td = times[-1]
    return td.name, td


def _u_field_path(time_dir: Path) -> Path | None:
    p = time_dir / "U"
    return p if p.is_file() else None


def _discover_vtk_output_dir(case_dir: Path) -> Path | None:
    """Find the foamToVTK output dir that carries internal.vtu.

    DEC-V61-205 (M5 C2) fix: foamToVTK names its output
    ``VTK/<caseMountName>_<timeINDEX>/`` — the time **index** (step
    counter), NOT the time value. The case mounts at ``/case`` so the
    prefix is ``case``; for t=2.0s at deltaT=5e-3 the dir is ``case_400``,
    not ``case_2``. Constructing ``case_<time_value>`` therefore missed
    the real output and 500'd ("internal.vtu missing") on any case whose
    time index ≠ time value. Discover it instead: ``-latestTime`` writes
    exactly one such dir, so pick the one with internal.vtu and the
    highest numeric index suffix.
    """
    vtk_dir = case_dir / "VTK"
    if not vtk_dir.is_dir():
        return None
    candidates: list[tuple[int, Path]] = []
    for child in vtk_dir.iterdir():
        if child.is_dir() and (child / "internal.vtu").is_file():
            m = re.search(r"_(\d+)$", child.name)
            candidates.append((int(m.group(1)) if m else -1, child))
    if not candidates:
        return None
    candidates.sort()
    return candidates[-1][1]


def _vtk_is_stale(case_dir: Path, time_dir: Path) -> bool:
    """Return True if the cached VTK output is missing or older than the
    latest U field (i.e. solver re-ran since last export)."""
    target = _discover_vtk_output_dir(case_dir)
    if target is None:
        return True
    internal = target / "internal.vtu"
    u_field = _u_field_path(time_dir)
    if u_field is None:
        return False  # no U yet; nothing fresher exists either
    return internal.stat().st_mtime < u_field.stat().st_mtime


def _run_foam_to_vtk(case_dir: Path) -> subprocess.CompletedProcess[str]:
    cmd = [
        "docker", "run", "--rm",
        "--entrypoint", "/bin/bash",
        "-v", f"{case_dir}:/case", "-w", "/case",
        IMAGE,
        "-c", f"source {BASHRC} && foamToVTK -latestTime",
    ]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=600)


def ensure_vtk_output(case_dir: Path, *, force: bool = False) -> VtkExportResult:
    """Make sure VTK/case_<latestTime>/ exists and is fresh. Returns the
    paths the caller needs.

    Raises
    ------
    VtkExportError
        Case has no time directories (solver hasn't run), or foamToVTK
        failed in the container.
    """
    latest = _latest_time(case_dir)
    if latest is None:
        raise VtkExportError(
            f"no time directories under {case_dir} — solver hasn't run yet."
        )
    time_name, time_dir = latest
    if float(time_name) == 0.0:
        raise VtkExportError(
            "only initial condition (0/) exists — solver hasn't run yet."
        )

    if not force and not _vtk_is_stale(case_dir, time_dir):
        out = _discover_vtk_output_dir(case_dir)
        if out is not None:
            return VtkExportResult(
                case_time_dir=out,
                internal_vtu=out / "internal.vtu",
                boundary_dir=out / "boundary",
                latest_time=time_name,
            )

    result = _run_foam_to_vtk(case_dir)
    if result.returncode != 0:
        raise VtkExportError(
            f"foamToVTK failed (exit={result.returncode}):\n"
            f"stderr tail: {result.stderr[-500:]}"
        )

    out = _discover_vtk_output_dir(case_dir)
    if out is None or not (out / "internal.vtu").is_file():
        raise VtkExportError(
            f"foamToVTK returned 0 but no VTK/case_*/internal.vtu found under "
            f"{case_dir / 'VTK'}.\nstdout tail: {result.stdout[-500:]}"
        )
    return VtkExportResult(
        case_time_dir=out,
        internal_vtu=out / "internal.vtu",
        boundary_dir=out / "boundary",
        latest_time=time_name,
    )
