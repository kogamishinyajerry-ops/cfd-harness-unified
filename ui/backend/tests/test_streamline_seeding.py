"""DEC-V61-205 (M5 C2) bug #4: mesh-derived streamline seeding.

The legacy seeder hardcoded an x=-2.95 line (KJ66 external-aero box), so
streamLine seeded OUTSIDE every other mesh → a single degenerate track
(NumberOfPoints=1, U=0) and the streamline overlay never rendered. Seeds
must now come from the case's real bounding box (mesh points → manifest →
legacy fallback).
"""
from __future__ import annotations

from pathlib import Path

from ui.backend.services.case_visualize.streamline_export import (
    _bbox_from_manifest,
    _bbox_from_points_file,
    _build_streamlines_dict,
    _mesh_bbox,
    _seed_points_from_bbox,
)

_POINTS_HEADER = (
    "FoamFile { version 2.0; format ascii; class vectorField; "
    'location "constant/polyMesh"; object points; }\n'
)


def _write_points(case_dir: Path, pts: list[tuple[float, float, float]]) -> None:
    poly = case_dir / "constant" / "polyMesh"
    poly.mkdir(parents=True, exist_ok=True)
    body = "\n".join(f"({x} {y} {z})" for x, y, z in pts)
    (poly / "points").write_text(
        f"{_POINTS_HEADER}{len(pts)}\n(\n{body}\n)\n"
    )


# -- bbox from points ---------------------------------------------------


def test_bbox_from_points_file_reads_min_max(tmp_path: Path):
    _write_points(tmp_path, [(0, 0, 0), (10, 2, 1), (3, 1, 0.5)])
    box = _bbox_from_points_file(tmp_path / "constant" / "polyMesh" / "points")
    assert box == ((0.0, 0.0, 0.0), (10.0, 2.0, 1.0))


def test_bbox_from_points_file_none_when_missing(tmp_path: Path):
    assert _bbox_from_points_file(tmp_path / "nope" / "points") is None


def test_bbox_from_points_file_none_when_binary(tmp_path: Path):
    poly = tmp_path / "constant" / "polyMesh"
    poly.mkdir(parents=True)
    # No parenthesized triples → binary/opaque → None (caller falls back).
    (poly / "points").write_bytes(b"\x00\x01\x02 binary blob no triples")
    assert _bbox_from_points_file(poly / "points") is None


# -- bbox from manifest -------------------------------------------------


def test_bbox_from_manifest_reads_ingest_summary(tmp_path: Path):
    (tmp_path / "case_manifest.yaml").write_text(
        "ingest_report_summary:\n"
        "  bbox_min: [0.0, 0.0, 0.0]\n"
        "  bbox_max: [10.0, 2.0, 1.0]\n"
    )
    assert _bbox_from_manifest(tmp_path) == (
        (0.0, 0.0, 0.0),
        (10.0, 2.0, 1.0),
    )


def test_mesh_bbox_prefers_points_over_manifest(tmp_path: Path):
    # Points say [0..5]; manifest says [0..10]. Mesh extent wins.
    _write_points(tmp_path, [(0, 0, 0), (5, 5, 5)])
    (tmp_path / "case_manifest.yaml").write_text(
        "ingest_report_summary:\n"
        "  bbox_min: [0.0, 0.0, 0.0]\n"
        "  bbox_max: [10.0, 10.0, 10.0]\n"
    )
    assert _mesh_bbox(tmp_path) == ((0.0, 0.0, 0.0), (5.0, 5.0, 5.0))


# -- seed generation ----------------------------------------------------


def test_seed_points_lie_strictly_inside_bbox(tmp_path: Path):
    bmin, bmax = (0.0, 0.0, 0.0), (10.0, 2.0, 1.0)
    pts = _seed_points_from_bbox(bmin, bmax, 12)
    assert len(pts) == 12
    for x, y, z in pts:
        assert 0.0 < x < 10.0
        assert 0.0 < y < 2.0
        assert 0.0 < z < 1.0
    # Spans the interior diagonal (first near min-corner, last near max).
    assert pts[0][0] < pts[-1][0]
    assert pts[0] != pts[-1]


def test_seed_points_handle_thin_axis_without_nan(tmp_path: Path):
    # backward_step is ~1 cell thick in z; a zero-width axis must not NaN.
    pts = _seed_points_from_bbox((0.0, 0.0, 0.5), (10.0, 2.0, 0.5), 8)
    assert all(z == 0.5 for _, _, z in pts)
    assert all(x == x for x, _, _ in pts)  # no NaN


# -- dict integration ---------------------------------------------------


def test_build_dict_uses_mesh_bbox_not_legacy(tmp_path: Path):
    _write_points(tmp_path, [(0, 0, 0), (10, 2, 1)])
    (tmp_path / "system").mkdir()
    n = _build_streamlines_dict(tmp_path)
    assert n == 12
    text = (tmp_path / "system" / "streamlinesDict").read_text()
    # Legacy KJ66 seeds were at x=-2.95; the mesh-derived seeds are in
    # x∈(0,10) so the old marker must be gone.
    assert "-2.95" not in text
    assert "type            streamLine;" in text
    assert "seedSampleSet" in text


def test_build_dict_falls_back_to_legacy_without_bbox(tmp_path: Path):
    (tmp_path / "system").mkdir()
    # No polyMesh/points, no manifest → legacy KJ66 box.
    n = _build_streamlines_dict(tmp_path)
    assert n == 8
    text = (tmp_path / "system" / "streamlinesDict").read_text()
    assert "-2.95" in text
