---
decision_id: V61-212
title: shm_dict extractor (case dir → Mapping[str, Any]) — sub-DEC
status: Accepted
parent_dec: V61-211
phase: P2 (Blueprint v4)
notion_sync_status: synced 2026-05-29 (https://www.notion.so/36fc68942bed8169813be0e5c9076bf7)
---

# DEC-V61-212 · snappyHexMeshDict extractor for case-behavioral eval

## Context

DEC-V61-211 landed the first `case_extractors` member (`solver_block_extractor`),
proving the pattern: a stdlib-only, line-anchored, pure-function extractor that
turns a case dir into a typed input for an existing advisor, with explicit
scope-locking and truth-chain refusal on ambiguous source. That DEC explicitly
deferred `shm_dict` to a separate sub-DEC (DEC-V61-211 §"Out (separate sub-DECs)").

The consumer advisor `validate_shm_dict` lives at
`ui/backend/services/geometry_ingest/shm_dict_validator.py:317` and accepts a
free-form `dict[str, Any]` matching the parsed snappyHexMeshDict tree (no
custom dataclass — it walks the dict directly). `assemble_stack` dispatches it
whenever `shm_dict is not None` (`ui/backend/services/advisor_stack.py:769-781`),
calling `validate_shm_dict(dict(shm_dict))`. Wire payload precedent in
`routes/ai_review.py:114,138,741` reads `<case_dir>/inputs/shm_dict.{yaml,yml,json}`,
but **no production code constructs `shm_dict` from a case's actual
`system/snappyHexMeshDict`** — only hand-built test fixtures
(`tests/test_advisor_stack.py:59-74`). This is the gap the extractor closes.

Survey (this session, 2026-05-28) — `find .planning/case_profiles/*_dicts -name snappyHexMeshDict`:
11 files across 10 profiles ship a snappyHexMeshDict (case_004_mesh_conv_study
ships two: `h2/` + `h4/` subdirs). Sampled diversity (case_006 / case_028 /
case_029):
- case_006: 5 geometry entries via `file "<name>.stl"` form, `features ()`
  empty, layers on 2 surfaces, `meshQualityControls #include "meshQualityDict"`.
- case_028: 29 geometry entries via `<name>.stl { name <name>; }` alias form
  (V99-WIDEN idiom), `features ()` empty, `refinementRegions {}` empty — would
  trigger `orphaned_emesh_feature` IF `.eMesh` files were inventoried.
- case_029: NACA stall — single STL geometry with `.stl`-key+`name:` alias,
  PLUS a `box` geometry primitive, `features` non-empty with one entry, AND
  `refinementRegions.refineBox` with `mode inside`.

That is real case-discrimination: 0 / 0 / non-empty `features`; 5 / 29 / 2
geometry entries; alias-form / file-form / mixed; with/without refinementRegions.

## Decision

Add a second `case_extractors` member:
`shm_dict_extractor.extract(case_dir) → Mapping[str, Any] | None`. Mirror
DEC-V61-211's architecture exactly — stdlib-only, pure function, read-only,
no route, no mutation; v0.1 deliberately narrow scope; honest `None` over
fabrication.

### Scope (v0.1 · this DEC)

The extractor parses `<case_dir>/system/snappyHexMeshDict` (or the canonical
single-case path when case_004_mesh_conv_study-style sub-mesh dirs apply —
see "Out" below) and returns a `Mapping[str, Any]` populated with the
**minimum subset that makes `validate_shm_dict` produce case-specific
findings**. Concretely, four top-level keys with this shape (each
INDEPENDENTLY optional — missing block ⇒ key absent, not key=None):

```python
{
    "geometry": {
        "<entry_key>": {"type": "<type_token>", "name": "<alias_or_key>"},
        ...
    },
    "castellatedMeshControls": {
        "features": [{"file": "<name>.eMesh"}, ...] | [],
        "refinementSurfaces": {
            "<surf>": {"patchInfo": {"type": "<wall|patch|symmetryPlane|...>"}},
            ...
        },
        "refinementRegions": {"<reg>": {}, ...},
    },
}
```

The values inside (e.g. `level`, `mode`, `levels`, `nSurfaceLayers`,
`maxLocalCells`, etc.) are **NOT extracted** — they're not read by
`validate_shm_dict`'s detection paths (a)/(b)/(b')/(c)/(d). Including them
would be gold-plating that widens the extractor's surface for zero finding-gain.

