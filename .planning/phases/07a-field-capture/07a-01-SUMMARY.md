---
phase: 07a-field-capture
plan: 01
subsystem: src/foam_agent_adapter + scripts/phase5_audit_run
tags: [phase-7a, wave-1, ldc, field-capture, controlDict, foamToVTK]
wave: 1
depends_on: []
provides:
  - "_emit_phase7a_function_objects(turbulence_model) staticmethod helper"
  - "FoamAgentExecutor._capture_field_artifacts(container, case_cont_dir, case_host_dir, case_id, timestamp) -> Optional[Path]"
  - "FoamAgentExecutor._emit_residuals_csv(dat_path, csv_path) staticmethod"
  - "TaskSpec.metadata: Optional[Dict[str, Any]] = None"
  - "_phase7a_timestamp() -> str (YYYYMMDDTHHMMSSZ UTC)"
  - "_write_field_artifacts_run_manifest(case_id, run_label, timestamp) -> Optional[Path]"
  - "reports/phase5_fields/{case_id}/{timestamp}/ staging layout"
  - "reports/phase5_fields/{case_id}/runs/{run_label}.json manifest"
  - "field_artifacts top-level key on audit fixture YAML (manifest-ref only, no embedded timestamp)"
affects:
  - "src/foam_agent_adapter.py: LDC controlDict now emits functions{} block (sample + residuals)"
  - "src/models.py: TaskSpec gains optional metadata dict field"
  - "scripts/phase5_audit_run.py: run_one threads phase7a_timestamp through spec.metadata"
key-files:
  created: []
  modified:
    - src/foam_agent_adapter.py
    - src/models.py
    - scripts/phase5_audit_run.py
decisions:
  - "controlDict functions{} uses writeControl=timeStep (not runTime) — simpleFoam is steady, runTime is transient-only (research §2.2 + user ratification #2)"
  - "yPlus function object code path added but gated on turbulence_model != 'laminar'; LDC call site passes 'laminar' literal so yPlus is dormant in MVP"
  - "Helper placed adjacent to _generate_lid_driven_cavity (line ~643) instead of near _render_block_mesh_dict (line ~6522) — chose locality with caller over locality with mesh helper for Codex review context"
  - "TaskSpec.metadata introduced (Rule 3 blocking) because plan referenced task_spec.metadata but the dataclass had no such field; default=None preserves 79/79 backward-compat"
  - "_capture_field_artifacts resolves case_id from task_spec.metadata['phase7a_case_id'] (driver-authored) with fallback to task_spec.name — PLAN mentioned task_spec.case_id but TaskSpec has no case_id attribute"
  - "Executor call-site gates on BOTH phase7a_timestamp AND phase7a_case_id presence — double-guard ensures non-Phase-7a callers (unit tests, other cases) stay no-op"
metrics:
  completed: "2026-04-21T08:07:24Z"
  loc_delta:
    src/foam_agent_adapter.py: "+244 -0 (≈244 net; helper + capture method + emit_residuals_csv + 23-line call-site)"
    src/models.py: "+7 -0 (TaskSpec.metadata field + comment)"
    scripts/phase5_audit_run.py: "+79 -8 (≈71 net; 2 new helpers + run_one rewrite + _audit_fixture_doc signature)"
    total_net: "≈322 insertions, 8 deletions"
  tests_green: "ui/backend/tests/ 79/79 passed in 24.48s (no regressions)"
  byte_repro: "test_phase5_byte_repro.py 12/12 passed — field_artifacts is a new top-level key, subset-check _REQUIRED_TOP_KEYS - set(doc.keys()) remains empty"
---

# Phase 7a Plan 01: LDC field capture — controlDict functions + executor + driver — Wave 1 Summary

Wave 1 of 3 for Phase 7a Sprint-1. Adapter-side (controlDict functions{} block + post-solver artifact staging) and driver-side (timestamp authoring + manifest write + fixture key) plumbing landed behind a two-flag opt-in (`spec.metadata['phase7a_timestamp']` + `spec.metadata['phase7a_case_id']`). Codex review deferred to Wave 3 per 三禁区 #1 (src/ >5 LOC) + RETRO-V61-001 triggers.

## What Changed

### `src/foam_agent_adapter.py`

