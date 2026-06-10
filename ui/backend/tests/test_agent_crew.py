"""Tests for Agent Crew Observatory backend (V93_CREW_UI_SPEC.md §3.8)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ui.backend.main import app

client = TestClient(app)


# ---------- smoke: real repository --------------------------------------------


def test_snapshot_returns_200():
    resp = client.get("/api/agent-crew")
    assert resp.status_code == 200


def test_snapshot_decisions_total_ge_400():
    body = client.get("/api/agent-crew").json()
    assert body["stats"]["decisions_total"] >= 400, (
        f"Expected >= 400 decision files, got {body['stats']['decisions_total']}"
    )


def test_snapshot_arcs_date_descending():
    body = client.get("/api/agent-crew").json()
    arcs = body["arcs"]
    dates = [a["date"] for a in arcs]
    assert dates == sorted(dates, reverse=True), "arcs should be in date descending order"


def test_snapshot_arc_decision_ids_start_with_dec():
    body = client.get("/api/agent-crew").json()
    for arc in body["arcs"]:
        assert arc["decision_id"].startswith("DEC-"), (
            f"decision_id {arc['decision_id']!r} doesn't start with DEC-"
        )


def test_snapshot_roles_count_is_seven():
    body = client.get("/api/agent-crew").json()
    assert len(body["roles"]) == 7


def test_snapshot_edges_count_is_nine():
    body = client.get("/api/agent-crew").json()
    assert len(body["edges"]) == 9


def test_snapshot_stats_fields_present():
    body = client.get("/api/agent-crew").json()
    stats = body["stats"]
    for key in ("decisions_total", "codex_reports_total", "autonomous_total",
                "loop_auditor_total", "kogami_total"):
        assert key in stats, f"missing stats key: {key}"
        assert isinstance(stats[key], int), f"stats.{key} should be int"


# ---------- synthetic fixture tests ------------------------------------------


@pytest.fixture()
def synthetic_repo(tmp_path: Path, monkeypatch) -> Path:
    """
    Create a minimal fake repo with:
    - one DEC with brace-expanded codex_tool_report_path
    - R0 report: CHANGES_REQUIRED
    - R1 report: APPROVE
    Returns the tmp_path (repo root).
    """
    # DEC file
    decisions_dir = tmp_path / ".planning" / "decisions"
    decisions_dir.mkdir(parents=True)

    reports_dir = tmp_path / "reports" / "codex_tool_reports"
    reports_dir.mkdir(parents=True)

    # Write R0 report (CHANGES_REQUIRED)
    r0_path = reports_dir / "t_R0.md"
    r0_path.write_text("Some findings\nVERDICT: CHANGES_REQUIRED\nP1: something\nP2: another\n", encoding="utf-8")

    # Write R1 report (APPROVE)
    r1_path = reports_dir / "t_R1.md"
    r1_path.write_text("All looks good\nVERDICT: APPROVE\n", encoding="utf-8")

    # Write DEC file with brace-expanded path
    dec_text = """\
---
decision_id: DEC-V61-999
autonomous_governance: true
confidence: high
date: 2026-06-10
loop_auditor: "FLAG (pre-implementation)"
codex_tool_report_path: reports/codex_tool_reports/t_R{0,1}.md
codex_review_relay: 86gs (gpt-5.4)
---

# DEC-V61-999 · Synthetic test DEC

