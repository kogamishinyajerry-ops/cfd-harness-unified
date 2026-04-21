# Audit Package Canonical JSON Spec — L4

**Status:** Active (DEC-V61-033, 2026-04-21)
**Supersedes:** `audit_package_canonical_L3.md` (DEC-V61-023, generated_at → build_fingerprint rename)
**Superseded by:** *(none)*

## Change from L3 → L4

L4 adds a new optional top-level key `"phase7"` to the manifest dict. When
present, the signed zip carries an extra tree under `phase7/` containing real
post-processing artifacts from Phase 7a/7b/7c:

- `phase7/comparison_report.pdf`      — 8-section CFD-vs-Gold HTML/PDF from Phase 7c
- `phase7/renders/*.png`              — 2D U-magnitude contour + streamlines, profile overlay, pointwise deviation, residuals (Phase 7b)
- `phase7/renders/*.plotly.json`      — interactive profile figure (Phase 7b)
- `phase7/field_artifacts/VTK/*.vtk`  — raw OpenFOAM volume + boundary VTK (Phase 7a)
- `phase7/field_artifacts/sample/{iter}/*.xy`  — sampled centerline profiles per iteration (Phase 7a)
- `phase7/field_artifacts/residuals.csv`       — parsed residual convergence history (Phase 7a)
- `phase7/field_artifacts/residuals/0/residuals.dat` — raw OpenFOAM residuals function-object output
- `phase7/field_artifacts/log.simpleFoam`      — full solver log

## Manifest `phase7` schema

```json
{
  "phase7": {
    "schema_level": "L4",
    "canonical_spec": "docs/specs/audit_package_canonical_L4.md",
    "entries": [
      {
        "zip_path":         "phase7/comparison_report.pdf",
        "disk_path_rel":    "reports/phase5_reports/lid_driven_cavity/20260421T082340Z/audit_real_run_comparison_report.pdf",
        "sha256":           "945bba9d...",
        "size_bytes":       622078
      }
    ],
    "total_files": 14,
    "total_bytes": 4740367
  }
}
```

**Rules:**

- `entries` is sorted alphabetically by `zip_path`.
- `zip_path` values all start with `phase7/`.
- `sha256` is the full 64-hex-char hash of the file at `disk_path_rel`.
- `disk_path_rel` is repo-relative POSIX style; always resolves under one of
  `reports/phase5_fields/{case}/`, `reports/phase5_renders/{case}/`, or
  `reports/phase5_reports/{case}/` — enforced in `_collect_phase7_artifacts`.
- The key is **optional**. Audit packages built before Phase 7 produced any
  artifacts, or with `include_phase7=False`, omit the key entirely.

## Byte-reproducibility contract

L4 preserves the L3 byte-reproducibility guarantee:

- Two `build_audit_package` calls with the same `(case_id, run_id)` against
  the same repo state produce byte-identical `bundle.zip` and therefore
  identical HMAC signatures.
- Enabled by: sorted zip entry order (`phase7/...` entries sort between
  `manifest.json` and `decisions/*.txt`); epoch mtime on every entry
  (1980-01-01 per `_fixed_zipinfo`); deterministic compression level.
- `phase7` artifact file contents themselves are deterministic for a given
  OpenFOAM run timestamp: the VTK/sample/residual files are frozen by the
  driver at run time; re-rendering Phase 7b produces byte-identical PNGs
  given fixed matplotlib rcParams; Phase 7c HTML is a pure function of
  (gold, artifact bytes).

**Live-verified 2026-04-21:** two consecutive `POST audit-package/build`
calls for `lid_driven_cavity/audit_real_run` produced identical
`bundle.zip` SHA256 (`39990076bfb634d0...`) and identical HMAC signatures
(`a80a549c3d905908...`).

## Security: manifest-path traversal defense

The `phase7` section is built from on-disk state but every value flowing
into `zip_path` / `disk_path_rel` is validated:

1. **Timestamp gate**: `runs/{run_id}.json::timestamp` must match
   `^\d{8}T\d{6}Z$` (`_PHASE7_TIMESTAMP_RE`). Tampered values (e.g.
   `../../outside`, URL-encoded traversal) are rejected before any
   filesystem composition.
2. **Per-entry root containment**: each collected file's resolved path
   must be inside one of the three Phase 7 roots or the entry is silently
   dropped.
3. **Serialize-time re-check**: `serialize._zip_entries_from_manifest`
   re-resolves each `disk_path_rel` and verifies it's under `repo_root`
   before reading bytes — a tampered manifest between build_manifest and
   serialize_zip still can't exfiltrate outside-repo files.

This mirrors the 7a and 7c path-traversal defenses established in
DEC-V61-031 and DEC-V61-032.

## Size characteristics

For a typical LDC simpleFoam run at 129×129 mesh:

| Component                          | Size   |
|------------------------------------|--------|
| `phase7/field_artifacts/VTK/*.vtk` | ~3.2 MB (volume + 45 KB boundary) |
| `phase7/field_artifacts/log.simpleFoam` | ~490 KB |
| `phase7/field_artifacts/sample/*/uCenterline.xy` (×3 iters) | ~27 KB |
| `phase7/field_artifacts/residuals*.csv/.dat`     | ~100 KB |
| `phase7/renders/*.png`             | ~290 KB (4 figures) |
| `phase7/renders/*.plotly.json`     | ~12 KB |
| `phase7/comparison_report.pdf`     | ~622 KB |
| **L4 signed-zip total**            | **~1.97 MB** (was ~260 KB at L3) |

Very large VTK blobs (> 50 MB) are skipped automatically to keep the zip
from ballooning for high-resolution runs; the skipped file is not an error.

## Backward compatibility

L3 consumers (verifiers that don't know about `phase7`) continue to
function — they see the new top-level key and JSON-lenient parsers ignore
unknown keys. HMAC signature generation uses the canonical JSON over the
full manifest dict including `phase7`, so signature matches require
L4-aware re-building.

## Reference implementation

- Manifest builder: `src/audit_package/manifest.py::_collect_phase7_artifacts`
- Zip serializer:   `src/audit_package/serialize.py::_zip_entries_from_manifest`
- HMAC signing:     `src/audit_package/sign.py::sign` (unchanged from L3)
- Tests:            `ui/backend/tests/test_audit_package_phase7e.py` (8 tests)

## Related decisions

- DEC-V61-023 — L3 `generated_at` → `build_fingerprint` rename
- DEC-V61-031 — Phase 7a field capture (source of field_artifacts/)
- DEC-V61-032 — Phase 7b/7c/7f render + report (source of renders/ + comparison_report.pdf)
- DEC-V61-033 — Phase 7d + 7e — this spec
