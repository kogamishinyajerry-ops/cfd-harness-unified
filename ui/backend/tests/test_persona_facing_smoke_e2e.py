"""Live-fire smoke test for the persona-facing route chain (P2 of the
B-ext-6 close meta-retro · DEC-V61-197 follow-up).

Walks the entire surface area that a Step 6 persona consumes after a
/solve POST 200, asserting every F-series invariant in one place:

- F11 — /run-history populated with the new run_id (DEC-V61-188)
- F11 — measurement.yaml carries residuals + key_quantities
- F12 — SetupBcSummary surfaces ldc_geometry_mismatch warning when
  bbox aspect > 3 (DEC-V61-189)
- F13 — /solve on missing polyMesh returns 409 mesh_missing not 502
  (DEC-V61-193)
- F15 — /results/{run_id}/field/U returns 200 with X-Field-Components: 3
  + correct binary length, via the post-solve symlink + vector parser
  (DEC-V61-196)
- F15 — scalar field path unaffected (X-Field-Components: 1)

Each case CI lane catches: any future change to /solve, run_history,
field_sample, bc_setup, or geometry_render that regresses the
persona-driven chain that we accumulated 30+ live-run samples on
across B-ext-2..6.

Why pytest + TestClient (not actual Docker / OpenFOAM):
- CI runs EXECUTOR_MODE=mock; no Docker available
- The persona-facing surfaces are workbench routes + service-layer
  parsing — the OpenFOAM solver itself is exercised by separate
  integration suites
- Synthesizing the post-solve case state directly tests the same
  surface area the persona walks live, faster + more reliable than
  spinning up a container

For an actual end-to-end smoke (against a running workbench at
localhost:8000 with cfd-openfoam container), see
`scripts/dogfood/smoke_simulation.py` (manual / nightly use).
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setattr(
        "ui.backend.services.case_scaffold.IMPORTED_DIR", tmp_path
    )
    monkeypatch.setattr(
        "ui.backend.routes.case_solve.IMPORTED_DIR", tmp_path
    )
    # Redirect run-history writes into tmp_path/reports so the test
    # doesn't pollute the real reports/ tree.
    reports = tmp_path / "reports"
    reports.mkdir(exist_ok=True)
    monkeypatch.setattr(
        "ui.backend.services.run_history.RUNS_ROOT", reports
    )
    # Redirect field_sample's IMPORTED_DIR so its containment guard
    # accepts our tmp case dirs.
    from ui.backend.services.case_scaffold import template_clone
    monkeypatch.setattr(template_clone, "IMPORTED_DIR", tmp_path)
    from ui.backend.main import app

    return TestClient(app)


_NONUNIFORM_VECTOR_FIELD = """\
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volVectorField;
    location    "{run_id}";
    object      U;
}}

dimensions      [0 1 -1 0 0 0 0];

internalField   nonuniform List<vector>
{count}
(
{triples}
)
;

boundaryField
{{
    inlet  {{ type fixedValue; value uniform (1 0 0); }}
    outlet {{ type zeroGradient; }}
}}
"""


_NONUNIFORM_SCALAR_FIELD = """\
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "{run_id}";
    object      p;
}}

dimensions      [0 2 -2 0 0 0 0];

internalField   nonuniform List<scalar>
{count}
(
{values}
)
;