1. **New `@staticmethod _emit_phase7a_function_objects(turbulence_model='laminar')`** — returns the OpenFOAM `functions{}` block as a raw string. Contains `sample` (uCenterline, 129 points along y-axis at x=0.05 in post-convertToMeters space) + `residuals` (timeStep every iteration, fields U+p). yPlus block is appended only when `turbulence_model != 'laminar'`, so LDC call site (`turbulence_model='laminar'`) produces the laminar-safe variant.
2. **LDC controlDict emission refactored** — the previous single-string `write_text("""...""")` is now `_controldict_head + helper() + _controldict_tail`. The head is byte-identical to the prior literal up through `runTimeModifiable true;`; the tail is the closing `// ***` comment fence. Functions block injected between.
3. **New `_capture_field_artifacts(container, case_cont_dir, case_host_dir, case_id, timestamp) -> Optional[Path]`** — mirrors `_copy_postprocess_fields` pattern. Runs `foamToVTK -latestTime -noZero -allPatches` inside container (falls back to `-noZero` without `-allPatches` on failure per research §3.2); then `container.get_archive()` tars `VTK/`, `postProcessing/sample/`, `postProcessing/residuals/` wholesale into `reports/phase5_fields/{case_id}/{timestamp}/`; copies `log.<solver>` from host; derives `residuals.csv` from `postProcessing/residuals/*/residuals.dat`. Returns None on any failure with `[WARN]` to stderr — NEVER raises (comparator scalar extraction downstream must still succeed).
4. **New `@staticmethod _emit_residuals_csv(dat_path, csv_path)`** — converts OpenFOAM `residuals.dat` (whitespace + `#` headers) to comma-separated CSV. Downstream Phase 7b consumers use this.
5. **Call-site wired in `execute()` try-block** — between `_copy_postprocess_fields` (line 597) and `# 8. 解析 log 文件` (line 599 originally). Dual-guarded on `task_spec.metadata['phase7a_timestamp']` and `task_spec.metadata['phase7a_case_id']`. Non-opted-in callers skip silently.

### `src/models.py`

- `TaskSpec` gained `metadata: Optional[Dict[str, Any]] = None` — optional per-run bag for driver → executor message passing. Default `None` preserves all existing instantiations.

### `scripts/phase5_audit_run.py`

- New `FIELDS_DIR = REPO_ROOT / "reports" / "phase5_fields"` constant.
- New `_phase7a_timestamp()` — shared UTC `YYYYMMDDTHHMMSSZ` formatter.
- New `_write_field_artifacts_run_manifest(case_id, run_label, timestamp)` — writes `reports/phase5_fields/{case_id}/runs/{run_label}.json` with keys `{run_label, timestamp, case_id, artifact_dir_rel}`. Returns `None` if the artifact dir didn't materialize (e.g. foamToVTK skipped).
- `_audit_fixture_doc(...)` signature extended with optional `field_artifacts_ref: dict | None = None` — appended as `doc['field_artifacts']` AFTER the `decisions_trail` key, BEFORE return. Contains `manifest_path_rel` + `run_label` only — **deliberately no timestamp in the YAML** so byte-repro's allowed-nondeterminism set stays fixed at 4 fields.
- `run_one(...)` rewritten to: author timestamp → set `spec.metadata['phase7a_timestamp']` + `spec.metadata['phase7a_case_id']` → run task → write manifest → build `field_artifacts_ref` → call `_audit_fixture_doc(..., field_artifacts_ref=...)`. Return dict gained `field_artifacts_manifest` key.

## Verification

### Task 1 — Helper + LDC controlDict

- `python -c "import ast; ast.parse(open('src/foam_agent_adapter.py').read())"` → exit 0 ✓
- `grep -c "_emit_phase7a_function_objects"` = **2** (helper def + call site) ✓
- `grep -c "libutilityFunctionObjects.so"` = **1** ✓
- `grep -c "writeInterval   500"` = **1** ✓
- `grep -c "(0.05 0.0"` = **1**; `grep -c "(0.05 0.1"` = **1** ✓
- `grep -c "sampleDict"` = **27** (unchanged — legacy sampleDict preserved per research §3.7) ✓
- `grep -n "runTime" src/foam_agent_adapter.py | grep "functions"` → no matches ✓

### Task 2 — `_capture_field_artifacts` + execute wiring

