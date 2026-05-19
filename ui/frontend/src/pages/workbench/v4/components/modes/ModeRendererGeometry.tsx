/**
 * V4 · Mode renderer · 几何 (Geometry) · per UI-SPEC §4.2 · Phase C-R2 wired.
 *
 * Real vtk.js viewport (geometry.glb) when authored CAD semantics are
 * available; otherwise the blueprint-intake page uses a local bitmap scene
 * derived from image 2. No schematic SVG fallback is used for this mode.
 *
 * Phase C-R2: part legend now reads real patches from workbench-basics
 * grouped by surface role (inlet/outlet/wall/...), with a role-color
 * swatch and Chinese role label. Hover/click highlights the row;
 * full bidirectional sync with the viewport (legend → highlight cells
 * on the matching vtk actor) requires extending the kernel surface
 * with getActorByPatchName + getNumCells and is deferred to R3.
 */
import { useState } from "react";

import { useV4WorkbenchContext } from "../../hooks/useV4WorkbenchContext";
import {
  geometryGlbUrl,
  useGlbAvailability,
} from "../../hooks/useGlbAvailability";
import { ViewportV4, type V4CameraPreset } from "../ViewportV4";
import {
  GEOMETRY_BLUEPRINT_PARTS,
  GEOMETRY_BLUEPRINT_SCENE,
  GEOMETRY_BLUEPRINT_SUMMARY,
  GEOMETRY_BLUEPRINT_TABS,
  GEOMETRY_BLUEPRINT_TOOLBAR,
  hasAuthoredCadParts,
} from "../geometryBlueprint";
import { V4_PALETTE } from "@/theme/industrial_minimalist";
import type { PatchRole } from "@/types/workbench_basics";

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
  empty: "空",
  airfoil: "翼面",
};

function roleColor(role: PatchRole): string {
  return ROLE_COLOR[role] ?? V4_PALETTE.textTertiary;
}
function roleLabel(role: PatchRole): string {
  return ROLE_LABEL_ZH[role] ?? role;
}

function BlueprintBitmapScene() {
  return (
    <div className="flex h-full w-full items-center justify-center px-3 py-3">
      <div className="relative h-full max-h-[680px] w-full overflow-hidden border border-v4-border bg-v4-canvas shadow-[inset_0_0_120px_rgba(0,0,0,0.32)]">
        <img
          src={GEOMETRY_BLUEPRINT_SCENE.imageUrl}
          alt="Exploded APU CAD assembly"
          className="h-full w-full object-contain"
          data-testid="v4-mode-geometry-bitmap-scene"
          draggable={false}
        />
      </div>
    </div>
  );
}

function GeometryEmptyState() {
  return (
    <div
      className="flex h-full w-full items-center justify-center px-6 text-center"
      data-testid="v4-mode-geometry-empty-scene"
    >
      <div className="max-w-sm border border-v4-border bg-v4-surface/80 px-5 py-4">
        <div className="text-[12px] font-medium text-v4-textPrimary">
          未找到可渲染几何
        </div>
        <div className="mt-2 text-[11px] leading-5 text-v4-textSecondary">
          当前算例没有可用的 GLB 资产或 CAD 分件语义。Geometry 页不再用示意 SVG
          代替真实几何。
        </div>
      </div>
    </div>
  );
}

interface Props {
  caseId?: string;
  cameraPreset?: V4CameraPreset;
}

