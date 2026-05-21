# Architecture

## Layers

```
+----------------------------------------------------+
|  Cockpit & static UI (Phase 0 = MD/HTML cockpit)   |
+----------------------------------------------------+
|  cfdtrust CLI  (validate | audit | run | report)   |
+----------------------------------------------------+
|  Audit modules: geometry / mesh / bc / solver /    |
|  qoi / report                                      |
+----------------------------------------------------+
|  Schemas + manifest loader (case_manifest /        |
|  trust_report)                                     |
+----------------------------------------------------+
|  Backends:                                         |
|    - mocked (Phase 0)                              |
|    - openfoam (Phase 1+)  ← thin adapter           |
+----------------------------------------------------+
|  CWOS state (.cwos/) + tools (cwos_event,          |
|  cwos_status, cwos_render_dashboard)               |
+----------------------------------------------------+
```

## Data flow

1. operator writes `case_manifest.yaml`
2. `cfdtrust validate-manifest` checks against `case_manifest.schema.json`
3. `cfdtrust audit` runs each audit module; each module writes a JSON/CSV artifact
4. `cfdtrust run` executes the solver gate (mocked in Phase 0)
5. `cfdtrust report` aggregates gates into `trust_report.json`, validated against
   `trust_report.schema.json`
6. `tools/cwos_status.py` discovers `trust_report.json` files and aggregates them
7. `tools/cwos_render_dashboard.py` renders `COCKPIT.md` + `COCKPIT.html`
8. each agent that does work appends an event via `tools/cwos_event.py`

## Module boundaries

- `src/cfdtrust/manifest.py` — single source of truth for "is this a valid case?"
- `src/cfdtrust/audit/*.py` — each module is responsible for exactly one gate
- `src/cfdtrust/audit/report.py` — only place that writes `trust_report.json`
- `src/cfdtrust/schemas/` — only place that defines the contract shape
- `tools/` — stateless utilities; never imported by `cfdtrust`
- `.cwos/` — append-only state; modified only by `tools/cwos_event.py` and
  `tools/cwos_status.py`

## Non-goals (architecture)

- no plugin system in Phase 0
- no concurrency / scheduler in Phase 0
- no database; the repo IS the database
- no service / API in Phase 0; CLI only

## Failure isolation

Each gate is independent. A failure in `mesh.py` must not prevent
`boundary_conditions.py` from running; the trust_report aggregates all gate
results. Tests assert that one gate's exception does not break the loop.

## Where OpenFOAM enters

A single thin adapter file (TBD path, likely `src/cfdtrust/backends/openfoam.py`)
will own all OpenFOAM-specific code. The audit modules will call into the
adapter, never directly into shell. This isolates OpenFOAM dependency to one
file and keeps the rest of the codebase unit-testable without OpenFOAM
installed.

OpenFOAM-specific work begins in Phase 1, not Phase 0.
