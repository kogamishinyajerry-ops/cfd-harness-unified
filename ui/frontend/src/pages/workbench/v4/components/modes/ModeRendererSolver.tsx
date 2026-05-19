/**
 * V4 · Mode renderer · 求解 (Solver) · per UI-SPEC §4.6
 *
 * 蓝图 6/7 视觉契合 (2026-05-19 dogfood retrofit):
 *   - Real geometry viewport via ViewportV4 → loads case glb.
 *   - Real residual chart from the residual-series endpoint
 *     (the same one R6-R8 wired for Post mode, now reused here).
 *   - Run telemetry overlay reads latest run from useV4WorkbenchContext.
 *
 * What used to live here:
 *   - IndustrialBoxScene + StreamlineField (hand-drawn SVG cartoon)
 *   - Hardcoded residual series + temp history + GPU/CPU chips
 * That was visually-pleasing wireframe but **zero real data** — the
 * KJ66 dogfood (2026-05-19) caught this gap; Codex R3-R8 missed it.
 *
 * Still SVG / advisor-only for the moment (clearly labeled):
 *   - Temp history sparkline (no temp probe exposed yet)
 *   - GPU/CPU/MEM/δt chips (no solver-host telemetry endpoint)
 * Replacing those is M3.5+ — they don't block the viewport-truthfulness
 * arc.
 */
import { useCallback, useState } from "react";

import { useResidualSeries } from "../../hooks/useResidualSeries";
import { useV4WorkbenchContext } from "../../hooks/useV4WorkbenchContext";
import { V4_CFD_COLORMAP, V4_PALETTE } from "@/theme/industrial_minimalist";
import { ViewportV4, type V4CameraPreset } from "../ViewportV4";
import {
  geometryGlbUrl,
  useGlbAvailability,
} from "../../hooks/useGlbAvailability";
import type { ResidualSeriesPayload } from "@/types/residual_series";

interface ModeRendererSolverProps {
  caseId: string | null | undefined;
  cameraPreset?: V4CameraPreset;
}

// Canonical legend order — same convention as ModeRendererPost (R6 L-1).
const CANONICAL_ORDER: readonly string[] = [
  "Ux", "Uy", "Uz", "U", "p", "k", "omega", "epsilon", "T",
];
const RESIDUAL_COLOR: Record<string, string> = {
  Ux: V4_PALETTE.brand,
  Uy: V4_PALETTE.active,
  Uz: V4_PALETTE.warn,
  U: V4_PALETTE.brand,
  p: V4_PALETTE.healthy,
  k: V4_PALETTE.crit,
  omega: V4_PALETTE.textPrimary,
  epsilon: V4_PALETTE.textSecondary,
  T: V4_PALETTE.warn,
};

function canonicalEntries<T>(series: Record<string, T>): Array<[string, T]> {
  return Object.entries(series).sort(([a], [b]) => {
    const ai = CANONICAL_ORDER.indexOf(a);
    const bi = CANONICAL_ORDER.indexOf(b);
    if (ai >= 0 && bi >= 0) return ai - bi;
    if (ai >= 0) return -1;
    if (bi >= 0) return 1;
    return a.localeCompare(b);
  });
}

function colorFor(name: string): string {
  return RESIDUAL_COLOR[name] ?? V4_PALETTE.textTertiary;
}

function VelocityLegendStrip({ range }: { range: [number, number] | null }) {
  const hi = range?.[1] ?? null;
  return (
    <div
      className="absolute bottom-3 left-1/2 z-10 -translate-x-1/2 rounded border border-v4-border bg-v4-shell/85 px-2 py-1 text-[9px] shadow-lg backdrop-blur"
      data-testid="v4-solver-velocity-legend"
    >
      <div className="flex items-center gap-2">
        <span className="font-mono text-v4-textTertiary">|U|</span>
        <div
          className="h-2 w-36 rounded-sm"
          style={{
            background: `linear-gradient(to right, ${V4_CFD_COLORMAP.join(", ")})`,
          }}
        />
        <span className="font-mono text-v4-textPrimary">
          0 → {hi != null ? hi.toFixed(2) : "—"} m/s
        </span>
      </div>
    </div>
  );
}

/** Real multi-series log-y residual chart from the same data source the
 *  Post-mode chart uses. Decade gridlines + target-floor reference line.
 *  Identical math to ModeRendererPost's ResidualLogChart — kept inline
 *  here to avoid forcing a cross-mode shared component while the arc
 *  is still in motion. */
