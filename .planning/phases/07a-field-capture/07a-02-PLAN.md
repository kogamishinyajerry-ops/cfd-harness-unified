---
phase: 07a-field-capture
plan: 02
type: execute
wave: 2
depends_on: [07a-01]
files_modified:
  - ui/backend/schemas/validation.py
  - ui/backend/services/run_ids.py          # NEW
  - ui/backend/services/field_artifacts.py  # NEW
  - ui/backend/routes/field_artifacts.py    # NEW
  - ui/backend/main.py
  - ui/backend/tests/test_field_artifacts_route.py                         # NEW
  - ui/backend/tests/fixtures/runs/lid_driven_cavity/field_artifacts_manifest.yaml  # NEW
  - ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/20260421T000000Z/.gitkeep  # NEW (dir marker; files added by fixture_builder below)
autonomous: true   # NEW-file heavy, no src/ touch → Codex post-merge in Wave 3
requirements: [DEC-V61-031]

must_haves:
  truths:
    - "GET /api/runs/lid_driven_cavity__audit_real_run/field-artifacts returns HTTP 200 with JSON {run_id, case_id, timestamp, artifacts: [...]} where artifacts has ≥3 items"
    - "Each artifact item has {kind in ['vtk','csv','residual_log'], filename, url, sha256 (64 hex chars), size_bytes (>0)}"
    - "Artifacts are sorted by (kind_order, filename) with kind_order: vtk<csv<residual_log (user ratification #6)"
    - "GET /api/runs/{run_id}/field-artifacts/{filename} returns HTTP 200 with the file bytes and correct media_type by extension"
    - "Path traversal attempts (../../etc/passwd as filename or malformed run_id) return 404, not 200 or 500"
    - "79/79 existing pytest remains green after new tests + schema additions"
  artifacts:
    - path: "ui/backend/schemas/validation.py"
      provides: "FieldArtifact + FieldArtifactsResponse Pydantic v2 models"
      contains: "class FieldArtifact"
    - path: "ui/backend/services/run_ids.py"
      provides: "parse_run_id helper (user ratification #5)"
      contains: "def parse_run_id"
    - path: "ui/backend/services/field_artifacts.py"
      provides: "list_artifacts, resolve_artifact_path, sha256_of with (path, mtime, size) caching"
      contains: "def list_artifacts"
    - path: "ui/backend/routes/field_artifacts.py"
      provides: "Two FastAPI routes (JSON manifest + FileResponse download)"
      contains: "def get_field_artifacts"
    - path: "ui/backend/main.py"
      provides: "Router registration line"
      contains: "field_artifacts.router"
    - path: "ui/backend/tests/test_field_artifacts_route.py"
      provides: "7 unit tests covering manifest JSON, download, SHA256, traversal, ordering"
      contains: "def test_get_manifest_200"
  key_links:
    - from: "routes/field_artifacts.py::get_field_artifacts"
      to: "services/field_artifacts.py::list_artifacts"
      via: "direct import"
      pattern: "from ui.backend.services.field_artifacts import list_artifacts"
    - from: "routes/field_artifacts.py::download_field_artifact"
      to: "services/field_artifacts.py::resolve_artifact_path"
      via: "traversal-safe path resolution (precedent: audit_package.py:284-342)"
      pattern: "resolved.relative_to"
    - from: "services/field_artifacts.py::list_artifacts"
      to: "reports/phase5_fields/{case_id}/runs/{run_label}.json"
      via: "manifest read (written by Wave 1 Task 3)"
      pattern: "runs/.*\\.json"
    - from: "main.py"
      to: "routes/field_artifacts.py"
      via: "app.include_router"
      pattern: "field_artifacts\\.router"
---

