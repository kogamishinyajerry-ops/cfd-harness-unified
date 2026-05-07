"""DEC-V61-169 / B.5.3 · /api/cases/{id}/actions catalogue tests."""
from __future__ import annotations

import secrets
from pathlib import Path

from fastapi.testclient import TestClient


def _isolate(monkeypatch, tmp_path: Path) -> Path:
    target = tmp_path / "imported"
    target.mkdir()
    monkeypatch.setattr(
        "ui.backend.services.case_scaffold.IMPORTED_DIR", target
    )
    monkeypatch.setattr(
        "ui.backend.routes.actions_catalogue.IMPORTED_DIR", target
    )
    return target


def _stage(imported_dir: Path, case_id: str) -> Path:
    case_dir = imported_dir / case_id
    case_dir.mkdir()
    (case_dir / "constant").mkdir()
    return case_dir


def _client() -> TestClient:
    from ui.backend.main import app

    return TestClient(app)


def _safe_id() -> str:
    return f"imported_2026-05-07T00-00-00Z_{secrets.token_hex(4)}"


def test_catalogue_returns_200_with_substituted_case_id(monkeypatch, tmp_path):
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage(imported, case_id)

    resp = _client().get(f"/api/cases/{case_id}/actions")
    assert resp.status_code == 200
    body = resp.json()
    assert body["case_id"] == case_id
    # case_id substituted into URLs
    for entry in body["query"] + body["advisor"]:
        if "{case_id}" in entry["url"]:
            raise AssertionError(f"unsubstituted template in {entry}")
        # case_id appears in routes that are case-scoped
        if entry["name"] not in {"import_geometry"}:
            assert case_id in entry["url"], (
                f"{entry['name']} url should include case_id; got {entry['url']}"
            )


def test_catalogue_has_all_five_workflow_steps(monkeypatch, tmp_path):
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage(imported, case_id)

    body = _client().get(f"/api/cases/{case_id}/actions").json()
    steps = body["steps"]
    assert len(steps) == 5
    step_names = [s["name"] for s in steps]
    assert step_names == [
        "import_geometry", "mesh", "physics", "setup_bc", "solve",
    ]
    # step indices 1-5 in order
    assert [s["step"] for s in steps] == [1, 2, 3, 4, 5]


def test_all_workflow_steps_are_post(monkeypatch, tmp_path):
    """V130 invariant: workflow steps mutate state — must all be POST."""
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage(imported, case_id)
    body = _client().get(f"/api/cases/{case_id}/actions").json()
    for s in body["steps"]:
        assert s["method"] == "POST", f"workflow step {s['name']} should be POST"


def test_advisor_routes_include_review_and_diagnose(monkeypatch, tmp_path):
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage(imported, case_id)
    body = _client().get(f"/api/cases/{case_id}/actions").json()
    advisor_names = {a["name"] for a in body["advisor"]}
    assert {"ai_review", "ai_diagnose"}.issubset(advisor_names)


def test_advisor_routes_are_get(monkeypatch, tmp_path):
    """V130 invariant: AI advisor is read-only — must all be GET."""
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage(imported, case_id)
    body = _client().get(f"/api/cases/{case_id}/actions").json()
    for a in body["advisor"]:
        assert a["method"] == "GET", f"advisor {a['name']} should be GET"


def test_query_routes_include_state_completeness_meshquality(monkeypatch, tmp_path):
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage(imported, case_id)
    body = _client().get(f"/api/cases/{case_id}/actions").json()
    query_names = {q["name"] for q in body["query"]}
    for required in ("state", "completeness", "mesh_quality", "physics_state"):
        assert required in query_names, f"missing query route {required}"


def test_query_routes_are_get(monkeypatch, tmp_path):
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage(imported, case_id)
    body = _client().get(f"/api/cases/{case_id}/actions").json()
    for q in body["query"]:
        assert q["method"] == "GET", f"query {q['name']} should be GET"


def test_self_discovery_fallback_present(monkeypatch, tmp_path):
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage(imported, case_id)
    body = _client().get(f"/api/cases/{case_id}/actions").json()
    assert body["self_discovery_fallback"] == "/api/openapi.json"


def test_404_for_missing_case(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    resp = _client().get(f"/api/cases/{_safe_id()}/actions")
    assert resp.status_code == 404


def test_400_for_unsafe_case_id(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    resp = _client().get("/api/cases/..%2Fevil/actions")
    assert resp.status_code in (400, 404)


def test_step_descriptions_mention_step_number(monkeypatch, tmp_path):
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage(imported, case_id)
    body = _client().get(f"/api/cases/{case_id}/actions").json()
    for s in body["steps"]:
        assert f"Step {s['step']}" in s["description"], (
            f"step {s['name']} description missing Step N marker"
        )


def test_each_post_step_has_example_body(monkeypatch, tmp_path):
    """B.5.5 / DEC-V61-170: schema discoverability — every POST step must
    ship an example_body so personas don't need to round-trip
    /api/openapi.json for working JSON."""
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage(imported, case_id)
    body = _client().get(f"/api/cases/{case_id}/actions").json()
    for s in body["steps"]:
        if s["method"] == "POST" and s["name"] != "import_geometry":
            assert s["example_body"] is not None, (
                f"step {s['name']} missing example_body"
            )
            assert isinstance(s["example_body"], dict)


def test_physics_example_body_uses_real_preset_ids(monkeypatch, tmp_path):
    """The physics example_body must reference actual preset_ids that the
    schema validator will accept (not fabricated)."""
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage(imported, case_id)
    body = _client().get(f"/api/cases/{case_id}/actions").json()
    physics = next(s for s in body["steps"] if s["name"] == "physics")
    eg = physics["example_body"]
    # Real preset_ids from materials_library / regimes_library
    real_material_presets = {
        "water_20c", "air_20c", "air_20c_isothermal", "oil_iso_vg_46_40c",
    }
    real_regime_presets = {
        "laminar_internal_default", "rans_ras_kepsilon_default",
        "rans_komegasst_default", "les_stub_placeholder",
    }
    assert eg["material"]["preset_id"] in real_material_presets
    assert eg["regime"]["preset_id"] in real_regime_presets


def test_import_geometry_url_has_no_case_id_substitution(monkeypatch, tmp_path):
    """Step 1 import is the entry — url must remain /api/import/stl."""
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage(imported, case_id)
    body = _client().get(f"/api/cases/{case_id}/actions").json()
    step1 = next(s for s in body["steps"] if s["name"] == "import_geometry")
    assert step1["url"] == "/api/import/stl"
    assert case_id not in step1["url"]
