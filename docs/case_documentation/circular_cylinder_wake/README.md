# Circular Cylinder Wake (2D Karman shedding)

> Case ID: `circular_cylinder_wake` · Whitelist row 3 · Status: COMPATIBLE_WITH_SILENT_PASS_HAZARD (DEC-V61-053 in flight)
> GOV-1 enrichment · 2026-04-26 · Option B

## Physics description

Two-dimensional incompressible flow past a circular cylinder at Re=100, where the wake forms a periodic Karman vortex street. Re=100 sits in the laminar shedding regime (40 < Re < ~190; 3D transition at Re ≈ 190 per Williamson 1996). Vortices shed alternately from upper and lower cylinder shoulders at the Strouhal frequency.

- Re = 100 (cylinder diameter D × free-stream U / ν)
- Solver: `pimpleFoam` (transient PISO) — laminar (no RAS model)
- Mesh: 40000 cells (BODY_IN_CHANNEL adapter)
- Domain: L_inlet=10D, L_outlet=20D, H=±6D (post-DEC-V61-053 Batch B1; was 20% blockage pre-B1)
- Geometry: `BODY_IN_CHANNEL` adapter path
- Time integration: long enough to capture ≥ 8 shedding cycles + window-trim startup transient

## Expected behavior (Williamson 1996 Re=100)

| Observable | Reference | Source |
|---|---|---|
| `strouhal_number` St = fD/U | 0.164 | Williamson 1996 |
| `cd_mean` | 1.33 | Williamson 1996 |
| `cl_rms` | 0.048 | Williamson 1996 |
| `u_mean_centerline` (wake deficit (U_inf − u)/U_inf) | x/D=1→0.83, x/D=2→0.64, x/D=3→0.55, x/D=5→0.35 | Williamson 1996 |

> **Naming caveat**: gold YAML key is `u_Uinf` (historical), but values are wake **deficit**, not raw u/U_inf. Per-point `description: centerline velocity deficit` confirms intent. Extractor `cylinder_centerline_extractor.py` self-names output keys `deficit_x_over_D_*`. Rename deferred to a future DEC due to downstream blast radius.

## Boundary-condition compatibility

| BC type | Compatible? | Notes |
|---|---|---|
| Uniform freestream + cylinder no-slip | ✅ Canonical | Williamson 1996 anchor |
| Confined channel (small H/D) | ⚠️ Different anchor | Blockage > 5% biases Cd; current 8.3% gives ~3-5% Cd bias |
| Symmetry plane along wake centerline | ❌ Wrong physics | Suppresses Karman shedding entirely |
| Periodic spanwise (3D) at Re > 190 | ⚠️ Different regime | 3D transition; needs separate gold |
| RANS turbulence model (kOmegaSST etc.) | ❌ Over-dissipative at Re=100 | Under-predicts St 10-20%, Cl_rms 30-50%; whitelist explicitly declares laminar |

## Tolerance → citation map

| Observable | Tolerance | Citation key | Type |
|---|---|---|---|
| `strouhal_number` | 0.05 (relative) | `williamson1996` | Williamson reports St scatter ~3% across Re=100 references; 5% covers numerical FFT windowing |
| `cd_mean` | 0.05 (relative) | `williamson1996` | Williamson Cd repeatability ~3-5%; tolerance covers blockage residual |
| `cl_rms` | 0.05 (relative) | `williamson1996` | Williamson Cl_rms scatter ~5%; mesh + windowing |
| `u_mean_centerline` | 0.05 (relative) | `asme_vv20_2009` | Engineering V&V band; deficit profile shape match |

Citation coverage: 4/4 = 100% (3 literature-anchored + 1 engineering).

## Geometry sketch

```
      U_inf →
   ┌─────────────────────────────────────────────┐  H = +6D
   │                                             │
   │            ●                                │
   │         (cylinder D=1)                      │
   │            │                                │
   │            └── Karman vortex street ──→     │
   │                                             │
   └─────────────────────────────────────────────┘  H = -6D
   ↑                                              ↑
  L_inlet=10D ←──────── L_outlet=20D ────────────→
```

## Known good results

- DEC-V61-041 retired the canonical_st=0.165 hardcode; St now from FFT of Cl(t) on the trimmed time-series (forceCoeffs FO output)
- DEC-V61-053 Batch B1 grew domain from 20% to 8.3% blockage (commit 63c11cb / f1a9cf3); residual 3-5% Cd bias documented as RESIDUAL_RISK_CARRIED
- Active hazard: silent `kOmegaSST` override in adapter ignores whitelist `turbulence_model: laminar` field (foam_agent_adapter.py:515-518 → :668). Resolution plan in DEC-V61-053 Batch B1 decision (a).

## References

See [`citations.bib`](citations.bib). Key refs: Williamson 1996 (Annu. Rev. Fluid Mech.), Zdravkovich 1997 (blockage corrections), ASME V&V 20-2009.
