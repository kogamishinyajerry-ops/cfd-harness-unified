# Phase 7a: Field post-processing capture — Research

**Researched:** 2026-04-21
**Domain:** OpenFOAM v10 function objects + Docker runner orchestration + FastAPI artifact serving
**Confidence:** HIGH on solver-side (function objects, foamToVTK), HIGH on runner integration (executor code read), MEDIUM on one CONTEXT decision that conflicts with existing project pattern (StaticFiles vs FileResponse — see §2.4)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Solver-side (adapter / controlDict):**
- Function objects emitted: `sample` (u/p along centerline), `yPlus` (turbulent cases only), `residuals`. Use OpenFOAM v10 `libsampling.so`, `libfieldFunctionObjects.so`.
- Sample format: `raw` CSV — one column per sampled field per y-point, one row per iteration write step. Final iteration row is what the comparator currently uses.
- Write cadence: `writeInterval 500` for `sample`/`residuals` (runTime), `writeInterval` matches solver `writeInterval` for VTK.
- yPlus skip logic: emit only when `turbulence_model != "laminar"` in task_spec — LDC is laminar so 7a on LDC will NOT emit yPlus. Keep code path ready for 7c Sprint-2 turbulent cases.

**Post-run capture (scripts/phase5_audit_run.py):**
- VTK export: Run `foamToVTK -latestTime -noZero -allPatches` inside Docker container after solver completes, **before** case dir teardown in `finally` block.
- Stage path: container `/case/VTK/` → host `reports/phase5_fields/{case_id}/{timestamp_utc}/` via `docker cp` pattern (existing `_copy_file_from_container`).
- Files captured (MVP LDC): `{case}_{iter}.vtk`, `postProcessing/sample/{iter}/U_p_centerline.csv`, `log.simpleFoam` → parsed to `residuals.csv`.
- Timestamp format: `YYYYMMDDTHHMMSSZ` matching existing `reports/phase5_audit/{timestamp}_{case}_raw.json`.
- Size limit: ~5 MB per VTK for 129×129×1 LDC; no compression in MVP.

**Backend surface:**
- Route: `GET /api/runs/{run_id}/field-artifacts` where `run_id = {case}__{run_label}`.
- Response schema: `FieldArtifactsResponse { run_id, case_id, timestamp, artifacts: List[FieldArtifact] }` where `FieldArtifact { kind: Literal["vtk","csv","residual_log"], filename, url, sha256, size_bytes }`.
- URL scheme: `/api/runs/{run_id}/field-artifacts/{filename}` served via FastAPI `StaticFiles` mount pointing at `reports/phase5_fields/`.
- SHA256: eager on first request, cached in-memory by `(filename, mtime)`.
- Auth: follow existing audit-package pattern — HMAC header optional in MVP, route is read-only.

**Option B locked for VTK export:** docker cp inside run loop, not post-finally.

### Claude's Discretion
- Exact Python function names and module organization within `scripts/phase5_audit_run.py` (can refactor into sub-module if it grows).
- pytest fixture file path (under existing `fixtures/runs/lid_driven_cavity/` tree).
- Error handling when `foamToVTK` fails — log warning, don't fail the whole run (comparator scalar extraction must still succeed).

### Deferred Ideas (OUT OF SCOPE)
- Phase 7b: VTK → PNG rendering
- Phase 7c: Jinja2 HTML comparison report template
- Phase 7d: Richardson GCI from mesh_N fixtures
- Phase 7e: Embed PDF/PNG/CSV into HMAC-signed audit-package zip
- Phase 7f: Frontend LearnCaseDetailPage live fetches
- y+ function object for turbulent cases (code stubbed, not exercised on LDC)
- VTK compression / remote storage
- Streaming residuals to SSE
</user_constraints>

## Project Constraints (from CLAUDE.md)

