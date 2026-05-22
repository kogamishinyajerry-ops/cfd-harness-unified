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


# ---------- Gap #17: versioned log_*/ subdir discovery (case_006 dogfood) ----------


def test_ingest_finds_log_in_versioned_log_subdir(monkeypatch, tmp_path: Path):
    """Gap #17 (case_006 ONERA M6 transonic dogfood): industrial Allrun
    layouts version their log directories
    (`log_v64_v2/04_solver.log`, `log_v64_v3/...`). The exact candidate
    names (`log_<solver>.txt`, `log.<solver>`, `<solver>.log`) must be
    searched inside any single-level `log_*/` subdir in addition to the
    `log/` subdir from Gap #10."""
    _make_ingestable_case(tmp_path, with_log=False)
    versioned = tmp_path / "log_v64_v2"
    versioned.mkdir()
    (versioned / "simpleFoam.log").write_text(_CANONICAL_SIMPLEFOAM_LOG)
    _patch_docker_for_ingest(monkeypatch)

    gate = ofa.ingest(tmp_path, _ingest_manifest_fixture())

    assert gate["status"] != "BLOCKED", gate
    assert gate["details"]["external_log_source"] == "log_v64_v2/simpleFoam.log"


def test_ingest_log_subdir_still_wins_over_versioned_log_subdir(
    monkeypatch, tmp_path: Path,
):
    """Gap #17: precedence — when BOTH `log/` (Gap #10) and `log_v64_*/`
    (Gap #17) carry solver logs, the plain `log/` directory wins to
    preserve Gap #10 behaviour."""
    _make_ingestable_case(tmp_path, with_log=False)
    plain = tmp_path / "log"
    plain.mkdir()
    (plain / "simpleFoam.log").write_text(_CANONICAL_SIMPLEFOAM_LOG)
    versioned = tmp_path / "log_v64_v2"
    versioned.mkdir()
    (versioned / "simpleFoam.log").write_text("VERSIONED — MUST NOT WIN\n")
    _patch_docker_for_ingest(monkeypatch)

    gate = ofa.ingest(tmp_path, _ingest_manifest_fixture())

    assert gate["details"]["external_log_source"] == "log/simpleFoam.log"


# ---------- Gap #20: diagonal solver in residual regex ----------


def test_parse_simplefoam_log_captures_diagonal_solver_residuals():
    """Gap #20 (case_006 ONERA M6 / rhoCentralFoam): density-based
    compressible solvers use the `diagonal:` solver for rho-related
    fields. The residual regex must capture these or compressible runs
    will report zero parseable residuals.
    """
    log = (
        "Time = 1\n"
        "diagonal:  Solving for rho, Initial residual = 0.5, Final residual = 0.0001, No Iterations 1\n"
        "diagonal:  Solving for rhoUx, Initial residual = 0.4, Final residual = 0.0001, No Iterations 1\n"
        "diagonal:  Solving for rhoE, Initial residual = 0.3, Final residual = 0.0001, No Iterations 1\n"
    )
    parsed = ofa._parse_simplefoam_log(log)

    assert len(parsed["iterations"]) == 1
    residuals = parsed["iterations"][0]["residuals"]
    assert residuals["rho"] == 0.5
    assert residuals["rhoUx"] == 0.4
    assert residuals["rhoE"] == 0.3


# ---------- Gap #21: counter for sub-second transient timestamps ----------


def test_parse_simplefoam_log_counts_iters_for_subsecond_timesteps():
    """Gap #21 (case_006 / case_007 transient dogfood): when the run is
    transient with sub-second timesteps (`Time = 1e-06`), the iter
    field must report the count of timesteps, NOT `int(timestamp) == 0`.
    Steady-state runs (Time = 1, 2, 3) preserve iter == int(Time)
    semantics (verified by existing
    test_parse_simplefoam_log_extracts_iterations_and_yplus).
    """
    lines = []
    for step in range(1, 6):
        lines.append(f"Time = {step}e-06")
        lines.append(
            "diagonal:  Solving for rho, Initial residual = 0.5, "
            "Final residual = 0.0001, No Iterations 1"
        )
    parsed = ofa._parse_simplefoam_log("\n".join(lines) + "\n")

    # 5 sub-second timesteps → final_iter must be 5 (not 0).
    assert parsed["final_iter"] == 5, (
        f"sub-second iters collapsed; got final_iter={parsed['final_iter']}"
    )
    assert len(parsed["iterations"]) == 5
    iters = [it["iter"] for it in parsed["iterations"]]
    assert iters == [1, 2, 3, 4, 5]


# ---------- Gap #22: gate.summary uses manifest solver name ----------


def test_gate_summary_uses_manifest_solver_name_not_hardcoded_simplefoam():
    """Gap #22 (case_006 / case_007 dogfood): when the manifest declares
    `solver: rhoCentralFoam` (or any non-simpleFoam solver), the gate
    summary string must use that name, not lie by saying
    "simpleFoam converged …"."""
    manifest = {
        "solver": "rhoCentralFoam",
        "solver_contract": {
            "residual_targets": {"rho": 1.0e-3},
            "max_iterations": 1000,
        },
    }
    log = (
        "Time = 1\n"
        "diagonal:  Solving for rho, Initial residual = 1e-4, "
        "Final residual = 1e-5, No Iterations 1\n"
    )
    parsed = ofa._parse_simplefoam_log(log)
    gate = ofa._compute_gate_from_residuals(parsed, manifest)

    assert gate["status"] == "PASS", gate
    assert "rhoCentralFoam" in gate["summary"], gate["summary"]
    assert "simpleFoam" not in gate["summary"], gate["summary"]


# ---------- Gap #25: VOF dotted-field names (alpha.water) ----------


def test_parse_simplefoam_log_captures_dotted_vof_fields():
    """Gap #25 (case_007 KCS ship VOF dogfood): VOF transport residuals
    use dotted phase-field names (`alpha.water`, `alpha.air`).
    The widened `[\\w.]+` capture group must extract them, otherwise
    every VOF case looks like "no residuals parsed"."""
    log = (
        "Time = 1\n"
        "MULES: Solving for alpha.water\n"
        "smoothSolver:  Solving for alpha.water, Initial residual = 0.5, "
        "Final residual = 0.001, No Iterations 3\n"
        "GAMG:  Solving for p_rgh, Initial residual = 0.3, "
        "Final residual = 0.0001, No Iterations 5\n"
    )
    parsed = ofa._parse_simplefoam_log(log)

    assert len(parsed["iterations"]) == 1
    residuals = parsed["iterations"][0]["residuals"]
    assert residuals["alpha.water"] == 0.5, (
        f"alpha.water missing from residuals; got {list(residuals.keys())}"
    )
    # p_rgh (underscored) must still parse via the same widened group.
    assert residuals["p_rgh"] == 0.3


# ---------- TBD-17 (case_009 Sandia Flame D reacting dogfood, honesty-adjacent) ----------


