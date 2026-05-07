---
decision_id: DEC-V61-145
dec_id: DEC-V61-145
title: N4 phase charter · BC + solver unification (Physics setup workbench under Step 3)
status: Accepted
parent_dec: V61-130
phase: N4
notion_sync_status: pending
parent_artifacts:
  - .planning/strategic/blueprint_v3_2026-05-07.md
  - .planning/strategic/n3_n6_outline_2026-05-07.md
  - .planning/decisions/2026-05-06_v61_130_strategic_pivot_ai_advisor.md
  - .planning/decisions/2026-05-06_v61_132_n1_2_mutating_routes_registry_behavioral_contract.md
  - .planning/decisions/2026-05-07_v61_133_governance_simplification_b_plus.md
  - .planning/decisions/2026-05-07_v61_134_n2_mesh_control_parity_charter.md
  - .planning/decisions/2026-05-07_v61_139_n3_physics_materials_charter.md
trigger: V130 charter mandates workbench-first parity build-out; M4 (BC + solver unification) is the post-N3 capability phase that turns Step 3 from "BC face annotation only" into the full "Physics setup workbench" carrying BC + solver dict + URF + timing + raw escape hatch.
autonomous_governance: true
counter_impact: +1
codex_review_relay: pending
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-07
confidence: med
---

# DEC-V61-145 · N4 Phase Charter · BC + Solver Unification

## Status

**Accepted 2026-05-07** — user mandate "继续 N4". N3 phase closed cleanly
(N3.0 charter + N3.1-N3.5 sub-DECs all Accepted). N4 begins per
blueprint v3 §convergence sequencing.

## Context

V130 (strategic pivot · 2026-05-06) established AI as advisor. N1
closed AI-as-actor; N2 delivered engineer-driven mesh control; N3
delivered structured material + regime contracts. **N4 is the BC +
solver-config parity phase** — converts Step 3 from a single-purpose
BC face-annotation view into a full "Physics setup workbench"
holding BC type per patch + solver dict (fvSchemes / fvSolution) +
URF + controlDict timing + raw-edit escape hatch.

## Naming clarification

The N3-N6 outline §2 wording "Step 3 + Step 4 merge" was imprecise.
The current code base has:

| StepId | Current component | Role |
|---|---|---|
| 1 | `Step1Import.tsx` | geometry import |
| 2 | `Step2Mesh.tsx` | mesh control |
| 3 | `Step3SetupBC.tsx` | BC face annotation only (single-purpose) |
| 4 | `Step4SolveRun.tsx` | solver run (kick off + watch residuals) |
| 5 | `Step5ResultsView.tsx` | post-processing |

**N4 does NOT remove or merge Step 4.** Step 4 remains the solver-
run step. What "merges" is: Step 3 absorbs the solver-CONFIG
functionality (dict editor + URF + timing) that would otherwise have
required a separate panel. After N4: Step 3 = "Physics setup workbench"
holding everything between mesh and run; Step 4 unchanged.

## Decision

Adopt the **N4 six-step phase plan** in `.planning/strategic/n3_n6_outline_2026-05-07.md` §2:

| Sub-phase | Capability | Slim DEC ID (planned) | Risk | Pre-merge Codex? |
|---|---|---|---|---|
| **N4.1** | BC type per-patch palette: inlet (velocity / volumetric / massFlow) · outlet (pressureOutlet / inletOutlet) · wall (noSlip / movingWall) · symmetry / cyclic / empty | DEC-V61-146 | medium | per Opus confidence |
| **N4.2** | Solver dict editor: schema-aware fvSchemes + fvSolution editor with diff against derived defaults from N3.4/N3.5 | DEC-V61-147 | medium | per Opus confidence |
| **N4.3** | URF panel: per-equation under-relaxation; visual stability advisor (read-only) hints when URF too high vs regime | DEC-V61-148 | medium | per Opus confidence |
| **N4.4** | RawDict escape hatch unification: per-dict copy-to-clipboard + read-back from disk | DEC-V61-149 | low | no |
| **N4.5** | controlDict timing: endTime + writeInterval + adjustTimeStep + maxCo (when transient) | DEC-V61-150 | low | no |

**Sequencing**: strict serial N4.1 → N4.2 → N4.3 → N4.4 → N4.5.

## Rationale

