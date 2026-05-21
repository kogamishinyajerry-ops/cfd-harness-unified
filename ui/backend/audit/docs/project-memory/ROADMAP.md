# Roadmap

The roadmap is phased to prevent the wedge from drifting into the North Star
before its foundations are credible. Each phase has a stop condition and a
go condition.

## Phase 0 — Project Operating System + Trust Harness Scaffold

**Goal:** make CFD correctness explicit and machine-auditable for one sample case,
even if the solver is mocked.

Deliverables:
- repo skeleton, project memory, agents, skills
- `cfdtrust` CLI with `validate-manifest`, `audit`, `run`, `report`
- JSON schemas for `case_manifest` and `trust_report`
- one sample case (`flat_plate_rans_sst`)
- `.cwos/` state + 1-minute cockpit
- pytest suite that catches obvious false-pass paths

Stop condition (Phase 0 incomplete if any are true):
- a trust_report can be produced without a valid manifest
- a mocked solver run is not labeled in trust_report.json
- the cockpit shows PASS counts not backed by evidence

Go condition (enter Phase 1):
- `make bootstrap-check` exits 0
- Red Team review against the bootstrap is filed
- `OPEN_QUESTIONS.md` and `NEXT_ACTIONS.md` reflect actual residual work

## Phase 1 — Real OpenFOAM Adapter + One Canonical Benchmark

**Goal:** swap the mocked solver gate for a real OpenFOAM invocation on
`flat_plate_rans_sst`, with a finalized reference dataset.

Deliverables:
- `openfoam-adapter-engineer` produces a thin OpenFOAM execution wrapper
- residuals + QoI extracted from real solver output, not synthetic
- finalized reference data + licensing
- `validation_status` may move from `not_validated` to `validated` for the first time
- mesh independence study artifact recorded

Stop condition:
- any artifact derives from a mocked run without being labeled
- residuals look fine but QoI is unstable and no FAIL is raised

## Phase 2 — Negative Tests + Red Team Hardening

**Goal:** prove the harness catches bad cases.

Deliverables:
- ≥7 of 10 seeded negative cases listed in `negative_tests/README.md`
- Red Team certification that each seeded bad case produces a non-PASS verdict
- regression tests integrated into `pytest`

Stop condition:
- any seeded bad case yields PASS or MOCKED instead of WARN/FAIL

## Phase 3 — Minimal Workbench UI

**Goal:** three static screens, no more.

Screens:
1. Case Contract — view + validate `case_manifest.yaml`
2. Run Timeline — residuals, log tail, gate status
3. Trust Report — gates, artifacts, limitations

Stop condition:
- any screen exposes "approve / change BC / pick turbulence model" buttons
  (that is workbench scope, not Phase 3 scope)

## Phase 4 — AI Advisor over Evidence

**Goal:** AI advisor reads existing artifacts and answers, in natural language,
"what does this trust_report mean and what should I do next?"

Constraints:
- advisor never modifies case files
- advisor never overrides a gate
- advisor cites artifacts by path

## Phase 5 — Design Exploration (long-term)

**Goal:** structured parameter sweeps over verified cases. Out of scope until
Phases 0–4 hold.

## Cross-phase non-negotiables

- never accept "completed" without an artifact
- never let mocked execution graduate to PASS
- never let AI advisor turn FAIL into PASS
- never expand scope outside the active phase without a decision