Some body text.
"""
    (decisions_dir / "2026-06-10_v61_999_synthetic.md").write_text(dec_text, encoding="utf-8")

    # Monkeypatch REPO_ROOT inside the service module
    import ui.backend.services.agent_crew as svc
    monkeypatch.setattr(svc, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(svc, "DECISIONS_DIR", tmp_path / ".planning" / "decisions")
    monkeypatch.setattr(svc, "CODEX_REPORTS_DIR", tmp_path / "reports" / "codex_tool_reports")
    monkeypatch.setattr(svc, "KOGAMI_DIR", tmp_path / ".planning" / "reviews" / "kogami")

    return tmp_path


def test_synthetic_rounds_brace_expansion(synthetic_repo):
    """brace-expanded path → two rounds, R0=CHANGES_REQUIRED, R1=APPROVE."""
    import ui.backend.services.agent_crew as svc
    snap = svc.build_snapshot()
    # Find the synthetic arc
    arc = next((a for a in snap.arcs if a.decision_id == "DEC-V61-999"), None)
    assert arc is not None, "synthetic DEC-V61-999 should appear in arcs"
    assert len(arc.codex_rounds) == 2, f"expected 2 rounds, got {len(arc.codex_rounds)}"
    r0 = next((r for r in arc.codex_rounds if r.round == 0), None)
    r1 = next((r for r in arc.codex_rounds if r.round == 1), None)
    assert r0 is not None and r0.verdict == "CHANGES_REQUIRED"
    assert r1 is not None and r1.verdict == "APPROVE"


def test_synthetic_rounds_p_counts(synthetic_repo):
    """R0 has P1=1, P2=1; R1 has P1=0, P2=0."""
    import ui.backend.services.agent_crew as svc
    snap = svc.build_snapshot()
    arc = next(a for a in snap.arcs if a.decision_id == "DEC-V61-999")
    r0 = next(r for r in arc.codex_rounds if r.round == 0)
    assert r0.p1 == 1, f"expected p1=1 in R0, got {r0.p1}"
    assert r0.p2 == 1, f"expected p2=1 in R0, got {r0.p2}"


# ---------- verdict fail-closed tests ----------------------------------------


def test_verdict_unparsed_when_no_token():
    from ui.backend.services.agent_crew import _extract_verdict
    assert _extract_verdict("no verdict tokens here") == "UNPARSED"


def test_verdict_missing_report(tmp_path: Path, monkeypatch):
    """Report path not on disk → missing=True + verdict=MISSING."""
    decisions_dir = tmp_path / ".planning" / "decisions"
    decisions_dir.mkdir(parents=True)
    (tmp_path / "reports" / "codex_tool_reports").mkdir(parents=True)

    dec_text = """\
---
decision_id: DEC-V61-888
codex_tool_report_path: reports/codex_tool_reports/nonexistent.md
---

# DEC-V61-888 · Missing report test
"""
    (decisions_dir / "2026-06-10_v61_888_missing.md").write_text(dec_text, encoding="utf-8")

    import ui.backend.services.agent_crew as svc
    monkeypatch.setattr(svc, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(svc, "DECISIONS_DIR", decisions_dir)
    monkeypatch.setattr(svc, "CODEX_REPORTS_DIR", tmp_path / "reports" / "codex_tool_reports")
    monkeypatch.setattr(svc, "KOGAMI_DIR", tmp_path / ".planning" / "reviews" / "kogami")

    snap = svc.build_snapshot()
    arc = next((a for a in snap.arcs if a.decision_id == "DEC-V61-888"), None)
    assert arc is not None
    assert len(arc.codex_rounds) == 1
    assert arc.codex_rounds[0].missing is True
    assert arc.codex_rounds[0].verdict == "MISSING"


def test_approve_with_comments_not_parsed_as_approve():
    """APPROVE_WITH_COMMENTS text must NOT be extracted as plain APPROVE."""
    from ui.backend.services.agent_crew import _extract_verdict
    text = "Final verdict: APPROVE_WITH_COMMENTS\nsome other text"
    result = _extract_verdict(text)
    assert result == "APPROVE_WITH_COMMENTS", (
        f"expected APPROVE_WITH_COMMENTS, got {result!r}"
    )


def test_approve_with_comments_not_approve_standalone():
    """Regression: if text only has APPROVE_WITH_COMMENTS, result != APPROVE."""
    from ui.backend.services.agent_crew import _extract_verdict
    text = "APPROVE_WITH_COMMENTS is the verdict here"
    result = _extract_verdict(text)
    assert result != "APPROVE", f"should not be APPROVE, got {result!r}"


# ---------- arc detail 404 + injection guard ---------------------------------


def test_arc_detail_404_for_nonexistent_id():
    resp = client.get("/api/agent-crew/arc/DEC-DOES-NOT-EXIST-99999")
    assert resp.status_code == 404


def test_arc_detail_invalid_id_rejected():
    """Path traversal / invalid characters → 422, not file leak."""
    resp = client.get("/api/agent-crew/arc/../etc/passwd")
    # FastAPI may return 422 for URL decode issues, but either 404 or 422 is acceptable
    assert resp.status_code in (404, 422)


def test_arc_detail_invalid_id_with_slash_rejected():
    """Double-encoded or otherwise non-DEC id → rejected."""
    resp = client.get("/api/agent-crew/arc/NOT_A_DEC_ID")
    assert resp.status_code in (404, 422)
