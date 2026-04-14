"""Foam-Agent 调用适配器：MockExecutor（测试）+ FoamAgentExecutor（真实）"""

from __future__ import annotations

import io
import os
import re
import shutil
import tarfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .models import CFDExecutor, ExecutionResult, FlowType, GeometryType, TaskSpec

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
        ncx: int = 40,
        ncy: int = 20,
    ) -> None:
        self._work_dir = Path(work_dir or self.DEFAULT_WORK_DIR)
        self._container_name = container_name or self.CONTAINER_NAME
        self._timeout = self.SOLVER_TIMEOUT
        self._docker_client: Any = None
        self._ncx = ncx
        self._ncy = ncy

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
            # 4. 根据几何类型生成 case 文件
            if task_spec.geometry_type == GeometryType.BACKWARD_FACING_STEP:
                self._generate_backward_facing_step(case_host_dir, task_spec)
                solver_name = "simpleFoam"
            elif task_spec.geometry_type == GeometryType.NATURAL_CONVECTION_CAVITY:
                self._generate_natural_convection_cavity(case_host_dir, task_spec)
                solver_name = "buoyantSimpleFoam"
            elif task_spec.geometry_type == GeometryType.BODY_IN_CHANNEL:
                self._generate_circular_cylinder_wake(case_host_dir, task_spec)
                solver_name = "pimpleFoam"
            elif task_spec.geometry_type == GeometryType.AIRFOIL:
                self._generate_airfoil_flow(case_host_dir, task_spec)
                solver_name = "simpleFoam"
            elif task_spec.geometry_type == GeometryType.IMPINGING_JET:
                self._generate_impinging_jet(case_host_dir, task_spec)
                solver_name = "simpleFoam"
            elif task_spec.geometry_type == GeometryType.SIMPLE_GRID:
                # lid_driven_cavity 用专用 laminar generator (icoFoam)
                if "lid" in task_spec.name.lower() or task_spec.Re is not None and task_spec.Re < 2300:
                    self._generate_lid_driven_cavity(case_host_dir, task_spec)
                    solver_name = "icoFoam"
                else:
                    self._generate_steady_internal_flow(case_host_dir, task_spec)
                    solver_name = "simpleFoam"
            else:
                self._generate_lid_driven_cavity(case_host_dir, task_spec)
                solver_name = "icoFoam"

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

            if task_spec.geometry_type in {GeometryType.BODY_IN_CHANNEL, GeometryType.AIRFOIL}:
                topo_ok, topo_log = self._docker_exec(
                    "topoSet", case_cont_dir, self.BLOCK_MESH_TIMEOUT,
                )
                if not topo_ok:
                    return self._fail(
                        f"topoSet failed:\n{topo_log}",
                        time.monotonic() - t0,
                        raw_output_path=raw_output_path,
                    )

                baffles_ok, baffles_log = self._docker_exec(
                    "createBaffles -overwrite", case_cont_dir, self.BLOCK_MESH_TIMEOUT,
                )
                if not baffles_ok:
                    return self._fail(
                        f"createBaffles failed:\n{baffles_log}",
                        time.monotonic() - t0,
                        raw_output_path=raw_output_path,
                    )

            # 6. 执行求解器
            solver_ok, solver_log = self._docker_exec(
                solver_name, case_cont_dir, self._timeout,
            )
            if not solver_ok:
                return self._fail(
                    f"{solver_name} failed:\n{solver_log}",
                    time.monotonic() - t0,
                    raw_output_path=raw_output_path,
                )

            # 6.5. 执行 postProcess 提取完整场数据用于关键物理量计算
            # writeObjects: 写出 U/p/phi 等场文件
            # writeCellCentres: 写出 Cx/Cy/Cz cell center 坐标 (用于定位 probe 坐标)
            # 注意: 用 -funcs '(...)' 而非 -func，OpenFOAM 才能识别多个 functionObject
            post_ok, post_log = self._docker_exec(
                "postProcess -funcs '(writeObjects writeCellCentres)' -latestTime", case_cont_dir, 120,
            )
            # postProcess 失败不阻塞主流程（后续解析会处理无数据的情况）

            # 7. 复制 postProcess 输出的场文件到宿主机
            # postProcess 写出到 latestTime 目录，需要复制回 host 才能解析
            self._copy_postprocess_fields(container, case_cont_dir, case_host_dir)

            # 8. 解析 log 文件
            log_path = case_host_dir / f"log.{solver_name}"
            residuals, key_quantities = self._parse_solver_log(log_path, solver_name, task_spec)

            # 9. 从 writeObjects 输出的场文件提取 case-specific 关键物理量
            key_quantities = self._parse_writeobjects_fields(
                log_path.parent, solver_name, task_spec, key_quantities
            )

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

        # 2. constant/physicalProperties — 水的物性
        # convertToMeters=0.1, 实际 L=0.1m, U_lid=1 m/s
        # Re = U*L/nu → nu = U*L/Re = 0.1/Re
        Re = float(task_spec.Re or 100)
        nu_val = 0.1 / Re  # Re=100 → nu=0.001; Re=10 → nu=0.01
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

        # 8. system/sampleDict — 提取 mid-plane velocity profile (Ghia 1982)
        (case_dir / "system" / "sampleDict").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
|  sampleDict - extract velocity profile for Gold Standard comparison      |
\\*---------------------------------------------------------------------------*/
type            sets;
libs            ("libsampling.so");

interpolationScheme cellPoint;

setFormat       raw;

sets
(
    uCenterline
    {
        type        uniform;
        axis        y;
        start       (0.5 0.0 0.0);
        end         (0.5 1.0 0.0);
        nPoints     16;
    }
);

fields          (U);

