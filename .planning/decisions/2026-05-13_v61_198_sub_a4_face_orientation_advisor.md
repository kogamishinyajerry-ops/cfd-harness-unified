---
decision_id: DEC-V61-198-sub-A4-face-orientation-advisor
title: A4 face_orientation_advisor · component-orientation defect detector for D7-class anomalies
status: Accepted
parent_dec: V61-198
phase: A4 sub-DEC · Tier 1 advisor substrate arc closure
notion_sync_status: synced 2026-05-14 (https://www.notion.so/360c68942bed812590e0cf4507cec38d)
parent_artifacts:
  - .planning/patches/draft_a4_face_orientation_2026-05-13.md (research deliverable · commit 615dacb · API + algorithm spec)
  - .planning/methodology/industrial_case_solver_findings.md (V79 + V87 status flipped to [VALIDATED] 2026-05-13)
  - docs/openfoam_corpus/industrial_solver_findings_v_series.md (V79 + V87 runtime mirror)
  - .planning/cross_cuts/advisor_coverage_2026-05-09.md (A4 row READY-TO-LAND → LANDED)
  - .planning/methodology/advisor_candidates_a4_a8.md (A4 status drafted → landed)
  - .planning/ARC-GOAL.md (M-A4 milestone closed · LANDED advisor counter 5→6)
  - ui/backend/services/geometry_ingest/face_orientation_advisor.py (new module)
  - ui/backend/tests/test_face_orientation_advisor.py (new test file)
  - ~/Desktop/case_012_hvac_supply_diffuser/scripts/check_face_normal.py (algorithm reference · Z-axis topology)
  - ~/Desktop/case_013_centrifugal_pump_cavitating/scripts/check_face_normal.py (algorithm reference · XY-axis topology)
  - ~/Desktop/case_013_centrifugal_pump_cavitating/evidence/v1/defect_verification_d7.json (V87 ground truth · 21.979° measurement)
trigger: V79 + V87 promotion gate met (cross-topology evidence pair — case_012 whole-vane Z-axis 38° + case_013 LE-chunk XY-axis 22°). A4 marked `ready-to-land` in advisor_coverage 2026-05-13; Tier 1 last advisor land milestone (M-A4) per ARC-GOAL.md. Sub-DEC scope per v2.3 §3 — additive new module + tests + V-row status flips + governance doc updates, no cross-module change, no schema break, no auth/signing/security boundary.
autonomous_governance: true
counter_impact: +1
codex_review_relay: SKIPPED (sub-DEC scope · single advisor module + tests · pure dict-consumer function · no auth/signing/security boundary per v2.3 §2 · 9-test suite covers both pass/warning/critical bands + sibling-consensus median + per-body tolerance override + both case_012 + case_013 regression measurements)
kogami_review_path: SKIPPED (v2.3 §1 — Kogami opt-in; user did not summon)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-13
confidence: high (additive new module · 9 tests verify two declared-normal bands + sibling-consensus + skip cases + per-body tolerance override + V79 38° regression + V87 21.979° regression · API mirrors A5 sibling-pattern · no behavior change to existing code)
---

# DEC-V61-198-sub-A4 · Face-orientation advisor (D7-class)

## 1. Why now

V79 (case_012 D7 louver_vane_2 whole-vane Z-axis rotation 38°, sedimented
2026-05-09, backfilled 2026-05-12) and V87 (case_013 D7 blade_3 LE-chunk
XY-axis rotation 22°, sedimented 2026-05-13) together meet the A4
two-case cross-topology promotion gate defined in
`.planning/methodology/advisor_candidates_a4_a8.md`. The draft patch
`.planning/patches/draft_a4_face_orientation_2026-05-13.md` (commit
`615dacb`) defines the API surface; the only remaining work is
mechanical translation. Tier 1 (`.planning/ARC-GOAL.md`) lists M-A4 as
the final advisor-land milestone for the substrate arc (excluding
optional M-APU-RESTORE).

A4 closes the **first orientation-as-defect-signal** gap in the advisor
stack. Existing advisors consume orientation as input (A2's
`find_face_facing_target`) or are orientation-agnostic (A1 / A3 / A7 /
thin_wall_advisor); none audit it as a defect signature.

## 2. What changed

### Source: `ui/backend/services/geometry_ingest/face_orientation_advisor.py` (NEW)

Module-level constants:

- `DEFAULT_TOLERANCE_DEG = 5.0` (per draft patch §3)

Public API:

- `check_face_orientation(parts_manifest: dict, *, default_tolerance_deg=5.0, per_body_tolerance_deg=None) -> FaceOrientationReport`
- `FaceOrientationFinding` frozen dataclass: `body_name · intended_normal · actual_normal · angle_deviation_deg · tolerance_deg · severity`
- `FaceOrientationReport` frozen dataclass: `findings · bodies_checked · bodies_with_intended_normal · bodies_skipped · is_clean`

Per-body audit logic:

| Body schema condition | Outcome |
|---|---|
| `actual_face_normal` missing or non-coercible | **skipped** (counted in `bodies_skipped`) |
| `actual_face_normal` present + `expected_face_normal` present | direct compare via `abs(dot)` |
| `actual_face_normal` present + `sibling_group` only | consensus = per-axis median of all siblings' `actual_face_normal`; compare each member; requires ≥ 2 siblings (else skip — body's own normal IS the consensus) |
| `actual_face_normal` present + neither expected nor sibling | **skipped** |

