---
decision_id: DEC-V61-198
title: APU bay industrial signal · close B-extend arc · 5-artifact extraction · roadmap v2 priority shift · M2.5 CAD ingest hardening as new milestone
status: Accepted
parent_dec: V61-130
phase: strategic-pivot
notion_sync_status: synced 2026-05-12 (resync from base 2026-05-07 https://www.notion.so/359c68942bed81e0ba4eef75df08d778)
---

# DEC-V61-198 · APU bay strategic pivot

## Status

**Accepted 2026-05-07** — strategic charter triggered by external
signal: a one-day industrial CFD case (`~/Desktop/apu-bay-ventilation/`)
completed full pipeline (CATIA STEP → snappyHexMesh 943k cells →
buoyantSimpleFoam pseudo-steady) **without** using main project's
N2.x mesh UI / N3 physics UI / AI auto-mutate paths. This is decisive
evidence that:

1. Workbench is **already capable** of industrial CFD when used in
   "engineer + Claude Code hand-edit SSOT YAML + Jinja2 templates" mode
2. The bottleneck is NOT N2-N5 UI; it is **CAD ingest hardening + solver
   convergence diagnosis codification**
3. v2.3 AI-as-advisor pivot direction (DEC-V61-130) is correct — APU
   bay is the natural-existence proof
4. B-extend arc (V61-172 .. V61-197) has hit edge of marginal returns
   — F1-F15 exhausted persona-facing surface; toy-case grinding will
   not surface F16+ that matters

This DEC closes the B-extend arc, resequences the M1-M6 roadmap, and
commits to a 5-artifact extraction from the APU bay reference case.

## New development philosophy (the framing this DEC encodes)

The user's framing, captured verbatim in conversation post-charter
draft (2026-05-07):

> 工程师 + 现有项目 + Claude Code 已经能从 0 完成工业级 CFD 仿真。
> 接下来通过各种各样不同方面（或者同一个方面不同工况）的真正工业
> 级 CFD 仿真作为案例去不断积累，在过程中积累项目对不同算力类型
> 的处理能力，并且把之前可能累积的错误的设计及时修正。也就是说，
> 从 RAG 论文 + RAG 简单算例，变成 RAG 复杂的真实工程级仿真。

This is the load-bearing reframe. Old vs new mental model:

| Axis | Old | New |
|---|---|---|
| What is the project | A toolbox (feature list) | A **container that accumulates industrial CFD experience** |
| What is value | UI coverage breadth × feature count | **Industrial-case breadth covered × depth sedimented per case** |
| What is progress | Landed N DECs / shipped N UIs | **+1 new solver-class covered AND −K old assumptions falsified by industrial cases** |
| What is RAG corpus | OpenFOAM docs + textbooks + benchmark cases | **Real industrial-case process logs + V-series death-mode chains + decision rationale** |
| What is a case | Test fixture | **Nutrient — each industrial case feeds the container** |
| What is UI | Entry ticket | **Luxury — defer until proven necessary by repeated industrial-case friction** |

### Three pillars of the new philosophy

#### Pillar 1 — Industrial cases are the new dogfood substrate

Not as a calendar target ("one per month"), but as a **systematic
capability axis**. Each new industrial case = one corpus injection
+ one round of stale-assumption falsification.

Solver-class coverage map (priority unranked beyond "what's already
covered"):

| Solver class | Physics signature | Candidate case | Validates |
|---|---|---|---|
| Internal flow + forced convection + buoyancy ✅ | buoyantSimpleFoam, kωSST→laminar | APU bay (covered) | CAD ingest, V-series death modes |
| External flow + high-Re + boundary layer | simpleFoam, kωSST, y+ control | intake diffuser / aircraft external | prism layer in practice, y+ tuning |
| Conjugate heat transfer (CHT) | chtMultiRegion*Foam | radiator / cooled turbine blade | multi-region coupling, fluid-solid interface |
| Rotating machinery | MRF / SRF / sliding mesh | fan / turbine stage | periodic boundary, rotating frame |
| Multiphase / free surface | interFoam / multiphaseEulerFoam | sloshing oil sump / offshore platform | VOF, density ratio |
| Compressible high-speed | rhoCentralFoam / sonicFoam | nozzle / transonic | shock capture, high Mach |
| Combustion / reacting flow | reactingFoam / fireFoam | combustor / fire spread | chemistry source terms, radiation |
| Transient LES / DES | pisoFoam-LES / hybrid | bluff-body / aeroacoustics | time stepping, spectral analysis |

Each new solver-class = a **systematic capability expansion**, not
"one more case in the fleet". Project state is described by what
coverage rows are filled, not by case count.

#### Pillar 2 — Run-and-correct (retroactive correction)

Each new industrial case will surface 3 classes of stale design
assumptions. **Fix in place, do not open a new DEC arc.**

1. **Toy-case-biased thresholds** — e.g. an advisor threshold tuned
   on LDC trips false-positive on industrial cases → adjust + add
   V-series row
2. **Over-narrow schema** — e.g. `BCSetupRequest` schema assumed all
   cases use mass-flow as primary; APU bay's pressure-outlet
   simplification path was outside it → widen schema
3. **Over-confident capability claims** — e.g. README says "supports
   industrial CFD" but doesn't actually support CHT today → update
   the today-can / today-cannot explicit list

Frequency = per-case high-cadence small steps, not low-cadence
versioned releases. Commit message documents the correction; no
full DEC unless the correction crosses ≥3 modules.

#### Pillar 3 — RAG corpus pivots from "papers + simple cases" to "real engineering simulations"

This is the most important paradigm shift. Original M6 AI-advisor
RAG-corpus assumption was:

- OpenFOAM official docs
- Fluent / StarCCM user manuals
- Classical textbook excerpts
- 10 academic gold-standard cases

**New corpus assumption**:

- Each industrial case's **complete process log** (e.g. the V3→V13
  13-version progression, debugging reasoning, final selection)
- V-series finding index (symptom → root cause → fix chain)
- `solver_convergence_playbook.md` decision tree
- Each case's SSOT YAML + rendered dict + checkMesh log + solver
  log + final report
- The **engineering decision rationale** (why v1 used laminar
  fallback, why BC simplified to pressure-outlet, etc.)

**What "AI Review" button does under new corpus**: feed current case's
case.yaml + checkMesh.log + solver log into RAG, get answer
"your version most resembles industrial case X version Y in our
corpus; likely failure mode is V-series Vn".

**What "AI Diagnose" button does under new corpus**: on convergence
failure, match nearest V-series entry, give specific suggestion
e.g. "S2 + S3 combination: try PBiCGStab + diagonal preconditioner".

This is **orders of magnitude more useful than RAG-papers** —
papers tell you "why ω blowup happens"; the industrial corpus
tells you "APU bay V4 had this exact failure; v7 switched to
laminar and converged."

### Operating procedure (per-case standard moves)

Six mandatory moves after each new industrial case:

1. Write `case_NNN_<name>` reference profile (NOT gold-standard);
   pointer to local case path
2. Append V-series rows for each new death mode → V14, V15, ...
3. Append solver_convergence_playbook decision-tree row (if a new
   pattern class)
4. Fix stale design assumptions discovered this run (parameters,
   schema, docs)
5. Extract artifacts (if reusable engineer hand-work patterns
   surfaced) → land in main project as sub-DEC
6. Inject into RAG corpus (once M6 lands): feed case process logs

### Explicit reject list

Behaviors that look like progress but are negative-value under the
new philosophy:

| Reject | Reason |
|---|---|
| Restart persona-driven dogfood | F1-F15 exhausted; CI smoke covers; continued grinding is negative-value |
| Use toy cases (LDC / backward_step) as primary substrate | Surfaces toy-class problems only; cannot surface industrial-class problems |
| Large UI investments (sizing-field UI, region-refinement UI under old M2-M5 plan) | APU bay falsified UI as entry ticket; UI deferred |
| AI auto-mutate routes (any AI call to mutating endpoint) | Violates V130 advisory-only |
| Use "case count" as KPI | Progress = solver-class coverage breadth + assumption-correction depth, not case count |
| Write charter DEC per new case | sub-DEC scope suffices; only **first-time solver-class introduction** (e.g. first CHT case) warrants charter |

### Compatibility with v2.3 governance

Fully compatible and mutually reinforcing:

- **DEC scope-driven**: new case = sub-DEC (commit message + tests);
  charter only for solver-class first-introduction
- **Codex round cap=3**: marginal-return threshold for industrial
  cases is naturally low; cap prevents over-review
- **Kogami opt-in**: invoked only on first-introduction charter
  level, not per case
- **Counter as pure telemetry**: counting +1 per case is not
  meaningful; what matters is monthly solver-class coverage delta

### Project narrative shift

When describing the project externally, the framing changes:

**Old**: "cfd-harness-unified is a CFD workbench providing full-stack
UI for mesh generation / BC setup / solver control / post-processing
/ AI advisor"
(—sounds like another Fluent shell)

**New**: "cfd-harness-unified is a **container that accumulates
industrial CFD experience**. Every real engineering-grade case
that runs through it deposits another layer of OpenFOAM practical
knowledge. Today's capability = solver-classes covered ×
sediment-depth per class. The AI advisor's leverage is not
OpenFOAM textbooks; it is our own industrial process logs."

### Single-sentence framing

**The project shifts from "building a tool" to "growing a container
that gets stronger with every industrial simulation it digests".
Cases are not test fixtures — they are nutrients. UI is not the
entry ticket — it is a luxury. The AI advisor's corpus is not
papers — it is the death-mode chains we ourselves produced, one
industrial case at a time.**

## Trigger event

User completed `~/Desktop/apu-bay-ventilation/` over one development
day (2026-05-07):

| Dimension | APU bay (one day) | Main project same period (10 days, B-ext-4..6 + N6) |
|---|---|---|
| Geometry | CATIA STEP, 29 named bodies | LDC backward_step (1 cube) |
| Mesh | sHM 943,411 cells, max skew=4.0 | 2,829 cells |
| Solver | buoyantSimpleFoam (compressible buoyant + kωSST→laminar v1) | icoFoam (incompressible single-case) |
| BC coverage | mass-flow / freestream / wall_hot / pressure_outlet / symmetry | velocity / pressure / wall (LDC defaults) |
| Death-mode chain | 13 versions documented (V3→V13) | F11→F15 persona-facing routes |
| Automation | SSOT YAML + 11 scripts + Jinja2 + Makefile | UI 5-step + persona REST chain |

The APU bay case re-used only 5 main-project utility modules
(`geometry_ingest`, `case_scaffold`, `case_bc`, `mesh_quality`,
`audit_package`) via `PYTHONPATH`. **It did not consume any
N2-N5-specific UI surface and did not invoke any AI-mutate path.**

## What this signals

1. **N2-N5 UI is not the critical path.** The assumption "must land
   sizing field UI / region refinement UI / prism layer UI before
   industrial cases work" is falsified. Hand-written sHM template +
   YAML SSOT is sufficient.
2. **CAD ingest is the real entry-point bottleneck.** APU bay needed
   custom code for: CATIA `Import.insert()` name preservation,
   virtual interface face detection (BREP 1:1 face matching fails on
   non-manifold CATIA exports), geometry surgery (decimate-by-tier +
   axial stretch to seal narrow gaps). None of these exist in main
   project; all are reusable.
3. **Solver convergence playbook is missing.** The V3→V13 progression
   (kOmegaSST + zero IC → ω blowup; GAMG p_rgh stuck → switch
   PBiCGStab; DIC SIGFPE on ill-conditioned matrices → diagonal
   preconditioner; mass-flow + zero IC catastrophe → potentialFoam
   warm start or pressure-outlet workaround) is real OpenFOAM
   knowledge that should be codified, not re-derived per case.
4. **persona-driven dogfood is at edge of marginal returns.** F1-F15
   covered the persona-facing surface; B-ext-7+ would surface
   variations of F1-F15 not new failure classes. CI-level smoke
   (`smoke_simulation.py` + `test_persona_facing_smoke_e2e.py` per
   V61-197 close meta-retro) is sufficient regression guard.

## Decision

### A. Close B-extend arc

**No B-ext-7 / B-ext-8 / further**. The B-extend arc (DEC-V61-172
charter through DEC-V61-197 close) is declared closed. Future
persona-facing route changes are addressable as standalone DECs, not
as B-extend continuations.

Marginal-return reasoning: F1-F15 are the persona-facing surface of
the workbench REST API. Continuing to grind toy-case (backward_step,
2829 cells) personas through the same surface produces variations
of known failure classes, not new ones. The valuable signal now
comes from **engineer-driven industrial cases**, which exercise a
different surface (solver convergence, mesh sizing for thin walls
+ narrow gaps, CAD ingest robustness).

CI-level protection against regression on F-series is preserved:
- `ui/backend/tests/test_persona_facing_smoke_e2e.py` (7 tests)
- `scripts/dogfood/smoke_simulation.py` (live-fire entry point)

These ran green at V61-197 close and are wired into both CI lanes
(main pytest + plane-guard WARN-mode re-run).

### B. APU bay = `case_002_apu_bay_industrial` reference profile

A new entry in `.planning/case_profiles/case_002_apu_bay_industrial/`
will document the case as an **industrial reference**, NOT a
gold-standard case. It does not have a verdict-pass criterion (no
benchmark comparison data); it serves as:

1. The substrate for V-series finding extraction (engineer/solver
   surface, parallel to F-series persona/UI surface)
2. The reference architecture for industrial-case workflow (SSOT
   YAML + Jinja2 + 11-script pipeline pattern)
3. The proof artifact for "workbench can do industrial CFD today"

The reference profile points at `~/Desktop/apu-bay-ventilation/` —
the case is **not copied** into the main repository (it is a live,
sometimes-edited industrial sandbox; copying creates drift risk).

### C. Five-artifact extraction (v2.3 sub-DEC scope: each <250 LOC)

| # | Artifact | Destination | Source in APU bay |
|---|---|---|---|
| A1 | CATIA `Import.insert()` name-preserving STEP loader | `ui/backend/services/geometry_ingest/cad_ingest_freecad.py` (new) | `02_domain_subtract.py:102` |
| A2 | Virtual interface face detector (shared / endcap modes) | `ui/backend/services/geometry_ingest/virtual_interface_detector.py` (new) | `02_domain_subtract.py:92` |
| A3 | Geometry surgery (decimate-by-tier + axial stretch) | `ui/backend/services/geometry_ingest/geometry_surgery.py` (new) | `01b_optimize_geom.py` (entire file) |
| A4 | Mass conservation pre-flight check | added to `ui/backend/services/case_bc/writer.py` | `05_make_dicts.py` mass-balance check |
| A5 | Solver convergence playbook (decision tree) | `.planning/methodology/solver_convergence_playbook.md` (new) | V3→V13 history in REPORT.md |

Each artifact lands as a separate commit (v2.3 DEC scope-driven —
sub-DEC with commit-message + tests, no individual full DEC).

### D. V-series finding index (parallel to F-series)

New file `.planning/methodology/industrial_case_solver_findings.md`
seeds with V1-V13 from APU bay's 13-version solver progression.

V-series and F-series are **complementary, non-overlapping**:
- **F-series** = persona/UI surface (route taxonomy, OpenAPI parsing,
  HTTP semantics, response shape)
- **V-series** = engineer/solver internal surface (mesh quality,
  preconditioner choice, BC initial conditions, turbulence model
  stability)

A reciprocal cross-link is added to
`.planning/methodology/workbench_persona_findings.md` (the F-series
SSOT) so future engineers find both indices from either entry point.

### E. Roadmap v2 priority shift (no rewrite, only relabel)

The M1-M6 roadmap from project_cfd_harness_roadmap_v2 is preserved
verbatim. The following labels are added in-line:

| Milestone | Original priority | New label | Rationale |
|---|---|---|---|
| M1 (AI-mutate retirement) | high | unchanged | already in flight, on track |
| M2 (mesh UI) | high | **DOWNGRADED** → focus on "industrial mesh diagnostic advisor" rather than sizing-field UI | template+YAML proven sufficient |
| M2.5 (NEW · CAD ingest hardening) | n/a | **NEW MILESTONE** with A1+A2+A3 as deliverables | industrial entry-point surface, highest wear |
| M3 (physics UI) | medium | **SPLIT**: schema first, UI deferred | APU bay needs buoyantSimpleFoam + kωSST schema today |
| M4 (BC + solver controls) | medium | **UPGRADED** → priority above M2; codify fvSolution debugging chain | APU bay 13-version trail lives here |
| M5 (post-processing) | medium | unchanged | not the bottleneck |
| M6 (AI advisor stack) | last | **PARALLELIZE** with M2.5/M3/M4 | V-series + APU bay logs are natural RAG corpus |

The relabel does not invalidate any in-flight work; it changes the
priority queue for next-DEC selection.

### F. Monthly industrial-case dogfood (S5)

Going forward, **one new industrial case per month** as primary
dogfood substrate. APU bay = month 0 (May 2026). Candidate
sequence: intake diffuser, heat exchanger internal flow,
fan-stator passage, turbocharger volute. Each run produces V-series
finding deltas; each run is recorded in
`.planning/case_profiles/case_NNN_<name>/`.

This replaces "B-extend live-persona dogfood" as the primary
quality signal.

## Why this charter (not a sub-DEC)

Per v2.3 DEC scope: a charter / governance-rule-change / cross-≥3-modules
DEC warrants full DEC schema. This decision:

- **Cross ≥3 modules**: geometry_ingest (3 new files), case_bc (1
  modification), methodology docs (2 new files), case_profiles (1 new
  reference), roadmap relabel, B-extend arc closure
- **Governance-rule-equivalent**: changes the dogfood substrate from
  toy-case + persona to industrial-case + engineer; changes the
  priority order of M1-M6
- **Charter**: states a strategic stance ("workbench is industrial-CFD
  capable today; bottleneck is CAD ingest + convergence playbook")
  that future DECs are subordinate to

## What this charter does NOT do

- Does NOT invalidate any merged work in V61-172..V61-197
- Does NOT modify the v2.3 governance baseline (Kogami opt-in, Codex
  round cap=3, etc., all preserved)
- Does NOT delete or rewrite the M1-M6 roadmap; only re-labels
  priority within
- Does NOT copy APU bay code into the main repo wholesale; only the
  5 enumerated artifacts are extracted, with generic refactoring
- Does NOT commit to monthly cadence as a hard requirement; "month +
  case" is a target, not a scheduling gate (per project rule "no
  date / schedule gating")

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| APU bay is N=1; over-generalizing from one case | Extract only the 5 enumerated artifacts; observe 1-2 more industrial cases before further roadmap restructure |
| CAD ingest portability beyond CATIA STEP (NX / SolidWorks / CREO) | A1's `Import.insert()` trick is FreeCAD-specific; mark cad_ingest_freecad.py as "FreeCAD path"; future NX/SW/CREO paths are separate sub-DECs |
| Closing B-extend arc loses persona-facing quality signal | smoke_simulation.py + test_persona_facing_smoke_e2e.py preserve regression coverage; F-series index remains live for future additions |
| Roadmap relabel confuses next-DEC selection | This DEC ships before any next sub-DEC; cross-reference is mandatory in next-DEC frontmatter `parent_dec` |

## Counter

DEC-V61-198: +1 (`autonomous_governance: true` — strategic decision,
no external gate). New cumulative counter advances by 1 per
RETRO-V61-001.

## Files changed (this DEC + immediate followups)

This DEC itself:
- `.planning/decisions/2026-05-07_v61_198_apu_bay_strategic_pivot.md` (this file)

Immediate followups (separate commits, sub-DEC scope):
- `.planning/methodology/solver_convergence_playbook.md` (A5)
- `.planning/methodology/industrial_case_solver_findings.md` (B)
- `.planning/methodology/workbench_persona_findings.md` (F↔V cross-link)
- `.planning/case_profiles/case_002_apu_bay_industrial/INDUSTRIAL_CASE_PROFILE.md`
- `ui/backend/services/geometry_ingest/geometry_surgery.py` (A3 starter; A1+A2+A4 next session)

## References

- `~/Desktop/apu-bay-ventilation/README.md` — case overview
- `~/Desktop/apu-bay-ventilation/evidence/v13_post_v5_183632/REPORT.md` — V3→V13 progression
- DEC-V61-130 — AI-as-advisor strategic turn (parent)
- DEC-V61-133 — v2.3 governance simplification baseline
- DEC-V61-172 — B-extend charter (closed by this DEC)
- DEC-V61-197 — B-extend-6 close (last sub-DEC of B-extend arc)
- `.planning/methodology/workbench_persona_findings.md` — F-series index
- project memory `project_cfd_apu_bay_strategic_pivot.md` — durable plan trace

## Status update (2026-05-12)

Audit pass confirms all §C artifacts and §"Files changed" followups
have landed; the charter is operationally complete. Status field
remains `Accepted` — no flip needed, this is just a closure note.

| Artifact | Status | Landed at |
|---|---|---|
| A1 `cad_ingest_freecad.py` | ✅ | `ui/backend/services/geometry_ingest/cad_ingest_freecad.py` |
| A2 `virtual_interface_detector.py` | ✅ | same dir |
| A3 `geometry_surgery.py` | ✅ | same dir |
| A4 mass-balance pre-flight | ✅ | `ui/backend/services/case_bc/writer.py::check_mass_balance` (commit `3b21802` · this audit) |
| A5 `solver_convergence_playbook.md` | ✅ | `.planning/methodology/` · 327 lines |
| V-series seed (V1-V13) | ✅ extended | `.planning/methodology/industrial_case_solver_findings.md` · 824 lines, V1-V51+ |
| F↔V cross-link | ✅ | `.planning/methodology/workbench_persona_findings.md` · 298 lines |
| case_002 reference profile | ✅ split | `case_profiles/case_002a_apu_bay_buoyant_simple.md` + `case_002b_apu_bay_cht.md` |

The §F monthly industrial-case dogfood substrate target has been
exceeded: as of audit, case_003..016 have sedimented (CRM-HLS BL /
NREL phase VI MRF / RAE M2129 / ONERA M6 / KCS ship VOF / GLC305
IRT / Sandia Flame D / DrivAer LES / plate-fin CHT / HVAC diffuser /
Vattenfall T-junction / M219 cavity DES), driving V-series to V51+
and S-series to S21+. The "container that accumulates industrial CFD
experience" framing is materializing as designed.

A4 was the only artifact still owing at audit time. It is implemented
as advisory (returns `MassBalanceCheck` dataclass, never blocks) and
adapts the APU bay source to the main-repo schema, which has no
`mass_flow_outlet` BC variant (relief check covers `PressureOutletBC`
and `InletOutletBC` instead).

**Notion sync drift**: this addendum drifts the local DEC from the
2026-05-07 Notion mirror. Session-end batch sync should re-push.
