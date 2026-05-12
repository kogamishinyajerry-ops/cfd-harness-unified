# Case Proposal Queue · Codex-driven (replaces case_list.md)

> **2026-05-07 evening reframe.** Old `case_list.md` (static
> Ahmed/NACA/S-duct roster) deleted by user direction: "your case
> list mostly lacks ready STEP files — meaning you are NOT being
> 出题 by anything." New model: **Codex 出题, geometry from public
> sources first**, with Codex generating CadQuery only as fallback.
>
> This queue is what main session works through, NOT a static
> menu. Items get proposed by Codex on demand, validated by main
> session, then dispatched to sub-sessions.

## Workflow

```
                    ┌─────────────────────┐
                    │ Project main session │
                    │ (this Claude Code)   │
                    └──────────┬───────────┘
                               │
              "Need a new case in solver-class X"
                               │
                               ▼
                  ┌────────────────────────┐
                  │ codex-relay-with gpt-5.5 │
                  │ Codex (case 出题者)        │
                  └──────────┬───────────────┘
                             │
        Tier 1 priority → public source check first
                             │
                             ▼
              ┌────────────────────────────┐
              │ Codex returns 5 deliverables: │
              │   1. Engineering brief         │
              │   2. CAD generation script     │
              │   3. STEP file (post-defect)   │
              │   4. Parts manifest YAML       │
              │   5. Defect manifest YAML      │
              └──────────┬─────────────────┘
                         │
                         ▼
              ┌────────────────────────────┐
              │ Main session validates:      │
              │   ✓ script executes          │
              │   ✓ STEP imports             │
              │   ✓ patch names valid        │
              │   ✓ defects actually present │
              │   ✓ solver class matches     │
              └──────────┬─────────────────┘
                         │
                  pass / fail (≤3 rounds)
                         │
                         ▼
                ┌──────────────────┐
                │ Per-case kickoff   │
                │ (paste-to-sub-session)│
                └──────────┬───────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │ User opens new Claude Code  │
              │ session, pastes kickoff      │
              │ → sub-session executes        │
              └──────────────────────────┘
```

## Coverage map progress (where to point Codex next)

When main session asks Codex for the NEXT case, target a row that
is **pending** or **partially covered**:

| Solver class | Numerics class | Coverage | Next-case priority |
|---|---|---|---|
| Internal flow + buoyancy + forced convection | compressible-buoyant-RANS | ✅ case_002a (active, v14+) | LOW (covered) |
| CHT (multi-region + radiation) | compressible-buoyant-RANS + solid-thermo | ✅ case_002b (active, v2 norad) | LOW (covered, v3 in case_002b) |
| External flow + high-Re + boundary layer | incompressible-RANS | 🟦 dispatched (case_003, deferred) | LOW (queued) |
| Internal compressible diffuser (subsonic to transonic) | compressible-RANS | 🟦 dispatched (case_005, deferred) | LOW (queued) |
| Rotating machinery (MRF / sliding mesh) | incompressible-RANS-MRF | 🟦 dispatched (case_004, deferred) | LOW (queued) |
| Compressible high-speed (shock-density-based) | compressible-shock-density-based | 🟦 dispatched (case_006, deferred) | LOW (queued) |
| Multiphase / VOF | multiphase-VOF | 🟦 dispatched (case_007, deferred) | LOW (queued) |
| Particle-laden / Lagrangian (icing) | incompressible-RANS-Lagrangian | 🟦 dispatched (case_008, deferred) | LOW (queued) |
| Combustion / reacting flow | reacting-low-Mach | 🟦 dispatched (case_009, deferred) | LOW (queued; longest sub-session effort) |
| Transient LES / DES | incompressible-LES | 🟦 dispatched (case_010, deferred) | LOW (queued) |

## Active queue (proposed but not yet dispatched)

> **Roster expansion 2026-05-07 evening** (case_005 → case_010, 6
> proposed cases). Each picks a distinct numerics class so Pattern
> 6 inheritance is empty — every case becomes a NEW V-finding root,
> maximizing index diversity. Dispatch order is flexible; HIGH-impact
> + Tier-1-clean cases (case_005, case_006) likely first.
>
> **2026-05-08 evening update** — second batch (case_011 → case_020)
> proposed per `.planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md`.
> Strategic pivot: research-benchmark roster (003-010) → industrial-
> service roster (011-020). Each new case selected by **APU-leverage
> × industrial-demand × implementation-cost** rather than numerics-
> root coverage (most roots already covered). 4 phases dispatched
> sequentially; A2-v2 sub-DEC (drafted at
> `patches/draft_a2_v2_gap_detection_2026-05-08.md`) must land
> before Phase 2 begins.

