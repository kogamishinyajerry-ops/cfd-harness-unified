# Reference data — flat_plate_rans_sst

## Status

**Phase 0 placeholder. Reference data is NOT finalized.**

No claim of validation is made by this case in Phase 0.

## Plan

In Phase 1 we will adopt a canonical published reference for the flat-plate
k-omega SST verification case. Candidates:

- NASA TMR (Turbulence Modeling Resource) flat plate, Mach 0.2 reference
- Wieghardt flat plate experimental data
- Equivalent published SST reference

Whichever is selected, the reference data and its license must be stored under
this directory, and `case_manifest.yaml > reference_comparison.status` must
move from `placeholder` to `finalized`.

## What lives here later

- `reference_cf.csv` — published skin-friction distribution
- `reference_drag.csv` — published drag values (if applicable)
- `provenance.md` — exact source, citation, license terms
