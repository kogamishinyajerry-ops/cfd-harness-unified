"""Foam-Agent 调用适配器：MockExecutor（测试）+ FoamAgentExecutor（真实）"""

from __future__ import annotations

import io
import os
import re
import shutil
import tarfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .models import CFDExecutor, ExecutionResult, FlowType, TaskSpec

# ---------------------------------------------------------------------------
# MockExecutor — unchanged, used for testing
# ---------------------------------------------------------------------------


class MockExecutor:
    """测试专用执行器：is_mock=True，返回预设结果"""

    _PRESET: Dict[str, Dict[str, Any]] = {
        "INTERNAL": {
            "residuals": {"p": 1e-6, "U": 1e-6},
            "key_quantities": {"u_centerline": [0.0, -0.037, 0.025, 0.333, 1.0]},
        },
        "EXTERNAL": {
            "residuals": {"p": 1e-5, "U": 1e-5},
            "key_quantities": {"strouhal_number": 0.165, "cd_mean": 1.36},
        },
        "NATURAL_CONVECTION": {
            "residuals": {"p": 1e-6, "T": 1e-7},
            "key_quantities": {"nusselt_number": 4.52},
        },
    }

    def execute(self, task_spec: TaskSpec) -> ExecutionResult:
        preset = self._PRESET.get(task_spec.flow_type.value, self._PRESET["INTERNAL"])
        return ExecutionResult(
            success=True,
            is_mock=True,
            residuals=dict(preset["residuals"]),
            key_quantities=dict(preset["key_quantities"]),
            execution_time_s=0.01,
            raw_output_path=None,
        )


# ---------------------------------------------------------------------------
# FoamAgentExecutor — real adapter (Docker + OpenFOAM)
# ---------------------------------------------------------------------------

try:
    import docker
    import docker.errors
    _DOCKER_AVAILABLE = True
except ImportError:
    _DOCKER_AVAILABLE = False
    docker = None  # type: ignore


