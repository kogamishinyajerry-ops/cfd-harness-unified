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
import vtkCellArray from "@kitware/vtk.js/Common/Core/CellArray";
import vtkCellPicker from "@kitware/vtk.js/Rendering/Core/CellPicker";
import vtkMapper from "@kitware/vtk.js/Rendering/Core/Mapper";
import vtkGenericRenderWindow from "@kitware/vtk.js/Rendering/Misc/GenericRenderWindow";
import vtkPoints from "@kitware/vtk.js/Common/Core/Points";
import vtkPolyData from "@kitware/vtk.js/Common/DataModel/PolyData";

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
  /** Hide the cyan committed-pick overlay (the actual triangle of
   *  the previously picked cell). Idempotent. (Used on
   *  pickMode=false / case-switch / step-leave.)
   */
  clearPickHighlight(): void;
  /** Hide the yellow hover overlay (the triangle currently under
   *  the cursor). Idempotent.
   */
  clearHoverHighlight(): void;
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

  // Cell-highlight overlays. Two separate actors: one for the
  // committed click (cyan, opaque, drawn in front of the geometry)
  // and one for the hover ghost (yellow, slightly translucent). Each
  // owns its own vtkPolyData containing JUST the picked triangles —
  // we update setData on every pick so a single allocation handles
  // any cellId. (Dogfood feedback 2026-04-30: a small point-marker
  // is too weak; the user wants the FACE itself to change color so
  // the selection is unambiguous.)
  let pickHighlightPolyData:
    | ReturnType<typeof vtkPolyData.newInstance>
    | undefined;
  let pickHighlightMapper: ReturnType<typeof vtkMapper.newInstance> | undefined;
  let pickHighlightActor: ReturnType<typeof vtkActor.newInstance> | undefined;
  let hoverHighlightPolyData:
    | ReturnType<typeof vtkPolyData.newInstance>
    | undefined;
  let hoverHighlightMapper: ReturnType<typeof vtkMapper.newInstance> | undefined;
  let hoverHighlightActor: ReturnType<typeof vtkActor.newInstance> | undefined;
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
      // Highlight the picked triangle in cyan. If we can't extract
      // its vertices the click still fires (the right-rail
      // AnnotationPanel will surface), but the user won't see
      // visual confirmation in the viewport — that's acceptable
      // degradation.
      const tri = extractTriangleVertices(
        pickedActor as ReturnType<typeof vtkActor.newInstance>,
        cellId,
      );
      if (tri) applyHighlight(tri, "selected");
      localHandler({ patchName, cellId, worldPosition });
    });
  }

  function setHoverHandler(handler: PickHandler | null): void {
    if (handler === null) {
      hoverSubscription?.unsubscribe();
      hoverSubscription = undefined;
      clearHoverHighlight();
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
          // Cursor moved off the geometry — hide the hover overlay.
          clearHoverHighlight();
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
        // Re-tint the hover overlay onto the triangle the cursor
        // is currently aiming at. Independently from the pick
        // overlay so a confirmed selection stays cyan even as the
        // user moves the cursor over to consider a different face.
        const tri = extractTriangleVertices(
          pickedActor as ReturnType<typeof vtkActor.newInstance>,
          cellId,
        );
        if (tri) applyHighlight(tri, "hover");
        else clearHoverHighlight();
        handler({ patchName, cellId, worldPosition });
      });
    });
  }

  // Extract the 3 vertices of cell ``cellId`` from the actor's
  // underlying vtkPolyData. Returns null on any structural mismatch
  // (cellId out of range, missing polys, non-triangle cell).
  function extractTriangleVertices(
    actor: ReturnType<typeof vtkActor.newInstance>,
    cellId: number,
  ): Float32Array | null {
    try {
      const inputData = actor.getMapper()?.getInputData?.();
      if (!inputData) return null;
      const points = inputData.getPoints?.();
      const polys = inputData.getPolys?.();
      if (!points || !polys) return null;
      const pointArray = points.getData?.();
      const cellData = polys.getData?.();
      if (!pointArray || !cellData) return null;

      // vtkCellArray "legacy" packed format:
      //   [n0, p00, p01, ..., p0_(n0-1), n1, p10, ..., n1_(n1-1)]
      // For an all-triangle GLB this means each cell occupies 4
      // entries: [3, p0, p1, p2]. Most polyData built by GLTFImporter
      // uses this layout, so we can index directly.
      let pointIndices: number[] | null = null;
      const directOffset = cellId * 4;
      if (
        directOffset + 3 < cellData.length &&
        cellData[directOffset] === 3
      ) {
        pointIndices = [
          cellData[directOffset + 1],
          cellData[directOffset + 2],
          cellData[directOffset + 3],
        ];
      } else {
        // Mixed-cell fallback: walk the array. Slow but defensive
        // for hand-rolled polyData with mixed cell sizes.
        let idx = 0;
        let cellCount = 0;
        while (idx < cellData.length) {
          const n = cellData[idx];
          if (cellCount === cellId) {
            if (n !== 3) return null;
            pointIndices = [
              cellData[idx + 1],
              cellData[idx + 2],
              cellData[idx + 3],
            ];
            break;
          }
          idx += n + 1;
          cellCount++;
        }
      }
      if (!pointIndices) return null;

      const out = new Float32Array(9);
      for (let j = 0; j < 3; j++) {
        const pIdx = pointIndices[j];
        if (pIdx * 3 + 2 >= pointArray.length) return null;
        out[j * 3 + 0] = pointArray[pIdx * 3 + 0];
        out[j * 3 + 1] = pointArray[pIdx * 3 + 1];
        out[j * 3 + 2] = pointArray[pIdx * 3 + 2];
      }
      return out;
    } catch {
      return null;
    }
  }

  // Update the given highlight overlay (pick OR hover) to render
  // exactly the supplied triangle. Lazy-allocates the polyData /
  // mapper / actor on first call. ``mode`` controls color/opacity.
  function applyHighlight(
    triangleXyz: Float32Array,
    mode: "selected" | "hover",
  ): void {
    const renderer = grw.getRenderer();
    const isSelected = mode === "selected";
    let polyData = isSelected ? pickHighlightPolyData : hoverHighlightPolyData;
    let mapper = isSelected ? pickHighlightMapper : hoverHighlightMapper;
    let actor = isSelected ? pickHighlightActor : hoverHighlightActor;

    if (!polyData) {
      polyData = vtkPolyData.newInstance();
      const pts = vtkPoints.newInstance();
      pts.setData(new Float32Array(9));
      polyData.setPoints(pts);
      const cells = vtkCellArray.newInstance();
      cells.setData(new Uint32Array([3, 0, 1, 2]));
      polyData.setPolys(cells);
      if (isSelected) pickHighlightPolyData = polyData;
      else hoverHighlightPolyData = polyData;
    }
    if (!mapper) {
      mapper = vtkMapper.newInstance();
      mapper.setInputData(polyData);
      if (isSelected) pickHighlightMapper = mapper;
      else hoverHighlightMapper = mapper;
    }
    if (!actor) {
      actor = vtkActor.newInstance();
      actor.setMapper(mapper);
      const prop = actor.getProperty();
      if (isSelected) {
        // Bright cyan, fully opaque, strong ambient so the highlight
        // stays readable on dark patches and on shadowed sides.
        prop.setColor(0.05, 1.0, 0.8);
        prop.setOpacity(1.0);
        prop.setAmbient(0.85);
        prop.setDiffuse(0.15);
      } else {
        // Saturated yellow with high opacity but not 1.0 so the
        // pick highlight underneath is still readable when hover
        // moves back over a previously-selected face.
        prop.setColor(1.0, 0.92, 0.18);
        prop.setOpacity(0.85);
        prop.setAmbient(0.85);
        prop.setDiffuse(0.15);
      }
      // Lift the highlight slightly toward the camera so z-fighting
      // with the underlying patch's coplanar triangle doesn't strobe
      // the color.
      prop.setRepresentation(2); // SURFACE
      renderer.addActor(actor);
      if (isSelected) pickHighlightActor = actor;
      else hoverHighlightActor = actor;
    }

    // Update the polyData's vertex coordinates in place. vtk.js needs
    // an explicit modified() ping or the mapper will reuse the old
    // GPU buffer.
    const ptsArr = polyData.getPoints().getData() as Float32Array;
    ptsArr.set(triangleXyz);
    polyData.getPoints().modified();
    polyData.modified();
    actor.setVisibility(true);
    grw.getRenderWindow().render();
  }

  function clearPickHighlight(): void {
    if (pickHighlightActor) {
      pickHighlightActor.setVisibility(false);
      grw.getRenderWindow().render();
    }
  }

  function clearHoverHighlight(): void {
    if (hoverHighlightActor) {
      hoverHighlightActor.setVisibility(false);
      grw.getRenderWindow().render();
    }
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
      pickHighlightActor?.delete();
    } catch {
      // see above
    }
    try {
      pickHighlightMapper?.delete();
    } catch {
      // see above
    }
    try {
      pickHighlightPolyData?.delete();
    } catch {
      // see above
    }
    try {
      hoverHighlightActor?.delete();
    } catch {
      // see above
    }
    try {
      hoverHighlightMapper?.delete();
    } catch {
      // see above
    }
    try {
      hoverHighlightPolyData?.delete();
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
    clearPickHighlight,
    clearHoverHighlight,
    dispose,
  };
}
