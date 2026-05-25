"""DEC-V61-205 (M5 C2): foamToVTK output-dir discovery.

Regression for the bug the M4 live run surfaced: foamToVTK names its output
VTK/<caseMountName>_<timeINDEX>/ (step counter), not the time value. For
t=2.0s at deltaT=5e-3 the dir is case_400, but the old code constructed
VTK/case_2 and 500'd ("internal.vtu missing"). Discovery must glob for the
real dir and pick the highest index carrying internal.vtu.
"""
from __future__ import annotations

from pathlib import Path

from ui.backend.services.case_visualize.vtk_export import (
    _discover_vtk_output_dir,
    _vtk_is_stale,
)


def _mk(case_dir: Path, sub: str, with_internal: bool = True) -> Path:
    d = case_dir / "VTK" / sub
    d.mkdir(parents=True, exist_ok=True)
    if with_internal:
        (d / "internal.vtu").write_text("<VTKFile/>")
    return d


def test_discovers_index_named_dir_not_time_value(tmp_path: Path):
    # the exact bug: time value 2, but foamToVTK wrote case_400
    out = _mk(tmp_path, "case_400")
    assert _discover_vtk_output_dir(tmp_path) == out


def test_picks_highest_index_when_multiple(tmp_path: Path):
    _mk(tmp_path, "case_2")
    hi = _mk(tmp_path, "case_400")
    assert _discover_vtk_output_dir(tmp_path) == hi


def test_ignores_dirs_without_internal_vtu(tmp_path: Path):
    _mk(tmp_path, "case_400", with_internal=False)
    real = _mk(tmp_path, "case_50")
    assert _discover_vtk_output_dir(tmp_path) == real


def test_none_when_no_vtk_dir(tmp_path: Path):
    assert _discover_vtk_output_dir(tmp_path) is None


def test_none_when_no_internal_anywhere(tmp_path: Path):
    _mk(tmp_path, "case_400", with_internal=False)
    assert _discover_vtk_output_dir(tmp_path) is None


def test_stale_true_when_no_output(tmp_path: Path):
    time_dir = tmp_path / "2"
    time_dir.mkdir()
    (time_dir / "U").write_text("U")
    assert _vtk_is_stale(tmp_path, time_dir) is True


def test_stale_false_when_output_newer_than_U(tmp_path: Path):
    time_dir = tmp_path / "2"
    time_dir.mkdir()
    (time_dir / "U").write_text("U")
    out = _mk(tmp_path, "case_400")  # internal.vtu written after U
    assert out.is_dir()
    assert _vtk_is_stale(tmp_path, time_dir) is False


def test_stale_true_when_U_newer_than_output(tmp_path: Path):
    out = _mk(tmp_path, "case_400")  # internal.vtu first
    import os
    import time

    time.sleep(0.01)
    time_dir = tmp_path / "2"
    time_dir.mkdir()
    u = time_dir / "U"
    u.write_text("U")
    # force U mtime strictly newer
    future = (out / "internal.vtu").stat().st_mtime + 10
    os.utime(u, (future, future))
    assert _vtk_is_stale(tmp_path, time_dir) is True
