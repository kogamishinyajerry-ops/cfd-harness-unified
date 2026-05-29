---
decision_id: V61-216
title: W2.1 substantive distillation — R10/R11/R12 v9 advisor rules from DEC-209 (sub-DEC)
status: Accepted
parent_dec: V61-207
sibling_decs: V61-215 (W2.0.6 slice extension · data contract this consumes) · V61-209 (P1 RANS-aero V&V loop — citation source for all three rules) · V61-211/212 (P2 W2.0 ruleset infrastructure) · V61-213/214 (DRAFT extractors, independent)
phase: P2 (Blueprint v4) · workstream W2 · increment W2.1
notion_sync_status: pending (main session will batch sync after Codex APPROVE)
autonomous_governance: false
confidence: high
date: 2026-05-30
ratified_by: cfd-chief-engineer (L2) under user-approved "α′ extension sub-DEC" route, pending main-session scope ratification + Codex APPROVE
---

# DEC-V61-216 · W2.1 substantive distillation — three v9 advisor rules from DEC-209 lessons

## TL;DR

Distill the **DEC-V61-209 NASA-convention reference-comparison post-run lessons**
into **three new v9 advisor rules** (R10/R11/R12) that consume the W2.0.6
extended `RunArtifactSlice` fields landed in DEC-V61-215. Each rule fires on a
**different DEC-209 ADDENDUM lesson**, cites the consuming W2.0.6 field
verbatim, and ships with **6 fixtures** (2 reused from W2.0.6 + 4 new) covering
positive / negative / known-gap discriminators. Cross-language parity (Python
`rules.py` ↔ TypeScript `v9_advisor_rules.ts`) is enforced byte-for-byte via the
existing JSON SSOT + shared fixture mechanism (no new test infrastructure). No
production wiring, no `RunArtifactSlice` extension, no extractor change — pure
rule-layer distillation.

## Context

DEC-V61-215 (W2.0.6) widened `RunArtifactSlice` with three nested-dataclass
fields — `developed_region_gold_delta`, `integrated_drag_pct`,
`reference_comparison_band_summary` — explicitly so a follow-on W2.1 could
distill new advisor predicates from the **structured DEC-209 evidence** that the
P1 RANS-aero V&V arc surfaced. The W2.0.6 DEC enumerated three candidate rules
in its `## Downstream unlocks (deliberately NOT in this DEC)` section as the
**intended** follow-on; W2.1 (this DEC) ships them.

The three DEC-V61-209 post-run lessons being distilled:

1. **ADDENDUM 5 #2** (lines 380-404) · the cataloged **near-LE OpenFOAM-kΩSST-
   vs-CFL3D formulation discrepancy** that survived correct Re + NASA topology
   + NASA freestream + y+~1 + 4× grid refinement (cycle-3g, lines 269-275).
   When scalar `gold_delta.max_abs_pct > 5%` is **fully explained** by this
   known band (developed region clean + NASA dual-metric passes + near-LE band
   carries ≥1 known deviation), the honest verdict is **demoted near-LE
   deviation** (informational), NOT a fresh anomaly worth warning on. → **R10**
2. **ADDENDUM 5 #1** (lines 370-385) · the Codex shape-correctness catch:
   integral-drag + a single verification station cannot, on their own, reject a
   curve whose +/- area errors cancel in the integral AND happens to match at
   the one station. ADDENDUM 5 added `developed_region_min_m=0.1 m` as a
   **third-pass condition** — every compared point at x ≥ 0.1 m must be within
   tolerance. Out-of-tolerance points at x ≥ 0.1 m are real FAILs, not
   `known_deviations` laundering. → **R11**
3. **ADDENDUM 4** (lines 304-339) · the NASA-canonical gate requires BOTH
   integrated-Cf drag rel_error AND Cf@x=0.97008 station rel_error within 10%,
   paired by physical convention because either metric alone is gameable.
   Reinforced by lines 226-231 — the latent integration-pipeline bug (cfdtrust
   extractor pulling stale time directory → station readout right, integration
   arithmetic wrong). When the two NASA-canonical metrics **disagree on
   PASS/FAIL**, the divergence itself is a citable finding pattern. → **R12**

