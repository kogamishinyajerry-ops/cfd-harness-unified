# Reference data provenance — flat_plate_rans_sst

## Source

NASA Turbulence Modeling Resource (TMR), 2D flat plate verification case, SST turbulence model — **CFL3D solution**.

- Published URL (mirror): https://tmbwg.github.io/turbmodels/flatplate_sst.html
- Direct data file: https://tmbwg.github.io/turbmodels/FlatPlate/SST/cf_plate_sstv.dat
- Original source: NASA Langley Research Center, TMR project
- Original SHA-256 of `cf_plate_sstv.dat`: `a56bd2d16818456af015b13839f0a991b4b85bfa6c18242e7c331a2c7a4d40e8`
- Fetch timestamp: 2026-05-21T18:00Z
- License: U.S. Government work (NASA), public domain in the United States. No restrictions on use, modification, or redistribution.

## What we kept

Only the **CFL3D zone** of the published file (the file also contains a FUN3D zone; both are valid SST solutions but slightly differ due to discretization). CFL3D is the canonical TMR reference per the NASA TMR documentation.

Only **on-plate points** (`x ≥ 0`). The original file extends to `x = -0.32` upstream of the leading edge where Cf is identically zero (no plate exists there). Keeping those rows adds noise without adding information.

Format: 2-column CSV with header `x_m,Cf`. 448 rows.

## Canonical case conditions (NASA TMR)

- Plate length L = 2.0 m
- Free-stream velocity U∞ giving Re_L = 5×10⁶
- Standard sea-level air properties

## Local case conditions vs reference

Our `case_manifest.yaml` (UPDATED 2026-05-27, DEC-V61-209 — Re now matched):

- Plate length L = 2.0 m (matches NASA)
- Free-stream velocity U∞ = 30 m/s
- Kinematic viscosity ν = **6×10⁻⁶ m²/s** (was 1.5×10⁻⁵)
- Re per unit length = U/ν = 30 / 6×10⁻⁶ = **5×10⁶ = NASA TMR canonical Re** (exact match)

**Re now matches the reference.** The prior ν=1.5×10⁻⁵ (Re/L=2×10⁶) gave a real
Cf error of **15–17%** vs the NASA Re=5×10⁶ curve — far worse than the "~5% delta"
the earlier note predicted. Widening tolerance to absorb a Reynolds mismatch was the
wrong fix; matching the reference Re is the honest one.

**Empirical validation (real simpleFoam + kΩSST run, OF10, DEC-V61-209)**:
- **Developed turbulent region (x ≥ 0.2 m): worst Cf error 2.4%** vs NASA TMR CFL3D
  SST — comfortably inside the 10% gate.
- **Near-leading-edge band (x ≈ 0.05–0.15 m): 10–14.5%** — NOT a Reynolds or model
  error but **mesh under-resolution**: the current blockMesh gives y+ ≈ 120
  (wall-function regime), while `case_manifest.yaml > mesh_contract.wall_function_policy`
  declares `low_re_resolved` (y+ ~ 1). The thin near-LE boundary layer needs the
  y+~1 mesh the case already declares; the thick developed-region BL tolerates y+~120.
  **Resolution (queued)**: refine near-wall grading to y+~1 (matches the declared
  policy and NASA's resolved mesh) → expected to bring the full x≥0.01 region inside gate.

The 10% `reference_comparison.tolerance` stands, now justified by genuine
discretization uncertainty (not a hidden Reynolds offset).

## Comparison region

Skip-window: `x < 0.01 m`. The first 1 cm of the plate covers the laminar-to-turbulent transition region where the simulation's RANS k-ω SST model is known to be off — and where NASA's CFL3D solution shows a spike from `Cf ≈ 0.015` at x=0 to `Cf ≈ 0.006` at x=0.005, a 3× swing in 5 mm that no manifest-level tolerance would meaningfully describe. The trust comparator drops points with `x < 0.01 m` from both curves before computing per-point error.

## Verifying this dataset

Regenerate from source:

```bash
# Re-fetch source
curl -L -o /tmp/cf_plate_sstv.dat https://tmbwg.github.io/turbmodels/FlatPlate/SST/cf_plate_sstv.dat
shasum -a 256 /tmp/cf_plate_sstv.dat  # must equal the SHA-256 above
```

Then re-run the extraction script (see PROGRESS.md sub-commit 2d entry).

## Updating this dataset

- If NASA TMR publishes a revised SST solution: bump the SHA-256, re-extract, document the delta in this file, and re-run `cfdtrust run` on `flat_plate_rans_sst` to see if the gate flips.
- If the local case manifest changes Re_L: revise the "Local case conditions vs reference" section above and reconsider the tolerance.
- Do not silently swap the reference; every change must be cited here with a date.
