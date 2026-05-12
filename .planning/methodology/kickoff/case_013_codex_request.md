# Codex Case-Design Request · case_013

> **Status**: PENDING — Codex round 1 not yet sent.
> **Phase**: Industrial Extension Phase 2 #1 per
> `.planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md`.
> **Strategic role**: Confined high-speed rotating machinery with phase change —
> replaces case_004's open-rotor with industrial-mainstream confined pump.
> Combines case_004 MRF infrastructure + NEW phase-change solver (cavitatingFoam).
> **Backend**: 86gs gpt-5.5 xhigh primary (complex turbomachinery reasoning);
> CRS gpt-5.4 high fallback.
> **Soft blocker**: A2-v2 sub-DEC ideally landed before this dispatch, but D1
> (tip clearance) verification can use `[QUESTIONABLE]` marker per harvest 002
> convention pending A2-v2 land.

## Target

| field | value |
|---|---|
| case_id | `case_013_<short_name>` (Codex picks; suggested: `centrifugal_pump_cavitating`) |
| solver_class_target | Confined rotating + phase change: `simpleFoam` + MRF for v1 (no cavitation, head curve baseline); `cavitatingFoam` or `interPhaseChangeFoam` for v2 (NPSH onset + cavitation map) |
| numerics_class | incompressible-MRF-cavitating (NEW root — combines case_004 MRF + first phase-change physics) |
| coverage map row to fill | "Industrial confined rotating machinery (pump/compressor/fan)" — currently uncovered (case_004 is open wind-rotor, NOT confined industrial) |
| CAD source priority | Tier 2-adjacent (ERCOFTAC pump benchmark or Pumpkit reference geometry) → Tier 3 parametric fallback. Document license check |
| defect injection count | 2 |
| defect injection hint | D1 (impeller tip clearance gap, 0.1-0.5 mm — performance-critical, real industrial spec) + **D7** (CAM blade leading-edge wrong-normal — 2nd D7 injection if case_012 already landed) |
| sandbox path suggestion | `~/Desktop/case_013_centrifugal_pump_cavitating/` |

## Why centrifugal pump as case_013 (Phase 2 #1 strategic role)

After Phase 1 (cases 011-012, direct APU CHT/buoyant reuse),
Phase 2 establishes industrial **confined rotating machinery**
credibility — case_004 wind turbine alone is **insufficient** for
the bulk of industrial-service rotating-machinery work:

1. **case_004 limitation**: open-rotor (wind turbine), no confined
   flow, no phase change, no performance curves, no NPSH. 80% of
   industrial-service rotating-machinery work involves **confined
   high-speed rotation** in pumps/compressors/fans.
2. **Largest single class**: centrifugal pumps are the largest
   single class of industrial fluid machinery (water treatment,
   oil-gas, chemical, power, HVAC chilled-water loops).
3. **Cavitation = real $$$**: pump cavitation is a high-value
   industrial CFD diagnostic (NPSH margin, cavitation onset
   location). First phase-change physics for project.
4. **MRF infrastructure reuse**: case_004 MRFProperties writer +
   `08b_write_mrf.py` + `07b_audit_mrf.py` directly applicable;
   confined-volute MRF zone definition is the NEW element.
5. **Defect rebalance**: D1 9th-or-10th injection (depending on
   012 sequence) extends to NEW topology (impeller blade tips);
   D7 second injection if case_012 already landed (consistency
   check on advisor-gap surfacing).

## Hard constraints (Codex must honor)

1. **Solver class**: v1 = `simpleFoam` + MRF (no cavitation; head
   curve baseline at 3-5 flow rates spanning Q/Q_BEP = 0.6 - 1.2);
   v2 = `cavitatingFoam` or `interPhaseChangeFoam` (cavitation
   onset + extent at low NPSH operating point). Document v1 → v2
   transition criteria explicitly.
2. **CAD source**: Tier 2 ERCOFTAC pump benchmark OR Pumpkit
   reference geometry preferred (publicly documented impeller +
   volute). Tier 3 parametric fallback if license blocks.
   Document tier choice + license.
3. **Geometry must be physically realistic** — not a toy. Required
   features:
   - **Impeller**: 5-7 backward-curved blades, realistic
     impeller diameter D2 = 200-400 mm (industrial size class)
   - **Volute**: spiral casing with realistic cutwater geometry
     (NOT just a circular duct around impeller)
   - **Suction inlet**: axial inlet pipe with realistic length
     (≥ 4× D2 for inlet flow development)
   - **Discharge outlet**: tangential outlet from volute with
     transition to straight pipe
   - **Tip clearance**: realistic 0.3-1.0 mm baseline gap between
     impeller blade tip and volute shroud (D1 defect = additional
     0.1-0.5 mm GAP-DEFECT in ONE blade tip vs nominal)