### Why charter DEC, not 5 slim DECs only

Per V133 §2.2 scope-driven rule, charter DEC required when scope
spans ≥3 modules **and** introduces a new architectural surface. N4:

- Adds `services/case_bc/` (NEW or extends existing case_solve/bc_setup)
  — structured BC contract per patch
- Modifies `services/case_dicts/` (extends allowlist + adds structured
  fvSchemes/fvSolution writer)
- Modifies `services/case_solve/solver_profiles/` (consumes N3.4
  derivation as default-with-override)
- Adds `routes/case_bc.py` + `routes/solver_dicts.py` (NEW V132 mutators)
- Modifies `services/ai_actions/mutating_routes.py` (V132 registry)
- Modifies frontend Step 3 (replace single-purpose with workbench
  layout) — multiple test files
- Modifies `pages/workbench/step_panel_shell/types.ts` (new schemas)

Cross 7+ modules + new structured architectural surface + 2 new V132
mutators = full charter DEC pattern.

### Why this sequence

- **N4.1 first**: BC contract is the foundation; `bc_setup_from_stl_patches.py`
  already has the face-annotation infrastructure — N4.1 builds the
  structured BC-type-per-patch contract on top
- **N4.2 second**: solver dict editor consumes the BC contract +
  N3.4 solver derivation; depends on N4.1 schema to know what fields
  need writing in `0.orig/{U, p, T, ...}`
- **N4.3 third**: URF panel modifies the same `system/fvSolution`
  file the dict editor writes; building URF first would force
  rewrites when N4.2 lands
- **N4.4 fourth**: raw escape hatch is read/copy-only; depends on
  the structured dicts existing first so it has something to copy
  FROM. Building first would mean copy-paste of legacy hand-crafted
  dicts, which is exactly what we're replacing
- **N4.5 last**: timing controls are a small additive form on top
  of `system/controlDict`; controlDict already exists from
  bc_setup.py legacy path, but N4.5 turns its timing fields into
  structured editor surface

### Why no parallel sub-DEC work within N4

Same reasoning as N2/N3 charters:
1. Schema coordination overhead between N4.1 BC contract + N4.2 solver
   dict consumer
2. V132 registry migration order — N4.1 + N4.2 each add a mutator;
   single migration when the second lands is cleaner than two
3. Codex review chain stays auditable per sub-DEC (V133 cap=3)

**N6 parallel-eligible after N4.2 stabilizes** the solver-dict shape
that N6 advisor reads.

## UI contract change (charter §risk-register row 1)

Step 3 panel placement changes from "single-purpose BC view" to
"workbench with multiple panels". URL `?step=3` continues to resolve
to the same StepId. **Backwards-compat strategy**:

1. `Step3SetupBC.tsx` is renamed to `Step3PhysicsSetup.tsx` (file move
   + import update) in N4.1
2. The existing BC face-annotation UI moves into the new workbench's
   "BC palette" panel — no behavior change for Step 1+2 → BC flow
3. Already-saved cases (with face annotations + classifications)
   continue to work — N4.1 reads existing `face_annotations` /
   `patch_classifications` sidecar files unchanged
4. Step IDs 1-5 remain unchanged (`StepId = 1 | 2 | 3 | 4 | 5`); no
   URL redirect needed

This avoids the URL-redirect complexity the outline §risk-register
worried about; Step 4 was never going to be removed.

## Workbench-first acceptance (V130 Principle B)

Every N4 sub-DEC MUST satisfy these gates before Status=Accepted:

1. **Q1 LLM-offline reachability**: with `LLM_PROVIDER=disabled`, engineer
   completes BC setup + solver dict edit + URF tune + raw escape via
   forms only. No LLM call required.
2. **Q2 artifacts output**: writes manifest into `0.orig/{U, p, T, k, ω, ε}`
   + `system/{fvSchemes, fvSolution, controlDict}`. Engineer can `cat`
   the case directory and see legible OpenFOAM dicts.
3. **Q3 audit explainable**: TrustGate (or successor) shows BC fill rate
   per patch + dict-vs-derived-default diff + URF override count. Trail
   records dict SHA on commit.
4. **Q4 AI advisory only**: any AI helper added is read-only. URF
   "stability advisor" surfaces hints in the UI but never auto-tunes.
   New AI helpers MUST register in V132 dispatch path with
   `is_mutating_route() == False`.

