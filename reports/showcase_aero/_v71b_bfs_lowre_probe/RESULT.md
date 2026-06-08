# V71.B · low-Re k-omega-SST backward-facing-step (Re=5000, wall-RESOLVED) — frozen LIVE probe

**Status**: LIVE_VALIDATED (DEC-V61-235). This is the frozen evidence the
`backward_facing_step_lowre` gold + gate LAG (anti-fraud charter §6 — the registration
follows working, tested code). The case is NOT whitelisted in this V&V slice (Codex R1
P1): a selectable entry without live wiring would be exposed-but-unverifiable; the
whitelist entry + live `execute()`/TaskRunner wiring are deferred to V71B-FOLLOWUP-1
(the wedge precedent — whitelist landed in the wiring slice DEC-V61-234, not the V&V
slice 233). The case_definition here IS adapter-generated; it was solved by a fresh
container, NOT yet through `execute()`.

## What this anchors

`backward_facing_step` at **Re_H=5000** with **k-omega-SST integrated to the wall**
(wall-RESOLVED, **first-cell y+<1 on the reattachment floor**) — the low-Re
turbulence-MODELING regime (integrate-to-wall, NOT a low Reynolds number).
Distinguished from the high-Re sibling (Re=7600, Spalding wall function, first-cell
y+≈5) purely by the **resolved near-wall mesh** (y-grading + ncy; x-grading/ncx
unchanged). **Same incompressible-RANS compute type — runnable-coverage STAYS 3**;
this is a turbulence-TREATMENT breadth anchor.

## Provenance (the honest "runnable through the adapter" claim)

The `case_definition/` here is **adapter-generated**: `foam_agent_adapter`
`_generate_backward_facing_step` with `boundary_conditions.wall_treatment='resolved'`
(12320-cell graded mesh). It was solved by a fresh `docker run` OF11
(`openfoam/openfoam11-paraview510`) — `blockMesh` (checkMesh OK) + `foamRun -solver
incompressibleFluid` to t=3000 + `foamToVTK -latestTime -allPatches` — disturbing no
running container. The gate (`src.bfs_lowre_gate.gate_bfs_lowre_against_gold`) reads
THESE artifacts.

## Measured result (live solve, OF11, ~90 s to t=3000)

| Metric | Value | Bar | Verdict |
|---|---|---|---|
| reattachment **Xr/H** (wall-shear tau_x zero-crossing) | **5.881** | 6.26 ±10% → [5.634, 6.886] | **PASS** (−6.05% vs 6.26; −6.35% vs DNS 6.28 — both inside) |
| first-cell **y+** max, reattachment floor (119 faces, y<0.05 ∧ 0.05<x<29.5) | **0.066** | < 1 (resolved) | **PASS** |
| wall-shear pos→neg crossings on floor | 1 | == 1 (single clean reattachment) | **PASS** |
| mesh | 12 320 cells | checkMesh "Mesh OK" | PASS |

## Honest framing (no over-tuning)

- **Anchor = Xr/H 6.26**, the **blended engineering anchor INHERITED** from the
  high-Re BFS gold (DEC-V61-046): Le/Moin/Kim 1997 DNS @ Re_H=5100 = 6.28; Driver &
  Seegmiller 1985 = 6.26; the 0.32% spread is inside the 10% band. The anchor is
  NOT re-shopped per slice; tolerance 0.10 is UNCHANGED.
- **Reattachment is the wall-shear tau_x zero-crossing** (the physical definition,
  the established Path-1a method) — NOT a fixed-height U_x proxy. On the high-Re
  mesh a y=0.02 U_x probe sits in the first cell and agrees with wall-shear to the
  4th digit; on the **resolved** mesh y=0.02 is ~15-20 cells up, so the U_x proxy
  is grid-height-biased (it reads 5.43→5.88 as the probe height→wall, converging
  to the wall-shear value). Confirmed by re-running the high-Re case through the
  identical pipeline: wall-shear Xr/H=5.647, matching this gold's documented 5.647.
- **Value added by resolving the BL**: the resolved mesh moves the MEASURED
  reattachment from the high-Re 5.647 (−9.8%) to **5.881 (−6.05%)** — CLOSER to the
  anchor. The ~6% residual is the documented kOmegaSST separated-flow
  under-prediction (V104), **reported, not tuned away**. This is the
  low-Re-capability the `low_re_komegasst_trigger` advisor flags.
- **The y+<1 claim is MACHINE-ENFORCED**, not attested: the gate hard-gates
  `max(yPlus) < 1` over the SAME floor faces the reattachment QoI uses (shared mask
  `src.bfs_floor_region`). The high-Re mesh measures ~4.22 here and would correctly
  FAIL. The sharp step corner (y+~3.4, geometric singularity) and the attached
  upper wall (y+~200) are wall-functioned and disclosed — both are OUTSIDE the
  floor mask, so neither is read by the gate.

## Files

- `case_definition/` — adapter-generated case (0/, constant/, system/).
- `VTK/allPatches/allPatches_3000.vtk` — the solver-derived source (wallShearStress
  + yPlus co-located on the lower_wall faces).
- `proof/floor_faces.csv` — per-face `(x, y, yplus, tau_x)` for the masked floor,
  derived ONCE from the VTK via the shared mask; the stdlib gate-replay input.
- `logs/` — blockMesh (12320 cells), checkMesh tail (Mesh OK), foamRun head+tail.
