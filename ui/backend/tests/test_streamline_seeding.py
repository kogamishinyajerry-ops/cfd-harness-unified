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
    _SEED_POLICY_VERSION,
    _bbox_from_points_file,
    _build_streamlines_dict,
    _mesh_bbox,
    _read_seed_policy,
    _seed_grid_from_bbox,
    _streamlines_root,
    _write_seed_policy,
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


# -- mesh bbox source (Codex R0 P2: NO manifest STL-bbox fallback) ------


def test_mesh_bbox_uses_mesh_points(tmp_path: Path):
    _write_points(tmp_path, [(0, 0, 0), (5, 5, 5)])
    assert _mesh_bbox(tmp_path) == ((0.0, 0.0, 0.0), (5.0, 5.0, 5.0))


def test_mesh_bbox_does_not_fall_back_to_manifest_stl_bbox(tmp_path: Path):
    # Codex R0 P2: the ingest STL bbox is the solid body for external-flow
    # cases — seeding it would land inside the obstacle. Binary/unreadable
    # points must yield None (→ caller uses legacy seeds), NOT the manifest.
    poly = tmp_path / "constant" / "polyMesh"
    poly.mkdir(parents=True)
    (poly / "points").write_bytes(b"\x00\x01 binary no triples")
    (tmp_path / "case_manifest.yaml").write_text(
        "ingest_report_summary:\n"
        "  bbox_min: [0.0, 0.0, 0.0]\n"
        "  bbox_max: [10.0, 10.0, 10.0]\n"
    )
    assert _mesh_bbox(tmp_path) is None


# -- seed grid generation (Codex R1 P1: grid, not diagonal) -------------


def test_seed_grid_lies_strictly_inside_bbox(tmp_path: Path):
    bmin, bmax = (0.0, 0.0, 0.0), (10.0, 2.0, 1.0)
    pts = _seed_grid_from_bbox(bmin, bmax)
    assert len(pts) == 5 * 4 * 3  # default nx*ny*nz
    for x, y, z in pts:
        assert 0.0 < x < 10.0
        assert 0.0 < y < 2.0
        assert 0.0 < z < 1.0


def test_seed_grid_covers_fluid_region_of_non_convex_domain(tmp_path: Path):
    # backward_step: solid step occupies x<2 && y<1. A single diagonal would
    # start inside that solid; a grid must place many seeds in the fluid
    # region (x>2 OR y>1) so streamLine keeps enough tracks.
    pts = _seed_grid_from_bbox((0.0, 0.0, 0.0), (10.0, 2.0, 1.0))
    fluid = [(x, y, z) for x, y, z in pts if x > 2.0 or y > 1.0]
    assert len(fluid) >= 20  # broad coverage of the open channel


def test_seed_grid_handles_thin_axis_without_nan(tmp_path: Path):
    # backward_step is ~1 cell thick in z; a zero-width axis collapses to a
    # single mid value rather than producing NaNs.
    pts = _seed_grid_from_bbox((0.0, 0.0, 0.5), (10.0, 2.0, 0.5))
    assert all(z == 0.5 for _, _, z in pts)
    assert all(x == x for x, _, _ in pts)  # no NaN
    assert len(pts) == 5 * 4 * 1  # thin z collapses to one plane


# -- dict integration ---------------------------------------------------


def test_build_dict_uses_mesh_bbox_not_legacy(tmp_path: Path):
    _write_points(tmp_path, [(0, 0, 0), (10, 2, 1)])
    (tmp_path / "system").mkdir()
    n = _build_streamlines_dict(tmp_path)
    assert n == 5 * 4 * 3  # mesh-derived seed grid
    text = (tmp_path / "system" / "streamlines").read_text()
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
    text = (tmp_path / "system" / "streamlines").read_text()
    assert "-2.95" in text


# -- seed-policy cache marker (Codex R0 P1) -----------------------------


def test_seed_policy_marker_roundtrip(tmp_path: Path):
    # No marker yet → None (a pre-fix cache reads as stale).
    assert _read_seed_policy(tmp_path) is None
    _streamlines_root(tmp_path).mkdir(parents=True)
    _write_seed_policy(tmp_path)
    assert _read_seed_policy(tmp_path) == _SEED_POLICY_VERSION


def test_write_seed_policy_noop_without_root(tmp_path: Path):
    # No streamlines output dir → best-effort write is a no-op, no crash.
    _write_seed_policy(tmp_path)
    assert _read_seed_policy(tmp_path) is None


def test_stale_policy_reads_as_mismatch(tmp_path: Path):
    # A cache stamped with the old policy must not equal the current one,
    # so ensure_streamlines re-runs the (now mesh-derived) seeding.
    root = _streamlines_root(tmp_path)
    root.mkdir(parents=True)
    (root / ".seed_policy").write_text("1", encoding="utf-8")
    assert _read_seed_policy(tmp_path) != _SEED_POLICY_VERSION