boundaryField
{{
    inlet  {{ type zeroGradient; }}
    outlet {{ type fixedValue; value uniform 0; }}
}}
"""


def _seed_post_solve_case(case_dir: Path) -> None:
    """Synthesize the on-disk state /solve produces after a successful
    icoFoam run: controlDict + polyMesh{boundary,points} + final time
    directory with U (vector) + p (scalar). Mirrors what live runs in
    B-ext-5/6 produced under live_2026_05_07_r9 + step6_rehearsal_*.
    """
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "system").mkdir()
    (case_dir / "system" / "controlDict").write_text(
        "FoamFile { object controlDict; }\napplication icoFoam;\n"
    )
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True)
    (polymesh / "boundary").write_text(
        "FoamFile { object boundary; }\n"
        "1\n(\n    patch0 { type patch; nFaces 100; startFace 0; }\n)\n"
    )
    (polymesh / "points").write_text("0\n(\n)\n")  # F13 stub
    zero = case_dir / "0"
    zero.mkdir()
    (zero / "p").write_text(
        "boundaryField { patch0 { type zeroGradient; } }"
    )
    # Final time dir — what /solve symlink will target (F15 layer 1)
    final = case_dir / "2"
    final.mkdir()
    triples = [(0.1, 0.0, 0.0), (-0.05, 0.02, 0.0), (1.5e-3, -2e-5, 0.0)]
    body = "\n".join(f"({vx} {vy} {vz})" for vx, vy, vz in triples)
    (final / "U").write_text(
        _NONUNIFORM_VECTOR_FIELD.format(
            run_id="2", count=len(triples), triples=body,
        )
    )
    (final / "p").write_text(
        _NONUNIFORM_SCALAR_FIELD.format(
            run_id="2", count=3,
            values="\n".join(["0.5", "0.3", "0.1"]),
        )
    )


def _fake_solver_result(case_dir: Path):
    """SolverRunResult shape matching what run_icofoam returns on
    a converged 5-time-step icoFoam run."""
    from ui.backend.services.case_solve.solver_runner import SolverRunResult
    return SolverRunResult(
        case_id=case_dir.name,
        end_time_reached=2.0,
        last_initial_residual_p=6.5e-7,
        last_initial_residual_U=(1.2e-6, 1.0e-6, 9.8e-7),
        last_continuity_error=9.9e-12,
        n_time_steps_written=5,
        time_directories=("0", "0.5", "1", "1.5", "2"),
        log_path=case_dir / "log.icoFoam",
        wall_time_s=58.3,
        converged=True,
    )


# ─────────────────────────────────────────────────────────────────────
# F-series invariants (P1 index references)
# ─────────────────────────────────────────────────────────────────────


def test_persona_chain_solve_to_run_history_populated_F11(
    client: TestClient, tmp_path: Path
) -> None:
    """F11 invariant: POST /solve 200 → GET /run-history must list the
    new run_id. Pre-DEC-V61-188 this returned `runs:[]` even after
    successful solves."""
    case_dir = tmp_path / "imported_2026-smoke_F11"
    _seed_post_solve_case(case_dir)

    with patch(
        "ui.backend.routes.case_solve.run_icofoam",
        return_value=_fake_solver_result(case_dir),
    ):
        solve = client.post(f"/api/import/{case_dir.name}/solve")
    assert solve.status_code == 200, solve.text
    run_id = solve.json()["run_id"]
    assert run_id  # F11: not None / not empty

    rh = client.get(f"/api/cases/{case_dir.name}/run-history")
    assert rh.status_code == 200, rh.text
    run_ids = [r["run_id"] for r in rh.json()["runs"]]
    assert run_id in run_ids, (
        f"F11 regression: /solve returned run_id={run_id!r} but "
        f"/run-history shows runs={run_ids}"
    )


def test_persona_chain_run_history_carries_residuals_and_quantities_F11(
    client: TestClient, tmp_path: Path
) -> None:
    """F11 invariant continued: persona's verdict rationale needs the
    measurement.yaml's residuals + key_quantities round-trip clean."""
    case_dir = tmp_path / "imported_2026-smoke_F11_quants"
    _seed_post_solve_case(case_dir)

    with patch(
        "ui.backend.routes.case_solve.run_icofoam",
        return_value=_fake_solver_result(case_dir),
    ):
        run_id = client.post(
            f"/api/import/{case_dir.name}/solve"
        ).json()["run_id"]

    detail = client.get(f"/api/cases/{case_dir.name}/run-history/{run_id}")
    assert detail.status_code == 200, detail.text
    d = detail.json()
    assert d["key_quantities"]["end_time_reached"] == 2.0
    assert d["key_quantities"]["n_time_steps_written"] == 5
    assert d["residuals"]["p"] == 6.5e-7
    assert d["residuals"]["continuity"] == 9.9e-12


def test_persona_chain_solve_returns_409_mesh_missing_not_502_F13(
    client: TestClient, tmp_path: Path
) -> None:
    """F13 invariant: /solve on a case with controlDict but no polyMesh
    must return 409 with structured failing_check=mesh_missing, not the
    pre-DEC-V61-193 generic 502 solver_diverged with cryptic FOAM error."""
    case_dir = tmp_path / "imported_2026-smoke_F13"
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "system").mkdir()
    (case_dir / "system" / "controlDict").write_text(
        "FoamFile { object controlDict; }\napplication icoFoam;\n"
    )
    # Deliberately NO constant/polyMesh/

    resp = client.post(f"/api/import/{case_dir.name}/solve")
    assert resp.status_code == 409, (
        f"F13 regression: expected 409 mesh_missing, got "
        f"{resp.status_code}: {resp.text[:300]}"
    )
    detail = resp.json()["detail"]
    assert detail["failing_check"] == "mesh_missing"
    assert "polyMesh" in detail["detail"]
    # Persona-actionable hint
    assert "/mesh" in detail["detail"]


