/**
 * V4 · Mode renderer · 几何 (Geometry) · per UI-SPEC §4.2 · Phase C-R2 wired.
 *
 * Real vtk.js viewport (geometry.glb) when available; falls back to the
 * stylised IndustrialBoxScene SVG when the case has no imported
 * geometry (curated teaching cases like LDC).
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
import { IndustrialBoxScene } from "../scene/IndustrialBoxScene";
import { ModeTabStrip } from "../ModeTabStrip";
import { ViewportV4, type V4CameraPreset } from "../ViewportV4";
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

interface Props {
  caseId?: string;
  cameraPreset?: V4CameraPreset;
}

export function ModeRendererGeometry({ caseId, cameraPreset }: Props) {
  const ctx = useV4WorkbenchContext(caseId ?? null);
  const glbUrl = geometryGlbUrl(caseId);
  const probe = useGlbAvailability(glbUrl);
  const showViewport = probe.available === true;

  const patches = ctx.basics?.patches ?? [];
  const dim = ctx.basics?.dimension;
  const cl = ctx.basics?.geometry?.characteristic_length;
  const [selectedPatchId, setSelectedPatchId] = useState<string | null>(null);

  return (
    <div data-testid="v4-mode-geometry" className="flex h-full w-full flex-col bg-v4-canvas">
      <ModeTabStrip
        tabs={[
          { id: "geom", label: "几何" },
          { id: "info", label: "几何/CAD 信息" },
        ]}
        activeTabId="geom"
        trailing={
          <span className="font-mono text-[10px]">
            {dim ? `${dim}D` : "—"} · {patches.length} 边界面
            {cl ? ` · ${cl.name} ${cl.value.toPrecision(3)}${cl.unit}` : ""}
          </span>
        }
      />
      <div className="flex min-h-0 flex-1">
        {/* Part legend · left — real patches from workbench-basics */}
        <aside
          className="flex w-[200px] shrink-0 flex-col border-r border-v4-border bg-v4-shell/60"
          data-testid="v4-mode-geometry-legend"
        >
          <div className="border-b border-v4-border px-3 py-2 text-[10px] uppercase tracking-wider text-v4-textTertiary">
            边界面 · {patches.length} 项
          </div>
          <ul className="flex-1 overflow-y-auto px-1.5 py-1.5 text-[11px]">
            {patches.length === 0 && (
              <li className="px-2 py-1 text-v4-textTertiary">
                {caseId ? "无几何元数据" : "选择算例后显示"}
              </li>
            )}
            {patches.map((p) => {
              const c = roleColor(p.role);
              const isSelected = p.id === selectedPatchId;
              return (
                <li key={p.id}>
                  <button
                    type="button"
                    onClick={() =>
                      setSelectedPatchId((cur) => (cur === p.id ? null : p.id))
                    }
                    className={[
                      "flex w-full items-center gap-2 rounded px-2 py-1 text-left transition-colors",
                      isSelected
                        ? "bg-v4-surfaceRaised text-v4-textPrimary"
                        : "text-v4-textSecondary hover:bg-v4-surfaceRaised hover:text-v4-textPrimary",
                    ].join(" ")}
                    style={
                      isSelected ? { boxShadow: `inset 2px 0 0 ${c}` } : undefined
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
            })}
          </ul>
          {ctx.basics?.geometry && (
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
          )}
        </aside>

        {/* Scene · viewport over SVG fallback */}
        <div
          className="relative flex min-h-0 flex-1 items-center justify-center"
          data-viewport-active={showViewport ? "true" : "false"}
        >
          {showViewport ? (
            <ViewportV4
              glbUrl={glbUrl}
              cameraPreset={cameraPreset ?? "iso"}
              highlightedPatchId={selectedPatchId}
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center px-4 py-2">
              <IndustrialBoxScene
                variant="geometry"
                className="h-full max-h-[400px] w-full max-w-3xl"
              >
                <g>
                  <circle cx="260" cy="150" r="2.5" fill={V4_PALETTE.brand} opacity="0.85" />
                  <circle cx="330" cy="150" r="2.5" fill={V4_PALETTE.brand} opacity="0.85" />
                  <circle cx="395" cy="150" r="2.5" fill={V4_PALETTE.brand} opacity="0.85" />
                  <circle cx="455" cy="150" r="2.5" fill={V4_PALETTE.brand} opacity="0.85" />
                </g>
              </IndustrialBoxScene>
            </div>
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
              当前算例无导入几何 · 显示示意场景
            </div>
          )}
          {selectedPatchId && (
            <div
              className="pointer-events-none absolute left-3 bottom-3 rounded border border-v4-active/50 bg-v4-surfaceRaised/95 px-2 py-1 text-[10px]"
              data-testid="v4-mode-geometry-selection"
            >
              <span className="text-v4-textTertiary">已选 </span>
              <span className="font-mono text-v4-textPrimary">
                {patches.find((p) => p.id === selectedPatchId)?.label_zh ??
                  selectedPatchId}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
