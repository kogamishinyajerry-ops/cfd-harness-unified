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

    # solver.log content was transcribed from external log (R5-P1:
    # INGEST_BANNER is prepended for honesty-fence recovery; original
    # log content immediately follows).
    assert (art / "solver.log").read_text().endswith(_CANONICAL_SIMPLEFOAM_LOG)

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


# ---------- Codex R3-P1: decomposed-parallel time-dir detection ----------


def test_ingest_blocks_pure_decomposed_with_reconstructPar_next_step(
    monkeypatch, tmp_path: Path,
):
    """Codex R4-P2 (relaxed by DEC-V61-201-SUB-INGEST-P2-DECOMPOSED-NOT-
    FINALIZED): a pure-decomposed case (processor*/<time>/ but no
    top-level time dir) must BLOCK ingest WHEN the manifest's
    reference_comparison is finalized — because downstream QoI then
    reads time directories and would silently fall back to BLOCKED.

    Sharpened reason `case_decomposed_not_reconstructed_with_finalized_reference`
    distinguishes this from the pre-relaxation generic reason."""
    _make_ingestable_case(tmp_path, with_time_dir=False)
    for i in range(4):
        (tmp_path / f"processor{i}" / "100").mkdir(parents=True)
        (tmp_path / f"processor{i}" / "100" / "U").write_text("(placeholder)\n")
    _patch_docker_for_ingest(monkeypatch)

    manifest = _ingest_manifest_fixture()
    manifest["reference_comparison"] = {"status": "finalized"}
    gate = ofa.ingest(tmp_path, manifest)
    assert gate["status"] == "BLOCKED"
    assert (
        gate["details"]["reason"]
        == "case_decomposed_not_reconstructed_with_finalized_reference"
    )
    # next_step must mention reconstructPar — that's the actionable fix.
    assert "reconstructPar" in gate["details"]["next_step"]
    # Diagnostic carries the discovered time values so the user knows
    # which times will materialise after reconstructPar.
    assert "100.0" in gate["details"]["time_directories_found_under_processor"]


def test_ingest_accepts_decomposed_only_when_reference_not_finalized(
    monkeypatch, tmp_path: Path,
):
    """DEC-V61-201-SUB-INGEST-P2-DECOMPOSED-NOT-FINALIZED: when the
    manifest's reference_comparison.status is `not_finalized` (or
    placeholder), QoI + reference gates MOCK out downstream and never
    touch time directories. Decomposed-only ingest must therefore be
    accepted — the R4-P2 BLOCK is too aggressive for this path."""
    _make_ingestable_case(tmp_path, with_time_dir=False)
    for i in range(4):
        (tmp_path / f"processor{i}" / "100").mkdir(parents=True)
        (tmp_path / f"processor{i}" / "100" / "U").write_text("(placeholder)\n")
    _patch_docker_for_ingest(monkeypatch)

    manifest = _ingest_manifest_fixture()  # default reference_comparison.status="not_finalized"
    gate = ofa.ingest(tmp_path, manifest)
    # The decomposed-only BLOCK must NOT fire — ingest proceeds past
    # this gate. (Some other gate may still BLOCK on synthetic-fixture
    # quirks, but never with the decomposed reason.)
    assert (
        gate["details"].get("reason")
        != "case_decomposed_not_reconstructed_with_finalized_reference"
    )
    assert (
        gate["details"].get("reason") != "case_decomposed_not_reconstructed"
    )


def test_ingest_blocks_decomposed_only_when_reference_finalized_sharpened_reason(
    monkeypatch, tmp_path: Path,
):
    """DEC-V61-201-SUB-INGEST-P2-DECOMPOSED-NOT-FINALIZED: when the
    reference IS finalized, the BLOCK is preserved but with sharpened
    reason `case_decomposed_not_reconstructed_with_finalized_reference`
    so users see exactly why (and have two recovery options:
    reconstructPar OR demote reference to placeholder/not_finalized)."""
    _make_ingestable_case(tmp_path, with_time_dir=False)
    for i in range(2):
        (tmp_path / f"processor{i}" / "100").mkdir(parents=True)
    _patch_docker_for_ingest(monkeypatch)

    manifest = _ingest_manifest_fixture()
    manifest["reference_comparison"] = {"status": "finalized"}
    gate = ofa.ingest(tmp_path, manifest)
    assert gate["status"] == "BLOCKED"
    assert (
        gate["details"]["reason"]
        == "case_decomposed_not_reconstructed_with_finalized_reference"
    )
    # next_step lists BOTH recovery options.
    assert "reconstructPar" in gate["details"]["next_step"]
    assert (
        "placeholder" in gate["details"]["next_step"]
        or "not_finalized" in gate["details"]["next_step"]
    )


def test_ingest_recognizes_mixed_top_level_and_processor_layout(
    monkeypatch, tmp_path: Path,
):
    """When both layouts coexist (post-reconstruction artifacts left
    behind alongside the decomposed dirs), time-dir detection should
    dedup across both sources."""
    _make_ingestable_case(tmp_path)  # creates top-level 100/
    # Decomposed copies for a later time too.
    for i in range(2):
        (tmp_path / f"processor{i}" / "200").mkdir(parents=True)
        (tmp_path / f"processor{i}" / "200" / "U").write_text("(placeholder)\n")
    _patch_docker_for_ingest(monkeypatch)

    times = ofa._find_time_directories(tmp_path)
    # Union of top-level (100) + processor (200). Sorted.
    assert times == [100.0, 200.0]


def test_ingest_blocked_when_processor_dirs_have_only_time_zero(
    monkeypatch, tmp_path: Path,
):
    """Negative: even with processor*/ present, if none of them has a
    time dir > 0 (e.g., decomposed but never run), ingest must still
    BLOCK with no_time_directory_found."""
    _make_ingestable_case(tmp_path, with_time_dir=False)
    # Decomposed `0/` only — case was decomposed but solver never ran.
    for i in range(2):
        (tmp_path / f"processor{i}" / "0").mkdir(parents=True)
    _patch_docker_for_ingest(monkeypatch)
    gate = ofa.ingest(tmp_path, _ingest_manifest_fixture())
    assert gate["status"] == "BLOCKED"
    assert gate["details"]["reason"] == "no_time_directory_found"