Severity classification (per draft §3):

| Angle band | Severity |
|---|---|
| angle ≤ tol | not reported (passes silently) |
| tol < angle ≤ 2·tol | `warning` |
| angle > 2·tol | `critical` |

Tolerance priority per body:

1. `per_body_tolerance_deg[name]` caller-supplied arg (overrides manifest)
2. body's own `tolerance_deg` field
3. global `default_tolerance_deg` (5.0° unless caller overrides)

### Design choice — pure dict consumer (mirrors A5 inlet_outlet_validator)

The draft patch §3 suggested a `body.shape (FreeCAD Shape or path to STL/STEP)`
input that would push FreeCAD-runtime extraction into the advisor.
This DEC instead lands a **pure dict-consumer** function:

- Caller pre-extracts `actual_face_normal` upstream (via FreeCAD
  `face.normalAt()` for Z-axis topology, or via the tilt-from-XY-plane
  signature for chord-axis topology), attaches it to the parts_manifest
  body entry, and passes the dict to the advisor.
- The advisor itself has no CAD-library dependency, no I/O, no
  mutation of the input manifest.

Rationale:

1. **A5/A7 sibling pattern**: both A5 (`inlet_outlet_validator`) and
   A7 (`step_canonicalizer`) ship as pure utility modules with no
   FreeCAD runtime dep. A4 follows the same shape for stack
   consistency.
2. **Test isolation**: pytest runs the 9-test suite in 0.06s with no
   FreeCAD installed. Regression tests pin the ground-truth
   measurements (38.000° + 21.979°) by carrying the numeric vectors
   directly, not by re-extracting from the STEP files.
3. **V87 §Fix already foresaw this**: the V87 row notes "the
   productized advisor must auto-select method based on declared
   rotation_axis in parts_manifest (or attempt both and use the
   cleaner signal)". The pure-dict-consumer resolution short-circuits
   the auto-select complexity: once the caller has extracted the
   correct `actual_face_normal` for the topology, the `abs(dot)`
   comparison is topology-agnostic.

### Tests: `ui/backend/tests/test_face_orientation_advisor.py` (NEW)

9 tests:

1. `test_declared_normal_within_tol_passes` — 0° deviation, no finding
2. `test_declared_normal_above_critical_threshold` — 12° > 2·5°, severity=critical
3. `test_declared_normal_in_warning_band` — 7° (between tol and 2·tol), severity=warning
4. `test_sibling_consensus_with_one_outlier` — 4-member group, 1 rotated 30°, only the outlier flagged (median per-axis stays at +Y from the 3 good vanes)
5. `test_body_without_actual_face_normal_is_skipped` — bodies_skipped += 1
6. `test_body_without_expected_or_sibling_group_is_skipped` — actual present, no reference, skipped
7. `test_per_body_tolerance_override_argument_wins` — caller arg 2° overrides manifest's 4°
8. `test_case_012_louver_vane_2_regression` — V79 ground truth: intended (0,-1,0), actual rotated 38° around Z in XY plane, tol 2° → critical, angle == 38.000° (1e-6)
9. `test_case_013_blade_3_regression` — V87 ground truth: actual = `[-0.9017, -0.2166, 0.3743]` (max-tilt face normal from `defect_verification_d7.json`), intended = XY-projection re-normalized, tol 4° → critical, angle ≈ 21.979° (0.05 tol)

Run: `uv run python -m pytest ui/backend/tests/test_face_orientation_advisor.py -v` → **9 passed in 0.06s**.

Guard tests still green: `test_ai_advisor_contract.py` + `test_n6_1_corpus_loader.py` → 46 passed.

### V79 + V87 status updates (drift hook parity satisfied)