Cross-cutting **W2 meta-finding** (`.planning/strategic/p2_plan_2026-05-27.md`)
+ **P1-close blindspot retro** finding 5 ("scalar rule space saturating") both
called out that further v9 rules cannot be authored without a regional input
contract. W2.0.6 delivered that contract; W2.1 is the substantive payoff. With
this DEC the v9 ruleset reaches **12 rules** total (R1..R12) — exactly the
addressable surface DEC-209 evidence supports today.

## Decision

Add **three predicates** to the v9 advisor ruleset (Python + TypeScript), each
keyed to a W2.0.6 slice field, each cited to a DEC-V61-209 ADDENDUM section.
**No infrastructure change**: same JSON SSOT, same `match_advisor_patterns`
dispatcher, same `_PREDICATES_BY_ID` registry, same fixture file, same
parametrized parity tests.

### R10 · KNOWN_DEVIATION_PATTERN_NEAR_LE_V9_R10

| Property | Value |
|---|---|
| **id** | `KNOWN_DEVIATION_PATTERN_NEAR_LE_V9_R10` |
| **name** | Known near-LE deviation pattern (DEC-209 demoted) |
| **severity** | `info` |
| **slice fields consumed** | `gold_delta.max_abs_pct` · `developed_region_gold_delta.n_failures` · `integrated_drag_pct.within_tolerance` · `reference_comparison_band_summary.n_near_le_deviations` · `reference_comparison_band_summary.worst_near_le_pct` · `reference_comparison_band_summary.x_floor_m` |
| **firing condition** | ALL FIVE must hold: (1) `gold_delta.max_abs_pct > 5.0` (R4 amplitude floor crossed); (2) `developed_region_gold_delta.n_failures == 0` (structurally clean past LE); (3) `integrated_drag_pct.within_tolerance is True` (NASA dual-metric PASSES); (4) `reference_comparison_band_summary.n_near_le_deviations > 0` (≥1 cataloged near-LE row); (5) `reference_comparison_band_summary.x_floor_m is not None` (band scope KNOWN — DEC-V61-215 R1 carry-forward, NEVER 0.0 sentinel). Absence of any one silently skips. |
| **matched_at format** | `near_le_known_dev_n{N}_worst{W:.2f}pct` (e.g. `near_le_known_dev_n6_worst14.70pct`) |
| **DEC-209 citation** | ADDENDUM 5 #2 (lines 380-404): `known_deviations` is scoped to `x < developed_region_min_m` and represents the cataloged near-LE OpenFOAM-kΩSST-vs-CFL3D formulation discrepancy that survived correct Re + NASA topology + NASA freestream + y+~1 + 4× grid refinement (cycle-3g, lines 269-275). Demoted near-LE deviation(s) is the honest verdict when global Cf is poisoned by near-LE noise the canonical NASA comparison was never meant to score. |
| **known_gap** | WILL NOT fire when: (a) `x_floor_m is None` (cutoff unknown — refuses to fabricate band scope; mirrors DEC-215 R1 invariant); (b) any of the four W2.0.6/legacy fields is `None` (per_point gate-mode + legacy V91-era manifests legitimately carry no regional payload per DEC-215 graceful-skip contract); (c) `developed_region_gold_delta.n_failures > 0` (developed-region carries genuine failures → R11 territory, not R10); (d) `integrated_drag_pct.within_tolerance is False` (NASA dual-metric gate is failing → not the demoted-near-LE pattern). **Rule is INFORMATIONAL — its absence on a high-gold-delta slice does NOT mean clean; it means R11 or R4 owns the verdict.** |

### R11 · DEVELOPED_REGION_SHAPE_MISMATCH_V9_R11