def test_find_time_directories_ignores_non_numeric_subdirs(tmp_path: Path):
    """Sanity: regression guard around the float-parsing branch.
    Subdirs whose names aren't numeric (constant/, system/, postProcessing/,
    a stray 'backup_5000_old/') must NOT count as time dirs."""
    for name in ("constant", "system", "postProcessing", "backup_5000_old"):
        (tmp_path / name).mkdir()
    (tmp_path / "100").mkdir()
    assert ofa._find_time_directories(tmp_path) == [100.0]


def test_ingest_hybrid_layout_top_level_present_still_accepted(
    monkeypatch, tmp_path: Path,
):
    """Codex R4-P2 boundary: the post-R4 gate is "no top-level time
    dir → BLOCK". A *hybrid* case (top-level + processor*/) must still
    be accepted because top-level time dirs satisfy downstream QoI."""
    _make_ingestable_case(tmp_path)  # creates top-level 100/
    # Add leftover processor*/ from before reconstructPar.
    for i in range(2):
        (tmp_path / f"processor{i}" / "100").mkdir(parents=True)
    _patch_docker_for_ingest(monkeypatch)
    gate = ofa.ingest(tmp_path, _ingest_manifest_fixture())
    # Top-level time dir is present → gate must NOT block on the
    # decomposed-only reason.
    assert gate["details"].get("reason") != "case_decomposed_not_reconstructed"


# ---------- Codex R4-P2 (explain WARN contributors) ----------


def test_explain_tldr_warn_non_ingested_lists_only_non_pass_gates(tmp_path: Path):
    """Codex R4-P2: the WARN-non-ingested branch must identify
    contributors from gate STATUS (in report["gates"][g]["status"]),
    NOT from `gate_severities` — `_render_per_gate` never emits
    `none`/`pass` severities, so the pre-fix predicate listed every
    gate as a WARN contributor."""
    from cfdtrust.cli_explain import _render_tldr

    report = {
        "overall_status": "WARN",
        "solver_execution": "real",
        "validation_status": "unknown",
        "gates": {
            "geometry_contract":     {"status": "PASS"},
            "mesh_contract":         {"status": "WARN"},   # the actual culprit
            "bc_contract":           {"status": "PASS"},
            "solver_execution":      {"status": "PASS"},
            "qoi_extraction":        {"status": "PASS"},
            "reference_comparison":  {"status": "PASS"},
        },
    }
    # severities map from _render_per_gate — would historically have
    # marked all 6 gates with `info`/`blocker`/`quality`, never
    # `none`/`pass`.
    tldr = _render_tldr(report, gate_severities={
        "geometry_contract": "info",
        "mesh_contract":     "quality",
        "bc_contract":       "info",
        "solver_execution":  "info",
        "qoi_extraction":    "info",
        "reference_comparison": "info",
    })
    # The TLDR must mention mesh_contract (the actual WARN gate)…
    assert "mesh_contract" in tldr
    # …and must NOT mention any of the PASS gates.
    assert "geometry_contract" not in tldr
    assert "bc_contract" not in tldr
    assert "qoi_extraction" not in tldr
    assert "reference_comparison" not in tldr


def test_ingest_prepends_ingest_banner_to_solver_log(monkeypatch, tmp_path: Path):
    """Codex R5-P1: the transcribed `artifacts/solver.log` must start
    with INGEST_BANNER so read_artifacts can recover the ingest
    provenance even if solver_gate.json is later lost."""
    from cfdtrust.audit.solver import INGEST_BANNER

    _make_ingestable_case(tmp_path)
    _patch_docker_for_ingest(monkeypatch)
    ofa.ingest(tmp_path, _ingest_manifest_fixture())

    log_content = (tmp_path / "artifacts" / "solver.log").read_text()
    assert log_content.startswith(INGEST_BANNER)
    # Original log content still present after the banner.
    assert _CANONICAL_SIMPLEFOAM_LOG in log_content


def test_read_artifacts_recovers_ingested_when_gate_json_missing(
    monkeypatch, tmp_path: Path,
):
    """Codex R5-P1 + P2-FOLLOWUP: simulate `solver_gate.json` loss after
    a successful ingest. read_artifacts() must (1) classify as
    `execution="ingested"` (NOT `"real"`) by detecting the banner, AND
    (2) recompute the gate status from the residuals (NOT hard-code
    WARN). The canonical fixture log converges all targets so the
    recomputed status is PASS — the `assemble()` honesty fences will
    then demote the overall to WARN + partial-validation."""
    from cfdtrust.audit.solver import read_artifacts

    _make_ingestable_case(tmp_path)
    _patch_docker_for_ingest(monkeypatch)
    solver_mod.ingest(tmp_path, _ingest_manifest_fixture())
    # Simulate the failure mode: solver_gate.json lost (e.g., OSError
    # at write time augmented `gate_persistence_failed`, or user
    # accidentally `rm`ed it).
    (tmp_path / "artifacts" / "solver_gate.json").unlink()

    recovered = read_artifacts(tmp_path, _ingest_manifest_fixture())
    # MUST be ingested, NOT real — that's the whole fix.
    assert recovered["details"]["execution"] == "ingested", (
        "fallback must preserve ingested classification when gate JSON missing; "
        "silently upgrading to 'real' bypasses DEC-V61-201-SUB-INGEST honesty fences"
    )
    assert recovered["details"]["real_solver_invoked"] is False
    assert recovered["details"]["recovered_from_log_banner"] is True
    # Status is PASS — the canonical log's final residuals (1e-7) meet
    # the manifest target (1e-3). Pre-P2-FOLLOWUP this was a hard-coded
    # WARN, which silently demoted real evidence and blocked the
    # PASS+ingested → partial-validation path in assemble().
    assert recovered["status"] == "PASS"