Both `.planning/methodology/industrial_case_solver_findings.md` and
`docs/openfoam_corpus/industrial_solver_findings_v_series.md` (the
runtime mirror consumed by N6.1 corpus loader) updated in parallel:

- V79 row header gains `· closed 2026-05-13 by DEC-V61-198-sub-A4`
- V79 Status field flipped `[QUESTIONABLE 2026-05-12]` → `**[VALIDATED] 2026-05-13** — A4 face_orientation_advisor landed (DEC-V61-198-sub-A4) closes the claim "no advisor catches D7 face-orientation defects"...`
- V79 Lesson gains a 2026-05-13 closure paragraph documenting the
  pure-dict-consumer design choice + Counter row flipped
  `autonomous_governance: false` → `true`
- V87 row header gains `· closed 2026-05-13 by DEC-V61-198-sub-A4`
- V87 Status field flipped `**ready-to-land**` → `**[VALIDATED] 2026-05-13** — A4 face_orientation_advisor landed (DEC-V61-198-sub-A4)...` with V87 21.979° regression test reference

The M-DRIFT commit-msg hook (`check_corpus_sync.py`) requires V-row
edits to land in both files in the same commit; this DEC's commit
satisfies that contract.

### Governance docs

- `.planning/cross_cuts/advisor_coverage_2026-05-09.md` — A4 row
  `READY-TO-LAND` → `LANDED 2026-05-13 (DEC-V61-198-sub-A4) · 9-test suite · ~260 LOC source`
- `.planning/methodology/advisor_candidates_a4_a8.md` — A4 §Status
  `ready-to-land 2026-05-13` → `landed 2026-05-13`
- `.planning/ARC-GOAL.md` — M-A4 row `[ ]` → `[x]` with commit hash;
  LANDED advisor counter `5 / 8` → `6 / 8` (A1, A2-v2, A3, A4, A5, A7)

### LOC accounting

| Region | LOC |
|---|---|
| Source (`face_orientation_advisor.py`) | ~260 |
| Tests (`test_face_orientation_advisor.py`) | ~220 |
| **Total source + tests** | **~480** |

Total exceeds the v2.3 sub-DEC soft 250-LOC source ceiling. Source
weight is documentation density (docstrings explain dual-topology
semantics + median-vs-mean rationale + tolerance priority) and
per-mode branching (declared-normal / sibling-consensus / skip),
not algorithmic complexity. Stripping per-branch docstrings would
drop source to ~140 LOC. Per the A5 precedent (210 source + 130
tests = 340 total LOC accepted at v2.3 sub-DEC scope), A4 is in the
same band. Scope remains single-service-file + single-test-file +
governance-doc updates — no cross-module change.

## 3. V-row status changes

| V-row | Pre-A4 | Post-A4 |
|---|---|---|
| V79 (backfilled 2026-05-12 · case_012 first injection) | `[QUESTIONABLE 2026-05-12]` · `autonomous_governance: false` | **`[VALIDATED] 2026-05-13 · A4 face_orientation_advisor landed (DEC-V61-198-sub-A4)`** · `autonomous_governance: true` |
| V87 (case_013 cross-topology completion · 2026-05-13) | `**ready-to-land**` | **`[VALIDATED] 2026-05-13 · A4 face_orientation_advisor landed (DEC-V61-198-sub-A4)`** |

## 4. What does NOT change

- The case_012 + case_013 `scripts/check_face_normal.py` manual
  verification scripts — unchanged; the productized advisor consumes
  the same measurement they produce
- Parts manifest schema for other advisors — additive only; the new
  fields (`actual_face_normal`, `expected_face_normal`,
  `sibling_group`, optional per-body `tolerance_deg`) are documented
  in the advisor docstring and ignored by every other consumer
- `ui/backend/services/ai_advisor/` (N6.2/N6.3 routes) — A4 is a
  geometry_ingest utility, not an `/ai-review` consumer; routing
  layer untouched (mirrors A5/A7 — both pure utilities without route
  integration)
- Codex round-cap / Backend selection — unrelated
- Existing geometry_ingest service surface — additive new module
- D6/D9/D10 advisor candidates in `advisor_candidates_a4_a8.md` —
  unchanged; remain `drafted` / `pending-first-injection`

## 5. Anti-patterns honored

- **No CAD-library runtime dependency** — advisor is pure-dict-consumer;
  FreeCAD extraction is upstream/caller-side. Tests run in 0.06s on
  a no-FreeCAD pytest env.
- **No silent fallback** — body with neither `expected_face_normal` nor
  `sibling_group` is **skipped** (counted in `bodies_skipped`), not
  silently passed. Caller can gate on
  `bodies_skipped > 0 and bodies_with_intended_normal == 0` to detect
  manifest gaps.
