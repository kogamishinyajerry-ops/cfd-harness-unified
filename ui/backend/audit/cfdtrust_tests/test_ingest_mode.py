"""DEC-V61-201-SUB-INGEST tests — cfdtrust ingest mode.

Three layers:
  - backend ingest: monkeypatch _run_docker_command + _docker_available
                    + _image_present and verify the full ingest pipeline
                    against a synthetic case directory.
  - solver dispatcher: solver.ingest refuses non-openfoam backends; passes
                       through openfoam to the backend helper.
  - report aggregation: assemble() treats solver_execution=ingested
                        correctly — caps overall_status at WARN, caps
                        validation_status at partial, surfaces
                        ingest_manifest in artifacts index.

All tests are subprocess-free; no Docker daemon required.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cfdtrust.backends import openfoam as ofa
from cfdtrust.audit import solver as solver_mod
from cfdtrust.audit.report import assemble


# ---------- canonical fixtures ----------


_CANONICAL_CHECKMESH_OK = (
    "Mesh stats\n"
    "    points:           23682\n"
    "    faces:            46640\n"
    "    internal faces:   34864\n"
    "    cells:            11600\n"
    "    boundary patches: 6\n"
    "\n"
    "Mesh non-orthogonality Max: 0 average: 0\n"
    "Max skewness = 8.68421e-14 OK.\n"
    "Max aspect ratio = 22.2268 OK.\n"
    "Max cell openness = 2.5e-16 OK.\n"
    "Mesh OK.\n"
)

_CANONICAL_SIMPLEFOAM_LOG = (
    "Time = 1\n"
    "smoothSolver:  Solving for Ux, Initial residual = 1.0e-1, Final residual = 1.0e-2, No Iterations 5\n"
    "GAMG:  Solving for p, Initial residual = 4.5e-1, Final residual = 3.0e-3, No Iterations 12\n"
    "Time = 2\n"
    "smoothSolver:  Solving for Ux, Initial residual = 5.0e-3, Final residual = 5.0e-4, No Iterations 5\n"
    "GAMG:  Solving for p, Initial residual = 2.0e-3, Final residual = 5.0e-5, No Iterations 6\n"
    "Time = 3\n"
    "smoothSolver:  Solving for Ux, Initial residual = 1.0e-7, Final residual = 1.0e-8, No Iterations 5\n"
    "GAMG:  Solving for p, Initial residual = 1.0e-7, Final residual = 1.0e-8, No Iterations 6\n"
)

# Minimal valid polyMesh/boundary file (3 patches: 1 wall + 1 inlet + 1 outlet).
_CANONICAL_POLYMESH_BOUNDARY = (
    "FoamFile { class polyBoundaryMesh; object boundary; }\n"
    "3\n"
    "(\n"
    "    inlet { type patch; nFaces 10; startFace 100; }\n"
    "    outlet { type patch; nFaces 10; startFace 110; }\n"
    "    wall { type wall; nFaces 40; startFace 120; }\n"
    ")\n"
)

# Minimal valid 0/U file — boundaryField entry per patch.
_CANONICAL_0_U = (
    "FoamFile { class volVectorField; object U; }\n"
    "dimensions [0 1 -1 0 0 0 0];\n"
    "internalField uniform (1 0 0);\n"
    "boundaryField\n"
    "{\n"
    "    inlet { type fixedValue; value uniform (1 0 0); }\n"
    "    outlet { type zeroGradient; }\n"
    "    wall { type noSlip; }\n"
    "}\n"
)

_CANONICAL_0_P = (
    "FoamFile { class volScalarField; object p; }\n"
    "dimensions [0 2 -2 0 0 0 0];\n"
    "internalField uniform 0;\n"
    "boundaryField\n"
    "{\n"
    "    inlet { type zeroGradient; }\n"
    "    outlet { type fixedValue; value uniform 0; }\n"
    "    wall { type zeroGradient; }\n"
    "}\n"
)


def _make_ingestable_case(case_dir: Path, *, with_log: bool = True,
                          with_time_dir: bool = True) -> None:
    """Build a synthetic OpenFOAM case directory shaped like one an
    external runner left behind."""
    for sub in ("system", "constant", "0"):
        (case_dir / sub).mkdir(parents=True, exist_ok=True)
    (case_dir / "constant" / "polyMesh").mkdir(parents=True, exist_ok=True)
    (case_dir / "constant" / "polyMesh" / "boundary").write_text(
        _CANONICAL_POLYMESH_BOUNDARY,
    )
    (case_dir / "0" / "U").write_text(_CANONICAL_0_U)
    (case_dir / "0" / "p").write_text(_CANONICAL_0_P)

    if with_time_dir:
        (case_dir / "100").mkdir()
        (case_dir / "100" / "U").write_text("(empty placeholder)\n")
    if with_log:
        (case_dir / "log_simpleFoam.txt").write_text(_CANONICAL_SIMPLEFOAM_LOG)


def _patch_docker_for_ingest(monkeypatch, *, checkmesh_rc=0,
                              checkmesh_stdout=_CANONICAL_CHECKMESH_OK,
                              checkmesh_stderr=""):
    """Fake docker for ingest path: version → image inspect → checkMesh.

    Notice ingest does NOT call blockMesh or simpleFoam — the fake will
    fail the test if those are invoked (helpful for catching regressions).
    """
    monkeypatch.setattr(ofa.shutil, "which", lambda cmd: "/usr/local/bin/docker")

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
        if "blockMesh" in cmd_str:
            pytest.fail(
                "ingest must NOT invoke blockMesh — would clobber existing polyMesh."
            )
        if "simpleFoam" in cmd_str:
            pytest.fail(
                "ingest must NOT invoke simpleFoam — would overwrite time directories."
            )
        if "checkMesh" in cmd_str:
            R.returncode = checkmesh_rc
            R.stdout = checkmesh_stdout
            R.stderr = checkmesh_stderr
            return R()
        return R()

    monkeypatch.setattr(ofa.subprocess, "run", fake_run)


def _ingest_manifest_fixture() -> dict:
    return {
        "case_id": "synthetic_ingest_test",
        "case_family": "test",
        "solver_backend": "openfoam",
        "solver": "simpleFoam",
        "physics": {
            "regime": "steady_incompressible_laminar",
            "fluid": "test",
            "turbulence_model": "laminar",
        },
        "geometry_contract": {
            "required_patches": ["inlet", "outlet", "wall"],
            "dimensionality": "3D",
            "unit_system": "SI",
        },
        "mesh_contract": {
            "checkmesh_required": True,
            "boundary_layer_required": False,
            "y_plus_target": {"min": 0.0, "max": 5.0},
        },
        "bc_contract": {
            "inlet": {"velocity": {"type": "fixedValue"}},
            "outlet": {"pressure": {"type": "fixedValue"}},
            "wall": {"velocity": {"type": "noSlip"}},
            "turbulence_fields": ["__none_laminar__"],
        },
        "solver_contract": {
            "residual_targets": {"Ux": 1.0e-3, "p": 1.0e-3},
            "max_iterations": 1000,
            "qoi_stability": {
                "window_iterations": 100,
                "relative_drift_tolerance": 1.0e-3,
            },
        },
        "qoi": [{"name": "tau_w", "kind": "scalar_uniform"}],
        "reference_comparison": {"status": "not_finalized"},
        "required_artifacts": ["geometry_report.json"],
    }


# ---------- backend ingest: happy path ----------


def test_ingest_writes_all_artifacts_on_happy_path(monkeypatch, tmp_path: Path):
    _make_ingestable_case(tmp_path)
    _patch_docker_for_ingest(monkeypatch)

    gate = ofa.ingest(tmp_path, _ingest_manifest_fixture())

    # gate carries ingest provenance
    assert gate["details"]["execution"] == "ingested"
    assert gate["details"]["real_solver_invoked"] is False
    assert gate["details"]["external_log_source"] == "log_simpleFoam.txt"

    # all the artifacts the audit gates expect
    art = tmp_path / "artifacts"
    assert (art / "geometry_quality.json").exists()
    assert (art / "mesh_quality.json").exists()
    assert (art / "bc_quality.json").exists()
    assert (art / "solver.log").exists()
    assert (art / "residuals.csv").exists()
    assert (art / "ingest_manifest.json").exists()

    # solver.log content was transcribed from external log
    assert (art / "solver.log").read_text() == _CANONICAL_SIMPLEFOAM_LOG

    # residuals.csv has the iter / Ux / p columns
    residuals_text = (art / "residuals.csv").read_text()
    assert "iter," in residuals_text.splitlines()[0]
    assert "Ux" in residuals_text.splitlines()[0]
    assert "p" in residuals_text.splitlines()[0]

    # geometry_quality.json captured all 3 patches
    geom = json.loads((art / "geometry_quality.json").read_text())
    assert geom["polymesh_boundary_parsed"] is True
    assert set(geom["patches"].keys()) == {"inlet", "outlet", "wall"}

    # mesh_quality.json captured checkMesh OK
    mesh = json.loads((art / "mesh_quality.json").read_text())
    assert mesh["checkmesh_status"] == "ok"
    assert mesh["overall_mesh_ok"] is True

    # bc_quality.json saw the parsed U + p boundary blocks
    bc = json.loads((art / "bc_quality.json").read_text())
    assert "U" in bc["fields"]
    assert bc["fields"]["U"]["parsed"] is True

    # ingest_manifest carries provenance with checksums + honesty note
    ingest_m = json.loads((art / "ingest_manifest.json").read_text())
    assert ingest_m["external_solver_log"]["source_relative"] == "log_simpleFoam.txt"
    assert ingest_m["external_solver_log"]["sha256"] is not None
    assert len(ingest_m["external_solver_log"]["sha256"]) == 64
    assert ingest_m["polymesh_boundary"]["source_relative"] == "constant/polyMesh/boundary"
    assert ingest_m["time_directories"] == ["100.0"]
    assert "did not witness" in ingest_m["honesty_note"]


# ---------- backend ingest: BLOCKED states ----------


def test_ingest_blocked_when_no_time_directory(monkeypatch, tmp_path: Path):
    """Case with 0/ but no time > 0 → not ingestable."""
    _make_ingestable_case(tmp_path, with_time_dir=False)
    _patch_docker_for_ingest(monkeypatch)
    gate = ofa.ingest(tmp_path, _ingest_manifest_fixture())
    assert gate["status"] == "BLOCKED"
    assert gate["details"]["reason"] == "no_time_directory_found"
    # No mesh_quality.json side-effect should have happened on this early-out.
    assert not (tmp_path / "artifacts" / "mesh_quality.json").exists()


def test_ingest_blocked_when_no_solver_log(monkeypatch, tmp_path: Path):
    """Case ran (has time dir) but log file is missing."""
    _make_ingestable_case(tmp_path, with_log=False)
    _patch_docker_for_ingest(monkeypatch)
    gate = ofa.ingest(tmp_path, _ingest_manifest_fixture())
    assert gate["status"] == "BLOCKED"
    assert gate["details"]["reason"] == "no_solver_log_found"
    assert "log_simpleFoam.txt" in gate["details"]["searched"]


def test_ingest_blocked_when_docker_unavailable(monkeypatch, tmp_path: Path):
    _make_ingestable_case(tmp_path)
    monkeypatch.setattr(ofa.shutil, "which", lambda cmd: None)
    gate = ofa.ingest(tmp_path, _ingest_manifest_fixture())
    assert gate["status"] == "BLOCKED"
    assert gate["details"]["reason"] == "docker_not_available"


def test_ingest_finds_log_simpleFoam_first(monkeypatch, tmp_path: Path):
    """When multiple candidate logs exist, the more-specific one wins."""
    _make_ingestable_case(tmp_path)
    # add a second candidate that is older convention
    (tmp_path / "solver.log").write_text("PLACEHOLDER OLDER LOG")
    _patch_docker_for_ingest(monkeypatch)
    gate = ofa.ingest(tmp_path, _ingest_manifest_fixture())
    assert gate["details"]["external_log_source"] == "log_simpleFoam.txt"
    # And the transcribed solver.log content equals the chosen log
    assert (tmp_path / "artifacts" / "solver.log").read_text() == _CANONICAL_SIMPLEFOAM_LOG


# ---------- solver.ingest dispatcher ----------


def test_solver_ingest_refuses_mocked_backend(tmp_path: Path):
    m = _ingest_manifest_fixture()
    m["solver_backend"] = "mocked"
    gate = solver_mod.ingest(tmp_path, m)
    assert gate["status"] == "BLOCKED"
    assert gate["details"]["reason"] == "ingest_backend_unsupported"


def test_solver_ingest_persists_gate_json(monkeypatch, tmp_path: Path):
    """The solver_gate.json must be written so cfdtrust report reads
    the SAME truth (M2.3a invariant)."""
    _make_ingestable_case(tmp_path)
    _patch_docker_for_ingest(monkeypatch)
    solver_mod.ingest(tmp_path, _ingest_manifest_fixture())
    gate_path = tmp_path / "artifacts" / "solver_gate.json"
    assert gate_path.exists()
    persisted = json.loads(gate_path.read_text())
    assert persisted["details"]["execution"] == "ingested"


# ---------- report aggregation: honesty fences ----------


def test_report_caps_overall_status_at_warn_for_ingested(tmp_path: Path):
    """Even when every gate is PASS individually, an ingested case must
    land overall_status at WARN — the harness didn't witness the run."""
    gates = {
        "geometry_contract":     {"status": "PASS", "summary": "ok"},
        "mesh_contract":         {"status": "PASS", "summary": "ok"},
        "bc_contract":           {"status": "PASS", "summary": "ok"},
        "solver_execution":      {
            "status": "PASS",
            "summary": "ingested converged",
            "details": {
                "execution": "ingested",
                "real_solver_invoked": False,
            },
        },
        "qoi_extraction":        {"status": "PASS", "summary": "ok"},
        "reference_comparison":  {
            "status": "PASS",
            "summary": "ok",
            "details": {"real_comparison_performed": True},
        },
    }
    manifest = _ingest_manifest_fixture()
    rp = assemble(tmp_path, manifest, gates)
    report = json.loads(rp.read_text())
    assert report["solver_execution"] == "ingested"
    # Honesty fence: overall capped at WARN, not PASS.
    assert report["overall_status"] == "WARN"
    # Honesty fence: validation_status capped at "partial".
    assert report["validation_status"] == "partial"
    # Limitation surfaces the ingest caveat.
    assert any("ingested" in lim.lower() for lim in report["limitations"])