def test_tbd17_solver_gate_blocks_on_incomplete_residual_coverage():
    """TBD-17 (CRITICAL · honesty-adjacent): when a manifest declares N
    target fields but the parser only finds < N in residuals.csv (e.g.
    a 27-field reacting manifest whose log truncated mid-iteration after
    only the 3 momentum fields were emitted), `_compute_gate_from_residuals`
    must BLOCK with `incomplete_residual_coverage` — NOT silently PASS on
    the 3-of-27 subset.

    Pre-TBD-17, the gate's per-target loop used `if actual is None:
    continue` to silently drop manifest fields absent from the log,
    then declared PASS based on the present subset. For case_009
    reacting cases that was the closest the dogfood arc came to a real
    honesty break — the solver_gate said "PASS" with no flag that
    24/27 fields had been silently dropped, even though the top-level
    overall_status was correctly capped at WARN by the
    solver_execution=ingested fences.

    Disposition choice: BLOCKED-with-reason rather than FAIL — half
    evidence cannot be EVALUATED for convergence; "cannot evaluate" is
    the honest signal, distinct from "evaluated and failed."
    """
    # Synthetic short log: momentum + pressure only, no species (mirrors
    # the case_009 truncated-log scenario where the log cut off before
    # the species transport equations printed residuals).
    log = (
        "Time = 1\n"
        "smoothSolver:  Solving for Ux, Initial residual = 1e-06, Final residual = 1e-07, No Iterations 5\n"
        "smoothSolver:  Solving for Uy, Initial residual = 1e-06, Final residual = 1e-07, No Iterations 5\n"
        "smoothSolver:  Solving for Uz, Initial residual = 1e-06, Final residual = 1e-07, No Iterations 5\n"
    )
    # Manifest declares 8 fields total: 3 momentum + temperature + 4 species.
    # Log only has the 3 momentum fields → coverage = 3/8.
    manifest = {
        "solver": "reactingFoam",
        "solver_contract": {
            "max_iterations": 5000,
            "residual_targets": {
                "Ux": 1e-5,
                "Uy": 1e-5,
                "Uz": 1e-5,
                "T": 1e-5,
                "CH4": 1e-5,
                "O2": 1e-5,
                "CO2": 1e-5,
                "H2O": 1e-5,
            },
        },
    }
    parsed = ofa._parse_simplefoam_log(log)
    gate = ofa._compute_gate_from_residuals(parsed, manifest)

    # Honesty fences: BLOCKED, not PASS/FAIL.
    assert gate["status"] == "BLOCKED", (
        f"3/8 coverage must BLOCK, got {gate!r}"
    )
    assert gate["details"]["reason"] == "incomplete_residual_coverage"
    assert gate["details"]["incomplete_residual_coverage"] is True
    # The 5 missing target fields must be enumerated so users can see
    # exactly what was dropped vs. what was checked.
    assert set(gate["details"]["missing_target_fields"]) == {
        "T", "CH4", "O2", "CO2", "H2O",
    }, gate["details"]["missing_target_fields"]
    # The 3 present targets are recorded (not silently dropped).
    assert set(gate["details"]["checked_fields"]) == {"Ux", "Uy", "Uz"}
    # Solver name lifted from manifest (Gap #22 preserved).
    assert "reactingFoam" in gate["summary"]


# ---------- TBD-15 (case_009 multi-stage log filename fallback) ----------


def test_tbd15_find_external_solver_log_accepts_multi_stage_log_with_solver_in_head(
    tmp_path: Path,
):
    """TBD-15 (case_009 reacting dogfood): multi-stage reacting workflows
    commonly split runs into `log_cold.txt` (cold-flow init) and
    `log_ignite.txt` (ignition + burn). None of these match the canonical
    `log_<solver>.txt` / `log.<solver>` / `<solver>.log` candidates, so
    the pre-fix loop returned None and the user got
    `BLOCKED no_solver_log_found` on a perfectly valid ingest.

    Fix: after exact-name and versioned-suffix glob exhaustion, fall
    back to `log_*.txt` glob — but require the file head to reference
    the manifest's declared solver name (e.g. `Build: reactingFoam-...`
    in the OpenFOAM banner) so this fallback does not pick up unrelated
    stdout dumps that happen to live in the case dir.
    """
    # Build a minimal case dir with two multi-stage logs, neither
    # matching the canonical name list.
    (tmp_path / "system").mkdir()
    (tmp_path / "constant").mkdir()
    (tmp_path / "0").mkdir()
    # log_cold.txt — cold-flow stage, contains the OpenFOAM banner with
    # `Build  : reactingFoam-...` to identify the solver.
    cold_log_head = (
        "/*--------------------------------*- C++ -*----------------------------------*\\\n"
        "Build  : reactingFoam-11\n"
        "Exec   : reactingFoam\n"
        "Date   : ...\n"
        "Time = 0.001\n"
        "smoothSolver:  Solving for Ux, Initial residual = 1, Final residual = 0.5, No Iterations 3\n"
    )
    (tmp_path / "log_cold.txt").write_text(cold_log_head)

    manifest = {"solver": "reactingFoam"}
    found = ofa._find_external_solver_log(tmp_path, manifest)
    assert found is not None, (
        "TBD-15: multi-stage log_cold.txt with reactingFoam in head must "
        "be located via the general log_*.txt fallback"
    )
    assert found.name == "log_cold.txt"

    # Negative: a log_*.txt file that does NOT reference the manifest
    # solver must not be returned (false-positive guard).
    (tmp_path / "log_unrelated_stdout.txt").write_text(
        "This is not an OpenFOAM solver log at all, just some stdout.\n"
    )
    # Remove the legitimate one so the false-positive candidate would be
    # the only match if the head heuristic were missing.
    (tmp_path / "log_cold.txt").unlink()
    found_neg = ofa._find_external_solver_log(tmp_path, manifest)
    assert found_neg is None, (
        f"TBD-15 false-positive guard: log without solver name in head "
        f"must NOT be returned, got {found_neg!r}"
    )


# ---------- TBD-19 (case_009 chemkin parenthesized species names) ----------


def test_tbd19_residual_regex_captures_parenthesized_species():
    """TBD-19 (case_009 Sandia Flame D reacting dogfood, sibling to Gap #25):
    chemkin-style species names contain parentheses to disambiguate spin
    states — `CH2(S)` (singlet methylene) vs `CH2(T)` (triplet methylene),
    both present in GRI-Mech 3.0 reacting mechanisms. The Gap #25 widened
    `[\\w.]+` group stopped at the first `(`, capturing `CH2` and
    silently colliding with the real `CH2` species — two distinct
    chemical species sharing one residuals column.

    Fix: widen the capture group to `[\\w.()]+` so parenthesized species
    are captured intact and appear as a separate field from `CH2`.
    """
    log = (
        "Time = 0.001\n"
        "diagonal:  Solving for CH2, Initial residual = 0.4, "
        "Final residual = 0.04, No Iterations 1\n"
        "diagonal:  Solving for CH2(S), Initial residual = 0.5, "
        "Final residual = 0.05, No Iterations 1\n"
        "diagonal:  Solving for CH2(T), Initial residual = 0.6, "
        "Final residual = 0.06, No Iterations 1\n"
    )
    parsed = ofa._parse_simplefoam_log(log)

    assert len(parsed["iterations"]) == 1
    residuals = parsed["iterations"][0]["residuals"]
    # All three species captured intact, with distinct initial residuals
    # (no collision between CH2 and CH2(S) on the `CH2` key).
    assert residuals.get("CH2") == 0.4, (
        f"CH2 (no parens) must remain a distinct column; got "
        f"{list(residuals.keys())}"
    )
    assert residuals.get("CH2(S)") == 0.5, (
        f"CH2(S) parenthesized singlet must be captured intact; got "
        f"{list(residuals.keys())}"
    )
    assert residuals.get("CH2(T)") == 0.6, (
        f"CH2(T) parenthesized triplet must be captured intact; got "
        f"{list(residuals.keys())}"
    )


# ---------- DEC-V61-201-SUB-INGEST-MULTI-REGION-BC (Gap #11) ----------
#
# case_011 chtMultiRegionFoam dogfood surfaced: bc_audit parser was hard-coded
# to read 0/<field>, missing 0/region_<name>/<field> layouts. Backend now
# detects + iterates per region and emits a multi-region bc_quality.json;
# downstream audit emits structural BLOCKED until charter-class per-region
# bc_contract schema lands (Gap #28).


