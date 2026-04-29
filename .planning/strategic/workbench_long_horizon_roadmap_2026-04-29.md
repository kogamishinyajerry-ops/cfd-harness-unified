# Workbench Long-Horizon Roadmap — 2026-04-29
## Single-user CFD Automation Workbench · Self-Evolution Edition

**Status**: PROPOSAL · Draft v1 · awaiting CFDJerry ratification
**Authority**: Pivot Charter Addendum 3 §4.c (post-M8 future scope · this doc proposes that future)
**Authored under**: CFDJerry direction 2026-04-29 — *"暂时不考虑成熟SaaS，先作为单用户的CFD自动化工作台，来进行深度的优化开发。最重要的是：能配合人类工程师完成任意的简单3D几何的全流程仿真设置、仿真、后处理、归档、学习……这样整个项目就可以运转起来了，真正意义上获得了自进化能力，还提升了人类工程师的效率"*
**Counter impact**: NONE (planning doc · not a DEC · ratification will spawn a charter addendum or kickoff DEC chain)
**Horizon**: 12-18 months (post-M8 closure, ~end of Charter Addendum 3 hard ordering)
**Successor format**: each milestone listed here will become its own kickoff DEC at startup, mirroring V61-094/095/096/098 pattern

---

## §0 · Why this document exists

Charter Addendum 3 §4.c hard ordering (M-VIZ → M-RENDER-API → M-PANELS → M-AI-COPILOT → M7 → M8) covers the next ~2 months of work. After M8 (stranger dogfood on the new step-panel UI), the roadmap is **uncharted**. CFDJerry asked for deep, long-horizon planning that turns the workbench into a product that:

1. Handles **any** simple 3D geometry (not just LDC fixture) end-to-end
2. Runs the **full lifecycle**: setup → simulate → post-process → archive → **learn**
3. Achieves **self-evolution capability** — every completed case makes the next case easier
4. **Amplifies** the human engineer's productivity rather than replacing them

This document fixes the post-M8 milestone sequence, the closed feedback loop, and the integration with the existing strategic spine (P1-P6 + Knowledge Object Model). It is **not** a charter modification (Pivot Charter §1 + Addendums 1-3 unchanged); it is the implementation arc that operationalizes Charter §3 ("Case Intelligence Layer") for the workbench-driven path.

---

## §1 · The closed loop (the strategic centerpiece)

```
   ┌─────────────────────────────────────────────────────────────┐
   │                    THE SELF-EVOLUTION LOOP                  │
   │                                                             │
   │  arbitrary 3D geom (STL · STEP · IGES)                      │
   │       ↓ [intake]                                            │
   │  geometry semantics annotated                               │
   │  (face_annotations.yaml · M-AI-COPILOT primitive)           │
   │       ↓ [meshing]                                           │
   │  mesh w/ engineer-validated quality                         │
   │  (Mesh Wizard · cell estimate · BL prisms)                  │
   │       ↓ [physics setup]                                     │
   │  BC + turbulence + solver                                   │
   │  (AI-suggested · engineer-confirmed)                        │
   │       ↓ [solve]                                             │
   │  OpenFOAM in Docker · live SSE residuals                    │
   │       ↓ [verdict]                                           │
   │  TrustGate auto-decision (P1 spine)                         │
   │       ↓ [post-process]                                      │
   │  vtk.js paraview-grade · slices · streamlines               │
   │       ↓ [archive]                                           │
   │  case → CaseProfile (P4 KO #1)                              │
   │  run  → SimulationObject + ExecutionArtifacts (P4 KO #3+#4) │
   │  failure traces → FailurePattern (P4 KO #6)                 │
   │  successful fixes → CorrectionPattern (P4 KO #7)            │
   │       ↓ [learn]                                             │
   │  next case starts from accumulated knowledge:               │
   │   • similarity recommender                                  │
   │   • inherited setup from prior case                         │
   │   • failure-pattern early warnings                          │
   │   • correction-pattern auto-suggestions                     │
   │       ↑                                                     │
   │  (loop closes — self-evolution achieved)                    │
   └─────────────────────────────────────────────────────────────┘
```

**Critical insight**: the workbench is the FRONT-END for the entire CFD Harness OS. Every workbench run is a **training signal** for the OS. Once this loop runs end-to-end for ONE arbitrary case, the project compounds — the 2nd case takes less time than the 1st, the 100th case is dramatically faster than the 10th.

**This is the differentiator.** Commercial CAE workbenches (ANSYS Workbench, Star-CCM+, Helyx) do NOT have this property — each case starts from scratch unless the engineer manually maintains a template library. By baking the Knowledge Object Model into the workbench from day 1, every engineer-AI interaction permanently improves the system.

---

## §2 · What this roadmap explicitly DROPS

Per CFDJerry 2026-04-29: "暂时不考虑成熟SaaS". The following capabilities are EXPLICITLY out of scope for this 12-18 month horizon:

| Dropped | Why | When may revisit |
|---|---|---|
| Multi-tenancy / accounts / billing | Single-user product | After loop runs robustly for CFDJerry's own use ≥6 months |
| Cloud bursting (AWS / GCP / Azure) | Local Docker is enough for one engineer | When solve queue depth > 1 case/day sustained |
| Real-time collaboration (multi-user same case) | Solo workflow | Never within this charter |
| Parametric DOE / response surface / surrogate-driven adaptive sampling | Single-user can drive batch matrix manually | When loop is closed AND engineer wants 100+ similar cases |
| Adjoint sensitivity / shape optimization | Single-user research scope | After Era 3 (self-evolution) is mature |
| CI/CD pipeline integration | Engineer-driven cadence, not automated | Never within this charter |
| Plugin marketplace / 3rd-party solvers | Single OpenFOAM 10 spine per Charter §1 C19 | Never within this charter |
| Workbench-as-a-library API (other tools call workbench) | Workbench is the destination, not a dependency | Never within this charter |

