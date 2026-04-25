"""Stage 5 · batch-matrix route tests.

Verifies 10×4 grid completeness, monotonic-improvement guarantee, and
verdict count consistency.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from ui.backend.main import app

client = TestClient(app)


def test_returns_200_and_full_grid() -> None:
    r = client.get("/api/batch-matrix")
    assert r.status_code == 200
    body = r.json()
    assert body["n_cases"] == 10
    assert body["n_densities"] == 4
    assert len(body["rows"]) == 10
    for row in body["rows"]:
        assert len(row["cells"]) == 4


def test_density_columns_in_canonical_order() -> None:
    body = client.get("/api/batch-matrix").json()
    assert body["densities"] == ["mesh_20", "mesh_40", "mesh_80", "mesh_160"]
    for row in body["rows"]:
        density_ids = [c["density_id"] for c in row["cells"]]
        assert density_ids == ["mesh_20", "mesh_40", "mesh_80", "mesh_160"]


def test_count_rollups_match_cells() -> None:
    body = client.get("/api/batch-matrix").json()
    counts = body["counts"]
    expected_total = body["n_cases"] * body["n_densities"]
    sum_counts = counts["PASS"] + counts["HAZARD"] + counts["FAIL"] + counts["UNKNOWN"]
    assert sum_counts == expected_total
    assert counts["total"] == expected_total


def test_each_row_carries_workbench_basics_flag() -> None:
    body = client.get("/api/batch-matrix").json()
    for row in body["rows"]:
        assert isinstance(row["has_workbench_basics"], bool)
    # Stage 2 closed at 10/10 — all rows should have basics.
    assert all(row["has_workbench_basics"] for row in body["rows"])


def test_monotonic_improvement_invariant() -> None:
    """Validation invariant: for any case, refining the mesh should not
    make the verdict regress (FAIL→PASS is fine; PASS→FAIL would be a
    bug in either the comparator or the fixtures). Stage 5 close
    trigger explicitly notes "10/10 monotonic improvement"."""
    rank = {"FAIL": 0, "UNKNOWN": 1, "HAZARD": 2, "PASS": 3}
    body = client.get("/api/batch-matrix").json()
    for row in body["rows"]:
        verdicts = [c["verdict"] for c in row["cells"]]
        ranks = [rank[v] for v in verdicts]
        for i in range(1, len(ranks)):
            assert ranks[i] >= ranks[i - 1], (
                f"{row['case_id']}: verdict regressed from "
                f"{verdicts[i-1]} to {verdicts[i]} when going from "
                f"mesh_{row['cells'][i-1]['n_cells_1d']} to "
                f"mesh_{row['cells'][i]['n_cells_1d']}"
            )


def test_at_least_one_case_passes_at_finest_mesh() -> None:
    """Sanity check: not every case can be FAIL even at mesh_160 — that
    would mean comparator never accepts anything, which is its own bug.
    Confirms the harness has a meaningful PASS path."""
    body = client.get("/api/batch-matrix").json()
    finest_verdicts = [row["cells"][-1]["verdict"] for row in body["rows"]]
    assert any(v == "PASS" for v in finest_verdicts), (
        "no case PASSes at finest mesh — comparator may be broken"
    )


def test_deviation_pct_is_finite_or_none() -> None:
    body = client.get("/api/batch-matrix").json()
    for row in body["rows"]:
        for cell in row["cells"]:
            dev = cell.get("deviation_pct")
            if dev is not None:
                assert isinstance(dev, (int, float))
                assert dev == dev  # not NaN


def test_pass_cells_have_no_reason_others_do() -> None:
    """Opus 4.7 review 2026-04-25 LDC tolerance probe outcome:
    HAZARD/FAIL cells must carry a verdict_reason so users don't see
    '0.19% HAZARD' as an unexplained tolerance bug. PASS cells leave
    it null (no explanation needed)."""
    body = client.get("/api/batch-matrix").json()
    seen_pass_with_no_reason = False
    seen_non_pass_with_reason = False
    for row in body["rows"]:
        for cell in row["cells"]:
            if cell["verdict"] == "PASS":
                # PASS should have no reason
                assert cell.get("verdict_reason") in (None, ""), (
                    f"{row['case_id']}/{cell['density_id']} PASS but reason set: "
                    f"{cell['verdict_reason']!r}"
                )
                seen_pass_with_no_reason = True
            else:
                # HAZARD / FAIL / UNKNOWN must explain themselves
                assert cell.get("verdict_reason"), (
                    f"{row['case_id']}/{cell['density_id']} {cell['verdict']} "
                    f"but no verdict_reason"
                )
                seen_non_pass_with_reason = True
    assert seen_pass_with_no_reason, "no PASS cells found — fixtures regressed"
    assert seen_non_pass_with_reason, (
        "no non-PASS cells found — should see at least HAZARD or FAIL"
    )


def test_lid_driven_cavity_finest_mesh_reason_cites_precondition() -> None:
    """Regression guard for the actual Opus probe finding: LDC mesh_160
    has dev=0.19% which looks like a tolerance bug, but is HAZARD because
    secondary vortices precondition is unsatisfied (DEC-V61-050 batch 4
    noise floor). The reason must mention 'precondition' so the user knows
    where to look."""
    body = client.get("/api/batch-matrix").json()
    ldc = next((r for r in body["rows"] if r["case_id"] == "lid_driven_cavity"), None)
    assert ldc is not None
    finest = ldc["cells"][-1]
    assert finest["density_id"] == "mesh_160"
    assert finest["verdict"] == "HAZARD"
    assert abs(finest["deviation_pct"]) < 1.0, (
        f"LDC mesh_160 deviation should be ~0.2%, got {finest['deviation_pct']}"
    )
    reason = finest["verdict_reason"] or ""
    assert "precondition" in reason.lower(), (
        f"LDC mesh_160 reason should cite precondition gap, got {reason!r}"
    )
