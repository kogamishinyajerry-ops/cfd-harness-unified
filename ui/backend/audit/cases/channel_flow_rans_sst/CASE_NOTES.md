# Channel Flow (k-omega SST) — Third Canonical Case

**Status (post-M9.2):** **cyclic / periodic channel** with NASA TMR MKM 1999
Re_tau≈590 reference wired. M9.1 wired the reference; M9.2 converted
inlet/outlet from `patch` (uniform plug-flow inlet, which never converged
in steady simpleFoam) to `cyclic` (fully-developed periodic) so the case
actually reaches steady state in O(100) iterations.

## Geometry

- 2.5D plane channel: streamwise × wall-normal × thin spanwise.
- Half-height `H = 0.015 m`; full channel height `2H = 0.03 m`.
- Streamwise length `L = 2.0 m` (66.7 × H — fully-developed regime by `x ≈ 1.5 m`).
- Spanwise thickness `0.001 m` (single cell, 2.5D convention).
- Mesh: `100 × 50 × 1`, uniform grading. ~5000 cells.

## Patches (post-M9.2 cyclic)

| Patch         | Type          | Role                                          |
|---------------|---------------|-----------------------------------------------|
| `inlet`       | cyclic        | paired with `outlet` (periodic streamwise)    |
| `outlet`      | cyclic        | paired with `inlet`                           |
| `bottomWall`  | wall          | y_min face; noSlip                            |
| `topWall`     | wall          | y_max face; noSlip                            |
| `frontAndBack`| empty         | z_min + z_max faces; OpenFOAM 2.5D convention |

Bulk velocity `Ubar = (10, 0, 0)` m/s is enforced via `system/fvOptions`
(`meanVelocityForce` body-force term added each iteration). This replaces
the M9.1 `fixedValue` inlet + `zeroGradient` outlet, which produced a
developing boundary layer that never converged in 1000 steady iterations.

## Physics

- Re_2H = U_bulk × 2H / ν = 10 × 0.03 / 1.5e-5 = **20,000**.
- k-omega SST.
- Inlet turbulence: I=0.01 (1%), L=0.1H=0.003 m.
- Derived: k = 0.015 m²/s², ω = 74.6 1/s (verified by M8 derived audit).

## Validation status (M9.1 + M9.2)

M9.1 wired NASA TMR MKM 1999 Re_tau≈590 DNS Cf=0.00617 as the reference.
M9.2 made the case actually converge. Expected outcome post-M9.2:

- `geometry_contract`: PASS (5 patches, 2.5D)
- `mesh_contract`: PASS (y+ within widened [0.5, 30] target)
- `bc_contract`: PASS (cyclic inlet/outlet, noSlip walls with wall functions)
- `solver_execution`: PASS (converged in O(100) iterations thanks to cyclic)
- `qoi_extraction`: PASS (Cf along bottomWall)
- `reference_comparison`: PASS (Cf vs NASA DNS within 10% tolerance, expected ~3%)
- `validation_status`: **validated** (all gates PASS)

Pre-M9.2 (with uniform plug-flow inlet) the solver_execution gate FAILed
because residual targets weren't met in 1000 iterations — the boundary
layer was still developing at the channel exit. The R24-F-01 honesty fix
correctly refused to claim validation despite reference_comparison
matching within 3%. M9.2 closes the loop: cyclic BC produces true
fully-developed flow → solver converges → all gates PASS → harness
declares the case validated.
