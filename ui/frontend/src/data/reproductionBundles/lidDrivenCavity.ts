// Reproduction bundle — lid_driven_cavity (Re=100)
//
// DEC-V61-049 batch B: novice reproduction required complete OpenFOAM
// dictionaries on the page itself. Previously the /learn/lid_driven_cavity
// page described editing files ("$EDITOR system/blockMeshDict") without
// providing their contents, so a first-semester CFD student could not
// reproduce the run without either inventing the files or reverse-
// engineering src/foam_agent_adapter.py. This bundle mirrors exactly
// what foam_agent_adapter.py:_generate_lid_driven_cavity emits for
// Re=100, so "copy these 8 files" gives the audit-grade run.
//
// Drift prevention: if the generator changes, this bundle goes stale.
// The right long-term fix is to have the bundle *generated* from the
// same templates, but that is a structural change outside pilot scope.
// For now, the bundle is manually synchronized with the generator as
// of commit 920b4b0 (DEC-V61-049 batch A alignment).

export interface ReproductionBundle {
  intro: string;
  usage: string;
  files: Array<{
    path: string;
    role: string;
    content: string;
  }>;
}

export const LDC_REPRODUCTION_BUNDLE: ReproductionBundle = {
  intro: `下面是本仓库 generator 在 Re=100 下 emit 给 OpenFOAM 10 simpleFoam 的 8 个核心 case 文件原文。和 src/foam_agent_adapter.py:_generate_lid_driven_cavity 逐字节对齐（同步于 commit 920b4b0），直接复制就能跑出 audit-grade 129×129 解，不用再从 icoFoam tutorial 反向凑。`,
  usage: `操作流程：(1) 空目录下建 0/、constant/、system/ 三个子目录；(2) 按下表逐个文件粘贴（文件路径列就是放哪里）；(3) 跑 blockMesh → simpleFoam → 自动结束（residualControl 在 p/U 都 <1e-5 时停）；(4) 取样结果出现在 postProcessing/sets/<time>/uCenterline_U.xy（controlDict 里 functions 块自动写的，每 500 iter 一版）；(5) 想对齐 Ghia Table I 的 17 点 gold 做 point-wise L2，可以跑 postProcess -func sampleDict -time <time> 用下面的 system/sampleDict 做二次采样。`,
  files: [
    {
      path: "system/blockMeshDict",
      role: "定义方腔几何 + 129×129 网格 + 5 个 patch。convertToMeters 0.1 让物理 domain = 0.1m × 0.1m × 0.01m（薄 2D 切片），vertices 在单位立方顶点。",
      content: `/*--------------------------------*- C++ -*---------------------------------*\\
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
    object      blockMeshDict;
}
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
    hex (0 1 2 3 4 5 6 7) (129 129 1) simpleGrading (1 1 1)
);

edges
(
);

boundary
(
    lid
    {
        type            wall;
        faces           ((3 7 6 2));
    }
    wall1
    {
        type            wall;
        faces           ((0 4 7 3));
    }
    wall2
    {
        type            wall;
        faces           ((1 2 6 5));
    }
    bottom
    {
        type            wall;
        faces           ((0 1 5 4));
    }
    frontAndBack
    {
        type            empty;
        faces
        (
            (0 3 2 1)
            (4 5 6 7)
        );
    }
);

mergePatchPairs
(
);

// ************************************************************************* //
`,
    },
    {
      path: "constant/physicalProperties",
      role: "层流不可压缩流体物性。nu=0.001 给 Re = U·L/ν = 1·0.1/0.001 = 100（物理长度 L=0.1m 来自 convertToMeters）。OpenFOAM 10 的 simpleFoam 读 physicalProperties；OpenFOAM ≤9 读 constant/transportProperties，语法相同。",
      content: `/*--------------------------------*- C++ -*---------------------------------*\\
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
    object      physicalProperties;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

transportModel  Newtonian;

nu              [0 2 -1 0 0 0 0] 0.001;

// ************************************************************************* //
`,
    },
    {
      path: "constant/momentumTransport",
      role: "OpenFOAM 10 的 simpleFoam 强制要求此文件。simulationType=laminar 告诉 solver 不启用 RANS/LES 闭合。OpenFOAM ≤9 的等价文件是 constant/turbulenceProperties + RASModel laminar。",
      content: `/*--------------------------------*- C++ -*---------------------------------*\\
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
    object      momentumTransport;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

simulationType  laminar;

// ************************************************************************* //
`,
    },
    {
      path: "system/controlDict",
      role: "solver + 迭代/时间控制 + functions 块（自动采 uCenterline 129 点 + 记录 residuals）。SIMPLE 里 deltaT 是 iter 计数，writeInterval=2000 只写末态场，sample function object 独立 writeInterval=500。",
      content: `/*--------------------------------*- C++ -*---------------------------------*\\
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

endTime         2000;

deltaT          1;

writeControl    timeStep;

writeInterval   2000;

purgeWrite      0;

writeFormat     ascii;

writePrecision  6;

writeCompression off;

timeFormat      general;

timePrecision   6;

runTimeModifiable true;

functions
{
    sample
    {
        type            sets;
        libs            ("libsampling.so");
        writeControl    timeStep;
        writeInterval   500;

        interpolationScheme cellPoint;
        setFormat       raw;

        fields          (U p);

        sets
        (
            uCenterline
            {
                type        lineUniform;
                axis        y;
                start       (0.05 0.0   0.005);
                end         (0.05 0.1   0.005);
                nPoints     129;
            }
        );
    }

    residuals
    {
        type            residuals;
        libs            ("libutilityFunctionObjects.so");
        writeControl    timeStep;
        writeInterval   1;
        fields          (U p);
    }
}

// ************************************************************************* //
`,
    },
    {
      path: "system/fvSchemes",
      role: "离散格式。ddtSchemes steadyState 去掉时间项；div(phi,U) 用 bounded Gauss limitedLinearV 1 — 二阶精度带通量限制器，比 upwind（一阶，过耗散）和 linear（二阶无限制，易震荡）都合适稳态层流。",
      content: `/*--------------------------------*- C++ -*---------------------------------*\\
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
    div(phi,U)      bounded Gauss limitedLinearV 1;
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

wallDist
{
    method          meshWave;
}

// ************************************************************************* //
`,
    },
    {
      path: "system/fvSolution",
      role: "线性求解器 + SIMPLE 迭代控制 + 压力参考 + 松弛因子。consistent yes 启用 SIMPLEC（稳定性好于 SIMPLE），pRefCell/pRefValue 锁死 pressure 零点，residualControl 在达到 1e-5 时自动停。URF U=0.9 / p=0.3 是本仓库实测可用组合。",
      content: `/*--------------------------------*- C++ -*---------------------------------*\\
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
        tolerance       1e-06;
        relTol          0.1;
        smoother        GaussSeidel;
    }

    U
    {
        solver          smoothSolver;
        smoother        GaussSeidel;
        tolerance       1e-05;
        relTol          0.1;
        nSweeps         1;
    }
}

SIMPLE
{
    nNonOrthogonalCorrectors 0;
    consistent      yes;
    pRefCell        0;
    pRefValue       0;
    residualControl
    {
        p               1e-5;
        U               1e-5;
    }
}

relaxationFactors
{
    equations
    {
        U               0.9;
    }
    fields
    {
        p               0.3;
    }
}

// ************************************************************************* //
`,
    },
    {
      path: "0/U",
      role: "速度初场 + 边界条件。dimensions [0 1 -1 0 0 0 0] = m/s。lid 是唯一 momentum source；其余三面 noSlip（等价 fixedValue (0 0 0)）；frontAndBack empty 伪 2D。",
      content: `/*--------------------------------*- C++ -*---------------------------------*\\
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
    bottom
    {
        type            noSlip;
    }
    frontAndBack
    {
        type            empty;
    }
}

// ************************************************************************* //
`,
    },
    {
      path: "0/p",
      role: "压力初场 + 边界条件。dimensions [0 2 -2 0 0 0 0] = m²/s²（不可压 OpenFOAM 里 p 是 kinematic pressure p_actual/ρ）。所有 wall zeroGradient 让 BL 自然发展；绝对零点由 fvSolution::SIMPLE::pRefCell 锚定。",
      content: `/*--------------------------------*- C++ -*---------------------------------*\\
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
    bottom
    {
        type            zeroGradient;
    }
    frontAndBack
    {
        type            empty;
    }
}

// ************************************************************************* //
`,
    },
    {
      path: "system/sampleDict",
      role: "可选 · gold-anchored 17 点 post-hoc 采样。这 17 个 y 正是 Ghia 1982 Table I 的 y 坐标（归一化），让 postProcess -func sampleDict 直接产出和 gold 逐点对应的 17 值，避免插值误差。Run 完 simpleFoam 后再跑 postProcess 即可。",
      content: `/*--------------------------------*- C++ -*---------------------------------*\\
|  sampleDict - gold-anchored 17-point centerline (Ghia 1982 Table I y grid)|
\\*---------------------------------------------------------------------------*/
type            sets;
libs            ("libsampling.so");

interpolationScheme cellPoint;

setFormat       raw;

sets
(
    uCenterlineGold
    {
        type        points;
        axis        y;
        ordered     on;
        points
        (
            (0.05 0.00000 0.005)
            (0.05 0.00625 0.005)
            (0.05 0.01250 0.005)
            (0.05 0.01875 0.005)
            (0.05 0.02500 0.005)
            (0.05 0.03125 0.005)
            (0.05 0.03750 0.005)
            (0.05 0.04375 0.005)
            (0.05 0.05000 0.005)
            (0.05 0.05625 0.005)
            (0.05 0.06250 0.005)
            (0.05 0.06875 0.005)
            (0.05 0.07500 0.005)
            (0.05 0.08125 0.005)
            (0.05 0.08750 0.005)
            (0.05 0.09375 0.005)
            (0.05 0.10000 0.005)
        );
    }
);

fields          (U);

// ************************************************************************* //
`,
    },
  ],
};
