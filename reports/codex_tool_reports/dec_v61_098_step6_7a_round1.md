Verdict: CHANGES_REQUIRED

Base note: the live `origin/main` in this checkout is `67b0465` on 2026-04-29, not `c49fd11`. I reviewed the requested Step 6a + 6b + 7a slice (`d06d41d`, `36ef308`, `6d41c00`) as the intended scope.

## Findings

### 1. BUG — `primitiveIndex` is not aligned with backend `primitives[i]`, so face picks can resolve to the wrong `face_id`

- Frontend assumption: [ui/frontend/src/visualization/viewport_kernel.ts](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/visualization/viewport_kernel.ts:143) snapshots `renderer.getActors()` and treats that array as “glTF primitive order”; later [viewport_kernel.ts](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/visualization/viewport_kernel.ts:204) uses `orderedActors.findIndex(...)` as the `primitiveIndex` sent back to `Viewport`, and [Viewport.tsx](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/visualization/Viewport.tsx:231) uses that index to read `primitives[result.primitiveIndex].face_ids[cellId]`.
- Backend contract: [ui/backend/services/render/face_index.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/render/face_index.py:84) emits `primitives[]` in bc_glb patch order only, with no extra placeholder entries.
- Real vtk.js behavior in the installed dependency contradicts the frontend assumption:
  - `GLTFImporter` first inserts a node-level actor via `model.actors.set(node.id, nodeActor)` before adding primitive actors via `model.actors.set(node.id + "_" + primitive.name, actor)` in [ui/frontend/node_modules/@kitware/vtk.js/IO/Geometry/GLTFImporter/Reader.js:392](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/node_modules/@kitware/vtk.js/IO/Geometry/GLTFImporter/Reader.js:392) and [Reader.js:396](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/node_modules/@kitware/vtk.js/IO/Geometry/GLTFImporter/Reader.js:396).
  - `importActors()` then adds every actor from that map to the renderer in map iteration order in [GLTFImporter.js:136](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/node_modules/@kitware/vtk.js/IO/Geometry/GLTFImporter.js:136).
  - Primitive creation itself is done inside `Promise.all(...)` in [Reader.js:393](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/node_modules/@kitware/vtk.js/IO/Geometry/GLTFImporter/Reader.js:393), so multi-primitive insertion order is not guaranteed to stay source-order.
- Consequence: even on the simple “one node, N primitives” path, `renderer.getActors()` contains at least one non-primitive node actor ahead of the primitive actors, so the picked primitive actor’s index is shifted relative to backend `primitives[]`. On denser or slower-to-build meshes, primitive order can also become nondeterministic across async completion timing.
- Impact: Step 6b’s `vtkCellPicker` hit can map to the wrong `face_id`, which is exactly the byte-reproducibility-sensitive contract this slice was supposed to protect.

## Test Evidence

- Backend: `PYTHONPATH=. ./.venv/bin/pytest -q ui/backend/tests/test_face_index.py ui/backend/tests/test_face_annotations_route.py ui/backend/tests/test_case_annotations.py` → `47 passed`
- Frontend: `(cd ui/frontend && npx vitest run src/visualization/__tests__/Viewport.test.tsx src/pages/workbench/step_panel_shell/__tests__/AnnotationPanel.test.tsx src/pages/workbench/step_panel_shell/__tests__/DialogPanel.test.tsx)` → `29 passed`

## Notes

- I did not find a separate correctness issue in `AnnotationPanel` name validation or `DialogPanel` default-answer / face-selection gating from the reviewed code and targeted tests.
- I also did not find another active `np.float64` leak path beyond the one already fixed in [ui/backend/services/render/face_index.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/render/face_index.py:109).
- The blocker above is not exercised by the current mocked `Viewport` test because `attachGltf` is stubbed and no real vtk.js actor ordering is asserted.
