"""DEC-V61-126 · checkMesh runner unit tests.

Coverage:
  * polymesh_missing → typed CheckMeshError before any Docker call
  * Docker SDK error paths (ImportError → docker_sdk_missing,
    NotFound → container_unavailable, status!="running" → container_not_running,
    DockerException → docker_sdk_error)
  * exec_run nonzero exit → checkmesh_exit_nonzero
  * Parser: canonical Mesh OK output
  * Parser: Failed N mesh checks output
  * Parser: severe non-orthogonal face count
  * Parser: missing metrics return None gracefully
  * Schemas backward compat (V122 callers see no checkmesh_* fields when
    not requested)
  * analyze_mesh_quality with run_checkmesh=True augments the report
  * analyze_mesh_quality graceful degradation when container unavailable
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ui.backend.services.mesh_quality.checkmesh_runner import (
    CheckMeshError,
    CheckMeshResult,
    _parse_checkmesh_output,
    _parse_faceset_body,
    run_checkmesh,
)


# Fixture: realistic checkMesh "Mesh OK" output captured from OpenFOAM 10.
_REAL_CHECKMESH_OK = """\
/*---------------------------------------------------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
\\*---------------------------------------------------------------------------*/

Create time

Create polyMesh for time = 0

Time = 0

Mesh stats
    points:           8
    internal points:  0
    faces:            48
    internal faces:   24
    cells:            8
    faces per cell:   6
    boundary patches: 2
    point zones:      0
    face zones:       0
    cell zones:       0

Overall number of cells of each type:
    hexahedra:     8
    prisms:        0
    wedges:        0
    pyramids:      0
    tet wedges:    0
    tetrahedra:    0
    polyhedra:     0

Checking topology...
    Boundary definition OK.
    Cell to face addressing OK.
    Point usage OK.
    Upper triangular ordering OK.
    Face vertices OK.
    Number of regions: 1 (OK).

Checking patch topology for multiply connected surfaces...
    Patch               Faces    Points   Surface topology
    walls               24       18       ok (non-closed singly connected)
    inlet               0        0        ok (empty)

Checking geometry...
    Overall domain bounding box (0 0 0) (1 1 1)
    Mesh has 3 geometric (non-empty/wedge) directions (1 1 1)
    Mesh has 3 solution (non-empty) directions (1 1 1)
    Boundary openness (1.7e-17 -8.3e-18 4.2e-18) OK.
    Max cell openness = 1.5e-16 OK.
    Max aspect ratio = 1.0 OK.
    Minimum face area = 0.25. Maximum face area = 0.25.  Face area magnitudes OK.
    Min volume = 0.125. Max volume = 0.125.  Total volume = 1. Cell volumes OK.
    Mesh non-orthogonality Max: 0 average: 0
    Non-orthogonality check OK.
    Face pyramids OK.
    Max skewness = 1.5e-16 OK.
    Coupled point location match (averaged) OK.

Mesh OK.

End
"""

_REAL_CHECKMESH_FAILED = """\
Checking geometry...
    Overall domain bounding box (0 0 0) (1 1 1)
    Mesh has 3 geometric (non-empty/wedge) directions (1 1 1)
    Boundary openness (1e-15) OK.
    Max cell openness = 2e-15 OK.
    Max aspect ratio = 850.5 OK.
    Min volume = 1e-12. Max volume = 0.5. Total volume = 1. Cell volumes OK.
    Mesh non-orthogonality Max: 78.4 average: 25.1
   *Number of severely non-orthogonal (> 70 degrees) faces: 18.
    Non-orthogonality check OK.
    Face pyramids OK.
    Max skewness = 4.2 ***Max skewness = 4.2 > 4 -- SKEWED CELLS DETECTED.
    Coupled point location match (averaged) OK.

Failed 1 mesh checks.

