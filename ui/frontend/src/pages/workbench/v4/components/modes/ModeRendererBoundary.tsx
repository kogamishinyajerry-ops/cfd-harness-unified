/**
 * V4 · Mode renderer · 边界 (BC) · per UI-SPEC §4.5 · Phase C-R2 wired.
 *
 * Real polyMesh boundary patches (bc.glb) when the case has run setup-bc;
 * falls back to the stylised SVG scaffold with hardcoded leader-line
 * labels when only triSurface STL exists (Phase D blueprint look).
 *
 * Pick contract (when bc.glb is available):
 *   - ViewportV4 mounts with pickMode=true
 *   - Click on any face → onFacePick fires with patch_name (= patch.id
 *     since backend sets primitive.name=patch_name in bc_glb.py)
 *   - We resolve patch_name → Patch in workbench-basics.patches and
 *     highlight the matching row in the left panel
 *   - Selected patch row shows a 2px left border in the role's color
 *
 * Patch list is grouped by role (inlet/outlet/wall/symmetry/etc) so the
 * 边界统计 right panel and the left selectable list share the same
 * source of truth (no hardcoded counts).
 */
import { useState } from "react";

import { useV4WorkbenchContext } from "../../hooks/useV4WorkbenchContext";
// DEC-V61-202-SUB-M30-INTEGRATION-V4-SHELL · publish V4 face picks to
// FacePickContext so FacePickUrlSync mirrors patchName → ?focus_patch=
// and the backend decide() biases rail/cards to the current patch.
import { useFacePickPublisher } from "../../../step_panel_shell/FacePickContext";
import {
  geometryGlbUrl,
  useGlbAvailability,
} from "../../hooks/useGlbAvailability";
import { BOUNDARY_BLUEPRINT_TYPES } from "../boundaryBlueprint";
import { IndustrialBoxScene } from "../scene/IndustrialBoxScene";
import { ViewportV4, type V4CameraPreset, type V4FacePickEvent } from "../ViewportV4";
import { V4_PALETTE } from "@/theme/industrial_minimalist";
import type { Patch, PatchRole } from "@/types/workbench_basics";

/** Role → display color · matches §4.5 spec BC types. Falls back to
 *  textTertiary for roles we don't have a dedicated color for. */
const ROLE_COLOR: Partial<Record<PatchRole, string>> = {
  inlet: V4_PALETTE.bcTypes.inlet,
  outlet: V4_PALETTE.bcTypes.outlet,
  wall: V4_PALETTE.bcTypes.wall,
  moving_wall: V4_PALETTE.bcTypes.rotor,
  symmetry: V4_PALETTE.bcTypes.symmetry,
  cyclic: V4_PALETTE.bcTypes.symmetry,
  periodic: V4_PALETTE.bcTypes.symmetry,
  empty: V4_PALETTE.textTertiary,
  airfoil: V4_PALETTE.bcTypes.wall,
};

const ROLE_LABEL_ZH: Partial<Record<PatchRole, string>> = {
  inlet: "入口",
  outlet: "出口",
  wall: "壁面",
  moving_wall: "运动壁",
  symmetry: "对称",
  cyclic: "周期",
  periodic: "周期",
  empty: "空（2D）",
  airfoil: "翼面",
};

function roleColor(role: PatchRole): string {
  return ROLE_COLOR[role] ?? V4_PALETTE.textTertiary;
}

function roleLabel(role: PatchRole): string {
  return ROLE_LABEL_ZH[role] ?? role;
}

interface Props {
  caseId?: string;
  cameraPreset?: V4CameraPreset;
}

