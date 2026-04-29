// Imperative vtk.js kernel for the Viewport. All @kitware/vtk.js imports
// live in this module so the React component stays free of WebGL/native
// concerns and is fully testable under jsdom (vitest can mock this whole
// module without touching the vtk.js module tree).
//
// Lifecycle contract:
//   - createKernel(container, opts) returns a handle that owns:
//       * the GenericRenderWindow (renderer + render window + interactor)
//       * the trackball interactor style
//   - attachStl(handle, reader) wires a Mapper + Actor for the parsed STL
//     and triggers an initial reset+render
//   - resetCamera(handle) recenters
//   - dispose(handle) tears everything down (must be called from useEffect
//     cleanup; otherwise the GL context leaks across remounts — known
//     defect class per DEC-V61-094 §Failure modes row 2)

import "@kitware/vtk.js/Rendering/Profiles/Geometry";
import vtkActor from "@kitware/vtk.js/Rendering/Core/Actor";
import vtkCellPicker from "@kitware/vtk.js/Rendering/Core/CellPicker";
import vtkMapper from "@kitware/vtk.js/Rendering/Core/Mapper";
import vtkGenericRenderWindow from "@kitware/vtk.js/Rendering/Misc/GenericRenderWindow";

import type { vtkSTLReader } from "@kitware/vtk.js/IO/Geometry/STLReader";
import type { vtkGLTFImporter } from "@kitware/vtk.js/IO/Geometry/GLTFImporter";

/** Result of a successful vtkCellPicker hit. The frontend pickMode
 *  uses ``primitiveIndex`` + ``cellId`` to look up the face_id in the
 *  cached face-index document (DEC-V61-098 spec_v2 §A6).
 */
export interface PickResult {
  /** Index of the picked actor within the kernel's primitive list.
   *  For glb, this matches the glTF primitive index (kernel preserves
   *  importer.getActors() order). For stl this is always 0.
   */
  primitiveIndex: number;
  /** Cell index within the picked actor's polyData (0-based triangle
   *  index for triangulated surfaces).
   */
  cellId: number;
  /** World-space pick position (xyz). Useful for the AnnotationPanel
   *  to anchor itself near the picked face.
   */
  worldPosition: [number, number, number];
}

export type PickHandler = (result: PickResult) => void;

export interface ViewportKernel {
  setBackground(rgb: [number, number, number]): void;
  attachStl(reader: vtkSTLReader): void;
  /** glb path · adds the importer's actors to the renderer (M-RENDER-API). */
  attachGltf(importer: vtkGLTFImporter): void;
  resetCamera(): void;
  /** Enable cell-level picking. ``handler`` fires on left-click; pass
   *  ``null`` to disable picking. The kernel attaches/removes the
   *  vtkCellPicker subscription idempotently. (DEC-V61-098 spec_v2 §A6)
   */
  setPickHandler(handler: PickHandler | null): void;
  dispose(): void;
}

export interface KernelOptions {
  background?: [number, number, number];
}

