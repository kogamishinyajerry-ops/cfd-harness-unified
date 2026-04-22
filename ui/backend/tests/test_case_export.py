"""Tests for /api/cases/{id}/export — reference bundle download."""

from __future__ import annotations

import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from ui.backend.main import app

client = TestClient(app)


def _open_zip(data: bytes) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(data), mode="r")


def test_export_returns_zip_with_readme_and_contract() -> None:
    response = client.get("/api/cases/lid_driven_cavity/export")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert (
        'filename="lid_driven_cavity_reference.zip"'
        in response.headers["content-disposition"]
    )

    zf = _open_zip(response.content)
    names = zf.namelist()
    assert "lid_driven_cavity/README.md" in names
    assert "lid_driven_cavity/validation_contract.md" in names
    assert "lid_driven_cavity/gold_standard.yaml" in names

    readme = zf.read("lid_driven_cavity/README.md").decode()
    assert "Ghia" in readme or "lid_driven_cavity" in readme.lower()
    contract = zf.read("lid_driven_cavity/validation_contract.md").decode()
    assert "u_centerline" in contract or "Tolerance" in contract


def test_export_renders_physics_contract_with_three_state_markers() -> None:
    """Regression guard for the honesty bug where `satisfied_by_current_adapter: partial`
    was truthy-rendered as `[✓]`, laundering a documented gap into a clean check.
    LDC's physics_contract has 4 `true` preconditions + 1 `partial`, so the rendered
    markdown must carry the [~] marker at least once, and the Contract status headline
    must surface the nuanced status string."""
    response = client.get("/api/cases/lid_driven_cavity/export")
    assert response.status_code == 200
    contract = _open_zip(response.content).read(
        "lid_driven_cavity/validation_contract.md"
    ).decode()
    assert "## Contract status" in contract
    assert "SATISFIED_FOR_U_CENTERLINE_ONLY" in contract
    assert "[~]" in contract, (
        "partial-satisfied precondition must render as [~], not laundered to [✓]"
    )
    assert "[✓]" in contract
    # Legend must be present so readers know what [~] means.
    assert "Legend" in contract


def test_export_preserves_gold_yaml_byte_identity() -> None:
    """Gold YAML in the zip must be byte-identical to knowledge/gold_standards/."""
    from pathlib import Path

    gold_path = (
        Path(__file__).resolve().parents[3]
        / "knowledge"
        / "gold_standards"
        / "lid_driven_cavity.yaml"
    )
    on_disk = gold_path.read_text(encoding="utf-8")

    response = client.get("/api/cases/lid_driven_cavity/export")
    zf = _open_zip(response.content)
    bundled = zf.read("lid_driven_cavity/gold_standard.yaml").decode()

    assert bundled == on_disk, (
        "Exported gold_standard.yaml drifted from on-disk knowledge/gold_standards/ "
        "— bundle must preserve byte identity to avoid two-source-of-truth hazard."
    )


def test_export_rejects_unknown_case() -> None:
    response = client.get("/api/cases/not_a_real_case/export")
    assert response.status_code == 404


@pytest.mark.parametrize(
    "case_id",
    [
        "lid_driven_cavity",
        "circular_cylinder_wake",
        "turbulent_flat_plate",
        "backward_facing_step",
        "differential_heated_cavity",
        "duct_flow",
        "plane_channel_flow",
        "impinging_jet",
        "naca0012_airfoil",
        "rayleigh_benard_convection",
    ],
)
def test_export_available_for_every_whitelist_case(case_id: str) -> None:
    response = client.get(f"/api/cases/{case_id}/export")
    assert response.status_code == 200
    zf = _open_zip(response.content)
    # Every bundle must have the three canonical members so the client
    # doesn't need case-specific handling.
    expected = {
        f"{case_id}/README.md",
        f"{case_id}/validation_contract.md",
        f"{case_id}/gold_standard.yaml",
    }
    assert expected.issubset(set(zf.namelist()))