// ************************************************************************* //
""",
            encoding="utf-8",
        )

    def _generate_backward_facing_step(self, case_dir: Path, task_spec: TaskSpec) -> None:
        """生成 Backward-Facing Step 最小 OpenFOAM case 文件。

        几何参数 (Driver & Seegmiller 1985, Gold Standard):
        - Re = 7600 (基于 step height H)
        - Expansion ratio = 1.125 (channel height 1.125H, inlet height H)
        - 2D channel flow, steady, incompressible
        - solver: simpleFoam
        """
        (case_dir / "system").mkdir(parents=True, exist_ok=True)
        (case_dir / "constant").mkdir(parents=True, exist_ok=True)
        (case_dir / "0").mkdir(parents=True, exist_ok=True)

        # Re=7600, H=1, U_bulk = nu*Re/H = nu*7600
        # 运动粘度 nu = 1e-5 (空气) 近似, 但 BFS 通常用水
        # Gold Standard: nu = U_bulk * H / Re, U_bulk 由 Re 反推
        # 这里 nu = 1/7600 m^2/s  (U_bulk=1 m/s, H=1 m)
        nu_val = 1.0 / float(task_spec.Re)  # ~1.316e-4 for Re=7600
        H = 1.0  # step height
        channel_height = 1.125 * H  # 1.125

        # 1. system/blockMeshDict — 2D channel with step at x=0
        block_mesh = self._render_bfs_block_mesh_dict(task_spec, H, channel_height, self._ncx, self._ncy)
        (case_dir / "system" / "blockMeshDict").write_text(block_mesh, encoding="utf-8")

        # 2. constant/physicalProperties — 牛顿流体物性
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

        # 3. system/controlDict — simpleFoam, steady-state
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

application     simpleFoam;

startFrom       startTime;

startTime       0;

stopAt          endTime;

endTime         1000;

deltaT          1;

writeControl    runTime;

writeInterval   100;

purgeWrite      0;

writeFormat     ascii;

writePrecision  6;

writeCompression off;

timeFormat      general;

timePrecision   6;

runTimeModifiable true;

maxCo           0.5;

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 4. system/fvSchemes — SIMPLE pressure-velocity coupling
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
    default         steadyState;
}

gradSchemes
{
    default         Gauss linear;
}

divSchemes
{
    default         none;
    div(phi,U)      Gauss linear;
    div(phi,k)      Gauss linear;
    div(phi,epsilon) Gauss linear;
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}

laplacianSchemes
{
    default         Gauss linear corrected;
}

interpolationSchemes
{
    default         linear;
}

snGradSchemes
{
    default         corrected;
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 5. system/fvSolution — SIMPLE solver settings, k-epsilon turbulence
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
        solver          GAMG;
        smoother        GaussSeidel;
        tolerance       1e-6;
        relTol          0.01;
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
        tolerance       1e-8;
        relTol          0.01;
    }

    k
    {
        solver          smoothSolver;
        smoother        GaussSeidel;
        tolerance       1e-8;
        relTol          0.01;
    }

    epsilon
    {
        solver          smoothSolver;
        smoother        GaussSeidel;
        tolerance       1e-8;
        relTol          0.01;
    }
}

SIMPLE
{
    nNonOrthogonalCorrectors 0;

    residualControl
    {
        Ux              1e-5;
        Uy              1e-5;
        p               1e-4;
        k               1e-5;
        epsilon         1e-5;
    }
}

relaxationFactors
{
    equations
    {
        U               0.9;
        k               0.9;
        epsilon         0.9;
    }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 6. 0/U — 速度边界条件
        # Inlet: uniform flow U = (U_bulk, 0, 0), where U_bulk = 1 m/s
        # (Re = U_bulk*H/nu, so U_bulk = nu*Re/H = nu*7600)
        u_bulk = nu_val * float(task_spec.Re)  # = 1.0 m/s for this nu/Re pairing
        (case_dir / "0" / "U").write_text(
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
    class       volVectorField;
    location    "0";
    object      U;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 1 -1 0 0 0 0];

internalField   uniform (0 0 0);

boundaryField
{{
    inlet
    {{
        type            fixedValue;
        value           uniform ({u_bulk} 0 0);
    }}
    outlet
    {{
        type            zeroGradient;
    }}
    lower_wall
    {{
        type            noSlip;
    }}
    upper_wall
    {{
        type            noSlip;
    }}
    front
    {{
        type            empty;
    }}
    back
    {{
        type            empty;
    }}
}}

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
    inlet
    {
        type            zeroGradient;
    }
    outlet
    {
        type            fixedValue;
        value           uniform 0;
    }
    lower_wall
    {
        type            zeroGradient;
    }
    upper_wall
    {
        type            zeroGradient;
    }
    front
    {
        type            empty;
    }
    back
    {
        type            empty;
    }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 8. constant/turbulenceProperties — k-epsilon model
        (case_dir / "constant" / "turbulenceProperties").write_text(
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
    location    "constant";
    object      turbulenceProperties;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

simulationType  RAS;

RAS
{
    RASModel     kEpsilon;

    turbulence   on;

    printCoeffs  on;
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 9. 0/nut — turbulent viscosity (required by kEpsilon)
        # Estimated: nut ~ 0.01 for Re=7600 (based on nu=1.316e-4 and U=1)
        nut_val = 0.01  # initial estimate
        (case_dir / "0" / "nut").write_text(
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
    class       volScalarField;
    location    "0";
    object      nut;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -1 0 0 0 0];

internalField   uniform {nut_val};

boundaryField
{{
    inlet
    {{
        type            fixedValue;
        value           uniform {nut_val};
    }}
    outlet
    {{
        type            zeroGradient;
    }}
    lower_wall
    {{
        type            nutkWallFunction;
        value           uniform 0;
    }}
    upper_wall
    {{
        type            nutkWallFunction;
        value           uniform 0;
    }}
    front
    {{
        type            empty;
    }}
    back
    {{
        type            empty;
    }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 10. 0/k — turbulent kinetic energy
        # Estimated: k = 0.001 for low turbulence
        k_val = 0.001
        (case_dir / "0" / "k").write_text(
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
    class       volScalarField;
    location    "0";
    object      k;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -2 0 0 0 0];

internalField   uniform {k_val};

boundaryField
{{
    inlet
    {{
        type            fixedValue;
        value           uniform {k_val};
    }}
    outlet
    {{
        type            zeroGradient;
    }}
    lower_wall
    {{
        type            kqRWallFunction;
        value           uniform {k_val};
    }}
    upper_wall
    {{
        type            kqRWallFunction;
        value           uniform {k_val};
    }}
    front
    {{
        type            empty;
    }}
    back
    {{
        type            empty;
    }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 11. 0/epsilon — turbulent dissipation rate
        # Estimated: epsilon = 0.001 for low turbulence
        epsilon_val = 0.001
        (case_dir / "0" / "epsilon").write_text(
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
    class       volScalarField;
    location    "0";
    object      epsilon;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -3 0 0 0 0];

internalField   uniform {epsilon_val};

boundaryField
{{
    inlet
    {{
        type            fixedValue;
        value           uniform {epsilon_val};
    }}
    outlet
    {{
        type            zeroGradient;
    }}
    lower_wall
    {{
        type            epsilonWallFunction;
        value           uniform {epsilon_val};
    }}
    upper_wall
    {{
        type            epsilonWallFunction;
        value           uniform {epsilon_val};
    }}
    front
    {{
        type            empty;
    }}
    back
    {{
        type            empty;
    }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 8. system/sampleDict — extract velocity profile to find reattachment length (Driver 1985)
        # Sample Ux at y=0.5 (boundary layer) along x from -1 to 12
        # Reattachment point: where Ux changes from negative (recirculation) to positive
        (case_dir / "system" / "sampleDict").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
|  sampleDict - extract velocity profile for reattachment length           |
\\*---------------------------------------------------------------------------*/
type            sets;
libs            ("libsampling.so");

interpolationScheme cellPoint;

setFormat       raw;

sets
(
    wallProfile
    {
        type        uniform;
        axis        x;
        start       (-1.0 0.5 0.0);
        end         (12.0 0.5 0.0);
        nPoints     100;
    }
);

fields          (U);

// ************************************************************************* //
""",
            encoding="utf-8",
        )

    def _generate_natural_convection_cavity(self, case_dir: Path, task_spec: TaskSpec) -> None:
        """生成自然对流腔体（差温腔体）OpenFOAM case 文件。

        参考: Dhir 2001, Ampofo & Karayiannis 2003 (Ra=10^10).
        - Square cavity, aspect ratio = 1
        - Left wall: hot (T_hot), Right wall: cold (T_cold)
        - Top/bottom: adiabatic
        - 2D approximation (z-depth = 0.1m)
        - Solver: buoyantSimpleFoam (Boussinesq approximation)
        - Turbulence: k-omega SST
        """
        (case_dir / "system").mkdir(parents=True, exist_ok=True)
        (case_dir / "constant").mkdir(parents=True, exist_ok=True)
        (case_dir / "0").mkdir(parents=True, exist_ok=True)

        # Physical parameters
        Ra = float(task_spec.Re or 1e10)  # Use Re field as Ra proxy (1e10 default)
        Pr = 0.71  # Prandtl number (air)
        T_hot = 305.0  # K
        T_cold = 295.0  # K
        dT = T_hot - T_cold  # 10K
        L = 1.0  # cavity length (m)
        beta = 1.0 / T_hot  # thermal expansion coefficient (Boussinesq)
        nu = 1.0e-5  # kinematic viscosity (air, m^2/s)
        alpha = nu / Pr  # thermal diffusivity

        # Derived
        # Ra = g * beta * dT * L^3 / (nu * alpha)
        # g = Ra * nu * alpha / (beta * dT * L^3)
        g = Ra * nu * alpha / (beta * dT * L**3)  # gravity magnitude

        # --------------------------------------------------------------------------
        # 1. system/blockMeshDict — Square cavity, 40x40 cells
        # --------------------------------------------------------------------------
        (case_dir / "system" / "blockMeshDict").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      blockMeshDict;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

convertToMeters 1;

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
    hex (0 1 2 3 4 5 6 7) (40 40 1) simpleGrading (1 1 1)
);

edges
(
);

boundary
(
    hot_wall
    {
        type            wall;
        faces           ((0 4 7 3));
    }
    cold_wall
    {
        type            wall;
        faces           ((1 2 6 5));
    }
    adiabatic_top
    {
        type            wall;
        faces           ((3 7 6 2));
    }
    adiabatic_bottom
    {
        type            wall;
        faces           ((0 1 5 4));
    }
    front
    {
        type            empty;
        faces           ((0 3 2 1));
    }
    back
    {
        type            empty;
        faces           ((4 5 6 7));
    }
);

mergePatchPairs
(
);

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # --------------------------------------------------------------------------
        # 2. constant/physicalProperties — Boussinesq fluid
        # --------------------------------------------------------------------------
        (case_dir / "constant" / "physicalProperties").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
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

nu              [0 2 -1 0 0 0 0] {nu:.16e};

Pr              {Pr};

Prt             0.71;

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # --------------------------------------------------------------------------
        # 3. constant/g — Gravity
        # --------------------------------------------------------------------------
        (case_dir / "constant" / "g").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      g;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

value           (0 -{g:.16e} 0);

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # --------------------------------------------------------------------------
        # 4. constant/turbulenceProperties
        # --------------------------------------------------------------------------
        (case_dir / "constant" / "turbulenceProperties").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      turbulenceProperties;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

simulationType  RAS;

RAS
{
    RASModel      kOmegaSST;

    turbulence    on;

    printCoeffs   on;
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # --------------------------------------------------------------------------
        # 5. system/controlDict — buoyantSimpleFoam
        # --------------------------------------------------------------------------
        (case_dir / "system" / "controlDict").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      controlDict;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

application     buoyantSimpleFoam;

startFrom       startTime;

startTime       0;

stopAt          endTime;

endTime         1000;

deltaT          1;

writeControl    runTime;

writeInterval   100;

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

        # --------------------------------------------------------------------------
        # 6. system/fvSchemes
        # --------------------------------------------------------------------------
        (case_dir / "system" / "fvSchemes").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
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
    default         steadyState;
}

gradSchemes
{
    default         Gauss linear;
}

divSchemes
{
    default         none;
    div(phi,U)      Gauss linearUpwind grad(U);
    div(phi,T)      Gauss linearUpwind grad(T);
    div(phi,k)      Gauss linearUpwind grad(k);
    div(phi,epsilon) Gauss linearUpwind grad(epsilon);
    div(phi,omega)  Gauss linearUpwind grad(omega);
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}

laplacianSchemes
{
    default         Gauss linear corrected;
}

interpolationSchemes
{
    default         linear;
}

snGradSchemes
{
    default         corrected;
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # --------------------------------------------------------------------------
        # 7. system/fvSolution
        # --------------------------------------------------------------------------
        (case_dir / "system" / "fvSolution").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
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
        solver          GAMG;
        smoother        GaussSeidel;
        tolerance       1e-6;
        relTol          0.01;
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
        tolerance       1e-7;
        relTol          0.01;
    }
    UFinal
    {
        $U;
        relTol          0;
    }
    T
    {
        solver          PBiCGStab;
        preconditioner   DILU;
        tolerance       1e-7;
        relTol          0.01;
    }
    TFinal
    {
        $T;
        relTol          0;
    }
    k
    {
        solver          PBiCGStab;
        preconditioner   DILU;
        tolerance       1e-7;
        relTol          0.01;
    }
    epsilon
    {
        solver          PBiCGStab;
        preconditioner   DILU;
        tolerance       1e-6;
        relTol          0.01;
    }
    omega
    {
        solver          PBiCGStab;
        preconditioner   DILU;
        tolerance       1e-7;
        relTol          0.01;
    }
}

SIMPLE
{
    nNonOrthogonalCorrectors 1;

    residualControl
    {
        U       1e-5;
        T       1e-5;
        p       1e-4;
        k       1e-5;
        epsilon 1e-5;
        omega   1e-5;
    }
}

