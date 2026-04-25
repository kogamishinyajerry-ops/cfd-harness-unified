"""Stage 4 · preflight route tests.

Covers route 200 + 5-category coverage + cross-case verdict variance
(no greenwashing — different cases really do show different gates).
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from ui.backend.main import app

client = TestClient(app)


def test_lid_driven_cavity_preflight_200() -> None:
    r = client.get("/api/cases/lid_driven_cavity/preflight")
    assert r.status_code == 200
    body = r.json()
    assert body["case_id"] == "lid_driven_cavity"
    assert "checks" in body
    assert "counts" in body
    assert body["n_categories"] >= 5  # Stage 4 close trigger


def test_five_categories_covered() -> None:
    """Stage 4 close trigger: ≥5 distinct categories surfaced."""
    r = client.get("/api/cases/lid_driven_cavity/preflight")
    body = r.json()
    cats = {c["category"] for c in body["checks"]}
    expected = {"adapter", "schema", "gold_standard", "physics", "mesh"}
    assert expected.issubset(cats), f"missing categories: {expected - cats}"


def test_count_rollups_match_check_list() -> None:
    r = client.get("/api/cases/lid_driven_cavity/preflight")
    body = r.json()
    counts = body["counts"]
    n = len(body["checks"])
    sum_counts = counts["pass"] + counts["fail"] + counts["partial"] + counts["skip"]
    assert sum_counts == n
    assert counts["total"] == n


def test_cross_case_verdict_variance() -> None:
    """No greenwashing — different cases show different overall verdicts.
    DHC has all preconditions satisfied (Stage 6 v1 pass);
    cylinder/jet have flagged physics_precondition rows (fail)."""
    seen_verdicts = set()
    for cid in (
        "lid_driven_cavity",
        "differential_heated_cavity",
        "circular_cylinder_wake",
        "rayleigh_benard_convection",
    ):
        r = client.get(f"/api/cases/{cid}/preflight")
        assert r.status_code == 200
        seen_verdicts.add(r.json()["overall"])
    # Should see at least 2 distinct verdicts; if everything's green
    # something's wrong (greenwashing regression).
    assert len(seen_verdicts) >= 2, f"only saw {seen_verdicts}"


def test_failures_carry_evidence() -> None:
    """Codex anti-pattern guard: red rows must surface evidence_ref so
    the user can act, not just see redness."""
    found_failure_with_evidence = False
    for cid in ("lid_driven_cavity", "circular_cylinder_wake", "impinging_jet"):
        r = client.get(f"/api/cases/{cid}/preflight")
        body = r.json()
        for check in body["checks"]:
            if check["status"] == "fail":
                assert (
                    check.get("evidence") or check.get("consequence")
                ), f"{cid} fail row missing evidence: {check}"
                found_failure_with_evidence = True
                break
        if found_failure_with_evidence:
            break
    # Don't fail this test if no fails happened to land — but we expect
    # at least one across the 3 cases above based on commit-time data.
    # If this becomes flaky, widen the case list.
    assert found_failure_with_evidence, "expected ≥1 fail with evidence across 3 cases"


def test_partial_failure_does_not_500_whole_endpoint(monkeypatch) -> None:
    """Opus 4.7 review 2026-04-25 ACCEPT_WITH_COMMENTS edge case #4:
    when a single category builder throws, that single category should
    degrade to 'indeterminate' status while the other 4 categories
    continue to evaluate normally. Guards the per-category isolation
    we added via _safe_run."""
    from ui.backend.services import preflight as preflight_svc

    def boom(*_a, **_kw):
        raise RuntimeError("synthetic failure for graceful-degradation test")

    # Force the mesh-checks builder to throw. The preflight endpoint
    # should still return 200, with the mesh category showing
    # 'indeterminate' rather than failing the whole request.
    monkeypatch.setattr(preflight_svc, "_mesh_checks", boom)
    r = client.get("/api/cases/lid_driven_cavity/preflight")
    assert r.status_code == 200, f"got {r.status_code} body={r.text[:200]}"
    body = r.json()
    mesh_rows = [c for c in body["checks"] if c["category"] == "mesh"]
    assert len(mesh_rows) >= 1
    assert any(c["status"] == "indeterminate" for c in mesh_rows)
    # The other four categories must still report their normal verdicts
    for cat in ("adapter", "schema", "gold_standard", "physics"):
        cat_rows = [c for c in body["checks"] if c["category"] == cat]
        assert len(cat_rows) >= 1
        # None of the non-mesh rows should be tainted by the mesh failure
        for c in cat_rows:
            assert c["status"] != "indeterminate", (
                f"{cat} got indeterminate; isolation broken"
            )


def test_unknown_case_returns_response() -> None:
    """The preflight service is permissive — for an unknown case_id it
    still runs the structural checks (adapter, schema, mesh) and returns
    a fail-heavy response rather than 404. This matches the design
    intent: surface gaps as visible red rather than hiding behind a
    404."""
    r = client.get("/api/cases/clearly_unknown/preflight")
    assert r.status_code == 200
    body = r.json()
    # adapter check should be fail since case_id isn't in whitelist
    adapter_check = next(
        (c for c in body["checks"] if c["category"] == "adapter"), None
    )
    assert adapter_check is not None
    assert adapter_check["status"] == "fail"
