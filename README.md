# cfd-harness-unified

A demo-first AI-CFD workbench. Ten canonical flow problems, each paired with
its historical gold standard, tolerance band, and common pitfalls — so you can
see the distance between *getting a number* and *getting it right*.

## Quick start

```bash
# Python 3.12 is the supported runtime. Everything below assumes .venv is
# Python 3.12.x (see `./.venv/bin/python --version`).
python3.12 -m venv .venv
.venv/bin/pip install -e ".[ui,dev]"
(cd ui/frontend && npm install)

./scripts/start-ui-dev.sh
# UI:      http://127.0.0.1:5173/learn          ← demo front door
# Pro:     http://127.0.0.1:5173/pro            ← evidence workbench
# API doc: http://127.0.0.1:8000/api/docs
```

## What you see

### `/learn` — demo front door

Ten classic CFD problems as a visual catalog. Each card carries its historical
citation, a difficulty dot, and a one-line teaser. Click into a case and you
get five tabs:

- **故事 / Story** — physics, canonical reference, why validation matters, the
  literature reference plot, and the solver contour + residuals from a real
  OpenFOAM run.
- **对比 / Compare** — your measurement vs. the gold value on a tolerance band.
  Run selector lets you flip between reference / under-resolved / wrong-model
  runs to watch the verdict change — that's the teaching moment.
- **网格 / Mesh** — grid-convergence slider (4 densities), live sparkline that
  plots your measurement as it converges toward gold.
- **运行 / Run** — jump into Pro Workbench for the real solver loop.
- **进阶 / Advanced** — decision trail, audit concerns, signed audit package
  builder.

Anchor cases (the ones with the tightest story → compare → evidence loop):

- `lid_driven_cavity` (Ghia 1982)
- `circular_cylinder_wake` (Williamson 1996)
- `naca0012_airfoil` (Ladson 1988)

### `/pro` — evidence workbench

Path B V&V-first surface for audit, regulated-industry contexts, and anyone
who needs to hand a CFD result to someone whose signature is on the line.
Screens: Dashboard · Cases · Decisions · Runs · Audit Package.

Not the right starting point for a demo. Reachable from every `/learn` page
via `进入专业工作台 →` and from the top-nav `Pro Workbench →` link.

## Testing

```bash
# Core engine + knowledge + report engine
.venv/bin/pytest

# UI backend (FastAPI routes, comparator gates, attestor, audit package)
.venv/bin/pytest ui/backend/tests -q

# UI frontend
(cd ui/frontend && npm run typecheck && npm run build)
```

## Architecture (one screen)

```
knowledge/whitelist.yaml + knowledge/gold_standards/*.yaml
       │
       ├─► auto_verifier  ─────► report_engine  ─────► reports/<case>/
       │                                                auto_verify_report.yaml
       │
       ├─► task_runner  ──► FoamAgentExecutor ──► reports/phase5_fields/<case>/
       │                   (Docker + OpenFOAM)
       │
       └─► ui/backend  ──► /api/cases/*
                               │
                               ▼
                         ui/frontend  /learn  /pro
```

- `MockExecutor`: unit-test fast path; returns preset results.
- `FoamAgentExecutor`: the real Docker + OpenFOAM path (optional,
  install via `.venv/bin/pip install -e '.[cfd-real-solver]'`).
- `src/convergence_attestor.py` + `src/comparator_gates.py`: the A1..A6 /
  G1..G5 hard-FAIL guards that stop a PASS-washed verdict from leaking out
  of the system (DEC-V61-036, DEC-V61-038, DEC-V61-045).

## Configuration

- `config/notion_config.yaml` — Notion control-plane (optional, only wired
  up for the internal decisions mirror).
- `config/foam_agent_config.yaml` — Foam-Agent executor (only needed when
  running real OpenFOAM, not for the demo path).

## Where to look next

- `.planning/STATE.md` — current phase state, open decisions, external gates.
- `.planning/decisions/` — the numbered DEC-V61-* ledger; every non-trivial
  contract change is recorded here.
- `knowledge/gold_standards/*.yaml` — one canonical file per case. Each now
  carries a `physics_contract` block (preconditions, contract_status) so a
  PASS is explicitly a physics-valid PASS.
