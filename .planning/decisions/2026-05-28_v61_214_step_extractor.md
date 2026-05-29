---
decision_id: V61-214
title: STEP-path extractor (case dir → StepArtifacts) — sub-DEC
status: Accepted
parent_dec: V61-211
phase: P2 (Blueprint v4)
notion_sync_status: synced 2026-05-30 (https://www.notion.so/36fc68942bed8128837bd617b6a28271) · commit ded415b
---

# DEC-V61-214 · STEP-path extractor for case-behavioral eval (Stage-2 2b extension)

## Context

DEC-V61-211 landed `solver_block_extractor` as the first `case_extractors/`
member; DEC-V61-212 added `shm_dict_extractor`; DEC-V61-213 added
`thermo_dict_extractor`. Each established the pattern: stdlib-only,
line-anchored, pure-function reader; local-mirror dataclass when upstream
import drags trimesh; scope-locked NON-features in the docstring; honest
`None` on absent or malformed source; Codex R0/R1 review cycle.

`assemble_stack` (`ui/backend/services/advisor_stack.py:898-915`) dispatches
`unit_detector.detect_unit` whenever `step_path is not None`, passing
`step_path` plus optional `bbox_max_extent_raw` + `body_extents_raw`
kwargs. The wire-form HTTP route already auto-discovers these in
`ui/backend/routes/ai_review.py:342-356` (`_autodiscover_step`) and
`:359-406` (`_autodiscover_geometry_metadata`) — but the **case-behavioral
eval has no equivalent path**, mirroring the gap that DEC-V61-211
through -213 closed for `SolverBlockSnapshot` / `shm_dict` / `thermo_dict`.

### Correction to brief assumption (truth-chain)

The original scoping brief stated that `step_path` /
`step_bbox_max_extent_raw` / `step_body_extents_raw` feed
`face_orientation_advisor` and `extra_body_advisor`. They do not. The
single consumer is `unit_detector.detect_unit`
(`advisor_stack.py:898-911`; signature at
`ui/backend/services/geometry_ingest/unit_detector.py:165-169`).
Recording this explicitly so a future reader does not over-credit the
extractor's downstream reach.

Additional brief-vs-DRAFT scope conflicts resolved in favor of the
DRAFT (THIS DEC is the SSOT, not the brief):

- **Brief**: "parse ISO 10303-21 HEADER (FILE_DESCRIPTION / FILE_NAME /
  FILE_SCHEMA / originating_system / schema AP203/AP214/AP242)" — **DENIED**
  for v0.1. The actual consumer
  `unit_detector.parse_step_header_unit`
  (`unit_detector.py:81-139`) already handles the only header-derived
  signal v0.1 needs (LENGTH unit via SI_UNIT / CONVERSION_BASED_UNIT
  regex over the first 1 MB). Duplicating header parsing in the
  extractor is gold-plating + drift risk. Defer to v0.2 sub-DEC iff a
  future advisor needs `originating_system` / `schema` beyond unit
  decision.
