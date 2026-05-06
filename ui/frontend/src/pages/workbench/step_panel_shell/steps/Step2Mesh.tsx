// Step 2 · Mesh — wired body (DEC-V61-096 spec_v2 §E Step 5).
//
// Surfaces the gmsh+sHM mesh-mode form (beginner / power) and registers
// a mesh-generation action with the shell so the StepNavigation
// [AI 处理] button drives it. On success the polyMesh lands at
// <case>/constant/polyMesh/ and the center-pane Viewport (driven by
// Step 2's viewportConfig) re-fetches /api/cases/<id>/mesh/render.

import { useCallback, useEffect, useState } from "react";

import { api, ApiError } from "@/api/client";
import type {
  BoxRefinementZone,
  MeshRefinementZone,
  MeshRejectionDetail,
  MeshRequestMode,
  MeshSizingField,
  MeshSuccessResponse,
  RefinementLevel,
  SphereRefinementZone,
} from "@/types/mesh_imported";
import {
  REFINEMENT_LEVEL_MAX,
  REFINEMENT_LEVEL_MIN,
} from "@/types/mesh_imported";
import type {
  PatchPrismConfig,
  PrismLayersRejectionDetail,
  PrismLayersSuccessResponse,
} from "@/types/mesh_prism_layers";
import {
  PRISM_EXPANSION_RATIO_MAX,
  PRISM_EXPANSION_RATIO_MIN,
  PRISM_MAX_LAYER_COUNT,
} from "@/types/mesh_prism_layers";

import { MeshQualityCard } from "../MeshQualityCard";
import type { StepTaskPanelProps } from "../types";

// DEC-V61-135 (N2.1): empty sizing-field literal for resetting the
// advanced panel back to "preset only".
const EMPTY_SIZING: MeshSizingField = {
  base_lc: null,
  min_lc: null,
  max_lc: null,
  curvature_target_size: null,
  proximity_layers: null,
};

// DEC-V61-136 (N2.2): factory helpers for new zones. Defaults give a
// non-zero extent so the "Add zone" click immediately has a valid
// payload — engineer can edit numbers in place.
function makeBoxZone(): BoxRefinementZone {
  return {
    geometry: "box",
    bbox: [0.0, 0.0, 0.0, 1.0, 1.0, 1.0],
    level: 2,
  };
}
function makeSphereZone(): SphereRefinementZone {
  return {
    geometry: "sphere",
    center: [0.5, 0.5, 0.5],
    radius: 0.1,
    level: 2,
  };
}

const REJECTION_HINTS: Record<string, string> = {
  cell_cap_exceeded:
    "Coarsen the geometry or pick a different mesh tier. The 50M-cell hard cap is a resource guard, not a quality threshold.",
  gmsh_diverged:
    "gmsh failed to converge on this geometry. Verify the STL is watertight and free of self-intersections in your CAD.",
  gmshToFoam_failed:
    "The OpenFOAM container could not convert the mesh. Confirm cfd-openfoam is running (docker ps | grep cfd-openfoam).",
  source_not_imported:
    "This case has no triSurface/ STL to mesh — only imported cases can use the gmsh path.",
  refinement_zone_invalid:
    "A refinement zone has no overlap with the case geometry. Adjust the bbox or sphere center so it intersects the imported STL bounding box.",
  // DEC-V61-137 (N2.3): prism-layer rejection hints.
  polyMesh_not_ready:
    "Run the mesh stage first — prism layers operate on the existing constant/polyMesh produced by gmsh.",
  patch_not_found:
    "The patch name does not match any patch in constant/polyMesh/boundary. Check the imported case's declared patches and retry.",
  snappy_diverged:
    "snappyHexMesh did not run cleanly. Inspect the host log (case_dir/log.snappyHexMesh) for the cause.",
  snappy_addlayers_did_not_converge:
    "snappyHexMesh ran but no layers were actually added. Reduce first_cell_height or expansion_ratio, or pick a different patch.",
  snappy_container_failed:
    "The cfd-openfoam container could not run snappyHexMesh. Confirm cfd-openfoam is running and reachable.",
};

// DEC-V61-137 (N2.3): default prism config for the form. First-cell
// height defaults to 1e-4 (typical wall-bounded RANS y+ ~ 1 starting
// point); engineer must edit before clicking apply.
const DEFAULT_PRISM_CONFIG: PatchPrismConfig = {
  patch: "walls",
  first_cell_height: 1.0e-4,
  expansion_ratio: 1.2,
  num_layers: 5,
};

