# DEC-V61-057 · Codex Round 4 Review (Stages C + D)

**Reviewer**: Codex GPT-5.4 (xhigh reasoning)
**Date**: 2026-04-25 (Track B autonomous mandate · cfd-s1-dhc worktree)
**Branch**: `dec-v61-057-stage-b` @ commit `e3d0d83`
**PR**: #37
**Round budget**: 4 / 4 (intake §8 normal planned checkpoint)

## Verdict

**APPROVE_WITH_COMMENTS** · 1 MED + 1 LOW · NO Stage E blocker

| | Findings |
|---|---|
| HIGH | 0 |
| MED  | 1 |
| LOW  | 1 |

**Estimated pass rate after fixes**: 96 % (Codex)
**Stage E readiness**: GO. The only caveat (preflight-shape mismatch) is
itself addressed by this commit so Stage E preflight will enforce, not warn.

## Findings

### F1-MED · DHC observables[] gold schema not wired into preflight scalar gate · ADDRESSED

**File refs (round-4 cited)**:
- `scripts/preflight_case_visual.py:287` (multi-doc `quantity:` walk)
- `scripts/preflight_case_visual.py:341` (cylinder secondary gate; same shape assumption)
- `knowledge/gold_standards/differential_heated_cavity.yaml:36` (schema_v2 observables[] block)

**Finding**: `_check_scalar_contract()` previously walked the gold YAML as a
multi-doc stream looking for per-document `quantity:` blocks. DHC migrated
to schema_v2 (single doc with `observables:` array) in Stage C, so the
primary lookup returned `warn` "gold has no quantity block for
'nusselt_number'" — preflight degraded to AMBER instead of evaluating the
scalar contract. Codex confirmed via direct probe of the on-disk fixture.

**Resolution (this commit, round-4 addressing edit)**:
- Primary observable lookup now tries shape (a) per-doc `quantity:`, then
  shape (b) `observables[]` array within any document. First match wins.
- Secondary observable lookup likewise normalized: `sec_lookup` map merges
  both shapes into `{name: (expected, tolerance, gate_status)}`.
- Advisory observables (`gate_status == "PROVISIONAL_ADVISORY"`) surface as
  `level=warn` (yellow) on outside-tolerance, NOT `level=fail` (red), so
  preflight does not block live runs on advisory misses.
- 4 new regression tests under `tests/test_preflight_multi_scalar.py`:
  - `test_schema_v2_primary_is_evaluated_not_warned`
  - `test_schema_v2_secondary_observables_evaluated`
  - `test_schema_v2_advisory_outside_tolerance_emits_warn_not_fail`
  - `test_schema_v2_real_dhc_gold_yaml_still_loads` (live YAML smoke)

### F2-LOW · Legacy markdown report still treats advisory as hard-gated · ADDRESSED

**File refs (round-4 cited)**:
- `src/auto_verifier/gold_standard_comparator.py:28` (Stage C added gate_status)
- `src/report_engine/generator.py:91` (`_build_template_context` match_rate)
- `templates/partials/results_comparison.md.j2:3` (markdown template)

**Finding**: Comparator now excludes PROVISIONAL_ADVISORY from the verdict
(Stage C), but `ReportGenerator._build_template_context()` still computed
`match_rate` over ALL observables. Codex demonstrated the mismatch via
direct probe: comparator `overall='PASS'` while report-engine `match_rate
== 0.667` for the same data when only an advisory observable missed.

**Resolution (this commit)**:
- `_build_template_context()` filters `observables` to HARD_GATED before
  computing pass_count / total_count. Backward compat preserved by the
  default `gate_status == "HARD_GATED"` from `ObservableCheck.to_dict()`.
- Markdown template surface (`results_comparison.md.j2`) deferred — once
  match_rate semantics agree, the table can render an advisory row in a
  follow-up batch (Stage E sweep cosmetic; not a Codex blocker per the
  LOW severity).

## Items Codex explicitly DID NOT block

- Pending placeholder UX (Stage D.2 amber + "Stage E live run 待跑" caption)
  reads as "not populated yet", not "measurement failed". OK.
- Amber treatment for PROVISIONAL_ADVISORY (Stage D.2 frontend) matches
  the comparator semantics; "不计入裁决" disambiguator adequate. OK.
- Plane separation clean (`src/dhc_extractors.py` Execution-only, comparator
  + UI on Evaluation/Control). OK.

## Open follow-ups (non-blocking, Stage E or later)

- Stage D → Stage E contract (Codex "open question 4"): the dhc_extractors
  return rich dict payloads (`{value, profile_spread, peak_to_profile_spread,
  source}`), but `scripts/phase5_audit_run.py:532` and
  `ui/backend/services/comparison_report.py` consume flat numeric
  `secondary_scalars`. Stage E live-run wiring must extract `value` from
  each dict (not pass the dict through verbatim). Add one explicit Stage E
  regression test for that mapping.

## Round 4 Disposition

| Finding | Status | Resolution |
|---|---|---|
| F1-MED  | ✅ Addressed | this commit (preflight schema_v2 normalization + 4 regression tests) |
| F2-LOW  | ✅ Addressed | this commit (`_build_template_context` HARD_GATED filter) |

**Stage E unblocked**. Round 4 budget consumed (4 / 4). Round 5 = halt-risk;
round 6 = FORCE ABANDON. No further Codex review planned for Stage E
itself — the live OpenFOAM run is operational verification, not code
review territory. Any post-R4 defects surfaced by the live run go into
RETRO-V61-057 addendum per RETRO-V61-053 protocol.