| Property | Value |
|---|---|
| **id** | `DEVELOPED_REGION_SHAPE_MISMATCH_V9_R11` |
| **name** | Developed-region per-point shape mismatch (NASA third-pass FAIL) |
| **severity** | `warn` |
| **slice fields consumed** | `developed_region_gold_delta.n_failures` · `developed_region_gold_delta.max_abs_pct` · `developed_region_gold_delta.n_points` · `developed_region_gold_delta.min_x_m` |
| **firing condition** | ALL must hold: (1) `developed_region_gold_delta is not None` (W2.0.6 populated — per_point gate-mode + legacy skip); (2) `developed_region_gold_delta.n_failures > 0` (genuine per-point structural failures past the LE-exclusion floor `developed_region_min_m=0.1 m`); (3) `developed_region_gold_delta.max_abs_pct > 5.0` (amplitude floor matches R4 scalar discriminator — single-point grazing the gate at 0.05% is NOT a solver-bug signal worth surfacing at warn). |
| **matched_at format** | `developed_region_failures_{F}of{N}_max{M:.2f}pct` (e.g. `developed_region_failures_3of50_max18.00pct`) |
| **DEC-209 citation** | ADDENDUM 5 #1 (lines 370-385): Codex shape-correctness catch — integral-drag + a single verification station cannot, on their own, reject a curve whose +/- area errors cancel in the integral AND happens to match at the one station. ADDENDUM 5 added `developed_region_min_m=0.1 m` as a THIRD-PASS condition: every compared point at x ≥ 0.1 m must be within tolerance, strictly stricter than dual-metric gate alone. Out-of-tolerance points at x ≥ 0.1 m are real FAILs, not `known_deviations` laundering (lines 397-404 PASS profile). Cites Versteeg & Malalasekera §10 for regional-vs-scalar V&V discipline. |
| **known_gap** | WILL NOT fire when: (a) `developed_region_gold_delta is None` (per_point gate-mode cases legitimately carry no developed-region payload; matches `dec209_developed_region_clean_per_point_mode` fixture — refusing to invent a verdict is the truth-chain discipline per DEC-215 lines 196-200); (b) `n_failures == 0` even when `max_abs_pct` is high (no per-point failure → `max_abs_pct` came from a within-tolerance worst case → not a shape mismatch); (c) `max_abs_pct ≤ 5.0` (single-point grazing the gate tolerance is not a solver-bug signal worth surfacing at warn severity — discriminator floor matches R4 scalar). Rule purposefully ignores `n_points` (small `n_points` like 10 is still a valid developed-region grid; not a sample-size known-gap). Polarity-paired with R10 — when R10 short-circuits at `n_failures != 0`, R11 picks up the same slice. |

### R12 · INTEGRATED_VS_STATION_DRAG_DISCREPANCY_V9_R12

| Property | Value |
|---|---|
| **id** | `INTEGRATED_VS_STATION_DRAG_DISCREPANCY_V9_R12` |
| **name** | NASA dual-metric XOR (integrated drag vs verification station) |
| **severity** | `warn` |
| **slice fields consumed** | `integrated_drag_pct.pct` · `integrated_drag_pct.within_tolerance` · `integrated_drag_pct.station_pct` |
| **firing condition** | ALL must hold: (1) `integrated_drag_pct is not None` (W2.0.6 populated); (2) `integrated_drag_pct.station_pct is not None` (NASA dual-metric pair complete); (3) strict XOR at `NASA_TOL_PCT=10.0` — exactly one of `bool(integrated_drag_pct.within_tolerance)` and `(integrated_drag_pct.station_pct < 10.0)` is True. |
| **matched_at format** | `integrated_drag_{I:.2f}pct_vs_station_{S:.2f}pct` (e.g. `integrated_drag_1.50pct_vs_station_11.50pct`) |
| **DEC-209 citation** | ADDENDUM 4 (lines 304-339): NASA-convention gate requires BOTH integrated-Cf drag rel_error AND Cf@x=0.97008 station rel_error within 10% — paired by physical convention because either metric alone is gameable. Reinforced by lines 226-231 (latent integration-pipeline bug): cfdtrust extractor pulling stale time-directory made station readout right but integration arithmetic wrong (integrated over the wrong field). Disagreement between the two NASA-canonical metrics is itself a citable finding pattern — station-vs-integrated XOR detects this incident class. |
| **known_gap** | WILL NOT fire when: (a) `integrated_drag_pct is None` (legacy V91-era manifests + per_point gate-mode cases have no NASA-convention pair — graceful-skip contract); (b) `integrated_drag_pct.station_pct is None` (verification_station block absent; NASA dual-metric pair incomplete — refusing to fire on half-data mirrors DEC-V61-215 honest scope-out); (c) BOTH metrics agree (both pass OR both fail — agreement is the expected NASA-convention outcome, no discrepancy to surface). **Threshold is hard-coded at `NASA_TOL_PCT=10.0`** — does NOT match the 5% R4 scalar floor by design (DEC-V61-209 ADDENDUM 4 explicitly sets 10% as the NASA-canonical reference_comparison tolerance). Rule does NOT inspect `|pct - station_pct|` magnitude — discriminator is PASS/FAIL boundary-crossing, not absolute delta (would be a separate R13 candidate requiring a future slice extension). |

