# DRAFT patch · A2-v2 gap-defect detection API extension

> **Status**: DRAFT · suggested-only · NOT auto-applied
> **Author**: harvester · 2026-05-08 · cycle 002
> **Target**: main session (or whichever actor lands extraction sub-DECs)
> **Scope**: single sub-DEC, <250 LOC per v2.3 scope rules
> **Successor to**: `draft_a2_extraction_2026-05-08.md` (cycle 001 — landed at commit `a09ae0a`)
> **Triggers**: V25 (open · 2026-05-08) + V19 (superseded → V25) + V21 (closed) + V22 (closed) + V17 (open) — 5-instance compounded evidence

## Why this patch (compounded evidence summary)

A2 LANDED 2026-05-08 (commit `a09ae0a`) for V2 pattern (shared
interface confirmation on non-manifold STEP). case_005 v1+v2
disambiguation surfaced V25 (open):

> A2's `_run_shared` returns `matched=True` with **hardcoded
> placeholder fields** (`bbox_overlap_fraction=1.0`,
> `area_diff_fraction=0.0`, lines 200-201 of the advisor) regardless
> of actual face geometry. The actual inter-face gap distance is
> never computed and never returned. Three industrial cases
> (003 + 004 + 005 v2) all reported "A2 PASS" — none of them
> field-validate A2 as a gap-defect detector. The capability the
> kickoffs assumed exists is not implemented.

Pattern 6 application: V19 v1 conclusion ("A2 doesn't catch D1") was
directionally correct. V19 mechanism diagnosis (`faces_match_shared`
bbox-volume-zero rejection) was code-path-incorrect — the public
API `_run_shared` doesn't call `faces_match_shared` at all.
**V25 is the sharp form**: silent placeholder semantic in the
public API, not bbox failure in a lower-level helper.

Compounded with V17 (A3 advisor scope-narrowness on D2 redundancy
overlay) → 2 advisors with the same shape of scope gap → ready for
"advisor-scope-expansion" sub-DEC arc covering both.

## Proposed extension (suggestion to main session)

### File

`ui/backend/services/geometry_ingest/virtual_interface_detector.py`
(extend; do NOT replace)

### API additions

**1. New field on `DetectedInterface` schema**:

```python
@dataclass
class DetectedInterface:
    spec_name: str
    matched: bool
    body_owner: str | None
    face_owner_index: int | None
    face_target_body: str | None
    face_target_index: int | None
    bbox_overlap_fraction: float
    area_diff_fraction: float
    normal_dot: float
    inter_face_gap_mm: float | None  # NEW
    debug_notes: list[str]
```

**2. Compute real gap in `_run_shared`** (replace hardcoded placeholders):

```python
def _run_shared(spec, owner_body, target_body):
    ...
    if face_o is None or face_t is None:
        return DetectedInterface(
            spec_name=spec.name, matched=False,
            ..., inter_face_gap_mm=None, ...
        )
    # Compute real values, not placeholders:
    bbox_overlap = bbox_overlap_fraction(face_o.bbox, face_t.bbox)
    area_diff = area_diff_fraction(face_o.area, face_t.area)
    n_dot = normal_dot(face_o.normal, face_t.normal)
    # NEW: project centroid-to-centroid vector onto axis defined
    # by face_o normal; this is the perpendicular distance between
    # the two facing planes.
    gap_mm = perpendicular_distance(face_o, face_t)
    return DetectedInterface(
        ..., bbox_overlap_fraction=bbox_overlap,
        area_diff_fraction=area_diff, normal_dot=n_dot,
        inter_face_gap_mm=gap_mm, ...
    )
```

**3. New classifier**:

```python
def should_have_been_shared_with_unintended_gap(
    detected: DetectedInterface,
    max_gap_mm: float = 1.0,
) -> bool:
    """
    Returns True when:
      - matched=True (A2 found facing-face candidates), AND
      - inter_face_gap_mm is not None, AND
      - 0 < inter_face_gap_mm < max_gap_mm
    
    This is the D1-class defect detector: bodies the engineer
    SHOULD share but accidentally separated by a sub-mm gap.
    """
    if not detected.matched:
        return False
    if detected.inter_face_gap_mm is None:
        return False
    return 0.0 < detected.inter_face_gap_mm < max_gap_mm
```

### Test cases (must add)

Append to existing 11 tests in
`ui/backend/tests/test_virtual_interface_detector.py`:

1. **`test_inter_face_gap_mm_zero_for_touching_faces`** — V2-pattern
   shared interfaces (touching, gap=0) return `inter_face_gap_mm=0.0`
2. **`test_inter_face_gap_mm_positive_for_separated_faces`** —
   axis-aligned 0.35 mm gap (case_003 D1 reproduction) returns
   `inter_face_gap_mm ≈ 0.35`
