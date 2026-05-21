"""M4 — Real mesh_contract tests.

Two layers:
  - parser unit tests: feed canonical / failure / malformed checkMesh logs
    to `_parse_check_mesh_log` and check it extracts the right structured
    data without ever raising.
  - backend integration tests: monkeypatch `_run_docker_command` so we
    don't depend on Docker; assert that `run()` writes
    `artifacts/mesh_quality.json` with the expected shape for the three
    checkMesh outcomes (OK / failed checks / OSError / timeout).

The mesh audit gate (`audit/mesh.py`) is exercised in M4.2's tests; here we
only verify the truth-source persistence layer (M4.1).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cfdtrust.backends import openfoam as ofa


# ---------- canonical checkMesh outputs ----------


_CANONICAL_OK_LOG = """\
/*---------------------------------------------------------------------------*\\
|  =========                 |                                                 |
|  \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|   \\\\    /   O peration     | Version:  11                                    |
\\*---------------------------------------------------------------------------*/

Create mesh for time = 0

Time = 0

Mesh stats
    points:           23682
    faces:            46640
    internal faces:   34864
    cells:            11600
    faces per cell:   7.000
    boundary patches: 6
    point zones:      0
    face zones:       0
    cell zones:       1

Overall number of cells of each type:
    hexahedra:     11600
    prisms:        0

Checking topology...
    Boundary definition OK.
    Cell to face addressing OK.
    Point usage OK.
    Upper triangular ordering OK.
    Face vertices OK.
    Number of regions: 1 (OK).

Checking geometry...
    Overall domain bounding box (-7.62 -0.00635 -0.00635) (12.7 0.0381 0.00635)
    Mesh has 2 geometric (non-empty/wedge) directions (1 1 0)
    Mesh has 2 solution (non-empty/wedge) directions (1 1 0)
    All edges aligned with or perpendicular to non-empty directions.
    Boundary openness (-3.45e-19 1.23e-18 0) OK.
    Max cell openness = 2.5e-16 OK.
    Max aspect ratio = 22.2268 OK.
    Minimum face area = 1.6e-07. Maximum face area = 1.05e-03.  Face area magnitudes OK.
    Min volume = 1.0e-10. Max volume = 6.7e-07.  Total volume = 2.5e-05.  Cell volumes OK.
    Mesh non-orthogonality Max: 0 average: 0
    Non-orthogonality check OK.
    Face pyramids OK.
    Max skewness = 8.68421e-14 OK.
    Coupled point location match (average 0) OK.

Mesh OK.

End

"""


_FAILED_CHECKS_LOG = """\
Mesh stats
    points:           5000
    faces:            12000
    cells:            3000
    boundary patches: 4

Checking geometry...
    Max aspect ratio = 12345.7 FAILED.
    Mesh non-orthogonality Max: 92 average: 35
    ***Number of non-orthogonality errors: 47
    Max skewness = 9.5 FAILED.
    ***Number of severely skew faces: 12

***Number of incorrectly-oriented faces: 23

Failed 3 mesh checks.

End

