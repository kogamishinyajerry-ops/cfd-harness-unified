"""Tests for /api/demo-fixtures (M-PANELS Step 10 visual-smoke entry).

Covers:
  - GET /api/demo-fixtures            → catalogue (filters out missing-on-disk)
  - POST /api/demo-fixtures/<n>/import → happy path import
  - POST /api/demo-fixtures/bogus/import → 404 (unknown name)
  - missing-on-disk fixture → 500 (operator fault, not user fault)
  - Codex Round 6 P2 regression: stale size_bytes after fixture removal
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

from ui.backend.main import app
from ui.backend.routes import demo_fixtures as demo_mod


client = TestClient(app)


@pytest.fixture
def isolated_fixture_root(tmp_path: Path, monkeypatch) -> Iterator[Path]:
    """Redirect the fixture root + repopulate the catalogue with copies
    of the real on-disk STLs so tests can mutate the directory without
    touching the repo's examples/imports/.
    """
    fake_root = tmp_path / "fixtures"
    fake_root.mkdir()
    real_root = demo_mod._FIXTURE_ROOT
    for fx in demo_mod._FIXTURES.values():
        src = real_root / fx.filename
        if src.exists():
            (fake_root / fx.filename).write_bytes(src.read_bytes())
    monkeypatch.setattr(demo_mod, "_FIXTURE_ROOT", fake_root)
    demo_mod._refresh_sizes()
    yield fake_root
    # Restore original sizes so other tests see the real catalogue.
    demo_mod._refresh_sizes()


def test_list_demo_fixtures_returns_catalogue(isolated_fixture_root: Path) -> None:
    """Happy path: every checked-in fixture appears with its real size."""
    r = client.get("/api/demo-fixtures")
    assert r.status_code == 200
    body = r.json()
    names = {fx["name"] for fx in body}
    assert names == {"ldc_box", "cylinder", "naca0012"}
    for fx in body:
        assert fx["size_bytes"] > 0
        assert fx["filename"].endswith(".stl")
        assert fx["title"]
        assert fx["description"]


def test_list_demo_fixtures_hides_missing_on_disk(isolated_fixture_root: Path) -> None:
    """Codex Round 6 P2 regression guard: removing a fixture from disk
    must clear the cached size_bytes so list_demo_fixtures stops
    advertising it. Previously _refresh_sizes only WROTE non-zero
    sizes, leaking stale values that 500'd on click.
    """
    (isolated_fixture_root / "cylinder.stl").unlink()
    r = client.get("/api/demo-fixtures")
    assert r.status_code == 200
    names = {fx["name"] for fx in r.json()}
    assert "cylinder" not in names, (
        "cylinder.stl removed from disk should not appear in catalogue"
    )
    # The other two fixtures are still present.
    assert {"ldc_box", "naca0012"}.issubset(names)


def test_import_demo_fixture_happy_path(isolated_fixture_root: Path) -> None:
    """POST /api/demo-fixtures/cylinder/import returns the same
    ImportSTLResponse shape /api/import/stl returns, so the frontend
    post-import navigation logic works unchanged."""
    r = client.post("/api/demo-fixtures/cylinder/import")
    assert r.status_code == 200
    body = r.json()
    assert body["case_id"].startswith("imported_")
    assert body["edit_url"] == f"/workbench/case/{body['case_id']}/edit"
    assert body["ingest_report"]["is_watertight"] is True
    assert body["ingest_report"]["face_count"] > 0


def test_import_demo_fixture_unknown_name_404(isolated_fixture_root: Path) -> None:
    """Allowlist guard: unknown names 404 with a structured message."""
    r = client.post("/api/demo-fixtures/totally_made_up/import")
    assert r.status_code == 404
    detail = r.json()["detail"]
    assert "unknown demo fixture" in detail
    assert "totally_made_up" in detail


def test_import_demo_fixture_missing_on_disk_500(isolated_fixture_root: Path) -> None:
    """When a fixture is in the catalogue but missing on disk (e.g.
    operator deletion), the import endpoint returns 500 — operator
    fault, not user fault. Reach this state by deleting the file
    after _refresh_sizes ran (so the catalogue still lists the
    fixture in-memory but the file is gone).
    """
    # Re-stat with the file present so size_bytes is non-zero, then
    # delete it just before the POST so the route's own existence
    # check is what triggers 500. (After our P2 fix, _refresh_sizes
    # would zero it out — but the catalogue snapshot in _FIXTURES
    # still has the in-memory size; the route re-checks path.exists
    # before reading.)
    (isolated_fixture_root / "ldc_box.stl").unlink()
    # Force size_bytes back to non-zero so the route is reachable
    # (simulating a race: catalogue snapshot from a prior list call
    # is stale relative to current disk state).
    demo_mod._FIXTURES["ldc_box"].size_bytes = 684

    r = client.post("/api/demo-fixtures/ldc_box/import")
    assert r.status_code == 500
    detail = r.json()["detail"]
    assert "ldc_box.stl" in detail
    assert "missing on disk" in detail


def test_import_demo_fixture_corrupt_asset_returns_500(
    isolated_fixture_root: Path,
) -> None:
    """Codex Round 6 Q3 follow-up: a corrupt server-owned asset is an
    operator fault, not a user upload fault. Parse / watertight
    failures on a checked-in demo STL must surface as 500 (operator
    needs to fix), NOT 400 (which is the right code for user uploads
    via /api/import/stl).
    """
    # Replace cylinder.stl with garbage so STL parse fails.
    (isolated_fixture_root / "cylinder.stl").write_bytes(b"this is not an STL")
    demo_mod._refresh_sizes()  # pick up the new (smaller) size

    r = client.post("/api/demo-fixtures/cylinder/import")
    assert r.status_code == 500
    detail = r.json()["detail"]
    assert "cylinder.stl" in detail
    assert "corrupt" in detail or "STL parse" in detail