relaxationFactors
{
    equations
    {
        U               0.9;
        T               0.7;
        k               0.9;
        epsilon         0.9;
        omega           0.9;
    }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # --------------------------------------------------------------------------
        # 8. 0/U — Velocity (initial: zero)
        # --------------------------------------------------------------------------
        (case_dir / "0" / "U").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
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
    hot_wall
    {
        type            fixedValue;
        value           uniform (0 0 0);
    }
    cold_wall
    {
        type            fixedValue;
        value           uniform (0 0 0);
    }
    adiabatic_top
    {
        type            fixedValue;
        value           uniform (0 0 0);
    }
    adiabatic_bottom
    {
        type            fixedValue;
        value           uniform (0 0 0);
    }
    front { type empty; }
    back  { type empty; }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # --------------------------------------------------------------------------
        # 9. 0/p — Pressure
        # --------------------------------------------------------------------------
        (case_dir / "0" / "p").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
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
    hot_wall
    {
        type            zeroGradient;
    }
    cold_wall
    {
        type            zeroGradient;
    }
    adiabatic_top
    {
        type            zeroGradient;
    }
    adiabatic_bottom
    {
        type            zeroGradient;
    }
    front { type empty; }
    back  { type empty; }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # --------------------------------------------------------------------------
        # 10. 0/T — Temperature
        # --------------------------------------------------------------------------
        (case_dir / "0" / "T").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      T;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 0 1 0 0 0 0];

internalField   uniform {T_cold};

