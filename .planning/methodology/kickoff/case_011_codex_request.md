# Codex Case-Design Request · case_011

> **Status**: PENDING — Codex round 1 not yet sent.
> **Phase**: Industrial Extension Phase 1 #1 per
> `.planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md`.
> **Strategic role**: Maximum APU CHT (002b) leverage demonstration —
> direct Pattern 6 inheritance from compressible-buoyant-RANS-CHT to
> a completely different industrial part (heat exchanger).
> **Backend**: 86gs gpt-5.5 xhigh primary (governance baseline);
> CRS gpt-5.4 high fallback if 503.

## Target

| field | value |
|---|---|
| case_id | `case_011_<short_name>` (Codex picks short_name; suggested: `plate_fin_compact_hx`) |
| solver_class_target | Multi-stream CHT (industrial heat exchanger): chtMultiRegionFoam steady, 2 fluid regions + 1 solid region |
| numerics_class | incompressible-RANS-CHT-multi-stream (NEW root — partial inheritance from 002b CHT for the multi-region machinery, but multi-stream is genuinely new) |
| coverage map row to fill | "Industrial heat exchanger — multi-stream CHT" — currently uncovered (010 closes original 10-case roster but CHT was only validated on APU) |
| CAD source priority | Tier 3 (parametric CadQuery) — plate-fin HX has no canonical Tier-1 STEP; parametric is the right path. Tier 2 (GrabCAD compact-HX library) acceptable if a clean license-permissive model exists |
| defect injection count | 2 |
| defect injection hint | D8 (thin fin walls — already 6-of-6 validated, this case extends to 7th case for under-utilized topology) + D5 (slightly mis-aligned plate-to-plate interface — UNCOVERED in 003-010 roster) |
| sandbox path suggestion | `~/Desktop/case_011_plate_fin_compact_hx/` |

## Why heat exchanger as case_011 (Phase 1 strategic role)

After completing 10-case roster (002a/b + 003-010), strategic
analysis (`case_011_020_industrial_extension_roadmap_2026-05-08.md`)
identified **heat exchangers as #2 industrial CFD demand category**
not yet covered. Plate-fin compact HX is the highest-leverage
choice because:

1. **Direct 002b CHT inheritance** — `chtMultiRegionFoam` machinery
   already validated; multi-stream is a small extension (2 fluid
   regions instead of 1, plus solid). Pattern 6 inheritance carries
   V14 (CHT post-processor sentinel) + V15 (cross-family clamping)
   directly forward.
2. **Industrial demand is huge** — auto radiator / HVAC evaporator /
   gas-turbine recuperator / data center cooling all use compact HX.
   Service market value is ~10× wind turbine analysis.
3. **Defect catalog rebalance** — D5 (mis-aligned shared face)
   has 0/8 cases injecting; case_011 fills this gap. D8 thin fins
   add 7th data point for `[VALIDATED]` cross-topology arc.
4. **NEW engineering metrics** — ε-NTU, fin efficiency, manifold
   maldistribution → 3-4 new post-processors → main-project
   capability extension.
5. **No conflict with deferred sub-sessions** — case_011 doesn't
   exercise A2 (no critical D1 dependence) so V25 placeholder
   issue doesn't block dispatch.

## Hard constraints (Codex must honor)

1. **Solver class**: chtMultiRegionFoam steady. v1 target: 2 fluid
   regions (hot, cold) + 1 solid region (fin matrix + separator
   plates), conjugate heat transfer at all fluid-solid interfaces.
   v2 fallback: chtMultiRegionPimpleFoam if steady residuals
   oscillate (V13 pattern).
2. **CAD source**: Tier 3 parametric. Multi-stream plate-fin HX
   has no public Tier-1 STEP; parametric generation is correct.
   Codex MAY check Tier 2 (GrabCAD industrial-aero tag) but
   Tier-3 is the expected path. If using GrabCAD, license must be
   verified.
3. **Geometry must be physically realistic** — not a toy. Required
   features:
   - Two cross-flow channels (hot above, cold below; OR side-by-
     side; OR concentric — Codex picks)
   - Plate-fin matrix between channels with realistic fin spacing
     (1-3 mm typical for industrial compact HX)
   - Inlet + outlet manifolds on EACH stream (4 boundary patches
     total for fluid streams)
   - Solid fin + plate body as ONE region (cellZone) for thermal
     conduction
   - Realistic dimensions: 100-300 mm length, 50-150 mm width
