"""Tests for Phase 2 Decisions Queue + Phase 4 Dashboard + Phase 3 Run Monitor."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from ui.backend.main import app

client = TestClient(app)


# ---------- Phase 2: Decisions Queue ----------------------------------------


def test_decisions_returns_cards_with_columns():
    resp = client.get("/api/decisions")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["cards"], list)
    assert len(body["cards"]) >= 6, "should find all .planning/decisions/*.md"
    ids = {c["decision_id"] for c in body["cards"]}
    assert "DEC-V61-001" in ids
    assert "DEC-V61-002" in ids
    # Column counts should sum to len(cards).
    assert sum(body["counts"].values()) == len(body["cards"])


def test_decisions_emit_notion_and_pr_urls_when_present():
    body = client.get("/api/decisions").json()
    v61_002 = next((c for c in body["cards"] if c["decision_id"] == "DEC-V61-002"), None)
    assert v61_002 is not None
    assert v61_002["notion_url"] and v61_002["notion_url"].startswith("https://www.notion.so/")
    assert v61_002["github_pr_url"] and "pull/" in v61_002["github_pr_url"]


def test_decisions_gate_queue_included():
    body = client.get("/api/decisions").json()
    qids = {g["qid"] for g in body["gate_queue"]}
    assert {"Q-1", "Q-2", "Q-3"}.issubset(qids)
    # Q-3 closed 2026-04-19; must be CLOSED.
    q3 = next(g for g in body["gate_queue"] if g["qid"] == "Q-3")
    assert q3["state"] == "CLOSED"


# ---------- Phase 3: Run Monitor --------------------------------------------


def test_run_checkpoints_snapshot():
    resp = client.get("/api/runs/differential_heated_cavity/checkpoints")
    assert resp.status_code == 200
    body = resp.json()
    assert body["case_id"] == "differential_heated_cavity"
    assert len(body["checkpoints"]) == 8


def test_run_stream_first_events():
    # Just consume the first ~3 SSE messages to verify wire format.
    with client.stream(
        "GET", "/api/runs/turbulent_flat_plate/stream"
    ) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        events: list[dict] = []
        for raw in resp.iter_lines():
            if not raw:
                continue
            line = raw if isinstance(raw, str) else raw.decode()
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
                if len(events) >= 3:
                    break
    assert events[0]["phase"] == "init"
    assert all("iter" in e for e in events)


# ---------- Phase 4: Dashboard ----------------------------------------------


def test_dashboard_has_cases_and_summary():
    body = client.get("/api/dashboard").json()
    assert body["summary"]["total_cases"] == len(body["cases"])
    assert body["summary"]["total_cases"] >= 10
    # DEC-V61-035 (2026-04-22 deep-review correction): default-run resolution
    # now prefers `audit_real_run` over `reference_pass`, so the dashboard
    # verdict distribution reflects HONEST solver-in-the-loop results, not
    # curated narrative PASSes. Expect FAILs to dominate: every
    # audit_real_run on the current adapter is FAIL/PARTIAL per the
    # 2026-04-22 review. HAZARD cases may or may not survive (cylinder/
    # NACA silent-pass gates), PASS cases may be zero.
    assert body["summary"]["fail_cases"] >= 1


def test_dashboard_includes_gate_queue_and_timeline():
    body = client.get("/api/dashboard").json()
    assert {"Q-1", "Q-2"}.issubset({g["qid"] for g in body["gate_queue"]})
    assert len(body["timeline"]) >= 6
    assert all("date" in t and "decision_id" in t for t in body["timeline"])


def test_dashboard_reports_current_phase():
    body = client.get("/api/dashboard").json()
    # current_phase should be a string (might be "" if STATE.md evolves);
    # we just check the field is present and types are sensible.
    assert isinstance(body["current_phase"], str)
    assert body["autonomous_governance_counter"] in (None, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
