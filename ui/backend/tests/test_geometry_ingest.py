"""Unit tests for ``ui.backend.services.geometry_ingest`` (M5.0)."""

from __future__ import annotations

import io

import pytest
import trimesh

from ui.backend.services.geometry_ingest import (
    canonical_stl_bytes,
    detect_patches,
    ingest_stl,
    load_stl_from_bytes,
    run_health_checks,
)


def _box_stl(size: float = 0.1) -> bytes:
    m = trimesh.creation.box([size, size, size])
    buf = io.BytesIO()
    m.export(buf, file_type="stl")
    return buf.getvalue()


def _open_box_stl() -> bytes:
    """Non-watertight: cube with the first 2 triangles removed (open top)."""
    m = trimesh.creation.box([0.1, 0.1, 0.1])
    open_mesh = trimesh.Trimesh(vertices=m.vertices, faces=m.faces[2:].copy())
    buf = io.BytesIO()
    open_mesh.export(buf, file_type="stl")
    return buf.getvalue()


def test_cube_ingest_passes_with_default_face_warning():
    report = ingest_stl(_box_stl())
    assert report.errors == []
    assert report.is_watertight is True
    assert report.face_count == 12  # 6 sides × 2 triangles
    assert report.is_single_shell is True
    assert report.solid_count == 1
    assert report.unit_guess == "m"
    # Binary-exported STL has no named solids — defaultFaces warning expected.
    assert report.all_default_faces is True
    assert any("defaultFaces" in w for w in report.warnings)
    assert [p.name for p in report.patches] == ["defaultFaces"]


def test_empty_bytes_rejected_with_parse_error():
    report = ingest_stl(b"")
    assert report.errors
    assert "empty" in report.errors[0].lower()
    assert report.face_count == 0


def test_garbage_bytes_rejected_with_parse_error():
    report = ingest_stl(b"this is not an STL file at all, just some garbage\x00\xff")
    assert report.errors  # parse failure
    assert report.face_count == 0


def test_non_watertight_stl_produces_error():
    report = ingest_stl(_open_box_stl())
    assert report.is_watertight is False
    assert any("watertight" in e.lower() for e in report.errors)


def test_unit_guess_mm_band_kicks_in_for_large_extent():
    # 500-unit cube → bbox extent 500 → mm band (250 < 500 ≤ 1e5)
    report = ingest_stl(_box_stl(size=500.0))
    assert report.unit_guess == "mm"


def test_unit_guess_unknown_for_extreme_extent():
    # 1e7-unit cube → bbox extent 1e7 → outside all bands → unknown
    report = ingest_stl(_box_stl(size=1.0e7))
    assert report.unit_guess == "unknown"
    assert any("unit could not be guessed" in w.lower() for w in report.warnings)


def test_canonical_bytes_roundtrip_remains_loadable():
    original = _box_stl()
    loaded, errs = load_stl_from_bytes(original)
    assert errs == []
    canon = canonical_stl_bytes(loaded)
    # Re-load the canonicalized bytes — must still parse + be watertight.
    loaded2, errs2 = load_stl_from_bytes(canon)
    assert errs2 == []
    patches2, all_default2 = detect_patches(loaded2)
    report2 = run_health_checks(loaded=loaded2, patches=patches2, all_default_faces=all_default2)
    assert report2.is_watertight is True
    assert report2.face_count == 12


def test_load_stl_from_bytes_returns_errors_on_garbage():
    loaded, errs = load_stl_from_bytes(b"\x00\x01\x02\x03not stl")
    assert loaded is None
    assert errs