def test_report_validation_status_not_validated_when_ingested_and_ref_fails(tmp_path: Path):
    """Ingested + reference FAIL → not_validated, never validated."""
    gates = {
        "geometry_contract":     {"status": "PASS", "summary": "ok"},
        "mesh_contract":         {"status": "PASS", "summary": "ok"},
        "bc_contract":           {"status": "PASS", "summary": "ok"},
        "solver_execution":      {
            "status": "PASS",
            "summary": "ingested converged",
            "details": {"execution": "ingested", "real_solver_invoked": False},
        },
        "qoi_extraction":        {"status": "PASS", "summary": "ok"},
        "reference_comparison":  {
            "status": "FAIL",
            "summary": "reference disagrees",
            "details": {"real_comparison_performed": True},
        },
    }
    rp = assemble(tmp_path, _ingest_manifest_fixture(), gates)
    report = json.loads(rp.read_text())
    assert report["solver_execution"] == "ingested"
    assert report["validation_status"] == "not_validated"


def test_report_artifacts_index_includes_ingest_manifest_when_present(tmp_path: Path):
    """When artifacts/ingest_manifest.json exists, the trust_report.artifacts
    index must surface it for downstream tooling."""
    (tmp_path / "artifacts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "artifacts" / "ingest_manifest.json").write_text(
        json.dumps({"ingested_at": "2026-05-21T00:00:00Z"})
    )
    gates = {
        "geometry_contract":     {"status": "PASS", "summary": "ok"},
        "mesh_contract":         {"status": "PASS", "summary": "ok"},
        "bc_contract":           {"status": "PASS", "summary": "ok"},
        "solver_execution":      {
            "status": "PASS",
            "summary": "ingested",
            "details": {"execution": "ingested", "real_solver_invoked": False},
        },
        "qoi_extraction":        {"status": "PASS", "summary": "ok"},
        "reference_comparison":  {
            "status": "MOCKED",
            "summary": "no ref",
            "details": {"real_comparison_performed": False},
        },
    }
    rp = assemble(tmp_path, _ingest_manifest_fixture(), gates)
    report = json.loads(rp.read_text())
    assert "ingest_manifest" in report["artifacts"]
    assert report["artifacts"]["ingest_manifest"] == "artifacts/ingest_manifest.json"


