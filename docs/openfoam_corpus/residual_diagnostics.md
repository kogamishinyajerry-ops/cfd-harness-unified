# Residual diagnostics

The solver log records initial and final residuals per timestep / outer
iteration. Reading these is the first step in any diagnosis.

## Reading the log

Each iteration prints lines like:

    smoothSolver:  Solving for Ux, Initial residual = 1.2e-3, Final residual = 4.5e-7

- **Initial residual**: error at the start of this iteration.
- **Final residual**: error after the linear solve.
- **No. Iterations**: how many smoother sweeps.

The initial residual is the convergence indicator. A run is converged
when initial residuals reach a low plateau (typically 1e-4 to 1e-6 for
incompressible RANS).

## Interpretation patterns

### Stalled residuals

Initial residuals plateau above target (e.g., 1e-2). Causes:

- BC mismatch (over-constrained system; check patch list).
- Bad mesh (high non-orthogonality, inverted cells).
- Insufficient relaxation (PIMPLE outer loops too few).

The N5.2 issue list emits `output_residuals_stalled` when this is detected.

### Oscillating residuals

Initial residuals bounce between two values without trending. Causes:

- URFs too tight (see under_relaxation_factors.md).
- Vortex shedding or other transient unsteadiness in a "steady" run
  (use pimpleFoam instead).

### Diverging residuals

Initial residuals grow exponentially. Causes:

- Negative cell volumes (run checkMesh).
- BC inconsistency (e.g., total flow rate mismatched between inlets and outlets).
- Time step too large (Co > 1 in transient; reduce `deltaT`).

### Healthy convergence

Initial residuals decrease ~1 order per 100-500 iterations and reach
target within `endTime`. This is the green-flag pattern.

## Audit policy

The N5.1 beginner report includes a "verdict" derived from final
residuals + N5.2 issue list. A verdict of `physics_setup_incomplete`
means residuals never decreased; `has_open_issues` means residuals
plateaued above target.
