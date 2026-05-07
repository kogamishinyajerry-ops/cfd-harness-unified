# DRAFT patch · A2 virtual_interface_detector extraction

> **Status**: DRAFT · suggested-only · NOT auto-applied
> **Author**: harvester · 2026-05-08 · cycle 001
> **Target**: main session (or whichever actor lands extraction sub-DECs)
> **Scope**: single sub-DEC, <250 LOC per v2.3 scope rules

## Why this patch

Compounded evidence from harvest cross-cut snapshot:
- 6-of-6 confirmed cases 003-008 expect `virtual_interface_detector`
  for D1 sub-mm gap defects; cases 009-010 expected to be 8-of-8
- All 8 deferred cases require sub-session manual FreeCAD
  `distToShape` workaround until A2 lands
- Each deferred sub-session run will surface "A2-pending"
  V-finding redundantly — wasted harvest signal

## Proposed extraction (suggestion to main session)

**File**: `ui/backend/services/geometry_ingest/virtual_interface_detector.py`

**Source**: APU bay `~/Desktop/apu-bay-ventilation/scripts/02_domain_subtract.py`
`INTERFACE_SPECS` block (line ~92 + neighborhood)

**Algorithm (per V2 finding)**:
```python
def detect_virtual_interface(face_a, face_b, mode="shared"):
    """
    Geometric (not topological) face match.

    Returns dict with:
      - matched: bool
      - bbox_overlap_fraction: float (0..1)
      - area_diff_fraction: float
      - normal_dot: float
      - mode: "shared" | "endcap"
    """
    # bbox overlap > 80%
    # area diff < 5%
    # normal dot < -0.5 for "shared" / > 0.5 for "endcap"
```

**Public API (suggestion)**:
- `detect_virtual_interfaces(shape, specs: list[InterfaceSpec])`
  → list of detected interface pairs
- `validate_interface_coverage(detected, expected)` → coverage report
- `InterfaceSpec` dataclass mirroring APU bay's spec format

**Unit tests** (suggested, not authoritative):
- 2-body fixture with known shared face → matched
- 2-body fixture with known mismatch → not matched
- BREP equality fails but geometric matches → matched (V2 case)
- Endcap mode: parallel-aligned normals → matched
- Threshold sensitivity: 79% bbox overlap → not matched (boundary)

## Why now (not after sub-sessions run)

- Source code already proven in APU bay; this is refactor not invent
- 6-cases-pending evidence beyond compounded threshold (3) by 2×
- Each sub-session that runs WITHOUT A2 produces redundant
  V-finding noise — opportunity cost is real
- Defect distribution will rebalance post-A2 (Codex stops
  defaulting to D1; under-exercised D3/D5/D6/D7 get coverage)

## Risk + mitigation

| Risk | Mitigation |
|---|---|
| APU bay code is too case-specific; generalization breaks | Land first cut as "generic" + explicit acceptance test against APU bay STEP; do NOT delete case-local copy until generalization verified on case_005 sub-session |
| LOC creeps over 250 in extraction | Split: detector + spec-loader as separate sub-DECs |
| First sub-session that uses A2 (case_005) discovers blind spots | Expected — A3 first-exercise pattern says blind spots ARE the V-finding; book it as feature |
| A2 logic differs across CAD vendors (CATIA STEP vs CadQuery STEP) | Initial scope: support CadQuery-generated STEP (all queued cases use this). CATIA path stays in case-local script until next CATIA case lands |

## What this patch does NOT propose

- Does NOT modify any V-series row (that's the V-series file's job
  after A2 actually lands)
- Does NOT change `codex_case_design_protocol.md` defect-distribution
  rules (that's a separate patch — see `draft_defect_diversity_*`)
- Does NOT rewrite APU bay's case-local script (case-local kept
  as ground truth until generalization verified)
- Does NOT deprecate manual FreeCAD `distToShape` workaround in
  defect manifests (sub-sessions can still verify by hand;
  A2 just makes verification automatic)

## Suggested commit-message form (sub-DEC scope per v2.3)

```
feat(geometry_ingest): A2 · virtual_interface_detector extraction

Extracts geometric face-matching from APU bay case-local script.
Closes 6-of-6 compounded-evidence A2-pending V-findings (cases
003-008 via virtual_interface_detector_pending_A2). Sub-sessions
can now use landed advisor instead of manual FreeCAD distToShape.

Sourced from: ~/Desktop/apu-bay-ventilation/scripts/02_domain_subtract.py
V-series: V2 (closes "partial" → "closed")
Pillar 2: stale-assumption-fix triggered by 6-case compounded evidence
Tests: ui/backend/tests/test_virtual_interface_detector.py (5 cases)

confidence: med
Surface-scan: clean (no prior implementation in main project)
```

## References

- `.planning/decisions/2026-05-07_v61_198_apu_bay_strategic_pivot.md`
  · A2 specification
- `.planning/methodology/industrial_case_solver_findings.md` · V2
- `.planning/cross_cuts/advisor_coverage_2026-05-08.md` · 8-case pressure
- `~/Desktop/apu-bay-ventilation/scripts/02_domain_subtract.py:92` ·
  reference implementation