**Why these four keys, this depth, no more**:

| Advisor detection path | Source dict key the path reads | Extractor field |
|---|---|---|
| (a) orphaned_emesh_feature | `castellatedMeshControls.features` (length == 0) | `cmc.features` (as list) |
| (b) missing_geometry_ref | `cmc.refinementSurfaces.keys()` ⊆ `geometry` effective names | `cmc.refinementSurfaces`, `geometry` (with `name:` alias) |
| (b') geometry_orphan | inverse of (b) | same |
| (c) missing_region_ref | `cmc.refinementRegions.keys()` ⊆ `geometry` effective names | `cmc.refinementRegions`, `geometry` |
| (d) typo_suspicion | walks ALL keys under top-level blocks | the four blocks above (enough for V52: `addLayersControls.minMedianAxisAngle` typo) |
| (e) multi_normal_constrained_patch | `cmc.refinementSurfaces.<surf>.patchInfo.type` | `refinementSurfaces.<surf>.patchInfo.type` |

Path (d)'s V52 sediment lives in `addLayersControls.minMedianAxisAngle` — so
v0.1 ALSO extracts `addLayersControls` as a flat key-set (keys only, values
discarded — typo detection only needs the keys to fuzzy-match). Five
top-level keys total: `geometry`, `castellatedMeshControls`, `addLayersControls`,
plus the implicit "everything not extracted is silently absent."

### v0.1 explicit NON-features (deferred / out of scope)

The extractor will NOT parse — and the docstring will record each line-item
so a future caller cannot quietly assume more:

1. **Numeric/quantitative values** (level, levels, nSurfaceLayers,
   maxLocalCells, resolveFeatureAngle, tolerance, expansionRatio, etc.) —
   none are read by `validate_shm_dict`; including them adds surface for zero
   finding-gain. Deferred to a future advisor (sizing-field / refinement-ratio
   audit) under its own sub-DEC.
2. **`snapControls` / `meshQualityControls`** — typo fuzzy-match COULD fire
   on keys here (CANONICAL_KEYS table at `shm_dict_validator.py:68`), but no
   in-repo case has a known typo here today. v0.1 ships geometry +
   castellatedMeshControls + addLayersControls only; a follow-on sub-DEC
   expands the typo-detection key surface if real evidence emerges.
3. **`#include` directives** (e.g. case_006's
   `meshQualityControls { #include "meshQualityDict" }`) — followed includes
   are a multi-hour parsing task. v0.1 ignores them; the `#include` line
   produces no extracted key (silent omission). A `meshQualityControls` typo
   inside an included file is invisible to v0.1 — recorded as known
   limitation.
4. **OpenFOAM regex-pattern keys** (e.g. `"(U|k|omega)" { ... }`) — v0.1
   captures them as literal string keys (not expanded). `validate_shm_dict`'s
   typo fuzzy-match would not false-fire on them (edit-distance > 2 vs every
   CANONICAL key). Honest preservation, no expansion.
5. **STL face-normals extraction for path (e)** — `validate_shm_dict`'s V99
   widening reads `stl_face_normals` as a SEPARATE kwarg (caller supplies via
   trimesh). That's a different extractor entirely (NOT part of `shm_dict` —
   would be `shm_stl_normals_extractor`, separate sub-DEC). v0.1's extracted
   shm_dict alone is sufficient for paths (a)/(b)/(b')/(c)/(d).
6. **Sub-mesh-dir convention** — case_004_mesh_conv_study ships
   `h2/snappyHexMeshDict` + `h4/snappyHexMeshDict` instead of
   `system/snappyHexMeshDict`. v0.1 looks for `system/snappyHexMeshDict` only
   and returns `None` for case_004_mesh_conv_study (honest omission). A
   follow-on sub-DEC can add multi-mesh-dir handling if cross-case eval needs
   it; today, returning None is fine because case_004_mesh_conv_study still
   has a `system/controlDict` and the eval can run with `shm_dict=None`.
7. **Macros / variable substitution** (`$macroName`) — captured as literal
   string values. `validate_shm_dict` walks keys not values for most paths;
   the only value-sensitive path is (e) (patchInfo.type), where a `$macro`
   value would not match `_CONSTRAINED_PATCH_TYPES` (correct: no
   false-positive). Honest preservation.
8. **Quotes around tokens** (`type "wall";` vs `type wall;`) — both stripped
   to the bare token. The advisor only checks token equality, not quoting.
9. **`patchInfo.type` for `_CONSTRAINED_PATCH_TYPES` cases under uncertain
   parse** — see Truth-chain §below for the dispatch-fabrication risk and
   refusal policy.

### Why shm_dict next (not thermo/step/thin_wall)

- **Universal-ish**: 10 in-repo case profiles ship a snappyHexMeshDict
  (vs 26 controlDict). Strictly less universal than solver_block but
  substantially broader than thermo (4 CHT cases) / step (CAD-having cases)
  / thin_wall (geometry-derived, not file-derived).
- **Real differentiation at v0.1 scope**: the five-key extracted shape is
  sufficient to trigger every existing detection path (a)/(b)/(b')/(c)/(d)
  EXCEPT (a) which additionally needs `available_emeshes` (separate concern).
  case_028's empty `features ()` + 29-entry `geometry` block vs case_029's
  one-entry `features` + 1-entry geometry IS the case-class discriminator —
  visible from the extracted dict alone.
- **Highest-density advisor** for case-behavioral spike extension:
  shm_dict_validator emits 4 distinct V-series finding codes (V52, V86, V99,
  V100) — more than any other extractor target. Each is a real sediment
  hit, each can fire from real case data, none requires hand-built fixture.

### Scope-locking rationale (anti-feature-creep)

A general OpenFOAM-dict parser is multi-hour engineering (nested lists,
mixed scalar/list values, includes, macros, regex keys, computed expressions).
v0.1 is intentionally narrower than DEC-211's solver_block extractor in one
axis: it does NOT promise to recover every value, only the **key topology**
and **patchInfo.type strings** that the advisor consumes. The extractor's
docstring records the 9 line-items above so a future caller cannot assume
more. Future sub-DECs can widen detection (sizing-field audit needing
`level` values, refinement-ratio audit needing `maxLocalCells`, etc.) as
discrete arcs.

### Codex review

This is correctness-critical shared code (output is fed to advisor logic
that produces findings consumed by the cross-case eval — a buggy extractor
would either fail the eval or entrench wrong expectations). Codex review
required (cap=3) before commit lands in `origin/main`. Local commit
allowed under L2. Report archived to `reports/codex_tool_reports/dec212_*`.

## Architectural placement

- Same sub-package as DEC-V61-211:
  `ui/backend/services/case_extractors/shm_dict_extractor.py`. Export added
  to `case_extractors/__init__.py` next to `extract_solver_block_snapshot`.
- **Import-linter (ADR-001)**: `ui/backend/*` is out of contract scope per
  ADR-001 §3.2 (root_package=`src`). No contract impact (mirrors DEC-211).
- Imports: stdlib only (`pathlib`, `re`). **Crucially: NO import from
  `geometry_ingest.shm_dict_validator`** — that module is dict-consuming and
  has no dataclass to mirror; the return type IS `Mapping[str, Any]`, so
  the DEC-211 local-mirror pattern does not apply here. Zero third-party deps.
  (This is a meaningful surface reduction vs DEC-211 — no mirror drift risk.)

## Four-question gate

| Question | Answer |
|---|---|
| LLM-offline runnable? | ✅ pure function, stdlib only |
| Clear artifacts? | the extracted `Mapping[str, Any]`; pytest fixtures derived from real case profiles |
| TrustGate/audit explains trust? | the extractor is THE input to behavioral adjudication via `shm_dict_validator`; the eval IS the trust mechanism; non-extracted keys are documented |
| AI advisory-only, no mutating route? | ✅ read-only, no writes, no route, no mutation |

## Acceptance (sub-DEC passes when)

1. `ui/backend/services/case_extractors/shm_dict_extractor.py` exists,
   imports cleanly with stdlib-only, exports
   `extract(case_dir: Path) → Mapping[str, Any] | None`.
2. `ui/backend/services/case_extractors/__init__.py` re-exports as
   `extract_shm_dict` (mirroring DEC-211's `extract_solver_block_snapshot`).
3. `tests/test_shm_dict_extractor.py` parametrizes over all 10 in-repo
   profiles that ship `system/snappyHexMeshDict`, asserts each yields a
   non-None Mapping whose `geometry` keys match a baseline list (grep-verified).
4. Per-shape canary tests:
   - `test_features_empty_vs_populated` — case_028 yields
     `cmc["features"] == []`; case_029 yields `len(cmc["features"]) == 1`.
   - `test_geometry_alias_form_preserved` — case_028's
     `Outer_Surf.stl` literal key with `name: Outer_Surf` alias is captured
     as `geometry["Outer_Surf.stl"] = {"type": "triSurfaceMesh",
     "name": "Outer_Surf"}` so `validate_shm_dict._resolve_geometry_aliases`
     can resolve it.
   - `test_patchinfo_type_extracted_for_constrained_check` — case with a
     `symmetryPlane` patchInfo.type yields the type string verbatim (if no
     such case exists in-repo, synthesize via `tmp_path` fixture; record
     "no in-repo evidence" in test docstring).
5. `tests/test_shm_dict_extractor.py::test_e2e_with_validate_shm_dict` —
   pipe one real extracted shm_dict (e.g. case_028) directly into
   `validate_shm_dict` (skip-if-trimesh-missing-or-import-chain-fails)
   and assert the returned `ShmDictReport` has the expected baseline
   findings (e.g. `geometry_orphan` warnings for orphan parts, OR
   `is_clean` if no V52/V86/V99/V100 hits). This is the live
   case-discrimination proof — mirroring DEC-211's
   `test_advisor_stack_real_case_behavioral_spike` extension.
6. Codex relay APPROVE or APPROVE_WITH_COMMENTS-with-inline-fixes on the
   extractor module (cap=3); local commit allowed before review per L2.
7. No regression in the broader test sweep (full advisor_stack + canonical
   + the new tests pass).

## Truth-chain risk (mirror of DEC-211 R0 P2#2 pattern)

The DEC-211 P2#2 pattern: an extractor field whose `None`-default value
silently flips the downstream advisor's dispatch into a false-positive.
The shm_dict equivalents:

**(R1) `castellatedMeshControls.features` empty-vs-absent ambiguity**:
- If the source SHM has NO `features` key at all, advisor path (a) reads
  `cmc.get("features", None)`, gets `None`, skips the V86 check. Correct.
- If the source SHM has `features ()` empty (case_028 case), advisor reads
  an empty list, AND fires V86 ONLY when `available_emeshes` is non-empty.
- **Risk**: if the extractor encounters a parse failure on the `features`
  block and silently maps it to `[]` (instead of omitting the key), and
  the caller separately supplies `available_emeshes` from disk, the
  advisor will emit a V86 `orphaned_emesh_feature` that was actually a
  parse artifact, not a real orphan. **Mitigation**: parse failure on
  `features` ⇒ omit the `features` key entirely (do NOT default to `[]`).
  Empty list is only emitted when the source literally said `features ()`.

**(R2) `refinementSurfaces.<surf>.patchInfo.type` partial-parse**:
- If the extractor captures `refinementSurfaces.<surf>` but fails to extract
  the nested `patchInfo.type`, the advisor's path (e) silently skips that
  surface (correct — `stl_face_normals` is None or no measurement; v0.1
  extractor explicitly DOES NOT supply normals, so path (e) never runs
  for v0.1-extracted dicts).
- **However**: a partial extraction where the surface exists but
  `patchInfo` is missing could mask a real `symmetryPlane`-typed surface
  IF a future caller fed `stl_face_normals` from a separate
  `shm_stl_normals_extractor` (deferred to its own sub-DEC).
- **v0.1 policy (refined from DRAFT)**: extract `patchInfo.type` best-
  effort and ALWAYS emit the surface in `refinementSurfaces`, even when
  patchInfo is unparseable or absent. Rationale: the DRAFT's "drop
  surface entirely on patchInfo failure" recommendation costs path (b)/
  (b')/(c) reach (missing_geometry_ref / missing_region_ref /
  geometry_orphan detection) for ZERO path (e) benefit under v0.1
  (extractor doesn't supply normals). When path (e) eventually
  materializes via the separate normals-extractor sub-DEC, that
  sub-DEC's contract can refuse-on-ambiguity at the normals level
  without polluting refinementSurfaces here. Three sub-cases:
  - patchInfo block ABSENT in source ⇒ emit `{<surf>: {}}` (no
    patchInfo key). Path (e) silently skips. Paths (b)/(c) work.
  - patchInfo block PRESENT, type parsed (e.g. `wall`, `symmetryPlane`)
    ⇒ emit `{<surf>: {"patchInfo": {"type": "<token>"}}}`.
  - patchInfo block PRESENT, type unparseable (malformed / `$macro` /
    absent inside block) ⇒ emit `{<surf>: {"patchInfo": {}}}`. Path
    (e) silently skips (no string type in `_CONSTRAINED_PATCH_TYPES`).
    Paths (b)/(c) still work.
- **Tests** assert all three sub-cases (canary + tmp_path) and document
  the deviation from the DRAFT recommendation.

**(R3) `geometry` `name:` alias parsing**:
- case_028's idiom is `Outer_Surf.stl { type triSurfaceMesh; name Outer_Surf; }`.
  If the extractor fails to capture the `name:` alias, advisor path (b)
  will emit `missing_geometry_ref` for every refinementSurfaces entry
  (because `Outer_Surf` ≠ `Outer_Surf.stl` literal key) — a FABRICATED
  finding deluge from case_028 alone (29 surfaces × `missing_geometry_ref`).
- **Mitigation**: tests assert the alias is captured for case_028
  specifically; failure here is highly visible (29 fabricated criticals).

**(R4) NO drift-parity canary needed** (unlike DEC-211):
- DEC-211 needed a `_DENSITY_BASED_AT_RISK_SOLVERS` mirror canary because
  it imported nothing from upstream (mirror dataclass).
- DEC-212 imports nothing from `shm_dict_validator` and returns a generic
  `Mapping[str, Any]`. No advisor dataclass / no advisor constants are
  mirrored. **The advisor's CANONICAL_KEYS / _CONSTRAINED_PATCH_TYPES /
  _COLINEAR_DEVIATION_MAX live exclusively in the advisor and are read at
  call-time** — extractor cannot drift from them because extractor does
  not encode them.

## Estimated LOC

- `shm_dict_extractor.py`: ~150-180 LOC (regex-based, comparable to DEC-211's
  205-LOC `solver_block_extractor.py`, modulo nested-block scanning being
  slightly more involved than three top-level regexes; mitigated by
  flat-keys-only extraction for `addLayersControls`).
- `__init__.py` patch: +2 LOC (re-export).
- `tests/test_shm_dict_extractor.py`: ~200-260 LOC (10-profile parametrized
  sweep + 5-6 shape canaries + 2-3 tmp_path edge cases + 1 e2e advisor
  hookup test).
- **Total ~360-450 LOC including tests** (vs DEC-211's ~205 impl + ~470
  test). Smaller test footprint because no local-mirror drift canaries are
  needed (R4 above).

## Status

Accepted 2026-05-28 by cfd-chief-engineer under user-approved "α′ extension
sub-DEC" route. DRAFT investigator (workflow `wj0v7usep`, agent #1) wrote
the original 335-line scoping document; chief-engineer ratification refined
the R2 mitigation paragraph from "drop surface entirely on patchInfo
failure" to "always emit surface; tier patchInfo per parse outcome" (the
DRAFT recommendation cost path-b/c reach for zero path-e benefit in v0.1
since v0.1 extractor doesn't supply stl_face_normals; the path-e safety
concern materializes only when the separate `shm_stl_normals_extractor`
sub-DEC lands, at which point that sub-DEC owns the refuse-on-ambiguity
contract at the normals level).

## Out of scope (do NOT do under this DEC; record as follow-on)

- Numeric/quantitative value extraction (sizing-field audit · separate sub-DEC).
- `snapControls` / `meshQualityControls` block coverage (typo widening · separate sub-DEC).
- `#include` directive following (multi-file parsing · separate sub-DEC).
- Multi-mesh-dir convention (case_004_mesh_conv_study h2/h4 · separate sub-DEC).
- STL face-normals extraction for V99 widening (`shm_stl_normals_extractor`
  · separate sub-DEC; geometric, not dict-based).
- thermo_dict / step / thin_wall extractors (separate sub-DECs each).
- Wiring the extractor into production routes (route-side discovery
  decision · different DEC).
- Extending behavioral assertions to FULL E-case firing sets (needs all
  extractors landed first).

— investigator (scoping agent), 2026-05-28