export function createKernel(
  container: HTMLElement,
  opts: KernelOptions = {},
): ViewportKernel {
  const grw = vtkGenericRenderWindow.newInstance({
    background: opts.background ?? [0.06, 0.07, 0.09],
  });
  grw.setContainer(container);
  grw.resize();

  // GenericRenderWindow.newInstance already installs a
  // vtkInteractorStyleTrackballCamera on its interactor (see
  // node_modules/@kitware/vtk.js/Rendering/Misc/GenericRenderWindow.js
  // — `model.interactor.setInteractorStyle(vtkInteractorStyleTrackballCamera.newInstance())`).
  // Earlier revisions of this kernel created and installed a second
  // trackball style here, which (a) replaced the default style without
  // freeing it and (b) was itself never delete()'d on dispose, leaking
  // vtk objects on every preview mount (Codex round-3 P3 finding).
  // We rely on the built-in default and skip the explicit install.
  const interactor = grw.getInteractor();

  // Attached lazily when the STL or glb load resolves.
  let mapper: ReturnType<typeof vtkMapper.newInstance> | undefined;
  let actor: ReturnType<typeof vtkActor.newInstance> | undefined;
  let reader: vtkSTLReader | undefined;
  let importer: vtkGLTFImporter | undefined;

  // Picking infrastructure. The picker is constructed on first
  // setPickHandler() call and torn down on dispose. We track the
  // attached actors in primitive order so the React layer can resolve
  // cellId → face_id via the face-index doc keyed by primitiveIndex.
  let picker: ReturnType<typeof vtkCellPicker.newInstance> | undefined;
  let pickHandler: PickHandler | null = null;
  let pickSubscription: { unsubscribe: () => void } | undefined;
  const orderedActors: ReturnType<typeof vtkActor.newInstance>[] = [];

  function attachStl(r: vtkSTLReader): void {
    mapper = vtkMapper.newInstance();
    mapper.setInputConnection(r.getOutputPort());
    actor = vtkActor.newInstance();
    actor.setMapper(mapper);
    reader = r;

    const renderer = grw.getRenderer();
    renderer.addActor(actor);
    orderedActors.length = 0;
    orderedActors.push(actor);
    renderer.resetCamera();
    grw.getRenderWindow().render();
  }

  function attachGltf(imp: vtkGLTFImporter): void {
    // GLTFImporter brings its own actors via importActors(); we just
    // bind the renderer and let the importer populate it. The importer
    // itself owns the actors so dispose only needs to delete the
    // importer (cascades to its actors per vtk.js GLTFImporter semantics).
    //
    // Round-2 Finding 5: defer ownership transfer until importActors()
    // succeeds. If setRenderer or importActors throws (truncated payload
    // surviving the parse gate, GL state mismatch, etc.) the kernel
    // would otherwise hold a half-imported reference that leaks until
    // the next dispose. Delete the importer immediately on throw and
    // re-raise so the React layer can surface an error banner.
    try {
      imp.setRenderer(grw.getRenderer());
      imp.importActors();
    } catch (err) {
      try {
        imp.delete();
      } catch {
        // delete() is not formally idempotent in vtk.js
      }
      throw err;
    }
    importer = imp;

    const renderer = grw.getRenderer();
    // Snapshot actors in glTF primitive order so vtkCellPicker hits
    // can be resolved back to a primitive index. GLTFImporter populates
    // the renderer in primitive order; getActors() returns them in the
    // same order. The face-index document on the backend uses this
    // exact order (lid → fixedWalls → alphabetical per bc_glb).
    orderedActors.length = 0;
    const actors = renderer.getActors();
    if (Array.isArray(actors)) {
      for (const a of actors) {
        orderedActors.push(a as ReturnType<typeof vtkActor.newInstance>);
      }
    }
    renderer.resetCamera();
    grw.getRenderWindow().render();
  }

  function setPickHandler(handler: PickHandler | null): void {
    pickHandler = handler;
    if (handler === null) {
      // Tear down any active subscription. The picker itself can be
      // kept around; setPickHandler(null) is a soft-disable so the
      // user can re-arm pickMode without rebuilding the picker.
      pickSubscription?.unsubscribe();
      pickSubscription = undefined;
      return;
    }
    if (!picker) {
      picker = vtkCellPicker.newInstance();
      // setPickFromList(false) means "search all visible actors" rather
      // than a curated subset — appropriate since the kernel owns the
      // full primitive list. We don't need a tolerance > 0 for clean
      // triangulated surfaces.
      picker.setPickFromList(false);
      picker.setTolerance(0);
    }
    if (pickSubscription) {
      // Already armed — handler change is enough; no need to resubscribe.
      return;
    }
    pickSubscription = interactor.onLeftButtonPress((callData: unknown) => {
      const localHandler = pickHandler;
      if (!localHandler || !picker) return;
      // The interactor delivers the pointer in display coords on the
      // callData record. vtk.js types are loose here; use a defensive
      // shape check.
      const cd = callData as
        | { position?: { x?: number; y?: number } }
        | undefined;
      const pos = cd?.position;
      if (
        !pos ||
        typeof pos.x !== "number" ||
        typeof pos.y !== "number"
      ) {
        return;
      }
      const renderer = grw.getRenderer();
      picker.pick([pos.x, pos.y, 0], renderer);
      const pickedActors = picker.getActors();
      if (!Array.isArray(pickedActors) || pickedActors.length === 0) return;
      const pickedActor = pickedActors[0];
      const primitiveIndex = orderedActors.findIndex(
        (a) => a === pickedActor,
      );
      if (primitiveIndex < 0) return;
      const cellId = picker.getCellId();
      if (typeof cellId !== "number" || cellId < 0) return;
      const world = picker.getPickPosition();
      const worldPosition: [number, number, number] = Array.isArray(world)
        ? [
            Number(world[0]) || 0,
            Number(world[1]) || 0,
            Number(world[2]) || 0,
          ]
        : [0, 0, 0];
      localHandler({ primitiveIndex, cellId, worldPosition });
    });
  }

  function resetCamera(): void {
    grw.getRenderer().resetCamera();
    grw.getRenderWindow().render();
  }

  function setBackground(rgb: [number, number, number]): void {
    grw.setBackground(rgb);
    grw.getRenderWindow().render();
  }

  function dispose(): void {
    // Order matters: actor/mapper/reader first (consumers of the
    // renderer), then `grw.delete()` BEFORE `interactor.delete()`.
    //
    // Why grw before interactor (Codex round-4 R4 #1 P2 finding):
    // vtkGenericRenderWindow.delete is a macro chain that calls
    // setContainer(undefined), which in turn calls
    // `interactor.unbindEvents(model.container)` against the old
    // container. If we delete the interactor first, its internal
    // container ref is cleared and the subsequent unbindEvents
    // becomes a no-op — DOM keyup/pointer listeners then accumulate
    // across mount/unmount cycles.
    //
    // After grw.delete() unbinds events, we still call
    // interactor.delete() to release any remaining vtk handles
    // (event listeners are gone by then, so the call is safe).
    try {
      actor?.delete();
    } catch {
      // delete() is not formally idempotent in vtk.js; swallow to keep
      // cleanup atomic across React StrictMode double-invocations.
    }
    try {
      mapper?.delete();
    } catch {
      // see above
    }
    try {
      reader?.delete();
    } catch {
      // see above
    }
    try {
      // GLTFImporter cascades dispose to its imported actors per
      // vtk.js semantics, so deleting the importer here is sufficient
      // for the glb path. If both stl and glb were ever attached on
      // the same kernel (not currently exercised), each cleanup is
      // independent.
      importer?.delete();
    } catch {
      // see above
    }
    try {
      pickSubscription?.unsubscribe();
    } catch {
      // see above
    }
    try {
      picker?.delete();
    } catch {
      // see above
    }
    try {
      grw.delete();
    } catch {
      // see above
    }
    try {
      interactor.delete();
    } catch {
      // see above
    }
  }

  return {
    setBackground,
    attachStl,
    attachGltf,
    resetCamera,
    setPickHandler,
    dispose,
  };
}