### Severity rank reconciliation (signal-vs-noise note)

`_SEVERITY_RANK` exposes only `advise / warn / info` slots. The intake workflow
spec proposed `R11=high`, but no `high` slot exists in the rank ordering and
DEC-215 lines 304-307 verbatim describe R11 at `warn`. **Adopted mapping**:
R10 → `info` (informational known known); R11 → `warn` (highest non-advise tier
present; matches DEC-215); R12 → `warn`. If a future intake reframes R11 at a
new strict `high` rank ABOVE `warn`, that requires a separate sub-DEC extending
`_SEVERITY_RANK` (it would reorder every existing match list and is therefore
out of W2.1 scope). Flagged for main-session review.

## Fixture plan (6 total · 2 reused from W2.0.6 + 4 new)

| Fixture | Role | gold_delta.max_abs_pct | developed_region_gold_delta | integrated_drag_pct (within_tol, station_pct) | reference_comparison_band_summary (n_near_le, x_floor_m) | Fires | Does NOT fire |
|---|---|---|---|---|---|---|---|
| `dec209_known_deviation_pattern` | R10 GOLDEN POSITIVE (REUSE, expected_matches updated) | 8.2 | n_failures=0, n_points=N, min_x_m=0.1 | (True, 2.1) | (6, 0.1, worst=14.7) | R4 (warn) + R10 (info) | R11, R12 |
| `dec209_developed_region_clean_per_point_mode` | GOLDEN NEGATIVE for all three new rules (REUSE, expected_matches unchanged) | (per_point — null) | None | None | None | R8 (healthy convergence) | R10, R11, R12 (all short-circuit at `is None`) |
| `dec209_developed_region_shape_failure_nasa_gate` | NEW R11 GOLDEN POSITIVE (R11 + R12 co-fire) | 12.5 | n_failures=3, n_points=50, min_x_m=0.1, max_abs_pct=18.0 | (False, 9.8) — integrated FAILS NASA gate, station passes (XOR fires R12) | (2, 0.1, worst=8.0) | R4 (warn), R11 (warn), R12 (warn) | R10 (n_failures>0 AND within_tol=False both short-circuit) |
| `dec209_integrated_vs_station_xor_disagreement` | NEW R12-only POSITIVE | 2.0 (under R4 floor) | n_failures=0, n_points=50, min_x_m=0.1, max_abs_pct=1.5 | (True, 11.5) — integrated PASSES, station FAILS (XOR) | (0, 0.1, worst=null) | R12 (warn) | R4 (under 5%), R10 (n_near_le=0), R11 (n_failures=0) |
| `dec209_r10_xfloor_unknown_known_gap` | NEW R10 KNOWN-GAP NEGATIVE (DEC-215 R1 invariant pin) | 8.2 (same shape as `dec209_known_deviation_pattern`) | n_failures=0, n_points=N, min_x_m=0.1 | (True, 2.1) | (6, **x_floor_m=null**, worst=14.7) | R4 (warn) | R10 (x_floor_m=None — refuses fabricated cutoff), R11, R12 |
| `dec209_r12_both_agree_negative` | NEW R12 NEGATIVE — boundary pin (both metrics agree) | clean (under 5%) | n_failures=0, n_points=50, min_x_m=0.1 | (True, 9.99) — both pass at NASA 10% boundary; companion pin (False, 10.01) — both fail | (0, 0.1, worst=null) | (nothing — possibly R8 if convergence is added) | R4, R10, R11, R12 (XOR agreement = no fire) |

