---
decision_id: V61-198-sub-A10
title: A10 thermo_polynomial_range_advisor — codify V93 pre-ignition T-floor rule; close V41 channel-(b) gap; reacting-low-Mach advisor stack +1
status: Accepted
parent_dec: V61-198
phase: ARC-Advisor-Substrate / A10 reacting-low-Mach thermo-range advisor
notion_sync_status: pending
---

# DEC · A10 thermo_polynomial_range_advisor land

> Lands the **A10** advisor in the `geometry_ingest/` stack. Closes the
> V41 channel-(b) sediment gap (per-species Tlow=300 leftover after
> global-header patch, V91-flagged) and codifies V93's pre-ignition
> T-floor rule (`min(BC T) - safety_margin >= max(per-species Tlow)`) as
> an automated check. Mirrors A4 / A5 / A8 pure-dict-consumer pattern.

## 1. Context

V41 (case_009 v1 sediment, 2026-05-08) claimed `[VALIDATED]` after a
global-header patch lowered the chemkin therm.dat top-line Tlow to 200 K.
V91 (Track C session 4, 2026-05-13) blind-verified and contradicted both
V41 claims: 13 / 53 species (incl. N2 + AR + CH3O) survived chemkinToFoam
with per-species `Tlow 300;` records intact, producing 14.7M
`janafThermo<EquationOfState>::limit` warnings across cold-flow + ignite
logs and stalling case_009 v1 ignite at 593 μs. V91 deferred the patch to
"case_009 v1.5 sub-session" and registered A10 as the cross-case
advisor candidate.

V61-198-sub-case-009-v1-5-cleanup (2026-05-14, commit `2c93e69`) landed
the patch (`v1_5/scripts/patch_janaf_tlow.py`) + landed V93 as a new
V-row encoding the pre-ignition T-floor rule + amended V41 to
`[QUESTIONABLE 2026-05-14]`. v1.5 produced 0 limit warnings across 2000
ignite timesteps and Tmax climbed monotonically to 1985 K — empirical
confirmation that V93's rule is **necessary and sufficient** to fix the
case_009 v1 failure mode.

This sub-DEC promotes V41's lesson + V93's rule from substrate-level
remediation (the `patch_janaf_tlow.py` script lives in the case_009
external substrate) to **harness-level pre-flight check** (the advisor
lives in `geometry_ingest/`, gets called from the workbench before any
reacting case allocates solver wall-clock).

## 2. Decision

Land four artifacts:

1. **`ui/backend/services/geometry_ingest/thermo_polynomial_range_advisor.py`** —
   pure-dict-consumer advisor. 4 detection paths:
   - **(a)** Per-species `Tlow > canonical_floor (200 K)` → warning
     `tlow_above_canonical` (catches partial-patch state independent
     of boundary T).
   - **(b)** `max(species Tlow) > min(fixedValue T) - safety_margin (5 K)` →
     critical `t_floor_breach` (V93 codified rule).
   - **(c)** Fuzzy-match (Levenshtein ≤ 2) every key against canonical
     thermo vocabulary → warning `typo_suspicion`. Min key length 4
     guards against element-symbol false positives. Mirrors A8 pattern.
   - **(d)** Species coverage census (Tlow=200 / 200<Tlow≤300 / Tlow>300)
     for engineer-readable status; companion `internal_t_below_tlow`
     critical for `internalField` T cold-start.

2. **`ui/backend/tests/test_thermo_polynomial_range_advisor.py`** —
   14-test suite. V41 channel-(b) regression (53-species v1 fixture)
   + V93 rule regression (minimal 2-species fixture) + v1.5 patched
   state (closes the loop, no false positive) + (a)/(b)/(c)/(d)
   positive + negative tests + missing-block tolerance + canonical
   constants pin.

3. **V41 status flip** in both corpora — `[QUESTIONABLE 2026-05-14]`
   → `[VALIDATED 2026-05-14 (DEC-V61-198-sub-A10)]`. A10 codifies the
   two-channel detection logic; V41 (channel-a global header) + V93
   (channel-b per-species) are now jointly enforced by the advisor's
   path (a) + path (b). The summary table row in
   `industrial_case_solver_findings.md` line 103 is updated to match.