"""


# ---------- _parse_check_mesh_log: canonical OK ----------


def test_parse_checkmesh_canonical_ok_extracts_stats():
    out = ofa._parse_check_mesh_log(_CANONICAL_OK_LOG)
    assert out["stats"] == {
        "points": 23682,
        "faces": 46640,
        "internal_faces": 34864,
        "cells": 11600,
        "boundary_patches": 6,
    }


def test_parse_checkmesh_canonical_ok_extracts_geometry():
    out = ofa._parse_check_mesh_log(_CANONICAL_OK_LOG)
    g = out["geometry"]
    assert g["max_non_orthogonality"] == pytest.approx(0.0)
    assert g["avg_non_orthogonality"] == pytest.approx(0.0)
    assert g["max_skewness"] == pytest.approx(8.68421e-14)
    assert g["max_aspect_ratio"] == pytest.approx(22.2268)
    assert g["max_cell_openness"] == pytest.approx(2.5e-16)


def test_parse_checkmesh_canonical_ok_sets_overall_true():
    out = ofa._parse_check_mesh_log(_CANONICAL_OK_LOG)
    assert out["overall_mesh_ok"] is True
    assert out["failed_checks_count"] == 0


# ---------- _parse_check_mesh_log: failed checks ----------


def test_parse_checkmesh_failed_checks_sets_overall_false():
    out = ofa._parse_check_mesh_log(_FAILED_CHECKS_LOG)
    assert out["overall_mesh_ok"] is False
    assert out["failed_checks_count"] == 3


def test_parse_checkmesh_failed_checks_still_extracts_geometry():
    """Honesty: bad-quality runs still must expose the numbers so the
    audit gate can show WHY it failed (max_skewness=9.5 vs target 4.0)."""
    out = ofa._parse_check_mesh_log(_FAILED_CHECKS_LOG)
    g = out["geometry"]
    assert g["max_skewness"] == pytest.approx(9.5)
    assert g["max_aspect_ratio"] == pytest.approx(12345.7)
    assert g["max_non_orthogonality"] == pytest.approx(92.0)
    assert g["avg_non_orthogonality"] == pytest.approx(35.0)


# ---------- _parse_check_mesh_log: robustness ----------


def test_parse_checkmesh_empty_log_returns_safe_defaults():
    out = ofa._parse_check_mesh_log("")
    assert out["stats"] == {}
    assert out["geometry"] == {}
    assert out["overall_mesh_ok"] is False
    assert out["failed_checks_count"] == 0


def test_parse_checkmesh_partial_log_keeps_what_it_can():
    """A log that contains only the stats block but no geometry section
    (e.g. checkMesh crashed mid-run) must yield partial data, NOT raise."""
    log = "Mesh stats\n    points:           100\n    cells:            50\n"
    out = ofa._parse_check_mesh_log(log)
    assert out["stats"]["points"] == 100
    assert out["stats"]["cells"] == 50
    assert out["geometry"] == {}
    assert out["overall_mesh_ok"] is False


def test_parse_checkmesh_per_check_ok_does_not_set_overall():
    """`Max skewness = 8.68e-14 OK.` is a PER-CHECK ok suffix, NOT the
    terminal `Mesh OK.` line. The parser must distinguish them — a log
    where every per-check passes but is missing the terminal line should
    NOT be reported as overall OK."""
    log = (
        "Max skewness = 1.0 OK.\n"
        "Max aspect ratio = 100 OK.\n"
        "Mesh non-orthogonality Max: 5 average: 1\n"
        "Non-orthogonality check OK.\n"
        # NO `Mesh OK.` terminal line — checkMesh died here
    )
    out = ofa._parse_check_mesh_log(log)
    assert out["overall_mesh_ok"] is False
    # But per-check values were still extracted:
    assert out["geometry"]["max_skewness"] == pytest.approx(1.0)


def test_parse_checkmesh_garbage_numbers_skipped_not_raised():
    """A malformed numeric value must be ignored, not crash the parser."""
    log = "Max skewness = NaN_token OK.\nMesh OK.\n"
    out = ofa._parse_check_mesh_log(log)
    # The non-numeric matched the regex char class? No — `_` is not in
    # `[\d.eE+\-]`, so the regex won't match at all. This is the
    # belt-side check: ensure no crash on malformed-but-checkmesh-shaped
    # input.
    assert "max_skewness" not in out["geometry"]
    assert out["overall_mesh_ok"] is True


# ---------- _persist_mesh_quality: file shape ----------


def test_persist_mesh_quality_ok_path_writes_full_dict(tmp_path: Path):
    parsed = ofa._parse_check_mesh_log(_CANONICAL_OK_LOG)
    out = ofa._persist_mesh_quality(
        tmp_path,
        invoked=True,
        returncode=0,
        log_relative="artifacts/mesh_quality.log",
        parsed=parsed,
    )
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["checkmesh_invoked"] is True
    assert data["checkmesh_status"] == "ok"
    assert data["checkmesh_returncode"] == 0
    assert data["log"] == "artifacts/mesh_quality.log"
    assert data["stats"]["cells"] == 11600
    assert data["geometry"]["max_skewness"] == pytest.approx(8.68421e-14)
    assert data["overall_mesh_ok"] is True
    assert data["failed_checks_count"] == 0


def test_persist_mesh_quality_failed_path_marks_status_failed(tmp_path: Path):
    parsed = ofa._parse_check_mesh_log(_FAILED_CHECKS_LOG)
    out = ofa._persist_mesh_quality(
        tmp_path,
        invoked=True,
        returncode=0,
        log_relative="artifacts/mesh_quality.log",
        parsed=parsed,
    )
    data = json.loads(out.read_text())
    assert data["checkmesh_status"] == "failed"
    assert data["overall_mesh_ok"] is False
    assert data["failed_checks_count"] == 3


def test_persist_mesh_quality_blocked_oserror_records_reason(tmp_path: Path):
    out = ofa._persist_mesh_quality(
        tmp_path,
        invoked=False,
        returncode=-1,
        log_relative=None,
        parsed=None,
        blocked_reason="docker_invocation_failed",
        blocked_detail="fork failed: too many processes",
    )
    data = json.loads(out.read_text())
    assert data["checkmesh_invoked"] is False
    assert data["checkmesh_status"] == "blocked"
    assert data["reason"] == "docker_invocation_failed"
    assert "too many processes" in data["detail"]
    # Honesty: NO partial stats / geometry leaking from a non-invocation.
    assert "stats" not in data
    assert "geometry" not in data


def test_persist_mesh_quality_blocked_timeout_records_reason(tmp_path: Path):
    out = ofa._persist_mesh_quality(
        tmp_path,
        invoked=True,
        returncode=-1,
        log_relative="artifacts/mesh_quality.log",
        parsed=None,
        blocked_reason="checkmesh_timed_out",
        blocked_detail="timeout_s=60",
    )
    data = json.loads(out.read_text())
    # Invoked but blocked — meaningful distinction from OSError.
    assert data["checkmesh_invoked"] is True
    assert data["checkmesh_status"] == "blocked"
    assert data["reason"] == "checkmesh_timed_out"


# ---------- run() integration: monkeypatched docker ----------


def _make_minimal_case(case_dir: Path) -> None:
    """A stub case dir that passes the env-detection layer's depth-1
    subdir check. We don't need real OpenFOAM dicts because subprocess
    is monkeypatched out entirely."""
    for sub in ("system", "constant", "0"):
        (case_dir / sub).mkdir(parents=True, exist_ok=True)


def _patch_docker(monkeypatch, *, blockmesh_rc=0, checkmesh_rc=0,
                  checkmesh_stdout="", checkmesh_stderr="",
                  simplefoam_rc=0, simplefoam_stdout=""):
    """Install a fake docker subprocess that walks the canonical 5-call
    sequence: version → image inspect → blockMesh → checkMesh → simpleFoam.
    Each call's outcome is configurable."""
    monkeypatch.setattr(ofa.shutil, "which", lambda cmd: "/usr/local/bin/docker")

    def fake_run(args, **kwargs):
        class R:
            returncode = 0
            stdout = ""
            stderr = ""
        # docker version
        if "version" in args:
            R.stdout = "26.0.0\n"
            return R()
        # docker image inspect
        if "inspect" in args:
            return R()
        # docker run ... blockMesh|checkMesh|simpleFoam
        cmd_str = args[-1] if args else ""
        if "blockMesh" in cmd_str:
            R.returncode = blockmesh_rc
            return R()
        if "checkMesh" in cmd_str:
            R.returncode = checkmesh_rc
            R.stdout = checkmesh_stdout
            R.stderr = checkmesh_stderr
            return R()
        if "simpleFoam" in cmd_str:
            R.returncode = simplefoam_rc
            R.stdout = simplefoam_stdout
            return R()
        return R()

    monkeypatch.setattr(ofa.subprocess, "run", fake_run)


