---
decision_id: DEC-V61-198-sub-A6-unit-detector-hardening
title: A6 unit_detector · V96 max_bytes 64 KB → 1 MB + V97 bbox cap 100 m → 1000 m
status: Accepted
parent_dec: V61-198
phase: A6 sub-DEC · spike-class advisor hardening (bug-fix only, not new advisor land)
notion_sync_status: pending (session-end batch · Accepted DEC only per v2.3 round-1 SSOT)
parent_artifacts:
  - docs/openfoam_corpus/industrial_solver_findings_v_series.md (V96 + V97 status flipped to [VALIDATED])
  - .planning/methodology/industrial_case_solver_findings.md (V96 + V97 status flipped to [VALIDATED])
  - ui/backend/services/geometry_ingest/unit_detector.py (2 constants + 2 docstring touch-ups)
  - ui/backend/tests/test_unit_detector.py (+2 regression tests; 5 existing fixtures bumped to preserve semantic intent under widened range)
  - .planning/retrospectives/2026-05-14_track_c_session_6_case_003_crm_hls.md (source retrospective surfacing V96+V97 silent fall-through)
trigger: Track C session 6 case_003 v2 e2e attempt (2026-05-14) surfaced A6 silent fall-through on HLPW6 CRM-HLS source STEP. A6 returned (None, decision=UNKNOWN, confidence=0) via two independent channels: (a) `parse_step_header_unit` 64 KB read window missed the CONVERSION_BASED_UNIT('INCH') declaration at byte 707,430 of 716,110 (V96); (b) `bbox_plausible_units` 100 m upper bound rejected the airframe at 182.88 m as implausible (V97). Combined silence → engineer received zero unit-advisory signal → cadquery silently converted INCH→MM at importStep time → 25.4× scale anomaly cascaded into V98 (y+ ≈ 2.1×10⁵, force coefficients non-physical). V96 + V97 are V83 6th cross-application class (regex/range surface check passes; intent check never asked).
autonomous_governance: true
counter_impact: +1
codex_review_relay: SKIPPED (spike-class scope per ~/CLAUDE.md v2.3 §9 — 6 LOC source diff, 2 constant changes + 2 docstring lines, +2 regression tests, 5 fixture bumps to preserve semantic intent; not cross ≥3 shared code paths; no schema break, no auth/signing/security boundary, no risk-tier hit per RETRO-V61-001 v2.2 1-sync-trigger list)
kogami_review_path: SKIPPED (v2.3 §1 — Kogami opt-in; user did not summon for this hardening)
authored_by: Claude Code Opus 4.7 (1M context · A6 hardening dispatched sub-session)
authored_at: 2026-05-14
confidence: high (constant-only fixes verifiable against documented HLPW6 evidence; 24/24 pytest green including 2 new regression tests; cascading test fixture bumps preserve semantic intent of pre-existing assertions)
---

# DEC-V61-198-sub-A6 · A6 unit_detector hardening (V96 + V97)

## 1. Why now

Track C session 6 case_003 v2 (CRM-HLS external-high-Re-BL) reached the e2e
attempt at the HLPW6 source STEP and surfaced **A6 silent fall-through** —
the unit advisor returned `(declared_unit=None, decision=UNKNOWN, confidence=0)`
across both of its independent channels. The downstream cascade (cadquery
INCH→MM silent conversion → 5× CRM scale → y+ ≈ 2.1×10⁵ at sHM L3 → V98
non-physical force coefficients) traces back to A6's silence, not to a
broken regex or broken plausibility model. The regex and the model are
correct; **two empirical constants** were tuned against the wrong
distribution:

- **V96 root cause**: `max_bytes=65536` (64 KB) optimizes for SolidWorks-2018
  / CATIA-with-early-context placement (case_002a unit decl at byte ~6,000).
  HLPW6 / ST-Developer / CATIA-V5 AP242 place GLOBAL_UNIT_ASSIGNED_CONTEXT
  near end-of-file (HLPW6 INCH decl at byte 707,430 of 716,110 — last 1.2 %
  of file bytes).

- **V97 root cause**: `_INDUSTRIAL_EXTENT_RANGE_M = (0.01, 100.0)` captures
  the academic-reference middle of the industrial-CFD operating envelope
  (airfoils, heat-exchangers, single rooms) and rejects the upper tail
  (full aircraft 60–80 m, ships 200–400 m, civil structures 300+ m,
  wind farms 1+ km). HLPW6 CRM-HLS airframe at 182.88 m sits just above
  the 100 m cap and gets silently rejected as implausible.

Both V-rows are V83 6th cross-application instances (surface check passes;
intent check never asked). The fix is a single sub-DEC bundling two
constant changes plus regression tests; spike-class scope per v2.3 §9.