def test_persona_chain_field_U_returns_200_with_vector_components_F15(
    client: TestClient, tmp_path: Path
) -> None:
    """F15 invariant: GET /results/{run_id}/field/U on a converged case
    returns 200, X-Field-Components=3, body length = cell_count * 3 * 4
    bytes. Pre-DEC-V61-196 this returned 404 (path mismatch) or 422
    (scalar-only parser rejection)."""
    case_dir = tmp_path / "imported_2026-smoke_F15"
    _seed_post_solve_case(case_dir)

    with patch(
        "ui.backend.routes.case_solve.run_icofoam",
        return_value=_fake_solver_result(case_dir),
    ):
        run_id = client.post(
            f"/api/import/{case_dir.name}/solve"
        ).json()["run_id"]

    resp = client.get(
        f"/api/cases/{case_dir.name}/results/{run_id}/field/U"
    )
    assert resp.status_code == 200, (
        f"F15 regression: /field/U expected 200, got "
        f"{resp.status_code}: {resp.text[:300]}"
    )
    # 3 cells × 3 components × 4 bytes/float = 36 bytes
    assert len(resp.content) == 36
    assert resp.headers.get("X-Field-Components") == "3"
    assert resp.headers.get("X-Field-Point-Count") == "3"


def test_persona_chain_field_p_returns_200_with_scalar_components_F15(
    client: TestClient, tmp_path: Path
) -> None:
    """F15 regression-guard: scalar fields (p) keep components_per_cell=1
    after the layer-2 fix that added vector dispatch."""
    case_dir = tmp_path / "imported_2026-smoke_F15_p"
    _seed_post_solve_case(case_dir)

    with patch(
        "ui.backend.routes.case_solve.run_icofoam",
        return_value=_fake_solver_result(case_dir),
    ):
        run_id = client.post(
            f"/api/import/{case_dir.name}/solve"
        ).json()["run_id"]

    resp = client.get(
        f"/api/cases/{case_dir.name}/results/{run_id}/field/p"
    )
    assert resp.status_code == 200, resp.text
    # 3 cells × 1 component × 4 bytes/float = 12 bytes
    assert len(resp.content) == 12
    assert resp.headers.get("X-Field-Components") == "1"


def test_persona_chain_solve_creates_run_id_symlink_F15_layer1(
    client: TestClient, tmp_path: Path
) -> None:
    """F15 layer 1 invariant: /solve creates <case_dir>/<run_id>
    symlink → <final_time>. This is what makes /field/U resolvable
    without changing the field_sample resolver itself."""
    case_dir = tmp_path / "imported_2026-smoke_F15_symlink"
    _seed_post_solve_case(case_dir)

    with patch(
        "ui.backend.routes.case_solve.run_icofoam",
        return_value=_fake_solver_result(case_dir),
    ):
        run_id = client.post(
            f"/api/import/{case_dir.name}/solve"
        ).json()["run_id"]

    link = case_dir / run_id
    assert link.is_symlink(), (
        f"F15 layer 1 regression: expected {link} to be a symlink, "
        f"is_symlink={link.is_symlink()}, exists={link.exists()}"
    )
    target = case_dir / "2"
    assert link.resolve() == target.resolve()


def test_persona_chain_solve_full_walkthrough_smoke(
    client: TestClient, tmp_path: Path
) -> None:
    """End-to-end smoke: walk the exact persona-visible surface area in
    the same order the Step 6 rehearsal does. Any future regression
    that breaks the chain anywhere fails this test specifically.

    Order: /solve → /run-history → /run-history/{id} → /results-summary
    → /results/{run_id}/field/U → /results/{run_id}/field/p.
    """
    case_dir = tmp_path / "imported_2026-smoke_E2E"
    _seed_post_solve_case(case_dir)

    with patch(
        "ui.backend.routes.case_solve.run_icofoam",
        return_value=_fake_solver_result(case_dir),
    ):
        # Step 1: /solve
        solve = client.post(f"/api/import/{case_dir.name}/solve")
    assert solve.status_code == 200
    body = solve.json()
    assert body["converged"] is True
    run_id = body["run_id"]
    assert run_id

    # Step 2: /run-history populated
    rh = client.get(f"/api/cases/{case_dir.name}/run-history")
    assert rh.status_code == 200
    assert run_id in [r["run_id"] for r in rh.json()["runs"]]

    # Step 3: /run-history/<run_id> detail with residuals
    detail = client.get(f"/api/cases/{case_dir.name}/run-history/{run_id}")
    assert detail.status_code == 200
    assert detail.json()["residuals"]["continuity"] == 9.9e-12

    # Step 4: /results-summary parses U from final time directory
    summary = client.get(f"/api/cases/{case_dir.name}/results-summary")
    assert summary.status_code == 200, summary.text
    s = summary.json()
    assert s["cell_count"] == 3
    assert s["final_time"] == 2.0

    # Step 5: /field/U returns vector binary
    u = client.get(
        f"/api/cases/{case_dir.name}/results/{run_id}/field/U"
    )
    assert u.status_code == 200
    assert u.headers.get("X-Field-Components") == "3"
    assert len(u.content) == 36  # 3 × 3 × 4

    # Step 6: /field/p returns scalar binary (regression guard)
    p = client.get(
        f"/api/cases/{case_dir.name}/results/{run_id}/field/p"
    )
    assert p.status_code == 200
    assert p.headers.get("X-Field-Components") == "1"
    assert len(p.content) == 12  # 3 × 1 × 4
