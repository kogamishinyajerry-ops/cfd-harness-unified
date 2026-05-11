# case_016 · M219 Weapons-Bay Cavity · Transient Compressible IDDES + FW-H

> **Phase 3 #2** — first aeroacoustics root (compressible-DES-acoustic).
> Sandbox: `~/Desktop/case_016_m219_cavity_des_acoustic/`
> Codex brief: `.planning/methodology/kickoff/case_016_codex_response.md`
> (validated PASS 2026-05-08, R1 single-round emit, math correction caught)
> Sub-session executed: 2026-05-11

## Bank ID
`E4_m219_weapons_bay_cavity` (Tier-1 reference-derived; baked into
`scripts/build_cad.py` per case_006 V32-resilience pattern)

## Solver class
`rhoPimpleFoam + kOmegaSSTIDDES` · transient compressible · `transonic yes`

## Numerics class
`compressible-DES-acoustic` (NEW — first case at this anchor)

## Inheritance ancestry
- **case_006 V26-V32** (compressible-shock-density, ONERA M6 transonic):
  - V26 (CAD off-by-half-width) mitigated: `make_box` here is explicit min/max
  - V27 (rhoCentralFoam fixed deltaT) N/A — we use rhoPimpleFoam + adjustTimeStep
  - V28 (DILU on symmetric) → see V53 (inverse: DIC on asymmetric, this case)
  - V29 (foam-extend BC names) mitigated: `waveTransmissive` + `freestream*` only
  - V30 (extreme thinness) N/A
  - V31 (advisor mapping wrong) → see V52 (turbulence-block-registry, similar class)
  - V32 (Tier-1 fetch failures) mitigated: bake CAD into script
- **case_010 V45-V46** (incompressible-LES, DrivAer):
  - V45 (transient infrastructure) adapted: backward time + linearUpwindV grad(U)
  - V46 (sHM scaling) followed: 273k-cell proof-of-concept; production scope HPC

## Geometry (m)

| element | dim |
|---|---|
| cavity L × W × D | 0.508 × 0.102 × 0.102 |
| upstream plate | 5.080 |
| downstream plate | 9.652 |
| side plate (each) | 0.408 |
| top far-field | 6.096 |
| total domain bbox | 15.24 × 0.918 × 6.246 m (x × y × z) |

## Defects

| ID | type | spec | advisor | status (post-V55/V56) |
|---|---|---|---|---|
| D6 | floating debris cube in cavity | 10 mm @ (0.320, 0.018, -0.079) m | none landed | `[QUESTIONABLE 2026-05-11]` (V55) |
| D9 | faceted LE+TE lip curvature | 16 facets/90° @ 8 mm baseline radius | none landed | `[QUESTIONABLE 2026-05-11]` (V56) |

D6 manual verification (`00_check_region.py::check_d6_debris`): cube inside
cavity; clearances {TE: 183, LE: 315, port: 64, starboard: 28, floor: 18,
ceiling: 74} mm. D9 manual verification (`check_d9_facets`): per-segment
angle 5.625°, max chord deviation 0.0096 mm.

## Operating point
M=0.85 · U=290 m/s · T=273.15 K · p=101.325 kPa · Re_L≈6×10⁶ · ρ_∞≈1.292
kg/m³ · a_∞≈331.3 m/s · ν_∞=1.34×10⁻⁵ m²/s

## Time stepping
Δt request 1×10⁻⁴ s (CFL≤1); first run reduced to 6.85×10⁻⁵ s by
`adjustTimeStep yes` after Co max 1.0003 on first step. Sample rate
≈14.6 kHz at adjusted dt (Nyquist 7.3 kHz, comfortably above 5 kHz
aeroacoustic upper).

