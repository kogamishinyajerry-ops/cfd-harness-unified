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

**Empirical validation (real simpleFoam + kΩSST, OF11, DEC-V61-209 cycle-3g, HONEST FAIL)**:
The case uses **NASA TMR topology**: a leading **symmetry** section [-0.333, 0] then the
no-slip **plate** [0, 2], y+ ≈ 1.3 avg, converged at iter 394 (all 5 residuals ≤ 1e-5),
NASA SST **freestream turbulence** (Tu=0.039%, mu_t/mu=0.009). Real Cf(x) vs NASA TMR
CFL3D SST, with NASA's documented **x < 0.01** LE exclusion (NOT a tuned cutoff):
- `overall_status: FAIL`, `validation_status: not_validated` (honest).
- **4 near-LE points fail**: 0.0129 ≤ x ≤ 0.0232, worst **21.2%** at x=0.0129.
- **171 / 175 points pass**; mid plate (x ≈ 0.05–0.2) 3–6%; developed (x ≥ 0.2) **~1.5%**.

The 10% `reference_comparison.tolerance` stands, justified by genuine discretization
uncertainty (not a hidden Reynolds offset).

## Comparison region

Skip-window: `x_min_compare_m = 0.01` — **NASA TMR's own documented LE exclusion** (TMR
notes local anomalous SST activation in `0 < x < 0.01`). The comparator drops points
with `x < 0.01 m` from both curves before computing per-point error.

**Honesty note (DEC-V61-209 cycle-3e→3g):** an interim attempt raised this to `0.03` to
clear the residual near-LE failures. That was **reverted** as post-hoc gate movement
(Codex review, RATIONALIZED): the failures persisted to x≈0.027, and moving the cutoff
to exactly past them was masking, not scoping. NASA's documented exclusion is `0.01`,
and that is what stands.

**What the near-LE band is (causal evidence, not a justification to exclude it):**
the 0.01 < x < 0.027 over-prediction survives every correct-setup fix, so it is a
near-LE OpenFOAM-kΩSST-vs-CFL3D formulation discrepancy (TMR's `openfoam_issues` page
documents OpenFOAM SST historically not matching CFL3D's SST equations), NOT a fixable
setup error:

| cycle | change | near-LE error @ x≈0.0128 | failing band |
|---|---|---|---|
| 3c | plate-only (LE on inlet)        | 26.5% | x ≤ 0.035 |
| 3e | + NASA symmetry pre-plate       | 21.8% | x ≤ 0.027 |
| 3f | + 4× LE x-refinement (180→260)  | 21.6% (grid-converged) | x ≤ 0.027 |
| 3g | + NASA freestream turbulence    | 21.2% | x ≤ 0.023 |

The pre-plate fixed a non-convergence and shrank the band; grid refinement did not move
the fixed-location error (so it is not discretization); NASA-exact freestream barely
moved it (so it is not the inlet turbulence). The residual is intrinsic to the
solver-vs-reference near the LE. **It is reported honestly as a FAIL, not excluded.**
Whether the workbench's flat-plate gate should remain per-point-from-x=0.01 (strict) or
adopt NASA's own convention (integrated drag + downstream Cf at x=0.97) is a V&V-gate
methodology decision for the sponsor — see DEC-V61-209 ADDENDUM 3.

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
