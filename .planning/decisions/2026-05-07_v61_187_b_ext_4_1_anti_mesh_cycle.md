---
decision_id: DEC-V61-187
title: B-ext-4.1 · anti-mesh-cycle persona prompt — Step 2 destructive-mesh warning in all 3 prompts
status: Accepted
parent_dec: V61-186
phase: B-extend-4
notion_sync_status: synced 2026-05-07 (https://www.notion.so/359c68942bed8116a51bd3f260ccd727)
---

# DEC-V61-187 · B-Ext-4.1 anti-mesh-cycle prompt

## Status

**Accepted 2026-05-07** — content-only persona prompt extension.
No harness/runner code changes. 42/42 persona library + assignment
+ runner tests pass.

## Motivation

R7 cell 1 (naca0012/experienced_fluent, run_id `9218e2d7`) shows
the persona executed:

```
early POST /mesh                          → 200
later POST /setup-bc?from_stl_patches=1    → 200
later POST /mesh again                     → 200 (Fix 2 invalidated 0/)
later POST /setup-bc                       → 200
later POST /mesh × 2 more                  → 200
... step 63 SSL EOF
```

Persona never POSTed /solve in 63 turns. The Fix 2 invalidation
from V61-182 is doing exactly what it should — clearing 0/* on
each /mesh — but the persona doesn't realize that re-meshing is
the destructive operation. It keeps regenerating mesh trying to
fix perceived issues in /face-index or /patch-classification
responses.

## Fix

Add a Step 2 warning in each persona prompt's "How to drive the
workbench" section. Voice tailored per persona:

- **novice.md**: "POST /mesh is DESTRUCTIVE. ... If /face-index or
  /patch-classification shows something unexpected, fix it via
  PUT /face-annotations or PUT /patch-classification — never by
  re-meshing."
- **experienced_fluent.md**: "POST /mesh is DESTRUCTIVE. ... Fluent's
  remesh-and-recover habit doesn't apply — patch classification is
  fixed via PUT /face-annotations / PUT /patch-classification, not
  by re-meshing."
- **debug.md**: "POST /mesh is DESTRUCTIVE — single-shot only. ...
  If /solve returns 409 mesh_bc_mismatch (DEC-V61-182), the
  remediation is POST /setup-bc, NOT POST /mesh."

The debug variant explicitly references the DEC-V61-182
mesh_bc_mismatch error so the persona connects the dots when it
sees that 409 response.

## Files changed

- `scripts/dogfood/personas/prompts/novice.md` — Step 2 destructive warning
- `scripts/dogfood/personas/prompts/experienced_fluent.md` — same, terser voice
- `scripts/dogfood/personas/prompts/debug.md` — same, with V61-182 cross-ref

## V130 / V132 contract

Zero impact. Content-only addition; engineer-driven semantic
preserved verbatim. V130 advisory-only attestation continues to
hold; V132 MUTATING_ROUTES + KNOWN_MUTATION_FUNCTIONS registry
unchanged.

## Verification

- ✅ `pytest tests/dogfood/test_personas_library.py` 22/22
- ✅ `pytest tests/dogfood/test_personas_assignment.py` 16/16
- ✅ `pytest tests/dogfood/test_persona_runner.py` 4/4
- 🔜 R8 (DEC-V61-190) provides empirical signal on whether the
  warning closes the mesh-cycle pathology

## Counter

B-ext-4.1 increment: +1. Cumulative B-ext-4: 2 (charter +1, +1).

## References

- DEC-V61-186 · B-ext-4 charter
- DEC-V61-184 · R7 mesh-cycle finding
- DEC-V61-182 · Fix 2 (mesh route invalidation) — referenced in debug prompt