def test_report_artifacts_index_omits_ingest_manifest_for_non_ingested(tmp_path: Path):
    """When no ingest_manifest.json on disk, the artifacts index must NOT
    include the key — keeps non-ingested trust_reports tidy."""
    gates = {
        "geometry_contract":     {"status": "PASS", "summary": "ok"},
        "mesh_contract":         {"status": "PASS", "summary": "ok"},
        "bc_contract":           {"status": "PASS", "summary": "ok"},
        "solver_execution":      {
            "status": "PASS",
            "summary": "real",
            "details": {"execution": "real", "real_solver_invoked": True},
        },
        "qoi_extraction":        {"status": "PASS", "summary": "ok"},
        "reference_comparison":  {
            "status": "PASS",
            "summary": "ref matched",
            "details": {"real_comparison_performed": True},
        },
    }
    rp = assemble(tmp_path, _ingest_manifest_fixture(), gates)
    report = json.loads(rp.read_text())
    assert "ingest_manifest" not in report["artifacts"]
    # A real, fully-passing run still lands on PASS / validated — sanity
    # check that we did not over-demote.
    assert report["overall_status"] == "PASS"
    assert report["validation_status"] == "validated"


# ---------- schema: new enum value accepted ----------


def test_trust_report_schema_accepts_ingested_solver_execution():
    """The schema must accept the new enum value (DEC-V61-201-SUB-INGEST)."""
    from importlib import resources
    import jsonschema

    with resources.files("cfdtrust.schemas").joinpath(
        "trust_report.schema.json"
    ).open("r") as f:
        schema = json.load(f)
    assert "ingested" in schema["properties"]["solver_execution"]["enum"]

    # And a synthetic report with solver_execution=ingested + overall=WARN
    # validates clean.
    synthetic_report = {
        "case_id": "synthetic",
        "generated_at": "2026-05-21T00:00:00Z",
        "overall_status": "WARN",
        "solver_execution": "ingested",
        "validation_status": "partial",
        "gates": {
            "geometry_contract":   {"status": "PASS"},
            "mesh_contract":       {"status": "PASS"},
            "bc_contract":         {"status": "PASS"},
            "solver_execution":    {"status": "PASS"},
            "qoi_extraction":      {"status": "PASS"},
            "reference_comparison":{"status": "PASS"},
        },
        "artifacts": {},
        "limitations": ["test"],
        "next_actions": ["test"],
    }
    # Should not raise — validates against the extended enum.
    jsonschema.Draft7Validator(schema).validate(synthetic_report)


