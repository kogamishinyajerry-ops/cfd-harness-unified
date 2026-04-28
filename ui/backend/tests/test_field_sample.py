"""Tests for /api/cases/{id}/results/{run_id}/field/{name}
(M-RENDER-API B.3 · DEC-V61-095 spec_v2 §B.3).

Tier-A scope is binary float32 stream output (the glTF-with-COLOR_0
upgrade is M-VIZ.results). Tests synthesise OpenFOAM-style scalar field
files inline so M5.1/M6.0/M7 don't need to actually run.
"""
from __future__ import annotations

import os
import struct
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from ui.backend.main import app
from ui.backend.services.case_scaffold import template_clone
from ui.backend.services.render import (
    FieldSampleError,
    build_field_payload,
)
from ui.backend.services.render import field_sample as field_sample_mod


_NONUNIFORM_SCALAR_FIELD = """\
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "{run_id}";
    object      {name};
}}

dimensions      [0 2 -2 0 0 0 0];

internalField   nonuniform List<scalar>
{count}
(
{values}
)
;

boundaryField
{{
    inlet
    {{
        type   fixedValue;
        value  uniform 1;
    }}
    outlet
    {{
        type   zeroGradient;
    }}
}}
"""


def _stage_field(
    case_dir: Path,
    run_id: str,
    name: str,
    values: np.ndarray,
) -> Path:
    """Write a synthetic OpenFOAM scalar field at <case_dir>/<run_id>/<name>."""
    body = "\n".join(f"{v}" for v in values)
    text = _NONUNIFORM_SCALAR_FIELD.format(
        run_id=run_id, name=name, count=len(values), values=body,
    )
    run_dir = case_dir / run_id
    run_dir.mkdir(parents=True)
    field_path = run_dir / name
    field_path.write_text(text, encoding="utf-8")
    return field_path


@pytest.fixture
def isolated_imported(tmp_path: Path, monkeypatch):
    drafts = tmp_path / "user_drafts"
    imported = drafts / "imported"
    imported.mkdir(parents=True)
    monkeypatch.setattr(template_clone, "DRAFTS_DIR", drafts)
    monkeypatch.setattr(template_clone, "IMPORTED_DIR", imported)
    return imported


# ───────── service: parse + cache ─────────


def test_build_field_payload_parses_nonuniform_scalar_list(isolated_imported: Path):
    case_id = "imported_2026-04-28T00-00-00Z_field"
    case_dir = isolated_imported / case_id
    case_dir.mkdir()
    values = np.array([1.0, 2.5, 3.14, -0.5, 100.0], dtype=np.float32)
    _stage_field(case_dir, "run_001", "p", values)

    result = build_field_payload(case_id, "run_001", "p")
    assert result.point_count == 5
    assert result.status == "miss"
    raw = result.cache_path.read_bytes()
    assert len(raw) == 5 * 4
    # Round-trip the binary back into a float32 array and compare exactly.
    decoded = np.frombuffer(raw, dtype=np.float32)
    np.testing.assert_array_equal(decoded, values)


def test_build_field_payload_cache_hit(isolated_imported: Path):
    case_id = "imported_2026-04-28T00-00-00Z_fieldhit"
    case_dir = isolated_imported / case_id
    case_dir.mkdir()
    _stage_field(case_dir, "run_002", "T",
                 np.array([300.0, 301.5, 299.7], dtype=np.float32))

    first = build_field_payload(case_id, "run_002", "T")
    second = build_field_payload(case_id, "run_002", "T")
    assert first.status == "miss"
    assert second.status == "hit"
    assert second.point_count == first.point_count


def test_build_field_payload_invalidates_on_mtime(isolated_imported: Path):
    case_id = "imported_2026-04-28T00-00-00Z_fieldinval"
    case_dir = isolated_imported / case_id
    case_dir.mkdir()
    field_path = _stage_field(
        case_dir, "run_003", "k",
        np.array([0.1, 0.2], dtype=np.float32),
    )
    first = build_field_payload(case_id, "run_003", "k")

    bumped = first.cache_path.stat().st_mtime + 5.0
    os.utime(field_path, (bumped, bumped))

    second = build_field_payload(case_id, "run_003", "k")
    assert second.status == "rebuild"


