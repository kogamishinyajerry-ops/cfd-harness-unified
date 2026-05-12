# Boundary condition basics

Every patch in `0/` needs a BC for each transported field (U, p, k, omega/epsilon, T...).
Picking the right BC pattern is upstream of solver convergence.

## Velocity inlet patterns

### fixedValue

Set a uniform or non-uniform velocity at the inlet. Pick when the
upstream velocity profile is known or assumed uniform.

### flowRateInletVelocity

Specify volumetric or mass flow rate; OpenFOAM derives the velocity
from patch area. Pick when the boundary is mass-balanced.

### turbulentInlet

fixedValue + perturbation for synthetic turbulence inflow. Pick when
LES inlet realism matters; not needed for RANS.

## Pressure outlet patterns

### fixedValue (p = 0)

Reference pressure at outlet. Most common steady-state outlet for
incompressible flow.

### inletOutlet

Allows reverse flow at outlet without divergence. Pick when wake
recirculation may push fluid back into the domain.

### totalPressure

Specifies total (stagnation) pressure; static pressure derived from
local velocity. Pick for inflow with known reservoir conditions.

## Wall patterns

### noSlip

U = 0 at wall. The default for solid walls.

### slip

Symmetry-like; tangential velocity unconstrained, normal = 0. Pick
for free surfaces or symmetry planes (note: `symmetryPlane` patch
type is more idiomatic for symmetry).

### movingWallVelocity

Wall moves at a specified velocity (e.g., lid-driven cavity). The
mesh stays static; only the BC value changes.

## Turbulence inlet conditions

For RANS, set k and omega (or epsilon) at inlets:

- **k_inlet** ≈ 1.5 * (U_ref * I)^2 where I is turbulence intensity (0.05 typical).
- **omega_inlet** ≈ k^(1/2) / (Cmu^(1/4) * L) where L is turbulence length scale.

Order-of-magnitude estimates are usually sufficient; the solver smooths
out inlet-region differences after a few diameters.

## Common pitfall: missing BC

If a patch has no entry in `0/U` or `0/p`, the solver crashes at startup
with `keyword X is undefined in dictionary`. The N4.1 BC contract
(DEC-V61-146) catches this before solver invocation.