def test_trust_report_schema_rejects_ingested_with_validated_status():
    """Honesty fence: validation_status=validated still requires
    solver_execution=real (Red Team F-03 carries through to ingested)."""
    from importlib import resources
    import jsonschema

    with resources.files("cfdtrust.schemas").joinpath(
        "trust_report.schema.json"
    ).open("r") as f:
        schema = json.load(f)

    bad_report = {
        "case_id": "synthetic",
        "generated_at": "2026-05-21T00:00:00Z",
        "overall_status": "PASS",
        "solver_execution": "ingested",
        "validation_status": "validated",   # MUST be rejected
        "gates": {
            "geometry_contract":   {"status": "PASS"},
            "mesh_contract":       {"status": "PASS"},
            "bc_contract":         {"status": "PASS"},
            "solver_execution":    {"status": "PASS"},
            "qoi_extraction":      {"status": "PASS"},
            "reference_comparison":{"status": "PASS"},
        },
        "artifacts": {},
        "limitations": ["test"],
        "next_actions": ["test"],
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft7Validator(schema).validate(bad_report)


def test_trust_report_schema_rejects_ingested_with_pass_overall():
    """Honesty fence: overall_status=PASS still requires solver_execution=real."""
    from importlib import resources
    import jsonschema

    with resources.files("cfdtrust.schemas").joinpath(
        "trust_report.schema.json"
    ).open("r") as f:
        schema = json.load(f)

    bad_report = {
        "case_id": "synthetic",
        "generated_at": "2026-05-21T00:00:00Z",
        "overall_status": "PASS",       # MUST be rejected for ingested
        "solver_execution": "ingested",
        "validation_status": "partial",
        "gates": {
            "geometry_contract":   {"status": "PASS"},
            "mesh_contract":       {"status": "PASS"},
            "bc_contract":         {"status": "PASS"},
            "solver_execution":    {"status": "PASS"},
            "qoi_extraction":      {"status": "PASS"},
            "reference_comparison":{"status": "PASS"},
        },
        "artifacts": {},
        "limitations": ["test"],
        "next_actions": ["test"],
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft7Validator(schema).validate(bad_report)
