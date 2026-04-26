# Backward-Facing Step (BFS)

> Case ID: `backward_facing_step` · Whitelist row 2 · Status: PASS (post-DEC-V61-052)
> GOV-1 enrichment · 2026-04-26 · Option B

## Physics description

Two-dimensional incompressible separated flow over a backward-facing step. Inlet channel of height H_inlet = 8·H expands to downstream channel of height 9·H, giving expansion ratio ER = 1.125. The flow separates at the step corner, recirculates over a region of length Xr, and reattaches downstream.

- Re_H = 7600 (bulk velocity × step height / ν), post-transition regime
- Solver: `simpleFoam` (steady SIMPLE) + `kOmegaSST` + Spalding wall function
- Mesh: 3-block topology, ~7360 cells in quick-run fixture (36000 cells aspirational)
- Geometry: `BACKWARD_FACING_STEP` adapter path
- Schemes: SIMPLEC + bounded linearUpwind

## Expected behavior

| Observable | Reference | Source |
|---|---|---|
| `reattachment_length` Xr/H | 6.26 (blended anchor: Le/Moin/Kim 6.28 DNS @ Re_H=5100, Driver/Seegmiller 6.26 expt @ Re_H=37500) | Le 1997 / Driver 1985 |
| `cd_mean` | 2.08 (mean drag coefficient, step height H reference) | Le 1997 DNS |
| `pressure_recovery` Cp | inlet -0.90, outlet +0.10, rise +1.00 | Le 1997 DNS |
| `velocity_profile_reattachment` u/U_bulk at x/H=6.0 | y/H=0.5→0.40, y/H=1.0→0.85, y/H=2.0→1.05 | Le 1997 DNS |

The post-transition Xr/H plateau is **weakly Re-sensitive**, not a tight <2% claim — the 10% tolerance band is engineering-justified rather than literature-quoted.

## Boundary-condition compatibility

| BC type | Compatible? | Notes |
|---|---|---|
| Uniform inlet (`fixedValue` U), no-slip walls, zeroGradient outlet | ✅ Canonical | Standard BFS configuration |
| Profiled inlet (developed channel) | ⚠️ Different anchor | Inlet BL state shifts Xr; not the Le 1997 anchor |
| Slip walls | ❌ Breaks reattachment physics | No wall shear → no plateau |
| Periodic side walls (3D) | ⚠️ Different benchmark | 3D BFS has spanwise modulation; needs separate DNS gold |
| Heated walls / passive scalar | ❌ Out of scope | Adds energy equation; different validation target |

## Tolerance → citation map

| Observable | Tolerance | Citation key | Type |
|---|---|---|---|
| `reattachment_length` | 0.10 (relative) | `asme_vv20_2009` | Engineering V&V band; absorbs ER mismatch (1.2 DNS vs 1.125 adapter) + inlet BL state + 2D-empty-patch simplification |
| `cd_mean` | 0.10 (relative) | `asme_vv20_2009` | Engineering, same rationale |
| `pressure_recovery` | 0.10 (relative) | `asme_vv20_2009` | Engineering, same rationale |
| `velocity_profile_reattachment` | 0.10 (relative) | `asme_vv20_2009` | Engineering; profile shape match in qualitative recovery zone |

Citation coverage: 4/4 = 100% (all engineering, anchored to ASME V&V 20).

## Geometry sketch

```
              U_bulk →
        ┌───────────────────────────────────────────────┐
        │                                               │
   inlet│  H_inlet = 8H                                 │outflow
        │                                               │
        └────────┐                                      │
                 │ ↺ recirc. bubble                     │
                 │                                      │
                 │     reattach @ Xr/H ≈ 6.26           │
                 └──────────────────────────────────────┘
                    H ↑                       ↓
                       L_up = 10H ─→  L_down = 30H
```

## Known good results (current adapter, post-DEC-V61-052)

- `reattachment_length`: Xr/H = **5.647** via wall-shear τ_x zero-crossing on `lower_wall` allPatches VTK; -9.8% vs 6.26 (inside 10% tolerance)
- Cross-check: near-wall Ux proxy gives 5.647 (4-digit agreement)
- Solver convergence: continuity sum_local = 1.30e-7, two-fixture Xr stability +0.09% drift t=1000→1500
- G3/G4/G5 attestor gates all clean

## References

See [`citations.bib`](citations.bib). Key refs: Le, Moin & Kim 1997 (DNS Re_H=5100), Driver & Seegmiller 1985 (experiment Re_H≈37500), Armaly 1983 (laminar/transitional envelope), ASME V&V 20-2009.