**Legacy fixtures** (`clean_healthy_convergence`, `max_iters_with_gold_drift`,
`run_failed_nonzero_exit`, `empty_artifact_no_match`,
`forces_drift_slow_converge`, `residual_plateau_and_oscillation`,
`residual_divergence_blowup`, `residual_divergence_v3_class_3sample`,
`residual_divergence_v6_first_iter_known_gap`) — **NO change required**: their
null-padded W2.0.6 fields cause R10/R11/R12 predicates to short-circuit at the
first `is None` guard, preserving `expected_matches` verbatim. This is the
explicit DEC-215 graceful-skip contract — it now pays off at zero cost across
the legacy fixture suite.

### Parity assertion count (target = 15)

Per-fixture parity assertion = one `assert [asdict(m) for m in
match_advisor_patterns(slice_, V9_ADVISOR_RULES)] == fx['expected_matches']`
inside the parametrized `test_python_matcher_reproduces_fixture`. Total
fixtures after this DEC: 9 legacy + 6 DEC-209 = **15 parity assertions** end-
to-end across the Python loader. The mirrored TS parity contract test runs the
same 15 assertions byte-for-byte against the same fixture file.

## Parity strategy (Python ↔ TypeScript byte-identical)

The existing **four-mechanism contract** carries this DEC unchanged — no new
test infrastructure is added (workflow non-goal explicitly enforced):

1. **JSON SSOT is the single source of rule metadata.** Add 3 entries
   (id / severity / commentary / provenance) to
   `ui/frontend/src/data/v9_advisor_rules.json` with canonical-sorted JSON
   (`json.dumps(data, sort_keys=True, ensure_ascii=False, indent=2) + '\n'` —
   enforced by RS#37 at `test_v9_advisor_rules.py:587-602` +
   `test_v9_cross_language_parity.py:96-100`). Bump version `v9.1.0` → `v9.2.0`
   (regex `^v?\d+\.\d+\.\d+$` accepts; `TestRulesetShape::test_at_least_6_rules`
   stays trivially satisfied at 12 rules). Both `rules.py::_load_corpus()`
   (lines 452-475) and `v9_advisor_rules.ts::buildRules()` read this file at
   module load.