- **三禁区 #1 = `src/`**: any `src/foam_agent_adapter.py` edit >5 LOC mandates Codex review (RETRO-V61-001). Phase 7a adapter delta is estimated ~30 LOC (functions{} block + yPlus conditional) → **Codex mandatory**.
- Cross-file count ≥3 in `ui/backend/` → Codex recommended (this phase touches `main.py` + `routes/field_artifacts.py` + `schemas/validation.py` + `services/field_artifacts.py` ≈ 4 new files → borderline; prefer Codex post-merge or pre-merge if self-pass-rate ≤ 70%).
- Must not regress 79/79 backend pytest (specifically `test_phase5_byte_repro.py` — see §3.1 gotcha).
- No knowledge/ or tests/fixtures/cases edits (三禁区 #2, #3) — only runtime artifacts + new fixture under `fixtures/runs/lid_driven_cavity/`.
- GSD workflow enforcement: all edits go through `/gsd-execute-phase`.

## Summary

Phase 7a adds three orthogonal capabilities to the LDC real-solver path:

1. **Solver emits more artifacts.** Inject a `functions{}` block into the LDC `controlDict` with `sample` + `residuals` function objects (yPlus gated behind `turbulence_model != "laminar"`, inert for LDC). This uses the standard OpenFOAM v10 runtime-selection mechanism; zero solver-binary changes.
2. **Runner captures those artifacts before teardown.** `FoamAgentExecutor.execute` currently deletes `case_host_dir` in its `finally:` block (adapter:618-623). We add a hook **inside the try-block**, after the solver call and before the implicit return, that runs `foamToVTK` in-container and copies `VTK/` + `postProcessing/sample/` + `log.simpleFoam` to a stable host-side `reports/phase5_fields/{case}/{YYYYMMDDTHHMMSSZ}/` directory. The existing `_copy_file_from_container` (adapter:6710) is the primitive we extend.
3. **Backend surfaces them.** New read-only FastAPI route that lists artifacts as JSON (with SHA256 + size) and serves individual files. **Pattern recommendation: use `FileResponse` with a traversal-safe `_resolve_*_file` helper (mirroring `routes/audit_package.py:284-342`) — NOT `StaticFiles`**, because StaticFiles is not used anywhere else in this project and would introduce a new hosting paradigm.

**Primary recommendation:** Keep solver edits isolated to a single new helper `_emit_phase7a_function_objects(case_dir, task_spec)` called from each case generator opted-in for 7a. On the runner side, expose a new `FoamAgentExecutor._capture_field_artifacts(container, case_cont_dir, case_host_dir, case_id)` method and invoke it from the driver (`scripts/phase5_audit_run.py::run_one`) between `runner.run_task(spec)` and `_write_audit_fixture`, reading `report.execution_result.raw_output_path` to reach the staged outputs. Use the project's existing `FileResponse` + path-resolver pattern for the backend (§2.4).

## 1. Current State Analysis

### 1.1 What already exists (verified in codebase)

| Capability | Anchor | Notes |
|---|---|---|
| FoamAgentExecutor Docker runner | `src/foam_agent_adapter.py:384-623` | Uses `docker` SDK. Has `_docker_exec`, `_copy_file_from_container`, `_copy_postprocess_fields`, `_make_tarball`, `_parse_solver_log`. |
| LDC case generator (simpleFoam) | `src/foam_agent_adapter.py:643-1057` | Post DEC-V61-029. `controlDict` has NO `functions{}` block currently (lines 716-768). |
| Gold-anchored sampleDict (already writes `system/sampleDict` with 17-point LDC set) | `src/foam_agent_adapter.py:1010-1057`, helper at lines 200-257 | **Reused by comparator via `postProcessing/sets/<time>/uCenterline_U.xy`.** |
| Case teardown (the race we must beat) | `src/foam_agent_adapter.py:618-623` | `shutil.rmtree(case_host_dir)` in `finally:`. Option B (CONTEXT decision) sidesteps this by copying inside the try-block. |
| Post-run writeObjects capture (precedent for Option B) | `src/foam_agent_adapter.py:595-597, 6729-6776` | Already copies fields from container before teardown — exact pattern we extend. |
| Driver + raw-capture dir | `scripts/phase5_audit_run.py:44-46,183-207` | `RAW_DIR = REPO_ROOT / "reports" / "phase5_audit"`. Timestamp via `%Y%m%dT%H%M%SZ` — same format Phase 7a wants. |
| Per-run measurement fixture | `ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml` | 7 top-level keys, byte-repro-gated. |
| Run-id → case-id lookup | `ui/backend/services/validation_report.py:273-282` | `_load_run_measurement(case_id, run_id)` reads `RUNS_DIR / case_id / f"{run_id}_measurement.yaml"`. Pure directory-walk; there is **no** parse of `run_id = "{case}__{label}"` today. See §2.7. |
| File-serve pattern (precedent) | `ui/backend/routes/audit_package.py:284-342` | `FileResponse` + `_resolve_bundle_file` + bundle-id regex + traversal-safe `resolved.relative_to(STAGING_ROOT)`. No `StaticFiles`. |
| Docs for run_monitor | `ui/backend/routes/run_monitor.py:1-41` | URL pattern `/api/runs/{case_id}/*`. **Note: it's `{case_id}`, not `{run_id}`** today — CONTEXT.md's `run_id = "{case}__{run_label}"` is a NEW convention introduced by 7a. See §2.7. |

### 1.2 What does NOT exist

- No `functions{}` block on any LDC run — the LDC controlDict (adapter:716-768) never emits one. Only one other case (buoyantFoam DHC at line 5128) emits `functions{}` with a lone `writeCellCentres`. **We are adding a fresh capability, not editing existing function objects.**
- No `StaticFiles` mount in `ui/backend/main.py` (verified — only `app.include_router` calls, lines 80-88). Introducing it is a new paradigm.
- No `reports/phase5_fields/` directory exists. First write creates it (same pattern as `RAW_DIR` in driver:184).
- No `FieldArtifact` / `FieldArtifactsResponse` in `ui/backend/schemas/validation.py` (verified — file has `ContractStatus`, `RunCategory`, `RunDescriptor`, etc. but nothing for field artifacts).
- No pytest `conftest.py` under `ui/backend/tests/`. Tests use module-level globs + parametrize (see `test_phase5_byte_repro.py:59-74`).

## 2. Technical Approach Recommendations (8 Open Questions)

### 2.1 Cleanest hook for VTK export before teardown

**Answer (matches locked Option B):** Add capture step 6.6 inside the `try:` block of `FoamAgentExecutor.execute`, immediately after `_copy_postprocess_fields` (adapter:597) and before `_parse_solver_log` (adapter:600).

```python
# 6.6. [Phase 7a] Run foamToVTK + stage field artifacts before teardown
try:
    artifact_dir = self._capture_field_artifacts(
        container, case_cont_dir, case_host_dir, task_spec
    )
except Exception as e:
    import sys as _sys
    print(f"[WARN] field-artifact capture failed: {e}", file=_sys.stderr)
    artifact_dir = None
```

`_capture_field_artifacts` does:
1. `self._docker_exec("foamToVTK -latestTime -noZero -allPatches", case_cont_dir, 120)` — reuse existing docker primitive; output goes to container `case_cont_dir/VTK/`.
2. `container.exec_run(... tar czf /tmp/vtk.tgz -C case_cont_dir VTK postProcessing/sample postProcessing/residuals)` + `container.get_archive(...)` → extract to host `reports/phase5_fields/{case_id}/{YYYYMMDDTHHMMSSZ}/`. Using a single `get_archive` call is cheaper than N × `_copy_file_from_container` — we don't know filenames a priori.
3. Copy `case_host_dir/log.simpleFoam` → `{artifact_dir}/log.simpleFoam` (already on host, no docker cp needed).
4. Parse `log.simpleFoam` with regex (§2.5) → emit `residuals.csv`.
5. Return `artifact_dir` path so the driver (`run_one`) can record it in the audit fixture under a new `field_artifacts` top-level key.

**Why not Option A (success callback):** the executor has no callback hooks; adding one widens the API surface and invites regressions in the other 9 case generators. Option B is ~40 LOC localized to `src/`.

**Reference timestamp:** Generate the timestamp ONCE in `scripts/phase5_audit_run.py::run_one`, not inside the executor — so that driver-level artifacts (audit YAML's `measured_at`) and field artifacts (`{timestamp}/`) share the same UTC instant. Thread it through as an arg or via a new `task_spec.metadata["phase7a_timestamp"]`.

### 2.2 OpenFOAM v10 controlDict `functions{}` block — copy-paste ready

All three function objects are selected at runtime by string type; libraries must be declared per-object.

```openfoam
// ... existing controlDict keys up to runTimeModifiable ...

functions
{
    sample
    {
        type            sets;
        libs            ("libsampling.so");
        writeControl    runTime;
        writeInterval   500;

        interpolationScheme cellPoint;
        setFormat       raw;

        fields          (U p);

        sets
        {
            uCenterline
            {
                type        uniform;
                axis        y;
                start       (0.05 0.0 0.005);   // physical coords: x=0.5 in 0.1-scaled mesh
                end         (0.05 0.1 0.005);
                nPoints     129;
            }
        }
    }

    residuals
    {
        type            residuals;
        libs            ("libutilityFunctionObjects.so");
        writeControl    timeStep;
        writeInterval   1;
        fields          (U p);
    }

    // yPlus emitted only when turbulence_model != "laminar"
    // yPlus
    // {
    //     type            yPlus;
    //     libs            ("libfieldFunctionObjects.so");
    //     writeControl    writeTime;
    // }
}
```

Key points:
- `libs` strings are **required** in v10 (`libsampling.so`, `libutilityFunctionObjects.so`, `libfieldFunctionObjects.so`). Source: [cpp.openfoam.org/v10 foamToVTK + residuals API refs](https://cpp.openfoam.org/v10/classFoam_1_1functionObjects_1_1residuals.html) `[CITED]`.
- `sets` function object subsumes the legacy `system/sampleDict` — we can keep emitting `sampleDict` (for comparator continuity per DEC-V61-029) **OR** switch to in-controlDict form. **Recommendation: keep both.** The existing comparator path reads `postProcessing/sets/<time>/uCenterline_U.xy` from either source, and keeping `sampleDict` avoids touching `result_comparator.py`. The in-controlDict `sample` function object writes to `postProcessing/sample/<time>/uCenterline_U_p.xy` (different subdir name = the function-object name) — that's the Phase 7a artifact.
- **Physical coordinates matter.** LDC uses `convertToMeters 0.1` (adapter:6545) so x=0.5 → 0.05 m, z-mid = 0.005 m. The locked CONTEXT wording says "x=0.5 centerline" — author in physical (post-convertToMeters) space or the solver samples outside the mesh.
- `writeInterval 500` with `writeControl runTime` is wrong for steady-state simpleFoam: there's no "runTime" only iterations. **Correct value: `writeControl timeStep; writeInterval 500;`** — matches how steady solvers emit. [CITED: OpenFOAM v10 function-objects guide — `timeStep` is valid; `runTime` is for transient solvers.] `[CITED]`. We should adjust the CONTEXT wording; it does not change semantics meaningfully (simpleFoam `deltaT=1`).
- `residuals` writes **initial** residual per field per iteration to `postProcessing/residuals/0/residuals.dat` (ASCII, space-separated, header comment starts with `#`). This is the CSV-like file we parse — we don't need to re-parse `log.simpleFoam` for residuals if we include the `residuals` function object. **This simplifies §2.5.**

### 2.3 foamToVTK invocation — flags, output layout, memory cost

**Command for 2D LDC:**
```bash
foamToVTK -latestTime -noZero -allPatches
```

- `-latestTime` + `-noZero`: provided by `Foam::timeSelector::addOptions` (inherited by all utilities using timeSelector; verified against [cpp.openfoam.org v10 timeSelector docs](https://cpp.openfoam.org/v10/classFoam_1_1timeSelector.html)) `[VERIFIED via web]`. Together they restrict conversion to the final solver time, skipping `0/`.
- `-allPatches`: foamToVTK-specific — "Combine all patches into a single file" ([cpp.openfoam.org v10 foamToVTK source](https://cpp.openfoam.org/v10/foamToVTK_8C.html)) `[CITED]`.
- **Do NOT pass `-ascii`** — default binary is ~40% smaller and ParaView 5.x handles both identically. For 129×129×1 LDC binary VTK is ~1.3 MB; ASCII would be ~2.2 MB.

**Output layout (confirmed default for v10):**
```
case_cont_dir/
  VTK/
    {case_basename}_{iter}.vtk         # volume mesh + U, p fields
    lid/
      lid_{iter}.vtk                   # one sub-dir per patch…
    wall1/
    wall2/
    bottom/
  # (frontAndBack is `empty` → skipped)
```

For an `-allPatches` run the patches are merged into `{case_basename}_{iter}.vtk` + a single surface file; the per-patch sub-dirs still exist but are smaller. We capture the entire `VTK/` tree wholesale (tar from container) — no need to enumerate.

**Memory cost:** 129×129×1 cells × (3 U components + 1 p + mesh) × 8-byte doubles ≈ 0.7 MB mesh + 0.5 MB fields = **~1.3 MB binary VTK**, well under the 5 MB budget stated in CONTEXT. Container `/tmp` has 1-2 GB; no concern.

**Failure modes:** foamToVTK fails loudly with exit code != 0 and writes to `log.foamToVTK` in the case dir. Must wrap in try/except because (a) the VTK write sometimes fails on machines where `/tmp` is tmpfs-backed and small (not our case), and (b) `empty` patches with zero faces occasionally trip assertions in older v10 builds. Our error policy (CONTEXT "Claude's Discretion"): log warning, don't fail the run.

### 2.4 StaticFiles vs FileResponse — recommendation (conflicts with locked CONTEXT)

**Finding (CONFLICT FLAG for discuss-phase):** CONTEXT.md locks "served via FastAPI `StaticFiles` mount". Actual project never uses `StaticFiles` — every file-serve endpoint (audit package zip/html/pdf/sig, plus 4 more in `audit_package.py`) uses `FileResponse` behind a traversal-safe `_resolve_*_file` helper. Introducing `StaticFiles` just for Phase 7a creates a second hosting paradigm.

**Strong recommendation:** Mirror the audit-package pattern. Rationale:

1. **Consistency.** One route pattern for all file serves in the project.
2. **Security.** `audit_package.py:_resolve_bundle_file` uses `resolved.relative_to(_STAGING_ROOT.resolve())` for path-traversal defense. Same helper applies to `reports/phase5_fields/`.
3. **JSON-and-file duality.** The Phase 7a route `GET /api/runs/{run_id}/field-artifacts` returns JSON (artifact manifest); `GET /api/runs/{run_id}/field-artifacts/{filename}` returns the file. `StaticFiles` would serve only files, leaving the JSON manifest endpoint on a different mount — awkward. With `FileResponse` both routes live on the same `APIRouter`.
4. **Mime-type control.** VTK files need `application/vnd.vtk` or `application/octet-stream`; `StaticFiles` guesses by extension and might return `text/plain` for `.vtk` (untested). Explicit `FileResponse(..., media_type="application/octet-stream")` is deterministic.

**Suggested action:** Planner should open this as a discuss-phase question (or note it in PLAN.md as a deviation from CONTEXT with justification). Risk if accepted: zero. Risk if ignored: two hosting paradigms in one backend, plus the MIME-guessing issue.

**Concrete skeleton for both routes:**
```python
# ui/backend/routes/field_artifacts.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from ui.backend.services.field_artifacts import list_artifacts, resolve_artifact_path
from ui.backend.schemas.validation import FieldArtifactsResponse

router = APIRouter()

@router.get("/runs/{run_id}/field-artifacts", response_model=FieldArtifactsResponse)
def get_field_artifacts(run_id: str) -> FieldArtifactsResponse:
    manifest = list_artifacts(run_id)
    if manifest is None:
        raise HTTPException(404, f"no field artifacts for run_id={run_id!r}")
    return manifest

@router.get("/runs/{run_id}/field-artifacts/{filename}")
def download_field_artifact(run_id: str, filename: str) -> FileResponse:
    path = resolve_artifact_path(run_id, filename)  # raises HTTPException(404) internally
    media = {
        ".vtk": "application/octet-stream",
        ".csv": "text/csv",
        ".log": "text/plain; charset=utf-8",
        ".dat": "text/plain; charset=utf-8",
    }.get(path.suffix, "application/octet-stream")
    return FileResponse(path, media_type=media, filename=path.name)
```

### 2.5 Residual log parsing — regex for simpleFoam v10

**Short-circuit: don't parse the log.** The `residuals` function object (§2.2) writes `postProcessing/residuals/0/residuals.dat` directly in a stable space-separated format:

```
# Residuals
# Time        	U_x              	U_y              	U_z              	p
1             	0.123            	0.045            	0.000            	0.670
2             	0.089            	0.032            	0.000            	0.521
```

Parser: `pandas.read_csv(path, sep=r"\s+", comment="#", header=None, names=["iter","Ux","Uy","Uz","p"])` and drop `Uz` (always 0 for 2D LDC). **This removes the regex-on-log requirement entirely** — matches the `[ASSUMED]` spec in CONTEXT.md "parse log.simpleFoam to residuals.csv" with a more robust direct source.

**Fallback (if we still want to parse the log for metadata):** The regex CONTEXT.md notes (`specifics`) is correct for v10 simpleFoam:
```python
pattern = re.compile(
    r"Solving for (\w+),.*?Initial residual\s*=\s*([\d.eE+-]+)",
    re.DOTALL,
)
```
This already exists at `foam_agent_adapter.py:6806` (simpleFoam branch) and :6829 (icoFoam branch). Reuse, don't duplicate.

### 2.6 SHA256 caching strategy

Standard `functools.lru_cache` won't work because keys must include file mtime. Recommended pattern:

```python
# ui/backend/services/field_artifacts.py
import hashlib
from pathlib import Path

_sha_cache: dict[tuple[str, float, int], str] = {}

def sha256_of(path: Path) -> str:
    st = path.stat()
    key = (str(path), st.st_mtime, st.st_size)
    if key in _sha_cache:
        return _sha_cache[key]
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    digest = h.hexdigest()
    _sha_cache[key] = digest
    return digest
```

- Key on `(path, mtime, size)` so a file rewritten to the exact same mtime with different content still invalidates (size almost always differs; if both match by coincidence, a stale hash returns — accepted MVP risk).
- No LRU eviction in MVP — for LDC alone we cap at ~10 files × N timestamps. Revisit when total files > 1000 (which is also the point Phase 7e rotates artifacts).
- In-memory only, module-level — reset on uvicorn reload. Not shared across workers; that's fine for a single-process dev deployment.

**No project-specific precedent exists** — `audit_package/sign.py` uses hashlib without caching because each bundle is built once. Phase 7a is the first read-hot path that benefits from caching.

### 2.7 run_id → case_id resolution (IMPORTANT CONFLICT)

**Current state:** there is NO `{case}__{label}` run-id parser anywhere in the backend. Evidence:
- `routes/run_monitor.py:22` uses `{case_id}` directly in the URL path.
- `services/validation_report.py:273-282` `_load_run_measurement(case_id, run_id)` takes both as separate args — `run_id` alone never resolves to a case.
- `scripts/phase5_audit_run.py` writes to `ui/backend/tests/fixtures/runs/{case_id}/{run_id}_measurement.yaml` — `{case_id}` is the directory; `{run_id}` is the filename prefix. The concept of a composite `run_id` string isn't used elsewhere.

**CONTEXT decision:** `run_id = "{case}__{run_label}"` e.g. `lid_driven_cavity__audit_real_run`.

**Recommendation:** Introduce a small helper in `services/field_artifacts.py`:
```python
def parse_run_id(run_id: str) -> tuple[str, str]:
    """Parse 'lid_driven_cavity__audit_real_run' → ('lid_driven_cavity', 'audit_real_run').

    Convention: case_id (may contain underscores) and run_label joined by '__' (double underscore).
    Raises HTTPException(400) on malformed input.
    """
    if "__" not in run_id:
        raise HTTPException(400, f"run_id must match '{{case}}__{{label}}': got {run_id!r}")
    case_id, _, run_label = run_id.rpartition("__")
    return case_id, run_label
```

- `rpartition` (not `split`) handles cases where the label itself could contain `__` (doesn't today, but resilient).
- On-disk layout: `reports/phase5_fields/{case_id}/{timestamp}/...`. The `run_label` selects **which** timestamp → need a sidecar manifest (or we pick "latest timestamp for this run_label"). **Recommendation:** write a single `latest.json` symlink or a `runs/{run_label}.json` manifest in `reports/phase5_fields/{case_id}/` so the route can resolve `run_label → timestamp` deterministically. Example:
  ```
  reports/phase5_fields/lid_driven_cavity/
    runs/
      audit_real_run.json          ← {"timestamp": "20260421T063729Z"}
    20260421T063729Z/
      VTK/lid_driven_cavity_2000.vtk
      postProcessing/sample/2000/uCenterline_U_p.xy
      residuals.csv
      log.simpleFoam
  ```

**Call-out for planner:** the `FieldArtifactsResponse.timestamp` field in CONTEXT is the bridge — when the route reads the manifest, it returns the timestamp explicitly so callers don't need to re-resolve.

### 2.8 Test fixture pattern + `field_artifacts_manifest.yaml` sibling

**Existing pattern:** per-case fixtures sit at `ui/backend/tests/fixtures/runs/{case_id}/*.yaml`, one file per run (e.g. `audit_real_run_measurement.yaml`, `mesh_20_measurement.yaml`). Tests enumerate with `RUNS_DIR.glob("*/audit_real_run_measurement.yaml")` (test_phase5_byte_repro.py:60).

**Recommendation for Phase 7a:** add a sibling `field_artifacts_manifest.yaml` at `ui/backend/tests/fixtures/runs/lid_driven_cavity/field_artifacts_manifest.yaml` with the **expected filenames, kinds, and size bounds**, NOT exact bytes (OpenFOAM output has non-reproducible metadata — hostname, wall-clock; see DEC-V61-030 pattern of not byte-asserting):

```yaml
# Phase 7a expected-artifact manifest — AUTO-VERIFIED by
# ui/backend/tests/test_field_artifacts.py
run_label: audit_real_run
expected_artifacts:
  - filename: lid_driven_cavity_2000.vtk
    kind: vtk
    min_size_bytes: 500000        # ~0.5 MB floor for 129×129×1 binary
    max_size_bytes: 2500000       # ~2.5 MB ceiling
  - filename: uCenterline_U_p.xy
    kind: csv
    min_size_bytes: 500
  - filename: residuals.csv
    kind: residual_log
    min_size_bytes: 100
```

**Assertions (in a new `test_field_artifacts.py`):**
1. Directory `reports/phase5_fields/lid_driven_cavity/*/` exists (glob `*/` for timestamp).
2. For each `expected_artifacts` entry: file exists, size within bounds.
3. Backend route `GET /api/runs/lid_driven_cavity__audit_real_run/field-artifacts` returns HTTP 200, JSON contains ≥3 artifacts, each with non-empty 64-hex-char `sha256`.
4. Download route `GET .../field-artifacts/{filename}` returns HTTP 200 with `content-length` matching the file's `st_size`.

**Do NOT run the solver in the test.** Gate behind `os.getenv("EXECUTOR_MODE") == "foam_agent"` like `test_phase5_byte_repro.py` gates its re-run path. The default CI test uses a pre-staged fixture directory committed under `ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/{frozen_timestamp}/` — 3 small files, committed as test data. This preserves the 79/79 green guarantee without a solver dependency in CI.

## 3. Implementation Gotchas / Risks

### 3.1 test_phase5_byte_repro.py will NOT break — but watch key order

`_REQUIRED_TOP_KEYS` (test_phase5_byte_repro.py:30-37) uses **subset check** (`_REQUIRED_TOP_KEYS - set(doc.keys())`), not equality (line 81-82). Adding a new top-level key `field_artifacts` to the audit fixture is **safe**. However:

- The yaml dump in `_write_audit_fixture` (phase5_audit_run.py:179) uses `sort_keys=False` — the insertion order is the serialization order. The `_audit_fixture_doc` builder (lines 100-136) assembles the dict literal-style; inserting `field_artifacts` in the right position matters for byte-repro across commits. **Rule:** append `field_artifacts` **after** `decisions_trail` so existing fixture bytes shift only at the end.
- `test_audit_fixtures_nondeterministic_fields_are_isolated` (test_phase5_byte_repro.py:119-141) is a frozen set — if the new `field_artifacts` entries contain any timestamp or hash, add them to `allowed_nondeterministic` **and justify in a DEC** (the test literally says so at line 141). Recommendation: store timestamps as paths (`reports/phase5_fields/.../{ts}/...`) not as fields in the YAML, to keep the YAML deterministic. The fixture's `field_artifacts` block should reference the manifest by relative path, not duplicate its contents.

### 3.2 Docker `-allPatches` behavior when `empty` patch has zero faces

The LDC `frontAndBack` patch is `type empty`. Some v10 builds assert on empty-face iteration in foamToVTK. Mitigation: catch failure and fall back to `foamToVTK -latestTime -noZero` (no `-allPatches`) — internal mesh VTK is sufficient for Phase 7a's volume-contour needs; patches are only needed for Phase 7c heatmaps.

### 3.3 Docker container may not have foamToVTK in PATH at the bash level

`_docker_exec` already sources `/opt/openfoam10/etc/bashrc` (adapter:6659) — foamToVTK is in `$FOAM_UTILITIES/postProcessing/dataConversion/foamToVTK/` and added to PATH by the bashrc. **Verified pattern works for blockMesh, simpleFoam, postProcess** (adapter:538, 576, 590). Zero risk.

### 3.4 `writeInterval 500` for `sample` function object on 2000-iteration run

`writeControl timeStep; writeInterval 500` → captures iterations 500, 1000, 1500, 2000. Four snapshots. For an audit run this is fine (final iteration is what the comparator uses). For Phase 7b renders, four snapshots enable a mini convergence animation. **No change needed to CONTEXT.**

### 3.5 Race: driver timestamp vs executor artifact timestamp

The driver creates a timestamp string at the top of `run_one` (for `_write_raw_capture` filename). The executor runs for ~22s. If the executor generates its own timestamp, the two differ and the artifact-manifest → fixture linkage becomes fuzzy. **Mitigation (restated from §2.1):** pass the single timestamp from driver into executor via `task_spec.metadata` or as a new kwarg on `execute()`. Alternatively, the driver reads back the timestamp chosen by the executor from the directory name `reports/phase5_fields/{case}/{ts_from_exec}/` and writes IT into the audit fixture.

### 3.6 In-memory SHA256 cache leaks across uvicorn reload

`_sha_cache` dict grows unbounded in a long-lived dev server. Not a concern for MVP (< 100 MB at worst). Add an LRU eviction if any cache entry count exceeds 10000 — trivially revisitable.

### 3.7 Existing comparator depends on `postProcessing/sets/` path (not `postProcessing/sample/`)

`foam_agent_adapter.py:7257-7287` parses `postProcessing/sets/<time>/uCenterline_U.xy` from the LEGACY `sampleDict` route (adapter:1028). The new controlDict `sample` function object writes to `postProcessing/sample/<time>/uCenterline_U_p.xy` (note: different subdir name = function-object's dict key; different file suffix = all requested fields concatenated). **These are two independent artifacts.** Keep both:
- Existing `system/sampleDict` → `postProcessing/sets/` — reused by comparator, DO NOT touch.
- New in-controlDict `sample` function object → `postProcessing/sample/` — Phase 7a artifact.

This avoids any risk to the 11/17 PASS comparator result.

### 3.8 Path in `FoamAgentExecutor._work_dir` is `/tmp/cfd-harness-cases`

Field artifacts must live at the repo-relative `reports/phase5_fields/{case}/{ts}/`, not under `/tmp` (which is transient). The executor today has no concept of a repo-relative output path — fix by either (a) passing a second `artifact_output_dir` kwarg into `execute()`, or (b) computing `REPO_ROOT / "reports" / "phase5_fields"` inside `_capture_field_artifacts` as a constant (mirrors `scripts/phase5_audit_run.py::RAW_DIR` line 45). Recommendation: (b) — zero API change, one `pathlib.Path` at top of method.

## 4. Validation Architecture

Test framework already in place: pytest 7.4+, no conftest at `ui/backend/tests/`. Full suite command: `cd /Users/Zhuanz/Desktop/cfd-harness-unified && .venv/bin/pytest ui/backend/tests/ -v`. Quick subset: `.venv/bin/pytest ui/backend/tests/test_field_artifacts.py -x`.

### 4.1 Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 7.4+ (existing deps, no add needed) |
| Config file | `pyproject.toml` `[tool.pytest]` section (not inspected here — inherited from existing 79/79 green config) |
| Quick run | `.venv/bin/pytest ui/backend/tests/test_field_artifacts.py -x` |
| Full suite | `.venv/bin/pytest ui/backend/tests/ -v` (must stay 79 → 80+ green) |
| Solver-gated path | `EXECUTOR_MODE=foam_agent .venv/bin/python scripts/phase5_audit_run.py lid_driven_cavity` — integration, NOT in default pytest run |

### 4.2 Observable Signals → Test Map

| Signal | Behavior | Test Type | Automated Command | Fixture Needed? |
|--------|----------|-----------|-------------------|-----------------|
| S1 — artifact dir exists | `reports/phase5_fields/lid_driven_cavity/{YYYYMMDDTHHMMSSZ}/` exists after driver run | integration | `EXECUTOR_MODE=foam_agent .venv/bin/python scripts/phase5_audit_run.py lid_driven_cavity && ls -la reports/phase5_fields/lid_driven_cavity/*/` | No — live artifact |
| S2 — ≥ 3 artifacts present | VTK + CSV + residuals.csv | integration | same as S1 + `find reports/phase5_fields/lid_driven_cavity -type f \| wc -l` → ≥ 3 | No |
| S3 — artifact sizes reasonable | VTK 500kB-2.5MB, CSV > 500 B, residuals.csv > 100 B | unit (pytest) | `.venv/bin/pytest ui/backend/tests/test_field_artifacts.py::test_expected_artifact_sizes` | **YES** — Wave 0 committed fixture at `tests/fixtures/phase7a_sample_fields/` |
| S4 — JSON manifest 200 OK | `GET /api/runs/{id}/field-artifacts` HTTP 200, JSON schema matches `FieldArtifactsResponse` | unit (pytest + TestClient) | `.venv/bin/pytest ui/backend/tests/test_field_artifacts.py::test_get_manifest_200` | YES |
| S5 — ≥ 3 artifacts in JSON | Response `artifacts` array length ≥ 3 | unit | `.venv/bin/pytest ui/backend/tests/test_field_artifacts.py::test_manifest_three_artifacts` | YES |
| S6 — SHA256 valid hex | Each artifact's `sha256` is 64-char lowercase hex | unit | `.venv/bin/pytest ui/backend/tests/test_field_artifacts.py::test_sha256_format` | YES |
| S7 — File download 200 OK | `GET .../field-artifacts/{filename}` HTTP 200, content-length matches `st_size` | unit | `.venv/bin/pytest ui/backend/tests/test_field_artifacts.py::test_download_200_sizes` | YES |
| S8 — path traversal rejected | `GET .../field-artifacts/../../etc/passwd` returns 404 (not 200 or 500) | unit (security) | `.venv/bin/pytest ui/backend/tests/test_field_artifacts.py::test_reject_traversal` | No |
| S9 — byte-repro regression guard | `test_phase5_byte_repro.py` still passes with new `field_artifacts` top-level key in audit fixture | unit | `.venv/bin/pytest ui/backend/tests/test_phase5_byte_repro.py` | Regenerated audit fixture |
| S10 — comparator verdict unchanged | LDC still produces 11/17 PASS after solver edits | integration | `EXECUTOR_MODE=foam_agent .venv/bin/python scripts/phase5_audit_run.py lid_driven_cavity` + verify `audit_concerns[1].summary == "6 deviation(s) over tolerance"` | No |

### 4.3 Sampling Rate

- **Per task commit (adapter changes):** S3..S9 unit tests (< 2s).
- **Per wave merge:** full `.venv/bin/pytest ui/backend/tests/` (should be 80 → 85+ green after phase 7a).
- **Phase gate (pre-`/gsd-verify-work`):** full suite + S1, S2, S10 integration (gated by `EXECUTOR_MODE=foam_agent` — requires local Docker).

### 4.4 Wave 0 Gaps

- [ ] `ui/backend/tests/test_field_artifacts.py` — new test file covering S3-S8
- [ ] `ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/20260421T000000Z/` — committed sample VTK (~500 kB minimal stub), `uCenterline_U_p.xy`, `residuals.csv` for offline unit tests
- [ ] `ui/backend/tests/fixtures/runs/lid_driven_cavity/field_artifacts_manifest.yaml` — expected-artifacts manifest
- [ ] `ui/backend/schemas/validation.py` — add `FieldArtifact` + `FieldArtifactsResponse` Pydantic models
- [ ] `ui/backend/services/field_artifacts.py` — new service: `list_artifacts`, `resolve_artifact_path`, `parse_run_id`, `sha256_of`
- [ ] `ui/backend/routes/field_artifacts.py` — new route file
- [ ] `ui/backend/main.py` — register new router (one line: `app.include_router(field_artifacts.router, prefix="/api", tags=["field-artifacts"])`)
- [ ] `scripts/phase5_audit_run.py` — inject `field_artifacts` block into `_audit_fixture_doc` **after** `decisions_trail`
- [ ] `src/foam_agent_adapter.py` — new `_emit_phase7a_function_objects` + `_capture_field_artifacts` methods, call-site wiring in `execute()` post-solver

## 5. Security Domain

### 5.1 Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Phase 7a route is read-only dev API; auth deferred to Phase 7e (HMAC) |
| V3 Session Management | no | stateless |
| V4 Access Control | no | no multi-tenant split in MVP |
| V5 Input Validation | **yes** | `run_id` must match `^[a-z0-9_]+__[a-z0-9_]+$` regex before filesystem ops; `filename` must have no `..` or `/` segments — delegate to `pathlib.resolve().relative_to()` audit-package pattern (`audit_package.py:_resolve_bundle_file:290-297`) |
| V6 Cryptography | **yes** (SHA256 integrity) | `hashlib.sha256` — stdlib, never hand-roll |

### 5.2 Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal in `{filename}` | Tampering | `resolved.relative_to(_FIELDS_ROOT.resolve())` — fail closed |
| Path traversal via `{run_id}` (containing `../`) | Tampering | Regex-validate `run_id` before `rpartition("__")` |
| Serving arbitrary file via MIME confusion | Information Disclosure | Explicit `media_type` per extension (§2.4) |
| Docker command injection via case_id in `_docker_exec("foamToVTK -latestTime …", case_cont_dir, …)` | Tampering | `case_cont_dir` is internally generated (`f"/tmp/cfd-harness-cases/{case_id}"` with `case_id = f"ldc_{os.getpid()}_{int(time.time()*1000)}"` — adapter:478-480); no user input touches it |

## 6. Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Binary VTK output is ~1.3 MB for 129×129×1 LDC | §2.3 | Low — if wrong, disk usage doubles; 5 MB budget still holds |
| A2 | `-allPatches` is stable on v10 for `empty` patches with 0 faces | §2.3, §3.2 | Medium — mitigation documented (fallback without `-allPatches`) |
| A3 | `writeControl timeStep writeInterval 500` produces 4 snapshots for a 2000-iter simpleFoam run | §2.2, §3.4 | Low — even if 0 snapshots, final `VTK/` still has latest-time field |
| A4 | `residuals` function object writes `postProcessing/residuals/0/residuals.dat` in OF10 | §2.5 | Medium — if format differs, fall back to regex-parse `log.simpleFoam` (precedent at adapter:6801) |
| A5 | Pydantic v2 is already in project (for `BaseModel` + `Literal`) | §2.4 schema | Zero — verified in `ui/backend/schemas/validation.py:9-11` |
| A6 | Adding a `field_artifacts` top-level key to `audit_real_run_measurement.yaml` does not break `test_phase5_byte_repro.py` | §3.1 | Low — subset check confirmed at test_phase5_byte_repro.py:81 |
| A7 | The `run_id = "{case}__{label}"` convention is new in this project | §2.7 | Low — confirmed by grep; no caller depends on it today |

## 7. Open Questions (RESOLVED)

All 6 research questions were ratified by the user in auto mode and are encoded in CONTEXT.md `<decisions>` as ratifications R#1-R#7. The planner honored all 7 in `07a-01-PLAN.md` and `07a-02-PLAN.md`.

1. **StaticFiles vs FileResponse.** **RESOLVED: R#1 — FileResponse** + traversal-safe `_resolve_artifact_path` mirroring `ui/backend/routes/audit_package.py:284-342`. No `StaticFiles` mount in project.
2. **writeControl for `sample` function object.** **RESOLVED: R#2 — `writeControl timeStep; writeInterval 500`** (simpleFoam is steady, iteration-indexed; `runTime` is semantically wrong). Plan 01 Task 1 acceptance includes negative assertion `grep -n "runTime" functions{} block = 0`.
3. **Reuse `residuals` function object vs parsing `log.simpleFoam`?** **RESOLVED: R#3 — function object** writes `postProcessing/residuals/0/residuals.dat` (structured ASCII). Plan 01 Task 2 `_emit_residuals_csv` reads that structured file, not regex on log.
4. **Timestamp authority: driver or executor?** **RESOLVED: R#7 — driver is authoritative.** `scripts/phase5_audit_run.py` generates timestamp `YYYYMMDDTHHMMSSZ` and passes via `task_spec.metadata["phase7a_timestamp"]`; executor consumes read-only.
5. **Artifact ordering in response JSON.** **RESOLVED: R#6 — explicit kind order** `vtk < csv < residual_log` via `_KIND_ORDER = {"vtk": 0, "csv": 1, "residual_log": 2}` + stable `filename` tiebreak. Plan 02 Task 1.
6. **`run_label → timestamp` resolution.** **RESOLVED: R#7 — per-run manifest** `reports/phase5_fields/{case_id}/runs/{run_label}.json` written by driver at end of per-case loop; route reads manifest to find timestamp directory. Plan 01 Task 3 `_write_field_artifacts_run_manifest`.

**Cross-ref:** CONTEXT.md `<decisions>` section has ratifications R#1-R#7; `07a-01-PLAN.md` Task 1-3 and `07a-02-PLAN.md` Task 1 encode them in concrete `<action>` blocks.

## 8. References (exact file:line anchors)

### Primary (HIGH confidence — read in this session)
- `src/foam_agent_adapter.py:384-623` — FoamAgentExecutor class + `execute()` with teardown finally block at :618-623
- `src/foam_agent_adapter.py:595-597, 6729-6776` — `_copy_postprocess_fields` — exact template for Option B
- `src/foam_agent_adapter.py:643-1057` — `_generate_lid_driven_cavity` (simpleFoam + 129×129); controlDict at :716-768 (no functions block); sampleDict at :1010-1057
- `src/foam_agent_adapter.py:6522-6606` — `_render_block_mesh_dict` (`convertToMeters 0.1` → physical coord calc for §2.2)
- `src/foam_agent_adapter.py:6612-6708` — `_docker_exec`, `_make_tarball`
- `src/foam_agent_adapter.py:6710-6727` — `_copy_file_from_container` (reuse primitive)
- `src/foam_agent_adapter.py:5128-5136` — precedent of `functions{}` block in controlDict (DHC buoyantFoam)
- `src/foam_agent_adapter.py:6782-6825` — `_parse_solver_log` regex (fallback for §2.5)
- `scripts/phase5_audit_run.py:44-46,183-207` — RAW_DIR pattern + timestamp `%Y%m%dT%H%M%SZ`
- `scripts/phase5_audit_run.py:93-162,210-233` — `_audit_fixture_doc` + `run_one` — exact insertion point for `field_artifacts` key
- `ui/backend/routes/audit_package.py:270-342` — `FileResponse` + `_resolve_bundle_file` pattern (adopt for §2.4)
- `ui/backend/routes/run_monitor.py:1-41` — existing `/api/runs/{case_id}/*` URL convention (CONTEXT overloads with composite run_id)
- `ui/backend/services/validation_report.py:273-282` — `_load_run_measurement(case_id, run_id)` — separate args today
- `ui/backend/schemas/validation.py:1-199` — Pydantic models home (add `FieldArtifact`/`FieldArtifactsResponse` here)
- `ui/backend/main.py:80-88` — router registration block (one-line addition)
- `ui/backend/tests/test_phase5_byte_repro.py:30-141` — byte-repro test (subset check at :81, non-determinism set at :127-141)
- `ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml` — existing fixture format

### Secondary (MEDIUM confidence — web/official docs)
- [cpp.openfoam.org v10 foamToVTK source](https://cpp.openfoam.org/v10/foamToVTK_8C.html) — `-allPatches`, `-ascii`, `-fields` options `[CITED]`
- [cpp.openfoam.org v10 timeSelector](https://cpp.openfoam.org/v10/classFoam_1_1timeSelector.html) — `-latestTime`, `-noZero` inherited from timeSelector `[VERIFIED]`
- [cpp.openfoam.org v10 residuals function object](https://cpp.openfoam.org/v10/classFoam_1_1functionObjects_1_1residuals.html) — controlDict dict syntax `[CITED]`
- [doc.cfd.direct v8 graphs-monitoring](https://doc.cfd.direct/openfoam/user-guide-v8/graphs-monitoring) — `sets` function object structure `[CITED; v8 syntax close to v10]`

### Tertiary (LOW confidence — flagged for validation)
- A2 (`-allPatches` + empty-patch stability) — anecdotal from CFD forums; not verified against specific v10 build in our container

## 9. Metadata

**Confidence breakdown:**
- Current-state analysis: HIGH — all claims sourced from file reads in this session
- OpenFOAM function-object syntax: HIGH — three independent authoritative sources
- foamToVTK flags: HIGH — verified against OpenFOAM v10 API Guide
- StaticFiles-vs-FileResponse conflict: HIGH — grep confirmed no `StaticFiles` usage
- Byte-repro safety of adding fixture key: HIGH — test code inspected
- `-allPatches` empty-patch behavior: MEDIUM — documented mitigation, not live-tested

**Research date:** 2026-04-21
**Valid until:** 2026-05-21 (30 days for stable stack; Docker image / OF10 could change container behavior)
