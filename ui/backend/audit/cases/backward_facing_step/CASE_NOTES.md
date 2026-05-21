# CASE_NOTES — backward_facing_step

## Status

M2.1 scaffold (2026-05-21). Production-quality OpenFOAM dictionaries +
Driver-Seegmiller experimental Cf reference data shipped. **Honest gap**:
the case ships with the same coarse-mesh + high-Re wall-function strategy
as `flat_plate_rans_sst`; the harness is expected to FAIL the
reference_comparison gate on first live run. This is the M2 milestone's
explicit accepted state (M2 proves harness GENERALITY, not PASS).

## Geometry

Driver-Seegmiller backward-facing step (NASA TMR canonical validation
case).

- Step height **H = 0.0127 m** (0.5 inch, Driver-Seegmiller original)
- Upstream channel: x ∈ [−4H, 0], y ∈ [0, 9H]
- Downstream channel: x ∈ [0, 30H], y ∈ [−H, 9H]
- 2.5D extrusion: z ∈ [0, 0.5H], single cell in z, `empty` BC
- Re_H = U·H/ν = 44.2 × 0.0127 / 1.5e−5 ≈ 37 400 (target 36 000)
- Reattachment point (experimental): x/H ≈ 6.26 ± 0.10

## Patch Topology

- **inlet** (x = −4H): `fixedValue U=(44.2, 0, 0)`, zeroGradient p,
  turbulentIntensityKineticEnergyInlet k (I=1%), mixingLengthFrequency
  omega (L=0.1H)
- **outlet** (x = 30H): zeroGradient U, fixedValue p=0
- **bottomWall** (y=0 for x<0, y=−H for x>0): no-slip, kqRWallFunction k,
  omegaWallFunction omega, nutkWallFunction nut
- **stepFace** (x=0, y ∈ [−H, 0]): same as bottomWall (no-slip + WF)
- **topWall** (y=9H, all x): no-slip + wall functions
- **frontAndBack** (z=0 and z=0.5H): empty (2.5D)

Note: NASA TMR's experimental setup had the upper wall as no-slip with
its own boundary layer. Some CFD reference simulations approximate it as
symmetryPlane to simplify the BC mismatch with the experimental inlet
profile. The M2.1 scaffold uses no-slip top wall (matches experiment
more faithfully). If reattachment differs by >1 H from canonical,
revisit this choice.

## Mesh

3-block L-shape via `blockMesh`:

- B0 (upstream channel): 40 × 50 × 1 cells, y-grading 30 (refine to bottomWall)
- B1 (downstream upper channel): 120 × 50 × 1 cells, x-grading 4 (refine to step)
              + y-grading 30 (refine to top wall AND to the recirculation shear layer)
- B2 (downstream step zone): 120 × 30 × 1 cells, x-grading 4

Total: ~10 000 cells. Expected y+ on the bottomWall: similar to
flat_plate's ~52 (coarse mesh + high-Re wall function) — explicitly
acknowledged below as the M2.1 known gap.

## Known M2.1 gaps (carried as accepted state)

1. **y+ vs target window**: estimated y+ ≈ 30-60 on the bottomWall
   downstream of the step (manifest target 0.5-5). Same gap as
   `flat_plate_rans_sst > CASE_NOTES.md > R14-F-03`. The trust harness
   reports this gap via the (still-mocked) mesh_contract gate, and the
   reference_comparison gate quantifies the consequence.
2. **k-omega SST reattachment under-prediction**: SST is documented to
   under-predict reattachment by ~15-20% on BFS (Driver-Seegmiller).
   This is a turbulence-model limitation, NOT a harness bug. The 0.20
   tolerance on reference_comparison accommodates this.
3. **Top wall BL not from experimental profile**: NASA TMR's
   experimental inlet has a non-uniform BL profile; our scaffold uses
   uniform inlet. Affects upstream-of-step Cf comparison (x/H < 0). The
   x_min_compare_m = 0.0 setting drops upstream points from the gate.
4. **Scalar QoI not extracted**: `reattachment_length_xH` is declared in
   the manifest as a future QoI; M2 does NOT implement scalar QoI
   extraction (deferred to a later milestone).

## Re-running

```bash
# Mocked (Phase 0 default):
PYTHONPATH=src python -m cfdtrust.cli run cases/backward_facing_step

# Live (requires Docker + the OpenFOAM 11 image):
sed -i.bak 's/solver_backend: mocked/solver_backend: openfoam/' \
    cases/backward_facing_step/case_manifest.yaml
PYTHONPATH=src python -m cfdtrust.cli run cases/backward_facing_step
```

Expected outcome on a live run with this M2.1 scaffold: solver converges,
reference_comparison gate FAILs with ~20-50% max relative Cf error in
the recirculation region (-1 < x/H < 6.26). FAIL is the *correct* outcome
given the deliberately-coarse mesh + high-Re wall functions.