def test_read_artifacts_recovers_ingested_fail_when_residuals_miss_targets(
    tmp_path: Path,
):
    """DEC-V61-201-SUB-INGEST-P2-FOLLOWUP: a non-converged ingested case
    whose `solver_gate.json` is lost must recover as status=FAIL via
    re-parsing the log + recomputing against manifest residual_targets.
    Pre-P2-FOLLOWUP this was hard-coded WARN — silently upgrading real
    FAIL evidence."""
    from cfdtrust.audit.solver import INGEST_BANNER, read_artifacts
    art = tmp_path / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    # Banner-prefixed log whose final residuals (1e-1) are well ABOVE
    # the manifest target (1e-3). No "converged" message either.
    (art / "solver.log").write_text(
        INGEST_BANNER
        + "Time = 1\n"
        + "smoothSolver:  Solving for Ux, Initial residual = 5.0e-1, Final residual = 1.0e-1, No Iterations 5\n"
        + "GAMG:  Solving for p, Initial residual = 5.0e-1, Final residual = 1.0e-1, No Iterations 12\n"
        + "Time = 2\n"
        + "smoothSolver:  Solving for Ux, Initial residual = 1.0e-1, Final residual = 5.0e-2, No Iterations 5\n"
        + "GAMG:  Solving for p, Initial residual = 1.0e-1, Final residual = 5.0e-2, No Iterations 6\n"
    )
    (art / "residuals.csv").write_text("iter,Ux,p\n1,5.0e-1,5.0e-1\n2,1.0e-1,1.0e-1\n")
    recovered = read_artifacts(tmp_path, _ingest_manifest_fixture())
    assert recovered["details"]["execution"] == "ingested"
    assert recovered["details"]["real_solver_invoked"] is False
    assert recovered["details"]["recovered_from_log_banner"] is True
    assert recovered["status"] == "FAIL", (
        "non-converged ingested run must recover as FAIL — silently "
        "upgrading to WARN demotes real failure evidence"
    )
    # Failed-field details propagate from _compute_gate_from_residuals.
    assert "failed_fields" in recovered["details"]


def test_read_artifacts_real_fallback_still_works_for_non_banner_logs(
    tmp_path: Path,
):
    """Regression guard: a real (non-mocked, non-banner) log still
    falls back to `execution="real"` per the legacy path. The R5-P1
    fix must NOT regress the existing fallback behaviour for true
    real runs whose solver_gate.json was lost."""
    from cfdtrust.audit.solver import read_artifacts
    art = tmp_path / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    # A real-shaped log with NO banner of any kind.
    (art / "solver.log").write_text(
        "Time = 1\n"
        "smoothSolver:  Solving for Ux, Initial residual = 1, Final residual = 0.1, No Iterations 5\n"
    )
    (art / "residuals.csv").write_text("iter,Ux\n1,1.0e-1\n")
    out = read_artifacts(tmp_path, _ingest_manifest_fixture())
    assert out["details"]["execution"] == "real"
    assert out["status"] == "PASS"


def test_ingest_banner_detection_avoids_false_positive_on_word_ingested(
    tmp_path: Path,
):
    """Codex R5-P1 defense-in-depth: the banner check matches the literal
    phrase 'ingested external solver log', NOT just the word 'ingested'.
    A user log that mentions 'this run was previously ingested' in some
    application diagnostic must NOT be misclassified."""
    from cfdtrust.audit.solver import read_artifacts
    art = tmp_path / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    (art / "solver.log").write_text(
        "Time = 1\n"
        "  Note: this case was previously ingested by another tool.\n"
        "smoothSolver:  Solving for Ux, Initial residual = 1, Final residual = 0.1, No Iterations 5\n"
    )
    (art / "residuals.csv").write_text("iter,Ux\n1,1.0e-1\n")
    out = read_artifacts(tmp_path, _ingest_manifest_fixture())
    # Should fall through to "real" because the banner phrase isn't present.
    assert out["details"]["execution"] == "real"


def test_assemble_honesty_fence_holds_via_log_banner_recovery(monkeypatch, tmp_path: Path):
    """Codex R5-P1 + P2-FOLLOWUP end-to-end: with solver_gate.json
    deleted post-ingest on a fully-converged case, the recomputed
    solver gate is PASS and `assemble()` then writes
    overall_status=WARN + validation_status=`partial`. Pre-P2-FOLLOWUP
    the hard-coded WARN solver gate forced `validation_status` to
    `not_validated`, blocking the partial-validation branch from
    firing after gate-JSON loss."""
    from cfdtrust.audit.solver import read_artifacts

    _make_ingestable_case(tmp_path)
    _patch_docker_for_ingest(monkeypatch)
    solver_mod.ingest(tmp_path, _ingest_manifest_fixture())
    # Wipe the gate JSON — the bug Codex R5-P1 surfaced.
    (tmp_path / "artifacts" / "solver_gate.json").unlink()

    # Now simulate cfdtrust report: read_artifacts + assemble.
    manifest = _ingest_manifest_fixture()
    solver_gate = read_artifacts(tmp_path, manifest)
    assert solver_gate["status"] == "PASS"
    gates = {
        "geometry_contract":     {"status": "PASS"},
        "mesh_contract":         {"status": "PASS"},
        "bc_contract":           {"status": "PASS"},
        "solver_execution":      solver_gate,
        "qoi_extraction":        {"status": "PASS"},
        "reference_comparison":  {
            "status": "PASS",
            "details": {"real_comparison_performed": True},
        },
    }
    rp = assemble(tmp_path, manifest, gates)
    report = json.loads(rp.read_text())
    # Honesty fences hold AND the partial-validation branch fires.
    assert report["solver_execution"] == "ingested"
    assert report["overall_status"] == "WARN"
    assert report["validation_status"] == "partial"


def test_explain_tldr_warn_non_ingested_empty_when_all_pass(tmp_path: Path):
    """Edge case: WARN overall with every gate PASS (e.g., from a
    limitations-driven demotion). The 'no per-gate blockers' branch
    must fire."""
    from cfdtrust.cli_explain import _render_tldr

    report = {
        "overall_status": "WARN",
        "solver_execution": "real",
        "validation_status": "unknown",
        "gates": {
            "geometry_contract":     {"status": "PASS"},
            "mesh_contract":         {"status": "PASS"},
            "bc_contract":           {"status": "PASS"},
            "solver_execution":      {"status": "PASS"},
            "qoi_extraction":        {"status": "PASS"},
            "reference_comparison":  {"status": "PASS"},
        },
    }
    tldr = _render_tldr(report, gate_severities={})
    assert "no per-gate blockers" in tldr


def test_ingest_blocked_when_no_solver_log(monkeypatch, tmp_path: Path):
    """Case ran (has time dir) but log file is missing."""
    _make_ingestable_case(tmp_path, with_log=False)
    _patch_docker_for_ingest(monkeypatch)
    gate = ofa.ingest(tmp_path, _ingest_manifest_fixture())
    assert gate["status"] == "BLOCKED"
    assert gate["details"]["reason"] == "no_solver_log_found"
    # Codex R1-P1: diagnostic split into solver-specific + fallback lists.
    # Manifest declares solver=simpleFoam, so `log_simpleFoam.txt` is in
    # the solver-specific bucket (deduped out of fallback).
    assert "log_simpleFoam.txt" in gate["details"]["searched_solver_specific"]
    # Fallback bucket still contains the other historical names.
    assert "log_pimpleFoam.txt" in gate["details"]["searched_fallback"]


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
    # And the transcribed solver.log content ends with the chosen log
    # (R5-P1: INGEST_BANNER is prepended for honesty-fence recovery).
    assert (tmp_path / "artifacts" / "solver.log").read_text().endswith(
        _CANONICAL_SIMPLEFOAM_LOG
    )


