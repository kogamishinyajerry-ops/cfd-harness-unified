# Module Boundaries

## Hard boundaries (Phase 0)

| boundary | allowed direction | violation example |
|---|---|---|
| `tools/` ⇄ `src/cfdtrust/` | `tools/` may NOT import from `cfdtrust` | `tools/cwos_status.py` importing `cfdtrust.audit.report` |
| `src/cfdtrust/schemas/` ⇄ everything | only `manifest.py` and `audit/report.py` load schemas | another module reading `case_manifest.schema.json` directly |
| audit modules ⇄ each other | no cross-imports between gate modules | `mesh.py` importing `boundary_conditions.py` |
| `cfdtrust.audit.report` ⇄ audit gates | `report.py` consumes gate dicts; gate modules NEVER call `report.py` | `geometry.py` writing to `trust_report.json` |
| `cfdtrust` ⇄ OpenFOAM | only via `cfdtrust.backends.openfoam` (Phase 1+) | audit modules calling `subprocess` directly |
| `.cwos/` ⇄ writers | only `tools/cwos_event.py` and `tools/cwos_status.py` may write here | `cfdtrust` writing event files |
| AI advisor ⇄ case files | advisor is read-only | advisor writing `case_manifest.yaml` |

## Why each boundary

1. **`tools/` cannot import `cfdtrust`** — keeps tools usable even when the
   package is broken; ensures a build failure does not poison the cockpit.
2. **Schemas centralized** — one place to evolve contracts; tests assert that
   only `manifest.py` / `report.py` import the schemas.
3. **No audit cross-imports** — gates must remain independently failable; a bug
   in one gate cannot cascade.
4. **Only `report.py` writes `trust_report.json`** — single writer prevents
   inconsistent gate aggregation.
5. **OpenFOAM behind an adapter** — keeps Phase 0 testable without a CFD install;
   Phase 1 swaps the adapter, not the audit modules.
6. **CWOS writers are confined** — append-only audit trail; arbitrary writers
   would defeat the audit trail.
7. **AI advisor read-only** — the largest single risk category in the project.
   This boundary is enforced by repo rule and by Red Team review.

## How violations are caught

- pytest tests assert import boundaries via `ast` inspection.
- Red Team review checks for boundary violations during code review.
- Cockpit flags PASS events whose evidence list includes files outside the
  expected module.

## When a boundary should change

A boundary change requires a `DECISION_LOG.md` entry and a Red Team review.
Boundaries are part of the architecture, not implementation details.