4. **Defect injection**: exactly 2 defects from catalog. Required
   set:
   - **D1**: tip clearance gap defect on ONE blade — 0.1-0.5 mm
     additional gap beyond nominal (real manufacturing
     out-of-tolerance defect). Apply [QUESTIONABLE 2026-05-08]
     marker (A2 v1 cannot field-validate gap distance per V25;
     A2-v2 draft pending).
   - **D7**: wrong-normal face on ONE CAM blade leading edge
     (15-30° rotation around blade chord axis from intended
     orientation). Advisor=NONE per case_012 outcome (or A4 if
     case_012 retro lands D7 advisor).
5. **Patch naming**: all body names `^[A-Za-z][A-Za-z0-9_]*$`.
6. **Multi-region cellZone**: parts manifest MUST declare:
   - `region_fluid` (single fluid: water; cavitating mixture in v2)
   - **MRF zone** declared as cellZone within region_fluid (NOT
     a separate region — this is single-region MRF, not
     chtMultiRegion)
   - Patches: suction_inlet, discharge_outlet, blade_<i>,
     blade_tip_<i>, volute_shroud, volute_cutwater, hub_disk,
     casing_walls, axial_inlet_pipe_walls
7. **Operating point**: pick a documented industrial design point
   - N (rotation): 1450 or 2900 rpm (50 Hz industry standard)
     OR 1750 or 3500 rpm (60 Hz)
   - Q_BEP (best-efficiency-point flow): documented from chosen
     reference (ERCOFTAC or Pumpkit)
   - H_BEP (head): documented
   - NPSH_required curve: document operating points spanning
     above-NPSHr / at-NPSHr / below-NPSHr for cavitation map
8. **Determinism**: CadQuery script byte-identical regeneration.
9. **Industrial flavor**: must be recognizable as ERCOFTAC /
   Pumpkit-style centrifugal pump with realistic volute.
10. **Reference data**: predicted H(Q) curve at 3-5 flow points,
    η(Q) efficiency curve, NPSH_3% curve. CFD H within ±10% of
    reference at BEP; cavitation onset NPSH within ±15%.

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

12 prior cases (original 10-case roster + Phase 1 of new batch):
- case_002a (APU bay buoyantSimpleFoam): active · v14
- case_002b (APU bay CHT chtMultiRegionFoam): active · v2
- case_003 through case_010: dispatched (5 of 8 with v1 sediment)
- case_011 (plate-fin compact HX, multi-stream CHT): dispatched
- case_012 (HVAC supply diffuser, buoyantSimpleFoam): dispatched

You designed case_004 through case_012. **case_013 is Phase 2 #1**
per the strategic roadmap. Phase 2 establishes industrial
confined rotating machinery — case_004 (wind turbine, open-rotor)
is insufficient because mainstream industrial rotating machinery
is **confined high-speed rotating with phase change** (centrifugal
pumps, centrifugal compressors). Your case_013 design role:
extend MRF infrastructure from case_004 to confined-volute
geometry, plus FIRST phase-change physics for the project.

## Required reading (in cfd-harness-unified repo)

Read these in order before designing:
1. .planning/methodology/codex_case_design_protocol.md — your
   contract (5 deliverables + validation steps)
2. .planning/methodology/component_bank.md — D-class pump entries
3. .planning/methodology/public_cad_sources.md — Tier 2 ERCOFTAC /
   Pumpkit options
4. .planning/methodology/kickoff/case_004_codex_response.md —
   MRF infrastructure prior art
5. .planning/methodology/kickoff/case_005_codex_response.md AND
   case_011_codex_response.md — multi-region examples (note: 013
   is single-region MRF, NOT multi-region CHT)
6. .planning/case_profiles/case_004_nrel_phase_vi_mrf.md — your
   prior MRF case (open rotor; 013 is confined volute)
7. .planning/methodology/industrial_case_solver_findings.md —
   V-series; case_013 inherits MRF lessons (V22-V24) but
   cavitation phase-change physics is NEW (no inheritance)
8. .planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md
   — strategic SSOT; case_013 is Phase 2 #1
9. .planning/strategic/case_013_020_dispatch_plan_2026-05-08.md —
   per-case readiness criteria