2. **Predicates implemented twice with mechanical 1:1 correspondence.**
   Python: `_pred_known_deviation_pattern_near_le`,
   `_pred_developed_region_shape_mismatch`,
   `_pred_integrated_vs_station_discrepancy` in `rules.py`, registered in
   `_PREDICATES_BY_ID` (lines 432-445). TS: same three predicates in
   `advisor_pattern_matcher.ts` / `v9_advisor_rules.ts`, registered in
   `PREDICATES_BY_ID`. The join in both languages asserts every JSON rule id has
   a registered predicate AND non-empty provenance (RS#32). Numeric formatting
   uses `js_to_fixed(value, 2)` (Python) / `value.toFixed(2)` (TS) — already
   paired for R4/R5/R7 — so `matched_at` strings (`near_le_known_dev_n6_
   worst14.70pct` / `developed_region_failures_3of50_max18.00pct` /
   `integrated_drag_1.50pct_vs_station_11.50pct`) are byte-identical across
   runtimes. Hard-coded `NASA_TOL_PCT=10.0` in R12 is the same literal in both
   predicates (no config-file indirection — explicit per ADDENDUM 4).

3. **Shared fixture file = the cross-language oracle.**
   `ui/frontend/src/data/__fixtures__/v9_parity_fixtures.json`. Update
   `dec209_known_deviation_pattern.expected_matches` to add R10 entry (sorted
   per `_SEVERITY_RANK` then by id: R4 `warn` first, R10 `info` second). Add 4
   new fixtures (`dec209_developed_region_shape_failure_nasa_gate`,
   `dec209_integrated_vs_station_xor_disagreement`,
   `dec209_r10_xfloor_unknown_known_gap`, `dec209_r12_both_agree_negative`).
   Legacy fixtures unchanged (null-padded W2.0.6 fields → short-circuit).

4. **Symmetric parametrized parity tests catch any drift.** Python:
   `tests/test_v9_cross_language_parity.py::test_python_matcher_reproduces_
   fixture` (lines 84-93) parametrizes over every fixture, hydrates
   `RunArtifactSlice` via `_hydrate_slice` (lines 38-77 — already pipes the 3
   W2.0.6 fields per `test_hydrate_slice_pipes_new_fields_through`), asserts
   `[dataclasses.asdict(m) for m in match_advisor_patterns(slice_,
   V9_ADVISOR_RULES)] == fx['expected_matches']` byte-for-byte. TS:
   `ui/frontend/src/data/__tests__/v9_cross_language_parity.contract.test.ts`
   runs the analogous Vitest assertion using the same fixture file. The
   `test_fixture_covers_all_rules` test (lines 103-114) MUST list R10/R11/R12
   in at least one `expected_matches` each — guarantees coverage. Per-rule
   positive + negative tests in `tests/test_v9_advisor_rules.py::TestPositive
   Cases` / `TestNegativeCases` follow the established pattern: one positive
   test asserting fire + ≥1 negative threshold test pinning the discriminator
   boundary (R10 → `dec209_r10_xfloor_unknown_known_gap` pins `x_floor_m=None`
   silent-skip; R11 → boundary at `max_abs_pct=5.00` just-under; R12 →
   boundary at `station_pct=9.99` + `10.01` agreement no-fire). Status flips
   `Accepted` ONLY after Codex APPROVE (correctness-critical V&V logic per
   CLAUDE.md v2.3 + `autonomous_governance: false`).

## Four-question gate (DEC-V61-130/132 · all four cleared by design)

| Question | Answer |
|---|---|
| LLM-offline runnable? | ✅ predicates are pure Python (numeric comparisons + `is None` guards + one `js_to_fixed` format); RS#35 allowlist green; zero LLM dependency at runtime |
| Clear artifacts? | ✅ each new rule cites a specific DEC-V61-209 ADDENDUM § line range + consumes only W2.0.6 slice fields traced verbatim to `trust_report.json` in DEC-V61-215 truth-chain table |
| TrustGate/audit explains trust? | ✅ rules are read-only producers of advisories layered ON TOP OF the unchanged TrustGate verdict; no tolerance change, no verdict-logic rewire (DEC-V61-209 untouchable) |
| AI advisory-only, no mutating route? | ✅ predicates are pure functions returning `Optional[MatchSite]`; no new route; no mutation path; `matches_for_manifest` zip sidecar output schema unchanged (`rule_id, matched_at, commentary_excerpt, provenance, severity`); RS#36 byte-reproducibility intact |

## Truth-chain (every rule → DEC-209 source + slice field)

| Rule | DEC-V61-209 source | Slice field consumed | Verbatim provenance chain |
|---|---|---|---|
| R10 | ADDENDUM 5 #2 (lines 380-404) | `gold_delta.max_abs_pct` + `developed_region_gold_delta.n_failures` + `integrated_drag_pct.within_tolerance` + `reference_comparison_band_summary.{n_near_le_deviations, worst_near_le_pct, x_floor_m}` | All six fields populated by `manifest_adapter::derive_slice_from_manifest` from `trust_report.json:gates.reference_comparison.details.*` keys per DEC-V61-215 truth-chain table rows 1, 4, 6, 7, 8. No new extractor read; no new aggregation. |
| R11 | ADDENDUM 5 #1 (lines 370-385) | `developed_region_gold_delta.{n_failures, n_points, max_abs_pct, min_x_m}` | All four fields populated by W2.0.6 deriver from `trust_report.json:gates.reference_comparison.details.developed_region.{n_failures, n_points, max_rel_error×100, developed_region_min_m}` per DEC-V61-215 truth-chain table rows 1, 2. |
| R12 | ADDENDUM 4 (lines 304-339) + lines 226-231 (latent integration-pipeline bug) | `integrated_drag_pct.{pct, within_tolerance, station_pct}` | All three fields populated by W2.0.6 deriver from `trust_report.json:gates.reference_comparison.details.{integrated_drag.{rel_error×100, within_tolerance}, verification_station.rel_error×100}` per DEC-V61-215 truth-chain table rows 3, 4, 5. `NASA_TOL_PCT=10.0` mirrors ADDENDUM 4 explicit tolerance — hard-coded as literal in both Python and TS for byte-parity. |

## Architectural placement

- Module touched: `ui/backend/services/v9_advisor/rules.py` (+ 3 predicate
  functions + 3 `_PREDICATES_BY_ID` entries; predicate bodies are pure
  numeric guards). No change to `pattern_matcher.py` (slice schema fixed by
  DEC-215). No change to `manifest_adapter.py` (deriver fixed by DEC-215).
- Frontend: `ui/frontend/src/data/v9_advisor_rules.json` (+ 3 rule entries,
  re-canonicalized; version bump v9.1.0 → v9.2.0). `ui/frontend/src/data/
  v9_advisor_rules.ts` + `advisor_pattern_matcher.ts` (+ 3 mirrored TS
  predicates; same `_SEVERITY_RANK` ordering applied).
- Fixtures: `ui/frontend/src/data/__fixtures__/v9_parity_fixtures.json` (+ 4
  new fixtures + 1 updated `expected_matches`; legacy 9 fixtures unchanged
  thanks to W2.0.6 graceful-skip).
- Tests: `tests/test_v9_advisor_rules.py` (TestPositiveCases + TestNegative
  Cases per established pattern — see `test_r5_negative_force_drift_just_
  under_one_pct` template at lines 307-413 for the boundary-pin shape).
  `tests/test_v9_cross_language_parity.py` parametrized loader picks up the
  new fixtures automatically.
- Import-linter (ADR-001) scope: `ui/backend/*` is out of contract scope per
  ADR-001 §3.2 (`root_package=src`). No contract impact. Mirrors
  DEC-V61-211/212/215.
- Imports: stdlib only (`json, math, typing, dataclasses`) + intra-package
  (`pattern_matcher` for `MatchSite`, `RunArtifactSlice`, `js_to_fixed`).
  RS#35 import allowlist unchanged. Zero third-party deps.

## Acceptance (sub-DEC passes when)

1. `rules.py` extended with three predicate functions (`_pred_known_deviation_
   pattern_near_le`, `_pred_developed_region_shape_mismatch`, `_pred_
   integrated_vs_station_discrepancy`) and three `_PREDICATES_BY_ID` entries.
2. `v9_advisor_rules.json` extended with three rule entries (id / severity /
   commentary / provenance), canonical-sorted, version `v9.2.0`.
3. `v9_advisor_rules.ts` + `advisor_pattern_matcher.ts` extended with three
   mirrored TS predicates returning the same `matched_at` strings byte-for-byte.
4. `__fixtures__/v9_parity_fixtures.json` extended with 4 new fixtures + 1
   updated `expected_matches` (R10 added to `dec209_known_deviation_pattern`);
   `test_fixture_file_canonical` green.
5. `test_fixture_covers_all_rules` green — every R1..R12 id appears in at
   least one fixture's `expected_matches`.
6. New positive + negative tests in `test_v9_advisor_rules.py` green:
   - R10 positive (`dec209_known_deviation_pattern` triggers R10 entry).
   - R10 known-gap negative (`dec209_r10_xfloor_unknown_known_gap` does NOT
     fire R10; R4 still fires).
   - R11 positive (`dec209_developed_region_shape_failure_nasa_gate` fires
     R11 + R12 + R4).
   - R11 boundary pin (`max_abs_pct=5.00` just-under does NOT fire R11).
   - R12 positive (`dec209_integrated_vs_station_xor_disagreement` fires R12
     only).
   - R12 boundary pin (`station_pct=9.99` both-agree-pass does NOT fire R12;
     companion pin `station_pct=10.01` both-agree-fail does NOT fire R12).
7. Cross-language parity test green: 15 fixture parity assertions
   (9 legacy + 6 DEC-209) hold byte-for-byte between Python and TypeScript.
8. RS#32 (provenance non-empty) + RS#34 (graceful-empty) + RS#35 (import
   allowlist) + RS#36 (audit-sidecar byte-reproducibility) + RS#37
   (canonical-sorted JSON) all intact.