3. **`test_inter_face_gap_mm_curved_geometry`** — flange-ring axial
   gap (case_005 D1 reproduction) returns `inter_face_gap_mm ≈ 0.35`
4. **`test_should_have_been_shared_classifier_pass`** — D1-class
   defect → returns True
5. **`test_should_have_been_shared_classifier_fail_clean`** —
   touching faces → returns False (gap=0)
6. **`test_should_have_been_shared_classifier_fail_no_match`** —
   bodies don't have facing faces → returns False (matched=False)

### Backfill of v1 placeholder semantic

Replace lines 200-201 in `_run_shared`:

```python
# OLD (placeholder):
bbox_overlap_fraction=1.0,
area_diff_fraction=0.0,

# NEW (computed):
bbox_overlap_fraction=bbox_overlap,
area_diff_fraction=area_diff,
inter_face_gap_mm=gap_mm,
```

## Acceptance criteria

- [ ] All 11 existing tests still pass (no regression on V2-pattern
      shared-interface detection)
- [ ] 6 new tests above pass
- [ ] case_005 v3 sub-session re-runs A2 falsification on D1 with
      A2-v2 API, expects `inter_face_gap_mm ≈ 0.35`,
      `should_have_been_shared_with_unintended_gap = True`
- [ ] case_003 + case_004 V-rows in
      `industrial_case_solver_findings.md` re-interpret PASS
      semantically: from "advisor field-validated" to "advisor
      `_run_shared` runs cleanly + finds facing-face candidates
      (V25 capability not yet exercised)" — pending A2-v2 land
- [ ] V25 status: `open` → `[VALIDATED 2026-05-08-or-later]:
      A2-v2 lands; case_005 v3 confirms; case_003/004 re-validation
      planned`
- [ ] Patch documented in commit message body referencing V25 +
      V19 (superseded) + V21 (closed) + V22 (closed) + V17 (open,
      separate patch needed) compounded evidence

## Estimated LOC

- Algorithm: ~30 LOC (perpendicular_distance helper + gap field
  population in `_run_shared`)
- New classifier: ~15 LOC
- New tests: ~120 LOC
- Documentation update in module docstring: ~20 LOC
- **Total: ~185 LOC** (under v2.3 sub-DEC <250 LOC scope ceiling)

## Sub-DEC scope (per v2.3 / DEC-V61-133)

This is **not** a charter / not cross-≥3-modules / not
governance-rule-change → **sub-DEC scope**, no full DEC required.
Commit message + frontmatter sub-DEC fields (decision_id, title,
status, parent_dec=V61-198, phase, notion_sync_status) is enough.

Suggested decision_id: `V61-198-sub-A2v2-gap-detection`.

## Dependencies / sequencing

1. **Before**: harvester writes harvest_002.md (this cycle) — done
2. **Land**: this patch's content as A2-v2 implementation +
   tests pass
3. **After**: case_005 v3 re-runs D1 falsification via A2-v2 →
   V25 → `[VALIDATED]`
4. **Cascade**: case_003 + case_004 reference profiles updated
   to clarify what their A2 PASS actually meant (per
   knowledge_status_convention.md)
5. **Future**: A3 v2 redundancy-overlay-detection patch
   (V17 fix; separate sub-DEC)

## Anti-patterns to avoid

1. **Don't break V2-pattern detection** — the existing 11 tests
   guard the V2 use case; gap-detection is ADDITIVE
2. **Don't add `isSame()` fast-path** — V2 lesson preserved
3. **Don't introduce a separate `gap_detector` module** — extending
   A2's API is correct; bifurcating creates two advisors that must
   be invoked together
4. **Don't auto-classify on call** — the classifier
   `should_have_been_shared_with_unintended_gap` is a separate
   function; engineers can opt in. A2's `detect_virtual_interfaces`
   should still return the raw `DetectedInterface` for V2-pattern
   confirmation use without forcing gap classification.

## Open questions for user

- Should `max_gap_mm` default to 1.0 (covers D1 typical 0.30-0.35
  mm) or be required-arg (forces engineer to think about the
  threshold)?
- Should `inter_face_gap_mm` for touching faces (V2 pattern) return
  `0.0` or `None`? `0.0` is informative; `None` matches "no gap to
  measure when bodies are in contact." Recommend `0.0` for
  symmetry with D1 case.
- Should the classifier handle the `_run_endcap` mode too (single-
  body axis-extreme face), or stay shared-mode-only? Recommend
  shared-mode-only; endcap is for a different defect topology
  (open boundaries) that doesn't have a "should-have-been-shared"
  interpretation.

These are user/main-session decisions, not harvester decisions.