def test_run_writes_mesh_quality_json_on_canonical_path(monkeypatch, tmp_path: Path):
    """Happy path: checkMesh stdout is canonical OK; mesh_quality.json
    must capture parsed stats + overall_mesh_ok=True."""
    _make_minimal_case(tmp_path)
    _patch_docker(
        monkeypatch,
        checkmesh_stdout=_CANONICAL_OK_LOG,
        simplefoam_stdout="Time = 1\nsmoothSolver:  Solving for Ux, Initial residual = 0.1, Final residual = 0.01, No Iterations 5\n",
    )

    ofa.run(tmp_path, {})

    mq = tmp_path / "artifacts" / "mesh_quality.json"
    assert mq.exists(), "mesh_quality.json must be persisted between blockMesh and simpleFoam"
    data = json.loads(mq.read_text())
    assert data["checkmesh_status"] == "ok"
    assert data["overall_mesh_ok"] is True
    assert data["stats"]["cells"] == 11600
    assert data["geometry"]["max_skewness"] == pytest.approx(8.68421e-14)

    # And the raw log was captured too.
    mlog = tmp_path / "artifacts" / "mesh_quality.log"
    assert mlog.exists()
    assert "Mesh OK." in mlog.read_text()


def test_run_writes_mesh_quality_json_on_failed_checks(monkeypatch, tmp_path: Path):
    """checkMesh exit 0 but `Failed N mesh checks.` line present — the
    persistence layer must mark status=failed and overall_mesh_ok=False,
    so the audit gate can refuse PASS on the same evidence."""
    _make_minimal_case(tmp_path)
    _patch_docker(
        monkeypatch,
        checkmesh_rc=0,
        checkmesh_stdout=_FAILED_CHECKS_LOG,
        simplefoam_stdout="Time = 1\n",
    )

    ofa.run(tmp_path, {})

    data = json.loads((tmp_path / "artifacts" / "mesh_quality.json").read_text())
    assert data["checkmesh_status"] == "failed"
    assert data["overall_mesh_ok"] is False
    assert data["failed_checks_count"] == 3


