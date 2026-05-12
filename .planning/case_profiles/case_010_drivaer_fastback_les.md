# Case 010 · DrivAer Fastback LES · pimpleFoam thread (Industrial Reference)

> **NOT a gold-standard case.** No automated benchmark verdict.
> **Industrial reference** — proof artifact + V-series finding source.
>
> Established by DEC-V61-198 (APU bay strategic pivot, 2026-05-07) as the
> **first transient LES** case in the project's case fleet. Fills the
> **incompressible-LES** row of the solver-class coverage map.
> Per Pattern 6, case_010 is the **root for incompressible-LES**: inherits NO
> V-findings from any prior case (V3-V42 cover compressible-buoyant-RANS,
> incompressible-RANS, MRF, compressible-RANS, compressible-shock-density-
> based, multiphase-VOF, incompressible-RANS-Lagrangian, reacting-low-Mach —
> none are LES). **Final case in the 10-case roster.** After case_010 v1
> sediment lands, all 10 numerics-class roots are covered.

## What this entry is

A real industrial-flavored CFD case with a Tier-1 reference geometry (TUM
DrivAer fastback `F_S_wM_wW`, half-vehicle external aerodynamics) regenerated
parametrically by Codex's CAD design (per
`.planning/methodology/codex_case_design_protocol.md`). The case-thread
sandbox at `~/Desktop/case_010_drivaer_fastback_les/` ran v1 end-to-end
through scaffold + CAD + advisor exercises + LES templates + initial
mesh and surfaced **3 net-new V-findings (V43-V45)** plus reinforced
V37 thin_wall_advisor `[VALIDATED]` to a **7-topology arc** and the
A2 `_run_shared` cross-topology arc to **7-of-7**.

## What this entry is for

Three orthogonal uses (parallel to case_002a / case_005 / case_006 / case_009):

1. **Proof artifact**: workbench can drive an industrial transient LES
   case through CAD → blockMesh half-domain → snappyHexMesh refinement near
   vehicle body → LES infrastructure (WALE + nutUSpaldingWallFunction +
   cubeRootVol filter + forceCoeffs + fieldAverage + Q + Lambda2 +
   yPlus FOs) → pimpleFoam two-stage transient (settling + averaging).
   v1 baseline runs scaffold + advisor exercises + dicts + bg-mesh + sHM
   end-to-end (full transient solver run deferred to v2/v3 per Codex
   effort estimate of 10-14h × 3-4 versions). Hand-coded LES schemes
   writer, LES turbulenceProperties writer, wall-function writer (LES
   variant, no nuTilda/k/omega), field-average function-object writer,
   Q-criterion post-processor stub — none existed in the main project
   before case_010. **4 artifact extraction candidates** identified.

2. **V-series finding source**: 3 net-new findings spanning LES-specific
   infrastructure (V45: WALE + nutUSpaldingWallFunction + cubeRootVol
   filter + LES function-object trio; transient half-domain pimpleFoam
   never seen before in project) and advisor consistency (V43: A2 `_run_shared`
   cross-topology PASS on vehicle-aero side-mirror trim — 7th algorithm-
   path PASS, [QUESTIONABLE] per V25 chain; V44: thin_wall_advisor
   7th cross-topology PASS reinforces V37 `[VALIDATED]`). All
   documented in `industrial_case_solver_findings.md`.

3. **First transient LES case** in the project. Establishes patterns for
   wall-modeled LES at y+=30-100 + cubeRootVol-filter LES models +
   two-stage transient/averaging restart workflow + Q/λ2 wake-topology
   post-processing that all future LES cases (DES, hybrid LES-RANS, LES-CHT)
   will inherit.

## Pointer

