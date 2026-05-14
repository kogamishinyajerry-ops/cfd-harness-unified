---
decision_id: DEC-V62-A-sub-D10
title: D10 bc_type_name_validity_advisor — fork-aware BC catalog lookup (single-case land · V29 evidence)
status: Accepted
parent_dec: DEC-V62-A-charter
phase: V62-A Tier 2 supplement · driven by M-STACK-TRACK-3 §gap2
notion_sync_status: synced 2026-05-14 (https://www.notion.so/360c68942bed8109bc6adb6594450262)
---

## Status

Accepted · 2026-05-14 · single-case-land per A2 v1 / D6 precedent ·
pending 2nd-case cross-validation (carry [QUESTIONABLE] marker until
a second case sediments using foam-extend BC names or a typo BC name
that the unknown-class severity catches in the field).

## Goal (verbatim from M-STACK-TRACK-3 §gap2)

> **A5 `inlet_outlet_validator` does not inspect `bc:` block BC-type
> names** (new) — V29 documents 6 case_006 parts using foam-extend-only
> BC names that don't exist in `opencfd/openfoam-default:2312`. Solver
> would crash on these at runtime, but the stack never warns because
> A5 short-circuits on `role` outside THROUGH_FLOW_ROLES. **D-class
> candidate**: `bc_type_name_validity_advisor` checking each part's
> `bc.{U,p,T,nut,k,omega}` field-value against a known-BC-name catalog
> per OpenFOAM fork. Single highest-leverage net-new advisor for
> compressible cases.
>
> — `.planning/retrospectives/2026-05-14_stack_track_c_session_3_case_006.md`
> §5 (V29 row) + §7 item 2 + §9 item 3.

D10 closes that gap. Each declared BC type name is classified against
three frozensets (`STANDARD_OPENFOAM_BCS` / `FOAM_EXTEND_ONLY_BCS` /
`SENTINEL_BC_NAMES`) and the verdict + active fork pick the severity.

## Scope

**This sub-DEC adds:**

- `ui/backend/services/geometry_ingest/bc_type_name_validity_advisor.py`
  (~450 LOC including docstrings + 3 frozen-set catalogs + 4 dataclasses
  + 3 public functions: `check_bc_type_name_validity` /
  `detect_invalid_bc_types` / `extract_bc_specs_from_parts_manifest`)
- `ui/backend/tests/test_bc_type_name_validity_advisor.py` (13 tests
  covering standard pass / foam-extend-only critical / foam-extend
  fork tolerance / unknown typo warning / sentinel pass / parts_manifest
  adapter / case_006 V29 6-declaration regression / 4Q gate no-LLM /
  4Q gate no-writes / invalid-input defensive / fork=unknown branch /
  catalog disjointness)
- `ui/backend/services/advisor_stack.py` registration:
  - `_V_ROWS_PER_ADVISOR["bc_type_name_validity_advisor"] = ("V29",)`
  - `_normalize_bc_type_name(report)` helper
  - `assemble_stack(..., bc_specs=None, bc_fork="main", ...)` signature
    addition (forward-compatible · existing callers see zero behavior
    change when neither kwarg is provided AND parts_manifest carries no
    `bc:` blocks)
  - Dispatch path: explicit `bc_specs` win; else auto-extract from
    `parts_manifest['parts'][*]['bc']` blocks via the adapter
- `ui/backend/tests/test_advisor_stack.py` 4 new tests:
  - `test_bc_specs_dispatches_d10_with_v29_evidence`
  - `test_parts_manifest_with_bc_blocks_auto_extracts_d10`
  - `test_bc_specs_explicit_wins_over_parts_manifest_extraction`
  - `test_bc_fork_foam_extend_tolerates_characteristic_family`
- `ui/backend/routes/ai_review.py` wire-schema expansion:
  - `AIReviewRequest.bc_specs: Optional[list[dict[str, Any]]] = None`
  - `AIReviewRequest.bc_fork: Optional[str] = None`
  - Plumb to `assemble_stack(**stack_kwargs)`
- `ui/backend/tests/test_ai_review_route.py` 3 new route tests:
  - `test_bc_specs_explicit_dispatches_d10_with_v29_evidence`
  - `test_parts_manifest_bc_blocks_auto_extract_to_d10`
  - `test_bc_fork_foam_extend_tolerates_characteristic_family`

## This sub-DEC does NOT add

To keep the scope surgical and defendable as `confidence: med` (not
charter):

- ❌ BC *value* numeric validity checks (e.g., negative `totalPressure`,
  out-of-range `flowRateInletVelocity volumetricFlowRate`). Value-range
  is a separate advisor class (A10 thermo-range is the only such
  LANDED today).
- ❌ BC *consistency* across coupled fields (V19 / V11 territory —
  `fixedValue U` paired with `zeroGradient p` violating SIMPLE / PIMPLE
  algorithm). Belongs to a per-field-pair checker, not this catalog-
  based name validator.
- ❌ `patch type` checks (`boundary` file `type wall;` vs `type patch;`
  vs `type symmetryPlane;`). A8 `shm_dict_validator` is the SSOT.
- ❌ Patch-geometry / inlet-outlet topology mistakes — **A5
  `inlet_outlet_validator` is the SSOT for that. D10 supplements A5,
  does NOT replace it.** A5 reads `role:` + topology; D10 reads `bc:`
  + literal type name.
- ❌ `case_dir/<polyMesh>/boundary` parsing as an auto-discovery
  source. Auto-discovery is via `parts_manifest['parts'][*]['bc']`
  blocks only (already the project-canonical source; polyMesh/boundary
  parsing is a future widening).
- ❌ D6 `extra_body_advisor` stack plumbing (separate sub-DEC per
  REQ-SCHEMA-EXPAND closing note).
- ❌ Any mutation of `case_dir` — V130 advisor-not-driver: D10 only
  ever returns a frozen `BcTypeNameReport`; the caller decides what
  to do.
- ❌ Notion sync for this sub-DEC at land time — per v2.3 round-1
  loosen rule, Notion sync happens at session-end batch only for
  `status: Accepted` DECs.
- ❌ Pre-merge Codex review — no security boundary touched (the route
  expansion is read-only, no new auth surface). Per v2.3 1-sync-trigger
  rule, this is `confidence: high` on Opus self-judgment for the route
  diff (5 wire fields + 2 stack kwargs) and `confidence: med` on the
  catalog completeness (single-case-land precedent).

## Catalog provenance

- **`STANDARD_OPENFOAM_BCS`** (61 entries): derived from OpenFOAM-ESI
  v2412 documentation
  (https://www.openfoam.com/documentation/guides/v2412/doc/) Boundary
  Conditions section, cross-checked against `opencfd/openfoam-default:2312`
  Docker image's BC registry (project default substrate for case_006 /
  011 / 016). Intentionally non-exhaustive — OpenFOAM ships 200+
  registered patchField subclasses across the inlet/outlet/wall-function/
  thermal-coupling/coded namespaces; the advisor's value is catching
  foam-extend-vs-ESI mismatches and typos, not enforcing closure over
  a moving registry. Catalog policy: additions append-only; removals
  require a sub-DEC (because removing a name silently flips passing
  cases to `unknown → warning`).
- **`FOAM_EXTEND_ONLY_BCS`** (6 entries): derived from foam-extend-5.0
  release notes (https://sourceforge.net/p/foam-extend/foam-extend-5.0/)
  + case_006 retro V29 enumeration. Covers the `characteristic*` BC
  family that ESI deprecated circa OpenFOAM-3.x in favor of `freestream`
  / `waveTransmissive`.
- **`SENTINEL_BC_NAMES`** (5 entries: `none` / `none_volume_reference` /
  `n/a` / `na` / `placeholder`): project-internal placeholders observed
  in `case_006/inputs/parts_manifest.yaml` (`farfield_reference` body
  declares `none_volume_reference` for U/p/T) and similar non-emitted-
  patch sentinel patterns across case profiles. Membership is lowercase-
  insensitive.

Catalog disjointness is enforced at test time via
`test_catalogs_are_disjoint` — a name appearing in two frozensets would
cause verdict ambiguity, so the test fires the day someone misplaces
an entry.

## Test catalog boundary evidence

| boundary case | input | expected verdict | actual |
|---|---|---|---|
| canonical ESI BC | `noSlip` | `valid_standard` / pass | ✓ |
| wall function | `kqRWallFunction` | `valid_standard` / pass | ✓ |
| compressible CHT BC | `compressible::turbulentTemperatureCoupledBaffleMixed` | `valid_standard` / pass | ✓ |
| ESI freestream replacement | `freestream` | `valid_standard` / pass | ✓ |
| foam-extend BC on main fork | `characteristicPressureInletOutletPressure` (fork=main) | `valid_foam_extend_only` / **critical** | ✓ |
| foam-extend BC on foam-extend fork | same name (fork=foam-extend) | `valid_foam_extend_only` / info (suppressed) | ✓ |
| foam-extend BC on unknown fork | same name (fork=unknown) | `valid_foam_extend_only` / warning | ✓ |
| typo | `fixedValeu` | `unknown` / warning | ✓ |
| typo with capital-I-for-l | `totaIPressure` | `unknown` / warning | ✓ |
| sentinel | `none_volume_reference` | `valid_sentinel` / info (suppressed) | ✓ |
| empty input | `[]` | empty report, `is_clean=True` | ✓ |
| None input | `None` | empty report, no raise | ✓ |
| non-dict entries | `["string", 42, None, {...valid...}]` | only valid entry counted; rest silently skipped | ✓ |
| non-string bc_type | `check_bc_type_name_validity(123)` | TypeError | ✓ |
| case_006 V29 6-declaration replay | 3 farfield parts × {U=characteristic*, p=characteristic*, T=freestream} | 6 critical findings, all naming foam-extend BC + carrying ESI fix hint | ✓ |

## Surface scan

Per DEC-V61-088 pre-implementation discipline:

- **Step 1 (ROADMAP scan)**: M-STACK-TRACK-3 retro §9 item 3 explicitly
  names `bc_type_name_validity_advisor` as a "D-class candidate" with
  ~120 LOC + 6-8 tests + sub-DEC scope estimate. ARC-GOAL.md Done dim
  #4 is already MET (1/1 ✓ via D6); this sub-DEC raises D-class count
  to 2 and `LANDED advisor 总数` 9 → 10.
- **Step 2 (existing-implementation grep)**:
  `grep -rin "bc_type_name_validity\|D10\|bc_name_validity" ui/backend
  .planning` returned only:
  - `.planning/case_proposal_queue.md` (D10 references the **defect**
    catalog D10 = non-watertight-shell from case_020 injection — a
    different D10 than this advisor's name; collision is project-
    internal naming friction inherited from V62 charter draft listing
    `D6/D9/D10` as advisor-candidate IDs)
  - `.planning/ARC-GOAL.md` Done dim #4 mention
  - `.planning/2026-05-14_v62_charter*.md` charter listing D6/D9/D10
    as promotable D-class candidates
- **No prior implementation found** — clean greenfield. Surface-scan
  trailer: **clean**.

## v2.3 compliance

- **Surface scan**: clean (per §Surface scan above) — trailer optional
  per v2.3 round-1 loosen (Surface-scan-found absence is fine when
  scan returns no prior impl)
- **DEC scope**: this sub-DEC crosses `services/` (1 new file +
  `advisor_stack.py` register) + `routes/` (`ai_review.py` 2 new wire
  fields) + `tests/` (3 test files). 3-shared-paths threshold reached
  → full sub-DEC body authored (this file). NOT elevated to charter
  because parent charter `DEC-V62-A-charter` already covers V62-A
  scope; this is supplemental Tier 2 milestone work.
- **Codex review**: SKIPPED — per v2.2 1-sync-trigger / v2.3 carry-over:
  no auth / signing / security-boundary change. Route field expansion
  is identical pattern to REQ-SCHEMA-EXPAND (B31, also Codex-skipped
  precedent). `confidence: med` overall (catalog completeness is
  single-case-evidence; Opus self-judgment on diff correctness is high).
- **Kogami**: NOT invoked — opt-in only per v2.3; no charter scope
  change.
- **Counter**: +1 to `autonomous_governance_counter_v61` (autonomous
  governance · land without external gate).
- **Notion sync**: pending — flag `notion_sync_status: pending`; will
  flip to `synced <date> (<url>)` at session-end batch sync only if
  this DEC remains `Status: Accepted` (per v2.3 round-1 rule).

## Promotion gate (single-case-land → [VALIDATED])

D10 lands as `single-case-land` per A2 v1 / D6 precedent:

- **Current evidence**: V29 (case_006 ONERA M6 transonic, 6
  foam-extend-only BC declarations) — single case.
- **[QUESTIONABLE] marker**: V29 carries this status until a 2nd
  industrial case sediments using foam-extend BC names OR a typo BC
  name that D10's `unknown`-class severity catches in a live Track C
  session. Candidate forward-loaded cases (per case_proposal_queue.md):
  case_018 (cyclone)·case_019·case_020. Any of these declaring a
  foam-extend-family BC name OR producing a runtime advisor-firing
  promotes D10 to [VALIDATED].
- **No artificial backfill** — sediment must arise from an actual
  Track C session running the case substrate, not synthesized.

## Confidence: med

- High on the diff correctness (140 tests green; 13 advisor + 4 stack
  + 3 route + 70 adjacent regressions; explicit kwargs precedence
  matches B31 pattern; 4Q gate inline-verified for both advisor source
  + stack dispatch).
- Med on the catalog completeness — only 61 of OpenFOAM's ~200+
  patchField subclasses are listed; future cases will exercise the
  `unknown`-class warning path against legitimate but uncatalogued
  ESI BC names, and the catalog will need append-only widening
  (sub-DEC per addition). Acceptable for single-case-land; the
  alternative (exhaustive ESI registry parse) is out of scope and
  would couple this advisor to a specific OpenFOAM release.

## Closing reference

- M-STACK-TRACK-3 retro §gap2 closes (V29 BC-name-validity gap →
  D10 LANDED).
- Done dim #4 advances from 1/1 ✓ to 2/1 ✓ (over-met).
- ARC-GOAL.md `LANDED advisor 总数` 9 → 10 ✓.
- M-V63 charter material remains the route-schema widening (V30 + D1
  unblocking via stl_bbox_set / D6 wire-up) per TRACK-3 §9 item 1.