export function Step2Mesh({
  caseId,
  onStepComplete,
  onStepError,
  registerAiAction,
}: StepTaskPanelProps) {
  const [meshMode, setMeshMode] = useState<MeshRequestMode>("beginner");
  const [response, setResponse] = useState<MeshSuccessResponse | null>(null);
  const [rejection, setRejection] = useState<MeshRejectionDetail | null>(null);
  const [networkError, setNetworkError] = useState<string | null>(null);
  // DEC-V61-135 (N2.1): structured sizing field. Collapsed by default;
  // expanded when the engineer toggles the disclosure. All five fields
  // are optional — null = "fall back to mesh_mode preset". sizingFieldError
  // surfaces client-side validation (min ≤ base ≤ max) before the
  // backend rejects with 422.
  const [sizingFieldOpen, setSizingFieldOpen] = useState(false);
  const [sizingField, setSizingField] = useState<MeshSizingField>(EMPTY_SIZING);
  const [sizingFieldError, setSizingFieldError] = useState<string | null>(null);
  // DEC-V61-136 (N2.2): refinement zones repeater. Collapsed by default;
  // empty list = behavior identical to N2.1 (api client omits body
  // attribute). zonesError surfaces client-side validation (zero-extent
  // bbox / negative radius) before the backend rejects with 422.
  const [zonesOpen, setZonesOpen] = useState(false);
  const [zones, setZones] = useState<MeshRefinementZone[]>([]);
  const [zonesError, setZonesError] = useState<string | null>(null);
  // DEC-V61-137 (N2.3): prism-layer config + apply state. Engineer
  // explicit click — NOT bound to the [AI 处理] action — because
  // prism layers refresh the existing polyMesh and are an additive
  // step the engineer chooses after the gmsh stage succeeds.
  const [prismOpen, setPrismOpen] = useState(false);
  const [prismConfig, setPrismConfig] = useState<PatchPrismConfig>(
    DEFAULT_PRISM_CONFIG,
  );
  const [prismResponse, setPrismResponse] =
    useState<PrismLayersSuccessResponse | null>(null);
  const [prismRejection, setPrismRejection] =
    useState<PrismLayersRejectionDetail | null>(null);
  const [prismError, setPrismError] = useState<string | null>(null);
  const [prismApplying, setPrismApplying] = useState(false);
  // V127: bumped on every successful mesh regeneration so the
  // MeshQualityCard child re-fetches against the new polyMesh. Also
  // listens for ai-coach:proposal-applied (regenerate_mesh tool) so
  // an AI-driven re-mesh refreshes the gauges without remounting.
  const [meshGenSeq, setMeshGenSeq] = useState(0);
  // R1 P1 (Codex 86gs): track in-flight gmsh runs so the prism
  // button can refuse to start while a mesh op is already mutating
  // constant/polyMesh. Without this guard, an engineer on a
  // restored-from-disk case could click [AI 处理] (gmsh remesh) AND
  // "Apply prism layers" simultaneously, sending two concurrent
  // POSTs that both rewrite polyMesh — whichever finishes last
  // silently wins.
  const [meshInFlight, setMeshInFlight] = useState(false);

  // Register the mesh-generation action with the shell. The shell's
  // wrapped onAiProcess sets aiInFlight + captures errors; this body
  // owns the form state + structured rejection panel.
  const triggerMesh = useCallback(async () => {
    setRejection(null);
    setNetworkError(null);
    setSizingFieldError(null);
    setZonesError(null);
    // V136 R1 P2 (Codex CRS): blur the focused element before validation.
    // ZoneNumberInput keeps a local draft string for partial / negative
    // edits; if the engineer types "" / "-" / "." (draft-only states
    // that never commit) and then clicks [AI 处理] without leaving the
    // field, the visible text would diverge from parent zones state.
    // Forcing blur fires each input's onBlur, which clears the draft so
    // the displayed value snaps back to the canonical committed
    // number — what gets submitted is what the engineer now sees.
    if (typeof document !== "undefined") {
      const active = document.activeElement;
      if (active instanceof HTMLElement) {
        active.blur();
      }
    }
    // DEC-V61-135: client-side ordering check before the round-trip.
    // The backend re-validates; this just gives instant feedback.
    if (sizingFieldOpen) {
      const { base_lc, min_lc, max_lc } = sizingField;
      if (min_lc != null && max_lc != null && min_lc > max_lc) {
        setSizingFieldError("min_lc must be ≤ max_lc");
        onStepError("sizing-field validation: min_lc > max_lc");
        return;
      }
      if (min_lc != null && base_lc != null && min_lc > base_lc) {
        setSizingFieldError("min_lc must be ≤ base_lc");
        onStepError("sizing-field validation: min_lc > base_lc");
        return;
      }
      if (base_lc != null && max_lc != null && base_lc > max_lc) {
        setSizingFieldError("base_lc must be ≤ max_lc");
        onStepError("sizing-field validation: base_lc > max_lc");
        return;
      }
    }
    // DEC-V61-136 (N2.2): client-side zone shape validation. Backend
    // re-validates extent + AABB overlap; this just gives instant
    // feedback for the obvious mistakes. Validate every configured
    // zone regardless of disclosure state — same rationale as the
    // send-on-length>0 fix below: zones list is the data, panel
    // open/closed is UX state only.
    for (let i = 0; i < zones.length; i++) {
      const z = zones[i];
      if (z.geometry === "box") {
        const [xmin, ymin, zmin, xmax, ymax, zmax] = z.bbox;
        if (!(xmin < xmax && ymin < ymax && zmin < zmax)) {
          const msg = `zones[${i}] (box) has zero or inverted extent`;
          setZonesError(msg);
          onStepError(`zone validation: ${msg}`);
          return;
        }
      } else if (z.geometry === "sphere") {
        if (!(z.radius > 0)) {
          const msg = `zones[${i}] (sphere) radius must be > 0`;
          setZonesError(msg);
          onStepError(`zone validation: ${msg}`);
          return;
        }
      }
    }
    setMeshInFlight(true);
    try {
      // Pass sizingField only when the panel is open and at least one
      // field is non-null; otherwise the api client omits the body
      // attribute entirely (preserves V124/V125-era wire shape).
      // V136 R0 P2 (Codex CRS): zones are explicit data (length > 0 =
      // engineer added refinement intent); the disclosure state is
      // UX-only. Sending zones must NOT depend on `zonesOpen` —
      // otherwise collapsing the panel before mesh-run would silently
      // drop configured zones with no indication. The summary still
      // shows the count, so the engineer's mental model is "zones are
      // configured" regardless of disclosure state.
      const r = await api.meshImported(
        caseId,
        meshMode,
        sizingFieldOpen ? sizingField : null,
        zones.length > 0 ? zones : null,
      );
      setResponse(r);
      // V127 R4 P2: api.meshImported now dispatches mesh:mutated which
      // the MeshQualityCard module-level listener handles, so explicit
      // invalidateMeshQualityCache() is no longer needed here. Still
      // bump meshGenSeq so the in-mounted card re-fetches against the
      // new polyMesh (the cache is keyed on caseId and the entry for
      // this case has just been cleared by the dispatched event).
      setMeshGenSeq((s) => s + 1);
      onStepComplete();
    } catch (e) {
      // Codex R0 P2 #2: distinguish three error shapes:
      //   1. structured pipeline rejection · ApiError with
      //      e.detail = {reason, failing_check}
      //   2. FastAPI request-validation 422 · ApiError with
      //      e.detail = [{loc, msg, type, ...}, ...]   (array)
      //   3. network / non-ApiError · plain Error
      // Old code conflated #2 with #1 and rendered "mesh rejected:
      // undefined" + a blank rejection panel. The sizing-field surface
      // makes #2 a routine path (e.g. base_lc=0 / proximity_layers=11),
      // so route 422s to networkError instead of the rejection panel.
      if (
        e instanceof ApiError &&
        e.detail &&
        typeof e.detail === "object" &&
        !Array.isArray(e.detail) &&
        "failing_check" in (e.detail as Record<string, unknown>)
      ) {
        const detail = e.detail as MeshRejectionDetail;
        setRejection(detail);
        onStepError(`mesh rejected: ${detail.failing_check}`);
      } else if (e instanceof ApiError && Array.isArray(e.detail)) {
        const issues = (
          e.detail as Array<{ loc?: unknown[]; msg?: string }>
        )
          .map((d) => {
            const loc = Array.isArray(d.loc)
              ? d.loc.filter((p) => typeof p !== "number").join(".")
              : "";
            return loc ? `${loc}: ${d.msg ?? ""}` : (d.msg ?? "");
          })
          .filter(Boolean)
          .join(" · ");
        const msg = `request validation failed${issues ? ` — ${issues}` : ""}`;
        setNetworkError(msg);
        onStepError(msg);
      } else {
        const msg = e instanceof Error ? e.message : String(e);
        setNetworkError(msg);
        onStepError(msg);
      }
      // Re-throw so the shell's aiInFlight wrapper sees the failure
      // and surfaces aiErrorMessage in the StatusStrip.
      throw e;
    } finally {
      setMeshInFlight(false);
    }
  }, [
    caseId,
    meshMode,
    onStepComplete,
    onStepError,
    sizingField,
    sizingFieldOpen,
    zones,
    // zonesOpen intentionally omitted from deps — disclosure state
    // does not gate validation or send (V136 R0 P2 fix).
  ]);

  useEffect(() => {
    registerAiAction(triggerMesh);
    return () => registerAiAction(null);
  }, [registerAiAction, triggerMesh]);

  // DEC-V61-137 (N2.3): explicit prism-apply handler. Distinct from
  // triggerMesh because prism layers depend on a successful mesh run
  // and require engineer-driven explicit confirmation (additive step,
  // not part of the [AI 处理] gmsh kick-off).
  const applyPrismLayers = useCallback(async () => {
    setPrismRejection(null);
    setPrismError(null);
    // R1 P1 (Codex 86gs): refuse to start if a gmsh remesh is already
    // in flight. Both routes mutate constant/polyMesh and neither
    // backend takes a case_lock, so concurrent requests would race —
    // whichever finishes last silently wins. Make the contract
    // explicit at the click handler.
    if (meshInFlight) {
      const msg =
        "mesh stage is currently running — wait for it to finish before applying prism layers";
      setPrismError(msg);
      onStepError(`prism validation: ${msg}`);
      return;
    }
    if (typeof document !== "undefined") {
      const active = document.activeElement;
      if (active instanceof HTMLElement) active.blur();
    }
    // Client-side defensive validation. Backend re-validates.
    if (!prismConfig.patch || prismConfig.patch.length === 0) {
      const msg = "patch name required";
      setPrismError(msg);
      onStepError(`prism validation: ${msg}`);
      return;
    }
    if (!(prismConfig.first_cell_height > 0)) {
      const msg = "first_cell_height must be > 0";
      setPrismError(msg);
      onStepError(`prism validation: ${msg}`);
      return;
    }
    if (
      prismConfig.expansion_ratio < PRISM_EXPANSION_RATIO_MIN ||
      prismConfig.expansion_ratio > PRISM_EXPANSION_RATIO_MAX
    ) {
      const msg = `expansion_ratio must be in [${PRISM_EXPANSION_RATIO_MIN}, ${PRISM_EXPANSION_RATIO_MAX}]`;
      setPrismError(msg);
      onStepError(`prism validation: ${msg}`);
      return;
    }
    if (
      !Number.isInteger(prismConfig.num_layers) ||
      prismConfig.num_layers < 1 ||
      prismConfig.num_layers > PRISM_MAX_LAYER_COUNT
    ) {
      const msg = `num_layers must be an integer in [1, ${PRISM_MAX_LAYER_COUNT}]`;
      setPrismError(msg);
      onStepError(`prism validation: ${msg}`);
      return;
    }
    setPrismApplying(true);
    try {
      const r = await api.meshPrismLayers(caseId, [prismConfig]);
      setPrismResponse(r);
      setMeshGenSeq((s) => s + 1);
    } catch (e) {
      if (
        e instanceof ApiError &&
        e.detail &&
        typeof e.detail === "object" &&
        !Array.isArray(e.detail) &&
        "failing_check" in (e.detail as Record<string, unknown>)
      ) {
        const detail = e.detail as PrismLayersRejectionDetail;
        setPrismRejection(detail);
        onStepError(`prism rejected: ${detail.failing_check}`);
      } else {
        const msg = e instanceof Error ? e.message : String(e);
        setPrismError(msg);
        onStepError(msg);
      }
    } finally {
      setPrismApplying(false);
    }
  }, [caseId, meshInFlight, onStepError, prismConfig]);

  // V127: re-fetch the mesh-quality gauges when the AI coach applies a
  // regenerate_mesh proposal (V125 lifecycle). The same custom event
  // PatchClassificationPanel listens to.
  useEffect(() => {
    if (!caseId) return;
    const onProposalApplied = (e: Event) => {
      const evt = e as CustomEvent<{ caseId?: string; tool?: string }>;
      if (
        evt.detail?.caseId === caseId &&
        evt.detail?.tool === "regenerate_mesh"
      ) {
        setMeshGenSeq((s) => s + 1);
      }
    };
    window.addEventListener("ai-coach:proposal-applied", onProposalApplied);
    return () => {
      window.removeEventListener(
        "ai-coach:proposal-applied",
        onProposalApplied,
      );
    };
  }, [caseId]);

  return (
    <div className="space-y-3 p-3 text-[12px]" data-testid="step2-mesh-body">
      <h2 className="text-sm font-mono uppercase tracking-wider text-surface-200">
        Step 2 · Mesh
      </h2>
      <p className="text-surface-400">
        Generate the polyMesh via gmsh + sHM. Click [AI 处理] in the
        navigation row below to run gmsh on the imported STL — the
        request stays open for ~30–300 s.
      </p>

      <fieldset className="border-0 p-0">
        <legend className="mb-2 block text-[10px] font-mono uppercase tracking-wider text-surface-500">
          Mesh sizing tier
        </legend>
        <div className="flex flex-col gap-2">
          <ModeOption
            value="beginner"
            label="Beginner"
            hint="≈5M-cell sizing target"
            checked={meshMode === "beginner"}
            onChange={() => setMeshMode("beginner")}
          />
          <ModeOption
            value="power"
            label="Power"
            hint="finer · 50M hard cap"
            checked={meshMode === "power"}
            onChange={() => setMeshMode("power")}
          />
        </div>
      </fieldset>

      {/* DEC-V61-135 (N2.1): Advanced sizing field (collapsed by default).
       *  Engineer-driven base/min/max + curvature + proximity overrides
       *  the preset path (mesh_mode_used = "custom" in response).
       *  Workbench-first acceptance: usable without LLM. */}
      <details
        data-testid="step2-mesh-advanced-sizing"
        className="rounded-sm border border-surface-800 bg-surface-950/40"
        open={sizingFieldOpen}
        onToggle={(e) =>
          setSizingFieldOpen((e.target as HTMLDetailsElement).open)
        }
      >
        <summary className="cursor-pointer px-2 py-1 text-[11px] font-mono uppercase tracking-wider text-surface-300 hover:text-surface-100">
          Advanced sizing (override preset)
        </summary>
        <div className="space-y-2 border-t border-surface-800 p-2">
          <p className="text-[11px] text-surface-400">
            Set any field to override the preset. Empty = preset default.
            Backend enforces min ≤ base ≤ max and 50M cell-cap.
          </p>
          <SizingFieldInput
            label="base_lc"
            hint="Nominal lc (gmsh CharacteristicLengthMax baseline)"
            value={sizingField.base_lc ?? ""}
            onChange={(v) => setSizingField({ ...sizingField, base_lc: v })}
          />
          <SizingFieldInput
            label="min_lc"
            hint="Lower clamp (CharacteristicLengthMin)"
            value={sizingField.min_lc ?? ""}
            onChange={(v) => setSizingField({ ...sizingField, min_lc: v })}
          />
          <SizingFieldInput
            label="max_lc"
            hint="Upper clamp (CharacteristicLengthMax)"
            value={sizingField.max_lc ?? ""}
            onChange={(v) => setSizingField({ ...sizingField, max_lc: v })}
          />
          <SizingFieldInput
            label="curvature_target_size"
            hint="MeshSizeFromCurvature value (elements per 2π)"
            value={sizingField.curvature_target_size ?? ""}
            onChange={(v) =>
              setSizingField({ ...sizingField, curvature_target_size: v })
            }
          />
          <SizingFieldInput
            label="proximity_layers"
            hint="MeshSizeExtendFromBoundary (1–10)"
            value={sizingField.proximity_layers ?? ""}
            onChange={(v) =>
              setSizingField({
                ...sizingField,
                proximity_layers: v == null ? null : Math.round(v),
              })
            }
            integer
          />
          <button
            type="button"
            data-testid="step2-mesh-sizing-reset"
            onClick={() => {
              setSizingField(EMPTY_SIZING);
              setSizingFieldError(null);
            }}
            className="rounded-sm border border-surface-700 px-2 py-1 text-[11px] text-surface-300 hover:border-surface-500"
          >
            Reset to preset
          </button>
          {sizingFieldError && (
            <p
              data-testid="step2-mesh-sizing-error"
              className="rounded-sm border border-rose-500/40 bg-rose-500/10 px-2 py-1 text-[11px] text-rose-200"
            >
              {sizingFieldError}
            </p>
          )}
        </div>
      </details>

      {/* DEC-V61-136 (N2.2): Refinement zones (collapsed by default).
       *  Engineer-driven box / sphere zones layered on top of the
       *  sizing path. Empty list = N2.1 behavior. Workbench-first
       *  acceptance: all interactions are forms — no AI surface here. */}
      <details
        data-testid="step2-mesh-refinement-zones"
        className="rounded-sm border border-surface-800 bg-surface-950/40"
        open={zonesOpen}
        onToggle={(e) =>
          setZonesOpen((e.target as HTMLDetailsElement).open)
        }
      >
        <summary className="cursor-pointer px-2 py-1 text-[11px] font-mono uppercase tracking-wider text-surface-300 hover:text-surface-100">
          Refinement zones (box / sphere · {zones.length})
        </summary>
        <div className="space-y-2 border-t border-surface-800 p-2">
          <p className="text-[11px] text-surface-400">
            Each zone tightens gmsh&apos;s characteristic length inside a
            box or sphere. Level 1-3 → lc × 1/2, 1/4, 1/8 inside the
            zone. Backend rejects out-of-AABB zones with HTTP 422.
          </p>
          {zones.map((zone, idx) => (
            <RefinementZoneRow
              key={idx}
              zone={zone}
              onChange={(next) =>
                setZones(zones.map((z, i) => (i === idx ? next : z)))
              }
              onRemove={() =>
                setZones(zones.filter((_, i) => i !== idx))
              }
              testIdSuffix={`${idx}`}
            />
          ))}
          <div className="flex gap-2">
            <button
              type="button"
              data-testid="step2-mesh-zones-add-box"
              onClick={() => setZones([...zones, makeBoxZone()])}
              className="rounded-sm border border-surface-700 px-2 py-1 text-[11px] text-surface-300 hover:border-surface-500"
            >
              + Box zone
            </button>
            <button
              type="button"
              data-testid="step2-mesh-zones-add-sphere"
              onClick={() => setZones([...zones, makeSphereZone()])}
              className="rounded-sm border border-surface-700 px-2 py-1 text-[11px] text-surface-300 hover:border-surface-500"
            >
              + Sphere zone
            </button>
            {zones.length > 0 && (
              <button
                type="button"
                data-testid="step2-mesh-zones-clear"
                onClick={() => {
                  setZones([]);
                  setZonesError(null);
                }}
                className="rounded-sm border border-surface-700 px-2 py-1 text-[11px] text-surface-300 hover:border-surface-500"
              >
                Clear all
              </button>
            )}
          </div>
          {zonesError && (
            <p
              data-testid="step2-mesh-zones-error"
              className="rounded-sm border border-rose-500/40 bg-rose-500/10 px-2 py-1 text-[11px] text-rose-200"
            >
              {zonesError}
            </p>
          )}
        </div>
      </details>

      {/* DEC-V61-137 (N2.3): Prism layers (boundary-layer addLayers).
       *  Distinct from the gmsh stage — engineer clicks "Apply prism
       *  layers" after a successful mesh run. v0 supports a single
       *  patch; multi-patch is N2.3-extend. Workbench-first: form
       *  inputs, no AI surface added; backend mutating route is
       *  registered in V132 MUTATING_ROUTES contract. */}
      <details
        data-testid="step2-mesh-prism-layers"
        className="rounded-sm border border-surface-800 bg-surface-950/40"
        open={prismOpen}
        onToggle={(e) => setPrismOpen((e.target as HTMLDetailsElement).open)}
      >
        <summary className="cursor-pointer px-2 py-1 text-[11px] font-mono uppercase tracking-wider text-surface-300 hover:text-surface-100">
          Boundary layers · prism (snappyHexMesh)
        </summary>
        <div className="space-y-2 border-t border-surface-800 p-2">
          <p className="text-[11px] text-surface-400">
            Adds wall-normal prism layers to the existing polyMesh via
            snappyHexMesh addLayers. Run the mesh stage first, then
            click "Apply prism layers" — this refreshes
            constant/polyMesh in place. v0 accepts one patch; multi-
            patch in N2.3-extend.
          </p>
          <PrismFieldInput
            label="patch"
            hint="Patch name from constant/polyMesh/boundary"
            type="text"
            value={prismConfig.patch}
            onChange={(v) =>
              setPrismConfig({ ...prismConfig, patch: v as string })
            }
          />
          <PrismFieldInput
            label="first_cell_height"
            hint="Wall-normal thickness of the first layer (case units)"
            type="number"
            value={prismConfig.first_cell_height}
            onChange={(v) =>
              setPrismConfig({
                ...prismConfig,
                first_cell_height: v as number,
              })
            }
          />
          <PrismFieldInput
            label="expansion_ratio"
            hint={`Geometric expansion (${PRISM_EXPANSION_RATIO_MIN}-${PRISM_EXPANSION_RATIO_MAX})`}
            type="number"
            value={prismConfig.expansion_ratio}
            onChange={(v) =>
              setPrismConfig({
                ...prismConfig,
                expansion_ratio: v as number,
              })
            }
          />
          <PrismFieldInput
            label="num_layers"
            hint={`Number of prism layers (1-${PRISM_MAX_LAYER_COUNT})`}
            type="number"
            value={prismConfig.num_layers}
            integer
            onChange={(v) =>
              setPrismConfig({
                ...prismConfig,
                num_layers: Math.round(v as number),
              })
            }
          />
          {/* R0 P2 (Codex 86gs): do NOT gate on local `response` —
            it is null on cases meshed in earlier sessions even though
            the polyMesh exists on disk (StepPanelShell's /mesh/render
            probe restores Step 2 in that scenario). The backend
            already returns a structured `polyMesh_not_ready` 422 if
            apply is clicked without a polyMesh, which the rejection
            panel surfaces with a clear hint.
            R1 P1 (Codex 86gs): also disable while a gmsh remesh is
            in flight — both routes mutate constant/polyMesh without
            a case_lock, so concurrent runs would race. */}
          <button
            type="button"
            data-testid="step2-mesh-prism-apply"
            disabled={prismApplying || meshInFlight}
            onClick={applyPrismLayers}
            className="rounded-sm border border-emerald-600/60 bg-emerald-600/10 px-3 py-1 text-[11px] text-emerald-200 hover:border-emerald-400 disabled:cursor-not-allowed disabled:border-surface-700 disabled:bg-surface-950 disabled:text-surface-500"
            title={
              meshInFlight
                ? "Mesh stage running — wait for it to finish before applying prism layers"
                : "Run snappyHexMesh addLayers on the existing polyMesh (mesh stage must have produced one)"
            }
          >
            {prismApplying ? "Applying…" : "Apply prism layers"}
          </button>
          {prismResponse && (
            <div
              data-testid="step2-mesh-prism-success"
              className="rounded-sm border border-emerald-500/30 bg-emerald-500/5 p-2 text-[11px]"
            >
              <strong className="text-emerald-300">
                Prism layers applied
              </strong>
              <dl className="mt-1 grid grid-cols-[max-content_1fr] gap-x-3 gap-y-0.5 font-mono">
                <dt className="text-surface-500">layers_added</dt>
                <dd className="text-surface-200">
                  {prismResponse.prism_summary.layers_added}
                </dd>
                <dt className="text-surface-500">coverage</dt>
                <dd className="text-surface-200">
                  {prismResponse.prism_summary.coverage_fraction !== null
                    ? `${(prismResponse.prism_summary.coverage_fraction * 100).toFixed(1)}%`
                    : "(unparsed)"}
                </dd>
                <dt className="text-surface-500">time</dt>
                <dd className="text-surface-200">
                  {prismResponse.prism_summary.generation_time_s.toFixed(2)}s
                </dd>
              </dl>
            </div>
          )}
          {prismRejection && (
            <div
              data-testid="step2-mesh-prism-rejection"
              className="rounded-sm border border-rose-500/40 bg-rose-500/10 p-2 text-[11px]"
            >
              <div className="flex items-baseline justify-between">
                <strong className="text-rose-200">Prism rejected</strong>
                <code className="font-mono text-rose-300">
                  {prismRejection.failing_check}
                </code>
              </div>
              <p className="mt-1 text-rose-200/90">{prismRejection.reason}</p>
              {REJECTION_HINTS[prismRejection.failing_check] && (
                <p className="mt-1 text-rose-200/80">
                  {REJECTION_HINTS[prismRejection.failing_check]}
                </p>
              )}
            </div>
          )}
          {prismError && (
            <p
              data-testid="step2-mesh-prism-error"
              className="rounded-sm border border-rose-500/40 bg-rose-500/10 px-2 py-1 text-rose-200"
            >
              {prismError}
            </p>
          )}
        </div>
      </details>

      {response && (
        <div
          data-testid="step2-mesh-success"
          className="rounded-sm border border-emerald-500/30 bg-emerald-500/5 p-2"
        >
          <div className="flex items-baseline justify-between">
            <strong className="text-emerald-300">Mesh generated</strong>
            <code className="font-mono text-[11px] text-surface-500">
              {response.mesh_summary.mesh_mode_used}
            </code>
          </div>
          <dl className="mt-2 grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1 font-mono text-[11px]">
            <dt className="text-surface-500">cells</dt>
            <dd className="text-surface-200">
              {response.mesh_summary.cell_count.toLocaleString()}
            </dd>
            <dt className="text-surface-500">faces</dt>
            <dd className="text-surface-200">
              {response.mesh_summary.face_count.toLocaleString()}
            </dd>
            <dt className="text-surface-500">points</dt>
            <dd className="text-surface-200">
              {response.mesh_summary.point_count.toLocaleString()}
            </dd>
            <dt className="text-surface-500">time</dt>
            <dd className="text-surface-200">
              {response.mesh_summary.generation_time_s.toFixed(2)}s
            </dd>
          </dl>
          {response.mesh_summary.warning && (
            <p className="mt-2 rounded-sm border border-amber-500/40 bg-amber-500/10 px-2 py-1 text-[11px] text-amber-200">
              {response.mesh_summary.warning}
            </p>
          )}
        </div>
      )}

      {/* V127: Fluent-style quality gauges + per-patch chips.
       *  R1 P1 fix: always mount when caseId is set so the card also
       *  appears for cases meshed in an earlier session (the
       *  meshGenSeq>0 gate broke the "review existing mesh" workflow
       *  — Step 2 marks complete from the /mesh/render probe but
       *  meshGenSeq stays 0 unless the user re-runs the mesh).
       *  MeshQualityCard's own 404 handling self-hides when polyMesh
       *  isn't ready yet, so a fresh case shows nothing here.
       *  meshGenSeq still drives re-fetches after manual or
       *  AI-coach-driven regenerate. */}
      {caseId && (
        <MeshQualityCard caseId={caseId} meshGenSeq={meshGenSeq} />
      )}

      {rejection && (
        <div
          data-testid="step2-mesh-rejection"
          className="rounded-sm border border-rose-500/40 bg-rose-500/10 p-2"
        >
          <div className="flex items-baseline justify-between">
            <strong className="text-rose-200">Mesh rejected</strong>
            <code className="font-mono text-[11px] text-rose-300">
              {rejection.failing_check}
            </code>
          </div>
          <p className="mt-1 text-rose-200/90">{rejection.reason}</p>
          {REJECTION_HINTS[rejection.failing_check] && (
            <p className="mt-1 text-rose-200/80">
              {REJECTION_HINTS[rejection.failing_check]}
            </p>
          )}
        </div>
      )}

      {networkError && (
        <p
          data-testid="step2-mesh-network-error"
          className="rounded-sm border border-rose-500/40 bg-rose-500/10 px-2 py-1 text-rose-200"
        >
          Network error: {networkError}
        </p>
      )}
    </div>
  );
}