## Out of scope

- Parallel decomposition options (decomposeParDict editor) — M4-extend
- Dynamic mesh / MRF / FSI — M4+ in roadmap_v2
- Custom function-object editor beyond residual sampling — M5-extend
- Solver-execution control (Step 4 / `Step4SolveRun.tsx` keeps current
  shape) — would be a separate charter
- Compressible solvers (rhoSimpleFoam, sonicFoam, etc.) — depend on
  M3-extend compressibility regime

## Threat model

| Threat | Vector | Mitigation |
|---|---|---|
| New `POST /api/cases/{id}/bc` mis-registered as read-only, bypassing V132 | Forgetting to add to `MUTATING_ROUTES` in N4.1 | Layer-C AST namespace-binding test catches; PR check `ai-path-mutation-grep` warns; sub-DEC N4.1 acceptance §3 explicit |
| New `POST /api/cases/{id}/solver-dicts` mis-registered, same | Forgetting in N4.2 | Same as above; Layer-A patched-function sentinel + AST test |
| Schema-aware fvSchemes/fvSolution editor produces dicts solvers reject | Missing key validation | Tests exercise icoFoam / simpleFoam / pimpleFoam / buoyantSimpleFoam round-trip; rejected dicts surface 422 with structured `failing_check: scheme_invalid_for_solver` |
| URF advisor heuristics auto-tune (V132 violation) | Sliding scale of "advice" | Stability advisor is pure read-only function returning `list[StabilityHint]`; render as hints in panel; no `setUrf()` mutation path. Test asserts no `commit*` API call from advisor surface |
| Raw escape hatch loses engineer's edits | Stale read on subsequent overwrite | N4.4 records SHA of disk state at read time; commit checks SHA still matches before overwrite; mismatch → 409 conflict |
| Step 3 layout regression for already-saved cases | Existing face annotations / classifications break | N4.1 acceptance includes regression test loading 3 fixture cases (LDC / channel / elbow_duct) and asserts BC fill rate matches pre-N4 snapshot |
| controlDict timing editor lets transient endTime be set on steady solver | endTime > 0 with simpleFoam | N4.5 reads N3.4 derived solver + warns when timing values mismatch family (`steady` solvers ignore deltaT/maxCo) — INFO hint, not blocker |

## Verification (charter-level)

- [x] Outline doc `.planning/strategic/n3_n6_outline_2026-05-07.md` §2 reachable
- [ ] Sub-DECs N4.1-N4.5 use **slim 6-field** schema (per V133 §2.2)
- [ ] Each sub-DEC PR includes Blueprint v3 four-question gate results
- [ ] N4 phase counter increments only by sub-DEC count (charter +1, sub-DECs +5 → N4 final delta = 6)
- [ ] N6 charter (DEC-V61-151 planned) explicitly waits on N4.2 acceptance commit SHA

## Counter / governance bookkeeping

- `counter_impact: +1` (charter DEC)
- Sub-DECs: +5 (N4.1-N4.5)
- N4 phase total counter delta: **+6**
- No Kogami review (opt-in per V133; charter implements V130, not a
  governance-rule change)

## Calibration window

Track during N4 execution:
- R0 Codex APPROVE rate on sub-DECs (target ≥30% per V133 calibration)
- Number of sub-DECs hitting V133 round cap=3 (target = 0)
- Workbench-first gate fails (target = 0)
- BC fill-rate test regression count for the 3 fixture cases (target = 0)

If sub-DEC count exceeds 5 (e.g., N4.x emerges for compressible BCs),
update charter with `Status: Amended` and append new sub-DEC IDs.

## Self-bootstrap exception

Standard authoring path applies — N4 is a child of V130, not a
governance-rule-change DEC.

## References

- DEC-V61-130 · Strategic pivot to AI-as-advisor
- DEC-V61-132 · MUTATING_ROUTES registry contract
- DEC-V61-133 · B+ governance simplification
- DEC-V61-134 · N2 phase charter
- DEC-V61-139 · N3 phase charter
- DEC-V61-144 · N3.5 (immediate predecessor — closes N3)
- `.planning/strategic/blueprint_v3_2026-05-07.md`
- `.planning/strategic/n3_n6_outline_2026-05-07.md`
