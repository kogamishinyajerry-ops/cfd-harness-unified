# Under-relaxation factors (URF) guidance

URFs damp the change-per-iteration in pressure-velocity coupling.
Tighter URFs (closer to 1.0) iterate faster but risk divergence;
looser URFs (closer to 0.3) are more stable but slow to converge.

## SIMPLE solver defaults

For `simpleFoam` (steady, RANS):

- **p (pressure)**: 0.3 — most-relaxed because p is solved first and
  feeds back into U.
- **U (momentum)**: 0.7
- **k, omega/epsilon**: 0.7

These defaults work for most cases. Loosen p further (0.2) if
residuals oscillate. Tighten U to 0.8-0.9 if convergence stalls.

## PISO / PIMPLE differences

For transient PISO (`icoFoam`), URFs are usually 1.0 — PISO
self-relaxes through the corrector loop. PIMPLE (`pimpleFoam`) uses
SIMPLE-like URFs in the outer loop, then PISO-like 1.0 in correctors.

## Symptoms vs adjustments

### Residuals oscillate at constant amplitude

Cause: URFs too tight. Mitigation: drop p to 0.2, U to 0.6.

### Residuals decrease but never reach target

Cause: URFs too loose, not enough iterations. Mitigation: increase
`endTime` or tighten URFs.

### Diverging (residuals increasing exponentially)

Cause: physics setup issue, not URF. Mitigation: check BC patches,
turbulence inlet conditions, mesh quality. URF tweaks rarely save
a divergent case.

## Audit policy

The N4.3 URF advisor (DEC-V61-148) emits an `info` hint when URFs
deviate from textbook ranges; the engineer is expected to confirm
the deviation is intentional.
