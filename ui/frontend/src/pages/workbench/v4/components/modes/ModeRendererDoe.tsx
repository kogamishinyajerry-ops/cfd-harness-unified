/**
 * V4 · Mode renderer · 设计探索 (DOE) · per UI-SPEC §4.8
 *
 * 3×3 thumbnail grid + scatter plot. Each thumbnail has VARIATION (different
 * seed for streamlines) so the 9 samples read as different parameter sweeps,
 * not 9 identical images.
 */
import { useState } from "react";

import { IndustrialBoxScene } from "../scene/IndustrialBoxScene";
import { StreamlineField } from "../scene/streamlines";
import { ModeTabStrip } from "../ModeTabStrip";
import { V4_PALETTE } from "@/theme/industrial_minimalist";
import {
  DOE_BLUEPRINT_KPIS,
  DOE_BLUEPRINT_SAMPLES,
  DOE_BLUEPRINT_SCATTER,
  DOE_BLUEPRINT_TABS,
  DOE_BLUEPRINT_VERDICT,
  type DoeBlueprintSample,
} from "../doeBlueprint";

function Thumbnail({
  sample,
  active,
  onClick,
}: {
  sample: DoeBlueprintSample;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      data-testid={`v4-mode-doe-thumb-${sample.id}`}
      data-active={active ? "true" : "false"}
      className={[
        "group flex min-h-0 flex-col gap-1 overflow-hidden rounded-md border-2 bg-v4-surfaceRaised p-1.5 text-left transition-all duration-150",
        active
          ? "scale-[1.02] border-v4-active shadow-[0_0_18px_rgba(240,169,59,0.18)]"
          : "border-v4-border hover:border-v4-borderActive",
      ].join(" ")}
    >
      <div className="relative aspect-[5/3] overflow-hidden rounded bg-v4-canvas">
        <IndustrialBoxScene variant="post" className="h-full w-full">
          <StreamlineField
            count={26}
            seed={sample.seed}
            opacityMul={0.62}
            baseStroke={0.38}
          />
        </IndustrialBoxScene>
        {sample.recommended && (
          <span className="absolute left-1.5 top-1.5 rounded border border-v4-healthy/40 bg-v4-canvas/85 px-1.5 py-0.5 font-mono text-[8px] text-v4-healthy">
            REC
          </span>
        )}
      </div>
      <div className="flex items-baseline justify-between text-[9px]">
        <span className="font-mono text-v4-textSecondary">{sample.id}</span>
        <span
          className={
            sample.deltaPct >= 0
              ? "font-mono text-v4-healthy"
              : "font-mono text-v4-warn"
          }
        >
          {sample.deltaPct >= 0 ? "+" : ""}
          {sample.deltaPct.toFixed(1)}%
        </span>
      </div>
      <div className="grid grid-cols-2 gap-x-2 gap-y-0.5 text-[9px] text-v4-textTertiary">
        <span>P {sample.pressurePa.toFixed(1)}</span>
        <span>T {sample.temperatureC.toFixed(1)}</span>
        <span className="col-span-2">V {sample.volumeM3.toFixed(2)} m³</span>
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
  const pMin = Math.min(...samples.map((s) => s.pressurePa));
  const pMax = Math.max(...samples.map((s) => s.pressurePa));
  const tMin = Math.min(...samples.map((s) => s.temperatureC));
  const tMax = Math.max(...samples.map((s) => s.temperatureC));
  return (
    <svg viewBox="0 0 300 100" preserveAspectRatio="none" className="h-full w-full">
      {[0.25, 0.5, 0.75].map((t) => (
        <line
          key={`h-${t}`}
          x1="20"
          x2="290"
          y1={10 + t * 80}
          y2={10 + t * 80}
          stroke={V4_PALETTE.border}
          strokeWidth="0.3"
        />
      ))}
      <line
        x1="40"
        y1="72"
        x2="280"
        y2="20"
        stroke={DOE_BLUEPRINT_SCATTER.frontierColor}
        strokeWidth="0.6"
        strokeDasharray="3 3"
        opacity="0.55"
      />
      {samples.map((s) => {
        const x = 20 + ((s.pressurePa - pMin) / (pMax - pMin || 1)) * 270;
        const y = 10 + ((tMax - s.temperatureC) / (tMax - tMin || 1)) * 80;
        const isActive = s.id === activeId;
        return (
          <g key={s.id}>
            <circle
              cx={x}
              cy={y}
              r={isActive ? 4.8 : s.recommended ? 3.6 : 2.8}
              fill={
                isActive
                  ? DOE_BLUEPRINT_SCATTER.activeColor
                  : s.recommended
                    ? DOE_BLUEPRINT_SCATTER.recommendedColor
                    : V4_PALETTE.brand
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
      <text x="20" y="98" fontSize="7" fill={V4_PALETTE.textTertiary} fontFamily="ui-monospace, monospace">
        {DOE_BLUEPRINT_SCATTER.xLabel} →
      </text>
      <text x="22" y="10" fontSize="7" fill={V4_PALETTE.textTertiary} fontFamily="ui-monospace, monospace">
        ↑ {DOE_BLUEPRINT_SCATTER.yLabel}
      </text>
    </svg>
  );
}

export function ModeRendererDoe() {
  const [activeId, setActiveId] = useState<string>(
    DOE_BLUEPRINT_VERDICT.selectedId,
  );
  const activeSample =
    DOE_BLUEPRINT_SAMPLES.find((s) => s.id === activeId) ??
    DOE_BLUEPRINT_SAMPLES[0];

  return (
    <div data-testid="v4-mode-doe" className="flex h-full w-full flex-col bg-v4-canvas">
      <ModeTabStrip
        tabs={DOE_BLUEPRINT_TABS}
        activeTabId="samples"
        trailing={
          <span className="font-mono text-[10px]">
            {DOE_BLUEPRINT_KPIS.sampleCount} 样本 · 已选 {activeId} ·{" "}
            {activeSample.deltaPct >= 0 ? "+" : ""}
            {activeSample.deltaPct.toFixed(1)}%
          </span>
        }
      />
      <div className="flex min-h-0 flex-1 flex-col gap-2.5 p-3">
        <div className="grid min-h-0 flex-[1.35] grid-cols-3 gap-2">
          {DOE_BLUEPRINT_SAMPLES.map((s) => (
            <Thumbnail
              key={s.id}
              sample={s}
              active={s.id === activeId}
              onClick={() => setActiveId(s.id)}
            />
          ))}
        </div>
        <div className="flex h-28 shrink-0 flex-col gap-1 rounded border border-v4-border bg-v4-surfaceRaised p-2">
          <div className="flex items-baseline justify-between text-[10px]">
            <span className="text-v4-textSecondary">
              Pareto · 压降 vs 温度 · {DOE_BLUEPRINT_KPIS.sampleCount} 样本
            </span>
            <span className="font-mono text-v4-textTertiary">
              推荐 5 · 已选 {activeId}
            </span>
          </div>
          <div className="min-h-0 flex-1">
            <ScatterPlot samples={DOE_BLUEPRINT_SAMPLES} activeId={activeId} />
          </div>
        </div>
      </div>
    </div>
  );
}