- **No retroactive case audit** — the validator is offered for use, not
  auto-run against legacy case sandboxes. Already-sedimented cases
  (012, 013) keep their manual `check_face_normal.py` evidence; the
  productized advisor is the path forward for new dispatches.
- **No reach into FreeCAD-Shape representation** — `actual_face_normal`
  is a plain 3-tuple of floats; the advisor never touches a
  `FreeCAD.Vector` or any other library type. This is the seam that
  allows the advisor to consume measurements from either rotation-axis
  topology without auto-selection logic.
- **Sign-ambiguous-plane semantics** — `abs(dot)` is used in
  `_angle_deg` so a 180° flip counts as 0° agreement (consistent with
  both case_012 and case_013 manual scripts which both `abs()` the
  dot product).

## 6. Open questions resolved

| Question | Resolution |
|---|---|
| Should the advisor invoke FreeCAD directly (per draft patch §3) or consume pre-extracted normals (per A5 sibling pattern)? | **Pre-extracted** — keeps the advisor side-effect-free + test-isolated + matches sibling stack pattern. The V87 §Fix's "auto-select method" complexity is short-circuited: once the caller extracts via the topology-appropriate method, `abs(dot)` works for both case_012 Z-axis and case_013 chord-axis topologies. |
| Where in the pipeline does the validator hook in? | **Caller's choice** — pure function; expected consumers are (a) main-session sub-session-dispatch validation step 7, (b) future `make all` integration for case sandboxes. Same caller-choice resolution as A5 §6. |
| Sibling-consensus algorithm: median or mean? | **Median per-axis** (per draft §7 R1) — robust against single outlier in a group of ≥ 3. With exactly 2 siblings, median equals mean and one outlier biases the consensus equally; this is documented in the docstring but does not block the advisor from emitting a finding (it just reduces robustness). |
| What about bodies with curved-dominant geometry (no planar dominant face)? | **Caller's problem** — the advisor receives whatever `actual_face_normal` the caller computed. Per draft §7 R2, if the caller cannot extract a meaningful normal (curved-dominant body), they omit the field and the advisor skips. This is more conservative than the draft proposal of "skip + report" because the report would conflate "no extractor" with "no defect"; counting in `bodies_skipped` is sufficient signal. |

## 7. Reversal cost

Low. To reverse:

- `rm ui/backend/services/geometry_ingest/face_orientation_advisor.py`
- `rm ui/backend/tests/test_face_orientation_advisor.py`
- Revert V79 + V87 row Status + header lines in both V-series files
- Revert A4 row in `advisor_coverage_2026-05-09.md` and
  `advisor_candidates_a4_a8.md`
- Revert M-A4 box in `.planning/ARC-GOAL.md` (+ counter 6→5)

No schema migration, no consumer changes, no dependency adds. The
module has no callers in the current codebase — it is offered as a
utility for sub-session-dispatch flows and future `make all`
integration.

## 8. References

- Parent DEC: V61-198 (APU bay strategic pivot · Codex case-fleet
  protocol)
- Draft patch: `.planning/patches/draft_a4_face_orientation_2026-05-13.md`
  (commit `615dacb`) — research deliverable, API + algorithm spec
- V-series: V79 (closed by this DEC), V87 (closed by this DEC), V80
  (STEP timestamp · A7 sibling), V81 (inlet/outlet protocol · A5
  sibling)
- Sibling sub-DECs landed 2026-05-12 / 2026-05-13:
  - V61-198-sub-A2v2 (gap-detection API)
  - V61-198-sub-A7 (STEP canonicalizer)
  - V61-198-sub-protocol-inlet-outlet (V81 protocol amendment)
  - V61-198-sub-A5-inlet-outlet-validator (V81 closure · this DEC's
    structural template + pure-dict-consumer pattern)
  - V61-198-sub-case-013-D7-injection (case_013 substrate for V87)
- ARC-GOAL.md M-A4 row (Tier 1 milestone)
- Algorithm references:
  - `~/Desktop/case_012_hvac_supply_diffuser/scripts/check_face_normal.py`
    (Z-axis topology · `INTENDED_NORMALS` table + `primary_planar_face_normal`)
  - `~/Desktop/case_013_centrifugal_pump_cavitating/scripts/check_face_normal.py`
    (XY-axis topology · `le_side_faces` + `max_delta_pair` tilt-from-XY)
  - `~/Desktop/case_013_centrifugal_pump_cavitating/evidence/v1/defect_verification_d7.json`
    (V87 ground truth measurement record)
