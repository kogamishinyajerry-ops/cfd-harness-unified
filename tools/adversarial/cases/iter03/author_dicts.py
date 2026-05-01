"""Iter03: hand-author OpenFOAM-10 dicts for the iter02 duct case
that bypass the LDC-hardcoded /setup-bc route (defect 3 workaround).

Uses the named polyMesh patches from defect 2a fix (inlet, outlet,
walls) as BC keys, with intent.json's flow definition. This is the
same dict shape that setup_ldc_bc writes, just with patch names
matching the imported geometry instead of the LDC `lid`/`fixedWalls`.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

REPO = Path("/Users/Zhuanz/Desktop/cfd-harness-unified")
HERE = Path(__file__).resolve().parent

case_id = (HERE / "case_id.txt").read_text().strip()
case_dir = REPO / "ui/backend/user_drafts/imported" / case_id
intent = json.loads((HERE / "intent.json").read_text())

# Sanity-check the polyMesh has the patches we expect.
boundary = (case_dir / "constant/polyMesh/boundary").read_text()
patches_in_mesh = set()
for m in re.finditer(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\n\s*\{\s*\n\s*type", boundary, re.MULTILINE):
    patches_in_mesh.add(m.group(1))
expected = set(intent["patches"].keys())
missing = expected - patches_in_mesh
if missing:
    sys.exit(f"polyMesh missing patches: {missing} (have {patches_in_mesh})")
print(f"polyMesh patches: {patches_in_mesh} ✓")

# Write 0/U from intent
def fmt_u(spec):
    """spec is either [vx, vy, vz] (fixedValue) or 'zeroGradient'."""
    if spec == "zeroGradient":
        return "{ type zeroGradient; }"
    if isinstance(spec, list):
        return f"{{ type fixedValue; value uniform ({spec[0]} {spec[1]} {spec[2]}); }}"
    raise ValueError(f"unknown U spec: {spec}")

def fmt_p(spec):
    if spec == "zeroGradient":
        return "{ type zeroGradient; }"
    if isinstance(spec, dict) and spec.get("type") == "fixedValue":
        return f"{{ type fixedValue; value uniform {spec['value']}; }}"
    raise ValueError(f"unknown p spec: {spec}")

(case_dir / "0").mkdir(exist_ok=True)
(case_dir / "system").mkdir(exist_ok=True)
(case_dir / "constant").mkdir(exist_ok=True)

# Roles → wall vs flow boundary determine no-slip etc.
def u_for(name, p_spec):
    role = p_spec["role"]
    if role == "wall":
        return "{ type noSlip; }"
    return fmt_u(p_spec["U"])

u_blocks = "\n".join(
    f"    {name:<10} {u_for(name, sp)}"
    for name, sp in intent["patches"].items()
)
p_blocks = "\n".join(
    f"    {name:<10} {fmt_p(sp['p'])}"
    for name, sp in intent["patches"].items()
)

(case_dir / "0/U").write_text(
    f'FoamFile {{ version 2.0; format ascii; class volVectorField; '
    f'location "0"; object U; }}\n'
    f"dimensions      [0 1 -1 0 0 0 0];\n"
    f"internalField   uniform (0 0 0);\n"
    f"boundaryField\n"
    f"{{\n{u_blocks}\n}}\n"
)
(case_dir / "0/p").write_text(
    'FoamFile { version 2.0; format ascii; class volScalarField; '
    'location "0"; object p; }\n'
    "dimensions      [0 2 -2 0 0 0 0];\n"
    "internalField   uniform 0;\n"
    "boundaryField\n"
    f"{{\n{p_blocks}\n}}\n"
)

nu = intent["physics"]["nu_m2_s"]
(case_dir / "constant/physicalProperties").write_text(
    'FoamFile { version 2.0; format ascii; class dictionary; '
    'location "constant"; object physicalProperties; }\n'
    "transportModel  Newtonian;\n"
    f"nu              [0 2 -1 0 0 0 0] {nu};\n"
)
(case_dir / "constant/momentumTransport").write_text(
    'FoamFile { version 2.0; format ascii; class dictionary; '
    'location "constant"; object momentumTransport; }\n'
    "simulationType laminar;\n"
)

solver = intent["solver"]
end_time = solver["end_time_s"]
delta_t = solver["delta_t_s"]
# Use icoFoam (transient incompressible) since simpleFoam isn't wired
# in setup_ldc_bc and we want to mirror what the existing solve route
# expects. CFL ≈ U·dt/dx = 0.5 · dt / 0.005 should stay ≤ 1 →
# dt ≤ 0.01. iter02 intent's dt=1.0 was for steady-state simpleFoam;
# for icoFoam we override.
ico_dt = 0.01
ico_end = 5.0
(case_dir / "system/controlDict").write_text(
    'FoamFile { version 2.0; format ascii; class dictionary; '
    'location "system"; object controlDict; }\n'
    "application icoFoam;\n"
    "startFrom startTime;\n"
    "startTime 0;\n"
    "stopAt endTime;\n"
    f"endTime {ico_end};\n"
    f"deltaT {ico_dt};\n"
    "writeControl runTime;\n"
    "writeInterval 1.0;\n"
    "purgeWrite 0;\n"
    "writeFormat ascii;\n"
    "writePrecision 6;\n"
    "writeCompression off;\n"
    "timeFormat general;\n"
    "timePrecision 6;\n"
    "runTimeModifiable true;\n"
)
(case_dir / "system/fvSchemes").write_text(
    'FoamFile { version 2.0; format ascii; class dictionary; '
    'location "system"; object fvSchemes; }\n'
    "ddtSchemes  { default Euler; }\n"
    "gradSchemes { default Gauss linear; }\n"
    "divSchemes  { default none; div(phi,U) Gauss linear; }\n"
    "laplacianSchemes { default Gauss linear orthogonal; }\n"
    "interpolationSchemes { default linear; }\n"
    "snGradSchemes { default orthogonal; }\n"
)
(case_dir / "system/fvSolution").write_text(
    'FoamFile { version 2.0; format ascii; class dictionary; '
    'location "system"; object fvSolution; }\n'
    "solvers\n"
    "{\n"
    "    p  { solver PCG; preconditioner DIC; tolerance 1e-06; relTol 0.05; }\n"
    "    pFinal { $p; relTol 0; }\n"
    "    U  { solver smoothSolver; smoother symGaussSeidel; "
    "tolerance 1e-05; relTol 0; }\n"
    "}\n"
    "PISO\n"
    "{\n"
    "    nCorrectors 2;\n"
    "    nNonOrthogonalCorrectors 2;\n"
    "    pRefCell 0;\n"
    "    pRefValue 0;\n"
    "}\n"
)

print(f"Authored 7 dicts under {case_dir}")
print("  patches in 0/U:", list(intent["patches"].keys()))
print(f"  controlDict: icoFoam, endTime={ico_end}, deltaT={ico_dt}")
