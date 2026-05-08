# Case 011 · Plate-Fin Compact HX · chtMultiRegionFoam multi-stream (Industrial Reference, NEW BATCH Phase 1 #1)

> **First case in the industrial-extension batch** (case_011-020) per
> `.planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md`.
> Pivots from research-benchmark cases toward industrial-service-market cases.
>
> **NOT a gold-standard case.** Reference target is Kays-London ε-NTU
> compact-HX prediction (ε≈0.466, Q≈225 W) within ±20% tolerance band.
>
> **Direct inheritance**: case_002b CHT machinery (Pattern 6); the
> multi-stream BC bookkeeping + multi-fluid thermophysics is a NEW
> numerics-class root extension to **steady-laminar-CHT-multi-stream**.

## What this entry is

This case validates that the harness can produce industrial-grade
results on a **compact plate-fin air-air recuperator** (gas-turbine /
APU thermal recovery flavor). Two fluid streams (hot air at 420 K,
cold air at 300 K) cross-flow through unmixed channels separated by
aluminum 6061 plate-fin matrix; conjugate heat transfer through the
solid is solved with `chtMultiRegionFoam` steady.

This unlocks a new **numerics-class root**:
**steady-laminar-CHT-multi-stream**. case_002b covered single-stream
CHT (1 fluid + 6 solid extrusions); case_011 covers multi-stream CHT
(2 fluids + 1 solid). Multi-stream conjugate BC bookkeeping +
multi-fluid thermophysics setup is genuinely new ground.

## Pointer

| field | value |
|---|---|
| Case path | `~/Desktop/case_011_plate_fin_compact_hx/` |
| SSOT YAML | `~/Desktop/case_011_plate_fin_compact_hx/config/case.yaml` |
| Top-level overview | `~/Desktop/case_011_plate_fin_compact_hx/evidence/v1/REPORT.md` |
| CAD source | `inputs/cad_codex_v1.step` (492-LOC CadQuery, byte-deterministic) |
| Pipeline scripts | `scripts/{build_cad, 00..11, thin_wall_falsification_d8, a2_falsification_d5}` |
| Templates | `templates/{regionProperties, thermophysicalProperties_air_hot/cold/aluminum, turbulenceProperties_laminar, g}` |
| Solver | `chtMultiRegionFoam` (ESI OpenFOAM v2312, steady) |
| Reference target | ε ≈ 0.466, Q ≈ 225 W (Kays-London ε-NTU); ±20% band |

## What's different from case_002b

| Axis | case_002b | case_011 |
|---|---|---|
| Solver | chtMultiRegionSimpleFoam | chtMultiRegionFoam (ESI 2312) |
| Region count | 7 (1 fluid + 6 Ti shell solids) | 3 (2 fluids + 1 aluminum solid) |
| Stream count | 1 | **2 (hot + cold cross-flow, both unmixed)** |
| Geometry source | CATIA → STL ingest | CadQuery parametric (Tier-3) |
| Manifolds | n/a (single inlet/outlet) | tapered hot + cold manifolds (K_manifold=2.5 ref) |
| Reference KPI | none (no benchmark) | ε ≈ 0.466, Q ≈ 225 W (Kays-London) |
| Defect set | D1, D8 | **D8 + D5 (D5 = first 30μm plate offset, A2-v2 dependency)** |
| Re range | 8,000-15,000 (turbulent) | 711-1149 (**laminar both sides**) |

## Operating point + reference KPI

| field | value |
|---|---|
| `T_h_in` | 420 K |
| `T_c_in` | 300 K |
| `m_dot_hot` | 0.004 kg/s (Re_hot ≈ 1149, laminar) |
| `m_dot_cold` | 0.0045 kg/s (Re_cold ≈ 711, laminar) |
| `epsilon` (predicted) | 0.466 |
| `Q` (predicted) | 225 W |
| `T_h_out` (predicted) | 364 K |
| `T_c_out` (predicted) | 350 K |
| `Δp_hot` (predicted) | 168 Pa |
| `Δp_cold` (predicted) | 26 Pa |
| Tolerance band | ε ∈ [0.37, 0.56], Q ∈ [180 W, 270 W] |

## Defect set + advisor exercise

| Defect | Target | Advisor | Status (v1) |
|---|---|---|---|
| D8 | Cold-fin rear-1/3 thickness 0.6mm | `thin_wall_advisor` | **PASS · critical · 7th cross-topology data point** |
| D5 | separator_plate_3_4 rear-1/3 30μm x-offset | `virtual_interface_detector` (A2) | **ALGORITHM_RUNS_CLEANLY · [QUESTIONABLE 2026-05-08]** |

D5 [QUESTIONABLE] marker per `knowledge_status_convention.md`: A2 v1
returns `bbox_overlap_fraction=1.0 / area_diff_fraction=0.0`
(hardcoded placeholders) regardless of actual offset — 30μm
field-validation pending A2-v2 sub-DEC merge. Did NOT propose
`isSame()` fast-path (V2 lesson preserved).

## v1 progression (planned + actual)

| Version | Key change | Status |
|---|---|---|
| v1 | Initial multi-stream CHT setup, sHM mesh at level (1,2), steady chtMultiRegionFoam | **first run** |
| v2 (planned) | Bump cold_fin patches to level 4 (per thin_wall_advisor recommendation); install sampleDict for per-channel ṁ + h(x) sampling | TBD |
| v3 (planned, fallback) | Switch to chtMultiRegionPimpleFoam if T-residual oscillates; relax T 0.95→0.85 | TBD |

## Provenance

- Designed by: Codex gpt-5.5 xhigh (86gs R0 design + sizing convergence)
  + Codex gpt-5.4 high (CRS R1 emit, fallback after 86gs 429)
- Validated by: Opus 4.7 (1M ctx) main session, 2026-05-08 — see
  `.planning/methodology/kickoff/case_011_validation.md` (PASS)
- Executed by: Opus 4.7 (1M ctx) sub-session, 2026-05-09
- Governance: V130 advisory-only · V132 no AI-mutating routes · CLAUDE.md v2.3
