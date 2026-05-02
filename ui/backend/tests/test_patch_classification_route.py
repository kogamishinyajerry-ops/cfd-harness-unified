"""Tests for the GET/PUT/DELETE /api/cases/{case_id}/patch-classification
route (DEC-V61-108 Phase A).
"""
from __future__ import annotations

import secrets
from pathlib import Path

import yaml
from fastapi.testclient import TestClient


def _isolated_imported(monkeypatch, tmp_path: Path) -> Path:
    target = tmp_path / "imported"
    target.mkdir()
    monkeypatch.setattr(
        "ui.backend.services.case_scaffold.IMPORTED_DIR", target
    )
    monkeypatch.setattr(
        "ui.backend.routes.case_patch_classification.IMPORTED_DIR", target
    )
    return target


def _stage_imported_case(
    imported_dir: Path, case_id: str, *, with_polymesh: bool = True
) -> Path:
    case_dir = imported_dir / case_id
    case_dir.mkdir()
    if with_polymesh:
        polymesh = case_dir / "constant" / "polyMesh"
        polymesh.mkdir(parents=True)
        body = "\n".join(
            f"    {name}\n    {{\n        type            patch;\n"
            f"        nFaces          {n};\n        startFace       {s};\n    }}"
            for name, n, s in [
                ("inlet", 50, 0),
                ("outlet", 50, 50),
                ("walls", 500, 100),
                ("custom_patch_3", 25, 600),
            ]
        )
        (polymesh / "boundary").write_text(
            "FoamFile {}\n4\n(\n" + body + "\n)\n"
        )
    return case_dir


def _new_client() -> TestClient:
    from ui.backend.main import app

    return TestClient(app)


def _safe_case_id() -> str:
    return f"imported_2026-05-02T00-00-00Z_{secrets.token_hex(4)}"


# ─────────── GET ───────────


def test_get_returns_state_with_auto_classifications_no_overrides(
    monkeypatch, tmp_path
):
    imported = _isolated_imported(monkeypatch, tmp_path)
    case_id = _safe_case_id()
    _stage_imported_case(imported, case_id)
    client = _new_client()

    resp = client.get(f"/api/cases/{case_id}/patch-classification")
    assert resp.status_code == 200
    body = resp.json()
    assert body["case_id"] == case_id
    assert body["schema_version"] == 1
    assert set(body["available_patches"]) == {
        "inlet", "outlet", "walls", "custom_patch_3"
    }
    # Heuristic-derived classifications.
    assert body["auto_classifications"]["inlet"] == "velocity_inlet"
    assert body["auto_classifications"]["outlet"] == "pressure_outlet"
    assert body["auto_classifications"]["walls"] == "no_slip_wall"
    # custom_patch_3 has no canonical token → falls through to wall.
    assert body["auto_classifications"]["custom_patch_3"] == "no_slip_wall"
    assert body["overrides"] == {}


def test_get_returns_existing_overrides(monkeypatch, tmp_path):
    imported = _isolated_imported(monkeypatch, tmp_path)
    case_id = _safe_case_id()
    case_dir = _stage_imported_case(imported, case_id)
    (case_dir / "system").mkdir()
    (case_dir / "system" / "patch_classification.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "overrides": {"custom_patch_3": "velocity_inlet"},
            }
        )
    )
    client = _new_client()

    resp = client.get(f"/api/cases/{case_id}/patch-classification")
    assert resp.status_code == 200
    body = resp.json()
    assert body["overrides"] == {"custom_patch_3": "velocity_inlet"}
    # auto_classifications shows what the heuristic WOULD say,
    # not what the override forces — so the UI can render
    # "you're overriding wall → inlet".
    assert body["auto_classifications"]["custom_patch_3"] == "no_slip_wall"


