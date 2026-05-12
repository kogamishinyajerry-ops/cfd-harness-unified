# Case 011-020 Industrial Extension Roadmap

> **Status**: strategic SSOT · 2026-05-08
> **Author**: main session deep-research synthesis (post harvest cycle 002)
> **Trigger**: user request "结合 case_002a/b APU 仿真算例经验，深度思考，此项目如果要进一步提升工业级部件仿真能力，需要补充哪些部件仿真？"
> **Follow-up**: this doc seeds the next 10-case batch; case_011 dispatch begins immediately after this doc lands.
> **Parent DEC**: V61-198 (industrial-case-driven philosophy)
> **Successor expected**: case_011_020_phase1_close.md after Phase 1 (cases 011-012) sediment lands

## Context

Project completed 10-case roster dispatch 2026-05-08 (cases 002a/b
active + cases 003-010 dispatched). All 10 numerics-class roots
covered. Harvest cycle 002 captured V25 (A2 placeholder semantic
open). Deep-research deliverable evaluating: **what does APU
experience uniquely give us, what's the current 10-case roster
weakness, where is the next high-leverage batch?**

This doc is the strategic SSOT for the next batch (cases 011-020).
It is **NOT** the dispatched roster yet — Codex 出题 + main-session
6/13-check validation must follow per `codex_case_design_protocol.md`
before each case becomes a paste-ready kickoff.

## §1 · APU experience distilled

### Capabilities landed (direct from case_002a/b)

| Capability | Source | V-series trace |
|---|---|---|
| `chtMultiRegionFoam` multi-region thermal coupling | case_002b CHT v2 norad | V14 / V15 |
| Buoyancy + forced-convection mixed | case_002a v14 @ iter 813+ | V13 (pseudo-steady) / V18 (sharpened) |
| Industrial CATIA STEP ingest | 002a v1 imports | V1 / V2 / V8 / V16 / V20 / V24 |
| Geometry surgery (thin-wall + stitching) | A3 advisor (LANDED) | V8 / V10 |
| thin_wall_advisor | A1 (LANDED, 6-of-6 `[VALIDATED]`) | V10 / V23 / V30 / V37 |
| virtual_interface_detector | A2 (LANDED but V25 scope-narrow) | V2 / V19 / V21 / V22 / V25 |
| Preconditioner pathology resilience | V5 lesson | V4 / V5 / V15 cross-family |
| BC writer per-field schema | V11 lesson | V11 |
| Mass conservation pre-flight | V12 lesson | V12 |
| Pseudo-steady residual interpretation | V13 → S13 | V13 → S13 |

### APU's actual physical archetype

APU bay = **"confined-space ventilation + multi-source thermal coupling"**:
- Forced convection (fan-driven) + buoyancy (heat sources) compound
- Multi-region solid (shell / panel / frame) + single fluid (air)
- Mid Re (10⁴-10⁵), low Mach (< 0.1), no phase change
- Industrial CAD from real CATIA assemblies (not parametrically generated)

**Maximum APU leverage**: any case satisfying ≥2 of these elements
inherits V3-V15 + landed tooling directly → development cost drops sharply.

### APU non-coverage

- High-speed rotation (limited to fixed fan, no turbomachine)
- Phase change (no boiling / condensation / cavitation)
- Multi-fluid (limited to single-phase air)
- True transient (v14 is pseudo-steady, not real LES/DES)
- Chemical reaction (no combustion / catalysis)
- Free surface (no VOF)
- Large-scale parameter sweeps
- Acoustics (no FW-H far-field)
- FSI (no solid mechanics coupling)

## §2 · Current 10-case roster coverage matrix