_CANONICAL_0_REGION_FLUID_U = (
    "FoamFile { class volVectorField; object U; }\n"
    "dimensions [0 1 -1 0 0 0 0];\n"
    "internalField uniform (0.5 0 0);\n"
    "boundaryField\n"
    "{\n"
    "    inlet { type fixedValue; value uniform (0.5 0 0); }\n"
    "    outlet { type zeroGradient; }\n"
    "    fluid_to_solid { type fixedValue; value uniform (0 0 0); }\n"
    "}\n"
)


_CANONICAL_0_REGION_FLUID_P = (
    "FoamFile { class volScalarField; object p; }\n"
    "dimensions [0 2 -2 0 0 0 0];\n"
    "internalField uniform 0;\n"
    "boundaryField\n"
    "{\n"
    "    inlet { type zeroGradient; }\n"
    "    outlet { type fixedValue; value uniform 0; }\n"
    "    fluid_to_solid { type zeroGradient; }\n"
    "}\n"
)


_CANONICAL_0_REGION_SOLID_T = (
    "FoamFile { class volScalarField; object T; }\n"
    "dimensions [0 0 0 1 0 0 0];\n"
    "internalField uniform 300;\n"
    "boundaryField\n"
    "{\n"
    "    solid_to_fluid { type fixedValue; value uniform 300; }\n"
    "    solid_outer_wall { type fixedValue; value uniform 350; }\n"
    "}\n"
)


def _make_multi_region_case(case_dir: Path) -> None:
    """Build a synthetic chtMultiRegionFoam case directory:
    fluid region (U, p) + solid region (T) under 0/region_<name>/.

    case_011 plate-fin HX is the production-grade case this layout
    represents. Top-level 0/<field> files are absent — that is the
    chtMultiRegion convention.
    """
    for sub in ("system", "constant", "0"):
        (case_dir / sub).mkdir(parents=True, exist_ok=True)
    (case_dir / "0" / "region_fluid").mkdir(parents=True, exist_ok=True)
    (case_dir / "0" / "region_solid").mkdir(parents=True, exist_ok=True)
    (case_dir / "0" / "region_fluid" / "U").write_text(
        _CANONICAL_0_REGION_FLUID_U,
    )
    (case_dir / "0" / "region_fluid" / "p").write_text(
        _CANONICAL_0_REGION_FLUID_P,
    )
    (case_dir / "0" / "region_solid" / "T").write_text(
        _CANONICAL_0_REGION_SOLID_T,
    )


def test_collect_bc_multi_region_emits_per_region_layout(tmp_path: Path):
    """Test A: case with 0/region_fluid/U + 0/region_solid/T produces
    bc_quality.json with `layout: "multi_region"` and per-region
    sub-dicts. Verifies the backend detection + per-region parsing
    pipeline end-to-end without invoking docker / ingest.
    """
    _make_multi_region_case(tmp_path)
    manifest = _ingest_manifest_fixture()
    # Drop the synthetic "__none_laminar__" turbulence field so the
    # expected_fields list is just ["U", "p"].
    manifest["bc_contract"]["turbulence_fields"] = []

    ofa._collect_and_persist_bc(tmp_path, manifest)

    bc_path = tmp_path / "artifacts" / "bc_quality.json"
    assert bc_path.exists()
    bc = json.loads(bc_path.read_text())

    # Multi-region marker present.
    assert bc["bc_parsing_status"] == "ok"
    assert bc["layout"] == "multi_region"
    assert bc["region_count"] == 2
    assert bc["regions_detected"] == ["region_fluid", "region_solid"]

    # Top-level single-region keys ABSENT (no `fields` at top level —
    # downstream must iterate `regions` instead). expected_fields is
    # still present as the canonical fluid-region expectation but is
    # marked at the top for advisory use.
    assert "fields" not in bc
    assert "fields_present" not in bc
    assert "fields_missing" not in bc
    assert bc["expected_fields"] == ["U", "p"]

    # Fluid region: U and p parsed, no missing fields.
    fluid = bc["regions"]["region_fluid"]
    assert fluid["fields_present"] == ["U", "p"]
    assert fluid["fields_missing"] == []
    assert fluid["fields"]["U"]["parsed"] is True
    assert fluid["fields"]["U"]["patches"]["inlet"]["type"] == "fixedValue"
    assert fluid["fields"]["U"]["patches"]["fluid_to_solid"]["type"] == "fixedValue"
    assert fluid["fields"]["p"]["parsed"] is True
    # File paths point inside the region sub-dir.
    assert fluid["fields"]["U"]["file"] == "0/region_fluid/U"

    # Solid region: T parsed; U and p legitimately missing for a solid
    # region (per-region expected_fields semantics is charter work,
    # Gap #28 — for now `fields_missing` carries advisory entries).
    solid = bc["regions"]["region_solid"]
    assert solid["fields_missing"] == ["U", "p"]
    # T was not in expected_fields (manifest bc_contract.turbulence_fields
    # is empty, canonical only adds U/p) — but the file IS on disk;
    # this advisory mismatch is exactly the gap charter work resolves.
    # The point of this test is: solid region is surfaced + iterated
    # without crash, fields_missing list is honest.
    assert "fields" in solid


def test_collect_bc_single_region_unchanged_shape(tmp_path: Path):
    """Test B: regression guard — single-region case (no 0/region_*/
    subdirs) produces bc_quality.json with the existing top-level
    `fields` shape, NO `layout` key, NO `regions` key. Byte-identical
    to pre-DEC behavior for the 99% single-region path.
    """
    # _make_ingestable_case produces a vanilla 0/U + 0/p layout.
    _make_ingestable_case(tmp_path, with_log=False, with_time_dir=False)
    manifest = _ingest_manifest_fixture()
    manifest["bc_contract"]["turbulence_fields"] = []

    ofa._collect_and_persist_bc(tmp_path, manifest)

    bc = json.loads((tmp_path / "artifacts" / "bc_quality.json").read_text())

    # Existing top-level shape.
    assert bc["bc_parsing_status"] == "ok"
    assert bc["expected_fields"] == ["U", "p"]
    assert bc["fields_present"] == ["U", "p"]
    assert bc["fields_missing"] == []
    assert "fields" in bc
    assert bc["fields"]["U"]["parsed"] is True

    # Multi-region keys ABSENT.
    assert "layout" not in bc, (
        "single-region cases must not gain a `layout` key — would "
        "trigger downstream multi-region BLOCKED path."
    )
    assert "regions" not in bc
    assert "regions_detected" not in bc
    assert "region_count" not in bc


