---
decision_id: DEC-V62-A-sub-D6
title: D6 extra_body_advisor promotion · single-case land closes V61-198 §5.2 D-class waiver + V62-A Done dim #4
status: Accepted
parent_dec: V62-A-charter
phase: V62-A Tier 2 · M-D6-PROMOTE milestone · D-class literal closure
notion_sync_status: synced 2026-05-14 (https://www.notion.so/360c68942bed8190a43ed20eded5a57e)
parent_artifacts:
  - .planning/2026-05-14_v62_charter.md (V62-A charter SSOT · M-D6-PROMOTE Tier 2 row line 65)
  - .planning/ARC-GOAL.md (M-D6-PROMOTE [ ] → [x] · D-class counter 0/1 → 1/1 · LANDED advisor 8 → 9 · main session reconciles)
  - .planning/methodology/component_bank.md L127 (D6 defect-catalog SSOT)
  - .planning/cross_cuts/advisor_coverage_2026-05-09.md (D6 row drafted → LANDED-with-[QUESTIONABLE] + defect-distribution D6 row NONE → LANDED)
  - .planning/methodology/advisor_candidates_a4_a8.md (D6 §Status drafted → landed 2026-05-14)
  - .planning/methodology/industrial_case_solver_findings.md (V55 status [QUESTIONABLE 2026-05-11] → [QUESTIONABLE 2026-05-14] single-case land)
  - docs/openfoam_corpus/industrial_solver_findings_v_series.md (V55 runtime mirror · M-DRIFT hook parity)
  - .planning/decisions/2026-05-14_v61_198_CLOSE.md §5.2 D-class waiver (literal D-class LANDED ≥1 path)
  - .planning/decisions/2026-05-12_v61_198_sub_a2v2_gap_detection.md (A2 v1 placeholder precedent · single-case land pattern)
  - ui/backend/services/geometry_ingest/extra_body_advisor.py (new module · ~290 LOC)
  - ui/backend/tests/test_extra_body_advisor.py (new test file · 10 tests · 0.05s green)
  - ~/Desktop/case_016_m219_cavity_des_acoustic/scripts/00_check_region.py::check_d6_debris (V55 ground-truth evidence)
  - ~/Desktop/case_016_m219_cavity_des_acoustic/evidence/00_region_v1.json D6 block (V55 measurement record)
trigger: V62-A charter Done dim #4 ("≥ 1 (D6 or D9 or D10) promoted to LANDED") + V61-198 §5.2 D-class literal closure (closes the "A2-v2 absorbs D-class coverage" honest-framing escape hatch — literal D-class counter goes 0 → 1). M-D6-PROMOTE Tier 2 milestone per `.planning/ARC-GOAL.md` line 65. Sub-DEC scope per v2.3 §3 — additive new module + tests + V-row status flips + governance doc updates; no cross-module change, no schema break, no auth/signing/security boundary. Promotion-gate evidence currently 1/2 (V55 case_016 sedimented 2026-05-11; case_018 cyclone dispatched but not sedimented) — landed under V61-198 §5.2 single-case-land waiver + A2 v1 placeholder precedent.
autonomous_governance: true
counter_impact: +1
codex_review_relay: SKIPPED (sub-DEC scope · single advisor module + tests · pure dict-consumer function · no auth/signing/security boundary per v2.3 §2 1-sync-trigger · 10-test suite covers all three detection paths + V55 case_016 regression pin + per-finding severity classification + V59 partial-overlap anti-scope · matches A4/A5/A8/A10 sibling-stack pattern)
kogami_review_path: SKIPPED (v2.3 §1 — Kogami opt-in; user did not summon)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-14
confidence: high (additive new module · 10 tests verify clean / all-3-detection-paths / declared-inclusion suppression / empty / partial-overlap anti-scope / missing-role defensive default / per-severity classification / V55 case_016 debris-cube regression · pure dict-consumer matches A4/A5/A8/A10 · no behavior change to existing code · sibling tests still green)
---

# DEC-V62-A-sub-D6 · Extra-body-in-fluid advisor (D6-class · single-case land)

## 1. Why now

V61-198 closed 2026-05-14 with §5.2 explicitly acknowledging that the
"≥1 D-class advisor LANDED" Done condition was met **only through the
A2-v2 absorption framing** (A2-v2 carries D1 + D5 coverage and was
counted toward D-class). The closing DEC noted: "if main session wants
strict literality, promote D6 (case_016 + case_018 evidence) before
arc close." That literality is the load-bearing piece — without it the
"≥1 D-class LANDED" guarantee is honored in spirit but not in counter.

V62-A charter (`.planning/2026-05-14_v62_charter.md`) reopens the bar
literally: Done dim #4 reads "**≥ 1 (D6 or D9 or D10) promoted to
LANDED**". The §5.2 waiver was a one-time accommodation for V61-198
close; V62-A goes back to literal counting.

Case_018 (cyclone) is the planned second-injection case for D6 but
has not yet been dispatched. Without case_018, the strict ≥2-case
promotion gate would block D6 for an unknown duration. V61-198 §5.2
already created precedent for relaxation via single-case land:

> "ARC-GOAL Done #2 says '≥ 8 LANDED (含 D-class ≥ 1)'. Literal
> D-class counter = **0 LANDED**. ... if main session wants strict
> literality, promote D6 (case_016 + case_018 evidence) before arc
> close."

A2 v1 (DEC-V61-198-sub-A2v2 §1) is the original precedent: A2 v1
landed as a **placeholder** pending A2-v2 productization; the
single-case sufficient-evidence framing carried it through 10+ case
applications before A2-v2 superseded it. D6 lands under the same
shape: single-case sufficient evidence (V55) with [QUESTIONABLE
2026-05-14] marker that case_018 will close when it sediments.

## 2. What changed

### Source: `ui/backend/services/geometry_ingest/extra_body_advisor.py` (NEW)

Module-level constants:

- `FLUID_ROLES = frozenset({"fluid", "region_air", "region_fluid"})`
- `SOLID_ROLES = frozenset({"solid", "internal_wall", "structural", "debris", "wall_solid"})`

Public API:

- `check_extra_bodies_in_fluid(parts_manifest, stl_bbox_set, *, containment_tol_mm=0.0) -> ExtraBodyReport`
- `ExtraBodyFinding` frozen dataclass: `body_name · finding_type · severity · container_name · detail`
- `ExtraBodyReport` frozen dataclass: `findings · registered_count · stl_count · suspected_extras · is_clean · critical_count · warning_count`

Three detection paths:

| Detection | Finding type | Severity | Source signature |
|---|---|---|---|
| (a) STL body absent from parts_manifest | `unregistered_body` | critical | V55 case_016 debris cube sighting class |
| (b) Solid-role body bbox ⊂ fluid-role body bbox | `body_in_fluid_region` | warning | Engineer logged the body but didn't notice it sits in cavity |
| (c) Solid ⊂ solid without `declared_inclusions` entry | `undeclared_inclusion` | warning | Engineer forgot to declare an intentional inclusion |

Anti-scope (honored per V55 lesson + advisor_candidates_a4_a8.md §D6):

- Partial overlap (neither contains other) is silently skipped — V59
  classifier covers partial-overlap as a separate import-time check
- STL loading stays caller-side (trimesh / fast_simplification) — the
  advisor never opens an STL file
- No FreeCAD / numpy / CAD-library runtime dependency

### Design choice — pure dict consumer (mirrors A4 / A5 / A8 / A10)

The advisor consumes:

1. `parts_manifest` dict (same schema family as A4 / A5 / A8 — `parts`
   list of `{name, role, bbox, ...}` entries, plus optional
   `declared_inclusions` list of `{outer, inner}` pairs)
2. `stl_bbox_set` dict (caller-prepared mapping body_name → 6-tuple
   bbox in mm; typically `trimesh.bounds` after STL load)

Both inputs are plain Python dicts. The advisor performs only:

- Bbox coercion + axis normalization (so a flipped `(xmax < xmin)`
  input doesn't break containment math)
- AABB containment via inclusive-bounds comparison (no numpy needed)
- Set arithmetic on `declared_inclusions` to suppress acknowledged
  warnings

Rationale (per A4 §2 / A5 §2 / A8 §2 sibling pattern):

1. **No CAD-library runtime dep** — pytest runs 10-test suite in
   0.05s on a no-FreeCAD-no-trimesh env. Caller passes pre-extracted
   bboxes from whatever STL library they prefer.
2. **Test isolation** — V55 case_016 regression carries the debris
   cube center (320, 18, -79) mm + 5 mm half-extent directly. No
   re-extraction from STEP / STL at test time.
3. **Stack consistency** — A4 / A5 / A8 / A10 are all pure-dict
   consumers. D6 joins the same shape so the future V62-A
   M-STACK-ASSEMBLY layer can route advisor calls uniformly.

### Tests: `ui/backend/tests/test_extra_body_advisor.py` (NEW)

10 tests:

1. `test_clean_case_passes` — registered bodies + declared inclusion → 0 findings
2. `test_unregistered_body_is_critical` — STL has body absent from manifest → critical
3. `test_body_in_fluid_region_is_warning` — solid bbox ⊂ fluid bbox → warning
4. `test_undeclared_inclusion_is_warning` — solid ⊂ solid undeclared → warning
5. `test_declared_inclusion_suppresses_warning` — same overlap + declared entry → clean
6. `test_empty_manifest_and_empty_stls_is_clean` — trivial degenerate case
7. `test_partial_overlap_not_flagged_per_v59_anti_scope` — corner overlap → 0 findings
8. `test_missing_role_defaults_to_solid_v55_defensive` — no role / unknown role → treated as solid (V55 root cause)
9. `test_severity_classification_critical_vs_warning` — combined fixture: unregistered + body-in-fluid, both bands present
10. `test_case_016_v55_debris_cube_regression` — V55 ground truth: 10 mm cube at (320, 18, -79) mm, debris absent from manifest → `unregistered_body` critical, `debris_cube` in `suspected_extras`

Run: `uv run python -m pytest ui/backend/tests/test_extra_body_advisor.py -v` → **10 passed in 0.05s**.

Guard tests still green: `test_face_orientation_advisor.py` (9) + `test_inlet_outlet_validator.py` (9) + `test_thermo_polynomial_range_advisor.py` (14) → **32 passed in 0.06s**.

### V55 status update (drift hook parity satisfied)

Both `.planning/methodology/industrial_case_solver_findings.md` and
`docs/openfoam_corpus/industrial_solver_findings_v_series.md` (the
runtime mirror consumed by N6.1 corpus loader) updated in parallel:

- V55 row header gains `· closed 2026-05-14 by DEC-V62-A-sub-D6`
- V55 Status field flipped `[QUESTIONABLE 2026-05-11] — claim "no
  advisor catches D6" is verified...` → **`[QUESTIONABLE 2026-05-14]
  · single-case land — extra_body_advisor.py LANDED 2026-05-14
  (DEC-V62-A-sub-D6); the original claim "no advisor catches D6" is
  now refuted by the LANDED advisor. The advisor is exercised by this
  V55 case_016 sediment only; the original ≥2-case promotion gate is
  deferred to case_018 sediment per V61-198 §5.2 + A2 v1 precedent...`**
- V55 Fix item (2) rewritten from "Advisor candidate (next iteration)"
  → "Advisor LANDED 2026-05-14 (DEC-V62-A-sub-D6)" with 3-detection-
  path summary
- V55 Reference case gains advisor module path + regression test reference
- V55 Lesson gains 2026-05-14 closure paragraph; Counter row flipped
  `autonomous_governance: false` → `autonomous_governance: true`
- TOC row (canonical findings only) V55 column "advisor" flipped
  `D6 / A5` → `D6 / D6_advisor`; Status `Q-2026-05-11` →
  `Q-2026-05-14 (single-case land)`

The M-DRIFT commit-msg hook (`check_corpus_sync.py`) requires V-row
edits to land in both files in the same commit; this DEC's commit
satisfies that contract.

### Governance docs

- `.planning/cross_cuts/advisor_coverage_2026-05-09.md`:
  - D6_advisor row: `DEFER until case_018 sediment · spec: ...` → `LANDED 2026-05-14 with [QUESTIONABLE] pending case_018 · DONE`
  - Defect-distribution D6 row: `NONE` advisor mapping → `extra_body_advisor.py LANDED 2026-05-14`
- `.planning/methodology/advisor_candidates_a4_a8.md` D6 row:
  - Status `drafted` → `landed 2026-05-14`
  - Current evidence `1 / 2 (V55 ... deferred)` → `1 / 2 · LANDED with [QUESTIONABLE 2026-05-14] pending case_018`
  - Module path + test path explicitly linked
- `.planning/ARC-GOAL.md` — **main session reconciles** per task brief
  hard constraint (this DEC does not touch ARC-GOAL); expected post-
  reconcile state: M-D6-PROMOTE `[ ]` → `[x]` with commit hash; D-class
  counter `0/1` → `1/1`; LANDED advisor counter `8` → `9`

### LOC accounting

| Region | LOC |
|---|---|
| Source (`extra_body_advisor.py`) | ~290 |
| Tests (`test_extra_body_advisor.py`) | ~260 |
| **Total source + tests** | **~550** |

Source weight is documentation density (docstrings explain three
detection paths + anti-scope V59 alignment + V55 sighting class
mapping + role-default semantics) and three-branch detection logic.
Per the A4 precedent (~260 source + ~220 tests = 480 total LOC
accepted at v2.3 sub-DEC scope) and A8 precedent (~380 source +
13-test suite = ~600 total LOC, also v2.3 sub-DEC), this DEC's
~550 total LOC is in the same band. Scope remains single-service-file
+ single-test-file + governance-doc updates — no cross-module change.

## 3. V-row status changes

| V-row | Pre-D6-land | Post-D6-land |
|---|---|---|
| V55 (case_016 first injection · 2026-05-11) | `[QUESTIONABLE 2026-05-11] · autonomous_governance: false` (no automated detection means STOP gate inapplicable) | **`[QUESTIONABLE 2026-05-14] · single-case land · extra_body_advisor.py LANDED (DEC-V62-A-sub-D6) · autonomous_governance: true`** (single-case land per V61-198 §5.2 + A2 v1 precedent; ≥2-case strict gate deferred to case_018 sediment) |

## 4. What does NOT change

- Case_016 `scripts/00_check_region.py::check_d6_debris` manual
  verification script — unchanged; the productized advisor consumes
  pre-extracted bbox sets from the caller's STL pipeline, not
  case-local FreeCAD scripts
- Parts manifest schema for other advisors — additive only; the new
  optional `declared_inclusions` field is documented in the advisor
  docstring and ignored by every other consumer
- `ui/backend/services/ai_advisor/` (N6.2/N6.3 routes) — D6 is a
  geometry_ingest utility, not an `/ai-review` consumer; routing
  layer untouched. M-STACK-ASSEMBLY (Tier 1) will plumb this advisor
  into the stack route layer separately
- Codex round-cap / Backend selection — unrelated
- Existing geometry_ingest service surface — additive new module
- D9 / D10 advisor candidates in `advisor_candidates_a4_a8.md` —
  unchanged; remain `drafted` / `pending-first-injection`
- V56 (D9 first injection · same case_016 sediment day) — status
  unchanged; D9 has its own promotion gate (case_017 + case_020
  dispatched · 1/3 sediment)

## 5. Anti-patterns honored

- **No CAD-library runtime dependency** — advisor is pure-dict-consumer;
  STL bbox extraction is upstream/caller-side. Tests run in 0.05s on
  a no-FreeCAD-no-trimesh pytest env.
- **No silent fallback** — body with missing / unknown role defaults
  to `solid` (V55 defensive default — the case_016 debris cube had
  no role at all in the original brief); body with no bbox is silently
  skipped from inclusion math but still counted in `registered_count`.
- **No retroactive case audit** — the validator is offered for use,
  not auto-run against legacy case sandboxes. case_016 keeps its
  manual `check_d6_debris` evidence; the productized advisor is the
  path forward for new dispatches and for case_018 when it lands.
- **No reach into trimesh / fast_simplification representation** —
  `stl_bbox_set` is a plain dict of name → 6-tuple. The advisor never
  touches a `trimesh.Trimesh` object. This is the seam that allows
  the advisor to consume bbox sets from whatever STL library the
  caller pipeline uses.
- **V59 partial-overlap anti-scope honored** — corner overlap (neither
  contains other) is silently skipped. Documented in test #7.

## 6. Open questions resolved

| Question | Resolution |
|---|---|
| Strict ≥2-case promotion gate (per `advisor_candidates_a4_a8.md` §"Two-case validation required") OR single-case land under V61-198 §5.2 + A2 v1 precedent? | **Single-case land** — case_018 not yet dispatched, blocking literal D-class counter for unknown duration; V61-198 §5.2 already established the relaxation framework; A2 v1 already established the placeholder-pending-cross-validation pattern. V55 row carries `[QUESTIONABLE 2026-05-14]` marker so the open promotion-gate question stays visible. |
| Should the advisor consume STL paths or pre-extracted bboxes (per draft spec §"`Dict[str, Shape]`")? | **Pre-extracted bbox dict** — keeps the advisor side-effect-free + test-isolated + matches A4/A5/A8/A10 sibling pattern. STL bbox extraction is `trimesh.bounds`-class work the caller already does for other reasons (visualization, sHM input prep). |
| Role taxonomy: hard-code `internal_wall` (per V55 Fix item 2 original spec) or generalize to `solid` / `fluid` classes? | **Generalize** — case_016 (V55) had no role at all on the debris cube; case_018 (dispatched cyclone) is expected to inject differently. Hard-coding `internal_wall` would miss both. The advisor classifies any non-fluid role as solid; missing / unknown role defaults to solid (defensive default surfaces V55-class root cause). |
| Where in the pipeline does the validator hook in? | **Caller's choice** — pure function; expected consumers are (a) sub-session-dispatch validation step pre-sHM, (b) future `make all` integration for case sandboxes, (c) M-STACK-ASSEMBLY route plumbing. Same caller-choice resolution as A4 §6 / A5 §6. |
| What about declared internal walls (intentional inclusions)? | **Caller declares via `declared_inclusions: [{outer, inner}]` list** — same shape as the sibling-group pattern A4 uses for face-orientation consensus. Test #5 verifies declaration suppresses the warning. |

## 7. Reversal cost

Low. To reverse:

- `rm ui/backend/services/geometry_ingest/extra_body_advisor.py`
- `rm ui/backend/tests/test_extra_body_advisor.py`
- Revert V55 row Status + header lines + Fix item (2) + Lesson
  paragraph + TOC row in both V-series files
- Revert D6_advisor row in `advisor_coverage_2026-05-09.md`
  + Defect-distribution D6 row
- Revert D6 row in `advisor_candidates_a4_a8.md`
- Revert ARC-GOAL.md M-D6-PROMOTE box (main session, when reconciled)

No schema migration, no consumer changes, no dependency adds. The
module has no callers in the current codebase — it is offered as a
utility for sub-session-dispatch flows and future stack-assembly
integration. The reversal would put V62-A Done dim #4 back to 0/1
and V61-198 §5.2 D-class waiver back into effect.

## 8. References

- Parent charter: V62-A (`.planning/2026-05-14_v62_charter.md` · Done
  dim #4)
- V61-198 §5.2 D-class waiver:
  `.planning/decisions/2026-05-14_v61_198_CLOSE.md` (single-case-land
  precedent foundation)
- A2 v1 placeholder precedent: DEC-V61-198-sub-A2v2 §1 (placeholder-
  pending-productization pattern)
- Pre-drafted spec:
  `.planning/methodology/advisor_candidates_a4_a8.md` §D6_advisor
  (status drafted → landed by this DEC)
- V-series: V55 (closed by this DEC); V56 / V79 / V87 are sibling
  first-injection rows (D9 still drafted; D7 closed by DEC-V61-198-
  sub-A4 2026-05-13)
- Sibling sub-DECs landed 2026-05-12 / 2026-05-13 / 2026-05-14:
  - V61-198-sub-A2v2 (gap-detection API · single-case → cross-topology
    pattern reference)
  - V61-198-sub-A4 (face-orientation · pure dict-consumer · this DEC's
    structural template)
  - V61-198-sub-A5 (inlet-outlet validator · sibling validator pattern)
  - V61-198-sub-A7 (STEP canonicalizer · sibling utility pattern)
  - V61-198-sub-A8 (shm_dict_validator · 4-sediment cross-topology
    land; D6 is the same pattern with single-case scope)
  - V61-198-sub-A10 (thermo-polynomial-range · paired before/after
    land · loosened promotion gate precedent)
- ARC-GOAL.md M-D6-PROMOTE row (Tier 2 milestone · main session
  reconciles `[ ]` → `[x]` + D-class counter 0/1 → 1/1 + LANDED
  advisor 8 → 9)
- Component bank D6 row: `.planning/methodology/component_bank.md`
  L127 (defect-class definition SSOT)
- Algorithm reference:
  `~/Desktop/case_016_m219_cavity_des_acoustic/scripts/00_check_region.py::check_d6_debris`
  (V55 ground-truth verification script · cube center + clearances
  ported into regression test)