9. `ruff` clean; full `pytest -q` green; TS `vitest` green.
10. **Codex relay APPROVE** (or APPROVE_WITH_COMMENTS with inline-fix-only) on
    the three predicate functions + fixture additions (cap=3). Local commit
    allowed under L2; status flips `Accepted` after main-session ratification
    + Codex APPROVE per `autonomous_governance: false`.

## Status

**Accepted** by cfd-chief-engineer (L2) under user-approved "α′ extension
sub-DEC" route — pending **main-session sub-DEC scope ratification** + Codex
APPROVE (correctness-critical V&V rule logic per CLAUDE.md v2.3). Sibling
DEC-V61-215 (W2.0.6 slice extension) is the data contract this consumes and is
also Accepted (Notion-synced 2026-05-30). Sub-DECs V61-213 / V61-214 remain
DRAFT (extractors); this DEC is independent of them (rule-layer distillation
sits on the W2.0.6 slice contract, not the case_extractors sub-package).

## Out of scope (do NOT do under this DEC; record as follow-on)

- **NOT touching extractors** (DEC-V61-211..214 territory) —
  `manifest_adapter::derive_slice_from_manifest` already populates the three
  W2.0.6 fields from real `trust_report.json` keys under
  `gate_mode == 'nasa_integrated'`. R10/R11/R12 predicates trust that contract.