def test_collect_bc_multi_region_empty_region_dir_graceful(tmp_path: Path):
    """Test C: edge case — `0/region_<name>/` directory present but
    EMPTY (no field files inside). The region is still listed in
    `regions` dict with all expected fields marked missing. No crash,
    bc_parsing_status remains `"ok"` so the downstream multi-region
    BLOCKED handler fires on the schema marker rather than on a
    parse error.
    """
    for sub in ("system", "constant", "0"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    (tmp_path / "0" / "region_fluid").mkdir(parents=True, exist_ok=True)
    (tmp_path / "0" / "region_empty").mkdir(parents=True, exist_ok=True)
    # Only fluid has files; region_empty is empty.
    (tmp_path / "0" / "region_fluid" / "U").write_text(
        _CANONICAL_0_REGION_FLUID_U,
    )

    manifest = _ingest_manifest_fixture()
    manifest["bc_contract"]["turbulence_fields"] = []

    ofa._collect_and_persist_bc(tmp_path, manifest)

    bc = json.loads((tmp_path / "artifacts" / "bc_quality.json").read_text())

    assert bc["bc_parsing_status"] == "ok"
    assert bc["layout"] == "multi_region"
    assert bc["region_count"] == 2
    assert bc["regions_detected"] == ["region_empty", "region_fluid"]

    # Empty region: both expected fields missing, no crash, fields
    # dict carries the synthetic "missing=True" entries (NOT absent).
    empty = bc["regions"]["region_empty"]
    assert empty["fields_present"] == []
    assert empty["fields_missing"] == ["U", "p"]
    assert empty["fields"]["U"]["parsed"] is False
    assert empty["fields"]["U"]["missing"] is True
    assert empty["fields"]["p"]["parsed"] is False
    assert empty["fields"]["p"]["missing"] is True

    # Fluid region: U parsed, p missing.
    fluid = bc["regions"]["region_fluid"]
    assert fluid["fields_present"] == ["U"]
    assert fluid["fields_missing"] == ["p"]
# ---------- M2.6 cycle 1 spike-class: case_010 LES dogfood Gap #29 + #31 ----------


def test_ingest_accepts_zero_orig_when_zero_absent(monkeypatch, tmp_path: Path):
    """Gap #29 (case_010 LES dogfood): when `0/` is absent but
    `0.orig/` is present (canonical OpenFOAM pre-init workflow — user
    copies `0.orig/` → `0/` before running solver), ingest's env check
    must accept the case. BCs are read from `0.orig/` instead.
    """
    # Build an ingestable case but with `0.orig/` instead of `0/`.
    for sub in ("system", "constant"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    (tmp_path / "constant" / "polyMesh").mkdir(parents=True, exist_ok=True)
    (tmp_path / "constant" / "polyMesh" / "boundary").write_text(
        _CANONICAL_POLYMESH_BOUNDARY,
    )
    (tmp_path / "0.orig").mkdir()  # canonical pre-init dir, no `0/`
    (tmp_path / "0.orig" / "U").write_text(_CANONICAL_0_U)
    (tmp_path / "0.orig" / "p").write_text(_CANONICAL_0_P)
    (tmp_path / "100").mkdir()
    (tmp_path / "100" / "U").write_text("(placeholder)\n")
    (tmp_path / "log_simpleFoam.txt").write_text(_CANONICAL_SIMPLEFOAM_LOG)
    _patch_docker_for_ingest(monkeypatch)

    # Env-check should accept this shape.
    ok, reason = ofa._is_openfoam_compatible_ingest_case_dir(tmp_path)
    assert ok, f"Gap #29: 0.orig/ must satisfy `0` slot for ingest; got reason={reason}"

    gate = ofa.ingest(tmp_path, _ingest_manifest_fixture())
    # Must NOT block on case_dir_not_openfoam_compatible.
    assert gate["details"].get("reason") != "case_dir_not_openfoam_compatible"
    # BC artifact written, reading from 0.orig/.
    bc = json.loads((tmp_path / "artifacts" / "bc_quality.json").read_text())
    assert "U" in bc["fields"]
    assert bc["fields"]["U"]["parsed"] is True, (
        "Gap #29: BC parser must fall back to 0.orig/ when 0/ absent"
    )
    assert bc["fields"]["U"]["file"].startswith("0.orig/"), (
        f"BC source file must point at 0.orig/U; got {bc['fields']['U']['file']}"
    )


def test_bc_expected_fields_rans_komega_includes_k_omega_nut(monkeypatch, tmp_path: Path):
    """Gap #31a: when manifest declares `physics.turbulence_model =
    k-omega-SST` AND does NOT explicitly set
    `bc_contract.turbulence_fields`, the BC layer must expect
    [U, p, k, omega, nut] (RANS canonical). Hardcoded expected_fields
    is replaced by model-driven derivation.
    """
    _make_ingestable_case(tmp_path)
    _patch_docker_for_ingest(monkeypatch)

    m = _ingest_manifest_fixture()
    m["physics"]["turbulence_model"] = "k-omega-SST"
    # Strip explicit turbulence_fields so derivation kicks in.
    m["bc_contract"].pop("turbulence_fields", None)

    ofa.ingest(tmp_path, m)
    bc = json.loads((tmp_path / "artifacts" / "bc_quality.json").read_text())
    expected = bc.get("expected_fields", [])
    assert "k" in expected, f"Gap #31a: RANS k-omega-SST must expect k; got {expected}"
    assert "omega" in expected, f"Gap #31a: must expect omega; got {expected}"
    assert "nut" in expected, f"Gap #31a: must expect nut; got {expected}"


def test_bc_expected_fields_les_wale_is_nut_only(monkeypatch, tmp_path: Path):
    """Gap #31b: when manifest declares `physics.turbulence_model =
    LES-WALE` (algebraic SGS), expected_fields must be [U, p, nut] only
    — k and omega are NOT solved (no transport eqns for LES algebraic
    SGS). Pre-fix, hardcoded expected_fields=[k, omega, nut] would
    flag every legitimate LES-WALE case as false-INCOMPLETE for
    missing k/omega.
    """
    _make_ingestable_case(tmp_path)
    _patch_docker_for_ingest(monkeypatch)

    m = _ingest_manifest_fixture()
    m["physics"]["turbulence_model"] = "LES-WALE"
    # Strip explicit turbulence_fields so derivation kicks in.
    m["bc_contract"].pop("turbulence_fields", None)

    ofa.ingest(tmp_path, m)
    bc = json.loads((tmp_path / "artifacts" / "bc_quality.json").read_text())
    expected = bc.get("expected_fields", [])
    assert "nut" in expected, f"Gap #31b: LES-WALE must expect nut; got {expected}"
    assert "k" not in expected, (
        f"Gap #31b: LES-WALE algebraic SGS solves NO k transport eqn; "
        f"k must NOT be in expected_fields; got {expected}"
    )
    assert "omega" not in expected, (
        f"Gap #31b: LES-WALE algebraic SGS solves NO omega transport eqn; "
        f"omega must NOT be in expected_fields; got {expected}"
    )


# ---------- TBD-15 · reacting/combustion solver log fallback names ----------


def test_log_fallback_includes_reacting_family(monkeypatch, tmp_path: Path):
    """TBD-15 (case_009 dogfood): a reacting case with no `manifest.solver`
    declaration must still find `log_reactingFoam.txt` via the generic
    fallback list. Pre-fix, the fallback tuple only listed incompressible
    solvers (simpleFoam / pimpleFoam / icoFoam / potentialFoam / foamRun)
    and false-BLOCKED reacting / combustion / VOF / compressible / CHT
    cases even when the log sat right there on disk."""
    _make_ingestable_case(tmp_path, with_log=False)
    # Drop a reactingFoam log on disk under its canonical filename.
    (tmp_path / "log_reactingFoam.txt").write_text(_CANONICAL_SIMPLEFOAM_LOG)
    _patch_docker_for_ingest(monkeypatch)

    # Manifest WITHOUT manifest["solver"] — exercise the fallback path
    # exclusively (per `_candidate_log_names`, manifest-derived primary
    # is empty when solver is absent).
    manifest = _ingest_manifest_fixture()
    del manifest["solver"]

    gate = ofa.ingest(tmp_path, manifest)
    # The fallback must locate log_reactingFoam.txt; the gate may be
    # any status OTHER than the specific "no log found" BLOCK.
    assert gate["details"].get("reason") != "no_solver_log_found", (
        f"TBD-15: fallback must locate reactingFoam log; got {gate}"
    )
    # And the chosen external log must be the reactingFoam one.
    assert gate["details"].get("external_log_source") == "log_reactingFoam.txt", (
        f"TBD-15: expected log_reactingFoam.txt; got {gate['details'].get('external_log_source')}"
    )


# ---------- TBD-20 · streaming log parser for multi-GiB logs ----------


def test_stream_parser_equivalence(tmp_path: Path):
    """TBD-20: the streaming parser `_parse_simplefoam_log_stream` must
    return a dict byte-identical to `_parse_simplefoam_log` for the same
    input. We build a synthetic multi-iteration log in memory, write it
    to a tmp file, parse both via text-mode and stream-mode, and assert
    dict equality. This is the load-bearing correctness invariant —
    case_009's 3.3 GiB reactingFoam log was unusable via text-mode (OOM
    at 13.0 GiB peak RSS); the stream variant only has value if it
    produces the identical structured output."""
    # Build a multi-iteration log with the canonical residual format,
    # mixed with y+ output and a SIMPLE convergence message. ~5 KiB —
    # enough variety to exercise every state-machine branch.
    lines = []
    for t in range(1, 51):
        lines.append(f"Time = {t}")
        lines.append(
            f"smoothSolver:  Solving for Ux, Initial residual = {1.0/t:.6e}, "
            f"Final residual = {1.0/(t*10):.6e}, No Iterations 5"
        )
        lines.append(
            f"GAMG:  Solving for p, Initial residual = {0.5/t:.6e}, "
            f"Final residual = {0.5/(t*10):.6e}, No Iterations 8"
        )
        if t == 25:
            lines.append("patch wall y+ : min = 0.5, max = 5.0, average = 2.3")
    lines.append("SIMPLE solution converged in 50 iterations")
    log_text = "\n".join(lines) + "\n"

    log_path = tmp_path / "log_streaming_equivalence.txt"
    log_path.write_text(log_text)

    via_text = ofa._parse_simplefoam_log(log_text)
    via_stream = ofa._parse_simplefoam_log_stream(log_path)

    assert via_text == via_stream, (
        f"TBD-20: stream parser output must equal text parser output. "
        f"text={via_text}\nstream={via_stream}"
    )
    # Spot-check the structural invariants too — guards against a
    # degenerate case where both paths return the same empty result.
    assert via_stream["final_iter"] == 50
    assert len(via_stream["iterations"]) == 50
    assert "wall" in via_stream["y_plus"]
    assert via_stream["converged"] is True


# ---------- Gap #26-#27: step-numbered mesh-pipeline log discovery ----------


def test_mesh_log_discovery_step_numbered_blockmesh(monkeypatch, tmp_path: Path):
    """Gap #26-#27: industrial Allrun scripts name mesh logs
    `01_blockMesh.log` (step-numbered). Discovery must find them; mesh
    ingest must reflect them in mesh_quality.json's `mesh_pipeline_logs`."""
    _make_ingestable_case(tmp_path)
    # Drop ONLY the step-numbered variant (no unprefixed blockMesh log).
    (tmp_path / "01_blockMesh.log").write_text("Create polyMesh for time = 0\n")
    _patch_docker_for_ingest(monkeypatch)

    # Direct helper assertion: step-numbered log is found and keyed by tool.
    found = ofa._find_mesh_pipeline_logs(tmp_path)
    assert "blockMesh" in found
    assert found["blockMesh"].name == "01_blockMesh.log"

    # Integration: ingest persists the discovery into mesh_quality.json.
    ofa.ingest(tmp_path, _ingest_manifest_fixture())
    mq = json.loads((tmp_path / "artifacts" / "mesh_quality.json").read_text())
    assert mq.get("mesh_pipeline_logs", {}).get("blockMesh") == "01_blockMesh.log"


def test_mesh_log_discovery_prefers_latest_step_number(monkeypatch, tmp_path: Path):
    """Gap #26-#27: when multiple step-numbered runs of the same tool
    coexist, the highest step number (= latest run = canonical evidence)
    must win."""
    _make_ingestable_case(tmp_path)
    (tmp_path / "01_snappyHexMesh.log").write_text(
        "FOAM FATAL ERROR: locationInMesh outside domain\n"
    )
    (tmp_path / "03_snappyHexMesh.log").write_text(
        "snappyHexMesh: Finished meshing in 42 s\n"
    )
    _patch_docker_for_ingest(monkeypatch)

    found = ofa._find_mesh_pipeline_logs(tmp_path)
    assert found["snappyHexMesh"].name == "03_snappyHexMesh.log", (
        "highest step number must win as canonical evidence"
    )

    # Integration: mesh_report reflects the picked (newer) log path.
    ofa.ingest(tmp_path, _ingest_manifest_fixture())
    mq = json.loads((tmp_path / "artifacts" / "mesh_quality.json").read_text())
    assert mq["mesh_pipeline_logs"]["snappyHexMesh"] == "03_snappyHexMesh.log"


def test_collect_bc_sentinel_turbulence_fields_filtered_out(tmp_path: Path):
    """Gap #32 (case_011 cycle-2 dogfood): __none_laminar__ sentinel in
    manifest.bc_contract.turbulence_fields must NOT propagate into
    bc_quality.json as a literal expected_field. The sentinel is a
    manifest-authoring convention to signal "no turbulence fields";
    the canonical way is now `turbulence_fields: []` or omit-the-key
    (Gap #31 derivation), but historical sentinel manifests are
    accepted + filtered."""
    _make_ingestable_case(tmp_path, with_log=False, with_time_dir=False)
    manifest = _ingest_manifest_fixture()
    manifest["bc_contract"]["turbulence_fields"] = ["__none_laminar__"]

    ofa._collect_and_persist_bc(tmp_path, manifest)
    bc = json.loads((tmp_path / "artifacts" / "bc_quality.json").read_text())

    assert "__none_laminar__" not in bc["expected_fields"], (
        f"sentinel must be filtered; got {bc['expected_fields']}"
    )
    # The valid fields still come through.
    assert bc["expected_fields"] == ["U", "p"]
    # And it doesn't ghost into fields_missing either.
    assert "__none_laminar__" not in bc.get("fields_missing", [])


# ---------- Codex CHANGES_REQUIRED R0 cycle 3 fixes (Gap #36 / #37) ----------


def test_collect_bc_multi_region_in_zero_orig(tmp_path: Path):
    """Codex P1-1 (Gap #36): when CHT case has 0.orig/region_*/ but
    no 0/ (canonical pre-Allrun shape ingest now accepts per Gap #29),
    multi-region detection MUST still light up. Pre-fix, the regions
    walker only inspected 0/ and silently fell through to the single-
    region path, writing a broken bc_quality.json."""
    for sub in ("system", "constant"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    (tmp_path / "0.orig").mkdir()
    (tmp_path / "0.orig" / "region_fluid").mkdir()
    (tmp_path / "0.orig" / "region_solid").mkdir()
    (tmp_path / "0.orig" / "region_fluid" / "U").write_text(
        _CANONICAL_0_REGION_FLUID_U,
    )
    (tmp_path / "0.orig" / "region_fluid" / "p").write_text(
        _CANONICAL_0_REGION_FLUID_P,
    )
    (tmp_path / "0.orig" / "region_solid" / "T").write_text(
        _CANONICAL_0_REGION_SOLID_T,
    )

    manifest = _ingest_manifest_fixture()
    manifest["bc_contract"]["turbulence_fields"] = []

    ofa._collect_and_persist_bc(tmp_path, manifest)
    bc = json.loads((tmp_path / "artifacts" / "bc_quality.json").read_text())

    assert bc["layout"] == "multi_region", (
        f"Gap #36: 0.orig/region_*/ must trigger multi_region; got {bc}"
    )
    assert bc["region_count"] == 2
    assert bc["regions_detected"] == ["region_fluid", "region_solid"]
    # Per-region file paths reflect 0.orig/ source, not 0/.
    fluid = bc["regions"]["region_fluid"]
    assert fluid["fields"]["U"]["file"] == "0.orig/region_fluid/U", (
        f"file path must point at on-disk source; got {fluid['fields']['U']['file']}"
    )


def test_external_log_step_numbered_in_versioned_subdir(monkeypatch, tmp_path: Path):
    """Codex P1-2 (Gap #37): case_006 ONERA M6 production layout writes
    log_v64_v3/02_rhoSimpleFoam.log etc. — step-numbered inside
    versioned log/ subdirs. Pre-fix, the log_* subdir walker only
    tried exact basenames and missed step-numbered variants, ending
    at no_solver_log_found despite the file being on disk."""
    _make_ingestable_case(tmp_path, with_log=False, with_time_dir=False)
    (tmp_path / "log_v64_v3").mkdir()
    (tmp_path / "log_v64_v3" / "01_blockMesh.log").write_text("ok\n")
    (tmp_path / "log_v64_v3" / "02_rhoSimpleFoam.log").write_text(
        _CANONICAL_SIMPLEFOAM_LOG,
    )
    _patch_docker_for_ingest(monkeypatch)

    m = _ingest_manifest_fixture()
    m["solver"] = "rhoSimpleFoam"

    found = ofa._find_external_solver_log(tmp_path, m)
    assert found is not None, (
        "Gap #37: step-numbered log in versioned subdir must be discovered"
    )
    assert found.name == "02_rhoSimpleFoam.log"
    assert "log_v64_v3" in str(found)


# ---------- DEC-V61-201-SUB-INGEST-COMPRESSIBLE-CONTRACT (Gap #18 + #19) ----------


def test_compressible_contract_optional_absent_no_break(tmp_path: Path):
    """Gap #18 schema discipline: incompressible cases (no compressible_contract
    key) must continue validating + ingest unchanged. Backwards-compat
    floor — every existing case_021/027/004/011 case lives here."""
    _make_ingestable_case(tmp_path, with_log=False, with_time_dir=False)
    manifest = _ingest_manifest_fixture()
    assert "compressible_contract" not in manifest
    # Should not raise.
    ofa._collect_and_persist_bc(tmp_path, manifest)
    bc = json.loads((tmp_path / "artifacts" / "bc_quality.json").read_text())
    # Expected fields unchanged from pre-DEC default.
    assert "T" not in bc["expected_fields"]
    assert "rho" not in bc["expected_fields"]


def test_compressible_contract_full_case006_shape(tmp_path: Path):
    """Gap #18: case_006 ONERA M6 shape — all 6 model declarations +
    freestream — round-trips through validate_manifest cleanly."""
    import yaml
    from cfdtrust.manifest import validate_manifest

    _make_ingestable_case(tmp_path, with_log=False, with_time_dir=False)
    manifest = _ingest_manifest_fixture()
    manifest["compressible_contract"] = {
        "thermophysical_model": "hePsiThermo",
        "mixture_model": "pureMixture",
        "transport_model": "sutherland",
        "thermo_model": "hConst",
        "equation_of_state": "perfectGas",
        "energy": "sensibleEnthalpy",
        "freestream": {
            "p_Pa": 93600.0,
            "T_K": 288.0,
            "U_ms": [285.193, 0.0, 15.245],
            "Mach": 0.8395,
            "Re_chord": 11.72e6,
        },
    }
    # Round-trip via the project's validate_manifest helper. If the
    # schema rejects the case_006 shape, this raises.
    (tmp_path / "case_manifest.yaml").write_text(yaml.safe_dump(manifest))
    validated = validate_manifest(tmp_path)
    assert validated["compressible_contract"]["thermophysical_model"] == "hePsiThermo"
    assert validated["compressible_contract"]["freestream"]["Mach"] == 0.8395


def test_thermal_fields_in_bc_contract_walked(tmp_path: Path):
    """Gap #19: bc_contract.thermal_fields lists T → engine walks 0/T
    same way it walks 0/U, 0/p, 0/k, etc. Pre-fix, T BCs were silently
    invisible to bc_audit even when 0/T file existed."""
    _make_ingestable_case(tmp_path, with_log=False, with_time_dir=False)
    # Add 0/T with a freestream + zeroGradient pattern.
    (tmp_path / "0" / "T").write_text(
        "FoamFile { class volScalarField; object T; }\n"
        "dimensions [0 0 0 1 0 0 0];\n"
        "internalField uniform 288;\n"
        "boundaryField\n"
        "{\n"
        "    farfield_inlet { type freestream; freestreamValue uniform 288; }\n"
        "    wing_surface_reference { type zeroGradient; }\n"
        "}\n"
    )

    manifest = _ingest_manifest_fixture()
    manifest["bc_contract"]["turbulence_fields"] = []
    manifest["bc_contract"]["thermal_fields"] = ["T"]

    ofa._collect_and_persist_bc(tmp_path, manifest)
    bc = json.loads((tmp_path / "artifacts" / "bc_quality.json").read_text())

    assert "T" in bc["expected_fields"], (
        f"Gap #19: thermal_fields must extend expected; got {bc['expected_fields']}"
    )
    assert "T" in bc["fields_present"], (
        f"Gap #19: 0/T file present must show in fields_present; got {bc['fields_present']}"
    )
    assert bc["fields"]["T"]["parsed"] is True
    # Patches parsed from 0/T (sanity).
    assert "farfield_inlet" in bc["fields"]["T"]["patches"]


def test_diagonal_solver_residuals_already_parsed():
    """Gap #20 regression guard: _RESIDUAL_LINE_RE already includes
    `diagonal` in its alternation; verify density-based conserved
    variables (rho, rhoUx, rhoE) are captured from a synthetic
    rhoCentralFoam log slice. If this test fails, someone removed
    `diagonal` from the regex and broke compressible support."""
    log = (
        "Time = 1\n"
        "diagonal:  Solving for rho, Initial residual = 0, Final residual = 0, No Iterations 1\n"
        "diagonal:  Solving for rhoUx, Initial residual = 1e-08, Final residual = 1e-12, No Iterations 1\n"
        "diagonal:  Solving for rhoE, Initial residual = 2e-09, Final residual = 2e-13, No Iterations 1\n"
        "smoothSolver:  Solving for Ux, Initial residual = 3.34e-11, Final residual = 1.2e-13, No Iterations 5\n"
        "smoothSolver:  Solving for e, Initial residual = 6.94e-13, Final residual = 1e-15, No Iterations 3\n"
    )
    parsed = ofa._parse_simplefoam_log(log)
    assert parsed["iterations"], "rhoCentralFoam log must produce ≥1 iteration"
    iter1 = parsed["iterations"][0]
    for field in ("rho", "rhoUx", "rhoE", "Ux", "e"):
        assert field in iter1["residuals"], (
            f"Gap #20: {field} must be parsed from rhoCentralFoam log; "
            f"got {list(iter1['residuals'].keys())}"
        )


def test_compressible_contract_accepts_heRhoThermo(tmp_path: Path):
    """Codex R0 P1-1: heRhoThermo is the canonical OpenFOAM thermophysical
    model for liquid/CHT compressible cases. Pre-fix the enum only had
    hRhoThermo, blocking any case mirroring real `thermoType { type
    heRhoThermo; }` from adopting the new compressible_contract."""
    import yaml
    from cfdtrust.manifest import validate_manifest

    _make_ingestable_case(tmp_path, with_log=False, with_time_dir=False)
    manifest = _ingest_manifest_fixture()
    manifest["compressible_contract"] = {
        "thermophysical_model": "heRhoThermo",
        "equation_of_state": "perfectGas",
    }
    (tmp_path / "case_manifest.yaml").write_text(yaml.safe_dump(manifest))
    validated = validate_manifest(tmp_path)
    assert validated["compressible_contract"]["thermophysical_model"] == "heRhoThermo"


def test_compressible_contract_accepts_janaf_bare(tmp_path: Path):
    """Codex R0 P1-2: reacting OpenFOAM cases declare `thermo janaf`
    (bare, no `Thermo` suffix) in `thermophysicalProperties`. Pre-fix
    the enum only had `janafThermo`, blocking chemFoam/reacting cases
    from adopting compressible_contract — exactly the solver family
    the schema $comment named."""
    import yaml
    from cfdtrust.manifest import validate_manifest

    _make_ingestable_case(tmp_path, with_log=False, with_time_dir=False)
    manifest = _ingest_manifest_fixture()
    manifest["compressible_contract"] = {
        "thermophysical_model": "hePsiThermo",
        "mixture_model": "reactingMixture",
        "thermo_model": "janaf",
        "equation_of_state": "perfectGas",
    }
    (tmp_path / "case_manifest.yaml").write_text(yaml.safe_dump(manifest))
    validated = validate_manifest(tmp_path)
    assert validated["compressible_contract"]["thermo_model"] == "janaf"


# ---------- DEC-V61-201-SUB-INGEST-LES-CONTRACT (Gap #28) ----------


def test_les_contract_optional_absent_no_break(tmp_path: Path):
    """Gap #28 schema discipline: incompressible RANS cases (no
    les_contract key) must continue validating + ingest unchanged.
    Backwards-compat floor for every existing case_021/027/004/011."""
    _make_ingestable_case(tmp_path, with_log=False, with_time_dir=False)
    manifest = _ingest_manifest_fixture()
    assert "les_contract" not in manifest
    ofa._collect_and_persist_bc(tmp_path, manifest)
    bc = json.loads((tmp_path / "artifacts" / "bc_quality.json").read_text())
    # Default RANS expected fields unchanged.
    assert "U" in bc["expected_fields"] and "p" in bc["expected_fields"]


def test_les_contract_full_case010_shape(tmp_path: Path):
    """Gap #28: case_010 DrivAer LES shape — full LES declaration —
    round-trips through validate_manifest cleanly."""
    import yaml
    from cfdtrust.manifest import validate_manifest

    _make_ingestable_case(tmp_path, with_log=False, with_time_dir=False)
    manifest = _ingest_manifest_fixture()
    manifest["physics"]["turbulence_model"] = "LES_WALE"
    manifest["les_contract"] = {
        "simulation_type": "LES",
        "les_model": "WALE",
        "delta": "cubeRootVol",
        "delta_coeff": 1.0,
        "sgs_wall_function": "nutUSpaldingWallFunction",
        "transported_fields": [],  # WALE algebraic SGS — no transport eqn
    }
    (tmp_path / "case_manifest.yaml").write_text(yaml.safe_dump(manifest))
    validated = validate_manifest(tmp_path)
    assert validated["les_contract"]["simulation_type"] == "LES"
    assert validated["les_contract"]["les_model"] == "WALE"
    assert validated["les_contract"]["delta"] == "cubeRootVol"


def test_les_contract_transported_fields_does_not_replace_expected(tmp_path: Path):
    """Codex R0 P1 regression: les_contract.transported_fields is
    INFORMATIONAL ONLY — it describes what the SGS model itself
    transports. It must NOT replace BC-layer expected_fields. WALE has
    transported_fields=[] (algebraic SGS) but the solver still writes
    0/nut as a derived field that the BC audit must check exists.
    Pre-fix shape made expected_fields = transported_fields, suppressing
    nut/nuSgs from the audit — a real weakening of LES coverage."""
    _make_ingestable_case(tmp_path, with_log=False, with_time_dir=False)
    manifest = _ingest_manifest_fixture()
    # No bc_contract.turbulence_fields → derivation path fires.
    manifest["bc_contract"].pop("turbulence_fields", None)
    # Physics says LES_WALE; les_contract.transported_fields=[] (algebraic).
    manifest["physics"]["turbulence_model"] = "LES_WALE"
    manifest["les_contract"] = {
        "simulation_type": "LES",
        "les_model": "WALE",
        "transported_fields": [],  # WALE: SGS itself transports nothing
    }
    ofa._collect_and_persist_bc(tmp_path, manifest)
    bc = json.loads((tmp_path / "artifacts" / "bc_quality.json").read_text())
    # Despite transported_fields=[], the BC layer must still expect nut
    # (Gap #31 derivation: LES_WALE → [nut]). expected_fields = U + p + nut.
    assert "nut" in bc["expected_fields"], (
        f"Codex R0 P1: transported_fields=[] must NOT suppress nut; "
        f"got {bc['expected_fields']}"
    )
    # Same expected_fields the heuristic would have produced WITHOUT
    # les_contract.transported_fields — proves transported_fields didn't
    # override.
    assert bc["expected_fields"] == ["U", "p", "nut"]


def test_les_contract_spalart_allmaras_derives_nuTilda(tmp_path: Path):
    """Codex R0 P2 regression: les_contract.les_model: SpalartAllmaras
    (and its DES/DDES/IDDES variants) must derive expected fields as
    [nuTilda, nut] — NOT the conservative RANS default [k, omega, nut].
    Pre-fix, an SA-based case fell through to the unknown-model branch,
    auditing as missing k/omega while the case actually solves nuTilda."""
    _make_ingestable_case(tmp_path, with_log=False, with_time_dir=False)
    manifest = _ingest_manifest_fixture()
    manifest["bc_contract"].pop("turbulence_fields", None)
    manifest["physics"]["turbulence_model"] = ""
    manifest["les_contract"] = {
        "simulation_type": "DES",
        "les_model": "SpalartAllmarasDES",
        # No transported_fields → derivation fires via les_model name.
    }
    ofa._collect_and_persist_bc(tmp_path, manifest)
    bc = json.loads((tmp_path / "artifacts" / "bc_quality.json").read_text())
    assert "nuTilda" in bc["expected_fields"], (
        f"Codex R0 P2: SpalartAllmarasDES must derive nuTilda; got "
        f"{bc['expected_fields']}"
    )
    assert "nut" in bc["expected_fields"]
    # The fall-through RANS default would have wrongly added these:
    assert "k" not in bc["expected_fields"]
    assert "omega" not in bc["expected_fields"]


def test_les_contract_simulation_type_required(tmp_path: Path):
    """Codex R0 P3 regression: when les_contract block is present,
    simulation_type is required. les_contract: {} or {les_model: WALE}
    without simulation_type must fail validate_manifest. Pre-fix,
    incomplete LES declarations were silently accepted."""
    import yaml
    import pytest
    from cfdtrust.manifest import validate_manifest, ManifestError

    _make_ingestable_case(tmp_path, with_log=False, with_time_dir=False)
    manifest = _ingest_manifest_fixture()
    # les_contract present but missing simulation_type — must fail.
    manifest["les_contract"] = {"les_model": "WALE"}
    (tmp_path / "case_manifest.yaml").write_text(yaml.safe_dump(manifest))
    with pytest.raises(ManifestError):
        validate_manifest(tmp_path)


def test_les_contract_keqn_les_model_derives_transport(tmp_path: Path):
    """Gap #28: when manifest carries les_contract.les_model but NEITHER
    bc_contract.turbulence_fields NOR les_contract.transported_fields,
    derive from les_model name via the Gap #31 LES one-eq branch:
    kEqn → [nut, nuSgs, k]. Saves authors writing the redundant
    `physics.turbulence_model: LES_kEqn` when les_model already says
    everything."""
    _make_ingestable_case(tmp_path, with_log=False, with_time_dir=False)
    manifest = _ingest_manifest_fixture()
    manifest["bc_contract"].pop("turbulence_fields", None)
    # physics carries no turbulence_model — only les_contract knows.
    manifest["physics"].pop("turbulence_model", None)
    manifest["physics"]["turbulence_model"] = ""  # explicitly empty
    manifest["les_contract"] = {
        "simulation_type": "LES",
        "les_model": "kEqn",
        # No transported_fields → engine derives from les_model name.
    }
    ofa._collect_and_persist_bc(tmp_path, manifest)
    bc = json.loads((tmp_path / "artifacts" / "bc_quality.json").read_text())
    # Gap #31 LES one-eq branch: [nut, nuSgs, k].
    assert "nut" in bc["expected_fields"], (
        f"Gap #28 + #31 LES one-eq: kEqn must derive nut; got "
        f"{bc['expected_fields']}"
    )
    assert "k" in bc["expected_fields"]
    assert "nuSgs" in bc["expected_fields"]


# ---------- DEC-V61-201-SUB-INGEST-VOF-CONTRACT (TBD-3) ----------


def test_vof_contract_optional_absent_no_break(tmp_path: Path):
    """TBD-3 schema discipline: single-phase cases (no vof_contract) must
    continue validating + ingest unchanged. Backwards-compat floor."""
    _make_ingestable_case(tmp_path, with_log=False, with_time_dir=False)
    manifest = _ingest_manifest_fixture()
    assert "vof_contract" not in manifest
    ofa._collect_and_persist_bc(tmp_path, manifest)
    bc = json.loads((tmp_path / "artifacts" / "bc_quality.json").read_text())
    # No alpha.* fields in expected_fields without vof_contract.
    assert not any(f.startswith("alpha.") for f in bc["expected_fields"])


def test_vof_contract_full_case007_shape(tmp_path: Path):
    """TBD-3: case_007 KCS ship VOF shape — interFoam water/air with
    surface tension, density+viscosity pair, MULES correctors —
    round-trips through validate_manifest cleanly."""
    import yaml
    from cfdtrust.manifest import validate_manifest

    _make_ingestable_case(tmp_path, with_log=False, with_time_dir=False)
    manifest = _ingest_manifest_fixture()
    manifest["vof_contract"] = {
        "phases": ["water", "air"],
        "interface_method": "VOF_MULES",
        "alpha_field_name": "alpha.water",
        "surface_tension_N_per_m": 0.072,
        "interface_compression_coeff": 1.0,
        "density_pair": {"water": 998.8, "air": 1.225},
        "viscosity_pair": {"water": 1.05e-06, "air": 1.5e-05},
        "mules_correctors": 2,
    }
    (tmp_path / "case_manifest.yaml").write_text(yaml.safe_dump(manifest))
    validated = validate_manifest(tmp_path)
    assert validated["vof_contract"]["phases"] == ["water", "air"]
    assert validated["vof_contract"]["alpha_field_name"] == "alpha.water"
    assert validated["vof_contract"]["surface_tension_N_per_m"] == 0.072


def test_phase_fields_in_bc_contract_walked(tmp_path: Path):
    """TBD-3 Gap #19-parallel: bc_contract.phase_fields = [alpha.water]
    + 0/alpha.water file present → bc_quality.fields_present includes
    alpha.water. Pre-fix, VOF alpha BCs were silently invisible like
    case_006 thermal T was."""
    _make_ingestable_case(tmp_path, with_log=False, with_time_dir=False)
    # Add 0/alpha.water with interFoam-style BCs.
    (tmp_path / "0" / "alpha.water").write_text(
        "FoamFile { class volScalarField; object alpha.water; }\n"
        "dimensions [0 0 0 0 0 0 0];\n"
        "internalField uniform 0;\n"
        "boundaryField\n"
        "{\n"
        "    water_inlet { type variableHeightFlowRate; lowerBound 0; "
        "upperBound 1; value uniform 0; }\n"
        "    atmosphere { type inletOutlet; inletValue uniform 0; "
        "value uniform 0; }\n"
        "}\n"
    )

    manifest = _ingest_manifest_fixture()
    manifest["bc_contract"]["turbulence_fields"] = []
    manifest["bc_contract"]["phase_fields"] = ["alpha.water"]

    ofa._collect_and_persist_bc(tmp_path, manifest)
    bc = json.loads((tmp_path / "artifacts" / "bc_quality.json").read_text())

    assert "alpha.water" in bc["expected_fields"], (
        f"TBD-3: phase_fields must extend expected; got {bc['expected_fields']}"
    )
    assert "alpha.water" in bc["fields_present"]
    assert bc["fields"]["alpha.water"]["parsed"] is True
    assert "water_inlet" in bc["fields"]["alpha.water"]["patches"]


def test_phase_fields_derived_from_vof_contract_alpha_field_name(tmp_path: Path):
    """TBD-3: when bc_contract.phase_fields is absent BUT vof_contract.
    alpha_field_name is set, derive phase_fields = [alpha_field_name].
    Saves authors writing both."""
    _make_ingestable_case(tmp_path, with_log=False, with_time_dir=False)
    manifest = _ingest_manifest_fixture()
    manifest["bc_contract"]["turbulence_fields"] = []
    # No phase_fields in bc_contract.
    manifest["bc_contract"].pop("phase_fields", None)
    # But vof_contract carries alpha_field_name.
    manifest["vof_contract"] = {
        "phases": ["water", "air"],
        "alpha_field_name": "alpha.water",
    }
    ofa._collect_and_persist_bc(tmp_path, manifest)
    bc = json.loads((tmp_path / "artifacts" / "bc_quality.json").read_text())

    assert "alpha.water" in bc["expected_fields"], (
        f"TBD-3 derivation: alpha_field_name must auto-populate phase_fields; "
        f"got {bc['expected_fields']}"
    )


def test_alpha_dotted_residual_already_parsed():
    """Gap #25 regression guard (TBD-3 follow-up): the residual regex
    `[\\w.()]+` group correctly captures dotted phase-field names like
    `alpha.water`. Pre-Gap-#25, the regex used `\\w+` which stopped at
    the `.`, dropping every VOF residual line. The case_007 manifest
    comment claims this still happens (stale — was fixed in cycle 1)."""
    log = (
        "Time = 1\n"
        "smoothSolver:  Solving for alpha.water, Initial residual = 1.249e-10, "
        "Final residual = 5e-12, No Iterations 1\n"
        "DICPCG:  Solving for p_rgh, Initial residual = 9.4e-08, "
        "Final residual = 1e-10, No Iterations 5\n"
        "smoothSolver:  Solving for Ux, Initial residual = 3.8e-08, "
        "Final residual = 1e-10, No Iterations 3\n"
    )
    parsed = ofa._parse_simplefoam_log(log)
    assert parsed["iterations"], "interFoam log must produce >=1 iteration"
    res = parsed["iterations"][0]["residuals"]
    assert "alpha.water" in res, (
        f"Gap #25 regression: alpha.water must parse; got {list(res.keys())}"
    )
    assert "p_rgh" in res
    assert "Ux" in res
