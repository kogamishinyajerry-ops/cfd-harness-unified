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

interface DoeSample {
  id: string;
  pressure: number;
  temp: number;
  flow: number;
  delta: string;
  deltaTone: "healthy" | "warn";
  seed: number;
}

const SAMPLES: DoeSample[] = [
  { id: "S-01", pressure: 198.7, temp: 96.8, flow: 3.42, delta: "-2.1%", deltaTone: "warn", seed: 3 },
  { id: "S-02", pressure: 222.1, temp: 95.1, flow: 3.61, delta: "+0.8%", deltaTone: "healthy", seed: 7 },
  { id: "S-03", pressure: 231.4, temp: 94.7, flow: 3.78, delta: "+2.2%", deltaTone: "healthy", seed: 11 },
  { id: "S-04", pressure: 206.8, temp: 95.9, flow: 3.51, delta: "-1.0%", deltaTone: "warn", seed: 13 },
  { id: "S-05", pressure: 212.6, temp: 94.1, flow: 3.95, delta: "+4.2%", deltaTone: "healthy", seed: 17 },
  { id: "S-06", pressure: 248.6, temp: 93.6, flow: 3.62, delta: "+0.9%", deltaTone: "healthy", seed: 19 },
  { id: "S-07", pressure: 196.4, temp: 96.2, flow: 3.38, delta: "-2.4%", deltaTone: "warn", seed: 23 },
  { id: "S-08", pressure: 219.2, temp: 95.4, flow: 3.65, delta: "+1.5%", deltaTone: "healthy", seed: 29 },
  { id: "S-09", pressure: 235.7, temp: 94.8, flow: 3.71, delta: "+2.8%", deltaTone: "healthy", seed: 31 },
];

function Thumbnail({
  sample,
  active,
  onClick,
}: {
  sample: DoeSample;
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
        "group flex flex-col gap-1 overflow-hidden rounded-md border-2 bg-v4-surfaceRaised p-1.5 transition-all duration-150",
        active
          ? "border-v4-active scale-[1.02]"
          : "border-v4-border hover:border-v4-borderActive",
      ].join(" ")}
    >
      <div className="aspect-[5/3] overflow-hidden rounded bg-v4-canvas">
        <IndustrialBoxScene variant="solver" className="h-full w-full">
          <StreamlineField count={28} seed={sample.seed} opacityMul={0.7} baseStroke={0.4} />
        </IndustrialBoxScene>
      </div>
      <div className="flex items-baseline justify-between text-[9px]">
        <span className="font-mono text-v4-textSecondary">{sample.id}</span>
        <span
          className={
            sample.deltaTone === "healthy"
              ? "font-mono text-v4-healthy"
              : "font-mono text-v4-warn"
          }
        >
          {sample.delta}
        </span>
      </div>
      <div className="flex justify-between text-[9px] text-v4-textTertiary">
        <span>P {sample.pressure.toFixed(1)}</span>
        <span>T {sample.temp.toFixed(1)}</span>
        <span>Q {sample.flow.toFixed(2)}</span>
      </div>
    </button>
  );
}

function ScatterPlot({ samples, activeId }: { samples: DoeSample[]; activeId: string }) {
  const pMin = Math.min(...samples.map((s) => s.pressure));
  const pMax = Math.max(...samples.map((s) => s.pressure));
  const tMin = Math.min(...samples.map((s) => s.temp));
  const tMax = Math.max(...samples.map((s) => s.temp));
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
        y1="22"
        x2="280"
        y2="78"
        stroke={V4_PALETTE.healthy}
        strokeWidth="0.6"
        strokeDasharray="3 3"
        opacity="0.55"
      />
      {samples.map((s) => {
        const x = 20 + ((s.pressure - pMin) / (pMax - pMin || 1)) * 270;
        const y = 10 + ((tMax - s.temp) / (tMax - tMin || 1)) * 80;
        const isActive = s.id === activeId;
        return (
          <circle
            key={s.id}
            cx={x}
            cy={y}
            r={isActive ? 4.5 : 3}
            fill={isActive ? V4_PALETTE.active : V4_PALETTE.brand}
            stroke={V4_PALETTE.shell}
            strokeWidth={isActive ? "1.5" : "0.8"}
          />
        );
      })}
      <text x="20" y="98" fontSize="7" fill={V4_PALETTE.textTertiary} fontFamily="ui-monospace, monospace">
        压力 →
      </text>
      <text x="22" y="10" fontSize="7" fill={V4_PALETTE.textTertiary} fontFamily="ui-monospace, monospace">
        ↑ 温度
      </text>
    </svg>
  );
}

export function ModeRendererDoe() {
  const [activeId, setActiveId] = useState("S-05");
  const activeSample = SAMPLES.find((s) => s.id === activeId)!;

  return (
    <div data-testid="v4-mode-doe" className="flex h-full w-full flex-col bg-v4-canvas">
      <ModeTabStrip
        tabs={[
          { id: "samples", label: "样本网格" },
          { id: "pareto", label: "Pareto" },
          { id: "sensitivity", label: "敏感性" },
        ]}
        activeTabId="samples"
        trailing={
          <span className="font-mono text-[10px]">
            28 样本 · 已选 {activeId} · {activeSample.delta}
          </span>
        }
      />
      <div className="flex min-h-0 flex-1 flex-col gap-3 p-3">
        <div className="grid flex-[1.4] grid-cols-3 gap-2">
          {SAMPLES.map((s) => (
            <Thumbnail
              key={s.id}
              sample={s}
              active={s.id === activeId}
              onClick={() => setActiveId(s.id)}
            />
          ))}
        </div>
        <div className="flex h-24 shrink-0 flex-col gap-1 rounded border border-v4-border bg-v4-surfaceRaised p-2">
          <div className="flex items-baseline justify-between text-[10px]">
            <span className="text-v4-textSecondary">Pareto · 压力 vs 温度 · 28 样本</span>
            <span className="font-mono text-v4-textTertiary">已选 {activeId}</span>
          </div>
          <div className="min-h-0 flex-1">
            <ScatterPlot samples={SAMPLES} activeId={activeId} />
          </div>
        </div>
      </div>
    </div>
  );
}
