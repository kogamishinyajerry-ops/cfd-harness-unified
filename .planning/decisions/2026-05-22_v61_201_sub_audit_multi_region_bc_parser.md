---
decision_id: DEC-V61-201-SUB-INGEST-MULTI-REGION-BC
title: bc_audit parser detects + iterates 0/region_*/ multi-region CHT layouts
status: Accepted
accepted_date: 2026-05-22
parent_dec: DEC-V61-201-SUB-INGEST
phase: post-merge follow-up (M2.6)
notion_sync_status: synced 2026-05-22 (https://www.notion.so/367c68942bed8131b43af55249184344)
---

## Why

case_011 (plate-fin CHT, `chtMultiRegionFoam`) dogfood surfaced
Gap #11: the M6.1 `bc_audit` parser is hard-coded to read `0/U`,
`0/p`, `0/<turbulence_fields>` at the top of the `0/` directory. But
multi-region conjugate-heat-transfer cases use OpenFOAM's
`0/region_<name>/` layout instead — one fluid region + N solid
regions, each with its own field files under a region sub-directory.

Result on the case_011 production-grade industrial case:
`bc_quality.json` was essentially empty (`fields_missing` = `["U",
"p", ...]` because none of those files exist at `0/U`), and
downstream `boundary_conditions.py` could only emit BLOCKED with
`reason: missing_files` — losing all real BC evidence the case
actually carried under `0/region_fluid/U`, `0/region_solid/T`, etc.

Witnesses queued for this gap:
- case_011 (plate-fin fluid+solid HX) — primary trigger
- case_028 (potential second multi-region CHT case in v2 branch)
- future intake of any chtMultiRegionFoam / chtMultiRegionSimpleFoam
  case (common in industrial cooling, HX, electronics thermal)

## What

**In scope (this sub-DEC)**: bc_audit parser DETECTION + per-region
iteration only. When `0/` contains entries whose names start with
`region_`, treat the case as multi-region and produce
`bc_quality.json` with a top-level `layout: "multi_region"` marker
plus a top-level `regions` key:

```jsonc
{
  "bc_parsing_status": "ok",
  "layout": "multi_region",
  "expected_fields": ["U", "p", ...],   // canonical fluid-region fields
  "regions": {
    "region_fluid": {
      "expected_fields": ["U", "p", ...],
      "fields_present": ["U", "p"],
      "fields_missing": [],
      "fields": { "U": { ... per-patch dict ... }, "p": { ... } }
    },
    "region_solid": {
      "expected_fields": ["T"],
      "fields_present": ["T"],
      "fields_missing": [],
      "fields": { "T": { ... } }
    }
  }
}
```

Single-region cases (the existing 99% path) remain BYTE-IDENTICAL —
no `layout` key, no `regions` key, the existing top-level `fields`
+ `fields_present` + `fields_missing` + `expected_fields` shape is
preserved exactly.

Downstream `boundary_conditions.py` detects the multi-region marker
and emits a graceful BLOCKED with
`reason: multi_region_bc_validation_not_yet_wired`, surfacing the
per-region evidence in the report (so the user sees what regions +
fields ARE parsed) without falsely claiming PASS on a contract
schema that wasn't designed for multi-stream cases.

## What this DEC DOES NOT do (out of scope)

- **Schema redesign for multi-region `bc_contract`**: the existing
  `bc_contract.{inlet, outlet, wall}` literal-keys schema does NOT
  fit multi-stream CHT cases. A solid region's `T` field has its
  own boundary patches (`fluid_to_solid_interface`,
  `solid_outer_wall`, etc.) that don't map to `inlet`/`outlet`/`wall`
  trichotomy. Reworking the schema (per-region `bc_contract.regions.
  <name>.{interfaces, walls, ...}` or similar) is **CHARTER-SCOPED
  work — explicitly Gap #28 territory** and out of scope here.
- **Per-region patch coverage / type match / value match**: these
  evaluations require the manifest schema work above. This sub-DEC
  emits structural BLOCKED downstream rather than evaluating
  half-defined dimensions and lying about coverage.
- **`audit/qoi.py` multi-region handling**: separate concern (qoi
  already has its own paths and may need its own per-region
  pivot — out of scope here, not investigated).
- **`audit/geometry.py` polyMesh/boundary multi-region**: the
  `polyMesh/<region_name>/boundary` layout is a separate parsing
  task with its own scope — out of scope here.

## How (implementation)

**File: `ui/backend/audit/cfdtrust/backends/openfoam.py`** —
extend `_collect_and_persist_bc()` and `_persist_bc_quality()`:

1. **Detect**: in `_collect_and_persist_bc()`, list `(case_dir /
   "0").iterdir()` (if it exists) and check for any entry that
   `is_dir()` and whose name starts with `region_`.
2. **Single-region branch (unchanged)**: if no `region_*` subdirs
   found, run the existing parse-files-at-top-of-`0/` logic and
   persist with the existing top-level shape. ZERO behavior change.
3. **Multi-region branch**: iterate each `region_<name>/` subdir,
   run the SAME field-collection logic but rooted at
   `case_dir / "0" / region_name / <field>`. Per-region results
   accumulate into a `regions[name]` sub-dict. The top-level
   `layout: "multi_region"` marker plus the top-level `regions`
   key signal to downstream that the schema is the multi-region
   variant.
4. **Schema additive**: when multi-region, `expected_fields` AT THE
   TOP LEVEL is the union of canonical fields (the same default
   list `["U", "p", ...]` from `bc_contract.turbulence_fields`),
   purely as a manifest-side declaration; each region carries its
   OWN `expected_fields` if a region-specific expectation can be
   inferred (currently same default — solid regions may legitimately
   have only `T`, which surfaces as `fields_missing: ["U", "p", ...]`
   under that region; the multi-region downstream BLOCKED handler
   treats `fields_missing` per-region as advisory, not as a hard
   FAIL, since per-region expected-fields semantics are out of scope
   for this DEC).

**File: `ui/backend/audit/cfdtrust/audit/boundary_conditions.py`** —
add a single early-detection branch in `run()`:

5. After reading `bc_quality.json`, if `bc_quality.get("layout") ==
   "multi_region"`, return a `BLOCKED` gate with:
   - `reason: multi_region_bc_validation_not_yet_wired`
   - `details.regions_detected`: sorted list of region names
   - `details.per_region_field_summary`: small dict
     `{region: {fields_present, fields_missing}}`
   - `details.next_step`: pointer to Gap #28 / future schema work

   This is the structural fallback — bc_audit honestly says "I see
   multi-region evidence, I can't evaluate it under the current
   bc_contract schema, here's what I found" rather than crashing or
   silently passing.

**File: `ui/backend/audit/cfdtrust_tests/test_ingest_mode.py`** —
add 3 tests at the end:
- Test A: synthetic case with `0/region_fluid/U` + `0/region_solid/T`
  produces `bc_quality.json` with `layout: "multi_region"` +
  `regions.region_fluid.fields.U.parsed == True` +
  `regions.region_solid.fields.T.parsed == True`.
- Test B: existing single-region path (top-level `0/U`, `0/p`)
  still produces the unchanged shape (no `layout`, no `regions`,
  top-level `fields` present) — regression guard.
- Test C: edge case — `0/region_<name>/` directory present but
  EMPTY (no field files inside) → region listed in `regions` dict
  with all fields marked missing, NO crash, `bc_parsing_status`
  remains `"ok"` so downstream BLOCKED-handler fires on the schema
  marker not on a parse error.

## Acceptance criteria

- [x] DEC file landed at this path with `Accepted` status
- [x] `_collect_and_persist_bc()` detects `0/region_*/` and produces
      multi-region `bc_quality.json` schema
- [x] Single-region cases produce byte-identical `bc_quality.json`
      (regression test B)
- [x] Multi-region cases surface graceful BLOCKED downstream via
      `boundary_conditions.py` instead of crashing or silently passing
- [x] 3 new tests in `test_ingest_mode.py` pass
- [x] Full `pytest -q ui/backend/audit/cfdtrust_tests/` still green

## Risks

- **Medium**: schema-additive change. Existing single-region tests
  must still pass exactly. Mitigation: keep the existing top-level
  shape literally unchanged when no `region_*` subdirs are present;
  the multi-region branch is purely additive.
- **Low**: downstream gate consumers other than `boundary_conditions.py`
  reading `bc_quality.json` (none found via grep; trust_report.py
  uses the bc_audit gate output, not bc_quality.json directly).
- **Low**: per-region expected_fields list may surface noise
  (`fields_missing: ["U", "p"]` on a solid region) — accepted as
  advisory in this sub-DEC; charter work (Gap #28) will introduce
  per-region-class expected-fields when the schema is reworked.

## Scope class

**Sub-DEC** — bounded to `backends/openfoam.py` BC parsing +
`audit/boundary_conditions.py` detection branch + tests. ~80-120
LOC across 3 files. NOT charter — does NOT touch the bc_contract
schema or cross more than 2 modules in the audit subsystem.
