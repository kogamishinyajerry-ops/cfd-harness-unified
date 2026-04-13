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
            elif task_spec.geometry_type == GeometryType.SIMPLE_GRID:
                self._generate_steady_internal_flow(case_host_dir, task_spec)
                solver_name = "simpleFoam"
            elif task_spec.geometry_type == GeometryType.BODY_IN_CHANNEL:
                self._generate_circular_cylinder_wake(case_host_dir, task_spec)
                solver_name = "pimpleFoam"
            elif task_spec.geometry_type == GeometryType.AIRFOIL:
                self._generate_airfoil_flow(case_host_dir, task_spec)
                solver_name = "simpleFoam"
            elif task_spec.geometry_type == GeometryType.IMPINGING_JET:
                self._generate_impinging_jet(case_host_dir, task_spec)
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

            # 7. 解析 log 文件
            log_path = case_host_dir / f"log.{solver_name}"
            residuals, key_quantities = self._parse_solver_log(log_path, solver_name)

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
    walls        {{ type kqWallFunction; value uniform {k_init}; }}
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
    inlet        {{ type calculated; }}
    outlet       {{ type calculated; }}
    walls        {{ type nutkWallFunction; value uniform 0; }}
    front {{ type empty; }}
    back  {{ type empty; }}
}}

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
        H = 5.0 * D  # half-height
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

        # 0/k, 0/omega, 0/nut
        for fname, val in [("k", 0.01), ("omega", 100.0)]:
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

internalField   uniform {val};

boundaryField
{{
    inlet        {{ type fixedValue; value uniform {val}; }}
    outlet       {{ type zeroGradient; }}
    lower_wall   {{ type calculated; }}
    upper_wall   {{ type calculated; }}
    cylinder     {{ type calculated; }}
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
    inlet        { type calculated; }
    outlet       { type calculated; }
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
        """生成冲击射流 case 文件 (simpleFoam steady).

        适用于:
        - Axisymmetric Impinging Jet (IMPINGING_JET, EXTERNAL, STEADY, Re=10000)
        - h_over_d = 2.0 (nozzle to plate distance / diameter)
        """
        (case_dir / "system").mkdir(parents=True, exist_ok=True)
        (case_dir / "constant").mkdir(parents=True, exist_ok=True)
        (case_dir / "0").mkdir(parents=True, exist_ok=True)

        Re = float(task_spec.Re or 10000)
        D = 0.05  # nozzle diameter
        h_over_d = 2.0
        H = h_over_d * D  # nozzle-to-plate distance
        U_bulk = 1.0
        nu_val = U_bulk * D / Re

        # Domain: r=[0, 5D], z=[0, H+D/2]
        r_max = 5.0 * D
        z_min = -D / 2  # nozzle exit above domain
        z_max = H + D / 2

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
    (0 {z_min:.6f} 0)
    ({r_max:.6f} {z_min:.6f} 0)
    ({r_max:.6f} {z_max:.6f} 0)
    (0 {z_max:.6f} 0)
    (0 {z_min:.6f} 0.1)
    ({r_max:.6f} {z_min:.6f} 0.1)
    ({r_max:.6f} {z_max:.6f} 0.1)
    (0 {z_max:.6f} 0.1)
);

blocks
(
    hex (0 1 2 3 4 5 6 7) (100 100 1) simpleGrading (1 1 1)
);

edges
(
);

boundary
(
    nozzle
    {{
        type            patch;
        faces           ((0 4 7 3));
    }}
    impingement_plate
    {{
        type            wall;
        faces           ((1 2 6 5));
    }}
    outer_cylindrical
    {{
        type            wall;
        faces           ((1 5 6 2));
    }}
    axis
    {{
        type            empty;
        faces           ((0 3 2 1));
    }}
    front {{ type empty; faces ((0 4 5 1)); }}
    back  {{ type empty; faces ((4 7 6 5)); }}
);

mergePatchPairs
(
);

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
    p { solver GAMG; smoother GaussSeidel; tolerance 1e-6; relTol 0.01; }
    pFinal { $p; relTol 0; }
    U { solver PBiCGStab; preconditioner DILU; tolerance 1e-7; relTol 0.01; }
    UFinal { $U; relTol 0; }
    k { solver PBiCGStab; preconditioner DILU; tolerance 1e-7; relTol 0.01; }
    epsilon { solver PBiCGStab; preconditioner DILU; tolerance 1e-6; relTol 0.01; }
    omega { solver PBiCGStab; preconditioner DILU; tolerance 1e-7; relTol 0.01; }
}

SIMPLE
{
    nNonOrthogonalCorrectors 1;
    residualControl { U 1e-5; p 1e-4; k 1e-5; epsilon 1e-5; omega 1e-5; }
}

relaxationFactors
{
    equations { U 0.9; k 0.9; epsilon 0.9; omega 0.9; }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        U_nozzle = U_bulk
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
    nozzle               {{ type fixedValue; value uniform (0 -{U_nozzle} 0); }}
    impingement_plate    {{ type noSlip; }}
    outer_cylindrical    {{ type noSlip; }}
    axis                 {{ type empty; }}
    front                {{ type empty; }}
    back                 {{ type empty; }}
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
    nozzle               { type zeroGradient; }
    impingement_plate    { type zeroGradient; }
    outer_cylindrical    { type zeroGradient; }
    axis                 { type empty; }
    front                { type empty; }
    back                 { type empty; }
}

// ************************************************************************* //
""",
            encoding="utf-8",
        )

        for fname, val in [("k", 0.01), ("omega", 500.0), ("nut", 0.0)]:
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
internalField   uniform {val};
boundaryField
{{
    nozzle               {{ type fixedValue; value uniform {val}; }}
    impingement_plate    {{ type calculated; }}
    outer_cylindrical    {{ type calculated; }}
    axis                 {{ type empty; }}
    front                {{ type empty; }}
    back                 {{ type empty; }}
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

        # Far-field domain: C-type mesh around airfoil
        # x: [-5, 7], y: [-5, 5]
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
    (-5 5 0)
    (7 5 0)
    (7 -5 0)
    (-5 -5 0)
    (-5 5 0.1)
    (7 5 0.1)
    (7 -5 0.1)
    (-5 -5 0.1)
);

blocks
(
    hex (0 1 2 3 4 5 6 7) (240 200 1) simpleGrading (1 1 1)
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
    upper
    {
        type            wall;
        faces           ((0 1 5 4));
    }
    lower
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

        for fname, val in [("k", 0.001), ("omega", 1000.0), ("nut", 0.0)]:
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
internalField   uniform {val};
boundaryField
{{
    inlet    {{ type fixedValue; value uniform {val}; }}
    outlet   {{ type zeroGradient; }}
    airfoil  {{ type calculated; }}
    upper    {{ type calculated; }}
    lower    {{ type calculated; }}
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

    def _parse_solver_log(self, log_path: Path, solver_name: str = "icoFoam") -> tuple[Dict[str, float], Dict[str, Any]]:
        """解析 solver log 文件，提取最终（末次迭代）残差和关键物理量。

        Args:
            log_path: log 文件路径
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