# ---------- Codex R1-P1: log selection derives from manifest.solver ----------


def test_ingest_log_search_prefers_manifest_solver_over_fallback(
    monkeypatch, tmp_path: Path,
):
    """Codex R1-P1: a pisoFoam case must find log_pisoFoam.txt even when
    a stale log_simpleFoam.txt sits alongside. The manifest's declared
    solver wins over fallback list ordering."""
    _make_ingestable_case(tmp_path, with_log=False)
    # Stale legacy log — must NOT be chosen.
    (tmp_path / "log_simpleFoam.txt").write_text("STALE LEGACY LOG\n")
    # The current run's log — must be chosen because manifest says pisoFoam.
    (tmp_path / "log_pisoFoam.txt").write_text(_CANONICAL_SIMPLEFOAM_LOG)
    _patch_docker_for_ingest(monkeypatch)

    m = _ingest_manifest_fixture()
    m["solver"] = "pisoFoam"
    gate = ofa.ingest(tmp_path, m)
    assert gate["details"]["external_log_source"] == "log_pisoFoam.txt"
    # R5-P1: INGEST_BANNER is prepended for honesty-fence recovery; the
    # original log content (from the manifest-derived candidate) follows.
    assert (tmp_path / "artifacts" / "solver.log").read_text().endswith(
        _CANONICAL_SIMPLEFOAM_LOG
    )


def test_ingest_finds_solver_specific_log_when_fallback_absent(
    monkeypatch, tmp_path: Path,
):
    """Codex R1-P1: even when no generic fallback log exists, a solver-
    specific log derived from manifest.solver must be discovered."""
    _make_ingestable_case(tmp_path, with_log=False)
    # ONLY a solver-specific log, with a solver name that isn't in the
    # historical fallback list at all.
    (tmp_path / "log_myCustomFoam.txt").write_text(_CANONICAL_SIMPLEFOAM_LOG)
    _patch_docker_for_ingest(monkeypatch)

    m = _ingest_manifest_fixture()
    m["solver"] = "myCustomFoam"
    gate = ofa.ingest(tmp_path, m)
    assert gate["status"] != "BLOCKED"
    assert gate["details"]["external_log_source"] == "log_myCustomFoam.txt"


def test_ingest_blocked_diagnostic_lists_both_candidate_sets(
    monkeypatch, tmp_path: Path,
):
    """Codex R1-P1: when no log is found, the BLOCKED diagnostic must
    enumerate the searched solver-specific AND fallback names so users
    know what conventions were tried."""
    _make_ingestable_case(tmp_path, with_log=False)
    _patch_docker_for_ingest(monkeypatch)
    m = _ingest_manifest_fixture()
    m["solver"] = "pisoFoam"
    gate = ofa.ingest(tmp_path, m)
    assert gate["status"] == "BLOCKED"
    assert gate["details"]["reason"] == "no_solver_log_found"
    # solver-derived names appear first; fallback list is also returned.
    assert "log_pisoFoam.txt" in gate["details"]["searched_solver_specific"]
    assert "log.pisoFoam" in gate["details"]["searched_solver_specific"]
    assert "pisoFoam.log" in gate["details"]["searched_solver_specific"]
    # The generic fallbacks are still listed so users see the full search.
    assert "log_simpleFoam.txt" in gate["details"]["searched_fallback"]


# ---------- Gap #10: log/ subdir fallback (case_011 dogfood) ----------


def test_ingest_finds_log_in_log_subdir_when_top_level_absent(
    monkeypatch, tmp_path: Path,
):
    """Gap #10 (case_011 plate-fin CHT): when `Allrun.sh` writes solver
    output to `case_dir/log/<solver>.log` and nothing sits at the top
    level, ingest must still locate the log via the bounded subdir
    fallback. Provenance must record the full relative path so users
    can audit where the log came from."""
    _make_ingestable_case(tmp_path, with_log=False)
    log_subdir = tmp_path / "log"
    log_subdir.mkdir()
    (log_subdir / "simpleFoam.log").write_text(_CANONICAL_SIMPLEFOAM_LOG)
    _patch_docker_for_ingest(monkeypatch)

    gate = ofa.ingest(tmp_path, _ingest_manifest_fixture())

    assert gate["status"] != "BLOCKED"
    assert gate["details"]["external_log_source"] == "log/simpleFoam.log"
    # provenance in ingest_manifest also points at the subdir location
    ingest_m = json.loads(
        (tmp_path / "artifacts" / "ingest_manifest.json").read_text()
    )
    assert (
        ingest_m["external_solver_log"]["source_relative"]
        == "log/simpleFoam.log"
    )


def test_ingest_top_level_log_wins_over_log_subdir(
    monkeypatch, tmp_path: Path,
):
    """Gap #10: top-level precedence must be preserved. When the case
    carries BOTH `case_dir/log_simpleFoam.txt` (top level) AND
    `case_dir/log/simpleFoam.log` (subdir), the top-level one wins so
    existing ingest behaviour is not perturbed."""
    _make_ingestable_case(tmp_path)  # writes log_simpleFoam.txt
    log_subdir = tmp_path / "log"
    log_subdir.mkdir()
    (log_subdir / "simpleFoam.log").write_text("SUBDIR LOG — MUST NOT WIN\n")
    _patch_docker_for_ingest(monkeypatch)

    gate = ofa.ingest(tmp_path, _ingest_manifest_fixture())

    assert gate["details"]["external_log_source"] == "log_simpleFoam.txt"


