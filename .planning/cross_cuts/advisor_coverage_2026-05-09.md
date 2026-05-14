# Advisor coverage matrix · 2026-05-09 (harvest 003 full-mode)

> **Snapshot**: harvest cycle 003. Supersedes `advisor_coverage_2026-05-08.md`
> for current-state view. Two new sediments (case_011, case_012) +
> 8 dispatched-deferred (case_013-020). Pre-emptive priority scoring
> for the advisor extraction queue based on compounded evidence
> across landed sediment AND dispatched manifests.

## Landed advisors (in `ui/backend/services/geometry_ingest/`)

| File | Advisor | Sediment evidence | Verdict |
|---|---|---|---|
| `geometry_surgery.py` (205 LOC) | A3 — decimate-by-tier + axial stretch | case_005 v1 PARTIAL (V17 scope-narrow on D2 redundancy) | scope-expansion sub-DEC arc opened (low priority — single-instance) |
| `thin_wall_advisor.py` (210 LOC) | V10 advisor — bbox-min vs cell-size | case_002a/b origin + 7-topology cross-topology arc PASS (case_003/004/006/007/008/010/011) | **[VALIDATED]** — most robust advisor in stack; case_011 V48/V50 demonstrates pre-mesh PASS correctly predicts post-mesh sHM struggle |
| `virtual_interface_detector.py` (~290 LOC post-A2-v2) | A2 v1 + A2-v2 — V2-pattern shared-interface detection + D1-class gap-defect classifier | 10-of-10 cross-topology PASS (case_003/004/005/006/007/008/009/010/011/012); v1 placeholder-semantic closed by A2-v2 | **A2-v2 LANDED 2026-05-12 (DEC-V61-198-sub-A2v2)** — `inter_face_gap_mm` + `perpendicular_distance` + `should_have_been_shared_with_unintended_gap` classifier; 18-test suite green; V25 closed; V22/V33/V36/V42/V43/V50 [QUESTIONABLE 2026-05-08] markers field-validated |
| `stl_loader.py` / `patch_detector.py` / `health_check.py` | Utilities | All cases reuse | (utility, not advisory) |

## Pending advisor extractions (priority-scored for harvest 003)