| case_id | Solver class | Numerics class (Pattern 6 root) | Tier-1 candidate | Defect candidates | Industrial impact | Effort | Why this case |
|---|---|---|---|---|---|---|---|
| ~~case_005_rae_m2129_sduct~~ → **DISPATCHED** see Dispatched section below | | | | | | | |
| ~~case_006_onera_m6_transonic~~ → **DISPATCHED** see Dispatched section below | | | | | | | |
| ~~case_007_kcs_ship_vof~~ → **DISPATCHED** see Dispatched section below | | | | | | | |
| ~~case_008_irt_icing_lagrangian~~ → **DISPATCHED** see Dispatched section below | | | | | | | |
| ~~case_009_sandia_flame_d~~ → **DISPATCHED** see Dispatched section below | | | | | | | |
| ~~case_010_drivaer_les~~ → **DISPATCHED** see Dispatched section below | | | | | | | |
| ~~case_011_plate_fin_compact_hx~~ → **DISPATCHED** see Dispatched section below | | | | | | | |
| ~~case_012_hvac_supply_diffuser~~ → **DISPATCHED** see Dispatched section below | | | | | | | |
| ~~case_013_centrifugal_pump_cavitating~~ → **DISPATCHED** see Dispatched section below | | | | | | | |
| ~~case_014_nasa_cc3_compressor_stage~~ → **DISPATCHED** see Dispatched section below | | | | | | | |
| ~~case_015_vattenfall_t_junction_thermal_striping~~ → **DISPATCHED** see Dispatched section below | | | | | | | |
| ~~case_016_m219_cavity_des_acoustic~~ → **DISPATCHED** see Dispatched section below | | | | | | | |
| ~~case_017_pin_fin_electronic_heatsink~~ → **DISPATCHED** see Dispatched section below | | | | | | | |
| ~~case_018_stairmand_cyclone_separator~~ → **DISPATCHED** see Dispatched section below | | | | | | | |
| ~~case_019_kenics_static_mixer~~ → **DISPATCHED** see Dispatched section below | | | | | | | |
| ~~case_020_porous_media_filter_darcy_forchheimer~~ → **DISPATCHED** see Dispatched section below | | | | | | | |

### Roster rationale

**Why these 6, in this order**:

1. **Numerics-class diversity is the ranking objective**, not industrial sector. Each case picks a numerics root NOT covered by case_002a/b/case_003/case_004. After all 10 land, the project covers: incompressible-RANS, incompressible-RANS-MRF, compressible-buoyant-RANS, CHT, compressible-RANS, compressible-shock-density-based, multiphase-VOF, RANS-Lagrangian, reacting-low-Mach, incompressible-LES. That's **the workhorse OpenFOAM solver matrix**.

2. **Industrial impact tiebreaker**: within numerics axes, pick the most-used industrial reference (RAE M2129 over Sajben; ONERA M6 over NACA airfoils; KCS over Wigley hull; DrivAer over Ahmed).

3. **Tier-1 availability**: 5 of 6 are clean Tier-1 (RAE M2129 / ONERA M6 / Sandia Flame D / NASA IRT / DrivAer). KCS is Tier-1-adjacent (ITTC benchmark, geometry available via NMRI / FreeShip). No Tier-3 from-scratch needed — Codex pressure stays low.

4. **Effort progression**: case_005 (5-8h) → case_006 (6-9h) → case_007 (8-12h) → case_008 (8-12h) → case_010 (10-14h) → case_009 (12-16h, deferred climb). Sub-session resources scale gradually.

5. **Lane B exclusions respected throughout**: no Ahmed body, no NACA 0012 airfoil at standard Re, no Sajben diffuser, no BFS, no Ercoftac mixing tank. These remain validation references (`component_bank.md` Lane B), not primary roster.

### Dispatch policy for the queue

- **No pre-allocation beyond 1-2 cases ahead** (per concurrency policy below). Cases sit in this queue as INTENT, not commitment. Only Codex round + 6-check validation moves a case to Dispatched.
- **Order is suggestive, not strict**: when next dispatch slot opens, pick highest HIGH-impact + lowest infrastructure climb. case_005 likely first; case_009 likely last.
- **Round cap stays at 2 per case**: if Codex's first design fails validation badly, one revision; otherwise escalate to user.
- **case_007 KCS ship caveat**: ITTC geometry license needs verification before dispatch. If license blocks redistribution of derived STEP, fall back to Wigley hull (Tier 3 from-scratch, well-documented analytic form).
- **case_008 icing caveat**: confirm Codex picks GLC305 or 23012, NOT NACA 0012, in the case-design request prompt.
- **case_009 Sandia Flame D caveat**: chemistry mechanism is the long pole. Codex prompt should specify "2-step or DRM-19 reduced mechanism, NOT GRI-Mech 3.0" to keep solver tractable. Even so, this is the highest-effort case in the roster.

