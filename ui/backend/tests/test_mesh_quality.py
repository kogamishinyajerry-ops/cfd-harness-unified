"""DEC-V61-122 · mesh-quality analyzer unit tests.

Synthetic polyMesh fixtures live entirely in tmp_path so the tests
are hermetic. Format is the V1 ASCII shape — 3D cube + a 2D plate
+ corrupt/missing variants.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ui.backend.services.mesh_quality import (
    MeshQualityNotAvailableError,
    MeshQualityParseError,
    MeshQualityReport,
    analyze_mesh_quality,
)


_FOAM_HEADER = """\
FoamFile
{
    version     2.0;
    format      ascii;
    class       vectorField;
    location    "constant/polyMesh";
    object      points;
}
"""


def _write_foam_block(path: Path, header_object: str, count: int, body: str) -> None:
    """Write a polyMesh parens-list FOAM file the analyzer recognizes."""
    text = (
        f"{_FOAM_HEADER.replace('object      points', f'object      {header_object}')}"
        f"\n{count}\n(\n{body}\n)\n"
    )
    path.write_text(text, encoding="utf-8")


def _write_boundary(path: Path, patches: list[tuple[str, int, int]]) -> None:
    """Write a polyMesh/boundary file with the given (name, nFaces, startFace) entries."""
    parts = [_FOAM_HEADER.replace('object      points', 'object      boundary')]
    parts.append(f"\n{len(patches)}\n(\n")
    for name, nfaces, start in patches:
        parts.append(
            f"    {name}\n    {{\n"
            f"        type            patch;\n"
            f"        nFaces          {nfaces};\n"
            f"        startFace       {start};\n"
            f"    }}\n"
        )
    parts.append(")\n")
    path.write_text("".join(parts), encoding="utf-8")


def _make_3d_case(tmp_path: Path, *, cells: int = 8, case_id: str = "ldc") -> Path:
    """Build a synthetic 3D case dir with polyMesh files. ``cells`` is
    the cell count — owner entries 0..cells-1 with one-cell-per-face
    ordering. Bounding box is a unit cube."""
    case_dir = tmp_path / case_id
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True, exist_ok=True)
    # Points: 8 corners of a unit cube.
    points = [
        (0.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (1.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
        (1.0, 0.0, 1.0),
        (0.0, 1.0, 1.0),
        (1.0, 1.0, 1.0),
    ]
    pts_body = "\n".join(f"({x} {y} {z})" for x, y, z in points)
    _write_foam_block(polymesh / "points", "points", len(points), pts_body)
    # Owner: total_face_count entries, each one a cell index. The
    # MAX cell index drives cell_count = max+1. Internal + boundary.
    # Use 6*cells faces (every cell-face referenced once via owner;
    # neighbour will declare half of them as internal).
    n_faces = cells * 6
    owner_body = "\n".join(str(i % cells) for i in range(n_faces))
    _write_foam_block(polymesh / "owner", "owner", n_faces, owner_body)
    # Neighbour: declare half the faces as internal (3*cells); the
    # remaining 3*cells are boundary.
    n_internal = cells * 3
    neighbour_body = "\n".join(str(i % cells) for i in range(n_internal))
    _write_foam_block(polymesh / "neighbour", "neighbour", n_internal, neighbour_body)
    # Boundary: split the boundary faces across two patches.
    n_boundary = n_faces - n_internal
    half = n_boundary // 2
    _write_boundary(
        polymesh / "boundary",
        [
            ("walls", half, n_internal),
            ("inlet", n_boundary - half, n_internal + half),
        ],
    )
    return case_dir


def _make_2d_case(tmp_path: Path, *, cells: int = 8) -> Path:
    """Build a synthetic 2D case (z-axis collapsed)."""
    case_dir = tmp_path / "plate2d"
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True, exist_ok=True)
    # 4 corners on z=0 only — z axis collapsed.
    points = [
        (0.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (1.0, 1.0, 0.0),
    ]
    pts_body = "\n".join(f"({x} {y} {z})" for x, y, z in points)
    _write_foam_block(polymesh / "points", "points", len(points), pts_body)
    owner_body = "\n".join(str(i % cells) for i in range(cells * 4))
    _write_foam_block(polymesh / "owner", "owner", cells * 4, owner_body)
    _write_foam_block(polymesh / "neighbour", "neighbour", cells * 2, "\n".join(str(i % cells) for i in range(cells * 2)))
    _write_boundary(polymesh / "boundary", [("walls", cells * 2, cells * 2)])
    return case_dir


# ────────── Happy paths ──────────


def test_analyze_3d_cube_returns_expected_counts(tmp_path):
    case_dir = _make_3d_case(tmp_path, cells=27)
    report = analyze_mesh_quality(case_dir)
    assert isinstance(report, MeshQualityReport)
    assert report.case_id == "ldc"
    assert report.polymesh_present is True
    assert report.point_count == 8
    assert report.cell_count == 27  # max(owner) + 1
    assert report.internal_face_count == 81  # 3 * 27
    assert report.boundary_face_count == 81  # 6*27 - 3*27
    assert report.bounding_box_min == (0.0, 0.0, 0.0)
    assert report.bounding_box_max == (1.0, 1.0, 1.0)
    assert report.bounding_box_volume == 1.0
    assert report.cells_per_unit_volume == 27.0
    assert report.patch_face_counts == {"walls": 40, "inlet": 41}


def test_analyze_2d_plate_collapsed_z_axis_warns(tmp_path):
    case_dir = _make_2d_case(tmp_path, cells=4)
    report = analyze_mesh_quality(case_dir)
    assert report.bounding_box_volume == 0.0
    assert report.cells_per_unit_volume is None
    codes = [w.code for w in report.warnings]
    assert "bb_collapsed_dim" in codes


def test_analyze_dense_mesh_warns(tmp_path):
    case_dir = _make_3d_case(tmp_path, cells=6_000_000)
    report = analyze_mesh_quality(case_dir)
    codes = [w.code for w in report.warnings]
    assert "dense_mesh" in codes


def test_analyze_low_cell_count_warns(tmp_path):
    case_dir = _make_3d_case(tmp_path, cells=10)
    report = analyze_mesh_quality(case_dir)
    codes = [w.code for w in report.warnings]
    assert "cell_count_low" in codes


def test_analyze_zero_face_patch_warns(tmp_path):
    case_dir = _make_3d_case(tmp_path, cells=27)
    polymesh = case_dir / "constant" / "polyMesh"
    _write_boundary(
        polymesh / "boundary",
        [
            ("walls", 0, 0),       # zero faces — should warn
            ("inlet", 162, 0),
        ],
    )
    report = analyze_mesh_quality(case_dir)
    codes = [w.code for w in report.warnings]
    assert "patch_zero_faces" in codes


# ────────── Error paths ──────────


def test_analyze_missing_polymesh_dir_raises_not_available(tmp_path):
    case_dir = tmp_path / "fresh"
    case_dir.mkdir()
    with pytest.raises(MeshQualityNotAvailableError):
        analyze_mesh_quality(case_dir)


def test_analyze_missing_owner_file_raises_not_available(tmp_path):
    case_dir = _make_3d_case(tmp_path)
    (case_dir / "constant" / "polyMesh" / "owner").unlink()
    with pytest.raises(MeshQualityNotAvailableError):
        analyze_mesh_quality(case_dir)


def test_analyze_corrupt_points_count_mismatch_raises_parse_error(tmp_path):
    case_dir = _make_3d_case(tmp_path)
    # Declared count 999 but only 8 actual points → mismatch.
    points_path = case_dir / "constant" / "polyMesh" / "points"
    points_path.write_text(
        _FOAM_HEADER + "\n999\n(\n(0.0 0.0 0.0)\n(1.0 1.0 1.0)\n)\n"
    )
    with pytest.raises(MeshQualityParseError) as exc_info:
        analyze_mesh_quality(case_dir)
    assert exc_info.value.failing_check == "points_count_mismatch"


def test_analyze_unterminated_owner_raises_parse_error(tmp_path):
    case_dir = _make_3d_case(tmp_path)
    owner_path = case_dir / "constant" / "polyMesh" / "owner"
    # Drop the closing ")" so the parser raises.
    text = owner_path.read_text()
    owner_path.write_text(text.replace("\n)\n", "\n"))
    with pytest.raises(MeshQualityParseError) as exc_info:
        analyze_mesh_quality(case_dir)
    assert exc_info.value.failing_check == "owner_unreadable"


def test_analyze_no_neighbour_file_yields_zero_internal_faces(tmp_path):
    case_dir = _make_3d_case(tmp_path)
    # Some degenerate meshes (single cell) have no neighbour file.
    (case_dir / "constant" / "polyMesh" / "neighbour").unlink()
    report = analyze_mesh_quality(case_dir)
    assert report.internal_face_count == 0
    # All faces become boundary in this degenerate case (default
    # _make_3d_case has cells=8, owner = 8*6 = 48 faces).
    assert report.boundary_face_count == 8 * 6


# ────────── Codex R1 P1 (symlink escape) ──────────


def test_analyze_refuses_symlinked_points_file(tmp_path):
    """Codex R1 P1: a planted symlink at polyMesh/points must not be
    followed — otherwise the analyzer (and the AI-coach prefetch) can
    exfiltrate arbitrary host files."""
    case_dir = _make_3d_case(tmp_path)
    points_path = case_dir / "constant" / "polyMesh" / "points"
    # Replace the real points file with a symlink to an outside target.
    outside_target = tmp_path / "outside.txt"
    outside_target.write_text("FoamFile{}\n1\n(\n(0.0 0.0 0.0)\n)\n")
    points_path.unlink()
    points_path.symlink_to(outside_target)
    with pytest.raises(MeshQualityParseError) as exc_info:
        analyze_mesh_quality(case_dir)
    assert exc_info.value.failing_check == "symlink_escape"


# ────────── Codex R1 P2 (truncated block detection) ──────────


def test_analyze_truncated_owner_body_raises_count_mismatch(tmp_path):
    """Codex R1 P2: owner declared count must match parsed entries.
    A truncated owner file otherwise produces a 200 with bogus
    cell_count derived from max(owner)+1."""
    case_dir = _make_3d_case(tmp_path)
    owner_path = case_dir / "constant" / "polyMesh" / "owner"
    # Declared 999 but only 5 entries provided. Properly terminated.
    owner_path.write_text(
        _FOAM_HEADER.replace("object      points", "object      owner")
        + "\n999\n(\n0\n1\n2\n3\n4\n)\n"
    )
    with pytest.raises(MeshQualityParseError) as exc_info:
        analyze_mesh_quality(case_dir)
    assert exc_info.value.failing_check == "owner_count_mismatch"


def test_analyze_truncated_neighbour_body_raises_count_mismatch(tmp_path):
    """Codex R1 P2: neighbour declared count must match parsed entries."""
    case_dir = _make_3d_case(tmp_path)
    neighbour_path = case_dir / "constant" / "polyMesh" / "neighbour"
    neighbour_path.write_text(
        _FOAM_HEADER.replace("object      points", "object      neighbour")
        + "\n777\n(\n0\n1\n2\n)\n"
    )
    with pytest.raises(MeshQualityParseError) as exc_info:
        analyze_mesh_quality(case_dir)
    assert exc_info.value.failing_check == "neighbour_count_mismatch"


def test_analyze_truncated_boundary_raises_count_mismatch(tmp_path):
    """Codex R1 P2: boundary declared patch count must match parsed
    patches when a header is present."""
    case_dir = _make_3d_case(tmp_path)
    boundary_path = case_dir / "constant" / "polyMesh" / "boundary"
    # Declares 5 patches but only 1 patch entry follows.
    boundary_path.write_text(
        _FOAM_HEADER.replace("object      points", "object      boundary")
        + "\n5\n(\n"
        "    walls\n    {\n"
        "        type            patch;\n"
        "        nFaces          12;\n"
        "        startFace       0;\n"
        "    }\n"
        ")\n"
    )
    with pytest.raises(MeshQualityParseError) as exc_info:
        analyze_mesh_quality(case_dir)
    assert exc_info.value.failing_check == "boundary_count_mismatch"


# ────────── Determinism / purity ──────────


def test_analyzer_is_pure_repeatable(tmp_path):
    case_dir = _make_3d_case(tmp_path)
    a = analyze_mesh_quality(case_dir)
    b = analyze_mesh_quality(case_dir)
    assert a.model_dump() == b.model_dump()