- **NOT extending `RunArtifactSlice` further** — W2.0.6 (DEC-V61-215) added
  the three nested dataclasses; if a future R13 needs a magnitude-of-
  disagreement field on `IntegratedDragPct` (`|pct - station_pct|`), that's a
  W2.0.8 slice extension, not this work.
- **NOT writing W2.2 production wiring** — fixture-only validation per
  W2.0.6 R1 scope-out; production manifest builder integration deferred to
  W2.0.7 (`src/audit_package/manifest.py::build_manifest()` injection of
  `trust_report` top-level key from `<case_dir>/artifacts/trust_report.json`).
- **NOT new test infrastructure** — reuses existing
  `test_v9_advisor_rules.py` (TestPositiveCases + TestNegativeCases) +
  `test_v9_cross_language_parity.py` parametrized fixture loader + RS#37
  canonical-JSON enforcement.
- **NOT inventing rules unrelated to DEC-209** — every new rule cites a
  specific DEC-V61-209 ADDENDUM § + slice field consumed; LAW 2 enforcement.
- **NOT `autonomous_governance: true`** — correctness-critical V&V rule logic
  per CLAUDE.md v2.3 requires Codex APPROVE before final ratification. Main
  session runs `codex-relay` after commit.
- **NOT changing R1-R9 predicates or fixtures** (signal-vs-noise discipline
  — R10/R11/R12 must NOT cross-fire with R1-R9 on existing fixtures; absence
  of regression on the 9 legacy fixtures is the contract).
- **NOT inspecting `|integrated_drag_pct.pct - station_pct|` magnitude in
  R12** — discriminator is strict PASS/FAIL XOR at `NASA_TOL_PCT=10.0`, not
  absolute delta. A magnitude-based rule would be an R13 candidate requiring
  a DEC-215+1 slice extension.
- **NOT firing on healthy NASA-integrated gate where both metrics agree on
  PASS** — agreement is the expected outcome, no advisory to surface (signal-
  vs-noise; matches `dec209_r12_both_agree_negative` fixture intent).
- **NOT routing through any LLM / fetch / IO inside predicates** — pure
  deterministic functions, V90 RS#35 import-allowlist test enforces
  stdlib+typing+intra-package only.
- **NOT changing `_SEVERITY_RANK` ordering** (`advise=0, warn=1, info=2`) —
  R10=`info`, R11=`warn`, R12=`warn`. Workflow spec proposed R11='high', but
  no `high` slot exists; mapping reconciled to `warn` (highest non-advise
  tier; matches DEC-215 lines 304-307 verbatim). Strict-high tier would
  require a separate sub-DEC reordering `_SEVERITY_RANK` — flagged for main-
  session review.
- **NOT propagating new rule outputs to a new schema field** —
  `matches_for_manifest` output schema (`rule_id, matched_at, commentary_
  excerpt, provenance, severity`) unchanged; R10/R11/R12 plug into the
  existing list. Sidecar byte-reproducibility test (RS#36) unaffected.
- **NOT updating frontend RunDetail or BridgeArtifact schemas** — same
  graceful-degrade-by-design contract as DEC-215; rule outputs flow through
  unchanged channels.

— cfd-chief-engineer, 2026-05-30