| Artifact | Trigger source | Compounded count (sediment + dispatched) | Score = N × HIGH / LOC | Priority |
|---|---|---|---|---|
| **A2-v2** — gap-distance API + classifier | V25 (closed 2026-05-12 by DEC-V61-198-sub-A2v2) | **LANDED** | 174 LOC source+test; under 250 sub-DEC ceiling | **DONE — was #1; closed by Claude Code main session 2026-05-12** |
| **A6** — `hvac_adpi.py` ADPI/throw/dumping post-processor | case_012 v1 sediment | 1 sediment + N dispatched (012/015 likely) | 1 × MED / 150 LOC = LOW | DEFER until 2nd HVAC-class case |
| **A7** — `step_canonicalizer.py` | V80 (case_012 backfill 2026-05-13 + cross-cuts case_002a / case_005 / case_011) | **4 sediment · LANDED 2026-05-12** | ~115 LOC source + 10-test suite | **DONE — was #3; closed by Claude Code main session 2026-05-12 by DEC-V61-198-sub-A7** |
| **A8** — `shm_dict_validator.py` | V52 (case_012 typo) + V86 (case_011 features-list orphan) sedimented 2026-05-09 · **widened V99 (case_003 v2 STL/patchInfo.type cross-consistency) + V100 (case_003 v2 entry-point type-guard) 2026-05-14** | **4 sediment · LANDED-with-widening 2026-05-14** | ~380 LOC source + 13-test suite (0.06s) | **DONE-with-widening — closes V52 + V86 + V99 + V100 markers; 7 detection paths (was 5): (a) missing_emesh_file · (b/b') missing_geometry_ref+geometry_orphan · (c) missing_region_ref · (d) typo_suspicion · (a') orphaned_emesh_feature · (e) `multi_normal_constrained_patch` via STL face-normal × patchInfo.type cross-check (V99 widening · `_CONSTRAINED_PATCH_TYPES = {symmetryPlane, wedge, empty, cyclic, cyclicAMI}`) · (f) entry-point `isinstance(parsed_dict, dict)` TypeError guard (V100 widening). M-A8 Tier 2 milestone met (DEC-V61-198-sub-A8); M-A8-WIDEN widening milestone met (DEC-V61-198-sub-A8-widening-V99-V100); mesh-debug-loop axis bottleneck on capability radar v2 closed → radar v3 left half-axis re-paint expected ≥7.20 (main session reconciles ARC-GOAL §B19+).** |
| **A4** — face-orientation advisor | V79/case_012 + V87/case_013 sedimented 2026-05-13 | **2 sediment · LANDED 2026-05-13** | ~260 LOC source + 9-test suite | **DONE — closes V79 + V87 [QUESTIONABLE] markers; M-A4 Tier 1 milestone met (DEC-V61-198-sub-A4-face-orientation-advisor)** |
| **A5** — `inlet_outlet_validator.py` | V81 (case_012 backfill 2026-05-13) closure | 1 sediment + 6 dispatched at risk · **LANDED 2026-05-13** | ~210 LOC source + 9-test suite | **DONE — closes V81 partial; M-V81 milestone met (DEC-V61-198-sub-A5-inlet-outlet-validator)** |
| **A10** — `thermo_polynomial_range_advisor.py` | V41 (case_009 v1 channel-(b) gap, V91-flagged) + V93 (case_009 v1.5 codified rule, paired before/after) sedimented 2026-05-14 | **paired before/after on case_009 v1+v1.5 · LANDED 2026-05-14** | ~410 LOC source + 14-test suite (0.03s) | **DONE — closes V41 [QUESTIONABLE]→[VALIDATED] + codifies V93 pre-ignition T-floor rule; M-A10 Tier 1 milestone met (DEC-V61-198-sub-A10); promotion gate loosening from "2 independent reacting cases" to "paired before/after on ≥ 1 case OR 2 independent cases" per session 5 retro §4 + §9** |
| **A1** — `cad_ingest_freecad.py` (CATIA + unit-context) | V1, V20, V24 | 3 sediment | 3 × MED / 100 LOC = MED | DEFER until A2-v2 lands (queued) |
| **D6_advisor** (extra-body-in-fluid) | case_016 + case_018 dispatched · case_016 V55 sediment 2026-05-11 | **1 sediment + 1 dispatched** | speculative · spec drafted | DEFER until case_018 sediment · spec: `methodology/advisor_candidates_a4_a8.md` |
| **D9_advisor** (over-aggressive simplification) | case_016 + case_017 + case_020 dispatched · case_016 V56 sediment 2026-05-11 | **1 sediment + 2 dispatched** | speculative · spec drafted | DEFER until 2-of-3 sediment · spec: `methodology/advisor_candidates_a4_a8.md` |
| **D10_advisor** (open-shell beyond watertight) | case_020 dispatched | 0 sediment + 1 dispatched | speculative · spec drafted | DEFER · spec: `methodology/advisor_candidates_a4_a8.md` |
| **Codex CAD inlet/outlet protocol amendment** | V81 (case_012 backfill 2026-05-13) | 1 sediment + 6 dispatched at risk · **LANDED 2026-05-12** | governance amendment + V81 row | **DONE — was #2; protocol amended 2026-05-12 by DEC-V61-198-sub-protocol-inlet-outlet · A8 auto-validator deferred** |

## Loop closure check on advisor priorities (harvest 002 → harvest 003)

Harvest 002 said:
- A2-v2: "drafted, top-1 this cycle, OVERDETERMINED"
- A1 + unit-context: "compounded 3-instance, queued behind A2-v2"

Harvest 003 reality (1 sub-session cycle later):
- A2-v2: **STILL DRAFTED, NOT LANDED**. Compounded evidence grew from 5 → 15 (10 sediment + 5 dispatched). Now blocking 17 [QUESTIONABLE 2026-05-08] markers across 11 case kickoffs from upgrading.
- A1: still pending; harvest 003 surfaces no new pressure.
- A6: still drafted (deferred to 2nd HVAC-class case); A7 LANDED 2026-05-12; A8 LANDED 2026-05-14 (V52+V86 cross-topology pair met promotion gate).

**Loop-closure verdict**: top-1 actionable from harvest 002 did NOT land. This is the harvest 003 #2 (re-list as compounded escalation).

## D8 / thin_wall_advisor consistency arc — 8 cross-topology (post case_011)