function RealResidualsChart({ payload }: { payload: ResidualSeriesPayload }) {
  const entries = canonicalEntries(payload.series).filter(
    ([, pts]) => pts.length > 0,
  );
  if (entries.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-[10px] text-v4-textTertiary">
        无残差数据
      </div>
    );
  }

  // Y axis = log10. Find global range padded one decade.
  const ys: number[] = [];
  for (const [, pts] of entries)
    for (const p of pts) if (p.y > 0 && Number.isFinite(p.y)) ys.push(p.y);
  if (ys.length === 0) return null;
  const logMin = Math.floor(Math.log10(Math.min(...ys))) - 1;
  const logMax = Math.ceil(Math.log10(Math.max(...ys)));
  const xMax = payload.sample_count;

  function px(x: number): number {
    return 24 + (x / Math.max(1, xMax)) * 208;
  }
  function py(y: number): number {
    const lv = Math.log10(Math.max(1e-30, y));
    return 8 + ((logMax - lv) / Math.max(1, logMax - logMin)) * 92;
  }

  const targetLogV = Math.log10(payload.target_floor);
  const targetWithinRange = targetLogV >= logMin && targetLogV <= logMax;

  return (
    <svg viewBox="0 0 240 110" preserveAspectRatio="none" className="h-full w-full">
      {/* Decade gridlines */}
      {Array.from({ length: logMax - logMin + 1 }, (_, k) => logMin + k).map(
        (logV, i) => {
          const y = py(Math.pow(10, logV));
          return (
            <g key={`g${i}`}>
              <line
                x1="22" x2="232" y1={y} y2={y}
                stroke={V4_PALETTE.border} strokeWidth="0.3"
              />
              <text
                x="2" y={y + 3} fontSize="6"
                fill={V4_PALETTE.textTertiary}
                fontFamily="ui-monospace, monospace"
              >
                1e{logV}
              </text>
            </g>
          );
        },
      )}
      {/* Target floor reference */}
      {targetWithinRange && (
        <line
          x1="22" x2="232"
          y1={py(payload.target_floor)}
          y2={py(payload.target_floor)}
          stroke={V4_PALETTE.healthy} strokeWidth="0.6" strokeDasharray="2 2"
          opacity="0.7"
        />
      )}
      {/* Series */}
      {entries.map(([name, pts], idx) => {
        const polyPoints = pts
          .map((p) => `${px(p.x)},${py(p.y)}`)
          .join(" ");
        return (
          <g key={name}>
            <polyline
              points={polyPoints}
              fill="none"
              stroke={colorFor(name)}
              strokeWidth="1.2"
            />
            <text
              x="236" y={14 + idx * 10}
              fontSize="7" fill={colorFor(name)}
              fontFamily="ui-monospace, monospace"
              textAnchor="end"
            >
              {name}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export function ModeRendererSolver({
  caseId,
  cameraPreset = "iso",
}: ModeRendererSolverProps) {
  const glbUrl = geometryGlbUrl(caseId);
  const glbProbe = useGlbAvailability(glbUrl);
  const hasGeom = glbProbe.available === true;

  const ctx = useV4WorkbenchContext(caseId ?? null);
  const residuals = useResidualSeries(caseId ?? null);
  const surfaceVtpUrl = caseId
    ? `/api/cases/${encodeURIComponent(caseId)}/post/surface.vtp?patch=engine`
    : null;
  const streamlinesVtpUrl = caseId
    ? `/api/cases/${encodeURIComponent(caseId)}/post/streamlines.vtp`
    : null;
  const [vtpScalarRange, setVtpScalarRange] =
    useState<[number, number] | null>(null);
  const handleVtpRangeReady = useCallback((range: [number, number]) => {
    setVtpScalarRange((prev) => [
      0,
      Math.max(prev?.[1] ?? 0, range[1]),
    ]);
  }, []);

  const iterCount = residuals.data?.sample_count ?? 0;
  const runId = ctx.latestRun?.run_id ?? null;
  const elapsed = ctx.elapsedDisplay;
  const converging =
    residuals.data?.source === "log" || residuals.data?.source === "runs";
  const achieved = residuals.data?.achieved === true;

  return (
    <div data-testid="v4-mode-solver" className="flex h-full w-full bg-v4-canvas">
      {/* Scene · ~60% */}
      <div className="relative flex min-h-0 flex-[1.4] items-center justify-center">
        {hasGeom && glbUrl ? (
          <>
            <ViewportV4
              glbUrl={glbUrl}
              cameraPreset={cameraPreset}
              // Solver mode is the blueprint first screen: keep the
              // latest U-colored surface and integrated tracks together
              // so the field stays readable on the dark industrial canvas.
              surfaceVtpUrl={surfaceVtpUrl}
              streamlinesVtpUrl={streamlinesVtpUrl}
              onVtpRangeReady={handleVtpRangeReady}
            />
            <VelocityLegendStrip range={vtpScalarRange} />
          </>
        ) : (
          <EmptyViewport probing={glbProbe.available === undefined} />
        )}

        {/* Iteration progress overlay · top-left · real data */}
        <div
          className="absolute left-4 top-2 flex items-center gap-2 rounded border border-v4-border bg-v4-shell/90 px-2.5 py-1 text-[10px]"
          data-testid="v4-mode-solver-iter-overlay"
        >
          <span
            aria-hidden
            className="h-1.5 w-1.5 rounded-full"
            style={{
              backgroundColor: achieved
                ? V4_PALETTE.healthy
                : converging
                  ? V4_PALETTE.active
                  : V4_PALETTE.textTertiary,
              animation: converging && !achieved ? "pulse 2s infinite" : undefined,
            }}
          />
          <span className="font-mono text-v4-textPrimary">
            {iterCount > 0 ? `iter ${iterCount}` : "无运行"}
          </span>
          {runId && (
            <>
              <span className="text-v4-textTertiary">·</span>
              <span className="font-mono text-v4-textSecondary">
                {runId.slice(0, 8)}
              </span>
              <span className="text-v4-textTertiary">·</span>
              <span className="font-mono text-v4-textSecondary">{elapsed}</span>
            </>
          )}
          {streamlinesVtpUrl && (
            <>
              <span className="text-v4-textTertiary">·</span>
              <span className="font-mono text-v4-textSecondary">
                latest field
              </span>
            </>
          )}
        </div>
      </div>

      {/* Telemetry strip · ~30% */}
      <div className="flex w-64 shrink-0 flex-col gap-2 border-l border-v4-border bg-v4-shell p-3">
        <div className="flex flex-col gap-1 rounded border border-v4-border bg-v4-surfaceRaised p-2">
          <div className="flex items-baseline justify-between text-[10px]">
            <span className="text-v4-textSecondary">残差 · residual (log)</span>
            <span
              className={
                achieved
                  ? "font-mono text-v4-healthy"
                  : converging
                    ? "font-mono text-v4-active"
                    : "font-mono text-v4-textTertiary"
              }
            >
              {achieved ? "✓ 已达标" : converging ? "↓ converging" : "—"}
            </span>
          </div>
          <div className="h-[110px]">
            {residuals.isLoading && (
              <div className="flex h-full items-center justify-center text-[10px] text-v4-textTertiary">
                加载残差…
              </div>
            )}
            {residuals.data && residuals.data.source === "empty" && (
              <div className="flex h-full flex-col items-center justify-center gap-1 text-[10px] text-v4-textTertiary">
                <span>无求解记录</span>
                <span className="text-[9px]">运行 simpleFoam 后此处显示残差衰减</span>
              </div>
            )}
            {residuals.data && residuals.data.source !== "empty" && (
              <RealResidualsChart payload={residuals.data} />
            )}
          </div>
          {residuals.data && residuals.data.source !== "empty" && (
            <div className="text-[9px] text-v4-textTertiary">
              {residuals.data.note}
            </div>
          )}
        </div>
        <div className="flex flex-col gap-1 rounded border border-v4-border bg-v4-surfaceRaised p-2 text-[10px]">
          <div className="flex justify-between">
            <span className="text-v4-textTertiary">来源</span>
            <span className="font-mono text-v4-textPrimary">
              {residuals.data?.source ?? "—"}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-v4-textTertiary">样本数</span>
            <span className="font-mono text-v4-textPrimary">{iterCount}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-v4-textTertiary">目标</span>
            <span className="font-mono text-v4-textPrimary">
              {residuals.data?.target_floor.toExponential(0) ?? "1e-6"}
            </span>
          </div>
        </div>
        <div className="rounded border border-dashed border-v4-border bg-v4-canvas p-2 text-[9px] leading-relaxed text-v4-textTertiary">
          GPU/CPU/MEM/δt 仪表板 · 求解器主机遥测端点未上线 · 暂不显示假数据
        </div>
      </div>
    </div>
  );
}

function EmptyViewport({ probing }: { probing: boolean }) {
  return (
    <div
      data-testid="v4-solver-empty-viewport"
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