| Numerics root | Covered case | Status | Industrial representativeness |
|---|---|---|---|
| compressible-buoyant-RANS | 002a APU | active v14 | High (HVAC, confined space, battery thermal) |
| + CHT extension | 002b APU | active v2 | High (same + multi-region) |
| incompressible-RANS external | 003 CRM-HLS | active v1 paused | Medium (aerospace high-lift) |
| incompressible-RANS-MRF | 004 NREL Phase VI | active v1 advisor done | **LOW** (wind turbine = open rotor, NOT representative of most industrial pumps/compressors) |
| compressible-RANS internal | 005 M2129 | active v1+v2 | Medium (aerospace intake) |
| compressible-shock-density | 006 ONERA-M6 | active v1 baseline | Medium (transonic wing) |
| multiphase-VOF | 007 KCS | dispatched-deferred | Medium (ship hydrodynamics) |
| incompressible-Lagrangian | 008 GLC305 | active v1 advisor | Medium (aerospace icing / spray) |
| reacting-low-Mach | 009 Sandia Flame D | active v1 baseline | Medium (academic combustion benchmark) |
| incompressible-LES | 010 DrivAer | dispatched-deferred | High (vehicle aerodynamics) |

**Key observations**:

1. D-class (rotating) covers only **open-shaft wind turbine**;
   completely misses true industrial heavy-hitters — **centrifugal
   pumps, centrifugal compressors, fans, mixing impellers** (largest
   share of fluid-machinery industry).
2. All cases are **single-functional validation algorithms** from
   public benchmarks. **None** is a part that industrial CFD
   service companies actually handle daily (heat exchangers,
   HVAC diffusers, electronic heatsinks, filters, static mixers).
3. Reacting flow only covers **academic combustion flame**;
   misses real industrial combustors (furnaces, gas turbine
   combustor, IC engine).
4. LES only covers **vehicle aerodynamics**; misses typical
   industrial LES applications (pipe turbulence, mixing, cavity
   noise).

## §3 · Industrial CFD demand landscape

Rough demand-frequency ranking from public ANSYS Fluent /
Simcenter STAR-CCM+ / OpenFOAM commercial service case studies:

| Rank | Industrial part category | Current coverage | Gap severity |
|---|---|---|---|
| 1 | External aerodynamics (auto / aircraft) | ✅ 006/010 | covered |
| 2 | **Heat exchangers** (plate-fin / shell-tube / compact) | ❌ | **CRITICAL** |
| 3 | **Pumps / compressors** (confined high-speed rotating) | ❌ (only 004 open-rotor) | **HIGH** |
| 4 | **HVAC components** (diffuser / register / duct) | ❌ | **HIGH** |
| 5 | Combustion | 🟡 009 academic | medium (need industrial combustor) |
| 6 | Multiphase | 🟡 007 ship | medium (missing boiling/cavitation/spray) |
| 7 | Reacting flows | 🟡 009 | medium (missing catalytic reactor) |
| 8 | **Turbomachinery cascade** (single compressor/turbine row) | ❌ | **HIGH** |
| 9 | Ship / hydrodynamics | ✅ 007 | covered |
| 10 | **Aeroacoustics** (FW-H, cavity, jet) | ❌ | **HIGH** |
| 11 | **Electronic cooling / microchannel** | ❌ | **HIGH** (data center / EV battery booming) |
| 12 | **Mixing reactor** (stirred tank, static mixer) | ❌ | medium |
| 13 | **Battery thermal management** | ❌ | **rapid growth** (close to 002b CHT) |
| 14 | **Cavity / bay flow** (weapons bay, gear bay) | ❌ | medium |
| 15 | **Nuclear thermal-hydraulics** (T-junction, jet) | ❌ | medium |
| 16 | **Filter / porous media** (HEPA / catalyst bed) | ❌ | medium |
| 17 | **Aeroacoustic / jet noise** | ❌ | medium |
| 18 | **FSI fluid-structure interaction** | ❌ | medium (needs preCICE) |

**Strategic verdict**: current roster is **research-oriented**
not **industrial-service-oriented**. 10 cases cover all OpenFOAM
solver-family roots; **none** corresponds to top-5 industrial CFD
service revenue categories.

## §4 · Recommended Phase 1-4 extension (cases 011-020)

Prioritized by **APU-leverage × industrial-demand × implementation-cost**:

### Phase 1 · Direct APU CHT reuse (highest ROI)

