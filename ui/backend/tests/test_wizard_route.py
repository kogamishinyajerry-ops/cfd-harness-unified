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


def test_q13_schema_accepts_forward_compat_fields() -> None:
    """Round-3 Q13 schema audit: the level / stream / exit_code fields are
    optional now (mock leaves them None) but Stage 8b real-solver runs
    will populate them. Validate the schema accepts each field with
    realistic values so the wire contract is locked before the Stage 8b
    PR."""
    from ui.backend.schemas.wizard import RunPhaseEvent

    # Mock-style event: forward-compat fields absent
    mock_ev = RunPhaseEvent(
        type="log", phase="solver", t=1.0, line="Time = 0.05s residual 1e-3",
    )
    assert mock_ev.level is None
    assert mock_ev.stream is None
    assert mock_ev.exit_code is None

    # Real-solver-style event: warning to stderr
    real_warn = RunPhaseEvent(
        type="log", phase="solver", t=1.0,
        line="--> FOAM Warning : non-orthogonality > 70°",
        level="warning", stream="stderr",
    )
    assert real_warn.level == "warning"
    assert real_warn.stream == "stderr"

    # phase_done with exit_code (subprocess wait result)
    done_ev = RunPhaseEvent(
        type="phase_done", phase="solver", t=2.0,
        status="ok", summary="converged · 200 iterations",
        exit_code=0,
    )
    assert done_ev.exit_code == 0


def test_q13_event_serialization_omits_none_fields() -> None:
    """SSE wire format should be lean. Pydantic .model_dump() with
    `exclude_none` keeps the mock event payload at the same size as
    pre-audit (no schema bloat). Stage 8b can keep the SSE message
    body minimal by serializing this way."""
    from ui.backend.schemas.wizard import RunPhaseEvent

    ev = RunPhaseEvent(type="log", phase="mesh", t=1.0, line="Reading blockMeshDict")
    payload = ev.model_dump(exclude_none=True)
    # Forward-compat fields should be absent
    assert "level" not in payload
    assert "stream" not in payload
    assert "exit_code" not in payload
    # Core fields present
    assert payload["type"] == "log"
    assert payload["phase"] == "mesh"


# --- Opus round-2 Q11: server-rendered preview must be byte-exact ----------

def test_preview_matches_create_byte_for_byte() -> None:
    """Q11 trust contract: the preview YAML the user sees and the YAML
    the server writes on /draft must be character-identical. Client-side
    string-concat (the original implementation) said 'lid_velocity:' while
    the server emitted 'top_wall_u:' — which broke the wizard's first
    promise (WYSIWYG).
    """
    case_id = "wizard_test_preview_match"
    payload = {
        "template_id": "square_cavity",
        "case_id": case_id,
        "name_display": "preview-match guard",
        "params": {"Re": 333.0, "lid_velocity": 0.7},
    }
    try:
        preview = client.post("/api/wizard/preview", json=payload).json()["yaml_text"]
        create = client.post("/api/wizard/draft", json=payload).json()["yaml_text"]
        assert preview == create, (
            "Preview drift detected — round-2 Q11 trust contract violated.\n"
            f"--- preview ---\n{preview}\n--- create ---\n{create}"
        )
    finally:
        _cleanup_draft(case_id)


def test_preview_renders_for_all_three_templates() -> None:
    """All starter templates must produce a non-empty preview without
    falling back to lint errors. Frontend depends on this for step-3 UX
    (no template should silently render an empty <pre>)."""
    for tid in ("square_cavity", "backward_facing_step", "pipe_flow"):
        r = client.post(
            "/api/wizard/preview",
            json={
                "template_id": tid,
                "case_id": "preview_smoke",
                "params": {},
            },
        )
        assert r.status_code == 200, f"{tid}: {r.status_code} {r.text}"
        text = r.json()["yaml_text"]
        assert text.strip(), f"{tid}: empty preview"
        assert "id: preview_smoke" in text
        assert "geometry_type" in text


# --- Round-2 Q9: param input validation (inf / nan / out-of-range) ---------