- **Brief constraint #5**: "Mojibake DETECTION (not decoding): flag
  presence as a structural advisory" — **DENIED** for v0.1. Mojibake
  byte-sniff requires opening the STEP file (X2-escape patterns like
  `\X2\7197...\X0\` for Chinese PRODUCT names; GBK-mangled raw bytes).
  v0.1 deliberately NEVER opens the STEP file — see §"Scope locking"
  below. Defer to future `step_brep_inspector` sub-DEC triggered by a
  real CAD-bearing case landing in `case_profiles/`. See §"Mojibake
  handling (deferred · explicit NON-feature)" below for full rationale.

## Decision

Add `case_extractors.step_extractor.extract(case_dir: Path) →
StepArtifacts | None` mirroring the v0.1 shape of `_autodiscover_step` +
the bbox/extents subset of `_autodiscover_geometry_metadata`. Return
`None` when **all three** fields are unresolvable (no STEP under
`<case_dir>` or `<case_dir>/cad/`, no `cad/bbox.json` with `bbox` /
`extents`, no `manifest.json` fallback). Absence is a normal case-class
signal (most OF cases are bbox-meshed, not CAD-imported), not an error.

**Per-field per-failure-mode honest omission** — when at least
`step_path` resolves, the returned `StepArtifacts` may carry per-field
`None` on `bbox_max_extent_raw` and `body_extents_raw` independently
(per-field, NOT whole-snapshot — different from solver_block's
whole-snapshot refusal because the downstream advisor `unit_detector`
tolerates partial input per its docstring at
`unit_detector.py:170-173`). When bbox/extents are present but
`step_path` is absent, the extractor still collapses to `None`
(consumer-gated by `step_path is not None`).

Public alias: `extract_step_path_snapshot` re-exported from
`case_extractors/__init__.py`, mirroring the
`extract_solver_block_snapshot` / `extract_shm_dict` /
`extract_thermo_dict_snapshot` pattern.

### Scope (v0.1 · this DEC)

**In** — three fields from disk:

| Extractor field | Source on disk | Source LOC reference (lift target) | Consumer site | Failure mode |
|---|---|---|---|---|
| `step_path: str \| None` | First glob hit under `<case_dir>` then `<case_dir>/cad/` for `*.step` / `*.stp` / `*.STEP` / `*.STP`, sorted per suffix | `ai_review.py:342-356` `_autodiscover_step` (18 LOC lift) | `advisor_stack.py:898-911` `unit_detector.detect_unit(step_path=…)` | `None` when no STEP file under either dir (silent — most cases) |
| `bbox_max_extent_raw: float \| None` | `max(xmax-xmin, ymax-ymin, zmax-zmin)` from `<case_dir>/cad/bbox.json` `bbox` (6-tuple) with `<case_dir>/manifest.json` `bbox` fallback | `ai_review.py:505-531` `_bbox_max_extent` arithmetic (REPLACE HTTPException with `return None`) + `:377-401` bbox/manifest discovery | `advisor_stack.py:901-902` `unit_kwargs["bbox_max_extent_raw"]` → `detect_unit` | Per-field `None`: `bbox.json` absent OR `bbox` key malformed (arity ≠ 6 / non-numeric / non-list). DEC-213 R1 carry-forward — distinguish key-absent (no `bbox.json`) from key-present-malformed (`bbox.json` has malformed `bbox`) with two tests; both yield `None` but for traceably different reasons |
| `body_extents_raw: list[float] \| None` | `<case_dir>/cad/bbox.json` `extents` list with `manifest.json` fallback; coerce each element to float | `ai_review.py:380-383` + `:398-401` manifest fallback | `advisor_stack.py:903-904` `unit_kwargs["body_extents_raw"]` → `detect_unit` | Per-field `None`: `bbox.json` absent OR `extents` key non-list / element non-coercible. Independent of `step_path` and `bbox_max_extent_raw` |

**Scope-determinism rules**:

- Root searched before `<case_dir>/cad/` (mirror HTTP path); within each
  dir, suffix order is `(*.step, *.stp, *.STEP, *.STP)`; within each
  suffix, `sorted()` enforces deterministic first-pick.
- Absolute `str` for JSON-safety (advisor consumes path as string;
  `Path.is_absolute()` pinned by test).
- Manifest fallback applies per-field, only when `cad/bbox.json` does NOT
  resolve that field (so a present `cad/bbox.json` with `bbox` but no
  `extents` correctly falls through to `manifest.json` for `extents`
  only). Mirror `_autodiscover_geometry_metadata:395-404`.

**Out (deferred to v0.2 / future sub-DEC)**:

- Actually opening the STEP file at byte or semantic level — for ANY
  purpose. This includes B-rep parsing, header re-reading, PRODUCT
  entity inspection, mojibake byte-sniff. The contract is **discovery
  + pre-staged-metadata lift only**. Requires OpenCascade / FreeCAD
  for geometry → violates stdlib-only.
- Disambiguating multiple STEP files in the same case by heuristic
  (size / mtime / name match). v0.1 contract = first-sorted-wins,
  byte-stable with `_autodiscover_step`.
- Parsing STEP-header unit (`unit_detector.parse_step_header_unit`
  already does this at the consumer site; the extractor stays out of
  the unit-decision business).
- ISO 10303-21 header field extraction (`FILE_DESCRIPTION`,
  `FILE_NAME`, `FILE_SCHEMA`, `originating_system`, `preprocessor`,
  `authorization`, AP203 / AP214 / AP242 schema discrimination).
  Brief's framing is OVERRIDDEN — not v0.1 scope.
- Mojibake detection / flagging / decoding (brief constraint #5 —
  OVERRIDDEN; see §"Mojibake handling" below).
- Synthesizing bbox / extents from STEP geometry when `bbox.json`
  absent (would require opening the STEP file — out of scope).
- Caching across calls. Pure read-every-time. Mirrors siblings
  211/212/213.
- Writing anything to disk. Pure read-only.

### Architectural placement

`Lift, not re-implement`. The existing `_autodiscover_step` (~18 LOC)
and the bbox/extents portion of `_autodiscover_geometry_metadata`
(~25 LOC) are already battle-tested in the HTTP path. The extractor
copies that logic into `case_extractors/step_extractor.py` and returns
a single `StepArtifacts` dataclass; the HTTP autodiscover stays put so
the route's behavior is byte-stable. A follow-on sub-DEC may DRY the
two later when both have ≥1 release of bake time.

Re-implementation would risk drift between `case_dir` semantics on the
HTTP path vs. the eval path — exactly the failure mode V20
reclassification captured. A lift preserves drift-parity at zero cost;
a parametrized drift-parity canary test pins the equivalence.

- New module: `ui/backend/services/case_extractors/step_extractor.py`
  + `__init__.py` re-export `extract_step_path_snapshot`.
- **Import-linter (ADR-001) scope**: `ui/backend/*` is out of contract
  scope per ADR-001 §3.2 (root_package=`src`). No contract impact
  (mirrors DEC-211/212/213).
- **Local-mirror policy** (mirror DEC-211 R0 P1): `StepArtifacts` is a
  **new** dataclass defined in this extractor, NOT imported from
  `geometry_ingest`. No upstream class to mirror today; `unit_detector`
  consumes plain kwargs (path/float/list), not a structured class. If
  a future advisor consumes `StepArtifacts`, a mirror-parity canary in
  `geometry_ingest` would be added then.
- **trimesh import risk** (DEC-211 R0 P1 root cause): same risk applies
  — `from geometry_ingest.unit_detector import …` would pull
  `geometry_ingest/__init__.py → health_check → trimesh`. Resolution
  identical: this extractor does NOT import `unit_detector`; it emits
  the three plain kwarg shapes (str / float / list[float]) the consumer
  already accepts.
- **Imports**: stdlib only (`pathlib`, `json`, `dataclasses`,
  `typing`). No `re` needed (no source-file parsing — `bbox.json` is
  JSON; STEP file is path-string-only).

### Why this extractor (priority context)

Rank within `case_extractors` backlog:

- `solver_block_extractor` — LANDED (DEC-V61-211).
- `shm_dict_extractor` — LANDED (DEC-V61-212).
- `thermo_dict_extractor` — LANDED (DEC-V61-213).
- **`step_extractor` (this DEC)** — universal-applicability LOW (zero
  in-repo case profiles ship STEP files today; see §"Case-differentiation
  signal" below), but unblocks `unit_detector` dispatch in the eval and
  is the smallest remaining extractor (~50-70 LOC discovery + ~30 LOC
  bbox arithmetic + ~30 LOC dataclass/extract). Worth landing now
  precisely **because** the case_profiles corpus is CAD-poor: the
  absence pattern itself becomes the eval signal, and the extractor
  starts producing non-`None` the day a CAD-bearing case sediments
  without any other code change.
- `thin_wall_inputs_extractor` — bigger surface (geometry-derived from
  STL), defer to follow-on DEC.

### Case-differentiation signal (honest)

**Zero** of 27 `.planning/case_profiles/*_dicts/` profiles ship `.step`
/ `.stp` / `bbox.json` / `cad/` (verified 2026-05-30: `find
.planning/case_profiles -iname "*.step" -o -iname "*.stp" -o -name
"bbox.json" -o -type d -name cad` → empty). The only STEP files in the
repo are gmsh tutorials under `.venv/share/doc/gmsh/{tutorials,examples}/`
(6 files; see §"Sample STEP files" below).

So at v0.1 every existing profile returns `None`, which is the **correct
honest output** — they have no CAD, `unit_detector` should not dispatch,
and the eval sees a deterministic 27/27 absence row. The extractor's
value is unlocked when a future case (e.g., APU bay 0527, case_002a/b
with CAD, the M3.9-3.12 STEP→STL bridge from DEC-V61-209 lineage)
sediments a STEP into its profile dir; the extractor then starts
producing non-`None` and `unit_detector` joins the dispatch set without
any other code change.

This is **honest discrimination = 1 output today** (`None` for all 27),
vs. solver_block's `5 density-based / 22 incompressible` two-class
split and thermo_dict's `4 distinct (transport, energy) tuples across
5 hConst profiles`. We accept it because: (a) the absence row itself
is a case-class signal the eval can assert deterministically, (b) the
cost is low (~150 LOC impl + tests) and the future-proofing is free,
(c) the drift-parity canary against `_autodiscover_step` provides
audit value immediately (lights up the instant either path silently
changes).

### Sample STEP files (verification corpus for tests)

The 6 in-repo STEP files all live under
`.venv/share/doc/gmsh/{tutorials,examples}/` — all clean ASCII, zero
mojibake, four distinct exporters across three schemas:

| Sample path | Exporter | Schema |
|---|---|---|
| `.venv/share/doc/gmsh/tutorials/t20_data.step` | ST-DEVELOPER v8 | `CONFIG_CONTROL_DESIGN` (AP203 dialect) |
| `.venv/share/doc/gmsh/examples/boolean/component8.step` | ST-Developer | `CONFIG_CONTROL_DESIGN` (uses `/* */` block comments inside HEADER) |
| `.venv/share/doc/gmsh/examples/api/as1-tu-203.stp` | THEOREM SOLUTIONS GCO → AP203 E2 PREPROCESSOR 10.0.053 (`originating_system=UG`) | `CONFIGURATION_CONTROL_3D_DESIGN_ED2_MIM_LF` (full ISO-tagged AP203) |
| `.venv/share/doc/gmsh/examples/api/step_boundary_colors.stp` | 3DEXPERIENCE Platform STEP AP214 | `AUTOMOTIVE_DESIGN` AP214 |
| `.venv/share/doc/gmsh/examples/api/step_header_data.stp` | Open CASCADE STEP translator 7.8 / Gmsh wrapper | `AUTOMOTIVE_DESIGN` AP214 (non-canonical field order: `FILE_NAME` before `FILE_DESCRIPTION`) |

These six are NOT used in v0.1 (the extractor only ever reads path
strings, never opens the files). They are referenced here to document
that (a) the in-repo corpus is exporter-diverse so future
header-parsing sub-DECs have real test material, and (b) **zero
mojibake test corpus exists in-repo today** — confirming that building
mojibake detection now would be speculative infrastructure with no
validation surface.

### Mojibake handling (deferred · explicit NON-feature)

**v0.1 NON-feature**. The extractor NEVER opens the STEP file at byte
level — would violate §"Scope locking" line "Opening the STEP file to
inspect contents". Brief constraint #5 ("Mojibake DETECTION (not
decoding): flag presence as a structural advisory") CONFLICTS with the
v0.1 scope-lock; the DRAFT/DEC wins.

Reference recipe (when a future sub-DEC needs it): see
`~/.claude/projects/-Users-Zhuanz/memory/reference_step_chinese_mojibake.md`
("STEP 中文 PRODUCT 名 mojibake 解码" · 2026-05-11) — three-step
decode (X2-escape unescape → strip trailing `?` → GBK encode + UTF-8
decode, with odd-byte-count last-char-truncation manual fix-up). This
is the X2 escape encoding bug emitted by some ST-Developer exporter
versions when Chinese PRODUCT entity names get serialized through a
GBK-aware DOS pipeline.

**Sub-DEC trigger condition**: when an APU 0507/0527-class case
sediments a real STEP with Chinese PRODUCT names into
`.planning/case_profiles/`, a new sub-DEC will scope a
`step_brep_inspector` extractor that DOES open the STEP file and
either (i) flag mojibake presence as a structural advisory finding
(per brief constraint #5), or (ii) decode + re-emit clean PRODUCT
names. THAT extractor will live alongside `step_extractor`, NOT
replace it.

**Flag-only-no-decode policy if/when it lands**: a future
`StepArtifacts.mojibake_present: bool | None = None` field (currently
NOT in v0.1 dataclass) would carry `True` / `False` / `None`; the
structural advisory routes through the existing `advisor_calls` /
`findings` channel in `assemble_stack` — NOT into `step_path` itself
(path stays clean for `unit_detector` consumption).

### v0.1 explicit NON-features (deferred / out of scope)

The extractor will NOT do — and the docstring records each line-item
so a future caller cannot quietly assume more:

1. **ISO 10303-21 header parse** (FILE_DESCRIPTION / FILE_NAME /
   FILE_SCHEMA / originating_system / preprocessor / authorization;
   schema AP203 / AP214 / AP242 discrimination). Brief framing
   OVERRIDDEN. Header parsing is already done at the consumer site
   (`unit_detector.parse_step_header_unit`) for the only signal v0.1
   needs. Defer to v0.2 sub-DEC iff a future advisor needs richer
   header content.
2. **Mojibake detection / flagging / decoding** (brief constraint #5
   OVERRIDDEN — see §"Mojibake handling" above for full rationale).
   Defer to `step_brep_inspector` sub-DEC.
3. **B-rep / geometry parsing / OpenCascade / FreeCAD invocation**.
   v0.1 surfaces ONLY what is pre-staged on disk. `bbox.json` absent
   ⇒ `bbox_max_extent_raw=None`, NOT synthesized by walking the STEP
   file. Same architectural promise as siblings 211/212/213
   (stdlib-only).
4. **Multi-STEP disambiguation by heuristic** (size / mtime / name
   match). v0.1 contract = first-sorted-wins, byte-stable with HTTP
   path. Sub-DEC if a real case ships ≥2 STEPs and the eval needs a
   smarter pick rule.
5. **Recursion into vendored paths** (`.venv/`, `node_modules/`,
   ancestor directories). Only `(case_dir, case_dir/cad)` are
   checked — no `os.walk`, no `.glob('**/*.step')`, no ancestor
   traversal. A bug that recursed would silently leak the 6 gmsh
   tutorial STEPs into eval discovery; pinned by
   `test_no_recursion_into_vendored_dirs`.
6. **Caching across calls**. Pure read-every-time. Mirrors siblings.
7. **Writing anything to disk**. Pure read-only.
8. **Wire-form `step_bbox` validation parity with `_bbox_max_extent`**.
   The HTTP route raises 400; the extractor silently returns `None`
   per-field. By design (different transport: HTTP wants actionable
   error; eval wants honest absence row).
9. **A `cad_artifacts_extractor` aggregating STEP + STL +
   face_normals + stl_bbox_set into one snapshot**. v0.2 convenience;
   v0.1 keeps one extractor per kwarg-cluster.
10. **DRYing / lifting `ai_review.py:_autodiscover_step` +
    `:_autodiscover_geometry_metadata`** after both have ≥1 release
    bake. Separate refactor DEC.

### Codex review

This is **correctness-critical shared code** (the extractor's output
feeds advisor dispatch). Codex review required per RETRO-V61-001
risk-tier (cap=3) before commit lands in `origin/main`. Local commit
allowed under L2. Report archived to `reports/codex_tool_reports/dec214_*`.

Expected review surface:

- Sort determinism across case-insensitive filesystems (HFS+ / APFS
  default insensitive on macOS; `sorted()` over a glob that includes
  both `*.step` and `*.STEP` could double-yield. Pre-empt with
  `test_sort_determinism_case_insensitive_filesystem`).
- `manifest.json` precedence: must NOT override an existing
  `cad/bbox.json` field (R1 risk if precedence inverted). Pinned by
  `test_manifest_does_not_override_cad_bbox`.
- bbox arity / type coercion: mirror `_bbox_max_extent` which raises
  HTTPException; extractor must silently return `None`. Different
  transport ⇒ different error model. Distinguish key-absent vs
  key-present-malformed (DEC-213 R1 carry-forward).
- No recursion into vendored dirs. Pinned by
  `test_no_recursion_into_vendored_dirs`.

### Truth-chain risks specific to this extractor

1. **STEP present but unparseable**: this extractor never opens the
   STEP file, so it cannot encounter parse failure. `unit_detector`
   handles header-parse failure (`parse_step_header_unit` returns
   `(None, evidence)`). v0.1's contract: "the file exists and is
   readable as a path string." Truth chain stays clean.
2. **`bbox.json` present but malformed**: return `None` for the
   malformed field, keep the `step_path` if STEP itself was found.
   Per-field honest omission, not all-or-nothing refusal — different
   from solver_block's whole-snapshot refusal because the fields here
   are independent and `unit_detector` tolerates partial input.
   **DEC-213 R1 carry-forward**: distinguish key-absent (no `bbox.json`
   at all) from key-present-malformed (`bbox.json` has malformed
   `bbox`) with two separate tests; both yield `None` but for traceably
   different reasons. Silent drift between the two arms (e.g., future
   refactor making one raise while the other silently returns) is
   caught by having distinct test names + sources.
3. **STEP file collision with auto-generated tutorial paths**: must
   not glob into `.venv/` or other vendored dirs. v0.1 only looks at
   `<case_dir>` and `<case_dir>/cad/` — no recursion, no ancestor
   traversal. Pinned by `test_no_recursion_into_vendored_dirs`.
4. **Step-path-absent-but-bbox-present collapse to None**: design-phase
   pinned decision. When `step_path is None` AND both `bbox`/`extents`
   are also `None`, return `None` (clean contract). When `step_path is
   None` but bbox/extents have populated values (e.g.,
   `cad/bbox.json` present but no STEP file), STILL return `None` —
   because the single downstream consumer gates dispatch on
   `step_path is not None`; populated bbox/extents without `step_path`
   are useless. Pinned by `test_no_step_but_bbox_collapses_to_None`.

## Scope locking (anti-feature-creep)

This DEC is **file-discovery + on-disk-metadata lift only**. Any of the
following requires a new sub-DEC, not a v0.1 expansion:

- Opening the STEP file to inspect contents (B-rep parsing, header
  re-read for unit beyond what `parse_step_header_unit` already does,
  PRODUCT entity inspection, mojibake byte-sniff).
- Picking among multiple STEPs by heuristic (size, mtime, name match).
- Synthesizing a bbox when `bbox.json` absent by walking the STEP.
- Caching across calls.
- Writing anything to disk.

## Architectural placement

(Consolidated into §"Decision · Architectural placement" above to
avoid duplication.)

## Four-question gate

| Question | Answer |
|---|---|
| LLM-offline runnable? | yes — pure function, stdlib only, no LLM in import chain |
| Clear artifacts? | the returned `StepArtifacts` dataclass + pytest |
| TrustGate/audit explains trust? | extractor's docstring enumerates non-features; truth-chain: returns `None` on missing/malformed per-field (never fabricates); collapses whole-snapshot `None` when `step_path` absent (consumer-gated); `_autodiscover_step` drift-parity canary lights up on silent change |
| AI advisory-only, no mutating route? | yes — read-only `Path.glob` + `Path.read_text` (on `bbox.json` / `manifest.json` only — never on the STEP file itself), no writes, no route registration |

## Truth-chain table (every field → source line)

| Extracted field | Verifiable source line(s) | Lift target | Detection path in advisor | Failure mode |
|---|---|---|---|---|
| `step_path: str \| None` | First-existing absolute path under `(case_dir, case_dir/cad)` matching glob `*.step` ∨ `*.stp` ∨ `*.STEP` ∨ `*.STP`, sorted per suffix | `ai_review.py:342-356` `_autodiscover_step` | `advisor_stack.py:898-911` → `unit_detector.detect_unit(step_path=…)` | `None` when no STEP under either dir (silent — most cases today: 27/27 in-repo profiles) |
| `bbox_max_extent_raw: float \| None` | `max(xmax-xmin, ymax-ymin, zmax-zmin)` from `<case_dir>/cad/bbox.json` `bbox` 6-tuple with `manifest.json` `bbox` fallback | `ai_review.py:505-531` `_bbox_max_extent` arithmetic (replace HTTPException with `return None`) + `:377-401` discovery | `advisor_stack.py:901-902` `unit_kwargs["bbox_max_extent_raw"]` → `detect_unit` | Per-field `None`: bbox.json absent OR `bbox` key absent OR `bbox` malformed (arity ≠ 6 / non-numeric / non-list); DEC-213 R1 carry-forward distinguishes key-absent vs key-present-malformed by separate tests |
| `body_extents_raw: list[float] \| None` | `<case_dir>/cad/bbox.json` `extents` list of floats with `manifest.json` `extents` fallback; element-coerce to float | `ai_review.py:380-383` + `:398-401` manifest fallback | `advisor_stack.py:903-904` `unit_kwargs["body_extents_raw"]` → `detect_unit` (F-NEW-12 body-class filter at `unit_detector.py:191-200`) | Per-field `None`: bbox.json absent OR `extents` key non-list / element non-coercible; independent of `step_path` + `bbox_max_extent_raw` |
| `[NOT EXTRACTED] FILE_DESCRIPTION / FILE_NAME / FILE_SCHEMA` | (workflow brief framing — OVERRIDDEN; see §"Correction to brief assumption") | — would require opening STEP, out of scope | `unit_detector.parse_step_header_unit` (`unit_detector.py:81-139`) already does the only header-derived signal v0.1 needs (LENGTH unit) | brief constraint conflict resolved in favor of DRAFT/DEC scope-lock; defer to v0.2 sub-DEC |
| `[NOT EXTRACTED] mojibake_present` | (brief constraint #5 — OVERRIDDEN; see §"Mojibake handling") | — would require opening STEP at byte level | (no current consumer) | defer to future `step_brep_inspector` sub-DEC |
| Drift-parity canary | parametrize over all 27 in-repo `*_dicts/` profiles | `_autodiscover_step(profile_dir)` (imported from `ai_review.py` under `pytest.importorskip('trimesh')` — FastAPI route transitively pulls trimesh) | (test-only) | both arms return `None` today; canary lights up the instant either implementation silently drifts (V20 reclassification analog) |

## Acceptance (sub-DEC passes when)

1. `ui/backend/services/case_extractors/step_extractor.py` exists,
   imports cleanly without trimesh in chain, exports
   `extract(case_dir: Path) → StepArtifacts | None` and `StepArtifacts`
   dataclass with exactly 3 fields: `body_extents_raw`,
   `bbox_max_extent_raw`, `step_path`.
2. `ui/backend/services/case_extractors/__init__.py` re-exports as
   `extract_step_path_snapshot` (mirror sibling pattern).
3. `tests/test_step_extractor.py` covers:
   - **(A) Drift-parity canary against `_autodiscover_step`** —
     parametrize over all 27 `*_dicts/` profile dirs; assert
     `extract(profile).step_path == _autodiscover_step(profile)` AND
     both `None` today. Skip-if-trimesh-missing (FastAPI route pulls
     trimesh transitively).
   - **(A) Drift-parity canary against
     `_autodiscover_geometry_metadata`** — same 27 profiles; assert
     extractor's `bbox_max_extent_raw` / `body_extents_raw` match the
     `bbox`/`extents` subset of `_autodiscover_geometry_metadata(profile)`
     — all `None` today (no profile ships `cad/bbox.json` or
     `manifest.json` with bbox keys per 2026-05-30 verification).
   - **(B) Tmp_path canary suite**:
     - `test_step_root_wins_over_cad_subdir` — root searched before
       `cad/`.
     - `test_cad_subdir_when_root_empty` — fallback to `cad/`.
     - `test_sort_determinism_case_insensitive_filesystem` —
       deterministic first-pick across HFS+/APFS; per-suffix
       `sorted()` (not concatenated glob) must NOT double-yield.
     - `test_no_recursion_into_vendored_dirs` — `<case>/.venv/share/…/t20_data.step`
       NOT found.
     - `test_no_step_no_bbox_returns_None_or_empty_artifacts` —
       whole-snapshot `None` collapse.
     - `test_bbox_well_formed_yields_max_extent` —
       `{"bbox":[0,0,0,10,5,2]}` → `bbox_max_extent_raw=10.0`.
     - `test_bbox_key_absent_returns_none_extent` — key absent →
       `None` (DEC-213 R1 carry-forward, distinct test from
       key-malformed).
     - `test_bbox_key_present_malformed_returns_none_extent_per_R1`
       — `{"bbox":[0,0,0]}` arity 3 → `None`, BUT `step_path` still
       populated (per-field, not whole-snapshot).
     - `test_bbox_non_numeric_per_field_none` — `[0,0,0,"oops",5,2]`.
     - `test_bbox_non_list_per_field_none` — `{"bbox":"not a list"}`.
     - `test_extents_malformed_per_field_none` — `[1,2,"oops"]`.
     - `test_manifest_fallback_when_cad_bbox_absent` — manifest
       supplies bbox/extents when `cad/bbox.json` absent.
     - `test_manifest_does_not_override_cad_bbox` — `cad/bbox.json`
       wins (precedence).
     - `test_malformed_json_per_field_none` — `{not valid json` →
       both fields `None`, `step_path` preserved.
     - `test_uppercase_suffix_recognized` — `MODEL.STEP` honored.
     - `test_absolute_path_returned_for_json_safety` — `str` AND
       `Path(step_path).is_absolute()`.
     - `test_extractor_module_loads_without_trimesh` — subprocess
       stub `sys.modules['trimesh']=None`, import + access dataclass
       fields. Mirrors DEC-211 R0 P1.
     - `test_assemble_stack_dispatches_unit_detector_when_step_path_present`
       — live discrimination proof under
       `pytest.importorskip('trimesh')`; positive twin asserts
       `unit_detector` IN dispatched set; negative twin asserts NOT
       in dispatched.
     - `test_no_step_but_bbox_collapses_to_None` — populated
       bbox/extents WITHOUT STEP file → whole-snapshot `None`
       (consumer-gated by `step_path is not None`).
     - `test_corrupt_bbox_value_is_not_silently_swallowed_into_key_absent`
       — DEC-213 R1 carry-forward integration: same `None` outcome
       from two structurally distinct sources via separate tests
       captures silent-drift between arms.
     - `test_return_type_is_step_artifacts_dataclass` — defensive
       against future field-add leakage.
4. Codex relay APPROVE or APPROVE_WITH_COMMENTS-with-inline-fixes
   (cap=3); local commit allowed before review per L2.
5. No regression in v9 + canonical + advisor_stack test sweeps.

## Estimated LOC

- `step_extractor.py` impl: ~150-200 LOC (dataclass + 3 small private
  helpers `_discover_step_path` / `_discover_geometry_metadata` /
  `_compute_bbox_max_extent` / `_coerce_extents` / `_load_json_dict` +
  `extract` + 80-line docstring block).
- `__init__.py` patch: +2 LOC (re-export).
- `tests/test_step_extractor.py`: ~600-800 LOC (drift-parity canary
  parametrized over 27 profiles + ~20 tmp_path edge-case + module-
  loads-without-trimesh subprocess + assemble_stack discrimination
  test). Larger than DEC-213's ~250-320 LOC because of the wider
  shape-canary surface (bbox malformed-key vs absent-key + per-field
  vs whole-snapshot + sort determinism + suffix variations).
- **Total ~750-1000 LOC including tests** — sub-DEC scope (not
  charter, not spike).

## Status

Accepted 2026-05-30 by cfd-chief-engineer under user-approved "α′
extension sub-DEC" L2 route, mirroring DEC-V61-211 / DEC-V61-212 /
DEC-V61-213 landing pattern. Implementation landed locally pending
main-session ratification + Codex R0 review chain.

Confidence: **high** — extractor lifts proven HTTP-path logic
(`_autodiscover_step` + bbox/extents subset of
`_autodiscover_geometry_metadata`) with a single transport adjustment
(silent `None` for malformed instead of HTTPException 400). All 65
tests pass locally (37 passed, 28 skipped under no-trimesh / no
in-repo CAD corpus). Codex R0 expected to surface 0-2 P2/P3 findings
on the truth-chain surface listed in §"Codex review".

## Out of scope (do NOT do under this DEC; record as follow-on)

- ISO 10303-21 header parse (FILE_DESCRIPTION / FILE_NAME /
  FILE_SCHEMA / originating_system / preprocessor / authorization;
  AP203 / AP214 / AP242 schema discrimination). Brief framing
  OVERRIDDEN — defer to v0.2 sub-DEC iff a future advisor needs richer
  header content beyond LENGTH unit (which `parse_step_header_unit`
  already handles).
- Mojibake detection / flagging / decoding. Brief constraint #5
  OVERRIDDEN — defer to `step_brep_inspector` sub-DEC triggered by a
  real CAD-bearing case with Chinese PRODUCT names landing in
  `case_profiles/`.
- Opening the STEP file at byte or semantic level for ANY purpose
  (B-rep parse, header re-read, PRODUCT entity inspection, mojibake
  sniff). Scope-locked OUT.
- Multi-STEP disambiguation by heuristic (size / mtime / name match).
  First-sorted-wins is the v0.1 contract — matches HTTP path
  byte-for-byte.
- Synthesizing bbox / extents from STEP geometry when `bbox.json`
  absent. Requires OpenCascade / FreeCAD; violates stdlib-only.
- Caching across calls. Pure read-every-time.
- Writing anything to disk. Pure read-only.
- DRYing / lifting `ai_review.py:_autodiscover_step` +
  `:_autodiscover_geometry_metadata` after both have ≥1 release bake.
  Separate refactor DEC.
- Wire-form `step_bbox` validation parity with `_bbox_max_extent`
  (HTTP raises 400, extractor silently returns `None` — by design,
  different transport).
- A `cad_artifacts_extractor` aggregating STEP + STL + face_normals +
  stl_bbox_set into one snapshot — v0.2 convenience; v0.1 keeps one
  extractor per kwarg-cluster for Codex review surface.
- Recursing into vendored directories (`.venv/`, `node_modules/`).
  Only `(case_dir, case_dir/cad)` are checked — pinned by
  `test_no_recursion_into_vendored_dirs`.
- `thin_wall_inputs_extractor` — separate sub-DEC; geometry-derived
  from STL.
- Wiring the extractor into production `ai_diagnose.py` /
  `ai_review.py` routes (route-side discovery decision under a
  different DEC).
- Extending behavioral assertions to FULL E-case firing sets (needs
  all extractors landed first).

— cfd-chief-engineer, 2026-05-30
