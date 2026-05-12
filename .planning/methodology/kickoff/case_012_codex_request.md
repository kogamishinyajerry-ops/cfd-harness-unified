# Codex Case-Design Request · case_012

> **Status**: PENDING — Codex round 1 not yet sent.
> **Phase**: Industrial Extension Phase 1 #2 per
> `.planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md`.
> **Strategic role**: Maximum APU 002a buoyant inheritance —
> direct `buoyantSimpleFoam` reuse on a completely different
> industrial part (HVAC supply diffuser). Demonstrates Pattern 6
> on the buoyant-RANS root.
> **Backend**: 86gs gpt-5.5 xhigh primary; CRS gpt-5.4 high fallback.
> **Blocker**: none (case_011 sediment NOT required; 002a
> inheritance is independent of 011 multi-stream learnings).
> **Dispatch readiness**: ready as soon as user confirms.

## Target

| field | value |
|---|---|
| case_id | `case_012_<short_name>` (Codex picks short_name; suggested: `hvac_supply_diffuser`) |
| solver_class_target | Industrial confined buoyant ventilation: buoyantSimpleFoam steady, single fluid (air), single solid envelope (room walls + diffuser plenum) |
| numerics_class | compressible-buoyant-RANS (already covered by 002a; this is the **industrial-deployment form**, not a NEW root) |
| coverage map row to fill | "HVAC supply diffuser thermal stratification" — currently uncovered (002a is APU bay, not HVAC delivery) |
| CAD source priority | Tier 3 (parametric CadQuery) — HVAC diffusers are commodity geometry, parametric is the right path. Tier 2 acceptable IF a permissively-licensed standard ASHRAE/IEA Annex 20 model exists |
| defect injection count | 2 |
| defect injection hint | D1 (slot gap between diffuser plate and ceiling — 0.3-0.5 mm, real installation tolerance defect; **9th D1 injection** but applied to NEW industrial topology) + **D7 (wrong-normal louver face)** — D7 is UNCOVERED in 003-011 roster (per harvest-002 catalog rebalance) |
| sandbox path suggestion | `~/Desktop/case_012_hvac_supply_diffuser/` |

## Why HVAC supply diffuser as case_012 (Phase 1 #2 strategic role)

After case_011 (multi-stream CHT, NEW root), case_012 returns to
**already-covered** numerics root (compressible-buoyant-RANS) but
applies it to a **different industrial topology**. Strategic value:

