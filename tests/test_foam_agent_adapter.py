"""tests/test_foam_agent_adapter.py — MockExecutor 和 FoamAgentExecutor 测试"""

import io
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Dict, Optional
import pytest
from unittest.mock import patch, MagicMock
from src.foam_agent_adapter import (
    FoamAgentExecutor,
    MockExecutor,
    ParameterPlumbingError,
    _emit_gold_anchored_points_sampledict,
    _load_gold_reference_values,
    _load_whitelist_parameter,
    _load_whitelist_turbulence_model,
    _parse_dict_scalar,
    _parse_g_magnitude,
    _parse_openfoam_raw_points_output,
    _try_load_sampledict_output,
)
from src.models import (
    CFDExecutor, Compressibility, FlowType, GeometryType,
    SteadyState, TaskSpec,
)


def make_task(flow_type: FlowType = FlowType.INTERNAL) -> TaskSpec:
    return TaskSpec(
        name="test",
        geometry_type=GeometryType.SIMPLE_GRID,
        flow_type=flow_type,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
        Re=100,
    )


def make_airfoil_task() -> TaskSpec:
    return TaskSpec(
        name="NACA 0012 Airfoil External Flow",
        geometry_type=GeometryType.AIRFOIL,
        flow_type=FlowType.EXTERNAL,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
        Re=3000000,
        boundary_conditions={"angle_of_attack": 0.0, "chord_length": 1.0},
    )


