# Frozen BACKEND-LAUNCHED e2e — P4 V71.A supersonic-wedge (DEC-V61-234)

**This is the e2e evidence DEC-V61-233 lacked.** It proves the **workbench
execution backend** (`src.foam_agent_adapter.DockerOpenFOAMSolverExecutor`)
LAUNCHED a real `rhoCentralFoam` solve on the ESI v2312 image end-to-end — NOT a
hand-typed `docker run`. This is what flips runnable-coverage **2 → 3** under
Blueprint v4 Law-1 + the DEC-V61-224(b) image-reconciliation provision.

## Why this is distinct from `../_w71a_wedge_probe/`

| | `_w71a_wedge_probe` (DEC-V61-233) | `_w71a_wedge_backend_e2e` (DEC-V61-234, this dir) |
|---|---|---|
| Launcher | hand-typed `docker run --rm` (a DIRECT container solve) | `foam_agent_adapter.execute(TaskSpec(SUPERSONIC_WEDGE))` — the **workbench backend** |
| Proves | solver + gate correctness (V&V benchmark LIVE_VALIDATED) | the **workbench can launch a supersonic case end-to-end** |
| Coverage effect | none (Codex R0 P2-1 refused the flip) | **flips 2 → 3** (the deferred wiring now exists) |

The physics is identical (same frozen `case_definition/`, same ESI image) — what
changed is **who launched it**: the execution backend, via the new
`GeometryType.SUPERSONIC_WEDGE` route → `_execute_supersonic_wedge` →
`_docker_run_esi_rm` (fresh `--rm` ESI container, `/openfoam/profile.rc`).

## What `foam_agent_adapter.execute()` returned (see `execution_result.json`)

- `launcher`: `src.foam_agent_adapter.DockerOpenFOAMSolverExecutor.execute()`
- `success`: `true`, `is_mock`: `false` (a REAL container run, ~25 s)
- measured QoIs: β=45.2372°, M₂=1.4445, p₂/p₁=2.1879, ρ₂/ρ₁=1.7219, T₂/T₁=1.2692

## Control-plane gate verdict on the BACKEND output (see `gate_verdict.json`)

`src.wedge_oblique_shock_gate.gate_wedge_against_gold` → **PASS**: every observable
within 3% of the analytical θ-β-M gold AND all **6 hard gates** PASS (supersonic
inflow, inflow-matches-M1, downstream-supersonic, β>Mach-angle, ideal-gas
consistency, shock-locus cross-consistency).

Plane discipline: the Execution-plane runner EXECUTES + EXTRACTS (returns the
QoIs); the Control-plane gate is run by the **caller** (the e2e test /
`gate_wedge_against_gold`), never imported by the adapter — no Execution⇄Control
cycle (four-plane import-linter KEPT).

## Reproduce

```bash
# the committed, opt-in gated e2e test reproduces this exactly (needs docker + ESI image):
CFDTRUST_LIVE_WEDGE_E2E=1 .venv/bin/python -m pytest \
  tests/p4/test_supersonic_wedge_live.py -v -s
```

The test stages the frozen `../_w71a_wedge_probe/case_definition/` through the
backend, runs `blockMesh && checkMesh && rhoCentralFoam` in a FRESH `--rm` ESI
container (disturbing no running container), extracts the QoIs, and asserts the
gate PASSES. `SHA256SUMS` is the tamper manifest for the frozen artifacts here.