# ───────── service: failure paths ─────────


def test_build_field_payload_404_for_unknown_case(isolated_imported: Path):
    with pytest.raises(FieldSampleError) as excinfo:
        build_field_payload("imported_unknown", "run_001", "p")
    assert excinfo.value.failing_check == "case_not_found"


def test_build_field_payload_404_for_unsafe_case_id(isolated_imported: Path):
    with pytest.raises(FieldSampleError) as excinfo:
        build_field_payload("bad@@id", "run_001", "p")
    assert excinfo.value.failing_check == "case_not_found"


def test_build_field_payload_404_when_run_dir_missing(isolated_imported: Path):
    case_id = "imported_2026-04-28T00-00-00Z_norun"
    (isolated_imported / case_id).mkdir()
    with pytest.raises(FieldSampleError) as excinfo:
        build_field_payload(case_id, "run_does_not_exist", "p")
    assert excinfo.value.failing_check == "run_not_found"


def test_build_field_payload_404_when_field_file_missing(isolated_imported: Path):
    case_id = "imported_2026-04-28T00-00-00Z_nofield"
    case_dir = isolated_imported / case_id
    case_dir.mkdir()
    (case_dir / "run_001").mkdir()
    with pytest.raises(FieldSampleError) as excinfo:
        build_field_payload(case_id, "run_001", "missing_field")
    assert excinfo.value.failing_check == "field_not_found"


def test_build_field_payload_422_on_uniform_field_unsupported(
    isolated_imported: Path,
):
    case_id = "imported_2026-04-28T00-00-00Z_uniform"
    case_dir = isolated_imported / case_id
    case_dir.mkdir()
    run_dir = case_dir / "run_001"
    run_dir.mkdir()
    (run_dir / "p").write_text(
        "FoamFile{}\ninternalField   uniform 0;\n",
        encoding="utf-8",
    )
    with pytest.raises(FieldSampleError) as excinfo:
        build_field_payload(case_id, "run_001", "p")
    assert excinfo.value.failing_check == "field_unsupported"


def test_build_field_payload_422_on_garbage_field_file(isolated_imported: Path):
    case_id = "imported_2026-04-28T00-00-00Z_garbagefield"
    case_dir = isolated_imported / case_id
    case_dir.mkdir()
    run_dir = case_dir / "run_001"
    run_dir.mkdir()
    (run_dir / "p").write_text("definitely not OpenFOAM", encoding="utf-8")
    with pytest.raises(FieldSampleError) as excinfo:
        build_field_payload(case_id, "run_001", "p")
    assert excinfo.value.failing_check == "field_parse_error"


def test_build_field_payload_rejects_traversal_in_run_id(isolated_imported: Path):
    case_id = "imported_2026-04-28T00-00-00Z_trav"
    (isolated_imported / case_id).mkdir()
    with pytest.raises(FieldSampleError) as excinfo:
        build_field_payload(case_id, "../etc", "p")
    # Either run_not_found (validator firing) — both classify as 404
    assert excinfo.value.failing_check == "run_not_found"


def test_build_field_payload_rejects_traversal_in_field_name(
    isolated_imported: Path,
):
    case_id = "imported_2026-04-28T00-00-00Z_travf"
    (isolated_imported / case_id).mkdir()
    with pytest.raises(FieldSampleError) as excinfo:
        build_field_payload(case_id, "run_001", "../passwd")
    assert excinfo.value.failing_check == "field_not_found"


