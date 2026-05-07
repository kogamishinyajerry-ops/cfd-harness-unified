# Solver selection guide

OpenFOAM ships many incompressible solvers. Pick by physics regime,
not by familiarity.

## simpleFoam

Steady-state, single-phase, incompressible, turbulent. Uses SIMPLE
algorithm. Pick when:

- Final state is what matters (no transient features of interest).
- Geometry has fully-developed flow zones.
- Pressure-velocity coupling can be solved iteratively.

Common with: external aero, HVAC ducting, valve sizing.

## icoFoam

Transient, single-phase, incompressible, **laminar** only. PISO
algorithm. Pick when:

- Flow is laminar (Re < ~2300 in ducts, lower in 3D bluff-body wakes).
- Need transient evolution (vortex shedding, startup transients).
- Mesh is fine enough for resolved unsteadiness.

Switch to `pimpleFoam` if RANS turbulence is needed transiently.

## pimpleFoam

Transient, single-phase, incompressible, RANS or LES. PIMPLE = PISO +
SIMPLE outer loop. Pick when:

- Transient + turbulent.
- Larger time steps acceptable (PIMPLE allows Co > 1).
- Boundary-driven instabilities matter (rotating machinery, transient
  heat transfer).

## interFoam (out of N6 scope)

Multiphase VOF. N6 advisor does not currently cover multiphase setups.

## Choosing between simpleFoam and pimpleFoam

For RANS turbulence with a steady mean flow, prefer `simpleFoam`. It
converges faster and produces the same time-averaged result. Use
`pimpleFoam` only when transient features matter (vortex shedding
frequency, startup behavior).