def test_ingest_accepts_large_case_above_run_paths_cap(monkeypatch, tmp_path: Path):
    """Codex R2-P1: a case whose entry count exceeds `_MAX_PATHS_WALKED`
    (the run() DoS bound, 10k) must NOT be rejected by ingest. Industrial
    cases with many saved time directories routinely break this cap.

    Test strategy: monkeypatch `_MAX_PATHS_WALKED_INGEST` to a tiny
    value and `_MAX_PATHS_WALKED` to an even tinier one, then build a
    case that exceeds the run() cap but is well within the ingest cap.
    We assert ingest succeeds (no `case_dir_not_openfoam_compatible`).
    """
    _make_ingestable_case(tmp_path)
    # Add many empty regular files (no symlinks) so the walker sees a
    # large entry count without spending real time on stat().
    deep = tmp_path / "100" / "many"
    deep.mkdir(parents=True, exist_ok=True)
    for i in range(50):
        (deep / f"f{i}").write_text("x")
    # Pretend the run() cap is 20 (so this case definitely overflows it)
    # and the ingest cap is 1000 (so the same case fits comfortably).
    monkeypatch.setattr(ofa, "_MAX_PATHS_WALKED", 20)
    monkeypatch.setattr(ofa, "_MAX_PATHS_WALKED_INGEST", 1000)
    _patch_docker_for_ingest(monkeypatch)

    gate = ofa.ingest(tmp_path, _ingest_manifest_fixture())
    # Must NOT be `case_dir_not_openfoam_compatible` due to the entry
    # count. Either PASS / FAIL on residuals is acceptable here — the
    # ingest-shape gate is what we're testing.
    assert gate["details"].get("reason") != "case_dir_not_openfoam_compatible"


def test_ingest_walker_fail_opens_on_cap_hit_when_no_escape_found(
    monkeypatch, tmp_path: Path,
):
    """Codex R2-P1: when the walker hits its budget without finding any
    escaping symlink, ingest must accept the case (not refuse). The cap
    is a walk budget for ingest, not a fail-closed bound like run()."""
    _make_ingestable_case(tmp_path)
    # Same setup as above but make the bound extremely small so the
    # walker hits it before exhausting the tree.
    monkeypatch.setattr(ofa, "_MAX_PATHS_WALKED_INGEST", 1)
    # No escaping symlinks added — walker will hit the cap with nothing
    # bad found. Direct unit test of the walker for clarity.
    found_escape, where = ofa._find_escaping_symlink_for_ingest(tmp_path)
    assert found_escape is False, (
        "ingest walker must fail-open on cap-hit (no escape found in budget)"
    )
    assert where == ""


def test_ingest_walker_still_catches_escape_within_budget(
    monkeypatch, tmp_path: Path,
):
    """Codex R2-P1 follow-up: even with a larger ingest cap, an actual
    escaping symlink (target outside case_dir) must still be caught."""
    _make_ingestable_case(tmp_path)
    # Create an external file and a symlink that escapes case_dir.
    outside = tmp_path.parent / "escape_target.txt"
    outside.write_text("BAD")
    (tmp_path / "evil_link").symlink_to(outside)

    found_escape, where = ofa._find_escaping_symlink_for_ingest(tmp_path)
    assert found_escape is True
    assert "escape" in where or "escapes" in where


def test_ingest_log_search_rejects_unsafe_solver_name(monkeypatch, tmp_path: Path):
    """Codex R1-P1 defense-in-depth: a manifest with `solver: '../etc/passwd'`
    must not coerce the search into a parent directory. Only the
    sanitised solver name (alphanumeric/underscore/dash) ever drives
    candidate-name construction; bad names degrade silently to fallbacks."""
    _make_ingestable_case(tmp_path)  # includes log_simpleFoam.txt
    _patch_docker_for_ingest(monkeypatch)
    m = _ingest_manifest_fixture()
    m["solver"] = "../etc/passwd"
    gate = ofa.ingest(tmp_path, m)
    # Fallback list still hits log_simpleFoam.txt — that's fine, the
    # test is that no '../' candidate was attempted.
    assert gate["details"]["external_log_source"] == "log_simpleFoam.txt"


def test_candidate_log_names_unit():
    """Direct unit test of the candidate-name builder so each branch is
    independently covered (solver present / solver missing / bad solver)."""
    primary, fallback = ofa._candidate_log_names({"solver": "pisoFoam"})
    assert primary == ["log_pisoFoam.txt", "log.pisoFoam", "pisoFoam.log"]
    assert "log_simpleFoam.txt" in fallback

    primary, fallback = ofa._candidate_log_names({})
    assert primary == []
    assert "log_simpleFoam.txt" in fallback

    primary, fallback = ofa._candidate_log_names({"solver": "simpleFoam"})
    # Dedup: simpleFoam-derived names that already appear in the fallback
    # list must not be duplicated.
    assert primary == ["log_simpleFoam.txt", "log.simpleFoam", "simpleFoam.log"]
    assert "log_simpleFoam.txt" not in fallback
    assert "log.simpleFoam" not in fallback
    assert "simpleFoam.log" not in fallback
    # Other fallback names still present.
    assert "log_pimpleFoam.txt" in fallback


# ---------- Codex R1-P2: cmd_ingest exit codes ----------


def test_cmd_ingest_exits_zero_on_fail_gate(monkeypatch, tmp_path: Path):
    """Codex R1-P2: a FAIL gate (e.g. residuals didn't meet target) must
    still exit 0 because ingest itself succeeded — evidence was imported.
    Scripted `ingest && report` flows depend on this."""
    from cfdtrust.cli_ingest import cmd_ingest
    from cfdtrust.audit import solver as solver_mod

    _make_ingestable_case(tmp_path)
    # Write the case_manifest.yaml so validate_manifest can load it.
    import yaml
    m = _ingest_manifest_fixture()
    # Tighten residual targets so the synthetic log's final residuals
    # (1.0e-7) fail against 1.0e-9.
    m["solver_contract"]["residual_targets"] = {"Ux": 1.0e-9, "p": 1.0e-9}
    (tmp_path / "case_manifest.yaml").write_text(yaml.safe_dump(m))
    (tmp_path / "artifacts").mkdir(exist_ok=True)
    _patch_docker_for_ingest(monkeypatch)

    rc = cmd_ingest(str(tmp_path))
    assert rc == 0, "FAIL gate must still exit 0 (ingest step succeeded)"
    # And the solver_gate.json was persisted so report can read it.
    assert (tmp_path / "artifacts" / "solver_gate.json").exists()