#### case_011 · Plate-fin compact heat exchanger

| Field | Value |
|---|---|
| Solver | `chtMultiRegionFoam` (**direct 002b inheritance**) + multi-stream extension |
| Numerics class | incompressible-RANS-CHT-multi-stream (NEW root) |
| Industrial rep | Auto radiator / HVAC evaporator / gas-turbine recuperator / data center cooling |
| Tier-1 source | Kays & London compact-HX tables / Modine public data / Bell-Delaware |
| Engineering metrics | ε-NTU effectiveness / Δp / local h(x) / outlet T / flow-distribution uniformity |
| Defects | D8 (thin fins) + D5 (mis-aligned plates) + D9 (faceted curved fins) |
| Effort | 10-12h, ~3 versions |
| New artifacts | `multi_stream_solver_runner.py` / `epsilon_ntu_post_processor.py` / `fin_efficiency_calculator.py` / `manifold_distribution_advisor.py` |
| V-series projection | ~3-5 new findings on multi-stream BC coordination, fin-conduction thermal short-circuit, manifold maldistribution, contact resistance BC |

**Core rationale**: heat exchangers = #2 industrial CFD demand;
002b CHT toolchain reuses **directly** to a completely different
industrial part — best demonstration of Pattern 6 numerics-class
inheritance.

#### case_012 · HVAC supply diffuser with thermal stratification