boundaryField
{{
    hot_wall
    {{
        type            fixedValue;
        value           uniform {T_hot};
    }}
    cold_wall
    {{
        type            fixedValue;
        value           uniform {T_cold};
    }}
    adiabatic_top
    {{
        type            zeroGradient;
    }}
    adiabatic_bottom
    {{
        type            zeroGradient;
    }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # --------------------------------------------------------------------------
        # 11. 0/k and 0/omega — Turbulence (initial)
        # --------------------------------------------------------------------------
        for fname, val in [("k", 1e-4), ("omega", 1e-4)]:
            (case_dir / "0" / fname).write_text(
                f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      {fname};
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -2 0 0 0 0];

internalField   uniform {val:.16e};

boundaryField
{{
    hot_wall           {{ type calculated; value uniform {val:.16e}; }}
    cold_wall          {{ type calculated; value uniform {val:.16e}; }}
    adiabatic_top       {{ type calculated; value uniform {val:.16e}; }}
    adiabatic_bottom    {{ type calculated; value uniform {val:.16e}; }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
                encoding="utf-8",
            )

        # --------------------------------------------------------------------------
        # 12. 0/nut — Turbulent viscosity (for k-omega SST)
        # --------------------------------------------------------------------------
        (case_dir / "0" / "nut").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      nut;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -1 0 0 0 0];

internalField   uniform 0;

boundaryField
{
    hot_wall           { type nutkWallFunction; value uniform 0; }
    cold_wall          { type nutkWallFunction; value uniform 0; }
    adiabatic_top       { type nutkWallFunction; value uniform 0; }
    adiabatic_bottom    { type nutkWallFunction; value uniform 0; }
    front { type empty; }
    back  { type empty; }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

    def _generate_steady_internal_flow(self, case_dir: Path, task_spec: TaskSpec) -> None:
        """生成稳态内部流 case 文件（simpleFoam + k-epsilon）。

        适用于:
        - Turbulent Flat Plate (SIMPLE_GRID, Re=5e4)
        - Fully Developed Pipe Flow (SIMPLE_GRID, Re=5e4)

        几何: 矩形通道, 2D 近似 (z-depth = 0.1m)
        - inlet: uniform velocity U = (U_bulk, 0, 0)
        - walls: no-slip
        - outlet: zeroGradient pressure
        """
        (case_dir / "system").mkdir(parents=True, exist_ok=True)
        (case_dir / "constant").mkdir(parents=True, exist_ok=True)
        (case_dir / "0").mkdir(parents=True, exist_ok=True)

        Re = float(task_spec.Re or 50000)
        L = float(task_spec.boundary_conditions.get("plate_length", 1.0)) if task_spec.boundary_conditions else 1.0
        nu_val = 1.0 / Re  # U_bulk=1 m/s → nu = 1/Re
        U_bulk = 1.0  # m/s (consistent with nu=1/Re)

        # Domain: x=[0, 5L], y=[0, 0.5], z=[0, 0.1]
        x_min, x_max = 0.0, 5.0 * L
        y_min, y_max = 0.0, 0.5
        z_min, z_max = 0.0, 0.1

        (case_dir / "system" / "blockMeshDict").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      blockMeshDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

convertToMeters 1;

vertices
(
    ({x_min} {y_min} {z_min})
    ({x_max} {y_min} {z_min})
    ({x_max} {y_max} {z_min})
    ({x_min} {y_max} {z_min})
    ({x_min} {y_min} {z_max})
    ({x_max} {y_min} {z_max})
    ({x_max} {y_max} {z_max})
    ({x_min} {y_max} {z_max})
);

blocks
(
    hex (0 1 2 3 4 5 6 7) (100 20 1) simpleGrading (1 1 1)
);

edges
(
);

boundary
(
    inlet
    {{
        type            patch;
        faces           ((0 4 7 3));
    }}
    outlet
    {{
        type            patch;
        faces           ((1 2 6 5));
    }}
    walls
    {{
        type            wall;
        faces           ((0 1 5 4)) ((3 6 7 2));
    }}
    front
    {{
        type            empty;
        faces           ((0 3 2 1));
    }}
    back
    {{
        type            empty;
        faces           ((4 5 6 7));
    }}
);

mergePatchPairs
(
);

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # constant/physicalProperties
        (case_dir / "constant" / "physicalProperties").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
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

        # constant/turbulenceProperties — k-epsilon
        (case_dir / "constant" / "turbulenceProperties").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      turbulenceProperties;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

simulationType  RAS;

RAS
{
    RASModel      kEpsilon;
    turbulence    on;
    printCoeffs   on;
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # system/controlDict
        (case_dir / "system" / "controlDict").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      controlDict;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

application     simpleFoam;

startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         1000;
deltaT          1;
writeControl    runTime;
writeInterval   100;
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

        # system/fvSchemes
        (case_dir / "system" / "fvSchemes").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
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
    default         steadyState;
}
gradSchemes
{
    default         Gauss linear;
}
divSchemes
{
    default         none;
    div(phi,U)      Gauss linearUpwind grad(U);
    div(phi,k)      Gauss linearUpwind grad(k);
    div(phi,epsilon) Gauss linearUpwind grad(epsilon);
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes
{
    default         Gauss linear corrected;
}
interpolationSchemes
{
    default         linear;
}
snGradSchemes
{
    default         corrected;
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # system/fvSolution
        (case_dir / "system" / "fvSolution").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
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
        solver          GAMG;
        smoother        GaussSeidel;
        tolerance       1e-6;
        relTol          0.01;
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
        tolerance       1e-7;
        relTol          0.01;
    }
    UFinal
    {
        $U;
        relTol          0;
    }
    k
    {
        solver          PBiCGStab;
        preconditioner   DILU;
        tolerance       1e-7;
        relTol          0.01;
    }
    epsilon
    {
        solver          PBiCGStab;
        preconditioner   DILU;
        tolerance       1e-6;
        relTol          0.01;
    }
}

SIMPLE
{
    nNonOrthogonalCorrectors 1;
    residualControl
    {
        U       1e-5;
        p       1e-4;
        k       1e-5;
        epsilon  1e-5;
    }
}

relaxationFactors
{
    equations
    {
        U               0.9;
        k               0.9;
        epsilon         0.9;
    }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 0/U
        (case_dir / "0" / "U").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volVectorField;
    location    "0";
    object      U;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 1 -1 0 0 0 0];

internalField   uniform (0 0 0);

boundaryField
{{
    inlet
    {{
        type            fixedValue;
        value           uniform ({U_bulk} 0 0);
    }}
    outlet
    {{
        type            zeroGradient;
    }}
    walls
    {{
        type            noSlip;
    }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 0/p
        (case_dir / "0" / "p").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
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
    inlet
    {
        type            zeroGradient;
    }
    outlet
    {
        type            fixedValue;
        value           uniform 0;
    }
    walls
    {
        type            zeroGradient;
    }
    front { type empty; }
    back  { type empty; }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 0/k
        k_init = 0.01
        (case_dir / "0" / "k").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      k;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -2 0 0 0 0];

internalField   uniform {k_init};

boundaryField
{{
    inlet        {{ type fixedValue; value uniform {k_init}; }}
    outlet       {{ type zeroGradient; }}
    walls        {{ type kLowReWallFunction; value uniform {k_init}; }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 0/epsilon
        eps_init = 0.001
        (case_dir / "0" / "epsilon").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      epsilon;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -3 0 0 0 0];

internalField   uniform {eps_init};

boundaryField
{{
    inlet        {{ type fixedValue; value uniform {eps_init}; }}
    outlet       {{ type zeroGradient; }}
    walls        {{ type epsilonWallFunction; value uniform {eps_init}; }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 0/nut
        (case_dir / "0" / "nut").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      nut;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -1 0 0 0 0];

internalField   uniform 0;

boundaryField
{{
    inlet        {{ type calculated; value uniform 0; }}
    outlet       {{ type calculated; value uniform 0; }}
    walls        {{ type nutkWallFunction; value uniform 0; }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # system/sampleDict — extract temperature profile for Nusselt number validation
        (case_dir / "system" / "sampleDict").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
|  sampleDict - extract temperature profile for natural convection cavity     |
\\*---------------------------------------------------------------------------*/
type            sets;
libs            ("libsampling.so");

interpolationScheme cellPoint;

setFormat       raw;

sets
(
    midPlaneT
    {
        type        uniform;
        axis        y;
        start       (0.5 0.0 0.0);
        end         (0.5 1.0 0.0);
        nPoints     20;
    }
);

fields          (T);

// ************************************************************************* //
""",
            encoding="utf-8",
        )

    def _generate_circular_cylinder_wake(self, case_dir: Path, task_spec: TaskSpec) -> None:
        """生成圆柱尾迹 case 文件 (pimpleFoam transient).

        适用于:
        - Circular Cylinder Wake (BODY_IN_CHANNEL, EXTERNAL, TRANSIENT, Re=100)
        - Plane Channel Flow DNS (BODY_IN_CHANNEL, INTERNAL, STEADY, Re_tau=180)

        几何: 矩形通道中央放置圆柱
        - 圆柱直径 D = 0.1m
        - 通道截面: 20D × 10D
        - 圆柱位于 x=2D 位置
        """
        (case_dir / "system").mkdir(parents=True, exist_ok=True)
        (case_dir / "constant").mkdir(parents=True, exist_ok=True)
        (case_dir / "0").mkdir(parents=True, exist_ok=True)

        Re = float(task_spec.Re or 100)
        D = 0.1  # cylinder diameter
        U_bulk = 1.0  # m/s
        nu_val = U_bulk * D / Re  # kinematic viscosity

        # Channel dimensions
        W = 2.0 * D  # half-width
        H = 2.5 * D  # half-height
        L_inlet = 2.0 * D  # upstream length
        L_outlet = 8.0 * D  # downstream length
        z_depth = 0.1 * D  # 2D thickness

        x_min = -L_inlet
        x_max = L_outlet
        y_min = -H
        y_max = H
        z_min = -z_depth / 2
        z_max = z_depth / 2

        # Vertex indices for blockMesh (single block, cylindrical hole via boundary)
        # We'll create a rectangular channel and define cylinder via curved boundary
        # Simple approach: rectangular channel with cylinder as a circular patch
        (case_dir / "system" / "blockMeshDict").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      blockMeshDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

convertToMeters 1;

vertices
(
    ({x_min:.6f} {y_min:.6f} {z_min:.6f})
    ({x_max:.6f} {y_min:.6f} {z_min:.6f})
    ({x_max:.6f} {y_max:.6f} {z_min:.6f})
    ({x_min:.6f} {y_max:.6f} {z_min:.6f})
    ({x_min:.6f} {y_min:.6f} {z_max:.6f})
    ({x_max:.6f} {y_min:.6f} {z_max:.6f})
    ({x_max:.6f} {y_max:.6f} {z_max:.6f})
    ({x_min:.6f} {y_max:.6f} {z_max:.6f})
);

blocks
(
    hex (0 1 2 3 4 5 6 7) (200 100 1) simpleGrading (1 1 1)
);

edges
(
);

boundary
(
    inlet
    {{
        type            patch;
        faces           ((0 4 7 3));
    }}
    outlet
    {{
        type            patch;
        faces           ((1 2 6 5));
    }}
    lower_wall
    {{
        type            wall;
        faces           ((0 1 5 4));
    }}
    upper_wall
    {{
        type            wall;
        faces           ((3 6 7 2));
    }}
    front
    {{
        type            empty;
        faces           ((0 3 2 1));
    }}
    back
    {{
        type            empty;
        faces           ((4 5 6 7));
    }}
);

mergePatchPairs
(
);

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # system/topoSetDict -- cylinder cellZone via cylinderToCell + faceZone for createBaffles
        (case_dir / "system" / "topoSetDict").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\\\    /   O peration     | Version:  10                                    |
|   \\\\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      topoSetDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

actions
(
    {{
        name    cylinderCells;
        type    cellSet;
        action  new;
        source  cylinderToCell;
        sourceInfo
        {{
            point1 (0 0 {z_min:.6f});
            point2 (0 0 {z_max:.6f});
            radius {D / 2:.6f};
        }}
    }}
    {{
        name    cylinderZone;
        type    cellZoneSet;
        action  new;
        source  setToCellZone;
        sourceInfo
        {{
            set cylinderCells;
        }}
    }}
    {{
        name    cylinderAllFaces;
        type    faceSet;
        action  new;
        source  cellToFace;
        sourceInfo
        {{
            set cylinderCells;
            option all;
        }}
    }}
    {{
        name    cylinderInternalFaces;
        type    faceSet;
        action  new;
        source  cellToFace;
        sourceInfo
        {{
            set cylinderCells;
            option both;
        }}
    }}
    {{
        name    cylinderBaffleFaces;
        type    faceSet;
        action  new;
        source  faceToFace;
        sourceInfo
        {{
            set cylinderAllFaces;
        }}
    }}
    {{
        name    cylinderBaffleFaces;
        type    faceSet;
        action  delete;
        source  faceToFace;
        sourceInfo
        {{
            set cylinderInternalFaces;
        }}
    }}
    {{
        name    cylinderBaffleZone;
        type    faceZoneSet;
        action  new;
        source  setsToFaceZone;
        sourceInfo
        {{
            faceSet cylinderBaffleFaces;
            cellSet cylinderCells;
            flip false;
        }}
    }}
);

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # system/createBafflesDict -- converts internal faceZone to wall patch "cylinder"
        (case_dir / "system" / "createBafflesDict").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\\\    /   O peration     | Version:  10                                    |
|   \\\\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      createBafflesDict;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

internalFacesOnly true;

baffles
{
    cylinderBaffleZone
    {
        type faceZone;
        zoneName cylinderBaffleZone;
        patches
        {
            owner
            {
                name cylinder;
                type wall;
            }
            neighbour
            {
                name cylinder;
                type wall;
            }
        }
    }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )
        # constant/physicalProperties
        (case_dir / "constant" / "physicalProperties").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
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

nu              [0 2 -1 0 0 0 0] {nu_val:.6e};

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # constant/turbulenceProperties — k-omega SST for external aerodynamic
        (case_dir / "constant" / "turbulenceProperties").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      turbulenceProperties;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

simulationType  RAS;

RAS
{
    RASModel      kOmegaSST;
    turbulence    on;
    printCoeffs   on;
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # system/controlDict — pimpleFoam transient
        (case_dir / "system" / "controlDict").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      controlDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

application     pimpleFoam;

startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         5.0;
deltaT          0.002;
writeControl    runTime;
writeInterval   0.5;
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

        # system/fvSchemes
        (case_dir / "system" / "fvSchemes").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
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
    div(phi,U)      Gauss linearUpwind grad(U);
    div(phi,k)      Gauss linearUpwind grad(k);
    div(phi,epsilon) Gauss linearUpwind grad(epsilon);
    div(phi,omega)   Gauss linearUpwind grad(omega);
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes
{
    default         Gauss linear corrected;
}
interpolationSchemes
{
    default         linear;
}
snGradSchemes
{
    default         corrected;
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # system/fvSolution
        (case_dir / "system" / "fvSolution").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
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
        solver          GAMG;
        smoother        GaussSeidel;
        tolerance       1e-5;
        relTol          0.01;
    }
    pFinal
    {
        $p;
        relTol          0;
    }
    U
    {
        solver          PBiCGStab;
        preconditioner   DILU;
        tolerance       1e-6;
        relTol          0.01;
    }
    UFinal
    {
        $U;
        relTol          0;
    }
    k
    {
        solver          PBiCGStab;
        preconditioner   DILU;
        tolerance       1e-6;
        relTol          0.01;
    }
    epsilon
    {
        solver          PBiCGStab;
        preconditioner   DILU;
        tolerance       1e-5;
        relTol          0.01;
    }
    omega
    {
        solver          PBiCGStab;
        preconditioner   DILU;
        tolerance       1e-7;
        relTol          0.01;
    }
}

PIMPLE
{
    nOuterCorrectors 1;
    nCorrectors     2;
    nNonOrthogonalCorrectors 1;
}

relaxationFactors
{
    equations
    {
        U               0.9;
        k               0.9;
        epsilon         0.9;
        omega           0.9;
    }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 0/U
        (case_dir / "0" / "U").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volVectorField;
    location    "0";
    object      U;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 1 -1 0 0 0 0];

internalField   uniform ({U_bulk} 0 0);

boundaryField
{{
    inlet        {{ type fixedValue; value uniform ({U_bulk} 0 0); }}
    outlet       {{ type zeroGradient; }}
    lower_wall   {{ type noSlip; }}
    upper_wall   {{ type noSlip; }}
    cylinder     {{ type noSlip; }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 0/p
        (case_dir / "0" / "p").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      p;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -2 0 0 0 0];

internalField   uniform 0;

boundaryField
{{
    inlet        {{ type zeroGradient; }}
    outlet       {{ type fixedValue; value uniform 0; }}
    lower_wall   {{ type zeroGradient; }}
    upper_wall   {{ type zeroGradient; }}
    cylinder     {{ type zeroGradient; }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 0/k — turbulent kinetic energy
        (case_dir / "0" / "k").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      k;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -2 0 0 0 0];

internalField   uniform 0.01;

boundaryField
{{
    inlet        {{ type fixedValue; value uniform 0.01; }}
    outlet       {{ type zeroGradient; }}
    lower_wall   {{ type kLowReWallFunction; value uniform 0; }}
    upper_wall   {{ type kLowReWallFunction; value uniform 0; }}
    cylinder     {{ type kLowReWallFunction; value uniform 0; }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 0/omega — specific dissipation rate (kOmegaSST)
        (case_dir / "0" / "omega").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      omega;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 0 -1 0 0 0 0];

internalField   uniform 100.0;

boundaryField
{{
    inlet        {{ type fixedValue; value uniform 100.0; }}
    outlet       {{ type zeroGradient; }}
    lower_wall   {{ type omegaWallFunction; value uniform 1.0; }}
    upper_wall   {{ type omegaWallFunction; value uniform 1.0; }}
    cylinder     {{ type omegaWallFunction; value uniform 1.0; }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )
        (case_dir / "0" / "nut").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      nut;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -1 0 0 0 0];

internalField   uniform 0;

boundaryField
{
    inlet        { type calculated; value uniform 0; }
    outlet       { type calculated; value uniform 0; }
    lower_wall   { type nutkWallFunction; value uniform 0; }
    upper_wall   { type nutkWallFunction; value uniform 0; }
    cylinder     { type nutkWallFunction; value uniform 0; }
    front { type empty; }
    back  { type empty; }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

    def _generate_impinging_jet(self, case_dir: Path, task_spec: TaskSpec) -> None:
        """Generate impinging jet case files (simpleFoam steady)."""
        (case_dir / "system").mkdir(parents=True, exist_ok=True)
        (case_dir / "constant").mkdir(parents=True, exist_ok=True)
        (case_dir / "0").mkdir(parents=True, exist_ok=True)

        Re = float(task_spec.Re or 10000)
        D = 0.05
        h_over_d = 2.0
        H = h_over_d * D
        U_bulk = 1.0
        nu_val = U_bulk * D / Re

        # Domain: r=[0, 5D], z=[z_min, z_max]; split at z=0 for planar faces
        r_max = 5.0 * D
        z_min = -D / 2
        z_split = 0.0
        z_max = H + D / 2
        n_r = 60
        total_nz = 80
        n_z_lower = max(1, int(round(total_nz * (z_split - z_min) / (z_max - z_min))))
        n_z_upper = total_nz - n_z_lower

        (case_dir / "system" / "blockMeshDict").write_text(
            f"""/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \    /   O peration     | Version:  10                                    |
|   \  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      blockMeshDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

convertToMeters 1;

vertices
(
    (0 {z_min:.6f} 0)
    ({r_max:.6f} {z_min:.6f} 0)
    ({r_max:.6f} {z_split:.6f} 0)
    (0 {z_split:.6f} 0)
    (0 {z_min:.6f} 0.1)
    ({r_max:.6f} {z_min:.6f} 0.1)
    ({r_max:.6f} {z_split:.6f} 0.1)
    (0 {z_split:.6f} 0.1)
    (0 {z_max:.6f} 0)
    ({r_max:.6f} {z_max:.6f} 0)
    ({r_max:.6f} {z_max:.6f} 0.1)
    (0 {z_max:.6f} 0.1)
);

blocks
(
    hex (0 1 2 3 4 5 6 7) ({n_r} {n_z_lower} 1) simpleGrading (1 1 1)
    hex (3 2 9 8 7 6 10 11) ({n_r} {n_z_upper} 1) simpleGrading (1 1 1)
);

edges
(
);

boundary
(
    inlet
    {{
        type            patch;
        faces           ((0 4 5 1));
    }}
    plate
    {{
        type            wall;
        faces           ((8 9 10 11));
    }}
    outer
    {{
        type            wall;
        faces           ((1 5 6 2) (2 6 10 9));
    }}
    axis
    {{
        type            empty;
        faces           ((0 3 7 4) (3 8 11 7));
    }}
    front
    {{
        type            empty;
        faces           ((0 1 2 3) (3 2 9 8));
    }}
    back
    {{
        type            empty;
        faces           ((4 5 6 7) (7 6 10 11));
    }}
);

mergePatchPairs
(
);

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        (case_dir / "constant" / "physicalProperties").write_text(
            f"""/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \    /   O peration     | Version:  10                                    |
|   \  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
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
nu              [0 2 -1 0 0 0 0] {nu_val:.6e};

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        (case_dir / "constant" / "turbulenceProperties").write_text(
            """/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \    /   O peration     | Version:  10                                    |
|   \  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      turbulenceProperties;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

simulationType  RAS;
RAS
{
    RASModel      kOmegaSST;
    turbulence    on;
    printCoeffs   on;
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        (case_dir / "system" / "controlDict").write_text(
            """/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \    /   O peration     | Version:  10                                    |
|   \  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      controlDict;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

application     simpleFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         1000;
deltaT          1;
writeControl    runTime;
writeInterval   100;
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

        (case_dir / "system" / "fvSchemes").write_text(
            """/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \    /   O peration     | Version:  10                                    |
|   \  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSchemes;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

ddtSchemes { default steadyState; }
gradSchemes { default Gauss linear; }
divSchemes {
    default none;
    div(phi,U) Gauss linearUpwind grad(U);
    div(phi,k) Gauss linearUpwind grad(k);
    div(phi,omega) Gauss linearUpwind grad(omega);
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
wallDist { method meshWave; }

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        (case_dir / "system" / "fvSolution").write_text(
            """/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \    /   O peration     | Version:  10                                    |
|   \  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
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
    p { solver GAMG; smoother GaussSeidel; tolerance 1e-6; relTol 0.01; }
    U { solver PBiCGStab; preconditioner DILU; tolerance 1e-7; relTol 0.01; }
    k { solver PBiCGStab; preconditioner DILU; tolerance 1e-7; relTol 0.01; }
    omega { solver PBiCGStab; preconditioner DILU; tolerance 1e-7; relTol 0.01; }
}

SIMPLE
{
    nNonOrthogonalCorrectors 1;
    residualControl { U 1e-5; p 1e-4; k 1e-5; omega 1e-5; }
}

relaxationFactors
{
    equations { U 0.7; k 0.7; omega 0.7; }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        U_nozzle = U_bulk
        (case_dir / "0" / "U").write_text(
            f"""/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \    /   O peration     | Version:  10                                    |
|   \  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volVectorField;
    location    "0";
    object      U;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 1 -1 0 0 0 0];

internalField   uniform (0 0 0);

boundaryField
{{
    inlet           {{ type fixedValue; value uniform (0 {U_nozzle:.6f} 0); }}
    plate           {{ type noSlip; }}
    outer           {{ type zeroGradient; }}
    axis            {{ type empty; }}
    front           {{ type empty; }}
    back            {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        (case_dir / "0" / "p").write_text(
            """/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \    /   O peration     | Version:  10                                    |
|   \  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
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
    inlet       { type zeroGradient; }
    plate       { type zeroGradient; }
    outer       { type fixedValue; value uniform 0; }
    axis        { type empty; }
    front       { type empty; }
    back        { type empty; }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        (case_dir / "0" / "k").write_text(
            f"""/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \    /   O peration     | Version:  10                                    |
|   \  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      k;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -2 0 0 0 0];
internalField   uniform 0.01;
boundaryField
{{
    inlet           {{ type fixedValue; value uniform 0.01; }}
    plate           {{ type kLowReWallFunction; value uniform 0.01; }}
    outer           {{ type fixedValue; value uniform 0.01; }}
    axis            {{ type empty; }}
    front           {{ type empty; }}
    back            {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        (case_dir / "0" / "omega").write_text(
            f"""/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \    /   O peration     | Version:  10                                    |
|   \  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      omega;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 0 -1 0 0 0 0];
internalField   uniform 500.0;
boundaryField
{{
    inlet           {{ type fixedValue; value uniform 500.0; }}
    plate           {{ type omegaWallFunction; value uniform 500.0; }}
    outer           {{ type fixedValue; value uniform 500.0; }}
    axis            {{ type empty; }}
    front           {{ type empty; }}
    back            {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        (case_dir / "0" / "nut").write_text(
            f"""/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \    /   O peration     | Version:  10                                    |
|   \  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      nut;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -1 0 0 0 0];
internalField   uniform 0.0;
boundaryField
{{
    inlet           {{ type calculated; value uniform 0.0; }}
    plate           {{ type nutkWallFunction; value uniform 0.0; }}
    outer           {{ type calculated; value uniform 0.0; }}
    axis            {{ type empty; }}
    front           {{ type empty; }}
    back            {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

    def _generate_airfoil_flow(self, case_dir: Path, task_spec: TaskSpec) -> None:
        """生成翼型外部流 case 文件 (simpleFoam steady k-omega SST).

        适用于:
        - NACA 0012 Airfoil External Flow (AIRFOIL, EXTERNAL, STEADY, Re=3e6)
        """
        (case_dir / "system").mkdir(parents=True, exist_ok=True)
        (case_dir / "constant").mkdir(parents=True, exist_ok=True)
        (case_dir / "0").mkdir(parents=True, exist_ok=True)

        Re = float(task_spec.Re or 3000000)
        chord = 1.0  # chord length
        U_inf = 1.0  # freestream velocity
        nu_val = U_inf * chord / Re

        # Rectangular tunnel with internal cylinder baffle (D=0.12) approximating airfoil.
        # x: [-5, 7], y: [-0.5, 0.5]
        (case_dir / "system" / "blockMeshDict").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\\\    /   O peration     | Version:  10                                    |
|   \\\\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      blockMeshDict;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

convertToMeters 1;

vertices
(
    (-5 -0.5 0)
    (7 -0.5 0)
    (7 0.5 0)
    (-5 0.5 0)
    (-5 -0.5 0.1)
    (7 -0.5 0.1)
    (7 0.5 0.1)
    (-5 0.5 0.1)
);

blocks
(
    hex (0 1 2 3 4 5 6 7) (240 80 1) simpleGrading (1 1 1)
);

edges
(
);

boundary
(
    inlet
    {
        type            patch;
        faces           ((0 4 7 3));
    }
    outlet
    {
        type            patch;
        faces           ((1 2 6 5));
    }
    lower
    {
        type            wall;
        faces           ((0 1 5 4));
    }
    upper
    {
        type            wall;
        faces           ((3 6 7 2));
    }
    front
    {
        type            empty;
        faces           ((0 3 2 1));
    }
    back
    {
        type            empty;
        faces           ((4 5 6 7));
    }
);

mergePatchPairs
(
);

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # system/topoSetDict -- cylinder cellZone via cylinderToCell
        (case_dir / "system" / "topoSetDict").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\\\    /   O peration     | Version:  10                                    |
|   \\\\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      topoSetDict;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

actions
(
    {
        name    airfoilCells;
        type    cellSet;
        action  new;
        source  cylinderToCell;
        sourceInfo
        {
            point1 (0 0 0);
            point2 (0 0 0.1);
            radius 0.06;
        }
    }
    {
        name    airfoilZone;
        type    cellZoneSet;
        action  new;
        source  setToCellZone;
        sourceInfo
        {
            set airfoilCells;
        }
    }
    {
        name    airfoilAllFaces;
        type    faceSet;
        action  new;
        source  cellToFace;
        sourceInfo
        {
            set airfoilCells;
            option all;
        }
    }
    {
        name    airfoilInternalFaces;
        type    faceSet;
        action  new;
        source  cellToFace;
        sourceInfo
        {
            set airfoilCells;
            option both;
        }
    }
    {
        name    airfoilBaffleFaces;
        type    faceSet;
        action  new;
        source  faceToFace;
        sourceInfo
        {
            set airfoilAllFaces;
        }
    }
    {
        name    airfoilBaffleFaces;
        type    faceSet;
        action  delete;
        source  faceToFace;
        sourceInfo
        {
            set airfoilInternalFaces;
        }
    }
    {
        name    airfoilBaffleZone;
        type    faceZoneSet;
        action  new;
        source  setsToFaceZone;
        sourceInfo
        {
            faceSet airfoilBaffleFaces;
            cellSet airfoilCells;
            flip false;
        }
    }
);

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # system/createBafflesDict -- converts internal faceZone to wall patch "airfoil"
        (case_dir / "system" / "createBafflesDict").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\\\    /   O peration     | Version:  10                                    |
|   \\\\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      createBafflesDict;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

internalFacesOnly true;

baffles
{
    airfoilBaffleZone
    {
        type faceZone;
        zoneName airfoilBaffleZone;
        patches
        {
            owner
            {
                name airfoil;
                type wall;
            }
            neighbour
            {
                name airfoil;
                type wall;
            }
        }
    }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )
        (case_dir / "constant" / "physicalProperties").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
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
nu              [0 2 -1 0 0 0 0] {nu_val:.6e};

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        (case_dir / "constant" / "turbulenceProperties").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      turbulenceProperties;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

simulationType  RAS;
RAS
{
    RASModel      kOmegaSST;
    turbulence    on;
    printCoeffs   on;
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        (case_dir / "system" / "controlDict").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      controlDict;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

application     simpleFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         2000;
deltaT          1;
writeControl    runTime;
writeInterval   200;
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

        (case_dir / "system" / "fvSchemes").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSchemes;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

ddtSchemes { default steadyState; }
gradSchemes { default Gauss linear; }
divSchemes {
    default none;
    div(phi,U) Gauss linearUpwind grad(U);
    div(phi,k) Gauss linearUpwind grad(k);
    div(phi,epsilon) Gauss linearUpwind grad(epsilon);
    div(phi,omega) Gauss linearUpwind grad(omega);
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
wallDist
{
    method meshWave;
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        (case_dir / "system" / "fvSolution").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
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
    p { solver GAMG; smoother GaussSeidel; tolerance 1e-7; relTol 0.001; }
    pFinal { $p; relTol 0; }
    U { solver PBiCGStab; preconditioner DILU; tolerance 1e-8; relTol 0.001; }
    UFinal { $U; relTol 0; }
    k { solver PBiCGStab; preconditioner DILU; tolerance 1e-8; relTol 0.001; }
    epsilon { solver PBiCGStab; preconditioner DILU; tolerance 1e-7; relTol 0.001; }
    omega { solver PBiCGStab; preconditioner DILU; tolerance 1e-8; relTol 0.001; }
}

SIMPLE
{
    nNonOrthogonalCorrectors 2;
    residualControl { U 1e-6; p 1e-5; k 1e-6; epsilon 1e-6; omega 1e-6; }
}

relaxationFactors
{
    equations { U 0.95; k 0.9; epsilon 0.9; omega 0.9; }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        Ux = U_inf
        (case_dir / "0" / "U").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volVectorField;
    location    "0";
    object      U;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 1 -1 0 0 0 0];
internalField   uniform ({Ux} 0 0);
boundaryField
{{
    inlet    {{ type fixedValue; value uniform ({Ux} 0 0); }}
    outlet   {{ type zeroGradient; }}
    airfoil  {{ type noSlip; }}
    upper    {{ type noSlip; }}
    lower    {{ type noSlip; }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        (case_dir / "0" / "p").write_text(
            """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\//     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
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
    inlet    { type zeroGradient; }
    outlet   { type fixedValue; value uniform 0; }
    airfoil  { type zeroGradient; }
    upper    { type zeroGradient; }
    lower    { type zeroGradient; }
    front { type empty; }
    back  { type empty; }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 0/k — turbulent kinetic energy
        (case_dir / "0" / "k").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      k;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -2 0 0 0 0];
internalField   uniform 0.001;
boundaryField
{{
    inlet    {{ type fixedValue; value uniform 0.001; }}
    outlet   {{ type zeroGradient; }}
    airfoil  {{ type kLowReWallFunction; value uniform 0; }}
    upper    {{ type kLowReWallFunction; value uniform 0; }}
    lower    {{ type kLowReWallFunction; value uniform 0; }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 0/omega — specific dissipation rate
        (case_dir / "0" / "omega").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      omega;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 0 -1 0 0 0 0];
internalField   uniform 1000.0;
boundaryField
{{
    inlet    {{ type fixedValue; value uniform 1000.0; }}
    outlet   {{ type zeroGradient; }}
    airfoil  {{ type omegaWallFunction; value uniform 1.0; }}
    upper    {{ type omegaWallFunction; value uniform 1.0; }}
    lower    {{ type omegaWallFunction; value uniform 1.0; }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        # 0/nut — turbulent viscosity
        (case_dir / "0" / "nut").write_text(
            f"""\
/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      nut;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -1 0 0 0 0];
internalField   uniform 0.0;
boundaryField
{{
    inlet    {{ type calculated; value uniform 0; }}
    outlet   {{ type calculated; value uniform 0; }}
    airfoil  {{ type nutkWallFunction; value uniform 0; }}
    upper    {{ type nutkWallFunction; value uniform 0; }}
    lower    {{ type nutkWallFunction; value uniform 0; }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

    def _render_bfs_block_mesh_dict(
        self, task_spec: TaskSpec, H: float, channel_height: float,
        ncx: int = 40, ncy: int = 20,
    ) -> str:
        """渲染简化 BFS 的 blockMeshDict（单矩形通道，简单几何）。

        使用单矩形通道近似 BFS（无 step 几何细节），
        用于 Phase 2 Grid Refinement Study。
        ncx × ncy: X方向 × Y方向 cell 数（默认 40×20）。
        """
        x_min = -10.0 * H
        x_max = 30.0 * H
        y_min = 0.0
        y_max = channel_height
        z_min = 0.0
        z_max = 0.1 * H

        return f"""\
/*--------------------------------*- C++ -*---------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  10                                    |
|   \\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      blockMeshDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

convertToMeters 1;

vertices
(
    ({x_min} {y_min} {z_min})
    ({x_max} {y_min} {z_min})
    ({x_max} {y_max} {z_min})
    ({x_min} {y_max} {z_min})
    ({x_min} {y_min} {z_max})
    ({x_max} {y_min} {z_max})
    ({x_max} {y_max} {z_max})
    ({x_min} {y_max} {z_max})
);

blocks
(
    hex (0 1 2 3 4 5 6 7) ({ncx} {ncy} 1) simpleGrading (1 1 1)
);

edges
(
);

boundary
(
    inlet
    {{
        type            patch;
        faces           ((0 4 7 3));
    }}
    outlet
    {{
        type            patch;
        faces           ((1 2 6 5));
    }}
    lower_wall
    {{
        type            wall;
        faces           ((0 1 5 4));
    }}
    upper_wall
    {{
        type            wall;
        faces           ((3 7 6 2));
    }}
    front
    {{
        type            empty;
        faces           ((0 3 2 1));
    }}
    back
    {{
        type            empty;
        faces           ((4 5 6 7));
    }}
);

mergePatchPairs
(
);

// ************************************************************************* //
"""

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
    ) -> Tuple[bool, str]:
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

        Recursive walk of all subdirectories.
        Strips host permissions to avoid container write issues.
        All files set to 0644, all dirs set to 0755.
        """
        import io as _io, tarfile as _tarfile, os as _os
        buf = _io.BytesIO()
        with _tarfile.open(fileobj=buf, mode="w", format=_tarfile.PAX_FORMAT) as tar:
            for root, dirs, files in _os.walk(src_dir):
                dirs.sort()
                files.sort()
                for fname in sorted(files):
                    fpath = Path(root) / fname
                    arcname = str(fpath.relative_to(src_dir))
                    info = _tarfile.TarInfo(arcname)
                    info.size = fpath.stat().st_size
                    info.mode = 0o644
                    info.mtime = fpath.stat().st_mtime
                    info.type = _tarfile.REGTYPE
                    tar.addfile(info, fileobj=fpath.open("rb"))
                for dname in sorted(dirs):
                    dpath = Path(root) / dname
                    arcname = str(dpath.relative_to(src_dir)) + "/"
                    info = _tarfile.TarInfo(arcname)
                    info.size = 0
                    info.mode = 0o755
                    info.type = _tarfile.DIRTYPE
                    tar.addfile(info)
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

    def _copy_postprocess_fields(
        self, container: Any, case_cont_dir: str, case_host_dir: Path
    ) -> None:
        """从容器内复制 postProcess -func writeObjects 输出的场文件到宿主机。

        postProcess 在 latestTime 目录写出 U, Cx, Cy, (T) 等场文件，
        将这些文件复制到宿主机的对应时间目录。
        """
        try:
            # 找到容器内最新时间目录（数字目录）
            result = container.exec_run(
                cmd=["bash", "-c", f"ls {case_cont_dir}/ 2>/dev/null | grep -E '^[0-9]' | sort -n | tail -1"]
            )
            latest_time = result.output.decode().strip()
            if not latest_time:
                return

            latest_cont_dir = f"{case_cont_dir}/{latest_time}"

            # 场文件：U 和 Cx/Cy 必选，T 可选
            field_files = ["U", "Cx", "Cy", "T"]

            for field_file in field_files:
                cont_path = f"{latest_cont_dir}/{field_file}"
                host_time_dir = case_host_dir / latest_time
                host_path = host_time_dir / field_file
                self._copy_file_from_container(container, cont_path, host_path)
        except Exception:
            pass  # 静默失败，后续解析会处理无数据的情况

    # ------------------------------------------------------------------
    # Log parsing
    # ------------------------------------------------------------------

    def _parse_solver_log(self, log_path: Path, solver_name: str = "icoFoam", task_spec: Optional[TaskSpec] = None) -> Tuple[Dict[str, float], Dict[str, Any]]:
        """解析 solver log 文件，提取最终（末次迭代）残差和关键物理量。

        Args:
            log_path: log 文件路径
            solver_name: "icoFoam" 或 "simpleFoam" 或 "buoyantSimpleFoam"
            task_spec: 任务规格，用于 case-specific 物理量解释
            solver_name: "icoFoam" 或 "simpleFoam"

        Returns:
            (residuals, key_quantities)
        """
        if not log_path.exists():
            return {}, {}

        text = log_path.read_text(encoding="utf-8", errors="replace")

        residuals: Dict[str, float] = {}
        key_quantities: Dict[str, Any] = {}

        if solver_name == "simpleFoam":
            # simpleFoam 格式:
            # "Solving for Ux, Initial residual = X, Final residual = Y, No Iterations Z"
            # 也可能有: "Solving for Ux, Initial residual = X, Final residual = Y"
            # 还有 turbulence: "Solving for k, Initial residual = X, Final residual = Y"
            pattern = re.compile(
                r"Solving for (\w+),.*?Initial residual\s*=\s*([\d.eE+-]+)"
            )
            for match in pattern.finditer(text):
                var = match.group(1)
                # 只保留最后一个匹配（最终迭代）
                residuals[var] = float(match.group(2))

            # 从最终迭代提取速度分量残差用于 key_quantities
            ux_matches = list(re.finditer(
                r"Solving for Ux,.*?Initial residual\s*=\s*([\d.eE+-]+)", text
            ))
            uy_matches = list(re.finditer(
                r"Solving for Uy,.*?Initial residual\s*=\s*([\d.eE+-]+)", text
            ))
            if ux_matches and uy_matches:
                ux_res = float(ux_matches[-1].group(1))
                uy_res = float(uy_matches[-1].group(1))
                key_quantities["U_residual_magnitude"] = (ux_res ** 2 + uy_res ** 2) ** 0.5

        else:
            # icoFoam 格式:
            # "Solving for <var>, Initial residual = X, Final residual = Y"
            for match in re.finditer(
                r"Solving for (\w+).*?Initial residual\s*=\s*([\d.eE+-]+)", text
            ):
                var = match.group(1)
                residuals[var] = float(match.group(2))

            # 关键物理量：末次时间步的最大速度
            ux_matches = list(re.finditer(
                r"Solving for Ux,.*?Initial residual\s*=\s*([\d.eE+-]+)", text
            ))
            uy_matches = list(re.finditer(
                r"Solving for Uy,.*?Initial residual\s*=\s*([\d.eE+-]+)", text
            ))
            if ux_matches and uy_matches:
                ux_res = float(ux_matches[-1].group(1))
                uy_res = float(uy_matches[-1].group(1))
                key_quantities["U_max_approx"] = max(ux_res, abs(uy_res))

        # 从 postProcessing/sets 目录读取 sample utility 输出的关键物理量
        post_dir = log_path.parent / "postProcessing"
        if post_dir.exists():
            sets_dir = post_dir / "sets"
            if sets_dir.exists():
                # 遍历所有时间目录
                for time_dir in sorted(sets_dir.iterdir()):
                    if time_dir.is_dir():
                        # 查找 sample 输出文件 (e.g., U_uCenterline, T_midPlaneT)
                        for sample_file in sorted(time_dir.iterdir()):
                            filename = sample_file.name
                            lines = sample_file.read_text(encoding="utf-8", errors="replace").splitlines()

                            # 解析 sample 文件格式:
                            # #   Time  x  y  z  Ux  Uy  Uz  (for vector fields)
                            # #   Time  x  y  z  T         (for scalar fields)
                            if filename.startswith("U_"):
                                # Velocity sample - extract Ux component for centerline profile
                                set_name = filename[2:]  # e.g., "uCenterline"
                                vals = []
                                y_coords = []
                                for line in lines:
                                    if line.startswith("#") or not line.strip():
                                        continue
                                    parts = line.split()
                                    # Format: time x y z Ux Uy Uz
                                    if len(parts) >= 6:
                                        try:
                                            y_coords.append(float(parts[2]))  # y coordinate
                                            vals.append(float(parts[4]))  # Ux component
                                        except ValueError:
                                            pass
                                if vals:
                                    # Use set name as key, e.g., "uCenterline"
                                    key_quantities[set_name] = vals
                                    # Also store y coordinates for profile matching
                                    key_quantities[f"{set_name}_y"] = y_coords

                            elif filename.startswith("T_"):
                                # Temperature sample - extract T component
                                set_name = filename[2:]  # e.g., "midPlaneT"
                                vals = []
                                y_coords = []
                                for line in lines:
                                    if line.startswith("#") or not line.strip():
                                        continue
                                    parts = line.split()
                                    # Format: time x y z T
                                    if len(parts) >= 5:
                                        try:
                                            y_coords.append(float(parts[2]))  # y coordinate
                                            vals.append(float(parts[4]))  # T value
                                        except ValueError:
                                            pass
                                if vals:
                                    key_quantities[set_name] = vals
                                    key_quantities[f"{set_name}_y"] = y_coords

        # Case-specific interpretation: 映射 sample 输出到 Gold Standard 期望的 quantity 名称
        if task_spec is not None:
            geom = task_spec.geometry_type
            name_lower = task_spec.name.lower()

            # LDC: uCenterline -> u_centerline (Gold Standard 格式)
            if geom == GeometryType.SIMPLE_GRID and ("lid" in name_lower or task_spec.Re < 2300):
                if "uCenterline" in key_quantities:
                    key_quantities["u_centerline"] = key_quantities["uCenterline"]
                    del key_quantities["uCenterline"]
                    if "uCenterline_y" in key_quantities:
                        key_quantities["u_centerline_y"] = key_quantities["uCenterline_y"]
                        del key_quantities["uCenterline_y"]

            # BFS: 从 wallProfile 计算再附着长度 Xr/H
            elif geom == GeometryType.BACKWARD_FACING_STEP:
                if "wallProfile" in key_quantities:
                    x_coords = key_quantities.get("wallProfile_x", [])
                    ux_vals = key_quantities.get("wallProfile", [])
                    if x_coords and ux_vals and len(x_coords) == len(ux_vals):
                        # 找再附着点: Ux 从负变正的第一个位置
                        reattachment_x = None
                        for i in range(1, len(ux_vals)):
                            if ux_vals[i-1] < 0 and ux_vals[i] >= 0:
                                # 线性插值找精确零交点
                                x1, x2 = x_coords[i-1], x_coords[i]
                                u1, u2 = ux_vals[i-1], ux_vals[i]
                                if u2 != u1:
                                    reattachment_x = x1 - u1 * (x2 - x1) / (u2 - u1)
                                else:
                                    reattachment_x = x1
                                break
                        if reattachment_x is not None:
                            H = 1.0  # step height
                            key_quantities["reattachment_length"] = reattachment_x / H
                    # 清理中间数据
                    for k in list(key_quantities.keys()):
                        if k.startswith("wallProfile"):
                            del key_quantities[k]

            # NC Cavity: 从 midPlaneT 计算 Nusselt number
            elif geom == GeometryType.NATURAL_CONVECTION_CAVITY:
                if "midPlaneT" in key_quantities:
                    T_vals = key_quantities.get("midPlaneT", [])
                    y_coords = key_quantities.get("midPlaneT_y", [])
                    if T_vals and y_coords and len(T_vals) == len(y_coords):
                        # Nu = -L * dT/dy |wall / dT_bulk
                        # 用壁面梯度 (y 最小处) 近似
                        # 找到 y 最小的点（热壁）及其邻点来计算梯度
                        min_y_idx = min(range(len(y_coords)), key=lambda i: y_coords[i])
                        if min_y_idx < len(T_vals) - 1:
                            dy = y_coords[min_y_idx + 1] - y_coords[min_y_idx]
                            dT = T_vals[min_y_idx + 1] - T_vals[min_y_idx]
                            if abs(dy) > 1e-10:
                                # 简化: Nu ≈ |dT/dy| * L / dT (取 L=1, dT=10K)
                                L = 1.0
                                dT_bulk = 10.0  # T_hot - T_cold
                                grad_T = abs(dT / dy) if dT != 0 else 0.0
                                key_quantities["nusselt_number"] = grad_T * L / dT_bulk
                    # 清理中间数据
                    for k in list(key_quantities.keys()):
                        if k.startswith("midPlaneT"):
                            del key_quantities[k]

        return residuals, key_quantities

    # ------------------------------------------------------------------
    # writeObjects field extraction
    # ------------------------------------------------------------------

    def _parse_writeobjects_fields(
        self,
        case_dir: Path,
        solver_name: str,
        task_spec: Optional[TaskSpec],
        key_quantities: Dict[str, Any],
    ) -> Dict[str, Any]:
        """从 postProcess writeObjects 输出的场文件提取 case-specific 关键物理量。

        postProcess -func writeObjects -latestTime 在最新时间目录写出:
        - U: vector field (Ux, Uy, Uz) for each cell
        - Cx, Cy, Cz: cell centre coordinates
        - p: pressure field
        这些文件格式为 OpenFOAM internalField nonuniform List<...>。

        Returns:
            key_quantities updated with u_centerline, reattachment_length, nusselt_number
        """
        if task_spec is None:
            return key_quantities

        # 找到最新时间目录
        time_dirs = []
        for item in case_dir.iterdir():
            if item.is_dir():
                try:
                    t = float(item.name)
                    time_dirs.append((t, item))
                except ValueError:
                    pass
        if not time_dirs:
            return key_quantities

        latest_t, latest_dir = max(time_dirs, key=lambda x: x[0])

        # 检查是否有 U 和 Cx/Cy 文件
        u_path = latest_dir / "U"
        cx_path = latest_dir / "Cx"
        cy_path = latest_dir / "Cy"
        if not all(p.exists() for p in [u_path, cx_path, cy_path]):
            return key_quantities

        # 读取场数据
        cxs = self._read_openfoam_scalar_field(cx_path)
        cys = self._read_openfoam_scalar_field(cy_path)
        u_vecs = self._read_openfoam_vector_field(u_path, len(cxs))

        if len(cxs) != len(cys) or len(cxs) != len(u_vecs):
            return key_quantities

        geom = task_spec.geometry_type
        name_lower = task_spec.name.lower()

        # LDC / SIMPLE_GRID: 提取 x=0.5 (normalized) 的中心线速度剖面
        if geom == GeometryType.SIMPLE_GRID and ("lid" in name_lower or task_spec.Re < 2300):
            key_quantities = self._extract_ldc_centerline(
                cxs, cys, u_vecs, task_spec, key_quantities
            )

        # BFS: 提取 y=0.5 (wall) 的速度剖面找再附着长度
        elif geom == GeometryType.BACKWARD_FACING_STEP:
            key_quantities = self._extract_bfs_reattachment(
                cxs, cys, u_vecs, task_spec, key_quantities
            )

        # NC Cavity: 提取 mid-plane 温度剖面算 Nusselt number
        elif geom == GeometryType.NATURAL_CONVECTION_CAVITY:
            t_path = latest_dir / "T"
            if t_path.exists():
                t_vals = self._read_openfoam_scalar_field(t_path)
                key_quantities = self._extract_nc_nusselt(
                    cxs, cys, t_vals, task_spec, key_quantities
                )

        return key_quantities

    @staticmethod
    def _read_openfoam_scalar_field(filepath: Path) -> List[float]:
        """解析 OpenFOAM internalField nonuniform List<scalar> 文件。"""
        with filepath.open() as f:
            lines = f.readlines()
        # 找 count 行（紧跟在 internalField nonuniform List<scalar> 之后）
        count_line = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and stripped[0].isdigit():
                count_line = i
                n = int(stripped.rstrip(';'))
                break
        if count_line is None:
            return []
        # count 后第一个非空行是 '('，数据从下一行开始
        data_start = count_line + 2
        data_end = data_start + n
        vals = []
        for j in range(n):
            line = lines[data_start + j].strip()
            if not line or line == ')':
                break
            try:
                vals.append(float(line.rstrip(';')))
            except ValueError:
                break
        return vals

    @staticmethod
    def _read_openfoam_vector_field(filepath: Path, n_expected: int) -> List[Tuple]:
        """解析 OpenFOAM internalField nonuniform List<vector> 文件。"""
        with filepath.open() as f:
            lines = f.readlines()
        # 找 count 行
        count_line = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and stripped[0].isdigit():
                count_line = i
                break
        if count_line is None:
            return []
        # 数据从 count + 2 行开始 (跳过 '(')
        data_start = count_line + 2
        vecs = []
        for j in range(min(n_expected, 100000)):
            line = lines[data_start + j].strip()
            if not line or line in (')', 'boundaryField'):
                break
            inner = line.strip('();')
            parts = inner.split()
            if len(parts) >= 3:
                try:
                    vecs.append((float(parts[0]), float(parts[1]), float(parts[2])))
                except ValueError:
                    break
        return vecs

    @staticmethod
    def _extract_ldc_centerline(
        cxs: List[float],
        cys: List[float],
        u_vecs: List[Tuple],
        task_spec: TaskSpec,
        key_quantities: Dict[str, Any],
    ) -> Dict[str, Any]:
        """LDC: 提取 x=0.5 中心线速度剖面，对应 Ghia 1982 标准值。

        Cavity mesh: x∈[0,0.1], y∈[0,0.1], z∈[0,0.1]
        Ghia 1982 标准: x_norm=0.5 → x_actual=0.05m
        网格 x-cell centers: 0.0025, 0.0075, ..., 0.0975 (步长 0.005)
        目标 x=0.05 落在 cells 9-10 (cx=0.0475 和 0.0525)，取平均
        """
        # x=0.05m = normalized x=0.5
        x_target = 0.05
        x_tol = 0.006  # 半格宽 0.0025 × 1.2

        from collections import defaultdict
        y_groups: Dict[float, List[float]] = defaultdict(list)

        for i in range(len(cxs)):
            if abs(cxs[i] - x_target) < x_tol:
                yr = round(cys[i], 4)
                y_groups[yr].append(u_vecs[i][0])  # Ux component

        if not y_groups:
            return key_quantities

        # 建立 [y_norm, avg_Ux] profile，插值到 Ghia 1982 位置
        ghia_y = [0.0000, 0.0625, 0.1250, 0.1875, 0.2500, 0.3125, 0.3750,
                  0.4375, 0.5000, 0.5625, 0.6250, 0.6875, 0.7500, 0.8125,
                  0.8750, 0.9375, 1.0000]

        sorted_y = sorted(y_groups.keys())
        profile = [(yr / 0.1, sum(y_groups[yr]) / len(y_groups[yr])) for yr in sorted_y]

        # 线性插值到 Ghia y 位置
        u_centerline = []
        for g_y in ghia_y:
            p_below = None
            p_above = None
            for p_y, p_u in profile:
                if p_y <= g_y:
                    p_below = (p_y, p_u)
                if p_y >= g_y and p_above is None:
                    p_above = (p_y, p_u)
            if p_below and p_above and p_above[0] != p_below[0]:
                frac = (g_y - p_below[0]) / (p_above[0] - p_below[0])
                sim_u = p_below[1] + frac * (p_above[1] - p_below[1])
            elif p_below:
                sim_u = p_below[1]
            elif p_above:
                sim_u = p_above[1]
            else:
                sim_u = 0.0
            u_centerline.append(sim_u)

        key_quantities["u_centerline"] = u_centerline
        key_quantities["u_centerline_y"] = ghia_y
        return key_quantities

    @staticmethod
    def _extract_bfs_reattachment(
        cxs: List[float],
        cys: List[float],
        u_vecs: List[Tuple],
        task_spec: TaskSpec,
        key_quantities: Dict[str, Any],
    ) -> Dict[str, Any]:
        """BFS: 从 y=0.5 (normalized) wall profile 找 Ux 零交点计算再附着长度。"""
        # BFS mesh: step at x=0, step height H=1, domain x∈[-1,8], y∈[0,3]
        # y=0.5 normalized = y_actual = 0.5*H = 0.5 (in mesh coords)
        y_target = 0.5
        y_tol = 0.15  # capture wall BL region

        from collections import defaultdict
        x_groups: Dict[float, List[float]] = defaultdict(list)

        for i in range(len(cxs)):
            if abs(cys[i] - y_target) < y_tol:
                xr = round(cxs[i], 3)
                x_groups[xr].append(u_vecs[i][0])  # Ux

        if not x_groups:
            return key_quantities

        sorted_x = sorted(x_groups.keys())
        x_ux_pairs = [(xr, sum(x_groups[xr]) / len(x_groups[xr])) for xr in sorted_x]

        # 找 Ux 零交点（从负变正）
        reattachment_x = None
        for j in range(1, len(x_ux_pairs)):
            x1, u1 = x_ux_pairs[j - 1]
            x2, u2 = x_ux_pairs[j]
            if u1 < 0 and u2 >= 0:
                if abs(u2 - u1) > 1e-10:
                    reattachment_x = x1 - u1 * (x2 - x1) / (u2 - u1)
                else:
                    reattachment_x = x1
                break

        if reattachment_x is not None:
            H = 1.0  # step height
            key_quantities["reattachment_length"] = reattachment_x / H

        return key_quantities

    @staticmethod
    def _extract_nc_nusselt(
        cxs: List[float],
        cys: List[float],
        t_vals: List[float],
        task_spec: TaskSpec,
        key_quantities: Dict[str, Any],
    ) -> Dict[str, Any]:
        """NC Cavity: 从 mid-plane 温度剖面计算 Nusselt number。"""
        if not cxs or not cys or not t_vals:
            return key_quantities

        # Natural-convection cavity blockMesh uses x in [0, 1], so mid-plane is x=0.5
        x_target = 0.5 * (min(cxs) + max(cxs))
        unique_x = sorted({round(x, 6) for x in cxs})
        if len(unique_x) >= 2:
            dx = min(unique_x[i + 1] - unique_x[i] for i in range(len(unique_x) - 1))
            x_tol = max(0.6 * dx, 1e-6)
        else:
            x_tol = 0.015

        from collections import defaultdict
        y_groups: Dict[float, List[float]] = defaultdict(list)

        for i in range(min(len(cxs), len(cys), len(t_vals))):
            if abs(cxs[i] - x_target) < x_tol:
                yr = round(cys[i], 4)
                y_groups[yr].append(t_vals[i])

        if not y_groups:
            return key_quantities

        sorted_y = sorted(y_groups.keys())
        y_t_pairs = [(yr, sum(y_groups[yr]) / len(y_groups[yr])) for yr in sorted_y]

        # 找热壁（y 最小处）并计算壁面梯度
        if len(y_t_pairs) >= 2:
            y0, T0 = y_t_pairs[0]
            y1, T1 = y_t_pairs[1]
            dy = y1 - y0
            if abs(dy) > 1e-10:
                dT = T1 - T0
                L = 1.0
                dT_bulk = 10.0  # ΔT hot-cold
                grad_T = abs(dT / dy)
                key_quantities["nusselt_number"] = grad_T * L / dT_bulk

        # 存储 mid-plane T profile
        key_quantities["midPlaneT"] = [T for _, T in y_t_pairs]
        key_quantities["midPlaneT_y"] = [y for y, _ in y_t_pairs]

        return key_quantities

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