function SizingFieldInput({
  label,
  hint,
  value,
  onChange,
  integer = false,
}: {
  label: string;
  hint: string;
  value: number | "";
  onChange: (next: number | null) => void;
  integer?: boolean;
}) {
  return (
    <label
      data-testid={`step2-mesh-sizing-${label}`}
      className="flex items-baseline gap-2 text-[11px]"
    >
      <span className="w-44 font-mono text-surface-200">{label}</span>
      <input
        type="number"
        step={integer ? 1 : "any"}
        min={integer ? 1 : 0}
        value={value}
        onChange={(e) => {
          const raw = e.target.value;
          if (raw === "") onChange(null);
          else {
            const n = Number(raw);
            onChange(Number.isFinite(n) ? n : null);
          }
        }}
        className="w-28 rounded-sm border border-surface-700 bg-surface-950 px-2 py-1 font-mono text-surface-100"
      />
      <span className="flex-1 text-surface-400">{hint}</span>
    </label>
  );
}

// DEC-V61-136 (N2.2): one row per refinement zone. Box vs sphere is
// dispatched on ``zone.geometry``; both branches share the level
// dropdown + remove button.
function RefinementZoneRow({
  zone,
  onChange,
  onRemove,
  testIdSuffix,
}: {
  zone: MeshRefinementZone;
  onChange: (next: MeshRefinementZone) => void;
  onRemove: () => void;
  testIdSuffix: string;
}) {
  return (
    <div
      data-testid={`step2-mesh-zone-${testIdSuffix}`}
      className="space-y-1 rounded-sm border border-surface-800 bg-surface-950/30 p-2"
    >
      <div className="flex items-baseline justify-between">
        <code className="text-[11px] font-mono uppercase tracking-wider text-surface-300">
          {zone.geometry} · zone {testIdSuffix}
        </code>
        <div className="flex items-baseline gap-2">
          <label className="flex items-baseline gap-1 text-[11px] text-surface-400">
            level
            <select
              data-testid={`step2-mesh-zone-${testIdSuffix}-level`}
              value={zone.level}
              onChange={(e) => {
                const lvl = Number(e.target.value);
                if (
                  lvl >= REFINEMENT_LEVEL_MIN &&
                  lvl <= REFINEMENT_LEVEL_MAX
                ) {
                  onChange({ ...zone, level: lvl as RefinementLevel });
                }
              }}
              className="rounded-sm border border-surface-700 bg-surface-950 px-1 py-0.5 font-mono text-surface-100"
            >
              <option value={1}>1 (×0.5)</option>
              <option value={2}>2 (×0.25)</option>
              <option value={3}>3 (×0.125)</option>
            </select>
          </label>
          <button
            type="button"
            data-testid={`step2-mesh-zone-${testIdSuffix}-remove`}
            onClick={onRemove}
            className="rounded-sm border border-rose-500/40 px-2 py-0.5 text-[11px] text-rose-300 hover:border-rose-400"
          >
            Remove
          </button>
        </div>
      </div>
      {zone.geometry === "box" ? (
        <div className="grid grid-cols-2 gap-x-2 gap-y-1">
          {(
            [
              ["xmin", 0],
              ["ymin", 1],
              ["zmin", 2],
              ["xmax", 3],
              ["ymax", 4],
              ["zmax", 5],
            ] as const
          ).map(([label, ix]) => (
            <ZoneNumberInput
              key={label}
              label={label}
              value={zone.bbox[ix]}
              onChange={(v) => {
                const next = [...zone.bbox] as typeof zone.bbox;
                next[ix] = v;
                onChange({ ...zone, bbox: next });
              }}
              testId={`step2-mesh-zone-${testIdSuffix}-${label}`}
            />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-x-2 gap-y-1">
          {(
            [
              ["x", 0],
              ["y", 1],
              ["z", 2],
            ] as const
          ).map(([label, ix]) => (
            <ZoneNumberInput
              key={label}
              label={`center.${label}`}
              value={zone.center[ix]}
              onChange={(v) => {
                const next = [...zone.center] as typeof zone.center;
                next[ix] = v;
                onChange({ ...zone, center: next });
              }}
              testId={`step2-mesh-zone-${testIdSuffix}-c${label}`}
            />
          ))}
          <ZoneNumberInput
            label="radius"
            value={zone.radius}
            onChange={(v) => onChange({ ...zone, radius: v })}
            testId={`step2-mesh-zone-${testIdSuffix}-radius`}
          />
        </div>
      )}
    </div>
  );
}

// DEC-V61-137 (N2.3): single-row form input for prism config. Text
// inputs use string draft state internally to avoid the partial-edit
// snap-back that ZoneNumberInput documents below; number inputs use
// the same draft pattern.
function PrismFieldInput({
  label,
  hint,
  type,
  value,
  onChange,
  integer = false,
}: {
  label: string;
  hint: string;
  type: "text" | "number";
  value: string | number;
  onChange: (next: string | number) => void;
  integer?: boolean;
}) {
  const [draft, setDraft] = useState<string | null>(null);
  const display = draft ?? String(value);
  return (
    <label
      data-testid={`step2-mesh-prism-${label}`}
      className="flex items-baseline gap-2 text-[11px]"
    >
      <span className="w-32 font-mono text-surface-200">{label}</span>
      <input
        type="text"
        inputMode={type === "number" ? "decimal" : "text"}
        value={display}
        onChange={(e) => {
          const raw = e.target.value;
          setDraft(raw);
          if (type === "text") {
            onChange(raw);
            return;
          }
          if (raw === "" || raw === "-" || raw === "." || raw === "-.") {
            return;
          }
          const n = Number(raw);
          if (Number.isFinite(n)) {
            onChange(integer ? Math.round(n) : n);
          }
        }}
        onBlur={() => setDraft(null)}
        className="w-32 rounded-sm border border-surface-700 bg-surface-950 px-2 py-1 font-mono text-surface-100"
      />
      <span className="flex-1 text-surface-400">{hint}</span>
    </label>
  );
}

// V136 R0 P1 (Codex CRS): a controlled <input type="number"> that
// coerces every keystroke through Number() destroys partial / negative
// edits — typing "-1" or ".25" or clearing the field gets stuck on
// "0" because the intermediate strings parse to 0 / NaN. Track the
// raw string in local state and only fire onChange when parsing
// succeeds to a finite number; on blur, drop the draft so the
// canonical parent value renders again.
//
// Implementation note: do NOT auto-reset draft from a useEffect on
// [value]. React's Object.is comparison distinguishes 0 from -0, so
// Number("-0.") committing -0 over a previous 0 fires a re-render
// that would erase a half-typed "-0." draft. Letting blur be the only
// reset path keeps mid-edit drafts stable through value re-syncs that
// match the user's intermediate parse.
function ZoneNumberInput({
  label,
  value,
  onChange,
  testId,
}: {
  label: string;
  value: number;
  onChange: (next: number) => void;
  testId: string;
}) {
  const [draft, setDraft] = useState<string | null>(null);
  const display = draft ?? String(value);

  return (
    <label className="flex items-baseline gap-2 text-[11px]">
      <span className="w-20 font-mono text-surface-400">{label}</span>
      <input
        type="text"
        inputMode="decimal"
        data-testid={testId}
        value={display}
        onChange={(e) => {
          const raw = e.target.value;
          setDraft(raw);
          // Only commit when the raw string parses to a finite number.
          // Partial states ("", "-", ".", "-.") leave the parent
          // value alone so the user can finish typing without losing
          // characters.
          if (raw === "" || raw === "-" || raw === "." || raw === "-.") {
            return;
          }
          const n = Number(raw);
          if (Number.isFinite(n)) onChange(n);
        }}
        onBlur={() => {
          // On blur, drop the draft so the canonical committed value
          // renders. This collapses partial-state drafts like "-" or
          // "" back to whatever the parent currently holds.
          setDraft(null);
        }}
        className="w-24 rounded-sm border border-surface-700 bg-surface-950 px-1 py-0.5 font-mono text-surface-100"
      />
    </label>
  );
}

function ModeOption({
  value,
  label,
  hint,
  checked,
  onChange,
}: {
  value: MeshRequestMode;
  label: string;
  hint: string;
  checked: boolean;
  onChange: () => void;
}) {
  return (
    <label
      data-testid={`step2-mesh-mode-${value}`}
      className={`flex cursor-pointer items-baseline gap-2 rounded-sm border px-2 py-1 transition ${
        checked
          ? "border-emerald-500/60 bg-emerald-500/10"
          : "border-surface-800 bg-surface-950/40 hover:border-surface-700"
      }`}
    >
      <input
        type="radio"
        name="step2-mesh-mode"
        value={value}
        checked={checked}
        onChange={onChange}
        className="accent-emerald-400"
      />
      <span className="text-[11px] font-semibold text-surface-100">
        {label}
      </span>
      <span className="text-[11px] text-surface-400">{hint}</span>
    </label>
  );
}
