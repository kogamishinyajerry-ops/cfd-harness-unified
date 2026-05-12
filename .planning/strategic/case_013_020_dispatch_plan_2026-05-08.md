# Case 013-020 Dispatch Plan

> **Status**: planning · 2026-05-08 evening
> **Author**: main session (post case_011 dispatch + case_012 codex_request prepared)
> **Trigger**: user "继续规划后续的 case" (no new compute)
> **Parent SSOT**: `.planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md`
> **Companion**: `.planning/methodology/kickoff/case_012_codex_request.md`
> **Scope**: dispatch order, dependencies, blockers, per-case readiness criteria for cases 013-020. Codex requests are NOT pre-written for these — speculative request files would rot before use because each case's design is shaped by preceding-case sediment.

## §1 · Dispatch order + dependencies

```
                       ┌─────────────────────────────────────┐
                       │ case_011 (dispatched 2026-05-08)    │
                       │ ↓ awaiting sub-session sediment      │
                       └─────────────────────────────────────┘
                                       ↓
                       ┌─────────────────────────────────────┐
                       │ case_012 (codex_request READY)      │
                       │ ↓ awaiting user "go"                 │
                       └─────────────────────────────────────┘
                                       ↓
                          [Phase 1 close · harvest cycle]
                                       ↓
                       ┌─────────────────────────────────────┐
                       │ A2-v2 sub-DEC must land first       │
                       │ (drafted at draft_a2_v2_*.md)        │
                       └─────────────────────────────────────┘
                                       ↓
                  ┌────────────────────┴────────────────────┐
                  ↓                                          ↓
       ┌────────────────────┐                    ┌────────────────────┐
       │ case_013           │                    │ case_014           │
       │ centrifugal pump   │ ←  parallelizable  │ centrifugal        │
       │ + cavitation       │                    │ compressor stage   │
       └────────────────────┘                    └────────────────────┘
                  ↓                                          ↓
                          [Phase 2 close · harvest cycle]
                                       ↓
                  ┌────────────────────┴────────────────────┐
                  ↓                                          ↓
       ┌────────────────────┐                    ┌────────────────────┐
       │ case_015           │                    │ case_016           │
       │ T-junction LES+CHT │  parallelizable    │ M219 cavity DES    │
       │                    │                    │ + acoustic         │
       └────────────────────┘                    └────────────────────┘
                  ↓                                          ↓
                          [Phase 3 close · harvest cycle]
                                       ↓
       ┌──────────────────────────────────────────────────────────┐
       │ case_017 / 018 / 019 / 020 (parallelizable, 4 short cases) │
       └──────────────────────────────────────────────────────────┘
                                       ↓
                              [Phase 4 close · harvest 003]
```

**Critical path (sequential)**:
- case_011 → case_012 → A2-v2 land → Phase 2

**Within-phase parallelization**: Phase 2 (013/014), Phase 3
(015/016), Phase 4 (017-020) are designable in parallel but
**should sediment one-at-a-time** to extract Pattern 6 / V-series
findings cleanly. "Parallelizable" means Codex can design 013 and
014 in two close-together rounds; sub-sessions still run
sequentially.

## §2 · Hard blockers

### Blocker B1: A2-v2 sub-DEC must land before case_013 dispatch

- **Why**: case_013 D1 = impeller tip clearance gap (0.1-0.5 mm
  typical industrial spec). Without A2-v2's `inter_face_gap_mm`
  field, D1 verification on case_013 produces yet another
  algorithm-runs-cleanly evidence (V25 placeholder), accumulating
  more `[QUESTIONABLE]` markers without resolving any. Pump tip
  clearance is **performance-critical** (head curve, NPSH); the
  CFD case loses engineering value if defect verification can't
  field-validate the actual gap distance.
- **A2-v2 draft location**: `.planning/patches/draft_a2_v2_gap_detection_2026-05-08.md`
- **Estimated effort**: 4-6h sub-DEC implementation + Codex
  review + sediment
- **Recommended sequencing**: land A2-v2 between case_012
  sediment and case_013 dispatch. A2-v2 also retroactively
  upgrades V25 + relevant `[QUESTIONABLE]` markers on case_005,
  case_006, case_011 D1/D5 evidence.

### Blocker B2: case_011 multi-stream CHT learnings should inform case_015 LES+CHT

