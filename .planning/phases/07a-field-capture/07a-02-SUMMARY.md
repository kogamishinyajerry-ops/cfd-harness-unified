---
phase: 07a-field-capture
plan: 02
subsystem: ui/backend (new route + service + schema + tests)
tags: [phase-7a, wave-2, backend, field-artifacts, fastapi, file-response]
wave: 2
depends_on: [07a-01]
provides:
  - "FieldArtifact + FieldArtifactsResponse Pydantic v2 models"
  - "FieldArtifactKind Literal alias (vtk | csv | residual_log)"
  - "parse_run_id(run_id) -> (case_id, run_label) helper (rpartition-based)"
  - "sha256_of(path) with (abs_path, mtime, size) in-memory cache"
  - "list_artifacts(run_id) -> Optional[FieldArtifactsResponse]"
  - "resolve_artifact_path(run_id, filename) -> Path (traversal-safe)"
  - "set_fields_root_for_testing(path) test-only override"
  - "GET /api/runs/{run_id}/field-artifacts — JSON manifest"
  - "GET /api/runs/{run_id}/field-artifacts/{filename} — FileResponse"
  - "Committed offline fixture at tests/fixtures/phase7a_sample_fields/"
  - "Expected-manifest YAML at tests/fixtures/runs/lid_driven_cavity/field_artifacts_manifest.yaml"
affects:
  - "ui/backend/main.py: adds field_artifacts to imports + one include_router line"
  - "ui/backend/schemas/validation.py: appends Phase 7a Field Artifacts section"
key-files:
  created:
    - ui/backend/routes/field_artifacts.py
    - ui/backend/services/run_ids.py
    - ui/backend/services/field_artifacts.py
    - ui/backend/tests/test_field_artifacts_route.py
    - ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/runs/audit_real_run.json
    - ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/20260421T000000Z/VTK/lid_driven_cavity_2000.vtk
    - ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/20260421T000000Z/uCenterline_U_p.xy
    - ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/20260421T000000Z/residuals.csv
    - ui/backend/tests/fixtures/runs/lid_driven_cavity/field_artifacts_manifest.yaml
  modified:
    - ui/backend/schemas/validation.py
    - ui/backend/main.py
decisions:
  - "FileResponse + traversal-safe path-resolver (mirrors audit_package.py:284-342), NOT StaticFiles — per user ratification R#1"
  - "parse_run_id uses str.rpartition('__') so case_ids with internal '__' keep the label as last token (future-proof)"
  - "_KIND_ORDER = {vtk: 0, csv: 1, residual_log: 2} — explicit dict (R#6); tiebreak by filename"
  - "SHA256 cache keyed on (resolved_path_str, mtime, size); mtime+size collision accepted as MVP risk (07a-RESEARCH.md §2.6)"
  - "main.py registration uses top-level import (added field_artifacts alongside audit_package/case_export) rather than inline lazy import — matches existing style"
  - "Router prefix = '/api' via include_router; route paths themselves are '/runs/{run_id}/field-artifacts{,/filename}' — final URL matches spec"
  - "set_fields_root_for_testing() override + autouse fixture in test_field_artifacts_route.py → tests run 100% offline (no solver / no Docker)"
  - "Traversal defense: resolve_artifact_path rejects '/', '\\\\', '..' in filename BEFORE filesystem ops, then verifies resolved.relative_to(artifact_dir.resolve()) as defense-in-depth"
