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

| case_id | Solver class | Numerics class (Pattern 6 root) | Tier-1 candidate | Defect candidates | Industrial impact | Effort | Why this case |
|---|---|---|---|---|---|---|---|
| ~~case_005_rae_m2129_sduct~~ → **DISPATCHED** see Dispatched section below | | | | | | | |
| ~~case_006_onera_m6_transonic~~ → **DISPATCHED** see Dispatched section below | | | | | | | |
| ~~case_007_kcs_ship_vof~~ → **DISPATCHED** see Dispatched section below | | | | | | | |
| ~~case_008_irt_icing_lagrangian~~ → **DISPATCHED** see Dispatched section below | | | | | | | |
| ~~case_009_sandia_flame_d~~ → **DISPATCHED** see Dispatched section below | | | | | | | |
| ~~case_010_drivaer_les~~ → **DISPATCHED** see Dispatched section below | | | | | | | |

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
| `case_006_onera_m6_transonic` | External transonic 3D wing | 1 of 2 (no revision needed; **CRS gpt-5.4 high fallback** — 86gs xhigh 503'd) | Tier-1 NASA Glenn ONERA M6 (T1.A3; URL HTTP 500 persistent — same as case_005) | D1 (0.35 mm root-fairing gap) + D4 (0.18 mm tip-cap sliver) | `methodology/kickoff/case_006_onera_m6_transonic.md` | 2026-05-08 | **DEFERRED** — single-fire sequence. **Notable**: first density-based solver case (rhoCentralFoam + Kurganov + venkatakrishnan). 4th consecutive case A2-pending (compounded). D4 advisor mapping likely wrong (Codex→geometry_surgery, sub-session should try thin_wall_advisor first) — sub-session exercises judgment + sources V-finding either way. CRS fallback noted in retro queue |
| `case_007_kcs_ship_vof` | Free-surface ship hydrodynamics | 2 of 2 (round 1 hallucinated read-only-workspace; round 2 succeeded with clarification) | Tier-1-adjacent KRISO KCS (NMRI/Tokyo Workshop; URLs HTTP 200; bake-into-script license strategy) | D1 (0.35 mm rudder hub gap) + D8 (0.80 mm thin transom plate) | `methodology/kickoff/case_007_kcs_ship_vof.md` | 2026-05-08 | **DEFERRED** — single-fire. **Notable**: first multiphase case (interFoam + alpha.water + MULES). 5th consecutive A2-pending (overdetermined). D8 exercises landed thin_wall_advisor (consistency check vs case_004 D8). Round-1 Codex hallucination logged — RETRO addendum candidate (clarification preamble in future prompt template) |
| `case_008_glc305_irt_lagrangian` | External + Lagrangian (icing droplet impingement) | 1 of 2 (clarification preamble worked) | Tier-1 NASA IRT GLC305 (NOT NACA 0012; NTRS citations 20020061865) | D1 (0.35 mm root_mount_pad↔strut gap) + D8 (0.80 mm trailing_edge_tab_thin) | `methodology/kickoff/case_008_glc305_irt_lagrangian.md` | 2026-05-08 | **DEFERRED** — single-fire. **Notable**: first Lagrangian case (simpleFoam + kinematicCloud one-way). 6th consecutive A2-pending (unambiguous priority). D8 exercises landed thin_wall_advisor (3-case consistency: cases 004 + 007 + 008). Hard exclusion `NACA0012_not_used` honored explicitly |
| `case_009_sandia_flame_d` | Reacting low-Mach piloted jet flame | 1 of 2 (clarification preamble worked) | Tier-1 Sandia TUD Flame D (TNF Workshop CH4/air piloted jet, URL HTTP 200) | 2 defects per Codex manifest (likely D2 over-dense + auxiliary structure defect) on coflow plenum bracket / lip / shim, OUTSIDE z/D=7.5/15/30/45/60 measurement stations | `methodology/kickoff/case_009_sandia_flame_d.md` | 2026-05-08 | **DEFERRED** — single-fire. **Notable**: longest case in roster (12-16h, highest infra climb). First reacting case. **DRM-19 chemistry** primary (NOT GRI-Mech 3.0 hard exclusion); Westbrook-Dryer 2-step fallback. 5+ artifact extractions likely (chemkin loader + combustion thermo writer + species BC writer + combustion properties + mixture-fraction post-processor) |
| `case_010_drivaer_fastback_les` | External transient LES (vehicle aerodynamics) | 1 of 2 (clarification preamble worked) | Tier-1 TUM DrivAer fastback (smooth + mirrors + wheels; URL HTTP 200; license: TUM registration required, bake-into-script strategy) | D1 (0.35 mm mirror_edge_trim_strip gap) + D8 (sub-mm underbody_sensor_cover_thin between axles) | `methodology/kickoff/case_010_drivaer_fastback_les.md` | 2026-05-08 | **DEFERRED** — single-fire. **Notable**: first transient LES (pimpleFoam + WALE wall-modeled). 8th consecutive A2-pending (overdetermined). 4-case D8 consistency (cases 004 + 007 + 008 + 010). Hard exclusion `no_Ahmed_body_geometry: true` honored. Target Cd≈0.281. **FINAL CASE IN ROSTER** — coverage matrix complete |

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
