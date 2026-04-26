# Rayleigh-Bénard Convection (Ra=10⁶)

> Case ID: `rayleigh_benard_convection` · Whitelist row 10 · Status: COMPATIBLE (gold value PROVISIONAL pending Chaivat 2006 paper re-read)
> GOV-1 enrichment · 2026-04-26 · Option B

## Physics description

Two-dimensional incompressible natural convection in a horizontal layer heated from below and cooled from above. Boussinesq approximation; Pr = 0.71 (air); aspect ratio AR = 2.0. The Rayleigh number Ra = β·g·ΔT·L³ / (ν·α) = 10⁶ sits in the **steady laminar convective** regime — fully turbulent onset is at Ra ≈ 1.5·10⁸ for moderate Pr. The flow develops counter-rotating convection rolls.

- Ra = 10⁶, Pr = 0.71, AR = 2.0
- Solver: `buoyantFoam` + Boussinesq + `turbulenceProperties simulationType laminar` (per DEC-V61-005)
- Mesh: moderate, no dedicated wall functions required
- Geometry: `NATURAL_CONVECTION_CAVITY` adapter path

## Expected behavior (Chaivat 2006, Ra=10⁶ regime)

| Observable | Reference | Source |
|---|---|---|
| `nusselt_number` (mean Nu, hot bottom wall) | 10.5 (PROVISIONAL — Gate Q-new Case 10 HOLD) | Chaivat 2006 |

**Cross-check correlation**: Chaivat 2006 Nu = 0.229 · Ra^0.269. At Ra=10⁶: 0.229 · (10⁶)^0.269 = **9.4** (re-computed), giving 11.5% discrepancy with the stored gold 10.5 — within the declared 15% tolerance but suggesting the original correlation variant or coefficient may differ from the paper's primary equation. Paper re-read pending (HOLD).

## Boundary-condition compatibility

| BC type | Compatible? | Notes |
|---|---|---|
| Bottom T_h, top T_c, periodic side walls (or insulated), Boussinesq | ✅ Canonical | Chaivat 2006 setup |
| Constant-flux walls instead of constant-T | ⚠️ Different anchor | Different correlation family |
| AR ≠ 2.0 | ⚠️ Roll number changes | Stable roll wavelength is roughly L_roll ≈ depth → 2 rolls fit AR=2; AR=1 favors single-cell solutions |
| Pr ≠ 0.71 | ⚠️ Different anchor | Chaivat correlation derived for air-Pr |
| Ra ≥ 1.5·10⁸ (turbulent onset) | ❌ Out of scope | Soft / hard turbulence regime needs different solver path; see differential_heated_cavity FM-DHC-1 for the high-Ra cautionary tale |
| 3D box | ⚠️ Different physics | 3D adds spanwise modulation; needs separate gold |

## Tolerance → citation map

| Observable | Tolerance | Citation key | Type |
|---|---|---|---|
| `nusselt_number` | 0.15 (relative) | `chaivat2006` | Correlation Nu = 0.229·Ra^0.269 has stated correlation uncertainty in the laminar / soft-turbulence onset band; 15% covers the correlation spread + harness mesh + scheme. Literature-anchored, with a documented HOLD on the gold value's exact variant. |

Citation coverage: 1/1 = 100% (literature-anchored to Chaivat 2006).

## Geometry sketch

```
   T_cold (top, Dirichlet)
   ─────────────────────────────────────────
   ↑                                       ↑
   │   ↺  ↻  ↺  ↻      (counter-rotating   │
   │   ↺  ↻  ↺  ↻       convection rolls)  │  L (depth)
   │                                       │
   ↓                                       ↓
   ─────────────────────────────────────────
   T_hot (bottom, Dirichlet)
   ←───────── 2L (AR = 2) ─────────────────→
```

## Known good results

- Docker E2E (Phase 7, 2026-04-16, buoyantFoam Boussinesq Ra=10⁶) reported Nu = 10.5 — matches ref exactly (rel_error = 0.0)
- Convergence flagged OSCILLATING but Nu-value stable
- Per project memory: h URF reduced 0.1 → 0.05 (commit e7fa556) to address oscillation

## References

See [`citations.bib`](citations.bib). Key refs: Chaivat 2006 (primary, the source of the gold value 10.5), Globe & Dropkin 1959 (classical correlation), ASME V&V 20-2009.
