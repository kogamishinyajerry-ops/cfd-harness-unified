/**
 * V4 · Mode renderer · 物理 (Physics) · per UI-SPEC §4.4
 *
 * 蓝图 3 视觉契合：半透 APU 外壳 + 内部真发动机几何。
 * Real-data wiring (2026-05-19):
 *   - When case has geometry.glb → ViewportV4 mounts vtk.js kernel and
 *     renders the actual case geometry (replaces the prior SVG cartoon
 *     IndustrialBoxScene that misled R3-R8 Codex reviews).
 *   - When no case yet → minimal "empty viewport" badge (no SVG fake).
 *
 * Materials & non-dimensional numbers in the right aside remain
 * advisor-derived; replacing those with case-real values is M5.5 (not
 * blocking the viewport-truthfulness arc).
 */
import { useState } from "react";

import { V4_CFD_COLORMAP } from "@/theme/industrial_minimalist";
import { ViewportV4, type V4CameraPreset } from "../ViewportV4";
import { ModeTabStrip } from "../ModeTabStrip";
import {
  geometryGlbUrl,
  useGlbAvailability,
} from "../../hooks/useGlbAvailability";
import {
  PHYSICS_BLUEPRINT_MATERIALS,
  PHYSICS_BLUEPRINT_MODELS,
  PHYSICS_BLUEPRINT_SUMMARY,
  PHYSICS_BLUEPRINT_TABS,
  PHYSICS_BLUEPRINT_VELOCITY_RANGE,
  PHYSICS_BLUEPRINT_VELOCITY_RANGE_TUPLE,
} from "../physicsBlueprint";

interface ModeRendererPhysicsProps {
  caseId: string | null | undefined;
  cameraPreset?: V4CameraPreset;
}

export function ModeRendererPhysics({
  caseId,
  cameraPreset = "iso",
}: ModeRendererPhysicsProps) {
  const glbUrl = geometryGlbUrl(caseId);
  const probe = useGlbAvailability(glbUrl);
  const hasGeometry = probe.available === true;
  const surfaceVtpUrl = caseId
    ? `/api/cases/${encodeURIComponent(caseId)}/post/surface.vtp?patch=engine`
    : null;
  const [vtpScalarRange, setVtpScalarRange] =
    useState<[number, number] | null>(null);
  const velocityRange: [number, number] = vtpScalarRange ?? [
    PHYSICS_BLUEPRINT_VELOCITY_RANGE.min,
    PHYSICS_BLUEPRINT_VELOCITY_RANGE.max,
  ];

  return (
    <div data-testid="v4-mode-physics" className="flex h-full w-full flex-col bg-v4-canvas">
      <ModeTabStrip
        tabs={PHYSICS_BLUEPRINT_TABS}
        activeTabId="recommended"
        trailing={
          <span className="font-mono text-[10px]">
            {PHYSICS_BLUEPRINT_SUMMARY.caseType} ·{" "}
            {PHYSICS_BLUEPRINT_SUMMARY.recommendedModel} · Re 8.4e5 · Pr 0.71
          </span>
        }
      />
      <div className="flex min-h-0 flex-1">
        <div className="relative flex min-h-0 flex-1 items-center justify-center">
          {hasGeometry && glbUrl ? (
            <>
              <ViewportV4
                glbUrl={glbUrl}
                cameraPreset={cameraPreset}
                surfaceVtpUrl={surfaceVtpUrl}
                surfaceVtpScalarRange={PHYSICS_BLUEPRINT_VELOCITY_RANGE_TUPLE}
                onVtpRangeReady={setVtpScalarRange}
              />
              <PhysicsVelocityLegend range={velocityRange} />
            </>
          ) : (
            <EmptyViewport probing={probe.available === undefined} />
          )}
        </div>
        <aside className="flex w-[180px] shrink-0 flex-col border-l border-v4-border bg-v4-shell p-3">
          <div className="mb-2 mt-3 text-[10px] uppercase tracking-wider text-v4-textTertiary">
            模型 · {PHYSICS_BLUEPRINT_MODELS.length}
          </div>
          <ul className="space-y-1.5">
            {PHYSICS_BLUEPRINT_MODELS.map((model) => (
              <li
                key={model.name}
                className={[
                  "rounded border bg-v4-surfaceRaised px-2 py-1.5 text-[11px]",
                  model.recommended
                    ? "border-v4-active/50"
                    : "border-v4-border",
                ].join(" ")}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-v4-textPrimary" title={model.name}>
                    {model.name}
                  </span>
                  <span
                    className="h-1.5 w-1.5 shrink-0 rounded-full"
                    style={{ backgroundColor: model.color }}
                  />
                </div>
                <div className="mt-0.5 flex justify-between gap-2 font-mono text-[9px] text-v4-textTertiary">
                  <span>{model.family}</span>
                  <span>{model.note}</span>
                </div>
              </li>
            ))}
          </ul>
          <div className="mb-2 text-[10px] uppercase tracking-wider text-v4-textTertiary">
            材料 · {PHYSICS_BLUEPRINT_MATERIALS.length}
          </div>
          <ul className="space-y-1.5">
            {PHYSICS_BLUEPRINT_MATERIALS.map((m) => (
              <li
                key={m.name}
                className="flex items-center justify-between gap-2 rounded border border-v4-border bg-v4-surfaceRaised px-2 py-1 text-[10px]"
              >
                <span className="truncate text-v4-textPrimary" title={m.name}>
                  {m.name}
                </span>
                <span className="shrink-0 font-mono text-[9px] text-v4-textTertiary">
                  ρ {m.rho}
                </span>
              </li>
            ))}
          </ul>
        </aside>
      </div>
    </div>
  );
}

function PhysicsVelocityLegend({ range }: { range: [number, number] }) {
  return (
    <div
      data-testid="v4-physics-velocity-legend"
      className="absolute bottom-3 left-3 flex items-center gap-2 rounded-md border border-v4-border bg-v4-canvas/90 px-2.5 py-1.5 text-[10px] text-v4-textSecondary shadow-lg"
    >
      <span className="font-mono text-v4-textTertiary">|U|</span>
      <div
        className="h-2 w-32 rounded-sm"
        style={{
          background: `linear-gradient(to right, ${V4_CFD_COLORMAP.join(", ")})`,
        }}
      />
      <span className="font-mono text-v4-textPrimary">
        {range[0].toFixed(0)} → {range[1].toFixed(2)} m/s
      </span>
    </div>
  );
}

/** Replaces the prior IndustrialBoxScene SVG cartoon — honest empty
 *  state when no case geometry has been ingested. */
function EmptyViewport({ probing }: { probing: boolean }) {
  return (
    <div
      data-testid="v4-physics-empty-viewport"
      className="flex h-full w-full flex-col items-center justify-center gap-2 text-v4-textTertiary"
    >
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4" opacity="0.4">
        <path d="M12 2L2 7v10l10 5 10-5V7L12 2z" />
        <path d="M2 7l10 5 10-5" />
        <path d="M12 22V12" />
      </svg>
      <div className="text-[11px]">
        {probing ? "正在探测几何…" : "无案例几何 · 先在导入步骤上传"}
      </div>
    </div>
  );
}
