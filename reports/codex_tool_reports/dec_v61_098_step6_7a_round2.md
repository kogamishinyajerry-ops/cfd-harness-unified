Verdict: RESOLVED

Reviewed scope: commit `b3e1720` (`DEC-V61-098` Steps `6+7a` round-2 fix).

## Findings

No blocking correctness issues found in the requested slice.

## Verification

### 1. Actor-map key parsing

- The kernel no longer derives primitive identity from `renderer.getActors()` order. The live pick path now resolves the picked actor through `actorPatchNames.get(pickedActor)` in [ui/frontend/src/visualization/viewport_kernel.ts](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/visualization/viewport_kernel.ts:238), and `Viewport` resolves that `patchName` by equality against `face-index.primitives[].patch_name` in [ui/frontend/src/visualization/Viewport.tsx](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/visualization/Viewport.tsx:234).
- The actor map is populated from vtk.js importer keys in [viewport_kernel.ts](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/visualization/viewport_kernel.ts:166). Installed vtk.js currently creates:
  - node actors as ``${node.id}``
  - primitive actors as ``${node.id}_${primitive.name}``
  Evidence: [ui/frontend/node_modules/@kitware/vtk.js/IO/Geometry/GLTFImporter/Reader.js](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/node_modules/@kitware/vtk.js/IO/Geometry/GLTFImporter/Reader.js:388).
- Edge cases:
  - `patch_name` containing underscores is handled correctly by the current parser. It splits at the first underscore and keeps the full suffix, so `0_fixed_walls` becomes `fixed_walls`.
  - keys without underscore are skipped, which is correct for node actors.
  - Non-blocking note: this still assumes the prefix (`node.id`) itself contains no underscore and vtk.js keeps the current key format. In the current importer path, `node.id` is numeric, so this is safe for this slice.

### 2. `primitive.name` is present in the emitted glTF

- Backend now serializes `"name": name` on every primitive in [ui/backend/services/render/bc_glb.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/render/bc_glb.py:343).
- I also generated a fresh GLB via `build_bc_render_glb("case_001")` and decoded its JSON chunk. The emitted primitive names were:
  - `lid`
  - `fixedWalls`
  - `frontAndBack`
- Each primitive JSON object contained the `name` key.

### 3. Round-1 actor-ordering bug status

- The round-1 bug is resolved. I did not find any remaining runtime dependency on renderer actor ordering in the Step `6+7a` pick path.
- Search result: only explanatory comments still mention `renderer.getActors()` / `primitiveIndex`; no active code uses them.
- The live mapping chain is now:
  - backend GLB primitive `name = patch_name`
  - vtk.js importer actor-map key preserves that name
  - kernel stores `actor -> patchName`
  - React layer resolves `patchName -> primitive`
  - `cellId` indexes `primitive.face_ids`

## Test Evidence

- Backend:
  - `PYTHONPATH=. ./.venv/bin/pytest -q ui/backend/tests/test_face_index.py ui/backend/tests/test_face_annotations_route.py ui/backend/tests/test_case_annotations.py ui/backend/tests/test_bc_glb.py`
  - Result: `59 passed`
- Frontend:
  - `(cd ui/frontend && npx vitest run src/visualization/__tests__/Viewport.test.tsx src/pages/workbench/step_panel_shell/__tests__/AnnotationPanel.test.tsx src/pages/workbench/step_panel_shell/__tests__/DialogPanel.test.tsx)`
  - Result: `3 files passed`, `29 tests passed`

## Conclusion

Round-2 closes the round-1 HIGH finding. The latent `"0_undefined"` primitive collision is also addressed by naming primitives in the GLB. I would treat this review item as resolved.