**This list is a feature.** Saying NO to these enables saying YES to the self-evolution loop with focused, single-user-grade quality.

---

## §3 · Capability axes (what gets deepened)

Eight axes, each evolves across the four post-M8 eras:

| # | Axis | Today (post-M-AI-COPILOT) | End of Era 4 (M22) |
|---|---|---|---|
| 1 | **Geometry intake** | STL (mostly LDC) + Tier-A face-pick | STL/STEP/IGES + auto-feature-recognition + named selections |
| 2 | **Meshing** | gmsh + snappyHexMesh stub, single mode | Wizard with BL prisms, refinement zones, mesh-independence auto-study |
| 3 | **Physics** | icoFoam (laminar incompressible) | RANS turb (k-ω SST + k-ε) + heat transfer (CHT + buoyancy) + compressible (rhoSimpleFoam) |
| 4 | **Solver routing** | hard-wired icoFoam | auto-pick simpleFoam/pimpleFoam/buoyantSimpleFoam/rhoSimpleFoam from physics flags |
| 5 | **Post-processing** | residual chart + z=0 slice PNG | vtk.js paraview-grade: slices · isosurfaces · streamlines · probes · custom expressions |
| 6 | **V&V** | Gold Standard offline only | TrustGate per-run + auto mesh-independence + Richardson GCI verdict |
| 7 | **Archive** | case_manifest.yaml + audit-package | every run → P4 KOs (CaseProfile + SimulationObject + ExecutionArtifacts + Provenance) |
| 8 | **Learn** | NONE | similarity recommender + failure-pattern warnings + correction-pattern playback + recipe library |

---

## §4 · Roadmap eras

### Era 1 · LOOP SPINE — Any simple 3D geometry, full lifecycle (M9-M14)

Goal: take any simple 3D geometry from intake to archive end-to-end. The loop is closed but learning is shallow (single case at a time, no cross-case memory yet).

**Critical path**. M9-M14 are the milestones that the strategic claim "workbench handles any simple 3D geom" depends on.

#### M9 · Tier-B AI rule-based classifier (post-M-AI-COPILOT extension) — **ACCEPTED 2026-04-30**
- **Problem**: M-AI-COPILOT Tier-A demos the dialog flow on LDC with a forced-blocked flag. For a real arbitrary STL, the AI must actually have something to say.
- **Scope**: rule-based classifier reading `face_annotations.yaml` + polyMesh boundary geometry:
  - axis-alignment heuristic (face normal close to ±x/±y/±z → likely a wall or symmetry plane)
  - face-area clustering (tiny faces grouped → likely an inlet/outlet; vast face → likely a wall)
  - topology (faces on the convex hull of the geometry → external boundaries; internal → ducts)
  - sphericity / aspect-ratio heuristics for inlet vs outlet disambiguation
- **Output**: AIActionEnvelope with `confidence: uncertain`, candidate face_ids + default_answer for each `UnresolvedQuestion`. User confirms or corrects via face-pick.
- **Dependencies**: M-AI-COPILOT Tier-A merged.
- **Success criteria**: 5 canonical "simple 3D" geometries classified with ≥70% accuracy on the AI-suggested defaults (engineer corrects ≤30% of patches). Geometries: pipe (straight), pipe (elbow), flange, simple manifold, external sphere bluff body.
- **Self-pass-rate estimate**: 60% (heuristic classifier — easy to overfit to the 5 fixtures, easy to break on the 6th).
- **§11.1 BREAK_FREEZE**: not consumed (post-M-AI-COPILOT, dogfood window quota exhausted; this rides under normal feature-freeze rules).
- **As-shipped (DEC-V61-100)**: aspect-ratio-based ldc_cube vs non_cube split (5%-tolerance · classifier confident on cube only with verified top-plane lid pin · classifier confident on non_cube with verified inlet+outlet pins). Multi-q dialog UX hardened (DEC-V61-100 Step 3 · Codex 3-round arc R3 APPROVE) for the rapid-double-pick race + ai_mode toggle staleness. The "5 fixtures" success criterion is conditionally met: classifier handles axis-aligned cube + non-cube via name-substring-match on inlet/outlet pins · richer geometry-class detection (curved pipes · sphericity heuristics) deferred to a future tightening if real-world fixtures show the substring match insufficient.

