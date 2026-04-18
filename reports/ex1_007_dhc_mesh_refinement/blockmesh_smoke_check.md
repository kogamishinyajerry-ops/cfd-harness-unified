# EX-1-007 B1 Post-Commit blockMesh Smoke Check

## Purpose
Verify the new DHC simpleGrading multi-section syntax before committing to the
long-running (30-120 min) solver measurement.

## Run 1 — initial commit 54b57ab (grading direction wrong)

### Configuration
```
simpleGrading (((0.5 0.5 0.1667) (0.5 0.5 6)) ((0.5 0.5 0.1667) (0.5 0.5 6)) 1)
```

### Mesh Stats
- Cell size range (Block 0 i): `0.00838149 .. 0.00838209`
- Min volume: 1.95e-7 m³ → ~1.4mm cell at **midline**
- Max volume: 7.03e-6 m³ → ~8.4mm cell at **walls**
- Max aspect ratio: 6

### Verdict
**PHYSICS-DIRECTION BUG.** Expansion semantics:
- Section 1 (x ∈ [0, 0.5], expansion=1/6): last_cell/first_cell = 1/6 → first cell is BIG
  at wall x=0, small near midline.
- Section 2 (x ∈ [0.5, 1], expansion=6): first cell small near midline, big at cold wall.

Net effect: fine cells clustered at **bulk flow midline**, coarse cells at walls.
Opposite of wall-packing. Thermal BL (δ_T ≈ 3.16mm at Ra=1e10) would be
unresolved — 8.4mm wall cell is **coarser than the uniform 80-cell baseline**
(12.5mm) by only 33%, and the fine cells are wasted where gradients are weak.

Expected Nu under this broken grading: likely **worse than 80-uniform baseline
(5.85)**, not better. The C5 a priori prediction (16.1 ± 5) was based on 1.3mm
first-cell at the walls.

## Run 2 — fix commit (grading direction corrected)

### Configuration
```
simpleGrading (((0.5 0.5 6) (0.5 0.5 0.1667)) ((0.5 0.5 6) (0.5 0.5 0.1667)) 1)
```

### Mesh Stats
- Cell size range (Block 0 i): `0.00139701 .. 0.00139719`
- Min volume: 1.95e-7 m³ → ~1.4mm cell at **walls** ✓
- Max volume: 7.03e-6 m³ → ~8.4mm cell at **midline** ✓
- Max aspect ratio: 6

### Verdict
**PHYSICS-DIRECTION CORRECT.** Section 1 expansion=6 means first cell small at
wall x=0; Section 2 expansion=1/6 means last cell small at cold wall. Midline
cells are coarse (bulk flow, weak gradients).

Observed first-cell 1.40mm at both walls:
- cells_in_BL(δ_T=3.162mm) ≈ 3.162/1.40 ≈ **2.26 cells in BL** ✓ (C5 target: ~2)
- Matches the C5 a priori Nu prediction premise.

## Why blockMesh Ran Both Configurations Silently

Multi-section simpleGrading is accepted by OpenFOAM v10 parser for both orderings;
the direction is purely a physics choice the author must verify. checkMesh
reports Max aspect ratio = 6 for both, so only the min/max cell-location
(near wall vs near midline) distinguishes them — invisible to generic mesh checks.

## Lesson (captured as D4+ rule candidate)

For any simpleGrading multi-section change on a case with a known-good
baseline Nu (or equivalent wall-gradient observable), **run blockMesh smoke-check
and inspect min-volume location before committing the solver run**. The cost
is ~5s vs a 30-120 min wasted solver trajectory.

Proposed rule: `rule_6_mesh_refinement_wall_packing_smoke_check: MANDATORY
when simpleGrading changes from uniform on a wall-bounded BL observable`.

## Artifacts
- Smoke-check script: `reports/ex1_007_dhc_mesh_refinement/run_dhc_blockmesh_check.py`
- Fix applied: `src/foam_agent_adapter.py::_generate_natural_convection_cavity` L1317-L1325

Produced: 2026-04-18 (between commits 54b57ab and the fix-up commit).
Reviewer: opus47-main (self-Gate).