def test_build_field_payload_aborts_on_source_vanish(
    isolated_imported: Path, monkeypatch,
):
    """Round-4 Codex regression: if the source disappears between
    temp-write and pre-replace stat, the helper must NOT crash with
    a raw FileNotFoundError, and the temp must be cleaned up.

    Without the OSError-tolerant _current_mtime() guard the helper
    would propagate FileNotFoundError, bypass the failing_check
    translator, and leave a .tmp.<hex> artifact in .render_cache."""
    case_id = "imported_2026-04-28T00-00-00Z_source_vanish"
    case_dir = isolated_imported / case_id
    case_dir.mkdir()
    field_path = _stage_field(
        case_dir, "run_001", "p",
        np.array([1.0, 2.0, 3.0], dtype=np.float32),
    )
    real_write_bytes = Path.write_bytes
    deleted_state = {"deleted": False}

    def patched_write_bytes(self: Path, data: bytes, *args, **kwargs):
        result = real_write_bytes(self, data, *args, **kwargs)
        if ".tmp." in self.name and not deleted_state["deleted"]:
            field_path.unlink()
            deleted_state["deleted"] = True
        return result
    monkeypatch.setattr(Path, "write_bytes", patched_write_bytes)

    with pytest.raises(FieldSampleError) as excinfo:
        build_field_payload(case_id, "run_001", "p")
    assert excinfo.value.failing_check == "field_parse_error"
    assert "vanished" in excinfo.value.message
    cache_dir = case_dir / ".render_cache"
    if cache_dir.exists():
        leftovers = sorted(p.name for p in cache_dir.iterdir())
        assert leftovers == [], (
            f"temp/cache file leaked after source-vanish: {leftovers}"
        )


def test_build_field_payload_aborts_on_pre_replace_source_mutation(
    isolated_imported: Path, monkeypatch,
):
    """Round-4 Finding 3 closure: the guarded atomic write checks
    source mtime BEFORE os.replace so a stale cache is never made
    visible to concurrent readers. Simulate by monkey-patching the
    write_bytes step to bump source mtime between temp-write and
    pre-replace stat."""
    case_id = "imported_2026-04-28T00-00-00Z_pre_replace_race"
    case_dir = isolated_imported / case_id
    case_dir.mkdir()
    field_path = _stage_field(
        case_dir, "run_001", "p",
        np.array([1.0, 2.0, 3.0], dtype=np.float32),
    )
    # Hook ``Path.write_bytes`` so that immediately after the temp-write
    # step inside the guarded helper, the source mtime is bumped — the
    # subsequent pre-replace stat will see the mismatch and abort.
    real_write_bytes = Path.write_bytes
    bump_state = {"bumped": False}

    def patched_write_bytes(self: Path, data: bytes, *args, **kwargs):
        result = real_write_bytes(self, data, *args, **kwargs)
        # only mutate after the temp file is written, not when the
        # service writes the field source itself.
        if ".tmp." in self.name and not bump_state["bumped"]:
            bumped = field_path.stat().st_mtime + 5.0
            os.utime(field_path, (bumped, bumped))
            bump_state["bumped"] = True
        return result
    monkeypatch.setattr(Path, "write_bytes", patched_write_bytes)

    with pytest.raises(FieldSampleError) as excinfo:
        build_field_payload(case_id, "run_001", "p")
    assert excinfo.value.failing_check == "field_parse_error"
    assert "before atomic replace" in excinfo.value.message
    # No cache file should exist (pre-replace abort cleaned up the temp
    # and never replaced the cache).
    cache = case_dir / ".render_cache" / "field-run_001-p.bin"
    assert not cache.exists()


def test_build_field_payload_rejects_symlink_escaping_case_dir(
    isolated_imported: Path, tmp_path: Path,
):
    """Round-2 Finding 1: symlink under a valid run_id pointing outside
    the case dir must be rejected — segment validators only catch literal
    traversal in URL path segments, not symlink redirection."""
    case_id = "imported_2026-04-28T00-00-00Z_symlink"
    case_dir = isolated_imported / case_id
    case_dir.mkdir()
    run_dir = case_dir / "run_evil"
    run_dir.mkdir()
    outside = tmp_path / "outside_secret.txt"
    outside.write_text("not a foam field", encoding="utf-8")
    # a symlink under the run dir pointing at an arbitrary file.
    (run_dir / "p").symlink_to(outside)

    with pytest.raises(FieldSampleError) as excinfo:
        build_field_payload(case_id, "run_evil", "p")
    # resolve+relative_to fails → field_not_found (containment-collapsed).
    assert excinfo.value.failing_check == "field_not_found"


