"""tests/test_foam_agent_adapter.py — MockExecutor 和 FoamAgentExecutor 测试"""

import io
import tarfile
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock
from src.foam_agent_adapter import FoamAgentExecutor, MockExecutor
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

    def test_extract_cylinder_strouhal_uses_canonical_low_re_value_for_unreasonable_pressure(self):
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
        assert result["strouhal_number"] == pytest.approx(0.165)
        assert "p_rms_near_cylinder" not in result
        assert "pressure_coefficient_rms_near_cylinder" not in result

    def test_extract_cylinder_strouhal_records_reasonable_pressure_diagnostics(self):
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
        assert result["strouhal_number"] == pytest.approx(0.165)
        assert result["p_rms_near_cylinder"] == pytest.approx(0.073950997289)
        assert result["pressure_coefficient_rms_near_cylinder"] == pytest.approx(0.147901994577)

    def test_extract_nc_nusselt_uses_horizontal_wall_gradient_for_side_heated_cavity(self):
        task = TaskSpec(
            name="nc-cavity",
            geometry_type=GeometryType.NATURAL_CONVECTION_CAVITY,
            flow_type=FlowType.NATURAL_CONVECTION,
            steady_state=SteadyState.STEADY,
            compressibility=Compressibility.INCOMPRESSIBLE,
            boundary_conditions={"dT": 10.0, "L": 2.0, "aspect_ratio": 2.0},
        )
        cxs = [0.05, 0.15, 1.0, 1.85, 1.95, 0.05, 0.15, 1.0, 1.85, 1.95, 0.05, 0.15, 1.0, 1.85, 1.95]
        cys = [0.05, 0.05, 0.05, 0.05, 0.05, 0.50, 0.50, 0.50, 0.50, 0.50, 0.95, 0.95, 0.95, 0.95, 0.95]
        t_vals = [304.90, 299.60, 300.00, 295.35, 295.05, 305.00, 299.75, 300.01, 295.25, 295.00, 304.95, 299.65, 300.02, 295.30, 295.02]

        result = FoamAgentExecutor._extract_nc_nusselt(cxs, cys, t_vals, task, {})

        assert result["nusselt_number"] == pytest.approx(10.5)

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
            # Determine which command based on cmd content
            cmd_str = str(cmd) if not isinstance(cmd, str) else cmd
            if isinstance(cmd, list):
                cmd_str = " ".join(str(c) for c in cmd)
            if "blockMesh" in cmd_str and "source" in cmd_str:
                # blockMesh command - succeeds
                return MagicMock(exit_code=0)
            elif "icoFoam" in cmd_str and "source" in cmd_str:
                # icoFoam command - fails (SIMPLE_GRID Re<2300 routes here)
                return MagicMock(exit_code=1, output=b"solver error")
            else:
                # mkdir/chmod commands - succeed
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
        assert "icoFoam failed" in result.error_message

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
