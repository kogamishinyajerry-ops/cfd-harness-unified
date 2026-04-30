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
import vtkSphereSource from "@kitware/vtk.js/Filters/Sources/SphereSource";

import type { vtkSTLReader } from "@kitware/vtk.js/IO/Geometry/STLReader";
import type { vtkGLTFImporter } from "@kitware/vtk.js/IO/Geometry/GLTFImporter";

/** Result of a successful vtkCellPicker hit. The frontend pickMode
 *  uses ``patchName`` + ``cellId`` to look up the face_id in the
 *  cached face-index document (DEC-V61-098 spec_v2 §A6).
 *
 *  Codex round 1 finding 1 (2026-04-29): an earlier revision returned
 *  ``primitiveIndex`` based on ``renderer.getActors()`` order. That
 *  mechanism was unsound — vtk.js GLTFImporter inserts a node-level
 *  actor into the renderer ahead of every primitive actor (see
 *  ``IO/Geometry/GLTFImporter/Reader.js:392``), and primitive actor
 *  insertion is concurrent under ``Promise.all`` so order is also not
 *  stable. The kernel now keys by patch_name extracted from the glTF
 *  actor map, which the backend bc_glb sets on each primitive
 *  (``primitive.name = patch_name``).
 */
export interface PickResult {
  /** Patch name resolved from the picked actor's glTF primitive.name
   *  attribute. The Viewport layer maps this to ``primitives[i]``
   *  in the face-index by ``patch_name`` equality. For STL (single
   *  actor, no primitive metadata) this is the empty string and the
   *  Viewport falls back to primitive index 0.
   */
  patchName: string;
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
  /** Hover-preselect handler. Throttled to one pick-per-RAF; fires
   *  on every mouse move with the same PickResult shape as the
   *  click handler. Pass ``null`` to disable. Independently from
   *  setPickHandler so the kernel can do hover-only or click-only
   *  modes if a future viewport needs that. (Dogfood feedback
   *  2026-04-30 — without hover feedback users can't tell which
   *  face they're about to commit to.)
   */
  setHoverHandler(handler: PickHandler | null): void;
  /** Place a small bright cyan sphere at the given world position
   *  so the user gets immediate visual confirmation that a pick
   *  succeeded. Pass ``null`` to hide the marker. Sized relative to
   *  the current scene bounds. (Dogfood feedback 2026-04-30 —
   *  without visual feedback the user can't tell pick from no-op.)
   */
  setPickMarker(world: [number, number, number] | null): void;
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
  // setPickHandler() call and torn down on dispose. We track each
  // primitive actor by its glTF primitive.name (= bc_glb's patch_name)
  // so the React layer can resolve actor → patch_name → face_index
  // primitive without depending on renderer.getActors() ordering
  // (see PickResult docstring for why that's unsound).
  let picker: ReturnType<typeof vtkCellPicker.newInstance> | undefined;
  let pickHandler: PickHandler | null = null;
  let pickSubscription: { unsubscribe: () => void } | undefined;
  // Hover preselect (dogfood feedback 2026-04-30): mouse-move runs the
  // picker on the cursor position so the user gets which-face-you'll-
  // -hit feedback BEFORE they click. Throttled to one pick per RAF
  // tick because vtkCellPicker.pick is non-trivial work and mouse-move
  // events fire at high frequency.
  let hoverSubscription: { unsubscribe: () => void } | undefined;
  let hoverPending = false;

  // Pick-marker actor (sphere placed at the last successful pick's
  // worldPosition). Built lazily on first setPickMarker call.
  let markerSource:
    | ReturnType<typeof vtkSphereSource.newInstance>
    | undefined;
  let markerMapper: ReturnType<typeof vtkMapper.newInstance> | undefined;
  let markerActor: ReturnType<typeof vtkActor.newInstance> | undefined;
  // Hover-marker (translucent yellow ghost that tracks the cursor).
  // Separate from the click marker so the click marker can stay parked
  // at the engineer's confirmed selection while the hover one flits
  // around. Lazy-allocated.
  let hoverMarkerSource:
    | ReturnType<typeof vtkSphereSource.newInstance>
    | undefined;
  let hoverMarkerMapper: ReturnType<typeof vtkMapper.newInstance> | undefined;
  let hoverMarkerActor: ReturnType<typeof vtkActor.newInstance> | undefined;
  // Map: actor object identity → its glTF primitive.name. Empty for
  // STL (single anonymous actor; we record "" and the React layer
  // falls back to primitive index 0).
  const actorPatchNames = new Map<
    ReturnType<typeof vtkActor.newInstance>,
    string
  >();