| Case | D8 dimension | Industrial topology | Outcome |
|---|---|---|---|
| case_002a/b | (origin) | curved CATIA Frame | LANDED |
| case_003 | 0.80 mm | planar CadQuery box | PASS · field-validated |
| case_004 | 0.75 mm | rotating-machinery shim | PASS (V23) |
| case_006 | 0.18 mm | extreme-thinness sliver | PASS (V30) |
| case_007 | 0.80 mm | ship transom plate | PASS (V33-V35) |
| case_008 | 0.80 mm | airfoil TE tab | PASS (V37) |
| case_010 | sub-mm | vehicle underbody plate | PASS (V44) |
| **case_011** | **0.60 mm** | **HX cold fin (NEW topology)** | **PASS · pre-mesh advisor warning empirically validated by V48 sHM struggle** |

**8-case [VALIDATED]** at this point. Pending: case_014 D8 (compressor blade LE 0.70 mm) and case_017 D8 (pin-fin 0.5 mm). At 9-10 successful cross-topology PASSes the advisor enters "do-not-touch" stability tier.

## Defect-catalog distribution observed (post 11-case dispatch)

| Defect | Cases targeting | Advisor mapping | Notes |
|---|---|---|---|
| D1 (sub-mm gap) | 003-008/010/012/013/014 = **11×** | A2 v1 (placeholder per V25) | Over-saturated; A2-v2 will rebalance |
| D2 (over-dense) | 005, 019 = 2× | A3 (LANDED) | OK distribution |
| D3 (non-manifold shared face) | **0× UNCOVERED** | (none) | Carry to next batch |
| D4 (sliver) | 006 = 1× | A3 (likely wrong; V31) | **0× UNCOVERED** beyond case_006; carry to next batch |
| D5 (mis-aligned shared face) | 011, 015 = 2× | A2 + sub-µm extension (none) | First D5 in case_011 v1 sediment |
| D6 (extra body in fluid) | 016, 018 = 2× | NONE | Phase 3-4 dispatched-deferred |
| D7 (face-orientation) | 012, 013 = 2× sedimented 2026-05-13 | **A4 LANDED 2026-05-13** (DEC-V61-198-sub-A4) | V79 + V87 closed; both regressions pinned in 9-test suite |
| D8 (thin shell) | 002b/003/004/007/008/010/011/014/017 = **9×** | thin_wall_advisor [VALIDATED] | Strongest arc |
| D9 (over-simplification) | 016, 017, 020 = 3× | NONE | Phase 3-4 dispatched-deferred |
| D10 (open shell) | 020 = 1× | health_check (LANDED, watertight check) | Deeper open-shell pattern beyond watertight |

**Catalog gap**: D3 + D4 still uncovered after the 11-case batch. Recommend Codex case-design protocol amendment to seed D3 + D4 in the next batch.

## A2-v2 patch readiness check (cross-link to harvest 003 #1 + #2)

`.planning/patches/draft_a2_v2_gap_detection_2026-05-08.md` — exists, drafted, scope ~185 LOC (under 250 cap). User has not ratified.

If main session lands A2-v2:
- Backfill sweep mode triggers — all 10 sediment-confirmed [QUESTIONABLE 2026-05-08] markers can be re-evaluated; expect ~6-8 to upgrade to [VALIDATED] or [REFUTED] depending on actual gap-distance measurements
- Cases 013-020 sub-sessions get cleaner V-finding signal (advisor reports gap distance, not just matched=True placeholder)
- A6/A7/A8 land in Phase 2 alongside

## References

- `.planning/methodology/component_bank.md` — defect catalog SSOT
- DEC-V61-198 — 5-artifact extraction list
- `.planning/patches/draft_a2_v2_gap_detection_2026-05-08.md` — A2-v2 drafted patch (top-1 unresolved)
- `.planning/patches/draft_a6_adpi_post_processor_2026-05-09.md` — case_012 A6 candidate
- `.planning/patches/draft_a7_step_canonicalizer_2026-05-09.md` — case_012 A7 candidate (4-case compounded → MEDIUM-HIGH)
- `.planning/patches/draft_a8_shm_dict_validator_2026-05-09.md` — case_012 A8 candidate
- `.planning/cross_cuts/v_series_2026-05-09.md` — companion V-series snapshot