10. .planning/methodology/knowledge_status_convention.md — apply
    [QUESTIONABLE] markers on D1 verification

## Hard constraints

1. **Solver class**: v1 = simpleFoam + MRF (head curve baseline at
   Q/Q_BEP = 0.6-1.2 flow points, no cavitation); v2 = cavitatingFoam
   or interPhaseChangeFoam (cavitation onset at low-NPSH operating
   point). Document v1 → v2 transition criteria.
2. **CAD source priority**: Tier 2 ERCOFTAC pump or Pumpkit
   reference geometry. Tier 3 parametric fallback if license
   blocks. Document choice.
3. **Geometry physical realism**:
   - 5-7 backward-curved blades, D2 = 200-400 mm
   - Realistic spiral volute with cutwater (NOT circular duct)
   - Axial suction inlet pipe ≥ 4× D2 length
   - Tangential discharge outlet with straight-pipe transition
   - Realistic tip clearance baseline 0.3-1.0 mm
4. **Defect injection (REQUIRED 2 defects)**:
   - D1: tip clearance gap on ONE blade, 0.1-0.5 mm additional
     beyond nominal. Apply [QUESTIONABLE 2026-05-08] per V25.
   - D7: wrong-normal face on ONE CAM blade leading edge,
     15-30° rotation. Advisor=NONE in v1 (or A4 if case_012
     retro lands D7 advisor — sub-session checks at execute time).
5. **Patch naming**: ^[A-Za-z][A-Za-z0-9_]*$.
6. **Single fluid region** + MRF zone as cellZone (NOT
   multi-region; cavitation in v2 uses two-phase mixture, still
   single region).
7. **Industrial flavor**: ERCOFTAC / Pumpkit-style centrifugal
   pump; recognizable as water-treatment / oil-gas pump.
8. **Operating point**: documented N (1450/2900/1750/3500 rpm),
   Q_BEP, H_BEP, NPSHr curve from chosen reference.
9. **Reference data validity**: H(Q) ± 10%, NPSH_onset ± 15%
   tolerance.