def test_cmd_ingest_exits_one_on_blocked(monkeypatch, tmp_path: Path):
    """Codex R1-P2: BLOCKED (env / case-shape problem) still exits 1 —
    nothing was imported, downstream report can't proceed."""
    from cfdtrust.cli_ingest import cmd_ingest
    _make_ingestable_case(tmp_path, with_time_dir=False)
    import yaml
    (tmp_path / "case_manifest.yaml").write_text(
        yaml.safe_dump(_ingest_manifest_fixture())
    )
    _patch_docker_for_ingest(monkeypatch)
    rc = cmd_ingest(str(tmp_path))
    assert rc == 1


def test_cmd_ingest_exits_zero_on_pass(monkeypatch, tmp_path: Path):
    """Codex R1-P2: PASS gate exits 0 (sanity)."""
    from cfdtrust.cli_ingest import cmd_ingest
    import yaml
    _make_ingestable_case(tmp_path)
    (tmp_path / "case_manifest.yaml").write_text(
        yaml.safe_dump(_ingest_manifest_fixture())
    )
    _patch_docker_for_ingest(monkeypatch)
    rc = cmd_ingest(str(tmp_path))
    assert rc == 0


# ---------- Codex R1-P3: cli_explain WARN branch ----------


def test_explain_tldr_warn_for_ingested_does_not_say_did_not_pass(tmp_path: Path):
    """Codex R1-P3: `cfdtrust explain` on an ingested WARN case (all
    gates PASS, overall demoted to WARN per honesty fence) must NOT
    surface the FAIL-flavoured 'did NOT pass its declared case contract'
    string. It must instead explain the witness-gap explicitly."""
    from cfdtrust.cli_explain import _render_tldr

    report = {
        "overall_status": "WARN",
        "solver_execution": "ingested",
        "validation_status": "partial",
        "gates": {
            "geometry_contract":     {"status": "PASS"},
            "mesh_contract":         {"status": "PASS"},
            "bc_contract":           {"status": "PASS"},
            "solver_execution":      {"status": "PASS"},
            "qoi_extraction":        {"status": "PASS"},
            "reference_comparison":  {"status": "PASS"},
        },
    }
    tldr = _render_tldr(report, gate_severities={})
    assert "did NOT pass" not in tldr
    assert "WARN" in tldr or "did not witness" in tldr or "ingested" in tldr.lower()


def test_explain_tldr_warn_non_ingested_uses_generic_warn_body(tmp_path: Path):
    """Codex R1-P3: WARN that's NOT from ingested demotion still gets
    its own branch — must not fall through to FAIL message."""
    from cfdtrust.cli_explain import _render_tldr

    report = {
        "overall_status": "WARN",
        "solver_execution": "real",
        "validation_status": "unknown",
        "gates": {
            "geometry_contract":     {"status": "PASS"},
            "mesh_contract":         {"status": "WARN"},
            "bc_contract":           {"status": "PASS"},
            "solver_execution":      {"status": "PASS"},
            "qoi_extraction":        {"status": "PASS"},
            "reference_comparison":  {"status": "PASS"},
        },
    }
    tldr = _render_tldr(report, gate_severities={"mesh_contract": "warning"})
    assert "did NOT pass" not in tldr


def test_explain_status_badge_handles_warn():
    """Codex R1-P3 follow-up: WARN must render as a recognized badge,
    not fall through to UNKNOWN."""
    from cfdtrust.cli_explain import _status_badge
    assert _status_badge("WARN") == "WARN"


# ---------- solver.ingest dispatcher ----------


def test_solver_ingest_refuses_mocked_backend(tmp_path: Path):
    m = _ingest_manifest_fixture()
    m["solver_backend"] = "mocked"
    gate = solver_mod.ingest(tmp_path, m)
    assert gate["status"] == "BLOCKED"
    assert gate["details"]["reason"] == "ingest_backend_unsupported"


def test_solver_ingest_refusal_does_not_persist_blocked_state(tmp_path: Path):
    """Codex R2-P2: refusing the backend must NOT write
    artifacts/solver_gate.json. Persisting a refusal would poison
    `cfdtrust report` forever — read_artifacts prefers the persisted
    gate, so a later `cfdtrust run` would still appear BLOCKED.
    """
    m = _ingest_manifest_fixture()
    m["solver_backend"] = "mocked"
    gate = solver_mod.ingest(tmp_path, m)
    assert gate["status"] == "BLOCKED"
    # No solver_gate.json should exist (file was never created).
    assert not (tmp_path / "artifacts" / "solver_gate.json").exists()


def test_solver_ingest_blocked_precondition_does_not_clobber_existing_gate(
    monkeypatch, tmp_path: Path,
):
    """Codex R6-P1: an ingest attempt that BLOCKs on a precondition
    (no_solver_log_found, case_decomposed_not_reconstructed,
    solver_log_unreadable, ...) must NOT overwrite a pre-existing
    `artifacts/solver_gate.json` from an earlier successful
    `cfdtrust run`. Pre-fix the BLOCKED ingest gate would be persisted
    and subsequent `cfdtrust report` would surface the stale BLOCKED
    verdict instead of the real harness-witnessed run.

    Tests the `no_solver_log_found` path (representative of all
    backend-emitted BLOCKED-with-reason returns)."""
    # Set up a case that has system/constant/0 + a successful prior
    # solver_gate.json from a "previous run".
    _make_ingestable_case(tmp_path, with_log=False, with_time_dir=True)
    art = tmp_path / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    prior_gate = {
        "status": "PASS",
        "summary": "harness-witnessed run converged",
        "details": {
            "execution": "real",
            "real_solver_invoked": True,
            "iterations": 5000,
        },
    }
    (art / "solver_gate.json").write_text(json.dumps(prior_gate))
    _patch_docker_for_ingest(monkeypatch)

    # Trigger the BLOCKED-precondition path: no solver log in case dir.
    blocked_gate = solver_mod.ingest(tmp_path, _ingest_manifest_fixture())
    assert blocked_gate["status"] == "BLOCKED"
    assert blocked_gate["details"]["reason"] == "no_solver_log_found"

    # CRITICAL: pre-existing solver_gate.json MUST be intact.
    persisted = json.loads((art / "solver_gate.json").read_text())
    assert persisted["status"] == "PASS"
    assert persisted["details"]["execution"] == "real"
    assert persisted["summary"] == "harness-witnessed run converged"


