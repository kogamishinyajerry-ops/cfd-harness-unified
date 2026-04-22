# [CLAUDE → CODEX TOOL INVOCATION]

    from: claude-code-opus47 (Main Driver v6.2)
    to: codex-gpt54-xhigh (Joint Dev Peer · §A Diff Generator)
    task: "DEC-V61-045 Wave 1 Invocation B — comparator_gates.py VTK reader fix"
    contract: Notion DEC-V61-045 PROPOSAL
    spec: .planning/decisions/2026-04-22_phase8_dec045_attestor_gates_blocker_fixes_PROPOSAL.md
    upstream_findings:
      - reports/codex_tool_reports/20260422_dec036b_codex_review.md (CHANGES_REQUIRED, B3 finding)

    scope_tracks:
      - Track 7: Fix read_final_velocity_max() to use latest-time internal-field VTK only

    allowed_files:
      - src/comparator_gates.py

    read_only_context:
      - reports/phase5_fields/lid_driven_cavity/<ts>/VTK/   (real VTK layout reference)
      - reports/phase5_fields/circular_cylinder_wake/<ts>/VTK/  (multi-timestep layout)
      - reports/codex_tool_reports/20260422_dec036b_codex_review.md  (finding B3)

    forbidden_files:
      - any file not in allowed_files
      - especially tests/, scripts/, ui/backend/

    autonomy: TOOL-SCOPE

---

## Problem statement (from Codex DEC-036b B3)

Current `read_final_velocity_max()` at `src/comparator_gates.py:194-245` scans every `*.vtk` under the VTK tree via `vtk_dir.rglob("*.vtk")`. This:

1. **Includes `allPatches/*.vtk`** — these are boundary-patch exports, NOT internal-field. A boundary velocity spike (e.g., LDC lid moving at U=1) propagates into `u_max` even when internal field is clean.
2. **Includes earlier timesteps** — foamToVTK emits `{case}_{timestep}.vtk` for each time. An early-iter velocity transient can false-fire G3 even if the final solution converged to clean field.
3. **Sorts alphabetically** — `sorted(vtk_dir.rglob(...))` gives alphabetical order, which does NOT guarantee latest-time last. `case_100.vtk` sorts after `case_1000.vtk` alphabetically? Actually no, Python string sort: `case_100.vtk` < `case_1000.vtk` (shorter comes first with prefix match). But `case_2.vtk` > `case_1000.vtk` (2 > 1 at position 5). So alphabetical is unreliable for numeric suffixes.

## Required fix

Rewrite `read_final_velocity_max(vtk_dir: Path) -> Optional[float]` to:

1. **Identify latest timestep only**. Parse timestep from filename pattern `{anything}_{integer}.vtk`. If multiple files share the max timestep (e.g., one internal + one allPatches), prefer internal.

2. **Exclude boundary-patch files**. Skip any `*.vtk` whose path contains a directory component named `allPatches` OR whose filename starts with a boundary name (harder to enumerate — prefer the allPatches/ subdir exclusion).

3. **Read exactly one VTK file** (the latest internal). Apply current pyvista reading + max-|U| computation to that single file.

4. **Graceful degradation**: if pattern not parseable OR no internal VTK found OR pyvista unavailable → return None (same as current behavior).

## Reference: real VTK layouts

From repo artifacts:

```
reports/phase5_fields/lid_driven_cavity/20260421T131010Z/VTK/
├── allPatches/
│   └── allPatches_1000.vtk
└── case_1000.vtk                      ← INTERNAL FIELD (use this)
```

```
reports/phase5_fields/circular_cylinder_wake/20260421T150630Z/VTK/
├── allPatches/
│   ├── allPatches_100.vtk
│   ├── allPatches_200.vtk
│   ...
│   └── allPatches_500.vtk
├── ldc_xxx_100.vtk
├── ldc_xxx_200.vtk
...
└── ldc_xxx_500.vtk                    ← LATEST INTERNAL (use this)
```