- **Why**: case_015 (T-junction LES+CHT) combines case_002b CHT +
  case_010 LES. case_011 multi-stream sediment will surface the
  multi-region cellZone bookkeeping pattern (V-finding candidates
  per case_011 kickoff §"Six per-case standard moves" item 2).
  Case_015 design benefits from those V-findings being indexed
  before its dispatch.
- **Soft blocker**: case_015 dispatch can technically proceed
  without case_011 sediment, but Codex round-cap=3 efficiency
  drops because Codex will rediscover the same multi-region
  bookkeeping issues case_011 already surfaced.
- **Recommended sequencing**: case_011 sub-session sediment →
  V-series append → case_015 design.

### Blocker B3: case_009 D2 evidence informs A3-v2 priority

- **Why**: A3 redundancy gap (V17 open) was sourced by case_005
  v1 but is intentionally untested in cases 006-011. case_009
  D2 (over-dense triangulation in coflow plenum) is the
  scheduled re-test. If A3 pattern is reproduced on 009, A3-v2
  becomes a higher-priority sub-DEC; if not reproduced, V17
  status updates without v2 patch.
- **Affects**: case_019 (Kenics static mixer) defect choice.
  case_019 is currently planned with D2 (over-dense mixer
  element triangulation) — if A3 is unstable, case_019 may need
  A3-v2 first OR switch to a different defect.
- **Soft blocker**: case_019 is Phase 4, so this resolves
  naturally during Phase 2-3 cycle.

### Blocker B4 (optional): D7 advisor depending on case_012 outcome

- **Why**: case_012 introduces D7 (wrong-normal louver). No
  LANDED advisor for face-orientation defects. Post-case_012
  retro evaluates whether D7 advisor is worth a sub-DEC. If
  case_016 (cavity walls) and case_020 (filter shell) also
  inject D7, advisor becomes high-priority.
- **Affects**: case_016, case_020 readiness if D7 advisor is
  desired before dispatch.
- **Recommended sequencing**: defer D7 advisor sub-DEC until
  3+ cases have surfaced D7 patterns (case_012 + 016 + 020 if
  all inject).

## §3 · Per-case dispatch readiness

### case_013 · Centrifugal pump impeller + volute + cavitation

| Field | Value |
|---|---|
| **Solver** | `simpleFoam` + MRF (inherits 004) → `interPhaseChangeFoam` or `cavitatingFoam` for cavitation extension |
| **Numerics class** | incompressible-MRF-cavitating (NEW root) |
| **Tier-1 source** | ERCOFTAC centrifugal pump test case OR Pumpkit benchmark |
| **Defects** | D1 (impeller tip clearance gap, 0.1-0.5 mm) + D7 (CAM blade leading-edge wrong-normal) |
| **Effort** | 12-15h |
| **APU leverage** | MRF infrastructure from 004 reused; cavitation phase-change is NEW |
| **Blocker readiness** | ❌ A2-v2 must land first (B1) |
| **Risk** | High — first phase-change physics for project; cavitation BC pathology potential. Round cap=3 may need full usage. |
| **Pre-dispatch checklist** | (1) A2-v2 landed + V25 retroactively upgraded; (2) case_004 v2 sediment landed (CFD pipeline complete, MRF infrastructure validated); (3) `cavitationProperties.j2` template scaffold candidate identified |

### case_014 · Centrifugal compressor stage (NASA CC3)

| Field | Value |
|---|---|
| **Solver** | `rhoSimpleFoam` + MRF (combines 004 + 005) |
| **Numerics class** | compressible-RANS-MRF (NEW root) |
| **Tier-1 source** | NASA CC3 compressor stage (publicly fully-documented; URL pattern same as 005/006 — expect HTTP 500 transient, plan caching strategy) |
| **Defects** | D1 (tip clearance critical, 0.2-0.5 mm) + D8 (thin blade leading edge, 0.6-0.8 mm) |
| **Effort** | 14-18h (longest in roster) |
| **APU leverage** | Combines 004 MRF + 005 compressible-RANS infrastructure |
| **Blocker readiness** | ❌ A2-v2 must land (B1) · case_004 + case_005 v2 sediment recommended for full inheritance |
| **Risk** | High — first turbomachinery for project; periodic boundary conditions + total-total reference state are new. Tip-leakage capture grid sensitivity may force v3+. |
| **Pre-dispatch checklist** | (1) A2-v2 landed; (2) case_004 v2 sediment (MRF clean); (3) case_005 v2 sediment (compressible BC patterns); (4) Codex prompt explicitly asks for **periodic blade-row** boundary handling |