End
"""


# ────────── Parser tests ──────────


def test_parse_checkmesh_output_canonical_ok_format():
    """Canonical Mesh OK output → all numeric fields populated, mesh_ok=True."""
    result = _parse_checkmesh_output(_REAL_CHECKMESH_OK)
    assert isinstance(result, CheckMeshResult)
    assert result.mesh_ok is True
    assert result.max_non_orthogonality_deg == 0.0
    assert result.max_skewness is not None and result.max_skewness < 1e-10
    assert result.max_aspect_ratio == 1.0
    # No severe non-orthogonal line in OK output → None
    assert result.n_severe_non_ortho_faces is None
    assert result.failed_checks == []


def test_parse_checkmesh_output_failed_format():
    """Failed N mesh checks → mesh_ok=False, failures captured."""
    result = _parse_checkmesh_output(_REAL_CHECKMESH_FAILED)
    assert result.mesh_ok is False
    assert result.max_non_orthogonality_deg == 78.4
    assert result.max_skewness == 4.2
    assert result.max_aspect_ratio == 850.5
    assert result.n_severe_non_ortho_faces == 18
    # The "***" marker line for skewness should be captured.
    assert any("SKEWED" in check.upper() for check in result.failed_checks)


def test_parse_checkmesh_output_handles_missing_metrics_gracefully():
    """Partial output (e.g. checkMesh aborted early) → fields default to
    None / False; parser does NOT raise."""
    aborted = "Create time\n\nCreate polyMesh for time = 0\n\nMesh stats\n    points: 5\n"
    result = _parse_checkmesh_output(aborted)
    assert result.mesh_ok is False  # no Mesh OK line
    assert result.max_non_orthogonality_deg is None
    assert result.max_skewness is None
    assert result.max_aspect_ratio is None
    assert result.n_severe_non_ortho_faces is None
    assert result.failed_checks == []


def test_parse_checkmesh_output_raw_excerpt_captures_tail():
    """raw_log_excerpt captures the last ~50 lines for diagnosis."""
    result = _parse_checkmesh_output(_REAL_CHECKMESH_FAILED)
    assert "Failed 1 mesh checks" in result.raw_log_excerpt


# ────────── Docker SDK error paths ──────────


def test_run_checkmesh_polymesh_missing_raises_typed_error(tmp_path):
    """polymesh_missing failing_check fires BEFORE any Docker call —
    the synthetic case dir has no constant/polyMesh."""
    case_dir = tmp_path / "fresh_case"
    case_dir.mkdir()
    with pytest.raises(CheckMeshError) as exc_info:
        run_checkmesh(case_dir)
    assert exc_info.value.failing_check == "polymesh_missing"


def test_run_checkmesh_container_unavailable_raises_typed_error(
    tmp_path, monkeypatch
):
    """When docker.containers.get raises NotFound, surface as
    container_unavailable so analyze_mesh_quality can graceful-degrade."""
    case_dir = tmp_path / "lc_case"
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True)
    (polymesh / "points").write_text("dummy")  # any file makes is_dir True

    import docker.errors

    class _FakeClient:
        class containers:
            @staticmethod
            def get(name):
                raise docker.errors.NotFound("container not found")

    monkeypatch.setattr(
        "ui.backend.services.mesh_quality.checkmesh_runner.docker"
        if False
        else "docker.from_env",
        lambda: _FakeClient(),
    )
    with pytest.raises(CheckMeshError) as exc_info:
        run_checkmesh(case_dir)
    assert exc_info.value.failing_check == "container_unavailable"


def test_run_checkmesh_container_not_running_raises_typed_error(
    tmp_path, monkeypatch
):
    """When the container exists but status != 'running', surface as
    container_not_running."""
    case_dir = tmp_path / "lc_case"
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True)
    (polymesh / "points").write_text("dummy")

    class _FakeContainer:
        status = "exited"

    class _FakeClient:
        class containers:
            @staticmethod
            def get(name):
                return _FakeContainer()

    monkeypatch.setattr("docker.from_env", lambda: _FakeClient())
    with pytest.raises(CheckMeshError) as exc_info:
        run_checkmesh(case_dir)
    assert exc_info.value.failing_check == "container_not_running"


def test_run_checkmesh_docker_sdk_error_raises_typed_error(
    tmp_path, monkeypatch
):
    """Generic DockerException at client init surfaces as
    docker_sdk_error."""
    case_dir = tmp_path / "lc_case"
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True)
    (polymesh / "points").write_text("dummy")

    import docker.errors

    def _boom():
        raise docker.errors.DockerException("daemon socket unreachable")

    monkeypatch.setattr("docker.from_env", _boom)
    with pytest.raises(CheckMeshError) as exc_info:
        run_checkmesh(case_dir)
    assert exc_info.value.failing_check == "docker_sdk_error"


def test_run_checkmesh_exit_nonzero_raises_typed_error(tmp_path, monkeypatch):
    """When checkMesh exits nonzero (corrupt polyMesh in the container,
    missing required files), surface as checkmesh_exit_nonzero so the
    operator can diagnose."""
    case_dir = tmp_path / "lc_case"
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True)
    (polymesh / "points").write_text("dummy")

    class _FakeExecResult:
        exit_code = 1

        @property
        def output(self):
            return b"checkMesh: cannot read polyMesh/owner: No such file"

    class _FakeContainer:
        status = "running"

        def exec_run(self, **_):
            return _FakeExecResult()

        def put_archive(self, **_):
            return True

    class _FakeClient:
        class containers:
            @staticmethod
            def get(name):
                return _FakeContainer()

    monkeypatch.setattr("docker.from_env", lambda: _FakeClient())
    with pytest.raises(CheckMeshError) as exc_info:
        run_checkmesh(case_dir)
    assert exc_info.value.failing_check == "checkmesh_exit_nonzero"


def test_run_checkmesh_happy_path_parses_output(tmp_path, monkeypatch):
    """End-to-end happy: container running, exec_run returns canonical
    Mesh OK output → CheckMeshResult populated."""
    case_dir = tmp_path / "lc_case"
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True)
    (polymesh / "points").write_text("dummy")

    class _FakeExecResult:
        exit_code = 0

        @property
        def output(self):
            return _REAL_CHECKMESH_OK.encode("utf-8")

    class _FakeContainer:
        status = "running"

        def exec_run(self, **_):
            return _FakeExecResult()

        def put_archive(self, **_):
            return True

    class _FakeClient:
        class containers:
            @staticmethod
            def get(name):
                return _FakeContainer()

    monkeypatch.setattr("docker.from_env", lambda: _FakeClient())
    result = run_checkmesh(case_dir)
    assert result.mesh_ok is True
    assert result.max_aspect_ratio == 1.0


# ────────── Schema backward compat ──────────


def test_mesh_quality_report_schema_v122_backward_compat():
    """V126 R1 P2 backward-compat: V122 base MeshQualityReport must
    NOT carry checkmesh_* fields. The extended MeshQualityReportV126
    subclass adds them only when run_checkmesh=True. Legacy callers
    serializing the base shape never see null checkmesh_* keys."""
    from ui.backend.services.mesh_quality.schemas import MeshQualityReport

    report = MeshQualityReport(
        report_kind="v122",
        case_id="ldc",
        polymesh_present=True,
        cell_count=125,
        point_count=8,
        internal_face_count=200,
        boundary_face_count=100,
        bounding_box_min=(0.0, 0.0, 0.0),
        bounding_box_max=(1.0, 1.0, 1.0),
        bounding_box_volume=1.0,
        cells_per_unit_volume=125.0,
        patch_face_counts={},
        warnings=[],
    )
    dump = report.model_dump()
    # V122 contract: NO checkmesh_* keys appear in the serialized
    # payload — that is the whole point of the schema split.
    for key in dump:
        assert not key.startswith("checkmesh_"), (
            f"V122 base shape leaked checkmesh field {key!r}"
        )


def test_mesh_quality_report_v126_serializes_with_checkmesh_fields():
    """When checkmesh_* fields are populated on the V126 extension,
    they round-trip through Pydantic serialization."""
    from ui.backend.services.mesh_quality.schemas import MeshQualityReportV126

    report = MeshQualityReportV126(
        report_kind="v126",
        case_id="ldc",
        polymesh_present=True,
        cell_count=125,
        point_count=8,
        internal_face_count=200,
        boundary_face_count=100,
        bounding_box_min=(0.0, 0.0, 0.0),
        bounding_box_max=(1.0, 1.0, 1.0),
        bounding_box_volume=1.0,
        cells_per_unit_volume=125.0,
        patch_face_counts={},
        warnings=[],
        checkmesh_max_non_orthogonality_deg=32.5,
        checkmesh_max_skewness=0.7,
        checkmesh_max_aspect_ratio=4.5,
        checkmesh_mesh_ok=True,
        checkmesh_n_severe_non_ortho_faces=0,
        checkmesh_failed_checks=None,
    )
    dump = report.model_dump()
    assert dump["checkmesh_max_skewness"] == 0.7
    assert dump["checkmesh_mesh_ok"] is True


# ────────── analyze_mesh_quality integration ──────────


def _write_synthetic_polymesh(case_dir: Path, cells: int = 8) -> None:
    """Minimal valid polyMesh for the V122 analyzer (matches the
    test_mesh_quality.py fixture pattern but condensed)."""
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True, exist_ok=True)
    points = [
        (0.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (1.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
        (1.0, 0.0, 1.0),
        (0.0, 1.0, 1.0),
        (1.0, 1.0, 1.0),
    ]
    pts_body = "\n".join(f"({x} {y} {z})" for x, y, z in points)
    (polymesh / "points").write_text(
        f"FoamFile{{}}\n{len(points)}\n(\n{pts_body}\n)\n"
    )
    n_faces = cells * 6
    (polymesh / "owner").write_text(
        f"FoamFile{{}}\n{n_faces}\n(\n"
        + "\n".join(str(i % cells) for i in range(n_faces))
        + "\n)\n"
    )
    n_internal = cells * 3
    (polymesh / "neighbour").write_text(
        f"FoamFile{{}}\n{n_internal}\n(\n"
        + "\n".join(str(i % cells) for i in range(n_internal))
        + "\n)\n"
    )
    (polymesh / "boundary").write_text(
        "FoamFile{}\n2\n(\n"
        "    walls\n    {\n        type            patch;\n"
        f"        nFaces          {n_faces - n_internal};\n"
        f"        startFace       {n_internal};\n    }}\n"
        "    inlet\n    {\n        type            patch;\n"
        "        nFaces          0;\n        startFace       0;\n    }\n"
        ")\n"
    )


def test_analyze_mesh_quality_default_omits_checkmesh(tmp_path):
    """V126 R1 P2 backward compat: run_checkmesh=False (default)
    returns a V122-shape MeshQualityReport — NOT the V126 extension —
    so legacy callers never see the checkmesh_* fields at all."""
    from ui.backend.services.mesh_quality import analyze_mesh_quality
    from ui.backend.services.mesh_quality.schemas import (
        MeshQualityReport,
        MeshQualityReportV126,
    )

    case_dir = tmp_path / "ldc"
    _write_synthetic_polymesh(case_dir)
    report = analyze_mesh_quality(case_dir)  # default False
    assert isinstance(report, MeshQualityReport)
    assert not isinstance(report, MeshQualityReportV126)
    # The V122 model has no checkmesh_* attributes — accessing one
    # would AttributeError. Confirm via model_dump.
    dump = report.model_dump()
    assert not any(k.startswith("checkmesh_") for k in dump)


def test_analyze_mesh_quality_with_checkmesh_augments_report(
    tmp_path, monkeypatch
):
    """V126: run_checkmesh=True invokes the runner and lands fields on
    the report."""
    from ui.backend.services.mesh_quality import analyze_mesh_quality
    from ui.backend.services.mesh_quality.checkmesh_runner import (
        CheckMeshResult,
    )

    case_dir = tmp_path / "ldc"
    _write_synthetic_polymesh(case_dir)

    fake_result = CheckMeshResult(
        max_non_orthogonality_deg=12.5,
        max_skewness=0.3,
        max_aspect_ratio=2.1,
        mesh_ok=True,
        n_severe_non_ortho_faces=0,
        failed_checks=[],
        raw_log_excerpt="Mesh OK.",
    )
    monkeypatch.setattr(
        "ui.backend.services.mesh_quality.analyzer.run_checkmesh"
        if False
        else "ui.backend.services.mesh_quality.checkmesh_runner.run_checkmesh",
        lambda case_dir: fake_result,
    )
    report = analyze_mesh_quality(case_dir, run_checkmesh=True)
    assert report.checkmesh_max_skewness == 0.3
    assert report.checkmesh_mesh_ok is True
    # DEC-V61-138 (N2.4): clean mesh → empty suggestions list (a single
    # mesh_ok info entry would be noise).
    assert report.suggestions == []


def test_analyze_mesh_quality_populates_advisor_suggestions_on_failure(
    tmp_path, monkeypatch
):
    """DEC-V61-138 (N2.4): analyzer wires advisor.derive_suggestions
    into the V126 report when checkMesh metrics breach thresholds.
    Verifies the integration without re-testing rule-engine semantics
    (covered exhaustively in test_mesh_quality_advisor.py)."""
    from ui.backend.services.mesh_quality import analyze_mesh_quality
    from ui.backend.services.mesh_quality.checkmesh_runner import (
        CheckMeshResult,
    )

    case_dir = tmp_path / "ldc"
    _write_synthetic_polymesh(case_dir)

    fake_result = CheckMeshResult(
        max_non_orthogonality_deg=82.0,  # > critical 75°
        max_skewness=1.1,                # > reject 0.95
        max_aspect_ratio=2500.0,         # > defect 1000
        mesh_ok=False,
        n_severe_non_ortho_faces=12,
        failed_checks=["non-orthogonality exceeded"],
        raw_log_excerpt="Failed",
    )
    monkeypatch.setattr(
        "ui.backend.services.mesh_quality.checkmesh_runner.run_checkmesh",
        lambda case_dir: fake_result,
    )
    report = analyze_mesh_quality(case_dir, run_checkmesh=True)
    metrics = {s.metric for s in report.suggestions}
    assert "n_severe_non_ortho_faces" in metrics
    assert "max_non_orthogonality" in metrics
    assert "max_skewness" in metrics
    assert "max_aspect_ratio" in metrics


def test_analyze_mesh_quality_graceful_degradation_on_container_down(
    tmp_path, monkeypatch
):
    """V126: when container is unavailable, V122 fields populate as
    normal; checkmesh_* fields stay None; NO exception."""
    from ui.backend.services.mesh_quality import analyze_mesh_quality
    from ui.backend.services.mesh_quality.checkmesh_runner import (
        CheckMeshError,
    )

    case_dir = tmp_path / "ldc"
    _write_synthetic_polymesh(case_dir)

    def _container_down(case_dir):
        raise CheckMeshError(
            "container 'cfd-openfoam' not found",
            failing_check="container_unavailable",
        )

    monkeypatch.setattr(
        "ui.backend.services.mesh_quality.checkmesh_runner.run_checkmesh",
        _container_down,
    )
    # Must NOT raise; V122 fields populate.
    report = analyze_mesh_quality(case_dir, run_checkmesh=True)
    assert report.cell_count == 8  # V122 still works
    assert report.checkmesh_max_skewness is None  # graceful degradation


def test_analyze_mesh_quality_re_raises_on_genuine_checkmesh_failure(
    tmp_path, monkeypatch
):
    """V126: parse_error / checkmesh_exit_nonzero / docker_sdk_error
    are real bugs and MUST surface (not graceful-degrade)."""
    from ui.backend.services.mesh_quality import analyze_mesh_quality
    from ui.backend.services.mesh_quality.checkmesh_runner import (
        CheckMeshError,
    )

    case_dir = tmp_path / "ldc"
    _write_synthetic_polymesh(case_dir)

    def _fatal(case_dir):
        raise CheckMeshError(
            "checkMesh exit_code=1: corrupt polyMesh",
            failing_check="checkmesh_exit_nonzero",
        )

    monkeypatch.setattr(
        "ui.backend.services.mesh_quality.checkmesh_runner.run_checkmesh",
        _fatal,
    )
    with pytest.raises(CheckMeshError) as exc_info:
        analyze_mesh_quality(case_dir, run_checkmesh=True)
    assert exc_info.value.failing_check == "checkmesh_exit_nonzero"


# ────────── V129a · faceSet parser + per-patch aggregator ──────────


# Captured directly from `checkMesh -allGeometry -allTopology` on a
# deliberately skewed OpenFOAM 10 mesh (see V129a empirical sweep
# 2026-05-06). The header banner + FoamFile dict + separator + count
# + paren list + closer is the canonical shape we must parse.
_REAL_FACESET_BODY = """\
/*--------------------------------*- C++ -*----------------------------------*\\
  =========                 |
  \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox
\\*---------------------------------------------------------------------------*/
FoamFile
{
    format      ascii;
    class       faceSet;
    location    "constant/polyMesh/sets";
    object      nonOrthoFaces;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //


30
(
0
3
5
7
8
11
13
15
16
18
19
20
21
24
26
28
29
32
34
36
37
39
40
41
42
44
47
49
52
53
)

// ************************************************************************* //
"""


def test_parse_faceset_body_real_openfoam_10_output():
    """Canonical OpenFOAM-10 faceSet body parses to 30 face IDs."""
    ids = _parse_faceset_body(_REAL_FACESET_BODY)
    assert len(ids) == 30
    assert ids[0] == 0
    assert ids[-1] == 53
    assert 47 in ids


def test_parse_faceset_body_empty_input_returns_empty():
    """Absent set file (cat returned empty) yields empty tuple, not raise."""
    assert _parse_faceset_body("") == ()
    assert _parse_faceset_body("   \n\n") == ()


def test_parse_faceset_body_body_without_list_returns_empty():
    """Header-only file (no `(` opener) yields empty tuple."""
    text = "FoamFile { object nonOrthoFaces; }\n// separator\n"
    assert _parse_faceset_body(text) == ()


def test_aggregate_severe_faces_per_patch_maps_ids_to_patches():
    """Face IDs straddling patch [start, start+n) ranges map correctly."""
    from ui.backend.services.mesh_quality.analyzer import (
        aggregate_severe_faces_per_patch,
    )

    # 100 internal faces, then walls=[100..150), inlet=[150..160), outlet=[160..170).
    patch_ranges = {
        "walls": (100, 50),
        "inlet": (150, 10),
        "outlet": (160, 10),
    }
    severe_face_ids = (5, 105, 155, 165, 175)  # 5=internal (dropped), 175=out-of-range
    result = aggregate_severe_faces_per_patch(severe_face_ids, patch_ranges)
    assert result == {"walls": 1, "inlet": 1, "outlet": 1}


def test_aggregate_severe_faces_per_patch_empty_ids_returns_zero_for_each_patch():
    """Empty face-id list → zero count for every patch (NOT empty dict)."""
    from ui.backend.services.mesh_quality.analyzer import (
        aggregate_severe_faces_per_patch,
    )

    patch_ranges = {"walls": (100, 50), "inlet": (150, 10)}
    result = aggregate_severe_faces_per_patch((), patch_ranges)
    assert result == {"walls": 0, "inlet": 0}


def test_aggregate_severe_faces_per_patch_no_patches_returns_empty():
    """Empty patch_ranges → empty dict regardless of face-id input."""
    from ui.backend.services.mesh_quality.analyzer import (
        aggregate_severe_faces_per_patch,
    )

    assert aggregate_severe_faces_per_patch((1, 2, 3), {}) == {}


def test_run_checkmesh_bash_chain_preserves_checkmesh_exit_code(
    tmp_path, monkeypatch
):
    """V129a R1 P1 regression: when checkMesh itself exits non-zero
    (corrupt polyMesh, missing required files), the bash chain must
    propagate that exit code so `checkmesh_exit_nonzero` still fires.

    Failure mode the original V129a R0 bash had: the trailing
    `cat ... || true` set the chain's final exit status to 0,
    swallowing checkMesh's real failure exit and converting fatal
    runner failures into bogus parsed-success V126 responses.

    This test runs the actual bash_cmd string against a real
    /bin/bash with checkMesh stubbed by an `exit 1` script, so
    a regression in the rc=$?; ... exit $rc pattern would fail.
    """
    import shlex
    import subprocess

    case_dir = tmp_path / "lc_case"
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True)

    # Capture the bash_cmd as the production runner builds it. Probe
    # by mocking exec_run to record its `cmd` argument.
    captured: dict[str, list[str]] = {}

    class _FakeExecResult:
        exit_code = 1
        output = b""

    class _FakeContainer:
        status = "running"

        def exec_run(self, **kwargs):
            cmd = kwargs.get("cmd")
            if isinstance(cmd, list) and len(cmd) >= 3 and "checkMesh" in cmd[-1]:
                captured["bash_cmd"] = cmd
            return _FakeExecResult()

        def put_archive(self, **_):
            return True

    class _FakeClient:
        class containers:
            @staticmethod
            def get(name):
                return _FakeContainer()

    monkeypatch.setattr("docker.from_env", lambda: _FakeClient())
    with pytest.raises(CheckMeshError):
        run_checkmesh(case_dir)
    assert "bash_cmd" in captured, "production runner did not invoke checkMesh"
    bash_cmd_str = captured["bash_cmd"][-1]

    # Substitute a non-zero exiting stub for `checkMesh` and verify the
    # chain's final exit reflects that, NOT the trailing cat. Replace
    # `source /opt/openfoam10/etc/bashrc &&` with `:` (no-op) so we
    # don't depend on the container env.
    #
    # R2 P2 closure: the production bash uses
    #   cd {CONTAINER_WORK_BASE}/{case_id}_{uuid}
    # which is a CONTAINER path, NOT a host path. Rewrite the cd target
    # via a regex anchored on `cd /tmp/cfd-harness-cases-checkmesh/...`
    # so the substitution actually fires. The previous string-replace
    # on `polymesh.parent.parent` was a no-op (that path was never in
    # bash_cmd_str), so host bash early-exited from a missing-dir cd
    # BEFORE reaching the stubbed checkMesh — assertion passed for the
    # wrong reason and would not catch a regression that snapshotted
    # $? before checkMesh.
    import re as _re_test
    test_chain = bash_cmd_str.replace(
        "source /opt/openfoam10/etc/bashrc &&", ":; "
    ).replace(
        "checkMesh -allGeometry -allTopology",
        "false",  # stand-in checkMesh that exits 1
    )
    test_chain = _re_test.sub(
        r"cd /tmp/cfd-harness-cases-checkmesh/[^\s&]+",
        f"cd {shlex.quote(str(tmp_path))}",
        test_chain,
    )
    # Defensive: confirm the cd was actually rewritten — this would
    # have caught the R0 test bug.
    assert "cd /tmp/cfd-harness-cases-checkmesh/" not in test_chain, (
        f"regex failed to rewrite container cd path: {test_chain!r}"
    )

    proc = subprocess.run(
        ["bash", "-c", test_chain],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1, (
        f"bash chain swallowed checkMesh's exit 1 (got {proc.returncode}); "
        f"the rc=$?; ... exit $rc pattern is broken. "
        f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )

    # Sanity: the same chain with a SUCCESSFUL stub should exit 0.
    # This proves the test would catch a regression that hard-codes
    # exit 1 instead of preserving rc — without this twin-check, a
    # future "always exit 1" change would still pass the failure case.
    success_chain = test_chain.replace("false", "true")
    proc_ok = subprocess.run(
        ["bash", "-c", success_chain],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc_ok.returncode == 0, (
        f"bash chain failed even with successful stub (got "
        f"{proc_ok.returncode}); cd or echo+cat tail is broken. "
        f"stdout={proc_ok.stdout!r} stderr={proc_ok.stderr!r}"
    )