def test_solver_ingest_blocked_decomposed_does_not_clobber_existing_gate(
    monkeypatch, tmp_path: Path,
):
    """Same protection for the decomposed-only precondition path
    (R4-P2 + R6-P1 interaction). Post DEC-V61-201-SUB-INGEST-P2-
    DECOMPOSED-NOT-FINALIZED, the BLOCK only fires when reference is
    finalized — so the manifest must declare that to reach the gate."""
    _make_ingestable_case(tmp_path, with_time_dir=False)
    # Decomposed-only (triggers post-relaxation finalized-reference BLOCK).
    for i in range(2):
        (tmp_path / f"processor{i}" / "100").mkdir(parents=True)
    art = tmp_path / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    prior_gate = {
        "status": "PASS",
        "summary": "harness ran the case before decomposition",
        "details": {"execution": "real", "real_solver_invoked": True},
    }
    (art / "solver_gate.json").write_text(json.dumps(prior_gate))
    _patch_docker_for_ingest(monkeypatch)

    manifest = _ingest_manifest_fixture()
    manifest["reference_comparison"] = {"status": "finalized"}
    blocked_gate = solver_mod.ingest(tmp_path, manifest)
    assert blocked_gate["status"] == "BLOCKED"
    assert (
        blocked_gate["details"]["reason"]
        == "case_decomposed_not_reconstructed_with_finalized_reference"
    )
    # Existing gate intact.
    persisted = json.loads((art / "solver_gate.json").read_text())
    assert persisted["details"]["execution"] == "real"


def test_solver_ingest_success_still_persists_gate(monkeypatch, tmp_path: Path):
    """Regression guard for R6-P1: successful ingest (PASS / WARN /
    FAIL gate) must STILL be persisted to solver_gate.json. The fix
    must not over-correct and prevent legitimate persistence."""
    _make_ingestable_case(tmp_path)
    _patch_docker_for_ingest(monkeypatch)
    gate = solver_mod.ingest(tmp_path, _ingest_manifest_fixture())
    assert gate["status"] != "BLOCKED"
    # solver_gate.json was written.
    assert (tmp_path / "artifacts" / "solver_gate.json").exists()
    persisted = json.loads(
        (tmp_path / "artifacts" / "solver_gate.json").read_text()
    )
    assert persisted["details"]["execution"] == "ingested"


# ---------- DEC-V61-201-SUB-INGEST-P1-GUARD-DISCRIMINATE (R7-P1 follow-up) ----------


def test_solver_ingest_post_residual_blocked_persists_real_diagnostic(
    monkeypatch, tmp_path: Path,
):
    """DEC-V61-201-SUB-INGEST-P1-GUARD-DISCRIMINATE: a post-residual
    BLOCKED gate (e.g., `no_iterations_in_log` from a log that
    transcribed cleanly but contained zero parseable iterations) MUST
    persist to `artifacts/solver_gate.json`. These gates carry
    `details.execution == "ingested"` (set by `openfoam.ingest()` after
    `_compute_gate_from_residuals`) — they are REAL ingested-solver
    evidence outcomes, not precondition refusals.

    Pre-fix (R6-P1's status-only guard): such gates fell through the
    `if status == BLOCKED: return gate` short-circuit and were dropped.
    `cfdtrust report` then read the banner-fallback path in
    `read_artifacts()` and surfaced the generic ingested-WARN message
    instead of the actual `no_iterations_in_log` diagnostic — masking
    the real solver-side failure reason.
    """
    _make_ingestable_case(tmp_path, with_log=False)
    # Log file exists (so we pass the precondition check) but contains
    # zero parseable `Time = N` iterations → triggers the post-residual
    # `no_iterations_in_log` BLOCKED in `_compute_gate_from_residuals`.
    (tmp_path / "log_simpleFoam.txt").write_text(
        "Starting time loop\n"
        "Some preamble that has no Time = lines whatsoever.\n"
        "End of log (solver crashed before first iteration printout).\n"
    )
    _patch_docker_for_ingest(monkeypatch)

    blocked_gate = solver_mod.ingest(tmp_path, _ingest_manifest_fixture())
    assert blocked_gate["status"] == "BLOCKED"
    assert blocked_gate["details"]["reason"] == "no_iterations_in_log"
    # The discriminator that drives the new guard: post-residual outcomes
    # are stamped `execution="ingested"` by the backend wrapper.
    assert blocked_gate["details"]["execution"] == "ingested"

    # CRITICAL: this real diagnostic MUST be persisted to disk so
    # `cfdtrust report` surfaces `no_iterations_in_log` instead of the
    # generic ingested-WARN banner-fallback.
    gate_path = tmp_path / "artifacts" / "solver_gate.json"
    assert gate_path.exists(), (
        "post-residual BLOCKED (execution=ingested) must persist — "
        "dropping it forces report to fall back to the generic "
        "ingested-WARN banner and masks the real diagnostic"
    )
    persisted = json.loads(gate_path.read_text())
    assert persisted["status"] == "BLOCKED"
    assert persisted["details"]["reason"] == "no_iterations_in_log"
    assert persisted["details"]["execution"] == "ingested"


def test_solver_ingest_precondition_blocked_still_protected_by_discriminator(
    monkeypatch, tmp_path: Path,
):
    """DEC-V61-201-SUB-INGEST-P1-GUARD-DISCRIMINATE: the tighter guard
    must NOT regress the R6-P1 protection. Precondition refusals carry
    `details.execution == "skipped"` and still must NOT clobber an
    existing solver_gate.json from an earlier successful `cfdtrust run`.

    This is the symmetric inverse of the test above: same fixture shape
    as the original R6-P1 test (no_solver_log_found path), but explicitly
    asserts the prior-gate-intact invariant under the new discriminator
    logic."""
    _make_ingestable_case(tmp_path, with_log=False, with_time_dir=True)
    art = tmp_path / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    prior_gate = {
        "status": "PASS",
        "summary": "harness-witnessed run converged",
        "details": {
            "execution": "real",
            "real_solver_invoked": True,
            "iterations": 5000,
        },
    }
    (art / "solver_gate.json").write_text(json.dumps(prior_gate))
    _patch_docker_for_ingest(monkeypatch)

    blocked_gate = solver_mod.ingest(tmp_path, _ingest_manifest_fixture())
    assert blocked_gate["status"] == "BLOCKED"
    assert blocked_gate["details"]["reason"] == "no_solver_log_found"
    # The discriminator that drives the guard: precondition refusals are
    # stamped `execution="skipped"` by the backend.
    assert blocked_gate["details"]["execution"] == "skipped"

    # Existing solver_gate.json from prior `cfdtrust run` is INTACT.
    persisted = json.loads((art / "solver_gate.json").read_text())
    assert persisted["status"] == "PASS"
    assert persisted["details"]["execution"] == "real"
    assert persisted["summary"] == "harness-witnessed run converged"


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