### case_015 · T-junction thermal striping (LES + CHT)

| Field | Value |
|---|---|
| **Solver** | `chtMultiRegionFoam` + LES variant OR `buoyantPimpleFoam` + LES (combines 002b + 010) |
| **Numerics class** | incompressible-LES-CHT (NEW root) |
| **Tier-1 source** | Vattenfall T-junction (OECD/NEA benchmark, well-documented; URL accessible per public benchmark archive) |
| **Defects** | D5 (pipe-pipe weld interface mis-alignment, 30-100 μm — real welding tolerance) |
| **Effort** | 12-15h |
| **APU leverage** | 002b CHT + 010 LES, both inherited; multi-region LES coupling is NEW |
| **Blocker readiness** | ❌ A2-v2 must land for D5 (same as case_011 D5 pattern) · ⚠️ case_011 sediment helpful (B2) · ⚠️ case_010 sediment helpful (LES infrastructure) |
| **Risk** | Medium-High — first compound numerics root (LES + CHT). Long-time statistic sample size + LES-side T-residual oscillation are new pathology vectors. |
| **Pre-dispatch checklist** | (1) A2-v2 landed; (2) case_011 multi-region cellZone V-findings indexed; (3) case_010 v1+v2 LES infrastructure indexed (or at least case_010 v1 sediment); (4) Codex prompt asks for explicit **wall-T spectrum sampling rate** + **time-window length sufficiency check** |

### case_016 · Aircraft cavity DES + acoustic

| Field | Value |
|---|---|
| **Solver** | `rhoPimpleFoam` + DDES (combines 006 + 010) |
| **Numerics class** | compressible-DES (NEW root) |
| **Tier-1 source** | M219 cavity (UK MOD public data complete) OR NASA cavity dataset |
| **Defects** | D6 (debris in cavity, **uncovered** in 003-011) + D9 (faceted curved walls, **uncovered** in 003-011) |
| **Effort** | 12-14h |
| **APU leverage** | 006 compressible-shock + 010 LES inherited; DDES + FW-H acoustic is NEW |
| **Blocker readiness** | ⚠️ case_006 sediment helpful (rhoCentralFoam → rhoPimpleFoam infrastructure adjacent) · ⚠️ case_010 sediment helpful (LES → DES) |
| **Risk** | High — first aeroacoustic for project. Tonal-noise capture vs grid + FW-H surface placement are new pathology vectors. Boundary acoustic reflection requires non-reflective BC infrastructure. |
| **Pre-dispatch checklist** | (1) case_006 v1 baseline complete (already done); (2) case_010 v1 sediment recommended for LES infrastructure; (3) Codex prompt asks for explicit **FW-H control surface** definition + **non-reflective BC** at far-field; (4) D6 and D9 first injections in project — flag for post-case_016 retro to evaluate advisor-gap |

### case_017 · Pin-fin electronic heatsink

| Field | Value |
|---|---|
| **Solver** | `chtMultiRegionFoam` + low-Re air at chip scale (extends 002b to microscale) |
| **Numerics class** | chtMultiRegionFoam at chip scale (extends 002b — partial inheritance, scale shift μm) |
| **Tier-1 source** | TIMA Lab benchmarks / IBM thermal data |
| **Defects** | D8 (thin pin walls, 0.3-0.6 mm — already 6-validated as `[VALIDATED]` so this is consistency check) + D9 (faceted fin curvature) |
| **Effort** | 8-10h (Phase 4 single-case) |
| **APU leverage** | 002b CHT + case_011 multi-stream patterns directly applicable; scale shift is the NEW element |
| **Blocker readiness** | ⚠️ case_011 sediment helpful (multi-stream CHT machinery) · scale shift to chip-microscale may surface new V-findings |
| **Risk** | Low-Medium — well-trodden electronic-cooling territory. Component A1 bank entry directly maps. |
| **Pre-dispatch checklist** | (1) case_011 v1+v2 sediment recommended; (2) component_bank.md A1 entry refined to "compact heat exchanger / electronic heatsink" sub-categories per case_011 promotion; (3) Codex prompt asks for explicit **microscale Re check** (Re_pin typically 10²-10³, may be laminar or transitional) |

