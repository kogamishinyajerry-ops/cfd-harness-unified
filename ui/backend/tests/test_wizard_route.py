"""Stage 8a · onboarding-wizard route tests.

Covers the three wizard surfaces: template list, draft creation
(+ user_drafts side effect), and SSE phase stream framing.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from ui.backend.main import app
from ui.backend.services.case_drafts import DRAFTS_DIR

client = TestClient(app)


def test_lists_three_starter_templates() -> None:
    r = client.get("/api/wizard/templates")
    assert r.status_code == 200
    body = r.json()
    ids = {t["template_id"] for t in body["templates"]}
    assert ids == {"square_cavity", "backward_facing_step", "pipe_flow"}


def test_each_template_carries_param_schema() -> None:
    body = client.get("/api/wizard/templates").json()
    for t in body["templates"]:
        assert len(t["params"]) >= 2
        for p in t["params"]:
            assert "key" in p and "default" in p
            assert p["type"] in ("int", "float")
            # bilingual labels are required so the wizard renders both
            assert p["label_zh"] and p["label_en"]


def _cleanup_draft(case_id: str) -> None:
    path = Path(DRAFTS_DIR) / f"{case_id}.yaml"
    if path.exists():
        path.unlink()


def test_create_draft_writes_to_user_drafts_and_returns_yaml() -> None:
    case_id = "wizard_test_first_cavity"
    try:
        r = client.post(
            "/api/wizard/draft",
            json={
                "template_id": "square_cavity",
                "case_id": case_id,
                "name_display": "Wizard test first cavity",
                "params": {"Re": 250.0, "lid_velocity": 1.5},
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["case_id"] == case_id
        assert body["lint_ok"] is True
        # Sanity: rendered YAML carries the template parameters back
        assert f"id: {case_id}" in body["yaml_text"]
        assert "Re: 250.0" in body["yaml_text"]
        assert "top_wall_u: 1.5" in body["yaml_text"]
        # Side effect: file actually exists on disk
        path = Path(DRAFTS_DIR) / f"{case_id}.yaml"
        assert path.exists()
        assert "Re: 250.0" in path.read_text(encoding="utf-8")
    finally:
        _cleanup_draft(case_id)


def test_create_draft_rejects_path_traversal_case_id() -> None:
    r = client.post(
        "/api/wizard/draft",
        json={
            "template_id": "square_cavity",
            "case_id": "../escape",
            "params": {},
        },
    )
    assert r.status_code == 400
    assert "alphanumeric" in r.json()["detail"]


def test_create_draft_rejects_unknown_template() -> None:
    case_id = "wizard_test_bad_template"
    try:
        r = client.post(
            "/api/wizard/draft",
            json={"template_id": "no_such_template", "case_id": case_id, "params": {}},
        )
        assert r.status_code == 400
        assert "unknown template_id" in r.json()["detail"]
    finally:
        _cleanup_draft(case_id)


def test_pipe_flow_template_uses_axisymmetric_geometry() -> None:
    """Sanity guard: each template renders to its expected geometry_type
    enum so a frontend reading the YAML preview sees the right shape."""
    case_id = "wizard_test_pipe"
    try:
        r = client.post(
            "/api/wizard/draft",
            json={
                "template_id": "pipe_flow",
                "case_id": case_id,
                "params": {"Re": 500.0},
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert "geometry_type: AXISYMMETRIC" in body["yaml_text"]
    finally:
        _cleanup_draft(case_id)


def test_run_stream_walks_five_phases_and_closes() -> None:
    """SSE phase stream contract: 5 phase_start + 5 phase_done + 1 run_done.
    This is what the frontend's state machine expects."""
    with client.stream("GET", "/api/wizard/run/wizard_test_stream/stream") as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        phase_starts: list[str] = []
        phase_dones: list[str] = []
        saw_run_done = False
        for line in r.iter_lines():
            if not line.startswith("data:"):
                continue
            ev = json.loads(line[5:].strip())
            if ev["type"] == "phase_start":
                phase_starts.append(ev["phase"])
            elif ev["type"] == "phase_done":
                phase_dones.append(ev["phase"])
            elif ev["type"] == "run_done":
                saw_run_done = True
                break

    assert phase_starts == ["geometry", "mesh", "boundary", "solver", "compare"]
    assert phase_dones == ["geometry", "mesh", "boundary", "solver", "compare"]
    assert saw_run_done


def test_run_stream_validates_case_id() -> None:
    """Path-traversal in the SSE URL must 400, not stream a garbage run."""
    r = client.get("/api/wizard/run/..%2Fescape/stream")
    assert r.status_code in (400, 404)  # FastAPI may 404 the path before our check
