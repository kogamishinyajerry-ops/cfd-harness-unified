# case_015 Codex Output Validation

> **Verdict**: **PASS**
> **Designed by**: Codex (gpt-5.4 high, CRS) · single-round emit, 160k tokens
> **Validated**: 2026-05-08
> **Round count**: R1 only · cap=3
> **Note**: Codex used compact section markers (`**1. Engineering brief**` instead of `## Deliverable 1`). Main session normalized to canonical format.

## Validation checklist

| # | Check | Result | Notes |
|---|---|---|---|
| 1 | Tier-1 Vattenfall declared | ✅ | OECD/NEA URL cited (CSNI CFD benchmark + Vattenfall-T-junction report) |
| 2 | py_compile | ✅ | 130 LOC clean |
| 3 | Names regex | ✅ | All entities valid |
| 4 | 3 regions declared | ✅ | region_main_fluid + region_branch_fluid + region_wall_solid |
| 5 | Conjugate interfaces | ✅ | turbulentTemperatureCoupledBaffleMixed at both fluid-solid junctions |
| 6 | Vattenfall geometry | ✅ | main ID 140 mm, branch ID 100 mm, 90°, wall 6 mm SS304 |
| 7 | Operating point matches | ✅ | T_cold=19°C ṁ=9.0 / T_hot=36°C ṁ=6.0 |
| 8 | LES config documented | ✅ | WALE + nutUSpaldingWallFunction + dt=1e-4 + y+ 30-100 |
| 9 | Statistics window | ✅ | min 5 flow-throughs + 10 for FFT |
| 10 | Tx10..Tx100 probes | ✅ | 10 thermocouple sampling stations declared |
| 11 | D5 weld misalignment | ✅ | 60 μm offset (within 30-100 μm spec); [QUESTIONABLE 2026-05-08]; A2-v2 reference |
| 12 | SS304 thermal | ✅ | ρ=7900, cp=500, k=15 W/m·K |
| 13 | Reference tolerance | ✅ | mean ±2K, RMS ±0.5K |
| 14 | Industrial flavor | ✅ | nuclear primary loop / steam pipe |

## Round-cap usage
- R1 (CRS gpt-5.4 high, 160k tok): full 5 deliverables in compact format. Section-marker normalization done by main session.
- R2/R3 reserved.

## Decision
**PASS** — proceed to per-case kickoff.