def test_report_omits_ingest_manifest_for_real_run_even_if_stale_file_present(
    tmp_path: Path,
):
    """Codex R2-P2: stale `artifacts/ingest_manifest.json` on disk must
    NOT be advertised when the current report's solver_execution is
    `real`. Previously the artifacts index attached the file whenever
    it existed, regardless of the live verdict — that left downstream
    tooling with contradictory provenance for the same report.
    """
    (tmp_path / "artifacts").mkdir(parents=True, exist_ok=True)
    # Stale provenance from an earlier ingest.
    (tmp_path / "artifacts" / "ingest_manifest.json").write_text(
        json.dumps({"ingested_at": "2026-05-21T00:00:00Z"})
    )
    # Current report is a real harness-witnessed run.
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
    # Honesty: the live report is `real`, so no ingest provenance is
    # advertised even though the stale file is still on disk.
    assert "ingest_manifest" not in report["artifacts"]
    assert report["solver_execution"] == "real"


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


# ---------- Gap #13: divergence detection on no-time-dir BLOCKED ----------


_CANONICAL_DIVERGED_LOG = (
    "Time = 1\n"
    "smoothSolver:  Solving for Ux, Initial residual = 1.0, Final residual = 9.0, No Iterations 1000\n"
    "Time = 2\n"
    "smoothSolver:  Solving for Ux, Initial residual = 1e6, Final residual = 1e9, No Iterations 1000\n"
    "Time = 3\n"
    "smoothSolver:  Solving for Ux, Initial residual = -nan, Final residual = -nan, No Iterations 1000\n"
    "Time = 4\n"
    "[1] #0  Foam::error::printStack(Foam::Ostream&) at ??:?\n"
    "FOAM FATAL ERROR: Maximum number of iterations exceeded, divergence detected\n"
    "From function GAMG\n"
)


def test_ingest_no_time_dir_with_diverged_log_attaches_likely_divergence(
    monkeypatch, tmp_path: Path,
):
    """Gap #13 (case_004 NREL MRF dogfood): when the case has no time
    directory > 0 (so ingest BLOCKs) but the solver log carries
    divergence markers (FATAL / nan / printStack), the BLOCKED gate
    must attach `likely_divergence: True` + `divergence_evidence` so
    the user gets actionable diagnostic instead of the generic
    'never-ran' next_step."""
    _make_ingestable_case(tmp_path, with_time_dir=False, with_log=False)
    (tmp_path / "log_simpleFoam.txt").write_text(_CANONICAL_DIVERGED_LOG)
    _patch_docker_for_ingest(monkeypatch)

    gate = ofa.ingest(tmp_path, _ingest_manifest_fixture())

    assert gate["status"] == "BLOCKED"
    assert gate["details"]["reason"] == "no_time_directory_found"
    assert gate["details"].get("likely_divergence") is True
    evidence = gate["details"].get("divergence_evidence")
    assert evidence, "divergence_evidence missing"
    assert any(
        marker in evidence
        for marker in ("FATAL", "printStack", "-nan", "nan")
    ), f"unexpected divergence evidence: {evidence!r}"
    assert gate["details"].get("divergence_log_source") == "log_simpleFoam.txt"


def test_ingest_no_time_dir_with_clean_log_does_not_attach_divergence(
    monkeypatch, tmp_path: Path,
):
    """Gap #13: preserve existing 'never-ran' path. If a solver log is
    present but contains NO divergence markers, the BLOCKED gate must
    NOT add likely_divergence — that surface is reserved for the case
    where there's strong evidence the case crashed."""
    _make_ingestable_case(tmp_path, with_time_dir=False, with_log=True)
    # _CANONICAL_SIMPLEFOAM_LOG is clean (no FATAL/nan).
    _patch_docker_for_ingest(monkeypatch)

    gate = ofa.ingest(tmp_path, _ingest_manifest_fixture())

    assert gate["status"] == "BLOCKED"
    assert gate["details"]["reason"] == "no_time_directory_found"
    assert "likely_divergence" not in gate["details"]
    assert "divergence_evidence" not in gate["details"]


# ---------- Gap #14: versioned-suffix log discovery ----------


def test_ingest_finds_versioned_suffix_log_picks_newest_by_mtime(
    monkeypatch, tmp_path: Path,
):
    """Gap #14 (case_004 NREL MRF dogfood): industrial workflows save
    versioned suffix variants like `log.simpleFoam.v4`,
    `log.simpleFoam.v5` parallel to each other. After exact-name
    exhaustion, the loader must glob `log.<solver>*` and pick newest
    by mtime — older v4 must be ignored in favor of the v5 the user
    actually ran most recently."""
    import os as _os
    import time as _time
    _make_ingestable_case(tmp_path, with_log=False)
    older = tmp_path / "log.simpleFoam.v4"
    newer = tmp_path / "log.simpleFoam.v5"
    older.write_text(_CANONICAL_SIMPLEFOAM_LOG)
    newer.write_text(_CANONICAL_SIMPLEFOAM_LOG)
    now = _time.time()
    _os.utime(older, (now - 3600, now - 3600))
    _os.utime(newer, (now, now))
    _patch_docker_for_ingest(monkeypatch)

    gate = ofa.ingest(tmp_path, _ingest_manifest_fixture())

    assert gate["status"] != "BLOCKED", gate
    assert gate["details"]["external_log_source"] == "log.simpleFoam.v5", (
        f"expected newest-by-mtime .v5; got {gate['details'].get('external_log_source')!r}"
    )


def test_ingest_exact_log_name_still_wins_over_versioned_glob(
    monkeypatch, tmp_path: Path,
):
    """Gap #14: precedence — exact-name candidates (e.g. `log.simpleFoam`)
    must beat the glob fallback. A case that only carries the canonical
    `log.simpleFoam` (no versioned variants) must still pick it up."""
    _make_ingestable_case(tmp_path, with_log=False)
    (tmp_path / "log.simpleFoam").write_text(_CANONICAL_SIMPLEFOAM_LOG)
    _patch_docker_for_ingest(monkeypatch)

    gate = ofa.ingest(tmp_path, _ingest_manifest_fixture())

    assert gate["status"] != "BLOCKED", gate
    assert gate["details"]["external_log_source"] == "log.simpleFoam"