def test_get_404_for_missing_case(monkeypatch, tmp_path):
    _isolated_imported(monkeypatch, tmp_path)
    client = _new_client()
    resp = client.get(
        "/api/cases/imported_2026-05-02T00-00-00Z_doesnt_exist/"
        "patch-classification"
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["failing_check"] == "case_not_found"


# ─────────── PUT ───────────


def test_put_writes_override_and_returns_merged_state(
    monkeypatch, tmp_path
):
    imported = _isolated_imported(monkeypatch, tmp_path)
    case_id = _safe_case_id()
    case_dir = _stage_imported_case(imported, case_id)
    client = _new_client()

    resp = client.put(
        f"/api/cases/{case_id}/patch-classification",
        json={"patch_name": "custom_patch_3", "bc_class": "velocity_inlet"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["overrides"] == {"custom_patch_3": "velocity_inlet"}

    # Sidecar must exist on disk.
    sidecar = case_dir / "system" / "patch_classification.yaml"
    assert sidecar.is_file()
    on_disk = yaml.safe_load(sidecar.read_text())
    assert on_disk["overrides"]["custom_patch_3"] == "velocity_inlet"


def test_put_rejects_invalid_bc_class(monkeypatch, tmp_path):
    imported = _isolated_imported(monkeypatch, tmp_path)
    case_id = _safe_case_id()
    _stage_imported_case(imported, case_id)
    client = _new_client()

    resp = client.put(
        f"/api/cases/{case_id}/patch-classification",
        json={"patch_name": "inlet", "bc_class": "bogus_class"},
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["failing_check"] == "invalid_bc_class"
    assert "velocity_inlet" in detail["allowed"]


def test_put_rejects_patch_not_in_mesh(monkeypatch, tmp_path):
    imported = _isolated_imported(monkeypatch, tmp_path)
    case_id = _safe_case_id()
    _stage_imported_case(imported, case_id)
    client = _new_client()

    resp = client.put(
        f"/api/cases/{case_id}/patch-classification",
        json={"patch_name": "ghost_patch", "bc_class": "velocity_inlet"},
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["failing_check"] == "patch_not_in_mesh"
    assert "inlet" in detail["available_patches"]


def test_put_pre_mesh_accepts_forward_looking_override(
    monkeypatch, tmp_path
):
    """When polyMesh isn't there yet (engineer staging classifications
    before meshing), the route must NOT block the PUT — there's no
    ground truth to validate against. Once the mesh lands the
    classification will either match a real patch or be silently
    dropped at solve time."""
    imported = _isolated_imported(monkeypatch, tmp_path)
    case_id = _safe_case_id()
    _stage_imported_case(imported, case_id, with_polymesh=False)
    client = _new_client()

    resp = client.put(
        f"/api/cases/{case_id}/patch-classification",
        json={
            "patch_name": "future_patch_named_at_meshing_time",
            "bc_class": "symmetry",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["available_patches"] == []
    assert body["overrides"] == {
        "future_patch_named_at_meshing_time": "symmetry"
    }


def test_put_overwrites_existing_override(monkeypatch, tmp_path):
    imported = _isolated_imported(monkeypatch, tmp_path)
    case_id = _safe_case_id()
    _stage_imported_case(imported, case_id)
    client = _new_client()

    client.put(
        f"/api/cases/{case_id}/patch-classification",
        json={"patch_name": "custom_patch_3", "bc_class": "velocity_inlet"},
    )
    resp = client.put(
        f"/api/cases/{case_id}/patch-classification",
        json={"patch_name": "custom_patch_3", "bc_class": "pressure_outlet"},
    )
    assert resp.status_code == 200
    assert resp.json()["overrides"]["custom_patch_3"] == "pressure_outlet"


# ─────────── DELETE ───────────


def test_delete_clears_one_override_keeps_others(monkeypatch, tmp_path):
    imported = _isolated_imported(monkeypatch, tmp_path)
    case_id = _safe_case_id()
    case_dir = _stage_imported_case(imported, case_id)
    (case_dir / "system").mkdir()
    (case_dir / "system" / "patch_classification.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "overrides": {
                    "custom_patch_3": "velocity_inlet",
                    "walls": "symmetry",
                },
            }
        )
    )
    client = _new_client()

    resp = client.delete(
        f"/api/cases/{case_id}/patch-classification?patch_name=walls"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["overrides"] == {"custom_patch_3": "velocity_inlet"}


def test_delete_idempotent_for_missing_patch(monkeypatch, tmp_path):
    imported = _isolated_imported(monkeypatch, tmp_path)
    case_id = _safe_case_id()
    _stage_imported_case(imported, case_id)
    client = _new_client()

    resp = client.delete(
        f"/api/cases/{case_id}/patch-classification?patch_name=never_set"
    )
    assert resp.status_code == 200
    assert resp.json()["overrides"] == {}