## 2. Decision

Single sub-DEC, two constant changes + matching docstring touch-ups in
`ui/backend/services/geometry_ingest/unit_detector.py`:

1. `parse_step_header_unit` default `max_bytes`: **65,536 → 1,048,576** (1 MB).
   Covers all observed industrial STEP unit-declaration placements while
   preserving the chunk-not-stream guard for huge STEPs.

2. `_INDUSTRIAL_EXTENT_RANGE_M`: **(0.01, 100.0) → (0.01, 1000.0)**.
   Covers full-aircraft + ship + civil-structure scale geometries while
   preserving the "absurdly large" rejection semantics (a > 1 km extent
   is still flagged as implausible, which catches wind-farm domains as a
   future widening candidate — not in scope here).

3. Two regression tests in `ui/backend/tests/test_unit_detector.py`:
   - `test_parse_step_header_inch_past_64kb_window`: writes a synthetic
     STEP with INCH conversion line past byte 65536 (~84 KB padding);
     asserts default args surface INCH; pins the old 64 KB ceiling as
     a counter-example (`max_bytes=65536` returns `None` on the same
     fixture — proves the constant change actually matters).
   - `test_bbox_plausible_full_aircraft_scale_locks_mm`: asserts
     `bbox_plausible_units(182880.0) == (GeometricUnit.MM,)` at the
     default range. Mirrors the V97 row's documented regression target.

4. Five pre-existing test fixtures bumped to preserve semantic intent
   under the widened range (otherwise their `"MM-only-plausible"` /
   `"M-excluded"` assertions would break for incidental reasons unrelated
   to the V96+V97 fix). Specifically:
   - `test_bbox_plausible_industrial_mm_only`: 50000 → 500000
   - `test_bbox_plausible_multiple_candidates`: 200 → 2000
   - `test_detect_unit_header_agrees_with_unique_bbox`: 50000 → 500000
   - `test_detect_unit_header_agrees_with_multi_plausible_bbox`: 200 → 2000
   - `test_detect_unit_no_header_single_plausible_bbox`: 50000 → 500000
   - `test_detect_unit_no_body_extents_backward_compat`: 50000 → 500000
   - `test_detect_unit_returns_unit_detection_dataclass`: 50000 → 500000

5. `test_detect_unit_body_class_filter_case_003_like` updated: the
   airframe at 182880 mm (182.88 m) now survives the body-class filter
   under the widened range, so the discard count drops from 4/7 to 3/7
   (only the 3 CFD-domain walls at 1.5M–2.4M mm remain implausible).
   Decision still locks to MM, confidence still ≥ 0.85, but the assertion
   string moved from `"4/7"` to `"3/7"`. This is the correct cascading
   semantic effect of widening the cap — the test was previously pinning
   "the over-100 m airframe is filtered" as the expected behavior, which
   was the bug, not the spec.

## 3. Why spike-class scope (not full DEC, no Kogami, no Codex review)

Per ~/CLAUDE.md v2.3 round-1 loosen §9 (spike-class), this work fits
spike-class because:

- **LOC**: source diff is ≤ 8 LOC (2 constant values + ~6 lines of
  docstring text updating "64 KB" / "1cm-100m" to the new values). Well
  under the 30 LOC spike ceiling.
- **Schema/contract**: zero schema breaks. The function signatures keep
  the same defaults position; callers passing explicit values for either
  argument are unaffected by the default change.
- **Cross-cutting**: not cross ≥3 shared code paths. `unit_detector.py`
  is a single module; the change is constant-tuning, not API change.
- **Safety surface**: no auth, no signing, no security boundary, no
  RETRO-V61-001 risk-tier hit per the v2.2 1-sync-trigger list.
- **Confidence**: high — directly verifiable against the documented
  HLPW6 evidence (byte 707,430 INCH decl; 182,880 mm airframe extent).

This DEC exists as sub-DEC not because the work is "cross-cutting"
(spike-class would qualify for commit-only) but because the **two
corpora amend together** (V96 + V97 status flip in both
`docs/openfoam_corpus/industrial_solver_findings_v_series.md` and
`.planning/methodology/industrial_case_solver_findings.md`). Corpus
status-flip provenance benefits from a DEC anchor for future readers
tracing why the V-rows say `[VALIDATED 2026-05-14 (DEC-V61-198-sub-A6-...)]`.

## 4. Verification

```
$ cd ~/Desktop/cfd-harness-unified
$ PYTHONPATH=. uv run pytest ui/backend/tests/test_unit_detector.py -q
24 passed in 0.12s
```

