/**
 * V4 · Mode renderer · 设计探索 (DOE) · per UI-SPEC §4.8
 *
 * DOE blueprint image 8: a dense design-exploration cockpit with a
 * 3x3 visible solution matrix, Pareto scatter, and decision-summary rails.
 * It remains display-only until the real DOE backend lands, but the
 * thumbnails render the real APU CAD GLB instead of the old SVG sketch.
 */
import { useState } from "react";

import { GEOMETRY_REAL_CAD_ASSEMBLY } from "../geometryBlueprint";
import { ViewportV4 } from "../ViewportV4";
import { useGlbAvailability } from "../../hooks/useGlbAvailability";
import { V4_CFD_COLORMAP, V4_PALETTE } from "@/theme/industrial_minimalist";
import {
  DOE_BLUEPRINT_KPIS,
  DOE_BLUEPRINT_SCATTER_POINTS,
  DOE_BLUEPRINT_SCATTER,
  DOE_BLUEPRINT_TOOLBAR,
  DOE_BLUEPRINT_VISIBLE_SAMPLES,
  DOE_BLUEPRINT_VERDICT,
  type DoeBlueprintSample,
} from "../doeBlueprint";

function Thumbnail({
  sample,
  active,
  onClick,
  cadReady,
  cadLoading,
}: {
  sample: DoeBlueprintSample;
  active: boolean;
  onClick: () => void;
  cadReady: boolean;
  cadLoading: boolean;
}) {
  const colorA = V4_CFD_COLORMAP[sample.seed % V4_CFD_COLORMAP.length];
  const colorB = V4_CFD_COLORMAP[(sample.seed + 2) % V4_CFD_COLORMAP.length];

  return (
    <button
      type="button"
      onClick={onClick}
      data-testid={`v4-mode-doe-thumb-${sample.id}`}
      data-active={active ? "true" : "false"}
      className={[
        "group flex h-full min-h-0 flex-col overflow-hidden rounded-md border-2 bg-v4-surfaceRaised text-left transition-all duration-150",
        active
          ? "scale-[1.02] border-v4-active shadow-[0_0_18px_rgba(240,169,59,0.18)]"
          : "border-v4-border hover:border-v4-borderActive",
      ].join(" ")}
    >
      <div className="flex items-start justify-between px-2 pt-1 text-[9px]">
        <div>
          <div className="font-mono text-[11px] text-v4-textPrimary">
            {sample.id}
          </div>
          <div className="mt-0.5 max-w-[150px] truncate text-v4-textSecondary">
            {sample.variableLabel}
          </div>
        </div>
        <span className="font-mono text-[9px] text-v4-textTertiary">
          +{sample.deltaPct.toFixed(1)}%
        </span>
      </div>
      <div
        className="relative mx-2 mt-1 h-12 shrink-0 overflow-hidden rounded bg-v4-canvas"
        data-testid={`v4-mode-doe-cad-thumb-${sample.id}`}
      >
        {cadReady ? (
          <ViewportV4
            glbUrl={GEOMETRY_REAL_CAD_ASSEMBLY.glbUrl}
            cameraPreset="iso"
            showGrid={false}
          />
        ) : (
          <div className="flex h-full items-center justify-center px-2 text-center text-[9px] text-v4-textTertiary">
            {cadLoading ? "加载 CAD 缩略图…" : "CAD 缩略图不可用"}
          </div>
        )}
        <div
          className="pointer-events-none absolute inset-0 opacity-35 mix-blend-screen"
          style={{
            background: `linear-gradient(110deg, transparent 0 34%, ${colorA} 48%, ${colorB} 64%, transparent 82%)`,
          }}
          aria-hidden
        />
        {sample.optimal && (
          <span className="absolute right-1.5 top-1.5 rounded border border-v4-active/50 bg-v4-canvas/85 px-1.5 py-0.5 text-[8px] text-v4-active">
            最优
          </span>
        )}
        <span className="absolute bottom-1 left-1 rounded border border-v4-border bg-v4-canvas/80 px-1.5 py-0.5 font-mono text-[8px] text-v4-textTertiary">
          CAD GLB
        </span>
      </div>
      <div className="grid grid-cols-2 gap-px border-t border-v4-border px-2 pb-1 pt-1 text-[9px]">
        <div className="flex items-center justify-between gap-1 rounded bg-v4-canvas/55 px-1 py-0.5">
          <div className="text-v4-textTertiary">Pa</div>
          <div
            className={[
              "font-mono text-[11px] tabular-nums",
              sample.optimal ? "text-v4-healthy" : "text-v4-textPrimary",
            ].join(" ")}
          >
            {sample.pressurePa.toFixed(1)}
          </div>
        </div>
        <div className="flex items-center justify-between gap-1 rounded bg-v4-canvas/55 px-1 py-0.5">
          <div className="text-v4-textTertiary">°C</div>
          <div
            className={[
              "font-mono text-[11px] tabular-nums",
              sample.optimal ? "text-v4-healthy" : "text-v4-textPrimary",
            ].join(" ")}
          >
            {sample.temperatureC.toFixed(1)}
          </div>
        </div>
      </div>
    </button>
  );
}

