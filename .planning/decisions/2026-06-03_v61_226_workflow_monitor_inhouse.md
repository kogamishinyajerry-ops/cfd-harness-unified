---
decision_id: V61-226
title: Workflow Monitor — in-house workflow-runtime surface (NOT Trigger.dev) · mock-first frontend
status: Accepted
parent_dec: none (new product surface — user-directed 2026-06-03)
sibling_decs: V61-092 (nav-discoverability) · V61-203 (frontend tsc -b gate)
phase: cross-cutting (workflow-runtime UX) · MVP-1 frontend design preview
autonomous_governance: true
confidence: high
kogami_opt_in: false (additive new surface, outside §11.1 freeze; reversible — no shared-logic mutation)
round_cap: 3
codex_review_relay: CRS gpt-5.4 high (86gs xhigh on standby)
codex_verdict: PENDING
notion_sync_status: synced 2026-06-03 (https://app.notion.com/p/374c68942bed8148a916c0e19e04b6c4)
touches_shared_dec: none (App.tsx route + Layout.tsx nav are additive entries; new files under pages/workflow_monitor/)
date: 2026-06-03
---

# DEC-V61-226 · Workflow Monitor — in-house workflow-runtime surface

## Context

User proposed integrating the project with **Trigger.dev v3** to build a
"visible / resumable / traceable CFD workflow runtime": wrap each engineering
stage as a task emitting structured status, with a frontend Workflow Monitor
page (stage graph · object preview · advisor log · timeline), mock-first.

## Decision

**Adopt the GOAL, reject the MEANS.** Build the workflow-runtime surface
**in-house** on the existing FastAPI + SSE + React substrate. Do **not** adopt
Trigger.dev.

### Why not Trigger.dev (chief-engineer assessment, evidence-based)

A repo surface scan established the project **already carries ~80% of the
substrate** the proposal wants — each of the six stages already exists as a
backend route:

| Proposed node | Existing implementation |
|---|---|
| Geometry Intake | `routes/import_geometry.py` + `geometry_render.py` |
| Geometry Validation | `routes/preflight.py` + `validation.py` |
| Mesh Generation | `services/meshing_gmsh/pipeline.py` · `meshing_snappy/pipeline.py` |
| Mesh Quality Check | `routes/mesh_quality.py` + `mesh_metrics.py` |
| Solver Run | `routes/case_solve.py` + **`solver_stream.py` (already SSE)** |
| Result Report | `routes/comparison_report.py` + `audit_package.py` |

Plus `run_ids.py`/`run_history.py` (run abstraction), `ai_advisor.py`/`ai_coach.py`
(advisor layer), `src/task_runner.py`, and the React workbench + visualization.
Trigger.dev is **not present** in the repo.

Rejecting Trigger.dev because (ordered by blast radius):
1. **North-star conflict.** Project is local-first / offline-runnable / auditable
   (Blueprint v4 + four-question gate "LLM offline-runnable"). Trigger.dev v3 is
   either a cloud SaaS (run data leaves the box) or self-hosted (Postgres + Redis
   + Docker-in-Docker). Adopting a new orchestration platform requires explicit
   owner sign-off (global CLAUDE.md: "不擅自引入新框架/编排系统").
2. **Polyglot seam.** Trigger.dev tasks are TypeScript; the execution core is
   Python + Docker (OpenFOAM). It would orchestrate Python solvers from a TS
   layer — two extra hops + a serialization boundary per stage.
3. **Rewrite of existing stages.** The six stages already exist as Python; wrapping
   them as TS tasks re-implements working code for a dashboard.
4. **Honesty risk.** The proposal's "mock runner that pretends to solve" collides
   with the project's defining principle. Mock is allowed ONLY as clearly-stamped
   dev scaffolding reusing the existing `is_mock` plumbing — never confusable with
   a real run.

### What we build instead

- **`StageStatus` contract** (`types/workflow.ts`; Pydantic mirror later) — the
  genuinely valuable schema: stage/state/progress/currentObject/metrics/warnings/
  errors/artifacts/nextAction/advisor. `state` includes `blocked` as a first-class
  honest outcome.
- **WorkflowRunner** (Python, future) — runs the existing stages, persists each
  StageStatus + artifacts to `runs/<run_id>/` → resumable (re-enter at first
  non-complete stage) + auditable. Streams over the existing SSE path.
- **WorkflowMonitor page** (`pages/workflow_monitor/`) — left stage graph · center
  object preview + structured status · right advisor log · bottom timeline.

## This DEC's deliverable (MVP-1 · user-chosen: frontend first)

Frontend page, **mock-data-driven**, to validate layout before backend wiring:

- `types/workflow.ts` — the cross-stage contract.
- `data/workflowMonitorMock.ts` — an honest fixture: a transport-wing external
  RANS run captured mid-solve, showing a **mesh-QC HAZARD** (LE skewness 0.91)
  carried forward and the **report stage BLOCKED** pending convergence evidence.
  The "evidence-insufficient → BLOCK" principle made visible — not an all-green
  happy path.
- `pages/workflow_monitor/{WorkflowMonitorPage,panels}.tsx` + test.
- `App.tsx` route `/workflow-monitor` (inside Layout) + `Layout.tsx` nav entry.

**Honesty invariant:** `run.isMock` renders an indelible "MOCK · 非真实算例"
banner. A design-preview run can never be mistaken for a solve.

## Scope decisions

- **§11.1 freeze:** files live under `pages/workflow_monitor/` (NOT
  `pages/workbench/`) — a new OBSERVATION surface, not a workbench fork. Outside
  the freeze scope; no BREAK_FREEZE needed.
- **No new dependency:** stage graph hand-rolled (no react-flow). Consistent with
  "自研薄层, 不加框架".

## Verification

- `tsc -b` gate (DEC-V61-203): pass.
- `vitest run src/pages/workflow_monitor`: 6/6 pass (mock banner shown/hidden by
  isMock · 6 stages render · default selection follows currentStage · BLOCKED
  report surfaced · stage selection interactive).
- Live render: headless Chrome screenshot of `/workflow-monitor` on the dev
  server confirms the 3-column layout + banner + timeline.

## Follow-ups (not in this DEC)

- Backend `StageStatus` Pydantic mirror + `WorkflowRunner` + `/api/runs/<id>` and
  `/api/runs/<id>/events` (SSE) — wires real stages, swaps the mock fixture.
- Center-panel real viewport (geometry/mesh/field) reusing existing visualization.
