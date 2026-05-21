# Reference data provenance — backward_facing_step

## Source

NASA Turbulence Modeling Resource (TMR), 2D backward-facing step validation case — **Driver-Seegmiller experimental Cf along the bottom wall**.

- Published URL: https://tmbwg.github.io/turbmodels/backstep_val.html
- Direct data file: https://tmbwg.github.io/turbmodels/Backstep_validation/cf.exp.dat
- Original SHA-256 of `cf.exp.dat`: `cd9b6434b7956bc58e859de6af654cd7f891e25303babf1dd8633d6c58f74276`
- Fetch timestamp: 2026-05-21T02:40Z
- Primary citation: Driver, D. M. and Seegmiller, H. L. (1985), "Features of a Reattaching Turbulent Shear Layer in Divergent Channel Flow," AIAA Journal, Vol. 23, No. 2, pp. 163-171
- License: Experimental data published openly by NASA under their TMR project; no restrictions on use, modification, or redistribution.

## What we kept

The raw NASA file has 3 columns (x/H, Cf, measurement error). The harness compares **x_m vs Cf** so we drop the error column and convert x/H → x_m by multiplying by step height H = 0.0127 m:

- Format: 2-column CSV with header `x_m,Cf`, sorted by `x_m`
- 20 rows from upstream (x/H = -3.956 → x_m = -0.050) to far downstream (x/H = 35.994 → x_m = 0.457)
- Reattachment from Driver-Seegmiller: x/H = 6.26 ± 0.10 (canonical metric)
- Cf goes NEGATIVE in the recirculation region (-0.804 < x/H < ~6.26) — this is real reverse-flow stress, not a sign convention bug

## Canonical case conditions (NASA TMR)

- Step height **H = 0.0127 m** (0.5 inch)
- Free-stream Mach **M ≈ 0.128** upstream of step (incompressible-OK)
- Reynolds **Re_H ≈ 36 000**
- Boundary-layer thickness pre-step **δ ≈ 1.5H**

## Local case conditions vs reference

Our `case_manifest.yaml`:

- H = 0.0127 m (matches NASA exactly)
- U_∞ = 44.2 m/s
- ν = 1.5e-5 m²/s
- Re_H = 44.2 × 0.0127 / 1.5e-5 ≈ **37 400** (NASA target 36 000; +4% offset)

The Re_H offset is small enough that no tolerance widening was needed beyond what we already pay for the SST-model reattachment-length under-prediction (~15-20% per published literature).

## Comparison region

Default `x_min_compare_m = 0.0` skips upstream-of-step points (x_m < 0). NASA's data covers both regions, but our scaffold uses a uniform-profile inlet BC (not the experimental BL profile NASA provides), so upstream-of-step Cf comparison would be misleading. Downstream-of-step is where the BFS physics lives anyway.

## Verifying this dataset

Regenerate from source:

```bash
curl -sL https://tmbwg.github.io/turbmodels/Backstep_validation/cf.exp.dat -o /tmp/bfs.dat
shasum -a 256 /tmp/bfs.dat
# expect: cd9b6434b7956bc58e859de6af654cd7f891e25303babf1dd8633d6c58f74276
```

Then re-run the extraction script from PROGRESS.md sub-commit M2.2 entry.

## Why x in meters not x/H

Project-wide convention (set by the flat_plate case): every `cf_reference.csv` carries `x_m,Cf` columns. Consistent with `qoi.csv` from the wallShearStress extractor. The x/H normalization is a domain convention; the harness operates on physical units to stay agnostic across case families.

## Updating this dataset

- If NASA TMR republishes Driver-Seegmiller with revised values: bump `source_sha256` AND `reference_csv_sha256`, regenerate from source, document the delta here with date.
- If the local case manifest changes Re_H: revise "Local case conditions" above and reconsider whether to revise the tolerance.
- Do not silently swap the reference; every change cited here with a date.