export function ModeRendererBoundary({ caseId, cameraPreset }: Props) {
  const ctx = useV4WorkbenchContext(caseId ?? null);
  const glbUrl = caseId ? `/api/cases/${encodeURIComponent(caseId)}/bc/render` : null;
  const bcProbe = useGlbAvailability(glbUrl);
  // Fall back to geometry.glb for pickMode if bc.glb missing — picks
  // still work, just no per-patch coloring.
  //
  // M5.5 C4 · probe geometry.glb UNCONDITIONALLY (DEC-V61-206). The previous
  // gate (`bcProbe.available === false ? geomUrl : null`) only probed geometry
  // once bc resolved to exactly false; when the bc/render probe stalls at
  // `undefined` (the common case — most cases never run setup-bc to produce a
  // bc.glb), the geometry fallback never activated and the step fell through to
  // the fabricated BoundaryBlueprintScene SVG even though the REAL geometry was
  // available (it renders fine in Physics/Solver). Probing unconditionally
  // makes the real geometry show whenever it exists; bc.glb is still preferred.
  const geomUrl = geometryGlbUrl(caseId);
  const geomProbe = useGlbAvailability(geomUrl);

  const activeGlbUrl =
    bcProbe.available === true
      ? glbUrl
      : geomProbe.available === true
        ? geomUrl
        : null;

  const [selectedPatchId, setSelectedPatchId] = useState<string | null>(null);
  const [lastPickedFaceId, setLastPickedFaceId] = useState<string | null>(null);
  // R5 · capture the exact click-pick world position so the viewport
  // annotation anchors at the picked face instead of the actor centroid.
  // null when the selection came from the legend (centroid fallback).
  const [lastPickedWorld, setLastPickedWorld] = useState<
    [number, number, number] | null
  >(null);

  const patches: Patch[] = ctx.basics?.patches ?? [];
  // Group by role for the right summary panel.
  const counts: Partial<Record<PatchRole, number>> = {};
  for (const p of patches) {
    counts[p.role] = (counts[p.role] ?? 0) + 1;
  }
  const sortedRoles = (Object.keys(counts) as PatchRole[]).sort();

  // Codex R0 P1 fix · M3.0 integration: V4 face picks must publish into
  // FacePickContext so FacePickUrlSync mirrors patchName → URL. Without
  // this the focus_patch driver is dead on the live V4 route.
  const publishFacePick = useFacePickPublisher();

  function onFacePick(event: V4FacePickEvent) {
    // bc_glb sets primitive.name = patch.id, so patchName === patch.id.
    const hit = patches.find((p) => p.id === event.patchName);
    if (hit) setSelectedPatchId(hit.id);
    setLastPickedFaceId(event.faceId);
    setLastPickedWorld(event.worldPosition);
    // Publish into FacePickContext. The publisher tolerates the V4
    // event shape (cellId / faceIds optional) — see useFacePickPublisher.
    publishFacePick({
      faceId: event.faceId,
      patchName: event.patchName,
      cellId: 0,
      worldPosition: event.worldPosition,
    });
  }

  const showViewport = activeGlbUrl != null;
  const hasBoundaryPatches = patches.length > 0;
  // Provenance: "derived" patches are mirrored from the real OpenFOAM case
  // on disk (DEC-V61-206), not hand-authored — and crucially NOT fabricated.
  // Label them so the user can tell real-derived from curated.
  const isDerived = ctx.basics?.provenance === "derived";

  // "标注出来你怎么设置的边界条件": surface the ACTUAL per-patch BC values
  // (e.g. inlet U=(1,0,0), outlet p=0). Default view lists each patch's U
  // BC (the driving field); selecting a patch shows all of its fields.
  const boundaryConditions = ctx.basics?.boundary_conditions ?? [];
  const uField = boundaryConditions.find((bc) => bc.field === "U");
  const selectedBcRows: Array<{ field: string; display: string }> =
    selectedPatchId
      ? boundaryConditions
          .map((bc) => {
            const pp = bc.per_patch?.[selectedPatchId];
            return pp ? { field: bc.field, display: pp.display_zh ?? pp.type } : null;
          })
          .filter((r): r is { field: string; display: string } => r !== null)
      : [];

  return (
    <div data-testid="v4-mode-boundary" className="flex h-full w-full bg-v4-canvas">
      {/* Left · real patch list grouped by role */}
      <aside
        className="flex w-[184px] shrink-0 flex-col border-r border-v4-border bg-v4-shell/60"
        data-testid="v4-mode-boundary-patch-list"
      >
        <div className="flex items-center justify-between gap-1 border-b border-v4-border px-3 py-2 text-[10px] uppercase tracking-wider text-v4-textTertiary">
          <span>
            {hasBoundaryPatches
              ? `边界面 · ${patches.length} 项`
              : "边界面 · 待识别"}
          </span>
          {hasBoundaryPatches && isDerived && (
            <span
              className="rounded-sm bg-v4-surfaceRaised px-1 py-0.5 text-[8px] normal-case tracking-normal text-v4-active"
              data-testid="v4-mode-boundary-provenance"
              title="边界面派生自算例磁盘文件（polyMesh/boundary + 0/U），非人工录入、非示意"
            >
              派生自算例
            </span>
          )}
        </div>
        <ul className="flex-1 overflow-y-auto px-1.5 py-1.5 text-[11px]">
          {!hasBoundaryPatches && (
            // M5.5 C4 · de-faked (DEC-V61-206). Was BOUNDARY_BLUEPRINT_TREE_COUNTS
            // (fabricated 入口×28 / 出口×27 / … presented as recognised patches).
            // Honest pending state until the case's patches are derived.
            <li
              className="px-2 py-2 text-[10px] leading-relaxed text-v4-textTertiary"
              data-testid="v4-mode-boundary-patches-pending"
            >
              边界面尚未识别 · 运行 setup-bc 后在此显示真实分组
            </li>
          )}
          {hasBoundaryPatches && patches.map((p) => {
            const c = roleColor(p.role);
            const isSelected = p.id === selectedPatchId;
            return (
              <li key={p.id}>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedPatchId(p.id);
                    // R4 Codex finding · clear stale face_id when
                    // user switches patches via legend; otherwise the
                    // annotation card keeps showing a face_id that
                    // belongs to the previously-clicked patch.
                    setLastPickedFaceId(null);
                    // R5 · also clear the cached pick world position
                    // so the annotation falls back to the new patch's
                    // centroid (legend selection = centroid anchor).
                    setLastPickedWorld(null);
                  }}
                  className={[
                    "flex w-full items-center gap-2 rounded px-2 py-1 text-left transition-colors",
                    isSelected
                      ? "bg-v4-surfaceRaised text-v4-textPrimary"
                      : "text-v4-textSecondary hover:bg-v4-surfaceRaised hover:text-v4-textPrimary",
                  ].join(" ")}
                  style={isSelected ? { boxShadow: `inset 2px 0 0 ${c}` } : undefined}
                  data-testid={`v4-mode-boundary-patch-${p.id}`}
                  data-selected={isSelected ? "true" : "false"}
                  title={p.label_en}
                >
                  <span
                    aria-hidden
                    className="h-2 w-2 shrink-0 rounded-sm"
                    style={{ backgroundColor: c }}
                  />
                  <span className="flex-1 truncate">{p.label_zh}</span>
                  <span className="font-mono text-[9px] text-v4-textTertiary">
                    {roleLabel(p.role)}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </aside>

      {/* Center · viewport or SVG fallback */}
      <div
        className="relative flex min-h-0 flex-1 items-center justify-center"
        data-viewport-active={showViewport ? "true" : "false"}
      >
        {showViewport ? (
          <ViewportV4
            glbUrl={activeGlbUrl}
            cameraPreset={cameraPreset ?? "iso"}
            pickMode
            caseId={caseId ?? null}
            onFacePick={onFacePick}
            highlightedPatchId={selectedPatchId}
            annotation={
              selectedPatchId
                ? (() => {
                    const hit = patches.find((p) => p.id === selectedPatchId);
                    if (!hit) return null;
                    return {
                      patchName: hit.id,
                      faceId: lastPickedFaceId,
                      label: hit.label_zh,
                      roleLabel: roleLabel(hit.role),
                      color: roleColor(hit.role),
                      worldPos: lastPickedWorld,
                    };
                  })()
                : null
            }
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center px-4 py-2">
            <BoundaryBlueprintScene />
          </div>
        )}
        {bcProbe.available === false && geomProbe.available === true && hasBoundaryPatches && (
          <div
            className="pointer-events-none absolute right-3 bottom-3 rounded border border-v4-border bg-v4-surfaceRaised/90 px-2 py-0.5 font-mono text-[10px] text-v4-textTertiary"
            data-testid="v4-mode-boundary-bcfallback"
          >
            未运行 setup-bc · 使用几何拾选
          </div>
        )}
        {bcProbe.available === false &&
          geomProbe.available === false &&
          caseId && (
            <div
              className="pointer-events-none absolute right-3 bottom-3 rounded border border-v4-border bg-v4-surfaceRaised/90 px-2 py-0.5 font-mono text-[10px] text-v4-textTertiary"
              data-testid="v4-mode-boundary-empty-state"
            >
              当前算例无几何 · 显示示意场景
            </div>
          )}
        {/* R5 · annotation is now owned by ViewportV4 (real screen-space
            projection of selected patch centroid or last-pick world
            position). The static top-right card from R4 is removed —
            see ViewportV4's <AnnotationLayer />. */}
        {lastPickedFaceId && !selectedPatchId && (
          <div
            className="pointer-events-none absolute left-3 bottom-3 rounded border border-v4-active/50 bg-v4-surfaceRaised/95 px-2 py-1 text-[10px]"
            data-testid="v4-mode-boundary-pick-toast"
          >
            <span className="text-v4-textTertiary">已拾选 </span>
            <span className="font-mono text-v4-textPrimary">{lastPickedFaceId}</span>
          </div>
        )}
      </div>

      {/* Right · BC type legend with real counts */}
      <aside className="flex w-[172px] shrink-0 flex-col border-l border-v4-border bg-v4-shell p-3">
        <div className="mb-2 text-[10px] uppercase tracking-wider text-v4-textTertiary">
          边界统计
        </div>
        <ul className="space-y-1.5 text-[11px]">
          {hasBoundaryPatches
            ? sortedRoles.map((role) => (
                <li key={role} className="flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <span
                      className="h-2 w-2 rounded-full"
                      style={{ backgroundColor: roleColor(role) }}
                    />
                    <span className="text-v4-textPrimary">{roleLabel(role)}</span>
                  </span>
                  <span className="font-mono text-v4-textSecondary">
                    {counts[role]} 处
                  </span>
                </li>
              ))
            : (
                // M5.5 C4 · de-faked (DEC-V61-206): was BOUNDARY_BLUEPRINT_TYPES
                // fabricated per-type counts. Honest pending state instead.
                <li
                  className="text-[10px] leading-relaxed text-v4-textTertiary"
                  data-testid="v4-mode-boundary-stats-pending"
                >
                  边界面待识别 · 暂无统计
                </li>
              )}
        </ul>
        <div className="mt-3 border-t border-v4-border pt-2">
          <div className="flex items-baseline justify-between text-[10px]">
            <span className="text-v4-textTertiary">边界条件</span>
            <span className="font-mono text-v4-textSecondary">
              {hasBoundaryPatches
                ? (ctx.basics?.boundary_conditions?.length ?? "—")
                : "—"}{" "}
              项
            </span>
          </div>
          <div className="mt-1 flex items-baseline justify-between text-[10px]">
            <span className="text-v4-textTertiary">求解器</span>
            <span className="font-mono text-v4-textPrimary">
              {ctx.basics?.solver?.name ?? "—"}
            </span>
          </div>
        </div>

        {/* Actual BC values — "标注出来你怎么设置的边界条件" (DEC-V61-206).
            Selected patch → all its fields; otherwise each patch's U BC. */}
        {hasBoundaryPatches && (
          <div
            className="mt-3 border-t border-v4-border pt-2"
            data-testid="v4-mode-boundary-bc-values"
          >
            <div className="mb-1 flex items-baseline justify-between text-[10px] uppercase tracking-wider text-v4-textTertiary">
              <span>
                {selectedPatchId
                  ? `${selectedPatchId} · 边界条件`
                  : "边界条件 · U"}
              </span>
              {selectedPatchId && (
                <button
                  className="normal-case tracking-normal text-v4-active hover:underline"
                  onClick={() => setSelectedPatchId(null)}
                >
                  全部
                </button>
              )}
            </div>
            <ul className="space-y-1 font-mono text-[10px]">
              {selectedPatchId
                ? selectedBcRows.map((row) => (
                    <li
                      key={row.field}
                      className="flex items-baseline justify-between gap-2"
                    >
                      <span className="text-v4-textTertiary">{row.field}</span>
                      <span className="truncate text-v4-textPrimary" title={row.display}>
                        {row.display}
                      </span>
                    </li>
                  ))
                : patches.map((p) => {
                    const pp = uField?.per_patch?.[p.id];
                    return (
                      <li
                        key={p.id}
                        className="flex items-baseline justify-between gap-2"
                      >
                        <button
                          className="truncate text-left text-v4-textSecondary hover:text-v4-textPrimary"
                          onClick={() => setSelectedPatchId(p.id)}
                          title={`查看 ${p.id} 全部场`}
                        >
                          {p.id}
                        </button>
                        <span
                          className="truncate text-v4-textPrimary"
                          title={pp?.display_zh ?? pp?.type ?? "—"}
                        >
                          {pp?.display_zh ?? pp?.type ?? "—"}
                        </span>
                      </li>
                    );
                  })}
            </ul>
          </div>
        )}
      </aside>
    </div>
  );
}

function BoundaryBlueprintScene() {
  return (
    <IndustrialBoxScene
      variant="boundary"
      className="h-full max-h-[520px] w-full max-w-5xl scale-125"
      bodyOverlay={<BoundaryBlueprintBodyPatches />}
    >
      <BoundaryBlueprintAttachedPatches />
      <BoundaryBlueprintCallouts />
    </IndustrialBoxScene>
  );
}

function BoundaryBlueprintBodyPatches() {
  const inlet = BOUNDARY_BLUEPRINT_TYPES.find((type) => type.id === "inlet")!;
  const hotWall = BOUNDARY_BLUEPRINT_TYPES.find((type) => type.id === "hot-wall")!;
  const wall = BOUNDARY_BLUEPRINT_TYPES.find((type) => type.id === "wall")!;

  return (
    <g data-testid="v4-boundary-blueprint-body-patches" pointerEvents="none">
      <rect
        x="230"
        y="120"
        width="68"
        height="60"
        fill={inlet.color}
        opacity="0.86"
      />
      <rect
        x="300"
        y="115"
        width="60"
        height="70"
        fill={hotWall.color}
        opacity="0.82"
      />
      <rect
        x="360"
        y="120"
        width="70"
        height="60"
        fill={wall.color}
        opacity="0.58"
      />
    </g>
  );
}

function BoundaryBlueprintAttachedPatches() {
  const outlet = BOUNDARY_BLUEPRINT_TYPES.find((type) => type.id === "outlet")!;
  const rotor = BOUNDARY_BLUEPRINT_TYPES.find((type) => type.id === "rotor-zone")!;
  const wall = BOUNDARY_BLUEPRINT_TYPES.find((type) => type.id === "wall")!;

  return (
    <g data-testid="v4-boundary-blueprint-attached-patches" pointerEvents="none">
      <polygon
        points="430,135 478,118 478,182 430,165"
        fill={outlet.color}
        opacity="0.9"
        stroke={outlet.color}
        strokeWidth="1.2"
      />
      <ellipse
        cx="230"
        cy="150"
        rx="11"
        ry="36"
        fill={rotor.color}
        opacity="0.88"
        stroke={rotor.color}
        strokeWidth="1"
      />
      <path
        d="M248 122 H292 M250 178 H294 M372 122 H420 M374 178 H422"
        stroke={wall.color}
        strokeWidth="2.4"
        strokeLinecap="round"
        opacity="0.95"
      />
    </g>
  );
}

function BoundaryBlueprintCallouts() {
  const callouts = [
    { id: "inlet", x: 150, y: 93, anchorX: 236, anchorY: 132 },
    { id: "rotor-zone", x: 126, y: 188, anchorX: 226, anchorY: 160 },
    { id: "hot-wall", x: 304, y: 76, anchorX: 330, anchorY: 118 },
    { id: "wall", x: 382, y: 214, anchorX: 396, anchorY: 178 },
    { id: "outlet", x: 498, y: 118, anchorX: 474, anchorY: 145 },
  ] as const;

  return (
    <g data-testid="v4-boundary-blueprint-callouts">
      {callouts.map((callout) => {
        const type = BOUNDARY_BLUEPRINT_TYPES.find((item) => item.id === callout.id)!;
        return (
          <g key={type.id} className="group">
            <line
              x1={callout.anchorX}
              y1={callout.anchorY}
              x2={callout.x}
              y2={callout.y + 12}
              stroke={type.color}
              strokeWidth="0.8"
              opacity="0.75"
            />
            <circle
              cx={callout.anchorX}
              cy={callout.anchorY}
              r="3"
              fill={type.color}
              opacity="0.95"
            />
            <rect
              x={callout.x}
              y={callout.y}
              width="76"
              height="24"
              rx="4"
              fill={V4_PALETTE.surfaceRaised}
              stroke={type.color}
              strokeWidth="0.7"
              opacity="0.96"
            />
            <text
              x={callout.x + 8}
              y={callout.y + 10}
              fill={V4_PALETTE.textPrimary}
              fontSize="9"
              fontFamily="ui-sans-serif, system-ui"
            >
              {type.labelZh}
            </text>
            <text
              x={callout.x + 8}
              y={callout.y + 20}
              fill={V4_PALETTE.textTertiary}
              fontSize="7.5"
              fontFamily="ui-monospace, monospace"
            >
              {type.labelEn}
            </text>
          </g>
        );
      })}
      <g data-testid="v4-boundary-blueprint-unidentified-callout">
        <line
          x1="402"
          y1="134"
          x2="522"
          y2="226"
          stroke={V4_PALETTE.warn}
          strokeDasharray="3 3"
          strokeWidth="0.8"
          opacity="0.85"
        />
        <rect
          x="516"
          y="214"
          width="88"
          height="24"
          rx="4"
          fill={V4_PALETTE.surfaceRaised}
          stroke={V4_PALETTE.warn}
          strokeWidth="0.7"
          opacity="0.96"
        />
        <text
          x="524"
          y="224"
          fill={V4_PALETTE.warn}
          fontSize="9"
          fontFamily="ui-sans-serif, system-ui"
        >
          未识别
        </text>
        <text
          x="524"
          y="234"
          fill={V4_PALETTE.textTertiary}
          fontSize="7.5"
          fontFamily="ui-monospace, monospace"
        >
          示意
        </text>
      </g>
    </g>
  );
}