def test_run_writes_mesh_quality_json_on_oserror(monkeypatch, tmp_path: Path):
    """When checkMesh's docker invocation OSErrors, we MUST persist
    a blocked-status mesh_quality.json (not skip it) so the audit gate
    surfaces BLOCKED on the same evidence."""
    _make_minimal_case(tmp_path)

    monkeypatch.setattr(ofa.shutil, "which", lambda cmd: "/usr/local/bin/docker")

    def fake_run(args, **kwargs):
        class R:
            returncode = 0
            stdout = "26.0.0\n"
            stderr = ""
        if "version" in args:
            return R()
        if "inspect" in args:
            return R()
        cmd_str = args[-1] if args else ""
        if "blockMesh" in cmd_str:
            return R()
        if "checkMesh" in cmd_str:
            raise OSError("[Errno 12] Cannot allocate memory")
        if "simpleFoam" in cmd_str:
            R.stdout = "Time = 1\n"
            return R()
        return R()

    monkeypatch.setattr(ofa.subprocess, "run", fake_run)

    ofa.run(tmp_path, {})

    data = json.loads((tmp_path / "artifacts" / "mesh_quality.json").read_text())
    assert data["checkmesh_invoked"] is False
    assert data["checkmesh_status"] == "blocked"
    assert data["reason"] == "docker_invocation_failed"
    # And the simpleFoam stage was still permitted to run (mesh failure
    # surfacing is the mesh gate's job, not the backend's — the backend
    # captures evidence and moves on).


def test_run_writes_mesh_quality_json_on_timeout(monkeypatch, tmp_path: Path):
    """checkMesh that times out must persist blocked-status with
    reason=checkmesh_timed_out, NOT silently treat the mesh as OK."""
    import subprocess as _subprocess
    _make_minimal_case(tmp_path)

    monkeypatch.setattr(ofa.shutil, "which", lambda cmd: "/usr/local/bin/docker")

    def fake_run(args, **kwargs):
        class R:
            returncode = 0
            stdout = "26.0.0\n"
            stderr = ""
        if "version" in args:
            return R()
        if "inspect" in args:
            return R()
        cmd_str = args[-1] if args else ""
        if "blockMesh" in cmd_str:
            return R()
        if "checkMesh" in cmd_str:
            raise _subprocess.TimeoutExpired(cmd=args, timeout=60, output="partial...")
        if "simpleFoam" in cmd_str:
            R.stdout = "Time = 1\n"
            return R()
        return R()

    monkeypatch.setattr(ofa.subprocess, "run", fake_run)

    ofa.run(tmp_path, {})

    data = json.loads((tmp_path / "artifacts" / "mesh_quality.json").read_text())
    assert data["checkmesh_invoked"] is True   # process started, then timed out
    assert data["checkmesh_status"] == "blocked"
    assert data["reason"] == "checkmesh_timed_out"