<objective>
Surface the artifacts captured in Wave 1 through a read-only FastAPI route following the existing `FileResponse + _resolve_*_file` precedent (user ratification #1, not StaticFiles). The route resolves `run_id = "{case}__{run_label}"` via the per-run manifest written by Wave 1 Task 3, lists artifacts as JSON with SHA256 + size, and serves individual files.

Purpose: Wave 3 runs an end-to-end integration test (`scripts/phase5_audit_run.py lid_driven_cavity` → `GET /api/runs/lid_driven_cavity__audit_real_run/field-artifacts`). Without the route, the phase goal is not verifiable.

Output:
- Pydantic models: `FieldArtifact` + `FieldArtifactsResponse` in `ui/backend/schemas/validation.py`
- Helper: `ui/backend/services/run_ids.py::parse_run_id(run_id) -> (case_id, run_label)`
- Service: `ui/backend/services/field_artifacts.py` with `list_artifacts`, `resolve_artifact_path`, `sha256_of`
- Route file: `ui/backend/routes/field_artifacts.py` with `GET /runs/{run_id}/field-artifacts` + `GET /runs/{run_id}/field-artifacts/{filename}`
- Router registration in `ui/backend/main.py`
- Test suite `ui/backend/tests/test_field_artifacts_route.py` with ≥7 tests covering S3-S8 from 07a-RESEARCH.md §4.2
- Committed sample-artifacts fixture under `ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/20260421T000000Z/` so tests run offline (no solver needed)
- Expected-artifact manifest `ui/backend/tests/fixtures/runs/lid_driven_cavity/field_artifacts_manifest.yaml`
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/07a-field-capture/07a-CONTEXT.md
@.planning/phases/07a-field-capture/07a-RESEARCH.md
@ui/backend/routes/audit_package.py
@ui/backend/routes/run_monitor.py
@ui/backend/schemas/validation.py
@ui/backend/main.py

<interfaces>
<!-- Precedents the executor MUST mirror. -->

From ui/backend/routes/audit_package.py:284-342 (FileResponse + path-resolver precedent):
```python
_BUNDLE_ID_RE = re.compile(r"^[0-9a-f]{32}$")

def _resolve_bundle_file(bundle_id: str, filename: str) -> Path:
    if not _BUNDLE_ID_RE.match(bundle_id):
        raise HTTPException(status_code=404, detail="bundle not found")
    candidate = _STAGING_ROOT / bundle_id / filename
    try:
        resolved = candidate.resolve()
        resolved.relative_to(_STAGING_ROOT.resolve())
    except (ValueError, OSError):
        raise HTTPException(status_code=404, detail="bundle not found")
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="bundle not found")
    return resolved

@router.get("/audit-packages/{bundle_id}/bundle.zip")
def download_zip(bundle_id: str) -> FileResponse:
    return FileResponse(
        _resolve_bundle_file(bundle_id, "bundle.zip"),
        media_type="application/zip",
        filename=f"cfd-audit-{bundle_id[:8]}.zip",
    )
```

From ui/backend/schemas/validation.py:1-50 (existing Pydantic v2 patterns):
```python
from typing import Literal
from pydantic import BaseModel, Field
# Models are Pydantic v2 (verified via existing usage).
# ContractStatus / RunCategory are module-level Literal aliases.
# Any new model uses `BaseModel` directly; Field(...) for constraints.
```

From ui/backend/main.py:80-88 (router registration block):
```python
app.include_router(health.router,        prefix="/api", tags=["health"])
# ... other routers ...
app.include_router(audit_package.router, prefix="/api", tags=["audit-package"])
app.include_router(case_export.router,   prefix="/api", tags=["case-export"])
# → add:  app.include_router(field_artifacts.router, prefix="/api", tags=["field-artifacts"])
```

Expected on-disk layout written by Wave 1 Task 3:
```
reports/phase5_fields/
  lid_driven_cavity/
    runs/
      audit_real_run.json          # {"run_label":"audit_real_run","timestamp":"20260421T063729Z","case_id":"lid_driven_cavity","artifact_dir_rel":"reports/phase5_fields/lid_driven_cavity/20260421T063729Z"}
    20260421T063729Z/
      VTK/lid_driven_cavity_2000.vtk
      postProcessing/sample/2000/uCenterline_U_p.xy
      postProcessing/residuals/0/residuals.dat
      residuals.csv
      log.simpleFoam
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add FieldArtifact + FieldArtifactsResponse Pydantic models; add parse_run_id helper; add services/field_artifacts.py</name>
  <files>
    ui/backend/schemas/validation.py
    ui/backend/services/run_ids.py
    ui/backend/services/field_artifacts.py
    ui/backend/tests/fixtures/runs/lid_driven_cavity/field_artifacts_manifest.yaml
    ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/20260421T000000Z/VTK/lid_driven_cavity_2000.vtk
    ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/20260421T000000Z/uCenterline_U_p.xy
    ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/20260421T000000Z/residuals.csv
    ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/runs/audit_real_run.json
  </files>
  <read_first>
    - ui/backend/schemas/validation.py (existing Pydantic v2 idiom; see lines 1-50 header)
    - ui/backend/routes/audit_package.py (lines 284-342 for _resolve_bundle_file precedent — we copy the try/resolve/relative_to pattern)
    - .planning/phases/07a-field-capture/07a-RESEARCH.md (§2.4 route skeleton, §2.6 SHA256 cache, §2.7 parse_run_id, §2.8 test fixture)
  </read_first>
  <behavior>
    - Test 1 (schema): `FieldArtifact(kind="vtk", filename="x.vtk", url="/api/runs/a__b/field-artifacts/x.vtk", sha256="a"*64, size_bytes=1).model_dump()` returns a dict with all 5 keys.
    - Test 2 (schema reject): `FieldArtifact(kind="invalid", ...)` raises `ValidationError` (Literal constraint).
    - Test 3 (parse_run_id): `parse_run_id("lid_driven_cavity__audit_real_run") == ("lid_driven_cavity", "audit_real_run")`.
    - Test 4 (parse_run_id malformed): `parse_run_id("no_separator")` raises `HTTPException(status_code=400)`.
    - Test 5 (parse_run_id multi-__ label — rpartition): `parse_run_id("case_a__label__with__extra") == ("case_a__label__with", "extra")` (rpartition on last `__`).
    - Test 6 (sha256_of): computing on a committed fixture returns a 64-char lowercase hex string matching `hashlib.sha256(file_bytes).hexdigest()`.
    - Test 7 (sha256 cache hit): second `sha256_of(path)` call on same file does NOT re-read (verify via patching `open` or tracking call count).
    - Test 8 (list_artifacts): given the committed sample fixture, returns `FieldArtifactsResponse` with `len(artifacts) >= 3`, sorted by `(kind_order, filename)` with `vtk < csv < residual_log`.
    - Test 9 (list_artifacts missing manifest): nonexistent run_id returns `None` (route will 404).
    - Test 10 (resolve_artifact_path traversal): filename="../../etc/passwd" raises HTTPException 404.
  </behavior>
  <action>
**Step 1 — Append to `ui/backend/schemas/validation.py`** (at the end of the file, after existing models):

```python
# ---------------------------------------------------------------------------
# Phase 7a — Field Artifacts
# ---------------------------------------------------------------------------

FieldArtifactKind = Literal["vtk", "csv", "residual_log"]
"""Kind of artifact surfaced by GET /api/runs/{run_id}/field-artifacts.

- vtk: OpenFOAM foamToVTK output (binary, ~1 MB/case for 129×129 LDC)
- csv: sampled profile data (e.g. uCenterline_U_p.xy from OpenFOAM `sets` function object)
- residual_log: residuals.csv (derived from OpenFOAM `residuals` function object .dat output) or raw log.<solver>

Phase 7a captures these per audit_real_run; Phase 7b renders them to PNG/HTML.
"""


class FieldArtifact(BaseModel):
    """A single field artifact captured by Phase 7a.

    Paths are served via GET /api/runs/{run_id}/field-artifacts/{filename}
    (separate download endpoint; this struct carries metadata).
    """

    kind: FieldArtifactKind
    filename: str = Field(..., description="Basename only; no directory segments.")
    url: str = Field(..., description="Download URL under /api/runs/{run_id}/field-artifacts/{filename}")
    sha256: str = Field(..., pattern=r"^[0-9a-f]{64}$", description="Lowercase hex SHA256 of file bytes.")
    size_bytes: int = Field(..., ge=0)


class FieldArtifactsResponse(BaseModel):
    """Response for GET /api/runs/{run_id}/field-artifacts."""

    run_id: str
    case_id: str
    run_label: str
    timestamp: str = Field(..., description="YYYYMMDDTHHMMSSZ UTC — resolved via per-run manifest.")
    artifacts: list[FieldArtifact]
```

**Step 2 — Create `ui/backend/services/run_ids.py`** (new file):

```python
"""Phase 7a — run_id parsing helper.

Per user ratification #5 (2026-04-21): run_id = "{case_id}__{run_label}".
We use rpartition on the last "__" so case_ids with internal underscores
(e.g. 'lid_driven_cavity') still parse correctly (07a-RESEARCH.md §2.7).
"""
from __future__ import annotations

from fastapi import HTTPException


def parse_run_id(run_id: str) -> tuple[str, str]:
    """Parse 'lid_driven_cavity__audit_real_run' → ('lid_driven_cavity', 'audit_real_run').

    Uses rpartition on '__' so the label is the LAST token; case_id keeps any
    internal underscores. Labels today are simple identifiers without '__';
    rpartition is resilient if that changes.

    Raises HTTPException(400) on malformed input.
    """
    if "__" not in run_id:
        raise HTTPException(
            status_code=400,
            detail=f"run_id must match '{{case}}__{{label}}': got {run_id!r}",
        )
    case_id, _, run_label = run_id.rpartition("__")
    if not case_id or not run_label:
        raise HTTPException(
            status_code=400,
            detail=f"run_id has empty case_id or label: {run_id!r}",
        )
    return case_id, run_label
```

**Step 3 — Create `ui/backend/services/field_artifacts.py`** (new file):

```python
"""Phase 7a — field artifact service.

Reads the per-run manifest at reports/phase5_fields/{case_id}/runs/{run_label}.json
(written by scripts/phase5_audit_run.py::_write_field_artifacts_run_manifest),
enumerates files in the pointed-to timestamp directory, and serves them via
the FastAPI route in ui/backend/routes/field_artifacts.py.

File-serve pattern mirrors ui/backend/routes/audit_package.py:284-342
(FileResponse + traversal-safe _resolve_bundle_file) per user ratification #1.

Artifact ordering: sort by (kind_order, filename) with kind_order
vtk=0 < csv=1 < residual_log=2 per user ratification #6.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional

from fastapi import HTTPException

from ui.backend.schemas.validation import (
    FieldArtifact,
    FieldArtifactsResponse,
    FieldArtifactKind,
)
from ui.backend.services.run_ids import parse_run_id

# Repo root: 3 levels up from this file (ui/backend/services/field_artifacts.py)
_REPO_ROOT = Path(__file__).resolve().parents[3]
_FIELDS_ROOT = _REPO_ROOT / "reports" / "phase5_fields"

# Test override hook — see test_field_artifacts_route.py::_set_fields_root.
def _current_fields_root() -> Path:
    return _FIELDS_ROOT_OVERRIDE or _FIELDS_ROOT


_FIELDS_ROOT_OVERRIDE: Optional[Path] = None


def set_fields_root_for_testing(path: Optional[Path]) -> None:
    """Override the reports/phase5_fields/ root (test-only hook)."""
    global _FIELDS_ROOT_OVERRIDE
    _FIELDS_ROOT_OVERRIDE = path
    # Invalidate sha cache when root changes.
    _sha_cache.clear()


_KIND_ORDER: dict[str, int] = {"vtk": 0, "csv": 1, "residual_log": 2}

# SHA256 cache keyed on (abs_path, st_mtime, st_size) per 07a-RESEARCH.md §2.6.
_sha_cache: dict[tuple[str, float, int], str] = {}


def sha256_of(path: Path) -> str:
    """Compute (or return cached) SHA256 hex digest for `path`.

    Cache key: (absolute_path, st_mtime, st_size). Mtime+size collision would
    return a stale hash — MVP-accepted risk per 07a-RESEARCH.md §2.6.
    """
    st = path.stat()
    key = (str(path.resolve()), st.st_mtime, st.st_size)
    cached = _sha_cache.get(key)
    if cached is not None:
        return cached
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    digest = h.hexdigest()
    _sha_cache[key] = digest
    return digest


def _classify(filename: str) -> FieldArtifactKind | None:
    """Map a filename suffix to its kind. Returns None for files we don't surface."""
    low = filename.lower()
    if low.endswith(".vtk") or low.endswith(".vtu") or low.endswith(".vtp"):
        return "vtk"
    if low.endswith(".csv") or low.endswith(".xy") or low.endswith(".dat"):
        # residuals.csv is a residual_log by convention.
        if low == "residuals.csv" or "residual" in low:
            return "residual_log"
        return "csv"
    if low.startswith("log.") or low.endswith(".log"):
        return "residual_log"
    return None


def _read_run_manifest(case_id: str, run_label: str) -> Optional[dict]:
    root = _current_fields_root()
    manifest_path = root / case_id / "runs" / f"{run_label}.json"
    if not manifest_path.is_file():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def list_artifacts(run_id: str) -> Optional[FieldArtifactsResponse]:
    """Build the JSON manifest for a run_id. Returns None if no data exists."""
    case_id, run_label = parse_run_id(run_id)
    manifest = _read_run_manifest(case_id, run_label)
    if manifest is None:
        return None
    timestamp = manifest.get("timestamp", "")
    if not timestamp:
        return None
    root = _current_fields_root()
    artifact_dir = root / case_id / timestamp
    if not artifact_dir.is_dir():
        return None

    items: list[FieldArtifact] = []
    # Walk the whole tree — kind-classify leaves; skip directories.
    for p in artifact_dir.rglob("*"):
        if not p.is_file():
            continue
        kind = _classify(p.name)
        if kind is None:
            continue
        # Use basename only in the URL (traversal via URL blocked by route).
        items.append(
            FieldArtifact(
                kind=kind,
                filename=p.name,
                url=f"/api/runs/{run_id}/field-artifacts/{p.name}",
                sha256=sha256_of(p),
                size_bytes=p.stat().st_size,
            )
        )
    items.sort(key=lambda a: (_KIND_ORDER.get(a.kind, 99), a.filename))

    return FieldArtifactsResponse(
        run_id=run_id,
        case_id=case_id,
        run_label=run_label,
        timestamp=timestamp,
        artifacts=items,
    )


def resolve_artifact_path(run_id: str, filename: str) -> Path:
    """Return the on-disk path for {run_id}/{filename}, or raise HTTPException 404.

    Traversal defense: reject any filename with path separators or '..';
    additionally verify `resolved.relative_to(artifact_dir.resolve())`.
    """
    # Reject anything with path structure.
    if "/" in filename or "\\" in filename or ".." in filename.split("/"):
        raise HTTPException(status_code=404, detail="artifact not found")
    if filename in ("", ".", ".."):
        raise HTTPException(status_code=404, detail="artifact not found")

    case_id, run_label = parse_run_id(run_id)
    manifest = _read_run_manifest(case_id, run_label)
    if manifest is None:
        raise HTTPException(status_code=404, detail="artifact not found")
    timestamp = manifest.get("timestamp", "")
    if not timestamp:
        raise HTTPException(status_code=404, detail="artifact not found")

    root = _current_fields_root()
    artifact_dir = root / case_id / timestamp
    if not artifact_dir.is_dir():
        raise HTTPException(status_code=404, detail="artifact not found")

    # We serve basenames; files may live in subdirs (VTK/x.vtk). Walk and match.
    # This mirrors audit_package.py's traversal defense.
    for p in artifact_dir.rglob(filename):
        try:
            resolved = p.resolve()
            resolved.relative_to(artifact_dir.resolve())
        except (ValueError, OSError):
            continue
        if resolved.is_file() and resolved.name == filename:
            return resolved
    raise HTTPException(status_code=404, detail="artifact not found")
```

**Step 4 — Create committed sample fixture** at `ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/`:

Tests run offline without the solver (07a-RESEARCH.md §2.8 + §4.2 S3). Create these files as text/binary stubs (small, deterministic, committed):

`ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/runs/audit_real_run.json`:
```json
{
  "run_label": "audit_real_run",
  "timestamp": "20260421T000000Z",
  "case_id": "lid_driven_cavity",
  "artifact_dir_rel": "ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/20260421T000000Z"
}
```

`ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/20260421T000000Z/VTK/lid_driven_cavity_2000.vtk`:
Write a minimal but plausible text VTK legacy header + one cell; total file ≥ 600 bytes. Use Python to generate:
```python
from pathlib import Path
p = Path("ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/20260421T000000Z/VTK/lid_driven_cavity_2000.vtk")
p.parent.mkdir(parents=True, exist_ok=True)
header = (
    "# vtk DataFile Version 2.0\n"
    "Phase7a LDC stub fixture — DO NOT USE FOR SCIENCE\n"
    "ASCII\n"
    "DATASET UNSTRUCTURED_GRID\n"
    "POINTS 8 float\n"
    "0 0 0\n1 0 0\n0 1 0\n1 1 0\n0 0 1\n1 0 1\n0 1 1\n1 1 1\n"
    "CELLS 1 9\n8 0 1 3 2 4 5 7 6\n"
    "CELL_TYPES 1\n12\n"
    "POINT_DATA 8\nSCALARS U float 3\nLOOKUP_TABLE default\n"
    "0 0 0\n1 0 0\n0 0 0\n1 0 0\n0 0 0\n1 0 0\n0 0 0\n1 0 0\n"
    "SCALARS p float 1\nLOOKUP_TABLE default\n"
    "0\n0\n0\n0\n0\n0\n0\n0\n"
)
# Pad to ≥ 600 bytes so the test_expected_artifact_sizes assertion passes.
pad = "# padding: " + ("x" * (max(0, 600 - len(header)))) + "\n"
p.write_text(header + pad, encoding="utf-8")
```

`ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/20260421T000000Z/uCenterline_U_p.xy` (minimum 500 bytes):
```
# raw-format sample output — Phase7a LDC stub fixture
# Columns: y Ux Uy Uz p
0.0000   0.0000   0.0000   0.0000   0.0000
0.0078  -0.0372  -0.0020   0.0000   0.0001
0.0156  -0.0420  -0.0010   0.0000   0.0002
0.0234  -0.0320   0.0010   0.0000   0.0003
0.0313  -0.0180   0.0030   0.0000   0.0005
0.0391   0.0000   0.0050   0.0000   0.0006
0.0469   0.0210   0.0070   0.0000   0.0007
0.0547   0.0470   0.0080   0.0000   0.0008
0.0625   0.0830   0.0090   0.0000   0.0009
0.0703   0.1260   0.0080   0.0000   0.0010
0.0781   0.1740   0.0050   0.0000   0.0011
0.0859   0.2290   0.0000   0.0000   0.0011
0.0938   0.3050   -0.0090   0.0000   0.0010
0.1000   1.0000   0.0000   0.0000   0.0000
```
(Use a real tab/space mix; ensure total bytes ≥ 500.)

`ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/20260421T000000Z/residuals.csv` (minimum 100 bytes):
```
#,Time,U_x,U_y,U_z,p
1,1,0.123,0.045,0.000,0.670
2,2,0.089,0.032,0.000,0.521
3,3,0.054,0.022,0.000,0.389
4,4,0.031,0.014,0.000,0.241
5,5,0.014,0.008,0.000,0.132
```

**Step 5 — Create the expected-artifacts manifest** at `ui/backend/tests/fixtures/runs/lid_driven_cavity/field_artifacts_manifest.yaml`:
```yaml
# Phase 7a expected-artifact manifest — AUTO-VERIFIED by
# ui/backend/tests/test_field_artifacts_route.py
run_label: audit_real_run
expected_artifacts:
  - filename: lid_driven_cavity_2000.vtk
    kind: vtk
    min_size_bytes: 500
    max_size_bytes: 2500000
  - filename: uCenterline_U_p.xy
    kind: csv
    min_size_bytes: 500
  - filename: residuals.csv
    kind: residual_log
    min_size_bytes: 100
```
  </action>
  <verify>
    <automated>.venv/bin/python -c "
import pathlib, json
from ui.backend.schemas.validation import FieldArtifact, FieldArtifactsResponse, FieldArtifactKind
from ui.backend.services.run_ids import parse_run_id
from ui.backend.services.field_artifacts import sha256_of, list_artifacts, resolve_artifact_path, set_fields_root_for_testing
# Schema roundtrip
fa = FieldArtifact(kind='vtk', filename='x.vtk', url='/api/runs/a__b/field-artifacts/x.vtk', sha256='a'*64, size_bytes=1)
assert fa.model_dump()['kind'] == 'vtk'
# parse_run_id
assert parse_run_id('lid_driven_cavity__audit_real_run') == ('lid_driven_cavity', 'audit_real_run')
# sha256 on fixture
p = pathlib.Path('ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/20260421T000000Z/residuals.csv')
h = sha256_of(p)
assert len(h) == 64
# list_artifacts via fixture root override
set_fields_root_for_testing(pathlib.Path('ui/backend/tests/fixtures/phase7a_sample_fields'))
resp = list_artifacts('lid_driven_cavity__audit_real_run')
assert resp is not None
assert len(resp.artifacts) >= 3
# Ordering: vtk first, then csv, then residual_log
kinds = [a.kind for a in resp.artifacts]
assert kinds == sorted(kinds, key=lambda k: {'vtk':0,'csv':1,'residual_log':2}[k]), kinds
set_fields_root_for_testing(None)
print('OK')
"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "class FieldArtifact" ui/backend/schemas/validation.py` returns `1`
    - `grep -c "class FieldArtifactsResponse" ui/backend/schemas/validation.py` returns `1`
    - `grep -c "FieldArtifactKind" ui/backend/schemas/validation.py` returns ≥2 (alias + usage)
    - `ui/backend/services/run_ids.py` exists, `grep -c "def parse_run_id" ui/backend/services/run_ids.py` returns `1`
    - `ui/backend/services/field_artifacts.py` exists, contains `def list_artifacts`, `def resolve_artifact_path`, `def sha256_of`, `def set_fields_root_for_testing`
    - `grep -n "_sha_cache" ui/backend/services/field_artifacts.py` returns ≥2 matches (definition + lookup)
    - `grep -n "_KIND_ORDER" ui/backend/services/field_artifacts.py` confirms the order `vtk=0, csv=1, residual_log=2` (user ratification #6)
    - `ls ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/20260421T000000Z/VTK/lid_driven_cavity_2000.vtk` exits 0 and file is ≥ 500 bytes
    - `ls ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/20260421T000000Z/uCenterline_U_p.xy` exits 0 and file is ≥ 500 bytes
    - `ls ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/20260421T000000Z/residuals.csv` exits 0 and file is ≥ 100 bytes
    - `cat ui/backend/tests/fixtures/phase7a_sample_fields/lid_driven_cavity/runs/audit_real_run.json | python -c "import sys,json; d=json.load(sys.stdin); assert d['timestamp']=='20260421T000000Z'; assert d['case_id']=='lid_driven_cavity'"` exits 0
    - `cat ui/backend/tests/fixtures/runs/lid_driven_cavity/field_artifacts_manifest.yaml` shows `run_label: audit_real_run` and 3 expected_artifacts entries
    - The inline Python verification block above exits 0 (importable + all assertions pass)
  </acceptance_criteria>
  <done>
Pydantic models exist on `ui/backend/schemas/validation.py`. Helper `parse_run_id` exists on `ui/backend/services/run_ids.py`. Service module `ui/backend/services/field_artifacts.py` implements `list_artifacts`, `resolve_artifact_path`, `sha256_of` with (path, mtime, size) caching and a test-only `set_fields_root_for_testing` override. Committed sample fixture + expected-manifest YAML let tests run offline. Artifact sort order is `vtk < csv < residual_log` per user ratification #6.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add routes/field_artifacts.py + register router in main.py + full test suite</name>
  <files>
    ui/backend/routes/field_artifacts.py
    ui/backend/main.py
    ui/backend/tests/test_field_artifacts_route.py
  </files>
  <read_first>
    - ui/backend/routes/audit_package.py (lines 280-342 — FileResponse + _resolve_bundle_file pattern; we mirror EXACTLY)
    - ui/backend/main.py (lines 80-88 — router registration block, add one line)
    - ui/backend/services/field_artifacts.py (written in Task 1 — we import list_artifacts + resolve_artifact_path + set_fields_root_for_testing)
    - ui/backend/schemas/validation.py (FieldArtifactsResponse — route's response_model)
    - ui/backend/tests/test_phase5_byte_repro.py (existing test style — TestClient-free where possible; uses fixtures/runs/ glob patterns)
  </read_first>
  <behavior>
    - Test 1 (manifest 200): `GET /api/runs/lid_driven_cavity__audit_real_run/field-artifacts` returns HTTP 200 with JSON matching `FieldArtifactsResponse` schema (with pointer set to the committed fixture root via `set_fields_root_for_testing`).
    - Test 2 (manifest 404 bad run_id shape): `GET /api/runs/no_separator/field-artifacts` returns HTTP 400 (from parse_run_id) OR 404 (from route-level catch).
    - Test 3 (manifest 404 missing run): `GET /api/runs/nonexistent_case__no_run/field-artifacts` returns HTTP 404.
    - Test 4 (manifest ≥3 artifacts + ordering): response `artifacts` length ≥ 3, ordered by (kind_order, filename) with vtk first.
    - Test 5 (SHA256 valid hex): every artifact's `sha256` is exactly 64 lowercase hex chars.
    - Test 6 (download 200): `GET /api/runs/{id}/field-artifacts/residuals.csv` returns HTTP 200, content-length matches file st_size.
    - Test 7 (download 404 traversal): `GET /api/runs/{id}/field-artifacts/..%2F..%2Fetc%2Fpasswd` returns 404 (not 200, not 500).
    - Test 8 (download 404 missing): `GET /api/runs/{id}/field-artifacts/does_not_exist.csv` returns 404.
    - Test 9 (manifest size bounds): each artifact in response has `size_bytes > 0`.
  </behavior>
  <action>
**Step 1 — Create `ui/backend/routes/field_artifacts.py`**:

```python
"""Phase 7a — field artifacts route.

GET /api/runs/{run_id}/field-artifacts              → JSON manifest
GET /api/runs/{run_id}/field-artifacts/{filename}   → FileResponse

Pattern mirrors ui/backend/routes/audit_package.py:284-342 (FileResponse +
path-resolver) per user ratification #1. No StaticFiles.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ui.backend.schemas.validation import FieldArtifactsResponse
from ui.backend.services.field_artifacts import (
    list_artifacts,
    resolve_artifact_path,
)

router = APIRouter()


# MIME map — explicit per user ratification #1 rationale (no StaticFiles guessing).
_MEDIA_TYPES: dict[str, str] = {
    ".vtk": "application/octet-stream",
    ".vtu": "application/octet-stream",
    ".vtp": "application/octet-stream",
    ".csv": "text/csv",
    ".xy":  "text/plain; charset=utf-8",
    ".dat": "text/plain; charset=utf-8",
    ".log": "text/plain; charset=utf-8",
}


def _media_type_for(path: Path) -> str:
    return _MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream")


@router.get(
    "/runs/{run_id}/field-artifacts",
    response_model=FieldArtifactsResponse,
    tags=["field-artifacts"],
)
def get_field_artifacts(run_id: str) -> FieldArtifactsResponse:
    """List field artifacts for a given run_id = '{case}__{run_label}'."""
    resp = list_artifacts(run_id)
    if resp is None:
        raise HTTPException(
            status_code=404,
            detail=f"no field artifacts for run_id={run_id!r}",
        )
    return resp


@router.get(
    "/runs/{run_id}/field-artifacts/{filename}",
    tags=["field-artifacts"],
)
def download_field_artifact(run_id: str, filename: str) -> FileResponse:
    """Serve a single field artifact file. Traversal-safe."""
    path = resolve_artifact_path(run_id, filename)  # raises HTTPException(404)
    return FileResponse(
        path,
        media_type=_media_type_for(path),
        filename=path.name,
    )
```

**Step 2 — Register router in `ui/backend/main.py`**. Locate the block at lines 80-88 and add a new line AFTER the `case_export` registration (line 88):

```python
app.include_router(case_export.router,   prefix="/api", tags=["case-export"])
from ui.backend.routes import field_artifacts as _field_artifacts  # noqa: E402
app.include_router(_field_artifacts.router, prefix="/api", tags=["field-artifacts"])
```

Alternative (cleaner): add `field_artifacts` to the existing imports block at the top of `main.py` alongside the other route imports, then one registration line. Use whichever matches the existing style (grep the file to check — if routes are pre-imported at top, add `from ui.backend.routes import field_artifacts` there; if routes are imported inline, use the inline form).

**Step 3 — Create `ui/backend/tests/test_field_artifacts_route.py`**:

```python
"""Phase 7a — field artifacts route tests.

Runs OFFLINE against the committed fixture at
ui/backend/tests/fixtures/phase7a_sample_fields/ via
set_fields_root_for_testing. Must NOT call the solver.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ui.backend.main import app
from ui.backend.services.field_artifacts import set_fields_root_for_testing

_FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "phase7a_sample_fields"
_RUN_ID = "lid_driven_cavity__audit_real_run"


@pytest.fixture(autouse=True)
def _point_fields_root_at_fixture():
    set_fields_root_for_testing(_FIXTURE_ROOT)
    yield
    set_fields_root_for_testing(None)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ---------- Manifest endpoint ----------

def test_get_manifest_200(client: TestClient) -> None:
    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["run_id"] == _RUN_ID
    assert body["case_id"] == "lid_driven_cavity"
    assert body["run_label"] == "audit_real_run"
    assert body["timestamp"] == "20260421T000000Z"


def test_manifest_three_artifacts(client: TestClient) -> None:
    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts")
    assert r.status_code == 200
    artifacts = r.json()["artifacts"]
    assert len(artifacts) >= 3, artifacts
    # sum of kinds must include vtk + csv + residual_log
    kinds = {a["kind"] for a in artifacts}
    assert {"vtk", "csv", "residual_log"}.issubset(kinds), kinds


def test_manifest_ordering(client: TestClient) -> None:
    """User ratification #6: sort by (kind_order, filename), vtk < csv < residual_log."""
    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts")
    assert r.status_code == 200
    artifacts = r.json()["artifacts"]
    order = {"vtk": 0, "csv": 1, "residual_log": 2}
    keys = [(order[a["kind"]], a["filename"]) for a in artifacts]
    assert keys == sorted(keys), keys


_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def test_sha256_format(client: TestClient) -> None:
    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts")
    artifacts = r.json()["artifacts"]
    for a in artifacts:
        assert _HEX64.match(a["sha256"]), a


def test_manifest_sizes_positive(client: TestClient) -> None:
    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts")
    artifacts = r.json()["artifacts"]
    for a in artifacts:
        assert a["size_bytes"] > 0, a


def test_manifest_404_missing_run(client: TestClient) -> None:
    r = client.get("/api/runs/nonexistent_case__no_run/field-artifacts")
    assert r.status_code == 404, r.text


def test_manifest_400_or_404_malformed_run_id(client: TestClient) -> None:
    r = client.get("/api/runs/no_separator_here/field-artifacts")
    # parse_run_id raises 400; some FastAPI versions wrap as 422. Accept 400 or 404.
    assert r.status_code in (400, 404, 422), r.text


# ---------- Download endpoint ----------

def test_download_residuals_csv_200(client: TestClient) -> None:
    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts/residuals.csv")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/csv")
    # content-length matches the fixture file size
    fixture = _FIXTURE_ROOT / "lid_driven_cavity" / "20260421T000000Z" / "residuals.csv"
    assert int(r.headers.get("content-length", "-1")) == fixture.stat().st_size


def test_download_vtk_200(client: TestClient) -> None:
    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts/lid_driven_cavity_2000.vtk")
    assert r.status_code == 200, r.text


def test_download_404_traversal(client: TestClient) -> None:
    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts/..%2F..%2Fetc%2Fpasswd")
    assert r.status_code == 404, r.text


def test_download_404_missing(client: TestClient) -> None:
    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts/does_not_exist.csv")
    assert r.status_code == 404, r.text
```

**Step 4 — Verify no regression on existing 79 tests**:
Run `.venv/bin/pytest ui/backend/tests/ -v` and confirm the full count is now 79 + 10 (new tests) = 89 green. If the previous 79 drops to <79, revert and debug.
  </action>
  <verify>
    <automated>.venv/bin/pytest ui/backend/tests/test_field_artifacts_route.py -v -x && .venv/bin/pytest ui/backend/tests/ -x --tb=short</automated>
  </verify>
  <acceptance_criteria>
    - `ui/backend/routes/field_artifacts.py` exists, contains `router = APIRouter()`, `def get_field_artifacts`, `def download_field_artifact`
    - `grep -c "field_artifacts" ui/backend/main.py` returns ≥2 (import + include_router)
    - `grep -n "include_router.*field_artifacts" ui/backend/main.py` returns ≥1 match
    - `.venv/bin/pytest ui/backend/tests/test_field_artifacts_route.py -v` passes with ≥10 tests green
    - `.venv/bin/pytest ui/backend/tests/ -x` passes with total count ≥ 89 (79 existing + 10 new; actual count may differ by ±2 depending on parametrize expansion — must be ≥ 79 prior)
    - No existing test was skipped, removed, or marked xfail
    - `python -c "from ui.backend.main import app; paths = [r.path for r in app.routes]; assert '/api/runs/{run_id}/field-artifacts' in paths; assert '/api/runs/{run_id}/field-artifacts/{filename}' in paths; print('OK')"` exits 0
    - `python -c "from ui.backend.routes.field_artifacts import router; assert len(router.routes) == 2"` exits 0 (exactly 2 endpoints registered)
  </acceptance_criteria>
  <done>
Two FastAPI endpoints registered under `/api/runs/{run_id}/field-artifacts` and `/api/runs/{run_id}/field-artifacts/{filename}`. Route file mirrors `audit_package.py` precedent (FileResponse + explicit media_type map — NOT StaticFiles). Test suite covers 10 behaviors (manifest 200/404, ordering, SHA256 format, size, download 200/404, traversal reject). Full `pytest ui/backend/tests/` stays green with total ≥ 89 tests.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Client → FastAPI route | `run_id` + `filename` are client-controlled strings reaching filesystem operations |
| Filesystem → HTTP response | `FileResponse` streams local file bytes to the client |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-07a-07 | Tampering | `filename` path-traversal in `download_field_artifact` | mitigate | Reject `/`, `\\`, `..` early in `resolve_artifact_path`; verify `resolved.relative_to(artifact_dir.resolve())` — mirrors audit_package.py:290-297. Test `test_download_404_traversal` covers |
| T-07a-08 | Tampering | `run_id` malformed / traversal via `../` in segment | mitigate | `parse_run_id` rejects missing `__` (400); downstream path ops use only the rpartition results which cannot contain `/` |
| T-07a-09 | Information Disclosure | Route returns SHA256 of files | accept | SHA256 of our own artifacts is public integrity info, not a secret; intended for Phase 7e manifest use |
| T-07a-10 | Denial of Service | Large VTK files served without rate-limit | accept | Dev-only API, single-user scope; FastAPI's `FileResponse` streams chunked so memory is bounded. Revisit in Phase 7e if exposed publicly |
| T-07a-11 | Information Disclosure | MIME confusion — `.vtk` served as `text/html` | mitigate | Explicit `_MEDIA_TYPES` dict per-extension; default is `application/octet-stream` (never `text/html`). User ratification #1 rationale |
| T-07a-12 | Tampering | SHA256 cache poisoning via mtime+size collision | accept | MVP risk per 07a-RESEARCH.md §2.6; stale hash only if attacker can precisely match mtime+size which requires filesystem write access (already compromised) |
</threat_model>

<verification>
Wave 2 acceptance:

1. `.venv/bin/pytest ui/backend/tests/test_field_artifacts_route.py -v` — all 10 new tests green
2. `.venv/bin/pytest ui/backend/tests/ -x` — total count ≥ 89 (79 existing still green)
3. `python -c "from ui.backend.main import app; paths=[r.path for r in app.routes]; assert '/api/runs/{run_id}/field-artifacts' in paths"` — route registered
4. Integration readiness (consumed by Wave 3): route + fixture + models can be exercised by the `TestClient`; the real end-to-end `scripts/phase5_audit_run.py lid_driven_cavity` integration is deferred to Wave 3
</verification>

<success_criteria>
- 10+ new pytest cases in `test_field_artifacts_route.py` all green
- Total pytest count increases from 79 to ≥ 89 (no existing test breaks)
- Route registered in `main.py` with correct prefix `/api`
- Route file is a clean `FileResponse + path-resolver` copy of the `audit_package.py` precedent (no StaticFiles)
- Pydantic models use existing `Literal` + `Field` idiom (match validation.py style)
- parse_run_id uses `rpartition` (resilient to future labels with internal `__`)
- Artifact sort order is deterministic: `(kind_order, filename)` with `vtk=0, csv=1, residual_log=2`
</success_criteria>

<output>
After Wave 2 completion, Wave 3 (07a-03-PLAN.md) runs:
1. The real integration (scripts/phase5_audit_run.py lid_driven_cavity with EXECUTOR_MODE=foam_agent) against the live code from Wave 1
2. Codex review of ALL Wave 1 + Wave 2 changes
3. DEC-V61-031 authoring + Notion sync
4. STATE.md + ROADMAP.md Phase 7a → COMPLETE
5. Atomic git commit + push

Create `.planning/phases/07a-field-capture/07a-02-SUMMARY.md` documenting:
- Total new pytest count
- Any deviations from the plan (e.g. media_type tweaks, extra helpers)
- Confirmation that 79 existing tests stayed green
</output>
