# Fully Developed Turbulent Square-Duct Flow

> Case ID: `duct_flow` · Whitelist row 5 · Status: SATISFIED (post-DEC-V61-011 rename)
> Legacy aliases: `fully_developed_pipe`, `fully_developed_turbulent_pipe_flow` (preserved via `legacy_case_ids`)
> GOV-1 enrichment · 2026-04-26 · Option B

## Physics description

Fully developed turbulent flow in a smooth-walled rectangular duct with aspect ratio 1 (square cross-section), incompressible. The Reynolds number Re = 50000 is based on hydraulic diameter D_h = side length. The flow is parallel and unidirectional in the streamwise direction (∂u/∂x = 0).

- Re = 50000, hydraulic_diameter = 0.1 m, aspect_ratio = 1.0
- Solver: `simpleFoam` (steady SIMPLE) + k-ε (whitelist) — runs as periodic / sufficient L/D_h
- Mesh: `SIMPLE_GRID` adapter path (rectangular block domain, **not** circular pipe)
- Smooth walls: Nikuradse sand-grain roughness ε → 0

## Expected behavior (Jones 1976)

| Observable | Reference | Source |
|---|---|---|
| `friction_factor` (Darcy f) at Re=50000 | f = 0.0185 (Jones 1976 smooth square duct) | Jones 1976 |

Cross-check: Colebrook smooth pipe at Re=50000 gives f ≈ 0.0206. Jones 1976 correlation: f_duct ≈ 0.88 · f_pipe(Re_h) ≈ 0.88 · 0.0206 = 0.0181. The stored ref_value 0.0185 sits inside both Jones (±10%) and Colebrook (±8%) bands.

## Boundary-condition compatibility

| BC type | Compatible? | Notes |
|---|---|---|
| Periodic streamwise + no-slip walls + driven by ∂p/∂x | ✅ Canonical | Standard fully developed |
| Inlet/outlet with sufficient L/D_h to develop | ✅ Compatible | Adapter path |
| Circular cross-section | ❌ Different geometry | Use a true axisymmetric pipe gold (NOT this case) |
| Roughened walls | ❌ Out of scope | Adds Nikuradse / Colebrook roughness term |
| Heated walls (Nu correlation) | ❌ Different validation target | Adds energy equation |
| Aspect ratio ≠ 1 (rectangular slabs) | ⚠️ Different correlation | Jones 1976 covers AR ∈ [1, 8]; AR ≠ 1 needs the appropriate correlation row |

## Tolerance → citation map

| Observable | Tolerance | Citation key | Type |
|---|---|---|---|
| `friction_factor` | 0.10 (relative) | `jones1976` | Jones 1976 correlation uncertainty band; the rectangular-duct correlation is wider than Moody-pipe (~5%) because the secondary-flow contribution to wall shear varies with AR. Literature-anchored. |

Citation coverage: 1/1 = 100% (literature-anchored to Jones 1976).

## Geometry sketch

```
   periodic streamwise / sufficient L/D_h
        ┌──────────────────────────┐
        │                          │   ↑
   no   │       u(y, z)            │   D_h = 0.1
   slip │   secondary flow ⤺ ⤻     │   (side length)
        │                          │   ↓
        └──────────────────────────┘
        ←──── square (AR=1) ──────→
```

Secondary flows (Prandtl's second kind, ~0.5-2% of bulk velocity) are the physical origin of the 0.88 reduction factor relative to circular pipe at the same Re_h.

## Known good results

- `friction_factor`: post-DEC-V61-011 verdict matches gold within 10% on the rectangular SIMPLE_GRID adapter (numerical agreement preserved across the rename: pre-rename used Colebrook 0.0181, post-rename uses Jones 0.0185, comparator within 2% — verdict unchanged)

## References

See [`citations.bib`](citations.bib). Key refs: Jones 1976 (primary), Jones & Launder 1973 (k-ε original), Colebrook 1939 (cross-check pipe correlation), ASME V&V 20-2009.