#### M9.5 · Minimal laminar channel executor (DEC-V61-101 · ACCEPTED 2026-04-30)
- **Problem**: M9 classifier emitted inlet+outlet face questions for non-cube geometries but the only downstream executor (setup_ldc_bc) was LDC-shaped. Engineer pinned faces, dialog returned `blocked: non-LDC executor pending M11/M12` — annotations saved, nothing solvable.
- **Scope (intentionally bounded)**: laminar icoFoam executor that mirrors setup_ldc_bc but routes the boundary into 3 patches (inlet · outlet · walls) by face_id match against user-pinned annotations. No turbulence model · no BL prism control · no BC override UI.
- **Out of scope (preserved for M11/M12)**: turbulence (k-ω SST · k-ε · Spalart-Allmaras), boundary-layer prism control, refinement zones, compressible flow, heat transfer, multi-inlet velocity differentiation, BC value editing UI.
- **As-shipped**: setup_channel_bc + classifier-executor parity (face_id verification before confidence, mirroring the Codex M9 Step 2 R2 lesson) + idempotency hardening (polyMesh.pre_split backup invalidation on Step 2 re-mesh, Codex 3-round arc R3 APPROVE). Multi-inlet "merge by name substring" implicitly supported and now under test. Defaults locked: U_inlet=(1,0,0) m/s · p_outlet=0 · ν=0.01 (Re~100 on unit-section channels).

#### Agent-runnable dogfood smoke (`scripts/smoke/dogfood_loop.py` · 2026-04-30)
- **Problem**: human visual-smoke gating ("Awaiting CFDJerry") couldn't be agent-triggered, so the dev workflow stalled on every DEC closure.
- **Scope**: TestClient-based exec of the §4a LDC + §4c channel + §7 negative-paths loops · spawns a Vite dev server on an ephemeral port to verify the frontend boots cleanly. Replaces the previous human-smoke gate as the DEC-acceptance check.
- **Acceptance**: `PYTHONPATH=. .venv/bin/python scripts/smoke/dogfood_loop.py` exits 0.
- **Out of scope**: real `icoFoam` solve in Docker (Step 4 validation) and real face-pick from the 3D viewport remain "human-only" notes in the dogfood guide and are not gates.

#### M10 · STEP/IGES intake (folds in M6.0/M6.1 already-Accepted)
- **Problem**: SolidWorks/CATIA/FreeCAD users export STEP/IGES, not STL. STL discards CAD topology — feature recognition is impossible.
- **Scope**: STEP/IGES upload route → gmsh (with OpenCASCADE backend) tessellates to STL → existing M5.0 pipeline takes over. Crucially: gmsh PRESERVES the named selections from CAD (`Inlet`, `Outlet`, `Wall_1` etc.) when present, so face-pick can be skipped if the engineer has already labeled in CAD.
- **Dependencies**: M9 Tier-B AI (so AI can fall back when CAD has no named selections).
- **Success criteria**: import a SolidWorks STEP file with named selections → patches arrive labeled, no face-pick needed → mesh → solve.
- **Self-pass-rate estimate**: 65% (gmsh OCC integration has known quirks: STEP version compatibility, units inconsistency).