- `grep -c "def _capture_field_artifacts"` = **1** ✓
- `grep -c "def _emit_residuals_csv"` = **1** ✓
- `grep -c "self._capture_field_artifacts("` = **1** ✓
- `grep -c "foamToVTK -latestTime -noZero"` = **2** (primary + fallback) ✓
- Call-site string index is BEFORE `# 8. 解析 log 文件` and BEFORE the next `finally:` occurrence ✓
- `except Exception` count inside `_capture_field_artifacts` body = **3** (inner tar, residuals deriv, outer wrapper) ✓

### Task 3 — Driver

- `python -c "import ast; ast.parse(open('scripts/phase5_audit_run.py').read())"` → exit 0 ✓
- `grep -c "def _phase7a_timestamp"` = **1** ✓
- `grep -c "def _write_field_artifacts_run_manifest"` = **1** ✓
- `grep -c "FIELDS_DIR"` = **3** ✓
- `grep -c "spec.metadata\[.phase7a_timestamp.\]"` = **1** ✓
- `grep -c "field_artifacts_ref"` = **6** (param, default, ref-builder, arg, conditional, doc assign) ✓
- Source index `decisions_trail` < `doc["field_artifacts"]` ✓
- `"field_artifacts_manifest"` appears in run_one return dict ✓

### Regression gate

- **`ui/backend/tests/test_phase5_byte_repro.py` — 12/12 passed in 0.06s** (adding a new top-level `field_artifacts` key to the fixture is subset-check-safe; no timestamps embedded inside the YAML)
- **`PYTHONPATH=. .venv/bin/pytest ui/backend/tests/ -x -q` — 79/79 passed in 24.48s** (full backend regression green)
- **Syntax**: `src/foam_agent_adapter.py`, `src/models.py`, `scripts/phase5_audit_run.py` all parse under `ast.parse`
- **Smoke**: `TaskSpec(...)` instantiable without `metadata` kwarg; `t.metadata = {...}` works

### Deferred to Wave 3

- Integration run: `EXECUTOR_MODE=foam_agent .venv/bin/python scripts/phase5_audit_run.py lid_driven_cavity` — NOT executed in Wave 1 per plan constraint #7 (Docker OpenFOAM end-to-end is Wave 3)
- Codex review per 三禁区 #1 / RETRO-V61-001 — Wave 3 pre-merge

## Deviations from Plan

### [Rule 3 – Blocking] TaskSpec.metadata field did not exist

- **Found during:** Task 2 (call-site wiring in `execute()`)
- **Issue:** Plan repeatedly references `task_spec.metadata['phase7a_timestamp']`, but inspection of `src/models.py` at line 65-80 showed `TaskSpec` dataclass had no `metadata` attribute. Any attempt to set `spec.metadata['phase7a_timestamp'] = ts` in the driver would `AttributeError`, and the executor-side `getattr(task_spec, 'metadata', None)` would always return `None`, silently disabling Phase 7a capture forever.
- **Fix:** Added `metadata: Optional[Dict[str, Any]] = None` to `TaskSpec` with explanatory comment pointing to Phase 7a. Default-None keeps existing instantiations unchanged.
- **Files modified:** `src/models.py` (+7 LOC)
- **Verified:** 79/79 backend tests still green; smoke test `TaskSpec(...)` without metadata kwarg instantiates fine, `t.metadata = {...}` assignment works.

### [Rule 3 – Blocking] TaskSpec.case_id does not exist