1. **Direct 002a buoyant inheritance** — `buoyantSimpleFoam` machinery
   already validated; no NEW solver infrastructure needed. Pattern 6
   inheritance carries V3-V13 + S1-S13 directly forward. Effort drops
   to 8-10h (vs case_011's 10-12h).
2. **Industrial deployment ubiquity** — every commercial building,
   aircraft cabin, data center cold aisle, clean room uses HVAC
   diffusers. Service market value is high-volume but lower per-job
   than turbomachinery. Demonstrates the harness can do
   "HVAC consulting" workload.
3. **Defect catalog rebalance** — D7 (wrong-normal louver) is 0/11
   injected so far. case_012 is the first chance to exercise the
   advisor path for face-orientation defects. D1 9th injection
   confirms the sub-mm-gap arc remains stable across topologies
   (confined-buoyant-room is genuinely different from APU bay).
4. **NEW engineering metrics** — ADPI, throw distance, dumping
   criterion, occupied-zone uniformity — 3-4 new post-processors
   that extend the industrial-metrics catalog beyond CFD-internal
   residuals.
5. **No A2-v2 dependency** — D1 is sub-mm gap (A2 v1 still
   `[QUESTIONABLE]` per V25, but slot-gap pattern at 0.3-0.5 mm is
   100× larger than case_011's 30 μm plate offset; A2 `_run_shared`
   PASS evidence accumulates without depending on A2-v2 for D1
   gap-distance field-validation. Marker still applied per harvest 002
   convention).

## Hard constraints (Codex must honor)

1. **Solver class**: `buoyantSimpleFoam` steady. v1 target:
   single-fluid air with realistic Boussinesq buoyancy
   (`g = (0, 0, -9.81)`) + ASHRAE-style supply jet from
   ceiling-mounted diffuser into a representative occupied-zone
   room. v2 fallback: `buoyantPimpleFoam` if steady residuals
   oscillate (V13 pattern; same fallback as 002a).
2. **CAD source**: Tier 3 parametric. HVAC diffusers are commodity
   geometry; parametric generation is correct.
3. **Geometry must be physically realistic** — not a toy. Required
   features:
   - **Room envelope**: 5-8 m × 4-6 m × 3 m (occupied office /
     conference room). Walls = solid boundaries; floor and one
     "wall" optionally are heat-source surfaces (occupants /
     equipment).
   - **Ceiling-mounted supply diffuser**: 4-way throw or linear-
     slot pattern (Codex picks). Must have realistic louver/vane
     geometry — not a square hole. Slot width 5-15 mm typical.
   - **Return air grille**: low-side-wall or ceiling-corner return.
   - **Heat sources** (steady): occupant simulators (75 W each ×
     N people, distributed on floor) OR equipment heat (e.g., 200
     W server rack patch on one wall) OR solar gain (window patch
     on one wall). At least one heat source MUST be present to
     drive thermal stratification.
   - Supply jet inlet: T_supply ≈ 14-18 °C, U_supply ≈ 1.5-3.5 m/s
     (typical ASHRAE / IEA Annex 20 supply-air conditions).
4. **Defect injection**: exactly 2 defects from catalog. Required
   set:
   - **D1**: 0.3-0.5 mm slot gap between diffuser face plate and
     ceiling structure (real installation tolerance defect).
   - **D7**: wrong-normal louver face (inward-pointing surface
     normal on one of the diffuser louver vanes; 30-45° rotation
     from intended orientation). This is UNCOVERED in 003-011
     roster.
5. **Patch naming**: all body names `^[A-Za-z][A-Za-z0-9_]*$`.
6. **Region structure**: single fluid region (`region_air`) + walls
   as patches (not separate solid region — this is buoyant single-
   region, NOT chtMultiRegion). Heat-source surfaces are wall
   patches with `fixedValue T` or `fixedHeatFlux`. Sub-session
   v1: do NOT include CHT to room walls (this is single-region
   buoyant); v2 may extend to walls-as-CHT if user requests.
7. **Determinism**: CadQuery script byte-identical regeneration.
8. **Industrial flavor**: must be recognizable as a real HVAC
   diffuser installation (e.g., commercial office, data center
   cold aisle, aircraft cabin). NOT a research-paper toy
   (rectangular box with idealized inlet).
9. **Reference data**: pick an operating point with documented
   ASHRAE / IEA Annex 20 isothermal-jet or non-isothermal-jet
   reference. Document predicted ADPI (target ≥ 80% per ASHRAE
   55), expected throw distance, and dumping criterion threshold.
   CFD ADPI should be comparable to design-table prediction within
   ±10 percentage points if geometry honest.

## Codex prompt (paste-ready)

```
You are Codex, acting as case 出题者 (case designer) for the
cfd-harness-unified project. The project main session is asking
you to design ONE industrial CFD case end-to-end so a Claude Code
sub-session can execute it.

This is your design task, not your solver task. You design; the
sub-session runs.

## Project context (read first)

cfd-harness-unified is a CFD harness over OpenFOAM at
/Users/Zhuanz/Desktop/cfd-harness-unified/. Per DEC-V61-198
(2026-05-07 strategic charter), the project's development
philosophy is "container that accumulates industrial CFD
experience" — each industrial case extends a solver-class
coverage axis and feeds the V-series finding index.

11 prior cases (original 10-case roster + Phase 1 #1):
- case_002a (APU bay buoyantSimpleFoam): active · v14
- case_002b (APU bay CHT chtMultiRegionFoam): active · v2
- case_003 through case_010: dispatched (5 of 8 with v1 sediment)
- case_011 (plate-fin compact HX, multi-stream CHT): dispatched
  2026-05-08 evening (Phase 1 #1 of new industrial-extension batch)

You designed case_004 through case_011. **case_012 is Phase 1 #2**
per the strategic roadmap at
`.planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md`.
The new batch pivots from research-benchmark cases toward
industrial-service-market cases. Your case_012 design role:
maximize APU 002a buoyantSimpleFoam inheritance to demonstrate
Pattern 6 working on a completely different industrial topology
(HVAC delivery vs APU bay confinement).

## Required reading (in cfd-harness-unified repo)

Read these in order before designing:
1. .planning/methodology/codex_case_design_protocol.md — your
   contract (5 deliverables + validation steps)
2. .planning/methodology/component_bank.md — Tier-3 fallback
   menu; B-class includes HVAC diffusers
3. .planning/methodology/public_cad_sources.md — Tier-1 likely
   none for parametric HVAC; Tier-3 is the path
4. .planning/methodology/kickoff/case_004_codex_response.md AND
   case_005_codex_response.md AND case_011_codex_response.md —
   examples of your prior multi-deliverable case design output
5. .planning/case_profiles/case_002a_apu_bay_buoyant.md — the
   buoyantSimpleFoam pattern your design inherits
6. .planning/methodology/industrial_case_solver_findings.md —
   V-series; case_012's compressible-buoyant-RANS class inherits
   V3-V13 + S1-S13 directly (already-covered numerics root)
7. .planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md
   — strategic SSOT; case_012 is Phase 1 #2
8. .planning/methodology/knowledge_status_convention.md —
   2026-05-08 harvest 002 convention; apply [QUESTIONABLE] /
   [VALIDATED] markers in your defect manifest where appropriate
9. ASHRAE Standard 55 / IEA Annex 20 reference background
   (your training data should suffice; cite design-table values)

## Hard constraints

1. **Solver class**: buoyantSimpleFoam steady. v1: single fluid
   region (air) with Boussinesq buoyancy + supply jet from
   ceiling diffuser + at least one steady heat source. v2:
   buoyantPimpleFoam if oscillation.
2. **CAD source priority**: Tier 3 parametric. HVAC diffusers are
   commodity geometry. Document tier choice + justification.
3. **Geometry physical realism**:
   - Realistic occupied-zone room: 5-8 m × 4-6 m × 3 m
   - Ceiling-mounted supply diffuser with REAL louver/vane
     geometry (4-way throw or linear-slot, Codex picks). Slot
     width 5-15 mm.
   - Return air grille (low side wall or ceiling corner)
   - At least 1 heat source: occupant simulators (75 W) /
     equipment patch (200 W) / solar gain patch
   - Supply: T_supply ≈ 14-18 °C, U_supply ≈ 1.5-3.5 m/s
4. **Defect injection (REQUIRED 2 defects)**:
   - **D1**: 0.3-0.5 mm slot gap between diffuser face plate and
     ceiling. **9th D1 injection** in project history.
   - **D7**: wrong-normal louver face (30-45° rotation from
     intended). UNCOVERED in 003-011 roster — first chance to
     exercise advisor path for face-orientation defects.
5. **Patch naming**: ^[A-Za-z][A-Za-z0-9_]*$, OpenFOAM rule.
6. **Single fluid region** (buoyantSimpleFoam): no CHT to walls
   in v1. Walls are patches with T or heat-flux BC, not a
   separate solid region.
7. **Industrial flavor**: must be recognizable as commercial
   office HVAC / aircraft cabin supply / data center cold aisle.
8. **Reference data validity**: pick an operating point where
   ASHRAE / IEA Annex 20 ADPI prediction is applicable.
   Document predicted ADPI, throw distance, dumping criterion.
   CFD ADPI within ±10 percentage points expected.
9. **NO Ahmed body, NO NACA, NO Sajben** (Lane B exclusions; not
   relevant here anyway).
10. **NO new defect categories** outside D1-D10.

## Your 5 deliverables

Same format as case_011 response. Per
codex_case_design_protocol.md §"What Codex returns":

### 1. Engineering brief (Markdown)

Sections (mandatory):
- Component picked + bank ID + reasoning (B-class HVAC diffuser
  bank entry; reference ASHRAE design table)
- Engineering question (1-2 sentences: what does the engineer
  want to know? — typical: "does this diffuser meet ADPI ≥ 80%
  in the design occupied zone with the as-installed defect
  set?")
- Physics signature: buoyantSimpleFoam, expected Re_supply
  (typical 5e3-5e4 for jet from slot), Pr ≈ 0.71, Boussinesq
  buoyancy, Ra ≈ 1e9-1e10 for room scale
- Parts inventory: room walls (each as named patch), diffuser
  face plate, louver vanes (each one or grouped), supply inlet,
  return outlet, heat-source patches
- Boundary conditions plan: ALL patches with explicit BC type
  (supply: flowRateInletVelocity / fixedValue T; return:
  pressureOutlet; walls: zeroGradient or fixedValue T or
  fixedHeatFlux; floor with occupants: fixedHeatFlux 75 W per
  occupant ÷ patch area)
- Expected metrics: ADPI per ASHRAE 55 (target ≥ 80% in occupied
  zone), throw distance L_throw to T_50 isovalue, dumping
  criterion (vertical T gradient near floor < 2 K/m), occupied-
  zone U_max (< 0.25 m/s for comfort), thermal stratification
  ΔT_ceiling-floor
- Hypothesized failure modes (V-findings prediction, including
  HVAC-specific ones):
  - V3-V13 inheritance from 002a (already covered findings)
  - NEW: ceiling-attached jet detachment (Coanda effect breaking
    down)
  - NEW: cold-jet dumping (low-U supply falls into occupied zone)
  - NEW: wrong-normal louver D7 producing unexpected jet
    deflection
  - NEW: ADPI sensitivity to slot-gap D1 leakage
  - NEW: occupied-zone thermal stratification residual
    convergence (steady-state ambiguous)
- Defect injection summary (D1 + D7 with measurable verification
  commands)
- Sub-session estimated effort (target: 8-10h — should be
  TIGHTER than case_011 because solver infrastructure is
  already 002a)

### 2. CAD generation script (Python, executable)

CadQuery preferred. Same requirements as case_011:
- Deterministic
- --out CLI with default
- Parametric constants at top (room_length, room_width,
  room_height, diffuser_slot_width, diffuser_throw_pattern,
  louver_count, louver_angle, return_grille_size, occupant_count,
  occupant_heat_W, supply_T, supply_U, ...)
- Comments at decision points
- Single fluid region (room interior volume) + named patches:
  - region_air (single fused solid representing room interior)
  - patches: ceiling, floor, wall_north/south/east/west, supply_inlet,
    return_outlet, diffuser_face_plate, louver_vane_<i>,
    occupant_<i> (heat source), other_heat_sources_as_named
- Defect injection: D1 introduces 0.3-0.5 mm gap on
  diffuser_face_plate periphery; D7 rotates one louver_vane_<i>
  by 30-45° around its own axis
- STEP export with named patches preserved (same V16/V24 lessons:
  use cq.Solid.fuse() not cq.Compound.makeCompound())

### 3. STEP file path

Single path string:
/Users/Zhuanz/Desktop/case_012_hvac_supply_diffuser/inputs/cad_codex_v1.step

### 4. Parts manifest YAML

Required fields beyond standard:
- region: region_air (single fluid, no CHT in v1)
- patches: list of patches with bc_type plan (supply/return/
  walls/heat sources/diffuser face/louvers)
- thermophysics: air with Boussinesq buoyancy (β ≈ 1/T0,
  T_ref ≈ 293 K, ρ_ref, Pr, gravity)
- HVAC operating point: T_supply, U_supply, T_return (initial
  guess), heat-source W distribution
- ADPI reference: predicted ADPI from ASHRAE 55 design table
  for the chosen diffuser pattern + room dimensions

### 5. Defect manifest YAML

Two defects per catalog. For D1 slot gap:
expected_advisor_to_catch should reference the planned A2-v2
gap-detection extension (drafted at
`.planning/patches/draft_a2_v2_gap_detection_2026-05-08.md`) —
acknowledge that A2 v1 cannot field-validate gap-distance
(V25 scope-narrow). Apply [QUESTIONABLE] marker per
knowledge_status_convention.md.

For D7 wrong-normal louver: expected_advisor_to_catch =
**no advisor exists yet** for face-orientation defects. This is
the FIRST D7 injection in project; expected outcome is
"advisor gap surfaced; A4 or new advisor candidate flagged for
post-case_012 retro". Sub-session manually verifies via
FreeCAD `Face.normalAt()` + dot-product check.

## Format your response

Wrap in clear section headers (same as prior responses):

## Deliverable 1 — Engineering brief
<markdown>

## Deliverable 2 — CAD generation script
```python
<full script>
```

## Deliverable 3 — STEP file path
<single path string>

## Deliverable 4 — Parts manifest
```yaml
<full yaml>
```

## Deliverable 5 — Defect manifest
```yaml
<full yaml>
```

## Round budget

Round 1 of 3 (cap=3 per V133). Round 2 reserved for revision if
validation fails; round 3 for further revision.

## What you should NOT do

- Do NOT propose a CHT room (walls-as-solid-region) in v1; that's
  single-region buoyantSimpleFoam, not multi-region.
- Do NOT skip defect injection.
- Do NOT pick Lane-B exclusions.
- Do NOT use cq.Compound.makeCompound for "this should be one
  body" — use cq.Solid.fuse() per V16/V24 lessons.
- Do NOT propose new defects outside D1-D10.
- Do NOT use Ahmed/NACA/Sajben.
- Do NOT exceed 10h estimated sub-session effort (Phase 1 #2
  must be tighter than case_011 because solver is already
  002a-validated).
- Do NOT propose D1 as a "novel detection target" — D1 is the
  9th injection; advisor path is already cross-topology
  validated. The point of D1 in case_012 is consistency
  (room-scale topology) + A2 placeholder reaffirmation.

## Begin
```

## Validation checklist (main session runs after Codex responds)

Before writing the per-case kickoff:

- [ ] CAD source picked (Tier 1 / 2 / 3 declared with justification)
- [ ] CadQuery script `python3 -m py_compile` passes
- [ ] Generated STEP would open in FreeCAD without errors
- [ ] FreeCAD reports body count + named patches matching parts
      manifest
- [ ] All patch + region names satisfy ^[A-Za-z][A-Za-z0-9_]*$
- [ ] **Single fluid region** declared (NOT multi-region; this is
      buoyantSimpleFoam not chtMultiRegionFoam)
- [ ] **Realistic louver geometry** present (not just rectangular
      hole)
- [ ] **At least 1 heat source** patch declared with W rating
- [ ] **Supply + return** both declared with realistic conditions
- [ ] **Boussinesq buoyancy** declared in thermophysics
- [ ] **ADPI reference** documented as design-table prediction
- [ ] D1 slot gap: 0.3-0.5 mm, marked with V25 [QUESTIONABLE]
      (A2 v1 cannot field-validate gap distance)
- [ ] D7 wrong-normal louver: 30-45° rotation, advisor=NONE
      (first D7 in project; flag for post-case retro)
- [ ] Both defects in patches OUTSIDE the ADPI comparison zone
      (occupied-zone is the comparison zone; defects on diffuser
      installation periphery)
- [ ] Engineering brief targets buoyantSimpleFoam single-region

## After validation passes

1. Save Codex response at `kickoff/case_012_codex_response.md`
2. Format per-case kickoff at `kickoff/case_012_<short_name>.md`
   (apply harvest 002 convention: A2 LANDED + V25 marker on D1,
   knowledge_status_convention reference, all required reading
   items per case_007-011 pattern; D7 advisor-gap finding flagged
   for post-case retro)
3. Update `case_proposal_queue.md`: case_012 row from "Active
   queue (Proposed Phase 1)" to "Dispatched"
4. Update `case_index.md` with case_012 row, status=dispatched
5. Tell user: "case_012 kickoff ready. Open new Claude Code
   session and paste contents of `kickoff/case_012_<short_name>.md`."

## Risk mitigations

- If Codex returns a CHT room (walls-as-solid-region) instead of
  single-region buoyantSimpleFoam → revision request round 2
  with explicit "v1 single-region; CHT walls is v2 user-driven"
- If Codex picks a research-paper toy (rectangular box without
  louver geometry) → revision request with industrial-realism
  constraints
- If Codex returns D1 + D8 instead of D1 + D7 → revision request
  pointing to harvest-002 catalog rebalance: D7 is uncovered,
  D8 is over-sampled (5-6/11 cases)
- If 86gs gpt-5.5 503s or 429s → fall back to CRS gpt-5.4 high
  per case_011 pattern; document `codex_review_relay: crs (effort=high, fallback)`

## D7 advisor-gap pre-emption note

D7 (wrong-normal face) has **no LANDED advisor**. Expected
outcome of case_012:
- Sub-session manually verifies D7 via FreeCAD
  `Face.normalAt()` + dot-product against expected normal
- Surfaces this as **V-finding: "no advisor exists for D7 face-
  orientation defects; A4 or new advisor candidate"**
- Post-case_012 retro evaluates whether D7 advisor is
  worth landing as a sub-DEC. If 2+ Phase 1-4 cases inject D7
  (012, possibly 016 cavity walls, 020 filter shell), advisor
  becomes high-priority.

This is **expected and intentional** — case_012 is the first
chance to surface the D7 advisor-gap. Do NOT treat this as a
case-design failure.