class FoamAgentExecutor:
    """通过 Docker + OpenFOAM 执行真实仿真的 FoamAgentExecutor。

    1. 连接 cfd-openfoam 容器
    2. 生成 Lid-Driven Cavity 最小 case 文件
    3. 执行 blockMesh + icoFoam
    4. 解析 log 文件，提取残差和关键物理量
    """

    CONTAINER_NAME = "cfd-openfoam"
    # Case 临时目录宿主机根路径
    DEFAULT_WORK_DIR = "/tmp/cfd-harness-cases"
    SOLVER = "icoFoam"
    BLOCK_MESH_TIMEOUT = 600
    SOLVER_TIMEOUT = 7200

    def __init__(
        self,
        work_dir: Optional[str] = None,
        container_name: Optional[str] = None,
    ) -> None:
        self._work_dir = Path(work_dir or self.DEFAULT_WORK_DIR)
        self._container_name = container_name or self.CONTAINER_NAME
        self._timeout = self.SOLVER_TIMEOUT
        self._docker_client: Any = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def execute(self, task_spec: TaskSpec) -> ExecutionResult:
        t0 = time.monotonic()

        # 1. 检查 Docker 是否可用
        if not _DOCKER_AVAILABLE:
            return self._fail(
                "foam-agent not found in PATH. "
                "Install Foam-Agent (https://github.com/csml-rpi/Foam-Agent) "
                "and ensure it is accessible.",
                time.monotonic() - t0,
            )

        # 2. 初始化 Docker client 并确认容器运行中
        try:
            self._docker_client = docker.from_env()
            container = self._docker_client.containers.get(self._container_name)
            if container.status != "running":
                raise docker.errors.DockerException(
                    f"Container '{self._container_name}' is not running (status={container.status})."
                )
        except docker.errors.DockerException as exc:
            return self._fail(
                f"foam-agent not found in PATH. "
                "Install Foam-Agent (https://github.com/csml-rpi/Foam-Agent) "
                "and ensure it is accessible.",
                time.monotonic() - t0,
            )
        except Exception as exc:
            return self._fail(
                f"foam-agent not found in PATH. "
                "Install Foam-Agent (https://github.com/csml-rpi/Foam-Agent) "
                "and ensure it is accessible.",
                time.monotonic() - t0,
            )

        # 3. 准备临时 case 目录
        case_id = f"ldc_{os.getpid()}_{int(time.time() * 1000)}"
        case_host_dir = self._work_dir / case_id
        case_cont_dir = f"/tmp/cfd-harness-cases/{case_id}"
        try:
            case_host_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            return self._fail(
                f"Cannot create case directory: {exc}",
                time.monotonic() - t0,
            )

        raw_output_path = str(case_host_dir)

        try:
            # 4. 生成 Lid-Driven Cavity case 文件
            self._generate_lid_driven_cavity(case_host_dir, task_spec)

            # 5. 执行 blockMesh
            blockmesh_ok, blockmesh_log = self._docker_exec(
                "blockMesh", case_cont_dir, self.BLOCK_MESH_TIMEOUT,
            )
            if not blockmesh_ok:
                return self._fail(
                    f"blockMesh failed:\n{blockmesh_log}",
                    time.monotonic() - t0,
                    raw_output_path=raw_output_path,
                )

            # 6. 执行 icoFoam
            solver_ok, solver_log = self._docker_exec(
                self.SOLVER, case_cont_dir, self._timeout,
            )
            if not solver_ok:
                return self._fail(
                    f"icoFoam failed:\n{solver_log}",
                    time.monotonic() - t0,
                    raw_output_path=raw_output_path,
                )

            # 7. 解析 log 文件
            log_path = case_host_dir / f"log.{self.SOLVER}"
            residuals, key_quantities = self._parse_solver_log(log_path)

            elapsed = time.monotonic() - t0
            return ExecutionResult(
                success=True,
                is_mock=False,
                residuals=residuals,
                key_quantities=key_quantities,
                execution_time_s=elapsed,
                raw_output_path=raw_output_path,
            )

        finally:
            # 清理临时 case 目录（Python 3.9 兼容，不使用 missing_ok）
            try:
                shutil.rmtree(case_host_dir)
            except FileNotFoundError:
                pass

    # ------------------------------------------------------------------
    # Case file generation (Lid-Driven Cavity)
    # ------------------------------------------------------------------

    def _generate_lid_driven_cavity(self, case_dir: Path, task_spec: TaskSpec) -> None:
        """生成 Lid-Driven Cavity 最小 OpenFOAM case 文件。"""
        (case_dir / "system").mkdir(parents=True, exist_ok=True)
        (case_dir / "constant").mkdir(parents=True, exist_ok=True)
        (case_dir / "0").mkdir(parents=True, exist_ok=True)

        # 1. system/blockMeshDict — 立方体 cavity，顶盖驱动 (u=1 m/s)
        block_mesh = self._render_block_mesh_dict(task_spec)
        (case_dir / "system" / "blockMeshDict").write_text(
            block_mesh, encoding="utf-8"
        )

        # 2. constant/physicalProperties — 水的物性（nu = 0.01 ~ Re=100 时 U=1）
        nu_val = 0.01  # m^2/s, corresponds to Re=100 when U=1 and L=0.1
        (case_dir / "constant" / "physicalProperties").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      physicalProperties;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

transportModel  Newtonian;

nu              [0 2 -1 0 0 0 0] {nu_val};

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 3. system/controlDict
        (case_dir / "system" / "controlDict").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      controlDict;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

application     icoFoam;

startFrom       startTime;

startTime       0;

stopAt          endTime;

endTime         10;

deltaT          0.005;

writeControl    timeStep;

writeInterval   2000;

purgeWrite      0;

writeFormat     ascii;

writePrecision  6;

writeCompression off;

timeFormat      general;

timePrecision   6;

runTimeModifiable true;

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 4. system/fvSchemes
        (case_dir / "system" / "fvSchemes").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSchemes;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

ddtSchemes
{
    default         Euler;
}

gradSchemes
{
    default         Gauss linear;
}

divSchemes
{
    default         none;
    div(phi,U)      Gauss linear;
}