10. **NO Ahmed/NACA/Sajben** (Lane B; not relevant).
11. **NO new defect categories** outside D1-D10.
12. **NO open-rotor** (that's case_004 territory; 013 is confined).

## Your 5 deliverables

Same format as case_011/012 responses. Per
codex_case_design_protocol.md §"What Codex returns":

### 1. Engineering brief (Markdown)

Sections (mandatory):
- Component picked + bank ID + reasoning (D-class pump entry)
- Engineering question (1-2 sentences: typical "does this pump
  meet H-Q-η spec at design point with the as-installed defect
  set; where does cavitation onset occur as NPSH degrades?")
- Physics signature: simpleFoam + MRF, expected Re_impeller
  (typical 1e5-1e6), turbulence model selection (k-ε vs k-ω-SST
  for confined rotating; document choice rationale), cavitatingFoam
  for v2 (Schnerr-Sauer or Kunz model)
- Parts inventory: region_fluid + MRF cellZone declaration,
  patches list with bc plan
- BC plan: suction_inlet (totalPressure or flowRateInlet),
  discharge_outlet (pressureOutlet at design back-pressure for
  v1; reduced for v2 NPSH degradation), blade walls (no-slip),
  hub/shroud walls (rotating wall in MRF zone, no-slip otherwise)
- Expected metrics: H(Q) curve at 5 points, η(Q), NPSHr at 3
  points (above/at/below 3% head drop), cavitation map at lowest
  NPSH point (vapor volume fraction iso-surface)
- Hypothesized failure modes (V-findings prediction):
  - V22 inheritance from case_004 (MRF rotation BC patterns)
  - NEW: cavitation phase-change BC pathology (vapor pressure +
    saturation curve)
  - NEW: confined-volute MRF zone boundary placement (vs open
    rotor case_004 — different cellZone topology)
  - NEW: NPSH inlet boundary specification (totalPressure with
    cavitation-saturation reference)
  - NEW: tip-shear capture grid sensitivity
- Defect injection summary (D1 + D7 with measurable verification
  commands)
- Sub-session estimated effort (target: 12-15h — longer than 011
  due to cavitation phase-change pipeline novelty)

### 2. CAD generation script (Python, executable)

CadQuery preferred (or pythonOCC if cavitatingFoam reference
geometry comes as STEP):
- Deterministic
- --out CLI with default
- Parametric constants (n_blades, D2, blade_angle_inlet, blade_angle_outlet,
  volute_throat_area, cutwater_position, tip_clearance_baseline_mm,
  d1_tip_gap_offset_mm, d7_blade_index, d7_normal_rotation_deg, ...)
- Comments at decision points
- Single fused fluid region body + named patches (all blades named,
  blade_tip_<i> patches separately for tip-leakage post-processing)
- Defect injection: D1 enlarges tip clearance on blade_<i>;
  D7 rotates leading edge of blade_<j>
- STEP export with named patches preserved (cq.Solid.fuse() per
  V16/V24)

### 3. STEP file path

Single path string:
/Users/Zhuanz/Desktop/case_013_centrifugal_pump_cavitating/inputs/cad_codex_v1.step

### 4. Parts manifest YAML

Required fields beyond standard:
- region: region_fluid (single)
- mrf_zone: cellZone declaration with axis + omega
- patches: full list with bc_type plan
- thermophysics_v1: water (single phase, simpleFoam)
- thermophysics_v2: water + water_vapor mixture for cavitatingFoam
  (Schnerr-Sauer or Kunz cavitation model parameters)
- pump operating point: N rpm, Q_BEP, H_BEP, NPSHr at 3 points
- reference: ERCOFTAC pump or Pumpkit benchmark citation

### 5. Defect manifest YAML

Two defects per catalog. For D1:
expected_advisor_to_catch should reference A2-v2 draft (A2 v1
cannot field-validate tip-clearance gap distance per V25).
Apply [QUESTIONABLE 2026-05-08] marker.

For D7: expected_advisor_to_catch = TBD (NONE in v1 if case_012
retro hasn't landed D7 advisor; A4 candidate if it has).
Sub-session manually verifies via FreeCAD `Face.normalAt()`.

## Format your response

(same as case_011/012)

## Round budget

Round 1 of 3 (cap=3 per V133).

## What you should NOT do

- Do NOT propose open-rotor (that's case_004 territory)
- Do NOT skip cavitation v2 (the v1+v2 progression is the case
  identity)
- Do NOT use chtMultiRegionFoam (single-region + MRF cellZone,
  NOT multi-region)
- Do NOT skip realistic volute (cutwater geometry is required)
- Do NOT exceed 15h estimated effort
- Do NOT propose D8 thin blade (that's case_014 compressor's
  defect; D7 is the under-utilized choice for 013)
- Do NOT use Ahmed/NACA/Sajben

## Begin
```

## Validation checklist (main session runs after Codex responds)

- [ ] CAD source picked (Tier 2 / Tier 3 with license check)
- [ ] CadQuery script `python3 -m py_compile` passes
- [ ] All patch + region names satisfy ^[A-Za-z][A-Za-z0-9_]*$
- [ ] **Single region_fluid** declared (NOT multi-region)
- [ ] **MRF zone** declared as cellZone with axis + omega
- [ ] **5-7 backward-curved blades** with realistic D2
- [ ] **Spiral volute with cutwater** (not circular duct)
- [ ] **Axial suction inlet ≥ 4× D2** length
- [ ] **Tip clearance baseline** declared (0.3-1.0 mm)
- [ ] D1 tip-gap defect: 0.1-0.5 mm additional, [QUESTIONABLE]
- [ ] D7 wrong-normal blade: 15-30° rotation, advisor=TBD
- [ ] Both defects in OUTSIDE the H(Q)/η_BEP comparison zone
      (defects on edge blade or LE; comparison uses bulk impeller)
- [ ] Operating point documented (N, Q_BEP, H_BEP, NPSHr)
- [ ] Reference (ERCOFTAC / Pumpkit) cited
- [ ] v1 → v2 transition criteria explicit
- [ ] Cavitation model selection documented (Schnerr-Sauer / Kunz)

## After validation passes

1. Save Codex response at `kickoff/case_013_codex_response.md`
2. Format kickoff at `kickoff/case_013_<short_name>.md`
3. Update `case_proposal_queue.md`: case_013 → Dispatched
4. Update `case_index.md` with case_013 row
5. Tell user: "case_013 kickoff ready"

## Risk mitigations

- If Codex returns open-rotor (case_004 redux) → revision round 2
- If Codex skips cavitation v2 → revision round 2
- If Codex picks Tier-3 from-scratch when ERCOFTAC pump available →
  challenge in revision; accept if license issue documented
- If 86gs gpt-5.5 503/429 → fall back to CRS gpt-5.4 high