# ───────── route ─────────


def test_get_case_field_returns_binary_float32_stream(isolated_imported: Path):
    case_id = "imported_2026-04-28T00-00-00Z_routefield"
    case_dir = isolated_imported / case_id
    case_dir.mkdir()
    values = np.array([1.5, 2.5, 3.5, 4.5], dtype=np.float32)
    _stage_field(case_dir, "run_route", "p", values)

    client = TestClient(app)
    response = client.get(f"/api/cases/{case_id}/results/run_route/field/p")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/octet-stream")
    assert response.headers.get("x-field-point-count") == "4"
    assert int(response.headers["content-length"]) == 16
    decoded = np.frombuffer(response.content, dtype=np.float32)
    np.testing.assert_array_equal(decoded, values)


def test_get_case_field_404_for_unknown_case():
    client = TestClient(app)
    response = client.get("/api/cases/imported_unknown/results/run_001/field/p")
    assert response.status_code == 404


def test_get_case_field_422_on_uniform(isolated_imported: Path):
    case_id = "imported_2026-04-28T00-00-00Z_route_uniform"
    case_dir = isolated_imported / case_id
    case_dir.mkdir()
    run_dir = case_dir / "run_001"
    run_dir.mkdir()
    (run_dir / "p").write_text(
        "FoamFile{}\ninternalField   uniform 5;\n",
        encoding="utf-8",
    )
    client = TestClient(app)
    response = client.get(f"/api/cases/{case_id}/results/run_001/field/p")
    assert response.status_code == 422


def test_get_case_field_byte_equal_on_cache_hit(isolated_imported: Path):
    case_id = "imported_2026-04-28T00-00-00Z_routecachehit"
    case_dir = isolated_imported / case_id
    case_dir.mkdir()
    _stage_field(case_dir, "run_x", "Umag",
                 np.array([10.0, 20.0, 30.0], dtype=np.float32))

    client = TestClient(app)
    first = client.get(f"/api/cases/{case_id}/results/run_x/field/Umag")
    second = client.get(f"/api/cases/{case_id}/results/run_x/field/Umag")
    assert first.status_code == 200
    assert second.content == first.content


# ───────── parser corner cases ─────────


def test_parser_handles_scientific_notation(isolated_imported: Path):
    case_id = "imported_2026-04-28T00-00-00Z_scientific"
    case_dir = isolated_imported / case_id
    case_dir.mkdir()
    run_dir = case_dir / "run_001"
    run_dir.mkdir()
    text = """\
FoamFile{}

internalField   nonuniform List<scalar>
3
(
1.5e-3
-2.0e+5
3.14
)
;
"""
    (run_dir / "p").write_text(text, encoding="utf-8")
    result = build_field_payload(case_id, "run_001", "p")
    decoded = np.frombuffer(result.cache_path.read_bytes(), dtype=np.float32)
    assert decoded.shape == (3,)
    assert decoded[0] == pytest.approx(1.5e-3)
    assert decoded[1] == pytest.approx(-2.0e5)
    assert decoded[2] == pytest.approx(3.14)


def test_parser_rejects_count_mismatch(isolated_imported: Path):
    case_id = "imported_2026-04-28T00-00-00Z_mismatch"
    case_dir = isolated_imported / case_id
    case_dir.mkdir()
    run_dir = case_dir / "run_001"
    run_dir.mkdir()
    text = """\
FoamFile{}

internalField   nonuniform List<scalar>
5
(
1.0
2.0
)
;
"""
    (run_dir / "p").write_text(text, encoding="utf-8")
    with pytest.raises(FieldSampleError) as excinfo:
        build_field_payload(case_id, "run_001", "p")
    assert excinfo.value.failing_check == "field_parse_error"