export function ModeRendererGeometry({ caseId, cameraPreset }: Props) {
  const ctx = useV4WorkbenchContext(null);
  const glbUrl = geometryGlbUrl(caseId);
  const probe = useGlbAvailability(glbUrl);

  const patches = ctx.basics?.patches ?? [];
  const dim = ctx.basics?.dimension;
  const cl = ctx.basics?.geometry?.characteristic_length;
  const [selectedPatchId, setSelectedPatchId] = useState<string | null>(null);
  const authoredCadParts = hasAuthoredCadParts(patches.length);
  const blueprintCadMode = !authoredCadParts;
  const showViewport = probe.available === true && authoredCadParts;
  const selectedBlueprintPart = blueprintCadMode
    ? GEOMETRY_BLUEPRINT_PARTS.find((p) => p.id === selectedPatchId)
    : null;

  return (
    <div
      data-testid="v4-mode-geometry"
      className="flex h-full w-full flex-col bg-v4-canvas"
      data-cad-source={blueprintCadMode ? "blueprint-intake" : "workbench-basics"}
    >
      <div className="flex h-11 shrink-0 items-end justify-between border-b border-v4-border px-3">
        <div className="flex h-full items-end gap-6">
          {GEOMETRY_BLUEPRINT_TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={[
                "h-full border-b-2 px-1 text-[13px] font-medium transition-colors",
                tab.id === "cad"
                  ? "border-v4-active text-v4-active"
                  : "border-transparent text-v4-textSecondary hover:text-v4-textPrimary",
              ].join(" ")}
              data-testid={`v4-mode-geometry-tab-${tab.id}`}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <span className="pb-2 font-mono text-[10px] text-v4-textTertiary">
          {blueprintCadMode
            ? `CAD intake · ${GEOMETRY_BLUEPRINT_SUMMARY.partCount} 零件 · ${GEOMETRY_BLUEPRINT_SUMMARY.gapCount} 缝隙`
            : `${dim ? `${dim}D` : "—"} · ${patches.length} 边界面${
                cl ? ` · ${cl.name} ${cl.value.toPrecision(3)}${cl.unit}` : ""
              }`}
        </span>
      </div>
      <div className="flex h-14 shrink-0 items-center gap-2 border-b border-v4-border bg-v4-shell/45 px-3">
        <div className="flex min-w-0 flex-1 items-center">
          {GEOMETRY_BLUEPRINT_TOOLBAR.map((tool, index) => (
            <button
              key={tool.id}
              type="button"
              className="flex h-11 min-w-[62px] flex-col items-center justify-center gap-0.5 border-r border-v4-border px-2 text-v4-textSecondary transition-colors hover:bg-v4-surfaceRaised hover:text-v4-textPrimary"
              data-testid={`v4-mode-geometry-tool-${tool.id}`}
            >
              <span className="font-mono text-[15px] leading-none">
                {tool.glyph}
              </span>
              <span className="text-[10px] leading-none">{tool.label}</span>
              {index === 0 && (
                <span className="sr-only">几何准备工具</span>
              )}
            </button>
          ))}
        </div>
        <button
          type="button"
          className="h-8 min-w-[96px] rounded border border-v4-border bg-v4-surfaceRaised px-3 text-[11px] text-v4-textSecondary hover:border-v4-borderActive hover:text-v4-textPrimary"
          data-testid="v4-mode-geometry-camera"
        >
          等轴测
          <span className="ml-3 text-v4-textTertiary">⌄</span>
        </button>
      </div>
      <div className="flex min-h-0 flex-1">
        {/* Part legend · left — real patches, or blueprint CAD intake when CAD semantics are absent. */}
        {!blueprintCadMode && (
          <aside
            className="flex w-[200px] shrink-0 flex-col border-r border-v4-border bg-v4-shell/60"
            data-testid="v4-mode-geometry-legend"
          >
            <div className="border-b border-v4-border px-3 py-2 text-[10px] uppercase tracking-wider text-v4-textTertiary">
              边界面 · {patches.length} 项
            </div>
            <ul className="flex-1 overflow-y-auto px-1.5 py-1.5 text-[11px]">
              {patches.length === 0 ? (
              <li className="px-2 py-1 text-v4-textTertiary">
                {caseId ? "无几何元数据" : "选择算例后显示"}
              </li>
            ) : (
              patches.map((p) => {
                const c = roleColor(p.role);
                const isSelected = p.id === selectedPatchId;
                return (
                  <li key={p.id}>
                    <button
                      type="button"
                      onClick={() =>
                        setSelectedPatchId((cur) =>
                          cur === p.id ? null : p.id,
                        )
                      }
                      className={[
                        "flex w-full items-center gap-2 rounded px-2 py-1 text-left transition-colors",
                        isSelected
                          ? "bg-v4-surfaceRaised text-v4-textPrimary"
                          : "text-v4-textSecondary hover:bg-v4-surfaceRaised hover:text-v4-textPrimary",
                      ].join(" ")}
                      style={
                        isSelected
                          ? { boxShadow: `inset 2px 0 0 ${c}` }
                          : undefined
                      }
                      data-testid={`v4-mode-geometry-patch-${p.id}`}
                      data-selected={isSelected ? "true" : "false"}
                      title={p.label_en}
                    >
                      <span
                        aria-hidden
                        className="h-2.5 w-2.5 shrink-0 rounded-sm"
                        style={{ backgroundColor: c }}
                      />
                      <span className="flex-1 truncate">{p.label_zh}</span>
                      <span className="font-mono text-[9px] text-v4-textTertiary">
                        {roleLabel(p.role)}
                      </span>
                    </button>
                  </li>
                );
              })
            )}
            </ul>
            {ctx.basics?.geometry ? (
            <div className="border-t border-v4-border px-3 py-2 text-[10px] text-v4-textTertiary">
              <div className="flex justify-between">
                <span>类型</span>
                <span className="font-mono text-v4-textPrimary">
                  {ctx.basics.geometry.shape}
                </span>
              </div>
              {cl && (
                <div className="mt-1 flex justify-between">
                  <span>{cl.name}</span>
                  <span className="font-mono text-v4-textPrimary">
                    {cl.value.toPrecision(3)} {cl.unit}
                  </span>
                </div>
              )}
              <div className="mt-1 flex justify-between">
                <span>材料</span>
                <span className="font-mono text-v4-textPrimary">
                  {ctx.basics?.materials?.length ?? 0}
                </span>
              </div>
            </div>
          ) : null}
          </aside>
        )}

        {/* Scene · real viewport, or blueprint bitmap / honest empty state. */}
        <div
          className="relative flex min-h-0 flex-1 items-center justify-center bg-[radial-gradient(circle_at_50%_35%,rgba(91,180,255,0.08),transparent_42%)]"
          data-viewport-active={showViewport ? "true" : "false"}
        >
          {showViewport ? (
            <ViewportV4
              glbUrl={glbUrl}
              cameraPreset={cameraPreset ?? "iso"}
              highlightedPatchId={authoredCadParts ? selectedPatchId : null}
            />
          ) : blueprintCadMode ? (
            <BlueprintBitmapScene />
          ) : (
            <GeometryEmptyState />
          )}
          {probe.isLoading && (
            <div
              className="pointer-events-none absolute left-3 top-3 rounded border border-v4-border bg-v4-surfaceRaised/90 px-2 py-0.5 font-mono text-[10px] text-v4-textTertiary"
              data-testid="v4-mode-geometry-probe-loading"
            >
              检查几何…
            </div>
          )}
          {probe.available === false && caseId && (
            <div
              className="pointer-events-none absolute right-3 bottom-3 rounded border border-v4-border bg-v4-surfaceRaised/90 px-2 py-0.5 font-mono text-[10px] text-v4-textTertiary"
              data-testid="v4-mode-geometry-empty-state"
            >
              当前算例无导入几何 · 等待 GLB 资产
            </div>
          )}
          {probe.available === true && blueprintCadMode && (
            <div
              className="pointer-events-none absolute right-3 bottom-3 rounded border border-v4-border bg-v4-surfaceRaised/90 px-2 py-0.5 font-mono text-[10px] text-v4-textTertiary"
              data-testid="v4-mode-geometry-blueprint-source"
            >
              GLB 可用 · CAD 分件语义待命名
            </div>
          )}
          {selectedPatchId && (
            <div
              className="pointer-events-none absolute left-3 bottom-3 rounded border border-v4-active/50 bg-v4-surfaceRaised/95 px-2 py-1 text-[10px]"
              data-testid="v4-mode-geometry-selection"
            >
              <span className="text-v4-textTertiary">已选 </span>
              <span className="font-mono text-v4-textPrimary">
                {selectedBlueprintPart?.labelZh ??
                  patches.find((p) => p.id === selectedPatchId)?.label_zh ??
                  selectedPatchId}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
