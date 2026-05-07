---
decision_id: DEC-V61-181
title: B-ext-3.1 · investigate F10 setup-bc → polyMesh/boundary patch-name divergence (root cause: mesh-after-setup-bc invalidates BC files)
status: Accepted
parent_dec: V61-180
phase: B-extend-3
notion_sync_status: pending
---

# DEC-V61-181 · B-Ext-3.1 F10 investigation

## Status

**Accepted 2026-05-07** — root cause positively identified.

## Findings

R6 friction log analysis on backward_step (run_id `fba6717e`) shows
the persona POSTed `/api/import/<id>/mesh` AFTER `/api/import/<id>/setup-bc`
multiple times (steps 70, 112, 159, 190, 214, 262, 271). Each `/mesh`
call regenerates `constant/polyMesh/` from gmsh+gmshToFoam, producing
a fresh single-`patch0` mesh on the single-shell STL inputs. setup-bc
had previously rewritten `polyMesh/boundary` to `lid`+`fixedWalls`
(LDC default mode) AND authored `0/p`, `0/U` referencing those names;
the subsequent `/mesh` regeneration left `0/p` and `0/U` stale —
referencing patches the new mesh no longer has.

`/solve` then surfaced the inconsistency cryptically inside OpenFOAM:

```
--> FOAM FATAL IO ERROR:
Cannot find patchField entry for patch0
file: /tmp/.../<case>/0/p/boundaryField from line 6 to line 7.
```

On-disk verification of backward_step case dir confirmed:

| File | Patch names |
|---|---|
| `constant/polyMesh/boundary` | `patch0` (1408 faces, single) |
| `0/p` boundaryField | `lid`, `fixedWalls` |
| `0/U` boundaryField | `lid`, `fixedWalls` |

Mesh has one patch; BC files reference patches the mesh doesn't have.
OpenFOAM's `Cannot find patchField entry for patch0` error is
phrased confusingly — it means "boundaryField is missing an entry
for the mesh-side patch named patch0", not "boundaryField references
a non-existent patch0 name". The persona had no chance of
diagnosing this from the OpenFOAM error alone.

## Sequence (backward_step R6)

```
step  64  POST /setup-bc                  → 200  (writes 0/{p,U} with lid/fixedWalls; rewrites polyMesh/boundary if LDC mode)
step  70  POST /mesh                      → 200  (regenerates polyMesh; resets to single patch0)
step  84  POST /setup-bc?from_stl_patches=1 → 200  (single-patch path? — investigated below)
step 112  POST /mesh                      → 200  (regen)
step 118  POST /setup-bc?from_stl_patches=0 → 200
step 133  POST /setup-bc?from_stl_patches=1 → 200
... (5 more /mesh + /setup-bc cycles)
step 271  POST /mesh                      → 200  (final regen; never POSTs /solve)
```

Persona never escaped the loop and never POSTed /solve in this trace.
naca0012 in same R6 hit /solve 4× → all 502 because the on-disk state
at /solve time had the same stale-BC pattern.

Note `from_stl_patches=1` returning 200 on a single-`patch0` mesh
contradicts the route's `if patch_names == ["patch0"]: raise
no_named_patches` check; the explanation is that at the moment of
each POST, polyMesh had multiple patches (a recent setup-bc had
just split it). The next /mesh erased the split.

## Why this is workbench-side, not persona-prompt

The /mesh route does not signal its destructive effect on BC state.
Persona prompts cannot be expected to encode "after /mesh, your
prior /setup-bc is invalid" because (a) it's an internal state
contract not documented in the actions catalogue, (b) re-running
/setup-bc isn't something the persona thinks of after seeing 502
solver-diverged. The mesh→BC contract must be enforced workbench-side.

## Fix scope (V61-182)

Two-pronged workbench-side fix:

1. **Pre-flight validation in `run_icofoam`** — refuse to invoke the
   solver when `0/<field>/boundaryField` keys reference patches not
   present in `polyMesh/boundary`. Raise `mesh_bc_mismatch` mapped
   to HTTP 409 with a clear remediation message.
2. **Eager invalidation in `mesh_imported_case`** — after a
   successful gmshToFoam, remove `0/`, `0.orig/`, and clear `0/*`
   manifest user-overrides. The next /setup-bc authors fresh BC
   files from AI defaults.

Implementation in DEC-V61-182.

## V130 / V132 contract

No persona-prompt changes; advisory-only contract continues to hold.
No new mutating routes.

## Counter

B-ext-3.1 increment: +1.

## References

- DEC-V61-180 · B-ext-3 charter
- `.planning/dogfood/runs/live_2026_05_07_r6/backward_step__novice__deepseek__fba6717e/`
- `ui/backend/services/case_solve/bc_setup_from_stl_patches.py:923` — `if patch_names == ["patch0"]` guard
- `ui/backend/services/case_solve/bc_setup.py:518` — `_split_lid_walls` writes lid/fixedWalls into polyMesh
- `ui/backend/routes/mesh_imported.py` — /mesh route (no BC invalidation pre-fix)
