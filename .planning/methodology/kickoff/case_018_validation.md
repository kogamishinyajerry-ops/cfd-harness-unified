# case_018 Codex Output Validation

> **Verdict**: **PASS**
> **Designed by**: Codex (gpt-5.4 high, CRS) · 139k tokens, single-round emit
> **Validated**: 2026-05-08 · cap=3, R1 only
> **Note**: Section markers normalized (compact `## N. ...` → canonical `## Deliverable N`)

## Validation checklist

| # | Check | Result | Notes |
|---|---|---|---|
| 1 | Tier-1 Stairmand declared | ✅ | Stairmand high-efficiency cyclone, public literature ratios baked into script |
| 2 | py_compile | ✅ | 157 LOC clean |
| 3 | Names regex | ✅ | All entities valid |
| 4 | Single fluid region | ✅ | region_air |
| 5 | Stairmand dimensions | ✅ | D=250mm; ratios per Stairmand spec (0.5/0.2/1.5/2.5/0.5/0.4 D) |
| 6 | RSM turbulence | ✅ | LaunderGibsonRSTM (NOT k-ε / k-ω-SST) |
| 7 | pimpleFoam transient | ✅ | for vortex precession capture |
| 8 | kinematicCloud one-way | ✅ | particle motion follows air, no momentum feedback |
| 9 | Particle distribution | ✅ | 1-50 μm log-normal, ρ_p=2650 (silica reference) |
| 10 | Operating point | ✅ | U_inlet=20 m/s, Re_D=3.3e5, swirl number S~1-3 |
| 11 | D6 debris | ✅ | 10-30 mm cube in collection chamber; advisor=NONE [QUESTIONABLE]; 2nd D6 evidence (after case_016) |
| 12 | Wall interaction | ✅ | rebound baseline, escape at outlets |
| 13 | Reference data | ✅ | d50 ±10%, η(d_p) ±10-20% per Stairmand correlation |
| 14 | Vortex precession (PVC) | ✅ | acknowledged as expected metric + failure mode |

## Round-cap usage
- R1 (CRS gpt-5.4 high, 139k tok): clean exit. R2/R3 reserved.

## Decision: **PASS**
