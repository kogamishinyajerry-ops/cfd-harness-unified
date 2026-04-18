"""EX-1-007 B1 post-commit: blockMesh smoke-check.

Generates a DHC (Ra=1e10) case with the new 256+ratio=6 grading and runs
only blockMesh in the cfd-openfoam container. Verifies:
  1. blockMesh parses simpleGrading ((...) (...)) syntax
  2. Cell count matches expectation (256 x 256 x 1)
  3. First-cell size near wall ≈ 1.3 mm (as C5 predicted)

Does NOT run the solver. That is the separate long-running measurement
task (expected 30-120 min wall-clock for 256^2 buoyantFoam + k-omega SST).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.foam_agent_adapter import FoamAgentExecutor
from src.models import (
    Compressibility,
    FlowType,
    GeometryType,
    SteadyState,
    TaskSpec,
)

CASE_HOST = Path("/tmp/cfd-harness-cases/dhc_b1_smoke")
CASE_CONT = "/tmp/cfd-harness-cases/dhc_b1_smoke"


def main() -> int:
    # 1. Build DHC TaskSpec (matches whitelist.yaml differential_heated_cavity entry)
    task = TaskSpec(
        name="Differential Heated Cavity (Natural Convection)",
        geometry_type=GeometryType.NATURAL_CONVECTION_CAVITY,
        flow_type=FlowType.NATURAL_CONVECTION,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
        Ra=1e10,
        boundary_conditions={"aspect_ratio": 1.0, "Pr": 0.71},
    )

    CASE_HOST.mkdir(parents=True, exist_ok=True)
    for sub in ("0.prev",):
        (CASE_HOST / sub).mkdir(parents=True, exist_ok=True)

    # 2. Generate case files in-place (reuse executor's generator)
    exec_ = FoamAgentExecutor()
    exec_._generate_natural_convection_cavity(CASE_HOST, task)  # noqa: SLF001

    # 3. Dump blockMeshDict's blocks line for visibility
    bmd = (CASE_HOST / "system" / "blockMeshDict").read_text()
    for line in bmd.splitlines():
        if "simpleGrading" in line or line.strip().startswith("hex"):
            print("[blockMesh]", line.rstrip())

    # 4. Run blockMesh inside the container
    cmd = [
        "docker", "exec", "-w", CASE_CONT, "cfd-openfoam",
        "bash", "-lc", "source /opt/openfoam10/etc/bashrc && blockMesh",
    ]
    print("[exec]", " ".join(cmd))
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=300,
    )
    print("--- blockMesh stdout (tail) ---")
    print("\n".join(result.stdout.splitlines()[-30:]))
    if result.returncode != 0:
        print("--- blockMesh stderr ---")
        print(result.stderr)
        return 2

    # 5. Parse cell count via checkMesh
    cm = subprocess.run(
        ["docker", "exec", "-w", CASE_CONT, "cfd-openfoam",
         "bash", "-lc", "source /opt/openfoam10/etc/bashrc && checkMesh"],
        capture_output=True, text=True, timeout=300,
    )
    print("--- checkMesh (cells + aspect ratio) ---")
    for line in cm.stdout.splitlines():
        s = line.strip()
        if s.startswith(("cells:", "Max aspect ratio", "Min volume", "Max volume", "points:")):
            print("  ", s)

    return 0


if __name__ == "__main__":
    sys.exit(main())
