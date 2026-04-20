# CFD Harness UI — Frontend (Phase 0)

Vite + React 18 + TypeScript + Tailwind CSS. Implements Screen 4
(Validation Report) from `docs/ui_design.md` and is the starting
surface for the Path-B Agentic V&V Workbench (DEC-V61-002).

## Quick start

```bash
# 1. Start the FastAPI backend in another shell (loopback only):
uvicorn ui.backend.main:app --host 127.0.0.1 --port 8000 --reload

# 2. Install + run the dev server:
cd ui/frontend
pnpm install        # or: npm install
pnpm dev            # or: npm run dev
```

Dev server binds to `127.0.0.1:5173` and proxies `/api/**` to the
backend on `127.0.0.1:8000`. Nothing listens on a public interface
in Phase 0.

## Phase-0 scope

- `GET /api/cases` — renders the whitelist-of-10 with contract chips.
- `GET /api/validation-report/{case_id}` — renders Screen 4 against
  the three canonical cases (`differential_heated_cavity`,
  `circular_cylinder_wake`, `turbulent_flat_plate`). Other cases
  still load; their contract status will say `UNKNOWN` until a
  measurement fixture lands.

Out of scope for Phase 0: case editing, run control, audit-package
export, authentication, dashboards. See `docs/ui_roadmap.md`.

## Design tokens

All design tokens live in `tailwind.config.ts` (palette, fonts,
contract-status colors). If you want to bump a token, edit it there
once and rebuild — do not hard-code hex values in components.

## Component inventory (Phase 0)

| Component                     | Purpose                                        |
| ----------------------------- | ---------------------------------------------- |
| `Layout`                      | Left nav + main content shell (dark surface)   |
| `PassFailChip`                | Three-state contract chip (PASS/HAZARD/FAIL)   |
| `BandChart`                   | Inline-SVG tolerance-band chart (no Plotly)    |
| `AuditConcernList`            | Per-concern rows with collapsible detail       |
| `PreconditionList`            | Physics preconditions with satisfied/unmet     |
| `DecisionsTrail`              | DEC-xxx linked list with autonomy marker       |
| `CaseListPage`                | Index route (`/cases`)                         |
| `ValidationReportPage`        | Screen 4 (`/cases/:caseId/report`)             |

## Typecheck / build

```bash
pnpm typecheck
pnpm build
```

`pnpm build` runs `tsc -b` first, so a type error breaks the build.

## Not covered yet

- Unit tests for the React components (Phase 1 — we'll add Vitest
  + Testing Library then).
- Storybook / visual regression (Phase 4 Dashboard).
- i18n (Phase 6 Enterprise).

---

Path B workbench · Phase 0 · DEC-V61-002.