### case_018 · Cyclone separator (3D swirl + Lagrangian)

| Field | Value |
|---|---|
| **Solver** | `pimpleFoam` + kinematicCloud (extends 008 to swirl-dominant) |
| **Numerics class** | incompressible-RANS-Lagrangian-swirl (extends 008) |
| **Tier-1 source** | Stairmand / Lapple cyclone (industry standard geometries with documented η(d_p) curves) |
| **Defects** | D6 (debris in collection chamber, **second D6 injection** if 016 already done; otherwise first) |
| **Effort** | 10-12h |
| **APU leverage** | 008 Lagrangian infrastructure inherited; swirl-dominant flow + cyclone d50 cut-off curves are NEW |
| **Blocker readiness** | ⚠️ case_008 v2 sediment helpful (Lagrangian CFD pipeline complete; v1 only landed advisor-validation) |
| **Risk** | Medium — RSM turbulence model recommended for high-swirl (k-ε under-predicts vortex core). |
| **Pre-dispatch checklist** | (1) case_008 v2 sediment landed (kinematicCloud full pipeline); (2) Codex prompt asks for **RSM vs k-ε** turbulence-model selection rationale + **swirl number** documentation; (3) η(d_p) reference curve documented (Stairmand or Lapple) |

### case_019 · Static mixer (Kenics / Sulzer)

| Field | Value |
|---|---|
| **Solver** | `simpleFoam` + scalar transport (extends 003) |
| **Numerics class** | incompressible-RANS + scalar (extends 003) |
| **Tier-1 source** | Sulzer Chemtech public material / academic LES literature |
| **Defects** | D2 (over-dense mixer-element triangulation, 50k-100k tris per element) — A3 stress-test, depends on B3 resolution |
| **Effort** | 8h (shortest in roster) |
| **APU leverage** | 003 incompressible-RANS infrastructure directly inherited; scalar transport (mixing index) is NEW |
| **Blocker readiness** | ⚠️ B3 — A3 evidence from case_009 D2 outcome should resolve before 019 dispatch |
| **Risk** | Low — well-trodden territory. RTD (residence time distribution) + COV (coefficient of variation) are clean engineering KPIs. |
| **Pre-dispatch checklist** | (1) case_009 v1+v2 sediment landed (D2 → A3 outcome documented); (2) if A3-v2 needed, A3-v2 sub-DEC landed before 019; (3) Codex prompt asks for explicit **scalar transport BC** (Robin / Dirichlet inlet for tracer) |

### case_020 · Porous-media filter (Darcy-Forchheimer)

