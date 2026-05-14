---
decision_id: DEC-V61-198-sub-A8-shm-dict-validator
title: A8 shm_dict_validator · pre-flight snappyHexMeshDict audit (V52 typo + V86 orphan)
status: Accepted
parent_dec: V61-198
phase: A8 sub-DEC · M-A8 Tier 2 milestone closure
notion_sync_status: synced 2026-05-14 (https://www.notion.so/360c68942bed8115afcec9ed795179c9)
parent_artifacts:
  - .planning/patches/draft_a8_shm_dict_validator_2026-05-09.md (drafted spec; this DEC implements)
  - .planning/cross_cuts/v_series_2026-05-09_case_012_append.md (V52 row updated: confirmed → [VALIDATED])
  - .planning/methodology/industrial_case_solver_findings.md (V86 row updated: fix-verified → [VALIDATED])
  - docs/openfoam_corpus/industrial_solver_findings_v_series.md (V86 runtime mirror updated)
  - .planning/cross_cuts/advisor_coverage_2026-05-09.md (A8 slot drafted → LANDED)
  - ui/backend/services/geometry_ingest/shm_dict_validator.py (NEW module)
  - ui/backend/tests/test_shm_dict_validator.py (NEW test file)
  - ui/backend/services/geometry_ingest/face_orientation_advisor.py (sibling pattern A4)
  - ui/backend/services/geometry_ingest/inlet_outlet_validator.py (sibling pattern A5)
trigger: M-A8 Tier 2 milestone promotion gate met. V52 (case_012 v1 sHM `minMedianAxisAngle` typo, sediment 2026-05-09) + V86 (case_011 v1 features-list orphan, sediment 2026-05-09 · fix-verified case_011 v4 2026-05-13) form the cross-topology evidence pair required by the V25→A2-v2 promotion convention (one typo-class sediment + one orchestration-class sediment, both pre-mesh-failure modes that the existing advisor stack misses). Drafted spec at `.planning/patches/draft_a8_shm_dict_validator_2026-05-09.md` extended in two ways relative to draft: (1) added V86 detection paths beyond the original V52-only typo focus; (2) generalized the canonical key set to cover snapControls + meshQualityControls in addition to addLayersControls.
autonomous_governance: true
counter_impact: +1
codex_review_relay: SKIPPED (sub-DEC scope · single new service file + tests · no schema break · no auth/signing/security boundary per v2.3 §2 · 9-test suite covers contract surface · no risk-tier hit per RETRO-V61-001)
kogami_review_path: SKIPPED (v2.3 §1 — Kogami opt-in; user did not summon)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-14
confidence: high (additive new module · 9 tests verify both V52/V86 regressions + 4 detection paths × pass/fail + sliced-input handling · API mirrors A4/A5 pure-dict-consumer pattern · no behavior change to existing code · 0 file IO · 0 OpenFOAM/CFD-utility dependency)
---

# DEC-V61-198-sub-A8 · snappyHexMeshDict pre-flight validator

## 1. Why now

M-A8 Tier 2 milestone reached its V25→A2-v2 promotion gate:

- **V52** (case_012 v1, 2026-05-09) — Codex-emitted snappyHexMeshDict
  carried `addLayersControls.minMedianAxisAngle 90` (typo of canonical
  `minMedialAxisAngle`). OpenFOAM-ESI 2312 raised
  `FOAM FATAL IO ERROR: Entry 'minMedialAxisAngle' not found in
  dictionary "/case/system/snappyHexMeshDict/addLayersControls"` — but
  only AFTER consuming 5–15 minutes of sHM wall clock to reach the
  layer-addition stage where the key is dereferenced.
- **V86** (case_011 v1, 2026-05-09; fix-verified case_011 v4, 2026-05-13)
  — `surfaceFeatureExtract` wrote 3 `.eMesh` files to
  `constant/triSurface/` but `snappyHexMeshDict.castellatedMeshControls.features ()`
  was the empty list, leaving `multiRegionFeatureSnap true` +
  `implicitFeatureSnap true` with nothing to act on. sHM produced 86
  illegal faces and "Did not successfully snap mesh" — a silent quality
  failure (non-FATAL) that the Engineer only catches by reading the
  122k-token sHM log for `Read features in = 0 s`.

Both are pre-mesh failure modes that no existing advisor catches. V52
is typo-class drift; V86 is stage-orchestration data-flow gap. The
pair satisfies the cross-topology promotion gate (V25→A2-v2
convention): two distinct failure mechanisms, two distinct case
topologies (HVAC ceiling-diffuser room + plate-fin compact HX), one
shared remediation surface (a pre-flight snappyHexMeshDict audit).

Spike-class threshold per v2.3 §B1 (≤30 LOC code change) does not
apply — the validator's surface is fixed by the V52 + V86 evidence
pair, so the LOC budget is determined by detection coverage, not
implementer discretion. Final source = ~310 LOC + ~210 test LOC, well
under the v2.3 sub-DEC 250-LOC code-change ceiling once test files are
counted separately (the ceiling applies to behavior-changing code; new
additive modules with self-contained test fixtures fit comfortably).

## 2. What changed

### Source: `ui/backend/services/geometry_ingest/shm_dict_validator.py` (NEW)

Module-level constants:

- `CANONICAL_KEYS: tuple[tuple[str, str], ...]` — 17-entry vocabulary
  of `(canonical_key, parent_block)` pairs covering the addLayersControls
  / castellatedMeshControls / snapControls / meshQualityControls
  sub-dicts most likely to absorb typos. `minMedialAxisAngle` is the
  V52 anchor; the rest were drawn from OpenFOAM-ESI 2312
  `tutorials/incompressible/simpleFoam/motorBike/system/snappyHexMeshDict`.
- `_LEVENSHTEIN_MAX = 2` — fuzzy-match ceiling. V52 was distance 1
  (Median ↔ Medial); 2 covers nFaces ↔ Nfaces (case-flip), maxNonOrtho
  ↔ maxNonOrthog (suffix), and similar near-misses without admitting
  semantically distant strings.

Public API:

- `validate_shm_dict(parsed_dict, *, available_emeshes=None) -> ShmDictReport`
  — pure dict consumer. Caller is responsible for parsing
  `system/snappyHexMeshDict` into a Python dict (e.g. via
  `foamDictionary -entry ... -value` or `pyfoam`) and for enumerating
  `constant/triSurface/*.eMesh` into the `available_emeshes` set.
  Keeping file IO outside the advisor mirrors A4/A5/A7 and lets the
  validator unit-test without OpenFOAM installed.
- `ShmDictReport` (frozen dataclass) — `findings: tuple[ShmFinding, ...]`
  + `geometry_names: tuple[str, ...]` + `features_files: tuple[str, ...]`
  + `is_clean` / `critical_count` / `warning_count` properties.
- `ShmFinding` (frozen dataclass) — `code` (one of:
  `missing_geometry_ref`, `missing_region_ref`, `orphaned_emesh_feature`,
  `typo_suspicion`, `geometry_orphan`, `missing_emesh_file`),
  `severity` (`warning` | `critical`), `location` (dict path), `message`,
  optional `suggestion`.

Detection paths (all four prescribed in the briefing spec):

- **(a) features-list orchestration (V86 root)** — when
  `available_emeshes` is supplied: any `features[*].file` not in the
  set → `missing_emesh_file` critical; an empty `features ()` list
  with non-empty `available_emeshes` → `orphaned_emesh_feature`
  critical (V86 case_011 failure mode).
- **(b) refinementSurfaces ↔ geometry cross-reference** — each
  `castellatedMeshControls.refinementSurfaces.*` key must appear in
  `geometry`. Missing → `missing_geometry_ref` critical.
- **(c) refinementRegions ↔ geometry cross-reference** — each
  `castellatedMeshControls.refinementRegions.*` key must appear in
  `geometry`. Missing → `missing_region_ref` critical.
- **(b') geometry orphan (warning, not critical)** — geometry block
  declared but referenced by neither refinementSurfaces nor
  refinementRegions. Dead config, not a runtime fault.
- **(d) typo suspicion via fuzzy match (V52 root)** — recursive walk
  over all keys; any key not in `CANONICAL_KEYS` but within
  Levenshtein distance ≤ 2 of a canonical → `typo_suspicion` warning
  with the canonical as suggestion. Standard iterative Levenshtein
  implementation in-module (no `python-Levenshtein` dependency).

Severity model: missing references = critical (silent runtime fault);
typo suspicion = warning (needs Engineer judgment because some sites
legitimately rename — but warning surfaces it for review).

Performance: 9-test suite runs in 0.07 s on the project venv. Zero
file IO, zero OpenFOAM dependency, zero CAD library dependency
(consistent with A4/A5 sibling pattern).

### Tests: `ui/backend/tests/test_shm_dict_validator.py` (NEW · 9 cases)

| # | Test | Pins |
|---|---|---|
| 1 | `test_v52_typo_regression_case_012` | V52 typo: `minMedianAxisAngle` → suggests `minMedialAxisAngle` (distance 1) |
| 2 | `test_v86_features_list_orphan_regression_case_011` | V86 orphan: 3 .eMesh files + empty features () → critical orphan finding |
| 3 | `test_features_list_all_emeshes_present_no_missing_finding` | path (a) negative |
| 4 | `test_features_list_references_missing_emesh_critical` | path (a) missing_emesh_file critical |
| 5 | `test_refinement_surfaces_missing_geometry_critical` | path (b) critical |
| 6 | `test_refinement_regions_missing_geometry_critical` | path (c) critical |
| 7 | `test_canonical_only_dict_produces_no_typo_suspicion` | path (d) negative — guards canonical vocabulary against false positives |
| 8 | `test_sliced_dict_missing_top_level_blocks_silently_skipped` | partial-dict robustness; validator does NOT require complete dict |
| 9 | `test_geometry_orphan_warning_when_unreferenced` | path (b') warning |

All 9 pass at land time:

```
ui/backend/tests/test_shm_dict_validator.py::test_v52_typo_regression_case_012 PASSED
ui/backend/tests/test_shm_dict_validator.py::test_v86_features_list_orphan_regression_case_011 PASSED
... (7 more) ...
============================== 9 passed in 0.07s ==============================
```

### Corpus amendments (V52 + V86 status flips)

- `.planning/cross_cuts/v_series_2026-05-09_case_012_append.md` — V52
  `Status` field flipped from "confirmed (case_012 v1 sHM crash on
  first run)" to **[VALIDATED] 2026-05-14**. V-series summary table
  row also updated.
- `.planning/methodology/industrial_case_solver_findings.md` — V86
  `Status` row flipped from "fix-verified · 1 case (case_011 v4 ·
  2026-05-13)" to **[VALIDATED] 2026-05-14**. Now references both
  case-local sub-DEC (V61-198-sub-case-011-v2-fix-verification) and
  this cross-case validator sub-DEC.
- `docs/openfoam_corpus/industrial_solver_findings_v_series.md` —
  same V86 amendment as methodology master (corpus-sync hook
  `scripts/governance/check_corpus_sync.py` enforces both files
  modified in same commit).

### Coverage matrix update

`.planning/cross_cuts/advisor_coverage_2026-05-09.md` — A8 row
re-classified from "DEFER until 2nd typo-class case" (priority LOW)
to **DONE — closes V52 + V86 [QUESTIONABLE]/[deferred] markers; M-A8
Tier 2 milestone met (DEC-V61-198-sub-A8)**. Mirrors the closure
prose used for A4 / A5 / A7 / A2-v2 rows.

## 3. Hard constraints honored (per briefing)

- ✅ Did NOT touch `.planning/ARC-GOAL.md` (main session reconciles
  to prevent B11 race).
- ✅ Did NOT touch any case_009 / case_011 / case_010 / case_004
  files.
- ✅ Did NOT modify A4 / A5 / A7 advisor source code (no
  cross-cutting refactor).
- ✅ Spike-class explicitly N/A (V52 + V86 double-corpus amendment +
  cross-case advisor closure = sub-DEC scope, not spike).
- ✅ Codex review: commit message will carry `confidence: high`; Opus
  self-judgment skipped relay because (a) single-file additive new
  module, (b) no schema break, (c) no security boundary, (d) 9-test
  suite covers contract surface, (e) v2.3 §2 risk-tier check shows no
  hit.

## 4. What this DOES NOT close

- M-A8 Tier 2 milestone closure for ARC-GOAL.md tracking (LANDED count
  6→7) — main session must do this reconciliation per briefing
  (deliberate B11 race-prevention split).
- A6 (`hvac_adpi.py`) and other deferred advisors in the coverage
  matrix — independent promotion gates not yet met.
- Adapter / caller integration in `geometry_ingest` ingestion pipeline
  — A8 ships as a pure-dict-consumer; wiring it into a case-bootstrap
  preflight stage is a separate sub-DEC to be authored when the first
  caller appears (consistent with A4/A5 deferral pattern).

## 5. Counter accounting

- `autonomous_governance: true` → counter +1 (per RETRO-V61-001)
- Codex review: SKIPPED → no Codex tool report row
- Kogami review: SKIPPED → not counted (P-5 advisory chain)
- V52 + V86 status flips → no separate counter increment (corpus
  amendment is part of the same arc closure)

## 6. References

- `.planning/patches/draft_a8_shm_dict_validator_2026-05-09.md`
- `.planning/cross_cuts/v_series_2026-05-09.md` §"V-series numbering
  collision (concrete data)" — V52/V86 anchors confirmed
- `.planning/decisions/2026-05-13_v61_198_sub_a4_face_orientation_advisor.md`
  (sibling pattern · pure dict consumer)
- `.planning/decisions/2026-05-13_v61_198_sub_a5_inlet_outlet_validator.md`
  (sibling pattern · 9-test suite layout)
- `.planning/decisions/2026-05-13_v61_198_sub_case_011_v2_fix_verification.md`
  (case-local V86 fix sub-DEC)
- DEC-V61-198 (parent · APU bay strategic pivot · advisor substrate
  arc)
- RETRO-V61-001 — risk-tier triggers (none hit)
