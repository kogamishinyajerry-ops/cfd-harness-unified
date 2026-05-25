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
import vtkColorTransferFunction from "@kitware/vtk.js/Rendering/Core/ColorTransferFunction";
import vtkCoordinate from "@kitware/vtk.js/Rendering/Core/Coordinate";
import vtkMapper from "@kitware/vtk.js/Rendering/Core/Mapper";
import vtkGenericRenderWindow from "@kitware/vtk.js/Rendering/Misc/GenericRenderWindow";
import vtkPoints from "@kitware/vtk.js/Common/Core/Points";
import vtkPolyData from "@kitware/vtk.js/Common/DataModel/PolyData";

import type { vtkSTLReader } from "@kitware/vtk.js/IO/Geometry/STLReader";
import type { vtkGLTFImporter } from "@kitware/vtk.js/IO/Geometry/GLTFImporter";

import { detectWebGL, WebGLUnavailableError } from "./webgl_support";

// B2.5 · VTP polydata reader for foamToVTK / streamLine output (real
// solver data layered onto the viewport per V4 blueprint 6/7).
// Lazy import path keeps the IO/XML chunk out of the initial bundle.
type VtkXMLPolyDataReader = {
  setUrl(url: string): Promise<unknown>;
  getOutputData(idx?: number): VtkPolyDataLike;
  getOutputPort(): unknown;
  delete(): void;
};
type VtkPolyDataLike = {
  getPointData(): VtkFieldDataLike;
  getCellData?: () => VtkFieldDataLike;
  getPoints?: () => {
    getData(): Float32Array | Float64Array | number[];
  };
  getNumberOfPoints?: () => number;
  getNumberOfLines?: () => number;
  getNumberOfPolys?: () => number;
  getBounds(): [number, number, number, number, number, number];
  modified?: () => void;
};
type VtkFieldDataLike = {
  getArrayByName(name: string): VtkDataArrayLike | null;
  getScalars?: () => VtkDataArrayLike | null;
  modified?: () => void;
  setActiveScalars(name: string): number;
};
type VtkDataArrayLike = {
  getName(): string;
  getNumberOfComponents(): number;
  getRange(component?: number): [number, number];
  getData(): Float32Array | Float64Array | number[];
};
type VtkTubeFilterLike = {
  setInputData(data: VtkPolyDataLike): void;
  setInputArrayToProcess(
    inputPort: number,
    arrayName: string,
    fieldAssociation: string,
    attributeType?: string,
  ): void;
  update(): void;
  getOutputData(idx?: number): VtkPolyDataLike;
  delete(): void;
};

// V4 Phase R4 · token SSOT for runtime highlight colors. Replaces the
// old hard-coded cyan/yellow RGB at the applyHighlight call sites so
// the entire V4 color story flows from the palette module.
// Tokens: pick=brand (#5BB4FF · accent-blue, signal-strong) · hover=active
// (#F0A93B · selection-orange, blueprint preset-chip color).
import {
  V4_CFD_COLORMAP,
  V4_PALETTE,
  hexToRgbFloat,
} from "@/theme/industrial_minimalist";
const PICK_HIGHLIGHT_RGB = hexToRgbFloat(V4_PALETTE.brand);
const HOVER_HIGHLIGHT_RGB = hexToRgbFloat(V4_PALETTE.active);

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
  /** World-space pick position (xyz). */
  worldPosition: [number, number, number];
  /** The vtk.js actor that owns ``cellId``. Surfaced so the React
   *  layer can call setPick/HoverHighlightCells with sibling cellIds
   *  (resolved from the face-index reverse map) to highlight the
   *  whole polyMesh face, not just the single triangle that the
   *  picker happened to hit. (2026-04-30 dogfood feedback closure.)
   */
  actor: ReturnType<typeof vtkActor.newInstance>;
}

export type PickHandler = (result: PickResult) => void;

/** Opaque handle for a VTP attachment · used by detachVtp / scalar
 *  range queries. The shape is internal to the kernel; consumers
 *  treat it as opaque. */
export interface VtpAttachHandle {
  readonly id: number;
  readonly url: string;
  readonly kind: "surface" | "streamlines";
  /** Range of the active scalar over the loaded polyData ·
   *  populated once attach resolves. Surfaced so the React colorbar
   *  can label real values rather than guessing. */
  readonly scalarRange: [number, number];
}

