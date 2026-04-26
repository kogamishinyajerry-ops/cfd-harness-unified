# Lid-Driven Cavity (LDC)

> Case ID: `lid_driven_cavity` · Whitelist row 1 · Status: PASS (3 of 4 Ghia observables, secondaries noise-floor-bounded)
> GOV-1 enrichment · 2026-04-26 · Option B (docs-only, no `knowledge/**` writes)

## Physics description

Two-dimensional incompressible square cavity (L=0.1 m) with a lid translating tangentially at constant velocity (U_lid = 1.0 m/s) and three no-slip walls. Steady-state laminar flow at Re = U·L/ν = 100. The flow develops a single primary vortex with two corner eddies (BL bottom-left, BR bottom-right) at this Re; the third (TL top-left) eddy emerges only at Re ≥ 1000.

- Reynolds: 100 (well below the cavity transition regime ~7500)
- Solver: `simpleFoam` (steady SIMPLE), turbulence_model = `laminar`
- Mesh: 129×129 (Ghia mesh) → 16641 cells, structured
- Geometry: `SIMPLE_GRID` adapter path, square cavity

## Expected behavior (Ghia 1982 Re=100 observables)

| Observable | Reference | Source |
|---|---|---|
| `u_centerline` (x=0.5, vary y) | Table I col 2; non-monotone, min u = -0.20581 at y ≈ 0.45 | Ghia 1982 |
| `v_centerline` (y=0.5, vary x) | Table II col 2; min v = -0.24533 at x = 0.8047 | Ghia 1982 |
| `primary_vortex_location` | Table III: x=0.6172, y=0.7344, ψ_min = -0.103423 | Ghia 1982 |
| `secondary_vortices` | Table III: BL (0.0313, 0.0391, ψ=+1.749e-6), BR (0.9453, 0.0625, ψ=+1.254e-5) | Ghia 1982 |

## Boundary-condition compatibility

| BC type | Compatible? | Notes |
|---|---|---|
| Lid translating, three walls no-slip | ✅ Canonical | Re = U_lid·L/ν |
| Lid translating + temperature on walls | ❌ Out of scope | Adds Marangoni / buoyancy coupling — different benchmark family (Iwatsu 1993) |
| Periodic spanwise (3D extension) | ⚠️ Different benchmark | Shankar & Deshpande 2000; needs separate gold |
| Outflow / inflow patches | ❌ Wrong topology | LDC is closed-cavity by definition |
| Slip walls | ❌ Breaks closure | No-slip is required for the corner eddies to exist |

## Tolerance → citation map

| Observable | Tolerance | Citation key | Type |
|---|---|---|---|
| `u_centerline` | 0.05 (relative) | `asme_vv20_2009` | Engineering V&V band absorbing mesh + scheme dissipation; Ghia native grid is 129² so 5% covers truncation on coarser harness meshes |
| `v_centerline` | 0.05 (relative) | `asme_vv20_2009` | Same rationale as u_centerline |
| `primary_vortex_location.position` | 0.02 (relative) | `ghia1982` | Ghia grid spacing 1/128 ≈ 0.0078; ±2 grid cells = 0.016 < 0.02 → literature-anchored |
| `primary_vortex_location.psi` | 0.05 (relative) | `asme_vv20_2009` | Engineering, mirrors u/v tolerance |
| `secondary_vortices.position` | 0.02 (relative) | `ghia1982` | Same Ghia-grid argument as primary position |
| `secondary_vortices.psi` | 0.10 (relative) | `TBD-GOV1` | Relaxed from 0.05 because corner-eddy ψ is 5–6 orders of magnitude smaller than primary; mesh sensitivity dominates. No direct literature anchor for the 10% relaxation. **GOV-1 v0.7 trace attempted** (DEC-V61-086 follow-up): Ghia 1982 Table III gives corner-eddy ψ gold values but no §X mesh-sensitivity table or quantitative discussion of the relaxation factor. Fails methodology §1.1 (direct support); the scale-separation fact visible in Table III is a `gold-value-by-association` path explicitly forbidden by methodology §2. Retained as `TBD-GOV1` pending CFDJerry direction on README §"Open HOLDs" item 3 ("formally accept as engineering choice" path would mint an LDC-specific engineering-choice DEC analog to `dec_v61_057_intake`, enabling tier-(c) classification — Charter-level call, not autonomous). |

Citation coverage: 5/6 = 83%.

## Geometry sketch

```
                   U_lid = 1.0 m/s →
        ┌────────────────────────────┐  y=L
        │          (lid)             │
        │                            │
        │       ●──── primary ─►     │
   no   │       (0.62, 0.73)         │ no
   slip │                            │ slip
        │  ↗ TL                  ↘   │
        │  (none@Re=100)             │
        │                            │
        │  ● BL          ● BR        │
        │  (0.03,0.04)   (0.95,0.06) │
        └────────────────────────────┘  y=0
       x=0          (no-slip)         x=L
```

## Known good results

- `u_centerline`: ATTEST_PASS on current 17-point uniform y grid (Ghia Table I interpolated)
- `v_centerline`: ATTEST_PASS on Ghia Table II native 17-point non-uniform x grid (Re-extracted in DEC-V61-050 batch 1, 2026-04-23)
- `primary_vortex_location`: ATTEST_PASS via 2D-argmin of ψ = ∫₀^y U_x dy' on 129² resampling (DEC-V61-050 batch 3)
- `secondary_vortices`: `all_pass=False` — flagged via signal-to-residual gate (Codex round 1 MED #2, see [`failure_notes.md`](failure_notes.md))

Contract status: `SATISFIED_FOR_U_V_AND_PRIMARY_VORTEX_NOT_SECONDARIES` (3 of 4 Ghia observables fully validated).

## References

See [`citations.bib`](citations.bib). Key refs: Ghia, Ghia & Shin 1982 (Table I/II/III), ASME V&V 20-2009 (tolerance practice).