def test_run_orders_checkmesh_between_blockmesh_and_simplefoam(monkeypatch, tmp_path: Path):
    """Honesty + sequencing: checkMesh must run AFTER blockMesh (needs the
    polyMesh) and BEFORE simpleFoam (so a mesh-quality FAIL surfaces in
    audit/mesh.py before the solver even attempts). Record the call order."""
    _make_minimal_case(tmp_path)

    monkeypatch.setattr(ofa.shutil, "which", lambda cmd: "/usr/local/bin/docker")
    seen: list[str] = []

    def fake_run(args, **kwargs):
        class R:
            returncode = 0
            stdout = ""
            stderr = ""
        if "version" in args:
            R.stdout = "26.0.0\n"
            return R()
        if "inspect" in args:
            return R()
        cmd_str = args[-1] if args else ""
        for tool in ("blockMesh", "checkMesh", "simpleFoam"):
            if tool in cmd_str:
                seen.append(tool)
                if tool == "checkMesh":
                    R.stdout = _CANONICAL_OK_LOG
                elif tool == "simpleFoam":
                    R.stdout = "Time = 1\n"
                return R()
        return R()

    monkeypatch.setattr(ofa.subprocess, "run", fake_run)
    ofa.run(tmp_path, {})

    assert seen == ["blockMesh", "checkMesh", "simpleFoam"], (
        f"expected blockMesh → checkMesh → simpleFoam, got {seen}"
    )


# ============================================================================
# M4.2 — audit/mesh.run() gate evaluation
# ============================================================================

from cfdtrust.audit.mesh import run as mesh_gate


def _write_mesh_quality(case_dir: Path, payload: dict) -> None:
    art = case_dir / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    (art / "mesh_quality.json").write_text(json.dumps(payload, indent=2))


def _write_solver_gate(case_dir: Path, y_plus_map: dict) -> None:
    art = case_dir / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    (art / "solver_gate.json").write_text(json.dumps({
        "status": "PASS",
        "summary": "stub solver gate for mesh test",
        "details": {"y_plus": y_plus_map},
    }, indent=2))


def _bfs_manifest(**overrides) -> dict:
    """Manifest fragment for the M4 gate. Override leaves bypass via kwargs."""
    m = {
        "case_id": "test_case",
        "solver_backend": "openfoam",
        "mesh_contract": {
            "quality_thresholds": {
                "max_non_orthogonality": 65,
                "max_skewness": 4.0,
                "max_aspect_ratio": 1000,
            },
            "y_plus_target": {
                "min": 0.5,
                "max": 5.0,
            },
        },
        "reference_comparison": {
            "wall_patch": "bottomWall",
        },
    }
    m.update(overrides)
    return m


# ---------- mocked backend still returns MOCKED ----------


def test_mesh_gate_mocked_backend_returns_mocked(tmp_path: Path):
    """Phase-0 honesty: solver_backend=mocked → no checkMesh ran → MOCKED.
    The new real-gate logic must NOT silently demand mesh_quality.json
    when the manifest declared the case is mocked."""
    m = _bfs_manifest(solver_backend="mocked")
    gate = mesh_gate(tmp_path, m)
    assert gate["status"] == "MOCKED"
    # And the mesh_report.json was still written with the contract on file.
    rep = json.loads((tmp_path / "artifacts" / "mesh_report.json").read_text())
    assert rep["gate_status"] == "MOCKED"
    assert rep["checkmesh_invoked"] is False


# ---------- BLOCKED: missing / unreadable / blocked-status mesh_quality.json ----------


def test_mesh_gate_blocked_when_mesh_quality_missing(tmp_path: Path):
    """openfoam backend but no mesh_quality.json on disk → BLOCKED, NOT PASS.
    Pre-fix the mocked gate would have lied PASS in this scenario."""
    m = _bfs_manifest()
    gate = mesh_gate(tmp_path, m)
    assert gate["status"] == "BLOCKED"
    assert gate["details"]["reason"] == "mesh_quality_json_missing"


def test_mesh_gate_blocked_when_checkmesh_oserrored(tmp_path: Path):
    """M4.1 persisted a blocked-status mesh_quality.json (OSError);
    the gate must propagate BLOCKED with the original reason."""
    _write_mesh_quality(tmp_path, {
        "checkmesh_invoked": False,
        "checkmesh_status": "blocked",
        "reason": "docker_invocation_failed",
        "detail": "fork failed",
    })
    gate = mesh_gate(tmp_path, _bfs_manifest())
    assert gate["status"] == "BLOCKED"
    assert gate["details"]["reason"] == "docker_invocation_failed"