function ScatterPlot({
  samples,
  activeId,
}: {
  samples: DoeBlueprintSample[];
  activeId: string;
}) {
  const pMin = 180;
  const pMax = 370;
  const tMin = 92;
  const tMax = 102;
  return (
    <svg viewBox="0 0 620 130" preserveAspectRatio="none" className="h-full w-full">
      {[0.2, 0.4, 0.6, 0.8].map((t) => (
        <line
          key={`h-${t}`}
          x1="54"
          x2="598"
          y1={16 + t * 92}
          y2={16 + t * 92}
          stroke={V4_PALETTE.border}
          strokeWidth="0.3"
        />
      ))}
      {[0.25, 0.5, 0.75].map((t) => (
        <line
          key={`v-${t}`}
          x1={54 + t * 544}
          x2={54 + t * 544}
          y1="16"
          y2="108"
          stroke={V4_PALETTE.border}
          strokeWidth="0.25"
        />
      ))}
      <line
        x1="92"
        y1="92"
        x2="392"
        y2="55"
        stroke={DOE_BLUEPRINT_SCATTER.frontierColor}
        strokeWidth="0.6"
        strokeDasharray="3 3"
        opacity="0.55"
      />
      {samples.map((s) => {
        const x = 54 + ((s.pressurePa - pMin) / (pMax - pMin || 1)) * 544;
        const y = 16 + ((tMax - s.temperatureC) / (tMax - tMin || 1)) * 92;
        const isActive = s.id === activeId;
        return (
          <g key={s.id}>
            <circle
              cx={x}
              cy={y}
              r={isActive ? 5.4 : s.optimal ? 4.2 : 3.2}
              fill={
                isActive
                  ? DOE_BLUEPRINT_SCATTER.activeColor
                  : s.optimal
                    ? DOE_BLUEPRINT_SCATTER.recommendedColor
                    : V4_PALETTE.textTertiary
              }
              stroke={V4_PALETTE.shell}
              strokeWidth={isActive ? "1.5" : "0.8"}
            />
            {isActive && (
              <text
                x={x + 7}
                y={y - 4}
                fontSize="7"
                fill={V4_PALETTE.active}
                fontFamily="ui-monospace, monospace"
              >
                {s.id}
              </text>
            )}
          </g>
        );
      })}
      <text x="54" y="123" fontSize="8" fill={V4_PALETTE.textTertiary} fontFamily="ui-monospace, monospace">
        {DOE_BLUEPRINT_SCATTER.xLabel} →
      </text>
      <text x="18" y="16" fontSize="8" fill={V4_PALETTE.textTertiary} fontFamily="ui-monospace, monospace">
        ↑ {DOE_BLUEPRINT_SCATTER.yLabel}
      </text>
    </svg>
  );
}

export function ModeRendererDoe() {
  const [activeId, setActiveId] = useState<string>(
    DOE_BLUEPRINT_VERDICT.selectedId,
  );
  const cadProbe = useGlbAvailability(GEOMETRY_REAL_CAD_ASSEMBLY.glbUrl);
  const cadReady = cadProbe.available === true;

  return (
    <div data-testid="v4-mode-doe" className="flex h-full w-full flex-col bg-v4-canvas">
      <div className="flex h-11 shrink-0 items-center gap-3 border-b border-v4-border px-3">
        <div className="min-w-[210px] text-[13px] font-medium text-v4-textPrimary">
          设计探索
          <span className="ml-2 text-[12px] font-normal text-v4-textSecondary">
            / 探索集_02 ({DOE_BLUEPRINT_KPIS.sampleCount})
          </span>
        </div>
        <div className="ml-auto flex min-w-0 items-center gap-2 text-[10px] text-v4-textSecondary">
          {DOE_BLUEPRINT_TOOLBAR.map((item) => {
            if (item.id === "search") {
              return (
                <div
                  key={item.id}
                  className="flex h-7 w-[150px] items-center gap-2 rounded border border-v4-border bg-v4-surfaceRaised px-2"
                  data-testid="v4-doe-toolbar-search"
                >
                  <span className="text-v4-textTertiary">⌕</span>
                  <span className="text-v4-textTertiary">{item.label}</span>
                </div>
              );
            }
            if (item.id === "view") {
              return (
                <div
                  key={item.id}
                  className="flex h-7 items-center rounded border border-v4-border bg-v4-surfaceRaised"
                  data-testid="v4-doe-toolbar-view"
                >
                  <span className="border-r border-v4-border px-2 text-v4-textPrimary">
                    ▦
                  </span>
                  <span className="px-2 text-v4-textTertiary">☰</span>
                </div>
              );
            }
            return (
              <button
                key={item.id}
                type="button"
                className="h-7 rounded border border-v4-border bg-v4-surfaceRaised px-2 hover:border-v4-borderActive hover:text-v4-textPrimary"
                data-testid={`v4-doe-toolbar-${item.id}`}
              >
                {item.label}
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-2.5 p-3">
        <div className="grid min-h-0 flex-1 grid-cols-3 grid-rows-3 gap-2">
          {DOE_BLUEPRINT_VISIBLE_SAMPLES.map((s) => (
            <Thumbnail
              key={s.id}
              sample={s}
              active={s.id === activeId}
              onClick={() => setActiveId(s.id)}
              cadReady={cadReady}
              cadLoading={cadProbe.isLoading}
            />
          ))}
        </div>
        <div className="flex h-24 shrink-0 flex-col gap-1 rounded border border-v4-border bg-v4-surfaceRaised p-2">
          <div className="flex items-baseline justify-between text-[10px]">
            <span className="text-v4-textSecondary">
              帕累托前沿 · 压降 vs 最高温度
            </span>
            <span className="font-mono text-v4-textTertiary">
              全部方案 · 最优解 {DOE_BLUEPRINT_VERDICT.selectedId}
            </span>
          </div>
          <div className="min-h-0 flex-1">
            <ScatterPlot
              samples={DOE_BLUEPRINT_SCATTER_POINTS}
              activeId={activeId}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
