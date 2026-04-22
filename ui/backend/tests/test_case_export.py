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


# ---------------------------------------------------------------------------
# DEC-V61-046 round-1 R3-N2/N3: _precondition_marker edge cases
# ---------------------------------------------------------------------------

def test_precondition_marker_three_state_boolean_and_string() -> None:
    """Direct behavioural pin for `_precondition_marker`.

    Ensures YAML booleans, stringly-typed booleans, partial labels, int-as-bool,
    and unknown types all resolve to one of the three documented markers.
    R3-N2/N3 codex finding: silent [✗] for `"True"` was launder-by-miscoercion;
    silent [✓] for `"partial"` (pre-patch) was launder-in-the-other-direction.
    Both paths now explicit."""
    from ui.backend.routes.case_export import _precondition_marker

    # Canonical booleans
    assert _precondition_marker(True) == "\u2713"
    assert _precondition_marker(False) == "\u2717"
    # String booleans (hand-edited YAMLs)
    assert _precondition_marker("true") == "\u2713"
    assert _precondition_marker("True") == "\u2713"
    assert _precondition_marker("TRUE") == "\u2713"
    assert _precondition_marker("false") == "\u2717"
    assert _precondition_marker("False") == "\u2717"
    # Partial labels (both YAML-idiomatic spellings)
    assert _precondition_marker("partial") == "~"
    assert _precondition_marker("partially") == "~"
    assert _precondition_marker("Partial") == "~"
    # Int-as-bool
    assert _precondition_marker(1) == "\u2713"
    assert _precondition_marker(0) == "\u2717"
    # Unknown types → fail-visible [\u2717], not laundered to [\u2713]
    assert _precondition_marker(None) == "\u2717"
    assert _precondition_marker({}) == "\u2717"
    assert _precondition_marker([]) == "\u2717"
    assert _precondition_marker("nonsense") == "\u2717"


def test_export_bundle_renders_fail_marker_on_explicit_false() -> None:
    """Live export must render [\u2717] for `satisfied_by_current_adapter: false`.
    LDC`s physics_contract has preconditions #4 and #5 explicitly false (v_centerline
    and primary_vortex_location provenance per DEC-V61-046 round-1 R2-M1 fix).
    If rendering ever regressed to laundering those to [\u2713], the downloadable
    contract bundle would no longer surface the documented gap — exactly the
    honesty bug R3-N2 was guarding against."""
    response = client.get("/api/cases/lid_driven_cavity/export")
    assert response.status_code == 200
    contract = _open_zip(response.content).read(
        "lid_driven_cavity/validation_contract.md"
    ).decode()
    assert "[\u2717]" in contract, (
        "LDC validation_contract.md should render [\u2717] for false preconditions"
    )
    # And confirm the false preconditions are the v/vortex ones (evidence-level
    # check, not prose). If the YAML is re-ordered or edited without updating
    # the indexing evidence, this assertion will fail loudly.
    assert "v_centerline" in contract
    assert "primary_vortex_location" in contract