def test_mesh_gate_blocked_when_checkmesh_timed_out(tmp_path: Path):
    _write_mesh_quality(tmp_path, {
        "checkmesh_invoked": True,
        "checkmesh_status": "blocked",
        "reason": "checkmesh_timed_out",
        "detail": "timeout_s=60",
    })
    gate = mesh_gate(tmp_path, _bfs_manifest())
    assert gate["status"] == "BLOCKED"
    assert gate["details"]["reason"] == "checkmesh_timed_out"


# ---------- quality dimension ----------


def test_mesh_gate_quality_pass_when_all_metrics_under_threshold(tmp_path: Path):
    _write_mesh_quality(tmp_path, {
        "checkmesh_status": "ok",
        "overall_mesh_ok": True,
        "stats": {"cells": 11600},
        "geometry": {
            "max_non_orthogonality": 0.0,
            "max_skewness": 8.68e-14,
            "max_aspect_ratio": 22.2,
        },
    })
    _write_solver_gate(tmp_path, {"bottomWall": {"min": 1, "max": 3, "avg": 2.0}})
    gate = mesh_gate(tmp_path, _bfs_manifest())
    assert gate["status"] == "PASS"
    assert gate["details"]["quality_dimension"]["dimension_status"] == "PASS"


def test_mesh_gate_quality_fail_on_skewness_exceeded(tmp_path: Path):
    """Manifest says max_skewness 4.0 but checkMesh reports 9.5 → FAIL."""
    _write_mesh_quality(tmp_path, {
        "checkmesh_status": "ok",
        "overall_mesh_ok": True,
        "stats": {"cells": 100},
        "geometry": {
            "max_non_orthogonality": 30.0,
            "max_skewness": 9.5,
            "max_aspect_ratio": 100.0,
        },
    })
    _write_solver_gate(tmp_path, {"bottomWall": {"min": 1, "max": 3, "avg": 2.0}})
    gate = mesh_gate(tmp_path, _bfs_manifest())
    assert gate["status"] == "FAIL"
    qd = gate["details"]["quality_dimension"]
    assert qd["dimension_status"] == "FAIL"
    assert "max_skewness" in qd["fails"]
    assert qd["metrics"]["max_skewness"]["actual"] == 9.5
    assert qd["metrics"]["max_skewness"]["ok"] is False


def test_mesh_gate_quality_fail_on_non_orthogonality_exceeded(tmp_path: Path):
    _write_mesh_quality(tmp_path, {
        "checkmesh_status": "ok",
        "overall_mesh_ok": True,
        "stats": {"cells": 100},
        "geometry": {
            "max_non_orthogonality": 88.0,   # > 65 threshold
            "max_skewness": 0.1,
            "max_aspect_ratio": 100.0,
        },
    })
    _write_solver_gate(tmp_path, {"bottomWall": {"min": 1, "max": 3, "avg": 2.0}})
    gate = mesh_gate(tmp_path, _bfs_manifest())
    assert gate["status"] == "FAIL"
    assert "max_non_orthogonality" in gate["details"]["quality_dimension"]["fails"]


def test_mesh_gate_quality_incomplete_when_metric_missing_from_log(tmp_path: Path):
    """Manifest declared a threshold but the parsed log doesn't expose
    the corresponding metric → INCOMPLETE → overall FAIL (cannot validate
    what we cannot measure)."""
    _write_mesh_quality(tmp_path, {
        "checkmesh_status": "ok",
        "overall_mesh_ok": True,
        "stats": {"cells": 100},
        "geometry": {
            # max_skewness intentionally missing (parser gap)
            "max_non_orthogonality": 0.0,
            "max_aspect_ratio": 22.0,
        },
    })
    _write_solver_gate(tmp_path, {"bottomWall": {"min": 1, "max": 3, "avg": 2.0}})
    gate = mesh_gate(tmp_path, _bfs_manifest())
    assert gate["status"] == "FAIL"  # incomplete → overall FAIL per honesty rule
    qd = gate["details"]["quality_dimension"]
    assert qd["dimension_status"] == "INCOMPLETE"
    assert "max_skewness" in qd["incompletes"]


