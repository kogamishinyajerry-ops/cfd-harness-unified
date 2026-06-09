# Frozen BACKEND-LAUNCHED e2e — P4 V71.B low-Re k-ω-SST backward-facing-step (DEC-V61-236)

**This is the e2e evidence DEC-V61-235 deferred.** It proves the **workbench
execution backend** (`src.foam_agent_adapter.DockerOpenFOAMSolverExecutor`)
LAUNCHED a real wall-RESOLVED low-Re kOmegaSST `foamRun -solver incompressibleFluid`
solve end-to-end — NOT a hand-typed `docker run` — and that the Control-plane gate
PASSES on the BACKEND-produced output. This closes V71B-FOLLOWUP-1 item 1 (the gate
live-wiring), the low-Re analog of the wedge's DEC-V61-234.

This does **NOT** flip runnable-coverage: it is still incompressible RANS (the same
compute type as the high-Re BFS) — a turbulence-**treatment** breadth anchor
(integrate-to-wall, y+<1), not a new compute type.

## Why this is distinct from `../_v71b_bfs_lowre_probe/`

| | `_v71b_bfs_lowre_probe` (DEC-V61-235) | `_v71b_bfs_lowre_backend_e2e` (DEC-V61-236, this dir) |
|---|---|---|
| Launcher | hand-typed `docker run --rm` (a DIRECT container solve) | `foam_agent_adapter.execute(TaskSpec(name='backward_facing_step_lowre'))` — the **workbench backend** |
| Proves | solver + gate correctness (V&V benchmark LIVE_VALIDATED) | the **workbench can launch + verify the low-Re anchor end-to-end** |
| Coverage effect | none | none (still incompressible RANS — treatment breadth, NOT a new compute type) |

The physics is identical — what changed is **who launched it**: the execution
backend, via the new identity-keyed route (`name=='backward_facing_step_lowre'`) →
`_execute_backward_facing_step_lowre` → `_docker_run_of11_rm` (fresh `--rm` OF11
`openfoam/openfoam11-paraview510` container, `/opt/openfoam11/etc/bashrc`), which
forces `wall_treatment='resolved'` + `turbulence_model='kOmegaSST'` and persists the
output (no `finally: rmtree`) so the gate reads real solver artifacts.

## Byte-for-byte reproducibility of the V&V probe (the strong result)

The backend `execute()` solve produced a **byte-identical** surface VTK to the
hand-typed DEC-V61-235 probe:

```
allPatches_3000.vtk  SHA256 = fd25bfce0d1a402bc53f36a385f47b060c5c70dae48eed8a37c99e15db0ff749
                     (IDENTICAL to ../_v71b_bfs_lowre_probe/VTK/allPatches/allPatches_3000.vtk)
```

The OF11 incompressibleFluid solve of this adapter-generated case is deterministic:
the workbench backend reproduces the V&V probe's solver output bit-for-bit. The
derived `proof/floor_faces.csv` data rows are likewise identical to the probe's; the
only difference is one cosmetic header-comment path label (`allPatches_3000.vtk` vs
`VTK/allPatches/allPatches_3000.vtk`).

## What `foam_agent_adapter.execute()` returned (see `execution_result.json`)

- `launcher`: `src.foam_agent_adapter.DockerOpenFOAMSolverExecutor.execute()`
- `success`: `true`, `is_mock`: `false` (a REAL container run, ~63 s)
- measured QoIs: **Xr/H = 5.8812** (reattachment, `wall_shear_tau_x_zero_crossing`),
  **floor y+ max = 0.0661** (`< 1` — wall-RESOLVED precondition met),
  1 reattachment crossing, 119 floor faces.

## Control-plane gate verdict on the BACKEND output (see `gate_verdict.json`)

`src.bfs_lowre_gate.gate_bfs_lowre_against_gold` → **PASS**: Xr/H within 10% of the
6.26 gold (measured **−6.05%**) AND all **4 hard gates** PASS (reattachment-within-tol,
resolved-near-wall y+<1, single-reattachment, floor-mask-nondegenerate).

Plane discipline: the Execution-plane runner EXECUTES + EXTRACTS (returns the QoIs);
the Control-plane gate is run by the **caller** (the e2e test / `TaskRunner._verify_bfs_lowre`),
never imported by the adapter — no Execution⇄Control cycle (four-plane import-linter KEPT).

## Reproduce

```bash
# the committed, opt-in gated e2e test reproduces this exactly (needs docker + OF11 image):
CFDTRUST_LIVE_BFS_LOWRE_E2E=1 .venv/bin/python -m pytest \
  tests/p4/test_bfs_lowre_live.py -v -s
```

The test stages the adapter-generated resolved case through the backend, runs
`blockMesh && checkMesh && foamRun -solver incompressibleFluid && foamToVTK
-latestTime -allPatches` in a FRESH `--rm` OF11 container (disturbing no running
container), extracts the QoIs, and asserts the gate PASSES. `SHA256SUMS` is the
tamper manifest for the frozen artifacts here.