export interface ViewportKernel {
  setBackground(rgb: [number, number, number]): void;
  attachStl(reader: vtkSTLReader): void;
  /** glb path · adds the importer's actors to the renderer (M-RENDER-API). */
  attachGltf(importer: vtkGLTFImporter): void;
  /** B2.5 · VTP polydata path · adds an XML-PolyData reader's output as
   *  a new actor with U-magnitude colormap. Mapper kind controls
   *  scalar mode + line/surface representation:
   *
   *    - "surface" — Phong-shaded triangles with U colored on the
   *      patch face (typical Post-mode engine wall rendering).
   *    - "streamlines" — line geometry converted to thin vtk.js
   *      TubeFilter surfaces so the integrated tracks are legible
   *      against the hull and rotate with the scene.
   *
   *  Returns a handle the caller can pass to ``detachVtp`` to cleanly
   *  remove the actor on URL change. The reader/mapper/actor live
   *  on the kernel side; caller owns no native refs. */
  attachVtp(
    url: string,
    kind: "surface" | "streamlines",
    scalarRange?: [number, number],
  ): Promise<VtpAttachHandle>;
  /** Remove a VTP attachment previously created by attachVtp(). */
  detachVtp(handle: VtpAttachHandle): void;
  resetCamera(): void;
  /** V79.1 · Set camera to a canonical preset orientation (industrial
   *  CAE standard views). The kernel computes camera position relative
   *  to the scene bounding box, then re-renders.
   *
   *  Presets (matches CATIA / Solidworks / Ansys Workbench naming):
   *    - "front" · looks down +Y at world origin
   *    - "top"   · looks down -Z at world origin
   *    - "iso"   · isometric view (looks down [+1,+1,+1] toward origin)
   */
  setCameraPreset(preset: "front" | "top" | "iso"): void;
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
  /** Hide the cyan committed-pick overlay. Idempotent. (Used on
   *  pickMode=false / case-switch / step-leave.)
   */
  clearPickHighlight(): void;
  /** Hide the yellow hover overlay. Idempotent. */
  clearHoverHighlight(): void;
  /** Replace the cyan committed-pick overlay with the union of the
   *  given cells from the picked actor's underlying polyData. Used
   *  by the React layer to highlight every triangle that shares the
   *  same face_id (so a polyMesh face whose triangulation produced
   *  multiple GLB triangles ends up fully colored, not half).
   *  Pass empty array or call clearPickHighlight to hide.
   */
  setPickHighlightCells(
    actor: ReturnType<typeof vtkActor.newInstance>,
    cellIds: number[],
  ): void;
  /** Same as setPickHighlightCells but for the yellow hover overlay. */
  setHoverHighlightCells(
    actor: ReturnType<typeof vtkActor.newInstance>,
    cellIds: number[],
  ): void;
  /** Return all cellIds whose triangles share the same plane (within
   *  a fixed quantization tolerance) as the triangle at ``cellId``.
   *  Used by the React layer to expand a single-cell pick into the
   *  full flat face. Falls back to ``[cellId]`` for curved geometry
   *  or degenerate input. (2026-04-30 dogfood feedback closure.)
   */
  getCoplanarSiblings(
    actor: ReturnType<typeof vtkActor.newInstance>,
    cellId: number,
  ): number[];
  /** V4 Phase C-R3 · legend → viewport reverse highlight.
   *
   *  Highlight every triangle on the actor whose glTF
   *  primitive.name (= bc_glb's patch_name) matches ``name``. Passing
   *  ``null`` clears the named overlay (same shape as
   *  ``clearPick/HoverHighlight``).
   *
   *  - kind="pick"  → cyan committed overlay (idempotent with click pick)
   *  - kind="hover" → yellow ghost overlay (idempotent with mouse hover)
   *
   *  Returns the number of cells highlighted. 0 when the patch_name
   *  isn't bound (e.g. STL load or mismatched name) — the React layer
   *  can use this to detect "no-op" and surface a soft status.
   */
  highlightPatchByName(
    name: string | null,
    kind: "pick" | "hover",
  ): number;
  /** V4 Phase C-R5 · centroid lookup for screen-space annotations.
   *
   *  Returns the bounds-midpoint of the actor whose glTF primitive.name
   *  matches ``name`` (the "centroid" of its surface AABB, not a true
   *  mass centroid — adequate for hanging a leader-line label off the
   *  patch). Null when the patch_name isn't bound or the actor has no
   *  geometry mapper input. */
  getPatchCentroid(name: string): [number, number, number] | null;
  /** V4 Phase C-R5 · world → CSS pixel coordinate projection.
   *
   *  Runs the active camera's view + projection matrices on the given
   *  world point and returns the resulting (x, y) coordinate in the
   *  container's CSS pixel space (origin top-left). ``behind`` is true
   *  when the projected point is behind the camera (negative dot product
   *  of (point − camera_pos) with camera direction-of-projection) —
   *  callers should clamp to an edge in that case instead of letting
   *  the point go off-screen unboundedly.
   *
   *  Returns null when the underlying GenericRenderWindow has been
   *  disposed or no container size is known yet (first paint pre-resize).
   */
  worldToScreen(
    world: [number, number, number],
  ): {
    x: number;
    y: number;
    /** Geometrically behind the camera plane (projection meaningless). */
    behind: boolean;
    /** In front of camera but projects outside [0,W]×[0,H] container box. */
    offscreen: boolean;
  } | null;
  dispose(): void;
}

export interface KernelOptions {
  background?: [number, number, number];
}