def test_mesh_gate_fails_when_checkmesh_reports_failed_checks(tmp_path: Path):
    """checkMesh ran, exposed all metrics within manifest thresholds, BUT
    its own `Failed N mesh checks.` line was emitted (e.g. incorrectly-
    oriented faces). Overall must be FAIL — checkMesh found something we
    didn't have a manifest threshold for."""
    _write_mesh_quality(tmp_path, {
        "checkmesh_status": "failed",
        "overall_mesh_ok": False,
        "failed_checks_count": 2,
        "stats": {"cells": 100},
        "geometry": {
            "max_non_orthogonality": 0.0,
            "max_skewness": 0.1,
            "max_aspect_ratio": 22.0,
        },
    })
    _write_solver_gate(tmp_path, {"bottomWall": {"min": 1, "max": 3, "avg": 2.0}})
    gate = mesh_gate(tmp_path, _bfs_manifest())
    assert gate["status"] == "FAIL"
    assert gate["details"]["checkmesh_overall_ok"] is False


# ---------- y+ dimension ----------


def test_mesh_gate_y_plus_fail_when_avg_above_target(tmp_path: Path):
    """The live-BFS reproducer: y+ 20.7 outside [0.5, 5.0] → FAIL."""
    _write_mesh_quality(tmp_path, {
        "checkmesh_status": "ok",
        "overall_mesh_ok": True,
        "stats": {"cells": 11600},
        "geometry": {
            "max_non_orthogonality": 0.0,
            "max_skewness": 8.68e-14,
            "max_aspect_ratio": 22.2,
        },
    })
    _write_solver_gate(tmp_path, {"bottomWall": {"min": 1.09, "max": 25.88, "avg": 20.77}})
    gate = mesh_gate(tmp_path, _bfs_manifest())
    assert gate["status"] == "FAIL"
    yd = gate["details"]["y_plus_dimension"]
    assert yd["dimension_status"] == "FAIL"
    assert yd["patch_evaluated"] == "bottomWall"
    assert yd["actual_avg"] == pytest.approx(20.77)


def test_mesh_gate_y_plus_incomplete_when_no_solver_gate(tmp_path: Path):
    """mesh_quality.json present (quality dim can be evaluated) but
    solver_gate.json missing → y+ dim INCOMPLETE → overall FAIL.

    Honesty: a missing solver gate is NOT the same as 'y+ is fine'."""
    _write_mesh_quality(tmp_path, {
        "checkmesh_status": "ok",
        "overall_mesh_ok": True,
        "stats": {"cells": 100},
        "geometry": {
            "max_non_orthogonality": 0.0,
            "max_skewness": 0.1,
            "max_aspect_ratio": 22.0,
        },
    })
    gate = mesh_gate(tmp_path, _bfs_manifest())
    assert gate["status"] == "FAIL"
    yd = gate["details"]["y_plus_dimension"]
    assert yd["dimension_status"] == "INCOMPLETE"
    assert yd["reason"] == "no_solver_y_plus_data"


def test_mesh_gate_y_plus_uses_wall_patch_hint(tmp_path: Path):
    """Manifest's reference_comparison.wall_patch must steer patch
    selection — even if another patch contains 'wall' in its name first."""
    _write_mesh_quality(tmp_path, {
        "checkmesh_status": "ok",
        "overall_mesh_ok": True,
        "stats": {"cells": 100},
        "geometry": {
            "max_non_orthogonality": 0.0,
            "max_skewness": 0.1,
            "max_aspect_ratio": 22.0,
        },
    })
    # topWall would also match the "contains wall" fallback; the hint
    # must keep us on bottomWall.
    _write_solver_gate(tmp_path, {
        "topWall": {"min": 80, "max": 420, "avg": 250},
        "bottomWall": {"min": 0.6, "max": 4.5, "avg": 2.5},
    })
    gate = mesh_gate(tmp_path, _bfs_manifest())
    assert gate["details"]["y_plus_dimension"]["patch_evaluated"] == "bottomWall"
    assert gate["status"] == "PASS"


def test_mesh_gate_y_plus_falls_back_to_first_wall_named_patch(tmp_path: Path):
    """When the manifest doesn't pin a wall_patch, fall back to the first
    patch whose name contains 'wall' (case-insensitive)."""
    m = _bfs_manifest()
    m["reference_comparison"] = {}  # no wall_patch hint
    _write_mesh_quality(tmp_path, {
        "checkmesh_status": "ok",
        "overall_mesh_ok": True,
        "stats": {"cells": 100},
        "geometry": {
            "max_non_orthogonality": 0.0,
            "max_skewness": 0.1,
            "max_aspect_ratio": 22.0,
        },
    })
    _write_solver_gate(tmp_path, {
        "inlet": {"min": 0, "max": 0, "avg": 0},
        "wallA": {"min": 1, "max": 3, "avg": 2.0},
    })
    gate = mesh_gate(tmp_path, m)
    assert gate["details"]["y_plus_dimension"]["patch_evaluated"] == "wallA"