| Field | Value |
|---|---|
| Solver | `buoyantSimpleFoam` (**direct 002a inheritance**) |
| Numerics class | compressible-buoyant-RANS (already covered; this is 002a's industrial-deployment form) |
| Industrial rep | Commercial HVAC / aircraft cabin / data center cold aisle / clean room |
| Tier-1 source | ASHRAE benchmarks / IEA Annex 20 isothermal jet data |
| Engineering metrics | ADPI (Air Diffusion Performance Index) / throw distance / dumping criterion |
| Defects | D1 (slot gap) + D7 (louver wrong-normal) |
| Effort | 8-10h, ~3 versions |
| New artifacts | `adpi_post_processor.py` / `diffuser_throw_calculator.py` / `room_uniformity_advisor.py` |
| V-series projection | ceiling-to-occupied-zone stratification, low-U dumping, wall-attached jet detachment ~3 findings |

### Phase 2 · Industrial rotating machinery (case_004 alone is insufficient)

#### case_013 · Centrifugal pump impeller + volute + cavitation

| Field | Value |
|---|---|
| Solver | `simpleFoam` + MRF (inherits 004) + `interPhaseChangeFoam` or `cavitatingFoam` (NEW) |
| Numerics class | incompressible-MRF-cavitating (NEW root) |
| Industrial rep | Water treatment / oil-gas / chemical / power — **largest single class of industrial fluid machinery** |
| Tier-1 source | ERCOFTAC centrifugal pump test case / Pumpkit benchmark |
| Engineering metrics | Head-vs-flow performance curve / η efficiency / NPSHa/r / cavitation onset location |
| Defects | D1 (impeller tip clearance gap) + D7 (CAM blade leading-edge wrong normal) |
| Effort | 12-15h, ~3 versions |
| New artifacts | `pump_curve_generator.py` / `cavitation_advisor.py` / `npsh_post_processor.py` / `cellzone_volute_audit.py` |
| V-series projection | cavitation phase-change BC pathology, confined-volute MRF (vs 004 open-rotor), tip shear, NPSH inlet boundary ~4-5 findings |

**Core rationale**: case_004 is **open wind turbine**; mainstream
industrial fluid machinery (**confined high-speed rotating**) is
physically very different: phase change, confined flow,
performance curves, cavitation. This case extends the project
from "wind power" to **true industrial pumping/hydraulics**;
80% of industrial-service rotating machinery work has this form.

#### case_014 · Centrifugal compressor stage (with tip clearance)

| Field | Value |
|---|---|
| Solver | `rhoSimpleFoam` + MRF (**combines 004 + 005**) |
| Numerics class | compressible-RANS-MRF (NEW root) |
| Industrial rep | Gas turbine / turbocharger / refrigeration / aero engine boost stage |
| Tier-1 source | NASA CC3 compressor stage (publicly fully-documented) |
| Engineering metrics | PR total pressure ratio / η efficiency / surge margin / choke boundary / characteristic curve |
| Defects | D1 (tip clearance — performance-critical) + D8 (thin blade leading edge) |
| Effort | 14-18h, ~3 versions |
| New artifacts | `turbo_characteristic_post_processor.py` / `tip_clearance_advisor.py` / `surge_choke_detector.py` / `periodic_blade_row_writer.py` |
| V-series projection | tip-leakage flow capture, surge prediction sensitivity, periodic boundary conditions, total-total vs total-static reference state ~5 findings |

**Core rationale**: combines case_004 rotation + case_005
compression → **true industrial turbomachine**. NASA CC3 is
turbomachinery CFD's "gold standard" — landing this gives the
project credibility for turbomachinery business.

### Phase 3 · Compound numerics roots (multi-prior-case inheritance)

#### case_015 · T-junction thermal striping (LES + CHT)

| Field | Value |
|---|---|
| Solver | `chtMultiRegionFoam` + LES variant or `buoyantPimpleFoam` + LES (**combines 002b + 010**) |
| Numerics class | incompressible-LES-CHT (NEW root) |
| Industrial rep | Nuclear primary loop / steam pipe / chemical reactor inlet — **fatigue failure is real $$$ problem** |
| Tier-1 source | Vattenfall T-junction (OECD/NEA benchmark, well-documented) |
| Engineering metrics | Wall T striping amplitude / wall-T frequency spectrum / RMS T' / thermal fatigue stress estimate |
| Defects | D5 (pipe-pipe interface mis-alignment — real welding defect) |
| Effort | 12-15h, ~3 versions |
| New artifacts | `wall_temperature_striping_post_processor.py` / `thermal_fatigue_advisor.py` / `T_spectrum_extractor.py` |
| V-series projection | LES + CHT coupling stability, wall-T spectrum extraction, long-time statistic sample size ~4 findings |

#### case_016 · Aircraft weapons bay cavity flow (transient compressible DES)

| Field | Value |
|---|---|
| Solver | `rhoPimpleFoam` + DDES (**combines 006 + 010**) |
| Numerics class | compressible-DES (NEW root) |
| Industrial rep | Military weapons bay / landing gear bay / high-speed train pantograph / car sunroof — noise + drag dual demand |
| Tier-1 source | M219 cavity (UK MOD public data complete) / NASA cavity |
| Engineering metrics | SPL spectrum (Rossiter modes) / drag increment / base pressure / FW-H far-field SPL |
| Defects | D6 (debris in cavity) + D9 (faceted curved walls) |
| Effort | 12-14h, ~3 versions |
| New artifacts | `rossiter_mode_post_processor.py` / `FW_H_acoustic_writer.py` / `cavity_spl_advisor.py` / `frequency_spectrum_extractor.py` |
| V-series projection | tonal noise capture vs grid, FW-H surface placement, time-window length, boundary acoustic reflection ~5 findings |

**Core rationale**: project currently has **zero aeroacoustic
capability** but industrial aeroacoustics (FW-H, Rossiter, jet
noise) is one of the fastest-growing CFD directions in
aerospace/automotive. M219 is the most economical case for
establishing baseline capability.

### Phase 4 · Specialized industrial verticals

| # | Case | Solver | Industrial rep | Tier-1 | Effort |
|---|---|---|---|---|---|
| 017 | Pin-fin electronic heatsink | `chtMultiRegionFoam` + low-Re air | CPU/GPU / EV battery / IGBT | TIMA / IBM thermal | 8-10h |
| 018 | Cyclone separator (3D swirl + Lagrangian) | `pimpleFoam` + kinematicCloud (extends 008 to swirl) | Chemical / mining / dust collection | Stairmand / Lapple | 10-12h |
| 019 | Static mixer (Kenics / Sulzer) | `simpleFoam` + scalar transport | Chemical / polymer / food / pharma | Sulzer Chemtech / academic LES | 8h |
| 020 | Filter / porous media (Darcy-Forchheimer) | `simpleFoam` + porous source (extends 003) | HEPA / catalyst bed / EV cooling / fuel cell | ERCOFTAC porous-media | 8h |

## §5 · Defect catalog coverage analysis

D1-D10 catalog with current coverage:

| Defect | Cases injecting | Status |
|---|---|---|
| D1 (sub-mm gap) | 8/8 (003-010) | severely over-sampled |
| D2 (over-dense triangulation) | 1/8 (case_005) | normal |
| D3 (non-manifold shared face) | 0/8 | **uncovered** |
| D4 (curved sliver) | 1/8 (case_006 wing tip) | normal |
| D5 (mis-aligned shared face) | 0/8 | **uncovered** |
| D6 (floating debris body) | 0/8 | **uncovered** |
| D7 (wrong-normal face) | 0/8 | **uncovered** |
| D8 (thin shell) | 5-6/8 | over-sampled |
| D9 (over-simplified curved surface) | 0/8 | **uncovered** |
| D10 (open shell non-watertight) | 0/8 | **uncovered** |

**Phase 1-4 defect distribution correction**: D3 / D5 / D6 / D7 /
D9 / D10 each get at least one injection opportunity; D1/D8 get
replaced with under-utilized defects. This is itself a project
capability extension (each defect type needs a different advisor
path).

## §6 · Engineering metrics catalog extension

Current case-produced metrics (external-readable deliverables):

```
Cl, Cd, Cm, Cp(x/c), residuals, β(s/c), DC60, lambda-shock map,
Ct/Cf/Cw, force coefficients, T(r,z), Z(r,z), wave elevation,
y+ histogram, mass flow balance
```

Phase 1-4 metric extensions:

```
+ ε-NTU effectiveness (HX)
+ h(x) local convective heat transfer coefficient
+ pressure drop Δp (HX / porous / static mixer)
+ pump head H, NPSHa/r, η_pump
+ compressor PR, η_compressor, surge margin
+ ADPI, throw distance (HVAC)
+ wall temperature spectrum, RMS T' (T-junction)
+ SPL spectrum, Rossiter mode tones (cavity)
+ FW-H far-field SPL (acoustic)
+ θ_junction-to-ambient thermal resistance (electronic)
+ d50 cut-off diameter, collection efficiency η(dp) (cyclone)
+ RTD residence time distribution, COV (mixer)
+ anisotropic flow split (porous)
```

Each new metric corresponds to a new post-processor advisor.

## §7 · Implementation strategy

### Recommended pacing

| Time window | Recommended | Estimated total effort |
|---|---|---|
| **Batch 1** (cases 011-012, Phase 1) | HX + HVAC, max 002a/b reuse | 18-22h sub-session total |
| **Batch 2** (cases 013-014, Phase 2) | Pump + compressor, fill D-class industrial core | 26-33h |
| **Batch 3** (cases 015-016, Phase 3) | LES+CHT + cavity acoustic, validate compound capability | 24-29h |
| **Batch 4** (cases 017-020, Phase 4) | 4 specialized parts, single-case short | 34-42h |

Total **~100-130h sub-session work** (vs current 10-case roster
~80-110h estimate); **roster doubles, industrial representativeness
grows by an order of magnitude**.

### Coordination with existing governance

- Each case follows current 4-file kickoff + Codex 出题 + main-session
  6/13-check validation flow
- Harvester triggers cycle on ≥3 sub-session sediment (skill
  `cfd-harness-harvest` already established)
- Each Phase end triggers full-mode harvest evaluation
- **A2-v2 sub-DEC must land before Phase 2 begins** (otherwise
  case_013/014 repeat V25 placeholder problem)
- A3-v2 sub-DEC priority depends on case_009 D2 evidence
- Knowledge-status convention applied throughout per
  `knowledge_status_convention.md`

### Component bank extension

`component_bank.md` already pre-lists Class A1-A5 / B1-B5 / C1-C4 /
D1-D4 / E1-E3 (21 candidates). Phase 1-4 directly maps to several:

- A1 plate-fin heat sink → case_017
- A2 centrifugal fan housing → case_012 neighbor
- B1 server rack → case_017 neighbor
- B5 industrial oven → case_012 neighbor
- D1 centrifugal pump → case_013 (direct)
- D2 mixer tank → case_018/019 neighbor
- D3 cooling fan in shroud → case_017 neighbor
- E2 supersonic intake → case_006 partial

Bank **completely missing** these important categories (recommend
adding):

- Compact heat exchangers (plate-fin / shell-tube / printed circuit)
- HVAC diffusers / registers
- Centrifugal compressor cascade
- Static mixer
- Cyclone separator
- Porous media / filter
- Cavity acoustic
- Axial turbine cascade

**Side recommendation**: harvest 003 should include a "extend
component_bank.md with industrial archetypes" patch draft.

## §8 · Key judgment · TL;DR

1. **Current 10-case roster is research-benchmark-oriented, not
   industrial-service-oriented**. Covers all OpenFOAM solver-family
   roots, but top-5 industrial CFD service revenue categories
   (HX / pumps / HVAC / electronic cooling / turbomachinery)
   are essentially missing.

2. **APU 002a/b's real assets are CHT toolchain + buoyancy +
   industrial CAD ingest**. These assets are under-utilized in
   003-010 — only case_017 (pin-fin) directly reuses. Next batch
   should **maximize APU CHT reuse**.

3. **Highest-ROI next batch**: case_011 compact HX (direct 002b
   reuse) + case_013 centrifugal pump (fill industrial rotating)
   + case_016 cavity acoustic (open new capability). 3 cases ~36h
   estimate covering the 3 biggest industrial gaps.

4. **Defect catalog has many under-used entries** (D3 / D5 / D6 /
   D7 / D9 / D10); new batch case selection prioritizes injecting
   these for advisor-toolchain diversification.

5. **A2-v2 sub-DEC must land before Phase 2 begins**, otherwise
   case_013/014 repeat V25 placeholder problem, wasting sub-session
   cycles.

6. **Pre-batch checklist**:
   - [ ] Harvest 003 to check 003-010 sediment trends
   - [ ] Push A2-v2 sub-DEC (draft at
         `patches/draft_a2_v2_gap_detection_2026-05-08.md`)
   - [ ] Add "industrial archetypes" section to `component_bank.md`
   - [ ] Have Codex design case_011 per new bank addition

## Decision log

| Date | Decision | Rationale |
|---|---|---|
| 2026-05-08 | Establish this roadmap as strategic SSOT | User request for deep analysis of industrial extension |
| 2026-05-08 | Phase 1 = HX + HVAC (cases 011-012) | Maximum APU CHT leverage, lowest risk, highest industrial demand |
| 2026-05-08 | Phase 2 must wait for A2-v2 | Avoid V25 placeholder problem on rotating machinery |
| 2026-05-08 | 5+ artifact extractions per phase 2-3 cases | Pump/compressor/cavity acoustic each need new infra |
| 2026-05-08 | component_bank.md to be extended in harvest 003 | Bank missing key industrial archetypes |

## References

- `.planning/decisions/2026-05-07_v61_198_apu_bay_strategic_pivot.md`
  — parent strategic charter
- `.planning/methodology/industrial_case_solver_findings.md` — V-series
- `.planning/methodology/component_bank.md` — existing component menu
- `.planning/methodology/knowledge_status_convention.md` — 2026-05-08 convention
- `.planning/harvest_reports/2026-05-08_harvest_002.md` — recent cycle
- `.planning/patches/draft_a2_v2_gap_detection_2026-05-08.md` — A2-v2 prerequisite
- `.claude/skills/cfd-harness-harvest/SKILL.md` — harvest workflow
- `.planning/case_index.md` — current case truth (SSOT)
- `.planning/case_proposal_queue.md` — Codex-fed roster