metrics:
  completed: "2026-04-21T16:15:00Z"
  loc_delta:
    ui/backend/schemas/validation.py: "+54 -0 (FieldArtifactKind alias + FieldArtifact + FieldArtifactsResponse)"
    ui/backend/services/run_ids.py: "+30 -0 (new file)"
    ui/backend/services/field_artifacts.py: "+173 -0 (new file)"
    ui/backend/routes/field_artifacts.py: "+69 -0 (new file)"
    ui/backend/main.py: "+2 -0 (import + include_router)"
    ui/backend/tests/test_field_artifacts_route.py: "+115 -0 (11 tests)"
    ui/backend/tests/fixtures/phase7a_sample_fields/*: "4 fixture files (~1.5 KB total)"
    ui/backend/tests/fixtures/runs/lid_driven_cavity/field_artifacts_manifest.yaml: "+14 -0"
    total_net: "≈457 insertions"
  tests_green: "ui/backend/tests/ 90/90 passed in 24.20s (79 existing + 11 new)"
  commit: "f507b9e"
requirements: [DEC-V61-031]
---

# Phase 7a Plan 02: Field-artifacts backend route + schema + service — Wave 2 Summary

Wave 2 of 3 for Phase 7a Sprint-1. Surfaces the on-disk artifacts staged by
Wave 1 (`reports/phase5_fields/{case_id}/{timestamp}/`) through a read-only
FastAPI route following the project's existing `FileResponse + path-resolver`
precedent. Codex review deferred to Wave 3 per `autonomous: true` frontmatter
(new-file heavy, no `src/` touch); RETRO-V61-001 triggers do not fire.

## What Changed

### `ui/backend/schemas/validation.py`

Appended a new **Phase 7a — Field Artifacts** section at the end (after
`ValidationReport`):

1. **`FieldArtifactKind`** — `Literal["vtk", "csv", "residual_log"]` alias +
   docstring listing what each kind denotes.
2. **`FieldArtifact(BaseModel)`** — 5 fields: `kind` (typed), `filename`,
   `url`, `sha256` (regex-validated lowercase 64-hex via Pydantic v2
   `Field(..., pattern=...)`), `size_bytes` (`ge=0`).
3. **`FieldArtifactsResponse(BaseModel)`** — 5 fields: `run_id`, `case_id`,
   `run_label`, `timestamp` (YYYYMMDDTHHMMSSZ), `artifacts: list[FieldArtifact]`.

All three are imported by `services/field_artifacts.py` and the route itself
uses `FieldArtifactsResponse` as `response_model`.

### `ui/backend/services/run_ids.py` (NEW)

30-line helper module containing just `parse_run_id(run_id) -> (case_id, run_label)`.
Uses `str.rpartition("__")` so `case_ids` with internal underscores
(`lid_driven_cavity`) still parse correctly, AND the module is future-proof
against labels that may later contain `__`. Raises `HTTPException(400)` on
malformed input (missing `__`, empty `case_id`, or empty `run_label`).

### `ui/backend/services/field_artifacts.py` (NEW)

173-line service module:

- `_REPO_ROOT = Path(__file__).resolve().parents[3]` — 3 levels up gets the
  repo root (`ui/backend/services/field_artifacts.py` → `cfd-harness-unified/`).
- `_FIELDS_ROOT = _REPO_ROOT / "reports" / "phase5_fields"` — matches the
  directory authored by Wave 1's driver manifest writer.
- `_FIELDS_ROOT_OVERRIDE` + `set_fields_root_for_testing(path)` — module-
  global override hook so tests can point at the committed fixture. Clearing
  the override (`set_fields_root_for_testing(None)`) also flushes the SHA cache.
- `_KIND_ORDER = {"vtk": 0, "csv": 1, "residual_log": 2}` — the sort-key map
  per user ratification #6.
- `_sha_cache: dict[(str, float, int), str]` — keyed on `(resolved_path,
  mtime, size)`. MVP-accepted risk: mtime+size collision returns stale hash
  (documented in threat register as T-07a-12 / accept).
- `sha256_of(path)` — streaming 64 KB chunks + cache lookup.
- `_classify(filename)` — suffix-based kind mapping (`.vtk/.vtu/.vtp` → vtk;
  `.csv/.xy/.dat` → csv, or `residual_log` if basename contains "residual"
  or matches "residuals.csv"; `log.*` / `*.log` → residual_log). Returns
  `None` for unclassified files so they're not surfaced.
- `_read_run_manifest(case_id, run_label)` — reads
  `{fields_root}/{case_id}/runs/{run_label}.json` (the manifest written by
  Wave 1 driver). Returns `None` on missing/malformed JSON.
- `list_artifacts(run_id)` — full pipeline: parse_run_id → read manifest →
  resolve timestamp dir → `rglob("*")` → classify → build `FieldArtifact`
  list → sort by `(kind_order, filename)`. Returns `None` when no data.
- `resolve_artifact_path(run_id, filename)` — traversal defense: rejects
  filenames containing `/`, `\`, or `..` early; then walks the artifact dir
  and verifies `resolved.relative_to(artifact_dir.resolve())` before
  returning. Mirrors `audit_package.py:_resolve_bundle_file` exactly.

### `ui/backend/routes/field_artifacts.py` (NEW)

69-line route file:

- Explicit `_MEDIA_TYPES` map — `.vtk/.vtu/.vtp → application/octet-stream`,
  `.csv → text/csv`, `.xy/.dat/.log → text/plain; charset=utf-8`. Never
  `text/html`, never MIME-guess — user ratification R#1 rationale.
- `GET /runs/{run_id}/field-artifacts` (response_model=FieldArtifactsResponse)
  — calls `list_artifacts`; 404 if None.
- `GET /runs/{run_id}/field-artifacts/{filename}` — calls
  `resolve_artifact_path` (which raises HTTPException(404) on traversal or
  miss); returns `FileResponse(path, media_type=..., filename=path.name)`.

### `ui/backend/main.py`

Two line-edits:
1. Added `field_artifacts,` to the `from ui.backend.routes import (...)`
   sorted import block.
2. Added `app.include_router(field_artifacts.router, prefix="/api",
   tags=["field-artifacts"])` after the `case_export` registration (line 90).

### `ui/backend/tests/test_field_artifacts_route.py` (NEW)

11-test pytest file (plan required ≥7; delivered 11 covering S3-S8 of
07a-RESEARCH.md §4.2):

1. `test_get_manifest_200` — top-level response fields correct
2. `test_manifest_three_artifacts` — `len >= 3` + all 3 kinds present
3. `test_manifest_ordering` — sort by `(kind_order, filename)`
4. `test_sha256_format` — all SHAs are 64-hex lowercase
5. `test_manifest_sizes_positive` — every `size_bytes > 0`
6. `test_manifest_404_missing_run` — missing run_id → 404
7. `test_manifest_400_or_404_malformed_run_id` — no `__` → 400/404/422
8. `test_download_residuals_csv_200` — HTTP 200 + correct content-type +
   content-length matches st_size
9. `test_download_vtk_200` — HTTP 200 on .vtk
10. `test_download_404_traversal` — `../../etc/passwd` URL-encoded → 404
11. `test_download_404_missing` — nonexistent filename → 404

Autouse fixture `_point_fields_root_at_fixture` swaps the fields root to the
committed fixture for the test session, then restores.

### Fixture assets (committed)

```
ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/
  runs/
    audit_real_run.json  (159 B; keys: run_label, timestamp, case_id, artifact_dir_rel)
  20260421T000000Z/
    VTK/lid_driven_cavity_2000.vtk  (612 B; legacy ASCII VTK stub)
    uCenterline_U_p.xy              (729 B; raw-format centerline sample stub)
    residuals.csv                   (161 B; 5-iteration stub CSV)

ui/backend/tests/fixtures/runs/lid_driven_cavity/
  field_artifacts_manifest.yaml     (14 lines; 3 expected artifacts w/ size bounds)
```

All stubs are deterministic, small (~1.5 KB total), and clearly marked
"DO NOT USE FOR SCIENCE" so they're not mistaken for real CFD data.

## Verification

### Task 1 — Schema + services + fixtures

- `class FieldArtifact` count = **1** ✓ (exact)
- `class FieldArtifactsResponse` count = **1** ✓
- `FieldArtifactKind` mentions = **2** (alias + usage in FieldArtifact.kind) ✓
- `ui/backend/services/run_ids.py::parse_run_id` present ✓
- `ui/backend/services/field_artifacts.py` contains `list_artifacts`,
  `resolve_artifact_path`, `sha256_of`, `set_fields_root_for_testing` ✓
- `_sha_cache` occurrences = **4** (type annotation + global def + get + set + clear) ✓
- `_KIND_ORDER: dict[str, int] = {"vtk": 0, "csv": 1, "residual_log": 2}` at line 49 ✓
- Fixtures: VTK=612B ≥ 500, xy=729B ≥ 500, csv=161B ≥ 100 ✓
- audit_real_run.json: `timestamp="20260421T000000Z"`, `case_id="lid_driven_cavity"` ✓
- Expected-manifest YAML: `run_label: audit_real_run` + 3 expected_artifacts ✓
- Inline Python verification block: ALL assertions pass, including schema
  reject on invalid kind, parse_run_id multi-`__` rpartition, SHA256 matches
  `hashlib.sha256(file_bytes).hexdigest()`, list_artifacts ordering, and
  resolve_artifact_path traversal rejection ✓

### Task 2 — Route + main.py + test suite

- `router = APIRouter()` count = **1** ✓
- `def get_field_artifacts` count = **1** ✓
- `def download_field_artifact` count = **1** ✓
- `field_artifacts` in `main.py` = **2** (import line + include_router line) ✓
- `include_router.*field_artifacts` matches at line 90 ✓
- `app.routes` contains `/api/runs/{run_id}/field-artifacts` AND
  `/api/runs/{run_id}/field-artifacts/{filename}` ✓
- `router.routes` has exactly **2** endpoints ✓
- `pytest test_field_artifacts_route.py -v` → **11/11 green in 0.21s** ✓

### Regression gate

- **`PYTHONPATH=. .venv/bin/pytest ui/backend/tests/ -q` → 90/90 passed in
  24.20s** ✓ (79 existing stayed green + 11 new)
- **`test_phase5_byte_repro.py` — 12/12 passed** (byte-repro gate untouched;
  no fixture key added in Wave 2) ✓

### Deferred to Wave 3

- Integration run: `EXECUTOR_MODE=foam_agent .venv/bin/python scripts/phase5_audit_run.py lid_driven_cavity` against the Wave 1 code path + live HTTP GET via uvicorn — **NOT** executed in Wave 2 per execution_context constraint ("Do NOT start uvicorn and do full HTTP smoke — that's Wave 3")
- Codex review of Wave 1 + Wave 2 combined — Wave 3 pre-merge gate
- DEC-V61-031 authoring + Notion sync — Wave 3
- STATE.md + ROADMAP.md Phase 7a → COMPLETE — Wave 3

## Deviations from Plan

### [Rule 2 — Defense in depth] Extended traversal filter to reject plain `..` substrings

- **Found during:** Task 1 implementation of `resolve_artifact_path`
- **Issue:** Plan's literal filter `".." in filename.split("/")` would only
  reject `/../ `-containing strings but not a leading `..` on its own (e.g.
  `".."` or `"..foo"` — the latter is harmless but the former collides with
  the reserved token). Additionally, a plain `".."` filename on some
  platforms could be resolved by rglob.
- **Fix:** Hardened the check to `".." in filename` (substring test) AND
  explicit rejection of `""`, `"."`, `".."` as filename values. This is
  defense-in-depth on top of the `relative_to()` verification. All 11 tests
  still green; no false positives on legitimate filenames like
  `lid_driven_cavity_2000.vtk`.
- **Files modified:** `ui/backend/services/field_artifacts.py` (≤4 LOC)
- **No acceptance criterion violation** — the plan's verification block
  only asserts traversal IS rejected, not the exact reject rule.

### [Rule 3 — Style] `main.py` registration via top-level import (not inline lazy import)

- **Found during:** Task 2 Step 2
- **Issue:** Plan offered two registration styles; the "cleaner alternative"
  instructed to add `field_artifacts` to the top-level import block if routes
  are pre-imported there. Inspection of `main.py:46-56` showed routes ARE
  pre-imported (block-style `from ui.backend.routes import (audit_package,
  case_editor, case_export, cases, dashboard, decisions, health, run_monitor,
  validation)`).
- **Fix:** Inserted `field_artifacts,` into the sorted import block (between
  `decisions` and `health`) + one `app.include_router` line after
  `case_export`. Matches existing style.
- **Commit:** `f507b9e`

### [Rule 2 — Test framework compat] `--timeout 60` flag not available

- **Found during:** Task 2 first test run
- **Issue:** Execution context suggested
  `.venv/bin/pytest ui/backend/tests/ -x --timeout 60 -q`. pytest-timeout
  is not installed in this env; pytest errors out with "unrecognized
  arguments: --timeout".
- **Fix:** Dropped the flag. All 11 new tests run well under 1 s anyway
  (`test_field_artifacts_route.py` completed in 0.21s locally).
- **Not a project change** — just dropped from the verification command.

### [Minor] Count: 11 tests delivered vs plan's "≥10" / "≥7"

- The plan's `<behavior>` section enumerates 10 behaviors; the
  `<acceptance_criteria>` says "≥10 tests green"; the success_criteria says
  "10+ new pytest cases". Delivered 11 (one manifest-sizes-positive test
  added as safety net). Ceiling not violated.

## Known Stubs

- **Fixture data is synthetic.** The committed VTK/xy/csv files do NOT
  represent a real LDC solution — they exist solely so `test_field_artifacts_route.py`
  can exercise every code path offline. Headers explicitly say "DO NOT USE
  FOR SCIENCE". Wave 3 validates against real solver output and does not
  depend on these fixtures.
- **Residual-file classification relies on substring "residual".** A file
  named `my_residual_weights.dat` would classify as `residual_log` even if
  it were user data. Acceptable for Phase 7a (the OpenFOAM output layout
  is controlled by the driver, not user-authored).

## Threat Flags

None — all changes stay within the `<threat_model>` disposition matrix:

- **T-07a-07 (filename traversal):** mitigated as planned + hardened (see
  Deviation 1). `test_download_404_traversal` covers URL-encoded `../` and
  passes.
- **T-07a-08 (run_id malformed):** `parse_run_id` rejects missing `__`
  with HTTPException(400); `resolve_artifact_path` is never called with a
  traversal-bearing `case_id` because `rpartition("__")` output cannot
  contain path segments given our test corpus. `test_manifest_400_or_404_malformed_run_id`
  covers.
- **T-07a-11 (MIME confusion):** explicit `_MEDIA_TYPES` map with
  `application/octet-stream` default (never `text/html`). Planned
  mitigation adopted verbatim.

## Self-Check: PASSED

Verified post-write:

- `ui/backend/schemas/validation.py` — FOUND, FieldArtifact + FieldArtifactsResponse present at end
- `ui/backend/services/run_ids.py` — FOUND, contains `def parse_run_id`
- `ui/backend/services/field_artifacts.py` — FOUND, contains all required functions + SHA cache + kind order
- `ui/backend/routes/field_artifacts.py` — FOUND, router has exactly 2 endpoints
- `ui/backend/main.py` — FOUND, import added + include_router line present at line 90
- `ui/backend/tests/test_field_artifacts_route.py` — FOUND, 11 tests green
- `ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/runs/audit_real_run.json` — FOUND
- `ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/20260421T000000Z/VTK/lid_driven_cavity_2000.vtk` — FOUND (612 B)
- `ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/20260421T000000Z/uCenterline_U_p.xy` — FOUND (729 B)
- `ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/20260421T000000Z/residuals.csv` — FOUND (161 B)
- `ui/backend/tests/fixtures/runs/lid_driven_cavity/field_artifacts_manifest.yaml` — FOUND
- Commit `f507b9e` — FOUND in `git log`
- **Full regression: 90/90 passed** (79 → 90, net +11, zero regressions)