## Dispatched (kickoff paste-ready, awaiting sub-session start)

| case_id | Solver class | Codex 出题 round | CAD source | Defects | Kickoff file | Dispatched | Status note |
|---|---|---|---|---|---|---|---|
| `case_003_crm_hls_boundary_layer` | External high-Re + boundary layer | 1 of 2 (no revision needed) | Tier-1 NASA/AIAA HLPW6 CRM-HLS | D1 (0.35 mm gap) + D8 (0.80 mm thin plate) | `methodology/kickoff/case_003_crm_hls_boundary_layer.md` | 2026-05-07 evening | **IN-FLIGHT · v1 PAUSED** (2026-05-08) — sub-session executed v1 milestone: CAD generation + D1+D8 ground-truth + first industrial cross-topology field-validation of A2 (PASS, planar-box Z-axis gap) + thin_wall_advisor (PASS, planar plate). V2/V10 status upgrades landed; V20 (HLPW6 unit-scale: 91 m semi-span ≈ 25.4× over physical) + V21 (A2 cross-case divergence vs case_005 V19) new findings landed. CFD pipeline deferred pending V20 main-session resolution. Reference profile: `.planning/case_profiles/case_003_crm_hls_boundary_layer.md` |
| `case_004_nrel_phase_vi_mrf` | Rotating machinery (MRF / sliding mesh) | 1 of 2 (no revision needed) | Tier-1 NREL Phase VI / NREL TP-500-29955 | D1 (0.30 mm gap nacelle↔cover) + D8 (0.75 mm thin yaw shim) | `methodology/kickoff/case_004_nrel_phase_vi_mrf.md` | 2026-05-07 evening | **IN-FLIGHT · v1 PAUSED** (2026-05-08) — sub-session executed: CAD generation 1.96 MB STEP + Tier-1 PDF cached 7.89 MB (no DNS hijack on this run, contradicts main session's earlier validation note); D1+D8 ground-truth FreeCAD distToShape=0.30000 mm exact + bbox-min=0.75000 mm exact; A2 advisor 3rd cross-topology PASS via `_run_shared` (Y-axis gap, axis-aligned planar boxes — V22) refining V21 hypothesis toward "case_005-failure is curved-geometry-specific"; thin_wall_advisor 3rd cross-topology PASS @ severity=critical (V23, no scope gap surfaces — cleanest A1-A5 sediment); V16 fragmentation reproduced + new datum-frame finding (V24, compounds Codex protocol revision recommendation). MRFProperties.j2 + 08b_write_mrf.py + 07b_audit_mrf.py NEW infrastructure ready (extract candidates after 1-2 more rotating-machinery cases). Mesh + solver run deferred to v2 sub-session. Reference profile: `.planning/case_profiles/case_004_nrel_phase_vi_mrf.md` |
| `case_005_rae_m2129_sduct` | Internal compressible subsonic-transonic diffuser | 1 of 2 (no revision needed) | Tier-1 NASA Glenn RAE M2129 (T1.I1; URL HTTP 500 transient) | D1 (0.35 mm flange gap) + D2 (102,400-tri over-dense throat liner) | `methodology/kickoff/case_005_rae_m2129_sduct.md` | 2026-05-08 | **IN-FLIGHT (v1 baseline complete 2026-05-08)** — sub-session ran end-to-end: 52,078 cells, rhoSimpleFoam 0-500 iter in 144 s, pseudo-steady oscillating. **A3 first industrial falsification = PARTIAL** (V17). **A2 first industrial falsification = PARTIAL** (V19) — kickoff's "A2 still pending" was stale (A2 landed at commit a09ae0a); A2 has V2-pattern shared-interface detection but lacks D1-pattern sub-mm gap-as-defect detection. 4 V-findings sourced (V16: STEP roundtrip fragmentation; V17: A3 redundancy gap; V18: compressible-RANS pseudo-steady mass imbalance; V19: A2 sub-mm gap scope gap). 2 playbook entries (S13, S14). 2-of-2 advisor scope-narrowness pattern in single case-thread → recommended advisor-scope-expansion arc sub-DEC. Hand-coded compressible BC writer + thermo writer + DC60 post-processor — extraction candidates after case_006 |
| `case_006_onera_m6_transonic` | External transonic 3D wing | 1 of 2 (no revision needed; **CRS gpt-5.4 high fallback** — 86gs xhigh 503'd) | Tier-1 NASA Glenn ONERA M6 (T1.A3; URL HTTP 500 persistent — same as case_005) | D1 (0.35 mm root-fairing gap) + D4 (0.18 mm tip-cap sliver) | `methodology/kickoff/case_006_onera_m6_transonic.md` | 2026-05-08 | **IN-FLIGHT (v1 baseline complete 2026-05-08)** — sub-session executed end-to-end: CAD generation with V26 fix-in-place (Codex centered=True off-by-half-width formula bug; pre-fix D1=22.35 mm, post-fix D1=0.35 mm exact); D1+D4 ground-truth verified; **D4 dual-advisor exercise = Outcome 2** (thin_wall_advisor fires critical at all levels, geometry_surgery silent — Codex's mapping wrong, V31); **A2 D1 = 4th V25 placeholder confirmation** (matched=True both orderings, hardcoded 1.0/0.0 fields); V-findings V26-V32 sourced (Codex CAD pattern + 3 rhoCentralFoam infrastructure findings + advisor extension + Codex mapping + Tier-1-source-availability); first density-based solver pipeline runs (rhoCentralFoam 5 ms physical, Cl=0.250 / Cd=0.054 — supersonic pocket M=1.18 captured at η=0.64 but lambda pattern unresolved at 48k cells). Reference profile: `.planning/case_profiles/case_006_onera_m6_transonic.md` |
| `case_007_kcs_ship_vof` | Free-surface ship hydrodynamics | 2 of 2 (round 1 hallucinated read-only-workspace; round 2 succeeded with clarification) | Tier-1-adjacent KRISO KCS (NMRI/Tokyo Workshop; URLs HTTP 200; bake-into-script license strategy) | D1 (0.35 mm rudder hub gap) + D8 (0.80 mm thin transom plate) | `methodology/kickoff/case_007_kcs_ship_vof.md` | 2026-05-08 | **DEFERRED** — single-fire. **Notable**: first multiphase case (interFoam + alpha.water + MULES). 5th consecutive A2-pending (overdetermined). D8 exercises landed thin_wall_advisor (consistency check vs case_004 D8). Round-1 Codex hallucination logged — RETRO addendum candidate (clarification preamble in future prompt template) |
| `case_008_glc305_irt_lagrangian` | External + Lagrangian (icing droplet impingement) | 1 of 2 (clarification preamble worked) | Tier-1 NASA IRT GLC305 (NOT NACA 0012; NTRS citations 20020061865) | D1 (0.35 mm root_mount_pad↔strut gap) + D8 (0.80 mm trailing_edge_tab_thin) | `methodology/kickoff/case_008_glc305_irt_lagrangian.md` | 2026-05-08 | **DEFERRED** — single-fire. **Notable**: first Lagrangian case (simpleFoam + kinematicCloud one-way). 6th consecutive A2-pending (unambiguous priority). D8 exercises landed thin_wall_advisor (3-case consistency: cases 004 + 007 + 008). Hard exclusion `NACA0012_not_used` honored explicitly |
| `case_009_sandia_flame_d` | Reacting low-Mach piloted jet flame | 1 of 2 (clarification preamble worked) | Tier-1 Sandia TUD Flame D (TNF Workshop CH4/air piloted jet, URL HTTP 200) | 2 defects per Codex manifest (likely D2 over-dense + auxiliary structure defect) on coflow plenum bracket / lip / shim, OUTSIDE z/D=7.5/15/30/45/60 measurement stations | `methodology/kickoff/case_009_sandia_flame_d.md` | 2026-05-08 | **DEFERRED** — single-fire. **Notable**: longest case in roster (12-16h, highest infra climb). First reacting case. **DRM-19 chemistry** primary (NOT GRI-Mech 3.0 hard exclusion); Westbrook-Dryer 2-step fallback. 5+ artifact extractions likely (chemkin loader + combustion thermo writer + species BC writer + combustion properties + mixture-fraction post-processor) |
| `case_010_drivaer_fastback_les` | External transient LES (vehicle aerodynamics) | 1 of 2 (clarification preamble worked) | Tier-1 TUM DrivAer fastback (smooth + mirrors + wheels; URL HTTP 200; license: TUM registration required, bake-into-script strategy) | D1 (0.35 mm mirror_edge_trim_strip gap) + D8 (sub-mm underbody_sensor_cover_thin between axles) | `methodology/kickoff/case_010_drivaer_fastback_les.md` | 2026-05-08 | **DEFERRED** — single-fire. **Notable**: first transient LES (pimpleFoam + WALE wall-modeled). 8th consecutive A2-pending (overdetermined). 4-case D8 consistency (cases 004 + 007 + 008 + 010). Hard exclusion `no_Ahmed_body_geometry: true` honored. Target Cd≈0.281. **FINAL CASE IN ORIGINAL ROSTER** — numerics-class root coverage complete |
| `case_011_plate_fin_compact_hx` | Multi-stream CHT (chtMultiRegionFoam steady, gas-turbine/APU air-air recuperator) | R0 design via 86gs gpt-5.5 xhigh (296k tok, 429 mid-emit) + R1 emit via CRS gpt-5.4 high (29k tok, clean exit) — total 2 rounds, well under cap=3 | Tier-3 parametric CadQuery (492 LOC, 3 fused regions: hot/cold/solid) | D8 (0.6 mm fin in rear-1/3 cold matrix · 7th cross-topology arc) + **D5 (30 μm separator_plate_3_4 offset · uncovered in 003-010 roster · marked [QUESTIONABLE 2026-05-08] pending A2-v2)** | `methodology/kickoff/case_011_plate_fin_compact_hx.md` | 2026-05-09 | **EXECUTED → ACTIVE v1** (sub-session 2026-05-09 Opus 4.7 1M ctx). v1 outcome: STEP byte-deterministic ✓, surfaces extracted ✓, D8 thin_wall_advisor PASS critical 7th-arc ✓, D5 A2 ALGORITHM_RUNS_CLEANLY [QUESTIONABLE 2026-05-08] = V25 4th confirmation ✓, sHM 980,618 cells with snap-quality cliff per V48 prediction, splitMeshRegions PARTIAL_FRAGMENTED (region_hot_fluid in 312 connected components per V50 advisor pre-prediction), chtMultiRegionFoam SKIPPED (broken mesh, honest evidence). **V47-V50 NEW + S22-S23 candidates + 2 stale-assumption fixes**. v2 will bump fin refinement to (3,4) per advisor recommendation. |
| `case_012_hvac_supply_diffuser` | Industrial HVAC delivery (buoyantSimpleFoam, 4-way ceiling diffuser commercial office) | R1 single-round emit via CRS gpt-5.4 high (118k tok, clean exit) | Tier-3 parametric CadQuery (248 LOC, single region_air + 4 louver vanes + 5 heat sources) | D1 (0.35 mm gap diffuser_face_plate ↔ ceiling · 9th D1 injection · [QUESTIONABLE 2026-05-08] pending A2-v2) + **D7 (louver_vane_2 rotated 38° · FIRST D7 injection · NO LANDED ADVISOR · advisor-gap V-finding triggered)** | `methodology/kickoff/case_012_hvac_supply_diffuser.md` | 2026-05-08 | **DISPATCHED — Phase 1 #2 close**. Direct 002a buoyantSimpleFoam inheritance (V3-V13, S1-S13). 6.0×4.5×3.0 m office, T_supply=16°C, U=2.6 m/s, 500 W internal heat (4 occupants + equipment). Predicted ADPI ≈85% (ASHRAE 55 / IEA Annex 20), throw distance ≈2.7 m, ΔT_ceiling-floor ≈3 K. CFD ADPI ±10 pp tolerance. **D7 first injection surfaces advisor-gap** → harvest 003 retro evaluates A4 face-orientation advisor candidate. Closes Phase 1; unblocks Phase 2 dispatch. |
| `case_013_centrifugal_pump_cavitating` | Confined rotating + phase-change (simpleFoam+MRF v1, cavitatingFoam+Schnerr-Sauer v2; industrial water-treatment pump) | R0 design via 86gs gpt-5.5 xhigh (125k tok, network disconnect mid-emit) + R1 emit via CRS gpt-5.4 high (69k tok, clean exit) — total 2 rounds, well under cap=3 | Tier-3 reference-derived CadQuery (412 LOC, single region_fluid + MRF cellZone + 6 backward-curved blades + spiral volute) cited Energies 2019 12(11) 2088 class | D1 (blade_5 tip-clearance 0.5→0.8 mm · 10th D1 injection · [QUESTIONABLE 2026-05-08]) + **D7 (blade_3 LE 22° wrong-normal · 2ND D7 injection · advisor-gap evidence accumulating)** | `methodology/kickoff/case_013_centrifugal_pump_cavitating.md` | 2026-05-08 | **DISPATCHED — Phase 2 #1**. First true industrial confined rotating machinery + first phase-change physics. Inherits case_004 MRF (V22-V24); cavitation pipeline NEW. N=2900 rpm, D2=250mm, Q_BEP=0.080 m³/s, H_BEP=35m, η=0.78, NPSHr_BEP=4.5m, NPSHr_0.8Q=3.5m. v1 head curve 4 points + v2 cavitation map at 0.8 Q_BEP. **2nd network-disconnect / quota fallback recovery** (after case_011) — pattern `[VALIDATED] 2-of-2`. Unblocks Phase 2 #2 (case_014). |
| `case_014_nasa_cc3_compressor_stage` | High-speed rotating + compressible (rhoSimpleFoam+MRF+cyclicAMI; NASA CC3 gold-standard turbomachinery) | R1 single-round via CRS gpt-5.4 high (148k tok, clean exit; 86gs skipped after case_011/013 fallback pattern) | Tier-1 NASA CC3 (NASA/TM-2013-216566 + AIAA 2013-3631; bake-into-script per case_006 strategy) | D1 (one blade tip-clearance +0.30 mm beyond 0.30 nominal = 0.60 mm · 11th D1 injection · [QUESTIONABLE 2026-05-08]) + **D8 (one blade LE 0.70 mm · 8th cross-topology arc data point · thin_wall_advisor [VALIDATED 6-of-6])** | `methodology/kickoff/case_014_nasa_cc3_compressor_stage.md` | 2026-05-08 | **DISPATCHED — Phase 2 #2 close**. Gold-standard turbomachinery validation. Combines case_004 MRF + case_005 compressible-RANS + case_013 confined-volute lessons. 15 main + 15 splitter blades, R_TE=215.5 mm, U_tip=492 m/s, 21,789 rpm, ṁ=4.54 kg/s, PR=4.0. v1 design point + v2 characteristic curve 5-7 points. First periodic-blade-row + cyclicAMI infrastructure for project. Closes Phase 2; unblocks Phase 3 (cases 015/016). |
| `case_015_vattenfall_t_junction_thermal_striping` | LES + CHT compound (chtMultiRegionFoam WALE; Vattenfall OECD/NEA T-junction; thermal striping fatigue) | R1 single-round via CRS gpt-5.4 high (160k tok, clean exit; section markers normalized by main session) | Tier-1 OECD/NEA Vattenfall benchmark (URLs cited; CSNI CFD spec + Vattenfall report) | **D5 (60 μm pipe-pipe weld interface misalignment · 2nd D5 injection after case_011 · [QUESTIONABLE 2026-05-08] pending A2-v2)** — single-defect case (complexity comes from LES+CHT compound) | `methodology/kickoff/case_015_vattenfall_t_junction_thermal_striping.md` | 2026-05-08 | **DISPATCHED — Phase 3 #1**. First compound numerics root (LES + CHT). Combines case_002b CHT + case_010 LES. Main pipe ID=140mm, branch ID=100mm, 90° T-junction, wall 6mm SS304. Cold ṁ=9.0 @ 19°C / hot ṁ=6.0 @ 36°C. WALE LES, wall-modeled y+ 30-100, dt=1e-4s, 10 thermocouples Tx10..Tx100, ≥10 flow-through FFT statistics. Reference: ±2K mean, ±0.5K RMS. Validates compound-root methodology before case_016 (compressible-DES). |
| `case_016_m219_cavity_des_acoustic` | Transient compressible DES + acoustic (rhoPimpleFoam + k-ω-SST IDDES + FW-H; M219 weapons-bay cavity) | R1 single-round via CRS gpt-5.4 high (228k tok, clean exit; **flagged + corrected request math error on time-window** — true 100-cycle R1 needs 0.75s not 0.1s) | Tier-1 M219 cavity (UK MOD; bake-into-script per case_006 strategy) | **D6 (10mm debris cube at (320,18,-79) · FIRST D6 INJECTION · advisor=NONE [QUESTIONABLE 2026-05-08])** + **D9 (16-facet LE+TE lip approximation · FIRST D9 INJECTION · advisor=NONE [QUESTIONABLE 2026-05-08])** | `methodology/kickoff/case_016_m219_cavity_des_acoustic.md` | 2026-05-08 | **DISPATCHED — Phase 3 #2 close**. First aeroacoustic capability for project. Second compound numerics root (compressible+DES; combines case_006 V26-V32 + case_010 V45-V46). M=0.85, U=290 m/s, T=273.15K, Re_L≈6e6. Cavity 508×102×102 mm. v1 min 0.12s + convergence 0.75s for true 100-cycle FFT; ESI-compatible BCs (V29 lesson). Published Rossiter modes 142/353/592/813 Hz at K09. **D6+D9 first injections consolidate advisor-gap V-findings** (with D7 from cases 012/013) → harvest 003 retro evaluates A4-A8 candidates. Closes Phase 3; unblocks Phase 4. |
| `case_017_pin_fin_electronic_heatsink` | Microscale CHT (chtMultiRegionFoam steady · 4-region: air+chip+TIM+heatsink; CPU/GPU/IGBT/EV-battery cooler) | R1 single-round via CRS gpt-5.4 high (157k tok, clean exit; section markers normalized) | Tier-3 parametric CadQuery; bank ID `A1` ORIGINAL pin-fin meaning (case_011 promoted A1 to compact HX; 017 re-anchors original) | D8 (4 corner pins thinned to 0.5 mm · 9th cross-topology arc data point · thin_wall_advisor [VALIDATED 6-of-6]) + **D9 (4 inboard corner-adjacent pins faceted to 10-sided · 2nd or 3rd D9 evidence)** | `methodology/kickoff/case_017_pin_fin_electronic_heatsink.md` | 2026-05-08 | **DISPATCHED — Phase 4 #1**. Microscale CHT with 4-region setup (TIM layer adds solid-solid conjugate; distinguishes from 002b 1-fluid-1-solid). Heatsink 50×50×5mm, chip 10×10×0.7mm Si, Al-6063 heatsink, k=4 W/m·K TIM. T_air_in=25°C, U=2-5 m/s, P_chip=50-100W, Re_pin≈300-400 laminar/transitional. T_chip target <85°C; R_θ ±15% per TIMA/IBM correlation. Component_bank.md split candidate: A1a (compact HX) + A1b (pin-fin heatsink). |
| `case_018_stairmand_cyclone_separator` | 3D swirl + Lagrangian (pimpleFoam + LaunderGibsonRSTM + kinematicCloud one-way; Stairmand high-efficiency cyclone) | R1 single-round via CRS gpt-5.4 high (139k tok, clean exit; section markers normalized) | Tier-1 Stairmand (public literature ratios baked into script) | **D6 (10-30 mm debris cube in collection chamber · 2ND D6 INJECTION after case_016 · advisor=NONE [QUESTIONABLE 2026-05-08])** — single-defect case (complexity comes from RSM + Lagrangian) | `methodology/kickoff/case_018_stairmand_cyclone_separator.md` | 2026-05-08 | **DISPATCHED — Phase 4 #2**. First 3D swirl-dominant separator + first RSM turbulence for project. Extends case_008 Lagrangian to cyclone topology. D=250mm Stairmand standard ratios (0.5/0.2/1.5/2.5/0.5/0.4 D); U_inlet=20 m/s, Re_D=3.3e5, swirl S~1-3. Particle 1-50 μm log-normal, ρ_p=2650 silica. d50 ±10%, η ±10-20% per Stairmand correlation. **2nd D6 advisor-gap evidence** consolidates. |
| `case_019_kenics_static_mixer` | Forced mixing + scalar transport (simpleFoam steady + passive scalar; 8-element Kenics helical static mixer) | R1 single-round via CRS gpt-5.4 high (183k tok, clean exit; section markers normalized) | Tier-3 fallback (Kenics literature ratios from Sulzer + ScienceDirect papers; no clean public STEP) | **D2 (element 3 over-dense triangulation 5k→80k tris · A3 advisor stress-test · [QUESTIONABLE V17] pending case_009 sediment)** — single-defect case | `methodology/kickoff/case_019_kenics_static_mixer.md` | 2026-05-08 | **DISPATCHED — Phase 4 #3**. Process-industry classic; extends case_003 to scalar transport. D=80mm pipe, 8 elements (L/D=1.5, 180° twist, 90° rotation between), upstream 3D + downstream 5D RTD zone. Re=3200 transitional; water, Sc_t=0.7. RTD F(t) + COV ≤ 0.05 + Z_static Δp correlation. **A3 cross-case stability data point** (3rd if case_009 lands clean). |
| `case_020_porous_media_filter_darcy_forchheimer` | Anisotropic porous resistance (simpleFoam + DarcyForchheimer fvOption; HEPA terminal filter cassette in HVAC housing) | R1 single-round via CRS gpt-5.4 high (117k tok, clean exit; section markers normalized) | Tier-3 parametric fallback (no Tier-1 ERCOFTAC porous-filter CAD found) | D9 (16-facet housing corner vs smooth R=18mm reference · 2nd or 3rd D9 evidence · advisor=NONE) + **D10 (1.0 mm slit at filter-frame corner · FIRST D10 INJECTION in project · advisor=NONE [QUESTIONABLE 2026-05-08])** | `methodology/kickoff/case_020_porous_media_filter_darcy_forchheimer.md` | 2026-05-08 | **DISPATCHED — Phase 4 #4 (FINAL CASE in 11-case batch)**. HEPA terminal filter; U_face=2.5 m/s, Re_housing≈3.3e4. Anisotropic Darcy-Forchheimer (streamwise < cross-stream). Δp ±10%, uniformity ±0.05, bypass flow % through D10. **D10 first injection closes defect-catalog gap analysis** (D3+D4 still uncovered; carry to next batch). **Triggers harvest cycle 003 full-mode** after sediment lands. |

## In-flight sub-sessions

Tracked in `case_index.md` as authoritative status. Cases with
`status: active` in `case_index.md` are running.

## Closed cases

Tracked in `case_index.md` "Closed threads" section.

## How to add a new entry to this queue

Main session, when ready to enqueue a new case:

1. Pick target solver-class from coverage map (HIGH priority row)
2. Pick CAD source preference:
   - Tier 1 (NASA CRM / ONERA M6 / NREL / etc.) if a published
     reference fits the solver-class
   - Tier 3 (Codex from-scratch) if no Tier 1/2 fits
3. Pick component bank preferred ID (if Tier 3) OR target public
   source (if Tier 1/2)
4. Pick 1-2 defect catalog IDs to inject
5. Write Codex prompt at
   `.planning/methodology/kickoff/case_<NNN>_<name>_codex_request.md`
6. Send via `codex-relay-with gpt-5.5 < <prompt-file>`
7. Receive Codex's response (5 deliverables); save at
   `kickoff/case_<NNN>_<name>_codex_response.md`
8. Validate per protocol §"Main session validation step"
9. If pass: write per-case kickoff at
   `kickoff/case_<NNN>_<name>.md` (template + Codex brief slot)
10. Add row to "Dispatched" section of this file with kickoff
    file pointer
11. Inform user: "case_<NNN> kickoff ready, paste into new Claude
    Code session"

If validation fails after 3 Codex rounds: escalate to user.

## Concurrency policy

Up to 4 sub-sessions in parallel (per `case_list.md` removed →
captured here):
- 1 active in-flight v.N optimization (e.g., case_002a)
- 1 fresh sub-session on a new solver-class
- 1 secondary on a different solver-class
- 1 reserved for high-priority custom user brief

Beyond 4, harvest cadence stalls.

## Why "queue" not "list"

The old `case_list.md` was a static enumerable list. This is
explicitly NOT that — it's a **queue** because:

- New entries arrive on-demand (main session asks Codex when
  coverage gap warrants)
- Order is dynamic (priority recalculated each turn based on
  what's covered)
- Items have lifecycle (queued → dispatched → in-flight → closed)
- The queue's contents are NEVER pre-allocated more than 1-2
  cases ahead — premature enqueueing wastes Codex compute

## Promotion: from "proposed" to "dispatched"

A queued case promotes to dispatched when:
1. Codex round-trip complete + 5 deliverables in repo
2. Main session validation pass (all 6 checks)
3. Per-case kickoff written
4. CAD adapter pipeline (if Tier 1/2 source) executed; STEP file
   in case-thread sandbox
5. User confirms ready to start sub-session

## Demotion: from "in-flight" to "queued for re-design"

A case can return to the queue if the sub-session reports the
geometry/brief is fundamentally unworkable (e.g., the component
chosen by Codex requires solver-class capability the project
doesn't support yet, surfaced only mid-run). Main session asks
Codex to revise.

This is rare — Tier 1 sources are validated; Tier 3 generation is
predictable. Most "broken" cases are recoverable with v2/v3 case
iterations within the sub-session, not by re-queuing.

## References

- `codex_case_design_protocol.md` — what Codex returns
- `component_bank.md` — Tier-3 from-scratch menu
- `public_cad_sources.md` — Tier 1+2 catalog
- `case_kickoff_prompt_template.md` — sub-session briefing template
- `case_index.md` — active/closed thread tracker (this queue is
  intake-side; case_index is execution-side)
- DEC-V61-198 — strategic philosophy SSOT