Note: the `ldc_` prefix in cylinder_wake files is historical naming drift; don't hard-code prefixes. Parse timestep numerically from suffix.

## Recommended algorithm

```python
def read_final_velocity_max(vtk_dir: Path) -> Optional[float]:
    if not vtk_dir.is_dir():
        return None
    try:
        import numpy as np
        import pyvista as pv
    except ImportError:
        return None

    # Collect internal-field VTK files (exclude allPatches subdirectory).
    internal = []
    for p in vtk_dir.rglob("*.vtk"):
        # Skip anything inside an allPatches/ directory.
        if "allPatches" in p.parts:
            continue
        # Parse trailing _<int>.vtk
        m = re.search(r"_(\d+)\.vtk$", p.name)
        if not m:
            continue
        timestep = int(m.group(1))
        internal.append((timestep, p))

    if not internal:
        return None

    # Pick highest timestep. If tie, first encountered wins (deterministic
    # via sort on (timestep, str(path))).
    internal.sort(key=lambda tp: (tp[0], str(tp[1])))
    _, latest_path = internal[-1]

    try:
        mesh = pv.read(str(latest_path))
    except Exception:
        return None

    # Existing U extraction logic (preserve):
    point_fields = set(mesh.point_data.keys()) if hasattr(mesh, "point_data") else set()
    cell_fields = set(mesh.cell_data.keys()) if hasattr(mesh, "cell_data") else set()
    U_array = None
    for field_name in ("U", "velocity", "u"):
        if field_name in point_fields:
            U_array = np.asarray(mesh.point_data[field_name])
            break
        if field_name in cell_fields:
            U_array = np.asarray(mesh.cell_data[field_name])
            break
    if U_array is None or U_array.size == 0:
        return None
    if U_array.ndim == 2 and U_array.shape[1] >= 3:
        mags = np.linalg.norm(U_array[:, :3], axis=1)
    else:
        mags = np.abs(U_array.ravel())
    if mags.size == 0:
        return None
    return float(np.nanmax(mags))
```

## Acceptance Checks

CHK-1: On a VTK dir with `case_100.vtk` (internal, max |U|=1.0) + `allPatches/allPatches_100.vtk` (boundary, max |U|=1.0), returns 1.0 from the internal file.

CHK-2: On a VTK dir with `case_100.vtk` (max |U|=999) + `case_500.vtk` (max |U|=1.0), returns 1.0 (latest timestep).

CHK-3: On a VTK dir with only `allPatches/allPatches_500.vtk` (no internal), returns None.

CHK-4: On a VTK dir with a mix `case_10.vtk`, `case_100.vtk`, `case_2.vtk`, picks `case_100.vtk` (largest numeric timestep, NOT alphabetically sorted where `case_2.vtk` > `case_100.vtk`).

CHK-5: On a VTK dir with filename `case.vtk` (no timestep suffix), skips that file (no match against `_<int>.vtk`); if no other files match returns None.

CHK-6: Existing callers of `read_final_velocity_max(vtk_dir)` (in `_check_g3_velocity_overflow`) work unchanged — signature and return type preserved.

## Reject Conditions

REJ-1: Any edit outside `src/comparator_gates.py`.
REJ-2: Changing the function signature `read_final_velocity_max(vtk_dir: Path) -> Optional[float]`.
REJ-3: Introducing new imports beyond `re` + existing `numpy`/`pyvista` dynamic imports.
REJ-4: Breaking backward compat for `_check_g3_velocity_overflow` caller.

## Output format

```
# Codex Diff Report — DEC-V61-045 Wave 1 B

## Files modified
- src/comparator_gates.py [+N/-M]

## Changes summary
- Rewrite read_final_velocity_max to use latest internal VTK only

## Acceptance checks self-verified
- CHK-1..CHK-6: PASS/FAIL + evidence

## Tokens used
```

---

[/CLAUDE → CODEX TOOL INVOCATION]
