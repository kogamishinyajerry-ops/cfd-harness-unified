# case_012 Codex Output Validation

> **Verdict**: **PASS**
> **Designed by**: Codex (gpt-5.4 high, CRS) · single-round emit, 118k tokens
> **Validated**: 2026-05-08 by main session
> **Round count**: R1 only (cap=3 per V133)
> **Backend rationale**: CRS gpt-5.4 high (saves 86gs xhigh quota for Phase 2 turbomachinery cases 013/014). Phase 1 #2 is a buoyantSimpleFoam direct-inheritance case; CRS suffices.

## 14-item validation checklist

| # | Check | Result | Notes |
|---|---|---|---|
| 1 | CAD source declared | ✅ | Tier-3 parametric CadQuery, bank ID `B_HVAC_DIFFUSER_01` |
| 2 | `python3 -m py_compile` | ✅ | 248 LOC compiles clean |
| 3 | STEP openable in FreeCAD | ⏳ | Defer to sub-session |
| 4 | Body count + names match manifest | ⏳ | Defer to sub-session |
| 5 | Names regex `^[A-Za-z][A-Za-z0-9_]*$` | ✅ | All entity names verified |
| 6 | Single fluid region (NOT multi-region) | ✅ | `region_air` only; no CHT in v1 |
| 7 | Realistic louver geometry | ✅ | 4-way ceiling diffuser with 4 louver vanes (louver_vane_0..3); 32° angle |
| 8 | At least 1 heat source patch | ✅ | 4 occupants (75 W each) + 1 equipment patch (200 W) = 500 W total |
| 9 | Supply + return both declared | ✅ | supply_inlet (T=289.15K, U=2.6 m/s) + return_outlet (pressureOutlet) |
| 10 | Boussinesq buoyancy declared | ✅ | T_ref=293.15K, ρ_ref=1.204, β=0.00341, gravity=(0,0,-9.81) |
| 11 | ADPI reference documented | ✅ | predicted 85%, target ≥80%, ASHRAE 55 / IEA Annex 20 basis |
| 12 | D1 slot gap, [QUESTIONABLE] marker | ✅ | 0.35 mm gap diffuser_face_plate ↔ ceiling; 9th D1 in project; A2-v2 reference |
| 13 | D7 wrong-normal louver, advisor=NONE | ✅ | louver_vane_2 rotated 38° from intended; first D7 injection; flagged for retro |
| 14 | Both defects outside ADPI comparison zone | ✅ | both on diffuser hardware periphery; occupied-zone (room interior) is ADPI comparison zone |

## Bonus checks

- **Engineering brief targets buoyantSimpleFoam single-region** ✅
- **Realistic room dimensions** ✅ — 6.0 × 4.5 × 3.0 m (within 5-8 × 4-6 × 3 range)
- **Realistic supply jet** ✅ — T=16°C, U=2.6 m/s (within ASHRAE design)
- **Industrial flavor** ✅ — recognizable commercial office topology
- **Determinism** ⏳ defer to sub-session (script structure supports byte-identical regen)
- **D7 retro flag** ✅ — explicit "post-case_012 retro: A4 advisor candidate"

## Round-cap usage

- R1 (CRS gpt-5.4 high, 118k tokens): full 5 deliverables, clean exit. No revision triggered.
- R2/R3 reserved.

## Per harvest-002 convention

- D1 verification gets `[QUESTIONABLE 2026-05-08]` marker per V25 (A2 v1 cannot field-validate 0.35 mm gap distance).
- D7 verification flags advisor-gap (no LANDED advisor for face-orientation); post-case_012 retro evaluates A4 promotion.

## Decision

**PASS** — proceed to per-case kickoff format.
