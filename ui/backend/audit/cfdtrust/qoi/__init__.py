"""QoI extraction + reference comparison — pure functions.

Sub-commit 2d: this package owns the data plumbing between OpenFOAM output
and the trust harness's `reference_comparison.csv` artifact. All functions
here are intentionally pure (no I/O outside the function itself, no docker
calls) so each one can be unit-tested with synthetic fixtures and so the
audit layer can compose them safely.

Modules:
  - `flat_plate_cf` — NASA TMR reference loading + per-x comparison logic
                       for the flat-plate-canonical Cf curve.
  - `wall_shear` — OpenFOAM `<time>/wallShearStress` + `constant/polyMesh/*`
                     parser → per-x wall shear stress on a named patch.
"""