  function attachStl(r: vtkSTLReader): void {
    mapper = vtkMapper.newInstance();
    mapper.setInputConnection(r.getOutputPort());
    actor = vtkActor.newInstance();
    actor.setMapper(mapper);
    reader = r;

    const renderer = grw.getRenderer();
    renderer.addActor(actor);
    actorPatchNames.clear();
    // STL has no patch metadata. Record the empty string; the Viewport
    // resolution path uses primitive[0] as the fallback when
    // patchName === "".
    actorPatchNames.set(actor, "");
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
    // Build the actor → patch_name map by walking the importer's
    // internal actor map. vtk.js GLTFImporter sets keys as
    // ``${node.id}`` for node actors and ``${node.id}_${primitive.name}``
    // for primitive actors (see Reader.js:392 + 396). Keys without an
    // underscore are node actors (skip — they have no primitive); keys
    // with underscore embed the patch_name as the suffix (we set
    // primitive.name=patch_name in bc_glb.py to make these distinct).
    actorPatchNames.clear();
    const importerWithGetters = imp as unknown as {
      getActors?: () => Map<string, ReturnType<typeof vtkActor.newInstance>>;
    };
    const actorsMap = importerWithGetters.getActors?.();
    if (actorsMap && typeof actorsMap.forEach === "function") {
      actorsMap.forEach((a, key) => {
        const underscoreIdx = typeof key === "string" ? key.indexOf("_") : -1;
        if (underscoreIdx <= 0) {
          // Node actor (just the node id, no primitive suffix). Skip.
          return;
        }
        const patchName = key.slice(underscoreIdx + 1);
        actorPatchNames.set(a, patchName);
      });
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
      // full primitive list.
      picker.setPickFromList(false);
      // Dogfood feedback 2026-04-30: tolerance=0 was silently missing
      // most clicks on real-world meshes (the user reported clicks
      // produced no feedback at all). vtk.js cell-picker tolerance is
      // a fraction of the renderer diagonal; 0.005 = 0.5% gives the
      // ray a small "fat" radius that handles rasterization-rounding
      // edge cases on tiny triangles without smearing across faces.
      picker.setTolerance(0.005);
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
      // Dogfood feedback 2026-04-30: actor-map lookup returning
      // undefined was silently dropping every click. Fall back to ""
      // so the Viewport's resolution path picks primitives[0] of the
      // face-index — the right answer for single-primitive GLBs and
      // STL fallback cases. Multi-primitive GLBs still get their
      // proper patch name from the actorsMap walk above.
      const patchName =
        actorPatchNames.get(
          pickedActor as ReturnType<typeof vtkActor.newInstance>,
        ) ?? "";
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
      localHandler({ patchName, cellId, worldPosition });
    });
  }

  function setHoverHandler(handler: PickHandler | null): void {
    if (handler === null) {
      hoverSubscription?.unsubscribe();
      hoverSubscription = undefined;
      // Hide the hover marker if any.
      if (hoverMarkerActor) {
        hoverMarkerActor.setVisibility(false);
        grw.getRenderWindow().render();
      }
      return;
    }
    if (!picker) {
      // Hover wants the same picker as click; reuse it. If picker
      // isn't built yet, build now.
      picker = vtkCellPicker.newInstance();
      picker.setPickFromList(false);
      picker.setTolerance(0.005);
    }
    if (hoverSubscription) return;
    hoverSubscription = interactor.onMouseMove((callData: unknown) => {
      if (hoverPending) return;
      hoverPending = true;
      requestAnimationFrame(() => {
        hoverPending = false;
        if (!picker) return;
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
        if (!Array.isArray(pickedActors) || pickedActors.length === 0) {
          // Cursor moved off the geometry — hide the hover marker.
          if (hoverMarkerActor && hoverMarkerActor.getVisibility?.()) {
            hoverMarkerActor.setVisibility(false);
            grw.getRenderWindow().render();
          }
          return;
        }
        const pickedActor = pickedActors[0];
        const patchName =
          actorPatchNames.get(
            pickedActor as ReturnType<typeof vtkActor.newInstance>,
          ) ?? "";
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
        // Move the hover marker to the new spot. Independently from
        // the click marker so a confirmed selection stays parked
        // even as the user moves on to consider a different face.
        showHoverMarker(worldPosition);
        handler({ patchName, cellId, worldPosition });
      });
    });
  }

  function showHoverMarker(world: [number, number, number]): void {
    const renderer = grw.getRenderer();
    if (!hoverMarkerSource) {
      hoverMarkerSource = vtkSphereSource.newInstance({
        thetaResolution: 12,
        phiResolution: 12,
      });
    }
    if (!hoverMarkerMapper) {
      hoverMarkerMapper = vtkMapper.newInstance();
      hoverMarkerMapper.setInputConnection(hoverMarkerSource.getOutputPort());
    }
    if (!hoverMarkerActor) {
      hoverMarkerActor = vtkActor.newInstance();
      hoverMarkerActor.setMapper(hoverMarkerMapper);
      // Soft yellow with high opacity so it reads as "you're aiming
      // here" — distinct from the cyan click marker which means
      // "you've committed to this face".
      hoverMarkerActor.getProperty().setColor(1.0, 0.9, 0.2);
      hoverMarkerActor.getProperty().setAmbient(0.7);
      hoverMarkerActor.getProperty().setDiffuse(0.3);
      hoverMarkerActor.getProperty().setOpacity(0.7);
      renderer.addActor(hoverMarkerActor);
    }
    const bounds = renderer.computeVisiblePropBounds();
    let radius = 0.008;
    if (Array.isArray(bounds) && bounds.length === 6) {
      const dx = (bounds[1] - bounds[0]) || 0;
      const dy = (bounds[3] - bounds[2]) || 0;
      const dz = (bounds[5] - bounds[4]) || 0;
      const diag = Math.sqrt(dx * dx + dy * dy + dz * dz);
      if (diag > 0) radius = Math.max(diag * 0.009, 1e-6);
    }
    hoverMarkerSource.setCenter(world[0], world[1], world[2]);
    hoverMarkerSource.setRadius(radius);
    hoverMarkerActor.setVisibility(true);
    grw.getRenderWindow().render();
  }

  function setPickMarker(world: [number, number, number] | null): void {
    const renderer = grw.getRenderer();
    if (world === null) {
      // Hide the marker (keep the actor + source allocated so a
      // subsequent pick re-shows it without re-allocation churn).
      if (markerActor) {
        markerActor.setVisibility(false);
        grw.getRenderWindow().render();
      }
      return;
    }
    // Lazy-allocate on first pick.
    if (!markerSource) {
      markerSource = vtkSphereSource.newInstance({
        thetaResolution: 16,
        phiResolution: 16,
      });
    }
    if (!markerMapper) {
      markerMapper = vtkMapper.newInstance();
      markerMapper.setInputConnection(markerSource.getOutputPort());
    }
    if (!markerActor) {
      markerActor = vtkActor.newInstance();
      markerActor.setMapper(markerMapper);
      // Bright cyan with full alpha — distinct from any patch color
      // (lid red / wall gray / frontAndBack slate). Slight emissive
      // tint via ambient so it stays visible even when the geometry's
      // lighting puts it in shadow.
      markerActor.getProperty().setColor(0.0, 1.0, 0.85);
      markerActor.getProperty().setAmbient(0.6);
      markerActor.getProperty().setDiffuse(0.4);
      renderer.addActor(markerActor);
    }
    // Size the sphere relative to the scene bounds so it stays
    // visible without occluding meaningful geometry. Falls back to a
    // small absolute radius if bounds are degenerate.
    const bounds = renderer.computeVisiblePropBounds();
    let radius = 0.01;
    if (Array.isArray(bounds) && bounds.length === 6) {
      const dx = (bounds[1] - bounds[0]) || 0;
      const dy = (bounds[3] - bounds[2]) || 0;
      const dz = (bounds[5] - bounds[4]) || 0;
      const diag = Math.sqrt(dx * dx + dy * dy + dz * dz);
      if (diag > 0) radius = Math.max(diag * 0.012, 1e-6);
    }
    markerSource.setCenter(world[0], world[1], world[2]);
    markerSource.setRadius(radius);
    markerActor.setVisibility(true);
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
      hoverSubscription?.unsubscribe();
    } catch {
      // see above
    }
    try {
      picker?.delete();
    } catch {
      // see above
    }
    try {
      markerActor?.delete();
    } catch {
      // see above
    }
    try {
      markerMapper?.delete();
    } catch {
      // see above
    }
    try {
      markerSource?.delete();
    } catch {
      // see above
    }
    try {
      hoverMarkerActor?.delete();
    } catch {
      // see above
    }
    try {
      hoverMarkerMapper?.delete();
    } catch {
      // see above
    }
    try {
      hoverMarkerSource?.delete();
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
    setHoverHandler,
    setPickMarker,
    dispose,
  };
}