#### M11 · Mesh Wizard v1 (replaces snappyHexMesh stub)
- **Problem**: Step 2 currently uses a hardcoded mesh strategy. For arbitrary geom, the engineer needs:
  - cell-count estimator BEFORE meshing (so they don't run a 50M-cell job by accident)
  - boundary layer prism control (y+ target, layer count, growth rate)
  - refinement zones (refine near small features, coarsen in far-field)
- **Scope**:
  - cell-count predictor (volume / target cell size + boundary adjustment) with hard cap at 5M cells (per CFDJerry's M7 Wizard ask)
  - BL prism wizard: AI suggests y+ target based on physics (Re, turb model); engineer confirms layer count + growth
  - refinement-zone painter: engineer paints box/sphere refinement regions on the 3D viewport (extends face-pick UI)
  - foamyHexMesh and cfMesh as alternative backends for tetrahedral and hex-dominant
- **Dependencies**: M-AI-COPILOT Viewport pickMode (for refinement-zone painter).
- **Success criteria**: arbitrary STL → wizard recommends cell count + BL setup → engineer adjusts → mesh runs → snappyHexMesh quality metrics in viewport → engineer accepts.
- **Self-pass-rate estimate**: 50% (multi-axis interaction: cell estimator + BL physics + refinement UI is structurally complex).

#### M12 · Multi-physics + multi-solver routing (turbulence + heat)
- **Problem**: icoFoam covers laminar incompressible only. "Any simple 3D geom" means at minimum: turbulent flow + steady heat transfer + buoyancy.
- **Scope**:
  - Solver registry: `simpleFoam` (steady RANS), `pimpleFoam` (transient RANS), `buoyantSimpleFoam` (steady CHT + buoyancy), `rhoSimpleFoam` (steady compressible)
  - physics-flag → solver auto-pick (steady? transient? compressible? heat? buoyancy? → unique solver name)
  - turbulence model selector: k-ω SST (default for external aero), k-ε realizable (industrial flows), Spalart-Allmaras (aerospace)
  - auto y+ post-mortem: after first iter, if y+ is wrong for the chosen turb model, warn + suggest mesh fix or wall-function swap
  - boundary-condition library: turbulence inlet (TI + TLength → k + ω + ε), wall (no-slip + temperature), outlet (zero-grad)
- **Dependencies**: M11 Mesh Wizard (for BL prism layers, required for low-Re turb models).
- **Success criteria**: 5 canonical cases run end-to-end with auto-picked solver: laminar pipe (icoFoam), turbulent pipe (simpleFoam + k-ω SST), heated cavity (buoyantSimpleFoam), high-speed nozzle (rhoSimpleFoam), transient vortex shedding (pimpleFoam).
- **Self-pass-rate estimate**: 45% (LARGEST surface yet — 4 new solvers + 3 turb models + ~12 BC types · each combination has fragility modes).

#### M13 · Post-processing v1 (paraview-grade vtk.js)
- **Problem**: today's "results" view is a single z=0 PNG. For real engineering work the user needs slices in any direction, isosurfaces, streamlines, probes.
- **Scope**:
  - field selector (U, p, T, k, ω, alpha, custom expressions)
  - slice plane: arbitrary normal + offset, dragged in 3D viewport
  - isosurface at threshold value (vorticity, Q-criterion, scalar fields)
  - streamline / particle trace from seed points or seed regions
  - probe at (x,y,z) → time-series for transient runs, single value for steady
  - field-on-patch (color by field on a boundary, e.g. wall heat flux on a heat exchanger)
  - export to ParaView state file (`.pvsm`) for engineers who want to deep-dive
- **Dependencies**: M-RENDER-API field/{name} endpoint already exists; needs extension to support arbitrary slices and isosurfaces server-side.
- **Success criteria**: load a transient case, drag a slice plane, scrub through time, place 3 probes, export state file to ParaView and confirm parity.
- **Self-pass-rate estimate**: 60% (vtk.js has paraview-grade primitives but composing them with our state model takes care).

#### M14 · Auto V&V (TrustGate + mesh independence)
- **Problem**: every run today gets a binary "succeeded / FOAM Fatal" verdict. Engineer doesn't know if the result is grid-converged.
- **Scope**:
  - TrustGate per-run verdict integrated into Step 5 (3-state: PASS, PASS_WITH_DISCLAIMER, FAIL · already designed in P1)
  - auto mesh-independence study: run at 3 cell counts (coarse/medium/fine), compute Richardson extrapolation, report GCI (Grid Convergence Index)
  - if GCI > 5% → DISCLAIMER ("results may not be grid-converged; recommend finer mesh")
  - if monotonic divergence detected → FAIL with diagnostic
  - tolerance comes from CaseProfile (from P1 / RETRO-V61-004)
- **Dependencies**: M11 Mesh Wizard (need cell-count handle to vary), P1 TrustGate already in spine.
- **Success criteria**: arbitrary STL → solve → TrustGate verdict displayed in Step 5 with GCI percentage and grid-conv plot.
- **Self-pass-rate estimate**: 55% (multi-mesh runs sequentially × verdict logic × tolerance from CaseProfile = several integration seams).

**End of Era 1 milestone**: workbench handles any simple 3D geometry end-to-end (intake → mesh → setup → solve → post → verdict). Loop is CLOSED for one case at a time. **No learning yet.**

### Era 2 · ARCHIVE + LEARN — The self-evolution payoff (M15-M18)

Goal: every completed case feeds back into the system so the NEXT case is easier. This is the strategic differentiator.

**M15-M18 are the highest-value milestones in this entire roadmap.** Without them the workbench is "ANSYS Workbench but cleaner" — useful but commodity. With them the workbench is "an organism that learns from every case."

#### M15 · Knowledge Object integration (workbench → P4)
- **Problem**: P4 KOs (CaseProfile, SimulationObject, ExecutionArtifacts, Provenance, FailurePattern, CorrectionPattern, GoldStandard, AttributionReport) are defined in `docs/specs/KNOWLEDGE_OBJECT_MODEL.md` v0.1 Draft. Currently no workbench code emits them. Audit-package builder writes its own format.
- **Scope**:
  - on Step 1 (Import) completion → emit `CaseProfile` with geometry features (volume, surface area, characteristic length, # patches, etc.)
  - on Step 4 (Solve) start → emit `SimulationObject` (physics flags, solver, turbulence model, BC catalog)
  - on Step 4 (Solve) completion → emit `ExecutionArtifacts` (all log files + 0/, constant/, and timestep dirs as a content-addressable bundle)
  - on TrustGate verdict → emit `Provenance` linking case → simulation → artifacts → verdict
  - integrate with audit-package builder: audit-package becomes a P4-compliant KO bundle, not a parallel format
- **Dependencies**: P4 KNOWLEDGE_OBJECT_MODEL promote from Draft v0.1 → Active v1.0 (currently blocked on SPEC_PROMOTION_GATE §2). M15 implementation will likely force the promote conversation.
- **Success criteria**: complete a case end-to-end → 4 KOs (CaseProfile + SimulationObject + ExecutionArtifacts + Provenance) emit to `knowledge/cases/<case_id>/` with valid JSON against schemas.
- **Self-pass-rate estimate**: 40% (cross-track: workbench writes Knowledge plane objects · 4 schemas × validation × audit-package merge = high coordination cost). Will trigger Kogami strategic review (line-A workbench writing Knowledge plane = arguably a line-A extension beyond M-VIZ's claim per V61-094 P2 #1 bounding clause).

#### M16 · Failure pattern aggregation
- **Problem**: when a run fails (FOAM Fatal / divergence / non-convergence / TrustGate FAIL), the engineer fixes it and moves on. The fix is not captured for future cases.
- **Scope**:
  - on every run failure → automatically build a FailurePattern KO with:
    - geometry signature (Re, characteristic length, geometry type tag from M9)
    - mesh signature (cell count, max skewness, max y+, BL layers)
    - solver signature (solver name, turb model, BC catalog)
    - failure signature (FOAM Fatal message OR divergence iter + residual snapshot OR non-conv with final residuals)
  - clustering: when N similar failures land (same geometry+mesh+solver signature, same failure signature), promote the cluster to a "known failure mode" with confidence
  - presentation: when a NEW case matches a known failure-mode signature with high confidence, warn the engineer at Step 4 BEFORE solve runs (e.g., "this configuration matches 12 prior cases that diverged at iter ~200; consider lowering URF or refining BL")
- **Dependencies**: M15 KO integration (FailurePattern KO is one of the 8).
- **Success criteria**: trigger 5 distinct failure modes manually (FOAM Fatal: missing controlDict + divergence with bad URF + non-conv low Re + wall y+ misalignment with k-ε + Co > 1 in transient). All 5 land as FailurePattern KOs. Trigger one of them again on a different case → warning fires at Step 4.
- **Self-pass-rate estimate**: 45% (clustering heuristics + signature matching are easy to over-fit / under-fit).

#### M17 · Correction pattern playback
- **Problem**: when a run fails AND the engineer fixes it, the (problem → fix) pair contains gold but isn't captured.
- **Scope**:
  - when a FailurePattern matches a current setup, AFTER engineer applies a fix and re-runs successfully → emit a `CorrectionPattern` KO linking (failure_signature, fix_diff, success_proof)
  - "fix_diff" is a structured diff between failed setup and successful setup (URF before/after, mesh before/after, BC before/after)
  - on next failure with similar signature → suggest the prior fix as a one-click "Apply prior correction" button in the Step 4 task panel
  - engineer can accept (auto-apply diff), reject (mark "this fix won't work for this case · here's why" → trains the suppression), or edit (apply but tweak)
- **Dependencies**: M16 Failure aggregation.
- **Success criteria**: re-trigger one of the 5 failure modes from M16 → "Apply prior correction" button appears with the previously-successful diff → engineer accepts → run succeeds.
- **Self-pass-rate estimate**: 40% (UX-heavy + diff structure design + acceptance/rejection feedback loop).

#### M18 · Cross-case search & similarity recommender
- **Problem**: even without explicit failure/correction patterns, just **searchability** of prior cases is a force multiplier. Engineer should be able to ask: "show me prior cases with similar geometry / similar physics / similar mesh quality" and inherit setup.
- **Scope**:
  - feature extractor over CaseProfile + SimulationObject (geometry: volume, sphericity, characteristic length, patch count, Re; physics: solver, turb model, BC types; mesh: cell count, BL layers)
  - vector embedding (simple Euclidean over normalized features for v1; surrogate-backed nearest-neighbor for v2)
  - search UI: "find similar cases" panel in Step 1; results show top-5 with similarity %, geometry thumbnails, verdict status
  - "inherit setup from prior case X" button → copies CaseProfile + SimulationObject minus the parts that depend on geometry-specific face_ids
  - face_id remapping: prior case's `inlet` patch → match to current geometry's most-similar patch by feature (axis-alignment, area, centroid distance from origin)
- **Dependencies**: M15 KO integration (need accumulated KOs to search over).
- **Success criteria**: complete 10 cases → for an 11th case, "find similar" returns top-3 with sensible matches → "inherit setup from case #7" copies BC + solver + turb model + mesh strategy → engineer just runs.
- **Self-pass-rate estimate**: 35% (the LARGEST cross-stack feature: feature extractor + similarity metric + UI + face_id remapping each have 2+ failure modes).

**End of Era 2 milestone**: SELF-EVOLUTION ACHIEVED. Every completed case enriches the next case. The 11th case is observably easier than the 1st. Project compounds.

### Era 3 · ENGINEER EFFICIENCY — Compounding the human side (M19-M22)

Goal: take the same engineer-AI loop and make EACH ITERATION faster. Era 2 accumulates knowledge across cases; Era 3 reduces per-case friction.

#### M19 · Recipe library (engineer-owned templates)
- **Problem**: engineer has personal best practices ("my external aero recipe": k-ω SST + 1e-6 inlet TI + zero-grad outlet + 30 BL layers + Sponge-zone refinement). Today these live in tribal knowledge.
- **Scope**:
  - "Save current setup as recipe" button at Step 4 (post-successful-solve)
  - recipe = SimulationObject template + mesh strategy + custom expressions
  - recipe browser: engineer's recipes list + "Apply recipe to this case" button at Step 1
  - recipe versioning: when engineer edits a recipe, prior versions retained (linked via Provenance)
- **Dependencies**: M15 KO integration.
- **Success criteria**: engineer saves "external aero v1" recipe; applies it to a new STL; mesh + BC + solver auto-populate; just run.
- **Self-pass-rate estimate**: 65% (mostly UI + KO field plumbing).

#### M20 · Comparison + diff view (case A vs case B)
- **Problem**: engineer running parameter studies (or comparing a fix to baseline) needs side-by-side: BC diff, mesh diff, residuals overlay, results overlay.
- **Scope**:
  - side-by-side viewport: case A | case B with synchronized camera
  - field overlay: same field on both cases, rendered in matched color scale
  - residual chart overlay: A and B in same chart, colored differently
  - probe comparison: at the same (x,y,z), A vs B values + delta
  - structured diff: SimulationObject A vs B → list of differing fields (turb model, URF, etc.)
- **Dependencies**: M13 Post-processing v1 (slices/probes/field overlay).
- **Success criteria**: run baseline + 1 perturbed; "Compare to baseline" button → diff view shows where they differ.
- **Self-pass-rate estimate**: 55% (synchronized 3D camera + matched color scale + overlay charts have multi-axis state).

#### M21 · Re-run on geometry change
- **Problem**: engineer modifies the STL (small CAD change in upstream tool); wants to re-run with same setup. Today: re-import → re-mesh → re-do face-pick from scratch.
- **Scope**:
  - geometry diff: detect what topologically changed between old STL and new STL (by face_id matching · which faces survived, which are new, which disappeared)
  - inherit setup with delta: surviving faces keep their annotations; new/disappeared faces flagged for engineer review
  - "re-run with new geometry" button → mesh + setup + solve in one shot, with delta-review checkpoint before solve
- **Dependencies**: M9 Tier-B AI (re-classify new faces), M-AI-COPILOT face_id stable hash (V61-098 already specifies this).
- **Success criteria**: take an LDC variant where the lid is offset by 1mm; re-run with prior setup; only the lid annotation needs confirmation; everything else flows through.
- **Self-pass-rate estimate**: 50% (geometry diff topology is hard; face_id hash is the key but corner cases on regen abound).

#### M22 · Engineer journal + LLM dialog upgrade
- **Problem**: currently the workbench dialog is structured (UnresolvedQuestion checklist from M-AI-COPILOT). For complex flows the engineer wants free-form: "this is a heated kitchen extractor, I want steady-state at 80°C inlet, k-ω SST, target y+ 30."
- **Scope**:
  - LLM dialog (per Pivot Charter §1 P3+ promise) — engineer types intent in natural language → LLM proposes SimulationObject template → engineer confirms/edits via Step 3 dialog (which is still structured)
  - engineer journal: every case auto-summarizes what was done (CaseProfile changes + SimulationObject changes + Verdict + retrospective notes engineer typed)
  - journal feeds back to LLM: when a similar case comes in, LLM has prior journals as context
- **Dependencies**: M-AI-COPILOT structured dialog (kept as fallback / verifier), P4 Knowledge accumulated (~50 cases for LLM context).
- **Success criteria**: engineer types intent in NL; system proposes setup; engineer confirms; case runs; journal auto-populates; subsequent similar case has LLM-suggested setup that references the prior journal.
- **Self-pass-rate estimate**: 30% (LLM integration with structured fallback + journal automation is the most novel surface in this entire roadmap).

**End of Era 3 milestone**: the engineer's productivity is compounded by both system memory (Era 2) and per-case efficiency (Era 3). A typical case takes 1/4 the time of a fresh start.

---

## §5 · Critical path

```
        Era 1 LOOP SPINE                      Era 2 ARCHIVE+LEARN              Era 3 ENGINEER EFFICIENCY
   ┌──────────────────────┐              ┌──────────────────────────┐         ┌──────────────────────────┐
   │  M9  Tier-B AI       │──┐           │  M15 KO integration      │         │  M19 Recipe library      │
   │  M10 STEP/IGES       │  ├──────────►│  M16 FailurePattern      │────────►│  M20 Comparison view     │
   │  M11 Mesh Wizard     │  │           │  M17 CorrectionPattern   │         │  M21 Re-run on geom Δ    │
   │  M12 Multi-physics   │  │           │  M18 Similarity recommend│         │  M22 LLM dialog + journal│
   │  M13 Post-process v1 │  │           └──────────────────────────┘         └──────────────────────────┘
   │  M14 Auto V&V        │──┘                          ▲
   └──────────────────────┘                             │
              │                                         │
              ▼                                         │
    PROJECT INFLECTION POINT          ◄─────────────────┘
    (Era 1 closes the loop for         Era 2 makes the loop SELF-EVOLVE
     ONE case at a time)               Era 3 makes EACH ITERATION fast
```

**Era 1 (M9-M14)** is non-negotiable: without it the project's core promise ("any simple 3D geom end-to-end") is unmet. **Era 2 (M15-M18)** is the strategic differentiator: without it the workbench is just a cleaner ANSYS Workbench. **Era 3 (M19-M22)** is value-maximizing: without it the engineer still benefits from Era 2 just slower per case.

**If forced to compress for time**: Era 1 + M15+M16+M18 (skip M17 CorrectionPattern, skip Era 3) is the minimum viable self-evolving system. ~10 milestones, ~6 months at the V61-097 pace.

---

## §6 · Tied to existing strategic spine (P1-P6)

This roadmap is the workbench-driven implementation arc for several P-series milestones already in the spine:

| Strategic spine milestone | This roadmap's contribution |
|---|---|
| **P1 Metrics & Trust Gate** (Done · Active) | M14 Auto V&V exposes TrustGate per-run in Step 5; M16 FailurePattern uses TrustGate FAIL as a trigger |
| **P2 Executor Abstraction** (HOLD · paused for Pivot Addendum 3) | M12 Multi-solver routing requires ExecutorMode; P2 unpause is the prerequisite for M12 |
| **P3 Dataset/Task/Sim Protocol** (Planned) | M15 KO integration provides the workbench → P3 protocol bridge; M22 LLM dialog leverages P3 protocols |
| **P4 Knowledge Object Model** (Planned · spec Draft v0.1) | M15 forces P4 promote from Draft → Active v1.0; M16-M18 + M19 use 4 of the 8 KO types |
| **P5 Surrogate Backend Plugin** (Planned远期) | M18 v2 similarity recommender can use surrogate-backed embeddings; M21 re-run on geom Δ can use surrogate for fast re-mesh quality |
| **P6 Differentiable Lab** (Planned远期) | NOT touched by this roadmap; D-lab remains research-track per Pivot Charter |

**Crucial alignment note**: P2 Executor Abstraction is currently HOLD pending Pivot Addendum 3 closure. M12 Multi-solver routing needs P2. So either (a) M12 forces P2 unpause AT M12 START, or (b) M12 ships a workbench-local mini-router and P2 abstraction lands later as a refactor. Path (a) is cleaner; path (b) is faster. **Decision needed at M12 kickoff.**

---

## §7 · §11.1 BREAK_FREEZE quota & line-A scope

**§11.1 BREAK_FREEZE quota**: 3/3 EXHAUSTED at M-AI-COPILOT (DEC-V61-098). All Era 1+2+3 milestones operate under normal feature-freeze rules — no per-PR escape clause.

**Line-A path additions** that THIS ROADMAP would require (each needs its own ROADMAP §"Line-A / Line-B isolation contract" extension at the kickoff DEC):
- `ui/backend/services/case_setup/` (already added by M-AI-COPILOT, ✓)
- `ui/backend/services/mesh_wizard/` (M11 NEW)
- `ui/backend/services/solver_router/` (M12 NEW)
- `ui/backend/services/post_processing/` (M13 NEW)
- `ui/backend/services/trust_gate/` (M14 NEW · or reuse `src/trust_gate/`)
- `ui/backend/services/knowledge_objects/` (M15 NEW · cross-track contract)
- `ui/frontend/src/visualization/PostProcessing/` (M13 NEW)
- `ui/frontend/src/pages/workbench/comparison/` (M20 NEW)

Each kickoff DEC will list the line-A extensions explicitly per V61-094/095/096/098 precedent.

---

## §8 · Governance posture (per RETRO-V61-001 + V61-087)

| Milestone | Codex pre-merge | Kogami strategic review | self-pass-rate est | risk class |
|---|:-:|:-:|:-:|---|
| M9 Tier-B AI | ✅ | ❌ (V61-094 P2#1 bounding) | 60% | rule-based heuristic; mostly add-on |
| M10 STEP/IGES | ✅ | ❌ | 65% | gmsh OCC integration |
| M11 Mesh Wizard | ✅ | ❌ | 50% | multi-axis interaction |
| M12 Multi-physics | ✅ | ⚠️ TBD | 45% | LARGEST surface · likely Kogami trigger |
| M13 Post-processing | ✅ | ❌ | 60% | UI-heavy |
| M14 Auto V&V | ✅ | ❌ | 55% | integrates P1 |
| **M15 KO integration** | ✅ | ✅ **HARD YES** | 40% | cross-track (workbench writes Knowledge plane) · charter-level integration |
| M16 FailurePattern | ✅ | ⚠️ TBD | 45% | KO writer · downstream of M15 |
| M17 CorrectionPattern | ✅ | ❌ | 40% | downstream of M16 |
| M18 Similarity recommend | ✅ | ❌ | 35% | algorithmic + UI · borderline LARGEST |
| M19 Recipe library | ✅ | ❌ | 65% | mostly UI |
| M20 Comparison view | ✅ | ❌ | 55% | viewport state-machine |
| M21 Re-run on geom Δ | ✅ | ❌ | 50% | depends on face_id stability |
| M22 LLM dialog | ✅ | ✅ **HARD YES** | 30% | charter §1 P3+ promise · LLM integration is line-A risk-tier change |

**Counter projection**: 14 milestones × `autonomous_governance: true` = +14 to counter. From V61-098 (counter 63) → counter 77 at M22 close. RETRO at counter 80 (per RETRO-V61-001 cadence ≥20 from RETRO-V61-005's 50 baseline).

---

## §9 · Honest pacing assessment

V61-097 (M-PANELS Phase-1A) took **5 days end-to-end** including 4 Codex rounds for an arc of comparable complexity to most of these milestones. Realistic per-milestone time: **2-4 weeks** including Codex pre-merge rounds.

**14 milestones × 3 weeks/avg = ~10 months sustained pace.** Plus:
- M-AI-COPILOT (in flight) closes ~2026-05-12
- M7-redefined + M8-redefined: ~3 weeks combined
- → Era 1 starts ~2026-06-02 → ends ~2026-09-30 (4 months for M9-M14)
- → Era 2 starts ~2026-10-01 → ends ~2027-01-31 (4 months for M15-M18)
- → Era 3 starts ~2027-02-01 → ends ~2027-05-31 (4 months for M19-M22)

**Total horizon: 13 months from 2026-04-29.** This is realistic if no other major arcs fire (RETRO arc-size milestones, governance incidents, Tier-2 OS sandbox upgrades).

If pace slips by 50% (more typical for novel surface area): 18-20 months. If we pre-empt by skipping Era 3: 9-10 months.

**Recommendation**: don't pre-commit to dates. Charter Addendum 3 §6 explicitly says "估期可调整". Each kickoff DEC sets its own self-pass-rate + risk class; pace emerges from the work.

---

## §10 · Open questions (must resolve before each era)

### Before Era 1
1. **Tier-B AI fixture set**: 5 canonical "simple 3D" geometries that M9 must classify well. Pipe (straight) + pipe (elbow) + flange + manifold + bluff body? Or different mix?
2. **STEP/IGES backend**: gmsh OCC vs FreeCAD CLI vs python-occ? gmsh is in stack, others would add deps.
3. **Mesh Wizard cell-count cap**: 5M (per CFDJerry's M7 ask) or 10M (more headroom but risks runaway runs)?

### Before Era 2 (CRITICAL)
1. **P4 KNOWLEDGE_OBJECT_MODEL promote**: M15 forces this. Promote from Draft v0.1 → Active v1.0 needs SPEC_PROMOTION_GATE clearance. Is the existing 8-object schema sufficient for workbench needs? Probably yes for KO #1 + #3 + #4 + #5; #6 + #7 may need refinement.
2. **Where do KOs live on disk**: `knowledge/cases/<case_id>/` (parallel to `knowledge/case_profiles/`) or inside `<case_dir>/.knowledge/`? First option is global view; second is case-portable.
3. **Cross-track contract review**: workbench writing Knowledge plane MAY breach line-A purity per ADR-001 four-plane import direction. M15 needs Kogami strategic review to confirm acceptable boundary.

### Before Era 3
1. **LLM provider for M22**: GLM-5.1 (already in stack via /glm-execute) or Claude API direct or Codex GPT-5.4 (existing review channel)?
2. **Recipe library scope**: per-engineer (single-user → single recipe set) or per-physics-domain (external aero / internal flow / heat transfer)? Latter is more useful but requires categorization.
3. **Engineer journal format**: structured (template-driven) or free-form (LLM-summarized)? Hybrid?

### Strategic decision points
1. **Era 2 vs Era 3 priority**: if Era 2 lands and consumes 4 months as expected, is it more valuable to push Era 3 to deepen engineer efficiency OR pivot to Era 4 (parametric/optimization · currently OUT-of-scope)? Decide at end of Era 2 based on engineer dogfood signal.
2. **P2 unpause**: M12 needs P2. Force P2 unpause at M12 kickoff (clean) or ship workbench-local mini-router and refactor later (faster)? **Decision at M12 kickoff.**
3. **Dogfood gate**: Path A first-customer recruitment is currently gated at M-PANELS Tier-A merge (Gate-3). Should Gate-4 (M-AI-COPILOT) also be a recruitment milestone, OR should Path A wait until Era 1 is done (genuinely arbitrary STL works)? Recommendation: Gate-4 yes, Gate-5 at end of Era 1.

---

## §11 · What this roadmap is NOT

Per the strategic discipline of saying NO:

- It is **not** a charter modification. Pivot Charter §1 + Addendums 1-3 are unchanged. This roadmap is the implementation plan for §3 ("Case Intelligence Layer") on the workbench-driven path.
- It is **not** a SaaS product plan. Single-user only.
- It is **not** a competitive product plan ("we will replace ANSYS Workbench"). It is a self-evolving tool for ONE engineer.
- It is **not** a research project plan. Differentiable Lab (P6) and adjoint optimization remain research-track.
- It is **not** a customer-development roadmap. Path A first-customer recruitment is orthogonal; this roadmap is about product capability.
- It is **not** binding. Each milestone needs its own kickoff DEC with CFDJerry ratification at startup.

---

## §12 · Linked artifacts

- **Pivot Charter** (binding): `docs/governance/PIVOT_CHARTER_2026-04-22.md`
- **Pivot Charter Addendum 3** (binding · ordering through M8): `docs/governance/PIVOT_CHARTER_ADDENDUM_3_2026-04-28.md`
- **P4 KNOWLEDGE_OBJECT_MODEL** (Draft v0.1): `docs/specs/KNOWLEDGE_OBJECT_MODEL.md`
- **M-AI-COPILOT (collab-first) kickoff** (Active): DEC-V61-098 + spec_v2 (foundation for M9 Tier-B AI)
- **Workbench Beginner-Full-Stack Roadmap (M5-M8 60-day window)**: Notion sub-page (precursor to this doc, covers Charter Addendum 3 §4.a milestones)
- **CFD-Harness-OS strategic spine**: P1 Metrics_and_TrustGate (Active) + P2 Executor (HOLD) + P3 Protocol (Planned) + P4 KO (Planned) + P5 Surrogate (远期) + P6 D-Lab (远期)

---

## §13 · Closing assessment

**The strategic claim of this roadmap**: the cfd-harness-unified workbench can become a self-evolving CFD automation tool that compounds in value with each completed case. The closed loop runs end-to-end at end of Era 1 (M14, ~4 months). Self-evolution kicks in at end of Era 2 (M18, ~8 months). Per-case efficiency optimizes at end of Era 3 (M22, ~12 months).

**The biggest risk**: M15 KO integration is the cross-track integration that wires the workbench into the Knowledge plane. If P4 KNOWLEDGE_OBJECT_MODEL promote stalls or its 8-object schema proves insufficient, Era 2 cannot start. **Mitigation**: at M14 close (end of Era 1), spawn a parallel P4 promote workstream so it lands BEFORE M15 starts.

**The biggest opportunity**: every successful run through this loop is a permanent capability gain. Unlike a SaaS product where churn resets the value, a self-evolving single-user tool that runs daily for 6 months has accumulated 6 months of failure patterns + correction patterns + recipes — the value is in the engineer's accumulated state, not in the codebase.

**The biggest unknown**: whether the P3 Sim Protocol + P4 Knowledge Object Model schemas, designed in 2026 Q1 for the broader CFD Harness OS, are the right fit for what the workbench actually emits in real engineer use. We will only know after 50-100 cases through the loop. **Plan for refactor at the M22 → Era 4 boundary if needed.**

---

**Awaiting CFDJerry ratification.** Upon ratification, M9 kickoff DEC will be drafted as the first operative milestone in this roadmap (sequenced after M-AI-COPILOT closes ~2026-05-12).