| Field | Value |
|---|---|
| **Solver** | `simpleFoam` + porous source term (extends 003) |
| **Numerics class** | incompressible-RANS + Darcy-Forchheimer (extends 003) |
| **Tier-1 source** | ERCOFTAC porous-media benchmarks |
| **Defects** | D9 (porous-zone surface tessellation, **uncovered** if 016 hasn't injected D9 yet) + D10 (open shell at filter edge, **uncovered** in 003-011) |
| **Effort** | 8h |
| **APU leverage** | 003 inherited; porous source term + anisotropic resistance tensor is NEW |
| **Blocker readiness** | ⚠️ B4 — D7 advisor decision may inform whether D9/D10 advisors are also needed |
| **Risk** | Low-Medium — porous source terms are well-documented; D9 + D10 first injections may surface new advisor-gap V-findings. |
| **Pre-dispatch checklist** | (1) case_011 v1 sediment recommended (CHT + multi-region patterns adjacent to porous-zone definition); (2) Codex prompt asks for explicit **Darcy-Forchheimer coefficient sourcing** (literature value vs derived from pressure-drop curve); (3) D9 + D10 first injections in project — flag for post-case retro |

## §4 · Suggested dispatch cadence

Assuming user dispatches one Codex case per session and sub-session
runs in between:

| Sequence | Case | Prerequisite | Estimated calendar |
|---|---|---|---|
| 1 | case_011 sub-session | Codex sediment landed | done dispatch; awaiting compute |
| 2 | case_012 Codex round | (none — request ready) | next dispatch slot |
| 3 | case_012 sub-session | case_012 kickoff written | after case_012 Codex pass |
| 4 | A2-v2 sub-DEC implementation | (parallel to 1-3 if user prioritizes) | bench-side, no Codex |
| 5 | Phase 1 harvest cycle | cases 011 + 012 v1 sediment | full-mode harvest |
| 6 | case_013 Codex round | A2-v2 landed + Phase 1 harvest | after step 4 + 5 |
| 7 | case_014 Codex round | (parallel to 6, design only) | after step 6 |
| 8 | case_013 + 014 sub-sessions | sequential, not parallel | after step 6/7 |
| 9 | Phase 2 harvest cycle | 013 + 014 sediment | full-mode harvest |
| 10 | case_015 + 016 design + sub-session | Phase 2 close | similar pattern |
| 11 | Phase 3 harvest cycle | 015 + 016 sediment | full-mode harvest |
| 12 | case_017 / 018 / 019 / 020 design + sub-session | Phase 3 close | parallelizable design, sequential sediment |
| 13 | Phase 4 harvest cycle = harvest 003 | all 10 industrial-extension cases sedimented | major retro |

**Notes on cadence**:
- "Calendar" deliberately omitted (per "禁用日期/调度门控" rule); above is dependency order, not date plan.
- User can prioritize A2-v2 implementation in parallel with case_012 sub-session — those are independent.
- If a Codex round hits round-cap=3 without converging, the case parks; remaining cases not blocked.

## §5 · Codex request preparation strategy

For cases 013-020, Codex requests will be written **just-in-time**
when their dispatch becomes the next priority. Reasons:

1. **Sediment-informed design**: each case's hard constraints
   should reflect findings from preceding cases. Pre-writing all
   8 requests now would force re-revision after case_011/012/etc
   sediment.
2. **Round-cap efficiency**: Codex round 1 succeeds when the
   request includes precise risk pre-emptions (e.g., V25 marker
   on D1, V13 fallback note on solver, etc.). Pre-emptions need
   to be sourced from current V-series, not stale.
3. **A2-v2 / D7 advisor / D9 advisor decisions** are pending and
   will affect case_013/016/020 request content.

Recommended pattern:
- After case_012 sediment + A2-v2 land: write case_013 + case_014
  requests in one batch (Phase 2 design parallel)
- After case_014 sediment: write case_015 + case_016 requests
- After case_016 sediment: write case_017-020 requests (Phase 4
  parallelizable)

## §6 · Strategic-doc updates triggered by this plan

1. `case_011_020_industrial_extension_roadmap_2026-05-08.md` —
   no changes; this dispatch plan is downstream of it
2. `INDEX.md` — add reference to this dispatch plan under
   "Reference / strategic documents"
3. `case_proposal_queue.md` — case_012 row will move to
   Dispatched after case_012 Codex round completes

## §7 · Open questions / decisions deferred

- **Q1**: Should A2-v2 sub-DEC implementation be Codex-led
  (codegen) or main-session-led (Opus 4.7 single-flight)?
  Decision deferred to user; recommended Opus single-flight
  given the patch is ~185 LOC well-scoped.
- **Q2**: Do we batch Phase 4 (017-020) as 4 parallel Codex
  rounds, or one-at-a-time? Decision deferred until Phase 3
  closes; depends on remaining round-cap budget.
- **Q3**: Is there a case worth promoting from Phase 4 to Phase
  3 (e.g., case_017 electronic heatsink could be high-leverage
  given case_011 + case_002b CHT prep)? Decision deferred to
  Phase 2 close retro.

## §8 · TL;DR

- **Next dispatch**: case_012 Codex round (request file ready;
  awaiting user "go").
- **Hard blocker**: A2-v2 sub-DEC must land before case_013.
- **Phase 1 close trigger**: cases 011 + 012 v1 sediment.
- **Phase 2 (013+014)**: parallel design, sequential sediment.
- **Phase 3 (015+016)**: parallel design, sequential sediment.
- **Phase 4 (017-020)**: 4 short cases, parallelizable design.
- **Codex request strategy for 013-020**: just-in-time (not
  pre-written) so each request inherits preceding-case
  sediment.
- **Companion files**:
  - `methodology/kickoff/case_012_codex_request.md` (READY)
  - `patches/draft_a2_v2_gap_detection_2026-05-08.md` (READY,
    awaiting implementation)