# ---------- combined PASS path ----------


def test_mesh_gate_pass_when_both_dimensions_pass(tmp_path: Path):
    """Counterfactual flat-plate-grade case: quality + y+ both inside
    targets → overall PASS. Also asserts mesh_report.json has the full
    evidence so the cockpit can render it."""
    _write_mesh_quality(tmp_path, {
        "checkmesh_status": "ok",
        "overall_mesh_ok": True,
        "stats": {"cells": 50000},
        "geometry": {
            "max_non_orthogonality": 12.5,
            "max_skewness": 0.8,
            "max_aspect_ratio": 50.0,
        },
        "failed_checks_count": 0,
    })
    _write_solver_gate(tmp_path, {"bottomWall": {"min": 0.6, "max": 4.5, "avg": 2.5}})
    gate = mesh_gate(tmp_path, _bfs_manifest())
    assert gate["status"] == "PASS"

    rep = json.loads((tmp_path / "artifacts" / "mesh_report.json").read_text())
    assert rep["gate_status"] == "PASS"
    assert rep["stats"]["cells"] == 50000
    assert rep["quality_dimension"]["dimension_status"] == "PASS"
    assert rep["y_plus_dimension"]["dimension_status"] == "PASS"


# ---------- honesty / regression fences ----------


def test_mesh_gate_does_not_silently_pass_when_artifacts_missing(tmp_path: Path):
    """Honesty fence: removing the mesh.run quality evaluation must NOT
    allow a PASS to leak through. With no artifacts AND openfoam backend,
    the status MUST be BLOCKED, never PASS or MOCKED."""
    gate = mesh_gate(tmp_path, _bfs_manifest())
    assert gate["status"] not in ("PASS", "MOCKED")
    assert gate["status"] == "BLOCKED"


def test_mesh_gate_does_not_silently_pass_when_thresholds_unchecked(tmp_path: Path):
    """If the manifest declares a y+ target but the solver never produced
    y+ data, the gate cannot be PASS. This is the same honesty rule
    M2.3a closed at the solver layer, applied to the mesh layer."""
    _write_mesh_quality(tmp_path, {
        "checkmesh_status": "ok",
        "overall_mesh_ok": True,
        "stats": {"cells": 100},
        "geometry": {
            "max_non_orthogonality": 0.0,
            "max_skewness": 0.1,
            "max_aspect_ratio": 22.0,
        },
    })
    # NO solver_gate.json on disk.
    gate = mesh_gate(tmp_path, _bfs_manifest())
    assert gate["status"] == "FAIL"  # not PASS, not MOCKED


def test_y_plus_incomplete_advice_does_not_recommend_cfdtrust_run_only(tmp_path: Path):
    """Gap #12 (case_011 CHT dogfood): the INCOMPLETE-y+ advice used to
    say only `cfdtrust run`, which is wrong for ingested cases — those
    cases were already externally run. Advice must mention either
    re-meshing/re-ingest path or manifest-y_plus_target removal, so
    ingest users get an actionable next step rather than being told to
    invoke a mode that would overwrite their existing time directories."""
    _write_mesh_quality(tmp_path, {
        "checkmesh_status": "ok",
        "overall_mesh_ok": True,
        "stats": {"cells": 100},
        "geometry": {
            "max_non_orthogonality": 0.0,
            "max_skewness": 0.1,
            "max_aspect_ratio": 22.0,
        },
    })
    # No solver_gate.json → y+ INCOMPLETE branch.
    gate = mesh_gate(tmp_path, _bfs_manifest())
    yd = gate["details"]["y_plus_dimension"]
    assert yd["reason"] == "no_solver_y_plus_data"
    advice = yd["next_step"]
    # Must surface ingested-case path.
    assert "ingest" in advice.lower(), (
        f"ingest-case path missing from y+ INCOMPLETE advice: {advice!r}"
    )
    # Must offer the manifest-removal escape hatch.
    assert "y_plus_target" in advice or "mesh_contract" in advice, (
        f"manifest-removal escape hatch missing from advice: {advice!r}"
    )