def test_q9_rejects_nan_param() -> None:
    """NaN must be rejected — round-2 Q9 trust boundary."""
    case_id = "wizard_test_nan"
    try:
        # JSON has no native NaN — encode as the string 'NaN' in raw body to
        # simulate what a buggy client (or hostile actor) might send. fastapi
        # / pydantic parse it as float NaN.
        r = client.post(
            "/api/wizard/preview",
            content='{"template_id":"square_cavity","case_id":"' + case_id + '","params":{"Re":NaN,"lid_velocity":1.0}}',
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 400
        detail = r.json().get("detail", "").lower()
        assert "nan" in detail
    finally:
        _cleanup_draft(case_id)


def test_q9_rejects_inf_param() -> None:
    """+Infinity must be rejected — yaml.safe_dump would emit `.inf`
    which downstream consumers can't compare numerically."""
    case_id = "wizard_test_inf"
    try:
        r = client.post(
            "/api/wizard/preview",
            content='{"template_id":"square_cavity","case_id":"' + case_id + '","params":{"Re":Infinity,"lid_velocity":1.0}}',
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 400
        detail = r.json().get("detail", "").lower()
        assert "infinity" in detail or "inf" in detail
    finally:
        _cleanup_draft(case_id)


def test_q9_rejects_value_below_min() -> None:
    """Re=5 is below the square_cavity Re min=10."""
    case_id = "wizard_test_below_min"
    try:
        r = client.post(
            "/api/wizard/preview",
            json={
                "template_id": "square_cavity",
                "case_id": case_id,
                "params": {"Re": 5.0, "lid_velocity": 1.0},
            },
        )
        assert r.status_code == 400
        assert "below min" in r.json()["detail"].lower()
    finally:
        _cleanup_draft(case_id)


def test_q9_rejects_value_above_max() -> None:
    """lid_velocity=99 is above square_cavity max=10."""
    case_id = "wizard_test_above_max"
    try:
        r = client.post(
            "/api/wizard/preview",
            json={
                "template_id": "square_cavity",
                "case_id": case_id,
                "params": {"Re": 100.0, "lid_velocity": 99.0},
            },
        )
        assert r.status_code == 400
        assert "above max" in r.json()["detail"].lower()
    finally:
        _cleanup_draft(case_id)


def test_q9_unknown_param_keys_silently_dropped() -> None:
    """Extra param keys are tolerated (forward-compat for older clients
    sending obsolete fields). They just don't affect the rendered YAML."""
    case_id = "wizard_test_extra_keys"
    try:
        r = client.post(
            "/api/wizard/preview",
            json={
                "template_id": "square_cavity",
                "case_id": case_id,
                "params": {
                    "Re": 100.0,
                    "lid_velocity": 1.0,
                    "obsolete_field": 42.0,  # tolerated
                },
            },
        )
        assert r.status_code == 200
        text = r.json()["yaml_text"]
        assert "obsolete_field" not in text
    finally:
        _cleanup_draft(case_id)


def test_q9_create_draft_also_validates() -> None:
    """The validation must run on both /preview and /draft (otherwise
    user could see a clean preview but write a corrupt YAML to disk)."""
    case_id = "wizard_test_create_validates"
    try:
        r = client.post(
            "/api/wizard/draft",
            content='{"template_id":"square_cavity","case_id":"' + case_id + '","params":{"Re":NaN,"lid_velocity":1.0}}',
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 400
        # File must NOT exist
        path = Path(DRAFTS_DIR) / f"{case_id}.yaml"
        assert not path.exists()
    finally:
        _cleanup_draft(case_id)


def test_preview_does_not_write_user_drafts() -> None:
    """Preview MUST be side-effect free — no file written.

    Critical because users will hit /preview many times while iterating
    on params. If preview also wrote a draft, the user_drafts dir would
    fill up with abandoned ids."""
    case_id = "preview_should_not_write_to_disk"
    try:
        r = client.post(
            "/api/wizard/preview",
            json={
                "template_id": "square_cavity",
                "case_id": case_id,
                "params": {"Re": 100.0},
            },
        )
        assert r.status_code == 200
        path = Path(DRAFTS_DIR) / f"{case_id}.yaml"
        assert not path.exists(), (
            f"preview wrote {path} — must be side-effect-free"
        )
    finally:
        _cleanup_draft(case_id)  # belt-and-suspenders
