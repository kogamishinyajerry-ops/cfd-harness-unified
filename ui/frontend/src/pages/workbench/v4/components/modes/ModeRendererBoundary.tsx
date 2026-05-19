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
import {
  geometryGlbUrl,
  useGlbAvailability,
} from "../../hooks/useGlbAvailability";
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
  const geomUrl = geometryGlbUrl(caseId);
  const geomProbe = useGlbAvailability(bcProbe.available === false ? geomUrl : null);

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

  function onFacePick(event: V4FacePickEvent) {
    // bc_glb sets primitive.name = patch.id, so patchName === patch.id.
    const hit = patches.find((p) => p.id === event.patchName);
    if (hit) setSelectedPatchId(hit.id);
    setLastPickedFaceId(event.faceId);
    setLastPickedWorld(event.worldPosition);
  }

  const showViewport = activeGlbUrl != null;

  return (
    <div data-testid="v4-mode-boundary" className="flex h-full w-full bg-v4-canvas">
      {/* Left · real patch list grouped by role */}
      <aside
        className="flex w-[220px] shrink-0 flex-col border-r border-v4-border bg-v4-shell/60"
        data-testid="v4-mode-boundary-patch-list"
      >
        <div className="border-b border-v4-border px-3 py-2 text-[10px] uppercase tracking-wider text-v4-textTertiary">
          边界面 · {patches.length} 项
        </div>
        <ul className="flex-1 overflow-y-auto px-1.5 py-1.5 text-[11px]">
          {patches.length === 0 && (
            <li className="px-2 py-1 text-v4-textTertiary">
              {caseId ? "无边界数据" : "选择算例后显示"}
            </li>
          )}
          {patches.map((p) => {
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
            <IndustrialBoxScene
              variant="boundary"
              className="h-full max-h-[420px] w-full max-w-3xl"
            />
          </div>
        )}
        {bcProbe.available === false && geomProbe.available === true && (
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
      <aside className="flex w-[200px] shrink-0 flex-col border-l border-v4-border bg-v4-shell p-3">
        <div className="mb-2 text-[10px] uppercase tracking-wider text-v4-textTertiary">
          边界统计
        </div>
        <ul className="space-y-1.5 text-[11px]">
          {sortedRoles.length === 0 && (
            <li className="text-v4-textTertiary">—</li>
          )}
          {sortedRoles.map((role) => (
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
          ))}
        </ul>
        <div className="mt-3 border-t border-v4-border pt-2">
          <div className="flex items-baseline justify-between text-[10px]">
            <span className="text-v4-textTertiary">边界条件</span>
            <span className="font-mono text-v4-textSecondary">
              {ctx.basics?.boundary_conditions?.length ?? "—"} 项
            </span>
          </div>
          <div className="mt-1 flex items-baseline justify-between text-[10px]">
            <span className="text-v4-textTertiary">求解器</span>
            <span className="font-mono text-v4-textPrimary">
              {ctx.basics?.solver?.name ?? "—"}
            </span>
          </div>
        </div>
      </aside>
    </div>
  );
}