## Mesh
- blockMesh: 191×11×78 = 163,878 background hex cells (80 mm base)
- sHM (after castellate + snap; layers disabled this run): **273,589 cells**
- Refinement distribution: L0 154,633 / L1 24,232 / L2 73,980 / L3 17,520 / L4 3,224
- FW-H: cellZone `fwh_inside` (14,056 cells) + faceZone `fwh_porous_surface` (2,040 faces)
- Quality: max non-orthogonality 47° / max skewness 0.94 / max aspect ratio 4.6 / 8 concave faces (sHM corner artifacts, non-fatal)

## V-findings filed (V52-V57)

| V# | type | role |
|---|---|---|
| V52 | Codex case-design knowledge gap (4th) | `kOmegaSSTIDDES` belongs in `LES` block not `RAS` |
| V53 | matrix-symmetry-class fvSolution | compressible PIMPLE transonic → PBiCGStab/DILU (V28 inverse) |
| V54 | CAD-surface-vs-mesh-face offset | probes at literal CAD coord fall inside patch-tag helpers |
| V55 | advisor-stack scope gap | first D6: extra_body_in_fluid detector missing |
| V56 | advisor-stack scope gap | first D9: curved-surface-tessellation-accuracy detector missing |
| V57 | first compound-DES root anchor | sandbox + scaffold + pipeline validates end-to-end |

## Playbook S-series candidates (NOT promoted; pending HPC v2)
- S15 "tonal noise weak → check cavity LE refinement ≥5 cells across shear layer"
- S16 "FW-H spectrum noisy → move porous surface inside resolved turbulence region"
- S17 "low Rossiter mode missing → extend time window to 0.75 s for 100-cycle FFT"
- S18 "acoustic reflection contamination → verify waveTransmissive coefficient + far-field box ≥ 30L"

All four are written into V57's lesson cell but NOT yet appended to
`solver_convergence_playbook.md` — promotion requires a second compressible-
DES case OR HPC v2 run of case_016 to ≥0.12 s.

## Reference data (M219 clean cavity at M=0.85, K09 station)

| Rossiter mode | f (Hz) | SPL (dB) |
|---|---|---|
| R1 | 142.0 | 141.6 |
| R2 | 353.0 | 146.3 |
| R3 | 592.0 | 143.4 |
| R4 | 813.0 | 130.2 |

Reference-data validity: **partial** (D6 + D9 defected case ≠ clean
baseline; ±3 dB direct comparison not valid; use as "deviation vs
clean" frame only).

## Wall-clock honesty

| stage | wall time |
|---|---|
| CAD generation | 1.0 s |
| STL extraction | 7 s |
| OF case scaffolding | 0.5 s |
| blockMesh | < 1 s |
| sHM castellate + snap | 26 s |
| checkMesh | 8 s |
| potentialFoam init | 0.3 s |
| rhoPimpleFoam (6 steps, 0.0005 s sim) | 20 s |
| **Total proof-of-concept** | **~75 s** |
| **Production R1 capture (0.12 s sim)** | **estimated days at 273k cells; HPC scope** |
| **Production full Rossiter (0.75 s sim @ ~10M cells)** | **estimated week+ scope** |

## Artifact extraction candidates (per kickoff §6 step 5)
1. `rossiter_mode_post_processor.py` — extract from `09_compute_rossiter_modes.py` (~150 LOC standalone)
2. `FW_H_acoustic_writer.py` — extract from `02_scaffold_case.py::_function_objects_block` (~80 LOC)
3. `cavity_spl_advisor.py` — proposed S15-S18 rule encoding (~120 LOC, pending HPC v2 evidence)
4. `frequency_spectrum_extractor.py` — extract FFT + Hann windowing (~100 LOC)

All four are < 250 LOC; none block v1 sediment. Recommend extraction
after HPC v2 to ensure the FFT path is exercised by real Rossiter peaks.

## Boundaries respected (per kickoff brief)
- CAN: end-to-end run on sandbox · sediment commits · ≤250 LOC artifact extraction (4 candidates listed)
- CANNOT: redesign case · modify other cases · 2D simplification · rhoCentralFoam (we use rhoPimpleFoam transient) · exceed 14 h (used ~2 h)