4. **Defect injection**: exactly 2 defects from catalog. Required
   set: D8 (thin fin shell — 0.5-1.0 mm) + D5 (mis-aligned plate-
   plate interface — 5-50 μm offset between adjacent plate faces).
5. **Patch naming**: all body names ^[A-Za-z][A-Za-z0-9_]*$.
   Specifically required for chtMultiRegion: per-region
   `region_<name>` block in regionProperties.
6. **Multi-region cellZone identification**: parts manifest MUST
   declare each region explicitly with `region_type: fluid|solid`
   and `couples_to: [<region>, <region>, ...]`. Sub-session will
   use this to write `regionProperties` and `coupledTemperatureBC`
   on conjugate interfaces.
7. **Determinism**: CadQuery script byte-identical regeneration.
8. **Industrial flavor**: must be recognizable as a real industrial
   compact HX (auto radiator-like or HVAC evaporator-like).
9. **Reference data**: pick a parametric design point with
   well-documented analytical reference (Kays & London ε-NTU
   correlation predictions for the chosen fin geometry); document
   in defect manifest `reference_data_validity`. The CFD result
   should be comparable to ε-NTU prediction within ±20% if
   geometry honest.

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

10 prior cases (the original roster, all numerics-class roots
covered):
- case_002a (APU bay buoyantSimpleFoam): active
- case_002b (APU bay CHT, multi-region thermal coupling): active
- case_003 through case_010: dispatched (5 of 8 with v1 sediment
  in active state)