Baseline before patch: **22 passed**. After patch: **24 passed** (+2 new
regression tests; 6 pre-existing tests updated with bumped fixtures
preserving semantic intent; 0 tests removed).

Direct probes (pre-patch) confirming the fall-through:
- `bbox_plausible_units(182880)` returns `()` under old range
- `bbox_plausible_units(182880, (0.01, 1000.0))` returns `(MM,)` under
  widened range (now the default)

Direct probe (post-patch) confirming the fix:
- `parse_step_header_unit(<HLPW6-like STEP with INCH at byte ~84,000>)`
  returns `(INCH, [evidence])` at default args; same fixture with
  explicit `max_bytes=65536` returns `(None, [evidence])` — the
  counter-example assertion in the V96 regression test.

## 5. Out of scope (deliberately not in this DEC)

- **A6 logging / structured evidence enrichment**: brief explicitly
  rules out "logging 周边" scope. Future hardening if A6 is escalated
  to a phase plan.
- **Range widening to (0.001, 10000.0)** (wind-farm + atmospheric BL
  scale): trades off "absurdly large" rejection semantics. V97 row
  considered this alternative explicitly and recommended (0.01, 1000.0)
  as the minimal sufficient widening.
- **Stream-scan whole-file V96 alternative**: more complete but higher
  memory hit. V96 row considered this and recommended the 1 MB cap as
  the minimal sufficient widening.
- **A11 candidate y+ pre-flight advisor** (V98 cascade root): registered
  in V98 row, blocked on 2-case evidence promotion gate. Out of scope
  here.
- **ARC-GOAL.md reconciliation** (LANDED counter / V-series status):
  brief explicitly forbids touching ARC-GOAL from this sub-session
  (race risk with B17). Main session will reconcile in next ARC-GOAL
  pass — see §6 below for the recommended deltas.

## 6. Recommended ARC-GOAL deltas (for main session, NOT applied here)

The main session, when reconciling ARC-GOAL.md, should consider:

1. **V96 status** in line ≈92: "V96 A6 max_bytes 64KB STEP truncation
   (case_003)" → add `[VALIDATED]` marker referencing this sub-DEC.
2. **V97 status** in line ≈92: "V97 A6 bbox 100m upper bound cap
   (case_003)" → add `[VALIDATED]` marker referencing this sub-DEC.
3. **LANDED counter**: A6 was originally counted at 7/8 with note
   "A6 unit_detector silent fall-through V96+V97 surfaced via
   case_003 — fix candidate emerged ... 待 land 决策". This sub-DEC
   lands the fix candidate. The decision for the main session:
   - **Option A** (recommended): keep LANDED at 7/8. A6 was always
     counted as LANDED in the original advisor enumeration
     (A1/A2-v2/A3/A4/A5/A7/A8 — A6 is not in that list because
     A6 was implemented earlier and never enumerated alongside the
     case-driven A-series). This sub-DEC is **advisor hardening**,
     not a new advisor land. Bookkeeping: do NOT increment.
   - **Option B**: re-enumerate A6 explicitly into the LANDED set if
     ARC-GOAL audit reveals it was missing from the original 7. In
     that case, LANDED moves 7 → 8 and one of the existing 待 land
     slots adjusts accordingly. Requires main-session review of the
     A-series enumeration; not actionable from this sub-DEC.
   - The author of this sub-DEC defaults to Option A (no counter
     change) unless the main session has independent grounds for
     re-enumeration.
4. **last_updated timestamp** in line ≈98: bump to reflect this land.

These are recommendations; ARC-GOAL writes are explicitly forbidden
from this sub-session per brief hard-constraint to prevent B17 race.

## 7. Provenance

- Author: Claude Code Opus 4.7 (1M context) · A6 hardening dispatched
  sub-session of Track C session 6
- Authored: 2026-05-14
- Source retro: `.planning/retrospectives/2026-05-14_track_c_session_6_case_003_crm_hls.md`
- Evidence file: `~/Desktop/case_003_crm_hls_boundary_layer/evidence/session6_advisor_xapp.txt`
- Reference STEP: `~/Desktop/case_003_crm_hls_boundary_layer/inputs/cad_codex_v1.step` (and `inputs/cache/tier1_crm_hls_hlpw6_tc1.stp` for the original HLPW6 source)
- V-series rows: V96 (parse_step_header_unit truncation) + V97
  (bbox_plausible_units cap) + V98 (cascade root, NOT addressed here)

## 8. Notion sync intent

Per v2.3 round-1 (2026-05-11), Notion sync is restricted to Status=Accepted
DECs. This DEC is Accepted as of authoring (no further gating required —
constant fix verified against documented evidence + pytest green). To be
synced at session-end batch (not by this sub-session).