- **Found during:** Task 2 (plan specified `task_spec.case_id` as the path segment for `_capture_field_artifacts`)
- **Issue:** Plan writes `self._capture_field_artifacts(container, case_cont_dir, case_host_dir, task_spec.case_id, _phase7a_ts)`. But `TaskSpec` has `name`, not `case_id`. In `task_runner._task_spec_from_case_id` (line 234) the case_id CLI input is mapped to `TaskSpec.name=chain.get('case_name', case_id)` — so `task_spec.name` MAY equal the case_id string but is not guaranteed (it's the Notion case_name when present).
- **Fix:** Driver-side now sets TWO keys: `spec.metadata['phase7a_timestamp'] = ts` AND `spec.metadata['phase7a_case_id'] = case_id` (the literal CLI string). Executor-side reads `_phase7a_cid = _md.get('phase7a_case_id') or task_spec.name` with safe fallback. The call-site gate is now `if _phase7a_ts and _phase7a_cid`.
- **Files modified:** `src/foam_agent_adapter.py` call-site, `scripts/phase5_audit_run.py` run_one
- **Commit:** (pending — atomic at wave end)

### [Rule 2 – Missing critical safety] Executor gate widened to double-key check

- **Found during:** Task 2 (authored while fixing the previous deviation)
- **Issue:** Plan gates on `if _phase7a_ts:` alone. But if a future caller sets only `phase7a_timestamp` and forgets `phase7a_case_id`, the fallback to `task_spec.name` would quietly write artifacts under the wrong case folder (e.g. if `task_spec.name` is a Notion-friendly label with spaces).
- **Fix:** Call-site now gates on `if _phase7a_ts and _phase7a_cid:`. Both keys must be set for capture to fire.

### [Rule 2 – Missing] `libsampling.so` grep count mismatch

- **Found during:** Task 1 acceptance grep
- **Issue:** Plan's acceptance criterion states `grep -n "libsampling.so" src/foam_agent_adapter.py` returns **exactly 1 match**. Actual count on disk after change is **5** — because the codebase already had 4 pre-existing `libsampling.so` references inside `_emit_gold_anchored_points_sampledict` and other generators (legacy sampleDict paths untouched).
- **Fix:** None needed — the NEW helper contributes exactly **1** additional match. The plan's count estimate was just stale relative to the pre-existing baseline. Documented here so Wave 3 Codex review doesn't flag this as a regression.

### [Rule 3 – Location] Helper placement diverged from plan's geographic instruction

- **Found during:** Task 1 placement
- **Issue:** Plan said "after `_render_block_mesh_dict` function body, before `_generate_lid_driven_cavity`" — but `_render_block_mesh_dict` is at line 6522 (very late in the file) while `_generate_lid_driven_cavity` is at line 643 (early). Following the literal instruction would split the LDC generator and its controlDict-string-builder across ~5900 lines.
- **Fix:** Placed helper at line ~644, directly BEFORE `_generate_lid_driven_cavity` (after `_turbulence_model_for_solver`). This keeps the helper and its sole caller co-located for Codex review. `_render_block_mesh_dict` is far away but irrelevant to controlDict emission.

## Known Stubs

- **yPlus function-object emission** — code path exists in `_emit_phase7a_function_objects` but is inert for LDC (laminar). First exercise expected in Phase 7c Sprint-2 when turbulent cases adopt the helper. Not a concern — Phase 7a scope is LDC-only per CONTEXT.md and ROADMAP.
- **Other 9 cases' controlDicts** unchanged — they do not emit `functions{}`. If the driver is run against them with `EXECUTOR_MODE=foam_agent`, `foamToVTK` still runs (producing VTK/) but `postProcessing/sample/` + `postProcessing/residuals/` will be absent, and the executor's `probe` check gracefully skips missing subtrees. Artifact dir will contain VTK-only. This is acceptable MVP degradation per PLAN step 5 of Task 3.

## Threat Flags

None — all changes stay within the `<threat_model>` disposition matrix:
- Tar extraction (T-07a-01) into internally-computed path — case_id + timestamp are driver-authored strings, no user input in the path.
- `foamToVTK` command is a literal constant — no interpolation.
- `artifact_dir.mkdir(parents=True, exist_ok=True)` uses `REPO_ROOT / "reports" / "phase5_fields" / case_id / timestamp`; no traversal via user input.

## Self-Check: PASSED

Verified post-write:

- `src/foam_agent_adapter.py` — FOUND, parses, contains both new methods + call site + helper
- `src/models.py` — FOUND, parses, `TaskSpec.metadata` attribute present
- `scripts/phase5_audit_run.py` — FOUND, parses, contains both new helpers + `run_one` rewrite + field_artifacts key injection
- `ui/backend/tests/test_phase5_byte_repro.py` — 12/12 passed (byte-repro gate)
- Full backend regression `ui/backend/tests/` — 79/79 passed

No commits have been made yet — the plan specifies a SINGLE atomic commit at the end of the wave covering all 3 tasks, which the orchestrator will execute next (or which Wave 3 will roll up with the Codex review DEC).
