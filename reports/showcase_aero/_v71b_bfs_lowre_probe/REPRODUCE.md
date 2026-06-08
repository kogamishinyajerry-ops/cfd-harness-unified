# Reproduce — V71.B low-Re k-omega-SST backward-facing-step (wall-resolved)

This is a **real solver run** of the **adapter-generated** wall-resolved low-Re BFS
case. The gate measures reattachment + floor y+ from the artifacts here; nothing is
authored by hand.

## 1. Generate the case (through the adapter)

```python
from src.foam_agent_adapter import DockerOpenFOAMSolverExecutor
from src.models import TaskSpec, GeometryType, FlowType, SteadyState, Compressibility
ad = DockerOpenFOAMSolverExecutor()
ts = TaskSpec(name="backward_facing_step_lowre",
              geometry_type=GeometryType.BACKWARD_FACING_STEP,
              flow_type=FlowType.INTERNAL, steady_state=SteadyState.STEADY,
              compressibility=Compressibility.INCOMPRESSIBLE, Re=5000.0,
              boundary_conditions={"turbulence_model": "kOmegaSST", "wall_treatment": "resolved"})
ad._generate_backward_facing_step(out_dir, ts)   # → case_definition/ here
```

## 2. Solve (fresh OF11 container, disturbs nothing)

```bash
# in a fresh `docker run` openfoam/openfoam11-paraview510 (do NOT reuse a running container)
source /opt/openfoam11/etc/bashrc
blockMesh            # → 12320 cells, checkMesh "Mesh OK"
checkMesh
foamRun -solver incompressibleFluid    # → endTime 3000 (resolved Xr plateau)
foamToVTK -latestTime -noZero -allPatches -noFaceZones   # → VTK/allPatches/allPatches_3000.vtk
```

## 3. Derive the frozen floor CSV (shared mask)

```python
from pathlib import Path
from src.bfs_lowre_extractor import write_floor_faces_csv
write_floor_faces_csv(Path("VTK/allPatches/allPatches_3000.vtk"),
                      Path("proof/floor_faces.csv"))
```

## 4. Gate (offline replay; stdlib, no pyvista)

```python
from pathlib import Path
from src.bfs_lowre_gate import gate_bfs_lowre_against_gold
g = gate_bfs_lowre_against_gold(Path("reports/showcase_aero/_v71b_bfs_lowre_probe"))
assert g.passed     # Xr/H=5.881 (−6.05% vs 6.26), floor y+ max 0.066 (<1), 1 crossing, 119 faces
```

The gate resolves `proof/floor_faces.csv` first (stdlib replay) and falls back to
`VTK/allPatches/*.vtk` (pyvista) for a live run — both feed the identical
`_metrics_from_floor_faces` core, masked by `src.bfs_floor_region` (the single
source of truth shared with the live adapter Path-1a reattachment extractor).

## Cross-check (the V&V dual-method finding)

Re-running the **high-Re** BFS (Re=7600, no `wall_treatment`) through the identical
pipeline yields wall-shear Xr/H = **5.647**, matching this project's documented
high-Re value — confirming the extraction is sound and the resolved-mesh 5.881 is a
genuine physics improvement, not an extraction artifact. The fixed-height U_x proxy
is grid-height-biased on the resolved mesh and is NOT used as the anchor (see
RESULT.md).