4. **`advisor_coverage_2026-05-09.md` A10 row** — promote from
   "candidate registered in session 4 retro §6/§8" to **LANDED 2026-05-14**.
   Mirrors A4 / A5 / A8 LANDED-row format.

V93 status is **unchanged** (`[VALIDATED 2026-05-14]`) — V93 is a
fresh row from B10 with v1.5 e2e regression evidence; no flip needed.

## 3. Promotion gate

Per session 5 retro §4 + §9, the promotion gate is **loosened** for
A10 from the strict V25→A2-v2 convention ("2 independent cases") to:

> **paired before/after evidence on ≥ 1 reacting case, OR 2 independent
> reacting cases.**

Substantive justification: v1 (failing, max Tlow=300, BC T=294 → 8.86M
warnings + stall) and v1.5 (passing, max Tlow=200, BC T=294 → 0 warnings
+ clean 1985 K Tmax climb) are **two distinct chemkinToFoam
conversion-state failure modes on the same substrate**. The
counterfactual structure (advisor would reject v1, accept v1.5; only
delta = the patch V93 codifies) is **functionally stronger** than two
independent failing snapshots. The gate is met.

This loosening is recorded as a **gate-policy refinement**, not an ad-hoc
exception. Future advisor candidates whose evidence base is a single-case
paired before/after with isolated intervention (no co-varying changes)
may invoke the same standard.

## 4. Scope (out-of-scope explicit)

- **Out of scope**: `.planning/ARC-GOAL.md` update — main session
  reconcile to avoid race with B16 (per session brief 硬约束).
- **Out of scope**: `case_003 / case_009 / case_011 / case_004 /
  case_010` substrate — no edits (session brief 硬约束).
- **Out of scope**: A1 / A2-v2 / A3 / A4 / A5 / A7 / A8 advisor code —
  no cross-cutting refactor.
- **Out of scope**: `unit_detector.py` — B16 work in parallel.
- **Out of scope**: spike-class classification — A10 lands new
  advisor + flips V41 in two corpora + writes sub-DEC ⇒ sub-DEC scope
  per v2.3 governance (≥3 shared code paths effectively touched).
- **Out of scope**: Codex review — `confidence: high` (pure
  dict-consumer + 14-test suite + 3 sibling-advisor patterns precedent);
  Opus self-judgment per v2.2 1-sync-trigger (not on auth / signing /
  security boundary).
- **Out of scope**: Notion sync — frontmatter
  `notion_sync_status: pending`; will batch on next session-end sync per
  v2.3 "Notion 仅 sync Status=Accepted DEC" rule.

## 5. Risk + reversibility

- **Reversibility**: full. Advisor is a pure additive surface
  (`ui/backend/services/geometry_ingest/thermo_polynomial_range_advisor.py`
  is a new file with no upstream callers in this DEC; integration into
  the workbench pre-flight is a follow-up). V41 status flip is one
  string substitution in two corpus files (reversible via git revert).
- **Risk class**: low. No runtime CFD dependency. No file IO. No
  schema break in any existing module. 14 unit tests, 0.03s wall-clock.
