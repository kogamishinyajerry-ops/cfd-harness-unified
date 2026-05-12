# DRAFT patch · A7 STEP canonicalizer (byte-determinism for Codex CAD)

> **Status**: DRAFT · suggested-only · NOT auto-applied
> **Author**: case_012 sub-session · 2026-05-09
> **Target**: main session for landing as sub-DEC
> **Scope**: single sub-DEC, ~80 LOC (well under 250 cap)
> **Triggers**: V51 — STEP timestamp embedded in `FILE_NAME` line breaks byte-determinism

## Why this patch

cadquery 2.7.0 + OCP STEP exporter writes a wall-clock timestamp into
the `FILE_NAME(...)` line of every STEP file. Repeat invocations of
the same `build_cad.py` produce different SHA-256 even when geometry
is byte-identical. This breaks the Codex case-design protocol's
determinism check (per `codex_case_design_protocol.md`).

case_012 v1 carries a workaround (`canonicalize_step()` in
`scripts/build_cad.py`) that strips the timestamp post-write. Promote
to a main-project utility so all cadquery-based Codex cases inherit
it without case-local duplication.

## Surface scan

`grep -rn "FILE_NAME.*Open CASCADE\|step_canonicalize" ui/backend/services/` —
no existing implementation. New module:
`ui/backend/services/geometry_ingest/step_canonicalizer.py`.

## Promotion plan

### Public API surface (proposed)

```python
from ui.backend.services.geometry_ingest.step_canonicalizer import (
    canonicalize_step_file,
    canonicalize_step_text,
    StepCanonicalizationReport,
)

report: StepCanonicalizationReport = canonicalize_step_file(
    path="/path/to/case_012/inputs/cad_codex_v1.step",
    inplace=True,             # or False to write to .canonical.step
    sentinel_timestamp="1970-01-01T00:00:00",
    fields_to_canonicalize=("FILE_NAME",),  # opt-in extension to FILE_DESCRIPTION etc.
)
# report.replaced_lines, report.original_sha256, report.canonical_sha256
```

### Determinism contract

After `canonicalize_step_file()`, two consecutive runs of the same
CAD generator + canonicalizer yield byte-identical STEP files. Test
fixture: case_012 v1 generates → sha256 → canonicalize → sha256
matches reference golden.

### Cross-references

- V51 — case_012 cross-cut (timestamp determinism finding)
- `case_002a` / `case_005` / `case_011` / `case_012` — all observed
  the same Codex CadQuery pattern; canonicalization should be applied
  retroactively to existing case sandboxes for byte-determinism audit
- DEC-V61-198 — APU bay strategic pivot
- `codex_case_design_protocol.md` — determinism contract

## Open questions

- Should the canonicalizer also strip `FILE_DESCRIPTION` (some Codex
  generations include them)? Conservative first-pass: only FILE_NAME.
  Extend per-evidence basis.
- Should the canonicalizer warn if no FILE_NAME line is found (could
  indicate a binary-STEP input or non-OCP exporter)?