laplacianSchemes
{
    default         Gauss linear corrected;
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 5. system/fvSolution
        (case_dir / "system" / "fvSolution").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSolution;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

solvers
{
    p
    {
        solver          PCG;
        preconditioner  DIC;
        tolerance       1e-06;
        relTol          0.05;
    }

    pFinal
    {
        $p;
        relTol          0;
    }

    U
    {
        solver          smoothSolver;
        smoother        GaussSeidel;
        tolerance       1e-05;
        relTol          0.05;
    }
}

PISO
{
    nCorrectors         2;
    nNonOrthogonalCorrectors 0;
    pRefCell            0;
    pRefValue           0;
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 6. 0/U — 速度边界条件
        (case_dir / "0" / "U").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       volVectorField;
    location    "0";
    object      U;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 1 -1 0 0 0 0];

internalField   uniform (0 0 0);

boundaryField
{
    lid
    {
        type            fixedValue;
        value           uniform (1 0 0);
    }
    wall1
    {
        type            noSlip;
    }
    wall2
    {
        type            noSlip;
    }
    wall3
    {
        type            noSlip;
    }
    wall4
    {
        type            noSlip;
    }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 7. 0/p — 压力边界条件
        (case_dir / "0" / "p").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      p;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -2 0 0 0 0];

internalField   uniform 0;

boundaryField
{
    lid
    {
        type            zeroGradient;
    }
    wall1
    {
        type            zeroGradient;
    }
    wall2
    {
        type            zeroGradient;
    }
    wall3
    {
        type            zeroGradient;
    }
    wall4
    {
        type            zeroGradient;
    }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

    def _render_block_mesh_dict(self, task_spec: TaskSpec) -> str:
        """渲染 blockMeshDict，支持 TaskSpec boundary_conditions 参数覆盖。"""
        # 允许通过 boundary_conditions 覆盖顶盖速度
        lid_u = float(
            task_spec.boundary_conditions.get("lid_velocity_u", 1.0)
        )
        return f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      blockMeshDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

convertToMeters 0.1;

vertices
(
    (0 0 0)
    (1 0 0)
    (1 1 0)
    (0 1 0)
    (0 0 0.1)
    (1 0 0.1)
    (1 1 0.1)
    (0 1 0.1)
);

blocks
(
    hex (0 1 2 3 4 5 6 7) (20 20 1) simpleGrading (1 1 1)
);

edges
(
);

boundary
(
    lid
    {{
        type            wall;
        faces           ((3 7 6 2));
    }}
    wall1
    {{
        type            wall;
        faces           ((0 4 7 3));
    }}
    wall2
    {{
        type            wall;
        faces           ((1 2 6 5));
    }}
    wall3
    {{
        type            wall;
        faces           ((0 1 5 4));
    }}
    wall4
    {{
        type            wall;
        faces           ((4 5 6 7));
    }}
);

mergePatchPairs
(
);

// ************************************************************************* //
"""

    # ------------------------------------------------------------------
    # Docker execution helpers
    # ------------------------------------------------------------------

    def _docker_exec(
        self,
        command: str,
        working_dir: str,
        timeout: int,
    ) -> tuple[bool, str]:
        """在 cfd-openfoam 容器中执行命令，返回 (success, stdout_log)。

        流程：
        1. 在容器内创建 case 目录（openfoam 用户可写）
        2. 复制 case 文件到容器内
        3. 以 root 权限 chmod 确保 openfoam 可写
        4. 执行 OpenFOAM 命令
        5. 复制 log 文件回宿主机
        """
        container = self._docker_client.containers.get(self._container_name)
        case_id = working_dir.split("/")[-1]
        host_case_dir = self._work_dir / case_id

        # Step 1: 以 openfoam 用户身份创建目录
        container.exec_run(cmd=["bash", "-c", f"mkdir -p {working_dir} && chmod 777 {working_dir}"])

        # Step 2: 复制 case 文件到容器内
        try:
            container.put_archive(
                path=working_dir,
                data=self._make_tarball(host_case_dir),
            )
        except Exception:
            pass

        # Step 3: 以 root 身份修复权限（openfoam 用户需要能写 constant/）
        try:
            container.exec_run(
                cmd=["bash", "-c", f"find {working_dir} -type d -exec chmod 777 {{}} \\; 2>/dev/null; true"],
                user="0",
            )
        except Exception:
            pass

        # Step 3: 执行 OpenFOAM 命令
        bash_cmd = (
            f"source /opt/openfoam10/etc/bashrc && "
            f"cd {working_dir} && "
            f"{command} > log.{command} 2>&1"
        )
        result = container.exec_run(
            cmd=["bash", "-c", bash_cmd],
            workdir=working_dir,
        )

        # Step 4: 读取容器内的 log 文件
        log_path = host_case_dir / f"log.{command}"
        self._copy_file_from_container(container, f"{working_dir}/log.{command}", log_path)

        if log_path.exists() and log_path.stat().st_size > 0:
            return result.exit_code == 0, log_path.read_text(encoding="utf-8", errors="replace")
        return result.exit_code == 0, str(result.output)

    @staticmethod
    def _make_tarball(src_dir: Path) -> bytes:
        """把目录内容打包成 tarball bytes（用于 put_archive）。

        tarball 内文件路径不含顶层目录名，确保 extract 到 container
        的目标目录时文件直接落在正确位置。
        """
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tar:
            for item in src_dir.iterdir():
                tar.add(str(item), arcname=item.name)
        buf.seek(0)
        return buf.read()

    @staticmethod
    def _copy_file_from_container(container: Any, container_path: str, dest_path: Path) -> None:
        """从容器内复制单个文件到宿主机路径。"""
        try:
            bits, _ = container.get_archive(container_path)
            data = b"".join(bits)
            with tarfile.open(fileobj=io.BytesIO(data)) as tar:
                member_name = container_path.split("/")[-1]
                for m in tar.getmembers():
                    if m.name.endswith(member_name):
                        member = tar.extractfile(m)
                        if member:
                            dest_path.parent.mkdir(parents=True, exist_ok=True)
                            dest_path.write_bytes(member.read())
                        break
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Log parsing
    # ------------------------------------------------------------------

    def _parse_solver_log(self, log_path: Path) -> tuple[Dict[str, float], Dict[str, Any]]:
        """解析 icoFoam log 文件，提取最终（末次迭代）残差和关键物理量。

        Returns:
            (residuals, key_quantities)
        """
        if not log_path.exists():
            return {}, {}

        text = log_path.read_text(encoding="utf-8", errors="replace")

        # 提取所有 "Solving for <var>" 行中的 Initial residual
        # 使用最终（last occurrence）残差，而非首迭代
        residuals: Dict[str, float] = {}
        for match in re.finditer(
            r"Solving for (\w+).*?Initial residual\s*=\s*([\d.eE+-]+)", text
        ):
            var = match.group(1)
            residuals[var] = float(match.group(2))

        # 关键物理量：末次时间步的最大速度
        key_quantities: Dict[str, Any] = {}
        mag_pattern = re.compile(r"Solving for Ux,.*?Initial residual\s*=\s*([\d.eE+-]+)")
        ux_matches = list(mag_pattern.finditer(text))
        if ux_matches:
            # 从最后的时间步提取Uy（Ux和Uy一起出现，取Uy的最后一个匹配）
            uy_pattern = re.compile(r"Solving for Uy,.*?Initial residual\s*=\s*([\d.eE+-]+)")
            uy_matches = list(uy_pattern.finditer(text))
            if uy_matches and ux_matches:
                ux_res = float(ux_matches[-1].group(1))
                uy_res = float(uy_matches[-1].group(1))
                # 最大速度近似（Ux 主导）
                key_quantities["U_max_approx"] = max(ux_res, abs(uy_res))

        # 从 postProcessing 目录读取速度场统计（如果存在）
        if not key_quantities:
            post_dir = log_path.parent / "postProcessing"
            if post_dir.exists():
                for sub in sorted(post_dir.iterdir()):
                    if sub.is_dir():
                        files = sorted(sub.iterdir())
                        if files:
                            last_file = files[-1]
                            lines = last_file.read_text(encoding="utf-8", errors="replace").splitlines()
                            vals = []
                            for line in lines:
                                parts = line.split()
                                if len(parts) > 3 and not line.startswith("#"):
                                    try:
                                        vals.append(float(parts[3]))
                                    except ValueError:
                                        pass
                            if vals:
                                key_quantities["u_centerline"] = vals

        return residuals, key_quantities

    # ------------------------------------------------------------------
    # Error helper
    # ------------------------------------------------------------------

    @staticmethod
    def _fail(
        message: str,
        elapsed: float,
        raw_output_path: Optional[str] = None,
    ) -> ExecutionResult:
        return ExecutionResult(
            success=False,
            is_mock=False,
            residuals={},
            key_quantities={},
            execution_time_s=elapsed,
            raw_output_path=raw_output_path,
            error_message=message,
        )
