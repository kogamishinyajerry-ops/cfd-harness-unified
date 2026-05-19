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


def _vtk_output_dir(case_dir: Path, time_name: str) -> Path:
    return case_dir / "VTK" / f"case_{time_name}"


def _vtk_is_stale(case_dir: Path, time_name: str, time_dir: Path) -> bool:
    """Return True if the cached VTK output is missing or older than the
    latest U field (i.e. solver re-ran since last export)."""
    target = _vtk_output_dir(case_dir, time_name)
    if not target.is_dir():
        return True
    internal = target / "internal.vtu"
    if not internal.is_file():
        return True
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

    if not force and not _vtk_is_stale(case_dir, time_name, time_dir):
        out = _vtk_output_dir(case_dir, time_name)
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

    out = _vtk_output_dir(case_dir, time_name)
    if not (out / "internal.vtu").is_file():
        raise VtkExportError(
            f"foamToVTK returned 0 but {out / 'internal.vtu'} missing.\n"
            f"stdout tail: {result.stdout[-500:]}"
        )
    return VtkExportResult(
        case_time_dir=out,
        internal_vtu=out / "internal.vtu",
        boundary_dir=out / "boundary",
        latest_time=time_name,
    )