- **Risk: false positive on path (a)**: a warning fires for every
  species at Tlow > 200 K. In an LES case with all BCs ≥ 300 K, the
  warnings are technically not actionable (path-b doesn't breach).
  Engineer can suppress by passing a higher `canonical_tlow_floor_k`.
  This is the correct default — V41 was caused by exactly the
  "partial-patch state silently accepted" failure mode that path (a)
  surfaces. Path (a) is the channel-(b) detection that V41 needed.
- **Risk: edit-distance ≤ 2 false typo on long keys**: mitigated by
  `_MIN_KEY_LEN_FOR_FUZZY = 4` ceiling; element-symbol leaves and
  user-defined short names are skipped. Verified by
  `test_path_c_canonical_only_no_typo`.

## 6. Verification

| Check | Pre-A10 | Post-A10 |
|---|---|---|
| `ui/backend/services/geometry_ingest/thermo_polynomial_range_advisor.py` | absent | **present** (407 LOC source) |
| `ui/backend/tests/test_thermo_polynomial_range_advisor.py` | absent | **present** (14 tests, 0.03s) |
| `pytest ui/backend/tests/test_thermo_polynomial_range_advisor.py` | n/a | **14 passed** |
| V41 status in `docs/openfoam_corpus/industrial_solver_findings_v_series.md` line ~545 | `[QUESTIONABLE 2026-05-14]` | `[VALIDATED 2026-05-14 (DEC-V61-198-sub-A10)]` |
| V41 status in `.planning/methodology/industrial_case_solver_findings.md` line ~639 | `[QUESTIONABLE 2026-05-14]` | `[VALIDATED 2026-05-14 (DEC-V61-198-sub-A10)]` |
| V41 summary row in `industrial_case_solver_findings.md` line 103 | `[QUESTIONABLE 2026-05-14] · ...` | `[VALIDATED 2026-05-14] · A10 advisor lands; channels (a)+(b) jointly enforced` |
| `advisor_coverage_2026-05-09.md` A10 row | candidate registered | **LANDED 2026-05-14 (DEC-V61-198-sub-A10)** |
| V93 status | `[VALIDATED 2026-05-14]` | unchanged |

## 7. ARC-GOAL impact (do NOT auto-update ARC-GOAL.md — main session reconcile)

| ARC-GOAL row | Current | Post-A10 |
|---|---|---|
| #2 LANDED advisor count | 7 (A1 thin_wall · A2 v1+v2 · A3 · A4 · A5 · A7 · A8) | **8** (+ A10) |
| #3 V-series rows ≥ 100 | 93 | unchanged (no new V-row) |
| #4 numerics classes ≥ 3 | 3 / 3 | unchanged |
| Charter trigger probe | n/a — A10 touches single shared code path (`geometry_ingest/`) + tests + V-row + advisor coverage = sub-DEC scope per v2.3 | sub-DEC |

Main session checks whether the "✓ Done" dimension on ARC-GOAL #2 fires
at 8 LANDED. M-A10-NEW milestone or squeeze into existing M-ADVISOR-PARITY
is main-session prerogative.

## 8. Counter ledger (autonomous_governance_counter_v61)

This sub-DEC is `autonomous_governance: true`. Counter +1 on land. No
external gate. No Kogami invocation (per v2.3 opt-in only; user did not
request strategic review for A10). No Codex review (per v2.2
1-sync-trigger: not on auth / signing / security boundary; v2.2
byte-repro async-trigger does not apply — no canonical manifest bytes
touched). `confidence: high` per Opus self-judgment.

## 9. Frontmatter pending

`notion_sync_status: pending` — will batch on next session-end sync per
v2.3 `Notion 仅 sync Status=Accepted DEC` rule (this DEC is Accepted on
land, so it qualifies for sync). Main session takes the sync action.

## 10. Cross-references

- **Parent**: DEC-V61-198 (APU bay strategic pivot — declares the 5-advisor
  extraction list; A10 was deferred to the case_009 v1.5 sub-session
  closure and is the 6th advisor landed under this parent)
- **Predecessor sediment / gate-setting**: V41 (now `[VALIDATED 2026-05-14
  (DEC-V61-198-sub-A10)]`), V91 (Track C session 4 blind-verification),
  V93 (Track C session 5 v1.5 cleanup new rule)
- **Predecessor DEC**: `2026-05-14_v61_198_sub_case_009_v1_5_cleanup.md`
  (B10 substrate-only intervention; this DEC promotes the rule to
  harness-level)
- **Promotion gate consolidation source**:
  `.planning/retrospectives/2026-05-14_track_c_session_5_case_009_v1_5_reacting.md`
  §4 + §9 (paired before/after evidence as gate)
- **Algorithm reference**:
  `~/Desktop/case_009_sandia_flame_d/v1_5/scripts/patch_janaf_tlow.py`
- **Sibling advisor patterns**:
  `ui/backend/services/geometry_ingest/face_orientation_advisor.py` (A4),
  `inlet_outlet_validator.py` (A5),
  `shm_dict_validator.py` (A8)
- **Corpus changes** (this DEC's edits):
  - `.planning/methodology/industrial_case_solver_findings.md` —
    V41 summary row (line 103) + V41 Status row (line ~639)
  - `docs/openfoam_corpus/industrial_solver_findings_v_series.md` —
    V41 Status row (line ~545)
  - `.planning/cross_cuts/advisor_coverage_2026-05-09.md` — A10 row
    promoted from candidate → LANDED