Sub-session sandbox: `~/Desktop/case_010_drivaer_fastback_les/`
- `evidence/v1/REPORT.md` — full v1 sediment report (scope, findings, deferred items, artifact extraction candidates, license caveat)
- `evidence/v1/step_validation.json` — STEP geometry validation (12/12 parts, D1 0.350 mm gap, D8 0.80 mm dz, all PASS via analytical re-derivation)
- `evidence/v1/a2_d1_falsification.json` — A2 `_run_shared` PASS on side-mirror trim, [QUESTIONABLE] per V25
- `evidence/v1/thin_wall_d8_falsification.json` — 3 refinement-level scenarios all `severity=critical`, recommended_level_max=9
- `evidence/v1/check_mesh_summary.json` — bg mesh 4.644M cells, max_skewness 3e-13
- `inputs/cad_codex_v1.step` — 12 named bodies, 0.39 MB, byte-stable header

Reference dataset:
- TUM DrivAer overview: https://www.epc.ed.tum.de/en/aer/research-groups/automotive/drivaer/
- TUM geometry taxonomy: https://www.epc.ed.tum.de/en/aer/research-groups/automotive/drivaer/geometry/
- Heft, Indinger, Adams, *Introduction of a New Realistic Generic Car Model for Aerodynamic Investigations*, SAE 2012-01-0168
- Fastback LES dimensions/Re reference: https://www.mdpi.com/2311-5521/7/1/19/xml
- Target: time-averaged Cd ≈ 0.281 (configuration-dependent; compare only after matching half-domain, fixed-ground, stationary-wheel v1 assumptions)

## Configuration summary

- L = 4.61 m, W = 1.76 m, H = 1.42 m, wheelbase = 2.79 m
- Half-vehicle (centerline symmetry plane), smooth underbody, mirrors `wM`, stationary wheels `wW`
- U_inf = 16 m/s, Re_L = 4.87e6, Mach ≈ 0.05 (incompressible)
- Solver v1: `pimpleFoam` + WALE LES + `nutUSpaldingWallFunction`
- v2 fallback: `dynamicKEqn` LES OR `pisoFoam` if PIMPLE under-converges
- y+ target 30-100 (wall-modeled, NOT wall-resolved)
- dt = 1e-4 s (CFL ≤ 1, adjustableTimeStep, maxCo=1)
- Averaging window: settle 0 → 0.576 s (= 2 L/U_inf), accumulate 0.576 → 2.017 s (≥ 5 L/U_inf)
- Defects (both outside protected validation zones):
  - D1: 0.35 mm gap between `side_mirror_outboard` and `mirror_edge_trim_strip` at outboard trailing edge of mirror housing
  - D8: 0.80 mm thick `underbody_sensor_cover_thin` between axles, away from wheel housings + rear wake plane

## Coverage matrix completion

After case_010 v1 sediment lands, the project's 10-case roster covers all
10 numerics-class roots. Workhorse OpenFOAM solver matrix complete:

| # | Numerics class | Anchor case |
|---|---|---|
| 1 | compressible-buoyant-RANS | case_002a |
| 2 | + CHT extension | case_002b |
| 3 | incompressible-RANS external | case_003 |
| 4 | incompressible-RANS-MRF | case_004 |
| 5 | compressible-RANS internal | case_005 |
| 6 | compressible-shock-density-based | case_006 |
| 7 | multiphase-VOF | case_007 |
| 8 | incompressible-RANS-Lagrangian | case_008 |
| 9 | reacting-low-Mach | case_009 |
| 10 | **incompressible-LES** | **case_010** |

Future cases extend combinations (LES+CHT, reacting-LES, compressible-LES,
hybrid LES-RANS) but each numerics root has at least one anchor case.

## License caveat

TUM provides DrivAer STEP/IGES/STL after registration. The CAD generator
in `scripts/build_cad.py` produces a deterministic CadQuery reconstruction
from public TUM dimensions and the published Heft/Indinger/Adams 2012 SAE
paper — **NOT** a redistribution of the TUM binary. The generated STEP at
`inputs/cad_codex_v1.step` is **NOT for external redistribution** without
TUM registration verification (per case_007 KCS license-caveat pattern +
kickoff hard guardrail #8).
