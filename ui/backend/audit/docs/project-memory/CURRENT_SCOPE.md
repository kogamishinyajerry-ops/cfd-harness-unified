# Current Scope — v0 Wedge

## The wedge

**OpenFOAM-based CFD Trust Workbench.**

The wedge is not a workbench you click around in. The wedge is a machine-checkable
trust contract for a CFD case, plus the minimal infrastructure to run it.

## Trust loop (the v0 product)

```
case_manifest.yaml
  → geometry audit       → geometry_report.json
  → mesh audit           → mesh_report.json
  → boundary cond audit  → bc_audit.json
  → solver run           → solver.log + residuals.csv    (Phase 0: mocked)
  → log parsing          → residuals.csv
  → QoI extraction       → qoi.csv
  → reference comparison → reference_comparison.csv
  → trust_report.json
  → cockpit / report
```

Every step writes an artifact. The trust_report aggregates the gates and is the
single source of truth for whether the case is in PASS / WARN / FAIL / MOCKED /
BLOCKED state.

## What v0 ships

- Python package `cfdtrust` with CLI: `validate-manifest`, `audit`, `run`, `report`
- JSON schemas for `case_manifest` and `trust_report`
- One sample case: `flat_plate_rans_sst`
- A repo-native project status system in `.cwos/`
- A 1-minute cockpit in `docs/status/`
- Thirteen project-level Claude agents in `.claude/agents/`
- Five repeatable workflows in `.claude/skills/`
- A pytest suite that catches obvious false-pass paths

## What v0 explicitly does not ship

See `SCOPE_FIREWALL.md`.

## Honesty constraint

Phase 0 is allowed to mock the solver layer. When mocked:

- `trust_report.json` carries `solver_execution: "mocked"` and
  `validation_status: "not_validated"`
- the `limitations` array states "No real CFD solver was executed."
- the cockpit shows mocked status, not PASS
- the README disclosure section says so in English

If any of those become false, the wedge has been broken and must be repaired
before further work.
