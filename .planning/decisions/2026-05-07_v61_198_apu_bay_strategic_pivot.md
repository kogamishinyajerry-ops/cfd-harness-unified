---
decision_id: DEC-V61-198
title: APU bay industrial signal · close B-extend arc · 5-artifact extraction · roadmap v2 priority shift · M2.5 CAD ingest hardening as new milestone
status: Accepted
parent_dec: V61-130
phase: strategic-pivot
notion_sync_status: pending
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
