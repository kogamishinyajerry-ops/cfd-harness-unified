# DRAFT patch · A8 snappyHexMeshDict pre-flight key validator

> **Status**: DRAFT · suggested-only · NOT auto-applied
> **Author**: case_012 sub-session · 2026-05-09
> **Target**: main session for landing as sub-DEC
> **Scope**: single sub-DEC, ~120 LOC (under 250 cap)
> **Triggers**: V52 — `minMedialAxisAngle` (canonical) vs `minMedianAxisAngle` (typo) in OF 2312

## Why this patch

case_012 v1 first-attempt `snappyHexMeshDict` carried
`addLayersControls.minMedianAxisAngle 90;`. OpenFOAM 2312
`displacementMedialAxis` mesh-mover expects `minMedialAxisAngle`.
Typo class is high-frequency (Median ↔ Medial; nFaces ↔ Nfaces;
maxNonOrtho ↔ maxNonOrthog) and produces:

```
--> FOAM FATAL IO ERROR: Entry 'X' not found in dictionary "/case/system/snappyHexMeshDict/Y"
```

after a 5-15 minute sHM run wastes wall-clock. A pre-flight validator
catches typo-class drift and version-pinned key mismatches in <1 sec
before the meshing pipeline starts.

## Surface scan

`grep -rn "snappy.*validator\|snappyHexMeshDict.*check" ui/backend/services/` —
no existing implementation. Closest: `mesh_quality.py` parses
`checkMesh` log post-mesh; this complements it pre-mesh.
New module: `ui/backend/services/mesh_quality/shm_dict_validator.py`.

## Promotion plan

### Public API surface (proposed)

```python
from ui.backend.services.mesh_quality.shm_dict_validator import (
    validate_shm_dict,
    SHMDictValidationReport,
    OPENFOAM_2312_KEY_SET,
    OPENFOAM_FOUNDATION_11_KEY_SET,
)

report: SHMDictValidationReport = validate_shm_dict(
    dict_path="/case/system/snappyHexMeshDict",
    expected_version="2312",       # or "foundation-11" / "esi-2406"
)
# report.unknown_keys: list of {key, dict_path, suggested_alternates}
# report.missing_required_keys: list of {key, dict_path, default_value}
```

### Strategy

- **Per-version key set** — encode canonical keys for OF ESI 2312
  (case_002a / case_012 baseline), foundation-11, ESI 2406. Keys at
  the leaf (e.g., `minMedialAxisAngle`) and at the dict-path prefix
  (`addLayersControls.minMedialAxisAngle`).
- **Fuzzy suggestion** — for unknown keys, return suggested alternates
  via Levenshtein distance ≤ 2. e.g., `minMedianAxisAngle` →
  suggests `minMedialAxisAngle` (distance 1).
- **Optional / required taxonomy** — distinguish "missing this key
  is fatal" from "missing this key uses default value".

### Test fixtures

case_012 v1 first-attempt dict (with `minMedianAxisAngle` typo) →
validator returns `unknown_keys=[{key=minMedianAxisAngle, path=addLayersControls,
suggested_alternates=[minMedialAxisAngle]}]`.

## Cross-references

- V52 — case_012 cross-cut
- `mesh_quality.py` — post-mesh parsing complement
- DEC-V61-198 — APU bay strategic pivot

## Open questions

- Should the validator also detect deprecated keys (e.g., `nGrow`
  changing semantics across OF versions)? First-pass: only typo-class
  unknown keys; deprecation tracking is v2.
