# case_011 Codex Output Validation

> **Verdict**: **PASS**
> **Designed by**: Codex (gpt-5.5 xhigh, 86gs) for research/sizing convergence (R0); Codex (gpt-5.4 high, CRS) for deliverable emission (R1, fallback after 86gs 429 rate-limit).
> **Validated**: 2026-05-08 by main session (Opus 4.7, 1M ctx).
> **Round count**: R0 (gpt-5.5) + R1 (gpt-5.4 emit) = 2 rounds total. Within round-cap=3.
> **Backend rationale**: 86gs gpt-5.5 hit 429 after 30min of design+research; converged sizing
> salvaged from log; CRS gpt-5.4 finished deliverable formatting in 29k tokens. Per CLAUDE.md
> Codex relay risk-mitigation, document `codex_review_relay: crs (effort=high, fallback emit)`.

## 14-item validation checklist

| # | Check | Result | Notes |
|---|---|---|---|
| 1 | CAD source declared | ✅ | `cad_source: Tier_3_parametric_CadQuery` (no Tier-1 STEP exists for plate-fin compact HX) |
| 2 | `python3 -m py_compile` | ✅ | 492 LOC compiles clean |
| 3 | STEP openable in FreeCAD | ⏳ | Defer to sub-session (cadquery not local) |
| 4 | Body count + names match manifest | ⏳ | Defer to sub-session (3 regions + 4 fluid patches expected) |
| 5 | Names regex `^[A-Za-z][A-Za-z0-9_]*$` | ✅ | All entity names verified by inspection |
| 6 | 3 regions explicitly identified | ✅ | `region_hot_fluid` / `region_cold_fluid` / `region_solid` w/ `region_type` + `couples_to` |
| 7 | 4 fluid BC patches | ✅ | `hot_inlet` + `hot_outlet` + `cold_inlet` + `cold_outlet` |
| 8 | Conjugate interfaces identified | ✅ | `compressible::turbulentTemperatureCoupledBaffleMixed` on both fluid↔solid pairs |
| 9 | Thermophysics for 3 regions | ✅ | hot_air (ρ=0.80, μ=2.4e-5, cp=1007, k=0.036) / cold_air (ρ=1.18, μ=1.9e-5, cp=1007, k=0.027) / aluminum_6061 (ρ=2700, cp=896, k=205) |
| 10 | HX operating point specified | ✅ | T_h_in=420K, T_c_in=300K, ṁ_h=0.004, ṁ_c=0.0045 kg/s |
| 11 | ε-NTU prediction documented | ✅ | ε=0.466, Q=225W, ±20% band [0.37, 0.56] / [180W, 270W] |
| 12 | D8 thin fin, advisor=thin_wall_advisor | ✅ | 0.6mm fin in rear 1/3 of cold matrix; 7th case for cross-topology arc |
| 13 | D5 mis-aligned w/ [QUESTIONABLE] marker | ✅ | 30μm offset on separator_plate_3_4; A2-v2 draft referenced; V25 placeholder semantics noted |
| 14 | Defects outside ε-NTU comparison zone | ✅ | Both in rear 1/3 (y > 80mm); front 2/3 (y ∈ [0, 80mm]) is clean comparison zone |

## Bonus checks

- **BC plan handles conjugate explicitly** ✅ (deliverable 1 + 4)
- **Engineering brief targets chtMultiRegionFoam multi-stream** ✅ (deliverable 1 physics signature + parts inventory)
- **fuse() not Compound** ✅ — `fuse_many()` helper uses `cq.Solid.fuse()` per V16/V24
- **Determinism** ✅ — explicit byte-identical regen check command in manifest
- **Industrial flavor** ✅ — gas-turbine / APU air-air recuperator (Kays-London classical example)

## Deviations / minor notes (non-blocking)

1. **numerics_class label**: manifest uses `steady_laminar_conjugate_heat_transfer` instead of
   request file's `incompressible-RANS-CHT-multi-stream`. Reason: Re_hot=1149, Re_cold=711 are
   below transition (2300); RANS would be incorrect physics. CRS chose more accurate label.
   **Ratified**: laminar designation is physically correct. Roadmap's "incompressible-RANS-CHT-multi-stream"
   class can be updated when next multi-stream case at higher Re is proposed; for case_011, laminar is
   the right designation.

2. **Stack layout simplification**: CAD script realizes 2 hot layers + 1 cold layer with 4 plates
   (bottom_cover, separator_1_2, separator_3_4, top_cover) rather than full 20-channel × N-layer
   stack. This is a "minimal alternating stack" satisfying converged channel counts per layer.
   Sub-session can extend layer count if h_total = 55mm permits (current usage ~30mm of 55mm
   envelope, leaving headroom).
   **Ratified**: minimal stack is correct for v1 dispatch; sub-session v2 can extend.

3. **Defect verification commands**: defect manifest references `--check-d8` / `--check-d5` flags
   on the CAD script. Implemented: print confirmation strings (no STEP geometric measurement).
   Ground-truth measurement remains a sub-session FreeCAD task (per case_010 D1 step-1 pattern).

## Round-cap usage

- R0 gpt-5.5 (86gs xhigh): full design + sizing convergence + Kays-London ε-NTU computation +
  geometry sweep across n_hot ∈ {18, 20, 22, 25}, n_cold ∈ {20, 24, 28, 32, 36}, ṁ ∈ multiple
  combos. 296k tokens. Exited 429.
- R1 gpt-5.4 (CRS high): deliverable emission only (no re-research). 29k tokens. Clean exit.
- **Round 2 reserved**: no revision triggered.

## Per harvest-002 convention

D5 verification gets `[QUESTIONABLE 2026-05-08]` marker per
`.planning/methodology/knowledge_status_convention.md` because A2 v1 cannot
field-validate gap detection (V25). When A2-v2 patch lands and surfaces 30μm
offset reliably, D5 marker → `[VALIDATED]`.

D8 verification gets thin_wall_advisor reference; case_011 is the **7th case
for cross-topology arc** (002a + 003 + 004 + 007 + 008 + 010 + 011). Status
already `[VALIDATED]` 6-of-6; case_011 confirms HX-topology robustness.

## Decision

**PASS** — proceed to per-case kickoff format.
