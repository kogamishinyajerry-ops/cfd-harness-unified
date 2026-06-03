"""DEC-V61-226 · Workflow Monitor API + assembler tests.

Verifies the real-data path: the assembler derives all six stages from REAL
on-disk showcase artifacts (run_record.json), is_mock is False, the honest
report gate keys on the recorded convergence flag (not a misfiring re-derived
metric), edges serialize as from/to, and the SSE replay emits run+stage+done.
"""
from __future__ import annotations

from fastapi.testclient import TestClient


def _client() -> TestClient:
    from ui.backend.main import app

    return TestClient(app)


def test_list_workflow_runs_returns_real_showcase_runs() -> None:
    c = _client()
    r = c.get("/api/workflow-runs")
    assert r.status_code == 200
    runs = r.json()
    # the real NACA0012 showcase AoA sweep is on disk
    keys = {x["runKey"] for x in runs}
    assert "naca0012_showcase_a04" in keys
    # real data → never flagged mock
    assert all(x["isMock"] is False for x in runs)


def test_get_workflow_run_assembles_six_stages_from_real_artifacts() -> None:
    c = _client()
    r = c.get("/api/workflow-runs/naca0012_showcase_a04")
    assert r.status_code == 200
    run = r.json()
    assert run["isMock"] is False
    assert [s["key"] for s in run["stages"]] == [
        "geometry_intake",
        "geometry_validation",
        "mesh_generation",
        "mesh_quality_check",
        "solver_run",
        "result_report",
    ]
    # edges serialize with the literal "from"/"to" keys the frontend expects
    assert run["edges"][0]["from"] == "geometry_intake"
    assert run["edges"][0]["to"] == "geometry_validation"
    # a04 really converged → solver passed, report HONESTLY passed
    solver = next(s for s in run["stages"] if s["key"] == "solver_run")
    report = next(s for s in run["stages"] if s["key"] == "result_report")
    assert solver["state"] == "passed"
    assert report["state"] == "passed"
    # real solver numbers surfaced (Cl/Cd present as metrics)
    metric_labels = {m["label"] for m in solver["metrics"]}
    assert "Cl" in metric_labels and "Cd" in metric_labels


def test_report_gate_keys_on_recorded_convergence_not_cl_pct_at_zero_lift() -> None:
    """a00 (α=0°) has ~zero lift → cl_drift_pct is a meaningless 7747%. The
    report gate must NOT block on that; it keys on the recorded convergence
    flag, so a00 reports passed (it really converged)."""
    c = _client()
    run = c.get("/api/workflow-runs/naca0012_showcase_a00").json()
    report = next(s for s in run["stages"] if s["key"] == "result_report")
    assert report["state"] == "passed"


def test_unknown_run_key_is_404() -> None:
    c = _client()
    assert c.get("/api/workflow-runs/not_a_real_run").status_code == 404
    # traversal-style keys are rejected by the strict run_key pattern (404)
    assert c.get("/api/workflow-runs/..%2f..%2fetc").status_code in (400, 404)


def test_events_stream_emits_run_then_stages_then_done() -> None:
    c = _client()
    r = c.get("/api/workflow-runs/naca0012_showcase_a04/events")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    body = r.text
    assert '"type": "run"' in body
    assert '"type": "stage"' in body
    assert '"type": "done"' in body
