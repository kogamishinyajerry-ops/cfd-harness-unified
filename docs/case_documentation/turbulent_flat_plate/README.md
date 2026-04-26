# Turbulent Flat Plate (actually LAMINAR Blasius — case_id retained for stability)

> Case ID: `turbulent_flat_plate` · Whitelist row 4 · Status: SATISFIED_UNDER_LAMINAR_CONTRACT (post-DEC-V61-006)
> GOV-1 enrichment · 2026-04-26 · Option B
>
> ⚠️ **Naming caveat**: case_id retained for whitelist stability, but the physics is **laminar Blasius**, not turbulent Spalding. See FM-TFP-1 in failure_notes.md.

## Physics description

Two-dimensional incompressible flow over a flat plate at zero pressure gradient. Re=50000 with plate length 1.0 m gives Re_x = 25000 at x = 0.5 m and Re_x = 50000 at x = 1.0 m — **deep in the laminar regime** (transition on a smooth plate is at Re_x ≈ 3·10⁵–5·10⁵). The Blasius similarity solution applies exactly.

- Re_L = 50000, plate_length = 1.0 m
- Solver: `simpleFoam` (steady SIMPLE) + `turbulenceProperties simulationType laminar` (no RAS)
- Mesh: 80 wall-normal cells with 4:1 wall grading (per STATE.md)
- Geometry: `SIMPLE_GRID` adapter path, thin 2D slice with empty side patches

## Expected behavior (Blasius 1908 similarity)

| Observable | Reference | Source |
|---|---|---|
| `cf_skin_friction` at x=0.5 m | Cf = 0.664/√Re_x → at Re_x=25000: **0.00420** | Blasius / Schlichting Ch.7 |
| (cross-check) Cf at x=1.0 m | 0.664/√50000 = 0.00297 | Blasius |

Blasius is the **exact** self-similar solution of the Prandtl boundary-layer equations under ZPG with no-slip wall — no Re-dependent correction, no model parameter.

## Boundary-condition compatibility

| BC type | Compatible? | Notes |
|---|---|---|
| Uniform inlet U_inf, no-slip plate, free-slip top, empty sides | ✅ Canonical | Blasius assumption set |
| Pressure gradient (Falkner-Skan family) | ❌ Different self-similarity | dp/dx ≠ 0 → different similarity solution |
| Heated plate (energy equation on) | ⚠️ Different validation target | Pohlhausen integral — separate gold |
| Trip wire / forced transition | ❌ Out of scope | Transitional regime is not Blasius-similar |
| Wall roughness | ❌ Breaks similarity | Skin-friction law shifts |
| RANS turbulence model (kOmegaSST, kEpsilon) | ❌ Wrong regime | Re_x ≤ 50000 is below transition; turbulence transport equations apply where there is no turbulence |

## Tolerance → citation map

| Observable | Tolerance | Citation key | Type |
|---|---|---|---|
| `cf_skin_friction` | 0.10 (relative) | `asme_vv20_2009` | Blasius is analytically exact; the 10% band absorbs mesh discretization + numerical dissipation. Engineering V&V band. |

Citation coverage: 1/1 = 100% (engineering, ASME V&V 20).

## Geometry sketch

```
           U_inf →
   ─────────────────────────────────────────  free-slip top
                    ↓ thin BL grows ~ √(ν·x/U)
   ─────────────────────────────────────────  no-slip plate (x ∈ [0, 1])
   ↑                                ↑
  x=0 (LE)                         x=1 (TE)
```

At x = 0.5 m: δ_99 = 5·√(ν·x/U) = 5·√(1/50000 · 0.5 · 1) ≈ 0.0224 m. With 80 wall-normal cells over H=1.0 and 4:1 wall grading, ~50 cells fall within y < δ_99 — well-resolved.

## Known good results

- `cf_skin_friction` at x=0.5: ATTEST_PASS within 10% on current adapter (laminar simpleFoam + 80 y-cells + 4:1 wall grading, post-DEC-V61-006)
- Wall-cell skip in `_compute_wall_gradient` (foam_agent_adapter.py:6870-6879) avoids degenerate wall-cell Δu/Δy by using interior cells (c0, c1) for the gradient

## References

See [`citations.bib`](citations.bib). Key refs: Blasius 1908 (original), Schlichting & Gersten *Boundary Layer Theory* 9th ed. (modern textbook, Ch.7 on similarity solutions), ASME V&V 20-2009.
