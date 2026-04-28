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
import vtkMapper from "@kitware/vtk.js/Rendering/Core/Mapper";
import vtkGenericRenderWindow from "@kitware/vtk.js/Rendering/Misc/GenericRenderWindow";

import type { vtkSTLReader } from "@kitware/vtk.js/IO/Geometry/STLReader";

export interface ViewportKernel {
  setBackground(rgb: [number, number, number]): void;
  attachStl(reader: vtkSTLReader): void;
  resetCamera(): void;
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

  // Attached lazily when the STL load resolves.
  let mapper: ReturnType<typeof vtkMapper.newInstance> | undefined;
  let actor: ReturnType<typeof vtkActor.newInstance> | undefined;
  let reader: vtkSTLReader | undefined;

  function attachStl(r: vtkSTLReader): void {
    mapper = vtkMapper.newInstance();
    mapper.setInputConnection(r.getOutputPort());
    actor = vtkActor.newInstance();
    actor.setMapper(mapper);
    reader = r;

    const renderer = grw.getRenderer();
    renderer.addActor(actor);
    renderer.resetCamera();
    grw.getRenderWindow().render();
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

  return { setBackground, attachStl, resetCamera, dispose };
}