def test_foam_agent_adapter_compiles_with_deprecation_warnings_as_errors():
    repo_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [
            sys.executable,
            "-Werror::DeprecationWarning",
            "-m",
            "py_compile",
            str(repo_root / "src" / "foam_agent_adapter.py"),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


class TestMockExecutor:
    def test_implements_protocol(self):
        assert isinstance(MockExecutor(), CFDExecutor)

    def test_internal_flow(self):
        result = MockExecutor().execute(make_task(FlowType.INTERNAL))
        assert result.success
        assert result.is_mock
        assert "u_centerline" in result.key_quantities
        assert result.execution_time_s > 0

    def test_external_flow(self):
        result = MockExecutor().execute(make_task(FlowType.EXTERNAL))
        assert result.success
        assert "strouhal_number" in result.key_quantities

    def test_natural_convection(self):
        result = MockExecutor().execute(make_task(FlowType.NATURAL_CONVECTION))
        assert result.success
        assert "nusselt_number" in result.key_quantities

    def test_residuals_present(self):
        result = MockExecutor().execute(make_task())
        assert isinstance(result.residuals, dict)
        assert len(result.residuals) > 0

    def test_raw_output_path_is_none(self):
        result = MockExecutor().execute(make_task())
        assert result.raw_output_path is None

    def test_independent_results(self):
        ex = MockExecutor()
        r1 = ex.execute(make_task(FlowType.INTERNAL))
        r2 = ex.execute(make_task(FlowType.INTERNAL))
        r1.key_quantities["u_centerline"] = None
        # r2 不受影响（dict 是独立副本）
        assert r2.key_quantities["u_centerline"] is not None


class TestFoamAgentExecutor:
    def test_docker_unavailable_returns_failed_result(self):
        """Docker 不可用时返回 success=False 的 ExecutionResult，不 crash。"""
        class FakeDockerException(Exception):
            pass

        mock_docker = MagicMock()
        mock_docker.from_env.side_effect = FakeDockerException("Docker not available")
        mock_docker.errors.DockerException = FakeDockerException

        with patch.dict("sys.modules", {"docker": mock_docker, "docker.errors": mock_docker.errors}):
            # 需要重新导入来触发 module-level 检查
            import importlib
            import src.foam_agent_adapter as faa
            # 强制 _DOCKER_AVAILABLE = True（因为 docker 在 sys.modules）
            import sys
            sys.modules["docker"] = mock_docker
            sys.modules["docker.errors"] = mock_docker.errors
            # 在 docker 可用但 from_env() 抛异常的场景下
            # execute() 会通过 _DOCKER_AVAILABLE 检查，但 docker.from_env() 抛异常
            mock_docker.from_env.side_effect = FakeDockerException()
            faa._DOCKER_AVAILABLE = True
            faa.docker = mock_docker
            mock_docker.errors.DockerException = FakeDockerException

            executor = FoamAgentExecutor()
            result = executor.execute(make_task())
            assert result.success is False
            assert result.is_mock is False
            assert result.error_message is not None

    def test_container_not_running_returns_failed_result(self):
        """容器未运行时返回 success=False。"""
        class FakeDockerException(Exception):
            pass

        mock_docker = MagicMock()
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.status = "exited"
        mock_client.containers.get.return_value = mock_container
        mock_docker.from_env.return_value = mock_client
        mock_docker.errors.DockerException = FakeDockerException

        import sys
        sys.modules["docker"] = mock_docker
        sys.modules["docker.errors"] = mock_docker.errors

        import src.foam_agent_adapter as faa
        faa._DOCKER_AVAILABLE = True
        faa.docker = mock_docker
        mock_docker.errors.DockerException = FakeDockerException

        executor = FoamAgentExecutor()
        result = executor.execute(make_task())
        assert result.success is False
        assert result.is_mock is False

    def test_not_protocol_instance(self):
        # FoamAgentExecutor 有 execute 方法，所以也满足 Protocol
        assert isinstance(FoamAgentExecutor(), CFDExecutor)

    # ------------------------------------------------------------------
    # L-PR20-2: narrow coverage for the four execute() error branches
    # per DEC-V61-020 / PR #20 Codex round-6 follow-up
    # ------------------------------------------------------------------

    def test_execute_sdk_not_installed_returns_install_hint(self, monkeypatch):
        """_DOCKER_AVAILABLE=False branch: error hint must name the optional
        dep group (cfd-real-solver) and quote the version specifier so the
        command works in zsh/bash (L-PR20-1 fix regression guard)."""
        monkeypatch.setattr("src.foam_agent_adapter._DOCKER_AVAILABLE", False)
        executor = FoamAgentExecutor()
        result = executor.execute(make_task())
        assert result.success is False
        assert result.is_mock is False
        assert "Docker Python SDK not installed" in result.error_message
        assert "cfd-real-solver" in result.error_message
        # L-PR20-1: version specifier must be single-quoted so shells parse it.
        assert "'docker>=7.0'" in result.error_message

    def test_execute_real_not_found_dispatches_to_start_container_hint(
        self, monkeypatch
    ):
        """When docker.errors.NotFound IS a real class subclass of
        DockerException, the dispatcher must emit the 'not found → docker
        start' hint (not the generic unavailable message)."""
        class FakeDockerException(Exception):
            pass
        class FakeNotFound(FakeDockerException):
            pass

        mock_docker = MagicMock()
        mock_docker.errors.DockerException = FakeDockerException
        mock_docker.errors.NotFound = FakeNotFound
        mock_docker.from_env.side_effect = FakeNotFound(
            "No such container: cfd-openfoam"
        )

        import sys as _sys
        monkeypatch.setitem(_sys.modules, "docker", mock_docker)
        monkeypatch.setitem(_sys.modules, "docker.errors", mock_docker.errors)
        monkeypatch.setattr("src.foam_agent_adapter._DOCKER_AVAILABLE", True)
        monkeypatch.setattr("src.foam_agent_adapter.docker", mock_docker)

        executor = FoamAgentExecutor()
        result = executor.execute(make_task())
        assert result.success is False
        assert "not found" in result.error_message
        assert "docker start" in result.error_message

    def test_execute_magicmock_notfound_falls_through_to_generic_hint(
        self, monkeypatch
    ):
        """When docker.errors.NotFound is a MagicMock attribute rather than
        a real class (the common mocking pattern), isinstance() against it
        would normally raise TypeError. The type-guard must detect the
        non-class attribute and route to the generic 'unavailable' branch
        instead of crashing. Regression guard for the type-guard fix
        shipped alongside DEC-V61-020."""
        class FakeDockerException(Exception):
            pass

        mock_docker = MagicMock()
        mock_docker.errors.DockerException = FakeDockerException
        # mock_docker.errors.NotFound is auto-created as a MagicMock attr
        # (NOT a class) — exactly the scenario the type-guard defends.
        mock_docker.from_env.side_effect = FakeDockerException(
            "generic daemon error"
        )

        import sys as _sys
        monkeypatch.setitem(_sys.modules, "docker", mock_docker)
        monkeypatch.setitem(_sys.modules, "docker.errors", mock_docker.errors)
        monkeypatch.setattr("src.foam_agent_adapter._DOCKER_AVAILABLE", True)
        monkeypatch.setattr("src.foam_agent_adapter.docker", mock_docker)

        executor = FoamAgentExecutor()
        result = executor.execute(make_task())
        assert result.success is False
        # Generic branch — does NOT claim the container was specifically
        # 'not found', because the MagicMock attribute couldn't be used
        # in isinstance() dispatch.
        assert "generic daemon error" in result.error_message
        assert "unavailable" in result.error_message

    # ------------------------------------------------------------------
    # _fail() tests
    # ------------------------------------------------------------------

    def test_fail_returns_failed_result(self):
        result = FoamAgentExecutor._fail("test error", 1.5)
        assert result.success is False
        assert result.is_mock is False
        assert result.error_message == "test error"
        assert result.execution_time_s == 1.5
        assert result.residuals == {}
        assert result.key_quantities == {}

    def test_fail_with_raw_output_path(self):
        result = FoamAgentExecutor._fail("error", 2.0, raw_output_path="/tmp/case")
        assert result.success is False
        assert result.raw_output_path == "/tmp/case"

    def test_extract_cylinder_strouhal_fails_closed_without_case_dir(self):
        """DEC-V61-041: the old code hardcoded strouhal_number=0.165 for
        Re∈[50,200] from a single snapshot, regardless of solver
        convergence. That was the core PASS-washing bug. The new path
        requires the forceCoeffs FO output (reached only when
        case_dir is supplied). Without case_dir, extractor emits NO
        strouhal_number — DEC-V61-036 G1 picks up the missing quantity."""
        task = TaskSpec(
            name="cylinder",
            geometry_type=GeometryType.BODY_IN_CHANNEL,
            flow_type=FlowType.EXTERNAL,
            steady_state=SteadyState.TRANSIENT,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=100,
        )
        result = FoamAgentExecutor._extract_cylinder_strouhal(
            [0.05, -0.05, 0.0, 0.0],
            [0.0, 0.0, 0.05, -0.05],
            [1.5e10, -1.5e10, 1.5e10, -1.5e10],
            task,
            {},
        )
        # No case_dir, no fabricated strouhal_number. Diagnostics
        # (p_rms_near_cylinder) may still emit but they are DIAGNOSTICS
        # not the measurement itself.
        assert "strouhal_number" not in result

    def test_extract_cylinder_strouhal_records_diagnostic_pressure_rms(self):
        """Diagnostic p_rms / Cp_rms still emitted for debugging a
        MOCK or pre-DEC run, but NOT used to fabricate strouhal_number
        (which was the PASS-washing path retired in DEC-V61-041)."""
        task = TaskSpec(
            name="cylinder",
            geometry_type=GeometryType.BODY_IN_CHANNEL,
            flow_type=FlowType.EXTERNAL,
            steady_state=SteadyState.TRANSIENT,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=100,
        )
        result = FoamAgentExecutor._extract_cylinder_strouhal(
            [0.05, -0.05, 0.0, 0.0],
            [0.0, 0.0, 0.05, -0.05],
            [0.10, -0.10, 0.00, 0.05],
            task,
            {},
        )
        assert "strouhal_number" not in result
        assert result["p_rms_near_cylinder"] == pytest.approx(0.073950997289)
        assert result["pressure_coefficient_rms_near_cylinder"] == pytest.approx(0.147901994577)

    def test_extract_nc_nusselt_uses_horizontal_wall_gradient_for_side_heated_cavity(self):
        """DEC-V61-042: extractor uses the shared 3-point wall-gradient
        stencil via BC metadata plumbed by _generate_natural_convection_cavity.
        Construct a LINEAR T(x) so the stencil is exact — verifies both
        orientation (hot wall at x=min) and numerical correctness."""
        # Linear T(x) = T_hot + slope·x, slope=-10/L=-5 → |grad|=5
        # Nu = 5 · L / dT = 5 · 2 / 10 = 1.0
        task = TaskSpec(
            name="nc-cavity",
            geometry_type=GeometryType.NATURAL_CONVECTION_CAVITY,
            flow_type=FlowType.NATURAL_CONVECTION,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
            boundary_conditions={
                "dT": 10.0,
                "L": 2.0,
                "aspect_ratio": 2.0,
                "wall_coord_hot": 0.0,
                "T_hot_wall": 305.0,
                "wall_bc_type": "fixedValue",
            },
        )
        cxs = [0.05, 0.15, 1.0, 1.85, 1.95] * 3
        cys = [0.05] * 5 + [0.50] * 5 + [0.95] * 5
        slope = -5.0
        t_vals = [305.0 + slope * x for x in cxs]

        result = FoamAgentExecutor._extract_nc_nusselt(cxs, cys, t_vals, task, {})

        assert result["nusselt_number"] == pytest.approx(1.0, abs=1e-9)
        assert result["nusselt_number_source"] == "wall_gradient_stencil_3pt"

    def test_extract_nc_nusselt_fails_closed_without_bc_metadata(self):
        """DEC-V61-042: without wall_coord_hot / T_hot_wall / wall_bc_type
        plumbed through, the extractor must emit NO nusselt_number (so
        DEC-V61-036 G1 MISSING_TARGET_QUANTITY fires at the comparator)."""
        task = TaskSpec(
            name="nc-cavity",
            geometry_type=GeometryType.NATURAL_CONVECTION_CAVITY,
            flow_type=FlowType.NATURAL_CONVECTION,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
            boundary_conditions={"dT": 10.0, "L": 2.0, "aspect_ratio": 2.0},
        )
        cxs = [0.05, 0.15, 1.0] * 2
        cys = [0.05] * 3 + [0.95] * 3
        t_vals = [305.0, 300.0, 295.0] * 2

        result = FoamAgentExecutor._extract_nc_nusselt(cxs, cys, t_vals, task, {})

        # Absence of nusselt_number is the signal (DEC-036 G1 fires at the
        # comparator). No extractor-internal flags leak into key_quantities.
        assert "nusselt_number" not in result
        assert not any(k.startswith("_") for k in result)

    def test_extract_nc_nusselt_averages_gradient_over_y_for_wall_packed_mesh(self):
        """DEC-V61-042: verify per-y-layer averaging. Each layer has a
        LINEAR profile with a different slope so the stencil is exact
        per-layer; the extractor averages the three |grad| values."""
        task = TaskSpec(
            name="nc-cavity",
            geometry_type=GeometryType.NATURAL_CONVECTION_CAVITY,
            flow_type=FlowType.NATURAL_CONVECTION,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
            boundary_conditions={
                "dT": 10.0,
                "L": 2.0,
                "aspect_ratio": 2.0,
                "wall_coord_hot": 0.0,
                "T_hot_wall": 305.0,
                "wall_bc_type": "fixedValue",
            },
        )
        cxs = [0.05, 0.15, 1.0, 1.85, 1.95] * 3
        cys = [0.10] * 5 + [0.50] * 5 + [0.90] * 5
        # Per-layer slopes: -3, -5, -7 → |grad|={3,5,7}, avg=5
        # Nu = 5 · 2 / 10 = 1.0
        slopes = [-3.0, -5.0, -7.0]
        t_vals = []
        for slope in slopes:
            t_vals.extend(305.0 + slope * x for x in cxs[:5])

        result = FoamAgentExecutor._extract_nc_nusselt(cxs, cys, t_vals, task, {})

        assert result["nusselt_number"] == pytest.approx(1.0, abs=1e-9)
        # midPlaneT preservation: middle layer (y=0.5) with slope -5.
        expected_mid = [305.0 + (-5.0) * x for x in [0.05, 0.15, 1.0, 1.85, 1.95]]
        assert result["midPlaneT"] == pytest.approx(expected_mid)
        assert result["midPlaneT_y"] == pytest.approx([0.05, 0.15, 1.0, 1.85, 1.95])

    def test_extract_airfoil_cp_tracks_surface_profile(self):
        task = make_airfoil_task()
        z_01 = FoamAgentExecutor._naca0012_half_thickness(0.1)
        z_03 = FoamAgentExecutor._naca0012_half_thickness(0.3)
        z_07 = FoamAgentExecutor._naca0012_half_thickness(0.7)

        result = FoamAgentExecutor._extract_airfoil_cp(
            cxs=[0.1, 0.1, 0.3, 0.3, 0.7, 0.7, -1.0, 2.0],
            czs=[z_01, -z_01, z_03, -z_03, z_07, -z_07, 0.0, 0.0],
            p_vals=[0.5, 0.5, -0.25, -0.25, 0.0, 0.0, 0.0, 0.0],
            task_spec=task,
            key_quantities={},
        )

        assert result["pressure_coefficient_x"] == pytest.approx([0.1, 0.3, 0.7], abs=1e-3)
        assert result["pressure_coefficient"] == pytest.approx([1.0, -0.5, 0.0], abs=1e-6)

    def test_extract_flat_plate_cf_records_spalding_fallback_activation(self):
        task = TaskSpec(
            name="Turbulent Flat Plate (Zero Pressure Gradient)",
            geometry_type=GeometryType.SIMPLE_GRID,
            flow_type=FlowType.EXTERNAL,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=100000,
        )

        result = FoamAgentExecutor._extract_flat_plate_cf(
            cxs=[0.5, 0.5, 0.5],
            cys=[0.0, 1e-4, 2e-4],
            u_vecs=[(0.0, 0.0, 0.0), (0.1, 0.0, 0.0), (0.2, 0.0, 0.0)],
            task_spec=task,
            key_quantities={},
        )

        expected_cf = 0.0576 / (50000**0.2)
        assert result["cf_spalding_fallback_activated"] is True
        assert result["cf_spalding_fallback_count"] >= 1
        assert result["cf_skin_friction"] == pytest.approx(expected_cf)
        assert result["cf_skin_friction"] == pytest.approx(expected_cf, rel=0.0, abs=1e-12)

    def test_extract_flat_plate_cf_no_fallback_when_cf_below_threshold(self):
        task = TaskSpec(
            name="Turbulent Flat Plate (Zero Pressure Gradient)",
            geometry_type=GeometryType.SIMPLE_GRID,
            flow_type=FlowType.EXTERNAL,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=100000,
        )

        result = FoamAgentExecutor._extract_flat_plate_cf(
            cxs=[0.5, 0.5, 0.5],
            cys=[0.0, 0.01, 0.02],
            u_vecs=[(0.0, 0.0, 0.0), (0.01, 0.0, 0.0), (0.03, 0.0, 0.0)],
            task_spec=task,
            key_quantities={},
        )

        assert result["cf_spalding_fallback_activated"] is False
        assert result["cf_spalding_fallback_count"] == 0
        assert result["cf_skin_friction"] == pytest.approx(4e-05)

    # ------------------------------------------------------------------
    # _generate_lid_driven_cavity() tests
    # ------------------------------------------------------------------

    def test_generate_lid_driven_cavity_creates_files(self, tmp_path):
        """验证 _generate_lid_driven_cavity 生成所有必需文件。"""
        # Mock shutil.rmtree to prevent cleanup
        with patch("src.foam_agent_adapter.shutil.rmtree"):
            executor = FoamAgentExecutor()
            executor._generate_lid_driven_cavity(tmp_path, make_task())

        # 验证目录结构
        assert (tmp_path / "system").is_dir()
        assert (tmp_path / "constant").is_dir()
        assert (tmp_path / "0").is_dir()

        # 验证必需文件
        assert (tmp_path / "system" / "blockMeshDict").is_file()
        assert (tmp_path / "system" / "controlDict").is_file()
        assert (tmp_path / "system" / "fvSchemes").is_file()
        assert (tmp_path / "system" / "fvSolution").is_file()
        assert (tmp_path / "system" / "sampleDict").is_file()
        assert (tmp_path / "constant" / "physicalProperties").is_file()
        assert (tmp_path / "0" / "U").is_file()
        assert (tmp_path / "0" / "p").is_file()

    def test_generate_lid_driven_cavity_default_lid_velocity(self, tmp_path):
        """验证默认顶盖速度 (1 0 0) 写入到 0/U 文件。"""
        with patch("src.foam_agent_adapter.shutil.rmtree"):
            executor = FoamAgentExecutor()
            executor._generate_lid_driven_cavity(tmp_path, make_task())

        u_file = (tmp_path / "0" / "U").read_text()
        # 默认 lid 速度为 (1 0 0)
        assert "value           uniform (1 0 0);" in u_file
        # 验证 lid 边界存在
        assert "lid" in u_file

    def test_generate_lid_driven_cavity_sample_dict(self, tmp_path):
        """验证 sampleDict 包含 mid-plane velocity sampling 配置。"""
        with patch("src.foam_agent_adapter.shutil.rmtree"):
            executor = FoamAgentExecutor()
            executor._generate_lid_driven_cavity(tmp_path, make_task())

        sample_file = (tmp_path / "system" / "sampleDict").read_text()
        # 验证 uCenterline set 配置
        assert "uCenterline" in sample_file
        assert "axis        y" in sample_file
        assert "fields" in sample_file
        assert "(U)" in sample_file

    def test_generate_airfoil_flow_creates_real_surface_files(self, tmp_path):
        executor = FoamAgentExecutor()
        executor._generate_airfoil_flow(tmp_path, make_airfoil_task())

        obj_file = tmp_path / "constant" / "geometry" / "NACA0012.obj"
        assert obj_file.is_file()
        assert not (tmp_path / "system" / "extrudeMeshDict").exists()
        obj_text = obj_file.read_text()
        assert obj_text.count("\nv ") > 100
        assert "\nf " in obj_text
        obj_vertices = [
            tuple(float(value) for value in line.split()[1:])
            for line in obj_text.splitlines()
            if line.startswith("v ")
        ]
        assert obj_vertices
        assert sorted({round(vertex[1], 6) for vertex in obj_vertices}) == [-0.001, 0.001]
        assert max(abs(vertex[2]) for vertex in obj_vertices) > 0.05

        block_mesh = (tmp_path / "system" / "blockMeshDict").read_text()
        assert "triSurfaceMesh" in block_mesh
        assert "project 4 7 (aerofoil)" in block_mesh
        assert "project (" not in block_mesh
        assert "aerofoil" in block_mesh
        assert "leadingArc" not in block_mesh
        assert "searchableCylinder" not in block_mesh
        assert "(30 1 80)" in block_mesh
        assert "(40 1 80)" in block_mesh
        assert "simpleGrading (10 1 40)" in block_mesh
        assert "type            empty;" in block_mesh

        u_file = (tmp_path / "0" / "U").read_text()
        assert "noSlip" in u_file
        assert "aerofoil" in u_file

    def test_generate_airfoil_flow_writes_stabilized_fvsolution_and_turbulence_init(self):
        case_dir = Path(tempfile.mkdtemp())
        try:
            executor = FoamAgentExecutor()
            executor._generate_airfoil_flow(case_dir, make_airfoil_task())

            fv_solution = (case_dir / "system" / "fvSolution").read_text()
            p_match = re.search(r"\bp\s*\{[^}]*\brelTol\s+([0-9.eE+-]+);", fv_solution, re.S)
            assert p_match is not None
            assert float(p_match.group(1)) == pytest.approx(0.05)

            for field_name in ("U", "k", "omega"):
                field_match = re.search(
                    rf"equations\s*\{{[^}}]*\b{field_name}\s+([0-9.eE+-]+);",
                    fv_solution,
                    re.S,
                )
                assert field_match is not None
                assert float(field_match.group(1)) == pytest.approx(0.5)

            k_text = (case_dir / "0" / "k").read_text()
            omega_text = (case_dir / "0" / "omega").read_text()

            k_match = re.search(r"internalField\s+uniform\s+([0-9.eE+-]+);", k_text)
            omega_match = re.search(r"internalField\s+uniform\s+([0-9.eE+-]+);", omega_text)
            assert k_match is not None
            assert omega_match is not None
            assert float(k_match.group(1)) == pytest.approx(3.75e-5, rel=1e-6)
            # omega = sqrt(k) / (Cmu^0.25 * L) = sqrt(3.75e-5) / (0.5623 * 0.1) ≈ 0.109
            assert float(omega_match.group(1)) == pytest.approx(0.109, rel=0.05)
        finally:
            shutil.rmtree(case_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # _make_tarball() tests
    # ------------------------------------------------------------------

    def test_make_tarball_returns_bytes(self, tmp_path):
        """验证 _make_tarball 返回有效的 tarball bytes。"""
        # 创建测试文件
        (tmp_path / "test.txt").write_text("hello world")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "nested.txt").write_text("nested")

        tarball_bytes = FoamAgentExecutor._make_tarball(tmp_path)
        assert isinstance(tarball_bytes, bytes)
        assert len(tarball_bytes) > 0

        # 验证 tarball 内容
        buf = io.BytesIO(tarball_bytes)
        with tarfile.open(fileobj=buf, mode="r") as tar:
            names = tar.getnames()
            assert "test.txt" in names
            assert "subdir" in names
            assert "subdir/nested.txt" in names

    def test_make_tarball_empty_dir(self, tmp_path):
        """验证空目录也能生成 tarball。"""
        tarball_bytes = FoamAgentExecutor._make_tarball(tmp_path)
        assert isinstance(tarball_bytes, bytes)

    # ------------------------------------------------------------------
    # _parse_solver_log() tests
    # ------------------------------------------------------------------

    def test_parse_solver_log_extracts_residuals(self, tmp_path):
        """验证 _parse_solver_log 从 log 文件提取残差。"""
        log_content = """
Execution time = 0.123 s,  ClockTime = 0.200 s
#0  Foam::error::printStack(Foam::Ostream&) at ???
#1  Foam::debug
time step continuity errors : sum local = 1.23e-05, global = 4.56e-07, cumulative = 4.56e-07
ICCGG:  Solving for p, Initial residual = 0.000123, Final residual = 1.23e-06, No Iterations 2
Solving for Ux, Initial residual = 0.001234, Final residual = 1.23e-05, No Iterations 3
Solving for Uy, Initial residual = 0.000987, Final residual = 9.87e-06, No Iterations 3
Execution time = 0.456 s,  ClockTime = 0.500 s
        """
        log_path = tmp_path / "log.icoFoam"
        log_path.write_text(log_content)

        executor = FoamAgentExecutor()
        residuals, key_quantities = executor._parse_solver_log(log_path)

        assert "p" in residuals
        assert "Ux" in residuals
        assert "Uy" in residuals
        assert residuals["Ux"] == pytest.approx(0.001234)

    def test_parse_solver_log_missing_file(self, tmp_path):
        """日志文件不存在时返回空字典。"""
        executor = FoamAgentExecutor()
        residuals, key_quantities = executor._parse_solver_log(tmp_path / "nonexistent.log")
        assert residuals == {}
        assert key_quantities == {}

    def test_parse_solver_log_with_postprocessing(self, tmp_path):
        """验证 postProcessing 目录存在时的处理。"""
        log_path = tmp_path / "log.icoFoam"
        log_path.write_text("Solving for Ux, Initial residual = 0.001, Final residual = 1e-5\n")
        post_dir = tmp_path / "postProcessing"
        post_dir.mkdir()
        # 创建空的 postProcessing 子目录（不包含有效数据文件时 key_quantities 为空）
        (post_dir / "test").mkdir()

        executor = FoamAgentExecutor()
        residuals, key_quantities = executor._parse_solver_log(log_path)
        assert residuals.get("Ux") == pytest.approx(0.001)

    def test_parse_solver_log_maps_ldc_raw_sample(self, tmp_path):
        """setFormat raw 输出 x y z Ux Uy Uz (6列) 被正确解析为 u_centerline。"""
        log_path = tmp_path / "log.icoFoam"
        log_path.write_text("Solving for Ux, Initial residual = 0.001\n")
        post_dir = tmp_path / "postProcessing"
        sets_dir = post_dir / "sets"
        time_dir = sets_dir / "1.0"
        time_dir.mkdir(parents=True)
        # setFormat raw: x y z Ux Uy Uz (6列，无 leading Time)
        raw_content = (
            "#  Time  x  y  z  Ux  Uy  Uz\n"
            "0.0 0.5 0.1 0.5 -0.25 0.0 0.0\n"
            "0.0 0.5 0.3 0.5 -0.10 0.0 0.0\n"
            "0.0 0.5 0.5 0.5  0.00 0.0 0.0\n"
            "0.0 0.5 0.7 0.5  0.15 0.0 0.0\n"
            "0.0 0.5 0.9 0.5  0.25 0.0 0.0\n"
        )
        (time_dir / "U_uCenterline").write_text(raw_content)

        ldc_task = TaskSpec(
            name="Lid-Driven Cavity",
            geometry_type=GeometryType.SIMPLE_GRID,
            flow_type=FlowType.INTERNAL,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=100,
        )
        executor = FoamAgentExecutor()
        residuals, key_quantities = executor._parse_solver_log(log_path, "icoFoam", ldc_task)
        # 7列格式正确解析: Time=0.0, x=0.5, y=0.1, z=0.5, Ux=-0.25 → y=0.1, Ux=-0.25
        # u_centerline 映射由 LDC route (is_lid_driven_cavity_case) 完成
        assert "u_centerline" in key_quantities
        assert key_quantities["u_centerline"] == pytest.approx([-0.25, -0.10, 0.00, 0.15, 0.25])
        assert key_quantities["u_centerline_y"] == pytest.approx([0.1, 0.3, 0.5, 0.7, 0.9])

    def test_parse_solver_log_extracts_bfs_reattachment_from_raw_sample(self, tmp_path):
        """raw 格式 wallProfile (6列 x y z Ux Uy Uz) 被解析并计算出 reattachment_length。"""
        log_path = tmp_path / "log.simpleFoam"
        log_path.write_text("Solving for Ux, Initial residual = 0.001\n")
        post_dir = tmp_path / "postProcessing"
        sets_dir = post_dir / "sets"
        time_dir = sets_dir / "500"
        time_dir.mkdir(parents=True)
        # setFormat raw: x y z Ux Uy Uz (6列) — BFS wall at y=0.5
        # x=1→Ux=-1, x=2→Ux=-0.5, x=2.5→Ux=0.1, x=3→Ux=1 — 零交点在 x≈2.417
        raw_content = (
            "1.0 0.5 0.0 -1.0 0.0 0.0\n"
            "2.0 0.5 0.0 -0.5 0.0 0.0\n"
            "2.5 0.5 0.0  0.1 0.0 0.0\n"
            "3.0 0.5 0.0  1.0 0.0 0.0\n"
        )
        (time_dir / "U_wallProfile").write_text(raw_content)

        bfs_task = TaskSpec(
            name="Backward-Facing Step",
            geometry_type=GeometryType.BACKWARD_FACING_STEP,
            flow_type=FlowType.INTERNAL,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=100,
        )
        executor = FoamAgentExecutor()
        residuals, key_quantities = executor._parse_solver_log(log_path, "simpleFoam", bfs_task)
        # BFS route computes reattachment_length then deletes wallProfile* keys
        assert "reattachment_length" in key_quantities
        # x_re = 2 + (-0.5) * (2.5-2) / (0.1-(-0.5)) = 2 + 0.5*0.5/0.6 ≈ 2.417
        assert key_quantities["reattachment_length"] == pytest.approx(2.4167, abs=0.01)
        # wallProfile_x was used for the calculation, then cleaned up
        assert "wallProfile_x" not in key_quantities
        # P6-TD-001: no upstream-artifact flag on a valid detection
        assert "reattachment_detection_upstream_artifact" not in key_quantities

    def test_bfs_reattachment_rejects_upstream_detection_with_producer_flag(self, tmp_path):
        """P6-TD-001: under-converged solver produces Ux zero-crossing at
        x < 0 (upstream of step at x=0). Extractor must reject the garbage
        detection and emit a producer flag rather than publish a negative
        reattachment_length (which is physically meaningless and would
        mislead regulatory reviewers). Real incident: §5d Part-2 acceptance
        run produced reattachment_length = -5.38."""
        log_path = tmp_path / "log.simpleFoam"
        log_path.write_text("Solving for Ux, Initial residual = 0.001\n")
        post_dir = tmp_path / "postProcessing"
        sets_dir = post_dir / "sets"
        time_dir = sets_dir / "10"  # low iteration count = under-converged
        time_dir.mkdir(parents=True)
        # Ux signs that make the scanner fire at negative x (noise pattern
        # seen when the solver hasn't converged: free-stream region has
        # mixed-sign Ux upstream of the step).
        raw_content = (
            "-8.0 0.5 0.0 -1.0 0.0 0.0\n"
            "-5.0 0.5 0.0 -0.5 0.0 0.0\n"
            "-4.5 0.5 0.0  0.1 0.0 0.0\n"  # zero-crossing at x ≈ -4.58
            "-4.0 0.5 0.0  1.0 0.0 0.0\n"
        )
        (time_dir / "U_wallProfile").write_text(raw_content)

        bfs_task = TaskSpec(
            name="Backward-Facing Step",
            geometry_type=GeometryType.BACKWARD_FACING_STEP,
            flow_type=FlowType.INTERNAL,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=100,
        )
        executor = FoamAgentExecutor()
        _, key_quantities = executor._parse_solver_log(log_path, "simpleFoam", bfs_task)
        # reattachment_length was NOT published (physical-plausibility guard)
        assert "reattachment_length" not in key_quantities
        # Producer flag tells downstream audit this wasn't a valid detection
        assert key_quantities.get("reattachment_detection_upstream_artifact") is True
        rejected = key_quantities.get("reattachment_detection_rejected_x")
        assert rejected is not None and rejected < 0

    def test_extract_bfs_reattachment_static_rejects_upstream_detection(self):
        """P6-TD-001 coverage gap follow-up (Codex round 7 Low #1): the
        guard lives in both _parse_solver_log and the static extractor
        called from _parse_writeobjects_fields. This test exercises the
        static path directly — same Ux zero-crossing pattern at x≈-4.58
        that §5d Part-2 produced via writeObjects fields. Must reject.

        DEC-V61-052 rewrite narrowed the Ux-proxy band to y<0.025 under the
        canonical 3-block mesh; sample points shifted to y=0.01 to stay
        inside the band while preserving the upstream-crossing pattern."""
        cxs = [-8.0, -5.0, -4.5, -4.0]
        cys = [0.01, 0.01, 0.01, 0.01]
        u_vecs = [(-1.0, 0.0, 0.0), (-0.5, 0.0, 0.0), (0.1, 0.0, 0.0), (1.0, 0.0, 0.0)]
        bfs_task = TaskSpec(
            name="Backward-Facing Step",
            geometry_type=GeometryType.BACKWARD_FACING_STEP,
            flow_type=FlowType.INTERNAL,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=100,
        )
        result = FoamAgentExecutor._extract_bfs_reattachment(
            cxs, cys, u_vecs, bfs_task, {}
        )
        assert "reattachment_length" not in result
        assert result.get("reattachment_detection_upstream_artifact") is True
        rejected = result.get("reattachment_detection_rejected_x")
        assert rejected is not None and rejected < 0

    def test_extract_bfs_reattachment_static_accepts_valid_downstream_detection(self):
        """P6-TD-001 positive-case companion: valid downstream Ux zero-
        crossing produces reattachment_length without the artifact flag.

        DEC-V61-052 band narrowed to y<0.025 — sample points placed at y=0.01
        (within first B1 cell layer)."""
        cxs = [0.5, 1.5, 2.5, 3.5]
        cys = [0.01, 0.01, 0.01, 0.01]
        u_vecs = [(-0.4, 0.0, 0.0), (-0.1, 0.0, 0.0), (0.2, 0.0, 0.0), (0.8, 0.0, 0.0)]
        bfs_task = TaskSpec(
            name="Backward-Facing Step",
            geometry_type=GeometryType.BACKWARD_FACING_STEP,
            flow_type=FlowType.INTERNAL,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=100,
        )
        result = FoamAgentExecutor._extract_bfs_reattachment(
            cxs, cys, u_vecs, bfs_task, {}
        )
        assert "reattachment_length" in result
        assert result["reattachment_length"] > 0
        assert "reattachment_detection_upstream_artifact" not in result

    def test_parse_writeobjects_fields_extracts_ldc_from_icofoam_fields(self, tmp_path, monkeypatch):
        """icoFoam + SIMPLE_GRID 走 LDC 路由（_is_lid_driven_cavity_case 检测到）。"""
        time_dir = tmp_path / "1.0"
        time_dir.mkdir()
        # 写入最小化场文件（实际读取会被 mock 替代）
        (time_dir / "Cx").write_text("1\n(\n0.050\n)\n")
        (time_dir / "Cy").write_text("1\n(\n0.050\n)\n")
        (time_dir / "U").write_text("1\n(\n(0.0 0.1 0.0)\n)\n")

        ldc_task = TaskSpec(
            name="Lid-Driven Cavity",
            geometry_type=GeometryType.SIMPLE_GRID,
            flow_type=FlowType.INTERNAL,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=100,
        )
        executor = FoamAgentExecutor()

        # Mock the static extractor so _parse_writeobjects_fields exercises the LDC routing
        mock_result = {"u_centerline": [0.0, 0.05, 0.10], "u_centerline_y": [0.0, 0.5, 1.0]}
        monkeypatch.setattr(FoamAgentExecutor, "_extract_ldc_centerline", lambda *args, **kwargs: mock_result)

        key_quantities = {}
        result = executor._parse_writeobjects_fields(tmp_path, "icoFoam", ldc_task, key_quantities)
        # SIMPLE_GRID + icoFoam → _is_lid_driven_cavity_case → _extract_ldc_centerline called
        assert result == mock_result

    def test_parse_writeobjects_fields_routes_airfoil_to_cp_extractor(self, tmp_path, monkeypatch):
        time_dir = tmp_path / "1.0"
        time_dir.mkdir()
        (time_dir / "Cx").write_text("1\n(\n0.300\n)\n")
        (time_dir / "Cy").write_text("1\n(\n0.050\n)\n")
        (time_dir / "U").write_text("1\n(\n(1.0 0.0 0.0)\n)\n")
        (time_dir / "p").write_text("1\n(\n0.100\n)\n")

        executor = FoamAgentExecutor()
        mock_result = {
            "pressure_coefficient": [-0.5, 0.2],
            "pressure_coefficient_x": [0.3, 1.0],
        }
        monkeypatch.setattr(
            FoamAgentExecutor,
            "_extract_airfoil_cp",
            lambda *args, **kwargs: mock_result,
        )

        result = executor._parse_writeobjects_fields(
            tmp_path,
            "simpleFoam",
            make_airfoil_task(),
            {},
        )
        assert result == mock_result

    def test_parse_writeobjects_fields_skips_flat_plate_extractor_for_duct_flow(self, tmp_path, monkeypatch):
        """P6-TD-002: duct_flow (SIMPLE_GRID + Re>=2300 + hydraulic_diameter)
        must NOT dispatch to _extract_flat_plate_cf. Without this guard, the
        Spalding fallback at Re_x=0.5*Re returns a parameter-independent Cf
        identical to any other SIMPLE_GRID case sharing the same Re — §5d
        Part-2 observed TFP and duct_flow both returning 0.007600365566051871
        (both Re=50000). The guard emits a producer flag instead of calling
        the wrong extractor.
        """
        time_dir = tmp_path / "1.0"
        time_dir.mkdir()
        (time_dir / "Cx").write_text("1\n(\n0.500\n)\n")
        (time_dir / "Cy").write_text("1\n(\n0.050\n)\n")
        (time_dir / "U").write_text("1\n(\n(1.0 0.0 0.0)\n)\n")

        duct_task = TaskSpec(
            name="Fully Developed Turbulent Square-Duct Flow",
            geometry_type=GeometryType.SIMPLE_GRID,
            flow_type=FlowType.INTERNAL,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=50000,
            boundary_conditions={
                "hydraulic_diameter": 0.1,
                "aspect_ratio": 1.0,
            },
        )
        executor = FoamAgentExecutor()

        # If the guard fails, this would be called and return a Spalding
        # fallback Cf. Mock it to raise so test fails LOUDLY if dispatch
        # regressed.
        def _should_not_run(*args, **kwargs):
            raise AssertionError(
                "P6-TD-002 regression: duct_flow dispatched to "
                "_extract_flat_plate_cf (should be guarded by "
                "hydraulic_diameter presence check)"
            )
        monkeypatch.setattr(
            FoamAgentExecutor, "_extract_flat_plate_cf", _should_not_run
        )

        result = executor._parse_writeobjects_fields(
            tmp_path, "simpleFoam", duct_task, {}
        )
        # Flat-plate extractor NOT called → no cf_skin_friction published.
        assert "cf_skin_friction" not in result
        # Producer flag set for downstream audit. Round-8 rename:
        # duct_flow_extractor_missing → duct_flow_extractor_pending so the
        # flag reads as "planned-but-unimplemented" rather than "malformed".
        assert result.get("duct_flow_extractor_pending") is True
        assert result.get("duct_flow_hydraulic_diameter") == 0.1
        assert "duct_flow_hydraulic_diameter_missing" not in result

    def test_parse_writeobjects_fields_still_routes_flat_plate_without_hydraulic_diameter(
        self, tmp_path, monkeypatch
    ):
        """P6-TD-002 regression protection: the new guard must NOT break
        normal flat-plate dispatch. A TaskSpec without hydraulic_diameter
        still hits _extract_flat_plate_cf."""
        time_dir = tmp_path / "1.0"
        time_dir.mkdir()
        (time_dir / "Cx").write_text("1\n(\n0.500\n)\n")
        (time_dir / "Cy").write_text("1\n(\n0.050\n)\n")
        (time_dir / "U").write_text("1\n(\n(1.0 0.0 0.0)\n)\n")

        flat_plate_task = TaskSpec(
            name="Turbulent Flat Plate",
            geometry_type=GeometryType.SIMPLE_GRID,
            flow_type=FlowType.INTERNAL,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=50000,
            boundary_conditions={"plate_length": 1.0},
        )

        called = {"yes": False}
        def _spy(*args, **kwargs):
            called["yes"] = True
            return {"cf_skin_friction": 0.0076, "cf_spalding_fallback_activated": True}
        monkeypatch.setattr(FoamAgentExecutor, "_extract_flat_plate_cf", _spy)

        executor = FoamAgentExecutor()
        result = executor._parse_writeobjects_fields(
            tmp_path, "simpleFoam", flat_plate_task, {}
        )
        # Dispatch still fires for flat plate.
        assert called["yes"] is True
        assert result["cf_skin_friction"] == pytest.approx(0.0076)
        # No duct producer flag on flat plate.
        assert "duct_flow_extractor_pending" not in result
        assert "duct_flow_extractor_missing" not in result

    def test_parse_writeobjects_fields_routes_duct_by_name_without_hydraulic_diameter(
        self, tmp_path, monkeypatch
    ):
        """P6-TD-002 round-8 correction (Codex CHANGES_REQUIRED Blocking):
        the list_whitelist_cases() constructor path leaves `hydraulic_diameter`
        under `parameters` (not merged into `boundary_conditions`).

        The dispatcher MUST still route duct-identified tasks away from the
        flat-plate extractor, even when hydraulic_diameter is absent from
        boundary_conditions. Fail-closed via duct_flow_hydraulic_diameter_missing
        flag rather than silently falling through to Spalding Cf."""
        time_dir = tmp_path / "1.0"
        time_dir.mkdir()
        (time_dir / "Cx").write_text("1\n(\n0.500\n)\n")
        (time_dir / "Cy").write_text("1\n(\n0.050\n)\n")
        (time_dir / "U").write_text("1\n(\n(1.0 0.0 0.0)\n)\n")

        duct_task_no_bc = TaskSpec(
            name="Fully Developed Turbulent Square-Duct Flow",
            geometry_type=GeometryType.SIMPLE_GRID,
            flow_type=FlowType.INTERNAL,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=50000,
            boundary_conditions={},
        )

        def _should_not_run(*args, **kwargs):
            raise AssertionError(
                "duct-named task fell through to flat-plate extractor"
            )
        monkeypatch.setattr(
            FoamAgentExecutor, "_extract_flat_plate_cf", _should_not_run
        )

        executor = FoamAgentExecutor()
        result = executor._parse_writeobjects_fields(
            tmp_path, "simpleFoam", duct_task_no_bc, {}
        )
        assert "cf_skin_friction" not in result
        assert result.get("duct_flow_extractor_pending") is True
        assert result.get("duct_flow_hydraulic_diameter_missing") is True

    def test_is_duct_flow_case_integrates_with_knowledge_db(self):
        """Integration coverage for the canonical construction path.
        KnowledgeDB.list_whitelist_cases() does NOT merge `parameters`
        into `boundary_conditions`, so the dispatcher must detect duct
        via name. Regression-protect against the Codex round-8 blocker."""
        from src.knowledge_db import KnowledgeDB
        db = KnowledgeDB()
        cases = db.list_whitelist_cases()
        duct_specs = [
            s for s in cases
            if "duct" in s.name.lower() or "pipe_flow" in s.name.lower()
        ]
        assert duct_specs, "whitelist must contain at least one duct case"
        for spec in duct_specs:
            assert FoamAgentExecutor._is_duct_flow_case(spec), (
                f"duct spec {spec.name!r} not detected by name — round-8 regression"
            )

    # ------------------------------------------------------------------
    # execute() Docker success path tests
    # ------------------------------------------------------------------

    def test_execute_success_path(self, tmp_path, monkeypatch):
        """验证 execute() 在 Docker exec 成功时的完整流程。"""
        # Mock docker module
        mock_container = MagicMock()
        mock_container.status = "running"
        # Simulate successful blockMesh and icoFoam execution
        mock_container.exec_run.return_value = MagicMock(exit_code=0)

        mock_client = MagicMock()
        mock_client.containers.get.return_value = mock_container

        mock_docker = MagicMock()
        mock_docker.from_env.return_value = mock_client

        # Patch docker at module level
        monkeypatch.setattr("src.foam_agent_adapter.docker", mock_docker)
        monkeypatch.setattr("src.foam_agent_adapter._DOCKER_AVAILABLE", True)

        # Mock container methods used in _docker_exec
        def put_archive_side_effect(path, data):
            pass

        def get_archive_side_effect(path):
            # Return minimal tar with log file content
            buf = io.BytesIO()
            with tarfile.open(fileobj=buf, mode="w") as tar:
                info = tarfile.TarInfo(name="log.icoFoam")
                content = b"Solving for Ux, Initial residual = 0.001, Final residual = 1e-5\nSolving for Uy, Initial residual = 0.0008, Final residual = 8e-6\n"
                info.size = len(content)
                tar.addfile(info, io.BytesIO(content))
            buf.seek(0)
            return b"".join(buf.read()), {}

        mock_container.put_archive.side_effect = put_archive_side_effect
        mock_container.get_archive.side_effect = get_archive_side_effect

        # Mock shutil.rmtree to prevent cleanup
        monkeypatch.setattr("src.foam_agent_adapter.shutil.rmtree", MagicMock())

        executor = FoamAgentExecutor(work_dir=str(tmp_path))
        result = executor.execute(make_task())

        assert result.success is True
        assert result.is_mock is False
        assert result.execution_time_s > 0
        assert result.raw_output_path is not None

    def test_execute_airfoil_runs_direct_2d_mesh_path(self, tmp_path, monkeypatch):
        mock_container = MagicMock()
        mock_container.status = "running"
        mock_client = MagicMock()
        mock_client.containers.get.return_value = mock_container
        mock_docker = MagicMock()
        mock_docker.from_env.return_value = mock_client

        monkeypatch.setattr("src.foam_agent_adapter.docker", mock_docker)
        monkeypatch.setattr("src.foam_agent_adapter._DOCKER_AVAILABLE", True)
        monkeypatch.setattr("src.foam_agent_adapter.shutil.rmtree", MagicMock())

        commands = []

        def fake_docker_exec(self, command, working_dir, timeout):
            commands.append(command)
            return True, f"ok:{command}"

        monkeypatch.setattr(FoamAgentExecutor, "_docker_exec", fake_docker_exec)
        monkeypatch.setattr(FoamAgentExecutor, "_parse_solver_log", lambda *args, **kwargs: ({}, {}))
        monkeypatch.setattr(FoamAgentExecutor, "_copy_postprocess_fields", lambda *args, **kwargs: None)

        executor = FoamAgentExecutor(work_dir=str(tmp_path))
        result = executor.execute(make_airfoil_task())

        assert result.success is True
        assert commands[:2] == [
            "blockMesh",
            "simpleFoam",
        ]
        assert 'transformPoints "scale=(1 0 1)"' not in commands
        assert "extrudeMesh" not in commands
        assert any("postProcess -funcs" in cmd for cmd in commands)

    def test_execute_blockmesh_failure(self, tmp_path, monkeypatch):
        """blockMesh 失败时返回 failed result。"""
        mock_container = MagicMock()
        mock_container.status = "running"
        # blockMesh fails, icoFoam succeeds
        mock_container.exec_run.return_value = MagicMock(exit_code=1, output=b"blockMesh error")

        mock_client = MagicMock()
        mock_client.containers.get.return_value = mock_container

        mock_docker = MagicMock()
        mock_docker.from_env.return_value = mock_client

        monkeypatch.setattr("src.foam_agent_adapter.docker", mock_docker)
        monkeypatch.setattr("src.foam_agent_adapter._DOCKER_AVAILABLE", True)
        monkeypatch.setattr("src.foam_agent_adapter.shutil.rmtree", MagicMock())

        executor = FoamAgentExecutor(work_dir=str(tmp_path))
        result = executor.execute(make_task())

        assert result.success is False
        assert "blockMesh failed" in result.error_message

    def test_execute_solver_failure(self, tmp_path, monkeypatch):
        """simpleFoam 失败时返回 failed result。"""
        mock_container = MagicMock()
        mock_container.status = "running"

        def exec_run_side_effect(cmd, **kwargs):
            # Determine which command based on cmd content.
            #
            # SOLVER ROUTING UPDATE: the default make_task() (SIMPLE_GRID +
            # INTERNAL + Re=100) now routes through the lid-driven-cavity
            # detection path (`_is_lid_driven_cavity_case` → simpleFoam) per
            # foam_agent_adapter.py ~L530. The previous `SIMPLE_GRID + Re<2300
            # → icoFoam` fallback was deliberately narrowed in the Phase 8
            # sprint work to stop misrouting laminar cavity to pimpleFoam's
            # kinematic solver. Mocking `simpleFoam` for solver failure keeps
            # the test covering "solver non-zero exit bubbles up as failure".
            cmd_str = str(cmd) if not isinstance(cmd, str) else cmd
            if isinstance(cmd, list):
                cmd_str = " ".join(str(c) for c in cmd)
            if "blockMesh" in cmd_str and "source" in cmd_str:
                return MagicMock(exit_code=0)
            elif "simpleFoam" in cmd_str and "source" in cmd_str:
                return MagicMock(exit_code=1, output=b"solver error")
            else:
                return MagicMock(exit_code=0)

        mock_container.exec_run.side_effect = exec_run_side_effect

        mock_client = MagicMock()
        mock_client.containers.get.return_value = mock_container

        mock_docker = MagicMock()
        mock_docker.from_env.return_value = mock_client

        monkeypatch.setattr("src.foam_agent_adapter.docker", mock_docker)
        monkeypatch.setattr("src.foam_agent_adapter._DOCKER_AVAILABLE", True)
        monkeypatch.setattr("src.foam_agent_adapter.shutil.rmtree", MagicMock())

        executor = FoamAgentExecutor(work_dir=str(tmp_path))
        result = executor.execute(make_task())

        assert result.success is False
        assert "simpleFoam failed" in result.error_message

    def test_execute_mkdir_failure(self, tmp_path, monkeypatch):
        """case 目录创建失败时返回 failed result。"""
        mock_container = MagicMock()
        mock_container.status = "running"
        mock_container.exec_run.return_value = MagicMock(exit_code=0)

        mock_client = MagicMock()
        mock_client.containers.get.return_value = mock_container

        mock_docker = MagicMock()
        mock_docker.from_env.return_value = mock_client

        monkeypatch.setattr("src.foam_agent_adapter.docker", mock_docker)
        monkeypatch.setattr("src.foam_agent_adapter._DOCKER_AVAILABLE", True)
        monkeypatch.setattr("src.foam_agent_adapter.shutil.rmtree", MagicMock())

        # Mock Path.mkdir to raise an exception
        def mkdir_raise(*args, **kwargs):
            raise OSError("Cannot create directory")

        monkeypatch.setattr("pathlib.Path.mkdir", mkdir_raise)

        executor = FoamAgentExecutor(work_dir=str(tmp_path))
        result = executor.execute(make_task())

        assert result.success is False
        assert "Cannot create case directory" in result.error_message

    def test_copy_file_from_container_exception(self):
        """_copy_file_from_container 在异常时静默失败。"""
        mock_container = MagicMock()
        mock_container.get_archive.side_effect = Exception("Container error")

        # Should not raise, just pass silently
        FoamAgentExecutor._copy_file_from_container(
            mock_container, "/tmp/log.icoFoam", Path("/tmp/log.icoFoam")
        )
        # If we get here without exception, the test passes


class TestCylinderStrouhalExtractor:
    def test_extract_cylinder_strouhal_no_hardcode_in_canonical_band(self):
        """DEC-V61-041: the old code hardcoded strouhal_number=0.165 whenever
        Re∈[50,200] (canonical shedding band), bypassing the actual flow
        data. That was PASS-washing. New semantics: without case_dir (no
        forceCoeffs FO), no strouhal_number is emitted regardless of Re.
        DEC-V61-036 G1 then picks up MISSING_TARGET_QUANTITY."""
        task = TaskSpec(
            name="cylinder",
            geometry_type=GeometryType.BODY_IN_CHANNEL,
            flow_type=FlowType.EXTERNAL,
            steady_state=SteadyState.TRANSIENT,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=100.0,
        )

        result = FoamAgentExecutor._extract_cylinder_strouhal(
            [0.05, -0.05, 0.0, 0.0],
            [0.0, 0.0, 0.05, -0.05],
            [0.10, -0.10, 0.00, 0.05],
            task,
            {},
        )

        assert "strouhal_number" not in result
        assert "strouhal_canonical_band_shortcut_fired" not in result

    def test_extract_cylinder_strouhal_no_shortcut_flag_outside_band(self):
        task = TaskSpec(
            name="cylinder",
            geometry_type=GeometryType.BODY_IN_CHANNEL,
            flow_type=FlowType.EXTERNAL,
            steady_state=SteadyState.TRANSIENT,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=400.0,
        )

        result = FoamAgentExecutor._extract_cylinder_strouhal(
            [0.05, -0.05, 0.0, 0.0],
            [0.0, 0.0, 0.05, -0.05],
            [0.10, -0.10, 0.00, 0.05],
            task,
            {},
        )

        assert "strouhal_number" not in result
        assert "strouhal_canonical_band_shortcut_fired" not in result


class TestCylinderGeneratorBatchB1:
    """DEC-V61-053 Batch B1 adapter changes — laminar threading, domain grow,
    runtime sampleDict, forceCoeffs axis convention. Each test is a narrow
    assertion so Codex round-1 review can pinpoint regressions by name.
    """

    def _generate(self, turbulence_model: str) -> Path:
        import tempfile
        from pathlib import Path as _P
        tmp = _P(tempfile.mkdtemp(prefix=f"cyl_b1_{turbulence_model}_"))
        task = TaskSpec(
            name="circular_cylinder_wake",
            geometry_type=GeometryType.BODY_IN_CHANNEL,
            flow_type=FlowType.EXTERNAL,
            steady_state=SteadyState.TRANSIENT,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=100.0,
        )
        ex = FoamAgentExecutor.__new__(FoamAgentExecutor)
        ex._generate_circular_cylinder_wake(tmp, task, turbulence_model=turbulence_model)
        return tmp

    def test_laminar_turbulenceProperties_uses_laminar_simulationType(self):
        """Whitelist `turbulence_model: laminar` path — constant/turbulenceProperties
        must declare `simulationType laminar;` (no RAS block)."""
        case_dir = self._generate("laminar")
        tp = (case_dir / "constant" / "turbulenceProperties").read_text()
        assert "simulationType  laminar" in tp
        assert "RASModel" not in tp

    def test_laminar_skips_k_omega_nut_initial_fields(self):
        """Laminar solver stack doesn't register k/omega/nut — writing them
        causes 'Field not found' / RAS-model-not-registered errors at startup.
        Contract: these 3 files MUST NOT exist for laminar."""
        case_dir = self._generate("laminar")
        assert not (case_dir / "0" / "k").exists()
        assert not (case_dir / "0" / "omega").exists()
        assert not (case_dir / "0" / "nut").exists()

    def test_kOmegaSST_writes_k_omega_nut_initial_fields(self):
        """Dual of above — kOmegaSST path MUST write all three."""
        case_dir = self._generate("kOmegaSST")
        assert (case_dir / "0" / "k").exists()
        assert (case_dir / "0" / "omega").exists()
        assert (case_dir / "0" / "nut").exists()

    def test_domain_grown_to_williamson_unconfined_geometry(self):
        """Batch B1 decision (b): blockage 20% → ~8% via L_inlet 2D→10D,
        L_outlet 8D→20D, H 2.5D→6D. blockMeshDict vertices encode these."""
        case_dir = self._generate("laminar")
        bm = (case_dir / "system" / "blockMeshDict").read_text()
        # x_min = -L_inlet = -10*D = -10*0.1 = -1.0 m
        assert "-1.000000" in bm, "x_min should be -1.0 m (10D upstream)"
        # x_max = L_outlet = 20*D = 2.0 m
        assert "2.000000" in bm, "x_max should be 2.0 m (20D downstream)"
        # Block count 600x240 per Codex round-1 MED-2 (matches pre-B1 0.05D
        # resolution across the new larger domain).
        assert "(600 240 1)" in bm

    def test_forceCoeffs_axis_convention_explicit(self):
        """DEC-V61-053 Batch B1 hardening per intake risk_flag
        `forceCoeffs_axis_convention`: OpenFOAM defaults for forceCoeffs
        dragDir/liftDir/pitchAxis differ across versions; any generator edit
        that accidentally drops the explicit triple would silently invert
        Cl/Cd. Assert the exact strings are present."""
        case_dir = self._generate("laminar")
        cd = (case_dir / "system" / "controlDict").read_text()
        assert "dragDir         (1 0 0);" in cd
        assert "liftDir         (0 1 0);" in cd
        assert "pitchAxis       (0 0 1);" in cd
        # And the force-coefficients FO is actually enabled
        assert "forceCoeffs1" in cd
        assert 'patches         (cylinder);' in cd

    def test_cylinderCenterline_runtime_sampling_has_4_gold_stations(self):
        """Batch B1b new function object: wakeCenterline sampleSet with 4
        points at x/D ∈ {1,2,3,5} (D=0.1 → x ∈ {0.1, 0.2, 0.3, 0.5}). These
        are the u_mean_centerline gold stations from Williamson 1996."""
        case_dir = self._generate("laminar")
        cd = (case_dir / "system" / "controlDict").read_text()
        assert "cylinderCenterline" in cd
        assert "wakeCenterline" in cd
        for expected_point in ("(0.1 0 0)", "(0.2 0 0)", "(0.3 0 0)", "(0.5 0 0)"):
            assert expected_point in cd, f"Missing centerline probe point {expected_point}"
        # Fields must include U (velocity is what we're sampling)
        assert "fields          (U)" in cd
        # DEC-V61-053 live-run attempt 6 fix: executeControl + executeInterval
        # MUST be present. Without them, OF10 registers the FO and parses the
        # set description but sampling never runs (no Writing in log, no files
        # on disk). Silent failure mode that cost attempt 6 a u_centerline
        # gate — guard with an assertion.
        assert "executeControl  timeStep" in cd
        assert "executeInterval 20" in cd


# ---------------------------------------------------------------------------
# P-B C2: parameter plumbing pre-run assertion
# ---------------------------------------------------------------------------

def _make_nc_spec(
    Ra: float,
    aspect_ratio: float,
    name: Optional[str] = None,
    *,
    include_aspect_ratio_in_bc: bool = True,
) -> TaskSpec:
    """Construct a natural-convection TaskSpec for adapter tests.

    DEC-V61-057 Batch A.1: parameterized `name` so tests can exercise the
    case-id-aware AR fallback path (DHC at Ra=1e6 → AR=1.0; RBC at Ra=1e6
    → AR=2.0). When `include_aspect_ratio_in_bc` is False, simulates a
    whitelist-driven path where AR is NOT in boundary_conditions but must
    be resolved from whitelist parameters or case-id default.
    """
    bc: Dict[str, float] = {"Pr": 0.71}
    if include_aspect_ratio_in_bc:
        bc["aspect_ratio"] = aspect_ratio
    return TaskSpec(
        name=name if name is not None else f"nc-Ra{Ra:g}",
        geometry_type=GeometryType.NATURAL_CONVECTION_CAVITY,
        flow_type=FlowType.NATURAL_CONVECTION,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
        Ra=Ra,
        boundary_conditions=bc,
    )


class TestParameterPlumbingParsers:
    """Regex helpers must tolerate both OpenFOAM dict forms we emit."""

    def test_parse_scalar_with_dimensions(self):
        text = "nu              [0 2 -1 0 0 0 0] 1.234e-05;\n"
        assert _parse_dict_scalar(text, "nu") == pytest.approx(1.234e-5)

    def test_parse_scalar_without_dimensions(self):
        text = "    Pr              0.71;\n    Cp   1005.0;\n"
        assert _parse_dict_scalar(text, "Pr") == pytest.approx(0.71)
        assert _parse_dict_scalar(text, "Cp") == pytest.approx(1005.0)

    def test_parse_scalar_missing_key_returns_none(self):
        text = "Pr 0.71;\n"
        assert _parse_dict_scalar(text, "beta") is None

    def test_parse_g_vector_magnitude(self):
        text = "value           (0 -9.81 0);\n"
        assert _parse_g_magnitude(text) == pytest.approx(9.81)

    def test_parse_g_vector_missing_returns_none(self):
        assert _parse_g_magnitude("no vector here") is None


class TestBuoyantCasePlumbingVerification:
    """Natural convection cavity: Ra must survive the write pipeline intact."""

    def test_rayleigh_benard_ra_1e6_round_trip_passes(self):
        spec = _make_nc_spec(Ra=1e6, aspect_ratio=2.0, name="rayleigh_benard_convection")
        with tempfile.TemporaryDirectory() as tmp:
            case_dir = Path(tmp) / "case"
            # Does not raise — verifier is called internally on success.
            FoamAgentExecutor()._generate_natural_convection_cavity(case_dir, spec)
            assert (case_dir / "constant" / "physicalProperties").exists()
            assert (case_dir / "constant" / "g").exists()

    def test_dhc_ra_1e10_round_trip_passes(self):
        spec = _make_nc_spec(Ra=1e10, aspect_ratio=1.0, name="differential_heated_cavity")
        with tempfile.TemporaryDirectory() as tmp:
            case_dir = Path(tmp) / "case"
            FoamAgentExecutor()._generate_natural_convection_cavity(case_dir, spec)

    def test_dhc_ra_1e6_round_trip_passes(self):
        """DEC-V61-057 Batch A.1: DHC at Ra=1e6 (de Vahl Davis 1983) is the canonical
        benchmark — square cavity AR=1.0, NOT the rayleigh_benard 2:1-rectangle branch."""
        spec = _make_nc_spec(Ra=1e6, aspect_ratio=1.0, name="differential_heated_cavity")
        with tempfile.TemporaryDirectory() as tmp:
            case_dir = Path(tmp) / "case"
            FoamAgentExecutor()._generate_natural_convection_cavity(case_dir, spec)
            assert (case_dir / "constant" / "physicalProperties").exists()
            blockmesh = (case_dir / "system" / "blockMeshDict").read_text()
            # Square cavity: x-domain and y-domain both = 1.0L, so vertices
            # (1 0 0) and (0 1 0) should both appear (NOT 2.0 from RBC branch).
            assert "(1 0 0)" in blockmesh or "(1.0 0 0)" in blockmesh, (
                f"DHC AR=1.0 should yield x=1 vertex, got blockMesh={blockmesh[:300]}"
            )

    def test_dhc_ra_1e6_dispatch_falls_back_to_case_id_when_bc_lacks_ar(self):
        """DEC-V61-057 Batch A.1 (Codex F1-HIGH): when boundary_conditions does NOT
        carry aspect_ratio (e.g. whitelist-driven path), the adapter must consult
        whitelist parameters or fall back to case-id-aware default — NOT to the
        Ra-threshold heuristic that previously sent Ra=1e6 → AR=2.0."""
        spec = _make_nc_spec(
            Ra=1e6, aspect_ratio=1.0, name="differential_heated_cavity",
            include_aspect_ratio_in_bc=False,
        )
        with tempfile.TemporaryDirectory() as tmp:
            case_dir = Path(tmp) / "case"
            FoamAgentExecutor()._generate_natural_convection_cavity(case_dir, spec)
            blockmesh = (case_dir / "system" / "blockMeshDict").read_text()
            # Without explicit BC AR, DHC must still dispatch AR=1.0 (whitelist parameter
            # OR case-id-aware fallback both lead here). If the regression hits, we'd see
            # x-domain=2.0 from the legacy Ra<1e9 → AR=2.0 heuristic.
            assert "(1 0 0)" in blockmesh or "(1.0 0 0)" in blockmesh, (
                f"DHC dispatch fell back to AR != 1.0 — Ra-heuristic regression. "
                f"blockMesh head: {blockmesh[:300]}"
            )

    def test_load_whitelist_parameter_dhc_aspect_ratio(self):
        """DEC-V61-057 Batch A.1: smoke-test the whitelist parameter loader against
        the live whitelist.yaml — DHC must report AR=1.0 (de Vahl Davis canonical)."""
        ar = _load_whitelist_parameter("differential_heated_cavity", "aspect_ratio")
        assert ar == 1.0, f"whitelist DHC aspect_ratio expected 1.0, got {ar}"

    def test_load_whitelist_parameter_missing_returns_none(self):
        ar = _load_whitelist_parameter("nonexistent_case_xyz", "aspect_ratio")
        assert ar is None

    def test_dhc_emits_laminar_turbulence_props(self):
        """DEC-V61-057 Batch A.2 (Codex F1-HIGH): whitelist declares laminar
        for DHC at Ra=1e6 (de Vahl Davis benchmark). Adapter must emit
        simulationType laminar, NOT RAS+kOmegaSST hard-write."""
        spec = _make_nc_spec(Ra=1e6, aspect_ratio=1.0, name="differential_heated_cavity")
        with tempfile.TemporaryDirectory() as tmp:
            case_dir = Path(tmp) / "case"
            FoamAgentExecutor()._generate_natural_convection_cavity(case_dir, spec)
            tp = (case_dir / "constant" / "turbulenceProperties").read_text()
            assert "simulationType  laminar" in tp, (
                f"DHC turbulenceProperties should be laminar, got:\n{tp}"
            )
            assert "kOmegaSST" not in tp, "DHC must not seed RAS kOmegaSST"

    def test_dhc_skips_turbulent_initial_fields(self):
        """DEC-V61-057 Batch A.2: laminar regime → no k/epsilon/omega/nut written."""
        spec = _make_nc_spec(Ra=1e6, aspect_ratio=1.0, name="differential_heated_cavity")
        with tempfile.TemporaryDirectory() as tmp:
            case_dir = Path(tmp) / "case"
            FoamAgentExecutor()._generate_natural_convection_cavity(case_dir, spec)
            for fname in ("k", "epsilon", "omega", "nut"):
                assert not (case_dir / "0" / fname).exists(), (
                    f"DHC laminar should not write 0/{fname}; got phantom turbulent field"
                )

    def test_dhc_ra_1e6_uses_graded_mesh(self):
        """DEC-V61-057 Batch A.3 (Codex F1-HIGH): DHC at Ra=1e6 needs BL grading.
        At Ra=1e6, δ_T/L ≈ 0.032; uniform 80 cells gives 2.56 BL cells, below
        the 5-cell minimum. Solution: 4:1 symmetric wall-packing → wall cell
        ≈ 0.006L → 5.3 BL cells. blockMeshDict must contain the graded
        simpleGrading expression, not the uniform '1'."""
        spec = _make_nc_spec(Ra=1e6, aspect_ratio=1.0, name="differential_heated_cavity")
        with tempfile.TemporaryDirectory() as tmp:
            case_dir = Path(tmp) / "case"
            FoamAgentExecutor()._generate_natural_convection_cavity(case_dir, spec)
            blockmesh = (case_dir / "system" / "blockMeshDict").read_text()
            # 4:1 symmetric wall-packing string for DHC at moderate Ra
            assert "((0.5 0.5 4) (0.5 0.5 0.25))" in blockmesh, (
                f"DHC Ra=1e6 should use 4:1 wall grading; got blockMesh:\n"
                f"{blockmesh[blockmesh.find('hex'):blockmesh.find('hex')+400]}"
            )

    def test_dhc_legacy_display_name_alias_resolves_correctly(self):
        """DEC-V61-057 Batch A.5 (Codex round-1 F1-HIGH): TaskSpecs created
        from Notion or other display-title pipelines carry the human-
        readable name (e.g. 'Differential Heated Cavity (Natural
        Convection)'), NOT the canonical case_id. Without alias
        normalization, the whitelist lookup misses, the substring fallback
        misses, and Ra=1e6 reverts to the legacy AR=2.0 + RAS heuristic.
        Stage A.5 normalizes through TASK_NAME_TO_CASE_ID — verify both
        AR=1.0 and simulationType=laminar materialize correctly."""
        spec = _make_nc_spec(
            Ra=1e6,
            aspect_ratio=1.0,  # ignored — see include_aspect_ratio_in_bc=False
            name="Differential Heated Cavity (Natural Convection)",  # legacy display title
            include_aspect_ratio_in_bc=False,
        )
        with tempfile.TemporaryDirectory() as tmp:
            case_dir = Path(tmp) / "case"
            FoamAgentExecutor()._generate_natural_convection_cavity(case_dir, spec)
            blockmesh = (case_dir / "system" / "blockMeshDict").read_text()
            tp = (case_dir / "constant" / "turbulenceProperties").read_text()
            # AR=1.0 means x-domain vertex (1 0 0), not (2 0 0) from RBC branch
            assert "(1 0 0)" in blockmesh or "(1.0 0 0)" in blockmesh, (
                "Legacy DHC display name should resolve to AR=1.0; got "
                f"blockMesh head:\n{blockmesh[:300]}"
            )
            assert "simulationType  laminar" in tp, (
                f"Legacy DHC display name should resolve to laminar (whitelist "
                f"says laminar); got turbulenceProperties:\n{tp}"
            )
            # And no phantom turbulent fields
            assert not (case_dir / "0" / "k").exists(), (
                "Laminar DHC should not write 0/k even when alias-resolved"
            )
            # And the BL-graded mesh dispatch also fires
            assert "((0.5 0.5 4) (0.5 0.5 0.25))" in blockmesh, (
                "DHC mesh dispatch should fire BL-grading for legacy alias too"
            )

    def test_dhc_extended_alias_with_ra_1e6_benchmark_suffix(self):
        """DEC-V61-057 Batch A.5: also exercise the extended alias 'Differential
        Heated Cavity (Natural Convection, Ra=10^6 benchmark)' which is the
        current whitelist `name` field — must resolve identically."""
        spec = _make_nc_spec(
            Ra=1e6, aspect_ratio=1.0,
            name="Differential Heated Cavity (Natural Convection, Ra=10^6 benchmark)",
            include_aspect_ratio_in_bc=False,
        )
        with tempfile.TemporaryDirectory() as tmp:
            case_dir = Path(tmp) / "case"
            FoamAgentExecutor()._generate_natural_convection_cavity(case_dir, spec)
            tp = (case_dir / "constant" / "turbulenceProperties").read_text()
            assert "simulationType  laminar" in tp

    def test_dhc_validation_artifact_lineage_invariant(self):
        """DEC-V61-057 Batch A.4 (Codex F2-HIGH): the three sources of truth
        for DHC reference Nu must agree byte-identically:
          1. knowledge/gold_standards/differential_heated_cavity.yaml ::
             observables[].ref_value
          2. reports/differential_heated_cavity/auto_verify_report.yaml ::
             gold_standard_comparison.observables[].ref_value (consumed by
             results_comparison.md.j2 template)
          3. The rendered cell in reports/differential_heated_cavity/report.md
             (downstream of #2 via Jinja).
        The pre-fix state showed (1)=8.8, (2)=30.0, (3)=30.0 — split-brain
        rendering. After A.4 regen all three must be 8.8."""
        import yaml as _yaml
        repo_root = Path(__file__).parent.parent

        gold = _yaml.safe_load(
            (repo_root / "knowledge/gold_standards/differential_heated_cavity.yaml").read_text(
                encoding="utf-8"
            )
        )
        gold_ref = gold["observables"][0]["ref_value"]
        assert gold["observables"][0]["name"] == "nusselt_number"

        avr = _yaml.safe_load(
            (repo_root / "reports/differential_heated_cavity/auto_verify_report.yaml").read_text(
                encoding="utf-8"
            )
        )
        avr_ref = avr["gold_standard_comparison"]["observables"][0]["ref_value"]
        assert avr["gold_standard_comparison"]["observables"][0]["name"] == "nusselt_number"

        report_md = (repo_root / "reports/differential_heated_cavity/report.md").read_text(
            encoding="utf-8"
        )

        assert gold_ref == avr_ref, (
            f"Invariant broken: gold YAML ref_value={gold_ref!r} but "
            f"auto_verify_report.yaml ref_value={avr_ref!r}. The "
            f"results_comparison.md.j2 template reads from "
            f"auto_verify_report — drift here breaks the rendered report."
        )
        # report.md cell text is "| `nusselt_number` | `8.8` | ..." — verify
        # the gold value appears as a literal cell.
        assert f"`{gold_ref}`" in report_md, (
            f"report.md does not contain reference cell `{gold_ref}` — "
            f"renderer regen drift. report.md head:\n{report_md[:500]}"
        )

    def test_rbc_keeps_uniform_mesh(self):
        """DEC-V61-057 Batch A.3: RBC convection rolls span full domain — no
        thin BL to resolve, uniform mesh is fine. The case-id-aware mesh
        dispatch must not over-grade RBC just because it's an NC cavity."""
        spec = _make_nc_spec(Ra=1e6, aspect_ratio=2.0, name="rayleigh_benard_convection")
        with tempfile.TemporaryDirectory() as tmp:
            case_dir = Path(tmp) / "case"
            FoamAgentExecutor()._generate_natural_convection_cavity(case_dir, spec)
            blockmesh = (case_dir / "system" / "blockMeshDict").read_text()
            # Uniform grading "1" still expected for RBC.
            # The simpleGrading line for uniform should look like "(1 1 1)"
            # in the hex block (not the multi-segment graded form).
            assert "(0.5 0.5 4)" not in blockmesh and "(0.5 0.5 6)" not in blockmesh, (
                "RBC should not use DHC's graded mesh"
            )

    def test_rbc_still_emits_ras_when_whitelist_silent(self):
        """DEC-V61-057 Batch A.2: rayleigh_benard_convection's whitelist also
        declares turbulence_model=laminar today, so we use a synthetic case
        name that has no whitelist entry to exercise the kOmegaSST fallback."""
        spec = _make_nc_spec(Ra=1e6, aspect_ratio=2.0, name="nc-test-fallback-ra1e6")
        with tempfile.TemporaryDirectory() as tmp:
            case_dir = Path(tmp) / "case"
            FoamAgentExecutor()._generate_natural_convection_cavity(case_dir, spec)
            tp = (case_dir / "constant" / "turbulenceProperties").read_text()
            assert "simulationType  RAS" in tp, (
                f"Synthetic case (no whitelist) must fall back to RAS, got:\n{tp}"
            )
            assert "kOmegaSST" in tp
            # Turbulent fields should be written for kOmegaSST regime.
            assert (case_dir / "0" / "k").exists()

    def test_tampered_gravity_raises_plumbing_error(self):
        """If someone bumps |g| post-write, Ra_effective drifts — detect it."""
        spec = _make_nc_spec(Ra=1e6, aspect_ratio=2.0)
        ex = FoamAgentExecutor()
        with tempfile.TemporaryDirectory() as tmp:
            case_dir = Path(tmp) / "case"
            ex._generate_natural_convection_cavity(case_dir, spec)
            g_path = case_dir / "constant" / "g"
            tampered = g_path.read_text().replace(
                "value           (0 -", "value           (0 -100"
            )
            g_path.write_text(tampered)
            with pytest.raises(ParameterPlumbingError) as ei:
                ex._verify_buoyant_case_plumbing(
                    case_dir=case_dir,
                    declared_Ra=1e6,
                    declared_Pr=0.71,
                    declared_L=2.0,
                    declared_dT=10.0,
                    declared_beta=1.0 / 300.0,
                )
            assert "Ra_effective" in str(ei.value)
            assert "declared Ra=1e+06" in str(ei.value)

    def test_tampered_pr_raises_plumbing_error(self):
        spec = _make_nc_spec(Ra=1e6, aspect_ratio=2.0)
        ex = FoamAgentExecutor()
        with tempfile.TemporaryDirectory() as tmp:
            case_dir = Path(tmp) / "case"
            ex._generate_natural_convection_cavity(case_dir, spec)
            props_path = case_dir / "constant" / "physicalProperties"
            props_path.write_text(
                props_path.read_text().replace("Pr              0.71", "Pr              7.1")
            )
            with pytest.raises(ParameterPlumbingError) as ei:
                ex._verify_buoyant_case_plumbing(
                    case_dir=case_dir,
                    declared_Ra=1e6,
                    declared_Pr=0.71,
                    declared_L=2.0,
                    declared_dT=10.0,
                    declared_beta=1.0 / 300.0,
                )
            # Either the Ra drift catches it first, or the Pr check does — both are valid
            assert "plumbing" in str(ei.value).lower()

    def test_missing_props_file_raises(self):
        ex = FoamAgentExecutor()
        with tempfile.TemporaryDirectory() as tmp:
            case_dir = Path(tmp) / "case"
            case_dir.mkdir(parents=True)
            (case_dir / "constant").mkdir()
            with pytest.raises(ParameterPlumbingError, match="physicalProperties missing"):
                ex._verify_buoyant_case_plumbing(
                    case_dir=case_dir,
                    declared_Ra=1e6, declared_Pr=0.71, declared_L=2.0,
                    declared_dT=10.0, declared_beta=1.0 / 300.0,
                )


class TestInternalChannelPlumbingVerification:
    """Plane channel flow: Re must survive the 1/nu round trip."""

    def _make_spec(self, Re: float) -> TaskSpec:
        return TaskSpec(
            name="plane-channel",
            geometry_type=GeometryType.BODY_IN_CHANNEL,
            flow_type=FlowType.INTERNAL,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=Re,
        )

    def test_re_5600_round_trip_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            case_dir = Path(tmp) / "case"
            FoamAgentExecutor()._generate_steady_internal_channel(case_dir, self._make_spec(5600))
            assert (case_dir / "constant" / "physicalProperties").exists()

    def test_tampered_nu_raises_plumbing_error(self):
        ex = FoamAgentExecutor()
        with tempfile.TemporaryDirectory() as tmp:
            case_dir = Path(tmp) / "case"
            ex._generate_steady_internal_channel(case_dir, self._make_spec(5600))
            props = case_dir / "constant" / "physicalProperties"
            # Rewrite nu to 1e-3 (→ Re_effective=1000, way off declared 5600)
            props.write_text(
                props.read_text().replace("0.00017857142857142857", "0.001")
            )
            with pytest.raises(ParameterPlumbingError, match="Re_effective"):
                ex._verify_internal_channel_plumbing(case_dir=case_dir, declared_Re=5600)

    def test_missing_props_raises(self):
        ex = FoamAgentExecutor()
        with tempfile.TemporaryDirectory() as tmp:
            case_dir = Path(tmp) / "case"
            case_dir.mkdir()
            (case_dir / "constant").mkdir()
            with pytest.raises(ParameterPlumbingError, match="physicalProperties missing"):
                ex._verify_internal_channel_plumbing(case_dir=case_dir, declared_Re=5600)

    def test_zero_nu_is_rejected(self):
        ex = FoamAgentExecutor()
        with tempfile.TemporaryDirectory() as tmp:
            case_dir = Path(tmp) / "case"
            (case_dir / "constant").mkdir(parents=True)
            (case_dir / "constant" / "physicalProperties").write_text(
                "transportModel Newtonian;\nnu [0 2 -1 0 0 0 0] 0.0;\n"
            )
            with pytest.raises(ParameterPlumbingError, match="non-positive nu"):
                ex._verify_internal_channel_plumbing(case_dir=case_dir, declared_Re=5600)


# ---------------------------------------------------------------------------
# C3 — Gold-anchored sampleDict helpers
# ---------------------------------------------------------------------------

class TestLoadGoldReferenceValues:
    """_load_gold_reference_values — whitelist lookup behavior."""

    def test_returns_values_for_lid_driven_cavity_id(self):
        """Real whitelist entry 'lid_driven_cavity' exposes the full Ghia 1982
        u_centerline reference table. The gold YAML was expanded from a
        5-point subsample to the full 17-point canonical table when the
        profile comparator (DEC-V61-029 / DEC-V61-045 attestor-first
        pipeline) started using per-y interpolation. Pin the current
        shape + canonical endpoints so any future corruption is caught."""
        values = _load_gold_reference_values("lid_driven_cavity")
        assert values is not None
        assert len(values) == 17
        y_values = [rv["y"] for rv in values if "y" in rv]
        # Endpoints and a few signature interior points from Ghia 1982 Table I.
        assert y_values[0] == 0.0
        assert y_values[-1] == 1.0
        assert 0.5 in y_values

    def test_returns_values_for_lid_driven_cavity_display_name(self):
        """Matching on case.name (not just case.id) also works."""
        values = _load_gold_reference_values("Lid-Driven Cavity")
        assert values is not None
        assert len(values) == 17

    def test_returns_none_for_unknown_name(self):
        """Synthetic test names (not in whitelist) → None, no error."""
        assert _load_gold_reference_values("test") is None
        assert _load_gold_reference_values("") is None

    def test_returns_none_when_whitelist_missing(self, tmp_path):
        """Nonexistent whitelist_path → None."""
        missing = tmp_path / "nope.yaml"
        assert _load_gold_reference_values("anything", whitelist_path=missing) is None

    def test_returns_none_for_malformed_whitelist(self, tmp_path):
        """Unparseable YAML → None, no raise."""
        bad = tmp_path / "bad.yaml"
        bad.write_text("cases: [this is : broken yaml :: [")
        assert _load_gold_reference_values("x", whitelist_path=bad) is None

    def test_returns_none_when_reference_values_empty(self, tmp_path):
        """Whitelist entry with empty reference_values → None."""
        wl = tmp_path / "wl.yaml"
        wl.write_text(
            "cases:\n"
            "  - id: empty_case\n"
            "    name: Empty\n"
            "    gold_standard:\n"
            "      reference_values: []\n"
        )
        assert _load_gold_reference_values("empty_case", whitelist_path=wl) is None


class TestLoadWhitelistTurbulenceModel:
    """_load_whitelist_turbulence_model — DEC-V61-053 Batch B1 whitelist lookup.

    Regression for the `self._db.get_execution_chain` bug that slipped B1a
    unit tests by calling _generate_circular_cylinder_wake directly with an
    explicit turbulence_model arg. The earlier code path dereferenced
    self._db which doesn't exist on FoamAgentExecutor, blowing up the
    live audit run with AttributeError on the first cylinder attempt.
    """

    def test_returns_laminar_for_cylinder(self):
        """Production whitelist has `turbulence_model: laminar` for the cylinder case."""
        assert _load_whitelist_turbulence_model("circular_cylinder_wake") == "laminar"

    def test_returns_none_when_whitelist_missing(self, tmp_path):
        missing = tmp_path / "nope.yaml"
        assert _load_whitelist_turbulence_model("x", whitelist_path=missing) is None

    def test_returns_none_when_case_not_in_whitelist(self, tmp_path):
        wl = tmp_path / "wl.yaml"
        wl.write_text("cases:\n  - id: other\n    turbulence_model: kEpsilon\n")
        assert _load_whitelist_turbulence_model("missing", whitelist_path=wl) is None

    def test_matches_by_id_or_name(self, tmp_path):
        wl = tmp_path / "wl.yaml"
        wl.write_text(
            "cases:\n"
            "  - id: my_case\n"
            "    name: My Case\n"
            "    turbulence_model: kOmegaSST\n"
        )
        assert _load_whitelist_turbulence_model("my_case", whitelist_path=wl) == "kOmegaSST"
        assert _load_whitelist_turbulence_model("My Case", whitelist_path=wl) == "kOmegaSST"

    def test_returns_none_when_turbulence_model_absent(self, tmp_path):
        wl = tmp_path / "wl.yaml"
        wl.write_text("cases:\n  - id: no_model\n    name: No Model\n")
        assert _load_whitelist_turbulence_model("no_model", whitelist_path=wl) is None

    def test_returns_none_when_turbulence_model_not_string(self, tmp_path):
        """Fail closed on non-string (e.g. accidental list/dict)."""
        wl = tmp_path / "wl.yaml"
        wl.write_text("cases:\n  - id: bad\n    turbulence_model: [laminar]\n")
        assert _load_whitelist_turbulence_model("bad", whitelist_path=wl) is None

    def test_returns_none_for_malformed_yaml(self, tmp_path):
        bad = tmp_path / "bad.yaml"
        bad.write_text("cases: [this is : broken yaml :: [")
        assert _load_whitelist_turbulence_model("x", whitelist_path=bad) is None


class TestEmitGoldAnchoredPointsSampleDict:
    """_emit_gold_anchored_points_sampledict — dict file emission."""

    def test_writes_system_sampledict_with_all_points(self, tmp_path):
        (tmp_path / "system").mkdir()
        points = [(0.5, 0.0625, 0.0), (0.5, 0.5, 0.0), (0.5, 1.0, 0.0)]
        _emit_gold_anchored_points_sampledict(
            tmp_path,
            set_name="uCenterline",
            physical_points=points,
            fields=["U"],
            axis="y",
        )
        text = (tmp_path / "system" / "sampleDict").read_text()
        assert "uCenterline" in text
        assert "type        points;" in text
        assert "axis        y" in text
        assert "fields          (U);" in text
        # All 3 points present
        assert "0.5 0.0625 0" in text
        assert "0.5 0.5 0" in text
        assert "0.5 1 0" in text

    def test_multiple_fields_emitted(self, tmp_path):
        (tmp_path / "system").mkdir()
        _emit_gold_anchored_points_sampledict(
            tmp_path,
            set_name="probes",
            physical_points=[(0.0, 0.0, 0.0)],
            fields=["U", "p", "T"],
        )
        text = (tmp_path / "system" / "sampleDict").read_text()
        assert "(U p T)" in text

    def test_raises_on_empty_points(self, tmp_path):
        (tmp_path / "system").mkdir()
        with pytest.raises(ValueError, match="must not be empty"):
            _emit_gold_anchored_points_sampledict(
                tmp_path, set_name="x", physical_points=[], fields=["U"]
            )

    def test_header_comment_included(self, tmp_path):
        (tmp_path / "system").mkdir()
        _emit_gold_anchored_points_sampledict(
            tmp_path,
            set_name="probes",
            physical_points=[(0.0, 0.0, 0.0)],
            fields=["U"],
            header_comment="LDC 5 gold y-coords (Ghia 1982)",
        )
        text = (tmp_path / "system" / "sampleDict").read_text()
        assert "Ghia 1982" in text


class TestLidDrivenCavityGoldAnchoredSampling:
    """End-to-end: _generate_lid_driven_cavity emits gold-anchored sampling
    when task_spec.name matches the whitelist LDC entry."""

    def _make_ldc_task(self, name):
        return TaskSpec(
            name=name,
            geometry_type=GeometryType.SIMPLE_GRID,
            flow_type=FlowType.INTERNAL,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=100,
        )

    def test_gold_anchored_path_emits_explicit_points_for_whitelist_id(self, tmp_path):
        """task_spec.name='lid_driven_cavity' → sampleDict has 5 y-coords from whitelist."""
        with patch("src.foam_agent_adapter.shutil.rmtree"):
            executor = FoamAgentExecutor()
            executor._generate_lid_driven_cavity(tmp_path, self._make_ldc_task("lid_driven_cavity"))

        text = (tmp_path / "system" / "sampleDict").read_text()
        assert "type        points;" in text
        # All 5 Ghia y-coords present
        for y in (0.0625, 0.125, 0.5, 0.75, 1.0):
            assert f"0.5 {y:g} 0" in text, f"missing y={y} in sampleDict"
        # Uniform fallback markers absent
        assert "type        uniform;" not in text
        assert "nPoints     16;" not in text
        # Existing test expectations hold (regression guard)
        assert "uCenterline" in text
        assert "axis        y" in text
        assert "(U)" in text

    def test_fallback_uniform_path_for_non_whitelist_name(self, tmp_path):
        """task_spec.name='test' (not in whitelist) → uniform 16-point fallback."""
        with patch("src.foam_agent_adapter.shutil.rmtree"):
            executor = FoamAgentExecutor()
            executor._generate_lid_driven_cavity(tmp_path, self._make_ldc_task("test"))

        text = (tmp_path / "system" / "sampleDict").read_text()
        assert "type        uniform;" in text
        assert "nPoints     16;" in text
        # Gold-anchored path absent
        assert "type        points;" not in text

    def test_whitelist_display_name_also_matches(self, tmp_path):
        """task_spec.name='Lid-Driven Cavity' (display name) also triggers gold-anchored path."""
        with patch("src.foam_agent_adapter.shutil.rmtree"):
            executor = FoamAgentExecutor()
            executor._generate_lid_driven_cavity(tmp_path, self._make_ldc_task("Lid-Driven Cavity"))

        text = (tmp_path / "system" / "sampleDict").read_text()
        assert "type        points;" in text
        assert "0.5 0.5 0" in text  # the y=0.5 gold coord


class TestNaca0012GoldAnchoredSampling:
    """C3b: _generate_airfoil_flow emits gold-anchored Cp sampling at the 3
    x/c coordinates in whitelist reference_values."""

    def test_gold_anchored_sampledict_emitted_for_whitelist_name(self, tmp_path):
        """make_airfoil_task has name='NACA 0012 Airfoil External Flow' which matches whitelist."""
        executor = FoamAgentExecutor()
        executor._generate_airfoil_flow(tmp_path, make_airfoil_task())

        sample_path = tmp_path / "system" / "sampleDict"
        assert sample_path.is_file()
        text = sample_path.read_text()
        # Gold-anchored path signals
        assert "type        points;" in text
        assert "airfoilCp" in text
        assert "fields          (p);" in text
        # 3 x/c coords from whitelist: 0.0, 0.3, 1.0 → at chord=1.0 → x=0, 0.3, 1
        # Upper surface z: 0 at LE, half-thickness(0.3) at mid, 0 at TE
        assert "(0 0 0)" in text                       # leading edge (x/c=0)
        half_thickness_03 = FoamAgentExecutor._naca0012_half_thickness(0.3)
        assert f"(0.3 0 {half_thickness_03:.12g})" in text  # upper surface at x/c=0.3
        assert "(1 0 0)" in text                       # trailing edge (x/c=1)

    def test_fallback_no_sampledict_for_non_whitelist_name(self, tmp_path):
        """Unknown airfoil task name → no sampleDict emitted (no fallback by design for C3b)."""
        off_whitelist_task = TaskSpec(
            name="synthetic_airfoil_probe",
            geometry_type=GeometryType.AIRFOIL,
            flow_type=FlowType.EXTERNAL,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=3000000,
            boundary_conditions={"angle_of_attack": 0.0, "chord_length": 1.0},
        )
        executor = FoamAgentExecutor()
        executor._generate_airfoil_flow(tmp_path, off_whitelist_task)
        # No prior sampleDict existed for airfoil case → off-whitelist produces none
        assert not (tmp_path / "system" / "sampleDict").exists()

    def test_sampledict_honors_chord_scaling(self, tmp_path):
        """When chord_length != 1.0, physical points scale accordingly."""
        task = TaskSpec(
            name="NACA 0012 Airfoil External Flow",  # whitelist match
            geometry_type=GeometryType.AIRFOIL,
            flow_type=FlowType.EXTERNAL,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=3000000,
            boundary_conditions={"angle_of_attack": 0.0, "chord_length": 2.0},
        )
        executor = FoamAgentExecutor()
        executor._generate_airfoil_flow(tmp_path, task)
        text = (tmp_path / "system" / "sampleDict").read_text()
        # x/c=0.3 at chord=2.0 → x=0.6, z=half_thickness*2
        half_thickness_03 = FoamAgentExecutor._naca0012_half_thickness(0.3)
        assert f"(0.6 0 {half_thickness_03 * 2.0:.12g})" in text
        # x/c=1.0 at chord=2.0 → x=2.0
        assert "(2 0 0)" in text

    def test_header_records_chord_and_uinf(self, tmp_path):
        """Header comment carries chord + U_inf for traceability."""
        executor = FoamAgentExecutor()
        executor._generate_airfoil_flow(tmp_path, make_airfoil_task())
        text = (tmp_path / "system" / "sampleDict").read_text()
        assert "NACA0012 upper surface" in text
        assert "chord=1" in text
        assert "U_inf=1" in text
        assert "gold x/c coords" in text


class TestImpingingJetGoldAnchoredSampling:
    """C3c: _generate_impinging_jet emits gold-anchored Nu sampling at the
    r/d coordinates in whitelist reference_values. Sampling infrastructure
    only — Nu derivation from (T, U) probes is a follow-up refactor (gold
    values themselves on HOLD per Gate Q-new Case 9)."""

    def _make_ij_task(self, name):
        return TaskSpec(
            name=name,
            geometry_type=GeometryType.IMPINGING_JET,
            flow_type=FlowType.EXTERNAL,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=10000,
        )

    def test_gold_anchored_sampledict_emitted_for_whitelist_id(self, tmp_path):
        """task_spec.name='impinging_jet' (whitelist id) triggers gold-anchored path."""
        with patch("src.foam_agent_adapter.shutil.rmtree"):
            executor = FoamAgentExecutor()
            executor._generate_impinging_jet(tmp_path, self._make_ij_task("impinging_jet"))

        sample_path = tmp_path / "system" / "sampleDict"
        assert sample_path.is_file()
        text = sample_path.read_text()
        assert "type        points;" in text
        assert "plateProbes" in text
        assert "fields          (T U);" in text
        # Whitelist has r/d=0 and r/d=1; D=0.05 → points at (0, 0, 0.001) and (0.05, 0, 0.001)
        assert "(0 0 0.001)" in text
        assert "(0.05 0 0.001)" in text

    def test_gold_anchored_sampledict_emitted_for_whitelist_display_name(self, tmp_path):
        """Display name 'Axisymmetric Impinging Jet (Re=10000)' also triggers."""
        with patch("src.foam_agent_adapter.shutil.rmtree"):
            executor = FoamAgentExecutor()
            executor._generate_impinging_jet(
                tmp_path, self._make_ij_task("Axisymmetric Impinging Jet (Re=10000)")
            )

        text = (tmp_path / "system" / "sampleDict").read_text()
        assert "plateProbes" in text
        assert "(0 0 0.001)" in text

    def test_fallback_no_sampledict_for_non_whitelist_name(self, tmp_path):
        """Unknown task name → no sampleDict (consistent with C3b airfoil behavior)."""
        with patch("src.foam_agent_adapter.shutil.rmtree"):
            executor = FoamAgentExecutor()
            executor._generate_impinging_jet(tmp_path, self._make_ij_task("synthetic_ij"))
        assert not (tmp_path / "system" / "sampleDict").exists()

    def test_header_records_physical_constants(self, tmp_path):
        """Header carries D, T_inlet, T_plate for downstream Nu derivation."""
        with patch("src.foam_agent_adapter.shutil.rmtree"):
            executor = FoamAgentExecutor()
            executor._generate_impinging_jet(tmp_path, self._make_ij_task("impinging_jet"))
        text = (tmp_path / "system" / "sampleDict").read_text()
        assert "D=0.05" in text
        assert "T_inlet=310" in text
        assert "T_plate=290" in text
        assert "Nu derivation" in text  # TODO marker for follow-up


# ---------------------------------------------------------------------------
# C3 result-harvest side: parse sampleDict output → comparator keys
# ---------------------------------------------------------------------------

class TestParseOpenFoamRawPointsOutput:
    """Module-level parser for OpenFOAM setFormat raw output."""

    def test_3d_coord_rows_with_vector_field(self):
        text = (
            "# x y z U_x U_y U_z\n"
            "0.5 0.0625 0 -0.037 0 0\n"
            "0.5 0.1250 0 -0.042 0 0\n"
            "0.5 0.5000 0 0.025 0 0\n"
        )
        out = _parse_openfoam_raw_points_output(text)
        assert len(out) == 3
        assert out[0] == ((0.5, 0.0625, 0.0), (-0.037, 0.0, 0.0))
        assert out[2][0] == (0.5, 0.5, 0.0)
        assert out[2][1][0] == 0.025

    def test_3d_coord_rows_with_scalar_field(self):
        text = (
            "0 0 0 290.0\n"
            "0.05 0 0 293.5\n"
        )
        out = _parse_openfoam_raw_points_output(text)
        assert len(out) == 2
        assert out[0] == ((0.0, 0.0, 0.0), (290.0,))
        assert out[1] == ((0.05, 0.0, 0.0), (293.5,))

    def test_distance_column_mode(self):
        """Some sets emit `distance value` pairs (no xyz)."""
        text = "0.0 1.2\n0.5 2.4\n1.0 3.6\n"
        out = _parse_openfoam_raw_points_output(text)
        assert len(out) == 3
        assert out[0] == ((0.0,), (1.2,))

    def test_comments_and_blanks_skipped(self):
        text = (
            "# header comment\n"
            "\n"
            "0.5 0.0625 0 -0.037 0 0\n"
            "  # another comment\n"
            "   \n"
            "0.5 0.1250 0 -0.042 0 0\n"
        )
        out = _parse_openfoam_raw_points_output(text)
        assert len(out) == 2

    def test_malformed_lines_skipped_not_raise(self):
        text = (
            "0.5 0.0625 0 -0.037 0 0\n"
            "this is garbage\n"
            "0.5 0.1250 0 -0.042 0 0\n"
        )
        out = _parse_openfoam_raw_points_output(text)
        assert len(out) == 2

    def test_empty_input_returns_empty(self):
        assert _parse_openfoam_raw_points_output("") == []
        assert _parse_openfoam_raw_points_output("# only comments\n") == []


class TestTryLoadSampleDictOutput:
    """Path discovery under postProcessing/sets/."""

    def _mk_raw_file(self, case_dir, time, set_name, field, text):
        """Helper: populate layout A postProcessing/sets/<time>/<set>_<field>.xy."""
        time_dir = case_dir / "postProcessing" / "sets" / str(time)
        time_dir.mkdir(parents=True, exist_ok=True)
        (time_dir / f"{set_name}_{field}.xy").write_text(text)

    def test_returns_none_when_no_postprocessing(self, tmp_path):
        assert _try_load_sampledict_output(tmp_path, "anything", "x") is None

    def test_picks_latest_time_dir(self, tmp_path):
        self._mk_raw_file(tmp_path, 100, "uC", "U", "0.5 0.1 0 -0.04 0 0\n")
        self._mk_raw_file(tmp_path, 200, "uC", "U", "0.5 0.1 0 -0.07 0 0\n")
        self._mk_raw_file(tmp_path, 150, "uC", "U", "0.5 0.1 0 -0.05 0 0\n")
        out = _try_load_sampledict_output(tmp_path, "uC", "U")
        assert out is not None
        # Latest (t=200) should be picked
        assert out[0][1][0] == -0.07

    def test_returns_none_for_unknown_set_name(self, tmp_path):
        self._mk_raw_file(tmp_path, 100, "uC", "U", "0.5 0.1 0 -0.04 0 0\n")
        assert _try_load_sampledict_output(tmp_path, "other", "U") is None

    def test_handles_empty_file_returns_none(self, tmp_path):
        self._mk_raw_file(tmp_path, 100, "uC", "U", "# header only\n")
        assert _try_load_sampledict_output(tmp_path, "uC", "U") is None


class TestPopulateLdcFromSampleDict:
    """LDC u_centerline overwrite from sampleDict."""

    def _mk_ldc_output(self, tmp_path, y_u_pairs, time=1000):
        d = tmp_path / "postProcessing" / "sets" / str(time)
        d.mkdir(parents=True, exist_ok=True)
        body = "\n".join(f"0.5 {y} 0 {u} 0 0" for y, u in y_u_pairs)
        (d / "uCenterline_U.xy").write_text(body + "\n")

    def test_overwrites_u_centerline_when_output_present(self, tmp_path):
        self._mk_ldc_output(
            tmp_path,
            [(0.0625, -0.03717), (0.125, -0.04192), (0.5, 0.02526),
             (0.75, 0.33304), (1.0, 1.0)],
        )
        task = TaskSpec(
            name="lid_driven_cavity",
            geometry_type=GeometryType.SIMPLE_GRID,
            flow_type=FlowType.INTERNAL,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=100,
        )
        out = FoamAgentExecutor._populate_ldc_centerline_from_sampledict(
            tmp_path, task, {"u_centerline": [99.0, 99.0]}  # stale legacy value
        )
        assert out["u_centerline"] == [-0.03717, -0.04192, 0.02526, 0.33304, 1.0]
        assert out["u_centerline_source"] == "sampleDict_direct"
        assert out["u_centerline_y"] == [0.0625, 0.125, 0.5, 0.75, 1.0]

    def test_noop_when_output_missing(self, tmp_path):
        original = {"u_centerline": [0.1, 0.2, 0.3]}
        out = FoamAgentExecutor._populate_ldc_centerline_from_sampledict(
            tmp_path, TaskSpec(name="x", geometry_type=GeometryType.SIMPLE_GRID,
                               flow_type=FlowType.INTERNAL,
                               steady_state=SteadyState.STEADY,
                               compressibility=Compressibility.INCOMPRESSIBLE),
            original,
        )
        assert out is original  # identity — no mutation when no sampleDict


class TestPopulateNacaCpFromSampleDict:
    """NACA Cp conversion from sampleDict `p` values."""

    def _mk_naca_output(self, tmp_path, x_p_pairs, time=2000):
        d = tmp_path / "postProcessing" / "sets" / str(time)
        d.mkdir(parents=True, exist_ok=True)
        # For NACA the z-coord is the airfoil half-thickness at x/c; use 0 for LE/TE
        body = "\n".join(f"{x} 0 0 {p}" for x, p in x_p_pairs)
        (d / "airfoilCp_p.xy").write_text(body + "\n")

    def test_overwrites_pressure_coefficient_with_cp_conversion(self, tmp_path):
        # With U_inf=1, rho=1, q_ref=0.5. So Cp = p / 0.5 = 2*p
        self._mk_naca_output(
            tmp_path,
            [(0.0, 0.5), (0.3, -0.25), (1.0, 0.1)],
        )
        task = TaskSpec(
            name="NACA 0012 Airfoil External Flow",
            geometry_type=GeometryType.AIRFOIL,
            flow_type=FlowType.EXTERNAL,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=3000000,
            boundary_conditions={"angle_of_attack": 0.0, "chord_length": 1.0},
        )
        out = FoamAgentExecutor._populate_naca_cp_from_sampledict(
            tmp_path, task, {}
        )
        # DEC-V61-044 round-1 FLAG closure: legacy sampleDict path now
        # emits parallel scalar+axis lists (not list[dict]) so the
        # comparator's numeric-vector path doesn't TypeError.
        assert out["pressure_coefficient_x"] == [0.0, 0.3, 1.0]
        # Cp = 2·p: 2·0.5=1.0, 2·-0.25=-0.5, 2·0.1=0.2
        assert out["pressure_coefficient"] == pytest.approx([1.0, -0.5, 0.2])
        assert out["pressure_coefficient_source"] == "sampleDict_direct"

    def test_chord_scaling_in_x_over_c(self, tmp_path):
        """When chord=2, x=0.6 in sampleDict → x/c=0.3."""
        self._mk_naca_output(tmp_path, [(0.6, -0.25)])
        task = TaskSpec(
            name="NACA 0012 Airfoil External Flow",
            geometry_type=GeometryType.AIRFOIL,
            flow_type=FlowType.EXTERNAL,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=3000000,
            boundary_conditions={"chord_length": 2.0},
        )
        out = FoamAgentExecutor._populate_naca_cp_from_sampledict(
            tmp_path, task, {}
        )
        assert out["pressure_coefficient_x"][0] == pytest.approx(0.3)


class TestPopulateIjNusseltFromSampleDict:
    """Impinging Jet Nu derivation from wall-adjacent T probes."""

    def _mk_ij_output(self, tmp_path, x_T_pairs, time=1000):
        d = tmp_path / "postProcessing" / "sets" / str(time)
        d.mkdir(parents=True, exist_ok=True)
        body = "\n".join(f"{x} 0 0.001 {T}" for x, T in x_T_pairs)
        (d / "plateProbes_T.xy").write_text(body + "\n")

    def test_stagnation_nusselt_computed_from_smallest_r(self, tmp_path):
        # T_plate=290, T_inlet=310, ΔT_ref=20, D=0.05, Δz=0.001
        # Probe at r=0 with T=300 → Nu = |300-290|·0.05 / (0.001·20) = 10·2.5 = 25
        self._mk_ij_output(tmp_path, [(0.0, 300.0), (0.05, 295.0)])
        task = TaskSpec(
            name="impinging_jet",
            geometry_type=GeometryType.IMPINGING_JET,
            flow_type=FlowType.EXTERNAL,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=10000,
        )
        out = FoamAgentExecutor._populate_ij_nusselt_from_sampledict(
            tmp_path, task, {}
        )
        assert out["nusselt_number"] == pytest.approx(25.0)
        # Profile: [25, |295-290|·2.5 = 12.5]
        assert out["nusselt_number_profile"][0] == pytest.approx(25.0)
        assert out["nusselt_number_profile"][1] == pytest.approx(12.5)
        assert out["nusselt_number_source"] == "sampleDict_direct"

    def test_nu_runaway_surfaces_unphysical_magnitude_flag(self, tmp_path):
        """DEC-V61-042 round-1 FLAG 3: previously the sampleDict path
        silently clamped runaway Nu to 500 — hiding solver divergence
        behind a benign-looking value. Now it returns the raw Nu and
        surfaces `nusselt_number_unphysical_magnitude=True` so the
        downstream comparator/UI can treat it honestly."""
        # T_probe=1290K vs T_plate=290K, ΔT=20K, D=0.05, Δz=0.001
        # → Nu = |1290−290|·0.05 / (0.001·20) = 2500
        self._mk_ij_output(tmp_path, [(0.0, 1290.0)])
        task = TaskSpec(
            name="impinging_jet",
            geometry_type=GeometryType.IMPINGING_JET,
            flow_type=FlowType.EXTERNAL,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
        )
        out = FoamAgentExecutor._populate_ij_nusselt_from_sampledict(
            tmp_path, task, {}
        )
        assert out["nusselt_number"] == pytest.approx(2500.0)
        assert out.get("nusselt_number_unphysical_magnitude") is True

    def test_noop_when_output_missing(self, tmp_path):
        task = TaskSpec(
            name="impinging_jet",
            geometry_type=GeometryType.IMPINGING_JET,
            flow_type=FlowType.EXTERNAL,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
        )
        original = {"nusselt_number": 15.0}
        out = FoamAgentExecutor._populate_ij_nusselt_from_sampledict(
            tmp_path, task, original
        )
        assert out["nusselt_number"] == 15.0  # untouched


# ============================================================================
# DEC-V61-058 Stage B2: TestNACA0012MultiDim
# ============================================================================
# Tests for src/airfoil_extractors.py + Stage B1 adapter α-routing changes.
# Test class is EXCLUSIVE per Track B SESSION 2 mandate (no overlap with
# parallel SESSION 1 DHC / SESSION 3 plane_channel work).

from src.airfoil_extractors import (
    AirfoilExtractorError,
    CoeffsResult,
    LiftSlopeResult,
    YPlusResult,
    assert_sign_convention,
    compute_cl_cd,
    compute_lift_slope,
    compute_y_plus_max,
)


def _write_synthetic_coefficient_dat(
    path: Path, t_cl_cd: list, *, with_header: bool = True
) -> None:
    """Write a synthetic forceCoeffs coefficient.dat for unit tests.

    Mirrors OpenFOAM 10 layout: ``# Time  Cm  Cd  Cl  Cd(f) Cd(r) Cl(f) Cl(r)``
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list = []
    if with_header:
        lines.append("# Time   Cm           Cd           Cl           Cd(f)        Cd(r)        Cl(f)        Cl(r)")
    for t, cl, cd in t_cl_cd:
        lines.append(
            f"{t:.6f}    0.0000e+00    {cd:.6e}   {cl:.6e}   "
            f"{cd*0.5:.6e}   {cd*0.5:.6e}   {cl*0.5:.6e}   {cl*0.5:.6e}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_synthetic_yplus_dat(
    path: Path, rows: list, *, with_header: bool = True
) -> None:
    """Write a synthetic yPlus.dat. rows = [(t, patch, ymin, ymax, yavg), ...]."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list = []
    if with_header:
        lines.append("# Time   patch    min      max      average")
    for t, patch, ymin, ymax, yavg in rows:
        lines.append(f"{t:.6f}    {patch}    {ymin:.6e}    {ymax:.6e}    {yavg:.6e}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class TestNACA0012MultiDim:
    """DEC-V61-058 Stage B2 — multi-α extractor + adapter integration tests."""

    # ------------------------------------------------------------------
    # compute_cl_cd: forceCoeffs final-time row extraction
    # ------------------------------------------------------------------

    def test_compute_cl_cd_alpha_eight_returns_final_row(self, tmp_path):
        # Synthetic 200-step run at α=8°: Cl ramps to 0.815, Cd to 0.0095
        coeff_path = tmp_path / "postProcessing" / "forceCoeffs1" / "0" / "coefficient.dat"
        rows = [(float(i), 0.005 + 0.815 * (i / 200.0), 0.005 + 0.0095 * (i / 200.0))
                for i in range(1, 201)]
        _write_synthetic_coefficient_dat(coeff_path, rows)
        result = compute_cl_cd(tmp_path, alpha_deg=8.0)
        assert isinstance(result, CoeffsResult)
        assert result.alpha_deg == 8.0
        assert result.Cl == pytest.approx(0.820, rel=0.01)  # 0.005 + 0.815·(200/200)
        assert result.Cd == pytest.approx(0.0145, rel=0.05)  # 0.005 + 0.0095·1
        assert result.n_samples == 200
        assert result.final_time == 200.0

    def test_compute_cl_cd_missing_dir_raises(self, tmp_path):
        with pytest.raises(AirfoilExtractorError, match="forceCoeffs FO output dir"):
            compute_cl_cd(tmp_path, alpha_deg=0.0)

    def test_compute_cl_cd_zero_rows_raises(self, tmp_path):
        coeff_path = tmp_path / "postProcessing" / "forceCoeffs1" / "0" / "coefficient.dat"
        coeff_path.parent.mkdir(parents=True, exist_ok=True)
        coeff_path.write_text("# Time   Cm   Cd   Cl\n", encoding="utf-8")  # header only
        with pytest.raises(AirfoilExtractorError, match="parse failed|zero rows"):
            compute_cl_cd(tmp_path, alpha_deg=0.0)

    def test_compute_cl_cd_drift_pct_zero_when_few_samples(self, tmp_path):
        """Drift metric returns 0 when fewer than 100 samples (insufficient signal)."""
        coeff_path = tmp_path / "postProcessing" / "forceCoeffs1" / "0" / "coefficient.dat"
        rows = [(float(i), 0.815, 0.008) for i in range(1, 51)]  # 50 samples
        _write_synthetic_coefficient_dat(coeff_path, rows)
        result = compute_cl_cd(tmp_path, alpha_deg=8.0)
        assert result.cl_drift_pct_last_100 == 0.0
        assert result.cd_drift_pct_last_100 == 0.0

    # ------------------------------------------------------------------
    # compute_lift_slope: 3-point linear fit + linearity check
    # ------------------------------------------------------------------

    def test_lift_slope_canonical_ladson_anchors_recovers_gold_slope(self):
        """Gold anchors (Ladson 1988 Tab.1 Re=3e6) → slope ≈ 0.105/deg."""
        points = [(0.0, 0.0), (4.0, 0.434), (8.0, 0.815)]
        result = compute_lift_slope(points)
        # Least-squares slope through these 3 points
        assert result.slope_per_deg == pytest.approx(0.1031, abs=0.005)
        assert result.intercept == pytest.approx(0.005, abs=0.01)
        assert result.linearity_ok is True
        assert result.linearity_residual < 0.05
        assert result.n_points == 3

    def test_lift_slope_nonlinear_points_flags_linearity_violation(self):
        """Strongly curved Cl(α) (e.g. stall onset before α=8°) → linearity_ok=False."""
        # Cl(0°)=0, Cl(4°)=0.5, Cl(8°)=0.6 — clearly nonlinear (recovery slows)
        points = [(0.0, 0.0), (4.0, 0.5), (8.0, 0.6)]
        result = compute_lift_slope(points)
        # midpoint = 0.3; |0.5 - 0.3| / |0.6| = 0.333 > 0.05
        assert result.linearity_ok is False
        assert result.linearity_residual > 0.05

    def test_lift_slope_two_points_skips_linearity_check(self):
        """With only 2 points, slope is computable but linearity check is N/A."""
        points = [(0.0, 0.0), (8.0, 0.815)]
        result = compute_lift_slope(points)
        assert result.slope_per_deg == pytest.approx(0.815 / 8.0, abs=0.001)
        assert result.linearity_ok is True  # default true when α∈{0,4,8} not all present
        assert result.linearity_residual == 0.0

    def test_lift_slope_one_point_raises(self):
        with pytest.raises(AirfoilExtractorError, match="≥2 points"):
            compute_lift_slope([(0.0, 0.0)])

    def test_lift_slope_degenerate_all_same_alpha_raises(self):
        with pytest.raises(AirfoilExtractorError, match="degenerate"):
            compute_lift_slope([(4.0, 0.4), (4.0, 0.5), (4.0, 0.6)])

    # ------------------------------------------------------------------
    # compute_y_plus_max: yPlus FO patch-row extraction
    # ------------------------------------------------------------------

    def test_yplus_max_in_band_returns_PASS(self, tmp_path):
        yplus_path = tmp_path / "postProcessing" / "yPlus" / "200" / "yPlus.dat"
        _write_synthetic_yplus_dat(yplus_path, [
            (200.0, "aerofoil", 11.5, 84.0, 47.0),
        ])
        result = compute_y_plus_max(tmp_path)
        assert result.y_plus_max == pytest.approx(84.0)
        assert result.advisory_status == "PASS"

    def test_yplus_max_above_500_returns_FLAG(self, tmp_path):
        yplus_path = tmp_path / "postProcessing" / "yPlus" / "200" / "yPlus.dat"
        _write_synthetic_yplus_dat(yplus_path, [
            (200.0, "aerofoil", 50.0, 750.0, 300.0),
        ])
        result = compute_y_plus_max(tmp_path)
        assert result.advisory_status == "FLAG"

    def test_yplus_max_above_1000_returns_BLOCK(self, tmp_path):
        yplus_path = tmp_path / "postProcessing" / "yPlus" / "200" / "yPlus.dat"
        _write_synthetic_yplus_dat(yplus_path, [
            (200.0, "aerofoil", 50.0, 1500.0, 500.0),
        ])
        result = compute_y_plus_max(tmp_path)
        assert result.advisory_status == "BLOCK"

    def test_yplus_missing_patch_raises(self, tmp_path):
        yplus_path = tmp_path / "postProcessing" / "yPlus" / "200" / "yPlus.dat"
        _write_synthetic_yplus_dat(yplus_path, [
            (200.0, "freestream", 0.5, 2.0, 1.0),  # wrong patch
        ])
        with pytest.raises(AirfoilExtractorError, match="no rows for patch"):
            compute_y_plus_max(tmp_path, patch_name="aerofoil")

    # ------------------------------------------------------------------
    # Sign-convention smoke + symmetry probe (intake §9 close gates)
    # ------------------------------------------------------------------

    def test_sign_convention_alpha_8_positive_cl_passes(self):
        result = CoeffsResult(
            alpha_deg=8.0, Cl=0.815, Cd=0.0145, final_time=200.0, n_samples=200
        )
        assert_sign_convention(result)  # no raise

    def test_sign_convention_alpha_8_negative_cl_raises(self):
        result = CoeffsResult(
            alpha_deg=8.0, Cl=-0.5, Cd=0.0145, final_time=200.0, n_samples=200
        )
        with pytest.raises(AirfoilExtractorError, match="sign-convention violation"):
            assert_sign_convention(result)

    def test_symmetry_probe_alpha_0_zero_cl_passes(self):
        """SANITY_CHECK: α=0° symmetric airfoil → |Cl| < 0.005."""
        result = CoeffsResult(
            alpha_deg=0.0, Cl=0.001, Cd=0.008, final_time=200.0, n_samples=200
        )
        assert_sign_convention(result)  # passes, |Cl|=0.001 < 0.005

    def test_symmetry_probe_alpha_0_large_cl_raises(self):
        """Asymmetric solve at α=0° (mesh asymmetry / numerical noise) → SANITY_CHECK fail."""
        result = CoeffsResult(
            alpha_deg=0.0, Cl=0.05, Cd=0.008, final_time=200.0, n_samples=200
        )
        with pytest.raises(AirfoilExtractorError, match="sanity_check violation"):
            assert_sign_convention(result)

    # ------------------------------------------------------------------
    # Adapter integration: B1 α-routing produces consistent forceCoeffs FO
    # ------------------------------------------------------------------

    def test_adapter_alpha_zero_emits_default_freestream(self, tmp_path):
        """α-routing default 0° produces (1, 0, 0) freestream."""
        task = TaskSpec(
            name="NACA 0012 Airfoil External Flow",
            geometry_type=GeometryType.AIRFOIL,
            flow_type=FlowType.EXTERNAL,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=3000000.0,
            boundary_conditions={"chord_length": 1.0},  # alpha_deg omitted → default 0
        )
        FoamAgentExecutor()._generate_airfoil_flow(tmp_path, task, "kOmegaSST")
        u_text = (tmp_path / "0" / "U").read_text()
        assert "uniform (1.000000e+00 0 0.000000e+00)" in u_text

    def test_adapter_alpha_eight_emits_rotated_freestream(self, tmp_path):
        """α=+8° produces freestream (cos 8°, 0, sin 8°) ≈ (0.990, 0, 0.139)."""
        task = TaskSpec(
            name="NACA 0012 Airfoil External Flow",
            geometry_type=GeometryType.AIRFOIL,
            flow_type=FlowType.EXTERNAL,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=3000000.0,
            boundary_conditions={"chord_length": 1.0, "alpha_deg": 8.0},
        )
        FoamAgentExecutor()._generate_airfoil_flow(tmp_path, task, "kOmegaSST")
        u_text = (tmp_path / "0" / "U").read_text()
        assert "9.902681e-01" in u_text  # cos 8°
        assert "1.391731e-01" in u_text  # sin 8°

    def test_adapter_angle_of_attack_alias_honored(self, tmp_path):
        """`angle_of_attack` alias (whitelist parameters→bc field) honored at adapter."""
        task = TaskSpec(
            name="NACA 0012 Airfoil External Flow",
            geometry_type=GeometryType.AIRFOIL,
            flow_type=FlowType.EXTERNAL,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=3000000.0,
            boundary_conditions={"chord_length": 1.0, "angle_of_attack": 4.0},
        )
        FoamAgentExecutor()._generate_airfoil_flow(tmp_path, task, "kOmegaSST")
        u_text = (tmp_path / "0" / "U").read_text()
        assert "9.975641e-01" in u_text  # cos 4°
        assert "6.975647e-02" in u_text  # sin 4°

    def test_adapter_force_coeffs_aref_is_chord_times_thin_span(self, tmp_path):
        """V61-041 trap: Aref must be 0.002 (chord × span), not 0.01 or 1.0."""
        task = TaskSpec(
            name="NACA 0012 Airfoil External Flow",
            geometry_type=GeometryType.AIRFOIL,
            flow_type=FlowType.EXTERNAL,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=3000000.0,
            boundary_conditions={"chord_length": 1.0, "alpha_deg": 0.0},
        )
        FoamAgentExecutor()._generate_airfoil_flow(tmp_path, task, "kOmegaSST")
        cd_text = (tmp_path / "system" / "controlDict").read_text()
        assert "Aref            2.000000e-03" in cd_text
        assert "lRef            1.000000e+00" in cd_text
        assert "rhoInf          1.0" in cd_text  # incompressible kinematic
        assert "patches         (aerofoil)" in cd_text

    def test_adapter_force_coeffs_lift_drag_dirs_are_alpha_aware(self, tmp_path):
        """liftDir/dragDir at α=8° match (-sin 8°, 0, cos 8°) / (cos 8°, 0, sin 8°)."""
        task = TaskSpec(
            name="NACA 0012 Airfoil External Flow",
            geometry_type=GeometryType.AIRFOIL,
            flow_type=FlowType.EXTERNAL,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=3000000.0,
            boundary_conditions={"chord_length": 1.0, "alpha_deg": 8.0},
        )
        FoamAgentExecutor()._generate_airfoil_flow(tmp_path, task, "kOmegaSST")
        cd_text = (tmp_path / "system" / "controlDict").read_text()
        assert "liftDir         (-1.391731e-01 0 9.902681e-01)" in cd_text
        assert "dragDir         (9.902681e-01 0 1.391731e-01)" in cd_text

    def test_adapter_yplus_fo_emitted(self, tmp_path):
        """B1.3: yPlus FO present in controlDict functions{} block."""
        task = TaskSpec(
            name="NACA 0012 Airfoil External Flow",
            geometry_type=GeometryType.AIRFOIL,
            flow_type=FlowType.EXTERNAL,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=3000000.0,
            boundary_conditions={"chord_length": 1.0, "alpha_deg": 0.0},
        )
        FoamAgentExecutor()._generate_airfoil_flow(tmp_path, task, "kOmegaSST")
        cd_text = (tmp_path / "system" / "controlDict").read_text()
        assert "yPlus" in cd_text
        assert 'libs            ("libfieldFunctionObjects.so")' in cd_text

    def test_adapter_plumbs_alpha_fields_into_boundary_conditions(self):
        """task_spec.boundary_conditions ends up with alpha_deg + U_inf_x + U_inf_z."""
        import tempfile
        from pathlib import Path as _Path
        task = TaskSpec(
            name="NACA 0012 Airfoil External Flow",
            geometry_type=GeometryType.AIRFOIL,
            flow_type=FlowType.EXTERNAL,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
            Re=3000000.0,
            boundary_conditions={"chord_length": 1.0, "alpha_deg": 4.0},
        )
        with tempfile.TemporaryDirectory() as td:
            FoamAgentExecutor()._generate_airfoil_flow(_Path(td), task, "kOmegaSST")
        bc = task.boundary_conditions
        assert bc["alpha_deg"] == 4.0
        assert bc["U_inf_x"] == pytest.approx(0.997564, abs=1e-5)
        assert bc["U_inf_z"] == pytest.approx(0.069756, abs=1e-5)
        assert bc["U_inf"] == 1.0
        assert bc["rho"] == 1.0
        assert bc["p_inf"] == 0.0

    # ------------------------------------------------------------------
    # Gate-set sanity: Cl@α=0° EXCLUDED (Codex F1 + numerical_noise_snr)
    # ------------------------------------------------------------------

    def test_cl_at_alpha_zero_not_in_gate_set(self):
        """Per Codex F1 + intake §3 sanity_checks: Cl@α=0 is SANITY_CHECK only."""
        import yaml
        gold_yaml = yaml.safe_load(
            (Path(__file__).resolve().parents[1]
             / "knowledge" / "gold_standards" / "naca0012_airfoil.yaml").read_text()
        )
        observable_names = [obs["name"] for obs in gold_yaml["observables"]]
        assert "lift_coefficient_alpha_zero" not in observable_names, (
            "Cl@α=0° must NOT be in observables[] (HARD gate set); per Codex F1 + "
            "intake §3 it must live ONLY in sanity_checks[]."
        )
        # And it MUST be in sanity_checks[] with excluded_from_gate_set=true.
        sanity_names = [s["name"] for s in gold_yaml["sanity_checks"]]
        assert "lift_coefficient_alpha_zero" in sanity_names
        sc = next(s for s in gold_yaml["sanity_checks"]
                  if s["name"] == "lift_coefficient_alpha_zero")
        assert sc["excluded_from_gate_set"] is True
        assert sc["expected_value"] == 0.0
        assert sc["expected_band_absolute"] == 0.005
