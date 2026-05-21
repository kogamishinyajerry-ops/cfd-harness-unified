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

Our `case_manifest.yaml`:

- Plate length L = 2.0 m (matches NASA)
- Free-stream velocity U∞ = 30 m/s
- Kinematic viscosity ν = 1.5×10⁻⁵ m²/s
- Re_L = 30 × 2.0 / 1.5×10⁻⁵ = **4×10⁶** (NASA = 5×10⁶)

**This is a documented Re_L mismatch of 25%.** A turbulent boundary-layer Cf scales approximately as `Re_x^(-1/5)`, so the same x position carries a slightly higher Cf in our run than in NASA's. Predicted Cf delta at matching x: ~5%.

**Implication for the gate**: `reference_comparison.tolerance` is set to **0.10** (10%), wider than the QoI-stability tolerance of 0.05, to accommodate this known Re_L mismatch. The gate is honest about what it's checking: it answers "is our Cf curve close to NASA's published CFL3D SST curve at the same x positions?" — not "is our case at exactly the same Reynolds number." A future case profile with U∞ = 37.5 m/s would match Re_L exactly and could tighten the tolerance.

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