You designed case_004 through case_010. **case_011 is the FIRST
case in a NEW STRATEGIC BATCH (Phase 1 #1)** per the strategic
roadmap at `.planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md`.
The new batch pivots from research-benchmark cases toward
industrial-service-market cases. Your case_011 design role:
maximize APU 002b CHT inheritance to demonstrate Pattern 6
working at scale on a completely different industrial part.

## Required reading (in cfd-harness-unified repo)

Read these in order before designing:
1. .planning/methodology/codex_case_design_protocol.md — your
   contract (5 deliverables + validation steps)
2. .planning/methodology/component_bank.md — Tier-3 fallback
   menu; A1 (plate-fin heat sink) is the closest existing
   component but **case_011 is a HEAT EXCHANGER** (multi-stream)
   not a heatsink (single-stream + air). Promote A1 to
   "compact heat exchanger" as needed.
3. .planning/methodology/public_cad_sources.md — check Tier 1
   (likely none for plate-fin HX) and Tier 2 (GrabCAD compact-HX
   tag) before falling back to Tier 3 parametric
4. .planning/methodology/kickoff/case_004_codex_response.md AND
   case_005_codex_response.md AND case_009_codex_response.md —
   examples of your prior multi-deliverable case design output
5. .planning/case_profiles/case_002b_apu_bay_cht.md — the CHT
   case-thread pattern your design inherits
6. .planning/methodology/industrial_case_solver_findings.md —
   V-series; note Pattern 6. case_011's
   incompressible-RANS-CHT-multi-stream class inherits V14 + V15
   (CHT-specific findings) but NOT V3-V13 (single-fluid buoyant)
7. .planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md
   — strategic SSOT for the new batch; case_011 is Phase 1 #1
8. .planning/methodology/knowledge_status_convention.md —
   2026-05-08 harvest 002 convention; apply [QUESTIONABLE] /
   [VALIDATED] markers in your defect manifest where appropriate

## Hard constraints

1. **Solver class**: chtMultiRegionFoam steady. v1: 2 fluid
   regions (hot, cold) + 1 solid region. v2 fallback:
   chtMultiRegionPimpleFoam if oscillation.
2. **CAD source priority**: Tier 3 parametric (plate-fin HX has
   no canonical Tier-1 STEP). Tier 2 GrabCAD acceptable IF
   license-permissive. Document tier choice + justification.
3. **Geometry physical realism**:
   - Two cross-flow (or counter-flow) channels with plate-fin
     matrix between them
   - Industrial dimensions: 100-300 mm length, 50-150 mm width,
     30-80 mm height
   - Realistic fin spacing 1-3 mm
   - 4 fluid boundary patches (hot inlet, hot outlet, cold inlet,
     cold outlet) + 1 solid (no fluid BC, conjugate-only)
   - Manifolds at each end with realistic geometry (not just
     square inlets — real HX has tapered manifolds for flow
     distribution)
4. **Defect injection (REQUIRED 2 defects)**:
   - D8: 0.5-1.0 mm thin fin walls in part of the fin matrix
   - D5: 5-50 μm mis-aligned plate-to-plate interface (real
     manufacturing tolerance defect, UNCOVERED in 003-010 roster)
5. **Patch naming**: ^[A-Za-z][A-Za-z0-9_]*$, OpenFOAM rule.
6. **Multi-region cellZone**: parts manifest MUST declare each
   region with `region_type: fluid|solid` and `couples_to:`.
7. **Industrial flavor**: must be recognizable as auto radiator
   / HVAC evaporator / gas-turbine recuperator. NOT a toy.
8. **Reference data validity**: pick an operating point where
   Kays & London ε-NTU correlation is applicable; document in
   defect manifest. CFD ε vs predicted ε within ±20% expected.
9. **NO Ahmed body, NO NACA, NO Sajben** (Lane B exclusions).
10. **NO new defect categories** outside D1-D10.

## Your 5 deliverables

Same format as case_004/005/009 responses. Per
codex_case_design_protocol.md §"What Codex returns":

### 1. Engineering brief (Markdown)

Sections (mandatory):
- Component picked + bank ID + reasoning (note: A1 doesn't
  exactly fit; you may need to promote it to "compact HX" or
  propose a new bank entry name)
- Engineering question (1-2 sentences: what does the engineer
  want to know?)
- Physics signature: chtMultiRegionFoam, expected Re per stream
  (typical industrial compact HX is Re=200-2000), Pr ≈ 0.7,
  flow regime, target pressure drop, target effectiveness
- Parts inventory: list each region with role (fluid/solid),
  couples_to map, BC plan per region
- Boundary conditions plan: ALL 4 fluid patches + conjugate
  interfaces; explicit T BC at each fluid inlet, p BC type,
  zeroGradient/wall details
- Expected metrics: ε-NTU effectiveness, Δp_hot, Δp_cold,
  outlet T_hot, outlet T_cold, h(x) local distribution along
  hot stream, fin efficiency η_fin, manifold uniformity index
- Hypothesized failure modes (V-findings prediction, including
  multi-stream specific ones — V14/V15 inheritance, plus 3-5
  new ones expected)
- Defect injection summary (D8 + D5 with measurable verification
  commands)
- Sub-session estimated effort (target: 10-12h)

### 2. CAD generation script (Python, executable)

CadQuery preferred. Same requirements as case_004/005:
- Deterministic
- --out CLI with default
- Parametric constants at top (fin_spacing_mm, fin_thickness_mm,
  plate_thickness_mm, channel_height_hot_mm, channel_height_cold_mm,
  HX_length_mm, HX_width_mm, n_fins_per_channel, ...)
- Comments at decision points
- Each region exported as separate named body or compound:
  - region_hot_fluid (single solid representing hot channel volume)
  - region_cold_fluid (single solid representing cold channel volume)
  - region_solid (fin matrix + plates as one body)
  - 4 fluid boundary patches as planar faces (or thin solids)
- Defect injection: D8 reduces fin thickness in part of matrix
  to 0.5-1.0 mm; D5 introduces 5-50 μm offset on one plate
  interface
- STEP export with named bodies preserved (per V16/V24 lessons,
  use cq.Solid.fuse() not cq.Compound.makeCompound() for "one
  body intent")

### 3. STEP file path

Single path string:
/Users/Zhuanz/Desktop/case_011_plate_fin_compact_hx/inputs/cad_codex_v1.step

### 4. Parts manifest YAML

Required fields beyond standard:
- regions: list with region_type (fluid|solid), couples_to,
  bc per fluid region
- thermophysics: hot fluid + cold fluid + solid (use water /
  ethylene glycol / aluminum or similar realistic combos; document
  ρ, μ, Cp, k for each)
- HX operating point: hot inlet T, cold inlet T, hot mass flow,
  cold mass flow, target ε
- ε-NTU reference: predicted effectiveness from Kays & London
  for the chosen geometry + flow rates

### 5. Defect manifest YAML

Two defects per catalog. For D5 mis-aligned interface:
expected_advisor_to_catch should reference the planned A2-v2
gap-detection extension (drafted at
`.planning/patches/draft_a2_v2_gap_detection_2026-05-08.md`) —
acknowledge that A2 v1 cannot detect 5-50 μm interface
mis-alignment (V25 scope-narrow). Apply [QUESTIONABLE] marker
per knowledge_status_convention.md if needed.

For D8 thin fin: expected_advisor_to_catch =
thin_wall_advisor (LANDED, robust 6-of-6, 7th case for case_011).

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

Round 1 of 2 (round 2 reserved for revision if validation fails).

## What you should NOT do

- Do NOT propose a single-stream heatsink (that's case_017's
  scope). case_011 is multi-stream HX.
- Do NOT skip defect injection.
- Do NOT pick Lane-B exclusions.
- Do NOT use cq.Compound.makeCompound for "this should be one
  body" — use cq.Solid.fuse() per V16/V24 lessons.
- Do NOT propose new defects outside D1-D10.
- Do NOT use Ahmed/NACA/Sajben.
- Do NOT exceed 12h estimated sub-session effort (Phase 1 case
  must be tight).

## Begin
```

## Validation checklist (main session runs after Codex responds)

Before writing the per-case kickoff:

- [ ] CAD source picked (Tier 1 / 2 / 3 declared with justification)
- [ ] CadQuery script `python3 -m py_compile` passes
- [ ] Generated STEP would open in FreeCAD without errors
  (verify via `FreeCADCmd -c 'Import.insert(...)'`)
- [ ] FreeCAD reports body count + names matching parts manifest
- [ ] All patch + region names satisfy ^[A-Za-z][A-Za-z0-9_]*$
- [ ] **3 regions explicitly identified** (hot fluid, cold fluid,
      solid) with `region_type` and `couples_to`
- [ ] **4 fluid BC patches** (2 inlets + 2 outlets) declared per
      region
- [ ] **Conjugate interfaces** identified (where fluid touches solid)
- [ ] **Thermophysics** declared for all 3 regions (different
      fluids OK; realistic ρ/μ/Cp/k)
- [ ] **HX operating point** specified (mass flows, inlet temps,
      target ε)
- [ ] **ε-NTU prediction** documented as reference target
- [ ] D8 thin fin: bbox-min < 1.0 mm, advisor reference =
      thin_wall_advisor
- [ ] D5 mis-aligned plate: 5-50 μm offset, advisor reference
      flagged with V25 [QUESTIONABLE] (A2 v1 cannot detect this
      scale)
- [ ] Both defects in regions OUTSIDE the ε-NTU comparison zone
- [ ] BC plan handles conjugate temperature interface explicitly
- [ ] Engineering brief targets chtMultiRegionFoam multi-stream

## After validation passes

1. Save Codex response at `kickoff/case_011_codex_response.md`
2. Format per-case kickoff at `kickoff/case_011_<short_name>.md`
   (apply harvest 002 convention: A2 LANDED + V25 marker if D1
   used, knowledge_status_convention reference, all required
   reading items per case_007-010 pattern)
3. Update `case_proposal_queue.md`: case_011 row from "Active
   queue (Proposed Phase 1)" to "Dispatched"
4. Update `case_index.md` with case_011 row, status=dispatched
5. Tell user: "case_011 kickoff ready. Open new Claude Code
   session and paste contents of `kickoff/case_011_<short_name>.md`."

## Risk mitigations

- If Codex returns a single-stream heatsink instead of multi-
  stream HX → revision request round 2 with explicit "this MUST
  be 2 fluid regions + 1 solid" emphasis
- If Codex picks an unrealistic geometry (toy proportions) →
  revision request with industrial-dimension constraints
- If Codex uses cq.Compound.makeCompound for "one body" intent →
  point to V16/V24 lessons in revision request
- If 86gs gpt-5.5 503s → fall back to CRS gpt-5.4 high; document
  in DEC frontmatter `codex_review_relay: crs (effort=high, fallback)`
