"""V72.A dam-break extractor unit tests (DEC-V61-237).

Synthetic ascii OpenFOAM cases exercise the fail-closed contract: every
missing/garbled input raises, never a fabricated QoI.
"""
import math
from pathlib import Path

import pytest

from src.dam_break_extractor import (
    DamBreakExtractionError,
    extract_dam_break,
    read_scalar_field,
    read_vector_field,
)

A = 0.1461          # column width [m]
BAND = 0.1 * A      # floor band height
G = 9.81


def _foam_header(cls: str, obj: str, fmt: str = "ascii") -> str:
    return (
        "FoamFile\n{\n    version     2.0;\n"
        f"    format      {fmt};\n"
        f"    class       {cls};\n"
        f"    object      {obj};\n}}\n"
        'dimensions      [0 0 0 0 0 0 0];\n'
    )


def _write_scalar(path: Path, name: str, values, fmt: str = "ascii"):
    body = (
        _foam_header("volScalarField", name, fmt)
        + f"internalField   nonuniform List<scalar> \n{len(values)}\n(\n"
        + "\n".join(f"{v}" for v in values)
        + "\n)\n;\n\nboundaryField\n{\n}\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    (path).write_text(body)


def _write_vector(path: Path, name: str, vectors):
    body = (
        _foam_header("volVectorField", name)
        + f"internalField   nonuniform List<vector> \n{len(vectors)}\n(\n"
        + "\n".join(f"({x} {y} {z})" for x, y, z in vectors)
        + "\n)\n;\n\nboundaryField\n{\n}\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)


def _grid():
    """4x2 cell-centre grid: floor row inside the band, top row outside."""
    xs = [0.5 * A, 1.0 * A, 1.5 * A, 2.0 * A]
    return [(x, 0.5 * BAND, 0.0) for x in xs] + [(x, 5.0 * BAND, 0.0) for x in xs]


def _case(tmp_path: Path, alpha_by_time: dict) -> Path:
    case = tmp_path / "case"
    centres = _grid()
    _write_vector(case / "0" / "C", "C", centres)
    _write_scalar(case / "0" / "V", "V", [1.0e-6] * len(centres))
    for tname, alpha in alpha_by_time.items():
        _write_scalar(case / tname / "alpha.water", "alpha.water", alpha)
    return case


def _extract(case, times):
    return extract_dam_break(
        case, sample_times=times, column_width_a=A, floor_band_y=BAND
    )


class TestHappyPath:
    def test_front_is_max_wet_band_cell(self, tmp_path):
        # floor row wet up to x=1.5A; top row wet everywhere (must be ignored)
        alpha = [1.0, 1.0, 0.8, 0.0] + [1.0, 1.0, 1.0, 1.0]
        case = _case(tmp_path, {"0.086293": alpha})
        m = _extract(case, [0.086293])
        snap = m.snapshots[0]
        assert math.isclose(snap.z_front, 1.5, rel_tol=1e-9)
        assert snap.n_wet_band_cells == 3
        # volume = sum(alpha*V) over ALL cells incl. top row
        assert math.isclose(snap.water_volume, (2.8 + 4.0) * 1e-6, rel_tol=1e-9)

    def test_uniform_alpha_expands_to_mesh_size(self, tmp_path):
        case = _case(tmp_path, {})
        f = case / "0.086293" / "alpha.water"
        f.parent.mkdir(parents=True)
        f.write_text(
            _foam_header("volScalarField", "alpha.water")
            + "internalField   uniform 1;\n\nboundaryField\n{\n}\n"
        )
        m = _extract(case, [0.086293])
        assert m.snapshots[0].z_front == pytest.approx(2.0)


class TestFailClosed:
    def test_missing_time_dir_raises(self, tmp_path):
        case = _case(tmp_path, {"0.086293": [1.0] * 8})
        with pytest.raises(DamBreakExtractionError, match="no time directory"):
            _extract(case, [0.172586])

    def test_ambiguous_time_dirs_raise(self, tmp_path):
        # same numeric time, two formatting variants -> ambiguous, fail-closed
        alpha = [1.0] * 8
        case = _case(tmp_path, {"0.086293": alpha, "0.0862930": alpha})
        with pytest.raises(DamBreakExtractionError, match="ambiguous"):
            _extract(case, [0.086293])

    def test_off_target_write_time_fails_closed(self, tmp_path):
        # Codex R0 P2-2: a run that wrote 0.086 instead of the pinned 0.086293
        # (~1% of the physical time) must NOT be silently graded as the sample
        alpha = [1.0] * 8
        case = _case(tmp_path, {"0.086": alpha})
        with pytest.raises(DamBreakExtractionError, match="no time directory"):
            _extract(case, [0.086293])

    def test_missing_volumes_raises_no_uniform_fallback(self, tmp_path):
        case = _case(tmp_path, {"0.086293": [1.0] * 8})
        (case / "0" / "V").unlink()
        with pytest.raises(DamBreakExtractionError, match="cell-volumes field V"):
            _extract(case, [0.086293])

    def test_missing_centres_raises(self, tmp_path):
        case = _case(tmp_path, {"0.086293": [1.0] * 8})
        (case / "0" / "C").unlink()
        with pytest.raises(DamBreakExtractionError, match="cell-centres field C"):
            _extract(case, [0.086293])

    def test_binary_format_raises(self, tmp_path):
        case = _case(tmp_path, {})
        _write_scalar(
            case / "0.086293" / "alpha.water", "alpha.water", [1.0] * 8, fmt="binary"
        )
        with pytest.raises(DamBreakExtractionError, match="writeFormat"):
            _extract(case, [0.086293])

    def test_cell_count_mismatch_raises(self, tmp_path):
        case = _case(tmp_path, {"0.086293": [1.0] * 5})  # 5 != 8 mesh cells
        with pytest.raises(DamBreakExtractionError, match="cell count"):
            _extract(case, [0.086293])

    def test_splash_guard_too_few_wet_cells(self, tmp_path):
        # only 1 wet band cell (< 3) -> refuse to report a front
        alpha = [1.0, 0.0, 0.0, 0.0] + [0.0] * 4
        case = _case(tmp_path, {"0.086293": alpha})
        with pytest.raises(DamBreakExtractionError, match="splash guard"):
            _extract(case, [0.086293])

    def test_header_count_mismatch_raises(self, tmp_path):
        case = _case(tmp_path, {})
        f = case / "0.086293" / "alpha.water"
        f.parent.mkdir(parents=True)
        f.write_text(
            _foam_header("volScalarField", "alpha.water")
            + "internalField   nonuniform List<scalar> \n9\n(\n1\n1\n)\n;\n"
        )
        with pytest.raises(DamBreakExtractionError, match="header count"):
            _extract(case, [0.086293])


class TestParsers:
    def test_vector_roundtrip(self, tmp_path):
        p = tmp_path / "C"
        vecs = [(0.1, 0.2, 0.3), (1e-3, -2e-3, 0.0)]
        _write_vector(p, "C", vecs)
        assert read_vector_field(p) == [pytest.approx(v) for v in vecs]

    def test_scalar_roundtrip(self, tmp_path):
        p = tmp_path / "V"
        _write_scalar(p, "V", [1.5e-6, 2.5e-6])
        assert read_scalar_field(p) == [pytest.approx(1.5e-6), pytest.approx(2.5e-6)]