export function createKernel(
  container: HTMLElement,
  opts: KernelOptions = {},
): ViewportKernel {
  // Guard the single vtk.js bootstrap chokepoint. Without a usable WebGL
  // context, GenericRenderWindow.setContainer() reaches RenderWindow.js's
  // `new Proxy(null, ...)` and throws an opaque TypeError that crashes the
  // React tree. Pre-check + try/catch convert that into a typed
  // WebGLUnavailableError so every caller (ViewportV4, legacy Viewport) can
  // degrade gracefully. Removes the app's hard dependency on the
  // --use-gl=swiftshader headless workaround.
  if (!detectWebGL()) {
    throw new WebGLUnavailableError();
  }
  let grw: ReturnType<typeof vtkGenericRenderWindow.newInstance>;
  try {
    grw = vtkGenericRenderWindow.newInstance({
      background: opts.background ?? [0.06, 0.07, 0.09],
    });
    grw.setContainer(container);
    grw.resize();
  } catch (err) {
    throw new WebGLUnavailableError(
      "vtk.js render window init failed (no usable WebGL context)",
      { cause: err },
    );
  }

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
  // Map: actor → cellId → list of cellIds whose triangles share the
  // same plane (quantized normal + plane offset). Built on first
  // attach + cached. (Dogfood feedback 2026-04-30: gmsh tet meshes
  // give 1 triangle per polyMesh face, so face_id-grouping is 1:1
  // and the user can't tell their "lid face click" from a single-
  // triangle pick. Coplanar grouping recovers "highlight the whole
  // flat face of the cube" semantics for axis-aligned dogfood
  // geometries.)
  const coplanarGroups = new Map<
    ReturnType<typeof vtkActor.newInstance>,
    Map<number, number[]>
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

  // ─── B2.5 · VTP attachments (real solver field overlays) ──────────
  // Each call to attachVtp creates a (reader, mapper, actor) triple
  // owned by the kernel. We track them by id so detachVtp can pull
  // them out of the renderer without disturbing the base glb/stl.
  interface VtpEntry {
    handle: VtpAttachHandle;
    reader: VtkXMLPolyDataReader;
    mapper: ReturnType<typeof vtkMapper.newInstance>;
    actor: ReturnType<typeof vtkActor.newInstance>;
    lut: ReturnType<typeof vtkColorTransferFunction.newInstance>;
    tube?: VtkTubeFilterLike;
    bounds: [number, number, number, number, number, number];
  }
  const vtpEntries = new Map<number, VtpEntry>();
  let nextVtpId = 1;
  let surfaceOverlayCount = 0;
  const baseActorStates = new Map<
    ReturnType<typeof vtkActor.newInstance>,
    { opacity: number; visible: boolean }
  >();

  function _setBaseGeometryOpacity(opacity: number | null): void {
    type KernelActor = ReturnType<typeof vtkActor.newInstance>;
    const renderer = grw.getRenderer() as unknown as {
      getActors?: () => unknown[];
    };
    const currentVtpActors = new Set(
      Array.from(vtpEntries.values()).map((entry) => entry.actor),
    );
    const isKernelActor = (candidate: unknown): candidate is KernelActor =>
      typeof (candidate as { getProperty?: unknown } | null)?.getProperty ===
      "function";
    const actors = (
      renderer.getActors?.() ??
      Array.from(new Set([actor, ...Array.from(actorPatchNames.keys())]))
    ).filter(isKernelActor);

    for (const a of actors) {
      if (currentVtpActors.has(a)) continue;
      if (a === pickHighlightActor || a === hoverHighlightActor) continue;
      const prop = a.getProperty();
      if (opacity === null) {
        const original = baseActorStates.get(a);
        if (original != null) {
          prop.setOpacity(original.opacity);
          a.setVisibility(original.visible);
        }
      } else {
        if (!baseActorStates.has(a)) {
          baseActorStates.set(a, {
            opacity: prop.getOpacity?.() ?? 1,
            visible: a.getVisibility?.() ?? true,
          });
        }
        prop.setOpacity(opacity);
        a.setVisibility(false);
      }
      a.modified?.();
    }

    if (opacity === null) {
      baseActorStates.clear();
    }
  }

  function _fitVtpCamera(): void {
    if (vtpEntries.size === 0) return;
    const bounds: [number, number, number, number, number, number] = [
      Infinity,
      -Infinity,
      Infinity,
      -Infinity,
      Infinity,
      -Infinity,
    ];
    for (const entry of vtpEntries.values()) {
      const b = entry.bounds;
      bounds[0] = Math.min(bounds[0], b[0]);
      bounds[1] = Math.max(bounds[1], b[1]);
      bounds[2] = Math.min(bounds[2], b[2]);
      bounds[3] = Math.max(bounds[3], b[3]);
      bounds[4] = Math.min(bounds[4], b[4]);
      bounds[5] = Math.max(bounds[5], b[5]);
    }
    if (!bounds.every(Number.isFinite)) return;

    const renderer = grw.getRenderer();
    const camera = renderer.getActiveCamera();
    const [xMin, xMax, yMin, yMax, zMin, zMax] = bounds;
    const cx = (xMin + xMax) / 2;
    const cy = (yMin + yMax) / 2;
    const cz = (zMin + zMax) / 2;
    const span = Math.max(xMax - xMin, yMax - yMin, zMax - zMin, 1);
    const dist = span * 2.2;
    const iso = dist / Math.sqrt(3);
    camera.setPosition(cx + iso, cy - iso, cz + iso);
    camera.setFocalPoint(cx, cy, cz);
    camera.setViewUp(0, 0, 1);
    renderer.resetCameraClippingRange();
    grw.getRenderWindow().render();
  }

  function _buildLut(
    range: [number, number],
  ): ReturnType<typeof vtkColorTransferFunction.newInstance> {
    const lut = vtkColorTransferFunction.newInstance();
    const [lo, hi] = range[0] < range[1] ? range : [0, 1];
    const stops = V4_CFD_COLORMAP.map((hex, i) => {
      const [r, g, b] = hexToRgbFloat(hex);
      const t = i / Math.max(1, V4_CFD_COLORMAP.length - 1);
      return [t, r, g, b] as const;
    });
    for (const [t, r, g, b] of stops) {
      lut.addRGBPoint(lo + t * (hi - lo), r, g, b);
    }
    return lut;
  }

  async function attachVtp(
    url: string,
    kind: "surface" | "streamlines",
    explicitRange?: [number, number],
  ): Promise<VtpAttachHandle> {
    // Lazy import keeps the XML reader chunk out of the initial bundle.
    const [ReaderModule, DataArrayModule] = await Promise.all([
      import("@kitware/vtk.js/IO/XML/XMLPolyDataReader"),
      import("@kitware/vtk.js/Common/Core/DataArray"),
    ]);
    const reader = (
      ReaderModule.default as unknown as { newInstance: () => VtkXMLPolyDataReader }
    ).newInstance();
    await reader.setUrl(url);

    const polyData = reader.getOutputData();
    const pointData = polyData.getPointData();
    const cellData = polyData.getCellData?.();
    type ScalarAssociation = "PointData" | "CellData";
    type ScalarChoice = {
      name: string;
      range: [number, number];
      association: ScalarAssociation;
      fieldData: VtkFieldDataLike;
    };
    const hasRange = (range: [number, number]) =>
      Number.isFinite(range[0]) && Number.isFinite(range[1]) && range[1] > range[0];
    const buildScalarChoice = (
      fieldData: VtkFieldDataLike | undefined,
      association: ScalarAssociation,
    ): ScalarChoice | null => {
      if (!fieldData) return null;
      const uArr = fieldData.getArrayByName("U");
      if (!uArr) return null;
      const ncomp = uArr.getNumberOfComponents();
      if (ncomp === 3) {
        // Vector U · vtk.js mapper has no built-in magnitude mode, so
        // we synthesize a scalar "magU" array, push it onto the field
        // data, and color by that. The original U vector array stays
        // for downstream uses (probes, glyphs, etc.).
        const raw = uArr.getData();
        const n = raw.length / 3;
        const magData = new Float32Array(n);
        let mn = Infinity;
        let mx = -Infinity;
        for (let i = 0; i < n; i++) {
          const ux = raw[3 * i];
          const uy = raw[3 * i + 1];
          const uz = raw[3 * i + 2];
          const m = Math.sqrt(ux * ux + uy * uy + uz * uz);
          magData[i] = m;
          if (m < mn) mn = m;
          if (m > mx) mx = m;
        }

        // Add the synthesized scalar to the polyData field data so
        // the mapper can find it by name. vtk.js exposes ``addArray``
        // on the FieldData base — the type stub doesn't list it.
        const pd = fieldData as unknown as {
          addArray(arr: unknown): number;
        };
        const magArray = (
          DataArrayModule.default as unknown as {
            newInstance: (opts: {
              name: string;
              values: Float32Array;
              numberOfComponents: number;
            }) => unknown;
          }
        ).newInstance({
          name: "magU",
          values: magData,
          numberOfComponents: 1,
        });
        pd.addArray(magArray);
        fieldData.setActiveScalars("magU");
        return {
          name: "magU",
          range: [mn, mx],
          association,
          fieldData,
        };
      }

      // Already a scalar — color by it directly.
      fieldData.setActiveScalars("U");
      return {
        name: "U",
        range: uArr.getRange(0),
        association,
        fieldData,
      };
    };
    const buildSpatialScalarChoice = (
      range: [number, number],
    ): ScalarChoice | null => {
      const pointValues = polyData.getPoints?.()?.getData();
      if (!pointValues || pointValues.length < 3) return null;
      const bounds = polyData.getBounds();
      const spanX = Math.max(1e-9, bounds[1] - bounds[0]);
      const spanZ = Math.max(1e-9, bounds[5] - bounds[4]);
      const n = Math.floor(pointValues.length / 3);
      const values = new Float32Array(n);
      const [lo, hi] = range;

      for (let i = 0; i < n; i++) {
        const xNorm = (pointValues[3 * i] - bounds[0]) / spanX;
        const zNorm = (pointValues[3 * i + 2] - bounds[4]) / spanZ;
        const t = Math.min(1, Math.max(0, 0.08 + 0.84 * xNorm + 0.08 * zNorm));
        values[i] = lo + t * (hi - lo);
      }

      const pd = pointData as unknown as {
        addArray(arr: unknown): number;
      };
      const scalarArray = (
        DataArrayModule.default as unknown as {
          newInstance: (opts: {
            name: string;
            values: Float32Array;
            numberOfComponents: number;
          }) => unknown;
        }
      ).newInstance({
        name: "blueprintU",
        values,
        numberOfComponents: 1,
      });
      pd.addArray(scalarArray);
      pointData.setActiveScalars("blueprintU");
      return {
        name: "blueprintU",
        range,
        association: "PointData",
        fieldData: pointData,
      };
    };
    // Prefer point data when it has real variation; foamToVTK often
    // writes the useful wall-field U on CellData, so fall back there
    // when PointData is present but degenerate.
    const pointScalar = buildScalarChoice(pointData, "PointData");
    const cellScalar = buildScalarChoice(cellData, "CellData");
    let scalarChoice =
      pointScalar && hasRange(pointScalar.range)
        ? pointScalar
        : cellScalar && hasRange(cellScalar.range)
          ? cellScalar
          : pointScalar ?? cellScalar;
    if (explicitRange && (!scalarChoice || !hasRange(scalarChoice.range))) {
      // Physics setup can request a visual blueprint contour even when
      // the VTP's U array is all zero. This scalar is deterministic and
      // geometry-derived; result/post views do not pass explicitRange,
      // so they remain tied to real solver U values.
      scalarChoice = buildSpatialScalarChoice(explicitRange) ?? scalarChoice;
    }
    let scalarName = scalarChoice?.name ?? "";
    let scalarAssociation = scalarChoice?.association ?? null;
    let scalarRange: [number, number] = scalarChoice?.range ?? [0, 1];

    if (explicitRange) {
      scalarRange = explicitRange;
    }

    let renderPolyData = polyData;
    let tube: VtkTubeFilterLike | undefined;
    if (kind === "streamlines" && (polyData.getNumberOfLines?.() ?? 0) > 0) {
      const TubeModule = await import("@kitware/vtk.js/Filters/General/TubeFilter");
      tube = (
        TubeModule.default as unknown as {
          newInstance: (opts: {
            radius: number;
            numberOfSides: number;
            capping: boolean;
          }) => VtkTubeFilterLike;
        }
      ).newInstance({
        radius: 0.018,
        numberOfSides: 8,
        capping: true,
      });
      if (scalarName && scalarAssociation) {
        tube.setInputArrayToProcess(0, scalarName, scalarAssociation, "Scalars");
      }
      tube.setInputData(polyData);
      tube.update();
      renderPolyData = tube.getOutputData();
      if (scalarName && scalarAssociation === "PointData") {
        renderPolyData.getPointData().setActiveScalars(scalarName);
      }
      if (scalarName && scalarAssociation === "CellData") {
        renderPolyData.getCellData?.().setActiveScalars(scalarName);
      }
      renderPolyData.getPointData().modified?.();
      renderPolyData.getCellData?.().modified?.();
      renderPolyData.modified?.();
    }

    const displayRange: [number, number] =
      scalarRange[0] < scalarRange[1] ? scalarRange : [0, 1];
    const bounds = renderPolyData.getBounds();
    const lut = _buildLut(displayRange);
    scalarChoice?.fieldData.modified?.();
    pointData.modified?.();
    cellData?.modified?.();
    polyData.modified?.();
    const mapper = vtkMapper.newInstance();
    mapper.setInputData(
      renderPolyData as Parameters<typeof mapper.setInputData>[0],
    );
    if (scalarName) {
      mapper.setScalarVisibility(true);
      mapper.setLookupTable(lut);
      mapper.setUseLookupTableScalarRange(true);
      mapper.setScalarRange(displayRange[0], displayRange[1]);
      const m = mapper as unknown as {
        setColorModeToMapScalars: () => void;
        setScalarModeToUsePointFieldData: () => void;
        setScalarModeToUseCellFieldData: () => void;
        setColorByArrayName: (name: string) => boolean;
      };
      m.setColorModeToMapScalars();
      if (scalarAssociation === "CellData") {
        m.setScalarModeToUseCellFieldData();
      } else {
        m.setScalarModeToUsePointFieldData();
      }
      m.setColorByArrayName(scalarName);
    } else {
      mapper.setScalarVisibility(false);
    }
    mapper.modified?.();
    (mapper as { update?: () => void }).update?.();

    const actor = vtkActor.newInstance();
    actor.setMapper(mapper);
    if (kind === "streamlines") {
      // TubeFilter gives the tracks real screen-space presence; line
      // width is retained for the non-tube fallback path.
      const prop = actor.getProperty();
      prop.setLineWidth(8);
      prop.setOpacity(1);
      prop.setLighting(false);
    } else {
      // Surface kind · scalar color should read directly; the dimmed
      // base GLB supplies the geometric silhouette under the overlay.
      const prop = actor.getProperty();
      prop.setOpacity(1);
      prop.setLighting(false);
      const coincidentMapper = mapper as unknown as {
        setResolveCoincidentTopologyToPolygonOffset?: () => void;
        setRelativeCoincidentTopologyPolygonOffsetParameters?: (
          factor: number,
          offset: number,
        ) => void;
      };
      coincidentMapper.setResolveCoincidentTopologyToPolygonOffset?.();
      coincidentMapper.setRelativeCoincidentTopologyPolygonOffsetParameters?.(
        -1,
        -1,
      );
      if (surfaceOverlayCount === 0) {
        _setBaseGeometryOpacity(0.06);
      }
      surfaceOverlayCount += 1;
    }
    actor.modified?.();

    const renderer = grw.getRenderer();
    renderer.addActor(actor);
    const id = nextVtpId++;
    const handle: VtpAttachHandle = {
      id,
      url,
      kind,
      scalarRange,
    };
    vtpEntries.set(id, { handle, reader, mapper, actor, lut, tube, bounds });
    const renderWindow = grw.getRenderWindow();
    queueMicrotask(() => {
      _fitVtpCamera();
    });
    window.setTimeout(_fitVtpCamera, 50);
    renderWindow.render();
    return handle;
  }

  function detachVtp(handle: VtpAttachHandle): void {
    const entry = vtpEntries.get(handle.id);
    if (!entry) return;
    try {
      grw.getRenderer().removeActor(entry.actor);
    } catch {
      // Renderer may already be torn down — safe to ignore.
    }
    try {
      entry.actor.delete();
    } catch {
      // delete() is not formally idempotent in vtk.js
    }
    try {
      entry.mapper.delete();
    } catch {}
    try {
      entry.lut.delete();
    } catch {}
    try {
      entry.tube?.delete();
    } catch {}
    try {
      entry.reader.delete();
    } catch {}
    vtpEntries.delete(handle.id);
    if (handle.kind === "surface") {
      surfaceOverlayCount = Math.max(0, surfaceOverlayCount - 1);
      if (surfaceOverlayCount === 0) {
        _setBaseGeometryOpacity(null);
      }
    }
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
      // The actual highlight is now driven by the React layer via
      // setPickHighlightCells (so all sibling triangles sharing the
      // same face_id can be coalesced into a single overlay). The
      // kernel just reports the hit; the React layer looks up the
      // sibling cellIds in the face-index and fires back.
      localHandler({
        patchName,
        cellId,
        worldPosition,
        actor: pickedActor as ReturnType<typeof vtkActor.newInstance>,
      });
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
        // The React layer will call setHoverHighlightCells with
        // the sibling cellIds resolved from the face-index. We
        // hand off the actor so the kernel can extract the
        // triangle vertices when that arrives.
        handler({
          patchName,
          cellId,
          worldPosition,
          actor: pickedActor as ReturnType<typeof vtkActor.newInstance>,
        });
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

  // Precompute face-segment groups for an actor by region-growing
  // BFS over edge-adjacent triangles, only crossing edges whose
  // dihedral angle is smooth (below ~30°). This subsumes pure
  // coplanar grouping:
  //   - Cube: same-face triangles share dihedral=0 (merge), cross-
  //     face triangles share dihedral=90° (split). Result: 6 faces.
  //   - Cylinder side: gmsh's circumferential discretization has
  //     ~360°/N dihedral per segment-step (typically 5–15° for
  //     N≥24). All triangles merge into one smooth segment.
  //   - Cylinder side meeting flat caps: dihedral spike at the
  //     rim (90°) splits side from caps cleanly.
  //
  // Edge keys are built from quantized vertex POSITIONS rather
  // than vertex indices, so the algorithm is robust to vertex
  // duplication at primitive boundaries. Quantization is tight
  // enough (1e-5) to avoid false-merging numerically-near-but-
  // -physically-distinct vertices.
  //
  // For ~3260 LDC triangles this runs in ~3 ms (one-shot,
  // cached). Curved surfaces no longer degrade to singletons.
  // (Dogfood feedback 2026-04-30: cylinder side was unselectable
  // as one face under pure coplanar grouping.)
  function precomputeFaceSegments(
    actor: ReturnType<typeof vtkActor.newInstance>,
  ): void {
    if (coplanarGroups.has(actor)) return;
    const inputData = actor.getMapper()?.getInputData?.();
    if (!inputData) return;
    const polys = inputData.getPolys?.();
    const points = inputData.getPoints?.();
    if (!polys || !points) return;
    const cellData = polys.getData?.();
    const pointArray = points.getData?.();
    if (!cellData || !pointArray) return;

    // Pass 1: walk cellData, compute per-cell normalized normal +
    // record vertex indices in cell-id order. Skip non-triangles
    // (still increment cellId so the index space stays aligned
    // with picker.getCellId()).
    const cellNormals: number[] = []; // flat: cellId*3 + axis
    const cellVerts: number[] = []; // flat: cellId*3 + slot
    let cellCount = 0;
    for (let i = 0; i + 3 < cellData.length; ) {
      const n = cellData[i];
      if (n !== 3) {
        // Push placeholders so cellId space stays contiguous.
        cellNormals.push(0, 0, 0);
        cellVerts.push(-1, -1, -1);
        i += n + 1;
        cellCount++;
        continue;
      }
      const a = cellData[i + 1];
      const b = cellData[i + 2];
      const c = cellData[i + 3];
      i += 4;

      const ax = pointArray[a * 3 + 0],
        ay = pointArray[a * 3 + 1],
        az = pointArray[a * 3 + 2];
      const bx = pointArray[b * 3 + 0],
        by = pointArray[b * 3 + 1],
        bz = pointArray[b * 3 + 2];
      const cx = pointArray[c * 3 + 0],
        cy = pointArray[c * 3 + 1],
        cz = pointArray[c * 3 + 2];

      const ux = bx - ax,
        uy = by - ay,
        uz = bz - az;
      const vx = cx - ax,
        vy = cy - ay,
        vz = cz - az;
      let nx = uy * vz - uz * vy;
      let ny = uz * vx - ux * vz;
      let nz = ux * vy - uy * vx;
      const len = Math.sqrt(nx * nx + ny * ny + nz * nz);
      if (len > 0) {
        nx /= len;
        ny /= len;
        nz /= len;
      }
      cellNormals.push(nx, ny, nz);
      cellVerts.push(a, b, c);
      cellCount++;
    }

    // Pass 2: build position-quantized edge → cellIds map. Edge
    // key uses sorted quantized endpoint coords, so two triangles
    // that share a physical edge but use different vertex INDICES
    // (because the GLB primitive boundary duplicated the vertex)
    // still hash to the same edge.
    const POS_TOL = 1e5;
    const quantize = (idx: number): string => {
      const x = pointArray[idx * 3 + 0];
      const y = pointArray[idx * 3 + 1];
      const z = pointArray[idx * 3 + 2];
      return (
        Math.round(x * POS_TOL) +
        "/" +
        Math.round(y * POS_TOL) +
        "/" +
        Math.round(z * POS_TOL)
      );
    };
    const edgeKey = (qa: string, qb: string): string =>
      qa < qb ? qa + "|" + qb : qb + "|" + qa;
    const edgeMap = new Map<string, number[]>();
    for (let cid = 0; cid < cellCount; cid++) {
      const a = cellVerts[cid * 3 + 0];
      const b = cellVerts[cid * 3 + 1];
      const c = cellVerts[cid * 3 + 2];
      if (a < 0) continue; // skipped non-triangle
      const qa = quantize(a),
        qb = quantize(b),
        qc = quantize(c);
      for (const k of [edgeKey(qa, qb), edgeKey(qb, qc), edgeKey(qc, qa)]) {
        let list = edgeMap.get(k);
        if (!list) {
          list = [];
          edgeMap.set(k, list);
        }
        list.push(cid);
      }
    }

    // Pass 3: BFS from each unvisited cell, traversing edges
    // whose adjacent normals form a smooth dihedral. Threshold
    // 30° (cos ≈ 0.866) keeps cube faces split (90° edges fail)
    // while merging typical CAD discretization (≤15° per step
    // on circular features). The check is signed dot (NOT |dot|)
    // — Codex e844a6f review P2: an absolute-value check would
    // flood across opposite-facing folds where two normals point
    // in opposite directions (dot ≈ -1) but |dot| ≈ 1, merging a
    // genuinely sharp re-entrant crease into one segment.
    // GLTFImporter preserves gmsh's outward winding, so the
    // self-back-to-back fan case the |dot| variant guarded
    // against does not occur in practice; the trade was anti-
    // correctness.
    const COS_THRESHOLD = Math.cos((30 * Math.PI) / 180);
    const segmentOfCell = new Int32Array(cellCount).fill(-1);
    const segmentLists: number[][] = [];
    const groups = new Map<number, number[]>();

    for (let start = 0; start < cellCount; start++) {
      if (segmentOfCell[start] !== -1) continue;
      const a = cellVerts[start * 3 + 0];
      if (a < 0) {
        // Non-triangle placeholder: own group.
        const seg = [start];
        segmentLists.push(seg);
        groups.set(start, seg);
        segmentOfCell[start] = segmentLists.length - 1;
        continue;
      }
      const segId = segmentLists.length;
      const seg: number[] = [];
      segmentLists.push(seg);
      // Use array-based queue with head pointer (shift() is O(n)).
      const queue: number[] = [start];
      let head = 0;
      segmentOfCell[start] = segId;
      while (head < queue.length) {
        const cell = queue[head++];
        seg.push(cell);
        const nx = cellNormals[cell * 3 + 0];
        const ny = cellNormals[cell * 3 + 1];
        const nz = cellNormals[cell * 3 + 2];
        const va = cellVerts[cell * 3 + 0];
        const vb = cellVerts[cell * 3 + 1];
        const vc = cellVerts[cell * 3 + 2];
        const qa = quantize(va),
          qb = quantize(vb),
          qc = quantize(vc);
        const edges = [edgeKey(qa, qb), edgeKey(qb, qc), edgeKey(qc, qa)];
        for (const k of edges) {
          const neighbors = edgeMap.get(k);
          if (!neighbors) continue;
          for (const nb of neighbors) {
            if (nb === cell || segmentOfCell[nb] !== -1) continue;
            const mx = cellNormals[nb * 3 + 0];
            const my = cellNormals[nb * 3 + 1];
            const mz = cellNormals[nb * 3 + 2];
            const dot = nx * mx + ny * my + nz * mz;
            if (dot >= COS_THRESHOLD) {
              segmentOfCell[nb] = segId;
              queue.push(nb);
            }
          }
        }
      }
      // Bind every cellId in the segment to the same list ref.
      for (const cid of seg) groups.set(cid, seg);
    }
    coplanarGroups.set(actor, groups);
  }

  function getCoplanarSiblings(
    actor: ReturnType<typeof vtkActor.newInstance>,
    cellId: number,
  ): number[] {
    precomputeFaceSegments(actor);
    return coplanarGroups.get(actor)?.get(cellId) ?? [cellId];
  }

  // Replace the given highlight overlay (pick OR hover) with the
  // supplied triangles. ``trianglesXyz`` is a flat array of N*9 floats
  // (3 vertices per triangle, no shared indices). Lazy-allocates the
  // polyData/mapper/actor on first call; subsequent calls reallocate
  // the points + cell arrays only when the triangle count changes
  // (vtk.js needs a fresh array if the size differs from the
  // previously-bound one).
  function applyHighlight(
    trianglesXyz: Float32Array,
    mode: "selected" | "hover",
  ): void {
    const renderer = grw.getRenderer();
    const isSelected = mode === "selected";
    const triCount = trianglesXyz.length / 9;
    if (triCount === 0) {
      // No triangles — hide the overlay.
      const a = isSelected ? pickHighlightActor : hoverHighlightActor;
      if (a) {
        a.setVisibility(false);
        grw.getRenderWindow().render();
      }
      return;
    }

    let polyData = isSelected ? pickHighlightPolyData : hoverHighlightPolyData;
    let mapper = isSelected ? pickHighlightMapper : hoverHighlightMapper;
    let actor = isSelected ? pickHighlightActor : hoverHighlightActor;

    if (!polyData) {
      polyData = vtkPolyData.newInstance();
      polyData.setPoints(vtkPoints.newInstance());
      polyData.setPolys(vtkCellArray.newInstance());
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
      // V4 Phase R4 (Codex R3 C-1 closure): colors now flow from the
      // V4_PALETTE SSOT via hexToRgbFloat, not hard-coded RGB tuples.
      // The semantic intent is unchanged (committed=signal-brand,
      // hover=selection-active) but a future palette tweak now
      // propagates here automatically.
      if (isSelected) {
        const [r, g, b] = PICK_HIGHLIGHT_RGB;
        prop.setColor(r, g, b);
        prop.setOpacity(1.0);
        prop.setAmbient(0.85);
        prop.setDiffuse(0.15);
      } else {
        const [r, g, b] = HOVER_HIGHLIGHT_RGB;
        prop.setColor(r, g, b);
        // Opacity <1 so an underlying committed pick (different color)
        // remains readable when hover crosses back over it.
        prop.setOpacity(0.85);
        prop.setAmbient(0.85);
        prop.setDiffuse(0.15);
      }
      prop.setRepresentation(2); // SURFACE
      renderer.addActor(actor);
      if (isSelected) pickHighlightActor = actor;
      else hoverHighlightActor = actor;
    }

    // (Re-)bind the points and cells. We always replace the arrays
    // when the triangle count changes; for the same triangle count
    // we'd still need to update the data + ping modified, so just
    // always replace — the cost is N*36 bytes for points + N*16 for
    // indices, trivial at our scales.
    polyData.getPoints().setData(trianglesXyz);
    const cellData = new Uint32Array(triCount * 4);
    for (let i = 0; i < triCount; i++) {
      cellData[i * 4 + 0] = 3;
      cellData[i * 4 + 1] = i * 3 + 0;
      cellData[i * 4 + 2] = i * 3 + 1;
      cellData[i * 4 + 3] = i * 3 + 2;
    }
    polyData.getPolys().setData(cellData);
    polyData.getPoints().modified();
    polyData.getPolys().modified();
    polyData.modified();
    actor.setVisibility(true);
    grw.getRenderWindow().render();
  }

  // Helper used by both the kernel-internal pick handlers and the
  // public setPick/HoverHighlightCells API: build the triangle blob
  // for a list of cellIds against a single actor's polyData.
  function buildTriangleBlob(
    actor: ReturnType<typeof vtkActor.newInstance>,
    cellIds: number[],
  ): Float32Array {
    const result = new Float32Array(cellIds.length * 9);
    let outOffset = 0;
    for (const cellId of cellIds) {
      const tri = extractTriangleVertices(actor, cellId);
      if (!tri) continue;
      result.set(tri, outOffset);
      outOffset += 9;
    }
    // Trim if some cellIds didn't resolve.
    return outOffset === result.length
      ? result
      : result.slice(0, outOffset);
  }

  function setPickHighlightCells(
    actor: ReturnType<typeof vtkActor.newInstance>,
    cellIds: number[],
  ): void {
    if (cellIds.length === 0) {
      clearPickHighlight();
      return;
    }
    const tris = buildTriangleBlob(actor, cellIds);
    applyHighlight(tris, "selected");
  }

  function setHoverHighlightCells(
    actor: ReturnType<typeof vtkActor.newInstance>,
    cellIds: number[],
  ): void {
    if (cellIds.length === 0) {
      clearHoverHighlight();
      return;
    }
    const tris = buildTriangleBlob(actor, cellIds);
    applyHighlight(tris, "hover");
  }

  /** V4 Phase C-R5 · getPatchCentroid implementation. */
  function getPatchCentroid(
    name: string,
  ): [number, number, number] | null {
    let target: ReturnType<typeof vtkActor.newInstance> | undefined;
    actorPatchNames.forEach((patchName, a) => {
      if (target) return;
      if (patchName === name) target = a;
    });
    if (!target) return null;
    // actor.getBounds() returns [xmin, xmax, ymin, ymax, zmin, zmax].
    // The bounds midpoint is the cheapest valid annotation anchor.
    const b = (target as unknown as {
      getBounds?: () => number[];
    }).getBounds?.();
    if (!b || b.length < 6) return null;
    // Reject degenerate or uninitialized bounds (vtk returns
    // [+inf,-inf,+inf,-inf,+inf,-inf] before any data is loaded).
    if (!Number.isFinite(b[0]) || b[1] < b[0]) return null;
    return [(b[0] + b[1]) / 2, (b[2] + b[3]) / 2, (b[4] + b[5]) / 2];
  }

  /** V4 Phase C-R5 · world → CSS pixel projection.
   *
   *  Uses vtkCoordinate with COORDINATE_SYSTEM=WORLD to drive the
   *  active renderer's camera matrices, then converts the resulting
   *  vtk-display coords (origin bottom-left, **framebuffer** pixels)
   *  to CSS px (origin top-left, **CSS** pixels) so the React overlay
   *  can drop a <div> at the returned (x,y) without further math.
   *
   *  R5.1 (Codex finding) · HiDPI fix: vtk's display coords are in
   *  framebuffer (device) pixels — they're already multiplied by
   *  `devicePixelRatio`. Dividing back to CSS pixels matches what
   *  `getBoundingClientRect()` measures, so the overlay <div> lands
   *  on the right place under Retina (DPR=2) and standard displays.
   *
   *  `behind` is now a real behind-camera test using the camera's
   *  view direction · (point − camera_pos) dot product. Negative dot
   *  = point is behind the camera plane (vtkCoordinate would project
   *  it to nonsensical screen coords, often wrapping around). The
   *  separate `offscreen` field reports points that are in front of
   *  the camera but project outside the [0,W]×[0,H] container box;
   *  callers can clamp those to an edge with a real leader instead
   *  of hiding the annotation entirely. */
  function worldToScreen(
    world: [number, number, number],
  ): {
    x: number;
    y: number;
    behind: boolean;
    offscreen: boolean;
  } | null {
    const container = grw.getContainer();
    if (!container) return null;
    const rect = container.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return null;
    const renderer = grw.getRenderer();

    // Real behind-camera detection · camera.getDirectionOfProjection
    // is the unit vector pointing from camera toward focal point.
    // (point − camera_pos) · direction < 0  ⇒ point is behind camera.
    let behind = false;
    try {
      const cam = (renderer as unknown as {
        getActiveCamera?: () => {
          getPosition?: () => number[];
          getDirectionOfProjection?: () => number[];
        };
      }).getActiveCamera?.();
      const pos = cam?.getPosition?.();
      const dir = cam?.getDirectionOfProjection?.();
      if (pos && dir && pos.length >= 3 && dir.length >= 3) {
        const dx = world[0] - pos[0];
        const dy = world[1] - pos[1];
        const dz = world[2] - pos[2];
        const dot = dx * dir[0] + dy * dir[1] + dz * dir[2];
        behind = dot <= 0;
      }
    } catch {
      // If camera API differs in some vtk.js minor version, fall back
      // to !behind (we'll still surface offscreen below).
      behind = false;
    }

    const coord = vtkCoordinate.newInstance();
    coord.setCoordinateSystemToWorld();
    coord.setValue([world[0], world[1], world[2]]);
    let display: number[];
    try {
      display = coord.getComputedDisplayValue(renderer);
    } catch {
      return null;
    }

    // Framebuffer px → CSS px · divide by DPR (R5.1 Codex finding).
    const dpr = typeof window !== "undefined" ? window.devicePixelRatio || 1 : 1;
    const cssXfb = display[0] / dpr;
    const cssYfb = display[1] / dpr;
    // vtk origin bottom-left → CSS origin top-left flip.
    const cssX = cssXfb;
    const cssY = rect.height - cssYfb;

    // Mutually exclusive with `behind`: a behind-camera point can
    // project anywhere on the canvas via vtkCoordinate (the matrix
    // doesn't care), so we don't redundantly tag it as `offscreen`.
    // The React layer only ever consumes `offscreen` to clamp leader
    // endpoints — it never wants to clamp a behind-camera anchor.
    const offscreen =
      !behind &&
      (cssX < 0 || cssX > rect.width || cssY < 0 || cssY > rect.height);

    return { x: cssX, y: cssY, behind, offscreen };
  }

  /** V4 Phase C-R3 implementation · scan actorPatchNames for a match,
   *  build the cellIds = [0..numCells-1] range from the actor's bound
   *  polyData, and dispatch to set{Pick,Hover}HighlightCells. Returns
   *  the cell count actually highlighted (0 = patch_name not found
   *  or actor has no cells / no mapper). */
  function highlightPatchByName(
    name: string | null,
    kind: "pick" | "hover",
  ): number {
    if (name === null) {
      if (kind === "pick") clearPickHighlight();
      else clearHoverHighlight();
      return 0;
    }
    let targetActor: ReturnType<typeof vtkActor.newInstance> | undefined;
    actorPatchNames.forEach((patchName, a) => {
      if (targetActor) return;
      if (patchName === name) targetActor = a;
    });
    if (!targetActor) {
      if (kind === "pick") clearPickHighlight();
      else clearHoverHighlight();
      return 0;
    }
    // actor.getMapper().getInputData() can be undefined briefly during
    // GLTFImporter binding; guard so a fast hover doesn't throw.
    const m = (targetActor as unknown as {
      getMapper?: () => {
        getInputData?: () =>
          | { getNumberOfCells?: () => number }
          | null
          | undefined;
      };
    }).getMapper?.();
    const polyData = m?.getInputData?.();
    const numCells = polyData?.getNumberOfCells?.() ?? 0;
    if (numCells === 0) {
      if (kind === "pick") clearPickHighlight();
      else clearHoverHighlight();
      return 0;
    }
    const cellIds = new Array<number>(numCells);
    for (let i = 0; i < numCells; i++) cellIds[i] = i;
    if (kind === "pick") setPickHighlightCells(targetActor, cellIds);
    else setHoverHighlightCells(targetActor, cellIds);
    return numCells;
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

  function setCameraPreset(preset: "front" | "top" | "iso"): void {
    const renderer = grw.getRenderer();
    const camera = renderer.getActiveCamera();
    // Derive a sensible viewing distance from the current scene bbox.
    // If no actors are attached yet, fall back to unit distance — the
    // subsequent resetCamera() pass refits.
    const bounds = renderer.computeVisiblePropBounds();
    const [xMin, xMax, yMin, yMax, zMin, zMax] = bounds;
    const cx = (xMin + xMax) / 2;
    const cy = (yMin + yMax) / 2;
    const cz = (zMin + zMax) / 2;
    const dx = xMax - xMin;
    const dy = yMax - yMin;
    const dz = zMax - zMin;
    // Distance = 2× the largest extent, clamped to a minimum so empty
    // scenes still produce a usable camera.
    const span = Math.max(dx, dy, dz, 1);
    const dist = span * 2;
    if (preset === "front") {
      camera.setPosition(cx, cy - dist, cz);
      camera.setFocalPoint(cx, cy, cz);
      camera.setViewUp(0, 0, 1);
    } else if (preset === "top") {
      camera.setPosition(cx, cy, cz + dist);
      camera.setFocalPoint(cx, cy, cz);
      camera.setViewUp(0, 1, 0);
    } else {
      // iso: equal contributions on +X +Y +Z
      const iso = dist / Math.sqrt(3);
      camera.setPosition(cx + iso, cy - iso, cz + iso);
      camera.setFocalPoint(cx, cy, cz);
      camera.setViewUp(0, 0, 1);
    }
    renderer.resetCameraClippingRange();
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
    // B2.5 · clean up any VTP attachments. Walk a copy of the entries
    // so detachVtp can mutate the map without throwing.
    for (const handle of Array.from(vtpEntries.values()).map((e) => e.handle)) {
      try {
        detachVtp(handle);
      } catch {
        // see above
      }
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
    attachVtp,
    detachVtp,
    resetCamera,
    setCameraPreset,
    setPickHandler,
    setHoverHandler,
    setPickHighlightCells,
    setHoverHighlightCells,
    getCoplanarSiblings,
    highlightPatchByName,
    getPatchCentroid,
    worldToScreen,
    clearPickHighlight,
    clearHoverHighlight,
    dispose,
  };
}
